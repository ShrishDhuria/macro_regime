"""Phase 3 orchestrator - fit 2-state AND 3-state HMMs with cross-comparison."""
from __future__ import annotations
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from data.storage import save_panel
from features.short_rate import build_unified_short_rate
from regimes.data_prep import assemble_hmm_inputs
from regimes.hmm_model import fit_hmm, label_regimes_by_volatility
from regimes.diagnostics import (regime_statistics, plot_regime_overlay,
                                  plot_regime_probabilities)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("build_regimes")


def fit_and_diagnose(X, raw, n_states, n_seeds=1):
    log.info(f"=== Fitting {n_states}-state HMM (n_seeds={n_seeds}) ===")
    res = fit_hmm(X, n_states=n_states, n_seeds=n_seeds)
    log.info(f"Converged: {res['converged']}  LL: {res['log_likelihood']:.2f}  per-obs: {res['score_per_obs']:.4f}")
    labels = label_regimes_by_volatility(res["emission_means"])
    log.info(f"Labels: {labels}")
    stats = regime_statistics(res["viterbi"], labels)
    print(f"\n=== {n_states}-state regime statistics ==="); print(stats.to_string(index=False))
    print(f"\n=== {n_states}-state transition matrix ==="); print(res["transition_matrix"].round(3).to_string())
    print(f"\n=== {n_states}-state emission means (raw units) ===")
    raw_means = raw.assign(regime=res["viterbi"]).groupby("regime").mean().round(3)
    raw_means.index = [f"regime_{i} ({labels[i]})" for i in raw_means.index]
    print(raw_means.to_string())
    plot_regime_overlay(res["viterbi"], labels, filename=f"regime_overlay_{n_states}state.png")
    label_cols = [f"P({labels[i]})" for i in range(len(labels))]
    probs_labeled = res["probabilities"].copy(); probs_labeled.columns = label_cols
    plot_regime_probabilities(probs_labeled, filename=f"regime_probabilities_{n_states}state.png")
    save_panel(res["viterbi"].to_frame(), name=f"hmm_viterbi_{n_states}state")
    save_panel(probs_labeled, name=f"hmm_probabilities_{n_states}state")
    save_panel(res["transition_matrix"], name=f"hmm_transition_{n_states}state")
    save_panel(res["emission_means"], name=f"hmm_emissions_{n_states}state")
    return res, labels


def find_contiguous_runs(dates, max_gap_days=14):
    if len(dates) == 0:
        return []
    sorted_dates = dates.sort_values()
    runs, run_start, prev = [], sorted_dates[0], sorted_dates[0]
    for d in sorted_dates[1:]:
        if (d - prev) > pd.Timedelta(days=max_gap_days):
            runs.append((run_start, prev)); run_start = d
        prev = d
    runs.append((run_start, prev))
    return runs


def main():
    log.info("=== Step 1: building unified ESTR/EONIA short-rate series ===")
    try:
        build_unified_short_rate()
    except Exception as e:
        log.error(f"EONIA fetch failed: {type(e).__name__}: {e}"); sys.exit(1)

    log.info("=== Step 2: assembling HMM input matrix ===")
    X, raw = assemble_hmm_inputs()
    log.info(f"Feature matrix: {X.shape}")

    res2, labels2 = fit_and_diagnose(X, raw, n_states=2, n_seeds=1)
    res3, labels3 = fit_and_diagnose(X, raw, n_states=3, n_seeds=5)

    aligned = pd.DataFrame({"2state": res2["viterbi"].map(labels2),
                            "3state": res3["viterbi"].map(labels3)})
    print("\n=== 2-state vs 3-state cross-tab (week counts) ===")
    print(pd.crosstab(aligned["2state"], aligned["3state"]).to_string())

    bridge = aligned[(aligned["2state"] == "calm") & (aligned["3state"] == "transition")].index
    if len(bridge) > 0:
        runs = find_contiguous_runs(bridge)
        runs_with_len = sorted([(s, e, (e - s).days // 7 + 1) for s, e in runs], key=lambda x: -x[2])
        print(f"\n=== Periods 3-state calls 'transition' but 2-state called 'calm' ===")
        print(f"Total: {len(bridge)} weeks across {len(runs)} runs. Top 8 longest:")
        for s, e, w in runs_with_len[:8]:
            print(f"  {s.date()} -> {e.date()}  ({w} weeks)")

    crisis_dates = aligned[aligned["3state"] == "crisis"].index
    if len(crisis_dates) > 0:
        print(f"\n=== 'Crisis' periods (3-state's most extreme regime) ===")
        for s, e in find_contiguous_runs(crisis_dates):
            print(f"  {s.date()} -> {e.date()}  ({(e - s).days // 7 + 1} weeks)")

    print("\n=== Phase 3 complete ===")


if __name__ == "__main__":
    main()
