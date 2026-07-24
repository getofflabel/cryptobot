"""
step58_divergence_mtf.py — round 58: DIVERGENCES + OSCILLATOR REGIME TOOLS +
MULTI-TIMEFRAME ALIGNMENT on BTC, formalized for the first time in this repo.

Run:  python3 step58_divergence_mtf.py

Research only — no live orders, no commits. Touches nothing outside this
file / step58_results.md. Concurrent agents own step55/56/57 — not touched.

THREE FAMILIES

  1. DIVERGENCES at confirmed swings — RSI(14) and MACD-histogram, regular
     AND hidden (continuation) flavors, on 1h and 4h.
  2. OSCILLATOR REGIME TOOLS — ADX / Stochastic / RSI-band tested as ENTRY
     overlays on a fixed base (1h donchian-20 breakout long). Head-to-head:
     does the filter improve val expectancy, or just cut sample size?
  3. MULTI-TIMEFRAME ALIGNMENT — 4h BIAS -> 1h SETUP -> {1h, 15m} TRIGGER,
     tested as a stacking ladder (full vs bias+setup vs setup-only) to see
     whether each added timeframe layer earns its keep.

PLUMBING REUSE (per the round-58 brief)
  - Data: fetch_bybit_deep (step7_deep_search) + fetch_funding_history /
    align_funding (step11_round6) — all cache hits, no network calls.
  - Gauntlet mechanics: split_points / score / verdict_for / hold_stats /
    day_trade_signal / champ_aligned / bar_hours / hours_to_bars / CHAMP_KW
    / HARD_STOP_CAP / MIN_TRAIN_TRADES / MIN_VAL_TRADES are imported
    directly from step43_daytrade rather than reimplemented. champ_aligned
    is generalized here (align_signal) to also project a 1h series down to
    15m — the existing helper hardcodes a 4h source.
  - Chronological 60/20/20 split, test sealed (never sliced), selection by
    TRAIN expectancy only, val checked once. Same discipline as every prior
    round.

NO-LOOKAHEAD FOR SWING CONFIRMATION (the part that's new to this repo)
  swings(k): a bar i is a confirmed swing high/low once a CENTERED window
  of radius k around it (i-k .. i+k) is fully known to have i at its
  extreme. That centered window is only fully known once bar i+k has
  printed — so the swing "exists," for signal purposes, starting at bar
  i+k, not at bar i. Implementation: compute the centered rolling
  extreme (which technically peeks forward within the window), then
  .shift(k) the resulting boolean flag so it only reads True starting at
  the bar where that future information has actually arrived. This is the
  same trick the rest of the codebase uses for session-window closes
  (step43 FAMILY 2) — a boundary condition, not a per-bar peek.

STOP GEOMETRY FOR DIVERGENCES
  backtest.run_backtest takes ONE fixed stop_pct/target_pct for the whole
  run (see step43 header). Divergence stops are naturally per-trade
  ("past the swing extreme"), so — same approximation step43 uses for
  session-breakout/VWAP-fade — we take the TRAIN-only median distance
  from entry close to the qualifying swing extreme, plus a stated buffer,
  and hold that fixed across train+val. Two buffer sizes are tested
  (0.15%, 0.35%) since the buffer choice materially changes both the stop
  distance and the whipsaw rate; this is a legitimate second dimension of
  the family, not padding.
"""

import numpy as np
import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step43_daytrade import (
    CHAMP_KW, HARD_STOP_CAP, MIN_TRAIN_TRADES, MIN_VAL_TRADES,
    bar_hours, champ_aligned, day_trade_signal, hold_stats, hours_to_bars,
    score, split_points, verdict_for,
)
from strategy import atr, donchian_breakout, rsi, vol_gated_ma

STOP_CAP_SWING = 4.0     # % — swing-based stops run wider than day-trade's 1.7% cap
STOP_CAP_MTF = 3.0       # % — ATR-based MTF stops, tighter than swing but not day-trade tight
MAKER_ROUND_TRIP_BPS = 2 * (2.0 + 1.0 + 2.0)   # maker fee + half-spread + slippage, both fills = 10bps
COST_FLOOR_15M_BPS = 9.0   # the brief's stated ~9bps cost-floor check for sparse 15m entries


