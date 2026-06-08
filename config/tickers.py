"""Canonical ticker registry for the macro regime platform."""

EQUITY = {
    "SX5E":  {"source": "yfinance", "symbol": "^STOXX50E", "name": "Euro Stoxx 50",  "cadence": "daily"},
    "CAC":   {"source": "yfinance", "symbol": "^FCHI",     "name": "CAC 40",         "cadence": "daily"},
    "DAX":   {"source": "yfinance", "symbol": "^GDAXI",    "name": "DAX 40",         "cadence": "daily"},
    "BANKS": {"source": "yfinance", "symbol": "EXV1.DE",   "name": "iShares STOXX 600 Banks ETF (SX7E proxy)", "cadence": "daily"},
}

FX = {
    "EURUSD": {"source": "yfinance", "symbol": "EURUSD=X", "name": "EUR/USD", "cadence": "daily"},
}

COMMODITIES = {
    "BRENT": {"source": "yfinance", "symbol": "BZ=F", "name": "Brent front-month", "cadence": "daily"},
    "GOLD":  {"source": "yfinance", "symbol": "GC=F", "name": "Gold front-month",  "cadence": "daily"},
}

VOL = {
    "VIX": {"source": "yfinance", "symbol": "^VIX",  "name": "CBOE VIX", "cadence": "daily"},
    "V2X": {"source": "yfinance", "symbol": "^V2TX", "name": "VSTOXX (delisted on Yahoo; replaced by SX5E realized vol)",
            "cadence": "daily", "expect_failure": True},
}

RATES = {
    "DE10Y": {"source": "fred", "symbol": "IRLTLT01DEM156N", "name": "Germany 10Y yield", "cadence": "monthly"},
    "FR10Y": {"source": "fred", "symbol": "IRLTLT01FRM156N", "name": "France 10Y yield",  "cadence": "monthly"},
    "IT10Y": {"source": "fred", "symbol": "IRLTLT01ITM156N", "name": "Italy 10Y yield",   "cadence": "monthly"},
    # ESTR via FRED (ECBESTRVOLWGTTRMDMNRT), NOT the ECB Data Portal.
    # The ECB host (data-api.ecb.europa.eu) is unreachable from some networks
    # (DNS getaddrinfo failures); FRED mirrors the identical EST.B.EU000A2X2A25.WT
    # series, keyless and reliably, and is consistent with the EONIA-via-FRED splice
    # in features/short_rate.py. This removes the last live-ECB dependency.
    "ESTR":  {"source": "fred", "symbol": "ECBESTRVOLWGTTRMDMNRT", "name": "Euro short-term rate", "cadence": "daily"},
}

MACRO = {
    # OECD_CLI DISABLED: FRED's OECD CLI feed for the Euro Area is broken since Nov 2022.
    # Both OECDLOLITOAASTSAM and EA19LOLITONOSTSAM stop at 2022-11. Revisit with PMI.
    # "OECD_CLI": {"source": "fred", "symbol": "EA19LOLITONOSTSAM", "name": "OECD CLI EA19", "cadence": "monthly"},
    "EA_HICP":  {"source": "fred", "symbol": "CP0000EZ19M086NEST", "name": "Euro HICP", "cadence": "monthly"},
}

ALL_TICKERS = {**EQUITY, **FX, **COMMODITIES, **VOL, **RATES, **MACRO}
