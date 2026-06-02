"""Term-structure and sovereign spreads - the core macro-regime indicators."""
import pandas as pd
from data.storage import load_panel


def compute_spreads() -> pd.DataFrame:
    """Spreads computed on the weekly panel.

    TERM_DE        : DE10Y - ESTR     -- German curve slope; ECB stance + growth
    SPREAD_IT_DE   : IT10Y - DE10Y    -- Italian sovereign stress (2011-12, 2018)
    SPREAD_FR_DE   : FR10Y - DE10Y    -- French sovereign stress (milder)
    SPREAD_IT_FR   : IT10Y - FR10Y    -- Peripheral vs core
    """
    panel = load_panel()
    out = pd.DataFrame(index=panel.index)
    if "DE10Y" in panel and "ESTR" in panel:
        out["TERM_DE"] = panel["DE10Y"] - panel["ESTR"]
    if "IT10Y" in panel and "DE10Y" in panel:
        out["SPREAD_IT_DE"] = panel["IT10Y"] - panel["DE10Y"]
    if "FR10Y" in panel and "DE10Y" in panel:
        out["SPREAD_FR_DE"] = panel["FR10Y"] - panel["DE10Y"]
    if "IT10Y" in panel and "FR10Y" in panel:
        out["SPREAD_IT_FR"] = panel["IT10Y"] - panel["FR10Y"]
    return out
