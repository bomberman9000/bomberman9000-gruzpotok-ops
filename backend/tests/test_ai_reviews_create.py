from unittest.mock import patch

from fastapi.testclient import TestClient


@patch("app.api.ai_review_routes.get_review_by_id")
@patch("app.api.ai_review_routes.insert_review_manual")
@patch("app.api.ai_review_routes.get_ai_call_by_id")
def test_create_review(mock_call, mock_insert, mock_getrid, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
    from app.core.config import get_settings

    get_settings.cache_clear()
    mock_call.return_value = {"id": 1, "request_id": "r1"}
    mock_insert.return_value = 99
    mock_getrid.return_value = {"id": 99, "ai_call_id": 1, "operator_action": "ignored"}
    from app.main import app

    client = TestClient(app)
    r = client.post(
        "/api/v1/internal/ai/reviews",
        json={
            "ai_call_id": 1,
            "request_id": "r1",
            "operator_action": "ignored",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["review"]["id"] == 99


@patch("app.api.ai_review_routes.upsert_review")
@patch("app.api.ai_review_routes.get_ai_call_by_id")
def test_accept_call(mock_call, mock_up, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
    from app.core.config import get_settings

    get_settings.cache_clear()
    mock_call.return_value = {
        "id": 3,
        "request_id": "r3",
        "response_summary": "AI text",
        "normalized_status": "ok",
        "user_input_json": {},
    }
    mock_up.return_value = 5
    from app.main import app

    client = TestClient(app)
    r = client.post("/api/v1/internal/ai/calls/3/accept", json={})
    assert r.status_code == 200
    assert mock_up.called
    args, kwargs = mock_up.call_args
    assert kwargs["operator_action"] == "accepted"
    assert kwargs["final_text"] == "AI text"
