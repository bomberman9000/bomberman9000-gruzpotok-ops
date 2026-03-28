from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.services.export_bundle import (
    export_analytics_bundle,
    export_call_bundle,
    export_review_queue_bundle,
    json_bytes,
)
from app.services.ai.problem_cases_service import export_problem_cases
from app.services.ai.quality_report_service import get_quality_report
from app.services.notifications.high_priority import get_high_priority_bundle, notify_high_priority_hook

router = APIRouter(prefix="/api/v1/internal/ai", tags=["internal-ai-ops"])


@router.get("/notifications/high-priority")
def high_priority_notifications(
    limit: int = Query(default=30, ge=1, le=100),
    pool_limit: int = Query(default=2000, ge=100, le=10000),
) -> dict[str, Any]:
    return get_high_priority_bundle(limit=limit, pool_limit=pool_limit)


@router.get("/quality-report")
def quality_report(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
) -> dict[str, Any]:
    """Сводка качества для internal beta: сбои, правки, сигналы по данным/промпту."""
    return get_quality_report(date_from=date_from, date_to=date_to)


@router.post("/notifications/high-priority/emit-log")
def high_priority_emit_log(
    limit: int = Query(default=30, ge=1, le=100),
) -> dict[str, Any]:
    """Вручную прогнать текст алерта через hook (лог + webhook/Telegram при env)."""
    out = get_high_priority_bundle(limit=limit)
    notify_high_priority_hook(str(out.get("alert_text") or ""))
    return {"ok": True, "items_count": len(out.get("items") or [])}


@router.get("/export/call/{call_id}")
def export_call(call_id: int) -> Response:
    data = export_call_bundle(call_id)
    if not data:
        raise HTTPException(status_code=404, detail="ai_call not found")
    return Response(
        content=json_bytes(data),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="ai-call-{call_id}.json"'},
    )


@router.get("/export/review-queue")
def export_review_queue(
    scenario: str | None = Query(default=None),
    persona: str | None = Query(default=None),
    status: str | None = Query(default=None),
    llm_invoked: bool | None = Query(default=None),
    reviewed: bool | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    pool_limit: int = Query(default=5000, ge=100, le=10000),
    review_reason_code: str | None = Query(default=None),
) -> Response:
    data = export_review_queue_bundle(
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
    return Response(
        content=json_bytes(data),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="ai-review-queue.json"'},
    )


@router.get("/export/analytics")
def export_analytics(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
) -> Response:
    data = export_analytics_bundle(date_from=date_from, date_to=date_to)
    return Response(
        content=json_bytes(data),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="ai-analytics.json"'},
    )


@router.get("/export/problem-cases")
def export_problem_cases_route(
    rejected_only: bool = Query(default=False),
    edited_only: bool = Query(default=False),
    insufficient_only: bool = Query(default=False),
    persona: str | None = Query(default=None),
    scenario: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
) -> Response:
    data = export_problem_cases(
        date_from=date_from,
        date_to=date_to,
        persona=persona,
        scenario=scenario,
        rejected_only=rejected_only,
        edited_only=edited_only,
        insufficient_only=insufficient_only,
        limit=limit,
    )
    return Response(
        content=json_bytes(data),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="ai-problem-cases.json"'},
    )
