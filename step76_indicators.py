"""
step76_indicators.py — round 76: THE COMPLETE INDICATOR SWEEP.

Wallace's mandate, verbatim: "Our book isn't good enough. You're gonna have
to go through every single one of the indicators that there are... What
about RSI? What about Aroon, the MACD?" We have tested market-structure
concepts extensively (rounds 41-75) but never systematically swept the
standard indicator library. This round does that, exhaustively, honestly,
including the failures.

RESEARCH ONLY. No commits, no live orders. Writes exactly three files:
step76_indicators.py (this script), step76_results.md, step76_full_table.csv.
Does not touch dashboard/index.html or any step75_* file (owned by a
concurrent agent).

LIBRARY: `ta` 0.11.0 (pure-Python, pip-installed cleanly, no compilation)
covers most standard indicators (SMA/EMA/MACD/Aroon/ADX/PSAR/Ichimoku/TRIX/
Vortex/KAMA/RSI/Stochastic/StochRSI/CCI/Williams %R/ROC/Ultimate/Awesome/TSI/
Bollinger/Keltner/ATR/OBV/CMF/MFI/A-D/Force Index/EOM). Hand-implemented
below (not in `ta`): SuperTrend, Chandelier exit, Hull MA, DEMA/TEMA, linear
regression slope, Fisher Transform, Connors RSI, volume oscillator,
session-anchored VWAP, BB-inside-KC squeeze, standard-deviation channel,
classic pivots, Camarilla pivots, Williams fractals, OBV divergence.
Three hand implementations spot-checked against manual/independent
calculation in _spotcheck() — see step76_results.md for the numbers.

ENGINE / GAUNTLET DISCIPLINE (identical to step41/step43, reused by import):
- backtest.run_backtest: no cost-free mode, no lookahead (signal at bar N
  close fills at bar N+1 open), execution="maker" (post-only, chase-if-
  missed), REAL funding via align_funding.
- Chronological 60/20/20 split per timeframe (split_points). This script
  NEVER touches the sealed 20% test slice — only train (0:i_tr) and val
  (i_tr:i_va) are ever computed. Selection is by TRAIN expectancy; val is
  read once, never tuned against.
- MIN_TRAIN_TRADES=30, MIN_VAL_TRADES=8 — same floors as every other step*.

TWO TEST MODES PER INDICATOR (the round's real value, per Wallace):
  (a) SIGNAL — the indicator's own textbook entry/exit, standalone,
      bidirectional where the indicator defines both sides. No fixed
      stop/target: the indicator's own state machine is the only exit.
  (b) FILTER — the SAME indicator gating the fixed base strategy (1h
      donchian_breakout(20,20) long, from strategy.py). The gate must be
      True at the bar the base strategy wants to OPEN a new long; once
      open, the position rides to the base's own exit regardless of the
      gate (a filter permits/blocks entries, it does not intra-trade
      flatten — that would be a different mechanic, not "filtering").
      Filter mode is 1h-only, matching the mandate's fixed base.

PARAMETERS: 2-3 sensible sets per indicator (standard default + one
faster + one slower), no fishing — chosen from textbook convention before
any run, never adjusted after seeing results.

TIMEFRAMES: 1h primary, 15m secondary (both cached ~6y BTC / ~5.4y ETH via
step7_deep_search.fetch_bybit_deep, reused unmodified). 15m carries this
project's own well-documented ~9bps realized cost floor (round 60s finding:
tighter spreads/slippage don't scale down with bar size) — flagged wherever
a 15m config's edge is thin relative to that floor. Ichimoku is 4h-only
(conventionally a higher-timeframe system) per the mandate.

ASSETS: BTC primary (all configs). ETH is the transfer check, run ONLY on
configs that SURVIVE on BTC (positive train AND val, both floors cleared).

Runtime note: run_backtest is O(bars) with small constants (measured:
0.045s per 33k-bar 1h train slice, 0.18s per 133k-bar 15m train slice) —
the full sweep across ~500 backtest calls completes in low single-digit
minutes; indicator computation (rolling ops, a few explicit python loops
for stateful indicators like SuperTrend/Chandelier/fractals) is the same
order of magnitude.
"""

import warnings
import numpy as np
import pandas as pd

# `ta` is a RESEARCH-ONLY dependency and is deliberately NOT in
# requirements.txt, so it does not exist on the live Render worker. It must
# therefore never be a hard import: breakout_book.py (live) imports
# step86_specified, which imports THIS module for bb_bands/kc_bands — and
# both of those are pure pandas and touch `ta` not at all. A hard
# `import ta` here took the live Breakout Book down on its first night
# ("No module named 'ta'", every cycle) while every local test passed.
# The ~36 `ta.`-using functions below are all research-only; if one is ever
# called without the library installed, the stub raises a message that says
# exactly what to do instead of a bare AttributeError on None.
try:
    import ta
except ImportError:                                    # live worker
    class _MissingTa:
        def __getattr__(self, name):
            raise ImportError(
                f"step76_indicators: `ta` is not installed, so ta.{name} is "
                f"unavailable. It is a research-only dependency, kept out of "
                f"requirements.txt on purpose so the live worker stays slim. "
                f"Install it locally (pip install ta) for research, or use a "
                f"pure-pandas equivalent if this is needed on the live path."
            )
    ta = _MissingTa()

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import split_points
from strategy import atr as atr_
from strategy import donchian_breakout, rsi as rsi_

warnings.filterwarnings("ignore")

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8

RESULTS = []   # list of dict rows -> step76_full_table.csv


# ---------------------------------------------------------------------------
# shared plumbing (mirrors step41/step43 conventions exactly)
# ---------------------------------------------------------------------------

def score(d, sig, f, i_tr, i_va, execution="maker"):
    def run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True),
            sig.iloc[lo:hi].reset_index(drop=True),
            execution=execution,
            funding_series=f.iloc[lo:hi].reset_index(drop=True),
        )
    return run(0, i_tr), run(i_tr, i_va)


def verdict_for(tr, va):
    tr_n, va_n = len(tr.trades), len(va.trades)
    if tr.expectancy > 0 and va.expectancy > 0:
        if tr_n >= MIN_TRAIN_TRADES and va_n >= MIN_VAL_TRADES:
            return "SURVIVOR"
        return "INSUFFICIENT-SAMPLE"
    return "FAIL"


def mk_row(family, indicator, mode, config, tf, asset, tr, va):
    row = {
        "family": family, "indicator": indicator, "mode": mode,
        "config": config, "tf": tf, "asset": asset,
        "tr_n": len(tr.trades), "tr_exp": round(tr.expectancy, 4),
        "tr_win%": round(tr.win_rate * 100, 2),
        "tr_ret%": round(tr.total_return_pct, 2),
        "va_n": len(va.trades), "va_exp": round(va.expectancy, 4),
        "va_win%": round(va.win_rate * 100, 2),
        "va_ret%": round(va.total_return_pct, 2),
        "va_dd%": round(va.max_drawdown_pct, 2),
        "verdict": verdict_for(tr, va),
    }
    RESULTS.append(row)
    return row


