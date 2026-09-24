"""Reale Tests für Phase-0 Audit-Log Stub — kein Platzhalter."""
import json
from pathlib import Path

from app.audit.audit_log import append, verify_chain


def test_append_and_verify_chain(tmp_path: Path, monkeypatch):
    # Audit-Pfad auf temp umleiten (isoliert, kein Einfluss auf data/audit/audit.log)
    audit_file = tmp_path / "audit.log"
    monkeypatch.setenv("AUDIT_LOG_PATH", str(audit_file))
    # Modul neu laden damit AUDIT_PATH neu ausgewertet wird
    import app.audit.audit_log as mod
    import importlib

    importlib.reload(mod)
    mod.AUDIT_PATH = audit_file

    e1 = mod.append(actor="system", action="test.start", payload={"phase": "0"})
    e2 = mod.append(actor="user", action="test.next", payload={"n": 1})

    assert audit_file.exists()
    lines = audit_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

    j1 = json.loads(lines[0])
    j2 = json.loads(lines[1])
    assert j1["entry_hash"] != j2["entry_hash"]
    assert j2["prev_hash"] == j1["entry_hash"]

    assert mod.verify_chain(audit_file) is True

    # Manipulation erkennen
    tampered = json.loads(lines[1])
    tampered["action"] = "tampered"
    audit_file.write_text(lines[0] + "\n" + json.dumps(tampered, ensure_ascii=False) + "\n", encoding="utf-8")
    assert mod.verify_chain(audit_file) is False


def test_empty_chain_is_valid(tmp_path: Path):
    from app.audit.audit_log import verify_chain

    empty = tmp_path / "empty.log"
    # Existiert nicht -> gilt als valide
    assert verify_chain(empty) is True
    empty.write_text("", encoding="utf-8")
    assert verify_chain(empty) is True
