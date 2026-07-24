"""
step66_scenario_mind.py — round 66: THE SCENARIO MIND.

Run:  python3 step66_scenario_mind.py

THE OWNER'S MANDATE (verbatim spirit, relayed via the Fable-5 lead): "a real
trader reads the scenario first, then picks the tool" (the TJR vision).
Every prior round asked "does tool X work, unconditionally or in ONE
hand-picked scenario cell." This round asks the compound question no prior
round asked: learn from HISTORY which validated tool belongs to which
market situation, then TEST whether a router that only fires each tool in
its own historically-positive scenario beats (a) running every tool always,
(b) any single tool alone, and (c) a fake "router" that gates on arbitrary
non-market cells instead of real ones. Research only — no live orders, no
commits. Touches only this file, step66_results.md, step66_results_raw.csv.

======================================================================
THE 5-AXIS SCENARIO CLASSIFIER — REUSED VERBATIM FROM step63_rehab.py
======================================================================
step63_rehab.py already built and documented a 5-axis classifier for this
exact owner brief (round 63's "graveyard rehabilitation" round, concurrent
with round 62's now-superseded router pass). Per this round's own
instruction, the axis DEFINITIONS are reused verbatim for comparability —
imported directly from step63_rehab (a pure function-definition module, safe
to import) rather than re-typed and risking silent drift:
  TREND   — build_trend_axis_1h: 4h vol_gated_ma(20/100, gate1.5,
            allow_short=True) sign AGREEING with the 4h BOS-chain (bos_chain,
            k=8) -> trending-up / trending-down / ranging. 4h-computed,
            visible on 1h only from the 4h bar's own CLOSE (merge_asof
            backward on open_time+4h) — step63's exact mechanism.
  VOL     — build_vol_axis: ATR%(14) vs its OWN trailing 365-day rolling
            median (shift(1)'d, min_periods=max(30,window//10)) -> quiet
            (<0.67x) / normal / violent (>1.5x).
  NEWS-HEAT — build_news_axis: an ai_relevant WatcherGuru headline within 2h
            before-or-at the bar's own timestamp, restricted to the ~13mo
            harvested span (bars outside the span never qualify as "hot" —
            they are excluded from the news-axis cell, never mislabeled
            "not hot").
  CROWD   — build_crowd_axis: funding_bps >= +1.5bp crowded-long,
            <= -0.5bp crowded-short, else neutral.
  SESSION — build_session_axis: pure UTC calendar fact (asia 00-07 / london
            07-13 / newyork 13-21 / off-hours 21-24 UTC), weekend override.

NATIVE-RESOLUTION EXTENSION FOR 4h-TRADING TOOLS (this round's own addition,
stated plainly — step63 never needed it because every one of its tools
traded 1h): two of this round's eight tools (T2 hidden-RSI-divergence, T8
BB-width-squeeze) trade on 4h candles natively. VOL / CROWD / NEWS / SESSION
are already resolution-agnostic functions (they take a candle frame `d` and
compute purely off IT — step63 states this explicitly: "computed natively on
whichever frame a tool trades"), so calling them directly on the 4h frame
is calling them exactly as designed, no change needed. TREND is the one
axis the classifier itself defines as cross-timeframe (a 4h read, by
construction) — for a 4h-native tool there's no coarser frame to borrow
from, so TREND is read directly off the SAME 4h frame the tool trades,
using the identical champ-sign + BOS-chain-agreement formula, with NO extra
shift beyond what champ/bos_chain already build in (this matches how
step56's bias_series_4h is used raw wherever the trading itself happens at
4h, e.g. step56 family1/2). This is the ONLY axis with two code paths in
this file (build_trend_axis_1h for 1h tools, build_trend_axis_native for 4h
tools) — everything else is one function shared by both resolutions.

======================================================================
CELL ENUMERATION (73 cells per tool, fixed and documented ONCE here — not
re-derived per tool, so nothing is cherry-picked after the fact)
======================================================================
  1-9   TREND(3) x VOL(3)                     — the core grid (step63's own)
  10-54 TREND(3) x VOL(3) x SESSION(5) = 45    — the flagship "read the
                                                  scenario" grid: this is
                                                  what produces rows like
                                                  "trending-up + quiet +
                                                  london"
  55-57 CROWD(3) x VOL=violent                 — is crowd positioning
                                                  different in a violent
                                                  regime (step63's own)
  58    news-hot (13mo span only)
  59    ALL-violent (VOL=violent alone, any trend/crowd/session)
  60-64 SESSION alone (5)                      — marginal single-axis cut
  65-67 CROWD alone (3)                        — marginal single-axis cut
  68-70 VOL alone (3)                          — marginal single-axis cut
  71-73 TREND alone (3)                        — marginal single-axis cut

Every cell is tagged with the axis (or axes) it references (axes_of), used
both to report which axis "carries" a finding and to build the marginal-
axis-removed router variants (see ROUTER section).

CELL FLOOR (same as step63, this round's own explicit instruction): a cell
is only ever LOOKED AT on val if train n>=MIN_TRAIN_TRADES=15 and train
expectancy>0; cells failing that gate are UNRELIABLE and never checked on
val — the multiplicity firewall. MIN_VAL_TRADES=8 for calling a val result
meaningful.

======================================================================
THE EIGHT TOOLS — reconstructed EXACTLY from each one's own source round
(same entry logic, same stop/target/max_hold, derived ONCE from that round's
own train-only reconstruction and then held FIXED across the baseline and
every scenario cell — the ONLY new variable this round adds is the
scenario gate ANDed onto each tool's entries, identical discipline to
step63's own "the gate only guards the door")
======================================================================
T1 NEWS-MOMENTUM (step45b / step65) — a relevant WatcherGuru headline
   (classify_headline) -> align_events' no-lookahead floor/trading-bar
   mapping -> the first FULL 1h bar after the event -> enter at THAT bar's
   own close, direction = that bar's own close-vs-open sign (the ONLY
   step45b direction variant that ever passed sealed). TP+2.4%/SL-1.2%/24h.
   Universe: the WatcherGuru-harvested 13mo BTC 1h span only (news_min-24h
   -> news_max+24h), its OWN chronological 60/20/20 split — matches
   step65's "NEWS-SPAN SPLIT" convention exactly.
T2 HIDDEN-RSI-DIVERGENCE 4h (step58) — RSI(14) hidden bullish/bearish
   divergence at k=5 confirmed swings, gated to the 4h champion's own
   trend (continuation flavor), buffer 0.15% past the swing extreme,
   target=3x stop (capped 3x STOP_CAP_SWING), max_hold 96h. Best-of-toolkit
   pick per step58_results.md's own ranking (#1: "RSI14 k5 hidden
   buf0.15% tgt3x hold96h, 4h").
T3 CHoCH+CONFLUENCE>=2 1h (step56) — the first BOS event against the
   prevailing 1h structure (k=8), gated to >=2 of 5 agreeing conditions
   (4h bias, discount/premium, 0.618-0.79 fib zone, a same-direction pool
   sweep in the last 24h, a same-direction unfilled FVG). target=2x the
   train-median stop distance to the opposite structure point. Exactly
   step56's own "CHoCH, k=8, target=2x, 1h" — the round's own clean-
   monotonic confluence winner (train +$15.45/t x52, val +$72.51/t x24).
T4 DONCHIAN20 1h BREAKOUT — close > prior 20-bar high, long only. No prior
   round ever deployed this WITH an exit of its own; reconstructed per
   step59_exit_science.py's own "E4 constructed X0" baseline (its own
   stated fair-fixed-% construction for exactly this reason): stop = 1.5x
   the train-only median ATR14%, target = 2R, max_hold = 240 1h-bars (10d).
T5 RSI3<15-IN-UPTREND DIP ("STRIKES", step59/tactical.py) — 4h champion
   (vol_gated_ma 20/100, gate1.5) long AND the last-closed 1h bar's
   RSI(3) < 15, long only. INCUMBENT exit TP+4.5%/SL-1.5%/48h (the live
   book's own bracket, per step59's E1).
T6 FORENSIC-SHORT (step41 family 4, widened) — funding > 1.5bp (euphoric)
   AND a 4h pop > 1.5% AND ATR% > 1.2% (live volatility), short only.
   stop 1.69% / target 5.07% ("established forensic geometry", step41's
   own phrase) / 48h hold. The f>1.5bp widening (step41's own SURVIVOR:
   train +$24.57/t x55, val +$193.25/t x8).
T7 VOLUME-SHOCK CONTINUATION (step50 family C) — volume >= 6x its trailing
   48-bar median AND |return| >= 2x its trailing 48-bar median |return|,
   traded WITH the move (falsification-arm control that turned out to be
   the round's strongest single config). stop=1.5xATR(train-median,capped
   1.7%), target=3x stop, max_hold 24h, 1h. step50's own #1 sealed-look
   pick.
T8 BB-WIDTH-SQUEEZE EXPANSION 4h (step57 family 3b, watch-list survivor) —
   Bollinger-bandwidth in its own bottom-20th trailing-365d percentile
   (squeeze), price closes outside the bands (expansion), ungated,
   4h. stop = 1.0x train-median ATR% (clamped [0.30,3.0]), NO fixed
   target ("trailing" in step57's own family sense = ride to stop or the
   48h cap only), max_hold 48h. step57's own #1-ranked candidate (train
   +$11.64/t x122, val +$80.02/t x26).

All eight are expressed uniformly as day_trade_signal(enter_long,
enter_short, max_hold_bars) + run_backtest(stop_pct, target_pct,
execution="maker", real funding) — this round's OWN stated engine-
normalization simplification: some of these tools were originally
gauntleted through a different hand-rolled engine (T1/T4/T5 through
step59/step65's own event-driven simulator). Re-expressing every tool
through ONE engine is exactly step63's own precedent (it reconstructed
ALL of ITS graveyard tools, regardless of original engine, through
day_trade_signal+run_backtest) and is required here for apples-to-apples
scenario-cell comparability across all eight.

======================================================================
THE ROUTER
======================================================================
TRAIN-ONLY SELECTION: for each (tool, cell) pair, using the SAME 73-cell
evaluation built for the playbook, a cell is "eligible" for that tool iff
train n>=15 AND train expectancy>0 (identical to the cell floor above —
one gate serves both the playbook and the router, no separate mechanism).
A tool's ROUTED entries = its own unconditional entries ANDed with the
UNION of all its eligible cells' masks (a bar fires the tool if it matches
ANY scenario the tool has proven itself in on train — a trader recognizing
one of several valid setups, not a strict single-cell partition).
VAL EXECUTION: entries rebuilt with this union mask, day_trade_signal +
run_backtest rerun on VAL ONLY (train's job was selection, not itself a
result).
PORTFOLIO MERGE: each tool's own VAL trades (a list of Trade objects, each
already carrying its own real $-costs from ITS OWN run_backtest call, on
ITS OWN native timeframe/stop/target/funding) are converted to a
timeframe-and-equity-independent PERCENT RETURN (pnl / (units*entry_price)
— exact by construction since size_frac=1.0 means notional==equity-in at
entry) and merged chronologically across all 8 tools into ONE single-slot
portfolio (first trade to START wins the slot; a human trader can only
take one trade at a time — the SAME simplifying assumption step65's own
hand-rolled multi-policy portfolio merge uses, applied here at multi-TOOL
scale). The merged trade sequence is then replayed against ONE shared
$10,000 compounding equity curve — same INITIAL_EQUITY / size_frac=1.0
convention as backtest.py itself, so "tool solo" numbers (which come
directly from that tool's own isolated run_backtest call, same
compounding convention) are directly comparable to the portfolio numbers
with no re-scaling needed.
CONTROLS:
  ALL-TOOLS-ALWAYS-ON ("the rack") — same portfolio merge, but each tool's
    UNCONDITIONAL VAL trades (no scenario filter at all) instead of its
    routed subset.
  DUMB-ROUTER — same mechanism as the real router (union of cell masks ->
    AND into entries -> rerun VAL), but the union is built from a RANDOM
    set of cells (matched COUNT to the real router's eligible-cell count
    for that tool, fixed seed per tool for reproducibility) instead of the
    train-positive ones — "does routing help because it's SMART, or just
    because it's SELECTIVE (fewer trades, less noise)?"
  EACH TOOL SOLO — that tool's own unconditional VAL run_backtest result,
    directly (no merge needed — mathematically identical methodology).

======================================================================
MARGINAL AXIS VALUE
======================================================================
Five more router variants, each built by re-running the SAME train-side
eligibility gate but EXCLUDING every cell that references one axis (e.g.
"router-noSESSION" drops the 45-cell TREND x VOL x SESSION grid and the
5 SESSION-alone cells, keeping everything else) — cheap, since it reuses
the SAME 73-cell train/val numbers already computed for the playbook, no
new backtests beyond the 5 VAL portfolio re-executions. Compared against
the FULL 5-axis router's own portfolio numbers.

DISCIPLINE: costs always on, CostModel defaults, execution="maker", real
funding via align_funding — identical to every prior round. No sealed
test slice exists in this round's data prep (train/val only, per the
mandate) — this is explicitly a research/comparison round, not a
sealed-look round.
"""

