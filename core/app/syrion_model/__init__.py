"""SYRION Model — eigenes, lokal-first Modell (kein Ollama, kein externes LLM als Kern).

Dieses Paket definiert die technische Grundlage für das spätere SYRION-Modell.
Kein Training eines großen Modells in diesem Schritt — nur Architektur, Schnittstellen,
Pipelines und Registry, damit später kontrolliert trainiert werden kann.

Struktur:
  tokenizer/   — Tokenizer-Schnittstelle
  vocabulary.py — Vocabulary-Struktur
  embeddings.py — Embedding-Schnittstelle
  transformer.py — Transformer/Neural-Network-Schnittstelle
  model.py     — SYRIONModel Architektur
  dataset.py   — Dataset-Pipeline
  training.py  — Training-Pipeline
  checkpoint.py — Checkpoint-System
  evaluation.py — Evaluation
  inference.py — Inference Engine
  registry.py  — Model Registry + Versionierung
"""
from .model import SyrionModel  # noqa: F401
from .registry import SyrionModelRegistry  # noqa: F401
from .tokenizer import SyrionTokenizer  # noqa: F401

__all__ = ["SyrionModel", "SyrionTokenizer", "SyrionModelRegistry"]
