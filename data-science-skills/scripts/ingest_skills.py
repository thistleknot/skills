"""Ingest skills_master/ -> langchain PGVector (cmetadata) + neo4j entity graph.

Pipeline per chunk: Docling HybridChunker -> nomic embedding (via langchain
OllamaEmbeddings) -> KG entity extraction (LLM S-P-O + surface-preserve
canonicalization + WordNet enrichment + spaCy NER) -> stored as a langchain
Document (entity data in cmetadata JSONB) -> entity co-occurrence graph upserted
into the dedicated dss-neo4j.

Design (see ../references/ingestion.md):
- Storage is langchain `PGVector` (collection `data_science_skills`), NOT a
  hand-rolled table. Entity/SPO/synset/hypernym data lives in `cmetadata`
  (the operator's `ts_vector`-like signal), usable with pgvector metadata
  filtering. No separate BM25 sparse column.
- **Canonical entity id = normalized surface span** (`ridge_regression`,
  `gradient_descent`). WordNet synsets/hypernyms are kept only as *enrichment*
  tokens for plain single common words — they NEVER replace a domain term's
  identity. This is a deliberate departure from kg_ontology's synset-canonical
  approach: WordNet mis-resolves ML terms ("ridge regression" -> "mountain
  ridge"), which would poison the graph that is the retrieval backbone.
- The graph is persisted in neo4j during ingestion (ready to expand at query
  time), not rebuilt from Postgres per query.
- Full drop-and-reingest is canonical (`--reset`).

Preconditions:
    - Ollama serving nomic-embed-text at localhost:11434 (embeddings only; no LLM).
    - triplet-extract + spaCy en_core_web_sm + NLTK wordnet/punkt installed.
    - langchain_postgres reachable (db=langchain, port 5432).
    - dss-neo4j reachable at bolt://localhost:7688 (docker/neo4j-compose.yml).
    - spaCy en_core_web_sm; NLTK wordnet + stopwords.

Run:
    python ingest_skills.py --reset      # canonical full rebuild
    python ingest_skills.py --resume     # skip chunk ids already stored
"""

import argparse
import re
import sys
from pathlib import Path

try:
    from docling.chunking import HybridChunker
    from docling.document_converter import DocumentConverter
    from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
except ImportError:
    HybridChunker = DocumentConverter = HuggingFaceTokenizer = None

try:
    import spacy
except ImportError:
    spacy = None

try:
    import triplet_extract as te   # ClausIE/OpenIE-style deterministic SPO extractor
except ImportError:
    te = None

import psycopg
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_postgres import PGVector
from neo4j import GraphDatabase
from nltk.corpus import wordnet as wn
from nltk.tokenize import sent_tokenize

SKILLS_MASTER = Path(r"C:\Users\user\Documents\wiki\data science\stackskills\skills_master")

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
# KG extraction is fully deterministic (spaCy dependency parse + WordNet) — NO
# LLM. An LLM extraction call was ~12-18s/chunk (~days for the corpus); spaCy
# is milliseconds, so the full ingest is minutes.

CHUNK_TOKENIZER = "sentence-transformers/all-MiniLM-L6-v2"
MAX_CHUNK_TOKENS = 1900

PG_CONN = "postgresql+psycopg://langchain:langchain@localhost:5432/langchain"
PG_RAW = dict(host="localhost", port=5432, dbname="langchain",
              user="langchain", password="langchain")
COLLECTION = "data_science_skills"

NEO4J_URI = "bolt://localhost:7688"
N_TAGS = 5


# =============================================================================
# Entity resolution — surface-preserve canonical + WordNet enrichment
# =============================================================================

def normalize_entity(text: str) -> str:
    """Canonical id for a domain term: ASCII-folded, lowercased, punctuation
    stripped, spaces -> underscores. 'Ridge Regression' -> 'ridge_regression'.
    ASCII fold first so unicode math ('r²', em-dashes, decode artifacts like
    'r�') don't leak mojibake into node ids. This IS the graph node identity."""
    t = text.lower().encode("ascii", "ignore").decode()   # drop non-ASCII (², —, �)
    t = re.sub(r"[^a-z0-9\s-]", "", t)
    t = re.sub(r"[\s-]+", "_", t).strip("_")
    return t


