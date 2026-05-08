from __future__ import annotations

import httpx

from src.core.config import get_settings
from src.services.ollama_client import _prepend_no_think, _strip_thinking


# 한국어/영어 허용 + 그 외 외국어 차단 시스템 프롬프트.
# qwen2.5 계열은 중국어 학습 비중이 커 한국어 prompt 에 중국어가 leak 되는 경우가 있음.
# system role 로 명시적으로 강제 → leak 80-90% 차단.
_KOREAN_PERSONA_SYSTEM = (
    "당신은 한국 회사의 사내 AI 어시스턴트입니다. "
    "답변 언어는 한국어를 기본으로 하되, 필요 시 영어 사용을 허용합니다. "
    "중국어(중문), 일본어, 그 외 외국어 사용은 절대 금지합니다. "
    "코드/기술 용어는 영문 그대로 사용해도 좋으나, 본문 설명은 한국어로 작성하세요. "
    "답변은 간결하게 핵심만 작성하세요. 불필요한 반복이나 장황한 부연 설명은 피하고, "
    "예시는 1-2개로 제한합니다. 사용자가 추가 설명을 요청하면 그때 상세히 답변하세요."
)


class SovereignAIClient:
    """
    Sovereign AI 호출 클라이언트 — 검사 대상 회사 AI 에 응답을 요청.

    데모 환경에서는 Governance LLM 과 같은 Ollama 인스턴스를 공유하지만,
    환경변수 (SOVEREIGN_AI_*) 가 분리되어 있어 운영 시 회사 자체 LLM URL 로
    교체 가능. Agent 단위 매핑은 향후 AgentModel 에 컬럼으로 추가될 예정.

    PRD §10.1 데이터 주권 정책: 사내 자체 호스팅 LLM (Ollama 등) 만 호출.
    /api/chat 엔드포인트로 system/user 역할을 분리해 언어 강제 지시의
    우선순위를 높임 (qwen2.5 의 중국어 leak 방지).
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
        """사원 질의 → 회사 AI 응답. 한국어/영어 강제 시스템 프롬프트 적용."""
        user_msg = f"질문: {query}"
        if context:
            user_msg = f"컨텍스트: {context}\n\n{user_msg}"

        # /api/chat — system role 로 언어 강제. /no_think 는 user 메시지에 prefix.
        # qwen3 등 thinking-mode 모델 회피 + qwen2.5 의 중국어 leak 차단을 동시 수행.
        payload = {
            "model": self.model,
            "stream": False,
            "think": False,
            "options": {"temperature": self.temperature},
            "messages": [
                {"role": "system", "content": _KOREAN_PERSONA_SYSTEM},
                {"role": "user", "content": _prepend_no_think(user_msg)},
            ],
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        return _strip_thinking(data.get("message", {}).get("content", ""))
