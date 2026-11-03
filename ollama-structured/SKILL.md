---
name: ollama-structured
description: >
  Structured JSON output from Ollama models via schema-constrained generation.
  Two paths: native ollama SDK (format=Model.model_json_schema()) or OpenAI-compat
  endpoint (response_format + extra_body). Covers Qwen3 thinking suppression,
  vision models, and failure modes. Use whenever an Ollama call must return a
  typed Pydantic object rather than free-form text.
status: active
last_validated: 2026-05-31
---

# Ollama Structured Output

## When to Use

- Any Ollama call where the response must be parsed into a typed object
- LLM judge pipelines (RAG eval, quality scoring, classification)
- Vision + structured description
- Replacing brittle regex extraction with schema-enforced JSON

---

## Two API Paths

### Path A — Native `ollama` SDK (preferred for local scripts)

```python
from ollama import chat
from pydantic import BaseModel

class MySchema(BaseModel):
    field_a: str
    field_b: int

response = chat(
    model="qwen3.5:4b",
    messages=[{"role": "user", "content": prompt}],
    format=MySchema.model_json_schema(),
    options={"temperature": 0},
)
result = MySchema.model_validate_json(response.message.content)
```

Pass `think=False` at call level to suppress Qwen3 chain-of-thought:

```python
response = chat(
    model="qwen3.5:4b",
    messages=[{"role": "user", "content": "/no_think\n" + prompt}],
    format=MySchema.model_json_schema(),
    options={"temperature": 0},
    think=False,          # Ollama-level kill switch; top-level, NOT inside options
)
```

### Path B — OpenAI-compat endpoint (preferred when code already uses `openai` SDK)

```python
from openai import OpenAI
from pydantic import BaseModel

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

response = client.chat.completions.create(
    model="qwen3.5:4b",
    messages=[
        {"role": "system", "content": "Return ONLY valid JSON. No thinking."},
        {"role": "user",   "content": "/no_think\n" + prompt},
    ],
    response_format={"type": "json_object"},
    temperature=0.0,
    extra_body={"think": False},   # Ollama-specific; suppresses Qwen3 CoT at runtime level
)
raw = response.choices[0].message.content
result = MySchema.model_validate_json(raw)
```

---

## Qwen3 Thinking Suppression

Qwen3 models have thinking mode enabled by default. Without suppression the
model spends its entire token budget on `<think>` blocks, leaving `response`/
`content` empty or truncated.

**Two layers required — both, not one:**

| Layer | Mechanism | Where |
|---|---|---|
| Model-level | `/no_think` prefix in user message | user message content |
| Runtime-level | `think=False` (native SDK) or `extra_body={"think": False}` (OpenAI SDK) | top-level call param |

`think=False` must be **top-level**, never inside `options` — putting it in
`options` is silently ignored by Ollama.

If thinking bleeds through despite suppression, strip it before parsing:

```python
import re

def strip_thinking(raw: str) -> str:
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    raw = re.sub(r"```(?:json)?", "", raw)
    return raw.strip()
```

---

## Vision + Structured Output

Vision models accept the same `format` parameter:

```python
from ollama import chat
from pydantic import BaseModel
from typing import Literal, Optional

class ImageDescription(BaseModel):
    summary: str
    scene: str
    colors: list[str]
    time_of_day: Literal["Morning", "Afternoon", "Evening", "Night"]
    setting: Literal["Indoor", "Outdoor", "Unknown"]
    text_content: Optional[str] = None

response = chat(
    model="gemma3",
    messages=[{
        "role": "user",
        "content": "Describe this image.",
        "images": ["path/to/image.jpg"],
    }],
    format=ImageDescription.model_json_schema(),
    options={"temperature": 0},
)
result = ImageDescription.model_validate_json(response.message.content)
```

---

## Free-Form JSON (no schema)

When you want JSON but don't have a fixed schema yet:

```python
# Native SDK
response = chat(model="...", messages=[...], format="json")

# OpenAI compat
response = client.chat.completions.create(
    ...,
    response_format={"type": "json_object"},
)
```

Always include "return JSON" in the prompt — `format="json"` alone does not
guarantee the model emits a valid object.

---

## Failure Modes

| Failure | Cause | Fix |
|---|---|---|
| Empty `content` / `response` | Qwen3 thinking consumed all tokens | Add `think=False` + `/no_think` prefix |
| `JSONDecodeError` | Model emitted markdown fences or preamble | Run `strip_thinking()` before parse |
| `ValidationError` | Model returned wrong keys or types | Pass schema in prompt as a JSON example |
| Timeout (>120s) | 4b+ model cold-loading from disk | First call is slow; subsequent calls use cached weights |
| `extra_body` ignored | Wrong placement in options dict | `extra_body` is a top-level SDK kwarg, not inside `options` |

---

## Schema Design Tips

- Keep field names lowercase with underscores — models are more reliable on snake_case
- Add `description=` to `Field(...)` for complex fields; it appears in the schema and guides the model
- Use `Literal[...]` for categorical fields instead of `str` — schema constrains token choices
- Avoid deeply nested schemas for small models; flatten where possible
- Pass the schema as a JSON example in the prompt **in addition to** the `format` parameter

---

## See Also

- `rag-eval` — uses Path B (OpenAI compat + extra_body) for 10-metric judge scoring
- `substrate-selection` — choosing between Ollama-local and provider-routed runtimes
- `agentic-harness` — pipeline control; use this skill for any structured node output
"""
