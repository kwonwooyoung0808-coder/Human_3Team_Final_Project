import json

from sqlalchemy.orm import Session

from src.database.models import AuditLogModel
from src.schemas.audit import AuditLogCreate


class AuditLogger:
    def __init__(self, db: Session):
        self.db = db

    def log(self, event: AuditLogCreate) -> None:
        self.db.add(
            AuditLogModel(
                run_id=event.run_id,
                event_type=event.event_type,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                reason=event.reason,
                context_json=json.dumps(event.context_json),
            )
        )
        self.db.flush()

