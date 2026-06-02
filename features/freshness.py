"""Staleness check - flag series that haven't updated in N days.

Run after every panel build. Would have caught OECD_CLI on day one.
"""
from datetime import datetime, timezone
import pandas as pd
from data.storage import load_panel

DEFAULT_STALENESS_DAYS = 90


def freshness_report(staleness_days: int = DEFAULT_STALENESS_DAYS) -> pd.DataFrame:
    panel = load_panel()
    today = pd.Timestamp(datetime.now(timezone.utc).date())
    rows = []
    for col in panel.columns:
        s = panel[col].dropna()
        last_obs = s.index.max() if not s.empty else pd.NaT
        days_stale = (today - last_obs).days if pd.notna(last_obs) else None
        flag = "STALE" if (days_stale is not None and days_stale > staleness_days) else "ok"
        rows.append({"series": col,
                     "last_observation": last_obs.date() if pd.notna(last_obs) else None,
                     "days_stale": days_stale, "flag": flag})
    return (pd.DataFrame(rows)
            .sort_values("days_stale", ascending=False, na_position="last")
            .reset_index(drop=True))
