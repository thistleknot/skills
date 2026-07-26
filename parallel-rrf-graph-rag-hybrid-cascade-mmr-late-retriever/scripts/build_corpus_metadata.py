"""Generate skills_master/metadata.json — the corpus ToC augmented with tags,
consumed by the query expander as its ZERO-SHOT prompt context (so the ToC/tag
vocabulary is not re-derived at query time).

One-and-done corpus-wide: derive from pgvector now; going forward it is
regenerated at the END of ingestion (ingest_skills.ingest() calls this).

Shape (topic-grouped ToC + per-topic tag cloud — compact enough for a prompt):
  {
    "collection": ..., "n_skills": N, "generated_at": ISO,
    "topics": {
      "<topic>": {"count": n, "tags": [top entity tags], "skills": [leaf-slug, ...]},
      ...
    }
  }

Run:  python build_corpus_metadata.py            # derive from pgvector -> skills_master/metadata.json
"""

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).parent))
import eval_ablation as ab   # noqa: E402  (PG_RAW, COLLECTION)

SKILLS_MASTER = Path(r"C:\Users\user\Documents\wiki\data science\stackskills\skills_master")
OUT = SKILLS_MASTER / "metadata.json"
TOP_TAGS_PER_TOPIC = 40
_JUNK = re.compile(r"^\d|_.*_.*_.*_.*_|^.{41,}$")   # numeric-lead / >=5-underscore / >40 chars


def _clean_tag(t: str) -> bool:
    t = (t or "").strip()
    return bool(t) and len(t) >= 3 and not _JUNK.search(t)


def build(conn) -> Path:
    """Derive metadata.json from pgvector cmetadata (skill_slug, topic, entities)."""
    by_topic_skills = defaultdict(set)
    by_topic_tagcount = defaultdict(Counter)
    tag_topics = defaultdict(set)          # tag -> topics it appears in (for hub filtering)
    with conn.cursor(name="meta") as cur:
        cur.itersize = 2000
        cur.execute("""SELECT e.cmetadata->>'skill_slug', e.cmetadata->>'topic',
                              e.cmetadata->'entities'
                       FROM langchain_pg_embedding e JOIN langchain_pg_collection col
                       ON col.uuid=e.collection_id WHERE col.name=%s""", (ab.COLLECTION,))
        for slug, topic, ents in cur:
            if not slug or not topic:
                continue
            by_topic_skills[topic].add(slug.split("/")[-1])
            for e in (ents or []):
                if _clean_tag(e):
                    by_topic_tagcount[topic][e] += 1
                    tag_topics[e].add(topic)
    n_topics = len(by_topic_skills)
    hub_cut = max(3, int(0.6 * n_topics))   # tag in >60% of topics = too generic, drop
    topics = {}
    for topic in sorted(by_topic_skills):
        tags = [t for t, _ in by_topic_tagcount[topic].most_common()
                if len(tag_topics[t]) <= hub_cut][:TOP_TAGS_PER_TOPIC]
        topics[topic] = {
            "count": len(by_topic_skills[topic]),
            "tags": tags,
            "skills": sorted(by_topic_skills[topic]),
        }
    meta = {
        "collection": ab.COLLECTION,
        "n_skills": sum(len(v["skills"]) for v in topics.values()),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "topics": topics,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return OUT


def build_standalone() -> Path:
    conn = psycopg.connect(**ab.PG_RAW)
    try:
        return build(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    p = build_standalone()
    meta = json.loads(p.read_text(encoding="utf-8"))
    print(f"wrote {p}")
    print(f"  {meta['n_skills']} skills across {len(meta['topics'])} topics")
    for t, d in meta["topics"].items():
        print(f"  {t:22} {d['count']:>4} skills · tags: {', '.join(d['tags'][:8])} ...")
