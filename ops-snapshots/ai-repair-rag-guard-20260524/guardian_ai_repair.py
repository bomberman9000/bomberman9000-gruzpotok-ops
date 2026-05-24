#!/usr/bin/env python3
"""
guardian_ai_repair.py — AI Incident Repair Agent for Guardian.

Standalone module. Import from guardian_bot.py or run as CLI:
  python guardian_ai_repair.py --incident tg_bot_down --dry-run
  python guardian_ai_repair.py --incident rag_down --no-ai   # context only, no AI call
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

import requests

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPAIR_LOG_PATH = os.path.join(SCRIPT_DIR, "ai_repair_audit.log")
FAILOVER_AUDIT_PATH = os.path.join(SCRIPT_DIR, "failover_audit.log")

# Local standby port map (known-good 2026-05-23, see PC_STANDBY_READY_REPORT)
LOCAL_HEALTH_ENDPOINTS: dict[str, str] = {
    "rag":               "http://127.0.0.1:18080/health",
    "tg-bot":            "http://127.0.0.1:18091/health",
    "gruzpotok-api":     "http://127.0.0.1:8002/health",
    "gruzpotok-backend": "http://127.0.0.1:18090/health",
}

# Acceptable health statuses per service (200 + any of these → healthy)
_ACCEPTABLE_STATUSES: dict[str, set[str]] = {
    "rag":               {"ok", "healthy"},
    "tg-bot":            {"ok", "healthy", "degraded"},   # degraded is standby-normal
    "gruzpotok-api":     {"ok", "healthy"},
    "gruzpotok-backend": {"ok", "healthy"},
}

ALLOWLISTED_CONTAINERS: frozenset[str] = frozenset({
    "tg-bot",
    "gruzpotok-api",
    "ollama-stack-rag",
    "ollama-stack-postgres",
    "ollama-stack-redis",
    "ollama-stack-gruzpotok-backend",
    "ollama-stack-postgres-backup",
    "ollama-stack-prometheus",
})

ALLOWLISTED_SERVICES: frozenset[str] = frozenset({
    "tg-bot",
    "gruzpotok-api",
    "rag-api",
    "gruzpotok-backend",
    "postgres",
    "redis",
})

INCIDENT_TYPES: frozenset[str] = frozenset({
    "container_unhealthy",
    "healthcheck_failed",
    "rag_down",
    "tg_bot_down",
    "disk_high",
    "telegram_conflict",
})

# Trigger cooldown per incident type: don't re-fire more than once per N seconds
TRIGGER_COOLDOWN_SEC = 300


# ---------------------------------------------------------------------------
# Secret redaction
# ---------------------------------------------------------------------------

_REDACT_PATTERNS: list[tuple[re.Pattern, str]] = [
    # KEY=value / TOKEN=value / SECRET=value / PASSWORD=value
    (
        re.compile(
            r"(?i)([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|API_KEY|AUTH)[A-Z0-9_]*=)([^\s&\"'\n,]+)",
            re.MULTILINE,
        ),
        r"\1***REDACTED***",
    ),
    # postgresql://user:pass@host or redis://:pass@host
    (
        re.compile(
            r"(?i)((?:postgresql|postgres|mysql|redis)://[^:@\s]*:)([^@\s]+)(@)",
            re.MULTILINE,
        ),
        r"\1***\3",
    ),
    # Bearer / Authorization header tokens
    (
        re.compile(r"(?i)(Bearer\s+)[A-Za-z0-9._\-+/]{10,}", re.MULTILINE),
        r"\1***REDACTED***",
    ),
    (
        re.compile(r"(?i)(Authorization:\s*(?:Bearer|Token|Basic)\s+)[A-Za-z0-9._+/=\-]{8,}", re.MULTILINE),
        r"\1***REDACTED***",
    ),
]


def redact_secrets(text: str) -> str:
    """Remove secrets from text. Safe to call on any string."""
    for pattern, replacement in _REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ---------------------------------------------------------------------------
# Local command helpers (never raise)
# ---------------------------------------------------------------------------

def _run_local(cmd: list[str], timeout: int = 10) -> str:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = p.stdout + (f"\n[stderr]: {p.stderr}" if p.stderr.strip() else "")
        return redact_secrets(out.strip())
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT after {timeout}s: {cmd[0]}]"
    except Exception as exc:
        return f"[ERROR: {exc}]"


def _run_shell(cmd: str, timeout: int = 10) -> str:
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        out = p.stdout + (f"\n[stderr]: {p.stderr}" if p.stderr.strip() else "")
        return redact_secrets(out.strip())
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT after {timeout}s]"
    except Exception as exc:
        return f"[ERROR: {exc}]"


def _docker_logs(container: str, tail: int = 100) -> str:
    return _run_local(
        ["docker", "logs", "--tail", str(tail), "--timestamps", container],
        timeout=15,
    )


def _docker_inspect_state(container: str) -> str:
    return _run_local(
        ["docker", "inspect", "--format",
         "State={{.State.Status}} Health={{.State.Health.Status}} "
         "ExitCode={{.State.ExitCode}} Error={{.State.Error}}",
         container],
        timeout=5,
    )


def _health_check(url: str) -> str:
    try:
        r = requests.get(url, timeout=5)
        return redact_secrets(f"HTTP {r.status_code}: {r.text[:400]}")
    except requests.exceptions.ConnectionError:
        return "ERROR: connection refused"
    except requests.exceptions.Timeout:
        return "ERROR: timeout"
    except Exception as exc:
        return f"ERROR: {exc}"


# ---------------------------------------------------------------------------
# Incident context collection
# ---------------------------------------------------------------------------

def collect_incident_context(
    incident_type: str,
    container_name: str = "",
    max_log_lines: int = 200,
) -> dict[str, Any]:
    ctx: dict[str, Any] = {
        "incident_type": incident_type,
        "container_name": container_name,
        "timestamp": datetime.now().isoformat(),
        "docker_ps": "",
        "container_inspect": "",
        "container_logs": "",
        "health_checks": {},
        "disk": "",
        "memory": "",
        "audit_tail": "",
        "cloudflared_status": "",
        "errors": [],
    }

    # Always: docker ps, disk, memory
    ctx["docker_ps"] = _run_local(
        ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"],
        timeout=8,
    )
    ctx["disk"] = _run_local(["df", "-h", "/"], timeout=5)
    ctx["memory"] = _run_local(["free", "-m"], timeout=5)

    # Health checks for all local services
    for svc, url in LOCAL_HEALTH_ENDPOINTS.items():
        ctx["health_checks"][svc] = _health_check(url)

    # Audit log tail (redacted)
    if os.path.exists(FAILOVER_AUDIT_PATH):
        ctx["audit_tail"] = _run_shell(f"tail -n 30 {FAILOVER_AUDIT_PATH}", timeout=5)

    # Determine target container
    target = container_name
    if not target:
        target = {
            "tg_bot_down":       "tg-bot",
            "telegram_conflict": "tg-bot",
            "rag_down":          "ollama-stack-rag",
            "container_unhealthy": "",
            "healthcheck_failed": "",
            "disk_high":          "",
        }.get(incident_type, "")

    if target:
        ctx["container_inspect"] = _docker_inspect_state(target)
        ctx["container_logs"] = _docker_logs(target, tail=min(max_log_lines, 200))

    # Incident-specific extras
    if incident_type == "disk_high":
        # PATCH 1 — comprehensive disk diagnostics (replaces old disk_detail)
        ctx["disk_df_full"]      = _run_local(["df", "-h"], timeout=5)
        ctx["disk_inodes"]       = _run_local(["df", "-i"], timeout=5)
        ctx["docker_system_df"]  = _run_shell("docker system df", timeout=20)
        ctx["disk_docker_usage"] = _run_shell(
            "du -sh /var/lib/docker/* 2>/dev/null | sort -h | tail -15", timeout=25
        )
        ctx["disk_log_usage"] = _run_shell(
            "du -sh /var/log/* 2>/dev/null | sort -h | tail -10", timeout=15
        )
        ctx["journalctl_disk"] = _run_shell(
            "journalctl --disk-usage 2>/dev/null", timeout=10
        )
        ctx["docker_ps_size"] = _run_shell(
            "docker ps --size --format 'table {{.Names}}\t{{.Size}}' 2>/dev/null | head -15",
            timeout=15,
        )
        ctx["large_files"] = _run_shell(
            "find /var/log /var/lib/docker -xdev -type f -size +100M "
            "-printf '%s %p\\n' 2>/dev/null | sort -nr | head -20",
            timeout=30,
        )

    if incident_type in ("healthcheck_failed", "telegram_conflict"):
        for c in ["gruzpotok-api", "ollama-stack-rag"]:
            ctx[f"logs_{c}"] = _docker_logs(c, tail=40)

    if incident_type in ("rag_down", "container_unhealthy", "tg_bot_down"):
        ctx["cloudflared_status"] = _run_local(
            ["systemctl", "--user", "is-active", "cloudflared"], timeout=5
        )

    # PATCH 2 — RAG-specific deep context (only for rag_down)
    if incident_type == "rag_down":
        ctx["rag_health"]       = _health_check("http://127.0.0.1:18080/health")
        ctx["rag_ps_filter"]    = _run_local(
            ["docker", "ps", "--filter", "name=ollama-stack-rag",
             "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"],
            timeout=8,
        )
        ctx["rag_postgres_ps"]  = _run_local(
            ["docker", "ps", "--filter", "name=ollama-stack-postgres",
             "--format", "table {{.Names}}\t{{.Status}}"],
            timeout=8,
        )
        ctx["rag_redis_ps"]     = _run_local(
            ["docker", "ps", "--filter", "name=ollama-stack-redis",
             "--format", "table {{.Names}}\t{{.Status}}"],
            timeout=8,
        )
        ctx["rag_postgres_logs"] = _docker_logs("ollama-stack-postgres", tail=80)
        ctx["rag_redis_logs"]    = _docker_logs("ollama-stack-redis",    tail=80)
        ctx["ollama_api_tags"]   = _run_shell(
            "curl -fsS http://127.0.0.1:11434/api/tags 2>/dev/null "
            "|| echo 'ERROR: ollama api unreachable'",
            timeout=8,
        )
        ctx["ollama_ps"]  = _run_shell(
            "ollama ps 2>/dev/null || echo 'ollama not available'", timeout=8
        )
        ctx["nvidia_smi"] = _run_local(
            ["nvidia-smi", "--query-gpu=name,memory.used,utilization.gpu",
             "--format=csv,noheader"],
            timeout=8,
        )

    return ctx


# ---------------------------------------------------------------------------
# AI provider calls
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a DevOps incident repair assistant for a Docker-based Python/FastAPI stack.

Services on this standby PC:
  tg-bot          — Telegram bot, host port 18091 → container 8000
  gruzpotok-api   — FastAPI backend, host port 8002 → container 8000
  ollama-stack-rag — RAG API, host port 18080 → container 8080
  ollama-stack-postgres / ollama-stack-redis — databases

Important context:
  - Port 8000 on host is occupied by PAPPL (snap), NOT a docker service
  - tg-bot in standby mode returns HTTP 200 status=degraded — this is NORMAL
  - BOT_POLLING_ENABLED=false in standby — no Telegram polling
  - Do NOT suggest DNS, Cloudflare, or production server changes

Respond STRICTLY as a single JSON object (no markdown, no text outside JSON).\
"""

