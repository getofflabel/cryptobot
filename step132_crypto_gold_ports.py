"""
step132_crypto_gold_ports.py — ROUND 132. Ports crypto/gold-validated
family SHAPES onto SPX, re-deriving every threshold from SPX's own daily
ATR%/structure (never a ported BTC or gold constant).

IMPORTANT DISCOVERY MADE TONIGHT (see step130_family_map.md preamble):
this is NOT the second SPX round — step48_tradfi_trend.py (gold's "port,
don't reinvent" round) and step77_spx_playbook.py (an earlier, un-cited
SPX breadth round) already exist. Before writing anything below, both
were read in full and cross-checked against morgan's requested port list
so nothing here duplicates settled ground:
  - CHoCH + confluence: ALREADY comprehensively dead on SPX
    (step77 families 3a/3c: 0/72 + 0/8 = 0/80 across k in {5,8}, wick vs
    body structure, SPY/ES=F/QQQ). NOT re-run here — cited, not repeated.
  - Trend + vol-gate: ALREADY validated (step60 family 3, SMA100/200-
    regime + adaptive vol gate, 4/4 SURVIVOR cross-instrument) AND
    step77 family 4c (vol-gated opening-range breakout, 3/3 SURVIVOR).
    NOT re-run here.
  - Donchian breakout (gold's shape): ALREADY validated on SPY AND QQQ
    in step48 family 3 (donchian20/55 + EMA20 exit, 4/4 SURVIVOR) — but
    NEVER tested on ES=F (step48's SYMBOLS list has no S&P futures leg,
    only GC=F/CL=F for gold/oil). PART A below closes exactly that one
    gap: the identical config, unchanged, replayed on ES=F.
  - Hidden RSI divergence / confirmation-gated regular divergence: NOT
    yet tested on SPX anywhere in this program. PART B is genuinely new.
  - RSI3 dip-buy: R60 gridded RSI2 thresholds {5,10,15} but never RSI(3).
    PART C is a cheap, genuinely new variant test.
  - Volume-gated breakout: NOT yet tested (R77's family 4 gates on
    ATR%-percentile "vol", never on raw VOLUME itself). PART D is new.

Costs/split/verdict machinery all from step130_common.py. execution=
"taker". No sealed-test look spent.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import step130_common as C
from step48_tradfi_trend import donchian_ema_exit

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", None)


# ===========================================================================
# PART A — donchian breakout + EMA20 exit, ES=F transfer test (closes the
# one gap in step48's already-validated SPY/QQQ result)
# ===========================================================================

def run_part_a(frames, meta) -> list[dict]:
    rows = []
    for tag in ("SPY", "QQQ", "ES"):    # SPY/QQQ = reproduce step48 exactly; ES = the new leg
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = C.COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        for N in (20, 55):
            sig = donchian_ema_exit(d, N, ema_n=20)
            tr, va = C.score(d, sig, costs, i_tr, i_va)
            rows.append(C.mk_row("A-donchian-ema-transfer", f"donchian{N} EMA20exit", tag, "1d", tr, va))
    return rows


# ===========================================================================
# PART B — hidden RSI divergence + confirmation-gated regular divergence
# (genuinely new territory; shape adapted from step58_divergence_mtf's
# divergence_events(), re-implemented directly here rather than imported
# because step58's version threads a crypto-4h "champ_al" trend gate this
# script substitutes with SPX's own SMA200 trend — the SHAPE is the same,
# the gate's SOURCE is SPX-native, per the mandate: "shape only, constants
# recomputed, state what you replaced.")
# ===========================================================================

def confirmed_swings_price(d: pd.DataFrame, k: int):
    """Same fractal-pivot definition as step41_shorts.confirmed_swings
    (imported as C.confirmed_swings) applied to price highs/lows; kept as
    a thin local wrapper so this file can also swing the RSI series with
    the identical k through the same causal alignment."""
    return C.confirmed_swings(d, k)


def rsi_divergence_events(d: pd.DataFrame, k: int, trend_up: pd.Series):
    """Regular bullish: price LOWER low, RSI HIGHER low -> long (classic
    reversal-warning divergence). Hidden bullish: price HIGHER low, RSI
    LOWER low, gated to an EXISTING uptrend (trend_up at the swing's
    confirm bar) -> long, continuation flavor — this is the 'confirmation-
    gated' half of the mandate (gated by trend_up, i.e. only trusted when
    already confirmed by the daily SMA200 regime). Mirror on the short
    side is tested too (dies everywhere per house long-bias doctrine,
    reported honestly). Adapted from step58_divergence_mtf.divergence_
    events() with champ_al replaced by SPX's own SMA200 trend_up."""
    sh_price, sl_price = confirmed_swings_price(d, k)
    r2 = C.rsi(d["close"], 2)
    n = len(d)
    sl_np, sh_np = sl_price.to_numpy(), sh_price.to_numpy()
    r_np = r2.to_numpy()
    trend_np = trend_up.to_numpy()

    long_reg = np.zeros(n, dtype=bool)
    short_reg = np.zeros(n, dtype=bool)
    long_hid = np.zeros(n, dtype=bool)
    short_hid = np.zeros(n, dtype=bool)

    prev_low = None
    prev_high = None
    for j in range(n):
        if not np.isnan(sl_np[j]):
            origin = j - k
            p, o = sl_np[j], r_np[origin] if 0 <= origin < n else np.nan
            if prev_low is not None and not (np.isnan(o) or np.isnan(prev_low[1])):
                p0, o0 = prev_low
                if p < p0 and o > o0:
                    long_reg[j] = True
                elif p > p0 and o < o0 and (0 <= j < n and trend_np[j]):
                    long_hid[j] = True
            prev_low = (p, o)
        if not np.isnan(sh_np[j]):
            origin = j - k
            p, o = sh_np[j], r_np[origin] if 0 <= origin < n else np.nan
            if prev_high is not None and not (np.isnan(o) or np.isnan(prev_high[1])):
                p0, o0 = prev_high
                if p > p0 and o < o0:
                    short_reg[j] = True
                elif p < p0 and o > o0 and (0 <= j < n and not trend_np[j]):
                    short_hid[j] = True
            prev_high = (p, o)

    idx = d.index
    return (pd.Series(long_reg, index=idx), pd.Series(short_reg, index=idx),
            pd.Series(long_hid, index=idx), pd.Series(short_hid, index=idx))


