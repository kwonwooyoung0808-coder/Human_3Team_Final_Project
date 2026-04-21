import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.dependencies import get_db
from src.database.models import EvidenceSpanModel, ViolationModel, WorkflowRunModel
from src.schemas.audit import AuditLogCreate
from src.schemas.workflow import EvaluateRequest, EvaluateResponse
from src.services.audit_logger import AuditLogger
from src.services.trace_logger import TraceLogger
from src.workflows.agent_workflow import generate_workflow_state
from src.workflows.interceptors.interceptor import evaluate_final_response

router = APIRouter(prefix="/api/v1", tags=["evaluate"])


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate(request: EvaluateRequest, db: Session = Depends(get_db)) -> EvaluateResponse:
    settings = get_settings()
    trace_logger = TraceLogger(db)
    trace_logger.log_node(request.run_id, settings.workflow_name, "input", "api")

    state = generate_workflow_state(request)
    trace_logger.log_node(request.run_id, settings.workflow_name, "generator", "fake_llm")

    violations, action = evaluate_final_response(state)
    trace_logger.log_node(request.run_id, settings.workflow_name, "governance_interceptor", "policy")
    trace_logger.log_node(request.run_id, settings.workflow_name, "action_engine", "action")

    db.merge(
        WorkflowRunModel(
            run_id=request.run_id,
            input=request.input,
            output=action.delivered_response,
            final_status="completed",
            final_action=action.action_type,
            has_violation=bool(violations),
            workflow_name=settings.workflow_name,
            context_json=json.dumps(request.context),
        )
    )
    db.commit()

    for violation in violations:
        db.add(
            ViolationModel(
                violation_id=violation.id,
                run_id=violation.run_id,
                policy_id=violation.policy_id,
                policy_name=violation.policy_name,
                reason=violation.reason,
                source=violation.source,
                risk_score=violation.risk_score,
                recommended_action=violation.recommended_action,
                judge_verdict=violation.judge_verdict,
                judge_confidence=violation.judge_confidence,
            )
        )
        if violation.evidence_span:
            db.add(
                EvidenceSpanModel(
                    violation_id=violation.id,
                    text=violation.evidence_span.text,
                    start_char=violation.evidence_span.start_char,
                    end_char=violation.evidence_span.end_char,
                    source=violation.evidence_span.source,
                    condition=violation.evidence_span.condition,
                    policy_id=violation.evidence_span.policy_id,
                    confidence=violation.evidence_span.confidence,
                    human_reason=violation.evidence_span.human_reason,
                )
            )
    db.commit()

    AuditLogger(db).log(
        AuditLogCreate(
            run_id=request.run_id,
            event_type="policy_evaluation",
            entity_type="run",
            entity_id=request.run_id,
            reason="Violation detected." if violations else "No violation detected.",
            context_json=request.context,
        )
    )

    return EvaluateResponse(
        run_id=request.run_id,
        has_violation=bool(violations),
        final_action=action.action_type,
        final_response=action.delivered_response,
        violations=violations,
    )

