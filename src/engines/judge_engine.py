from pathlib import Path

from src.core.config import get_settings
from src.schemas.judge import JudgeResult
from src.schemas.policy import Policy


class JudgeEngine:
    def __init__(self, prompt_dir: str | None = None):
        self.prompt_dir = Path(prompt_dir or get_settings().prompt_dir)

    def _read_prompt(self, name: str) -> str:
        path = self.prompt_dir / name
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def judge(self, policy: Policy, response: str, retrieved_context: list[str] | None) -> JudgeResult:
        if policy.id == "GROUND_001":
            if not retrieved_context:
                return JudgeResult(
                    verdict="FAIL",
                    confidence=0.65,
                    reason="No retrieved context was provided.",
                    evidence_text=response[:120],
                )
            normalized = response.lower()
            for context in retrieved_context:
                if context and context.lower()[:30] in normalized:
                    return JudgeResult(
                        verdict="PASS",
                        confidence=0.85,
                        reason="The response is supported by the provided context.",
                        evidence_text=context[:120],
                    )
            return JudgeResult(
                verdict="FAIL",
                confidence=0.72,
                reason="The response is not sufficiently grounded in the provided context.",
                evidence_text=response[:120],
            )

        return JudgeResult(
            verdict="PASS",
            confidence=0.7,
            reason="No additional judge-only violation was detected.",
            evidence_text=None,
        )

