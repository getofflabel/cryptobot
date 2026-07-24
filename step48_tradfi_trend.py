"""
step48_tradfi_trend.py — Round 48: port the proven crypto strategy SHAPES to
GOLD and NASDAQ (plus SPY/USO/CL=F as broader cross-checks) and test whether
those markets pay them.

RESEARCH ONLY. This script:
  - fetches yfinance daily (max history) and hourly (~730d) bars for
    GLD, QQQ, SPY, USO, GC=F, CL=F, saves them as
    data_tradfi_<SYM>_<TF>.parquet (normalized OHLCV, UTC tz-aware),
  - reuses backtest.py's run_backtest/CostModel and strategy.py's
    vol_gated_ma/rsi/atr verbatim (Wallace's mandate: port, don't
    reimplement the engine or the proven signal primitives),
  - ports the plumbing CONVENTIONS from step41_shorts.py (adaptive vol
    gate, chronological 60/20/20 split_points, score()/mk_row()/verdict_for()
    idiom, event-state-machine entries) without importing that crypto-
    specific module,
  - runs 4 families (trend, dip-buy, breakout, short) across the two
    target markets (gold, Nasdaq) with parameters ADAPTED to each market's
    own volatility, not blindly copied from BTC,
  - NEVER touches the sealed final 20% (test) of any split. Only train/val
    are computed or printed. This script does not write step48_results.md;
    that is composed by hand from this script's stdout so the file list
    stays exactly {step48_tradfi_trend.py, step48_results.md,
    data_tradfi_<SYM>_<TF>.parquet}.

COSTS (no cost-free mode exists — see backtest.py's CostModel):
  ETFs (GLD/QQQ/SPY/USO):  1bp fee + 1bp slippage EACH SIDE, 0 half-spread
                            -> round_trip_bps() = 2*(1+0+1) = 4bps.
  Futures (GC=F/CL=F):     0.5bp fee + 0.5bp slippage each side
                            -> round_trip_bps() = 2*(0.5+0+0.5) = 2bps,
                            matching the task's "2bp round trip" spec.
  FUNDING: perpetual-futures funding does not exist on ETFs or dated
  futures. backtest.py's run_backtest() ALWAYS charges its conservative
  default funding_bps_8h (even when funding_series=None — verified by
  reading the engine) UNLESS the CostModel itself has funding_bps_8h=0.
  Every CostModel built here sets funding_bps_8h=0.0 explicitly. This is
  the single most important "check the engine, don't assume" catch of
  this round: leaving the default (1.0) would have silently taxed every
  TradFi trade ~3bps/day (24h bar / 8h interval x 1bp) that isn't a real
  cost these instruments pay.

GAP HONESTY (explicitly required by the task):
  backtest.py's intrabar stop check is: "did lows[i]/highs[i] touch the
  stop level" -> fill AT the stop price (adjusted for spread/slippage).
  It does NOT check whether bar i's OPEN had already gapped past the stop
  before the bar even started trading — a real stop order sitting at that
  price would have been filled at the (worse) open, not at the stop level.
  On 24/7 crypto this bias is negligible; on equities/gold/oil daily bars
  (17.5h closed overnight, plus weekends) it is not. Two things are done
  about it here, not one:
    1. gap_stats() reports, per symbol/TF, what fraction of bars have an
       open-vs-prior-close gap larger than each stop candidate — the
       structural exposure, independent of which trades were taken.
    2. gap_honesty_correction() finds every trade in a family-2 (dip-buy)
       result whose exit matches the stop-fill formula, checks whether
       that bar's open had already gapped through the stop level, and if
       so recomputes the fill at the open instead — producing an
       HONEST, gap-corrected expectancy alongside the engine's raw one.
  Families 1/3/4 do not use stop_pct (trend/breakout exit on the signal
  itself, filled at next-open like every other engine trade — no special
  intrabar gap issue beyond the one the engine already prices correctly).
"""

