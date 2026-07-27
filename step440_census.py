"""
step440_census.py — what actually happened to the runner, and what the
spread buffer costs, measured against the build AS FOUND (step438).

Reads step438_trades.csv rather than the live bot, so it keeps answering the
same question after tjr_bot.py changes underneath it.

Three questions, all of them factual:

  1. Of the trades whose first target filled, how many ended at break even
     and how many reached a further target? He calls a runner stopped at
     break even a normal outcome, so this is a census, not a complaint.

  2. When the break-even stop took the runner out, how much further did
     price go in the trade's favour before the session ended? That is the
     only way to see whether break even protected a winner or strangled one.

  3. What fraction of the distance to the stop is the spread buffer? Reward
     per dollar risked has the stop in the denominator, so a buffer sized
     for the wrong instrument moves the number without any change to the
     exit.

RESEARCH ONLY. No orders. Nothing here can reach a broker.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
from tjr_bot import to_et_frame

REPO = "/Users/wallacechen/cryptobot"
FLAT = pd.Timestamp("1970-01-01 15:55").time()


def bars_for(cache, symbol, day):
    if symbol not in cache:
        cache[symbol] = to_et_frame(
            pd.read_parquet(f"{REPO}/data_alpaca_{symbol}_1m.parquet"))
    f = cache[symbol]
    lo = day + pd.Timedelta(hours=9, minutes=30)
    hi = day + pd.Timedelta(hours=16)
    return f[(f["t"] >= lo) & (f["t"] < hi)].reset_index(drop=True)


def main() -> int:
    t = pd.read_csv(f"{REPO}/step438_trades.csv")
    cache = {}
    rows = []
    for r in t.itertuples():
        day = pd.Timestamp(r.date)
        d = 1 if r.side == "long" else -1
        bars = bars_for(cache, r.symbol, day)
        entry_t = day + pd.Timedelta(hours=int(r.entry_at[:2]),
                                     minutes=int(r.entry_at[3:5]))
        exit_t = day + pd.Timedelta(hours=int(r.exit_at[:2]),
                                    minutes=int(r.exit_at[3:5]))
        rps = r.risk_per_share

        # replay the build as found: stop first inside a bar, then target 1,
        # then the whole runner out at target 2
        stop, filled, ended = r.stop, False, ""
        t1_t = t2_t = None
        for b in bars[bars["t"] >= entry_t].itertuples():
            if (b.low <= stop) if d > 0 else (b.high >= stop):
                ended = "stopped at break even" if filled else "stopped out"
                break
            if not filled and ((b.high >= r.target1) if d > 0
                               else (b.low <= r.target1)):
                filled, stop, t1_t = True, r.entry, b.t
            if filled and ((b.high >= r.target2) if d > 0 else (b.low <= r.target2)):
                ended, t2_t = "reached target 2", b.t
                break
            if b.t.time() >= FLAT:
                ended = "flat by the close"
                break
        ended = ended or "flat by the close"

        # after the exit, before the ORIGINAL stop: how much more was there
        after = bars[bars["t"] > exit_t]
        best = None
        for b in after.itertuples():
            if (b.low <= r.stop) if d > 0 else (b.high >= r.stop):
                break
            px = b.high if d > 0 else b.low
            if best is None or (px > best if d > 0 else px < best):
                best = px
        left_on_table = 0.0 if best is None else d * (best - r.exit_price) / rps

        rows.append({
            "date": r.date, "symbol": r.symbol,
            "target1_filled": filled,
            "runner_ended": ended if filled else "never got a partial",
            "made_per_dollar_risked": r.reward_vs_risk,
            "left_on_table_per_dollar_risked": round(left_on_table, 3),
            "buffer_share_of_the_stop_distance":
                round(100 * 0.0001 * r.entry / rps, 2),
        })
    c = pd.DataFrame(rows)
    c.to_csv(f"{REPO}/step440_census.csv", index=False)

    print("=" * 72)
    print("1. WHAT HAPPENED TO THE RUNNER  (build as found, 20 trades)")
    print("=" * 72)
    print(f"  first target filled            {int(c['target1_filled'].sum())} of {len(c)}")
    print(f"  never got a partial            {int((~c['target1_filled']).sum())}")
    for k, v in c[c["target1_filled"]]["runner_ended"].value_counts().items():
        print(f"  runner {k:<28} {v}")

    print()
    print("=" * 72)
    print("2. WHEN THE BREAK-EVEN STOP TOOK THE RUNNER, WHAT WAS LEFT BEHIND")
    print("=" * 72)
    be = c[c["runner_ended"] == "stopped at break even"]
    if len(be):
        print(be[["date", "symbol", "made_per_dollar_risked",
                  "left_on_table_per_dollar_risked"]].to_string(index=False))
        print(f"\n  median left behind after a break-even stop: "
              f"{be['left_on_table_per_dollar_risked'].median():+.3f} per $1 risked")
    else:
        print("  none")

    print()
    print("=" * 72)
    print("3. THE SPREAD BUFFER AS A SHARE OF THE DISTANCE TO THE STOP")
    print("   (the buffer is 0.01% of price — his number, taken from an index")
    print("    quoted near 5,000, applied to funds quoted near 700)")
    print("=" * 72)
    b = c["buffer_share_of_the_stop_distance"]
    print(f"  median {b.median():.2f}%   mean {b.mean():.2f}%   "
          f"worst {b.max():.2f}%   best {b.min():.2f}%")
    print("  every percent of the stop distance is a percent off what the")
    print("  trade makes for every $1 risked, with the exit untouched.")
    print(f"\nwritten: {REPO}/step440_census.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
