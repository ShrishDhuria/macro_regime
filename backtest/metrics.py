"""Performance and risk metrics for backtests."""
from __future__ import annotations
import numpy as np
import pandas as pd


def annualized_return(r, freq=52):
    return float((1 + r).prod() ** (freq / len(r)) - 1) if len(r) else float("nan")

def annualized_vol(r, freq=52):
    return float(r.std() * np.sqrt(freq))

def sharpe_ratio(r, freq=52, rf=0.0):
    excess = r - rf / freq; sd = excess.std()
    return float(excess.mean() / sd * np.sqrt(freq)) if sd > 0 else float("nan")

def sortino_ratio(r, freq=52, rf=0.0):
    excess = r - rf / freq; dn = excess[excess < 0].std()
    return float(excess.mean() / dn * np.sqrt(freq)) if dn > 0 else float("nan")

def max_drawdown(r):
    cum = (1 + r).cumprod()
    return float(((cum - cum.cummax()) / cum.cummax()).min())

def calmar_ratio(r, freq=52):
    dd = abs(max_drawdown(r))
    return annualized_return(r, freq) / dd if dd > 0 else float("nan")

def hit_ratio(r):
    return float((r > 0).mean())

def annualized_turnover(t, freq=52):
    return float(t.mean() * freq)

def summary(r, turnover=None, freq=52):
    return {"ann_return": annualized_return(r, freq), "ann_vol": annualized_vol(r, freq),
            "sharpe": sharpe_ratio(r, freq), "sortino": sortino_ratio(r, freq),
            "max_drawdown": max_drawdown(r), "calmar": calmar_ratio(r, freq),
            "hit_ratio": hit_ratio(r), "best_week": float(r.max()),
            "worst_week": float(r.min()), "n_weeks": float(len(r)),
            "ann_turnover": annualized_turnover(turnover, freq) if turnover is not None else float("nan")}
