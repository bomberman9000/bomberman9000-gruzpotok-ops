from __future__ import annotations

import logging
from typing import Any

from app.services.ai.review_queue import build_review_queue
from app.services.notifications.alert_delivery import deliver_high_priority_alert

logger = logging.getLogger(__name__)


def render_high_priority_alert(items: list[dict[str, Any]], *, max_lines: int = 25) -> str:
    """
    Плоский текст для Telegram / внутренних алертов (без HTML).
    """
    if not items:
        return "🔔 AI queue: нет элементов повышенного приоритета."
    lines = [
        "🔔 ГрузПоток AI — high priority queue",
        f"Показано: {min(len(items), max_lines)} из {len(items)}",
        "",
    ]
    for it in items[:max_lines]:
        cid = it.get("call_id")
        persona = it.get("persona") or "?"
        st = it.get("normalized_status") or it.get("status_badge") or "?"
        sc = it.get("priority_score")
        rs = it.get("priority_reasons") or it.get("reasons") or []
        rstr = ", ".join(rs[:5]) if isinstance(rs, list) else str(rs)
        lines.append(f"• #{cid} | {persona} | {st} | score={sc} | {rstr}")
    lines.append("")
    lines.append("Открыть UI: /queue")
    return "\n".join(lines)


def notify_high_priority_hook(text: str) -> None:
    """
    Hook для внешней доставки (Telegram bot, webhook и т.д.).
    Логируем всегда; при ALERT_WEBHOOK_URL / Telegram env — HTTP-доставка (см. alert_delivery).
    """
    logger.info("high_priority_notification\n%s", text)
    deliver_high_priority_alert(text)


def get_high_priority_bundle(*, limit: int = 30, pool_limit: int = 2000) -> dict[str, Any]:
    """
    Кандидаты без review, отсортированные по priority_score; фильтр по правилам high-priority.
    """
    raw = build_review_queue(
        date_from=None,
        date_to=None,
        scenario=None,
        persona=None,
        status=None,
        llm_invoked=None,
        reviewed=False,
        limit=limit,
        offset=0,
        pool_limit=pool_limit,
    )
    items_in = raw.get("items") or []
    picked: list[dict[str, Any]] = []
    for it in items_in:
        score = float(it.get("priority_score") or 0)
        reasons = it.get("priority_reasons") or []
        rlow = " ".join(str(x) for x in reasons).lower()
        is_hp = False
        if score >= 55:
            is_hp = True
        elif (it.get("persona") or "").lower() in ("legal", "antifraud") and "risk=high" in rlow:
            is_hp = True
        elif "negative_feedback" in rlow and "no_review_yet" in rlow:
            is_hp = True
        elif it.get("has_negative_feedback") and not it.get("review_id"):
            is_hp = True
        elif "pattern_edited_rejected" in rlow:
            is_hp = True
        elif (it.get("normalized_status") or "") == "unavailable" and score >= 35:
            is_hp = True
        if is_hp:
            picked.append(it)

    alert_text = render_high_priority_alert(picked)
    return {
        "items": picked,
        "alert_text": alert_text,
        "total_in_pool": raw.get("total_in_pool"),
        "filters": raw.get("filters"),
        "pool_limit": raw.get("pool_limit"),
    }
