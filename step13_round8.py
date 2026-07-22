"""
step13_round8.py — round 8: retrials under REAL funding cashflows.

Run:  python3 step13_round8.py

Round 7 convicted the cascade shorts under a cost model that charged them
funding they would actually have COLLECTED. Round 6 parked the squeeze-boost
longs on train-only evidence — and those enter when funding is negative,
meaning they too would collect, not pay. Both get honest retrials, and the
champion gets repriced so the headline number uses real cashflows.

Verdict rules unchanged: shorts qualify by WINNING both windows (standalone,
Wallace's rule); longs must beat the champion's validation. One test look
for qualifiers only.
"""

import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from strategy import atr, event_short, ma_crossover, rsi, vol_gated_ma

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
         "va_ret%": r_va.total_return_pct, "va_dd%": r_va.max_drawdown_pct,
         "fund$": r_tr.total_funding + r_va.total_funding}
    if with_test:
        d.update({"te_n": len(r_te.trades), "te_exp": r_te.expectancy,
                  "te_ret%": r_te.total_return_pct,
                  "te_dd%": r_te.max_drawdown_pct})
    return d


def lo_n(d, n):
    return d["low"].rolling(n).min().shift(1)


def hi_n(d, n):
    return d["high"].rolling(n).max().shift(1)


def main():
    funding = fetch_funding_history()
    frames = {tf: fetch_bybit_deep(tf, "BTCUSDT") for tf in ["1h", "4h"]}
    fb = {tf: align_funding(d, funding) for tf, d in frames.items()}

    d4, f4 = frames["4h"], fb["4h"]
    d1, f1 = frames["1h"], fb["1h"]

    print("\n[1] CHAMPION repriced under real funding (accounting fix only)")
    champ_filter = f4 <= 1.0
    champ_sig = vol_gated_ma(d4, **CHAMP_KW, entry_filter=champ_filter)
    champ = score(d4, champ_sig, f4)
    rows = [row("champion (+cap, real funding)", champ, with_test=True)]
    print(pd.DataFrame(rows).to_string(index=False,
                                       float_format=lambda x: f"{x:,.2f}"))
    print("  (fund$ = NET funding over train+val: negative means collected)")

    print("\n[2] SQUEEZE-BOOST retrial — longs that enter when the crowd is "
          "short (they collect funding)")
    results = {}
    rows2 = []
    base = ma_crossover(d4, 20, 100)
    for thresh in [-1.0, -2.0]:
        squeeze = (base == 1) & (f4 <= thresh)
        boosted = champ_sig.copy()
        boosted[(boosted == 0) & squeeze] = 1.0
        runs = score(d4, boosted, f4)
        results[f"squeeze {thresh:.0f}bp"] = runs
        rows2.append(row(f"squeeze {thresh:.0f}bp", runs))
    print(pd.DataFrame(rows2).to_string(index=False,
                                        float_format=lambda x: f"{x:,.2f}"))

    print("\n[3] CASCADE-SHORT retrial — shorts that enter when longs are "
          "paying heavily (now they collect it)")
    rows3 = []
    cascade_defs = [
        ("4h cascade f>1.5", d4, f4,
         (f4 > 1.5) & (d4["close"] < lo_n(d4, 20)),
         d4["close"] > hi_n(d4, 10), 30),
        ("4h cascade f>2.5", d4, f4,
         (f4 > 2.5) & (d4["close"] < lo_n(d4, 20)),
         d4["close"] > hi_n(d4, 10), 30),
        ("1h cascade f>1.5", d1, f1,
         (f1 > 1.5) & (d1["close"] < lo_n(d1, 20)),
         d1["close"] > hi_n(d1, 10), 72),
        ("1h crash-cont 3%/12", d1, f1,
         (d1["close"].pct_change() * 100 < -3.0)
         & ((atr(d1, 14) / d1["close"] * 100) >= 1.0),
         pd.Series(False, index=d1.index), 12),
    ]
    for tag, d, f_, enter, exit_, hold in cascade_defs:
        sig = event_short(d, enter, exit_, hold)
        runs = score(d, sig, f_)
        results[tag] = runs
        rows3.append(row(tag, runs))
    print(pd.DataFrame(rows3).to_string(index=False,
                                        float_format=lambda x: f"{x:,.2f}"))

    # ---- qualification ---------------------------------------------------
    champ_va_ret = champ[1].total_return_pct
    qual = []
    for tag, runs in results.items():
        r_tr, r_va, _ = runs
        if "squeeze" in tag:
            if (r_tr.expectancy > 0 and r_va.expectancy > 0
                    and r_va.total_return_pct > champ_va_ret):
                qual.append(tag)
        else:                                    # shorts: just WIN
            min_tr = 10 if tag.startswith("4h") else 25
            if (r_tr.expectancy > 0 and r_va.expectancy > 0
                    and len(r_tr.trades) >= min_tr):
                qual.append(tag)
    print(f"\nqualified for the one test look: {qual or 'NONE'}")

    finals = []
    for tag in qual[:3]:
        finals.append(row(tag, results[tag], with_test=True))
    if finals:
        print("\nFINAL TEST:")
        print(pd.DataFrame(finals).to_string(
            index=False, float_format=lambda x: f"{x:,.2f}"))

    # ---- before/after -----------------------------------------------------
    print("\n" + "=" * 70)
    print("ROUND 8 vs ROUND 7 — the before/after")
    print("=" * 70)
    b = champ[2]
    print(f"  champion, honest funding: test ${b.expectancy:+,.2f}/trade, "
          f"{b.total_return_pct:+.1f}%, DD {b.max_drawdown_pct:.1f}%")
    print(f"  (was $+356.87 / +28.5% / -12.9% under flat-charge funding)")
    any_new = False
    for f in finals:
        if f["te_exp"] > 0 and f["te_ret%"] > 0:
            kind = ("NEW CHAMPION candidate" if "squeeze" in f["config"]
                    else "SHORT SLEEVE earned")
            print(f"  {kind}: {f['config']} — test ${f['te_exp']:+,.2f}/trade, "
                  f"{f['te_ret%']:+.1f}%, DD {f['te_dd%']:.1f}%")
            any_new = True
    if not any_new:
        print("  No retrial survived test. The round-7 verdicts stand even")
        print("  under honest funding; contamination was not the reason.")


if __name__ == "__main__":
    main()
