from typing import Any, Literal

from pydantic import BaseModel, Field


class PolicyRule(BaseModel):
    condition: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class PolicyJudgeConfig(BaseModel):
    enabled: bool = False
    criteria: str | None = None


class PolicyAction(BaseModel):
    type: Literal["BLOCK", "LOG"]
    message: str


class Policy(BaseModel):
    id: str
    name: str
    enabled: bool = True
    type: Literal["rule", "judge", "hybrid"]
    rules: list[PolicyRule] = Field(default_factory=list)
    judge: PolicyJudgeConfig = Field(default_factory=PolicyJudgeConfig)
    action: PolicyAction
    severity: Literal["low", "medium", "high"] = "medium"


class PolicyEvaluationResult(BaseModel):
    policy_id: str
    policy_name: str
    triggered: bool = False
    judge_required: bool = False
    judge_result: dict[str, Any] | None = None
    recommended_action: Literal["BLOCK", "LOG"]
    severity: Literal["low", "medium", "high"]
    evidence_spans: list[dict[str, Any]] = Field(default_factory=list)
    reason: str

