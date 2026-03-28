from app.services.ingestion.runner import should_index_relative_knowledge_path


def test_allows_normal_paths():
    assert should_index_relative_knowledge_path("freight.md") is True
    assert should_index_relative_knowledge_path("internal/freight_market_orienters_ru.md") is True
    assert should_index_relative_knowledge_path("examples/legal/test_claim_deadline.txt") is True


def test_skips_examples_freight():
    assert should_index_relative_knowledge_path("examples/freight/test_transport_rules.md") is False
