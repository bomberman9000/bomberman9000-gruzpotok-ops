from __future__ import annotations

import json
import logging
from typing import Any

from app.services.ai.ai_call_service import get_ai_calls_by_request_id, list_feedback_for_request
from app.services.ai.call_detail_enrichment import effective_outcome, feedback_summary
from app.services.ai.operator_action_hints import operator_action_hints
from app.services.ai.priority_rules import risk_level_from_call_row
from app.services.ai.review_service import get_review_by_call_id

logger = logging.getLogger(__name__)


_ALLOWED_UI_KEYS = frozenset({"product_claim_id", "product_load_id", "product_document_id"})


def find_calls_by_entity_field(field: str, value: str) -> list[dict[str, Any]]:
    from app.core.config import get_settings
    from app.db.pool import get_conn
    from psycopg2.extras import RealDictCursor

    s = get_settings()
    if not s.database_url:
        return []
    if field not in _ALLOWED_UI_KEYS:
        return []
    try:
        with get_conn() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                """
                SELECT id, created_at, request_id, endpoint, persona, mode, user_input_json,
                       normalized_status, llm_invoked, citations_count, response_summary,
                       raw_meta_json, raw_data_json, latency_ms, is_error
                FROM ai_calls
                WHERE user_input_json ->> %s = %s
                ORDER BY created_at DESC
                LIMIT 200
                """,
                (field, value),
            )
            rows = cur.fetchall()
            cur.close()
        out: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            if d.get("created_at"):
                d["created_at"] = str(d["created_at"])
            out.append(d)
        return out
    except Exception:
        logger.exception("find_calls_by_entity_field")
        return []


def _citations_from_call(row: dict[str, Any]) -> list[dict[str, Any]]:
    raw = row.get("raw_data_json")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = None
    if not isinstance(raw, dict):
        return []
    cits = raw.get("citations") or []
    if not isinstance(cits, list):
        return []
    slim: list[dict[str, Any]] = []
    for c in cits[:30]:
        if isinstance(c, dict):
            slim.append(
                {
                    "title": c.get("title") or c.get("source") or "",
                    "snippet": (c.get("snippet") or c.get("text") or "")[:500],
                    "ref": c.get("ref") or c.get("id"),
                }
            )
    return slim


def _ai_result_block(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("raw_data_json")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = None
    status = row.get("normalized_status")
    summary = row.get("response_summary")
    risk = risk_level_from_call_row(row)
    return {
        "normalized_status": status,
        "response_summary": summary,
        "persona": row.get("persona"),
        "mode": row.get("mode"),
        "llm_invoked": row.get("llm_invoked"),
        "risk_level": risk,
        "answer_preview": (raw or {}).get("answer") or (raw or {}).get("summary") if isinstance(raw, dict) else None,
    }


def build_case_panel(
    *,
    panel_kind: str,
    entity_id: str,
    calls: list[dict[str, Any]],
    request_id: str | None = None,
) -> dict[str, Any]:
    """
    UI-ready панель по списку вызовов (best-effort; доменных сущностей может не быть в БД).
    """
    warnings: list[dict[str, Any]] = []
    if not calls:
        warnings.append(
            {
                "level": "info",
                "code": "NO_AI_CALLS",
                "message": "Нет записей ai_calls по метаданным сущности. TODO: связать с доменным API претензий/перевозок/документов.",
            }
        )
        return {
            "panel_kind": panel_kind,
            "header": {
                "title": f"{panel_kind} {entity_id}",
                "subtitle": None,
                "entity_type": panel_kind,
                "entity_id": entity_id,
                "request_id": request_id,
            },
            "status_badge": "unknown",
            "summary": None,
            "ai_result": {},
            "citations": [],
            "feedback_state": {"items": [], "summary": {"count": 0, "useful_true": 0, "useful_false": 0}},
            "review_state": None,
            "operator_actions": [],
            "history_refs": {"calls": [], "note": "Нет вызовов для построения ссылок"},
            "warnings": warnings,
            "next_steps": ["Проверить идентификатор сущности", "Выполнить новый AI-запрос с корректным user_input"],
        }

    primary = calls[0]
    call_id = int(primary.get("id") or 0)
    rid = str(request_id or primary.get("request_id") or "")
    fb = list_feedback_for_request(rid) if rid else []
    fsum = feedback_summary(fb)
    rev = get_review_by_call_id(call_id) if call_id else None
    eff = effective_outcome(review_row=rev, fb_summary=fsum)

    status_badge = str(primary.get("normalized_status") or "unknown")
    if rev and rev.get("operator_action"):
        status_badge = f"review:{rev.get('operator_action')}"

    history_refs = {
        "calls": [
            {
                "call_id": int(c.get("id")),
                "created_at": c.get("created_at"),
                "endpoint": c.get("endpoint"),
                "request_id": c.get("request_id"),
            }
            for c in calls[:50]
        ],
        "detail_paths": [f"/api/v1/internal/ai/calls/{c.get('id')}" for c in calls[:20]],
    }

    hints = operator_action_hints(call_id=call_id, request_id=rid) if call_id else []

    next_steps: list[str] = []
    if rev is None and (fsum.get("useful_false") or 0) > 0:
        next_steps.append("Рассмотреть в очереди review (негативный feedback)")
    if primary.get("normalized_status") == "insufficient_data":
        next_steps.append("Запросить недостающие данные у клиента")

    return {
        "panel_kind": panel_kind,
        "header": {
            "title": f"{panel_kind} {entity_id}",
            "subtitle": primary.get("endpoint"),
            "entity_type": panel_kind,
            "entity_id": entity_id,
            "request_id": rid or None,
            "persona": primary.get("persona"),
        },
        "status_badge": status_badge,
        "summary": primary.get("response_summary"),
        "ai_result": _ai_result_block(primary),
        "citations": _citations_from_call(primary),
        "feedback_state": {"items": fb, "summary": fsum},
        "review_state": rev,
        "operator_actions": hints,
        "history_refs": history_refs,
        "warnings": warnings,
        "next_steps": next_steps or ["При необходимости открыть детали последнего вызова"],
        "effective_outcome": eff,
        "primary_call_id": call_id,
    }


def panel_for_claim(claim_id: str) -> dict[str, Any]:
    rows = find_calls_by_entity_field("product_claim_id", claim_id)
    return build_case_panel(panel_kind="claim", entity_id=claim_id, calls=rows)


def panel_for_freight(load_id: str) -> dict[str, Any]:
    rows = find_calls_by_entity_field("product_load_id", load_id)
    return build_case_panel(panel_kind="freight", entity_id=load_id, calls=rows)


def panel_for_document(doc_id: str) -> dict[str, Any]:
    rows = find_calls_by_entity_field("product_document_id", doc_id)
    return build_case_panel(panel_kind="document", entity_id=doc_id, calls=rows)


def panel_for_request(request_id: str) -> dict[str, Any]:
    rows = get_ai_calls_by_request_id(request_id)
    return build_case_panel(
        panel_kind="request",
        entity_id=request_id,
        calls=rows,
        request_id=request_id,
    )
