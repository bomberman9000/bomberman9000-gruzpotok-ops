from __future__ import annotations

from psycopg2.extras import RealDictCursor

from app.core.config import settings
from app.db.pool import get_conn
from app.services.retrieval.rerank import rerank_chunks
from app.utils.text import normalize_query

_VALID_CATS = frozenset({"legal", "freight", "general"})
_VALID_ST = frozenset({"law", "contract", "template", "internal", "other"})


def _sanitize_list(values: list[str] | None, allowed: frozenset[str]) -> list[str] | None:
    if not values:
        return None
    out = [v for v in values if v in allowed]
    return out or None


def vector_search(
    embedding: list[float],
    *,
    top_k: int,
    categories: list[str] | None = None,
    source_types: list[str] | None = None,
) -> list[dict]:
    cats = _sanitize_list(categories, _VALID_CATS)
    sts = _sanitize_list(source_types, _VALID_ST)

    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        sql = """
            SELECT
                c.id AS chunk_id,
                c.chunk_text,
                c.chunk_index,
                c.section_title,
                c.article_ref,
                c.embedding <=> %s::vector AS dist,
                d.id AS document_id,
                d.file_name,
                d.source_path,
                d.category,
                d.source_type,
                d.title AS document_title
            FROM document_chunks c
            INNER JOIN documents d ON d.id = c.document_id
            WHERE d.is_active = TRUE
        """
        params: list = [embedding]
        if cats:
            sql += " AND d.category = ANY(%s)"
            params.append(cats)
        if sts:
            sql += " AND d.source_type = ANY(%s)"
            params.append(sts)
        sql += """
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """
        params.extend([embedding, top_k])
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]


def retrieve_for_query(
    query_embedding: list[float],
    raw_query: str,
    *,
    top_k: int | None = None,
    final_k: int | None = None,
    categories: list[str] | None = None,
    source_types: list[str] | None = None,
    persona: str | None = None,
) -> tuple[list[dict], str]:
    tk = top_k if top_k is not None else settings.rag_top_k
    fk = final_k if final_k is not None else settings.rag_final_k
    nq = normalize_query(raw_query)
    rows = vector_search(
        query_embedding,
        top_k=tk,
        categories=categories,
        source_types=source_types,
    )
    ranked = rerank_chunks(
        rows,
        normalized_query=nq,
        category_filter=categories[0] if categories and len(categories) == 1 else None,
        final_k=fk,
        persona=persona,
    )
    return ranked, nq


def strict_retrieval_ok(rows: list[dict]) -> bool:
    if not rows:
        return False
    best = rows[0]
    score = float(best.get("rerank_score", 0.0))
    dist = float(best.get("dist", 99.0))
    if score < settings.strict_min_rerank_score:
        return False
    if dist > settings.strict_max_vector_distance:
        return False
    return True
