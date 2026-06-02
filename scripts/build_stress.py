"""Phase 6 - run stress tests across portfolio scenarios."""
from __future__ import annotations
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.storage import load_panel, save_panel
from risk.portfolio import DEFAULT_PORTFOLIO
from stress.scenarios import STRESS_SCENARIOS
from stress.transmission import run_stress

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("stress")


def main():
    panel = load_panel()
    features = load_panel("master_features")
    asset_names = list(DEFAULT_PORTFOLIO.keys())
    log.info(f"Running stress on {len(STRESS_SCENARIOS)} scenarios...")
    results = run_stress(features, panel, STRESS_SCENARIOS, asset_names, DEFAULT_PORTFOLIO, window=156)
    print("\n=== Stress test results (portfolio P&L impact) ===")
    cols = ["scenario", "trigger", "trigger_shock", "portfolio_pnl"] + [f"impl_{a}" for a in asset_names]
    fmt = results[cols].copy()
    fmt["portfolio_pnl"] = fmt["portfolio_pnl"].apply(lambda x: f"{x:+.2%}")
    fmt["trigger_shock"] = fmt["trigger_shock"].apply(lambda x: f"{x:+.2f}")
    for a in asset_names:
        fmt[f"impl_{a}"] = fmt[f"impl_{a}"].apply(lambda x: f"{x:+.2%}")
    print(fmt.to_string(index=False))
    save_panel(results, name="stress_results")
    log.info("Saved to data_store/panel/stress_results.parquet")


if __name__ == "__main__":
    main()
