#!/usr/bin/env python3
"""Запуск eval suite: из каталога backend — python scripts/run_eval.py --base-url http://127.0.0.1:8090"""
from __future__ import annotations

import sys
from pathlib import Path

# backend/ в PYTHONPATH
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.services.evals.runner import main  # noqa: E402

if __name__ == "__main__":
    main()
