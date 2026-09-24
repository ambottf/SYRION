"""Vocabulary — feste Struktur für SYRION Tokenizer.

Kein dynamisches Erweitern zur Laufzeit durch Modell selbst (Leitplanke).
Erweiterung nur via signierten Dataset-Release und neuem Checkpoint.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class SpecialTokens:
    pad: str = "<pad>"
    unk: str = "<unk>"
    bos: str = "<bos>"
    eos: str = "<eos>"
    mask: str = "<mask>"


@dataclass
class Vocabulary:
    """Deterministische Vocab-Struktur, versioniert, speicherbar."""

    tokens: List[str] = field(default_factory=list)
    special: SpecialTokens = field(default_factory=SpecialTokens)
    version: str = "0.1.0"

    def __post_init__(self) -> None:
        # Sicherstellen, dass Special Tokens enthalten sind und eindeutig
        for tok in [self.special.pad, self.special.unk, self.special.bos, self.special.eos, self.special.mask]:
            if tok not in self.tokens:
                self.tokens.append(tok)
        # Deduplizieren unter Erhalt der Reihenfolge
        seen: set[str] = set()
        deduped: List[str] = []
        for t in self.tokens:
            if t not in seen:
                seen.add(t)
                deduped.append(t)
        self.tokens = deduped
        self._stoi: Dict[str, int] = {tok: i for i, tok in enumerate(self.tokens)}
        self._itos: Dict[int, str] = {i: tok for tok, i in self._stoi.items()}

    @property
    def size(self) -> int:
        return len(self.tokens)

    def token_to_id(self, token: str) -> int:
        return self._stoi.get(token, self._stoi[self.special.unk])

    def id_to_token(self, idx: int) -> str:
        return self._itos.get(idx, self.special.unk)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": self.version, "tokens": self.tokens, "special": self.special.__dict__}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Vocabulary:
        data = json.loads(path.read_text(encoding="utf-8"))
        special = SpecialTokens(**data.get("special", {}))
        return cls(tokens=data.get("tokens", []), special=special, version=data.get("version", "0.1.0"))

    @classmethod
    def minimal(cls, extra_tokens: List[str] | None = None) -> Vocabulary:
        """Kleine, testbare Vocab für Unit-Tests (kein großes Training)."""
        base = [
            "hello", "world", "SYRION", "is", "a", "test", ".", ",", "!", "?", "The", "and", "-", ":", ";", "/", "(", ")",
            # Deutsch häufig + System-Prompt Worte
            "Hallo", "Wie", "geht", "es", "dir", "ist", "ein", "eine", "das", "der", "die", "Du", "bist",
            "SYRION", "lokales", "lokale", "System", "lokal", "Intelligence", "Plattform", "Intelligence-Plattform",
            "Brain", "Memory", "Wissen", "Antworte", "antwort", "hilfreich", "präzise", "verweise", "Quellen", "wenn", "vorhanden",
            "ich", "du", "wir", "ihr", "sie", "bin", "bist", "sind", "habe", "hast", "haben",
            "was", "wer", "wo", "wann", "warum", "wie", "gut", "schlecht", "ja", "nein",
            "danke", "bitte", "Hilfe", "Frage", "Antwort", "Thema", "Tag", "heute", "morgen",
            "User", "Assistant", "Chat",
            # Englisch häufig
            "I", "you", "we", "are", "have", "has", "what", "who", "where", "when", "why",
            "good", "bad", "yes", "no", "thanks", "please", "help", "question", "answer",
        ]
        if extra_tokens:
            base.extend(extra_tokens)
        return cls(tokens=base, version="0.1.0-minimal")

    @classmethod
    def from_texts(cls, texts: List[str], *, max_vocab: int = 500, version: str = "0.1.0-auto") -> Vocabulary:
        """Baut Vocab direkt aus Texten (für Training) — vermeidet <unk>."""
        import re

        words: set[str] = set()
        for t in texts:
            # Behalte Groß/Kleinschreibung, aber sammle beides
            words.update(re.findall(r"\w+", t))
            words.update(re.findall(r"\w+", t.lower()))
        # Häufigste / erste
        vocab_list = sorted(words)[:max_vocab]
        # Basis + gelernte
        base = cls.minimal()
        for w in vocab_list:
            if w not in base.tokens:
                base.tokens.append(w)
        # Dedup wird in __post_init__ gemacht, neu erstellen
        return Vocabulary(tokens=base.tokens, version=version)
