"""
SYRION Security — PolicyEngine Stub (Phase 0)
- Lädt SecurityPolicy.yaml READ-ONLY beim Start
- Keine Schreibmethoden, keine Self-Modifikation
- check() ist Stub und verweigert schreibende Scopes in Phase 0
- Immutability: Datei wird nach Laden nicht erneut geschrieben
SYRION_ARCHITEKTUR.md Kap. 6, 7
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

POLICY_PATH = Path(os.getenv("SECURITY_POLICY_PATH", "config/SecurityPolicy.yaml"))

class PolicyEngine:
    """Read-only Stub. Keine Geschäftslogik."""

    def __init__(self, policy_path: Path | None = None) -> None:
        self.policy_path = Path(policy_path) if policy_path else POLICY_PATH
        self.policy: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if not self.policy_path.exists():
            # In Phase 0: leeres Policy-Objekt, Gateway meldet degraded
            self.policy = {"immutable": True, "roles": {}, "immutable_rules": {}}
            return
        with self.policy_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        # Schutz: immutable Flag darf nicht zur Laufzeit überschrieben werden
        self.policy = data

    def is_immutable(self) -> bool:
        return bool(self.policy.get("immutable", True))

    def get_version(self) -> str:
        return str(self.policy.get("policy_version", "unknown"))

    def check(self, actor_role: str, scope: str) -> bool:
        """
        Stub-Entscheidung: Nur lesende Scopes für health/config in Phase 0 erlaubt.
        Schreibende Scopes immer deny — Freigabesystem noch nicht implementiert.
        """
        if scope in ("system:health:read", "system:config:read"):
            return True
        # In Phase 0: Default deny für alles andere (SYRION_ARCHITEKTUR.md:7 default_policy deny)
        return False

    # Explizit KEINE Methoden wie save(), update_policy(), escalate(), modify_model()

# Singleton für Gateway
engine = PolicyEngine()
