from __future__ import annotations

import re

from app.schemas.unified import AIEnvelope, CitationShort


def _md_escape(text: str) -> str:
    """Минимальное экранирование для Telegram MarkdownV2 — здесь plain text без MD, только убираем опасные символы."""
    return re.sub(r"([_*[\]()~`>#+\-=|{}.!\\])", r"\\\1", text or "")


def render_citations_for_telegram(citations: list[CitationShort], *, max_items: int = 5) -> str:
    lines: list[str] = []
    for i, c in enumerate(citations[:max_items], 1):
        fn = (c.file_name or "документ")[:120]
        ex = (c.excerpt or "")[:180]
        lines.append(f"{i}. {fn}\n   {ex}")
    if not lines:
        return "Источники: нет в ответе."
    return "Источники:\n" + "\n".join(lines)


def render_ai_result_for_telegram(envelope: AIEnvelope, *, use_markdown_escape: bool = False) -> str:
    """Короткий текст для Telegram: заголовок, summary, блоки warnings / дальше."""
    p = envelope.data.presentation
    meta = envelope.meta
    if not p:
        t = envelope.data.user_message or envelope.data.answer or "Нет данных."
        return _md_escape(t) if use_markdown_escape else t

    title = p.title or "AI"
    sub = p.subtitle or ""
    summary = p.short_summary or ""

    lines: list[str] = [title]
    if sub:
        lines.append(sub)
    lines.append("")
    lines.append(summary[:3500])

    if p.warnings:
        lines.append("")
        lines.append("Предупреждения:")
        for w in p.warnings[:8]:
            lines.append(f"• {w}")

    if p.next_steps:
        lines.append("")
        lines.append("Что делать дальше:")
        for s in p.next_steps[:10]:
            lines.append(f"• {s}")

    if p.pdf_attachment_hint:
        h = p.pdf_attachment_hint
        lines.append("")
        lines.append(h.heading)
        lines.append(h.embed_note)
        lines.append(f"{h.download_label}: {h.http_method} {h.download_path}")
        lines.append(h.request_body_hint)
        lines.append(h.size_note)
        lines.append(f"Обычно страниц: {h.page_count_typical}")

    if p.bullets and not p.next_steps:
        lines.append("")
        for b in p.bullets[:10]:
            lines.append(f"• {b}")

    lines.append("")
    lines.append(f"Статус: {p.status_label} ({meta.request_id})")
    lines.append(render_citations_for_telegram(p.citations_short))

    out = "\n".join(lines)
    return _md_escape(out) if use_markdown_escape else out


def render_feedback_buttons(*, request_id: str) -> list[dict[str, str]]:
    """Подсказка для inline-кнопок (клиент бота сам создаёт callback_data)."""
    return [
        {"text": "Полезно", "action": "mark_useful", "request_id": request_id},
        {"text": "Не полезно", "action": "mark_not_useful", "request_id": request_id},
    ]


def render_fallback_plain(envelope: AIEnvelope) -> str:
    st = envelope.data.status
    if st == "unavailable":
        return envelope.data.user_message or "AI временно недоступен."
    if st == "insufficient_data":
        return envelope.data.user_message or "Недостаточно данных для уверенного ответа."
    if st == "disabled":
        return envelope.data.user_message or "AI отключён."
    return render_ai_result_for_telegram(envelope)