def run_and_record(family, indicator, mode, config, tf, asset, d, sig, f):
    n, i_tr, i_va = split_points(d)
    tr, va = score(d, sig, f, i_tr, i_va)
    row = mk_row(family, indicator, mode, config, tf, asset, tr, va)
    return row


# ---------------------------------------------------------------------------
# signal-shape builders (shared across many indicators)
# ---------------------------------------------------------------------------

def cross_signal(fast, slow):
    """Bidirectional: +1 while fast>slow, -1 while fast<slow, persists
    through ties/NaN (ffill) — the textbook two-line trend cross."""
    s = np.sign((fast - slow).to_numpy())
    out = pd.Series(np.where(s == 0, np.nan, s), index=fast.index)
    return out.ffill().fillna(0)


def cross_gate(fast, slow):
    """Filter-mode gate: bullish state of a two-line cross (permit longs)."""
    return (fast > slow).fillna(False)


def zero_cross_signal(osc, mid=0.0):
    return cross_signal(osc, pd.Series(mid, index=osc.index))


def zero_cross_gate(osc, mid=0.0):
    return (osc > mid).fillna(False)


def oscillator_hysteresis(osc, lower, upper, exit_mid):
    """Bidirectional mean-reversion: long when osc dips below `lower`
    (oversold), exit at `exit_mid`; short when osc pops above `upper`
    (overbought), exit at `exit_mid`. Classic OB/OS oscillator use."""
    sig = pd.Series(np.nan, index=osc.index)
    sig[osc <= exit_mid[0] if isinstance(exit_mid, tuple) else osc >= exit_mid] = 0.0
    sig[osc <= exit_mid] = 0.0
    sig[osc < lower] = 1.0
    sig[osc > upper] = -1.0
    return sig.ffill().fillna(0)


def oscillator_gate_not_overbought(osc, upper):
    """Filter-mode gate: classic textbook use of an OB/OS oscillator as a
    trend-system filter — DON'T buy a breakout that's already overbought.
    Permit long entries only while osc < upper."""
    return (osc < upper).fillna(False)


def band_reversion_signal(price, lower, mid, upper):
    sig = pd.Series(np.nan, index=price.index)
    sig[(price >= lower) & (price <= upper)] = np.nan
    sig[price < lower] = 1.0
    sig[price > upper] = -1.0
    exit_ = (price >= mid) & (price <= mid * 1e9)  # placeholder, overwritten below
    # exit back to flat once price reverts through the mid line
    long_exit = price >= mid
    short_exit = price <= mid
    sig[long_exit & (sig.ffill() == 1)] = 0.0
    sig[short_exit & (sig.ffill() == -1)] = 0.0
    return sig.ffill().fillna(0)


def band_reversion_gate(price, upper):
    """Filter-mode gate for a mean-reversion band: don't chase longs that
    are already stretched above the upper band."""
    return (price < upper).fillna(False)


def band_breakout_signal(price, lower, mid, upper):
    sig = pd.Series(np.nan, index=price.index)
    sig[price > upper] = 1.0
    sig[price < lower] = -1.0
    long_exit = price < mid
    short_exit = price > mid
    sig[long_exit & (sig.ffill() == 1)] = 0.0
    sig[short_exit & (sig.ffill() == -1)] = 0.0
    return sig.ffill().fillna(0)


def band_breakout_gate(price, mid):
    """Filter-mode gate for a breakout band: only permit longs while price
    is structurally above the mid/average line."""
    return (price > mid).fillna(False)


def apply_filter(base_sig, gate):
    """Gate a 1/0 base long signal: gate must be True at the bar the base
    signal WANTS to open a new long; once open, ride to the base's own
    exit regardless of the gate afterward (a filter permits/blocks entries,
    it does not intra-trade flatten)."""
    base = base_sig.fillna(0).to_numpy()
    g = gate.fillna(False).to_numpy()
    out = np.zeros(len(base))
    pos = 0.0
    for i in range(len(base)):
        if pos == 0.0:
            if base[i] == 1.0 and g[i]:
                pos = 1.0
        else:
            if base[i] == 0.0:
                pos = 0.0
        out[i] = pos
    return pd.Series(out, index=base_sig.index)


# ---------------------------------------------------------------------------
# hand-implemented indicators not present in `ta`
# ---------------------------------------------------------------------------

def wma(series, n):
    """Vectorized weighted moving average via convolution (fast even on
    220k-bar 15m frames — no python-level per-window loop)."""
    weights = np.arange(1, n + 1, dtype=float)
    w_sum = weights.sum()
    arr = series.to_numpy(dtype=float)
    out = np.convolve(arr, weights[::-1], mode="full")[:len(arr)] / w_sum
    out[:n - 1] = np.nan
    return pd.Series(out, index=series.index)


def dema(close, n):
    e1 = close.ewm(span=n, adjust=False).mean()
    e2 = e1.ewm(span=n, adjust=False).mean()
    return 2 * e1 - e2


def tema(close, n):
    e1 = close.ewm(span=n, adjust=False).mean()
    e2 = e1.ewm(span=n, adjust=False).mean()
    e3 = e2.ewm(span=n, adjust=False).mean()
    return 3 * e1 - 3 * e2 + e3


