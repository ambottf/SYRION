"""Transformer — Schnittstelle für SYRION Neural Network.

Kein großes Training hier — nur Architektur, damit später kontrolliert trainiert werden kann.
Eigene SYRION-Transformer-Blöcke, nicht von externem LLM kopiert.

Für Tests: winzige, deterministische Forward-Pässe (keine GPU Pflicht).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List
import math
import random


@dataclass(frozen=True)
class TransformerConfig:
    d_model: int = 64
    n_heads: int = 4
    n_layers: int = 2  # winzig für Tests, später 12/24
    d_ff: int = 128
    vocab_size: int = 1024
    max_seq_len: int = 512
    dropout: float = 0.1


def _softmax(xs: List[float]) -> List[float]:
    m = max(xs)
    exps = [math.exp(x - m) for x in xs]
    s = sum(exps)
    return [e / s for e in exps]


class MultiHeadAttention:
    def __init__(self, config: TransformerConfig, seed: int = 1) -> None:
        self.config = config
        rnd = random.Random(seed)
        d = config.d_model
        # Winzige, deterministische Gewichte
        self.w_q = [[rnd.uniform(-0.1, 0.1) for _ in range(d)] for _ in range(d)]
        self.w_k = [[rnd.uniform(-0.1, 0.1) for _ in range(d)] for _ in range(d)]
        self.w_v = [[rnd.uniform(-0.1, 0.1) for _ in range(d)] for _ in range(d)]
        self.w_o = [[rnd.uniform(-0.1, 0.1) for _ in range(d)] for _ in range(d)]

    def _mat_vec(self, m: List[List[float]], v: List[float]) -> List[float]:
        return [sum(row[j] * v[j] for j in range(len(v))) for row in m]

    def forward(self, x: List[List[float]]) -> List[List[float]]:
        # x: seq_len x d_model -> vereinfachte Attention pro Position (kein KV-Cache hier)
        out = []
        for vec in x:
            q = self._mat_vec(self.w_q, vec)
            k = self._mat_vec(self.w_k, vec)
            v = self._mat_vec(self.w_v, vec)
            # Simplified score: dot(q,k)/sqrt(d)
            score = sum(a * b for a, b in zip(q, k)) / math.sqrt(self.config.d_model)
            # Softmax über single score -> 1.0, aber für Test deterministisch
            attn = _softmax([score])[0]
            # v * attn
            av = [a * attn for a in v]
            o = self._mat_vec(self.w_o, av)
            out.append(o)
        return out


class TransformerBlock:
    def __init__(self, config: TransformerConfig, seed: int = 1) -> None:
        self.attn = MultiHeadAttention(config, seed=seed)
        self.config = config
        rnd = random.Random(seed + 1)
        d = config.d_model
        self.w1 = [[rnd.uniform(-0.1, 0.1) for _ in range(d)] for _ in range(config.d_ff)]
        self.w2 = [[rnd.uniform(-0.1, 0.1) for _ in range(config.d_ff)] for _ in range(d)]
        self.b1 = [0.0] * config.d_ff
        self.b2 = [0.0] * d

    def forward(self, x: List[List[float]]) -> List[List[float]]:
        # Attention
        a = self.attn.forward(x)
        # Residual + FFN (vereinfacht, keine LayerNorm für Test-Kürze)
        out = []
        for i, vec in enumerate(a):
            # FFN
            hidden = [sum(vec[j] * self.w1[r][j] for j in range(len(vec))) + self.b1[r] for r in range(self.config.d_ff)]
            hidden = [max(0, h) for h in hidden]  # ReLU
            out_vec = [sum(hidden[r] * self.w2[j][r] for r in range(self.config.d_ff)) + self.b2[j] for j in range(self.config.d_model)]
            # Residual
            out_vec = [out_vec[j] + vec[j] for j in range(len(vec))]
            out.append(out_vec)
        return out


class SyrionTransformer:
    """Stack aus Blöcken — deterministisch, testbar."""

    def __init__(self, config: TransformerConfig) -> None:
        self.config = config
        self.blocks = [TransformerBlock(config, seed=i * 10) for i in range(config.n_layers)]

    def forward(self, embeddings: List[List[float]]) -> List[List[float]]:
        x = embeddings
        for blk in self.blocks:
            x = blk.forward(x)
        return x

    def get_config(self) -> TransformerConfig:
        return self.config
