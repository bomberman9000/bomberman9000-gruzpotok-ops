#!/usr/bin/env python3
"""
Анализ docs/evals/session_log.json — счётчики, TOP ISSUE, tuning hints.

  cd backend
  py scripts/analyze_session.py
  py scripts/analyze_session.py --input docs/evals/session_log.json --json-out report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.services.evals.session_analyze import analyze_cases
from app.services.evals.session_logger import load_cases


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--input",
        default=str(Path(__file__).resolve().parents[2] / "docs" / "evals" / "session_log.json"),
    )
    p.add_argument(
        "--threshold",
        type=int,
        default=2,
        help="Минимум вхождений reason для TOP ISSUE (на малой выборке обычно 2)",
    )
    p.add_argument("--json-out", default=None, help="Полный JSON анализа в файл")
    args = p.parse_args()

    path = Path(args.input)
    cases = load_cases(path)
    result = analyze_cases(cases, top_issue_threshold=args.threshold)

    print(result["text_report"])
    if args.json_out:
        outp = Path(args.json_out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(
            json.dumps(
                {
                    "summary": {k: v for k, v in result.items() if k != "text_report"},
                    "text_report": result["text_report"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"JSON: {outp}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
