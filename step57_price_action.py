"""
step57_price_action.py — round 57: PRICE-ACTION PATTERNS + ORDER BLOCKS +
VOLATILITY COMPRESSION on BTC. Three classic discretionary-trader tool
families, formalized as mechanical, shift-disciplined rules and run through
the standard gauntlet. Research only — no live orders, no commits, and no
file touched outside step57_price_action.py / step57_results.md.

PLUMBING REUSE (imported, not reimplemented — same discipline the whole
program has used since round 41/43): split_points, day_trade_signal, score,
mk_row, verdict_for, champ_aligned, CHAMP_KW, bar_hours, hours_to_bars from
step43_daytrade.py; adaptive_vol_gate from step41_shorts.py (imported for
completeness/possible reuse by a future round; this round's compression
families use their OWN adaptive trailing-percentile/median gates per the
mandate's explicit spec rather than the fixed-window adaptive_vol_gate, see
FAMILY 3 notes below for why).

GAUNTLET (unchanged): chronological 60/20/20 per timeframe. This script
NEVER slices into the final 20% (test) — split_points/score only ever see
train (0:i_tr) and val (i_tr:i_va). CostModel defaults (6bps taker/2bps
maker, 1bp half-spread, 2bp slippage), execution="maker", REAL funding via
align_funding. Selection is by TRAIN expectancy only; val is checked once,
never tuned against.

STOP-DISTANCE CONVENTION (same approximation this repo has used since round
17/41/43 — run_backtest takes ONE fixed stop_pct/target_pct per run, not a
per-trade dynamic level): wherever the family spec calls for a structural
stop ("past the block's far edge", "opposite side of the mother bar"), we
compute the TRAIN-only median of that per-event distance and hold it fixed
across train/val, stated plainly here and in the results file. Wherever the
spec calls for a vol-scaled stop, we use A x median(ATR%) on that
timeframe's TRAIN slice, same as always. Every computed stop is capped at
STOP_CAP_PCT = 3.0% — looser than step43's momentum-specific 1.7% ceiling
(these are structural/geometric stops, not tight momentum entries — they
need more room) but still safely inside BloFin's ~4.5% liquidation buffer
at 20x, so nothing here is disqualified from the 15-20x tier by construction.

MAX-HOLD CHOICES: the mandate fixes max hold at 48h for order blocks
explicitly. It does not fix a hold for rejection candles or compression —
reasonable day-trade-tier defaults were chosen and are stated plainly
(pin bars/engulfing 24h, inside-bar breakout 12h, NR compression 24h,
BB-width squeeze 48h — "ride" implies more room, range-compression 24h).
These are FIXED, not gridded, to keep the total config count in budget.

NO-LOOKAHEAD DISCIPLINE (read strategy.py's donchian_breakout / step41's
confirmed_swings / step43's champ_aligned for the ground truth this follows):
- All rolling extremes used to define a breakout/context LEVEL are
  shift(1)'d — the bar that breaks a level is never inside the window that
  defines it.
- Fractal swing points (order-block "confirmed swing" requirement) use a
  centered rolling window then shift(k) — a swing at bar j is only "known"
  once bar j+k has printed, exactly step41's confirmed_swings pattern.
- Trailing percentile/median gates (BB-width squeeze, range-compression)
  are computed on a rolling window that itself EXCLUDES the current bar
  (extra shift(1) beyond the window's own backward-looking construction).
- Cross-timeframe (4h trend bias read from 1h, or read onto 4h itself) uses
  champ_aligned's availability-at-CLOSE merge_asof, never a still-forming
  bar. Daily SMA50 context is aligned the same way (available at daily
  close + 1 day).
- Smoothing indicators (ATR, RSI-adjacent, Bollinger) are NOT shifted,
  matching the rest of the codebase — the engine's own bar-close-N ->
  fill-at-open-N+1 mechanic is what enforces no-lookahead there.

THREE FAMILIES (full definitions also restated in step57_results.md):
  1. ORDER BLOCKS — the last opposing candle before a confirmed-swing-
     breaking impulse; entry on first retracement into the block (50%
     touch or full sweep); stop past the block's far edge; target 2x/3x
     stop; max hold 48h. Also the BREAKER variant: a block that FAILS
     (price closes through it) flips role — entry on the retest from the
     other side, trading the continuation of the break.
  2. REJECTION CANDLES — (a) pin bars (wick >= 2x/3x body, close in the
     outer 33% of the range) at a context level (mandatory for the
     tradeable version; a "none" context arm is run ALONGSIDE for the
     required context-vs-no-context comparison); (b) engulfing at the
     same context levels; (c) inside-bar breakouts (1-2 inside bars, then
     trade the mother bar's range break), both with-trend-gated (4h
     vol_gated_ma bias) and ungated.
  3. VOLATILITY COMPRESSION — (a) NR4/NR7 narrowest-range-in-N breakout;
     (b) Bollinger-bandwidth squeeze (lowest 10th/20th percentile of its
     own trailing 365d distribution) breaking the bands, fixed 2x/3xATR
     target OR a "trailing exit" approximation (stop-only, ride to
     max_hold — run_backtest has no native trailing-stop, stated plainly);
     (c) range-compression breakout (12/24-bar range < 0.5x/0.7x its own
     trailing 180d median). All three run both with-trend-gated and
     ungated.

REQUIRED ANALYSES (all in step57_results.md): per-family raw event counts
(impulse/block/pattern frequency — are these setups rare or common?), a
context-vs-no-context comparison for the rejection family quantifying
whether requiring a level actually helps, and a cross-family overlap note
(a simple from-scratch 3-candle FVG recompute on 1h vs the order-block
family's entry bars — do these SMC tools fire at the same bars?).
"""

