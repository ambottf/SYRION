"""Dataset-Pipeline — kontrolliert, versioniert, für späteres Training.

Kein automatisches Scraping hier — nur Pipeline, die kuratierte, freigegebene
Daten in Trainingsform bringt. Quelle immer PENDING → APPROVED.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timezone


@dataclass
class DatasetEntry:
    id: str
    text: str
    source: str
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    # Hash für Dedupe
    content_hash: str = field(init=False)

    def __post_init__(self) -> None:
        self.content_hash = hashlib.sha256(self.text.encode("utf-8")).hexdigest()[:16]


@dataclass
class DatasetVersion:
    version: str
    entries: List[DatasetEntry]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def dedupe(self) -> DatasetVersion:
        seen: set[str] = set()
        uniq: List[DatasetEntry] = []
        for e in self.entries:
            if e.content_hash not in seen:
                seen.add(e.content_hash)
                uniq.append(e)
        return DatasetVersion(version=self.version, entries=uniq, created_at=self.created_at)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self.version,
            "created_at": self.created_at,
            "entries": [e.__dict__ for e in self.entries],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> DatasetVersion:
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = [DatasetEntry(id=e["id"], text=e["text"], source=e["source"], tags=e.get("tags", []), created_at=e.get("created_at", "")) for e in data.get("entries", [])]
        return cls(version=data.get("version", "0.1.0"), entries=entries, created_at=data.get("created_at", ""))

    def stats(self) -> Dict[str, Any]:
        return {"count": len(self.entries), "unique_hashes": len({e.content_hash for e in self.entries}), "version": self.version}


def build_dataset(entries: List[Dict[str, Any]], version: str = "0.1.0") -> DatasetVersion:
    """Factory für Tests — aus Dicts."""
    ds_entries = [DatasetEntry(id=str(e.get("id", f"ds_{i}")), text=e["text"], source=e.get("source", "test"), tags=e.get("tags", [])) for i, e in enumerate(entries)]
    return DatasetVersion(version=version, entries=ds_entries)
