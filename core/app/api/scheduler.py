"""Scheduler API — 24/7 kontrolliert."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.activity.stream import activity_stream
from app.memory.store import MemoryStore
from app.research.engine import ResearchEngine, ResearchTask
from app.scheduler.engine import Scheduler

router = APIRouter(prefix="/api/v1/scheduler", tags=["scheduler"])
scheduler = Scheduler(max_parallel=3)
store = MemoryStore()
research_engine = ResearchEngine(store)


async def _handler(task) -> dict:
    # Handler für Scheduler: führt Research aus
    activity_stream.push(f"Research gestartet (Scheduler): {task.topic}", topic=task.topic)
    t = ResearchTask(topic=task.topic, urls=task.urls, tags=task.tags, engine="chromium", timeout=task.timeout_s)
    result = await research_engine.run(t)
    return {"created": result.created, "fetched": result.fetched}


class CreateTaskRequest(BaseModel):
    topic: str = Field(min_length=2)
    urls: list[str] = Field(min_length=1)
    interval_s: int = Field(ge=30, description="Sekunden zwischen Läufen, min 30")
    priority: int = Field(default=5, ge=1, le=10)
    tags: list[str] = Field(default_factory=list)
    timeout_s: float = Field(default=30, ge=5, le=120)


@router.get("")
async def list_tasks() -> JSONResponse:
    return JSONResponse({"tasks": scheduler.list(), "counts": scheduler.counts(), "status": scheduler.status})


@router.post("")
async def create_task(body: CreateTaskRequest) -> JSONResponse:
    task = scheduler.add(topic=body.topic, urls=body.urls, interval_s=body.interval_s, priority=body.priority, tags=body.tags, timeout_s=body.timeout_s)
    activity_stream.push(f"Scheduler Task erstellt: {body.topic} alle {body.interval_s}s", topic=body.topic)
    return JSONResponse(task.to_dict(), status_code=201)


@router.post("/{task_id}/pause")
async def pause_task(task_id: str) -> JSONResponse:
    # Einzelner Task pausieren: enabled=False
    t = scheduler.tasks.get(task_id)
    if not t:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": f"Task {task_id} not found"})
    t.enabled = False
    activity_stream.push(f"Scheduler Task pausiert: {t.topic}", topic=t.topic)
    return JSONResponse(t.to_dict())


@router.post("/{task_id}/resume")
async def resume_task(task_id: str) -> JSONResponse:
    t = scheduler.tasks.get(task_id)
    if not t:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": f"Task {task_id} not found"})
    t.enabled = True
    activity_stream.push(f"Scheduler Task fortgesetzt: {t.topic}", topic=t.topic)
    return JSONResponse(t.to_dict())


@router.delete("/{task_id}")
async def delete_task(task_id: str) -> JSONResponse:
    if task_id not in scheduler.tasks:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": f"Task {task_id} not found"})
    scheduler.remove(task_id)
    activity_stream.push(f"Scheduler Task gelöscht: {task_id}")
    return JSONResponse({"deleted": task_id})


@router.post("/pause")
async def pause_all() -> JSONResponse:
    scheduler.pause()
    return JSONResponse({"status": scheduler.status})


@router.post("/resume")
async def resume_all() -> JSONResponse:
    scheduler.resume()
    return JSONResponse({"status": scheduler.status})


@router.post("/stop")
async def stop_all() -> JSONResponse:
    scheduler.stop()
    return JSONResponse({"status": scheduler.status})


@router.post("/start")
async def start_all() -> JSONResponse:
    scheduler.start()
    return JSONResponse({"status": scheduler.status})


@router.post("/tick")
async def tick() -> JSONResponse:
    """Manueller Tick für Tests — führt fällige Tasks aus."""
    await scheduler.tick(_handler)
    return JSONResponse({"ticked": True, "counts": scheduler.counts()})


@router.get("/logs")
async def scheduler_logs() -> JSONResponse:
    try:
        lines = scheduler.log_path.read_text(encoding="utf-8").splitlines()[-50:]
        import json

        entries = [json.loads(l) for l in lines if l.strip()]
        return JSONResponse({"logs": entries})
    except Exception:
        return JSONResponse({"logs": []})
