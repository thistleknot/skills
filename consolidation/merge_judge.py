#!/usr/bin/env python3
"""LLM adjudication of the MERGE quadrant only.

Thesis
------
The two-axis screen is cheap, deterministic, and has a real false-positive rate:
measured 2026-07-26 it put `codebase-knowledge-graph` + `git-workflow` in MERGE
on shared vocabulary alone. Vocabulary overlap cannot see that one skill is a
PARENT of the other (`consolidation` calls `nearest-neighbor-chain` as a named
sub-skill -- that is XREF by construction, never a merge).

So the judge runs on the MERGE bucket only -- ~29 pairs, not 8,778 -- which is
the cheapest sufficient placement: the screen removes 99.7% of the work, the
judge supplies the semantics the screen cannot.

The judge may only DOWNGRADE (MERGE -> XREF/SEPARATE) or confirm. It cannot
promote a pair the screen rejected, because it never sees those.

Require   - ollama serving JUDGE_MODEL; merge_report.md present.
Guarantee - one verdict + one-sentence reason per MERGE pair; a pair whose
            verdict cannot be parsed after retries is reported UNJUDGED, never
            silently confirmed.
Maintain  - verdicts checkpointed by (skill_a, skill_b, model) so a re-run costs
            nothing for pairs already judged.
Assert    - refuses to write merged content; this module only labels.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

JUDGE_MODEL = "qwen3.5-reasoning-thinking-256k:9b"   # most capable on disk
OLLAMA = "http://localhost:11434"
CHECKPOINT = Path(__file__).with_name(".merge_judge.db")

PROMPT = """You are auditing a skill library for redundancy. Two skills were flagged
as possible duplicates by an automated screen. Decide what should happen to them.

SKILL A: {a}
{a_desc}

SKILL B: {b}
{b_desc}

Verdicts:
- MERGE    the two cover the SAME ground; one should absorb the other
- XREF     genuinely related but distinct scope; keep both, link them.
           Use this when one is a PARENT or SUB-SKILL of the other.
- SEPARATE flagged only by shared vocabulary; they are different subjects

