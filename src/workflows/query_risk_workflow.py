from __future__ import annotations

import json
import re
import uuid
from functools import lru_cache

from langgraph.graph import END, StateGraph

from src.database.connection import SessionLocal
from src.database.models import QueryAuditLogModel
from src.schemas.query_risk import QueryRiskState
from src.services.ollama_client import OllamaClient
from src.utils.yaml_loader import load_policy


# ──────────────────────────────────────────────────────────────
# 노드 1: 정책 로더 (DB → yaml_path → Policy 객체)
# ──────────────────────────────────────────────────────────────
def policy_loader_node(state: QueryRiskState) -> dict:
    """
    DB의 policies 테이블에서 policy_id로 yaml_path 조회.
    is_active=TRUE인 정책만 허용.
    실패 → rule_blocked=True (Fail-Safe BLOCKED).
    """
    from src.database.models import PolicyModel
    session = SessionLocal()
    try:
        row = session.query(PolicyModel).filter(
            PolicyModel.id == state["policy_id"],
            PolicyModel.is_active == True,
        ).first()

        if not row:
            return {
                "error_message": f"policy_id={state['policy_id']} 활성 정책 없음",
                "rule_blocked":  True,
                "rule_violations": [{
                    "type": "POLICY_NOT_FOUND",
                    "matched": state["policy_id"],
                    "severity": "HIGH",
                }],
            }

        policy = load_policy(row.yaml_path)
        return {"policy": policy.model_dump()}

    except Exception as e:
        return {
            "error_message": str(e),
            "rule_blocked": True,
            "rule_violations": [{
                "type": "POLICY_LOAD_ERROR",
                "matched": str(e)[:200],
                "severity": "HIGH",
            }],
        }
    finally:
        session.close()


# ──────────────────────────────────────────────────────────────
# 룰 엔진 헬퍼: 단어 경계 매칭 (영문) vs substring (한국어)
# ──────────────────────────────────────────────────────────────
def _term_matches(term: str, query: str, case_insensitive: bool = True) -> bool:
    """
    ASCII 전용 단어는 \\b 경계 적용 → 'kill'이 'skillet'에 매칭되지 않게 함.
    한국어/혼합 단어는 substring 매칭 (한글에는 자연스러운 단어 경계 없음).
    """
    if not term:
        return False
    flags = re.IGNORECASE if case_insensitive else 0
    if all(ord(c) < 128 for c in term):
        # ASCII only — word boundary
        pattern = r"\b" + re.escape(term) + r"\b"
        return bool(re.search(pattern, query, flags=flags))
    # Korean / mixed — substring
    if case_insensitive:
        return term.lower() in query.lower()
    return term in query


def _safe_regex_search(pattern: str, query: str) -> bool:
    """잘못된 정규식 패턴이 있어도 워크플로우 전체가 깨지지 않도록 격리."""
    try:
        return bool(re.search(pattern, query))
    except re.error:
        return False


# ──────────────────────────────────────────────────────────────
# Jailbreak 패턴 (영문 + 한국어) — PRD 5.1.2: BLOCK
# ──────────────────────────────────────────────────────────────
_JAILBREAK_PATTERNS: list[str] = [
    # 영문
    r"(?i)ignore\s+(previous|above|all)\s+(instruction|rule|policy|prompt)",
    r"(?i)disregard\s+(all|previous|above)\s+(instruction|rule|prompt)",
    r"(?i)act\s+as\s+(if\s+you\s+are|a|an)",
    r"(?i)you\s+are\s+now\s+(a|an|the)",
    r"(?i)(pretend|imagine|roleplay).*(no\s+restriction|no\s+limit|no\s+filter)",
    r"(?i)bypass\s+(all|the)\s+(restriction|filter|safety|guardrail)",
    # 한국어 — 한국어 조사(을/를/은/는/이/가)는 (?:을|를|은|는|이|가)? 로 흡수
    r"(이전|위의?|앞의?)\s*(지시|규칙|정책|명령|프롬프트)(?:을|를|은|는|이|가)?\s*(무시|잊|벗어)",
    r"(너|당신|네)\s*(는|은)?\s*(이제|지금부터)\s*(다른|새로운)?\s*(AI|역할|페르소나|봇)",
    r"(제약|제한|규칙|가이드라인)(?:을|를|은|는|이|가)?\s*(풀고|해제|무력화|벗어나|우회)",
    r"(역할|페르소나|캐릭터)\s*(놀이|플레이|연기)",
]


