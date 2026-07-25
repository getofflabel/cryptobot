"""
step311_hidden_div_confirm.py — ROUND 310, dead edge 2 of 4:
4h hidden RSI divergence (the continuation flavour).

WHAT OUR CODE ACTUALLY DID (step150b_hidden_divergence.py, read line by line)
  trigger : step58's divergence_events(). At the bar where a k=8 swing low
            is CONFIRMED, compare it to the previous confirmed swing low.
            Higher price low with a lower RSI(14) low, while the 4h trend
            gauge says uptrend, fires a long. Mirror for shorts.
  entry   : the very next bar's OPEN. So we entered on the divergence bar
            itself, the moment the pattern was recognised.
  stop    : the real confirmed swing the divergence formed at, plus a
            0.35% cushion.
  target  : 3x the stop distance.
  hold cap: 48 hours, which on 4h bars is only 12 bars.
  sample  : 66 trades in the first 60%, 25 in the middle 20%.
  result  : first 60% +$15.20 per trade, middle 20% -$9.30 per trade. FAIL.
            Median hold sat EXACTLY on the 12-bar cap in both windows.

WHAT PRACTITIONERS OF THIS METHOD REQUIRE THAT WE DID NOT IMPLEMENT
The confirmation close. This is not a guess: our own round 86 found it,
tested it and proved it on the regular flavour of divergence, and the
research log states it in one line — "Do not enter on the divergence bar.
Wait for price to close back through the swing sitting BETWEEN the two
divergent points; that close is the entry." That gate was the only one of
three candidate gates that carried signal beyond Bitcoin. It was applied
to REGULAR divergence and never applied to the HIDDEN flavour, because at
the time hidden divergence was a live, sealed, working edge and nobody
re-opened it. Round 150 then killed hidden divergence while still entering
on the divergence bar. So the exact condition we already proved matters is
the exact condition this edge has never been tested with.

For a hidden bullish divergence the intervening structural level is the
HIGHEST HIGH between the two swing lows, meaning the top of the pullback.
A close above it says the pullback is finished and the trend has actually
resumed, which is the entire premise of a continuation pattern. Entering
on the divergence bar means entering while the pullback may still be
running, which is also a clean explanation of the round-150 symptom that
trades drifted to the 48-hour cap without reaching a 3x target: we were
spending the first chunk of a 12-bar clock waiting for the pullback to
finish rather than riding the resumption.

THE ONE CONDITION ADDED
Entry moves off the divergence bar and onto the first later bar, within a
wait window, that CLOSES above the highest high between the two swing lows
(mirrored for shorts). Nothing else changes: same divergence definition,
same trend gate, same stop method and cushion, same 3x target, same 48
hour cap, same market-order costs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import exits as E
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import confirmed_swings, split_points
from step58_divergence_mtf import hours_to_bars
from strategy import rsi, vol_gated_ma
from step150b_hidden_divergence import (BUFFER_PCT, CHAMP_KW, K, MAX_HOLD_H,
                                        TARGET_MULT)
from step150_common import mask_to_events
from step310_common import score_cell, wait_for_close_through, write_table

WAIT_WINDOWS = (3, 6, 12, 24, 48)   # 4h bars allowed for the confirming close
EDGE = "2 - 4h hidden RSI divergence"


def stop_builder(tc):
    return E.stop_structure(k=K, n_back=1, buffer_pct=BUFFER_PCT, use="wick")


def target_builder(stop):
    return E.target_fixed_r(stop, r_multiple=TARGET_MULT)


def hidden_events_with_confirm_level(d, osc, k, champ):
    """step58.divergence_events' HIDDEN branch, reimplemented locally so it
    can ALSO emit the intervening structural level the confirmation close
    must clear. The long_hid / short_hid masks it returns are bit-for-bit
    the same events step150b traded — that is checked in main() by scoring
    the baseline cell and matching round 150's published numbers."""
    conf_high, conf_low = confirmed_swings(d, k)
    conf_high = conf_high.notna().to_numpy()
    conf_low = conf_low.notna().to_numpy()
    price_h, price_l = d["high"].to_numpy(), d["low"].to_numpy()
    osc_v, champ_v = osc.to_numpy(), champ.to_numpy()
    n = len(d)
    long_hid = np.zeros(n, dtype=bool)
    short_hid = np.zeros(n, dtype=bool)
    conf_lvl_long = np.full(n, np.nan)     # top of the pullback
    conf_lvl_short = np.full(n, np.nan)    # bottom of the bounce
    prev_low = prev_high = None
    for j in range(n):
        if conf_low[j]:
            origin = j - k
            p, o = price_l[origin], osc_v[origin]
            if prev_low is not None and not (np.isnan(o) or np.isnan(prev_low[1])):
                p0, o0, orig0 = prev_low
                if p < p0 and o > o0:
                    pass                                   # regular flavour, not ours
                elif p > p0 and o < o0 and champ_v[j] == 1:
                    long_hid[j] = True
                    conf_lvl_long[j] = price_h[orig0:origin + 1].max()
            prev_low = (p, o, origin)
        if conf_high[j]:
            origin = j - k
            p, o = price_h[origin], osc_v[origin]
            if prev_high is not None and not (np.isnan(o) or np.isnan(prev_high[1])):
                p0, o0, orig0 = prev_high
                if p > p0 and o < o0:
                    pass
                elif p < p0 and o > o0 and champ_v[j] == 0:
                    short_hid[j] = True
                    conf_lvl_short[j] = price_l[orig0:origin + 1].min()
            prev_high = (p, o, origin)
    idx = d.index
    return (pd.Series(long_hid, index=idx), pd.Series(short_hid, index=idx),
            conf_lvl_long, conf_lvl_short)


