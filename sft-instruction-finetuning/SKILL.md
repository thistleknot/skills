---
name: sft-instruction-finetuning
description: >
  Supervised fine-tuning (SFT) for instruction-following LLMs. Covers: dataset preparation
  with instruction/output pairs, completion-only loss masking (labels=-100 on prompt tokens),
  batch creation with padding and collation, training loop with AdamW, and evaluation of
  instruction-tuned models. Use when implementing or debugging SFT pipelines, understanding
  why full-sequence loss drowns short completion signals, or building data loaders for
  chat-formatted training. Source: "Build a Large Language Model (From Scratch)" Ch 7,
  Sebastian Raschka.
---

# SFT / Instruction Fine-Tuning (Raschka, Ch 7)

## Core Concept

SFT teaches a pretrained model to follow instructions by training on (instruction, response) pairs with cross-entropy loss on the RESPONSE tokens only.

### Why Completion-Only Loss

Full-sequence loss = loss on prompt + loss on response.
- Prompt tokens are predictable (the model already knows how to continue them)
- Response tokens are where the model needs to LEARN
- At token ratios like 500 prompt : 5 response, the response signal is <1% of total loss
- Result: model learns to reproduce prompts, not to generate responses
- Fix: mask prompt tokens with labels=-100 (ignored by cross-entropy)

### Dataset Format

```python
# Each training example:
{
    "instruction": "What is the capital of France?",
    "input": "",  # optional context
    "output": "The capital of France is Paris."
}

# Formatted as chat template:
# <|im_start|>system\nYou are a helpful assistant.<|im_end|>
# <|im_start|>user\n{instruction}\n{input}<|im_end|>
# <|im_start|>assistant\n{output}<|im_end|>
```

### Tokenization with Masking

```python
def encode_example(instruction, output, tokenizer, max_len):
    prompt_text = format_prompt(instruction)
    full_text = prompt_text + output + tokenizer.eos_token
    
    prompt_ids = tokenizer(prompt_text)["input_ids"]
    full_ids = tokenizer(full_text)["input_ids"][:max_len]
    
    # Labels: -100 for prompt, actual token IDs for completion
    labels = [-100] * len(prompt_ids) + full_ids[len(prompt_ids):]
    
    return {"input_ids": full_ids, "labels": labels, "attention_mask": [1]*len(full_ids)}
```

### Batch Collation

Variable-length sequences need padding:
```python
# DataCollatorForSeq2Seq handles:
# 1. Pad input_ids with pad_token_id
# 2. Pad labels with -100 (so padding doesn't contribute to loss)
# 3. Pad attention_mask with 0
```

### Training

```python
from transformers import Trainer, TrainingArguments

args = TrainingArguments(
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,  # effective batch = 8
    learning_rate=2e-5,
    num_train_epochs=3,
    fp16=True,
    gradient_checkpointing=True,
    optim="adamw_8bit",  # saves VRAM on optimizer state
)

trainer = Trainer(model=model, args=args, train_dataset=dataset,
                  data_collator=DataCollatorForSeq2Seq(tokenizer, label_pad_token_id=-100))
trainer.train()
```

### Evaluation

Generate from test prompts and compare to gold:
- Use greedy decoding (do_sample=False) for deterministic eval
- Score with task-specific metrics (F1, accuracy, judge)
- The model should now format responses in the expected style

## Key Lessons

1. **Completion-only loss is non-negotiable** for instruction tuning where prompts are long relative to responses
2. **Learning rate**: 1e-5 to 5e-5 for full-param SFT; 1e-4 for LoRA
3. **Epochs**: 2-3 is typical; more risks overfitting on small datasets
4. **Data quality > quantity**: 1000 high-quality examples often beats 10000 noisy ones
5. **Validation during training**: generate and inspect outputs every N steps to catch collapse early
6. **AdamW 8-bit**: halves optimizer state memory (6GB → 3GB for 0.8B model)

## Relation to Our Pipeline

Our `vibe_sft.py` implements this pattern:
- `enc()` function creates labels with -100 masking on prompt tokens
- Cross-hatch sampling ensures class-balanced training data
- Quantile-blocked batching minimizes padding waste
- Observable callback generates from held-aside prompts every 10 steps
- Full-param FFN-only (attention frozen) is the current best config
