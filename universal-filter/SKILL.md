Here is the complete transcription of the code and text from the image:

```text
● [observed] your_goal | is | map skewed nominal clause lengths into a near-normal space, set the
  upper 97.5% cutoff there, then invert back to nominal

  [inferred] this_method | gives | an asymmetric nominal cutoff that matches non-symmetric source
  distributions

  import numpy as np
  from scipy import stats

  EPS = 1e-9
  MAD_SCALE = 1.4826  # normal-consistent MAD factor

  def inv_yeojohnson(y, lam):
      y = np.asarray(y, dtype=float)
      out = np.empty_like(y)
      pos = y >= 0
      neg = ~pos

      if abs(lam) < 1e-9:
          out[pos] = np.expm1(y[pos])
      else:
          out[pos] = np.power(lam * y[pos] + 1.0, 1.0 / lam) - 1.0

      if abs(lam - 2.0) < 1e-9:
          out[neg] = 1.0 - np.exp(-y[neg])
      else:
          out[neg] = 1.0 - np.power(1.0 - (2.0 - lam) * y[neg], 1.0 / (2.0 - lam))
      return out

  def nominal_upper_bound(values_nominal, coverage=0.95):
      v = np.asarray(values_nominal, dtype=float)
      v = np.clip(v, 0.0, None)

      # 1) nominal -> log space
      x = np.log1p(v)

      # 2) robust unit normalization (median/MAD)
      med = np.median(x)
      mad = np.median(np.abs(x - med))
      s = max(MAD_SCALE * mad, np.std(x), EPS)
      z = (x - med) / s

      # 3) Yeo-Johnson to near-normal
      lam = stats.yeojohnson_normmax(z)
      y = stats.yeojohnson(z, lmbda=lam)

      # 4) percentile weights (sum to 1)
      order = np.argsort(y)
      pct = np.empty_like(y)
      denom = max(len(y) - 1, 1)
      pct[order] = np.arange(len(y)) / denom
      w = np.maximum(pct, EPS)
      w = w / w.sum()

      # weighted mean/std in transformed space
      mu = np.sum(w * y)
      sig = np.sqrt(np.sum(w * (y - mu) ** 2))
      n_eff = 1.0 / np.sum(w ** 2)

      # 5) 95% PI upper tail = 97.5%
      q_upper = 0.5 + coverage / 2.0  # 0.975 when coverage=0.95
      zq = stats.norm.ppf(q_upper)
      sig_pred = sig * np.sqrt(1.0 + 1.0 / max(n_eff, 1.0))
      y_upper = mu + zq * sig_pred

      # 6) invert back to nominal
      z_upper = inv_yeojohnson(np.array([y_upper]), lam)[0]
      x_upper = z_upper * s + med
      v_upper = np.expm1(x_upper)
      return float(max(v_upper, 0.0))

  def is_upper_outlier(candidate_nominal, upper_bound_nominal):
      return float(candidate_nominal) > float(upper_bound_nominal)

  [syllogism] If you define exclusion in transformed near-normal space at the upper 97.5% cutoff,
  then invert that boundary to nominal space, you get the correct asymmetric nominal threshold for
  /home/user/harness [⭮ main*%]

```