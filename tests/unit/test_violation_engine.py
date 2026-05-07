import pytest
from src.engines.violation_engine import ViolationEngine
from src.schemas.policy import Policy, PolicyEvaluationResult, PolicyAction
from src.schemas.judge import JudgeResult

@pytest.fixture
def violation_engine():
    return ViolationEngine()

@pytest.fixture
def base_policy():
    return Policy(
        id="test-policy",
        name="Test Policy",
        type="hybrid",
        priority=80,
        judge_required="rule_triggered",
        action=PolicyAction(type="BLOCK", message="Blocked by policy")
    )

# U-VE-01: Violation 객체 필수 필드 존재 확인
def test_violation_required_fields(violation_engine, base_policy):
    result = PolicyEvaluationResult(
        policy_id=base_policy.id,
        policy_name=base_policy.name,
        triggered=True,
        recommended_action="BLOCK",
        severity="high",
        reason="Test violation"
    )
    
    violation = violation_engine.from_policy_result(
        run_id="run-001",
        policy=base_policy,
        result=result
    )
    
    # 필수 필드 8개 존재 확인
    assert violation.id is not None
    assert violation.run_id == "run-001"
    assert violation.policy_id == base_policy.id
    assert violation.reason == "Test violation"
    assert violation.evidence_span is not None
    assert violation.source == "rule"
    assert violation.recommended_action == "BLOCK"
    assert violation.risk_score == 0.8

# U-VE-02: Rule 매칭 존재 시 evidence_span 확인
def test_evidence_span_rule_priority(violation_engine, base_policy):
    # Rule 매칭 정보(evidence_spans)가 포함된 결과
    result = PolicyEvaluationResult(
        policy_id=base_policy.id,
        policy_name=base_policy.name,
        triggered=True,
        recommended_action="BLOCK",
        severity="high",
        reason="Rule triggered",
        evidence_spans=[{"text": "위험한 단어", "start_char": 0, "end_char": 6, "source": "rule"}]
    )
    
    violation = violation_engine.from_policy_result(
        run_id="run-002",
        policy=base_policy,
        result=result
    )
    
    assert violation.evidence_span.text == "위험한 단어"
    assert violation.evidence_span.source == "rule"
    assert violation.evidence_span.confidence == 1.0

# U-VE-03: Rule 없고 Judge evidence_text 존재 시 evidence_span 확인
def test_evidence_span_judge_fallback(violation_engine, base_policy):
    result = PolicyEvaluationResult(
        policy_id=base_policy.id,
        policy_name=base_policy.name,
        triggered=False,
        recommended_action="BLOCK",
        severity="high",
        reason="Judge failed"
    )
    judge_result = JudgeResult(
        verdict="FAIL",
        confidence=0.7,
        reason="LLM detected risk",
        evidence_text="Judge가 찾은 증거 문장"
    )
    
    violation = violation_engine.from_policy_result(
        run_id="run-003",
        policy=base_policy,
        result=result,
        judge_result=judge_result
    )
    
    assert violation.evidence_span.text == "Judge가 찾은 증거 문장"
    assert violation.evidence_span.source == "judge"

# U-VE-04: Rule 기반 위반 risk score 검증 (High Priority)
def test_risk_score_rule_based_high(violation_engine, base_policy):
    # Priority 95 -> risk_score 0.95
    base_policy.priority = 95
    result = PolicyEvaluationResult(
        policy_id=base_policy.id,
        policy_name=base_policy.name,
        triggered=True,
        recommended_action="BLOCK",
        severity="high",
        reason="Critical Rule"
    )
    
    violation = violation_engine.from_policy_result(
        run_id="run-004",
        policy=base_policy,
        result=result
    )
    
    assert violation.risk_score == 0.95
    assert violation.risk_score >= 0.9

# U-VE-05: Judge 기반 위반 risk score 검증 (Confidence 기반)
def test_risk_score_judge_based_confidence(violation_engine, base_policy):
    # Rule은 발생 안함, Judge Confidence 0.7 -> risk_score 0.7
    result = PolicyEvaluationResult(
        policy_id=base_policy.id,
        policy_name=base_policy.name,
        triggered=False,
        recommended_action="BLOCK",
        severity="medium",
        reason="Judge failed"
    )
    judge_result = JudgeResult(
        verdict="FAIL",
        confidence=0.7,
        reason="LLM risk detection"
    )
    
    violation = violation_engine.from_policy_result(
        run_id="run-005",
        policy=base_policy,
        result=result,
        judge_result=judge_result
    )
    
    assert pytest.approx(violation.risk_score) == 0.7

# U-VE-06: Violation의 run_id 연결 확인
def test_violation_run_id_linked(violation_engine, base_policy):
    target_run_id = "run-link-test-999"
    result = PolicyEvaluationResult(
        policy_id=base_policy.id,
        policy_name=base_policy.name,
        triggered=True,
        recommended_action="BLOCK",
        severity="high",
        reason="Link test"
    )
    
    violation = violation_engine.from_policy_result(
        run_id=target_run_id,
        policy=base_policy,
        result=result
    )
    
    assert violation.run_id == target_run_id

# 추가: Clamping 검증
def test_risk_score_clamping_max(violation_engine, base_policy):
    base_policy.priority = 150
    result = PolicyEvaluationResult(
        policy_id=base_policy.id,
        policy_name=base_policy.name,
        triggered=True,
        recommended_action="BLOCK",
        severity="high",
        reason="Over priority"
    )
    
    violation = violation_engine.from_policy_result(
        run_id="run-clamp",
        policy=base_policy,
        result=result
    )
    
    assert violation.risk_score == 1.0
