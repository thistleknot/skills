"""
Tests for the whole-skill consolidation backend.
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from skill_similarity import (
    DENSE_SIMILARITY_WEIGHT,
    ExtractedTriplet,
    OpenAITripletExtractor,
    SkillDerivation,
    SkillDocument,
    build_similarity_matrix,
    build_skill_documents,
    build_triplet_with_choices,
    derive_skill_corpus,
    load_cached_derivations,
    save_derivations,
)


def write_file(path: Path, text: str) -> None:
    """Create a test markdown file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_build_skill_documents_concatenates_all_markdown_in_canonical_order(tmp_path: Path) -> None:
    """All markdown under one skill folder should be included deterministically."""
    skill_dir = tmp_path / "alpha"
    write_file(skill_dir / "SKILL.md", "# Skill\nMain body")
    write_file(skill_dir / "DESCRIPTION.md", "# Desc\nSecondary body")
    write_file(skill_dir / "notes.md", "Loose notes")
    write_file(skill_dir / "references" / "ref.md", "Nested reference")

    documents = build_skill_documents(tmp_path)

    assert len(documents) == 1
    document = documents[0]
    assert document.name == "alpha"
    assert [path.relative_to(skill_dir).as_posix() for path in document.markdown_files] == [
        "SKILL.md",
        "DESCRIPTION.md",
        "notes.md",
        "references/ref.md",
    ]
    assert "=== FILE: SKILL.md ===" in document.source_text
    assert "=== FILE: references/ref.md ===" in document.source_text


def test_build_similarity_matrix_uses_triplet_jaccard(tmp_path: Path) -> None:
    """Similarity should be driven by canonical triplet overlap, not TF-IDF."""
    left_doc = SkillDocument(
        name="left",
        folder=tmp_path / "left",
        skill_file=tmp_path / "left" / "SKILL.md",
        markdown_files=tuple(),
        source_text="left",
        derivation_text="left",
        content_hash="left-hash",
    )
    right_doc = SkillDocument(
        name="right",
        folder=tmp_path / "right",
        skill_file=tmp_path / "right" / "SKILL.md",
        markdown_files=tuple(),
        source_text="right",
        derivation_text="right",
        content_hash="right-hash",
    )

    left = SkillDerivation.from_triplets(
        left_doc,
        [
            ExtractedTriplet("skill", "owns", "memory"),
            ExtractedTriplet("skill", "uses", "graph"),
        ],
    )
    right = SkillDerivation.from_triplets(
        right_doc,
        [
            ExtractedTriplet("skill", "owns", "memory"),
            ExtractedTriplet("skill", "routes", "tasks"),
        ],
    )

    db_path = tmp_path / ".checkpoint.db"
    matrix = build_similarity_matrix([left_doc, right_doc], [left, right], db_path=db_path)

    assert matrix.shape == (2, 2)
    assert np.isclose(matrix[0, 1], 1.0 / 3.0)
    assert np.isclose(matrix[1, 0], 1.0 / 3.0)

    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            "SELECT score, overlap_size, union_size FROM pairwise_similarity WHERE doc_a = 'left' AND doc_b = 'right'"
        ).fetchone()
    finally:
        con.close()

    assert row == (1.0 / 3.0, 1, 3)


def test_derivation_cache_round_trip(tmp_path: Path) -> None:
    """Derived triplets should round-trip through SQLite cache storage."""
    derivation = SkillDerivation(
        name="alpha",
        content_hash="hash-1",
        triplets=(
            ExtractedTriplet("alpha", "owns", "graph", confidence=0.9),
            ExtractedTriplet("alpha", "uses", "bm25"),
        ),
        canonical_triplets=(
            ("alpha", "owns", "graph"),
            ("alpha", "uses", "bm25"),
        ),
        bm25_text="alpha owns graph SEP alpha uses bm25",
        triplet_sequence_text="alpha | owns | graph SEP alpha | uses | bm25",
        embedding_ref="embed-alpha",
        embedding_model="nomic-embed-text:latest",
        embedding_vector=(0.1, 0.2, 0.3),
        markdown_files=("SKILL.md", "DESCRIPTION.md"),
    )

    db_path = tmp_path / ".checkpoint.db"
    save_derivations(db_path, [derivation])
    cached = load_cached_derivations(db_path)

    assert "alpha" in cached
    restored = cached["alpha"]
    assert restored.content_hash == "hash-1"
    assert restored.triplets[0].subject == "alpha"
    assert restored.triplets[0].confidence == 0.9
    assert restored.canonical_triplets[1] == ("alpha", "uses", "bm25")
    assert restored.embedding_ref == "embed-alpha"
    assert restored.embedding_vector == (0.1, 0.2, 0.3)