# ---------------------------------------------------------------------------
# shared helpers not already in step43
# ---------------------------------------------------------------------------

def align_signal(src_frame, src_series, target_frame, src_bar_hours):
    """Generalization of step43.champ_aligned: project ANY series computed
    on src_frame down onto a finer target_frame, available only from the
    close of the src bar that produced it (open_time + src_bar_hours) —
    never from a still-open bar. Same no-lookahead discipline, just not
    hardcoded to a 4h source."""
    avail = pd.DataFrame({
        "timestamp": src_frame["timestamp"] + pd.Timedelta(hours=src_bar_hours),
        "val": src_series.fillna(0.0).to_numpy(),
    }).sort_values("timestamp")
    merged = pd.merge_asof(target_frame[["timestamp"]].sort_values("timestamp"),
                            avail, on="timestamp", direction="backward")
    return merged["val"].fillna(0.0).reset_index(drop=True)


def macd_hist(close, fast=12, slow=26, signal=9):
    """MACD histogram: MACD line minus its own signal-line EMA. Standard
    12/26/9. Purely causal (EMAs only look backward) — no shift needed."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    sig_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line - sig_line


def adx(d, n=14):
    """Wilder's ADX(14): trend-strength gauge, 0-100, direction-agnostic."""
    high, low, close = d["high"], d["low"], d["close"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(),
                     (low - prev_close).abs()], axis=1).max(axis=1)
    atr_n = tr.ewm(alpha=1 / n, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=d.index).ewm(alpha=1 / n, adjust=False).mean() / atr_n
    minus_di = 100 * pd.Series(minus_dm, index=d.index).ewm(alpha=1 / n, adjust=False).mean() / atr_n
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, float("nan"))
    return dx.ewm(alpha=1 / n, adjust=False).mean()


def stochastic_k(d, k_n=14, d_n=3):
    """Stochastic %K (and its %D smoothing), 0-100."""
    low_n = d["low"].rolling(k_n).min()
    high_n = d["high"].rolling(k_n).max()
    k = 100 * (d["close"] - low_n) / (high_n - low_n).replace(0, float("nan"))
    return k, k.rolling(d_n).mean()


def swings(high, low, k):
    """Bar i is a confirmed swing high/low once bars i-k..i+k are all known
    (see module docstring). Returns TWO boolean series already shifted so a
    True at bar j means 'bar j-k was a confirmed extreme, as of bar j's
    close' — directly usable at bar j with no further lookahead."""
    roll_max = high.rolling(2 * k + 1, center=True).max()
    roll_min = low.rolling(2 * k + 1, center=True).min()
    is_high = (high == roll_max).fillna(False)
    is_low = (low == roll_min).fillna(False)
    return is_high.shift(k).fillna(False), is_low.shift(k).fillna(False)


def mk_row(family, cfg, tf, tr, va, **extra):
    med_h, mean_h = hold_stats(tr, va)
    row = {
        "family": family, "config": cfg, "tf": tf,
        "tr_n": len(tr.trades), "tr_exp": tr.expectancy,
        "tr_win%": tr.win_rate * 100, "tr_ret%": tr.total_return_pct,
        "tr_dd%": tr.max_drawdown_pct,
        "va_n": len(va.trades), "va_exp": va.expectancy,
        "va_win%": va.win_rate * 100, "va_ret%": va.total_return_pct,
        "va_dd%": va.max_drawdown_pct,
        "med_hold_h": med_h, "mean_hold_h": mean_h,
        "verdict": verdict_for(tr, va),
    }
    row.update(extra)
    return row


def trades_per_year(tr, va, tr_span_days, va_span_days):
    n = len(tr.trades) + len(va.trades)
    span_yrs = (tr_span_days + va_span_days) / 365.25
    return n / span_yrs if span_yrs > 0 else float("nan")


# ---------------------------------------------------------------------------
# FAMILY 1 — divergences at confirmed swings
# ---------------------------------------------------------------------------

