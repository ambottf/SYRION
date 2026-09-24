"""Browser Adapter — gemeinsame Schnittstelle (kein Captcha-Bypass, nur öffentlich)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class BrowserType(str, Enum):
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    GENERIC = "generic"


@dataclass
class FetchResult:
    url: str
    status: int
    content: str  # extrahierter Text
    raw_html: str
    title: str | None = None
    engine: str = BrowserType.GENERIC.value


class BrowserAdapter(ABC):
    """Abstraktion — SYRION darf keine Sicherheitsmechanismen umgehen."""

    engine: BrowserType

    @abstractmethod
    async def fetch(self, url: str, *, timeout: float = 10) -> FetchResult:
        """Holt öffentlich zugängliche Seite, extrahiert Text. Kein Login/Captcha-Bypass."""

    @abstractmethod
    async def health(self) -> bool:
        pass
