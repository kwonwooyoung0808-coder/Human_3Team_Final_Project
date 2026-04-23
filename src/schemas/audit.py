from datetime import datetime
from typing import Any
from pydantic import BaseModel

# 생성용 스키마 (기존)
class AuditLogCreate(BaseModel):
    run_id: str
    event_type: str
    entity_type: str
    entity_id: str | None = None
    reason: str
    context_json: dict | str

# 응답용 스키마 (추가)
class AuditLogResponse(BaseModel):
    id: int
    run_id: str
    event_type: str
    entity_type: str
    entity_id: str | None
    reason: str
    context: dict[str, Any]
    created_at: datetime