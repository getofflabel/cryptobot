"""
step74_structure.py — round 74: THE FAIR TEST of Alex Gonzalez's ("fxalexg")
structure -> retest -> engulfing system, at the DAILY timeframe with deep
(20+ year) history, closing round 73's data-depth gap.

Run:  python3 step74_structure.py

Research only — no commits, no live orders. Writes step74_structure.py
(this file), step74_results.md, step74_gauntlet_full.csv.

WHY THIS ROUND: round 73 gauntleted this same trader's system on a daily-
context -> 4h-entry two-tier collapse, because yfinance's ~60d cap on
sub-hourly bars made an honest 60/20/20 gauntlet at his real 15m/30m/1h
entry resolution impossible for forex/gold/index. The result: 85% of
round 73's 108 configs came back INSUFFICIENT-SAMPLE (his system fires
roughly once every 25-90 days -> a ~2-year intraday-derived history simply
never accumulates the 30 train / 8 val trade floors). That is a DATA-DEPTH
verdict, not a strategy verdict. His own structure work is explicitly
weekly/daily anyway ("I only use the weekly, the daily, the 4 hour...").
Free DAILY history for forex/metals/indices runs 20+ years via yfinance,
and this repo already holds a 14.9-year BTC daily cache (bitstamp, back to
2011) — deep enough that his stated 4-14 trades/yr SHOULD clear the
floors if the system has any real signal. This round drops the two-tier
HTF/LTF collapse entirely and runs his system on ONE timeframe: daily
structure, daily retest, daily engulfing confirmation. Simpler, and more
faithful to the source's own framing of the mechanical core (see
step73_rules.md, read FIRST — this docstring only covers what's NEW here).

REUSE / ATTRIBUTION (do not reimplement — imported or copied verbatim):
- confirmed_swings, bar_hours, days_to_bars, hours_to_bars, split_points
  -> step41_shorts.py, UNMODIFIED, imported.
- bos_chain (break-of-structure / CHoCH chain-state detector)
  -> step56_smc_toolkit.py, UNMODIFIED, imported.
- body_frame (wick-excluded body-substituted OHLC), engulf2_events (his
  own "engulf the last TWO candlesticks minimum" rule, also stands in for
  his morning-star/evening-star pattern per step73's docstring),
  breakout_entries (fire on first armed bar, no retest wait),
  retest_confirm_entries (armed-window state machine: touch -> engulf ->
  entry), merge_event_recency_with_value (no-lookahead event availability
  + frozen broken-level value, carried through an armed window),
  day_trade_signal (max-hold position state machine)
  -> step73_video.py, UNMODIFIED, imported. Round 73's own docstring
  attributes body_frame/engulf2_events/etc. to the same "his own stated
  rule" quotes documented in step73_rules.md — not re-derived here.

WHAT'S DIFFERENT FROM ROUND 73 (single-timeframe collapse)
- ONE frame, not two: merge_event_recency_with_value is called with
  struct_ts == entry_ts == d["timestamp"] and struct_bar_hours ==
  entry_bar_hours == bar_hours(d) (24 for daily bars). This still uses
  the function's no-lookahead avail_time = struct_ts + bar_hours logic
  correctly (a break confirmed at bar i's close only becomes tradeable
  starting bar i+1) — it was written generically enough that same-frame
  use needs no modification, just different arguments.
- STOP is WICK-based, not body-based, and carries an EXPLICIT buffer:
  round 73 approximated the stop as the nearest confirmed BODY-swing
  extreme (a stated simplification under the wick-exclusion structure
  rule). This round's task spec is more literal about his one numeric
  worked example ("stop loss anywhere from 10 to 15 pips above THIS
  WICK... 20 23 pips total") — stop = nearest confirmed swing extreme on
  RAW (wick-included) high/low, TRAIN-median % distance, PLUS an explicit
  buffer swept over {0.1%, 0.2%} of price (a cross-instrument-portable
  stand-in for his pip buffer, exactly like round 73's TOL_PCT
  retest-tolerance approximation). New function: stop_distance_pct_wick
  (this file) — same shape as step73_video.py's stop_distance_pct, but
  calls confirmed_swings() on the RAW frame instead of body_frame(d).
- NEW HELPER: retest_touch_entries (this file) — a stripped-down sibling
  of step73_video.py's retest_confirm_entries with the engulf-confirmation
  gate REMOVED (enters on the first retest touch instead). This is
  ablation (a)'s engine: does his signature "engulf the last two
  candlesticks" rule earn its keep, or is break+retest the whole edge?
- NEW HELPER: apply_trend_filter (this file) — a 200-day SMA higher-
  timeframe-trend gate (long only if close > SMA200, short only if
  close < SMA200 at entry). This is ablation (c)'s engine, testing his
  own claim (chapter 20, "Reversal Patterns") that reversal trades
  against the prevailing trend work about as well as trend-continuation
  trades — i.e. does restricting to WITH-TREND-only entries change the
  edge, or does the break-retest-engulf trigger carry it regardless of
  directional bias.

GRID (kept in the repo's established ~100-configs/round band, scaled up
for 9 instruments and 3 extra ablation axes vs round 73's 5):
- STAGE 1 (the literal config, full sensitivity sweep): MODE in
  {reversal(choch), continuation(cont), both(any bos)} x k in {2,3} x
  RETEST_WINDOW in {5,10} bars x STOP_BUFFER in {0.1%,0.2%} x R in
  {2,3,4} = 72 configs/instrument, full stack (retest REQUIRED, engulf
  REQUIRED), TREND_FILTER off.
- STAGE 2 (component ablations, run at a fixed representative point
  k=3/window=10/buffer=0.1% to isolate ONE change at a time, R swept):
  (a) no_engulf (retest_touch_entries, engulf dropped) x R{2,3,4} = 3
  (b) breakout (no retest at all, enter at break) x R{2,3,4} = 3
  (c) trend_filter=on (full stack + 200-SMA with-trend gate) x R{2,3,4} = 3
  All three ablations use mode="both" to isolate the ablated component
  from the mode question already answered in stage 1. Baseline for
  comparison = stage 1's own "both k=3 w=10 buf=0.1 R=*" rows.
- 81 configs/instrument x 9 instruments = 729 total.

DATA: yfinance daily, max period, per the round's task spec: GBPUSD,
USDJPY, EURUSD, USDCAD, USDCHF, GBPJPY (his live chapters actually trade
GBPCHF/USDJPY/GBPJPY/EURUSD/USDCAD/NZDCAD/USDCHF per step73_rules.md;
GBPCHF and NZDCAD are not plain yfinance tickers with deep max-period
daily coverage the way the majors are, so the task spec swaps in GBPUSD
as his other most-traded home-turf major, keeping USDJPY/EURUSD/USDCAD/
USDCHF/GBPJPY exactly as he actually traded them), plus GC=F (gold, his
claimed-but-never-demonstrated commodity market) and SPY (cross-market
equity check), plus
BTC daily from this repo's own deep bitstamp cache (2011-present, the
crypto arm — also claimed but never demonstrated live). Cached as
data_fx_<TAG>_1d.parquet for every yfinance pull (BTC reuses the existing
data_bitstamp_BTCUSD_1d_2011.parquet cache directly, per the task's
"our own deep cache" instruction — no re-fetch).

COSTS (no cost-free mode exists — see backtest.py's CostModel):
- FOREX (GBPUSD/USDJPY/EURUSD/USDCAD/USDCHF/GBPJPY): fee 0.1bp +
  half-spread 0.4bp + slippage 0.25bp each side = 1.5bps round trip — a
  stated approximation of "1 pip spread equivalent," no funding (spot
  forex doesn't carry it). Slightly tighter than round 73's FOREX_COSTS
  (1.8bps) because this round's task spec asks for "~1.5bps" explicitly.
- GOLD (GC=F): fee 0.5bp + slippage 0.5bp each side, 0 half-spread = 2bps
  RT — this repo's established futures convention (step48_tradfi_trend.py,
  step60_spx_system.py's FUT_COSTS, unchanged).
- SPY: fee 1.0bp + slippage 1.0bp each side, 0 half-spread = 4bps RT —
  this repo's established ETF convention (step48/step60's ETF_COSTS,
  unchanged).
- BTC: fee 6.0bp taker/2.0bp maker + funding 1.0bp/8h, 0 half-spread/
  slippage = 12bps RT + funding — round 72/73's BTC_COSTS convention,
  unchanged. funding_series is left None (the engine's own documented
  conservative default: every held position always PAYS the flat rate,
  correctly time-weighted for daily bars per backtest.py's bar_hours /
  FUNDING_INTERVAL_HOURS logic — verified this scales correctly at any
  bar resolution, not just the 1h/4h bars every prior round used it on).
  Stated simplification: the bitstamp series is SPOT, not perpetual, so
  no real funding history exists to align against it; the flat
  conservative default is used instead of inventing one.

GAUNTLET: chronological 60/20/20 per instrument (split_points, step41,
unmodified). Select by TRAIN expectancy > 0 AND VAL expectancy > 0,
tr_n>=30 and va_n>=8 = SURVIVOR (unchanged floors from round 73). The
sealed 20% test window is NEVER computed by this script for any config —
score() only ever touches [0:i_tr] and [i_tr:i_va], exactly like every
prior round's discipline.

MAX HOLD: 60 trading days (~3 calendar months), not swept — NEW choice
for this round (round 73 used 240h/10 days on 4h bars for a swing/day-
trade hybrid entry pace; this round's daily-only entries fire far less
often per the task's own framing — "roughly once every 25-90 days" — and
his stated R:R "potential" up to 1:4 needs real room to develop on a
daily chart, not a 10-day cap sized for an hourly entry cadence). Stated,
reasoned choice, not from the source transcript (he never gives a max-
hold rule).

RISK PER TRADE / SIZING: UNSPECIFIED in the source (see step73_rules.md
section 1) — engine's standard full-equity size_frac=1.0 convention used,
as in every prior round.
"""

