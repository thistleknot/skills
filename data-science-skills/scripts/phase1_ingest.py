"""Phase 1 — whole-skill embedding into pgvector. 1 document : 1 skill.

The simplest thing that works: read each skills_master/<topic>/<slug>.md, embed
the WHOLE file as one document, store in the langchain PGVector collection with
skill name/topic from the folder path. No hybrid chunking, no KG extraction, no
graph — those are later phases. This is cheap (1467 embeddings, minutes) and
proves the storage+retrieval path end-to-end.

Phase 2 (phase2_ingest.py) sends each skill through Docling HybridChunker and
adds chunk_index + doc_id per chunk.

Run:  python phase1_ingest.py            # ingest all skills (reset collection)
      python phase1_ingest.py --resume   # skip skills already stored
"""

import argparse
import sys
from pathlib import Path

import psycopg
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_postgres import PGVector

SKILLS_MASTER = Path(r"C:\Users\user\Documents\wiki\data science\stackskills\skills_master")
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
PG_CONN = "postgresql+psycopg://langchain:langchain@localhost:5432/langchain"
PG_RAW = dict(host="localhost", port=5432, dbname="langchain",
              user="langchain", password="langchain")
COLLECTION = "data_science_skills"
# nomic ctx is 2048 tokens; a few skills exceed that as one blob. Phase 1 caps
# by characters (~4 chars/token) so nomic never HTTP-500s on over-length input.
# Phase 2's hybrid chunking is the real fix for long skills.
MAX_CHARS = 7200


def existing_slugs() -> set:
    try:
        with psycopg.connect(**PG_RAW) as c, c.cursor() as cur:
            cur.execute("""SELECT e.cmetadata->>'skill_slug'
                           FROM langchain_pg_embedding e JOIN langchain_pg_collection col
                           ON col.uuid=e.collection_id WHERE col.name=%s""", (COLLECTION,))
            return {r[0] for r in cur.fetchall()}
    except Exception:
        return set()


def ingest(reset: bool = False, resume: bool = False) -> int:
    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_URL)
    store = PGVector(embeddings=embeddings, collection_name=COLLECTION,
                     connection=PG_CONN, use_jsonb=True)
    if reset:
        store.delete_collection()
        store = PGVector(embeddings=embeddings, collection_name=COLLECTION,
                         connection=PG_CONN, use_jsonb=True)

    done = existing_slugs() if resume else set()
    md_files = sorted(SKILLS_MASTER.glob("*/*.md"))

    docs, ids, batch = [], [], 0
    n = 0
    for i, path in enumerate(md_files, 1):
        skill_slug = f"{path.parent.name}/{path.stem}"    # topic/skill, from folder
        if skill_slug in done:
            continue
        topic = path.parent.name
        text = path.read_text(encoding="utf-8", errors="replace")[:MAX_CHARS]
        docs.append(Document(page_content=text, metadata={
            "doc_id": skill_slug, "skill_slug": skill_slug,
            "skill_name": path.stem, "topic": topic,
        }))
        ids.append(skill_slug)
        if len(docs) >= 100:                              # embed+insert in batches
            store.add_documents(docs, ids=ids); n += len(docs); docs, ids = [], []
            print(f"  {i}/{len(md_files)} skills embedded ({n})", flush=True)
    if docs:
        store.add_documents(docs, ids=ids); n += len(docs)
    print(f"phase 1 done: {n} skills embedded into {COLLECTION}")
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reset", action="store_true", help="drop + recreate the collection")
    ap.add_argument("--resume", action="store_true", help="skip skills already stored")
    args = ap.parse_args()
    ingest(reset=args.reset or not args.resume, resume=args.resume)
