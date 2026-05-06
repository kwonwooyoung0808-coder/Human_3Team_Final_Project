import pytest
from pathlib import Path

from src.utils.yaml_loader import load_policy, PolicyLoaderError

# 테스트용 YAML 파일 생성

@pytest.fixture
def content_safety_yaml_path(tmp_path: Path) -> Path:
    content = """id: "CONTENT_001"
name: "corporate_content_safety"
version: "2.1.0"
enabled: true
type: "rule"
judge_required: "never"
severity: "high"
priority: 100
context_scope: ["query", "response"]
rules:
  - condition: "contains_categorized_forbidden_terms"
    on_rule_failure: "block_immediately"
action:
  type: "BLOCK"
  fallback_response: "차단되었습니다."
"""
    file_path = tmp_path / "content_safety_policy.yaml"
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def context_compliance_yaml_path(tmp_path: Path) -> Path:
    content = """id: "CTX_001"
name: "context_based_compliance"
version: "2.1.0"
enabled: true
type: "judge"
judge_required: "always"
severity: "high"
priority: 90
context_scope: ["query", "response"]
rules: []
judge:
  enabled: true
  score_field: "confidence"
action:
  type: "BLOCK"
  fallback_response: "차단되었습니다."
"""
    file_path = tmp_path / "context_compliance_policy.yaml"
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def format_compliance_yaml_path(tmp_path: Path) -> Path:
    content = """id: "FORMAT_001"
name: "response_format_compliance"
version: "2.1.0"
enabled: true
type: "rule"
judge_required: "never"
severity: "high"
priority: 80
context_scope: ["query", "response"]
rules:
  - condition: "format_validation"
    parameters:
      required_formats: ["JSON"]
action:
  type: "BLOCK"
  fallback_response: "포맷 에러"
"""
    file_path = tmp_path / "format_compliance_policy.yaml"
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def hallucination_yaml_path(tmp_path: Path) -> Path:
    content = """id: "HAL_001"
name: "hallucination_and_grounding_check"
version: "2.1.0"
enabled: true
type: "judge"
judge_required: "always"
severity: "medium"
priority: 70
context_scope: ["query", "context", "response"]
rules: []
judge:
  enabled: true
  score_field: "confidence"
action:
  type: "LOG"
  fallback_response: "환각 의심 로그"
"""
    file_path = tmp_path / "hallucination_policy.yaml"
    file_path.write_text(content, encoding="utf-8")
    return file_path


# 단위 테스트 실행

def test_load_valid_content_safety_policy(content_safety_yaml_path: Path):
    """U-YL-01: 규칙 기반(rule) 정책 정상 로드 및 속성 검증"""
    policy = load_policy(content_safety_yaml_path)

    assert policy is not None
    assert policy.id == "CONTENT_001"
    assert policy.enabled is True
    assert policy.type == "rule"
    assert policy.judge_required == "never"
    assert len(policy.rules) >= 1

    if hasattr(policy, "judge") and policy.judge is not None:
        assert policy.judge.enabled is False


def test_load_valid_context_compliance_policy(context_compliance_yaml_path: Path):
    """U-YL-02: 심사 기반(judge) 정책 정상 로드 및 속성 검증"""
    policy = load_policy(context_compliance_yaml_path)

    assert policy is not None
    assert policy.id == "CTX_001"
    assert policy.enabled is True
    assert policy.type == "judge"
    assert policy.judge_required == "always"
    assert len(policy.rules) == 0
    assert policy.judge is not None
    assert policy.judge.enabled is True


def test_load_valid_format_compliance_policy(format_compliance_yaml_path: Path):
    """U-YL-03: Format Compliance 정책 로드 및 속성 검증"""
    policy = load_policy(format_compliance_yaml_path)

    assert policy is not None
    assert policy.id == "FORMAT_001"
    assert policy.type == "rule"
    assert policy.judge_required == "never"
    assert policy.rules[0].parameters.get("required_formats") == ["JSON"]


def test_load_valid_hallucination_policy(hallucination_yaml_path: Path):
    """U-YL-04: Hallucination 정책 로드 및 속성 검증"""
    policy = load_policy(hallucination_yaml_path)

    assert policy is not None
    assert policy.id == "HAL_001"
    assert policy.type == "judge"
    assert policy.judge_required == "always"

    if isinstance(policy.action, dict):
        assert policy.action.get("type") == "LOG"
    else:
        assert policy.action.type == "LOG"
    assert policy.judge.enabled is True


def test_missing_required_field_raises_error(tmp_path: Path):
    """U-YL-05: 필수 필드 누락 시 PolicyLoaderError 발생 여부 검증"""
    invalid_content = """name: "missing_id_policy"
enabled: true
type: "rule"
"""
    file_path = tmp_path / "invalid_missing_id.yaml"
    file_path.write_text(invalid_content, encoding="utf-8")

    with pytest.raises(PolicyLoaderError) as exc_info:
        load_policy(file_path)

    assert "Schema validation failed" in str(exc_info.value)


def test_invalid_yaml_syntax_raises_error(tmp_path: Path):
    """U-YL-06: 잘못된 YAML 문법 사용 시 파싱 예외 처리 검증"""
    invalid_syntax = """id: "ERR_01"
name: [unclosed_list_syntax
"""
    file_path = tmp_path / "syntax_error.yaml"
    file_path.write_text(invalid_syntax, encoding="utf-8")

    with pytest.raises(PolicyLoaderError) as exc_info:
        load_policy(file_path)

    assert "Invalid YAML syntax" in str(exc_info.value)


def test_disabled_policy_not_evaluated(tmp_path: Path):
    """U-YL-07: enabled가 false인 경우 정책 객체의 상태 검증"""
    disabled_content = """id: "DISABLED_001"
name: "disabled_policy"
enabled: false
type: "rule"
judge_required: "never"
severity: "low"
priority: 10
context_scope: ["query"]
action:
  type: "LOG"
"""
    file_path = tmp_path / "disabled_policy.yaml"
    file_path.write_text(disabled_content, encoding="utf-8")

    policy = load_policy(file_path)

    assert policy.id == "DISABLED_001"
    assert policy.enabled is False


# === <> 테스트 코드 실행 방법 <> ===
# $env:PYTHONPATH='.'; pytest tests/unit/test_yaml_loader.py