import warnings

import numpy as np
import pandas as pd
import yfinance as yf

import config  # noqa: F401 — imported for parity with every other step*.py; unused directly here
from backtest import CostModel, run_backtest
from step41_shorts import bar_hours, confirmed_swings, days_to_bars, split_points
from step56_smc_toolkit import bos_chain
from step73_video import (
    body_frame,
    breakout_entries,
    day_trade_signal,
    engulf2_events,
    merge_event_recency_with_value,
    retest_confirm_entries,
    _fetch_yf,
)

warnings.filterwarnings("ignore")
pd.set_option("display.width", 260)
pd.set_option("display.max_columns", None)

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8
STOP_CAP_PCT = 6.0
STOP_FLOOR_PCT = 0.15

FOREX_COSTS = CostModel(fee_bps=0.1, maker_fee_bps=0.1, half_spread_bps=0.4,
                         slippage_bps=0.25, funding_bps_8h=0.0)   # 1.5bps RT
GOLD_COSTS = CostModel(fee_bps=0.5, maker_fee_bps=0.5, half_spread_bps=0.0,
                        slippage_bps=0.5, funding_bps_8h=0.0)     # 2bps RT
SPY_COSTS = CostModel(fee_bps=1.0, maker_fee_bps=1.0, half_spread_bps=0.0,
                       slippage_bps=1.0, funding_bps_8h=0.0)      # 4bps RT