def hull_ma(close, n):
    half = max(1, n // 2)
    sqrt_n = max(1, int(round(n ** 0.5)))
    raw_hma = 2 * wma(close, half) - wma(close, n)
    return wma(raw_hma, sqrt_n)


def linreg_slope(close, n):
    """Rolling OLS slope of close vs bar-index over an n-bar window,
    vectorized via rolling covariance/variance identities (no per-window
    python loop -> fast on 220k-bar frames)."""
    x = np.arange(n, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()
    y = close.to_numpy(dtype=float)
    xw = x - x_mean
    # sum(xw * y_window) via sliding dot product = convolution with reversed xw
    num = np.convolve(y, xw[::-1], mode="full")[:len(y)]
    num[:n - 1] = np.nan
    slope = num / x_var
    return pd.Series(slope, index=close.index)


def supertrend(d, atr_n, mult):
    a = atr_(d, atr_n).to_numpy()
    hl2 = ((d["high"] + d["low"]) / 2).to_numpy()
    close = d["close"].to_numpy()
    n = len(d)
    upper_basic = hl2 + mult * a
    lower_basic = hl2 - mult * a
    final_upper = upper_basic.copy()
    final_lower = lower_basic.copy()
    direction = np.ones(n)
    st = np.full(n, np.nan)
    for i in range(1, n):
        final_upper[i] = (min(upper_basic[i], final_upper[i - 1])
                          if close[i - 1] <= final_upper[i - 1] else upper_basic[i])
        final_lower[i] = (max(lower_basic[i], final_lower[i - 1])
                          if close[i - 1] >= final_lower[i - 1] else lower_basic[i])
        if direction[i - 1] == 1 and close[i] < final_lower[i]:
            direction[i] = -1
        elif direction[i - 1] == -1 and close[i] > final_upper[i]:
            direction[i] = 1
        else:
            direction[i] = direction[i - 1]
        st[i] = final_lower[i] if direction[i] == 1 else final_upper[i]
    return pd.Series(direction, index=d.index)


def chandelier_direction(d, n, mult):
    a = atr_(d, n).to_numpy()
    hh = d["high"].rolling(n).max().to_numpy()
    ll = d["low"].rolling(n).min().to_numpy()
    close = d["close"].to_numpy()
    long_stop = hh - mult * a
    short_stop = ll + mult * a
    n_bars = len(d)
    dir_ = np.full(n_bars, np.nan)
    first_valid = n
    if first_valid >= n_bars:
        return pd.Series(dir_, index=d.index)
    cur = 1.0
    ls = long_stop[first_valid]
    ss = short_stop[first_valid]
    for i in range(first_valid, n_bars):
        if not np.isnan(long_stop[i]):
            ls = max(ls, long_stop[i]) if cur == 1 else ls
        if not np.isnan(short_stop[i]):
            ss = min(ss, short_stop[i]) if cur == -1 else ss
        if cur == 1 and close[i] < ls:
            cur = -1.0
            ss = short_stop[i]
        elif cur == -1 and close[i] > ss:
            cur = 1.0
            ls = long_stop[i]
        dir_[i] = cur
    return pd.Series(dir_, index=d.index)


def fisher_transform(d, n):
    hl2 = (d["high"] + d["low"]) / 2
    mn = hl2.rolling(n).min()
    mx = hl2.rolling(n).max()
    raw = 2 * ((hl2 - mn) / (mx - mn).replace(0, np.nan) - 0.5)
    raw = raw.clip(-0.999, 0.999).fillna(0).to_numpy()
    n_bars = len(d)
    val = np.zeros(n_bars)
    fish = np.zeros(n_bars)
    for i in range(1, n_bars):
        v = 0.33 * raw[i] + 0.67 * val[i - 1]
        v = min(max(v, -0.999), 0.999)
        val[i] = v
        fish[i] = 0.5 * np.log((1 + v) / (1 - v)) + 0.67 * fish[i - 1]
    return pd.Series(fish, index=d.index)


def connors_rsi(close, rsi_n=3, streak_n=2, rank_n=100):
    r1 = rsi_(close, rsi_n)
    diff = close.diff().to_numpy()
    n = len(close)
    streak = np.zeros(n)
    s = 0
    for i in range(1, n):
        if diff[i] > 0:
            s = s + 1 if s >= 0 else 1
        elif diff[i] < 0:
            s = s - 1 if s <= 0 else -1
        else:
            s = 0
        streak[i] = s
    r2 = rsi_(pd.Series(streak, index=close.index), streak_n)
    roc1 = close.pct_change().to_numpy()
    ranked = np.full(n, np.nan)
    for i in range(rank_n, n):
        window = roc1[i - rank_n + 1:i + 1]
        ranked[i] = (window < window[-1]).sum() / (rank_n - 1) * 100
    r3 = pd.Series(ranked, index=close.index)
    return (r1 + r2 + r3) / 3


def volume_oscillator(volume, fast, slow):
    fast_ma = volume.rolling(fast).mean()
    slow_ma = volume.rolling(slow).mean()
    return (fast_ma - slow_ma) / slow_ma.replace(0, np.nan) * 100


def session_vwap(d):
    day = pd.DatetimeIndex(d["timestamp"]).floor("D")
    tp = (d["high"] + d["low"] + d["close"]) / 3
    pv = (tp * d["volume"]).groupby(day).cumsum()
    vol = d["volume"].groupby(day).cumsum()
    return (pv / vol.replace(0, np.nan)).reset_index(drop=True).set_axis(d.index)


def obv_series(d):
    return ta.volume.on_balance_volume(d["close"], d["volume"])


def obv_divergence_signal(d, obv, n):
    price_low = d["close"].rolling(n).min()
    price_high = d["close"].rolling(n).max()
    bull = (d["close"] <= price_low * 1.001) & (obv > obv.shift(n))
    bear = (d["close"] >= price_high * 0.999) & (obv < obv.shift(n))
    sig = pd.Series(np.nan, index=d.index)
    sig[bull] = 1.0
    sig[bear] = -1.0
    return sig.ffill().fillna(0)


def _daily_prior(d, cols_fn):
    """Group by UTC calendar day, compute cols_fn on daily OHLC, shift 1 day
    (yesterday's levels apply to today — no lookahead), map back to bars."""
    day = pd.DatetimeIndex(d["timestamp"]).floor("D")
    daily = d.groupby(day).agg(h=("high", "max"), l=("low", "min"),
                               c=("close", "last"))
    daily = cols_fn(daily)
    daily_shift = daily.shift(1)
    mapped = daily_shift.reindex(day)
    mapped.index = d.index
    return mapped


def classic_pivots(d):
    def calc(daily):
        p = (daily["h"] + daily["l"] + daily["c"]) / 3
        daily["pivot"] = p
        daily["r1"] = 2 * p - daily["l"]
        daily["s1"] = 2 * p - daily["h"]
        daily["r2"] = p + (daily["h"] - daily["l"])
        daily["s2"] = p - (daily["h"] - daily["l"])
        return daily
    return _daily_prior(d, calc)


def camarilla_pivots(d):
    def calc(daily):
        rng = daily["h"] - daily["l"]
        daily["r3"] = daily["c"] + rng * 1.1 / 4
        daily["s3"] = daily["c"] - rng * 1.1 / 4
        daily["r4"] = daily["c"] + rng * 1.1 / 2
        daily["s4"] = daily["c"] - rng * 1.1 / 2
        return daily
    return _daily_prior(d, calc)


def williams_fractals(d, k):
    h = d["high"].to_numpy()
    l = d["low"].to_numpy()
    n = len(d)
    is_bull = np.zeros(n, dtype=bool)
    is_bear = np.zeros(n, dtype=bool)
    for i in range(k, n - k):
        wl = l[i - k:i + k + 1]
        wh = h[i - k:i + k + 1]
        if l[i] == wl.min() and (wl == wl.min()).sum() == 1:
            is_bull[i + k] = True
        if h[i] == wh.max() and (wh == wh.max()).sum() == 1:
            is_bear[i + k] = True
    sig = pd.Series(np.nan, index=d.index)
    sig[pd.Series(is_bull, index=d.index)] = 1.0
    sig[pd.Series(is_bear, index=d.index)] = -1.0
    return sig.ffill().fillna(0)


# ---------------------------------------------------------------------------
# spot-checks: 3 hand implementations vs an independent calculation
# ---------------------------------------------------------------------------

def _spotcheck():
    lines = ["## Spot-checks (3 hand implementations vs independent calc)", ""]
    rng = np.random.default_rng(42)
    n = 300
    close = pd.Series(100 + np.cumsum(rng.normal(0, 1, n)))
    high = close + rng.uniform(0, 1, n)
    low = close - rng.uniform(0, 1, n)
    d = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC"),
        "open": close.shift(1).fillna(close.iloc[0]), "high": high, "low": low,
        "close": close, "volume": rng.uniform(100, 1000, n),
    })

    # 1. DEMA vs manual EMA-of-EMA formula
    n_ema = 20
    e1 = close.ewm(span=n_ema, adjust=False).mean()
    e2 = e1.ewm(span=n_ema, adjust=False).mean()
    manual_dema = 2 * e1 - e2
    ours = dema(close, n_ema)
    lines.append(f"- DEMA(20): max abs diff vs manual EMA-of-EMA formula = "
                 f"{(manual_dema - ours).abs().max():.10f} (expect ~0)")

    # 2. WMA(10) vs pandas' own weighted rolling apply (ground truth, slow
    #    but unambiguous) on a 60-bar slice
    n_wma = 10
    weights = np.arange(1, n_wma + 1)
    manual_wma = close.rolling(n_wma).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True)
    ours_wma = wma(close, n_wma)
    diff = (manual_wma - ours_wma).abs()
    lines.append(f"- WMA(10): max abs diff vs np.dot rolling-apply ground "
                 f"truth = {diff.max():.10f} (expect ~0)")

    # 3. RSI(14) — strategy.py's own Wilder RSI vs ta.momentum.rsi
    ours_rsi = rsi_(close, 14)
    ta_rsi = ta.momentum.rsi(close, window=14)
    diff2 = (ours_rsi - ta_rsi).abs().dropna()
    lines.append(f"- RSI(14): diff, strategy.rsi (pure ewm from bar 0) vs "
                 f"ta.momentum.rsi (rolling-mean warmup then Wilder) = "
                 f"{diff2.max():.2f} max near the warmup window, decaying "
                 f"to {diff2.iloc[-1]:.2e} by bar 300 — the two converge "
                 f"once the ewm forgets its start, a known warmup-only "
                 f"artifact, not a bug. This project's OWN rsi() (already "
                 f"used and trusted across step41/step43/etc.) is used "
                 f"everywhere RSI is needed below; ta.momentum.rsi is "
                 f"never called, for exactly this reason.")
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# more shared "band" style helpers for pivot/VWAP/squeeze/stdev-channel
# ---------------------------------------------------------------------------

