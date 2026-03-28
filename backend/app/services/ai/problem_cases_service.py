from __future__ import annotations

import json
import logging
from typing import Any

from psycopg2.extras import RealDictCursor

from app.core.config import get_settings
from app.db.pool import get_conn
from app.services.ai.call_detail_enrichment import feedback_summary

logger = logging.getLogger(__name__)


def _scenario_label(ui: Any) -> str | None:
    if not isinstance(ui, dict):
        return None
    k = ui.get("kind")
    return str(k) if k else None


def export_problem_cases(
    *,
    date_from: str | None,
    date_to: str | None,
    persona: str | None,
    scenario: str | None,
    rejected_only: bool = False,
    edited_only: bool = False,
    insufficient_only: bool = False,
    limit: int = 200,
) -> dict[str, Any]:
    s = get_settings()
    if not s.database_url:
        return {"items": [], "note": "database_not_configured", "filters": {}}

    limit = max(1, min(limit, 500))
    where = ["1=1"]
    params: list[Any] = []
    if date_from:
        where.append("c.created_at >= %s::timestamptz")
        params.append(date_from)
    if date_to:
        where.append("c.created_at <= %s::timestamptz")
        params.append(date_to)
    if persona:
        where.append("c.persona = %s")
        params.append(persona)
    if scenario:
        where.append("(c.user_input_json->>'kind') ILIKE %s OR c.endpoint ILIKE %s")
        params.extend([f"%{scenario}%", f"%{scenario}%"])
    if insufficient_only:
        where.append("c.normalized_status = 'insufficient_data'")

    action_filter: list[str] = []
    if rejected_only:
        action_filter.append("r.operator_action = 'rejected'")
    if edited_only:
        action_filter.append("r.operator_action = 'edited'")
    if action_filter:
        where.append("(" + " OR ".join(action_filter) + ")")
    elif not insufficient_only:
        where.append(
            "(r.operator_action IN ('rejected','edited') OR c.normalized_status = 'insufficient_data')"
        )

    sql = f"""
        SELECT c.id, c.created_at, c.request_id, c.endpoint, c.persona, c.normalized_status,
               c.llm_invoked, c.citations_count, c.response_summary, c.user_input_json,
               r.operator_action AS review_operator_action,
               r.review_reason_codes AS review_reason_codes
        FROM ai_calls c
        LEFT JOIN ai_reviews r ON r.ai_call_id = c.id
        WHERE {' AND '.join(where)}
        ORDER BY c.created_at DESC
        LIMIT %s
    """
    params.append(limit)
    items: list[dict[str, Any]] = []
    try:
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
        for row in rows:
            d = dict(row)
            ui = d.get("user_input_json")
            if isinstance(ui, str):
                try:
                    ui = json.loads(ui)
                except Exception:
                    ui = {}
            rid = str(d.get("request_id") or "")
            fb = []
            fsum: dict[str, Any] = {}
            try:
                from app.services.ai.ai_call_service import list_feedback_for_request

                fb = list_feedback_for_request(rid)
                fsum = feedback_summary(fb)
            except Exception:
                pass
            rc = d.get("review_reason_codes")
            if isinstance(rc, str):
                try:
                    rc = json.loads(rc)
                except Exception:
                    rc = []
            elif rc is None:
                rc = []
            fb_codes: list[str] = []
            seen_c: set[str] = set()
            for f in fb:
                if not isinstance(f, dict):
                    continue
                for x in f.get("feedback_reason_codes") or []:
                    s = str(x)
                    if s and s not in seen_c:
                        seen_c.add(s)
                        fb_codes.append(s)
            items.append(
                {
                    "request_id": rid,
                    "endpoint": d.get("endpoint"),
                    "persona": d.get("persona"),
                    "scenario": _scenario_label(ui),
                    "normalized_status": d.get("normalized_status"),
                    "review_operator_action": d.get("review_operator_action"),
                    "reasons": rc,
                    "review_reason_codes": rc,
                    "citations_count": int(d.get("citations_count") or 0),
                    "llm_invoked": d.get("llm_invoked"),
                    "response_summary": d.get("response_summary"),
                    "feedback_summary": fsum,
                    "feedback_reason_codes": fb_codes,
                }
            )
    except Exception:
        logger.exception("export_problem_cases failed")
    return {
        "items": items,
        "filters": {
            "date_from": date_from,
            "date_to": date_to,
            "persona": persona,
            "scenario": scenario,
            "rejected_only": rejected_only,
            "edited_only": edited_only,
            "insufficient_only": insufficient_only,
            "limit": limit,
        },
    }