import numpy as np
import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import adaptive_vol_gate          # imported per mandate (see header note)
from step43_daytrade import (CHAMP_KW, bar_hours, champ_aligned,
                             day_trade_signal, hours_to_bars, mk_row, score,
                             split_points, verdict_for)
from strategy import atr, vol_gated_ma

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8
STOP_CAP_PCT = 3.0
STOP_FLOOR_PCT = 0.30
TIMEFRAMES = ("1h", "4h")


# ---------------------------------------------------------------------------
# generic shared helpers (family-agnostic)
# ---------------------------------------------------------------------------

def last_true_idx(bool_arr):
    """value[i] = index of the most recent True at or before i, else -1.
    Pure forward-fill of the running index via cummax — vectorized."""
    idx = np.where(bool_arr, np.arange(len(bool_arr)), -1)
    return np.maximum.accumulate(idx)


def apply_trend_gate(enter_long, enter_short, champ_al, gated):
    """'gated' = with-trend only, same convention as step43's momentum-burst
    'champ' condition: longs only when champ==1, shorts only when champ==0.
    'ungated' passes both through unfiltered ('both' directions, spec's
    'ungated' arm of every compression/inside-bar family)."""
    if not gated:
        return enter_long, enter_short
    return (enter_long & (champ_al == 1)), (enter_short & (champ_al == 0))


def daily_sma_aligned(daily_frame, sma_series, target_frame):
    """Daily SMA50, available at daily bar CLOSE (open_time + 1 day), merged
    onto a finer target frame with the same causal merge_asof pattern
    champ_aligned uses for the 4h trend."""
    avail = pd.DataFrame({
        "timestamp": daily_frame["timestamp"] + pd.Timedelta(days=1),
        "sma50": sma_series.to_numpy(),
    }).dropna(subset=["sma50"]).sort_values("timestamp")
    merged = pd.merge_asof(target_frame[["timestamp"]].sort_values("timestamp"),
                            avail, on="timestamp", direction="backward")
    return merged["sma50"].reset_index(drop=True)


def stop_from_train_events(events, i_tr, fallback):
    """events: list of (bar_idx, dist_pct). TRAIN-only median, capped."""
    train_d = [dist for (b, dist) in events if b < i_tr]
    stop = float(np.median(train_d)) if train_d else fallback
    return min(max(stop, STOP_FLOOR_PCT), STOP_CAP_PCT)


# ===========================================================================
# FAMILY 1 — ORDER BLOCKS (+ BREAKER variant)
# ===========================================================================

def confirmed_swings57(d, k=5):
    """Centered k-bar fractal swing high/low, confirmed (knowable) k bars
    later — identical construction to step41's confirmed_swings, k=5 chosen
    here (not gridded) so 'confirmed swing' means something structurally
    real at hourly resolution rather than 3-bar noise."""
    h, l = d["high"], d["low"]
    is_sh = (h == h.rolling(2 * k + 1, center=True).max())
    is_sl = (l == l.rolling(2 * k + 1, center=True).min())
    sh_conf = is_sh.shift(k).astype("boolean").fillna(False).astype(bool)
    sl_conf = is_sl.shift(k).astype("boolean").fillna(False).astype(bool)
    sh_price = h.shift(k).where(sh_conf)
    sl_price = l.shift(k).where(sl_conf)
    return sh_price, sl_price


def impulse_series(d, med_baseline, mult, bars_move):
    """impulse = |close-to-close move over bars_move bars| >= mult x the
    TRAIN-only median |1-bar return|%."""
    ret = (d["close"] / d["close"].shift(bars_move) - 1) * 100
    thresh = mult * med_baseline
    return (ret >= thresh).fillna(False), (ret <= -thresh).fillna(False)


