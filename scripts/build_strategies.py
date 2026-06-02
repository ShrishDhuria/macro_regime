"""Phase 5b orchestrator - six strategies including predictive drawdown classifier."""
from __future__ import annotations
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from data.storage import load_panel, save_panel, load_raw
from risk.portfolio import DEFAULT_PORTFOLIO
from forecast.vol_model import walk_forward_vol_forecast
from forecast.drawdown_model import walk_forward_predict, calibration_table, compute_auc
from portfolio.risk_parity import safe_erc, vol_target_scale
from portfolio.weights import (apply_regime_tilt, apply_vol_forecast_tilt,
                                apply_drawdown_predictive_scale)
from backtest.engine import run_backtest
from backtest.metrics import summary
from regimes.data_prep import assemble_hmm_inputs
from regimes.walk_forward_hmm import walk_forward_regimes, agreement

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("build_strategies")
ROOT = Path(__file__).resolve().parent.parent

TRAIN_END_FIRST = pd.Timestamp("2010-12-31")
EVAL_START = TRAIN_END_FIRST    # common apples-to-apples window for all six
COST_BPS = 5.0
TARGET_VOL = 0.10
WINDOW_COV = 156
MIN_HISTORY = 156
DD_THRESHOLD = -0.02
ASSETS = list(DEFAULT_PORTFOLIO.keys())


def weekly_financing_rate(index):
    """Weekly ESTR/EONIA-spliced financing rate (decimal), aligned to `index`.

    Charged on the cash leg in the backtest: leverage above 1.0 pays it, idle
    cash earns it. Falls back to 0 if the spliced series is unavailable.
    """
    try:
        short = load_raw("ESTR_UNIFIED").sort_index()
    except Exception as e:
        log.warning(f"ESTR_UNIFIED unavailable ({type(e).__name__}); financing rate = 0")
        return 0.0
    weekly = short.resample("W-FRI").last().ffill()
    rate = (weekly / 100.0) / 52.0          # percent annual -> weekly decimal
    return rate.reindex(index).ffill().fillna(0.0)


def build_weights(asset_returns, regime_labels, vol_forecasts, vol_baseline,
                   p_drawdown, p_dd_baseline):
    dates = asset_returns.index
    asset_cols = list(asset_returns.columns)
    asset_short = [c.replace("_ret_1w", "") for c in asset_cols]
    n = len(asset_cols)
    strategies = ["EW", "ERC", "VT-ERC", "Regime-Tilt", "Vol-Forecast", "DD-Predict"]
    w_hist = {s: pd.DataFrame(index=dates, columns=asset_cols, dtype=float) for s in strategies}
    for date in dates:
        history = asset_returns.loc[:date]
        if len(history) < MIN_HISTORY:
            continue
        cov = history.iloc[-WINDOW_COV:].cov().values
        w_ew = np.ones(n) / n
        w_erc = safe_erc(cov)
        w_vt = vol_target_scale(w_erc, cov, target_vol_annual=TARGET_VOL,
                                 max_leverage=1.5, min_exposure=0.30)
        regime = regime_labels.get(date)
        w_rt = apply_regime_tilt(w_vt, asset_short, regime) if pd.notna(regime) else w_vt.copy()
        vf, vb = vol_forecasts.get(date), vol_baseline.get(date)
        w_vf = apply_vol_forecast_tilt(w_vt, asset_short, vf, vb) if (pd.notna(vf) and pd.notna(vb)) else w_vt.copy()
        pdd, pbl = p_drawdown.get(date), p_dd_baseline.get(date)
        w_dd = apply_drawdown_predictive_scale(w_vt, pdd, pbl) if (pd.notna(pdd) and pd.notna(pbl)) else w_vt.copy()
        w_hist["EW"].loc[date] = w_ew
        w_hist["ERC"].loc[date] = w_erc
        w_hist["VT-ERC"].loc[date] = w_vt
        w_hist["Regime-Tilt"].loc[date] = w_rt
        w_hist["Vol-Forecast"].loc[date] = w_vf
        w_hist["DD-Predict"].loc[date] = w_dd
    for s in strategies:
        w_hist[s] = w_hist[s].dropna(how="all")
    return w_hist


def regime_conditional_returns(returns, regimes):
    out = {}
    for r in ["calm", "transition", "crisis"]:
        mask = regimes.reindex(returns.index) == r
        n = int(mask.sum())
        out[r] = float((1 + returns[mask]).prod() ** (52 / n) - 1) if n > 0 else float("nan")
    return pd.Series(out)


