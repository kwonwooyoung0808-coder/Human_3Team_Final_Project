import os
from functools import lru_cache

from pydantic import BaseModel
from dotenv import load_dotenv


load_dotenv()


# ──────────────────────────────────────────────────────────────
# 두 종류의 LLM 분리:
# 1) Governance LLM — 정책 평가/Judge 용도. SafeAgent 내부 도구.
# 2) Sovereign AI   — 검사 대상 회사 AI. 데모에서는 같은 Ollama 공유,
#                     운영 시 회사별 LLM URL 로 교체 (Agent 단위 매핑은 향후).
#
# 하위 호환: OLLAMA_* 환경변수가 있으면 두 LLM 모두 거기서 읽어옴.
# ──────────────────────────────────────────────────────────────
class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "SafeAgent_Manager")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://safeagent_app:safeagent_password@localhost:5432/safeagent",
    )
    policy_dir: str = os.getenv("POLICY_DIR", "src/policies")
    prompt_dir: str = os.getenv("PROMPT_DIR", "src/prompts")
    workflow_name: str = os.getenv("WORKFLOW_NAME", "governance_workflow")

    # ── 정책 분리 전략 (Stage A) ──
    # F1 (질의 검사) 는 모든 사용자에게 동일한 보편 안전 정책만 적용
    # F2 (응답 검증) 는 시스템 정책 + agent 의 부서별 정책을 결합
    system_input_policy_id: str = os.getenv("SYSTEM_INPUT_POLICY_ID", "CONTENT_001")

    # ── F2 Self-Consistency Check (PRD §5.2.2) ──
    # True  : Judge LLM 을 temp=0.0 / temp=0.7 로 2회 병렬 호출 후 verdict 비교 (정확도 ↑, latency ↑)
    # False : 단일 호출만 (CPU 환경 권장 — 8B 모델 Self-Consistency 는 timeout 위험)
    enable_self_consistency: bool = os.getenv("ENABLE_SELF_CONSISTENCY", "false").lower() == "true"

    # ── Governance LLM (정책 평가/Judge 용 내부 도구) ──
    governance_llm_url: str = os.getenv(
        "GOVERNANCE_LLM_URL", os.getenv("OLLAMA_URL", "http://localhost:11434")
    )
    governance_llm_model: str = os.getenv(
        "GOVERNANCE_LLM_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    )
    governance_llm_temperature: float = float(
        os.getenv("GOVERNANCE_LLM_TEMPERATURE", os.getenv("OLLAMA_TEMPERATURE", "0.1"))
    )

    # ── Sovereign AI (검사 대상 회사 AI) ──
    sovereign_ai_url: str = os.getenv(
        "SOVEREIGN_AI_URL", os.getenv("OLLAMA_URL", "http://localhost:11434")
    )
    sovereign_ai_model: str = os.getenv(
        "SOVEREIGN_AI_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    )
    sovereign_ai_temperature: float = float(
        os.getenv("SOVEREIGN_AI_TEMPERATURE", "0.7")  # 응답 생성은 다양성 허용
    )

    # ── Safe Response Generator (PRD §8 — 차단/거부 시 대체 응답 생성) ──
    # 빠른 응답을 위해 가벼운 모델 권장. 미설정 시 governance LLM 재사용.
    safe_response_llm_url: str = os.getenv(
        "SAFE_RESPONSE_LLM_URL",
        os.getenv("GOVERNANCE_LLM_URL", os.getenv("OLLAMA_URL", "http://localhost:11434")),
    )
    safe_response_llm_model: str = os.getenv(
        "SAFE_RESPONSE_LLM_MODEL",
        os.getenv("GOVERNANCE_LLM_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5:7b")),
    )
    safe_response_llm_temperature: float = float(
        os.getenv("SAFE_RESPONSE_LLM_TEMPERATURE", "0.3")
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
