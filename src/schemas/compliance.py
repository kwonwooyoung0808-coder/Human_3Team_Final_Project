from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


class ViolationDetail(BaseModel):
    type: str
    description: str
    severity: Literal["HIGH", "MEDIUM", "LOW"]


class ResponseValidateRequest(BaseModel):
    agent_id: str
    query: str
    response: str
    policy_id: str
    audit_query_id: str | None = None


class ResponseValidateResponse(BaseModel):
    status: Literal["APPROVED", "FLAGGED", "REJECTED"]
    compliance_score: float = 1.0
    violations: list[ViolationDetail] = Field(default_factory=list)
    audit_id: str


class ComplianceState(TypedDict, total=False):
    """LangGraph 상태 — Feature 2 워크플로우 노드 간 전달."""

    agent_id: str
    query: str
    response: str
    policy_id: str
    audit_query_id: str | None

    policy: dict[str, Any]
    rule_violations: list[dict[str, Any]]
    rule_rejected: bool

    llm_compliance_score: float
    llm_violations: list[dict[str, Any]]
    all_violations: list[dict[str, Any]]

    final_status: Literal["APPROVED", "FLAGGED", "REJECTED"]
    final_score: float

    audit_id: str
    error_message: str
