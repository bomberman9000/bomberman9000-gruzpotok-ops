from unittest.mock import patch

from fastapi.testclient import TestClient

from app.services.ai.call_detail_enrichment import human_ai_differs
from app.services.ai.review_presentation import build_review_ui_payload


def test_human_ai_diff_edited():
    call = {"id": 1, "response_summary": "A"}
    rev = {"operator_action": "edited", "final_text": "B"}
    assert human_ai_differs(call, rev) is True


def test_review_ui_payload():
    call = {"id": 7, "response_summary": "sug"}
    ui = build_review_ui_payload(call, None)
    assert ui["suggested_text"] == "sug"
    assert ui["editable_text"] == "sug"
    assert ui["review_status_badge"] == "pending"
    assert len(ui["operator_actions"]) == 3


@patch("app.api.ai_history_routes.get_review_by_call_id")
@patch("app.api.ai_history_routes.get_ai_call_by_id")
@patch("app.api.ai_history_routes.list_feedback_for_request")
def test_history_detail_with_review(mock_fb, mock_get, mock_rev, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
    from app.core.config import get_settings

    get_settings.cache_clear()
    mock_get.return_value = {
        "id": 42,
        "created_at": "2020-01-01",
        "request_id": "rid",
        "endpoint": "query",
        "user_input_json": {},
        "normalized_status": "ok",
        "llm_invoked": True,
        "citations_count": 0,
        "response_summary": "AI out",
        "latency_ms": 1,
        "is_error": False,
        "raw_meta_json": {},
        "raw_data_json": {},
    }
    mock_fb.return_value = [{"useful": False}]
    mock_rev.return_value = {
        "id": 1,
        "operator_action": "edited",
        "final_text": "Human",
        "ai_call_id": 42,
    }
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/internal/ai/calls/42")
    assert r.status_code == 200
    body = r.json()
    assert body["human_ai_diff"] is True
    assert body["effective_outcome"] == "edited"
    assert body["feedback_summary"]["useful_false"] == 1
    assert body["review_ui"]["review_status_badge"] == "edited"
