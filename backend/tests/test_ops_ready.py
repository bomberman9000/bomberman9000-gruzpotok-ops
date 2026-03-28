from fastapi.testclient import TestClient


def test_ready_endpoint(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    r = TestClient(app).get("/ready")
    assert r.status_code == 200
    assert r.json().get("ready") is True


def test_ops_status(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    r = TestClient(app).get("/internal/ops/status")
    assert r.status_code == 200
    body = r.json()
    assert "internal_auth" in body
    assert "database" in body
