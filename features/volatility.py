"""Annualised realized volatility from daily returns, plus vol-of-vol."""
import numpy as np
import pandas as pd
from data.storage import load_raw

VOL_SERIES = ["SX5E", "CAC", "DAX", "BANKS", "EURUSD", "BRENT"]


def compute_realized_vol(windows: tuple[int, ...] = (20, 60, 252),
                         weekday: str = "W-FRI") -> pd.DataFrame:
    """Rolling std of daily log returns, annualised by sqrt(252), resampled weekly.

    SX5E_rv_20d serves as the V2X replacement (V2X was delisted on Yahoo).
    """
    cols = []
    for name in VOL_SERIES:
        try:
            s = load_raw(name).sort_index()
        except FileNotFoundError:
            continue
        daily_ret = np.log(s / s.shift(1)).dropna()
        for w in windows:
            rv = daily_ret.rolling(window=w, min_periods=max(5, w // 4)).std() * np.sqrt(252)
            rv_w = rv.resample(weekday).last()
            rv_w.name = f"{name}_rv_{w}d"
            cols.append(rv_w)
    return pd.concat(cols, axis=1) if cols else pd.DataFrame()


def compute_vol_of_vol(window: int = 60, weekday: str = "W-FRI") -> pd.DataFrame:
    """Rolling std of SX5E 20-day RV - a tail-risk and regime-change signal."""
    s = load_raw("SX5E").sort_index()
    daily_ret = np.log(s / s.shift(1)).dropna()
    rv20 = daily_ret.rolling(20, min_periods=5).std() * np.sqrt(252)
    vov = rv20.rolling(window, min_periods=20).std()
    vov_w = vov.resample(weekday).last()
    vov_w.name = f"SX5E_vov_{window}d"
    return vov_w.to_frame()
