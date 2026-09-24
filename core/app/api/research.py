"""Research API — kontrollierte Recherche, PENDING, mit Activity Stream."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.activity.stream import activity_stream
from app.memory.store import MemoryStore
from app.research.engine import ResearchEngine, ResearchTask

router = APIRouter(prefix="/api/v1/research", tags=["research"])
store = MemoryStore()
engine = ResearchEngine(store)


class ResearchRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=200)
    urls: list[str] = Field(default_factory=list, max_length=10)
    tags: list[str] = Field(default_factory=list)
    engine: str = Field(default="chromium", pattern="^(chromium|firefox|generic)$")
    timeout: float = Field(default=10, ge=3, le=30)
    use_search: bool = False
    search_provider: str | None = Field(default=None, pattern="^(duckduckgo|mock|wikipedia)$")
    max_urls: int = Field(default=5, ge=1, le=10)


@router.post("")
async def run_research(body: ResearchRequest) -> JSONResponse:
    # Validierung: wenn keine URLs und kein search, Fehler
    if not body.urls and not body.use_search:
        return JSONResponse(status_code=422, content={"code": "NO_URLS", "message": "Entweder urls angeben oder use_search=true"})
    task = ResearchTask(topic=body.topic, urls=body.urls, tags=body.tags, engine=body.engine, timeout=body.timeout, use_search=body.use_search, search_provider=body.search_provider, max_urls=body.max_urls)
    activity_stream.push(f"Research gestartet: {body.topic}", topic=body.topic)
    result = await engine.run(task)
    # Push weitere Events (handle both URL sources and search meta)
    for src in result.sources:
        if "error" in src:
            url = src.get("url", "unknown")
            activity_stream.push(f"Quelle Fehler: {url} — {src['error']}", topic=body.topic, level="warning")
        elif "url" in src:
            activity_stream.push(f"Quelle gefunden: {src.get('title') or src['url']}", topic=body.topic)
        elif "search_provider" in src:
            # Search meta, not a URL source
            continue
        else:
            activity_stream.push(f"Quelle: {src}", topic=body.topic)
    for e in result.entries:
        activity_stream.push(f"neue Information erkannt: {e['content'][:60]}...", topic=body.topic)
        activity_stream.push(f"Quelle gespeichert: {e['source']}", topic=body.topic)
        if e.get("relations"):
            activity_stream.push(f"neue Beziehung erkannt: {e['id']} -> {e['relations'][0]}", topic=body.topic)
    if result.entries:
        activity_stream.push(f"Knowledge Graph aktualisiert: +{len(result.entries)} Knoten", topic=body.topic)
    return JSONResponse(
        {
            "task_id": result.task_id,
            "topic": result.topic,
            "fetched": result.fetched,
            "created": result.created,
            "deduped": result.deduped,
            "contradictions": result.contradictions,
            "entries": result.entries,
            "sources": result.sources,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
        }
    )


@router.get("/recent")
async def recent_research() -> JSONResponse:
    # Zeige letzte PENDING Einträge als Research-Ergebnisse
    entries = store.list(status="PENDING")
    return JSONResponse({"entries": [e.to_dict() for e in entries[:20]]})
