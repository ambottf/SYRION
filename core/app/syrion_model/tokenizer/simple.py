"""SimpleTokenizer — minimale, testbare Implementierung (Whitespace + Vocab Lookup).

Kein BPE-Training hier — nur Grundlage, damit Inference/Training pipelined testen kann.
Später ersetzbar durch SyrionBpeTokenizer ohne API-Bruch.
"""
from __future__ import annotations

import re
from typing import List

from ..vocabulary import Vocabulary
from .base import EncodingResult, SyrionTokenizer


class SimpleTokenizer(SyrionTokenizer):
    def __init__(self, vocab: Vocabulary) -> None:
        self.vocab = vocab

    def encode(self, text: str) -> EncodingResult:
        # Behandle SYRION Special Tokens als Einheiten: <|system|>, <|user|>, <|assistant|>, <|end|>
        # Ersetze sie temporär durch Platzhalter die im Vocab sind
        specials = ["<|system|>", "<|user|>", "<|assistant|>", "<|end|>"]
        # Sammle welche Specials im Text vorkommen
        found_specials: List[str] = []
        for s in specials:
            if s in text:
                found_specials.append(s)
        # Ersetze Specials durch eindeutige Marker die dann als Token erkannt werden
        # Wir nutzen die Specials selbst als Tokens wenn sie im Vocab sind, sonst als <unk> nicht
        # Daher: splitte Text an Specials und behandle sie separat
        # Erstelle Liste von Segmenten
        import re as _re

        # Pattern für Specials
        special_pat = r"(<\|system\|>|<\|user\|>|<\|assistant\|>|<\|end\|>)"
        parts = _re.split(special_pat, text)
        raw_tokens: List[str] = []
        for part in parts:
            if part in specials:
                raw_tokens.append(part)
            elif part:
                raw_tokens.extend(_re.findall(r"\w+|[^\w\s]", part, flags=_re.UNICODE))

        tokens: List[str] = []
        ids: List[int] = []
        for tok in raw_tokens:
            if tok in self.vocab.tokens:
                tokens.append(tok)
                ids.append(self.vocab.token_to_id(tok))
                continue
            lower = tok.lower()
            cap = tok.capitalize()
            if lower in self.vocab.tokens:
                tokens.append(lower)
                ids.append(self.vocab.token_to_id(lower))
                continue
            if cap in self.vocab.tokens:
                tokens.append(cap)
                ids.append(self.vocab.token_to_id(cap))
                continue
            tokens.append(self.vocab.special.unk)
            ids.append(self.vocab.token_to_id(self.vocab.special.unk))
        attention_mask = [1] * len(ids)
        return EncodingResult(ids=ids, tokens=tokens, attention_mask=attention_mask)

    def decode(self, ids: List[int]) -> str:
        tokens = [self.vocab.id_to_token(i) for i in ids]
        # Filter Special Tokens außer unk (für Anzeige)
        filtered = [t for t in tokens if t not in (self.vocab.special.pad, self.vocab.special.bos, self.vocab.special.eos)]
        # Simple detokenize: join mit Leerzeichen, Satzzeichen ohne Leerzeichen davor
        text = " ".join(filtered)
        text = re.sub(r"\s+([.,!?;:])", r"\1", text)
        return text

    def get_vocab_size(self) -> int:
        return self.vocab.size
