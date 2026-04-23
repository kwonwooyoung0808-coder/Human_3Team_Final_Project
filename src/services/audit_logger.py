import json
from sqlalchemy.orm import Session

from src.database.models import AuditLogModel, WorkflowRunModel
from src.schemas.workflow import EvaluateRequest

class AuditLogger:
    def __init__(self, db: Session):
        self.db = db

    # 기존 evaluate.py 와의 호환성을 위한 범용 log 메서드
    def log(self, run_id: str, event_type: str, entity_type: str, reason: str = "", context: dict = None) -> None:
        context_data = json.dumps(context) if isinstance(context, dict) else str(context or {})
        self.db.add(
            AuditLogModel(
                run_id=run_id,
                event_type=event_type,
                entity_type=entity_type,
                reason=reason,
                context_json=context_data,
            )
        )
        self.db.commit()

    # 우리가 새로 만들었던 구체적인 로깅 메서드들 (유지)
    def log_policy_evaluation(self, run_id: str, has_violation: bool, context: dict) -> None:
        context_data = json.dumps(context) if isinstance(context, dict) else str(context)
        self.db.add(
            AuditLogModel(
                run_id=run_id,
                event_type="policy_evaluation",
                entity_type="run",
                reason="Violation detected." if has_violation else "No violation detected.",
                context_json=context_data,
            )
        )
        self.db.commit()

    def log_run_summary(self, request: EvaluateRequest, final_output: str, final_action: str) -> None:
        context_data = json.dumps(request.context) if isinstance(request.context, dict) else str(request.context)
        self.db.add(
            WorkflowRunModel(
                run_id=request.run_id,
                input=request.input,
                output=final_output,
                final_action=final_action,
                has_violation=(final_action == "BLOCK"),
                workflow_name="governance_workflow",
                context_json=context_data,
            )
        )
        self.db.commit()