"""
step20_round15.py — round 15: the 10x campaign, opening salvo.

Run:  python3 step20_round15.py

MISSION (standing, Wallace's directive): find a strategy that WORKS at 10x.
That requires stops <= ~2% (10x liquidation sits ~9.5% away) and positive
after-cost expectancy through the full gauntlet. Rounds 12-14 got fast
families from clearly-negative to within ~$1/trade of breakeven as the
data improved. This round attacks from three new angles:

  A. MTF CONFLUENCE — the only edge that has ever survived here is the 4h
     champion's trend state. Use it as a FILTER: only take tight-stop 1h
     dip entries while the 4h machine says "this is a real, live uptrend".
     Proven edge for direction, tight timing for the stop geometry.
     (No lookahead: a 4h bar's state only applies to 1h bars AFTER that
     4h bar has fully closed.)
  B. SESSION FILTER — two PRE-SPECIFIED liquidity windows (US hours,
     Asia hours) applied to round-14's near-miss capitulation entries.
     Pre-specified to avoid bucket-mining.
  C. COMPRESSION BREAKOUT — volatility squeezes (tight Bollinger width)
     resolve violently; enter the break with a 1% stop, 1:4R.

Full discipline: 6 years, 60/20/20, intra-bar stops+targets, real
funding, maker entries where limit-natural (dips), taker where chasing
(breakouts). Survivors face the 10x frontier — the mission metric.
"""

import numpy as np
import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step17_round12 import hi_n, machine
from strategy import atr, rsi, vol_gated_ma


def champion_state_on_1h(d1, d4, f4):
    """The 4h champion's long/flat state, mapped onto 1h bars WITHOUT
    lookahead: each 4h bar's signal takes effect only after that bar
    closes (start time + 4h)."""
    sig4 = vol_gated_ma(d4, fast=20, slow=100, min_atr_pct=1.5,
                        entry_filter=(f4 <= 1.0)).fillna(0)
    eff = pd.DataFrame({
        "effective": d4["timestamp"] + pd.Timedelta(hours=4),
        "champ": sig4.values,
    })
    merged = pd.merge_asof(d1[["timestamp"]], eff,
                           left_on="timestamp", right_on="effective",
                           direction="backward")
    return merged["champ"].fillna(0)


def score(df, sig, f_bps, stop, target, execution):
    n = len(df)
    i_tr, i_va = int(n * 0.6), int(n * 0.8)

    def run(lo, hi):
        return run_backtest(df.iloc[lo:hi].reset_index(drop=True),
                            sig.iloc[lo:hi].reset_index(drop=True),
                            execution=execution, stop_pct=stop,
                            target_pct=target,
                            funding_series=f_bps.iloc[lo:hi].reset_index(drop=True))
    return run(0, i_tr), run(i_tr, i_va), run(i_va, n)