# =============================================================================
# Deterministic S-P-O extraction (triplet-extract) + per-word WordNet
#
# The operator's process: NLTK sentences -> triplet_extractor (ClausIE/OpenIE,
# spaCy-backed, NO LLM) -> for each S/P/O head word, its synset + hypernym ->
# store as metadata key-fields. ~51ms/sentence warm; the full corpus is minutes,
# not the hours an LLM extraction call per chunk would take.
# =============================================================================

def _head_wn(phrase: str, verb: bool = False):
    """(synset_name, hypernym_name) for a phrase's head word. NP head = last
    word; verb head = first. WordNet-lemmatized (morphy), POS-constrained.
    Returns (None, None) if no synset. No spaCy call — head heuristic + WN."""
    words = re.findall(r"[a-zA-Z]+", phrase.lower())
    if not words:
        return (None, None)
    head = words[0] if verb else words[-1]
    pos = wn.VERB if verb else wn.NOUN
    lemma = wn.morphy(head, pos) or head
    syns = wn.synsets(lemma, pos=pos) or wn.synsets(lemma)
    if not syns:
        return (None, None)
    hyp = syns[0].hypernyms()
    return (syns[0].name(), hyp[0].name() if hyp else None)


def extract_triplets(text: str, extractor) -> list:
    """NLTK sentences -> triplet-extract SPO -> per-word synset+hypernym.
    Returns storable triplet dicts. Fully deterministic (no LLM)."""
    out = []
    for sent in sent_tokenize(text):
        try:
            triples = extractor.extract_triplet_objects(sent)
        except Exception:  # noqa: BLE001 - one bad sentence shouldn't abort the chunk
            continue
        for tr in triples:
            subj = (tr.subject or "").strip()
            rel = (tr.relation or "").strip()
            obj = (tr.object or "").strip()
            if not subj or not rel:
                continue
            s_syn, s_hyp = _head_wn(subj)
            p_syn, p_hyp = _head_wn(rel, verb=True)
            o_syn, o_hyp = _head_wn(obj) if obj else (None, None)
            out.append({
                "subject": subj, "predicate": rel, "object": obj or None,
                "subject_id": normalize_entity(subj),
                "predicate_id": normalize_entity(rel),
                "object_id": normalize_entity(obj) if obj else None,
                "subject_synset": s_syn, "subject_hypernym": s_hyp,
                "predicate_synset": p_syn, "predicate_hypernym": p_hyp,
                "object_synset": o_syn, "object_hypernym": o_hyp,
                "confidence": round(float(getattr(tr, "confidence", 1.0)), 2),
            })
    return out


# spaCy labels that are noise for a technical ML corpus (chunk-reference
# numbers, dates, percentages) — they flood the graph and out-degree the real
# domain terms. The SPO triplets are the meaningful entity source; keep only
# concept-ish spaCy labels alongside them.
_NOISE_SPACY_LABELS = {"CARDINAL", "ORDINAL", "DATE", "TIME", "PERCENT",
                       "MONEY", "QUANTITY"}


def parse_frontmatter(md_path: Path) -> dict:
    """Extract the skill file's YAML frontmatter into structured metadata (once
    per file — it's identical across the file's chunks). Captured as its own
    cmetadata rather than discarded, so name/description/sources/topic/
    merged_slugs are queryable + displayable. Lightweight regex parse (no yaml
    dep); the skill files have a fixed, simple frontmatter shape."""
    text = md_path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    fm = m.group(1)
    def field(key):
        mm = re.search(rf"^{key}:\s*(.+)$", fm, re.MULTILINE)
        return mm.group(1).strip().strip('"') if mm else None
    books = re.findall(r"-\s*book:\s*(.+)$", fm, re.MULTILINE)
    merged = re.search(r"^merged_slugs:\s*\[(.*?)\]", fm, re.MULTILINE)
    return {
        "skill_name": field("name"),
        "skill_description": field("description"),
        "source_books": [b.strip() for b in books],
        "merged_slugs": [s.strip() for s in merged.group(1).split(",") if s.strip()] if merged else [],
    }


