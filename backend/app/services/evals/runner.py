from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

DEFAULT_FIXTURES = Path(__file__).resolve().parents[3] / "evals" / "fixtures"


@dataclass
class CaseResult:
    name: str
    path: str
    http_status: int
    ok: bool
    latency_ms: float | None
    status: str | None
    llm_invoked: bool | None
    citations_count: int
    checks: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


def _discover_cases(fixtures_root: Path) -> list[tuple[Path, dict[str, Any], dict[str, Any]]]:
    out: list[tuple[Path, dict[str, Any], dict[str, Any]]] = []
    for input_path in fixtures_root.rglob("input.json"):
        case_dir = input_path.parent
        exp_path = case_dir / "expected.json"
        if not exp_path.is_file():
            continue
        inp = json.loads(input_path.read_text(encoding="utf-8"))
        exp = json.loads(exp_path.read_text(encoding="utf-8"))
        out.append((case_dir, inp, exp))
    return sorted(out, key=lambda x: str(x[0]))


def _compare_envelope(
    body: dict[str, Any],
    expected: dict[str, Any],
) -> dict[str, Any]:
    meta = body.get("meta") or {}
    data = body.get("data") or {}
    status = str(data.get("status") or "")
    llm = data.get("llm_invoked")
    if llm is None:
        llm = meta.get("llm_invoked")
    cites = data.get("citations") or []
    n_cites = len(cites) if isinstance(cites, list) else 0

    checks: dict[str, Any] = {}

    allowed = expected.get("status_in")
    if allowed:
        checks["status_match"] = status in allowed
    elif "status" in expected:
        checks["status_match"] = status == expected["status"]
    else:
        checks["status_match"] = True

    min_c = int(expected.get("min_citations", 0))
    checks["citations_ok"] = n_cites >= min_c

    if "llm_invoked" in expected and expected["llm_invoked"] is not None:
        checks["llm_match"] = bool(llm) == bool(expected["llm_invoked"])
    else:
        checks["llm_match"] = True

    ep_needle = (expected.get("meta") or {}).get("endpoint_contains")
    if ep_needle:
        ep = str(meta.get("endpoint") or "")
        checks["meta_endpoint_ok"] = ep_needle in ep
    else:
        checks["meta_endpoint_ok"] = True

    req_fields = expected.get("require_fields_non_empty") or []
    missing = []
    for f in req_fields:
        v = data.get(f)
        if v is None or (isinstance(v, str) and not v.strip()):
            missing.append(f)
    checks["required_fields_ok"] = len(missing) == 0
    if missing:
        checks["required_fields_missing"] = missing

    rev_if = ((expected.get("heuristics") or {}).get("review_needed_if_status")) or []
    checks["review_needed_heuristic"] = status in rev_if if rev_if else False

    passed = all(
        checks.get(k, True)
        for k in ("status_match", "citations_ok", "llm_match", "meta_endpoint_ok", "required_fields_ok")
    )
    return {
        "passed": passed,
        "checks": checks,
        "observed": {
            "status": status,
            "llm_invoked": llm,
            "citations_count": n_cites,
            "latency_ms": meta.get("latency_ms"),
        },
    }


def run_case(
    *,
    base_url: str,
    inp: dict[str, Any],
    expected: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: float = 120.0,
) -> tuple[CaseResult, dict[str, Any]]:
    method = str(inp.get("method", "POST")).upper()
    path = str(inp.get("path", ""))
    url = base_url.rstrip("/") + path
    body = inp.get("body")
    t0 = time.perf_counter()
    err: str | None = None
    http_status = 0
    parsed: dict[str, Any] = {}
    try:
        with httpx.Client(timeout=timeout, headers=headers or {}) as client:
            if method == "POST":
                r = client.post(url, json=body)
            elif method == "GET":
                r = client.get(url)
            else:
                raise ValueError(f"unsupported method {method}")
            http_status = r.status_code
            parsed = r.json() if r.content else {}
    except Exception as e:
        err = str(e)
        latency_ms = (time.perf_counter() - t0) * 1000
        name = str(inp.get("name", path))
        return (
            CaseResult(
                name=name,
                path=path,
                http_status=http_status,
                ok=False,
                latency_ms=round(latency_ms, 2),
                status=None,
                llm_invoked=None,
                citations_count=0,
                checks={},
                error=err,
            ),
            {"passed": False, "checks": {}, "observed": {}},
        )

    latency_ms = (time.perf_counter() - t0) * 1000
    cmp = _compare_envelope(parsed, expected)
    meta = parsed.get("meta") or {}
    data = parsed.get("data") or {}
    name = str(inp.get("name", path))
    llm = data.get("llm_invoked")
    if llm is None:
        llm = meta.get("llm_invoked")
    cites = data.get("citations") or []
    n_cites = len(cites) if isinstance(cites, list) else 0

    case_ok = http_status < 400 and cmp.get("passed", False)
    if err:
        case_ok = False

    cr = CaseResult(
        name=name,
        path=path,
        http_status=http_status,
        ok=case_ok,
        latency_ms=round(latency_ms, 2),
        status=str(data.get("status") or "") or None,
        llm_invoked=bool(llm) if llm is not None else None,
        citations_count=n_cites,
        checks=cmp.get("checks") or {},
        error=err,
    )
    return cr, cmp


