"""SYRION Core Errors — typisierte, produktionsnahe Fehlerhierarchie."""
from __future__ import annotations


class SyrionError(Exception):
    """Basis für alle Core-Fehler. Trägt request_id für Korrelation."""

    def __init__(self, message: str, *, code: str = "SYRION_ERROR", request_id: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.request_id = request_id


class ModelTimeoutError(SyrionError):
    def __init__(self, message: str = "Model call timed out", *, request_id: str | None = None, timeout_ms: int | None = None) -> None:
        super().__init__(message, code="MODEL_TIMEOUT", request_id=request_id)
        self.timeout_ms = timeout_ms


class ModelUnavailableError(SyrionError):
    def __init__(self, message: str = "Model unavailable", *, request_id: str | None = None) -> None:
        super().__init__(message, code="MODEL_UNAVAILABLE", request_id=request_id)


class ContextBuildError(SyrionError):
    def __init__(self, message: str = "Context build failed", *, request_id: str | None = None) -> None:
        super().__init__(message, code="CONTEXT_BUILD_ERROR", request_id=request_id)


class MemoryError(SyrionError):
    def __init__(self, message: str = "Memory error", *, request_id: str | None = None) -> None:
        super().__init__(message, code="MEMORY_ERROR", request_id=request_id)
