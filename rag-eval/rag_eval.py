"""rag_eval.py — Single-pass 10-metric RAG evaluation via structured LLM judge.

Uses qwen3.5:4b through Ollama's OpenAI-compat endpoint. One prompt, one model
call, structured JSON output via Pydantic RAGEvalResult.

Require:
    openai, pydantic — pip install openai pydantic
    Ollama running at localhost:11434 with qwen3.5:4b pulled

Thinking suppression (Qwen3 quirk):
    /no_think prefix in user message  +  extra_body={"think": False}
    Both are needed: prefix is model-level, extra_body is Ollama-level.
    Without extra_body, the model may still emit <think> blocks that eat
    tokens and pollute the JSON response.
"""

from __future__ import annotations

import json
import logging
import re
import statistics
from typing import Optional

from openai import OpenAI
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_API_KEY  = "ollama"
DEFAULT_MODEL   = "qwen3.5:4b"

SYSTEM_PROMPT = (
    "You are a RAG evaluation engine. "
    "Return ONLY a valid JSON object with numeric scores. "
    "No markdown, no explanation, no extra keys, no thinking."
)

METRIC_DEFINITIONS = """/no_think

Score each of the 10 metrics on a scale from 0.0 (worst) to 1.0 (best).

Metric definitions:
  relevance                 - Does the answer directly address the question? (1.0 = complete match)
  entailment                - Is the answer logically entailed by the context? (NLI; 1.0 = fully supported)
  faithfulness              - Are all answer claims grounded in context with no hallucination? (1.0 = no drift)
  correctness               - Is the answer factually correct vs ground truth? (use 0.5 if no ground truth provided)
  context_entity_precision  - Fraction of named entities in the answer that appear in context (precision)
  context_entity_recall     - Fraction of named entities in context that are captured in the answer (recall)
  factualness               - Is the answer accurate against world knowledge, independent of context? (1.0 = accurate)
  fluency                   - Is the answer grammatically correct and readable? (1.0 = fluent)
  coherence                 - Is the answer internally consistent with no contradictions? (1.0 = coherent)
  informativeness           - Does the answer provide substantive content rather than vague filler? (1.0 = dense)

Return ONLY this JSON structure, no other text:
{
  "relevance": 0.0,
  "entailment": 0.0,
  "faithfulness": 0.0,
  "correctness": 0.0,
  "context_entity_precision": 0.0,
  "context_entity_recall": 0.0,
  "factualness": 0.0,
  "fluency": 0.0,
  "coherence": 0.0,
  "informativeness": 0.0
}"""


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class RAGEvalResult(BaseModel):
    """
    Structured output from a single RAG evaluation call.

    macro_mean is computed automatically from the 10 metric scores.
    Do not pass it to the constructor — it is set by the model_validator.
    """

    relevance: float                 = Field(..., ge=0.0, le=1.0)
    entailment: float                = Field(..., ge=0.0, le=1.0)
    faithfulness: float              = Field(..., ge=0.0, le=1.0)
    correctness: float               = Field(..., ge=0.0, le=1.0)
    context_entity_precision: float  = Field(..., ge=0.0, le=1.0)
    context_entity_recall: float     = Field(..., ge=0.0, le=1.0)
    factualness: float               = Field(..., ge=0.0, le=1.0)
    fluency: float                   = Field(..., ge=0.0, le=1.0)
    coherence: float                 = Field(..., ge=0.0, le=1.0)
    informativeness: float           = Field(..., ge=0.0, le=1.0)
    macro_mean: float                = Field(default=0.0, ge=0.0, le=1.0)

    _METRIC_FIELDS = [
        "relevance", "entailment", "faithfulness", "correctness",
        "context_entity_precision", "context_entity_recall",
        "factualness", "fluency", "coherence", "informativeness",
    ]

    @model_validator(mode="after")
    def compute_macro_mean(self) -> RAGEvalResult:
        scores = [getattr(self, f) for f in self._METRIC_FIELDS]
        self.macro_mean = round(statistics.mean(scores), 4)
        return self


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_prompt(
    question: str,
    answer: str,
    context: str,
    ground_truth: Optional[str],
) -> str:
    gt_line = f"Ground Truth: {ground_truth}" if ground_truth else "Ground Truth: not provided"
    return (
        f"{METRIC_DEFINITIONS}\n\n"
        f"Question: {question}\n"
        f"Context: {context}\n"
        f"Answer: {answer}\n"
        f"{gt_line}"
    )


