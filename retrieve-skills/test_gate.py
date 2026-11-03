"""Stub battery for skill-router (no model downloads, no network beyond localhost).

Gates (>=3 varied fixtures each, per quality-gate policy):
1. frontmatter parsing        — 5 fixtures: normal, folded multiline, missing
                                description, no frontmatter, BOM+CRLF
2. checkpoint re-embed counts — initial / unchanged / one-changed + prune
3. top_k ordering             — 3 synthetic vector sets
4. route gate                 — 4 prompts: accept-1 (margin), reject-all (flat
                                margins), NLI reject/accept when enabled, cap-2
5. session dedup              — same skill never injected twice per session
6. hook fail-open             — server down -> exit 0, empty stdout
7. hook contract              — stub HTTP server -> valid hookSpecificOutput JSON

Fixtures vary entities/structure/values; none seeded from a live failure case.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import numpy as np
import pytest

import router_core as rc

HERE = Path(__file__).parent

# ---------- stub scorers ----------

VOCAB = ["pdf", "merge", "spreadsheet", "formula", "deploy", "kubernetes",
         "chart", "colors", "invoice", "email"]


def stub_embed(texts):
    """Deterministic bag-of-words embedding over VOCAB."""
    out = np.zeros((len(texts), len(VOCAB)), dtype=np.float32)
    for i, t in enumerate(texts):
        words = t.lower().split()
        for j, v in enumerate(VOCAB):
            out[i, j] = float(sum(1 for w in words if v in w))
    return out


def stub_rerank(query, docs):
    """Keyword-overlap score."""
    q = set(query.lower().split())
    return [float(len(q & set(d.lower().split()))) for d in docs]


def make_nli(table, default=0.1):
    """NLI stub keyed by skill name found in the hypothesis."""
    def nli_fn(premise, hypothesis):
        for name, p in table.items():
            if f"'{name}'" in hypothesis:
                return p
        return default
    return nli_fn


# ---------- fixtures ----------

SKILL_FILES = {
    "pdf-tools/SKILL.md": "---\nname: pdf-tools\ndescription: Merge split and edit pdf files\n---\nBody: pdf instructions here.\n",
    "xlsx-wrangler/SKILL.md": "---\nname: xlsx-wrangler\ndescription: >\n  Build and repair spreadsheet files,\n  formula auditing included\n---\nBody: spreadsheet instructions.\n",
    "no-desc/SKILL.md": "---\nname: no-desc\n---\nShould be skipped: missing description.\n",
    "no-fm/SKILL.md": "Just a readme-looking file with no frontmatter at all.\n",
    "deploy-bot/SKILL.md": "﻿---\r\nname: deploy-bot\r\ndescription: Deploy services to kubernetes clusters\r\n---\r\nBody: deploy instructions.\r\n",
}


@pytest.fixture()
def store(tmp_path):
    for rel, content in SKILL_FILES.items():
        p = tmp_path / "store" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return tmp_path / "store"


@pytest.fixture()
def index(tmp_path):
    return rc.SkillIndex(tmp_path / "idx.db")


# ---------- gate 1: parsing ----------

def test_discover_parses_and_skips(store):
    skills = rc.discover_skills(store)
    names = {s.name for s in skills}
    assert names == {"pdf-tools", "xlsx-wrangler", "deploy-bot"}  # 2 skipped
    xlsx = next(s for s in skills if s.name == "xlsx-wrangler")
    assert "spreadsheet" in xlsx.description and "\n" not in xlsx.description
    bot = next(s for s in skills if s.name == "deploy-bot")  # BOM+CRLF survived
    assert bot.description == "Deploy services to kubernetes clusters"


def test_skill_body_strips_frontmatter():
    body = rc.skill_body(SKILL_FILES["pdf-tools/SKILL.md"])
    assert body.startswith("Body: pdf instructions")
    assert "name:" not in body


# ---------- gate 2: checkpointing ----------

def test_reindex_checkpoints(store, index):
    calls = {"n": 0}

    def counting_embed(texts):
        calls["n"] += len(texts)
        return stub_embed(texts)

    skills = rc.discover_skills(store)
    s1 = index.reindex(skills, counting_embed)
    assert (s1["embedded"], calls["n"]) == (3, 3)          # initial: all embedded

    s2 = index.reindex(skills, counting_embed)
    assert (s2["embedded"], calls["n"]) == (0, 3)          # unchanged: none

    skills[0] = rc.Skill(skills[0].name, skills[0].path, skills[0].description + " and ocr")
    s3 = index.reindex(skills, counting_embed)
    assert (s3["embedded"], calls["n"]) == (1, 4)          # one changed: one

    s4 = index.reindex(skills[:2], counting_embed)          # one removed: pruned
    assert s4["removed"] == 1
    assert len(index.vectors()[0]) == 2


# ---------- gate 3: top_k ----------

def test_top_k_ordering():
    mat = rc._normalize(np.array([[1, 0, 0], [0, 1, 0], [0.9, 0.1, 0]], dtype=np.float32))
    got = [i for i, _ in rc.top_k(np.array([1.0, 0, 0]), mat, 2)]
    assert got == [0, 2]                                    # set 1: nearest two
    got = [i for i, _ in rc.top_k(np.array([0, 1.0, 0]), mat, 3)]
    assert got[0] == 1                                      # set 2: axis match first
    assert rc.top_k(np.zeros(3), mat, 2) == []              # set 3: zero query -> []
    assert rc.top_k(np.array([1.0, 0, 0]), np.zeros((0, 0), dtype=np.float32), 2) == []


# ---------- gates 4+5: route gate + session dedup ----------

def routed(store, index, prompt, nli_table, cfg=None, session=None):
    skills = rc.discover_skills(store)
    index.reindex(skills, stub_embed)
    return rc.route(prompt, index, stub_embed, stub_rerank, make_nli(nli_table),
                    cfg or rc.RouteConfig(), session_id=session)


def test_gate_accepts_matching_skill(store, index):
    """Live gate is the rerank margin (NLI is off by default)."""
    out = routed(store, index, "merge these pdf files into one pdf",
                 {"pdf-tools": 0.95, "xlsx-wrangler": 0.05, "deploy-bot": 0.05})
    assert [a["name"] for a in out] == ["pdf-tools"]
    assert out[0]["entailment"] is None                     # gate disabled
    assert out[0]["rerank_margin"] >= rc.RouteConfig().rerank_margin


def test_gate_rejects_when_no_candidate_clears_margin(store, index):
    """Flat/off-topic scores -> every margin collapses to ~0 -> no skills."""
    out = routed(store, index, "pdf spreadsheet formula deploy kubernetes chart",
                 {"pdf-tools": 0.9, "xlsx-wrangler": 0.9, "deploy-bot": 0.9})
    assert out == []


def test_gate_nli_rejects_below_threshold(store, index):
    """Optional NLI stage still rejects when explicitly enabled."""
    out = routed(store, index, "merge these pdf files",
                 {"pdf-tools": 0.4, "xlsx-wrangler": 0.2, "deploy-bot": 0.1},
                 cfg=rc.RouteConfig(nli_enabled=True))
    assert out == []

    out = routed(store, index, "merge these pdf files",
                 {"pdf-tools": 0.95, "xlsx-wrangler": 0.2, "deploy-bot": 0.1},
                 cfg=rc.RouteConfig(nli_enabled=True))
    assert [a["name"] for a in out] == ["pdf-tools"]
    assert out[0]["entailment"] == 0.95


def test_gate_caps_at_max_accept(store, index):
    """Margin gate opened wide so the cap itself is what is under test."""
    out = routed(store, index, "pdf spreadsheet formula deploy kubernetes chart",
                 {"pdf-tools": 0.9, "xlsx-wrangler": 0.9, "deploy-bot": 0.9},
                 cfg=rc.RouteConfig(max_accept=2, rerank_margin=-10.0))
    assert len(out) == 2


def test_session_dedup(store, index):
    table = {"pdf-tools": 0.95}
    out1 = routed(store, index, "merge pdf files", table, session="sess-1")
    assert [a["name"] for a in out1] == ["pdf-tools"]
    out2 = routed(store, index, "another pdf merge please", table, session="sess-1")
    assert out2 == []                                       # not re-injected
    out3 = routed(store, index, "merge pdf files", table, session="sess-2")
    assert [a["name"] for a in out3] == ["pdf-tools"]       # fresh session unaffected


# ---------- gates 6+7: hook edge ----------

def run_hook(port, prompt="merge pdfs", timeout="1.0"):
    # Inherit the real env: a hand-built env omits SystemRoot, without which
    # the Python interpreter cannot seed its hash randomization on Windows and
    # dies before hook.py ever runs.
    env = {**os.environ,
           "SKILL_ROUTER_PORT": str(port),
           "SKILL_ROUTER_TIMEOUT": timeout}
    return subprocess.run(
        [sys.executable, str(HERE / "hook.py")],
        input=json.dumps({"prompt": prompt, "session_id": "s"}),
        capture_output=True, text=True, env=env, timeout=15,
    )


def test_hook_fail_open_when_server_down():
    r = run_hook(port=1)                                    # nothing listens on :1
    assert r.returncode == 0 and r.stdout.strip() == ""


def test_hook_fail_open_on_garbage_stdin():
    r = subprocess.run([sys.executable, str(HERE / "hook.py")], input="not json{{",
                       capture_output=True, text=True, timeout=15)
    assert r.returncode == 0 and r.stdout.strip() == ""


class StubHandler(BaseHTTPRequestHandler):
    payload = {"skills": [{"name": "pdf-tools", "path": "/x/SKILL.md",
                           "description": "Merge pdf files"}]}

    def do_POST(self):
        body = json.dumps(self.payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def test_hook_contract_against_stub_server():
    srv = HTTPServer(("127.0.0.1", 0), StubHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        r = run_hook(port=srv.server_port)
    finally:
        srv.shutdown()
    assert r.returncode == 0
    out = json.loads(r.stdout)
    hso = out["hookSpecificOutput"]
    assert hso["hookEventName"] == "UserPromptSubmit"
    assert "pdf-tools" in hso["additionalContext"]
    assert "read /x/SKILL.md" in hso["additionalContext"]   # pointer mode line


def test_hook_body_mode_block():
    from hook import build_context
    ctx = build_context([{"name": "a", "path": "/p", "description": "d", "body": "DO THE THING"}])
    assert '<skill name="a">' in ctx and "DO THE THING" in ctx
    assert build_context([]) == ""
