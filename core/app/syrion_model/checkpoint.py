"""Checkpoint-System — versioniert, signierbar, reproduzierbar."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timezone


class CheckpointManager:
    def __init__(self, base_dir: Path | str = "checkpoints") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, *, run_id: str, model_config: Dict[str, Any], dataset_version: str, metrics: Dict[str, Any]) -> Path:
        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model_config": model_config,
            "dataset_version": dataset_version,
            "metrics": metrics,
            "version": "0.1.0",
        }
        # Hash für Integrität
        payload["hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
        out = run_dir / "checkpoint.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        # Latest Link
        latest = self.base_dir / "latest.json"
        latest.write_text(json.dumps({"run_id": run_id, "path": str(out)}, ensure_ascii=False, indent=2), encoding="utf-8")
        return out

    def load(self, run_id: str) -> Dict[str, Any]:
        p = self.base_dir / run_id / "checkpoint.json"
        return json.loads(p.read_text(encoding="utf-8"))

    def list(self) -> list[str]:
        return sorted([p.name for p in self.base_dir.iterdir() if p.is_dir()])

    def latest(self) -> Dict[str, Any] | None:
        p = self.base_dir / "latest.json"
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))
