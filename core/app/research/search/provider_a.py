"""Provider A — DuckDuckGo HTML (kein API-Key, öffentlich)."""
from __future__ import annotations

import re
import httpx
from typing import List
from .base import SearchProvider, SearchResult


class DuckDuckGoProvider(SearchProvider):
    name = "duckduckgo"

    async def search(self, query: str, *, limit: int = 8) -> List[SearchResult]:
        # Einfache DDG HTML Suche (öffentlich, kein Bypass)
        url = "https://html.duckduckgo.com/html/"
        try:
            async with httpx.AsyncClient(timeout=8, follow_redirects=True, headers={"User-Agent": "SYRION-Research/0.4"}) as client:
                r = await client.post(url, data={"q": query})
                if r.status_code != 200:
                    return []
                html = r.text
                # Extrahiere Links: <a class="result__url" href="...">
                # Fallback: alle https:// Links
                links = re.findall(r'href="(https://[^"]+)"', html)
                # Dedupe, filter
                seen = set()
                out: List[SearchResult] = []
                for u in links:
                    if "duckduckgo.com" in u:
                        continue
                    if u in seen:
                        continue
                    seen.add(u)
                    out.append(SearchResult(url=u, title=None, snippet=None, provider=self.name))
                    if len(out) >= limit:
                        break
                return out
        except Exception:
            return []

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get("https://duckduckgo.com", headers={"User-Agent": "SYRION-Research/0.4"})
                return r.status_code == 200
        except Exception:
            return False
