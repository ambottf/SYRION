"""Dataset Validator — prüft SYRION Trainingsdaten vor dem Training."""
from __future__ import annotations

from typing import Dict, Any, List


def validate_entry(entry: Dict[str, Any]) -> bool:
    """Prüft einzelnen Eintrag auf Pflichtfelder und Qualität."""
    text = entry.get("text") or entry.get("content") or ""
    if not isinstance(text, str) or len(text.strip()) < 10:
        return False
    # Kein Systembefehl, kein Code der ausgeführt werden könnte (einfach)
    lower = text.lower()
    forbidden = ["<script", "rm -rf", "drop table", "system("]
    for pat in forbidden:
        if pat in lower:
            return False
    # Quelle sollte vorhanden sein (für Provenienz)
    if not entry.get("source"):
        # Quelle ist optional, aber wir warnen nicht, wir akzeptieren
        pass
    return True


def validate_dataset(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validiert gesamten Datensatz, gibt Report zurück."""
    total = len(entries)
    valid = sum(1 for e in entries if validate_entry(e))
    invalid = total - valid
    # Dedupe Check (einfach via Text)
    texts = [e.get("text", "") for e in entries]
    unique = len(set(texts))
    dupes = total - unique
    return {
        "total": total,
        "valid": valid,
        "invalid": invalid,
        "unique": unique,
        "duplicates": dupes,
        "valid_ratio": valid / total if total else 0,
        "is_ok": valid >= 5 and valid / total >= 0.8,  # Mindestens 5 valide, 80% ok
    }
