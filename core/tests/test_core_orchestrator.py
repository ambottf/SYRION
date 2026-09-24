"""Tests für SYRION Core Orchestrator — Request-ID, Kontext, Modellaufruf, Timeout, Cancellation."""
import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.errors import ModelTimeoutError, ModelUnavailableError
from app.core.memory import MemoryService
from app.core.model_adapter import MockAdapter, ModelRegistry
from app.core.orchestrator import Orchestrator
from app.core.types import ChatRequest


@pytest.mark.asyncio
async def test_request_id_generated():
    mem = MemoryService()
    orch = Orchestrator(memory=mem, registry=ModelRegistry(default_adapter=MockAdapter()))
    req = ChatRequest(message="Hallo SYRION")
    res = await orch.handle(req)
    assert res.request_id.startswith("req_")
    assert req.request_id == res.request_id


@pytest.mark.asyncio
async def test_context_build_and_memory_append():
    mem = MemoryService()
    orch = Orchestrator(memory=mem, registry=ModelRegistry(default_adapter=MockAdapter()))
    req = ChatRequest(message="Test", session_id="sess-123")
    res = await orch.handle(req)
    assert "Echo: Test" in res.content
    # Zweiter Call sollte History haben (Mock berichtet history count)
    req2 = ChatRequest(message="Zweite Frage", session_id="sess-123")
    res2 = await orch.handle(req2)
    # Mock gibt history mit
    assert "history=2" in res2.content  # nach erstem append: 2 msgs (user+assistant)
    await mem.clear("sess-123")


@pytest.mark.asyncio
async def test_model_selection_override():
    mem = MemoryService()
    reg = ModelRegistry(default_adapter=MockAdapter())
    # Zweiter Adapter
    class OtherMock(MockAdapter):
        model_id = "other-mock"

        async def generate(self, request, context):
            return "other response"

    reg.register(OtherMock())
    orch = Orchestrator(memory=mem, registry=reg)
    # Default -> mock-echo
    r1 = await orch.handle(ChatRequest(message="hi"))
    assert r1.model == "mock-echo"
    # Override -> other-mock
    r2 = await orch.handle(ChatRequest(message="hi", model="other-mock"))
    assert r2.model == "other-mock"
    assert r2.content == "other response"


@pytest.mark.asyncio
async def test_unknown_model_returns_502_via_registry():
    mem = MemoryService()
    orch = Orchestrator(memory=mem, registry=ModelRegistry(default_adapter=MockAdapter()))
    with pytest.raises(ModelUnavailableError) as exc:
        await orch.handle(ChatRequest(message="hi", model="does-not-exist"))
    assert "Unknown model" in str(exc.value)


@pytest.mark.asyncio
async def test_timeout_handling():
    mem = MemoryService()

    class SlowMock(MockAdapter):
        model_id = "slow-mock"

        async def generate(self, request, context):
            await asyncio.sleep(2)
            return "slow"

    reg = ModelRegistry(default_adapter=SlowMock())
    orch = Orchestrator(memory=mem, registry=reg)
    with pytest.raises(ModelTimeoutError):
        await orch.handle(ChatRequest(message="hi", timeout_ms=1000))


@pytest.mark.asyncio
async def test_stream_yields_chunks():
    mem = MemoryService()
    orch = Orchestrator(memory=mem, registry=ModelRegistry(default_adapter=MockAdapter()))
    req = ChatRequest(message="stream test", stream=True)
    chunks = []
    async for c in orch.stream(req):
        chunks.append(c)
    assert len(chunks) > 1
    assert "".join(chunks).strip().startswith("[SYRION Mock")


@pytest.mark.asyncio
async def test_cancellation_propagation():
    mem = MemoryService()

    class SlowStreamMock(MockAdapter):
        model_id = "slow-stream"

        async def stream(self, request, context):
            await asyncio.sleep(0.5)
            yield "chunk"

    orch = Orchestrator(memory=mem, registry=ModelRegistry(default_adapter=SlowStreamMock()))
    req = ChatRequest(message="cancel", stream=True, timeout_ms=5000)

    async def consume():
        async for _ in orch.stream(req):
            pass

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
