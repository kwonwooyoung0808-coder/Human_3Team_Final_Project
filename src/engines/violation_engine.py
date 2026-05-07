from uuid import uuid4

from src.schemas.judge import JudgeResult
from src.schemas.policy import Policy, PolicyEvaluationResult
from src.schemas.violation import EvidenceSpan, Violation


class ViolationEngine:
    def from_policy_result(
        self,
        run_id: str,
        policy: Policy,
        result: PolicyEvaluationResult,
        judge_result: JudgeResult | None = None,
        response: str = "",
    ) -> Violation | None:
        # 디버깅을 위한 입력 데이터 출력
        print(f"\n>>> [ViolationEngine Input] RunID: {run_id} | Policy: {policy.id} ({policy.name})")
        print(f"    Rule Triggered: {result.triggered} | Action: {result.recommended_action}")
        if judge_result:
            print(f"    Judge Result: {judge_result.verdict} | Confidence: {judge_result.confidence}")
        
        # 1. 위반 상태 확인
        is_rule_triggered = result.triggered
        is_judge_fail = judge_result is not None and judge_result.verdict == "FAIL"

        # 둘 다 위반이 아니면 아무것도 반환하지 않음
        if not is_rule_triggered and not is_judge_fail:
            return None

        # 2. 데이터 소스 및 사유 선택 (Rule 우선 원칙)
        if is_rule_triggered:
            source = "rule"
            reason = result.reason
        else:
            source = "judge"
            reason = judge_result.reason if judge_result else "LLM detection failed"

        # 3. 리스크 점수 산출 (Priority와 Confidence 중 최댓값 채택 + Clamping)
        rule_score = (policy.priority / 100.0) if is_rule_triggered else 0.0
        judge_score = judge_result.confidence if judge_result else 0.0
        risk_score = min(max(max(rule_score, judge_score), 0.0), 1.0)

        # 4. 증거(Evidence Span) 종합 및 생성
        raw_evidence = result.evidence_spans[0] if result.evidence_spans else None
        if raw_evidence:
            evidence_span = EvidenceSpan(**raw_evidence, confidence=1.0)
        else:
            text = (judge_result.evidence_text if judge_result else None) or response[:120]
            evidence_span = EvidenceSpan(
                text=text,
                start_char=0 if text == response[:120] else None,
                end_char=len(text) if text == response[:120] else None,
                source="judge" if judge_result else "fallback",
                policy_id=policy.id,
                confidence=judge_result.confidence if judge_result else 0.0,
                human_reason=reason,
            )

        # 5. 모든 결과값을 종합하여 Violation 객체 반환
        return Violation(
            id=f"vio_{uuid4().hex[:12]}",
            run_id=run_id,
            policy_id=policy.id,
            policy_name=policy.name,
            reason=reason,
            source=source,
            recommended_action=result.recommended_action,
            fallback_message=policy.action.fallback_response,
            risk_score=risk_score,
            evidence_span=evidence_span,
            judge_verdict=judge_result.verdict if judge_result else None,
            judge_confidence=judge_result.confidence if judge_result else None,
        )
