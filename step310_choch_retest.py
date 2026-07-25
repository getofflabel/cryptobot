"""
step310_choch_retest.py — ROUND 310, dead edge 1 of 4:
1h change-of-character (structure flip) + at least 2 agreeing tools.

WHAT OUR CODE ACTUALLY DID (step150a_choch_confluence.py, read line by line)
  trigger : bos_chain()'s choch_long/choch_short — the bar whose CLOSE
            finishes on the far side of the last confirmed swing level,
            when the prior structure chain was NOT already pointing that
            way. Plus a count of at least 2 of five agreeing tools.
  entry   : the very next bar's OPEN. So we bought the break itself.
  stop    : the most recent confirmed swing on the protective side, k=8.
  target  : 2x the stop distance.
  hold cap: 10 days of 1h bars.
  sample  : 74 trades in the first 60%, 34 in the middle 20%.
  result  : first 60% -$42.92 per trade, middle 20% +$70.61 per trade. FAIL.

WHAT PRACTITIONERS OF THIS METHOD REQUIRE THAT WE DID NOT IMPLEMENT
Everyone who teaches structure-flip trading says the same thing about the
break bar: do not buy it. The break tells you the level is now in play; the
TRADE is the return to that level. The sequence they all draw is break,
then retrace back to the broken level, then a close that holds above it,
and THAT close is the entry. Entering at the break is the single most
commonly named beginner error in this method, for a concrete reason: the
break bar is by definition the top of an impulse leg, so you buy at the
worst price in the move and your protective swing is a whole leg away,
which makes a 2x-stop-distance target unreachable inside any sane hold.
That is exactly the failure our own round-150 write-up diagnosed: "the
2x-R target isn't reached before max_hold on those" and trades drift to
the time cap.

Our own round 74 is corroborating evidence rather than a contradiction: it
found that a full break-plus-retest-plus-engulfing-candle stack was too
rare to test, and that dropping EITHER the retest OR the engulfing candle
produced every survivor it found, with Bitcoin's break configuration the
best expectancy in the round. Retest without the engulfing candle is the
half of that pair we never tried on this specific 1h structure-flip edge.

THE ONE CONDITION ADDED
Entry moves off the break bar and onto the first later bar, within a wait
window, whose LOW trades back to or through the broken level while its
CLOSE finishes back on the breakout side of it. If price instead closes
back through the level the wrong way, the break failed and the setup is
void, no entry. Nothing else changes: same signal, same tools count, same
stop method, same target multiple, same hold cap, same market-order costs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import exits as E
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import days_to_bars, split_points
from step150a_choch_confluence import (CONF_HOLD_DAYS, CONF_THRESHOLD, K,
                                       TARGET_MULT, build_entries)
from step150_common import mask_to_events
from step310_common import score_cell, wait_for_touch_then_close_back, write_table

WAIT_WINDOWS = (5, 10, 20)      # 1h bars allowed for the retest to arrive
EDGE = "1 - 1h structure flip + 2 agreeing tools"


def stop_builder(tc):
    return E.stop_structure(k=K, n_back=1, buffer_pct=0.0, use="wick")


def target_builder(stop):
    return E.target_fixed_r(stop, r_multiple=TARGET_MULT)


def main():
    print("=" * 78)
    print("STEP310 — edge 1: structure flip, entry moved to the RETEST of the")
    print("broken level instead of the break bar. Market orders throughout.")
    print("=" * 78)

    d1h_full = fetch_bybit_deep("1h", "BTCUSDT")
    d4h_full = fetch_bybit_deep("4h", "BTCUSDT")
    f1h_full = align_funding(d1h_full, fetch_funding_history("BTCUSDT"))

    n, i_tr, i_va = split_points(d1h_full)
    print(f"1h bars: {n} | first 60% ends {i_tr} | middle 20% ends {i_va} | "
          f"final {n - i_va} bars NEVER LOADED")

    d1h = d1h_full.iloc[:i_va].reset_index(drop=True)
    f1h = f1h_full.iloc[:i_va].reset_index(drop=True)
    cutoff = d1h["timestamp"].iloc[-1]
    d4h = d4h_full[d4h_full["timestamp"] <= cutoff].reset_index(drop=True)

    el, es = build_entries(d1h, d4h)
    max_hold = days_to_bars(d1h, CONF_HOLD_DAYS)

    # the broken level itself: bos_chain's forward-filled last confirmed
    # swing high (for an upward break) / swing low (for a downward break),
    # read AT the break bar. This is the level a retest returns to.
    from step56_smc_toolkit import bos_chain
    bos = bos_chain(d1h, K)
    lsh = bos["lsh"].to_numpy()
    lsl = bos["lsl"].to_numpy()
    close = d1h["close"].to_numpy()
    high = d1h["high"].to_numpy()
    low = d1h["low"].to_numpy()

    # ---------- baseline: exactly what step150a did, re-run here ----------
    direction = pd.Series(np.where(el, 1, np.where(es, -1, 0)), index=d1h.index)
    base_entries = mask_to_events(el | es, direction)
    long_frac = int(el.sum()) / max(1, int(el.sum()) + int(es.sum()))
    print(f"\nbreak-bar signals in the first 80% of history: {len(base_entries)} "
          f"(long {int(el.sum())} / short {int(es.sum())})")
    score_cell("BASELINE - enter on the break bar (what round 150 measured)",
               EDGE, d1h, i_tr, i_va, base_entries, stop_builder, target_builder,
               max_hold, f1h, long_frac, k=K)

    # ---------- the one condition added: wait for the retest ----------
    for w in WAIT_WINDOWS:
        trig_l, org_l = wait_for_touch_then_close_back(el, lsh, high, low, close, "long", w)
        trig_s, org_s = wait_for_touch_then_close_back(es, lsl, high, low, close, "short", w)
        nl, ns = int(trig_l.sum()), int(trig_s.sum())
        trig_l.index = d1h.index
        trig_s.index = d1h.index
        dirn = pd.Series(np.where(trig_l, 1, np.where(trig_s, -1, 0)), index=d1h.index)
        ents = mask_to_events(trig_l | trig_s, dirn)
        lf = nl / max(1, nl + ns)
        print(f"\nretest within {w} bars: {len(ents)} entries survive the gate "
              f"(long {nl} / short {ns}) out of {len(base_entries)} break signals")
        score_cell(f"RETEST of the broken level, wait up to {w} bars",
                   EDGE, d1h, i_tr, i_va, ents, stop_builder, target_builder,
                   max_hold, f1h, lf, k=K)

    write_table("step310_table.csv")


if __name__ == "__main__":
    main()
