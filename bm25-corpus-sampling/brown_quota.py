import numpy as np
from scipy.stats import median_abs_deviation
from sklearn.preprocessing import PowerTransformer
from nltk.corpus import brown

pool = {}
for cat in brown.categories():
    paras = []
    for fid in brown.fileids(categories=cat):
        for para in brown.paras(fid):
            tokens = [w.lower() for s in para for w in s if w.isalpha()]
            if tokens:
                paras.append(len(tokens))
    pool[cat] = paras

cats = sorted(pool.keys())
counts = np.array([len(pool[c]) for c in cats], dtype=float)

x = np.log1p(counts)
med = np.median(x)
mad = median_abs_deviation(x, scale=1.4826)
x = (x - med) / (mad + 1e-9)
pt = PowerTransformer(method='yeo-johnson', standardize=False)
x = pt.fit_transform(x.reshape(-1, 1)).ravel()

# weighted sum = 1: shift to positive, normalize linearly (NOT softmax)
# preserves relative ordering while compressing range so tail gets quota
x = x - x.min() + 1e-9
weights = x / x.sum()

N = 2000
quotas = np.round(weights * N).astype(int)
quotas = np.maximum(quotas, 1)
excess = int(quotas.sum()) - N
for idx in np.argsort(quotas)[::-1]:
    if excess <= 0: break
    trim = min(int(quotas[idx]) - 1, excess)
    quotas[idx] -= trim
    excess -= trim

total = int(counts.sum())
print(f"Total paragraphs (full corpus): {total:,}")
print(f"Target sample:                  {N:,}  ({N/total*100:.1f}% of corpus)")
print()
print(f"{'Category':<20} {'Total':>7} {'%corpus':>8} {'Quota':>7} {'%sample':>8} {'ratio':>7}")
print("-" * 62)
for i, cat in enumerate(cats):
    c = int(counts[i])
    q = int(quotas[i])
    print(f"{cat:<20} {c:>7,} {c/total*100:>7.1f}%  {q:>7} {q/N*100:>7.1f}%   {q/c*100:>5.1f}%")
print("-" * 62)
print(f"{'TOTAL':<20} {total:>7,} {'100.0%':>8}  {quotas.sum():>7} {'100.0%':>8}")
