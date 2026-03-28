from __future__ import annotations

import re
from dataclasses import dataclass

from app.utils.text import extract_article_ref, extract_section_title


@dataclass
class ChunkPiece:
    text: str
    section_title: str | None
    article_ref: str | None


def split_into_chunks(
    text: str,
    *,
    max_chars: int = 1400,
    overlap: int = 200,
    path_hint: str = "",
) -> list[ChunkPiece]:
    text = text.strip()
    if not text:
        return []

    legal_hint = any(
        x in path_hint.lower()
        for x in ("legal", "pravo", "law", "юр", "кодекс", "фз", "konstit")
    )

    # Split on markdown headings (line-start) or double newlines for long runs
    parts = re.split(r"(?m)(?=^#{1,6}\s+\S)", text)
    blocks: list[tuple[str | None, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        sec_title = None
        if part.startswith("#"):
            line_end = part.find("\n")
            first = part[:line_end] if line_end != -1 else part
            sec_title = re.sub(r"^#+\s*", "", first).strip()[:500]
            body = part[line_end + 1 :].strip() if line_end != -1 else ""
            if body:
                blocks.append((sec_title, body))
            else:
                blocks.append((sec_title, first))
        else:
            blocks.append((None, part))

    if not blocks:
        blocks = [(None, text)]

    pieces: list[ChunkPiece] = []
    for sec_title, body in blocks:
        sub = _window_chunks(body, max_chars=max_chars, overlap=overlap)
        for sc in sub:
            ar = extract_article_ref(sc) if legal_hint else None
            st = extract_section_title(sc) or sec_title
            pieces.append(ChunkPiece(text=sc, section_title=st, article_ref=ar))

    return pieces


def _window_chunks(text: str, max_chars: int, overlap: int) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []
    out: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        chunk = text[start:end].strip()
        if chunk:
            out.append(chunk)
        if end >= n:
            break
        start = max(0, end - overlap)
    return out if out else [text[:max_chars]]