def test_ontology_projection_uses_synsets_and_surface_fallbacks() -> None:
    """Ontology-enriched triplets should cache canonical IDs and BM25 surfaces."""
    from kg_ontology.triplet_enrichment import TripletEnricher

    triplet = {
        "subject": "skill",
        "predicate": "links",
        "object": "memory",
        "polarity": "affirmed",
        "inference_type": "observed",
    }
    augmented = {
        "subject": {
            "word_options": [
                {
                    "word": "skill",
                    "synset_options": [
                        {"synset": "skill.n.01", "hypernym_chain": ["skill.n.01", "ability.n.01"]}
                    ],
                }
            ]
        },
        "predicate": {
            "word_options": [
                {
                    "word": "links",
                    "synset_options": [
                        {"synset": "connect.v.01", "hypernym_chain": ["connect.v.01", "relate.v.01"]}
                    ],
                }
            ]
        },
        "object": {"word_options": [{"word": "memory", "synset_options": []}]},
    }

    chosen = build_triplet_with_choices(triplet, augmented, {})
    enriched = TripletEnricher.enrich_from_llm_response(triplet, chosen)
    projected = ExtractedTriplet.from_enriched_triplet(enriched)

    assert projected.subject_canonical_id == "skill.n.01"
    assert projected.predicate_canonical_id == "connect.v.01"
    assert projected.object_canonical_id == "surface::memory"
    assert projected.bm25_subject == "skill.n.01 ability.n.01"
    assert projected.sequence_fragment() == "skill.n.01 | connect.v.01 | surface::memory"


def test_build_similarity_matrix_blends_dense_embeddings_when_present(tmp_path: Path) -> None:
    """Dense similarity should contribute when triplet-sequence embeddings are present."""
    left_doc = SkillDocument(
        name="left",
        folder=tmp_path / "left",
        skill_file=tmp_path / "left" / "SKILL.md",
        markdown_files=tuple(),
        source_text="left",
        derivation_text="left",
        content_hash="left-hash",
    )
    right_doc = SkillDocument(
        name="right",
        folder=tmp_path / "right",
        skill_file=tmp_path / "right" / "SKILL.md",
        markdown_files=tuple(),
        source_text="right",
        derivation_text="right",
        content_hash="right-hash",
    )

    left = SkillDerivation(
        name="left",
        content_hash="left-hash",
        triplets=(ExtractedTriplet("alpha", "owns", "graph"),),
        canonical_triplets=(("alpha", "owns", "graph"),),
        bm25_text="alpha owns graph",
        triplet_sequence_text="alpha | owns | graph",
        embedding_ref="left-embed",
        embedding_model="nomic-embed-text:latest",
        embedding_vector=(1.0, 0.0),
        markdown_files=tuple(),
    )
    right = SkillDerivation(
        name="right",
        content_hash="right-hash",
        triplets=(ExtractedTriplet("beta", "uses", "memory"),),
        canonical_triplets=(("beta", "uses", "memory"),),
        bm25_text="beta uses memory",
        triplet_sequence_text="beta | uses | memory",
        embedding_ref="right-embed",
        embedding_model="nomic-embed-text:latest",
        embedding_vector=(1.0, 0.0),
        markdown_files=tuple(),
    )

    db_path = tmp_path / ".checkpoint.db"
    matrix = build_similarity_matrix([left_doc, right_doc], [left, right], db_path=db_path)

    assert np.isclose(matrix[0, 1], DENSE_SIMILARITY_WEIGHT)

    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            "SELECT score, sparse_score, dense_score FROM pairwise_similarity WHERE doc_a = 'left' AND doc_b = 'right'"
        ).fetchone()
    finally:
        con.close()

    assert row == (DENSE_SIMILARITY_WEIGHT, 0.0, 1.0)


