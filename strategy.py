"""
strategy.py — trading signals live here, and ONLY signals.

A strategy in this project is deliberately a tiny thing: a function that
takes candles and returns one number per bar:

    +1  "I want to be long after this bar closes"
     0  "I want to be flat"
    -1  "I want to be short"

It does NOT know about money, fees, position sizes, or orders. The backtest
engine (and later the live trader) owns all of that. This split is what lets
the exact same strategy code run in a backtest, an out-of-sample test, and
live paper trading without modification — if the strategy had its own idea
of money, those three would drift apart and the comparison would be garbage.

THE MOVING-AVERAGE CROSSOVER, PLAINLY

A simple moving average (SMA) over N bars is just the mean of the last N
closes — a smoothed, delayed version of price. A short (fast) average hugs
price; a long (slow) average drifts behind it.

    fast SMA above slow SMA  -> price has been rising lately -> be long
    fast SMA below slow SMA  -> price has been falling lately -> be flat
                                (or short, if allow_short=True)

That's the whole idea. It is a TREND-FOLLOWING strategy: it will never buy
the bottom or sell the top, it waits for a move to be underway and rides it.
Its known personality, worth predicting before you look at any results:
  - in long trends it does well
  - in sideways chop it gets "whipsawed": crossovers fire back and forth,
    each one a losing round trip that also pays the 18 bps cost hurdle
We picked it not because it prints money but because it is transparent:
when it wins or loses, you can see exactly why on a chart.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def ma_crossover(candles: pd.DataFrame, fast: int = 20, slow: int = 100,
                 allow_short: bool = False) -> pd.Series:
    """Signal: long when SMA(fast) > SMA(slow).

    fast, slow : lookback lengths in bars. fast must be < slow.
    allow_short: if True, be short when fast < slow instead of flat.

    Warmup: the slow SMA needs `slow` bars of history before it exists at
    all. Until then we emit NaN, which the engine treats as flat. No signal
    is ever produced from partial data.
    """
    if fast >= slow:
        raise ValueError(f"fast ({fast}) must be shorter than slow ({slow})")

    # .rolling(n).mean() = the SMA. min_periods defaults to the window size,
    # so the first (n-1) values are NaN automatically — exactly what we want.
    sma_fast = candles["close"].rolling(fast).mean()
    sma_slow = candles["close"].rolling(slow).mean()

    signal = pd.Series(0.0, index=candles.index)
    signal[sma_fast > sma_slow] = 1.0
    signal[sma_fast < sma_slow] = -1.0 if allow_short else 0.0
    signal[sma_slow.isna()] = float("nan")      # warmup: no opinion yet

    return signal


def _hysteresis(enter: pd.Series, exit_: pd.Series,
                short_enter: pd.Series | None = None) -> pd.Series:
    """Build a stateful signal from enter/exit conditions.

    Many strategies are 'enter when X, stay in until Y' — the signal at a
    bar depends on what state you were already in. The vectorized trick:
    mark 1 on enter bars, 0 on exit bars, NaN elsewhere, then forward-fill
    so the last decision persists until the next one.
    """
    sig = pd.Series(float("nan"), index=enter.index)
    sig[exit_] = 0.0
    sig[enter] = 1.0
    if short_enter is not None:
        sig[short_enter] = -1.0
    return sig.ffill().fillna(0)


def donchian_breakout(candles: pd.DataFrame, entry_n: int = 55,
                      exit_n: int = 20) -> pd.Series:
    """Classic turtle-style breakout: long when price makes a new
    entry_n-bar high, out when it makes a new exit_n-bar low. Trend
    following with hysteresis, so it trades far less than an MA cross.
    The .shift(1) keeps the channel strictly in the past — the bar that
    breaks the high must not be part of the high it is breaking."""
    hi = candles["high"].rolling(entry_n).max().shift(1)
    lo = candles["low"].rolling(exit_n).min().shift(1)
    return _hysteresis(candles["close"] > hi, candles["close"] < lo)


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """Wilder's RSI: 0-100 gauge of recent up-moves vs down-moves."""
    delta = close.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / down.replace(0, float("nan"))
    return 100 - 100 / (1 + rs)


