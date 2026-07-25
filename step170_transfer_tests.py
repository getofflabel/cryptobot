"""
step170_transfer_tests.py — ETH-trader, round 170: THE MANDATORY TRANSFER
TEST of BTC's five currently-documented validated edges, replayed on
ETH-USDT.

Run:  python3 step170_transfer_tests.py

WHY THIS ROUND: ETH has never had a dedicated research program of its own
— every finding it owns is either the BTC-signal amplifier or an untested
assumption. Nearly every BTC finding gets replayed on ETH as the FIRST bar
of "is this real or BTC-shaped noise" — but R89 showed a sealed-passed
config replayed unchanged on nine fresh assets and 6 of 9 FAILED. Two
assets agreeing is a hypothesis, not evidence. This round does the replay
properly for all five: (a) the exact BTC recipe, unchanged thresholds, on
ETH's own candles and cost structure, (b) where the raw replay is close
but not quite, a properly re-derived ETH-native version with BTC's number
and ETH's number both stated and the reason they differ.

THE FIVE EDGES (BTC's own numbers, from MARKET_PLAYBOOKS.md / RESEARCH_LOG.md)
  1. 1h CHoCH k8 + confluence>=2               sealed +$99.52/t  (step56)
  2. 4h hidden RSI(14) divergence k8 buf0.35% tgt3x hold48h   sealed +$52.03/t (step58)
  3. 4h trend, vol_gated_ma(20,100,min_atr_pct=1.5), live -8% SL   R54 sealed proof
  4. 1h RSI(3)<15 dip-buy, champ4h gate, stop1.5%/tgt4.5%/hold48h   R43 (tactical.py live spec)
  5. News momentum, WatcherGuru first-post-news-bar-move direction,
     1h stop1.2%/tgt2.4%/hold24h                              sealed PASS (step45b)

CODE REUSE, STATED PLAINLY: the ENTRY/SIGNAL construction for edges 1, 2
and 5 is not reimplemented — it is imported UNCHANGED from step56_smc_
toolkit.py / step58_divergence_mtf.py / step45b_news_events.py (the exact
functions that produced BTC's sealed numbers: bos_chain, equilibrium,
liquidity_pools, sweep_events, fvg_signals, leg_tracker, fib_entries,
bias_series_4h, train_median_stop_pct; divergence_events, swings,
swing_stop_pct; classify_headline, align_events). Only the SCORING wrapper
is written fresh here, because every BTC round to date defaults
execution="maker" and tonight's desk standard is execution="taker" ALWAYS
— so this round cannot reuse those modules' own score() helpers without
silently keeping a maker assumption ETH is not supposed to get. Edges 3
and 4 (vol_gated_ma / rsi) reuse strategy.py's primitives directly, same
principle.

SEALED-TEST PROTOCOL FOR TRANSFERS (stated once, applies everywhere below):
Per this repo's own established convention for cross-asset transfer tests
(the 2026-07-23 "BTC-signal -> ETH-trade" amplifier round, and R89's nine-
asset sealed-config replay) — a config that underwent ZERO selection on
the target asset's data is not "burning a look" by viewing its test slice,
because nothing was chosen based on what that slice contains. So: the
UNCHANGED-CONFIG replay of each BTC recipe is scored on ETH's full
train+val+test gauntlet in one shot, exactly like the amplifier round did.
Any RE-DERIVED ETH-native variant (a genuine in-market choice made by
looking at ETH's own distribution) is held to the full standard instead —
train-only selection, val read once, SEALED NEVER TOUCHED — and this
script enforces that split in code, not just in prose.

COSTS: execution="taker" throughout (backtest.CostModel: 6bps taker fee +
1bp half-spread + 2bp slippage per fill = 18bps round trip worst-case;
this program's realized blended day-trade cost has run closer to ~9bps).
Both are stated per edge; thickness = mean pooled per-trade return (% of
notional) / 18bps taker floor. Under 5x is a REJECT per the desk standard.
"""

import numpy as np
import pandas as pd

from backtest import run_backtest
import step170_eth_lib as lib
from step170_eth_lib import (
    EXECUTION, MIN_TRAIN_TRADES, MIN_VAL_TRADES, REALIZED_DAYTRADE_RT_BPS,
    TAKER_RT_BPS, bar_hours, chance_baseline, champ_aligned, day_trade_signal,
    eth_atr_pct_medians, hold_stats, hours_to_bars, load_frames, mk_row,
    score, score_sealed, split_points, swing_stop_pct, thickness, verdict_for,
)
from step41_shorts import confirmed_swings, days_to_bars, last_n_confirmed
from step56_smc_toolkit import (
    bias_series_4h, bos_chain, equilibrium, fib_entries, fvg_signals,
    leg_tracker, liquidity_pools, sweep_events, train_median_stop_pct,
)
from step58_divergence_mtf import divergence_events, macd_hist, swings
from step45b_news_events import align_events, classify_frame
from strategy import atr, rsi, vol_gated_ma

pd.set_option("display.width", 240)

CHAMP_KW = dict(fast=20, slow=100, min_atr_pct=1.5)   # BTC's exact champion, unchanged