def _strip_kg_noise(text: str) -> str:
    """Remove YAML frontmatter + source/chunk provenance lines before KG
    extraction (frontmatter is captured separately by parse_frontmatter). Left
    in, spaCy would tag chunk-ref numbers (CARDINAL) and book titles (ORG) as
    entities that dominate the graph. ENTITY extraction only — the full text is
    still embedded for the dense vector."""
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)  # leading frontmatter
    lines = [ln for ln in text.splitlines()
             if not re.match(r"\s*(- book:|chunks:|sources:|merged_slugs:|enriched:)", ln)]
    return "\n".join(lines)


def _is_junk_entity(eid: str) -> bool:
    """Reject entity ids that carry no domain meaning: empty, too short,
    numeric-only (chunk refs like '214'), or a whole clause rather than a term.
    triplet-extract returns full-clause objects ('a non-hierarchical approach
    that pre-specifies...') — those make 200-char nodes that are useless in the
    graph; a real entity is a short noun phrase, so cap at 5 words / 48 chars."""
    if (not eid) or len(eid) < 2 or eid.replace("_", "").isdigit():
        return True
    return len(eid) > 48 or eid.count("_") >= 5


def extract_spacy_entities(nlp, chunk_text: str) -> list:
    if nlp is None:
        return []
    doc = nlp(chunk_text)
    out = []
    for e in doc.ents:
        if not e.text.strip() or e.label_ in _NOISE_SPACY_LABELS:
            continue
        eid = normalize_entity(e.text)
        if _is_junk_entity(eid):
            continue
        out.append({"text": e.text, "label": e.label_, "id": eid})
    return out


def chunk_entity_ids(triplets: list, spacy_entities: list) -> list:
    """Canonical ids that become graph nodes: triplet subjects+objects (not
    predicates — those are edges/relations) + spaCy entities. Deduped."""
    ids = set()
    for t in triplets:
        for key in ("subject_id", "object_id"):
            if t.get(key) and not _is_junk_entity(t[key]):
                ids.add(t[key])
    ids.update(e["id"] for e in spacy_entities if e.get("id") and not _is_junk_entity(e["id"]))
    return sorted(ids)


# =============================================================================
# neo4j graph
# =============================================================================

def neo4j_reset(driver) -> None:
    with driver.session() as s:
        s.run("MATCH (n) DETACH DELETE n")
        s.run("CREATE CONSTRAINT dss_entity_id IF NOT EXISTS "
              "FOR (e:Entity) REQUIRE e.id IS UNIQUE")
        s.run("CREATE CONSTRAINT dss_skill_slug IF NOT EXISTS "
              "FOR (sk:Skill) REQUIRE sk.slug IS UNIQUE")
        s.run("CREATE CONSTRAINT dss_chunk_id IF NOT EXISTS "
              "FOR (c:Chunk) REQUIRE c.id IS UNIQUE")


