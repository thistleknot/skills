"""
Shared whole-skill derivation backend for consolidation.

Require:
- root points at the skills repository root
- every skill folder contains a SKILL.md file

Guarantee:
- one atomic document is derived per skill folder by concatenating all markdown
  files in a deterministic order
- triplet-derived similarity replaces surface-text TF-IDF similarity
- derived surfaces are cached in consolidation/.checkpoint.db by content hash

Failure modes:
- raises RuntimeError if the configured LLM endpoint is unavailable
- raises ValueError if the LLM returns invalid triplet JSON
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kg_ontology.batch_processing import BatchAugmentationResult, BatchSynsetOrchestrator
from kg_ontology.synset_selection_schema import ElementSynsetChoices, TripletWithChosenSynsets
from kg_ontology.triplet_enrichment import CanonicalityRules, EnrichedTriplet

TRIPLET_SEPARATOR = " SEP "
DEFAULT_EMBEDDING_MODEL = os.environ.get("LLM_EMBED_MODEL", "nomic-embed-text:latest")
SPARSE_SIMILARITY_WEIGHT = float(os.environ.get("SPARSE_SIMILARITY_WEIGHT", "0.7"))
DENSE_SIMILARITY_WEIGHT = float(os.environ.get("DENSE_SIMILARITY_WEIGHT", "0.3"))
MARKDOWN_PRIORITY = {
    "SKILL.md": 0,
    "DESCRIPTION.md": 1,
    "ARCHITECTURE.md": 2,
    "HISTORY.md": 3,
}
TRIPLET_EXTRACTION_PROMPT = """\
You are extracting atomic factual and behavioral claims from one AI-agent skill document.

Return ONLY valid JSON as an array. Preserve source order. Deduplicate obvious repeats.
Each array element must match this schema exactly:
{{
  "subject": "short noun phrase",
  "predicate": "short verb/relation phrase",
  "object": "short noun phrase",
  "polarity": "affirmed" | "negated",
  "inference_type": "observed" | "inferred",
  "confidence": 0.0 to 1.0
}}

Rules:
- Extract concrete claims only; skip boilerplate headings and examples.
- Keep phrases short and copy-close to the source text.
- Prefer 10-40 high-value claims over exhaustive low-value trivia.
- If a skill states what it owns, when to use it, or what it does not own, those are valid claims.
- Do not wrap the JSON in markdown fences.

=== SKILL NAME ===
{skill_name}

