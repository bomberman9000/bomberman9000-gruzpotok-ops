from fastapi.testclient import TestClient


def test_internal_routes_without_auth_when_disabled(monkeypatch):
    monkeypatch.delenv("INTERNAL_AUTH_ENABLED", raising=False)
    monkeypatch.delenv("INTERNAL_AUTH_TOKEN", raising=False)
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/internal/stats")
    assert r.status_code == 200


def test_internal_routes_401_when_enabled_no_header(monkeypatch):
    monkeypatch.setenv("INTERNAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("INTERNAL_AUTH_TOKEN", "secret-token")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/internal/stats")
    assert r.status_code == 401


def test_internal_routes_ok_with_token_header(monkeypatch):
    monkeypatch.setenv("INTERNAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("INTERNAL_AUTH_TOKEN", "secret-token")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/internal/stats", headers={"X-Internal-Token": "secret-token"})
    assert r.status_code == 200


def test_public_ai_not_blocked(monkeypatch):
    monkeypatch.setenv("INTERNAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("INTERNAL_AUTH_TOKEN", "secret-token")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    c = TestClient(app)
    # маршрут существует; без тела может быть 422, главное — не 401
    r = c.post("/api/v1/ai/feedback", json={})
    assert r.status_code != 401


def test_health_open_with_auth_enabled(monkeypatch):
    monkeypatch.setenv("INTERNAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("INTERNAL_AUTH_TOKEN", "secret-token")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    c = TestClient(app)
    assert c.get("/health").status_code == 200
    assert c.get("/ready").status_code == 200
