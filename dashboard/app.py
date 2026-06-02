"""Streamlit dashboard: regime monitor, risk panel, strategies, live stress tester."""
from __future__ import annotations
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from data.storage import load_panel
from risk.portfolio import DEFAULT_PORTFOLIO
from stress.scenarios import STRESS_SCENARIOS
from stress.transmission import run_stress

st.set_page_config(page_title="Macro Regime Platform", layout="wide",
                    initial_sidebar_state="expanded")

st.markdown("""
<style>
.big-metric { font-size: 36px; font-weight: bold; color: #1E3A5F; }
.metric-label { font-size: 14px; color: #4A4A4A; text-transform: uppercase; }
.section-header { color: #1E3A5F; border-bottom: 2px solid #1E3A5F; padding-bottom: 6px; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_all():
    panel = load_panel()
    features = load_panel("master_features")
    viterbi3 = load_panel("hmm_viterbi_3state")["regime"]
    emissions3 = load_panel("hmm_emissions_3state")
    sorted_states = emissions3["SX5E_rv_60d"].sort_values()
    label_map = dict(zip([int(s.split("_")[1]) for s in sorted_states.index],
                          ["calm", "transition", "crisis"]))
    regime_labels = viterbi3.map(label_map)
    summary_df = load_panel("backtest_summary")
    rc_df = load_panel("backtest_regime_conditional")
    backtests = {}
    for s in ["ew", "erc", "vt_erc", "regime_tilt", "vol_forecast", "dd_predict"]:
        try:
            backtests[s] = load_panel(f"backtest_{s}_returns")["net_return"]
        except Exception:
            pass
    try:
        risk_rc = load_panel("risk_regime_conditional_3state")
    except Exception:
        risk_rc = None
    return panel, features, regime_labels, emissions3, summary_df, rc_df, backtests, risk_rc


panel, features, regime_labels, emissions3, summary_df, rc_df, backtests, risk_rc = load_all()

st.sidebar.title("Macro Regime Platform")
st.sidebar.markdown("**ESSEC MIF research framework**")
st.sidebar.markdown("---")
current_regime = regime_labels.dropna().iloc[-1]
last_date = regime_labels.dropna().index[-1].date()
regime_colors = {"calm": "#9ec5a8", "transition": "#f4d35e", "crisis": "#c1121f"}
st.sidebar.markdown(f"### Current regime")
st.sidebar.markdown(
    f"<div style='padding:14px;background:{regime_colors[current_regime]};"
    f"border-radius:8px;text-align:center;font-size:24px;font-weight:bold;'>"
    f"{current_regime.upper()}</div>", unsafe_allow_html=True)
st.sidebar.caption(f"as of {last_date}")

tabs = st.tabs(["Regime Monitor", "Risk Panel", "Strategies", "Stress Tester"])

with tabs[0]:
    st.markdown("<h2 class='section-header'>Macro Regime Monitor</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    counts = regime_labels.value_counts(); total = counts.sum()
    for col, regime in zip([col1, col2, col3], ["calm", "transition", "crisis"]):
        n = int(counts.get(regime, 0)); pct = n / total * 100 if total else 0
        col.markdown(f"<div class='metric-label'>{regime}</div>", unsafe_allow_html=True)
        col.markdown(f"<div class='big-metric' style='color:{regime_colors[regime]};'>{pct:.1f}%</div>",
                       unsafe_allow_html=True)
        col.caption(f"{n} weeks")
    st.markdown("### SX5E with regime classification")
    sx5e = panel["SX5E"].dropna().reindex(regime_labels.dropna().index).dropna()
    aligned_regimes = regime_labels.reindex(sx5e.index)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sx5e.index, y=sx5e.values, mode="lines",
                              name="SX5E", line=dict(color="black", width=1.2)))
    in_run, run_start, run_regime = False, None, None
    for date, r in aligned_regimes.items():
        if not in_run or r != run_regime:
            if in_run:
                fig.add_vrect(x0=run_start, x1=date, fillcolor=regime_colors[run_regime],
                              opacity=0.25, line_width=0)
            run_start, run_regime, in_run = date, r, True
    if in_run:
        fig.add_vrect(x0=run_start, x1=aligned_regimes.index[-1],
                       fillcolor=regime_colors[run_regime], opacity=0.25, line_width=0)
    fig.update_layout(height=440, margin=dict(l=20, r=20, t=20, b=20),
                       xaxis_title="Date", yaxis_title="SX5E level")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("### Regime emission means (raw units)")
    sorted_states = emissions3["SX5E_rv_60d"].sort_values()
    state_to_label = dict(zip([int(s.split("_")[1]) for s in sorted_states.index],
                                ["calm", "transition", "crisis"]))
    em_disp = emissions3.copy()
    em_disp.index = [state_to_label[int(s.split("_")[1])] for s in em_disp.index]
    em_disp = em_disp.reindex(["calm", "transition", "crisis"])
    st.dataframe(em_disp.style.format("{:.4f}"), use_container_width=True)

with tabs[1]:
    st.markdown("<h2 class='section-header'>Risk Engine</h2>", unsafe_allow_html=True)
    st.markdown("### Multi-asset macro portfolio")
    pcol1, pcol2 = st.columns([1, 2])
    with pcol1:
        wdf = pd.DataFrame({"Asset": list(DEFAULT_PORTFOLIO.keys()),
                            "Weight": [f"{v:.0%}" for v in DEFAULT_PORTFOLIO.values()]})
        st.dataframe(wdf, use_container_width=True, hide_index=True)
    with pcol2:
        fig = px.pie(values=list(DEFAULT_PORTFOLIO.values()),
                       names=list(DEFAULT_PORTFOLIO.keys()), hole=0.5)
        fig.update_layout(height=280, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)
    if risk_rc is not None:
        st.markdown("### Regime-conditional risk metrics (3-state)")
        st.dataframe(risk_rc.style.format("{:.4f}"), use_container_width=True)
        st.caption("Crisis ES99 ~17.5% vs calm ES99 ~6.9% - regime-conditional framing is the "
                    "institutional payoff of the HMM.")

with tabs[2]:
    st.markdown("<h2 class='section-header'>Tactical Allocation Backtest</h2>", unsafe_allow_html=True)
    if backtests:
        fig = go.Figure()
        for name, ret in backtests.items():
            cum = (1 + ret).cumprod()
            fig.add_trace(go.Scatter(x=cum.index, y=cum.values, mode="lines",
                                       name=name.upper().replace("_", "-"), line=dict(width=1.6)))
        fig.update_layout(height=460, yaxis_type="log", xaxis_title="Date",
                            yaxis_title="Cumulative wealth (log)", margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
        if summary_df is not None:
            st.markdown("### Strategy comparison")
            st.dataframe(summary_df.T.style.format("{:.4f}"), use_container_width=True)
        if rc_df is not None:
            st.markdown("### Annualized return by regime")
            st.dataframe(rc_df.style.format("{:.4f}"), use_container_width=True)
    st.info("**Honest finding:** regime-tilt and DD-Predict underperformed equal-weight. "
              "Regime detection is a risk-monitoring tool, not a return-timing signal.")

with tabs[3]:
    st.markdown("<h2 class='section-header'>Live Stress Tester</h2>", unsafe_allow_html=True)
    st.markdown("Adjust shocks; portfolio P&L computed from rolling 156-week empirical betas.")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        ecb_shock = st.slider("ECB rate shock (pp)", -2.0, 2.0, 0.0, 0.25)
        brent_shock = st.slider("Brent return shock", -0.40, 0.40, 0.0, 0.05)
    with col_b:
        eurusd_shock = st.slider("EUR/USD return shock", -0.15, 0.15, 0.0, 0.01)
        equity_shock = st.slider("Equity (SX5E) shock", -0.30, 0.20, 0.0, 0.02)
    with col_c:
        spread_shock = st.slider("IT-DE spread shock (pp)", -1.0, 4.0, 0.0, 0.25)
        vol_shock = st.slider("Equity vol shock (pp)", -0.10, 0.20, 0.0, 0.02)
    custom = {
        "Custom: ECB":     {"description": "user", "trigger": "ESTR",         "shock": ecb_shock,    "shock_type": "level_pp"},
        "Custom: Brent":   {"description": "user", "trigger": "BRENT",        "shock": brent_shock,  "shock_type": "log_return"},
        "Custom: EUR/USD": {"description": "user", "trigger": "EURUSD",       "shock": eurusd_shock, "shock_type": "log_return"},
        "Custom: Equity":  {"description": "user", "trigger": "SX5E",         "shock": equity_shock, "shock_type": "log_return"},
        "Custom: Spread":  {"description": "user", "trigger": "SPREAD_IT_DE", "shock": spread_shock, "shock_type": "level_pp"},
        "Custom: Vol":     {"description": "user", "trigger": "SX5E_rv_60d",  "shock": vol_shock,    "shock_type": "level_pp"},
    }
    asset_names = list(DEFAULT_PORTFOLIO.keys())
    custom_results = run_stress(features, panel, custom, asset_names, DEFAULT_PORTFOLIO, window=156)
    total_pnl = float(custom_results["portfolio_pnl"].sum())
    st.markdown("---")
    bc1, bc2 = st.columns([1, 2])
    with bc1:
        st.markdown("<div class='metric-label'>Combined portfolio P&L</div>", unsafe_allow_html=True)
        color = "#c1121f" if total_pnl < 0 else "#2d6a4f"
        st.markdown(f"<div class='big-metric' style='color:{color}'>{total_pnl:+.2%}</div>", unsafe_allow_html=True)
        st.caption("Sum of independent-shock P&Ls (no second-order interactions)")
    with bc2:
        fig = go.Figure(go.Bar(x=custom_results["scenario"], y=custom_results["portfolio_pnl"],
                                marker_color=["#c1121f" if v < 0 else "#2d6a4f"
                                                for v in custom_results["portfolio_pnl"]]))
        fig.update_layout(height=260, margin=dict(l=20, r=20, t=20, b=20),
                            yaxis_tickformat=".1%", yaxis_title="P&L impact")
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("### Pre-defined scenarios (institutional benchmarks)")
    std = run_stress(features, panel, STRESS_SCENARIOS, asset_names, DEFAULT_PORTFOLIO, window=156)
    disp = std[["scenario", "description", "trigger", "trigger_shock", "portfolio_pnl"]].copy()
    disp["trigger_shock"] = disp["trigger_shock"].apply(lambda x: f"{x:+.2f}")
    disp["portfolio_pnl"] = disp["portfolio_pnl"].apply(lambda x: f"{x:+.2%}")
    st.dataframe(disp, use_container_width=True, hide_index=True)
