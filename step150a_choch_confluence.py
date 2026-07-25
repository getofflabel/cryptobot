"""
step150a_choch_confluence.py — ROUND 150, edge 1/5: 1h CHoCH + confluence>=2.

ORIGINAL VALIDATION (round 56, step56_smc_toolkit.py, RESEARCH_LOG.md):
  config: 1h, k=8, base_tool=CHoCH, threshold>=2, target_mult=2.0x,
          max_hold=10 days (240 1h-bars).
  stop  : train_median_stop_pct() — the TRAIN-window MEDIAN of (entry close
          to the CHoCH's own broken swing level) distance, collapsed to
          ONE fixed percentage for the whole run_backtest call (a swept
          number derived FROM structure, not a live per-trade level).
  execution: "maker" (step56_smc_toolkit.py line 130: "execution='maker'
          (the repo standard for [this round])").
  sealed (train $15.45/t x52, val $72.51/t x24) -> SEALED +$99.52/t x16.

TONIGHT'S CHANGE (Morgan's mandate)
  stop  : exits.stop_structure(k=8, n_back=1, use='wick') — the REAL,
          per-trade confirmed swing the CHoCH broke (not a median %).
  target: exits.target_fixed_r(stop, r=2.0) — same 2x-the-stop philosophy,
          sized off the real per-trade stop.
  execution: "taker", always (CostModel default; entry AND every exit pay
          fee+half-spread+slippage — see step150_common.py).
Entry signal (CHoCH direction + the 5-vote confluence counter: 4h bias,
discount/premium, fib-zone membership, swept-pool-in-last-24h, active FVG)
is REUSED VERBATIM from step56_smc_toolkit.py — nothing about WHEN a CHoCH
fires or HOW confluence is counted is under test tonight, only what happens
to the stop/target/execution after.

DISCIPLINE: entry-signal features (bos_chain, confluence votes) are computed
ONCE on the 1h/4h frames TRUNCATED to end of VAL (index i_va) — the sealed
final 20% is never loaded, matching every other step150 script tonight and
step56's own original convention (features computed over the cached history
being used, train/val scoring sliced afterward). Train and val are then
scored as INDEPENDENTLY-SLICED, index-reset frames through step150_common.
run_edge (matching step54/56/58's own score() pattern exactly).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import exits as E
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import days_to_bars, split_points
from step43_daytrade import champ_aligned
from step56_smc_toolkit import (bias_series_4h, bos_chain, equilibrium,
                                fib_entries, fvg_signals, leg_tracker,
                                liquidity_pools, sweep_events)
from step150_common import (chance_baseline, fmt_stats, mask_to_events,
                            run_edge, thickness, trade_stats, verdict_for)

K = 8
TARGET_MULT = 2.0
CONF_TOL, CONF_DEPTH = 0.1, 0.3
CONF_FILL, CONF_EXPIRE_DAYS = 0.5, 10
CONF_FIB_EXPIRE_DAYS = 20
CONF_HOLD_DAYS = 10
CONF_THRESHOLD = 2


def build_entries(d1h_trunc: pd.DataFrame, d4h_trunc: pd.DataFrame):
    bos = bos_chain(d1h_trunc, K)
    discount, premium, eq, lsh, lsl = equilibrium(d1h_trunc, K)
    pool_high, pool_low = liquidity_pools(d1h_trunc, K, CONF_TOL)
    sweep_long, sweep_short = sweep_events(d1h_trunc, pool_high, pool_low, CONF_DEPTH)
    window = days_to_bars(d1h_trunc, 1)   # 24h on 1h bars
    swept_recent_long = (sweep_long.astype(int).rolling(window, min_periods=1)
                         .max().fillna(0).astype(bool))
    swept_recent_short = (sweep_short.astype(int).rolling(window, min_periods=1)
                          .max().fillna(0).astype(bool))
    _, _, _, _, ab, ar = fvg_signals(d1h_trunc, CONF_FILL, days_to_bars(d1h_trunc, CONF_EXPIRE_DAYS))
    bull_low, bull_high, bear_low, bear_high = leg_tracker(
        d1h_trunc, K, days_to_bars(d1h_trunc, CONF_FIB_EXPIRE_DAYS))
    _, _, _, _, _, _, lz, sz = fib_entries(
        d1h_trunc, bull_low, bull_high, bear_low, bear_high, 0.618, 0.79)

    bias4h = bias_series_4h(d4h_trunc)
    bias_1h = champ_aligned(d4h_trunc, bias4h, d1h_trunc)
    bias_long = (bias_1h == 1)
    bias_short = (bias_1h == -1)

    count_long = (bias_long.astype(int) + discount.astype(int) + lz.astype(int)
                 + swept_recent_long.astype(int) + ab.astype(int))
    count_short = (bias_short.astype(int) + premium.astype(int) + sz.astype(int)
                  + swept_recent_short.astype(int) + ar.astype(int))

    choch_long, choch_short = bos["choch_long"], bos["choch_short"]
    el = choch_long & (count_long >= CONF_THRESHOLD)
    es = choch_short & (count_short >= CONF_THRESHOLD)
    return el, es


def stop_builder(tc):
    return E.stop_structure(k=K, n_back=1, buffer_pct=0.0, use="wick")


def target_builder(stop):
    return E.target_fixed_r(stop, r_multiple=TARGET_MULT)


def main():
    print("=" * 70)
    print("STEP150a — 1h CHoCH + confluence>=2 — TAKER + STRUCTURE RE-TEST")
    print("=" * 70)
    d1h_full = fetch_bybit_deep("1h", "BTCUSDT")
    d4h_full = fetch_bybit_deep("4h", "BTCUSDT")
    funding_hist = fetch_funding_history("BTCUSDT")
    f1h_full = align_funding(d1h_full, funding_hist)

    n, i_tr, i_va = split_points(d1h_full)
    print(f"1h: {n} bars total | train->{i_tr} val->{i_va} (sealed {n-i_va} bars NEVER LOADED)")

    d1h = d1h_full.iloc[:i_va].reset_index(drop=True)          # train+val only
    f1h = f1h_full.iloc[:i_va].reset_index(drop=True)
    cutoff_ts = d1h["timestamp"].iloc[-1]
    d4h = d4h_full[d4h_full["timestamp"] <= cutoff_ts].reset_index(drop=True)

    el, es = build_entries(d1h, d4h)
    direction = pd.Series(np.where(el, 1, np.where(es, -1, 0)), index=d1h.index)
    entries_all = mask_to_events(el | es, direction)
    max_hold_bars = days_to_bars(d1h, CONF_HOLD_DAYS)
    print(f"entries found (train+val window): {len(entries_all)} "
         f"(long {int(el.sum())} / short {int(es.sum())}) | max_hold={max_hold_bars} bars")

    def slice_entries(lo, hi):
        return [(i - lo, dr) for i, dr in entries_all if lo <= i < hi]

    tr_candles, tr_entries, tr_fund = d1h.iloc[0:i_tr].reset_index(drop=True), slice_entries(0, i_tr), f1h.iloc[0:i_tr].reset_index(drop=True)
    va_candles, va_entries, va_fund = d1h.iloc[i_tr:i_va].reset_index(drop=True), slice_entries(i_tr, i_va), f1h.iloc[i_tr:i_va].reset_index(drop=True)

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

    long_frac = int(el.sum()) / max(1, int(el.sum()) + int(es.sum()))
    n_events_va = len(va_entries)
    cb = chance_baseline(va_candles, n_events_va, long_frac, stop_builder, target_builder,
                         max_hold_bars, va_fund, "next_open", k=K, draws=100)
    print(f"CHANCE BASELINE (val window, {cb['n_draws']} random-entry draws, "
         f"n={cb['sample_events']} each, {long_frac*100:.0f}% long mix): "
         f"mean exp ${cb['mean_exp']:+,.2f}/trade")
    print(f"EDGE vs CHANCE: ${va_st['expectancy']:+,.2f} vs ${cb['mean_exp']:+,.2f} "
         f"-> {'BEATS' if va_st['expectancy'] > cb['mean_exp'] else 'DOES NOT BEAT'} chance")

    pd.DataFrame(tr_trades + va_trades).to_csv("step150a_table.csv", index=False)
    print("wrote step150a_table.csv")
    return dict(tr=tr_st, va=va_st, verdict=verdict, thickness=th, chance=cb,
               long_frac=long_frac, avg_notional=avg_notional)


if __name__ == "__main__":
    main()
