"""
step16_round11.py — round 11: exit engineering on the champion.

Run:  python3 step16_round11.py

Entries have had four upgrades; the exit is still the original slow MA
cross. Classic exit improvements, each layered ON TOP of the champion's
entries (same entries, different way out, so any difference is pure exit):

  TRAIL k   : chandelier stop — exit if price falls more than k x ATR
              below the highest close since entry. Locks in trends the MA
              cross would give back.
  BREAKEVEN : once a trade is up 2-3 ATR, refuse to let it turn into a
              loss (exit at entry price).
  PARTIAL   : bank half the position at +5%, ride the rest to the MA
              cross. Uses the round-10 fractional engine.

Re-entry discipline: if a custom exit fires while the underlying trend is
still "long", we do NOT hop straight back in next bar (that would churn).
One trade per trend episode; a fresh episode requires the trend to reset.

Same gauntlet: 6 years, 60/20/20, maker fills, real funding.
Champion baseline: val +64.0%/DD -24.7 | test $401.30, +32.1%, DD -12.3.
"""

import numpy as np
import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from strategy import atr, vol_gated_ma

CHAMP_KW = {"fast": 20, "slow": 100, "min_atr_pct": 1.5}


def champion_exits(d, f_bps, trail_k=None, be_atr=None, partial_pct=None):
    """Champion entries + optional exit overlays. Returns a signal series
    (fractional-capable: PARTIAL scales the position to 0.5)."""
    base = vol_gated_ma(d, **CHAMP_KW, entry_filter=(f_bps <= 1.0))
    base_v = base.fillna(0).to_numpy()
    warm = base.notna().to_numpy()
    a = atr(d, 14).to_numpy()
    close = d["close"].to_numpy()

    out = []
    pos, entry, hi, blocked = 0.0, 0.0, 0.0, False
    for i in range(len(d)):
        if not warm[i]:
            out.append(float("nan"))
            continue
        b = base_v[i]
        if b != 1:
            blocked = False          # trend episode over: re-arm entries
        if pos == 0.0:
            if b == 1 and not blocked:
                pos, entry, hi = 1.0, close[i], close[i]
        else:
            hi = max(hi, close[i])
            exit_now = b != 1                       # the champion's own exit
            if trail_k is not None and close[i] < hi - trail_k * a[i]:
                exit_now = True
            if (be_atr is not None and hi >= entry + be_atr * a[i]
                    and close[i] <= entry):
                exit_now = True
            if (partial_pct is not None and pos == 1.0
                    and close[i] >= entry * (1 + partial_pct / 100)):
                pos = 0.5                           # bank half, ride half
            if exit_now:
                pos = 0.0
                blocked = b == 1     # custom exit mid-trend: no instant rejoin
        out.append(pos)
    return pd.Series(out, index=d.index)


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
         "va_n": len(r_va.trades), "va_exp": r_va.expectancy,
         "va_ret%": r_va.total_return_pct, "va_dd%": r_va.max_drawdown_pct}
    if with_test:
        d.update({"te_n": len(r_te.trades), "te_exp": r_te.expectancy,
                  "te_ret%": r_te.total_return_pct,
                  "te_dd%": r_te.max_drawdown_pct})
    return d


def main():
    d = fetch_bybit_deep("4h", "BTCUSDT")
    f_bps = align_funding(d, fetch_funding_history("BTCUSDT"))

    variants = {
        "champion (MA-cross exit)": dict(),
        "trail 3xATR": dict(trail_k=3),
        "trail 4xATR": dict(trail_k=4),
        "trail 5xATR": dict(trail_k=5),
        "breakeven @2ATR": dict(be_atr=2),
        "breakeven @3ATR": dict(be_atr=3),
        "partial 50% @+5%": dict(partial_pct=5),
        "trail4 + breakeven3": dict(trail_k=4, be_atr=3),
    }

    rows, results = [], {}
    for tag, kw in variants.items():
        runs = score(d, champion_exits(d, f_bps, **kw), f_bps)
        results[tag] = runs
        rows.append(row(tag, runs))
    print("EXIT VARIANTS (train + validation):")
    print(pd.DataFrame(rows).to_string(index=False,
                                       float_format=lambda x: f"{x:,.2f}"))

    ch = results["champion (MA-cross exit)"]
    ch_ret, ch_dd = ch[1].total_return_pct, ch[1].max_drawdown_pct
    qual = [t for t, r in results.items()
            if t != "champion (MA-cross exit)"
            and r[0].total_return_pct > 0
            and (r[1].total_return_pct > ch_ret
                 or (r[1].total_return_pct >= 0.9 * ch_ret
                     and r[1].max_drawdown_pct > ch_dd + 3))]
    print(f"\nqualified vs champion val (+{ch_ret:.1f}%, DD {ch_dd:.1f}%): "
          f"{qual or 'NONE'}")

    finals = [row("champion (baseline)", ch, with_test=True)]
    for t in qual[:2]:
        finals.append(row(t, results[t], with_test=True))
    print("\nFINAL TEST:")
    print(pd.DataFrame(finals).to_string(index=False,
                                         float_format=lambda x: f"{x:,.2f}"))

    print("\n" + "=" * 70)
    print("ROUND 11 vs ROUND 10 — the before/after")
    print("=" * 70)
    b = ch[2]
    print(f"  BEFORE: test ${b.expectancy:+,.2f}/trade, "
          f"{b.total_return_pct:+.1f}%, DD {b.max_drawdown_pct:.1f}%")
    promoted = False
    for f in finals[1:]:
        if (f["te_ret%"] > b.total_return_pct
                or (f["te_ret%"] >= 0.9 * b.total_return_pct
                    and f["te_dd%"] > b.max_drawdown_pct + 3)):
            print(f"  AFTER : {f['config']} — ${f['te_exp']:+,.2f}/trade, "
                  f"{f['te_ret%']:+.1f}%, DD {f['te_dd%']:.1f}%  <- candidate")
            promoted = True
    if not promoted:
        print("  AFTER : no exit overlay beat the slow MA cross on test.")
        print("          Belt defense #8 — patience IS the exit edge.")


if __name__ == "__main__":
    main()
