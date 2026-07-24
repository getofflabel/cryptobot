"""
step55_gold_system.py — Round 55: the full multi-family, multi-timeframe
hunt for ADDITIONAL gold edges, beyond the one validated family (donchian20/
55 + EMA20 exit, daily, sealed-passed 4x, live in gold_book.py).

RESEARCH ONLY. Writes exactly: step55_gold_system.py (this file),
step55_results.md (composed by hand from this script's stdout, same
discipline as step48/step52), and data_gold_<TF>.parquet data files.
No commits, no live orders, gold_book.py and every other live file are
never touched or imported for anything except its already-sealed reference
numbers (quoted from RESEARCH_LOG.md / its own docstring, not re-derived
by importing it).

DATA
  GC=F (COMEX gold futures) via yfinance:
    - 1d: max history (20+ years). Reused directly from
      data_tradfi_GCF_1d.parquet (step48/step51/step52 already fetched
      this; re-fetching would just reproduce the same series) and re-saved
      as data_gold_1d.parquet.
    - 1h: ~730d-class history (yfinance's practical ceiling for hourly
      futures). Reused from data_tradfi_GCF_1h.parquet (fetched fresh this
      week) and re-saved as data_gold_1h.parquet. If neither cache exists,
      this script fetches fresh via yfinance.
    - 4h: built by resampling the 1h series with strategy.resample_4h
      (pandas .resample("4h"), default closed=left/label=left, OHLC
      first/max/min/last, volume summed, empty bins dropped). Session gaps
      (maintenance breaks, weekends) simply produce bins with fewer than 4
      real hours of underlying data, or no bin at all (dropped) — the bin's
      OHLC is still internally consistent (first/last/max/min of whatever
      really printed), so no synthetic bar is ever fabricated. This is the
      documented "indicator-continuity handling" for the resample.
  XAUT-USDT 1h from BloFin (exchange.py's BlofinExchange, prod, public
    endpoints, paginated to full history) — a YOUNG listing (instrument
    listTime = 2025-04-23), used ONLY as a post-hoc venue-transfer sanity
    check on whatever configs qualify as SURVIVORS on GC=F. It is never a
    primary validation venue: no train/val/test split is applied to it,
    just "does the identical signal, with the identical %-stop/%-target,
    still show positive expectancy on the live venue's own short history."
  5m/15m: DELIBERATELY NOT FETCHED. yfinance's free tier caps intraday
    bars below 1h at ~60 calendar days of history. A chronological 60/20/20
    split of 60 days leaves ~12 calendar days per side; gold's native
    entry frequency (even for the busiest families here) is nowhere near
    dense enough to clear MIN_TRAIN_TRADES=30 / MIN_VAL_TRADES=8 inside a
    12-day val window without exactly the kind of overfit-to-noise the
    gauntlet exists to prevent. Faking this with a shorter grace window
    would violate the "don't touch the floors" mandate, so it is skipped
    outright. See step55_results.md's data section for what a paid feed
    (minute-bar futures history — e.g. Databento, Polygon.io, CME's own
    historical files, or a broker's stored minute bars via Alpaca/IBKR)
    would unlock.

GAUNTLET
  Chronological 60/20/20 per timeframe/dataset (split_points, imported).
  >=30 train / >=8 val trades to earn SURVIVOR. Selection is by TRAIN
  expectancy only — val is computed and reported, never tuned against.
  This script NEVER slices into the final 20% (test) of any GC=F split.
  The XAUT-USDT check below is not a split at all, just a whole-history
  compatibility read, and is explicitly not a "look."

COSTS
  GC=F (all timeframes): step48_tradfi_trend's "futures" CostModel,
    reproduced here as GOLD_COSTS — 0.5bp fee + 0.5bp slippage each side,
    0 half-spread, funding_bps_8h=0.0 (dated futures pay no perpetual
    funding) -> round_trip_bps() = 2*(0.5+0+0.5) = 2.0 bps, matching the
    task's "2bps round trip" spec exactly. execution="taker" throughout —
    GOLD_COSTS's slippage term is designed for a flat taker-fill estimate,
    same as step48.
  XAUT-USDT (venue-transfer check only): BLOFIN_COSTS = the repo's
    default CostModel() (6bp taker/2bp maker, 1bp half-spread, 2bp
    slippage, funding_bps_8h=1.0 conservative-always-pay) — this is what a
    real position on this venue actually costs, per step52's identical
    convention for every non-BTC BloFin perp.

PLUMBING REUSE (by import, per the task mandate)
  step43_daytrade: split_points, day_trade_signal, hold_stats,
    session_range, hours_to_bars, bar_hours, MIN_TRAIN_TRADES,
    MIN_VAL_TRADES.
  step41_shorts: adaptive_vol_gate (direction="above" for trend-following
    "lively" gates, direction="below" for mean-reversion "calm" gates —
    the function already supports both, nothing to reimplement).
  step48_tradfi_trend: donchian_ema_exit, donchian_short_ema_exit,
    days_to_bars, gap_stats_summary, gap_honesty_correction,
    decade_breakdown, print_decade_breakdown.
  strategy.py: atr, rsi, resample_4h, _hysteresis (verbatim, never
    reimplemented).
  backtest.py: CostModel, run_backtest (verbatim, the only engine there is).
  score()/mk_row()/verdict_for() are written LOCALLY rather than imported
  from step41/step43, for the same reason step48 gave for not importing
  step41's: those crypto versions hardcode a funding_series parameter and
  the engine's crypto-default CostModel, neither of which fits GC=F's
  zero-funding/2bps convention or XAUT's need for a DIFFERENT cost model
  than GC=F. The THRESHOLDS and STRUCTURE (train>0 AND val>0, >=30/>=8
  trades -> SURVIVOR) are identical to step41/step43/step48 — only the
  plumbing needed to plug in a per-instrument CostModel changed.

FAMILIES — see the five family_*() functions below for exact specs; the
task's own family descriptions are reproduced in each function's docstring
so the config grid is traceable line-by-line back to the brief.
"""

