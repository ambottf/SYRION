"""Research Engine — kontrolliert, mit PENDING und Quellenpflicht.

Ablauf (kontrolliert):
  1. Suche (hier: URL-Liste, später SearXNG)
  2. Fetch via BrowserManager (nur öffentlich, kein Bypass)
  3. Extrahieren (Browser liefert bereits Text)
  4. Relevanz prüfen (einfach: Keyword im Topic)
  5. Duplikate erkennen (MemoryStore content_hash)
  6. Widerspruch prüfen (MemoryStore Flag)
  7. Aktualität speichern (freshness)
  8. PENDING Eintrag erzeugen (nie direkt APPROVED)
  9. Beziehungen erkennen (Tags)
  10. Quellen speichern (URL, Titel)
"""
from __future__ import annotations

import asyncio
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from app.browser.manager import browser_manager
from app.memory.store import MemoryStore
from app.research.search.manager import search_manager
from app.research.source import SourceStore
from app.activity.stream import activity_stream


@dataclass
class ResearchTask:
    topic: str
    urls: List[str] = field(default_factory=list)  # explizite URLs oder via Search
    tags: List[str] = field(default_factory=list)
    engine: str = "chromium"
    timeout: float = 10.0
    use_search: bool = False
    search_provider: str | None = None
    max_urls: int = 5


@dataclass
class ResearchResult:
    task_id: str
    topic: str
    fetched: int
    created: int
    deduped: int
    contradictions: int
    entries: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: str | None = None


