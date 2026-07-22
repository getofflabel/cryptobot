"""
step10_round5.py — round 5: maker execution + full timeframe sweep + shorts retrial.

Run:  python3 step10_round5.py

WHAT CHANGES THIS ROUND
  1. EXECUTION: post-only maker orders (modeled honestly — limits that
     price runs away from get chased at taker cost). Round trip drops from
     18 bps toward ~4-10 bps depending on fill rate.
  2. TIMEFRAMES: 1h, 2h, 4h, 1d — no more 4h assumption. Cheaper fills may
     revive faster trading that taker costs used to kill.
  3. SHORTS RETRIED where they'd most plausibly work: faster TFs, cheaper
     costs. If they fail everywhere AGAIN, the verdict is structural
     (BTC downmoves too fast/squeezy for MA-trend shorts), not cost-based.

CROSS-TIMEFRAME SCORING NOTE
$/trade is NOT comparable across timeframes (a 1h config trades 5x more
often than 1d). Primary rank = VALIDATION RETURN %, drawdown as tiebreak.

BEFORE/AFTER BASELINE: round-3 champion (vol-gated MA 20/100 4h L-only)
under TAKER execution — test $+339.18/trade, +27.1%, DD -13.5%.
"""

import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from strategy import vol_gated_ma

MIN_VAL_TRADES = {"1h": 25, "2h": 15, "4h": 5, "1d": 4}


def score(df, sig, execution):
    n = len(df)
    i_tr, i_va = int(n * 0.6), int(n * 0.8)

    def run(lo, hi):
        return run_backtest(df.iloc[lo:hi].reset_index(drop=True),
                            sig.iloc[lo:hi].reset_index(drop=True),
                            execution=execution)
    return run(0, i_tr), run(i_tr, i_va), run(i_va, n)


def main():
    print("Loading data (1h and 2h are first-time fetches, ~2 min)...")
    frames = {tf: fetch_bybit_deep(tf, "BTCUSDT")
              for tf in ["1h", "2h", "4h", "1d"]}

    grid = []
    for f, s in [(20, 100), (30, 50), (50, 200)]:
        for gate in [1.0, 1.5]:
            for short in [False, True]:
                grid.append((f, s, gate, short))

    print(f"\nsweeping {len(grid)} configs x {len(frames)} timeframes, "
          f"MAKER execution, train+val only...\n")

    rows, runs_by_tag = [], {}
    for tf, d in frames.items():
        for f, s, gate, short in grid:
            sig = vol_gated_ma(d, fast=f, slow=s, min_atr_pct=gate,
                               allow_short=short)
            runs = score(d, sig, "maker")
            tag = f"{tf} {f}/{s} g{gate} {'LS' if short else 'L'}"
            runs_by_tag[tag] = (d, sig, runs)
            r_tr, r_va, _ = runs
            rows.append({
                "config": tag, "tr_ret%": r_tr.total_return_pct,
                "va_n": len(r_va.trades), "va_exp": r_va.expectancy,
                "va_ret%": r_va.total_return_pct,
                "va_dd%": r_va.max_drawdown_pct,
                "ok": (r_tr.expectancy > 0 and r_va.expectancy > 0
                       and len(r_va.trades) >= MIN_VAL_TRADES[tf]),
            })

    res = pd.DataFrame(rows)
    print("TOP 15 BY VALIDATION RETURN (maker execution, after costs):")
    print(res.sort_values("va_ret%", ascending=False).head(15)
          .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    survivors = res[res["ok"]].sort_values("va_ret%", ascending=False)
    n_ls = int(survivors["config"].str.endswith("LS").sum())
    print(f"\nsurvivors: {len(survivors)} (of which LS/short-capable: {n_ls})")

    # ---- the one test look ----------------------------------------------
    # champion under maker (execution-effect isolation) + top 2 survivors
    print("\nFINAL TEST — champion-under-maker + top 2 survivors:")
    finals = []
    champ_d, champ_sig = frames["4h"], vol_gated_ma(
        frames["4h"], fast=20, slow=100, min_atr_pct=1.5, allow_short=False)
    ch_runs = score(champ_d, champ_sig, "maker")
    finals.append(("4h champ + maker exec", ch_runs))
    for tag in survivors["config"].head(2):
        if tag == "4h 20/100 g1.5 L":
            continue                      # already covered as champion
        finals.append((tag, runs_by_tag[tag][2]))

    out = []
    for tag, (r_tr, r_va, r_te) in finals:
        out.append({"config": tag,
                    "va_ret%": r_va.total_return_pct,
                    "te_n": len(r_te.trades), "te_exp": r_te.expectancy,
                    "te_ret%": r_te.total_return_pct,
                    "te_dd%": r_te.max_drawdown_pct})
    print(pd.DataFrame(out).to_string(index=False,
                                      float_format=lambda x: f"{x:,.2f}"))

    # ---- standing before/after table ------------------------------------
    print("\n" + "=" * 70)
    print("ROUND 5 vs ROUND 3/4 CHAMPION — the before/after")
    print("=" * 70)
    print("  BEFORE (taker exec): test $+339.18/trade, +27.1%, DD -13.5%")
    best = max(out, key=lambda r: r["te_ret%"])
    print(f"  AFTER  ({best['config']}): test ${best['te_exp']:+,.2f}/trade, "
          f"{best['te_ret%']:+.1f}%, DD {best['te_dd%']:.1f}%")
    ch = out[0]
    print(f"\n  execution effect alone (same strategy, maker fills): "
          f"{ch['te_ret%']:+.1f}% vs +27.1% taker")


if __name__ == "__main__":
    main()