def divergence_events(d, osc, k, champ_al):
    """One O(n) pass. At each confirmed swing low/high, compares against
    the PREVIOUS confirmed swing of the same type (price vs oscillator) to
    classify regular vs hidden divergence. Returns four boolean event
    series (long_reg, short_reg, long_hidden, short_hidden) plus the two
    swing-extreme price series (for stop placement) — all length n, all
    already lookahead-safe per swings().

    Regular bullish : price LOWER low, oscillator HIGHER low  -> long
    Hidden  bullish : price HIGHER low, oscillator LOWER low, gated to the
                       4h champion's uptrend (continuation flavor)  -> long
    Regular bearish : price HIGHER high, oscillator LOWER high -> short
    Hidden  bearish : price LOWER high, oscillator HIGHER high, gated to
                       the 4h champion's downtrend                  -> short
    """
    conf_high, conf_low = swings(d["high"], d["low"], k)
    conf_high, conf_low = conf_high.to_numpy(), conf_low.to_numpy()
    price_h, price_l = d["high"].to_numpy(), d["low"].to_numpy()
    osc_v = osc.to_numpy()
    champ_v = champ_al.to_numpy()
    n = len(d)

    long_reg = np.zeros(n, dtype=bool)
    short_reg = np.zeros(n, dtype=bool)
    long_hid = np.zeros(n, dtype=bool)
    short_hid = np.zeros(n, dtype=bool)
    low_extreme = np.full(n, np.nan)
    high_extreme = np.full(n, np.nan)

    prev_low = None    # (price, osc) at the previous confirmed swing low's origin
    prev_high = None
    for j in range(n):
        if conf_low[j]:
            origin = j - k
            p, o = price_l[origin], osc_v[origin]
            if prev_low is not None and not (np.isnan(o) or np.isnan(prev_low[1])):
                p0, o0 = prev_low
                if p < p0 and o > o0:
                    long_reg[j] = True
                    low_extreme[j] = p
                elif p > p0 and o < o0 and champ_v[j] == 1:
                    long_hid[j] = True
                    low_extreme[j] = p
            prev_low = (p, o)
        if conf_high[j]:
            origin = j - k
            p, o = price_h[origin], osc_v[origin]
            if prev_high is not None and not (np.isnan(o) or np.isnan(prev_high[1])):
                p0, o0 = prev_high
                if p > p0 and o < o0:
                    short_reg[j] = True
                    high_extreme[j] = p
                elif p < p0 and o > o0 and champ_v[j] == 0:
                    short_hid[j] = True
                    high_extreme[j] = p
            prev_high = (p, o)

    idx = d.index
    return (pd.Series(long_reg, index=idx), pd.Series(short_reg, index=idx),
            pd.Series(long_hid, index=idx), pd.Series(short_hid, index=idx),
            pd.Series(low_extreme, index=idx), pd.Series(high_extreme, index=idx))


def swing_stop_pct(entry_close, extreme, entries_mask, i_tr, buffer_pct, cap):
    """TRAIN-only median distance from entry close to the qualifying swing
    extreme, plus a stated buffer, hard-capped. Fixed across train+val —
    same approximation pattern as step43's session-breakout/VWAP-fade
    (run_backtest takes one stop_pct for the whole run)."""
    dist = ((entry_close - extreme).abs() / entry_close * 100)
    train_dist = dist.iloc[:i_tr][entries_mask.iloc[:i_tr]]
    if len(train_dist) == 0 or train_dist.isna().all():
        return cap
    return min(float(train_dist.median()) + buffer_pct, cap)


