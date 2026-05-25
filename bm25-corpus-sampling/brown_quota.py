import numpy as np
from scipy.stats import median_abs_deviation, norm
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

# weighted sum = 1: CDF bin areas (consecutive Gaussian CDF differences sorted by z_yj)
# Categories near z=0 (median-sized) get the most Gaussian mass.
# Extreme outliers (news z=+6.64, humor z=-5.68) land in thin tails → small quota.
# "news starts at 97%" = learned is at CDF≈96.7%; news's bin runs from there to +∞.
order = np.argsort(x)
z_sorted = x[order]
cdf_vals = norm.cdf(z_sorted)
weights_sorted = np.diff(cdf_vals, prepend=0.0)
weights_sorted /= weights_sorted.sum()
weights = np.empty_like(weights_sorted)
weights[order] = weights_sorted

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
print(f"{'Category':<20} {'z_yj':>7} {'CDF':>7} {'Δ CDF':>7} {'Total':>7} {'Quota':>6} {'%sample':>8}")
print("-" * 72)
cdf_by_cat = dict(zip(cats, norm.cdf(x)))
delta_by_cat = dict(zip(cats, weights))
for i, cat in enumerate(cats):
    c = int(counts[i])
    q = int(quotas[i])
    print(f"{cat:<20} {x[i]:>7.2f} {cdf_by_cat[cat]:>7.3f} {delta_by_cat[cat]:>7.3f} {c:>7,} {q:>6} {q/N*100:>7.1f}%")
print("-" * 72)
print(f"{'TOTAL':<20} {'':>7} {'':>7} {'':>7} {total:>7,} {quotas.sum():>6} {'100.0%':>8}")