from __future__ import annotations

import sys
import time

import numpy as np
import pandas as pd
import yfinance as yf

from backtest import CostModel, run_backtest
from strategy import _hysteresis, atr, rsi, vol_gated_ma

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8

SYMBOLS = ["GLD", "QQQ", "SPY", "USO", "GC=F", "CL=F"]
FILE_TAG = {"GLD": "GLD", "QQQ": "QQQ", "SPY": "SPY", "USO": "USO",
            "GC=F": "GCF", "CL=F": "CLF"}
ASSET_CLASS = {"GLD": "etf", "QQQ": "etf", "SPY": "etf", "USO": "etf",
               "GC=F": "future", "CL=F": "future"}
MARKET_TAG = {"GLD": "gold", "GC=F": "gold", "QQQ": "nasdaq",
              "SPY": "sp500(cross-check)", "USO": "oil(cross-check)",
              "CL=F": "oil(cross-check)"}


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

def fetch_and_save(symbol: str, interval: str, period: str,
                    use_cache: bool = True) -> pd.DataFrame:
    tag = FILE_TAG[symbol]
    tf = "1d" if interval == "1d" else "1h"
    fname = f"data_tradfi_{tag}_{tf}.parquet"

    if use_cache:
        try:
            cached = pd.read_parquet(fname)
            print(f"  cached {fname}: {len(cached)} bars, "
                  f"{cached['timestamp'].iloc[0]:%Y-%m-%d} -> {cached['timestamp'].iloc[-1]:%Y-%m-%d}")
            return cached
        except FileNotFoundError:
            pass

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
        "open": df["Open"].astype(float),
        "high": df["High"].astype(float),
        "low": df["Low"].astype(float),
        "close": df["Close"].astype(float),
        "volume": df["Volume"].astype(float),
    }).dropna().drop_duplicates(subset="timestamp").sort_values("timestamp")
    out = out.reset_index(drop=True)
    out.to_parquet(fname)
    print(f"  saved {fname}: {len(out)} bars, "
          f"{out['timestamp'].iloc[0]:%Y-%m-%d} -> {out['timestamp'].iloc[-1]:%Y-%m-%d}")
    return out


def load_all_data() -> dict:
    frames = {s: {} for s in SYMBOLS}
    print("Fetching DAILY (max history)...")
    for s in SYMBOLS:
        frames[s]["1d"] = fetch_and_save(s, "1d", "max")
    print("Fetching HOURLY (~730d, yfinance's cap for 1h bars)...")
    for s in SYMBOLS:
        frames[s]["1h"] = fetch_and_save(s, "1h", "730d")
    return frames


# ---------------------------------------------------------------------------
# ported plumbing conventions (step41_shorts.py: adaptive_vol_gate,
# split_points, score/mk_row/verdict_for idiom) — copied, not imported,
# because step41 is crypto/funding-specific and this round is a clean
# TradFi harness per the "touch nothing else" mandate.
# ---------------------------------------------------------------------------

def bar_hours(d: pd.DataFrame) -> float:
    t = pd.DatetimeIndex(d["timestamp"])
    return float((t[1:] - t[:-1]).total_seconds().min() / 3600)


def days_to_bars(d: pd.DataFrame, days: float) -> int:
    return max(1, round(days * 24 / bar_hours(d)))


def hours_to_bars(d: pd.DataFrame, hours: float) -> int:
    return max(1, round(hours / bar_hours(d)))


def split_points(d: pd.DataFrame):
    n = len(d)
    return n, int(n * 0.6), int(n * 0.8)


