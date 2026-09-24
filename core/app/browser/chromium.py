"""Chromium Adapter — für SYRION Research (kontrolliert, nur öffentlich)."""
from __future__ import annotations

import re
import httpx

from .base import BrowserAdapter, BrowserType, FetchResult


def _extract_text(html: str) -> tuple[str, str | None]:
    # Einfache Extraktion ohne externe Abhängigkeit (später trafilatura)
    # Titel
    m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    title = m.group(1).strip() if m else None
    if title:
        title = re.sub(r"\s+", " ", title)[:200]
    # Entferne Scripts/Styles
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:8000], title  # Limit


class ChromiumAdapter(BrowserAdapter):
    engine = BrowserType.CHROMIUM

    def __init__(self, *, user_agent: str = "SYRION-Research/0.1 (+local-first)") -> None:
        self.user_agent = user_agent

    async def fetch(self, url: str, *, timeout: float = 10) -> FetchResult:
        # Validierung: nur http/https, kein file://, kein localhost Bypass
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"Only http/https allowed, got {url}")
        if "localhost" in url or "127.0.0.1" in url:
            raise ValueError("Localhost not allowed for Research")
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers={"User-Agent": self.user_agent}) as client:
            r = await client.get(url)
            if r.status_code != 200:
                raise RuntimeError(f"Fetch {r.status_code} for {url}")
            html = r.text
            text, title = _extract_text(html)
            if not text:
                raise RuntimeError(f"Empty content after extraction for {url}")
            return FetchResult(url=url, status=r.status_code, content=text, raw_html=html[:20000], title=title, engine=self.engine.value)

    async def health(self) -> bool:
        return True
