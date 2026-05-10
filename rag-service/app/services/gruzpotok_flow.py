from __future__ import annotations

import logging
from typing import Any

import httpx

from app.schemas.api import (
    FreightDocumentCheckRequest,
    FreightDocumentCheckResponse,
    FreightRiskCheckRequest,
    FreightRiskCheckResponse,
    FreightRouteAdviceRequest,
    FreightRouteAdviceResponse,
    FreightTransportOrderComposeRequest,
    FreightTransportOrderComposeResponse,
    FreightTransportOrderFields,
    LegalClaimComposeRequest,
    LegalClaimComposeResponse,
    LegalClaimDraftRequest,
    LegalClaimDraftResponse,
    LegalClaimReviewRequest,
    LegalClaimReviewResponse,
    PersonaId,
    RetrievalDebug,
    RiskLevel,
)
from app.services.business.rules import (
    validate_claim_compose_input,
    validate_claim_review_input,
    validate_route_advice_input,
    validate_transport_order_compose_input,
)
from app.services.document_input_policy import (
    DocumentInputRouteError,
    log_document_prompt_input,
    resolve_document_capable_input,
)
from app.services.json_extract import as_str_list, parse_claim_review_model_output, parse_json_object
from app.services.rag_executor import RagExecuteResult, execute_rag_query

logger = logging.getLogger(__name__)


def _dbg(res: RagExecuteResult, debug: bool) -> RetrievalDebug | None:
    return res.retrieval_debug if debug else None


def _freight_transport_order_llm_json_schema() -> str:
    keys = tuple(FreightTransportOrderFields.model_fields.keys())
    inner = ",".join(f'"{k}":"строка"' for k in keys)
    return "{" + inner + ',"missing_information":["строка"]}'


def _coerce_risk(v: Any) -> RiskLevel:
    s = str(v or "").lower().strip()
    if s in ("low", "medium", "high"):
        return s  # type: ignore[return-value]
    return "medium"


async def legal_claim_review(
    client: httpx.AsyncClient,
    body: LegalClaimReviewRequest,
) -> LegalClaimReviewResponse:
    persona: PersonaId = "legal"
    try:
        claim_text, source_info = resolve_document_capable_input(
            body.claim_text,
            route_label="legal_claim_review",
            logger=logger,
        )
    except DocumentInputRouteError as e:
        return LegalClaimReviewResponse(
            summary=f"Не удалось извлечь текст документа: {e}",
            legal_risks=[],
            missing_information=[f"document_input_error={e.code}"],
            recommended_position="Исправьте источник документа и повторите запрос.",
            citations=[],
            llm_invoked=False,
            persona=persona,
            mode="strict",
            retrieval_debug=None,
        )
    miss = validate_claim_review_input(claim_text)
    q = (
        f"Разбор претензии для внутреннего чек-листа (не финальная юрпозиция).\n"
        f"Текст претензии:\n{claim_text.strip()}\n\n"
        f"Контекст договора/условий:\n{(body.contract_context or '').strip()}\n\n"
        f"Контрагент: {(body.counterparty or '').strip()}"
    )
    log_document_prompt_input(
        logger,
        handler_name="legal_claim_review",
        task="claim_review",
        source_info=source_info,
        input_text=claim_text,
        prompt_text=q,
    )
    if miss:
        return LegalClaimReviewResponse(
            summary="Недостаточно входных данных для разбора.",
            legal_risks=[],
            missing_information=miss,
            recommended_position="Уточните данные и повторите запрос.",
            citations=[],
            llm_invoked=False,
            persona=persona,
            mode="strict",
            retrieval_debug=None,
        )

    res = await execute_rag_query(
        client,
        query=q,
        mode="strict",
        category=None,
        source_type=None,
        persona=persona,
        top_k=None,
        final_k=None,
        debug=body.debug,
        strict_min_chunks=2,
        json_schema=(
            '{"summary":"строка","legal_risks":["строка"],'
            '"missing_information":["строка"],"recommended_position":"строка"}'
        ),
    )

    if res.insufficient_data or not res.llm_invoked:
        return LegalClaimReviewResponse(
            summary=res.answer,
            legal_risks=[],
            missing_information=["Недостаточно релевантных материалов в базе для строгого разбора."],
            recommended_position="Добавьте документы в knowledge или уточните запрос.",
            citations=res.citations,
            llm_invoked=False,
            persona=persona,
            mode=res.mode,
            retrieval_debug=_dbg(res, body.debug),
        )

    try:
        data = parse_claim_review_model_output(res.answer)
    except Exception:
        return LegalClaimReviewResponse(
            summary=res.answer[:2000],
            legal_risks=[],
            missing_information=["Не удалось разобрать JSON-ответ модели."],
            recommended_position="Повторите запрос или уменьшите объём текста.",
            citations=res.citations,
            llm_invoked=True,
            persona=persona,
            mode=res.mode,
            retrieval_debug=_dbg(res, body.debug),
        )

    return LegalClaimReviewResponse(
        summary=str(data.get("summary") or "").strip() or res.answer[:500],
        legal_risks=as_str_list(data.get("legal_risks")),
        missing_information=as_str_list(data.get("missing_information")),
        recommended_position=str(data.get("recommended_position") or "").strip(),
        citations=res.citations,
        llm_invoked=True,
        persona=persona,
        mode=res.mode,
        retrieval_debug=_dbg(res, body.debug),
    )


