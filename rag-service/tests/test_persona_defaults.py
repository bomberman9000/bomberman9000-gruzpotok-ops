from pathlib import Path

from app.core.config import settings
from app.schemas.api import QueryRequest
from app.services.personas.registry import (
    get_persona,
    resolve_effective_filters,
    validate_filters_for_persona,
)
from app.services.rag_executor import effective_mode


def test_effective_mode_explicit_overrides_persona():
    assert effective_mode(mode="balanced", persona="legal") == "balanced"


def test_effective_mode_legal_defaults_strict():
    assert effective_mode(mode=None, persona="legal") == "strict"


def test_effective_mode_logistics_defaults_balanced():
    assert effective_mode(mode=None, persona="logistics") == "balanced"


def test_effective_mode_antifraud_defaults_strict():
    assert effective_mode(mode=None, persona="antifraud") == "strict"


def test_effective_mode_no_persona_uses_settings():
    assert effective_mode(mode=None, persona=None) == settings.rag_mode_default


def test_resolve_filters_legal_defaults():
    cats, sts = resolve_effective_filters("legal", category=None, source_type=None)
    assert set(cats or []) == {"legal"}
    assert set(sts or []) == {"law", "contract", "template", "internal"}


def test_resolve_filters_explicit_ok():
    cats, sts = resolve_effective_filters("legal", category="legal", source_type="law")
    assert cats == ["legal"]
    assert sts == ["law"]


def test_validate_rejects_bad_category_for_legal():
    try:
        validate_filters_for_persona("legal", category="general", source_type=None)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_persona_config_has_prompt_template():
    assert get_persona("logistics").prompt_template == "logistics"


def test_logistics_system_prompt_has_pricing_discipline():
    root = Path(__file__).resolve().parents[1]
    path = root / "app" / "services" / "generation" / "prompts" / "logistics.txt"
    text = path.read_text(encoding="utf-8")
    assert "Один финальный pricing output" in text
    assert "несколько альтернативных диапазонов" in text
    assert "по России" in text
    assert "Один режим на ответ" in text
    assert "релевантного тарифного якоря" in text
    assert "не утверждай" in text
    assert "Соответствие маршрута" in text
    assert "Исключение (guardrail)" in text
    assert "Запрещённый пример" in text
    assert "Объём из габаритов" in text
    assert "Характер груза" in text
    assert "transport-order-pdf" in text
    assert "не умеет и не должна" in text
    assert "pdf_engine" in text

    legal_path = root / "app" / "services" / "generation" / "prompts" / "legal.txt"
    legal_text = legal_path.read_text(encoding="utf-8")
    assert "причинно-следственной связи" in legal_text
    assert "summary" in legal_text and "вложенного JSON" in legal_text
    assert "Составление исходящей претензии" in legal_text
    assert "draft_claim_text" in legal_text


def test_query_request_backward_compat_omits_mode_uses_balanced_via_executor():
    q = QueryRequest(query="hello")
    assert q.mode is None
    assert q.persona is None
    assert effective_mode(mode=q.mode, persona=q.persona) == settings.rag_mode_default
