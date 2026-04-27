import json
import re
from typing import Tuple, Dict, Any, Optional

from src.schemas.policy import Policy, PolicyEvaluationResult


class PolicyEngine:
    """
    YAML로 정의된 거버넌스 정책(Policy)을 로드하여 LLM의 응답(Response)을 평가하는 핵심 엔진.

    [성능 최적화 설계]
    1. 고속 문자열 매칭(exact_terms)을 정규식보다 무조건 먼저 처리합니다.
    2. Short-circuit: 첫 번째 위반이 발견되면 후속 Rule 검사를 즉시 중단합니다.
    """

    def evaluate_policy(
        self,
        policy: Policy,
        response: str,
        context: dict,
        retrieved_context: list[str] | None,
    ) -> PolicyEvaluationResult:

        # Preconditions 처리 (Groundedness 등 컨텍스트 의존 정책 대응)
        if policy.preconditions and policy.preconditions.requires_retrieved_context:
            precondition_result = self._handle_preconditions(policy, retrieved_context)
            if precondition_result is not None:
                return precondition_result

        # 초기 상태 설정
        triggered = False
        judge_required = (policy.judge_required == "always")
        evidence_spans: list[dict] = []
        reason = "No violation detected."
        recommended_action = policy.action.type or policy.action.default_type or "LOG"

        # Rule 평가 루프 (Short-circuit 적용)
        for rule in policy.rules:
            if rule.condition == "contains_categorized_forbidden_terms":
                is_violated, span, rule_reason = self._evaluate_content_safety(rule, response, policy.id)

                if is_violated:
                    evidence_spans.append(span)
                    reason = rule_reason
                    triggered = True

                    # 룰 위반 시 후속 행동(Action) 분기
                    if rule.on_rule_failure == "judge_fallback" or policy.judge_required == "rule_triggered":
                        judge_required = True
                    else:
                        judge_required = False
                    break # 첫 위반 탐지 시 불필요한 루프 중단 (최적화)

            elif rule.condition == "format_validation":
                is_violated, span, rule_reason = self._evaluate_format_compliance(rule, response, policy.id)

                if is_violated:
                    evidence_spans.append(span)
                    reason = rule_reason
                    triggered = True

                    if rule.on_rule_failure == "block_immediately":
                        judge_required = False
                    elif rule.on_rule_failure == "judge_fallback" or policy.judge_required == "rule_triggered":
                        judge_required = True
                    break

        # policy 레벨 judge_required 최종 조정
        if policy.judge_required == "always":
            judge_required = True
        elif policy.judge_required == "never":
            judge_required = False

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

    def _handle_preconditions(
        self,
        policy: Policy,
        retrieved_context: list[str] | None
    ) -> Optional[PolicyEvaluationResult]:
        """
        Preconditions 처리 전용 메서드.
        컨텍스트가 비어있는 경우 정책에 정의된 behavior(SKIP, WARN, FAIL)에 따라 라우팅합니다.
        """
        if not policy.preconditions:
            return None

        # 컨텍스트가 아예 없거나, ["", "   "] 처럼 공백만 존재하는 무의미한 배열인 경우 감지
        context_missing = retrieved_context is None or len(retrieved_context) == 0
        context_empty = retrieved_context and all(
            not c or len(str(c).strip()) == 0 for c in retrieved_context
        )

        if context_missing or context_empty:
            behavior = policy.preconditions.no_context_behavior or "SKIP"

            if behavior == "SKIP":
                return self._create_skipped_result(
                    policy,
                    reason_msg="no_context_or_empty",
                    skip_reason="retrieved_context is missing or empty"
                )
            elif behavior == "WARN":
                # [버그 픽스] WARN 모드일 때는 감사 로그에 남아야 하므로 triggered=True 로 설정
                return PolicyEvaluationResult(
                    policy_id=policy.id,
                    policy_name=policy.name,
                    triggered=True,
                    judge_required=False,
                    recommended_action="LOG",
                    severity=policy.severity,
                    reason="No meaningful retrieved_context provided for groundedness check (WARN mode)",
                    skip_reason="no_meaningful_context"
                )
            elif behavior == "FAIL":
                # 컨텍스트 없이 답변을 시도한 것 자체를 위험으로 간주하여 즉시 차단
                return PolicyEvaluationResult(
                    policy_id=policy.id,
                    policy_name=policy.name,
                    triggered=True,
                    judge_required=False,
                    recommended_action="BLOCK",
                    severity=policy.severity,
                    reason="Retrieved context required but missing or empty (FAIL mode)",
                    skip_reason="context_required_but_missing"
                )

        return None  # preconditions 통과 → 정상 평가 진행

    def _create_skipped_result(
        self,
        policy: Policy,
        reason_msg: str,
        skip_reason: Optional[str] = None
    ) -> PolicyEvaluationResult:
        """사전 조건 미충족으로 평가를 건너뛰는 경우 (정상 통과와 구분하기 위해 skip_reason 명시)"""
        result = PolicyEvaluationResult(
            policy_id=policy.id,
            policy_name=policy.name,
            triggered=False,
            judge_required=False,
            recommended_action=policy.action.type or policy.action.default_type or "LOG",
            severity=policy.severity,
            reason=f"Preconditions not met, skipped evaluation. ({reason_msg})"
        )
        if skip_reason:
            result.skip_reason = skip_reason
        return result

    def _evaluate_content_safety(self, rule, response: str, policy_id: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """안전성 룰 검사 (Exact Terms 1차 검사 -> Regex 2차 검사 구조)"""
        params = rule.parameters
        case_insensitive = params.get("case_insensitive", True)
        categories = params.get("categories", {})

        check_text = response.lower() if case_insensitive else response

        # 1차 검사: Exact Terms (고속 문자열 in 연산자 - 리소스 소모 최소화)
        for cat_name, cat_data in categories.items():
            if not cat_data.get("enabled", False):
                continue
            for term in cat_data.get("exact_terms", []):
                search_term = term.lower() if case_insensitive else term
                if search_term in check_text:
                    start = check_text.find(search_term)
                    span = {
                        "text": response[start:start + len(term)],
                        "start_char": start,
                        "end_char": start + len(term),
                        "source": "rule",
                        "condition": rule.condition,
                        "policy_id": policy_id,
                        "human_reason": f"[{cat_name}] Forbidden exact term detected: {term}"
                    }
                    return True, span, span["human_reason"]

        # 2차 검사: Regex Patterns (1차를 통과한 경우에만 수행되는 복잡한 패턴 탐지)
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
        """출력 포맷(JSON, Markdown 등) 준수 여부 검증"""
        params = rule.parameters
        required = params.get("required_formats", [])
        forbidden = params.get("forbidden_formats", [])

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

            if not passed_at_least_one:
                return self._create_format_span(response, rule, policy_id, f"Required format missing: {', '.join(errors)}")

        if "PLAIN_TEXT_WITH_MARKDOWN" in forbidden:
            if re.search(r"[*#`]", response):
                return self._create_format_span(response, rule, policy_id, "Forbidden markdown characters found.")

        return False, None, ""

    def _create_format_span(self, response: str, rule, policy_id: str, reason: str) -> Tuple[bool, Dict[str, Any], str]:
        """포맷 위반 증거 객체 생성 유틸리티"""
        span = {
            "text": response[:120],
            "start_char": 0,
            "end_char": min(len(response), 120), # 전체 문자열을 넣기엔 너무 길 수 있으므로 샘플링
            "source": "rule",
            "condition": rule.condition,
            "policy_id": policy_id,
            "human_reason": reason
        }
        return True, span, reason
