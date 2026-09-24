"""Tests für Memory, Knowledge, Brain — echte Daten, kein Fake."""
import pathlib
import pytest

from app.memory.store import MemoryStore, MemoryStatus
from app.knowledge.store import KnowledgeBase
from app.brain.store import BrainStore


def test_memory_add_and_dedupe(tmp_path: pathlib.Path):
    store = MemoryStore(path=tmp_path / "brain.jsonl")
    e1 = store.add(content="SYRION ist lokal", source="test", tags=["syrion"])
    assert e1.trust_status == MemoryStatus.PENDING.value
    assert e1.content_hash
    # Duplikat
    e2 = store.add(content="SYRION ist lokal", source="test2", tags=["syrion"])
    assert e2.id == e1.id  # deduped
    assert store.counts()["total"] == 1
    # Neue Info mit gleicher Tag -> Beziehung
    e3 = store.add(content="SYRION hat ein Brain", source="test", tags=["syrion"])
    assert e3.id != e1.id
    # Beziehungen
    assert e3.id in store.get(e1.id).relations or e1.id in e3.relations


def test_memory_contradiction(tmp_path: pathlib.Path):
    store = MemoryStore(path=tmp_path / "brain2.jsonl")
    e1 = store.add(content="SYRION ist schnell", source="test", tags=["speed"])
    e2 = store.add(content="SYRION ist nicht schnell", source="test", tags=["speed"])
    # Zweiter sollte Widerspruch flag haben
    assert any(h.get("action") == "contradiction_flagged" for h in e2.history)


def test_memory_approve_reject(tmp_path: pathlib.Path):
    store = MemoryStore(path=tmp_path / "brain3.jsonl")
    e = store.add(content="Test Fakt", source="test")
    assert e.trust_status == "PENDING"
    store.approve(e.id)
    assert store.get(e.id).trust_status == "APPROVED"
    e2 = store.add(content="Anderer Fakt", source="test")
    store.reject(e2.id, reason="test")
    assert store.get(e2.id).trust_status == "REJECTED"


def test_knowledge_base_only_approved(tmp_path: pathlib.Path):
    store = MemoryStore(path=tmp_path / "brain4.jsonl")
    e1 = store.add(content="Approved Fakt", source="test")
    e2 = store.add(content="Pending Fakt", source="test")
    store.approve(e1.id)
    kb = KnowledgeBase(store)
    assert kb.count() == 1
    assert kb.get(e1.id) is not None
    assert kb.get(e2.id) is None


def test_brain_snapshot(tmp_path: pathlib.Path):
    store = MemoryStore(path=tmp_path / "brain5.jsonl")
    store.add(content="Fakt 1", source="src1", tags=["a"], url="https://example.com")
    store.add(content="Fakt 2", source="src2", tags=["a", "b"])
    brain = BrainStore(memory=store)
    snap = brain.snapshot()
    assert snap["counts"]["total"] == 2
    assert snap["counts"]["relations"] >= 0
    assert "topics" in snap
    assert "sources" in snap
    assert "growth" in snap
    graph = brain.graph()
    assert "nodes" in graph
    assert "edges" in graph
    assert len(graph["nodes"]) == 2