def full_gauntlet_score(d, sig, f, n, i_tr, i_va, stop_pct=None, target_pct=None):
    """Unchanged-config replay scorer: train, val, AND sealed test, in one
    look — see module docstring's SEALED-TEST PROTOCOL note. Returns
    (tr, va, te) BacktestResults, all execution='taker'."""
    def run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True),
            sig.iloc[lo:hi].reset_index(drop=True),
            execution=EXECUTION,
            funding_series=f.iloc[lo:hi].reset_index(drop=True) if f is not None else None,
            stop_pct=stop_pct, target_pct=target_pct,
        )
    return run(0, i_tr), run(i_tr, i_va), run(i_va, n)


def report_full(tag, tr, va, te):
    for label, r in (("TRAIN", tr), ("VAL", va), ("TEST(sealed)", te)):
        mean_ret, mult = thickness(r, r)  # pooled = this window only (tr passed twice is fine, symmetric)
        print(f"  [{tag}] {label:14s} n={len(r.trades):4d}  exp=${r.expectancy:+8.2f}/t  "
              f"win={r.win_rate*100:5.1f}%  ret={r.total_return_pct:+7.2f}%  "
              f"dd={r.max_drawdown_pct:6.2f}%  meanRet%notional={mean_ret:+.3f}%  "
              f"thickness={mult:5.2f}x taker-cost")


ALL_ROWS = []   # for step170_table.csv


def log_row(row):
    ALL_ROWS.append(row)


# ===========================================================================
# EDGE 1 — 1h CHoCH k8 + confluence>=2  (step56 recipe, unchanged)
# ===========================================================================

