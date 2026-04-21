import os
from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "Policy-Aware Agent Governance Engine")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./governance.db")
    policy_dir: str = os.getenv("POLICY_DIR", "src/policies")
    prompt_dir: str = os.getenv("PROMPT_DIR", "src/prompts")
    workflow_name: str = os.getenv("WORKFLOW_NAME", "governance_workflow")


@lru_cache
def get_settings() -> Settings:
    return Settings()

