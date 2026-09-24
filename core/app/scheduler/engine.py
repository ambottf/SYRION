"""24/7 Scheduler — kontrolliert, mit Ressourcenlimits, Pause/Stop, Fehlerbehandlung."""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional, Callable, Awaitable
import json
from pathlib import Path


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class ScheduledTask:
    id: str
    topic: str
    urls: List[str]
    interval_s: int  # Sekunden zwischen Läufen
    priority: int = 5  # 1-10
    max_parallel: int = 2
    timeout_s: float = 30.0
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_run: str | None = None
    run_count: int = 0
    error_count: int = 0
    status: str = TaskStatus.PENDING.value

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SchedulerStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class Scheduler:
    """Kontrollierter Scheduler — max_parallel, Timeout, Pause/Stop, Logging, persistent."""

    def __init__(self, *, max_parallel: int = 3, log_path: Path | str = "logs/scheduler.jsonl", state_path: Path | str | None = None) -> None:
        self.max_parallel = max_parallel
        self.log_path = Path(log_path)
        # Absoluter Pfad für Persistenz (unabhängig von cwd)
        if not self.log_path.is_absolute():
            self.log_path = Path(__file__).resolve().parents[3] / self.log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        # State Pfad
        if state_path is None:
            state_path = Path(__file__).resolve().parents[3] / "data" / "scheduler" / "schedule.json"
        else:
            state_path = Path(state_path)
            if not state_path.is_absolute():
                state_path = Path(__file__).resolve().parents[3] / state_path
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.tasks: Dict[str, ScheduledTask] = {}
        self.status = SchedulerStatus.STOPPED.value
        self._sem = asyncio.Semaphore(max_parallel)
        self._running: Dict[str, asyncio.Task] = {}
        self._paused = False
        self._load_state()

    def _save_state(self) -> None:
        try:
            data = {"tasks": [t.to_dict() for t in self.tasks.values()], "status": self.status, "paused": self._paused}
            tmp = self.state_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.state_path)
        except Exception:
            pass

    def _load_state(self) -> None:
        if not self.state_path.exists():
            return
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            for td in data.get("tasks", []):
                # Rekonstruiere ScheduledTask
                task = ScheduledTask(
                    id=td["id"],
                    topic=td["topic"],
                    urls=td.get("urls", []),
                    interval_s=td.get("interval_s", 3600),
                    priority=td.get("priority", 5),
                    max_parallel=td.get("max_parallel", 2),
                    timeout_s=td.get("timeout_s", 30.0),
                    enabled=td.get("enabled", True),
                    tags=td.get("tags", []),
                    created_at=td.get("created_at", datetime.now(timezone.utc).isoformat()),
                    last_run=td.get("last_run"),
                    run_count=td.get("run_count", 0),
                    error_count=td.get("error_count", 0),
                    status=td.get("status", TaskStatus.PENDING.value),
                )
                self.tasks[task.id] = task
            self.status = data.get("status", SchedulerStatus.STOPPED.value)
            self._paused = data.get("paused", False)
        except Exception:
            pass

    def _log(self, event: str, task: ScheduledTask | None = None, **extra: Any) -> None:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "task_id": task.id if task else None,
            "topic": task.topic if task else None,
            **extra,
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def add(self, *, topic: str, urls: List[str], interval_s: int, priority: int = 5, tags: List[str] | None = None, timeout_s: float = 30.0) -> ScheduledTask:
        tid = f"sched_{uuid.uuid4().hex[:8]}"
        task = ScheduledTask(id=tid, topic=topic, urls=urls, interval_s=interval_s, priority=priority, tags=tags or [], timeout_s=timeout_s)
        self.tasks[tid] = task
        self._log("task.added", task)
        self._save_state()
        return task

    def remove(self, task_id: str) -> None:
        if task_id in self.tasks:
            self._log("task.removed", self.tasks[task_id])
            del self.tasks[task_id]
            if task_id in self._running:
                self._running[task_id].cancel()
            self._save_state()

    def pause(self) -> None:
        self._paused = True
        self.status = SchedulerStatus.PAUSED.value
        self._log("scheduler.paused")
        self._save_state()

    def resume(self) -> None:
        self._paused = False
        self.status = SchedulerStatus.RUNNING.value
        self._log("scheduler.resumed")
        self._save_state()

    def stop(self) -> None:
        self._paused = True
        self.status = SchedulerStatus.STOPPED.value
        for t in list(self._running.values()):
            t.cancel()
        self._log("scheduler.stopped")
        self._save_state()

    def start(self) -> None:
        if self.status == SchedulerStatus.RUNNING.value:
            return
        self._paused = False
        self.status = SchedulerStatus.RUNNING.value
        self._log("scheduler.started")
        self._save_state()

    async def _run_one(self, task: ScheduledTask, handler: Callable[[ScheduledTask], Awaitable[Dict[str, Any]]]) -> None:
        async with self._sem:
            if self._paused or not task.enabled:
                return
            task.status = TaskStatus.RUNNING.value
            self._save_state()
            try:
                # Retry mit Backoff (max 2 Retries)
                last_exc: Exception | None = None
                for attempt in range(3):
                    try:
                        result = await asyncio.wait_for(handler(task), timeout=task.timeout_s)
                        task.last_run = datetime.now(timezone.utc).isoformat()
                        task.run_count += 1
                        task.error_count = 0
                        task.status = TaskStatus.DONE.value
                        self._log("task.done", task, result=result)
                        self._save_state()
                        return
                    except asyncio.TimeoutError as e:
                        last_exc = e
                        if attempt < 2:
                            await asyncio.sleep(2**attempt)  # Backoff
                            continue
                        raise
                    except Exception as e:
                        last_exc = e
                        if attempt < 2 and "rate limit" not in str(e).lower():
                            await asyncio.sleep(2**attempt)
                            continue
                        raise
            except asyncio.TimeoutError:
                task.error_count += 1
                task.status = TaskStatus.FAILED.value
                self._log("task.timeout", task, timeout=task.timeout_s)
                if task.error_count >= 3:
                    task.enabled = False
                    self._log("task.disabled_after_failures", task)
                self._save_state()
            except asyncio.CancelledError:
                task.status = TaskStatus.PAUSED.value
                self._log("task.cancelled", task)
                self._save_state()
            except Exception as e:
                task.error_count += 1
                task.status = TaskStatus.FAILED.value
                self._log("task.failed", task, error=str(e)[:500])
                if task.error_count >= 3:
                    task.enabled = False
                    self._log("task.disabled_after_failures", task)
                self._save_state()

    async def tick(self, handler: Callable[[ScheduledTask], Awaitable[Dict[str, Any]]]) -> None:
        """Ein Tick: führt fällige Tasks aus (für Tests und echten Loop)."""
        if self._paused or self.status != SchedulerStatus.RUNNING.value:
            return
        now = datetime.now(timezone.utc)
        for task in sorted(self.tasks.values(), key=lambda t: t.priority):
            if not task.enabled:
                continue
            # Fällig wenn nie gelaufen oder Interval abgelaufen
            if task.last_run is None:
                due = True
            else:
                last = datetime.fromisoformat(task.last_run)
                due = (now - last).total_seconds() >= task.interval_s
            if due:
                # Starte Task als Hintergrund, respektiere max_parallel via _sem
                if task.id not in self._running or self._running[task.id].done():
                    self._running[task.id] = asyncio.create_task(self._run_one(task, handler))

    def list(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self.tasks.values()]

    def get(self, task_id: str) -> Dict[str, Any] | None:
        t = self.tasks.get(task_id)
        return t.to_dict() if t else None

    def counts(self) -> Dict[str, Any]:
        return {
            "total": len(self.tasks),
            "running": len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING.value]),
            "enabled": len([t for t in self.tasks.values() if t.enabled]),
            "paused": self._paused,
            "status": self.status,
        }