def order_block_engine(d, i_tr, med_baseline, mult, bars_move, touch,
                        breaker, max_wait_bars, k_swing=5):
    """Returns (enter_long, enter_short, stop_pct, events dict).
    touch: '50pct' or 'sweep'. breaker: False = trade the retracement in
    the impulse direction; True = trade the failed-block retest in the
    OPPOSITE direction (see header)."""
    n = len(d)
    highs, lows = d["high"].to_numpy(), d["low"].to_numpy()
    closes, opens = d["close"].to_numpy(), d["open"].to_numpy()

    up_raw, down_raw = impulse_series(d, med_baseline, mult, bars_move)
    sh_price, sl_price = confirmed_swings57(d, k_swing)
    last_sh = sh_price.ffill().shift(1)
    last_sl = sl_price.ffill().shift(1)
    up_valid = (up_raw & (d["close"] > last_sh)).fillna(False).to_numpy()
    down_valid = (down_raw & (d["close"] < last_sl)).fillna(False).to_numpy()

    bearish, bullish = closes < opens, closes > opens
    idx_last_bearish = last_true_idx(bearish)
    idx_last_bullish = last_true_idx(bullish)

    enter_long = np.zeros(n, dtype=bool)
    enter_short = np.zeros(n, dtype=bool)
    stop_events = []
    n_ob_formed = 0
    n_entries = 0

    for i in np.nonzero(up_valid)[0]:            # bullish impulse -> support OB
        j = i - bars_move + 1
        if j - 1 < 0:
            continue
        ob_idx = idx_last_bearish[j - 1]
        if ob_idx < 0:
            continue
        oh, ol = highs[ob_idx], lows[ob_idx]
        n_ob_formed += 1
        mid = (oh + ol) / 2.0
        level = mid if touch == "50pct" else ol
        lo_s, hi_s = i + 1, min(n, i + 1 + max_wait_bars)
        if not breaker:
            for t in range(lo_s, hi_s):
                if lows[t] <= level:
                    enter_long[t] = True
                    n_entries += 1
                    stop_events.append((t, max((closes[t] - ol) / closes[t] * 100, 0.05)))
                    break
        else:
            break_t = None
            for t in range(lo_s, hi_s):
                if closes[t] < ol:
                    break_t = t
                    break
                if lows[t] <= level:
                    break_t = -1
                    break
            if break_t is not None and break_t > 0:
                lo2, hi2 = break_t + 1, min(n, break_t + 1 + max_wait_bars)
                retest_level = mid if touch == "50pct" else oh
                for t2 in range(lo2, hi2):
                    if highs[t2] >= retest_level:
                        enter_short[t2] = True
                        n_entries += 1
                        stop_events.append((t2, max((oh - closes[t2]) / closes[t2] * 100, 0.05)))
                        break

    for i in np.nonzero(down_valid)[0]:           # bearish impulse -> resistance OB
        j = i - bars_move + 1
        if j - 1 < 0:
            continue
        ob_idx = idx_last_bullish[j - 1]
        if ob_idx < 0:
            continue
        oh, ol = highs[ob_idx], lows[ob_idx]
        n_ob_formed += 1
        mid = (oh + ol) / 2.0
        level = mid if touch == "50pct" else oh
        lo_s, hi_s = i + 1, min(n, i + 1 + max_wait_bars)
        if not breaker:
            for t in range(lo_s, hi_s):
                if highs[t] >= level:
                    enter_short[t] = True
                    n_entries += 1
                    stop_events.append((t, max((oh - closes[t]) / closes[t] * 100, 0.05)))
                    break
        else:
            break_t = None
            for t in range(lo_s, hi_s):
                if closes[t] > oh:
                    break_t = t
                    break
                if highs[t] >= level:
                    break_t = -1
                    break
            if break_t is not None and break_t > 0:
                lo2, hi2 = break_t + 1, min(n, break_t + 1 + max_wait_bars)
                retest_level = mid if touch == "50pct" else ol
                for t2 in range(lo2, hi2):
                    if lows[t2] <= retest_level:
                        enter_long[t2] = True
                        n_entries += 1
                        stop_events.append((t2, max((closes[t2] - ol) / closes[t2] * 100, 0.05)))
                        break

    stop_pct = stop_from_train_events(stop_events, i_tr, fallback=1.5)
    events = {
        "n_impulse_up": int(up_valid.sum()), "n_impulse_down": int(down_valid.sum()),
        "n_ob_formed": n_ob_formed, "n_entries": n_entries,
    }
    return (pd.Series(enter_long, index=d.index), pd.Series(enter_short, index=d.index),
            stop_pct, events)


