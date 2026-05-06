"""
merge_execute.py -- LLM-judge driven skill consolidation executor.

For each semantic group from the nearest-neighbor chain decomposition,
sends the group to an LLM judge that decides:
  - MERGE: which skills collapse into one (writes merged SKILL.md, git rm losers)
  - XREF:  keeps them separate, notes which pairs need cross-references

After all merges, re-runs consolidate.py --obsidian to refresh See Also blocks,
then commits and pushes.

Usage:
    python merge_execute.py [--dry-run] [--tau FLOAT] [--root PATH]

    --dry-run    Print decisions without writing or deleting any files.
    --tau FLOAT  Similarity floor for grouping (default 0.30 = same as consolidate.py).
    --root PATH  Skills root directory override.

Env vars (LLM routing):
    LLM_BASE_URL   API base URL (default: http://localhost:8081/v1)
    LLM_MODEL      Model name   (default: qwen3)
    LLM_API_KEY    API key      (default: local)

Require:
    - skills root exists with */SKILL.md files
    - openai python package installed
    - LLM endpoint reachable at LLM_BASE_URL
Guarantee:
    - No file is modified unless LLM returns a valid merge decision
    - dry-run never touches disk or git
    - After execution, consolidate.py --obsidian regenerates all See Also blocks
Maintain:
    - Every skill in a merged group either becomes winner or is deleted
    - git rm is used for deletions so git history tracks the removal
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from skill_similarity import (
    build_similarity_matrix,
    build_skill_documents,
    derive_skill_corpus,
)

TAU = 0.30

JUDGE_PROMPT = """\
You are reviewing a group of semantically related SKILL.md files from an AI agent \
skill library. Each file is a behavioral protocol used by a coding agent.

Your job: decide whether any skills in this group should be MERGED into a single file, \
or kept separate with cross-references.

MERGE when:
- Skills cover the same concept; one is a near-subset of the other.
- A single unified document would be more useful than two separate ones.
- No meaningful invocation distinction separates them.

KEEP SEPARATE when:
- Skills have distinct use cases even if the topic overlaps.
- Combining would create an unfocused, bloated document.
- A user would invoke them in genuinely different scenarios.

Return ONLY valid JSON matching this schema exactly:
{{
  "merges": [
    {{
      "winner": "folder-name-to-keep",
      "losers": ["folder-name-to-delete"],
      "merged_content": "<COMPLETE merged SKILL.md content — full file, not a snippet>",
      "reasoning": "one sentence"
    }}
  ],
  "xref_pairs": [["skill-a", "skill-b"]],
  "reasoning": "overall group reasoning"
}}

Rules:
- merged_content MUST be the complete SKILL.md file content.
- Winner folder name must be one from this group.
- If no merges are warranted, return empty merges array.
- List remaining correlated pairs (non-losers) in xref_pairs.

