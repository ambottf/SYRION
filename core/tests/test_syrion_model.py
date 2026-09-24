"""Tests für SYRION eigenes Modell — alle Schnittstellen."""
import pathlib
import pytest

from app.syrion_model.vocabulary import Vocabulary
from app.syrion_model.tokenizer.simple import SimpleTokenizer
from app.syrion_model.embeddings import SyrionEmbeddings, EmbeddingConfig
from app.syrion_model.transformer import SyrionTransformer, TransformerConfig
from app.syrion_model.model import SyrionModel, SyrionModelConfig
from app.syrion_model.dataset import build_dataset
from app.syrion_model.checkpoint import CheckpointManager
from app.syrion_model.evaluation import Evaluator
from app.syrion_model.inference import InferenceEngine
from app.syrion_model.registry import SyrionModelRegistry


def test_vocabulary():
    v = Vocabulary.minimal()
    assert v.size > 10
    assert v.token_to_id("hello") != v.token_to_id("<unk>")
    v.save(pathlib.Path("/tmp/test_vocab.json"))
    v2 = Vocabulary.load(pathlib.Path("/tmp/test_vocab.json"))
    assert v2.size == v.size


def test_tokenizer():
    v = Vocabulary.minimal()
    tok = SimpleTokenizer(v)
    enc = tok.encode("hello world")
    assert len(enc.ids) == 2
    assert enc.tokens == ["hello", "world"]
    dec = tok.decode(enc.ids)
    assert "hello" in dec
    assert tok.get_vocab_size() == v.size


def test_embeddings():
    v = Vocabulary.minimal()
    cfg = EmbeddingConfig(vocab_size=v.size, d_model=32, max_seq_len=16)
    emb = SyrionEmbeddings(cfg)
    seq = emb.lookup([0, 1, 2])
    assert len(seq) == 3
    assert len(seq[0]) == 32


def test_transformer():
    cfg = TransformerConfig(d_model=32, n_heads=4, n_layers=2, d_ff=64, vocab_size=100)
    trans = SyrionTransformer(cfg)
    embs = [[0.1] * 32 for _ in range(4)]
    out = trans.forward(embs)
    assert len(out) == 4
    assert len(out[0]) == 32


def test_syrion_model():
    v = Vocabulary.minimal()
    tok = SimpleTokenizer(v)
    cfg = SyrionModelConfig(vocab_size=v.size, d_model=32, n_layers=1)
    model = SyrionModel(cfg, v, tok)
    assert model.count_parameters() > 0
    text = model.generate("hello world", max_new_tokens=5)
    assert isinstance(text, str)
    assert len(text) > 0


def test_dataset_and_checkpoint(tmp_path: pathlib.Path):
    ds = build_dataset([{"text": "hello world", "source": "test"}, {"text": "SYRION is great", "source": "test"}], version="0.1.0")
    assert ds.stats()["count"] == 2
    ds2 = ds.dedupe()
    assert ds2.stats()["count"] == 2
    # Dedupe
    ds3 = build_dataset([{"text": "hello world", "source": "test"}, {"text": "hello world", "source": "test2"}], version="0.1.1")
    assert ds3.dedupe().stats()["count"] == 1
    # Checkpoint
    cm = CheckpointManager(base_dir=tmp_path / "checkpoints")
    from app.syrion_model.model import SyrionModelConfig
    from app.syrion_model.vocabulary import Vocabulary
    from app.syrion_model.tokenizer.simple import SimpleTokenizer

    v = Vocabulary.minimal()
    tok = SimpleTokenizer(v)
    cfg = SyrionModelConfig(vocab_size=v.size, d_model=32)
    model = SyrionModel(cfg, v, tok)
    from app.syrion_model.training import TrainingPipeline, TrainingConfig

    pipe = TrainingPipeline(model, ds, TrainingConfig(max_steps=2, output_dir=str(tmp_path / "checkpoints")))
    result = pipe.run()
    assert result.loss > 0
    assert (tmp_path / "checkpoints" / result.run_id / "checkpoint.json").exists()


def test_evaluation():
    v = Vocabulary.minimal()
    tok = SimpleTokenizer(v)
    cfg = SyrionModelConfig(vocab_size=v.size, d_model=32)
    model = SyrionModel(cfg, v, tok)
    ds = build_dataset([{"text": "hello world", "source": "test"}], version="0.1.0")
    ev = Evaluator(model)
    res = ev.evaluate(ds)
    assert res.perplexity > 0
    assert 0 <= res.accuracy <= 1


@pytest.mark.asyncio
async def test_inference():
    v = Vocabulary.minimal()
    tok = SimpleTokenizer(v)
    cfg = SyrionModelConfig(vocab_size=v.size, d_model=32)
    model = SyrionModel(cfg, v, tok)
    engine = InferenceEngine(model, tok)
    txt = await engine.generate("hello", max_new_tokens=5, timeout_s=5)
    assert isinstance(txt, str)
    chunks = []
    async for c in engine.stream("hello", max_new_tokens=5, timeout_s=5):
        chunks.append(c)
    assert len(chunks) > 0
    info = engine.get_model_info()
    assert info["vocab_size"] == v.size


def test_registry():
    import tempfile, pathlib

    with tempfile.TemporaryDirectory() as tmp:
        reg = SyrionModelRegistry(base_dir=pathlib.Path(tmp) / "models")
        from app.syrion_model.registry import ModelVersion

        v = ModelVersion(version="0.1.0", checkpoint="checkpoints/run_1/checkpoint.json", vocab_version="0.1.0")
        reg.register(v)
        assert len(reg.list()) == 1
        assert reg.latest().version == "0.1.0"
        reg.set_active("0.1.0")
        assert reg.active_version() == "0.1.0"