def family1_divergences(frames, funding, meta, champ4h, frame4h):
    rows = []
    oscillators = {
        "RSI14": lambda d: rsi(d["close"], 14),
        "MACDhist": lambda d: macd_hist(d["close"]),
    }
    for tf in ("1h", "4h"):
        d, f = frames[tf], funding[tf]
        n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]
        champ_al = champ4h if tf == "4h" else champ_aligned(frame4h, champ4h, d)
        for osc_name, osc_fn in oscillators.items():
            osc = osc_fn(d)
            for k in (5, 8):
                (long_reg, short_reg, long_hid, short_hid,
                 low_ext, high_ext) = divergence_events(d, osc, k, champ_al)
                for flavor, el, es, ext_l, ext_h in (
                    ("regular", long_reg, short_reg, low_ext, high_ext),
                    ("hidden", long_hid, short_hid, low_ext, high_ext),
                ):
                    if el.sum() == 0 and es.sum() == 0:
                        rows.append(mk_row(
                            "1-divergence", f"{osc_name} k{k} {flavor} — no qualifying swings",
                            tf, *score(d, day_trade_signal(d, el, es, 1), f, i_tr, i_va),
                            oscillator=osc_name, k=k, flavor=flavor, buffer_pct=None,
                            stop_pct=None, target_pct=None, max_hold_h=None))
                        continue
                    for buffer_pct in (0.15, 0.35):
                        stop_l = swing_stop_pct(d["close"], ext_l, el, i_tr, buffer_pct, STOP_CAP_SWING)
                        stop_s = swing_stop_pct(d["close"], ext_h, es, i_tr, buffer_pct, STOP_CAP_SWING)
                        # one fixed stop_pct per run_backtest call: use the
                        # entry-weighted average of the long/short stop
                        # distances (both directions share one call here).
                        n_l, n_s = int(el.sum()), int(es.sum())
                        stop_pct = ((stop_l * n_l + stop_s * n_s) / (n_l + n_s)
                                    if (n_l + n_s) else STOP_CAP_SWING)
                        for tmult in (2.0, 3.0):
                            target_pct = min(tmult * stop_pct, 3 * STOP_CAP_SWING)
                            for max_hold_h in (48, 96):
                                mh_bars = hours_to_bars(d, max_hold_h)
                                sig = day_trade_signal(d, el, es, mh_bars)
                                tr, va = score(d, sig, f, i_tr, i_va,
                                               stop_pct=stop_pct, target_pct=target_pct)
                                cfg = (f"{osc_name} k{k} {flavor} buf{buffer_pct:.2f}% "
                                       f"tgt{tmult:.0f}x hold{max_hold_h}h")
                                rows.append(mk_row(
                                    "1-divergence", cfg, tf, tr, va,
                                    oscillator=osc_name, k=k, flavor=flavor,
                                    buffer_pct=buffer_pct, stop_pct=stop_pct,
                                    target_pct=target_pct, max_hold_h=max_hold_h))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 2 — oscillator regime tools as overlays on donchian-20 breakout
# ---------------------------------------------------------------------------

def donchian_filtered(d, entry_n, exit_n, entry_filter=None):
    """strategy.donchian_breakout, but the entry condition can be ANDed with
    an extra filter — the EXIT (breach of exit_n low) is always untouched,
    because the question this family asks is whether a filter improves
    ENTRY quality on an already-known base, not a new exit rule."""
    hi = d["high"].rolling(entry_n).max().shift(1)
    lo = d["low"].rolling(exit_n).min().shift(1)
    enter = d["close"] > hi
    exit_ = d["close"] < lo
    if entry_filter is not None:
        enter = enter & entry_filter.fillna(False)
    sig = pd.Series(float("nan"), index=d.index)
    sig[exit_] = 0.0
    sig[enter] = 1.0
    return sig.ffill().fillna(0)


