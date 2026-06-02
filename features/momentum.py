"""Price momentum and rolling z-scores."""
import numpy as np
import pandas as pd
from data.storage import load_panel

MOM_SERIES = ["SX5E", "CAC", "DAX", "BANKS", "EURUSD", "BRENT", "GOLD"]


def compute_momentum(short_weeks: int = 13, long_weeks: int = 52) -> pd.DataFrame:
    """log(P_t / P_{t-N}) - standard cross-sectional momentum, ~3M and ~12M."""
    panel = load_panel()
    out = pd.DataFrame(index=panel.index)
    for name in MOM_SERIES:
        if name not in panel.columns:
            continue
        s = panel[name]
        out[f"{name}_mom_{short_weeks}w"] = np.log(s / s.shift(short_weeks))
        out[f"{name}_mom_{long_weeks}w"] = np.log(s / s.shift(long_weeks))
    return out


def compute_z_scores(window_weeks: int = 104) -> pd.DataFrame:
    """Rolling 2-year z-score of momentum - normalises across regimes."""
    mom = compute_momentum()
    out = pd.DataFrame(index=mom.index)
    for col in mom.columns:
        roll_mean = mom[col].rolling(window_weeks, min_periods=window_weeks // 4).mean()
        roll_std  = mom[col].rolling(window_weeks, min_periods=window_weeks // 4).std()
        out[f"{col}_z"] = (mom[col] - roll_mean) / roll_std
    return out
