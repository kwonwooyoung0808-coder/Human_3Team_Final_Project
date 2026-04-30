import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.core.dependencies import get_db
from src.database.models import ExecutionTraceModel, WorkflowRunModel
from src.schemas.workflow import RunResponse, RunTraceSummary, TraceNodeRead

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])

@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(WorkflowRunModel, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    
    try:
        parsed_context = json.loads(run.context_json) if run.context_json else {}
    except json.JSONDecodeError:
        parsed_context = {}

    return {
        "run_id": run.run_id,
        "input": run.input,
        "output": run.output,
        "final_status": run.final_status,
        "final_action": run.final_action,
        "has_violation": run.has_violation,
        "workflow_name": run.workflow_name,
        "context": parsed_context,
        "created_at": run.created_at,
    }


@router.get("/{run_id}/trace", response_model=RunTraceSummary)
def get_trace(run_id: str, db: Session = Depends(get_db)) -> RunTraceSummary:
    run = db.get(WorkflowRunModel, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    
    # 수정됨: ExecutionTraceModel.created_at.desc() 로 최신순 정렬 적용!
    nodes = list(
        db.scalars(
            select(ExecutionTraceModel)
            .where(ExecutionTraceModel.run_id == run_id)
            .order_by(ExecutionTraceModel.created_at.desc())
        )
    )
    
    return RunTraceSummary(
        run_id=run_id,
        workflow_name=run.workflow_name,
        status=run.final_status,
        nodes=[TraceNodeRead.model_validate(node, from_attributes=True) for node in nodes],
        created_at=run.created_at,
    )