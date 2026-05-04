"""
통합 테스트 공용 fixtures.

- client: 매 테스트마다 schema drop/create + lifespan 트리거 (seed 정책 자동 등록)
- mock_ollama: OllamaClient.generate / .chat을 가짜 응답으로 monkeypatch
- seeded_agent: CONTENT_001 정책에 연결된 테스트용 agent 생성
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """
    매 테스트마다 깨끗한 schema + 정책 seed 보장.
    `with TestClient(app)` 패턴으로 lifespan을 실행해 init_db()가 호출됨.
    """
    # 지연 import: tests/conftest.py가 DATABASE_URL을 redirect한 후에 src.* 로드
    from src.database import models  # noqa: F401 — 모델 등록
    from src.database.connection import Base, engine
    from src.main import app

    # 이전 테스트의 잔여 데이터 제거
    Base.metadata.drop_all(bind=engine)

    # TestClient의 with 블록이 lifespan 실행 → init_db() → create_all + seed
    with TestClient(app) as c:
        yield c

    # 종료 후 정리
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_ollama(monkeypatch):
    """
    OllamaClient의 두 메서드를 가짜 응답으로 교체.
    실제 Ollama 서버 없이도 LLM 의존 노드가 deterministic하게 동작.

    기본값:
    - generate() → JudgeEngine이 기대하는 PASS verdict JSON
    - chat() → query_risk_workflow가 기대하는 낮은 risk_score JSON

    필요 시 테스트 내에서 monkeypatch로 추가 override 가능.
    """
    canned_generate = (
        '{"verdict": "PASS", "confidence": 0.95, '
        '"reason": "mocked - 정상 응답", "evidence_text": ""}'
    )
    canned_chat = (
        '{"risk_score": 0.1, "risk_reasons": [], "risk_types": []}'
    )

    async def fake_generate(self, prompt: str, temperature=None) -> str:
        return canned_generate

    async def fake_chat(self, system_prompt, user_message, temperature=None) -> str:
        return canned_chat

    from src.services import ollama_client
    monkeypatch.setattr(ollama_client.OllamaClient, "generate", fake_generate)
    monkeypatch.setattr(ollama_client.OllamaClient, "chat", fake_chat)

    return {"generate": canned_generate, "chat": canned_chat}


@pytest.fixture
def seeded_agent(client):
    """CONTENT_001 정책에 연결된 테스트용 agent 1개 생성."""
    response = client.post(
        "/api/agents",
        json={
            "id": "agent-test-001",
            "name": "Test Agent",
            "policy_id": "CONTENT_001",
            "status": "ACTIVE",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