def family1_order_blocks(frames, funding, meta):
    rows = []
    for tf in TIMEFRAMES:
        d, f = frames[tf], funding[tf]
        i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
        med_baseline = meta[tf]["med_baseline"]
        max_wait_bars = hours_to_bars(d, 48)
        for mult in (2, 3):
            for bars_move in (1, 3):
                for touch in ("50pct", "sweep"):
                    for breaker in (False, True):
                        el, es, stop_pct, ev = order_block_engine(
                            d, i_tr, med_baseline, mult, bars_move, touch,
                            breaker, max_wait_bars)
                        for target_mult in (2.0, 3.0):
                            target_pct = target_mult * stop_pct
                            sig = day_trade_signal(d, el, es, max_wait_bars)
                            tr, va = score(d, sig, f, i_tr, i_va,
                                           stop_pct=stop_pct, target_pct=target_pct)
                            kind = "BREAKER" if breaker else "base"
                            cfg = (f"{kind} X{mult}x/{bars_move}bar touch={touch} "
                                   f"tgt{target_mult:.0f}xstop hold48h")
                            row = mk_row("1-order-block", cfg, tf, tr, va,
                                          stop_pct, target_pct, 48)
                            row.update({"n_impulse_up": ev["n_impulse_up"],
                                        "n_impulse_down": ev["n_impulse_down"],
                                        "n_ob_formed": ev["n_ob_formed"],
                                        "n_signal_events": ev["n_entries"],
                                        "context": None})
                            rows.append(row)
    return rows


# ===========================================================================
# FAMILY 2 — REJECTION CANDLES
# ===========================================================================

def context_bottom_top(d, context_type, roll_lo, roll_hi, daily_sma_al, tol=0.005):
    if context_type == "none":
        true_series = pd.Series(True, index=d.index)
        return true_series, true_series
    if context_type == "sma50":
        lo_ref = hi_ref = daily_sma_al
    else:
        lo_ref, hi_ref = roll_lo, roll_hi
    near_bottom = ((d["low"] - lo_ref).abs() / lo_ref <= tol).fillna(False)
    near_top = ((d["high"] - hi_ref).abs() / hi_ref <= tol).fillna(False)
    return near_bottom, near_top


def pin_bar_signals(d, wick_mult, context_type, daily_sma_al):
    o, h, l, c = d["open"], d["high"], d["low"], d["close"]
    body = (c - o).abs()
    upper_wick = h - pd.concat([c, o], axis=1).max(axis=1)
    lower_wick = pd.concat([c, o], axis=1).min(axis=1) - l
    rng = (h - l).replace(0, np.nan)
    close_pos = (c - l) / rng

    roll20_lo, roll20_hi = l.rolling(20).min().shift(1), h.rolling(20).max().shift(1)
    roll55_lo, roll55_hi = l.rolling(55).min().shift(1), h.rolling(55).max().shift(1)
    roll_lo, roll_hi = (roll20_lo, roll20_hi) if context_type == "roll20" else (roll55_lo, roll55_hi)
    near_bottom, near_top = context_bottom_top(d, context_type, roll_lo, roll_hi, daily_sma_al)

    bullish_pin = (lower_wick >= wick_mult * body) & (close_pos >= 0.67) & near_bottom
    bearish_pin = (upper_wick >= wick_mult * body) & (close_pos <= 0.33) & near_top
    return bullish_pin.fillna(False), bearish_pin.fillna(False)


def engulfing_signals(d, context_type, daily_sma_al):
    o, h, l, c = d["open"], d["high"], d["low"], d["close"]
    po, pc = o.shift(1), c.shift(1)
    bull_engulf = (c > o) & (pc < po) & (c >= po) & (o <= pc)
    bear_engulf = (c < o) & (pc > po) & (c <= po) & (o >= pc)

    roll20_lo, roll20_hi = l.rolling(20).min().shift(1), h.rolling(20).max().shift(1)
    roll55_lo, roll55_hi = l.rolling(55).min().shift(1), h.rolling(55).max().shift(1)
    roll_lo, roll_hi = (roll20_lo, roll20_hi) if context_type == "roll20" else (roll55_lo, roll55_hi)
    near_bottom, near_top = context_bottom_top(d, context_type, roll_lo, roll_hi, daily_sma_al)

    return (bull_engulf & near_bottom).fillna(False), (bear_engulf & near_top).fillna(False)


