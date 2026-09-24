"""SYRION Orchestrator — zentrale Schicht (Phase 1).

Verantwortung (Arch. Kap. 2B Query-Flow):
  1. Request-ID erzeugen
  2. Kontext aufbauen (MemoryService)
  3. Modell auswählen (ModelRegistry)
  4. Modell aufrufen (ModelAdapter) mit Timeout & Cancellation
  5. Antwort zurückgeben + Logging + Audit

Kein Agent, kein autonomer Loop — nur deterministische Orchestrierung.
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator

from .errors import ModelTimeoutError, SyrionError
from .logging import log
from .memory import MemoryService, memory_service
from .model_adapter import ModelRegistry
from .request_id import new_request_id
from .types import ChatRequest, ChatResponse, ChatUsage


class Orchestrator:
    def __init__(
        self,
        *,
        memory: MemoryService | None = None,
        registry: ModelRegistry | None = None,
    ) -> None:
        self.memory = memory or memory_service
        if registry is not None:
            self.registry = registry
        else:
            # Lokal-first: teile Registry mit ModelManager, damit Modellwechsel überall gilt
            from .model_manager import model_manager as _mm

            self.registry = _mm.registry

    async def handle(self, request: ChatRequest) -> ChatResponse:
        """Nicht-streaming: vollständige Antwort mit Timeout."""
        request_id = request.request_id or new_request_id()
        request.request_id = request_id
        log("info", "chat.handle start", request_id=request_id, session_id=request.session_id, model=request.model, stream=request.stream)

        # 1. Kontext
        try:
            ctx = await self.memory.build_context(session_id=request.session_id, current_message=request.message)
        except Exception as e:
            log("error", "context build failed", request_id=request_id, error=str(e))
            raise

        # 2. Modell wählen
        adapter = self.registry.resolve(request)
        log("info", "model selected", request_id=request_id, model_id=adapter.model_id)

        # 3. Aufruf mit Timeout + Cancellation-Unterstützung
        try:
            timeout_s = request.timeout_ms / 1000.0

            async def _call() -> str:
                return await adapter.generate(request, ctx)

            # asyncio.wait_for sorgt für Timeout; CancelledError wird propagiert (Client-Disconnect)
            content = await asyncio.wait_for(_call(), timeout=timeout_s)
        except asyncio.TimeoutError as e:
            log("error", "model timeout", request_id=request_id, timeout_ms=request.timeout_ms)
            raise ModelTimeoutError(request_id=request_id, timeout_ms=request.timeout_ms) from e
        except asyncio.CancelledError:
            log("warning", "chat cancelled (client disconnect)", request_id=request_id)
            raise
        except SyrionError:
            raise
        except Exception as e:
            log("error", "model generate failed", request_id=request_id, error=str(e))
            # Re-raise als SyrionError für einheitliche API-Fehler
            raise SyrionError(str(e), request_id=request_id) from e

        # 4. STM fortschreiben (best-effort, nicht kritisch)
        try:
            await self.memory.append_turn(session_id=request.session_id, user_msg=request.message, assistant_msg=content)
        except Exception as e:
            log("warning", "append_turn failed (non-critical)", request_id=request_id, error=str(e))

        log("info", "chat.handle done", request_id=request_id, content_len=len(content))
        return ChatResponse(request_id=request_id, model=adapter.model_id, content=content, usage=ChatUsage(), sources=[])

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """Streaming: liefert Chunks als AsyncIterator. Caller (API) wrappt in SSE."""
        request_id = request.request_id or new_request_id()
        request.request_id = request_id
        log("info", "chat.stream start", request_id=request_id, model=request.model)

        ctx = await self.memory.build_context(session_id=request.session_id, current_message=request.message)
        adapter = self.registry.resolve(request)

        # Timeout gilt für den gesamten Stream (nicht pro Chunk). Cancellation via CancelledError.
        try:
            timeout_s = request.timeout_ms / 1000.0
            gen = adapter.stream(request, ctx)

            async def _iter_with_timeout() -> AsyncIterator[str]:
                try:
                    # Sammle Chunks mit Gesamt-Timeout, aber erlaube laufendes Streaming
                    # Wir nutzen wait_for auf __anext__ pro Chunk — so bricht bei Stall ab
                    while True:
                        try:
                            chunk = await asyncio.wait_for(gen.__anext__(), timeout=timeout_s)
                        except StopAsyncIteration:
                            break
                        yield chunk
                except asyncio.CancelledError:
                    log("warning", "stream cancelled", request_id=request_id)
                    raise

            # Ergebnis-Chunks sammeln wir im API-Layer, hier nur Generator zurückgeben
            # Statt direkt zu yielden, sammeln wir in Liste und yielden danach — aber wir wollen echten Stream:
            # Deshalb geben wir den Generator direkt zurück — Caller iteriert.
            # Für STM müssen wir am Ende den vollständigen Text sammeln.
            full = ""
            async for chunk in _iter_with_timeout():
                full += chunk
                yield chunk
            # STM nach Stream-Ende
            try:
                await self.memory.append_turn(session_id=request.session_id, user_msg=request.message, assistant_msg=full)
            except Exception as e:
                log("warning", "append_turn after stream failed", request_id=request_id, error=str(e))
            log("info", "chat.stream done", request_id=request_id, content_len=len(full))

        except asyncio.TimeoutError as e:
            log("error", "stream timeout", request_id=request_id)
            raise ModelTimeoutError(request_id=request_id, timeout_ms=request.timeout_ms) from e
        except asyncio.CancelledError:
            raise
        except SyrionError:
            raise
        except Exception as e:
            log("error", "stream failed", request_id=request_id, error=str(e))
            raise SyrionError(str(e), request_id=request_id) from e


# Default-Orchestrator (Singleton für API)
orchestrator = Orchestrator()
