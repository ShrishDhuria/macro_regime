"""Translate stress shocks to portfolio asset return shocks via empirical betas."""
from __future__ import annotations
import numpy as np
import pandas as pd


def _trigger_change_series(features, panel, trigger, shock_type):
    if shock_type == "log_return":
        col = f"{trigger}_ret_1w"
        if col in features.columns:
            return features[col]
    elif shock_type == "level_pp":
        if trigger in panel.columns:
            return panel[trigger].diff()
        if trigger in features.columns:
            return features[trigger].diff()
    return None


def compute_betas(features, panel, trigger, shock_type, asset_names, window=156):
    x = _trigger_change_series(features, panel, trigger, shock_type)
    if x is None:
        return None
    betas = {}
    for asset in asset_names:
        y = features.get(f"{asset}_ret_1w")
        if y is None:
            betas[asset] = 0.0; continue
        df = pd.concat([y, x], axis=1).dropna().tail(window)
        if len(df) < 20:
            betas[asset] = 0.0; continue
        var_x = df.iloc[:, 1].var()
        betas[asset] = (df.iloc[:, 0].cov(df.iloc[:, 1]) / var_x) if var_x > 0 else 0.0
    return betas


def run_stress(features, panel, scenarios, asset_names, weights, window=156):
    rows = []
    for name, scen in scenarios.items():
        betas = compute_betas(features, panel, scen["trigger"], scen["shock_type"], asset_names, window)
        if betas is None:
            continue
        asset_shocks = {a: betas[a] * scen["shock"] for a in asset_names}
        if scen["trigger"] in asset_names and scen["shock_type"] == "log_return":
            asset_shocks[scen["trigger"]] = scen["shock"]
        pnl = sum(weights.get(a, 0) * asset_shocks[a] for a in asset_names)
        row = {"scenario": name, "description": scen["description"], "trigger": scen["trigger"],
               "trigger_shock": scen["shock"], "portfolio_pnl": pnl}
        for a in asset_names:
            row[f"impl_{a}"] = asset_shocks[a]
        rows.append(row)
    return pd.DataFrame(rows)
