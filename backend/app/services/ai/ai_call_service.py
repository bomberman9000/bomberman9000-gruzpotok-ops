from __future__ import annotations

import logging
from typing import Any

from psycopg2.extras import Json

from app.core.config import get_settings
from app.db.pool import get_conn
from app.schemas.unified import AIMeta, UnifiedAIResponse
from app.services import observability

logger = logging.getLogger(__name__)


def _summary_from_data(data: UnifiedAIResponse) -> str:
    parts: list[str] = []
    if data.summary:
        parts.append(str(data.summary)[:2000])
    elif data.answer:
        parts.append(str(data.answer)[:2000])
    elif data.draft_response_text:
        parts.append(str(data.draft_response_text)[:2000])
    elif data.user_message:
        parts.append(str(data.user_message)[:2000])
    return " | ".join(parts)[:8000]


def _is_error_status(status: str) -> bool:
    return status in ("unavailable", "invalid_upstream")


def record_ai_call(
    *,
    request_id: str,
    endpoint: str,
    meta: AIMeta,
    data: UnifiedAIResponse,
    user_input: dict[str, Any],
    latency_ms: int,
    rag_reachable: bool,
    rag_error: str | None,
) -> int | None:
    """Возвращает id записи или None при отключённой БД / ошибке записи."""
    observability.note_call_completed(
        normalized_status=data.status,
        rag_reachable=rag_reachable,
        rag_error=rag_error,
    )

    s = get_settings()
    if not s.database_url:
        return None

    meta_d = meta.model_dump()
    data_d = data.model_dump()
    # не дублируем огромные raw в логи при сериализации
    try:
        raw_meta_json = Json(meta_d)
        raw_data_json = Json(data_d)
        ui = Json(user_input or {})
    except Exception:
        return None

    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO ai_calls (
                    request_id, endpoint, persona, mode, user_input_json,
                    normalized_status, llm_invoked, citations_count, response_summary,
                    raw_meta_json, raw_data_json, latency_ms, is_error
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s
                ) RETURNING id
                """,
                (
                    request_id,
                    endpoint,
                    data.persona,
                    data.mode,
                    ui,
                    data.status,
                    data.llm_invoked,
                    len(data.citations or []),
                    _summary_from_data(data),
                    raw_meta_json,
                    raw_data_json,
                    int(latency_ms),
                    _is_error_status(data.status),
                ),
            )
            row = cur.fetchone()
            cur.close()
            return int(row[0]) if row else None
    except Exception:
        logger.exception("ai_calls insert failed request_id=%s", request_id)
        return None


def insert_feedback(
    *,
    request_id: str,
    useful: bool,
    correct: bool | None,
    comment: str,
    user_role: str,
    source_screen: str,
    feedback_reason_codes: list[str] | None = None,
) -> int | None:
    s = get_settings()
    if not s.database_url:
        return None
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM ai_calls WHERE request_id = %s ORDER BY created_at DESC LIMIT 1",
                (request_id,),
            )
            row = cur.fetchone()
            ai_call_id = int(row[0]) if row else None
            cur.execute(
                """
                INSERT INTO ai_feedback (
                    request_id, ai_call_id, useful, correct, comment, user_role, source_screen,
                    feedback_reason_codes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    request_id,
                    ai_call_id,
                    useful,
                    correct,
                    comment[:8000] if comment else None,
                    user_role[:500] if user_role else None,
                    source_screen[:500] if source_screen else None,
                    Json(feedback_reason_codes or []),
                ),
            )
            out = cur.fetchone()
            cur.close()
            return int(out[0]) if out else None
    except Exception:
        logger.exception("ai_feedback insert failed request_id=%s", request_id)
        return None


def count_ai_calls() -> int:
    s = get_settings()
    if not s.database_url:
        return 0
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM ai_calls")
            n = cur.fetchone()[0]
            cur.close()
            return int(n)
    except Exception:
        return 0


