"""Debug Logging — detailliert für SYRION Pipeline Diagnose."""
from __future__ import annotations

import json
from typing import List
from .vocabulary import Vocabulary
from .tokenizer.simple import SimpleTokenizer
from .model import SyrionModel, SyrionModelConfig


def debug_pipeline(text: str, *, vocab: Vocabulary | None = None) -> dict:
    """Loggt jeden Schritt: Text → Tokens → IDs → Embeddings → Logits → Selected → Decoded."""
    if vocab is None:
        vocab = Vocabulary.minimal()
    tok = SimpleTokenizer(vocab)
    cfg = SyrionModelConfig(vocab_size=vocab.size, d_model=32, n_layers=1, version="debug")
    model = SyrionModel(cfg, vocab, tok)

    enc = tok.encode(text)
    # Embeddings
    emb = model.embeddings.lookup(enc.ids)
    # Logits
    logits = model.forward(enc.ids)
    last_logits = logits[-1] if logits else []
    # Masked
    masked = model._mask_special(last_logits)  # type: ignore[attr-defined]
    # Top 5 before/after mask
    def top5(logits_list):
        return sorted(range(len(logits_list)), key=lambda i: logits_list[i], reverse=True)[:5]

    top_before = top5(last_logits) if last_logits else []
    top_after = top5(masked) if masked else []

    # Next token
    nxt = model.generate_next_token(enc.ids)
    decoded = tok.decode([nxt])

    return {
        "input": text,
        "tokens": enc.tokens,
        "token_ids": enc.ids,
        "vocab_size": vocab.size,
        "embedding_shape": f"{len(emb)}x{len(emb[0]) if emb else 0}",
        "logits_shape": f"{len(logits)}x{len(logits[0]) if logits and logits[0] else 0}",
        "logits_sample": last_logits[:5] if last_logits else [],
        "masked_sample": masked[:5] if masked else [],
        "top_before": [{"id": i, "token": vocab.id_to_token(i), "logit": last_logits[i]} for i in top_before],
        "top_after": [{"id": i, "token": vocab.id_to_token(i), "logit": masked[i]} for i in top_after],
        "selected_id": nxt,
        "selected_token": vocab.id_to_token(nxt),
        "decoded": decoded,
        "has_unk": "<unk>" in decoded,
        "has_mask": "<mask>" in decoded,
    }


if __name__ == "__main__":
    for txt in ["Hallo SYRION", "Wie geht es dir?", "SYRION ist ein lokales System"]:
        print(json.dumps(debug_pipeline(txt), ensure_ascii=False, indent=2))
