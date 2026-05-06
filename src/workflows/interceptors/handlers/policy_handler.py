from src.schemas.policy import Policy, PolicyEvaluationResult
from src.schemas.workflow import WorkflowState
from src.utils.yaml_loader import load_policies


def collect_policy_results(
    state: WorkflowState,
    policy_engine,
    policy_dir: str,
) -> list[tuple[Policy, PolicyEvaluationResult]]:
    response = state.generated_response or state.final_response or ""
    results: list[tuple[Policy, PolicyEvaluationResult]] = []
    # 정책을 우선순위(숫자가 높을수록 높음)에 따라 내림차순 정렬
    policies = sorted(load_policies(policy_dir), key=lambda p: p.priority, reverse=True)
    
    for policy in policies:
        evaluation = policy_engine.evaluate_policy(
            policy=policy,
            response=response,
            context=state.context,
            retrieved_context=state.retrieved_context,
        )
        results.append((policy, evaluation))

        # 현재 정책이 확실하게 차단(BLOCK)되었고 LLM 판단(Judge)도 필요 없다면,
        # 후속(우선순위가 낮은) 정책은 평가하지 않고 즉시 종료 (Short-Circuit)
        if evaluation.triggered and evaluation.recommended_action == "BLOCK" and not evaluation.judge_required:
            break

    return results
