from app.syrion_model.status import get_status
import json, pathlib
print("=== MODEL STATUS ===")
print(json.dumps(get_status(), indent=2))
print("\n=== CHECKPOINT ===")
ckpt = pathlib.Path("core/checkpoints/syrion_final_fixed/best/model.pt")
print(f"core checkpoint exists: {ckpt.exists()} size {ckpt.stat().st_size if ckpt.exists() else 0}")
ckpt2 = pathlib.Path("checkpoints/syrion_final_fixed/best/model.pt")
print(f"SYRION checkpoint exists: {ckpt2.exists()} size {ckpt2.stat().st_size if ckpt2.exists() else 0}")

from app.syrion_model.dataset_loader import DatasetLoader
loader = DatasetLoader()
data = loader.load_small_test_dataset()
print(f"\n=== DATASET {len(data)} ===")
for d in data[:3]:
    print(f"  {d['text'][:80]}")

fragments = ['assistant','who','Brain','Tag','hello','base','<unk>','<mask>']
print("\n=== FRAGMENT CHECK IN TRAINING DATA ===")
for frag in fragments:
    count = sum(1 for d in data if frag.lower() in d['text'].lower())
    print(f"  {repr(frag)} in {count}/{len(data)}")

# Check vocab
from app.syrion_model.vocabulary import Vocabulary
v = Vocabulary.minimal()
print(f"\n=== VOCAB ===")
print(f"size {v.size}")
print(f"tokens {v.tokens[:30]}")

# Check tokenizer
from app.syrion_model.tokenizer.simple import SimpleTokenizer
tok = SimpleTokenizer(v)
for txt in ["Hallo SYRION", "Was ist Robotik?", "Robotik centers around 3 main protagonists"]:
    enc = tok.encode(txt)
    print(f"\nTokenizer: {repr(txt)}")
    print(f"  -> IDs {enc.ids}")
    print(f"  -> Tokens {enc.tokens}")
    print(f"  -> Decoded {repr(tok.decode(enc.ids))}")
    unk_count = enc.tokens.count("<unk>")
    print(f"  <unk> count {unk_count}/{len(enc.tokens)}")

# Check model
from app.syrion_model.model import SyrionModel, SyrionModelConfig
cfg = SyrionModelConfig(vocab_size=v.size, d_model=32, n_layers=1, version='test')
model = SyrionModel(cfg, v, tok)
print(f"\n=== MODEL ===")
print(f"vocab_size {cfg.vocab_size} d_model {cfg.d_model} n_layers {cfg.n_layers}")
print(f"params {model.count_parameters()}")
print(f"embedding {len(model.embeddings.weight)}x{len(model.embeddings.weight[0])}")
print(f"vocab vs embedding: {v.size} vs {len(model.embeddings.weight)} match={v.size==len(model.embeddings.weight)}")
print(f"max token id {max([0]+[1])} < vocab_size {max([0]+[1]) < v.size}")

# Check SyrionAdapter
from app.core.model_adapter import SyrionAdapter
from app.core.types import ChatRequest, MemoryContext
import asyncio

async def test_adapter():
    adapter = SyrionAdapter(model_id="syrion-0.1.0-base")
    # Check what prompt is sent
    req = ChatRequest(message="Robotika centers around 3 main protagonists: Niko, Cherokee Geisha (C.G.) and Yuri Bronski")
    ctx = MemoryContext(history=[], system_prompt="Du bist SYRION, eine lokale Intelligence-Plattform. Antworte hilfreich, präzise und verweise auf Quellen wenn vorhanden.")
    # Manually build prompt as adapter does
    prompt_parts = [ctx.system_prompt]
    prompt_parts.append(f"user: {req.message}")
    prompt_parts.append("assistant:")
    prompt = "\n".join(prompt_parts)
    print(f"\n=== ACTUAL PROMPT TO MODEL ===")
    print(repr(prompt[:500]))
    print(f"Prompt contains 'assistant': {'assistant' in prompt}")
    print(f"Prompt contains 'user': {'user' in prompt}")
    # Tokenize
    enc = adapter._engine.tokenizer.encode(prompt)  # type: ignore
    print(f"Prompt tokens: {enc.tokens[:20]}...")
    print(f"Prompt ids: {enc.ids[:20]}...")
    print(f"Vocab size {adapter._engine.tokenizer.get_vocab_size()} vs model vocab {adapter._engine.model.vocab.size}")
    # Generate
    txt = await adapter.generate(req, ctx)
    print(f"\n=== ADAPTER GENERATE ===")
    print(f"Input: {req.message}")
    print(f"Output: {repr(txt[:300])}")
    print(f"has_unk {'<unk>' in txt} has_mask {'<mask>' in txt}")
    print(f"has who {'who' in txt} has Brain {'Brain' in txt} has Tag {'Tag' in txt} has hello {'hello' in txt} has base {'base' in txt}")

asyncio.run(test_adapter())

# Check conversation memory
from app.core.memory import memory_service
import asyncio
async def test_memory():
    print("\n=== CONVERSATION MEMORY ===")
    # Session A
    await memory_service.build_context(session_id="sess_A", current_message="Hallo")
    await memory_service.append_turn(session_id="sess_A", user_msg="Hallo", assistant_msg="Hallo! Wie kann ich helfen?")
    # Session B should not contain A
    ctxB = await memory_service.build_context(session_id="sess_B", current_message="Was ist Robotik?")
    print(f"Session B history len {len(ctxB.history)} should be 0")
    for m in ctxB.history:
        print(f"  {m.role}: {m.content[:50]}")
    # Check if old test data is loaded
    print(f"Session A history len after: {len((await memory_service.build_context(session_id='sess_A', current_message='test')).history)}")

asyncio.run(test_memory())
