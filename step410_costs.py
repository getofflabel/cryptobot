"""
step410_costs.py - ROUND 410, PART 0
WHAT DOES IT ACTUALLY COST TO TRADE EACH OF THESE NAMES?

Research only. No orders of any kind. The Alpaca account must still show
zero orders after this file runs; it only reads market data.

WHY THIS FILE EXISTS
  The brief says to measure the cost per name from the gap between the
  buy price and the sell price, not to assume a number. Alpaca charges no
  commission on US equities, so the whole cost of a round trip is the
  spread you cross plus whatever the market moves against a marketable
  order. A market order to BUY lifts the ask; a market order to SELL hits
  the bid. Do both and you have paid, at minimum, one full quoted spread.

  So: pull the real national best bid and offer for each name, at many
  random regular-hours moments spread across the whole history, and take
  the median. That number, expressed as a percentage of price, IS the
  round-trip cost of a market-in / market-out trade.

  A snapshot taken while the market is shut is worthless - the quotes go
  one-sided and crossed (measured 2026-07-25 after the close: NVDA showed
  an ask of 0.00). Every sample here is taken inside regular hours.

WHAT COMES OUT
  step410_table_costs.csv - per name, the median and the 75th-percentile
  quoted spread as a percentage of price, and the round-trip cost that
  implies. Every later step410 file reads its costs from this table.

UNITS
  Every number here is a PRICE move - how far the price has to travel -
  never a change in the value of a position. At ten times leverage a
  0.02% price cost is a 0.2% dent in the money put up.
"""

from __future__ import annotations

import sys
import time
import datetime as dt

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, "/Users/wallacechen/cryptobot")
import alpaca

REPO = "/Users/wallacechen/cryptobot"
NAMES = ["NVDA", "AMD", "AVGO", "MU", "MSFT", "GOOGL", "META", "AMZN",
         "TSLA", "SMH", "SPY", "QQQ"]

# random regular-hours minutes, spread across the sample, one per year-ish
SAMPLE_WINDOWS = [
    ("2016-06-15", 15, 0), ("2017-03-08", 18, 30), ("2018-09-12", 14, 45),
    ("2019-05-15", 16, 30), ("2020-10-14", 19, 0),  ("2021-04-14", 15, 30),
    ("2022-08-10", 17, 0),  ("2023-02-15", 18, 0),  ("2023-11-15", 14, 40),
    ("2024-06-12", 16, 15), ("2025-01-15", 19, 30), ("2025-09-10", 15, 45),
    ("2026-02-11", 17, 15), ("2026-07-22", 16, 0),
]
WINDOW_MIN = 3          # minutes of quotes per sample


def quotes_window(cli, sym, start_utc, minutes=WINDOW_MIN, limit=10000):
    end = start_utc + dt.timedelta(minutes=minutes)
    for attempt in range(3):
        r = requests.get(
            f"{alpaca.DATA_URL}/v2/stocks/{sym}/quotes",
            headers=cli._headers(),
            params={"start": start_utc.isoformat().replace("+00:00", "Z"),
                    "end": end.isoformat().replace("+00:00", "Z"),
                    "limit": limit},
            timeout=60)
        if r.status_code == 429:
            time.sleep(4)
            continue
        if r.status_code != 200:
            return []
        return r.json().get("quotes", []) or []
    return []


def main():
    cli = alpaca.from_env()
    if cli is None:
        raise SystemExit("ALPACA_API_KEY / ALPACA_API_SECRET missing from .env")

    rows = []
    for sym in NAMES:
        per_window = []
        allsp = []
        for (day, hh, mm) in SAMPLE_WINDOWS:
            t0 = dt.datetime.fromisoformat(day).replace(
                hour=hh, minute=mm, tzinfo=dt.timezone.utc)
            qs = quotes_window(cli, sym, t0)
            sp = []
            for x in qs:
                bp, ap = x.get("bp", 0.0), x.get("ap", 0.0)
                if bp > 0 and ap > 0 and ap >= bp:
                    mid = 0.5 * (ap + bp)
                    s = (ap - bp) / mid * 100.0
                    if s < 5.0:                 # drop obvious junk prints
                        sp.append(s)
            if len(sp) >= 50:
                per_window.append((day, float(np.median(sp)), len(sp)))
                allsp.extend(sp)
            time.sleep(0.25)

        if not allsp:
            print(f"{sym:6s}  no quote data returned")
            continue
        a = np.array(allsp)
        med = float(np.median(a))
        p75 = float(np.percentile(a, 75))
        rows.append(dict(symbol=sym, n_quotes=len(a), n_windows=len(per_window),
                         med_quoted_spread_pct=med, p75_quoted_spread_pct=p75,
                         roundtrip_cost_pct=med, roundtrip_cost_p75_pct=p75))
        print(f"{sym:6s}  windows {len(per_window):2d}  quotes {len(a):>7,}  "
              f"median quoted spread {med:.4f}% of price  "
              f"-> round trip {med:.4f}% of price  (p75 {p75:.4f}%)")
        for (day, m, n) in per_window:
            print(f"           {day}  median {m:.4f}%  n={n:,}")

    if rows:
        out = pd.DataFrame(rows)
        out.to_csv(f"{REPO}/step410_table_costs.csv", index=False)
        print(f"\nwrote step410_table_costs.csv ({len(out)} names)")
        print("\nA market order pays roughly half the quoted spread against the")
        print("midpoint on each side, so a full round trip pays about one whole")
        print("quoted spread. That is the round-trip cost column. Alpaca adds no")
        print("commission on US equities. Every profit number in this round is")
        print("compared against 5 times this figure.")


if __name__ == "__main__":
    sys.exit(main())
