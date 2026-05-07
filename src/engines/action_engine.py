from src.schemas.action import ActionResult
from src.schemas.violation import Violation

DEFAULT_BLOCK_MESSAGE = "The response was blocked because it violated a safety policy."


class ActionEngine:
    def decide(self, run_id: str, response: str, violations: list[Violation] | None) -> ActionResult:
        # 1. 위반 리스트가 None인 경우 빈 리스트로 처리
        violations = violations or []
        
        # 디버깅 출력
        print(f"\n>>> [ActionEngine Input] RunID: {run_id} | Total Violations: {len(violations)}")
        for i, v in enumerate(violations):
            print(f"    [{i}] Policy: {v.policy_id} | Action: {v.recommended_action} | Score: {v.risk_score:.4f}")

        # 2. BLOCK 대상 확인 (하나라도 BLOCK이면 최종 BLOCK)
        block_violations = [v for v in violations if v.recommended_action == "BLOCK"]

        if block_violations:
            # 가장 점수가 높거나 첫 번째 위반의 fallback_message 사용
            v = block_violations[0]
            msg = v.fallback_message or DEFAULT_BLOCK_MESSAGE
            result = ActionResult(
                run_id=run_id,
                action_type="BLOCK",
                message=msg,
                delivered_response=msg,  # 사용자에게는 fallback response 반환
            )
<<<<<<< Updated upstream
        return ActionResult(
            run_id=run_id,
            action_type="LOG",
            message="Response was logged.",
            delivered_response=response,
        )

=======
            print(f"!!! [ActionEngine Result] BLOCK | Message: {msg[:30]}...")
            return result

        # 3. LOG 대상 확인 (BLOCK은 없지만 위반 사항이 있는 경우)
        if violations:
            result = ActionResult(
                run_id=run_id,
                action_type="LOG",
                message="Response was logged due to policy violations.",
                delivered_response=response,  # 원본 응답 유지
            )
            print(f"--- [ActionEngine Result] LOG | Original Response Preserved")
            return result

        # 4. 위반 없음 (PASS)
        result = ActionResult(
            run_id=run_id,
            action_type="PASS",
            message="Response passed all checks.",
            delivered_response=response,
        )
        print(f"+++ [ActionEngine Result] PASS | No Violations")
        return result
>>>>>>> Stashed changes
