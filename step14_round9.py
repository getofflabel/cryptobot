"""
step14_round9.py — round 9: ETH with the full champion stack + hunting the
train-positive cascade short.

Run:  python3 step14_round9.py

1. ETH SLEEVE ATTEMPT: ETH failed as a bare MA cross (r3) and with just the
   vol gate (r4). It has never been tried with the FULL champion stack:
   vol gate + funding euphoria cap + real ETH funding cashflows. Sleeve
   rule applies (it's an additional book, not a replacement): it must WIN
   train and validation, not beat the BTC champion.

2. CASCADE-SHORT GRID: round 8 got this family to near-breakeven train /
   strongly positive validation at f>2.5. A coarse grid over the funding
   threshold, breakdown depth, and exit speed hunts for the train-positive
   version. Shorts qualify by winning both windows, standalone.

Regime-scaled sizing is DEFERRED to its own round: fractional position
targets need an engine change plus verification, and engine changes do not
ride along in the back of a strategy round.
"""

import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from strategy import event_short, vol_gated_ma

CHAMP_KW = {"fast": 20, "slow": 100, "min_atr_pct": 1.5}


def score(df, sig, f_bps):
    n = len(df)
    i_tr, i_va = int(n * 0.6), int(n * 0.8)

    def run(lo, hi):
        return run_backtest(df.iloc[lo:hi].reset_index(drop=True),
                            sig.iloc[lo:hi].reset_index(drop=True),
                            execution="maker",
                            funding_series=f_bps.iloc[lo:hi].reset_index(drop=True))
    return run(0, i_tr), run(i_tr, i_va), run(i_va, n)


def row(tag, runs, with_test=False):
    r_tr, r_va, r_te = runs
    d = {"config": tag, "tr_n": len(r_tr.trades), "tr_exp": r_tr.expectancy,
         "tr_ret%": r_tr.total_return_pct,
         "va_n": len(r_va.trades), "va_exp": r_va.expectancy,
         "va_ret%": r_va.total_return_pct, "va_dd%": r_va.max_drawdown_pct}
    if with_test:
        d.update({"te_n": len(r_te.trades), "te_exp": r_te.expectancy,
                  "te_ret%": r_te.total_return_pct,
                  "te_dd%": r_te.max_drawdown_pct})
    return d


def main():
    results = {}

    # ---- 1. ETH with the full stack -------------------------------------
    print("[1] ETH, full champion stack (vol gate + funding cap + real "
          "ETH funding)")
    eth = fetch_bybit_deep("4h", "ETHUSDT")
    eth_f = align_funding(eth, fetch_funding_history("ETHUSDT"))
    rows = []
    for gate in [1.5, 2.0, 2.5]:
        for cap in [1.0, 2.0]:
            sig = vol_gated_ma(eth, fast=20, slow=100, min_atr_pct=gate,
                               entry_filter=(eth_f <= cap))
            runs = score(eth, sig, eth_f)
            tag = f"ETH g{gate} cap{cap:.0f}"
            results[tag] = runs
            rows.append(row(tag, runs))
    print(pd.DataFrame(rows).to_string(index=False,
                                       float_format=lambda x: f"{x:,.2f}"))

    # ---- 2. cascade-short grid ------------------------------------------
    print("\n[2] CASCADE-SHORT grid (4h BTC, real funding — the near-miss "
          "family from round 8)")
    btc = fetch_bybit_deep("4h", "BTCUSDT")
    btc_f = align_funding(btc, fetch_funding_history("BTCUSDT"))

    def lo_n(n):
        return btc["low"].rolling(n).min().shift(1)

    def hi_n(n):
        return btc["high"].rolling(n).max().shift(1)

    rows2 = []
    for thresh in [2.0, 2.5, 3.0, 4.0]:
        for brk in [20, 55]:
            for ex in [10, 20]:
                enter = (btc_f > thresh) & (btc["close"] < lo_n(brk))
                exit_ = btc["close"] > hi_n(ex)
                sig = event_short(btc, enter, exit_, max_hold=30)
                runs = score(btc, sig, btc_f)
                tag = f"casc f>{thresh} brk{brk} ex{ex}"
                results[tag] = runs
                r = row(tag, runs)
                if r["tr_n"] >= 3:
                    rows2.append(r)
    t2 = pd.DataFrame(rows2).sort_values("va_exp", ascending=False)
    print(t2.head(10).to_string(index=False,
                                float_format=lambda x: f"{x:,.2f}"))

    # ---- qualification ---------------------------------------------------
    qual = []
    for tag, runs in results.items():
        r_tr, r_va, _ = runs
        min_tr, min_va = (10, 4) if tag.startswith("ETH") else (10, 3)
        if (r_tr.expectancy > 0 and r_va.expectancy > 0
                and len(r_tr.trades) >= min_tr
                and len(r_va.trades) >= min_va):
            qual.append(tag)
    print(f"\nqualified (win BOTH windows, enough trades): {qual or 'NONE'}")

    finals = []
    for tag in qual[:3]:
        finals.append(row(tag, results[tag], with_test=True))
    if finals:
        print("\nFINAL TEST — one look:")
        print(pd.DataFrame(finals).to_string(
            index=False, float_format=lambda x: f"{x:,.2f}"))

    # ---- before/after -----------------------------------------------------
    print("\n" + "=" * 70)
    print("ROUND 9 vs ROUND 8 — the before/after")
    print("=" * 70)
    print("  BEFORE: BTC champion alone — test $+401.30/trade, +32.1%, "
          "DD -12.3%")
    added = False
    for f in finals:
        if f["te_exp"] > 0 and f["te_ret%"] > 0:
            kind = "ETH SLEEVE" if f["config"].startswith("ETH") else \
                "SHORT SLEEVE"
            print(f"  AFTER : + {kind} {f['config']} — standalone test "
                  f"${f['te_exp']:+,.2f}/trade, {f['te_ret%']:+.1f}%, "
                  f"DD {f['te_dd%']:.1f}%")
            added = True
    if not added:
        print("  AFTER : unchanged. No sleeve earned; belt defense #6.")


if __name__ == "__main__":
    main()
