"""LightGBM-based volatility forecasting with walk-forward refitting.

Forecasts SX5E 20-day realized vol 4 weeks ahead. Training at refit date d uses
only rows whose target was observable by d (t <= d - horizon). No lookahead.
"""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd
import lightgbm as lgb

log = logging.getLogger(__name__)

FEATURE_COLS = [
    "SX5E_rv_20d", "SX5E_rv_60d", "SX5E_rv_252d", "SX5E_vov_60d",
    "SPREAD_IT_DE", "SPREAD_FR_DE", "TERM_DE",
    "CORR_SX5E_EURUSD_60d", "CORR_SX5E_BRENT_60d",
    "BRENT_rv_60d", "EURUSD_rv_60d",
    "SX5E_mom_13w_z", "SX5E_mom_52w_z",
]


def build_xy(features: pd.DataFrame, target_col: str = "SX5E_rv_20d", horizon: int = 4):
    cols = [c for c in FEATURE_COLS if c in features.columns]
    X = features[cols].copy()
    y = features[target_col].shift(-horizon)
    aligned = pd.concat([X, y.rename("__y")], axis=1).dropna()
    return aligned[cols], aligned["__y"]


def _train_lgb(X, y, num_rounds=200):
    params = dict(objective="regression", learning_rate=0.05, num_leaves=15,
                  min_data_in_leaf=20, feature_fraction=0.8, bagging_fraction=0.8,
                  bagging_freq=4, verbose=-1)
    return lgb.train(params, lgb.Dataset(X.values, y.values, feature_name=list(X.columns)),
                     num_boost_round=num_rounds)


def walk_forward_vol_forecast(features: pd.DataFrame, first_train_end: pd.Timestamp,
                                refit_weeks: int = 13, target_col: str = "SX5E_rv_20d",
                                horizon: int = 4) -> pd.Series:
    X, y = build_xy(features, target_col, horizon)
    forecast_dates = X.index[X.index > first_train_end]
    forecasts = pd.Series(index=forecast_dates, dtype=float, name=f"forecast_{target_col}")
    refit_dates, model = [], None
    next_refit = first_train_end
    for date in forecast_dates:
        if date >= next_refit:
            cutoff = date - pd.Timedelta(weeks=horizon)
            valid_idx = X.index[X.index <= cutoff]
            X_tr = X.loc[valid_idx]; y_tr = y.loc[valid_idx].dropna()
            X_tr = X_tr.loc[y_tr.index]
            if len(X_tr) >= 100:
                model = _train_lgb(X_tr, y_tr); refit_dates.append(date)
            next_refit = date + pd.Timedelta(weeks=refit_weeks)
        if model is not None:
            forecasts.loc[date] = float(model.predict(X.loc[date].values.reshape(1, -1))[0])
    log.info(f"Vol forecast: {len(refit_dates)} refits, {forecasts.notna().sum()} forecasts")
    return forecasts.dropna()
