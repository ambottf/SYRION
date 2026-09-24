"""Reale Tests für Phase-0 PolicyEngine Stub."""
from pathlib import Path

from app.security.policy_engine import PolicyEngine


def test_policy_immutable_and_version(tmp_path: Path):
    p = tmp_path / "SecurityPolicy.yaml"
    p.write_text(
        """
policy_version: "9.9.9-test"
immutable: true
""",
        encoding="utf-8",
    )
    eng = PolicyEngine(policy_path=p)
    assert eng.is_immutable() is True
    assert eng.get_version() == "9.9.9-test"


def test_policy_check_stub_allows_only_health(tmp_path: Path):
    p = tmp_path / "SecurityPolicy.yaml"
    p.write_text('policy_version: "0.1"\nimmutable: true\n', encoding="utf-8")
    eng = PolicyEngine(policy_path=p)
    assert eng.check("user", "system:health:read") is True
    assert eng.check("user", "system:config:read") is True
    # Schreibende Scopes in Phase 0 immer deny
    assert eng.check("user", "tool:web_search") is False
    assert eng.check("agent_background", "memory:write:quarantine") is False


def test_missing_policy_defaults(tmp_path: Path):
    missing = tmp_path / "does-not-exist.yaml"
    eng = PolicyEngine(policy_path=missing)
    assert eng.get_version() == "unknown"
    assert eng.is_immutable() is True
