import json
from sqlalchemy.orm import Session

from src.database.models import AuditLogModel, WorkflowRunModel
from src.schemas.workflow import EvaluateRequest

class AuditLogger:
    def __init__(self, db: Session):
        self.db = db

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