#!/usr/bin/env python
"""Expose memory-index to ADK agents via `BaseMemoryService`.

This is an EXPORT SEAM, not a backend. memory-index remains the system of record;
this lets a `google-adk` agent read our memories through the interface it expects.

Two deliberate asymmetries, both load-bearing:

* **Read-mostly.** `add_session_to_memory` is a no-op. Sessions enter our store through
  `events_store.log_event` on the hook path and are distilled by `mem dream` -- a second,
  ADK-shaped ingest path would bypass distillation and race the dreamer.

* **Retrievals here do not count toward promotion.** `cmd_search` bumps `hits` and can
  promote log->memory->skill. This adapter passes `count_hits=False` semantics by querying
  Chroma directly, because a retrieval by some external agent is not evidence that *our*
  operator found the memory useful. Letting it count would let an outside caller
  manufacture promotions.

Scores are dropped at the boundary: ADK's `SearchMemoryResponse` has nowhere to put them.
That is a limitation of the interface, not of the store -- see
`~/.claude/docs/adk-basememoryservice-eval-2026-08-05.md` §2(a).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from google.adk.memory.base_memory_service import (
    BaseMemoryService,
    SearchMemoryResponse,
)
from google.adk.memory.memory_entry import MemoryEntry
from google.genai import types

if TYPE_CHECKING:
    from google.adk.sessions.session import Session

DEFAULT_K = 8


def _default_mem_dir() -> Path:
    env = os.environ.get("MEM_DIR")
    if env:
        return Path(env)
    return Path.home() / ".claude" / "memory"


class MemoryIndexMemoryService(BaseMemoryService):
    """Read-only `BaseMemoryService` over the memory-index Chroma collection."""

    def __init__(self, mem_dir: Optional[Path] = None, k: int = DEFAULT_K):
        self._mem_dir = Path(mem_dir) if mem_dir else _default_mem_dir()
        self._k = k

    async def add_session_to_memory(self, session: Session):
        """Intentionally a no-op. Ingest is owned by the hook path + `mem dream`."""
        return None

    async def search_memory(
        self, *, app_name: str, user_id: str, query: str
    ) -> SearchMemoryResponse:
        # Imported lazily so that merely importing this module does not require
        # chroma or a live embedding service.
        import mem

        col = mem.get_collection(self._mem_dir)
        if col.count() == 0:
            return SearchMemoryResponse()

        qv = mem.embed([query], is_query=True)[0]
        res = col.query(
            query_embeddings=[qv], n_results=min(self._k, col.count())
        )

        ids = res["ids"][0]
        if not ids:
            return SearchMemoryResponse()
        metas = res["metadatas"][0]
        docs = res["documents"][0]
        dists = res["distances"][0]

        out: list[MemoryEntry] = []
        for mid, meta, doc, dist in zip(ids, metas, docs, dists):
            meta = meta or {}
            out.append(
                MemoryEntry(
                    id=mid,
                    author="memory-index",
                    content=types.Content(
                        parts=[types.Part(text=doc)], role="user"
                    ),
                    # The score has no home in MemoryEntry proper, so it is preserved
                    # here rather than silently discarded.
                    custom_metadata={
                        "name": meta.get("name"),
                        "type": meta.get("type"),
                        "kind": meta.get("kind"),
                        "scope": meta.get("scope"),
                        "file": meta.get("file"),
                        "score": 1.0 - float(dist),
                        "hits": int(meta.get("hits", 0)),
                        "counted_toward_promotion": False,
                    },
                )
            )
        return SearchMemoryResponse(memories=out)