import numpy as np
import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import days_to_bars
from step43_daytrade import (
    CHAMP_KW, HARD_STOP_CAP, bar_hours, champ_aligned, day_trade_signal,
    hours_to_bars, split_points,
)
from step45b_news_events import align_events, classify_headline
from step50_volume_absorption import absret_baseline, familyC_entries, volume_baseline
from step56_smc_toolkit import (
    bias_series_4h, bos_chain, equilibrium, fib_entries, fvg_signals,
    leg_tracker, liquidity_pools, sweep_events, train_median_stop_pct,
)
from step57_price_action import bbwidth_signals
from step57_price_action import STOP_CAP_PCT as S57_STOP_CAP
from step57_price_action import STOP_FLOOR_PCT as S57_STOP_FLOOR
from step58_divergence_mtf import STOP_CAP_SWING, divergence_events, swing_stop_pct
from step63_rehab import (
    build_crowd_axis, build_news_axis, build_session_axis, build_trend_axis_1h,
    build_vol_axis,
)
from strategy import atr, rsi, vol_gated_ma

pd.set_option("display.width", 240)
pd.set_option("display.max_columns", None)

MIN_TRAIN_TRADES = 15
MIN_VAL_TRADES = 8
INITIAL_EQUITY = 10_000.0

TOOL_NAMES = ["T1-news-momentum", "T2-hidden-div-4h", "T3-choch-confluence",
              "T4-donchian20-1h", "T5-strikes-rsi3-dip", "T6-forensic-short",
              "T7-volshock-continuation", "T8-bbwidth-squeeze-4h"]


