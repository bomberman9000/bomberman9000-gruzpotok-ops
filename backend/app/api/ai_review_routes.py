from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query

from app.schemas.review import AcceptBody, EditBody, RejectBody, ReviewCreate
from app.schemas.review_reasons import normalize_reason_codes
from app.services.ai.ai_call_service import get_ai_call_by_id
from app.services.ai.analytics_service import get_analytics
from app.services.ai.review_queue import build_review_queue
from app.services.ai.review_service import (
    get_review_by_call_id,
    get_review_by_id,
    insert_review_manual,
    list_reviews,
    upsert_review,
)

router = APIRouter(prefix="/api/v1/internal/ai", tags=["internal-ai-reviews"])


def _strip_operator(x: str | None) -> str | None:
    return x.strip() if x else None


def _entity_from_call(row: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    ui = row.get("user_input_json") or {}
    if not isinstance(ui, dict):
        return None, None, None
    kind = ui.get("kind")
    scenario = str(kind) if kind else None
    et = ei = None
    for k, ek in (
        ("product_claim_id", "claim"),
        ("product_load_id", "load"),
        ("product_document_id", "document"),
    ):
        if ui.get(k):
            et, ei = ek, str(ui[k])
            break
    return scenario, et, ei


@router.post("/reviews")
def create_review(body: ReviewCreate, x_reviewed_by: str | None = Header(default=None, alias="X-Reviewed-By")) -> dict[str, Any]:
    row = get_ai_call_by_id(body.ai_call_id)
    if not row:
        raise HTTPException(status_code=404, detail="ai_call not found")
    rid = _strip_operator(x_reviewed_by)
    oid = insert_review_manual(
        ai_call_id=body.ai_call_id,
        request_id=body.request_id,
        operator_action=body.operator_action,
        operator_comment=body.operator_comment,
        final_text=body.final_text,
        final_status=body.final_status,
        reviewed_by=rid,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        scenario=body.scenario,
        review_reason_codes=normalize_reason_codes(body.reason_codes),
    )
    if oid is None:
        raise HTTPException(status_code=503, detail="review not persisted")
    rev = get_review_by_id(oid) or {}
    return {"ok": True, "review": rev}


@router.get("/reviews")
def get_reviews(
    ai_call_id: int | None = Query(default=None),
    operator_action: str | None = Query(default=None),
    q: str | None = Query(default=None, description="ILIKE по comment, request_id, ai_call_id"),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    reviewed_by: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    scenario: str | None = Query(default=None),
    review_reason_code: str | None = Query(default=None, description="Код из review_reason_codes (JSON contains)"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    rows = list_reviews(
        ai_call_id=ai_call_id,
        operator_action=operator_action,
        review_reason_code=review_reason_code,
        q=q,
        date_from=date_from,
        date_to=date_to,
        reviewed_by=reviewed_by,
        entity_type=entity_type,
        entity_id=entity_id,
        scenario=scenario,
        limit=limit,
        offset=offset,
    )
    return {"items": rows, "limit": limit, "offset": offset}


@router.get("/reviews/{review_id}")
def get_review(review_id: int) -> dict[str, Any]:
    r = get_review_by_id(review_id)
    if not r:
        raise HTTPException(status_code=404, detail="review not found")
    return r


@router.post("/calls/{call_id}/accept")
def accept_call(call_id: int, body: AcceptBody, x_reviewed_by: str | None = Header(default=None, alias="X-Reviewed-By")) -> dict[str, Any]:
    row = get_ai_call_by_id(call_id)
    if not row:
        raise HTTPException(status_code=404, detail="ai_call not found")
    scenario, et, ei = _entity_from_call(row)
    final_t = body.final_text if body.final_text is not None else str(row.get("response_summary") or "")
    rc = normalize_reason_codes(body.reason_codes)
    oid = upsert_review(
        ai_call_id=call_id,
        request_id=str(row.get("request_id") or ""),
        operator_action="accepted",
        operator_comment=body.operator_comment,
        final_text=final_t,
        final_status=str(row.get("normalized_status") or ""),
        reviewed_by=_strip_operator(x_reviewed_by),
        entity_type=et,
        entity_id=ei,
        scenario=scenario,
        review_reason_codes=rc,
    )
    if oid is None:
        raise HTTPException(status_code=503, detail="review not persisted")
    return {"ok": True, "review_id": oid}


@router.post("/calls/{call_id}/reject")
def reject_call(call_id: int, body: RejectBody, x_reviewed_by: str | None = Header(default=None, alias="X-Reviewed-By")) -> dict[str, Any]:
    row = get_ai_call_by_id(call_id)
    if not row:
        raise HTTPException(status_code=404, detail="ai_call not found")
    scenario, et, ei = _entity_from_call(row)
    rc = normalize_reason_codes(body.reason_codes)
    if not rc:
        rc = ["other"]
    oid = upsert_review(
        ai_call_id=call_id,
        request_id=str(row.get("request_id") or ""),
        operator_action="rejected",
        operator_comment=body.reason,
        final_text=None,
        final_status=str(row.get("normalized_status") or ""),
        reviewed_by=_strip_operator(x_reviewed_by),
        entity_type=et,
        entity_id=ei,
        scenario=scenario,
        review_reason_codes=rc,
    )
    if oid is None:
        raise HTTPException(status_code=503, detail="review not persisted")
    return {"ok": True, "review_id": oid}


@router.post("/calls/{call_id}/edit")
def edit_call(call_id: int, body: EditBody, x_reviewed_by: str | None = Header(default=None, alias="X-Reviewed-By")) -> dict[str, Any]:
    row = get_ai_call_by_id(call_id)
    if not row:
        raise HTTPException(status_code=404, detail="ai_call not found")
    scenario, et, ei = _entity_from_call(row)
    rc = normalize_reason_codes(body.reason_codes)
    if not rc:
        rc = ["other"]
    oid = upsert_review(
        ai_call_id=call_id,
        request_id=str(row.get("request_id") or ""),
        operator_action="edited",
        operator_comment=body.operator_comment,
        final_text=body.final_text,
        final_status=str(row.get("normalized_status") or ""),
        reviewed_by=_strip_operator(x_reviewed_by),
        entity_type=et,
        entity_id=ei,
        scenario=scenario,
        review_reason_codes=rc,
    )
    if oid is None:
        raise HTTPException(status_code=503, detail="review not persisted")
    return {"ok": True, "review_id": oid}


@router.get("/review-queue")
def review_queue(
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
    review_reason_code: str | None = Query(default=None, description="Фильтр по review_reason_codes (есть review)"),
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


@router.get("/analytics")
def analytics(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
) -> dict[str, Any]:
    return get_analytics(date_from=date_from, date_to=date_to)
