"""
step313_news_native_floor.py — ROUND 310, dead edge 4 of 4:
news momentum, first-hour direction.

WHAT OUR CODE ACTUALLY DID (step150e_news_momentum.py, read line by line)
  trigger : a relevant WatcherGuru headline, then the first full 1h bar
            after it. Direction = that bar's own close-versus-open sign.
  entry   : that same bar's own CLOSE.
  stop    : exits.py's GENERIC structure-trailing floor, which starts at
            the most recent CONFIRMED k=5 swing on the protective side as
            of entry, or 8% away if no swing exists yet, and ratchets.
  target  : none, ride the floor.
  hold cap: 24 hours.
  result  : -$8.88 and -$15.25 per trade. FAIL. Win rate 27-33%.

WHAT THE LIVE VERSION ACTUALLY REQUIRES THAT WE DID NOT IMPLEMENT
The initial floor is the entry bar's OWN opposite extreme, not the most
recent confirmed swing. Round 65's N2, the version that was sealed at
+$10.35 per trade and deployed, sets the starting stop just beyond the low
of the reaction bar itself for a long, just beyond its high for a short,
and only then ratchets on confirmed swings. Round 150's own write-up
flagged this substitution as a confound in its own results section and
then reported the number as a verdict anyway.

This is not a cosmetic difference and it is not merely "our bug" either,
it is the practitioner's requirement for event trades specifically. A news
reaction can land anywhere on the chart, including in the middle of a
featureless range where the last confirmed swing is a long way off or, far
worse, immediately adjacent. The reaction candle IS the structure for an
event trade: the level at which the market's reaction to that headline is
proven wrong is the far side of the candle that reacted. Borrowing a
generic swing floor makes the stop distance essentially arbitrary from
trade to trade, which is a clean explanation of the round-150 symptom that
the win rate collapsed to 27%.

THE ONE CONDITION ADDED
The initial protective floor is restored to the entry bar's own opposite
extreme plus a small cushion, ratcheting on confirmed k=5 swings exactly
as before. Everything else stays as round 150 had it, and critically the
COST MODEL STAYS: market orders on entry and on every exit, crossing the
spread and paying slippage. Round 65's own simulator charged the cheaper
resting-limit-order fee on every entry and modelled no spread or slippage
at all, so this run is the honest question that was never asked: does the
REAL news strategy survive REAL trading costs?

The trailing floor is rebuilt here as a local exit method rather than by
editing exits.py, which is a shared library this round must not touch.
"""

from __future__ import annotations

import bisect

import numpy as np
import pandas as pd

import exits as E
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step65_news_eyes import MAX_HOLD_H, build_news_entries, split_points
from step310_common import score_cell, write_table

K = 5
FALLBACK_PCT = 8.0
BUFFERS = (0.1, 0.3)     # the two cushions round 65 itself swept
EDGE = "4 - news momentum, first-hour direction"


def stop_generic_trailing(buffer_pct=0.0):
    """What round 150 measured: floor starts at the most recent confirmed
    swing, or 8% away if there is none."""
    return E.stop_structure_trailing(buffer_pct=buffer_pct, fallback_pct=FALLBACK_PCT)


def stop_reaction_bar_trailing(buffer_pct: float):
    """The LIVE version's floor, restored. Starts just beyond the entry
    bar's own opposite extreme, then ratchets to confirmed k=5 swings that
    print after entry and sit further in the trade's favour. Reads only
    bars at or before i, and only pivots whose confirm index is at or
    before i, so it cannot see the future."""
    def level_fn(tc: E.TradeCtx, i: int):
        e = tc.entry_idx
        if tc.direction > 0:
            floor = float(tc.s.l[e]) * (1 - buffer_pct / 100)
        else:
            floor = float(tc.s.h[e]) * (1 + buffer_pct / 100)
        piv = tc.s.piv_low if tc.direction > 0 else tc.s.piv_high
        hi = bisect.bisect_right(piv["confirm_idx"], i)
        for cidx, price in zip(piv["confirm_idx"][:hi], piv["price"][:hi]):
            if cidx <= e:
                continue
            if tc.direction > 0 and price > floor:
                floor = float(price)
            elif tc.direction < 0 and price < floor:
                floor = float(price)
        return floor
    return E.ExitMethod(f"stop_reaction_bar_trailing(buffer_pct={buffer_pct})",
                        level_fn, style="intrabar_or_close")


def main():
    print("=" * 78)
    print("STEP313 — edge 4: news momentum with the LIVE version's own stop")
    print("(the reaction bar's far side), priced at market-order costs.")
    print("=" * 78)

    btc1h_full = fetch_bybit_deep("1h", "BTCUSDT")
    funding_hist = fetch_funding_history("BTCUSDT")
    news = pd.read_parquet("data_watcherguru_history.parquet")
    news_min, news_max = news["utc_timestamp"].min(), news["utc_timestamp"].max()
    mask = ((btc1h_full["timestamp"] >= news_min - pd.Timedelta(hours=24)) &
            (btc1h_full["timestamp"] <= news_max + pd.Timedelta(hours=24)))
    d_span = btc1h_full[mask].reset_index(drop=True)
    n, i_tr, i_va = split_points(d_span)
    print(f"news-span 1h bars: {n} | first 60% ends {i_tr} | middle 20% ends "
          f"{i_va} | final {n - i_va} bars NEVER LOADED")

    d = d_span.iloc[:i_va].reset_index(drop=True)
    entries = build_news_entries(d, news)
    funding = align_funding(d, funding_hist)
    nl = sum(1 for _, dd in entries if dd > 0)
    lf = nl / max(1, len(entries))
    print(f"news entries in the first 80% of history: {len(entries)} "
          f"(long {nl} / short {len(entries) - nl})")

    # ---------- baseline: exactly what step150e did ----------
    score_cell("BASELINE - generic swing floor (what round 150 measured)",
               EDGE, d, i_tr, i_va, entries, lambda tc: stop_generic_trailing(0.0),
               lambda s: None, MAX_HOLD_H, funding, lf, k=K,
               fill_convention="same_close")

    # ---------- the one condition restored: the reaction bar's own far side ----------
    for b in BUFFERS:
        score_cell(f"REACTION BAR's own far side as the starting floor, cushion {b}%",
                   EDGE, d, i_tr, i_va, entries, lambda tc, b=b: stop_reaction_bar_trailing(b),
                   lambda s: None, MAX_HOLD_H, funding, lf, k=K,
                   fill_convention="same_close")

    write_table("step313_table.csv")


if __name__ == "__main__":
    main()