class ResearchEngine:
    def __init__(self, store: MemoryStore | None = None, source_store: SourceStore | None = None) -> None:
        self.store = store or MemoryStore()
        self.source_store = source_store or SourceStore()

    def _is_relevant(self, text: str, topic: str) -> bool:
        # Einfache Relevanz: Topic-Worte müssen vorkommen (später Cross-Encoder)
        topic_words = [w.lower() for w in re.findall(r"\w+", topic) if len(w) > 2]
        text_low = text.lower()
        return any(w in text_low for w in topic_words) if topic_words else True

    def _extract_facts(self, text: str, topic: str) -> List[str]:
        # Sehr einfach: Sätze die Topic-Worte enthalten, max 3 Fakten
        sentences = re.split(r"[.!?]\s+", text)
        facts: List[str] = []
        for s in sentences:
            s = s.strip()
            if len(s) < 20 or len(s) > 300:
                continue
            if self._is_relevant(s, topic):
                facts.append(s)
            if len(facts) >= 3:
                break
        return facts

    async def run(self, task: ResearchTask) -> ResearchResult:
        task_id = f"res_{uuid.uuid4().hex[:8]}"
        result = ResearchResult(task_id=task_id, topic=task.topic, fetched=0, created=0, deduped=0, contradictions=0)
        activity_stream.push(f"Research gestartet: {task.topic}", topic=task.topic)
        adapter = browser_manager.get(task.engine)

        # Wenn keine URLs aber Topic, suche via SearchProvider
        urls = list(task.urls)
        if not urls or task.use_search:
            activity_stream.push(f"Suchanfrage ausgeführt: {task.topic}", topic=task.topic)
            try:
                search_results = await search_manager.search(task.topic, limit=task.max_urls, provider=task.search_provider)
                for r in search_results:
                    if r.url not in urls:
                        urls.append(r.url)
                activity_stream.push(f"{len(search_results)} URLs gefunden für {task.topic}", topic=task.topic)
                result.sources.append({"search_provider": task.search_provider or search_manager.default, "query": task.topic, "found": len(search_results)})
            except Exception as e:
                activity_stream.push(f"Search Fehler: {e}", topic=task.topic, level="warning")

        # High-throughput: paralleles Fetching für 500/min (8.3/sec)
        # Für 500/min: 10 URLs parallel, je 3 Fakten = 30 per Batch, 17 Batches pro Minute
        semaphore = asyncio.Semaphore(10)  # max 10 parallel

        async def fetch_one(url: str):
            async with semaphore:
                parsed = urlparse(url)
                if parsed.scheme not in ("http", "https"):
                    return {"url": url, "error": "invalid scheme, skipped"}
                if "localhost" in url or "127.0.0.1" in url:
                    return {"url": url, "error": "localhost blocked"}
                activity_stream.push(f"Quelle abgerufen: {url}", topic=task.topic)
                try:
                    fetched = await adapter.fetch(url, timeout=task.timeout)
                    source = self.source_store.add(url=url, title=fetched.title, content=fetched.content)
                    if source.status == "duplicate":
                        activity_stream.push(f"Duplikat erkannt: {url}", topic=task.topic)
                        return {"url": url, "title": fetched.title, "status": fetched.status, "duplicate": True, "deduped": True}
                    activity_stream.push(f"Inhalt extrahiert: {url} ({len(fetched.content)} Zeichen)", topic=task.topic)
                    if not self._is_relevant(fetched.content, task.topic):
                        activity_stream.push(f"Nicht relevant: {url}", topic=task.topic, level="warning")
                        return {"url": url, "title": fetched.title, "status": fetched.status, "fetched": True, "relevant": False}
                    facts = self._extract_facts(fetched.content, task.topic)
                    # Für High-Throughput: mehr Fakten pro URL (bis 5)
                    created_here: List[Dict[str, Any]] = []
                    deduped_here = 0
                    contradictions_here = 0
                    for fact in facts[:5]:
                        before_counts = self.store.counts()
                        entry = self.store.add(content=fact, type="research", source=f"research:{task.topic}", url=url, tags=[task.topic.lower()] + task.tags)
                        after_counts = self.store.counts()
                        if after_counts["total"] == before_counts["total"]:
                            deduped_here += 1
                        else:
                            created_here.append(entry.to_dict())
                            if any(h.get("action") == "contradiction_flagged" for h in entry.history):
                                contradictions_here += 1
                    return {
                        "url": url,
                        "title": fetched.title,
                        "status": fetched.status,
                        "source_id": source.source_id,
                        "fetched": True,
                        "facts": facts,
                        "created_entries": created_here,
                        "deduped": deduped_here,
                        "contradictions": contradictions_here,
                    }
                except Exception as e:
                    activity_stream.push(f"Quelle Fehler: {url} — {str(e)[:100]}", topic=task.topic, level="warning")
                    return {"url": url, "error": str(e)[:200]}

        # Parallel ausführen
        fetch_results = await asyncio.gather(*[fetch_one(u) for u in urls[: task.max_urls]], return_exceptions=False)
        for res in fetch_results:
            if "error" in res:
                result.sources.append(res)
            elif res.get("duplicate"):
                result.sources.append(res)
                result.deduped += 1
            elif res.get("fetched"):
                result.fetched += 1
                result.sources.append({"url": res["url"], "title": res.get("title"), "status": res.get("status"), "source_id": res.get("source_id")})
                if not res.get("relevant", True) and not res.get("facts"):
                    continue
                # Verarbeite erstellte Einträge
                for entry in res.get("created_entries", []):
                    result.created += 1
                    result.entries.append(entry)
                    activity_stream.push(f"neuer Knowledge Candidate: {entry['content'][:50]}...", topic=task.topic)
                    activity_stream.push(f"Candidate PENDING gespeichert: {entry['id']}", topic=task.topic)
                    if any(h.get("action") == "contradiction_flagged" for h in entry.get("history", [])):
                        result.contradictions += 1
                        activity_stream.push(f"Widerspruch erkannt: {entry['id']}", topic=task.topic, level="warning")
                    if entry.get("relations"):
                        activity_stream.push(f"neue Beziehung erkannt: {entry['id']} -> {entry['relations'][0]}", topic=task.topic)
                result.deduped += res.get("deduped", 0)
                result.contradictions += res.get("contradictions", 0)

        result.finished_at = datetime.now(timezone.utc).isoformat()
        if result.created > 0:
            activity_stream.push(f"Knowledge Graph aktualisiert: +{result.created} Knoten", topic=task.topic)
        activity_stream.push(f"Research abgeschlossen: {task.topic} — {result.created} neu, {result.deduped} Duplikate, {result.contradictions} Widersprüche", topic=task.topic)
        return result

    # Sync wrapper für Tests
    def run_sync(self, task: ResearchTask) -> ResearchResult:
        import asyncio

        return asyncio.run(self.run(task))
