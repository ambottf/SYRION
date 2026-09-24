"""Model Status — SYRION Modell Zustand (kein Fake)."""
from __future__ import annotations

import json
from pathlib import Path
from enum import Enum
from datetime import datetime, timezone


class ModelState(str, Enum):
    UNTRAINED = "UNTRAINED"
    TRAINING = "TRAINING"
    READY = "READY"
    ERROR = "ERROR"


# Pfad für Status-Datei (im Projekt-Root, unabhängig von cwd)
_STATUS_PATH = Path(__file__).resolve().parents[3] / "data" / "model" / "status.json"
_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)


def _default_status() -> dict:
    # Prüfe beide möglichen Checkpoint-Orte (core/checkpoints und SYRION/checkpoints)
    candidates = [
        Path(__file__).resolve().parents[3] / "checkpoints" / "syrion_final_run",
        Path(__file__).resolve().parents[2] / "checkpoints" / "syrion_final_run",  # core/checkpoints
        Path.cwd() / "checkpoints" / "syrion_final_run",
        Path.cwd() / "core" / "checkpoints" / "syrion_final_run",
    ]
    for ckpt_dir in candidates:
        has_ckpt = (ckpt_dir / "syrion_epoch_3" / "model.pt").exists() or (ckpt_dir / "best" / "model.pt").exists() or (ckpt_dir / "syrion_epoch_1" / "model.pt").exists()
        if has_ckpt:
            return {"state": ModelState.READY.value, "message": "SYRION Modell trainiert und bereit.", "checkpoint": str(ckpt_dir), "updated_at": datetime.now(timezone.utc).isoformat()}
    # Auch generisches checkpoints Verzeichnis prüfen
    for cand in [Path(__file__).resolve().parents[3] / "checkpoints", Path(__file__).resolve().parents[2] / "checkpoints"]:
        if any(cand.glob("syrion_*/model.pt")) or any(cand.glob("*/model.pt")):
            return {"state": ModelState.READY.value, "message": "SYRION Modell trainiert und bereit.", "checkpoint": str(cand), "updated_at": datetime.now(timezone.utc).isoformat()}
    return {"state": ModelState.UNTRAINED.value, "message": "SYRION Modell befindet sich noch in der Trainingsphase. Kein trainiertes Modell geladen.", "checkpoint": None, "updated_at": datetime.now(timezone.utc).isoformat()}


def get_status() -> dict:
    if not _STATUS_PATH.exists():
        status = _default_status()
        set_status(status["state"], status["message"])
        return status
    try:
        return json.loads(_STATUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _default_status()


def set_status(state: str, message: str, **extra) -> dict:
    payload = {"state": state, "message": message, "updated_at": datetime.now(timezone.utc).isoformat(), **extra}
    # Validierung
    if state not in [s.value for s in ModelState]:
        raise ValueError(f"Invalid state {state}")
    _STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def is_ready() -> bool:
    return get_status().get("state") == ModelState.READY.value


def is_untrained() -> bool:
    return get_status().get("state") == ModelState.UNTRAINED.value
