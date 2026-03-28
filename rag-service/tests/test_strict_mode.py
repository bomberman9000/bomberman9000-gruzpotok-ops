from app.services.retrieval.pipeline import strict_retrieval_ok


def test_strict_empty_fails():
    assert strict_retrieval_ok([]) is False


def test_strict_good_chunk():
    rows = [
        {
            "dist": 0.15,
            "rerank_score": 0.9,
            "chunk_text": "x",
        }
    ]
    assert strict_retrieval_ok(rows) is True
