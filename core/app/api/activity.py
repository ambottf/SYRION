"""Activity Stream API — SSE live."""
from __future__ import annotations

import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse

from app.activity.stream import activity_stream

router = APIRouter(prefix="/api/v1/activity", tags=["activity"])


@router.get("")
async def recent() -> JSONResponse:
    return JSONResponse({"events": activity_stream.recent(50)})


@router.get("/stream")
async def stream():
    async def gen():
        async for ev in activity_stream.subscribe():
            data = json.dumps(ev, ensure_ascii=False)
            yield f"data: {data}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"cache-control": "no-cache", "x-accel-buffering": "no"})


@router.post("/push")
async def push(body: dict) -> JSONResponse:
    msg = body.get("message", "test")
    topic = body.get("topic")
    ev = activity_stream.push(msg, topic=topic)
    return JSONResponse(ev)