def list_ai_calls(
    *,
    persona: str | None = None,
    endpoint: str | None = None,
    status: str | None = None,
    llm_invoked: bool | None = None,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    scenario: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    reviewed_by: str | None = None,
    review_reason_code: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    s = get_settings()
    if not s.database_url:
        return []
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    join = " LEFT JOIN ai_reviews r_rev ON r_rev.ai_call_id = c.id"
    where: list[str] = ["1=1"]
    params: list[Any] = []
    if reviewed_by:
        where.append("r_rev.reviewed_by = %s")
        params.append(reviewed_by)
    if review_reason_code:
        where.append("r_rev.review_reason_codes @> %s::jsonb")
        params.append(Json([review_reason_code]))
    if persona:
        where.append("c.persona = %s")
        params.append(persona)
    if endpoint:
        where.append("c.endpoint = %s")
        params.append(endpoint)
    if status:
        where.append("c.normalized_status = %s")
        params.append(status)
    if llm_invoked is not None:
        where.append("c.llm_invoked = %s")
        params.append(llm_invoked)
    if date_from:
        where.append("c.created_at >= %s::timestamptz")
        params.append(date_from)
    if date_to:
        where.append("c.created_at <= %s::timestamptz")
        params.append(date_to)
    if scenario:
        where.append("(c.user_input_json->>'kind') ILIKE %s OR c.endpoint ILIKE %s")
        params.extend([f"%{scenario}%", f"%{scenario}%"])
    if entity_type and entity_id:
        et = entity_type.lower()
        if et == "claim":
            where.append("c.user_input_json->>'product_claim_id' = %s")
            params.append(entity_id)
        elif et == "load":
            where.append("c.user_input_json->>'product_load_id' = %s")
            params.append(entity_id)
        elif et == "document":
            where.append("c.user_input_json->>'product_document_id' = %s")
            params.append(entity_id)
    if q:
        pat = f"%{q}%"
        where.append(
            "(c.response_summary ILIKE %s OR c.request_id ILIKE %s OR c.user_input_json::text ILIKE %s)"
        )
        params.extend([pat, pat, pat])
    sql = f"""
        SELECT c.id, c.created_at, c.request_id, c.endpoint, c.persona, c.mode, c.normalized_status,
               c.llm_invoked, c.citations_count, c.response_summary, c.latency_ms, c.is_error, c.user_input_json,
               r_rev.operator_action AS review_operator_action,
               r_rev.review_reason_codes AS review_reason_codes
        FROM ai_calls c
        {join}
        WHERE {' AND '.join(where)}
        ORDER BY c.created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])
    try:
        from psycopg2.extras import RealDictCursor

        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()
        out: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            if d.get("created_at"):
                d["created_at"] = str(d["created_at"])
            rc = d.get("review_reason_codes")
            if isinstance(rc, str):
                import json

                try:
                    d["review_reason_codes"] = json.loads(rc)
                except Exception:
                    d["review_reason_codes"] = []
            elif rc is None:
                d["review_reason_codes"] = []
            out.append(d)
        return out
    except Exception:
        logger.exception("list_ai_calls failed")
        return []


def get_ai_call_by_id(call_id: int) -> dict[str, Any] | None:
    s = get_settings()
    if not s.database_url:
        return None
    try:
        from psycopg2.extras import RealDictCursor

        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                """
                SELECT id, created_at, request_id, endpoint, persona, mode, user_input_json,
                       normalized_status, llm_invoked, citations_count, response_summary,
                       raw_meta_json, raw_data_json, latency_ms, is_error
                FROM ai_calls WHERE id = %s
                """,
                (call_id,),
            )
            row = cur.fetchone()
            cur.close()
        if not row:
            return None
        d = dict(row)
        if d.get("created_at"):
            d["created_at"] = str(d["created_at"])
        return d
    except Exception:
        logger.exception("get_ai_call_by_id failed")
        return None


def get_ai_calls_by_request_id(request_id: str) -> list[dict[str, Any]]:
    s = get_settings()
    if not s.database_url:
        return []
    try:
        from psycopg2.extras import RealDictCursor

        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                """
                SELECT id, created_at, request_id, endpoint, persona, mode, user_input_json,
                       normalized_status, llm_invoked, citations_count, response_summary,
                       raw_meta_json, raw_data_json, latency_ms, is_error
                FROM ai_calls WHERE request_id = %s
                ORDER BY created_at DESC
                """,
                (request_id,),
            )
            rows = cur.fetchall()
            cur.close()
        out: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            if d.get("created_at"):
                d["created_at"] = str(d["created_at"])
            out.append(d)
        return out
    except Exception:
        logger.exception("get_ai_calls_by_request_id failed")
        return []


def list_feedback_for_request(request_id: str) -> list[dict[str, Any]]:
    s = get_settings()
    if not s.database_url:
        return []
    try:
        from psycopg2.extras import RealDictCursor

        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                """
                SELECT id, created_at, request_id, ai_call_id, useful, correct, comment, user_role, source_screen,
                       feedback_reason_codes
                FROM ai_feedback WHERE request_id = %s ORDER BY created_at DESC
                """,
                (request_id,),
            )
            rows = cur.fetchall()
            cur.close()
        out: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            if d.get("created_at"):
                d["created_at"] = str(d["created_at"])
            frc = d.get("feedback_reason_codes")
            if isinstance(frc, str):
                import json

                try:
                    d["feedback_reason_codes"] = json.loads(frc)
                except Exception:
                    d["feedback_reason_codes"] = []
            elif frc is None:
                d["feedback_reason_codes"] = []
            out.append(d)
        return out
    except Exception:
        logger.exception("list_feedback_for_request failed")
        return []
