"""FRED fetcher - direct CSV download (no pandas-datareader, no API key needed).

pandas-datareader was dropped because it imports the removed `distutils` module
and fails on Python 3.12+. FRED's public CSV endpoint is simpler and has no key.
"""
import time
import logging
from io import StringIO
import requests
import pandas as pd
from .base import BaseFetcher

log = logging.getLogger(__name__)


class FREDFetcher(BaseFetcher):
    BASE_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    TIMEOUT = 60          # FRED's public CSV endpoint can be slow for long series
    RETRIES = 4           # transient 5xx / read-timeouts are common on this endpoint
    BACKOFF = 3.0         # seconds between attempts, grows linearly

    def fetch(self, symbol: str, start: str, end: str | None = None) -> pd.Series:
        params = {"id": symbol, "cosd": start}
        if end:
            params["coed"] = end
        headers = {"User-Agent": "macro-regime-platform/0.1"}

        last_err: Exception | None = None
        for attempt in range(1, self.RETRIES + 1):
            try:
                resp = requests.get(self.BASE_URL, params=params,
                                    timeout=self.TIMEOUT, headers=headers)
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
            except requests.HTTPError as e:
                status = getattr(e.response, "status_code", None)
                if status is not None and 400 <= status < 500:
                    raise  # bad ticker / permanent client error — retrying won't help
                last_err = e  # 5xx — transient, fall through to retry
            except (requests.RequestException, ValueError) as e:
                last_err = e  # timeout / connection / transient parse — retry
            if attempt < self.RETRIES:
                wait = self.BACKOFF * attempt
                log.warning(f"  FRED {symbol}: attempt {attempt}/{self.RETRIES} failed "
                            f"({type(last_err).__name__}); retrying in {wait:.0f}s")
                time.sleep(wait)
        raise last_err