=== DOCUMENT ===
{document_text}
"""


@dataclass(frozen=True)
class SkillDocument:
    """Atomic source document for one skill folder."""

    name: str
    folder: Path
    skill_file: Path
    markdown_files: tuple[Path, ...]
    source_text: str
    derivation_text: str
    content_hash: str


@dataclass(frozen=True)
class ExtractedTriplet:
    """One extracted claim in source order."""

    subject: str
    predicate: str
    object: str
    polarity: str = "affirmed"
    inference_type: str = "observed"
    confidence: float = 1.0
    subject_canonical_id: str | None = None
    predicate_canonical_id: str | None = None
    object_canonical_id: str | None = None
    bm25_subject: str | None = None
    bm25_predicate: str | None = None
    bm25_object: str | None = None

    def canonical_tuple(self) -> tuple[str, str, str]:
        """Normalize a triplet into a stable comparison tuple."""
        if (
            self.subject_canonical_id is not None
            and self.predicate_canonical_id is not None
            and self.object_canonical_id is not None
        ):
            return (
                self.subject_canonical_id,
                self.predicate_canonical_id,
                self.object_canonical_id,
            )
        return (
            normalize_phrase(self.subject),
            normalize_phrase(self.predicate),
            normalize_phrase(self.object),
        )

    def bm25_fragment(self) -> str:
        """Serialize one triplet into a BM25-friendly phrase stream."""
        parts = [
            self.bm25_subject or normalize_phrase(self.subject),
            self.bm25_predicate or normalize_phrase(self.predicate),
            self.bm25_object or normalize_phrase(self.object),
            normalize_phrase(self.polarity),
            normalize_phrase(self.inference_type),
        ]
        return " ".join(p for p in parts if p)

    def sequence_fragment(self) -> str:
        """Serialize one triplet into an ordered sequence element."""
        subject, predicate, obj = self.canonical_tuple()
        return f"{subject} | {predicate} | {obj}"

    def to_extracted_dict(self) -> dict:
        """Convert to the surface-only schema used by extraction/augmentation."""
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "polarity": self.polarity,
            "inference_type": self.inference_type,
            "confidence": self.confidence,
        }

    def to_dict(self) -> dict:
        """Convert to JSON-serializable storage format."""
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "polarity": self.polarity,
            "inference_type": self.inference_type,
            "confidence": self.confidence,
            "subject_canonical_id": self.subject_canonical_id,
            "predicate_canonical_id": self.predicate_canonical_id,
            "object_canonical_id": self.object_canonical_id,
            "bm25_subject": self.bm25_subject,
            "bm25_predicate": self.bm25_predicate,
            "bm25_object": self.bm25_object,
        }

    @staticmethod
    def from_dict(payload: dict) -> "ExtractedTriplet":
        """Rehydrate a cached triplet."""
        return ExtractedTriplet(
            subject=payload["subject"],
            predicate=payload["predicate"],
            object=payload["object"],
            polarity=payload.get("polarity", "affirmed"),
            inference_type=payload.get("inference_type", "observed"),
            confidence=float(payload.get("confidence", 1.0)),
            subject_canonical_id=payload.get("subject_canonical_id"),
            predicate_canonical_id=payload.get("predicate_canonical_id"),
            object_canonical_id=payload.get("object_canonical_id"),
            bm25_subject=payload.get("bm25_subject"),
            bm25_predicate=payload.get("bm25_predicate"),
            bm25_object=payload.get("bm25_object"),
        )

    @staticmethod
    def from_enriched_triplet(enriched: EnrichedTriplet) -> "ExtractedTriplet":
        """Project an ontology-enriched triplet into the cached consolidation surface."""
        return ExtractedTriplet(
            subject=enriched.subject,
            predicate=enriched.predicate,
            object=enriched.object,
            polarity=enriched.polarity,
            inference_type=enriched.inference_type,
            confidence=enriched.confidence,
            subject_canonical_id=CanonicalityRules.subject_canonical_id(enriched),
            predicate_canonical_id=CanonicalityRules.predicate_canonical_id(enriched),
            object_canonical_id=CanonicalityRules.object_canonical_id(enriched),
            bm25_subject=enriched.bm25_subject,
            bm25_predicate=enriched.bm25_predicate,
            bm25_object=enriched.bm25_object,
        )


@dataclass(frozen=True)
class SkillDerivation:
    """Cached derived surfaces for one skill."""

    name: str
    content_hash: str
    triplets: tuple[ExtractedTriplet, ...]
    canonical_triplets: tuple[tuple[str, str, str], ...]
    bm25_text: str
    triplet_sequence_text: str
    embedding_ref: str
    embedding_model: str
    embedding_vector: tuple[float, ...]
    markdown_files: tuple[str, ...]

    @staticmethod
    def from_triplets(
        document: SkillDocument,
        triplets: Iterable[ExtractedTriplet],
        embedding_model: str = "",
        embedding_vector: Iterable[float] = (),
    ) -> "SkillDerivation":
        """Build all derived surfaces from ordered triplets."""
        ordered_triplets = tuple(triplets)
        canonical_triplets = tuple(t.canonical_tuple() for t in ordered_triplets)
        bm25_text = f" {TRIPLET_SEPARATOR} ".join(
            fragment for fragment in (t.bm25_fragment() for t in ordered_triplets) if fragment
        )
        triplet_sequence_text = f" {TRIPLET_SEPARATOR} ".join(
            fragment for fragment in (t.sequence_fragment() for t in ordered_triplets) if fragment
        )
        embedding_vector_tuple = tuple(float(value) for value in embedding_vector)
        embedding_ref = content_hash(
            f"{embedding_model}\n{triplet_sequence_text}" if embedding_model else triplet_sequence_text
        )
        markdown_files = tuple(str(path.relative_to(document.folder)) for path in document.markdown_files)
        return SkillDerivation(
            name=document.name,
            content_hash=document.content_hash,
            triplets=ordered_triplets,
            canonical_triplets=canonical_triplets,
            bm25_text=bm25_text,
            triplet_sequence_text=triplet_sequence_text,
            embedding_ref=embedding_ref,
            embedding_model=embedding_model,
            embedding_vector=embedding_vector_tuple,
            markdown_files=markdown_files,
        )

    def to_row(self) -> tuple[str, str, str, str, str, str, str, str, str]:
        """Convert to SQLite row payload."""
        return (
            self.name,
            self.content_hash,
            json.dumps([triplet.to_dict() for triplet in self.triplets], ensure_ascii=True),
            json.dumps([list(item) for item in self.canonical_triplets], ensure_ascii=True),
            self.bm25_text,
            self.triplet_sequence_text,
            self.embedding_ref,
            self.embedding_model,
            json.dumps(list(self.embedding_vector), ensure_ascii=True),
        )

    @staticmethod
    def from_row(row: tuple) -> "SkillDerivation":
        """Rehydrate a cached derivation row."""
        (
            name,
            row_content_hash,
            triplets_json,
            canonical_json,
            bm25_text,
            triplet_sequence_text,
            embedding_ref,
            embedding_model,
            embedding_json,
        ) = row
        triplets = tuple(ExtractedTriplet.from_dict(item) for item in json.loads(triplets_json))
        canonical_triplets = tuple(tuple(item) for item in json.loads(canonical_json))
        return SkillDerivation(
            name=name,
            content_hash=row_content_hash,
            triplets=triplets,
            canonical_triplets=canonical_triplets,
            bm25_text=bm25_text,
            triplet_sequence_text=triplet_sequence_text,
            embedding_ref=embedding_ref or content_hash(triplet_sequence_text),
            embedding_model=embedding_model or "",
            embedding_vector=tuple(float(item) for item in json.loads(embedding_json or "[]")),
            markdown_files=tuple(),
        )


def strip_boilerplate(text: str) -> str:
    """Remove structural scaffolding that inflates shared vocabulary."""
    text = re.sub(r"^---.*?---\s*", "", text, flags=re.DOTALL)
    text = re.sub(r"^#{1,6}\s+.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\|.*\|$", "", text, flags=re.MULTILINE)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"^\s*[-*]\s*\*\*[^*]+\*\*\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def content_hash(text: str) -> str:
    """Hash content for checkpointing."""
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_phrase(text: str) -> str:
    """Normalize markdown-ish phrases into stable comparison strings."""
    normalized = text.lower()
    normalized = re.sub(r"\[\[([^\]]+)\]\]", r"\1", normalized)
    normalized = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", normalized)
    normalized = re.sub(r"`([^`]+)`", r"\1", normalized)
    normalized = re.sub(r"[_*#>\-\u2022]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def list_skill_files(root: Path) -> list[Path]:
    """Return canonical SKILL.md entrypoints for live skills."""
    return sorted(
        path
        for path in root.glob("*/SKILL.md")
        if "disabled" not in str(path)
    )


def ordered_markdown_files(skill_dir: Path) -> tuple[Path, ...]:
    """Return all markdown files under a skill folder in canonical order."""
    markdown_files = sorted(
        (path for path in skill_dir.rglob("*.md") if path.is_file()),
        key=lambda path: (
            0 if path.parent == skill_dir else 1,
            MARKDOWN_PRIORITY.get(path.name, 100),
            str(path.relative_to(skill_dir)).lower(),
        ),
    )
    return tuple(markdown_files)


def build_skill_documents(root: Path) -> list[SkillDocument]:
    """Assemble one atomic document per skill folder."""
    documents: list[SkillDocument] = []
    for skill_file in list_skill_files(root):
        folder = skill_file.parent
        markdown_files = ordered_markdown_files(folder)
        source_sections: list[str] = []
        derivation_sections: list[str] = []
        for markdown_file in markdown_files:
            rel_path = markdown_file.relative_to(folder).as_posix()
            text = markdown_file.read_text(encoding="utf-8", errors="ignore")
            source_sections.append(f"=== FILE: {rel_path} ===\n{text.strip()}")
            stripped = strip_boilerplate(text)
            if stripped:
                derivation_sections.append(f"=== FILE: {rel_path} ===\n{stripped}")

        source_text = "\n\n".join(source_sections).strip()
        derivation_text = "\n\n".join(derivation_sections).strip()
        documents.append(
            SkillDocument(
                name=folder.name,
                folder=folder,
                skill_file=skill_file,
                markdown_files=markdown_files,
                source_text=source_text,
                derivation_text=derivation_text,
                content_hash=content_hash(source_text),
            )
        )
    return documents


def call_chat_completion(base_url: str, model: str, api_key: str, prompt: str) -> str:
    """Call an OpenAI-compatible chat endpoint without the Python client wrapper."""
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "600"))
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": max_tokens,
        }
    )
    curl_bin = shutil.which("curl.exe") or shutil.which("curl")
    if not curl_bin:
        raise RuntimeError("curl is required for local LLM calls in this environment")

    result = subprocess.run(
        [
            curl_bin,
            "-sS",
            endpoint,
            "-H",
            "Content-Type: application/json",
            "-H",
            f"Authorization: Bearer {api_key}",
            "--data-binary",
            "@-",
        ],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "curl request failed")

    body = json.loads(result.stdout)

    choices = body.get("choices", [])
    if not choices:
        raise RuntimeError(f"LLM endpoint returned no choices: {body}")

    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, list):
        return "".join(part.get("text", "") for part in content if isinstance(part, dict)).strip()
    if not isinstance(content, str):
        raise RuntimeError(f"LLM endpoint returned unexpected content payload: {body}")
    return content.strip()


def call_embedding_completion(base_url: str, model: str, api_key: str, input_text: str) -> tuple[float, ...]:
    """Call an OpenAI-compatible embeddings endpoint through the stable curl transport."""
    endpoint = f"{base_url.rstrip('/')}/embeddings"
    payload = json.dumps({"model": model, "input": input_text})
    curl_bin = shutil.which("curl.exe") or shutil.which("curl")
    if not curl_bin:
        raise RuntimeError("curl is required for local embedding calls in this environment")

    result = subprocess.run(
        [
            curl_bin,
            "-sS",
            endpoint,
            "-H",
            "Content-Type: application/json",
            "-H",
            f"Authorization: Bearer {api_key}",
            "--data-binary",
            "@-",
        ],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "curl embedding request failed")

    body = json.loads(result.stdout)
    data = body.get("data", [])
    if not data or "embedding" not in data[0]:
        raise RuntimeError(f"Embedding endpoint returned unexpected payload: {body}")
    return tuple(float(value) for value in data[0]["embedding"])


def configured_models() -> tuple[str, ...]:
    """Return the ordered model fallback list for local LLM extraction."""
    model_list = os.environ.get("LLM_MODEL_LIST")
    if model_list:
        return tuple(model.strip() for model in model_list.split(",") if model.strip())
    ordered = [
        os.environ.get("LLM_MODEL", "qwen3.5:0.8b"),
        "qwen2.5-coder:1.5b",
        "qwen3.5:2b",
        "granite-1b:latest",
    ]
    return tuple(dict.fromkeys(model for model in ordered if model))


class OpenAITripletExtractor:
    """LLM-backed triplet extractor for whole-skill documents."""

    def __init__(self) -> None:
        self.base_url = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
        self.models = configured_models()
        self.api_key = os.environ.get("LLM_API_KEY", "ollama")

    def extract(self, document: SkillDocument) -> tuple[ExtractedTriplet, ...]:
        """Extract ordered atomic claims from one skill document."""
        prompt = TRIPLET_EXTRACTION_PROMPT.format(
            skill_name=document.name,
            document_text=document.derivation_text,
        )
        last_error: Exception | None = None
        payload: list[dict] | None = None
        for model in self.models:
            raw = call_chat_completion(
                base_url=self.base_url,
                model=model,
                api_key=self.api_key,
                prompt=prompt,
            )
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            try:
                payload = parse_triplet_payload(raw)
                break
            except ValueError as exc:
                last_error = exc
        if payload is None:
            raise last_error or ValueError("Triplet extractor returned no parseable JSON")
        return tuple(
            ExtractedTriplet(
                subject=item["subject"],
                predicate=item["predicate"],
                object=item["object"],
                polarity=item.get("polarity", "affirmed"),
                inference_type=item.get("inference_type", "observed"),
                confidence=float(item.get("confidence", 1.0)),
            )
            for item in payload
        )


class HeuristicSynsetSelector:
    """Deterministically select the top ontology candidate for each content word."""

    def select(
        self,
        triplets: list[dict],
        batch_result: BatchAugmentationResult,
    ) -> tuple[TripletWithChosenSynsets, ...]:
        """Build schema-valid synset choices without a second LLM round-trip."""
        chosen_triplets: list[TripletWithChosenSynsets] = []
        for triplet, augmented in zip(triplets, batch_result.augmented):
            chosen_triplets.append(build_triplet_with_choices(triplet, augmented, {}))
        return tuple(chosen_triplets)


class OpenAISynsetSelector:
    """Optional LLM refinement step for synset choice disambiguation."""

    def __init__(self) -> None:
        self.base_url = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
        self.models = configured_models()
        self.api_key = os.environ.get("LLM_API_KEY", "ollama")

    def select(
        self,
        triplets: list[dict],
        batch_result: BatchAugmentationResult,
    ) -> tuple[TripletWithChosenSynsets, ...]:
        """Ask the configured LLM to choose synsets from augmented candidates."""
        prompt = batch_result.to_llm_format()
        last_error: Exception | None = None
        selections: list[dict] | None = None
        for model in self.models:
            raw = call_chat_completion(
                base_url=self.base_url,
                model=model,
                api_key=self.api_key,
                prompt=prompt,
            )
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            try:
                selections = parse_synset_selection_payload(raw)
                break
            except ValueError as exc:
                last_error = exc
        if selections is None:
            raise last_error or ValueError("Synset selector returned no parseable JSON")
        selection_by_index = {
            int(item["triplet_index"]): item
            for item in selections
            if isinstance(item, dict) and "triplet_index" in item
        }
        chosen_triplets: list[TripletWithChosenSynsets] = []
        for index, (triplet, augmented) in enumerate(zip(triplets, batch_result.augmented)):
            selection = selection_by_index.get(index, {})
            chosen_triplets.append(build_triplet_with_choices(triplet, augmented, selection))
        return tuple(chosen_triplets)


class KgOntologySkillDeriver:
    """Whole-skill derivation through extraction, augmentation, and enrichment."""

    def __init__(
        self,
        extractor: OpenAITripletExtractor | None = None,
        selector: HeuristicSynsetSelector | OpenAISynsetSelector | None = None,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ) -> None:
        self.extractor = extractor or OpenAITripletExtractor()
        if selector is not None:
            self.selector = selector
        elif os.environ.get("KG_ONTOLOGY_LLM_SELECTION", "").lower() in {"1", "true", "yes"}:
            self.selector = OpenAISynsetSelector()
        else:
            self.selector = HeuristicSynsetSelector()
        self.orchestrator = BatchSynsetOrchestrator(word2vec_model=None, k_neighbors=5)
        self.base_url = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
        self.api_key = os.environ.get("LLM_API_KEY", "ollama")
        self.embedding_model = embedding_model

    def derive(self, document: SkillDocument) -> SkillDerivation:
        """Run the ontology-backed derivation pipeline for one skill document."""
        extracted_triplets = self.extractor.extract(document)
        if not extracted_triplets:
            return SkillDerivation.from_triplets(document, (), embedding_model=self.embedding_model)

        extracted_payload = [triplet.to_extracted_dict() for triplet in extracted_triplets]
        batch_result = self.orchestrator.augment_batch(extracted_payload)
        chosen_triplets = self.selector.select(extracted_payload, batch_result)
        enriched_batch = self.orchestrator.enrich_batch(batch_result, list(chosen_triplets))
        enriched_triplets = tuple(
            ExtractedTriplet.from_enriched_triplet(triplet)
            for triplet in enriched_batch.enriched_triplets
        )
        provisional = SkillDerivation.from_triplets(
            document,
            enriched_triplets,
            embedding_model=self.embedding_model,
        )
        embedding_vector = call_embedding_completion(
            base_url=self.base_url,
            model=self.embedding_model,
            api_key=self.api_key,
            input_text=provisional.triplet_sequence_text,
        )
        return SkillDerivation.from_triplets(
            document,
            enriched_triplets,
            embedding_model=self.embedding_model,
            embedding_vector=embedding_vector,
        )


def parse_triplet_payload(raw: str) -> list[dict]:
    """Parse the extractor JSON response into a list of dict triplets."""
    parsed = decode_first_json_value(raw)
    if parsed is None:
        raise ValueError(f"Triplet extractor returned no parseable JSON: {raw[:400]}")

    if isinstance(parsed, list):
        payload = parsed
    else:
        if isinstance(parsed, dict) and {"subject", "predicate", "object"}.issubset(parsed):
            payload = [parsed]
        elif "triplets" in parsed and isinstance(parsed["triplets"], list):
            payload = parsed["triplets"]
        else:
            raise ValueError(f"Triplet extractor returned unexpected schema: {raw[:400]}")

    if not isinstance(payload, list):
        raise ValueError("Triplet extractor payload must be a JSON array")

    required = {"subject", "predicate", "object"}
    sanitized: list[dict] = []
    for item in payload:
        if not isinstance(item, dict) or not required.issubset(item):
            raise ValueError(f"Triplet extractor item missing required fields: {item}")
        subject = str(item["subject"]).strip()
        predicate = str(item["predicate"]).strip()
        obj = str(item["object"]).strip()
        if not normalize_phrase(subject) or not normalize_phrase(predicate) or not normalize_phrase(obj):
            continue
        sanitized.append(
            {
                **item,
                "subject": subject,
                "predicate": predicate,
                "object": obj,
            }
        )
    return sanitized


def parse_synset_selection_payload(raw: str) -> list[dict]:
    """Parse the synset selector response into a list of per-triplet selections."""
    parsed = decode_first_json_value(raw)
    if parsed is None:
        raise ValueError(f"Synset selector returned no parseable JSON array: {raw[:400]}")
    payload = parsed
    if not isinstance(payload, list):
        raise ValueError("Synset selector payload must be a JSON array")
    return payload


def decode_first_json_value(raw: str) -> object | None:
    """Decode the first JSON object or array from a noisy model response."""
    decoder = json.JSONDecoder()
    for start_index, character in enumerate(raw):
        if character not in "[{":
            continue
        try:
            parsed, _ = decoder.raw_decode(raw[start_index:])
            return parsed
        except json.JSONDecodeError:
            continue
    return None


def surface_synset_id(word: str) -> str:
    """Generate a stable fallback identifier when WordNet candidates are unavailable."""
    return f"surface::{normalize_phrase(word).replace(' ', '_')}"


def select_word_choice(word_option: dict, chosen_synsets: dict, chosen_hypernyms: dict) -> tuple[str, list[str]]:
    """Select the chosen candidate for one word, falling back to the top ontology option."""
    word = word_option["word"]
    selected_synset = chosen_synsets.get(word)
    selected_chain = chosen_hypernyms.get(word)
    if selected_synset:
        if isinstance(selected_chain, list) and selected_chain:
            return selected_synset, [item for item in selected_chain if item]
        return selected_synset, [selected_synset]

    synset_options = word_option.get("synset_options", [])
    if synset_options:
        fallback = synset_options[0]
        fallback_chain = [item for item in fallback.get("hypernym_chain", []) if item]
        if fallback_chain:
            return fallback_chain[0], fallback_chain

    fallback_id = surface_synset_id(word)
    return fallback_id, [fallback_id]


def build_element_choices(element_text: str, element_augmented: dict, prefix: str, selection: dict) -> ElementSynsetChoices:
    """Build one element's chosen-synset schema from LLM or heuristic selections."""
    chosen_synsets_payload = selection.get(f"{prefix}_chosen_synsets", {})
    chosen_hypernyms_payload = selection.get(f"{prefix}_chosen_hypernyms", {})
    chosen_synsets: dict[str, str] = {}
    chosen_hypernyms: dict[str, list[str]] = {}

    for word_option in element_augmented.get("word_options", []):
        synset_id, hypernym_chain = select_word_choice(
            word_option,
            chosen_synsets_payload if isinstance(chosen_synsets_payload, dict) else {},
            chosen_hypernyms_payload if isinstance(chosen_hypernyms_payload, dict) else {},
        )
        chosen_synsets[word_option["word"]] = synset_id
        chosen_hypernyms[word_option["word"]] = hypernym_chain

    if not chosen_synsets and element_text.strip():
        fallback_word = normalize_phrase(element_text) or element_text.strip()
        fallback_id = surface_synset_id(fallback_word)
        chosen_synsets[fallback_word] = fallback_id
        chosen_hypernyms[fallback_word] = [fallback_id]

    return ElementSynsetChoices(
        element_text=element_text,
        chosen_synsets=chosen_synsets,
        chosen_hypernyms=chosen_hypernyms,
    )


