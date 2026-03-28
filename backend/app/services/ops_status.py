from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.db.pool import get_conn
from app.services import observability


def ping_database() -> bool:
    s = get_settings()
    if not s.database_url:
        return False
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
        return True
    except Exception:
        return False


def review_queue_size() -> int:
    s = get_settings()
    if not s.database_url:
        return 0
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT COUNT(*) FROM ai_calls c
                LEFT JOIN ai_reviews r ON r.ai_call_id = c.id
                WHERE r.id IS NULL
                """
            )
            n = int(cur.fetchone()[0])
            cur.close()
        return n
    except Exception:
        return 0


def operator_ui_build_present() -> bool:
    s = get_settings()
    if not s.operator_ui_dist:
        return False
    p = Path(s.operator_ui_dist) / "index.html"
    return p.is_file()


def build_ops_status() -> dict[str, Any]:
    s = get_settings()
    snap = observability.snapshot()
    db_ok = ping_database()
    return {
        "service": "gruzpotok-backend",
        "internal_auth": {
            "enabled": bool(s.internal_auth_enabled),
            "token_configured": bool((s.internal_auth_token or "").strip()),
        },
        "database": {"configured": bool(s.database_url), "reachable": db_ok},
        "rag": {
            "last_reachable": snap.get("last_rag_available"),
            "last_error": snap.get("last_rag_error"),
            "last_error_at": snap.get("last_rag_error_at"),
        },
        "queue": {"unreviewed_calls": review_queue_size()},
        "operator_ui": {
            "static_dir": s.operator_ui_dist,
            "index_present": operator_ui_build_present(),
            "ui_require_auth_env": bool(s.ui_require_auth),
        },
        "calls_processed": snap.get("total_ai_calls"),
    }