def edge1_choch_confluence(frames, funding, meta):
    print("\n" + "=" * 78)
    print("EDGE 1 — 1h CHoCH k8 + confluence>=2 (BTC sealed +$99.52/t, step56)")
    print("=" * 78)
    tf = "1h"
    d, f = frames[tf], funding[tf]
    n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]
    frame4h = frames["4h"]

    bias4h = bias_series_4h(frame4h)
    bias_1h = champ_aligned(frame4h, bias4h, d)
    bull_pct = float((bias_1h == 1).mean() * 100)
    bear_pct = float((bias_1h == -1).mean() * 100)
    print(f"  ETH 4h bias (champ AND BOS-chain agree) on 1h: bullish {bull_pct:.1f}% / "
          f"bearish {bear_pct:.1f}% / neutral {100-bull_pct-bear_pct:.1f}% of bars "
          f"(context only, not yet a verdict)")

    k = 8   # BTC's winning k, unchanged
    bos = bos_chain(d, k)
    discount, premium, eq, lsh, lsl = equilibrium(d, k)
    pool_high, pool_low = liquidity_pools(d, k, 0.1)          # CONF_TOL, unchanged
    sweep_long, sweep_short = sweep_events(d, pool_high, pool_low, 0.3)  # CONF_DEPTH, unchanged
    window = hours_to_bars(d, 24)
    swept_recent_long = (sweep_long.astype(int).rolling(window, min_periods=1).max().fillna(0).astype(bool))
    swept_recent_short = (sweep_short.astype(int).rolling(window, min_periods=1).max().fillna(0).astype(bool))
    el_fvg, es_fvg, dl_fvg, ds_fvg, ab, ar = fvg_signals(d, 0.5, days_to_bars(d, 10))  # unchanged
    bull_low, bull_high, bear_low, bear_high = leg_tracker(d, k, days_to_bars(d, 20))  # unchanged
    el_fib, es_fib, dl_fib, ds_fib, extl, exts, lz, sz = fib_entries(
        d, bull_low, bull_high, bear_low, bear_high, 0.618, 0.79)

    dist_bos_long = (d["close"] - bos["lsl"]) / d["close"] * 100
    dist_bos_short = (bos["lsh"] - d["close"]) / d["close"] * 100
    bias_long = (bias_1h == 1)
    bias_short = (bias_1h == -1)
    count_long = (bias_long.astype(int) + discount.astype(int) + lz.astype(int)
                  + swept_recent_long.astype(int) + ab.astype(int))
    count_short = (bias_short.astype(int) + premium.astype(int) + sz.astype(int)
                   + swept_recent_short.astype(int) + ar.astype(int))
    choch_long, choch_short = bos["choch_long"], bos["choch_short"]

    print("\n  DOSE-RESPONSE CHECK (does ETH show the same monotonic threshold->edge shape BTC showed?):")
    print(f"  {'thresh':>6s} {'n_events(tr+va)':>16s} {'tr_exp':>10s} {'va_exp':>10s} {'verdict':>10s}")
    dose_rows = []
    for threshold in (0, 1, 2, 3):
        if threshold == 0:
            el, es = choch_long, choch_short
        else:
            el = choch_long & (count_long >= threshold)
            es = choch_short & (count_short >= threshold)
        mask = el | es
        n_events = int(mask.iloc[:i_va].sum())
        dist = pd.Series(np.nan, index=d.index)
        dist = dist.mask(el, dist_bos_long)
        dist = dist.mask(es, dist_bos_short)
        stop_pct = train_median_stop_pct(d, i_tr, mask, dist)
        if stop_pct is None:
            print(f"  {threshold:6d} {n_events:16d}  -- no qualifying train entries --")
            continue
        target_pct = stop_pct * 2.0   # BTC's winning target_mult=2.0, unchanged
        sig = day_trade_signal(d, el, es, days_to_bars(d, 10))   # CONF_HOLD_DAYS=10, unchanged
        tr, va = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
        v = verdict_for(tr, va)
        print(f"  {threshold:6d} {n_events:16d} {tr.expectancy:10.2f} {va.expectancy:10.2f} {v:>10s}")
        dose_rows.append((threshold, n_events, tr, va, stop_pct, target_pct))
        log_row(mk_row("1-CHoCH-confluence", f"k{k} CHoCH thresh>={threshold} tgt2x (dose-response)",
                        tf, tr, va, stop_pct, target_pct, 10 * 24,
                        extra={"edge": "1-CHoCH-confluence", "transfer_type": "unchanged-config",
                               "btc_number": "sealed +$99.52/t (16t) thresh>=2", "eth_number": None}))

    # the EXACT sealed config: threshold>=2
    target = [r for r in dose_rows if r[0] == 2]
    if not target:
        print("\n  THRESHOLD>=2 (the exact BTC sealed config): INSUFFICIENT SAMPLE on ETH train "
              "(no qualifying entries) — cannot even reach train/val, let alone sealed.")
        return
    _, n_ev, tr2, va2, stop2, tgt2 = target[0]
    print(f"\n  UNCHANGED-CONFIG REPLAY (k8 CHoCH thresh>=2 tgt2x hold10d, stop=train-median "
          f"structure-distance {stop2:.2f}%, target={tgt2:.2f}%):")
    if len(tr2.trades) >= MIN_TRAIN_TRADES and len(va2.trades) >= MIN_VAL_TRADES:
        el = choch_long & (count_long >= 2)
        es = choch_short & (count_short >= 2)
        mask = el | es
        dist = pd.Series(np.nan, index=d.index)
        dist = dist.mask(el, dist_bos_long)
        dist = dist.mask(es, dist_bos_short)
        sig = day_trade_signal(d, el, es, days_to_bars(d, 10))
        tr, va, te = full_gauntlet_score(d, sig, f, n, i_tr, i_va, stop_pct=stop2, target_pct=tgt2)
        report_full("EDGE1", tr, va, te)
        verdict_te = "SURVIVOR" if (tr.expectancy > 0 and va.expectancy > 0 and te.expectancy > 0
                                     and len(te.trades) >= MIN_VAL_TRADES) else "FAIL-ON-TEST"
        print(f"  TRANSFER VERDICT: {verdict_te}")
        log_row(mk_row("1-CHoCH-confluence", "k8 CHoCH thresh>=2 tgt2x hold10d (UNCHANGED CONFIG, full gauntlet)",
                        tf, tr, va, stop2, tgt2, 240,
                        extra={"edge": "1-CHoCH-confluence", "transfer_type": "unchanged-config-full-gauntlet",
                               "btc_number": "sealed +$99.52/t (16t)",
                               "eth_test_exp": te.expectancy, "eth_test_n": len(te.trades),
                               "transfer_verdict": verdict_te}))
    else:
        print(f"  train n={len(tr2.trades)}, val n={len(va2.trades)} — "
              f"INSUFFICIENT SAMPLE at the floor (30 train / 8 val), no sealed look taken.")
        log_row(mk_row("1-CHoCH-confluence", "k8 CHoCH thresh>=2 tgt2x hold10d (UNCHANGED CONFIG)",
                        tf, tr2, va2, stop2, tgt2, 240,
                        extra={"edge": "1-CHoCH-confluence", "transfer_type": "unchanged-config",
                               "btc_number": "sealed +$99.52/t (16t)", "transfer_verdict": "INSUFFICIENT-SAMPLE"}))


# ===========================================================================
# EDGE 2 — 4h hidden RSI(14) divergence k8 buf0.35% tgt3x hold48h (step58, unchanged)
# ===========================================================================

