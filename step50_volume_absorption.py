"""
step50_volume_absorption.py — round 50: formalizing the OWNER'S OWN chart
read as a BTC day-trade family: VOLUME ABSORPTION / EFFORT-vs-RESULT
DIVERGENCE.

His read, verbatim in spirit: "if the volume candle is exponentially long
compared to the others but the price candle doesn't match it — that's a
very strong sign it's going the other way." Classic absorption / stopping
volume. This is the FIRST volume-shape family ever tested in this repo
(every prior fast family was price/OI-only and died to the 2025-26 grind's
cost floor — round 43/45). Research only: this script + step50_results.md
only. No commits, no live orders, no other step*.py file touched.

THREE SUB-FAMILIES (all shift(1)-disciplined: the signal bar must be fully
CLOSED before an entry fires; fills happen at the NEXT bar's open, which is
backtest.py's own no-lookahead mechanic — see its docstring)

  A. ABSORPTION FADE — his core read, literally. Volume shock (current bar
     volume >= K x trailing-median-48-bar volume, K in {4,6,10}) but the
     bar's own |close-open| return is SMALL relative to its own trailing
     typical move (|ret| <= m x trailing-median-48-bar |ret|, m in
     {1.0,1.5}). Trade OPPOSITE the signal bar's color: huge red volume +
     tiny drop -> LONG (selling got absorbed); huge green volume + tiny
     rise -> SHORT (buying got absorbed).

  B. STOPPING VOLUME AT EXTREMES — the refined classical tape-reading
     version. Same volume shock, PLUS the bar prints at a local price
     extreme (its low is the lowest low of the trailing 24 bars for longs,
     mirrored for shorts) PLUS the bar closes in the upper {40,50}% of its
     own range for longs (lower for shorts) — the wick is the rejection.

  C. VOLUME-SHOCK CONTINUATION — the REQUIRED control/falsification arm.
     Same volume shock, but price DID move with it (|ret| >= 2x trailing
     median |ret|): trade WITH the move. If the owner's divergence read is
     real, A/B should beat C on an apples-to-apples grid. If C wins
     instead, volume shocks are just momentum markers, not absorption —
     either way we say the truth plainly.

GEOMETRY (identical grid across all three sub-families, so A/B/C are
comparable): stop = {1.0, 1.5} x ATR(14), computed as a TRAIN-only median
ATR% held fixed for the whole run (this repo's established approximation,
see step41/step43 headers), hard-capped at 1.7%. target = {2, 3} x stop.
max_hold in {8h, 24h}.

ENGINE / PLUMBING — imported, not reimplemented, per the round-50 brief:
  split_points, day_trade_signal, score, verdict_for, mk_row,
  hours_to_bars, HARD_STOP_CAP  <- all from step43_daytrade.py
  (step43's gauntlet discipline: chronological 60/20/20, this script NEVER
  touches the sealed final 20% test slice; only train [0:i_tr] and val
  [i_tr:i_va] are ever computed. Costs always on, execution="maker", real
  funding via align_funding — same convention as step41/step43.)

VOLUME-SHOCK BASELINE, NO SELF-CONTAMINATION: the trailing-median volume
and trailing-median |ret| baselines are computed over the PRIOR 48 bars
ONLY (rolling(48).shift(1)) — a shock bar's own extreme volume/return must
never leak into the baseline it is being compared against, or every shock
would trivially look "exponentially long" relative to a baseline it just
inflated.

DISCIPLINE: selection is by TRAIN expectancy only; val is checked once and
never tuned against. Sealed test (final 20%) is never touched here — the
lead agent spends looks.
"""

import numpy as np
import pandas as pd

import config
from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step43_daytrade import (
    HARD_STOP_CAP,
    MIN_TRAIN_TRADES,
    MIN_VAL_TRADES,
    day_trade_signal,
    hours_to_bars,
    mk_row,
    score,
    split_points,
    verdict_for,
)
from strategy import atr

