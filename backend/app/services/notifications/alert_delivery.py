from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _telegram_send_message(*, token: str, chat_id: str, text: str) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    with httpx.Client(timeout=15.0) as client:
        r = client.post(
            url,
            json={"chat_id": chat_id, "text": text[:4000]},
        )
        r.raise_for_status()
        return r.json()


def _webhook_post(*, url: str, text: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"text": text, "source": "gruzpotok-ai", "severity": "high_priority"}
    with httpx.Client(timeout=15.0) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        try:
            return r.json() if r.content else {"ok": True, "status_code": r.status_code}
        except Exception:
            return {"ok": True, "status_code": r.status_code}


def deliver_high_priority_alert(text: str) -> dict[str, Any]:
    """
    Доставка алерта по env (webhook и/или Telegram). Без настроек — no-op с ok=True.
    Интерфейс стабильный: подключение внешнего сервиса = задать переменные окружения.
    """
    s = get_settings()
    out: dict[str, Any] = {"attempted": [], "errors": []}

    if s.alert_webhook_url and str(s.alert_webhook_url).strip():
        try:
            _webhook_post(url=str(s.alert_webhook_url).strip(), text=text)
            out["attempted"].append("webhook")
        except Exception as e:
            logger.exception("alert webhook failed")
            out["errors"].append({"channel": "webhook", "error": str(e)})

    tok = (s.alert_telegram_bot_token or "").strip()
    cid = (s.alert_telegram_chat_id or "").strip()
    if tok and cid:
        try:
            _telegram_send_message(token=tok, chat_id=cid, text=text)
            out["attempted"].append("telegram")
        except Exception as e:
            logger.exception("alert telegram failed")
            out["errors"].append({"channel": "telegram", "error": str(e)})

    if not out["attempted"] and not out["errors"]:
        out["note"] = "no_alert_channels_configured"
    out["ok"] = len(out["errors"]) == 0
    return out