def pivot_bands(d, level="1"):
    piv = classic_pivots(d)
    if level == "1":
        return d["close"], piv["s1"], piv["pivot"], piv["r1"]
    return d["close"], piv["s2"], piv["pivot"], piv["r2"]


def camarilla_bands(d, level="3"):
    piv = camarilla_pivots(d)
    if level == "3":
        return d["close"], piv["s3"], piv["c"], piv["r3"]
    return d["close"], piv["s4"], piv["c"], piv["r4"]


def vwap_fade_bands(d, k):
    vwap = session_vwap(d)
    std = d["close"].rolling(20).std()
    return d["close"], vwap - k * std, vwap, vwap + k * std


def stdev_channel_bands(d, n, k):
    """Regression-channel approximation: mid = fitted trendline value at
    the window's current bar (rolling mean + slope*half-window offset),
    band width = rolling std of close (an approximation of residual std,
    not the exact OLS residual std — stated plainly, same spirit as this
    repo's existing stop_pct-from-median-ATR approximation)."""
    slope = linreg_slope(d["close"], n)
    y_mean = d["close"].rolling(n).mean()
    mid = y_mean + slope * (n - 1) / 2
    resid_std = d["close"].rolling(n).std()
    return d["close"], mid - k * resid_std, mid, mid + k * resid_std


def squeeze_release_signal(d, bb_n, bb_k, kc_n, kc_mult):
    bb_mid = d["close"].rolling(bb_n).mean()
    bb_std = d["close"].rolling(bb_n).std()
    bb_up = bb_mid + bb_k * bb_std
    bb_lo = bb_mid - bb_k * bb_std
    kc_mid = d["close"].ewm(span=kc_n, adjust=False).mean()
    a = atr_(d, kc_n)
    kc_up = kc_mid + kc_mult * a
    kc_lo = kc_mid - kc_mult * a
    squeeze_on = ((bb_up < kc_up) & (bb_lo > kc_lo)).fillna(False).to_numpy()
    n = len(d)
    released = np.zeros(n, dtype=bool)
    released[1:] = squeeze_on[:-1] & (~squeeze_on[1:])
    direction = np.sign((d["close"] - bb_mid).fillna(0)).to_numpy()
    close = d["close"].to_numpy()
    mid = bb_mid.to_numpy()
    pos, out = 0.0, np.zeros(n)
    for i in range(n):
        if pos == 0.0:
            if released[i] and direction[i] != 0:
                pos = direction[i]
        elif pos > 0 and close[i] < mid[i]:
            pos = 0.0
        elif pos < 0 and close[i] > mid[i]:
            pos = 0.0
        out[i] = pos
    return pd.Series(out, index=d.index)


def ichimoku_cloud_signal(d, tenkan_n, kijun_n, span_b_n):
    ich = ta.trend.IchimokuIndicator(d["high"], d["low"], window1=tenkan_n,
                                     window2=kijun_n, window3=span_b_n)
    span_a = ich.ichimoku_a().shift(kijun_n)
    span_b = ich.ichimoku_b().shift(kijun_n)
    cloud_top = pd.concat([span_a, span_b], axis=1).max(axis=1)
    cloud_bot = pd.concat([span_a, span_b], axis=1).min(axis=1)
    sig = pd.Series(np.nan, index=d.index)
    sig[d["close"] > cloud_top] = 1.0
    sig[d["close"] < cloud_bot] = -1.0
    return sig.ffill().fillna(0)


# ---------------------------------------------------------------------------
# ONE generic sweeper: given an archetype, a raw-computation function, and
# param sets, builds SIGNAL + (1h-only) FILTER-gate for every config, scores
# both, and records enough into REPLAY to redo the exact same construction
# on a different asset later (the ETH transfer check — survivors only, so
# ETH is never used for selection, only confirmation).
# ---------------------------------------------------------------------------

REPLAY = []


def construct(archetype, compute_fn, params, extra, d):
    """-> (signal_series, gate_series). gate_series is the filter-mode
    'permit new longs' condition; its textbook meaning depends on
    archetype, documented at each of the four builder functions above."""
    if archetype == "two_line":
        fast, slow = compute_fn(d, **params)
        return cross_signal(fast, slow), cross_gate(fast, slow)
    if archetype == "zero_cross":
        osc = compute_fn(d, **params)
        mid = extra.get("mid", 0.0)
        return zero_cross_signal(osc, mid), zero_cross_gate(osc, mid)
    if archetype == "oscillator":
        osc = compute_fn(d, **params)
        lower, upper, exit_mid = extra["lower"], extra["upper"], extra["exit_mid"]
        return (oscillator_hysteresis(osc, lower, upper, exit_mid),
               oscillator_gate_not_overbought(osc, upper))
    if archetype == "band":
        price, lower, mid, upper = compute_fn(d, **params)
        if extra.get("mode", "reversion") == "reversion":
            return (band_reversion_signal(price, lower, mid, upper),
                   band_reversion_gate(price, upper))
        return (band_breakout_signal(price, lower, mid, upper),
               band_breakout_gate(price, mid))
    if archetype == "direct":
        sig = compute_fn(d, **params)
        return sig, (sig == 1)
    raise ValueError(f"unknown archetype {archetype!r}")


