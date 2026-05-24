# Guardian Auto-Fix Activation Plan — Dry-Run Report

**Date:** 2026-05-24  
**Mode:** PLAN + DRY-RUN ONLY  
**Final verdict:** READY_FOR_MANUAL_ACTIVATION_PLAN

## Safety mode

- NO AUTO-APPLY: PASS
- NO DNS: PASS
- NO DEPLOY: PASS
- NO DOCKER RESTART: PASS
- NO DB WRITES: PASS

## Current flags

- AI_REPAIR_ENABLED=true
- AI_REPAIR_AUTO_APPLY=false
- AUTO_FIX_INCIDENT_TYPES=tg_bot_down,container_unhealthy
- SAFE_MODE=true
- DOUBLE_RING_DRY_RUN=true

## Guardrails verified

- safety_gate: PASS
- preflight_container_down: PASS
- provider guard: PASS
- confidence guard: PASS
- incident allowlist: PASS
- rag target guard: PASS
- disk cleanup block: PASS

## Dry-runs

### container_unhealthy

- provider: ollama
- auto_fix: false
- commands_executed: 0
- verdict: PASS

### tg_bot_down

- provider: ollama
- auto_fix: false
- standby degraded handled: yes
- verdict: PASS

### rag_down

- provider: ollama
- target: ollama-stack-rag
- wrong target blocked: not needed, plan was correct
- verdict: PASS

### disk_high

- first diagnostics: df -h, df -i, docker system df
- cleanup blocked: yes
- verdict: PASS

## Final state

- AI_REPAIR_AUTO_APPLY=false
- SAFE_MODE=true
- DOUBLE_RING_DRY_RUN=true
- containers restarted=0
- files changed=0

## Activation recommendation

First real activation, if approved later:

AI_REPAIR_AUTO_APPLY=true  
AUTO_FIX_INCIDENT_TYPES=container_unhealthy  
SAFE_MODE=true  
DOUBLE_RING_DRY_RUN=true  

Do not enable tg_bot_down first.
