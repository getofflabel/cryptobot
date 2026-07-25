"""
step310_common.py — ROUND 310: "did it die, or did we mis-measure it?"

Morgan's mandate, 2026-07-25. Round 150 killed four of Bitcoin's five
documented edges under market-order costs and real chart-structure stops.
Round 86 is the cautionary template: our "regular divergence is noise"
verdict had measured a version of the method with NO confirmation close,
and the confirmation close is the one condition practitioners describe as
mandatory. Adding it turned a dead family into a survivor. The test had
measured a different strategy than the one people actually trade.

So for each dead edge this round asks ONE question: what condition do the
people who actually trade this method require, that our step150 script did
not implement? Add exactly that one condition. Re-run. Report dead-for-real
or dead-because-we-mis-measured-it.

REUSED, NOT REWRITTEN
The whole scoring apparatus is step150_common.run_edge / trade_stats /
thickness / chance_baseline / verdict_for, imported verbatim. That is
deliberate: if the engine changed at the same time as the entry condition,
no difference could be attributed to the entry condition. Market orders
always (execution="taker" via CostModel's default), stops at real chart
structure via exits.py, position size = dollars risked / stop distance,
leverage an output capped at the desk's 20x ceiling, 60/20/20 in date
order, the final untouched slice of history NEVER loaded.

FLOORS (unchanged from every other round in this repo)
>= 30 trades in the first slice, >= 8 in the middle slice, positive average
profit per trade in BOTH slices. Anything under the trade floors is
reported as NOT ENOUGH TRADES, never as a number.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from step150_common import (MIN_TRAIN_TRADES, MIN_VAL_TRADES, chance_baseline,
                            fmt_stats, run_edge, thickness, trade_stats)

ROWS: list[dict] = []


def wait_for_close_through(event_mask: pd.Series, level_arr, close_arr,
                           side: str, max_wait: int):
    """THE ROUND-86 SHAPE, generalised. Shift entry off the signal bar onto
    the first LATER bar that closes back through a named price level,
    within max_wait bars. Returns (trigger_mask, {trigger_idx: origin_idx}).

    side="long": trigger when close > level. side="short": close < level.
    Strictly forward-looking from the signal bar (range starts at j+1), so
    a trigger can never be the signal bar itself — that is the entire point
    of the gate and the documented number-one failure mode when skipped.
    """
    n = len(close_arr)
    idxs = np.flatnonzero(event_mask.fillna(False).to_numpy())
    lv = np.asarray(level_arr, dtype=float)
    out = np.zeros(n, dtype=bool)
    origin_of: dict[int, int] = {}
    for j in idxs:
        level = lv[j]
        if not (level == level):
            continue
        end = min(n, j + 1 + max_wait)
        for t in range(j + 1, end):
            c = close_arr[t]
            if (c > level) if side == "long" else (c < level):
                out[t] = True
                origin_of[t] = int(j)
                break
    return pd.Series(out, index=range(n)), origin_of


def wait_for_touch_then_close_back(event_mask: pd.Series, level_arr,
                                   high_arr, low_arr, close_arr,
                                   side: str, max_wait: int):
    """THE BREAK-AND-RETEST SHAPE. After a structure break at bar j, wait
    for price to trade back TO the broken level (the retest) and then close
    back on the breakout side of it (the retest holding). Entry is that
    bar. Returns (trigger_mask, {trigger_idx: origin_idx}).

    side="long": the level was broken upward, so the retest is a bar whose
    LOW reaches down to or below the level while its CLOSE finishes above
    it. side="short" mirrors that.
    """
    n = len(close_arr)
    idxs = np.flatnonzero(event_mask.fillna(False).to_numpy())
    lv = np.asarray(level_arr, dtype=float)
    out = np.zeros(n, dtype=bool)
    origin_of: dict[int, int] = {}
    for j in idxs:
        level = lv[j]
        if not (level == level):
            continue
        end = min(n, j + 1 + max_wait)
        for t in range(j + 1, end):
            if side == "long":
                touched = low_arr[t] <= level
                held = close_arr[t] > level
            else:
                touched = high_arr[t] >= level
                held = close_arr[t] < level
            if touched and held:
                out[t] = True
                origin_of[t] = int(j)
                break
            # if price closes decisively back through the level the wrong
            # way, the break failed and this setup is void — stop waiting.
            failed = (close_arr[t] < level) if side == "long" else (close_arr[t] > level)
            if failed and t > j + 1:
                break
    return pd.Series(out, index=range(n)), origin_of


def score_cell(label: str, edge: str, candles: pd.DataFrame, i_tr: int, i_va: int,
               entries_all: list[tuple[int, int]], stop_builder, target_builder,
               max_hold_bars: int, funding: pd.Series, long_frac: float,
               k: int = 5, fill_convention: str = "next_open",
               chance_draws: int = 60, verbose: bool = True) -> dict:
    """Run one configuration on the first 60% and the middle 20%, in date
    order, each as an independently sliced and index-reset frame (a pivot
    near the boundary must never see data from the other side). Returns one
    result row and appends it to ROWS."""
    def slice_entries(lo, hi):
        return [(i - lo, dr) for i, dr in entries_all if lo <= i < hi]

    tr_c = candles.iloc[0:i_tr].reset_index(drop=True)
    va_c = candles.iloc[i_tr:i_va].reset_index(drop=True)
    tr_f = funding.iloc[0:i_tr].reset_index(drop=True) if funding is not None else None
    va_f = funding.iloc[i_tr:i_va].reset_index(drop=True) if funding is not None else None
    tr_e, va_e = slice_entries(0, i_tr), slice_entries(i_tr, i_va)

    tr_t, tr_skip = run_edge(tr_c, tr_e, stop_builder, target_builder, max_hold_bars,
                             funding_bps=tr_f, fill_convention=fill_convention, k=k)
    va_t, va_skip = run_edge(va_c, va_e, stop_builder, target_builder, max_hold_bars,
                             funding_bps=va_f, fill_convention=fill_convention, k=k)
    tr_s, va_s = trade_stats(tr_t), trade_stats(va_t)

    enough = tr_s["n"] >= MIN_TRAIN_TRADES and va_s["n"] >= MIN_VAL_TRADES
    both_pos = tr_s["expectancy"] > 0 and va_s["expectancy"] > 0
    if not enough:
        verdict = "NOT ENOUGH TRADES"
    elif both_pos:
        verdict = "SURVIVOR (first 60% + middle 20%; final slice untouched)"
    else:
        verdict = "FAIL"

    all_t = tr_t + va_t
    avg_notional = float(np.mean([t["notional"] for t in all_t])) if all_t else 0.0
    th = thickness(va_s["expectancy"], avg_notional)

    cb = dict(mean_exp=float("nan"), n_draws=0, sample_events=len(va_e))
    if enough and both_pos:
        cb = chance_baseline(va_c, len(va_e), long_frac, stop_builder, target_builder,
                             max_hold_bars, va_f, fill_convention, k=k, draws=chance_draws)

    row = dict(edge=edge, cell=label,
               train_n=tr_s["n"], train_exp=tr_s["expectancy"], train_win=tr_s["win_rate"],
               val_n=va_s["n"], val_exp=va_s["expectancy"], val_win=va_s["win_rate"],
               val_pct_of_position=th["pct_notional"],
               val_x_cost_12bps=th["mult_12bps"], val_x_cost_full=th["mult_full_18bps"],
               random_entry_control=cb["mean_exp"], avg_notional=avg_notional,
               train_med_hold_h=tr_s["median_hold_h"], val_med_hold_h=va_s["median_hold_h"],
               skipped_no_structure=tr_skip + va_skip, verdict=verdict)
    ROWS.append(row)

    if verbose:
        print(f"\n--- {label} ---")
        print(fmt_stats("  FIRST 60%", tr_s), f"| skipped(no structure)={tr_skip}")
        print(fmt_stats("  MIDDLE 20%", va_s), f"| skipped(no structure)={va_skip}")
        print(f"  VERDICT: {verdict}")
        if enough:
            print(f"  profit per trade as a share of the full position (middle 20%): "
                  f"{th['pct_notional']:.4f}% | "
                  f"{th['mult_12bps']:.2f}x the market-order round-trip cost of 0.12% | "
                  f"{th['mult_full_18bps']:.2f}x the fuller round-trip cost")
        if cb["n_draws"]:
            print(f"  entering at random times instead, same number of trades, same "
                  f"stop/target/cost apparatus ({cb['n_draws']} draws): "
                  f"${cb['mean_exp']:+,.2f} per trade")
    return row


def write_table(path: str):
    df = pd.DataFrame(ROWS)
    df.to_csv(path, index=False)
    print(f"\nwrote {path} ({len(df)} rows)")
    return df
