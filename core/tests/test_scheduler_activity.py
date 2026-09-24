"""Tests für Scheduler und Activity Stream."""
import pathlib
import pytest

from app.scheduler.engine import Scheduler
from app.activity.stream import ActivityStream


@pytest.mark.asyncio
async def test_scheduler_add_pause_resume():
    sched = Scheduler(max_parallel=2, log_path=pathlib.Path("/tmp/test_sched.jsonl"))
    task = sched.add(topic="SYRION", urls=["https://example.com"], interval_s=60, priority=5)
    assert task.topic == "SYRION"
    assert sched.counts()["total"] == 1
    sched.pause()
    assert sched.status == "paused"
    sched.resume()
    assert sched.status == "running"
    sched.stop()
    assert sched.status == "stopped"


@pytest.mark.asyncio
async def test_scheduler_run_and_error_handling(tmp_path: pathlib.Path):
    log_path = tmp_path / "sched.log"
    sched = Scheduler(max_parallel=1, log_path=log_path)
    sched.start()

    async def ok_handler(task):
        return {"ok": True}

    task = sched.add(topic="test", urls=["https://example.com"], interval_s=0)  # sofort fällig
    await sched.tick(ok_handler)
    # Warte kurz für Hintergrund-Task
    import asyncio

    await asyncio.sleep(0.2)
    assert task.run_count >= 1
    assert task.status == "done"

    # Fehler-Handler: 3 Fehler -> disabled
    async def fail_handler(task):
        raise RuntimeError("fail")

    task2 = sched.add(topic="fail", urls=["https://example.com"], interval_s=0)
    for _ in range(3):
        await sched.tick(fail_handler)
        await asyncio.sleep(0.2)
    # Nach 3 Fehlern disabled
    assert task2.error_count == 3
    assert task2.enabled is False


@pytest.mark.asyncio
async def test_scheduler_timeout(tmp_path: pathlib.Path):
    sched = Scheduler(max_parallel=1, log_path=tmp_path / "sched2.log")
    sched.start()

    async def slow_handler(task):
        import asyncio

        await asyncio.sleep(2)
        return {"ok": True}

    task = sched.add(topic="slow", urls=["https://example.com"], interval_s=0, timeout_s=0.1)
    await sched.tick(slow_handler)
    import asyncio

    await asyncio.sleep(0.3)
    assert task.status == "failed"
    assert task.error_count == 1


def test_activity_stream():
    stream = ActivityStream(maxlen=10)
    stream.push("Research gestartet", topic="SYRION")
    stream.push("Quelle gefunden", topic="SYRION")
    recent = stream.recent(5)
    assert len(recent) == 2
    assert recent[0]["message"] == "Research gestartet"
    assert recent[1]["message"] == "Quelle gefunden"


@pytest.mark.asyncio
async def test_activity_subscribe():
    stream = ActivityStream(maxlen=10)
    stream.push("Test 1")
    # Subscribe sollte recent + neue liefern
    gen = stream.subscribe()
    ev1 = await gen.__anext__()
    assert ev1["message"] == "Test 1"
    stream.push("Test 2")
    ev2 = await gen.__anext__()
    assert ev2["message"] == "Test 2"
    await gen.aclose()
