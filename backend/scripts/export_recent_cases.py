#!/usr/bin/env python3
"""
Выгрузка последних вызовов из internal API в формат session_log (JSON).

Пример:
  cd backend
  set INTERNAL_TOKEN=...
  set API_BASE=http://127.0.0.1:8090
  py scripts/export_recent_cases.py --limit 20 --output docs/evals/session_log.json

Требуется DATABASE_URL на стороне backend и размеченные review/feedback для осмысленных полей.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import httpx

from app.services.evals.session_analyze import canonical_operator_action


def _truncate(s: object, n: int = 500) -> str:
    t = str(s) if s is not None else ""
    return t if len(t) <= n else t[: n - 3] + "..."


def fetch_session_cases(
    *,
    base_url: str,
    token: str | None,
    limit: int,
    date_from: str | None,
    date_to: str | None,
) -> list[dict]:
    headers: dict[str, str] = {}
    if token:
        headers["X-Internal-Token"] = token
    base = base_url.rstrip("/")
    params: dict[str, str] = {"limit": str(limit)}
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to

    cases: list[dict] = []
    with httpx.Client(timeout=120.0, headers=headers) as client:
        r = client.get(f"{base}/api/v1/internal/ai/calls", params=params)
        r.raise_for_status()
        rows = r.json()
        if not isinstance(rows, list):
            return []

        for row in rows:
            cid = row.get("id")
            if cid is None:
                continue
            dr = client.get(f"{base}/api/v1/internal/ai/calls/{int(cid)}")
            dr.raise_for_status()
            detail = dr.json()
            call = detail.get("call") or {}
            rev = detail.get("review") or {}
            fb_list = detail.get("feedback") or []
            ui = call.get("user_input_json") or {}
            kind = ui.get("kind") if isinstance(ui, dict) else None
            persona = call.get("persona")
            mode = call.get("mode")
            prompt_profile = f"{persona or 'unknown'}:{mode or ''}"
            if kind:
                prompt_profile = f"{prompt_profile}|{kind}"

            useful: bool | None = None
            for f in reversed(fb_list if isinstance(fb_list, list) else []):
                if isinstance(f, dict) and "useful" in f:
                    useful = bool(f.get("useful"))
                    break

            op = rev.get("operator_action") or row.get("review_operator_action")
            reason_codes = rev.get("review_reason_codes") or row.get("review_reason_codes") or []
            op_journal = canonical_operator_action(op) if op else ""

            cases.append(
                {
                    "request_id": str(call.get("request_id") or "")
                    or str(row.get("request_id") or ""),
                    "endpoint": str(call.get("endpoint") or row.get("endpoint") or ""),
                    "persona": persona,
                    "prompt_profile": prompt_profile,
                    "scenario": str(kind) if kind else "",
                    "input_summary": _truncate(ui),
                    "ai_summary": call.get("response_summary"),
                    "operator_action": op_journal,
                    "reason_codes": list(reason_codes) if isinstance(reason_codes, list) else [],
                    "useful": useful,
                    "notes": "",
                    "timestamp": str(call.get("created_at") or ""),
                }
            )

    return cases


def main() -> int:
    p = argparse.ArgumentParser(description="Export recent AI calls to session_log JSON")
    p.add_argument("--base-url", default=os.environ.get("API_BASE", "http://127.0.0.1:8090"))
    p.add_argument("--token", default=os.environ.get("INTERNAL_TOKEN") or os.environ.get("INTERNAL_AUTH_TOKEN"))
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--date-from", default=None)
    p.add_argument("--date-to", default=None)
    p.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parents[2] / "docs" / "evals" / "session_log.json"),
    )
    args = p.parse_args()

    try:
        cases = fetch_session_cases(
            base_url=args.base_url,
            token=args.token,
            limit=min(max(args.limit, 1), 200),
            date_from=args.date_from,
            date_to=args.date_to,
        )
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "source": "export_recent_cases",
        "cases": cases,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(cases)} cases to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
