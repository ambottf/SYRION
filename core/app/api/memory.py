"""Memory API — PENDING → APPROVED Workflow, echte Daten."""
from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.memory.store import MemoryStore

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])
store = MemoryStore()


class AddRequest(BaseModel):
    content: str
    type: str = "fact"
    source: str = "manual"
    url: str | None = None
    tags: list[str] = []


@router.get("")
async def list_memory(status: str | None = Query(None), tag: str | None = Query(None)) -> JSONResponse:
    entries = store.list(status=status, tag=tag)
    return JSONResponse({"entries": [e.to_dict() for e in entries], "counts": store.counts()})


@router.post("")
async def add_memory(body: AddRequest) -> JSONResponse:
    entry = store.add(content=body.content, type=body.type, source=body.source, url=body.url, tags=body.tags)
    return JSONResponse(entry.to_dict(), status_code=201)


@router.get("/{entry_id}")
async def get_memory(entry_id: str) -> JSONResponse:
    e = store.get(entry_id)
    if not e:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": f"Memory {entry_id} not found"})
    return JSONResponse(e.to_dict())


@router.post("/{entry_id}/approve")
async def approve_memory(entry_id: str) -> JSONResponse:
    try:
        e = store.approve(entry_id)
        return JSONResponse(e.to_dict())
    except KeyError as ex:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": str(ex)})
    except ValueError as ex:
        return JSONResponse(status_code=400, content={"code": "INVALID_STATE", "message": str(ex)})


@router.post("/{entry_id}/reject")
async def reject_memory(entry_id: str) -> JSONResponse:
    try:
        e = store.reject(entry_id)
        return JSONResponse(e.to_dict())
    except KeyError as ex:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": str(ex)})


@router.get("/stats/counts")
async def memory_counts() -> JSONResponse:
    return JSONResponse(store.counts())
