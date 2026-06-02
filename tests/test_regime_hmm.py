"""HMM regime detection + the no-lookahead guarantee of the walk-forward labeller."""
import numpy as np
import pytest

from regimes.hmm_model import fit_hmm, label_regimes_by_volatility
from regimes.walk_forward_hmm import walk_forward_regimes


# --------------------------------------------------------------------------
# In-sample fit: the model must recover an obvious two-regime structure
# --------------------------------------------------------------------------
def test_hmm_recovers_two_regimes(two_regime_features):
    feats, truth = two_regime_features
    res = fit_hmm(feats, n_states=2, n_seeds=3)

    # Transition matrix and posteriors are valid probabilities.
    np.testing.assert_allclose(res["transition_matrix"].values.sum(axis=1),
                               np.ones(2), rtol=1e-6)
    np.testing.assert_allclose(res["probabilities"].values.sum(axis=1),
                               np.ones(len(feats)), rtol=1e-6)

    # The state labelled "stress" must have the higher equity-vol emission mean.
    name_by_state = label_regimes_by_volatility(res["emission_means"])
    means = res["emission_means"]["SX5E_rv_60d"]
    calm_state = [s for s, nm in name_by_state.items() if nm == "calm"][0]
    stress_state = [s for s, nm in name_by_state.items() if nm == "stress"][0]
    assert means.loc[f"regime_{stress_state}"] > means.loc[f"regime_{calm_state}"]

    # Viterbi path should agree with the ground-truth blocks on the vast majority.
    decoded = res["viterbi"].map(name_by_state)
    accuracy = (decoded.values == truth.values).mean()
    assert accuracy > 0.9


# --------------------------------------------------------------------------
# The marquee test: walk-forward labels must not use future information
# --------------------------------------------------------------------------
def test_walk_forward_has_no_lookahead(long_two_regime_features):
    """A label at week t is computed from data up to t only. Therefore truncating
    the panel at some t* must not change any label dated <= t*."""
    feats = long_two_regime_features

    full = walk_forward_regimes(feats, n_states=2, min_train_years=4, n_seeds=1)

    # Truncate ~70% of the way through and re-run on the prefix only.
    t_star = feats.index[int(0.70 * len(feats))]
    trunc = walk_forward_regimes(feats.loc[:t_star], n_states=2,
                                 min_train_years=4, n_seeds=1)

    # There must be overlapping out-of-sample labels to compare.
    overlap = trunc.dropna()
    assert len(overlap) > 20

    # Every label produced on the prefix must match the full-history label.
    aligned_full = full.reindex(overlap.index)
    assert (aligned_full.values == overlap.values).all()
