from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AuditLogCreate(BaseModel):
    run_id: str
    event_type: str
    entity_type: str
    entity_id: str | None = None
    reason: str
    context_json: dict[str, Any] = Field(default_factory=dict)


class AuditLogRead(BaseModel):
    id: int
    run_id: str
    event_type: str
    entity_type: str
    entity_id: str | None = None
    reason: str
    context_json: dict[str, Any]
    created_at: datetime

