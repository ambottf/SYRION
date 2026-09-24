"""Provider C — Wikipedia OpenSearch (öffentlich, kein Key)."""
from __future__ import annotations

import httpx
from typing import List
from .base import SearchProvider, SearchResult


class WikipediaProvider(SearchProvider):
    name = "wikipedia"

    async def search(self, query: str, *, limit: int = 8) -> List[SearchResult]:
        url = "https://en.wikipedia.org/w/api.php"
        params = {"action": "opensearch", "search": query, "limit": limit, "namespace": 0, "format": "json"}
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.get(url, params=params, headers={"User-Agent": "SYRION-Research/0.4"})
                if r.status_code != 200:
                    return []
                data = r.json()
                # data: [query, [titles], [descriptions], [urls]]
                if len(data) < 4:
                    return []
                urls = data[3]
                titles = data[1]
                out: List[SearchResult] = []
                for i, u in enumerate(urls[:limit]):
                    title = titles[i] if i < len(titles) else None
                    out.append(SearchResult(url=u, title=title, snippet=None, provider=self.name))
                return out
        except Exception:
            return []
