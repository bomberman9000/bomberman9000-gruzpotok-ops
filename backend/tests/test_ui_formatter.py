from app.schemas.unified import AIMeta, AIEnvelope, TelegramMiniAppPresentation, UnifiedAIResponse
from app.services.presentation.ui_formatter import build_ui_card


def test_ui_card_has_footer_actions():
    p = TelegramMiniAppPresentation(
        title="T",
        short_summary="S",
        severity="warning",
        actions=[],
        citations_short=[],
    )
    d = UnifiedAIResponse(status="insufficient_data", presentation=p)
    m = AIMeta(request_id="r1", endpoint="query", latency_ms=1, citations_count=0, rag_path="/q")
    card = build_ui_card(AIEnvelope(meta=m, data=d))
    assert card.footer_meta.get("request_id") == "r1"
    assert "actions" in card.footer_meta
