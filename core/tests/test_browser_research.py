"""Tests für Browser und Research — kontrolliert, PENDING, kein Bypass."""
import pathlib
import pytest

from app.browser.base import BrowserType
from app.browser.manager import browser_manager
from app.memory.store import MemoryStore
from app.research.engine import ResearchEngine, ResearchTask


def test_browser_manager():
    m = browser_manager
    assert "chromium" in m.list_engines()
    assert "firefox" in m.list_engines()
    c = m.get("chromium")
    assert c.engine == BrowserType.CHROMIUM
    f = m.get("firefox")
    assert f.engine == BrowserType.FIREFOX


@pytest.mark.asyncio
async def test_browser_fetch_blocked():
    adapter = browser_manager.get("chromium")
    # localhost blockiert
    with pytest.raises(ValueError, match="Localhost"):
        await adapter.fetch("http://localhost:8080/")
    # file:// blockiert
    with pytest.raises(ValueError):
        await adapter.fetch("file:///etc/passwd")


@pytest.mark.asyncio
async def test_research_dedupe_and_pending(tmp_path: pathlib.Path):
    store = MemoryStore(path=tmp_path / "research.jsonl")
    engine = ResearchEngine(store)

    # Mock Browser: patch fetch to avoid real HTTP
    from app.browser.chromium import ChromiumAdapter
    from app.browser.base import FetchResult

    async def mock_fetch(self, url, timeout=10):
        return FetchResult(url=url, status=200, content="SYRION is a local intelligence platform. SYRION has a brain. SYRION is local.", raw_html="<html>SYRION is a local intelligence platform.</html>", title="Test", engine="chromium")

    # Patch
    orig = ChromiumAdapter.fetch
    ChromiumAdapter.fetch = mock_fetch  # type: ignore[assignment]
    try:
        task = ResearchTask(topic="SYRION", urls=["https://example.com"], tags=["test"])
        result = await engine.run(task)
        assert result.fetched == 1
        assert result.created >= 1
        # Alle Einträge sind PENDING, nie direkt APPROVED
        for e in result.entries:
            assert e["trust_status"] == "PENDING"
        # Dedupe: zweiter Lauf mit gleicher URL sollte Duplikate erkennen
        result2 = await engine.run(task)
        assert result2.deduped >= 1
    finally:
        ChromiumAdapter.fetch = orig  # type: ignore[assignment]


@pytest.mark.asyncio
async def test_research_contradiction(tmp_path: pathlib.Path):
    store = MemoryStore(path=tmp_path / "research2.jsonl")
    engine = ResearchEngine(store)
    # Erster Eintrag
    store.add(content="SYRION ist schnell", source="test", tags=["speed"])
    from app.browser.chromium import ChromiumAdapter
    from app.browser.base import FetchResult

    async def mock_fetch(self, url, timeout=10):
        return FetchResult(url=url, status=200, content="SYRION ist nicht schnell. Das ist ein Widerspruch.", raw_html="<html></html>", title="Test", engine="chromium")

    orig = ChromiumAdapter.fetch
    ChromiumAdapter.fetch = mock_fetch  # type: ignore[assignment]
    try:
        task = ResearchTask(topic="SYRION", urls=["https://example.com"], tags=["speed"])
        result = await engine.run(task)
        assert result.contradictions >= 1 or any("contradiction" in str(e.get("history", "")) for e in result.entries)
    finally:
        ChromiumAdapter.fetch = orig  # type: ignore[assignment]
