"""skill-router server: fastmcp app exposing the RAG gate two ways.

Purpose: one warm process, two entry points over the same index + gate:
- MCP tools (model-invoked, mid-task):
    retrieve_skills(query, k) -> ranked candidates with gate verdicts
    read_skill(name)          -> full SKILL.md body on demand
- HTTP custom routes (deterministic hook path + ops):
    POST /route   -> full gate + session dedup (hook.py calls this per prompt)
    POST /reindex -> re-embed changed descriptions
    GET  /health  -> status

Preconditions: skill store at SKILL_STORE (default: ~/.skills — a single
shared store accessible from any harness); start as one persistent service.

Failure modes: /route catches ALL errors and returns {skills: []} (fail-open —
a broken model must never block a prompt). MCP tools and /reindex report
errors to the caller (model/operator-invoked; visibility beats silence there).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

# Avast antivirus sets SSLKEYLOGFILE to \\.\aswMonFltProxy\... which causes
# PermissionError when Python's ssl module tries to open it. Must be removed
# before any import that triggers ssl.create_default_context().
os.environ.pop("SSLKEYLOGFILE", None)

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

import model_backends as mb
import router_core as rc

log = logging.getLogger("skill-router")
logging.basicConfig(level=logging.INFO)

HERE = Path(__file__).parent
STORE = os.path.expanduser(os.environ.get("SKILL_STORE", "~/.skills"))
DB = os.path.expanduser(os.environ.get("SKILL_ROUTER_DB", str(HERE / "index.db")))
PORT = int(os.environ.get("SKILL_ROUTER_PORT", "8765"))
INJECT_MODE = os.environ.get("SKILL_ROUTER_INJECT", "pointer")

CFG = rc.RouteConfig(
    top_k=int(os.environ.get("SKILL_ROUTER_TOP_K", "34")),
    rerank_keep=int(os.environ.get("SKILL_ROUTER_RERANK_KEEP", "21")),
    rerank_margin=float(os.environ.get("SKILL_ROUTER_RERANK_MARGIN", "1.5")),
    max_accept=int(os.environ.get("SKILL_ROUTER_MAX_ACCEPT", "2")),
)

index = rc.SkillIndex(DB)

mcp = FastMCP(
    name="retrieve-skills",
    instructions=(
        "Retrieval gate over the local skill store (the store is NOT loaded "
        "into context; skills are reachable only through retrieval). At the "
        "start of any non-trivial task, call retrieve_skills with a short "
        "task description to check whether specialized instructions exist; "
        "then read_skill(name) for any skill worth applying."
    ),
)


def _gate(prompt: str, session_id: str | None) -> list[dict]:
    return rc.route(
        prompt, index, mb.get_embedder(), mb.get_reranker(), CFG,
        session_id=session_id,
    )


@mcp.tool
def retrieve_skills(query: str, k: int = 3) -> str:
    """Retrieve skills relevant to a task from the local skill store."""
    skills, _ = index.vectors()
    if not skills:
        return "skill store is empty — run POST /reindex or indexer.py first"
    cfg = rc.RouteConfig(
        top_k=max(CFG.top_k, k), rerank_keep=max(CFG.rerank_keep, k),
        rerank_margin=CFG.rerank_margin, max_accept=k,
    )
    passed = rc.route(query, index, mb.get_embedder(), mb.get_reranker(), cfg)
    passed_names = {a["name"] for a in passed}
    lines = [
        f"PASS {a['name']} (rerank {a['rerank_score']:.3f}, margin {a['rerank_margin']:.3f}): "
        f"{a['description']} [read: {a['path']}]"
        for a in passed
    ]
    q = mb.get_embedder()([query])[0]
    _, mat = index.vectors()
    for i, _sim in rc.top_k(q, mat, k + len(passed_names)):
        s = skills[i]
        if s.name not in passed_names and len(lines) < k + len(passed_names):
            lines.append(f"CANDIDATE {s.name}: {s.description} [read: {s.path}]")
    return "\n".join(lines) if lines else "no relevant skills"


@mcp.tool
def read_skill(name: str) -> str:
    """Return the full instructions of a stored skill by name."""
    skills, _ = index.vectors()
    match = next((s for s in skills if s.name == name), None)
    if match is None:
        return f"unknown skill '{name}' — use retrieve_skills first"
    try:
        text = Path(match.path).read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return f"could not read '{name}': {e}"
    return rc.skill_body(text)


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> JSONResponse:
    skills, _m = index.vectors()
    return JSONResponse(
        {
            "status": "ok", "skills_indexed": len(skills), "store": STORE,
            "embed_model": mb.EMBED_MODEL, "rerank_backend": mb.RERANK_BACKEND,
            "top_k": CFG.top_k, "rerank_keep": CFG.rerank_keep,
            "rerank_margin": CFG.rerank_margin, "inject_mode": INJECT_MODE,
        }
    )


@mcp.custom_route("/reindex", methods=["POST"])
async def reindex(_: Request) -> JSONResponse:
    skills = rc.discover_skills(STORE)
    stats = index.reindex(skills, mb.get_embedder())
    log.info("reindex: %s", stats)
    return JSONResponse(stats)


@mcp.custom_route("/route", methods=["POST"])
async def route(request: Request) -> JSONResponse:
    """Hook path: full gate + session dedup. Fail-open on any error."""
    try:
        body = await request.json()
        accepted = _gate(body.get("prompt", ""), body.get("session_id"))
        if INJECT_MODE == "body":
            for a in accepted:
                try:
                    text = Path(a["path"]).read_text(encoding="utf-8", errors="replace")
                    a["body"] = rc.skill_body(text)
                except OSError as e:
                    log.warning("body read failed for %s: %s (pointer fallback)", a["name"], e)
        log.info(
            "route: %d accepted %s", len(accepted),
            [(a["name"], round(a["rerank_score"], 3), round(a["rerank_margin"], 3)) for a in accepted],
        )
        return JSONResponse({"skills": accepted})
    except Exception:
        log.exception("route failed; failing open with no skills")
        return JSONResponse({"skills": []})


def _warmup():
    """Eagerly load models so the first route call does not block."""
    log.info("warmup: loading embedder (%s)...", mb.EMBED_MODEL)
    emb = mb.get_embedder()
    emb(["warmup"])
    log.info("warmup: embedder ready")

    if mb.RERANK_BACKEND == "local":
        log.info("warmup: loading reranker (%s)...", mb.RERANK_LOCAL_MODEL)
        rfn = mb.get_reranker()
        rfn("warmup", ["warmup doc"])
        log.info("warmup: reranker ready")
    else:
        log.info("warmup: reranker backend=%s (no local model to load)", mb.RERANK_BACKEND)

    log.info("warmup: all models hot")


if __name__ == "__main__":
    _warmup()
    mcp.run(transport="streamable-http", host="127.0.0.1", port=PORT,
            stateless_http=True, show_banner=False)
