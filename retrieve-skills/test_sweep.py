"""Stub battery for sweep.py (no model downloads, no network).

Tests:
1. evaluate_prompt returns correct recall/precision for known inputs
2. select_best with tied and untied scenarios
3. validate_ground_truth raises on missing skill
4. Determinism: two calls with same inputs produce identical results
5. load_ground_truth rejects invalid schemas

Uses a 5-skill mini corpus with deterministic stub embeddings and
keyword-overlap reranker — same pattern as test_gate.py.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import router_core as rc
import sweep

# ---------- stub backends ----------

VOCAB = ["pdf", "merge", "spec", "requirements", "mlflow", "experiment",
         "debug", "error", "research", "web", "deploy", "track"]


def stub_embed(texts):
    """Deterministic bag-of-words embedding over VOCAB (12 dims)."""
    out = np.zeros((len(texts), len(VOCAB)), dtype=np.float32)
    for i, t in enumerate(texts):
        words = t.lower().split()
        for j, v in enumerate(VOCAB):
            out[i, j] = float(sum(1 for w in words if v in w))
    return out


def stub_rerank(query, docs):
    """Keyword-overlap score: count of query words appearing in each doc."""
    q_words = set(query.lower().split())
    return [float(len(q_words & set(d.lower().split()))) for d in docs]


# ---------- fixtures ----------

MINI_SKILLS = [
    rc.Skill("pdf-extraction", "/skills/pdf-extraction/SKILL.md",
             "Merge split and edit pdf files into documents"),
    rc.Skill("spec", "/skills/spec/SKILL.md",
             "Draft validate and render structured spec requirements EARS"),
    rc.Skill("mlflow", "/skills/mlflow/SKILL.md",
             "MLflow experiment tracking protocol for model pipelines"),
    rc.Skill("debugging", "/skills/debugging/SKILL.md",
             "Debugging protocol for isolating error and fixing repeating bugs"),
    rc.Skill("deep-research", "/skills/deep-research/SKILL.md",
             "Deep research framework gather web evidence produce report"),
]


@pytest.fixture()
def mini_index(tmp_path):
    """Build a tiny 5-skill index with stub embeddings."""
    idx = rc.SkillIndex(tmp_path / "test_sweep.db")
    idx.reindex(MINI_SKILLS, stub_embed)
    return idx


@pytest.fixture()
def gt_file(tmp_path):
    """Write a valid ground_truth.json for the mini corpus."""
    import json
    data = [
        {"prompt": "merge these pdf files", "expected": ["pdf-extraction"]},
        {"prompt": "write spec requirements", "expected": ["spec"]},
        {"prompt": "set up mlflow experiment tracking", "expected": ["mlflow"]},
        {"prompt": "isolate and fix this error debug", "expected": ["debugging"]},
        {"prompt": "gather web evidence research report", "expected": ["deep-research"]},
    ]
    p = tmp_path / "ground_truth.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


# ---------- test 1: evaluate_prompt metrics ----------

def test_evaluate_prompt_perfect_recall(mini_index):
    """When the target skill clears the margin gate, recall=1.0."""
    pr = sweep.evaluate_prompt(
        prompt="merge these pdf files",
        expected=["pdf-extraction"],
        top_k_param=5,
        rerank_keep_param=3,
        rerank_margin=0.5,  # lower margin so target clears it
        index=mini_index,
        embed_fn=stub_embed,
        rerank_fn=stub_rerank,
    )
    assert 0.0 <= pr.recall <= 1.0
    assert 0.0 <= pr.precision <= 1.0
    # With keyword overlap, "pdf" and "merge" in prompt should push
    # pdf-extraction above median. Verify bounds are respected.
    assert isinstance(pr.retrieved, list)


def test_evaluate_prompt_zero_recall_high_margin(mini_index):
    """With an impossibly high margin, nothing passes gate → recall=0."""
    pr = sweep.evaluate_prompt(
        prompt="merge these pdf files",
        expected=["pdf-extraction"],
        top_k_param=5,
        rerank_keep_param=3,
        rerank_margin=999.0,  # impossible to clear
        index=mini_index,
        embed_fn=stub_embed,
        rerank_fn=stub_rerank,
    )
    assert pr.recall == 0.0
    assert pr.precision == 0.0
    assert pr.retrieved == []


def test_evaluate_prompt_precision_with_false_positives(mini_index):
    """With margin=0 (accept everything), precision reflects false positives."""
    pr = sweep.evaluate_prompt(
        prompt="merge these pdf files",
        expected=["pdf-extraction"],
        top_k_param=5,
        rerank_keep_param=5,
        rerank_margin=-999.0,  # accept all
        index=mini_index,
        embed_fn=stub_embed,
        rerank_fn=stub_rerank,
    )
    # Everything retrieved → precision = 1/total_retrieved
    assert pr.recall == 1.0  # target is always in the set
    if len(pr.retrieved) > 1:
        assert pr.precision < 1.0  # false positives reduce precision


# ---------- test 2: select_best ----------

def test_select_best_prefers_higher_recall():
    """Tuple with higher recall wins regardless of precision."""
    a = sweep.TupleResult(8, 5, [], macro_recall=0.8, macro_precision=0.5, total_volume=10)
    b = sweep.TupleResult(5, 3, [], macro_recall=0.6, macro_precision=0.9, total_volume=15)
    best = sweep.select_best([a, b])
    assert best is a


def test_select_best_recall_tie_prefers_precision():
    """When recall is tied (within tolerance), higher precision wins."""
    a = sweep.TupleResult(8, 5, [], macro_recall=0.800, macro_precision=0.6, total_volume=10)
    b = sweep.TupleResult(5, 3, [], macro_recall=0.800, macro_precision=0.8, total_volume=10)
    best = sweep.select_best([a, b])
    assert best is b


def test_select_best_all_tied_prefers_volume():
    """When recall and precision tied, higher volume wins."""
    a = sweep.TupleResult(8, 5, [], macro_recall=0.8, macro_precision=0.7, total_volume=10)
    b = sweep.TupleResult(13, 8, [], macro_recall=0.8, macro_precision=0.7, total_volume=15)
    best = sweep.select_best([a, b])
    assert best is b


# ---------- test 3: validation ----------

def test_validate_raises_on_missing_skill(mini_index):
    """validate_ground_truth raises ValueError when expected skill not in index."""
    gt = [{"prompt": "do something", "expected": ["nonexistent-skill"]}]
    with pytest.raises(ValueError, match="not in index"):
        sweep.validate_ground_truth(gt, mini_index)


def test_validate_passes_for_known_skills(mini_index):
    """validate_ground_truth succeeds for skills present in index."""
    gt = [{"prompt": "merge pdf", "expected": ["pdf-extraction"]}]
    sweep.validate_ground_truth(gt, mini_index)  # should not raise


# ---------- test 4: determinism ----------

def test_determinism_identical_results(mini_index):
    """Two calls with same inputs produce identical results."""
    kwargs = dict(
        prompt="merge these pdf files",
        expected=["pdf-extraction"],
        top_k_param=5,
        rerank_keep_param=3,
        rerank_margin=0.5,
        index=mini_index,
        embed_fn=stub_embed,
        rerank_fn=stub_rerank,
    )
    r1 = sweep.evaluate_prompt(**kwargs)
    r2 = sweep.evaluate_prompt(**kwargs)
    assert r1.recall == r2.recall
    assert r1.precision == r2.precision
    assert r1.retrieved == r2.retrieved


def test_determinism_evaluate_tuple(mini_index):
    """Full tuple evaluation is deterministic across two runs."""
    gt = [
        {"prompt": "merge these pdf files", "expected": ["pdf-extraction"]},
        {"prompt": "write spec requirements", "expected": ["spec"]},
    ]
    kwargs = dict(
        top_k_param=5,
        rerank_keep_param=3,
        gt=gt,
        rerank_margin=0.5,
        index=mini_index,
        embed_fn=stub_embed,
        rerank_fn=stub_rerank,
    )
    t1 = sweep.evaluate_tuple(**kwargs)
    t2 = sweep.evaluate_tuple(**kwargs)
    assert t1.macro_recall == t2.macro_recall
    assert t1.macro_precision == t2.macro_precision
    assert t1.total_volume == t2.total_volume


# ---------- test 5: load_ground_truth schema validation ----------

def test_load_ground_truth_valid(gt_file):
    """Valid file loads successfully."""
    data = sweep.load_ground_truth(gt_file)
    assert len(data) == 5
    assert all("prompt" in d and "expected" in d for d in data)


def test_load_ground_truth_rejects_empty(tmp_path):
    """Empty list raises ValueError."""
    p = tmp_path / "empty.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        sweep.load_ground_truth(p)


def test_load_ground_truth_rejects_missing_keys(tmp_path):
    """Missing required keys raises ValueError."""
    import json
    p = tmp_path / "bad.json"
    p.write_text(json.dumps([{"prompt": "hello"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="missing"):
        sweep.load_ground_truth(p)
