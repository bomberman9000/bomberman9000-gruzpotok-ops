from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings
from app.db.pool import get_conn
from app.services import observability

logger = logging.getLogger(__name__)


def get_dashboard_summary(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """
    Агрегаты для операторского dashboard.
    Скользящие окна 24h / 7d фиксированы; date_from/date_to дополнительно задают «отчётный период»
    для части метрик (period в ответе).
    """
    s = get_settings()
    empty = _empty_dashboard(date_from, date_to)
    if not s.database_url:
        empty["health_snapshot"] = observability.snapshot()
        return empty

    try:
        with get_conn() as conn:
            cur = conn.cursor()

            cur.execute(
                """
                SELECT COUNT(*) FROM ai_calls
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                """
            )
            total_calls_24h = int(cur.fetchone()[0])

            cur.execute(
                """
                SELECT COUNT(*) FROM ai_calls
                WHERE created_at >= NOW() - INTERVAL '7 days'
                """
            )
            total_calls_7d = int(cur.fetchone()[0])

            cur.execute(
                """
                SELECT COUNT(*) FROM ai_calls c
                LEFT JOIN ai_reviews r ON r.ai_call_id = c.id
                WHERE r.id IS NULL
                """
            )
            review_queue_count = int(cur.fetchone()[0])

            cur.execute(
                """
                SELECT COUNT(*) FROM ai_calls c
                LEFT JOIN ai_reviews r ON r.ai_call_id = c.id
                WHERE r.id IS NULL
                  AND (
                    LOWER(COALESCE(c.persona, '')) IN ('legal', 'antifraud')
                    OR c.normalized_status = 'insufficient_data'
                    OR EXISTS (
                        SELECT 1 FROM ai_feedback f
                        WHERE f.request_id = c.request_id AND f.useful = FALSE
                    )
                  )
                """
            )
            pending_high_priority_count = int(cur.fetchone()[0])

            cur.execute(
                """
                SELECT COUNT(*) FROM ai_calls
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                  AND normalized_status = 'insufficient_data'
                """
            )
            insufficient_data_count_24h = int(cur.fetchone()[0])

            cur.execute(
                """
                SELECT COUNT(*) FROM ai_calls
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                  AND normalized_status = 'unavailable'
                """
            )
            unavailable_count_24h = int(cur.fetchone()[0])

            cur.execute(
                """
                SELECT COUNT(*) FROM ai_feedback
                WHERE created_at >= NOW() - INTERVAL '7 days'
                  AND useful = FALSE
                """
            )
            negative_feedback_count_7d = int(cur.fetchone()[0])

            cur.execute(
                """
                SELECT COUNT(*) FROM ai_reviews
                WHERE created_at >= NOW() - INTERVAL '7 days'
                  AND operator_action IN ('edited', 'rejected')
                """
            )
            edited_or_rejected_count_7d = int(cur.fetchone()[0])

            cur.execute(
                """
                SELECT COALESCE(persona, 'unknown'), COUNT(*) AS n
                FROM ai_calls
                WHERE created_at >= NOW() - INTERVAL '7 days'
                GROUP BY 1 ORDER BY n DESC LIMIT 5
                """
            )
            top_personas = [{"persona": str(a), "count": int(b)} for a, b in cur.fetchall()]

            cur.execute(
                """
                SELECT COALESCE(NULLIF(TRIM(user_input_json->>'kind'), ''), '(none)'), COUNT(*) AS n
                FROM ai_calls
                WHERE created_at >= NOW() - INTERVAL '7 days'
                GROUP BY 1 ORDER BY n DESC LIMIT 5
                """
            )
            top_scenarios = [{"scenario": str(a), "count": int(b)} for a, b in cur.fetchall()]

            cur.execute(
                """
                SELECT COALESCE(c.endpoint, ''), COALESCE(c.persona, ''), COUNT(*) AS n
                FROM ai_calls c
                WHERE c.created_at >= NOW() - INTERVAL '7 days'
                  AND (c.raw_data_json->'raw_response'->>'risk_level') = 'high'
                GROUP BY 1, 2 ORDER BY n DESC LIMIT 5
                """
            )
            top_risk_panels = [
                {"endpoint": ep, "persona": pe, "risk_level": "high", "count": int(n)}
                for ep, pe, n in cur.fetchall()
            ]

            period_extra: dict[str, Any] = {}
            if date_from or date_to:
                wc = "1=1"
                pparams: list[Any] = []
                if date_from:
                    wc += " AND created_at >= %s::timestamptz"
                    pparams.append(date_from)
                if date_to:
                    wc += " AND created_at <= %s::timestamptz"
                    pparams.append(date_to)
                cur.execute(f"SELECT COUNT(*) FROM ai_calls WHERE {wc}", pparams)
                period_extra["calls_in_period"] = int(cur.fetchone()[0])

            cur.close()

        out: dict[str, Any] = {
            "total_calls_24h": total_calls_24h,
            "total_calls_7d": total_calls_7d,
            "review_queue_count": review_queue_count,
            "pending_high_priority_count": pending_high_priority_count,
            "insufficient_data_count_24h": insufficient_data_count_24h,
            "unavailable_count_24h": unavailable_count_24h,
            "negative_feedback_count_7d": negative_feedback_count_7d,
            "edited_or_rejected_count_7d": edited_or_rejected_count_7d,
            "top_personas": top_personas,
            "top_scenarios": top_scenarios,
            "top_risk_panels": top_risk_panels,
            "health_snapshot": observability.snapshot(),
            "period": {"date_from": date_from, "date_to": date_to, **period_extra},
        }
        return out
    except Exception:
        logger.exception("get_dashboard_summary failed")
        empty["health_snapshot"] = observability.snapshot()
        return empty


def _empty_dashboard(date_from: str | None, date_to: str | None) -> dict[str, Any]:
    return {
        "total_calls_24h": 0,
        "total_calls_7d": 0,
        "review_queue_count": 0,
        "pending_high_priority_count": 0,
        "insufficient_data_count_24h": 0,
        "unavailable_count_24h": 0,
        "negative_feedback_count_7d": 0,
        "edited_or_rejected_count_7d": 0,
        "top_personas": [],
        "top_scenarios": [],
        "top_risk_panels": [],
        "health_snapshot": observability.snapshot(),
        "period": {"date_from": date_from, "date_to": date_to},
    }
