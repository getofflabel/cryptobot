"""
step9_round4.py — round 4: the short side + assets retried with the vol gate.

Run:  python3 step9_round4.py

CHAMPION TO BEAT (round 3): vol-gated MA 20/100 long-only, 4h BTC.
  validation: $362.80/trade    test: $339.18/trade, +27.1%, DD -13.5%

Protocol identical to rounds 2-3: six years, 60/20/20 train/val/test, full
BloFin costs, size 1.0x. Selection on VALIDATION, one test look for what
qualifies, then the standing before/after table.
"""

import numpy as np
import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from strategy import vol_filtered_ma, vol_gated_ma

CHAMP_KW = {"fast": 20, "slow": 100, "min_atr_pct": 1.5}


def slice_run(df, sig, lo, hi):
    return run_backtest(df.iloc[lo:hi].reset_index(drop=True),
                        sig.iloc[lo:hi].reset_index(drop=True))


def score(df, sig):
    n = len(df)
    i_tr, i_va = int(n * 0.6), int(n * 0.8)
    return (slice_run(df, sig, 0, i_tr), slice_run(df, sig, i_tr, i_va),
            slice_run(df, sig, i_va, n))


def row(tag, runs, with_test=False):
    r_tr, r_va, r_te = runs
    d = {"config": tag, "tr_n": len(r_tr.trades), "tr_exp": r_tr.expectancy,
         "va_n": len(r_va.trades), "va_exp": r_va.expectancy,
         "va_ret%": r_va.total_return_pct, "va_dd%": r_va.max_drawdown_pct}
    if with_test:
        d.update({"te_n": len(r_te.trades), "te_exp": r_te.expectancy,
                  "te_ret%": r_te.total_return_pct,
                  "te_dd%": r_te.max_drawdown_pct})
    return d


def main():
    btc = fetch_bybit_deep("4h", "BTCUSDT")

    # sanity: the new state-machine implementation must reproduce the
    # champion exactly in long-only mode, or every comparison is bogus
    a = vol_filtered_ma(btc, **CHAMP_KW).fillna(0)
    b = vol_gated_ma(btc, **CHAMP_KW, allow_short=False).fillna(0)
    assert (a == b).all(), "state-machine impl diverges from champion!"
    print("sanity check: new implementation == champion in long-only mode\n")

    champ = score(btc, vol_filtered_ma(btc, **CHAMP_KW))

    # ---- PART 1: the short side on BTC ----------------------------------
    print("[1] SHORT SIDE on BTC (champion shown for reference)")
    ls_grid = [
        ("LS 20/100 gate1.5", {"fast": 20, "slow": 100, "min_atr_pct": 1.5}),
        ("LS 20/100 gate2.0", {"fast": 20, "slow": 100, "min_atr_pct": 2.0}),
        ("LS 30/50  gate1.5", {"fast": 30, "slow": 50, "min_atr_pct": 1.5}),
        ("LS 50/200 gate1.5", {"fast": 50, "slow": 200, "min_atr_pct": 1.5}),
    ]
    rows = [row("champion (L-only)", champ)]
    results = {}
    for tag, kw in ls_grid:
        runs = score(btc, vol_gated_ma(btc, **kw, allow_short=True))
        results[tag] = runs
        rows.append(row(tag, runs))
    print(pd.DataFrame(rows).to_string(index=False,
                                       float_format=lambda x: f"{x:,.2f}"))

    # ---- PART 2: SOL and ETH, now WITH the vol gate ---------------------
    print("\n[2] ASSETS RETRIED with the vol gate (they failed without it)")
    rows2 = []
    for sym in ["ETHUSDT", "SOLUSDT"]:
        d = fetch_bybit_deep("4h", sym)
        runs = score(d, vol_filtered_ma(d, **CHAMP_KW))
        results[f"{sym}+gate"] = runs
        rows2.append(row(f"{sym} gate1.5 L-only", runs))
    print(pd.DataFrame(rows2).to_string(index=False,
                                        float_format=lambda x: f"{x:,.2f}"))

    # ---- selection (validation only, champion's bar to clear) -----------
    champ_va = champ[1].expectancy
    qualified = [tag for tag, runs in results.items()
                 if runs[0].expectancy > 0
                 and len(runs[1].trades) >= 5
                 and (runs[1].expectancy > champ_va
                      or ("USDT" in tag and runs[1].expectancy > 0))]
    print(f"\nqualified for the one test look: {qualified or 'NONE'}")

    # ---- PART 3: single test look ---------------------------------------
    finals = [row("champion (round-3 baseline)", champ, with_test=True)]
    for tag in qualified:
        finals.append(row(tag, results[tag], with_test=True))
    print("\n[3] FINAL TEST")
    print(pd.DataFrame(finals).to_string(index=False,
                                         float_format=lambda x: f"{x:,.2f}"))

    # ---- the standing before/after table --------------------------------
    print("\n" + "=" * 70)
    print("ROUND 4 vs ROUND 3 — did the upgrade actually improve anything?")
    print("=" * 70)
    b = champ[2]
    print(f"  BEFORE: champion test ${b.expectancy:+,.2f}/trade, "
          f"{b.total_return_pct:+.1f}%, DD {b.max_drawdown_pct:.1f}%")
    improved = False
    for f in finals[1:]:
        beats = (f["te_exp"] > b.expectancy and f["te_ret%"] > 0
                 and "USDT" not in f["config"])
        adds_asset = ("USDT" in f["config"] and f["te_exp"] > 0
                      and f["te_ret%"] > 0)
        if beats:
            print(f"  AFTER : {f['config']} test ${f['te_exp']:+,.2f}/trade, "
                  f"{f['te_ret%']:+.1f}%, DD {f['te_dd%']:.1f}%  <- NEW CHAMPION")
            improved = True
        elif adds_asset:
            print(f"  ADD   : {f['config']} test ${f['te_exp']:+,.2f}/trade, "
                  f"{f['te_ret%']:+.1f}%, DD {f['te_dd%']:.1f}%  "
                  f"<- qualifies as a second sleeve")
            improved = True
    if not improved:
        print("  AFTER : nothing beat the champion on test. Belt retained;")
        print("          the ledger changes nothing.")


if __name__ == "__main__":
    main()
