import json

from src.schemas.policy import Policy, PolicyEvaluationResult


class PolicyEngine:
    def evaluate_policy(
        self,
        policy: Policy,
        response: str,
        context: dict,
        retrieved_context: list[str] | None,
    ) -> PolicyEvaluationResult:
        triggered = False
        judge_required = policy.type in {"judge", "hybrid"} and policy.judge.enabled
        evidence_spans: list[dict] = []
        reason = "No violation detected."

        for rule in policy.rules:
            if rule.condition == "contains_forbidden_words":
                for word in rule.parameters.get("forbidden_words", []):
                    if word.lower() in response.lower():
                        start = response.lower().find(word.lower())
                        evidence_spans.append(
                            {
                                "text": response[start : start + len(word)],
                                "start_char": start,
                                "end_char": start + len(word),
                                "source": "rule",
                                "condition": rule.condition,
                                "policy_id": policy.id,
                                "human_reason": f"Forbidden word detected: {word}",
                            }
                        )
                        triggered = True
                        judge_required = False
                        reason = f"Forbidden word detected: {word}"
                        break
            elif rule.condition == "required_format":
                expected_format = (rule.parameters.get("format") or "").upper()
                if expected_format == "JSON":
                    try:
                        json.loads(response)
                    except json.JSONDecodeError:
                        triggered = True
                        judge_required = False
                        reason = "Response does not match required JSON format."
                        evidence_spans.append(
                            {
                                "text": response[:120],
                                "start_char": 0,
                                "end_char": min(len(response), 120),
                                "source": "rule",
                                "condition": rule.condition,
                                "policy_id": policy.id,
                                "human_reason": reason,
                            }
                        )

        return PolicyEvaluationResult(
            policy_id=policy.id,
            policy_name=policy.name,
            triggered=triggered,
            judge_required=judge_required,
            recommended_action=policy.action.type,
            severity=policy.severity,
            evidence_spans=evidence_spans,
            reason=reason,
        )