def adaptive_vol_gate(d: pd.DataFrame, direction: str = "above",
                       window_days: int = 365, atr_n: int = 14):
    """Boolean series: is current ATR% above/below its OWN trailing
    window_days median? shift(1) so the current bar's ATR never leaks into
    the threshold it's compared against. Same convention as round 41."""
    a_pct = atr(d, atr_n) / d["close"] * 100
    window = max(30, round(24 / bar_hours(d) * window_days))
    min_periods = max(30, window // 10)
    trailing_med = a_pct.rolling(window, min_periods=min_periods).median().shift(1)
    gate = (a_pct > trailing_med) if direction == "above" else (a_pct < trailing_med)
    return gate.fillna(False), a_pct


def costs_for(symbol: str) -> CostModel:
    if ASSET_CLASS[symbol] == "etf":
        return CostModel(fee_bps=1.0, maker_fee_bps=1.0, half_spread_bps=0.0,
                          slippage_bps=1.0, funding_bps_8h=0.0)
    return CostModel(fee_bps=0.5, maker_fee_bps=0.5, half_spread_bps=0.0,
                      slippage_bps=0.5, funding_bps_8h=0.0)


def score(d: pd.DataFrame, sig: pd.Series, costs: CostModel, i_tr: int, i_va: int,
          stop_pct: float | None = None, target_pct: float | None = None):
    def run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True),
            sig.iloc[lo:hi].reset_index(drop=True),
            costs=costs, execution="taker",
            stop_pct=stop_pct, target_pct=target_pct,
        )
    return run(0, i_tr), run(i_tr, i_va)


def verdict_for(tr, va) -> str:
    tr_n, va_n = len(tr.trades), len(va.trades)
    if tr.expectancy > 0 and va.expectancy > 0:
        if tr_n >= MIN_TRAIN_TRADES and va_n >= MIN_VAL_TRADES:
            return "SURVIVOR"
        return "INSUFFICIENT-SAMPLE"
    return "FAIL"


def mk_row(family, config, symbol, tf, tr, va, extra=None):
    row = {
        "family": family, "config": config, "symbol": symbol,
        "market": MARKET_TAG[symbol], "tf": tf,
        "tr_n": len(tr.trades), "tr_exp": tr.expectancy,
        "tr_win%": tr.win_rate * 100, "tr_dd%": tr.max_drawdown_pct,
        "tr_ret%": tr.total_return_pct,
        "va_n": len(va.trades), "va_exp": va.expectancy,
        "va_win%": va.win_rate * 100, "va_dd%": va.max_drawdown_pct,
        "va_ret%": va.total_return_pct,
        "verdict": verdict_for(tr, va),
    }
    if extra:
        row.update(extra)
    return row


# ---------------------------------------------------------------------------
# gap honesty
# ---------------------------------------------------------------------------

def gap_stats_summary(d: pd.DataFrame, thresholds: list[float]) -> str:
    prev_close = d["close"].shift(1)
    gap_pct = ((d["open"] - prev_close) / prev_close * 100).dropna().abs()
    parts = [f">{th:.2f}%:{(gap_pct > th).mean() * 100:.1f}%" for th in sorted(set(thresholds))]
    return "  ".join(parts)


def gap_honesty_correction(candles: pd.DataFrame, trades, stop_pct, costs: CostModel):
    """Returns (total_dollar_delta, n_trades_gapped_through) for the subset
    of `trades` whose exit matches the engine's intrabar-stop fill formula
    AND whose bar OPEN had already gapped past the stop level. Recomputes
    those fills at the (worse) open. See module docstring."""
    if stop_pct is None or not trades:
        return 0.0, 0
    c = candles.set_index("timestamp")
    adv = costs._adverse_frac
    total_delta = 0.0
    n_gapped = 0
    for t in trades:
        if t.direction > 0:
            stop_price = t.entry_price * (1 - stop_pct / 100)
            modeled_fill = stop_price * (1 - adv)
        else:
            stop_price = t.entry_price * (1 + stop_pct / 100)
            modeled_fill = stop_price * (1 + adv)
        if modeled_fill <= 0 or abs(t.exit_price - modeled_fill) > 1e-6 * modeled_fill:
            continue  # not a stop-exit (was signal/max-hold/target instead)
        if t.exit_time not in c.index:
            continue
        o = float(c.loc[t.exit_time, "open"])
        if t.direction > 0 and o < stop_price:
            actual_fill = o * (1 - adv)
            total_delta += (actual_fill - modeled_fill) * t.units
            n_gapped += 1
        elif t.direction < 0 and o > stop_price:
            actual_fill = o * (1 + adv)
            total_delta += (modeled_fill - actual_fill) * t.units
            n_gapped += 1
    return total_delta, n_gapped


