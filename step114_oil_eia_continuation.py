"""
step114_oil_eia_continuation.py — Round 114: the EIA-continuation COSTED
strategy (the one real oil-native lead step111's diagnostic produced),
plus two honest "not testable with what we have" entries for the family
map (OPEC meeting reactions, contango/backwardation).

CAUTION, STATED UP FRONT: round 78 already spent 2 of its sealed looks on
EIA-Wednesday-adjacent hypotheses (a "reversal" config, both CL and BZ,
both FAIL) and flagged an unresolved conflict between that "fade" result
and this week's step111 finding of a "continuation" shape on the raw
price reaction. This script does NOT touch the sealed 20% — train+val
only — specifically BECAUSE that budget is already partially spent on
this exact topic; a third sealed look without first reconciling the two
studies would be spending it blind. A TRAIN+VAL PASS here is evidence the
idea is worth reconciling and eventually spending a sealed look on — it
is NOT a new sealed verdict, exactly like every step150-style script
tonight.

SHAPE: at each EIA release-hour trading bar (align_events, no-lookahead,
same as step111), take the DIRECTION of that bar's own open->close move
as the trade direction (long if positive, short if negative) — the
"continuation" finding step111 measured, now built into an actual
strategy with a real stop and taker costs. Entry fills at the NEXT bar's
open (the earliest a real trader could act once the release-hour bar has
printed). Stop: exits.stop_structure (chart structure), target:
exits.target_fixed_r(stop, r=2.0) — max_hold 4h (step111's decay finding:
by 4h the excess-magnitude ratio was already down to 1.35x from 1.75x at
1h, so this is not a long-hold thesis).

RESEARCH ONLY. No commits, no live orders, no live-file edits, sealed
test never touched. Writes step114_oil_eia_continuation.py (this file),
step114_results.md, step114_table.csv, and appends to
step110_family_map.md.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

import exits as E
from step45b_news_events import align_events
from step111_eia_reaction import build_event_calendar
from step150_common import (chance_baseline, fmt_stats, mask_to_events,
                            run_edge, split_points, thickness, trade_stats,
                            verdict_for)

FAMILY_MAP_PATH = "step110_family_map.md"


def append_family_line(line: str):
    with open(FAMILY_MAP_PATH, "a") as fh:
        fh.write(line.rstrip("\n") + "\n")


def main():
    print("=" * 78)
    print("ROUND 114 — EIA-continuation COSTED strategy (train+val only, sealed untouched)")
    print("=" * 78)
    d = pd.read_parquet("data_oil_CL_1h.parquet").reset_index(drop=True)
    n, i_tr, i_va = split_points(d)
    start, end = d["timestamp"].iloc[0], d["timestamp"].iloc[i_va - 1]
    eia_ts, _ = build_event_calendar(start, end)   # train+val window only — sealed dates excluded
    floor_idx, trading_idx, valid = align_events(d, eia_ts)

    opens, closes = d["open"].to_numpy(), d["close"].to_numpy()
    react_bar = floor_idx[valid]
    react_ret = np.sign(closes[react_bar] - opens[react_bar])
    trade_bar = trading_idx[valid]   # entry SIGNAL bar for run_edge is trade_bar - 1's close;
                                     # run_edge fills at signal_bar+1's open, so pass trade_bar-1
    entries_all = [(int(trade_bar[k] - 1), int(react_ret[k])) for k in range(len(trade_bar))
                  if react_ret[k] != 0 and 0 <= trade_bar[k] - 1 < n]
    print(f"EIA events in train+val window: {len(eia_ts)} | usable directional entries: {len(entries_all)}")

    def stop_builder(tc):
        return E.stop_structure(k=5, n_back=1, buffer_pct=0.0, use="wick")

    def target_builder(stop):
        return E.target_fixed_r(stop, r_multiple=2.0)

    max_hold_bars = 4
    tr_e = [(i, dr) for i, dr in entries_all if i < i_tr]
    va_e = [(i - i_tr, dr) for i, dr in entries_all if i_tr <= i < i_va]
    tr_c, va_c = d.iloc[0:i_tr].reset_index(drop=True), d.iloc[i_tr:i_va].reset_index(drop=True)
    tr, tr_skip = run_edge(tr_c, tr_e, stop_builder, target_builder, max_hold_bars, k=5)
    va, va_skip = run_edge(va_c, va_e, stop_builder, target_builder, max_hold_bars, k=5)
    tr_st, va_st = trade_stats(tr), trade_stats(va)
    verdict = verdict_for(tr_st, va_st)
    floor_ok = tr_st["n"] >= 30 and va_st["n"] >= 8
    if verdict.startswith("SURVIVOR") and not floor_ok:
        verdict = "INSUFFICIENT-SAMPLE"

    all_trades = tr + va
    avg_not = float(np.mean([t["notional"] for t in all_trades])) if all_trades else 0.0
    th = thickness(va_st["expectancy"], avg_not) if va_st["n"] else \
        dict(pct_notional=float("nan"), mult_12bps=float("nan"), mult_full_18bps=float("nan"))
    if verdict.startswith("SURVIVOR") and th["mult_full_18bps"] < 5.0:
        verdict = "REJECT (thin, under 5x cost) — TRAIN+VAL ONLY, sealed never spent"

    print(fmt_stats("TRAIN", tr_st), f"| skipped(no structure)={tr_skip}")
    print(fmt_stats("VAL  ", va_st), f"| skipped(no structure)={va_skip}")
    print(f"THICKNESS(val): {th['mult_full_18bps']:.2f}x full round-trip cost")
    print(f"VERDICT: {verdict}  (train+val only — sealed test NEVER touched this round)")

    long_frac = sum(1 for i, dr in va_e if dr == 1) / max(1, len(va_e))
    cb = chance_baseline(va_c, len(va_e), long_frac, stop_builder, target_builder,
                         max_hold_bars, None, "next_open", k=5, draws=100)
    beats = va_st["expectancy"] > cb["mean_exp"] if va_st["n"] else False
    print(f"CHANCE (val, {cb['n_draws']} draws): ${cb['mean_exp']:+.2f}/t vs real "
         f"${va_st['expectancy']:+.2f}/t -> {'BEATS' if beats else 'DOES NOT BEAT'} chance")

    append_family_line(
        f"- **11. EIA-continuation strategy (costed, TRAIN+VAL ONLY, sealed untouched)** — "
        f"{verdict} | val {va_st['n']}t ${va_st['expectancy']:+.2f}/t (train {tr_st['n']}t "
        f"${tr_st['expectancy']:+.2f}/t) | chance baseline: random-entry mean "
        f"${cb['mean_exp']:+.2f}/t -> real {'beats' if beats else 'does NOT beat'} chance | "
        f"thickness: {th['mult_full_18bps']:+.2f}x full round-trip cost | NOTE: conflicts with "
        f"round 78's sealed-tested EIA-reversal FAIL on the same underlying event — see "
        f"step111_results.md for the flagged discrepancy; not eligible for a sealed look until "
        f"reconciled")
    append_family_line(
        "- **12. OPEC meeting reactions** — NOT TESTED (no reliable local OPEC/OPEC+ meeting "
        "calendar available in this repo or session; fabricating dates from memory risks a "
        "wrong calendar masquerading as a real one — flagged as an open data gap rather than "
        "guessed)")
    append_family_line(
        "- **13. Contango/backwardation front-month roll effect** — NOT TESTABLE with available "
        "data (only a single front-month CL=F/BZ=F series is cached — no second contract month "
        "or futures curve data exists in this repo to compute an actual term-structure signal; "
        "stated honestly per the round's own instruction rather than faked)")

    pd.DataFrame(tr + va).to_csv("step114_table.csv", index=False)
    print("\nWrote step114_table.csv. Appended 3 lines to step110_family_map.md "
         "(1 tested + 2 honest not-testable entries).")


if __name__ == "__main__":
    main()