# ===========================================================================
# DATA LOADING
# ===========================================================================

def load_data():
    print("Loading cached data (no network calls needed)...")
    d1h = fetch_bybit_deep("1h", "BTCUSDT")
    frame4h = fetch_bybit_deep("4h", "BTCUSDT")
    funding_hist = fetch_funding_history("BTCUSDT")
    funding1h = align_funding(d1h, funding_hist)
    funding4h = align_funding(frame4h, funding_hist)

    news = pd.read_parquet("data_watcherguru_history.parquet")
    tags = pd.read_parquet("data_watcherguru_ai_tags.parquet")
    news_tagged = news.merge(tags, on="message_id", how="inner")
    news_span_start = news["utc_timestamp"].min()
    news_span_end = news["utc_timestamp"].max()

    n1, i_tr1, i_va1 = split_points(d1h)
    n4, i_tr4, i_va4 = split_points(frame4h)
    print(f"  1h: {n1} bars, {d1h['timestamp'].iloc[0]:%Y-%m-%d} -> {d1h['timestamp'].iloc[-1]:%Y-%m-%d} | "
          f"train->{d1h['timestamp'].iloc[i_tr1]:%Y-%m-%d} val->{d1h['timestamp'].iloc[i_va1]:%Y-%m-%d}")
    print(f"  4h: {n4} bars, {frame4h['timestamp'].iloc[0]:%Y-%m-%d} -> {frame4h['timestamp'].iloc[-1]:%Y-%m-%d} | "
          f"train->{frame4h['timestamp'].iloc[i_tr4]:%Y-%m-%d} val->{frame4h['timestamp'].iloc[i_va4]:%Y-%m-%d}")
    print(f"  WatcherGuru: {len(news)} posts ({news_span_start:%Y-%m-%d} -> {news_span_end:%Y-%m-%d}), "
          f"{int(news_tagged['ai_relevant'].sum())} ai_relevant=True")

    return dict(d1h=d1h, frame4h=frame4h, funding1h=funding1h, funding4h=funding4h,
                news=news, news_tagged=news_tagged,
                news_span_start=news_span_start, news_span_end=news_span_end,
                i_tr1=i_tr1, i_va1=i_va1, i_tr4=i_tr4, i_va4=i_va4)


# ===========================================================================
# SCENARIO CLASSIFIER — axes + cell enumeration (see module docstring)
# ===========================================================================

def build_trend_axis_native(d, k=8):
    """TREND read directly at the frame's own native resolution (used for
    the two 4h-trading tools) — identical champ-sign + BOS-chain-agreement
    formula as build_trend_axis_1h's internal computation, with no extra
    cross-timeframe shift (there is no coarser frame to borrow from when
    the tool itself already trades at 4h). See module docstring."""
    champ_ls = vol_gated_ma(d, fast=20, slow=100, min_atr_pct=1.5, allow_short=True).fillna(0)
    chain = bos_chain(d, k)["chain"]
    trend = pd.Series("ranging", index=d.index, dtype=object)
    trend[(champ_ls == 1) & (chain == 1)] = "trending-up"
    trend[(champ_ls == -1) & (chain == -1)] = "trending-down"
    return trend.reset_index(drop=True)


