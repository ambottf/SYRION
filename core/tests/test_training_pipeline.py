"""Tests für komplette SYRION Training Pipeline — echter kleiner Run."""
import pathlib
import pytest
import torch

from app.syrion_model.dataset_loader import DatasetLoader
from app.syrion_model.dataset_validator import validate_dataset
from app.syrion_model.text_cleaning import clean_text, is_valid_for_training
from app.syrion_model.tokenization_pipeline import TokenizationPipeline
from app.syrion_model.batching import create_batches
from app.syrion_model.vocabulary import Vocabulary
from app.syrion_model.tokenizer.simple import SimpleTokenizer
from app.syrion_model.training_loop import train


def test_text_cleaning():
    assert clean_text("<p>Hello  world! https://example.com</p>") == "Hello world!"
    assert is_valid_for_training("SYRION ist ein tolles System mit vielen Fakten und Wissen.")
    assert not is_valid_for_training("hi")
    assert not is_valid_for_training("a a a a a")


def test_dataset_loader_and_validator(tmp_path: pathlib.Path):
    loader = DatasetLoader()
    data = loader.load_small_test_dataset()
    assert len(data) == 20
    report = validate_dataset(data)
    assert report["is_ok"]
    assert report["valid_ratio"] >= 0.8


def test_tokenization_and_batching():
    v = Vocabulary.minimal()
    tok = SimpleTokenizer(v)
    pipe = TokenizationPipeline(tok)
    texts = ["SYRION ist lokal", "Das Brain hat Memory"]
    toked = pipe.tokenize(texts, max_length=16)
    assert len(toked) == 2
    batches = create_batches(toked, batch_size=2, pad_token_id=v.token_to_id(v.special.pad))
    assert len(batches) == 1
    assert batches[0]["input_ids"].shape[0] == 2


def test_training_small_run(tmp_path: pathlib.Path):
    # Echter kleiner Training Run, lokal, CPU/GPU auto
    loader = DatasetLoader()
    data = loader.load_small_test_dataset()
    texts = [d["text"] for d in data[:12]]
    val_texts = [d["text"] for d in data[12:16]]

    result = train(
        train_texts=texts,
        val_texts=val_texts,
        batch_size=2,
        epochs=2,
        lr=5e-4,
        d_model=32,
        n_layers=1,
        checkpoint_dir=tmp_path / "checkpoints",
    )
    assert "train_loss" in result
    assert "val_loss" in result
    assert "ppl" in result
    assert result["train_loss"] > 0
    assert result["val_loss"] > 0
    assert result["duration_s"] > 0
    assert pathlib.Path(result["checkpoint_dir"]).exists()
    # Checkpoints existieren
    assert (tmp_path / "checkpoints" / "syrion_epoch_1" / "model.pt").exists()
    assert (tmp_path / "checkpoints" / "best" / "model.pt").exists()
    # Hardware erkannt
    assert "device" in result
    assert result["device"] in ("cpu", "cuda", "mps")
    # Loss sollte nicht explodieren
    assert result["train_loss"] < 10
    # Metrics vorhanden
    assert len(result["metrics"]) == 2
    assert result["metrics"][0]["train_loss"] >= 0


def test_resume_training(tmp_path: pathlib.Path):
    loader = DatasetLoader()
    data = loader.load_small_test_dataset()
    texts = [d["text"] for d in data[:8]]
    # Erster Run
    result1 = train(train_texts=texts, epochs=1, checkpoint_dir=tmp_path / "checkpoints_resume", batch_size=2, d_model=32, n_layers=1)
    assert result1["epochs"] == 1
    # Resume (sollte nicht crashen, auch wenn Logik simpel)
    result2 = train(train_texts=texts, epochs=2, checkpoint_dir=tmp_path / "checkpoints_resume", batch_size=2, d_model=32, n_layers=1, resume=True)
    assert result2["epochs"] == 2
