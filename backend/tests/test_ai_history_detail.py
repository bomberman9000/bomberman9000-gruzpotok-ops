from unittest.mock import patch

from fastapi.testclient import TestClient


@patch("app.api.ai_history_routes.get_review_by_call_id")
@patch("app.api.ai_history_routes.get_ai_call_by_id")
@patch("app.api.ai_history_routes.list_feedback_for_request")
def test_history_detail_404(mock_fb, mock_get, mock_rev, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
    from app.core.config import get_settings

    get_settings.cache_clear()
    mock_get.return_value = None
    mock_rev.return_value = None
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/internal/ai/calls/99")
    assert r.status_code == 404


@patch("app.api.ai_history_routes.get_review_by_call_id")
@patch("app.api.ai_history_routes.get_ai_calls_by_request_id")
@patch("app.api.ai_history_routes.list_feedback_for_request")
def test_history_by_request(mock_fb, mock_rows, mock_rev, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
    from app.core.config import get_settings

    get_settings.cache_clear()
    mock_rows.return_value = [
        {
            "id": 1,
            "created_at": "2020-01-01T00:00:00",
            "request_id": "rid",
            "endpoint": "query",
            "user_input_json": {"product_claim_id": "c1"},
            "normalized_status": "ok",
            "llm_invoked": True,
            "citations_count": 0,
            "response_summary": "",
            "latency_ms": 1,
            "is_error": False,
            "raw_meta_json": {},
            "raw_data_json": {},
        }
    ]
    mock_fb.return_value = []
    mock_rev.return_value = None
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/internal/ai/calls/by-request/rid")
    assert r.status_code == 200
    body = r.json()
    assert body["entity"].get("product_claim_id") == "c1"
