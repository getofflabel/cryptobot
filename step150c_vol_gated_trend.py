"""
step150c_vol_gated_trend.py — ROUND 150, edge 3/5: 4h trend w/ strict 1.5%
volatility gate (the "ride").

ORIGINAL VALIDATION (round 54, step54_adaptive_ride.py, RESEARCH_LOG.md):
  config: 4h, champion = vol_gated_ma(fast=20, slow=100, min_atr_pct=1.5)
          (SMA20/100 crossover, entries gated to ATR>=1.5% of price, LONG
          ONLY, holds until the trend flips flat).
  stop  : LIVE_SL_PCT = 8.0 — a flat -8% crash stop, a swept round number.
  execution: "maker" (docstring line 60: "long-only, maker execution, real
          funding").
  sealed (R54): FIXED 1.5 (live) 8t, +$401.30/t, +32.1%, DD -12.3%. KEEP
          THE FIXED GATE verdict — "in the grind, selectivity IS the edge."

TONIGHT'S CHANGE
  stop  : exits.stop_structure_trailing(fallback_pct=8.0) — a REAL
          ratcheting structural floor (gold_book.py's live design,
          generalized in exits.py), initialized at the most recent
          confirmed swing low and only ever moving in the trade's favor as
          new confirmed swings print. The 8% fallback is kept ONLY for the
          rare case with no confirmed swing yet at entry (same role the
          flat -8% played originally, now a backstop not the mechanism).
  target: None (target_opposite_signal instead — see below). This is a
          RIDE, not a bracketed trade; it never had a profit target
          originally either.
  exit  : whichever comes first — the structural floor breaking, OR the
          champion trend flipping flat (target_opposite_signal(champ,
          treat_zero_as_exit=True), exactly reproducing the original
          "held -> exit when the trend flips" state machine).
  execution: "taker", always.
Entry signal (vol_gated_ma, fast=20/slow=100, min_atr_pct=1.5, long-only)
is REUSED VERBATIM from strategy.py — nothing about the gate or the trend
definition is under test tonight, only the stop mechanism and execution.

NOTE ON SAMPLE SIZE: this is deliberately a LOW-FREQUENCY edge (~6.5/yr per
MARKET_PLAYBOOKS.md, "the gate's selectivity IS the edge"). The original
sealed test only cleared 8 trades. Expect this retest's train+val to also
run thin — the 30/8 floor is enforced honestly below, not waived.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import exits as E
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import split_points
from strategy import vol_gated_ma
from step150_common import (chance_baseline, fmt_stats, mask_to_events,
                            run_edge, thickness, trade_stats, verdict_for)

CHAMP_KW = dict(fast=20, slow=100, min_atr_pct=1.5)
K = 5             # SeriesCtx pivot lookback for the trailing floor (exits.py default)
FALLBACK_PCT = 8.0    # same magnitude as the live -8% SL, now a backstop only


def stop_builder(tc):
    return E.stop_structure_trailing(buffer_pct=0.0, fallback_pct=FALLBACK_PCT)


def make_target_builder(signal_arr):
    def target_builder(stop):
        return E.target_opposite_signal(signal_arr, treat_zero_as_exit=True)
    return target_builder


def rising_edges(sig01: pd.Series) -> pd.Series:
    """Bars where the long-only 0/1 champion signal turns on (flat -> long).
    Signal is known at that bar's own close (matches vol_gated_ma's own
    causal construction); filled next bar's open, matching every other
    edge tonight and the repo-standard no-lookahead rule."""
    prev = sig01.shift(1).fillna(0.0)
    return (sig01 == 1) & (prev != 1)


def main():
    print("=" * 70)
    print("STEP150c — 4h trend w/ strict 1.5% vol gate — TAKER + STRUCTURE RE-TEST")
    print("=" * 70)
    d4h_full = fetch_bybit_deep("4h", "BTCUSDT")
    funding_hist = fetch_funding_history("BTCUSDT")
    f4h_full = align_funding(d4h_full, funding_hist)

    n, i_tr, i_va = split_points(d4h_full)
    print(f"4h: {n} bars total | train->{i_tr} val->{i_va} (sealed {n-i_va} bars NEVER LOADED)")

    d4h = d4h_full.iloc[:i_va].reset_index(drop=True)
    f4h = f4h_full.iloc[:i_va].reset_index(drop=True)

    champ = vol_gated_ma(d4h, **CHAMP_KW).fillna(0.0)
    entries_mask = rising_edges(champ)
    entries_all = mask_to_events(entries_mask, 1)
    print(f"entries found (train+val window): {len(entries_all)} "
         f"(time-in-market {(champ == 1).mean() * 100:.1f}%)")

    def slice_entries(lo, hi):
        return [(i - lo, dr) for i, dr in entries_all if lo <= i < hi]

    tr_candles, tr_fund = d4h.iloc[0:i_tr].reset_index(drop=True), f4h.iloc[0:i_tr].reset_index(drop=True)
    va_candles, va_fund = d4h.iloc[i_tr:i_va].reset_index(drop=True), f4h.iloc[i_tr:i_va].reset_index(drop=True)
    tr_entries, va_entries = slice_entries(0, i_tr), slice_entries(i_tr, i_va)
    tr_signal = champ.iloc[0:i_tr].reset_index(drop=True).to_numpy()
    va_signal = champ.iloc[i_tr:i_va].reset_index(drop=True).to_numpy()

    tr_trades, tr_skip = run_edge(tr_candles, tr_entries, stop_builder,
                                  make_target_builder(tr_signal), len(tr_candles),
                                  funding_bps=tr_fund, k=K)
    va_trades, va_skip = run_edge(va_candles, va_entries, stop_builder,
                                  make_target_builder(va_signal), len(va_candles),
                                  funding_bps=va_fund, k=K)
    tr_st, va_st = trade_stats(tr_trades), trade_stats(va_trades)

    print(fmt_stats("TRAIN", tr_st), f"| skipped(no structure)={tr_skip}")
    print(fmt_stats("VAL  ", va_st), f"| skipped(no structure)={va_skip}")
    verdict = verdict_for(tr_st, va_st)
    print(f"VERDICT: {verdict}")

    all_trades = tr_trades + va_trades
    avg_notional = float(np.mean([t["notional"] for t in all_trades])) if all_trades else 0.0
    th = thickness(va_st["expectancy"], avg_notional)
    print(f"THICKNESS (val): {th['pct_notional']:.4f}% of notional | "
         f"{th['mult_12bps']:.2f}x task's 12bps round-trip | "
         f"{th['mult_full_18bps']:.2f}x full 18bps CostModel round-trip")

    n_events_va = len(va_entries)
    cb = chance_baseline(va_candles, n_events_va, 1.0, stop_builder,
                         make_target_builder(va_signal), len(va_candles), va_fund,
                         "next_open", k=K, draws=100)
    print(f"CHANCE BASELINE (val window, {cb['n_draws']} random-entry draws, "
         f"n={cb['sample_events']} each, 100% long -- this is a long-only book): "
         f"mean exp ${cb['mean_exp']:+,.2f}/trade")
    print(f"EDGE vs CHANCE: ${va_st['expectancy']:+,.2f} vs ${cb['mean_exp']:+,.2f} "
         f"-> {'BEATS' if va_st['expectancy'] > cb['mean_exp'] else 'DOES NOT BEAT'} chance")

    pd.DataFrame(tr_trades + va_trades).to_csv("step150c_table.csv", index=False)
    print("wrote step150c_table.csv")
    print("NOTE: low-frequency edge by design (~6.5/yr) -- verdict below honestly "
         "enforces the 30/8 trade floor; INSUFFICIENT-SAMPLE is expected and is not FAIL.")
    return dict(tr=tr_st, va=va_st, verdict=verdict, thickness=th, chance=cb,
               avg_notional=avg_notional)


if __name__ == "__main__":
    main()