def neo4j_write_chunk(driver, chunk_id: str, skill_slug: str, topic: str,
                      entity_ids: list) -> None:
    """Upsert the full graph for one chunk so query-time density + expansion are
    pure-neo4j (return chunk_ids, fetch content from pg):
      (Chunk)-[:HAS_ENTITY]->(Entity), (Chunk)-[:OF_SKILL]->(Skill),
      (Entity)-[:IN_SKILL]->(Skill), (Entity)-[:CO_OCCURS {weight}]-(Entity)."""
    pairs = [[a, b] for i, a in enumerate(entity_ids) for b in entity_ids[i + 1:]]
    with driver.session() as s:
        s.run("MERGE (sk:Skill {slug:$slug}) SET sk.topic=$topic", slug=skill_slug, topic=topic)
        s.run("MERGE (c:Chunk {id:$cid}) SET c.skill_slug=$slug "
              "WITH c MATCH (sk:Skill {slug:$slug}) MERGE (c)-[:OF_SKILL]->(sk)",
              cid=chunk_id, slug=skill_slug)
        if entity_ids:
            s.run("""
                UNWIND $ids AS eid
                MERGE (e:Entity {id: eid})
                WITH e
                MATCH (sk:Skill {slug:$slug}) MERGE (e)-[:IN_SKILL]->(sk)
                WITH e
                MATCH (c:Chunk {id:$cid}) MERGE (c)-[:HAS_ENTITY]->(e)
            """, ids=entity_ids, slug=skill_slug, cid=chunk_id)
        if pairs:
            s.run("""
                UNWIND $pairs AS p
                MATCH (a:Entity {id: p[0]}), (b:Entity {id: p[1]})
                MERGE (a)-[r:CO_OCCURS]-(b)
                ON CREATE SET r.weight = 1
                ON MATCH  SET r.weight = r.weight + 1
            """, pairs=pairs)


def neo4j_skill_tags(driver) -> None:
    """Top-N most-connected entities per skill -> Skill.tags (the ToC tags)."""
    with driver.session() as s:
        s.run("""
            MATCH (e:Entity)-[:IN_SKILL]->(sk:Skill)
            OPTIONAL MATCH (e)-[r:CO_OCCURS]-()
            WITH sk, e, coalesce(sum(r.weight),0) AS deg
            ORDER BY deg DESC
            WITH sk, collect(e.id)[0..$n] AS tags
            SET sk.tags = tags
        """, n=N_TAGS)


# =============================================================================
# Orchestration
# =============================================================================

def existing_ids(conn_raw) -> set:
    """chunk ids already stored for this collection (langchain_pg_embedding.id),
    for --resume. Empty if the collection tables don't exist yet."""
    try:
        with psycopg.connect(**conn_raw) as c, c.cursor() as cur:
            cur.execute("""
                SELECT e.id FROM langchain_pg_embedding e
                JOIN langchain_pg_collection col ON col.uuid = e.collection_id
                WHERE col.name = %s
            """, (COLLECTION,))
            return {r[0] for r in cur.fetchall()}
    except Exception:
        return set()