BTC_COSTS = CostModel(fee_bps=6.0, maker_fee_bps=2.0, half_spread_bps=0.0,
                       slippage_bps=0.0, funding_bps_8h=1.0)      # 12bps RT + funding

FX_TAGS = {
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "EURUSD": "EURUSD=X",
    "USDCAD": "USDCAD=X",
    "USDCHF": "USDCHF=X",
    "GBPJPY": "GBPJPY=X",
}

K_LIST = (2, 3)
WINDOW_LIST = (5, 10)          # bars = days, at daily resolution
BUFFER_LIST = (0.1, 0.2)       # % of price, added beyond the wick
R_LIST = (2.0, 3.0, 4.0)
TOL_PCT = 0.35                 # retest tolerance, % of price — same convention as round 73
MAX_HOLD_DAYS = 60.0
REP_K, REP_W, REP_BUF = 3, 10, 0.1   # ablation stage's fixed representative point


# ---------------------------------------------------------------------------
# NEW for round 74
# ---------------------------------------------------------------------------

def stop_distance_pct_wick(d, k, entry_long, entry_short):
    """Distance from entry close to the nearest confirmed swing extreme on
    RAW (wick-included) high/low, opposite the trade direction, in % —
    his stop 'beyond the invalidating wick,' literally (unlike round 73's
    body-only approximation). confirmed_swings() itself is UNMODIFIED,
    imported from step41_shorts."""
    sh, sl = confirmed_swings(d, k)
    lsh, lsl = sh.ffill(), sl.ffill()
    close = d["close"]
    dist_short = ((lsh - close) / close * 100).where(entry_short.to_numpy())
    dist_long = ((close - lsl) / close * 100).where(entry_long.to_numpy())
    return dist_long, dist_short


