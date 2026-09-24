"""
SYRION Gateway — Phase 2 Brain (SYRION-eigenes Modell, kein Ollama)
SYRION_MODEL -> CORE -> MEMORY -> KNOWLEDGE BASE -> KNOWLEDGE GRAPH
+ Research Engine (kontrolliert, PENDING) + Browser + Scheduler + Brain Live
"""
from __future__ import annotations

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.activity.stream import activity_stream
from app.api.activity import router as activity_router
from app.api.brain import router as brain_router
from app.api.brain_highthroughput import router as brain_ht_router
from app.api.chat import router as chat_router
from app.api.memory import router as memory_router
from app.api.models import router as models_router
from app.api.research import router as research_router
from app.api.scheduler import router as scheduler_router, scheduler
from app.audit.audit_log import append, verify_chain
from app.core.logging import log
from app.core.model_manager import model_manager
from app.security.policy_engine import engine

app = FastAPI(
    title="SYRION Gateway",
    version="0.4.0-brain",
    description="SYRION MODEL -> CORE -> MEMORY -> KNOWLEDGE BASE -> KNOWLEDGE GRAPH (eigenes Modell, kein Ollama)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(models_router)
app.include_router(brain_router)
app.include_router(brain_ht_router)
app.include_router(memory_router)
app.include_router(research_router)
app.include_router(scheduler_router)
app.include_router(activity_router)


@app.on_event("startup")
async def on_startup() -> None:
    append(actor="system", action="gateway.startup", payload={"policy_version": engine.get_version()})
    try:
        status = await model_manager.get_status()
        log("info", "model startup check", **status)
        append(actor="system", action="model.startup_check", payload=status)
        activity_stream.push("SYRION Gateway gestartet", level="info")
        activity_stream.push(f"SYRION Modell: {status.get('active_model')} — {status.get('message')}", level="info")
    except Exception as e:
        log("warning", "model startup check failed", error=str(e))
        append(actor="system", action="model.startup_check_failed", payload={"error": str(e)})

    # 24/7 Scheduler Hintergrund-Loop
    scheduler.start()

    async def scheduler_loop() -> None:
        from app.research.engine import ResearchEngine

        # Import hier, um Zyklus zu vermeiden — handler nutzt ResearchEngine
        while True:
            try:
                if scheduler.status == "running":
                    # Tick führt fällige Tasks aus
                    from app.api.scheduler import _handler

                    await scheduler.tick(_handler)
            except Exception as e:
                log("warning", "scheduler tick failed", error=str(e))
            await asyncio.sleep(5)

    asyncio.create_task(scheduler_loop())

@app.get("/api/v1/health")
def health() -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "phase": "1-llm",
        "policy_version": engine.get_version(),
        "policy_immutable": engine.is_immutable(),
        "audit_chain_ok": verify_chain(),
    })

@app.get("/api/v1/ready")
def ready() -> JSONResponse:
    ok = engine.get_version() != "unknown"
    return JSONResponse({"ready": ok, "policy_loaded": ok})

@app.get("/api/v1/policy")
def policy_readonly() -> JSONResponse:
    return JSONResponse({
        "policy_version": engine.get_version(),
        "immutable": engine.is_immutable(),
        "note": "Read-only stub. Änderungen nur offline, signiert.",
    })
