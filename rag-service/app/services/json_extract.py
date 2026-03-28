from __future__ import annotations

import json
import re
from typing import Any


def _strip_markdown_fence(t: str) -> str:
    t = t.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```\s*$", "", t)
    return t.strip()


def _repair_truncated_json_object(t: str) -> str:
    """LLM иногда обрывает ответ до закрывающей «}»."""
    t = t.rstrip()
    if not t:
        return t
    if t.endswith("}"):
        return t
    if t.startswith("{") and t.count("{") > t.count("}"):
        return t + ("}" * (t.count("{") - t.count("}")))
    return t


def parse_json_object(text: str) -> dict[str, Any]:
    t = _strip_markdown_fence(text or "")
    if not t:
        raise ValueError("empty text")
    t = _repair_truncated_json_object(t)

    try:
        out = json.loads(t)
        if isinstance(out, dict):
            return out
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for i, ch in enumerate(t):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(t, i)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue

    i, j = t.find("{"), t.rfind("}")
    if i != -1 and j != -1 and j > i:
        out = json.loads(t[i : j + 1])
        if isinstance(out, dict):
            return out
    raise ValueError("cannot parse JSON object from model output")


def _unwrap_nested_claim_json_in_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Модель иногда кладёт весь JSON повторно в строковое поле summary."""
    s = data.get("summary")
    if not isinstance(s, str):
        return data
    st = s.strip()
    if not st.startswith("{"):
        return data
    try:
        inner = parse_json_object(st)
    except Exception:
        return data
    if isinstance(inner, dict) and "summary" in inner:
        return inner
    return data


def parse_claim_review_model_output(text: str) -> dict[str, Any]:
    data = parse_json_object(text)
    return _unwrap_nested_claim_json_in_summary(data)


def as_str_list(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []
