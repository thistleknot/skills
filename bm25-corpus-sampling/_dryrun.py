"""Dry-run validation: corpus build, PI pruning, vocab, Jaccard — no Ollama needed."""
import brown_retrieval_eval as b
import numpy as np
from scipy.stats import median_abs_deviation

import nltk; nltk.download("brown", quiet=True)

docs = b.build_corpus()
print(f"corpus: {len(docs)} docs, {len(set(d['category'] for d in docs))} cats")

lens = [d["token_len"] for d in docs]
med = np.median(lens)
mad = median_abs_deviation(lens, scale=1.4826)
lo, hi = med - 1.96 * mad, med + 1.96 * mad
pruned = sum(1 for l in lens if not (lo <= l <= hi))
print(f"PI=[{lo:.0f},{hi:.0f}], pruned={pruned}")

idx = b.pi_stratified_sample(docs, n_sample=2000, seed=42)
print(f"sample size: {len(idx)}")

cv = b.ClosedVocab(docs)
print(f"Token vocab: {cv.V:,}  Char-3gram vocab: {cv.C:,}")

bv0 = cv.token_bitvec(docs[0]["tokens"])
bv1 = cv.token_bitvec(docs[1]["tokens"])
j = b.jaccard_bitvec(bv0, bv1)
print(f"Jaccard(doc0,doc1)={j:.4f}")

ids = cv.token_ids(docs[0]["tokens"])[:5]
back = cv.unpack_token_ids(ids)
print(f"token_ids[:5]={ids} -> {back}")


# MultiViewProjector smoke test
from sklearn.feature_extraction.text import TfidfVectorizer
proxy_tfidf = TfidfVectorizer(max_features=8_000, sublinear_tf=True, analyzer="word")
proxy_tfidf.fit([docs[i]["text"] for i in idx])

ae = b.MultiViewProjector(z_dim=64)
ae.fit(idx, docs, proxy_tfidf, cv)
print(f"AE explained_var: {ae.explained_variance():.3f}")

Z = ae.transform(idx[:5], docs, proxy_tfidf, cv)
print(f"Z shape: {Z.shape}  |  norms: {[round(float(__import__('numpy').linalg.norm(z)),4) for z in Z]}")

G = b.build_ae_graph(idx[:10], docs, ae, proxy_tfidf, cv)
print(f"AE graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

print("OK")
