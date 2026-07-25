"""
step115_oil_bz_transfer.py — Round 115: cross-instrument transfer check on
the one near-miss from the family map (Donchian(55) + structure-trail,
1d) — CL=F's config replayed UNCHANGED on BZ=F (Brent), the second
instrument round 78 already established as oil's natural transfer pair
("gold's donchian+structure-trail is directionally real on oil DAILY
(transfers CL<->BZ)"). Not technically mandatory (the config was a
REJECT for thin edge, not a SURVIVOR — the protocol only REQUIRES a
transfer test for survivors), but cheap and directly informative: does
whatever daily structure produced CL's positive-but-thin edge show up on
Brent too, or was it CL-specific noise? WTIOIL-USDT is NOT used here
(58 daily bars total — nowhere near enough for a 20/55-bar Donchian
lookback plus a 60/20/20 split; stated honestly rather than run anyway).

RESEARCH ONLY. No commits, no live orders. Writes
step115_oil_bz_transfer.py (this file), appends to
step110_family_map.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import exits as E
from step150_common import (mask_to_events, run_edge, split_points,
                            thickness, trade_stats, verdict_for)

FAMILY_MAP_PATH = "step110_family_map.md"


def append_family_line(line: str):
    with open(FAMILY_MAP_PATH, "a") as fh:
        fh.write(line.rstrip("\n") + "\n")


def main():
    print("=" * 78)
    print("ROUND 115 — BZ=F transfer check: Donchian(55) + structure-trail, UNCHANGED config")
    print("=" * 78)
    d = pd.read_parquet("data_oil_BZ_1d.parquet").reset_index(drop=True)
    n, i_tr, i_va = split_points(d)
    n_donch = 55
    hi = d["high"].rolling(n_donch).max().shift(1)
    lo = d["low"].rolling(n_donch).min().shift(1)
    el = (d["close"] > hi).fillna(False)
    es = (d["close"] < lo).fillna(False)

    def stop_builder(tc):
        return E.stop_structure_trailing(buffer_pct=0.0, fallback_pct=5.0)

    max_hold_bars = n
    entries_all = mask_to_events(el | es, pd.Series(np.where(el, 1, np.where(es, -1, 0))))
    tr_e = [(i, dr) for i, dr in entries_all if i < i_tr]
    va_e = [(i - i_tr, dr) for i, dr in entries_all if i_tr <= i < i_va]
    tr_c, va_c = d.iloc[0:i_tr].reset_index(drop=True), d.iloc[i_tr:i_va].reset_index(drop=True)
    tr, _ = run_edge(tr_c, tr_e, stop_builder, None, max_hold_bars)
    va, _ = run_edge(va_c, va_e, stop_builder, None, max_hold_bars)
    tr_st, va_st = trade_stats(tr), trade_stats(va)
    verdict = verdict_for(tr_st, va_st)
    floor_ok = tr_st["n"] >= 30 and va_st["n"] >= 8
    if verdict.startswith("SURVIVOR") and not floor_ok:
        verdict = "INSUFFICIENT-SAMPLE"
    all_trades = tr + va
    avg_not = float(np.mean([t["notional"] for t in all_trades])) if all_trades else 0.0
    th = thickness(va_st["expectancy"], avg_not) if va_st["n"] else \
        dict(mult_full_18bps=float("nan"))
    if verdict.startswith("SURVIVOR") and th["mult_full_18bps"] < 5.0:
        verdict = "REJECT (thin, under 5x cost)"

    print(f"TRAIN: n={tr_st['n']} exp=${tr_st['expectancy']:+.2f}")
    print(f"VAL  : n={va_st['n']} exp=${va_st['expectancy']:+.2f}")
    print(f"THICKNESS(val): {th['mult_full_18bps']:.2f}x full round-trip cost")
    print(f"VERDICT: {verdict}")

    cl_note = "CL=F val: n=20, +$7.35/t, 2.36x cost (family 5-1d-55, this same map)"
    transfer_holds = (tr_st["expectancy"] > 0 and va_st["expectancy"] > 0)
    append_family_line(
        f"- **14. BZ=F transfer check — Donchian(55)+structure-trail, UNCHANGED config from "
        f"family 5-1d-55** — {verdict} | val {va_st['n']}t ${va_st['expectancy']:+.2f}/t "
        f"(train {tr_st['n']}t ${tr_st['expectancy']:+.2f}/t) | thickness: "
        f"{th['mult_full_18bps']:+.2f}x full round-trip cost | {cl_note} | transfer "
        f"{'HOLDS (same sign, same-shape edge on the second instrument)' if transfer_holds else 'DOES NOT HOLD (sign flips or goes to zero on Brent — CL-specific, not a real cross-instrument edge)'} "
        f"| WTIOIL-USDT not used (only 58 daily bars cached — far short of what a 55-bar "
        f"Donchian + 60/20/20 split needs)")


if __name__ == "__main__":
    main()
