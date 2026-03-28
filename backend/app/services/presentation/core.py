from __future__ import annotations

from app.schemas.unified import (
    CitationShort,
    PdfAttachmentHint,
    TelegramMiniAppPresentation,
    UnifiedAIResponse,
)
from app.services.presentation.entity_context import EntityPresentationContext, context_from_gateway
from app.services.presentation.feedback_actions import standard_actions
from app.services.presentation.status_mapping import (
    badge_for_status,
    effective_severity,
    label_for_status,
)


def _risk_level_from_data(data: UnifiedAIResponse) -> str | None:
    rr = data.raw_response
    if isinstance(rr, dict) and rr.get("risk_level"):
        return str(rr.get("risk_level"))
    return None


def _title_for(data: UnifiedAIResponse) -> str:
    rr = data.raw_response
    if isinstance(rr, dict) and "fields" in rr and "missing_information" in rr:
        return "Договор-заявка на перевозку груза"
    if data.draft_response_text:
        return "Черновик ответа"
    if data.legal_risks or ("претенз" in (data.summary or "").lower()):
        return "Разбор претензии"
    if data.red_flags or data.risks:
        return "Проверка рисков"
    if data.operational_advice:
        return "Рекомендации по маршруту"
    if data.missing_information and not data.operational_advice:
        return "Проверка документа"
    return "AI-ответ"


def _next_steps(data: UnifiedAIResponse) -> list[str]:
    out: list[str] = []
    if data.recommendations:
        out.extend(data.recommendations[:12])
    if data.suggestions:
        out.extend(data.suggestions[:8])
    seen: set[str] = set()
    uniq: list[str] = []
    for x in out:
        k = x.strip()
        if not k or k in seen:
            continue
        seen.add(k)
        uniq.append(k)
    return uniq[:15]


def build_presentation(
    data: UnifiedAIResponse,
    *,
    endpoint: str,
    request_id: str,
    user_input: dict | None = None,
) -> TelegramMiniAppPresentation:
    ctx: EntityPresentationContext = context_from_gateway(
        endpoint=endpoint,
        user_input=user_input,
        request_id=request_id,
    )
    summary = data.summary or data.answer or data.draft_response_text or data.user_message or ""
    bullets: list[str] = []
    if data.operational_advice:
        bullets.extend(data.operational_advice[:12])
    elif data.legal_risks:
        bullets.extend(data.legal_risks[:12])
    elif data.red_flags:
        bullets.extend(data.red_flags[:12])
    elif data.risks:
        bullets.extend(data.risks[:12])
    elif data.recommendations:
        bullets.extend(data.recommendations[:12])

    warnings: list[str] = []
    if data.status == "insufficient_data":
        warnings.append("Недостаточно данных или слабый retrieval; ответ предварительный.")
    if data.missing_information:
        warnings.extend(data.missing_information[:5])
    if data.llm_invoked is False and data.status == "ok":
        warnings.append("Ответ без вызова LLM (режим strict или пустая база).")
    if data.status == "unavailable":
        warnings.append(data.user_message or "Сервис знаний недоступен.")
    if data.status == "disabled":
        warnings.append(data.user_message or "AI отключён конфигурацией.")

    cit_short: list[CitationShort] = []
    for c in (data.citations or [])[:8]:
        if not isinstance(c, dict):
            continue
        cit_short.append(
            CitationShort(
                file_name=str(c.get("file_name") or ""),
                excerpt=str(c.get("excerpt") or "")[:240],
                document_id=str(c.get("document_id") or ""),
            )
        )

    st = data.status or "ok"
    risk_level = _risk_level_from_data(data)
    sev = effective_severity(normalized_status=st, risk_level=risk_level)

    subtitle_parts = [data.persona or "—", data.mode or "—"]
    if risk_level:
        subtitle_parts.append(f"риск:{risk_level}")
    subtitle = " · ".join(subtitle_parts)[:240]

    actions = standard_actions(
        request_id=request_id,
        citations_count=len(data.citations or []),
        retryable=bool(data.retryable),
        status=st,
    )

    pdf_hint: PdfAttachmentHint | None = None
    if endpoint == "transport_order_compose" and st == "ok":
        rr = data.raw_response
        fields = rr.get("fields") if isinstance(rr, dict) else None
        if isinstance(fields, dict) and any(str(v).strip() for v in fields.values()):
            pdf_hint = PdfAttachmentHint()

    return TelegramMiniAppPresentation(
        title=_title_for(data)[:200],
        subtitle=subtitle,
        short_summary=summary[:1200],
        bullets=bullets[:15],
        warnings=warnings[:10],
        next_steps=_next_steps(data),
        citations_short=cit_short,
        badge=badge_for_status(st),
        status_label=label_for_status(st),
        severity=sev,
        actions=actions,
        entity_type=ctx.entity_type,
        entity_id=ctx.entity_id,
        scenario=ctx.scenario,
        screen_hint=ctx.screen_hint,
        pdf_attachment_hint=pdf_hint,
    )


def attach_presentation(
    data: UnifiedAIResponse,
    *,
    endpoint: str,
    request_id: str,
    user_input: dict | None = None,
) -> UnifiedAIResponse:
    data.presentation = build_presentation(
        data,
        endpoint=endpoint,
        request_id=request_id,
        user_input=user_input,
    )
    return data
