"""
step438_premarket.py — two measurements, no changes.

1) how many symbol-days lose a marked level to a sweep BEFORE 08:30 (which the
   build silently drops with no carve-out at all), versus between 08:30 and
   09:30 (the only window the build's carve-out can see)
2) how many 1-minute triggers land inside 09:30-09:50 and are refused

Research only. No orders.
"""

from __future__ import annotations

import sys
from collections import Counter

import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
import tjr_bot
import tjr_replay
from tjr_bot import (Config, NewsCalendar, US_INDEX_ETF, _unswept, daily_bars,
                     completed_before, resample_tf, session_levels,
                     swing_levels, session_start, TrendTracker, Bar)

START = pd.Timestamp("2026-01-02")
END = pd.Timestamp("2026-07-24")


def main() -> int:
    cfg, inst, news = Config(), US_INDEX_ETF, NewsCalendar()
    data = {s: tjr_replay.load(s) for s in tjr_replay.SYMBOLS}
    days = tjr_replay.trading_days(data, START, END)

    c = Counter()
    dirs = Counter()
    for day in days:
        if news.blocks(day.date()):
            continue
        sl = tjr_replay.slice_for(data, day, cfg)
        for sym in tjr_replay.SYMBOLS:
            d5 = sl[sym]["5m"]
            open_t = session_start(day, inst)
            hist = d5[d5["t"] < open_t]
            if len(hist) == 0:
                continue
            d_lev = hist[hist["t"] >= day - pd.Timedelta(days=cfg.level_lookback_days)]
            d_dir = hist[hist["t"] >= day - pd.Timedelta(days=cfg.dir_lookback_days)]

            levels = list(session_levels(d_lev, day, inst))
            for m in inst.level_minutes:
                levels += swing_levels(d_lev, m, open_t, f"{m//60}h")

            pre_start = day + pd.Timedelta(hours=4)     # the funds start trading
            at_pre = _unswept(levels, d_lev, pre_start)
            at_830 = _unswept(levels, d_lev, open_t - pd.Timedelta(hours=1))
            at_930 = _unswept(levels, d_lev, open_t)
            c["symbol-days"] += 1
            if len(at_830) < len(at_pre):
                c["a level was taken 04:00-08:30 (build sees NOTHING)"] += 1
            if len(at_930) < len(at_830):
                c["a level was taken 08:30-09:30 (the build's carve-out)"] += 1
            if len(at_930) < len(at_pre):
                c["a level was taken anywhere in pre-market"] += 1

            # the three directions, for the 2-of-3 question
            tt = TrendTracker()
            dl = completed_before(daily_bars(d_dir, inst), open_t)
            for r in dl.itertuples():
                tt.update(Bar(r.t, r.open, r.high, r.low, r.close))
            t4 = TrendTracker()
            for r in completed_before(resample_tf(d_dir, 240), open_t).itertuples():
                t4.update(Bar(r.t, r.open, r.high, r.low, r.close))
            t1 = TrendTracker()
            for r in completed_before(resample_tf(d_dir, 60), open_t).itertuples():
                t1.update(Bar(r.t, r.open, r.high, r.low, r.close))
            d, f, h = tt.state, t4.state, t1.state
            if d == 0:
                dirs["the daily has no direction yet"] += 1
            elif d == f and d == h:
                dirs["daily, 4-hour and 1-hour all agree"] += 1
            elif d == f:
                dirs["daily+4h agree, the 1-hour is against them"] += 1
            elif d == h:
                dirs["daily+1h agree, the 4-hour is against them"] += 1
            else:
                dirs["the daily stands alone against both"] += 1

    print("PRE-MARKET SWEEPS OF A MARKED LEVEL")
    for k, v in c.most_common():
        print(f"  {v:>4}  {k}")
    print("\nTHE THREE DIRECTIONS, on symbol-days the news gate lets through")
    for k, v in dirs.most_common():
        print(f"  {v:>4}  {k}")
    tot = sum(dirs.values())
    live_now = dirs["daily, 4-hour and 1-hour all agree"] + \
        dirs["daily+4h agree, the 1-hour is against them"]
    live_23 = live_now + dirs["daily+1h agree, the 4-hour is against them"]
    print(f"\n  the build's rule (daily==4h) leaves {live_now}/{tot} live")
    print(f"  daily + at least one of the two leaves  {live_23}/{tot} live")
    return 0


if __name__ == "__main__":
    sys.exit(main())
