"""Skill-router MCP server — stdio transport for IDE integration (Kiro, Claude Code).

Same tools as server.py (retrieve_skills, read_skill) but runs over stdio
instead of HTTP. No custom routes (/route, /health, /reindex) since those
are HTTP-only; the MCP tools are what the IDE model calls directly.

Usage in mcp.json:
  {
    "mcpServers": {
      "retrieve-skills": {
        "command": "c:/users/user/py310/Scripts/python.exe",
        "args": ["c:/users/user/.claude/skills/retrieve-skills/server_stdio.py"]
      }
    }
  }
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastmcp import FastMCP

import model_backends as mb
import router_core as rc

log = logging.getLogger("skill-router-stdio")
logging.basicConfig(level=logging.INFO)

HERE = Path(__file__).parent
STORE = os.path.expanduser(os.environ.get("SKILL_STORE", str(HERE.parent / ".skills")))
DB = os.path.expanduser(os.environ.get("SKILL_ROUTER_DB", str(HERE / "index.db")))

CFG = rc.RouteConfig(
    top_k=int(os.environ.get("SKILL_ROUTER_TOP_K", "21")),
    rerank_keep=int(os.environ.get("SKILL_ROUTER_RERANK_KEEP", "13")),
    rerank_margin=float(os.environ.get("SKILL_ROUTER_RERANK_MARGIN", "1.5")),
    max_accept=int(os.environ.get("SKILL_ROUTER_MAX_ACCEPT", "3")),
)

index = rc.SkillIndex(DB)

mcp = FastMCP(
    name="retrieve-skills",
    instructions=(
        "Retrieval gate over the local skill store. At the start of any "
        "non-trivial task, call retrieve_skills with a short task description "
        "to check whether specialized instructions exist; then read_skill(name) "
        "for any skill worth applying."
    ),
)


def _ensure_index():
    """Reindex if empty."""
    skills, _ = index.vectors()
    if not skills:
        all_skills = rc.discover_skills(STORE)
        if all_skills:
            index.reindex(all_skills, mb.get_embedder())
            log.info("Reindexed %d skills", len(all_skills))


@mcp.tool
def retrieve_skills(query: str, k: int = 3) -> str:
    """Retrieve skills relevant to a task from the local skill store.

    query: short description of the task at hand (what you are about to do).
    k: max candidates to return.
    Returns ranked candidates with scores and a gate verdict (PASS = cleared
    the rerank margin gate; CANDIDATE = ranked but below gate). Follow up
    with read_skill(name) to get full instructions.
    """
    _ensure_index()
    skills, mat = index.vectors()
    if not skills:
        return "skill store is empty — run indexer.py first"

    cfg = rc.RouteConfig(
        top_k=max(CFG.top_k, k * 3),
        rerank_keep=max(CFG.rerank_keep, k * 2),
        rerank_margin=CFG.rerank_margin,
        max_accept=k,
    )
    passed = rc.route(query, index, mb.get_embedder(), mb.get_reranker(), cfg)
    passed_names = {a["name"] for a in passed}

    lines = [
        f"PASS {a['name']} (rerank {a['rerank_score']:.3f}, margin {a['rerank_margin']:.3f}): "
        f"{a['description']}"
        for a in passed
    ]

    # Below-gate candidates for context
    import numpy as np
    q = np.asarray(mb.get_embedder()([query]), dtype=np.float32)[0]
    for i, _sim in rc.top_k(q, mat, k + len(passed_names)):
        s = skills[i]
        if s.name not in passed_names and len(lines) < k + len(passed_names):
            lines.append(f"CANDIDATE {s.name}: {s.description}")

    return "\n".join(lines) if lines else "no relevant skills found"


@mcp.tool
def read_skill(name: str) -> str:
    """Return the full instructions (SKILL.md body) of a stored skill by name.

    Use after retrieve_skills identifies a relevant skill. Returns the full
    content of the skill file (minus frontmatter).
    """
    _ensure_index()
    skills, _ = index.vectors()
    match = next((s for s in skills if s.name == name), None)
    if match is None:
        return f"unknown skill '{name}' — use retrieve_skills first"
    try:
        text = Path(match.path).read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return f"could not read '{name}': {e}"
    return rc.skill_body(text)


if __name__ == "__main__":
    mcp.run(transport="stdio")
