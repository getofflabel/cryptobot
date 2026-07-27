"""
step466_truncation.py — what the imaginary midnight bell cost the crypto book.

WALLACE, 2026-07-26: "crypto runs 24/7, then let it run 24/7. dont cut shit."

WHAT THIS MEASURES
    `tjr_bot.run_day` walks ONE day's bars and closes anything still open when
    they run out. On SPY that is the closing bell and it is real. On crypto
    there is no bell, so every trade that needed longer than the rest of a UTC
    day to reach its target was booked at whatever it happened to be worth at
    midnight. The live path never did this — `manage_step` returns "hold" at
    23:55 and the position runs on — so the replay was describing a bot we
    were not running.

    The asymmetry is the point. A loser always has time to reach its stop,
    because the stop is close by construction — just beyond the sweep. A
    winner needs room and it needs time. So a bell that lands at a fixed hour
    cuts winners far more often than losers, and it cuts them at whatever
    price the clock happened to land on.

HOW IT ISOLATES THE EFFECT
    Two books are walked side by side off ONE run, so the entries, the sizes,
    the stops and the targets are identical in both and the ONLY difference is
    what happens at midnight:

      the CUT book    every still-open trade is closed at the day's last bar,
                      exactly as `_force_flat` did it. This is the baseline
                      every crypto number in the project was measured on.
      the RUN book    the same trade, deep-copied mid-flight with its ladder
                      state intact, walked forward over the following days'
                      bars by the same `TjrBot._manage` until it reaches its
                      stop or its targets.

    The day loop is driven by the CUT book, so its equity, its losing-week
    ledger and therefore its entries are bit-for-bit the pre-step466 replay.
    That is deliberate: it separates "what the bell cost" from "what a
    different equity curve would have gone on to trade", which is a second and
    much noisier question answered by `--full`.

    A trade still open when the DATA runs out is closed at the last bar and
    counted separately. It is not a bell and is not called one.

    `--full` re-runs both books end to end instead, letting the carried
    profits and losses feed back into sizing and into the losing-streak rule.

USAGE
    python3 step466_truncation.py            # the isolation, all pairs
    python3 step466_truncation.py --full     # before/after, end to end
    python3 step466_truncation.py --pair BTC/USD

RESEARCH ONLY. Reads parquet off disk, walks it through the existing bot,
writes step466_* CSVs. No network, no broker, no orders, no git.
"""

from __future__ import annotations

import copy
import os
import sys
import time

import pandas as pd

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

import tjr_crypto as tc
from tjr_bot import Bar, NewsCalendar, TjrBot

ACCOUNT_START = 100_000.0
YEARS = range(2021, 2027)


def load_pair(pair: str) -> dict:
    """The cached bars, with step455's deeper DOT 1-minute refill when it is
    there — its own backfill died on a rate limit at 2026-03-01."""
    d = tc.load(pair)
    alt = f"{REPO}/step455_{pair.replace('/', '')}_1m.parquet"
    if os.path.exists(alt):
        a = pd.read_parquet(alt)
        if len(a) > len(d["1m"]):
            d["1m"] = a
    return d


