"""Tests für Model-Adapter Abstraktion (SYRION eigenes Modell, kein Ollama)."""
import pytest

from app.core.model_adapter import MockAdapter, ModelRegistry, SyrionAdapter
from app.core.types import ChatRequest, MemoryContext


@pytest.mark.asyncio
async def test_mock_generate_and_stream():
    adapter = MockAdapter()
    req = ChatRequest(message="hello")
    ctx = MemoryContext()
    txt = await adapter.generate(req, ctx)
    assert "Echo: hello" in txt
    chunks = [c async for c in adapter.stream(req, ctx)]
    assert "".join(chunks).strip() == txt


@pytest.mark.asyncio
async def test_syrion_adapter_generate():
    adapter = SyrionAdapter(model_id="syrion-0.1.0-base")
    req = ChatRequest(message="hello")
    ctx = MemoryContext()
    txt = await adapter.generate(req, ctx)
    # SYRION eigenes Modell generiert deterministisch, nicht Mock
    assert isinstance(txt, str)
    assert len(txt) > 0
    # Health sollte true sein (lokal, kein Ollama nötig)
    assert await adapter.health() is True


def test_registry_resolve():
    reg = ModelRegistry(default_adapter=MockAdapter())
    assert reg.default_model_id() == "mock-echo"
    assert "mock-echo" in reg.list_models()
    req = ChatRequest(message="hi")
    assert reg.resolve(req).model_id == "mock-echo"
    req2 = ChatRequest(message="hi", model="mock-echo")
    assert reg.resolve(req2).model_id == "mock-echo"


def test_syrion_registry():
    reg = ModelRegistry()
    # Default ist jetzt SYRION, nicht Mock
    assert reg.default_model_id().startswith("syrion-")
    assert "syrion-0.1.0-base" in reg.list_models()
