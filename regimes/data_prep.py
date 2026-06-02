"""Build the standardized HMM input matrix from features + spliced short rate."""
from __future__ import annotations
import logging
import pandas as pd
from data.storage import load_panel, load_raw

log = logging.getLogger(__name__)

HMM_FEATURES = [
    "SX5E_rv_60d",            # equity stress
    "SPREAD_IT_DE",           # sovereign stress
    "CORR_SX5E_EURUSD_60d",   # risk-on/risk-off correlation regime
    "TERM_DE_UNIFIED",        # ECB stance + growth (uses spliced short rate)
    "BRENT_rv_60d",           # commodity stress
]


def build_term_de_unified(weekday: str = "W-FRI") -> pd.Series:
    """DE10Y minus the EONIA-spliced short rate, weekly Friday close."""
    panel = load_panel()
    estr_unified = load_raw("ESTR_UNIFIED").sort_index()
    estr_weekly = estr_unified.resample(weekday).last()
    aligned = pd.concat([panel["DE10Y"], estr_weekly], axis=1)
    aligned.columns = ["DE10Y", "SHORT"]
    return (aligned["DE10Y"] - aligned["SHORT"]).rename("TERM_DE_UNIFIED")


def assemble_hmm_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (standardized_X, raw_X) - both as pd.DataFrame, NaN rows dropped."""
    features = load_panel("master_features")
    term_unified = build_term_de_unified()
    df = features.copy()
    df["TERM_DE_UNIFIED"] = term_unified
    raw = df[HMM_FEATURES].copy()
    n_before = len(raw)
    raw = raw.dropna()
    log.info(f"HMM input: dropped {n_before - len(raw)} rows with NaN; {len(raw)} usable obs")
    log.info(f"  Date range: {raw.index.min().date()} -> {raw.index.max().date()}")
    standardized = (raw - raw.mean()) / raw.std()
    return standardized, raw