def ingest(reset: bool = False, resume: bool = False, no_kg: bool = False) -> int:
    if HybridChunker is None:
        raise RuntimeError("docling not installed")
    nlp = None if no_kg else (spacy.load("en_core_web_sm") if spacy else None)
    if not no_kg and nlp is None:
        print("WARNING: spaCy unavailable — skipping named-entity extraction")
    # Reusable OpenIE extractor (shares the spaCy nlp). Entailment off: we want
    # the base S-P-O facts, not entailed variants that add graph noise.
    extractor = None
    if not no_kg and te is not None and nlp is not None:
        extractor = te.OpenIEExtractor(nlp=nlp, enable_entailment=False, fast=True)
    elif not no_kg and te is None:
        print("WARNING: triplet_extract unavailable — no SPO triplets will be extracted")

    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_URL)
    store = PGVector(embeddings=embeddings, collection_name=COLLECTION,
                     connection=PG_CONN, use_jsonb=True)
    if reset:
        store.delete_collection()
        store = PGVector(embeddings=embeddings, collection_name=COLLECTION,
                         connection=PG_CONN, use_jsonb=True)

    driver = GraphDatabase.driver(NEO4J_URI, auth=None)
    if reset:
        neo4j_reset(driver)

    done = existing_ids(PG_RAW) if resume else set()

    converter = DocumentConverter()
    tokenizer = HuggingFaceTokenizer.from_pretrained(
        model_name=CHUNK_TOKENIZER, max_tokens=MAX_CHUNK_TOKENS)
    chunker = HybridChunker(tokenizer=tokenizer, merge_peers=True)

    md_files = sorted(SKILLS_MASTER.glob("*/*.md"))
    n_ingested = 0
    for i, path in enumerate(md_files, 1):
        skill_slug = f"{path.parent.name}/{path.stem}"
        topic = path.parent.name
        frontmatter = parse_frontmatter(path)   # once per file, attached to every chunk
        doc = converter.convert(str(path)).document

        docs, ids = [], []
        for j, chunk in enumerate(chunker.chunk(doc)):
            chunk_id = f"{skill_slug}::c{j}"
            if chunk_id in done:
                continue
            raw_text = chunk.text
            header_path = list(getattr(chunk.meta, "headings", None) or [])

            if no_kg:
                # Fast cosine-only pass: embeddings + frontmatter only, NO
                # per-chunk LLM extraction or graph. The KG/graph signal (the
                # slow part — one LLM call per chunk) is backfilled later via a
                # normal --resume run. Gets a queryable dense corpus in minutes
                # instead of the ~hours a full KG ingest takes.
                triplets, spacy_ents, ent_ids, enrich_tokens = [], [], [], []
            else:
                # KG extraction runs on frontmatter/provenance-stripped text so
                # source book names + chunk-ref numbers don't become graph nodes.
                # The full raw_text is still embedded and stored.
                kg_text = _strip_kg_noise(raw_text)
                triplets = extract_triplets(kg_text, extractor) if extractor else []
                spacy_ents = extract_spacy_entities(nlp, kg_text)
                ent_ids = chunk_entity_ids(triplets, spacy_ents)
                # Drop source-book names that leak in as ORG entities from prose
                # mentions ("Data Mining for Business Analytics frames it as...").
                book_stop = {normalize_entity(b) for b in frontmatter.get("source_books", [])}
                ent_ids = [e for e in ent_ids if e not in book_stop]
                # vertical-alignment tokens = all synset + hypernym names across triplets
                enrich_tokens = sorted({
                    v for t in triplets
                    for k, v in t.items()
                    if k.endswith(("_synset", "_hypernym")) and v})

            # page_content = contextualized text (heading breadcrumb prepended)
            # per Docling best practice — that's what gets embedded and returned.
            docs.append(Document(
                page_content=chunker.contextualize(chunk),
                metadata={
                    "chunk_id": chunk_id, "skill_slug": skill_slug, "topic": topic,
                    "chunk_index": j, "header_path": header_path,
                    "raw_text": raw_text,
                    "triplets": triplets, "spacy_entities": spacy_ents,
                    "entities": ent_ids,          # flat canonical ids (metadata filter + graph join)
                    "enrich_tokens": enrich_tokens,  # WordNet vertical-alignment tokens
                    **frontmatter,                # skill_name/description/source_books/merged_slugs
                }))
            ids.append(chunk_id)
            if not no_kg:
                neo4j_write_chunk(driver, chunk_id, skill_slug, topic, ent_ids)

        if docs:
            store.add_documents(docs, ids=ids)   # langchain embeds page_content
            n_ingested += len(docs)

        if i % 25 == 0 or i == len(md_files):
            print(f"  {i}/{len(md_files)} files ({n_ingested} chunks)", flush=True)

    if not no_kg:
        neo4j_skill_tags(driver)
    driver.close()
    mode = " (cosine-only, no KG/graph)" if no_kg else ""
    print(f"ingested {n_ingested} chunks from {len(md_files)} files{mode}")
    return n_ingested


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reset", action="store_true", help="drop collection + graph, full rebuild")
    ap.add_argument("--resume", action="store_true", help="skip chunk ids already stored")
    ap.add_argument("--no-kg", action="store_true",
                    help="fast cosine-only pass: embeddings + frontmatter, skip per-chunk "
                         "LLM extraction + graph (backfill later with a normal --resume run)")
    args = ap.parse_args()
    ingest(reset=args.reset, resume=args.resume, no_kg=args.no_kg)
