import json
from sqlalchemy.orm import Session

from src.database.models import AuditLogModel, WorkflowRunModel
from src.schemas.workflow import EvaluateRequest
from src.schemas.audit import AuditLogCreate

class AuditLogger:
    def __init__(self, db: Session):
        self.db = db

    # 1. 범용 log 메서드 (PRD 규격 완벽 반영)
    def log(self, log_data: AuditLogCreate) -> None:
        # risk_reasons가 JSON(dict) 형식이 아닐 경우 안전하게 변환
        risk_reasons_data = log_data.risk_reasons if isinstance(log_data.risk_reasons, dict) else {"raw_data": str(log_data.risk_reasons)}

        self.db.add(
            AuditLogModel(
                run_id=log_data.run_id,
                event_type=log_data.event_type,
                #과거의 entity_id 등은 지우고 PRD 규격으로 교체!
                input_text=log_data.input_text,  
                risk_score=log_data.risk_score,
                reason=log_data.reason,
                risk_reasons=risk_reasons_data,  #구 context_json
            )
        )
        self.db.commit()

    # 2. 구체적인 로깅 메서드 (이곳도 PRD 규격에 맞게 매개변수 수정)
    def log_policy_evaluation(self, run_id: str, has_violation: bool, risk_reasons: dict, input_text: str = None, risk_score: float = 0.0) -> None:
        self.db.add(
            AuditLogModel(
                run_id=run_id,
                event_type="policy_evaluation",
                input_text=input_text,
                risk_score=risk_score,
                reason="Violation detected." if has_violation else "No violation detected.",
                risk_reasons=risk_reasons,
            )
        )
        self.db.commit()

    # 3. WorkflowRun 로그 (이 테이블은 기존 구조를 유지하므로 변경 없음)
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
                context_json=context_data, # WorkflowRunModel은 기존대로 context_json 유지
            )
        )
        self.db.commit()

# --- [여기서부터 맨 아래에 추가 (들여쓰기 주의: class 내부에 위치)] ---
    def log_policy_conversion(self, log_id: str, policy_id: str, filename: str, rule_count: int, status: str, warnings: dict = None) -> None:
        from src.database.models import PolicyConversionLogModel # 맨 위에 임포트해도 됩니다.
        
        self.db.add(
            PolicyConversionLogModel(
                id=log_id,
                policy_id=policy_id,
                original_filename=filename,
                parsed_rules_count=rule_count,
                conversion_status=status,
                warnings=warnings or {}
            )
        )
        self.db.commit()