def family2_oscillator_overlays(frames, funding, meta):
    rows = []
    tf = "1h"
    d, f = frames[tf], funding[tf]
    n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]

    adx14 = adx(d, 14)
    stoch_k, _ = stochastic_k(d, 14, 3)
    rsi14 = rsi(d["close"], 14)

    filters = {
        "baseline (no filter)": None,
        "ADX>=20": adx14 >= 20,
        "ADX>=25": adx14 >= 25,
        "Stoch<70 (not-OB)": stoch_k < 70,
        "Stoch<80 (not-OB)": stoch_k < 80,
        "RSI 40-70 band": (rsi14 >= 40) & (rsi14 <= 70),
        "RSI 35-65 band": (rsi14 >= 35) & (rsi14 <= 65),
        "ALL combined (ADX>=20 & Stoch<80 & RSI40-70)":
            (adx14 >= 20) & (stoch_k < 80) & (rsi14 >= 40) & (rsi14 <= 70),
    }

    for exit_n in (10, 20):
        for filt_name, filt in filters.items():
            sig = donchian_filtered(d, entry_n=20, exit_n=exit_n, entry_filter=filt)
            tr, va = score(d, sig, f, i_tr, i_va, execution="maker")
            rows.append(mk_row("2-oscillator-overlay",
                                f"donchian20/{exit_n} + {filt_name}", tf, tr, va,
                                filter_name=filt_name, exit_n=exit_n))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 3 — multi-timeframe alignment (4h bias -> 1h setup -> trigger)
# ---------------------------------------------------------------------------

def four_h_bias(frame4h, champ4h):
    """+1 when the 4h champion trend AND price-vs-SMA50 both say long,
    -1 when both say short, 0 (no bias) otherwise. allow_short=True champ
    is recomputed here (the family1/2 champ4h is long-only 0/1)."""
    champ_ls = vol_gated_ma(frame4h, allow_short=True, **CHAMP_KW)
    sma50 = frame4h["close"].rolling(50).mean()
    above = frame4h["close"] > sma50
    below = frame4h["close"] < sma50
    bias = pd.Series(0.0, index=frame4h.index)
    bias[(champ_ls == 1) & above] = 1.0
    bias[(champ_ls == -1) & below] = -1.0
    return bias


def rsi3_pullback_setup(d, thresh):
    r3 = rsi(d["close"], 3)
    return (r3 < thresh).fillna(False), (r3 > (100 - thresh)).fillna(False)


def fvg_return_setup(d, max_wait_bars=20):
    """3-bar imbalance ('fair value gap') return setup, both directions.
    Bullish FVG: bar i's low > bar i-2's high (a gap nothing traded
    through). Setup fires the first time price dips back INTO that zone
    within max_wait_bars — the classic 'return to the imbalance' pullback
    entry. Bearish mirrors it (gap down, price rallies back up into it).
    Approximation, stated plainly: doesn't invalidate a zone once price
    trades fully through it, and doesn't dedupe re-touches of the same
    zone — acceptable for a research-only sparse-signal family."""
    n = len(d)
    idx_arr = np.arange(n)

    bull_gap = (d["low"] > d["high"].shift(2)).fillna(False)
    bull_bot = d["high"].shift(2).where(bull_gap).ffill()
    bull_top = d["low"].where(bull_gap).ffill()
    bull_gap_idx = pd.Series(np.where(bull_gap, idx_arr, np.nan), index=d.index).ffill()
    bull_age = idx_arr - bull_gap_idx.to_numpy()
    bull_in_zone = (d["low"] <= bull_top) & (d["low"] >= bull_bot)
    bull_setup = (bull_in_zone.fillna(False) & (bull_age > 0) & (bull_age <= max_wait_bars)
                  & bull_gap_idx.notna())

    bear_gap = (d["high"] < d["low"].shift(2)).fillna(False)
    bear_top = d["low"].shift(2).where(bear_gap).ffill()
    bear_bot = d["high"].where(bear_gap).ffill()
    bear_gap_idx = pd.Series(np.where(bear_gap, idx_arr, np.nan), index=d.index).ffill()
    bear_age = idx_arr - bear_gap_idx.to_numpy()
    bear_in_zone = (d["high"] >= bear_bot) & (d["high"] <= bear_top)
    bear_setup = (bear_in_zone.fillna(False) & (bear_age > 0) & (bear_age <= max_wait_bars)
                  & bear_gap_idx.notna())

    return bull_setup.fillna(False), bear_setup.fillna(False)