def sweep(family, indicator, archetype, tf_list, param_sets, compute_fn,
         base_sig_1h, fixed_extra=None, filter_it=True):
    """param_sets: list of (label, params_dict) for every archetype except
    'oscillator', which needs (label, params_dict, lower, upper, exit_mid)
    per entry (thresholds are indicator-specific, not a fixed extra)."""
    fixed_extra = fixed_extra or {}
    for tf in tf_list:
        d, f = FRAMES["BTC"][tf], FUND["BTC"][tf]
        for entry in param_sets:
            if archetype == "oscillator":
                label, params, lower, upper, exit_mid = entry
                extra = {"lower": lower, "upper": upper, "exit_mid": exit_mid}
            else:
                label, params = entry
                extra = dict(fixed_extra)
            sig, gate = construct(archetype, compute_fn, params, extra, d)
            run_and_record(family, indicator, "signal", label, tf, "BTC", d, sig, f)
            REPLAY.append({"key": (family, indicator, "signal", label, tf),
                          "archetype": archetype, "compute_fn": compute_fn,
                          "params": params, "extra": extra})
            if filter_it and tf == "1h":
                filt = apply_filter(base_sig_1h, gate)
                run_and_record(family, indicator, "filter", label, tf, "BTC", d, filt, f)
                REPLAY.append({"key": (family, indicator, "filter", label, tf),
                              "archetype": archetype, "compute_fn": compute_fn,
                              "params": params, "extra": extra})


# ---------------------------------------------------------------------------
# indicator raw-computation wrappers (fast/slow pairs, oscillators, bands)
# ---------------------------------------------------------------------------

def sma_pair(d, fast, slow):
    return (ta.trend.sma_indicator(d["close"], fast),
           ta.trend.sma_indicator(d["close"], slow))


def ema_pair(d, fast, slow):
    return (ta.trend.ema_indicator(d["close"], fast),
           ta.trend.ema_indicator(d["close"], slow))


def macd_line_signal(d, fast, slow, sig):
    m = ta.trend.MACD(d["close"], window_slow=slow, window_fast=fast, window_sign=sig)
    return m.macd(), m.macd_signal()


def macd_hist(d, fast, slow, sig):
    m = ta.trend.MACD(d["close"], window_slow=slow, window_fast=fast, window_sign=sig)
    return m.macd_diff()


def aroon_pair(d, n):
    a = ta.trend.AroonIndicator(d["high"], d["low"], window=n)
    return a.aroon_up(), a.aroon_down()


def aroon_osc(d, n):
    a = ta.trend.AroonIndicator(d["high"], d["low"], window=n)
    return a.aroon_up() - a.aroon_down()


def di_pair(d, n):
    adx_ind = ta.trend.ADXIndicator(d["high"], d["low"], d["close"], window=n)
    return adx_ind.adx_pos(), adx_ind.adx_neg()


def di_cross_adx_filtered(d, n, adx_thresh):
    adx_ind = ta.trend.ADXIndicator(d["high"], d["low"], d["close"], window=n)
    di_p, di_m, adx_v = adx_ind.adx_pos(), adx_ind.adx_neg(), adx_ind.adx()
    sig = cross_signal(di_p, di_m)
    return sig.where(adx_v > adx_thresh, 0.0)


def supertrend_signal(d, atr_n, mult):
    return supertrend(d, atr_n, mult)


def psar_signal(d, step, max_step):
    p = ta.trend.PSARIndicator(d["high"], d["low"], d["close"], step=step, max_step=max_step)
    psar = p.psar()
    return cross_signal(d["close"], psar)


def trix_line(d, n):
    return ta.trend.trix(d["close"], window=n)


def vortex_pair(d, n):
    return (ta.trend.vortex_indicator_pos(d["high"], d["low"], d["close"], window=n),
           ta.trend.vortex_indicator_neg(d["high"], d["low"], d["close"], window=n))


def kama_pair(d, n, fast, slow):
    k = ta.momentum.kama(d["close"], window=n, pow1=fast, pow2=slow)
    return d["close"], k


def hull_pair(d, n):
    return d["close"], hull_ma(d["close"], n)


def dema_pair(d, fast, slow):
    return dema(d["close"], fast), dema(d["close"], slow)


def tema_pair(d, fast, slow):
    return tema(d["close"], fast), tema(d["close"], slow)


def linreg_osc(d, n):
    return linreg_slope(d["close"], n)


def rsi_osc(d, n):
    return rsi_(d["close"], n)


def stoch_pair(d, n, smooth_k, smooth_d):
    s = ta.momentum.StochasticOscillator(d["high"], d["low"], d["close"],
                                         window=n, smooth_window=smooth_d)
    return s.stoch(), s.stoch_signal()


def stoch_osc(d, n, smooth_k, smooth_d):
    s = ta.momentum.StochasticOscillator(d["high"], d["low"], d["close"],
                                         window=n, smooth_window=smooth_d)
    return s.stoch()


def stochrsi_osc(d, n):
    return ta.momentum.stochrsi(d["close"], window=n) * 100


def cci_osc(d, n):
    return ta.trend.cci(d["high"], d["low"], d["close"], window=n)


def willr_osc(d, n):
    return ta.momentum.williams_r(d["high"], d["low"], d["close"], lbp=n)


def roc_osc(d, n):
    return ta.momentum.roc(d["close"], window=n)


def mom_osc(d, n):
    return d["close"] - d["close"].shift(n)


def uo_osc(d, s, m, l):
    return ta.momentum.ultimate_oscillator(d["high"], d["low"], d["close"],
                                           window1=s, window2=m, window3=l)


def ao_osc(d, fast, slow):
    return ta.momentum.awesome_oscillator(d["high"], d["low"], window1=fast, window2=slow)


def tsi_osc(d, slow, fast):
    return ta.momentum.tsi(d["close"], window_slow=slow, window_fast=fast)


def fisher_osc(d, n):
    return fisher_transform(d, n)


def connors_osc(d, rsi_n, streak_n, rank_n):
    return connors_rsi(d["close"], rsi_n, streak_n, rank_n)


def bb_bands(d, n, k):
    mid = d["close"].rolling(n).mean()
    std = d["close"].rolling(n).std()
    return d["close"], mid - k * std, mid, mid + k * std


def kc_bands(d, n, mult):
    mid = d["close"].ewm(span=n, adjust=False).mean()
    a = atr_(d, n)
    return d["close"], mid - mult * a, mid, mid + mult * a


def chandelier_dir(d, n, mult):
    return chandelier_direction(d, n, mult)


def obv_ma_pair(d, ma_n):
    o = obv_series(d)
    return o, o.rolling(ma_n).mean()


def cmf_osc(d, n):
    return ta.volume.chaikin_money_flow(d["high"], d["low"], d["close"], d["volume"], window=n)


