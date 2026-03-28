from __future__ import annotations

from typing import Any

from app.services.ai.ai_call_service import get_ai_call_by_id, list_feedback_for_request
from app.services.ai.call_detail_enrichment import effective_outcome, feedback_summary
from app.services.ai.review_service import get_review_by_call_id


def build_call_timeline(call_id: int) -> list[dict[str, Any]]:
    row = get_ai_call_by_id(call_id)
    if not row:
        return []
    rid = str(row.get("request_id") or "")
    fb = list_feedback_for_request(rid)
    rev = get_review_by_call_id(call_id)
    fsum = feedback_summary(fb)
    outcome = effective_outcome(review_row=rev, fb_summary=fsum)

    events: list[dict[str, Any]] = []

    events.append(
        {
            "event_type": "ai_call_created",
            "timestamp": row.get("created_at"),
            "actor": "system",
            "summary": f"Запись вызова #{call_id}",
            "metadata": {"endpoint": row.get("endpoint"), "request_id": rid},
        }
    )
    events.append(
        {
            "event_type": "response_generated",
            "timestamp": row.get("created_at"),
            "actor": "ai",
            "summary": f"Статус: {row.get('normalized_status')}",
            "metadata": {
                "normalized_status": row.get("normalized_status"),
                "llm_invoked": row.get("llm_invoked"),
                "latency_ms": row.get("latency_ms"),
            },
        }
    )

    for f in fb:
        events.append(
            {
                "event_type": "feedback_added",
                "timestamp": f.get("created_at"),
                "actor": str(f.get("user_role") or "user"),
                "summary": f"Feedback useful={f.get('useful')}",
                "metadata": {
                    "feedback_id": f.get("id"),
                    "useful": f.get("useful"),
                    "correct": f.get("correct"),
                    "comment_preview": (str(f.get("comment") or ""))[:200],
                },
            }
        )

    if rev:
        events.append(
            {
                "event_type": "review_saved",
                "timestamp": rev.get("updated_at") or rev.get("created_at"),
                "actor": str(rev.get("reviewed_by") or "operator"),
                "summary": f"Review: {rev.get('operator_action')}",
                "metadata": {
                    "review_id": rev.get("id"),
                    "operator_action": rev.get("operator_action"),
                    "final_status": rev.get("final_status"),
                },
            }
        )

    events.append(
        {
            "event_type": "outcome_inferred",
            "timestamp": (rev or {}).get("reviewed_at")
            or (rev or {}).get("updated_at")
            or row.get("created_at"),
            "actor": "system",
            "summary": f"Итог (эвристика): {outcome}",
            "metadata": {"effective_outcome": outcome, "human_ai_diff_context": True},
        }
    )

    def _ts(e: dict[str, Any]) -> str:
        t = e.get("timestamp")
        return str(t) if t else ""

    events.sort(key=_ts)
    return events
