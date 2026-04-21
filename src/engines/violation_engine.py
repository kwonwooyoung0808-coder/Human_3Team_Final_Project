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
        if not result.triggered and not (judge_result and judge_result.verdict == "FAIL"):
            return None

        source = "rule" if result.triggered else "judge"
        reason = result.reason if result.triggered else judge_result.reason
        raw_evidence = result.evidence_spans[0] if result.evidence_spans else None

        if raw_evidence:
            evidence_span = EvidenceSpan(**raw_evidence, confidence=1.0)
            risk_score = 0.98 if policy.action.type == "BLOCK" else 0.75
        else:
            text = (judge_result.evidence_text if judge_result else None) or response[:120]
            evidence_span = EvidenceSpan(
                text=text,
                start_char=0 if text == response[:120] else None,
                end_char=len(text) if text == response[:120] else None,
                source="judge" if judge_result else "fallback",
                condition=None,
                policy_id=policy.id,
                confidence=judge_result.confidence if judge_result else 0.5,
                human_reason=reason,
            )
            risk_score = judge_result.confidence if judge_result else 0.5

        return Violation(
            id=f"vio_{uuid4().hex[:12]}",
            run_id=run_id,
            policy_id=policy.id,
            policy_name=policy.name,
            reason=reason,
            source=source,
            recommended_action=policy.action.type,
            risk_score=min(max(risk_score, 0.0), 1.0),
            evidence_span=evidence_span,
            judge_verdict=judge_result.verdict if judge_result else None,
            judge_confidence=judge_result.confidence if judge_result else None,
        )

