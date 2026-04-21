from src.schemas.action import ActionResult
from src.schemas.violation import Violation

FALLBACK_BLOCK_MESSAGE = "The response was blocked because it violated a policy."


class ActionEngine:
    def decide(self, run_id: str, response: str, violations: list[Violation]) -> ActionResult:
        should_block = any(violation.recommended_action == "BLOCK" for violation in violations)
        if should_block:
            return ActionResult(
                run_id=run_id,
                action_type="BLOCK",
                message=FALLBACK_BLOCK_MESSAGE,
                delivered_response=FALLBACK_BLOCK_MESSAGE,
            )
        return ActionResult(
            run_id=run_id,
            action_type="LOG",
            message="Response was logged.",
            delivered_response=response,
        )

