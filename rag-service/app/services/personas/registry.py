from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PersonaId = Literal["legal", "logistics", "antifraud"]


@dataclass(frozen=True)
class PersonaConfig:
    id: PersonaId
    prompt_template: str  # file name without .txt
    allowed_categories: frozenset[str]
    allowed_source_types: frozenset[str]
    default_mode: Literal["balanced", "strict", "draft"]
    response_format_hint: str


_PERSONAS: dict[PersonaId, PersonaConfig] = {
    "legal": PersonaConfig(
        id="legal",
        prompt_template="legal",
        allowed_categories=frozenset({"legal"}),
        allowed_source_types=frozenset({"law", "contract", "template", "internal"}),
        default_mode="strict",
        response_format_hint="Точный ответ с опорой на цитаты; без выдуманных статей.",
    ),
    "logistics": PersonaConfig(
        id="logistics",
        prompt_template="logistics",
        allowed_categories=frozenset({"freight", "general"}),
        allowed_source_types=frozenset({"law", "template", "internal", "other"}),
        default_mode="balanced",
        response_format_hint="Коротко, по шагам, при необходимости checklist.",
    ),
    "antifraud": PersonaConfig(
        id="antifraud",
        prompt_template="antifraud",
        allowed_categories=frozenset({"legal", "freight", "general"}),
        allowed_source_types=frozenset({"internal", "other", "law", "template"}),
        default_mode="strict",
        response_format_hint="Красные флаги, риски, предварительность при недостатке данных.",
    ),
}


def get_persona(persona: PersonaId) -> PersonaConfig:
    return _PERSONAS[persona]


def validate_filters_for_persona(
    persona: PersonaId | None,
    *,
    category: str | None,
    source_type: str | None,
) -> None:
    if not persona:
        return
    p = get_persona(persona)
    if category is not None and category not in p.allowed_categories:
        raise ValueError(
            f"category={category!r} не разрешена для persona={persona!r}; "
            f"допустимо: {sorted(p.allowed_categories)}"
        )
    if source_type is not None and source_type not in p.allowed_source_types:
        raise ValueError(
            f"source_type={source_type!r} не разрешён для persona={persona!r}; "
            f"допустимо: {sorted(p.allowed_source_types)}"
        )


def resolve_effective_filters(
    persona: PersonaId | None,
    *,
    category: str | None,
    source_type: str | None,
) -> tuple[list[str] | None, list[str] | None]:
    """
    Если persona задана и фильтры не переданы — берём политику персоны (списки для IN).
    Если persona нет — как раньше: одиночные фильтры или без ограничения.
    """
    if persona:
        p = get_persona(persona)
        cats: list[str] | None = list(p.allowed_categories) if not category else [category]
        sts: list[str] | None = list(p.allowed_source_types) if not source_type else [source_type]
        return cats, sts
    cats = [category] if category else None
    sts = [source_type] if source_type else None
    return cats, sts
