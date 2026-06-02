# Data Sources & Provenance

This document is the audit trail for every series in the platform. The guiding
principle is source diversification: where a series is available from more than
one provider, a fallback is documented so an API outage does not break the build.

## Market data (yfinance)

| Series | Yahoo symbol | Notes |
|---|---|---|
| SX5E   | `^STOXX50E` | Euro Stoxx 50 index level |
| CAC    | `^FCHI`     | CAC 40 |
| DAX    | `^GDAXI`    | DAX 40 |
| BANKS  | `EXV1.DE`   | iShares STOXX 600 Banks ETF, used as SX7E proxy |
| EURUSD | `EURUSD=X`  | Spot EUR/USD |
| BRENT  | `BZ=F`      | Brent crude front-month future |
| GOLD   | `GC=F`      | Gold front-month future |
| VIX    | `^VIX`      | CBOE VIX |
| V2X    | `^V2TX`     | **Delisted on Yahoo.** Replaced throughout by SX5E rolling realized vol. |

## Rates and macro (FRED)

FRED public CSV endpoint: `https://fred.stlouisfed.org/graph/fredgraph.csv?id={TICKER}`
No API key required. We hit this directly rather than via `pandas-datareader`,
which imports the removed `distutils` module and fails on Python 3.12+.

| Series | FRED ticker | Cadence | Notes |
|---|---|---|---|
| DE10Y   | `IRLTLT01DEM156N` | monthly | Germany 10Y benchmark yield |
| FR10Y   | `IRLTLT01FRM156N` | monthly | France 10Y; can run ~90d stale (OECD update cadence) |
| IT10Y   | `IRLTLT01ITM156N` | monthly | Italy 10Y; can run ~90d stale |
| EA_HICP | `CP0000EZ19M086NEST` | monthly | Euro-area HICP; lagged 30d for publication delay |
| EONIA   | `EONIARATE` | daily | **Discontinued Jan 2022.** Used only for pre-Oct-2019 history in the short-rate splice. |

### Disabled: OECD CLI
FRED's OECD Composite Leading Indicator feed for the Euro Area
(`EA19LOLITONOSTSAM` / `OECDLOLITOAASTSAM`) stops updating in November 2022.
Commented out in `config/tickers.py`. Candidate replacement: a PMI series.
The freshness check (`features/freshness.py`) is what surfaced this.

## Rates (ECB Data Portal)

ECB Data Portal (formerly SDW) REST API:
`https://data-api.ecb.europa.eu/service/data/{DATAFLOW}/{SERIES_KEY}?format=csvdata`

| Series | Series key | Notes |
|---|---|---|
| ESTR | `EST.B.EU000A2X2A25.WT` | Euro short-term rate, volume-weighted. Begins 2019-10-01. |

**Reliability note:** the ECB endpoint is occasionally slow or times out. FRED
mirror fallback for ESTR: `ECBESTRVOLWGTTRMDMNRT`.

## Short-rate splice (EONIA -> ESTR)

ESTR began 2 October 2019. Under ECB Recommendation 2019/C 295/02, EONIA was
from that date redefined as ESTR + 8.5bp (fixed spread). To build a continuous
overnight-rate series back to 2005, `features/short_rate.py` uses:

- ESTR directly from 2019-10-02 onwards
- (EONIA - 8.5bp) before that date

The result feeds the `TERM_DE_UNIFIED` feature (DE10Y minus unified short rate),
one of the five HMM inputs.

## Data-ops principles applied

1. **HTTP 200 != fresh data.** The freshness check inspects each series' last
   observation date, not just whether the fetch succeeded.
2. **Diversify sources.** FRED mirrors are documented for ECB series.
3. **Treat fetch failures as diagnostics.** A failed or stale series is a signal
   about the upstream feed, not just an error to suppress.
4. **Enforce publication lags.** Macro series are shifted by their release delay
   before entering any model, preventing lookahead bias.
