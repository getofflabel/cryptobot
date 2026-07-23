"""
step41_shorts.py — round 41: cracking BTC shorts, four native families.

Run:  python3 step41_shorts.py

CONTEXT
Short attempt count going into this round: ~42 (see RESEARCH_LOG.md /
project memory). Every mirror-image MA-cross short, event short, and
fixed-vol-gated short has failed, mostly because BTC's volatility has
structurally DECAYED era over era (round 30's finding) — a fixed ATR gate
calibrated on early, violent eras goes dead in the 2025-26 grind. The one
short that ever won BOTH train and val (the "forensic composite": short
when funding is euphoric AND price just popped AND ATR is live) was
strangled by sample size — only 6 validation trades against an 8-trade bar.

This round builds FOUR native short families per Wallace's mandate, using
ADAPTIVE vol gates (current ATR% vs its own trailing 365-day median)
wherever a vol gate is used, never a fixed threshold:

  1. BLEED RIDER      — stacked lower highs + failing bounces (structural
                         downtrend detection via confirmed swing points),
                         plus a simpler EMA/drawdown variant.
  2. PERSISTENCE SHORT — enter on a persistent run of red bars with a
                         real cumulative move and no meaningful bounce;
                         ride with an ATR-based stop / time stop.
  3. BREAKDOWN SHORT   — classic Donchian breakdown, raw AND vol-gated
                         both directions (only above / only below the
                         trailing adaptive median — the grind regime may
                         want the OPPOSITE gate direction from a violent one).
  4. FORENSIC WIDENED  — the one short with real prior evidence, widened
                         (looser funding threshold, 1h+2h, retest entries)
                         specifically to clear the 8-trade validation floor.

ENGINE NOTES (read backtest.py / strategy.py for the ground truth):
- stop_pct/target_pct are FIXED percentages for the whole backtest, not
  per-trade dynamic levels. True "trailing stop to the last swing high" is
  not directly expressible, so we approximate it the way this repo already
  does (round 17's "stop = 1.85 x median ATR%, computed on TRAIN only"):
  every family that wants a vol-scaled stop uses A x median(ATR%) measured
  on that timeframe's TRAIN slice, held fixed across train/val. This is a
  known simplification, stated plainly in the results file.
- No lookahead: rolling extremes used for breakout/structure comparisons
  are shift(1)'d (the bar that breaks a level must not be inside the
  window that defines the level) — same convention as strategy.py's
  donchian_breakout. Smoothing indicators (EMA, ATR, RSI) are NOT shifted,
  matching the rest of the codebase — the engine's own bar-close-N ->
  fill-at-open-N+1 mechanic is what enforces no-lookahead there.
- GAUNTLET: chronological 60/20/20 per timeframe. This script NEVER slices
  into the final 20% (test). Only train (0:i_tr) and val (i_tr:i_va) are
  ever computed or printed.

DISCIPLINE: costs always on (CostModel defaults: 6bps taker / 2bps maker,
1bp half-spread, 2bp slippage — matches config.py / other step*.py
scripts). Real funding wired via align_funding wherever funding is
relevant (family 4 always; families 1-3 also score with real funding).
Selection is by TRAIN expectancy only, never tuned on val.
"""

import numpy as np
import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from strategy import atr, event_short

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------

def bar_hours(d):
    t = pd.DatetimeIndex(d["timestamp"])
    return float((t[1:] - t[:-1]).total_seconds().min() / 3600)


def days_to_bars(d, days):
    return max(1, round(days * 24 / bar_hours(d)))


def hours_to_bars(d, hours):
    return max(1, round(hours / bar_hours(d)))


def split_points(d):
    n = len(d)
    return n, int(n * 0.6), int(n * 0.8)


