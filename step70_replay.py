"""
step70_replay.py — ROUND 70: THE WALK-FORWARD REPLAY EXAM.

Research only. Writes step70_replay.py (this file), step70_results.md,
step70_trades_btc.csv, step70_trades_oil.csv, step70_trades_spx.csv.
No commits, no live orders, no state file writes.

WHAT THIS DOES
===============
Replays the CURRENT validated brain (the tools actually frozen in the live
book files / the most recently sealed-passed research configs) bar-by-bar
through history, using ONLY information available as of each bar's own
close (no lookahead), and reports the dollar PnL a $250-margin-per-trade
account would have made. Three markets, reported separately: BTC, OIL,
S&P (SPY).

METHODOLOGY, STATED PLAINLY (read this before trusting a number)
==================================================================
1. SIGNAL CONSTRUCTION reuses the repo's own frozen, already-audited pure
   functions wherever they exist and are import-safe (step56_smc_toolkit,
   step58_divergence_mtf, step45b_news_events, strategy.py, gold_book.py's
   own ported swing-floor logic) rather than re-deriving them by hand —
   the whole point of a walk-forward exam is running the SAME brain, not
   a reinterpretation of it. Every one of those functions is written with
   an explicit no-lookahead contract in its own docstring (shift-by-k
   confirmation, rolling().shift(1) channels, etc.) which this script
   trusts and does not re-verify line by line.
2. ENTRY FILL PRICE = the signal bar's own CLOSE. This mirrors how the
   live daemon books actually behave (gold_book/diver/newsdesk all decide
   from a just-closed bar and fire a market order within seconds), and is
   simpler than backtest.py's generic next-bar-open convention. Stated
   plainly: this is slightly optimistic vs a "wait for the next bar to
   open" convention, and slightly pessimistic vs "maker leg, taker chase"
   (which the original research sometimes used). One consistent rule,
   applied identically to every tool and every market.
   15m ENTRY-TIMING NOTE (owner scope addition, "do the fifteen minute
   too", part 2): every 1h/4h BTC tool's own coarse bar boundary IS
   already a 15m-grid boundary (BTC 1h/4h bars close exactly on 15m
   candle closes), so "fill at the signal bar's own close" and "fill at
   the first 15m close after signal" are the IDENTICAL timestamp and
   price for every tool here — there is no daylight between the two
   conventions to model separately. Stated explicitly rather than
   silently assumed: T-DIVER (4h), T-CHOCH/T-STRIKES/T-FORENSIC/T-NEWS
   (1h) all already get the finer-grained answer for free from point 2.
   T-DONCH (BTC daily, yfinance) is the one tool where this genuinely
   matters and genuinely can't be resolved: yfinance daily BTC-USD starts
   2016, four years before BTC 15m bybit coverage begins (2020-03-25) —
   sub-daily fill timing for T-DONCH's pre-2020 entries is not
   reconstructable here and stays at daily-close resolution, stated
   plainly rather than faked.
3. EXIT / FILL FIDELITY: fixed stop/target tools (T-DIVER, T-CHOCH,
   T-STRIKES, T-FORENSIC) scan bar-by-bar from the bar AFTER entry. When a
   bar's low/high shows BOTH the stop and the target were touchable, this
   is genuinely ambiguous at 1h/4h resolution — the OWNER'S OWN SCOPE
   ADDITION ("do the fifteen minute too") asks this to be resolved with
   real path order, not assumed. For every BTC tool (15m bybit coverage
   is 2020-03-25 -> today, i.e. the full span of all four of these
   tools), this script walks the 15m sub-bars inside that hour/4h window
   IN ORDER and takes whichever level a 15m bar's own high/low actually
   reaches first; "stop wins ties" is now only the FALLBACK for the rare
   bar with no 15m coverage (should be ~none for these four). The
   honesty delta — how many trade outcomes this ACTUALLY changed vs the
   coarse stop-wins-ties convention — is measured and reported per tool
   in step70_results.md, not asserted. Structure-trailing tools
   (T-DONCH, T-NEWS/N2, and the OIL/SPX donchian tools) have only ONE
   exit condition (the floor), so there is no dual-touch ambiguity to
   resolve in the first place — noted, not glossed over. OIL and SPX 1h
   tools (O-1H, SP-1H) stay on the coarse stop-wins-ties convention: the
   free yfinance feed only has ~60 days of 15m history for SPY/CL=F,
   nowhere near the ~730-day 1h window being replayed, and this script
   does not fake finer data it doesn't have (owner's explicit
   instruction) — their results are flagged with the coarser convention
   in the results doc, not silently upgraded.
4. SIZING (owner's spec): margin $250/trade, leverage = min(20, max(10,
   floor(85/stop_pct))), notional = 250*leverage, non-compounding (each
   trade sizes off a flat $250, not off a growing account — this is "the
   PnL a $250-per-trade account would have made" as literally asked, not
   a compounding equity curve).
   - For tools with a real fixed stop_pct (T-DIVER, T-STRIKES, T-FORENSIC,
     T-CHOCH), that frozen number sizes leverage directly.
   - For structure-trailing tools (T-DONCH, O-DONCH, O-1H, SP-DONCH,
     SP-1H, T-NEWS/N2), stop_pct = the entry-to-initial-floor % distance
     AT ENTRY, before any ratchet — a real, honest number (where the
     protective stop actually sits the moment the trade opens).
   - For the two NO-STOP dip-buy tools (O-DIP, SP-DIP — R60's sealed
     config rides to a signal exit with no protective stop at all), there
     is no real stop_pct to size off. This script uses the FLOOR of the
     owner's own leverage band (10x) for these two tools only, flagged
     here explicitly rather than buried in a footnote.
5. COSTS: crypto taker 6bps/leg (BTC book), oil futures-proxy 2bps/leg
   (OIL book), ETF 1bp/leg (SPX book, per the owner's scope addition).
   Funding applied for BTC perp tools where real funding data exists
   (data_bybit_BTCUSDT_funding.parquet, 8h settlements, signed by
   direction — longs pay positive funding, shorts collect it), prorated
   over the exact hours held. No funding on daily-bar tools (T-DONCH,
   O-DONCH, O-DIP, SP-DONCH, SP-DIP) or on OIL/SPX 1h tools (no futures-
   funding data cached for those instruments here — stated, not silently
   omitted).
6. ONE POSITION PER TOOL, MULTIPLE TOOLS CONCURRENTLY: each tool's engine
   holds at most one open trade at a time (no pyramiding within a tool).
   Different tools in the same market book CAN be open simultaneously —
   this is "one shared account, multiple concurrent positions allowed
   only across different tools" exactly as specified. The shared-account
   equity curve (for drawdown) is built by sorting every tool's closed
   trades, across the whole book, by EXIT time, and cumulatively summing
   realized dollar PnL — sequence-honest, not each tool scored alone.
7. SELECTION-BIAS / OVERLAP TAGGING (mandatory, see step70_results.md
   top): every tool here was built and selected using research windows
   that sit INSIDE the very history being replayed. Years are tagged:
     [in-sample-overlap]  — inside the ORIGINAL tool's own TRAIN window
     [val-overlap]        — inside the ORIGINAL tool's own VAL window
     [sealed-overlap]     — inside the ORIGINAL tool's own SEALED/TEST
                             window (walled off during selection, but
                             checked once — distinct from never-looked-at)
     [transfer-assumption]— the tool was validated on a DIFFERENT
                             instrument entirely (e.g. donchian20+
                             structure-trail was sealed-validated on GOLD,
                             never on BTC/OIL/SPX) and applied here on
                             faith — no in-sample/val/sealed split
                             applies because this exact instrument was
                             never part of that tool's own research at
                             all. This is its own, SEPARATE caveat axis,
                             not a synonym for "clean".
     [clean]               — genuinely pre-dates or post-dates every
                             research window this repo has ever run for
                             this tool on this instrument (pre-2019 BTC
                             daily; most of OIL/BTC history for donchian
                             transfer tools once you set aside the
                             transfer caveat; the small span after a
                             tool's own sealed-test window ends).
   Where an exact original train/val/sealed date boundary is not
   recorded in a live production file (most tools were built as one-off
   research scripts, not re-run here), this script approximates the
   boundary with the SAME 60/20/20 chronological split
   (step43_daytrade.split_points) applied to THIS SAME instrument/
   timeframe's full history as loaded here — stated as an
   approximation, not a claim of the exact original date.

Run: python3 step70_replay.py
"""
from __future__ import annotations