=== SKILLS IN THIS GROUP ===
{skills_block}
"""


# ---------------------------------------------------------------------------
# Similarity + chain decomposition
# ---------------------------------------------------------------------------

def compute_chains(M: np.ndarray, tau: float = TAU) -> list[list[int]]:
    """
    Require:  M is a symmetric similarity matrix; tau > 0
    Guarantee: returns greedy nearest-neighbor chains at threshold tau
    """
    N = M.shape[0]

    pairs = sorted(
        ((M[i, j], i, j) for i in range(N) for j in range(i + 1, N)),
        reverse=True,
    )

    doc_to_chain: dict[int, int] = {}
    chains: list[list[int]] = []

    for score, i, j in pairs:
        if score < tau:
            break
        ci = doc_to_chain.get(i)
        cj = doc_to_chain.get(j)
        if ci is not None and cj is not None:
            continue
        if ci is None and cj is None:
            cidx = len(chains)
            chains.append([i, j])
            doc_to_chain[i] = cidx
            doc_to_chain[j] = cidx
        elif ci is None:
            if chains[cj][-1] == j:
                chains[cj].append(i)
                doc_to_chain[i] = cj
            elif chains[cj][0] == j:
                chains[cj].insert(0, i)
                doc_to_chain[i] = cj
        else:
            if chains[ci][-1] == i:
                chains[ci].append(j)
                doc_to_chain[j] = ci
            elif chains[ci][0] == i:
                chains[ci].insert(0, j)
                doc_to_chain[j] = ci

    for idx in range(N):
        if idx not in doc_to_chain:
            cidx = len(chains)
            chains.append([idx])
            doc_to_chain[idx] = cidx

    return chains


# ---------------------------------------------------------------------------
# LLM judge
# ---------------------------------------------------------------------------

def llm_judge(chain_names: list[str], raw_texts: dict[str, str]) -> dict:
    """
    Require:  chain_names are valid keys in raw_texts; LLM endpoint reachable
    Guarantee: returns dict with 'merges' list and 'xref_pairs' list
    Maintain:  temperature=0.0 for deterministic decisions
    """
    from openai import OpenAI

    base_url = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
    model    = os.environ.get("LLM_MODEL", "qwen3.5:2b")
    api_key  = os.environ.get("LLM_API_KEY", "ollama")

    client = OpenAI(base_url=base_url, api_key=api_key)

    skills_block = ""
    for name in chain_names:
        content = raw_texts[name]
        if len(content) > 6000:
            content = content[:6000] + "\n\n... [truncated for context] ..."
        skills_block += f"\n\n=== SKILL: {name} ===\n{content}\n"

    prompt = JUDGE_PROMPT.format(
        skills_block=skills_block,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )

    raw = response.choices[0].message.content.strip()

    # strip any <think>...</think> block Qwen3 emits despite enable_thinking=False
    raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()

    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if not m:
        print(f"  WARNING: LLM returned no parseable JSON for {chain_names}")
        print(f"  Raw response: {raw[:400]}")
        return {"merges": [], "xref_pairs": [], "reasoning": "parse failure"}

    try:
        return json.loads(m.group())
    except json.JSONDecodeError as e:
        print(f"  WARNING: JSON parse error for {chain_names}: {e}")
        return {"merges": [], "xref_pairs": [], "reasoning": "json parse failure"}


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def execute_merge(winner: str, losers: list[str], merged_content: str,
                  root: Path, dry_run: bool) -> bool:
    """
    Require:  winner and each loser are folder names under root
    Guarantee: writes merged_content to winner/SKILL.md; git rm -r each loser
    Maintain:  on dry_run, no files are written or deleted
    Assert:    winner path must exist; returns False on any failure
    """
    winner_path = root / winner / "SKILL.md"
    if not winner_path.parent.exists():
        print(f"  ERROR: winner folder {winner} does not exist in {root}")
        return False

    if dry_run:
        print(f"  [DRY-RUN] MERGE {losers} -> {winner}")
        for loser in losers:
            print(f"  [DRY-RUN]   would git rm -r {loser}/")
        print(f"  [DRY-RUN]   would write {len(merged_content)} chars to {winner_path}")
        return True

    winner_path.write_text(merged_content, encoding="utf-8")
    print(f"  Wrote merged SKILL.md -> {winner_path}")

    for loser in losers:
        loser_path = root / loser
        if loser_path.exists():
            result = subprocess.run(
                ["git", "rm", "-r", str(loser_path)],
                cwd=root, capture_output=True, text=True,
            )
            if result.returncode != 0:
                print(f"  WARNING: git rm failed for {loser}: {result.stderr.strip()}")
            else:
                print(f"  git rm -r {loser}/")
        else:
            print(f"  WARNING: loser folder {loser} not found, skipping")

    return True


def remove_from_readme(losers: list[str], root: Path, dry_run: bool) -> None:
    """Remove deleted skill entries from README.md skill graph AST."""
    readme = root / "README.md"
    if not readme.exists():
        return
    content = readme.read_text(encoding="utf-8", errors="ignore")
    original = content
    for loser in losers:
        # Remove any line referencing the loser skill (AST lines, table rows)
        pattern = re.compile(
            r'^.*\b' + re.escape(loser) + r'\b.*$\n?',
            re.MULTILINE,
        )
        content = pattern.sub("", content)
    if content != original:
        if dry_run:
            print(f"  [DRY-RUN] Would remove {losers} from README.md")
        else:
            readme.write_text(content, encoding="utf-8")
            print(f"  Updated README.md (removed {losers})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="LLM-judge driven skill merger: groups semantically related "
                    "skills and executes merge/xref decisions."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="print decisions without modifying any files")
    parser.add_argument("--tau", type=float, default=TAU,
                        help=f"similarity floor for grouping (default {TAU})")
    parser.add_argument("--root", type=Path,
                        default=Path(__file__).resolve().parent.parent,
                        help="skills root directory")
    args = parser.parse_args()

    root: Path = args.root
    db_path = Path(__file__).resolve().parent / ".checkpoint.db"

    print(f"Skills root: {root}")
    print(f"Tau: {args.tau}  |  Dry-run: {args.dry_run}")
    print(f"LLM: {os.environ.get('LLM_BASE_URL','http://localhost:11434/v1')} / "
          f"{os.environ.get('LLM_MODEL_LIST', os.environ.get('LLM_MODEL', 'qwen3.5:0.8b,qwen2.5-coder:1.5b,qwen3.5:2b,granite-1b:latest'))}")
    print()

    documents = build_skill_documents(root)
    names = [document.name for document in documents]
    raw_texts = {document.name: document.source_text for document in documents}
    derivations = derive_skill_corpus(documents, db_path)
    M = build_similarity_matrix(documents, derivations, db_path=db_path)
    chains = compute_chains(M, tau=args.tau)

    real_groups = [c for c in chains if len(c) > 1]
    singletons  = [c for c in chains if len(c) == 1]

    print(f"Groups: {len(real_groups)}  |  Singletons: {len(singletons)}")
    print()

    total_merges = 0
    all_losers: list[str] = []

    for rank, chain in enumerate(real_groups, 1):
        chain_names = [names[i] for i in chain]
        # show pairwise scores for context
        score_pairs = []
        for p in range(len(chain) - 1):
            score_pairs.append(f"{chain_names[p]}<->{chain_names[p+1]}:{M[chain[p],chain[p+1]]:.3f}")
        print(f"Group {rank}/{len(real_groups)}: {chain_names}")
        print(f"  Scores: {' | '.join(score_pairs)}")

        decision = llm_judge(chain_names, raw_texts)
        print(f"  Reasoning: {decision.get('reasoning','')}")

        for merge in decision.get("merges", []):
            winner  = merge.get("winner", "")
            losers  = merge.get("losers", [])
            content = merge.get("merged_content", "")
            reason  = merge.get("reasoning", "")

            if not winner or not losers or not content:
                print(f"  WARNING: incomplete merge spec, skipping: {merge.keys()}")
                continue

            print(f"  MERGE: {losers} -> {winner}  ({reason})")
            ok = execute_merge(winner, losers, content, root, args.dry_run)
            if ok:
                total_merges += 1
                all_losers.extend(losers)
                remove_from_readme(losers, root, args.dry_run)

        for pair in decision.get("xref_pairs", []):
            if len(pair) >= 2:
                print(f"  XREF:  {pair[0]} <-> {pair[1]}")

        print()

    print(f"Total merges: {total_merges}")

    if args.dry_run:
        print("\nDry-run complete. No files were modified.")
        return

    if total_merges == 0:
        print("No merges executed. Re-running obsidian links update anyway.")

    # Regenerate See Also blocks with fresh similarity after merges
    print("\nRegenerating See Also blocks...")
    subprocess.run(
        [sys.executable, str(Path(__file__).parent / "consolidate.py"),
         "--force", "--obsidian", "3"],
        cwd=root,
    )

    # Stage + commit everything
    subprocess.run(["git", "add", "-A"], cwd=root)

    losers_summary = ", ".join(all_losers) if all_losers else "none"
    msg = (
        f"consolidation: LLM-judge merged {total_merges} skill(s) (removed: {losers_summary})\n"
        "\n"
        "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
    )
    result = subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=root, capture_output=True, text=True,
    )
    if result.returncode == 0:
        subprocess.run(["git", "push"], cwd=root)
        print("Committed and pushed.")
    else:
        print(f"Commit output: {result.stdout.strip()} {result.stderr.strip()}")


if __name__ == "__main__":
    main()