def build_triplet_with_choices(
    triplet: dict,
    augmented: dict,
    selection: dict,
) -> TripletWithChosenSynsets:
    """Combine extracted triplet text with chosen or heuristic ontology selections."""
    return TripletWithChosenSynsets(
        subject=triplet["subject"],
        subject_choices=build_element_choices(
            triplet["subject"],
            augmented.get("subject") or {"word_options": []},
            "subject",
            selection,
        ),
        predicate=triplet["predicate"],
        predicate_choices=build_element_choices(
            triplet["predicate"],
            augmented.get("predicate") or {"word_options": []},
            "predicate",
            selection,
        ),
        object=triplet["object"],
        object_choices=build_element_choices(
            triplet["object"],
            augmented.get("object") or {"word_options": []},
            "object",
            selection,
        ),
        polarity=triplet.get("polarity", "affirmed"),
        inference_type=triplet.get("inference_type", "observed"),
    )


def ensure_derivation_tables(db_path: Path) -> None:
    """Create derivation cache tables if they do not exist."""
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS skill_derivations (
                skill_name            TEXT PRIMARY KEY,
                content_hash          TEXT NOT NULL,
                triplets_json         TEXT NOT NULL,
                canonical_triplets_json TEXT NOT NULL,
                bm25_text             TEXT NOT NULL,
                triplet_sequence_text TEXT NOT NULL,
                embedding_ref         TEXT NOT NULL DEFAULT '',
                embedding_model       TEXT NOT NULL DEFAULT '',
                embedding_json        TEXT NOT NULL DEFAULT '[]'
            )
            """
        )
        existing_columns = {
            row[1] for row in con.execute("PRAGMA table_info(skill_derivations)").fetchall()
        }
        for column_name, column_def in (
            ("embedding_ref", "TEXT NOT NULL DEFAULT ''"),
            ("embedding_model", "TEXT NOT NULL DEFAULT ''"),
            ("embedding_json", "TEXT NOT NULL DEFAULT '[]'"),
        ):
            if column_name not in existing_columns:
                con.execute(f"ALTER TABLE skill_derivations ADD COLUMN {column_name} {column_def}")
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS pairwise_similarity (
                doc_a        TEXT NOT NULL,
                doc_b        TEXT NOT NULL,
                score        REAL NOT NULL,
                sparse_score REAL NOT NULL DEFAULT 0.0,
                dense_score  REAL NOT NULL DEFAULT 0.0,
                overlap_size INTEGER NOT NULL,
                union_size   INTEGER NOT NULL,
                PRIMARY KEY (doc_a, doc_b)
            )
            """
        )
        pairwise_columns = {
            row[1] for row in con.execute("PRAGMA table_info(pairwise_similarity)").fetchall()
        }
        for column_name, column_def in (
            ("sparse_score", "REAL NOT NULL DEFAULT 0.0"),
            ("dense_score", "REAL NOT NULL DEFAULT 0.0"),
        ):
            if column_name not in pairwise_columns:
                con.execute(f"ALTER TABLE pairwise_similarity ADD COLUMN {column_name} {column_def}")
        con.commit()
    finally:
        con.close()


