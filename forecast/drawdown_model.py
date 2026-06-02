"""LightGBM drawdown probability forecasting, walk-forward.

Predicts P(next-week portfolio return < threshold) from macro+market features
directly - no regime classification middle layer. Refits every 13 weeks.
"""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd
import lightgbm as lgb

log = logging.getLogger(__name__)

DRAWDOWN_FEATURES = [
    "SX5E_rv_20d", "SX5E_rv_60d", "SX5E_rv_252d", "SX5E_vov_60d",
    "BRENT_rv_60d", "EURUSD_rv_60d", "BANKS_rv_60d",
    "TERM_DE", "SPREAD_IT_DE", "SPREAD_FR_DE", "SPREAD_IT_FR",
    "CORR_SX5E_EURUSD_60d", "CORR_SX5E_BRENT_60d",
    "CORR_SX5E_GOLD_60d", "CORR_BANKS_SX5E_60d",
    "SX5E_mom_13w_z", "SX5E_mom_52w_z",
    "BANKS_mom_13w_z", "EURUSD_mom_13w_z", "BRENT_mom_13w_z",
    "SX5E_ret_1w", "BRENT_ret_1w", "EURUSD_ret_1w", "GOLD_ret_1w",
]


def build_xy(features: pd.DataFrame, portfolio_returns: pd.Series, threshold: float = -0.02):
    feat_cols = [c for c in DRAWDOWN_FEATURES if c in features.columns]
    X = features[feat_cols].copy()
    next_ret = portfolio_returns.shift(-1)
    y = (next_ret < threshold).astype(int)
    aligned = pd.concat([X, y.rename("__y"), next_ret.rename("__nr")], axis=1)
    aligned = aligned.dropna(subset=feat_cols + ["__nr"])
    return aligned[feat_cols], aligned["__y"]


def _train(X, y, num_rounds=300):
    pos = int((y == 1).sum()); neg = int((y == 0).sum())
    spw = max(neg / max(pos, 1), 1.0)
    params = dict(objective="binary", learning_rate=0.04, num_leaves=15,
                  min_data_in_leaf=20, feature_fraction=0.7, bagging_fraction=0.8,
                  bagging_freq=4, scale_pos_weight=spw, verbose=-1)
    return lgb.train(params, lgb.Dataset(X.values, y.values, feature_name=list(X.columns)),
                     num_boost_round=num_rounds)


def walk_forward_predict(features, portfolio_returns, first_train_end,
                          refit_weeks=13, threshold=-0.02) -> dict:
    X, y = build_xy(features, portfolio_returns, threshold)
    forecast_dates = X.index[X.index > first_train_end]
    probs = pd.Series(index=forecast_dates, dtype=float, name="P_drawdown")
    refit_dates, feat_imps, model = [], [], None
    next_refit = first_train_end
    for date in forecast_dates:
        if date >= next_refit:
            cutoff = date - pd.Timedelta(weeks=1)
            mask = X.index <= cutoff
            X_tr, y_tr = X[mask], y[mask]
            if len(X_tr) >= 100 and y_tr.nunique() > 1:
                model = _train(X_tr, y_tr); refit_dates.append(date)
                feat_imps.append(pd.Series(model.feature_importance(importance_type="gain"),
                                            index=X.columns, name=str(date.date())))
            next_refit = date + pd.Timedelta(weeks=refit_weeks)
        if model is not None:
            probs.loc[date] = float(model.predict(X.loc[date].values.reshape(1, -1))[0])
    log.info(f"Drawdown classifier: {len(refit_dates)} refits, {probs.notna().sum()} predictions")
    feat_imp_df = pd.concat(feat_imps, axis=1) if feat_imps else pd.DataFrame()
    return {"probabilities": probs.dropna(), "refit_dates": refit_dates,
            "feature_importance": feat_imp_df, "threshold": threshold}


def calibration_table(probabilities, actual_events, n_bins=5):
    df = pd.concat([probabilities, actual_events], axis=1).dropna()
    df.columns = ["pred", "actual"]
    df["bin"] = pd.qcut(df["pred"], n_bins, duplicates="drop")
    return df.groupby("bin", observed=True).agg(
        n_obs=("actual", "size"), avg_pred_prob=("pred", "mean"),
        actual_freq=("actual", "mean")).reset_index()


def compute_auc(scores, labels):
    df = pd.concat([scores, labels], axis=1).dropna()
    df.columns = ["s", "y"]
    n_pos = int((df["y"] == 1).sum()); n_neg = int((df["y"] == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    df = df.sort_values("s", ascending=False).reset_index(drop=True)
    cumneg = (df["y"] == 0).cumsum()
    pos_mask = df["y"] == 1
    return float(((n_neg - cumneg)[pos_mask]).sum() / (n_pos * n_neg))