def reversal_bar(d):
    """1h TRIGGER: a bar that prints a fresh short-term extreme against the
    prior bar but closes back through it — long trigger makes a lower low
    than the prior bar yet closes green and above the prior close; short
    trigger mirrors it."""
    long_trig = ((d["close"] > d["open"]) & (d["low"] < d["low"].shift(1))
                 & (d["close"] > d["close"].shift(1))).fillna(False)
    short_trig = ((d["close"] < d["open"]) & (d["high"] > d["high"].shift(1))
                  & (d["close"] < d["close"].shift(1))).fillna(False)
    return long_trig, short_trig


def ema9_recross(d):
    """15m TRIGGER: close recrosses back above/below its own 9-bar EMA."""
    ema9 = d["close"].ewm(span=9, adjust=False).mean()
    long_trig = ((d["close"] > ema9) & (d["close"].shift(1) <= ema9.shift(1))).fillna(False)
    short_trig = ((d["close"] < ema9) & (d["close"].shift(1) >= ema9.shift(1))).fillna(False)
    return long_trig, short_trig


def stack_entries(setup_l, setup_s, bias_al, trig_l, trig_s, level):
    if level == "setup-only":
        return setup_l, setup_s
    if level == "bias+setup":
        return (setup_l & (bias_al == 1)), (setup_s & (bias_al == -1))
    if level == "full":
        return (setup_l & (bias_al == 1) & trig_l), (setup_s & (bias_al == -1) & trig_s)
    raise ValueError(level)


