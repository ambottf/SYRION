"""Provider B — Mock (für Tests, kein Internet nötig, deterministisch)."""
from __future__ import annotations

from typing import List
from .base import SearchProvider, SearchResult


class MockProvider(SearchProvider):
    name = "mock"

    def __init__(self, urls: List[str] | None = None) -> None:
        self.urls = urls or ["https://example.com", "https://httpbin.org/html"]

    async def search(self, query: str, *, limit: int = 8) -> List[SearchResult]:
        # Deterministisch: gibt example.com zurück, egal was query ist (für Tests)
        out: List[SearchResult] = []
        for u in self.urls[:limit]:
            out.append(SearchResult(url=u, title=f"Mock result for {query}", snippet="Mock snippet", provider=self.name))
        return out