def adaptive_vol_gate(d, direction="above", window_days=365, atr_n=14):
    """Boolean series: is current ATR% above/below its OWN trailing
    365-day median? Trailing = expanding-window-style rolling median that
    only ever looks backward, then shift(1) so the current bar's own ATR
    is compared against a median that EXCLUDES it (avoids the trivial
    self-inclusion lookahead a rolling().median() would otherwise carry
    at small window edges)."""
    a_pct = atr(d, atr_n) / d["close"] * 100
    window = max(30, round(24 / bar_hours(d) * window_days))
    min_periods = max(30, window // 10)
    trailing_med = a_pct.rolling(window, min_periods=min_periods).median().shift(1)
    gate = (a_pct > trailing_med) if direction == "above" else (a_pct < trailing_med)
    return gate.fillna(False), a_pct


def score(d, sig, f, i_tr, i_va, stop_pct=None, target_pct=None,
          execution="maker"):
    def run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True),
            sig.iloc[lo:hi].reset_index(drop=True),
            execution=execution,
            funding_series=f.iloc[lo:hi].reset_index(drop=True),
            stop_pct=stop_pct, target_pct=target_pct,
        )
    return run(0, i_tr), run(i_tr, i_va)


def verdict_for(tr, va):
    tr_n, va_n = len(tr.trades), len(va.trades)
    if tr.expectancy > 0 and va.expectancy > 0:
        if tr_n >= MIN_TRAIN_TRADES and va_n >= MIN_VAL_TRADES:
            return "SURVIVOR"
        return "INSUFFICIENT-SAMPLE"
    return "FAIL"


def mk_row(family, config, tf, tr, va):
    return {
        "family": family, "config": config, "tf": tf,
        "tr_n": len(tr.trades), "tr_exp": tr.expectancy,
        "tr_win%": tr.win_rate * 100, "tr_dd%": tr.max_drawdown_pct,
        "tr_ret%": tr.total_return_pct,
        "va_n": len(va.trades), "va_exp": va.expectancy,
        "va_win%": va.win_rate * 100, "va_dd%": va.max_drawdown_pct,
        "va_ret%": va.total_return_pct,
        "verdict": verdict_for(tr, va),
    }


# ---------------------------------------------------------------------------
# FAMILY 1 — bleed rider
# ---------------------------------------------------------------------------

def confirmed_swings(d, k):
    """Confirmed k-bar fractal swing high/low PRICES, aligned so that the
    value known at bar t reflects a peak/trough at bar t-k, confirmed
    using only data through bar t (no lookahead: a centered k-bar window
    around bar j needs data through j+k, so we can only KNOW bar j was a
    swing point once we reach bar j+k)."""
    h, l = d["high"], d["low"]
    is_sh = (h == h.rolling(2 * k + 1, center=True).max())
    is_sl = (l == l.rolling(2 * k + 1, center=True).min())
    sh_conf = is_sh.shift(k).astype("boolean").fillna(False).astype(bool)
    sl_conf = is_sl.shift(k).astype("boolean").fillna(False).astype(bool)
    sh_price = h.shift(k).where(sh_conf)
    sl_price = l.shift(k).where(sl_conf)
    return sh_price, sl_price


def last_n_confirmed(series, n):
    """At each bar, the last n CONFIRMED (non-NaN) values seen so far,
    most-recent-first, forward-filled. NaN until n have occurred."""
    vals = series.to_numpy()
    hist = []
    cols = [np.full(len(vals), np.nan) for _ in range(n)]
    for i, v in enumerate(vals):
        if not np.isnan(v):
            hist.append(v)
        for j in range(n):
            if len(hist) > j:
                cols[j][i] = hist[-(j + 1)]
    return [pd.Series(c, index=series.index) for c in cols]


def bleed_rider_structural(d, k, hold_days=10):
    sh_price, sl_price = confirmed_swings(d, k)
    sh1, sh2, sh3 = last_n_confirmed(sh_price, 3)
    sl1, _, _ = last_n_confirmed(sl_price, 3)
    lower_highs = (sh1 < sh2) & (sh2 < sh3)
    enter = lower_highs & (d["close"] < sl1)
    exit_ = d["close"] > sh1     # structure broken: reclaimed the last lower high
    return event_short(d, enter.fillna(False), exit_.fillna(False),
                        max_hold=days_to_bars(d, hold_days))


def bleed_rider_simple(d, dd_thresh_pct):
    ema20 = d["close"].ewm(span=20, adjust=False).mean()
    ema50 = d["close"].ewm(span=50, adjust=False).mean()
    roll_high30 = d["high"].rolling(30).max().shift(1)
    dd = (d["close"] - roll_high30) / roll_high30 * 100
    enter = (d["close"] < ema20) & (ema20 < ema50) & (dd <= -dd_thresh_pct)
    exit_ = d["close"] > ema20
    return event_short(d, enter.fillna(False), exit_.fillna(False), max_hold=0)


