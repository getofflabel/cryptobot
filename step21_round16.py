"""
step21_round16.py — round 16: the winning architecture, transferred.

Run:  python3 step21_round16.py

Round 15's breakthrough was an ARCHITECTURE, not just a strategy: a
proven slow trend filter gating tight-stop fast dip entries. This round
transfers it to ETH and SOL with the config FROZEN exactly as validated
on BTC (RSI(3)<15, 1.5% stop, 4.5% target, 48h max, maker entries, each
asset filtered by its OWN 4h vol-gated trend state). No tuning, no grids:
one config, one honest look per asset. Frozen-config transfer is the
lowest-overfit-risk test that exists — the strategy was designed blind to
these assets.

(Disclosure: ETH and SOL test windows were looked at in rounds 3/4/9 for
the CORE strategy family — different strategy, but the windows are not
pristine. Frozen config keeps this as clean as a transfer can be.)

Every surviving sleeve = ~50-70 more fast trades per year, which is
"take more trades, carefully" done the only way that survives: more
validated guns, not looser triggers.
"""

import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step17_round12 import machine
from step20_round15 import champion_state_on_1h
from strategy import rsi

STOP, TARGET, MAX_HOLD, RSI_TH = 1.5, 4.5, 48, 15   # FROZEN — round 15


def test_asset(sym):
    d1 = fetch_bybit_deep("1h", sym)
    d4 = fetch_bybit_deep("4h", sym)
    fund = fetch_funding_history(sym)
    f1, f4 = align_funding(d1, fund), align_funding(d4, fund)

    champ = champion_state_on_1h(d1, d4, f4)
    r3 = rsi(d1["close"], 3)
    sig = machine(d1, (champ == 1) & (r3 < RSI_TH),
                  pd.Series(False, index=d1.index), +1, MAX_HOLD)

    n = len(d1)
    i_tr, i_va = int(n * 0.6), int(n * 0.8)

    def run(lo, hi):
        return run_backtest(d1.iloc[lo:hi].reset_index(drop=True),
                            sig.iloc[lo:hi].reset_index(drop=True),
                            execution="maker", stop_pct=STOP,
                            target_pct=TARGET,
                            funding_series=f1.iloc[lo:hi].reset_index(drop=True))
    return run(0, i_tr), run(i_tr, i_va), run(i_va, n), d1, sig, f1


def main():
    print("MTF-DIP TRANSFER TEST — config frozen from BTC (round 15)\n")
    for sym in ["ETHUSDT", "SOLUSDT"]:
        r_tr, r_va, r_te, d1, sig, f1 = test_asset(sym)
        yrs = (d1["timestamp"].iloc[-1] - d1["timestamp"].iloc[0]).days / 365
        print(f"{sym} ({yrs:.1f} years of data):")
        for name, r in [("train", r_tr), ("val  ", r_va)]:
            print(f"  {name}: {len(r.trades):>3} trades | "
                  f"exp ${r.expectancy:>8,.2f} | {r.total_return_pct:>+7.1f}% "
                  f"| win {r.win_rate * 100:.0f}%")
        ok = (r_tr.expectancy > 0 and r_va.expectancy > 0
              and len(r_tr.trades) >= 30 and len(r_va.trades) >= 10)
        if not ok:
            print("  -> does not qualify; test stays sealed for this asset\n")
            continue
        print(f"  TEST : {len(r_te.trades):>3} trades | "
              f"exp ${r_te.expectancy:>8,.2f} | {r_te.total_return_pct:>+7.1f}% "
              f"| win {r_te.win_rate * 100:.0f}% | DD {r_te.max_drawdown_pct:.1f}%")
        if r_te.expectancy > 0:
            print(f"  ==> {sym} SLEEVE QUALIFIES for live paper "
                  f"(~{len(sig[sig == 1]) and (len(r_tr.trades) + len(r_va.trades) + len(r_te.trades)) / yrs:.0f} trades/yr)")
        else:
            print(f"  ==> died on test — no sleeve")
        print()


if __name__ == "__main__":
    main()
