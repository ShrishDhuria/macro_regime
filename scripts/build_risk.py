"""Phase 4 orchestrator - portfolio risk metrics, regime-conditional, Excel workbook."""
from __future__ import annotations
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from risk.portfolio import portfolio_weekly_returns, DEFAULT_PORTFOLIO
from risk.var import all_var_metrics
from risk.expected_shortfall import all_es_metrics
from risk.drawdown import max_drawdown
from risk.beta import rolling_beta
from risk.regime_conditional import regime_conditional_summary
from risk.excel_export import build_excel_workbook
from data.storage import save_panel, load_panel

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("build_risk")
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main():
    log.info("=== Step 1: portfolio returns ===")
    portfolio_ret = portfolio_weekly_returns()

    log.info("=== Step 2: unconditional VaR ===")
    var_table = all_var_metrics(portfolio_ret)
    print("\n=== Value-at-Risk (weekly portfolio loss magnitude) ===")
    print(var_table.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    log.info("=== Step 3: unconditional ES ===")
    es_table = all_es_metrics(portfolio_ret)
    print("\n=== Expected Shortfall ===")
    print(es_table.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    log.info("=== Step 4: drawdown analysis ===")
    dd = max_drawdown(portfolio_ret)
    print("\n=== Maximum drawdown ===")
    for k, v in dd.items():
        print(f"  {k}: {v}")

    log.info("=== Step 5: rolling beta (BANKS to IT-DE spread) ===")
    features = load_panel("master_features")
    if "BANKS_ret_1w" in features.columns and "SPREAD_IT_DE" in features.columns:
        spread_change = features["SPREAD_IT_DE"].diff() * 100
        beta = rolling_beta(features["BANKS_ret_1w"], spread_change, window=52)
        print(f"\n=== Rolling 52w beta of BANKS to weekly change in IT-DE spread ===")
        print(f"  Mean beta: {beta.mean():.4f}")
        print(f"  Min beta:  {beta.min():.4f}  on  {beta.idxmin().date() if pd.notna(beta.idxmin()) else 'n/a'}")
        print(f"  Max beta:  {beta.max():.4f}  on  {beta.idxmax().date() if pd.notna(beta.idxmax()) else 'n/a'}")
        save_panel(beta.to_frame(), name="risk_banks_beta_to_spread")

    log.info("=== Step 6: regime-conditional summary (3-state) ===")
    regime_summary = regime_conditional_summary(portfolio_ret, n_states=3)
    print("\n=== Risk metrics by regime (3-state HMM) ===")
    print(regime_summary.to_string(float_format=lambda x: f"{x:.4f}"))

    log.info("=== Step 7: building Excel workbook ===")
    output_path = PROJECT_ROOT / "reports" / "risk_workbook.xlsx"
    build_excel_workbook(DEFAULT_PORTFOLIO, portfolio_ret, var_table, es_table,
                         dd, regime_summary, output_path)
    save_panel(regime_summary, name="risk_regime_conditional_3state")

    print(f"\n=== Phase 4 complete ===")
    print(f"Excel workbook: {output_path}")


if __name__ == "__main__":
    main()
