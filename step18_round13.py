"""
step18_round13.py — round 13: the pro-trader archetype, quantified.

Run:  python3 step18_round13.py

Wallace's spec, taken seriously: intraday holds (out same day), tight 1R
stops, asymmetric payoffs (3R-6R targets), win rate ALLOWED to be lousy —
the rare runner pays for the string of small stops. That is expectancy
with a skewed payoff, and it is fully testable:

  expectancy = p(win) x R_win - p(loss) x 1R

At 4R targets, ~22% wins breaks even before costs; the edge question is
whether entries beat that hit-rate hurdle AFTER costs. Intra-bar stops AND
targets are both modeled (stop wins any both-touch bar — conservative).
Taker entries (momentum chases), maker target fills (resting limits).
Same 60/20/20 gauntlet. Survivors get the leverage frontier at 5-20x.
"""

import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step17_round12 import build as _unused  # noqa: F401 (import parity)
from step17_round12 import hi_n, lo_n, machine
from strategy import atr, rsi


def build(d, f_bps):
    """(tag, signal, stop_pct, target_pct) — all same-day archetypes."""
    sma100 = d["close"].rolling(100).mean()
    up, down = d["close"] > sma100, d["close"] < sma100
    lively = (atr(d, 14) / d["close"] * 100) >= 0.5
    bar_ret = d["close"].pct_change() * 100
    r3 = rsi(d["close"], 3)
    no_exit = pd.Series(False, index=d.index)     # exits = stop/target/time

    return [
        ("brkout24 1:4R", machine(d, (d["close"] > hi_n(d, 24)) & lively & up,
                                  no_exit, +1, max_hold=24), 1.0, 4.0),
        ("brkout24 1:6R", machine(d, (d["close"] > hi_n(d, 24)) & lively & up,
                                  no_exit, +1, max_hold=24), 1.0, 6.0),
        ("ignition 1:4R", machine(d, (bar_ret > 1.2) & lively & up,
                                  no_exit, +1, max_hold=24), 1.0, 4.0),
        ("ignition 1:3R tight", machine(d, (bar_ret > 1.5) & lively & up,
                                        no_exit, +1, max_hold=24), 0.75, 2.25),
        ("dip-snap 1:3R", machine(d, (r3 < 8) & up, no_exit, +1,
                                  max_hold=24), 1.0, 3.0),
        ("brkdown 1:4R short", machine(d, (d["close"] < lo_n(d, 24))
                                       & lively & down,
                                       no_exit, -1, max_hold=24), 1.0, 4.0),
        ("cascade 1:4R short", machine(d, (f_bps > 1.5)
                                       & (d["close"] < lo_n(d, 24)),
                                       no_exit, -1, max_hold=24), 1.0, 4.0),
    ]


def score(df, sig, f_bps, stop, target, size=1.0):
    n = len(df)
    i_tr, i_va = int(n * 0.6), int(n * 0.8)

    def run(lo, hi):
        return run_backtest(df.iloc[lo:hi].reset_index(drop=True),
                            sig.iloc[lo:hi].reset_index(drop=True),
                            execution="taker", stop_pct=stop,
                            target_pct=target, size_frac=size,
                            funding_series=f_bps.iloc[lo:hi].reset_index(drop=True))
    return run(0, i_tr), run(i_tr, i_va), run(i_va, n)


def main():
    d = fetch_bybit_deep("1h", "BTCUSDT")
    f_bps = align_funding(d, fetch_funding_history("BTCUSDT"))

    rows, keep = [], {}
    for tag, sig, stop, tgt in build(d, f_bps):
        runs = score(d, sig, f_bps, stop, tgt)
        keep[tag] = (sig, stop, tgt, runs)
        r_tr, r_va, _ = runs
        rows.append({
            "config": tag, "R": f"1:{tgt / stop:.0f}",
            "tr_n": len(r_tr.trades), "tr_win%": r_tr.win_rate * 100,
            "tr_exp": r_tr.expectancy, "tr_ret%": r_tr.total_return_pct,
            "va_n": len(r_va.trades), "va_win%": r_va.win_rate * 100,
            "va_exp": r_va.expectancy, "va_ret%": r_va.total_return_pct,
        })
    print("ASYMMETRIC R INTRADAY FAMILIES at 1x (train + validation):")
    print(pd.DataFrame(rows).to_string(index=False,
                                       float_format=lambda x: f"{x:,.2f}"))

    qual = [t for t, (s, st, tg, r) in keep.items()
            if r[0].expectancy > 0 and r[1].expectancy > 0
            and len(r[0].trades) >= 30 and len(r[1].trades) >= 10]
    print(f"\nqualified (positive BOTH windows): {qual or 'NONE'}")

    if not qual:
        print("\n" + "=" * 70)
        print("VERDICT: the archetype does not survive costs on this data")
        print("either — the R-math is fine, the ENTRIES don't clear the")
        print("hit-rate hurdle after fees. No leverage without an edge.")
        return

    print("\nFINAL TEST + LEVERAGE FRONTIER for survivors:")
    for t in qual[:2]:
        sig, stop, tgt, runs = keep[t]
        r_te = runs[2]
        print(f"\n  {t}: test exp ${r_te.expectancy:+,.2f}, "
              f"{r_te.total_return_pct:+.1f}%, win {r_te.win_rate * 100:.0f}%, "
              f"{len(r_te.trades)} trades, DD {r_te.max_drawdown_pct:.1f}%")
        if r_te.expectancy <= 0:
            print("    died on test — no frontier for a loser.")
            continue
        print(f"    {'lev':>5} {'final $':>11} {'maxDD':>7} {'lowest $':>9}")
        for lev in [1, 5, 10, 15, 20]:
            r = run_backtest(d, sig, initial_equity=1000, size_frac=lev,
                             execution="taker", stop_pct=stop,
                             target_pct=tgt, funding_series=f_bps)
            print(f"    {lev:>4}x {float(r.equity_curve.iloc[-1]):>11,.0f} "
                  f"{r.max_drawdown_pct:>6.1f}% "
                  f"{float(r.equity_curve.min()):>9,.2f}")


if __name__ == "__main__":
    main()
