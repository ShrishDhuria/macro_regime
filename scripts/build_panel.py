"""Phase 1 orchestrator - fetch all configured series, align, save panel."""
from __future__ import annotations
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.tickers import ALL_TICKERS
from data.ingestion.yfinance_fetcher import YFinanceFetcher
from data.ingestion.fred_fetcher import FREDFetcher
from data.ingestion.ecb_fetcher import ECBFetcher
from data.alignment import align_to_weekly
from data.storage import save_raw, save_panel

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-7s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("build_panel")

FETCHERS = {"yfinance": YFinanceFetcher(), "fred": FREDFetcher(), "ecb": ECBFetcher()}


def build_panel(start: str = "2005-01-01", end: str | None = None):
    raw, failed = {}, []
    for name, cfg in ALL_TICKERS.items():
        fetcher = FETCHERS[cfg["source"]]
        try:
            log.info(f"Fetching {name:10s} <- {cfg['source']:8s} {cfg['symbol']}")
            s = fetcher.fetch(cfg["symbol"], start=start, end=end)
            save_raw(name, s)
            raw[name] = s
            log.info(f"           OK   {len(s):5d} obs  {s.index.min().date()} -> {s.index.max().date()}")
        except Exception as e:
            tag = "EXPECTED" if cfg.get("expect_failure") else "FAILED  "
            log.warning(f"           {tag} {name}: {type(e).__name__}: {e}")
            failed.append(name)

    if not raw:
        log.error("No series fetched. Aborting.")
        return None

    log.info(f"Aligning {len(raw)} series to weekly Friday grid...")
    panel = align_to_weekly(raw, start=start, end=end)
    save_panel(panel)
    log.info(f"Master panel saved: shape={panel.shape}")
    if failed:
        log.warning(f"Failed/skipped: {failed}")
    return panel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2005-01-01")
    ap.add_argument("--end", default=None)
    args = ap.parse_args()
    panel = build_panel(start=args.start, end=args.end)
    if panel is None:
        sys.exit(1)
    print("\n=== head ===");    print(panel.head())
    print("\n=== tail ===");    print(panel.tail())
    print("\n=== missing ==="); print(panel.isna().sum().sort_values(ascending=False))


if __name__ == "__main__":
    main()
