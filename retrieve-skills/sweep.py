"""Cross-validation sweep for (top_k, rerank_keep) hyperparameters.

Usage: python sweep.py [--ground-truth PATH] [--db PATH] [--store PATH] [--margin FLOAT]
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import model_backends as mb
import router_core as rc

CANDIDATE_TUPLES: list[tuple[int, int]] = [(144, 89), (89, 55), (55, 34), (34, 21)]


@dataclass
class PromptResult:
    prompt: str
    expected: list[str]
    retrieved: list[str]
    recall: float
    precision: float


@dataclass
class TupleResult:
    top_k: int
    rerank_keep: int
    prompt_results: list[PromptResult]
    macro_recall: float
    macro_precision: float
    total_volume: int


def load_ground_truth(path: Path) -> list[dict]:
    """Load and parse ground_truth.json. Returns list of {prompt, expected}."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list) or not data:
        raise ValueError(f"ground_truth.json must be a non-empty list, got: {type(data)}")
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Item {i} is not a dict")
        if "prompt" not in item or "expected" not in item:
            raise ValueError(f"Item {i} missing 'prompt' or 'expected' key")
        if not isinstance(item["expected"], list) or not item["expected"]:
            raise ValueError(f"Item {i} 'expected' must be a non-empty list")
    return data


def validate_ground_truth(gt: list[dict], index: rc.SkillIndex) -> None:
    """Raise ValueError if any expected skill name not in index."""
    skills, _ = index.vectors()
    indexed_names = {s.name for s in skills}
    missing = []
    for item in gt:
        for name in item["expected"]:
            if name not in indexed_names:
                missing.append(name)
    if missing:
        raise ValueError(f"Ground-truth skill(s) not in index: {missing}")


def ensure_index(index: rc.SkillIndex, store: str) -> None:
    """If index is empty, reindex from store using production embedder."""
    skills, mat = index.vectors()
    if len(skills) == 0:
        all_skills = rc.discover_skills(store)
        if not all_skills:
            raise RuntimeError(f"No skills discovered from store: {store}")
        embed_fn = mb.get_embedder()
        result = index.reindex(all_skills, embed_fn)
        print(f"[sweep] Reindexed: {result}", file=sys.stderr)


def evaluate_prompt(
    prompt: str,
    expected: list[str],
    top_k_param: int,
    rerank_keep_param: int,
    rerank_margin: float,
    index: rc.SkillIndex,
    embed_fn,
    rerank_fn,
) -> PromptResult:
    """Run two-stage pipeline for one prompt under one config. Return metrics."""
    skills, mat = index.vectors()

    # Stage 1: dense recall
    q = np.asarray(embed_fn([prompt]), dtype=np.float32)[0]
    recall_hits = rc.top_k(q, mat, top_k_param)  # [(idx, cosine_sim)]

    # Stage 2: ColBERT rerank
    cands = [(skills[i], sim) for i, sim in recall_hits]
    docs = [f"{s.name}: {s.description}" for s, _ in cands]
    rr_scores = rerank_fn(prompt, docs)

    # Margin gate: median of FULL recall set as baseline
    baseline = float(np.median(np.array(rr_scores, dtype=np.float64)))

    # Sort by rerank score, keep top rerank_keep_param
    ranked = sorted(zip(cands, rr_scores), key=lambda t: -t[1])[:rerank_keep_param]

    # Accept only those clearing the margin
    accepted = []
    for (skill, _sim), score in ranked:
        if float(score) - baseline >= rerank_margin:
            accepted.append(skill.name)

    # Metrics
    expected_set = set(expected)
    accepted_set = set(accepted)
    hits = accepted_set & expected_set
    recall = len(hits) / len(expected_set) if expected_set else 0.0
    precision = len(hits) / len(accepted_set) if accepted_set else 0.0

    return PromptResult(prompt, expected, accepted, recall, precision)


def evaluate_tuple(
    top_k_param: int,
    rerank_keep_param: int,
    gt: list[dict],
    rerank_margin: float,
    index: rc.SkillIndex,
    embed_fn,
    rerank_fn,
) -> TupleResult:
    """Evaluate one (top_k, rerank_keep) tuple across all prompts."""
    prompt_results = []
    for item in gt:
        pr = evaluate_prompt(
            item["prompt"],
            item["expected"],
            top_k_param,
            rerank_keep_param,
            rerank_margin,
            index,
            embed_fn,
            rerank_fn,
        )
        prompt_results.append(pr)

    macro_recall = sum(pr.recall for pr in prompt_results) / len(prompt_results)
    macro_precision = sum(pr.precision for pr in prompt_results) / len(prompt_results)
    total_volume = sum(len(pr.retrieved) for pr in prompt_results)

    return TupleResult(
        top_k=top_k_param,
        rerank_keep=rerank_keep_param,
        prompt_results=prompt_results,
        macro_recall=macro_recall,
        macro_precision=macro_precision,
        total_volume=total_volume,
    )