def build_axes(d, funding_bps, news, span_start, span_end, native_trend, frame4h=None, d1h=None):
    if native_trend:
        trend = build_trend_axis_native(d)
    else:
        trend = build_trend_axis_1h(frame4h, d1h)
    vol = build_vol_axis(d)
    crowd = build_crowd_axis(d, funding_bps)
    news_hot = build_news_axis(d, news, span_start, span_end)
    session = build_session_axis(d)
    return dict(trend=trend.reset_index(drop=True), vol=vol.reset_index(drop=True),
                crowd=crowd.reset_index(drop=True), news_hot=news_hot.reset_index(drop=True),
                session=session.reset_index(drop=True))


def build_cells(trend, vol, crowd, news_hot, session):
    """73 cells, fixed enumeration — see module docstring. Returns
    (cells: name->bool Series, axes_of: name->set of axis names referenced)."""
    cells, axes_of = {}, {}
    trends = ("trending-up", "trending-down", "ranging")
    vols = ("quiet", "normal", "violent")
    sessions = ("asia", "london", "newyork", "off-hours", "weekend")
    crowds = ("crowded-long", "crowded-short", "neutral")

    for t in trends:
        for v in vols:
            name = f"{t}×{v}"
            cells[name] = ((trend == t) & (vol == v)).reset_index(drop=True)
            axes_of[name] = {"trend", "vol"}

    for t in trends:
        for v in vols:
            for s in sessions:
                name = f"{t}×{v}×{s}"
                cells[name] = ((trend == t) & (vol == v) & (session == s)).reset_index(drop=True)
                axes_of[name] = {"trend", "vol", "session"}

    cells["crowded-long×violent"] = ((crowd == "crowded-long") & (vol == "violent")).reset_index(drop=True)
    axes_of["crowded-long×violent"] = {"crowd", "vol"}
    cells["crowded-short×violent"] = ((crowd == "crowded-short") & (vol == "violent")).reset_index(drop=True)
    axes_of["crowded-short×violent"] = {"crowd", "vol"}
    cells["neutral-crowd×violent"] = ((crowd == "neutral") & (vol == "violent")).reset_index(drop=True)
    axes_of["neutral-crowd×violent"] = {"crowd", "vol"}

    cells["news-hot(13mo-span)"] = news_hot.reset_index(drop=True)
    axes_of["news-hot(13mo-span)"] = {"news"}

    cells["ALL-violent"] = (vol == "violent").reset_index(drop=True)
    axes_of["ALL-violent"] = {"vol"}

    for s in sessions:
        name = f"session={s}"
        cells[name] = (session == s).reset_index(drop=True)
        axes_of[name] = {"session"}

    for c in crowds:
        name = f"crowd={c}"
        cells[name] = (crowd == c).reset_index(drop=True)
        axes_of[name] = {"crowd"}

    for v in vols:
        name = f"vol={v}"
        cells[name] = (vol == v).reset_index(drop=True)
        axes_of[name] = {"vol"}

    for t in trends:
        name = f"trend={t}"
        cells[name] = (trend == t).reset_index(drop=True)
        axes_of[name] = {"trend"}

    return cells, axes_of


# ===========================================================================
# GENERIC BACKTEST PLUMBING (step63-style)
# ===========================================================================

def _run(d, sig, f, lo, hi, stop_pct, target_pct):
    return run_backtest(
        d.iloc[lo:hi].reset_index(drop=True), sig.iloc[lo:hi].reset_index(drop=True),
        execution="maker", funding_series=f.iloc[lo:hi].reset_index(drop=True),
        stop_pct=stop_pct, target_pct=target_pct,
    )


def verdict_cell(tr_n, tr_exp, checked_val, va_n, va_exp):
    if tr_n < MIN_TRAIN_TRADES:
        return "UNRELIABLE"
    if tr_exp <= 0:
        return "COLD"
    if not checked_val:
        return "UNRELIABLE"
    if va_n < MIN_VAL_TRADES:
        return "THIN-VAL"
    if va_exp <= 0:
        return "FADED"
    return "HOT"


def eval_cell(d, f, i_tr, i_va, sig, stop_pct, target_pct):
    tr = _run(d, sig, f, 0, i_tr, stop_pct, target_pct)
    tr_n, tr_exp = len(tr.trades), tr.expectancy
    checked_val = (tr_exp > 0 and tr_n >= MIN_TRAIN_TRADES)
    if checked_val:
        va = _run(d, sig, f, i_tr, i_va, stop_pct, target_pct)
        va_n, va_exp = len(va.trades), va.expectancy
    else:
        va, va_n, va_exp = None, 0, float("nan")
    verdict = verdict_cell(tr_n, tr_exp, checked_val, va_n, va_exp)
    return dict(tr_n=tr_n, tr_exp=tr_exp, checked_val=checked_val,
                va_n=va_n, va_exp=va_exp, verdict=verdict)


def eval_tool_cells(spec):
    """UNCONDITIONAL baseline + all 73 cells for one tool. Returns
    (baseline dict with tr/va BacktestResult, cell_results dict, rows list)."""
    d, f, i_tr, i_va = spec["d"], spec["f"], spec["i_tr"], spec["i_va"]
    el0, es0 = spec["enter_long"], spec["enter_short"]
    stop_pct, target_pct, mh_bars = spec["stop_pct"], spec["target_pct"], spec["mh_bars"]

    base_sig = day_trade_signal(d, el0, es0, mh_bars)
    b_tr = _run(d, base_sig, f, 0, i_tr, stop_pct, target_pct)
    b_va = _run(d, base_sig, f, i_tr, i_va, stop_pct, target_pct)
    baseline = dict(tr=b_tr, va=b_va)

    rows = [dict(tool=spec["name"], cell="UNCONDITIONAL",
                 tr_n=len(b_tr.trades), tr_exp=b_tr.expectancy,
                 va_n=len(b_va.trades), va_exp=b_va.expectancy, verdict="BASELINE")]

    cell_results = {}
    for cname, cmask in spec["cells"].items():
        elc = el0 & cmask.reindex(d.index).fillna(False)
        esc = es0 & cmask.reindex(d.index).fillna(False)
        sig = day_trade_signal(d, elc, esc, mh_bars)
        r = eval_cell(d, f, i_tr, i_va, sig, stop_pct, target_pct)
        cell_results[cname] = r
        rows.append(dict(tool=spec["name"], cell=cname, tr_n=r["tr_n"], tr_exp=r["tr_exp"],
                          va_n=r["va_n"], va_exp=r["va_exp"], verdict=r["verdict"]))
    return baseline, cell_results, rows


