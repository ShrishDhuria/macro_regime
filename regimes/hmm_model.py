"""Gaussian HMM fit with multi-seed robustness."""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM

log = logging.getLogger(__name__)


def fit_hmm(features: pd.DataFrame, n_states: int = 2,
            random_state: int = 42, n_iter: int = 500,
            n_seeds: int = 1) -> dict:
    """Fit Gaussian HMM. If n_seeds > 1, keep the best converged solution by LL."""
    X = features.values
    seeds = [random_state] if n_seeds == 1 else list(range(n_seeds))
    best_model, best_ll, best_seed = None, -np.inf, None

    for seed in seeds:
        try:
            model = GaussianHMM(n_components=n_states, covariance_type="full",
                                n_iter=n_iter, random_state=seed, tol=1e-4)
            model.fit(X)
            if not model.monitor_.converged:
                log.warning(f"  seed {seed}: did not converge, skipping")
                continue
            ll = model.score(X)
            if ll > best_ll:
                best_ll, best_model, best_seed = ll, model, seed
        except Exception as e:
            log.warning(f"  seed {seed}: {type(e).__name__}: {e}")

    if best_model is None:
        raise RuntimeError(f"No seed converged for n_states={n_states}")
    if n_seeds > 1:
        log.info(f"  best of {n_seeds} seeds: seed={best_seed}, LL={best_ll:.2f}")

    model = best_model
    viterbi_states = model.predict(X)
    state_probs = model.predict_proba(X)
    viterbi = pd.Series(viterbi_states, index=features.index, name="regime")
    probabilities = pd.DataFrame(state_probs, index=features.index,
                                 columns=[f"P(regime={i})" for i in range(n_states)])
    transition_matrix = pd.DataFrame(model.transmat_,
                                     index=[f"from_{i}" for i in range(n_states)],
                                     columns=[f"to_{i}" for i in range(n_states)])
    emission_means = pd.DataFrame(model.means_,
                                  index=[f"regime_{i}" for i in range(n_states)],
                                  columns=features.columns)
    return {"model": model, "viterbi": viterbi, "probabilities": probabilities,
            "transition_matrix": transition_matrix, "emission_means": emission_means,
            "log_likelihood": best_ll, "score_per_obs": best_ll / len(X),
            "converged": model.monitor_.converged, "seed": best_seed}


def label_regimes_by_volatility(emission_means: pd.DataFrame,
                                 vol_feature: str = "SX5E_rv_60d") -> dict:
    """HMM state IDs are arbitrary; sort by vol so labels are interpretable."""
    sorted_states = emission_means[vol_feature].sort_values()
    n = len(sorted_states)
    if n == 2:
        names = ["calm", "stress"]
    elif n == 3:
        names = ["calm", "transition", "crisis"]
    else:
        names = [f"regime_{i}" for i in range(n)]
    return {int(state.split("_")[1]): name
            for state, name in zip(sorted_states.index, names)}
