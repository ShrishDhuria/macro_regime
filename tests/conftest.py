"""Shared fixtures for the macro_regime tests.

Two synthetic feature panels with a clean low-vol / high-vol structure. The
``SX5E_rv_60d`` column name is mandatory because the regime code labels states
by sorting on it, so the fixtures include it explicitly. No data is read from
disk — the storage layer is bypassed entirely.
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _two_regime_panel(start, n_blocks, block_weeks, seed=0):
    """Alternating low-vol / high-vol weekly blocks with two features."""
    rng = np.random.default_rng(seed)
    rv, spread, labels = [], [], []
    for b in range(n_blocks):
        high = (b % 2 == 1)
        if high:
            rv.append(rng.normal(3.0, 0.30, block_weeks))
            spread.append(rng.normal(2.0, 0.30, block_weeks))
        else:
            rv.append(rng.normal(0.5, 0.10, block_weeks))
            spread.append(rng.normal(0.5, 0.10, block_weeks))
        labels += ["stress" if high else "calm"] * block_weeks
    n = n_blocks * block_weeks
    idx = pd.date_range(start, periods=n, freq="W-FRI")
    df = pd.DataFrame(
        {"SX5E_rv_60d": np.concatenate(rv), "SPREAD": np.concatenate(spread)},
        index=idx,
    )
    return df, pd.Series(labels, index=idx, name="truth")


@pytest.fixture
def two_regime_features():
    """Two clean regimes (calm first half, stress second half) for a single fit."""
    df, truth = _two_regime_panel("2015-01-02", n_blocks=2, block_weeks=200, seed=0)
    return df, truth


@pytest.fixture
def long_two_regime_features():
    """~12 years of weekly data with several regime switches, for walk-forward."""
    df, _ = _two_regime_panel("2008-01-04", n_blocks=6, block_weeks=104, seed=3)
    return df
