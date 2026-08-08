"""
Collinearity test: measure how much each sparse view contributes independently.

Tests:
  1. TruncatedSVD explained variance per view (tfidf-only, token-only, char-only, all)
  2. CCA collinearity between tfidf-only z and all-views z
  3. Community NMI: Louvain on tfidf-z graph vs Louvain on all-views z graph

Require: retrieval_eval.db exists with cached embeddings (embeddings are not used here,
         but the corpus is loaded the same way the eval does it).
"""
import sys
import numpy as np
import scipy.sparse as sp
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from sklearn.cross_decomposition import CCA
from sklearn.metrics import normalized_mutual_info_score
import community as community_louvain
import networkx as nx
import nltk

sys.path.insert(0, str(Path(__file__).parent))

# ── corpus (copied from eval) ─────────────────────────────────────────────────
nltk.download("brown", quiet=True)
from nltk.corpus import brown

AE_DIM   = 64
CHAR_N   = 3
N_PROXY  = 2000
SEED     = 42
AE_THRESH = 0.40   # intermediate threshold for NMI test

def load_corpus():
    docs = []
    for fid in brown.fileids():
        cat = brown.categories(fid)[0]
        sents = brown.sents(fid)
        para, para_toks = [], []
        for sent in sents:
            para.extend(sent); para_toks.extend([t.lower() for t in sent])
            if len(para_toks) > 30:
                docs.append({"text": " ".join(para), "tokens": para_toks, "cat": cat})
                para, para_toks = [], []
    return docs

print("Loading corpus...", flush=True)
docs = load_corpus()
rng  = np.random.default_rng(SEED)
proxy_idx = rng.choice(len(docs), size=min(N_PROXY, len(docs)), replace=False).tolist()
proxy_docs = [docs[i] for i in proxy_idx]
texts      = [d["text"] for d in proxy_docs]

print(f"  Proxy corpus: {len(proxy_docs)} docs", flush=True)

# ── build three view matrices ─────────────────────────────────────────────────
print("Building view matrices...", flush=True)

tfidf_vec = TfidfVectorizer(max_features=8000, sublinear_tf=True).fit(texts)
token_vec = CountVectorizer(min_df=2).fit(texts)
char_vec  = CountVectorizer(analyzer="char", ngram_range=(CHAR_N,CHAR_N), min_df=2).fit(texts)

X_tfidf = tfidf_vec.transform(texts)
X_token = token_vec.transform(texts).astype(np.float32)
X_char  = (char_vec.transform(texts) > 0).astype(np.float32)
X_all   = normalize(sp.hstack([X_tfidf, X_token, X_char], format="csr"), norm="l2")
X_tfidf_n = normalize(X_tfidf, norm="l2")

print(f"  TF-IDF: {X_tfidf.shape[1]} | Token: {X_token.shape[1]} | Char: {X_char.shape[1]} | All: {X_all.shape[1]}", flush=True)

# ── explained variance per view ───────────────────────────────────────────────
print("\n── Explained Variance (TruncatedSVD, k=64) ──", flush=True)

def ev(X, label):
    svd = TruncatedSVD(n_components=AE_DIM, random_state=SEED).fit(X)
    v = svd.explained_variance_ratio_.sum()
    print(f"  {label:<20s}  {v:.3f}")
    return svd

svd_tfidf = ev(X_tfidf_n, "tfidf-only")
ev(X_token,             "token-count-only")
ev(X_char,              "char-bitvec-only")
svd_all   = ev(X_all,   "all-views")

# ── CCA collinearity: tfidf-z vs all-views-z ─────────────────────────────────
print("\n── CCA Collinearity: tfidf-z vs all-views-z ──", flush=True)
z_tfidf = normalize(svd_tfidf.transform(X_tfidf_n), norm="l2")
z_all   = normalize(svd_all.transform(X_all),       norm="l2")

N_CCA = min(10, AE_DIM)
cca   = CCA(n_components=N_CCA, max_iter=2000)
z1_c, z2_c = cca.fit_transform(z_tfidf, z_all)
corrs = [np.corrcoef(z1_c[:,i], z2_c[:,i])[0,1] for i in range(N_CCA)]
mean_corr = float(np.mean(corrs))
print(f"  Mean canonical correlation ({N_CCA} components): {mean_corr:.3f}")
print(f"  Per-component: {[f'{c:.2f}' for c in corrs]}")
if mean_corr > 0.70:
    print("  → Views COLLINEAR: TF-IDF dominates z; token/char add little")
elif mean_corr < 0.40:
    print("  → Views ORTHOGONAL: all-views z captures distinct signal from tfidf alone")
else:
    print("  → Borderline: check community NMI below")

# ── Community NMI: tfidf-z graph vs all-views-z graph ────────────────────────
print(f"\n── Community NMI (Louvain, ae_thresh={AE_THRESH}) ──", flush=True)

sample_n = min(300, len(proxy_docs))
sample_i = list(range(sample_n))
z_t = z_tfidf[:sample_n]
z_a = z_all[:sample_n]

def build_cos_graph(Z, thresh):
    sim = Z @ Z.T
    G = nx.Graph()
    G.add_nodes_from(range(len(Z)))
    for i in range(len(Z)):
        for j in range(i+1, len(Z)):
            if sim[i,j] > thresh:
                G.add_edge(i, j, weight=float(sim[i,j]))
    return G

print(f"  Building graphs on {sample_n} docs...", flush=True)
G_tfidf = build_cos_graph(z_t, AE_THRESH)
G_all   = build_cos_graph(z_a, AE_THRESH)

part_tfidf = community_louvain.best_partition(G_tfidf, weight="weight", random_state=SEED)
part_all   = community_louvain.best_partition(G_all,   weight="weight", random_state=SEED)

labels_t = [part_tfidf.get(i, -1) for i in range(sample_n)]
labels_a = [part_all.get(i,   -1) for i in range(sample_n)]
nmi = normalized_mutual_info_score(labels_t, labels_a)

dens_t = G_tfidf.number_of_edges() / max(1, sample_n*(sample_n-1)/2)
dens_a = G_all.number_of_edges()   / max(1, sample_n*(sample_n-1)/2)
ncom_t = len(set(labels_t))
ncom_a = len(set(labels_a))

print(f"  tfidf-z graph:     {G_tfidf.number_of_edges()} edges, density={dens_t:.3f}, {ncom_t} communities")
print(f"  all-views-z graph: {G_all.number_of_edges()} edges,   density={dens_a:.3f}, {ncom_a} communities")
print(f"  NMI(tfidf_communities, all_communities) = {nmi:.3f}")
if nmi > 0.80:
    print("  → Same partition: multi-view z does not change community structure vs tfidf-only")
elif nmi < 0.50:
    print("  → Different partitions: multi-view views add retrieval-relevant structure")
else:
    print("  → Moderate agreement: partial signal gain from additional views")

print("\nDone.", flush=True)
