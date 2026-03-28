from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AIQueryBody(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    mode: Literal["balanced", "strict", "draft"] | None = None
    persona: Literal["legal", "logistics", "antifraud"] | None = None
    category: Literal["legal", "freight", "general"] | None = None
    source_type: Literal["law", "contract", "template", "internal", "other"] | None = None
    debug: bool | None = None


class AIClaimReviewBody(BaseModel):
    claim_text: str = Field(..., min_length=1)
    contract_context: str = ""
    counterparty: str = ""
    debug: bool | None = None


class AIClaimDraftBody(BaseModel):
    claim_text: str = Field(..., min_length=1)
    company_name: str = ""
    signer: str = ""


class AIRiskCheckBody(BaseModel):
    situation: str = Field(..., min_length=1)
    counterparty_info: str = ""
    route: str = ""
    debug: bool | None = None


class AIRouteAdviceBody(BaseModel):
    route_request: str = ""
    vehicle: str = ""
    cargo: str = ""
    constraints: str = ""


class AIDocumentCheckBody(BaseModel):
    document_text: str = Field(..., min_length=1)
    document_type: str = ""
    debug: bool | None = None
