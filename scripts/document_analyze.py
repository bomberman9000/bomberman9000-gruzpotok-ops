#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "rag-service"))

from app.services.document_pipeline import (  # noqa: E402
    SUPPORTED_CLAIM_REPLY_MODES,
    SUPPORTED_DOCUMENT_TASKS,
    DocumentPipelineError,
    analyze_document,
)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Извлечь текст из документа, прогнать через Ollama и вернуть summary/facts/draft reply."
    )
    p.add_argument("--file", required=True, help="Путь к документу")
    p.add_argument(
        "--task",
        default="claim_response",
        choices=SUPPORTED_DOCUMENT_TASKS,
        help="Сценарий анализа документа",
    )
    p.add_argument(
        "--output-dir",
        default=str(_ROOT / "artifacts" / "document-text"),
        help="Куда сохранять извлечённый текст",
    )
    p.add_argument("--max-file-mb", type=int, default=15, help="Лимит размера файла")
    p.add_argument("--max-pages", type=int, default=200, help="Лимит числа страниц для PDF")
    p.add_argument("--chunk-max-chars", type=int, default=6000, help="Размер одного чанка")
    p.add_argument("--chunk-overlap", type=int, default=400, help="Перекрытие между чанками")
    p.add_argument(
        "--enable-ocr-fallback",
        action="store_true",
        help="Разрешить degraded OCR fallback для PDF-сканов, если он будет доступен",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Печатать только structured JSON без служебных строк",
    )
    p.add_argument(
        "--reply-mode",
        default="auto",
        choices=SUPPORTED_CLAIM_REPLY_MODES,
        help="Стратегия ответа на претензию для claim_response",
    )
    return p


async def _run(args: argparse.Namespace) -> int:
    try:
        result = await analyze_document(
            args.file,
            task=args.task,
            output_dir=args.output_dir,
            max_file_mb=args.max_file_mb,
            max_pages=args.max_pages,
            chunk_max_chars=args.chunk_max_chars,
            chunk_overlap=args.chunk_overlap,
            enable_ocr_fallback=args.enable_ocr_fallback,
            reply_mode=args.reply_mode,
        )
    except DocumentPipelineError as e:
        print(f"DOCUMENT_ANALYZE=FAIL\nerror={e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"DOCUMENT_ANALYZE=FAIL\nunexpected_error={e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.raw_response, ensure_ascii=False, indent=2))
        return 0

    print("DOCUMENT_ANALYZE=PASS")
    print(f"task={result.task}")
    print(f"file={Path(result.source_path).name}")
    print(f"file_type={result.file_type}")
    print(f"extraction_method={result.extraction_method}")
    print(f"extraction_quality={result.extraction_quality}")
    print(f"extraction_status={result.extraction_status}")
    print(f"fallback_used={result.fallback_used}")
    print(f"text_layer_found={result.text_layer_found}")
    print(f"pages_present={result.pages_present}")
    if result.user_safe_reason:
        print(f"user_safe_reason={result.user_safe_reason}")
    if result.quality_reasons:
        print("quality_reasons=" + ", ".join(result.quality_reasons))
    else:
        print("quality_reasons=none")
    print(f"pages={result.page_count}")
    print(f"blocks={result.block_count}")
    print(f"chunks={result.chunk_count}")
    print(f"text_saved={result.text_path}")
    print(f"analysis_saved={result.analysis_path}")
    if result.reply_mode_requested:
        print(f"reply_mode_requested={result.reply_mode_requested}")
    if result.reply_mode_effective:
        print(f"reply_mode_effective={result.reply_mode_effective}")
    if result.warnings:
        print("warnings=" + "; ".join(result.warnings))
    else:
        print("warnings=none")
    print("\n=== summary ===")
    print(result.summary)
    print("\n=== extracted_facts ===")
    print(json.dumps(result.extracted_facts, ensure_ascii=False, indent=2))
    if result.draft_reply.strip():
        print("\n=== draft_reply ===")
        print(result.draft_reply)
    return 0


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_run(_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