def inside_bar_signals(d, inside_n, champ_al, gated):
    high, low, close = d["high"], d["low"], d["close"]
    mother_high, mother_low = high.shift(inside_n), low.shift(inside_n)
    ok = pd.Series(True, index=d.index)
    for k in range(0, inside_n):
        ok &= (high.shift(k) <= mother_high) & (low.shift(k) >= mother_low)
    pattern_confirmed = ok.fillna(False)

    pc_shift = pattern_confirmed.shift(1).fillna(False)
    mh_shift, ml_shift = mother_high.shift(1), mother_low.shift(1)
    enter_long = pc_shift & (close > mh_shift)
    enter_short = pc_shift & (close < ml_shift)
    enter_long, enter_short = apply_trend_gate(enter_long, enter_short, champ_al, gated)

    range_pct = ((mother_high - mother_low) / d["close"] * 100).where(pattern_confirmed)
    return enter_long.fillna(False), enter_short.fillna(False), range_pct, pattern_confirmed


def family2a_pin_bars(frames, funding, meta, daily_sma_al):
    rows = []
    for tf in TIMEFRAMES:
        d, f = frames[tf], funding[tf]
        i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
        med_atr = meta[tf]["med_atr"]
        mh_bars = hours_to_bars(d, 24)
        for wick_mult in (2, 3):
            for context_type in ("roll20", "roll55", "sma50", "none"):
                el, es = pin_bar_signals(d, wick_mult, context_type, daily_sma_al[tf])
                n_events = int((el | es).sum())
                for stop_mult in (1.0, 1.5):
                    stop_pct = min(max(stop_mult * med_atr, STOP_FLOOR_PCT), STOP_CAP_PCT)
                    for target_mult in (2.0, 3.0):
                        target_pct = target_mult * stop_pct
                        sig = day_trade_signal(d, el, es, mh_bars)
                        tr, va = score(d, sig, f, i_tr, i_va,
                                       stop_pct=stop_pct, target_pct=target_pct)
                        cfg = (f"wick{wick_mult}x ctx={context_type} stop{stop_mult:.1f}xATR "
                               f"tgt{target_mult:.0f}xstop hold24h")
                        row = mk_row("2a-pin-bar", cfg, tf, tr, va, stop_pct, target_pct, 24)
                        row.update({"n_signal_events": n_events, "context": context_type})
                        rows.append(row)
    return rows


def family2b_engulfing(frames, funding, meta, daily_sma_al):
    rows = []
    for tf in TIMEFRAMES:
        d, f = frames[tf], funding[tf]
        i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
        med_atr = meta[tf]["med_atr"]
        mh_bars = hours_to_bars(d, 24)
        for context_type in ("roll20", "roll55", "sma50", "none"):
            el, es = engulfing_signals(d, context_type, daily_sma_al[tf])
            n_events = int((el | es).sum())
            for stop_mult in (1.0, 1.5):
                stop_pct = min(max(stop_mult * med_atr, STOP_FLOOR_PCT), STOP_CAP_PCT)
                for target_mult in (2.0, 3.0):
                    target_pct = target_mult * stop_pct
                    sig = day_trade_signal(d, el, es, mh_bars)
                    tr, va = score(d, sig, f, i_tr, i_va,
                                   stop_pct=stop_pct, target_pct=target_pct)
                    cfg = (f"engulf ctx={context_type} stop{stop_mult:.1f}xATR "
                           f"tgt{target_mult:.0f}xstop hold24h")
                    row = mk_row("2b-engulfing", cfg, tf, tr, va, stop_pct, target_pct, 24)
                    row.update({"n_signal_events": n_events, "context": context_type})
                    rows.append(row)
    return rows


def family2c_inside_bar(frames, funding, meta, champ_al):
    rows = []
    for tf in TIMEFRAMES:
        d, f = frames[tf], funding[tf]
        i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
        mh_bars = hours_to_bars(d, 12)
        for inside_n in (1, 2):
            for gated in (True, False):
                el, es, range_pct, confirmed = inside_bar_signals(
                    d, inside_n, champ_al[tf], gated)
                n_events = int(confirmed.sum())
                med_range = float(range_pct.iloc[:i_tr].dropna().median()) if \
                    range_pct.iloc[:i_tr].notna().any() else 1.0
                stop_pct = min(max(med_range, STOP_FLOOR_PCT), STOP_CAP_PCT)
                for target_mult in (2.0, 3.0):
                    target_pct = target_mult * stop_pct
                    sig = day_trade_signal(d, el, es, mh_bars)
                    tr, va = score(d, sig, f, i_tr, i_va,
                                   stop_pct=stop_pct, target_pct=target_pct)
                    gate_lbl = "gated" if gated else "ungated"
                    cfg = (f"inside{inside_n} {gate_lbl} tgt{target_mult:.0f}xmotherrange "
                           f"hold12h")
                    row = mk_row("2c-inside-bar", cfg, tf, tr, va, stop_pct, target_pct, 12)
                    row.update({"n_signal_events": n_events, "context": None})
                    rows.append(row)
    return rows


# ===========================================================================
# FAMILY 3 — VOLATILITY COMPRESSION
# ===========================================================================

