"""SYRION Core Types — Pydantic DTOs, strikt typisiert (Phase 1)."""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ChatRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class ChatMessage(BaseModel):
    role: ChatRole
    content: str = Field(min_length=1, max_length=16000)


class ChatRequest(BaseModel):
    """Eingehende Chat-Anfrage (UI -> Core)."""

    message: str = Field(min_length=1, max_length=16000, description="User message")
    session_id: str | None = Field(default=None, max_length=64, description="Optional STM session")
    model: str | None = Field(default=None, description="Override model id, sonst Registry default")
    stream: bool = Field(default=False, description="SSE streaming gewünscht")
    timeout_ms: int = Field(default=30000, ge=1000, le=120000, description="Timeout für Modellaufruf")
    # interner Context, nicht vom Client gesetzt — wird vom Orchestrator gefüllt
    request_id: str | None = Field(default=None, description="Vom Core vergeben")


class MemoryContext(BaseModel):
    """Kontext, den Memory-Service liefert (STM + LTM Stub)."""

    system_prompt: str = Field(default="Du bist SYRION, eine lokale Intelligence-Plattform. Antworte hilfreich, präzise und verweise auf Quellen wenn vorhanden.")
    history: list[ChatMessage] = Field(default_factory=list)
    retrieved: list[str] = Field(default_factory=list, description="RAG snippets (Phase 1 Stub: leer)")
    session_id: str | None = None


class ChatUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class ChatResponse(BaseModel):
    request_id: str
    model: str
    content: str
    usage: ChatUsage | None = None
    # Provenienz für UI (Phase 1: leer, Phase 2: gefüllt)
    sources: list[str] = Field(default_factory=list)


class HealthStatus(BaseModel):
    status: Literal["ok", "degraded"]
    phase: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None = None
