"""
step90_level_significance.py — round 90: mechanizing round 84's finding.

Round 84 ran 40 blind discretionary chart drills. Shorts went 1W/11L
(-0.544R avg); every losing short broke a NEARBY (local, multi-hour) level
after a sharp move and got read as "momentum confirming down" when it was
really the extreme of the move. The one winning short (d018) broke to a
genuine new multi-day low outside the whole prior range. Separately,
consolidation-near-highs ("bull flag") only worked when the move producing
it was FRESH (d007/d024), not already extended (d037's 2930->3670 run).

This script tests both hypotheses MECHANICALLY, at scale, with full costs,
on BTC + ETH, 1h + 4h, cached data only, chronological 60/20/20 discipline
(train selects thresholds, val is read once, test is never touched).

RESEARCH ONLY. No commits, no live orders, no network calls. Writes exactly
three files: step90_level_significance.py (this file), step90_results.md,
step90_table.csv. No other file is read for writing and none is modified.

====================================================================
OPERATIONAL DEFINITIONS (see step90_results.md for the full writeup)
====================================================================

SWING DETECTION
  Reuses step41_shorts.confirmed_swings(d, k) verbatim (already the
  project's standing fractal-swing convention, also used by chart_reader.py
  itself). k=SWING_K=3: a swing point at bar i needs bars i-3..i+3 to
  confirm, so it is only KNOWABLE starting at bar i+3 (shift(k) discipline,
  built into confirmed_swings itself — verified no-lookahead by inspection
  and by construction below).

LEVEL TRACKING / BREAK EVENTS (scan_structure())
  A single forward pass over each frame. At every bar t:
    1. Check bar t's CLOSE against every currently ACTIVE (i.e. already
       known as of bar t-1's close — see note below) swing high/low. A
       close beyond an active level is a BREAK EVENT (long = close above an
       active swing high, short = close below an active swing low). Broken
       levels are removed from the active pool (never re-broken).
    2. For every active level NOT broken this bar, check for a TOUCH: bar
       t's high (for a swing high level) or low (for a swing low level)
       came within TOUCH_TOL = 0.25*ATR14[t] of the level without closing
       through it. touches is incremented per level.
    3. Any swing newly confirmed AT bar t (i.e. confirmed_swings reveals it
       this bar) is appended to the active pool for use starting bar t+1 —
       one bar more conservative than strictly necessary (all of a bar's
       OHLC is known simultaneously at its own close, so using a level
       confirmed at t to check t's own close would not technically be
       lookahead), but this removes any ambiguity about same-bar double
       duty and costs essentially nothing in sample size.
  age_bars = break_bar_idx - formation_bar_idx (formation = the actual
  swing bar, not the bar where it became knowable).
  touches = count of qualifying touches between formation and break.
  Multiple active levels can legitimately break on the same bar (a big
  move can clear several nested local levels at once); each is recorded as
  its own event with its own age/touch profile — intentional, not a bug.

TOUCH TOLERANCE: 0.25xATR14 at the touching bar. Chosen over a flat 0.15%-
  of-price tolerance (the brief's other suggested option) because it scales
  with the regime — BTC traded ~$5k in 2020 and ~$100k+ in 2025 on the same
  cached series, and a flat % tolerance would be far too tight in the wild
  2020-21 regime and far too loose in a quiet 2024 chop. A quarter of the
  bar's own typical range is close enough to count as a genuine approach,
  far enough that a slow multi-bar drift toward a level isn't counted as
  repeated "touches" every bar.

LEVEL-SIGNIFICANCE (LOCAL vs STRUCTURAL) CLASSIFICATION
  STRUCTURAL if age_bars >= age_cutoff AND touches >= touch_cutoff; LOCAL
  otherwise. Both cutoffs are SWEPT (see AGE_CUTOFFS / TOUCH_CUTOFFS below)
  and selected on BTC TRAIN only, independently per (timeframe, direction),
  maximizing (STRUCTURAL expectancy - LOCAL expectancy) subject to both
  buckets clearing MIN_TRAIN_TRADES on train. Confirmed once on BTC val,
  then (mandatory, only for cells that survive BTC train+val) replayed
  UNCHANGED on ETH.

EXIT RULE (one rule, chosen up front, applied uniformly — not swept)
  Pure time exit: force flat after MAX_HOLD_BARS (24 bars on both 1h [24h]
  and 4h [4 days], per the brief's own suggestion). No stop_pct/target_pct.
  Rationale: this round's question is about the ENTRY signal (is the break
  a locally-noisy event or a structurally-real one) — adding a stop/target
  sweep on top would let exit-rule tuning contaminate the level-
  significance answer, exactly the kind of hand-tuning the brief asks to
  avoid. Costs, funding, and execution match every other round in this
  project unchanged: run_backtest(execution="maker", real funding_series).

FRESHNESS (consolidation-near-highs continuation)
  "Leg start" = the formation bar of the most recently formed, still-
  UNBROKEN swing low as of bar t (i.e. literally the same active-level
  bookkeeping scan_structure() already tracks for short-side breaks,
  reused here for its long-side complement — no separate structure).
  "Consolidation near highs" (fixed operational definition, NOT swept —
  the freshness CUTOFF is what's swept, per the brief):
    - CONSOL_N=5 consecutive bars, each with (high-low) <= 0.7xATR14 at
      that bar ("tight" — comparable to a normal bar's typical range,
      deliberately not razor-tight so real consolidations aren't excluded)
    - each of those bars' LOW sits within 3% of the leg's rolling high-so-
      far (CONSOL_NEAR_HIGH_PCT=3.0)
    - the leg itself must be a real move: leg_high - low_at_leg_start >=
      2.0xATR14 at the consolidation's own start bar (MIN_LEG_ATR_MULT),
      so a flat chop with no real leg never qualifies
  distance_bars = consolidation_start_idx - leg_start_idx.
  distance_atr  = (close_at_consolidation_start - low_at_leg_start) /
                   ATR14_at_consolidation_start.
  Entry: long, first bar the N-bar window qualifies (day_trade_signal's own
  "ignore repeat signals while already in position" state machine handles
  de-duplication of a persisting consolidation the same way every other
  signal in this codebase already does).
  Distance cutoffs (both bar- and ATR-denominated, swept independently) are
  selected on BTC TRAIN only, confirmed on BTC val, and (mandatory if it
  survives) replayed unchanged on ETH.

DISCIPLINE
  - split_points(d) (step43_daytrade, imported) for the chronological
    60/20/20 split, identical to the rest of this repo.
  - ALL threshold selection (age/touch cutoffs, freshness cutoffs) happens
    on TRAIN ONLY, via a dedicated run_train() that never touches val.
  - VAL is read exactly once per selected config, via score() (step43_
    daytrade, imported) — the same train+val call every other round uses.
  - TEST ([i_va:n]) is never sliced, never scored, never referenced by any
    line of code in this file. Full stop.
  - MIN_TRAIN_TRADES=30 / MIN_VAL_TRADES=8 (imported from step43_daytrade,
    same floors as every prior round). Any cell short of these is reported
    as INSUFFICIENT SAMPLE, not hidden or rounded away.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import confirmed_swings
from step43_daytrade import (
    MIN_TRAIN_TRADES,
    MIN_VAL_TRADES,
    day_trade_signal,
    score,
    split_points,
)
from strategy import atr

pd.set_option("display.width", 160)

# ---------------------------------------------------------------------------
# constants (see module docstring for the rationale behind every one)
# ---------------------------------------------------------------------------

SWING_K = 3
TOUCH_ATR_FRAC = 0.25

AGE_CUTOFFS = [20, 50, 100, 200, 500]          # bars
TOUCH_CUTOFFS = [1, 2, 3]

MAX_HOLD_BARS = {"1h": 24, "4h": 24}            # 24h on 1h, 4 days on 4h

CONSOL_N = 5
CONSOL_TIGHT_MULT = 0.7
CONSOL_NEAR_HIGH_PCT = 3.0
MIN_LEG_ATR_MULT = 2.0

FRESH_BAR_CUTOFFS = [10, 20, 40, 80, 150]
FRESH_ATR_CUTOFFS = [2.0, 4.0, 6.0, 10.0, 15.0]

ASSETS = ("BTCUSDT", "ETHUSDT")
ASSET_LABEL = {"BTCUSDT": "BTC", "ETHUSDT": "ETH"}
TFS = ("1h", "4h")


# ---------------------------------------------------------------------------
# data loading (cache-only, no network — see module docstring)
# ---------------------------------------------------------------------------

def load_frames(symbol):
    frames, funding = {}, {}
    fund_hist = fetch_funding_history(symbol)
    for tf in TFS:
        d = fetch_bybit_deep(tf, symbol)
        frames[tf] = d
        funding[tf] = align_funding(d, fund_hist)
    return frames, funding


def build_meta(frames):
    meta = {}
    for tf, d in frames.items():
        n, i_tr, i_va = split_points(d)
        meta[tf] = {"n": n, "i_tr": i_tr, "i_va": i_va}
    return meta


# ---------------------------------------------------------------------------
# core scan: swing/level tracking + break events + leg-start bookkeeping
# ---------------------------------------------------------------------------

def scan_structure(d: pd.DataFrame, k: int = SWING_K,
                    touch_atr_frac: float = TOUCH_ATR_FRAC):
    """One forward, causal pass. Returns (events_df, leg_start_idx, atr_arr).

    events_df columns: idx, direction ('long'/'short'), formation_idx,
    age_bars, touches, level_price.

    leg_start_idx[t] = formation bar index of the most recently formed,
    still-unbroken swing LOW as of bar t's close (NaN if none) — the
    active-low bookkeeping this scan already needs, reused directly by
    detect_consolidations() for the freshness feature.
    """
    n = len(d)
    highs = d["high"].to_numpy()
    lows = d["low"].to_numpy()
    closes = d["close"].to_numpy()
    a = atr(d, 14).to_numpy()

    sh_price, sl_price = confirmed_swings(d, k)
    sh_price = sh_price.to_numpy()
    sl_price = sl_price.to_numpy()

    active_highs: list[dict] = []
    active_lows: list[dict] = []
    events: list[dict] = []
    leg_start_idx = np.full(n, np.nan)

    for t in range(n):
        tol = touch_atr_frac * a[t] if not np.isnan(a[t]) else 0.0
        c, h, l = closes[t], highs[t], lows[t]

        still = []
        for lvl in active_highs:
            if c > lvl["price"]:
                events.append({
                    "idx": t, "direction": "long",
                    "formation_idx": lvl["formation_idx"],
                    "age_bars": t - lvl["formation_idx"],
                    "touches": lvl["touches"], "level_price": lvl["price"],
                })
            else:
                if tol > 0 and h >= lvl["price"] - tol:
                    lvl["touches"] += 1
                still.append(lvl)
        active_highs = still

        still = []
        for lvl in active_lows:
            if c < lvl["price"]:
                events.append({
                    "idx": t, "direction": "short",
                    "formation_idx": lvl["formation_idx"],
                    "age_bars": t - lvl["formation_idx"],
                    "touches": lvl["touches"], "level_price": lvl["price"],
                })
            else:
                if tol > 0 and l <= lvl["price"] + tol:
                    lvl["touches"] += 1
                still.append(lvl)
        active_lows = still

        # leg start for freshness: state known as of bar t's close, BEFORE
        # this bar's own newly-confirmed swings join the pool (those join
        # for bar t+1 onward, per the conservative rule above).
        leg_start_idx[t] = active_lows[-1]["formation_idx"] if active_lows else np.nan

        if not np.isnan(sh_price[t]):
            active_highs.append({"formation_idx": t - k, "price": float(sh_price[t]), "touches": 0})
        if not np.isnan(sl_price[t]):
            active_lows.append({"formation_idx": t - k, "price": float(sl_price[t]), "touches": 0})

    events_df = pd.DataFrame(events, columns=["idx", "direction", "formation_idx",
                                               "age_bars", "touches", "level_price"])
    return events_df, leg_start_idx, a


def detect_consolidations(d: pd.DataFrame, leg_start_idx: np.ndarray, atr_arr: np.ndarray,
                           N: int = CONSOL_N, tight_mult: float = CONSOL_TIGHT_MULT,
                           near_high_pct: float = CONSOL_NEAR_HIGH_PCT,
                           min_leg_atr_mult: float = MIN_LEG_ATR_MULT) -> pd.DataFrame:
    """Consolidation-near-highs events (see module docstring for the fixed
    operational definition). Returns idx / distance_bars / distance_atr."""
    n = len(d)
    highs = d["high"].to_numpy()
    lows = d["low"].to_numpy()
    closes = d["close"].to_numpy()
    ranges = highs - lows

    events = []
    cur_leg_start = None
    leg_high = np.nan

    for t in range(n):
        ls = leg_start_idx[t]
        if np.isnan(ls):
            cur_leg_start = None
            continue
        ls = int(ls)
        if cur_leg_start != ls:
            cur_leg_start = ls
            leg_high = float(highs[ls:t + 1].max())
        else:
            leg_high = max(leg_high, float(highs[t]))

        w_start = t - N + 1
        if w_start <= cur_leg_start:
            continue

        ok = True
        for i in range(w_start, t + 1):
            ai = atr_arr[i]
            if np.isnan(ai) or ai <= 0:
                ok = False
                break
            if ranges[i] > tight_mult * ai:
                ok = False
                break
            if lows[i] < leg_high * (1 - near_high_pct / 100):
                ok = False
                break
        if not ok:
            continue

        a_t = atr_arr[t]
        low_at_leg_start = float(lows[cur_leg_start])
        if np.isnan(a_t) or a_t <= 0:
            continue
        if (leg_high - low_at_leg_start) < min_leg_atr_mult * a_t:
            continue

        a_ws = atr_arr[w_start]
        if np.isnan(a_ws) or a_ws <= 0:
            continue

        events.append({
            "idx": t,
            "distance_bars": w_start - cur_leg_start,
            "distance_atr": (closes[w_start] - low_at_leg_start) / a_ws,
        })

    return pd.DataFrame(events, columns=["idx", "distance_bars", "distance_atr"])


# ---------------------------------------------------------------------------
# signal construction + backtest plumbing
# ---------------------------------------------------------------------------

def signal_from_mask(d: pd.DataFrame, mask: np.ndarray, direction: str, max_hold_bars: int) -> pd.Series:
    if direction == "long":
        el = pd.Series(mask, index=d.index)
        es = pd.Series(False, index=d.index)
    else:
        el = pd.Series(False, index=d.index)
        es = pd.Series(mask, index=d.index)
    return day_trade_signal(d, el, es, max_hold_bars)


def run_train(d: pd.DataFrame, f: pd.Series, i_tr: int, sig: pd.Series):
    """Identical in shape to step43_daytrade.score()'s inner run() closure,
    pointed ONLY at [0:i_tr]. Used exclusively for threshold sweeps so val
    is never even computed during selection."""
    return run_backtest(
        d.iloc[:i_tr].reset_index(drop=True),
        sig.iloc[:i_tr].reset_index(drop=True),
        execution="maker",
        funding_series=f.iloc[:i_tr].reset_index(drop=True),
        stop_pct=None, target_pct=None,
    )


def build_level_masks(events_df: pd.DataFrame, direction: str, age_cut: int, touch_cut: int, n: int):
    sub = events_df[events_df["direction"] == direction]
    structural = np.zeros(n, dtype=bool)
    local = np.zeros(n, dtype=bool)
    if sub.empty:
        return structural, local
    is_struct = (sub["age_bars"] >= age_cut) & (sub["touches"] >= touch_cut)
    structural[sub.loc[is_struct, "idx"].astype(int).to_numpy()] = True
    local[sub.loc[~is_struct, "idx"].astype(int).to_numpy()] = True
    return structural, local


def build_fresh_masks(events_df: pd.DataFrame, col: str, cutoff: float, n: int):
    fresh = np.zeros(n, dtype=bool)
    extended = np.zeros(n, dtype=bool)
    if events_df.empty:
        return fresh, extended
    is_fresh = events_df[col] < cutoff
    fresh[events_df.loc[is_fresh, "idx"].astype(int).to_numpy()] = True
    extended[events_df.loc[~is_fresh, "idx"].astype(int).to_numpy()] = True
    return fresh, extended


def trades_per_year(n_trades: int, d: pd.DataFrame, lo: int, hi: int) -> float:
    if n_trades == 0 or hi <= lo:
        return float("nan")
    span_yrs = (d["timestamp"].iloc[hi - 1] - d["timestamp"].iloc[lo]).total_seconds() / (365.25 * 86400)
    return round(n_trades / span_yrs, 2) if span_yrs > 0 else float("nan")


def cell_row(**kw):
    return kw


# ---------------------------------------------------------------------------
# LEVEL SIGNIFICANCE: sweep on BTC train, select, confirm on val, ETH transfer
# ---------------------------------------------------------------------------

def level_sweep_btc(d, f, i_tr, events_df, tf, direction, max_hold_bars, table_rows):
    n = len(d)
    best = None  # (gap, age_cut, touch_cut, tr_s, tr_l)
    for age_cut in AGE_CUTOFFS:
        for touch_cut in TOUCH_CUTOFFS:
            structural, local = build_level_masks(events_df, direction, age_cut, touch_cut, n)
            sig_s = signal_from_mask(d, structural, direction, max_hold_bars)
            sig_l = signal_from_mask(d, local, direction, max_hold_bars)
            tr_s = run_train(d, f, i_tr, sig_s)
            tr_l = run_train(d, f, i_tr, sig_l)
            table_rows.append(cell_row(
                section="level_sweep", asset="BTC", tf=tf, direction=direction,
                age_cutoff=age_cut, touch_cutoff=touch_cut, dist_bar_cutoff=None,
                dist_atr_cutoff=None, bucket="STRUCTURAL", split="train",
                n_trades=len(tr_s.trades), expectancy=tr_s.expectancy,
                trades_per_year=trades_per_year(len(tr_s.trades), d, 0, i_tr),
                win_rate_pct=tr_s.win_rate * 100,
            ))
            table_rows.append(cell_row(
                section="level_sweep", asset="BTC", tf=tf, direction=direction,
                age_cutoff=age_cut, touch_cutoff=touch_cut, dist_bar_cutoff=None,
                dist_atr_cutoff=None, bucket="LOCAL", split="train",
                n_trades=len(tr_l.trades), expectancy=tr_l.expectancy,
                trades_per_year=trades_per_year(len(tr_l.trades), d, 0, i_tr),
                win_rate_pct=tr_l.win_rate * 100,
            ))
            if len(tr_s.trades) >= MIN_TRAIN_TRADES and len(tr_l.trades) >= MIN_TRAIN_TRADES:
                gap = tr_s.expectancy - tr_l.expectancy
                if best is None or gap > best[0]:
                    best = (gap, age_cut, touch_cut, tr_s, tr_l)
    return best


def level_significance_section(btc_frames, btc_funding, btc_meta, btc_events,
                                eth_frames, eth_funding, eth_meta, eth_events,
                                table_rows):
    selected = {}   # (tf, direction) -> dict with chosen config + BTC train/val results
    for tf in TFS:
        d, f = btc_frames[tf], btc_funding[tf]
        i_tr, i_va = btc_meta[tf]["i_tr"], btc_meta[tf]["i_va"]
        events_df = btc_events[tf]
        mh = MAX_HOLD_BARS[tf]
        for direction in ("long", "short"):
            best = level_sweep_btc(d, f, i_tr, events_df, tf, direction, mh, table_rows)
            if best is None:
                selected[(tf, direction)] = {"status": "INSUFFICIENT_SAMPLE_TRAIN"}
                continue
            gap, age_cut, touch_cut, _, _ = best
            n = len(d)
            structural, local = build_level_masks(events_df, direction, age_cut, touch_cut, n)
            sig_s = signal_from_mask(d, structural, direction, mh)
            sig_l = signal_from_mask(d, local, direction, mh)
            s_tr, s_va = score(d, sig_s, f, i_tr, i_va, execution="maker")
            l_tr, l_va = score(d, sig_l, f, i_tr, i_va, execution="maker")

            for bucket, tr, va in (("STRUCTURAL", s_tr, s_va), ("LOCAL", l_tr, l_va)):
                for split_name, res, lo, hi in (("train", tr, 0, i_tr), ("val", va, i_tr, i_va)):
                    table_rows.append(cell_row(
                        section="level_selected", asset="BTC", tf=tf, direction=direction,
                        age_cutoff=age_cut, touch_cutoff=touch_cut, dist_bar_cutoff=None,
                        dist_atr_cutoff=None, bucket=bucket, split=split_name,
                        n_trades=len(res.trades), expectancy=res.expectancy,
                        trades_per_year=trades_per_year(len(res.trades), d, lo, hi),
                        win_rate_pct=res.win_rate * 100,
                    ))

            survives = (s_tr.expectancy > 0 and s_va.expectancy > 0
                        and len(s_tr.trades) >= MIN_TRAIN_TRADES
                        and len(s_va.trades) >= MIN_VAL_TRADES)
            selected[(tf, direction)] = {
                "status": "SURVIVOR" if survives else "FAIL_OR_INSUFFICIENT",
                "age_cutoff": age_cut, "touch_cutoff": touch_cut,
                "s_tr": s_tr, "s_va": s_va, "l_tr": l_tr, "l_va": l_va,
            }

            if survives:
                # mandatory ETH transfer, IDENTICAL config, no re-tuning
                ed, ef = eth_frames[tf], eth_funding[tf]
                ei_tr, ei_va = eth_meta[tf]["i_tr"], eth_meta[tf]["i_va"]
                eevents = eth_events[tf]
                en = len(ed)
                e_structural, e_local = build_level_masks(eevents, direction, age_cut, touch_cut, en)
                e_sig_s = signal_from_mask(ed, e_structural, direction, mh)
                e_sig_l = signal_from_mask(ed, e_local, direction, mh)
                es_tr, es_va = score(ed, e_sig_s, ef, ei_tr, ei_va, execution="maker")
                el_tr, el_va = score(ed, e_sig_l, ef, ei_tr, ei_va, execution="maker")
                for bucket, tr, va in (("STRUCTURAL", es_tr, es_va), ("LOCAL", el_tr, el_va)):
                    for split_name, res, lo, hi in (("train", tr, 0, ei_tr), ("val", va, ei_tr, ei_va)):
                        table_rows.append(cell_row(
                            section="level_eth_transfer", asset="ETH", tf=tf, direction=direction,
                            age_cutoff=age_cut, touch_cutoff=touch_cut, dist_bar_cutoff=None,
                            dist_atr_cutoff=None, bucket=bucket, split=split_name,
                            n_trades=len(res.trades), expectancy=res.expectancy,
                            trades_per_year=trades_per_year(len(res.trades), ed, lo, hi),
                            win_rate_pct=res.win_rate * 100,
                        ))
                eth_survives = (es_tr.expectancy > 0 and es_va.expectancy > 0
                                and len(es_tr.trades) >= MIN_TRAIN_TRADES
                                and len(es_va.trades) >= MIN_VAL_TRADES)
                selected[(tf, direction)]["eth_es_tr"] = es_tr
                selected[(tf, direction)]["eth_es_va"] = es_va
                selected[(tf, direction)]["eth_el_tr"] = el_tr
                selected[(tf, direction)]["eth_el_va"] = el_va
                selected[(tf, direction)]["eth_survives"] = eth_survives

    return selected


# ---------------------------------------------------------------------------
# FRESHNESS: sweep on BTC train, select, confirm on val, ETH transfer
# ---------------------------------------------------------------------------

def freshness_sweep_btc(d, f, i_tr, cons_df, tf, mh, col, cutoffs, table_rows):
    n = len(d)
    best = None
    for cutoff in cutoffs:
        fresh, extended = build_fresh_masks(cons_df, col, cutoff, n)
        sig_f = signal_from_mask(d, fresh, "long", mh)
        sig_e = signal_from_mask(d, extended, "long", mh)
        tr_f = run_train(d, f, i_tr, sig_f)
        tr_e = run_train(d, f, i_tr, sig_e)
        table_rows.append(cell_row(
            section="fresh_sweep", asset="BTC", tf=tf, direction="long",
            age_cutoff=None, touch_cutoff=None,
            dist_bar_cutoff=cutoff if col == "distance_bars" else None,
            dist_atr_cutoff=cutoff if col == "distance_atr" else None,
            bucket="FRESH", split="train",
            n_trades=len(tr_f.trades), expectancy=tr_f.expectancy,
            trades_per_year=trades_per_year(len(tr_f.trades), d, 0, i_tr),
            win_rate_pct=tr_f.win_rate * 100,
        ))
        table_rows.append(cell_row(
            section="fresh_sweep", asset="BTC", tf=tf, direction="long",
            age_cutoff=None, touch_cutoff=None,
            dist_bar_cutoff=cutoff if col == "distance_bars" else None,
            dist_atr_cutoff=cutoff if col == "distance_atr" else None,
            bucket="EXTENDED", split="train",
            n_trades=len(tr_e.trades), expectancy=tr_e.expectancy,
            trades_per_year=trades_per_year(len(tr_e.trades), d, 0, i_tr),
            win_rate_pct=tr_e.win_rate * 100,
        ))
        if len(tr_f.trades) >= MIN_TRAIN_TRADES and len(tr_e.trades) >= MIN_TRAIN_TRADES:
            gap = tr_f.expectancy - tr_e.expectancy
            if best is None or gap > best[0]:
                best = (gap, cutoff)
    return best


def freshness_section(btc_frames, btc_funding, btc_meta, btc_cons,
                       eth_frames, eth_funding, eth_meta, eth_cons, table_rows):
    selected = {}
    for tf in TFS:
        d, f = btc_frames[tf], btc_funding[tf]
        i_tr, i_va = btc_meta[tf]["i_tr"], btc_meta[tf]["i_va"]
        cons_df = btc_cons[tf]
        mh = MAX_HOLD_BARS[tf]

        results_by_col = {}
        for col, cutoffs in (("distance_bars", FRESH_BAR_CUTOFFS),
                              ("distance_atr", FRESH_ATR_CUTOFFS)):
            best = freshness_sweep_btc(d, f, i_tr, cons_df, tf, mh, col, cutoffs, table_rows)
            results_by_col[col] = best

        # pick whichever denomination (bars vs ATR) gives the larger train gap;
        # if neither meets min-sample, this cell is INSUFFICIENT SAMPLE.
        valid = {c: b for c, b in results_by_col.items() if b is not None}
        if not valid:
            selected[tf] = {"status": "INSUFFICIENT_SAMPLE_TRAIN"}
            continue
        best_col = max(valid, key=lambda c: valid[c][0])
        gap, cutoff = valid[best_col]

        n = len(d)
        fresh, extended = build_fresh_masks(cons_df, best_col, cutoff, n)
        sig_f = signal_from_mask(d, fresh, "long", mh)
        sig_e = signal_from_mask(d, extended, "long", mh)
        f_tr, f_va = score(d, sig_f, f, i_tr, i_va, execution="maker")
        e_tr, e_va = score(d, sig_e, f, i_tr, i_va, execution="maker")

        for bucket, tr, va in (("FRESH", f_tr, f_va), ("EXTENDED", e_tr, e_va)):
            for split_name, res, lo, hi in (("train", tr, 0, i_tr), ("val", va, i_tr, i_va)):
                table_rows.append(cell_row(
                    section="fresh_selected", asset="BTC", tf=tf, direction="long",
                    age_cutoff=None, touch_cutoff=None,
                    dist_bar_cutoff=cutoff if best_col == "distance_bars" else None,
                    dist_atr_cutoff=cutoff if best_col == "distance_atr" else None,
                    bucket=bucket, split=split_name,
                    n_trades=len(res.trades), expectancy=res.expectancy,
                    trades_per_year=trades_per_year(len(res.trades), d, lo, hi),
                    win_rate_pct=res.win_rate * 100,
                ))

        survives = (f_tr.expectancy > 0 and f_va.expectancy > 0
                    and len(f_tr.trades) >= MIN_TRAIN_TRADES
                    and len(f_va.trades) >= MIN_VAL_TRADES)
        selected[tf] = {
            "status": "SURVIVOR" if survives else "FAIL_OR_INSUFFICIENT",
            "col": best_col, "cutoff": cutoff,
            "f_tr": f_tr, "f_va": f_va, "e_tr": e_tr, "e_va": e_va,
        }

        if survives:
            ed, ef = eth_frames[tf], eth_funding[tf]
            ei_tr, ei_va = eth_meta[tf]["i_tr"], eth_meta[tf]["i_va"]
            e_cons_df = eth_cons[tf]
            en = len(ed)
            ef_fresh, ef_ext = build_fresh_masks(e_cons_df, best_col, cutoff, en)
            e_sig_f = signal_from_mask(ed, ef_fresh, "long", mh)
            e_sig_e = signal_from_mask(ed, ef_ext, "long", mh)
            ef_tr, ef_va = score(ed, e_sig_f, ef, ei_tr, ei_va, execution="maker")
            ee_tr, ee_va = score(ed, e_sig_e, ef, ei_tr, ei_va, execution="maker")
            for bucket, tr, va in (("FRESH", ef_tr, ef_va), ("EXTENDED", ee_tr, ee_va)):
                for split_name, res, lo, hi in (("train", tr, 0, ei_tr), ("val", va, ei_tr, ei_va)):
                    table_rows.append(cell_row(
                        section="fresh_eth_transfer", asset="ETH", tf=tf, direction="long",
                        age_cutoff=None, touch_cutoff=None,
                        dist_bar_cutoff=cutoff if best_col == "distance_bars" else None,
                        dist_atr_cutoff=cutoff if best_col == "distance_atr" else None,
                        bucket=bucket, split=split_name,
                        n_trades=len(res.trades), expectancy=res.expectancy,
                        trades_per_year=trades_per_year(len(res.trades), ed, lo, hi),
                        win_rate_pct=res.win_rate * 100,
                    ))
            eth_survives = (ef_tr.expectancy > 0 and ef_va.expectancy > 0
                            and len(ef_tr.trades) >= MIN_TRAIN_TRADES
                            and len(ef_va.trades) >= MIN_VAL_TRADES)
            selected[tf]["eth_f_tr"] = ef_tr
            selected[tf]["eth_f_va"] = ef_va
            selected[tf]["eth_e_tr"] = ee_tr
            selected[tf]["eth_e_va"] = ee_va
            selected[tf]["eth_survives"] = eth_survives

    return selected


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("Loading cached BTC + ETH data (no network calls expected)...")
    btc_frames, btc_funding = load_frames("BTCUSDT")
    eth_frames, eth_funding = load_frames("ETHUSDT")
    btc_meta = build_meta(btc_frames)
    eth_meta = build_meta(eth_frames)
    for tf in TFS:
        print(f"  BTC {tf}: {btc_meta[tf]['n']} bars, train->{btc_frames[tf]['timestamp'].iloc[btc_meta[tf]['i_tr']]:%Y-%m-%d} "
              f"val->{btc_frames[tf]['timestamp'].iloc[btc_meta[tf]['i_va']]:%Y-%m-%d} (test sealed)")
        print(f"  ETH {tf}: {eth_meta[tf]['n']} bars, train->{eth_frames[tf]['timestamp'].iloc[eth_meta[tf]['i_tr']]:%Y-%m-%d} "
              f"val->{eth_frames[tf]['timestamp'].iloc[eth_meta[tf]['i_va']]:%Y-%m-%d} (test sealed)")

    print("\nScanning swing structure / break events (BTC + ETH, 1h + 4h)...")
    btc_events, eth_events = {}, {}
    btc_leg, eth_leg = {}, {}
    btc_atr, eth_atr = {}, {}
    for tf in TFS:
        btc_events[tf], btc_leg[tf], btc_atr[tf] = scan_structure(btc_frames[tf])
        eth_events[tf], eth_leg[tf], eth_atr[tf] = scan_structure(eth_frames[tf])
        print(f"  BTC {tf}: {len(btc_events[tf])} break events "
              f"({(btc_events[tf]['direction']=='long').sum()} long / "
              f"{(btc_events[tf]['direction']=='short').sum()} short)")
        print(f"  ETH {tf}: {len(eth_events[tf])} break events "
              f"({(eth_events[tf]['direction']=='long').sum()} long / "
              f"{(eth_events[tf]['direction']=='short').sum()} short)")

    print("\nDetecting consolidation-near-highs events (BTC + ETH, 1h + 4h)...")
    btc_cons, eth_cons = {}, {}
    for tf in TFS:
        btc_cons[tf] = detect_consolidations(btc_frames[tf], btc_leg[tf], btc_atr[tf])
        eth_cons[tf] = detect_consolidations(eth_frames[tf], eth_leg[tf], eth_atr[tf])
        print(f"  BTC {tf}: {len(btc_cons[tf])} consolidation events")
        print(f"  ETH {tf}: {len(eth_cons[tf])} consolidation events")

    table_rows: list[dict] = []

    print("\n" + "=" * 78)
    print("LEVEL SIGNIFICANCE — sweeping BTC train, selecting, confirming on val...")
    print("=" * 78)
    level_selected = level_significance_section(
        btc_frames, btc_funding, btc_meta, btc_events,
        eth_frames, eth_funding, eth_meta, eth_events,
        table_rows,
    )
    for (tf, direction), info in level_selected.items():
        print(f"\n[BTC {tf} {direction}] status={info['status']}")
        if "age_cutoff" in info:
            print(f"  selected: age>={info['age_cutoff']} touches>={info['touch_cutoff']}")
            print(f"  STRUCTURAL train n={len(info['s_tr'].trades)} exp=${info['s_tr'].expectancy:+.2f}  "
                  f"val n={len(info['s_va'].trades)} exp=${info['s_va'].expectancy:+.2f}")
            print(f"  LOCAL      train n={len(info['l_tr'].trades)} exp=${info['l_tr'].expectancy:+.2f}  "
                  f"val n={len(info['l_va'].trades)} exp=${info['l_va'].expectancy:+.2f}")
            if "eth_survives" in info:
                print(f"  ETH transfer: STRUCTURAL train n={len(info['eth_es_tr'].trades)} "
                      f"exp=${info['eth_es_tr'].expectancy:+.2f}  val n={len(info['eth_es_va'].trades)} "
                      f"exp=${info['eth_es_va'].expectancy:+.2f}  eth_survives={info['eth_survives']}")

    print("\n" + "=" * 78)
    print("FRESHNESS — sweeping BTC train, selecting, confirming on val...")
    print("=" * 78)
    fresh_selected = freshness_section(
        btc_frames, btc_funding, btc_meta, btc_cons,
        eth_frames, eth_funding, eth_meta, eth_cons,
        table_rows,
    )
    for tf, info in fresh_selected.items():
        print(f"\n[BTC {tf}] status={info['status']}")
        if "cutoff" in info:
            print(f"  selected: {info['col']} < {info['cutoff']}")
            print(f"  FRESH    train n={len(info['f_tr'].trades)} exp=${info['f_tr'].expectancy:+.2f}  "
                  f"val n={len(info['f_va'].trades)} exp=${info['f_va'].expectancy:+.2f}")
            print(f"  EXTENDED train n={len(info['e_tr'].trades)} exp=${info['e_tr'].expectancy:+.2f}  "
                  f"val n={len(info['e_va'].trades)} exp=${info['e_va'].expectancy:+.2f}")
            if "eth_survives" in info:
                print(f"  ETH transfer: FRESH train n={len(info['eth_f_tr'].trades)} "
                      f"exp=${info['eth_f_tr'].expectancy:+.2f}  val n={len(info['eth_f_va'].trades)} "
                      f"exp=${info['eth_f_va'].expectancy:+.2f}  eth_survives={info['eth_survives']}")

    df = pd.DataFrame(table_rows)
    df.to_csv("step90_table.csv", index=False)
    print(f"\nwrote step90_table.csv: {len(df)} rows")

    return level_selected, fresh_selected, df


if __name__ == "__main__":
    main()
