"""
step8_round3.py — round 3: entry quality + more assets, judged vs the champion.

Run:  python3 step8_round3.py

THE STANDING RULE THIS SCRIPT SERVES
Every research round ends with a BEFORE/AFTER table: the reigning champion
(round 2: MA 20/100 long-only, 4h BTC) against this round's best challenger,
on the identical protocol. Same six years, same 60/20/20 windows, same full
BloFin costs, same base sizing (1.0x — live leverage is applied separately).
If the table doesn't show improvement, the champion keeps its belt and the
ledger changes nothing.

ROUND 3 ATTACKS TWO THINGS
  1. ENTRY QUALITY (Wallace's critique: "did you actually find a good
     entry?"). Variants that demand a pullback, an RSI dip, or real
     volatility before entering the same trend the champion rides blindly.
  2. MORE ASSETS. ETH and SOL through the identical gauntlet. More
     independent trend-hunters = more good opportunities per year without
     adding leverage.
"""

import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from strategy import (ma_crossover, pullback_trend, rsi_dip_trend,
                      vol_filtered_ma)

CHAMPION = ("ma 20/100 (champion)", ma_crossover, {"fast": 20, "slow": 100})


def slice_run(df, sig, lo, hi):
    return run_backtest(df.iloc[lo:hi].reset_index(drop=True),
                        sig.iloc[lo:hi].reset_index(drop=True))


def windows(df):
    n = len(df)
    return int(n * 0.6), int(n * 0.8), n


def score(df, fn, kw):
    sig = fn(df, **kw)
    i_tr, i_va, n = windows(df)
    return (slice_run(df, sig, 0, i_tr), slice_run(df, sig, i_tr, i_va),
            slice_run(df, sig, i_va, n))


def row(tag, r_tr, r_va, r_te=None):
    d = {"config": tag,
         "tr_n": len(r_tr.trades), "tr_exp": r_tr.expectancy,
         "va_n": len(r_va.trades), "va_exp": r_va.expectancy,
         "va_ret%": r_va.total_return_pct, "va_dd%": r_va.max_drawdown_pct}
    if r_te is not None:
        d.update({"te_n": len(r_te.trades), "te_exp": r_te.expectancy,
                  "te_ret%": r_te.total_return_pct,
                  "te_dd%": r_te.max_drawdown_pct})
    return d


def main():
    print("Loading data...")
    btc = fetch_bybit_deep("4h", "BTCUSDT")

    # ---- PART 1: entry-quality variants on BTC --------------------------
    challengers = [
        ("pullback dip0%", pullback_trend,
         {"fast": 20, "slow": 100, "dip_pct": 0.0}),
        ("pullback dip1%", pullback_trend,
         {"fast": 20, "slow": 100, "dip_pct": 1.0}),
        ("rsi-dip <40", rsi_dip_trend,
         {"fast": 20, "slow": 100, "dip_below": 40}),
        ("rsi-dip <45", rsi_dip_trend,
         {"fast": 20, "slow": 100, "dip_below": 45}),
        ("vol-filter 1.0%", vol_filtered_ma,
         {"fast": 20, "slow": 100, "min_atr_pct": 1.0}),
        ("vol-filter 1.5%", vol_filtered_ma,
         {"fast": 20, "slow": 100, "min_atr_pct": 1.5}),
    ]

    print("\n[1] ENTRY QUALITY on BTC — challengers vs champion "
          "(train + validation only; test stays sealed for the winner)")
    rows = []
    champ_runs = score(btc, CHAMPION[1], CHAMPION[2])
    rows.append(row(CHAMPION[0], champ_runs[0], champ_runs[1]))
    results = {CHAMPION[0]: champ_runs}
    for tag, fn, kw in challengers:
        runs = score(btc, fn, kw)
        results[tag] = runs
        rows.append(row(tag, runs[0], runs[1]))
    t1 = pd.DataFrame(rows)
    print(t1.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    # Selection: beat the champion's VALIDATION expectancy with positive
    # train, decided before any test look.
    champ_va = champ_runs[1].expectancy
    better = [tag for tag, runs in results.items()
              if tag != CHAMPION[0]
              and runs[0].expectancy > 0
              and runs[1].expectancy > champ_va
              and len(runs[1].trades) >= 5]

    # ---- PART 2: more assets --------------------------------------------
    print("\n[2] MORE ASSETS — champion params on ETH and SOL")
    rows2 = []
    asset_runs = {}
    for sym in ["ETHUSDT", "SOLUSDT"]:
        d = fetch_bybit_deep("4h", sym)
        runs = score(d, CHAMPION[1], CHAMPION[2])
        asset_runs[sym] = (d, runs)
        rows2.append(row(f"ma 20/100 {sym}", runs[0], runs[1]))
    t2 = pd.DataFrame(rows2)
    print(t2.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    asset_ok = [s for s, (d, runs) in asset_runs.items()
                if runs[0].expectancy > 0 and runs[1].expectancy > 0
                and len(runs[1].trades) >= 5]

    # ---- PART 3: one test look for what earned it -----------------------
    print("\n[3] FINAL TEST — one look for qualified candidates only")
    finals = []
    if better:
        for tag in better[:2]:
            fn, kw = next((f, k) for t, f, k in challengers if t == tag)
            r_te = score(btc, fn, kw)[2]
            finals.append(row(f"BTC {tag}", *results[tag][:2], r_te))
    for sym in asset_ok:
        d, runs = asset_runs[sym]
        finals.append(row(f"{sym} champion-params", runs[0], runs[1], runs[2]))
    # champion's test numbers are already public from round 2; reprint for
    # the comparison table
    finals.insert(0, row("BTC champion (round-2 baseline)", *champ_runs))

    t3 = pd.DataFrame(finals)
    print(t3.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    # ---- THE BEFORE/AFTER TABLE -----------------------------------------
    print("\n" + "=" * 70)
    print("ROUND 3 vs ROUND 2 — did the upgrade actually improve anything?")
    print("=" * 70)
    base_te = champ_runs[2]
    print(f"  BEFORE (champion): test exp ${base_te.expectancy:+,.2f}/trade, "
          f"{base_te.total_return_pct:+.1f}%, DD {base_te.max_drawdown_pct:.1f}%")
    improved = False
    for f in finals[1:]:
        if "te_exp" in f and f["te_exp"] > base_te.expectancy and \
                f.get("te_ret%", -99) > 0:
            print(f"  AFTER  ({f['config']}): test exp ${f['te_exp']:+,.2f}"
                  f"/trade, {f['te_ret%']:+.1f}%, DD {f['te_dd%']:.1f}%  "
                  f"<- IMPROVEMENT")
            improved = True
    if not improved:
        print("  AFTER: no challenger beat the champion on the test window.")
        print("  The champion keeps the belt; the ledger changes nothing.")
    if asset_ok:
        print(f"\n  Asset expansion qualified: {', '.join(asset_ok)} — "
              f"diversification value even at similar expectancy.")


if __name__ == "__main__":
    main()