# ---------------------------------------------------------------------------
# FAMILY 1 — trend champion port (vol_gated_ma, long-only)
# ---------------------------------------------------------------------------

def trend_signal(d, fast, slow, gate_mode):
    if gate_mode == "ungated":
        return vol_gated_ma(d, fast, slow, min_atr_pct=0.0, allow_short=False)
    if gate_mode == "fixed1.0":
        return vol_gated_ma(d, fast, slow, min_atr_pct=1.0, allow_short=False)
    if gate_mode == "fixed1.5":
        return vol_gated_ma(d, fast, slow, min_atr_pct=1.5, allow_short=False)
    if gate_mode == "adaptive":
        gate, _ = adaptive_vol_gate(d, direction="above")
        return vol_gated_ma(d, fast, slow, min_atr_pct=0.0, allow_short=False,
                             entry_filter=gate)
    raise ValueError(gate_mode)


def family1_trend(frames, meta):
    rows = []
    for symbol in SYMBOLS:
        for tf, pairs in (("1d", ((20, 100), (50, 200))),
                          ("1h", ((20, 100), (80, 400)))):
            d = frames[symbol][tf]
            m = meta[symbol][tf]
            costs = costs_for(symbol)
            for fast, slow in pairs:
                for gate_mode in ("adaptive", "fixed1.0", "fixed1.5", "ungated"):
                    sig = trend_signal(d, fast, slow, gate_mode)
                    tr, va = score(d, sig, costs, m["i_tr"], m["i_va"])
                    rows.append(mk_row("1-trend", f"{fast}/{slow} {gate_mode}",
                                        symbol, tf, tr, va))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 2 — dip-buy port (RSI3 dip in an established uptrend)
# ---------------------------------------------------------------------------

def event_long(d, enter, exit_, max_hold=0):
    e = enter.fillna(False).to_numpy(dtype=bool)
    x = exit_.fillna(False).to_numpy(dtype=bool)
    out, pos, held = [], 0.0, 0
    for i in range(len(d)):
        if pos == 0.0:
            if e[i]:
                pos, held = 1.0, 0
        else:
            held += 1
            if x[i] or (max_hold and held >= max_hold):
                pos = 0.0
        out.append(pos)
    return pd.Series(out, index=d.index)


def dip_buy_signal(d, rsi_thresh, max_hold_bars, rsi_n=3):
    r = rsi(d["close"], rsi_n)
    sma100 = d["close"].rolling(100).mean()
    enter = (r < rsi_thresh) & (d["close"] > sma100)
    exit_ = pd.Series(False, index=d.index)   # exits via stop/target/max_hold only
    return event_long(d, enter.fillna(False), exit_, max_hold_bars)


