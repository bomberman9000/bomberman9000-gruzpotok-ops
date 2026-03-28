from unittest.mock import patch

from fastapi.testclient import TestClient


@patch("app.api.ai_ops_hardening_routes.export_call_bundle", return_value={"ai_call": {"id": 1}})
def test_export_call(mock_exp, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    r = TestClient(app).get("/api/v1/internal/ai/export/call/1")
    assert r.status_code == 200
    assert "attachment" in r.headers.get("content-disposition", "")


@patch("app.api.ai_ops_hardening_routes.export_analytics_bundle", return_value={"analytics": {}})
def test_export_analytics(mock_a, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    r = TestClient(app).get("/api/v1/internal/ai/export/analytics")
    assert r.status_code == 200