def run_part_b(frames, meta) -> list[dict]:
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = C.COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        med_atr = m["med_atr"]
        trend_up = (d["close"] > C.sma(d["close"], 200)).fillna(False)
        exit_cond = C.dipbuy_exit_mask(d).fillna(False)
        for k in (5, 8):
            long_reg, short_reg, long_hid, short_hid = rsi_divergence_events(d, k, trend_up)
            for label, enter, direction in (
                ("regular-bullish (reversal-warning)", long_reg, "long"),
                ("hidden-bullish (trend-confirmation-gated)", long_hid, "long"),
                ("regular-bearish (reversal-warning)", short_reg, "short"),
                ("hidden-bearish (trend-confirmation-gated)", short_hid, "short"),
            ):
                if direction == "long":
                    sig = C.event_long(d, enter, exit_cond, C.days_to_bars(d, 40))
                else:
                    from strategy import event_short
                    sig = event_short(d, enter, exit_cond, C.days_to_bars(d, 40))
                stop_pct = min(1.5 * med_atr, 5.0)
                tr, va = C.score(d, sig, costs, i_tr, i_va, stop_pct=stop_pct)
                cfg = f"k={k} {label}"
                rows.append(C.mk_row("B-rsi-divergence", cfg, tag, "1d", tr, va, stop_pct))
    return rows


# ===========================================================================
# PART C — RSI(3) dip-buy (cheap variant, R60 only gridded RSI2)
# ===========================================================================

