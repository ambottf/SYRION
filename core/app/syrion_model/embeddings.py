"""Embeddings — Schnittstelle für SYRION Modell.

Eigene Embeddings, nicht von externem Anbieter. Für Test deterministisch mit
kleiner Matrix (kein großes Training). Später durch gelernte Gewichte ersetzbar.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List
import random
import math


@dataclass
class EmbeddingConfig:
    vocab_size: int
    d_model: int = 64  # klein für Tests, später 512/768/1024
    max_seq_len: int = 512
    dropout: float = 0.1


class SyrionEmbeddings:
    """Deterministische Embeddings für Tests — kein Training hier."""

    def __init__(self, config: EmbeddingConfig, seed: int = 42) -> None:
        self.config = config
        rnd = random.Random(seed)
        # Kleine, deterministische Matrix vocab_size x d_model
        self.weight: List[List[float]] = [
            [rnd.uniform(-0.5, 0.5) for _ in range(config.d_model)] for _ in range(config.vocab_size)
        ]
        # Positional (sinusoidal, deterministisch)
        self.pos_encoding: List[List[float]] = [
            [math.sin(pos / (10000 ** (2 * (i // 2) / config.d_model))) if i % 2 == 0 else math.cos(pos / (10000 ** (2 * (i // 2) / config.d_model))) for i in range(config.d_model)]
            for pos in range(config.max_seq_len)
        ]

    def lookup(self, token_ids: List[int]) -> List[List[float]]:
        """Token-IDs -> Embeddings (seq_len x d_model)."""
        seq = []
        for idx, tid in enumerate(token_ids):
            tok_emb = self.weight[tid % self.config.vocab_size]
            pos_emb = self.pos_encoding[idx % self.config.max_seq_len]
            # Add
            seq.append([t + p for t, p in zip(tok_emb, pos_emb)])
        return seq

    def get_config(self) -> EmbeddingConfig:
        return self.config
