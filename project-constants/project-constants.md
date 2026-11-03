# Project Constants

## When to trigger
Before typing any model name, file path, numeric hyperparameter, or collection name
as a string literal or hardcoded value.

## Procedure

1. Open `config.py` (or project equivalent — grep for the value if unsure).
2. Find the constant that represents the value.
3. Import and use the constant name. Never use the literal string.

If no constant exists, add one to `config.py` — do not hardcode in multiple places.

## Key constants in RL_V2 (config.py)

| Constant | What it is |
|----------|------------|
| `MODEL_NAME` | Base model identifier |
| `SFT_CHECKPOINT` | SFT checkpoint path |
| `GRPO_CHECKPOINT` | GRPO output path |
| `GRPO_GROUP_SIZE` | Generation group size |
| `DATA_LABELED` | Labeled data directory |
| `DATA_SYNTHETIC` | Synthetic data directory |
| `CHROMA_DIR` | ChromaDB storage path |
| `CHROMA_COLLECTION` | ChromaDB collection name |
| `FETCH_K` | RAG retrieval k |

## Gotchas

- `generation_batch_size` in GRPOConfig must equal `GRPO_GROUP_SIZE` exactly
  (not a multiple — trl requires they divide evenly; same value is safest)
- A slightly different string ("Qwen3.5-0.8B" vs "unsloth/Qwen3.5-0.8B") will fail silently
  or load the wrong checkpoint — always use `MODEL_NAME`