def train_median_stop_pct(entry_mask, distance_pct, i_tr, buffer_pct,
                           cap=STOP_CAP_PCT, floor=STOP_FLOOR_PCT):
    """TRAIN-median wick distance, PLUS the stated buffer (his 'stop 10
    to 15 pips above this wick' — buffer approximates the pip cushion as
    a %). median(x) + c == median(x + c) for constant c, so the buffer is
    added once after taking the median rather than per-trade."""
    mask = entry_mask.iloc[:i_tr].fillna(False)
    vals = distance_pct.iloc[:i_tr][mask.to_numpy()].dropna()
    vals = vals[vals > 0]
    if len(vals) == 0:
        return None
    raw = float(vals.median())
    return float(min(max(raw + buffer_pct, floor), cap))


def retest_touch_entries(armed_long, armed_short, touch_long, touch_short):
    """Ablation (a) engine: step73_video.py's retest_confirm_entries with
    the engulf2 confirmation gate DROPPED — enters on the very first
    retest touch inside the armed window. Tests whether his signature
    'engulf the last two candlesticks minimum' rule earns its keep, or
    whether break+retest alone is already the whole edge."""
    n = len(armed_long)
    al, as_ = armed_long.to_numpy(), armed_short.to_numpy()
    tl, ts = touch_long.to_numpy(), touch_short.to_numpy()
    entry_long = np.zeros(n, dtype=bool)
    entry_short = np.zeros(n, dtype=bool)
    touched_l = touched_s = False
    for i in range(n):
        if al[i]:
            if not touched_l and tl[i]:
                entry_long[i] = True
                touched_l = True
        else:
            touched_l = False
        if as_[i]:
            if not touched_s and ts[i]:
                entry_short[i] = True
                touched_s = True
        else:
            touched_s = False
    idx = armed_long.index
    return pd.Series(entry_long, index=idx), pd.Series(entry_short, index=idx)


def apply_trend_filter(d, entry_long, entry_short, on):
    """Ablation (c) engine: a 200-day SMA higher-timeframe-trend gate.
    on=True keeps only WITH-TREND entries (long if close>SMA200, short if
    close<SMA200 at the entry bar) — tests his own claim (ch. 20,
    'Reversal Patterns') that against-trend reversal trades work about as
    well as with-trend continuation trades. on=False is the identity
    (both directions allowed, unrestricted by long-term trend)."""
    if not on:
        return entry_long, entry_short
    sma200 = d["close"].rolling(200).mean()
    long_ok = (d["close"] > sma200).fillna(False)
    short_ok = (d["close"] < sma200).fillna(False)
    return (entry_long & long_ok), (entry_short & short_ok)


# ---------------------------------------------------------------------------
# data loading
# ---------------------------------------------------------------------------

def load_yf_daily(tag, symbol):
    fname = f"data_fx_{tag}_1d.parquet"
    try:
        d = pd.read_parquet(fname)
        print(f"  cached {fname}: {len(d)} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> {d['timestamp'].iloc[-1]:%Y-%m-%d}")
    except FileNotFoundError:
        print(f"  fetching {symbol} 1d (max) via yfinance...")
        d = _fetch_yf(symbol, "1d", "max")
        d.to_parquet(fname)
        print(f"  saved: {len(d)} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> {d['timestamp'].iloc[-1]:%Y-%m-%d}")
    return d


