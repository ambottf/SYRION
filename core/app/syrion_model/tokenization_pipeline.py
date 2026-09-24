"""Tokenization Pipeline — SYRION Text → Token-IDs, mit Batching-Vorbereitung."""
from __future__ import annotations

from typing import List, Dict, Any
from .tokenizer.simple import SimpleTokenizer
from .vocabulary import Vocabulary


class TokenizationPipeline:
    def __init__(self, tokenizer: SimpleTokenizer) -> None:
        self.tokenizer = tokenizer

    def tokenize(self, texts: List[str], *, max_length: int = 128, truncation: bool = True, padding: bool = False) -> List[Dict[str, Any]]:
        """Wandelt Texte in Token-IDs um, mit Truncation."""
        out: List[Dict[str, Any]] = []
        for text in texts:
            enc = self.tokenizer.encode(text)
            ids = enc.ids
            if truncation and len(ids) > max_length:
                ids = ids[:max_length]
            # Für Training: Input = ids[:-1], Target = ids[1:]
            # Wir speichern beides
            out.append({"input_ids": ids, "attention_mask": [1] * len(ids), "raw": text})
        return out

    def build_vocab_from_texts(self, texts: List[str], *, max_vocab: int = 500) -> Vocabulary:
        """Baut minimale Vocab aus Texten (für kleine Tests)."""
        # Sammle alle Worte
        words: set[str] = set()
        for t in texts:
            # Einfache Wort-Sammlung
            import re

            words.update(re.findall(r"\w+", t.lower()))
        # Häufigste Worte (hier einfach erste)
        vocab_list = sorted(words)[:max_vocab]
        # Füge Basis hinzu
        base = Vocabulary.minimal()
        # Erweitere
        for w in vocab_list:
            if w not in base.tokens:
                base.tokens.append(w)
        # Neu initialisieren
        return Vocabulary(tokens=base.tokens, version="0.1.0-pipeline")
