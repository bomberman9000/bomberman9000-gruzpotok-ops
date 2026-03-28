from __future__ import annotations

from typing import Any

from app.services.ai.priority_rules import risk_level_from_call_row, score_review_queue_item
from app.services.ai.review_service import fetch_queue_pool_for_scoring


def build_review_queue(
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
    pool_limit: int = 5000,
    review_reason_code: str | None = None,
) -> dict[str, Any]:
    """
    Приоритетная очередь: выборка до pool_limit строк, скоринг в Python, сортировка по score DESC.
    Пагинация limit/offset применяется после сортировки (ограничение pool_limit в docs).
    """
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    pool_limit = max(limit + offset, min(pool_limit, 10000))
    rows = fetch_queue_pool_for_scoring(
        date_from=date_from,
        date_to=date_to,
        scenario=scenario,
        persona=persona,
        status=status,
        llm_invoked=llm_invoked,
        reviewed=reviewed,
        review_reason_code=review_reason_code,
        pool_limit=pool_limit,
    )
    scored: list[tuple[float, list[str], dict[str, Any]]] = []
    for row in rows:
        rl = risk_level_from_call_row(row)
        has_review = row.get("review_id") is not None
        op = row.get("review_operator_action")
        score, reasons = score_review_queue_item(
            persona=row.get("persona"),
            mode=row.get("mode"),
            endpoint=row.get("endpoint"),
            normalized_status=row.get("normalized_status"),
            llm_invoked=row.get("llm_invoked"),
            risk_level=rl,
            has_negative_feedback=bool(row.get("has_negative_feedback")),
            has_review=has_review,
            operator_action=op,
        )
        scored.append((score, reasons, row))
    scored.sort(key=lambda t: (-t[0], -int(t[2].get("id") or 0)))
    total_scored = len(scored)
    page = scored[offset : offset + limit]
    items: list[dict[str, Any]] = []
    for score, reasons, row in page:
        rid = row.get("id")
        items.append(
            {
                "call_id": int(rid) if rid is not None else None,
                "request_id": row.get("request_id"),
                "endpoint": row.get("endpoint"),
                "persona": row.get("persona"),
                "mode": row.get("mode"),
                "normalized_status": row.get("normalized_status"),
                "llm_invoked": row.get("llm_invoked"),
                "response_summary": row.get("response_summary"),
                "created_at": row.get("created_at"),
                "review_id": row.get("review_id"),
                "review_operator_action": row.get("review_operator_action"),
                "review_reason_codes": row.get("review_reason_codes") or [],
                "has_negative_feedback": bool(row.get("has_negative_feedback")),
                "priority_score": score,
                "priority_reasons": reasons,
            }
        )
    return {
        "items": items,
        "total_in_pool": total_scored,
        "limit": limit,
        "offset": offset,
        "pool_limit": pool_limit,
        "filters": {
            "date_from": date_from,
            "date_to": date_to,
            "scenario": scenario,
            "persona": persona,
            "status": status,
            "llm_invoked": llm_invoked,
            "reviewed": reviewed,
            "review_reason_code": review_reason_code,
        },
    }
