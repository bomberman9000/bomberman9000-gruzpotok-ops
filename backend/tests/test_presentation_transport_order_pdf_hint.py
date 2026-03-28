from app.schemas.unified import UnifiedAIResponse
from app.services.presentation.core import attach_presentation


def test_transport_order_compose_sets_pdf_hint_when_ok():
    raw = {
        "fields": {"customer_name": "ООО Тест", "loading_address": "Москва", "unloading_address": "Казань"},
        "missing_information": [],
        "llm_invoked": True,
    }
    data = UnifiedAIResponse(status="ok", summary="x", raw_response=raw)
    attach_presentation(
        data,
        endpoint="transport_order_compose",
        request_id="rid-1",
        user_input={"kind": "transport_order_compose"},
    )
    assert data.presentation is not None
    assert data.presentation.title == "Договор-заявка на перевозку груза"
    assert data.presentation.pdf_attachment_hint is not None
    assert data.presentation.pdf_attachment_hint.page_count_typical == 1
    assert "transport-order-pdf" in data.presentation.pdf_attachment_hint.download_path
    assert data.presentation.scenario == "transport_order_compose"


def test_transport_order_compose_no_pdf_hint_when_insufficient():
    raw = {"fields": {}, "missing_information": ["мало данных"], "llm_invoked": False}
    data = UnifiedAIResponse(status="insufficient_data", summary="x", raw_response=raw)
    attach_presentation(
        data,
        endpoint="transport_order_compose",
        request_id="rid-2",
        user_input={"kind": "transport_order_compose"},
    )
    assert data.presentation is not None
    assert data.presentation.pdf_attachment_hint is None
