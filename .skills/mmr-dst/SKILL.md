---
name: mmr-dst
description: Use when tagging a corpus of text strings with salient and differentiating terms for BM25/MMR-based retrieval tuning — e.g. building a preferred-term map, a ToC, or diagnosing what an ollama query-expander prompt actually sends.
---

# mmr-dst — salient + differentiating tags via ts_vector-canonical BM25/MMR

## What it does

Tags each string in a corpus with two term lists:

- **salient** — MMR *within* the string: what the doc is about (BM25-score
  relevance, redundancy = Jaccard vs terms already chosen for the same doc).
- **differentiating** — MMR *across* strings: what sets the doc apart from
  the rest of the corpus (in-doc-frequency relevance, redundancy = how often
  the term is salient in *other* docs).

Both lanes draw from the same per-text BM25 candidate pool and differ only in
diversity axis — no cascade (differentiating is never derived from salient's
output).

All terms are lexed through Postgres `to_tsvector('english', ...)` before any
scoring runs, so every returned term is an exact `content_tsv` lexeme root —
the same roots a `tsvector`-BM25 retrieval lane matches against. This is what
makes the tags usable as a preferred-term map for query expansion: the terms
line up 1:1 with what the retriever's index actually stores.

## When to use

- Building a per-skill/per-doc preferred-term map for a retrieval ToC.
- Deciding which terms should get boosted (differentiating) vs which just
  describe the topic broadly (salient) when composing a `to_tsquery`.
- Diagnosing an ollama-based query-expander prompt: what's actually being
  sent, how large it is, and whether that's a plausible timeout cause.

## Files

- `mmr_dst.py` — the whole skill, one file, four sections:
  1. **lexing** — `lex_texts()`: Postgres `to_tsvector` lexeme stream per text.
  2. **BM25 + two-lane MMR** — `tag_token_lists()`: candidate scoring, salient
     pass, differentiating pass (closed-form re-rank, not greedy — see the
     module docstring for why).
  3. **public entry point** — `tag_texts()`: lex + tag in one call.
  4. **expander prompt diagnostic** — `dump_prompt()`: renders the exact
     prompt `data-science-skills/query_expander.py` sends to ollama, without
     making a live call, plus size stats.

  Collapsed from three former files (`ts_lexer.py`, `bm25_salient_terms.py`,
  `mmr-dst.py`) plus a fourth (`dump_prompt.py`) — same responsibilities, no
  behavioral change, kept as clearly delimited sections in one module instead
  of four files. Read the module docstring for the full math, the two-lane
  design rationale, and a "lessons learned" list of dead ends already ruled
  out (hapax noise, idf inversion, etc.) — don't re-litigate those.

- `tag_corpus.py` — batch-tags every `.md` in a corpus folder, one
  `<skill>.tags.json` per file. Imports `mmr_dst` directly
  (`from mmr_dst import lex_texts, tag_token_lists`). Run modes:
  `python tag_corpus.py --gate` (battery only, no writes) or `--run` (gate,
  then full corpus write). Corpus folder via `MMR_DST_CORPUS` env var.

## Usage

```python
from mmr_dst import tag_texts

for salient, differentiating in tag_texts(["text one", "text two"]):
    ...  # both are lists of Postgres to_tsvector('english') lexemes
```

```
python mmr_dst.py --dump-prompt "your query here" [output.md]
```

## Requires

- `psycopg` importable; a reachable Postgres with `to_tsvector` (the
  `langchain_postgres` container, or set `MMR_DST_PG_DSN`).
- For `dump_prompt()` / `--dump-prompt`: `data-science-skills/query_expander.py`
  importable, with its ToC (`metadata_expander.json`) present.

## Known finding (2026-07-21/22, not yet resolved)

For the query `"reinforcement learning methods"`, the assembled USER message
sent to the ollama query-expander is **520,351 chars / ~130,318 approx
tokens**, `num_ctx=139264` — the full 11-topic ToC is sent on every call
regardless of query content. This is the leading root-cause candidate for
observed timeouts/wedged-server behavior under repeated live calls (GPU
contention and thinking-suppression were each checked and ruled out
separately). Next step: decide whether to prune the ToC per-call or accept
the fixed cost.
