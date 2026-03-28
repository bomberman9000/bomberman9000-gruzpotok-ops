#!/usr/bin/env python3
"""
Прогон 5 кейсов из docs/evals/POST_DEPLOY_PRICING_CHECKLIST.md через публичный API backend.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import httpx


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8090")
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument(
        "--dump-json",
        default=None,
        help="Сохранить полные ответы (JSON) для сравнения до/после",
    )
    p.add_argument(
        "--debug-case2",
        action="store_true",
        help="Для кейса 2 (МСК—СПб) передать debug=true в теле — retrieval_debug в raw",
    )
    p.add_argument(
        "--debug-case1",
        action="store_true",
        help="Для кейса 1 (мало данных) передать debug=true — проверка top-k без demo",
    )
    p.add_argument(
        "--only-case",
        type=int,
        default=None,
        help="Выполнить только один кейс (номер 1..5). Удобно с --repeat.",
    )
    p.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Сколько раз повторить выбранные кейсы (с --only-case — только его).",
    )
    args = p.parse_args()
    base = args.base_url.rstrip("/")

    queries: list[tuple[str, str, dict]] = [
        (
            "1 ориентир, мало данных",
            f"{base}/api/v1/ai/query",
            {
                "query": (
                    "Нужна ставка на автоперевозку Самара — Казань, груз около 3 т, 12 м³, "
                    "погрузка завтра. Тип кузова пока не выбрали. Дай ориентир по цене."
                ),
                "persona": "logistics",
                "category": "freight",
                "mode": "balanced",
            },
        ),
        (
            "2 ставка, данных достаточно",
            f"{base}/api/v1/ai/query",
            {
                "query": (
                    "Москва — Санкт-Петербург, 20 т, 82 м³, тент, загрузка сегодня вечером. "
                    "Нужна рыночная ставка на автоперевозку."
                ),
                "persona": "logistics",
                "category": "freight",
                "mode": "balanced",
            },
        ),
        (
            "3 провокация",
            f"{base}/api/v1/ai/query",
            {
                "query": "Сколько стоит перевезти груз по России?",
                "persona": "logistics",
                "category": "freight",
                "mode": "balanced",
            },
        ),
        (
            "4 короткое плечо",
            f"{base}/api/v1/ai/query",
            {
                "query": (
                    "Тула — Рязань, до 1.5 т палета, завтра утром. Сколько примерно стоит машина?"
                ),
                "persona": "logistics",
                "category": "freight",
                "mode": "balanced",
            },
        ),
        (
            "5 claim_review legal",
            f"{base}/api/v1/ai/claims/review",
            {
                "claim_text": (
                    "Претензия: перевозчик не доставил груз в срок, просим взыскать убытки "
                    "в размере примерно от пятисот тысяч до двух миллионов рублей без обоснования суммы. "
                    "Договор перевозки от 01.01.2025, маршрут Москва — Екатеринбург."
                ),
                "contract_context": "Условия договора перевозки: срок 3 суток, штраф 0.1% за день просрочки.",
                "counterparty": "ООО Перевозчик",
            },
        ),
    ]

    if args.only_case is not None:
        if not 1 <= args.only_case <= len(queries):
            print(f"--only-case must be 1..{len(queries)}", file=sys.stderr)
            return 2
        base_queries = [queries[args.only_case - 1]]
        repeat = max(1, min(args.repeat, 50))
        run_rows: list[tuple[str, str, dict, int]] = []
        for r in range(repeat):
            title, url, body = base_queries[0]
            suffix = f" (run {r + 1}/{repeat})" if repeat > 1 else ""
            run_rows.append((title + suffix, url, body, args.only_case - 1))
    else:
        if args.repeat != 1:
            print("--repeat применяется только вместе с --only-case; прогон полного чеклиста ×1.", file=sys.stderr)
        run_rows = [(title, url, body, idx) for idx, (title, url, body) in enumerate(queries)]

    n = len(run_rows)
    print(f"Post-deploy checklist: {n} запрос(ов) к backend\n")
    dumped: list[dict] = []
    with httpx.Client(timeout=args.timeout) as client:
        for run_i, (title, url, body, idx) in enumerate(run_rows):
            req_body = dict(body)
            if args.debug_case1 and idx == 0 and url.endswith("/query"):
                req_body["debug"] = True
            if args.debug_case2 and idx == 1 and url.endswith("/query"):
                req_body["debug"] = True
            try:
                r = client.post(url, json=req_body)
                r.raise_for_status()
                env = r.json()
                meta = env.get("meta") or {}
                data = env.get("data") or {}
                status = data.get("status") or meta.get("normalized_status")
                rid = meta.get("request_id")
                ans = data.get("answer") or data.get("summary") or ""
                summ = ans[:400]
                print(f"--- {title} ---")
                print(f"  request_id: {rid}")
                print(f"  status: {status}")
                print(f"  preview: {summ[:300]}...")
                print()
                dumped.append(
                    {
                        "title": title,
                        "run_index": run_i + 1,
                        "case_index": idx + 1,
                        "request_id": rid,
                        "url": url,
                        "status": status,
                        "answer": ans,
                        "raw_response": data.get("raw_response"),
                    }
                )
            except Exception as e:
                print(f"FAIL {title}: {e}", file=sys.stderr)
                return 1
    if args.dump_json:
        out = Path(args.dump_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(dumped, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON: {out}", file=sys.stderr)
    print("Готово. Дальше: export_recent_cases.py и analyze_session.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
