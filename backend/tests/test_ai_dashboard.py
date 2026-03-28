from unittest.mock import patch

from fastapi.testclient import TestClient


@patch("app.api.ai_operator_dashboard_routes.get_dashboard_summary")
def test_dashboard_endpoint(mock_dash, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
    from app.core.config import get_settings

    get_settings.cache_clear()
    mock_dash.return_value = {
        "total_calls_24h": 1,
        "total_calls_7d": 2,
        "review_queue_count": 0,
        "pending_high_priority_count": 0,
        "insufficient_data_count_24h": 0,
        "unavailable_count_24h": 0,
        "negative_feedback_count_7d": 0,
        "edited_or_rejected_count_7d": 0,
        "top_personas": [],
        "top_scenarios": [],
        "top_risk_panels": [],
        "health_snapshot": {},
        "period": {},
    }
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/internal/ai/dashboard")
    assert r.status_code == 200
    assert r.json()["total_calls_24h"] == 1
