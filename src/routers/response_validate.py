from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.dependencies import get_db
from src.database.models import AgentModel, PolicyModel, QueryAuditLogModel
from src.schemas.compliance import (
    ResponseValidateRequest,
    ResponseValidateResponse,
    ViolationDetail,
)
from src.workflows.compliance_workflow import build_compliance_graph

router = APIRouter(prefix="/v1/response", tags=["response-compliance"])


@router.post("/validate", response_model=ResponseValidateResponse)
async def response_validate(
    request: ResponseValidateRequest,
    db: Session = Depends(get_db),
) -> ResponseValidateResponse:
    """
    응답 내규 준수 검증 (Feature 2).
    그래프 진입 전 FK 대상(agent_id, policy_id, audit_query_id) 존재 여부 사전 검증.
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

    # Feature 1 연결 ID 유효성 검증 (선택적)
    if request.audit_query_id:
        qal = db.query(QueryAuditLogModel).filter(
            QueryAuditLogModel.id == request.audit_query_id
        ).first()
        if not qal:
            raise HTTPException(
                status_code=422,
                detail=f"audit_query_id={request.audit_query_id} 없음",
            )
        # F2-4: 다른 에이전트의 query audit 을 본 에이전트의 response audit 에
        # 연결하는 것은 데이터 무결성 위반 → 422 거부
        if qal.agent_id != request.agent_id:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"audit_query_id={request.audit_query_id} 의 agent_id 불일치 "
                    f"(query audit agent={qal.agent_id}, request agent={request.agent_id})"
                ),
            )

    graph = build_compliance_graph()
    final: dict = await graph.ainvoke({
        "agent_id":       request.agent_id,
        "query":          request.query,
        "response":       request.response,
        "policy_id":      request.policy_id,
        "audit_query_id": request.audit_query_id,
    })

    raw_violations = final.get("all_violations", [])
    violations: list[ViolationDetail] = []
    for v in raw_violations:
        try:
            violations.append(ViolationDetail(**v))
        except Exception:
            pass

    return ResponseValidateResponse(
        status=final.get("final_status", "APPROVED"),
        compliance_score=final.get("final_score", 1.0),
        violations=violations,
        audit_id=final.get("audit_id", ""),
    )
