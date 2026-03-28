from __future__ import annotations

from typing import Any


def build_tuning_hints_for_call(
    *,
    call_row: dict[str, Any],
    review_row: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Rule-based подсказки для оператора / следующего tuning pass (без ML).
    """
    hints: list[dict[str, Any]] = []
    status = str(call_row.get("normalized_status") or "")
    cites = int(call_row.get("citations_count") or 0)
    persona = str(call_row.get("persona") or "")
    ep = str(call_row.get("endpoint") or "")
    codes: list[str] = []
    if review_row:
        rc = review_row.get("review_reason_codes") or []
        if isinstance(rc, list):
            codes = [str(x) for x in rc]

    if status == "insufficient_data":
        hints.append(
            {
                "area": "more_input_or_retrieval",
                "severity": "info",
                "message": "Ответ с insufficient_data: проверить входные данные и покрытие RAG.",
            }
        )

    if cites == 0 and status == "ok":
        hints.append(
            {
                "area": "citations_retrieval",
                "severity": "warning",
                "message": "Статус ok, но citations_count=0 — проверить retrieval/цитирование.",
            }
        )

    for c in codes:
        if c == "weak_citations":
            hints.append(
                {
                    "area": "citations_retrieval",
                    "severity": "warning",
                    "message": "Оператор отметил weak_citations — усилить поиск/цитирование.",
                }
            )
        elif c in ("incorrect_legal_basis", "hallucination_suspected"):
            hints.append(
                {
                    "area": "prompt_grounding",
                    "severity": "danger",
                    "message": f"Код {c}: ужесточить промпт и привязку к источникам.",
                }
            )
        elif c in ("too_generic", "bad_draft_tone", "formatting_problem"):
            hints.append(
                {
                    "area": "prompt_style",
                    "severity": "info",
                    "message": f"Код {c}: доработать шаблон ответа / tone / формат.",
                }
            )
        elif c == "wrong_risk_level":
            hints.append(
                {
                    "area": "routing_or_threshold",
                    "severity": "warning",
                    "message": "wrong_risk_level: калибровка risk/persona или правил скоринга.",
                }
            )
        elif c == "insufficient_context":
            hints.append(
                {
                    "area": "more_input_or_retrieval",
                    "severity": "info",
                    "message": "insufficient_context: собрать контекст у пользователя или расширить индекс.",
                }
            )
        elif c == "operator_preferred_manual":
            hints.append(
                {
                    "area": "product_workflow",
                    "severity": "info",
                    "message": "Ручной режим предпочтительнее — возможен gap в автоматизации.",
                }
            )
        elif c == "bad_price_range":
            msg = "bad_price_range: калибровка прайсинга / справочников / промпта под рынок."
            pl = persona.lower()
            el = ep.lower()
            if pl == "logistics" and ("freight" in el or "sales" in el):
                msg = (
                    "bad_price_range (freight/logistics): избегать широких вилок без даты/окна погрузки, "
                    "типа ТС и объёма; сначала уточнения или узкий диапазон с явными допущениями."
                )
            hints.append(
                {
                    "area": "pricing_or_market_data",
                    "severity": "warning",
                    "message": msg,
                }
            )

    primary = None
    areas = [h["area"] for h in hints]
    if "prompt_grounding" in areas:
        primary = "prompt_grounding"
    elif "citations_retrieval" in areas:
        primary = "citations_retrieval"
    elif "more_input_or_retrieval" in areas:
        primary = "more_input_or_retrieval"
    elif "routing_or_threshold" in areas:
        primary = "routing_or_threshold"
    elif areas:
        primary = areas[0]

    return {
        "likely_primary_area": primary,
        "hints": hints,
        "context": {"endpoint": ep, "persona": persona, "normalized_status": status},
    }


def derive_quality_tuning_hints(report: dict[str, Any]) -> dict[str, Any]:
    """Агрегированные эвристики поверх уже посчитанного quality report."""
    out: dict[str, Any] = {
        "scenarios_needing_more_data": [],
        "scenarios_needing_stricter_prompt": [],
        "scenarios_needing_better_citations": [],
        "scenarios_needing_routing_or_persona_change": [],
        "scenarios_needing_threshold_tuning": [],
    }
    bd = report.get("breakdown") or {}
    for row in report.get("cases_needing_better_data") or []:
        ep = row.get("endpoint")
        if ep:
            out["scenarios_needing_more_data"].append(
                {"endpoint": ep, "count": row.get("count"), "signal": "insufficient_data_volume"}
            )
    for row in bd.get("by_reason") or []:
        reason = str(row.get("reason") or "")
        n = int(row.get("count") or 0)
        if reason == "weak_citations":
            out["scenarios_needing_better_citations"].append({"reason": reason, "count": n})
        if reason in ("incorrect_legal_basis", "hallucination_suspected", "too_generic"):
            out["scenarios_needing_stricter_prompt"].append({"reason": reason, "count": n})
        if reason == "wrong_risk_level":
            out["scenarios_needing_routing_or_persona_change"].append({"reason": reason, "count": n})
        if reason == "insufficient_context":
            out["scenarios_needing_more_data"].append({"reason": reason, "count": n, "signal": "operator_tag"})
    for row in report.get("top_edited_reasons") or []:
        ep = row.get("endpoint")
        reason = str(row.get("reason") or "")
        if reason == "weak_citations" and ep:
            out["scenarios_needing_better_citations"].append({"endpoint": ep, "reason": reason, "count": row.get("count")})
    for row in report.get("cases_needing_prompt_or_rule_tuning") or []:
        ep = row.get("endpoint")
        if ep and row.get("heuristic_reasons"):
            out["scenarios_needing_threshold_tuning"].append(
                {"endpoint": ep, "heuristic_reasons": row.get("heuristic_reasons")}
            )
    return out
