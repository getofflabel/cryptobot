"""
step134_dead_confirmations.py — ROUND 134. Cheap confirmation tests of
families already proven DEAD on BTC (or on other markets in this program),
per morgan's mandate: "dead on BTC isn't dead everywhere, test each."

ALREADY CONFIRMED DEAD ON SPX ITSELF (stronger evidence than a BTC-dead
transfer check — cited, NOT re-run):
  - always-on shorts: R60 (family 2a shorts, family 2c shorts) + R77
    (family 1a/1b short legs) — shorts lose to their long mirrors in
    EVERY family tested across two full rounds. Re-confirmed AGAIN
    tonight in step130 (gap continuation/reversal shorts, both dead) and
    step132 (divergence shorts, both dead). Six independent confirmations
    is a stronger verdict than one more cheap test would add.
  - BOS/CHoCH/sweep-reclaim/confluence (the SMC toolkit): R77 families
    3a/3b/3c, 0/92 across SPY/ES=F/QQQ. Also cited, not re-run (see
    step132's docstring for the full accounting).

NEW HERE (genuinely untested primitives, distinct from BOS/CHoCH):
  PART A — ORDER BLOCKS: the last down-candle immediately before a strong
    up-impulse (the SMC "the last sellers before the move" idea) — price
    returning to that candle's range is bought. Re-derived directly from
    confirmed_swings + a simple impulse detector (NOT step57's
    order_block_engine, which is wired to that round's crypto multi-
    exchange champion-alignment machinery; the SHAPE is ported, the
    implementation is fresh, per the mandate).
  PART B — CANDLE PATTERNS (bullish/bearish engulfing) at a confirmed
    swing extreme — the classic reversal-candle idea, untested on SPX.

execution="taker". Costs from step130_common.COSTS. No sealed-test look
spent.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import step130_common as C

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", None)


# ===========================================================================
# PART A — order blocks (re-derived, SPX-native)
# ===========================================================================

def order_block_signal(d: pd.DataFrame, impulse_atr_mult: float, touch_bars: int) -> pd.Series:
    """Impulse: a close-to-close move >= impulse_atr_mult x ATR(14) in one
    bar. Bullish order block: the last DOWN candle (close<open)
    immediately before an up-impulse bar. Entry: price later trades back
    down INTO that candle's [low,high] range (a 'touch', within
    touch_bars of the block forming) -> long. Exit: the shared R60
    dipbuy_exit (close>SMA5 or RSI2>65) for a fair apples-to-apples
    comparison against the already-validated dip-buy family."""
    close, open_, high, low = d["close"], d["open"], d["high"], d["low"]
    a = C.atr(d, 14)
    body_ret = close - close.shift(1)
    impulse_up = body_ret >= impulse_atr_mult * a
    is_down_candle = close < open_
    block_forms = is_down_candle.shift(1).fillna(False) & impulse_up
    block_low = low.shift(1).where(block_forms)
    block_high = high.shift(1).where(block_forms)
    block_low_ff = block_low.ffill(limit=touch_bars)
    block_high_ff = block_high.ffill(limit=touch_bars)
    touch = (low <= block_high_ff) & (close >= block_low_ff * 0.995)
    # only the FIRST touch after a fresh block counts (avoid re-firing every
    # bar the price sits inside an old, stale block)
    fresh = block_forms.rolling(touch_bars, min_periods=1).apply(lambda x: x.any(), raw=True).astype(bool)
    enter = (touch & fresh).fillna(False)
    return enter


def run_part_a(frames, meta) -> list[dict]:
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = C.COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        med_atr = m["med_atr"]
        exit_cond = C.dipbuy_exit_mask(d).fillna(False)
        for impulse_mult in (1.5, 2.0):
            for touch_bars in (5, 10):
                enter = order_block_signal(d, impulse_mult, touch_bars)
                for stop_name, stop_mult in (("none", None), ("1.5xATR", 1.5)):
                    stop_pct = None if stop_mult is None else stop_mult * med_atr
                    sig = C.event_long(d, enter, exit_cond, 0)
                    tr, va = C.score(d, sig, costs, i_tr, i_va, stop_pct=stop_pct)
                    cfg = f"impulse{impulse_mult}xATR touch<={touch_bars}b stop={stop_name}"
                    rows.append(C.mk_row("A-order-blocks", cfg, tag, "1d", tr, va, stop_pct))
    return rows


# ===========================================================================
# PART B — candle patterns (engulfing) at a confirmed swing extreme
# ===========================================================================

def engulfing_signals(d: pd.DataFrame, k: int) -> tuple[pd.Series, pd.Series]:
    """Bullish engulfing: today's body fully engulfs yesterday's body,
    today closes up, AND yesterday's low was within `k` bars of a
    confirmed swing low (a real support context, not a random engulf in
    open air). Bearish mirror at a confirmed swing high."""
    close, open_ = d["close"], d["open"]
    bull_engulf = (close > open_) & (open_.shift(1) > close.shift(1)) & \
                  (close >= open_.shift(1)) & (open_ <= close.shift(1))
    bear_engulf = (close < open_) & (open_.shift(1) < close.shift(1)) & \
                  (close <= open_.shift(1)) & (open_ >= close.shift(1))
    sh_price, sl_price = C.confirmed_swings(d, k)
    near_low_ctx = sl_price.ffill(limit=k * 2).notna()
    near_high_ctx = sh_price.ffill(limit=k * 2).notna()
    return (bull_engulf & near_low_ctx).fillna(False), (bear_engulf & near_high_ctx).fillna(False)


def run_part_b(frames, meta) -> list[dict]:
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = C.COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        med_atr = m["med_atr"]
        exit_cond = C.dipbuy_exit_mask(d).fillna(False)
        for k in (5, 8):
            bull, bear = engulfing_signals(d, k)
            for label, enter, direction in (("bullish-engulf@swinglow", bull, "long"),
                                            ("bearish-engulf@swinghigh", bear, "short")):
                for stop_name, stop_mult in (("none", None), ("1.5xATR", 1.5)):
                    stop_pct = None if stop_mult is None else stop_mult * med_atr
                    if direction == "long":
                        sig = C.event_long(d, enter, exit_cond, 0)
                    else:
                        from strategy import event_short
                        sig = event_short(d, enter, exit_cond, 0)
                    tr, va = C.score(d, sig, costs, i_tr, i_va, stop_pct=stop_pct)
                    cfg = f"k={k} {label} stop={stop_name}"
                    rows.append(C.mk_row("B-engulfing", cfg, tag, "1d", tr, va, stop_pct))
    return rows


# ===========================================================================
# main
# ===========================================================================

def main():
    print("=" * 78)
    print("ROUND 134 — CHEAP DEAD-CONFIRMATION TESTS: ORDER BLOCKS, CANDLE PATTERNS")
    print("=" * 78)

    frames = {tag: {} for tag in ("SPY", "ES")}
    meta = {tag: {} for tag in ("SPY", "ES")}
    for tag in ("SPY", "ES"):
        frames[tag]["1d"] = C.load_symbol(tag, "1d")
        meta[tag]["1d"] = C.span_meta(frames[tag]["1d"])

    cols = ["config", "symbol", "tr_n", "tr_exp", "tr_win%", "va_n", "va_exp", "va_win%", "verdict"]

    print("\nPART A — order blocks (re-derived, SPX-native)")
    a_df = pd.DataFrame(run_part_a(frames, meta))
    print(a_df[cols].to_string(index=False, float_format=lambda x: f"{x:,.3f}"))
    print(f"  verdicts: {a_df['verdict'].value_counts().to_dict()}")

    print("\nPART B — bullish/bearish engulfing at a confirmed swing extreme")
    b_df = pd.DataFrame(run_part_b(frames, meta))
    print(b_df[cols].to_string(index=False, float_format=lambda x: f"{x:,.3f}"))
    print(f"  verdicts: {b_df['verdict'].value_counts().to_dict()}")

    a_df.to_csv("step134_table_partA_orderblocks.csv", index=False)
    b_df.to_csv("step134_table_partB_engulfing.csv", index=False)

    print("\nDone. No sealed-test window touched.")
    return a_df, b_df


if __name__ == "__main__":
    main()
