from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.schemas.trust import TrustLevel, TrustProfileInternal, TrustStatus


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clear_cache():
    from app.services.trust import cache as trust_cache
    trust_cache.clear()
    yield
    trust_cache.clear()


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


def _make_profile(
    subject_type: str = "company",
    subject_id: str = "123",
    trust_score: int = 85,
    trust_level: TrustLevel = TrustLevel.excellent,
    status: TrustStatus = TrustStatus.fresh,
    expires_at: str | None = None,
) -> TrustProfileInternal:
    now = datetime.now(tz=timezone.utc)
    return TrustProfileInternal(
        subject_type=subject_type,
        subject_id=subject_id,
        trust_score=trust_score,
        trust_level=trust_level,
        status=status,
        verdict="Можно работать",
        positives=["Работает 7 лет"],
        warnings=[],
        checked_at=now.isoformat(),
        expires_at=expires_at or (now + timedelta(hours=24)).isoformat(),
        can_refresh=False,
        is_premium=False,
        full_report=None,
        source="test_source",
        report_version="1.0",
        internal_flags=["test_flag"],
        agent_run_id="run-uuid-1",
        refresh_count_24h=0,
    )


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


def test_trust_public_consistent(client):
    r1 = client.get("/api/v1/trust/profile/company/7712345678")
    r2 = client.get("/api/v1/trust/profile/company/7712345678")
    assert r1.json()["status"] == r2.json()["status"]


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


def test_trust_internal_includes_schema_fields(client):
    r = client.get("/api/v1/internal/ai/trust/profile/company/123")
    assert r.status_code == 200
    data = r.json()
    assert "internal_flags" in data
    assert "source" in data
    assert "report_version" in data
    assert "refresh_count_24h" in data
    assert isinstance(data["internal_flags"], list)


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


# ── P2: DB storage logic ───────────────────────────────────────────────────────

def test_profile_not_found_returns_empty(client):
    with patch("app.services.trust.db_repository.get_profile", return_value=None):
        r = client.get("/api/v1/trust/profile/company/nonexistent-999")
    assert r.status_code == 200
    assert r.json()["status"] == "empty"
    assert r.json()["trust_score"] is None


def test_profile_fresh(client):
    profile = _make_profile(status=TrustStatus.fresh)
    with patch("app.services.trust.db_repository.get_profile", return_value=profile):
        r = client.get("/api/v1/trust/profile/company/123")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "fresh"
    assert data["trust_score"] == 85
    assert data["trust_level"] == "excellent"
    assert data["verdict"] == "Можно работать"


def test_profile_stale(client):
    past = (datetime.now(tz=timezone.utc) - timedelta(hours=1)).isoformat()
    profile = _make_profile(status=TrustStatus.stale, expires_at=past)
    with patch("app.services.trust.db_repository.get_profile", return_value=profile):
        r = client.get("/api/v1/trust/profile/company/123")
    assert r.status_code == 200
    assert r.json()["status"] == "stale"


def test_public_hides_internal_fields_with_db_profile(client):
    profile = _make_profile()
    with patch("app.services.trust.db_repository.get_profile", return_value=profile):
        r = client.get("/api/v1/trust/profile/company/123")
    data = r.json()
    assert "source" not in data
    assert "internal_flags" not in data
    assert "agent_run_id" not in data
    assert "report_version" not in data
    assert "refresh_count_24h" not in data


def test_internal_shows_all_fields_with_db_profile(client):
    profile = _make_profile()
    with patch("app.services.trust.db_repository.get_profile", return_value=profile):
        r = client.get("/api/v1/internal/ai/trust/profile/company/123")
    data = r.json()
    assert data["source"] == "test_source"
    assert data["report_version"] == "1.0"
    assert data["internal_flags"] == ["test_flag"]
    assert data["agent_run_id"] == "run-uuid-1"
    assert data["refresh_count_24h"] == 0


def test_cache_hit_skips_db(client):
    profile = _make_profile()
    with patch("app.services.trust.db_repository.get_profile", return_value=profile) as mock_db:
        client.get("/api/v1/trust/profile/company/cache-test-id")
        client.get("/api/v1/trust/profile/company/cache-test-id")
    assert mock_db.call_count == 1


def test_cache_miss_after_refresh(client):
    profile = _make_profile(subject_id="refresh-test-id")
    with patch("app.services.trust.db_repository.get_profile", return_value=profile) as mock_db:
        client.get("/api/v1/trust/profile/company/refresh-test-id")
        client.post(
            "/api/v1/internal/ai/trust/refresh",
            json={"subject_type": "company", "subject_id": "refresh-test-id"},
        )
        client.get("/api/v1/trust/profile/company/refresh-test-id")
    assert mock_db.call_count == 2


# ── P2: DB repository unit ─────────────────────────────────────────────────────

def test_normalize_subject_id():
    from app.services.trust.db_repository import normalize_subject_id
    assert normalize_subject_id("  7712345678  ") == "7712345678"
    assert normalize_subject_id("ABC-123") == "abc-123"


def test_resolve_status_fresh():
    from app.services.trust.db_repository import _resolve_status
    future = datetime.now(tz=timezone.utc) + timedelta(hours=24)
    assert _resolve_status("fresh", future) == TrustStatus.fresh


def test_resolve_status_stale_by_expires_at():
    from app.services.trust.db_repository import _resolve_status
    past = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    assert _resolve_status("fresh", past) == TrustStatus.stale


def test_resolve_status_no_expires_at():
    from app.services.trust.db_repository import _resolve_status
    assert _resolve_status("empty", None) == TrustStatus.empty


# ── P2: Cache unit ─────────────────────────────────────────────────────────────

def test_cache_set_get():
    from app.services.trust import cache as c
    c.set("k1", "value1", ttl_seconds=60)
    assert c.get("k1") == "value1"


