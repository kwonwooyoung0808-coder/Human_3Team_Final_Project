from __future__ import annotations

import httpx

from src.core.config import get_settings


class SovereignAIClient:
    """
    Sovereign AI 호출 클라이언트 — 검사 대상 회사 AI 에 응답을 요청.

    데모 환경에서는 Governance LLM 과 같은 Ollama 인스턴스를 공유하지만,
    환경변수 (SOVEREIGN_AI_*) 가 분리되어 있어 운영 시 회사 자체 LLM URL 로
    교체 가능. Agent 단위 매핑은 향후 AgentModel 에 컬럼으로 추가될 예정.

    호출 측면에서는 Ollama API 와 동일한 /api/generate 형식을 따름.
    회사별 LLM 이 OpenAI 호환 / 자체 API 인 경우 해당 어댑터를 별도로 작성.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.sovereign_ai_url.rstrip("/")
        self.model = settings.sovereign_ai_model
        self.temperature = settings.sovereign_ai_temperature

    async def generate(
        self,
        query: str,
        context: str | None = None,
    ) -> str:
        """사원 질의 → 회사 AI 응답."""
        prompt = f"질문: {query}"
        if context:
            prompt = f"컨텍스트: {context}\n\n{prompt}"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
        return data.get("response", "")
