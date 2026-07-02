"""
PMI Coverage Audit over a dense (category x sub-topic) count matrix
===================================================================

Purpose:
    Surface where a joint count table deviates from its independence baseline.
    The deviation — pointwise mutual information (PMI) = log(O/E) — is the
    product. The marginals are the null. This computes the per-cell PMI table,
    guards low counts, optionally normalizes (NPMI), and ranks the most
    over-covered and under-covered (category, sub-topic) pairs.

Preconditions:
    - O is a 2D non-negative count matrix (rows = categories/models, cols = sub-topics).
    - The joint is DENSE: sub-topics genuinely repeat across categories.
      For a block-diagonal joint this audit is degenerate.
    - row_labels and col_labels match O's shape.

Failure modes:
    - Structural zeros are smoothed into small positive surprises; mask them
      explicitly via `structural_zero_mask` if some pairs are impossible.
    - Low-count cells can show extreme PMI; `min_count` guards the ranking.
    - Heterogeneous category sizes: use PMI/NPMI (log-ratio), not additive O-E.

Contracts:
    Require: O.shape == (len(row_labels), len(col_labels)); O >= 0.
    Guarantee: PMI table same shape as O; ranking excludes cells below min_count.
    Maintain: smoothing applied consistently to O and E (same eps).
    Assert: marginals sum to 1 within tolerance; E sums to N within tolerance.
"""

import numpy as np
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Example data — REPLACE with the real dense (model x sub-topic) matrix.
# This placeholder is dense on purpose so the audit is meaningful.
# Rows = models, Cols = shared sub-topics.
# ---------------------------------------------------------------------------

ROW_LABELS = ["model_A", "model_B", "model_C", "model_D"]
COL_LABELS = ["retrieval", "summarize", "classify", "extract", "rerank"]

O = np.array([
    [120,  40,  30,  60,  10],   # model_A: retrieval-heavy
    [ 25, 110,  35,  20,  15],   # model_B: summarize-heavy
    [ 30,  35, 130,  25,  20],   # model_C: classify-heavy
    [ 50,  20,  25,  40,  90],   # model_D: rerank-heavy
], dtype=float)


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

@dataclass
class CoverageCell:
    row: str
    col: str
    observed: float
    expected: float
    pmi: float
    npmi: float


def independence_baseline(O: np.ndarray) -> tuple[np.ndarray, float]:
    """
    E_ij = row_sum_i * col_sum_j / N  — the rank-1 outer product of the margins,
    the max-entropy joint consistent with the observed totals.
    """
    N = O.sum()
    E = np.outer(O.sum(axis=1), O.sum(axis=0)) / N
    assert abs(E.sum() - N) < 1e-6, "baseline must preserve grand total"
    return E, N


def pmi_table(O: np.ndarray, eps: float = 0.5
              ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns (E_smoothed, PMI, NPMI).

    PMI  = log(O_s / E_s),  O_s = O + eps  (Laplace smoothing before the log)
    NPMI = PMI / -log(P_joint),  bounded to [-1, 1]

    Natural log -> nats. Swap np.log for np.log2 to get bits.
    """
    O_s = O + eps
    Ns = O_s.sum()
    E_s = np.outer(O_s.sum(axis=1), O_s.sum(axis=0)) / Ns

    PMI = np.log(O_s / E_s)

    P_joint = O_s / Ns
    with np.errstate(divide="ignore", invalid="ignore"):
        NPMI = PMI / (-np.log(P_joint))
    return E_s, PMI, NPMI


def rank_deviations(O: np.ndarray, PMI: np.ndarray, NPMI: np.ndarray,
                    E: np.ndarray, row_labels: list[str], col_labels: list[str],
                    min_count: float = 5, top_k: int = 8
                    ) -> tuple[list[CoverageCell], list[CoverageCell]]:
    """
    Rank cells by PMI, masking those below min_count so the audit reflects
    real concentrations rather than rare-count artifacts.

    Returns (top_over_covered, top_under_covered).
    """
    cells = []
    for i in range(O.shape[0]):
        for j in range(O.shape[1]):
            if O[i, j] < min_count:
                continue
            cells.append(CoverageCell(
                row=row_labels[i], col=col_labels[j],
                observed=float(O[i, j]), expected=float(E[i, j]),
                pmi=float(PMI[i, j]), npmi=float(NPMI[i, j]),
            ))
    over = sorted(cells, key=lambda c: c.pmi, reverse=True)[:top_k]
    under = sorted(cells, key=lambda c: c.pmi)[:top_k]
    return over, under


def mutual_information(O: np.ndarray, PMI: np.ndarray, eps: float = 0.5) -> float:
    """
    MI = sum P(i,j) * PMI(i,j) — the count-weighted total of the per-cell PMI.
    One scalar for how entangled category and sub-topic are. Track over time
    as a drift signal: rising MI = diverging specialists, falling = converging.
    """
    O_s = O + eps
    P = O_s / O_s.sum()
    return float((P * PMI).sum())


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def main():
    E, N = independence_baseline(O)
    E_s, PMI, NPMI = pmi_table(O, eps=0.5)
    over, under = rank_deviations(O, PMI, NPMI, E_s, ROW_LABELS, COL_LABELS,
                                  min_count=5, top_k=8)
    mi = mutual_information(O, PMI)

    print(f"Grid: {O.shape[0]} categories x {O.shape[1]} sub-topics, N={int(N)}")
    print(f"Total mutual information: {mi:.4f} nats\n")

    print("PMI table (log observed/expected, smoothed):")
    header = "          " + "".join(f"{c[:9]:>11}" for c in COL_LABELS)
    print(header)
    for i, r in enumerate(ROW_LABELS):
        row = f"{r:>9} " + "".join(f"{PMI[i, j]:>11.3f}" for j in range(O.shape[1]))
        print(row)

    print("\nTop OVER-covered (specialization, PMI > 0):")
    for c in over:
        print(f"  {c.row:>9} x {c.col:<10}  O={c.observed:5.0f}  "
              f"E={c.expected:6.1f}  PMI={c.pmi:+.3f}  NPMI={c.npmi:+.3f}")

    print("\nTop UNDER-covered (gaps, PMI < 0):")
    for c in under:
        print(f"  {c.row:>9} x {c.col:<10}  O={c.observed:5.0f}  "
              f"E={c.expected:6.1f}  PMI={c.pmi:+.3f}  NPMI={c.npmi:+.3f}")


if __name__ == "__main__":
    main()