def select_best(results: list[TupleResult], tolerance: float = 0.001) -> TupleResult:
    """Rank by recall desc, precision desc, volume desc within tolerance."""

    def sort_key(r: TupleResult):
        # Quantize to tolerance bands, then prefer higher volume
        recall_band = round(r.macro_recall / tolerance) * tolerance
        prec_band = round(r.macro_precision / tolerance) * tolerance
        return (-recall_band, -prec_band, -r.total_volume)

    return sorted(results, key=sort_key)[0]


def print_report(results: list[TupleResult], best: TupleResult) -> None:
    """Print summary table + per-prompt detail + best config indicator."""
    # Summary table
    print("=" * 72)
    print("SWEEP RESULTS")
    print("=" * 72)
    print(f"{'top_k':>6} {'rerank_keep':>11} {'Recall':>8} {'Precision':>10} {'Volume':>7}  Best")
    print("-" * 72)
    for r in results:
        marker = " <--" if r is best else ""
        print(
            f"{r.top_k:>6} {r.rerank_keep:>11} {r.macro_recall:>8.4f} "
            f"{r.macro_precision:>10.4f} {r.total_volume:>7}{marker}"
        )
    print("-" * 72)
    print()

    # Per-prompt detail
    for r in results:
        print(f"--- ({r.top_k}, {r.rerank_keep}) ---")
        for pr in r.prompt_results:
            truncated = pr.prompt[:60]
            print(f"  Prompt: {truncated}")
            print(f"    Expected:  {pr.expected}")
            print(f"    Retrieved: {pr.retrieved}")
            print(f"    Recall={pr.recall:.4f}  Precision={pr.precision:.4f}")
        print()

    # Best config
    print("=" * 72)
    print(f"BEST CONFIG: top_k={best.top_k}, rerank_keep={best.rerank_keep}")
    print(f"  Macro Recall:    {best.macro_recall:.4f}")
    print(f"  Macro Precision: {best.macro_precision:.4f}")
    print(f"  Total Volume:    {best.total_volume}")
    print("=" * 72)


def main() -> None:
    """CLI entry point: parse args, load, validate, evaluate, select, report."""
    parser = argparse.ArgumentParser(description="CV sweep for skill-router hyperparameters")
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=Path(__file__).parent / "ground_truth.json",
        help="Path to ground_truth.json",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(__file__).parent / "index.db",
        help="Path to SkillIndex sqlite database",
    )
    parser.add_argument(
        "--store",
        type=str,
        default=str(Path(__file__).parent.parent / ".skills"),
        help="Path to skill store directory",
    )
    parser.add_argument(
        "--margin",
        type=float,
        default=1.5,
        help="Rerank margin threshold (default: 1.5)",
    )
    args = parser.parse_args()

    # Log backend info (Requirement 6)
    print(f"[sweep] Embed model: {mb.EMBED_MODEL}", file=sys.stderr)
    print(f"[sweep] Rerank backend: {mb.RERANK_BACKEND}", file=sys.stderr)

    # Load ground truth
    gt = load_ground_truth(args.ground_truth)

    # Open index
    index = rc.SkillIndex(args.db)

    # Ensure index is populated
    ensure_index(index, args.store)

    # Log index size
    skills, _ = index.vectors()
    print(f"[sweep] Indexed skills: {len(skills)}", file=sys.stderr)

    # Validate ground truth
    validate_ground_truth(gt, index)

    # Get backends
    embed_fn = mb.get_embedder()
    rerank_fn = mb.get_reranker()

    # Evaluate all candidate tuples
    results = []
    for top_k_param, rerank_keep_param in CANDIDATE_TUPLES:
        tr = evaluate_tuple(
            top_k_param, rerank_keep_param, gt, args.margin, index, embed_fn, rerank_fn
        )
        results.append(tr)

    # Select best and report
    best = select_best(results)
    print_report(results, best)


if __name__ == "__main__":
    main()
