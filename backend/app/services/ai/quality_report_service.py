from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings
from app.db.pool import get_conn
from app.services.ai.analytics_service import get_analytics
from app.services.ai.tuning_hints import derive_quality_tuning_hints

logger = logging.getLogger(__name__)


def _wc_params(
    date_from: str | None, date_to: str | None
) -> tuple[str, list[Any]]:
    wc = "1=1"
    params: list[Any] = []
    if date_from:
        wc += " AND c.created_at >= %s::timestamptz"
        params.append(date_from)
    if date_to:
        wc += " AND c.created_at <= %s::timestamptz"
        params.append(date_to)
    return wc, params


def get_quality_report(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """
    Агрегаты для внутреннего quality review: сбои, правки оператора, сигналы «нужны данные / промпт».
    """
    s = get_settings()
    base = get_analytics(date_from=date_from, date_to=date_to)
    out: dict[str, Any] = {
        "period": {"date_from": date_from, "date_to": date_to},
        "aggregate": {
            "total_calls": base.get("total_calls"),
            "by_status": base.get("by_status"),
            "by_endpoint": base.get("by_endpoint"),
            "llm_invoked_rate": base.get("llm_invoked_rate"),
            "insufficient_data_rate": base.get("insufficient_data_rate"),
            "unavailable_rate": base.get("unavailable_rate"),
            "by_operator_action": base.get("by_operator_action"),
        },
        "top_failure_patterns": [],
        "top_edited_patterns": [],
        "top_rejected_patterns": [],
        "cases_needing_better_data": [],
        "cases_needing_prompt_or_rule_tuning": [],
        "breakdown": {
            "by_reason": [],
            "by_persona_reason": [],
            "by_scenario_reason": [],
            "by_operator_action_reason": [],
        },
        "top_edited_reasons": [],
        "top_rejected_reasons": [],
        "top_insufficient_data_scenarios": [],
        "tuning_hints": {},
    }
    if not s.database_url:
        out["note"] = "database_not_configured"
        out["tuning_hints"] = derive_quality_tuning_hints(out)
        return out

    wc, params = _wc_params(date_from, date_to)
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT COALESCE(c.endpoint, ''), COUNT(*) AS n
                FROM ai_calls c
                WHERE {wc} AND (c.is_error OR c.normalized_status IN ('unavailable', 'invalid_upstream', 'upstream_error'))
                GROUP BY 1 ORDER BY n DESC LIMIT 15
                """,
                params,
            )
            out["top_failure_patterns"] = [
                {"endpoint": str(a), "count": int(n)} for a, n in cur.fetchall()
            ]

            cur.execute(
                f"""
                SELECT COALESCE(c.endpoint, ''), COUNT(*) AS n
                FROM ai_reviews r
                JOIN ai_calls c ON c.id = r.ai_call_id
                WHERE {wc} AND r.operator_action = 'edited'
                GROUP BY 1 ORDER BY n DESC LIMIT 15
                """,
                params,
            )
            out["top_edited_patterns"] = [
                {"endpoint": str(a), "count": int(n)} for a, n in cur.fetchall()
            ]

            cur.execute(
                f"""
                SELECT COALESCE(c.endpoint, ''), COUNT(*) AS n
                FROM ai_reviews r
                JOIN ai_calls c ON c.id = r.ai_call_id
                WHERE {wc} AND r.operator_action = 'rejected'
                GROUP BY 1 ORDER BY n DESC LIMIT 15
                """,
                params,
            )
            out["top_rejected_patterns"] = [
                {"endpoint": str(a), "count": int(n)} for a, n in cur.fetchall()
            ]

            cur.execute(
                f"""
                SELECT COALESCE(c.endpoint, ''), COUNT(*) AS n
                FROM ai_calls c
                WHERE {wc} AND c.normalized_status = 'insufficient_data'
                GROUP BY 1 ORDER BY n DESC LIMIT 15
                """,
                params,
            )
            out["cases_needing_better_data"] = [
                {"endpoint": str(a), "count": int(n)} for a, n in cur.fetchall()
            ]

            cur.execute(
                f"""
                WITH rev AS (
                    SELECT ai_call_id, operator_action FROM ai_reviews
                ),
                agg AS (
                    SELECT
                        c.endpoint,
                        COUNT(*)::float AS n_calls,
                        SUM(CASE WHEN c.normalized_status = 'insufficient_data' THEN 1 ELSE 0 END)::float AS n_id,
                        SUM(CASE WHEN r.operator_action = 'edited' THEN 1 ELSE 0 END)::float AS n_ed,
                        SUM(CASE WHEN r.operator_action = 'rejected' THEN 1 ELSE 0 END)::float AS n_rj
                    FROM ai_calls c
                    LEFT JOIN rev r ON r.ai_call_id = c.id
                    WHERE {wc}
                    GROUP BY c.endpoint
                )
                SELECT endpoint,
                    n_calls,
                    n_id / NULLIF(n_calls, 0) AS insufficient_share,
                    (n_ed + n_rj) / NULLIF(n_calls, 0) AS edit_reject_share
                FROM agg
                WHERE n_calls >= 3
                ORDER BY GREATEST(
                    COALESCE(n_id / NULLIF(n_calls, 0), 0),
                    COALESCE((n_ed + n_rj) / NULLIF(n_calls, 0), 0)
                ) DESC
                LIMIT 12
                """,
                params,
            )
            for row in cur.fetchall():
                ep, n_calls, ins_sh, er_sh = row
                reasons = []
                if ins_sh and float(ins_sh) >= 0.15:
                    reasons.append("high_insufficient_data_share")
                if er_sh and float(er_sh) >= 0.2:
                    reasons.append("high_edit_or_reject_share")
                out["cases_needing_prompt_or_rule_tuning"].append(
                    {
                        "endpoint": str(ep or ""),
                        "calls": int(n_calls),
                        "insufficient_data_share": float(ins_sh) if ins_sh is not None else None,
                        "edited_or_rejected_share": float(er_sh) if er_sh is not None else None,
                        "heuristic_reasons": reasons,
                    }
                )

            cur.execute(
                f"""
                SELECT elem AS reason, COUNT(*)::int AS n
                FROM ai_reviews r
                JOIN ai_calls c ON c.id = r.ai_call_id
                CROSS JOIN LATERAL jsonb_array_elements_text(r.review_reason_codes) AS elem
                WHERE {wc} AND jsonb_array_length(r.review_reason_codes) > 0
                GROUP BY elem ORDER BY n DESC LIMIT 30
                """,
                params,
            )
            out["breakdown"]["by_reason"] = [
                {"reason": str(a), "count": int(n)} for a, n in cur.fetchall()
            ]

            cur.execute(
                f"""
                SELECT COALESCE(c.persona, ''), elem AS reason, COUNT(*)::int AS n
                FROM ai_reviews r
                JOIN ai_calls c ON c.id = r.ai_call_id
                CROSS JOIN LATERAL jsonb_array_elements_text(r.review_reason_codes) AS elem
                WHERE {wc} AND jsonb_array_length(r.review_reason_codes) > 0
                GROUP BY 1, 2 ORDER BY n DESC LIMIT 40
                """,
                params,
            )
            out["breakdown"]["by_persona_reason"] = [
                {"persona": str(a), "reason": str(b), "count": int(n)} for a, b, n in cur.fetchall()
            ]

            cur.execute(
                f"""
                SELECT COALESCE(c.user_input_json->>'kind', ''), elem AS reason, COUNT(*)::int AS n
                FROM ai_reviews r
                JOIN ai_calls c ON c.id = r.ai_call_id
                CROSS JOIN LATERAL jsonb_array_elements_text(r.review_reason_codes) AS elem
                WHERE {wc} AND jsonb_array_length(r.review_reason_codes) > 0
                GROUP BY 1, 2 ORDER BY n DESC LIMIT 40
                """,
                params,
            )
            out["breakdown"]["by_scenario_reason"] = [
                {"scenario": str(a), "reason": str(b), "count": int(n)} for a, b, n in cur.fetchall()
            ]

            cur.execute(
                f"""
                SELECT r.operator_action, elem AS reason, COUNT(*)::int AS n
                FROM ai_reviews r
                JOIN ai_calls c ON c.id = r.ai_call_id
                CROSS JOIN LATERAL jsonb_array_elements_text(r.review_reason_codes) AS elem
                WHERE {wc} AND jsonb_array_length(r.review_reason_codes) > 0
                GROUP BY 1, 2 ORDER BY n DESC LIMIT 40
                """,
                params,
            )
            out["breakdown"]["by_operator_action_reason"] = [
                {"operator_action": str(a), "reason": str(b), "count": int(n)} for a, b, n in cur.fetchall()
            ]

            cur.execute(
                f"""
                SELECT COALESCE(c.endpoint, ''), elem AS reason, COUNT(*)::int AS n
                FROM ai_reviews r
                JOIN ai_calls c ON c.id = r.ai_call_id
                CROSS JOIN LATERAL jsonb_array_elements_text(r.review_reason_codes) AS elem
                WHERE {wc} AND r.operator_action = 'edited' AND jsonb_array_length(r.review_reason_codes) > 0
                GROUP BY 1, 2 ORDER BY n DESC LIMIT 25
                """,
                params,
            )
            out["top_edited_reasons"] = [
                {"endpoint": str(a), "reason": str(b), "count": int(n)} for a, b, n in cur.fetchall()
            ]

            cur.execute(
                f"""
                SELECT COALESCE(c.endpoint, ''), elem AS reason, COUNT(*)::int AS n
                FROM ai_reviews r
                JOIN ai_calls c ON c.id = r.ai_call_id
                CROSS JOIN LATERAL jsonb_array_elements_text(r.review_reason_codes) AS elem
                WHERE {wc} AND r.operator_action = 'rejected' AND jsonb_array_length(r.review_reason_codes) > 0
                GROUP BY 1, 2 ORDER BY n DESC LIMIT 25
                """,
                params,
            )
            out["top_rejected_reasons"] = [
                {"endpoint": str(a), "reason": str(b), "count": int(n)} for a, b, n in cur.fetchall()
            ]

            cur.execute(
                f"""
                SELECT COALESCE(c.user_input_json->>'kind', ''), COALESCE(c.endpoint, ''), COUNT(*)::int AS n
                FROM ai_calls c
                WHERE {wc} AND c.normalized_status = 'insufficient_data'
                GROUP BY 1, 2 ORDER BY n DESC LIMIT 25
                """,
                params,
            )
            out["top_insufficient_data_scenarios"] = [
                {"scenario": str(a), "endpoint": str(b), "count": int(n)} for a, b, n in cur.fetchall()
            ]

            cur.close()
    except Exception:
        logger.exception("get_quality_report failed")
    out["tuning_hints"] = derive_quality_tuning_hints(out)
    return out
