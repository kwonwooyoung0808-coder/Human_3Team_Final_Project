from unittest.mock import patch, MagicMock
from src.engines.judge_engine import JudgeEngine
from src.schemas.policy import Policy, SeverityByConfidence, PolicyPreconditions


class FakeLLMResponse:
    def __init__(self, content):
        self.content = content


class FakeLLMClient:
    def __init__(self, output):
        self.output = output
        self.last_prompt = None

    def invoke(self, prompt):
        self.last_prompt = prompt
        return FakeLLMResponse(self.output)


def make_policy(policy_id="CONTENT_001", category=None, threshold=None, requires_context=False):
    sev_conf = None
    if threshold:
        sev_conf = SeverityByConfidence(high_when_confidence_gte=threshold)
    
    preconditions = PolicyPreconditions(requires_retrieved_context=requires_context)
        
    # [수정] 기존에는 action={"type": "Retry"}를 사용했으나, PolicyAction.type은
    # Literal["BLOCK", "LOG"]만 허용하므로 ValidationError 발생.
    # "Retry" 같은 동적 액션은 _determine_action_by_severity()가 결정하는 값이며
    # Policy 스키마의 action.type 필드에 직접 지정하는 값이 아님.
    return Policy(
        id=policy_id,
        name="Test Policy",
        category=category,
        type="judge",
        judge_required="always",
        severity="high",
        action={"type": "LOG"},
        severity_by_confidence=sev_conf,
        preconditions=preconditions,
        judge={
            "enabled": True,
            "criteria": "Test criteria"
        }
    )

# U-JE-01: Mock LLM의 정상 JSON 응답이 JudgeResult로 변환되는지 확인
def test_judge_returns_structured_json():
    llm = FakeLLMClient(
        '{"verdict":"PASS","confidence":0.8,"reason":"정상 응답","evidence_text":null}'
    )
    engine = JudgeEngine(prompt_dir="src/prompts", llm_client=llm)

    result = engine.judge(
        policy=make_policy(),
        response="정상 응답",
        retrieved_context=[]
    )

    assert result.verdict == "PASS"
    assert result.confidence == 0.8
    assert result.severity == "Safe"
    assert result.action == "Allow"
    
# U-JE-02: JSON 파싱 불가 응답 시 Fallback 및 Policy 기반 Action 보정
def test_judge_fallback_on_malformed_json():
    llm = FakeLLMClient('invalid json')
    engine = JudgeEngine(prompt_dir="src/prompts", llm_client=llm)

    result = engine.judge(
        policy=make_policy("CONTENT_001", category="content_safety"),
        response="테스트 응답",
        retrieved_context=[]
    )

    assert result.verdict == "FAIL"
    assert result.severity == "Critical"
    assert result.action == "Block"

# U-JE-03: Policy 객체가 외부에서 주입됨을 검증 (Dependency Injection)
def test_judge_policy_injection():
    llm = FakeLLMClient('{"verdict":"PASS","confidence":1.0,"reason":"OK"}')
    engine = JudgeEngine(prompt_dir="src/prompts", llm_client=llm)
    
    # 별도로 생성한 Mock Policy 주입
    mock_policy = make_policy(policy_id="INJECTED_ID", category="test")
    
    # 실행 시 해당 정책 객체의 속성을 사용하는지 확인
    with patch.object(JudgeEngine, '_get_filtered_few_shot', return_value="") as mock_few_shot:
        engine.judge(policy=mock_policy, response="R", retrieved_context=[])
        # _get_filtered_few_shot이 주입된 mock_policy 객체를 인자로 받았는지 확인
        mock_few_shot.assert_called_once_with(mock_policy)

# U-JE-04: _read_prompt를 통한 실제 파일 로드 로직 검증
def test_judge_prompt_loaded_from_file():
    engine = JudgeEngine(prompt_dir="src/prompts", llm_client=None)

    # [수정] 기존에는 Path.read_text만 모킹했으나, _read_prompt()는 read_text() 호출 전에
    # path.exists()로 파일 존재 여부를 먼저 확인함. exists()가 False를 반환하면 ""를
    # 즉시 반환하고 read_text()는 아예 호출되지 않아 mock_read.assert_called_once()가 실패.
    # Path.exists도 함께 모킹해야 read_text 호출 경로까지 도달할 수 있음.
    with patch("src.engines.judge_engine.Path.exists", return_value=True), \
         patch("src.engines.judge_engine.Path.read_text") as mock_read:
        mock_read.return_value = "Mocked Prompt Content"

        # 1. 처음 읽을 때 파일 시스템 호출 확인
        content = engine._read_prompt("test.txt")
        assert content == "Mocked Prompt Content"
        mock_read.assert_called_once()

        # 2. [캐싱 검증] 두 번째 읽을 때는 파일 시스템 호출 없이 캐시에서 반환해야 함
        content_cached = engine._read_prompt("test.txt")
        assert content_cached == "Mocked Prompt Content"
        assert mock_read.call_count == 1  # 추가 호출 없음 확인