def test_triplet_extractor_skips_runtime_error_and_uses_next_model(monkeypatch) -> None:
    """Missing or broken fallback models should not abort extraction if a later model works."""
    calls: list[str] = []

    def fake_call_chat_completion(base_url: str, model: str, api_key: str, prompt: str) -> str:
        calls.append(model)
        if model == "missing-model":
            raise RuntimeError("model not found")
        return '[{"subject":"skill","predicate":"uses","object":"memory"}]'

    monkeypatch.setattr("skill_similarity.call_chat_completion", fake_call_chat_completion)

    extractor = OpenAITripletExtractor()
    extractor.models = ("missing-model", "working-model")
    document = SkillDocument(
        name="alpha",
        folder=Path("."),
        skill_file=Path("SKILL.md"),
        markdown_files=tuple(),
        source_text="alpha",
        derivation_text="alpha",
        content_hash="alpha-hash",
    )

    triplets = extractor.extract(document)

    assert calls == ["missing-model", "working-model"]
    assert triplets[0].subject == "skill"


def test_call_embedding_completion_accepts_ollama_embedding_shape(monkeypatch) -> None:
    """The embedding client should accept Ollama native payloads as well as OpenAI-style data."""
    payload = '{"embedding":[0.1,0.2,0.3]}'

    monkeypatch.setattr(
        "skill_similarity.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, stdout=payload, stderr=""),
    )

    from skill_similarity import call_embedding_completion

    embedding = call_embedding_completion(
        base_url="http://localhost:11434/api",
        model="nomic-embed-text:latest",
        api_key="ollama",
        input_text="hello world",
    )

    assert embedding == (0.1, 0.2, 0.3)


def test_call_chat_completion_uses_reasoning_when_content_is_empty(monkeypatch) -> None:
    """Reasoning-only Ollama responses should still surface usable model text."""
    payload = (
        '{"choices":[{"message":{"content":"","reasoning":"'
        '[{\\"subject\\":\\"skill\\",\\"predicate\\":\\"uses\\",\\"object\\":\\"memory\\"}]'
        '"}}]}'
    )

    monkeypatch.setattr(
        "skill_similarity.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, stdout=payload, stderr=""),
    )

    from skill_similarity import call_chat_completion

    raw = call_chat_completion(
        base_url="http://localhost:11434/v1",
        model="qwen3.5:0.8b",
        api_key="ollama",
        prompt="extract claims",
    )

    assert raw.startswith('[{"subject":"skill"')


def test_parse_triplet_payload_skips_malformed_items() -> None:
    """One bad triplet should not discard the entire extraction payload."""
    from skill_similarity import parse_triplet_payload

    payload = """
    [
      {"subject": "skill", "predicate": "uses", "object": "memory"},
      {"subject": "broken", "predicate": "misses object"},
      {"subject": "tool", "predicate": "writes", "object": "report"}
    ]
    """

    parsed = parse_triplet_payload(payload)

    assert len(parsed) == 2
    assert parsed[0]["subject"] == "skill"
    assert parsed[1]["object"] == "report"


def test_derive_skill_corpus_continues_after_per_skill_failure(tmp_path: Path) -> None:
    """One extraction failure should degrade that skill to an empty singleton, not abort the run."""

    class StubDeriver:
        embedding_model = "nomic-embed-text:latest"

        def derive(self, document: SkillDocument) -> SkillDerivation:
            if document.name == "broken":
                raise ValueError("no parseable JSON")
            return SkillDerivation.from_triplets(
                document,
                [ExtractedTriplet("skill", "uses", "memory")],
                embedding_model=self.embedding_model,
                embedding_vector=(0.1, 0.2),
            )

    broken = SkillDocument(
        name="broken",
        folder=tmp_path / "broken",
        skill_file=tmp_path / "broken" / "SKILL.md",
        markdown_files=tuple(),
        source_text="broken",
        derivation_text="broken",
        content_hash="broken-hash",
    )
    working = SkillDocument(
        name="working",
        folder=tmp_path / "working",
        skill_file=tmp_path / "working" / "SKILL.md",
        markdown_files=tuple(),
        source_text="working",
        derivation_text="working",
        content_hash="working-hash",
    )

    derivations = derive_skill_corpus(
        [broken, working],
        db_path=tmp_path / ".checkpoint.db",
        deriver=StubDeriver(),
    )

    assert len(derivations) == 2
    assert derivations[0].name == "broken"
    assert derivations[0].triplets == ()
    assert derivations[1].name == "working"
    assert derivations[1].triplets[0].object == "memory"
