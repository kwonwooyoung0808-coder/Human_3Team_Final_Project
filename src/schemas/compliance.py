from enum import Enum
from typing import Literal, Optional, TypedDict

from pydantic import BaseModel, Field


class ComplianceStatus(str, Enum):
    APPROVED = "APPROVED"
    FLAGGED = "FLAGGED"
    REJECTED = "REJECTED"


class ComplianceState(TypedDict, total=False):
    agent_id: str
    query: str
    response: str
    policy_id: str
    policy: dict
    audit_query_id: Optional[str]
    rule_violations: list[dict]
    rule_rejected: bool
    llm_compliance_score: float
    llm_violations: list[dict]
    all_violations: list[dict]
    final_status: str
    final_score: float
    audit_id: Optional[str]
    error_message: Optional[str]


class ViolationDetail(BaseModel):
    type: str
    description: str
    severity: Literal["HIGH", "MEDIUM", "LOW"]


class ResponseValidateRequest(BaseModel):
    agent_id: str
    query: str = Field(..., max_length=4096)
    response: str = Field(..., max_length=16384)
    policy_id: str
    audit_query_id: Optional[str] = None


class ResponseValidateResponse(BaseModel):
    status: Literal["APPROVED", "FLAGGED", "REJECTED"]
    compliance_score: float
    violations: list[ViolationDetail]
    audit_id: str
