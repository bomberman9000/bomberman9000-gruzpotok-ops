"""Постобработка ответов logistics: мелкие UX-фиксы, когда LLM игнорирует prompt."""

from __future__ import annotations

import re


def _has_price_like_number(text: str) -> bool:
    lo = text.lower()
    if re.search(r"\d+\s*[–-]\s*\d+", lo):
        return True
    if re.search(r"\d{1,3}\s*тыс", lo):
        return True
    return False


def is_ultra_general_pricing_query(normalized_query: str) -> bool:
    """Ультра-общие запросы без конкретного маршрута (guardrail без числа)."""
    s = " ".join(normalized_query.lower().replace("ё", "е").split())
    if "по россии" in s:
        return True
    if "по рф" in s and len(s) < 100:
        return True
    return False


def sanitize_logistics_answer(answer: str, normalized_query: str) -> str:
    """
    Для ультра-общих запросов убрать ложный префикс «Ориентир:» / «Ставка:», если нет вилки/тыс.
    """
    if not is_ultra_general_pricing_query(normalized_query):
        return answer
    if _has_price_like_number(answer):
        return answer
    t = answer.strip()
    m = re.match(r"(?is)^(ориентир|ставка)\s*:\s*", t)
    if m:
        body = t[m.end() :].lstrip()
        return ("Нужны уточнения: " + body) if body else (
            "Нужны уточнения: маршрут, тип ТС, вес/объём груза, даты."
        )
    m2 = re.match(r"(?is)^режим\s+ответа\s*:[^\n]*\n+", t)
    if m2:
        rest = t[m2.end() :].lstrip()
        om = re.match(r"(?is)^ориентир\s*:\s*", rest)
        if om and not _has_price_like_number(rest):
            body = rest[om.end() :].lstrip()
            return ("Нужны уточнения: " + body) if body else answer
    return answer
