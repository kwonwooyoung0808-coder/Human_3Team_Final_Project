from sqlalchemy.orm import Session
from src.database.models import QueryAuditLogModel, ResponseAuditLogModel, PolicyConversionLogModel
from src.schemas.audit import QueryAuditLogCreate, ResponseAuditLogCreate

class AuditLogger:
    def __init__(self, db: Session):
        self.db = db

    # 1. Feature 1: 질의(Query) 전용 로거
    def log_query_audit(self, log_data: QueryAuditLogCreate) -> str:
        db_log = QueryAuditLogModel(
            id=log_data.id,
            agent_id=log_data.agent_id,
            policy_id=log_data.policy_id,
            query=log_data.query,
            context=log_data.context,
            risk_score=log_data.risk_score,
            status=log_data.status,
            risk_reasons=log_data.risk_reasons,
            action_taken=log_data.action_taken
        )
        self.db.add(db_log)
        self.db.commit()
        return db_log.id

    # 2. Feature 2: 응답(Response) 전용 로거 (+ evaluate.py 하위호환)
    def log_response_audit(self, log_data: ResponseAuditLogCreate) -> str:
        db_log = ResponseAuditLogModel(
            id=log_data.id,
            query_audit_id=log_data.query_audit_id,
            agent_id=log_data.agent_id,
            policy_id=log_data.policy_id,
            query=log_data.query,
            response=log_data.response,
            compliance_score=log_data.compliance_score,
            status=log_data.status,
            violations=log_data.violations
        )
        self.db.add(db_log)
        self.db.commit()
        return db_log.id