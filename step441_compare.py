"""
step441_compare.py — run tjr_bot on the six dated mornings TJR recorded
himself analysing the S&P, and print what the bot decided.

READ ONLY. Imports tjr_bot, edits nothing, places nothing.

THE DATES (see the report for how each was pinned)
    2023-07-12 Wed  bootcamp Day 47, "Back Testing CPI"
    2023-07-13 Thu  bootcamp Day 48 pt2, "Live Daily Bias Analysis on PPI"
    2023-07-14 Fri  bootcamp Day 49, "$9k Loss SPX Trade Recap"
    2023-07-17 Mon  bootcamp Day 52, "Break Even Trading Recap"
    2023-07-18 Tue  bootcamp Day 53, "$19k Profit GBPJPY Recap"
    2023-07-19 Wed  bootcamp Day 54, "No Trades Today"

THE NEWS GATE
    When this file was written news_calendar.py cached 2026 only, so its own
    answer for any 2023 day was "no release calendar for this date" — which
    stood every day down for a reason that had nothing to do with his method.
    The real July-2023 release dates were therefore supplied by hand below,
    classified by the SAME rule the cached calendar uses (CPI/PPI/jobs/FOMC
    kill the day; the high-impact list halves the size).

    The cache now reaches back to 2016 and would answer these days itself.
    The hand-supplied set is kept exactly as it was, because it now doubles
    as an independent check: the cache, rebuilt from bls.gov's own 2023
    schedule, gives the identical answer — 12 July consumer prices, 13 July
    producer prices — for dates that were typed in here from the schedule
    months earlier and never touched since.
"""

from __future__ import annotations

import datetime as dt
import sys

import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
from tjr_bot import Config, NewsCalendar, TjrBot, to_et_frame  # noqa: E402

REPO = "/Users/wallacechen/cryptobot"
SYMBOLS = ["SPY", "QQQ"]

DAYS = [
    ("2023-07-12", "Wed", "Day47 CPI backtest"),
    ("2023-07-13", "Thu", "Day48pt2 PPI live"),
    ("2023-07-14", "Fri", "Day49 $9k SPX loss"),
    ("2023-07-17", "Mon", "Day52 break-even"),
    ("2023-07-18", "Tue", "Day53 $19k GBPJPY"),
    ("2023-07-19", "Wed", "Day54 no trades"),
]

# The real releases, from the BLS/Census/UMich July 2023 schedule.
BLOCK_2023 = {                       # day-killers, same four names as the cache
    dt.date(2023, 7, 12),            # Consumer Price Index, June, 08:30
    dt.date(2023, 7, 13),            # Producer Price Index, June, 08:30
}
DERISK_2023 = {                      # high-impact but not a killer -> half size
    dt.date(2023, 7, 14),            # Import/Export Price Indexes 08:30,
                                     # Consumer Sentiment prelim 10:00
    dt.date(2023, 7, 20),            # Unemployment Insurance Weekly Claims
}


def load(symbol: str) -> dict:
    return {
        "5m": to_et_frame(pd.read_parquet(f"{REPO}/data_alpaca_{symbol}_5m.parquet")),
        "1m": to_et_frame(pd.read_parquet(f"{REPO}/data_alpaca_{symbol}_1m.parquet")),
    }


def slice_for(data: dict, day: pd.Timestamp, cfg: Config) -> dict:
    lo = day - pd.Timedelta(days=max(cfg.dir_lookback_days, 120) + 10)
    hi = day + pd.Timedelta(days=1)
    out = {}
    for s, f in data.items():
        out[s] = {k: v[(v["t"] >= lo) & (v["t"] < hi)] for k, v in f.items()}
    return out


def word(d: int) -> str:
    return {1: "up", -1: "down", 0: "none"}[int(d)]


def show(tag: str, news: NewsCalendar) -> None:
    data = {s: load(s) for s in SYMBOLS}
    cfg = Config()
    print("=" * 78)
    print(tag)
    print("=" * 78)
    for iso, dow, label in DAYS:
        day = pd.Timestamp(iso)
        bot = TjrBot(cfg=cfg, news=news)
        bot.account = cfg.account_start
        res = bot.run_day(slice_for(data, day, cfg), day)
        ctx = res["context"]["SPY"]
        print(f"\n--- {iso} {dow}  ({label}) ---")
        print(f"  daily={word(ctx.daily_dir)}  4h={word(ctx.h4_dir)}  "
              f"1h={word(ctx.h1_dir)}  BIAS={word(ctx.bias_dir)}  "
              f"profile={ctx.profile}  regime={ctx.regime}  "
              f"derisk={res['derisk']}")
        if ctx.levels:
            byf = {}
            for lv in ctx.levels:
                byf.setdefault(lv.tf, []).append(lv)
            for tf in sorted(byf):
                s = ", ".join(f"{'H' if l.side > 0 else 'L'} {l.price:.2f}"
                              for l in sorted(byf[tf], key=lambda x: -x.price))
                print(f"    levels[{tf}]: {s}")
        if ctx.premarket_swept:
            print(f"    premarket swept: {ctx.premarket_swept}")
        tr = res["trade"]
        if tr:
            print(f"  TRADE {tr.symbol} {'LONG' if tr.direction > 0 else 'SHORT'} "
                  f"entry {tr.entry:.2f} @ {tr.entry_t:%H:%M}  stop {tr.stop:.2f} "
                  f"({tr.stop_basis})  tp1 {tr.tp1:.2f}  tp2 {tr.tp2:.2f}")
            print(f"        outcome {tr.outcome}  pnl ${tr.pnl:,.0f}  "
                  f"swept {tr.level_tf} {tr.level_price:.2f}")
        else:
            for s in SYMBOLS:
                if s in res["stand_down"]:
                    print(f"  NO TRADE [{s}]: {res['stand_down'][s]}")
        for n in res["notes"].get("SPY", [])[:14]:
            print(f"      . {n}")


if __name__ == "__main__":
    show("RUN A — real July-2023 news gate (CPI 7/12, PPI 7/13 block)",
         NewsCalendar(extra_block=BLOCK_2023, extra_derisk=DERISK_2023,
                      rules=False))
    show("RUN B — news gate OFF, to see what the setup logic alone would do",
         NewsCalendar(rules=False))
