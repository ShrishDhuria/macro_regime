"""Apply risk metrics conditional on HMM regime classification."""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd
from data.storage import load_panel
from risk.var import historical_var, parametric_var, cornish_fisher_var
from risk.expected_shortfall import historical_es, parametric_es

log = logging.getLogger(__name__)


def _regime_label_map(n_states: int) -> dict:
    emissions = load_panel(f"hmm_emissions_{n_states}state")
    sorted_states = emissions["SX5E_rv_60d"].sort_values()
    if n_states == 3:
        names = ["calm", "transition", "crisis"]
    elif n_states == 2:
        names = ["calm", "stress"]
    else:
        names = [f"regime_{i}" for i in range(n_states)]
    return {int(s.split("_")[1]): name for s, name in zip(sorted_states.index, names)}


def regime_classified_returns(returns: pd.Series, n_states: int = 3) -> pd.DataFrame:
    viterbi = load_panel(f"hmm_viterbi_{n_states}state")["regime"]
    labels = _regime_label_map(n_states)
    regime_series = viterbi.map(labels)
    aligned = pd.concat([returns, regime_series], axis=1).dropna()
    aligned.columns = ["return", "regime"]
    return aligned


def regime_conditional_summary(returns: pd.Series, n_states: int = 3) -> pd.DataFrame:
    classified = regime_classified_returns(returns, n_states=n_states)
    order = (["calm", "transition", "crisis"] if n_states == 3
             else ["calm", "stress"] if n_states == 2
             else sorted(classified["regime"].unique()))
    metrics = {
        "Mean weekly return":      lambda r: r.mean(),
        "Std dev (weekly)":        lambda r: r.std(),
        "Annualized vol":          lambda r: r.std() * np.sqrt(52),
        "Skew":                    lambda r: r.skew(),
        "Excess kurtosis":         lambda r: r.kurtosis(),
        "Min weekly return":       lambda r: r.min(),
        "Hist VaR 95%":            lambda r: historical_var(r, 0.05),
        "Hist VaR 99%":            lambda r: historical_var(r, 0.01),
        "Param VaR 95%":           lambda r: parametric_var(r, 0.05),
        "Cornish-Fisher VaR 95%":  lambda r: cornish_fisher_var(r, 0.05),
        "Hist ES 95%":             lambda r: historical_es(r, 0.05),
        "Hist ES 99%":             lambda r: historical_es(r, 0.01),
        "Param ES 95%":            lambda r: parametric_es(r, 0.05),
        "N weeks":                 lambda r: float(len(r)),
    }
    out = pd.DataFrame(index=list(metrics.keys()), columns=order, dtype=float)
    for regime in order:
        rgrp = classified.loc[classified["regime"] == regime, "return"]
        for name, fn in metrics.items():
            try:
                out.loc[name, regime] = float(fn(rgrp))
            except Exception:
                out.loc[name, regime] = float("nan")
    return out
