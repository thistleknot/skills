"""
consolidate.py -- Skill consolidation analysis for the skills repository.

Idempotency contract:
  Require:  skills root exists; sklearn installed
  Guarantee: only runs full analysis when ≥2 skills have changed since last run;
             otherwise exits early with a clear message
  Maintain:  content-hash checkpoint in consolidation/.checkpoint.db
  Assert:    changed_count computed before any vectorisation

Usage:
    python consolidate.py [--force] [--root PATH] [--obsidian [N]] [--graph]
    --force      bypass idempotency check and always run
    --root       override skills root directory
    --obsidian N write/update [[wikilinks]] See Also sections in each SKILL.md
                 and a root _skill_graph.md index (default N=3 neighbors)
    --graph      run graph analysis (community detection, betweenness, DWPC,
                 spring layout) after the main pipeline; writes graph_report.json
                 and graph.png to the consolidation/ directory
"""

import argparse
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from skill_similarity import (
    build_similarity_matrix,
    build_skill_documents,
    derive_skill_corpus,
)

TAU = 0.30          # semantic floor: minimum xref-worthy overlap
MIN_CHANGED = 2     # minimum skills changed to trigger a re-run

SEE_ALSO_START = "<!-- consolidation:see-also:start -->"
SEE_ALSO_END   = "<!-- consolidation:see-also:end -->"


def load_checkpoint(db_path: Path) -> dict:
    """Return {skill_name: hash} from last run, or {} if no checkpoint."""
    if not db_path.exists():
        return {}
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute("SELECT skill_name, content_hash FROM skill_hashes").fetchall()
        return {r[0]: r[1] for r in rows}
    except sqlite3.OperationalError:
        return {}
    finally:
        con.close()


def save_checkpoint(db_path: Path, hashes: dict, group_count: int, changed: int) -> None:
    """Persist current content hashes and run metadata."""
    con = sqlite3.connect(db_path)
    con.execute("""
        CREATE TABLE IF NOT EXISTS skill_hashes (
            skill_name   TEXT PRIMARY KEY,
            content_hash TEXT NOT NULL
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS run_log (
            run_ts         TEXT,
            skills_changed INTEGER,
            group_count    INTEGER
        )
    """)
    con.execute("DELETE FROM skill_hashes")
    con.executemany(
        "INSERT INTO skill_hashes VALUES (?, ?)",
        hashes.items(),
    )
    con.execute(
        "INSERT INTO run_log VALUES (?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), changed, group_count),
    )
    con.commit()
    con.close()


def prescribe(s: float) -> str:
    if s >= 0.80: return "MERGE"
    if s >= 0.50: return "migrate"
    if s >= 0.30: return "xref"
    return "low"


def action_label(s: float) -> str:
    if s >= 0.80: return "deduplicate"
    if s >= 0.50: return "migrate overlap"
    return "cross-reference"


def write_obsidian_links(skill_files: list, names: list, M: np.ndarray,
                         chains_sorted: list, real_groups: list,
                         root: Path, top_n: int) -> None:
    """Write/update [[wikilinks]] See Also blocks in each SKILL.md and
    write a root _skill_graph.md index for Obsidian graph navigation.

    Require:  M is the full NxN similarity matrix; skill_files[i] corresponds to names[i]
    Guarantee: See Also section is idempotent -- replaces itself on each run
    Maintain:  existing SKILL.md content outside the delimited block is unchanged
    """
    N = len(names)

    # top-N neighbors per skill, unconditional -- τ is a prescription floor,
    # not a navigation floor; every skill should connect to its closest peers
    neighbors: dict[str, list[str]] = {}
    for i, name in enumerate(names):
        row = [(M[i, j], names[j]) for j in range(N) if j != i]
        row.sort(reverse=True)
        neighbors[name] = [n for _, n in row[:top_n]]

    updated = 0
    for skill_path, name in zip(skill_files, names):
        links = neighbors.get(name, [])
        if links:
            link_line = "  ".join(f"[[{n}]]" for n in links)
            see_also_block = (
                f"\n{SEE_ALSO_START}\n"
                f"## See Also\n"
                f"{link_line}\n"
                f"{SEE_ALSO_END}\n"
            )
        else:
            see_also_block = ""

        original = skill_path.read_text(encoding="utf-8", errors="ignore")

        if SEE_ALSO_START in original:
            pattern = re.compile(
                re.escape(SEE_ALSO_START) + r'.*?' + re.escape(SEE_ALSO_END),
                re.DOTALL,
            )
            new_content = pattern.sub(see_also_block.strip(), original)
        else:
            new_content = original.rstrip() + see_also_block

        if new_content != original:
            skill_path.write_text(new_content, encoding="utf-8")
            updated += 1

    # root _skill_graph.md -- navigable Obsidian index
    singleton_names = [names[c[0]] for c in chains_sorted if len(c) == 1]
    lines = [
        "# Skill Graph",
        "",
        f"> Generated by `consolidation/consolidate.py --obsidian {top_n}`  ",
        f"> τ={TAU}  N={N}  groups={len(real_groups)}  singletons={len(singleton_names)}",
        "",
        "## Groups",
        "",
    ]
    for rank, chain in enumerate(real_groups, 1):
        chain_names = [names[i] for i in chain]
        member_links = "  -->  ".join(f"[[{n}]]" for n in chain_names)
        lines.append(f"### Group {rank} ({len(chain)} skills)")
        lines.append(member_links)
        lines.append("")

    lines += [
        "## Singletons",
        "",
        "  ".join(f"[[{n}]]" for n in singleton_names),
        "",
    ]

    graph_file = root / "_skill_graph.md"
    graph_file.write_text("\n".join(lines), encoding="utf-8")

    print(f"\nObsidian: {updated} SKILL.md file(s) updated with See Also links")
    print(f"Obsidian: index written -> {graph_file}")
    print("  Open this folder as an Obsidian vault -> Graph view shows semantic clusters.")


