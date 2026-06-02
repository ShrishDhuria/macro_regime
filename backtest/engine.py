"""Walk-forward backtest engine with transaction costs."""
from __future__ import annotations
import logging
import pandas as pd

log = logging.getLogger(__name__)


def run_backtest(asset_returns, weights_history, cost_bps=5.0, cash_return=0.0) -> dict:
    """Weights at row t are decided at end of t and apply during t+1.
    Turnover-cost incurred at t-rebalance reduces t+1's net return.

    cash_return may be a scalar weekly rate or a pd.Series of weekly financing
    rates (decimal, indexed like asset_returns). The cash weight is 1 - gross
    invested exposure: positive cash (under-invested) earns the rate, negative
    cash (leverage > 1) pays it as a funding cost. Passing the spliced ESTR here
    removes the implicit "free leverage" assumption for vol-targeted strategies.
    """
    common = asset_returns.index.intersection(weights_history.index)
    rets = asset_returns.loc[common]
    w = weights_history.loc[common].fillna(0.0)
    w_lag = w.shift(1)
    invested = w_lag.sum(axis=1)
    cash_w = 1 - invested
    if isinstance(cash_return, pd.Series):
        cash_r = cash_return.reindex(common).ffill().fillna(0.0)
    else:
        cash_r = cash_return
    gross_return = (w_lag * rets).sum(axis=1) + cash_w * cash_r
    turnover = (w - w.shift(1)).abs().sum(axis=1) / 2
    cost = turnover.shift(1) * cost_bps / 10000
    net_return = (gross_return - cost.fillna(0)).dropna()
    return {"net_returns": net_return, "gross_returns": gross_return.dropna(),
            "turnover": turnover.dropna(), "weights": w, "cash_weight": cash_w}
