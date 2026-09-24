"""Brain API — live Sicht, stabil, nie Crash, auch bei 10k+ Nodes."""
from __future__ import annotations

import time
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.brain.store import BrainStore

router = APIRouter(prefix="/api/v1/brain", tags=["brain"])
brain_store = BrainStore()

# Cache: 1s TTL für hohe Last (500/min + Polling)
_cache: dict[str, tuple[float, dict]] = {}
_last_req: dict[str, float] = {}


def _rate_limit_ok(key: str = "global", limit: float = 20.0) -> bool:
    now = time.time()
    last = _last_req.get(key, 0)
    if now - last < 1.0 / limit:
        return False
    _last_req[key] = now
    return True


def _cached(key: str, ttl: float = 1.0) -> dict | None:
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < ttl:
            return data
    return None


def _set_cache(key: str, data: dict) -> None:
    _cache[key] = (time.time(), data)


@router.get("")
async def brain_snapshot(limit: int = Query(100, ge=1, le=500)) -> JSONResponse:
    cache_key = f"snapshot:{limit}"
    cached = _cached(cache_key, ttl=1.0)
    if cached:
        return JSONResponse(cached)
    try:
        if not _rate_limit_ok("brain_snapshot", 30):
            snap = brain_store.snapshot()
            snap["nodes"] = snap["nodes"][:limit]
            snap["recent"] = snap["recent"][:20]
            _set_cache(cache_key, snap)
            return JSONResponse(snap)
        snap = brain_store.snapshot()
        snap["nodes"] = snap["nodes"][:limit]
        snap["recent"] = snap["recent"][:20]
        _set_cache(cache_key, snap)
        return JSONResponse(snap)
    except Exception as e:
        return JSONResponse({"counts": {"total": 0, "facts": 0, "pending": 0, "approved": 0, "relations": 0, "sources": 0}, "nodes": [], "topics": [], "sources": [], "growth": [], "recent": [], "error": str(e)[:200], "timestamp": ""})


@router.get("/graph")
async def brain_graph(limit: int = Query(200, ge=1, le=1000)) -> JSONResponse:
    cache_key = f"graph:{limit}"
    cached = _cached(cache_key, ttl=1.0)
    if cached:
        return JSONResponse(cached)
    try:
        if not _rate_limit_ok("brain_graph", 30):
            g = brain_store.graph()
            g["nodes"] = g["nodes"][:limit]
            visible = {n["id"] for n in g["nodes"]}
            g["edges"] = [e for e in g["edges"] if e["source"] in visible and e["target"] in visible][:500]
            _set_cache(cache_key, g)
            return JSONResponse(g)
        g = brain_store.graph()
        g["nodes"] = g["nodes"][:limit]
        visible = {n["id"] for n in g["nodes"]}
        g["edges"] = [e for e in g["edges"] if e["source"] in visible and e["target"] in visible][:1000]
        _set_cache(cache_key, g)
        return JSONResponse(g)
    except Exception as e:
        return JSONResponse({"nodes": [], "edges": [], "error": str(e)[:200]})


@router.get("/counts")
async def brain_counts() -> JSONResponse:
    try:
        snap = brain_store.snapshot()
        return JSONResponse(snap["counts"])
    except Exception as e:
        return JSONResponse({"total": 0, "facts": 0, "pending": 0, "approved": 0, "relations": 0, "sources": 0, "error": str(e)[:200]})
