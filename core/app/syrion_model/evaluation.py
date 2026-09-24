"""Evaluation — misst Modellqualität vor Freigabe."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List
import math

from .dataset import DatasetVersion
from .model import SyrionModel


@dataclass
class EvalResult:
    perplexity: float
    accuracy: float
    details: Dict[str, Any]


class Evaluator:
    def __init__(self, model: SyrionModel) -> None:
        self.model = model

    def perplexity(self, dataset: DatasetVersion, max_samples: int = 10) -> float:
        # Sehr einfache PPL: average negative log prob aus Logits (mock, aber deterministisch)
        total_nll = 0.0
        total_tokens = 0
        for entry in dataset.entries[:max_samples]:
            enc = self.model.tokenizer.encode(entry.text)
            if len(enc.ids) < 2:
                continue
            logits_seq = self.model.forward(enc.ids)
            # Für jedes Token: NLL = -log softmax[true]
            for i in range(len(enc.ids) - 1):
                logits = logits_seq[i]
                # softmax
                m = max(logits)
                exps = [math.exp(l - m) for l in logits]
                s = sum(exps)
                probs = [e / s for e in exps]
                true_id = enc.ids[i + 1]
                p = probs[true_id] if 0 <= true_id < len(probs) else 1e-9
                total_nll += -math.log(max(p, 1e-9))
                total_tokens += 1
        if total_tokens == 0:
            return float("inf")
        avg_nll = total_nll / total_tokens
        return math.exp(avg_nll)

    def evaluate(self, dataset: DatasetVersion) -> EvalResult:
        ppl = self.perplexity(dataset)
        # Accuracy: dummy, aber deterministisch aus PPL
        acc = max(0.0, min(1.0, 1.0 / (1.0 + math.log(ppl + 1))))
        return EvalResult(perplexity=ppl, accuracy=acc, details={"samples": min(len(dataset.entries), 10), "model_version": self.model.config.version})
