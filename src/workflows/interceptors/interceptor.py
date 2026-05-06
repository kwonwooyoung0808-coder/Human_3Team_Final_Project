from types import SimpleNamespace

import ollama as _ollama

from src.core.config import get_settings
from src.engines.action_engine import ActionEngine
from src.engines.judge_engine import JudgeEngine
from src.engines.policy_engine import PolicyEngine
from src.engines.violation_engine import ViolationEngine
from src.schemas.workflow import WorkflowState
from src.utils.yaml_loader import load_policies
from src.workflows.state import (
    apply_action,
    apply_judge_results,
    apply_policy_results,
    apply_violations,
)

class _OllamaClient:
    """ollama 패키지 기반 LLM 래퍼 (langchain 없이 LangGraph 워크플로와 통합)"""

    def __init__(self, model: str, temperature: float, base_url: str):
        self.model = model
        self.temperature = temperature
        self.base_url = base_url

    def invoke(self, prompt: str) -> SimpleNamespace:
        result = _ollama.generate(
            model=self.model,
            prompt=prompt,
            options={"temperature": self.temperature},
        )
        return SimpleNamespace(content=result["response"])

def evaluate_final_response(state: WorkflowState) -> WorkflowState:
    settings = get_settings()
    response = state.generated_response or state.final_response or ""

    policy_engine = PolicyEngine()
    llm = _OllamaClient(
        model=settings.ollama_model,
        temperature=settings.ollama_temperature,
        base_url=settings.ollama_url,
    )
    judge_engine = JudgeEngine(settings.prompt_dir, llm_client=llm)
    violation_engine = ViolationEngine()
    action_engine = ActionEngine()

    policies = load_policies(settings.policy_dir)

    policy_results = []
    judge_results = {}
    violations = []
    final_action = None

    for policy in policies:
        evaluation = policy_engine.evaluate_policy(
            policy=policy,
            response=response,
            context=state.context,
            retrieved_context=state.retrieved_context,
        )
        policy_results.append((policy, evaluation))

        judge_res = None
        if evaluation.judge_required and not evaluation.triggered:
            judge_res = judge_engine.judge(
                policy=policy,
                response=response,
                retrieved_context=state.retrieved_context,
            )
            judge_results[policy.id] = judge_res

        violation = violation_engine.from_policy_result(
            run_id=state.run_id,
            policy=policy,
            result=evaluation,
            judge_result=judge_res,
            response=response,
        )

        if violation:
            violations.append(violation)
            action = action_engine.decide(
                run_id=state.run_id,
                response=response,
                violations=[violation]
            )

            if action.action_type == "BLOCK":
                final_action = action
                break

    if final_action is None:
        final_action = action_engine.decide(
            run_id=state.run_id,
            response=response,
            violations=violations
        )

    state = apply_policy_results(state, policy_results)
    state = apply_judge_results(state, judge_results)
    state = apply_violations(state, violations)
    state = apply_action(state, final_action)

    return state
