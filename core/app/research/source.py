"""Source System — jede Information hat eine Quelle, Duplikate werden erkannt."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse


@dataclass
class Source:
    source_id: str
    url: str
    domain: str
    title: str | None
    retrieved_at: str
    published_at: str | None
    author: str | None
    content_hash: str
    content: str
    source_type: str = "web"
    status: str = "active"  # active, duplicate, invalid

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SourceStore:
    def __init__(self, path: Path | str = "data/research/sources.jsonl") -> None:
        self.path = Path(path)
        # Absoluter Pfad
        if not self.path.is_absolute():
            self.path = Path(__file__).resolve().parents[3] / self.path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._by_hash: Dict[str, Source] = {}
        self._by_url: Dict[str, Source] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                s = Source(**data)
                self._by_hash[s.content_hash] = s
                self._by_url[s.url] = s
            except Exception:
                continue

    def _persist(self, source: Source) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(source.to_dict(), ensure_ascii=False) + "\n")

    def add(self, *, url: str, title: str | None, content: str, author: str | None = None, published_at: str | None = None, source_type: str = "web") -> Source:
        domain = urlparse(url).netloc
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        # Duplikat-Prüfung: gleiche URL oder gleicher content_hash
        if url in self._by_url:
            existing = self._by_url[url]
            # Gleicher Inhalt? dann duplicate
            if existing.content_hash == content_hash:
                existing.status = "duplicate"
                return existing
        if content_hash in self._by_hash:
            # Gleicher Inhalt von anderer URL -> duplicate
            existing = self._by_hash[content_hash]
            existing.status = "duplicate"
            return existing

        source_id = f"src_{content_hash[:8]}"
        src = Source(
            source_id=source_id,
            url=url,
            domain=domain,
            title=title,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            published_at=published_at,
            author=author,
            content_hash=content_hash,
            content=content[:8000],
            source_type=source_type,
            status="active",
        )
        self._by_hash[content_hash] = src
        self._by_url[url] = src
        self._persist(src)
        return src

    def get_by_url(self, url: str) -> Source | None:
        return self._by_url.get(url)

    def get_by_hash(self, h: str) -> Source | None:
        return self._by_hash.get(h)

    def list(self, limit: int = 50) -> List[Source]:
        # Lade frisch
        self._load()
        # Dedupe by hash
        seen: Dict[str, Source] = {}
        for s in self._by_hash.values():
            seen[s.content_hash] = s
        return list(seen.values())[-limit:]

    def is_duplicate(self, url: str, content: str) -> bool:
        h = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        return url in self._by_url or h in self._by_hash
