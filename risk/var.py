"""Value-at-Risk: historical, parametric, Cornish-Fisher.

Convention: VaR returned as a positive number representing loss magnitude.
"""
from __future__ import annotations
import pandas as pd
from scipy import stats


def historical_var(returns: pd.Series, alpha: float = 0.05) -> float:
    if returns.empty: return float("nan")
    return -returns.quantile(alpha)


def parametric_var(returns: pd.Series, alpha: float = 0.05) -> float:
    if returns.empty: return float("nan")
    mu, sigma = returns.mean(), returns.std()
    z = stats.norm.ppf(alpha)
    return -(mu + sigma * z)


def cornish_fisher_var(returns: pd.Series, alpha: float = 0.05) -> float:
    """Adjusts parametric VaR for skew and excess kurtosis (4th-order CF expansion)."""
    if returns.empty: return float("nan")
    mu, sigma = returns.mean(), returns.std()
    skew, ekurt = returns.skew(), returns.kurtosis()
    z = stats.norm.ppf(alpha)
    z_cf = (z + (z**2 - 1) * skew / 6 + (z**3 - 3*z) * ekurt / 24
            - (2*z**3 - 5*z) * skew**2 / 36)
    return -(mu + sigma * z_cf)


def all_var_metrics(returns: pd.Series, alphas=(0.05, 0.01)) -> pd.DataFrame:
    rows = []
    for alpha in alphas:
        rows.append({"confidence": f"{int((1-alpha)*100)}%", "alpha": alpha,
                     "historical_var": historical_var(returns, alpha),
                     "parametric_var": parametric_var(returns, alpha),
                     "cornish_fisher_var": cornish_fisher_var(returns, alpha)})
    return pd.DataFrame(rows)
