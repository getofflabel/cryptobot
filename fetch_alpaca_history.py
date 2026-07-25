"""
fetch_alpaca_history.py — download the S&P history this project has never had.

WHY: every S&P result we own is on DAILY bars, and daily bars are where the
owner's actual trading style dies. Round 362 measured it: stop distances on
daily charts put position size at 0.3 to 1.1 times the account, nowhere near
the 15-20x he trades at. The reason is that chart structure sits far apart on
a daily chart. On a 5-minute chart it sits much closer, which is exactly why
his stops can be tight and his size can be large.

We have never been able to test that, because we had no intraday index data.
Alpaca gives 10+ years of it free. This fetches it once, to parquet, in the
same shape as the repo's other cached files so the existing backtest engine
can read it without changes.

USAGE
    python3 fetch_alpaca_history.py            # SPY+QQQ, 5Min/15Min/1Hour/1Day
    python3 fetch_alpaca_history.py SPY 5Min   # one symbol, one timeframe

NOTES
  - Alpaca returns NOTHING when no `start` is given. Always pass one.
  - Pages come back well under the requested limit (~2,400 of 10,000), so a
    full decade of 5-minute bars is roughly 200 requests. It is slow once and
    then never again.
  - Rate limit is 200 requests/minute on the free plan; the pause below stays
    far under it.
  - `adjustment=split` so old prices are comparable with today's.
"""

from __future__ import annotations

import os
import sys
import time

import pandas as pd

import alpaca

START = "2016-01-01"
PAUSE_S = 0.35                      # ~170 req/min, under the 200 ceiling
SYMBOLS = ["SPY", "QQQ"]
TIMEFRAMES = ["5Min", "15Min", "1Hour", "1Day"]


def fetch_all(symbol: str, timeframe: str, start: str = START) -> pd.DataFrame:
    """Every bar from `start` to now, following the page tokens."""
    import requests
    cli = alpaca.from_env()
    if cli is None:
        raise SystemExit("ALPACA_API_KEY / ALPACA_API_SECRET missing from .env")

    rows, token, pages = [], None, 0
    while True:
        params = {"timeframe": timeframe, "limit": 10000, "start": start,
                  "adjustment": "split"}
        if token:
            params["page_token"] = token
        r = requests.get(f"{alpaca.DATA_URL}/v2/stocks/{symbol}/bars",
                         headers=cli._headers(), params=params, timeout=60)
        if r.status_code == 429:                 # rate limited, wait it out
            time.sleep(5)
            continue
        r.raise_for_status()
        data = r.json()
        bars = data.get("bars") or []
        rows.extend(bars)
        pages += 1
        token = data.get("next_page_token")
        if pages % 20 == 0:
            print(f"    {symbol} {timeframe}: {len(rows):,} bars, {pages} pages")
        if not token:
            break
        time.sleep(PAUSE_S)

    if not rows:
        return pd.DataFrame()

    d = pd.DataFrame(rows).rename(columns={
        "t": "timestamp", "o": "open", "h": "high", "l": "low",
        "c": "close", "v": "volume"})
    d["timestamp"] = pd.to_datetime(d["timestamp"], utc=True)
    keep = ["timestamp", "open", "high", "low", "close", "volume"]
    d = d[[c for c in keep if c in d.columns]].sort_values("timestamp")
    return d.reset_index(drop=True)


def path_for(symbol: str, timeframe: str) -> str:
    tf = {"5Min": "5m", "15Min": "15m", "1Hour": "1h", "1Day": "1d"}[timeframe]
    return f"data_alpaca_{symbol}_{tf}.parquet"


def main() -> int:
    args = sys.argv[1:]
    syms = [args[0]] if args else SYMBOLS
    tfs = [args[1]] if len(args) > 1 else TIMEFRAMES

    for sym in syms:
        for tf in tfs:
            out = path_for(sym, tf)
            if os.path.exists(out):
                have = pd.read_parquet(out)
                print(f"  {out} exists ({len(have):,} bars) — skipping")
                continue
            print(f"  fetching {sym} {tf} from {START} ...")
            t0 = time.time()
            d = fetch_all(sym, tf)
            if d.empty:
                print(f"  {sym} {tf}: NOTHING RETURNED")
                continue
            d.to_parquet(out, index=False)
            span = f"{d['timestamp'].iloc[0].date()} to {d['timestamp'].iloc[-1].date()}"
            print(f"  {out}: {len(d):,} bars, {span}, {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
