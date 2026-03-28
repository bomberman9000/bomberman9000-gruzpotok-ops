from __future__ import annotations

from app.core.config import settings


def keyword_overlap_score(query: str, text: str) -> float:
    q_words = [w for w in query.lower().split() if len(w) > 1]
    if not q_words:
        return 0.0
    tl = text.lower()
    hits = sum(1 for w in q_words if w in tl)
    return hits / len(q_words)


def category_bonus(
    doc_category: str,
    *,
    filter_category: str | None,
) -> float:
    if not filter_category:
        return 0.0
    return settings.rerank_gamma if doc_category == filter_category else 0.0


def persona_rerank_bonus(persona: str | None, row: dict) -> float:
    """Лёгкий сдвиг скоринга под политику персоны (guardrails на уровне retrieval)."""
    if not persona:
        return 0.0
    cat = row.get("category") or ""
    st = row.get("source_type") or ""
    b = 0.0
    if persona == "legal":
        if cat == "legal":
            b += 0.08
        if st in ("law", "contract"):
            b += 0.05
        if st == "template":
            b += 0.02
    elif persona == "logistics":
        if cat == "freight":
            b += 0.08
        if cat == "general":
            b += 0.02
        if st in ("template", "internal"):
            b += 0.04
        if st == "law":
            b += 0.02
    elif persona == "antifraud":
        if st == "internal":
            b += 0.09
        if cat == "freight":
            b += 0.05
        if cat == "legal":
            b += 0.03
        if cat == "general":
            b -= 0.03
        if st == "other" and cat != "freight":
            b -= 0.02
    return b


def rerank_chunks(
    rows: list[dict],
    *,
    normalized_query: str,
    category_filter: str | None,
    final_k: int,
    persona: str | None = None,
) -> list[dict]:
    """
    rows must include: dist (cosine distance from pgvector), chunk_text, category (doc).
    """
    a, b = settings.rerank_alpha, settings.rerank_beta
    out: list[dict] = []
    for r in rows:
        dist = float(r["dist"])
        vec_sim = max(0.0, 1.0 - dist / 2.0)
        kw = keyword_overlap_score(normalized_query, r.get("chunk_text", ""))
        bonus = category_bonus(r.get("category", ""), filter_category=category_filter)
        pb = persona_rerank_bonus(persona, r)
        score = a * vec_sim + b * kw + bonus + pb
        r2 = dict(r)
        r2["rerank_score"] = score
        r2["vector_similarity"] = vec_sim
        r2["keyword_score"] = kw
        r2["persona_bonus"] = pb
        out.append(r2)
    out.sort(key=lambda x: -x["rerank_score"])
    return out[:final_k]