def load_btc_daily():
    d = pd.read_parquet("data_bitstamp_BTCUSD_1d_2011.parquet")
    print(f"  BTC (bitstamp, repo's deep cache): {len(d)} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> {d['timestamp'].iloc[-1]:%Y-%m-%d}")
    return d


# ---------------------------------------------------------------------------
# gauntlet plumbing (adapted from step73_video.py's score/verdict/mk_row)
# ---------------------------------------------------------------------------

def score(d, sig, costs, i_tr, i_va, stop_pct=None, target_pct=None):
    def run(lo, hi):
        return run_backtest(d.iloc[lo:hi].reset_index(drop=True),
                             sig.iloc[lo:hi].reset_index(drop=True),
                             costs=costs, execution="taker",
                             stop_pct=stop_pct, target_pct=target_pct)
    return run(0, i_tr), run(i_tr, i_va)


def verdict_for(tr, va):
    tr_n, va_n = len(tr.trades), len(va.trades)
    if tr.expectancy > 0 and va.expectancy > 0 and tr_n >= MIN_TRAIN_TRADES and va_n >= MIN_VAL_TRADES:
        return "SURVIVOR"
    if tr_n < MIN_TRAIN_TRADES or va_n < MIN_VAL_TRADES:
        return "INSUFFICIENT-SAMPLE"
    return "FAIL"


def rr_stats(tr, va):
    trades = list(tr.trades) + list(va.trades)
    if not trades:
        return float("nan"), float("nan"), float("nan"), float("nan")
    wins = [t.pnl for t in trades if t.pnl > 0]
    losses = [t.pnl for t in trades if t.pnl <= 0]
    win_rate = len(wins) / len(trades) * 100
    avg_win = float(np.mean(wins)) if wins else float("nan")
    avg_loss = float(np.mean(losses)) if losses else float("nan")
    rr = abs(avg_win / avg_loss) if losses and avg_loss != 0 else float("nan")
    return win_rate, avg_win, avg_loss, rr


def trades_per_year(d, tr, va, i_va):
    n_trades = len(tr.trades) + len(va.trades)
    span_days = (d["timestamp"].iloc[i_va - 1] - d["timestamp"].iloc[0]).total_seconds() / 86400
    return n_trades / span_days * 365.25 if span_days > 0 else float("nan")


def mk_row(dataset, cfg, tr, va, stop_pct, target_pct, d, i_va):
    win_rate, avg_win, avg_loss, rr = rr_stats(tr, va)
    return {
        "dataset": dataset, "config": cfg,
        "stop%": stop_pct, "target%": target_pct,
        "tr_n": len(tr.trades), "tr_exp": tr.expectancy, "tr_win%": tr.win_rate * 100,
        "tr_ret%": tr.total_return_pct, "tr_dd%": tr.max_drawdown_pct,
        "va_n": len(va.trades), "va_exp": va.expectancy, "va_win%": va.win_rate * 100,
        "va_ret%": va.total_return_pct, "va_dd%": va.max_drawdown_pct,
        "pooled_win%": win_rate, "pooled_RR": rr,
        "tr/yr": trades_per_year(d, tr, va, i_va),
        "verdict": verdict_for(tr, va),
    }


def no_entries_row(dataset, cfg):
    return {"dataset": dataset, "config": cfg, "stop%": None, "target%": None,
            "tr_n": 0, "tr_exp": np.nan, "tr_win%": np.nan, "tr_ret%": np.nan, "tr_dd%": np.nan,
            "va_n": 0, "va_exp": np.nan, "va_win%": np.nan, "va_ret%": np.nan, "va_dd%": np.nan,
            "pooled_win%": np.nan, "pooled_RR": np.nan, "tr/yr": np.nan, "verdict": "NO-ENTRIES"}


# ---------------------------------------------------------------------------
# core: build a full-stack (or ablated) entry pair for one (mode,k,window)
# ---------------------------------------------------------------------------