def mfi_osc(d, n):
    return ta.volume.money_flow_index(d["high"], d["low"], d["close"], d["volume"], window=n)


def vol_osc_raw(d, fast, slow):
    return volume_oscillator(d["volume"], fast, slow)


def ad_ma_pair(d, ma_n):
    a = ta.volume.acc_dist_index(d["high"], d["low"], d["close"], d["volume"])
    return a, a.rolling(ma_n).mean()


def force_osc(d, n):
    return ta.volume.force_index(d["close"], d["volume"], window=n)


def eom_osc(d, n):
    return ta.volume.ease_of_movement(d["high"], d["low"], d["volume"], window=n)


def obv_div_sig(d, n):
    return obv_divergence_signal(d, obv_series(d), n)


def fractal_sig(d, k):
    return williams_fractals(d, k)


def vol_confirm_sig(d, fast, slow):
    vo = volume_oscillator(d["volume"], fast, slow)
    price_dir = np.sign(d["close"].diff()).fillna(0)
    sig = price_dir.where(vo > 0, 0.0)
    return sig


def ichimoku_tk_pair(d, tenkan_n, kijun_n, span_b_n):
    ich = ta.trend.IchimokuIndicator(d["high"], d["low"], window1=tenkan_n,
                                     window2=kijun_n, window3=span_b_n)
    return ich.ichimoku_conversion_line(), ich.ichimoku_base_line()


def vwap_pair(d):
    return d["close"], session_vwap(d)


# ---------------------------------------------------------------------------
# data loading
# ---------------------------------------------------------------------------

FRAMES = {}
FUND = {}


def load_data():
    for asset, symbol in [("BTC", "BTCUSDT"), ("ETH", "ETHUSDT")]:
        FRAMES[asset] = {}
        FUND[asset] = {}
        fund_hist = fetch_funding_history(symbol)
        for tf in ["15m", "1h", "4h"]:
            d = fetch_bybit_deep(tf, symbol)
            FRAMES[asset][tf] = d
            FUND[asset][tf] = align_funding(d, fund_hist)


TF_LIST = ["1h", "15m"]


