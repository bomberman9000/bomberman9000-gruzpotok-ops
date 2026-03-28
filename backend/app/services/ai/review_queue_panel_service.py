from __future__ import annotations

from app.services.ai.review_queue import build_review_queue


def build_review_queue_panel(
    *,
    date_from: str | None,
    date_to: str | None,
    scenario: str | None,
    persona: str | None,
    status: str | None,
    llm_invoked: bool | None,
    reviewed: bool | None,
    limit: int,
    offset: int,
    pool_limit: int = 5000,
    review_reason_code: str | None = None,
) -> dict[str, Any]:
    raw = build_review_queue(
        date_from=date_from,
        date_to=date_to,
        scenario=scenario,
        persona=persona,
        status=status,
        llm_invoked=llm_invoked,
        reviewed=reviewed,
        limit=limit,
        offset=offset,
        pool_limit=pool_limit,
        review_reason_code=review_reason_code,
    )
    items_ui: list[dict[str, Any]] = []
    for it in raw.get("items") or []:
        per = it.get("persona") or "unknown"
        ep = it.get("endpoint") or ""
        st = it.get("normalized_status") or ""
        scenario_label = ep or st or "scenario"
        subtitle_parts = [str(x) for x in (per, ep, st) if x]
        rrc = it.get("review_reason_codes") or []
        if not isinstance(rrc, list):
            rrc = []
        items_ui.append(
            {
                "title": f"#{it.get('call_id')} · {per}",
                "subtitle": " · ".join(subtitle_parts),
                "priority": it.get("priority_score"),
                "persona_badge": per,
                "scenario_label": scenario_label,
                "status_badge": st,
                "review_reason_badges": [str(x) for x in rrc],
                "reasons": it.get("priority_reasons") or [],
                "quick_actions": [
                    {
                        "id": "open_call",
                        "label": "Открыть вызов",
                        "method": "GET",
                        "path": f"/api/v1/internal/ai/calls/{it.get('call_id')}",
                    },
                    {
                        "id": "accept",
                        "label": "Принять",
                        "method": "POST",
                        "path": f"/api/v1/internal/ai/calls/{it.get('call_id')}/accept",
                    },
                    {
                        "id": "reject",
                        "label": "Отклонить",
                        "method": "POST",
                        "path": f"/api/v1/internal/ai/calls/{it.get('call_id')}/reject",
                    },
                    {
                        "id": "edit",
                        "label": "Правка",
                        "method": "POST",
                        "path": f"/api/v1/internal/ai/calls/{it.get('call_id')}/edit",
                    },
                ],
                "raw": it,
            }
        )
    return {
        "items": items_ui,
        "total_in_pool": raw.get("total_in_pool"),
        "limit": raw.get("limit"),
        "offset": raw.get("offset"),
        "pool_limit": raw.get("pool_limit"),
        "filters": raw.get("filters"),
    }
