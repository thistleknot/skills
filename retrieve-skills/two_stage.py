import os, numpy as np, router_core as rc
from model_backends import get_embedder, get_reranker

TOP_K = int(os.environ.get("TK", "20"))
KEEP  = int(os.environ.get("KEEP", "5"))

idx = rc.SkillIndex("index.db")
skills, mat = idx.vectors()
embed = get_embedder(); rerank = get_reranker()

prompt = os.environ.get("P", "what is the capital of France?")
q = np.asarray(embed([prompt]), dtype=np.float32)[0]
recall = rc.top_k(q, mat, TOP_K)

print(f"PROMPT: {prompt}\n  {len(skills)} skills indexed | top_k={TOP_K} keep={KEEP}\n")
print("--- STAGE 1: semantic top_k (cosine) ---")
for r,(i,s) in enumerate(recall,1):
    print(f"{r:>3}. {s:+.4f}  {skills[i].name}")

docs = [f"{skills[i].name}: {skills[i].description}" for i,_ in recall]
rr = rerank(prompt, docs)
ranked = sorted(zip(recall, rr), key=lambda t: -t[1])[:KEEP]

print(f"\n--- STAGE 2: colbert-v2-64 rerank -> keep {KEEP} ---")
for r,((i,sim),sc) in enumerate(ranked,1):
    moved = [j for j,(k,_) in enumerate(recall,1) if k==i][0]
    print(f"{r:>3}. {sc:+.4f}  (was #{moved}, cos {sim:+.4f})  {skills[i].name}")
