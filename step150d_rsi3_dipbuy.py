"""
step150d_rsi3_dipbuy.py — ROUND 150, edge 4/5: 1h RSI3 dip-buy in uptrends
(needs 48h room).

ORIGINAL VALIDATION (live tactical.py "panic-dip" trigger; R43 confirmed the
48h-room requirement — same-day exits kill it):
  config: 1h RSI(3) < 15, gated to the 4h champion (vol_gated_ma fast=20/
          slow=100/min_atr_pct=1.5) == long. Single-slot (tactical.py only
          evaluates a new entry when flat).
  stop  : STOP_PCT = 1.5 (tactical.py line 70) — a flat percentage.
  target: TARGET_PCT = 4.5 (3:1 R) — a flat percentage.
  hold  : MAX_HOLD_H = 48.
  execution: live book fills mix maker/taker per bracket side (tactical.py's
          own _book_exit: 2.0bps on a TP hit, 6.0bps on an SL hit) — not a
          clean taker-always backtest assumption.

TONIGHT'S CHANGE
  stop  : exits.stop_structure(k=5, n_back=1, use='wick') — the real
          confirmed 1h swing low beneath entry (k=5: a fast tactical setup,
          not the slower k=8 used for the 4h-anchored edges above).
  target: exits.target_fixed_r(stop, r=3.0) — the SAME 3:1 R the live book
          already runs, now sized off the real per-trade stop distance.
  execution: "taker", always.
Entry signal (RSI(3)<15 on 1h AND 4h champion long) is REUSED VERBATIM from
strategy.py/tactical.py's own live definitions.
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
from step150_common import (chance_baseline, fmt_stats, mask_to_events,
                            run_edge, thickness, trade_stats, verdict_for)

CHAMP_KW = dict(fast=20, slow=100, min_atr_pct=1.5)
RSI_THRESH = 15
K = 5
TARGET_MULT = 3.0     # matches the live 4.5%/1.5% = 3:1 R
MAX_HOLD_H = 48


def stop_builder(tc):
    return E.stop_structure(k=K, n_back=1, buffer_pct=0.0, use="wick")


def target_builder(stop):
    return E.target_fixed_r(stop, r_multiple=TARGET_MULT)


def main():
    print("=" * 70)
    print("STEP150d — 1h RSI3 dip-buy in uptrends — TAKER + STRUCTURE RE-TEST")
    print("=" * 70)
    d1h_full = fetch_bybit_deep("1h", "BTCUSDT")
    d4h_full = fetch_bybit_deep("4h", "BTCUSDT")
    funding_hist = fetch_funding_history("BTCUSDT")
    f1h_full = align_funding(d1h_full, funding_hist)

    n, i_tr, i_va = split_points(d1h_full)
    print(f"1h: {n} bars total | train->{i_tr} val->{i_va} (sealed {n-i_va} bars NEVER LOADED)")

    d1h = d1h_full.iloc[:i_va].reset_index(drop=True)
    f1h = f1h_full.iloc[:i_va].reset_index(drop=True)
    cutoff_ts = d1h["timestamp"].iloc[-1]
    d4h = d4h_full[d4h_full["timestamp"] <= cutoff_ts].reset_index(drop=True)

    champ4h = vol_gated_ma(d4h, **CHAMP_KW)
    champ_1h = champ_aligned(d4h, champ4h, d1h)
    r3 = rsi(d1h["close"], 3)
    entries_mask = (champ_1h == 1) & (r3 < RSI_THRESH)
    entries_mask = entries_mask.fillna(False)
    entries_all = mask_to_events(entries_mask, 1)
    max_hold_bars = MAX_HOLD_H   # 1h bars
    print(f"raw condition-true bars (train+val window): {len(entries_all)} "
         f"(single-slot busy_until collapses runs of consecutive True bars "
         f"to one entry each, matching tactical.py's own 'only evaluate "
         f"entries when flat' live behavior)")

    def slice_entries(lo, hi):
        return [(i - lo, dr) for i, dr in entries_all if lo <= i < hi]

    tr_candles, tr_fund = d1h.iloc[0:i_tr].reset_index(drop=True), f1h.iloc[0:i_tr].reset_index(drop=True)
    va_candles, va_fund = d1h.iloc[i_tr:i_va].reset_index(drop=True), f1h.iloc[i_tr:i_va].reset_index(drop=True)
    tr_entries, va_entries = slice_entries(0, i_tr), slice_entries(i_tr, i_va)

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

    n_events_va = len(va_entries)
    cb = chance_baseline(va_candles, n_events_va, 1.0, stop_builder, target_builder,
                         max_hold_bars, va_fund, "next_open", k=K, draws=100)
    print(f"CHANCE BASELINE (val window, {cb['n_draws']} random-entry draws, "
         f"n={cb['sample_events']} each, 100% long -- this is a long-only book): "
         f"mean exp ${cb['mean_exp']:+,.2f}/trade")
    print(f"EDGE vs CHANCE: ${va_st['expectancy']:+,.2f} vs ${cb['mean_exp']:+,.2f} "
         f"-> {'BEATS' if va_st['expectancy'] > cb['mean_exp'] else 'DOES NOT BEAT'} chance")

    pd.DataFrame(tr_trades + va_trades).to_csv("step150d_table.csv", index=False)
    print("wrote step150d_table.csv")
    return dict(tr=tr_st, va=va_st, verdict=verdict, thickness=th, chance=cb,
               avg_notional=avg_notional)


if __name__ == "__main__":
    main()
