"""Request-ID — global, fälschungssicher, tracebar."""
from __future__ import annotations

import uuid


def new_request_id() -> str:
    """Erzeugt eine neue Request-ID (UUID v4, hex, prefix)."""
    return f"req_{uuid.uuid4().hex[:16]}"