def family1_bleed_rider(frames, funding, meta):
    rows = []
    for tf in ("1h", "4h"):
        d, f = frames[tf], funding[tf]
        n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]
        stop_pct = 2.0 * meta[tf]["med_atr"]     # 2x median ATR%, train-derived
        for k in (5, 8, 12):
            sig = bleed_rider_structural(d, k)
            tr, va = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct)
            rows.append(mk_row("1-bleed-structural", f"k={k}", tf, tr, va))
        for dd_thresh in (2.0, 3.0, 5.0):
            sig = bleed_rider_simple(d, dd_thresh)
            tr, va = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct)
            rows.append(mk_row("1-bleed-simple", f"dd>{dd_thresh:.0f}%", tf, tr, va))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 2 — persistence short
# ---------------------------------------------------------------------------

def persistence_signal(d, N, M, X, Y, max_hold):
    ret1 = d["close"].pct_change() * 100
    red_count = (ret1 < 0).rolling(M).sum()
    total_move = (d["close"] / d["close"].shift(M) - 1) * 100
    max_bounce = ret1.rolling(M).max()
    enter = (red_count >= N) & (total_move <= -X) & (max_bounce <= Y)
    exit_ = pd.Series(False, index=d.index)   # exits via stop_pct + max_hold only
    return event_short(d, enter.fillna(False), exit_, max_hold)


def family2_persistence(frames, funding, meta):
    rows = []
    Y = 1.0        # bounce cap, fixed (not swept, keeps grid modest)
    Z = 2.5        # ATR stop multiplier
    for tf in ("1h", "4h"):
        d, f = frames[tf], funding[tf]
        n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]
        stop_pct = Z * meta[tf]["med_atr"]
        B = hours_to_bars(d, 48)     # 2-day time stop
        for N, M in ((4, 5), (6, 8), (8, 10)):
            for X in (1.5, 2.5, 4.0):
                sig = persistence_signal(d, N, M, X, Y, B)
                tr, va = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct)
                rows.append(mk_row("2-persistence",
                                    f"N{N}/M{M} X{X:.1f}%", tf, tr, va))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 3 — breakdown (Donchian) short
# ---------------------------------------------------------------------------

def breakdown_signal(d, N, gate_bool, max_hold, ema_n=20):
    lo_n = d["low"].rolling(N).min().shift(1)
    enter = d["close"] < lo_n
    if gate_bool is not None:
        enter = enter & gate_bool
    ema = d["close"].ewm(span=ema_n, adjust=False).mean()
    exit_ = d["close"] > ema
    return event_short(d, enter.fillna(False), exit_.fillna(False), max_hold)


def family3_breakdown(frames, funding, meta):
    rows = []
    A = 2.0    # stop multiplier on median ATR%, fixed
    for tf in ("1h", "4h", "1d"):
        d, f = frames[tf], funding[tf]
        n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]
        stop_pct = A * meta[tf]["med_atr"]
        B = days_to_bars(d, 10)
        gate_above, _ = adaptive_vol_gate(d, direction="above")
        gate_below, _ = adaptive_vol_gate(d, direction="below")
        for N in (20, 55):
            variants = [("raw", None), ("gate-above-median", gate_above),
                        ("gate-below-median", gate_below)]
            for tag, gate in variants:
                sig = breakdown_signal(d, N, gate, B)
                tr, va = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct)
                rows.append(mk_row("3-breakdown", f"N{N} {tag}", tf, tr, va))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 4 — forensic short, widened
# ---------------------------------------------------------------------------