BASELINE_WINDOW = 48       # bars — trailing volume / |ret| baseline window
EXTREME_WINDOW = 24        # bars — family B's local-extreme lookback
K_GRID = (4, 6, 10)        # volume shock multiplier
M_GRID = (1.0, 1.5)        # family A "smallness" multiplier
WICK_GRID = (0.40, 0.50)   # family B "upper/lower X% of range" thresholds
CONT_MULT = 2.0            # family C "moved WITH it" multiplier
STOP_ATR_GRID = (1.0, 1.5)
TARGET_MULT_GRID = (2.0, 3.0)   # target = this x stop
MAX_HOLD_GRID = (8, 24)         # hours
EVENT_HORIZONS = (4, 24)        # bars — event-study forward horizons


# ---------------------------------------------------------------------------
# shared volume/return primitives
# ---------------------------------------------------------------------------

def bar_return_pct(d):
    """Signed close-to-open return of the bar itself, in %. This IS the
    'price candle' in the owner's read — no shift needed, it's the signal
    bar's own already-closed value."""
    return (d["close"] - d["open"]) / d["open"] * 100


def volume_baseline(d, window=BASELINE_WINDOW):
    """Trailing median volume over the PRIOR `window` bars (shift(1)) —
    excludes the current bar so a shock never inflates its own yardstick."""
    return d["volume"].rolling(window, min_periods=window // 2).median().shift(1)


def absret_baseline(d, window=BASELINE_WINDOW):
    """Trailing median |bar return| over the PRIOR `window` bars, same
    shift(1) no-self-contamination discipline."""
    ret = bar_return_pct(d)
    return ret.abs().rolling(window, min_periods=window // 2).median().shift(1)


def volume_shock(d, K, window=BASELINE_WINDOW, vol_base=None):
    """Boolean: is this bar's OWN (already-closed) volume >= K x the
    trailing baseline computed from bars strictly before it?"""
    vb = volume_baseline(d, window) if vol_base is None else vol_base
    return (d["volume"] >= K * vb) & vb.notna()


def local_extreme_low(d, window=EXTREME_WINDOW):
    """This bar's low is the lowest low of the trailing `window` bars
    (itself included) — uses only data through this bar's own close, no
    future information."""
    return d["low"] == d["low"].rolling(window).min()


def local_extreme_high(d, window=EXTREME_WINDOW):
    return d["high"] == d["high"].rolling(window).max()


def close_position_in_range(d):
    """0.0 = closed at the bar's low, 1.0 = closed at the bar's high.
    Zero-range bars (high==low) are treated as neutral (0.5)."""
    rng = (d["high"] - d["low"]).replace(0, np.nan)
    return ((d["close"] - d["low"]) / rng).fillna(0.5)


# ---------------------------------------------------------------------------
# FAMILY A — absorption fade (the owner's core read)
# ---------------------------------------------------------------------------

def familyA_entries(d, K, m, vol_base, absret_base):
    ret = bar_return_pct(d)
    vshock = (d["volume"] >= K * vol_base) & vol_base.notna()
    small = (ret.abs() <= m * absret_base) & absret_base.notna()
    cond = vshock & small
    red = ret < 0
    green = ret > 0
    enter_long = (cond & red).fillna(False)     # huge red vol, tiny drop -> LONG
    enter_short = (cond & green).fillna(False)  # huge green vol, tiny rise -> SHORT
    return enter_long, enter_short


# ---------------------------------------------------------------------------
# FAMILY B — stopping volume at extremes
# ---------------------------------------------------------------------------

def familyB_entries(d, K, wick_frac, vol_base, ext_low, ext_high, close_pos):
    vshock = (d["volume"] >= K * vol_base) & vol_base.notna()
    long_cond = vshock & ext_low & (close_pos >= (1 - wick_frac))
    short_cond = vshock & ext_high & (close_pos <= wick_frac)
    return long_cond.fillna(False), short_cond.fillna(False)


# ---------------------------------------------------------------------------
# FAMILY C — volume-shock continuation (control / falsification arm)
# ---------------------------------------------------------------------------

def familyC_entries(d, K, vol_base, absret_base, mult=CONT_MULT):
    ret = bar_return_pct(d)
    vshock = (d["volume"] >= K * vol_base) & vol_base.notna()
    moved = (ret.abs() >= mult * absret_base) & absret_base.notna()
    cond = vshock & moved
    green = ret > 0
    red = ret < 0
    enter_long = (cond & green).fillna(False)   # big green vol + big rise -> WITH it, LONG
    enter_short = (cond & red).fillna(False)     # big red vol + big drop -> WITH it, SHORT
    return enter_long, enter_short


# ---------------------------------------------------------------------------
# grid runner (shared geometry sweep for A/B/C)
# ---------------------------------------------------------------------------

def run_geometry_grid(family_tag, cfg_prefix, d, f, i_tr, i_va, med_atr,
                       enter_long, enter_short):
    """One entry-condition pair -> sweep the shared stop/target/hold grid.
    Event counts (train+val, pre-max-hold-statemachine raw qualifying
    bars) are computed ONCE here and stamped on every geometry row that
    shares this entry condition."""
    n_long_ev = int(enter_long.iloc[:i_va].sum())
    n_short_ev = int(enter_short.iloc[:i_va].sum())
    rows = []
    for stop_mult in STOP_ATR_GRID:
        stop_pct = min(stop_mult * med_atr, HARD_STOP_CAP)
        for tmult in TARGET_MULT_GRID:
            target_pct = tmult * stop_pct
            for max_hold_h in MAX_HOLD_GRID:
                mh_bars = hours_to_bars(d, max_hold_h)
                sig = day_trade_signal(d, enter_long, enter_short, mh_bars)
                tr, va = score(d, sig, f, i_tr, i_va,
                                stop_pct=stop_pct, target_pct=target_pct)
                cfg = (f"{cfg_prefix} stop{stop_mult:.1f}xATR "
                       f"tgt{tmult:.0f}xstop hold{max_hold_h}h")
                row = mk_row(family_tag, cfg, "?", tr, va,
                             stop_pct, target_pct, max_hold_h)
                row["n_long_events"] = n_long_ev
                row["n_short_events"] = n_short_ev
                row["realized_cost_bps"] = realized_cost_bps(tr, va)
                row["gross_edge_bps"] = gross_edge_bps(tr, va)
                rows.append(row)
    return rows


def realized_cost_bps(tr, va, initial_equity=None):
    """Empirical round-trip cost (fees + friction + funding), averaged per
    trade over train+val, expressed in bps of the account's starting
    notional. This is a fixed-notional APPROXIMATION (size_frac=1.0 means
    real notional compounds with equity) — stated plainly, matches the
    convention this repo already used to compute the ~9.2bps 15m cost
    floor in round 43."""
    if initial_equity is None:
        initial_equity = config.INITIAL_EQUITY
    n = len(tr.trades) + len(va.trades)
    if n == 0:
        return float("nan")
    total_cost = (tr.total_fees + tr.total_friction + tr.total_funding
                  + va.total_fees + va.total_friction + va.total_funding)
    return (total_cost / n) / initial_equity * 10_000


def gross_edge_bps(tr, va, initial_equity=None):
    """Pre-cost ('gross') edge per trade, in bps: net expectancy (already
    what the trades actually paid) plus the realized cost back out, scaled
    the same way as realized_cost_bps so the two are directly comparable —
    the cost-floor check this repo has used since round 43."""
    if initial_equity is None:
        initial_equity = config.INITIAL_EQUITY
    trades = list(tr.trades) + list(va.trades)
    if not trades:
        return float("nan")
    exp_dollars = float(np.mean([t.pnl for t in trades]))
    cost_dollars = realized_cost_bps(tr, va, initial_equity) / 10_000 * initial_equity
    return (exp_dollars + cost_dollars) / initial_equity * 10_000


# ---------------------------------------------------------------------------
# event study (family A only, per the round-50 brief): does the "eye" see
# something real, independent of any stop/target geometry?
# ---------------------------------------------------------------------------

def forward_return_pct(d, h):
    """(close[t+h]/close[t] - 1) x 100, purely descriptive (no trading
    decision attached), NaN at the tail where t+h runs off the frame."""
    return (d["close"].shift(-h) / d["close"] - 1) * 100


def event_study_familyA(frames, meta, tf):
    """For each K (m fixed at 1.0, the tightest/most literal reading of
    'the price candle doesn't match it'), forward {4,24}-bar return after
    an A-type long event vs after an A-type short event vs the UNCONDITIONAL
    baseline (same horizon, same train+val slice) — long and short kept
    separate per the brief."""
    d = frames[tf]
    i_va = meta[tf]["i_va"]
    vol_base = volume_baseline(d)
    absret_base = absret_baseline(d)
    rows = []
    for K in K_GRID:
        el, es = familyA_entries(d, K, 1.0, vol_base, absret_base)
        el_tv = el.iloc[:i_va]
        es_tv = es.iloc[:i_va]
        for h in EVENT_HORIZONS:
            fwd = forward_return_pct(d, h).iloc[:i_va]
            baseline_mean = float(fwd.dropna().mean())
            long_vals = fwd[el_tv.to_numpy()].dropna()
            short_vals = fwd[es_tv.to_numpy()].dropna()
            rows.append({
                "tf": tf, "K": K, "horizon_bars": h,
                "side": "LONG (absorbed-red)", "n_events": int(len(long_vals)),
                "mean_fwd_ret%": float(long_vals.mean()) if len(long_vals) else float("nan"),
                "median_fwd_ret%": float(long_vals.median()) if len(long_vals) else float("nan"),
                "pct_positive": float((long_vals > 0).mean() * 100) if len(long_vals) else float("nan"),
                "baseline_mean%": baseline_mean,
            })
            rows.append({
                "tf": tf, "K": K, "horizon_bars": h,
                "side": "SHORT (absorbed-green)", "n_events": int(len(short_vals)),
                # short thesis pays when forward return is NEGATIVE, so also
                # report the sign-flipped ("as PnL would see it") figure.
                "mean_fwd_ret%": float(short_vals.mean()) if len(short_vals) else float("nan"),
                "median_fwd_ret%": float(short_vals.median()) if len(short_vals) else float("nan"),
                "pct_positive": float((short_vals > 0).mean() * 100) if len(short_vals) else float("nan"),
                "baseline_mean%": baseline_mean,
            })
    return rows


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("Loading cached data (no network calls needed)...")
    frames = {tf: fetch_bybit_deep(tf, "BTCUSDT") for tf in ("15m", "1h")}
    funding_hist = fetch_funding_history("BTCUSDT")
    funding = {tf: align_funding(frames[tf], funding_hist) for tf in ("15m", "1h")}

    # ---- volume sanity ----
    print("\nVOLUME SANITY:")
    vol_report = []
    for tf in ("15m", "1h"):
        d = frames[tf]
        v = d["volume"]
        zeros = int((v == 0).sum())
        nans = int(v.isna().sum())
        line = (f"  {tf}: n={len(d)}  mean={v.mean():,.2f}  median={v.median():,.2f}  "
                f"min={v.min():,.4f}  max={v.max():,.2f}  zeros={zeros}  nans={nans}")
        print(line)
        vol_report.append((tf, len(d), float(v.mean()), float(v.median()),
                            float(v.min()), float(v.max()), zeros, nans))

    meta = {}
    for tf in ("15m", "1h"):
        d = frames[tf]
        n, i_tr, i_va = split_points(d)
        atr_pct = atr(d, 14) / d["close"] * 100
        med_atr_train = float(atr_pct.iloc[:i_tr].median())
        meta[tf] = {"n": n, "i_tr": i_tr, "i_va": i_va, "med_atr": med_atr_train}
        print(f"  {tf}: {n} bars, {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
              f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed) | "
              f"median train ATR% = {med_atr_train:.3f}%")

    # ---- event study (family A, both timeframes) ----
    print("\nRunning EVENT STUDY (family A, K in {4,6,10}, m=1.0, both tf)...")
    event_rows = []
    for tf in ("15m", "1h"):
        event_rows += event_study_familyA(frames, meta, tf)
    event_df = pd.DataFrame(event_rows)
    print(event_df.to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    # ---- full geometry grid, A / B / C, both timeframes ----
    all_rows = []
    for tf in ("15m", "1h"):
        d, f = frames[tf], funding[tf]
        i_tr, i_va, med_atr = meta[tf]["i_tr"], meta[tf]["i_va"], meta[tf]["med_atr"]
        vol_base = volume_baseline(d)
        absret_base = absret_baseline(d)
        ext_low = local_extreme_low(d)
        ext_high = local_extreme_high(d)
        close_pos = close_position_in_range(d)

        print(f"\nRunning FAMILY A (absorption fade) on {tf}...")
        for K in K_GRID:
            for m in M_GRID:
                el, es = familyA_entries(d, K, m, vol_base, absret_base)
                cfg_prefix = f"K>={K} m<={m:.1f}"
                rows = run_geometry_grid("A-absorption-fade", cfg_prefix, d, f,
                                          i_tr, i_va, med_atr, el, es)
                for r in rows:
                    r["tf"] = tf
                all_rows += rows

        print(f"Running FAMILY B (stopping volume at extremes) on {tf}...")
        for K in K_GRID:
            for wick_frac in WICK_GRID:
                el, es = familyB_entries(d, K, wick_frac, vol_base,
                                          ext_low, ext_high, close_pos)
                cfg_prefix = f"K>={K} wick-upper{wick_frac*100:.0f}%"
                rows = run_geometry_grid("B-stopping-volume", cfg_prefix, d, f,
                                          i_tr, i_va, med_atr, el, es)
                for r in rows:
                    r["tf"] = tf
                all_rows += rows

        print(f"Running FAMILY C (volume-shock continuation, control) on {tf}...")
        for K in K_GRID:
            el, es = familyC_entries(d, K, vol_base, absret_base)
            cfg_prefix = f"K>={K} continuation"
            rows = run_geometry_grid("C-shock-continuation", cfg_prefix, d, f,
                                      i_tr, i_va, med_atr, el, es)
            for r in rows:
                r["tf"] = tf
            all_rows += rows

    df = pd.DataFrame(all_rows)
    print(f"\n{len(df)} configs tested. Verdict counts:")
    print(df["verdict"].value_counts().to_string())

    survivors = df[df["verdict"] == "SURVIVOR"]
    near = df[df["verdict"] == "INSUFFICIENT-SAMPLE"]
    print(f"\nSURVIVORS (positive train+val, >=30 train / >=8 val trades): {len(survivors)}")
    if len(survivors):
        print(survivors[["family", "config", "tf", "tr_n", "tr_exp", "va_n", "va_exp",
                          "gross_edge_bps", "realized_cost_bps"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    print(f"\nINSUFFICIENT-SAMPLE: {len(near)}")
    if len(near):
        print(near[["family", "config", "tf", "tr_n", "tr_exp", "va_n", "va_exp"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    # A vs B vs C comparison, per timeframe, on TRAIN expectancy (selection
    # discipline: train only) -- mean across the whole grid, the honest
    # apples-to-apples comparison since geometry grids are identical.
    print("\nA vs B vs C comparison (mean TRAIN expectancy across the shared geometry grid):")
    comp = df.groupby(["family", "tf"])["tr_exp"].mean().reset_index()
    print(comp.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    df.to_csv("step50_results_raw.csv", index=False)
    event_df.to_csv("step50_event_study_raw.csv", index=False)
    print("\nRaw results written to step50_results_raw.csv / step50_event_study_raw.csv")
    print("(step50_results.md written separately after this run)")
    return df, event_df, vol_report, meta


if __name__ == "__main__":
    main()
