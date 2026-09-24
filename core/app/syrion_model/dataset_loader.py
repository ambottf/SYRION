"""Dataset Loader — lädt SYRION Trainingsdaten lokal, kein Download riesiger Datensätze."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any

from .text_cleaning import clean_text, is_valid_for_training
from .dataset_validator import validate_entry


class DatasetLoader:
    """Lädt JSONL/JSON Dateien oder Dict-Listen, bereinigt und validiert."""

    def __init__(self, *, min_len: int = 20, max_len: int = 2000) -> None:
        self.min_len = min_len
        self.max_len = max_len

    def load_from_file(self, path: Path | str) -> List[Dict[str, Any]]:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset {path} nicht gefunden")
        entries: List[Dict[str, Any]] = []
        if path.suffix == ".jsonl":
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    # Erwarte {"text": "...", "source": "..."} oder {"content": "..."}
                    text = obj.get("text") or obj.get("content") or ""
                    cleaned = clean_text(text)
                    if not is_valid_for_training(cleaned, min_len=self.min_len, max_len=self.max_len):
                        continue
                    if not validate_entry({"text": cleaned, "source": obj.get("source", "file")}):
                        continue
                    entries.append({"text": cleaned, "source": obj.get("source", str(path)), "id": obj.get("id")})
                except Exception:
                    continue
        elif path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            # Erwarte {"entries": [{"text": ...}]} oder Liste
            raw = data.get("entries") if isinstance(data, dict) else data
            if isinstance(raw, list):
                for obj in raw:
                    if isinstance(obj, dict):
                        text = obj.get("text") or obj.get("content") or ""
                        cleaned = clean_text(text)
                        if is_valid_for_training(cleaned, min_len=self.min_len, max_len=self.max_len) and validate_entry({"text": cleaned}):
                            entries.append({"text": cleaned, "source": obj.get("source", str(path))})
        else:
            raise ValueError(f"Unbekanntes Format {path.suffix}, erwartet .jsonl/.json")
        return entries

    def load_from_list(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Für Tests: direkt aus Liste, kein File."""
        out: List[Dict[str, Any]] = []
        for obj in data:
            text = obj.get("text") or obj.get("content") or ""
            cleaned = clean_text(text)
            if is_valid_for_training(cleaned, min_len=self.min_len, max_len=self.max_len) and validate_entry({"text": cleaned}):
                out.append({"text": cleaned, "source": obj.get("source", "manual"), "id": obj.get("id")})
        return out

    def load_small_test_dataset(self) -> List[Dict[str, Any]]:
        """Kleiner, fester Testdatensatz (kein Download, 20 Beispiele)."""
        samples = [
            {"text": "SYRION ist ein lokales Intelligence-System.", "source": "test"},
            {"text": "SYRION hat ein Brain mit Memory und Knowledge Graph.", "source": "test"},
            {"text": "Das Brain visualisiert Wissen als Knoten und Beziehungen.", "source": "test"},
            {"text": "Memory speichert Fakten mit Quelle und Zeitstempel.", "source": "test"},
            {"text": "Research sammelt Informationen aus dem Internet kontrolliert.", "source": "test"},
            {"text": "Der Scheduler führt 24/7 Rechercheaufgaben aus.", "source": "test"},
            {"text": "SYRION lernt kontinuierlich aus freigegebenem Wissen.", "source": "test"},
            {"text": "Wissen wird als PENDING gespeichert und geprüft.", "source": "test"},
            {"text": "Nach Freigabe wird Wissen in die Knowledge Base übernommen.", "source": "test"},
            {"text": "Der Knowledge Graph verbindet Fakten über Beziehungen.", "source": "test"},
            {"text": "SYRION ist lokal-first und offline-fähig.", "source": "test"},
            {"text": "Sicherheit: SYRION verändert keine eigenen Sicherheitsregeln.", "source": "test"},
            {"text": "Das Modell wird lokal trainiert, kein Cloud-API.", "source": "test"},
            {"text": "Tokenizer wandelt Text in Token-IDs um.", "source": "test"},
            {"text": "Embeddings sind Vektoren für Tokens.", "source": "test"},
            {"text": "Der Transformer lernt Muster in Daten.", "source": "test"},
            {"text": "Training nutzt kleine Batches und validiert regelmäßig.", "source": "test"},
            {"text": "Checkpoints speichern Modellgewichte versioniert.", "source": "test"},
            {"text": "Evaluation misst Perplexity und Accuracy.", "source": "test"},
            {"text": "Inference generiert Antworten aus dem Modell.", "source": "test"},
        ]
        return self.load_from_list(samples)
