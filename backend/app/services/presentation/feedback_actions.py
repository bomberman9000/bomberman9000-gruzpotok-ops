from __future__ import annotations

from typing import Any

from app.schemas.unified import PresentationAction


def quick_feedback_actions(*, request_id: str) -> list[PresentationAction]:
    return [
        PresentationAction(
            type="mark_useful",
            label="Полезно",
            payload={"request_id": request_id, "useful": True},
        ),
        PresentationAction(
            type="mark_not_useful",
            label="Не полезно",
            payload={"request_id": request_id, "useful": False},
        ),
    ]


def standard_actions(
    *,
    request_id: str,
    citations_count: int,
    retryable: bool,
    status: str,
) -> list[PresentationAction]:
    actions: list[PresentationAction] = []
    actions.extend(quick_feedback_actions(request_id=request_id))

    if citations_count > 0:
        actions.append(
            PresentationAction(
                type="open_citations",
                label="Источники",
                payload={"request_id": request_id, "count": citations_count},
            )
        )

    actions.append(
        PresentationAction(
            type="copy",
            label="Скопировать кратко",
            payload={"request_id": request_id, "field": "short_summary"},
        )
    )

    if status in ("unavailable", "insufficient_data") and retryable:
        actions.append(
            PresentationAction(
                type="regenerate",
                label="Повторить",
                payload={"request_id": request_id},
            )
        )

    actions.append(
        PresentationAction(
            type="ask_more",
            label="Уточнить запрос",
            payload={"request_id": request_id},
        )
    )

    return actions


def feedback_response_hints(*, request_id: str, saved: bool) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "saved": saved,
        "hint": "Отправьте POST /api/v1/ai/feedback с useful / comment при необходимости.",
        "quick_actions": [a.model_dump() for a in quick_feedback_actions(request_id=request_id)],
    }
