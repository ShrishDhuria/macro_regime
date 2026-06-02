"""Rolling cross-asset correlations on daily returns, resampled weekly.

Correlation regime shifts (e.g. equity-FX correlation flipping sign) are themselves
a regime signal - they typically accompany macro turning points.
"""
import numpy as np
import pandas as pd
from data.storage import load_raw

PAIRS = [
    ("SX5E", "EURUSD"),
    ("SX5E", "BRENT"),
    ("SX5E", "GOLD"),
    ("BANKS", "SX5E"),
]


def _daily_returns(name: str) -> pd.Series:
    s = load_raw(name).sort_index()
    return np.log(s / s.shift(1)).dropna()


def compute_rolling_correlations(window: int = 60,
                                  weekday: str = "W-FRI") -> pd.DataFrame:
    cols = []
    for a, b in PAIRS:
        try:
            ra, rb = _daily_returns(a), _daily_returns(b)
        except FileNotFoundError:
            continue
        joined = pd.concat([ra, rb], axis=1).dropna()
        if joined.empty:
            continue
        joined.columns = [a, b]
        rho = joined[a].rolling(window, min_periods=window // 2).corr(joined[b])
        rho_w = rho.resample(weekday).last()
        rho_w.name = f"CORR_{a}_{b}_{window}d"
        cols.append(rho_w)
    return pd.concat(cols, axis=1) if cols else pd.DataFrame()