def eligible_cells(cell_results, axes_of, exclude_axis=None):
    names = [name for name, r in cell_results.items()
             if r["tr_exp"] > 0 and r["tr_n"] >= MIN_TRAIN_TRADES
             and (exclude_axis is None or exclude_axis not in axes_of[name])]
    return names


def union_mask(cells, names):
    if not names:
        return None
    mask = None
    for name in names:
        m = cells[name]
        mask = m.copy() if mask is None else (mask | m)
    return mask


def val_trades_for_mask(spec, mask):
    d, f, i_tr, i_va = spec["d"], spec["f"], spec["i_tr"], spec["i_va"]
    el0, es0 = spec["enter_long"], spec["enter_short"]
    if mask is None:
        return []
    elc = el0 & mask.reindex(d.index).fillna(False)
    esc = es0 & mask.reindex(d.index).fillna(False)
    sig = day_trade_signal(d, elc, esc, spec["mh_bars"])
    va = _run(d, sig, f, i_tr, i_va, spec["stop_pct"], spec["target_pct"])
    return list(va.trades)


def dumb_mask_for(cells, k, seed):
    if k <= 0:
        return None, []
    names = sorted(cells.keys())
    rng = np.random.RandomState(seed)
    chosen = list(rng.choice(names, size=min(k, len(names)), replace=False))
    return union_mask(cells, chosen), chosen


# ===========================================================================
# PORTFOLIO MERGE (multi-tool, mixed-timeframe, single-slot)
# ===========================================================================

def trades_to_pct(trades):
    out = []
    for t in trades:
        notional = abs(t.units) * t.entry_price
        r = t.pnl / notional if notional else 0.0
        out.append((t.entry_time, t.exit_time, r))
    return out


def merge_portfolio(trade_lists):
    allc = []
    for lst in trade_lists:
        allc.extend(lst)
    allc.sort(key=lambda x: x[0])
    accepted = []
    busy_until = None
    for et, xt, r in allc:
        if busy_until is None or et >= busy_until:
            accepted.append((et, xt, r))
            busy_until = xt
    return accepted


def portfolio_stats(accepted, initial_equity=INITIAL_EQUITY):
    if not accepted:
        return dict(n=0, expectancy=0.0, total_return_pct=0.0, max_dd_pct=0.0)
    equity = initial_equity
    curve = [equity]
    pnls = []
    for et, xt, r in accepted:
        pnl = equity * r
        equity += pnl
        pnls.append(pnl)
        curve.append(equity)
    arr = np.array(pnls)
    curve_arr = np.array(curve)
    peaks = np.maximum.accumulate(curve_arr)
    dd = (curve_arr - peaks) / peaks
    return dict(n=len(accepted), expectancy=float(arr.mean()),
                total_return_pct=(equity / initial_equity - 1) * 100,
                max_dd_pct=float(dd.min() * 100))


# ===========================================================================
# TOOL RECONSTRUCTIONS (T1-T8) — see module docstring for source-round cites
# ===========================================================================

def build_t1(data, cells_1h):
    d1h, funding1h, news = data["d1h"], data["funding1h"], data["news"]
    news_min, news_max = news["utc_timestamp"].min(), news["utc_timestamp"].max()
    span_mask = ((d1h["timestamp"] >= news_min - pd.Timedelta(hours=24)) &
                 (d1h["timestamp"] <= news_max + pd.Timedelta(hours=24)))
    d = d1h[span_mask].reset_index(drop=True)
    f = funding1h[span_mask].reset_index(drop=True)
    n, i_tr, i_va = split_points(d)

    relevant_mask = news["text"].apply(lambda t: classify_headline(t).get("relevant", False))
    relevant_ts = pd.DatetimeIndex(sorted(news[relevant_mask]["utc_timestamp"]))
    _, trading_idx, valid = align_events(d, relevant_ts)
    trading_idx = trading_idx[valid]
    trading_idx = trading_idx[trading_idx < len(d)]
    o, c = d["open"].to_numpy(), d["close"].to_numpy()
    el_arr = np.zeros(len(d), dtype=bool)
    es_arr = np.zeros(len(d), dtype=bool)
    seen = set()
    for idx in sorted(set(int(x) for x in trading_idx)):
        if idx in seen:
            continue
        seen.add(idx)
        if c[idx] > o[idx]:
            el_arr[idx] = True
        elif c[idx] < o[idx]:
            es_arr[idx] = True
    enter_long = pd.Series(el_arr, index=d.index)
    enter_short = pd.Series(es_arr, index=d.index)

    cells = {name: m[span_mask.to_numpy()].reset_index(drop=True) for name, m in cells_1h.items()}
    return dict(name="T1-news-momentum", d=d, f=f, i_tr=i_tr, i_va=i_va,
                enter_long=enter_long, enter_short=enter_short,
                stop_pct=1.2, target_pct=2.4, mh_bars=hours_to_bars(d, 24), cells=cells)