def family3_mtf_alignment(frames, funding, meta, frame4h, bias4h):
    rows = []
    d1h, f1h = frames["1h"], funding["1h"]
    n1, i_tr1, i_va1 = meta["1h"]["n"], meta["1h"]["i_tr"], meta["1h"]["i_va"]
    med_atr_1h = meta["1h"]["med_atr"]

    d15, f15 = frames["15m"], funding["15m"]
    n15, i_tr15, i_va15 = meta["15m"]["n"], meta["15m"]["i_tr"], meta["15m"]["i_va"]
    med_atr_15 = meta["15m"]["med_atr"]

    bias_on_1h = align_signal(frame4h, bias4h, d1h, 4.0)
    bias_on_15 = align_signal(frame4h, bias4h, d15, 4.0)

    setups_1h = {
        "RSI3<10 pullback": rsi3_pullback_setup(d1h, 10),
        "RSI3<15 pullback": rsi3_pullback_setup(d1h, 15),
        "FVG-return (<=20bar)": fvg_return_setup(d1h, 20),
    }

    trig1_l, trig1_s = reversal_bar(d1h)
    trig15_l_raw, trig15_s_raw = ema9_recross(d15)

    for setup_name, (setup_l_1h, setup_s_1h) in setups_1h.items():
        for trigger_name, tf, d, f, i_tr, i_va, med_atr in (
            ("1h reversal bar", "1h", d1h, f1h, i_tr1, i_va1, med_atr_1h),
            ("15m EMA9 recross", "15m", d15, f15, i_tr15, i_va15, med_atr_15),
        ):
            if tf == "1h":
                setup_l, setup_s = setup_l_1h, setup_s_1h
                bias_al = bias_on_1h
                trig_l, trig_s = trig1_l, trig1_s
            else:
                # project the 1h-native setup down onto 15m (available only
                # from the 1h bar's close), same discipline as bias4h -> 1h.
                setup_l = align_signal(d1h, setup_l_1h.astype(float), d15, 1.0) >= 0.5
                setup_s = align_signal(d1h, setup_s_1h.astype(float), d15, 1.0) >= 0.5
                bias_al = bias_on_15
                trig_l, trig_s = trig15_l_raw, trig15_s_raw

            for level in ("setup-only", "bias+setup", "full"):
                el, es = stack_entries(setup_l, setup_s, bias_al, trig_l, trig_s, level)
                stop_pct = min(1.2 * med_atr, STOP_CAP_MTF)
                mh_bars = hours_to_bars(d, 72)
                sig = day_trade_signal(d, el, es, mh_bars)
                for tmult in (2.0, 3.0):
                    target_pct = tmult * stop_pct
                    tr, va = score(d, sig, f, i_tr, i_va,
                                   stop_pct=stop_pct, target_pct=target_pct)
                    cfg = f"{setup_name} / {trigger_name} / {level} / tgt{tmult:.0f}x"
                    row = mk_row("3-mtf-alignment", cfg, tf, tr, va,
                                  setup=setup_name, trigger=trigger_name, level=level,
                                  stop_pct=stop_pct, target_pct=target_pct, max_hold_h=72)
                    if tf == "15m":
                        pooled_n = len(tr.trades) + len(va.trades)
                        pooled_costs = (tr.total_fees + tr.total_friction
                                        + va.total_fees + va.total_friction)
                        pooled_notional = sum(t.units * t.entry_price
                                               for t in list(tr.trades) + list(va.trades))
                        cost_bps = (pooled_costs / pooled_notional * 10_000
                                    if pooled_notional else float("nan"))
                        row["cost_bps_per_trade"] = cost_bps
                        row["clears_9bps_floor"] = (
                            cost_bps < COST_FLOOR_15M_BPS if pooled_n else None)
                    rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("Loading cached data (no network calls needed)...")
    frames = {tf: fetch_bybit_deep(tf, "BTCUSDT") for tf in ("15m", "1h", "4h")}
    funding_hist = fetch_funding_history("BTCUSDT")
    funding = {tf: align_funding(frames[tf], funding_hist) for tf in ("15m", "1h", "4h")}

    meta = {}
    for tf in ("15m", "1h", "4h"):
        d = frames[tf]
        n, i_tr, i_va = split_points(d)
        atr_pct = atr(d, 14) / d["close"] * 100
        med_atr_train = float(atr_pct.iloc[:i_tr].median())
        meta[tf] = {"n": n, "i_tr": i_tr, "i_va": i_va, "med_atr": med_atr_train}
        print(f"  {tf}: {n} bars, {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
              f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed) | "
              f"median train ATR% = {med_atr_train:.3f}%")

    frame4h = frames["4h"]
    champ4h = vol_gated_ma(frame4h, **CHAMP_KW)                       # long-only 0/1 (families 1)
    bias4h = four_h_bias(frame4h, champ4h)                            # +1/0/-1 (family 3)
    print(f"  4h champion (long-only) time-in-market: {(champ4h == 1).mean() * 100:.1f}%")
    print(f"  4h bias (+SMA50 agreement) long%={100*(bias4h==1).mean():.1f} "
          f"short%={100*(bias4h==-1).mean():.1f}")

    print("\nRunning FAMILY 1 (divergences at confirmed swings)...")
    rows = family1_divergences(frames, funding, meta, champ4h, frame4h)
    print(f"  {len(rows)} configs done")

    print("Running FAMILY 2 (oscillator regime overlays on donchian-20)...")
    rows += family2_oscillator_overlays(frames, funding, meta)
    print(f"  {len(rows)} configs cumulative")

    print("Running FAMILY 3 (multi-timeframe alignment)...")
    rows += family3_mtf_alignment(frames, funding, meta, frame4h, bias4h)
    print(f"  {len(rows)} configs cumulative")

    df = pd.DataFrame(rows)
    print(f"\n{len(df)} configs tested. Verdict counts:")
    print(df["verdict"].value_counts().to_string())

    survivors = df[df["verdict"] == "SURVIVOR"]
    near = df[df["verdict"] == "INSUFFICIENT-SAMPLE"]
    print(f"\nSURVIVORS (positive train+val, >={MIN_TRAIN_TRADES} train / "
          f">={MIN_VAL_TRADES} val trades): {len(survivors)}")
    if len(survivors):
        print(survivors[["family", "config", "tf", "tr_n", "tr_exp", "va_n", "va_exp",
                          "med_hold_h"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    print(f"\nINSUFFICIENT-SAMPLE: {len(near)}")
    if len(near):
        print(near[["family", "config", "tf", "tr_n", "tr_exp", "va_n", "va_exp",
                     "med_hold_h"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    df.to_csv("step58_results_raw.csv", index=False)
    print("\nRaw results written to step58_results_raw.csv")
    return df


if __name__ == "__main__":
    main()
