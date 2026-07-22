"""
step6_strategy_search.py — the hunt for something with positive expectancy.

Run:  python3 step6_strategy_search.py

DISCIPLINE, TIGHTENED FOR A WIDER SEARCH

Step 4 used two windows (train/test). Now that we are testing SIX strategy
families x two timeframes x parameter grids, two windows are not enough:
with this many candidates, one will look good on any single holdout by
luck. So three windows:

  TRAIN (oldest 60%) : every combo runs here. Used only to rank.
  VAL   (next 20%)   : the ranking's survivors are re-scored here.
                       Selection happens HERE, on data training never saw.
  TEST  (newest 20%) : the final chosen few run here ONCE. This is the
                       closest thing to the future we own.

Multiple-look caveat, stated up front: our old Step 4 test window overlaps
this data, and testing several finalists (not one) weakens the holdout.
Whatever survives here is a CANDIDATE for live paper validation — the bot's
demo account is the only truly unseen data there is.
"""

import numpy as np
import pandas as pd

from backtest import run_backtest
from step3_run_strategy import fetch_history
from strategy import (bollinger_meanrev, buy_and_hold, donchian_breakout,
                      ma_crossover, ma_regime, momentum_roc, resample_4h,
                      rsi_meanrev)

MIN_TRADES = {"1h": 12, "4h": 6}     # fewer trades than this = noise


def slice_run(df, sig, lo, hi):
    c = df.iloc[lo:hi].reset_index(drop=True)
    s = sig.iloc[lo:hi].reset_index(drop=True)
    return run_backtest(c, s)


def build_candidates():
    """Every (name, function, params) combo we are willing to consider.
    Grids kept deliberately coarse: fine grids are overfitting machines."""
    cands = []
    for f, s in [(20, 50), (30, 50), (20, 100), (50, 200)]:
        cands.append((f"ma_cross {f}/{s}", ma_crossover,
                      {"fast": f, "slow": s}))
    for f, s, r in [(20, 50, 200), (30, 50, 400), (20, 100, 400)]:
        cands.append((f"ma_regime {f}/{s}/r{r}", ma_regime,
                      {"fast": f, "slow": s, "regime": r}))
    for e, x in [(55, 20), (100, 50), (30, 15)]:
        cands.append((f"donchian {e}/{x}", donchian_breakout,
                      {"entry_n": e, "exit_n": x}))
    for b, x in [(30, 55), (25, 50), (35, 60)]:
        cands.append((f"rsi_mr <{b}>{x}", rsi_meanrev,
                      {"buy_below": b, "exit_above": x}))
    for n in [72, 168, 336]:
        cands.append((f"momentum {n}", momentum_roc, {"n": n}))
    for n, k in [(20, 2.0), (48, 2.5)]:
        cands.append((f"boll_mr {n}/{k}", bollinger_meanrev,
                      {"n": n, "k": k}))
    return cands


def main():
    print("Loading data (cached)...")
    df_1h = fetch_history(8000)
    frames = {"1h": df_1h, "4h": resample_4h(df_1h)}
    for tf, d in frames.items():
        print(f"  {tf}: {len(d)} bars, "
              f"{d['timestamp'].iloc[0]:%Y-%m-%d} to "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d}")

    cands = build_candidates()
    print(f"\n{len(cands)} strategy configs x {len(frames)} timeframes "
          f"= {len(cands) * len(frames)} candidates\n")

    rows = []
    for tf, d in frames.items():
        n = len(d)
        i_tr, i_va = int(n * 0.6), int(n * 0.8)
        for name, fn, kw in cands:
            sig = fn(d, **kw)
            r_tr = slice_run(d, sig, 0, i_tr)
            r_va = slice_run(d, sig, i_tr, i_va)
            rows.append({
                "tf": tf, "strategy": name,
                "tr_trades": len(r_tr.trades), "tr_exp": r_tr.expectancy,
                "va_trades": len(r_va.trades), "va_exp": r_va.expectancy,
                "va_ret%": r_va.total_return_pct,
                "va_dd%": r_va.max_drawdown_pct,
            })

    res = pd.DataFrame(rows)

    # Selection rule, fixed BEFORE looking at test data:
    # positive expectancy on BOTH train and validation, enough trades in each.
    ok = res[
        (res["tr_exp"] > 0) & (res["va_exp"] > 0)
        & (res.apply(lambda r: r["tr_trades"] >= MIN_TRADES[r["tf"]], axis=1))
        & (res.apply(lambda r: r["va_trades"] >= MIN_TRADES[r["tf"]] // 2 + 1,
                     axis=1))
    ].sort_values("va_exp", ascending=False)

    print("TRAIN + VALIDATION (selection happens here, after costs):")
    show = res.sort_values("va_exp", ascending=False).head(12)
    print(show.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    print(f"\nsurvivors (positive on BOTH windows, enough trades): {len(ok)}")

    if ok.empty:
        print("\n" + "=" * 64)
        print("VERDICT: NO SURVIVORS")
        print("=" * 64)
        print("Every family that traded enough to judge has negative")
        print("after-cost expectancy on the validation window. The test")
        print("window stays SEALED — nothing earned the right to see it.")
        print("That seal matters: it is still virgin data for the next")
        print("research round instead of being burned on losers.")
        return

    # ---- the single look at TEST for the top survivors (max 3) ----------
    finalists = ok.head(3)
    print("\nFINAL TEST — one look, top survivors only:")
    out = []
    for _, row in finalists.iterrows():
        d = frames[row["tf"]]
        n = len(d)
        i_va = int(n * 0.8)
        name = row["strategy"]
        fn, kw = next((f, k) for nm, f, k in cands if nm == name)
        sig = fn(d, **kw)
        r_te = slice_run(d, sig, i_va, n)
        out.append({"tf": row["tf"], "strategy": name,
                    "va_exp": row["va_exp"], "te_trades": len(r_te.trades),
                    "te_exp": r_te.expectancy,
                    "te_ret%": r_te.total_return_pct,
                    "te_dd%": r_te.max_drawdown_pct})
    fin = pd.DataFrame(out)
    print(fin.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    # hold-out context: what did doing nothing earn on the same window?
    d = frames["1h"]
    r_bh = slice_run(d, buy_and_hold(d), int(len(d) * 0.8), len(d))
    print(f"\nbuy & hold on the same test window: "
          f"{r_bh.total_return_pct:+.2f}% (DD {r_bh.max_drawdown_pct:.1f}%)")

    print("\n" + "=" * 64)
    print("VERDICT")
    print("=" * 64)
    good = fin[fin["te_exp"] > 0]
    if good.empty:
        print("Validation winners DIED on the test window — the selection")
        print("was fitting noise. Nothing here deserves the demo account.")
    else:
        for _, g in good.iterrows():
            print(f"  CANDIDATE: {g['strategy']} on {g['tf']} — positive on")
            print(f"  train, validation AND test (${g['te_exp']:+,.2f}/trade,")
            print(f"  {g['te_trades']:.0f} test trades). Small sample, multiple")
            print("  looks taken — treat as promising, not proven. The next")
            print("  judge is live paper trading on data that doesn't exist yet.")


if __name__ == "__main__":
    main()
