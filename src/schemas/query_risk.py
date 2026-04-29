from enum import Enum
from typing import Literal, Optional, TypedDict

from pydantic import BaseModel, Field


class RiskStatus(str, Enum):
    BLOCKED = "BLOCKED"
    WARNED = "WARNED"
    PASSED = "PASSED"


class QueryRiskState(TypedDict, total=False):
    agent_id: str
    query: str
    context: Optional[str]
    policy_id: str
    policy: dict
    rule_violations: list[dict]
    rule_blocked: bool
    llm_risk_score: float
    llm_risk_reasons: list[str]
    final_status: str
    final_score: float
    action_taken: str
    audit_id: Optional[str]
    error_message: Optional[str]


class QueryCheckRequest(BaseModel):
    agent_id: str
    query: str = Field(..., min_length=1, max_length=4096)
    context: Optional[str] = Field(None, max_length=8192)
    policy_id: str


class QueryCheckResponse(BaseModel):
    status: Literal["BLOCKED", "WARNED", "PASSED"]
    risk_score: float
    risk_reasons: list[str]
    action_taken: Literal["BLOCK", "LOG", "PASS"]
    audit_id: str
