"""
step150b_hidden_divergence.py — ROUND 150, edge 2/5: 4h HIDDEN RSI divergence.

ORIGINAL VALIDATION (round 58, step58_divergence_mtf.py, RESEARCH_LOG.md):
  config: 4h, RSI14, k=8, buffer 0.35%, target 3x, hold 48h (12 4h-bars),
          champion-gated continuation (long only when 4h champion==uptrend,
          mirrored short in downtrend).
  stop  : swing_stop_pct() — TRAIN-window MEDIAN distance from entry close
          to the qualifying swing extreme (+buffer, capped at 4.0%),
          collapsed to ONE fixed percentage for the whole run_backtest call,
          averaged across long+short occurrences.
  execution: "maker" (MAKER_ROUND_TRIP_BPS used throughout, score(...,
          execution="maker")).
  sealed: train $74.22/t x66, val $31.99/t x24 -> SEALED +$52.03/t x24,
          +12.5%, DD -15.5%. PASS, deployed live.

TONIGHT'S CHANGE
  stop  : exits.stop_structure(k=8, buffer_pct=0.35, use='wick') — the REAL
          per-trade confirmed swing low/high the divergence formed at,
          + the SAME 0.35% buffer the original used, per-trade instead of
          collapsed to a train median.
  target: exits.target_fixed_r(stop, r=3.0) — same 3x-the-stop philosophy.
  execution: "taker", always.
Entry signal (divergence_events: price higher-low / RSI14 lower-low inside
a confirmed 4h uptrend, and the downtrend mirror) is REUSED VERBATIM from
step58_divergence_mtf.py.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import exits as E
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import split_points
from step58_divergence_mtf import divergence_events, hours_to_bars
from strategy import rsi, vol_gated_ma
from step150_common import (chance_baseline, fmt_stats, mask_to_events,
                            run_edge, thickness, trade_stats, verdict_for)

K = 8
BUFFER_PCT = 0.35
TARGET_MULT = 3.0
MAX_HOLD_H = 48
CHAMP_KW = dict(fast=20, slow=100, min_atr_pct=1.5)


def stop_builder(tc):
    return E.stop_structure(k=K, n_back=1, buffer_pct=BUFFER_PCT, use="wick")


def target_builder(stop):
    return E.target_fixed_r(stop, r_multiple=TARGET_MULT)


def main():
    print("=" * 70)
    print("STEP150b — 4h HIDDEN RSI divergence — TAKER + STRUCTURE RE-TEST")
    print("=" * 70)
    d4h_full = fetch_bybit_deep("4h", "BTCUSDT")
    funding_hist = fetch_funding_history("BTCUSDT")
    f4h_full = align_funding(d4h_full, funding_hist)

    n, i_tr, i_va = split_points(d4h_full)
    print(f"4h: {n} bars total | train->{i_tr} val->{i_va} (sealed {n-i_va} bars NEVER LOADED)")

    d4h = d4h_full.iloc[:i_va].reset_index(drop=True)     # train+val only
    f4h = f4h_full.iloc[:i_va].reset_index(drop=True)

    champ4h = vol_gated_ma(d4h, **CHAMP_KW)                # long-only 0/1
    osc = rsi(d4h["close"], 14)
    long_reg, short_reg, long_hid, short_hid, low_ext, high_ext = divergence_events(
        d4h, osc, K, champ4h)

    direction = pd.Series(np.where(long_hid, 1, np.where(short_hid, -1, 0)), index=d4h.index)
    entries_all = mask_to_events(long_hid | short_hid, direction)
    max_hold_bars = hours_to_bars(d4h, MAX_HOLD_H)
    print(f"entries found (train+val window): {len(entries_all)} "
         f"(long {int(long_hid.sum())} / short {int(short_hid.sum())}) | max_hold={max_hold_bars} bars")

    def slice_entries(lo, hi):
        return [(i - lo, dr) for i, dr in entries_all if lo <= i < hi]

    tr_candles, tr_entries, tr_fund = d4h.iloc[0:i_tr].reset_index(drop=True), slice_entries(0, i_tr), f4h.iloc[0:i_tr].reset_index(drop=True)
    va_candles, va_entries, va_fund = d4h.iloc[i_tr:i_va].reset_index(drop=True), slice_entries(i_tr, i_va), f4h.iloc[i_tr:i_va].reset_index(drop=True)

    tr_trades, tr_skip = run_edge(tr_candles, tr_entries, stop_builder, target_builder,
                                  max_hold_bars, funding_bps=tr_fund, k=K)
    va_trades, va_skip = run_edge(va_candles, va_entries, stop_builder, target_builder,
                                  max_hold_bars, funding_bps=va_fund, k=K)
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

    long_frac = int(long_hid.sum()) / max(1, int(long_hid.sum()) + int(short_hid.sum()))
    n_events_va = len(va_entries)
    cb = chance_baseline(va_candles, n_events_va, long_frac, stop_builder, target_builder,
                         max_hold_bars, va_fund, "next_open", k=K, draws=100)
    print(f"CHANCE BASELINE (val window, {cb['n_draws']} random-entry draws, "
         f"n={cb['sample_events']} each, {long_frac*100:.0f}% long mix): "
         f"mean exp ${cb['mean_exp']:+,.2f}/trade")
    print(f"EDGE vs CHANCE: ${va_st['expectancy']:+,.2f} vs ${cb['mean_exp']:+,.2f} "
         f"-> {'BEATS' if va_st['expectancy'] > cb['mean_exp'] else 'DOES NOT BEAT'} chance")

    pd.DataFrame(tr_trades + va_trades).to_csv("step150b_table.csv", index=False)
    print("wrote step150b_table.csv")
    return dict(tr=tr_st, va=va_st, verdict=verdict, thickness=th, chance=cb,
               long_frac=long_frac, avg_notional=avg_notional)


if __name__ == "__main__":
    main()