# U-JE-05: _extract_judged_text 메서드 직접 검증
# [추가 이유] 이 메서드는 _judge_groundedness_fallback 내부에서 호출되어
# LLM 응답이 JSON 형태인 경우 "answer" 키의 값만 추출해 판정 대상 텍스트로 사용함.
# 기존 테스트에는 이 로직에 대한 독립적인 단위 테스트가 없어 누락된 번호(U-JE-05)로 추가.
def test_extract_judged_text_plain_string():
    engine = JudgeEngine(prompt_dir="src/prompts", llm_client=None)
    result = engine._extract_judged_text("단순 텍스트 응답입니다.")
    assert result == "단순 텍스트 응답입니다."

def test_extract_judged_text_json_with_answer_key():
    engine = JudgeEngine(prompt_dir="src/prompts", llm_client=None)
    result = engine._extract_judged_text('{"answer": "추출된 답변 텍스트"}')
    assert result == "추출된 답변 텍스트"

def test_extract_judged_text_json_without_answer_key():
    engine = JudgeEngine(prompt_dir="src/prompts", llm_client=None)
    result = engine._extract_judged_text('{"other_key": "다른 값"}')
    assert result == '{"other_key": "다른 값"}'

# U-JE-06: Retry 횟수 초과 시 Block 전환 테스트
def test_judge_retry_escalation():
    llm = FakeLLMClient('{"verdict":"FAIL","confidence":0.7,"reason":"Retry 필요"}')
    engine = JudgeEngine(prompt_dir="src/prompts", llm_client=llm)

    result_0 = engine.judge(policy=make_policy("HAL_001", category="groundedness"), response="R", retrieved_context=["C"], current_retry=0)
    assert result_0.action == "Retry"

    result_3 = engine.judge(policy=make_policy("HAL_001", category="groundedness"), response="R", retrieved_context=["C"], current_retry=3)
    assert result_3.action == "Block"
    assert "Max Retries Exceeded" in result_3.reason

# U-JE-07: 사용자 정의 신뢰도 임계치(threshold) 작동 확인
def test_judge_custom_threshold():
    llm = FakeLLMClient('{"verdict":"FAIL","confidence":0.7,"reason":"애매함"}')
    engine = JudgeEngine(prompt_dir="src/prompts", llm_client=llm)

    policy_a = make_policy(category="groundedness", threshold=0.6)
    result_a = engine.judge(policy=policy_a, response="R", retrieved_context=["C"])
    assert result_a.action == "Retry"

    policy_b = make_policy(category="groundedness", threshold=0.8)
    result_b = engine.judge(policy=policy_b, response="R", retrieved_context=["C"])
    assert result_b.action == "Block"

# U-JE-08: LLM 응답 실패 시 RAG Fallback (토큰 중복 매칭) 작동 확인
# [수정] 기존 테스트는 동일한 PASS 케이스를 두 번 반복하는 중복 구조였음.
# 두 번째 블록을 FAIL 케이스(컨텍스트와 무관한 응답)로 교체하여
# Fallback의 PASS/FAIL 양방향 판정을 한 테스트 안에서 검증하도록 개선.
def test_judge_context_fallback():
    llm = FakeLLMClient(None)
    engine = JudgeEngine(prompt_dir="src/prompts", llm_client=llm)

    # 응답 토큰이 컨텍스트에 충분히 포함된 경우 -> PASS
    policy = make_policy(requires_context=True)
    result = engine.judge(
        policy=policy,
        response="사과는 빨갛다",
        retrieved_context=["사과는 빨갛다. 바나나는 노랗다."]
    )
    assert result.verdict == "PASS"
    assert "Fallback" in result.reason

    # 응답 토큰이 컨텍스트에 존재하지 않는 경우 -> FAIL
    policy_fail = make_policy(requires_context=True)
    result_fail = engine.judge(
        policy=policy_fail,
        response="포도는 보라색이다",
        retrieved_context=["사과는 빨갛다. 바나나는 노랗다."]
    )
    assert result_fail.verdict == "FAIL"
    assert "Fallback" in result_fail.reason
