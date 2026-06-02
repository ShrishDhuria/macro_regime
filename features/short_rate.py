"""EONIA + ESTR splice for full-history short-rate continuity.

ESTR began 2 October 2019. ECB methodology (Recommendation 2019/C 295/02):
from that date EONIA was redefined as ESTR + 8.5bp (fixed spread).

Splice rule: use ESTR from 2019-10-02 onwards, and (EONIA - 8.5bp) before that.
EONIA history sourced from FRED (ticker EONIARATE, discontinued Jan 2022); we
only need pre-October-2019 values. Routed through FRED for reliability.
"""
from __future__ import annotations
import logging
import pandas as pd
from data.storage import load_raw, save_raw
from data.ingestion.fred_fetcher import FREDFetcher

log = logging.getLogger(__name__)

ESTR_EONIA_SPREAD_PCT = 0.085          # 8.5 bp = 0.085 percentage points
ESTR_START = pd.Timestamp("2019-10-02")
EONIA_FRED_TICKER = "EONIARATE"


def fetch_eonia_fred(start: str = "2005-01-01") -> pd.Series:
    return FREDFetcher().fetch(EONIA_FRED_TICKER, start=start)


def build_unified_short_rate() -> pd.Series:
    """Splice EONIA (pre-Oct 2019, adjusted) with ESTR (from Oct 2019)."""
    log.info("Loading existing ESTR raw...")
    estr = load_raw("ESTR").sort_index()
    log.info(f"  ESTR: {estr.index.min().date()} -> {estr.index.max().date()} ({len(estr)} obs)")

    log.info(f"Fetching EONIA from FRED ({EONIA_FRED_TICKER})...")
    eonia = fetch_eonia_fred()
    log.info(f"  EONIA: {eonia.index.min().date()} -> {eonia.index.max().date()} ({len(eonia)} obs)")

    eonia_pre = eonia[eonia.index < ESTR_START] - ESTR_EONIA_SPREAD_PCT
    estr_post = estr[estr.index >= ESTR_START]

    unified = pd.concat([eonia_pre, estr_post]).sort_index()
    unified = unified[~unified.index.duplicated(keep="last")]
    unified.name = "ESTR_UNIFIED"
    log.info(f"  Spliced: {unified.index.min().date()} -> {unified.index.max().date()} ({len(unified)} obs)")
    save_raw("ESTR_UNIFIED", unified)
    return unified
