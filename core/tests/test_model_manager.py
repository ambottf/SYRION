"""Tests für ModelManager — SYRION eigenes Modell, kein Ollama."""
import pathlib
import pytest

from app.core.model_adapter import MockAdapter, ModelRegistry
from app.core.model_manager import ModelManager


def test_load_configured(tmp_path: pathlib.Path):
    cfg = tmp_path / "models.yaml"
    cfg.write_text(
        """
version: "0.4.0-syrion"
models:
  syrion_core:
    enabled: true
    provider: syrion
    model_id: "syrion-0.1.0-base"
""",
        encoding="utf-8",
    )
    mm = ModelManager(config_path=cfg, registry=ModelRegistry(default_adapter=MockAdapter()))
    assert mm.get_default_model_id() == "syrion-0.1.0-base"
    assert len(mm.list_configured()) == 1


@pytest.mark.asyncio
async def test_status_ok_with_syrion(tmp_path: pathlib.Path):
    cfg = tmp_path / "models.yaml"
    cfg.write_text(
        """
version: "0.4.0-syrion"
models:
  syrion_core:
    enabled: true
    provider: syrion
    model_id: "syrion-0.1.0-base"
""",
        encoding="utf-8",
    )
    mm = ModelManager(config_path=cfg, registry=ModelRegistry())
    status = await mm.get_status()
    # SYRION Basis ist immer lokal verfügbar (kein Ollama nötig)
    assert status["state"] in ("ok", "degraded")
    assert status["reachable"] is True
    assert "syrion" in status["active_model"].lower() or "SYRION" in status["message"]
    assert "resources" in status


def test_select_model_switches_registry(tmp_path: pathlib.Path):
    cfg = tmp_path / "models.yaml"
    cfg.write_text('version: "0.4"\nmodels: {}\n', encoding="utf-8")
    reg = ModelRegistry(default_adapter=MockAdapter())
    mm = ModelManager(config_path=cfg, registry=reg)
    mm.select_model("syrion-0.2.0-test")
    assert reg.default_model_id() == "syrion-0.2.0-test"
    assert "syrion-0.2.0-test" in reg.list_models()


@pytest.mark.asyncio
async def test_models_api_status(monkeypatch, tmp_path: pathlib.Path):
    from fastapi.testclient import TestClient

    from app.gateway.main import app

    client = TestClient(app)
    r = client.get("/api/v1/models/status")
    assert r.status_code == 200
    j = r.json()
    assert "state" in j
    assert "active_model" in j
    assert j["state"] in ("ok", "degraded", "unavailable")
    assert "engine" in j
    assert j["engine"] == "syrion"


def test_models_api_select():
    from fastapi.testclient import TestClient

    from app.gateway.main import app

    client = TestClient(app)
    r = client.post("/api/v1/models/select", json={"model_id": "syrion-0.1.0-base"})
    assert r.status_code == 200
    assert "syrion" in r.json()["active"]
