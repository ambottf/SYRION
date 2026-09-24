"""Chat-API — dünne HTTP-Schicht über Orchestrator (Phase 1).

POST /api/v1/chat        -> JSON (nicht-streaming)
POST /api/v1/chat/stream -> SSE  (text/event-stream)

Verantwortung nur: Validierung, Request-ID Header, SSE-Format, Fehler-Mapping.
Orchestrator bleibt testbar ohne HTTP.
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from app.audit.audit_log import append
from app.core.errors import ModelTimeoutError, ModelUnavailableError, SyrionError
from app.core.orchestrator import orchestrator
from app.core.request_id import new_request_id
from app.core.types import ChatRequest
from app.syrion_model.status import is_untrained, get_status as get_model_status

router = APIRouter(prefix="/api/v1", tags=["chat"])


def _request_id_from(request: Request, body: ChatRequest | None = None) -> str:
    # Header hat Vorrang, sonst Body, sonst neu
    return request.headers.get("x-request-id") or (body.request_id if body and body.request_id else new_request_id())


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> Response:
    rid = _request_id_from(request, body)
    body.request_id = rid
    # Wenn Modell UNTRAINED, keine Fake-Antwort, sondern klarer Hinweis
    if is_untrained():
        status = get_model_status()
        msg = status.get("message", "SYRION Model befindet sich noch in der Trainingsphase.")
        return JSONResponse(
            status_code=503,
            content={"code": "MODEL_UNTRAINED", "message": msg, "request_id": rid, "model_state": status.get("state")},
            headers={"x-request-id": rid},
        )
    try:
        result = await orchestrator.handle(body)
        # Audit: erfolgreicher Chat (ohne message content PII — nur Längen)
        append(actor="user", action="chat.completion", payload={"request_id": rid, "model": result.model, "content_len": len(result.content)})
        # Request-ID im Header zurückgeben
        return JSONResponse(
            content=result.model_dump(),
            headers={"x-request-id": rid},
        )
    except ModelTimeoutError as e:
        append(actor="system", action="chat.timeout", payload={"request_id": e.request_id or rid})
        return JSONResponse(status_code=504, content={"code": e.code, "message": str(e), "request_id": e.request_id or rid}, headers={"x-request-id": rid})
    except ModelUnavailableError as e:
        return JSONResponse(status_code=502, content={"code": e.code, "message": str(e), "request_id": e.request_id or rid}, headers={"x-request-id": rid})
    except SyrionError as e:
        return JSONResponse(status_code=500, content={"code": e.code, "message": str(e), "request_id": e.request_id or rid}, headers={"x-request-id": rid})
    except asyncio.CancelledError:
        # Client hat Verbindung getrennt
        return Response(status_code=499, headers={"x-request-id": rid})


@router.post("/chat/stream")
async def chat_stream(request: Request, body: ChatRequest) -> Response:
    rid = _request_id_from(request, body)
    body.request_id = rid
    body.stream = True

    # UNTRAINED Check auch für Stream
    if is_untrained():
        status = get_model_status()

        async def untrained_gen() -> AsyncIterator[str]:
            yield f"data: {json.dumps({'error': {'code': 'MODEL_UNTRAINED', 'message': status.get('message', 'SYRION Model befindet sich noch in der Trainingsphase.')}, 'request_id': rid})}\n\n"

        return StreamingResponse(untrained_gen(), media_type="text/event-stream", headers={"x-request-id": rid, "cache-control": "no-cache"})

    async def sse_gen() -> AsyncIterator[str]:
        try:
            async for chunk in orchestrator.stream(body):
                # Client-Disconnect erkennen: wenn disconnected, abbrechen
                if await request.is_disconnected():
                    break
                # SSE Format
                data = json.dumps({"content": chunk, "request_id": rid}, ensure_ascii=False)
                yield f"data: {data}\n\n"
            yield f"data: {json.dumps({'done': True, 'request_id': rid})}\n\n"
        except ModelTimeoutError as e:
            yield f"data: {json.dumps({'error': {'code': e.code, 'message': str(e)}, 'request_id': rid})}\n\n"
        except (ModelUnavailableError, SyrionError) as e:
            code = getattr(e, "code", "SYRION_ERROR")
            yield f"data: {json.dumps({'error': {'code': code, 'message': str(e)}, 'request_id': rid})}\n\n"
        except asyncio.CancelledError:
            return

    return StreamingResponse(sse_gen(), media_type="text/event-stream", headers={"x-request-id": rid, "cache-control": "no-cache", "x-accel-buffering": "no"})