from __future__ import annotations

import time

import numpy as np
import pandas as pd
import yfinance as yf

from backtest import CostModel, run_backtest
from exchange import BlofinExchange
from strategy import atr, resample_4h, rsi
from step41_shorts import adaptive_vol_gate
from step43_daytrade import (
    MIN_TRAIN_TRADES, MIN_VAL_TRADES,
    bar_hours, day_trade_signal, hold_stats, hours_to_bars,
    session_range, split_points,
)
from step48_tradfi_trend import (
    days_to_bars, decade_breakdown, donchian_ema_exit,
    donchian_short_ema_exit, gap_honesty_correction, gap_stats_summary,
    print_decade_breakdown,
)

pd.set_option("display.width", 240)
pd.set_option("display.max_columns", None)

GOLD_COSTS = CostModel(fee_bps=0.5, maker_fee_bps=0.5, half_spread_bps=0.0,
                        slippage_bps=0.5, funding_bps_8h=0.0)
BLOFIN_COSTS = CostModel()   # repo default: 6bp taker/2bp maker/1bp spread/2bp slip/1bp funding

# family5's protective-stop / family1's optional ATR-scaled stop both use
# this single train-derived multiplier — one number, not a further grid,
# matching the task's literal "with/without" (not "which multiplier") ask.
ATR_STOP_MULT = 1.5

# (family, config, tf) -> {"fn": callable(dd, i_tr=None)->pd.Series,
#                            "stop_pct": float|None, "target_pct": float|None}
# populated as each family builds its configs, consumed by the XAUT
# venue-transfer check so every survivor's EXACT signal can be rebuilt on
# XAUT-USDT's own (differently-lengthed) candle frame.
BUILDER_REGISTRY: dict[tuple, dict] = {}


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

def _fetch_yf(symbol: str, interval: str, period: str) -> pd.DataFrame:
    raw = None
    for attempt in range(3):
        try:
            raw = yf.Ticker(symbol).history(period=period, interval=interval,
                                             auto_adjust=False)
            if raw is not None and len(raw) > 0:
                break
        except Exception as e:
            print(f"  retry {symbol} {interval} ({e})")
        time.sleep(2)
    if raw is None or len(raw) == 0:
        raise RuntimeError(f"no data returned for {symbol} {interval}")
    df = raw.reset_index()
    tcol = "Date" if "Date" in df.columns else "Datetime"
    out = pd.DataFrame({
        "timestamp": pd.to_datetime(df[tcol], utc=True),
        "open": df["Open"].astype(float), "high": df["High"].astype(float),
        "low": df["Low"].astype(float), "close": df["Close"].astype(float),
        "volume": df["Volume"].astype(float),
    }).dropna().drop_duplicates(subset="timestamp").sort_values("timestamp")
    return out.reset_index(drop=True)


def load_gcf(tf: str) -> pd.DataFrame:
    """tf in {'1d','1h'}. Reuse cache in priority order: this round's own
    data_gold_<tf>.parquet -> the earlier round's data_tradfi_GCF_<tf>.parquet
    (same underlying series, just renamed for this round's file-list rule)
    -> fresh yfinance fetch."""
    own = f"data_gold_{tf}.parquet"
    try:
        d = pd.read_parquet(own)
        print(f"  cached {own}: {len(d)} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d}")
        return d
    except FileNotFoundError:
        pass
    legacy = f"data_tradfi_GCF_{tf}.parquet"
    try:
        d = pd.read_parquet(legacy)
        print(f"  reused {legacy} -> {own}: {len(d)} bars "
              f"{d['timestamp'].iloc[0]:%Y-%m-%d} -> {d['timestamp'].iloc[-1]:%Y-%m-%d}")
        d.to_parquet(own)
        return d
    except FileNotFoundError:
        pass
    period = "max" if tf == "1d" else "730d"
    interval = "1d" if tf == "1d" else "1h"
    print(f"  fetching fresh GC=F {tf} ({period}) via yfinance...")
    d = _fetch_yf("GC=F", interval, period)
    d.to_parquet(own)
    print(f"  saved {own}: {len(d)} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
          f"{d['timestamp'].iloc[-1]:%Y-%m-%d}")
    return d


def build_4h(d1h: pd.DataFrame) -> pd.DataFrame:
    fname = "data_gold_4h.parquet"
    try:
        d = pd.read_parquet(fname)
        print(f"  cached {fname}: {len(d)} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d}")
        return d
    except FileNotFoundError:
        pass
    d = resample_4h(d1h)
    d.to_parquet(fname)
    print(f"  saved {fname}: {len(d)} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
          f"{d['timestamp'].iloc[-1]:%Y-%m-%d}")
    return d


