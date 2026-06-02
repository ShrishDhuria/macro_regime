"""Rolling beta - exposure of one return series to another."""
from __future__ import annotations
import pandas as pd


def rolling_beta(y: pd.Series, x: pd.Series, window: int = 52) -> pd.Series:
    """beta_t = Cov(y, x) / Var(x) over trailing `window` periods."""
    df = pd.concat([y, x], axis=1).dropna()
    df.columns = ["y", "x"]
    cov = df["y"].rolling(window).cov(df["x"])
    var = df["x"].rolling(window).var()
    return (cov / var).rename("beta")
