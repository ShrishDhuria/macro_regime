"""Align heterogeneous-frequency series to a common weekly Friday-close grid."""
import pandas as pd


def align_to_weekly(series_dict: dict[str, pd.Series],
                    start: str,
                    end: str | None = None,
                    weekday: str = "W-FRI") -> pd.DataFrame:
    """Forward-fill each series, then resample to weekday close.

    Daily series: .last() within the week. Monthly series: most recent obs carried forward.
    Phase 1 stamps observations at reference period; Phase 2 lags macro by publication date.
    """
    if not series_dict:
        return pd.DataFrame()
    cols = []
    for name, s in series_dict.items():
        s = s.copy().sort_index()
        daily = s.asfreq("D").ffill()
        weekly = daily.resample(weekday).last()
        weekly.name = name
        cols.append(weekly)
    df = pd.concat(cols, axis=1)
    df = df.loc[start:end] if end else df.loc[start:]
    return df
