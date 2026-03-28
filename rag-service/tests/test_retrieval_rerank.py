from app.core.config import settings
from app.services.retrieval.rerank import rerank_chunks


def test_rerank_orders_by_score():
    rows = [
        {
            "dist": 0.9,
            "chunk_text": "договор перевозки срок претензия",
            "category": "legal",
        },
        {
            "dist": 0.2,
            "chunk_text": "несвязанный текст про погоду",
            "category": "legal",
        },
    ]
    out = rerank_chunks(
        rows,
        normalized_query="срок претензии по договору перевозки",
        category_filter="legal",
        final_k=2,
    )
    assert out[0]["rerank_score"] >= out[1]["rerank_score"]
