from app.schemas.unified import AIMeta, AIEnvelope, TelegramMiniAppPresentation, UnifiedAIResponse
from app.services.presentation.telegram_formatter import render_ai_result_for_telegram, render_fallback_plain


def _env(status: str) -> AIEnvelope:
    p = TelegramMiniAppPresentation(
        title="T",
        short_summary="S",
        status_label="X",
        warnings=["w"],
        next_steps=["n"],
        citations_short=[],
    )
    d = UnifiedAIResponse(status=status, user_message="u", presentation=p)
    m = AIMeta(request_id="r1", endpoint="query", latency_ms=1, citations_count=0, rag_path="/q")
    return AIEnvelope(meta=m, data=d)


def test_render_not_empty():
    out = render_ai_result_for_telegram(_env("ok"))
    assert "T" in out
    assert "Предупреждения" in out or "Что делать дальше" in out


def test_fallback_unavailable():
    d = UnifiedAIResponse(status="unavailable", user_message="down")
    m = AIMeta(request_id="r2", endpoint="query", latency_ms=1, citations_count=0, rag_path="/q")
    env = AIEnvelope(meta=m, data=d)
    plain = render_fallback_plain(env)
    assert "down" in plain
