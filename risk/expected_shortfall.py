"""Expected Shortfall (CVaR) - average loss conditional on a tail event."""
from __future__ import annotations
import pandas as pd
from scipy import stats


def historical_es(returns: pd.Series, alpha: float = 0.05) -> float:
    if returns.empty: return float("nan")
    threshold = returns.quantile(alpha)
    tail = returns[returns <= threshold]
    if tail.empty: return float("nan")
    return -tail.mean()


def parametric_es(returns: pd.Series, alpha: float = 0.05) -> float:
    if returns.empty: return float("nan")
    mu, sigma = returns.mean(), returns.std()
    z = stats.norm.ppf(alpha)
    return -(mu - sigma * stats.norm.pdf(z) / alpha)


def all_es_metrics(returns: pd.Series, alphas=(0.05, 0.01)) -> pd.DataFrame:
    rows = []
    for alpha in alphas:
        rows.append({"confidence": f"{int((1-alpha)*100)}%", "alpha": alpha,
                     "historical_es": historical_es(returns, alpha),
                     "parametric_es": parametric_es(returns, alpha)})
    return pd.DataFrame(rows)
