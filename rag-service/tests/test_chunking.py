from app.services.ingestion.chunking import split_into_chunks


def test_chunking_overlap_produces_multiple_pieces():
    text = "параграф один.\n\n" + ("слово " * 800)
    chunks = split_into_chunks(text, max_chars=200, overlap=40, path_hint="legal/test.md")
    assert len(chunks) >= 1
    assert all(len(c.text) <= 250 for c in chunks)


def test_legal_article_hint():
    text = "Статья 15. Текст про обязанности перевозчика."
    chunks = split_into_chunks(text, path_hint="legal_pravo/uk.md")
    assert chunks
    assert chunks[0].article_ref == "15" or "15" in chunks[0].text
