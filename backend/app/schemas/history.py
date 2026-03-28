from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AIHistoryListItem(BaseModel):
    id: int
    created_at: str
    request_id: str
    endpoint: str
    persona: str | None = None
    mode: str | None = None
    normalized_status: str
    llm_invoked: bool | None = None
    citations_count: int = 0
    response_summary: str | None = None
    latency_ms: int = 0
    is_error: bool = False
    user_input_json: dict[str, Any] = Field(default_factory=dict)
    review_operator_action: str | None = None
    review_reason_codes: list[str] = Field(default_factory=list)


class AIHistoryDetail(BaseModel):
    call: dict[str, Any]
    feedback: list[dict[str, Any]] = Field(default_factory=list)
    entity: dict[str, Any] = Field(default_factory=dict)
    review: dict[str, Any] | None = None
    feedback_summary: dict[str, Any] = Field(default_factory=dict)
    effective_outcome: str | None = None
    human_ai_diff: bool | None = None
    review_ui: dict[str, Any] | None = None
    tuning_hints: dict[str, Any] | None = None
