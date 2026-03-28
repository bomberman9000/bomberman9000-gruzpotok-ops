from app.services.retrieval.rerank import persona_rerank_bonus


def _row(*, category: str, source_type: str) -> dict:
    return {"category": category, "source_type": source_type}


def test_antifraud_boosts_internal_over_general_category():
    internal = persona_rerank_bonus("antifraud", _row(category="freight", source_type="internal"))
    general = persona_rerank_bonus("antifraud", _row(category="general", source_type="other"))
    assert internal > general


def test_legal_boosts_law():
    law = persona_rerank_bonus("legal", _row(category="legal", source_type="law"))
    other = persona_rerank_bonus("legal", _row(category="general", source_type="other"))
    assert law > other


def test_logistics_boosts_freight():
    fr = persona_rerank_bonus("logistics", _row(category="freight", source_type="template"))
    gen = persona_rerank_bonus("logistics", _row(category="general", source_type="other"))
    assert fr > gen


def test_no_persona_zero_bonus():
    assert persona_rerank_bonus(None, _row(category="legal", source_type="law")) == 0.0
