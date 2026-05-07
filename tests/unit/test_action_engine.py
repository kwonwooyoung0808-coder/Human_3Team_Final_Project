from src.engines.action_engine import ActionEngine, DEFAULT_BLOCK_MESSAGE
from src.schemas.violation import Violation

# 위반 없을 때 테스트 확인
def test_no_violation_returns_pass():
    result = ActionEngine().decide(
        run_id = "unit-001",
        response = "정상 응답",
        violations = None
    )

    assert result.action_type == "PASS"
    assert result.message == "Response passed all checks."
    assert result.delivered_response == "정상 응답"

# LOG 권고 위반이 있을 때 원본 응답을 유지하는지 확인
def test_log_action_preserves_original_response():
    violation = Violation(
        id="v-001",
        run_id="unit-002",
        policy_id="TEST_001",
        policy_name="Test Policy",
        reason="테스트 위반",
        source="rule",
        recommended_action="LOG",
        risk_score=0.5
    )

    result = ActionEngine().decide(
        run_id="unit-002",
        response="원본 응답",
        violations=[violation]
    )

    assert result.action_type == "LOG"
    assert result.message == "Response was logged due to policy violations."
    assert result.delivered_response == "원본 응답"
    
# BLOCK 액션은 원본 응답을 차단 메시지로 대체하는지 확인
def test_block_action_removes_original_response():
    violation = Violation(
        id="v-002",
        run_id="unit-003",
        policy_id="TEST_001",
        policy_name="Test Policy",
        reason="차단 대상 위반",
        source="rule",
        recommended_action="BLOCK",
        fallback_message="사용자 정의 차단 메시지",
        risk_score=0.9
    )

    result = ActionEngine().decide(
        run_id="unit-003",
        response="차단되어야 하는 원본 응답",
        violations=[violation]
    )

    assert result.action_type == "BLOCK"
    assert result.message == "사용자 정의 차단 메시지"
    assert result.delivered_response == "사용자 정의 차단 메시지"

# BLOCK 액션 시 fallback_message가 없을 때 기본 메시지 사용 확인
def test_block_action_uses_default_message():
    violation = Violation(
        id="v-003",
        run_id="unit-004",
        policy_id="TEST_001",
        policy_name="Test Policy",
        reason="차단 대상 위반",
        source="rule",
        recommended_action="BLOCK",
        fallback_message=None,
        risk_score=0.9
    )

    result = ActionEngine().decide(
        run_id="unit-004",
        response="원본 응답",
        violations=[violation]
    )

    assert result.action_type == "BLOCK"
    assert result.message == DEFAULT_BLOCK_MESSAGE
    assert result.delivered_response == DEFAULT_BLOCK_MESSAGE

# ActionResult에 필수 결과 필드가 포함되는지 확인
def test_action_result_has_run_id():
    result = ActionEngine().decide(
        run_id="unit-005",
        response="정상 응답",
        violations=[],
    )

    assert result.run_id == "unit-005"
    assert result.action_type == "PASS"
    assert result.status == "applied"
    assert result.delivered_response == "정상 응답"


# === <> 테스트 코드 실행 방법 <> ===
# python -m pytest tests/unit/test_action_engine.py
