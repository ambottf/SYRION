"""Brain Store — aggregiert Memory + Knowledge Base + Knowledge Graph für Live-Visualisierung.

Kein statisches Demo — echte Daten aus MemoryStore.
"""
from __future__ import annotations

from typing import List, Dict, Any
from datetime import datetime, timezone

from app.memory.store import MemoryStore, MemoryStatus
from app.knowledge.store import KnowledgeBase


class BrainStore:
    def __init__(self, memory: MemoryStore | None = None) -> None:
        self.memory = memory or MemoryStore()
        self.kb = KnowledgeBase(self.memory)

    def snapshot(self) -> Dict[str, Any]:
        """Gesamt-Snapshot für Dashboard (Knoten, Beziehungen, Wachstum)."""
        all_entries = self.memory.list()
        approved = self.memory.list(status=MemoryStatus.APPROVED.value)
        pending = self.memory.list(status=MemoryStatus.PENDING.value)

        # Themen: häufigste Tags
        from collections import Counter

        tag_counter = Counter(t for e in all_entries for t in e.tags)
        topics = [{"tag": tag, "count": c} for tag, c in tag_counter.most_common(10)]

        # Quellen: unique source+url
        sources = {}
        for e in all_entries:
            key = e.source + (f"|{e.url}" if e.url else "")
            sources[key] = sources.get(key, 0) + 1

        return {
            "nodes": [e.to_dict() for e in all_entries[:100]],  # Limit für UI
            "counts": {
                "facts": self.memory.facts_count(),
                "pending": len(pending),
                "approved": len(approved),
                "total": len(all_entries),
                "relations": self.memory.relations_count(),
                "sources": len(sources),
            },
            "topics": topics,
            "sources": [{"source": k.split("|")[0], "url": k.split("|")[1] if "|" in k else None, "count": v} for k, v in list(sources.items())[:20]],
            "growth": self.kb.growth_over_time(),
            "recent": [e.to_dict() for e in all_entries[:10]],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def graph(self) -> Dict[str, Any]:
        """Knoten + Kanten für Visualisierung."""
        entries = self.memory.list()
        nodes = [{"id": e.id, "label": e.content[:40], "type": e.type, "status": e.trust_status, "tags": e.tags} for e in entries]
        edges: List[Dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for e in entries:
            for r in e.relations:
                a, b = sorted([e.id, r])
                if (a, b) not in seen and self.memory.get(a) and self.memory.get(b):
                    seen.add((a, b))
                    edges.append({"source": a, "target": b, "type": "related"})
        return {"nodes": nodes, "edges": edges}
