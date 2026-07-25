"""
step312_rsi3_confirm.py — ROUND 310, dead edge 3 of 4:
1h RSI(3) dip-buy inside a 4h uptrend.

WHAT OUR CODE ACTUALLY DID (step150d_rsi3_dipbuy.py, read line by line)
  trigger : 1h RSI(3) below 15 while the 4h trend gauge says uptrend.
  entry   : the very next bar's OPEN. So we bought while the dip was still
            in progress, with no evidence it had stopped falling.
  stop    : the most recent confirmed k=5 swing low beneath entry.
  target  : 3x the stop distance.
  hold cap: 48 hours.
  sample  : 167 trades in the first 60%, 139 in the middle 20%.
  result  : -$70.09 and -$69.54 per trade. Both windows negative, and WORSE
            than entering at random times in the same window (-$28.22).

WHAT PRACTITIONERS OF THIS METHOD REQUIRE THAT WE DID NOT IMPLEMENT
Do not buy while it is still falling. Every version of buy-the-dip that is
actually taught with a protective stop attached requires some evidence the
fall has stopped before you commit: a bar that closes back above the prior
bar's high, the oscillator turning back up through its threshold, a higher
low printing. The reason is mechanical, not folklore, and our own round-150
autopsy named it exactly: if you buy while price is still making new lows,
the nearest confirmed swing low is BEHIND you and inches away, so a stop
placed at real structure is inside the noise and gets clipped constantly.
Our measured win rate collapsed to 41%, against roughly 57% under the live
bot's flat-percentage bracket. Buying the reversal bar instead of the
falling bar puts the low in place BEHIND the entry, which is the only
arrangement in which a swing-low stop means anything at all.

This is the same shape as the condition round 86 proved on divergence: the
entry belongs on the confirming bar, not on the signal bar.

THE ONE CONDITION ADDED
Entry moves off the RSI(3)-below-15 bar and onto the first later bar,
within a wait window, whose CLOSE finishes above the signal bar's own HIGH.
That is the upward turn, priced. Nothing else changes: same oscillator and
threshold, same 4h trend gate, same stop method, same 3x target, same 48
hour cap, same market-order costs, same risk-based sizing.

A SECOND CELL IS RUN FOR HONESTY, NOT FOR CHERRY-PICKING: the same idea
expressed through the oscillator instead of through price (RSI(3) crossing
back up through 25). If the mechanism is real, both spellings of "it turned
back up" should move the result the same way. If only one does, that is a
warning sign, and it is reported as one.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import exits as E
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import split_points
from step43_daytrade import champ_aligned
from strategy import rsi, vol_gated_ma
from step150d_rsi3_dipbuy import CHAMP_KW, K, MAX_HOLD_H, RSI_THRESH, TARGET_MULT
from step150_common import mask_to_events
from step310_common import score_cell, wait_for_close_through, write_table

WAIT_WINDOWS = (3, 6, 12)      # 1h bars allowed for the turn to show up
RSI_RECOVER = 25
EDGE = "3 - 1h RSI(3) dip-buy in a 4h uptrend"


def stop_builder(tc):
    return E.stop_structure(k=K, n_back=1, buffer_pct=0.0, use="wick")


def target_builder(stop):
    return E.target_fixed_r(stop, r_multiple=TARGET_MULT)


def first_true_within(event_mask: pd.Series, cond: pd.Series, max_wait: int):
    """First bar strictly AFTER the signal bar, within max_wait bars, where
    `cond` is true. Used for the oscillator spelling of the same idea."""
    n = len(cond)
    cv = cond.fillna(False).to_numpy()
    out = np.zeros(n, dtype=bool)
    for j in np.flatnonzero(event_mask.fillna(False).to_numpy()):
        for t in range(j + 1, min(n, j + 1 + max_wait)):
            if cv[t]:
                out[t] = True
                break
    return pd.Series(out, index=range(n))


def main():
    print("=" * 78)
    print("STEP312 — edge 3: RSI(3) dip-buy, entry moved off the falling bar")
    print("onto the bar that actually turns back up. Market orders throughout.")
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

    champ4h = vol_gated_ma(d4h, **CHAMP_KW)
    champ_1h = champ_aligned(d4h, champ4h, d1h)
    r3 = rsi(d1h["close"], 3)
    sig = ((champ_1h == 1) & (r3 < RSI_THRESH)).fillna(False)
    close = d1h["close"].to_numpy()
    high = d1h["high"].to_numpy()

    # ---------- baseline: exactly what step150d did ----------
    base = mask_to_events(sig, 1)
    print(f"\ndip signals in the first 80% of history: {len(base)} (all long)")
    score_cell("BASELINE - buy the falling bar (what round 150 measured)",
               EDGE, d1h, i_tr, i_va, base, stop_builder, target_builder,
               MAX_HOLD_H, f1h, 1.0, k=K)

    # ---------- the one condition added: wait for the upward turn ----------
    for w in WAIT_WINDOWS:
        trig, _ = wait_for_close_through(sig, high, close, "long", w)
        trig.index = d1h.index
        ents = mask_to_events(trig, 1)
        print(f"\nclose back above the signal bar's high within {w} bars: "
              f"{len(ents)} entries survive out of {len(base)} dip signals")
        score_cell(f"TURN CONFIRMED IN PRICE - close above the signal bar's high, "
                   f"wait up to {w} bars", EDGE, d1h, i_tr, i_va, ents,
                   stop_builder, target_builder, MAX_HOLD_H, f1h, 1.0, k=K)

    # ---------- the same idea spelled through the oscillator ----------
    recovered = (r3 > RSI_RECOVER) & (r3.shift(1) <= RSI_RECOVER)
    for w in (6,):
        trig = first_true_within(sig, recovered, w)
        trig.index = d1h.index
        ents = mask_to_events(trig, 1)
        print(f"\nRSI(3) crossing back up through {RSI_RECOVER} within {w} bars: "
              f"{len(ents)} entries survive out of {len(base)} dip signals")
        score_cell(f"TURN CONFIRMED IN THE OSCILLATOR - RSI(3) back above "
                   f"{RSI_RECOVER}, wait up to {w} bars", EDGE, d1h, i_tr, i_va,
                   ents, stop_builder, target_builder, MAX_HOLD_H, f1h, 1.0, k=K)

    write_table("step312_table.csv")


if __name__ == "__main__":
    main()