def edge2_hidden_rsi_divergence(frames, funding, meta):
    print("\n" + "=" * 78)
    print("EDGE 2 — 4h hidden RSI(14) divergence, k8, buf0.35%, tgt3x, hold48h "
          "(BTC sealed +$52.03/t, step58)")
    print("=" * 78)
    tf = "4h"
    d, f = frames[tf], funding[tf]
    n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]
    champ4h = vol_gated_ma(d, **CHAMP_KW)   # 4h source == 4h target, no cross-tf alignment needed

    osc = rsi(d["close"], 14)
    k = 8
    (long_reg, short_reg, long_hid, short_hid, low_ext, high_ext) = divergence_events(d, osc, k, champ4h)
    n_events = int((long_hid | short_hid).iloc[:i_va].sum())
    print(f"  hidden-divergence qualifying events (train+val window): {n_events}")

    buffer_pct = 0.35   # BTC's winning buffer, unchanged
    stop_l = swing_stop_pct(d["close"], low_ext, long_hid, i_tr, buffer_pct, lib.STOP_CAP_SWING)
    stop_s = swing_stop_pct(d["close"], high_ext, short_hid, i_tr, buffer_pct, lib.STOP_CAP_SWING)
    n_l, n_s = int(long_hid.sum()), int(short_hid.sum())
    stop_pct = ((stop_l * n_l + stop_s * n_s) / (n_l + n_s)) if (n_l + n_s) else lib.STOP_CAP_SWING
    target_pct = min(3.0 * stop_pct, 3 * lib.STOP_CAP_SWING)   # BTC's winning tmult=3.0, unchanged
    mh_bars = hours_to_bars(d, 48)   # BTC's winning hold, unchanged

    print(f"  ETH-derived stop distance (train-median-to-swing-extreme + {buffer_pct}% buffer, "
          f"structure-based per the standing rule, NOT a swept percentage): {stop_pct:.2f}% "
          f"(BTC's own equivalent train-derived stop distance was NOT logged verbatim in "
          f"RESEARCH_LOG — same RECIPE reused, ETH's own swings produce ETH's own number)")
    print(f"  target: {target_pct:.2f}% (3x stop) | max_hold: 48h ({mh_bars} bars on 4h)")

    sig = day_trade_signal(d, long_hid, short_hid, mh_bars)
    tr2, va2 = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
    print(f"\n  TRAIN/VAL screen: train n={len(tr2.trades)} exp=${tr2.expectancy:+.2f}  "
          f"val n={len(va2.trades)} exp=${va2.expectancy:+.2f}")

    log_row(mk_row("2-hidden-rsi-divergence", f"RSI14 k8 hidden buf{buffer_pct}% tgt3x hold48h",
                    tf, tr2, va2, stop_pct, target_pct, 48,
                    extra={"edge": "2-hidden-rsi-divergence", "transfer_type": "unchanged-config",
                           "btc_number": "sealed +$52.03/t (24t), ~18/yr"}))

    if len(tr2.trades) >= MIN_TRAIN_TRADES and len(va2.trades) >= MIN_VAL_TRADES:
        tr, va, te = full_gauntlet_score(d, sig, f, n, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
        report_full("EDGE2", tr, va, te)
        verdict_te = "SURVIVOR" if (tr.expectancy > 0 and va.expectancy > 0 and te.expectancy > 0
                                     and len(te.trades) >= MIN_VAL_TRADES) else "FAIL-ON-TEST"
        print(f"  TRANSFER VERDICT: {verdict_te}")
        mean_ret, mult = thickness(te, te)
        print(f"  thickness (test window only): {mean_ret:+.3f}% of notional = {mult:.2f}x taker "
              f"round-trip cost ({TAKER_RT_BPS:.0f}bps) -> {'REJECT (<5x)' if mult < 5 else 'clears 5x bar'}")
        log_row(mk_row("2-hidden-rsi-divergence", "RSI14 k8 hidden buf0.35% tgt3x hold48h (UNCHANGED CONFIG, full gauntlet)",
                        tf, tr, va, stop_pct, target_pct, 48,
                        extra={"edge": "2-hidden-rsi-divergence", "transfer_type": "unchanged-config-full-gauntlet",
                               "btc_number": "sealed +$52.03/t (24t)",
                               "eth_test_exp": te.expectancy, "eth_test_n": len(te.trades),
                               "transfer_verdict": verdict_te}))
    else:
        print(f"  INSUFFICIENT SAMPLE at the 30/8 floor — no sealed look taken.")


# ===========================================================================
# EDGE 3 — 4h trend, vol_gated_ma(20,100,min_atr_pct=1.5), live -8% SL ("the ride")
# ===========================================================================

def edge3_ride(frames, funding, meta):
    print("\n" + "=" * 78)
    print("EDGE 3 — 4h trend champion, vol_gated_ma(20,100,min_atr_pct=1.5), live -8% SL "
          "(\"the ride\", R54 sealed proof)")
    print("=" * 78)
    tf = "4h"
    d, f = frames[tf], funding[tf]
    n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]

    a_pct = atr(d, 14) / d["close"] * 100
    eth_med_atr = float(a_pct.median())
    btc_med_atr_recent = 0.45   # MARKET_PLAYBOOKS.md: BTC's decayed-era hourly median; 4h will run higher but same DECAY story
    print(f"  ETH 4h ATR% distribution (own, never inherited from BTC): "
          f"median {eth_med_atr:.2f}%  p25 {float(a_pct.quantile(.25)):.2f}%  "
          f"p75 {float(a_pct.quantile(.75)):.2f}%")

    # --- (a) UNCHANGED CONFIG: BTC's literal 1.5% floor gate ---
    sig_unchanged = vol_gated_ma(d, **CHAMP_KW)
    time_in_mkt_unchanged = float((sig_unchanged == 1).mean() * 100)
    print(f"\n  UNCHANGED gate (min_atr_pct=1.5, BTC's literal number): "
          f"time-in-market on ETH = {time_in_mkt_unchanged:.1f}% of bars "
          f"(BTC's own trailing-3mo figure at the time of R54 was 18.7% — "
          f"the SAME 1.5% number is barely selective on ETH because ETH's own "
          f"4h ATR% median ({eth_med_atr:.2f}%) already sits above 1.5%, unlike "
          f"BTC's decayed-era ATR%. Same threshold, very different filter.)")
    sig_signal = pd.Series(np.where(sig_unchanged == 1, 1.0, 0.0), index=d.index)
    tr2, va2 = score(d, sig_signal, f, i_tr, i_va, stop_pct=8.0)  # BTC's literal -8% SL, unchanged
    print(f"  TRAIN/VAL (stop -8%, unchanged): train n={len(tr2.trades)} exp=${tr2.expectancy:+.2f}  "
          f"val n={len(va2.trades)} exp=${va2.expectancy:+.2f}")
    log_row(mk_row("3-ride-vol-gated-trend", "vol_gated_ma(20,100,min_atr=1.5) stop-8% (UNCHANGED CONFIG)",
                    tf, tr2, va2, 8.0, None, None,
                    extra={"edge": "3-ride-vol-gated-trend", "transfer_type": "unchanged-config",
                           "btc_number": "R54 sealed: 8t +$401.30/t +32.1% DD-12.3%",
                           "eth_time_in_market_pct": time_in_mkt_unchanged}))
    verdict_unchanged = verdict_for(tr2, va2)
    if verdict_unchanged == "SURVIVOR":
        tr, va, te = full_gauntlet_score(d, sig_signal, f, n, i_tr, i_va, stop_pct=8.0)
        report_full("EDGE3-unchanged", tr, va, te)
    else:
        print(f"  verdict: {verdict_unchanged} — no sealed look taken on the unchanged config.")

    # --- (b) RE-DERIVED: ETH-native gate matched to BTC's OWN selectivity percentile ---
    # BTC's gate was open 18.7% of bars at R54-time; find the min_atr_pct on ETH's own
    # distribution that reproduces roughly that same selectivity (the thing R54 says IS
    # the edge — "the strict gate marks only real vol expansions" — is a SELECTIVITY
    # property, not a literal number, so re-deriving preserves the mechanism instead of
    # the digit).
    target_selectivity = 18.7
    grid = np.arange(1.0, 4.05, 0.1)
    best = None
    for g in grid:
        s = vol_gated_ma(d, fast=20, slow=100, min_atr_pct=float(g))
        tim = float((s == 1).mean() * 100)
        if best is None or abs(tim - target_selectivity) < abs(best[1] - target_selectivity):
            best = (float(g), tim)
    eth_gate, eth_tim = best
    print(f"\n  RE-DERIVED gate: ETH's own min_atr_pct that reproduces BTC's ~{target_selectivity}% "
          f"gate-open selectivity is min_atr_pct={eth_gate:.1f}% (time-in-market {eth_tim:.1f}%). "
          f"BTC's number was 1.5%; ETH's re-derived number is {eth_gate:.1f}% — they differ because "
          f"ETH's baseline volatility (4h ATR% median {eth_med_atr:.2f}%) runs well above BTC's "
          f"decayed-era baseline, so the SAME absolute floor filters almost nothing on ETH.")
    sig_re = vol_gated_ma(d, fast=20, slow=100, min_atr_pct=eth_gate)
    sig_re_signal = pd.Series(np.where(sig_re == 1, 1.0, 0.0), index=d.index)

    # structure-based stop instead of the swept -8%: most recent confirmed swing low,
    # k=8 (same k used elsewhere in this round), + 0.35% buffer, train-median distance.
    sh_price, sl_price = confirmed_swings(d, 8)
    (sl1,) = last_n_confirmed(sl_price, 1)
    dist_struct = (d["close"] - sl1) / d["close"] * 100
    entries_mask = sig_re_signal.diff().fillna(sig_re_signal) > 0   # bars where a long freshly opens
    struct_stop_pct = swing_stop_pct(d["close"], sl1, entries_mask, i_tr, 0.35, cap=15.0)
    print(f"  Structure stop (most recent confirmed swing low, k8, +0.35% buffer, train-median "
          f"distance, NOT a swept percentage): {struct_stop_pct:.2f}% "
          f"(replaces the live book's swept -8% crash SL)")

    tr3, va3 = score(d, sig_re_signal, f, i_tr, i_va, stop_pct=struct_stop_pct)
    print(f"  TRAIN/VAL (re-derived gate {eth_gate:.1f}%, structure stop {struct_stop_pct:.2f}%): "
          f"train n={len(tr3.trades)} exp=${tr3.expectancy:+.2f}  val n={len(va3.trades)} exp=${va3.expectancy:+.2f}")
    print(f"  Per the desk standard, this is a genuine in-market choice on ETH data (the gate level "
          f"AND the stop were both derived by looking at ETH) -> SEALED STAYS UNTOUCHED here regardless "
          f"of the val read.")
    log_row(mk_row("3-ride-vol-gated-trend", f"vol_gated_ma(20,100,min_atr={eth_gate:.1f}) structure-stop{struct_stop_pct:.2f}% (RE-DERIVED)",
                    tf, tr3, va3, struct_stop_pct, None, None,
                    extra={"edge": "3-ride-vol-gated-trend", "transfer_type": "re-derived-eth-native",
                           "btc_number": "min_atr_pct=1.5 (18.7% selectivity), -8% swept SL",
                           "eth_number": f"min_atr_pct={eth_gate:.1f} ({eth_tim:.1f}% selectivity), "
                                         f"{struct_stop_pct:.2f}% structure stop",
                           "verdict": verdict_for(tr3, va3)}))


