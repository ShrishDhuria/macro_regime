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


def _get_eonia() -> pd.Series | None:
    """Pre-Oct-2019 EONIA history.

    EONIA is a discontinued series (ended Jan 2022) and we only ever consume its
    fixed pre-Oct-2019 values, so it is cached permanently after the first
    successful fetch and reused offline thereafter — no reason to re-pull static
    history on every build. Returns None only if FRED is unreachable AND there is
    no cached copy (i.e. a first-ever build during a FRED outage).
    """
    # 1. Prefer the cached copy: static history, no network needed.
    try:
        cached = load_raw("EONIA").sort_index()
        if not cached.empty:
            log.info(f"  EONIA: using cached copy ({len(cached)} obs)")
            return cached
    except Exception:
        pass  # no cache yet — fall through to a live fetch

    # 2. No cache: fetch from FRED, then cache for all future (offline) runs.
    try:
        log.info(f"Fetching EONIA from FRED ({EONIA_FRED_TICKER})...")
        eonia = fetch_eonia_fred()
        save_raw("EONIA", eonia)
        log.info(f"  EONIA: {eonia.index.min().date()} -> {eonia.index.max().date()} "
                 f"({len(eonia)} obs, cached for future runs)")
        return eonia
    except Exception as e:
        log.warning(f"  EONIA unavailable ({type(e).__name__}: {e}); falling back to "
                    "ESTR-only short rate (history starts Oct 2019 instead of 2005)")
        return None


def build_unified_short_rate() -> pd.Series:
    """Splice EONIA (pre-Oct 2019, adjusted) with ESTR (from Oct 2019).

    If EONIA cannot be obtained (FRED down and nothing cached), the pipeline
    still completes on the ESTR-only series rather than aborting — the regime
    history simply begins at ESTR's inception instead of extending back to 2005.
    """
    log.info("Loading existing ESTR raw...")
    estr = load_raw("ESTR").sort_index()
    log.info(f"  ESTR: {estr.index.min().date()} -> {estr.index.max().date()} ({len(estr)} obs)")

    eonia = _get_eonia()
    if eonia is not None:
        eonia_pre = eonia[eonia.index < ESTR_START] - ESTR_EONIA_SPREAD_PCT
        estr_post = estr[estr.index >= ESTR_START]
        unified = pd.concat([eonia_pre, estr_post]).sort_index()
    else:
        unified = estr.copy()

    unified = unified[~unified.index.duplicated(keep="last")]
    unified.name = "ESTR_UNIFIED"
    log.info(f"  Unified short rate: {unified.index.min().date()} -> "
             f"{unified.index.max().date()} ({len(unified)} obs)")
    save_raw("ESTR_UNIFIED", unified)
    return unified