def family2_dipbuy(frames, meta):
    rows = []
    for symbol in SYMBOLS:
        for tf in ("1d", "1h"):
            d = frames[symbol][tf]
            m = meta[symbol][tf]
            costs = costs_for(symbol)
            med_atr = m["med_atr"]
            for rsi_thresh in (5, 10):
                for stop_mult in (0.7, 1.0):
                    stop_pct = stop_mult * med_atr
                    target_pct = 3.0 * stop_pct
                    if tf == "1d":
                        hold_variants = [("hold5d", days_to_bars(d, 5)),
                                          ("hold10d", days_to_bars(d, 10))]
                    else:
                        hold_variants = [("hold48h", hours_to_bars(d, 48))]
                    for hold_tag, mh in hold_variants:
                        sig = dip_buy_signal(d, rsi_thresh, mh)
                        tr, va = score(d, sig, costs, m["i_tr"], m["i_va"],
                                       stop_pct=stop_pct, target_pct=target_pct)
                        cfg = f"rsi3<{rsi_thresh} stop{stop_mult}xATR({stop_pct:.2f}%) {hold_tag}"
                        d_tr = d.iloc[:m["i_tr"]].reset_index(drop=True)
                        d_va = d.iloc[m["i_tr"]:m["i_va"]].reset_index(drop=True)
                        gap_tr, n_tr = gap_honesty_correction(d_tr, tr.trades, stop_pct, costs)
                        gap_va, n_va = gap_honesty_correction(d_va, va.trades, stop_pct, costs)
                        extra = {
                            "tr_exp_gapadj": tr.expectancy + (gap_tr / len(tr.trades) if tr.trades else 0.0),
                            "va_exp_gapadj": va.expectancy + (gap_va / len(va.trades) if va.trades else 0.0),
                            "tr_gapped_n": n_tr, "va_gapped_n": n_va,
                            "stop_pct": stop_pct, "target_pct": target_pct,
                        }
                        rows.append(mk_row("2-dipbuy", cfg, symbol, tf, tr, va, extra))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 3 — breakout port (Donchian + EMA20 exit, long only, daily)
# ---------------------------------------------------------------------------

def donchian_ema_exit(d, entry_n, ema_n=20):
    hi = d["high"].rolling(entry_n).max().shift(1)
    enter = d["close"] > hi
    ema = d["close"].ewm(span=ema_n, adjust=False).mean()
    exit_ = d["close"] < ema
    return _hysteresis(enter.fillna(False), exit_.fillna(False))


def family3_breakout(frames, meta):
    rows = []
    for symbol in SYMBOLS:
        d = frames[symbol]["1d"]
        m = meta[symbol]["1d"]
        costs = costs_for(symbol)
        for N in (20, 55):
            sig = donchian_ema_exit(d, N, ema_n=20)
            tr, va = score(d, sig, costs, m["i_tr"], m["i_va"])
            rows.append(mk_row("3-breakout", f"donchian{N} EMA20exit", symbol, "1d", tr, va))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 4 — mirrored shorts (QQQ + GLD daily only, per task)
# ---------------------------------------------------------------------------

def trend_short_signal(d, fast, slow, gate_mode):
    if gate_mode == "ungated":
        sig = vol_gated_ma(d, fast, slow, min_atr_pct=0.0, allow_short=True)
    elif gate_mode == "fixed1.0":
        sig = vol_gated_ma(d, fast, slow, min_atr_pct=1.0, allow_short=True)
    elif gate_mode == "fixed1.5":
        sig = vol_gated_ma(d, fast, slow, min_atr_pct=1.5, allow_short=True)
    elif gate_mode == "adaptive":
        gate, _ = adaptive_vol_gate(d, direction="above")
        sig = vol_gated_ma(d, fast, slow, min_atr_pct=0.0, allow_short=True, entry_filter=gate)
    else:
        raise ValueError(gate_mode)
    return sig.clip(upper=0.0)          # mirror: keep only the short side


def donchian_short_ema_exit(d, entry_n, ema_n=20):
    lo = d["low"].rolling(entry_n).min().shift(1)
    enter_short = d["close"] < lo
    ema = d["close"].ewm(span=ema_n, adjust=False).mean()
    exit_ = d["close"] > ema
    never_long = pd.Series(False, index=d.index)
    return _hysteresis(never_long, exit_.fillna(False), short_enter=enter_short.fillna(False))