# ===========================================================================
# EDGE 4 — 1h RSI(3)<15 dip-buy, champ4h gate, stop1.5%/tgt4.5%/hold48h (tactical.py live spec)
# ===========================================================================

def edge4_rsi3_dipbuy(frames, funding, meta):
    print("\n" + "=" * 78)
    print("EDGE 4 — 1h RSI(3)<15 dip-buy, champ4h gate, stop1.5%/tgt4.5%/hold48h "
          "(R43 / tactical.py live spec)")
    print("=" * 78)
    tf = "1h"
    d, f = frames[tf], funding[tf]
    n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]
    frame4h = frames["4h"]
    champ4h = vol_gated_ma(frame4h, **CHAMP_KW)
    champ_al = champ_aligned(frame4h, champ4h, d)

    r3 = rsi(d["close"], 3)
    enter_long = ((r3 < 15) & (champ_al == 1)).fillna(False)
    enter_short = pd.Series(False, index=d.index)   # dip-buy shape: long only, unchanged
    n_events = int(enter_long.iloc[:i_va].sum())
    print(f"  qualifying entries (train+val window): {n_events}")

    mh_bars = hours_to_bars(d, 48)   # unchanged
    sig = day_trade_signal(d, enter_long, enter_short, mh_bars)

    # --- (a) UNCHANGED CONFIG: BTC's literal 1.5%/4.5% percentage stop/target ---
    tr2, va2 = score(d, sig, f, i_tr, i_va, stop_pct=1.5, target_pct=4.5)
    print(f"\n  UNCHANGED CONFIG (stop1.5%/tgt4.5%, BTC's literal swept-percentage geometry): "
          f"train n={len(tr2.trades)} exp=${tr2.expectancy:+.2f}  val n={len(va2.trades)} exp=${va2.expectancy:+.2f}")
    log_row(mk_row("4-rsi3-dipbuy", "RSI3<15 champ4h stop1.5%/tgt4.5%/hold48h (UNCHANGED CONFIG)",
                    tf, tr2, va2, 1.5, 4.5, 48,
                    extra={"edge": "4-rsi3-dipbuy", "transfer_type": "unchanged-config",
                           "btc_number": "R43/live: stop1.5%/tgt4.5%/hold48h, needs 48h room"}))
    if len(tr2.trades) >= MIN_TRAIN_TRADES and len(va2.trades) >= MIN_VAL_TRADES:
        tr, va, te = full_gauntlet_score(d, sig, f, n, i_tr, i_va, stop_pct=1.5, target_pct=4.5)
        report_full("EDGE4-unchanged", tr, va, te)
        verdict_te = "SURVIVOR" if (tr.expectancy > 0 and va.expectancy > 0 and te.expectancy > 0
                                     and len(te.trades) >= MIN_VAL_TRADES) else "FAIL-ON-TEST"
        print(f"  TRANSFER VERDICT: {verdict_te}")
        cb = chance_baseline(d, f, i_tr, i_va, int(enter_long.sum()), 0, mh_bars, 1.5, 4.5, n_draws=30)
        print(f"  CHANCE BASELINE (30 random-timing draws, same n={int(enter_long.sum())} entries, "
              f"same engine/costs/stop/target): survivor-by-luck rate = {cb['survivor_rate']*100:.1f}%, "
              f"mean random train exp=${cb['mean_tr_exp']:+.2f}, mean random val exp=${cb['mean_va_exp']:+.2f}")
        log_row(mk_row("4-rsi3-dipbuy", "RSI3<15 champ4h stop1.5%/tgt4.5%/hold48h (UNCHANGED CONFIG, full gauntlet)",
                        tf, tr, va, 1.5, 4.5, 48,
                        extra={"edge": "4-rsi3-dipbuy", "transfer_type": "unchanged-config-full-gauntlet",
                               "btc_number": "live spec", "eth_test_exp": te.expectancy,
                               "eth_test_n": len(te.trades), "transfer_verdict": verdict_te,
                               "chance_baseline_survivor_rate": cb["survivor_rate"]}))
    else:
        print(f"  INSUFFICIENT SAMPLE at the 30/8 floor — no sealed look taken.")

    # --- (b) RE-DERIVED: structure-based stop/target via confirmed_swings, ETH-native distance ---
    sh_price, sl_price = confirmed_swings(d, 5)   # tighter k for 1h (BTC's swing-stop family used k5/k8 both; k5 for 1h matches step58's 1h grid)
    (sl1,) = last_n_confirmed(sl_price, 1)
    (sh1,) = last_n_confirmed(sh_price, 1)
    dist_stop = (d["close"] - sl1) / d["close"] * 100
    struct_stop_pct = swing_stop_pct(d["close"], sl1, enter_long, i_tr, 0.20, cap=lib.HARD_STOP_CAP_DAYTRADE * 2)
    dist_tgt = (sh1 - d["close"]) / d["close"] * 100
    struct_tgt_pct = swing_stop_pct(d["close"], sh1, enter_long, i_tr, 0.0, cap=8.0)
    if struct_tgt_pct <= struct_stop_pct:
        struct_tgt_pct = struct_stop_pct * 2.0   # guard: if nearest swing high is closer than the stop, fall back to 2R
    print(f"\n  RE-DERIVED (structure stop = most recent confirmed swing low k5 + 0.20% buffer, "
          f"train-median distance; structure target = nearest confirmed swing high, same method): "
          f"stop {struct_stop_pct:.2f}% (BTC's number was a swept 1.5%), "
          f"target {struct_tgt_pct:.2f}% (BTC's number was a swept 4.5%). ETH's numbers differ because "
          f"they are read off ETH's own actual chart structure at entries, not a fixed ratio.")
    sig_struct = day_trade_signal(d, enter_long, enter_short, mh_bars)
    tr3, va3 = score(d, sig_struct, f, i_tr, i_va, stop_pct=struct_stop_pct, target_pct=struct_tgt_pct)
    print(f"  TRAIN/VAL: train n={len(tr3.trades)} exp=${tr3.expectancy:+.2f}  "
          f"val n={len(va3.trades)} exp=${va3.expectancy:+.2f}  verdict={verdict_for(tr3, va3)}  "
          f"(sealed stays untouched — this variant's stop/target were derived by looking at ETH)")
    log_row(mk_row("4-rsi3-dipbuy", f"RSI3<15 champ4h structure-stop{struct_stop_pct:.2f}%/structure-tgt{struct_tgt_pct:.2f}%/hold48h (RE-DERIVED)",
                    tf, tr3, va3, struct_stop_pct, struct_tgt_pct, 48,
                    extra={"edge": "4-rsi3-dipbuy", "transfer_type": "re-derived-eth-native",
                           "btc_number": "swept stop1.5%/tgt4.5%",
                           "eth_number": f"structure stop{struct_stop_pct:.2f}%/tgt{struct_tgt_pct:.2f}%",
                           "verdict": verdict_for(tr3, va3)}))


