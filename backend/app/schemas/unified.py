from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


AIStatus = Literal[
    "ok",
    "unavailable",
    "insufficient_data",
    "upstream_error",
    "disabled",
    "invalid_upstream",
]


class CitationShort(BaseModel):
    file_name: str = ""
    excerpt: str = ""
    document_id: str = ""


PresentationSeverity = Literal["info", "warning", "danger", "success"]

PresentationActionType = Literal[
    "copy",
    "open_citations",
    "regenerate",
    "ask_more",
    "mark_useful",
    "mark_not_useful",
]


class PresentationAction(BaseModel):
    type: PresentationActionType
    label: str
    payload: dict[str, Any] = Field(default_factory=dict)


class PdfAttachmentHint(BaseModel):
    """Шаблон для UI/бота: как получить PDF договора-заявки после transport-order-compose."""

    heading: str = "Договор-заявка на перевозку груза"
    embed_note: str = (
        "Вставьте PDF из бинарного ответа POST /api/v1/ai/freight/transport-order-pdf "
        "(тело запроса — JSON с полями заявки, см. request_body_hint)."
    )
    download_label: str = "Скачать файл"
    download_path: str = "/api/v1/ai/freight/transport-order-pdf"
    http_method: str = "POST"
    request_body_hint: str = (
        "JSON: поля из envelope.data.raw_response.fields (дополнительно pdf_engine, pdf_template при необходимости)."
    )
    size_note: str = "Вес файла: по длине тела ответа (байты) или заголовку Content-Length, если есть."
    page_count_typical: int = 1


class TelegramMiniAppPresentation(BaseModel):
    """Presentation V2: Telegram / Mini App / Web / операторский UI."""

    title: str = ""
    subtitle: str = ""
    short_summary: str = ""
    bullets: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    citations_short: list[CitationShort] = Field(default_factory=list)
    badge: str = ""
    status_label: str = ""
    severity: PresentationSeverity = "info"
    actions: list[PresentationAction] = Field(default_factory=list)
    entity_type: str | None = None
    entity_id: str | None = None
    scenario: str | None = None
    screen_hint: str | None = None
    pdf_attachment_hint: PdfAttachmentHint | None = None


class UnifiedAIResponse(BaseModel):
    """Единый формат ответа backend после вызова rag-api."""

    status: AIStatus = "ok"
    answer: str | None = None
    summary: str | None = None
    persona: str | None = None
    mode: str | None = None
    llm_invoked: bool | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    draft_response_text: str | None = None
    legal_risks: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    operational_advice: list[str] = Field(default_factory=list)
    raw_response: dict[str, Any] | None = None
    # Fallback / UX
    user_message: str | None = None
    technical_reason: str | None = None
    retryable: bool = False
    suggestions: list[str] = Field(default_factory=list)
    presentation: TelegramMiniAppPresentation | None = None


class AIMeta(BaseModel):
    request_id: str
    endpoint: str
    latency_ms: int
    citations_count: int = 0
    rag_path: str = ""
    persona: str | None = None
    mode: str | None = None
    llm_invoked: bool | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    scenario: str | None = None
    screen_hint: str | None = None


class AIEnvelope(BaseModel):
    """Ответ HTTP API ГрузПотока."""

    meta: AIMeta
    data: UnifiedAIResponse


class AIFeedbackBody(BaseModel):
    request_id: str = Field(..., min_length=4, max_length=512)
    useful: bool
    correct: bool | None = None
    comment: str = Field(default="", max_length=8000)
    user_role: str = Field(default="", max_length=500)
    source_screen: str = Field(default="", max_length=500)
    reason_codes: list[str] = Field(default_factory=list, description="Опционально: нормализованные причины")


class AIFeedbackResponse(BaseModel):
    saved: bool
    feedback_id: int | None = None
    request_id: str | None = None
    message: str = ""
    hints: dict[str, Any] = Field(default_factory=dict)