def build_ctx(d, k):
    """Body-based bos_chain — his 'do not take the wicks into account'
    structure rule. bos_chain() itself is UNMODIFIED, imported from
    step56_smc_toolkit; body_frame() UNMODIFIED, imported from
    step73_video."""
    return bos_chain(body_frame(d), k)


def armed_and_touch(d, ctx, mode, window_bars):
    bh = bar_hours(d)
    EVENT_LONG = {"reversal": ctx["choch_long"], "continuation": ctx["cont_long"], "both": ctx["bos_up"]}
    EVENT_SHORT = {"reversal": ctx["choch_short"], "continuation": ctx["cont_short"], "both": ctx["bos_down"]}
    armed_long, level_long = merge_event_recency_with_value(
        d["timestamp"], d["timestamp"], EVENT_LONG[mode], ctx["lsh"], bh, window_bars, bh)
    armed_short, level_short = merge_event_recency_with_value(
        d["timestamp"], d["timestamp"], EVENT_SHORT[mode], ctx["lsl"], bh, window_bars, bh)
    close = d["close"]
    touch_long = (armed_long & ((close - level_long).abs() / level_long * 100 <= TOL_PCT)).fillna(False)
    touch_short = (armed_short & ((close - level_short).abs() / level_short * 100 <= TOL_PCT)).fillna(False)
    return armed_long, armed_short, touch_long, touch_short


