from __future__ import annotations

from app.schemas.api import CitationItem


def citations_from_chunks(chunks: list[dict]) -> list[CitationItem]:
    out: list[CitationItem] = []
    for ch in chunks:
        text = ch.get("chunk_text") or ""
        excerpt = text[:500] + ("…" if len(text) > 500 else "")
        out.append(
            CitationItem(
                document_id=str(ch.get("document_id")),
                file_name=ch.get("file_name") or "",
                source_path=ch.get("source_path") or "",
                section_title=ch.get("section_title"),
                article_ref=ch.get("article_ref"),
                chunk_index=int(ch.get("chunk_index", 0)),
                chunk_id=int(ch.get("chunk_id", 0)),
                excerpt=excerpt,
            )
        )
    return out