async def legal_claim_draft(
    client: httpx.AsyncClient,
    body: LegalClaimDraftRequest,
) -> LegalClaimDraftResponse:
    persona: PersonaId = "legal"
    try:
        claim_text, source_info = resolve_document_capable_input(
            body.claim_text,
            route_label="legal_claim_draft",
            logger=logger,
        )
    except DocumentInputRouteError as e:
        return LegalClaimDraftResponse(
            draft_response_text=f"Не удалось извлечь текст документа: {e}",
            tone="n/a",
            legal_basis=[],
            disclaimers=[f"document_input_error={e.code}"],
            citations=[],
            llm_invoked=False,
            persona=persona,
            mode="draft",
        )
    q = (
        "Подготовь ЧЕРНОВИК ответа на претензию (не финальный юридический документ; требуется проверка юристом).\n"
        f"Текст претензии:\n{claim_text.strip()}\n"
        f"Компания: {(body.company_name or '').strip()}\n"
        f"Подписант: {(body.signer or '').strip()}"
    )
    log_document_prompt_input(
        logger,
        handler_name="legal_claim_draft",
        task="claim_draft",
        source_info=source_info,
        input_text=claim_text,
        prompt_text=q,
    )
    res = await execute_rag_query(
        client,
        query=q,
        mode="draft",
        category=None,
        source_type=None,
        persona=persona,
        top_k=None,
        final_k=None,
        debug=False,
        strict_min_chunks=1,
        json_schema=(
            '{"draft_response_text":"строка","tone":"строка",'
            '"legal_basis":["строка"],"disclaimers":["строка"]}'
        ),
    )

    if res.insufficient_data or not res.llm_invoked:
        return LegalClaimDraftResponse(
            draft_response_text=res.answer,
            tone="n/a",
            legal_basis=[],
            disclaimers=[
                "Черновик не сформирован: недостаточно материалов в базе. Это не юридическое заключение."
            ],
            citations=res.citations,
            llm_invoked=False,
            persona=persona,
            mode=res.mode,
        )

    try:
        data = parse_json_object(res.answer)
    except Exception:
        return LegalClaimDraftResponse(
            draft_response_text=res.answer,
            tone="черновик",
            legal_basis=[],
            disclaimers=["Ответ модели не в JSON; показан как текст. Это черновик, не финальная позиция."],
            citations=res.citations,
            llm_invoked=True,
            persona=persona,
            mode=res.mode,
        )

    return LegalClaimDraftResponse(
        draft_response_text=str(data.get("draft_response_text") or res.answer).strip(),
        tone=str(data.get("tone") or "деловой").strip(),
        legal_basis=as_str_list(data.get("legal_basis")),
        disclaimers=as_str_list(data.get("disclaimers"))
        or ["Черновик; требуется проверка юристом. Не является юридическим заключением."],
        citations=res.citations,
        llm_invoked=True,
        persona=persona,
        mode=res.mode,
    )


