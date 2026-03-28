from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas.history import AIHistoryDetail, AIHistoryListItem
from app.services.ai.ai_call_service import (
    get_ai_call_by_id,
    get_ai_calls_by_request_id,
    list_ai_calls,
    list_feedback_for_request,
)
from app.services.ai.call_detail_enrichment import (
    effective_outcome,
    feedback_summary,
    human_ai_differs,
)
from app.services.ai.review_presentation import build_review_ui_payload
from app.services.ai.review_service import get_review_by_call_id
from app.services.ai.tuning_hints import build_tuning_hints_for_call

router = APIRouter(prefix="/api/v1/internal/ai", tags=["internal-ai"])


def _entity_from_user_input(ui: Any) -> dict[str, Any]:
    if not isinstance(ui, dict):
        return {}
    out: dict[str, Any] = {}
    for k in (
        "product_claim_id",
        "product_load_id",
        "product_document_id",
        "kind",
    ):
        if k in ui:
            out[k] = ui[k]
    return out


@router.get("/calls", response_model=list[AIHistoryListItem])
def history_list_calls(
    persona: str | None = Query(default=None),
    endpoint: str | None = Query(default=None),
    status: str | None = Query(default=None, description="normalized_status"),
    llm_invoked: bool | None = Query(default=None),
    q: str | None = Query(default=None, description="Поиск по summary, request_id, user_input (ILIKE)"),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    scenario: str | None = Query(default=None),
    entity_type: str | None = Query(default=None, description="claim | load | document"),
    entity_id: str | None = Query(default=None),
    reviewed_by: str | None = Query(default=None, description="Фильтр по ai_reviews.reviewed_by"),
    review_reason_code: str | None = Query(default=None, description="Код из review_reason_codes"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AIHistoryListItem]:
    rows = list_ai_calls(
        persona=persona,
        endpoint=endpoint,
        status=status,
        llm_invoked=llm_invoked,
        q=q,
        date_from=date_from,
        date_to=date_to,
        scenario=scenario,
        entity_type=entity_type,
        entity_id=entity_id,
        reviewed_by=reviewed_by,
        review_reason_code=review_reason_code,
        limit=limit,
        offset=offset,
    )
    return [AIHistoryListItem.model_validate(r) for r in rows]


@router.get("/calls/{call_id}", response_model=AIHistoryDetail)
def history_get_call(call_id: int) -> AIHistoryDetail:
    row = get_ai_call_by_id(call_id)
    if not row:
        raise HTTPException(status_code=404, detail="ai_call not found")
    rid = str(row.get("request_id") or "")
    fb = list_feedback_for_request(rid)
    ui = row.get("user_input_json") or {}
    rev = get_review_by_call_id(call_id)
    fsum = feedback_summary(fb)
    th = build_tuning_hints_for_call(call_row=row, review_row=rev)
    return AIHistoryDetail(
        call=row,
        feedback=fb,
        entity=_entity_from_user_input(ui),
        review=rev,
        feedback_summary=fsum,
        effective_outcome=effective_outcome(review_row=rev, fb_summary=fsum),
        human_ai_diff=human_ai_differs(row, rev),
        review_ui=build_review_ui_payload(row, rev),
        tuning_hints=th,
    )


@router.get("/calls/by-request/{request_id}", response_model=AIHistoryDetail)
def history_get_by_request(request_id: str) -> AIHistoryDetail:
    rows = get_ai_calls_by_request_id(request_id)
    if not rows:
        raise HTTPException(status_code=404, detail="no ai_calls for request_id")
    row = rows[0]
    call_id = int(row.get("id") or 0)
    fb = list_feedback_for_request(request_id)
    ui = row.get("user_input_json") or {}
    rev = get_review_by_call_id(call_id) if call_id else None
    fsum = feedback_summary(fb)
    th = build_tuning_hints_for_call(call_row=row, review_row=rev)
    return AIHistoryDetail(
        call=row,
        feedback=fb,
        entity=_entity_from_user_input(ui),
        review=rev,
        feedback_summary=fsum,
        effective_outcome=effective_outcome(review_row=rev, fb_summary=fsum),
        human_ai_diff=human_ai_differs(row, rev),
        review_ui=build_review_ui_payload(row, rev),
        tuning_hints=th,
    )
