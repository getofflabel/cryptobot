"""
step450_replay_by_year.py — how often does this method actually trade the
S&P, year by year, 2016 to today.

WHY
    The only window we could see was January to July 2026: 22 trades, 0.76 a
    week, 55% won. That is seven months. It was seven months because the
    release calendar only held 2026 and an uncovered date stood the bot down,
    so 2016-2025 came back with zero trades and a wall of "no release
    calendar for this date". The calendar now reaches 2016 (news_calendar.py,
    checked against the tape year by year in
    step450_news_calendar_history.py), and the 1-minute bar file was
    backfilled to match, so the question can finally be asked properly:

        is the trade rate stable across years, or is 2026 unusual?

HOW
    `tjr_replay.run` walks every session bar by bar through `tjr_bot`, which
    is untouched. Causality is the engine's, not this file's: higher
    timeframes are truncated to their last COMPLETED candle and the bot never
    sees a bar it has not reached. Nothing is tuned here — same Config every
    year, no per-year anything.

    Each year is run with a FRESH bot and a fresh account, so the years are
    comparable to each other. A bot carried across all eleven years would
    compound, and a good 2022 would then flatter 2023's dollar figures.

    Stand-downs are counted in two buckets that must never be added
    together: the method declining a day, and the calendar having no data.
    The second is a broken file, and the whole point of this round is that it
    stops being invisible.

USAGE
    python3 step450_replay_by_year.py
    python3 step450_replay_by_year.py --years=2016-2026 --csv

RESEARCH ONLY. Reads parquet off disk, walks it through the bot, writes a
CSV. No network, no broker, no orders.
"""

from __future__ import annotations

import os
import sys
import time

import pandas as pd

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

import news_calendar as nc
import tjr_bot
import tjr_replay
from tjr_bot import Config, NewsCalendar, TjrBot


def _cache_data():
    """Load SPY and QQQ once instead of once per year."""
    cached = {s: tjr_replay.load(s) for s in tjr_replay.SYMBOLS}
    tjr_replay.load = lambda symbol: cached[symbol]
    return cached


def run_year(year: int, cfg: Config):
    start = pd.Timestamp(f"{year}-01-01")
    end = pd.Timestamp(f"{year}-12-31")
    bot, trades, stand_downs, days = tjr_replay.run(
        start, end, cfg=cfg, news=NewsCalendar(), verbose=False)
    return bot, trades, stand_downs, days


def summarise_year(year, bot, trades, stand_downs, days, cfg) -> dict:
    n = len(trades)
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    weeks = sorted({(d - pd.Timedelta(days=d.weekday())).normalize()
                    for d in days})
    aw = sum(t.pnl for t in wins) / len(wins) if wins else 0.0
    al = -sum(t.pnl for t in losses) / len(losses) if losses else 0.0

    # the two stand-down buckets, kept apart on purpose
    gap = sum(1 for s in stand_downs if "no release calendar" in s["why"])
    news = sum(1 for s in stand_downs
               if "news gate" in s["why"] and "no release calendar" not in s["why"])
    return {
        "year": year,
        "sessions": len(days),
        "trading_weeks": len(weeks),
        "trades": n,
        "trades_per_week": round(n / len(weeks), 2) if weeks else 0.0,
        "trades_per_month": round(n / 12.0, 1),
        "share_of_sessions_traded_pct": round(100.0 * n / len(days), 1) if days else 0.0,
        "win_rate_pct": round(100.0 * len(wins) / n, 1) if n else 0.0,
        "avg_win_dollars": round(aw),
        "avg_loss_dollars": round(al),
        "avg_win_over_avg_loss": round(aw / al, 3) if al else float("nan"),
        "mean_result_x_risked": round(sum(t.r_multiple for t in trades) / n, 3) if n else 0.0,
        "net_dollars": round(sum(t.pnl for t in trades)),
        "account_end_dollars": round(bot.account),
        "return_on_the_account_pct": round(
            100.0 * (bot.account - cfg.account_start) / cfg.account_start, 2),
        "stood_down_on_a_release": news,
        "stood_down_because_no_calendar": gap,
        "stood_down_other": len(stand_downs) - news - gap,
    }