def load_xaut_1h() -> pd.DataFrame:
    fname = "data_gold_xaut_1h.parquet"
    try:
        d = pd.read_parquet(fname)
        if len(d):
            print(f"  cached {fname}: {len(d)} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
                  f"{d['timestamp'].iloc[-1]:%Y-%m-%d}")
            return d
    except FileNotFoundError:
        pass
    ex = BlofinExchange(demo=False)
    frames, end_ms = [], None
    for _ in range(40):
        chunk = ex.get_candles("XAUT-USDT", "1h", limit=1440, end_ms=end_ms)
        if chunk.empty:
            break
        frames.append(chunk)
        oldest = chunk["timestamp"].iloc[0]
        new_end_ms = int(oldest.timestamp() * 1000)
        if end_ms is not None and new_end_ms >= end_ms:
            break
        end_ms = new_end_ms
        if len(chunk) < 2:
            break
        time.sleep(0.05)
    if not frames:
        d = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    else:
        d = (pd.concat(frames).drop_duplicates(subset="timestamp")
             .sort_values("timestamp").reset_index(drop=True))
    d.to_parquet(fname)
    if len(d):
        print(f"  saved {fname}: {len(d)} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d}")
    else:
        print(f"  saved {fname}: EMPTY")
    return d


# ---------------------------------------------------------------------------
# local scoring plumbing (see module docstring for why these aren't imports)
# ---------------------------------------------------------------------------

def score(d, sig, costs, i_tr, i_va, stop_pct=None, target_pct=None, execution="taker"):
    def run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True), sig.iloc[lo:hi].reset_index(drop=True),
            costs=costs, execution=execution, stop_pct=stop_pct, target_pct=target_pct,
        )
    return run(0, i_tr), run(i_tr, i_va)


def verdict_for(tr, va) -> str:
    tr_n, va_n = len(tr.trades), len(va.trades)
    if tr.expectancy > 0 and va.expectancy > 0:
        if tr_n >= MIN_TRAIN_TRADES and va_n >= MIN_VAL_TRADES:
            return "SURVIVOR"
        return "INSUFFICIENT-SAMPLE"
    return "FAIL"


def mk_row(family, config, tf, tr, va, stop_pct=None, target_pct=None, extra=None):
    med_h, mean_h = hold_stats(tr, va)
    row = {
        "family": family, "config": config, "tf": tf,
        "stop%": stop_pct, "target%": target_pct,
        "tr_n": len(tr.trades), "tr_exp": tr.expectancy, "tr_win%": tr.win_rate * 100,
        "tr_ret%": tr.total_return_pct, "tr_dd%": tr.max_drawdown_pct,
        "va_n": len(va.trades), "va_exp": va.expectancy, "va_win%": va.win_rate * 100,
        "va_ret%": va.total_return_pct, "va_dd%": va.max_drawdown_pct,
        "med_hold_h": med_h, "mean_hold_h": mean_h,
        "verdict": verdict_for(tr, va),
    }
    if extra:
        row.update(extra)
    return row


def register_builder(family, config, tf, fn, stop_pct=None, target_pct=None):
    BUILDER_REGISTRY[(family, config, tf)] = {
        "fn": fn, "stop_pct": stop_pct, "target_pct": target_pct,
    }


def apply_gap_honesty(d, i_tr, i_va, tr, va, stop_pct, costs, tag):
    if stop_pct is None:
        return None
    d_tr = d.iloc[:i_tr].reset_index(drop=True)
    d_va = d.iloc[i_tr:i_va].reset_index(drop=True)
    gap_tr, n_tr = gap_honesty_correction(d_tr, tr.trades, stop_pct, costs)
    gap_va, n_va = gap_honesty_correction(d_va, va.trades, stop_pct, costs)
    return {
        "tag": tag, "tr_exp": tr.expectancy,
        "tr_exp_gapadj": tr.expectancy + (gap_tr / len(tr.trades) if tr.trades else 0.0),
        "tr_gapped_n": n_tr, "va_exp": va.expectancy,
        "va_exp_gapadj": va.expectancy + (gap_va / len(va.trades) if va.trades else 0.0),
        "va_gapped_n": n_va,
    }


# ---------------------------------------------------------------------------
# EMA crossover primitives (strategy.py only has the SMA version; the EMA
# version is written here, mirroring ma_crossover / vol_gated_ma's exact
# state-machine idiom so behavior stays predictable and auditable).
# ---------------------------------------------------------------------------

