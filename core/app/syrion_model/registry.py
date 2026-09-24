"""Model Registry — Versionierung für SYRION eigenes Modell.

Kein Ollama. Eigene Versionierung, signierbar, mit Checkpoint-Link.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any


@dataclass
class ModelVersion:
    version: str  # semver
    checkpoint: str  # Pfad zu checkpoint.json
    vocab_version: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    signed_by: str | None = None
    signature: str | None = None  # später: echte Signatur
    notes: str = ""


class SyrionModelRegistry:
    def __init__(self, base_dir: Path | str = "models/syrion") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.base_dir / "registry.json"
        if not self._index_path.exists():
            self._index_path.write_text(json.dumps({"versions": []}, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> Dict[str, Any]:
        return json.loads(self._index_path.read_text(encoding="utf-8"))

    def _save(self, data: Dict[str, Any]) -> None:
        self._index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def register(self, version: ModelVersion) -> None:
        data = self._load()
        # Duplikat verhindern
        for v in data["versions"]:
            if v["version"] == version.version:
                raise ValueError(f"Version {version.version} bereits registriert")
        data["versions"].append(version.__dict__)
        # Sort semver (einfach lexikografisch für 0.1.0)
        data["versions"].sort(key=lambda x: x["version"])
        self._save(data)

    def list(self) -> List[ModelVersion]:
        data = self._load()
        return [ModelVersion(**v) for v in data["versions"]]

    def latest(self) -> ModelVersion | None:
        vs = self.list()
        return vs[-1] if vs else None

    def get(self, version: str) -> ModelVersion | None:
        for v in self.list():
            if v.version == version:
                return v
        return None

    def set_active(self, version: str) -> None:
        if not self.get(version):
            raise ValueError(f"Version {version} nicht gefunden")
        data = self._load()
        data["active"] = version
        self._save(data)

    def active_version(self) -> str | None:
        data = self._load()
        return data.get("active")
