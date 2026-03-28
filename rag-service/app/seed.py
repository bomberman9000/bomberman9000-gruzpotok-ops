"""
Индексация базы знаний (обёртка над ingestion runner).
Запуск: python -m app.seed
"""
import sys

from app.services.ingestion.runner import run_ingestion


def main() -> None:
    try:
        r = run_ingestion()
    except FileNotFoundError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
    print(
        f"ingestion_run_id={r['ingestion_run_id']} status={r['status']} "
        f"seen={r['files_seen']} indexed={r['files_indexed']} skipped={r['files_skipped']} "
        f"deactivated={r.get('documents_deactivated', 0)}"
    )
    if r.get("errors"):
        for e in r["errors"]:
            print(f"[WARN] {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
