"""In-process retrieval probe: replicates the server gate without HTTP."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_backends as mb, router_core as rc

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("SKILL_ROUTER_DB", os.path.join(HERE, "index.db"))
index = rc.SkillIndex(DB)
skills, mat = index.vectors()
print(f"indexed={len(skills)} dim={mat.shape[1] if mat.size else 0} backend={mb.RERANK_BACKEND} embed={mb.EMBED_MODEL}")
if not skills:
    sys.exit("EMPTY INDEX - run indexer.py")

cfg = rc.RouteConfig(
    top_k=int(os.environ.get("SKILL_ROUTER_TOP_K", "8")),
    rerank_keep=int(os.environ.get("SKILL_ROUTER_RERANK_KEEP", "5")),
    rerank_margin=float(os.environ.get("SKILL_ROUTER_RERANK_MARGIN", "1.5")),
    max_accept=2,
)
print("cfg:", cfg)

PROBES = [
    ("draft an EARS requirements spec for a new feature", True),
    ("update the memory bank with this session's decisions", True),
    ("what is the capital of France", False),
    ("tell me a joke", False),
    ("review this plan document for gaps", True),
    ("build a react agent loop with tool calling", True),
]

t0 = time.time()
emb, rr = mb.get_embedder(), mb.get_reranker()
print(f"models warm in {time.time()-t0:.1f}s\n")

ok = 0
for prompt, expect in PROBES:
    t = time.time()
    acc = rc.route(prompt, index, emb, rr, cfg)
    got = bool(acc)
    verdict = "OK " if got == expect else "MISS"
    ok += got == expect
    print(f"{verdict} expect={'HIT ' if expect else 'MISS'} [{time.time()-t:.2f}s] {prompt!r}")
    for a in acc:
        print(f"      -> {a['name']}  score={a['rerank_score']:.3f} margin={a['rerank_margin']:.3f} base={a['rerank_baseline']:.3f} sim={a['recall_sim']:.3f}")
    if not acc:
        # show what was rejected and by how much
        q = emb([prompt])[0]
        recall = rc.top_k(q, mat, cfg.top_k)
        cands = [(skills[i], s) for i, s in recall]
        scores = rr(prompt, [f"{s.name}: {s.description}" for s, _ in cands])
        import numpy as np
        base = float(np.median(scores))
        top = sorted(zip(cands, scores), key=lambda t: -t[1])[:3]
        for (s, _sim), sc in top:
            print(f"      xx {s.name}  score={sc:.3f} margin={sc-base:.3f}")
print(f"\n{ok}/{len(PROBES)} probes matched expectation")