def run_suite(
    *,
    base_url: str,
    fixtures_root: Path | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 120.0,
) -> dict[str, Any]:
    root = fixtures_root or DEFAULT_FIXTURES
    cases = _discover_cases(root)
    results: list[dict[str, Any]] = []
    latencies: list[float] = []

    for case_dir, inp, exp in cases:
        cr, cmp = run_case(
            base_url=base_url,
            inp=inp,
            expected=exp,
            headers=headers,
            timeout=timeout,
        )
        if cr.latency_ms is not None:
            latencies.append(float(cr.latency_ms))
        try:
            case_rel = str(case_dir.relative_to(root))
        except ValueError:
            case_rel = str(case_dir)
        results.append(
            {
                "case_dir": case_rel,
                "name": cr.name,
                "http_status": cr.http_status,
                "ok": cr.ok,
                "error": cr.error,
                "compare": cmp,
                "latency_ms": cr.latency_ms,
            }
        )

    n = len(results)
    passed = sum(1 for r in results if r.get("ok"))
    sm = sum(
        1
        for r in results
        if (r.get("compare") or {}).get("checks", {}).get("status_match")
    )
    llm_n = sum(
        1
        for r in results
        if (r.get("compare") or {}).get("observed", {}).get("llm_invoked") is True
    )
    cit_n = sum(
        1
        for r in results
        if int((r.get("compare") or {}).get("observed", {}).get("citations_count") or 0) > 0
    )
    rev_n = sum(
        1
        for r in results
        if (r.get("compare") or {}).get("checks", {}).get("review_needed_heuristic")
    )
    rf_n = sum(
        1
        for r in results
        if (r.get("compare") or {}).get("checks", {}).get("required_fields_ok")
    )

    lat_summary: dict[str, Any] = {}
    if latencies:
        lat_sorted = sorted(latencies)
        lat_summary = {
            "count": len(lat_sorted),
            "min_ms": round(lat_sorted[0], 2),
            "max_ms": round(lat_sorted[-1], 2),
            "mean_ms": round(statistics.mean(lat_sorted), 2),
            "p50_ms": round(lat_sorted[len(lat_sorted) // 2], 2),
            "p95_ms": round(lat_sorted[int(len(lat_sorted) * 0.95)] if len(lat_sorted) > 1 else lat_sorted[-1], 2),
        }

    return {
        "fixtures_root": str(root),
        "base_url": base_url,
        "cases_total": n,
        "cases_passed": passed,
        "metrics": {
            "status_match_rate": round(sm / n, 4) if n else None,
            "llm_invoked_rate": round(llm_n / n, 4) if n else None,
            "citations_present_rate": round(cit_n / n, 4) if n else None,
            "required_fields_ok_rate": round(rf_n / n, 4) if n else None,
            "review_needed_heuristic_count": rev_n,
        },
        "latency": lat_summary,
        "results": results,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Run GrusPotok AI eval fixtures against HTTP API")
    p.add_argument("--base-url", default="http://127.0.0.1:8090", help="Backend base URL")
    p.add_argument("--fixtures", default=None, help="Path to evals/fixtures root")
    p.add_argument("--output", default=None, help="Write JSON report to file")
    p.add_argument(
        "--header",
        action="append",
        default=[],
        help='Extra header "Name: value" (repeatable)',
    )
    args = p.parse_args()
    hdrs: dict[str, str] = {}
    for h in args.header:
        if ":" in h:
            k, v = h.split(":", 1)
            hdrs[k.strip()] = v.strip()
    root = Path(args.fixtures).resolve() if args.fixtures else DEFAULT_FIXTURES
    report = run_suite(base_url=args.base_url, fixtures_root=root, headers=hdrs or None)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
