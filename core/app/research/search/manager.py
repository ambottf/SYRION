"""Search Manager — wählt Provider via Konfiguration, kein hartes Coupling."""
from __future__ import annotations

import os
from typing import List, Dict
from .base import SearchProvider, SearchResult
from .provider_a import DuckDuckGoProvider
from .provider_b import MockProvider
from .provider_c import WikipediaProvider


class SearchManager:
    def __init__(self, default: str | None = None) -> None:
        provider_name = (default or os.getenv("SYRION_SEARCH_PROVIDER", "mock")).lower()
        self.providers: Dict[str, SearchProvider] = {
            "duckduckgo": DuckDuckGoProvider(),
            "mock": MockProvider(),
            "wikipedia": WikipediaProvider(),
        }
        self.default = provider_name if provider_name in self.providers else "mock"

    def get(self, name: str | None = None) -> SearchProvider:
        return self.providers.get((name or self.default).lower(), self.providers[self.default])

    def list_providers(self) -> List[str]:
        return list(self.providers.keys())

    async def search(self, query: str, *, limit: int = 8, provider: str | None = None) -> List[SearchResult]:
        prov = self.get(provider)
        try:
            results = await prov.search(query, limit=limit)
            if results:
                return results
        except Exception:
            pass
        # Fallback: versuche Mock wenn primärer leer/fehlerhaft
        if prov.name != "mock":
            try:
                return await self.providers["mock"].search(query, limit=limit)
            except Exception:
                pass
        return []


search_manager = SearchManager()