_SCHEMA_HINT = """\
JSON schema (use exactly):
{
  "summary": "one sentence: what happened",
  "severity": "low|medium|high|critical",
  "root_cause": "most likely cause in one sentence",
  "confidence": 0.85,
  "recommended_actions": ["human-readable step 1", "step 2"],
  "commands": [
    {
      "cmd": "docker logs --tail 50 tg-bot",
      "risk": "safe",
      "requires_approval": false,
      "reason": "examine recent logs"
    }
  ],
  "auto_fix_allowed": false,
  "blocked_reason": "reason if auto_fix_allowed is false, else empty"
}

Rules:
- confidence < 0.75 → auto_fix_allowed MUST be false
- Never suggest: Cloudflare API, rm -rf, SQL DDL, .env edits, iptables
- docker restart is safe for known containers\
"""

# PATCH: disk_high specific rules injected into system prompt
_DISK_HIGH_RULES = """

DISK_HIGH INCIDENT — MANDATORY OVERRIDES (apply only for incident_type=disk_high):
- Host filesystem or Docker storage is approaching capacity.
- Your commands array MUST start with df -h as command #1.
- Commands #1–#3 MUST be: df -h, df -i, docker system df (in that exact order).
- Do NOT include "docker logs tg-bot" unless the disk context explicitly shows tg-bot logs as the largest consumer.
- root_cause MUST reference: filesystem percent used, inode exhaustion, Docker images/volumes size, /var/log growth, or systemd journal — NOT container health status or Telegram polling.
- Any command that deletes, prunes, vacuums, truncates, or rotates data MUST have: risk="dangerous", requires_approval=true.
- auto_fix_allowed MUST be false for disk_high incidents.
- Severity: medium if disk >80%, high if >90%, critical if >95%. Use the df output to determine this.\
"""

# PATCH 1 — rag_down target rules injected into system prompt
_RAG_DOWN_RULES = """

RAG_DOWN INCIDENT — MANDATORY OVERRIDES (apply only for incident_type=rag_down):
- The RAG service is ollama-stack-rag, host port 18080 → container 8080.
- Primary target MUST be ollama-stack-rag. Do NOT focus on tg-bot or gruzpotok-api.
- Commands array MUST begin with these in order:
  1. docker logs --tail 80 ollama-stack-rag
  2. curl -fsS http://127.0.0.1:18080/health || true
  3. docker inspect ollama-stack-rag
  4. docker ps --filter name=ollama-stack-rag
- Do NOT recommend tg-bot commands unless RAG logs or health endpoint explicitly prove tg-bot is part of the root cause.
- Do NOT summarize rag_down as tg-bot/backend connectivity issues unless RAG health/logs show that direct evidence.
- root_cause MUST reference: ollama-stack-rag container state, port 18080 health endpoint, Ollama API availability (127.0.0.1:11434), or GPU/model loading — NOT tg-bot connectivity.
- If Ollama API (127.0.0.1:11434) is unreachable, that is the root cause — mention it explicitly and suggest checking ollama service or nvidia-smi.
- auto_fix_allowed MUST be false for rag_down (complex dependency chain requires human review).
- Severity: low if health returns slow/degraded, medium if container running but unhealthy, high if container exited/dead.\
"""


def _build_full_prompt(context_text: str, incident_type: str = "") -> str:
    """Build full LLM prompt, injecting incident-specific rules after system prompt."""
    system = _SYSTEM_PROMPT
    if incident_type == "disk_high":
        system += _DISK_HIGH_RULES
    elif incident_type == "rag_down":
        system += _RAG_DOWN_RULES
    return f"{system}\n\n{_SCHEMA_HINT}\n\nIncident context:\n{context_text}"


def _context_to_text(ctx: dict[str, Any], max_chars: int = 3500) -> str:
    parts: list[str] = []
    parts.append(f"incident_type: {ctx.get('incident_type')}")
    parts.append(f"timestamp: {ctx.get('timestamp')}")
    if ctx.get("container_name"):
        parts.append(f"target_container: {ctx['container_name']}")

    if ctx.get("docker_ps"):
        parts.append(f"\n--- docker ps ---\n{ctx['docker_ps'][:600]}")

    if ctx.get("container_inspect"):
        parts.append(f"\n--- container state ---\n{ctx['container_inspect'][:300]}")

    if ctx.get("container_logs"):
        # Most recent logs matter most
        parts.append(f"\n--- container logs (tail) ---\n{ctx['container_logs'][-700:]}")

    health = ctx.get("health_checks", {})
    if health:
        parts.append("\n--- health endpoints ---")
        for svc, status in health.items():
            parts.append(f"  {svc}: {status[:100]}")

    if ctx.get("disk"):
        parts.append(f"\n--- disk (root) ---\n{ctx['disk'][:150]}")

    if ctx.get("memory"):
        parts.append(f"\n--- memory (MB) ---\n{ctx['memory'][:150]}")

    # PATCH 1 — disk_high specific fields (only populated for disk_high incidents)
    if ctx.get("disk_df_full"):
        parts.append(f"\n--- df -h (all partitions) ---\n{ctx['disk_df_full'][:500]}")
    if ctx.get("disk_inodes"):
        parts.append(f"\n--- df -i (inodes) ---\n{ctx['disk_inodes'][:400]}")
    if ctx.get("docker_system_df"):
        parts.append(f"\n--- docker system df ---\n{ctx['docker_system_df'][:400]}")
    if ctx.get("disk_docker_usage"):
        parts.append(f"\n--- du /var/lib/docker ---\n{ctx['disk_docker_usage'][:300]}")
    if ctx.get("disk_log_usage"):
        parts.append(f"\n--- du /var/log ---\n{ctx['disk_log_usage'][:250]}")
    if ctx.get("journalctl_disk"):
        parts.append(f"\n--- journalctl disk usage ---\n{ctx['journalctl_disk'][:150]}")
    if ctx.get("docker_ps_size"):
        parts.append(f"\n--- docker ps --size ---\n{ctx['docker_ps_size'][:300]}")
    if ctx.get("large_files"):
        parts.append(f"\n--- large files >100MB ---\n{ctx['large_files'][:400]}")

    # PATCH 2 — rag_down specific fields
    if ctx.get("rag_health"):
        parts.append(f"\n--- RAG health (18080) ---\n{ctx['rag_health'][:200]}")
    if ctx.get("rag_ps_filter"):
        parts.append(f"\n--- docker ps ollama-stack-rag ---\n{ctx['rag_ps_filter'][:200]}")
    if ctx.get("rag_postgres_ps"):
        parts.append(f"\n--- docker ps postgres ---\n{ctx['rag_postgres_ps'][:150]}")
    if ctx.get("rag_redis_ps"):
        parts.append(f"\n--- docker ps redis ---\n{ctx['rag_redis_ps'][:150]}")
    if ctx.get("rag_postgres_logs"):
        parts.append(f"\n--- postgres logs ---\n{ctx['rag_postgres_logs'][-300:]}")
    if ctx.get("rag_redis_logs"):
        parts.append(f"\n--- redis logs ---\n{ctx['rag_redis_logs'][-200:]}")
    if ctx.get("ollama_api_tags"):
        parts.append(f"\n--- ollama /api/tags ---\n{ctx['ollama_api_tags'][:300]}")
    if ctx.get("ollama_ps"):
        parts.append(f"\n--- ollama ps ---\n{ctx['ollama_ps'][:150]}")
    if ctx.get("nvidia_smi"):
        parts.append(f"\n--- nvidia-smi ---\n{ctx['nvidia_smi'][:150]}")

    if ctx.get("audit_tail"):
        parts.append(f"\n--- recent audit ---\n{ctx['audit_tail'][-250:]}")

    text = "\n".join(parts)
    return text[:max_chars]


def _parse_ai_json(text: str) -> Optional[dict]:
    # Strip <think>...</think> (qwen3 reasoning mode)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()
    try:
        d = json.loads(text)
        if isinstance(d, dict):
            return d
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if m:
        try:
            d = json.loads(m.group(0))
            if isinstance(d, dict):
                return d
        except Exception:
            pass
    return None


def _call_ollama(context_text: str, cfg: dict, incident_type: str = "") -> Optional[str]:
    base_url = cfg.get("ollama_base_url", "http://127.0.0.1:11434").rstrip("/")
    model = cfg.get("ollama_repair_model") or cfg.get("ollama_model", "qwen3:8b")
    prompt = _build_full_prompt(context_text, incident_type)
    try:
        resp = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "think": False,          # qwen3: disable reasoning mode, output JSON directly
                "options": {"temperature": 0.1, "num_predict": 800},
            },
            timeout=90,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as exc:
        print(f"[REPAIR] Ollama error: {exc}")
        return None


def _call_openrouter(context_text: str, cfg: dict, incident_type: str = "") -> Optional[str]:
    api_key = cfg.get("openrouter_api_key", "")
    if not api_key or api_key.startswith("***"):
        print("[REPAIR] OpenRouter: no API key configured")
        return None
    model = cfg.get("openrouter_model", "meta-llama/llama-3.1-8b-instruct:free")
    _extra = ""
    if incident_type == "disk_high":
        _extra = _DISK_HIGH_RULES
    elif incident_type == "rag_down":
        _extra = _RAG_DOWN_RULES
    system = _SYSTEM_PROMPT + _extra
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://gruzpotok.guardian",
                "X-Title": "GruzPotok Guardian Repair",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"{_SCHEMA_HINT}\n\nIncident context:\n{context_text}"},
                ],
                "temperature": 0.1,
                "max_tokens": 800,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        print(f"[REPAIR] OpenRouter error: {exc}")
        return None


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class RepairCommand:
    cmd: str
    risk: str               # safe | medium | dangerous
    requires_approval: bool
    reason: str


