#!/usr/bin/env python3
"""CLI reindexer for skill-router.

Purpose: build or refresh the SQLite embedding index without running a server.
Preconditions: the configured embedding model is installed or cached.
Failure modes: errors propagate; successful writes commit after all upserts.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import model_backends as mb
import router_core as rc

HERE = Path(__file__).parent


def main() -> None:
    ap = argparse.ArgumentParser(description="Reindex skill descriptions")
    ap.add_argument("--store", default=os.path.expanduser(os.environ.get("SKILL_STORE", "~/.skills")))
    ap.add_argument("--db", default=os.path.expanduser(os.environ.get("SKILL_ROUTER_DB", str(HERE / "index.db"))))
    args = ap.parse_args()

    skills = rc.discover_skills(args.store)
    if not skills:
        print(f"no skills found under {args.store} (need <dir>/SKILL.md with name+description frontmatter)")
        return
    index = rc.SkillIndex(args.db)
    stats = index.reindex(skills, mb.get_embedder())
    print(f"indexed: {stats['total']} skills, re-embedded {stats['embedded']}, removed {stats['removed']} -> {args.db}")


if __name__ == "__main__":
    main()
