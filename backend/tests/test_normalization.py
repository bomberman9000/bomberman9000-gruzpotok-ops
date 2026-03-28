from app.services.ai.normalization import (
    normalize_from_claim_review,
    normalize_from_query,
    normalize_from_route_advice,
    normalize_from_transport_order_compose,
)


def test_query_insufficient_when_strict_refusal():
    raw = {
        "answer": "В локальной базе знаний недостаточно релевантных материалов",
        "citations": [],
        "model": "m",
        "mode": "strict",
        "llm_invoked": False,
    }
    u = normalize_from_query(raw)
    assert u.status == "insufficient_data"
    assert u.llm_invoked is False


def test_claim_review_insufficient_without_llm():
    raw = {
        "summary": "x",
        "legal_risks": [],
        "missing_information": ["a"],
        "recommended_position": "",
        "citations": [],
        "llm_invoked": False,
        "persona": "legal",
        "mode": "strict",
    }
    u = normalize_from_claim_review(raw)
    assert u.status == "insufficient_data"


def test_route_advice_validation_missing():
    raw = {
        "summary": "Заполните поля",
        "operational_advice": [],
        "missing_information": ["route_request пустое"],
        "risks": [],
        "citations": [],
        "llm_invoked": False,
        "persona": "logistics",
        "mode": "balanced",
    }
    u = normalize_from_route_advice(raw)
    assert u.status == "insufficient_data"


def test_transport_order_compose_ok_with_filled_fields():
    raw = {
        "fields": {"customer_name": "ООО Тест", "loading_address": "Москва"},
        "missing_information": [],
        "citations": [],
        "llm_invoked": True,
        "persona": "logistics",
        "mode": "draft",
    }
    u = normalize_from_transport_order_compose(raw)
    assert u.status == "ok"
    assert u.raw_response is not None
