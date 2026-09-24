"""Browser Manager — wählt Engine, respektiert Allowlist, kein Bypass."""
from __future__ import annotations

from typing import Dict

from .base import BrowserAdapter, BrowserType
from .chromium import ChromiumAdapter
from .firefox import FirefoxAdapter


class BrowserManager:
    def __init__(self) -> None:
        self._adapters: Dict[str, BrowserAdapter] = {
            BrowserType.CHROMIUM.value: ChromiumAdapter(),
            BrowserType.FIREFOX.value: FirefoxAdapter(),
            BrowserType.GENERIC.value: ChromiumAdapter(),
        }
        self.default = BrowserType.CHROMIUM.value

    def get(self, engine: str | None = None) -> BrowserAdapter:
        return self._adapters.get(engine or self.default, self._adapters[self.default])

    def list_engines(self) -> list[str]:
        return list(self._adapters.keys())


browser_manager = BrowserManager()
