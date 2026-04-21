from src.schemas.policy import Policy, PolicyEvaluationResult
from src.schemas.workflow import WorkflowState


def collect_judge_results(
    state: WorkflowState,
    policies: list[tuple[Policy, PolicyEvaluationResult]],
    judge_engine,
) -> dict[str, object]:
    results: dict[str, object] = {}
    for policy, evaluation in policies:
        if evaluation.judge_required and not evaluation.triggered:
            results[policy.id] = judge_engine.judge(
                policy=policy,
                response=state.final_response,
                retrieved_context=state.retrieved_context,
            )
    return results