async def legal_claim_compose(
    client: httpx.AsyncClient,
    body: LegalClaimComposeRequest,
) -> LegalClaimComposeResponse:
    """Черновик текста исходящей претензии (не ответа контрагенту)."""
    persona: PersonaId = "legal"
    try:
        facts, source_info = resolve_document_capable_input(
            body.facts,
            route_label="legal_claim_compose",
            logger=logger,
        )
    except DocumentInputRouteError as e:
        return LegalClaimComposeResponse(
            draft_claim_text="",
            missing_facts=[f"document_input_error={e.code}"],
            disclaimers=["Не удалось извлечь текст документа. Исправьте источник и повторите запрос."],
            citations=[],
            llm_invoked=False,
            persona=persona,
            mode="draft",
        )

    miss = validate_claim_compose_input(facts)
    if miss:
        return LegalClaimComposeResponse(
            draft_claim_text="",
            missing_facts=miss,
            disclaimers=["Черновик не сформирован: недостаточно входных данных."],
            citations=[],
            llm_invoked=False,
            persona=persona,
            mode="draft",
        )

    q = (
        "Составь ЧЕРНОВИК текста ИСХОДЯЩЕЙ претензии (мы предъявляем требования контрагенту). "
        "Это не финальный юридический документ; только проект для правки юристом.\n"
        "Используй структуру из контекста базы (шапка, факты, нарушение, требования, приложения, подпись). "
        "Не выдумывай номера статей закона, конкретные сроки давности и суммы, если их нет во входе или в чанках. "
        "Недостающие реквизиты обозначай плейсхолдерами в квадратных скобках.\n\n"
        f"Факты и ситуация:\n{facts.strip()}\n\n"
        f"Контекст договора/условий:\n{(body.contract_context or '').strip()}\n\n"
        f"Заявитель (мы): {(body.claimant_company or '').strip()}\n"
        f"Контрагент: {(body.counterparty or '').strip()}\n"
        f"Адрес контрагента: {(body.counterparty_address or '').strip()}\n"
        f"Требования (если указаны): {(body.demands or '').strip()}\n"
        f"Приложения (заметка): {(body.attachments_note or '').strip()}"
    )
    log_document_prompt_input(
        logger,
        handler_name="legal_claim_compose",
        task="claim_compose",
        source_info=source_info,
        input_text=facts,
        prompt_text=q,
    )
    res = await execute_rag_query(
        client,
        query=q,
        mode="draft",
        category=None,
        source_type=None,
        persona=persona,
        top_k=None,
        final_k=None,
        debug=False,
        strict_min_chunks=1,
        json_schema=(
            '{"draft_claim_text":"строка — полный текст претензии деловым стилем",'
            '"missing_facts":["строка — чего не хватает для отправки или обоснования"],'
            '"disclaimers":["строка"]}'
        ),
    )

    if res.insufficient_data or not res.llm_invoked:
        return LegalClaimComposeResponse(
            draft_claim_text=res.answer,
            missing_facts=["Недостаточно релевантных материалов в базе для опоры на шаблон."],
            disclaimers=[
                "Черновик не сформирован или сформирован без опоры на базу. Это не юридическое заключение."
            ],
            citations=res.citations,
            llm_invoked=False,
            persona=persona,
            mode=res.mode,
        )

    try:
        data = parse_json_object(res.answer)
    except Exception:
        return LegalClaimComposeResponse(
            draft_claim_text=str(res.answer).strip(),
            missing_facts=[],
            disclaimers=[
                "Ответ модели не в JSON; показан как текст. Черновик; проверка юристом обязательна."
            ],
            citations=res.citations,
            llm_invoked=True,
            persona=persona,
            mode=res.mode,
        )

    disclaimers = as_str_list(data.get("disclaimers")) or [
        "Черновик претензии; требуется проверка юристом. Не является юридическим заключением."
    ]
    return LegalClaimComposeResponse(
        draft_claim_text=str(data.get("draft_claim_text") or res.answer).strip(),
        missing_facts=as_str_list(data.get("missing_facts")),
        disclaimers=disclaimers,
        citations=res.citations,
        llm_invoked=True,
        persona=persona,
        mode=res.mode,
    )


