from unittest.mock import patch

from fastapi.testclient import TestClient


@patch("app.api.ai_operator_dashboard_routes.build_call_timeline")
@patch("app.api.ai_operator_dashboard_routes.get_ai_call_by_id")
def test_timeline_404(mock_get, mock_tl, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
    from app.core.config import get_settings

    get_settings.cache_clear()
    mock_get.return_value = None
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/internal/ai/calls/99/timeline")
    assert r.status_code == 404


@patch("app.api.ai_operator_dashboard_routes.build_call_timeline")
@patch("app.api.ai_operator_dashboard_routes.get_ai_call_by_id")
def test_timeline_ok(mock_get, mock_tl, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
    from app.core.config import get_settings

    get_settings.cache_clear()
    mock_get.return_value = {"id": 1}
    mock_tl.return_value = [{"event_type": "ai_call_created", "timestamp": "t"}]
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/internal/ai/calls/1/timeline")
    assert r.status_code == 200
    assert r.json()["events"][0]["event_type"] == "ai_call_created"