def run_one_config(d, i_tr, i_va, k, el, es, buffer_pct, r_list, costs, dataset, cfg_prefix):
    """Given a finished (el, es) entry-signal pair, size the stop off
    TRAIN wick-distance + buffer, sweep R, run the gauntlet, return rows."""
    rows = []
    entry_mask = (el | es)
    dist_long, dist_short = stop_distance_pct_wick(d, k, el, es)
    dist_combined = dist_long.where(el.to_numpy(), dist_short)
    stop_pct = train_median_stop_pct(entry_mask, dist_combined, i_tr, buffer_pct)
    if stop_pct is None:
        rows.append(no_entries_row(dataset, f"{cfg_prefix} buf={buffer_pct} R=*"))
        return rows
    mh_bars = int(days_to_bars(d, MAX_HOLD_DAYS))
    for rmult in r_list:
        target_pct = round(stop_pct * rmult, 4)
        sig = day_trade_signal(d, el, es, mh_bars)
        tr, va = score(d, sig, costs, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
        cfg = f"{cfg_prefix} buf={buffer_pct} R={rmult:.1f}"
        rows.append(mk_row(dataset, cfg, tr, va, stop_pct, target_pct, d, i_va))
    return rows


def gauntlet_instrument(tag, d, costs):
    rows = []
    n, i_tr, i_va = split_points(d)
    print(f"  {tag}: n={n} bars, train=[0:{i_tr}] ({i_tr} bars), val=[{i_tr}:{i_va}] ({i_va - i_tr} bars), "
          f"test sealed=[{i_va}:{n}] ({n - i_va} bars, never touched)")

    # ---------------- STAGE 1: the literal config, full sensitivity sweep ----------------
    for mode in ("reversal", "continuation", "both"):
        for k in K_LIST:
            ctx = build_ctx(d, k)
            engulf_bull, engulf_bear = engulf2_events(d)
            for window in WINDOW_LIST:
                armed_long, armed_short, touch_long, touch_short = armed_and_touch(d, ctx, mode, window)
                el, es = retest_confirm_entries(armed_long, armed_short, touch_long, touch_short,
                                                 engulf_bull, engulf_bear)
                for buffer_pct in BUFFER_LIST:
                    cfg_prefix = f"main mode={mode} k={k} w={window}"
                    rows.extend(run_one_config(d, i_tr, i_va, k, el, es, buffer_pct, R_LIST,
                                                costs, tag, cfg_prefix))

    # ---------------- STAGE 2: component ablations (fixed rep point, mode=both) ----------------
    ctx_rep = build_ctx(d, REP_K)
    engulf_bull, engulf_bear = engulf2_events(d)
    armed_long, armed_short, touch_long, touch_short = armed_and_touch(d, ctx_rep, "both", REP_W)

    # (a) no_engulf — retest required, engulf DROPPED
    el, es = retest_touch_entries(armed_long, armed_short, touch_long, touch_short)
    rows.extend(run_one_config(d, i_tr, i_va, REP_K, el, es, REP_BUF, R_LIST, costs, tag,
                                f"ablation(a)-no_engulf mode=both k={REP_K} w={REP_W}"))

    # (b) breakout — retest DROPPED entirely, enter at break
    el, es = breakout_entries(armed_long, armed_short)
    rows.extend(run_one_config(d, i_tr, i_va, REP_K, el, es, REP_BUF, R_LIST, costs, tag,
                                f"ablation(b)-breakout(no_retest) mode=both k={REP_K}"))

    # (c) trend_filter=on — full stack + 200-SMA with-trend gate
    el, es = retest_confirm_entries(armed_long, armed_short, touch_long, touch_short,
                                     engulf_bull, engulf_bear)
    el, es = apply_trend_filter(d, el, es, True)
    rows.extend(run_one_config(d, i_tr, i_va, REP_K, el, es, REP_BUF, R_LIST, costs, tag,
                                f"ablation(c)-trend_filter_on mode=both k={REP_K} w={REP_W}"))

    return rows


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("=" * 90)
    print("ROUND 74 — STRUCTURE -> RETEST -> ENGULFING: the fair (daily, 20yr) test")
    print("=" * 90)

    all_rows = []

    print("\n--- loading FOREX (his own most-traded pairs, yfinance daily max) ---")
    fx_frames = {}
    for tag, sym in FX_TAGS.items():
        print(f"  {tag} ...")
        fx_frames[tag] = load_yf_daily(tag, sym)

    print("\n--- loading GOLD (GC=F, claimed commodity market) ---")
    gold_d = load_yf_daily("GC", "GC=F")

    print("\n--- loading SPY (cross-market equity check) ---")
    spy_d = load_yf_daily("SPY", "SPY")

    print("\n--- loading BTC (repo's deep bitstamp cache, crypto arm) ---")
    btc_d = load_btc_daily()

    frames = dict(fx_frames)
    frames["GOLD"] = gold_d
    frames["SPY"] = spy_d
    frames["BTC"] = btc_d

    costs_by_tag = {tag: FOREX_COSTS for tag in FX_TAGS}
    costs_by_tag["GOLD"] = GOLD_COSTS
    costs_by_tag["SPY"] = SPY_COSTS
    costs_by_tag["BTC"] = BTC_COSTS

    print("\n--- TRUE DATA SPANS ---")
    span_rows = []
    for tag, d in frames.items():
        span_years = (d["timestamp"].iloc[-1] - d["timestamp"].iloc[0]).days / 365.25
        span_rows.append({"instrument": tag, "bars": len(d),
                           "start": str(d["timestamp"].iloc[0].date()),
                           "end": str(d["timestamp"].iloc[-1].date()),
                           "years": round(span_years, 1)})
        print(f"  {tag}: {len(d)} bars, {d['timestamp'].iloc[0].date()} -> {d['timestamp'].iloc[-1].date()} "
              f"({span_years:.1f} years)")
    pd.DataFrame(span_rows).to_csv("step74_data_spans.csv", index=False)

    print("\n--- GAUNTLET ---")
    for tag, d in frames.items():
        print(f"\n  === {tag} ===")
        rows = gauntlet_instrument(tag, d, costs_by_tag[tag])
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    df.to_csv("step74_gauntlet_full.csv", index=False)
    print(f"\nTotal configs run: {len(df)}")

    survivors = df[df["verdict"] == "SURVIVOR"].sort_values("va_exp", ascending=False)
    print("\n--- SURVIVORS (train+val positive, floors met — sealed test NOT touched) ---")
    print(survivors.to_string(index=False) if len(survivors) else "  none")

    print("\n--- verdict counts overall ---")
    print(df["verdict"].value_counts().to_string())

    print("\n--- verdict counts per instrument ---")
    print(df.groupby(["dataset", "verdict"]).size().to_string())

    print("\nDone. See step74_results.md for the full writeup.")
    return df, survivors


if __name__ == "__main__":
    main()
