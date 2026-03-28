from __future__ import annotations

from typing import Any

from app.schemas.unified import UnifiedAIResponse


def _citations_to_dicts(raw: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for c in raw or []:
        if isinstance(c, dict):
            out.append(c)
        elif hasattr(c, "model_dump"):
            out.append(c.model_dump())
    return out


def _insufficient_from_query(answer: str, llm_invoked: bool) -> bool:
    if llm_invoked:
        return False
    a = (answer or "").lower()
    return (
        "недостаточно" in a
        or "проиндексированных" in a
        or "строгом режиме" in a
        or "недостаточно релевантных" in a
    )


def normalize_from_query(raw: dict[str, Any]) -> UnifiedAIResponse:
    answer = str(raw.get("answer") or "")
    llm = bool(raw.get("llm_invoked", False))
    cit = _citations_to_dicts(raw.get("citations") or [])
    insufficient = _insufficient_from_query(answer, llm)
    status = "insufficient_data" if insufficient else "ok"
    if not insufficient and not llm and "нет проиндексированных" in answer.lower():
        status = "insufficient_data"
    return UnifiedAIResponse(
        status=status,
        answer=answer,
        summary=None,
        persona=raw.get("persona"),
        mode=raw.get("mode"),
        llm_invoked=llm,
        citations=cit,
        missing_information=[] if status == "ok" else [answer[:500]],
        raw_response=raw,
        user_message=None,
        technical_reason=None,
        retryable=False,
    )


def normalize_from_claim_review(raw: dict[str, Any]) -> UnifiedAIResponse:
    llm = bool(raw.get("llm_invoked", False))
    cit = _citations_to_dicts(raw.get("citations") or [])
    miss = list(raw.get("missing_information") or [])
    status: str = "ok" if llm else "insufficient_data"
    recs: list[str] = []
    if raw.get("recommended_position"):
        recs.append(str(raw.get("recommended_position")))
    return UnifiedAIResponse(
        status=status,
        summary=str(raw.get("summary") or ""),
        persona=raw.get("persona"),
        mode=raw.get("mode"),
        llm_invoked=llm,
        citations=cit,
        missing_information=miss,
        legal_risks=list(raw.get("legal_risks") or []),
        risks=list(raw.get("legal_risks") or []),
        recommendations=recs,
        raw_response=raw,
    )


def normalize_from_claim_draft(raw: dict[str, Any]) -> UnifiedAIResponse:
    llm = bool(raw.get("llm_invoked", False))
    cit = _citations_to_dicts(raw.get("citations") or [])
    status = "ok" if llm else "insufficient_data"
    return UnifiedAIResponse(
        status=status,
        draft_response_text=str(raw.get("draft_response_text") or ""),
        persona=raw.get("persona"),
        mode=raw.get("mode"),
        llm_invoked=llm,
        citations=cit,
        recommendations=list(raw.get("disclaimers") or []),
        raw_response=raw,
        user_message=None if llm else "Черновик не сформирован полностью; проверьте базу знаний.",
    )


def normalize_from_risk_check(raw: dict[str, Any]) -> UnifiedAIResponse:
    llm = bool(raw.get("llm_invoked", False))
    cit = _citations_to_dicts(raw.get("citations") or [])
    status = "ok" if llm else "insufficient_data"
    return UnifiedAIResponse(
        status=status,
        summary=f"risk_level={raw.get('risk_level')}",
        persona=raw.get("persona"),
        mode=raw.get("mode"),
        llm_invoked=llm,
        citations=cit,
        risks=list(raw.get("red_flags") or []),
        recommendations=list(raw.get("recommended_checks") or []) + list(raw.get("suggested_next_steps") or []),
        red_flags=list(raw.get("red_flags") or []),
        raw_response=raw,
    )


def normalize_from_route_advice(raw: dict[str, Any]) -> UnifiedAIResponse:
    llm = bool(raw.get("llm_invoked", False))
    cit = _citations_to_dicts(raw.get("citations") or [])
    miss = list(raw.get("missing_information") or [])
    if miss:
        status = "insufficient_data"
    elif not llm:
        status = "insufficient_data"
    else:
        status = "ok"
    return UnifiedAIResponse(
        status=status,
        summary=str(raw.get("summary") or ""),
        persona=raw.get("persona"),
        mode=raw.get("mode"),
        llm_invoked=llm,
        citations=cit,
        missing_information=miss,
        risks=list(raw.get("risks") or []),
        operational_advice=list(raw.get("operational_advice") or []),
        recommendations=list(raw.get("operational_advice") or []),
        raw_response=raw,
    )


def normalize_from_transport_order_compose(raw: dict[str, Any]) -> UnifiedAIResponse:
    llm = bool(raw.get("llm_invoked", False))
    cit = _citations_to_dicts(raw.get("citations") or [])
    miss = list(raw.get("missing_information") or [])
    fields = raw.get("fields")
    filled = False
    if isinstance(fields, dict):
        filled = any(str(v).strip() for v in fields.values())
    if miss and not filled:
        status: str = "insufficient_data"
    elif not llm and not filled:
        status = "insufficient_data"
    else:
        status = "ok"
    return UnifiedAIResponse(
        status=status,
        summary="Договор-заявка на перевозку груза: поля в data.raw_response.fields; PDF — POST /api/v1/ai/freight/transport-order-pdf.",
        persona=raw.get("persona"),
        mode=raw.get("mode"),
        llm_invoked=llm,
        citations=cit,
        missing_information=miss,
        raw_response=raw,
        user_message=None if status == "ok" else "Заполните поля вручную или уточните запрос.",
    )


def normalize_from_document_check(raw: dict[str, Any]) -> UnifiedAIResponse:
    llm = bool(raw.get("llm_invoked", False))
    cit = _citations_to_dicts(raw.get("citations") or [])
    status = "ok" if llm else "insufficient_data"
    issues = list(raw.get("detected_issues") or [])
    return UnifiedAIResponse(
        status=status,
        summary="",
        persona=raw.get("persona"),
        mode=raw.get("mode"),
        llm_invoked=llm,
        citations=cit,
        risks=issues,
        recommendations=list(raw.get("recommended_fixes") or []),
        missing_information=list(raw.get("missing_fields") or []),
        raw_response=raw,
    )


def fallback_unavailable(
    *,
    reason: str,
    user_message: str,
    retryable: bool,
    suggestions: list[str] | None = None,
) -> UnifiedAIResponse:
    return UnifiedAIResponse(
        status="unavailable",
        user_message=user_message,
        technical_reason=reason,
        retryable=retryable,
        suggestions=suggestions or ["Повторите позже", "Проверьте доступность rag-api и Ollama"],
    )


def fallback_disabled() -> UnifiedAIResponse:
    return UnifiedAIResponse(
        status="disabled",
        user_message="AI-модуль отключён конфигурацией (RAG_API_ENABLED=false).",
        technical_reason="disabled",
        retryable=False,
        suggestions=["Включите RAG_API_ENABLED и задайте RAG_API_BASE_URL"],
    )


def fallback_invalid_upstream(detail: str) -> UnifiedAIResponse:
    return UnifiedAIResponse(
        status="invalid_upstream",
        user_message="Сервис знаний вернул неожиданный ответ. Попробуйте упростить запрос.",
        technical_reason=detail[:2000],
        retryable=False,
    )
