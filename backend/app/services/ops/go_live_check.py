from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.services.export_bundle import export_analytics_bundle
from app.services.ops_status import (
    build_ops_status,
    operator_ui_build_present,
    ping_database,
    review_queue_size,
)
from app.services import observability


def _export_sanity() -> tuple[bool, str]:
    s = get_settings()
    if not s.database_url:
        return True, "skipped_no_database_url"
    try:
        export_analytics_bundle(date_from=None, date_to=None)
        return True, "analytics_bundle_ok"
    except Exception as e:
        return False, f"export_failed: {e!s}"


def _alerts_configured() -> tuple[bool, str]:
    s = get_settings()
    if (s.alert_webhook_url or "").strip():
        return True, "webhook_url_set"
    tok = (s.alert_telegram_bot_token or "").strip()
    cid = (s.alert_telegram_chat_id or "").strip()
    if tok and cid:
        return True, "telegram_configured"
    return False, "no_webhook_or_telegram_env"


def build_go_live_check() -> dict[str, Any]:
    """
    Чеклист перед controlled rollout: env, auth, БД, RAG-снимок, UI, очередь, экспорт, алерты.
    """
    s = get_settings()
    snap = observability.snapshot()
    db_ok = ping_database()
    qn = review_queue_size()
    exp_ok, exp_detail = _export_sanity()
    alerts_ok, alerts_detail = _alerts_configured()

    checks: list[dict[str, Any]] = [
        {
            "id": "env_database_url",
            "ok": bool(s.database_url),
            "detail": "DATABASE_URL задан для истории и аналитики",
        },
        {
            "id": "env_rag_api_base",
            "ok": bool((s.rag_api_base_url or "").strip()),
            "detail": f"RAG_API_BASE_URL={s.rag_api_base_url!r}",
        },
        {
            "id": "auth_config_consistent",
            "ok": (not s.internal_auth_enabled)
            or (bool((s.internal_auth_token or "").strip())),
            "detail": "INTERNAL_AUTH_ENABLED требует непустой INTERNAL_AUTH_TOKEN",
        },
        {
            "id": "database_reachable",
            "ok": (not s.database_url) or db_ok,
            "detail": "ping SELECT 1" if s.database_url else "DATABASE_URL пуст — dev",
        },
        {
            "id": "rag_last_reachable",
            "ok": bool(snap.get("last_rag_available", True)),
            "detail": f"last_rag_error={snap.get('last_rag_error')}",
        },
        {
            "id": "operator_ui_build",
            "ok": operator_ui_build_present() or not (s.operator_ui_dist or "").strip(),
            "detail": "OPERATOR_UI_DIST с index.html или не задан",
        },
        {
            "id": "queue_sanity",
            "ok": True,
            "detail": f"unreviewed_calls={qn} (информационно)",
        },
        {
            "id": "export_works",
            "ok": exp_ok,
            "detail": exp_detail,
        },
        {
            "id": "alerts_configured",
            "ok": alerts_ok,
            "detail": alerts_detail,
        },
    ]

    critical_ids = {
        "env_rag_api_base",
        "auth_config_consistent",
        "database_reachable",
        "export_works",
    }
    optional_ids = {"alerts_configured", "queue_sanity", "operator_ui_build"}
    all_critical_ok = all(c["ok"] for c in checks if c["id"] in critical_ids)
    rollout_ok = all(c["ok"] for c in checks if c["id"] not in optional_ids)
    return {
        "all_ok": rollout_ok,
        "all_checks_green": all(c["ok"] for c in checks),
        "all_critical_ok": all_critical_ok,
        "checks": checks,
        "ops_status": build_ops_status(),
        "notes": [
            "alerts_configured=false допустим на этапе dev; для prod задайте ALERT_WEBHOOK_URL или Telegram.",
            "rag_last_reachable отражает последний вызов gateway; при cold start может быть True без реального ping.",
        ],
    }