def build_t2(data, cells_4h):
    frame4h, funding4h = data["frame4h"], data["funding4h"]
    d, f = frame4h, funding4h
    n, i_tr, i_va = split_points(d)
    champ4h = vol_gated_ma(d, **CHAMP_KW)          # long-only 0/1
    osc = rsi(d["close"], 14)
    k = 5
    long_reg, short_reg, long_hid, short_hid, low_ext, high_ext = divergence_events(d, osc, k, champ4h)
    buffer_pct = 0.15
    stop_l = swing_stop_pct(d["close"], low_ext, long_hid, i_tr, buffer_pct, STOP_CAP_SWING)
    stop_s = swing_stop_pct(d["close"], high_ext, short_hid, i_tr, buffer_pct, STOP_CAP_SWING)
    n_l, n_s = int(long_hid.sum()), int(short_hid.sum())
    stop_pct = (stop_l * n_l + stop_s * n_s) / (n_l + n_s) if (n_l + n_s) else STOP_CAP_SWING
    target_pct = min(3.0 * stop_pct, 3 * STOP_CAP_SWING)
    return dict(name="T2-hidden-div-4h", d=d, f=f, i_tr=i_tr, i_va=i_va,
                enter_long=long_hid, enter_short=short_hid,
                stop_pct=stop_pct, target_pct=target_pct, mh_bars=hours_to_bars(d, 96),
                cells=cells_4h)


def build_t3(data, cells_1h, bias_1h):
    d1h, funding1h = data["d1h"], data["funding1h"]
    d, f = d1h, funding1h
    n, i_tr, i_va = split_points(d)
    k = 8
    CONF_TOL, CONF_DEPTH = 0.1, 0.3
    CONF_FILL, CONF_EXPIRE_DAYS = 0.5, 10
    CONF_FIB_EXPIRE_DAYS = 20
    CONF_HOLD_DAYS = 10

    bos = bos_chain(d, k)
    discount, premium, eq, lsh, lsl = equilibrium(d, k)
    pool_high, pool_low = liquidity_pools(d, k, CONF_TOL)
    sweep_long, sweep_short = sweep_events(d, pool_high, pool_low, CONF_DEPTH)
    window = hours_to_bars(d, 24)
    swept_recent_long = (sweep_long.astype(int).rolling(window, min_periods=1).max().fillna(0).astype(bool))
    swept_recent_short = (sweep_short.astype(int).rolling(window, min_periods=1).max().fillna(0).astype(bool))
    el_fvg, es_fvg, dl_fvg, ds_fvg, ab, ar = fvg_signals(d, CONF_FILL, days_to_bars(d, CONF_EXPIRE_DAYS))
    bull_low, bull_high, bear_low, bear_high = leg_tracker(d, k, days_to_bars(d, CONF_FIB_EXPIRE_DAYS))
    el_fib, es_fib, dl_fib, ds_fib, extl, exts, lz, sz = fib_entries(
        d, bull_low, bull_high, bear_low, bear_high, 0.618, 0.79)

    bias_long = (bias_1h == 1)
    bias_short = (bias_1h == -1)
    count_long = (bias_long.astype(int) + discount.astype(int) + lz.astype(int)
                  + swept_recent_long.astype(int) + ab.astype(int))
    count_short = (bias_short.astype(int) + premium.astype(int) + sz.astype(int)
                   + swept_recent_short.astype(int) + ar.astype(int))

    choch_long, choch_short = bos["choch_long"], bos["choch_short"]
    threshold = 2
    el0 = (choch_long & (count_long >= threshold)).fillna(False)
    es0 = (choch_short & (count_short >= threshold)).fillna(False)

    dist_bos_long = (d["close"] - bos["lsl"]) / d["close"] * 100
    dist_bos_short = (bos["lsh"] - d["close"]) / d["close"] * 100
    mask = el0 | es0
    dist = pd.Series(np.nan, index=d.index)
    dist = dist.mask(el0, dist_bos_long)
    dist = dist.mask(es0, dist_bos_short)
    stop_pct = train_median_stop_pct(d, i_tr, mask, dist)
    if stop_pct is None:
        stop_pct = 1.0
    target_pct = stop_pct * 2.0

    return dict(name="T3-choch-confluence", d=d, f=f, i_tr=i_tr, i_va=i_va,
                enter_long=el0, enter_short=es0,
                stop_pct=stop_pct, target_pct=target_pct,
                mh_bars=days_to_bars(d, CONF_HOLD_DAYS), cells=cells_1h)


def build_t4(data, cells_1h):
    d1h, funding1h, i_tr1 = data["d1h"], data["funding1h"], data["i_tr1"]
    d, f = d1h, funding1h
    n, i_tr, i_va = split_points(d)
    hi = d["high"].rolling(20).max().shift(1)
    enter_long = (d["close"] > hi).fillna(False)
    enter_short = pd.Series(False, index=d.index)

    train_c = d.iloc[0:i_tr].reset_index(drop=True)
    atr_pct_train = atr(train_c, 14) / train_c["close"] * 100
    stop_pct = float(1.5 * atr_pct_train.median())
    target_pct = 2.0 * stop_pct
    return dict(name="T4-donchian20-1h", d=d, f=f, i_tr=i_tr, i_va=i_va,
                enter_long=enter_long, enter_short=enter_short,
                stop_pct=stop_pct, target_pct=target_pct, mh_bars=240, cells=cells_1h)


def build_t5(data, cells_1h):
    d1h, frame4h, funding1h = data["d1h"], data["frame4h"], data["funding1h"]
    d, f = d1h, funding1h
    n, i_tr, i_va = split_points(d)
    champ4h = vol_gated_ma(frame4h, fast=20, slow=100, min_atr_pct=1.5)   # long-only
    champ_on_1h = champ_aligned(frame4h, champ4h, d)
    r3 = rsi(d["close"], 3)
    enter_long = ((champ_on_1h == 1) & (r3 < 15)).fillna(False)
    enter_short = pd.Series(False, index=d.index)
    return dict(name="T5-strikes-rsi3-dip", d=d, f=f, i_tr=i_tr, i_va=i_va,
                enter_long=enter_long, enter_short=enter_short,
                stop_pct=1.5, target_pct=4.5, mh_bars=hours_to_bars(d, 48), cells=cells_1h)


