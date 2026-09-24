"""Browser Abstraction — SYRION soll mit mehreren Engines arbeiten können."""
from .base import BrowserAdapter, BrowserType  # noqa: F401
from .chromium import ChromiumAdapter  # noqa: F401
from .firefox import FirefoxAdapter  # noqa: F401
from .manager import BrowserManager  # noqa: F401

__all__ = ["BrowserAdapter", "BrowserType", "ChromiumAdapter", "FirefoxAdapter", "BrowserManager"]
