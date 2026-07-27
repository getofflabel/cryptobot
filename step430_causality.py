"""
step430_causality.py - the truncation test.

The confirmation sequence is the easiest thing in this round to get
wrong: a higher low is only KNOWN some bars after it forms, and a
two-candle swing is stamped on the second candle.  If any of that leaked
a future price, every distance in step430_results.md would be fiction.

The test: take a sample of confirmation bars found on the full history,
then rebuild the whole chain - higher-timeframe levels, the live pool of
unswept levels, the sweep, the higher low, the higher high - on data
TRUNCATED at that bar, with nothing after it in memory.  The signal must
appear at the same bar, on the same side, with the same stop.

RESEARCH ONLY.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
from step430_lib import (REPO, htf_new_levels, load_5m, scan_confirm,
                         scan_sweeps, tjr_swings)

LEVEL_TF = 60


def chain(d):
    nh, nl = htf_new_levels(d, LEVEL_TF)
    sw = scan_sweeps(d, nh, nl)
    sh5, sl5 = tjr_swings(d)
    return scan_confirm(d, sw, sh5, sl5)


def main():
    fh = open(f"{REPO}/step430_causality_out.txt", "w")
    W = lambda s: (print(s), fh.write(s + "\n"))
    rng = np.random.default_rng(430)
    W("TRUNCATION TEST - can every signal be produced without any price")
    W("that had not printed yet?")
    W("")
    for sym, src in [("SPY", "alpaca"), ("BTCUSDT", "bybit")]:
        d = load_5m(sym, src)
        full = chain(d)
        # only check signals with enough history in front of them to rebuild
        cand = full[full["sig_idx"] > 20000]
        pick = cand.sample(n=min(40, len(cand)), random_state=430)
        ok = bad = 0
        details = []
        for r in pick.itertuples():
            t = int(r.sig_idx)
            dt = d.iloc[:t + 1].reset_index(drop=True)   # nothing after t
            tr = chain(dt)
            m = tr[(tr["sig_idx"] == t) & (tr["side"] == int(r.side)) &
                   ((tr["stop"] - float(r.stop)).abs() < 1e-9)]
            # two levels can confirm on the same bar, so the test is that
            # the SAME signal is present, not that it is the only one
            same_bar_full = int((full["sig_idx"] == t).sum())
            if len(m) >= 1 and len(m) == int(
                    ((full["sig_idx"] == t) & (full["side"] == int(r.side)) &
                     ((full["stop"] - float(r.stop)).abs() < 1e-9)).sum()):
                ok += 1
            else:
                bad += 1
                details.append((t, len(m), same_bar_full))
        W(f"{sym}: rebuilt {ok + bad} signals from truncated history - "
          f"{ok} identical, {bad} different")
        if bad:
            W(f"   MISMATCHES (bar, times found in truncated run): "
              f"{details[:10]}")
        else:
            W("   every signal reproduced exactly, same bar, same side, "
              "same stop -> no price from the future is being used")
    fh.close()


if __name__ == "__main__":
    main()
