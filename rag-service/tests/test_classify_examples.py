from pathlib import Path

from app.services.ingestion.classify import category_from_relative_path, source_type_from_path


def test_examples_paths():
    assert (
        category_from_relative_path(Path("examples/legal/test_claim_deadline.txt")) == "legal"
    )
    assert (
        category_from_relative_path(Path("examples/freight/test_transport_rules.md"))
        == "freight"
    )
    assert (
        category_from_relative_path(Path("examples/general/test_company_note.txt"))
        == "general"
    )
    assert source_type_from_path(Path("examples/legal/x.txt")) == "law"
    assert source_type_from_path(Path("examples/general/x.txt")) == "internal"
    assert source_type_from_path(Path("examples/freight/x.md")) == "other"
