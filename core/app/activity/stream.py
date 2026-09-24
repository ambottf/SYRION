"""Live Activity Stream — SSE, automatisch aktualisiert."""
from __future__ import annotations

import asyncio
import json
from collections import deque
from datetime import datetime, timezone
from typing import AsyncIterator, List, Dict, Any


class ActivityStream:
    def __init__(self, maxlen: int = 200) -> None:
        self._events: deque[Dict[str, Any]] = deque(maxlen=maxlen)
        self._subscribers: List[asyncio.Queue] = []

    def push(self, message: str, *, topic: str | None = None, level: str = "info") -> Dict[str, Any]:
        ev = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": message,
            "topic": topic,
            "level": level,
        }
        self._events.append(ev)
        # Push to all subscribers
        for q in list(self._subscribers):
            try:
                q.put_nowait(ev)
            except Exception:
                pass
        return ev

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(self._events)[-limit:]

    async def subscribe(self) -> AsyncIterator[Dict[str, Any]]:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        try:
            # Erst recent senden
            for ev in self.recent(20):
                yield ev
            while True:
                ev = await q.get()
                yield ev
        finally:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def clear(self) -> None:
        self._events.clear()


activity_stream = ActivityStream()
