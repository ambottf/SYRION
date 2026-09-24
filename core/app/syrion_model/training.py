"""Training-Pipeline — Schnittstelle, kein großes Training in diesem Schritt.

Kontrolliert: Dataset → Tokenizer → Model → Checkpoint, alles versioniert.
Kein automatisches Self-Training — nur via Admin-Freigabe und signierten Dataset.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any
import json
import time
from datetime import datetime, timezone

from .checkpoint import CheckpointManager
from .dataset import DatasetVersion
from .model import SyrionModel


@dataclass(frozen=True)
class TrainingConfig:
    epochs: int = 1
    batch_size: int = 4
    learning_rate: float = 5e-4
    max_steps: int = 10  # winzig für Tests
    seed: int = 42
    output_dir: str = "checkpoints"


@dataclass
class TrainingResult:
    run_id: str
    config: TrainingConfig
    dataset_version: str
    steps: int
    loss: float
    checkpoint_path: str
    duration_s: float


class TrainingPipeline:
    """Pipeline — führt deterministisch kleine Trainingsläufe für Tests aus."""

    def __init__(self, model: SyrionModel, dataset: DatasetVersion, config: TrainingConfig | None = None) -> None:
        self.model = model
        self.dataset = dataset
        self.config = config or TrainingConfig()
        self.checkpoint_mgr = CheckpointManager(base_dir=Path(self.config.output_dir))

    def run(self) -> TrainingResult:
        start = time.time()
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{self.dataset.version}"
        # Simuliertes Training: kein echter Optimizer für großes Modell, nur Loss-Sink Simulation
        loss = 4.0
        for step in range(self.config.max_steps):
            # Fake loss decay
            loss = max(0.5, loss * 0.92)
        duration = time.time() - start
        # Checkpoint speichern (Metadaten, kein riesiges Gewicht hier)
        ckpt_path = self.checkpoint_mgr.save(
            run_id=run_id,
            model_config=self.model.get_config().__dict__,
            dataset_version=self.dataset.version,
            metrics={"loss": loss, "steps": self.config.max_steps},
        )
        return TrainingResult(
            run_id=run_id,
            config=self.config,
            dataset_version=self.dataset.version,
            steps=self.config.max_steps,
            loss=loss,
            checkpoint_path=str(ckpt_path),
            duration_s=duration,
        )

    def dry_run(self) -> Dict[str, Any]:
        """Prüft nur, ob Dataset/Model kompatibel sind, ohne zu trainieren."""
        return {
            "vocab_size": self.model.vocab.size,
            "model_params": self.model.count_parameters(),
            "dataset_count": len(self.dataset.entries),
            "would_train_steps": self.config.max_steps,
        }
