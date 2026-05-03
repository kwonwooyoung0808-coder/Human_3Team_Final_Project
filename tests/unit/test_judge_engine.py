from src.engines.judge_engine import JudgeEngine
from src.schemas.policy import Policy


class FakeLLMClient:
    def __init__(self, output):
        self.output = output
        self.last_prompt = None

    def generate(self, prompt):
        self.last_prompt = prompt
        return self.output


def make_policy(policy_id="CONTENT_001"):
    return Policy(
        id=policy_id,
        name="Test Policy",
        type="judge",
        judge_required="always",
        action={"default_type": "LOG"},
        judge={
            "enabled": True,
            "criteria": "Test criteria"
        }
    )

# U-JE-01
# Mock LLM의 정상 JSON 응답이 JudgeResult로 변환되는지 확인
def test_judge_returns_structured_json():
    llm = FakeLLMClient(
        '{"verdict":"PASS","confidence":0.8,"reason":"정상 응답","evidence_text":null}'
    )
    engine = JudgeEngine(prompt_dir=".", llm_client=llm)

    result = engine.judge(
        policy=make_policy(),
        response="정상 응답",
        retrieved_context=[]
    )

    assert result.verdict == "PASS"
    assert result.confidence == 0.8
    assert result.reason == "정상 응답"
    assert result.evidence_text is None

# U-JE-05
# JudgeResult confidence가 0.0 이상 1.0 이하인지 확인
def test_judge_confidence_range():
    llm = FakeLLMClient(
        '{"verdict":"PASS","confidence":0.6,"reason":"range test","evidence_text":null}'
    )
    engine = JudgeEngine(prompt_dir=".", llm_client=llm)

    result = engine.judge(
        policy=make_policy(),
        response="응답",
        retrieved_context=[]
    )

    assert 0.0 <= result.confidence <= 1.0

# === <> 테스트 코드 실행 방법 <> ===
# $env:PYTHONPATH='.'; pytest tests/unit/test_judge_engine.py