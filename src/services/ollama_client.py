from __future__ import annotations

import httpx

from src.core.config import get_settings


class OllamaClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.ollama_url.rstrip("/")
        self.model = settings.ollama_model
        self.temperature = settings.ollama_temperature

    async def generate(
        self,
        prompt: str,
        temperature: float | None = None,
    ) -> str:
        """
        단일 프롬프트 방식 — 기존 Feature 1/2/JudgeEngine 호환성 유지.
        temperature 명시 시 Self-Consistency Check 등에서 변형된 출력 유도 가능.
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else self.temperature
            },
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
        return data.get("response", "")

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float | None = None,
    ) -> str:
        """
        system/user 역할 분리 방식 — Feature 3 전용.
        /api/chat 엔드포인트 사용으로 프롬프트 인젝션 경계를 명확히 구분.
        temperature 오버라이드 가능 (Step 2 형식 변환 시 0.0 고정).
        """
        messages = []
        if system_prompt:  # 빈 문자열이면 system 메시지 생략
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": self.model,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else self.temperature
            },
            "messages": messages,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        return data.get("message", {}).get("content", "")
