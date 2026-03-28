from __future__ import annotations

import uuid

from fastapi import APIRouter, Header, Request

from app.schemas.requests import (
    AIClaimDraftBody,
    AIClaimReviewBody,
    AIDocumentCheckBody,
    AIRiskCheckBody,
)
from app.schemas.unified import AIEnvelope
from app.services.ai.gateway import run_ai_gateway
from app.services.ai.rag_client import RagApiClient

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])


def _rid(request: Request, x_request_id: str | None) -> str:
    return x_request_id or request.headers.get("X-Request-ID") or str(uuid.uuid4())


@router.post(
    "/claims/{claim_id}/ai-review",
    response_model=AIEnvelope,
    summary="AI-разбор претензии (привязка к claim_id)",
)
async def internal_claim_ai_review(
    claim_id: str,
    request: Request,
    body: AIClaimReviewBody,
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> AIEnvelope:
    """
    TODO: при появлении доменной модели Claim подставить текст из БД по claim_id.
    Сейчас тело такое же, как у /api/v1/ai/claims/review, плюс product_claim_id в user_input_json.
    """
    rid = _rid(request, x_request_id)

    async def call(c: RagApiClient):
        return await c.claim_review(
            claim_text=body.claim_text,
            contract_context=body.contract_context,
            counterparty=body.counterparty,
            debug=body.debug,
            request_id=rid,
        )

    return await run_ai_gateway(
        endpoint="internal_claim_review",
        rag_path="/legal/claim-review",
        request_id=rid,
        user_input={
            "kind": "internal_claim_review",
            "product_claim_id": claim_id,
            **body.model_dump(),
        },
        call=call,
    )


@router.post("/claims/{claim_id}/ai-draft", response_model=AIEnvelope)
async def internal_claim_ai_draft(
    claim_id: str,
    request: Request,
    body: AIClaimDraftBody,
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> AIEnvelope:
    """TODO: загрузить реквизиты претензии из БД по claim_id."""
    rid = _rid(request, x_request_id)

    async def call(c: RagApiClient):
        return await c.claim_draft(
            claim_text=body.claim_text,
            company_name=body.company_name,
            signer=body.signer,
            request_id=rid,
        )

    return await run_ai_gateway(
        endpoint="internal_claim_draft",
        rag_path="/legal/claim-draft",
        request_id=rid,
        user_input={"kind": "internal_claim_draft", "product_claim_id": claim_id, **body.model_dump()},
        call=call,
    )


@router.post("/freight/{load_id}/ai-risk-check", response_model=AIEnvelope)
async def internal_freight_risk(
    load_id: str,
    request: Request,
    body: AIRiskCheckBody,
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> AIEnvelope:
    """TODO: связать load_id с рейсом/заказом в продуктовой БД."""
    rid = _rid(request, x_request_id)

    async def call(c: RagApiClient):
        return await c.risk_check(
            situation=body.situation,
            counterparty_info=body.counterparty_info,
            route=body.route,
            debug=body.debug,
            request_id=rid,
        )

    return await run_ai_gateway(
        endpoint="internal_freight_risk",
        rag_path="/freight/risk-check",
        request_id=rid,
        user_input={"kind": "internal_freight_risk", "product_load_id": load_id, **body.model_dump()},
        call=call,
    )


@router.post("/documents/{doc_id}/ai-check", response_model=AIEnvelope)
async def internal_document_ai_check(
    doc_id: str,
    request: Request,
    body: AIDocumentCheckBody,
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> AIEnvelope:
    """TODO: подставить document_text из хранилища по doc_id."""
    rid = _rid(request, x_request_id)

    async def call(c: RagApiClient):
        return await c.document_check(
            document_text=body.document_text,
            document_type=body.document_type,
            debug=body.debug,
            request_id=rid,
        )

    return await run_ai_gateway(
        endpoint="internal_document_check",
        rag_path="/freight/document-check",
        request_id=rid,
        user_input={"kind": "internal_document_check", "product_document_id": doc_id, **body.model_dump()},
        call=call,
    )


@router.get("/stats")
def internal_stats() -> dict:
    from app.services.ai.ai_call_service import count_ai_calls
    from app.services.observability import snapshot

    snap = snapshot()
    snap["ai_calls_in_db"] = count_ai_calls()
    return snap