def run_part_c(frames, meta) -> list[dict]:
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = C.COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        med_atr = m["med_atr"]
        close = d["close"]
        sma200 = C.sma(close, 200)
        exit_cond = C.dipbuy_exit_mask(d).fillna(False)
        r3 = C.rsi(close, 3)
        for th in (5, 10, 15):
            enter = ((r3 < th) & (close > sma200)).fillna(False)
            for stop_name, stop_mult in (("none", None), ("1.5xATR", 1.5)):
                stop_pct = None if stop_mult is None else stop_mult * med_atr
                sig = C.event_long(d, enter, exit_cond, 0)
                tr, va = C.score(d, sig, costs, i_tr, i_va, stop_pct=stop_pct)
                cfg = f"rsi3<{th} stop={stop_name}"
                rows.append(C.mk_row("C-rsi3-dipbuy", cfg, tag, "1d", tr, va, stop_pct))
    return rows


# ===========================================================================
# PART D — volume-gated breakout (donchian20 entry, gated by today's
# volume vs its own N-day average — genuinely new axis, never tested)
# ===========================================================================

def run_part_d(frames, meta) -> list[dict]:
    rows = []
    for tag in ("SPY", "QQQ"):    # volume is not meaningfully comparable on ES=F futures contracts
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = C.COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        hi20 = d["high"].rolling(20).max().shift(1)
        ema20 = d["close"].ewm(span=20, adjust=False).mean()
        vol_avg = d["volume"].rolling(20).mean()
        for vol_mult in (1.0, 1.5, 2.0):
            enter = ((d["close"] > hi20) & (d["volume"] > vol_mult * vol_avg)).fillna(False)
            exit_ = (d["close"] < ema20).fillna(False)
            sig = C.event_long(d, enter, exit_, 0)
            tr, va = C.score(d, sig, costs, i_tr, i_va)
            cfg = f"donchian20+vol>{vol_mult}x20davg EMA20exit"
            rows.append(C.mk_row("D-volgate-breakout", cfg, tag, "1d", tr, va))
        # baseline: donchian20 alone, no volume gate, for direct comparison
        enter_base = (d["close"] > hi20).fillna(False)
        sig_base = C.event_long(d, enter_base, (d["close"] < ema20).fillna(False), 0)
        tr, va = C.score(d, sig_base, costs, i_tr, i_va)
        rows.append(C.mk_row("D-volgate-breakout", "donchian20 EMA20exit (no vol gate, baseline)", tag, "1d", tr, va))
    return rows


# ===========================================================================
# main
# ===========================================================================

def main():
    print("=" * 78)
    print("ROUND 132 — CRYPTO/GOLD FAMILY-SHAPE PORTS ON SPX")
    print("=" * 78)

    frames = {tag: {} for tag in ("SPY", "ES", "QQQ")}
    meta = {tag: {} for tag in ("SPY", "ES", "QQQ")}
    for tag in ("SPY", "ES", "QQQ"):
        frames[tag]["1d"] = C.load_symbol(tag, "1d")
        meta[tag]["1d"] = C.span_meta(frames[tag]["1d"])

    cols = ["family", "config", "symbol", "tr_n", "tr_exp", "tr_win%", "va_n", "va_exp", "va_win%", "verdict"]

    print("\nPART A — donchian breakout + EMA20 exit, ES=F transfer (SPY/QQQ reproduce step48)")
    a_df = pd.DataFrame(run_part_a(frames, meta))
    print(a_df[cols].to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\nPART B — RSI hidden/regular divergence, confirmation-gated by SMA200 trend")
    b_df = pd.DataFrame(run_part_b(frames, meta))
    print(b_df[cols].to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\nPART C — RSI(3) dip-buy (cheap variant of R60's RSI2 grid)")
    c_df = pd.DataFrame(run_part_c(frames, meta))
    print(c_df[cols].to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\nPART D — volume-gated donchian20 breakout")
    d_df = pd.DataFrame(run_part_d(frames, meta))
    print(d_df[cols].to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    a_df.to_csv("step132_table_partA_donchian_transfer.csv", index=False)
    b_df.to_csv("step132_table_partB_divergence.csv", index=False)
    c_df.to_csv("step132_table_partC_rsi3.csv", index=False)
    d_df.to_csv("step132_table_partD_volgate.csv", index=False)

    print("\nDone. No sealed-test window touched.")
    return a_df, b_df, c_df, d_df


if __name__ == "__main__":
    main()
