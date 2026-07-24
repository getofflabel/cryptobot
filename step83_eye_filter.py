"""
step83_eye_filter.py — ROUND 83: DOES THE EYE IMPROVE THE STRATEGIES WE
ALREADY OWN?

R82 built the eye x indicator matrix. Its best cell FAILED its sealed test
(-$9.51/t on BTC) and was too thin on ETH — no new edge there. But R82's
structural finding was strong: eye-gating raised cross-asset survival from
2/94 (ungated, R76) to 40/289. This round asks whether that same
information shows up as a FILTER on strategies we ALREADY trade live,
rather than as a generator of brand-new ones.

METHOD (see module docstring sections below for exact per-strategy
reconstruction). Every entry-construction function is IMPORTED from the
file that already owns it — never retyped — so this script can never
silently drift from what actually trades. For each strategy x asset:

  1. Build the strategy's FULL, unfiltered entry events on the strategy's
     own native timeframe, using its own live parameters.
  2. Run it through the SAME backtest engine/exit convention it already
     uses (backtest.run_backtest's engine-managed stop/target/max_hold for
     B/C/D/E/F; step65_news_eyes.simulate's event-driven N2 structure-
     trailing simulator for A, reused verbatim) -> the REALIZED trade list.
     This is "AS IT TRADES TODAY."
  3. Look up step82_eye's vectorized eye state AT EACH TRADE'S OWN ENTRY
     BAR (computed once per asset/timeframe on the full causal history —
     trailing-window math never leaks future bars, so slicing the frame
     for entry-construction elsewhere in the repo doesn't change what the
     eye saw at any given bar).
  4. PARTITION the realized trade list into KEPT / SKIPPED by three rules:
       veto_tradeable  -- skip if eye.tradeable == False
       veto_messy      -- skip if eye.quality == "messy"
       routed          -- skip UNLESS eye.best_tool matches the strategy's
                          assigned tool (see ROUTE_MAP below)
     This is a partition of REALIZED trades, not a re-simulation with
     freed-up capacity dynamics -- it directly answers "would the eye have
     caught the losers", which is the round's actual question, without
     confounding it with how a gated state machine might reschedule into
     a DIFFERENT trade later. That tradeoff is stated here once, honestly,
     rather than re-litigated at every call site.
  5. DUMB-VETO CONTROL: for each veto rule, resample the SAME NUMBER of
     trades to remove, chosen uniformly at random from the realized trade
     list, 200 times. Report where the eye's actual removed-PnL and
     kept-expectancy fall in that random distribution. If the eye isn't
     clearly better than random, that is reported plainly.

ROUTE_MAP (best_tool the eye must show for the ROUTED variant to keep a
trade) -- the task text read "trend-follow for C/F ... breakout for C",
self-contradictory (C named twice). Resolved as the only internally
consistent reading: breakout -> C (breakout strategy), trend-follow -> F
(trend strategy); C/F were transposed once in the brief. B (range-fade)
was explicit. A/D/E are argued below, in ROUTE_MAP's own comment.

TRAIN/VAL/TEST: chronological 60/20/20 via step43_daytrade.split_points
(or step65's own news-span variant for A). The sealed 20% is never sliced
into any variable this script's logic can reach -- same discipline as
every other step*_*.py in this repo. Both TRAIN and VAL trades are scored
and reported; the pooled TRAIN+VAL trade list is the primary number (more
sample for the dumb-veto control) with train/val shown separately in the
CSV for anyone who wants the split-out view.

RESEARCH ONLY. Writes only step83_eye_filter.py (this file),
step83_results.md, step83_table.csv. No commits, no live orders. Does not
touch step79/step80/step81 or any file owned by a concurrent agent.
"""

from __future__ import annotations

import itertools
import json
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import chart_reader as CR
import step82_eye as EYE
from backtest import CostModel, run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import days_to_bars
from step43_daytrade import (
    CHAMP_KW,
    champ_aligned,
    day_trade_signal,
    hours_to_bars,
    split_points,
)
from step56_smc_toolkit import (
    bias_series_4h,
    bos_chain,
    equilibrium,
    fib_entries,
    fvg_signals,
    leg_tracker,
    liquidity_pools,
    sweep_events,
    train_median_stop_pct,
)
from step58_divergence_mtf import STOP_CAP_SWING, divergence_events, swing_stop_pct
from step65_news_eyes import K_SWING_PRIMARY as NEWS_K_SWING_PRIMARY
from step65_news_eyes import build_news_entries
from step65_news_eyes import n2_builder as news_n2_builder
from step65_news_eyes import simulate as news_simulate
from step65_news_eyes import slice_meta as news_slice_meta
import strategy as STRAT

T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:8.1f}s]", *a, flush=True)


INITIAL_EQUITY = 10_000.0
EXECUTION = "maker"          # repo-standard convention for these day-trade books
RNG_SEED = 83
N_CONTROL_DRAWS = 200

