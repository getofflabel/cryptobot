"""
step63_rehab.py — round 63: GRAVEYARD REHABILITATION.

Run:  python3 step63_rehab.py

THE OWNER'S MANDATE (verbatim spirit): "the known indicators are known for
a reason. You can't say they didn't help — you just haven't found the
RIGHT SCENARIO to use them. Go back in time and find those scenarios."

Seven tools that FAILED unconditional testing in earlier rounds (G1-G7,
see each build_g*() function below for its citation) are retried
CONDITIONALLY, inside market-scenario cells — same entry rule, same costs,
same gauntlet discipline as when they were originally buried; the ONLY new
variable is a scenario gate ANDed onto each tool's ENTRIES (an open
position is still managed by the tool's own exit/stop/target, exactly like
every entry_filter in this repo — strategy.vol_gated_ma's docstring: "the
gate only guards the door").

Research only — no live orders, no commits. Concurrent agent owns
step62_* (the "scenario router" round, same scenario definition) — that
agent's files are never touched or imported. This script REIMPLEMENTS the
classifier from scratch below rather than importing it.

MID-ROUND ADDITION: the shared scenario spec grew a 5th axis (SESSION)
after this script's first pass, relayed via a peer agent working the
concurrent step62 round from the same owner brief. Folded in below —
see axis 5 and the "marginal session-only cut" note in Section-2 of
step63_results.md for how it's reported.

FILES WRITTEN: step63_rehab.py (this file), step63_results.md,
step63_results_raw.csv (the full per-cell grid, same convention as
step43/step50/step56/step58's *_results_raw.csv).

THE 5-AXIS SCENARIO CLASSIFIER (see build_scenario_cells() below)
  1. TREND   — 4h vol_gated_ma(fast=20,slow=100,min_atr_pct=1.5,
               allow_short=True) sign AGREEING with the 4h BOS-chain
               (bos_chain, imported from step56_smc_toolkit, k=8 — the
               same fixed "bias" k step56's own bias_series_4h uses,
               documented here rather than swept, since TREND is a
               classification input, not the primary signal under test)
               -> trending-up / trending-down / ranging. Read onto 1h with
               the standard "visible only at the 4h bar's CLOSE"
               merge_asof pattern (champ_aligned's own convention).
  2. VOL     — ATR%(14) vs its OWN trailing 365-DAY rolling median
               (min_periods = max(30, window//10), the window's own
               distribution EXCLUDES the current bar via .shift(1), same
               convention as step57's bbwidth squeeze) -> quiet (<0.67x),
               normal (0.67x-1.5x), violent (>1.5x, owner-mandated).
               Computed natively on whichever frame a tool trades (every
               tool below trades 1h, so VOL is computed on the 1h frame
               directly — no cross-timeframe alignment needed here).
  3. NEWS-HEAT — a WatcherGuru headline with ai_relevant==True (joined
               data_watcherguru_ai_tags.parquet -> data_watcherguru_
               history.parquet on message_id) within 2h BEFORE (or AT) the
               bar's own timestamp -> hot. WatcherGuru history spans
               2025-06-18 -> 2026-07-23 (~13 months) — VERIFIED
               programmatically below. The news-hot cell is explicitly
               ANDed with that span; no "not-hot" cell is ever scored, so
               pre-span bars are never mislabeled as a real measurement of
               "not hot" — they simply never qualify for the hot cell,
               which is the honest behavior.
  4. CROWD   — funding_bps (align_funding, step11_round6, native 8h
               cadence) -> crowded-long (>=+1.5), crowded-short (<=-0.5),
               neutral (otherwise).
  5. SESSION — pure UTC calendar fact off each bar's own timestamp, no
               lookahead concern whatsoever: asia (00:00-07:00 UTC),
               london (07:00-13:00 UTC), newyork (13:00-21:00 UTC),
               off-hours (21:00-24:00 UTC), with a WEEKEND OVERRIDE (Sat/
               Sun UTC calendar day -> "weekend" regardless of clock hour,
               checked and applied AFTER the four clock buckets so it
               takes priority over them).

CELL ENUMERATION (19 cells per tool-variant, same 19 for every tool —
documented once here, not re-derived per tool, so nothing is cherry-picked
after the fact):
  1-9   TREND(3) x VOL(3)                    — the core grid a trader
                                                 would reason about first
  10-12 CROWD(3) x VOL=violent                — "is crowd positioning
                                                 different in a violent
                                                 regime" — crossed per the
                                                 owner's instruction rather
                                                 than run as a marginal
  13    news-hot, restricted to the 13mo span
  14    ALL-violent (VOL=violent alone, any trend/crowd) — the owner
        explicitly named "violent" as its own hypothesis for G5/G7; this
        pooled cell tests that literally, not crossed with anything else
  15-19 SESSION alone (asia/london/newyork/off-hours/weekend) — added
        mid-round. Each is BOTH a scenario cell in this enumeration AND,
        by construction (unconditional entry rule, all other axes
        pooled/ignored, split only by session), the required "marginal
        session-only cut" for every tool — one computation serves both
        asks, no separate code path needed.

GAUNTLET (THIS ROUND'S NUMBERS — 15/8, not the repo's usual 30/8, per the
owner's explicit instruction that scenario cells are inherently smaller):
  Chronological 60/20/20 per timeframe (split_points, imported, unchanged).
  This script NEVER slices into the final 20% (test) — no sealed test in
  this round, train/val research only.
  Selection ONLY on train: a cell only gets a VAL look if TRAIN expectancy
  is positive there AND train n>=MIN_TRAIN_TRADES=15. Cells failing the
  n>=15 gate are reported as UNRELIABLE and never checked on val — that IS
  the multiplicity firewall (see step63_results.md section 5).
  REHABILITATED requires train_exp>0 AND train_n>=15 AND val_exp>0 AND
  val_n>=8 — both windows positive, both floors cleared.
  Costs: CostModel defaults, execution="maker", real funding via
  align_funding/fetch_funding_history — identical to step41/43/56/57/58.

STOP/TARGET DISCIPLINE: every tool's stop_pct/target_pct is derived ONCE
from its UNCONDITIONAL train-only reconstruction (exactly as step43/56/57/
58 derive their own train-median dynamic stops) and then held FIXED across
the baseline and every scenario cell. Re-deriving the stop per cell would
be introducing a SECOND new variable beyond the scenario gate, which would
break the round's central discipline ("the ONLY new variable is a scenario
gate on top").
"""