def build_t6(data, cells_1h):
    d1h, funding1h = data["d1h"], data["funding1h"]
    d, f = d1h, funding1h
    n, i_tr, i_va = split_points(d)
    fund_thresh, atr_thresh, pop_thresh, pop_hours = 1.5, 1.2, 1.5, 4
    pop_bars = hours_to_bars(d, pop_hours)
    pop = (d["close"] / d["close"].shift(pop_bars) - 1) * 100
    atr_pct = atr(d, 14) / d["close"] * 100
    enter_short = ((f > fund_thresh) & (pop > pop_thresh) & (atr_pct > atr_thresh)).fillna(False)
    enter_long = pd.Series(False, index=d.index)
    return dict(name="T6-forensic-short", d=d, f=f, i_tr=i_tr, i_va=i_va,
                enter_long=enter_long, enter_short=enter_short,
                stop_pct=1.69, target_pct=5.07, mh_bars=hours_to_bars(d, 48), cells=cells_1h)


def build_t7(data, cells_1h):
    d1h, funding1h, i_tr1 = data["d1h"], data["funding1h"], data["i_tr1"]
    d, f = d1h, funding1h
    n, i_tr, i_va = split_points(d)
    vol_base = volume_baseline(d)
    absret_base = absret_baseline(d)
    K = 6
    enter_long, enter_short = familyC_entries(d, K, vol_base, absret_base)
    atr_pct = atr(d, 14) / d["close"] * 100
    med_atr_train = float(atr_pct.iloc[:i_tr].median())
    stop_pct = min(1.5 * med_atr_train, HARD_STOP_CAP)
    target_pct = 3.0 * stop_pct
    return dict(name="T7-volshock-continuation", d=d, f=f, i_tr=i_tr, i_va=i_va,
                enter_long=enter_long, enter_short=enter_short,
                stop_pct=stop_pct, target_pct=target_pct, mh_bars=hours_to_bars(d, 24),
                cells=cells_1h)


def build_t8(data, cells_4h):
    frame4h, funding4h = data["frame4h"], data["funding4h"]
    d, f = frame4h, funding4h
    n, i_tr, i_va = split_points(d)
    el0, es0, is_sq = bbwidth_signals(d, 20)
    atr_pct = atr(d, 14) / d["close"] * 100
    med_atr_train = float(atr_pct.iloc[:i_tr].median())
    stop_pct = min(max(1.0 * med_atr_train, S57_STOP_FLOOR), S57_STOP_CAP)
    return dict(name="T8-bbwidth-squeeze-4h", d=d, f=f, i_tr=i_tr, i_va=i_va,
                enter_long=el0, enter_short=es0,
                stop_pct=stop_pct, target_pct=None, mh_bars=hours_to_bars(d, 48),
                cells=cells_4h)


# ===========================================================================
# main
# ===========================================================================

