from src.schemas.judge import JudgeResult
from src.schemas.policy import Policy, PolicyEvaluationResult
from src.schemas.workflow import WorkflowState


def collect_judge_results(
    state: WorkflowState,
    policies: list[tuple[Policy, PolicyEvaluationResult]],
    judge_engine,
) -> dict[str, JudgeResult]:
    response = state.generated_response or state.final_response or ""
    results: dict[str, JudgeResult] = {}
    for policy, evaluation in policies:
        # [수정 1] 기존 조건 `not evaluation.triggered`를 제거.
        # rule이 triggered된 경우에도 judge_required=True이면 judge를 실행해야
        # hybrid / rule_triggered 정책에서 보조 판정이 누락되지 않음.
        # [수정 2] query=state.user_input 추가.
        # 기존에는 query를 전달하지 않아 프롬프트 내 user_query가 빈 문자열로
        # 렌더링되었고, CTX_001 등 query 기반 판정 품질에 영향을 미쳤음.
        if evaluation.judge_required:
            results[policy.id] = judge_engine.judge(
                policy=policy,
                response=response,
                retrieved_context=state.retrieved_context,
                query=state.user_input,
            )
    return results