# ──────────────────────────────────────────────────────────────
# 노드 2: 룰 엔진 (결정론적 — LLM 독립)
# ──────────────────────────────────────────────────────────────
# PRD 5.1.2 매핑:
#   Forbidden Words / Phrase Patterns → BLOCK (HIGH)
#   Jailbreak Patterns                → BLOCK (HIGH)
#   PII Patterns                      → LOG+WARN (MEDIUM, blocked=False)
def rule_engine_node(state: QueryRiskState) -> dict:
    """
    정책의 카테고리별 forbidden_words / phrase_patterns / pii_patterns 를 평가.
    HIGH 위반 → rule_blocked=True (LLM 우회). MEDIUM (PII) → blocked=False, LLM 계속.
    """
    query = state.get("query", "")
    policy = state.get("policy", {})
    violations: list[dict] = []
    blocked = False  # HIGH severity 위반 발견 시에만 True

    # ── ① 정책 기반: forbidden_words / phrase_patterns / pii_patterns ──
    for rule in policy.get("rules", []):
        if rule.get("condition") != "contains_categorized_forbidden_terms":
            continue
        params = rule.get("parameters", {}) or {}
        case_insensitive = params.get("case_insensitive", True)
        categories = params.get("categories", {}) or {}

        for cat_name, cat in categories.items():
            if not cat.get("enabled", True):
                continue  # ⚠️ enabled=false 카테고리는 건너뜀

            # 1a. exact_terms — HIGH severity
            if not blocked:
                for term in cat.get("exact_terms", []) or []:
                    if _term_matches(term, query, case_insensitive):
                        violations.append({
                            "type": "FORBIDDEN_WORD",
                            "category": cat_name,
                            "matched": term,
                            "severity": "HIGH",
                        })
                        blocked = True
                        break

            # 1b. phrase_patterns (정규식) — HIGH severity
            if not blocked:
                for pattern in cat.get("phrase_patterns", []) or []:
                    if _safe_regex_search(pattern, query):
                        violations.append({
                            "type": "FORBIDDEN_PHRASE",
                            "category": cat_name,
                            "matched": pattern[:80],
                            "severity": "HIGH",
                        })
                        blocked = True
                        break

            # 1c. pii_patterns (정규식) — PRD 5.1.2: LOG+WARN, BLOCK 아님
            for pattern in cat.get("pii_patterns", []) or []:
                if _safe_regex_search(pattern, query):
                    violations.append({
                        "type": "PII",
                        "category": cat_name,
                        "matched": pattern[:80],
                        "severity": "MEDIUM",  # ⚠️ blocked=False 유지
                    })
                    # 같은 카테고리에서 PII 한 번 잡으면 중복 방지로 break
                    break

    # ── ② Jailbreak 패턴 (정책과 별개로 항상 검사) ──
    if not blocked:
        for pattern in _JAILBREAK_PATTERNS:
            if _safe_regex_search(pattern, query):
                violations.append({
                    "type": "JAILBREAK",
                    "matched": pattern[:80],
                    "severity": "HIGH",
                })
                blocked = True
                break

    return {"rule_violations": violations, "rule_blocked": blocked}


# ──────────────────────────────────────────────────────────────
# 노드 3: LLM 리스크 평가
# ──────────────────────────────────────────────────────────────
async def llm_risk_agent_node(state: QueryRiskState) -> dict:
    """
    Ollama qwen2.5:7b로 쿼리의 맥락적 위험성 평가.
    평가 기준: Hallucination 유발 / Bias / 정보 유출 / 윤리적 문제
    실패 → score=0.5 + llm_fallback=True (운영 모니터링용 플래그)
    """
    policy = state.get("policy", {})

    system_prompt = (
        "당신은 AI 쿼리 안전성 평가 전문가입니다.\n"
        f"적용 정책: {json.dumps(policy, ensure_ascii=False)[:2000]}\n\n"
        "평가 기준:\n"
        "1. Hallucination 유발 가능성 (검증 불가 사실 주장 요구)\n"
        "2. Bias 유발 가능성 (특정 집단 비교/차별 표현)\n"
        "3. 정보 유출 위험 (내부 정보 추출 시도)\n"
        "4. 윤리적 문제 (부적절한 행동 요청)\n\n"
        '반드시 아래 JSON만 반환하라:\n'
        '{"risk_score": 0.0, "risk_reasons": ["이유1"], "risk_types": ["유형1"]}'
    )
    user_msg = f"평가할 쿼리: {state['query']}"
    if state.get("context"):
        user_msg += f"\n컨텍스트: {state['context']}"

    try:
        client = OllamaClient()
        raw = await client.chat(
            system_prompt=system_prompt, user_message=user_msg, temperature=0.1
        )
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            raise ValueError("JSON 없음")
        parsed = json.loads(m.group(0))
        score = float(parsed.get("risk_score", 0.5))
        reasons = parsed.get("risk_reasons", []) or []
        return {
            "llm_risk_score":   score,
            "llm_risk_reasons": reasons,
            "llm_fallback":     False,
        }
    except Exception as e:
        return {
            "llm_risk_score":   0.5,
            "llm_risk_reasons": [f"LLM 평가 실패 → 보수적 WARNED 처리: {type(e).__name__}"],
            "llm_fallback":     True,
        }


