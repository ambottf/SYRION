"""Firefox Adapter — gleiche Schnittstelle wie Chromium, andere Engine-Kennung."""
from __future__ import annotations

from .chromium import ChromiumAdapter, _extract_text
import httpx
from .base import BrowserType, FetchResult


class FirefoxAdapter(ChromiumAdapter):
    engine = BrowserType.FIREFOX

    def __init__(self, *, user_agent: str = "SYRION-Research/0.1 Firefox (+local-first)") -> None:
        super().__init__(user_agent=user_agent)

    # fetch identisch, aber Engine-Kennung anders — so kann SYRION mehrere Engines nutzen
    # Für echte Firefox-Engine später Playwright mit firefox channel, jetzt httpx-basiert