def main():
    print("=" * 78)
    print("STEP311 — edge 2: hidden divergence, entry moved off the divergence")
    print("bar onto a CONFIRMING CLOSE through the pullback's own high.")
    print("=" * 78)

    d4h_full = fetch_bybit_deep("4h", "BTCUSDT")
    f4h_full = align_funding(d4h_full, fetch_funding_history("BTCUSDT"))
    n, i_tr, i_va = split_points(d4h_full)
    print(f"4h bars: {n} | first 60% ends {i_tr} | middle 20% ends {i_va} | "
          f"final {n - i_va} bars NEVER LOADED")

    d4h = d4h_full.iloc[:i_va].reset_index(drop=True)
    f4h = f4h_full.iloc[:i_va].reset_index(drop=True)

    champ = vol_gated_ma(d4h, **CHAMP_KW)
    osc = rsi(d4h["close"], 14)
    long_hid, short_hid, lvl_l, lvl_s = hidden_events_with_confirm_level(d4h, osc, K, champ)
    close = d4h["close"].to_numpy()
    max_hold = hours_to_bars(d4h, MAX_HOLD_H)

    # ---------- baseline: exactly what step150b did ----------
    dirn = pd.Series(np.where(long_hid, 1, np.where(short_hid, -1, 0)), index=d4h.index)
    base = mask_to_events(long_hid | short_hid, dirn)
    lf = int(long_hid.sum()) / max(1, int(long_hid.sum()) + int(short_hid.sum()))
    print(f"\ndivergence-bar signals in the first 80% of history: {len(base)} "
          f"(long {int(long_hid.sum())} / short {int(short_hid.sum())}) | "
          f"hold cap {max_hold} bars")
    score_cell("BASELINE - enter on the divergence bar (what round 150 measured)",
               EDGE, d4h, i_tr, i_va, base, stop_builder, target_builder,
               max_hold, f4h, lf, k=K)

    # ---------- the one condition added: the confirming close ----------
    for w in WAIT_WINDOWS:
        tl, _ = wait_for_close_through(long_hid, lvl_l, close, "long", w)
        ts, _ = wait_for_close_through(short_hid, lvl_s, close, "short", w)
        tl.index, ts.index = d4h.index, d4h.index
        nl, ns = int(tl.sum()), int(ts.sum())
        dd = pd.Series(np.where(tl, 1, np.where(ts, -1, 0)), index=d4h.index)
        ents = mask_to_events(tl | ts, dd)
        print(f"\nconfirming close within {w} bars: {len(ents)} entries survive "
              f"(long {nl} / short {ns}) out of {len(base)} divergence signals")
        score_cell(f"CONFIRMING CLOSE through the pullback high, wait up to {w} bars",
                   EDGE, d4h, i_tr, i_va, ents, stop_builder, target_builder,
                   max_hold, f4h, nl / max(1, nl + ns), k=K)

    write_table("step311_table.csv")


if __name__ == "__main__":
    main()
