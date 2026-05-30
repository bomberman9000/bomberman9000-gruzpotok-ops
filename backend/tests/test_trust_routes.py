from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.delenv("INTERNAL_AUTH_ENABLED", raising=False)
    monkeypatch.delenv("INTERNAL_AUTH_TOKEN", raising=False)
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    return TestClient(app)


@pytest.fixture()
def authed_client(monkeypatch):
    monkeypatch.setenv("INTERNAL_AUTH_ENABLED", "true")
    monkeypatch.setenv("INTERNAL_AUTH_TOKEN", "test-secret")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    return TestClient(app)


# ── Public endpoint ────────────────────────────────────────────────────────────

def test_trust_public_valid(client):
    r = client.get("/api/v1/trust/profile/company/7712345678")
    assert r.status_code == 200
    data = r.json()
    assert data["subject_type"] == "company"
    assert data["subject_id"] == "7712345678"
    assert data["status"] in ("fresh", "stale", "empty", "pending", "failed")
    assert isinstance(data["positives"], list)
    assert isinstance(data["warnings"], list)


def test_trust_public_invalid_type(client):
    r = client.get("/api/v1/trust/profile/banana/123")
    assert r.status_code == 422


def test_trust_public_all_subject_types(client):
    for t in ("company", "carrier", "shipper", "user", "claim", "freight"):
        r = client.get(f"/api/v1/trust/profile/{t}/test-id-123")
        assert r.status_code == 200, f"Failed for subject_type={t}"


def test_trust_public_does_not_expose_internal_fields(client):
    r = client.get("/api/v1/trust/profile/company/7712345678")
    assert r.status_code == 200
    data = r.json()
    assert "source" not in data
    assert "internal_flags" not in data
    assert "agent_run_id" not in data
    assert "report_version" not in data
    assert "refresh_count_24h" not in data


def test_trust_public_deterministic(client):
    r1 = client.get("/api/v1/trust/profile/company/7712345678")
    r2 = client.get("/api/v1/trust/profile/company/7712345678")
    assert r1.json()["trust_score"] == r2.json()["trust_score"]
    assert r1.json()["trust_level"] == r2.json()["trust_level"]


def test_trust_public_no_token_required(authed_client):
    r = authed_client.get("/api/v1/trust/profile/company/7712345678")
    assert r.status_code == 200


# ── Internal endpoint ──────────────────────────────────────────────────────────

def test_trust_internal_requires_token_when_enabled(authed_client):
    r = authed_client.get("/api/v1/internal/ai/trust/profile/company/123")
    assert r.status_code == 401


def test_trust_internal_ok_with_token(authed_client):
    r = authed_client.get(
        "/api/v1/internal/ai/trust/profile/company/123",
        headers={"X-Internal-Token": "test-secret"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "internal_flags" in data
    assert "source" in data
    assert "report_version" in data
    assert "refresh_count_24h" in data


def test_trust_internal_includes_extra_fields(client):
    r = client.get("/api/v1/internal/ai/trust/profile/company/123")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["internal_flags"], list)
    assert data["source"] == "p1_deterministic_stub"
    assert data["report_version"] == "0.1"
    assert data["refresh_count_24h"] == 0


def test_trust_internal_invalid_type(client):
    r = client.get("/api/v1/internal/ai/trust/profile/banana/123")
    assert r.status_code == 422


# ── Refresh stub ───────────────────────────────────────────────────────────────

def test_trust_refresh_stub(client):
    r = client.post(
        "/api/v1/internal/ai/trust/refresh",
        json={"subject_type": "company", "subject_id": "7712345678"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["queued"] is False
    assert data["status"] == "stub"
    assert data["run_id"] is None


def test_trust_refresh_invalid_type(client):
    r = client.post(
        "/api/v1/internal/ai/trust/refresh",
        json={"subject_type": "banana", "subject_id": "123"},
    )
    assert r.status_code == 422


# ── Profile shape ──────────────────────────────────────────────────────────────

def test_trust_profile_shape(client):
    r = client.get("/api/v1/trust/profile/freight/order-999")
    assert r.status_code == 200
    data = r.json()
    required = {
        "subject_type", "subject_id", "status", "positives", "warnings",
        "can_refresh", "is_premium", "full_report",
    }
    assert required.issubset(data.keys())
    assert data["can_refresh"] is False
    assert data["is_premium"] is False
    assert data["full_report"] is None
