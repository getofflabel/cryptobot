"""
step352_oil_clock_significance.py -- ROUND 350, part 3: is the clock's
effect on money bigger than luck?

Part 1 found every cell negative. Part 2 found something more interesting
than a flat wall: entering on a 24-hour breakout during London/New York
hours loses far LESS than entering at random times in the same hours
(-$9.07 versus -$38.38 per trade on a 24-hour leash), and on a longer
leash the London/NY arm gets within about a dollar of break-even
(-$1.27/trade at a 72-hour cap) while the Asia/off-hours arm stays at
-$12.09. So the clock clearly moves the money in the direction the
realized-movement measurement predicted.

The question this file answers: is that gap bigger than what shuffling
the session labels would produce anyway? Round 113 ran that shuffle on
realized price movement. Nobody has ever run it on P&L, which is the
only version that matters for deciding whether to trade it.

METHOD. Take every 24-hour-breakout trade on the train slice with no
session filter at all, through the same chart-structure trailing stop, at
the same market-order costs, on the leash being examined. Label each
trade by the hour it was entered. Compare the real average profit per
trade of the London/NY-entered group against the Asia/off-entered group.
Then shuffle the labels across the same set of trades 2,000 times and see
where the real gap sits in that distribution.

Train slice only. The validation slice is not read by this file and the
sealed final 20% is truncated at load, as in parts 1 and 2.

RESEARCH ONLY. No live orders, no live bot file edited.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from step150_common import run_edge, thickness, trade_stats
from step351_oil_session_controls import EXITS
from step350_oil_session_gate import (SESSION_FILTERS, entries_for, load_oil)

SHUFFLES = 2000


def main():
    d, i_tr, _ = load_oil()
    d_tr = d.iloc[:i_tr].reset_index(drop=True)
    sb, tb = EXITS["structure_trail_only"]
    rows = []

    for hold in (24, 48, 72):
        ev = entries_for(d_tr, "breakout_24h", "all_hours")
        trades, _ = run_edge(d_tr, ev, sb, tb, hold)
        if not trades:
            continue
        hrs = np.array([pd.Timestamp(t["entry_time"]).hour for t in trades])
        pnl = np.array([t["pnl"] for t in trades])
        ldn = np.isin(hrs, list(SESSION_FILTERS["london_ny"]))
        asia = np.isin(hrs, list(SESSION_FILTERS["asia_off"]))
        if ldn.sum() < 10 or asia.sum() < 10:
            continue
        gap = pnl[ldn].mean() - pnl[asia].mean()

        rng = np.random.default_rng(352)
        draws = np.empty(SHUFFLES)
        n_ldn = int(ldn.sum())
        for i in range(SHUFFLES):
            perm = rng.permutation(len(pnl))
            draws[i] = pnl[perm[:n_ldn]].mean() - pnl[perm[n_ldn:]].mean()
        pct = float((draws < gap).mean() * 100)
        one_sided_p = float((draws >= gap).mean())

        st_all = trade_stats(trades)
        th_all = thickness(st_all["expectancy"], st_all["avg_notional"])
        print(f"leash {hold:2d}h | all trades n={len(pnl)} avg ${pnl.mean():+.2f}/trade "
              f"({th_all['mult_12bps']:+.2f}x the cost of trading)")
        print(f"          London/NY-entered n={n_ldn} avg ${pnl[ldn].mean():+.2f} | "
              f"Asia/off-entered n={int(asia.sum())} avg ${pnl[asia].mean():+.2f} | "
              f"gap ${gap:+.2f}")
        print(f"          gap sits at the {pct:.1f}th percentile of {SHUFFLES} label shuffles "
              f"(one-sided chance of seeing this or better: {one_sided_p:.3f})\n")
        rows.append(dict(leash_h=hold, n_trades=len(pnl), avg_all=pnl.mean(),
                         n_london_ny=n_ldn, avg_london_ny=pnl[ldn].mean(),
                         n_asia_off=int(asia.sum()), avg_asia_off=pnl[asia].mean(),
                         gap=gap, shuffle_percentile=pct, one_sided_p=one_sided_p))

    pd.DataFrame(rows).to_csv("step352_table.csv", index=False)
    print("wrote step352_table.csv")


if __name__ == "__main__":
    main()