# ---------------------------------------------------------------------------
# Response cleanup
# ---------------------------------------------------------------------------

def _strip_thinking(raw: str) -> str:
    """
    Remove <think>...</think> blocks and markdown fences from model output.

    Require:  raw is the model's raw string output.
    Guarantee: returned string contains only the JSON payload or is unchanged.
    """
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    raw = re.sub(r"```(?:json)?", "", raw)
    return raw.strip()


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

def evaluate(
    question: str,
    answer: str,
    context: str | list[str],
    ground_truth: Optional[str] = None,
    base_url: str = OLLAMA_BASE_URL,
    model: str = DEFAULT_MODEL,
    timeout: float = 300.0,
) -> RAGEvalResult:
    """
    Evaluate a RAG response across 10 metrics in a single model call.

    Require:
        question     non-empty string
        answer       non-empty string
        context      string or list[str] — lists are newline-joined
        ground_truth optional; when None, correctness is forced to 0.5 post-hoc
                     rather than trusting the model to honour the prompt instruction
        timeout      seconds to wait for Ollama response; default 300 covers first-
                     load warm-up of larger models (httpx default is 5s — too short;
                     qwen3.5:4b first load can take 90-180s on cold GPU)

    Guarantee:
        Returns RAGEvalResult with all 10 scores in [0.0, 1.0] and
        macro_mean as the scalar fitness score.

    Maintain:
        One prompt, one model call. No retries, no multi-turn.

    Assert:
        Raw model output, after stripping thinking blocks, must be valid JSON
        containing all 10 required metric keys.
    """
    if isinstance(context, list):
        context = "\n".join(context)

    assert question.strip(), "question must be non-empty"
    assert answer.strip(),   "answer must be non-empty"
    assert context.strip(),  "context must be non-empty"

    client = OpenAI(base_url=base_url, api_key=OLLAMA_API_KEY, timeout=timeout)
    prompt = build_prompt(question, answer, context, ground_truth)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
        # Ollama-specific: disables Qwen3 chain-of-thought at the runtime level.
        # /no_think in the prompt is the model-level instruction; this is the
        # Ollama-level kill switch. Both are required for reliable suppression.
        extra_body={"think": False},
    )

    raw = response.choices[0].message.content
    logger.debug("raw model response:\n%s", raw)

    cleaned = _strip_thinking(raw)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Model did not return valid JSON.\nCleaned: {cleaned!r}\nRaw: {raw!r}"
        ) from exc

    result = RAGEvalResult(**parsed)

    # Post-hoc override: when no ground_truth is available the model can score
    # correctness arbitrarily. Force 0.5 (neutral) and recompute macro_mean.
    if ground_truth is None:
        d = result.model_dump()
        d["correctness"] = 0.5
        result = RAGEvalResult(**d)

    return result


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    result = evaluate(
        question="What causes the greenhouse effect?",
        answer=(
            "The greenhouse effect is caused by gases like CO2 and methane "
            "trapping heat in the atmosphere by absorbing infrared radiation."
        ),
        context=(
            "Greenhouse gases such as carbon dioxide, methane, and water vapor "
            "absorb infrared radiation emitted by Earth's surface and re-emit it, "
            "warming the lower atmosphere. Human activities have increased CO2 "
            "concentrations significantly since the industrial revolution."
        ),
        ground_truth=(
            "Greenhouse gases trap outgoing infrared radiation, causing the "
            "atmosphere to warm. CO2 and methane are the primary contributors."
        ),
    )

    print(result.model_dump_json(indent=2))
    print(f"\nMacro Mean: {result.macro_mean}")
