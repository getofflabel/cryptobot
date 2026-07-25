"""
step112_oil_family_sweep.py — Round 112: PORT CRYPTO-VALIDATED SHAPES ONTO
OIL, thresholds re-derived from oil's own distribution.

Morgan's mandate (2026-07-25 night, after the step110 stand-down verdict):
oil needs a family map comparable to BTC's ~30-family program. This script
covers the FIRST batch — six shapes proven (or previously tested) on
crypto/gold/SPX, ported onto CL=F with every ACTUAL price/vol threshold
recomputed on oil's own train-window distribution. Structural design
choices that are not themselves a tuned distribution number (swing
lookback k, confluence vote count, R-multiples, MA lengths) are kept as
the shape's own design and stated as such — only real distribution-tuned
numbers (ATR gates, stop caps, vol thresholds) are re-derived. Every
family states plainly which numbers were kept and which were replaced.

ENGINE: step150_common.run_edge — the SAME harness Morgan had built
tonight for the BTC re-test (taker execution always, exits.py structural
stops via SeriesCtx/TradeCtx, fixed-fractional risk sizing, chance
baseline via random-entry draws with the identical exit apparatus,
thickness in %notional AND multiples of round-trip cost). REUSED
UNCHANGED — no second engine invented for oil.

DATA: CL=F 1h (data_oil_CL_1h.parquet, 2024-03->2026-07) resampled to 4h/
1d where a family's source shape used a higher timeframe
(step73_video.resample_ohlc, imported unchanged). No funding series
exists for a dated future — every call passes funding_bps=None
(tradfi_engine.py's own documented convention for the same reason).

FAMILIES THIS ROUND (numbers replaced stated inline in each function):
  1. CHoCH (k=8) + confluence>=2, 1h/4h (round 56's BTC shape) — structural
     stop (exits.stop_structure, unchanged design) instead of round 56's
     original train-median-%; CONF_TOL/CONF_DEPTH/CONF_FILL kept as
     structural tolerances (they gate WHICH pivot counts as a pool/FVG
     touch, not a P&L threshold).
  2. 4h hidden RSI(14) divergence, k=8 (round 58's BTC shape) — champion
     4h trend context uses min_atr_pct RE-DERIVED from oil's own 4h TRAIN
     median ATR% (was BTC's fixed 1.5%); structural stop via
     exits.stop_structure instead of round 58's swing-median-%.
  3. 4h vol-gated trend, MA20/100 (round 4/step190a's BTC shape) —
     min_atr_pct gate RE-DERIVED from oil's own 4h TRAIN median ATR%
     (was BTC's fixed 1.5%); exit is exits.stop_chandelier (ATR-trailing,
     ratchets with the trend) instead of the source's flat -8% SL.
  4. 1h RSI3<10 washout dip-buy (daily_pick.py's live crypto shape,
     ALREADY the entry half of what step110 found dead as a full system)
     — stop is pure exits.stop_atr(mult=1.0), the flat 1.0% CAP dropped
     entirely (step110 already showed that cap binds on 19% of oil trades
     and is exactly the "swept percentage" the evidence bar forbids); RSI
     10/90 extremes kept as oscillator design, not re-derived (RSI is
     already self-normalizing 0-100, not a price/vol threshold).
  5. Donchian(20/55) breakout + REAL structure-trailing exit (gold_book.py's
     live shape, exits.stop_structure_trailing, K=5 unchanged) on oil 1h
     AND 1d — round 78 tested an approximation of this on daily data
     ("directionally real... fires 3.4/yr") and found it LOSES on 1h;
     this re-runs both under exits.py's real live-identical exit and
     today's taker-cost/structural-stop harness.
  6. RSI2<5 dip-buy above SMA200 (round 60's SPX shape), oil 1d — exit is
     exits.target_opposite_signal(close>SMA5 or RSI2>65) paired with a
     REAL structural backstop (exits.stop_structure) instead of round 78's
     original run (which used a swept-% stop and already found FAIL on
     oil, both timeframes) — re-run once more under the structural-stop
     standard for a clean confirmation/refutation.

Each family appends ONE line to step110_family_map.md: name, verdict,
key number, chance baseline, thickness multiple.

RESEARCH ONLY. No commits, no live orders, no live-file edits. Writes
step112_oil_family_sweep.py (this file), step112_results.md,
step112_table.csv, and appends to step110_family_map.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import exits as E
import strategy as STRAT
from step41_shorts import confirmed_swings
from step43_daytrade import champ_aligned, day_trade_signal, hours_to_bars
from step56_smc_toolkit import (
    CONF_DEPTH, CONF_EXPIRE_DAYS, CONF_FIB_EXPIRE_DAYS, CONF_FILL,
    CONF_HOLD_DAYS, CONF_TOL, bias_series_4h, bos_chain, equilibrium,
    fib_entries, fvg_signals, leg_tracker, liquidity_pools, sweep_events,
)
from step58_divergence_mtf import divergence_events
from step73_video import resample_ohlc
from step150_common import (chance_baseline, fmt_stats, mask_to_events,
                            run_edge, split_points, thickness, trade_stats,
                            verdict_for)

FAMILY_MAP_PATH = "step110_family_map.md"


def append_family_line(line: str):
    with open(FAMILY_MAP_PATH, "a") as fh:
        fh.write(line.rstrip("\n") + "\n")


def days_to_bars_generic(d: pd.DataFrame, days: float) -> int:
    t = pd.DatetimeIndex(d["timestamp"])
    bar_h = float((t[1:] - t[:-1]).total_seconds().min() / 3600) if len(t) > 1 else 1.0
    return max(1, round(days * 24 / bar_h))


def load_oil():
    d1h = pd.read_parquet("data_oil_CL_1h.parquet").reset_index(drop=True)
    d1d = pd.read_parquet("data_oil_CL_1d.parquet").reset_index(drop=True)
    d4h = resample_ohlc(d1h, "4h")
    return d1h, d4h, d1d


def report_and_log(family_key: str, tf: str, config_note: str, tr, va,
                   replaced_note: str, extra_note: str = ""):
    tr_st, va_st = trade_stats(tr), trade_stats(va)
    verdict = verdict_for(tr_st, va_st)
    all_trades = tr + va
    avg_not = float(np.mean([t["notional"] for t in all_trades])) if all_trades else 0.0
    th = thickness(va_st["expectancy"], avg_not) if va_st["n"] else \
        dict(pct_notional=float("nan"), mult_12bps=float("nan"), mult_full_18bps=float("nan"))
    print(f"\n--- {family_key} [{tf}] {config_note} ---")
    print(f"  numbers replaced: {replaced_note}")
    print(" ", fmt_stats("TRAIN", tr_st))
    print(" ", fmt_stats("VAL  ", va_st))
    print(f"  THICKNESS(val): {th['pct_notional']:.4f}% notional | "
         f"{th['mult_12bps']:.2f}x 12bps | {th['mult_full_18bps']:.2f}x full CostModel")
    print(f"  VERDICT: {verdict}")
    if extra_note:
        print(f"  {extra_note}")
    return dict(family=family_key, tf=tf, config=config_note,
               tr_n=tr_st["n"], tr_exp=tr_st["expectancy"],
               va_n=va_st["n"], va_exp=va_st["expectancy"],
               thickness_12bps=th["mult_12bps"], thickness_full=th["mult_full_18bps"],
               verdict=verdict, replaced=replaced_note), tr_st, va_st, th, verdict


def log_family_map(idx: str, name: str, verdict: str, key_number: str,
                   chance_note: str, thickness_note: str):
    append_family_line(
        f"- **{idx}. {name}** — {verdict} | {key_number} | chance baseline: "
        f"{chance_note} | thickness: {thickness_note}")


# ===========================================================================
# FAMILY 1 — CHoCH k8 + confluence>=2 (1h/4h), structural stop
# ===========================================================================

K1 = 8
TARGET_MULT_1 = 2.0
CONF_THRESHOLD_1 = 2


def build_choch_entries(d1h, d4h):
    bos = bos_chain(d1h, K1)
    discount, premium, eq, lsh, lsl = equilibrium(d1h, K1)
    pool_high, pool_low = liquidity_pools(d1h, K1, CONF_TOL)
    sweep_long, sweep_short = sweep_events(d1h, pool_high, pool_low, CONF_DEPTH)
    window = hours_to_bars(d1h, 24)
    swept_recent_long = (sweep_long.astype(int).rolling(window, min_periods=1)
                         .max().fillna(0).astype(bool))
    swept_recent_short = (sweep_short.astype(int).rolling(window, min_periods=1)
                          .max().fillna(0).astype(bool))
    _, _, _, _, ab, ar = fvg_signals(d1h, CONF_FILL, days_to_bars_generic(d1h, CONF_EXPIRE_DAYS))
    bull_low, bull_high, bear_low, bear_high = leg_tracker(
        d1h, K1, days_to_bars_generic(d1h, CONF_FIB_EXPIRE_DAYS))
    _, _, _, _, _, _, lz, sz = fib_entries(
        d1h, bull_low, bull_high, bear_low, bear_high, 0.618, 0.79)

    bias4h = bias_series_4h(d4h)
    bias_1h = champ_aligned(d4h, bias4h, d1h)
    bias_long, bias_short = (bias_1h == 1), (bias_1h == -1)

    count_long = (bias_long.astype(int) + discount.astype(int) + lz.astype(int)
                 + swept_recent_long.astype(int) + ab.astype(int))
    count_short = (bias_short.astype(int) + premium.astype(int) + sz.astype(int)
                  + swept_recent_short.astype(int) + ar.astype(int))
    choch_long, choch_short = bos["choch_long"], bos["choch_short"]
    el = choch_long & (count_long >= CONF_THRESHOLD_1)
    es = choch_short & (count_short >= CONF_THRESHOLD_1)
    return el, es


def family1(d1h, d4h):
    n, i_tr, i_va = split_points(d1h)
    el, es = build_choch_entries(d1h.iloc[:i_va].reset_index(drop=True),
                                 d4h[d4h["timestamp"] <= d1h["timestamp"].iloc[i_va - 1]].reset_index(drop=True))
    direction = pd.Series(np.where(el, 1, np.where(es, -1, 0)))
    entries_all = mask_to_events(el | es, direction)
    n_events = len(entries_all)
    if n_events == 0:
        log_family_map("1", "CHoCH k8 + confluence>=2 (1h/4h)", "FAIL",
                       "0 qualifying events on oil train+val", "n/a", "n/a")
        print("\n--- FAMILY 1: CHoCH+confluence — ZERO events, FAIL ---")
        return None

    def stop_builder(tc):
        return E.stop_structure(k=K1, n_back=1, buffer_pct=0.0, use="wick")

    def target_builder(stop):
        return E.target_fixed_r(stop, r_multiple=TARGET_MULT_1)

    max_hold_bars = days_to_bars_generic(d1h, CONF_HOLD_DAYS)
    tr_e = [(i, dr) for i, dr in entries_all if i < i_tr]
    va_e = [(i - i_tr, dr) for i, dr in entries_all if i_tr <= i < i_va]
    tr_c = d1h.iloc[0:i_tr].reset_index(drop=True)
    va_c = d1h.iloc[i_tr:i_va].reset_index(drop=True)
    tr, _ = run_edge(tr_c, tr_e, stop_builder, target_builder, max_hold_bars, k=K1)
    va, _ = run_edge(va_c, va_e, stop_builder, target_builder, max_hold_bars, k=K1)

    row, tr_st, va_st, th, verdict = report_and_log(
        "1_CHoCH_confluence", "1h/4h", f"k={K1} thresh>=2 tgt={TARGET_MULT_1}x",
        tr, va, "stop: exits.stop_structure (was round-56's train-median-% swept stop). "
                "CONF_TOL/CONF_DEPTH/CONF_FILL kept (pivot-matching tolerances, not P&L thresholds).")

    long_frac = el.iloc[:i_va].sum() / max(1, (el.iloc[:i_va].sum() + es.iloc[:i_va].sum()))
    cb = chance_baseline(va_c, len(va_e), long_frac, stop_builder, target_builder,
                         max_hold_bars, None, "next_open", k=K1, draws=100)
    beats = va_st["expectancy"] > cb["mean_exp"]
    print(f"  CHANCE (val, {cb['n_draws']} draws): ${cb['mean_exp']:+.2f}/t vs real "
         f"${va_st['expectancy']:+.2f}/t -> {'BEATS' if beats else 'DOES NOT BEAT'} chance")
    log_family_map("1", "CHoCH k8 + confluence>=2 (1h/4h)", verdict,
                   f"val {va_st['n']}t ${va_st['expectancy']:+.2f}/t (train {tr_st['n']}t "
                   f"${tr_st['expectancy']:+.2f}/t)",
                   f"random-entry mean ${cb['mean_exp']:+.2f}/t -> real "
                   f"{'beats' if beats else 'does NOT beat'} chance",
                   f"{th['mult_full_18bps']:+.2f}x full round-trip cost")
    return row


# ===========================================================================
# FAMILY 2 — 4h hidden RSI(14) divergence, k=8, structural stop
# ===========================================================================

def family2(d4h):
    n, i_tr, i_va = split_points(d4h)
    atr_pct_4h = STRAT.atr(d4h, 14) / d4h["close"] * 100
    min_atr_pct_oil = float(atr_pct_4h.iloc[:i_tr].median())  # RE-DERIVED (was BTC's 1.5%)
    champ4h = STRAT.vol_gated_ma(d4h, fast=20, slow=100, min_atr_pct=min_atr_pct_oil)
    osc = STRAT.rsi(d4h["close"], 14)
    k = 8
    long_reg, short_reg, long_hid, short_hid, low_ext, high_ext = divergence_events(d4h, osc, k, champ4h)
    el, es = long_hid, short_hid
    n_events_tv = int(el.iloc[:i_va].sum() + es.iloc[:i_va].sum())
    if n_events_tv == 0:
        log_family_map("2", "4h hidden RSI(14) divergence k8", "FAIL",
                       "0 qualifying swings on oil train+val", "n/a", "n/a")
        print("\n--- FAMILY 2: hidden divergence — ZERO events, FAIL ---")
        return None

    def stop_builder(tc):
        return E.stop_structure(k=k, n_back=1, buffer_pct=0.0, use="wick")

    def target_builder(stop):
        return E.target_fixed_r(stop, r_multiple=3.0)

    max_hold_bars = hours_to_bars(d4h, 48)
    entries_all = mask_to_events(el | es, pd.Series(np.where(el, 1, np.where(es, -1, 0))))
    tr_e = [(i, dr) for i, dr in entries_all if i < i_tr]
    va_e = [(i - i_tr, dr) for i, dr in entries_all if i_tr <= i < i_va]
    tr_c, va_c = d4h.iloc[0:i_tr].reset_index(drop=True), d4h.iloc[i_tr:i_va].reset_index(drop=True)
    tr, _ = run_edge(tr_c, tr_e, stop_builder, target_builder, max_hold_bars, k=k)
    va, _ = run_edge(va_c, va_e, stop_builder, target_builder, max_hold_bars, k=k)

    row, tr_st, va_st, th, verdict = report_and_log(
        "2_hidden_RSI_divergence", "4h", "RSI14 k8 tgt3x hold48h",
        tr, va, f"champion vol-gate min_atr_pct={min_atr_pct_oil:.3f}% (oil 4h TRAIN median "
                f"ATR%, was BTC's fixed 1.5%). stop: exits.stop_structure (was round-58's "
                f"swing-median-% stop).")
    long_frac = el.iloc[:i_va].sum() / max(1, n_events_tv)
    cb = chance_baseline(va_c, len(va_e), long_frac, stop_builder, target_builder,
                         max_hold_bars, None, "next_open", k=k, draws=100)
    beats = va_st["expectancy"] > cb["mean_exp"]
    print(f"  CHANCE (val, {cb['n_draws']} draws): ${cb['mean_exp']:+.2f}/t vs real "
         f"${va_st['expectancy']:+.2f}/t -> {'BEATS' if beats else 'DOES NOT BEAT'} chance")
    log_family_map("2", "4h hidden RSI(14) divergence k8", verdict,
                   f"val {va_st['n']}t ${va_st['expectancy']:+.2f}/t (train {tr_st['n']}t "
                   f"${tr_st['expectancy']:+.2f}/t)",
                   f"random-entry mean ${cb['mean_exp']:+.2f}/t -> real "
                   f"{'beats' if beats else 'does NOT beat'} chance",
                   f"{th['mult_full_18bps']:+.2f}x full round-trip cost")
    return row


# ===========================================================================
# FAMILY 3 — 4h vol-gated trend, MA20/100, ATR-chandelier exit
# ===========================================================================

def family3(d4h):
    n, i_tr, i_va = split_points(d4h)
    atr_pct_4h = STRAT.atr(d4h, 14) / d4h["close"] * 100
    min_atr_pct_oil = float(atr_pct_4h.iloc[:i_tr].median())   # RE-DERIVED (was BTC's 1.5%)
    sig = STRAT.vol_gated_ma(d4h, fast=20, slow=100, min_atr_pct=min_atr_pct_oil)
    sig_v = sig.fillna(0).to_numpy()
    changes = np.flatnonzero(np.diff(np.concatenate([[0], sig_v])) != 0)
    entries_all = [(int(i) - 1, int(sig_v[i])) for i in changes if sig_v[i] != 0 and i > 0]

    def stop_builder(tc):
        return E.stop_chandelier(mult=3.0)

    max_hold_bars = n   # ride the trend — chandelier stop is the real exit

    tr_e = [(i, dr) for i, dr in entries_all if i < i_tr]
    va_e = [(i - i_tr, dr) for i, dr in entries_all if i_tr <= i < i_va]
    tr_c, va_c = d4h.iloc[0:i_tr].reset_index(drop=True), d4h.iloc[i_tr:i_va].reset_index(drop=True)
    tr, _ = run_edge(tr_c, tr_e, stop_builder, None, max_hold_bars)
    va, _ = run_edge(va_c, va_e, stop_builder, None, max_hold_bars)

    row, tr_st, va_st, th, verdict = report_and_log(
        "3_vol_gated_trend", "4h", "MA20/100 chandelier(3xATR) exit",
        tr, va, f"vol gate min_atr_pct={min_atr_pct_oil:.3f}% (oil 4h TRAIN median ATR%, "
                f"was BTC's fixed 1.5%). exit: exits.stop_chandelier (was source's flat -8% SL).")
    time_in_mkt = float((sig.fillna(0) != 0).mean() * 100)
    print(f"  time-in-market: {time_in_mkt:.1f}% of 4h bars | oil train median ATR%={min_atr_pct_oil:.3f}%")
    log_family_map("3", "4h vol-gated trend MA20/100 (chandelier exit)", verdict,
                   f"val {va_st['n']}t ${va_st['expectancy']:+.2f}/t (train {tr_st['n']}t "
                   f"${tr_st['expectancy']:+.2f}/t)",
                   "N/A — trend state-machine, not fixed-hold events (time-in-market "
                   f"{time_in_mkt:.1f}% reported instead per step190a's own precedent)",
                   f"{th['mult_full_18bps']:+.2f}x full round-trip cost")
    return row


# ===========================================================================
# FAMILY 4 — 1h RSI3<10 washout dip-buy, pure ATR stop (cap dropped)
# ===========================================================================

def family4(d1h, d1d):
    n, i_tr, i_va = split_points(d1h)
    r3 = STRAT.rsi(d1h["close"], 3)
    sma20 = d1d["close"].rolling(20).mean()
    sma50 = d1d["close"].rolling(50).mean()
    trend1d = pd.Series(np.select(
        [(d1d["close"] > sma20) & (sma20 > sma50), (d1d["close"] < sma20) & (sma20 < sma50)],
        ["up", "down"], default="none"), index=d1d.index)
    avail = pd.DataFrame({"timestamp": d1d["timestamp"] + pd.Timedelta(hours=24),
                          "trend": trend1d.to_numpy()}).sort_values("timestamp")
    merged = pd.merge_asof(d1h[["timestamp"]].sort_values("timestamp"), avail,
                           on="timestamp", direction="backward")
    trend1d_on_1h = merged["trend"].fillna("none").reset_index(drop=True)
    turn_up = (d1h["close"] > d1h["open"]) & (d1h["close"] > d1h["close"].shift(1))
    turn_down = (d1h["close"] < d1h["open"]) & (d1h["close"] < d1h["close"].shift(1))
    el = (r3 < 10) & (trend1d_on_1h == "up") & turn_up
    es = (r3 > 90) & (trend1d_on_1h == "down") & turn_down
    el, es = el.fillna(False), es.fillna(False)

    def stop_builder(tc):
        return E.stop_atr(mult=1.0)

    def target_builder(stop):
        return E.target_fixed_r(stop, r_multiple=1.5)

    max_hold_bars = 4
    entries_all = mask_to_events(el | es, pd.Series(np.where(el, 1, np.where(es, -1, 0))))
    tr_e = [(i, dr) for i, dr in entries_all if i < i_tr]
    va_e = [(i - i_tr, dr) for i, dr in entries_all if i_tr <= i < i_va]
    tr_c, va_c = d1h.iloc[0:i_tr].reset_index(drop=True), d1h.iloc[i_tr:i_va].reset_index(drop=True)
    tr, _ = run_edge(tr_c, tr_e, stop_builder, target_builder, max_hold_bars)
    va, _ = run_edge(va_c, va_e, stop_builder, target_builder, max_hold_bars)

    row, tr_st, va_st, th, verdict = report_and_log(
        "4_RSI3_washout_dipbuy", "1h", "RSI3<10/>90 1d-trend-gate turn-guard hold4h",
        tr, va, "stop: pure exits.stop_atr(mult=1.0), the crypto shape's flat 1.0% CAP "
                "DROPPED ENTIRELY (step110 showed it binds 19% of the time on oil — a "
                "swept percentage by construction). RSI 10/90 kept (self-normalizing "
                "oscillator bounds, not a price/vol threshold).")
    n_ev = len(va_e)
    long_frac = el.iloc[i_tr:i_va].sum() / max(1, n_ev)
    cb = chance_baseline(va_c, n_ev, long_frac, stop_builder, target_builder,
                         max_hold_bars, None, "next_open", draws=100)
    beats = va_st["expectancy"] > cb["mean_exp"]
    print(f"  CHANCE (val, {cb['n_draws']} draws): ${cb['mean_exp']:+.2f}/t vs real "
         f"${va_st['expectancy']:+.2f}/t -> {'BEATS' if beats else 'DOES NOT BEAT'} chance")
    log_family_map("4", "1h RSI3 washout dip-buy (pure ATR stop, cap dropped)", verdict,
                   f"val {va_st['n']}t ${va_st['expectancy']:+.2f}/t (train {tr_st['n']}t "
                   f"${tr_st['expectancy']:+.2f}/t)",
                   f"random-entry mean ${cb['mean_exp']:+.2f}/t -> real "
                   f"{'beats' if beats else 'does NOT beat'} chance",
                   f"{th['mult_full_18bps']:+.2f}x full round-trip cost")
    return row


# ===========================================================================
# FAMILY 5 — Donchian(20/55) breakout + REAL structure-trailing exit
# (gold_book.py's live shape) on oil 1h AND 1d
# ===========================================================================

def family5(d, tag, tf, n_donch):
    n, i_tr, i_va = split_points(d)
    hi = d["high"].rolling(n_donch).max().shift(1)
    lo = d["low"].rolling(n_donch).min().shift(1)
    el = d["close"] > hi
    es = d["close"] < lo
    el, es = el.fillna(False), es.fillna(False)

    def stop_builder(tc):
        return E.stop_structure_trailing(buffer_pct=0.0, fallback_pct=5.0)

    max_hold_bars = n   # trail-only exit rides until stopped

    entries_all = mask_to_events(el | es, pd.Series(np.where(el, 1, np.where(es, -1, 0))))
    tr_e = [(i, dr) for i, dr in entries_all if i < i_tr]
    va_e = [(i - i_tr, dr) for i, dr in entries_all if i_tr <= i < i_va]
    tr_c, va_c = d.iloc[0:i_tr].reset_index(drop=True), d.iloc[i_tr:i_va].reset_index(drop=True)
    tr, _ = run_edge(tr_c, tr_e, stop_builder, None, max_hold_bars)
    va, _ = run_edge(va_c, va_e, stop_builder, None, max_hold_bars)

    key = f"5_donchian{n_donch}_structure_trail_{tag}"
    row, tr_st, va_st, th, verdict = report_and_log(
        key, tf, f"donchian({n_donch}) + structure-trailing exit (K=5, gold_book.py live shape)",
        tr, va, "unchanged shape (gold_book.py's own live exit, K=5) — this family is a "
                "PORT OF STRUCTURE, no percentage threshold to re-derive; donchian(20/55) "
                "kept as gold's own structural lookback design.")
    log_family_map(f"5-{tag}-{n_donch}", f"Donchian({n_donch}) + structure-trail ({tf})", verdict,
                   f"val {va_st['n']}t ${va_st['expectancy']:+.2f}/t (train {tr_st['n']}t "
                   f"${tr_st['expectancy']:+.2f}/t)",
                   "N/A — trend/breakout state-machine (see family 3's own note)",
                   f"{th['mult_full_18bps']:+.2f}x full round-trip cost")
    return row


# ===========================================================================
# FAMILY 6 — RSI2<5 dip-buy above SMA200 (SPX shape), structural backstop
# ===========================================================================

def family6(d1d):
    n, i_tr, i_va = split_points(d1d)
    rsi2 = STRAT.rsi(d1d["close"], 2)
    sma200 = d1d["close"].rolling(200).mean()
    sma5 = d1d["close"].rolling(5).mean()
    el = (rsi2 < 5) & (d1d["close"] > sma200)
    el = el.fillna(False)
    es = pd.Series(False, index=d1d.index)   # long-only, matching round 60's own shape

    exit_sig = np.where((d1d["close"] > sma5) | (rsi2 > 65), 0, 1)  # 0 = flip-flat signal

    def stop_builder(tc):
        return E.stop_structure(k=5, n_back=1, buffer_pct=0.0, use="wick")

    def target_builder(stop):
        return E.target_opposite_signal(np.where(exit_sig == 0, -1, 1), treat_zero_as_exit=False)

    max_hold_bars = 60
    entries_all = mask_to_events(el, pd.Series(1, index=d1d.index))
    tr_e = [(i, dr) for i, dr in entries_all if i < i_tr]
    va_e = [(i - i_tr, dr) for i, dr in entries_all if i_tr <= i < i_va]
    tr_c, va_c = d1d.iloc[0:i_tr].reset_index(drop=True), d1d.iloc[i_tr:i_va].reset_index(drop=True)
    tr, _ = run_edge(tr_c, tr_e, stop_builder, target_builder, max_hold_bars, k=5)
    va, _ = run_edge(va_c, va_e, stop_builder, target_builder, max_hold_bars, k=5)

    row, tr_st, va_st, th, verdict = report_and_log(
        "6_RSI2_dipbuy_SPXshape", "1d", "RSI2<5 above SMA200, exit close>SMA5|RSI2>65",
        tr, va, "stop: exits.stop_structure backstop ADDED (round 78's original run used a "
                "swept-% stop and already found FAIL on oil both timeframes — this is a "
                "clean re-confirmation under the structural-stop standard, not a re-tuning).")
    log_family_map("6", "RSI2<5 dip-buy above SMA200 (SPX shape)", verdict,
                   f"val {va_st['n']}t ${va_st['expectancy']:+.2f}/t (train {tr_st['n']}t "
                   f"${tr_st['expectancy']:+.2f}/t)",
                   "N/A — signal-exit family (see round 78's original FAIL, this confirms it)",
                   f"{th['mult_full_18bps']:+.2f}x full round-trip cost")
    return row


def main():
    print("=" * 78)
    print("ROUND 112 — OIL FAMILY SWEEP 1: crypto/gold/SPX shapes ported, "
         "thresholds re-derived from oil's own distribution")
    print("=" * 78)
    d1h, d4h, d1d = load_oil()
    print(f"CL=F 1h: {len(d1h)} bars {d1h['timestamp'].iloc[0]}->{d1h['timestamp'].iloc[-1]}")
    print(f"CL=F 4h (resampled): {len(d4h)} bars")
    print(f"CL=F 1d: {len(d1d)} bars {d1d['timestamp'].iloc[0]}->{d1d['timestamp'].iloc[-1]}")

    rows = []
    for fn, args in ((family1, (d1h, d4h)), (family2, (d4h,)), (family3, (d4h,)),
                     (family4, (d1h, d1d))):
        r = fn(*args)
        if r:
            rows.append(r)
    r5a = family5(d1d, "1d", "1d", 20)
    r5b = family5(d1d, "1d", "1d", 55)
    r5c = family5(d1h, "1h", "1h", 20)
    for r in (r5a, r5b, r5c):
        if r:
            rows.append(r)
    r6 = family6(d1d)
    if r6:
        rows.append(r6)

    pd.DataFrame(rows).to_csv("step112_table.csv", index=False)
    print(f"\nWrote step112_table.csv ({len(rows)} rows). Appended "
         f"{len(rows)} lines to {FAMILY_MAP_PATH}.")


if __name__ == "__main__":
    main()
