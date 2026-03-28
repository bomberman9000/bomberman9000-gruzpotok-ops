"""
Загрузка текстов законодательства РФ в rag-service/data/knowledge для последующей индексации (seed).

Источники:
  1) pravo_nd_catalog.json — полные тексты с pravo.gov.ru (ИПС), кодировка windows-1251.
  2) github_law_urls.json — зеркала в Markdown с GitHub (на случай недоступности pravo).

Запуск (из каталога rag-service в контейнере, PYTHONPATH=/app):
  python -m tools.import_rf_law --all
  python -m tools.import_rf_law --github-only
  python -m tools.import_rf_law --pravo-only

После загрузки: docker compose run --rm rag-api python -m app.seed
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote

import httpx
from bs4 import BeautifulSoup

TOOLS_DIR = Path(__file__).resolve().parent
RAG_ROOT = TOOLS_DIR.parent
DEFAULT_OUT = RAG_ROOT / "data" / "knowledge"

PRAVO_URL = "https://pravo.gov.ru/proxy/ips/?doc_itself=&nd={nd}&fulltext=1"
USER_AGENT = "Mozilla/5.0 (compatible; OfflineRAG/1.0; +local project)"


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [ln.strip() for ln in text.splitlines()]
    out = "\n".join(ln for ln in lines if ln)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def fetch_pravo(nd: str, title: str, slug: str, out_dir: Path, timeout: float) -> bool:
    url = PRAVO_URL.format(nd=nd)
    headers = {"User-Agent": USER_AGENT}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            r = client.get(url)
            r.raise_for_status()
    except Exception as e:
        print(f"[SKIP] nd={nd} ({slug}): {e}", file=sys.stderr)
        return False

    raw = r.content
    for enc in ("cp1251", "utf-8"):
        try:
            html = raw.decode(enc)
            break
        except UnicodeDecodeError:
            html = ""
    else:
        html = raw.decode("cp1251", errors="replace")

    body = html_to_text(html)
    if len(body) < 500:
        print(f"[SKIP] nd={nd}: слишком короткий текст ({len(body)} симв.) — проверьте nd.", file=sys.stderr)
        return False

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"legal_pravo_{slug}.md"
    header = (
        f"# {title}\n\n"
        f"Источник: Официальный портал правовой информации (ИПС pravo.gov.ru).\n"
        f"nd={nd}\n"
        f"URL: {url}\n\n"
        f"---\n\n"
    )
    path.write_text(header + body, encoding="utf-8")
    print(f"[OK] {path.name} ({len(body)} симв.)")
    return True


def fetch_github(url: str, rel_path: str, out_root: Path, timeout: float) -> bool:
    headers = {"User-Agent": USER_AGENT}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            r = client.get(url)
            r.raise_for_status()
    except Exception as e:
        print(f"[SKIP] {url}: {e}", file=sys.stderr)
        return False

    text = r.text
    if len(text) < 200:
        print(f"[SKIP] {url}: короткий ответ", file=sys.stderr)
        return False

    dest = out_root / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    note = (
        f"<!-- Источник: {unquote(url)} -->\n\n"
    )
    dest.write_text(note + text, encoding="utf-8")
    print(f"[OK] {dest.relative_to(out_root)} ({len(text)} симв.)")
    return True


def load_json(name: str) -> list:
    p = TOOLS_DIR / name
    if not p.is_file():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Импорт текстов НПА РФ в data/knowledge")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Корень knowledge")
    ap.add_argument("--pravo-delay", type=float, default=1.2, help="Пауза между запросами к pravo (сек)")
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--all", action="store_true", help="GitHub + pravo")
    ap.add_argument("--github-only", action="store_true")
    ap.add_argument("--pravo-only", action="store_true")
    args = ap.parse_args()

    out_root: Path = args.out
    out_root.mkdir(parents=True, exist_ok=True)
    pravo_dir = out_root / "legal_pravo"

    do_github = args.all or args.github_only
    do_pravo = args.all or args.pravo_only
    if not do_github and not do_pravo:
        do_github = do_pravo = True

    ok = 0
    fail = 0

    if do_github:
        for item in load_json("github_law_urls.json"):
            if fetch_github(item["url"], item["path"], out_root, args.timeout):
                ok += 1
            else:
                fail += 1

    if do_pravo:
        catalog = load_json("pravo_nd_catalog.json")
        if not catalog:
            print("[WARN] pravo_nd_catalog.json пуст или не найден.", file=sys.stderr)
        for i, item in enumerate(catalog):
            if fetch_pravo(
                str(item["nd"]),
                item["title"],
                item["slug"],
                pravo_dir,
                args.timeout,
            ):
                ok += 1
            else:
                fail += 1
            if i < len(catalog) - 1:
                time.sleep(args.pravo_delay)

    print(f"Готово: успешно {ok}, пропусков/ошибок {fail}. Каталог: {out_root}")


if __name__ == "__main__":
    main()
