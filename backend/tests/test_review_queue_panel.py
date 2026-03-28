from unittest.mock import patch

from fastapi.testclient import TestClient


@patch("app.api.ai_operator_dashboard_routes.build_review_queue_panel")
def test_review_queue_panel_route(mock_b, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
    from app.core.config import get_settings

    get_settings.cache_clear()
    mock_b.return_value = {
        "items": [{"title": "x", "priority": 10.0, "reasons": [], "quick_actions": []}],
        "total_in_pool": 1,
    }
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/internal/ai/review-queue/panel")
    assert r.status_code == 200
    assert r.json()["items"][0]["priority"] == 10.0
