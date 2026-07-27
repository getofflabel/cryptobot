"""
step466_bias_boundary.py — is the daily bias a thing on a market with no days?

THE QUESTION, AND WHY IT IS ASKED THIS WAY
    The daily bias is METHOD. "can we go against daily bias no... we're going
    to stick to this bias until we're proved wrong" (bootcamp Day 49), and
    `Config.enforce_daily_bias_side` is how it ships. Nothing here proposes
    removing it.

    What is NOT method is the twenty-four hours it is measured over.
    `tjr_bot.daily_bars` cuts a crypto daily candle at `t.dt.normalize()` —
    plain UTC midnight — and `build_context` reads a trend off that stack of
    candles once, at 00:00, and then forbids the opposite side until 00:00 the
    next day. On the markets he teaches, the venue decides where the candle is
    cut. On crypto nothing does. tjr_crypto.py says so in its own comment: "on
    a 24/7 market there is no correct answer here, only a stated one."

    So the honest test is not "which hour is best" — picking a smarter hour is
    still picking, and we do not invent rules. The test is: DOES THE ANSWER
    DEPEND ON THE HOUR? If the daily trend read is the same whichever of the
    24 hours you cut at, the boundary is harmless bookkeeping and the bias
    stands. If it flips depending on where you cut, then on a market with no
    days the "daily bias" is not reading the market, it is reading our choice,
    and that is a finding for Wallace to rule on rather than something to
    patch.

WHAT IT MEASURES
    For every pair, all 24 possible day boundaries, the same way the bot does
    it: group the 5-minute frame into daily candles at that boundary, feed
    them to `TrendTracker` — the same two-candle swing and body-close break of
    structure — and take `state` as the day's direction. Then, at every one of
    those daily closes, ask how many of the 24 readings say long, how many say
    short, and how many say not-yet-established.

    AGREEMENT is the share of readings that match UTC midnight's, the boundary
    we actually ship. UNANIMOUS is the share of days where all 24 boundaries
    give the same answer. Both are computed only from candles that had CLOSED,
    so the walk is causal at every hour.

    It also counts, from the replay itself, how many days stood down with the
    reason "a level was pushed through, but only on the side the day's bias
    forbids" — which is the sentence that refused the ETH move on 2026-07-26.

USAGE
    python3 step466_bias_boundary.py
    python3 step466_bias_boundary.py --pair ETH/USD

RESEARCH ONLY. Reads parquet off disk. No network, no broker, no orders,
no git.
"""

from __future__ import annotations

import os
import sys

import pandas as pd

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

import tjr_crypto as tc
from tjr_bot import Bar, TrendTracker

FORBIDS = "a level was pushed through, but only on the side the day's bias forbids"


def daily_direction_at(d5: pd.DataFrame, boundary_hour: int) -> pd.DataFrame:
    """The daily trend read, day by day, if the day were cut at
    `boundary_hour` UTC.

    Identical arithmetic to `tjr_bot.daily_bars` + `TrendTracker`, with the
    grouping key moved. `close_t` is the moment the candle finished, which is
    the first moment its direction could be known — the same causality stamp
    used everywhere else.
    """
    off = pd.Timedelta(hours=boundary_hour)
    g = (d5["t"] - off).dt.normalize() + off
    daily = pd.DataFrame({"open": d5.groupby(g)["open"].first(),
                          "high": d5.groupby(g)["high"].max(),
                          "low": d5.groupby(g)["low"].min(),
                          "close": d5.groupby(g)["close"].last()})
    daily.index.name = "t"
    daily = daily.reset_index()
    tt, states = TrendTracker(), []
    for r in daily.itertuples():
        tt.update(Bar(r.t, r.open, r.high, r.low, r.close))
        states.append(tt.state)
    daily["dir"] = states
    # the direction is only KNOWN once the candle has closed
    daily["known_at"] = daily["t"] + pd.Timedelta(days=1)
    return daily[["t", "known_at", "dir"]]


def sweep(pair: str) -> dict:
    d5 = tc.load(pair)["5m"]
    if len(d5) == 0:
        return {}
    reads = {h: daily_direction_at(d5, h) for h in range(24)}

    # line every boundary's reading up on ONE clock: at each UTC midnight, what
    # does each of the 24 boundaries say, using only candles closed by then?
    grid = sorted(reads[0]["known_at"])
    rows = []
    for h in range(24):
        r = reads[h].sort_values("known_at")
        s = pd.merge_asof(pd.DataFrame({"known_at": grid}), r,
                          on="known_at", direction="backward")
        rows.append(s["dir"].fillna(0).astype(int).to_numpy())
    m = pd.DataFrame(rows).T          # one row per day, one column per boundary
    m = m.iloc[60:]                   # let every tracker establish itself
    if len(m) == 0:
        return {}

    base = m[0]                       # UTC midnight — the boundary we ship
    agree = (m.eq(base, axis=0).sum(axis=1) - 1) / 23.0
    unanimous = (m.nunique(axis=1) == 1)
    # the days where the SIDE the method may take is not even agreed on
    both_sides = ((m > 0).any(axis=1) & (m < 0).any(axis=1))
    return {
        "pair": pair,
        "days": int(len(m)),
        "agree_with_midnight_pct": round(100 * float(agree.mean()), 1),
        "all_24_agree_pct": round(100 * float(unanimous.mean()), 1),
        "boundaries_disagree_on_the_side_pct": round(100 * float(both_sides.mean()), 1),
        "midnight_long_pct": round(100 * float((base > 0).mean()), 1),
        "midnight_short_pct": round(100 * float((base < 0).mean()), 1),
    }


def bias_stand_downs(pair: str, start=None, end=None) -> dict:
    """How often the shipped bias is the thing that refused the day."""
    r = tc.run_pair(pair, start, end)
    total = sum(r["reasons"].values())
    return {"pair": pair, "days_stood_down": total,
            "refused_by_the_bias": r["reasons"].get(FORBIDS, 0),
            "share_pct": round(100 * r["reasons"].get(FORBIDS, 0)
                               / max(total, 1), 1)}


def main() -> int:
    args = sys.argv[1:]
    pairs = [args[args.index("--pair") + 1]] if "--pair" in args else tc.PAIRS
    print("the daily trend read, at all 24 possible day boundaries")
    print("-" * 78)
    rows = []
    for p in pairs:
        try:
            s = sweep(p)
        except FileNotFoundError:
            print(f"  {p}: no cached bars")
            continue
        if not s:
            continue
        rows.append(s)
        print(f"  {p:9s} {s['days']:>5} days   "
              f"agree with midnight {s['agree_with_midnight_pct']:>5.1f}%   "
              f"all 24 agree {s['all_24_agree_pct']:>5.1f}%   "
              f"boundaries take opposite sides "
              f"{s['boundaries_disagree_on_the_side_pct']:>5.1f}% of days")
    d = pd.DataFrame(rows)
    if len(d):
        d.to_csv(f"{REPO}/step466_bias_boundary.csv", index=False)
        print()
        print(f"  pooled: {d['agree_with_midnight_pct'].mean():.1f}% agree with "
              f"midnight, all 24 agree on {d['all_24_agree_pct'].mean():.1f}% "
              f"of days, and on "
              f"{d['boundaries_disagree_on_the_side_pct'].mean():.1f}% of days "
              f"two boundaries would take OPPOSITE sides.")
        print("written: step466_bias_boundary.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
