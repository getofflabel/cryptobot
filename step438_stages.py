"""
step438_stages.py — how far each symbol-day gets through his four steps,
and the clock at each step. Research only. No orders. Nothing is tuned.
"""

from __future__ import annotations

import sys
from collections import Counter

import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
import tjr_bot
import tjr_replay
from tjr_bot import Config, NewsCalendar, TjrBot

START = pd.Timestamp("2026-01-02")
END = pd.Timestamp("2026-07-24")

def main() -> int:
    data = {s: tjr_replay.load(s) for s in tjr_replay.SYMBOLS}
    days = tjr_replay.trading_days(data, START, END)
    cfg, news = Config(), NewsCalendar()
    bot = TjrBot(cfg, news)

    ctxstats = Counter()
    pool_sizes = []

    for day in days:
        res = bot.run_day(tjr_replay.slice_for(data, day, cfg), day)
        for sym in tjr_replay.SYMBOLS:
            ctx = res["context"].get(sym)
            if ctx is None:
                continue
            if ctx.stand_down:
                ctxstats[ctx.stand_down.split(":")[0]] += 1
                continue
            ctxstats["reached the open"] += 1
            pool_sizes.append((len(ctx.levels), len(ctx.cont_levels), ctx.profile))

    print(f"sessions {len(days)}   symbol-days {2*len(days)}\n")
    print("BEFORE THE OPEN")
    for k, v in ctxstats.most_common():
        print(f"  {v:>4}  {k}")
    print()
    n = len(pool_sizes)
    print(f"of the {n} symbol-days that reached the open:")
    print(f"  marked-level pool size: mean {sum(p[0] for p in pool_sizes)/n:.1f}, "
          f"zero on {sum(1 for p in pool_sizes if p[0]==0)}")
    print(f"  15-minute pool size:    mean {sum(p[1] for p in pool_sizes)/n:.1f}, "
          f"non-zero on {sum(1 for p in pool_sizes if p[1]>0)}")
    prof = Counter(p[2] for p in pool_sizes)
    for k, v in prof.most_common():
        print(f"  session profile {k:<24} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