import math
import warnings
from datetime import timedelta

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# -- reused, frozen, pure repo functions (see module docstring point 1) ----
import strategy
from strategy import rsi as _rsi, atr as _atr, vol_gated_ma
from step41_shorts import confirmed_swings, last_n_confirmed
from step43_daytrade import CHAMP_KW, champ_aligned, hours_to_bars as _hours_to_bars_43
from step56_smc_toolkit import (
    bos_chain, equilibrium, liquidity_pools, sweep_events, fvg_signals,
    leg_tracker, fib_entries, train_median_stop_pct, bias_series_4h,
    STOP_CAP_PCT as S56_STOP_CAP, STOP_FLOOR_PCT as S56_STOP_FLOOR,
    CONF_TOL, CONF_DEPTH, CONF_FILL, CONF_EXPIRE_DAYS, CONF_FIB_EXPIRE_DAYS,
    CONF_HOLD_DAYS,
)
from step58_divergence_mtf import divergence_events, STOP_CAP_SWING
from step45b_news_events import classify_headline, align_events

pd.set_option("display.width", 160)

SCRATCH = "/Users/wallacechen/cryptobot"


def split_points(d):
    n = len(d)
    return n, int(n * 0.6), int(n * 0.8)


def days_to_bars(d, days):
    t = pd.DatetimeIndex(d["timestamp"])
    bar_h = float((t[1:] - t[:-1]).total_seconds().min() / 3600)
    return max(1, round(days * 24 / bar_h))


def hours_to_bars(d, hours):
    return _hours_to_bars_43(d, hours)


# ===========================================================================
# DATA LOADING
# ===========================================================================

