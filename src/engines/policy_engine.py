import json
import re
from typing import Tuple, Dict, Any, Optional

from src.schemas.policy import Policy, PolicyEvaluationResult


class PolicyEngine:
    """
    YAML로 정의된 거버넌스 정책(Policy)을 로드하여 LLM의 응답(Response)을 평가하는 핵심 엔진.
    고속 문자열 매칭과 정규식을 우선 처리하며, 필요한 경우에만 Judge Engine으로 판단을 위임.
    """

    def evaluate_policy(
        self,
        policy: Policy,
        response: str,
        context: dict,
        retrieved_context: list[str] | None,
    ) -> PolicyEvaluationResult:

        # B4 해소 : Preconditions (사전 조건) 검사
        # Groundedness 정책 등 RAG 검색 데이터가 필수인 경우, 데이터 부재 시 예외 처리(SKIP)
        if policy.preconditions and policy.preconditions.requires_retrieved_context:
            if retrieved_context is None and policy.preconditions.no_context_behavior == "SKIP":
                return self._create_skipped_result(policy, "retrieved_context is None")
            if not retrieved_context and policy.preconditions.empty_context_behavior == "SKIP":
                return self._create_skipped_result(policy, "retrieved_context is empty []")

        # A-7 반영 : 초기 상태 설정
        # judge_required 필드가 명시적인 "always"일 경우 초기값을 True로 셋팅
        triggered = False
        judge_required = (policy.judge_required == "always")
        evidence_spans: list[dict] = []
        reason = "No violation detected."

        # 액션 타입 결정: Rule 기반(type)이 없으면 Judge 기반(default_type) 사용, 둘 다 없으면 LOG
        recommended_action = policy.action.type or policy.action.default_type or "LOG"

        for rule in policy.rules:
            # [Content Policy] 카테고리 기반 금지어 및 정규식 패턴 탐지
            if rule.condition == "contains_categorized_forbidden_terms":
                is_violated, span, rule_reason = self._evaluate_content_safety(rule, response, policy.id)
                if is_violated:
                    evidence_spans.append(span)
                    reason = rule_reason
                    triggered = True
                    # B-1 연관: Rule 실패 시 동작 결정
                    if rule.on_rule_failure == "judge_fallback":
                        judge_required = True
                    else:
                        judge_required = False
                    break # 심각도 높은 차단이 확인되면 후속 Rule 검사 생략 (최적화)

            # [Compliance Policy] 포맷 준수 여부 검증
            elif rule.condition == "format_validation":
                is_violated, span, rule_reason = self._evaluate_format_compliance(rule, response, policy.id)
                if is_violated:
                    evidence_spans.append(span)
                    reason = rule_reason
                    triggered = True
                    if rule.on_rule_failure == "block_immediately":
                        judge_required = False
                    elif rule.on_rule_failure == "judge_fallback":
                        judge_required = True
                    break

        # 최종 평가 결과 객체 조립 후 반환 (Violation Builder로 전달됨)
        return PolicyEvaluationResult(
            policy_id=policy.id,
            policy_name=policy.name,
            triggered=triggered,
            judge_required=judge_required,
            recommended_action=recommended_action,
            severity=policy.severity,
            evidence_spans=evidence_spans,
            reason=reason,
        )

    def _create_skipped_result(self, policy: Policy, reason_msg: str) -> PolicyEvaluationResult:
        """사전 조건(Preconditions)을 만족하지 못해 평가를 건너뛰는 경우의 결과 객체 반환"""
        return PolicyEvaluationResult(
            policy_id=policy.id,
            policy_name=policy.name,
            triggered=False,
            judge_required=False,
            recommended_action=policy.action.type or policy.action.default_type or "LOG",
            severity=policy.severity,
            reason=f"Preconditions not met, skipped evaluation. ({reason_msg})"
        )

    def _evaluate_content_safety(self, rule, response: str, policy_id: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        [match_strategy 실행 순서]
        1. Exact Terms 고속 문자열 탐색 (in 연산자): CPU 부하 최소화를 위해 1차 필터링
        2. Phrase & PII 정규식 패턴 탐색 (re 모듈): 문맥 기반 위험어 및 개인정보 추출
        """
        params = rule.parameters
        case_insensitive = params.get("case_insensitive", True)
        categories = params.get("categories", {})

        # 대소문자 무시 조건일 경우 사전에 응답 텍스트를 소문자로 캐싱 처리
        check_text = response.lower() if case_insensitive else response

        # 1차 검사: Exact Terms (가장 빠름)
        for cat_name, cat_data in categories.items():
            if not cat_data.get("enabled", False):
                continue

            for term in cat_data.get("exact_terms", []):
                search_term = term.lower() if case_insensitive else term
                if search_term in check_text:
                    start = check_text.find(search_term)
                    span = {
                        "text": response[start:start+len(term)],
                        "start_char": start,
                        "end_char": start+len(term),
                        "source": "rule",
                        "condition": rule.condition,
                        "policy_id": policy_id,
                        "human_reason": f"[{cat_name}] Forbidden exact term detected: {term}"
                    }
                    return True, span, span["human_reason"]

        # 2차 검사: Regex Patterns (비교적 무거움)
        for cat_name, cat_data in categories.items():
            if not cat_data.get("enabled", False):
                continue

            patterns = cat_data.get("phrase_patterns", []) + cat_data.get("pii_patterns", [])
            flags = re.IGNORECASE if case_insensitive else 0

            for pattern in patterns:
                match = re.search(pattern, response, flags)
                if match:
                    span = {
                        "text": match.group(0),
                        "start_char": match.start(),
                        "end_char": match.end(),
                        "source": "rule",
                        "condition": rule.condition,
                        "policy_id": policy_id,
                        "human_reason": f"[{cat_name}] Forbidden pattern detected: {pattern}"
                    }
                    return True, span, span["human_reason"]

        return False, None, ""

    def _evaluate_format_compliance(self, rule, response: str, policy_id: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        params = rule.parameters
        required = params.get("required_formats", [])
        forbidden = params.get("forbidden_formats", [])

        # 필수 포맷 검사: 하나라도 만족하면 통과하는 'OR' 로직으로 변경
        if required:
            passed_at_least_one = False
            errors = []

            if "JSON" in required:
                try:
                    json.loads(response)
                    passed_at_least_one = True
                except json.JSONDecodeError:
                    errors.append("Not a valid JSON.")

            if "MARKDOWN_TABLE" in required and not passed_at_least_one:
                table_rows = [line for line in response.split('\n') if line.strip().startswith('|')]
                if len(table_rows) >= 2:
                    passed_at_least_one = True
                else:
                    errors.append("Not a valid MARKDOWN_TABLE.")

            # 모든 필수 형식 검사 후 하나도 통과 못 했을 때만 위반 처리
            if not passed_at_least_one:
                return self._create_format_span(response, rule, policy_id, f"Required format missing: {', '.join(errors)}")

        # 금지 포맷 검사: 하나라도 걸리면 즉시 위반
        if "PLAIN_TEXT_WITH_MARKDOWN" in forbidden:
            if re.search(r"[*#`]", response):
                return self._create_format_span(response, rule, policy_id, "Forbidden markdown characters found.")

        return False, None, ""

    """포맷 위반 발생 시 Evidence Span 생성 유틸리티"""
    def _create_format_span(self, response: str, rule, policy_id: str, reason: str) -> Tuple[bool, Dict[str, Any], str]:
        span = {
            "text": response[:120],
            "start_char": 0,
            "end_char": min(len(response), 120),
            "source": "rule",
            "condition": rule.condition,
            "policy_id": policy_id,
            "human_reason": reason
        }
        return True, span, reason
