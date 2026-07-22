"""
collector.py — records the market's POSITIONING panel, hourly, forever.

Run:  python collector.py     (one snapshot, then exit — designed for cron)

WHY THIS EXISTS
High-level traders don't trade candles; they trade POSITIONING — open
interest building against a level, crowded funding, a lopsided book.
Public history for that data is shallow (Bybit serves ~11 months of OI,
zero orderbook history). So we record our own: every hour, one snapshot of
everything a positioning trader looks at. In three months this dataset can
answer questions no free API can. The best time to start was a year ago;
the second best time is this cron tick.

Each snapshot (one JSON row in Supabase):
  price/mark, funding rate, next-funding countdown,
  open interest (Bybit, deepest public source),
  top-of-book: bid/ask sizes and the imbalance ratio,
  depth: size within 0.5% of mid, both sides (thin book = fragile market)
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import requests

SB_URL = os.environ["CRYPTOBOT_SUPABASE_URL"]
SB_KEY = os.environ["CRYPTOBOT_SUPABASE_ANON"]
SB_SECRET = os.environ["CRYPTOBOT_STATE_SECRET"]

BLOFIN = "https://openapi.blofin.com/api/v1"
BYBIT = "https://api.bybit.com/v5"


def get(url, params):
    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()
    return r.json()


def main():
    snap = {"ts": datetime.now(timezone.utc).isoformat(), "symbol": "BTC-USDT"}

    # price + funding (BloFin, our venue)
    t = get(f"{BLOFIN}/market/tickers", {"instId": "BTC-USDT"})["data"][0]
    snap["last"] = float(t["last"])
    snap["bid"], snap["ask"] = float(t["bidPrice"]), float(t["askPrice"])
    f = get(f"{BLOFIN}/market/funding-rate", {"instId": "BTC-USDT"})["data"][0]
    snap["funding_bps"] = float(f["fundingRate"]) * 10_000

    # open interest — Bybit first (deepest data, works from residential
    # IPs), then OKX, then Deribit: GitHub's US runners get geo-blocked by
    # some venues, so the collector carries fallbacks. Which source served
    # each snapshot is recorded so the series can be split later.
    for name, fn in [
        ("bybit", lambda: float(get(f"{BYBIT}/market/open-interest",
                                    {"category": "linear", "symbol": "BTCUSDT",
                                     "intervalTime": "1h", "limit": 1})
                                ["result"]["list"][0]["openInterest"])),
        ("okx", lambda: float(get("https://www.okx.com/api/v5/public/open-interest",
                                  {"instId": "BTC-USDT-SWAP"})
                              ["data"][0]["oiCcy"])),
        ("deribit", lambda: float(get("https://www.deribit.com/api/v2/public/ticker",
                                      {"instrument_name": "BTC-PERPETUAL"})
                                  ["result"]["open_interest"]) / snap["last"]),
    ]:
        try:
            snap["oi_btc"] = fn()
            snap["oi_source"] = name
            break
        except Exception:
            continue

    # order book: top-of-book imbalance + depth within 0.5% of mid
    book = get(f"{BLOFIN}/market/books",
               {"instId": "BTC-USDT", "size": "100"})["data"][0]
    bids = [(float(p), float(q)) for p, q, *_ in book["bids"]]
    asks = [(float(p), float(q)) for p, q, *_ in book["asks"]]
    mid = (bids[0][0] + asks[0][0]) / 2
    snap["bid1_qty"], snap["ask1_qty"] = bids[0][1], asks[0][1]
    lo, hi = mid * 0.995, mid * 1.005
    bid_depth = sum(q for p, q in bids if p >= lo)
    ask_depth = sum(q for p, q in asks if p <= hi)
    snap["bid_depth_05"], snap["ask_depth_05"] = bid_depth, ask_depth
    snap["book_imbalance"] = round(
        (bid_depth - ask_depth) / max(bid_depth + ask_depth, 1e-9), 4)

    r = requests.post(f"{SB_URL}/rest/v1/rpc/cryptobot_record_snap",
                      headers={"apikey": SB_KEY,
                               "Authorization": f"Bearer {SB_KEY}",
                               "Content-Type": "application/json"},
                      json={"secret": SB_SECRET, "s": snap}, timeout=25)
    r.raise_for_status()
    print(f"snapshot recorded: last={snap['last']:,.1f} "
          f"funding={snap['funding_bps']:+.2f}bps "
          f"OI={snap.get('oi_btc', 0):,.0f} BTC "
          f"imbalance={snap['book_imbalance']:+.3f}")


if __name__ == "__main__":
    main()
