import re


def normalize_query(q: str) -> str:
    q = q.strip().lower()
    q = re.sub(r"\s+", " ", q)
    return q


def approximate_token_count(text: str) -> int:
    """Rough estimate without tiktoken (offline-friendly)."""
    if not text:
        return 0
    words = len(text.split())
    return max(1, int(words * 1.3))


def extract_article_ref(text: str) -> str | None:
    """Best-effort for Russian legal snippets."""
    m = re.search(
        r"(?:статья|Статья|ст\.\s*|ст\s+)\s*(\d+(?:\.\d+)*)",
        text[:2000],
        re.IGNORECASE,
    )
    if m:
        return m.group(1)
    m2 = re.search(r"\bст\.\s*(\d+(?:\.\d+)?)\b", text[:500], re.IGNORECASE)
    if m2:
        return m2.group(1)
    return None


def extract_section_title(text: str) -> str | None:
    m = re.search(r"^#+\s*(.+)$", text[:800], re.MULTILINE)
    if m:
        return m.group(1).strip()[:500]
    return None