async def freight_transport_order_compose(
    client: httpx.AsyncClient,
    body: FreightTransportOrderComposeRequest,
) -> FreightTransportOrderComposeResponse:
    persona: PersonaId = "logistics"
    try:
        request_text, source_info = resolve_document_capable_input(
            body.request_text,
            route_label="freight_transport_order_compose",
            logger=logger,
        )
    except DocumentInputRouteError as e:
        return FreightTransportOrderComposeResponse(
            fields=FreightTransportOrderFields(),
            missing_information=[f"document_input_error={e.code}"],
            citations=[],
            llm_invoked=False,
            persona=persona,
            mode="draft",
            retrieval_debug=None,
        )

    miss = validate_transport_order_compose_input(request_text)
    if miss:
        return FreightTransportOrderComposeResponse(
            fields=FreightTransportOrderFields(),
            missing_information=miss,
            citations=[],
            llm_invoked=False,
            persona=persona,
            mode="draft",
            retrieval_debug=None,
        )

    q = (
        "Заполни поля заявки на перевозку груза по описанию пользователя. "
        "Верни ТОЛЬКО один JSON по схеме (поля + missing_information). "
        "Не генерируй PDF, не печатай бланк текстом, не рисуй таблицу для «печати» — файл PDF формирует "
        "сервер отдельно из этих полей (endpoint transport-order-pdf), языковая модель PDF не создаёт.\n"
        "Не выдумывай реквизиты, которых нет в тексте — оставь пустую строку и перечисли недостающее в "
        "missing_information. Числа и даты переноси как строки, как в запросе.\n\n"
        f"Описание от пользователя:\n{request_text.strip()}"
    )
    log_document_prompt_input(
        logger,
        handler_name="freight_transport_order_compose",
        task="transport_order_compose",
        source_info=source_info,
        input_text=request_text,
        prompt_text=q,
    )
    res = await execute_rag_query(
        client,
        query=q,
        mode="draft",
        category=None,
        source_type=None,
        persona=persona,
        top_k=None,
        final_k=None,
        debug=body.debug,
        strict_min_chunks=1,
        json_schema=_freight_transport_order_llm_json_schema(),
    )

    if res.insufficient_data or not res.llm_invoked:
        return FreightTransportOrderComposeResponse(
            fields=FreightTransportOrderFields(),
            missing_information=[
                "Недостаточно релевантных материалов в базе или отказ retrieval; заполните поля вручную для PDF."
            ],
            citations=res.citations,
            llm_invoked=False,
            persona=persona,
            mode=res.mode,
            retrieval_debug=_dbg(res, body.debug),
        )

    try:
        data = parse_json_object(res.answer)
    except Exception:
        return FreightTransportOrderComposeResponse(
            fields=FreightTransportOrderFields(),
            missing_information=["Не удалось разобрать JSON-ответ модели."],
            citations=res.citations,
            llm_invoked=True,
            persona=persona,
            mode=res.mode,
            retrieval_debug=_dbg(res, body.debug),
        )

    allowed = set(FreightTransportOrderFields.model_fields)
    raw: dict[str, str] = {}
    for k in allowed:
        v = data.get(k, "")
        raw[k] = str(v if v is not None else "").strip()
    try:
        fields = FreightTransportOrderFields.model_validate(raw)
    except Exception:
        fields = FreightTransportOrderFields()

    mi = as_str_list(data.get("missing_information"))
    return FreightTransportOrderComposeResponse(
        fields=fields,
        missing_information=mi,
        citations=res.citations,
        llm_invoked=True,
        persona=persona,
        mode=res.mode,
        retrieval_debug=_dbg(res, body.debug),
    )