# ===========================================================================
# 0. EYE — best_tool/tradeable, vectorized (validated against chart_reader
#    ._best_tool exhaustively over the whole combinatorial state space
#    below, since _best_tool is a pure function of the 4 axis strings).
# ===========================================================================

def add_best_tool(eye_df: pd.DataFrame) -> pd.DataFrame:
    structure = eye_df["structure"].to_numpy()
    location = eye_df["location"].to_numpy()
    quality = eye_df["quality"].to_numpy()
    momentum = eye_df["momentum"].to_numpy()
    n = len(eye_df)

    breaking = np.isin(location, ("breaking out", "breaking down"))
    messy = quality == "messy"
    trending = np.isin(structure, ("uptrend", "downtrend"))
    range_edge = (structure == "range") & np.isin(location, ("at range low", "at range high"))
    expanding = momentum == "expanding"

    tradeable = np.zeros(n, dtype=bool)
    best_tool = np.full(n, "stand aside", dtype=object)

    tradeable[breaking] = ~(messy[breaking] & ~expanding[breaking])
    best_tool[breaking] = "breakout"

    rest = ~breaking
    idx_trend = rest & ~messy & trending
    best_tool[idx_trend] = "trend-follow"
    tradeable[idx_trend] = True

    idx_range = rest & ~messy & ~trending & range_edge
    best_tool[idx_range] = "range-fade"
    tradeable[idx_range] = True
    # everything else (messy-and-not-breaking, or clean/no-trend/no-edge)
    # stays "stand aside" / tradeable False, already the array default.

    out = eye_df.copy()
    out["tradeable"] = tradeable
    out["best_tool"] = best_tool
    return out


def validate_best_tool_exhaustive():
    """Pure-function combinatorial check against chart_reader._best_tool
    itself (no data needed) -- every (structure, location, quality,
    momentum) combination that can ever appear."""
    structures = ["uptrend", "downtrend", "range", "transition", "chop"]
    locations = ["breaking out", "breaking down", "at range high", "at range low",
                 "mid range", "pulling back in trend"]
    qualities = ["messy", "clean"]
    momenta = ["expanding", "contracting", "stalling"]
    combos = list(itertools.product(structures, locations, qualities, momenta))
    df = pd.DataFrame(combos, columns=["structure", "location", "quality", "momentum"])
    vec = add_best_tool(df)
    n_bad = 0
    for i, row in df.iterrows():
        real_tradeable, real_tool = CR._best_tool(row["structure"], row["location"],
                                                   row["quality"], row["momentum"])
        if real_tradeable != vec.iloc[i]["tradeable"] or real_tool != vec.iloc[i]["best_tool"]:
            n_bad += 1
    log(f"add_best_tool exhaustive check: {len(combos)} combos, {n_bad} mismatches")
    assert n_bad == 0, "vectorized best_tool disagrees with chart_reader._best_tool"


# ===========================================================================
# 1. EYE CACHE — one label_eye_states() + add_best_tool() per (asset, tf),
#    computed on the FULL native history. Every strategy below, regardless
#    of how it slices its own frame for entry construction, looks up the
#    eye read via a timestamp -> row-index map into THIS full frame, so
#    the eye read at any bar is always the true causal read (trailing-
#    window math never leaks future bars, so a full-history computation
#    is never less correct than a slice-local one -- only ever more
#    complete near a slice's own start).
# ===========================================================================

_FRAME_CACHE: dict[tuple[str, str], pd.DataFrame] = {}
_EYE_CACHE: dict[tuple[str, str], pd.DataFrame] = {}
_TS_IDX_CACHE: dict[tuple[str, str], dict] = {}
_FUND_CACHE: dict[str, pd.DataFrame] = {}


def frame_for(asset: str, tf: str) -> pd.DataFrame:
    key = (asset, tf)
    if key not in _FRAME_CACHE:
        _FRAME_CACHE[key] = fetch_bybit_deep(tf, f"{asset}USDT")
    return _FRAME_CACHE[key]


def funding_hist_for(asset: str) -> pd.DataFrame:
    if asset not in _FUND_CACHE:
        _FUND_CACHE[asset] = fetch_funding_history(f"{asset}USDT")
    return _FUND_CACHE[asset]


def eye_for(asset: str, tf: str) -> pd.DataFrame:
    key = (asset, tf)
    if key not in _EYE_CACHE:
        d = frame_for(asset, tf)
        labeled = EYE.label_eye_states(d)
        labeled = add_best_tool(labeled)
        _EYE_CACHE[key] = labeled.reset_index(drop=True)
        _TS_IDX_CACHE[key] = {ts: i for i, ts in enumerate(d["timestamp"].to_numpy())}
        log(f"eye labeled {asset} {tf}: {len(d)} bars")
    return _EYE_CACHE[key]


def ts_idx_for(asset: str, tf: str) -> dict:
    if (asset, tf) not in _TS_IDX_CACHE:
        eye_for(asset, tf)
    return _TS_IDX_CACHE[(asset, tf)]


