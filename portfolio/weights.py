"""Strategy-specific weight transformations: regime tilts, vol-forecast, drawdown predictive."""
from __future__ import annotations
import numpy as np
import pandas as pd

REGIME_EQUITY_MULTIPLIER = {"calm": 1.30, "transition": 1.00, "crisis": 0.40, "stress": 0.65}


def apply_regime_tilt(weights, asset_names, regime, equity_assets=("SX5E",)):
    mult = REGIME_EQUITY_MULTIPLIER.get(regime, 1.0)
    out = weights.copy()
    for i, name in enumerate(asset_names):
        if name in equity_assets:
            out[i] *= mult
    return out


def apply_vol_forecast_tilt(weights, asset_names, vol_forecast, vol_baseline,
                             equity_assets=("SX5E",), min_mult=0.40, max_mult=1.50):
    if pd.isna(vol_forecast) or pd.isna(vol_baseline) or vol_forecast <= 0 or vol_baseline <= 0:
        return weights
    mult = float(np.clip(vol_baseline / vol_forecast, min_mult, max_mult))
    out = weights.copy()
    for i, name in enumerate(asset_names):
        if name in equity_assets:
            out[i] *= mult
    return out


def apply_drawdown_predictive_scale(weights, p_drawdown, baseline_p, min_mult=0.30, max_mult=1.20):
    """Scale ALL weights uniformly inverse to predicted drawdown probability."""
    if pd.isna(p_drawdown) or pd.isna(baseline_p) or baseline_p <= 0:
        return weights
    mult = float(np.clip(baseline_p / max(p_drawdown, 1e-6), min_mult, max_mult))
    return weights * mult
