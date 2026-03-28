from unittest.mock import patch

from fastapi.testclient import TestClient


@patch("app.api.ai_review_routes.get_analytics")
def test_analytics_endpoint(mock_ga, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
    from app.core.config import get_settings

    get_settings.cache_clear()
    mock_ga.return_value = {
        "total_calls": 10,
        "total_feedback": 3,
        "useful_rate": 0.5,
        "correct_rate": None,
        "llm_invoked_rate": 0.8,
        "unavailable_rate": 0.1,
        "insufficient_data_rate": 0.05,
        "by_persona": {"legal": 5},
        "by_endpoint": {"/query": 10},
        "by_status": {"ok": 8},
        "by_operator_action": {"accepted": 2},
        "top_negative_scenarios": [],
        "top_positive_scenarios": [],
        "period": {"date_from": None, "date_to": None},
    }
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/internal/ai/analytics")
    assert r.status_code == 200
    assert r.json()["total_calls"] == 10