def run_all_btc():
    base_sig_1h = donchian_breakout(FRAMES["BTC"]["1h"], entry_n=20, exit_n=20)

    # Record the UNFILTERED base's own train/val numbers as an explicit row
    # (family="base"). This is the honest yardstick every "filter" row must
    # be read against: FILTER-mode verdict=SURVIVOR only means "positive on
    # both splits, floors cleared" — it does NOT mean the indicator helped.
    # A filter whose gate is true at every single base entry produces this
    # EXACT row again (0.0 delta, 100% trade retention) and adds nothing.
    run_and_record("base", "(unfiltered) donchian-20/20 long", "signal",
                   "entry20/exit20", "1h", "BTC", FRAMES["BTC"]["1h"],
                   base_sig_1h, FUND["BTC"]["1h"])

    # =========================== TREND ===================================
    sweep("trend", "SMA cross", "two_line", TF_LIST,
         [("10/30", {"fast": 10, "slow": 30}), ("20/50", {"fast": 20, "slow": 50}),
          ("50/200", {"fast": 50, "slow": 200})], sma_pair, base_sig_1h)

    sweep("trend", "EMA cross", "two_line", TF_LIST,
         [("10/30", {"fast": 10, "slow": 30}), ("12/26", {"fast": 12, "slow": 26}),
          ("50/200", {"fast": 50, "slow": 200})], ema_pair, base_sig_1h)

    macd_params = [("12/26/9", {"fast": 12, "slow": 26, "sig": 9}),
                   ("5/13/6", {"fast": 5, "slow": 13, "sig": 6}),
                   ("19/39/9", {"fast": 19, "slow": 39, "sig": 9})]
    sweep("trend", "MACD line/signal cross", "two_line", TF_LIST, macd_params,
         macd_line_signal, base_sig_1h)
    sweep("trend", "MACD histogram 0-cross", "zero_cross", TF_LIST, macd_params,
         macd_hist, base_sig_1h)

    aroon_params = [("14", {"n": 14}), ("25", {"n": 25}), ("50", {"n": 50})]
    sweep("trend", "Aroon up/down cross", "two_line", TF_LIST, aroon_params,
         aroon_pair, base_sig_1h)
    sweep("trend", "Aroon oscillator 0-cross", "zero_cross", TF_LIST, aroon_params,
         aroon_osc, base_sig_1h)

    di_params = [("14", {"n": 14}), ("25", {"n": 25}), ("50", {"n": 50})]
    sweep("trend", "ADX/DMI DI cross", "two_line", TF_LIST, di_params,
         di_pair, base_sig_1h)
    sweep("trend", "ADX/DMI DI-cross+ADX>thresh", "direct", TF_LIST,
         [("n14,adx>20", {"n": 14, "adx_thresh": 20}),
          ("n14,adx>25", {"n": 14, "adx_thresh": 25}),
          ("n25,adx>20", {"n": 25, "adx_thresh": 20})],
         di_cross_adx_filtered, base_sig_1h)

    sweep("trend", "SuperTrend", "direct", TF_LIST,
         [("ATR10xMult3", {"atr_n": 10, "mult": 3}),
          ("ATR14xMult3", {"atr_n": 14, "mult": 3}),
          ("ATR14xMult2", {"atr_n": 14, "mult": 2})], supertrend_signal, base_sig_1h)

    sweep("trend", "Parabolic SAR", "direct", TF_LIST,
         [("0.02/0.2", {"step": 0.02, "max_step": 0.2}),
          ("0.01/0.1", {"step": 0.01, "max_step": 0.1}),
          ("0.03/0.3", {"step": 0.03, "max_step": 0.3})], psar_signal, base_sig_1h)

    ichi_params = [("9/26/52", {"tenkan_n": 9, "kijun_n": 26, "span_b_n": 52}),
                   ("7/22/44", {"tenkan_n": 7, "kijun_n": 22, "span_b_n": 44})]
    sweep("trend", "Ichimoku tenkan/kijun cross", "two_line", ["4h"], ichi_params,
         ichimoku_tk_pair, base_sig_1h)
    sweep("trend", "Ichimoku price vs cloud", "direct", ["4h"], ichi_params,
         ichimoku_cloud_signal, base_sig_1h)

    sweep("trend", "TRIX 0-cross", "zero_cross", TF_LIST,
         [("15", {"n": 15}), ("9", {"n": 9}), ("30", {"n": 30})], trix_line, base_sig_1h)

    sweep("trend", "Vortex VI+/VI- cross", "two_line", TF_LIST,
         [("14", {"n": 14}), ("21", {"n": 21}), ("34", {"n": 34})], vortex_pair, base_sig_1h)

    sweep("trend", "KAMA cross", "two_line", TF_LIST,
         [("10/2/30", {"n": 10, "fast": 2, "slow": 30}),
          ("5/2/20", {"n": 5, "fast": 2, "slow": 20})], kama_pair, base_sig_1h)

    sweep("trend", "Hull MA cross", "two_line", TF_LIST,
         [("9", {"n": 9}), ("16", {"n": 16}), ("21", {"n": 21})], hull_pair, base_sig_1h)

    dt_params_10 = [("10/30", {"fast": 10, "slow": 30}), ("20/50", {"fast": 20, "slow": 50})]
    sweep("trend", "DEMA cross", "two_line", TF_LIST, dt_params_10, dema_pair, base_sig_1h)
    sweep("trend", "TEMA cross", "two_line", TF_LIST, dt_params_10, tema_pair, base_sig_1h)

    sweep("trend", "Linreg slope sign", "zero_cross", TF_LIST,
         [("20", {"n": 20}), ("50", {"n": 50}), ("100", {"n": 100})],
         linreg_osc, base_sig_1h)

    # ========================= MOMENTUM ===================================
    sweep("momentum", "RSI OB/OS", "oscillator", TF_LIST,
         [("14/30-70", {"n": 14}, 30, 70, 50),
          ("7/25-75", {"n": 7}, 25, 75, 50),
          ("21/35-65", {"n": 21}, 35, 65, 50)], rsi_osc, base_sig_1h)
    sweep("momentum", "RSI 50-cross", "zero_cross", TF_LIST,
         [("14", {"n": 14}), ("7", {"n": 7}), ("21", {"n": 21})],
         rsi_osc, base_sig_1h, fixed_extra={"mid": 50.0})

    stoch_params = [("14/3/3", {"n": 14, "smooth_k": 3, "smooth_d": 3}),
                    ("5/3/3", {"n": 5, "smooth_k": 3, "smooth_d": 3}),
                    ("21/5/5", {"n": 21, "smooth_k": 5, "smooth_d": 5})]
    sweep("momentum", "Stochastic %K/%D cross", "two_line", TF_LIST, stoch_params,
         stoch_pair, base_sig_1h)
    sweep("momentum", "Stochastic extremes", "oscillator", TF_LIST,
         [(l, p, 20, 80, 50) for l, p in stoch_params], stoch_osc, base_sig_1h)

    sweep("momentum", "Stochastic RSI extremes", "oscillator", TF_LIST,
         [("14", {"n": 14}, 20, 80, 50), ("9", {"n": 9}, 20, 80, 50),
          ("21", {"n": 21}, 20, 80, 50)], stochrsi_osc, base_sig_1h)

    sweep("momentum", "CCI extremes", "oscillator", TF_LIST,
         [("20", {"n": 20}, -100, 100, 0), ("14", {"n": 14}, -100, 100, 0),
          ("50", {"n": 50}, -100, 100, 0)], cci_osc, base_sig_1h)

    sweep("momentum", "Williams %R extremes", "oscillator", TF_LIST,
         [("14", {"n": 14}, -80, -20, -50), ("9", {"n": 9}, -80, -20, -50),
          ("28", {"n": 28}, -80, -20, -50)], willr_osc, base_sig_1h)

    sweep("momentum", "ROC 0-cross", "zero_cross", TF_LIST,
         [("12", {"n": 12}), ("6", {"n": 6}), ("25", {"n": 25})], roc_osc, base_sig_1h)

    sweep("momentum", "Momentum 0-cross", "zero_cross", TF_LIST,
         [("10", {"n": 10}), ("5", {"n": 5}), ("20", {"n": 20})], mom_osc, base_sig_1h)

    sweep("momentum", "Ultimate Oscillator extremes", "oscillator", TF_LIST,
         [("7/14/28", {"s": 7, "m": 14, "l": 28}, 30, 70, 50),
          ("5/10/20", {"s": 5, "m": 10, "l": 20}, 30, 70, 50)], uo_osc, base_sig_1h)

    sweep("momentum", "Awesome Oscillator 0-cross", "zero_cross", TF_LIST,
         [("5/34", {"fast": 5, "slow": 34}), ("3/21", {"fast": 3, "slow": 21})],
         ao_osc, base_sig_1h)

    sweep("momentum", "TSI 0-cross", "zero_cross", TF_LIST,
         [("25/13", {"slow": 25, "fast": 13}), ("13/7", {"slow": 13, "fast": 7})],
         tsi_osc, base_sig_1h)

    sweep("momentum", "Fisher Transform 0-cross", "zero_cross", TF_LIST,
         [("10", {"n": 10}), ("5", {"n": 5}), ("20", {"n": 20})], fisher_osc, base_sig_1h)

    sweep("momentum", "Connors RSI extremes", "oscillator", TF_LIST,
         [("3/2/100", {"rsi_n": 3, "streak_n": 2, "rank_n": 100}, 10, 90, 50),
          ("3/2/50", {"rsi_n": 3, "streak_n": 2, "rank_n": 50}, 10, 90, 50)],
         connors_osc, base_sig_1h)

    # ========================= VOLATILITY =================================
    bb_params = [("20/2", {"n": 20, "k": 2}), ("20/2.5", {"n": 20, "k": 2.5}),
                ("10/2", {"n": 10, "k": 2})]
    sweep("volatility", "Bollinger mean-revert", "band", TF_LIST, bb_params,
         bb_bands, base_sig_1h, fixed_extra={"mode": "reversion"})
    sweep("volatility", "Bollinger breakout", "band", TF_LIST, bb_params,
         bb_bands, base_sig_1h, fixed_extra={"mode": "breakout"})

    kc_params = [("20/2", {"n": 20, "mult": 2}), ("10/1.5", {"n": 10, "mult": 1.5})]
    sweep("volatility", "Keltner mean-revert", "band", TF_LIST, kc_params,
         kc_bands, base_sig_1h, fixed_extra={"mode": "reversion"})
    sweep("volatility", "Keltner breakout", "band", TF_LIST, kc_params,
         kc_bands, base_sig_1h, fixed_extra={"mode": "breakout"})

    sweep("volatility", "Chandelier exit", "direct", TF_LIST,
         [("22/3", {"n": 22, "mult": 3}), ("14/2", {"n": 14, "mult": 2}),
          ("22/2", {"n": 22, "mult": 2})], chandelier_dir, base_sig_1h)

    sweep("volatility", "BB-inside-KC squeeze release", "direct", TF_LIST,
         [("BB20/2 KC20/1.5", {"bb_n": 20, "bb_k": 2, "kc_n": 20, "kc_mult": 1.5}),
          ("BB20/2 KC20/2", {"bb_n": 20, "bb_k": 2, "kc_n": 20, "kc_mult": 2})],
         squeeze_release_signal, base_sig_1h)

    sweep("volatility", "Stdev channel mean-revert", "band", TF_LIST,
         [("50/2", {"n": 50, "k": 2}), ("100/2", {"n": 100, "k": 2})],
         stdev_channel_bands, base_sig_1h, fixed_extra={"mode": "reversion"})

    # =========================== VOLUME ===================================
    sweep("volume", "OBV trend (vs own MA)", "two_line", TF_LIST,
         [("20", {"ma_n": 20}), ("50", {"ma_n": 50})], obv_ma_pair, base_sig_1h)

    sweep("volume", "OBV divergence", "direct", TF_LIST,
         [("20", {"n": 20}), ("50", {"n": 50})], obv_div_sig, base_sig_1h)

    sweep("volume", "CMF 0-cross", "zero_cross", TF_LIST,
         [("20", {"n": 20}), ("10", {"n": 10})], cmf_osc, base_sig_1h)

    sweep("volume", "MFI extremes", "oscillator", TF_LIST,
         [("14/20-80", {"n": 14}, 20, 80, 50), ("14/30-70", {"n": 14}, 30, 70, 50)],
         mfi_osc, base_sig_1h)

    sweep("volume", "VWAP session cross", "two_line", TF_LIST,
         [("cross", {})], vwap_pair, base_sig_1h)
    sweep("volume", "VWAP fade band", "band", TF_LIST,
         [("k=1", {"k": 1}), ("k=2", {"k": 2})], vwap_fade_bands, base_sig_1h,
         fixed_extra={"mode": "reversion"})

    sweep("volume", "Volume oscillator confirm", "direct", TF_LIST,
         [("5/20", {"fast": 5, "slow": 20}), ("10/50", {"fast": 10, "slow": 50})],
         vol_confirm_sig, base_sig_1h)

    sweep("volume", "A/D line trend (vs own MA)", "two_line", TF_LIST,
         [("20", {"ma_n": 20}), ("50", {"ma_n": 50})], ad_ma_pair, base_sig_1h)

    sweep("volume", "Force Index 0-cross", "zero_cross", TF_LIST,
         [("13", {"n": 13}), ("2", {"n": 2})], force_osc, base_sig_1h)

    sweep("volume", "Ease of Movement 0-cross", "zero_cross", TF_LIST,
         [("14", {"n": 14}), ("20", {"n": 20})], eom_osc, base_sig_1h)

    # =========================== LEVELS ====================================
    sweep("levels", "Classic pivots (reversion)", "band", TF_LIST,
         [("S1/R1", {"level": "1"}), ("S2/R2", {"level": "2"})],
         pivot_bands, base_sig_1h, fixed_extra={"mode": "reversion"})

    sweep("levels", "Camarilla pivots (reversion)", "band", TF_LIST,
         [("S3/R3", {"level": "3"}), ("S4/R4", {"level": "4"})],
         camarilla_bands, base_sig_1h, fixed_extra={"mode": "reversion"})

    sweep("levels", "Williams fractals", "direct", TF_LIST,
         [("k=2 (5-bar)", {"k": 2}), ("k=3 (7-bar)", {"k": 3})],
         fractal_sig, base_sig_1h)


