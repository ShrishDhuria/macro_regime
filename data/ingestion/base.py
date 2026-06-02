"""Abstract base for data fetchers."""
from abc import ABC, abstractmethod
import pandas as pd


class BaseFetcher(ABC):
    """All fetchers return a tz-naive pd.Series indexed by date."""

    @abstractmethod
    def fetch(self, symbol: str, start: str, end: str | None = None) -> pd.Series:
        raise NotImplementedError