def main():
    data = load_data()
    d1h, frame4h = data["d1h"], data["frame4h"]
    funding1h, funding4h = data["funding1h"], data["funding4h"]
    news, span_start, span_end = data["news_tagged"], data["news_span_start"], data["news_span_end"]

    print("\nBuilding 1h scenario axes...")
    axes_1h = build_axes(d1h, funding1h, news, span_start, span_end, native_trend=False, frame4h=frame4h, d1h=d1h)
    cells_1h, axes_of = build_cells(**axes_1h)
    print(f"  {len(cells_1h)} cells built (1h). Populated (of {len(d1h)} bars):")
    for name, m in list(cells_1h.items())[:9]:
        print(f"    {name:32s} {int(m.sum()):6d} bars ({m.mean()*100:5.1f}%)")
    print("    ... (full breakdown in raw output)")

    print("\nBuilding 4h scenario axes (native resolution, see docstring)...")
    axes_4h = build_axes(frame4h, funding4h, news, span_start, span_end, native_trend=True)
    cells_4h, axes_of_4h = build_cells(**axes_4h)
    print(f"  {len(cells_4h)} cells built (4h).")

    print("\nBuilding T3's 4h bias (step56 bias_series_4h -> champ_aligned onto 1h)...")
    bias4h = bias_series_4h(frame4h)
    bias_1h = champ_aligned(frame4h, bias4h, d1h)

    print("\nReconstructing all 8 tools...")
    specs = [
        build_t1(data, cells_1h),
        build_t2(data, cells_4h),
        build_t3(data, cells_1h, bias_1h),
        build_t4(data, cells_1h),
        build_t5(data, cells_1h),
        build_t6(data, cells_1h),
        build_t7(data, cells_1h),
        build_t8(data, cells_4h),
    ]
    for s in specs:
        print(f"  {s['name']:26s} n={len(s['d']):6d} bars | stop={s['stop_pct']:.2f}% "
              f"target={('%.2f%%' % s['target_pct']) if s['target_pct'] else 'none (stop+timecap only)'} "
              f"max_hold={s['mh_bars']}bars | i_tr={s['i_tr']} i_va={s['i_va']}")

    print("\n" + "=" * 78)
    print("PER-TOOL x PER-CELL EVALUATION (73 cells + UNCONDITIONAL baseline each)")
    print("=" * 78)
    all_rows = []
    baselines = {}
    cell_results_by_tool = {}
    for spec in specs:
        print(f"\n--- {spec['name']} ---")
        baseline, cell_results, rows = eval_tool_cells(spec)
        all_rows += rows
        baselines[spec["name"]] = baseline
        cell_results_by_tool[spec["name"]] = cell_results
        b_tr, b_va = baseline["tr"], baseline["va"]
        print(f"  UNCONDITIONAL: train ${b_tr.expectancy:+.2f}/t n={len(b_tr.trades)} | "
              f"val ${b_va.expectancy:+.2f}/t n={len(b_va.trades)}")
        n_hot = sum(1 for r in cell_results.values() if r["verdict"] == "HOT")
        n_elig = sum(1 for r in cell_results.values() if r["tr_exp"] > 0 and r["tr_n"] >= MIN_TRAIN_TRADES)
        print(f"  {n_hot} HOT cells (train+val both positive+floor) / {n_elig} train-eligible cells / "
              f"{len(cell_results)} total")

    df = pd.DataFrame(all_rows)
    df.to_csv("step66_results_raw.csv", index=False)
    print(f"\n{len(df)} rows written to step66_results_raw.csv")

    # ---- ROUTER: full 5-axis + 5 marginal-axis-removed + dumb control ----
    print("\n" + "=" * 78)
    print("ROUTER CONSTRUCTION (train-side selection) + VAL PORTFOLIO MERGE")
    print("=" * 78)

    router_names = {}          # tool -> eligible cell names (full router)
    router_val_trades = {}     # tool -> list[Trade]
    rack_val_trades = {}       # tool -> list[Trade] (unconditional)
    dumb_val_trades = {}       # tool -> list[Trade]
    dumb_names = {}
    marginal_val_trades = {axis: {} for axis in ("trend", "vol", "crowd", "news", "session")}
    marginal_names = {axis: {} for axis in ("trend", "vol", "crowd", "news", "session")}

    for i, spec in enumerate(specs):
        name = spec["name"]
        cr = cell_results_by_tool[name]
        elig = eligible_cells(cr, axes_of)
        router_names[name] = elig
        mask = union_mask(spec["cells"], elig)
        router_val_trades[name] = val_trades_for_mask(spec, mask)
        rack_val_trades[name] = list(baselines[name]["va"].trades)

        dmask, dnames = dumb_mask_for(spec["cells"], len(elig), seed=1000 + i)
        dumb_names[name] = dnames
        dumb_val_trades[name] = val_trades_for_mask(spec, dmask)

        for axis in marginal_val_trades:
            elig_ax = eligible_cells(cr, axes_of, exclude_axis=axis)
            marginal_names[axis][name] = elig_ax
            mask_ax = union_mask(spec["cells"], elig_ax)
            marginal_val_trades[axis][name] = val_trades_for_mask(spec, mask_ax)

        print(f"  {name:26s} eligible cells: {len(elig):3d} / 73 -> routed VAL trades: "
              f"{len(router_val_trades[name]):4d}  (rack: {len(rack_val_trades[name]):4d}, "
              f"dumb-matched: {len(dumb_val_trades[name]):4d})")

    def merge_and_stat(trade_dict):
        pct_lists = [trades_to_pct(trade_dict[n]) for n in TOOL_NAMES]
        accepted = merge_portfolio(pct_lists)
        return portfolio_stats(accepted), accepted

    router_stats, router_accepted = merge_and_stat(router_val_trades)
    rack_stats, _ = merge_and_stat(rack_val_trades)
    dumb_stats, _ = merge_and_stat(dumb_val_trades)

    print("\n--- PORTFOLIO COMPARISON (VAL, merged across all 8 tools, single-slot) ---")
    print(f"  {'ROUTED':22s} n={router_stats['n']:4d}  exp ${router_stats['expectancy']:+8.2f}/t  "
          f"ret {router_stats['total_return_pct']:+7.1f}%  maxDD {router_stats['max_dd_pct']:6.1f}%")
    print(f"  {'ALL-TOOLS-ALWAYS-ON':22s} n={rack_stats['n']:4d}  exp ${rack_stats['expectancy']:+8.2f}/t  "
          f"ret {rack_stats['total_return_pct']:+7.1f}%  maxDD {rack_stats['max_dd_pct']:6.1f}%")
    print(f"  {'DUMB-ROUTER (control)':22s} n={dumb_stats['n']:4d}  exp ${dumb_stats['expectancy']:+8.2f}/t  "
          f"ret {dumb_stats['total_return_pct']:+7.1f}%  maxDD {dumb_stats['max_dd_pct']:6.1f}%")

    print("\n--- EACH TOOL SOLO (VAL, unconditional, that tool's own run_backtest) ---")
    solo_rows = []
    for spec in specs:
        va = baselines[spec["name"]]["va"]
        solo_rows.append(dict(tool=spec["name"], n=len(va.trades), expectancy=va.expectancy,
                               total_return_pct=va.total_return_pct, max_dd_pct=va.max_drawdown_pct))
        print(f"  {spec['name']:26s} n={len(va.trades):4d}  exp ${va.expectancy:+8.2f}/t  "
              f"ret {va.total_return_pct:+7.1f}%  maxDD {va.max_drawdown_pct:6.1f}%")

    print("\n--- MARGINAL AXIS VALUE (router with one axis's cells removed, VAL portfolio) ---")
    marginal_stats = {}
    for axis in marginal_val_trades:
        stats, _ = merge_and_stat(marginal_val_trades[axis])
        marginal_stats[axis] = stats
        delta_exp = stats["expectancy"] - router_stats["expectancy"]
        print(f"  router-no{axis.upper():8s} n={stats['n']:4d}  exp ${stats['expectancy']:+8.2f}/t "
              f"(full router ${router_stats['expectancy']:+.2f}/t, delta {delta_exp:+.2f}) "
              f"ret {stats['total_return_pct']:+7.1f}%  maxDD {stats['max_dd_pct']:6.1f}%")

    # ---- playbook: populated HOT cells per tool ----
    print("\n" + "=" * 78)
    print("THE LEARNED PLAYBOOK (HOT cells: train+val both positive, both floors cleared)")
    print("=" * 78)
    hot_rows = df[df["verdict"] == "HOT"].sort_values(["cell", "tool"])
    print(hot_rows.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    hot_rows.to_csv("step66_hot_cells.csv", index=False)

    return dict(df=df, baselines=baselines, cell_results_by_tool=cell_results_by_tool,
                axes_of=axes_of, router_names=router_names, dumb_names=dumb_names,
                marginal_names=marginal_names, router_stats=router_stats, rack_stats=rack_stats,
                dumb_stats=dumb_stats, marginal_stats=marginal_stats, solo_rows=solo_rows,
                specs=specs)


if __name__ == "__main__":
    main()