def forensic_signal(d, f, fund_thresh, atr_thresh, pop_thresh, pop_hours,
                     max_hold_hours, retest):
    pop_bars = hours_to_bars(d, pop_hours)
    pop = (d["close"] / d["close"].shift(pop_bars) - 1) * 100
    atr_pct = atr(d, 14) / d["close"] * 100
    base = (f > fund_thresh) & (pop > pop_thresh) & (atr_pct > atr_thresh)

    if retest:
        # widened per task: allow entry on a RETEST of a recently broken
        # level (breakdown-then-bounce-back-to-resistance), still gated by
        # funding euphoria + live ATR — not just the pop condition.
        lo20 = d["low"].rolling(20).min().shift(1)
        broke_recently = (d["close"] < lo20).rolling(hours_to_bars(d, 8)).max().astype(bool)
        retest_cond = (broke_recently & (d["close"] > lo20 * 0.995)
                        & (d["close"] < lo20 * 1.01))
        enter = base | (retest_cond & (f > fund_thresh) & (atr_pct > atr_thresh))
    else:
        enter = base

    exit_ = pd.Series(False, index=d.index)   # exits via stop/target/max_hold
    max_hold = hours_to_bars(d, max_hold_hours)
    return event_short(d, enter.fillna(False), exit_, max_hold)


def family4_forensic_widened(frames, funding, meta):
    rows = []
    stop_pct, target_pct = 1.69, 5.07     # established forensic geometry
    for tf in ("1h", "2h"):
        d, f = frames[tf], funding[tf]
        n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]
        for fund_thresh in (2.0, 1.5, 1.0, 0.5):
            for retest in (False, True):
                sig = forensic_signal(d, f, fund_thresh, atr_thresh=1.2,
                                       pop_thresh=1.5, pop_hours=4,
                                       max_hold_hours=48, retest=retest)
                tr, va = score(d, sig, f, i_tr, i_va,
                               stop_pct=stop_pct, target_pct=target_pct)
                tag = f"f>{fund_thresh:.1f}bp" + (" +retest" if retest else "")
                rows.append(mk_row("4-forensic-widened", tag, tf, tr, va))
    return rows


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("Loading cached data (no network calls needed)...")
    frames = {tf: fetch_bybit_deep(tf, "BTCUSDT") for tf in ("1h", "2h", "4h", "1d")}
    funding_hist = fetch_funding_history("BTCUSDT")
    funding = {tf: align_funding(d, funding_hist) for tf, d in frames.items()}

    meta = {}
    for tf, d in frames.items():
        n, i_tr, i_va = split_points(d)
        atr_pct = atr(d, 14) / d["close"] * 100
        med_atr_train = float(atr_pct.iloc[:i_tr].median())
        meta[tf] = {"n": n, "i_tr": i_tr, "i_va": i_va, "med_atr": med_atr_train}
        print(f"  {tf}: {n} bars, {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
              f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed) | "
              f"median train ATR% = {med_atr_train:.2f}%")

    print("\nRunning FAMILY 1 (bleed rider)...")
    rows = family1_bleed_rider(frames, funding, meta)
    print("Running FAMILY 2 (persistence short)...")
    rows += family2_persistence(frames, funding, meta)
    print("Running FAMILY 3 (breakdown / Donchian, adaptive gates)...")
    rows += family3_breakdown(frames, funding, meta)
    print("Running FAMILY 4 (forensic short, widened)...")
    rows += family4_forensic_widened(frames, funding, meta)

    df = pd.DataFrame(rows)
    print(f"\n{len(df)} configs tested. Verdict counts:")
    print(df["verdict"].value_counts().to_string())

    print("\nFull results (train + val, full costs, test sealed):")
    with pd.option_context("display.max_rows", None, "display.width", 200):
        print(df.sort_values(["family", "tf", "tr_exp"], ascending=[True, True, False])
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    survivors = df[df["verdict"] == "SURVIVOR"]
    near = df[df["verdict"] == "INSUFFICIENT-SAMPLE"]
    print(f"\nSURVIVORS (positive train+val, >=30 train / >=8 val trades): "
          f"{len(survivors)}")
    if len(survivors):
        print(survivors[["family", "config", "tf", "tr_n", "tr_exp", "va_n", "va_exp"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    print(f"\nINSUFFICIENT-SAMPLE (positive both windows, but under the trade-count bar): "
          f"{len(near)}")
    if len(near):
        print(near[["family", "config", "tf", "tr_n", "tr_exp", "va_n", "va_exp"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    df.to_csv("step41_results_raw.csv", index=False)
    print("\nRaw results written to step41_results_raw.csv")
    print("(step41_results.md written separately after this run)")

    return df


if __name__ == "__main__":
    main()