# ======================================================= THE TWO BOOKS
def walk(pair: str, start, end, cfg, data) -> dict:
    """One walk, two books. See the module docstring for what differs.

    Nothing here is a rule. Every decision is `TjrBot`'s; this only chooses
    whether a still-open position is closed at midnight or handed the next
    day's bars.
    """
    bot = TjrBot(cfg, NewsCalendar(rules=False))
    d1 = data["1m"]
    days = tc.days_in(data, start, end)
    cut, run_twin = [], []          # the same trades, the two endings
    other = []                      # trades that closed inside their own day
    carries: list[tc._Carry] = []
    closed_cut: list = []           # what the CUT book had banked, for equity
    equity, last_row = ACCOUNT_START, None

    for day in days:
        day = pd.Timestamp(day)
        session1 = d1[(d1["t"] >= day) & (d1["t"] < day + pd.Timedelta(days=1))]
        if len(session1) == 0:
            continue
        last_row = session1.iloc[-1]

        bot.account = equity
        bot.week_pnl = tc._weeks(closed_cut)
        res = bot.run_day({pair: tc.slice_for(data, day, cfg)}, day)

        # the RUN book's carried positions get today's bars
        for c in list(carries):
            c.advance(bot, session1)
            if not c.trades:
                carries.remove(c)

        finished = [t for t in res["trades"] if t.outcome]
        open_now = [t for t in res["trades"] if not t.outcome]
        other += finished
        closed_cut += finished

        if open_now:
            # snapshot BEFORE the bell, with the ladder state intact
            twins = [copy.deepcopy(t) for t in open_now]
            carries.append(tc._Carry(twins, tc._one_minute_trend(d1, day)))
            run_twin += twins
            idx = {r.t: Bar(r.t, r.open, r.high, r.low, r.close)
                   for r in session1.itertuples()}
            for tr in open_now:
                tc._ORIGINAL_FORCE_FLAT(bot, tr, idx, None)
            cut += open_now
            closed_cut += open_now

        equity = ACCOUNT_START + sum(t.pnl for t in closed_cut)

    ran_out = 0
    for c in carries:
        for tr in c.trades:
            if last_row is None:
                continue
            bot._close(tr, float(last_row["close"]), last_row["t"], tc.RAN_OUT)
            ran_out += 1
    return {"cut": cut, "run": run_twin, "other": other, "ran_out": ran_out,
            "days": len(days)}


def _hours_held(tr) -> float:
    if tr.entry_t is None or tr.exit_t is None:
        return 0.0
    return (pd.Timestamp(tr.exit_t) - pd.Timestamp(tr.entry_t)).total_seconds() / 3600


def isolation(pairs=None, years=YEARS) -> pd.DataFrame:
    rows = []
    for pair in (pairs or tc.PAIRS):
        try:
            data = load_pair(pair)
        except FileNotFoundError:
            print(f"  {pair}: no cached bars")
            continue
        cfg = tc.crypto_config(pair)
        lo = pd.Timestamp(data["1m"]["t"].min()).year
        for y in years:
            if y < lo:
                continue
            t0 = time.time()
            r = walk(pair, pd.Timestamp(f"{y}-01-01"),
                     pd.Timestamp(f"{y}-12-31"), cfg, data)
            if not r["cut"] and not r["other"]:
                continue
            n_all = len(r["cut"]) + len(r["other"])
            cut_d = sum(t.pnl for t in r["cut"])
            run_d = sum(t.pnl for t in r["run"])
            rows.append({
                "pair": pair, "year": y, "days": r["days"],
                "trades": n_all,
                "truncated": len(r["cut"]),
                "truncated_share_pct": round(100 * len(r["cut"]) / max(n_all, 1), 1),
                "cut_at_midnight_dollars": round(cut_d),
                "allowed_to_run_dollars": round(run_d),
                "difference_dollars": round(run_d - cut_d),
                "book_cut_dollars": round(cut_d + sum(t.pnl for t in r["other"])),
                "book_run_dollars": round(run_d + sum(t.pnl for t in r["other"])),
                "median_hours_held_cut": round(pd.Series(
                    [_hours_held(t) for t in r["cut"]]).median(), 1) if r["cut"] else 0.0,
                "median_hours_held_run": round(pd.Series(
                    [_hours_held(t) for t in r["run"]]).median(), 1) if r["run"] else 0.0,
                "still_open_when_record_ended": r["ran_out"],
            })
            o = rows[-1]
            print(f"  {pair:9s} {y}  {n_all:>4} trades  "
                  f"{o['truncated']:>4} cut ({o['truncated_share_pct']:>4.1f}%)  "
                  f"cut ${o['cut_at_midnight_dollars']:>9,}  "
                  f"run ${o['allowed_to_run_dollars']:>9,}  "
                  f"diff ${o['difference_dollars']:>+9,}   ({time.time()-t0:.0f}s)")
    return pd.DataFrame(rows)