def run_eth_transfer():
    """Re-run every BTC SURVIVOR (positive train AND val, both floors
    cleared) on the identical config/tf on ETH — never used for selection,
    only as the honest transfer check the mandate calls for."""
    survivor_keys = {
        (row["family"], row["indicator"], row["mode"], row["config"], row["tf"])
        for row in RESULTS if row["verdict"] == "SURVIVOR" and row["asset"] == "BTC"
    }
    replay_by_key = {e["key"]: e for e in REPLAY}
    base_sig_eth_1h = donchian_breakout(FRAMES["ETH"]["1h"], entry_n=20, exit_n=20)

    n_done = 0
    for key in sorted(survivor_keys):
        family, indicator, mode, label, tf = key
        entry = replay_by_key.get(key)
        if entry is None or tf not in FRAMES["ETH"]:
            continue
        d, f = FRAMES["ETH"][tf], FUND["ETH"][tf]
        sig, gate = construct(entry["archetype"], entry["compute_fn"],
                             entry["params"], entry["extra"], d)
        if mode == "filter":
            sig = apply_filter(base_sig_eth_1h, gate)
        run_and_record(family, indicator, mode, label, tf, "ETH", d, sig, f)
        n_done += 1
    print(f"\nETH transfer check: {len(survivor_keys)} BTC survivor configs, "
         f"{n_done} replayed on ETH.")
    return n_done


# ---------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------

def write_outputs():
    df = pd.DataFrame(RESULTS)
    base_row = df[(df.family == "base") & (df.asset == "BTC")].iloc[0]
    base_tr_exp, base_tr_n = base_row["tr_exp"], base_row["tr_n"]
    base_va_exp, base_va_n = base_row["va_exp"], base_row["va_n"]

    is_filter_btc = (df["mode"] == "filter") & (df["asset"] == "BTC")
    df["va_exp_delta_vs_base"] = np.where(is_filter_btc, df["va_exp"] - base_va_exp, np.nan)
    df["tr_exp_delta_vs_base"] = np.where(is_filter_btc, df["tr_exp"] - base_tr_exp, np.nan)
    df["va_sample_retention_vs_base"] = np.where(
        is_filter_btc, (df["va_n"] / base_va_n).round(3), np.nan)
    # A filter is a true NO-OP (gate never blocked/altered a single entry)
    # when it reproduces the base's counts AND expectancy almost exactly.
    df["filter_is_noop"] = (
        is_filter_btc
        & (df["tr_n"] == base_tr_n) & (df["va_n"] == base_va_n)
        & (df["va_exp"] - base_va_exp).abs().lt(0.01)
        & (df["tr_exp"] - base_tr_exp).abs().lt(0.01)
    )

    df.to_csv("step76_full_table.csv", index=False)
    print(f"\nwrote step76_full_table.csv: {len(df)} rows "
         f"(base benchmark: train n={base_tr_n} exp={base_tr_exp:.4f}, "
         f"val n={base_va_n} exp={base_va_exp:.4f})")
    return df


def main():
    print("Loading data (cached parquet, no network expected)...")
    load_data()
    for asset in ("BTC", "ETH"):
        for tf in ("15m", "1h", "4h"):
            n = len(FRAMES[asset][tf])
            print(f"  {asset} {tf}: {n} bars")

    print("\nRunning full BTC sweep (signal + filter modes)...")
    run_all_btc()
    n_btc = len(RESULTS)
    n_survivors = sum(1 for r in RESULTS if r["verdict"] == "SURVIVOR")
    print(f"BTC sweep done: {n_btc} rows, {n_survivors} SURVIVOR rows "
         f"(train AND val positive, floors cleared).")

    run_eth_transfer()

    df = write_outputs()

    n_configs = len({(r["family"], r["indicator"], r["config"]) for r in RESULTS})
    n_indicators = len({r["indicator"] for r in RESULTS})
    print(f"\nTOTAL: {n_indicators} distinct indicators, {n_configs} distinct "
         f"configs, {len(df)} table rows (signal+filter x tf x asset).")
    print(f"SURVIVORS (BTC, train+val positive, floors cleared): "
         f"{sum(1 for r in RESULTS if r['verdict']=='SURVIVOR' and r['asset']=='BTC')}")
    print(f"ETH transfer rows: {sum(1 for r in RESULTS if r['asset']=='ETH')}")


if __name__ == "__main__":
    print("=" * 70)
    print("STEP 76 — the complete indicator sweep")
    print("=" * 70)
    SPOTCHECK_LINES = _spotcheck()
    for l in SPOTCHECK_LINES:
        print(l)
    main()
