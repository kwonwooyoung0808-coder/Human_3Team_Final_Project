from src.schemas.policy import Policy, PolicyEvaluationResult
from src.schemas.workflow import WorkflowState
from src.utils.yaml_loader import load_policies


def collect_policy_results(
    state: WorkflowState,
    policy_engine,
    policy_dir: str,
) -> list[tuple[Policy, PolicyEvaluationResult]]:
    results: list[tuple[Policy, PolicyEvaluationResult]] = []
    for policy in load_policies(policy_dir):
        results.append(
            (
                policy,
                policy_engine.evaluate_policy(
                    policy=policy,
                    response=state.final_response,
                    context=state.context,
                    retrieved_context=state.retrieved_context,
                ),
            )
        )
    return results