def rsi_meanrev(candles: pd.DataFrame, n: int = 14, buy_below: int = 30,
                exit_above: int = 55) -> pd.Series:
    """Mean reversion: buy panic (RSI oversold), exit once it normalizes.
    The philosophical opposite of trend following — it does best in the
    chop that kills MA crossovers, and gets run over by real downtrends."""
    r = rsi(candles["close"], n)
    return _hysteresis(r < buy_below, r > exit_above)


def momentum_roc(candles: pd.DataFrame, n: int = 168) -> pd.Series:
    """Time-series momentum: long if price is above where it was n bars
    ago, flat otherwise. The simplest trend claim there is."""
    sig = (candles["close"] > candles["close"].shift(n)).astype(float)
    sig[candles["close"].shift(n).isna()] = float("nan")
    return sig


def bollinger_meanrev(candles: pd.DataFrame, n: int = 20,
                      k: float = 2.0) -> pd.Series:
    """Buy when price stretches k standard deviations below its n-bar mean,
    exit when it reverts to the mean."""
    m = candles["close"].rolling(n).mean()
    s = candles["close"].rolling(n).std()
    return _hysteresis(candles["close"] < m - k * s, candles["close"] >= m)


def ma_regime(candles: pd.DataFrame, fast: int = 30, slow: int = 50,
              regime: int = 400) -> pd.Series:
    """MA crossover, but only allowed to be long when price is also above
    a long regime average — the classic fix for trend systems bleeding in
    bear markets: just don't take longs when the tide is out."""
    base = ma_crossover(candles, fast, slow)
    above = candles["close"] > candles["close"].rolling(regime).mean()
    out = base.where(above, 0.0)
    out[candles["close"].rolling(regime).mean().isna()] = float("nan")
    return out


