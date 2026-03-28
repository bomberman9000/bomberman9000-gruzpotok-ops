from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.unified import AIEnvelope


SectionTone = Literal["neutral", "warning", "danger", "success", "info"]


class UICardSection(BaseModel):
    title: str
    items: list[str] = Field(default_factory=list)
    tone: SectionTone = "neutral"


class UICard(BaseModel):
    """Карточка для Mini App / Web без дополнительных преобразований на фронте."""

    header: str = ""
    summary: str = ""
    sections: list[UICardSection] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    footer_meta: dict[str, Any] = Field(default_factory=dict)


def build_ui_card(envelope: AIEnvelope) -> UICard:
    p = envelope.data.presentation
    meta = envelope.meta
    if not p:
        return UICard(
            header="AI",
            summary=envelope.data.user_message or envelope.data.answer or "",
            footer_meta={
                "request_id": meta.request_id,
                "status": envelope.data.status,
            },
        )

    sections: list[UICardSection] = []
    if p.bullets:
        sections.append(UICardSection(title="Ключевые пункты", items=p.bullets[:20], tone="neutral"))
    if p.next_steps:
        sections.append(UICardSection(title="Дальнейшие шаги", items=p.next_steps[:20], tone="info"))
    if p.pdf_attachment_hint:
        h = p.pdf_attachment_hint
        pdf_lines = [
            h.embed_note,
            f"{h.download_label}: {h.http_method} {h.download_path}",
            h.request_body_hint,
            h.size_note,
            f"Обычно страниц: {h.page_count_typical}",
        ]
        sections.append(UICardSection(title=h.heading, items=pdf_lines, tone="info"))

    tone: SectionTone = "neutral"
    if p.severity == "danger":
        tone = "danger"
    elif p.severity == "warning":
        tone = "warning"
    elif p.severity == "success":
        tone = "success"

    citations = [c.model_dump() for c in p.citations_short]

    recs = list(envelope.data.recommendations or []) + list(envelope.data.suggestions or [])
    if not recs:
        recs = p.next_steps

    return UICard(
        header=p.title,
        summary=p.short_summary,
        sections=sections,
        warnings=p.warnings,
        recommendations=recs,
        citations=citations,
        footer_meta={
            "request_id": meta.request_id,
            "endpoint": meta.endpoint,
            "latency_ms": meta.latency_ms,
            "persona": meta.persona,
            "mode": meta.mode,
            "llm_invoked": meta.llm_invoked,
            "status": envelope.data.status,
            "severity": p.severity,
            "badge": p.badge,
            "status_label": p.status_label,
            "entity_type": p.entity_type,
            "entity_id": p.entity_id,
            "scenario": p.scenario,
            "screen_hint": p.screen_hint,
            "actions": [a.model_dump() for a in p.actions],
            "pdf_attachment_hint": p.pdf_attachment_hint.model_dump() if p.pdf_attachment_hint else None,
        },
    )
