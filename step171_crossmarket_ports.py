"""
step171_crossmarket_ports.py — ETH-trader, round 171: port GOLD's donchian
breakout and SPX's RSI2<5 dip-buy shapes to ETH, daily bars.

Run:  python3 step171_crossmarket_ports.py

WHY THESE TWO: per Morgan's expanded mandate, after the five-edge BTC
transfer test (step170, 0/5 survived) the next check is whether OTHER
markets' native edges generalize any better than BTC's did — gold's one
validated family (donchian20 + EMA20 exit, sealed-PASSED 4x across GLD/
GC=F) and the S&P's dip-buy folklore (RSI2<5 above SMA200, exit close>SMA5
or RSI2>65, no fixed target, TWO sealed passes on SPY/ES=F) are this
program's other two validated families outside BTC. Both are UNIT-FREE
by construction — a Donchian breakout is "close above its own N-bar high",
an RSI threshold is 0-100 regardless of instrument, an SMA-relative
position is scale-invariant — so, unlike vol_gated_ma's literal ATR%
floor (which needed re-deriving in step170 edge 3), these two ports do
NOT need their numeric thresholds re-derived from ETH's own distribution
to be a fair "unchanged config" replay. That is stated as a finding in
itself, not assumed silently.

DATA: ETH-USDT daily bars, bybit cache (data_bybit_ETHUSDT_1d_full.
parquet), 2021-03-15 -> 2026-07-23, 1957 bars (~5.4y — comparable span to
gold/SPX's own daily history used in step55/step60, though those ran on
decades of TradFi history this program doesn't have for crypto).

COSTS: execution="taker" (18bps round-trip worst case), real funding via
align_funding (backtest.py applies funding_events_per_bar = bar_hours/8,
so a daily bar correctly accrues ~3 funding settlements — no special
handling needed).
"""

import numpy as np
import pandas as pd

import step170_eth_lib as lib
from step170_eth_lib import (
    EXECUTION, MIN_TRAIN_TRADES, MIN_VAL_TRADES, TAKER_RT_BPS,
    chance_baseline, hold_stats, mk_row, score, score_sealed, split_points,
    thickness, verdict_for,
)
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from strategy import rsi

pd.set_option("display.width", 220)

ALL_ROWS = []


def log_row(row):
    ALL_ROWS.append(row)


def event_long(d, enter, exit_, max_hold=0):
    """Generic flat->long->flat state machine with a CONDITIONAL exit
    (not a fixed max_hold like day_trade_signal) — reused verbatim from
    step48_tradfi_trend.py's own event_long (copied, not imported, to
    keep this file dependency-light; identical logic)."""
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


def donchian_ema_exit(d, entry_n, ema_n=20):
    """Gold's exact winning shape (step48_tradfi_trend.donchian_ema_exit,
    reproduced verbatim): break above the N-bar high, ride until close
    crosses back under the EMA. No fixed stop, no fixed target — the
    trend-following exit IS the risk management, exactly as gold trades
    it live."""
    hi = d["high"].rolling(entry_n).max().shift(1)
    enter = d["close"] > hi
    ema = d["close"].ewm(span=ema_n, adjust=False).mean()
    exit_ = d["close"] < ema
    # hysteresis: enter only on fresh breakout, stay until exit fires
    sig = pd.Series(np.nan, index=d.index)
    sig[exit_.fillna(False)] = 0.0
    sig[enter.fillna(False)] = 1.0
    return sig.ffill().fillna(0)


def dipbuy_exit(d):
    """SPX's exact shared exit (step60_spx_system.dipbuy_exit, reproduced
    verbatim): close back above SMA5 OR RSI(2)>65."""
    sma5 = d["close"].rolling(5).mean()
    return (d["close"] > sma5) | (rsi(d["close"], 2) > 65)


