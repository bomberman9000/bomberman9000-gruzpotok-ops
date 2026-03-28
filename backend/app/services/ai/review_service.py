from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from psycopg2.extras import Json, RealDictCursor

from app.core.config import get_settings
from app.db.pool import get_conn

logger = logging.getLogger(__name__)

OperatorAction = str  # accepted | edited | rejected | ignored


def upsert_review(
    *,
    ai_call_id: int,
    request_id: str,
    operator_action: OperatorAction,
    operator_comment: str | None = None,
    final_text: str | None = None,
    final_status: str | None = None,
    reviewed_by: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    scenario: str | None = None,
    review_reason_codes: list[str] | None = None,
) -> int | None:
    s = get_settings()
    if not s.database_url:
        return None
    reviewed_at_dt = datetime.now(timezone.utc)
    rc_json = Json(review_reason_codes or [])
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO ai_reviews (
                    ai_call_id, request_id, entity_type, entity_id, scenario,
                    operator_action, operator_comment, final_text, final_status,
                    reviewed_by, reviewed_at, updated_at, review_reason_codes
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, NOW(), %s
                )
                ON CONFLICT (ai_call_id) DO UPDATE SET
                    updated_at = NOW(),
                    request_id = EXCLUDED.request_id,
                    entity_type = EXCLUDED.entity_type,
                    entity_id = EXCLUDED.entity_id,
                    scenario = EXCLUDED.scenario,
                    operator_action = EXCLUDED.operator_action,
                    operator_comment = EXCLUDED.operator_comment,
                    final_text = EXCLUDED.final_text,
                    final_status = EXCLUDED.final_status,
                    reviewed_by = EXCLUDED.reviewed_by,
                    reviewed_at = EXCLUDED.reviewed_at,
                    review_reason_codes = EXCLUDED.review_reason_codes
                RETURNING id
                """,
                (
                    ai_call_id,
                    request_id,
                    entity_type,
                    entity_id,
                    scenario,
                    operator_action,
                    operator_comment,
                    final_text,
                    final_status,
                    reviewed_by,
                    reviewed_at_dt,
                    rc_json,
                ),
            )
            row = cur.fetchone()
            cur.close()
            return int(row[0]) if row else None
    except Exception:
        logger.exception("upsert_review failed call_id=%s", ai_call_id)
        return None


def _serialize_review_row(d: dict[str, Any]) -> dict[str, Any]:
    for k in ("created_at", "updated_at", "reviewed_at"):
        if d.get(k):
            d[k] = str(d[k])
    rc = d.get("review_reason_codes")
    if isinstance(rc, str):
        import json

        try:
            d["review_reason_codes"] = json.loads(rc)
        except Exception:
            d["review_reason_codes"] = []
    elif rc is None:
        d["review_reason_codes"] = []
    return d


def get_review_by_id(review_id: int) -> dict[str, Any] | None:
    s = get_settings()
    if not s.database_url:
        return None
    try:
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM ai_reviews WHERE id = %s", (review_id,))
            row = cur.fetchone()
            cur.close()
        if not row:
            return None
        return _serialize_review_row(dict(row))
    except Exception:
        logger.exception("get_review_by_id")
        return None


def get_review_by_call_id(call_id: int) -> dict[str, Any] | None:
    s = get_settings()
    if not s.database_url:
        return None
    try:
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM ai_reviews WHERE ai_call_id = %s", (call_id,))
            row = cur.fetchone()
            cur.close()
        if not row:
            return None
        d = _serialize_review_row(dict(row))
        return d
    except Exception:
        logger.exception("get_review_by_call_id")
        return None


def list_reviews(
    *,
    ai_call_id: int | None = None,
    operator_action: str | None = None,
    review_reason_code: str | None = None,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    reviewed_by: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    scenario: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    s = get_settings()
    if not s.database_url:
        return []
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    where = ["1=1"]
    params: list[Any] = []
    if ai_call_id is not None:
        where.append("ai_call_id = %s")
        params.append(ai_call_id)
    if operator_action:
        where.append("operator_action = %s")
        params.append(operator_action)
    if reviewed_by:
        where.append("reviewed_by = %s")
        params.append(reviewed_by)
    if entity_type:
        where.append("entity_type = %s")
        params.append(entity_type)
    if entity_id:
        where.append("entity_id = %s")
        params.append(entity_id)
    if scenario:
        where.append("scenario ILIKE %s")
        params.append(f"%{scenario}%")
    if review_reason_code:
        where.append("review_reason_codes @> %s::jsonb")
        params.append(Json([review_reason_code]))
    if date_from:
        where.append("created_at >= %s::timestamptz")
        params.append(date_from)
    if date_to:
        where.append("created_at <= %s::timestamptz")
        params.append(date_to)
    if q:
        pat = f"%{q}%"
        where.append(
            "(operator_comment ILIKE %s OR request_id ILIKE %s OR CAST(ai_call_id AS TEXT) ILIKE %s)"
        )
        params.extend([pat, pat, pat])
    sql = f"SELECT * FROM ai_reviews WHERE {' AND '.join(where)} ORDER BY updated_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    try:
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
        return [_serialize_review_row(dict(r)) for r in rows]
    except Exception:
        logger.exception("list_reviews")
        return []


def insert_review_manual(
    *,
    ai_call_id: int,
    request_id: str,
    operator_action: str,
    operator_comment: str | None = None,
    final_text: str | None = None,
    final_status: str | None = None,
    reviewed_by: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    scenario: str | None = None,
    review_reason_codes: list[str] | None = None,
) -> int | None:
    return upsert_review(
        ai_call_id=ai_call_id,
        request_id=request_id,
        operator_action=operator_action,
        operator_comment=operator_comment,
        final_text=final_text,
        final_status=final_status,
        reviewed_by=reviewed_by,
        entity_type=entity_type,
        entity_id=entity_id,
        scenario=scenario,
        review_reason_codes=review_reason_codes,
    )


def _queue_filters(
    *,
    date_from: str | None,
    date_to: str | None,
    scenario: str | None,
    persona: str | None,
    status: str | None,
    llm_invoked: bool | None,
    reviewed: bool | None,
    review_reason_code: str | None = None,
) -> tuple[list[str], list[Any]]:
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
    if status:
        where.append("c.normalized_status = %s")
        params.append(status)
    if llm_invoked is not None:
        where.append("c.llm_invoked = %s")
        params.append(llm_invoked)
    if scenario:
        where.append("(c.user_input_json->>'kind') ILIKE %s OR c.endpoint ILIKE %s")
        params.extend([f"%{scenario}%", f"%{scenario}%"])
    if reviewed is True:
        where.append("r.id IS NOT NULL")
    elif reviewed is False:
        where.append("r.id IS NULL")
    if review_reason_code:
        where.append("r.review_reason_codes @> %s::jsonb")
        params.append(Json([review_reason_code]))
    return where, params


_QUEUE_SELECT = """
        SELECT
            c.*,
            r.id AS review_id,
            r.operator_action AS review_operator_action,
            r.review_reason_codes AS review_reason_codes,
            EXISTS (
                SELECT 1 FROM ai_feedback f
                WHERE f.request_id = c.request_id AND f.useful = FALSE
            ) AS has_negative_feedback,
            (SELECT BOOL_OR(f.useful) FROM ai_feedback f WHERE f.request_id = c.request_id) AS has_positive_feedback
        FROM ai_calls c
        LEFT JOIN ai_reviews r ON r.ai_call_id = c.id
        WHERE {where_clause}
