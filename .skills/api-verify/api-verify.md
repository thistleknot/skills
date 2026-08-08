# API Verify

## When to trigger
Before writing code that instantiates a class or calls a function from any ML or
fast-moving library (trl, transformers, peft, chromadb, etc.).

## Procedure

Run this to see the actual installed parameter names:

    python -c "import inspect; from <lib> import <Class>; print(list(inspect.signature(<Class>.__init__).parameters.keys()))"

For classmethods like `from_pretrained`:

    python -c "import inspect; from transformers import AutoModelForCausalLM; print(list(inspect.signature(AutoModelForCausalLM.from_pretrained).parameters.keys()))"

The installed version governs. Never trust documentation.

## Real examples (trl 1.6.0)

    python -c "import inspect; from trl import GRPOConfig; print(list(inspect.signature(GRPOConfig.__init__).parameters.keys()))"
    python -c "import inspect; from trl import GRPOTrainer; print(list(inspect.signature(GRPOTrainer.__init__).parameters.keys()))"

Verified names:
- `GRPOConfig`: `max_completion_length` (not `max_output_tokens` / `max_new_tokens`)
- `GRPOConfig`: `beta` (not `kl_coeff`), `output_dir` required
- `GRPOTrainer`: no `ref_model` kwarg (KL handled internally via `beta`)
- `AutoModelForCausalLM.from_pretrained`: `dtype` (not `torch_dtype`)

## Gotchas

- `from_pretrained` is a classmethod — inspect it directly, not via `.__init__`
- A param not found in `__init__` may be inherited from a parent class — check `Class.__mro__`
- Docs often document the latest release; the installed version may differ
