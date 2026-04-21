from src.core.config import get_settings
from src.engines.action_engine import ActionEngine
from src.engines.judge_engine import JudgeEngine
from src.engines.policy_engine import PolicyEngine
from src.engines.violation_engine import ViolationEngine
from src.schemas.workflow import WorkflowState
from src.workflows.interceptors.handlers.action_handler import build_action_result
from src.workflows.interceptors.handlers.judge_handler import collect_judge_results
from src.workflows.interceptors.handlers.policy_handler import collect_policy_results


def evaluate_final_response(state: WorkflowState):
    settings = get_settings()
    policies = collect_policy_results(
        state=state,
        policy_engine=PolicyEngine(),
        policy_dir=settings.policy_dir,
    )
    judge_results = collect_judge_results(
        state=state,
        policies=policies,
        judge_engine=JudgeEngine(settings.prompt_dir),
    )

    violation_engine = ViolationEngine()
    violations = []
    for policy, result in policies:
        violation = violation_engine.from_policy_result(
            run_id=state.run_id,
            policy=policy,
            result=result,
            judge_result=judge_results.get(policy.id),
            response=state.final_response,
        )
        if violation:
            violations.append(violation)

    action = build_action_result(
        run_id=state.run_id,
        response=state.final_response,
        violations=violations,
        action_engine=ActionEngine(),
    )
    return violations, action

