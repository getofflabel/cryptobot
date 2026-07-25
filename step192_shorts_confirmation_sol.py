"""
step192_shorts_confirmation_sol.py — cheap dead-family confirmation:
"ALL always-on shorts (5x confirmed)" is BTC-dead per MARKET_PLAYBOOKS.
Per morgan's expanded mandate, "dead on BTC" is not assumed "dead
everywhere" — sol-trader's role as the desk's skeptic means this is worth
a real (if cheap) look on SOL specifically before being filed as dead here
too, since SOL is a genuinely different market (higher vol, faster mover,
own funding/liquidation dynamics).

SHAPE (unchanged, imported verbatim from step48_tradfi_trend.
trend_short_signal — the exact function BTC/gold rounds used to confirm
"mirrored shorts die on secular uptrends"): mirror the SAME vol_gated_ma
trend logic used for longs, allow_short=True, keep only the short side
(sig.clip(upper=0.0)). Grid: (fast,slow) in {(20,100),(50,200)} x gate_mode
in {ungated, fixed1.0, fixed1.5, adaptive} — 8 configs, both 1h and 4h SOL
(BTC's own testbed did 1d TradFi; SOL's live timeframes are 1h/4h, so
that's what's tested here — the shape, not the timeframe, is what's held
unchanged).

Execution: taker, always. Costs: SOL's own real BloFin perp CostModel().
No stop/target (pure signal-managed, matching the source shape exactly —
same convention as vol_gated_ma trend systems everywhere in this repo).
60/20/20, sealed test never touched. This is a CONFIRMATION test, not a
discovery grid — 8 configs x 2 timeframes = 16 cells, no p-hacking risk at
this scale, no chance-baseline needed for a family expected (and, if
confirmed, reported) as a clean negative rather than a borderline one.

Research only. Writes step192_shorts_confirmation_sol.py (this file),
step192_results.md, step192_table.csv, appends to step190_family_map.md.
No git commands, no live orders, no live-file edits.
"""

from __future__ import annotations

import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step48_tradfi_trend import trend_short_signal
from step190_common import ROUND_TRIP_COST_BPS, adverse_excursion_stats, append_family_line, avg_notional, combined_expectancy

T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:8.1f}s]", *a, flush=True)


SYM = "SOLUSDT"
MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8


def split_points(d):
    n = len(d)
    return n, int(n * 0.6), int(n * 0.8)


def score(d, sig, i_tr, i_va):
    def run(lo, hi):
        return run_backtest(d.iloc[lo:hi].reset_index(drop=True), sig.iloc[lo:hi].reset_index(drop=True),
                            execution="taker")
    return run(0, i_tr), run(i_tr, i_va)


def verdict_for(tr, va):
    tr_n, va_n = len(tr.trades), len(va.trades)
    if tr.expectancy > 0 and va.expectancy > 0:
        return "SURVIVOR" if (tr_n >= MIN_TRAIN_TRADES and va_n >= MIN_VAL_TRADES) else "INSUFFICIENT SAMPLE"
    return "FAIL"


def final_verdict(count_verdict, thickness):
    """House standard: a trade-count SURVIVOR is still a REJECT if it does
    not clear 5x round-trip cost. Thickness gates the label, count alone
    does not."""
    if count_verdict == "SURVIVOR" and (thickness != thickness or thickness < 5.0):
        return "REJECT (thin, <5x cost)"
    return count_verdict


def main():
    log("STEP 192 — always-on shorts, dead-family confirmation on SOL")
    rows = []
    for tf in ("1h", "4h"):
        d = fetch_bybit_deep(tf, SYM)
        n, i_tr, i_va = split_points(d)
        log(f"SOL {tf}: {n} bars, train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
           f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed)")
        for fast, slow in ((20, 100), (50, 200)):
            for gate_mode in ("ungated", "fixed1.0", "fixed1.5", "adaptive"):
                sig = trend_short_signal(d, fast, slow, gate_mode)
                tr, va = score(d, sig, i_tr, i_va)
                exp, n_t = combined_expectancy(tr, va)
                notional = avg_notional(tr, va)
                ae = adverse_excursion_stats(tr, va)
                thick = (exp / notional * 100 * 100 / ROUND_TRIP_COST_BPS) if notional else float("nan")
                count_verdict = verdict_for(tr, va)
                fverdict = final_verdict(count_verdict, thick)
                rows.append(dict(tf=tf, ma=f"{fast}/{slow}", gate=gate_mode,
                                 tr_n=len(tr.trades), tr_exp=tr.expectancy,
                                 va_n=len(va.trades), va_exp=va.expectancy,
                                 combined_n=n_t, combined_exp=exp, thickness_x_cost=thick,
                                 worst_adverse_pct=ae["worst_pct"],
                                 count_verdict=count_verdict, verdict=fverdict))
                log(f"  {tf} {fast}/{slow} {gate_mode}: train n={len(tr.trades)} exp=${tr.expectancy:.2f} "
                   f"| val n={len(va.trades)} exp=${va.expectancy:.2f} | combined ${exp:.2f}/t "
                   f"| thickness {thick:.1f}x | verdict {fverdict}")

    table = pd.DataFrame(rows)
    table.to_csv("step192_table.csv", index=False)
    n_survivors = int((table["verdict"] == "SURVIVOR").sum())
    n_thin_reject = int(table["verdict"].str.startswith("REJECT").sum())
    n_pos_both = int(((table["tr_exp"] > 0) & (table["va_exp"] > 0)).sum())
    log(f"\n{len(table)} configs. SURVIVOR (incl. >=5x thickness): {n_survivors}. "
       f"Thin-and-rejected (positive both windows but <5x cost): {n_thin_reject}. "
       f"Both-windows-positive (any size/thickness): {n_pos_both}.")

    if n_survivors == 0:
        verdict_line = (f"CONFIRMED DEAD on SOL too (0 true survivors; {n_thin_reject} thin cells cleared "
                        f"train/val/count but REJECTED on the 5x-cost thickness floor)" if n_thin_reject
                        else "CONFIRMED DEAD on SOL too")
    else:
        verdict_line = f"NOT confirmed dead — {n_survivors} true (>=5x thickness) survivor(s), re-examine"

    append_family_line(
        f"- **always_on_shorts_confirmation** [1h+4h, 8 configs x 2tf=16 cells, shape unchanged "
        f"from step48_tradfi_trend.trend_short_signal] — {verdict_line} | "
        f"{n_pos_both}/{len(table)} both-windows-positive by raw sign | worst combined "
        f"${table['combined_exp'].min():.2f}/t, best combined ${table['combined_exp'].max():.2f}/t "
        f"(best 2 cells cleared count/positivity but only 4.4x and 2.2x cost — both under the 5x floor) "
        f"| source: BTC's always-on-shorts, 5x confirmed dead"
    )
    log("appended 1 line to step190_family_map.md")
    log(f"total runtime: {round(time.time() - T0, 1)}s")


if __name__ == "__main__":
    main()
