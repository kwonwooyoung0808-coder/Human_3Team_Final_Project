from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.dependencies import get_db
from src.database.models import AgentModel, PolicyModel
from src.schemas.query_risk import QueryCheckRequest, QueryCheckResponse
from src.workflows.query_risk_workflow import build_query_risk_graph

router = APIRouter(prefix="/v1/query", tags=["query-risk"])


@router.post("/check", response_model=QueryCheckResponse)
async def query_check(
    request: QueryCheckRequest,
    db: Session = Depends(get_db),
) -> QueryCheckResponse:
    """
    쿼리 위험성 평가 (Feature 1).
    그래프 진입 전 FK 대상(agent_id, policy_id) 존재 여부 사전 검증.
    """
    agent = db.query(AgentModel).filter(
        AgentModel.id == request.agent_id,
        AgentModel.status == "ACTIVE",
    ).first()
    if not agent:
        raise HTTPException(
            status_code=422,
            detail=f"agent_id={request.agent_id} 없음 또는 비활성",
        )

    policy = db.query(PolicyModel).filter(
        PolicyModel.id == request.policy_id,
        PolicyModel.is_active == True,
    ).first()
    if not policy:
        raise HTTPException(
            status_code=422,
            detail=f"policy_id={request.policy_id} 없음 또는 미활성",
        )

    graph = build_query_risk_graph()
    final: dict = await graph.ainvoke({
        "agent_id":  request.agent_id,
        "query":     request.query,
        "context":   request.context,
        "policy_id": request.policy_id,
    })

    return QueryCheckResponse(
        status=final.get("final_status", "PASSED"),
        risk_score=final.get("final_score", 0.0),
        # combined_reasons = 룰 위반 텍스트 + LLM 평가 사유 (룰 차단 시에도 사유 노출)
        risk_reasons=final.get("combined_reasons", []),
        action_taken=final.get("action_taken", "PASS"),
        audit_id=final.get("audit_id", ""),
    )
