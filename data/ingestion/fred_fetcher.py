"""FRED fetcher - direct CSV download (no pandas-datareader, no API key needed).

pandas-datareader was dropped because it imports the removed `distutils` module
and fails on Python 3.12+. FRED's public CSV endpoint is simpler and has no key.
"""
from io import StringIO
import requests
import pandas as pd
from .base import BaseFetcher


class FREDFetcher(BaseFetcher):
    BASE_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    TIMEOUT = 30

    def fetch(self, symbol: str, start: str, end: str | None = None) -> pd.Series:
        params = {"id": symbol, "cosd": start}
        if end:
            params["coed"] = end
        resp = requests.get(self.BASE_URL, params=params, timeout=self.TIMEOUT,
                            headers={"User-Agent": "macro-regime-platform/0.1"})
        resp.raise_for_status()
        if not resp.text.strip():
            raise ValueError(f"FRED empty body for {symbol}")
        df = pd.read_csv(StringIO(resp.text))
        if df.empty or df.shape[1] < 2:
            raise ValueError(f"FRED unexpected schema for {symbol}: {list(df.columns)}")
        date_col, value_col = df.columns[0], df.columns[1]
        idx = pd.to_datetime(df[date_col], errors="coerce")
        vals = pd.to_numeric(df[value_col], errors="coerce")
        s = pd.Series(vals.values, index=idx, name=symbol).sort_index().dropna()
        if s.empty:
            raise ValueError(f"FRED no valid observations for {symbol}")
        return s
