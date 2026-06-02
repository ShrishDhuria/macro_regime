"""Render the two headline findings as a README figure.

These are the reported walk-forward backtest results (2011-2026, 5bp costs,
ESTR-financed leverage) and the regime-conditional Expected Shortfall — the
same numbers in the README "Key findings" table. The full equity-curve and
drawdown plots are produced by the pipeline itself:

    python scripts/build_panel.py        # downloads + builds the panel
    python scripts/build_strategies.py   # writes reports/strategy_comparison.png
    python make_figures.py               # writes docs/strategy_results.png

Run this script directly for the summary figure (no network needed).
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "docs")
os.makedirs(DOCS, exist_ok=True)

# Reported results (see README "Key findings"). Re-run build_strategies.py to
# regenerate from the live pipeline; levels may shift but the ordering does not.
STRATEGIES = [
    ("Equal Weight", 0.29, True),
    ("ERC (risk parity)", 0.26, False),
    ("VT-ERC", 0.21, False),
    ("Vol-Forecast (LightGBM)", 0.21, False),
    ("Regime-Tilt", 0.17, False),
    ("DD-Predict (LightGBM)", 0.16, False),
]
ES_CALM, ES_CRISIS = 6.9, 17.5   # 99% historical ES by regime (%)


def main():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6),
                                   gridspec_kw={"width_ratios": [1.6, 1]})

    # Panel A — Sharpe by strategy; the benchmark (equal weight) is the bar to beat
    order = sorted(STRATEGIES, key=lambda s: s[1])
    names = [s[0] for s in order]
    sharpes = [s[1] for s in order]
    colours = ["#c44e34" if s[2] else "#4a7a96" for s in order]
    ax1.barh(names, sharpes, color=colours)
    ax1.axvline(0.29, color="#c44e34", ls="--", lw=1.2)
    for i, v in enumerate(sharpes):
        ax1.text(v + 0.004, i, f"{v:.2f}", va="center", fontsize=9)
    ax1.set_xlabel("Sharpe ratio (walk-forward, 2011–2026, net of 5bp costs)")
    ax1.set_title("Tactical timing does not beat equal-weight")
    ax1.grid(alpha=0.25, axis="x")

    # Panel B — regime-conditional 99% ES: the institutionally useful result
    bars = ax2.bar(["Calm", "Crisis"], [ES_CALM, ES_CRISIS],
                   color=["#5a9367", "#b5462f"])
    for b, v in zip(bars, [ES_CALM, ES_CRISIS]):
        ax2.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{v:.1f}%",
                 ha="center", va="bottom", fontsize=10)
    ax2.set_ylabel("99% historical Expected Shortfall (%)")
    ax2.set_title("Regime-conditional risk: 2.5× scaling")
    ax2.grid(alpha=0.25, axis="y")

    fig.tight_layout()
    out = os.path.join(DOCS, "strategy_results.png")
    fig.savefig(out, dpi=130, bbox_inches="tight")
    print("wrote", out)


if __name__ == "__main__":
    main()
