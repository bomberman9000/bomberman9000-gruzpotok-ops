from __future__ import annotations

from typing import Any

from app.services.ai.analytics_service import get_analytics


def build_analytics_panel(
    *,
    date_from: str | None,
    date_to: str | None,
) -> dict[str, Any]:
    a = get_analytics(date_from=date_from, date_to=date_to)
    by_p = a.get("by_persona") or {}
    by_e = a.get("by_endpoint") or {}
    by_s = a.get("by_status") or {}

    summary_cards = [
        {"id": "total_calls", "label": "Вызовы", "value": a.get("total_calls"), "format": "int"},
        {"id": "total_feedback", "label": "Feedback", "value": a.get("total_feedback"), "format": "int"},
        {"id": "useful_rate", "label": "Доля useful", "value": a.get("useful_rate"), "format": "percent"},
        {"id": "llm_invoked_rate", "label": "LLM включён", "value": a.get("llm_invoked_rate"), "format": "percent"},
        {"id": "unavailable_rate", "label": "Unavailable", "value": a.get("unavailable_rate"), "format": "percent"},
        {"id": "insufficient_data_rate", "label": "Недостаточно данных", "value": a.get("insufficient_data_rate"), "format": "percent"},
    ]

    charts_data = {
        "by_persona": {"labels": list(by_p.keys()), "values": list(by_p.values())},
        "by_endpoint": {"labels": list(by_e.keys()), "values": list(by_e.values())},
        "by_status": {"labels": list(by_s.keys()), "values": list(by_s.values())},
    }

    top_neg = a.get("top_negative_scenarios") or []
    top_pos = a.get("top_positive_scenarios") or []

    review_outcomes = [
        {"action": k, "count": v}
        for k, v in (a.get("by_operator_action") or {}).items()
    ]

    risks_and_notes: list[dict[str, Any]] = []
    if (a.get("unavailable_rate") or 0) > 0.05:
        risks_and_notes.append(
            {"level": "warning", "code": "HIGH_UNAVAILABLE", "message": "Доля unavailable заметна за период"}
        )
    if (a.get("insufficient_data_rate") or 0) > 0.1:
        risks_and_notes.append(
            {"level": "info", "code": "INSUFFICIENT_DATA", "message": "Много ответов с insufficient_data"}
        )

    return {
        "summary_cards": summary_cards,
        "charts_data": charts_data,
        "top_negative_patterns": top_neg,
        "top_positive_patterns": top_pos,
        "review_outcomes": review_outcomes,
        "risks_and_notes": risks_and_notes,
        "raw_analytics": a,
    }
