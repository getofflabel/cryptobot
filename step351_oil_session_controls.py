"""
step351_oil_session_controls.py -- ROUND 350, part 2: the controls that make
part 1's negative result mean something.

Part 1 (step350_oil_session_gate.py) found all 18 cells negative on the
train slice, so no validation look was spent and nothing was selected.
A wall of negatives is only informative if two further things are known,
and neither costs a validation look because both are measured on the
train slice alone:

1. THE FLOOR. What does entering at RANDOM TIMES, through the SAME
   chart-structure exits, at the SAME market-order costs, earn on this
   data? If the entry shapes land on the same number as random entries,
   then the shapes contribute nothing and the losses are simply the cost
   of trading plus oil's own drift -- a much stronger statement than
   "these three shapes lose money". Run separately for random entries
   confined to London/New York hours and random entries across all hours,
   so the clock itself is measured with no entry shape attached.

2. THE LEASH. Part 1 capped every trade at 24 hours held. If the session
   gate only pays on a longer leash, part 1 would have missed it. The
   three-arm comparison (all hours vs London/NY vs the Asia/off placebo)
   is therefore repeated for the least-bad shape at 24, 48 and 72 hours.
   This is a robustness check on part 1's headline, NOT a search for a
   winning setting: no cell here is eligible for selection and no
   validation slice is read by this file at all.

The sealed final 20% is truncated at load exactly as in part 1 and is
never seen. Market orders both legs throughout. Stops are chart levels
from exits.py.

RESEARCH ONLY. No live orders, no live bot file edited.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from step150_common import fmt_stats, run_edge, thickness, trade_stats
from step350_oil_session_gate import (EXITS, MAX_HOLD_BARS, SESSION_FILTERS,
                                      entries_for, load_oil, random_control)

DRAWS = 60


def main():
    d, i_tr, sealed_n = load_oil()
    d_tr = d.iloc[:i_tr].reset_index(drop=True)
    print(f"CL=F 1h train slice only: {len(d_tr)} bars "
          f"({pd.DatetimeIndex(d_tr['timestamp'])[0]} -> {pd.DatetimeIndex(d_tr['timestamp'])[-1]})")
    print(f"validation slice NOT read by this file; sealed {sealed_n} bars truncated at load\n")

    rows = []

    # ---- 1. THE FLOOR -------------------------------------------------
    print("=" * 78)
    print("1. THE FLOOR -- entries at random times, same chart-structure exits, same costs")
    print("=" * 78)
    for exit_name, (sb, tb) in EXITS.items():
        for session in ("all_hours", "london_ny", "asia_off"):
            ctl = random_control(d_tr, 250, 0.5, sb, tb, session, draws=DRAWS, seed=360)
            print(f"  {exit_name:22s} {session:10s} random entries -> "
                  f"${ctl['mean_exp']:+7.2f}/trade  ({ctl['n_draws']} draws of 250 trades, "
                  f"{ctl['pool']} eligible bars)")
            rows.append(dict(kind="random_floor", shape="(random times)", exit=exit_name,
                             session=session, max_hold_h=MAX_HOLD_BARS,
                             n=250, exp_per_trade=ctl["mean_exp"], draws=ctl["n_draws"]))

    # ---- 2. THE LEASH -------------------------------------------------
    print("\n" + "=" * 78)
    print("2. THE LEASH -- does a longer hold change the three-arm ordering? "
          "(least-bad shape from part 1)")
    print("=" * 78)
    shape = "breakout_24h"
    for hold in (24, 48, 72):
        for exit_name, (sb, tb) in EXITS.items():
            line = []
            for session in ("all_hours", "london_ny", "asia_off"):
                ev = entries_for(d_tr, shape, session)
                trs, _ = run_edge(d_tr, ev, sb, tb, hold)
                st = trade_stats(trs)
                th = thickness(st["expectancy"], st["avg_notional"])
                line.append(f"{session}:{st['n']}t/${st['expectancy']:+.2f}")
                rows.append(dict(kind="leash", shape=shape, exit=exit_name,
                                 session=session, max_hold_h=hold, n=st["n"],
                                 exp_per_trade=st["expectancy"],
                                 pct_of_position=th["pct_notional"],
                                 cost_multiple_12bps=th["mult_12bps"], draws=0))
            print(f"  hold<={hold:2d}h  {exit_name:22s} " + " | ".join(line))

    out = pd.DataFrame(rows)
    out.to_csv("step351_table.csv", index=False)
    print(f"\nwrote step351_table.csv ({len(out)} rows)")

    pos = out[(out.kind == "leash") & (out.exp_per_trade > 0)]
    print(f"cells with positive average profit per trade, losers included, anywhere in the "
          f"leash check: {len(pos)}/{len(out[out.kind == 'leash'])}")


if __name__ == "__main__":
    main()