def ema_crossover(d: pd.DataFrame, fast: int, slow: int, allow_short: bool = False) -> pd.Series:
    if fast >= slow:
        raise ValueError(f"fast ({fast}) must be shorter than slow ({slow})")
    ema_fast = d["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = d["close"].ewm(span=slow, adjust=False).mean()
    sig = pd.Series(0.0, index=d.index)
    sig[ema_fast > ema_slow] = 1.0
    sig[ema_fast < ema_slow] = -1.0 if allow_short else 0.0
    # warmup: an EMA computed from fewer than `slow` bars hasn't converged
    # to anything resembling the intended lookback — mask it NaN, exactly
    # the SMA convention's warmup-NaN spirit (ma_crossover / vol_gated_ma).
    sig.iloc[:slow] = float("nan")
    return sig


def ema_gated_signal(d: pd.DataFrame, fast: int, slow: int, allow_short: bool = True,
                      entry_filter: pd.Series | None = None) -> pd.Series:
    """Ported pattern from strategy.vol_gated_ma, with the EMA cross
    swapped in for the SMA cross. entry_filter, when given, gates NEW
    entries only (an open position rides the EMA cross alone) — identical
    contract to vol_gated_ma's own entry_filter."""
    base = ema_crossover(d, fast, slow, allow_short=True)
    warm = base.notna().to_numpy()
    base_v = base.fillna(0).to_numpy()
    if entry_filter is None:
        extra = np.ones(len(d), dtype=bool)
    else:
        extra = entry_filter.reindex(d.index).fillna(True).to_numpy(dtype=bool)
    out, pos = [], 0.0
    for b, w, ok in zip(base_v, warm, extra):
        if not w:
            out.append(float("nan"))
            continue
        target = b if allow_short else max(b, 0.0)
        if pos == 0.0:
            if target != 0.0 and ok:
                pos = target
        elif target != pos:
            pos = target if (target != 0.0 and ok) else 0.0
        out.append(pos)
    return pd.Series(out, index=d.index)


# ---------------------------------------------------------------------------
# FAMILY 1 — EMA CROSSES (the owner's named ask)
# ---------------------------------------------------------------------------

def family1_ema_crosses(frames, meta):
    """EMA{9/21, 20/50, 50/200} crossover long (+ short mirror), on 1h and
    4h, plus 50/200 on 20y daily; with/without a train-derived ATR-scaled
    fixed stop (ATR_STOP_MULT x median TRAIN ATR%); with/without the
    adaptive vol gate (both directions). No target_pct — exit is the
    crossover itself (trend-following shape, matching strategy.vol_gated_ma
    / step48 family1's own convention of no fixed target on trend exits)."""
    rows = []
    plan = [("1h", [(9, 21), (20, 50), (50, 200)]),
            ("4h", [(9, 21), (20, 50), (50, 200)]),
            ("1d", [(50, 200)])]
    for tf, pairs in plan:
        d = frames[tf]
        m = meta[tf]
        for fast, slow in pairs:
            gate, _ = adaptive_vol_gate(d, direction="above")
            for direction in ("long", "short"):
                allow_short = True
                for gate_name, ef in (("adaptive", gate), ("ungated", None)):
                    for stop_name, stop_pct in (("stop", ATR_STOP_MULT * m["med_atr"]),
                                                 ("nostop", None)):
                        def build(dd, fast=fast, slow=slow, gate_name=gate_name):
                            if gate_name == "adaptive":
                                g, _ = adaptive_vol_gate(dd, direction="above")
                            else:
                                g = None
                            return ema_gated_signal(dd, fast, slow, allow_short=True, entry_filter=g)

                        sig_full = build(d)
                        sig = sig_full.clip(lower=0.0) if direction == "long" else sig_full.clip(upper=0.0)
                        tr, va = score(d, sig, GOLD_COSTS, m["i_tr"], m["i_va"], stop_pct=stop_pct)
                        cfg = f"EMA{fast}/{slow} {direction} {gate_name} {stop_name}"
                        rows.append(mk_row("1-ema-cross", cfg, tf, tr, va, stop_pct=stop_pct))

                        def wrapped(dd, fast=fast, slow=slow, gate_name=gate_name, direction=direction):
                            s = build(dd, fast=fast, slow=slow, gate_name=gate_name)
                            return s.clip(lower=0.0) if direction == "long" else s.clip(upper=0.0)
                        register_builder("1-ema-cross", cfg, tf, wrapped, stop_pct=stop_pct)
    return rows


# ---------------------------------------------------------------------------
# FAMILY 2 — INTRADAY BREAKOUTS (does the daily winner fractal down?)
# ---------------------------------------------------------------------------

def family2_breakouts(frames, meta):
    """donchian{20,55} + EMA20 exit on 1h and 4h (long, imported verbatim
    from step48), PLUS a short-mirror bonus (donchian_short_ema_exit,
    also imported verbatim, same cheap add step48 made for its family4).
    Also runs the identical shape on 1d as an in-round REFERENCE row (not
    a new test — it reproduces the already-sealed incumbent's train/val
    numbers under this round's own cost model for an apples-to-apples
    head-to-head against the EMA-cross family)."""
    rows = []
    for tf in ("1h", "4h", "1d"):
        d = frames[tf]
        m = meta[tf]
        for N in (20, 55):
            sig = donchian_ema_exit(d, N, ema_n=20)
            tr, va = score(d, sig, GOLD_COSTS, m["i_tr"], m["i_va"])
            tag = "incumbent-reference (long)" if tf == "1d" else "long"
            rows.append(mk_row("2-breakout", f"donchian{N} EMA20exit {tag}", tf, tr, va))
            register_builder("2-breakout", f"donchian{N} EMA20exit {tag}", tf,
                              lambda dd, N=N: donchian_ema_exit(dd, N, ema_n=20))

            sig_s = donchian_short_ema_exit(d, N, ema_n=20)
            tr_s, va_s = score(d, sig_s, GOLD_COSTS, m["i_tr"], m["i_va"])
            tag_s = "incumbent-reference (short-mirror)" if tf == "1d" else "short-mirror"
            rows.append(mk_row("2-breakout", f"donchian{N} EMA20exit {tag_s}", tf, tr_s, va_s))
            register_builder("2-breakout", f"donchian{N} EMA20exit {tag_s}", tf,
                              lambda dd, N=N: donchian_short_ema_exit(dd, N, ema_n=20))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 3 — PULLBACK-IN-TREND
# ---------------------------------------------------------------------------

def daily_sma_mapped(d1d: pd.DataFrame, d_target: pd.DataFrame, sma_n: int = 50,
                      lag_days: float = 1.0) -> pd.Series:
    """Map the daily SMA50 onto an intraday frame with NO lookahead: the
    daily bar's SMA becomes visible `lag_days` after that daily bar's own
    timestamp (same +1-bar-length availability lag convention as step43's
    champ_aligned, generalized from 4h->1h to 1d->1h)."""
    sma = d1d["close"].rolling(sma_n).mean()
    avail = pd.DataFrame({
        "timestamp": d1d["timestamp"] + pd.Timedelta(days=lag_days),
        "sma": sma.to_numpy(),
    }).dropna().sort_values("timestamp")
    merged = pd.merge_asof(d_target[["timestamp"]].sort_values("timestamp"),
                            avail, on="timestamp", direction="backward")
    return merged["sma"].reset_index(drop=True)


def family3_pullback(frames_1h, meta_1h, d1d):
    """price above daily SMA50 (mapped shift-safe onto 1h) AND RSI{2,3}(1h)
    < {10,15} -> long; stops {0.5,0.8}x median TRAIN ATR%(1h), targets
    {2,3}x stop, hold <= 48h. Long only per the task spec."""
    rows = []
    d = frames_1h
    m = meta_1h
    sma_mapped = daily_sma_mapped(d1d, d, sma_n=50, lag_days=1.0)
    above = (d["close"] > sma_mapped).fillna(False)
    mh_bars = hours_to_bars(d, 48)
    for rsi_n in (2, 3):
        r = rsi(d["close"], rsi_n)
        for rsi_thresh in (10, 15):
            enter_long = ((r < rsi_thresh) & above).fillna(False)
            enter_short = pd.Series(False, index=d.index)
            for stop_mult in (0.5, 0.8):
                stop_pct = stop_mult * m["med_atr"]
                for target_mult in (2, 3):
                    target_pct = target_mult * stop_pct
                    sig = day_trade_signal(d, enter_long, enter_short, mh_bars)
                    tr, va = score(d, sig, GOLD_COSTS, m["i_tr"], m["i_va"],
                                   stop_pct=stop_pct, target_pct=target_pct)
                    cfg = (f"RSI{rsi_n}<{rsi_thresh} above-dailySMA50 "
                           f"stop{stop_mult}xATR tgt{target_mult}xstop hold48h")
                    rows.append(mk_row("3-pullback", cfg, "1h", tr, va, stop_pct, target_pct))

                    def build(dd, rsi_n=rsi_n, rsi_thresh=rsi_thresh, stop_pct=stop_pct):
                        rr = rsi(dd["close"], rsi_n)
                        sm = daily_sma_mapped(d1d, dd, sma_n=50, lag_days=1.0)
                        ab = (dd["close"] > sm).fillna(False)
                        el = ((rr < rsi_thresh) & ab).fillna(False)
                        es = pd.Series(False, index=dd.index)
                        mhb = hours_to_bars(dd, 48)
                        return day_trade_signal(dd, el, es, mhb)
                    register_builder("3-pullback", cfg, "1h", build, stop_pct, target_pct)
    return rows


# ---------------------------------------------------------------------------
# FAMILY 4 — SESSION STRUCTURE (gold-specific, likeliest real intraday edge)
# ---------------------------------------------------------------------------

def _hour_momentum(d: pd.DataFrame, hour: int):
    hr = d["timestamp"].dt.hour
    up = (d["close"] > d["open"])
    down = (d["close"] < d["open"])
    enter_long = ((hr == hour) & up).fillna(False)
    enter_short = ((hr == hour) & down).fillna(False)
    return enter_long, enter_short


def family4_session_structure(frames_1h, meta_1h):
    """(a) London-open momentum: direction of the 08:00-09:00 UTC hour
    followed for {4,8}h. (b) NY-open: same shape, proxy hour 13:00-14:00
    UTC (the 1h bar straddling the 13:30 NY cash open — hourly bars can't
    hit the 30-minute mark exactly; documented approximation, same spirit
    as step43/step48's stated VWAP-distance / range-height approximations).
    (c) Asia-range (00:00-07:00 UTC) breakout, exit by session end
    (~17h later) — reuses step43's session_range()/max-hold convention
    verbatim (H=7), plus a train-derived range-based stop/target exactly
    like step43's own session-breakout family."""
    rows = []
    d = frames_1h
    m = meta_1h
    i_tr, i_va = m["i_tr"], m["i_va"]

    for tag, hour in (("london-open(08-09z)", 8), ("ny-open(13-14z)", 13)):
        el, es = _hour_momentum(d, hour)
        for max_hold_h in (4, 8):
            mh_bars = hours_to_bars(d, max_hold_h)
            sig = day_trade_signal(d, el, es, mh_bars)
            tr, va = score(d, sig, GOLD_COSTS, i_tr, i_va)
            cfg = f"{tag} hold{max_hold_h}h"
            rows.append(mk_row("4-session", cfg, "1h", tr, va))

            def build(dd, hour=hour, max_hold_h=max_hold_h):
                el2, es2 = _hour_momentum(dd, hour)
                mhb = hours_to_bars(dd, max_hold_h)
                return day_trade_signal(dd, el2, es2, mhb)
            register_builder("4-session", cfg, "1h", build)

    win_high, win_low, after_window = session_range(d, 7)
    range_pct = (win_high - win_low) / win_low * 100
    med_range_pct = float(range_pct.iloc[:i_tr].dropna().median())
    stop_pct = min(med_range_pct, 3.0)
    enter_long = (after_window & (d["close"] > win_high)).fillna(False)
    enter_short = (after_window & (d["close"] < win_low)).fillna(False)
    mh_bars = hours_to_bars(d, max(1, 24 - 7))
    sig = day_trade_signal(d, enter_long, enter_short, mh_bars)
    for tmult in (1.5, 2.5):
        target_pct = tmult * med_range_pct
        tr, va = score(d, sig, GOLD_COSTS, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
        cfg = f"asia-range(00-07z) breakout tgt{tmult}xrange"
        rows.append(mk_row("4-session", cfg, "1h", tr, va, stop_pct, target_pct))

        def build(dd, stop_pct=stop_pct, tmult=tmult, med_range_pct=med_range_pct):
            wh, wl, aw = session_range(dd, 7)
            el = (aw & (dd["close"] > wh)).fillna(False)
            es = (aw & (dd["close"] < wl)).fillna(False)
            mhb = hours_to_bars(dd, max(1, 24 - 7))
            return day_trade_signal(dd, el, es, mhb)
        register_builder("4-session", cfg, "1h", build, stop_pct, target_pct)
    return rows, med_range_pct


# ---------------------------------------------------------------------------
# FAMILY 5 — MEAN REVERSION
# ---------------------------------------------------------------------------

def zscore(close: pd.Series, n: int):
    m = close.rolling(n).mean()
    s = close.rolling(n).std()
    return (close - m) / s.replace(0, float("nan")), m


def family5_mean_reversion(frames, meta):
    """z-score(close,{24,48}) < -{1.5,2.0} -> long to the mean (target =
    train-median distance-to-mean at qualifying entries, capped 2% —
    same "train-only representative fixed target" convention step43's
    VWAP-fade family used for an analogous per-trade-dynamic distance),
    calm-gated (adaptive_vol_gate direction="below": below-median vol —
    the mean-reversion mirror of the trend family's "above" lively gate)
    and ungated. A protective stop (ATR_STOP_MULT x median TRAIN ATR%)
    and a bounded max_hold (48h intraday / 10d daily) are added — not
    explicit in the task's one-line spec, but required so a mean-reversion
    entry that never reverts isn't held open indefinitely; documented
    here rather than silently assumed."""
    rows = []
    for tf in ("1h", "4h", "1d"):
        d = frames[tf]
        m = meta[tf]
        i_tr, i_va = m["i_tr"], m["i_va"]
        calm_gate, _ = adaptive_vol_gate(d, direction="below")
        mh_bars = hours_to_bars(d, 48) if tf in ("1h", "4h") else days_to_bars(d, 10)
        for n in (24, 48):
            z, mean = zscore(d["close"], n)
            dist_pct = ((mean - d["close"]) / d["close"] * 100)
            for thresh in (1.5, 2.0):
                enter_long_raw = (z < -thresh).fillna(False)
                entry_dists = dist_pct.iloc[:i_tr][enter_long_raw.iloc[:i_tr]]
                target_pct = min(float(entry_dists.median()), 2.0) if len(entry_dists) else 2.0
                stop_pct = ATR_STOP_MULT * m["med_atr"]
                for gate_name, gate in (("calm-gated", calm_gate), ("ungated", None)):
                    enter_long = (enter_long_raw & gate.reindex(d.index).fillna(False)) if gate is not None else enter_long_raw
                    enter_short = pd.Series(False, index=d.index)
                    sig = day_trade_signal(d, enter_long, enter_short, mh_bars)
                    tr, va = score(d, sig, GOLD_COSTS, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
                    cfg = f"z{n}<-{thresh} {gate_name} tgt{target_pct:.2f}% stop{stop_pct:.2f}%"
                    rows.append(mk_row("5-meanrev", cfg, tf, tr, va, stop_pct, target_pct))

                    def build(dd, n=n, thresh=thresh, gate_name=gate_name, target_pct=target_pct, mh_bars_tf=tf):
                        zz, mm = zscore(dd["close"], n)
                        el_raw = (zz < -thresh).fillna(False)
                        if gate_name == "calm-gated":
                            g, _ = adaptive_vol_gate(dd, direction="below")
                            el = (el_raw & g.reindex(dd.index).fillna(False))
                        else:
                            el = el_raw
                        es = pd.Series(False, index=dd.index)
                        mhb = hours_to_bars(dd, 48) if mh_bars_tf in ("1h", "4h") else days_to_bars(dd, 10)
                        return day_trade_signal(dd, el, es, mhb)
                    register_builder("5-meanrev", cfg, tf, build, stop_pct, target_pct)
    return rows


# ---------------------------------------------------------------------------
# XAUT-USDT venue-transfer check (survivors only, never primary validation)
# ---------------------------------------------------------------------------

def xaut_transfer_check(survivors: pd.DataFrame, d_xaut: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if d_xaut.empty:
        return pd.DataFrame(rows)
    for _, r in survivors.iterrows():
        if r["tf"] != "1h":
            continue
        key = (r["family"], r["config"], r["tf"])
        spec = BUILDER_REGISTRY.get(key)
        if spec is None:
            continue
        try:
            sig = spec["fn"](d_xaut)
            res = run_backtest(d_xaut, sig, costs=BLOFIN_COSTS, execution="taker",
                                stop_pct=spec["stop_pct"], target_pct=spec["target_pct"])
        except Exception as e:
            rows.append({"family": r["family"], "config": r["config"],
                         "xaut_n": 0, "xaut_exp": float("nan"), "note": f"ERROR: {e}"})
            continue
        rows.append({
            "family": r["family"], "config": r["config"],
            "xaut_n": len(res.trades), "xaut_exp": res.expectancy,
            "xaut_win%": res.win_rate * 100, "xaut_ret%": res.total_return_pct,
            "xaut_dd%": res.max_drawdown_pct,
            "gcf_tr_exp": r["tr_exp"], "gcf_va_exp": r["va_exp"],
            "note": "whole-history compatibility read, NOT a validation split",
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def build_meta(d: pd.DataFrame) -> dict:
    n, i_tr, i_va = split_points(d)
    atr_pct = atr(d, 14) / d["close"] * 100
    med_atr_train = float(atr_pct.iloc[:i_tr].median())
    return {"n": n, "i_tr": i_tr, "i_va": i_va, "med_atr": med_atr_train}


def main():
    print("=" * 78)
    print("ROUND 55 — GOLD SYSTEM: multi-family, multi-timeframe edge hunt")
    print("=" * 78)

    print("\nLoading data...")
    d1d = load_gcf("1d")
    d1h = load_gcf("1h")
    d4h = build_4h(d1h)
    d_xaut = load_xaut_1h()

    frames = {"1d": d1d, "1h": d1h, "4h": d4h}
    meta = {tf: build_meta(d) for tf, d in frames.items()}

    print("\nSpans + split points + median TRAIN ATR% + gap exposure:")
    for tf, d in frames.items():
        m = meta[tf]
        gaps = gap_stats_summary(d, [0.5 * m["med_atr"], 1.0 * m["med_atr"],
                                      1.5 * m["med_atr"], 1.0, 1.5])
        val_span_days = (d["timestamp"].iloc[m["i_va"]] - d["timestamp"].iloc[m["i_tr"]]).days
        print(f"  GC=F {tf:3s}: {m['n']:6d} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | train->{d['timestamp'].iloc[m['i_tr']]:%Y-%m-%d} "
              f"val->{d['timestamp'].iloc[m['i_va']]:%Y-%m-%d} (test sealed) | "
              f"val span ~{val_span_days}d (~{val_span_days/30.4:.1f}mo) | "
              f"med train ATR%={m['med_atr']:.3f}% | gap>thresh: {gaps}")
    if len(d_xaut):
        print(f"  XAUT-USDT 1h (BloFin, venue-transfer only): {len(d_xaut)} bars "
              f"{d_xaut['timestamp'].iloc[0]:%Y-%m-%d} -> {d_xaut['timestamp'].iloc[-1]:%Y-%m-%d}")
    else:
        print("  XAUT-USDT 1h: EMPTY (BloFin unreachable this run)")

    print("\n5m/15m: DELIBERATELY SKIPPED. yfinance free intraday history below 1h "
          "caps at ~60 calendar days; a 60/20/20 split leaves ~12 days val, "
          "nowhere near enough bars to clear MIN_TRAIN_TRADES=30/MIN_VAL_TRADES=8 "
          "honestly for gold's native entry frequency. Paid minute-bar futures "
          "history (Databento, Polygon.io, CME's own files, or a broker's stored "
          "bars via Alpaca/IBKR) would unlock a real gauntlet at these resolutions.")

    print("\nRunning FAMILY 1 (EMA crosses: 9/21, 20/50, 50/200 x 1h/4h, "
          "50/200 x 1d, long+short, gated/ungated, stop/nostop)...")
    rows = family1_ema_crosses(frames, meta)
    print(f"  {len(rows)} configs")

    print("Running FAMILY 2 (intraday breakouts: donchian20/55 + EMA20 exit, "
          "1h/4h, long + short-mirror, plus 1d incumbent-reference)...")
    rows += family2_breakouts(frames, meta)
    print(f"  {len(rows)} configs cumulative")

    print("Running FAMILY 3 (pullback-in-trend: daily SMA50 + RSI2/3(1h) dip)...")
    rows += family3_pullback(d1h, meta["1h"], d1d)
    print(f"  {len(rows)} configs cumulative")

    print("Running FAMILY 4 (session structure: London-open, NY-open, Asia-range)...")
    f4_rows, asia_med_range = family4_session_structure(d1h, meta["1h"])
    rows += f4_rows
    print(f"  {len(rows)} configs cumulative (Asia session train-median range = "
          f"{asia_med_range:.3f}%)")

    print("Running FAMILY 5 (mean reversion: z-score(24/48) < -1.5/-2.0, "
          "calm-gated/ungated, 1h/4h/1d)...")
    rows += family5_mean_reversion(frames, meta)
    print(f"  {len(rows)} configs cumulative")

    df = pd.DataFrame(rows)
    print(f"\n{len(df)} total configs tested. Verdict counts:")
    print(df["verdict"].value_counts().to_string())

    print("\nFull results table (train + val, full costs, test sealed):")
    cols = ["family", "config", "tf", "stop%", "target%", "tr_n", "tr_exp", "tr_win%",
            "tr_ret%", "tr_dd%", "va_n", "va_exp", "va_win%", "va_ret%", "va_dd%",
            "med_hold_h", "verdict"]
    with pd.option_context("display.max_rows", None):
        print(df[cols].sort_values(["family", "tf", "tr_exp"], ascending=[True, True, False])
              .to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    survivors = df[df["verdict"] == "SURVIVOR"].copy()
    near = df[df["verdict"] == "INSUFFICIENT-SAMPLE"].copy()
    print(f"\nSURVIVORS (positive train+val, >={MIN_TRAIN_TRADES} train / "
          f">={MIN_VAL_TRADES} val trades): {len(survivors)}")
    if len(survivors):
        print(survivors[["family", "config", "tf", "tr_n", "tr_exp", "va_n", "va_exp",
                          "med_hold_h"]].to_string(index=False, float_format=lambda x: f"{x:,.3f}"))
    print(f"\nINSUFFICIENT-SAMPLE (positive both windows, under the trade-count bar): {len(near)}")
    if len(near):
        print(near[["family", "config", "tf", "tr_n", "tr_exp", "va_n", "va_exp",
                     "med_hold_h"]].to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    # -----------------------------------------------------------------
    # EMA-cross vs incumbent donchian head-to-head, on IDENTICAL daily data
    # -----------------------------------------------------------------
    print("\nEMA-cross vs incumbent-donchian HEAD-TO-HEAD (1d, identical GOLD_COSTS, "
          "identical split, train/val only):")
    daily_ema = df[(df["family"] == "1-ema-cross") & (df["tf"] == "1d")]
    daily_don = df[(df["family"] == "2-breakout") & (df["tf"] == "1d")]
    with pd.option_context("display.max_rows", None):
        print(pd.concat([daily_don, daily_ema])[
            ["family", "config", "tr_n", "tr_exp", "tr_ret%", "va_n", "va_exp", "va_ret%", "verdict"]
        ].to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    # -----------------------------------------------------------------
    # gap-honesty report for every stop-bearing GC=F 1h/4h config
    # -----------------------------------------------------------------
    print("\nGap-honesty report (GC=F 1h/4h configs with a stop_pct; raw engine "
          "exp vs gap-corrected — fills AT THE OPEN when a bar's open had "
          "already gapped through the stop before the bar started):")
    gap_rows = []
    for _, r in df.iterrows():
        if r["tf"] not in ("1h", "4h") or pd.isna(r["stop%"]):
            continue
        d = frames[r["tf"]]
        m = meta[r["tf"]]
        key = (r["family"], r["config"], r["tf"])
        spec = BUILDER_REGISTRY.get(key)
        if spec is None:
            continue
        sig = spec["fn"](d)
        tr, va = score(d, sig, GOLD_COSTS, m["i_tr"], m["i_va"],
                       stop_pct=spec["stop_pct"], target_pct=spec["target_pct"])
        rep = apply_gap_honesty(d, m["i_tr"], m["i_va"], tr, va, spec["stop_pct"],
                                 GOLD_COSTS, f"{r['family']} {r['config']} {r['tf']}")
        if rep:
            gap_rows.append(rep)
    gap_df = pd.DataFrame(gap_rows).drop_duplicates(subset="tag")
    if len(gap_df):
        print(gap_df.to_string(index=False, float_format=lambda x: f"{x:,.3f}"))
    else:
        print("  (no stop-bearing 1h/4h configs to report)")

    # -----------------------------------------------------------------
    # decade-by-decade consistency, daily survivors/near-misses only
    # -----------------------------------------------------------------
    print("\nDecade-by-decade consistency (1d SURVIVOR/INSUFFICIENT-SAMPLE configs, "
          "TRAIN+VAL only, test window never touched):")
    daily_candidates = pd.concat([survivors, near])
    daily_candidates = daily_candidates[daily_candidates["tf"] == "1d"]
    for _, row in daily_candidates.iterrows():
        key = (row["family"], row["config"], row["tf"])
        spec = BUILDER_REGISTRY.get(key)
        if spec is None:
            continue
        sig = spec["fn"](d1d)
        by_decade = decade_breakdown(d1d, sig, GOLD_COSTS, meta["1d"]["i_va"],
                                      stop_pct=spec["stop_pct"], target_pct=spec["target_pct"])
        print_decade_breakdown(f"{row['family']} {row['config']}", by_decade)

    # -----------------------------------------------------------------
    # XAUT-USDT venue-transfer check (survivors only)
    # -----------------------------------------------------------------
    print("\nXAUT-USDT venue-transfer check (survivors only, whole-history read, "
          "NEVER a primary validation — BLOFIN_COSTS, not GOLD_COSTS):")
    xaut_df = xaut_transfer_check(survivors, d_xaut)
    if len(xaut_df):
        print(xaut_df.to_string(index=False, float_format=lambda x: f"{x:,.3f}"))
    else:
        print("  (no 1h survivors to transfer-check, or XAUT data unavailable)")

    print("\nDone. No GC=F test window was ever sliced or scored above. "
          "XAUT-USDT check above used its full available history with no split "
          "(explicitly not a train/val/test look).")
    return df, xaut_df


if __name__ == "__main__":
    main()
