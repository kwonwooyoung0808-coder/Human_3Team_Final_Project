from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.dependencies import get_db
from src.database.models import AgentModel, PolicyModel
from src.schemas.compliance import ViolationDetail
from src.schemas.proxy import ProxyChatRequest, ProxyChatResponse
from src.services.ollama_client import OllamaClient
from src.workflows.compliance_workflow import build_compliance_graph
from src.workflows.query_risk_workflow import build_query_risk_graph

router = APIRouter(prefix="/v1/proxy", tags=["proxy"])


# ──────────────────────────────────────────────────────────────
# 데모/테스트용 Sovereign AI 호출 — 실제 운영 시 고객사 LLM URL로 교체
# ──────────────────────────────────────────────────────────────
async def _call_sovereign_ai(query: str, context: str | None = None) -> str:
    """
    데모용: 같은 Ollama 인스턴스를 Sovereign AI로 재사용.
    실제 운영 시 이 함수를 고객사 Sovereign AI 호출로 교체.
    """
    client = OllamaClient()
    prompt = f"질문: {query}"
    if context:
        prompt = f"컨텍스트: {context}\n\n{prompt}"
    return await client.generate(prompt)


# ──────────────────────────────────────────────────────────────
# POST /v1/proxy/chat — Feature 1 → Sovereign AI → Feature 2 자동 연결
# ──────────────────────────────────────────────────────────────
@router.post("/chat", response_model=ProxyChatResponse)
async def proxy_chat(
    request: ProxyChatRequest,
    db: Session = Depends(get_db),
) -> ProxyChatResponse:
    """
    PRD 외 편의 엔드포인트. 다음 3단계를 자동으로 묶음:

    ① Feature 1 (질의 위험 감지) — query_risk_workflow 실행
    ② BLOCKED 아니면 Sovereign AI 호출 (현재 데모용 Ollama)
    ③ Feature 2 (응답 내규 검증) — compliance_workflow 실행 (audit_query_id 자동 연결)

    호출자는 한 번의 API 호출로 전 과정 결과를 받을 수 있음.
    개별 단계 추적이 필요하면 query_audit_id / response_audit_id로 감사 로그 조회.
    """
    # ── 사전 검증 (FK 무결성) ──────────────────────────────────
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

    # ── ① Feature 1: 질의 위험 감지 ────────────────────────────
    query_graph = build_query_risk_graph()
    q_final: dict = await query_graph.ainvoke({
        "agent_id":  request.agent_id,
        "query":     request.query,
        "context":   request.context,
        "policy_id": request.policy_id,
    })

    query_audit_id = q_final.get("audit_id", "")
    risk_score = q_final.get("final_score", 0.0)
    risk_reasons = q_final.get("llm_risk_reasons", [])

    if q_final.get("final_status") == "BLOCKED":
        return ProxyChatResponse(
            status="BLOCKED_BY_QUERY",
            final_response=None,
            query_audit_id=query_audit_id,
            risk_score=risk_score,
            risk_reasons=risk_reasons,
        )

    # ── ② Sovereign AI 호출 ────────────────────────────────────
    try:
        ai_response = await _call_sovereign_ai(request.query, request.context)
    except Exception as e:
        return ProxyChatResponse(
            status="FAILED",
            query_audit_id=query_audit_id,
            risk_score=risk_score,
            error_message=f"Sovereign AI 호출 실패: {e}",
        )

    # ── ③ Feature 2: 응답 내규 검증 (audit_query_id 자동 연결) ──
    compliance_graph = build_compliance_graph()
    r_final: dict = await compliance_graph.ainvoke({
        "agent_id":       request.agent_id,
        "query":          request.query,
        "response":       ai_response,
        "policy_id":      request.policy_id,
        "audit_query_id": query_audit_id,
    })

    response_audit_id = r_final.get("audit_id", "")
    compliance_score = r_final.get("final_score", 1.0)
    raw_violations = r_final.get("all_violations", [])

    violations: list[ViolationDetail] = []
    for v in raw_violations:
        try:
            violations.append(ViolationDetail(**v))
        except Exception:
            pass

    final_status = r_final.get("final_status", "APPROVED")
    if final_status == "REJECTED":
        return ProxyChatResponse(
            status="REJECTED_BY_RESPONSE",
            final_response=None,
            query_audit_id=query_audit_id,
            response_audit_id=response_audit_id,
            risk_score=risk_score,
            compliance_score=compliance_score,
            violations=violations,
            risk_reasons=risk_reasons,
        )

    if final_status == "FLAGGED":
        return ProxyChatResponse(
            status="FLAGGED",
            final_response=ai_response,
            query_audit_id=query_audit_id,
            response_audit_id=response_audit_id,
            risk_score=risk_score,
            compliance_score=compliance_score,
            violations=violations,
            risk_reasons=risk_reasons,
        )

    return ProxyChatResponse(
        status="APPROVED",
        final_response=ai_response,
        query_audit_id=query_audit_id,
        response_audit_id=response_audit_id,
        risk_score=risk_score,
        compliance_score=compliance_score,
        violations=violations,
        risk_reasons=risk_reasons,
    )
