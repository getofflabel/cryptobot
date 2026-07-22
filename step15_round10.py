"""
step15_round10.py — round 10: regime-scaled sizing on the champion.

Run:  python3 step15_round10.py

THE IDEA
The champion is all-or-nothing: 100% size whenever it's long. But not all
longs are equal. Two well-evidenced ways to scale size with conditions:

  VOL TARGETING : size = target_vol / current_vol (capped at 1). When the
                  market gets wild, an unchanged position secretly holds
                  more risk — shrinking size keeps RISK constant instead
                  of dollars constant. The most robust sizing result in
                  the trend-following literature.
  TREND TIERS   : full size only when the trend is emphatic (wide gap
                  between the fast and slow averages); reduced size when
                  it's marginal.

Both only ever scale DOWN from the champion's size, so they cannot win by
secretly levering up — any win must come from losing less in bad regimes.

Same gauntlet as always: 6 years, 60/20/20, maker fills, real funding.
Champion baseline: validation +64.0% / DD -24.7 | test +32.1% / DD -12.3.
"""

import numpy as np
import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from strategy import atr, vol_gated_ma

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
    d = {"config": tag, "tr_ret%": r_tr.total_return_pct,
         "tr_dd%": r_tr.max_drawdown_pct,
         "va_ret%": r_va.total_return_pct, "va_dd%": r_va.max_drawdown_pct,
         "va_n": len(r_va.trades)}
    if with_test:
        d.update({"te_exp": r_te.expectancy, "te_ret%": r_te.total_return_pct,
                  "te_dd%": r_te.max_drawdown_pct, "te_n": len(r_te.trades)})
    return d


def main():
    btc = fetch_bybit_deep("4h", "BTCUSDT")
    f_bps = align_funding(btc, fetch_funding_history("BTCUSDT"))

    base = vol_gated_ma(btc, **CHAMP_KW, entry_filter=(f_bps <= 1.0))
    atr_pct = atr(btc, 14) / btc["close"] * 100
    gap_pct = (btc["close"].rolling(20).mean()
               / btc["close"].rolling(100).mean() - 1) * 100

    variants = {"champion 1.0x (baseline)": base}

    # vol targeting: full size at/below target vol, shrink above it
    for tv in [1.5, 2.0, 2.5]:
        frac = (tv / atr_pct).clip(upper=1.0, lower=0.4)
        variants[f"vol-target {tv}%"] = base * frac

    # trend tiers: emphatic trend = full size, marginal trend = 60%
    for g in [1.5, 2.5]:
        frac = pd.Series(np.where(gap_pct >= g, 1.0, 0.6), index=btc.index)
        variants[f"trend-tier gap{g}%"] = base * frac

    rows, results = [], {}
    for tag, sig in variants.items():
        runs = score(btc, sig, f_bps)
        results[tag] = runs
        rows.append(row(tag, runs))
    print("SIZING VARIANTS (train + validation):")
    print(pd.DataFrame(rows).to_string(index=False,
                                       float_format=lambda x: f"{x:,.2f}"))

    # selection: better validation RISK-ADJUSTED result than the champion —
    # here: return no worse than ~90% of champion's AND drawdown clearly
    # shallower, or return higher outright. Decided before the test look.
    ch = results["champion 1.0x (baseline)"]
    ch_ret, ch_dd = ch[1].total_return_pct, ch[1].max_drawdown_pct
    qual = []
    for tag, runs in results.items():
        if tag.startswith("champion"):
            continue
        va = runs[1]
        better_ret = va.total_return_pct > ch_ret
        similar_ret_less_pain = (va.total_return_pct >= 0.9 * ch_ret
                                 and va.max_drawdown_pct > ch_dd + 3)
        if runs[0].total_return_pct > 0 and (better_ret or similar_ret_less_pain):
            qual.append(tag)
    print(f"\nqualified vs champion validation (+{ch_ret:.1f}%, DD {ch_dd:.1f}%): "
          f"{qual or 'NONE'}")

    finals = [row("champion (baseline)", ch, with_test=True)]
    for tag in qual[:2]:
        finals.append(row(tag, results[tag], with_test=True))
    print("\nFINAL TEST:")
    print(pd.DataFrame(finals).to_string(index=False,
                                         float_format=lambda x: f"{x:,.2f}"))

    print("\n" + "=" * 70)
    print("ROUND 10 vs ROUND 9 — the before/after")
    print("=" * 70)
    b = ch[2]
    print(f"  BEFORE: test ${b.expectancy:+,.2f}/trade, "
          f"{b.total_return_pct:+.1f}%, DD {b.max_drawdown_pct:.1f}%")
    promoted = False
    for f in finals[1:]:
        if (f["te_ret%"] > b.total_return_pct
                or (f["te_ret%"] >= 0.9 * b.total_return_pct
                    and f["te_dd%"] > b.max_drawdown_pct + 3)):
            print(f"  AFTER : {f['config']} — test ${f['te_exp']:+,.2f}/trade, "
                  f"{f['te_ret%']:+.1f}%, DD {f['te_dd%']:.1f}%  <- PROMOTED")
            promoted = True
    if not promoted:
        print("  AFTER : no sizing variant beat the champion where it counts.")
        print("          Belt defense #7; all-in-when-right remains optimal")
        print("          for this strategy's entry quality.")


if __name__ == "__main__":
    main()