def plot_strategies(results):
    REPORTS = ROOT / "reports"; REPORTS.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(14, 6))
    for name, res in results.items():
        cum = (1 + res["net_returns"]).cumprod()
        ax.plot(cum.index, cum.values, label=name, linewidth=1.5)
    ax.set_yscale("log"); ax.set_title("Cumulative net returns (log scale)")
    ax.set_ylabel("Wealth"); ax.set_xlabel("Date")
    ax.legend(loc="upper left"); ax.grid(True, alpha=0.3)
    fig.tight_layout(); fig.savefig(REPORTS / "strategy_comparison.png", dpi=120); plt.close(fig)
    fig, ax = plt.subplots(figsize=(14, 5))
    for name, res in results.items():
        cum = (1 + res["net_returns"]).cumprod()
        dd = (cum - cum.cummax()) / cum.cummax()
        ax.plot(dd.index, dd.values, label=name, linewidth=1.2)
    ax.set_title("Drawdowns"); ax.set_ylabel("Drawdown"); ax.set_xlabel("Date")
    ax.legend(loc="lower left"); ax.grid(True, alpha=0.3)
    fig.tight_layout(); fig.savefig(REPORTS / "strategy_drawdowns.png", dpi=120); plt.close(fig)


def plot_drawdown_predictions(p_drawdown, p_baseline, ew_returns, threshold):
    REPORTS = ROOT / "reports"; REPORTS.mkdir(exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    ax1.plot(p_drawdown.index, p_drawdown.values, color="darkred", linewidth=1, label="P(drawdown)")
    ax1.plot(p_baseline.index, p_baseline.values, color="black", linewidth=1,
             linestyle="--", alpha=0.7, label="52w rolling baseline")
    ax1.set_ylabel("P(next-week return < -2%)"); ax1.set_ylim(0, 1)
    ax1.set_title("Walk-forward predicted drawdown probability")
    ax1.legend(loc="upper right"); ax1.grid(True, alpha=0.3)
    common = p_drawdown.index.intersection(ew_returns.index)
    ax2.plot(common, ew_returns.loc[common].values, color="black", linewidth=0.8)
    events = ew_returns[ew_returns < threshold]
    ce = events.index.intersection(common)
    ax2.scatter(ce, ew_returns.loc[ce].values, color="red", s=20,
                label=f"Actual drawdowns (< {threshold:.0%})")
    ax2.axhline(threshold, color="red", linestyle=":", alpha=0.5)
    ax2.set_ylabel("EW portfolio weekly return"); ax2.set_xlabel("Date")
    ax2.legend(loc="lower left"); ax2.grid(True, alpha=0.3)
    fig.tight_layout(); fig.savefig(REPORTS / "drawdown_predictions.png", dpi=120); plt.close(fig)


def main():
    log.info("=== Step 1: loading inputs ===")
    features = load_panel("master_features")
    asset_returns = features[[f"{a}_ret_1w" for a in ASSETS]].dropna()
    viterbi = load_panel("hmm_viterbi_3state")["regime"]
    emissions = load_panel("hmm_emissions_3state")
    sorted_states = emissions["SX5E_rv_60d"].sort_values()
    label_map = dict(zip([int(s.split("_")[1]) for s in sorted_states.index],
                          ["calm", "transition", "crisis"]))
    regime_labels_fs = viterbi.map(label_map)    # full-sample; diagnostics only
    ew_w = np.ones(len(ASSETS)) / len(ASSETS)
    ew_returns = (asset_returns * ew_w).sum(axis=1)

    log.info("=== Step 1b: walk-forward (out-of-sample) HMM regime labels ===")
    _, hmm_raw = assemble_hmm_inputs()
    regime_labels = walk_forward_regimes(hmm_raw, n_states=3, n_seeds=5)
    log.info(f"Walk-forward vs full-sample regime agreement: "
             f"{agreement(regime_labels_fs, regime_labels):.1%} "
             f"(disagreement is the timing edge the full-sample fit silently borrowed)")

    log.info("=== Step 2: walk-forward LightGBM vol forecasts ===")
    vol_forecasts = walk_forward_vol_forecast(features, first_train_end=TRAIN_END_FIRST, refit_weeks=13)
    vol_baseline = vol_forecasts.rolling(52, min_periods=20).median()

    log.info("=== Step 3: walk-forward LightGBM drawdown classifier ===")
    dd_result = walk_forward_predict(features, ew_returns, first_train_end=TRAIN_END_FIRST,
                                       refit_weeks=13, threshold=DD_THRESHOLD)
    p_drawdown = dd_result["probabilities"]
    p_dd_baseline = p_drawdown.rolling(52, min_periods=20).median()

    log.info("=== Step 4: drawdown model diagnostics ===")
    actual_events = (ew_returns.shift(-1) < DD_THRESHOLD).astype(int)
    common = p_drawdown.index.intersection(actual_events.index)
    auc = compute_auc(p_drawdown.loc[common], actual_events.loc[common])
    print(f"\n=== Drawdown classifier diagnostics ===")
    print(f"  Out-of-sample AUC: {auc:.4f}")
    print(f"  Realized event rate: {actual_events.loc[common].mean():.4f}")
    print("\n=== Calibration table ===")
    print(calibration_table(p_drawdown, actual_events).to_string(index=False))
    fi = dd_result["feature_importance"]
    if not fi.empty:
        avg_imp = fi.mean(axis=1).sort_values(ascending=False)
        print(f"\n=== Top 10 features by avg gain importance ===")
        for name, val in avg_imp.head(10).items():
            print(f"  {name:30s}  {val:>10.1f}")

    log.info("=== Step 5: building strategy weights ===")
    weights_hist = build_weights(asset_returns, regime_labels, vol_forecasts,
                                   vol_baseline, p_drawdown, p_dd_baseline)

    log.info("=== Step 6: running backtests (ESTR-financed leverage) ===")
    fin_rate = weekly_financing_rate(asset_returns.index)
    results = {name: run_backtest(asset_returns, w, cost_bps=COST_BPS,
                                   cash_return=fin_rate)
               for name, w in weights_hist.items()}

    log.info("=== Step 7: performance metrics ===")
    # Common evaluation window so all six strategies are apples-to-apples. The
    # timing strategies (Vol-Forecast, DD-Predict) only carry their own signal
    # from EVAL_START; before it they coincide with VT-ERC, so crediting their
    # pre-signal path -- including the 2008 GFC drawdown -- would be misleading.
    common_idx = results["EW"]["net_returns"].index
    for res in results.values():
        common_idx = common_idx.intersection(res["net_returns"].index)
    common_idx = common_idx[common_idx >= EVAL_START]

    summary_table = pd.DataFrame()
    for name, res in results.items():
        r = res["net_returns"].reindex(common_idx).dropna()
        t = res["turnover"].reindex(common_idx)
        summary_table[name] = pd.Series(summary(r, t))
    print(f"\n=== Strategy comparison | common window "
          f"{common_idx.min().date()} -> {common_idx.max().date()} "
          f"({len(common_idx)} wks, net of {COST_BPS:.0f}bp + ESTR financing) ===")
    print(summary_table.to_string(float_format=lambda x: f"{x:.4f}"))

    full_table = pd.DataFrame()
    for name, res in results.items():
        full_table[name] = pd.Series(summary(res["net_returns"], res["turnover"]))
    print("\n=== Reference: full-period metrics (timing strategies coincide "
          "with VT-ERC before EVAL_START) ===")
    print(full_table.to_string(float_format=lambda x: f"{x:.4f}"))

    log.info("=== Step 8: regime-conditional returns (walk-forward labels) ===")
    rc_table = pd.DataFrame({
        name: regime_conditional_returns(
            res["net_returns"].reindex(common_idx).dropna(), regime_labels)
        for name, res in results.items()})
    print("\n=== Annualized return by (out-of-sample) regime ===")
    print(rc_table.to_string(float_format=lambda x: f"{x:.4f}"))

    log.info("=== Step 9: exposure stats ===")
    exposure_table = pd.DataFrame({
        name: {"avg_gross_exposure": float(res["weights"].sum(axis=1).mean()),
               "min_gross_exposure": float(res["weights"].sum(axis=1).min()),
               "max_gross_exposure": float(res["weights"].sum(axis=1).max()),
               "avg_equity_weight": float(res["weights"]["SX5E_ret_1w"].mean())}
        for name, res in results.items()})
    print("\n=== Exposure statistics ===")
    print(exposure_table.to_string(float_format=lambda x: f"{x:.4f}"))

    log.info("=== Step 10: saving + plotting ===")
    for name, res in results.items():
        clean = name.replace("-", "_").lower()
        save_panel(res["net_returns"].to_frame(name="net_return"), name=f"backtest_{clean}_returns")
        save_panel(res["weights"], name=f"backtest_{clean}_weights")
    save_panel(summary_table.T, name="backtest_summary")
    save_panel(full_table.T, name="backtest_summary_fullperiod")
    save_panel(rc_table, name="backtest_regime_conditional")
    save_panel(p_drawdown.to_frame(), name="dd_classifier_probabilities")
    plot_results = {name: {"net_returns": res["net_returns"].reindex(common_idx).dropna()}
                    for name, res in results.items()}
    plot_strategies(plot_results)
    plot_drawdown_predictions(p_drawdown, p_dd_baseline, ew_returns, DD_THRESHOLD)
    print("\n=== Phase 5b complete ===")


if __name__ == "__main__":
    main()
