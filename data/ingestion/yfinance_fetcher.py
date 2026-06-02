"""Yahoo Finance fetcher (equities, FX, commodities, vol)."""
import pandas as pd
import yfinance as yf
from .base import BaseFetcher


class YFinanceFetcher(BaseFetcher):
    def fetch(self, symbol: str, start: str, end: str | None = None) -> pd.Series:
        df = yf.download(symbol, start=start, end=end, progress=False,
                         auto_adjust=False, threads=False)
        if df is None or df.empty:
            raise ValueError(f"empty data for {symbol}")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if "Close" not in df.columns:
            raise ValueError(f"no Close column for {symbol}")
        s = df["Close"].copy()
        s.index = pd.to_datetime(s.index).tz_localize(None)
        s.name = symbol
        return s.dropna()