def main() -> int:
    years = range(2016, 2027)
    csv = None
    for a in sys.argv[1:]:
        if a.startswith("--years="):
            lo, _, hi = a.split("=", 1)[1].partition("-")
            years = range(int(lo), int(hi or lo) + 1)
        if a.startswith("--csv"):
            csv = (a.split("=", 1)[1] if "=" in a
                   else os.path.join(REPO, "step450_trade_rate_by_year.csv"))

    lo, hi = nc.coverage()
    print(f"release calendar covers {lo} .. {hi}")
    d5 = pd.read_parquet(f"{REPO}/data_alpaca_SPY_5m.parquet")
    d1 = pd.read_parquet(f"{REPO}/data_alpaca_SPY_1m.parquet")
    print(f"SPY 5-minute bars {d5['timestamp'].min().date()} .. "
          f"{d5['timestamp'].max().date()}   ({len(d5):,})")
    print(f"SPY 1-minute bars {d1['timestamp'].min().date()} .. "
          f"{d1['timestamp'].max().date()}   ({len(d1):,})")
    print(f"symbols {', '.join(tjr_replay.SYMBOLS)}\n")

    _cache_data()
    cfg = Config()
    rows, all_trades = [], []
    hdr = (f"{'year':<6}{'sessions':>9}{'trades':>8}{'per wk':>8}{'per mo':>8}"
           f"{'won':>7}{'win/loss':>10}{'mean x risked':>15}{'net $':>10}"
           f"{'no cal':>8}")
    print(hdr)
    print("-" * len(hdr))
    for year in years:
        t0 = time.time()
        bot, trades, sd, days = run_year(year, cfg)
        if not days:
            print(f"{year:<6}  no sessions in the bar data")
            continue
        r = summarise_year(year, bot, trades, sd, days, cfg)
        rows.append(r)
        all_trades += [(year, t) for t in trades]
        print(f"{year:<6}{r['sessions']:>9}{r['trades']:>8}"
              f"{r['trades_per_week']:>8.2f}{r['trades_per_month']:>8.1f}"
              f"{r['win_rate_pct']:>6.1f}%"
              f"{r['avg_win_over_avg_loss']:>10.3f}"
              f"{r['mean_result_x_risked']:>+15.3f}"
              f"{r['net_dollars']:>10,}{r['stood_down_because_no_calendar']:>8}"
              f"   ({time.time()-t0:.0f}s)")

    if not rows:
        return 1
    d = pd.DataFrame(rows)
    n = int(d["trades"].sum())
    w = int(d["trading_weeks"].sum())
    print("-" * len(hdr))
    print(f"{'all':<6}{int(d['sessions'].sum()):>9}{n:>8}{n/w:>8.2f}"
          f"{n/(len(d)*12):>8.1f}")

    won = sum(1 for _, t in all_trades if t.pnl > 0)
    print(f"\nacross every year: {n} trades in {w} trading weeks, "
          f"{n/w:.2f} a week, {100*won/n:.1f}% won")
    print(f"trades a week, year by year: "
          f"low {d['trades_per_week'].min():.2f}, "
          f"high {d['trades_per_week'].max():.2f}, "
          f"median {d['trades_per_week'].median():.2f}")
    print(f"win rate, year by year:     "
          f"low {d['win_rate_pct'].min():.1f}%, "
          f"high {d['win_rate_pct'].max():.1f}%, "
          f"median {d['win_rate_pct'].median():.1f}%")
    gaps = int(d["stood_down_because_no_calendar"].sum())
    print(f"sessions lost to a missing calendar: {gaps}"
          + ("  <-- FIX THE CALENDAR" if gaps else "  (none: the calendar covers "
             "every session walked)"))

    if csv:
        d.to_csv(csv, index=False)
        print(f"\nwritten to {csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