async def freight_risk_check(
    client: httpx.AsyncClient,
    body: FreightRiskCheckRequest,
) -> FreightRiskCheckResponse:
    persona: PersonaId = "antifraud"
    q = (
        "Оценка риска/антифрод по ситуации (предварительно, по материалам базы).\n"
        f"Ситуация:\n{body.situation.strip()}\n\n"
        f"Контрагент:\n{(body.counterparty_info or '').strip()}\n\n"
        f"Маршрут/рейс:\n{(body.route or '').strip()}"
    )
    res = await execute_rag_query(
        client,
        query=q,
        mode="strict",
        category=None,
        source_type=None,
        persona=persona,
        top_k=None,
        final_k=None,
        debug=body.debug,
        strict_min_chunks=2,
        json_schema=(
            '{"risk_level":"low|medium|high","red_flags":["строка"],'
            '"recommended_checks":["строка"],"suggested_next_steps":["строка"]}'
        ),
    )

    if res.insufficient_data or not res.llm_invoked:
        return FreightRiskCheckResponse(
            risk_level="medium",
            red_flags=[res.answer],
            recommended_checks=[],
            suggested_next_steps=["Уточните данные и/или пополните базу знаний."],
            citations=res.citations,
            llm_invoked=False,
            persona=persona,
            mode=res.mode,
            retrieval_debug=_dbg(res, body.debug),
        )

    try:
        data = parse_json_object(res.answer)
    except Exception:
        return FreightRiskCheckResponse(
            risk_level="medium",
            red_flags=[res.answer[:1500]],
            recommended_checks=[],
            suggested_next_steps=[],
            citations=res.citations,
            llm_invoked=True,
            persona=persona,
            mode=res.mode,
            retrieval_debug=_dbg(res, body.debug),
        )

    return FreightRiskCheckResponse(
        risk_level=_coerce_risk(data.get("risk_level")),
        red_flags=as_str_list(data.get("red_flags")),
        recommended_checks=as_str_list(data.get("recommended_checks")),
        suggested_next_steps=as_str_list(data.get("suggested_next_steps")),
        citations=res.citations,
        llm_invoked=True,
        persona=persona,
        mode=res.mode,
        retrieval_debug=_dbg(res, body.debug),
    )


async def freight_route_advice(
    client: httpx.AsyncClient,
    body: FreightRouteAdviceRequest,
) -> FreightRouteAdviceResponse:
    persona: PersonaId = "logistics"
    miss = validate_route_advice_input(body.route_request, body.vehicle)
    if miss:
        return FreightRouteAdviceResponse(
            summary="Заполните обязательные поля для рекомендации по маршруту.",
            operational_advice=[],
            missing_information=miss,
            risks=[],
            citations=[],
            llm_invoked=False,
            persona=persona,
            mode="balanced",
            retrieval_debug=None,
        )

    q = (
        f"Операционная консультация по маршруту/перевозке.\n"
        f"Запрос: {body.route_request.strip()}\n"
        f"ТС: {body.vehicle.strip()}\n"
        f"Груз: {(body.cargo or '').strip()}\n"
        f"Ограничения: {(body.constraints or '').strip()}"
    )
    res = await execute_rag_query(
        client,
        query=q,
        mode="balanced",
        category=None,
        source_type=None,
        persona=persona,
        top_k=None,
        final_k=None,
        debug=False,
        strict_min_chunks=1,
        json_schema=(
            '{"summary":"строка","operational_advice":["строка"],'
            '"missing_information":["строка"],"risks":["строка"]}'
        ),
    )

    if res.insufficient_data or not res.llm_invoked:
        return FreightRouteAdviceResponse(
            summary=res.answer,
            operational_advice=[],
            missing_information=["Нет проиндексированных фрагментов или недостаточно релевантности."],
            risks=[],
            citations=res.citations,
            llm_invoked=False,
            persona=persona,
            mode=res.mode,
            retrieval_debug=None,
        )

    try:
        data = parse_json_object(res.answer)
    except Exception:
        return FreightRouteAdviceResponse(
            summary=res.answer[:2000],
            operational_advice=[],
            missing_information=[],
            risks=[],
            citations=res.citations,
            llm_invoked=True,
            persona=persona,
            mode=res.mode,
            retrieval_debug=None,
        )

    return FreightRouteAdviceResponse(
        summary=str(data.get("summary") or "").strip() or "См. операционные пункты ниже.",
        operational_advice=as_str_list(data.get("operational_advice")),
        missing_information=as_str_list(data.get("missing_information")),
        risks=as_str_list(data.get("risks")),
        citations=res.citations,
        llm_invoked=True,
        persona=persona,
        mode=res.mode,
        retrieval_debug=None,
    )


