"""Cornish-Fisher VaR behaviour vs the Gaussian baseline."""
import math

import numpy as np
import pandas as pd
import pytest

from risk.var import historical_var, parametric_var, cornish_fisher_var


def test_cornish_fisher_collapses_to_gaussian_on_normal():
    """With ~zero skew and excess kurtosis, the CF expansion reduces to the
    parametric (Gaussian) VaR, and both track the empirical historical VaR."""
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.0, 0.01, size=300_000))

    pv = parametric_var(r, 0.01)
    cf = cornish_fisher_var(r, 0.01)
    hv = historical_var(r, 0.01)

    assert cf == pytest.approx(pv, rel=0.03)
    assert hv == pytest.approx(pv, rel=0.05)


def test_cornish_fisher_inflates_left_tail():
    """A left-skewed, fat-tailed series must push CF VaR above the Gaussian VaR
    (the whole reason the engine reports it)."""
    rng = np.random.default_rng(1)
    base = rng.normal(0.0, 0.01, size=200_000)
    # Inject occasional large negative jumps -> negative skew + excess kurtosis.
    jump = (rng.random(200_000) < 0.02) * rng.normal(-0.06, 0.01, size=200_000)
    r = pd.Series(base + jump)

    assert r.skew() < 0            # sanity: the construction is left-skewed
    assert r.kurtosis() > 0        # ...and fat-tailed (excess kurtosis)
    assert cornish_fisher_var(r, 0.01) > parametric_var(r, 0.01)


def test_var_monotone_in_confidence_and_empty_is_nan():
    rng = np.random.default_rng(2)
    r = pd.Series(rng.normal(0.0, 0.01, size=50_000))
    assert parametric_var(r, 0.01) >= parametric_var(r, 0.05)
    assert math.isnan(parametric_var(pd.Series(dtype=float), 0.05))
