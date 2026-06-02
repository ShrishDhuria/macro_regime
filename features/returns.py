"""Weekly log returns on price series, computed from daily raw."""
import numpy as np
import pandas as pd
from data.storage import load_raw

PRICE_SERIES = ["SX5E", "CAC", "DAX", "BANKS", "EURUSD", "BRENT", "GOLD"]


def compute_log_returns(weekday: str = "W-FRI") -> pd.DataFrame:
    """log(P_t / P_{t-1}) on the weekly Friday-close grid, one column per series."""
    cols = []
    for name in PRICE_SERIES:
        try:
            s = load_raw(name).sort_index()
        except FileNotFoundError:
            continue
        weekly = s.resample(weekday).last()
        log_ret = np.log(weekly / weekly.shift(1))
        log_ret.name = f"{name}_ret_1w"
        cols.append(log_ret)
    return pd.concat(cols, axis=1) if cols else pd.DataFrame()