def family4_shorts(frames, meta):
    rows = []
    for symbol in ("QQQ", "GLD"):
        d = frames[symbol]["1d"]
        m = meta[symbol]["1d"]
        costs = costs_for(symbol)
        for fast, slow in ((20, 100), (50, 200)):
            for gate_mode in ("adaptive", "fixed1.0", "fixed1.5", "ungated"):
                sig = trend_short_signal(d, fast, slow, gate_mode)
                tr, va = score(d, sig, costs, m["i_tr"], m["i_va"])
                rows.append(mk_row("4-short-trend", f"{fast}/{slow} {gate_mode}",
                                    symbol, "1d", tr, va))
        for N in (20, 55):
            sig = donchian_short_ema_exit(d, N)
            tr, va = score(d, sig, costs, m["i_tr"], m["i_va"])
            rows.append(mk_row("4-short-breakout", f"donchian{N} EMA20exit",
                                symbol, "1d", tr, va))
    return rows


# ---------------------------------------------------------------------------
# decade-by-decade consistency (TRAIN+VAL only — test stays sealed)
# ---------------------------------------------------------------------------

def decade_breakdown(d, sig, costs, i_va, stop_pct=None, target_pct=None):
    res = run_backtest(d.iloc[:i_va].reset_index(drop=True),
                        sig.iloc[:i_va].reset_index(drop=True),
                        costs=costs, execution="taker",
                        stop_pct=stop_pct, target_pct=target_pct)
    by_decade = {}
    for t in res.trades:
        dec = (t.entry_time.year // 10) * 10
        rec = by_decade.setdefault(dec, {"n": 0, "pnl": 0.0})
        rec["n"] += 1
        rec["pnl"] += t.pnl
    return by_decade


def print_decade_breakdown(tag, by_decade):
    parts = []
    for dec in sorted(by_decade):
        r = by_decade[dec]
        parts.append(f"{dec}s: n={r['n']} exp=${r['pnl']/r['n']:+.2f}" if r["n"]
                      else f"{dec}s: n=0")
    print(f"  [{tag}] " + " | ".join(parts))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("=" * 78)
    print("ROUND 48 — porting proven crypto strategy shapes to GOLD & NASDAQ")
    print("=" * 78)

    frames = load_all_data()

    meta = {s: {} for s in SYMBOLS}
    print("\nSpans + split points + median TRAIN ATR% (the market-native scale "
          "every stop/gate below is expressed in):")
    for symbol in SYMBOLS:
        for tf in ("1d", "1h"):
            d = frames[symbol][tf]
            n, i_tr, i_va = split_points(d)
            atr_pct = atr(d, 14) / d["close"] * 100
            med_atr_train = float(atr_pct.iloc[:i_tr].median())
            meta[symbol][tf] = {"n": n, "i_tr": i_tr, "i_va": i_va, "med_atr": med_atr_train}
            gaps = gap_stats_summary(d, [0.7 * med_atr_train, 1.0 * med_atr_train,
                                          1.5 * med_atr_train, 1.0, 1.5])
            print(f"  {symbol:5s} {tf}: {n:5d} bars {d['timestamp'].iloc[0]:%Y-%m-%d}->"
                  f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
                  f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed) | "
                  f"med train ATR%={med_atr_train:.2f}% | gap>thresh: {gaps}")

    print("\nRunning FAMILY 1 (trend champion port: vol_gated_ma, long-only)...")
    rows = family1_trend(frames, meta)
    print("Running FAMILY 2 (dip-buy port: RSI3 dip in uptrend)...")
    rows += family2_dipbuy(frames, meta)
    print("Running FAMILY 3 (breakout port: Donchian + EMA20 exit)...")
    rows += family3_breakout(frames, meta)
    print("Running FAMILY 4 (mirrored shorts: QQQ + GLD daily)...")
    rows += family4_shorts(frames, meta)

    df = pd.DataFrame(rows)
    print(f"\n{len(df)} configs tested. Verdict counts:")
    print(df["verdict"].value_counts().to_string())

    print("\nFull results (train + val, full costs, test sealed):")
    with pd.option_context("display.max_rows", None, "display.width", 240,
                            "display.max_columns", None):
        cols = ["family", "config", "symbol", "market", "tf", "tr_n", "tr_exp",
                "tr_win%", "tr_dd%", "tr_ret%", "va_n", "va_exp", "va_win%",
                "va_dd%", "va_ret%", "verdict"]
        print(df[cols].sort_values(["family", "symbol", "tf", "tr_exp"],
                                    ascending=[True, True, True, False])
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    dip = df[df["family"] == "2-dipbuy"]
    if len(dip):
        print("\nFamily 2 (dip-buy) gap-honesty detail (raw engine exp vs gap-corrected):")
        gcols = ["config", "symbol", "tf", "tr_exp", "tr_exp_gapadj", "tr_gapped_n",
                  "va_exp", "va_exp_gapadj", "va_gapped_n"]
        print(dip[gcols].to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    survivors = df[df["verdict"] == "SURVIVOR"]
    near = df[df["verdict"] == "INSUFFICIENT-SAMPLE"]
    print(f"\nSURVIVORS (positive train+val, >={MIN_TRAIN_TRADES} train / "
          f">={MIN_VAL_TRADES} val trades): {len(survivors)}")
    if len(survivors):
        print(survivors[["family", "config", "symbol", "tf", "tr_n", "tr_exp",
                          "va_n", "va_exp"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    print(f"\nINSUFFICIENT-SAMPLE (positive both windows, under the trade-count bar): "
          f"{len(near)}")
    if len(near):
        print(near[["family", "config", "symbol", "tf", "tr_n", "tr_exp",
                     "va_n", "va_exp"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    print("\nDecade-by-decade consistency (TRAIN+VAL only, daily configs that are "
          "SURVIVOR or INSUFFICIENT-SAMPLE — test window NEVER touched):")
    daily_candidates = pd.concat([survivors, near])
    daily_candidates = daily_candidates[daily_candidates["tf"] == "1d"]
    for _, row in daily_candidates.iterrows():
        symbol, family, config = row["symbol"], row["family"], row["config"]
        d = frames[symbol]["1d"]
        m = meta[symbol]["1d"]
        costs = costs_for(symbol)
        stop_pct = row.get("stop_pct")
        target_pct = row.get("target_pct")
        if family == "1-trend":
            fast_slow, gate_mode = config.split(" ", 1)
            fast, slow = (int(x) for x in fast_slow.split("/"))
            sig = trend_signal(d, fast, slow, gate_mode)
        elif family == "2-dipbuy":
            rsi_thresh = int(config.split("rsi3<")[1].split(" ")[0])
            hold_tag = config.split(" ")[-1]
            mh = days_to_bars(d, 5) if hold_tag == "hold5d" else days_to_bars(d, 10)
            sig = dip_buy_signal(d, rsi_thresh, mh)
        elif family == "3-breakout":
            N = int(config.replace("donchian", "").split(" ")[0])
            sig = donchian_ema_exit(d, N)
        elif family == "4-short-trend":
            fast_slow, gate_mode = config.split(" ", 1)
            fast, slow = (int(x) for x in fast_slow.split("/"))
            sig = trend_short_signal(d, fast, slow, gate_mode)
        elif family == "4-short-breakout":
            N = int(config.replace("donchian", "").split(" ")[0])
            sig = donchian_short_ema_exit(d, N)
        else:
            continue
        by_decade = decade_breakdown(d, sig, costs, m["i_va"],
                                      stop_pct=stop_pct if pd.notna(stop_pct) else None,
                                      target_pct=target_pct if pd.notna(target_pct) else None)
        print_decade_breakdown(f"{family} {config} {symbol}", by_decade)

    print("\nDone. No sealed-test window was ever sliced or scored above.")
    return df


if __name__ == "__main__":
    main()