async def freight_document_check(
    client: httpx.AsyncClient,
    body: FreightDocumentCheckRequest,
) -> FreightDocumentCheckResponse:
    persona: PersonaId = "logistics"
    try:
        document_text, source_info = resolve_document_capable_input(
            body.document_text,
            route_label="freight_document_check",
            logger=logger,
        )
    except DocumentInputRouteError as e:
        return FreightDocumentCheckResponse(
            detected_issues=[f"Не удалось извлечь текст документа: {e}"],
            missing_fields=[f"document_input_error={e.code}"],
            recommended_fixes=["Проверьте формат файла, OCR/backend и повторите запрос."],
            compliance_notes=["Анализ не выполнялся: extraction layer не смог подготовить текст."],
            citations=[],
            llm_invoked=False,
            persona=persona,
            mode="balanced",
            retrieval_debug=None,
        )
    q = (
        "Проверка логистического/сопроводительного документа по материалам базы (best-effort).\n"
        f"Тип: {(body.document_type or '').strip()}\n"
        f"Текст документа:\n{document_text.strip()}"
    )
    log_document_prompt_input(
        logger,
        handler_name="freight_document_check",
        task="document_check",
        source_info=source_info,
        input_text=document_text,
        prompt_text=q,
    )
    res = await execute_rag_query(
        client,
        query=q,
        mode="balanced",
        category=None,
        source_type=None,
        persona=persona,
        top_k=None,
        final_k=None,
        debug=body.debug,
        strict_min_chunks=1,
        json_schema=(
            '{"detected_issues":["строка"],"missing_fields":["строка"],'
            '"recommended_fixes":["строка"],"compliance_notes":["строка"]}'
        ),
    )

    if res.insufficient_data or not res.llm_invoked:
        return FreightDocumentCheckResponse(
            detected_issues=[res.answer],
            missing_fields=[],
            recommended_fixes=[],
            compliance_notes=["Недостаточно контекста из базы; проверка ограничена."],
            citations=res.citations,
            llm_invoked=False,
            persona=persona,
            mode=res.mode,
            retrieval_debug=_dbg(res, body.debug),
        )

    try:
        data = parse_json_object(res.answer)
    except Exception:
        return FreightDocumentCheckResponse(
            detected_issues=[res.answer[:2000]],
            missing_fields=[],
            recommended_fixes=[],
            compliance_notes=["Ответ модели не в JSON; показан как текст."],
            citations=res.citations,
            llm_invoked=True,
            persona=persona,
            mode=res.mode,
            retrieval_debug=_dbg(res, body.debug),
        )

    return FreightDocumentCheckResponse(
        detected_issues=as_str_list(data.get("detected_issues")),
        missing_fields=as_str_list(data.get("missing_fields")),
        recommended_fixes=as_str_list(data.get("recommended_fixes")),
        compliance_notes=as_str_list(data.get("compliance_notes")),
        citations=res.citations,
        llm_invoked=True,
        persona=persona,
        mode=res.mode,
        retrieval_debug=_dbg(res, body.debug),
    )
