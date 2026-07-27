"""
step455_fetch_dot.py — refill DOT/USD 1-minute bars back to where its
5-minute record already starts.

WHY
    DOT's 1-minute backfill died on a rate limit and only reached
    2026-03-01, while every other pair on the board reaches 2021. Comparing a
    four-month pair against a five-year one is not a comparison. Its
    5-minute record starts 2023-08-18, and Alpaca returns no 1-minute DOT
    bars before 2024, so 2023-08-18 is the honest ask.

WHAT IT WRITES
    step455_DOTUSD_1m.parquet next to the caches. It does NOT overwrite
    data_alpaca_DOTUSD_1m.parquet — this round writes step455_* files only.
    step455_measure.py picks the longer of the two automatically.

RESEARCH ONLY. Read-only market data. No orders, no account endpoints.
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.abspath(__file__))

import alpaca
import tjr_crypto as tc

START = "2023-08-18"


def main() -> int:
    cli = alpaca.from_env()
    if cli is None:
        print("ALPACA keys are not in .env")
        return 1
    t0 = time.time()
    rows = (cli.crypto_bars("DOT/USD", "1Min", start=START,
                            limit=10000, max_pages=600).get("DOT/USD") or [])
    d = tc.to_utc_frame(rows)
    out = f"{REPO}/step455_DOTUSD_1m.parquet"
    d.to_parquet(out)
    print(f"DOT/USD 1m  {len(d):,} bars  "
          f"{d['t'].min() if len(d) else '-'} .. {d['t'].max() if len(d) else '-'}"
          f"  ({time.time()-t0:.0f}s) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