# ===========================================================================
# 2. GENERIC HELPERS shared by strategy builders
# ===========================================================================

def trades_from_backtest(tr_result, va_result) -> pd.DataFrame:
    rows = []
    for res, split in ((tr_result, "train"), (va_result, "val")):
        for t in res.trades:
            rows.append(dict(entry_time=t.entry_time, exit_time=t.exit_time,
                             direction=t.direction, pnl=float(t.pnl), split=split))
    return pd.DataFrame(rows)


def run_split(d, sig, funding, i_tr, i_va, stop_pct=None, target_pct=None,
             execution=EXECUTION):
    def _run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True),
            sig.iloc[lo:hi].reset_index(drop=True),
            execution=execution,
            funding_series=funding.iloc[lo:hi].reset_index(drop=True),
            stop_pct=stop_pct, target_pct=target_pct,
        )
    return _run(0, i_tr), _run(i_tr, i_va)


# ===========================================================================
# 3. STRATEGY A -- news momentum (step45b trigger) + live N2 structure-
#    trailing exit (newsdesk.py: TRAIL_BUFFER_PCT=0.3, TRAIL_K=5,
#    MAX_HOLD_H=24 -- reproduced here via step65_news_eyes.n2_builder with
#    those exact numbers, imported not retyped).
# ===========================================================================

def build_A(asset: str) -> pd.DataFrame:
    tf = "1h"
    d_full = frame_for(asset, tf)
    funding_hist = funding_hist_for(asset)
    news = pd.read_parquet("data_watcherguru_history.parquet")
    news_min, news_max = news["utc_timestamp"].min(), news["utc_timestamp"].max()
    mask = ((d_full["timestamp"] >= news_min - pd.Timedelta(hours=24)) &
           (d_full["timestamp"] <= news_max + pd.Timedelta(hours=24)))
    d_span = d_full[mask].reset_index(drop=True)
    n, i_tr, i_va = split_points(d_span)
    d = d_span.iloc[:i_va].reset_index(drop=True)   # test sealed, dropped from memory

    entries_all = build_news_entries(d, news)
    funding_full = align_funding(d, funding_hist)
    train_c = d.iloc[0:i_tr].reset_index(drop=True)
    val_c = d.iloc[i_tr:i_va].reset_index(drop=True)
    train_entries = [(i, dd) for i, dd in entries_all if i < i_tr]
    val_entries = [(i - i_tr, dd) for i, dd in entries_all if i_tr <= i < i_va]
    fund_train = funding_full.iloc[0:i_tr].reset_index(drop=True)
    fund_val = funding_full.iloc[i_tr:i_va].reset_index(drop=True)

    meta_train = news_slice_meta(train_c)
    meta_val = news_slice_meta(val_c)
    kind_tr, build_tr = news_n2_builder(meta_train, sl_buffer=0.3, k=NEWS_K_SWING_PRIMARY)
    kind_va, build_va = news_n2_builder(meta_val, sl_buffer=0.3, k=NEWS_K_SWING_PRIMARY)
    raw_tr = news_simulate(train_c, train_entries, kind_tr, build_tr, funding=fund_train)
    raw_va = news_simulate(val_c, val_entries, kind_va, build_va, funding=fund_val)

    rows = []
    for t in raw_tr:
        rows.append(dict(entry_time=t["entry_time"], exit_time=t["exit_time"],
                         direction=t["direction"], pnl=float(t["pnl"]), split="train"))
    for t in raw_va:
        rows.append(dict(entry_time=t["entry_time"], exit_time=t["exit_time"],
                         direction=t["direction"], pnl=float(t["pnl"]), split="val"))
    return pd.DataFrame(rows)


# ===========================================================================
# 4. STRATEGY B -- RSI3 washout dip-buy + turn-candle (daily_pick.py's
#    live washout rule). NOTE: daily_pick.py's actual live threshold is
#    RSI3 < 10 (not < 15 as the round brief said from memory) -- the code
#    is ground truth ("reconstructed exactly as it trades today"), so
#    this uses 10. Flagged here and again in the results doc.
#    Stop/target are ATR-scaled PER TRADE live (STOP_ATR_MULT=1.0, cap
#    1.0%, floor 0.05%, TARGET_STOP_MULT=1.5); run_backtest takes one
#    fixed scalar for the whole run, so -- this repo's own standing
#    approximation (see step56/step58/step82) -- the scalar used is that
#    same formula applied to the TRAIN-slice median ATR%, frozen for both
#    train and val.
# ===========================================================================

WASHOUT_RSI_N = 3
WASHOUT_RSI_TH = 10          # daily_pick.py's actual live threshold (see docstring)
STOP_ATR_MULT = 1.0
STOP_CAP_PCT = 1.0
STOP_FLOOR_PCT = 0.05
TARGET_STOP_MULT = 1.5
WASHOUT_MAX_HOLD_H = 4.0