# -- main ---------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Skill consolidation analysis")
    parser.add_argument("--force", action="store_true", help="bypass idempotency check")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="skills root directory")
    parser.add_argument("--obsidian", nargs="?", const=3, type=int, metavar="N",
                        help="write [[wikilinks]] into each SKILL.md and generate "
                             "_skill_graph.md (default N=3 neighbors per skill)")
    parser.add_argument("--graph", action="store_true",
                        help="run graph analysis (Louvain, k-means elbow, betweenness, "
                             "DWPC, spring layout) after main pipeline")
    parser.add_argument("--cancel-pending", action="store_true",
                        help="cancel pending embedding queue tasks before running consolidation; "
                             "requires embedding_queue_server running at http://localhost:8000")
    args = parser.parse_args()

    root: Path = args.root
    db_path: Path = Path(__file__).resolve().parent / ".checkpoint.db"

    # -- embedding queue pre-flight: cancel pending tasks if requested -----------
    if args.cancel_pending:
        try:
            import requests
            resp = requests.post("http://localhost:8000/queue/cancel-pending", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                cancelled = data.get("cancelled_count", 0)
                print(f"[Embedding Queue] Cancelled {cancelled} pending task(s)")
            else:
                print(f"[Embedding Queue] Warning: cancel-pending returned {resp.status_code}")
        except Exception as e:
            print(f"[Embedding Queue] Warning: could not cancel pending tasks ({e})")
            print("  Continuing with consolidation anyway (queue server may be unavailable)")

    # -- collect skill files ---------------------------------------------------
    documents = build_skill_documents(root)
    if not documents:
        sys.exit(f"No SKILL.md files found under {root}")

    skill_files = [document.skill_file for document in documents]
    names = [document.name for document in documents]
    current_hashes = {document.name: document.content_hash for document in documents}

    # -- idempotency check -----------------------------------------------------
    prev_hashes = load_checkpoint(db_path)
    prev_names  = set(prev_hashes.keys())
    curr_names  = set(current_hashes.keys())

    new_skills     = curr_names - prev_names
    removed_skills = prev_names - curr_names
    modified       = {n for n in curr_names & prev_names
                      if current_hashes[n] != prev_hashes[n]}
    changed = new_skills | removed_skills | modified

    if not args.force and len(changed) < MIN_CHANGED:
        if not changed:
            print("Consolidation: no skills changed since last run. Nothing to do.")
        else:
            changed_list = ", ".join(sorted(changed))
            print(f"Consolidation: only {len(changed)} skill(s) changed since last run "
                  f"({changed_list}). Need >={MIN_CHANGED} for a meaningful correlation shift. "
                  f"Skipping. Use --force to override.")
        return

    if changed:
        print(f"[{len(changed)} skill(s) changed: "
              f"{len(new_skills)} new, {len(removed_skills)} removed, {len(modified)} modified]")
    else:
        print("[--force: running unconditionally]")

    derivations = derive_skill_corpus(documents, db_path)
    M = build_similarity_matrix(documents, derivations, db_path=db_path)
    N = len(names)

    pairs = sorted(
        ((M[i, j], i, j) for i in range(N) for j in range(i + 1, N)),
        reverse=True,
    )

    # -- greedy nearest-neighbor chain decomposition ---------------------------
    doc_to_chain: dict[int, int] = {}
    chains: list[list[int]] = []

    for score, i, j in pairs:
        if score < TAU:
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

    chains_sorted = sorted(chains, key=len, reverse=True)
    real_groups = [c for c in chains_sorted if len(c) > 1]
    singletons  = [c for c in chains_sorted if len(c) == 1]

    # -- report ----------------------------------------------------------------
    print(f"\ntau={TAU}  N={N} skills  groups={len(real_groups)}  singletons={len(singletons)}")
    print("=" * 80)
    print("\n-- GROUPS (read in unison, resolve per prescription) --\n")

    for rank, chain in enumerate(real_groups, 1):
        actions = {action_label(M[chain[p], chain[p+1]]) for p in range(len(chain)-1)}
        print(f"Group {rank}  ({len(chain)} skills)  [{' | '.join(sorted(actions))}]")
        for pos, idx in enumerate(chain):
            if pos < len(chain) - 1:
                nidx = chain[pos + 1]
                sim  = M[idx, nidx]
                print(f"  {names[idx]:<44}  --{sim:.3f} [{prescribe(sim)}]-->  {names[nidx]}")
            else:
                print(f"  {names[idx]}")
        print()

    print(f"\n-- SINGLETONS ({len(singletons)}) -- distinct, no resolution needed --\n")
    cols = 4
    for row in [singletons[i:i+cols] for i in range(0, len(singletons), cols)]:
        print("  " + "    ".join(f"{names[c[0]]:<30}" for c in row))

    # -- obsidian export -------------------------------------------------------
    if args.obsidian is not None:
        write_obsidian_links(skill_files, names, M, chains_sorted, real_groups,
                             root, top_n=args.obsidian)

    # -- graph analysis (optional) --------------------------------------------
    if args.graph:
        from graph_analysis import run_graph_analysis
        run_graph_analysis(
            db_path=db_path,
            tau=None,  # adaptive: 85th pct of pairwise cosines
            out_dir=db_path.parent,
            render=True,
        )

    # -- checkpoint ------------------------------------------------------------
    save_checkpoint(db_path, current_hashes, len(real_groups), len(changed))
    print(f"\nCheckpoint saved -> {db_path}")


if __name__ == "__main__":
    main()