def test_cache_miss():
    from app.services.trust import cache as c
    assert c.get("nonexistent") is None


def test_cache_delete():
    from app.services.trust import cache as c
    c.set("k2", "v2", ttl_seconds=60)
    c.delete("k2")
    assert c.get("k2") is None


def test_cache_ttl_expired(monkeypatch):
    import time
    from app.services.trust import cache as c
    base = time.monotonic()
    c.set("k3", "v3", ttl_seconds=1)
    monkeypatch.setattr(time, "monotonic", lambda: base + 3)
    assert c.get("k3") is None


def test_cache_key_format():
    from app.services.trust import cache as c
    assert c.cache_key("company", "123") == "trust:profile:company:123"


# ── Migration check ────────────────────────────────────────────────────────────

def test_migration_not_destructive():
    from pathlib import Path
    sql = (Path(__file__).parent.parent / "app/db/migrations/004_trust_profiles.sql").read_text()
    for bad in ("DROP TABLE", "DELETE FROM", "TRUNCATE", "ALTER TABLE"):
        assert bad.upper() not in sql.upper(), f"Destructive SQL found: {bad}"


def test_migration_idempotent_keywords():
    from pathlib import Path
    sql = (Path(__file__).parent.parent / "app/db/migrations/004_trust_profiles.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS" in sql
    assert "CREATE INDEX IF NOT EXISTS" in sql


# ── P3: Internal write path ─────────────────────────────────────────────────────

_WRITE_URL = "/api/v1/internal/ai/trust/profile/company/777"


def _write_body(
    trust_score: int = 85,
    trust_level: str = "excellent",
    checked_at: str | None = None,
    expires_at: str | None = None,
    **overrides,
) -> dict:
    now = datetime.now(tz=timezone.utc)
    body = {
        "trust_score": trust_score,
        "trust_level": trust_level,
        "verdict": "Можно работать",
        "positives": ["Работает 7 лет"],
        "warnings": [],
        "internal_flags": ["test_flag"],
        "source": "ai_agent",
        "report_version": "1.0",
        "agent_run_id": "run-uuid-1",
        "checked_at": checked_at or now.isoformat(),
        "expires_at": expires_at or (now + timedelta(hours=24)).isoformat(),
    }
    body.update(overrides)
    return body


def test_write_fresh_profile(client):
    with patch("app.services.trust.db_repository.upsert_profile") as mock_up:
        r = client.post(_WRITE_URL, json=_write_body())
    assert r.status_code == 200
    data = r.json()
    assert data["trust_score"] == 85
    assert data["trust_level"] == "excellent"
    assert data["status"] == "fresh"
    assert data["verdict"] == "Можно работать"
    assert mock_up.call_count == 1


def test_write_updates_existing(client):
    with patch("app.services.trust.db_repository.upsert_profile") as mock_up:
        r1 = client.post(_WRITE_URL, json=_write_body(trust_score=85))
        r2 = client.post(_WRITE_URL, json=_write_body(trust_score=42, trust_level="caution"))
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json()["trust_score"] == 42
    assert r2.json()["trust_level"] == "caution"
    assert mock_up.call_count == 2


def test_write_public_sees_safe_fields_only(client):
    written = _make_profile(subject_id="pub-id")
    with patch("app.services.trust.db_repository.upsert_profile"), \
         patch("app.services.trust.db_repository.get_profile", return_value=written):
        w = client.post("/api/v1/internal/ai/trust/profile/company/pub-id", json=_write_body())
        assert w.status_code == 200
        r = client.get("/api/v1/trust/profile/company/pub-id")
    assert r.status_code == 200
    data = r.json()
    for field in ("source", "internal_flags", "agent_run_id", "report_version", "refresh_count_24h"):
        assert field not in data


def test_write_internal_sees_full_fields(client):
    with patch("app.services.trust.db_repository.upsert_profile"):
        r = client.post(_WRITE_URL, json=_write_body())
    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "ai_agent"
    assert data["report_version"] == "1.0"
    assert data["internal_flags"] == ["test_flag"]
    assert data["agent_run_id"] == "run-uuid-1"
    assert "refresh_count_24h" in data


def test_write_invalid_score_rejected(client):
    with patch("app.services.trust.db_repository.upsert_profile") as mock_up:
        r = client.post(_WRITE_URL, json=_write_body(trust_score=150))
    assert r.status_code == 422
    assert mock_up.call_count == 0


def test_write_invalid_level_rejected(client):
    with patch("app.services.trust.db_repository.upsert_profile") as mock_up:
        r = client.post(_WRITE_URL, json=_write_body(trust_level="super_bad"))
    assert r.status_code == 422
    assert mock_up.call_count == 0


def test_write_expires_before_checked_rejected(client):
    now = datetime.now(tz=timezone.utc)
    body = _write_body(
        checked_at=now.isoformat(),
        expires_at=(now - timedelta(hours=1)).isoformat(),
    )
    with patch("app.services.trust.db_repository.upsert_profile") as mock_up:
        r = client.post(_WRITE_URL, json=body)
    assert r.status_code == 422
    assert mock_up.call_count == 0


def test_write_invalidates_cache(client):
    profile = _make_profile(subject_id="cache-write-id")
    with patch("app.services.trust.db_repository.get_profile", return_value=profile) as mock_db, \
         patch("app.services.trust.db_repository.upsert_profile"):
        client.get("/api/v1/trust/profile/company/cache-write-id")   # populates cache
        client.post(
            "/api/v1/internal/ai/trust/profile/company/cache-write-id",
            json=_write_body(),
        )                                                            # invalidates cache
        client.get("/api/v1/trust/profile/company/cache-write-id")   # cache miss -> DB again
    assert mock_db.call_count == 2
