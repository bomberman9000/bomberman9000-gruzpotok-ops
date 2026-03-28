from __future__ import annotations

from typing import Any

API_INTERNAL = "/api/v1/internal/ai"
API_PUBLIC_AI = "/api/v1/ai"


def operator_action_hints(
    *,
    call_id: int,
    request_id: str,
    include_feedback_post: bool = True,
) -> list[dict[str, Any]]:
    """
    Единый контракт подсказок действий для панелей оператора и таймлайна.
    """
    rid = str(request_id or "")
    hints: list[dict[str, Any]] = [
        {
            "id": "accept",
            "label": "Принять ответ",
            "method": "POST",
            "path": f"{API_INTERNAL}/calls/{call_id}/accept",
            "body_schema": {"final_text": "optional string", "operator_comment": "optional string"},
        },
        {
            "id": "reject",
            "label": "Отклонить",
            "method": "POST",
            "path": f"{API_INTERNAL}/calls/{call_id}/reject",
            "body_schema": {"reason": "required string"},
        },
        {
            "id": "edit",
            "label": "Редактировать финальный текст",
            "method": "POST",
            "path": f"{API_INTERNAL}/calls/{call_id}/edit",
            "body_schema": {"final_text": "required string", "operator_comment": "optional string"},
        },
    ]
    if include_feedback_post:
        hints.extend(
            [
                {
                    "id": "mark_useful",
                    "label": "Полезно",
                    "method": "POST",
                    "path": f"{API_PUBLIC_AI}/feedback",
                    "body_schema": {"request_id": rid, "useful": True, "comment": "optional"},
                },
                {
                    "id": "mark_not_useful",
                    "label": "Не полезно",
                    "method": "POST",
                    "path": f"{API_PUBLIC_AI}/feedback",
                    "body_schema": {"request_id": rid, "useful": False, "comment": "optional"},
                },
            ]
        )
    hints.extend(
        [
            {
                "id": "open_sources",
                "label": "Открыть детали вызова",
                "method": "GET",
                "path": f"{API_INTERNAL}/calls/{call_id}",
            },
            {
                "id": "retry",
                "label": "Повторить запрос (новый AI-вызов)",
                "method": "POST",
                "path": f"{API_PUBLIC_AI}/query",
                "note": "См. публичный AI API; при необходимости новый request_id",
            },
            {
                "id": "escalate",
                "label": "Эскалация",
                "method": None,
                "path": None,
                "note": "Внешний бизнес-процесс кабинета; placeholder",
            },
        ]
    )
    return hints
