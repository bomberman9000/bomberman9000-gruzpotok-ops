"""
Интеграционная верификация tuning: миграция 003 + API + quality-report + export.

Требует пустую (одноразовую) БД Postgres:
  set TUNING_VERIFY_DATABASE_URL=postgresql://user:pass@host:5432/gruzpotok_verify
  py -m pytest tests/test_tuning_verification_integration.py -v

Без переменной тест пропускается — CI остаётся зелёным.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

# Статические проверки — всегда выполняются
def test_migration_003_sql_uses_if_not_exists():
    p = Path(__file__).resolve().parents[1] / "app" / "db" / "migrations" / "003_review_reason_codes.sql"
    text = p.read_text(encoding="utf-8")
    assert "ADD COLUMN IF NOT EXISTS" in text
    assert "review_reason_codes" in text
    assert "feedback_reason_codes" in text
    assert "CREATE INDEX IF NOT EXISTS" in text


@pytest.mark.skipif(
    not os.getenv("TUNING_VERIFY_DATABASE_URL"),
    reason="Set TUNING_VERIFY_DATABASE_URL to an empty Postgres DB (see docs/AI_TUNING_VERIFICATION.md)",
)
def test_full_tuning_verification_flow(monkeypatch):
    import psycopg2
    from fastapi.testclient import TestClient

    url = os.environ["TUNING_VERIFY_DATABASE_URL"]
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("INTERNAL_AUTH_ENABLED", "false")
    monkeypatch.delenv("INTERNAL_AUTH_TOKEN", raising=False)

    from app.core.config import get_settings

    get_settings.cache_clear()

    from app.db.migrate import run_migrations

    conn = psycopg2.connect(url)
    try:
        cur = conn.cursor()
        cur.execute("DROP SCHEMA IF EXISTS public CASCADE")
        cur.execute("CREATE SCHEMA public")
        conn.commit()
        cur.close()

        applied1 = run_migrations(conn)
        assert any("001" in v for v in applied1), applied1
        assert any("003" in v for v in applied1), applied1
        applied2 = run_migrations(conn)
        assert applied2 == [], f"ожидалась идемпотентность runner, got {applied2}"

        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'ai_reviews'
              AND column_name = 'review_reason_codes'
            """
        )
        assert int(cur.fetchone()[0]) == 1
        cur.execute(
            """
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'ai_feedback'
              AND column_name = 'feedback_reason_codes'
            """
        )
        assert int(cur.fetchone()[0]) == 1
        cur.close()

        # Повторное «накатывание» только DDL из файла 003 (как ручной re-run) — не должно падать
        p003 = (
            Path(__file__).resolve().parents[1]
            / "app"
            / "db"
            / "migrations"
            / "003_review_reason_codes.sql"
        )
        raw = p003.read_text(encoding="utf-8")
        import sqlparse

        from app.db.migrate import _sql_without_line_comments

        cur = conn.cursor()
        for stmt in sqlparse.split(raw):
            s = _sql_without_line_comments(stmt)
            if not s:
                continue
            cur.execute(s)
        conn.commit()
        cur.close()

        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO ai_calls (request_id, endpoint, normalized_status, user_input_json)
            VALUES ('tuning-verify-req', 'claim_review', 'ok', '{}'::jsonb)
            RETURNING id
            """
        )
        call_id = int(cur.fetchone()[0])
        conn.commit()
        cur.close()
    finally:
        conn.close()

    from app.main import app

    client = TestClient(app)
    rj = client.post(
        f"/api/v1/internal/ai/calls/{call_id}/reject",
        json={"reason": "verification", "reason_codes": ["weak_citations"]},
    )
    assert rj.status_code == 200, rj.text

    d = client.get(f"/api/v1/internal/ai/calls/{call_id}")
    assert d.status_code == 200
    rev = d.json().get("review") or {}
    assert "weak_citations" in (rev.get("review_reason_codes") or [])

    hist = client.get("/api/v1/internal/ai/calls?limit=5")
    assert hist.status_code == 200
    rows = hist.json()
    assert any(
        "weak_citations" in (x.get("review_reason_codes") or []) for x in rows if x.get("id") == call_id
    )

    qr = client.get("/api/v1/internal/ai/quality-report")
    assert qr.status_code == 200
    by_reason = (qr.json().get("breakdown") or {}).get("by_reason") or []
    assert any(x.get("reason") == "weak_citations" for x in by_reason)

    ex = client.get("/api/v1/internal/ai/export/problem-cases?limit=50&rejected_only=true")
    assert ex.status_code == 200
    items = ex.json().get("items") or []
    assert any("weak_citations" in (it.get("reasons") or []) for it in items)
