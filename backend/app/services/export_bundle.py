from __future__ import annotations

import json
from typing import Any

from app.services.ai.ai_call_service import get_ai_call_by_id, list_feedback_for_request
from app.services.ai.analytics_service import get_analytics
from app.services.ai.call_timeline_service import build_call_timeline
from app.services.ai.review_queue import build_review_queue
from app.services.ai.review_service import get_review_by_call_id


def export_call_bundle(call_id: int) -> dict[str, Any] | None:
    row = get_ai_call_by_id(call_id)
    if not row:
        return None
    rid = str(row.get("request_id") or "")
    fb = list_feedback_for_request(rid)
    rev = get_review_by_call_id(call_id)
    tl = build_call_timeline(call_id)
    return {
        "ai_call": row,
        "feedback": fb,
        "review": rev,
        "timeline": tl,
    }


def export_review_queue_bundle(
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
    pool_limit: int,
    review_reason_code: str | None = None,
) -> dict[str, Any]:
    return build_review_queue(
        date_from=date_from,
        date_to=date_to,
        scenario=scenario,
        persona=persona,
        status=status,
        llm_invoked=llm_invoked,
        reviewed=reviewed,
        limit=limit,
        offset=offset,
        pool_limit=pool_limit,
        review_reason_code=review_reason_code,
    )


def export_analytics_bundle(*, date_from: str | None, date_to: str | None) -> dict[str, Any]:
    return {
        "analytics": get_analytics(date_from=date_from, date_to=date_to),
    }


def json_bytes(data: dict[str, Any]) -> bytes:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str).encode("utf-8")