Reply with ONLY a JSON object, no other text:
{{"verdict": "MERGE|XREF|SEPARATE", "reason": "<one sentence>", "keep": "<A or B or null>"}}"""


def _describe(root: Path, skill: str, limit: int = 700) -> str:
    """Frontmatter description if present, else the opening prose."""
    path = root / skill / "SKILL.md"
    if not path.is_file():
        return "(missing)"
    raw = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^description:\s*>?\s*\n?(.*?)(?=^\w[\w-]*:|^---)", raw, re.S | re.M)
    text = m.group(1) if m else raw
    return " ".join(text.split())[:limit]


def declared_relation(root: Path, a: str, b: str) -> str | None:
    """Non-null when either skill's text names the other as a related skill.

    A declared parent/sub-skill link is XREF by construction and must not depend
    on the judge noticing it. Measured 2026-07-26: asked to adjudicate
    `consolidation` vs `nearest-neighbor-chain` -- where consolidation/SKILL.md
    literally reads "sub-skill called in Step 3" -- the judge wrote the
    relationship correctly in its own reason ("Skill A applies as a specific
    step") and then returned MERGE anyway. The prompt already told it to answer
    XREF in that case. Structure beats instruction: enforce it in code.

    Guarantee - returns the direction found, or None. Never raises on a missing
                file, so a half-present corpus degrades to judge-only.
    """
    for owner, other in ((a, b), (b, a)):
        path = root / owner / "SKILL.md"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        # backticked or bare mention alongside a relationship word, same line
        for line in text.splitlines():
            if other.lower() in line and re.search(
                r"sub-skill|subskill|parent|calls?\b|cross-referenc|see also|companion|delegat", line
            ):
                return f"{owner} declares {other} as a related/sub-skill"
    return None


def ask(prompt: str, retries: int = 3) -> dict | None:
    """One judged verdict, or None when the model never returns parseable JSON."""
    for attempt in range(retries):
        req = urllib.request.Request(
            f"{OLLAMA}/api/generate",
            data=json.dumps({
                "model": JUDGE_MODEL,
                "prompt": prompt,
                "stream": False,
                "think": False,          # reasoning models otherwise bury the JSON
                "format": "json",        # schema-constrained decode
                "options": {"temperature": 0.0, "num_predict": 300},
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                body = json.loads(resp.read())["response"]
            data = json.loads(body)
            if str(data.get("verdict", "")).upper() in {"MERGE", "XREF", "SEPARATE"}:
                data["verdict"] = data["verdict"].upper()
                return data
        except Exception as exc:
            if attempt == retries - 1:
                print(f"    judge failed after {retries}: {type(exc).__name__}")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="adjudicate the MERGE quadrant")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--report", type=Path, default=Path(__file__).with_name("merge_report.md"))
    ap.add_argument("--out", type=Path, default=Path(__file__).with_name("merge_verdicts.md"))
    args = ap.parse_args()

    rows = [
        (float(m.group(1)), float(m.group(2)), m.group(3), m.group(4))
        for m in re.finditer(
            r"^\| MERGE \| ([\d.]+) \| ([\d.]+) \| `([^`]+)` \| `([^`]+)` \|$",
            args.report.read_text(encoding="utf-8"), re.M)
    ]
    print(f"{len(rows)} MERGE pairs to adjudicate with {JUDGE_MODEL}")

    conn = sqlite3.connect(CHECKPOINT)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS verdicts ("
        " a TEXT, b TEXT, model TEXT, verdict TEXT, reason TEXT, keep TEXT,"
        " judged_at TEXT, PRIMARY KEY (a,b,model))"
    )

    results = []
    for n, (av, bv, a, b) in enumerate(rows, 1):
        # Structural override runs BEFORE the judge and before the cache: a
        # declared sub-skill link is XREF by definition, so neither a model nor a
        # stale verdict may call it a merge.
        declared = declared_relation(args.root, a, b)
        if declared:
            results.append((a, b, av, bv, "XREF", f"structural: {declared}", None))
            print(f"  [{n}/{len(rows)}] XREF     (structural)  {a} <-> {b}")
            continue
        cached = conn.execute(
            "SELECT verdict, reason, keep FROM verdicts WHERE a=? AND b=? AND model=?",
            (a, b, JUDGE_MODEL)).fetchone()
        if cached:
            results.append((a, b, av, bv, *cached))
            continue
        t0 = time.time()
        out = ask(PROMPT.format(a=a, a_desc=_describe(args.root, a),
                                b=b, b_desc=_describe(args.root, b)))
        if out is None:
            results.append((a, b, av, bv, "UNJUDGED", "model returned no parseable verdict", None))
            print(f"  [{n}/{len(rows)}] UNJUDGED  {a} <-> {b}")
            continue
        v, r, k = out["verdict"], out.get("reason", ""), out.get("keep")
        conn.execute("INSERT OR REPLACE INTO verdicts VALUES (?,?,?,?,?,?,?)",
                     (a, b, JUDGE_MODEL, v, r, k, time.strftime("%Y-%m-%dT%H:%M:%S")))
        conn.commit()
        results.append((a, b, av, bv, v, r, k))
        print(f"  [{n}/{len(rows)}] {v:8} ({time.time()-t0:4.1f}s)  {a} <-> {b}")
    conn.close()

    order = {"MERGE": 0, "XREF": 1, "SEPARATE": 2, "UNJUDGED": 3}
    results.sort(key=lambda r: (order.get(r[4], 9), -(r[2] + r[3])))
    counts = {v: sum(1 for r in results if r[4] == v) for v in order}
    print("\nverdicts: " + ", ".join(f"{k}={v}" for k, v in counts.items() if v))

    lines = [
        "# Merge verdicts (judged)", "",
        f"Screen flagged **{len(rows)}** MERGE pairs out of 8,778; "
        f"`{JUDGE_MODEL}` adjudicated each.",
        "The judge can only downgrade or confirm -- it never sees pairs the screen rejected.",
        "", "| verdict | A rel | B coll | skill | skill | keep | reason |",
        "|---|---:|---:|---|---|---|---|",
    ]
    for a, b, av, bv, v, r, k in results:
        lines.append(f"| **{v}** | {av:.3f} | {bv:.3f} | `{a}` | `{b}` | {k or '-'} | {r} |")
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