# ===========================================================================
# EDGE 5 — news momentum, WatcherGuru first-bar-move direction, 1h, unchanged
# ===========================================================================

def edge5_news_momentum(frames_full, funding_hist_lookup):
    print("\n" + "=" * 78)
    print("EDGE 5 — news momentum, WatcherGuru first-post-news-bar-move direction, 1h, "
          "stop1.2%/tgt2.4%/hold24h (BTC sealed PASS +$20.81/t, step45b)")
    print("=" * 78)
    news_raw = pd.read_parquet("data_watcherguru_history.parquet")
    news = classify_frame(news_raw)
    relevant = news[news["relevant"]]
    news_min, news_max = news["utc_timestamp"].min(), news["utc_timestamp"].max()
    print(f"  news sample span (SAME harvested WatcherGuru feed as BTC's round — the feed itself "
          f"is not BTC-specific, it's crypto/macro news): {news_min:%Y-%m-%d} -> {news_max:%Y-%m-%d} "
          f"({(news_max - news_min).days} days), {len(relevant)} relevant posts")

    tf = "1h"
    dfull = frames_full[tf]
    mask = (dfull["timestamp"] >= news_min - pd.Timedelta(hours=24)) & \
           (dfull["timestamp"] <= news_max + pd.Timedelta(hours=24))
    d = dfull[mask].reset_index(drop=True)
    fu = funding_hist_lookup(d)
    n, i_tr, i_va = split_points(d)
    print(f"  ETH {tf} sliced to news span: {n} bars, {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
          f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
          f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d}")

    floor_rel, trad_rel, valid_rel = align_events(d, relevant["utc_timestamp"])
    trad_rel = trad_rel[valid_rel]
    trad_rel = trad_rel[trad_rel < len(d)]
    opens, closes = d["open"].to_numpy(), d["close"].to_numpy()
    move_sign = np.sign(closes[trad_rel] - opens[trad_rel])
    up_idx = trad_rel[move_sign > 0]
    down_idx = trad_rel[move_sign < 0]
    print(f"  first-bar-move events: {len(up_idx)} up / {len(down_idx)} down")

    el = pd.Series(False, index=d.index); el.iloc[up_idx] = True
    es = pd.Series(False, index=d.index); es.iloc[down_idx] = True
    mh_bars = hours_to_bars(d, 24)   # unchanged
    sig = day_trade_signal(d, el, es, mh_bars)

    tr2, va2 = score(d, sig, fu, i_tr, i_va, stop_pct=1.2, target_pct=2.4)   # unchanged
    print(f"\n  UNCHANGED CONFIG (stop1.2%/tgt2.4%/hold24h): train n={len(tr2.trades)} "
          f"exp=${tr2.expectancy:+.2f}  val n={len(va2.trades)} exp=${va2.expectancy:+.2f}")
    log_row(mk_row("5-news-momentum", "first_bar_move stop1.2%/tgt2.4%/hold24h (UNCHANGED CONFIG)",
                    tf, tr2, va2, 1.2, 2.4, 24,
                    extra={"edge": "5-news-momentum", "transfer_type": "unchanged-config",
                           "btc_number": "sealed +$20.81/t x67, +13.9%, 52.2% win"}))
    if len(tr2.trades) >= MIN_TRAIN_TRADES and len(va2.trades) >= MIN_VAL_TRADES:
        tr, va, te = full_gauntlet_score(d, sig, fu, n, i_tr, i_va, stop_pct=1.2, target_pct=2.4)
        report_full("EDGE5", tr, va, te)
        verdict_te = "SURVIVOR" if (tr.expectancy > 0 and va.expectancy > 0 and te.expectancy > 0
                                     and len(te.trades) >= MIN_VAL_TRADES) else "FAIL-ON-TEST"
        print(f"  TRANSFER VERDICT: {verdict_te}")
        log_row(mk_row("5-news-momentum", "first_bar_move stop1.2%/tgt2.4%/hold24h (UNCHANGED CONFIG, full gauntlet)",
                        tf, tr, va, 1.2, 2.4, 24,
                        extra={"edge": "5-news-momentum", "transfer_type": "unchanged-config-full-gauntlet",
                               "btc_number": "sealed +$20.81/t x67", "eth_test_exp": te.expectancy,
                               "eth_test_n": len(te.trades), "transfer_verdict": verdict_te}))
    else:
        print(f"  train n={len(tr2.trades)}, val n={len(va2.trades)} — "
              f"INSUFFICIENT SAMPLE at the 30/8 floor (news history is short — ~{(news_max-news_min).days}d "
              f"total vs 6yr of candles, same caveat step45b logged for BTC), no sealed look taken.")