def atr(candles: pd.DataFrame, n: int = 14) -> pd.Series:
    """Average True Range: the typical bar-to-bar movement, in price units.
    The standard yardstick for 'how much does this thing move right now'."""
    prev_close = candles["close"].shift(1)
    tr = pd.concat([
        candles["high"] - candles["low"],
        (candles["high"] - prev_close).abs(),
        (candles["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def pullback_trend(candles: pd.DataFrame, fast: int = 20, slow: int = 100,
                   dip_pct: float = 0.0) -> pd.Series:
    """Round-3 entry-quality variant: same trend definition as the champion
    (SMA fast > SMA slow), but instead of being long the whole time, WAIT
    for price to pull back to the fast average before entering. Exit when
    the trend ends. Buys weakness inside strength — a better price and a
    tighter effective stop, at the cost of sometimes missing runaway trends
    that never look back."""
    sma_f = candles["close"].rolling(fast).mean()
    sma_s = candles["close"].rolling(slow).mean()
    trend = sma_f > sma_s
    dipped = candles["close"] <= sma_f * (1 - dip_pct / 100)
    sig = _hysteresis(trend & dipped, ~trend)
    sig[sma_s.isna()] = float("nan")
    return sig


def rsi_dip_trend(candles: pd.DataFrame, fast: int = 20, slow: int = 100,
                  rsi_n: int = 14, dip_below: int = 40) -> pd.Series:
    """Round-3 variant: trend must be up AND RSI must show a short-term
    dip. Enter the dip, hold until the trend ends."""
    sma_f = candles["close"].rolling(fast).mean()
    sma_s = candles["close"].rolling(slow).mean()
    trend = sma_f > sma_s
    r = rsi(candles["close"], rsi_n)
    sig = _hysteresis(trend & (r < dip_below), ~trend)
    sig[sma_s.isna()] = float("nan")
    return sig


def vol_filtered_ma(candles: pd.DataFrame, fast: int = 20, slow: int = 100,
                    atr_n: int = 14, min_atr_pct: float = 1.0) -> pd.Series:
    """Round-3 variant: the champion, but only allowed to ENTER when the
    market is actually moving (ATR above min_atr_pct of price). Dead,
    compressed markets produce the whipsaws that bleed trend systems."""
    base = ma_crossover(candles, fast, slow)
    lively = (atr(candles, atr_n) / candles["close"] * 100) >= min_atr_pct
    # entries need liveliness; an already-open position may ride vol down
    sig = _hysteresis((base == 1) & lively, base != 1)
    sig[candles["close"].rolling(slow).mean().isna()] = float("nan")
    return sig


def vol_gated_ma(candles: pd.DataFrame, fast: int = 20, slow: int = 100,
                 atr_n: int = 14, min_atr_pct: float = 1.5,
                 allow_short: bool = False,
                 entry_filter: pd.Series | None = None) -> pd.Series:
    """Round-4 generalization of the champion: the vol-gated MA cross, with
    an optional SHORT side. On perpetual futures a short costs the same as
    a long, and 2022-style bear years are where a long-only trend system
    sits flat earning nothing.

    Rules, stated as a state machine (written as an explicit loop so the
    logic is readable rather than clever):
      flat  -> enter long/short when the trend points that way AND the
               market is lively (ATR >= min_atr_pct of price)
      held  -> exit when the trend flips; if it flips while lively, reverse
               straight into the other side, else go flat
    """
    base = ma_crossover(candles, fast, slow, allow_short=True)   # +1/-1
    lively = ((atr(candles, atr_n) / candles["close"] * 100)
              >= min_atr_pct).to_numpy()
    warm = base.notna().to_numpy()
    base_v = base.fillna(0).to_numpy()

    # optional extra ENTRY condition (e.g. "funding not euphoric"). Like the
    # vol gate it only guards the door — an open position is managed by the
    # trend alone.
    if entry_filter is None:
        extra = np.ones(len(candles), dtype=bool)
    else:
        extra = entry_filter.fillna(True).to_numpy(dtype=bool)

    out, pos = [], 0.0
    for b, lv, w, ok in zip(base_v, lively, warm, extra):
        if not w:
            out.append(float("nan"))
            continue
        target = b if allow_short else max(b, 0.0)
        if pos == 0.0:
            if target != 0.0 and lv and ok:
                pos = target
        elif target != pos:
            pos = target if (target != 0.0 and lv and ok) else 0.0
        out.append(pos)
    return pd.Series(out, index=candles.index)


def event_short(candles: pd.DataFrame, enter: pd.Series, exit_: pd.Series,
                max_hold: int = 0) -> pd.Series:
    """Short-only state machine for round 7.

    Shorts on BTC die of slowness: downmoves are violent and the snap-back
    (squeeze) arrives fast, so a short needs its own fast exits, not a
    mirrored trend rule. This machine supports:
      enter     boolean series — open a short on this bar
      exit_     boolean series — cover on this bar
      max_hold  hard time stop in bars (0 = none): cover after this many
                bars NO MATTER WHAT. Squeezes don't negotiate.
    Returns a 0/-1 signal series.
    """
    e = enter.fillna(False).to_numpy(dtype=bool)
    x = exit_.fillna(False).to_numpy(dtype=bool)
    out, pos, held = [], 0.0, 0
    for i in range(len(candles)):
        if pos == 0.0:
            if e[i]:
                pos, held = -1.0, 0
        else:
            held += 1
            if x[i] or (max_hold and held >= max_hold):
                pos = 0.0
        out.append(pos)
    return pd.Series(out, index=candles.index)


def resample_4h(candles: pd.DataFrame) -> pd.DataFrame:
    """Aggregate 1h bars into 4h bars. Fewer bars = fewer trades = less
    paid to the 18 bps hurdle. Often the cheapest 'edge' there is."""
    g = candles.set_index("timestamp").resample("4h")
    out = pd.DataFrame({
        "open": g["open"].first(), "high": g["high"].max(),
        "low": g["low"].min(), "close": g["close"].last(),
        "volume": g["volume"].sum(),
    }).dropna().reset_index()
    return out


def buy_and_hold(candles: pd.DataFrame) -> pd.Series:
    """The baseline every strategy must be measured against: buy on the
    first bar, hold to the end, pay costs once each way plus funding.

    If a strategy cannot beat this after costs, all its trading achieved
    was paying fees for a worse result than doing nothing.
    """
    return pd.Series(1.0, index=candles.index)