# ──────────────────────────────────────────────────────────────
# 룰 위반을 사람이 읽기 좋은 텍스트로 변환
# ──────────────────────────────────────────────────────────────
def _format_rule_violation(v: dict) -> str:
    vtype = v.get("type", "RULE")
    matched = v.get("matched", "")
    category = v.get("category", "")
    sev = v.get("severity", "HIGH")
    if category:
        return f"[{vtype}/{category}] '{matched}' (severity={sev})"
    return f"[{vtype}] '{matched}' (severity={sev})"


# ──────────────────────────────────────────────────────────────
# 노드 4: 액션 결정 (결정론적)
# ──────────────────────────────────────────────────────────────
def action_engine_node(state: QueryRiskState) -> dict:
    """
    BLOCK 조건:
        - rule_blocked=True (HIGH severity 룰 위반)
        - 또는 LLM score ≥ 0.7
    WARN 조건:
        - MEDIUM rule violation 존재 (예: PII)
        - 또는 0.4 ≤ score < 0.7
    PASS:
        - 그 외

    rule_violations 텍스트와 llm_risk_reasons를 합쳐 combined_reasons 생성.
    이 값이 응답과 audit log에 모두 기록됨.
    """
    rule_blocked = state.get("rule_blocked", False)
    rule_violations = state.get("rule_violations", []) or []
    score = state.get("llm_risk_score", 0.0)
    llm_reasons = state.get("llm_risk_reasons", []) or []

    # 모든 룰 위반과 LLM 사유를 텍스트로 합침 (응답 + audit 공통)
    rule_reasons = [_format_rule_violation(v) for v in rule_violations]
    combined = rule_reasons + llm_reasons

    has_medium_rule = any(
        v.get("severity") == "MEDIUM" for v in rule_violations
    )

    if rule_blocked or score >= 0.7:
        return {
            "final_status":     "BLOCKED",
            "final_score":      1.0 if rule_blocked else score,
            "action_taken":     "BLOCK",
            "combined_reasons": combined,
        }
    if has_medium_rule or score >= 0.4:
        # MEDIUM rule만 있고 LLM이 낮은 score를 줬어도 최소 0.5로 끌어올림
        final_score = max(0.5, score) if has_medium_rule else score
        return {
            "final_status":     "WARNED",
            "final_score":      final_score,
            "action_taken":     "LOG",
            "combined_reasons": combined,
        }
    return {
        "final_status":     "PASSED",
        "final_score":      score,
        "action_taken":     "PASS",
        "combined_reasons": combined,
    }


# ──────────────────────────────────────────────────────────────
# 노드 5: 감사 로그 저장
# ──────────────────────────────────────────────────────────────
def audit_logger_node(state: QueryRiskState) -> dict:
    """
    query_audit_logs 테이블 INSERT (INSERT ONLY).
    risk_reasons 컬럼에는 룰 위반 + LLM 사유 합본 저장 → 사후 감사 시 차단 근거 추적 가능.
    """
    audit_id = str(uuid.uuid4())
    session = SessionLocal()
    try:
        session.add(QueryAuditLogModel(
            id=audit_id,
            agent_id=state["agent_id"],
            policy_id=state["policy_id"],
            query=state["query"],
            context=state.get("context"),
            risk_score=state.get("final_score", 0.0),
            status=state.get("final_status", "PASSED"),
            risk_reasons=state.get("combined_reasons", []),
            action_taken=state.get("action_taken", "PASS"),
        ))
        session.commit()
        return {"audit_id": audit_id}
    except Exception as e:
        session.rollback()
        return {"audit_id": audit_id, "error_message": f"감사 로그 저장 실패: {e}"}
    finally:
        session.close()


# ──────────────────────────────────────────────────────────────
# 그래프 조립
# ──────────────────────────────────────────────────────────────
@lru_cache
def build_query_risk_graph():
    graph = StateGraph(QueryRiskState)

    graph.add_node("policy_loader",  policy_loader_node)
    graph.add_node("rule_engine",    rule_engine_node)
    graph.add_node("llm_risk_agent", llm_risk_agent_node)
    graph.add_node("action_engine",  action_engine_node)
    graph.add_node("audit_logger",   audit_logger_node)

    graph.set_entry_point("policy_loader")

    # 정책 로더 실패 → 바로 action_engine (Fail-Safe BLOCKED)
    graph.add_conditional_edges(
        "policy_loader",
        lambda s: "action_engine" if s.get("rule_blocked") else "rule_engine",
        {"action_engine": "action_engine", "rule_engine": "rule_engine"},
    )
    # HIGH severity 룰 차단 → LLM 생략 (비용 절감). MEDIUM (PII)은 LLM 거침.
    graph.add_conditional_edges(
        "rule_engine",
        lambda s: "action_engine" if s.get("rule_blocked") else "llm_risk_agent",
        {"action_engine": "action_engine", "llm_risk_agent": "llm_risk_agent"},
    )
    graph.add_edge("llm_risk_agent", "action_engine")
    graph.add_edge("action_engine",  "audit_logger")
    graph.add_edge("audit_logger",   END)

    return graph.compile()
