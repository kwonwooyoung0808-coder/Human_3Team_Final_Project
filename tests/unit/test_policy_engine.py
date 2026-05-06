import pytest
import json

from src.engines.policy_engine import PolicyEngine
from src.schemas.policy import Policy

# 4가지 정책(Policy) Mock 객체 생성

@pytest.fixture
def content_safety_policy():
    """Rule 기반, 즉시 차단(BLOCK) 정책"""
    return Policy(
        id="CONTENT_001",
        name="corporate_content_safety",
        version="2.1.0",
        enabled=True,
        type="rule",
        judge_required="never",
        severity="high",
        priority=100,
        context_scope=["query", "response"],
        action={"type": "BLOCK"},
        rules=[
            {
                "condition": "contains_categorized_forbidden_terms",
                "parameters": {
                    "categories": {
                        "test_category": {
                            "enabled": True,
                            "exact_terms": ["불법", "terror"]
                        }
                    }
                }
            }
        ]
    )

@pytest.fixture
def format_compliance_policy():
    """Rule 기반, JSON 포맷 검증 정책"""
    return Policy(
        id="FORMAT_001",
        name="response_format_compliance",
        version="2.1.0",
        enabled=True,
        type="rule",
        judge_required="never",
        severity="high",
        priority=80,
        context_scope=["query", "response"],
        action={"type": "BLOCK"},
        rules=[
            {
                "condition": "format_validation",
                "parameters": {"required_formats": ["JSON"]}
            }
        ]
    )

@pytest.fixture
def context_compliance_policy():
    """Judge 기반, 위반 시 차단(BLOCK) 정책"""
    return Policy(
        id="CTX_001",
        name="context_based_compliance",
        version="2.1.0",
        enabled=True,
        type="judge",
        judge_required="always",
        severity="high",
        priority=90,
        context_scope=["query", "response"],
        action={"type": "BLOCK"},
        judge={"enabled": True},
        rules=[]
    )

@pytest.fixture
def hallucination_policy():
    """Judge 기반, 위반 시 로그(LOG) 전용 정책"""
    return Policy(
        id="HAL_001",
        name="hallucination_and_grounding_check",
        version="2.1.0",
        enabled=True,
        type="judge",
        judge_required="always",
        severity="medium",
        priority=70,
        context_scope=["query", "context", "response"],
        action={"type": "LOG"},
        judge={"enabled": True},
        rules=[]
    )

# 단위 테스트 실행

def test_content_rule_match_forbidden_word(content_safety_policy):
    """U-PE-01: 금지어가 정확히 포함된 텍스트 차단"""
    engine = PolicyEngine()
    result = engine.evaluate_policy(
        policy=content_safety_policy,
        response="이것은 불법적인 동작입니다.",
        context={},
        retrieved_context=[]
    )

    assert result.triggered is True
    assert result.recommended_action == "BLOCK"
    assert "불법" in result.reason


def test_content_rule_no_match(content_safety_policy):
    """U-PE-02: 금지어가 없는 안전한 텍스트 통과"""
    engine = PolicyEngine()
    result = engine.evaluate_policy(
        policy=content_safety_policy,
        response="정상적인 시스템 가이드입니다.",
        context={},
        retrieved_context=[]
    )

    assert result.triggered is False


def test_content_rule_case_insensitive(content_safety_policy):
    """U-PE-03: 대소문자가 혼합된 영어 금지어 차단"""
    engine = PolicyEngine()
    result = engine.evaluate_policy(
        policy=content_safety_policy,
        response="TeRrOr를 사용한 우회 공격",
        context={},
        retrieved_context=[]
    )

    assert result.triggered is True
    assert result.recommended_action == "BLOCK"


def test_format_json_valid(format_compliance_policy):
    """U-PE-04: 정상적인 JSON 문자열 통과"""
    engine = PolicyEngine()
    valid_json = json.dumps({"summary": "내용", "evidence": "증거"})
    result = engine.evaluate_policy(
        policy=format_compliance_policy,
        response=valid_json,
        context={},
        retrieved_context=[]
    )

    assert result.triggered is False


def test_format_json_invalid(format_compliance_policy):
    """U-PE-05: JSON 파싱이 불가능한 일반 텍스트 차단"""
    engine = PolicyEngine()
    result = engine.evaluate_policy(
        policy=format_compliance_policy,
        response="일반 텍스트 응답입니다.",
        context={},
        retrieved_context=[]
    )

    assert result.triggered is True
    assert result.recommended_action == "BLOCK"


def test_context_compliance_judge_required(context_compliance_policy):
    """U-PE-06: Context Compliance 정책이 Judge 엔진으로 올바르게 위임되는지 확인"""
    engine = PolicyEngine()
    result = engine.evaluate_policy(
        policy=context_compliance_policy,
        response="사내 규정 관련 질문",
        context={},
        retrieved_context=[]
    )

    assert result.judge_required is True
    assert result.recommended_action == "BLOCK"


def test_hallucination_judge_log_action(hallucination_policy):
    """U-PE-07: 새로 추가된 Hallucination 정책의 Judge 위임 및 LOG 액션 타입 확인"""
    engine = PolicyEngine()
    result = engine.evaluate_policy(
        policy=hallucination_policy,
        response="매출이 500% 증가했습니다.",
        context={},
        retrieved_context=[]
    )

    assert result.judge_required is True
    assert result.recommended_action == "LOG"


def test_engine_empty_response_handling(format_compliance_policy):
    """U-PE-08: 응답이 아예 없는(빈 문자열) 엣지 케이스에서의 엔진 방어 로직"""
    engine = PolicyEngine()
    result = engine.evaluate_policy(
        policy=format_compliance_policy,
        response="",
        context={},
        retrieved_context=[]
    )

    assert result.triggered is True
    assert result.recommended_action == "BLOCK"


def test_policy_execution_error_isolated():
    """U-PE-09: 정책 내부에 알 수 없는 조건(condition)이 들어왔을 때의 예외 처리"""
    engine = PolicyEngine()
    broken_policy = Policy(
        id="ERR_001",
        name="broken_policy",
        version="1.0",
        enabled=True,
        type="rule",
        judge_required="never",
        severity="high",
        priority=1,
        context_scope=["response"],
        action={"type": "BLOCK"},
        rules=[{"condition": "unknown_broken_condition"}]
    )

    # 방금 추가한 방어 로직이 ValueError를 정상적으로 발생시키는지 검증
    with pytest.raises(ValueError) as exc_info:
        engine.evaluate_policy(
            policy=broken_policy,
            response="테스트 텍스트",
            context={},
            retrieved_context=[]
        )

    assert "Unknown rule condition" in str(exc_info.value)


# === <> 테스트 코드 실행 방법 <> ===
# $env:PYTHONPATH='.'; pytest tests/unit/test_policy_engine.py
