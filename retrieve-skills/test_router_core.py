"""Focused regression tests for the canonical retrieve-skills router core.

Retrieval daisy-chain note: the registered retrieve_skills MCP call was made
before this module was created and returned `Session not found`. That is the
retrieval regression under repair; these isolated tests continue regardless.
"""
from __future__ import annotations

import numpy as np

import router_core as rc


def _embed(texts: list[str]) -> np.ndarray:
    vocab = ("pdf", "debug", "deploy")
    return np.asarray(
        [[float(word in text.lower()) for word in vocab] for text in texts],
        dtype=np.float32,
    )


def _rerank(query: str, docs: list[str]) -> list[float]:
    query_words = set(query.lower().split())
    return [float(len(query_words & set(doc.lower().split()))) for doc in docs]


def test_frontmatter_and_body_contract() -> None:
    text = "---\nname: debugging\ndescription: Debug failures\n---\nFollow the evidence.\n"
    assert rc.parse_frontmatter(text) == {"name": "debugging", "description": "Debug failures"}
    assert rc.skill_body(text) == "Follow the evidence."
    bom_crlf = "\ufeff---\r\nname: debugging\r\ndescription: Debug failures\r\n---\r\nBody\r\n"
    assert rc.parse_frontmatter(bom_crlf) == {"name": "debugging", "description": "Debug failures"}
    assert rc.skill_body(bom_crlf) == "Body"
    assert rc.parse_frontmatter("no frontmatter") is None


def test_top_k_orders_matches_and_rejects_zero_query() -> None:
    matrix = rc._normalize(np.asarray([[1, 0], [0, 1], [0.8, 0.2]], dtype=np.float32))
    assert [index for index, _ in rc.top_k(np.asarray([1, 0]), matrix, 2)] == [0, 2]
    assert rc.top_k(np.zeros(2), matrix, 2) == []
    assert rc.top_k(np.ones(2), np.zeros((0, 0)), 2) == []


def test_route_applies_margin_cap_and_session_dedup(tmp_path) -> None:
    index = rc.SkillIndex(tmp_path / "index.db")
    skills = [
        rc.Skill("pdf", "pdf.md", "pdf document handling"),
        rc.Skill("debugging", "debug.md", "debug failure isolation"),
        rc.Skill("deploy", "deploy.md", "deploy service release"),
    ]
    index.reindex(skills, _embed)
    config = rc.RouteConfig(top_k=3, rerank_keep=3, rerank_margin=0.5, max_accept=1)

    first = rc.route("debug failure", index, _embed, _rerank, config, session_id="session-a")
    assert [item["name"] for item in first] == ["debugging"]
    assert first[0]["rerank_margin"] >= 0.5
    assert rc.route("debug failure", index, _embed, _rerank, config, session_id="session-a") == []
    assert [item["name"] for item in rc.route(
        "debug failure", index, _embed, _rerank, config, session_id="session-b"
    )] == ["debugging"]
