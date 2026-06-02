"""Enforce realistic publication-lag offsets on macro series.

Reference period T is NOT observable at T - there's a release delay. Stamping
HICP at March 31 when it's first published mid-April leaks the future into any
model trained on it. This module shifts macro columns forward by their lag.
"""
import pandas as pd
from data.storage import load_panel

RELEASE_LAGS = {
    "EA_HICP": 30,   # flash ~end of T, final ~T+15; use 30d for safety
}


def apply_release_lags() -> pd.DataFrame:
    """Return a DataFrame of lagged macro columns, suffixed with `_lagged`."""
    panel = load_panel()
    out = pd.DataFrame(index=panel.index)
    for col, lag_days in RELEASE_LAGS.items():
        if col not in panel.columns:
            continue
        lag_weeks = max(1, (lag_days + 6) // 7)
        out[f"{col}_lagged"] = panel[col].shift(lag_weeks)
    return out
