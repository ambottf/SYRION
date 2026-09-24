"""Search Provider Abstraction — SYRION kann mehrere Anbieter nutzen, konfigurierbar."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class SearchResult:
    url: str
    title: str | None = None
    snippet: str | None = None
    provider: str = "unknown"


class SearchProvider(ABC):
    """Abstraktion — kein hartes Coupling an einen Anbieter."""

    name: str

    @abstractmethod
    async def search(self, query: str, *, limit: int = 8) -> List[SearchResult]:
        """Führt Suche aus, gibt URLs zurück. Keine Ausführung von externem Code."""

    async def health(self) -> bool:
        return True
