"""Strukturiertes Logging mit Request-ID (Phase 1)."""
from __future__ import annotations

import json
import logging
import sys
from typing import Any

logger = logging.getLogger("syrion.core")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


def log(level: str, msg: str, *, request_id: str | None = None, **fields: Any) -> None:
    payload: dict[str, Any] = {"msg": msg, "request_id": request_id, **fields}
    # JSON-Lines für spätere Audit-Korrelation
    line = json.dumps(payload, ensure_ascii=False)
    if level == "error":
        logger.error(line)
    elif level == "warning":
        logger.warning(line)
    else:
        logger.info(line)