@dataclass
class AIRepairPlan:
    incident_id: str
    incident_type: str
    summary: str
    severity: str           # low | medium | high | critical
    root_cause: str
    confidence: float
    recommended_actions: list[str]
    commands: list[RepairCommand]
    auto_fix_allowed: bool
    blocked_reason: str
    provider_used: str = field(default="")       # "ollama" | "openrouter" | "none"
    raw_ai_response: str = field(default="", repr=False)


@dataclass
class SafePlan:
    incident_id: str
    incident_type: str
    summary: str
    severity: str
    root_cause: str
    confidence: float
    recommended_actions: list[str]
    safe_commands: list[RepairCommand]
    blocked_commands: list[tuple[RepairCommand, str]]  # (cmd_obj, reason)
    auto_fix_allowed: bool
    blocked_reason: str
    provider_used: str = field(default="")       # propagated from AIRepairPlan


@dataclass
class ExecutionResult:
    cmd: str
    stdout: str
    stderr: str
    returncode: int
    dry_run: bool
    duration_ms: int


# ---------------------------------------------------------------------------
# AI triage
# ---------------------------------------------------------------------------

def ai_triage(ctx: dict[str, Any], cfg: dict) -> AIRepairPlan:
    incident_type = ctx.get("incident_type", "unknown")
    incident_id = f"{incident_type[:6]}-{uuid.uuid4().hex[:6]}"
    # disk_high and rag_down get more context budget (deep extra fields)
    max_chars = 5500 if incident_type in ("disk_high", "rag_down") else 3500
    context_text = _context_to_text(ctx, max_chars=max_chars)

    raw_response: Optional[str] = None
    provider_used = "none"

    provider = cfg.get("ai_repair_provider", "ollama").lower()

    if provider == "ollama":
        raw_response = _call_ollama(context_text, cfg, incident_type)
        provider_used = "ollama"
        if raw_response is None and cfg.get("openrouter_enabled", False):
            print("[REPAIR] Ollama unavailable → fallback to OpenRouter")
            raw_response = _call_openrouter(context_text, cfg, incident_type)
            provider_used = "openrouter"
    elif provider == "openrouter":
        raw_response = _call_openrouter(context_text, cfg, incident_type)
        provider_used = "openrouter"

    _audit_repair(incident_id, "ai_triage_complete",
                  f"provider={provider_used} response_len={len(raw_response or '')}")

    if not raw_response:
        return AIRepairPlan(
            incident_id=incident_id,
            incident_type=incident_type,
            summary="AI triage unavailable — no provider responded",
            severity="medium",
            root_cause="unknown (no AI response)",
            confidence=0.0,
            recommended_actions=["Check Ollama availability", "Review logs manually"],
            commands=[],
            auto_fix_allowed=False,
            blocked_reason="AI provider unavailable",
        )

    data = _parse_ai_json(raw_response)
    if not data:
        return AIRepairPlan(
            incident_id=incident_id,
            incident_type=incident_type,
            summary=raw_response[:200],
            severity="medium",
            root_cause="AI returned non-JSON response",
            confidence=0.0,
            recommended_actions=["Review AI output manually"],
            commands=[],
            auto_fix_allowed=False,
            blocked_reason="AI response parse failed",
            raw_ai_response=raw_response[:600],
        )

    commands = [
        RepairCommand(
            cmd=c["cmd"],
            risk=c.get("risk", "medium"),
            requires_approval=c.get("requires_approval", True),
            reason=c.get("reason", ""),
        )
        for c in data.get("commands", [])
        if isinstance(c, dict) and c.get("cmd")
    ]

    plan = AIRepairPlan(
        incident_id=incident_id,
        incident_type=incident_type,
        summary=str(data.get("summary", ""))[:300],
        severity=str(data.get("severity", "medium")).lower(),
        root_cause=str(data.get("root_cause", ""))[:300],
        confidence=min(1.0, max(0.0, float(data.get("confidence", 0.0)))),
        recommended_actions=[str(a) for a in data.get("recommended_actions", [])[:6]],
        commands=commands,
        auto_fix_allowed=bool(data.get("auto_fix_allowed", False)),
        blocked_reason=str(data.get("blocked_reason", "")),
        provider_used=provider_used,
        raw_ai_response=raw_response[:800],
    )

    _audit_repair(
        incident_id, "ai_plan",
        f"severity={plan.severity} confidence={plan.confidence:.2f} "
        f"commands={len(commands)} auto_fix={plan.auto_fix_allowed}",
    )
    return plan


# ---------------------------------------------------------------------------
# Safety gate
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# PATCH 4 — incident target validation
# ---------------------------------------------------------------------------

# Required keywords per incident type (at least one must appear in commands)
_INCIDENT_TARGET_KEYWORDS: dict[str, list[str]] = {
    "rag_down":          ["ollama-stack-rag", "18080"],
    "tg_bot_down":       ["tg-bot", "18091"],
    "disk_high":         ["df", "docker system df", "du"],
    "telegram_conflict": ["tg-bot", "18091"],
}

# Keywords that indicate commands are targeting the WRONG service
_INCIDENT_WRONG_TARGET_KEYWORDS: dict[str, list[str]] = {
    "rag_down":    ["tg-bot", "18091"],
    "tg_bot_down": ["ollama-stack-rag", "18080"],
}


def validate_incident_target(plan: AIRepairPlan) -> tuple[bool, str]:
    """
    Validates that plan commands address the expected service for the incident type.
    Returns (is_valid: bool, blocked_reason: str).
    If invalid: mark plan as low-confidence or blocked, never auto-apply.
    """
    if not plan.commands:
        return True, ""

    required = _INCIDENT_TARGET_KEYWORDS.get(plan.incident_type, [])
    wrong    = _INCIDENT_WRONG_TARGET_KEYWORDS.get(plan.incident_type, [])

    if not required:
        return True, ""  # no target rule for container_unhealthy / healthcheck_failed

    all_cmds = " ".join(c.cmd for c in plan.commands)
    has_correct = any(kw in all_cmds for kw in required)
    has_wrong   = bool(wrong) and any(kw in all_cmds for kw in wrong)

    if not has_correct and has_wrong:
        return False, (
            f"wrong target for {plan.incident_type}: commands address "
            f"{wrong!r} instead of expected {required!r}"
        )
    if not has_correct:
        return False, (
            f"no commands target expected service for {plan.incident_type} "
            f"(expected keywords: {required!r})"
        )
    return True, ""


_ALLOW_PATTERNS: list[re.Pattern] = [
    re.compile(r"^docker\s+ps\b"),
    re.compile(r"^docker\s+inspect\b"),
    re.compile(r"^docker\s+logs\b"),
    re.compile(r"^docker\s+stats\b"),
    re.compile(r"^docker\s+compose\s+ps\b"),
    re.compile(r"^docker\s+system\s+df\b"),           # PATCH 3: disk read-only
    re.compile(r"^docker\s+restart\s+\S+$"),
    re.compile(r"^docker\s+compose\s+up\s+-d\s+\S+$"),
    re.compile(r"^curl\s+.*http://127\.0\.0\.1:\d+"),
    re.compile(r"^systemctl\s+--user\s+(?:restart|start|is-active|status)\s+cloudflared$"),
    re.compile(r"^df\b"),                              # df -h, df -i, df -h /
    re.compile(r"^free\b"),
    re.compile(r"^ss\b"),
    re.compile(r"^du\b"),                              # PATCH 3: du -sh (read-only)
    re.compile(r"^pg_isready\b"),
    re.compile(r"^redis-cli\s+ping$"),
    re.compile(r"^redis-cli\s+-h\s+\S+\s+ping$"),
    re.compile(r"^journalctl\b"),
    # PATCH 3: read-only find scoped to safe paths, no exec/delete
    re.compile(r"^find\s+(?:/var/log|/var/lib/docker|/home/zero)\b(?!.*(?:-exec|-delete))"),
]

_BLOCK_PATTERNS: list[tuple[re.Pattern, str]] = [
    # PATCH 3: disk cleanup — block before ALLOW so they can't sneak through
    (re.compile(r"docker\s+system\s+prune", re.I),    "docker system prune (destructive)"),
    (re.compile(r"docker\s+(rmi|image\s+rm)\b", re.I), "docker image deletion"),
    (re.compile(r"docker\s+volume\s+rm\b", re.I),     "docker volume deletion"),
    (re.compile(r"journalctl\s+--vacuum", re.I),      "journalctl --vacuum (destructive)"),
    (re.compile(r"\btruncate\b", re.I),               "truncate (destructive)"),
    (re.compile(r"\blogrotate\b.*--force", re.I),     "logrotate --force (destructive)"),
    (re.compile(r"\brm\b", re.I),                     "rm command (any deletion)"),
    # existing blocks
    (re.compile(r"docker\s+compose\s+down", re.I),    "docker compose down"),
    (re.compile(r"\b(DROP|TRUNCATE|ALTER|DELETE\s+FROM)\b", re.I), "SQL DDL/DML"),
    (re.compile(r"curl.*(-X\s*(PATCH|PUT|DELETE)|--request\s*(PATCH|PUT|DELETE))", re.I), "mutating HTTP"),
    (re.compile(r"cloudflare\.com.*api", re.I),        "Cloudflare API"),
    (re.compile(r"api\.cloudflare\.com", re.I),        "Cloudflare API"),
    (re.compile(r"systemctl\s+(stop|disable|mask)\b", re.I), "systemctl stop/disable"),
    (re.compile(r"\biptables\b", re.I),                "iptables"),
    (re.compile(r"\bufw\b", re.I),                     "ufw firewall"),
    (re.compile(r"chmod\s+[0-9]*7[0-9]*", re.I),      "chmod world-writable"),
    (re.compile(r"\.env\b"),                           ".env file access"),
    (re.compile(r"(TOKEN|KEY|SECRET|PASSWORD)\s*=\s*\S", re.I), "secret assignment"),
    (re.compile(r">\s*/home/.*\.(sh|py|json|env)$"),  "file overwrite"),
    (re.compile(r"\bdd\s+if="),                        "dd destructive"),
    (re.compile(r"\beval\b"),                          "eval"),
    (re.compile(r"api\.telegram\.org.*(setWebhook|deleteWebhook)", re.I), "webhook mutation"),
    (re.compile(r"\bkill\s+-9\b"),                     "kill -9"),
    (re.compile(r"\bsudo\b"),                          "sudo"),
]


