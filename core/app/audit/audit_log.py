"""
SYRION Audit-Log — Append-only Stub (Phase 0)
- Schreibt JSONL + Hash-Chain (SYRION_ARCHITEKTUR.md:3,8)
- Kein Überschreiben, kein Löschen, kein Update
- In Phase 0 nur: init + append + verify Stub
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_PATH = Path(os.getenv("AUDIT_LOG_PATH", "data/audit/audit.log"))

def _hash_entry(prev_hash: str, entry: dict[str, Any]) -> str:
    payload = prev_hash + json.dumps(entry, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def _last_hash(path: Path) -> str:
    if not path.exists() or path.stat().st_size == 0:
        return "0" * 64
    last_line = path.read_text(encoding="utf-8").strip().splitlines()[-1]
    try:
        obj = json.loads(last_line)
        return obj.get("entry_hash", "0" * 64)
    except Exception:
        return "0" * 64

def append(actor: str, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Append-only. Kein Business-Payload in Phase 0 außer health/startup."""
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prev = _last_hash(AUDIT_PATH)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "action": action,
        "payload": payload or {},
        "prev_hash": prev,
    }
    entry["entry_hash"] = _hash_entry(prev, {k: v for k, v in entry.items() if k != "entry_hash"})
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry

def verify_chain(path: Path | None = None) -> bool:
    """Stub-Verifikation: prüft Hash-Kette."""
    p = path or AUDIT_PATH
    if not p.exists():
        return True
    prev = "0" * 64
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        expected = _hash_entry(prev, {k: v for k, v in obj.items() if k != "entry_hash"})
        if obj.get("entry_hash") != expected:
            return False
        prev = obj["entry_hash"]
    return True
