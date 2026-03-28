from __future__ import annotations

import uuid

from fastapi import APIRouter, Header, HTTPException, Request, Response

from app.core.config import get_settings
from app.schemas.requests import (
    AIClaimDraftBody,
    AIClaimReviewBody,
    AIDocumentCheckBody,
    AIQueryBody,
    AIRiskCheckBody,
    AIRouteAdviceBody,
)
from app.schemas.review_reasons import normalize_reason_codes
from app.schemas.transport_order import AITransportOrderComposeBody, AITransportOrderPdfBody
from app.schemas.unified import AIEnvelope, AIFeedbackBody, AIFeedbackResponse, UnifiedAIResponse
from app.services.ai.ai_call_service import insert_feedback, record_ai_call
from app.services.ai.gateway import build_meta, run_ai_gateway
from app.services.presentation.feedback_actions import feedback_response_hints
from app.services.ai.rag_client import RagApiClient

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


def _request_id(request: Request, x_request_id: str | None) -> str:
    return x_request_id or request.headers.get("X-Request-ID") or str(uuid.uuid4())


@router.post("/query", response_model=AIEnvelope)
async def ai_query(
    request: Request,
    body: AIQueryBody,
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> AIEnvelope:
    rid = _request_id(request, x_request_id)

    async def call(c: RagApiClient):
        return await c.query(
            query=body.query,
            mode=body.mode,
            persona=body.persona,
            category=body.category,
            source_type=body.source_type,
            debug=body.debug,
            request_id=rid,
        )

    return await run_ai_gateway(
        endpoint="query",
        rag_path="/query",
        request_id=rid,
        user_input={"kind": "query", **body.model_dump()},
        call=call,
    )


@router.post("/claims/review", response_model=AIEnvelope)
async def ai_claim_review(
    request: Request,
    body: AIClaimReviewBody,
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> AIEnvelope:
    rid = _request_id(request, x_request_id)

    async def call(c: RagApiClient):
        return await c.claim_review(
            claim_text=body.claim_text,
            contract_context=body.contract_context,
            counterparty=body.counterparty,
            debug=body.debug,
            request_id=rid,
        )

    return await run_ai_gateway(
        endpoint="claim_review",
        rag_path="/legal/claim-review",
        request_id=rid,
        user_input={"kind": "claim_review", **body.model_dump()},
        call=call,
    )


@router.post("/claims/draft", response_model=AIEnvelope)
async def ai_claim_draft(
    request: Request,
    body: AIClaimDraftBody,
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> AIEnvelope:
    rid = _request_id(request, x_request_id)

    async def call(c: RagApiClient):
        return await c.claim_draft(
            claim_text=body.claim_text,
            company_name=body.company_name,
            signer=body.signer,
            request_id=rid,
        )

    return await run_ai_gateway(
        endpoint="claim_draft",
        rag_path="/legal/claim-draft",
        request_id=rid,
        user_input={"kind": "claim_draft", **body.model_dump()},
        call=call,
    )


@router.post("/freight/risk-check", response_model=AIEnvelope)
async def ai_freight_risk(
    request: Request,
    body: AIRiskCheckBody,
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> AIEnvelope:
    rid = _request_id(request, x_request_id)

    async def call(c: RagApiClient):
        return await c.risk_check(
            situation=body.situation,
            counterparty_info=body.counterparty_info,
            route=body.route,
            debug=body.debug,
            request_id=rid,
        )

    return await run_ai_gateway(
        endpoint="risk_check",
        rag_path="/freight/risk-check",
        request_id=rid,
        user_input={"kind": "risk_check", **body.model_dump()},
        call=call,
    )


@router.post("/freight/route-advice", response_model=AIEnvelope)
async def ai_freight_route(
    request: Request,
    body: AIRouteAdviceBody,
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> AIEnvelope:
    rid = _request_id(request, x_request_id)

    async def call(c: RagApiClient):
        return await c.route_advice(
            route_request=body.route_request,
            vehicle=body.vehicle,
            cargo=body.cargo,
            constraints=body.constraints,
            request_id=rid,
        )

    return await run_ai_gateway(
        endpoint="route_advice",
        rag_path="/freight/route-advice",
        request_id=rid,
        user_input={"kind": "route_advice", **body.model_dump()},
        call=call,
    )


@router.post("/documents/check", response_model=AIEnvelope)
async def ai_document_check(
    request: Request,
    body: AIDocumentCheckBody,
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> AIEnvelope:
    rid = _request_id(request, x_request_id)

    async def call(c: RagApiClient):
        return await c.document_check(
            document_text=body.document_text,
            document_type=body.document_type,
            debug=body.debug,
            request_id=rid,
        )

    return await run_ai_gateway(
        endpoint="document_check",
        rag_path="/freight/document-check",
        request_id=rid,
        user_input={"kind": "document_check", **body.model_dump()},
        call=call,
    )


@router.post("/freight/transport-order-compose", response_model=AIEnvelope)
async def ai_transport_order_compose(
    request: Request,
    body: AITransportOrderComposeBody,
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> AIEnvelope:
    rid = _request_id(request, x_request_id)

    async def call(c: RagApiClient):
        return await c.transport_order_compose(
            request_text=body.request_text,
            debug=body.debug,
            request_id=rid,
        )

    return await run_ai_gateway(
        endpoint="transport_order_compose",
        rag_path="/freight/transport-order-compose",
        request_id=rid,
        user_input={"kind": "transport_order_compose", **body.model_dump()},
        call=call,
    )


@router.post(
    "/freight/transport-order-pdf",
    summary="PDF заявки на перевозку",
    responses={
        200: {
            "description": "Бинарный файл PDF (`application/pdf`), не JSON. Заголовок `Content-Disposition: attachment`.",
            "content": {
                "application/pdf": {
                    "schema": {"type": "string", "format": "binary"},
                }
            },
        },
        503: {"description": "rag-api недоступен или ошибка генерации PDF."},
    },
)
async def ai_transport_order_pdf(
    request: Request,
    body: AITransportOrderPdfBody,
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> Response:
    """Прокси к rag-api: ответ — бинарный PDF (не AIEnvelope)."""
    from app.services.ai.rag_client import RagCallError, RagApiClient

    s = get_settings()
    rid = _request_id(request, x_request_id)
    if not s.rag_api_enabled:
        raise HTTPException(status_code=503, detail="AI/RAG отключён (RAG_API_ENABLED=false).")

    try:
        client = RagApiClient(s)
        pdf_bytes, used_rid, lm = await client.transport_order_pdf(
            body=body.model_dump(mode="json", exclude_none=True),
            request_id=rid,
        )
    except RagCallError as e:
        raise HTTPException(status_code=503, detail=str(e)[:2000]) from e

    stub = UnifiedAIResponse(
        status="ok",
        summary="PDF договора-заявки на перевозку",
        llm_invoked=False,
        raw_response={"pdf_size_bytes": len(pdf_bytes)},
    )
    ui = {"kind": "transport_order_pdf", **body.model_dump(mode="json", exclude_none=True)}
    meta = build_meta(
        endpoint="transport_order_pdf",
        request_id=used_rid,
        latency_ms=lm,
        rag_path="/freight/transport-order-pdf",
        data=stub,
        user_input=ui,
    )
    record_ai_call(
        request_id=used_rid,
        endpoint="transport_order_pdf",
        meta=meta,
        data=stub,
        user_input=ui,
        latency_ms=lm,
        rag_reachable=True,
        rag_error=None,
    )

    safe_no = "".join(
        c if c.isalnum() or c in "-_" else "_" for c in (body.order_number or "bez_nomera")[:80]
    )
    filename = f"zayavka_perevozka_{safe_no}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Request-ID": used_rid,
        },
    )


@router.post("/feedback", response_model=AIFeedbackResponse)
async def ai_feedback(body: AIFeedbackBody) -> AIFeedbackResponse:
    fid = insert_feedback(
        request_id=body.request_id,
        useful=body.useful,
        correct=body.correct,
        comment=body.comment,
        user_role=body.user_role,
        source_screen=body.source_screen,
        feedback_reason_codes=normalize_reason_codes(body.reason_codes),
    )
    saved = fid is not None
    return AIFeedbackResponse(
        saved=saved,
        feedback_id=fid,
        request_id=body.request_id,
        message="Feedback сохранён" if saved else "БД не настроена или ошибка записи",
        hints=feedback_response_hints(request_id=body.request_id, saved=saved),
    )