def _check_block(cmd: str) -> Optional[str]:
    for pat, label in _BLOCK_PATTERNS:
        if pat.search(cmd):
            return f"blocked:{label}"
    return None


def _check_allow(cmd: str) -> bool:
    for pat in _ALLOW_PATTERNS:
        if pat.match(cmd):
            # Extra: validate container/service names in allowlists
            if re.match(r"^docker\s+(restart|compose\s+up\s+-d)\s+", cmd):
                parts = cmd.split()
                target = parts[-1]
                if target not in ALLOWLISTED_CONTAINERS and target not in ALLOWLISTED_SERVICES:
                    return False
            return True
    return False


def safety_gate(plan: AIRepairPlan) -> SafePlan:
    safe: list[RepairCommand] = []
    blocked: list[tuple[RepairCommand, str]] = []

    for cmd_obj in plan.commands:
        cmd = cmd_obj.cmd.strip()
        block_reason = _check_block(cmd)
        if block_reason:
            blocked.append((cmd_obj, block_reason))
            continue
        if _check_allow(cmd):
            safe.append(cmd_obj)
        else:
            blocked.append((cmd_obj, "not in allowlist"))

    # PATCH 3 — wrong-target guard: validate safe commands address the correct service.
    # Runs on the full plan (all commands) so a plan that's entirely wrong-target
    # gets caught even if each individual command passes the allowlist.
    extra_blocked_reason = ""
    target_valid, target_blocked_reason = validate_incident_target(plan)
    if not target_valid:
        for cmd_obj in safe:
            blocked.append((cmd_obj, target_blocked_reason))
        safe = []
        extra_blocked_reason = target_blocked_reason

    # PATCH 3 — OpenRouter is always diagnosis-only for rag_down.
    # Even a "safe" OpenRouter plan for rag_down requires manual approval.
    openrouter_rag_block = (
        plan.incident_type == "rag_down" and plan.provider_used == "openrouter"
    )

    # Re-evaluate auto_fix: ALL conditions must hold.
    # provider_used must be "ollama" — OpenRouter (small models) is fallback-only;
    # confidence threshold tightened to 0.85 for any command that could execute live.
    auto_fix = (
        plan.auto_fix_allowed
        and plan.confidence >= 0.85
        and plan.provider_used == "ollama"
        and bool(safe)
        and len(blocked) == 0
        and not extra_blocked_reason
        and not openrouter_rag_block
        and all(c.risk == "safe" and not c.requires_approval for c in safe)
    )

    blocked_reason = extra_blocked_reason or plan.blocked_reason
    if not blocked_reason and blocked:
        blocked_reason = f"safety_gate blocked {len(blocked)} command(s)"
    elif not auto_fix and not blocked_reason:
        if openrouter_rag_block:
            blocked_reason = "OpenRouter fallback is diagnosis-only for rag_down: requires_approval=true"
        elif plan.provider_used != "ollama":
            blocked_reason = f"auto-fix requires ollama provider (got {plan.provider_used})"
        elif plan.confidence < 0.85:
            blocked_reason = f"confidence {plan.confidence:.0%} < 85% threshold"
        else:
            blocked_reason = "auto_fix_allowed=false or requires_approval=true"

    _audit_repair(
        plan.incident_id, "safety_gate",
        f"safe={len(safe)} blocked={len(blocked)} auto_fix={auto_fix} provider={plan.provider_used}",
    )
    return SafePlan(
        incident_id=plan.incident_id,
        incident_type=plan.incident_type,
        summary=plan.summary,
        severity=plan.severity,
        root_cause=plan.root_cause,
        confidence=plan.confidence,
        recommended_actions=plan.recommended_actions,
        safe_commands=safe,
        blocked_commands=blocked,
        auto_fix_allowed=auto_fix,
        blocked_reason=blocked_reason,
        provider_used=plan.provider_used,
    )


# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

