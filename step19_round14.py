"""
step19_round14.py — round 14: POSITIONING setups. The trader-replication round.

Run:  python3 step19_round14.py

Open interest is the count of live leveraged positions — the market's fuel
gauge. Combined with price and funding it reads like a trader reads a
crowd:

  CAPITULATION  : OI collapsing while price dumps = leveraged longs being
                  liquidated out. When the fuel is spent, the selling is
                  too — a bounce long with a tight stop.
  PILEUP FADE   : OI ballooning while price goes NOWHERE = leverage
                  stacking into a wall. Fragile. Fade it short.
  PILEUP BREAK  : that same stacked leverage + price snapping the range =
                  cascade of stop-outs to ride, short.
  CONFIRMED BRKOUT: price breaks out AND OI expands = real money entering,
                  not a hollow wick. The breakout filter round 12 lacked.

Six years of hourly OI (2020-2026). Full discipline: 60/20/20, taker
entries, intra-bar stops AND targets, real funding. Survivors get the
leverage frontier — this is the round built to answer "trade like the
high-level guys", so the bar stays exactly as high as ever.
"""

import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step17_round12 import hi_n, lo_n, machine
from strategy import atr


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
    oi = pd.read_parquet("data_bybit_BTCUSDT_oi_1h.parquet")
    d = pd.merge_asof(d, oi, on="timestamp", direction="backward")

    oi_24h = d["oi"].pct_change(24) * 100
    px_24h = d["close"].pct_change(24) * 100
    lively = (atr(d, 14) / d["close"] * 100) >= 0.5
    no_exit = pd.Series(False, index=d.index)

    cands = [
        ("capitulation -6/-3 1:3",
         machine(d, (oi_24h < -6) & (px_24h < -3), no_exit, +1, 48), 1.5, 4.5),
        ("capitulation -8/-4 1:4",
         machine(d, (oi_24h < -8) & (px_24h < -4), no_exit, +1, 48), 1.5, 6.0),
        ("pileup fade +6/flat 1:3",
         machine(d, (oi_24h > 6) & (px_24h.abs() < 1.5), no_exit, -1, 48),
         1.5, 4.5),
        ("pileup break +6 1:3",
         machine(d, (oi_24h > 6) & (d["close"] < lo_n(d, 24)), no_exit, -1, 48),
         1.5, 4.5),
        ("confirmed brkout +3 1:4",
         machine(d, (d["close"] > hi_n(d, 48)) & (oi_24h > 3) & lively,
                 no_exit, +1, 48), 1.0, 4.0),
        ("confirmed brkout +5 1:4",
         machine(d, (d["close"] > hi_n(d, 48)) & (oi_24h > 5) & lively,
                 no_exit, +1, 48), 1.0, 4.0),
    ]

    rows, keep = [], {}
    for tag, sig, stop, tgt in cands:
        runs = score(d, sig, f_bps, stop, tgt)
        keep[tag] = (sig, stop, tgt, runs)
        r_tr, r_va, _ = runs
        rows.append({
            "config": tag,
            "tr_n": len(r_tr.trades), "tr_win%": r_tr.win_rate * 100,
            "tr_exp": r_tr.expectancy, "tr_ret%": r_tr.total_return_pct,
            "va_n": len(r_va.trades), "va_win%": r_va.win_rate * 100,
            "va_exp": r_va.expectancy, "va_ret%": r_va.total_return_pct,
        })
    print("POSITIONING SETUPS at 1x (train + validation, 6yr, full costs):")
    print(pd.DataFrame(rows).to_string(index=False,
                                       float_format=lambda x: f"{x:,.2f}"))

    qual = [t for t, (s, st, tg, r) in keep.items()
            if r[0].expectancy > 0 and r[1].expectancy > 0
            and len(r[0].trades) >= 30 and len(r[1].trades) >= 8]
    print(f"\nqualified (positive BOTH windows): {qual or 'NONE'}")
    if not qual:
        print("\nVERDICT: positioning setups from OI/funding/price alone do")
        print("not clear costs. The collector keeps recording deeper data")
        print("(orderbook imbalance) that these numbers cannot see yet.")
        return

    print("\nFINAL TEST + LEVERAGE FRONTIER:")
    for t in qual[:3]:
        sig, stop, tgt, runs = keep[t]
        r_te = runs[2]
        print(f"\n  {t}: test exp ${r_te.expectancy:+,.2f}, "
              f"{r_te.total_return_pct:+.1f}%, win {r_te.win_rate * 100:.0f}%, "
              f"{len(r_te.trades)} trades, DD {r_te.max_drawdown_pct:.1f}%")
        if r_te.expectancy <= 0:
            print("    died on test.")
            continue
        print(f"    {'lev':>5} {'final $':>11} {'maxDD':>7} {'lowest $':>9}")
        for lev in [1, 3, 5, 10, 15, 20]:
            r = run_backtest(d, sig, initial_equity=1000, size_frac=lev,
                             execution="taker", stop_pct=stop, target_pct=tgt,
                             funding_series=f_bps)
            print(f"    {lev:>4}x {float(r.equity_curve.iloc[-1]):>11,.0f} "
                  f"{r.max_drawdown_pct:>6.1f}% "
                  f"{float(r.equity_curve.min()):>9,.2f}")


if __name__ == "__main__":
    main()
