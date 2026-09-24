"""Tokenizer Schnittstelle — SYRION.

Kein externes Tokenizer-Modell als Pflicht. Eigene Schnittstelle, damit später
BPE/SentencePiece trainiert werden kann, ohne Core zu ändern.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from ..vocabulary import Vocabulary


@dataclass(frozen=True)
class EncodingResult:
    ids: List[int]
    tokens: List[str]
    attention_mask: List[int]


class SyrionTokenizer(ABC):
    """Abstrakte Tokenizer-Schnittstelle. Jede Implementierung muss deterministisch sein."""

    vocab: Vocabulary

    @abstractmethod
    def encode(self, text: str) -> EncodingResult:
        """Text -> Token-IDs."""

    @abstractmethod
    def decode(self, ids: List[int]) -> str:
        """Token-IDs -> Text."""

    @abstractmethod
    def get_vocab_size(self) -> int:
        pass

    def batch_encode(self, texts: List[str]) -> List[EncodingResult]:
        return [self.encode(t) for t in texts]
