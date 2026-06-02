"""Per-regime statistics and visualization."""
from __future__ import annotations
import logging
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from data.storage import load_panel

log = logging.getLogger(__name__)
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

REGIME_COLORS = {"calm": "#9ec5a8", "transition": "#f4d35e", "stress": "#e07a5f", "crisis": "#c1121f"}
DEFAULT_PALETTE = ["#9ec5a8", "#f4d35e", "#e07a5f", "#c1121f"]


def regime_statistics(viterbi: pd.Series, regime_labels: dict) -> pd.DataFrame:
    features = load_panel("master_features")
    sx5e_ret = features["SX5E_ret_1w"].reindex(viterbi.index)
    sx5e_rv = features["SX5E_rv_60d"].reindex(viterbi.index)
    runs = (viterbi != viterbi.shift()).cumsum()
    rows = []
    for state_id, label in regime_labels.items():
        mask = viterbi == state_id
        n_weeks = int(mask.sum())
        pct = n_weeks / len(viterbi) * 100
        n_runs = runs[mask].nunique() if mask.any() else 0
        avg_dur = n_weeks / n_runs if n_runs > 0 else float("nan")
        rows.append({"regime_id": state_id, "label": label, "n_weeks": n_weeks,
                     "pct_of_sample": round(pct, 1), "n_runs": int(n_runs),
                     "avg_duration_weeks": round(avg_dur, 1),
                     "avg_sx5e_weekly_return": round(sx5e_ret[mask].mean(), 4),
                     "avg_sx5e_rv_60d": round(sx5e_rv[mask].mean(), 3)})
    return pd.DataFrame(rows).sort_values("regime_id").reset_index(drop=True)


def _plot_regime_spans(ax, viterbi, regime_labels):
    for state_id, label in regime_labels.items():
        color = REGIME_COLORS.get(label, DEFAULT_PALETTE[state_id % len(DEFAULT_PALETTE)])
        mask = viterbi == state_id
        in_run, run_start = False, None
        for date, m in mask.items():
            if m and not in_run:
                run_start, in_run = date, True
            elif not m and in_run:
                ax.axvspan(run_start, date, alpha=0.25, color=color); in_run = False
        if in_run:
            ax.axvspan(run_start, mask.index[-1], alpha=0.25, color=color)


def plot_regime_overlay(viterbi, regime_labels, filename="regime_overlay.png"):
    panel = load_panel()
    sx5e = panel["SX5E"].reindex(viterbi.index).dropna()
    viterbi_aligned = viterbi.reindex(sx5e.index)
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(sx5e.index, sx5e.values, color="black", linewidth=1)
    _plot_regime_spans(ax, viterbi_aligned, regime_labels)
    handles = [plt.Line2D([0], [0], color="black", label="SX5E")]
    for sid, label in regime_labels.items():
        color = REGIME_COLORS.get(label, DEFAULT_PALETTE[sid % len(DEFAULT_PALETTE)])
        handles.append(mpatches.Patch(color=color, alpha=0.5, label=label))
    ax.legend(handles=handles, loc="upper left")
    ax.set_title("SX5E with HMM-detected regimes")
    ax.set_ylabel("SX5E level"); ax.set_xlabel("Date"); ax.grid(True, alpha=0.3)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / filename
    fig.tight_layout(); fig.savefig(out, dpi=120); plt.close(fig)
    log.info(f"Saved {out}")
    return out


def plot_regime_probabilities(probabilities, filename="regime_probabilities.png"):
    fig, ax = plt.subplots(figsize=(14, 4))
    n = probabilities.shape[1]
    ax.stackplot(probabilities.index, probabilities.T.values,
                 labels=probabilities.columns, colors=DEFAULT_PALETTE[:n], alpha=0.7)
    ax.set_ylim(0, 1); ax.set_ylabel("Regime probability"); ax.set_xlabel("Date")
    ax.set_title("HMM regime probabilities through time")
    ax.legend(loc="upper left"); ax.grid(True, alpha=0.3)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / filename
    fig.tight_layout(); fig.savefig(out, dpi=120); plt.close(fig)
    log.info(f"Saved {out}")
    return out
