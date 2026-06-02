"""Walk-forward (out-of-sample) HMM regime classification.

Closes the one full-sample-fit gap on the tactical-allocation path. The HMM is
refit annually on an expanding window; each window is standardized using *only*
its own training statistics; and each out-of-sample week is classified by
Viterbi-decoding the expanding prefix [start, t] and taking the last state. No
observation dated after week t ever influences week t's label, so the regime
series is safe to feed a backtested timing strategy.

HMM state IDs are arbitrary and can permute between fits, so each fit's states
are mapped to calm / transition / crisis by sorting that fit's emission means on
the volatility feature. This keeps labels semantically stable across refits.

Scope note: use these labels for the Regime-Tilt *strategy*. The full-sample
labels (hmm_viterbi_3state) remain correct for the in-sample regime-conditional
*risk* table, which is a descriptive application, not a predictive one.
"""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM

log = logging.getLogger(__name__)

LABELS_BY_N = {2: ["calm", "stress"], 3: ["calm", "transition", "crisis"]}


def _fit_one(X_train_std: np.ndarray, n_states: int, n_seeds: int,
             n_iter: int = 500):
    """Best-of-n_seeds converged Gaussian HMM by log-likelihood."""
    best, best_ll = None, -np.inf
    seeds = [42] if n_seeds == 1 else list(range(n_seeds))
    for seed in seeds:
        try:
            m = GaussianHMM(n_components=n_states, covariance_type="full",
                            n_iter=n_iter, random_state=seed, tol=1e-4)
            m.fit(X_train_std)
            if not m.monitor_.converged:
                continue
            ll = m.score(X_train_std)
            if ll > best_ll:
                best, best_ll = m, ll
        except Exception as e:
            log.debug(f"  seed {seed}: {type(e).__name__}: {e}")
    return best


def _label_map(model: GaussianHMM, columns: list[str], vol_feature: str,
               n_states: int) -> dict:
    """Map this fit's state IDs to calm/transition/crisis by ascending vol."""
    means = pd.DataFrame(model.means_, columns=columns)
    order = means[vol_feature].sort_values().index.tolist()  # low -> high vol
    names = LABELS_BY_N.get(n_states, [f"regime_{i}" for i in range(n_states)])
    return {int(state_id): name for state_id, name in zip(order, names)}


def walk_forward_regimes(raw_features: pd.DataFrame, n_states: int = 3,
                         min_train_years: int = 5, refit_months: int = 12,
                         vol_feature: str = "SX5E_rv_60d",
                         n_seeds: int = 5) -> pd.Series:
    """Return an out-of-sample regime-label Series (calm / transition / crisis).

    Parameters
    ----------
    raw_features : unstandardized HMM input matrix with NaN rows already dropped
        (e.g. the `raw` returned by regimes.data_prep.assemble_hmm_inputs).
    min_train_years : length of the initial expanding window before the first
        out-of-sample classification.
    refit_months : EM is rerun on the expanding window this often (12 = annual).
    """
    raw = raw_features.dropna().sort_index()
    cols = list(raw.columns)
    if vol_feature not in cols:
        raise ValueError(f"{vol_feature!r} not in HMM features {cols}")
    idx = raw.index
    first_train_end = idx.min() + pd.DateOffset(years=min_train_years)
    refit_dates = pd.date_range(first_train_end, idx.max(),
                                freq=f"{refit_months}MS")

    labels = pd.Series(index=idx, dtype=object, name="regime_wf")
    model, label_map = None, {}
    train_mu = train_sd = None
    next_refit_i, n_refits = 0, 0
    min_train_obs = min_train_years * 40  # ~weeks guard (>=5y of weekly data)

    oos_idx = idx[idx > first_train_end]
    for t in oos_idx:
        # (Re)fit when a scheduled refit date has been reached, on data <= t-1wk.
        while next_refit_i < len(refit_dates) and t >= refit_dates[next_refit_i]:
            cutoff = t - pd.Timedelta(weeks=1)
            train = raw.loc[:cutoff]
            if len(train) >= min_train_obs:
                mu = train.mean()
                sd = train.std().replace(0.0, 1.0)
                m = _fit_one(((train - mu) / sd).values, n_states, n_seeds)
                if m is not None:
                    model, train_mu, train_sd = m, mu, sd
                    label_map = _label_map(model, cols, vol_feature, n_states)
                    n_refits += 1
            next_refit_i += 1
        if model is None:
            continue
        # Classify week t: Viterbi-decode the expanding prefix [start, t],
        # standardized with the frozen training stats, and take the last state.
        prefix = raw.loc[:t]
        Xp = ((prefix - train_mu) / train_sd).values
        state_t = int(model.predict(Xp)[-1])
        labels.loc[t] = label_map.get(state_t)

    out = labels.dropna()
    log.info(f"Walk-forward HMM: {n_refits} refits (every {refit_months}m), "
             f"{len(out)} out-of-sample labels "
             f"({out.index.min().date()} -> {out.index.max().date()})")
    return out


def agreement(full_sample_labels: pd.Series, wf_labels: pd.Series) -> float:
    """Fraction of overlapping weeks where the two labelings agree."""
    common = full_sample_labels.index.intersection(wf_labels.index)
    if len(common) == 0:
        return float("nan")
    return float((full_sample_labels.loc[common] == wf_labels.loc[common]).mean())
