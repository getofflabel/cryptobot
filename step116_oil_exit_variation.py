"""
step116_oil_exit_variation.py — Round 116: EXIT VARIATION on the one real
lead the family map produced — Donchian(55) breakout on oil DAILY, which
cleared both train+val with real sample size on BOTH CL=F and BZ=F but
sat under the house 5x-thickness bar using gold_book.py's unmodified
trail-only exit (family 5-1d-55 / family 14). Does a DIFFERENT stop/
target pairing from exits.py's composable library clear 5x where the
gold-shape exit didn't?

METHOD: same Donchian(55) entry signal (unchanged — this round is about
exits, not entries), same 60/20/20 split, SAME engine
(step150_common.run_edge). A small, stated grid of exits.py stop x
target pairs (not the full 10x7 — a representative subset spanning the
library's actual shapes): trail-only (the baseline already tested),
chandelier at two multiples, ATR-fixed, Bollinger-band. Each paired with
either no target (trail rides) or a fixed-R target at two multiples.
SELECTION IS TRAIN-ONLY (the best-by-train-expectancy config among those
clearing the train floor and positive), VAL IS READ EXACTLY ONCE for
that one selected config — never grid-searched on val, matching the
house discipline stated in every other round tonight. Sealed 20% is
never touched (this is a train+val screening round, same as every other
step11x tonight; a genuine SURVIVOR here would still need a dedicated
sealed look, Morgan's call).

RESEARCH ONLY. No commits, no live orders. Writes
step116_oil_exit_variation.py (this file), step116_results.md,
step116_table.csv, and appends to step110_family_map.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import exits as E
from step150_common import (chance_baseline, mask_to_events, run_edge,
                            split_points, thickness, trade_stats,
                            verdict_for)

FAMILY_MAP_PATH = "step110_family_map.md"


def append_family_line(line: str):
    with open(FAMILY_MAP_PATH, "a") as fh:
        fh.write(line.rstrip("\n") + "\n")


def donchian_entries(d, n_donch=55):
    hi = d["high"].rolling(n_donch).max().shift(1)
    lo = d["low"].rolling(n_donch).min().shift(1)
    el = (d["close"] > hi).fillna(False)
    es = (d["close"] < lo).fillna(False)
    return mask_to_events(el | es, pd.Series(np.where(el, 1, np.where(es, -1, 0))))


GRID = [
    ("trail_only(structure_trail)", lambda tc: E.stop_structure_trailing(buffer_pct=0.0, fallback_pct=5.0), None),
    ("chandelier2.5_trail", lambda tc: E.stop_chandelier(mult=2.5), None),
    ("chandelier3.5_trail", lambda tc: E.stop_chandelier(mult=3.5), None),
    ("chandelier2.5_r3", lambda tc: E.stop_chandelier(mult=2.5),
     lambda stop: E.target_fixed_r(stop, r_multiple=3.0)),
    ("atr2.0_r3", lambda tc: E.stop_atr(mult=2.0), lambda stop: E.target_fixed_r(stop, r_multiple=3.0)),
    ("atr2.0_r4", lambda tc: E.stop_atr(mult=2.0), lambda stop: E.target_fixed_r(stop, r_multiple=4.0)),
    ("bollinger_opp_trail", lambda tc: E.stop_bollinger(use="opposite_band"), None),
    ("structure_trail_r3", lambda tc: E.stop_structure_trailing(buffer_pct=0.0, fallback_pct=5.0),
     lambda stop: E.target_fixed_r(stop, r_multiple=3.0)),
    ("structure_trail_measmove", lambda tc: E.stop_structure_trailing(buffer_pct=0.0, fallback_pct=5.0),
     lambda stop: E.target_measured_move(extension=1.618)),
]


def run_one(tag, d, entries_all, i_tr, i_va, stop_fn, target_fn):
    max_hold_bars = len(d)
    tr_e = [(i, dr) for i, dr in entries_all if i < i_tr]
    va_e = [(i - i_tr, dr) for i, dr in entries_all if i_tr <= i < i_va]
    tr_c, va_c = d.iloc[0:i_tr].reset_index(drop=True), d.iloc[i_tr:i_va].reset_index(drop=True)
    tr, _ = run_edge(tr_c, tr_e, stop_fn, target_fn, max_hold_bars)
    va, _ = run_edge(va_c, va_e, stop_fn, target_fn, max_hold_bars)
    return tr, va, tr_e, va_e, tr_c, va_c


def screen_instrument(tag, path, n_donch=55):
    print(f"\n{'=' * 78}\n{tag} — Donchian({n_donch}) exit-variation screen\n{'=' * 78}")
    d = pd.read_parquet(path).reset_index(drop=True)
    n, i_tr, i_va = split_points(d)
    entries_all = donchian_entries(d, n_donch)
    print(f"{len(d)} daily bars | {len(entries_all)} total entries")

    rows = []
    for name, stop_fn, target_fn in GRID:
        tr, va, tr_e, va_e, tr_c, va_c = run_one(name, d, entries_all, i_tr, i_va, stop_fn, target_fn)
        tr_st, va_st = trade_stats(tr), trade_stats(va)
        rows.append(dict(config=name, tr_n=tr_st["n"], tr_exp=tr_st["expectancy"],
                         va_n=va_st["n"], va_exp=va_st["expectancy"],
                         tr_st=tr_st, va_st=va_st, tr_e=tr_e, va_e=va_e,
                         tr_c=tr_c, va_c=va_c, stop_fn=stop_fn, target_fn=target_fn))
        print(f"  {name:28s} TRAIN n={tr_st['n']:3d} exp=${tr_st['expectancy']:+8.2f} | "
             f"(val not read yet)")

    # SELECTION: TRAIN-ONLY, among configs clearing the train floor (n>=30) and positive
    eligible = [r for r in rows if r["tr_n"] >= 30 and r["tr_exp"] > 0]
    if not eligible:
        print("\n  No config clears TRAIN floor+positive -> INSUFFICIENT SAMPLE / FAIL, "
             "val not read for any config.")
        append_family_line(
            f"- **15-{tag}. Exit-variation screen — Donchian({n_donch})** — FAIL "
            f"(no exit pairing cleared TRAIN floor+positive expectancy; val never read "
            f"for any config, selection discipline preserved)")
        return None
    best = max(eligible, key=lambda r: r["tr_exp"])
    print(f"\n  SELECTED on TRAIN only: {best['config']} (train n={best['tr_n']} "
         f"exp=${best['tr_exp']:+.2f}) -> reading VAL once now.")

    va_st = best["va_st"]
    tr_st = best["tr_st"]
    verdict = verdict_for(tr_st, va_st)
    floor_ok = tr_st["n"] >= 30 and va_st["n"] >= 8
    if verdict.startswith("SURVIVOR") and not floor_ok:
        verdict = "INSUFFICIENT-SAMPLE"

    all_trades_sel = None
    tr_trades, va_trades, _, _, _, _ = run_one(best["config"], d, entries_all, i_tr, i_va,
                                               best["stop_fn"], best["target_fn"])
    all_trades_sel = tr_trades + va_trades
    avg_not = float(np.mean([t["notional"] for t in all_trades_sel])) if all_trades_sel else 0.0
    th = thickness(va_st["expectancy"], avg_not) if va_st["n"] else dict(mult_full_18bps=float("nan"))
    if verdict.startswith("SURVIVOR") and th["mult_full_18bps"] < 5.0:
        verdict = "REJECT (thin, under 5x cost)"

    print(f"  VAL (read once): n={va_st['n']} exp=${va_st['expectancy']:+.2f}")
    print(f"  THICKNESS(val): {th['mult_full_18bps']:.2f}x full round-trip cost")
    print(f"  VERDICT: {verdict}")

    long_frac = sum(1 for i, dr in best["va_e"] if dr == 1) / max(1, len(best["va_e"]))
    cb = chance_baseline(best["va_c"], len(best["va_e"]), long_frac, best["stop_fn"],
                         best["target_fn"], len(best["va_c"]), None, "next_open", draws=100)
    beats = va_st["expectancy"] > cb["mean_exp"] if va_st["n"] else False
    print(f"  CHANCE (val, {cb['n_draws']} draws): ${cb['mean_exp']:+.2f}/t vs real "
         f"${va_st['expectancy']:+.2f}/t -> {'BEATS' if beats else 'DOES NOT BEAT'} chance")

    append_family_line(
        f"- **15-{tag}. Exit-variation screen — Donchian({n_donch})** — {verdict} | "
        f"selected on TRAIN only: `{best['config']}` (train {tr_st['n']}t "
        f"${tr_st['expectancy']:+.2f}/t) | VAL READ ONCE: {va_st['n']}t "
        f"${va_st['expectancy']:+.2f}/t | chance baseline: random-entry mean "
        f"${cb['mean_exp']:+.2f}/t -> real {'beats' if beats else 'does NOT beat'} chance | "
        f"thickness: {th['mult_full_18bps']:+.2f}x full round-trip cost | baseline for "
        f"comparison (gold's unmodified trail-only exit): CL 2.36x / BZ 3.58x cost "
        f"(families 5-1d-55 and 14)")
    return dict(tag=tag, config=rows, selected=best["config"], verdict=verdict,
               va_exp=va_st["expectancy"], thickness=th["mult_full_18bps"])


def main():
    print("ROUND 116 — exit-variation screen on the Donchian(55) 1d near-miss")
    r_cl = screen_instrument("CL=F", "data_oil_CL_1d.parquet")
    r_bz = screen_instrument("BZ=F", "data_oil_BZ_1d.parquet")
    rows = [r for r in (r_cl, r_bz) if r]
    if rows:
        pd.DataFrame([{k: v for k, v in r.items() if k != "config"} for r in rows]
                    ).to_csv("step116_table.csv", index=False)
    print("\nWrote step116_table.csv (if any config screened). Appended lines to "
         f"{FAMILY_MAP_PATH}.")


if __name__ == "__main__":
    main()