"""


def fetch_queue_pool_for_scoring(
    *,
    date_from: str | None,
    date_to: str | None,
    scenario: str | None,
    persona: str | None,
    status: str | None,
    llm_invoked: bool | None,
    reviewed: bool | None,
    review_reason_code: str | None = None,
    pool_limit: int = 5000,
) -> list[dict[str, Any]]:
    """Кандидаты без ORDER BY — для приоритетной сортировки в Python (ограничение pool_limit)."""
    s = get_settings()
    if not s.database_url:
        return []
    where, params = _queue_filters(
        date_from=date_from,
        date_to=date_to,
        scenario=scenario,
        persona=persona,
        status=status,
        llm_invoked=llm_invoked,
        reviewed=reviewed,
        review_reason_code=review_reason_code,
    )
    pl = max(1, min(pool_limit, 10000))
    sql = _QUEUE_SELECT.format(where_clause=" AND ".join(where)) + " LIMIT %s"
    params = [*params, pl]
    try:
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
        out: list[dict[str, Any]] = []
        for row in rows:
            d = dict(row)
            if d.get("created_at"):
                d["created_at"] = str(d["created_at"])
            rc = d.get("review_reason_codes")
            if rc is None:
                d["review_reason_codes"] = []
            elif isinstance(rc, str):
                import json

                try:
                    d["review_reason_codes"] = json.loads(rc)
                except Exception:
                    d["review_reason_codes"] = []
            out.append(d)
        return out
    except Exception:
        logger.exception("fetch_queue_pool_for_scoring")
        return []


def fetch_queue_candidates(
    *,
    date_from: str | None,
    date_to: str | None,
    scenario: str | None,
    persona: str | None,
    status: str | None,
    llm_invoked: bool | None,
    reviewed: bool | None,
    limit: int,
    offset: int,
    review_reason_code: str | None = None,
) -> list[dict[str, Any]]:
    """Сырые строки ai_calls + флаги feedback/review (по дате создания)."""
    s = get_settings()
    if not s.database_url:
        return []
    where, params = _queue_filters(
        date_from=date_from,
        date_to=date_to,
        scenario=scenario,
        persona=persona,
        status=status,
        llm_invoked=llm_invoked,
        reviewed=reviewed,
        review_reason_code=review_reason_code,
    )

    sql = (
        _QUEUE_SELECT.format(where_clause=" AND ".join(where))
        + " ORDER BY c.created_at DESC LIMIT %s OFFSET %s"
    )
    params.extend([max(1, min(limit, 500)), max(0, offset)])
    try:
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
        out: list[dict[str, Any]] = []
        for row in rows:
            d = dict(row)
            if d.get("created_at"):
                d["created_at"] = str(d["created_at"])
            rc = d.get("review_reason_codes")
            if rc is None:
                d["review_reason_codes"] = []
            elif isinstance(rc, str):
                import json

                try:
                    d["review_reason_codes"] = json.loads(rc)
                except Exception:
                    d["review_reason_codes"] = []
            out.append(d)
        return out
    except Exception:
        logger.exception("fetch_queue_candidates")
        return []