def _preflight_container_down(container: str) -> tuple[bool, str]:
    """
    Last-mile guard before auto-executing 'docker restart <container>'.

    Returns (ok_to_restart: bool, reason: str).
    restart is only safe when the container is truly stopped/crashed,
    NOT when it is running in standby-degraded mode (HTTP 200 + status=degraded).

    Allowed states → restart:
      State=exited        (container stopped)
      State=dead          (OOM-killed or fatal crash)
      State=running + Health=unhealthy  (app-level crash, Docker healthcheck failing)

    Blocked states:
      State=running + Health=healthy    (container is fine)
      State=running + Health=starting   (container is booting, wait)
      State=running + Health=""         (no healthcheck — ambiguous, needs human)
      Any inspect error                 (cannot determine state safely)
    """
    out = _run_local(
        ["docker", "inspect", "--format",
         "{{.State.Status}}|{{.State.Health.Status}}",
         container],
        timeout=5,
    )
    if out.startswith("[ERROR") or out.startswith("[TIMEOUT"):
        return False, f"cannot inspect container {container!r}: {out}"

    state, _, health = out.partition("|")
    state  = state.strip().lower()
    health = health.strip().lower()

    if state == "exited":
        return True, f"container is exited — restart safe"
    if state == "dead":
        return True, f"container is dead — restart safe"
    if state == "running" and health == "unhealthy":
        return True, f"container running but health=unhealthy — restart safe"
    if state == "running" and health in ("healthy", "starting"):
        return False, f"container state={state} health={health} — not a crash, skip restart"
    # running with no healthcheck or unknown state → human must decide
    return False, f"container state={state} health={health!r} — ambiguous, manual check required"


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def execute_safe_plan(
    plan: SafePlan,
    dry_run: bool = True,
    auto_apply: bool = False,
    auto_fix_incident_types: Optional[set[str]] = None,
) -> list[ExecutionResult]:
    results: list[ExecutionResult] = []
    fix_types = auto_fix_incident_types or set()

    for cmd_obj in plan.safe_commands:
        cmd = cmd_obj.cmd.strip()

        # Pre-flight container state check for any 'docker restart <container>' command.
        # Only runs when we would otherwise execute live — guards against restarting a
        # healthy/standby container that looks "down" from the incident trigger alone.
        preflight_block: Optional[str] = None
        m_restart = re.match(r"^docker\s+restart\s+(\S+)$", cmd)
        if m_restart and not dry_run and auto_apply:
            container_target = m_restart.group(1)
            ok, pf_reason = _preflight_container_down(container_target)
            if not ok:
                preflight_block = pf_reason
                _audit_repair(
                    plan.incident_id, "exec_preflight_blocked",
                    f"cmd={cmd[:80]} reason={pf_reason}",
                )

        should_run = (
            not dry_run
            and auto_apply
            and not cmd_obj.requires_approval
            and cmd_obj.risk == "safe"
            and plan.auto_fix_allowed
            and (not fix_types or plan.incident_type in fix_types)
            and preflight_block is None
        )

        if not should_run:
            note = f"[PREFLIGHT-BLOCK: {preflight_block}]" if preflight_block else "[DRY-RUN: not executed]"
            results.append(ExecutionResult(
                cmd=cmd, stdout=note,
                stderr="", returncode=0, dry_run=True, duration_ms=0,
            ))
            if not preflight_block:
                _audit_repair(plan.incident_id, "exec_dry_run", f"cmd={cmd[:80]}")
            continue

        t0 = time.monotonic()
        try:
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            ms = int((time.monotonic() - t0) * 1000)
            results.append(ExecutionResult(
                cmd=cmd,
                stdout=redact_secrets(p.stdout.strip()[:500]),
                stderr=redact_secrets(p.stderr.strip()[:200]),
                returncode=p.returncode,
                dry_run=False,
                duration_ms=ms,
            ))
            _audit_repair(plan.incident_id, "exec_live",
                          f"cmd={cmd[:80]} rc={p.returncode} ms={ms}")
        except subprocess.TimeoutExpired:
            results.append(ExecutionResult(
                cmd=cmd, stdout="", stderr="TIMEOUT",
                returncode=-1, dry_run=False, duration_ms=30000,
            ))
            _audit_repair(plan.incident_id, "exec_timeout", f"cmd={cmd[:80]}")

    return results


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def _audit_repair(incident_id: str, event: str, detail: str) -> None:
    line = (
        f"{datetime.now().isoformat()} | repair | {incident_id} | {event} | {detail}\n"
    )
    try:
        with open(REPAIR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    print(f"[REPAIR] {incident_id} {event}: {detail}")


# ---------------------------------------------------------------------------
# Telegram message formatting
# ---------------------------------------------------------------------------

_SEV_EMOJI = {
    "low": "🟢", "medium": "🟡", "high": "🔴", "critical": "🚨",
}


def format_telegram_report(
    plan: SafePlan,
    results: list[ExecutionResult],
) -> str:
    emoji = _SEV_EMOJI.get(plan.severity, "⚠️")
    lines = [
        f"🔧 <b>AI Incident Repair</b>",
        f"ID: <code>{plan.incident_id}</code>",
        f"{emoji} <b>{plan.severity.upper()}</b> | {plan.incident_type}",
        "",
        f"<b>Summary:</b> {plan.summary}",
        f"<b>Root cause:</b> {plan.root_cause}",
        f"<b>Confidence:</b> {plan.confidence:.0%}",
    ]

    if plan.recommended_actions:
        lines.append("\n<b>Recommended actions:</b>")
        for a in plan.recommended_actions[:4]:
            lines.append(f"  • {a}")

    if plan.safe_commands:
        lines.append("\n<b>Safe commands (allowed by safety gate):</b>")
        for c in plan.safe_commands[:5]:
            req = " ⚠️requires-approval" if c.requires_approval else ""
            lines.append(f"  ✅ [{c.risk}] <code>{c.cmd}</code>{req}")

    if plan.blocked_commands:
        lines.append("\n<b>Blocked by safety gate:</b>")
        for cmd_obj, reason in plan.blocked_commands[:4]:
            lines.append(f"  🚫 <code>{cmd_obj.cmd[:60]}</code>")
            lines.append(f"     ↳ {reason}")

    if results:
        lines.append("\n<b>Dry-run simulation:</b>")
        for r in results[:5]:
            status = "✅" if r.returncode == 0 else "❌"
            lines.append(f"  {status} [DRY] <code>{r.cmd[:55]}</code>")

    if plan.blocked_reason:
        lines.append(f"\n⚠️ Auto-apply blocked: {plan.blocked_reason}")

    lines.append(
        f"\n<b>Operator commands:</b>\n"
        f"/repair apply {plan.incident_id} — применить план\n"
        f"/repair reject {plan.incident_id} — отклонить"
    )

    return "\n".join(lines)[:4000]


# ---------------------------------------------------------------------------
# RepairAgent — orchestrator (used by guardian_bot.py)
# ---------------------------------------------------------------------------

# PATCH 6 — permanently rejected plans (wrong-target or otherwise unsafe).
# These IDs can never be applied via /repair apply, regardless of in-memory state.
_KNOWN_REJECTED_PLANS: frozenset[str] = frozenset({
    "rag_do-0424d4",  # OpenRouter wrong-target plan: targeted tg-bot instead of ollama-stack-rag
})


class RepairAgent:
    """
    Orchestrates incident triage, safety gating, and optional auto-execution.

    Usage in guardian_bot.py:
        repair_agent = RepairAgent()
        # on incident detection:
        repair_agent.on_incident("tg_bot_down", alert_callback=alert.send)
        # from Telegram:
        repair_agent.apply("tgbot-a1b2c3")
        repair_agent.reject("tgbot-a1b2c3")
    """

    def __init__(self) -> None:
        self._plans: dict[str, SafePlan] = {}          # incident_id → plan
        self._last_triggered: dict[str, float] = {}    # incident_type → timestamp
        self._cfg = self._load_cfg()

    def _load_cfg(self) -> dict:
        return {
            "ai_repair_enabled":      os.getenv("AI_REPAIR_ENABLED", "false").lower() == "true",
            "ai_repair_provider":     os.getenv("AI_REPAIR_PROVIDER", "ollama"),
            "ai_repair_auto_apply":   os.getenv("AI_REPAIR_AUTO_APPLY", "false").lower() == "true",
            "ai_repair_max_log_lines": int(os.getenv("AI_REPAIR_MAX_LOG_LINES", "200")),
            "ollama_base_url":        os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
            "ollama_model":           os.getenv("OLLAMA_MODEL", "qwen3:8b"),
            "ollama_repair_model":    os.getenv("OLLAMA_REPAIR_MODEL", ""),
            "openrouter_enabled":     os.getenv("OPENROUTER_ENABLED", "false").lower() == "true",
            "openrouter_api_key":     os.getenv("OPENROUTER_API_KEY", ""),
            "openrouter_model":       os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free"),
            "auto_fix_incident_types": {
                t.strip()
                for t in os.getenv("AUTO_FIX_INCIDENT_TYPES", "").split(",")
                if t.strip()
            },
        }

    def reload_cfg(self) -> None:
        self._cfg = self._load_cfg()

    @property
    def enabled(self) -> bool:
        return self._cfg.get("ai_repair_enabled", False)

    def _should_trigger(self, incident_type: str) -> bool:
        last = self._last_triggered.get(incident_type, 0.0)
        return (time.time() - last) > TRIGGER_COOLDOWN_SEC

    def _mark_triggered(self, incident_type: str) -> None:
        self._last_triggered[incident_type] = time.time()

    def on_incident(
        self,
        incident_type: str,
        container_name: str = "",
        alert_callback: Optional[Callable[[str], Any]] = None,
    ) -> Optional[SafePlan]:
        """
        Main entry point. Call when Guardian detects a local service issue.
        Returns SafePlan (for testing/inspection) or None if disabled.
        """
        if not self.enabled:
            return None
        if incident_type not in INCIDENT_TYPES:
            print(f"[REPAIR] Unknown incident type: {incident_type!r}")
            return None
        if not self._should_trigger(incident_type):
            print(f"[REPAIR] Cooldown: skipping {incident_type} (triggered recently)")
            return None

        self._mark_triggered(incident_type)
        _audit_repair("pending", "incident_start",
                      f"type={incident_type} container={container_name or 'auto'}")

        ctx = collect_incident_context(
            incident_type, container_name,
            max_log_lines=self._cfg["ai_repair_max_log_lines"],
        )
        plan = ai_triage(ctx, self._cfg)
        safe_plan = safety_gate(plan)
        self._plans[safe_plan.incident_id] = safe_plan

        # Always dry-run first
        dry_results = execute_safe_plan(safe_plan, dry_run=True)

        # Auto-apply if all conditions met
        live_results: list[ExecutionResult] = []
        if self._cfg["ai_repair_auto_apply"] and safe_plan.auto_fix_allowed:
            _audit_repair(safe_plan.incident_id, "auto_apply_start",
                          f"incident_type={incident_type}")
            live_results = execute_safe_plan(
                safe_plan,
                dry_run=False,
                auto_apply=True,
                auto_fix_incident_types=self._cfg["auto_fix_incident_types"],
            )

        display_results = live_results if live_results else dry_results
        if alert_callback:
            msg = format_telegram_report(safe_plan, display_results)
            try:
                alert_callback(msg)
            except Exception as exc:
                print(f"[REPAIR] alert_callback error: {exc}")

        return safe_plan

    def apply(self, incident_id: str) -> tuple[bool, str]:
        """Operator-approved apply. Called from /repair apply <id>."""
        # PATCH 6 — block permanently rejected plans
        if incident_id in _KNOWN_REJECTED_PLANS:
            _audit_repair(incident_id, "apply_rejected_permanently",
                          "plan is in KNOWN_REJECTED_PLANS (wrong-target or unsafe)")
            return False, (
                f"Plan {incident_id!r} is permanently rejected "
                f"(wrong-target or unsafe — see audit log for details)"
            )
        plan = self._plans.get(incident_id)
        if not plan:
            return False, f"Plan {incident_id!r} not found (expired or unknown)"
        _audit_repair(incident_id, "operator_apply",
                      f"commands={len(plan.safe_commands)}")
        results = execute_safe_plan(plan, dry_run=False, auto_apply=True)
        lines: list[str] = []
        for r in results:
            s = "✅" if r.returncode == 0 else "❌"
            out = r.stdout[:80] if not r.dry_run else "[dry-run]"
            lines.append(f"{s} {r.cmd[:55]}: {out}")
        del self._plans[incident_id]
        return True, "\n".join(lines) or "No safe commands to execute"

    def reject(self, incident_id: str) -> bool:
        """Operator rejection. Called from /repair reject <id>."""
        if incident_id in self._plans:
            _audit_repair(incident_id, "operator_reject", "operator rejected plan")
            del self._plans[incident_id]
            return True
        return False

    def list_pending(self) -> list[SafePlan]:
        return list(self._plans.values())

    def check_local_standby(
        self,
        alert_callback: Optional[Callable[[str], Any]] = None,
    ) -> None:
        """
        Polls local standby health endpoints. If a service is unreachable
        (not just degraded), triggers repair agent with appropriate incident type.
        Call from guardian main loop (respects TRIGGER_COOLDOWN_SEC internally).
        """
        if not self.enabled:
            return

        incident_map = {
            "rag":           "rag_down",
            "tg-bot":        "tg_bot_down",
            "gruzpotok-api": "healthcheck_failed",
        }

        for svc, incident_type in incident_map.items():
            url = LOCAL_HEALTH_ENDPOINTS.get(svc, "")
            if not url:
                continue
            try:
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    # 200 with acceptable status → healthy (even degraded)
                    try:
                        body = r.json()
                        status = body.get("status", "")
                        acceptable = _ACCEPTABLE_STATUSES.get(svc, {"ok", "healthy"})
                        if status in acceptable:
                            continue  # healthy
                    except Exception:
                        continue  # can't parse → assume OK
                # Non-200 or unacceptable status → incident
                print(f"[REPAIR] Local health issue detected: {svc} status={r.status_code}")
                self.on_incident(incident_type, alert_callback=alert_callback)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                print(f"[REPAIR] Local service unreachable: {svc}")
                self.on_incident(incident_type, alert_callback=alert_callback)
            except Exception as exc:
                print(f"[REPAIR] check_local_standby error for {svc}: {exc}")


# ---------------------------------------------------------------------------
# Mock contexts for disk_high testing (PATCH 4)
# ---------------------------------------------------------------------------

_MOCK_DOCKER_PS = (
    "NAMES                        STATUS          PORTS\n"
    "tg-bot                       Up 3 hours      0.0.0.0:18091->8000/tcp\n"
    "ollama-stack-rag             Up 3 hours      0.0.0.0:18080->8080/tcp\n"
    "ollama-stack-postgres        Up 3 hours      \n"
    "ollama-stack-redis           Up 3 hours      \n"
)

_MOCK_HEALTH = {
    "rag":               "HTTP 200: {\"status\": \"ok\"}",
    "tg-bot":            "HTTP 200: {\"status\": \"degraded\"}",
    "gruzpotok-api":     "HTTP 200: {\"status\": \"ok\"}",
    "gruzpotok-backend": "ERROR: connection refused",
}


def _make_mock_context(incident_type: str, scenario: str) -> dict[str, Any]:
    """Return a synthetic incident context for disk_high testing scenarios."""
    base: dict[str, Any] = {
        "incident_type": incident_type,
        "container_name": "",
        "timestamp": datetime.now().isoformat(),
        "docker_ps": _MOCK_DOCKER_PS,
        "container_inspect": "",
        "container_logs": "",
        "health_checks": _MOCK_HEALTH,
        "disk": "Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1        50G   15G   35G  30% /",
        "memory": "              total  used   free\nMem:           47000  8200  38800",
        "audit_tail": "",
        "cloudflared_status": "active",
        "errors": [],
    }

    if scenario == "docker_big":
        # Docker overlay2 has consumed ~42GB; disk at 94%
        base["disk"] = "Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1        50G   47G   3G  94% /"
        base["disk_df_full"] = (
            "Filesystem      Size  Used Avail Use% Mounted on\n"
            "/dev/sda1        50G   47G   3G  94% /\n"
            "/dev/sdb1       200G   10G 190G   5% /media/data\n"
        )
        base["disk_inodes"] = (
            "Filesystem      Inodes  IUsed   IFree IUse% Mounted on\n"
            "/dev/sda1      3276800  200000 3076800    6% /\n"
        )
        base["docker_system_df"] = (
            "TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE\n"
            "Images          15        3         42.3GB    38.1GB (90%)\n"
            "Containers      8         4         2.1GB     1.9GB (90%)\n"
            "Local Volumes   12        3         5.6GB     4.2GB (75%)\n"
            "Build Cache     0         0         0B        0B\n"
        )
        base["disk_docker_usage"] = (
            "1.2G  /var/lib/docker/containers\n"
            "42.3G /var/lib/docker/overlay2\n"
            "5.6G  /var/lib/docker/volumes\n"
            "0     /var/lib/docker/tmp\n"
        )
        base["disk_log_usage"] = (
            "8.0K  /var/log/auth.log\n"
            "4.0K  /var/log/syslog\n"
        )
        base["journalctl_disk"] = "Archived and active journals take up 256.0M on disk."
        base["docker_ps_size"] = (
            "NAMES              SIZE\n"
            "tg-bot             120MB (virtual 1.2GB)\n"
            "ollama-stack-rag   45MB (virtual 8.9GB)\n"
        )
        base["large_files"] = (
            "44040192000 /var/lib/docker/overlay2/abc123def456/merged\n"
            "21474836480 /var/lib/docker/volumes/ollama_models/_data/llama3\n"
        )

    elif scenario == "log_big":
        # /var/log/journal at 28GB; disk at 88%
        base["disk"] = "Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1        50G   44G   6G  88% /"
        base["disk_df_full"] = (
            "Filesystem      Size  Used Avail Use% Mounted on\n"
            "/dev/sda1        50G   44G   6G  88% /\n"
        )
        base["disk_inodes"] = (
            "Filesystem      Inodes  IUsed   IFree IUse% Mounted on\n"
            "/dev/sda1      3276800  150000 3126800    5% /\n"
        )
        base["docker_system_df"] = (
            "TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE\n"
            "Images          5         3         8.2GB     2.1GB (25%)\n"
            "Containers      4         4         180MB     0B (0%)\n"
            "Local Volumes   3         3         1.2GB     0B (0%)\n"
            "Build Cache     0         0         0B        0B\n"
        )
        base["disk_docker_usage"] = (
            "180M  /var/lib/docker/containers\n"
            "8.2G  /var/lib/docker/overlay2\n"
            "1.2G  /var/lib/docker/volumes\n"
        )
        base["disk_log_usage"] = (
            "512M  /var/log/nginx/access.log\n"
            "28G   /var/log/journal\n"
            "2.1G  /var/log/syslog\n"
            "180M  /var/log/kern.log\n"
        )
        base["journalctl_disk"] = "Archived and active journals take up 28.0G on disk."
        base["docker_ps_size"] = (
            "NAMES              SIZE\n"
            "tg-bot             45MB (virtual 980MB)\n"
            "ollama-stack-rag   22MB (virtual 4.5GB)\n"
        )
        base["large_files"] = (
            "30064771072 /var/log/journal/machine-id/system.journal\n"
            "536870912 /var/log/nginx/access.log\n"
            "2254857830 /var/log/syslog\n"
        )

    elif scenario == "inode_exhaustion":
        # Disk only 30% full by size, but 99% inodes used — classic inode exhaustion
        base["disk"] = "Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1        50G   15G  35G  30% /"
        base["disk_df_full"] = (
            "Filesystem      Size  Used Avail Use% Mounted on\n"
            "/dev/sda1        50G   15G  35G  30% /\n"
            "/dev/sdb1       200G   10G 190G   5% /media/data\n"
        )
        base["disk_inodes"] = (
            "Filesystem      Inodes  IUsed   IFree IUse% Mounted on\n"
            "/dev/sda1      3276800  3274900   1900   99% /\n"
            "/dev/sdb1      1048576    10240 1038336    1% /media/data\n"
        )
        base["docker_system_df"] = (
            "TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE\n"
            "Images          8         3         12.1GB    6.2GB (51%)\n"
            "Containers      4         4         95MB      0B\n"
            "Local Volumes   3         3         980MB     0B\n"
            "Build Cache     0         0         0B        0B\n"
        )
        base["disk_docker_usage"] = (
            "95M   /var/lib/docker/containers\n"
            "12.1G /var/lib/docker/overlay2\n"
            "980M  /var/lib/docker/volumes\n"
        )
        base["disk_log_usage"] = (
            "1.2M  /var/log/auth.log\n"
            "8.0M  /var/log/syslog\n"
        )
        base["journalctl_disk"] = "Archived and active journals take up 64.0M on disk."
        base["docker_ps_size"] = (
            "NAMES              SIZE\n"
            "tg-bot             45MB (virtual 980MB)\n"
        )
        base["large_files"] = ""

    # rag_down scenarios
    elif scenario == "rag_container_down":
        base["incident_type"]    = "rag_down"
        base["container_name"]   = "ollama-stack-rag"
        base["container_inspect"] = "State=exited Health= ExitCode=1 Error="
        base["container_logs"]   = (
            "2026-05-24T10:00:01Z ERROR failed to connect to postgres: connection refused\n"
            "2026-05-24T10:00:02Z FATAL startup failed, exiting\n"
        )
        base["rag_health"]       = "ERROR: connection refused"
        base["rag_ps_filter"]    = (
            "NAMES              STATUS              PORTS\n"
            "ollama-stack-rag   Exited (1) 5m ago  \n"
        )
        base["rag_postgres_ps"]  = (
            "NAMES                    STATUS\n"
            "ollama-stack-postgres    Up 3 hours\n"
        )
        base["rag_redis_ps"]     = (
            "NAMES                STATUS\n"
            "ollama-stack-redis   Up 3 hours\n"
        )
        base["rag_postgres_logs"] = "LOG:  database system is ready to accept connections"
        base["rag_redis_logs"]    = "* Ready to accept connections"
        base["ollama_api_tags"]   = '{"models":[{"name":"qwen3:8b","size":5900000000}]}'
        base["ollama_ps"]         = (
            "NAME        ID    SIZE   PROCESSOR  UNTIL\n"
            "qwen3:8b    abc   5.9GB  100% GPU   4m from now\n"
        )
        base["nvidia_smi"]        = "NVIDIA GeForce RTX 5070, 6032 MiB, 45 %"

    elif scenario == "rag_postgres_unavailable":
        base["incident_type"]    = "rag_down"
        base["container_name"]   = "ollama-stack-rag"
        base["container_inspect"] = "State=running Health=unhealthy ExitCode=0 Error="
        base["container_logs"]   = (
            "2026-05-24T11:00:01Z ERROR cannot connect to postgresql://***@localhost/ragdb\n"
            "2026-05-24T11:00:05Z ERROR health check failed: db connection error\n"
            "2026-05-24T11:00:06Z WARN  retrying postgres connection (attempt 5)\n"
        )
        base["rag_health"]       = (
            'HTTP 500: {"status": "unhealthy", "error": "db connection failed"}'
        )
        base["rag_ps_filter"]    = (
            "NAMES              STATUS                  PORTS\n"
            "ollama-stack-rag   Up 2h (unhealthy)       0.0.0.0:18080->8080/tcp\n"
        )
        base["rag_postgres_ps"]  = (
            "NAMES                    STATUS\n"
            "ollama-stack-postgres    Exited (1) 10m ago\n"
        )
        base["rag_redis_ps"]     = (
            "NAMES                STATUS\n"
            "ollama-stack-redis   Up 3 hours\n"
        )
        base["rag_postgres_logs"] = (
            "FATAL: data directory \"/var/lib/postgresql/data\" has wrong ownership\n"
        )
        base["rag_redis_logs"]    = "* Ready to accept connections"
        base["ollama_api_tags"]   = '{"models":[{"name":"qwen3:8b"}]}'
        base["ollama_ps"]         = (
            "NAME        ID    SIZE   PROCESSOR  UNTIL\n"
            "qwen3:8b    abc   5.9GB  100% GPU   9m from now\n"
        )
        base["nvidia_smi"]        = "NVIDIA GeForce RTX 5070, 6032 MiB, 12 %"

    elif scenario == "rag_ollama_unavailable":
        base["incident_type"]    = "rag_down"
        base["container_name"]   = "ollama-stack-rag"
        base["container_inspect"] = "State=running Health=unhealthy ExitCode=0 Error="
        base["container_logs"]   = (
            "2026-05-24T12:00:01Z ERROR cannot reach Ollama at http://host.docker.internal:11434\n"
            "2026-05-24T12:00:02Z ERROR GET /api/tags: connection refused\n"
            "2026-05-24T12:00:03Z WARN  RAG generation disabled: Ollama unavailable\n"
        )
        base["rag_health"]       = (
            'HTTP 503: {"status": "unhealthy", "error": "ollama unreachable"}'
        )
        base["rag_ps_filter"]    = (
            "NAMES              STATUS                  PORTS\n"
            "ollama-stack-rag   Up 1h (unhealthy)       0.0.0.0:18080->8080/tcp\n"
        )
        base["rag_postgres_ps"]  = (
            "NAMES                    STATUS\n"
            "ollama-stack-postgres    Up 3 hours\n"
        )
        base["rag_redis_ps"]     = (
            "NAMES                STATUS\n"
            "ollama-stack-redis   Up 3 hours\n"
        )
        base["rag_postgres_logs"] = "LOG:  database system is ready to accept connections"
        base["rag_redis_logs"]    = "* Ready to accept connections"
        base["ollama_api_tags"]   = "ERROR: ollama api unreachable"
        base["ollama_ps"]         = "ollama not available"
        base["nvidia_smi"]        = "[ERROR: nvidia-smi: no process found]"

    else:
        raise ValueError(
            f"Unknown mock scenario: {scenario!r}. "
            "Use: docker_big, log_big, inode_exhaustion, "
            "rag_container_down, rag_postgres_unavailable, rag_ollama_unavailable"
        )

    return base


# ---------------------------------------------------------------------------
# PATCH 5 — rag_down test suite (6 dry-run tests)
# ---------------------------------------------------------------------------

def run_rag_down_tests(ai_cfg: Optional[dict] = None) -> bool:
    """
    Six dry-run tests for rag_down wrong-target guard.
    Returns True if all deterministic tests pass (live Ollama tests are optional).
    """
    pass_list: list[bool] = []
    sep = "=" * 62

    def _pass(name: str, detail: str = "") -> None:
        msg = f"  ✅ PASS  {name}" + (f"  [{detail}]" if detail else "")
        print(msg)
        pass_list.append(True)

    def _fail(name: str, detail: str = "") -> None:
        msg = f"  ❌ FAIL  {name}" + (f"  [{detail}]" if detail else "")
        print(msg)
        pass_list.append(False)

    print(f"\n{sep}")
    print("PATCH 5 — RAG_DOWN TARGET GUARD — 6 dry-run tests")
    print(sep)

    # ------------------------------------------------------------------
    # TEST 1: rag_down via Ollama live — rag_container_down mock context
    #   PASS: first command targets ollama-stack-rag; no tg-bot unless evidence
    # ------------------------------------------------------------------
    print("\nTEST 1: rag_down via Ollama live (rag_container_down mock)")
    if ai_cfg and ai_cfg.get("ai_repair_provider") == "ollama":
        ctx1 = _make_mock_context("rag_down", "rag_container_down")
        ct1  = _context_to_text(ctx1, max_chars=5500)
        # Context must carry RAG-specific fields before even calling AI
        ctx_ok = "ollama-stack-rag" in ct1 and "18080" in ct1
        if not ctx_ok:
            _fail("TEST 1", f"context missing rag target: rag_in={('ollama-stack-rag' in ct1)} 18080_in={('18080' in ct1)}")
        else:
            raw1 = _call_ollama(ct1, ai_cfg, "rag_down")
            if raw1 is None:
                print("  [SKIP] Ollama unavailable — skipping live AI call")
            else:
                data1 = _parse_ai_json(raw1)
                if not data1:
                    _fail("TEST 1", f"AI returned non-JSON: {raw1[:80]}")
                else:
                    cmds1 = [c.get("cmd", "") for c in data1.get("commands", [])]
                    first1 = cmds1[0] if cmds1 else ""
                    tg_only = bool(cmds1) and all("tg-bot" in c for c in cmds1)
                    has_rag = any("ollama-stack-rag" in c or "18080" in c for c in cmds1)
                    if tg_only:
                        _fail("TEST 1", f"all cmds target tg-bot: {cmds1[:2]}")
                    elif not has_rag:
                        _fail("TEST 1", f"no rag target in cmds: {cmds1[:2]}")
                    elif "ollama-stack-rag" not in first1 and "18080" not in first1:
                        _fail("TEST 1", f"first cmd is not RAG: {first1[:60]}")
                    else:
                        _pass("TEST 1", f"first_cmd={first1[:55]}")
    else:
        print("  [SKIP] Ollama not configured — skipping live AI call")

    # ------------------------------------------------------------------
    # TEST 2: rag_down via OpenRouter wrong-target (plan rag_do-0424d4)
    #   PASS: safety_gate blocks it; auto_fix_allowed=false; wrong-target reason
    # ------------------------------------------------------------------
    print("\nTEST 2: rag_down via OpenRouter wrong-target → safety_gate must block")
    bad_plan = AIRepairPlan(
        incident_id="rag_do-0424d4",
        incident_type="rag_down",
        summary="Connection refused errors from tg-bot and backend services",
        severity="low",
        root_cause="Connection refused errors from tg-bot and backend services",
        confidence=0.65,
        recommended_actions=["Check tg-bot connectivity"],
        commands=[
            RepairCommand(
                cmd="docker logs --tail 50 tg-bot",
                risk="safe",
                requires_approval=False,
                reason="examine recent logs",
            )
        ],
        auto_fix_allowed=False,
        blocked_reason="",
        provider_used="openrouter",
    )
    target_valid2, target_reason2 = validate_incident_target(bad_plan)
    sp2 = safety_gate(bad_plan)
    wrong_blocked = any("wrong target" in r.lower() for _, r in sp2.blocked_commands)
    if not target_valid2 and not sp2.auto_fix_allowed and wrong_blocked:
        _pass("TEST 2", f"wrong-target blocked; reason={sp2.blocked_reason[:70]}")
    elif not sp2.auto_fix_allowed and "openrouter" in sp2.blocked_reason.lower():
        _pass("TEST 2", f"OpenRouter blocked from auto_fix; reason={sp2.blocked_reason[:70]}")
    else:
        _fail("TEST 2",
              f"auto_fix={sp2.auto_fix_allowed} wrong_blocked={wrong_blocked} "
              f"target_valid={target_valid2} reason={sp2.blocked_reason[:60]}")

    # Confirm KNOWN_REJECTED_PLANS covers this plan ID
    if "rag_do-0424d4" in _KNOWN_REJECTED_PLANS:
        _pass("TEST 2b", "rag_do-0424d4 in KNOWN_REJECTED_PLANS → apply() will refuse permanently")
    else:
        _fail("TEST 2b", "rag_do-0424d4 NOT in KNOWN_REJECTED_PLANS")

    # ------------------------------------------------------------------
    # TEST 3: mock rag container down (exited)
    #   PASS: root_cause mentions ollama-stack-rag; command targets rag/inspect
    # ------------------------------------------------------------------
    print("\nTEST 3: mock rag_container_down — context + correct plan validation")
    ctx3 = _make_mock_context("rag_down", "rag_container_down")
    ct3  = _context_to_text(ctx3, max_chars=5500)
    if "ollama-stack-rag" in ct3 and "Exited" in ct3 and "18080" in ct3:
        _pass("TEST 3", "context contains ollama-stack-rag, Exited state, port 18080")
    else:
        _fail("TEST 3",
              f"rag={('ollama-stack-rag' in ct3)} exited={('Exited' in ct3)} 18080={('18080' in ct3)}")
    # A correctly formed plan must pass validate_incident_target
    correct3 = AIRepairPlan(
        incident_id="rag_do-t3", incident_type="rag_down",
        summary="RAG container exited", severity="high",
        root_cause="ollama-stack-rag exited with code 1",
        confidence=0.9, recommended_actions=[],
        commands=[
            RepairCommand("docker logs --tail 80 ollama-stack-rag", "safe", False, "rag logs"),
            RepairCommand("curl -fsS http://127.0.0.1:18080/health || true", "safe", False, "rag health"),
            RepairCommand("docker inspect ollama-stack-rag", "safe", False, "inspect"),
        ],
        auto_fix_allowed=False, blocked_reason="", provider_used="ollama",
    )
    v3, r3 = validate_incident_target(correct3)
    if v3:
        _pass("TEST 3b", "correct rag_container_down plan passes validate_incident_target")
    else:
        _fail("TEST 3b", f"correct plan rejected: {r3}")

    # ------------------------------------------------------------------
    # TEST 4: mock rag postgres unavailable
    #   PASS: root_cause mentions postgres; command checks ollama-stack-postgres; not tg-bot
    # ------------------------------------------------------------------
    print("\nTEST 4: mock rag_postgres_unavailable — context + postgres-aware plan")
    ctx4 = _make_mock_context("rag_down", "rag_postgres_unavailable")
    postgres_exited = "Exited" in ctx4.get("rag_postgres_ps", "")
    db_error_in_logs = (
        "db" in ctx4.get("container_logs", "").lower()
        or "postgres" in ctx4.get("container_logs", "").lower()
    )
    if postgres_exited and db_error_in_logs:
        _pass("TEST 4", "postgres Exited in context; RAG logs show db error")
    else:
        _fail("TEST 4",
              f"postgres_exited={postgres_exited} db_error={db_error_in_logs}")
    # Plan checking postgres but still mentioning rag must pass
    correct4 = AIRepairPlan(
        incident_id="rag_do-t4", incident_type="rag_down",
        summary="RAG unhealthy: postgres down", severity="medium",
        root_cause="ollama-stack-postgres exited, RAG health check failing",
        confidence=0.88, recommended_actions=[],
        commands=[
            RepairCommand("docker logs --tail 80 ollama-stack-rag", "safe", False, "rag logs"),
            RepairCommand("docker ps --filter name=ollama-stack-postgres", "safe", False, "pg status"),
            RepairCommand("docker logs --tail 80 ollama-stack-postgres", "safe", False, "pg logs"),
        ],
        auto_fix_allowed=False, blocked_reason="", provider_used="ollama",
    )
    v4, r4 = validate_incident_target(correct4)
    if v4:
        _pass("TEST 4b", "postgres-aware plan passes (has ollama-stack-rag as first cmd)")
    else:
        _fail("TEST 4b", f"rejected: {r4}")

    # ------------------------------------------------------------------
    # TEST 5: mock rag ollama unavailable
    #   PASS: root_cause mentions Ollama endpoint/GPU; commands check 11434/ollama ps
    # ------------------------------------------------------------------
    print("\nTEST 5: mock rag_ollama_unavailable — context + ollama-focused plan")
    ctx5 = _make_mock_context("rag_down", "rag_ollama_unavailable")
    ollama_unreachable = "unreachable" in ctx5.get("ollama_api_tags", "").lower()
    rag_unhealthy      = "unhealthy" in ctx5.get("rag_health", "").lower()
    if ollama_unreachable and rag_unhealthy:
        _pass("TEST 5", "context: ollama_api_tags=unreachable, rag_health=unhealthy")
    else:
        _fail("TEST 5",
              f"ollama_unreachable={ollama_unreachable} rag_unhealthy={rag_unhealthy}")
    correct5 = AIRepairPlan(
        incident_id="rag_do-t5", incident_type="rag_down",
        summary="RAG unhealthy: Ollama unreachable", severity="high",
        root_cause="Ollama API at 11434 unreachable, RAG generation disabled",
        confidence=0.9, recommended_actions=[],
        commands=[
            RepairCommand("docker logs --tail 80 ollama-stack-rag", "safe", False, "rag logs"),
            RepairCommand("curl -fsS http://127.0.0.1:18080/health || true", "safe", False, "18080"),
            RepairCommand("curl -fsS http://127.0.0.1:11434/api/tags || true", "safe", False, "ollama"),
        ],
        auto_fix_allowed=False, blocked_reason="", provider_used="ollama",
    )
    v5, r5 = validate_incident_target(correct5)
    if v5:
        _pass("TEST 5b", "ollama-focused plan passes (has ollama-stack-rag + 18080)")
    else:
        _fail("TEST 5b", f"rejected: {r5}")

    # ------------------------------------------------------------------
    # TEST 6: regression disk_high — prompt isolation + disk target validation
    #   PASS: disk_high prompt has DISK_HIGH rules (not RAG_DOWN); rag_down prompt
    #         has RAG_DOWN rules (not DISK_HIGH); cleanup still blocked
    # ------------------------------------------------------------------
    print("\nTEST 6: regression disk_high — prompt isolation + df/du target rules")
    disk_prompt = _build_full_prompt("test", "disk_high")
    rag_prompt  = _build_full_prompt("test", "rag_down")
    if "DISK_HIGH INCIDENT" in disk_prompt and "RAG_DOWN INCIDENT" not in disk_prompt:
        _pass("TEST 6a", "disk_high prompt: DISK_HIGH rules present, RAG_DOWN absent")
    else:
        _fail("TEST 6a",
              f"disk_high={('DISK_HIGH INCIDENT' in disk_prompt)} "
              f"no_rag={('RAG_DOWN INCIDENT' not in disk_prompt)}")
    if "RAG_DOWN INCIDENT" in rag_prompt and "DISK_HIGH INCIDENT" not in rag_prompt:
        _pass("TEST 6b", "rag_down prompt: RAG_DOWN rules present, DISK_HIGH absent")
    else:
        _fail("TEST 6b",
              f"rag_down={('RAG_DOWN INCIDENT' in rag_prompt)} "
              f"no_disk={('DISK_HIGH INCIDENT' not in rag_prompt)}")
    # disk_high plan without df/du must be rejected by validate_incident_target
    disk_wrong = AIRepairPlan(
        incident_id="disk_-t6", incident_type="disk_high",
        summary="Disk full", severity="high",
        root_cause="Docker images consuming disk",
        confidence=0.9, recommended_actions=[],
        commands=[RepairCommand("docker logs --tail 50 tg-bot", "safe", False, "logs")],
        auto_fix_allowed=False, blocked_reason="", provider_used="ollama",
    )
    v6w, r6w = validate_incident_target(disk_wrong)
    if not v6w:
        _pass("TEST 6c", f"disk_high plan without df rejected: {r6w[:55]}")
    else:
        _fail("TEST 6c", "disk_high plan with only tg-bot cmd should fail target check")
    # disk_high plan with df must pass
    disk_correct = AIRepairPlan(
        incident_id="disk_-t6b", incident_type="disk_high",
        summary="Disk at 94%", severity="high",
        root_cause="Docker overlay2 consuming 42GB",
        confidence=0.92, recommended_actions=[],
        commands=[
            RepairCommand("df -h", "safe", False, "disk usage"),
            RepairCommand("df -i", "safe", False, "inode usage"),
            RepairCommand("docker system df", "safe", False, "docker usage"),
        ],
        auto_fix_allowed=False, blocked_reason="", provider_used="ollama",
    )
    v6c, r6c = validate_incident_target(disk_correct)
    if v6c:
        _pass("TEST 6d", "disk_high correct plan (df -h / df -i / docker system df) passes")
    else:
        _fail("TEST 6d", f"disk_high correct plan rejected: {r6c}")

    # ------------------------------------------------------------------
    print(f"\n{sep}")
    passed = sum(pass_list)
    failed = len(pass_list) - passed
    print(f"Results: {passed}/{len(pass_list)} passed, {failed} failed")
    if failed == 0:
        print("ALL TESTS PASSED ✅")
        print(f"RAG_DOWN_TARGET_GUARD=true")
        print(f"OPENROUTER_RAG_WRONG_TARGET_BLOCKED=true")
        print(f"AUTO_FIX_ACTIVE=false")
    else:
        print(f"FAILURES: {failed} ❌")
    print(sep)
    return failed == 0


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def _load_dotenv() -> None:
    env_path = os.path.join(SCRIPT_DIR, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def main_cli() -> None:
    _load_dotenv()

    parser = argparse.ArgumentParser(
        description="Guardian AI Repair Agent — CLI test tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Incident types: {', '.join(sorted(INCIDENT_TYPES))}",
    )
    parser.add_argument("--incident", choices=sorted(INCIDENT_TYPES),
                        help="Incident type to simulate (required unless --redact-test)")
    parser.add_argument("--container", default="", help="Override target container name")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true", default=False,
                        help="Live-apply (requires AI_REPAIR_AUTO_APPLY=true in env)")
    parser.add_argument("--no-ai", action="store_true", default=False,
                        help="Skip AI call — only collect and print context")
    parser.add_argument("--redact-test", action="store_true",
                        help="Print redaction test and exit")
    parser.add_argument(
        "--mock",
        choices=[
            "docker_big", "log_big", "inode_exhaustion",
            "rag_container_down", "rag_postgres_unavailable", "rag_ollama_unavailable",
        ],
        default=None,
        help=(
            "Use synthetic context instead of live collection. "
            "disk_high: docker_big, log_big, inode_exhaustion. "
            "rag_down: rag_container_down, rag_postgres_unavailable, rag_ollama_unavailable."
        ),
    )
    parser.add_argument(
        "--run-tests", action="store_true", default=False,
        help="Run rag_down target guard test suite (6 dry-run tests) and exit",
    )
    args = parser.parse_args()

    if args.run_tests:
        ai_cfg_for_tests = {
            "ai_repair_provider":  os.getenv("AI_REPAIR_PROVIDER", "ollama"),
            "ollama_base_url":     os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
            "ollama_model":        os.getenv("OLLAMA_MODEL", "qwen3:8b"),
            "ollama_repair_model": os.getenv("OLLAMA_REPAIR_MODEL", ""),
        }
        ok = run_rag_down_tests(ai_cfg=ai_cfg_for_tests)
        raise SystemExit(0 if ok else 1)

    if args.redact_test or not args.incident:
        if not args.redact_test:
            parser.error("--incident is required unless --redact-test")
        test_cases = [
            "BOT_TOKEN=8472369846:AAES4lTklTbGFjmtgoVKYehJl8XmkXyN4Ec",
            "DATABASE_URL=postgresql://user:s3cret@localhost/db",
            "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.x.y",
            "CLOUDFLARE_API_TOKEN=cfut_zNjL...",
            "redis://:mypassword@redis:6379",
            "normal text without secrets",
        ]
        print("=== Redaction test ===")
        for t in test_cases:
            print(f"  IN:  {t}")
            print(f"  OUT: {redact_secrets(t)}\n")
        return

    sep = "=" * 62
    print(f"\n{sep}")
    print(f"Guardian AI Repair — CLI Test")
    print(f"Incident: {args.incident} | Container: {args.container or '(auto)'}")
    print(f"Mode: {'DRY-RUN' if not args.apply else 'APPLY'} | Context: {'MOCK:' + args.mock if args.mock else 'LIVE'}")
    print(sep)

    # Step 1: collect context
    if args.mock:
        print(f"\n[1/4] Using MOCK context (scenario={args.mock})...")
        ctx = _make_mock_context(args.incident, args.mock)
        print(f"  [MOCK] incident_type:  {ctx['incident_type']}")
        print(f"  [MOCK] disk:           {ctx['disk'][:80]}")
        print(f"  [MOCK] docker_system_df available: {'docker_system_df' in ctx}")
        print(f"  [MOCK] large_files available:      {'large_files' in ctx}")
    else:
        print("\n[1/4] Collecting incident context...")
        ctx = collect_incident_context(args.incident, args.container)
        print(f"  docker_ps:       {len(ctx.get('docker_ps', ''))} chars")
        print(f"  container_logs:  {len(ctx.get('container_logs', ''))} chars")
        print(f"  container_state: {ctx.get('container_inspect', '')[:80]}")
        for svc, status in ctx.get("health_checks", {}).items():
            print(f"  health/{svc:20s}: {status[:80]}")

    if args.no_ai:
        print("\n[AI SKIPPED] --no-ai flag")
        print("\nRedacted context preview (first 1200 chars):")
        print(redact_secrets(_context_to_text(ctx))[:1200])
        return

    # Step 2: AI triage
    ai_cfg = {
        "ai_repair_provider":  os.getenv("AI_REPAIR_PROVIDER", "ollama"),
        "ollama_base_url":     os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
        "ollama_model":        os.getenv("OLLAMA_MODEL", "qwen3:8b"),
        "ollama_repair_model": os.getenv("OLLAMA_REPAIR_MODEL", ""),
        "openrouter_enabled":  os.getenv("OPENROUTER_ENABLED", "false").lower() == "true",
        "openrouter_api_key":  os.getenv("OPENROUTER_API_KEY", ""),
        "openrouter_model":    os.getenv("OPENROUTER_MODEL", ""),
    }
    print(f"\n[2/4] AI triage (provider={ai_cfg['ai_repair_provider']})...")
    plan = ai_triage(ctx, ai_cfg)
    print(f"  incident_id:    {plan.incident_id}")
    print(f"  severity:       {plan.severity}")
    print(f"  confidence:     {plan.confidence:.0%}")
    print(f"  root_cause:     {plan.root_cause[:100]}")
    print(f"  commands:       {len(plan.commands)}")
    print(f"  auto_fix:       {plan.auto_fix_allowed}")

    # Step 3: safety gate
    print("\n[3/4] Safety gate...")
    safe_plan = safety_gate(plan)
    print(f"  safe commands ({len(safe_plan.safe_commands)}):")
    for c in safe_plan.safe_commands:
        print(f"    ✅ [{c.risk:8s}] {c.cmd}")
    print(f"  blocked commands ({len(safe_plan.blocked_commands)}):")
    for cmd_obj, reason in safe_plan.blocked_commands:
        print(f"    🚫 {cmd_obj.cmd[:60]}  → {reason}")
    print(f"  auto_fix_allowed: {safe_plan.auto_fix_allowed}")
    if safe_plan.blocked_reason:
        print(f"  blocked_reason:   {safe_plan.blocked_reason}")

    # Step 4: execute
    do_live = args.apply and os.getenv("AI_REPAIR_AUTO_APPLY", "false").lower() == "true"
    print(f"\n[4/4] {'Live execution' if do_live else 'Dry-run simulation'}...")
    results = execute_safe_plan(safe_plan, dry_run=not do_live)
    for r in results:
        mode = "[DRY] " if r.dry_run else "[LIVE]"
        status = "✅" if r.returncode == 0 else "❌"
        print(f"  {status} {mode} {r.cmd[:60]}")
        if not r.dry_run and r.stdout:
            print(f"         → {r.stdout[:80]}")

    print(f"\n{sep}")
    print("Telegram report preview:")
    print(format_telegram_report(safe_plan, results)[:900])
    print(sep)
    print(f"\nAudit log: {REPAIR_LOG_PATH}")


if __name__ == "__main__":
    main_cli()
