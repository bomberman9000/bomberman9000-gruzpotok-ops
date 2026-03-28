from unittest.mock import patch

from fastapi.testclient import TestClient


@patch("app.api.ai_review_routes.build_review_queue")
def test_review_queue_endpoint(mock_q, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
    from app.core.config import get_settings

    get_settings.cache_clear()
    mock_q.return_value = {
        "items": [
            {
                "call_id": 1,
                "priority_score": 100.0,
                "priority_reasons": ["persona=legal"],
            }
        ],
        "total_in_pool": 1,
        "limit": 50,
        "offset": 0,
        "pool_limit": 5000,
        "filters": {},
    }
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/internal/ai/review-queue")
    assert r.status_code == 200
    data = r.json()
    assert data["items"][0]["call_id"] == 1
    assert data["items"][0]["priority_score"] == 100.0


@patch("app.services.ai.review_queue.fetch_queue_pool_for_scoring")
def test_review_queue_sorts_by_score(mock_fetch):
    mock_fetch.return_value = [
        {
            "id": 10,
            "request_id": "a",
            "endpoint": "e",
            "persona": "legal",
            "mode": None,
            "normalized_status": "ok",
            "llm_invoked": True,
            "response_summary": "x",
            "created_at": "2020-01-01",
            "review_id": None,
            "review_operator_action": None,
            "has_negative_feedback": False,
            "raw_data_json": {"raw_response": {"risk_level": "high"}},
        },
        {
            "id": 11,
            "request_id": "b",
            "endpoint": "e",
            "persona": "logistics",
            "mode": None,
            "normalized_status": "ok",
            "llm_invoked": False,
            "response_summary": "y",
            "created_at": "2020-01-02",
            "review_id": None,
            "review_operator_action": None,
            "has_negative_feedback": False,
            "raw_data_json": {},
        },
    ]
    from app.services.ai.review_queue import build_review_queue

    out = build_review_queue(
        date_from=None,
        date_to=None,
        scenario=None,
        persona=None,
        status=None,
        llm_invoked=None,
        reviewed=None,
        limit=10,
        offset=0,
        pool_limit=100,
    )
    assert out["items"][0]["call_id"] == 10
    assert out["items"][0]["priority_score"] >= out["items"][1]["priority_score"]
