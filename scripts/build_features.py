"""Phase 2 orchestrator - build master features from the Phase 1 panel."""
from __future__ import annotations
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from data.storage import save_panel
from features.returns import compute_log_returns
from features.volatility import compute_realized_vol, compute_vol_of_vol
from features.spreads import compute_spreads
from features.correlations import compute_rolling_correlations
from features.momentum import compute_momentum, compute_z_scores
from features.macro_lag import apply_release_lags
from features.freshness import freshness_report

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("build_features")


def build_features():
    log.info("Freshness check on master panel...")
    fr = freshness_report()
    print(fr.to_string(index=False)); print()

    log.info("Log returns...");                  rets = compute_log_returns();          log.info(f"  -> {rets.shape[1]} cols")
    log.info("Realized vol (20d, 60d, 252d)..."); rv = compute_realized_vol();           log.info(f"  -> {rv.shape[1]} cols")
    log.info("Vol-of-vol (SX5E)...");            vov = compute_vol_of_vol();             log.info(f"  -> {vov.shape[1]} cols")
    log.info("Rate and sovereign spreads...");   spr = compute_spreads();                log.info(f"  -> {spr.shape[1]} cols")
    log.info("Rolling correlations (60d)...");   corr = compute_rolling_correlations();  log.info(f"  -> {corr.shape[1]} cols")
    log.info("Momentum (13w, 52w)...");          mom = compute_momentum();               log.info(f"  -> {mom.shape[1]} cols")
    log.info("Momentum z-scores (104w)...");     z = compute_z_scores();                 log.info(f"  -> {z.shape[1]} cols")
    log.info("Macro release lags...");           lag = apply_release_lags();             log.info(f"  -> {lag.shape[1]} cols")

    features = pd.concat([rets, rv, vov, spr, corr, mom, z, lag], axis=1)
    save_panel(features, name="master_features")
    log.info(f"Master features saved: shape={features.shape}")

    print("\n=== feature columns ===")
    for c in features.columns:
        print(f"  {c}")
    print(f"\nTotal: {features.shape[1]} features over {features.shape[0]} weekly observations")


if __name__ == "__main__":
    build_features()
