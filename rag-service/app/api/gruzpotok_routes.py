from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Response

from app.schemas.api import (
    FreightDocumentCheckRequest,
    FreightDocumentCheckResponse,
    FreightRiskCheckRequest,
    FreightRiskCheckResponse,
    FreightRouteAdviceRequest,
    FreightRouteAdviceResponse,
    FreightTransportOrderComposeRequest,
    FreightTransportOrderComposeResponse,
    FreightTransportOrderPdfRequest,
    LegalClaimComposeRequest,
    LegalClaimComposeResponse,
    LegalClaimDraftRequest,
    LegalClaimDraftResponse,
    LegalClaimReviewRequest,
    LegalClaimReviewResponse,
)
from app.core.config import settings
from app.services.freight.libreoffice_pdf import LibreOfficePdfError, build_transport_order_pdf_via_libreoffice
from app.services.freight.transport_order_pdf import build_transport_order_pdf_bytes
from app.services.gruzpotok_flow import (
    freight_document_check,
    freight_risk_check,
    freight_route_advice,
    freight_transport_order_compose,
    legal_claim_compose,
    legal_claim_draft,
    legal_claim_review,
)

router = APIRouter(tags=["ГрузПоток"])


@router.post("/legal/claim-review", response_model=LegalClaimReviewResponse)
async def post_legal_claim_review(body: LegalClaimReviewRequest) -> LegalClaimReviewResponse:
    async with httpx.AsyncClient(timeout=600.0) as client:
        return await legal_claim_review(client, body)


@router.post("/legal/claim-draft", response_model=LegalClaimDraftResponse)
async def post_legal_claim_draft(body: LegalClaimDraftRequest) -> LegalClaimDraftResponse:
    async with httpx.AsyncClient(timeout=600.0) as client:
        return await legal_claim_draft(client, body)


@router.post("/legal/claim-compose", response_model=LegalClaimComposeResponse)
async def post_legal_claim_compose(body: LegalClaimComposeRequest) -> LegalClaimComposeResponse:
    async with httpx.AsyncClient(timeout=600.0) as client:
        return await legal_claim_compose(client, body)


@router.post("/freight/risk-check", response_model=FreightRiskCheckResponse)
async def post_freight_risk_check(body: FreightRiskCheckRequest) -> FreightRiskCheckResponse:
    async with httpx.AsyncClient(timeout=600.0) as client:
        return await freight_risk_check(client, body)


@router.post("/freight/route-advice", response_model=FreightRouteAdviceResponse)
async def post_freight_route_advice(body: FreightRouteAdviceRequest) -> FreightRouteAdviceResponse:
    async with httpx.AsyncClient(timeout=600.0) as client:
        return await freight_route_advice(client, body)


@router.post("/freight/document-check", response_model=FreightDocumentCheckResponse)
async def post_freight_document_check(body: FreightDocumentCheckRequest) -> FreightDocumentCheckResponse:
    async with httpx.AsyncClient(timeout=600.0) as client:
        return await freight_document_check(client, body)


@router.post("/freight/transport-order-compose", response_model=FreightTransportOrderComposeResponse)
async def post_freight_transport_order_compose(
    body: FreightTransportOrderComposeRequest,
) -> FreightTransportOrderComposeResponse:
    async with httpx.AsyncClient(timeout=600.0) as client:
        return await freight_transport_order_compose(client, body)


@router.post("/freight/transport-order-pdf")
async def post_freight_transport_order_pdf(body: FreightTransportOrderPdfRequest) -> Response:
    try:
        if body.pdf_engine == "libreoffice":
            pdf_bytes = build_transport_order_pdf_via_libreoffice(
                body,
                soffice_executable=settings.libreoffice_soffice_path,
                timeout_sec=settings.libreoffice_convert_timeout_sec,
            )
        else:
            pdf_bytes = build_transport_order_pdf_bytes(body)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except LibreOfficePdfError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    safe_no = "".join(c if c.isalnum() or c in "-_" else "_" for c in (body.order_number or "bez_nomera")[:80])
    filename = f"zayavka_perevozka_{safe_no}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