def main():
    print("Loading ETH-USDT daily data (bybit cache)...")
    d = fetch_bybit_deep("1d", "ETHUSDT")
    funding_hist = fetch_funding_history("ETHUSDT")
    f = align_funding(d, funding_hist)
    n, i_tr, i_va = split_points(d)
    print(f"  1d: {n} bars, {d['timestamp'].iloc[0]:%Y-%m-%d} -> {d['timestamp'].iloc[-1]:%Y-%m-%d} "
          f"| train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed)")
    print(f"  Note: unlike step170's ATR%-floor edges, both families below are UNIT-FREE "
          f"(breakout-vs-own-N-bar-high, RSI 0-100, SMA-relative) — no re-derivation of the "
          f"numeric thresholds is needed for a fair unchanged-config replay; stated as a finding, "
          f"not assumed.")

    # =======================================================================
    # FAMILY A — gold's donchian20/55 + EMA20 exit, unchanged config
    # =======================================================================
    print("\n" + "=" * 78)
    print("FAMILY A — donchian breakout + EMA20 exit (GOLD's validated shape, unchanged)")
    print("=" * 78)
    for N in (20, 55):
        sig = donchian_ema_exit(d, N, ema_n=20)
        tr, va = score(d, sig, f, i_tr, i_va)  # no stop/target, exactly as gold trades it
        v = verdict_for(tr, va)
        n_tr_events = int((sig.iloc[:i_tr].diff().fillna(sig.iloc[:i_tr]) > 0).sum())
        print(f"  N={N}: train n={len(tr.trades)} exp=${tr.expectancy:+.2f} win={tr.win_rate*100:.1f}% "
              f"ret={tr.total_return_pct:+.2f}% | val n={len(va.trades)} exp=${va.expectancy:+.2f} "
              f"win={va.win_rate*100:.1f}% ret={va.total_return_pct:+.2f}% -> {v}")
        log_row(mk_row("A-gold-donchian-port", f"donchian{N}+EMA20exit (UNCHANGED CONFIG)", "1d",
                        tr, va, None, None, None,
                        extra={"edge": "A-gold-donchian-port", "transfer_type": "unchanged-config",
                               "source_number": "GLD/GC=F sealed-PASS 4x, ~5.4 trades/yr at d20"}))
        if v == "SURVIVOR":
            te = score_sealed(d, sig, f, i_va, n)
            mean_ret, mult = thickness(te, te)
            te_verdict = "SURVIVOR" if te.expectancy > 0 and len(te.trades) >= MIN_VAL_TRADES else "FAIL-ON-TEST"
            print(f"    -> SEALED TEST: n={len(te.trades)} exp=${te.expectancy:+.2f} win={te.win_rate*100:.1f}% "
                  f"ret={te.total_return_pct:+.2f}% thickness={mult:.2f}x taker-cost -> {te_verdict}")
            log_row(mk_row("A-gold-donchian-port", f"donchian{N}+EMA20exit (UNCHANGED CONFIG, sealed)", "1d",
                            tr, va, None, None, None,
                            extra={"edge": "A-gold-donchian-port", "transfer_type": "unchanged-config-sealed",
                               "eth_test_exp": te.expectancy, "eth_test_n": len(te.trades),
                               "transfer_verdict": te_verdict}))

    # =======================================================================
    # FAMILY B — SPX's RSI2<5 dip-buy above SMA200, unchanged config
    # =======================================================================
    print("\n" + "=" * 78)
    print("FAMILY B — RSI(2)<5 dip-buy above SMA200 (SPX's validated shape, unchanged)")
    print("=" * 78)
    sma200 = d["close"].rolling(200).mean()
    r2 = rsi(d["close"], 2)
    exit_cond = dipbuy_exit(d).fillna(False)
    frac_above_sma200 = float((d["close"] > sma200).mean() * 100)
    frac_rsi2lt5 = float((r2 < 5).mean() * 100)
    print(f"  context: ETH spends {frac_above_sma200:.1f}% of days above its own SMA200 "
          f"(a long-biased trend market spends most days above; a chop/bear-heavy one doesn't — "
          f"this alone is diagnostic of whether the folklore's PRECONDITION even holds on ETH)")
    print(f"  RSI(2)<5 fires on {frac_rsi2lt5:.1f}% of all days (any regime)")

    for th in (5, 10, 15):   # SPX's own swept thresholds; 5 is the sealed winner
        enter = ((r2 < th) & (d["close"] > sma200)).fillna(False)
        sig = event_long(d, enter, exit_cond, max_hold=0)   # no hold cap, exactly as SPX's sealed winner
        tr, va = score(d, sig, f, i_tr, i_va)   # NO fixed target, NO stop — literal spec
        v = verdict_for(tr, va)
        n_events = int(enter.iloc[:i_va].sum())
        print(f"  RSI2<{th}: n_events(tr+va)={n_events} | train n={len(tr.trades)} exp=${tr.expectancy:+.2f} "
              f"win={tr.win_rate*100:.1f}% | val n={len(va.trades)} exp=${va.expectancy:+.2f} "
              f"win={va.win_rate*100:.1f}% -> {v}")
        log_row(mk_row("B-spx-rsi2-dipbuy", f"RSI2<{th} above SMA200, exit SMA5/RSI65 (UNCHANGED CONFIG)", "1d",
                        tr, va, None, None, None,
                        extra={"edge": "B-spx-rsi2-dipbuy", "transfer_type": "unchanged-config",
                               "source_number": "SPY sealed +$75.36/t x33 / ES=F sealed +$124.07/t x29"}))
        if v == "SURVIVOR":
            te = score_sealed(d, sig, f, i_va, n)
            mean_ret, mult = thickness(te, te)
            te_verdict = "SURVIVOR" if te.expectancy > 0 and len(te.trades) >= MIN_VAL_TRADES else "FAIL-ON-TEST"
            print(f"    -> SEALED TEST: n={len(te.trades)} exp=${te.expectancy:+.2f} win={te.win_rate*100:.1f}% "
                  f"ret={te.total_return_pct:+.2f}% thickness={mult:.2f}x taker-cost -> {te_verdict}")
            log_row(mk_row("B-spx-rsi2-dipbuy", f"RSI2<{th} above SMA200 (UNCHANGED CONFIG, sealed)", "1d",
                            tr, va, None, None, None,
                            extra={"edge": "B-spx-rsi2-dipbuy", "transfer_type": "unchanged-config-sealed",
                               "eth_test_exp": te.expectancy, "eth_test_n": len(te.trades),
                               "transfer_verdict": te_verdict}))

    df = pd.DataFrame(ALL_ROWS)
    df.to_csv("step171_table.csv", index=False)
    print(f"\n\n{len(df)} rows written to step171_table.csv")
    print(df[["edge", "config", "tf", "tr_n", "tr_exp", "va_n", "va_exp", "verdict"]]
          .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    return df


if __name__ == "__main__":
    main()
