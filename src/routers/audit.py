import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.dependencies import get_db
from src.database.models import AuditLogModel

router = APIRouter(prefix="/api/v1", tags=["audit"])


@router.get("/audit-logs")
def list_audit_logs(limit: int = 100, db: Session = Depends(get_db)):
    rows = list(db.scalars(select(AuditLogModel).order_by(AuditLogModel.created_at.desc()).limit(limit)))
    return [
        {
            "id": row.id,
            "run_id": row.run_id,
            "event_type": row.event_type,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "reason": row.reason,
            "context": json.loads(row.context_json),
            "created_at": row.created_at,
        }
        for row in rows
    ]

