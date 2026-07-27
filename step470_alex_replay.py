#!/usr/bin/env python3
"""step470_alex_replay.py — the measurement. Replay only, no venue, no order.

WHAT IS REPORTED AND WHY IT IS REPORTED THAT WAY

    Per instrument, per window, and per session (London against New York),
    because he trades two sessions and the whole question of whether the
    engine has read him correctly is answered by the TRADE COUNT before it is
    answered by the money.

    LEVERAGE IS REPORTED, never "risk %". Leverage is what Wallace can see on
    a broker screen. The share of the account a trade may cost is the input;
    leverage is what falls out of it and the structural stop.

    EVERY PERCENTAGE SAYS WHICH ONE IT IS. A move in the PRICE and a change in
    what the position is worth differ by the leverage — twenty-fold at 20x —
    and a bare number that could be either is worse than no number.

    Each instrument runs on its OWN $100,000. Four instruments is four
    accounts, not one.

WINDOWS

    5 years is the cap Wallace set tonight and it is the deepest thing here.
    The 12-month and July-2026 windows are the ones the decision rests on.

Run:  python3 step470_alex_replay.py
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alex_engine as ae

REPO = os.path.dirname(os.path.abspath(__file__))
MODE = "dumb"

# A CLOSED TRADE IS A CLOSED TRADE. His Friday exit (the spine, 2026-06-14) is
# a real close at a real loss and it is counted with the rest — leaving it out
# would drop only losers and flatter every number on the page.
CLOSED = ["stop", "target", "friday"]

WINDOWS = [
    ("5 years", "2021-07-05", "2026-07-26"),
    ("12 months", "2025-07-27", "2026-07-26"),
    ("July 2026", "2026-07-01", "2026-07-26"),
]


def stats(f: pd.DataFrame, weeks: float) -> dict:
    """One row of the report. `f` is already one instrument, one window."""
    done = f[f["outcome"].isin(CLOSED)]
    n = len(done)
    wins = done[done["pnl"] > 0]
    lev = done["leverage"]
    return {
        "trades": n,
        "per_week": n / weeks if weeks else 0.0,
        "win_rate": 100.0 * len(wins) / n if n else 0.0,
        "mean_r": done["r"].mean() if n else 0.0,
        "net": done["pnl"].sum(),
        "cost": done["cost"].sum(),
        "lev_med": lev.median() if n else 0.0,
        "lev_lo": lev.min() if n else 0.0,
        "lev_hi": lev.max() if n else 0.0,
        "stop_lo": done["stop_move_in_price_pct"].min() if n else 0.0,
        "stop_hi": done["stop_move_in_price_pct"].max() if n else 0.0,
        "hold_med_h": done["hours_held"].median() if n else 0.0,
        "hold_max_h": done["hours_held"].max() if n else 0.0,
        "open": int((f["outcome"] == "open").sum()),
        "held_out": int((f["outcome"] == "held_out").sum()),
        "ties": int(done["same_bar_resolved"].sum()),
    }


def line(name: str, s: dict) -> str:
    return (f"  {name:<22s} {s['trades']:>4d} {s['per_week']:>6.2f} "
            f"{s['win_rate']:>7.1f}% {s['mean_r']:>7.2f} "
            f"${s['net']:>+11,.0f}  {s['lev_med']:>6.1f}x "
            f"({s['lev_lo']:.1f}-{s['lev_hi']:.1f}x)")


HEAD = ("  {:<22s} {:>4s} {:>6s} {:>8s} {:>7s} {:>12s}  {:>6s} {}".format(
    "", "n", "/week", "won", "mean R", "net $", "lev", "(band)"))


def weeks_between(a, b) -> float:
    return max(1.0, (pd.Timestamp(b) - pd.Timestamp(a)).days / 7.0)


def weekly_profitability(f: pd.DataFrame) -> tuple:
    """His own sanity check: he claims roughly 60-70% of WEEKS profitable.

    A week with no trade is not counted either way — he takes one to two
    trades a week and a flat week is not a losing one.
    """
    done = f[f["outcome"].isin(CLOSED)].copy()
    if not len(done):
        return 0, 0.0
    done["wk"] = pd.to_datetime(done["exit_t"]).dt.to_period("W")
    by = done.groupby("wk")["pnl"].sum()
    return len(by), 100.0 * float((by > 0).mean())


def main(argv=None):
    argv = argv or sys.argv[1:]
    cache: dict = {}
    global MODE
    MODE = "topdown" if "--topdown" in argv else "dumb"
    out_rows = []

    print("=" * 92)
    print(f"ALEX GONZALEZ ENGINE — replay, mode={MODE!r}. "
          f"No order was placed on any venue.")
    if MODE == "dumb":
        print("THE SPINE: KPVVOa6c6dY_dumb_clean.txt, 2026-06-14, his newest.")
        print("  'one pair, one time frame, one session, and one entry signal'")
        print("  EUR/USD, the 4 hour, pre-London and London, engulfing candles.")
        print("  HIS OWN SPINE IS ONE PAIR. The other three are OUR extension.")
    print("Each instrument on its own $100,000. 3% of the account risked per")
    print("trade; leverage below is the OUTPUT of that and the structural stop.")
    print("=" * 92)

    for label, a, b in WINDOWS:
        wk = weeks_between(a, b)
        book = ae.run_book(None, a, b, cache=cache, verbose=False, mode=MODE)
        f = ae.frame(book)
        print(f"\n### {label}   {a} -> {b}   ({wk:.0f} weeks)")
        print(HEAD)
        for inst in ae.INSTRUMENTS:
            g = f[f["instrument"] == inst]
            s = stats(g, wk)
            print(line(inst + (" (BloFin)" if inst == ae.GOLD else ""), s))
            s.update({"window": label, "instrument": inst, "session": "all"})
            out_rows.append(s)
            for sess in ("london", "new_york"):
                gs = g[g["session"] == sess]
                if not len(gs):
                    continue
                ss = stats(gs, wk)
                print(line("    " + sess, ss))
                ss.update({"window": label, "instrument": inst,
                           "session": sess})
                out_rows.append(ss)

        tot = stats(f, wk)
        print(line("  BOOK TOTAL", tot))
        nwk, pct = weekly_profitability(f)
        print(f"  weeks with a closed trade: {nwk}   "
              f"of those, {pct:.0f}% ended profitable "
              f"(his claim for himself: 60-70%)")
        d = f[f["outcome"].isin(CLOSED)]
        if len(d):
            print(f"  stop distance, as a MOVE IN THE PRICE: "
                  f"{d['stop_move_in_price_pct'].min():.2f}% to "
                  f"{d['stop_move_in_price_pct'].max():.2f}%")
            print(f"  hold time: median {d['hours_held'].median():.0f}h, "
                  f"longest {d['hours_held'].max():.0f}h "
                  f"({d['hours_held'].max() / 24:.1f} days)")
            print(f"  costs charged: ${d['cost'].sum():,.0f}   "
                  f"stop-and-target in the same 15 minutes, scored as the "
                  f"loss: {int(d['same_bar_resolved'].sum())}")
            print(f"  closed early on HIS FRIDAY RULE (a loss, never a break "
                  f"even): {int((f['outcome'] == 'friday').sum())}")
        print(f"  still open at the window's end: "
              f"{int((f['outcome'] == 'open').sum())}   "
              f"past our own 30-day cap: {int((f['outcome'] == 'held_out').sum())}")

    # ---------------------------------------------- the 1:3 reading
    print("\n" + "=" * 92)
    print("HIS TARGET IS SELF-CONTRADICTORY AND BOTH READINGS ARE MEASURED")
    print("  1:2  'always be a minimum of a one to two risk-to-reward'")
    print("       grw58BIzotU.txt 08:37:45, 2025-09-28   <- the default above")
    print("  1:3  'our risk-to-reward needs to be a minimum of a 1 to three+'")
    print("       LwMsai2ppKc.txt 00:07:24, 2026-02-22   <- NEWER")
    print("=" * 92)
    for r in (2.0, 3.0):
        book = ae.run_book(None, "2025-07-27", "2026-07-26",
                           cfg_over={"target_r": r}, cache=cache,
                           verbose=False, mode=MODE)
        f = ae.frame(book)
        s = stats(f, weeks_between("2025-07-27", "2026-07-26"))
        nwk, pct = weekly_profitability(f)
        print(line(f"12 months at 1:{r:.0f}", s) +
              f"   {pct:.0f}% of weeks green")

    if MODE == "dumb":
        print("\n" + "=" * 92)
        print("HIS OWN QUALITY DIAL — 'The more candlestick it engulfs, the "
              "better.'")
        print("  KPVVOa6c6dY_dumb_clean.txt, 2026-06-14. His floor is 1 (what "
              "ships); his")
        print("  favourite 'has eaten the last 10 candlesticks'. Swept over 5 "
              "years, not")
        print("  fitted — the shipping default stays at his literal floor.")
        print("=" * 92)
        print(HEAD)
        for n in (1, 2, 3, 4, 5, 6):
            bk = ae.run_book(None, "2021-07-05", "2026-07-26",
                             cfg_over={"min_engulfed": n}, cache=cache,
                             verbose=False, mode="dumb")
            fr = ae.frame(bk)
            eu = fr[fr["instrument"] == "EUR_USD"]
            eu_n = int(eu["outcome"].isin(CLOSED).sum())
            print(line(f"engulfs >= {n}", stats(fr, 264.0)) +
                  f"   EUR/USD alone: {eu_n / 264:.2f}/week")

        print("\n" + "=" * 92)
        print("HIS FRIDAY RULE, ON AND OFF — 5 years")
        print("  'if you're in a losing position and the weekend is coming up "
              "and you're")
        print("   halfway through your stop loss, I would probably close "
              "before the market")
        print("   closes'  — the spine, 2026-06-14. NEW; no older video has "
              "it.")
        print("=" * 92)
        print(HEAD)
        for on in (True, False):
            bk = ae.run_book(None, "2021-07-05", "2026-07-26",
                             cfg_over={"friday_exit_at_half_stop": on},
                             cache=cache, verbose=False, mode="dumb")
            print(line("Friday rule " + ("ON (his)" if on else "OFF"),
                       stats(ae.frame(bk), 264.0)))

    pd.DataFrame(out_rows).to_csv(
        os.path.join(REPO, "step470_alex_results.csv"), index=False)
    print("\nrows written to step470_alex_results.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
