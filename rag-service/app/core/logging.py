import json
import logging
import sys
from datetime import UTC, datetime

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    h = logging.StreamHandler(sys.stdout)
    if settings.log_json:
        h.setFormatter(JsonFormatter())
    else:
        h.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    root.handlers.clear()
    root.addHandler(h)