import numpy as np
import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step43_daytrade import (
    CHAMP_KW, HARD_STOP_CAP, bar_hours, champ_aligned, day_trade_signal,
    hours_to_bars, momentum_burst_entries, rolling_vwap, split_points,
)
from step55_gold_system import ema_crossover
from step56_smc_toolkit import bos_chain
from step57_price_action import (
    STOP_CAP_PCT, STOP_FLOOR_PCT, daily_sma_aligned, engulfing_signals,
    order_block_engine, pin_bar_signals,
)
from step58_divergence_mtf import (
    STOP_CAP_SWING, adx, divergence_events, donchian_filtered,
    swing_stop_pct,
)
from strategy import atr, rsi, vol_gated_ma

pd.set_option("display.width", 220)

MIN_TRAIN_TRADES = 15     # this round's own floor (looser than the usual 30)
MIN_VAL_TRADES = 8
VOL_QUIET_MULT = 0.67     # < this x trailing 365d median ATR% -> quiet
VOL_VIOLENT_MULT = 1.5    # > this x trailing 365d median ATR% -> violent (owner-mandated)
TREND_BOS_K = 8           # fixed secondary param for the BOS "bias" read (matches step56's BIAS_BOS_K)
FUNDING_LONG_BPS = 1.5    # crowded-long threshold
FUNDING_SHORT_BPS = -0.5  # crowded-short threshold


# ===========================================================================
# DATA LOADING
# ===========================================================================

def load_data():
    print("Loading cached data (no network calls needed)...")
    frames = {tf: fetch_bybit_deep(tf, "BTCUSDT") for tf in ("1h", "4h")}
    daily = fetch_bybit_deep("1d", "BTCUSDT")
    funding_hist = fetch_funding_history("BTCUSDT")
    funding = {tf: align_funding(frames[tf], funding_hist) for tf in ("1h", "4h")}

    meta = {}
    for tf in ("1h", "4h"):
        d = frames[tf]
        n, i_tr, i_va = split_points(d)
        atr_pct = atr(d, 14) / d["close"] * 100
        med_atr = float(atr_pct.iloc[:i_tr].median())
        meta[tf] = {"n": n, "i_tr": i_tr, "i_va": i_va, "med_atr": med_atr}
        print(f"  {tf}: {n} bars, {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
              f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (no sealed test this round) | "
              f"median train ATR%={med_atr:.3f}%")

    ret1 = frames["1h"]["close"].pct_change() * 100
    meta["1h"]["med_baseline"] = float(ret1.iloc[:meta["1h"]["i_tr"]].abs().median())

    daily_sma50 = daily["close"].rolling(50).mean()
    daily_sma_al = {tf: daily_sma_aligned(daily, daily_sma50, frames[tf]) for tf in ("1h", "4h")}

    hist = pd.read_parquet("data_watcherguru_history.parquet")
    tags = pd.read_parquet("data_watcherguru_ai_tags.parquet")
    news = hist.merge(tags, on="message_id", how="inner")
    news_span_start = hist["utc_timestamp"].min()
    news_span_end = hist["utc_timestamp"].max()
    print(f"  WatcherGuru: {len(hist)} posts harvested "
          f"({news_span_start:%Y-%m-%d} -> {news_span_end:%Y-%m-%d}), "
          f"{int(news['ai_relevant'].sum())} ai_relevant=True")

    return dict(frames=frames, funding=funding, daily=daily, meta=meta,
                daily_sma_al=daily_sma_al, news=news,
                news_span_start=news_span_start, news_span_end=news_span_end)


# ===========================================================================
# 4-AXIS SCENARIO CLASSIFIER
# ===========================================================================

def build_trend_axis_1h(frame4h, d1h):
    """4h vol_gated_ma sign AGREEING with the 4h BOS chain -> three states,
    read onto 1h visible only at the 4h bar's CLOSE (open_time + 4h)."""
    champ_ls = vol_gated_ma(frame4h, fast=20, slow=100, min_atr_pct=1.5,
                             allow_short=True).fillna(0)
    chain4h = bos_chain(frame4h, TREND_BOS_K)["chain"]
    trend4h = pd.Series("ranging", index=frame4h.index, dtype=object)
    trend4h[(champ_ls == 1) & (chain4h == 1)] = "trending-up"
    trend4h[(champ_ls == -1) & (chain4h == -1)] = "trending-down"

    avail = pd.DataFrame({
        "timestamp": frame4h["timestamp"] + pd.Timedelta(hours=4),
        "trend": trend4h.to_numpy(),
    }).sort_values("timestamp")
    merged = pd.merge_asof(d1h[["timestamp"]].sort_values("timestamp"), avail,
                            on="timestamp", direction="backward")
    return merged["trend"].fillna("ranging").reset_index(drop=True)


