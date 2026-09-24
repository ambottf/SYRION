"""Model-API — SYRION eigenes Modell (kein Ollama). Status, Liste, Wechsel, Laden."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.errors import ModelUnavailableError
from app.core.model_manager import model_manager

router = APIRouter(prefix="/api/v1/models", tags=["models"])


class SelectRequest(BaseModel):
    model_id: str


class PullRequest(BaseModel):
    model_id: str


@router.get("")
async def list_models(request: Request) -> JSONResponse:
    model_manager.sync_registry()
    return JSONResponse(
        {
            "active": model_manager.registry.default_model_id(),
            "available": model_manager.registry.list_models(),
            "configured": model_manager.list_configured(),
        }
    )


@router.get("/status")
async def model_status(request: Request) -> JSONResponse:
    status = await model_manager.get_status()
    return JSONResponse(status)


@router.post("/select")
async def select_model(body: SelectRequest, request: Request) -> JSONResponse:
    try:
        active = model_manager.select_model(body.model_id)
        from app.audit.audit_log import append

        append(actor="user", action="model.select", payload={"model_id": active})
        return JSONResponse({"active": active, "message": f"SYRION Modell gewechselt zu {active}"})
    except ModelUnavailableError as e:
        return JSONResponse(status_code=404, content={"code": e.code, "message": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"code": "MODEL_SELECT_ERROR", "message": str(e)})


@router.post("/pull")
async def pull_model(body: PullRequest, request: Request) -> JSONResponse:
    """Modell laden — für SYRION: prüft ob Version in Registry, sonst Hinweis auf Training."""
    # SYRION Modelle sind lokal, kein Ollama pull. Stattdessen: Registry prüfen
    configured = model_manager.list_configured()
    ids = [c["id"] for c in configured]
    if body.model_id in ids or body.model_id in model_manager.registry.list_models():
        return JSONResponse({"model_id": body.model_id, "status": "available", "message": f"SYRION Modell {body.model_id} lokal verfügbar (Basis)."})
    # Unbekanntes Modell -> registrieren als neues SYRION Modell (leere Basis)
    try:
        model_manager.select_model(body.model_id)
        return JSONResponse({"model_id": body.model_id, "status": "registered", "message": f"SYRION Modell {body.model_id} als neue Version registriert (Training erforderlich)."})
    except Exception as e:
        return JSONResponse(status_code=502, content={"code": "MODEL_PULL_FAILED", "message": str(e)})


@router.post("/load")
async def load_model(body: PullRequest, request: Request) -> JSONResponse:
    """Alias für pull — SYRION Terminologie: laden."""
    return await pull_model(body, request)
