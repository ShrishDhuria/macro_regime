"""Stress test scenario definitions: parametric shocks to underlying drivers."""

STRESS_SCENARIOS = {
    "ECB +100bps":         {"description": "Hawkish surprise; risk-off, EUR up, equity down",
                             "trigger": "ESTR",         "shock":  1.00, "shock_type": "level_pp"},
    "ECB -100bps (cut)":   {"description": "Recession scare; emergency cut",
                             "trigger": "ESTR",         "shock": -1.00, "shock_type": "level_pp"},
    "Brent +25%":          {"description": "Oil supply shock; inflation pickup",
                             "trigger": "BRENT",        "shock":  0.25, "shock_type": "log_return"},
    "Brent -25%":          {"description": "Oil demand collapse; growth scare",
                             "trigger": "BRENT",        "shock": -0.25, "shock_type": "log_return"},
    "EUR/USD -8%":         {"description": "Euro selloff; export benefit, import inflation",
                             "trigger": "EURUSD",       "shock": -0.08, "shock_type": "log_return"},
    "Equity crash -20%":   {"description": "Major drawdown a la Q1 2020 / Sep 2008",
                             "trigger": "SX5E",         "shock": -0.20, "shock_type": "log_return"},
    "IT-DE spread +200bp": {"description": "Italian sovereign stress (2011-12 style)",
                             "trigger": "SPREAD_IT_DE", "shock":  2.00, "shock_type": "level_pp"},
    "Vol shock +10pp":     {"description": "Equity vol regime shift; risk-off propagation",
                             "trigger": "SX5E_rv_60d",  "shock":  0.10, "shock_type": "level_pp"},
}
