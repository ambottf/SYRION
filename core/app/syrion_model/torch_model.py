"""SyrionTorchModel — kleines, echtes PyTorch Modell für Training (CPU/GPU)."""
from __future__ import annotations

import torch
import torch.nn as nn
import math


class SyrionTorchModel(nn.Module):
    def __init__(self, vocab_size: int, d_model: int = 64, n_layers: int = 2, n_heads: int = 4, d_ff: int = 128, max_seq_len: int = 128) -> None:
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size
        self.max_seq_len = max_seq_len
        self.token_emb = nn.Embedding(vocab_size, d_model)
        self.pos_emb = nn.Embedding(max_seq_len, d_model)
        # Einfache Transformer Blöcke (für Test klein)
        self.layers = nn.ModuleList([
            nn.TransformerEncoderLayer(d_model=d_model, nhead=n_heads, dim_feedforward=d_ff, batch_first=True, dropout=0.1)
            for _ in range(n_layers)
        ])
        self.ln = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor | None = None) -> torch.Tensor:
        # input_ids: (B, S)
        B, S = input_ids.shape
        device = input_ids.device
        pos = torch.arange(S, device=device).unsqueeze(0).expand(B, S)
        x = self.token_emb(input_ids) + self.pos_emb(pos)
        # Attention mask: 1 für echt, 0 für pad -> key_padding_mask True für pad
        if attention_mask is not None:
            key_padding_mask = attention_mask == 0
        else:
            key_padding_mask = None
        for layer in self.layers:
            x = layer(x, src_key_padding_mask=key_padding_mask)
        x = self.ln(x)
        logits = self.head(x)  # (B, S, V)
        return logits

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())
