from src.schemas.workflow import EvaluateRequest, WorkflowState


def generate_workflow_state(request: EvaluateRequest) -> WorkflowState:
    final_response = request.response or f"Generated response for: {request.input}"
    return WorkflowState(
        run_id=request.run_id,
        user_input=request.input,
        final_response=final_response,
        context=request.context,
        retrieved_context=request.retrieved_context,
    )

