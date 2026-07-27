#!/usr/bin/env python3
"""step470_fetch_oanda.py — READ-ONLY candle pull for the Alex Gonzalez engine.

WHAT THIS DOES AND WHAT IT REFUSES TO DO

    It reads candles. That is the entire surface. There is no order path in
    this file, no import of anything that places one, and `oanda_api` is
    reached only through `history`, `frame` and `pricing`. The OANDA practice
    account must end the night with zero orders ever placed, and the way to
    guarantee that is for the code that touches OANDA to have no way of
    sending one.

THE FIVE-YEAR CAP IS WALLACE'S, STATED TONIGHT

    "you dont need 2 decades of data just do the past 5 years", and earlier
    "theres honestly no point of testing it eleven years ago, the world is a
    different place now". OANDA holds twenty-one years. We take five. START
    below is that cap and nothing in this project may reach behind it.

WHY THESE GRANULARITIES

    Alex reads direction off the weekly, the daily and the 4 hour, and takes
    his entry confirmation off the 1 hour. Those are fetched natively rather
    than resampled from the hour, because OANDA pins the daily boundary at
    17:00 New York (`oanda_api.DAILY_ALIGNMENT_HOUR`) which is where the FX
    day actually rolls and where his own charts close it. Resampling the hour
    to midnight would put every daily body close five hours off his.

    M15 is fetched for one job only: deciding which of the stop and the
    target was reached first inside an hour that touched both. Without it the
    honest answer is "assume the loss", and a real distinction is thrown away.

THE SPREAD MEASUREMENT

    Bid and ask are pulled for a recent stretch of hours and the spread is
    taken as the MEDIAN during his own entry window, 01:00-10:30 New York.
    A single live snapshot taken at whatever hour this script happened to run
    would be the wrong number by a wide margin: the spread at 5pm New York is
    several times the spread during London.

Run:  python3 step470_fetch_oanda.py
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oanda_api

REPO = os.path.dirname(os.path.abspath(__file__))

# Wallace's five-year cap. Do not move this backwards.
START = pd.Timestamp("2021-07-01")
END = pd.Timestamp("2026-07-27")

# His pairs, plus gold. XAU_USD is READ ONLY here — gold would trade live as
# XAUT-USDT on BloFin, and OANDA is only ever the chart for it.
INSTRUMENTS = ["GBP_JPY", "GBP_USD", "EUR_USD", "XAU_USD"]

GRANS = {"H1": "1h", "H4": "4h", "D": "1d", "W": "1w", "M15": "15m"}


def cache_name(instrument: str, tf: str) -> str:
    return os.path.join(REPO, f"data_oanda_{instrument}_{tf}.parquet")


def measure_spreads(client, instruments=None, days: int = 120) -> dict:
    """Median spread as a SHARE OF THE PRICE during 01:00-10:30 New York.

    Returned as a plain fraction: 0.00012 is 0.012% of the price. Charged
    later without ever being consulted for a decision.
    """
    out = {}
    start = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=days)
    for name in (instruments or INSTRUMENTS):
        bid = client.frame(name, "H1", start=start, price="B")
        ask = client.frame(name, "H1", start=start, price="A")
        m = bid.merge(ask, on="t", suffixes=("_b", "_a"))
        if not len(m):
            continue
        hh = m["t"].dt.hour + m["t"].dt.minute / 60.0
        win = m[(hh >= 1.0) & (hh <= 10.5)]
        win = win if len(win) else m
        mid = (win["close_b"] + win["close_a"]) / 2.0
        out[name] = float(((win["close_a"] - win["close_b"]) / mid).median())
    return out


def main(argv=None):
    argv = argv or sys.argv[1:]
    client = oanda_api.from_env(practice=True)

    env = client.environment_check()
    print(f"host={env.get('host')}  practice={env.get('practice')}")
    assert "fxpractice" in str(env.get("host", "")), \
        "REFUSING TO RUN: this is not the practice host"

    for name in INSTRUMENTS:
        for gran, tf in GRANS.items():
            path = cache_name(name, tf)
            if os.path.exists(path) and "--refetch" not in argv:
                d = pd.read_parquet(path)
                print(f"  {name:8s} {tf:4s} cached {len(d):>7,} bars "
                      f"{d['t'].min()} -> {d['t'].max()}")
                continue
            d = client.history(name, gran, start=START, end=END, price="M")
            d.to_parquet(path, index=False)
            print(f"  {name:8s} {tf:4s} pulled {len(d):>7,} bars "
                  f"{d['t'].min()} -> {d['t'].max()}")

    sp = measure_spreads(client)
    with open(os.path.join(REPO, "step470_spreads.json"), "w") as f:
        json.dump({"measured_utc": dt.datetime.utcnow().isoformat(),
                   "window": "01:00-10:30 New York, last 120 days",
                   "spread_share_of_price": sp}, f, indent=2)
    print("\nmedian spread, share of price, during his entry window:")
    for k, v in sp.items():
        print(f"  {k:8s} {v * 100:.4f}% of the price")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
