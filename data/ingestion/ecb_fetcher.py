"""ECB Data Portal fetcher (formerly SDW).

Endpoint: https://data-api.ecb.europa.eu/service/data/{DATAFLOW}/{SERIES_KEY}
Note: the ECB endpoint is occasionally slow; FRED mirrors are used as fallback
for several series elsewhere in the pipeline.
"""
from io import StringIO
import requests
import pandas as pd
from .base import BaseFetcher


class ECBFetcher(BaseFetcher):
    BASE_URL = "https://data-api.ecb.europa.eu/service/data"
    TIMEOUT = 30

    def fetch(self, symbol: str, start: str, end: str | None = None) -> pd.Series:
        parts = symbol.split(".")
        if len(parts) < 2:
            raise ValueError(f"bad ECB symbol: {symbol!r}")
        dataflow, key = parts[0], ".".join(parts[1:])
        url = f"{self.BASE_URL}/{dataflow}/{key}"
        params = {"format": "csvdata", "startPeriod": start}
        if end:
            params["endPeriod"] = end
        resp = requests.get(url, params=params, timeout=self.TIMEOUT,
                            headers={"Accept": "text/csv"})
        resp.raise_for_status()
        if not resp.text.strip():
            raise ValueError(f"ECB empty body for {symbol}")
        df = pd.read_csv(StringIO(resp.text))
        if "TIME_PERIOD" not in df.columns or "OBS_VALUE" not in df.columns:
            raise ValueError(f"unexpected ECB schema: {list(df.columns)}")
        idx = pd.to_datetime(df["TIME_PERIOD"])
        s = pd.Series(pd.to_numeric(df["OBS_VALUE"], errors="coerce").values,
                      index=idx, name=symbol).sort_index().dropna()
        return s