# ============================================== THE WHOLE BOOK, END TO END
def full(pairs=None, years=YEARS) -> pd.DataFrame:
    """Both books re-run end to end, so the carried money feeds back into
    sizing and into the losing-streak rule. Noisier than the isolation and
    reported alongside it, never instead of it."""
    rows = []
    for pair in (pairs or tc.PAIRS):
        try:
            data = load_pair(pair)
        except FileNotFoundError:
            continue
        cfg = tc.crypto_config(pair)
        lo = pd.Timestamp(data["1m"]["t"].min()).year
        for y in years:
            if y < lo:
                continue
            t0 = time.time()
            out = {}
            for carry in (False, True):
                out[carry] = tc.run_pair(
                    pair, pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y}-12-31"),
                    cfg=cfg, data=data, carry_past_the_boundary=carry)
            if not out[False]["trades"] and not out[True]["trades"]:
                continue

            def lev(r):
                v = [t.notional / t.sizing_account for t in r["trades"]
                     if t.sizing_account]
                s = pd.Series(v)
                return (round(s.median(), 2), round(s.min(), 2), round(s.max(), 2)) \
                    if len(s) else (0.0, 0.0, 0.0)

            lo_, mn, mx = lev(out[True])
            rows.append({
                "pair": pair, "year": y, "days": out[False]["days"],
                "trades_cut": len(out[False]["trades"]),
                "trades_run": len(out[True]["trades"]),
                "dollars_cut": round(out[False]["account"] - ACCOUNT_START),
                "dollars_run": round(out[True]["account"] - ACCOUNT_START),
                "difference_dollars": round(out[True]["account"]
                                            - out[False]["account"]),
                "crossed_the_boundary": out[True]["crossed_the_boundary"],
                "leverage_median": lo_, "leverage_min": mn, "leverage_max": mx,
            })
            o = rows[-1]
            print(f"  {pair:9s} {y}  cut ${o['dollars_cut']:>9,} "
                  f"({o['trades_cut']:>4} trades)   "
                  f"run ${o['dollars_run']:>9,} ({o['trades_run']:>4})   "
                  f"diff ${o['difference_dollars']:>+9,}   "
                  f"leverage {o['leverage_median']}x   ({time.time()-t0:.0f}s)")
    return pd.DataFrame(rows)


def main() -> int:
    args = sys.argv[1:]
    pairs = None
    if "--pair" in args:
        pairs = [args[args.index("--pair") + 1]]
    if "--full" in args:
        print("the whole crypto book, cut at midnight versus allowed to run")
        d = full(pairs)
        d.to_csv(f"{REPO}/step466_full_before_after.csv", index=False)
        print(f"\n  trades cut  {d['trades_cut'].sum():>6,}   "
              f"trades run {d['trades_run'].sum():>6,}")
        print(f"  dollars     cut ${d['dollars_cut'].sum():>12,}   "
              f"run ${d['dollars_run'].sum():>12,}   "
              f"difference ${d['difference_dollars'].sum():>+12,}")
        print(f"  pair-years positive: cut "
              f"{(d['dollars_cut'] > 0).sum()}/{len(d)}   "
              f"run {(d['dollars_run'] > 0).sum()}/{len(d)}")
        print("written: step466_full_before_after.csv")
        return 0

    print("the trades the imaginary midnight bell cut, and what they were "
          "worth allowed to run")
    d = isolation(pairs)
    d.to_csv(f"{REPO}/step466_truncation.csv", index=False)
    print()
    print(f"  trades            {d['trades'].sum():>10,}")
    print(f"  truncated         {d['truncated'].sum():>10,}  "
          f"({100 * d['truncated'].sum() / max(d['trades'].sum(), 1):.1f}% of them)")
    print(f"  cut at midnight   ${d['cut_at_midnight_dollars'].sum():>+12,}")
    print(f"  allowed to run    ${d['allowed_to_run_dollars'].sum():>+12,}")
    print(f"  difference        ${d['difference_dollars'].sum():>+12,}")
    print(f"  whole book        cut ${d['book_cut_dollars'].sum():>+12,}   "
          f"run ${d['book_run_dollars'].sum():>+12,}")
    print(f"  pair-years positive: cut "
          f"{(d['book_cut_dollars'] > 0).sum()}/{len(d)}   "
          f"run {(d['book_run_dollars'] > 0).sum()}/{len(d)}")
    print("written: step466_truncation.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
