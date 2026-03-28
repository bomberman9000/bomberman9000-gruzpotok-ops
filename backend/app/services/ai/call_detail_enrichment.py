from __future__ import annotations

from typing import Any


def feedback_summary(feedback: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(feedback),
        "useful_true": sum(1 for f in feedback if f.get("useful") is True),
        "useful_false": sum(1 for f in feedback if f.get("useful") is False),
    }


def effective_outcome(
    *,
    review_row: dict[str, Any] | None,
    fb_summary: dict[str, Any],
) -> str:
    if review_row and review_row.get("operator_action"):
        return str(review_row["operator_action"])
    if fb_summary.get("useful_false", 0) > 0:
        return "negative_feedback"
    if fb_summary.get("useful_true", 0) > 0:
        return "positive_feedback"
    return "pending"


def human_ai_differs(
    call_row: dict[str, Any],
    review_row: dict[str, Any] | None,
) -> bool:
    if not review_row:
        return False
    op = (review_row.get("operator_action") or "").lower()
    if op in ("edited", "rejected"):
        return True
    ai_txt = (call_row.get("response_summary") or "").strip()
    fn = (review_row.get("final_text") or "").strip()
    if fn and ai_txt and fn != ai_txt:
        return True
    return False
