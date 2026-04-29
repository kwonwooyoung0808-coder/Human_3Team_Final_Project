import os
from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "Policy-Aware Agent Governance Engine")
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://safeagent_app:safeagent_password@localhost:5432/safeagent"
    )
    policy_dir: str = os.getenv("POLICY_DIR", "src/policies")
    prompt_dir: str = os.getenv("PROMPT_DIR", "src/prompts")
    workflow_name: str = os.getenv("WORKFLOW_NAME", "governance_workflow")
    ollama_url: str = os.getenv("OLLAMA_URL", "http://ollama:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    ollama_temperature: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