def main():
    d1 = fetch_bybit_deep("1h", "BTCUSDT")
    d4 = fetch_bybit_deep("4h", "BTCUSDT")
    funding = fetch_funding_history("BTCUSDT")
    f1 = align_funding(d1, funding)
    f4 = align_funding(d4, funding)
    oi = pd.read_parquet("data_bybit_BTCUSDT_oi_1h.parquet")
    doi = pd.merge_asof(d1, oi, on="timestamp", direction="backward")
    oi24 = doi["oi"].pct_change(24) * 100
    px24 = d1["close"].pct_change(24) * 100

    champ1h = champion_state_on_1h(d1, d4, f4)
    r3 = rsi(d1["close"], 3)
    sma20 = d1["close"].rolling(20).mean()
    no_exit = pd.Series(False, index=d1.index)

    # Bollinger width percentile for compression
    m = d1["close"].rolling(48).mean()
    s = d1["close"].rolling(48).std()
    width = (4 * s / m) * 100
    squeeze = width < width.rolling(500).quantile(0.2)

    us_hours = d1["timestamp"].dt.hour.isin(range(13, 22))
    asia_hours = d1["timestamp"].dt.hour.isin(range(0, 9))
    capit = (oi24 < -6) & (px24 < -3)

    cands = [
        # A: tight entries inside the proven 4h edge
        ("MTF dip rsi3<15", "maker",
         machine(d1, (champ1h == 1) & (r3 < 15), no_exit, +1, 48), 1.5, 4.5),
        ("MTF pullback sma20", "maker",
         machine(d1, (champ1h == 1) & (d1["close"] < sma20 * 0.995),
                 no_exit, +1, 48), 1.5, 4.5),
        ("MTF breakout 24h", "taker",
         machine(d1, (champ1h == 1) & (d1["close"] > hi_n(d1, 24)),
                 no_exit, +1, 48), 1.0, 4.0),
        # B: pre-specified session filters on the near-miss capitulation
        ("capit US-hours", "maker",
         machine(d1, capit & us_hours, no_exit, +1, 48), 1.5, 4.5),
        ("capit Asia-hours", "maker",
         machine(d1, capit & asia_hours, no_exit, +1, 48), 1.5, 4.5),
        # C: compression breakouts
        ("squeeze brkout 1:4", "taker",
         machine(d1, squeeze & (d1["close"] > hi_n(d1, 24)), no_exit, +1, 48),
         1.0, 4.0),
        ("squeeze brkout 1:6", "taker",
         machine(d1, squeeze & (d1["close"] > hi_n(d1, 24)), no_exit, +1, 72),
         1.0, 6.0),
    ]

    rows, keep = [], {}
    for tag, ex, sig, stop, tgt in cands:
        runs = score(d1, sig, f1, stop, tgt, ex)
        keep[tag] = (sig, stop, tgt, ex, runs)
        r_tr, r_va, _ = runs
        rows.append({
            "config": tag, "exec": ex,
            "tr_n": len(r_tr.trades), "tr_win%": r_tr.win_rate * 100,
            "tr_exp": r_tr.expectancy, "tr_ret%": r_tr.total_return_pct,
            "va_n": len(r_va.trades), "va_exp": r_va.expectancy,
            "va_ret%": r_va.total_return_pct,
        })
    print("ROUND 15 CANDIDATES at 1x (train + validation, 6yr, full costs):")
    print(pd.DataFrame(rows).to_string(index=False,
                                       float_format=lambda x: f"{x:,.2f}"))

    qual = [t for t, (s, st, tg, ex, r) in keep.items()
            if r[0].expectancy > 0 and r[1].expectancy > 0
            and len(r[0].trades) >= 30 and len(r[1].trades) >= 8]
    print(f"\nqualified (positive BOTH windows): {qual or 'NONE'}")
    if not qual:
        print("\nRound 15: no qualifiers. The campaign continues — next")
        print("angles queued: funding-settlement timing, then flow data as")
        print("the collector matures.")
        return

    print("\nFINAL TEST + THE 10x FRONTIER (the mission metric):")
    for t in qual[:3]:
        sig, stop, tgt, ex, runs = keep[t]
        r_te = runs[2]
        print(f"\n  {t}: test exp ${r_te.expectancy:+,.2f}, "
              f"{r_te.total_return_pct:+.1f}%, win {r_te.win_rate * 100:.0f}%, "
              f"{len(r_te.trades)} trades, DD {r_te.max_drawdown_pct:.1f}%")
        if r_te.expectancy <= 0:
            print("    died on test — the gauntlet holds.")
            continue
        print(f"    {'lev':>5} {'final $':>12} {'maxDD':>7} {'lowest $':>9}")
        for lev in [1, 5, 10, 15]:
            r = run_backtest(d1, sig, initial_equity=1000, size_frac=lev,
                             execution=ex, stop_pct=stop, target_pct=tgt,
                             funding_series=f1)
            print(f"    {lev:>4}x {float(r.equity_curve.iloc[-1]):>12,.0f} "
                  f"{r.max_drawdown_pct:>6.1f}% "
                  f"{float(r.equity_curve.min()):>9,.2f}")


if __name__ == "__main__":
    main()
