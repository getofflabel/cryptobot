"""
step438_funnel.py — WHY the bot stands down, counted, and what each filter costs.

Research only. Reads cached bars, runs tjr_bot.run_day, records reasons.
No orders. Nothing here can reach a broker. Nothing is tuned.

USAGE
    python3 step438_funnel.py                      # the baseline funnel
    python3 step438_funnel.py --counterfactual     # one filter off at a time
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


def walk(cfg=None, news=None, start=START, end=END, data=None):
    cfg = cfg or Config()
    news = news if news is not None else NewsCalendar()
    data = data or {s: tjr_replay.load(s) for s in tjr_replay.SYMBOLS}
    days = tjr_replay.trading_days(data, start, end)
    bot = TjrBot(cfg, news)
    trades, reasons, stages = [], Counter(), []
    for day in days:
        res = bot.run_day(tjr_replay.slice_for(data, day, cfg), day)
        tr = res["trade"]
        if tr is not None:
            trades.append(tr)
        for sym, why in res["stand_down"].items():
            reasons[why] += 1
        stages.append((day, res))
    return bot, trades, reasons, days, data


def stats(bot, trades, days):
    n = len(trades)
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    wr = 100.0 * len(wins) / n if n else 0.0
    aw = sum(t.pnl for t in wins) / len(wins) if wins else 0.0
    al = -sum(t.pnl for t in losses) / len(losses) if losses else 0.0
    months = len({(d.year, d.month) for d in days})
    return dict(trades=n, per_month=n / months if months else 0.0,
                win_rate=wr, rr=(aw / al if al else float("nan")),
                net=sum(t.pnl for t in trades), account=bot.account,
                sessions=len(days))


def line(tag, s):
    return (f"{tag:<44} {s['trades']:>4} trades  {s['per_month']:>5.1f}/mo  "
            f"win {s['win_rate']:>5.1f}%  1:{s['rr']:.3f}  net ${s['net']:>9,.0f}")


def main() -> int:
    print(f"walking {START:%Y-%m-%d} to {END:%Y-%m-%d}\n")
    bot, trades, reasons, days, data = walk()
    s0 = stats(bot, trades, days)
    print(f"sessions {s0['sessions']}   symbol-days {2*s0['sessions']}\n")
    print("WHY IT STOOD DOWN, by symbol-day, ranked")
    for why, c in reasons.most_common():
        print(f"  {c:>4}  {why}")
    print()
    print(line("BASELINE", s0))

    if "--counterfactual" not in sys.argv:
        return 0

    print("\nONE FILTER OFF AT A TIME (an upper bound on what each costs)")

    # news gate entirely removed
    b, t, _, d, _ = walk(news=NewsCalendar(rules=False), data=data)
    print(line("news gate removed", stats(b, t, d)))

    # daily/4-hour agreement veto removed
    c = Config(); c.enforce_daily_4h_agreement = False
    b, t, _, d, _ = walk(cfg=c, data=data)
    print(line("daily/4h agreement veto removed", stats(b, t, d)))

    # both indexes agreement removed
    c = Config(); c.enforce_index_agreement = False
    b, t, _, d, _ = walk(cfg=c, data=data)
    print(line("both-index agreement removed", stats(b, t, d)))

    # the 10:30 cut-off pushed out
    for hhmm in ("11:00", "11:30", "12:00"):
        import datetime as dtm
        h, m = [int(x) for x in hhmm.split(":")]
        c = Config()
        c.instrument = tjr_bot.Instrument(
            **{**tjr_bot.US_INDEX_ETF.__dict__, "cutoff_t": dtm.time(h, m)})
        b, t, _, d, _ = walk(cfg=c, data=data)
        print(line(f"cut-off moved to {hhmm}", stats(b, t, d)))

    # everything off at once
    c = Config()
    c.enforce_daily_4h_agreement = False
    c.enforce_index_agreement = False
    b, t, _, d, _ = walk(cfg=c, news=NewsCalendar(rules=False), data=data)
    print(line("news + both agreements off", stats(b, t, d)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
