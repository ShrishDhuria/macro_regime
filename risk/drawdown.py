"""Drawdown analysis."""
from __future__ import annotations
import pandas as pd


def cumulative_returns(returns: pd.Series) -> pd.Series:
    return (1 + returns).cumprod()


def drawdown_series(returns: pd.Series) -> pd.Series:
    cum = cumulative_returns(returns)
    return (cum - cum.cummax()) / cum.cummax()


def max_drawdown(returns: pd.Series) -> dict:
    if returns.empty: return {}
    cum = cumulative_returns(returns)
    dd = (cum - cum.cummax()) / cum.cummax()
    trough = dd.idxmin(); max_dd = float(dd.loc[trough])
    peak = cum.loc[:trough].idxmax(); peak_val = cum.loc[peak]
    post = cum.loc[trough:]; recovered = post[post >= peak_val]
    recovery = recovered.index[0] if len(recovered) > 0 else None
    return {"max_drawdown": max_dd, "peak_date": peak, "trough_date": trough,
            "recovery_date": recovery, "drawdown_weeks": (trough - peak).days // 7,
            "recovery_weeks": (recovery - trough).days // 7 if recovery else None}
