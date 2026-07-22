"""
step17_round12.py — round 12: the hunt for 10-20x-compatible strategies.

Run:  python3 step17_round12.py

THE GEOMETRY OF HIGH LEVERAGE
At 20x, liquidation sits ~4-5% from entry, so a viable 20x strategy must
use stops FAR tighter than that (1-1.5%), which forces short holds and
fast exits. Leverage never creates an edge — it multiplies one — so the
gate is unchanged: the strategy must be profitable at 1x AFTER COSTS
first. Only survivors get the leverage frontier mapped.

Execution is TAKER for these families (momentum entries chase; pretending
we'd get maker fills on a breakout would flatter). Stops are intra-bar via
the round-12 engine. Real funding. Same 60/20/20 discipline.
"""

import numpy as np
import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from strategy import atr, rsi


def machine(d, enter, exit_, direction, max_hold=0):
    """Event state machine: enter on `enter`, leave on `exit_` or after
    max_hold bars. Engine's stop_pct handles the hard stop underneath."""
    e = enter.fillna(False).to_numpy(bool)
    x = exit_.fillna(False).to_numpy(bool)
    out, pos, held = [], 0.0, 0
    for i in range(len(d)):
        if pos == 0.0:
            if e[i]:
                pos, held = float(direction), 0
        else:
            held += 1
            if x[i] or (max_hold and held >= max_hold):
                pos = 0.0
        out.append(pos)
    return pd.Series(out, index=d.index)


def hi_n(d, n):
    return d["high"].rolling(n).max().shift(1)


def lo_n(d, n):
    return d["low"].rolling(n).min().shift(1)


def build(d, f_bps):
    """(tag, signal, stop_pct) candidates — all tight-stop, fast-exit."""
    sma100 = d["close"].rolling(100).mean()
    up, down = d["close"] > sma100, d["close"] < sma100
    r3 = rsi(d["close"], 3)
    lively = (atr(d, 14) / d["close"] * 100) >= 0.5

    return [
        ("brkout 24h/exit6", machine(d, (d["close"] > hi_n(d, 24)) & lively & up,
                                     d["close"] < lo_n(d, 6), +1), 1.0),
        ("brkout 48h/exit12", machine(d, (d["close"] > hi_n(d, 48)) & lively & up,
                                      d["close"] < lo_n(d, 12), +1), 1.5),
        ("rsi3<10 dip", machine(d, (r3 < 10) & up,
                                r3 > 60, +1, max_hold=12), 1.5),
        ("rsi3<5 dip", machine(d, (r3 < 5) & up,
                               r3 > 60, +1, max_hold=12), 1.5),
        ("brkdown 24h short", machine(d, (d["close"] < lo_n(d, 24)) & lively & down,
                                      d["close"] > hi_n(d, 6), -1), 1.0),
        ("cascade tight short", machine(d, (f_bps > 1.5) & (d["close"] < lo_n(d, 24)),
                                        d["close"] > hi_n(d, 6), -1,
                                        max_hold=24), 1.0),
    ]


def score(df, sig, f_bps, stop, size=1.0):
    n = len(df)
    i_tr, i_va = int(n * 0.6), int(n * 0.8)

    def run(lo, hi):
        return run_backtest(df.iloc[lo:hi].reset_index(drop=True),
                            sig.iloc[lo:hi].reset_index(drop=True),
                            execution="taker", stop_pct=stop, size_frac=size,
                            funding_series=f_bps.iloc[lo:hi].reset_index(drop=True))
    return run(0, i_tr), run(i_tr, i_va), run(i_va, n)


def main():
    d = fetch_bybit_deep("1h", "BTCUSDT")
    f_bps = align_funding(d, fetch_funding_history("BTCUSDT"))

    rows, keep = [], {}
    for tag, sig, stop in build(d, f_bps):
        runs = score(d, sig, f_bps, stop)
        keep[tag] = (sig, stop, runs)
        r_tr, r_va, _ = runs
        rows.append({"config": tag, "stop%": stop,
                     "tr_n": len(r_tr.trades), "tr_exp": r_tr.expectancy,
                     "tr_ret%": r_tr.total_return_pct,
                     "va_n": len(r_va.trades), "va_exp": r_va.expectancy,
                     "va_ret%": r_va.total_return_pct,
                     "va_dd%": r_va.max_drawdown_pct})
    print("TIGHT-STOP FAMILIES at 1x (train + validation, taker, "
          "real funding):")
    print(pd.DataFrame(rows).to_string(index=False,
                                       float_format=lambda x: f"{x:,.2f}"))

    qual = [t for t, (s, st, r) in keep.items()
            if r[0].expectancy > 0 and r[1].expectancy > 0
            and len(r[0].trades) >= 30 and len(r[1].trades) >= 10]
    print(f"\nqualified (win train AND val at 1x): {qual or 'NONE'}")

    if not qual:
        print("\n" + "=" * 70)
        print("VERDICT: no tight-stop family survives costs at even 1x.")
        print("Leverage multiplies an edge; zero edge x 20 = zero. The")
        print("10-20x door stays closed until a fast edge earns it.")
        return

    print("\nFINAL TEST (one look) + LEVERAGE FRONTIER for survivors:")
    for t in qual[:2]:
        sig, stop, runs = keep[t]
        r_te = runs[2]
        print(f"\n  {t}: test exp ${r_te.expectancy:+,.2f}, "
              f"{r_te.total_return_pct:+.1f}%, DD {r_te.max_drawdown_pct:.1f}%, "
              f"{len(r_te.trades)} trades")
        if r_te.expectancy <= 0:
            print("    died on test — no leverage frontier for a loser.")
            continue
        print(f"    {'lev':>5} {'final $':>10} {'maxDD':>7} {'lowest $':>9}"
              f"  (full 6yr, $1k start)")
        for lev in [1, 5, 10, 15, 20]:
            r = run_backtest(d, sig, initial_equity=1000, size_frac=lev,
                             execution="taker", stop_pct=stop,
                             funding_series=f_bps)
            fin = float(r.equity_curve.iloc[-1])
            lo = float(r.equity_curve.min())
            print(f"    {lev:>4}x {fin:>10,.0f} {r.max_drawdown_pct:>6.1f}% "
                  f"{lo:>9,.2f}")


if __name__ == "__main__":
    main()
