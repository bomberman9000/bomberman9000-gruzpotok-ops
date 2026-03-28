from __future__ import annotations

from typing import Any


def build_review_ui_payload(
    call_row: dict[str, Any],
    review_row: dict[str, Any] | None,
) -> dict[str, Any]:
    suggested_text = str(call_row.get("response_summary") or "").strip()
    final_from_review = str((review_row or {}).get("final_text") or "").strip()
    editable_text = final_from_review if final_from_review else suggested_text

    badge = "pending"
    if review_row and review_row.get("operator_action"):
        badge = str(review_row["operator_action"])
    elif review_row:
        badge = "reviewed"

    diff_hint: str | None = None
    if suggested_text and editable_text and suggested_text != editable_text:
        diff_hint = "final_differs_from_ai_summary"
    elif review_row and (review_row.get("operator_action") or "").lower() == "edited":
        diff_hint = "edited"

    call_id = str(call_row.get("id") or "")
    operator_actions = [
        {
            "action": "accept",
            "label": "Принять",
            "method": "POST",
            "path": f"/api/v1/internal/ai/calls/{call_id}/accept",
        },
        {
            "action": "reject",
            "label": "Отклонить",
            "method": "POST",
            "path": f"/api/v1/internal/ai/calls/{call_id}/reject",
            "requires": ["reason"],
        },
        {
            "action": "edit",
            "label": "Изменить",
            "method": "POST",
            "path": f"/api/v1/internal/ai/calls/{call_id}/edit",
            "requires": ["final_text"],
        },
    ]

    return {
        "suggested_text": suggested_text,
        "editable_text": editable_text,
        "diff_hint": diff_hint,
        "review_status_badge": badge,
        "operator_actions": operator_actions,
    }