def nr_signals(d, N):
    rng = d["high"] - d["low"]
    is_nr = (rng == rng.rolling(N).min()).fillna(False)
    enter_long = is_nr.shift(1).fillna(False) & (d["close"] > d["high"].shift(1))
    enter_short = is_nr.shift(1).fillna(False) & (d["close"] < d["low"].shift(1))
    return enter_long.fillna(False), enter_short.fillna(False), is_nr


def bollinger_bandwidth(d, n=20):
    sma = d["close"].rolling(n).mean()
    std = d["close"].rolling(n).std()
    upper, lower = sma + 2 * std, sma - 2 * std
    bw = (upper - lower) / sma * 100
    return bw, upper, lower


def bbwidth_signals(d, pct):
    bw, upper, lower = bollinger_bandwidth(d, 20)
    window = max(30, hours_to_bars(d, 365 * 24))
    min_periods = max(30, window // 10)
    thresh = bw.rolling(window, min_periods=min_periods).quantile(pct / 100).shift(1)
    is_squeeze = (bw < thresh).fillna(False)
    enter_long = (is_squeeze & (d["close"] > upper)).fillna(False)
    enter_short = (is_squeeze & (d["close"] < lower)).fillna(False)
    return enter_long, enter_short, is_squeeze


def range_compression_signals(d, L, mult):
    rng_prior = (d["high"].rolling(L).max() - d["low"].rolling(L).min()).shift(1)
    window = max(30, hours_to_bars(d, 180 * 24))
    min_periods = max(30, window // 10)
    trail_med = rng_prior.rolling(window, min_periods=min_periods).median().shift(1)
    is_compressed = (rng_prior < mult * trail_med).fillna(False)
    roll_high, roll_low = d["high"].rolling(L).max().shift(1), d["low"].rolling(L).min().shift(1)
    enter_long = (is_compressed & (d["close"] > roll_high)).fillna(False)
    enter_short = (is_compressed & (d["close"] < roll_low)).fillna(False)
    return enter_long, enter_short, is_compressed


def family3a_nr(frames, funding, meta, champ_al):
    rows = []
    for tf in TIMEFRAMES:
        d, f = frames[tf], funding[tf]
        i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
        med_atr = meta[tf]["med_atr"]
        mh_bars = hours_to_bars(d, 24)
        for N in (4, 7):
            el0, es0, is_nr = nr_signals(d, N)
            n_events = int(is_nr.sum())
            for gated in (True, False):
                el, es = apply_trend_gate(el0, es0, champ_al[tf], gated)
                for stop_mult in (1.0, 1.5):
                    stop_pct = min(max(stop_mult * med_atr, STOP_FLOOR_PCT), STOP_CAP_PCT)
                    for target_mult in (2.0, 3.0):
                        target_pct = target_mult * stop_pct
                        sig = day_trade_signal(d, el, es, mh_bars)
                        tr, va = score(d, sig, f, i_tr, i_va,
                                       stop_pct=stop_pct, target_pct=target_pct)
                        gate_lbl = "gated" if gated else "ungated"
                        cfg = (f"NR{N} {gate_lbl} stop{stop_mult:.1f}xATR "
                               f"tgt{target_mult:.0f}xstop hold24h")
                        row = mk_row("3a-nr-squeeze", cfg, tf, tr, va, stop_pct, target_pct, 24)
                        row.update({"n_signal_events": n_events, "context": None})
                        rows.append(row)
    return rows


def family3b_bbwidth(frames, funding, meta, champ_al):
    rows = []
    for tf in TIMEFRAMES:
        d, f = frames[tf], funding[tf]
        i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
        med_atr = meta[tf]["med_atr"]
        mh_bars = hours_to_bars(d, 48)
        for pct in (10, 20):
            el0, es0, is_sq = bbwidth_signals(d, pct)
            n_events = int(is_sq.sum())
            for gated in (True, False):
                el, es = apply_trend_gate(el0, es0, champ_al[tf], gated)
                sig = day_trade_signal(d, el, es, mh_bars)
                stop_pct = min(max(1.0 * med_atr, STOP_FLOOR_PCT), STOP_CAP_PCT)
                gate_lbl = "gated" if gated else "ungated"
                for exit_style, target_mult in (("tgt2xATR", 2.0), ("tgt3xATR", 3.0),
                                                 ("trailing", None)):
                    target_pct = target_mult * stop_pct if target_mult else None
                    tr, va = score(d, sig, f, i_tr, i_va,
                                   stop_pct=stop_pct, target_pct=target_pct)
                    cfg = (f"BBpct{pct} {gate_lbl} {exit_style} stop{stop_pct:.2f}% hold48h")
                    row = mk_row("3b-bbwidth-squeeze", cfg, tf, tr, va, stop_pct,
                                  target_pct, 48)
                    row.update({"n_signal_events": n_events, "context": None})
                    rows.append(row)
    return rows


def family3c_range_compression(frames, funding, meta, champ_al):
    rows = []
    for tf in TIMEFRAMES:
        d, f = frames[tf], funding[tf]
        i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
        med_atr = meta[tf]["med_atr"]
        mh_bars = hours_to_bars(d, 24)
        for L in (12, 24):
            for cmult in (0.5, 0.7):
                el0, es0, is_c = range_compression_signals(d, L, cmult)
                n_events = int(is_c.sum())
                for gated in (True, False):
                    el, es = apply_trend_gate(el0, es0, champ_al[tf], gated)
                    for stop_mult in (1.0, 1.5):
                        stop_pct = min(max(stop_mult * med_atr, STOP_FLOOR_PCT), STOP_CAP_PCT)
                        for target_mult in (2.0, 3.0):
                            target_pct = target_mult * stop_pct
                            sig = day_trade_signal(d, el, es, mh_bars)
                            tr, va = score(d, sig, f, i_tr, i_va,
                                           stop_pct=stop_pct, target_pct=target_pct)
                            gate_lbl = "gated" if gated else "ungated"
                            cfg = (f"L{L} <{cmult:.1f}xmed {gate_lbl} stop{stop_mult:.1f}xATR "
                                   f"tgt{target_mult:.0f}xstop hold24h")
                            row = mk_row("3c-range-compression", cfg, tf, tr, va,
                                          stop_pct, target_pct, 24)
                            row.update({"n_signal_events": n_events, "context": None})
                            rows.append(row)
    return rows


# ===========================================================================
# CROSS-FAMILY: simple FVG recompute + overlap count (1h)
# ===========================================================================

def simple_fvg_bars(d):
    """Classic 3-candle fair value gap, no thresholds: bullish FVG at bar i
    if low[i] > high[i-2] (gap between candle i-2's high and candle i's low,
    spanning candle i-1); bearish FVG if high[i] < low[i-2]. Returns a
    boolean Series marking bar i as an FVG-forming bar (either direction)."""
    bull = d["low"] > d["high"].shift(2)
    bear = d["high"] < d["low"].shift(2)
    return (bull | bear).fillna(False)


def fvg_overlap_note(d, ob_entries_bool):
    fvg = simple_fvg_bars(d).to_numpy()
    ob = ob_entries_bool.to_numpy()
    n_fvg, n_ob = int(fvg.sum()), int(ob.sum())
    exact = int((fvg & ob).sum())
    # +/-2 bar tolerance overlap
    ob_idx = np.nonzero(ob)[0]
    fvg_idx_set = set(np.nonzero(fvg)[0].tolist())
    near = 0
    for i in ob_idx:
        if any((i + off) in fvg_idx_set for off in range(-2, 3)):
            near += 1
    return {"n_fvg_bars": n_fvg, "n_ob_entries": n_ob,
            "exact_bar_overlap": exact, "within_2bar_overlap": near}


# ===========================================================================
# main
# ===========================================================================

def main():
    print("Loading cached data (no network calls needed)...")
    frames = {tf: fetch_bybit_deep(tf, "BTCUSDT") for tf in ("1h", "4h")}
    daily = fetch_bybit_deep("1d", "BTCUSDT")
    funding_hist = fetch_funding_history("BTCUSDT")
    funding = {tf: align_funding(frames[tf], funding_hist) for tf in TIMEFRAMES}

    meta = {}
    for tf in TIMEFRAMES:
        d = frames[tf]
        n, i_tr, i_va = split_points(d)
        atr_pct = atr(d, 14) / d["close"] * 100
        med_atr_train = float(atr_pct.iloc[:i_tr].median())
        ret1 = d["close"].pct_change() * 100
        med_baseline_train = float(ret1.iloc[:i_tr].abs().median())
        meta[tf] = {"n": n, "i_tr": i_tr, "i_va": i_va,
                    "med_atr": med_atr_train, "med_baseline": med_baseline_train}
        print(f"  {tf}: {n} bars, {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
              f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed) | "
              f"median train ATR%={med_atr_train:.3f}% | median |1-bar ret|={med_baseline_train:.4f}%")

    frame4h = frames["4h"]
    champ4h = vol_gated_ma(frame4h, **CHAMP_KW)
    print(f"  champion (4h vol_gated_ma {CHAMP_KW}) time-in-market: "
          f"{(champ4h == 1).mean() * 100:.1f}% of bars")
    champ_al = {tf: champ_aligned(frame4h, champ4h, frames[tf]) for tf in TIMEFRAMES}

    daily_sma50 = daily["close"].rolling(50).mean()
    daily_sma_al = {tf: daily_sma_aligned(daily, daily_sma50, frames[tf]) for tf in TIMEFRAMES}

    all_rows = []
    print("\nFAMILY 1 — order blocks...")
    r = family1_order_blocks(frames, funding, meta); all_rows += r
    print(f"  {len(r)} configs")
    print("FAMILY 2a — pin bars...")
    r = family2a_pin_bars(frames, funding, meta, daily_sma_al); all_rows += r
    print(f"  {len(r)} configs")
    print("FAMILY 2b — engulfing...")
    r = family2b_engulfing(frames, funding, meta, daily_sma_al); all_rows += r
    print(f"  {len(r)} configs")
    print("FAMILY 2c — inside-bar breakout...")
    r = family2c_inside_bar(frames, funding, meta, champ_al); all_rows += r
    print(f"  {len(r)} configs")
    print("FAMILY 3a — NR squeeze...")
    r = family3a_nr(frames, funding, meta, champ_al); all_rows += r
    print(f"  {len(r)} configs")
    print("FAMILY 3b — BB-width squeeze...")
    r = family3b_bbwidth(frames, funding, meta, champ_al); all_rows += r
    print(f"  {len(r)} configs")
    print("FAMILY 3c — range-compression breakout...")
    r = family3c_range_compression(frames, funding, meta, champ_al); all_rows += r
    print(f"  {len(r)} configs")

    df = pd.DataFrame(all_rows)
    print(f"\n{len(df)} total configs. Verdict counts:")
    print(df["verdict"].value_counts().to_string())

    survivors = df[df["verdict"] == "SURVIVOR"]
    near = df[df["verdict"] == "INSUFFICIENT-SAMPLE"]
    cols = ["family", "config", "tf", "tr_n", "tr_exp", "va_n", "va_exp",
            "med_hold_h", "mean_hold_h", "n_signal_events"]
    print(f"\nSURVIVORS: {len(survivors)}")
    if len(survivors):
        print(survivors[cols].to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    print(f"\nINSUFFICIENT-SAMPLE: {len(near)}")
    if len(near):
        print(near[cols].to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    # ---- required analysis: context-vs-no-context (pin bars + engulfing) ----
    print("\n=== CONTEXT-VS-NO-CONTEXT (family 2a+2b pooled) ===")
    ctx_df = df[df["family"].isin(["2a-pin-bar", "2b-engulfing"])]
    ctx_summary = ctx_df.groupby("context").agg(
        n_configs=("tr_exp", "size"),
        mean_tr_exp=("tr_exp", "mean"),
        mean_tr_win=("tr_win%", "mean"),
        survivors=("verdict", lambda s: (s == "SURVIVOR").sum()),
        mean_events=("n_signal_events", "mean"),
    )
    print(ctx_summary.to_string(float_format=lambda x: f"{x:,.2f}"))

    # ---- required analysis: event-frequency table (order blocks + rejection) ----
    print("\n=== EVENT FREQUENCY (raw signal trigger counts, pre-test region) ===")
    freq_cols = ["family", "tf", "config", "n_signal_events"]
    ob_freq = df[df["family"] == "1-order-block"][
        ["tf", "config", "n_impulse_up", "n_impulse_down", "n_ob_formed", "n_signal_events"]]
    print("Order blocks (impulse/ob-formed/entries):")
    print(ob_freq.drop_duplicates(subset=["tf", "config"]).to_string(index=False))
    print("\nRejection + compression event counts by family/tf (min/median/max signal events):")
    other_freq = df[df["family"] != "1-order-block"].groupby(["family", "tf"])["n_signal_events"] \
        .agg(["min", "median", "max"])
    print(other_freq.to_string(float_format=lambda x: f"{x:,.0f}"))

    # ---- cross-family: FVG overlap on 1h, flagship OB config ----
    print("\n=== CROSS-FAMILY: order blocks vs simple FVG recompute (1h) ===")
    d1h, i_tr_1h = frames["1h"], meta["1h"]["i_tr"]
    max_wait_1h = hours_to_bars(d1h, 48)
    el_flag, es_flag, stop_flag, ev_flag = order_block_engine(
        d1h, i_tr_1h, meta["1h"]["med_baseline"], mult=2, bars_move=1,
        touch="50pct", breaker=False, max_wait_bars=max_wait_1h)
    ob_entries_bool = (el_flag | es_flag)
    overlap = fvg_overlap_note(d1h, ob_entries_bool)
    print(f"  Flagship OB config (X2x/1bar, 50% touch, base, 1h): {overlap}")

    print("\nDone. Compose step57_results.md from this output.")
    return df, ctx_summary, ob_freq, other_freq, overlap


if __name__ == "__main__":
    main()
