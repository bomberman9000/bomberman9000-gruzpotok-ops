from __future__ import annotations

from pathlib import Path

import httpx

from app.core.config import settings

SYSTEM_BALANCED = """Ты помощник по локальной офлайн-базе документов (юридические и логистические материалы).
Опирайся на переданный контекст. Если в контексте нет ответа — скажи об этом. Не выдумывай номера статей и нормы.
Это не юридическая консультация. Отвечай на русском, структурировано."""

SYSTEM_STRICT = """Ты отвечаешь СТРОГО по приведённым ниже фрагментам из локальной базы. Запрещено добавлять нормы, статьи, сроки и суммы, которых нет во фрагментах.
Если фрагментов недостаточно для ответа — напиши одно предложение: что в базе недостаточно релевантных материалов, и не заполняй пробелы догадками.
Можно кратко процитировать или пересказать только то, что есть в контексте. Не юридическая консультация."""

SYSTEM_DRAFT = """Ты помогаешь с черновиком ответа по материалам локальной базы. Можно формулировать свободнее, но явно отмечай неуверенность.
В конце напомни: текст требует ручной проверки и не является юридическим заключением."""


def mode_system(mode: str) -> str:
    if mode == "strict":
        return SYSTEM_STRICT
    if mode == "draft":
        return SYSTEM_DRAFT
    return SYSTEM_BALANCED


def load_prompt_template(name: str) -> str:
    path = Path(__file__).resolve().parent / "prompts" / f"{name}.txt"
    return path.read_text(encoding="utf-8")


def build_system_prompt(mode: str, persona: str | None) -> tuple[str, str | None]:
    """
    Возвращает (полный system prompt, имя шаблона персоны или None).
    """
    base_mode = mode_system(mode)
    if not persona:
        return base_mode, None
    body = load_prompt_template(persona).strip()
    combined = f"{body}\n\n---\n\nРежим ответа:\n{base_mode}"
    return combined, persona


async def embed_query(client: httpx.AsyncClient, text: str) -> list[float]:
    r = await client.post(
        f"{settings.ollama_base_url}/api/embeddings",
        json={"model": settings.embedding_model, "prompt": text},
        timeout=120.0,
    )
    r.raise_for_status()
    emb = r.json().get("embedding")
    dim = settings.embedding_dimensions
    if not emb or len(emb) != dim:
        raise RuntimeError(f"bad embedding dim: {len(emb) if emb else 0}")
    return emb


async def chat(
    client: httpx.AsyncClient,
    user_content: str,
    *,
    mode: str = "balanced",
    persona: str | None = None,
    system_override: str | None = None,
) -> str:
    if system_override is not None:
        system = system_override
    else:
        system, _ = build_system_prompt(mode, persona)
    r = await client.post(
        f"{settings.ollama_base_url}/api/chat",
        json={
            "model": settings.chat_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            "stream": False,
        },
        timeout=600.0,
    )
    r.raise_for_status()
    data = r.json()
    msg = data.get("message") or {}
    content = (msg.get("content") or "").strip()
    if not content:
        raise RuntimeError("empty chat response")
    return content


async def chat_raw(
    client: httpx.AsyncClient,
    *,
    system: str,
    user: str,
) -> str:
    r = await client.post(
        f"{settings.ollama_base_url}/api/chat",
        json={
            "model": settings.chat_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        },
        timeout=600.0,
    )
    r.raise_for_status()
    data = r.json()
    msg = data.get("message") or {}
    content = (msg.get("content") or "").strip()
    if not content:
        raise RuntimeError("empty chat response")
    return content


def build_json_user_prompt(task: str, chunks: list[dict], json_schema: str) -> str:
    parts = []
    for i, ch in enumerate(chunks, 1):
        meta = f"[{i}] {ch.get('file_name')} (chunk {ch.get('chunk_index')})"
        if ch.get("section_title"):
            meta += f" | раздел: {ch['section_title']}"
        if ch.get("article_ref"):
            meta += f" | ст.: {ch['article_ref']}"
        parts.append(f"{meta}\n{ch.get('chunk_text', '')}")
    ctx = "\n\n---\n\n".join(parts)
    return (
        f"{task.strip()}\n\n"
        f"Контекст из базы:\n\n{ctx}\n\n"
        f"Верни ТОЛЬКО один JSON-объект без markdown и без пояснений вне JSON. Поля:\n{json_schema.strip()}\n\n"
        f"Важно: в ключе summary — обычный текст на русском (краткое резюме для оператора), не JSON и не повтор всего объекта."
    )


def build_user_prompt(question: str, chunks: list[dict], *, mode: str) -> str:
    parts = []
    for i, ch in enumerate(chunks, 1):
        meta = f"[{i}] {ch.get('file_name')} (chunk {ch.get('chunk_index')})"
        if ch.get("section_title"):
            meta += f" | раздел: {ch['section_title']}"
        if ch.get("article_ref"):
            meta += f" | ст.: {ch['article_ref']}"
        parts.append(f"{meta}\n{ch.get('chunk_text', '')}")
    ctx = "\n\n---\n\n".join(parts)
    if mode == "draft":
        return (
            f"Контекст из базы:\n\n{ctx}\n\nВопрос:\n{question}\n\n"
            "Сформулируй черновик; отметь, где нужна проверка."
        )
    return f"Контекст из базы:\n\n{ctx}\n\nВопрос:\n{question}"