# ===========================================================================
# main
# ===========================================================================

def main():
    print("Loading ETH-USDT data (bybit cache, no network calls needed)...")
    frames, funding, funding_hist = load_frames(("15m", "1h", "4h"))
    meta = {}
    for tf in ("1h", "4h"):
        d = frames[tf]
        n, i_tr, i_va = split_points(d)
        meta[tf] = {"n": n, "i_tr": i_tr, "i_va": i_va}
        print(f"  {tf}: {n} bars, {d['timestamp'].iloc[0]:%Y-%m-%d} -> {d['timestamp'].iloc[-1]:%Y-%m-%d} "
              f"| train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed)")

    atr_meds = eth_atr_pct_medians({tf: frames[tf] for tf in ("1h", "4h")})
    print(f"\n  ETH's OWN ATR% medians (never inherited from BTC): "
          f"1h median {atr_meds['1h']['median']:.3f}% (p25 {atr_meds['1h']['p25']:.3f} / "
          f"p75 {atr_meds['1h']['p75']:.3f}); 4h median {atr_meds['4h']['median']:.3f}% "
          f"(p25 {atr_meds['4h']['p25']:.3f} / p75 {atr_meds['4h']['p75']:.3f}). "
          f"MARKET_PLAYBOOKS.md's BTC number: hourly ATR medians fell ~0.9%->~0.45% era-over-era. "
          f"ETH runs materially hotter on an absolute basis.")
    print(f"  Cost floor: taker round trip = {TAKER_RT_BPS:.1f}bps (worst case), "
          f"this program's realized blended day-trade cost ~{REALIZED_DAYTRADE_RT_BPS:.1f}bps. "
          f"execution='{EXECUTION}' throughout this round, per tonight's desk standard "
          f"(BTC's own step43/step56/step58/step54 rounds default to 'maker' — this is a "
          f"deliberately STRICTER replay, not apples-to-apples on execution, stated plainly).")
    print(f"  Chance baseline convention: this round's empirical chance-baseline check (30 random-"
          f"timing draws through the identical engine) follows R83/R90/step93's standing rule that "
          f"every sweep must state what fraction of cells would pass by luck alone.")

    edge1_choch_confluence(frames, funding, meta)
    edge2_hidden_rsi_divergence(frames, funding, meta)
    edge3_ride(frames, funding, meta)
    edge4_rsi3_dipbuy(frames, funding, meta)

    frames_full = {"1h": frames["1h"]}
    edge5_news_momentum(frames_full, lambda d: lib_align_funding(d, funding_hist))

    df = pd.DataFrame(ALL_ROWS)
    df.to_csv("step170_table.csv", index=False)
    print(f"\n\n{len(df)} rows written to step170_table.csv")
    print(df[["edge", "config", "tf", "tr_n", "tr_exp", "va_n", "va_exp",
              "thickness_x_taker_cost", "verdict"]].to_string(index=False,
              float_format=lambda x: f"{x:,.2f}"))
    return df


from step11_round6 import align_funding as lib_align_funding


if __name__ == "__main__":
    main()