def load_cached_derivations(db_path: Path) -> dict[str, SkillDerivation]:
    """Load cached derivations keyed by skill name."""
    if not db_path.exists():
        return {}
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            """
            SELECT skill_name, content_hash, triplets_json, canonical_triplets_json,
                   bm25_text, triplet_sequence_text, embedding_ref, embedding_model, embedding_json
            FROM skill_derivations
            """
        ).fetchall()
        return {row[0]: SkillDerivation.from_row(row) for row in rows}
    except sqlite3.OperationalError:
        return {}
    finally:
        con.close()


def save_derivations(db_path: Path, derivations: Iterable[SkillDerivation]) -> None:
    """Persist derivation cache rows."""
    ensure_derivation_tables(db_path)
    con = sqlite3.connect(db_path)
    try:
        con.executemany(
            """
            INSERT OR REPLACE INTO skill_derivations
            (
                skill_name,
                content_hash,
                triplets_json,
                canonical_triplets_json,
                bm25_text,
                triplet_sequence_text,
                embedding_ref,
                embedding_model,
                embedding_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [derivation.to_row() for derivation in derivations],
        )
        con.commit()
    finally:
        con.close()


def derive_skill_corpus(
    documents: list[SkillDocument],
    db_path: Path,
    extractor: OpenAITripletExtractor | None = None,
    deriver: KgOntologySkillDeriver | None = None,
) -> list[SkillDerivation]:
    """Derive or load cached surfaces for each whole-skill document."""
    ensure_derivation_tables(db_path)
    cached = load_cached_derivations(db_path)
    deriver = deriver or KgOntologySkillDeriver(extractor=extractor)
    derivations: list[SkillDerivation] = []

    for index, document in enumerate(documents, start=1):
        cached_item = cached.get(document.name)
        if (
            cached_item
            and cached_item.content_hash == document.content_hash
            and cached_item.embedding_vector
        ):
            print(f"[{index}/{len(documents)}] cache hit  {document.name}")
            derivations.append(cached_item)
            continue

        derivation = deriver.derive(document)
        print(f"[{index}/{len(documents)}] derived    {document.name}  triplets={len(derivation.triplets)}")
        derivations.append(derivation)
        save_derivations(db_path, [derivation])
    return derivations


def triplet_jaccard(left: SkillDerivation, right: SkillDerivation) -> tuple[float, int, int]:
    """Compute hard Jaccard overlap over canonical triplet sets."""
    left_set = set(left.canonical_triplets)
    right_set = set(right.canonical_triplets)
    union = left_set | right_set
    if not union:
        return 0.0, 0, 0
    overlap = left_set & right_set
    return len(overlap) / len(union), len(overlap), len(union)


def dense_cosine_similarity(left: SkillDerivation, right: SkillDerivation) -> float:
    """Compute cosine similarity over persisted triplet-sequence embeddings."""
    if not left.embedding_vector or not right.embedding_vector:
        return 0.0
    left_vec = np.array(left.embedding_vector, dtype=float)
    right_vec = np.array(right.embedding_vector, dtype=float)
    left_norm = np.linalg.norm(left_vec)
    right_norm = np.linalg.norm(right_vec)
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    cosine = float(np.dot(left_vec, right_vec) / (left_norm * right_norm))
    return max(min(cosine, 1.0), -1.0)


def fuse_similarity(sparse_score: float, dense_score: float, use_dense: bool) -> float:
    """Blend sparse and dense similarity explicitly."""
    if not use_dense:
        return sparse_score
    return (SPARSE_SIMILARITY_WEIGHT * sparse_score) + (DENSE_SIMILARITY_WEIGHT * dense_score)


def build_similarity_matrix(
    documents: list[SkillDocument],
    derivations: list[SkillDerivation],
    db_path: Path | None = None,
) -> np.ndarray:
    """Build the pairwise whole-skill similarity matrix from triplet Jaccard."""
    N = len(documents)
    M = np.zeros((N, N), dtype=float)
    rows: list[tuple[str, str, float, float, float, int, int]] = []

    for i in range(N):
        for j in range(i + 1, N):
            sparse_score, overlap_size, union_size = triplet_jaccard(derivations[i], derivations[j])
            dense_score = dense_cosine_similarity(derivations[i], derivations[j])
            fusion_score = fuse_similarity(
                sparse_score,
                dense_score,
                use_dense=bool(derivations[i].embedding_vector and derivations[j].embedding_vector),
            )
            M[i, j] = fusion_score
            M[j, i] = fusion_score
            rows.append(
                (
                    documents[i].name,
                    documents[j].name,
                    fusion_score,
                    sparse_score,
                    dense_score,
                    overlap_size,
                    union_size,
                )
            )

    if db_path is not None:
        ensure_derivation_tables(db_path)
        con = sqlite3.connect(db_path)
        try:
            con.execute("DELETE FROM pairwise_similarity")
            con.executemany(
                """
                INSERT INTO pairwise_similarity (
                    doc_a,
                    doc_b,
                    score,
                    sparse_score,
                    dense_score,
                    overlap_size,
                    union_size
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            con.commit()
        finally:
            con.close()

    return M
