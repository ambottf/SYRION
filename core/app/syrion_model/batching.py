"""Batching — SYRION Training Batches mit Padding."""
from __future__ import annotations

from typing import List, Dict, Any
import torch


def collate_batch(batch: List[Dict[str, Any]], *, pad_token_id: int = 0, max_length: int | None = None) -> Dict[str, torch.Tensor]:
    """Wandelt Liste von {input_ids} in Tensor-Batch mit Padding."""
    # Bestimme max_len
    max_len = max(len(x["input_ids"]) for x in batch) if batch else 0
    if max_length is not None:
        max_len = min(max_len, max_length)
    # Pad
    input_ids: List[List[int]] = []
    attention_mask: List[List[int]] = []
    labels: List[List[int]] = []  # Für Language Modeling: shift
    for item in batch:
        ids = item["input_ids"][:max_len]
        pad_len = max_len - len(ids)
        # Input
        padded = ids + [pad_token_id] * pad_len
        mask = [1] * len(ids) + [0] * pad_len
        # Labels: next token, -100 für pad (ignore) — basiert auf gepaddeter Sequenz
        lab = (padded[1:] + [pad_token_id])[:max_len]
        lab = [l if m else -100 for l, m in zip(lab, mask)]
        input_ids.append(padded)
        attention_mask.append(mask)
        labels.append(lab)
    return {
        "input_ids": torch.tensor(input_ids, dtype=torch.long),
        "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
        "labels": torch.tensor(labels, dtype=torch.long),
    }


def create_batches(tokenized: List[Dict[str, Any]], *, batch_size: int = 4, shuffle: bool = True, pad_token_id: int = 0) -> List[Dict[str, torch.Tensor]]:
    import random

    if shuffle:
        random.shuffle(tokenized)
    batches: List[Dict[str, torch.Tensor]] = []
    for i in range(0, len(tokenized), batch_size):
        chunk = tokenized[i : i + batch_size]
        batches.append(collate_batch(chunk, pad_token_id=pad_token_id))
    return batches
