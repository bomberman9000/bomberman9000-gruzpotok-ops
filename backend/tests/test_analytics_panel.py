from unittest.mock import patch

from fastapi.testclient import TestClient


@patch("app.api.ai_operator_dashboard_routes.build_analytics_panel")
def test_analytics_panel_route(mock_b, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
    from app.core.config import get_settings

    get_settings.cache_clear()
    mock_b.return_value = {"summary_cards": [], "charts_data": {}, "raw_analytics": {}}
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/internal/ai/analytics/panel")
    assert r.status_code == 200
    assert "summary_cards" in r.json()