def build_vol_axis(d):
    """ATR% vs its own trailing 365-day rolling median, window excludes the
    current bar (shift(1)), same convention as step57's bbwidth squeeze."""
    atr_pct = atr(d, 14) / d["close"] * 100
    window_bars = max(30, hours_to_bars(d, 365 * 24))
    min_periods = max(30, window_bars // 10)
    trail_med = atr_pct.rolling(window_bars, min_periods=min_periods).median().shift(1)
    ratio = atr_pct / trail_med
    vol = pd.Series(np.nan, index=d.index, dtype=object)
    vol[ratio < VOL_QUIET_MULT] = "quiet"
    vol[(ratio >= VOL_QUIET_MULT) & (ratio <= VOL_VIOLENT_MULT)] = "normal"
    vol[ratio > VOL_VIOLENT_MULT] = "violent"
    return vol


def build_crowd_axis(d, funding_bps):
    crowd = pd.Series("neutral", index=d.index, dtype=object)
    fb = funding_bps.reindex(d.index)
    crowd[fb >= FUNDING_LONG_BPS] = "crowded-long"
    crowd[fb <= FUNDING_SHORT_BPS] = "crowded-short"
    crowd[fb.isna()] = "neutral"
    return crowd


def build_news_axis(d, news, span_start, span_end):
    """hot = an ai_relevant==True WatcherGuru headline landed in the 2h
    window (bar_time - 2h, bar_time] — a headline strictly before or at
    the bar's own timestamp, never a future one. Explicitly restricted to
    the WatcherGuru harvested span; bars outside it can never be 'hot'."""
    hot_ts = news[news["ai_relevant"]]["utc_timestamp"].sort_values()
    hot_df = pd.DataFrame({"timestamp": hot_ts.to_numpy(), "news_time": hot_ts.to_numpy()})
    bars = d[["timestamp"]].reset_index(drop=True)
    merged = pd.merge_asof(bars, hot_df, on="timestamp", direction="backward")
    delta_h = (merged["timestamp"] - merged["news_time"]).dt.total_seconds() / 3600
    hot = ((delta_h >= 0) & (delta_h <= 2.0)).fillna(False)
    in_span = (bars["timestamp"] >= span_start) & (bars["timestamp"] <= span_end)
    return (hot & in_span).reset_index(drop=True)


def build_session_axis(d):
    """5th axis, added mid-round per the owner's mandatory addition to the
    shared 4-axis spec (relayed via a peer agent working the concurrent
    step62 'scenario router' round on the same brief). Pure UTC calendar
    fact — no lookahead concern whatsoever:
      asia      00:00-07:00 UTC
      london    07:00-13:00 UTC
      newyork   13:00-21:00 UTC
      off-hours 21:00-24:00 UTC
      weekend   Sat/Sun UTC calendar day, OVERRIDES the four clock buckets
                regardless of hour (checked first, below)."""
    ts = d["timestamp"]
    hour = ts.dt.hour
    session = pd.Series("off-hours", index=d.index, dtype=object)
    session[(hour >= 0) & (hour < 7)] = "asia"
    session[(hour >= 7) & (hour < 13)] = "london"
    session[(hour >= 13) & (hour < 21)] = "newyork"
    session[(hour >= 21) & (hour < 24)] = "off-hours"
    is_weekend = ts.dt.dayofweek.isin([5, 6])   # Sat=5, Sun=6
    session[is_weekend] = "weekend"
    return session.reset_index(drop=True)


def build_scenario_cells(data):
    frames, funding = data["frames"], data["funding"]
    d1h, frame4h = frames["1h"], frames["4h"]

    trend = build_trend_axis_1h(frame4h, d1h)
    vol = build_vol_axis(d1h)
    crowd = build_crowd_axis(d1h, funding["1h"])
    news_hot = build_news_axis(d1h, data["news"], data["news_span_start"], data["news_span_end"])
    session = build_session_axis(d1h)

    cells = {}
    for t in ("trending-up", "trending-down", "ranging"):
        for v in ("quiet", "normal", "violent"):
            cells[f"{t}×{v}"] = ((trend == t) & (vol == v)).reset_index(drop=True)
    cells["crowded-long×violent"] = ((crowd == "crowded-long") & (vol == "violent")).reset_index(drop=True)
    cells["crowded-short×violent"] = ((crowd == "crowded-short") & (vol == "violent")).reset_index(drop=True)
    cells["neutral-crowd×violent"] = ((crowd == "neutral") & (vol == "violent")).reset_index(drop=True)
    cells["news-hot(13mo-span)"] = news_hot
    cells["ALL-violent(any trend/crowd)"] = (vol == "violent").reset_index(drop=True)
    # SESSION axis (5th axis, added mid-round). SESSION-alone cells serve two
    # purposes at once: (a) they fold SESSION into the existing scenario-cell
    # enumeration per the same non-cherry-picked, documented-enumeration
    # pattern used for the other axes, and (b) each one IS, by construction,
    # the "marginal session-only cut" (unconditional entry rule, all other
    # axes pooled/ignored, split only by session) required as a first-class
    # rehabilitation hypothesis for every tool — same eval_cell/verdict/
    # dumb-control pipeline, no separate code path needed. Tagged with the
    # "session=" prefix so reporting code can pull them out as their own
    # table.
    for s in ("asia", "london", "newyork", "off-hours", "weekend"):
        cells[f"session={s}"] = (session == s).reset_index(drop=True)

    print(f"\nScenario cells built ({len(cells)} total, incl. 5 marginal SESSION-only cuts). "
          f"Bar counts (of {len(d1h)} 1h bars):")
    for name, mask in cells.items():
        print(f"  {name:32s} {int(mask.sum()):6d} bars ({mask.mean()*100:5.1f}%)")

    dumb_mask = (d1h["timestamp"].dt.hour % 2 == 0).reset_index(drop=True)

    return cells, dumb_mask, dict(trend=trend, vol=vol, crowd=crowd, news_hot=news_hot, session=session)


# ===========================================================================
# GENERIC EVAL PLUMBING
# ===========================================================================

def _run(d, sig, f, lo, hi, stop_pct, target_pct):
    return run_backtest(
        d.iloc[lo:hi].reset_index(drop=True), sig.iloc[lo:hi].reset_index(drop=True),
        execution="maker", funding_series=f.iloc[lo:hi].reset_index(drop=True),
        stop_pct=stop_pct, target_pct=target_pct,
    )


def verdict_cell(tr_n, tr_exp, checked_val, va_n, va_exp):
    if tr_n < MIN_TRAIN_TRADES:
        return "UNRELIABLE (train n<15, not attempted on val)"
    if tr_exp <= 0:
        return "FAIL-TRAIN"
    if not checked_val:
        return "UNRELIABLE (train n<15, not attempted on val)"
    if va_n < MIN_VAL_TRADES:
        return "INSUFFICIENT-VAL-SAMPLE"
    if va_exp <= 0:
        return "FAIL-VAL"
    return "REHABILITATED"


def eval_cell(d, f, i_tr, i_va, sig, stop_pct, target_pct):
    tr = _run(d, sig, f, 0, i_tr, stop_pct, target_pct)
    tr_n, tr_exp = len(tr.trades), tr.expectancy
    checked_val = (tr_exp > 0 and tr_n >= MIN_TRAIN_TRADES)
    if checked_val:
        va = _run(d, sig, f, i_tr, i_va, stop_pct, target_pct)
        va_n, va_exp = len(va.trades), va.expectancy
    else:
        va_n, va_exp = 0, float("nan")
    verdict = verdict_cell(tr_n, tr_exp, checked_val, va_n, va_exp)
    return dict(tr_n=tr_n, tr_exp=tr_exp, checked_val=checked_val,
                va_n=va_n, va_exp=va_exp, verdict=verdict)


def eval_daytrade_tool(tool, variant, d, f, i_tr, i_va, el, es, mh_bars,
                       stop_pct, target_pct, cells, dumb_mask):
    rows = []
    base_sig = day_trade_signal(d, el, es, mh_bars)
    b_tr = _run(d, base_sig, f, 0, i_tr, stop_pct, target_pct)
    b_va = _run(d, base_sig, f, i_tr, i_va, stop_pct, target_pct)
    rows.append(dict(tool=tool, variant=variant, cell="UNCONDITIONAL",
                      tr_n=len(b_tr.trades), tr_exp=b_tr.expectancy, checked_val=True,
                      va_n=len(b_va.trades), va_exp=b_va.expectancy, verdict="BASELINE"))
    for cname, cmask in cells.items():
        elc = el & cmask.reindex(d.index).fillna(False)
        esc = es & cmask.reindex(d.index).fillna(False)
        sig = day_trade_signal(d, elc, esc, mh_bars)
        r = eval_cell(d, f, i_tr, i_va, sig, stop_pct, target_pct)
        rows.append(dict(tool=tool, variant=variant, cell=cname, **r))
    # dumb-cell control only computed on demand (after we know which cell rehabilitated)
    return b_tr, b_va, rows


def eval_gated_tool(tool, variant, d, f, i_tr, i_va, build_signal,
                    stop_pct, target_pct, cells):
    rows = []
    base_sig = build_signal(None)
    b_tr = _run(d, base_sig, f, 0, i_tr, stop_pct, target_pct)
    b_va = _run(d, base_sig, f, i_tr, i_va, stop_pct, target_pct)
    rows.append(dict(tool=tool, variant=variant, cell="UNCONDITIONAL",
                      tr_n=len(b_tr.trades), tr_exp=b_tr.expectancy, checked_val=True,
                      va_n=len(b_va.trades), va_exp=b_va.expectancy, verdict="BASELINE"))
    for cname, cmask in cells.items():
        sig = build_signal(cmask)
        r = eval_cell(d, f, i_tr, i_va, sig, stop_pct, target_pct)
        rows.append(dict(tool=tool, variant=variant, cell=cname, **r))
    return b_tr, b_va, rows


def dumb_control(kind, d, f, i_tr, i_va, dumb_mask, stop_pct, target_pct,
                 el=None, es=None, mh_bars=None, build_signal=None):
    """Same tool, same fixed geometry, gated by an arbitrary non-market
    rule (bar hour is even) instead of a scenario cell — the illusion
    check for any REHABILITATED claim."""
    if kind == "daytrade":
        elc = el & dumb_mask.reindex(d.index).fillna(False)
        esc = es & dumb_mask.reindex(d.index).fillna(False)
        sig = day_trade_signal(d, elc, esc, mh_bars)
    else:
        sig = build_signal(dumb_mask)
    return eval_cell(d, f, i_tr, i_va, sig, stop_pct, target_pct)


# ===========================================================================
# G1 — pin bars + engulfing at context levels (step57_price_action.py)
# ===========================================================================

def g1_explore(data):
    """Search step57 family2a/2b's grid (pin bars: wick_mult x context x
    stop_mult x target_mult; engulfing: context x stop_mult x target_mult;
    both timeframes 1h/4h) to find the single best-of-family LONG-ONLY and
    single best-of-family SHORT-ONLY train configs (least-bad train
    expectancy), pooled across BOTH families — reconstructing step57's
    112-config pin-bar/engulfing search (0/112 survivors, see
    step57_results.md section on families 2a/2b) but scored per-direction
    since step57's own family runs pooled both directions in one call."""
    frames, funding, meta = data["frames"], data["funding"], data["meta"]
    daily_sma_al = data["daily_sma_al"]
    candidates = []
    # Restricted to 1h: every other graveyard tool in this round trades 1h,
    # and the scenario classifier built below is 1h-native (single
    # timeframe, one consistent cell universe for the whole round). step57's
    # ORIGINAL family2a/2b grid also swept 4h; that half of the search space
    # is intentionally not carried into this round's scenario-cell testing,
    # stated here plainly as a scoping simplification.
    for tf in ("1h",):
        d, f = frames[tf], funding[tf]
        i_tr = meta[tf]["i_tr"]
        med_atr = meta[tf]["med_atr"]
        mh_bars = hours_to_bars(d, 24)
        zero = pd.Series(False, index=d.index)

        def score_direction(family, ctx, wick_mult, stop_mult, target_mult, el, es):
            stop_pct = min(max(stop_mult * med_atr, STOP_FLOOR_PCT), STOP_CAP_PCT)
            target_pct = target_mult * stop_pct
            for direction, mask in (("long", el), ("short", es)):
                if direction == "long":
                    sig = day_trade_signal(d, mask, zero, mh_bars)
                else:
                    sig = day_trade_signal(d, zero, mask, mh_bars)
                tr = _run(d, sig, f, 0, i_tr, stop_pct, target_pct)
                spec = dict(family=family, tf=tf, wick_mult=wick_mult, ctx=ctx,
                            stop_mult=stop_mult, target_mult=target_mult,
                            stop_pct=stop_pct, target_pct=target_pct,
                            mh_bars=mh_bars, direction=direction)
                candidates.append((tr.expectancy, len(tr.trades), spec))

        for wick_mult in (2, 3):
            for ctx in ("roll20", "roll55", "sma50", "none"):
                el, es = pin_bar_signals(d, wick_mult, ctx, daily_sma_al[tf])
                for stop_mult in (1.0, 1.5):
                    for target_mult in (2.0, 3.0):
                        score_direction("pin-bar", ctx, wick_mult, stop_mult, target_mult, el, es)
        for ctx in ("roll20", "roll55", "sma50", "none"):
            el, es = engulfing_signals(d, ctx, daily_sma_al[tf])
            for stop_mult in (1.0, 1.5):
                for target_mult in (2.0, 3.0):
                    score_direction("engulfing", ctx, None, stop_mult, target_mult, el, es)

    longs = [c for c in candidates if c[2]["direction"] == "long"]
    shorts = [c for c in candidates if c[2]["direction"] == "short"]
    best_long = max(longs, key=lambda c: c[0])
    best_short = max(shorts, key=lambda c: c[0])
    print(f"\nG1 explore: {len(candidates)} (family x tf x ctx x stop x tgt x direction) "
          f"train-only scans.")
    print(f"  best LONG : {best_long[2]} tr_exp=${best_long[0]:+.2f} n={best_long[1]}")
    print(f"  best SHORT: {best_short[2]} tr_exp=${best_short[0]:+.2f} n={best_short[1]}")
    return best_long, best_short, len(candidates)


def g1_rebuild_mask(data, spec):
    d = data["frames"][spec["tf"]]
    daily_sma_al = data["daily_sma_al"][spec["tf"]]
    if spec["family"] == "pin-bar":
        el, es = pin_bar_signals(d, spec["wick_mult"], spec["ctx"], daily_sma_al)
    else:
        el, es = engulfing_signals(d, spec["ctx"], daily_sma_al)
    return (el if spec["direction"] == "long" else es)


# ===========================================================================
# G4 — EMA 20/50 long-only cross, 1h (fresh unconditional reconstruction)
# ===========================================================================

def ema_gated(d, fast, slow, entry_filter=None):
    """Event-gated EMA cross, long-only: entries need entry_filter's OK;
    an already-open position rides the crossover alone (same 'gate only
    guards the door' contract as strategy.vol_gated_ma's own entry_filter,
    ported here to the EMA-cross primitive since ema_crossover itself is
    level-based, not event-based)."""
    base = ema_crossover(d, fast, slow, allow_short=False)
    warm = base.notna().to_numpy()
    base_v = base.fillna(0).to_numpy()
    if entry_filter is None:
        extra = np.ones(len(d), dtype=bool)
    else:
        extra = entry_filter.reindex(d.index).fillna(False).to_numpy(dtype=bool)
    out, pos = [], 0.0
    for b, w, ok in zip(base_v, warm, extra):
        if not w:
            out.append(float("nan"))
            continue
        if pos == 0.0:
            if b == 1.0 and ok:
                pos = 1.0
        elif b == 0.0:
            pos = 0.0
        out.append(pos)
    return pd.Series(out, index=d.index)


# ===========================================================================
# main
# ===========================================================================

def main():
    data = load_data()
    cells, dumb_mask, axes = build_scenario_cells(data)
    frames, funding, meta = data["frames"], data["funding"], data["meta"]
    d1h, f1h = frames["1h"], funding["1h"]
    i_tr, i_va = meta["1h"]["i_tr"], meta["1h"]["i_va"]
    med_atr = meta["1h"]["med_atr"]
    frame4h = frames["4h"]

    champ4h_long = vol_gated_ma(frame4h, **CHAMP_KW)                 # long-only 0/1
    champ_al_1h = champ_aligned(frame4h, champ4h_long, d1h)

    all_rows = []
    baselines = {}      # tag -> {"b_tr":..,"b_va":..,"desc":..,"dumb_fn": callable()->dict}

    # ---- G1 ----------------------------------------------------------
    print("\n" + "=" * 70 + "\nG1 — pin bars + engulfing (step57_price_action.py)\n" + "=" * 70)
    g1_best_long, g1_best_short, g1_explore_n = g1_explore(data)
    for tag, best in (("G1-LONG", g1_best_long), ("G1-SHORT", g1_best_short)):
        exp, n, spec = best
        if spec["tf"] != "1h":
            raise RuntimeError(f"{tag} winning config landed on {spec['tf']} — scenario cells "
                                "are 1h-native in this script; extend before proceeding.")
        d, f = d1h, f1h
        mask = g1_rebuild_mask(data, spec)
        zero = pd.Series(False, index=d.index)
        el, es = (mask, zero) if spec["direction"] == "long" else (zero, mask)
        desc = (f"{spec['family']} tf={spec['tf']} ctx={spec['ctx']} wick={spec['wick_mult']} "
                f"stop={spec['stop_mult']}xATR tgt={spec['target_mult']}xstop dir={spec['direction']} "
                f"(train-only best-of-family, tr_exp=${exp:+.2f} n={n})")
        b_tr, b_va, rows = eval_daytrade_tool(tag, desc, d, f, i_tr, i_va, el, es,
                                              spec["mh_bars"], spec["stop_pct"],
                                              spec["target_pct"], cells, dumb_mask)
        all_rows += rows
        baselines[tag] = dict(
            b_tr=b_tr, b_va=b_va, desc=desc,
            dumb_fn=lambda el=el, es=es, mh=spec["mh_bars"], sp=spec["stop_pct"], tp=spec["target_pct"]:
                dumb_control("daytrade", d1h, f1h, i_tr, i_va, dumb_mask, sp, tp, el=el, es=es, mh_bars=mh))
        print(f"  {tag} unconditional: train ${b_tr.expectancy:+.2f}/t n={len(b_tr.trades)} | "
              f"val ${b_va.expectancy:+.2f}/t n={len(b_va.trades)} | {desc}")

    # ---- G2 ------------------------------------------------------------
    print("\n" + "=" * 70 + "\nG2 — order blocks, base 50%-touch (step57_price_action.py)\n" + "=" * 70)
    mh_bars_g2 = hours_to_bars(d1h, 48)
    el2, es2, stop2, ev2 = order_block_engine(d1h, i_tr, meta["1h"]["med_baseline"],
                                              mult=2, bars_move=1, touch="50pct",
                                              breaker=False, max_wait_bars=mh_bars_g2)
    target2 = 3.0 * stop2
    b_tr, b_va, rows = eval_daytrade_tool("G2", "base X2x/1bar touch=50pct tgt3xstop hold48h (1h)",
                                          d1h, f1h, i_tr, i_va, el2, es2, mh_bars_g2,
                                          stop2, target2, cells, dumb_mask)
    all_rows += rows
    baselines["G2"] = dict(
        b_tr=b_tr, b_va=b_va, desc="order-block base X2x/1bar touch=50pct tgt3xstop hold48h",
        dumb_fn=lambda: dumb_control("daytrade", d1h, f1h, i_tr, i_va, dumb_mask, stop2, target2,
                                     el=el2, es=es2, mh_bars=mh_bars_g2))
    print(f"  G2 unconditional: train ${b_tr.expectancy:+.2f}/t n={len(b_tr.trades)} | "
          f"val ${b_va.expectancy:+.2f}/t n={len(b_va.trades)} | stop={stop2:.2f}% tgt={target2:.2f}%")

    # ---- G3 ------------------------------------------------------------
    print("\n" + "=" * 70 + "\nG3 — RSI14 k8 REGULAR divergence (step58_divergence_mtf.py)\n" + "=" * 70)
    osc = rsi(d1h["close"], 14)
    long_reg, short_reg, long_hid, short_hid, low_ext, high_ext = divergence_events(
        d1h, osc, 8, champ_al_1h)
    buffer_pct = 0.15
    stop_l = swing_stop_pct(d1h["close"], low_ext, long_reg, i_tr, buffer_pct, STOP_CAP_SWING)
    stop_s = swing_stop_pct(d1h["close"], high_ext, short_reg, i_tr, buffer_pct, STOP_CAP_SWING)
    n_l, n_s = int(long_reg.sum()), int(short_reg.sum())
    stop3 = (stop_l * n_l + stop_s * n_s) / (n_l + n_s) if (n_l + n_s) else STOP_CAP_SWING
    target3 = min(2.0 * stop3, 3 * STOP_CAP_SWING)
    mh_bars_g3 = hours_to_bars(d1h, 48)
    b_tr, b_va, rows = eval_daytrade_tool("G3", "RSI14 k8 regular buf0.15% tgt2x hold48h (1h)",
                                          d1h, f1h, i_tr, i_va, long_reg, short_reg, mh_bars_g3,
                                          stop3, target3, cells, dumb_mask)
    all_rows += rows
    baselines["G3"] = dict(
        b_tr=b_tr, b_va=b_va, desc="RSI14 k8 regular buf0.15% tgt2x hold48h",
        dumb_fn=lambda: dumb_control("daytrade", d1h, f1h, i_tr, i_va, dumb_mask, stop3, target3,
                                     el=long_reg, es=short_reg, mh_bars=mh_bars_g3))
    print(f"  G3 unconditional: train ${b_tr.expectancy:+.2f}/t n={len(b_tr.trades)} | "
          f"val ${b_va.expectancy:+.2f}/t n={len(b_va.trades)} | stop={stop3:.2f}% tgt={target3:.2f}%")

    # ---- G4 ------------------------------------------------------------
    print("\n" + "=" * 70 + "\nG4 — EMA 20/50 long-only, 1h (fresh unconditional baseline)\n" + "=" * 70)
    stop4 = min(1.2 * med_atr, HARD_STOP_CAP)
    target4 = 2.5 * med_atr
    build_g4 = lambda mask: ema_gated(d1h, 20, 50, entry_filter=mask)
    b_tr, b_va, rows = eval_gated_tool("G4", "EMA20/50 long-only stop1.2xATR(cap1.7%) tgt2.5xATR (1h)",
                                       d1h, f1h, i_tr, i_va, build_g4, stop4, target4, cells)
    all_rows += rows
    baselines["G4"] = dict(
        b_tr=b_tr, b_va=b_va, desc="EMA20/50 long-only stop1.2xATR(cap1.7%) tgt2.5xATR",
        dumb_fn=lambda: dumb_control("gated", d1h, f1h, i_tr, i_va, dumb_mask, stop4, target4,
                                     build_signal=build_g4))
    print(f"  G4 unconditional: train ${b_tr.expectancy:+.2f}/t n={len(b_tr.trades)} | "
          f"val ${b_va.expectancy:+.2f}/t n={len(b_va.trades)} | stop={stop4:.2f}% tgt={target4:.2f}%")

    # ---- G5 ------------------------------------------------------------
    print("\n" + "=" * 70 + "\nG5 — momentum burst X1.8% champ-gated (step43_daytrade.py / step43c_test_look.py)\n" + "=" * 70)
    el5, es5 = momentum_burst_entries(d1h, champ_al_1h, 1.8, 1, "champ")
    stop5 = min(1.0 * med_atr, HARD_STOP_CAP)
    target5 = 3.0 * med_atr
    mh_bars_g5 = hours_to_bars(d1h, 24)
    b_tr, b_va, rows = eval_daytrade_tool("G5", "X1.8% champ tgt3xATR hold24h (1h)",
                                          d1h, f1h, i_tr, i_va, el5, es5, mh_bars_g5,
                                          stop5, target5, cells, dumb_mask)
    all_rows += rows
    baselines["G5"] = dict(
        b_tr=b_tr, b_va=b_va, desc="momentum burst X1.8% champ tgt3xATR hold24h",
        dumb_fn=lambda: dumb_control("daytrade", d1h, f1h, i_tr, i_va, dumb_mask, stop5, target5,
                                     el=el5, es=es5, mh_bars=mh_bars_g5))
    print(f"  G5 unconditional: train ${b_tr.expectancy:+.2f}/t n={len(b_tr.trades)} | "
          f"val ${b_va.expectancy:+.2f}/t n={len(b_va.trades)} (train/val SURVIVED per step43_results.md; "
          f"the ONE sealed test look FAILED per RESEARCH_LOG round 43 — that verdict stands, unrevisited here)")

    # ---- G6 (two configs: k=1.5xATR, k=2.5xATR) ------------------------
    print("\n" + "=" * 70 + "\nG6 — VWAP fade, both-directions champ-gated (step43_daytrade.py)\n" + "=" * 70)
    a1h = atr(d1h, 14)
    vwap1h = rolling_vwap(d1h, 24)
    mh_bars_g6 = hours_to_bars(d1h, 24)
    stop6 = min(1.2 * med_atr, HARD_STOP_CAP)
    for k in (1.5, 2.5):
        dist_long = d1h["close"] < (vwap1h - k * a1h)
        dist_short = d1h["close"] > (vwap1h + k * a1h)
        el6 = (dist_long & (champ_al_1h == 1)).fillna(False)
        es6 = (dist_short & (champ_al_1h == 0)).fillna(False)
        vwap_dist_pct = ((vwap1h - d1h["close"]).abs() / d1h["close"] * 100)
        entry_dists = pd.concat([
            vwap_dist_pct.iloc[:i_tr][el6.iloc[:i_tr]],
            vwap_dist_pct.iloc[:i_tr][es6.iloc[:i_tr]],
        ])
        target6 = min(float(entry_dists.median()), 3.0) if len(entry_dists) else 3.0
        tag = f"G6-k{k}"
        b_tr, b_va, rows = eval_daytrade_tool(tag, f"k={k}xATR both-directions champ-gated (1h)",
                                              d1h, f1h, i_tr, i_va, el6, es6, mh_bars_g6,
                                              stop6, target6, cells, dumb_mask)
        all_rows += rows
        baselines[tag] = dict(
            b_tr=b_tr, b_va=b_va, desc=f"VWAP fade k={k}xATR both-directions champ-gated",
            dumb_fn=lambda el6=el6, es6=es6, k=k, tp=target6:
                dumb_control("daytrade", d1h, f1h, i_tr, i_va, dumb_mask, stop6, tp,
                             el=el6, es=es6, mh_bars=mh_bars_g6))
        print(f"  {tag} unconditional: train ${b_tr.expectancy:+.2f}/t n={len(b_tr.trades)} | "
              f"val ${b_va.expectancy:+.2f}/t n={len(b_va.trades)} | tgt={target6:.2f}%")

    # ---- G7 (two donchian bases: exit_n=10, exit_n=20) ------------------
    print("\n" + "=" * 70 + "\nG7 — ADX>=25 on donchian20/{10,20} (step58_divergence_mtf.py)\n" + "=" * 70)
    adx_mask = adx(d1h, 14) >= 25
    for exit_n in (10, 20):
        def build_g7(mask, exit_n=exit_n):
            ef = adx_mask if mask is None else (adx_mask & mask.reindex(d1h.index).fillna(False))
            return donchian_filtered(d1h, entry_n=20, exit_n=exit_n, entry_filter=ef)
        tag = f"G7-donchian{exit_n}"
        b_tr, b_va, rows = eval_gated_tool(tag, f"donchian20/{exit_n} + ADX>=25 (1h)",
                                           d1h, f1h, i_tr, i_va, build_g7, None, None, cells)
        all_rows += rows
        baselines[tag] = dict(
            b_tr=b_tr, b_va=b_va, desc=f"donchian20/{exit_n} + ADX>=25",
            dumb_fn=lambda build_g7=build_g7: dumb_control(
                "gated", d1h, f1h, i_tr, i_va, dumb_mask, None, None, build_signal=build_g7))
        print(f"  {tag} unconditional: train ${b_tr.expectancy:+.2f}/t n={len(b_tr.trades)} | "
              f"val ${b_va.expectancy:+.2f}/t n={len(b_va.trades)}")

    # ---------------------------------------------------------------
    # assemble, write raw CSV, dumb-cell control on every REHABILITATED cell
    # ---------------------------------------------------------------
    df = pd.DataFrame(all_rows)
    df.to_csv("step63_results_raw.csv", index=False)
    print(f"\n{len(df)} rows (incl. {len(baselines)} baselines) written to step63_results_raw.csv")

    rehab_rows = df[df["verdict"] == "REHABILITATED"]
    print(f"\nREHABILITATED rows: {len(rehab_rows)}")
    dumb_results = []
    for _, r in rehab_rows.iterrows():
        tag = r["tool"]
        dr = baselines[tag]["dumb_fn"]()
        dumb_results.append(dict(tool=tag, cell=r["cell"], real_tr_exp=r["tr_exp"], real_tr_n=r["tr_n"],
                                  real_va_exp=r["va_exp"], real_va_n=r["va_n"],
                                  dumb_tr_exp=dr["tr_exp"], dumb_tr_n=dr["tr_n"],
                                  dumb_va_exp=dr["va_exp"], dumb_va_n=dr["va_n"], dumb_verdict=dr["verdict"]))
        va_str = f"${dr['va_exp']:+.2f}/t n={dr['va_n']}" if dr["checked_val"] else "not attempted"
        print(f"  dumb-cell control for {tag} / {r['cell']}: "
              f"real train ${r['tr_exp']:+.2f}/t n={r['tr_n']} val ${r['va_exp']:+.2f}/t n={r['va_n']} | "
              f"dumb(hour%2==0) train ${dr['tr_exp']:+.2f}/t n={dr['tr_n']} val {va_str} | "
              f"dumb verdict={dr['verdict']}")

    print("\nFull verdict counts across all cell evaluations (excl. baselines):")
    print(df[df["verdict"] != "BASELINE"]["verdict"].value_counts().to_string())

    n_variants = len(baselines)
    n_cells_each = len(cells)
    print(f"\n{n_variants} tool-variants x {n_cells_each} cells = "
          f"{n_variants * n_cells_each} scenario-cell evaluations "
          f"(+ {g1_explore_n} G1 pre-search train-only scans, config selection only, "
          f"not itself part of the scenario-cell multiplicity)")

    return df, baselines, dumb_results, cells, axes, data


if __name__ == "__main__":
    main()
