from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

# B-1 해소: Rule 검증 실패 시 즉시 차단할지, Judge로 넘길지 결정하는 흐름 제어 필드
class PolicyRule(BaseModel):
    condition: str

    # [LOW 이슈 반영]: 문자열 오타 방지 및 타입 안정성 강화를 위해 Literal 적용
    # Rule 검증 실패 시 즉시 차단할지, 아니면 Judge로 재검증할지 명확히 제한
    on_rule_failure: Optional[Literal["block_immediately", "judge_fallback"]] = None

    parameters: dict[str, Any] = Field(default_factory=dict)

# B-4 해소: Groundedness 등 컨텍스트가 필요한 정책에서 데이터 부재 시의 동작 정의
class PolicyPreconditions(BaseModel):
    # [LOW 이슈 반영]: Groundedness 등 컨텍스트가 필요한 정책에서 데이터 부재 시의 동작 정의
    requires_retrieved_context: bool = False

    # 단순 문자열 오류 방지를 위해 처리 방식을 Literal로 엄격히 제한
    # SKIP: 해당 정책 검사를 건너뜀 / WARN: 경고 로그를 남기고 다음 단계로 진행
    no_context_behavior: Optional[Literal["SKIP", "WARN"]] = None    # 데이터가 None일 때
    empty_context_behavior: Optional[Literal["SKIP", "WARN"]] = None # 데이터가 빈 리스트([])일 때

class PolicyJudgeConfig(BaseModel):
    enabled: bool = False
    score_field: Optional[str] = None
    criteria: Optional[str] = None
    output_contract: Optional[dict[str, Any]] = None

class PolicyAction(BaseModel):
    # [MEDIUM 이슈 반영]: 기존 시스템과의 하위 호환성(Backward Compatibility) 유지 및
    # 특정 조건이 없는 일반적인 Rule 정책에서 범용적으로 사용할 응답 메시지 필드
    message: Optional[str] = None

    # Rule 기반 정책의 Action 필드
    # 위반 시 수행할 액션 타입(차단 또는 기록)과 정책 위반 시 반환할 대체 응답 정의
    type: Optional[Literal["BLOCK", "LOG"]] = None
    fallback_response: Optional[str] = None

    # Judge 기반 정책의 Action 필드 (예: Groundedness Policy)
    # 신뢰도 점수가 임계값(threshold)을 넘었을 때와 그렇지 않았을 때의 메시지를 개별 관리
    default_type: Optional[Literal["BLOCK", "LOG"]] = None
    block_threshold: Optional[float] = None
    block_message: Optional[str] = None
    log_message: Optional[str] = None

# B-5 해소: 복수 정책 위반 시 우선순위 및 메시지 선택 전략 정의
class ConflictResolution(BaseModel):
    block_overrides_log: bool = True
    use_policy_priority: bool = True
    fallback_message_policy: str = "highest_priority_block"

# [MEDIUM 이슈 반영]: 점수 기반으로 심각도를 가변적으로 조정하기 위한 필드 확장
class SeverityByConfidence(BaseModel):
    high_when_confidence_gte: float
    medium_when_confidence_gte: Optional[float] = None
    low_when_confidence_gte: Optional[float] = None

class Policy(BaseModel):
    id: str
    name: str
    version: Optional[str] = None
    enabled: bool = True
    type: Literal["rule", "judge", "hybrid"]
    severity: Literal["low", "medium", "high"] = "medium"
    priority: int = 100

    # [MEDIUM 이슈 반영]: 정책 차단 여부를 결정하는 최소 심각도 임계값
    # 'high'로 설정 시, 위반 결과의 severity가 high일 때만 차단 로직이 활성화됨
    # 타입 오타 방지를 위해 문자열에서 Literal로 엄격하게 제한
    severity_threshold: Optional[Literal["low", "medium", "high"]] = None

    # A-7 해소: 불필요한 중복 제거 및 파이프라인 트리거 조건을 명시적 상수로 관리
    # always: 무조건 Judge 실행, rule_triggered: Rule 위반 시 실행, never: Rule만 실행
    judge_required: Literal["always", "rule_triggered", "never"]

    severity_threshold: Optional[str] = None

    # B-4 해소: 전처리 조건 정의 (데이터 유무에 따른 정책 실행 여부 결정)
    preconditions: Optional[PolicyPreconditions] = None

    rules: list[PolicyRule] = Field(default_factory=list)
    judge: PolicyJudgeConfig = Field(default_factory=PolicyJudgeConfig)

    # B-1, B-5 대응: 통합된 액션 관리 객체
    action: PolicyAction

    # 신뢰도 점수에 따른 심각도 매핑 로직
    severity_by_confidence: Optional[SeverityByConfidence] = None

    # 복수 정책 위반 처리 전략
    conflict_resolution: Optional[ConflictResolution] = None

class PolicyEvaluationResult(BaseModel):
    """
    Policy Engine의 최종 출력 규격
    모든 정책 검사 결과는 이 스키마로 표준화되어 Violation Builder로 전달됩니다.
    """
    policy_id: str
    policy_name: str
    triggered: bool = False
    judge_required: bool = False
    judge_result: dict[str, Any] | None = None
    recommended_action: Literal["BLOCK", "LOG"]
    severity: Literal["low", "medium", "high"]
    evidence_spans: list[dict[str, Any]] = Field(default_factory=list)
    reason: str
