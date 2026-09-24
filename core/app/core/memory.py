"""Memory-Service Stub (Phase 1). Liefert Kontext für Orchestrator.

Später: Redis (STM) + Qdrant (LTM) + RAG. Jetzt: typsicherer Stub, der
History aus Session-ID ableitet und retrieved leer lässt — so bleibt
Orchestrator testbar ohne externe DBs.
"""
from __future__ import annotations

from .errors import MemoryError
from .types import ChatMessage, MemoryContext

# In-Memory STM Stub (pro Prozess, für Tests deterministisch)
_STM: dict[str, list[ChatMessage]] = {}


class MemoryService:
    def __init__(self, *, max_history: int = 12) -> None:
        self.max_history = max_history

    async def build_context(self, *, session_id: str | None, current_message: str) -> MemoryContext:
        try:
            history: list[ChatMessage] = []
            if session_id and session_id in _STM:
                history = _STM[session_id][-self.max_history :]
            # current_message noch nicht in history — Orchestrator fügt User-Turn beim Modellaufruf hinzu
            return MemoryContext(history=history, retrieved=[], session_id=session_id)
        except Exception as e:
            raise MemoryError(f"build_context failed: {e}") from e

    async def append_turn(self, *, session_id: str | None, user_msg: str, assistant_msg: str) -> None:
        if not session_id:
            return
        try:
            buf = _STM.setdefault(session_id, [])
            buf.append(ChatMessage(role="user", content=user_msg))
            buf.append(ChatMessage(role="assistant", content=assistant_msg))
            # Cap
            if len(buf) > self.max_history * 2:
                _STM[session_id] = buf[-(self.max_history * 2) :]
        except Exception as e:
            raise MemoryError(f"append_turn failed: {e}") from e

    async def clear(self, session_id: str) -> None:
        _STM.pop(session_id, None)


# Singleton für Orchestrator (einfach austauschbar in Tests)
memory_service = MemoryService()
