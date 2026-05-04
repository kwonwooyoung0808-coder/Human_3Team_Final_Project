from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.dependencies import get_db
from src.database.models import (
    AgentModel,
    PolicyModel,
    QueryAuditLogModel,
    ResponseAuditLogModel,
)
from src.schemas.agent import AgentCreate, AgentPolicyUpdate, AgentResponse

router = APIRouter(prefix="/api/agents", tags=["agents"])


# ──────────────────────────────────────────────────────────────
# PRD 9: POST /api/agents — 에이전트 등록
# ──────────────────────────────────────────────────────────────
@router.post("", response_model=AgentResponse, status_code=201)
def create_agent(payload: AgentCreate, db: Session = Depends(get_db)) -> AgentResponse:
    """
    Sovereign AI 에이전트를 거버넌스 시스템에 등록.
    policy_id 지정 시 즉시 활성 정책 존재 여부 검증.
    중복 ID 등록 시 409 반환.
    """
    agent_id = payload.id or f"agent-{uuid.uuid4().hex[:8]}"

    if db.query(AgentModel).filter(AgentModel.id == agent_id).first():
        raise HTTPException(status_code=409, detail=f"agent_id={agent_id} 이미 존재")

    if payload.policy_id:
        policy = db.query(PolicyModel).filter(
            PolicyModel.id == payload.policy_id,
            PolicyModel.is_active == True,
        ).first()
        if not policy:
            raise HTTPException(
                status_code=422,
                detail=f"policy_id={payload.policy_id} 없음 또는 미활성",
            )

    now = datetime.now(timezone.utc)
    agent = AgentModel(
        id=agent_id,
        name=payload.name,
        description=payload.description,
        policy_id=payload.policy_id,
        status=payload.status,
        created_at=now,
        updated_at=now,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        policy_id=agent.policy_id,
        status=agent.status,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


# ──────────────────────────────────────────────────────────────
# PRD 9: GET /api/agents/{agent_id} — 에이전트 조회
# ──────────────────────────────────────────────────────────────
@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)) -> AgentResponse:
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"agent_id={agent_id} 없음")

    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        policy_id=agent.policy_id,
        status=agent.status,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


# ──────────────────────────────────────────────────────────────
# PRD 9: PUT /api/agents/{agent_id}/policy — 정책 연결
# ──────────────────────────────────────────────────────────────
@router.put("/{agent_id}/policy", response_model=AgentResponse)
def update_agent_policy(
    agent_id: str,
    payload: AgentPolicyUpdate,
    db: Session = Depends(get_db),
) -> AgentResponse:
    """
    에이전트에 활성 정책을 연결.
    비활성 정책 연결 시도 시 422 반환.
    """
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"agent_id={agent_id} 없음")

    policy = db.query(PolicyModel).filter(
        PolicyModel.id == payload.policy_id,
        PolicyModel.is_active == True,
    ).first()
    if not policy:
        raise HTTPException(
            status_code=422,
            detail=f"policy_id={payload.policy_id} 없음 또는 미활성",
        )

    agent.policy_id = payload.policy_id
    agent.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(agent)

    return AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        policy_id=agent.policy_id,
        status=agent.status,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


# ──────────────────────────────────────────────────────────────
# PRD 9: GET /api/agents/{agent_id}/audit — 감사 이력
# ──────────────────────────────────────────────────────────────
@router.get("/{agent_id}/audit")
def get_agent_audit(
    agent_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> dict:
    """
    에이전트의 query / response 감사 이력 조회.
    최근순 정렬, 기본 50건 제한.
    """
    if not db.query(AgentModel).filter(AgentModel.id == agent_id).first():
        raise HTTPException(status_code=404, detail=f"agent_id={agent_id} 없음")

    queries = (
        db.query(QueryAuditLogModel)
        .filter(QueryAuditLogModel.agent_id == agent_id)
        .order_by(QueryAuditLogModel.created_at.desc())
        .limit(limit)
        .all()
    )
    responses = (
        db.query(ResponseAuditLogModel)
        .filter(ResponseAuditLogModel.agent_id == agent_id)
        .order_by(ResponseAuditLogModel.created_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "agent_id": agent_id,
        "query_audits": [
            {
                "audit_id":     q.id,
                "query":        q.query,
                "status":       q.status,
                "risk_score":   q.risk_score,
                "action_taken": q.action_taken,
                "created_at":   q.created_at,
            }
            for q in queries
        ],
        "response_audits": [
            {
                "audit_id":         r.id,
                "query_audit_id":   r.query_audit_id,
                "status":           r.status,
                "compliance_score": r.compliance_score,
                "violation_count":  len(r.violations or []),
                "created_at":       r.created_at,
            }
            for r in responses
        ],
    }
