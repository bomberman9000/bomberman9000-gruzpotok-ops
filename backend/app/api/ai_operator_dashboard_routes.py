from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.services.ai.ai_call_service import get_ai_call_by_id
from app.services.ai.analytics_panel_service import build_analytics_panel
from app.services.ai.call_timeline_service import build_call_timeline
from app.services.ai.case_panel_service import (
    panel_for_claim,
    panel_for_document,
    panel_for_freight,
    panel_for_request,
)
from app.services.ai.dashboard_service import get_dashboard_summary
from app.services.ai.review_queue_panel_service import build_review_queue_panel

router = APIRouter(prefix="/api/v1/internal/ai", tags=["internal-ai-operator"])


@router.get("/dashboard")
def operator_dashboard(
    date_from: str | None = Query(default=None, description="Доп. фильтр периода для period.calls_in_period"),
    date_to: str | None = Query(default=None),
) -> dict[str, Any]:
    return get_dashboard_summary(date_from=date_from, date_to=date_to)


@router.get("/panels/claims/{claim_id}")
def panel_claim(claim_id: str) -> dict[str, Any]:
    return panel_for_claim(claim_id)


@router.get("/panels/freight/{load_id}")
def panel_freight(load_id: str) -> dict[str, Any]:
    return panel_for_freight(load_id)


@router.get("/panels/documents/{doc_id}")
def panel_document(doc_id: str) -> dict[str, Any]:
    return panel_for_document(doc_id)


@router.get("/panels/by-request/{request_id}")
def panel_by_request(request_id: str) -> dict[str, Any]:
    return panel_for_request(request_id)


@router.get("/review-queue/panel")
def review_queue_panel(
    scenario: str | None = Query(default=None),
    persona: str | None = Query(default=None),
    status: str | None = Query(default=None, description="normalized_status"),
    llm_invoked: bool | None = Query(default=None),
    reviewed: bool | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pool_limit: int = Query(default=5000, ge=100, le=10000),
    review_reason_code: str | None = Query(default=None),
) -> dict[str, Any]:
    return build_review_queue_panel(
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


@router.get("/analytics/panel")
def analytics_panel(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
) -> dict[str, Any]:
    return build_analytics_panel(date_from=date_from, date_to=date_to)


@router.get("/calls/{call_id}/timeline")
def call_timeline(call_id: int) -> dict[str, Any]:
    if not get_ai_call_by_id(call_id):
        raise HTTPException(status_code=404, detail="ai_call not found")
    return {"call_id": call_id, "events": build_call_timeline(call_id)}
