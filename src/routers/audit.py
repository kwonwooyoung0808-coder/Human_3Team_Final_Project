import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.dependencies import get_db
from src.database.models import AuditLogModel
from src.schemas.audit import AuditLogResponse # 스키마 임포트

router = APIRouter(prefix="/api/v1", tags=["audit"])

# response_model을 지정해 주어야 Swagger에 문서화됩니다.
@router.get("/audit-logs", response_model=list[AuditLogResponse])
def list_audit_logs(
    limit: int = Query(default=10, ge=1, le=100, description="Number of audit logs to return."),
    db: Session = Depends(get_db),
):
    rows = list(db.scalars(select(AuditLogModel).order_by(AuditLogModel.created_at.desc()).limit(limit)))
    result = []
    for row in rows:
        # 안전한 JSON 파싱 처리
        try:
            parsed_context = json.loads(row.context_json) if row.context_json else {}
        except json.JSONDecodeError:
            parsed_context = {}

        result.append({
            "id": row.id,
            "run_id": row.run_id,
            "event_type": row.event_type,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "reason": row.reason,
            "context": parsed_context,
            "created_at": row.created_at,
        })
    return result