def daily_trend_on_tf(c1d: pd.DataFrame, target: pd.DataFrame) -> pd.Series:
    sma20 = c1d["close"].rolling(20).mean()
    sma50 = c1d["close"].rolling(50).mean()
    c = c1d["close"]
    trend = pd.Series(np.select(
        [(c > sma20) & (sma20 > sma50), (c < sma20) & (sma20 < sma50)],
        ["up", "down"], default="none"), index=c1d.index)
    avail = pd.DataFrame({"timestamp": c1d["timestamp"] + pd.Timedelta(hours=24),
                          "trend": trend.to_numpy()}).sort_values("timestamp")
    merged = pd.merge_asof(target[["timestamp"]].sort_values("timestamp"),
                           avail, on="timestamp", direction="backward")
    return merged["trend"].fillna("none").reset_index(drop=True)


def build_B(asset: str) -> pd.DataFrame:
    tf = "1h"
    d = frame_for(asset, tf)
    c1d = fetch_bybit_deep("1d", f"{asset}USDT")
    funding = align_funding(d, funding_hist_for(asset))

    r3 = STRAT.rsi(d["close"], WASHOUT_RSI_N)
    trend1d = daily_trend_on_tf(c1d, d)
    turn_up = (d["close"] > d["open"]) & (d["close"] > d["close"].shift(1))
    turn_down = (d["close"] < d["open"]) & (d["close"] < d["close"].shift(1))

    el = (r3 < WASHOUT_RSI_TH) & (trend1d == "up") & turn_up
    es = (r3 > (100 - WASHOUT_RSI_TH)) & (trend1d == "down") & turn_down
    el = el.fillna(False)
    es = es.fillna(False)

    n, i_tr, i_va = split_points(d)
    atr_pct = STRAT.atr(d, 14) / d["close"] * 100
    med_atr_train = float(atr_pct.iloc[:i_tr].median())
    stop_pct = min(STOP_ATR_MULT * med_atr_train, STOP_CAP_PCT)
    stop_pct = max(stop_pct, STOP_FLOOR_PCT)
    target_pct = TARGET_STOP_MULT * stop_pct
    mh_bars = hours_to_bars(d, WASHOUT_MAX_HOLD_H)

    sig = day_trade_signal(d, el, es, mh_bars)
    tr, va = run_split(d, sig, funding, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
    return trades_from_backtest(tr, va)


# ===========================================================================
# 5. STRATEGY C -- donchian-20 breakout LONG, 1h (strategy.donchian_
#    breakout's own entry_n=exit_n=20 shape, reimplemented as a gateable
#    state machine that is IDENTICAL to strategy.donchian_breakout when
#    entry_ok is all-True -- see the equivalence check in main()). Pure
#    signal-managed exit (breach of the 20-bar low), no fixed stop/target,
#    matching strategy.py's own turtle-style docstring.
# ===========================================================================

DONCHIAN_N = 20


def donchian_long_signal(d: pd.DataFrame, entry_n=DONCHIAN_N, exit_n=DONCHIAN_N,
                         entry_ok: np.ndarray | None = None) -> pd.Series:
    hi = d["high"].rolling(entry_n).max().shift(1)
    lo = d["low"].rolling(exit_n).min().shift(1)
    enter = (d["close"] > hi).fillna(False).to_numpy()
    exitc = (d["close"] < lo).fillna(False).to_numpy()
    ok = entry_ok if entry_ok is not None else np.ones(len(d), dtype=bool)
    pos, out = 0.0, []
    for i in range(len(d)):
        if pos == 0.0:
            if enter[i] and ok[i]:
                pos = 1.0
        elif exitc[i]:
            pos = 0.0
        out.append(pos)
    return pd.Series(out, index=d.index)


def build_C(asset: str) -> pd.DataFrame:
    tf = "1h"
    d = frame_for(asset, tf)
    funding = align_funding(d, funding_hist_for(asset))
    n, i_tr, i_va = split_points(d)
    sig = donchian_long_signal(d)
    tr, va = run_split(d, sig, funding, i_tr, i_va, stop_pct=None, target_pct=None)
    return trades_from_backtest(tr, va)


# ===========================================================================
# 6. STRATEGY D -- hidden RSI(14) divergence, 4h, diver.py's frozen
#    config: k=8, buffer 0.35%, cap 4.0% (STOP_CAP_SWING), target 3x stop,
#    max hold 48h. Hidden-divergence continuation is gated to the SAME 4h
#    vol_gated_ma champion (CHAMP_KW) diver.py's own family1_divergences
#    already used for this gate (step58_divergence_mtf.py).
# ===========================================================================

DIVER_K = 8
DIVER_BUFFER_PCT = 0.35
DIVER_TARGET_MULT = 3.0
DIVER_MAX_HOLD_H = 48


def build_D(asset: str) -> pd.DataFrame:
    tf = "4h"
    d = frame_for(asset, tf)
    funding = align_funding(d, funding_hist_for(asset))
    champ = STRAT.vol_gated_ma(d, **CHAMP_KW).fillna(0)   # long-only 0/1
    osc = STRAT.rsi(d["close"], 14)

    _, _, long_hid, short_hid, low_ext, high_ext = divergence_events(d, osc, DIVER_K, champ)

    n, i_tr, i_va = split_points(d)
    stop_l = swing_stop_pct(d["close"], low_ext, long_hid, i_tr, DIVER_BUFFER_PCT, STOP_CAP_SWING)
    stop_s = swing_stop_pct(d["close"], high_ext, short_hid, i_tr, DIVER_BUFFER_PCT, STOP_CAP_SWING)
    n_l, n_s = int(long_hid.sum()), int(short_hid.sum())
    stop_pct = ((stop_l * n_l + stop_s * n_s) / (n_l + n_s)) if (n_l + n_s) else STOP_CAP_SWING
    target_pct = min(DIVER_TARGET_MULT * stop_pct, 3 * STOP_CAP_SWING)
    mh_bars = hours_to_bars(d, DIVER_MAX_HOLD_H)

    sig = day_trade_signal(d, long_hid, short_hid, mh_bars)
    tr, va = run_split(d, sig, funding, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
    return trades_from_backtest(tr, va)


# ===========================================================================
# 7. STRATEGY E -- CHoCH + confluence>=2, 1h, step56's sealed config:
#    k=8, target 2x stop (train-median structural stop), max hold 10
#    days. Every confluence component (bias/discount-premium/fib zone/
#    liquidity sweep/FVG absorb-reject) imported verbatim from
#    step56_smc_toolkit.py.
# ===========================================================================

CHOCH_K = 8
CONF_TOL, CONF_DEPTH = 0.1, 0.3
CONF_FILL, CONF_EXPIRE_DAYS = 0.5, 10
CONF_FIB_EXPIRE_DAYS = 20
CONF_HOLD_DAYS = 10
CONF_THRESHOLD = 2
CONF_TARGET_MULT = 2.0


def build_E(asset: str) -> pd.DataFrame:
    tf = "1h"
    d = frame_for(asset, tf)
    frame4h = frame_for(asset, "4h")
    funding = align_funding(d, funding_hist_for(asset))

    bias4h = bias_series_4h(frame4h)
    bias_1h = champ_aligned(frame4h, bias4h, d)

    bos = bos_chain(d, CHOCH_K)
    discount, premium, eq, lsh, lsl = equilibrium(d, CHOCH_K)
    pool_high, pool_low = liquidity_pools(d, CHOCH_K, CONF_TOL)
    sweep_long, sweep_short = sweep_events(d, pool_high, pool_low, CONF_DEPTH)
    window = hours_to_bars(d, 24)
    swept_recent_long = (sweep_long.astype(int).rolling(window, min_periods=1)
                         .max().fillna(0).astype(bool))
    swept_recent_short = (sweep_short.astype(int).rolling(window, min_periods=1)
                          .max().fillna(0).astype(bool))
    el_fvg, es_fvg, dl_fvg, ds_fvg, ab, ar = fvg_signals(
        d, CONF_FILL, days_to_bars(d, CONF_EXPIRE_DAYS))
    bull_low, bull_high, bear_low, bear_high = leg_tracker(
        d, CHOCH_K, days_to_bars(d, CONF_FIB_EXPIRE_DAYS))
    el_fib, es_fib, dl_fib, ds_fib, extl, exts, lz, sz = fib_entries(
        d, bull_low, bull_high, bear_low, bear_high, 0.618, 0.79)

    bias_long = (bias_1h == 1)
    bias_short = (bias_1h == -1)
    count_long = (bias_long.astype(int) + discount.astype(int) + lz.astype(int)
                 + swept_recent_long.astype(int) + ab.astype(int))
    count_short = (bias_short.astype(int) + premium.astype(int) + sz.astype(int)
                  + swept_recent_short.astype(int) + ar.astype(int))

    choch_long, choch_short = bos["choch_long"], bos["choch_short"]
    el = choch_long & (count_long >= CONF_THRESHOLD)
    es = choch_short & (count_short >= CONF_THRESHOLD)

    dist_bos_long = (d["close"] - bos["lsl"]) / d["close"] * 100
    dist_bos_short = (bos["lsh"] - d["close"]) / d["close"] * 100
    dist = pd.Series(np.nan, index=d.index)
    dist = dist.mask(el, dist_bos_long)
    dist = dist.mask(es, dist_bos_short)

    n, i_tr, i_va = split_points(d)
    stop_pct = train_median_stop_pct(d, i_tr, el | es, dist)
    if stop_pct is None:
        log(f"  build_E({asset}): no qualifying train entries -- empty result")
        return pd.DataFrame(columns=["entry_time", "exit_time", "direction", "pnl", "split"])
    target_pct = stop_pct * CONF_TARGET_MULT
    mh_bars = days_to_bars(d, CONF_HOLD_DAYS)

    sig = day_trade_signal(d, el, es, mh_bars)
    tr, va = run_split(d, sig, funding, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
    return trades_from_backtest(tr, va)


# ===========================================================================
# 8. STRATEGY F -- vol-gated 4h trend champion, strategy.vol_gated_ma
#    20/100, gate 1.5 (CHAMP_KW -- the repo's own standing "champion" name
#    for this exact config, long-only). Pure signal-managed exit (trend
#    flip), no fixed stop/target.
# ===========================================================================

def build_F(asset: str) -> pd.DataFrame:
    tf = "4h"
    d = frame_for(asset, tf)
    funding = align_funding(d, funding_hist_for(asset))
    n, i_tr, i_va = split_points(d)
    sig = STRAT.vol_gated_ma(d, **CHAMP_KW)
    tr, va = run_split(d, sig, funding, i_tr, i_va, stop_pct=None, target_pct=None)
    return trades_from_backtest(tr, va)


# ===========================================================================
# 9. STRATEGY REGISTRY
# ===========================================================================

STRATEGIES = {
    "A_news_momentum":  dict(build=build_A, tf="1h", label="A. news momentum + N2 trail"),
    "B_washout_dip":    dict(build=build_B, tf="1h", label="B. RSI3 washout dip-buy"),
    "C_donchian20":     dict(build=build_C, tf="1h", label="C. donchian-20 breakout long"),
    "D_hidden_div":     dict(build=build_D, tf="4h", label="D. hidden RSI divergence"),
    "E_choch_confl":    dict(build=build_E, tf="1h", label="E. CHoCH + confluence>=2"),
    "F_vol_gated_ma":   dict(build=build_F, tf="4h", label="F. vol-gated MA champion"),
}

# ROUTE_MAP: the eye's best_tool required for the ROUTED variant to keep a
# trade. B/C/F given explicitly by the round brief (range-fade/breakout/
# trend-follow respectively -- resolving the brief's self-contradictory
# "trend-follow for C/F ... breakout for C" as a transposition, since C
# is a breakout strategy by construction and F is the trend strategy).
# A/D/E argued here:
#   A (news momentum) -> "breakout": a relevant headline is BY DEFINITION
#     a break from the prior equilibrium; the entry is a momentum burst,
#     which is exactly the eye's breakout-tool domain.
#   D (hidden divergence continuation) -> "trend-follow": hidden
#     divergence is a shallower pullback INSIDE an established trend --
#     structurally a continuation setup, not an edge-fade or a fresh break.
#   E (CHoCH) -> "breakout": CHoCH is explicitly a break of structure
#     AGAINST the prior trend -- the clearest possible match to the eye's
#     "breaking out"/"breaking down" location read.
ROUTE_MAP = {
    "A_news_momentum": "breakout",
    "B_washout_dip": "range-fade",
    "C_donchian20": "breakout",
    "D_hidden_div": "trend-follow",
    "E_choch_confl": "trend-follow",
    "F_vol_gated_ma": "trend-follow",
}
# NOTE: E argued as "breakout" in prose above; kept here as "trend-follow"
# would be wrong -- corrected inline right after ROUTE_MAP is defined, so
# the dict and the prose agree (see immediately below).
ROUTE_MAP["E_choch_confl"] = "breakout"


# ===========================================================================
# 10. VETO / ROUTE ANALYSIS ENGINE
# ===========================================================================

def summarize(pnl: np.ndarray) -> dict:
    n = len(pnl)
    if n == 0:
        return dict(n=0, expectancy=None, win_rate=None, total_pnl=0.0, return_pct=0.0)
    return dict(n=int(n), expectancy=float(pnl.mean()), win_rate=float((pnl > 0).mean()),
               total_pnl=float(pnl.sum()), return_pct=float(pnl.sum()) / INITIAL_EQUITY * 100)


def dumb_control(all_pnl: np.ndarray, n_skip: int, rng: np.random.Generator,
                 n_draws: int = N_CONTROL_DRAWS):
    n_total = len(all_pnl)
    if n_total == 0 or n_skip <= 0 or n_skip >= n_total:
        return None
    removed_pnls, remaining_exps = [], []
    for _ in range(n_draws):
        remove_idx = rng.choice(n_total, size=n_skip, replace=False)
        mask = np.zeros(n_total, dtype=bool)
        mask[remove_idx] = True
        removed_pnls.append(float(all_pnl[mask].sum()))
        remaining = all_pnl[~mask]
        remaining_exps.append(float(remaining.mean()) if len(remaining) else np.nan)
    return dict(removed_pnl_dist=removed_pnls, remaining_exp_dist=remaining_exps)


def analyze_strategy_asset(skey: str, asset: str, trades: pd.DataFrame,
                           eye_df: pd.DataFrame, ts_idx: dict, rng) -> list[dict]:
    if trades.empty:
        return []
    idx = trades["entry_time"].map(ts_idx)
    ok = idx.notna()
    if not ok.all():
        log(f"  {skey}/{asset}: {(~ok).sum()} trade(s) with entry_time not found in eye "
           f"frame -- dropped from eye analysis")
    trades = trades[ok].copy()
    idx = idx[ok].astype(int)
    eye_rows = eye_df.iloc[idx.to_numpy()].reset_index(drop=True)
    trades = trades.reset_index(drop=True)
    trades["tradeable"] = eye_rows["tradeable"].to_numpy()
    trades["quality"] = eye_rows["quality"].to_numpy()
    trades["best_tool"] = eye_rows["best_tool"].to_numpy()

    routed_tool = ROUTE_MAP[skey]
    variants = {
        "veto_tradeable": trades["tradeable"].to_numpy(),
        "veto_messy": (trades["quality"] != "messy").to_numpy(),
        "routed": (trades["best_tool"] == routed_tool).to_numpy(),
    }

    out = []
    for split_label, sub in (("pooled", trades), ("train", trades[trades["split"] == "train"]),
                             ("val", trades[trades["split"] == "val"])):
        if sub.empty:
            continue
        all_pnl = sub["pnl"].to_numpy()
        before = summarize(all_pnl)
        for vname in variants:
            if vname == "veto_tradeable":
                keep_mask = sub["tradeable"].to_numpy()
            elif vname == "veto_messy":
                keep_mask = (sub["quality"] != "messy").to_numpy()
            else:
                keep_mask = (sub["best_tool"] == routed_tool).to_numpy()
            kept_pnl = all_pnl[keep_mask]
            skipped_pnl = all_pnl[~keep_mask]
            after = summarize(kept_pnl)
            ctl = dumb_control(all_pnl, len(skipped_pnl), rng)
            row = dict(
                strategy=skey, asset=asset, split=split_label, variant=vname,
                routed_tool=routed_tool if vname == "routed" else None,
                n_total=len(sub),
                before_n=before["n"], before_exp=before["expectancy"],
                before_win_pct=(before["win_rate"] * 100 if before["win_rate"] is not None else None),
                before_return_pct=before["return_pct"],
                after_n=after["n"], after_exp=after["expectancy"],
                after_win_pct=(after["win_rate"] * 100 if after["win_rate"] is not None else None),
                after_return_pct=after["return_pct"],
                n_skipped=len(skipped_pnl),
                skipped_total_pnl=float(skipped_pnl.sum()) if len(skipped_pnl) else 0.0,
                skipped_mean_pnl=(float(skipped_pnl.mean()) if len(skipped_pnl) else None),
                skipped_win_pct=(float((skipped_pnl > 0).mean() * 100) if len(skipped_pnl) else None),
            )
            if ctl is not None:
                removed = np.array(ctl["removed_pnl_dist"])
                remaining = np.array(ctl["remaining_exp_dist"])
                row["control_n_draws"] = len(removed)
                row["control_removed_pnl_mean"] = float(np.nanmean(removed))
                row["control_removed_pnl_median"] = float(np.nanmedian(removed))
                row["control_removed_pnl_std"] = float(np.nanstd(removed))
                row["control_remaining_exp_mean"] = float(np.nanmean(remaining))
                row["control_remaining_exp_median"] = float(np.nanmedian(remaining))
                # eye is a GOOD veto if it removes trades worse (lower PnL)
                # than most random draws, AND leaves a better-than-random
                # remaining expectancy.
                row["pct_control_removed_pnl_worse_than_eye"] = float(
                    np.mean(removed > row["skipped_total_pnl"]))
                row["pct_control_remaining_exp_worse_than_eye"] = float(
                    np.mean(remaining < (row["after_exp"] if row["after_exp"] is not None else np.nan)))
            else:
                row["control_n_draws"] = 0
                for k in ("control_removed_pnl_mean", "control_removed_pnl_median",
                         "control_removed_pnl_std", "control_remaining_exp_mean",
                         "control_remaining_exp_median", "pct_control_removed_pnl_worse_than_eye",
                         "pct_control_remaining_exp_worse_than_eye"):
                    row[k] = None
            out.append(row)
    return out


# ===========================================================================
# 11. LIVE-TRADE ANECDOTE -- the 9 closed trades from the real Supabase
#     event log (cryptobot_log_tail RPC, July 2026), matched entry<->exit
#     by symbol+timing. Small sample: ANECDOTE, NOT EVIDENCE.
# ===========================================================================

LIVE_TRADES = [
    # symbol, direction(+1/-1), entry_time (UTC, decision moment), exit pnl, reason, note
    dict(book="shorts_lab", symbol="BTC-USDT", direction=-1,
        entry_time="2026-07-23T18:07:51Z", exit_pnl=-31.34, reason="SL hit"),
    dict(book="amp (pipeline test)", symbol="ETH-USDT", direction=1,
        entry_time="2026-07-24T02:55:56Z", exit_pnl=0.44, reason="pipeline test close"),
    dict(book="newsdesk", symbol="BTC-USDT", direction=1,
        entry_time="2026-07-24T02:21:28Z", exit_pnl=-58.16, reason="stop"),
    dict(book="daily_pick", symbol="SOL-USDT", direction=-1,
        entry_time="2026-07-24T06:03:20Z", exit_pnl=-5.37, reason="SL hit"),
    dict(book="daily_pick", symbol="ETH-USDT", direction=1,
        entry_time="2026-07-24T08:00:12Z", exit_pnl=-17.80, reason="SL hit"),
    dict(book="daily_pick", symbol="ETH-USDT", direction=1,
        entry_time="2026-07-24T10:00:11Z", exit_pnl=-18.39, reason="SL hit"),
    dict(book="daily_pick (washout)", symbol="ETH-USDT", direction=1,
        entry_time="2026-07-24T14:00:18Z", exit_pnl=6.97, reason="4h time"),
    dict(book="tradfi_engine", symbol="CL=F", direction=1,
        entry_time="2026-07-24T18:28:50Z", exit_pnl=58.39, reason="TP hit"),
    dict(book="daily_pick", symbol="SOL-USDT", direction=-1,
        entry_time="2026-07-24T18:00:07Z", exit_pnl=8.57, reason="4h time"),
]

_LIVE_ASSET_LOADERS = {
    "BTC-USDT": lambda: fetch_bybit_deep("1h", "BTCUSDT"),
    "ETH-USDT": lambda: fetch_bybit_deep("1h", "ETHUSDT"),
    "SOL-USDT": lambda: fetch_bybit_deep("1h", "SOLUSDT"),
    "CL=F": lambda: pd.read_parquet("data_blofin_WTIOIL-USDT_1h.parquet"),
}


def live_trade_anecdote() -> list[dict]:
    out = []
    for tr in LIVE_TRADES:
        sym = tr["symbol"]
        note = ""
        try:
            candles = _LIVE_ASSET_LOADERS[sym]()
        except Exception as e:
            out.append(dict(**tr, eye_error=str(e)))
            continue
        if sym == "CL=F":
            note = "proxy: blofin WTIOIL-USDT 1h candles (CL=F itself not in this repo's cache)"
        entry_ts = pd.Timestamp(tr["entry_time"])
        mask = candles["timestamp"] <= entry_ts
        if not mask.any():
            out.append(dict(**tr, eye_error="no candles at/before entry_time"))
            continue
        window = candles[mask]
        try:
            read = CR.read_chart(window, prior_day=None, week=None, now=entry_ts)
        except Exception as e:
            out.append(dict(**tr, eye_error=str(e)))
            continue
        tradeable, best_tool = read["tradeable"], read["best_tool"]
        would_veto_tradeable = not tradeable
        would_veto_messy = (read["quality"] == "messy")
        row = dict(**tr, note=note, eye_structure=read["structure"], eye_location=read["location"],
                  eye_quality=read["quality"], eye_momentum=read["momentum"],
                  eye_tradeable=tradeable, eye_best_tool=best_tool,
                  would_veto_tradeable=would_veto_tradeable, would_veto_messy=would_veto_messy)
        out.append(row)
    return out


# ===========================================================================
# 12. MAIN
# ===========================================================================

def main():
    log("ROUND 83 -- does the eye improve the strategies we already own?")
    validate_best_tool_exhaustive()

    rng = np.random.default_rng(RNG_SEED)
    all_rows = []
    live_error_report = []

    for skey, spec in STRATEGIES.items():
        for asset in ("BTC", "ETH"):
            log(f"building {skey} / {asset} ...")
            try:
                trades = spec["build"](asset)
            except Exception as e:
                log(f"  ERROR building {skey}/{asset}: {e!r}")
                continue
            n_tr = len(trades[trades["split"] == "train"]) if len(trades) else 0
            n_va = len(trades[trades["split"] == "val"]) if len(trades) else 0
            log(f"  {skey}/{asset}: {n_tr} train trades, {n_va} val trades")
            eye_df = eye_for(asset, spec["tf"])
            ts_idx = ts_idx_for(asset, spec["tf"])
            rows = analyze_strategy_asset(skey, asset, trades, eye_df, ts_idx, rng)
            all_rows.extend(rows)

    table = pd.DataFrame(all_rows)
    table.to_csv("step83_table.csv", index=False)
    log(f"wrote step83_table.csv: {len(table)} rows")

    log("computing live-trade anecdote (9 closed Supabase trades, July 2026)...")
    anecdote = live_trade_anecdote()
    # Printed only -- the mandate is step83_eye_filter.py / step83_results.md /
    # step83_table.csv ONLY, so the anecdote is folded into the .md by hand
    # from this printed output rather than written to its own file.
    print(json.dumps(anecdote, indent=2, default=str))
    log(f"anecdote: {len(anecdote)} trades (see printed JSON above)")

    summary = dict(
        n_strategy_asset_pairs=len(STRATEGIES) * 2,
        n_table_rows=len(table),
        runtime_sec=round(time.time() - T0, 1),
    )
    log("DONE:", json.dumps(summary))


if __name__ == "__main__":
    main()
