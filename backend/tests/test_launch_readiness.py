from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.services.evals.runner import (
    DEFAULT_FIXTURES,
    _compare_envelope,
    _discover_cases,
    run_case,
)
from app.services.ops.go_live_check import build_go_live_check


def test_fixtures_load():
    cases = _discover_cases(DEFAULT_FIXTURES)
    assert len(cases) >= 3
    for _dir, inp, exp in cases:
        assert "path" in inp
        assert (
            "status_in" in exp
            or "status" in exp
            or exp.get("response_kind") == "pdf"
        )


def test_compare_envelope_pass():
    body = {
        "meta": {"endpoint": "claim_review", "latency_ms": 12, "llm_invoked": True},
        "data": {"status": "ok", "llm_invoked": True, "citations": [{"file_name": "a.pdf"}]},
    }
    exp = {
        "status_in": ["ok"],
        "min_citations": 1,
        "meta": {"endpoint_contains": "claim"},
    }
    r = _compare_envelope(body, exp)
    assert r["passed"] is True
    assert r["checks"]["status_match"] is True


def test_compare_envelope_review_heuristic():
    body = {
        "meta": {"endpoint": "claim_review", "latency_ms": 1},
        "data": {"status": "insufficient_data", "llm_invoked": False, "citations": []},
    }
    exp = {
        "status_in": ["ok", "insufficient_data"],
        "heuristics": {"review_needed_if_status": ["insufficient_data"]},
    }
    r = _compare_envelope(body, exp)
    assert r["checks"]["review_needed_heuristic"] is True


def test_go_live_check_structure():
    d = build_go_live_check()
    assert "checks" in d
    assert isinstance(d["checks"], list)
    assert "all_ok" in d
    ids = {c["id"] for c in d["checks"]}
    assert "database_reachable" in ids
    assert "rag_last_reachable" in ids


def test_go_live_endpoint(monkeypatch):
    monkeypatch.setenv("INTERNAL_AUTH_ENABLED", "false")
    monkeypatch.delenv("INTERNAL_AUTH_TOKEN", raising=False)
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    client = TestClient(app)
    r = client.get("/internal/ops/go-live-check")
    assert r.status_code == 200
    assert "checks" in r.json()


@patch("app.api.ai_ops_hardening_routes.get_quality_report")
def test_quality_report_endpoint(mock_qr, monkeypatch):
    monkeypatch.delenv("INTERNAL_AUTH_ENABLED", raising=False)
    from app.core.config import get_settings

    get_settings.cache_clear()
    mock_qr.return_value = {"aggregate": {"total_calls": 0}, "period": {}}
    from app.main import app

    client = TestClient(app)
    res = client.get("/api/v1/internal/ai/quality-report")
    assert res.status_code == 200
    assert res.json()["aggregate"]["total_calls"] == 0


def test_quality_report_service_empty_db(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.services.ai.quality_report_service import get_quality_report

    r = get_quality_report()
    assert r.get("note") == "database_not_configured"
    assert "aggregate" in r


@patch("app.services.notifications.alert_delivery.httpx.Client")
def test_alert_webhook_delivery(mock_client_cls, monkeypatch):
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://example.invalid/hook")
    monkeypatch.delenv("ALERT_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("ALERT_TELEGRAM_CHAT_ID", raising=False)
    from app.core.config import get_settings

    get_settings.cache_clear()

    inst = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = inst
    resp = MagicMock()
    resp.status_code = 200
    resp.content = b"{}"
    resp.json.return_value = {"ok": True}
    inst.post.return_value = resp

    from app.services.notifications.alert_delivery import deliver_high_priority_alert

    out = deliver_high_priority_alert("hello")
    assert "webhook" in out["attempted"]
    assert out["ok"] is True


@patch("app.services.notifications.high_priority.deliver_high_priority_alert")
def test_notify_hook_invokes_delivery(mock_deliver):
    from app.services.notifications.high_priority import notify_high_priority_hook

    notify_high_priority_hook("x")
    mock_deliver.assert_called_once_with("x")


@patch("app.services.evals.runner.httpx.Client")
def test_run_case_smoke(mock_client_cls):
    inst = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = inst
    resp = MagicMock()
    resp.status_code = 200
    resp.content = b"{}"
    resp.json.return_value = {
        "meta": {"endpoint": "claim_review", "latency_ms": 7},
        "data": {"status": "ok", "llm_invoked": True, "citations": []},
    }
    inst.post.return_value = resp

    inp = {
        "name": "t",
        "method": "POST",
        "path": "/api/v1/ai/claims/review",
        "body": {"claim_text": "x", "contract_context": "", "counterparty": "", "debug": False},
    }
    exp = {"status_in": ["ok"], "min_citations": 0, "meta": {"endpoint_contains": "claim"}}
    cr, cmp = run_case(base_url="http://127.0.0.1:8090", inp=inp, expected=exp)
    assert cr.ok is True
    assert cmp["passed"] is True


def test_fixture_json_valid():
    for p in DEFAULT_FIXTURES.rglob("input.json"):
        json.loads(p.read_text(encoding="utf-8"))
        json.loads((p.parent / "expected.json").read_text(encoding="utf-8"))
