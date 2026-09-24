"""Knowledge Base — liest nur APPROVED aus Memory, getrennt vom Modell."""
from __future__ import annotations

from typing import List, Dict, Any

from app.memory.store import MemoryStore, MemoryStatus


class KnowledgeBase:
    """View auf MemoryStore: nur APPROVED Einträge."""

    def __init__(self, store: MemoryStore | None = None) -> None:
        self.store = store or MemoryStore()

    def list(self, *, tag: str | None = None) -> List[Dict[str, Any]]:
        entries = self.store.list(status=MemoryStatus.APPROVED.value, tag=tag)
        return [e.to_dict() for e in entries]

    def get(self, id: str) -> Dict[str, Any] | None:
        e = self.store.get(id)
        if e and e.trust_status == MemoryStatus.APPROVED.value:
            return e.to_dict()
        return None

    def count(self) -> int:
        return len(self.store.list(status=MemoryStatus.APPROVED.value))

    def growth_over_time(self) -> List[Dict[str, Any]]:
        # Zeitverlauf: Anzahl APPROVED pro Tag
        from collections import Counter

        approved = self.store.list(status=MemoryStatus.APPROVED.value)
        # Gruppiere nach Datum (YYYY-MM-DD)
        c = Counter(e.timestamp[:10] for e in approved)
        return [{"date": d, "count": n} for d, n in sorted(c.items())]
