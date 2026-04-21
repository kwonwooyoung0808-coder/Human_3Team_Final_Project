from fastapi.testclient import TestClient

from src.main import app


def test_evaluate_normal_response() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/evaluate",
            json={
                "run_id": "run_test_normal",
                "input": "normal test",
                "response": "{\"answer\": \"This is supported by context.\"}",
                "context": {"workflow_name": "governance_workflow", "user_id": "demo_user"},
                "retrieved_context": ["This is supported by context."],
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["has_violation"] is False
    assert body["final_action"] == "LOG"

