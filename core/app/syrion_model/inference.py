"""Inference Engine — SYRION lokale Inferenz (kein Ollama).

Kapselt Tokenizer + Model + Streaming, mit Timeout/Cancellation.
Wird vom ModelAdapter verwendet, nicht direkt von Core.
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator, List

from .model import SyrionModel
from .tokenizer.base import SyrionTokenizer


class InferenceEngine:
    def __init__(self, model: SyrionModel, tokenizer: SyrionTokenizer | None = None) -> None:
        self.model = model
        self.tokenizer = tokenizer or model.tokenizer

    async def generate(self, prompt: str, *, max_new_tokens: int = 20, temperature: float = 0.8, timeout_s: float = 30) -> str:
        # In echtem Betrieb: Modell auf GPU, hier deterministisch schnell
        try:
            # Offload sync generate in Thread, damit Timeout greift
            def _sync() -> str:
                return self.model.generate(prompt, max_new_tokens=max_new_tokens, temperature=temperature)

            return await asyncio.wait_for(asyncio.to_thread(_sync), timeout=timeout_s)
        except asyncio.TimeoutError:
            raise
        except asyncio.CancelledError:
            raise

    async def stream(self, prompt: str, *, max_new_tokens: int = 20, temperature: float = 0.8, timeout_s: float = 30) -> AsyncIterator[str]:
        # Simuliere Token-Streaming: generiere voll, dann chunkweise yielden (für Test deterministisch)
        full = await self.generate(prompt, max_new_tokens=max_new_tokens, temperature=temperature, timeout_s=timeout_s)
        # Chunk als Worte
        words = full.split(" ")
        for w in words:
            yield w + " "
            await asyncio.sleep(0.02)

    def get_model_info(self) -> dict:
        return {
            "version": self.model.config.version,
            "vocab_size": self.model.vocab.size,
            "params": self.model.count_parameters(),
            "max_seq_len": self.model.config.max_seq_len,
        }
