"""ModelManager — verwaltet SYRION eigenes Modell (kein Ollama).

Lokal-first: Kein Cloud, kein externes LLM als Kern. Wenn kein SYRION Modell
verfügbar, läuft Core im degraded Modus (klare Meldung, kein Fake), aber kein Crash.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Literal

import yaml

from app.syrion_model.status import get_status as get_syrion_status

from .model_adapter import ModelRegistry, SyrionAdapter

# Config liegt im Projekt-Root: SYRION/config/models.yaml — unabhängig von cwd
_DEFAULT_CONFIG = Path(__file__).resolve().parents[3] / "config" / "models.yaml"
CONFIG_PATH = Path(__import__("os").getenv("SYRION_MODELS_CONFIG", str(_DEFAULT_CONFIG)))


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _check_resources() -> dict[str, Any]:
    """Prüft RAM/Disk/CPU — für SYRION Training/Inferenz."""
    result: dict[str, Any] = {}
    try:
        try:
            import psutil

            vm = psutil.virtual_memory()
            result["ram_total_mb"] = int(vm.total / 1024 / 1024)
            result["ram_available_mb"] = int(vm.available / 1024 / 1024)
            result["ram_percent"] = vm.percent
        except Exception:
            result["ram_total_mb"] = None
            result["ram_available_mb"] = None

        total, used, free = shutil.disk_usage(Path.cwd())
        result["disk_total_gb"] = round(total / 1024**3, 1)
        result["disk_free_gb"] = round(free / 1024**3, 1)
        result["cpu_count"] = __import__("os").cpu_count()
        ram_ok = (result.get("ram_available_mb") or 999999) >= 2000
        disk_ok = result["disk_free_gb"] >= 2
        result["sufficient_for_syrion_base"] = ram_ok and disk_ok
        result["sufficient_for_syrion_large"] = (result.get("ram_available_mb") or 0) >= 8000 and disk_ok
    except Exception as e:
        result["error"] = str(e)
        result["sufficient_for_syrion_base"] = None
    return result


class ModelManager:
    """Zentrale Stelle für SYRION Modell-Konfiguration und Status."""

    def __init__(self, *, config_path: Path | None = None, registry: ModelRegistry | None = None) -> None:
        self.config_path = config_path or CONFIG_PATH
        self.registry = registry or ModelRegistry()
        self._config: dict[str, Any] = _load_yaml(self.config_path)
        # Stelle sicher, dass Registry dem Config entspricht
        self.sync_registry()

    def reload(self) -> dict[str, Any]:
        self._config = _load_yaml(self.config_path)
        return self._config

    def list_configured(self) -> list[dict[str, Any]]:
        models = self._config.get("models", {})
        out: list[dict[str, Any]] = []
        for key, cfg in models.items():
            out.append({"key": key, "id": cfg.get("model_id"), "provider": cfg.get("provider"), "enabled": cfg.get("enabled"), "version": cfg.get("version")})
        return out

    def get_default_model_id(self) -> str | None:
        models = self._config.get("models", {})
        for k in ("llm_chat", "syrion_core", "syrion"):
            if k in models and models[k].get("enabled") and models[k].get("model_id"):
                return str(models[k]["model_id"])
        for cfg in models.values():
            if cfg.get("enabled") and cfg.get("model_id") and cfg.get("provider") == "syrion":
                return str(cfg["model_id"])
        # Fallback: erstes syrion Modell
        for cfg in models.values():
            if cfg.get("provider") == "syrion" and cfg.get("model_id"):
                return str(cfg["model_id"])
        return self.registry.default_model_id()

    def sync_registry(self) -> None:
        """Registriert SYRION Adapter für alle enabled syrion Modelle aus Config."""
        models = self._config.get("models", {})
        for cfg in models.values():
            if not cfg.get("enabled"):
                continue
            if cfg.get("provider") != "syrion":
                continue
            model_id = cfg.get("model_id")
            if model_id and model_id not in self.registry.list_models():
                try:
                    self.registry.register(SyrionAdapter(model_id=str(model_id)))
                except Exception:
                    pass

    async def check_reachable(self, base_url: str | None = None) -> bool:
        # SYRION Modell ist immer lokal erreichbar (kein externer Server) — prüfe ob Registry existiert
        try:
            # Health des aktiven Adapters
            adapter = self.registry._default  # type: ignore[attr-defined]
            return await adapter.health()
        except Exception:
            return False

    async def check_model_available(self, model_id: str, base_url: str | None = None) -> bool:
        # Für SYRION: verfügbar wenn Adapter registriert und health true
        try:
            if model_id in self.registry.list_models():
                adapter = self.registry._adapters[model_id]  # type: ignore[attr-defined]
                return await adapter.health()
            return False
        except Exception:
            return False

    def _endpoint_for(self, model_id: str | None) -> str | None:
        if not model_id:
            return None
        for cfg in self._config.get("models", {}).values():
            if cfg.get("model_id") == model_id:
                return cfg.get("endpoint")
        return None

    async def get_status(self) -> dict[str, Any]:
        """Gesamtstatus für /api/v1/models/status."""
        self.reload()
        self.sync_registry()
        configured_default = self.get_default_model_id()
        active = self.registry.default_model_id()

        # Auto-aktivieren wenn verfügbar
        if configured_default and configured_default != active and configured_default in self.registry.list_models():
            try:
                adapter = self.registry._adapters[configured_default]  # type: ignore[attr-defined]
                if await adapter.health():
                    self.registry.set_default(configured_default)
                    active = configured_default
            except Exception:
                pass

        reachable = await self.check_reachable()
        available = False
        if configured_default:
            available = await self.check_model_available(configured_default)

        resources = _check_resources()
        # SYRION eigenes Modell Status (UNTRAINED/TRAINING/READY)
        syrion_state = get_syrion_status()
        syrion_model_state = syrion_state.get("state", "UNTRAINED")

        if syrion_model_state == "UNTRAINED":
            state: Literal["ok", "degraded", "unavailable"] = "degraded"
            message = "SYRION Model befindet sich noch in der Trainingsphase. Kein trainiertes Modell aktiv — Basis-Inferenz mit zufälligen Gewichten."
        elif syrion_model_state == "TRAINING":
            state = "degraded"
            message = f"SYRION Modell Training läuft — Basis '{active}' aktiv, echtes Training folgt."
        elif not reachable or not available:
            if active.startswith("syrion-") and reachable:
                state = "ok"
                message = f"SYRION Modell '{active}' bereit (lokal, Version {active})."
            else:
                state = "degraded"
                message = f"SYRION Modell '{configured_default}' wird vorbereitet — Basis-Modell '{active}' aktiv. Training folgt."
        else:
            state = "ok"
            message = f"SYRION Modell '{active}' bereit."

        return {
            "state": state,
            "message": message,
            "active_model": active,
            "configured_default": configured_default,
            "reachable": reachable,
            "available": available,
            "syrion_model_state": syrion_model_state,
            "syrion_model_message": syrion_state.get("message"),
            "resources": resources,
            "registry_models": self.registry.list_models(),
            "configured": self.list_configured(),
            "engine": "syrion",
        }

    def select_model(self, model_id: str) -> str:
        """Wechselt aktives SYRION Modell."""
        self.sync_registry()
        if model_id not in self.registry.list_models():
            # Versuche, als SYRION Modell zu registrieren
            self.registry.register(SyrionAdapter(model_id=model_id))
        return self.registry.set_default(model_id)


# Singleton
model_manager = ModelManager()
