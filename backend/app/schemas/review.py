from __future__ import annotations

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    ai_call_id: int
    request_id: str
    entity_type: str | None = None
    entity_id: str | None = None
    scenario: str | None = None
    operator_action: str = Field(..., description="accepted | edited | rejected | ignored")
    operator_comment: str | None = None
    final_text: str | None = None
    final_status: str | None = None
    reason_codes: list[str] = Field(default_factory=list, description="Нормализованные причины (см. review_reasons)")


class AcceptBody(BaseModel):
    final_text: str | None = None
    operator_comment: str | None = None
    reason_codes: list[str] = Field(default_factory=list)


class RejectBody(BaseModel):
    reason: str = Field(..., min_length=1)
    reason_codes: list[str] = Field(default_factory=list)


class EditBody(BaseModel):
    final_text: str = Field(..., min_length=1)
    operator_comment: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
