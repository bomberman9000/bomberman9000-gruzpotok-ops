from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings
from app.db.pool import get_conn

logger = logging.getLogger(__name__)


def get_analytics(
    *,
    date_from: str | None,
    date_to: str | None,
) -> dict[str, Any]:
    s = get_settings()
    out: dict[str, Any] = {
        "total_calls": 0,
        "total_feedback": 0,
        "useful_rate": None,
        "correct_rate": None,
        "llm_invoked_rate": None,
        "unavailable_rate": None,
        "insufficient_data_rate": None,
        "by_persona": {},
        "by_endpoint": {},
        "by_status": {},
        "by_operator_action": {},
        "top_negative_scenarios": [],
        "top_positive_scenarios": [],
        "period": {"date_from": date_from, "date_to": date_to},
    }
    if not s.database_url:
        return out

    wc_calls = "1=1"
    wc_fb = "1=1"
    params_c: list[Any] = []
    params_f: list[Any] = []
    if date_from:
        wc_calls += " AND c.created_at >= %s::timestamptz"
        params_c.append(date_from)
        wc_fb += " AND f.created_at >= %s::timestamptz"
        params_f.append(date_from)
    if date_to:
        wc_calls += " AND c.created_at <= %s::timestamptz"
        params_c.append(date_to)
        wc_fb += " AND f.created_at <= %s::timestamptz"
        params_f.append(date_to)

    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM ai_calls c WHERE {wc_calls}", params_c)
            out["total_calls"] = int(cur.fetchone()[0])

            cur.execute(f"SELECT COUNT(*) FROM ai_feedback f WHERE {wc_fb}", params_f)
            out["total_feedback"] = int(cur.fetchone()[0])

            cur.execute(
                f"""
                SELECT
                    SUM(CASE WHEN f.useful THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0),
                    SUM(CASE WHEN f.correct IS TRUE THEN 1 ELSE 0 END)::float / NULLIF(SUM(CASE WHEN f.correct IS NOT NULL THEN 1 ELSE 0 END), 0)
                FROM ai_feedback f WHERE {wc_fb}
                """,
                params_f,
            )
            ur, cr = cur.fetchone()
            out["useful_rate"] = float(ur) if ur is not None else None
            out["correct_rate"] = float(cr) if cr is not None else None

            cur.execute(
                f"""
                SELECT
                    SUM(CASE WHEN c.llm_invoked IS TRUE THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0),
                    SUM(CASE WHEN c.normalized_status = 'unavailable' THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0),
                    SUM(CASE WHEN c.normalized_status = 'insufficient_data' THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0)
                FROM ai_calls c WHERE {wc_calls}
                """,
                params_c,
            )
            lr, ura, idr = cur.fetchone()
            out["llm_invoked_rate"] = float(lr) if lr is not None else None
            out["unavailable_rate"] = float(ura) if ura is not None else None
            out["insufficient_data_rate"] = float(idr) if idr is not None else None

            cur.execute(
                f"SELECT COALESCE(persona, ''), COUNT(*) FROM ai_calls c WHERE {wc_calls} GROUP BY 1",
                params_c,
            )
            out["by_persona"] = {str(a or "unknown"): int(b) for a, b in cur.fetchall()}

            cur.execute(
                f"SELECT endpoint, COUNT(*) FROM ai_calls c WHERE {wc_calls} GROUP BY endpoint",
                params_c,
            )
            out["by_endpoint"] = {str(a): int(b) for a, b in cur.fetchall()}

            cur.execute(
                f"SELECT normalized_status, COUNT(*) FROM ai_calls c WHERE {wc_calls} GROUP BY normalized_status",
                params_c,
            )
            out["by_status"] = {str(a): int(b) for a, b in cur.fetchall()}

            rparams: list[Any] = []
            rw = "1=1"
            if date_from:
                rw += " AND r.created_at >= %s::timestamptz"
                rparams.append(date_from)
            if date_to:
                rw += " AND r.created_at <= %s::timestamptz"
                rparams.append(date_to)
            cur.execute(
                f"SELECT operator_action, COUNT(*) FROM ai_reviews r WHERE {rw} GROUP BY operator_action",
                rparams,
            )
            out["by_operator_action"] = {str(a): int(b) for a, b in cur.fetchall()}

            cur.execute(
                f"""
                SELECT COALESCE(c.endpoint, ''), COALESCE(c.persona, ''), COUNT(*) AS n
                FROM ai_calls c
                JOIN ai_feedback f ON f.request_id = c.request_id AND f.useful = FALSE
                WHERE {wc_calls}
                GROUP BY 1, 2 ORDER BY n DESC LIMIT 10
                """,
                params_c,
            )
            out["top_negative_scenarios"] = [
                {"endpoint": a, "persona": b, "count": int(n)} for a, b, n in cur.fetchall()
            ]

            cur.execute(
                f"""
                SELECT COALESCE(c.endpoint, ''), COALESCE(c.persona, ''), COUNT(*) AS n
                FROM ai_calls c
                JOIN ai_feedback f ON f.request_id = c.request_id AND f.useful = TRUE
                WHERE {wc_calls}
                GROUP BY 1, 2 ORDER BY n DESC LIMIT 10
                """,
                params_c,
            )
            out["top_positive_scenarios"] = [
                {"endpoint": a, "persona": b, "count": int(n)} for a, b, n in cur.fetchall()
            ]

            cur.close()
        return out
    except Exception:
        logger.exception("get_analytics failed")
        return out
