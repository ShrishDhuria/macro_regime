"""Portfolio definition and weekly returns."""
from __future__ import annotations
import logging
import pandas as pd
from data.storage import load_panel

log = logging.getLogger(__name__)

# Weights chosen for asset-class representativeness, not optimal allocation.
DEFAULT_PORTFOLIO = {"SX5E": 0.50, "EURUSD": 0.15, "BRENT": 0.20, "GOLD": 0.15}


def portfolio_weekly_returns(weights: dict[str, float] | None = None) -> pd.Series:
    weights = weights or DEFAULT_PORTFOLIO
    if abs(sum(weights.values()) - 1.0) > 1e-6:
        raise ValueError(f"Weights must sum to 1, got {sum(weights.values())}")
    features = load_panel("master_features")
    ret_cols = [f"{name}_ret_1w" for name in weights]
    missing = [c for c in ret_cols if c not in features.columns]
    if missing:
        raise ValueError(f"Missing return columns: {missing}")
    returns = features[ret_cols].dropna()
    weight_vec = pd.Series({f"{name}_ret_1w": w for name, w in weights.items()})
    portfolio_ret = (returns * weight_vec).sum(axis=1).rename("portfolio_ret_1w")
    log.info(f"Portfolio weights: {weights}")
    log.info(f"  {len(portfolio_ret)} weekly obs, {portfolio_ret.index.min().date()} -> {portfolio_ret.index.max().date()}")
    return portfolio_ret


def asset_returns_matrix(weights: dict[str, float] | None = None) -> pd.DataFrame:
    weights = weights or DEFAULT_PORTFOLIO
    features = load_panel("master_features")
    return features[[f"{name}_ret_1w" for name in weights]].dropna()
