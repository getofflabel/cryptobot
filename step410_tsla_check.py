"""
step410_tsla_check.py - ROUND 410, JOB 1 FOLLOW-UP
THE ONE BREAKOUT SURVIVOR: IS IT A PLATEAU OR A SPIKE?

Research only. No orders. Nothing live is touched.

WHY
  Job 1 ran the daily breakout family on ten names, each picking its own
  breakout length and exit average on its own choosing slice. Nine failed
  the matched coin flip. TSLA passed, and passed hard: it sat at the top of
  the control distribution on return per bar held.

  One pass out of ten at a bar set to fire once in 360 by luck is more than
  chance would hand out, so it deserves a look rather than a shrug. But the
  setting was picked as the best of eighteen, which is exactly the way a
  lucky spike gets promoted. The check that separates the two is whether
  the neighbours agree. A real mechanism does not switch off when the
  breakout length moves one step.

  This file also reads TSLA's middle slice once, for that one setting.
  The final 20% is never opened.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
from step410_lib import (REPO, load_daily, split_60_20_20, costs_table,
                         run_long_engine, coin_flip_control, percentile_of,
                         summarise, fmt_summary)
from step410_nvda import signals, structural_stop, ENTRY_N, EXIT_EMA, N_CONFIGS

N_FLIPS = 2000
ADJ = 100.0 * (1 - 0.05 / N_CONFIGS)


def main():
    sym = "TSLA"
    costs = costs_table()
    cost = costs[sym]["p75"]
    d = load_daily(sym)
    i_tr, i_va = split_60_20_20(len(d))
    stop_lvl, _ = structural_stop(d, k=3)
    drift = np.log(d["close"].iloc[i_tr - 1] / d["open"].iloc[0]) / i_tr * 100.0

    print("=" * 84)
    print("TSLA daily breakout: the whole neighbourhood, choosing slice only")
    print("=" * 84)
    print(f"round-trip cost measured from real quotes: {cost:.4f}% of price")
    print(f"TSLA's own drift over the choosing slice: {drift:+.4f}% of price "
          f"per trading day")
    print(f"the sweep-adjusted bar is the {ADJ:.2f}th percentile of the matched")
    print("coin flip on return per BAR HELD")
    print(f"\n  {'N':>4}{'ema':>5}{'trades':>8}{'mean%/t':>10}{'%/bar':>9}"
          f"{'chance':>9}{'pctile':>8}{'hold R/C':>11}{'xcost':>7}")
    rows = []
    for N in ENTRY_N:
        for E in EXIT_EMA:
            e, x = signals(d, N, E)
            t = run_long_engine(d, e, x, stop_lvl, cost, 0, i_tr)
            s = summarise(t, cost)
            if s.get("n", 0) < 30:
                continue
            cf = coin_flip_control(d, x, stop_lvl, cost, 0, i_tr, len(t),
                                   n_runs=N_FLIPS, seed=23, eligible_mask=~x)
            p = percentile_of(s["perbar_pct"], cf["perbar"])
            rows.append(dict(entry_n=N, exit_ema=E, n=s["n"],
                             mean_pct=s["mean_pct"], perbar_pct=s["perbar_pct"],
                             cf_perbar=cf["perbar"].mean(), pctile=p,
                             real_hold=s["mean_hold"], cf_hold=cf["hold"].mean(),
                             thickness=s["thickness"]))
            print(f"  {N:>4}{E:>5}{s['n']:>8}{s['mean_pct']:>10.3f}"
                  f"{s['perbar_pct']:>9.4f}{cf['perbar'].mean():>9.4f}"
                  f"{p:>8.1f}{s['mean_hold']:>6.1f}/{cf['hold'].mean():<5.1f}"
                  f"{s['thickness']:>7.0f}")
    df = pd.DataFrame(rows)
    df.to_csv(f"{REPO}/step410_table_tsla_neighbourhood.csv", index=False)
    pb = df["pctile"].to_numpy()
    print(f"\n  {len(pb)} settings past the 30-trade floor")
    print(f"  percentile spread: lowest {pb.min():.1f}, median {np.median(pb):.1f}, "
          f"highest {pb.max():.1f}")
    print(f"  settings clearing the {ADJ:.2f}th bar: {(pb >= ADJ).sum()} of {len(pb)}")
    print(f"  settings clearing the plain 95th: {(pb >= 95).sum()} of {len(pb)}")

    # ---------------------------------------- read the middle slice once
    best = df.sort_values("mean_pct", ascending=False).iloc[0]
    bn, be = int(best.entry_n), int(best.exit_ema)
    print("\n" + "=" * 84)
    print(f"MIDDLE SLICE, READ ONCE, for the setting chosen on the choosing "
          f"slice: {bn}-day breakout, {be}-day average exit")
    print("=" * 84)
    e, x = signals(d, bn, be)
    tv = run_long_engine(d, e, x, stop_lvl, cost, i_tr, i_va)
    sv = summarise(tv, cost)
    if sv.get("n", 0) >= 8:
        cf = coin_flip_control(d, x, stop_lvl, cost, i_tr, i_va, sv["n"],
                               n_runs=N_FLIPS, seed=29, eligible_mask=~x)
        p = percentile_of(sv["perbar_pct"], cf["perbar"])
        dv = np.log(d["close"].iloc[i_va - 1] / d["open"].iloc[i_tr]) / (i_va - i_tr) * 100.0
        print(f"  {fmt_summary(sv)}")
        print(f"  {sv['perbar_pct']:+.4f}% of price per bar held vs chance "
              f"{cf['perbar'].mean():+.4f}% -> {p:.1f}th percentile")
        print(f"  TSLA's own drift over the middle slice: {dv:+.4f}% per trading day")
        print(f"  hold: real {sv['mean_hold']:.1f} bars, chance {cf['hold'].mean():.1f}")
        verdict = ("SURVIVES" if p >= ADJ and sv["thickness"] >= 5 else
                   "fails the coin flip out of sample")
        print(f"  VERDICT: {verdict}")
    else:
        print(f"  INSUFFICIENT SAMPLE ({sv.get('n',0)} trades, floor is 8)")
    print("\nwrote step410_table_tsla_neighbourhood.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
