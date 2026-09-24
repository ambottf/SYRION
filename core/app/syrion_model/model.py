"""SYRION Model — eigene Modell-Architektur (kein externes LLM als Kern).

Kombiniert Vocab/Tokenizer/Embeddings/Transformer zu einem end-to-end Modell.
Gewichte sind hier deterministisch klein und nicht trainiert — das eigentliche
Training erfolgt später über die Training-Pipeline mit versionierten Datasets
und Checkpoints. Kein Self-Modifying zur Laufzeit.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List
import random
import math

from .embeddings import EmbeddingConfig, SyrionEmbeddings
from .tokenizer.base import SyrionTokenizer
from .transformer import SyrionTransformer, TransformerConfig
from .vocabulary import Vocabulary


@dataclass(frozen=True)
class SyrionModelConfig:
    vocab_size: int
    d_model: int = 64
    n_layers: int = 2
    n_heads: int = 4
    d_ff: int = 128
    max_seq_len: int = 512
    version: str = "0.1.0-syrion-base"


class SyrionModel:
    """Eigenes SYRION Modell — inferenzfähig, aber noch nicht groß trainiert."""

    def __init__(self, config: SyrionModelConfig, vocab: Vocabulary, tokenizer: SyrionTokenizer) -> None:
        self.config = config
        self.vocab = vocab
        self.tokenizer = tokenizer
        emb_cfg = EmbeddingConfig(vocab_size=config.vocab_size, d_model=config.d_model, max_seq_len=config.max_seq_len)
        self.embeddings = SyrionEmbeddings(emb_cfg)
        trans_cfg = TransformerConfig(d_model=config.d_model, n_heads=config.n_heads, n_layers=config.n_layers, d_ff=config.d_ff, vocab_size=config.vocab_size, max_seq_len=config.max_seq_len)
        self.transformer = SyrionTransformer(trans_cfg)
        # Output head: d_model -> vocab_size (deterministisch)
        rnd = random.Random(42)
        self.lm_head = [[rnd.uniform(-0.1, 0.1) for _ in range(config.d_model)] for _ in range(config.vocab_size)]

    def _logits(self, hidden: List[float]) -> List[float]:
        # hidden: d_model -> logits: vocab_size
        return [sum(hidden[j] * self.lm_head[i][j] for j in range(self.config.d_model)) for i in range(self.config.vocab_size)]

    def forward(self, token_ids: List[int]) -> List[List[float]]:
        """Token-IDs -> Logits pro Position (seq_len x vocab_size)."""
        emb = self.embeddings.lookup(token_ids)
        hidden_seq = self.transformer.forward(emb)
        return [self._logits(h) for h in hidden_seq]

    def _mask_special(self, logits: List[float]) -> List[float]:
        """Maskiert <unk>, <pad>, <mask>, <bos> damit sie nie generiert werden (nur <eos> darf stoppen)."""
        masked = logits.copy()
        for tok in [self.vocab.special.unk, self.vocab.special.pad, self.vocab.special.mask, self.vocab.special.bos]:
            try:
                idx = self.vocab.token_to_id(tok)
                if 0 <= idx < len(masked):
                    masked[idx] = float("-inf")
            except Exception:
                pass
        return masked

    def generate_next_token(self, token_ids: List[int], temperature: float = 1.0, top_k: int | None = None, top_p: float | None = None, repetition_penalty: float = 1.2) -> int:
        """Sampling mit Maskierung, Temperatur, Top-K/P, Repetition Penalty (gegen who-Wiederholung)."""
        logits_seq = self.forward(token_ids)
        last_logits = logits_seq[-1] if logits_seq else [0.0] * self.config.vocab_size
        last_logits = self._mask_special(last_logits)
        # Repetition Penalty: bestrafe kürzlich generierte Tokens (gegen "Plattform Plattform..." und "who who")
        if repetition_penalty != 1.0 and len(token_ids) > 0:
            recent = set(token_ids[-8:])
            for tok_id in recent:
                if 0 <= tok_id < len(last_logits) and last_logits[tok_id] != float("-inf"):
                    if last_logits[tok_id] > 0:
                        last_logits[tok_id] /= repetition_penalty
                    else:
                        last_logits[tok_id] *= repetition_penalty
        if temperature != 1.0 and temperature > 0:
            last_logits = [l / temperature for l in last_logits]
        elif temperature == 0:
            return max(range(len(last_logits)), key=lambda i: last_logits[i])
        if top_k is not None and top_k > 0:
            top_idx = sorted(range(len(last_logits)), key=lambda i: last_logits[i], reverse=True)[:top_k]
            filtered = [float("-inf")] * len(last_logits)
            for i in top_idx:
                filtered[i] = last_logits[i]
            last_logits = filtered
        if all(v == float("-inf") for v in last_logits):
            return self.vocab.token_to_id(self.vocab.special.unk)
        max_idx = max(range(len(last_logits)), key=lambda i: last_logits[i])
        return max_idx

    def generate(self, prompt: str, max_new_tokens: int = 20, temperature: float = 0.8) -> str:
        """Einfache Greedy-Generierung — gibt nur neue Tokens zurück, nicht den Prompt (kein Leak)."""
        enc = self.tokenizer.encode(prompt)
        input_ids = enc.ids[: self.config.max_seq_len - max_new_tokens]
        if not input_ids:
            input_ids = [self.vocab.token_to_id(self.vocab.special.bos)]
        orig_len = len(input_ids)
        ids = list(input_ids)
        for _ in range(max_new_tokens):
            nxt = self.generate_next_token(ids, temperature=temperature)
            if nxt == self.vocab.token_to_id(self.vocab.special.eos):
                break
            ids.append(nxt)
            if len(ids) >= self.config.max_seq_len:
                break
        # Nur neue Tokens dekodieren, nicht den Prompt (verhindert System-Prompt-Leak)
        new_ids = ids[orig_len:]
        if not new_ids:
            return ""
        return self.tokenizer.decode(new_ids)

    def count_parameters(self) -> int:
        # Grob: embeddings + transformer + head
        emb = self.config.vocab_size * self.config.d_model
        # transformer: sehr grob
        per_layer = self.config.d_model * self.config.d_model * 4 + self.config.d_model * self.config.d_ff * 2
        trans = per_layer * self.config.n_layers
        head = self.config.vocab_size * self.config.d_model
        return emb + trans + head

    def get_config(self) -> SyrionModelConfig:
        return self.config