def load_btc_daily_yf():
    import yfinance as yf
    df = yf.Ticker("BTC-USD").history(period="max", interval="1d")
    df = df.reset_index().rename(columns={
        "Date": "timestamp", "Open": "open", "High": "high",
        "Low": "low", "Close": "close", "Volume": "volume"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df[df["timestamp"] >= pd.Timestamp("2016-01-01", tz="UTC")]
    return df[["timestamp", "open", "high", "low", "close", "volume"]].sort_values(
        "timestamp").reset_index(drop=True)


def load_bybit(tf):
    df = pd.read_parquet(f"{SCRATCH}/data_bybit_BTCUSDT_{tf}_full.parquet")
    return df.sort_values("timestamp").reset_index(drop=True)


def load_funding():
    df = pd.read_parquet(f"{SCRATCH}/data_bybit_BTCUSDT_funding.parquet")
    return df.sort_values("timestamp").reset_index(drop=True)


def align_funding_to(d, funding):
    """Most-recent-known funding_bps as of each bar's own timestamp (no
    lookahead — merge_asof backward)."""
    f = pd.merge_asof(
        pd.DataFrame({"timestamp": d["timestamp"]}).sort_values("timestamp"),
        funding.sort_values("timestamp"), on="timestamp", direction="backward")
    return f["funding_bps"]


def load_yf(ticker, interval, period):
    import yfinance as yf
    df = yf.Ticker(ticker).history(period=period, interval=interval)
    df = df.reset_index().rename(columns={
        "Date": "timestamp", "Datetime": "timestamp", "Open": "open",
        "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.dropna(subset=["open", "high", "low", "close"])
    return df[["timestamp", "open", "high", "low", "close", "volume"]].sort_values(
        "timestamp").drop_duplicates("timestamp").reset_index(drop=True)


def load_watcherguru():
    df = pd.read_parquet(f"{SCRATCH}/data_watcherguru_history.parquet")
    df = df.sort_values("utc_timestamp").reset_index(drop=True)
    df["utc_timestamp"] = pd.to_datetime(df["utc_timestamp"], utc=True)
    return df


# ===========================================================================
# GENERIC SWING-PIVOT / STRUCTURE-TRAIL ENGINE
# (ported verbatim from gold_book.py's _find_swing_lows/_compute_trail_floor
#  — R59 sealed-validated shape, reused here for every donchian+structure-
#  trail tool, long side only, per the owner's brief: "these tools fire
#  per its own live/validated rule")
# ===========================================================================

def _find_swing_extreme(arr, k, is_low=True):
    n = len(arr)
    confirm_idx, price = [], []
    for j in range(k, n - k):
        window = arr[j - k:j + k + 1]
        ok = (arr[j] <= window.min()) if is_low else (arr[j] >= window.max())
        if ok:
            confirm_idx.append(j + k)
            price.append(arr[j])
    return np.array(confirm_idx, dtype=int), np.array(price, dtype=float)


def donchian_structure_trail(d, entry_n=20, k_swing=5, crash_sl_pct=0.18,
                              fee_bps=6.0):
    """Long-only donchian(entry_n) breakout with a ratcheting structure-
    trailing floor exit (R59 exact shape, gold_book.py). One position at a
    time. Entry fires on the FIRST bar whose close breaks the prior
    entry_n-bar high; fills at that bar's own close (see module docstring
    point 2). Floor recomputed fresh every bar from confirmed swing lows
    (k=k_swing) after entry; exits the bar a low trades at/through it,
    fill AT the floor price. Crash-SL fallback (crash_sl_pct below entry)
    when no confirmed swing low exists below entry yet."""
    close = d["close"].to_numpy()
    high = d["high"].to_numpy()
    low = d["low"].to_numpy()
    ts = pd.DatetimeIndex(d["timestamp"])
    n = len(d)

    hi_roll = d["high"].rolling(entry_n).max().shift(1).to_numpy()
    breakout = (~np.isnan(hi_roll)) & (close > hi_roll)

    confirm_idx, piv_price = _find_swing_extreme(low, k_swing, is_low=True)

    trades = []
    i = 0
    while i < n:
        if breakout[i]:
            entry_i = i
            entry_price = close[i]
            entry_time = ts[i]
            # initial floor: most recent confirmed-by-entry swing low below entry
            init = None
            for ci, pr in zip(confirm_idx[::-1], piv_price[::-1]):
                if ci <= entry_i and pr < entry_price:
                    init = pr
                    break
            floor_px = init if init is not None else entry_price * (1 - crash_sl_pct)
            entry_stop_pct = (entry_price - floor_px) / entry_price * 100

            j = entry_i + 1
            exit_i = exit_price = exit_reason = None
            while j < n:
                # ratchet: any confirmed swing low with confirm_idx <= j and
                # confirm_idx > entry_i that beats current floor
                mask = (confirm_idx <= j) & (confirm_idx > entry_i)
                if mask.any():
                    cand = piv_price[mask]
                    cmax = cand.max()
                    if cmax > floor_px:
                        floor_px = float(cmax)
                if low[j] <= floor_px:
                    exit_i, exit_price, exit_reason = j, floor_px, "structure_floor"
                    break
                j += 1
            if exit_i is None:
                exit_i, exit_price, exit_reason = n - 1, close[n - 1], "data_end_open"

            trades.append(dict(
                direction=1, entry_time=entry_time, entry_price=float(entry_price),
                exit_time=ts[exit_i], exit_price=float(exit_price),
                exit_reason=exit_reason, stop_pct=float(max(entry_stop_pct, 0.05)),
                fee_bps=fee_bps))
            i = exit_i + 1
        else:
            i += 1
    return trades


def rsi2_dipbuy_sealed(d, fee_bps=1.0):
    """R60 SEALED-PASSED shape: RSI2<5, price>SMA200 (daily) -> long.
    Exit: close>SMA5 OR RSI2>65. NO fixed stop, no max hold — rides to the
    signal exit exactly (the winning config was 'stop=none hold=nocap').
    Long only, one position at a time."""
    close = d["close"]
    sma200 = close.rolling(200).mean()
    sma5 = close.rolling(5).mean()
    r2 = _rsi(close, 2)
    enter = ((r2 < 5) & (close > sma200)).fillna(False).to_numpy()
    exit_sig = ((close > sma5) | (r2 > 65)).fillna(False).to_numpy()
    ts = pd.DatetimeIndex(d["timestamp"])
    c = close.to_numpy()
    n = len(d)
    trades = []
    i = 0
    while i < n:
        if enter[i]:
            entry_i, entry_price, entry_time = i, c[i], ts[i]
            j = i + 1
            exit_i = None
            while j < n:
                if exit_sig[j]:
                    exit_i = j
                    break
                j += 1
            if exit_i is None:
                exit_i = n - 1
            trades.append(dict(
                direction=1, entry_time=entry_time, entry_price=float(entry_price),
                exit_time=ts[exit_i], exit_price=float(c[exit_i]),
                exit_reason="signal_exit" if exit_i != n - 1 or exit_sig[exit_i] else "data_end_open",
                stop_pct=None, fee_bps=fee_bps))
            i = exit_i + 1
        else:
            i += 1
    return trades


# ===========================================================================
# 15m FILL-FIDELITY RESOLVER (owner scope addition, round 70: "do the
# fifteen minute too"). Wherever a 1h/4h coarse bar shows BOTH the stop and
# the target inside its own high/low range, the coarse convention
# ("stop wins ties") is a MODELING CHOICE, not a fact — the 15m sub-bars
# inside that hour (or 4h window) know the actual chronological path.
# This walks them in order and returns whichever level a 15m bar's own
# high/low actually reaches FIRST; only falls back to stop-wins-ties if
# the 15m cache has a gap for that exact window (never silently assumed
# resolved). BTC 15m coverage is 2020-03-25 -> today, i.e. essentially
# the full span of every 1h/4h tool in this replay (T-DIVER, T-CHOCH,
# T-STRIKES, T-FORENSIC, T-NEWS all start >= 2020-03), so this should
# resolve nearly every ambiguous bar for BTC. OIL/SPX 1h tools stay on
# the coarse convention — SPY/CL=F 15m history is only ~60 days on the
# free feed, nowhere near enough to cover a 730-day 1h window, and this
# script does not fake finer data it doesn't have (owner's explicit
# instruction) — stated here, not buried.
# ===========================================================================

_D15M_CACHE = {"df": None}


def _get_btc_15m():
    # NOTE: pandas quirk — a tz-aware Series' .to_numpy() returns an OBJECT
    # array of Timestamp instances, while a tz-aware DatetimeIndex's .values
    # returns a plain naive datetime64[ns] (UTC-equivalent) array. Mixing
    # the two triggers "Cannot compare tz-naive and tz-aware timestamps" in
    # np.searchsorted. Cache the DatetimeIndex-derived naive array once so
    # every comparison in this module uses the SAME representation.
    if _D15M_CACHE["df"] is None:
        df = pd.read_parquet(f"{SCRATCH}/data_bybit_BTCUSDT_15m_full.parquet")
        df = df.sort_values("timestamp").reset_index(drop=True)
        _D15M_CACHE["df"] = df
        _D15M_CACHE["ts"] = pd.DatetimeIndex(df["timestamp"]).values
    return _D15M_CACHE["df"]


def _get_btc_15m_ts():
    _get_btc_15m()
    return _D15M_CACHE["ts"]


def _resolve_via_15m(d15m_ts, d15m_hi, d15m_lo, bar_start, bar_end, direction,
                      stop_px, tgt_px):
    """Returns 'stop', 'target', or None (no 15m coverage / neither
    touched in the sub-bars found — caller falls back to stop-wins-ties).
    `bar_start`/`bar_end` are the coarse bar's own open/next-open
    timestamps (half-open window [bar_start, bar_end))."""
    lo = np.searchsorted(d15m_ts, np.datetime64(bar_start), side="left")
    hi = np.searchsorted(d15m_ts, np.datetime64(bar_end), side="left")
    if hi <= lo:
        return None
    for k in range(lo, hi):
        if direction > 0:
            hit_stop = d15m_lo[k] <= stop_px
            hit_tgt = d15m_hi[k] >= tgt_px
        else:
            hit_stop = d15m_hi[k] >= stop_px
            hit_tgt = d15m_lo[k] <= tgt_px
        if hit_stop:
            return "stop"
        if hit_tgt:
            return "target"
    return None


# ===========================================================================
# FIXED STOP/TARGET BAR-BY-BAR SIMULATOR (shared by T-DIVER, T-CHOCH,
# T-STRIKES, T-FORENSIC)
# ===========================================================================

def simulate_fixed_bracket(d, enter_long, enter_short, stop_pct, target_pct,
                            max_hold_bars, fee_bps, per_trade_stop_pct=None,
                            use_15m=False, fidelity_stats=None):
    """One position at a time (whichever direction fires first is taken;
    no reversal mid-trade). stop_pct/target_pct may be a single float
    (shared) or a pd.Series indexed like d (per-signal-bar value, e.g.
    CHoCH's per-cell train-median stop). Stop wins ties intrabar UNLESS
    use_15m=True and BTC 15m sub-bar data can resolve the actual path
    order for that specific ambiguous bar (see resolver above).
    `fidelity_stats`, if passed a dict, is updated with
    {"dual_touch_bars": n, "resolved_by_15m": n, "flipped_outcome": n} —
    the honesty-delta the owner asked to see."""
    close = d["close"].to_numpy()
    high = d["high"].to_numpy()
    low = d["low"].to_numpy()
    ts = pd.DatetimeIndex(d["timestamp"])
    bar_ends = np.append(ts.values[1:], ts.values[-1] + (ts.values[-1] - ts.values[-2] if len(ts) > 1 else np.timedelta64(1, "h")))

    d15m_ts = d15m_hi = d15m_lo = None
    if use_15m:
        d15m = _get_btc_15m()
        d15m_ts = _get_btc_15m_ts()
        d15m_hi = d15m["high"].to_numpy()
        d15m_lo = d15m["low"].to_numpy()
    el = enter_long.fillna(False).to_numpy() if hasattr(enter_long, "fillna") else np.asarray(enter_long)
    es = enter_short.fillna(False).to_numpy() if hasattr(enter_short, "fillna") else np.asarray(enter_short)
    n = len(d)

    def get_pct(arr_or_scalar, i):
        if arr_or_scalar is None:
            return None
        if np.isscalar(arr_or_scalar):
            return arr_or_scalar
        v = arr_or_scalar[i] if isinstance(arr_or_scalar, np.ndarray) else arr_or_scalar.iloc[i]
        return float(v) if v == v else None

    stop_arr = stop_pct.to_numpy() if hasattr(stop_pct, "to_numpy") else stop_pct
    tgt_arr = target_pct.to_numpy() if hasattr(target_pct, "to_numpy") else target_pct

    trades = []
    i = 0
    while i < n:
        direction = 1 if el[i] else (-1 if es[i] else 0)
        if direction != 0:
            sp = get_pct(stop_arr, i)
            tp = get_pct(tgt_arr, i)
            if sp is None or tp is None:
                i += 1
                continue
            entry_i, entry_price, entry_time = i, close[i], ts[i]
            if direction > 0:
                stop_px = entry_price * (1 - sp / 100)
                tgt_px = entry_price * (1 + tp / 100)
            else:
                stop_px = entry_price * (1 + sp / 100)
                tgt_px = entry_price * (1 - tp / 100)

            j = entry_i + 1
            exit_i = exit_price = exit_reason = None
            held = 0
            while j < n:
                held += 1
                if direction > 0:
                    hit_stop = low[j] <= stop_px
                    hit_tgt = high[j] >= tgt_px
                else:
                    hit_stop = high[j] >= stop_px
                    hit_tgt = low[j] <= tgt_px
                if hit_stop and hit_tgt:
                    coarse_winner = "stop"     # coarse convention: stop wins ties
                    winner = "stop"
                    if use_15m:
                        if fidelity_stats is not None:
                            fidelity_stats["dual_touch_bars"] += 1
                        resolved = _resolve_via_15m(
                            d15m_ts, d15m_hi, d15m_lo, ts[j].to_datetime64(),
                            bar_ends[j], direction, stop_px, tgt_px)
                        if resolved is not None:
                            winner = resolved
                            if fidelity_stats is not None:
                                fidelity_stats["resolved_by_15m"] += 1
                                if winner != coarse_winner:
                                    fidelity_stats["flipped_outcome"] += 1
                    exit_i = j
                    exit_price = stop_px if winner == "stop" else tgt_px
                    exit_reason = winner
                    break
                if hit_stop:
                    exit_i, exit_price, exit_reason = j, stop_px, "stop"
                    break
                if hit_tgt:
                    exit_i, exit_price, exit_reason = j, tgt_px, "target"
                    break
                if max_hold_bars and held >= max_hold_bars:
                    exit_i, exit_price, exit_reason = j, close[j], "max_hold"
                    break
                j += 1
            if exit_i is None:
                exit_i, exit_price, exit_reason = n - 1, close[n - 1], "data_end_open"

            trades.append(dict(
                direction=direction, entry_time=entry_time, entry_price=float(entry_price),
                exit_time=ts[exit_i], exit_price=float(exit_price),
                exit_reason=exit_reason, stop_pct=float(sp), fee_bps=fee_bps))
            i = exit_i + 1
        else:
            i += 1
    return trades


# ===========================================================================
# T-DIVER — 4h hidden RSI divergence continuation (diver.py frozen config)
# ===========================================================================

def build_t_diver(d4h, fee_bps=6.0):
    champ4h = vol_gated_ma(d4h, **CHAMP_KW)
    osc = _rsi(d4h["close"], 14)
    long_reg, short_reg, long_hid, short_hid, low_ext, high_ext = \
        divergence_events(d4h, osc, 8, champ4h)
    STOP_PCT = 3.540350
    TARGET_PCT = min(3.0 * STOP_PCT, 3 * STOP_CAP_SWING)
    fidelity = {"dual_touch_bars": 0, "resolved_by_15m": 0, "flipped_outcome": 0}
    trades = simulate_fixed_bracket(
        d4h, long_hid, short_hid, STOP_PCT, TARGET_PCT,
        hours_to_bars(d4h, 48), fee_bps, use_15m=True, fidelity_stats=fidelity)
    for t in trades:
        t["tool"] = "T-DIVER"
    return trades, fidelity


# ===========================================================================
# T-CHOCH — 1h CHoCH + confluence>=2 (step56 exact config: k8 CHoCH
# thresh>=2 tgt2x, train-median stop)
# ===========================================================================

def build_t_choch(d1h, frame4h, fee_bps=6.0):
    k = 8
    n, i_tr, i_va = split_points(d1h)
    bos = bos_chain(d1h, k)
    discount, premium, eq, lsh, lsl = equilibrium(d1h, k)
    pool_high, pool_low = liquidity_pools(d1h, k, CONF_TOL)
    sweep_long, sweep_short = sweep_events(d1h, pool_high, pool_low, CONF_DEPTH)
    window = hours_to_bars(d1h, 24)
    swept_recent_long = (sweep_long.astype(int).rolling(window, min_periods=1)
                          .max().fillna(0).astype(bool))
    swept_recent_short = (sweep_short.astype(int).rolling(window, min_periods=1)
                           .max().fillna(0).astype(bool))
    el_fvg, es_fvg, dl_fvg, ds_fvg, ab, ar = fvg_signals(
        d1h, CONF_FILL, days_to_bars(d1h, CONF_EXPIRE_DAYS))
    bull_low, bull_high, bear_low, bear_high = leg_tracker(
        d1h, k, days_to_bars(d1h, CONF_FIB_EXPIRE_DAYS))
    el_fib, es_fib, dl_fib, ds_fib, extl, exts, lz, sz = fib_entries(
        d1h, bull_low, bull_high, bear_low, bear_high, 0.618, 0.79)

    bias4h = bias_series_4h(frame4h)
    bias_1h = champ_aligned(frame4h, bias4h, d1h)

    dist_bos_long = (d1h["close"] - bos["lsl"]) / d1h["close"] * 100
    dist_bos_short = (bos["lsh"] - d1h["close"]) / d1h["close"] * 100

    bias_long = (bias_1h == 1)
    bias_short = (bias_1h == -1)
    count_long = (bias_long.astype(int) + discount.astype(int) + lz.astype(int)
                  + swept_recent_long.astype(int) + ab.astype(int))
    count_short = (bias_short.astype(int) + premium.astype(int) + sz.astype(int)
                   + swept_recent_short.astype(int) + ar.astype(int))

    choch_long, choch_short = bos["choch_long"], bos["choch_short"]
    el = choch_long & (count_long >= 2)
    es = choch_short & (count_short >= 2)
    mask = el | es
    dist = pd.Series(np.nan, index=d1h.index)
    dist = dist.mask(el, dist_bos_long)
    dist = dist.mask(es, dist_bos_short)
    stop_pct = train_median_stop_pct(d1h, i_tr, mask, dist, cap=S56_STOP_CAP,
                                      floor=S56_STOP_FLOOR)
    if stop_pct is None:
        return [], None, None, None, {}
    target_pct = stop_pct * 2.0
    mh_bars = days_to_bars(d1h, CONF_HOLD_DAYS)
    fidelity = {"dual_touch_bars": 0, "resolved_by_15m": 0, "flipped_outcome": 0}
    trades = simulate_fixed_bracket(d1h, el, es, stop_pct, target_pct, mh_bars, fee_bps,
                                     use_15m=True, fidelity_stats=fidelity)
    for t in trades:
        t["tool"] = "T-CHOCH"
    return trades, stop_pct, target_pct, (i_tr, i_va, n), fidelity


# ===========================================================================
# T-STRIKES — daily_pick's washout rule, ported exactly from daily_pick.py
# (RSI3(1h) vs the ACTUAL live thresholds: <10 long / >90 short — NOTE the
# owner's brief said "<15"; the live source code says <10. This script
# follows the SOURCE CODE, since the whole point of round 70 is "port
# exactly," and flags the discrepancy loudly here and in the results doc.)
# ===========================================================================

STRIKES_RSI_LOW = 10.0
STRIKES_RSI_HIGH = 90.0


def build_t_strikes(d1h, d1d, fee_bps=6.0):
    close1h = d1h["close"]
    open1h = d1h["open"]
    r3 = _rsi(close1h, 3)
    atr14 = _atr(d1h, 14)
    atr_pct = (atr14 / close1h * 100)

    # daily trend_1d state aligned onto 1h, no lookahead (asof-merge on the
    # daily bar's own close time — a daily bar's trend is knowable only
    # once it has closed)
    sma20_1d = d1d["close"].rolling(20).mean()
    sma50_1d = d1d["close"].rolling(50).mean()
    trend_up_1d = (d1d["close"] > sma20_1d) & (sma20_1d > sma50_1d)
    trend_dn_1d = (d1d["close"] < sma20_1d) & (sma20_1d < sma50_1d)
    daily = pd.DataFrame({"timestamp": d1d["timestamp"], "trend_up": trend_up_1d,
                          "trend_dn": trend_dn_1d}).sort_values("timestamp")
    aligned = pd.merge_asof(
        pd.DataFrame({"timestamp": d1h["timestamp"]}).sort_values("timestamp"),
        daily, on="timestamp", direction="backward")
    trend_up = aligned["trend_up"].fillna(False).to_numpy()
    trend_dn = aligned["trend_dn"].fillna(False).to_numpy()

    turn_up = ((close1h > open1h) & (close1h > close1h.shift(1))).fillna(False).to_numpy()
    turn_dn = ((close1h < open1h) & (close1h < close1h.shift(1))).fillna(False).to_numpy()

    r3v = r3.to_numpy()
    enter_long = (r3v < STRIKES_RSI_LOW) & trend_up & turn_up
    enter_short = (r3v > STRIKES_RSI_HIGH) & trend_dn & turn_dn
    enter_long = pd.Series(enter_long, index=d1h.index).fillna(False)
    enter_short = pd.Series(enter_short, index=d1h.index).fillna(False)

    stop_pct = (atr_pct * 1.0).clip(upper=1.0).clip(lower=0.05)
    target_pct = stop_pct * 1.5
    fidelity = {"dual_touch_bars": 0, "resolved_by_15m": 0, "flipped_outcome": 0}
    trades = simulate_fixed_bracket(
        d1h, enter_long, enter_short, stop_pct, target_pct,
        hours_to_bars(d1h, 4), fee_bps, use_15m=True, fidelity_stats=fidelity)
    for t in trades:
        t["tool"] = "T-STRIKES"
    return trades, fidelity


# ===========================================================================
# T-NEWS — WatcherGuru first-bar-move entry + N2 structure trailing exit
# (newsdesk.py's live N2 shape, TRAIL_K=5, TRAIL_BUFFER_PCT=0.3%, 24h cap).
# Restricted to the WatcherGuru harvested span (news_min-24h -> news_max+24h)
# ===========================================================================

def build_t_news(d1h, headlines, fee_bps=6.0):
    tagged = headlines.copy()
    cls = tagged["text"].apply(classify_headline)
    tagged["relevant"] = cls.apply(lambda x: x["relevant"])
    relevant = tagged[tagged["relevant"]]
    if len(relevant) == 0:
        return [], None, None

    news_min, news_max = headlines["utc_timestamp"].min(), headlines["utc_timestamp"].max()
    span_lo = news_min - pd.Timedelta(hours=24)
    span_hi = news_max + pd.Timedelta(hours=24)
    d = d1h[(d1h["timestamp"] >= span_lo) & (d1h["timestamp"] <= span_hi)].reset_index(drop=True)
    if len(d) < 30:
        return [], span_lo, span_hi

    floor_idx, trading_idx, valid = align_events(d, relevant["utc_timestamp"])
    open_ = d["open"].to_numpy()
    high = d["high"].to_numpy()
    low = d["low"].to_numpy()
    close = d["close"].to_numpy()
    ts = pd.DatetimeIndex(d["timestamp"])
    n = len(d)

    TRAIL_K = 5
    TRAIL_BUFFER_PCT = 0.3
    MAX_HOLD_H = 24
    mh_bars = hours_to_bars(d, MAX_HOLD_H)

    hi_confirm, hi_price = _find_swing_extreme(high, TRAIL_K, is_low=False)
    lo_confirm, lo_price = _find_swing_extreme(low, TRAIL_K, is_low=True)

    events = sorted(set(int(x) for x in trading_idx[valid])) if hasattr(trading_idx, "__len__") else []
    trades = []
    occupied_until = -1
    for tidx in events:
        if tidx <= occupied_until or tidx >= n:
            continue
        entry_i = tidx
        direction = 1 if close[entry_i] > open_[entry_i] else (-1 if close[entry_i] < open_[entry_i] else 0)
        if direction == 0:
            continue
        entry_price = close[entry_i]
        entry_time = ts[entry_i]
        if direction > 0:
            floor_px = low[entry_i] * (1 - TRAIL_BUFFER_PCT / 100)
        else:
            floor_px = high[entry_i] * (1 + TRAIL_BUFFER_PCT / 100)
        entry_stop_pct = abs(entry_price - floor_px) / entry_price * 100

        j = entry_i + 1
        exit_i = exit_price = exit_reason = None
        held = 0
        piv_confirm, piv_price = (lo_confirm, lo_price) if direction > 0 else (hi_confirm, hi_price)
        while j < n:
            held += 1
            mask = (piv_confirm <= j) & (piv_confirm > entry_i)
            if mask.any():
                cand = piv_price[mask]
                if direction > 0:
                    cmax = cand.max()
                    if cmax > floor_px:
                        floor_px = float(cmax)
                else:
                    cmin = cand.min()
                    if cmin < floor_px:
                        floor_px = float(cmin)
            hit = (low[j] <= floor_px) if direction > 0 else (high[j] >= floor_px)
            if hit:
                exit_i, exit_price, exit_reason = j, floor_px, "structure_floor"
                break
            if held >= mh_bars:
                exit_i, exit_price, exit_reason = j, close[j], "max_hold_24h"
                break
            j += 1
        if exit_i is None:
            exit_i, exit_price, exit_reason = n - 1, close[n - 1], "data_end_open"

        trades.append(dict(
            direction=direction, entry_time=entry_time, entry_price=float(entry_price),
            exit_time=ts[exit_i], exit_price=float(exit_price),
            exit_reason=exit_reason, stop_pct=float(max(entry_stop_pct, 0.05)),
            fee_bps=fee_bps, tool="T-NEWS"))
        occupied_until = exit_i
    return trades, span_lo, span_hi


# ===========================================================================
# T-FORENSIC — R66-localized forensic-short (funding>1.5bp & 4h-pop>1.5% &
# ATR14%>1.2%, short only). Per step66_results.md this entry mask lives
# ENTIRELY inside the vol=violent + crowd=crowded-long cells already — no
# additional gating needed, the entry condition IS the gate.
# ===========================================================================

def build_t_forensic(d1h, funding_bps_1h, fee_bps=6.0):
    fund_thresh, atr_thresh, pop_thresh, pop_hours = 1.5, 1.2, 1.5, 4
    pop_bars = hours_to_bars(d1h, pop_hours)
    pop = (d1h["close"] / d1h["close"].shift(pop_bars) - 1) * 100
    atr_pct = _atr(d1h, 14) / d1h["close"] * 100
    f = funding_bps_1h
    enter_short = ((f > fund_thresh) & (pop > pop_thresh) & (atr_pct > atr_thresh)).fillna(False)
    enter_long = pd.Series(False, index=d1h.index)
    fidelity = {"dual_touch_bars": 0, "resolved_by_15m": 0, "flipped_outcome": 0}
    trades = simulate_fixed_bracket(
        d1h, enter_long, enter_short, 1.69, 5.07, hours_to_bars(d1h, 48), fee_bps,
        use_15m=True, fidelity_stats=fidelity)
    for t in trades:
        t["tool"] = "T-FORENSIC"
        t["funding_era_start"] = str(funding_bps_1h.dropna().index.min())
    return trades, fidelity


# ===========================================================================
# SIZING / PnL
# ===========================================================================

def size_and_price_trade(t, funding_series_1h=None, min_lev=10, max_lev=20,
                          margin=250.0):
    sp = t["stop_pct"]
    if sp is None or sp <= 0:
        lev = min_lev
        t["stop_pct_used_for_sizing"] = None
        t["sizing_note"] = "no-stop tool: floor leverage used"
    else:
        lev = min(max_lev, max(min_lev, math.floor(85.0 / sp)))
        t["stop_pct_used_for_sizing"] = sp
        t["sizing_note"] = ""
    notional = margin * lev
    units = notional / t["entry_price"]
    direction = t["direction"]
    gross = units * (t["exit_price"] - t["entry_price"]) * direction
    entry_notional = units * t["entry_price"]
    exit_notional = units * t["exit_price"]
    fee_bps = t["fee_bps"]
    fees = (entry_notional + exit_notional) * fee_bps / 10_000

    funding_cost = 0.0
    if funding_series_1h is not None:
        et, xt = t["entry_time"], t["exit_time"]
        fseg = funding_series_1h[(funding_series_1h["timestamp"] > et) &
                                  (funding_series_1h["timestamp"] <= xt)]
        for _, row in fseg.iterrows():
            funding_cost += entry_notional * row["funding_bps"] / 10_000 * direction

    net = gross - fees - funding_cost
    t.update(dict(leverage=lev, margin=margin, notional=notional, units=units,
                   gross_pnl=gross, fees=fees, funding_cost=funding_cost,
                   net_pnl=net, hold_hours=(t["exit_time"] - t["entry_time"]).total_seconds() / 3600))
    return t


def price_book(trades, funding_series_1h=None, fee_bps_override=None,
                min_lev=10, max_lev=20):
    out = []
    for t in trades:
        t = dict(t)
        if fee_bps_override is not None:
            t["fee_bps"] = fee_bps_override
        out.append(size_and_price_trade(t, funding_series_1h, min_lev, max_lev))
    return out


# ===========================================================================
# STATS
# ===========================================================================

def summarize(trades, label):
    if not trades:
        return dict(label=label, n=0)
    df = pd.DataFrame(trades).sort_values("exit_time").reset_index(drop=True)
    wins = df[df["net_pnl"] > 0]
    losses = df[df["net_pnl"] <= 0]
    df["cum"] = df["net_pnl"].cumsum()
    df["peak"] = df["cum"].cummax()
    df["dd"] = df["peak"] - df["cum"]
    max_dd = df["dd"].max()
    return dict(
        label=label, n=len(df), total_pnl=df["net_pnl"].sum(),
        win_rate=len(wins) / len(df) * 100, avg_win=wins["net_pnl"].mean() if len(wins) else 0.0,
        avg_loss=losses["net_pnl"].mean() if len(losses) else 0.0,
        max_dd=max_dd, df=df)


# ===========================================================================
# SELECTION-BIAS / OVERLAP TAGGING (module docstring point 7)
# ===========================================================================

def split_dates(d):
    n, i_tr, i_va = split_points(d)
    return d["timestamp"].iloc[i_tr], d["timestamp"].iloc[i_va]


def tag_year(entry_time, i_tr_date, i_va_date, clean_before=None, transfer=False):
    if transfer:
        return "transfer-assumption"
    if clean_before is not None and entry_time < clean_before:
        return "clean"
    if entry_time < i_tr_date:
        return "in-sample-overlap"
    if entry_time < i_va_date:
        return "val-overlap"
    return "sealed-overlap"


def apply_tags(trades, i_tr_date, i_va_date, clean_before=None, transfer=False):
    for t in trades:
        t["overlap_tag"] = tag_year(t["entry_time"], i_tr_date, i_va_date,
                                    clean_before, transfer)
    return trades


def year_table(df):
    if df is None or len(df) == 0:
        return pd.DataFrame()
    df = df.copy()
    df["year"] = df["exit_time"].dt.year
    rows = []
    for yr, g in df.groupby("year"):
        tags = g["overlap_tag"].value_counts()
        primary_tag = tags.idxmax()
        wins = g[g["net_pnl"] > 0]
        rows.append(dict(year=yr, n=len(g), pnl=g["net_pnl"].sum(),
                         win_rate=len(wins) / len(g) * 100, tag=primary_tag))
    return pd.DataFrame(rows).sort_values("year")


def clean_sealed_total(df):
    if df is None or len(df) == 0:
        return 0.0, 0
    mask = df["overlap_tag"].isin(["clean", "sealed-overlap"])
    return df.loc[mask, "net_pnl"].sum(), int(mask.sum())


def per_tool_table(df):
    if df is None or len(df) == 0:
        return pd.DataFrame()
    rows = []
    for tool, g in df.groupby("tool"):
        wins = g[g["net_pnl"] > 0]
        rows.append(dict(tool=tool, n=len(g), pnl=g["net_pnl"].sum(),
                         win_rate=len(wins) / len(g) * 100 if len(g) else 0,
                         avg_win=wins["net_pnl"].mean() if len(wins) else 0.0,
                         avg_loss=g[g["net_pnl"] <= 0]["net_pnl"].mean()
                         if len(g[g["net_pnl"] <= 0]) else 0.0))
    return pd.DataFrame(rows).sort_values("pnl", ascending=False)


# ===========================================================================
# RESULTS.MD WRITER
# ===========================================================================

def _fmt_money(x):
    sign = "-" if x < 0 else ""
    return f"{sign}${abs(x):,.2f}"


def _market_section(name, df, fee_note, extra_note=""):
    lines = []
    if df is None or len(df) == 0:
        lines.append(f"No trades fired for {name} — nothing to report.\n")
        return "\n".join(lines)

    total = df["net_pnl"].sum()
    wins = df[df["net_pnl"] > 0]
    losses = df[df["net_pnl"] <= 0]
    win_rate = len(wins) / len(df) * 100
    avg_win = wins["net_pnl"].mean() if len(wins) else 0.0
    avg_loss = losses["net_pnl"].mean() if len(losses) else 0.0

    dd_df = df.sort_values("exit_time").copy()
    dd_df["cum"] = dd_df["net_pnl"].cumsum()
    dd_df["peak"] = dd_df["cum"].cummax()
    dd_df["dd"] = dd_df["peak"] - dd_df["cum"]
    max_dd = dd_df["dd"].max()
    max_dd_date = dd_df.loc[dd_df["dd"].idxmax(), "exit_time"] if len(dd_df) else None

    clean_pnl, clean_n = clean_sealed_total(df)

    lines.append(f"### {name}\n")
    lines.append(f"- **Total trades:** {len(df)}")
    lines.append(f"- **Total net PnL (ALL years, includes overlap):** {_fmt_money(total)}")
    lines.append(f"- **Win rate:** {win_rate:.1f}%")
    lines.append(f"- **Avg win:** {_fmt_money(avg_win)}   **Avg loss:** {_fmt_money(avg_loss)}")
    lines.append(f"- **Max drawdown (sequence-honest, shared-account, $ terms):** "
                 f"{_fmt_money(max_dd)}" + (f" (around {max_dd_date:%Y-%m-%d})" if max_dd_date is not None else ""))
    lines.append(f"- **HONEST HEADLINE — clean + sealed-overlap years only:** "
                 f"{_fmt_money(clean_pnl)} across {clean_n} trades")
    lines.append(f"- Costs: {fee_note}")
    if extra_note:
        lines.append(extra_note)
    lines.append("")

    # per-year table
    yt = year_table(df)
    lines.append("| Year | Trades | Net PnL | Win% | Overlap tag |")
    lines.append("|---|---|---|---|---|")
    for _, row in yt.iterrows():
        lines.append(f"| {int(row['year'])} | {int(row['n'])} | {_fmt_money(row['pnl'])} | "
                     f"{row['win_rate']:.0f}% | [{row['tag']}] |")
    lines.append("")

    # per-tool table
    tt = per_tool_table(df)
    lines.append("| Tool | Trades | Net PnL | Win% | Avg win | Avg loss |")
    lines.append("|---|---|---|---|---|---|")
    for _, row in tt.iterrows():
        lines.append(f"| {row['tool']} | {int(row['n'])} | {_fmt_money(row['pnl'])} | "
                     f"{row['win_rate']:.0f}% | {_fmt_money(row['avg_win'])} | {_fmt_money(row['avg_loss'])} |")
    lines.append("")

    # best/worst 5
    top5 = df.nlargest(5, "net_pnl")
    bot5 = df.nsmallest(5, "net_pnl")
    lines.append("**5 best trades:**\n")
    for _, r in top5.iterrows():
        lines.append(f"- {r['tool']} {'LONG' if r['direction'] > 0 else 'SHORT'} "
                     f"{r['entry_time']:%Y-%m-%d %H:%M} -> {r['exit_time']:%Y-%m-%d %H:%M} "
                     f"({r['exit_reason']}, {r['leverage']:.0f}x, [{r['overlap_tag']}]): "
                     f"{_fmt_money(r['net_pnl'])}")
    lines.append("\n**5 worst trades:**\n")
    for _, r in bot5.iterrows():
        lines.append(f"- {r['tool']} {'LONG' if r['direction'] > 0 else 'SHORT'} "
                     f"{r['entry_time']:%Y-%m-%d %H:%M} -> {r['exit_time']:%Y-%m-%d %H:%M} "
                     f"({r['exit_reason']}, {r['leverage']:.0f}x, [{r['overlap_tag']}]): "
                     f"{_fmt_money(r['net_pnl'])}")
    lines.append("")
    return "\n".join(lines)


def write_results_md(btc_df, oil_df, spx_df, spx_df_4x, fidelity_totals, fidelity_by_tool,
                     splits):
    lines = []
    lines.append("# step70_results.md — ROUND 70: THE WALK-FORWARD REPLAY EXAM\n")
    lines.append("Research only. No live orders, no commits. Generated by `step70_replay.py`.\n")

    lines.append("## SELECTION-BIAS DISCLOSURE — READ THIS FIRST\n")
    lines.append(
        "Every tool replayed below was BUILT and SELECTED using research windows that sit "
        "INSIDE the very history this script just replayed. A tool that only exists because "
        "it already looked good on some slice of BTC 2019-2026 will, unsurprisingly, still "
        "look good when you replay that same slice — that is not new evidence, it's the "
        "SAME evidence read twice. Every trade below is tagged with exactly which kind of "
        "overlap it sits in:\n")
    lines.append(
        "- `[in-sample-overlap]` — inside that tool's own approximate TRAIN window on this "
        "same instrument (the years its parameters could have been directly fit to)\n"
        "- `[val-overlap]` — inside its approximate VALIDATION window (used to pick between "
        "candidate configs, still looked-at before this replay)\n"
        "- `[sealed-overlap]` — inside its approximate SEALED/TEST window: walled off during "
        "selection, checked once, genuinely closer to honest — but still the SAME sealed "
        "slice this repo's own results.md files already reported a number for, so this is "
        "confirmation, not a fresh look\n"
        "- `[clean]` — genuinely predates this whole research program (e.g. BTC daily "
        "2016-2020, before the bybit intraday data this program has ever used even existed)\n"
        "- `[transfer-assumption]` — the sharpest caveat of all: this tool was sealed-"
        "validated on a DIFFERENT INSTRUMENT ENTIRELY (donchian20 + structure-trailing exit "
        "was validated on GOLD — GLD and GC=F — never on BTC, OIL, or SPY) and is applied "
        "here purely on the transfer-of-shape assumption stated in the owner's own brief. "
        "No in-sample/val/sealed split even applies, because this exact instrument was never "
        "part of that tool's research AT ALL. Every T-DONCH, O-DONCH, O-DIP, O-1H, SP-DONCH, "
        "and SP-1H trade in this replay carries this tag for exactly that reason.\n")
    lines.append(
        "**The honest headline number in every section below is the `clean` + `sealed-"
        "overlap` total — never the all-years total, which is inflated by re-showing "
        "in-sample and val years the tools were quite literally built to look good on.** "
        "Where a tool is `[transfer-assumption]`, even ITS `clean`/`sealed` split is "
        "secondary to the bigger fact that the instrument itself was never validated — "
        "treat those numbers as a live-fire transfer test, not a confirmation.\n")

    lines.append("## 15m FILL-FIDELITY — THE HONESTY DELTA\n")
    lines.append(
        "Every BTC fixed-stop/target tool (T-DIVER 4h, T-CHOCH/T-STRIKES/T-FORENSIC 1h) was "
        "re-checked against real 15-minute bar sequences (bybit BTCUSDT 15m, 2020-03-25 -> "
        "today) wherever a coarse bar showed BOTH the stop and the target were touchable in "
        "the same hour/4h window — the ambiguous case the repo's own 'stop wins ties' "
        "convention used to just assume away.\n")
    lines.append(f"- Dual-touch (ambiguous) bars found across all 4 tools: "
                 f"**{fidelity_totals['dual_touch_bars']}**")
    lines.append(f"- Resolved with real 15m path data: **{fidelity_totals['resolved_by_15m']}**")
    lines.append(f"- Outcomes that actually FLIPPED vs the coarse stop-wins-ties convention: "
                 f"**{fidelity_totals['flipped_outcome']}**\n")
    lines.append("| Tool | Dual-touch bars | 15m-resolved | Flipped outcome |")
    lines.append("|---|---|---|---|")
    for tool, fid in fidelity_by_tool.items():
        lines.append(f"| {tool} | {fid['dual_touch_bars']} | {fid['resolved_by_15m']} | {fid['flipped_outcome']} |")
    lines.append(
        "\nStructure-trailing tools (T-DONCH, T-NEWS/N2, O-DONCH, O-1H, SP-DONCH, SP-1H) have "
        "only ONE exit condition (the ratcheting floor) — there is no dual-touch ambiguity to "
        "resolve for them in the first place. OIL/SPX 1h tools (O-1H, SP-1H) stay on the "
        "coarse convention: the free yfinance feed only carries ~60 days of 15m history for "
        "SPY/CL=F, far short of the ~730-day 1h window replayed here, and this script does "
        "not fabricate finer data it doesn't have.\n")

    lines.append("## SIZING & COST METHODOLOGY (summary — full detail in step70_replay.py's "
                 "own module docstring)\n")
    lines.append(
        "$250 margin per trade, non-compounding. leverage = min(20, max(10, "
        "floor(85/stop_pct))). Structure-trailing tools size off the entry-to-initial-floor "
        "distance; the two NO-STOP dip-buy tools (O-DIP, SP-DIP — R60's sealed config rides "
        "to a signal exit with no protective stop at all) use the floor leverage of 10x, "
        "flagged explicitly rather than inventing a stop that doesn't exist. Fees: BTC 6bps/"
        "leg taker, OIL 2bps/leg (futures-proxy), SPX 1bp/leg (ETF). BTC funding applied "
        "where real 8h-settlement data exists (all BTC intraday tools); no funding data "
        "modeled for OIL/SPX (not cached here, stated not hidden).\n")

    lines.append("---\n")
    lines.append("# BTC BOOK\n")
    lines.append(_market_section("BTC — all 6 tools, shared account", btc_df,
                                 "6bps/leg taker + real BTC perp funding"))

    lines.append("---\n")
    lines.append("# OIL BOOK\n")
    lines.append(_market_section(
        "OIL (CL=F) — all 3 tools, shared account", oil_df,
        "2bps/leg (futures-proxy), no funding data modeled",
        extra_note="**ALL THREE oil tools are `[transfer-assumption]`** — donchian20+"
                   "structure-trail was validated on gold, the RSI2 dip-buy was validated on "
                   "the S&P (R60), and O-1H is the gold shape applied to oil at 1h. None of "
                   "the three has ever been independently validated ON oil. Treat this whole "
                   "book as a live transfer test, not a confirmed edge."))

    lines.append("---\n")
    lines.append("# S&P (SPX / SPY) BOOK\n")
    lines.append(_market_section(
        "S&P — all 3 tools, shared account, owner's leverage spec (10-20x)", spx_df,
        "1bp/leg (ETF), no funding data modeled",
        extra_note="**SP-DONCH and SP-1H are `[transfer-assumption]`** (gold's shape, never "
                   "validated on SPY). **SP-DIP is the one real, non-transfer result in this "
                   "whole replay** — R60 sealed-validated RSI2<5/SMA200 directly on SPY/ES=F, "
                   "so its in-sample/val/sealed tags mean what they say."))

    if len(spx_df_4x):
        total_4x = spx_df_4x["net_pnl"].sum()
        clean_4x, clean_n_4x = clean_sealed_total(spx_df_4x)
        lines.append(
            f"\n**HONESTY LINE — realistic retail leverage:** the owner's sizing spec (10-20x) "
            f"is not realistic for a real SPY/ES broker account (~4x max in practice). Re-run "
            f"at a flat, realistic 4x for every S&P trade: all-years total "
            f"{_fmt_money(total_4x)}, clean+sealed-overlap total {_fmt_money(clean_4x)} "
            f"across {clean_n_4x} trades — for comparison against the spec's headline number "
            f"above, not a replacement for it.\n")

    lines.append("---\n")
    lines.append("## PLAIN-ENGLISH VERDICT\n")
    for name, df in (("BTC", btc_df), ("OIL", oil_df), ("S&P", spx_df)):
        if df is None or len(df) == 0:
            lines.append(f"- **{name}:** no trades fired — nothing to verdict.")
            continue
        clean_pnl, clean_n = clean_sealed_total(df)
        all_pnl = df["net_pnl"].sum()
        lines.append(
            f"- **{name}:** the current brain, walked bar-by-bar through this history with "
            f"zero future knowledge, would have turned $250 of at-risk margin per trade into "
            f"{_fmt_money(all_pnl)} net across all {len(df)} replayed trades — but only "
            f"{_fmt_money(clean_pnl)} of that, across {clean_n} trades, comes from years the "
            f"tools genuinely never looked at before (clean + sealed-overlap only). The gap "
            f"between those two numbers IS the in-sample caveat, quantified, not hand-waved.")
    lines.append("")

    lines.append("---\n")
    lines.append("## BIGGEST CAVEAT, LAST\n")
    lines.append(
        "This whole exercise measures whether a FIXED, ALREADY-CHOSEN set of rules would "
        "have made money walking forward — it does NOT measure how those rules were chosen. "
        "Every tool here survived a prior round of dozens-to-hundreds of candidate configs "
        "getting discarded on the SAME handful of years of BTC history (and, for the "
        "transfer tools, on a different instrument altogether). That selection process is "
        "exactly the kind of multiple-comparisons machine that manufactures impressive-"
        "looking backtests out of noise — the `[in-sample-overlap]`/`[val-overlap]` years "
        "above are not just \"a bit optimistic\", they are the SAME data the selection "
        "process already used to keep these six BTC tools and discard everything else it "
        "tried. The `clean`/`sealed-overlap` numbers are the only ones that come close to "
        "answering \"would this have worked on data the selection process never touched\" — "
        "and even those are thin (a handful of months to a couple of years per tool, not a "
        "full market cycle), a single-account walk-forward with no regime diversity, and for "
        "half the book (every donchian tool, on every market), an untested cross-instrument "
        "transfer assumption on top of everything else. Small, thin, correlated, and mostly "
        "revisited data — read every number above with that in mind before sizing a real "
        "account off it.\n")

    with open(f"{SCRATCH}/step70_results.md", "w") as f:
        f.write("\n".join(lines))
    print(f"  wrote step70_results.md")


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    print("=" * 70)
    print("ROUND 70 — WALK-FORWARD REPLAY EXAM")
    print("=" * 70)

    fidelity_totals = {"dual_touch_bars": 0, "resolved_by_15m": 0, "flipped_outcome": 0}
    fidelity_by_tool = {}

    def merge_fid(name, fid):
        fidelity_by_tool[name] = fid
        for k in fidelity_totals:
            fidelity_totals[k] += fid.get(k, 0)

    # -------------------------------------------------------------- BTC ---
    print("\n--- Loading BTC data ---")
    btc_daily = load_btc_daily_yf()
    d1h = load_bybit("1h")
    d4h = load_bybit("4h")
    funding = load_funding()
    funding_1h_bps = align_funding_to(d1h, funding)
    funding_df_1h = pd.DataFrame({"timestamp": d1h["timestamp"], "funding_bps": funding_1h_bps})
    headlines = load_watcherguru()

    print(f"  BTC daily (yfinance): {btc_daily['timestamp'].min()} -> {btc_daily['timestamp'].max()} ({len(btc_daily)} bars)")
    print(f"  BTC 1h (bybit): {d1h['timestamp'].min()} -> {d1h['timestamp'].max()} ({len(d1h)} bars)")
    print(f"  BTC 4h (bybit): {d4h['timestamp'].min()} -> {d4h['timestamp'].max()} ({len(d4h)} bars)")
    print(f"  WatcherGuru headlines: {headlines['utc_timestamp'].min()} -> {headlines['utc_timestamp'].max()} ({len(headlines)} rows)")

    print("\n--- Building BTC tools ---")
    t_donch = donchian_structure_trail(btc_daily, fee_bps=6.0)
    print(f"  T-DONCH: {len(t_donch)} trades")
    t_diver, fid = build_t_diver(d4h, fee_bps=6.0)
    merge_fid("T-DIVER", fid)
    print(f"  T-DIVER: {len(t_diver)} trades  (dual-touch bars={fid['dual_touch_bars']}, 15m-resolved={fid['resolved_by_15m']}, flipped={fid['flipped_outcome']})")
    t_choch, choch_stop, choch_tgt, choch_split, fid = build_t_choch(d1h, d4h, fee_bps=6.0)
    merge_fid("T-CHOCH", fid)
    print(f"  T-CHOCH: {len(t_choch)} trades  stop={choch_stop}  target={choch_tgt}  (dual-touch bars={fid['dual_touch_bars']}, 15m-resolved={fid['resolved_by_15m']}, flipped={fid['flipped_outcome']})")
    t_strikes, fid = build_t_strikes(d1h, btc_daily, fee_bps=6.0)
    merge_fid("T-STRIKES", fid)
    print(f"  T-STRIKES: {len(t_strikes)} trades  (dual-touch bars={fid['dual_touch_bars']}, 15m-resolved={fid['resolved_by_15m']}, flipped={fid['flipped_outcome']})")
    t_news, news_lo, news_hi = build_t_news(d1h, headlines, fee_bps=6.0)
    print(f"  T-NEWS: {len(t_news)} trades  (span {news_lo} -> {news_hi})")
    t_forensic, fid = build_t_forensic(d1h, funding_1h_bps, fee_bps=6.0)
    merge_fid("T-FORENSIC", fid)
    print(f"  T-FORENSIC: {len(t_forensic)} trades  (dual-touch bars={fid['dual_touch_bars']}, 15m-resolved={fid['resolved_by_15m']}, flipped={fid['flipped_outcome']})")

    # -- overlap tagging (BTC) --
    i_tr_1h, i_va_1h = split_dates(d1h)
    i_tr_4h, i_va_4h = split_dates(d4h)
    clean_before = pd.Timestamp("2020-03-25", tz="UTC")   # bybit BTC data start
    apply_tags(t_donch, i_tr_1h, i_va_1h, clean_before=clean_before, transfer=True)
    apply_tags(t_diver, i_tr_4h, i_va_4h)
    apply_tags(t_choch, i_tr_1h, i_va_1h)
    apply_tags(t_strikes, i_tr_1h, i_va_1h)
    if t_news:
        news_frame = d1h[(d1h["timestamp"] >= news_lo) & (d1h["timestamp"] <= news_hi)].reset_index(drop=True)
        i_tr_news, i_va_news = split_dates(news_frame)
        apply_tags(t_news, i_tr_news, i_va_news)
    apply_tags(t_forensic, i_tr_1h, i_va_1h)

    # -- price every BTC trade --
    btc_trades = []
    btc_trades += price_book(t_donch, funding_series_1h=None, fee_bps_override=6.0)
    for t in btc_trades:
        t["tool"] = "T-DONCH"
    for group, name in ((t_diver, "T-DIVER"), (t_choch, "T-CHOCH"),
                        (t_strikes, "T-STRIKES"), (t_news, "T-NEWS"),
                        (t_forensic, "T-FORENSIC")):
        priced = price_book(group, funding_series_1h=funding_df_1h, fee_bps_override=6.0)
        btc_trades += priced

    btc_df = pd.DataFrame(btc_trades).sort_values("exit_time").reset_index(drop=True) if btc_trades else pd.DataFrame()

    # -------------------------------------------------------------- OIL ---
    print("\n--- Loading OIL (CL=F) data ---")
    oil_daily = load_yf("CL=F", "1d", "10y")
    oil_1h = load_yf("CL=F", "1h", "730d")
    print(f"  CL=F daily: {oil_daily['timestamp'].min()} -> {oil_daily['timestamp'].max()} ({len(oil_daily)} bars)")
    print(f"  CL=F 1h: {oil_1h['timestamp'].min()} -> {oil_1h['timestamp'].max()} ({len(oil_1h)} bars)")

    o_donch = donchian_structure_trail(oil_daily, fee_bps=2.0)
    o_dip = rsi2_dipbuy_sealed(oil_daily, fee_bps=2.0)
    o_1h = donchian_structure_trail(oil_1h, fee_bps=2.0)
    for t in o_donch:
        t["tool"] = "O-DONCH"
    for t in o_dip:
        t["tool"] = "O-DIP"
    for t in o_1h:
        t["tool"] = "O-1H"
    print(f"  O-DONCH: {len(o_donch)} trades | O-DIP: {len(o_dip)} trades | O-1H: {len(o_1h)} trades")

    i_tr_od, i_va_od = split_dates(oil_daily)
    i_tr_o1, i_va_o1 = split_dates(oil_1h)
    apply_tags(o_donch, i_tr_od, i_va_od, transfer=True)
    apply_tags(o_dip, i_tr_od, i_va_od, transfer=True)
    apply_tags(o_1h, i_tr_o1, i_va_o1, transfer=True)

    oil_trades = price_book(o_donch + o_dip + o_1h, funding_series_1h=None, fee_bps_override=2.0)
    oil_df = pd.DataFrame(oil_trades).sort_values("exit_time").reset_index(drop=True) if oil_trades else pd.DataFrame()

    # -------------------------------------------------------------- SPX ---
    print("\n--- Loading SPX (SPY) data ---")
    spy_daily = load_yf("SPY", "1d", "10y")
    spy_1h = load_yf("SPY", "1h", "730d")
    print(f"  SPY daily: {spy_daily['timestamp'].min()} -> {spy_daily['timestamp'].max()} ({len(spy_daily)} bars)")
    print(f"  SPY 1h: {spy_1h['timestamp'].min()} -> {spy_1h['timestamp'].max()} ({len(spy_1h)} bars)")

    sp_dip = rsi2_dipbuy_sealed(spy_daily, fee_bps=1.0)
    sp_donch = donchian_structure_trail(spy_daily, fee_bps=1.0)
    sp_1h = donchian_structure_trail(spy_1h, fee_bps=1.0)
    for t in sp_dip:
        t["tool"] = "SP-DIP"
    for t in sp_donch:
        t["tool"] = "SP-DONCH"
    for t in sp_1h:
        t["tool"] = "SP-1H"
    print(f"  SP-DIP: {len(sp_dip)} trades | SP-DONCH: {len(sp_donch)} trades | SP-1H: {len(sp_1h)} trades")

    i_tr_sd, i_va_sd = split_dates(spy_daily)
    i_tr_s1, i_va_s1 = split_dates(spy_1h)
    apply_tags(sp_dip, i_tr_sd, i_va_sd)          # sealed-validated ON SPY itself (R60)
    apply_tags(sp_donch, i_tr_sd, i_va_sd, transfer=True)
    apply_tags(sp_1h, i_tr_s1, i_va_s1, transfer=True)

    # 4x realistic-broker-leverage honesty line for SPX (owner's scope addition)
    spx_trades_20x = price_book(sp_dip + sp_donch + sp_1h, funding_series_1h=None,
                                fee_bps_override=1.0)
    spx_trades_4x = price_book(sp_dip + sp_donch + sp_1h, funding_series_1h=None,
                               fee_bps_override=1.0, min_lev=4, max_lev=4)
    spx_df = pd.DataFrame(spx_trades_20x).sort_values("exit_time").reset_index(drop=True) if spx_trades_20x else pd.DataFrame()
    spx_df_4x = pd.DataFrame(spx_trades_4x).sort_values("exit_time").reset_index(drop=True) if spx_trades_4x else pd.DataFrame()

    # -------------------------------------------------------------- OUT ---
    print("\n--- Writing outputs ---")
    for df, path in ((btc_df, "step70_trades_btc.csv"), (oil_df, "step70_trades_oil.csv"),
                     (spx_df, "step70_trades_spx.csv")):
        cols = ["tool", "direction", "entry_time", "entry_price", "exit_time",
               "exit_price", "exit_reason", "hold_hours", "stop_pct",
               "leverage", "notional", "gross_pnl", "fees", "funding_cost",
               "net_pnl", "overlap_tag"]
        if len(df):
            df[[c for c in cols if c in df.columns]].to_csv(f"{SCRATCH}/{path}", index=False)
        else:
            pd.DataFrame(columns=cols).to_csv(f"{SCRATCH}/{path}", index=False)
        print(f"  wrote {path} ({len(df)} rows)")

    write_results_md(btc_df, oil_df, spx_df, spx_df_4x, fidelity_totals, fidelity_by_tool,
                     dict(i_tr_1h=i_tr_1h, i_va_1h=i_va_1h, i_tr_4h=i_tr_4h, i_va_4h=i_va_4h,
                          news_lo=news_lo if t_news else None, news_hi=news_hi if t_news else None,
                          i_tr_od=i_tr_od, i_va_od=i_va_od, i_tr_o1=i_tr_o1, i_va_o1=i_va_o1,
                          i_tr_sd=i_tr_sd, i_va_sd=i_va_sd, i_tr_s1=i_tr_s1, i_va_s1=i_va_s1))
    print("\nDone.")


if __name__ == "__main__":
    main()
