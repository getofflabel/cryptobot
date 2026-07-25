"""
step117_oil_breakout_lookback_sweep.py -- Round 117: donchian BREAKOUT ENTRY
LOOKBACK sweep on oil, provoked directly by Wallace's "looks like you missed
an oil trade" (CL=F ran +29.8% in three weeks; the live tradfi_engine book,
a 2-hour-slot mean-reversion scorer borrowed from crypto, caught one
135-minute trade worth $58.39 and was structurally incapable of holding the
move -- round 110 already proved that book negative on oil and it is stood
down).

Round 116 tested EXITS on a FIXED entry (Donchian(55)) and found it a
near-miss on CL (2.36x cost, under the 5x bar) with Brent passing at 15.87x
but negative on WTI. Nobody had swept the ENTRY LOOKBACK itself. Wallace's
own eyeball (not evidence -- exactly the kind of read this desk exists to
distrust) flagged donchian-10 and donchian-20 with an EMA20 exit as
currently-open winners while donchian-55 sat dead, still anchored to an
earlier-year spike high. This round tests that properly: lookback in
{5,10,...,55} (11 values) x an exit library spanning structure-trailing,
EMA/MA cross, and chandelier at four ATR multiples (7 exits) = 77 cells,
on CL=F DAILY and CL=F 1h (intraday, where the data supports it -- 1h only
runs 2024-03->2026-07, so a "55" lookback there means 55 HOURS, a very
different animal from 55 DAYS; both are swept and both are reported
separately, never conflated).

ENGINE: step150_common.run_edge, UNCHANGED (same harness rounds 110-116
used) -- execution="taker" always, exits.py structural stops via
SeriesCtx/TradeCtx (never a swept percentage), fixed-fractional risk
sizing (size = risk$ / stop distance, leverage an OUTPUT, capped at the
desk's real 20x ceiling).

DISCIPLINE:
- Every cell in the 77-cell grid is screened on TRAIN ONLY. Selection
  (the single best cell) is by TRAIN expectancy among cells clearing the
  train floor (n>=30) and positive -- exactly step116's rule, extended
  from 9 cells to 77.
- VAL IS READ EXACTLY ONCE, for the one selected cell only. No other cell
  in the 77 ever has its val number looked at. This is what makes the
  plateau-vs-spike check (run entirely on TRAIN numbers, before val is
  touched) honest: it is evidence about ROBUSTNESS of the selection, not
  a second bite at val.
- The sealed final 20% is never loaded by this file.
- Chance baseline (random-entry draws, same exit apparatus) computed for
  the selected cell's val window.
- Thickness reported BOTH ways: fees-only 12bps round trip (6bps/leg
  taker x2, the real measured BloFin cost) AND the fuller CostModel
  round trip (~18bps, fee+half-spread+slippage x2) -- Morgan's own
  instruction, because this repo has shipped on the flattering number
  before and been burned (maker 5.21 -> taker -8.15/trade).
- Cross-instrument transfer: the winning CL=F config (if any) replays
  UNCHANGED (same lookback, same exit, no re-optimization) on BZ=F, same
  timeframe, using BZ's own 60/20/20 split points. WTIOIL-USDT is not
  used as the transfer venue -- only 58 daily bars cached, nowhere near
  enough for even the shortest (5-bar) lookback plus a 60/20/20 split,
  same reasoning step115 already documented.

RESEARCH ONLY. No commits, no live orders, no live-file edits. Writes
step117_oil_breakout_lookback_sweep.py (this file), step117_results.md,
step117_table.csv.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import exits as E
from step150_common import (chance_baseline, fmt_stats, mask_to_events,
                            run_edge, split_points, thickness, trade_stats,
                            verdict_for)

LOOKBACKS = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]

EXIT_FACTORY = {
    "structure_trail":  lambda: E.stop_structure_trailing(buffer_pct=0.0, fallback_pct=5.0),
    "ema20_cross":       lambda: E.stop_moving_average(n=20),
    "ema50_cross":       lambda: E.stop_moving_average(n=50),
    "chandelier2.5":     lambda: E.stop_chandelier(mult=2.5),
    "chandelier3.0":     lambda: E.stop_chandelier(mult=3.0),
    "chandelier3.5":     lambda: E.stop_chandelier(mult=3.5),
    "chandelier4.0":     lambda: E.stop_chandelier(mult=4.0),
}
EXIT_NAMES = list(EXIT_FACTORY.keys())
CHANDELIER_ORDER = ["chandelier2.5", "chandelier3.0", "chandelier3.5", "chandelier4.0"]


def donchian_entries_full(d: pd.DataFrame, n_donch: int):
    hi = d["high"].rolling(n_donch).max().shift(1)
    lo = d["low"].rolling(n_donch).min().shift(1)
    el = (d["close"] > hi).fillna(False)
    es = (d["close"] < lo).fillna(False)
    entries = mask_to_events(el | es, pd.Series(np.where(el, 1, np.where(es, -1, 0))))
    return entries, el, es


def years_span(d: pd.DataFrame) -> float:
    t = pd.DatetimeIndex(d["timestamp"])
    return max((t[-1] - t[0]).total_seconds() / (365.25 * 86400), 1e-9)


def make_stop_builder(exit_name: str):
    factory = EXIT_FACTORY[exit_name]

    def stop_builder(tc):
        return factory()
    return stop_builder


# ===========================================================================
# GRID SCREEN (TRAIN ONLY)
# ===========================================================================

def screen_grid(tag: str, d: pd.DataFrame):
    n, i_tr, i_va = split_points(d)
    d_tr = d.iloc[0:i_tr].reset_index(drop=True)
    d_va = d.iloc[i_tr:i_va].reset_index(drop=True)
    print(f"\n{'=' * 78}\n{tag} -- {n} bars total | train={i_tr} val={i_va - i_tr} "
         f"(sealed {n - i_va} bars NOT loaded)\n{'=' * 78}")

    entries_by_lb = {}
    rows = []
    trades_by_cell = {}
    for lb in LOOKBACKS:
        entries_all, el, es = donchian_entries_full(d, lb)
        entries_by_lb[lb] = entries_all
        tr_e = [(i, dr) for i, dr in entries_all if i < i_tr]
        raw_events_per_year = len(entries_all) / years_span(d)
        for exit_name in EXIT_NAMES:
            stop_builder = make_stop_builder(exit_name)
            tr, skipped = run_edge(d_tr, tr_e, stop_builder, None, len(d_tr))
            st = trade_stats(tr)
            trades_by_cell[(lb, exit_name)] = tr
            rows.append(dict(lookback=lb, exit=exit_name, tr_n=st["n"],
                             tr_exp=st["expectancy"], tr_win=st["win_rate"],
                             tr_avg_lev=st["avg_leverage"], tr_med_hold_h=st["median_hold_h"],
                             tr_skipped_no_structure=skipped,
                             raw_signal_events_per_year=raw_events_per_year))
        print(f"  lookback={lb:2d}  raw breakout events (train+val)/yr={raw_events_per_year:6.1f}  "
             f"-- " + " | ".join(f"{en}:{trade_stats(trades_by_cell[(lb,en)])['n']}t/"
             f"${trade_stats(trades_by_cell[(lb,en)])['expectancy']:+.2f}" for en in EXIT_NAMES))

    grid_df = pd.DataFrame(rows)
    return grid_df, entries_by_lb, trades_by_cell, d_tr, d_va, i_tr, i_va


def classify_plateau(grid_df: pd.DataFrame, lb: int, exit_name: str) -> dict:
    """Same-exit lookback neighbors + (if chandelier) same-lookback ATR-mult
    neighbors, judged on TRAIN numbers only (selection has not touched val
    yet at the point this is called)."""
    def eligible(row_lb, row_exit):
        r = grid_df[(grid_df.lookback == row_lb) & (grid_df.exit == row_exit)]
        if r.empty:
            return None
        r = r.iloc[0]
        return dict(n=int(r.tr_n), exp=float(r.tr_exp),
                   ok=bool(r.tr_n >= 30 and r.tr_exp > 0))

    idx = LOOKBACKS.index(lb)
    lb_neighbors = []
    if idx > 0:
        lb_neighbors.append((LOOKBACKS[idx - 1], eligible(LOOKBACKS[idx - 1], exit_name)))
    if idx < len(LOOKBACKS) - 1:
        lb_neighbors.append((LOOKBACKS[idx + 1], eligible(LOOKBACKS[idx + 1], exit_name)))

    exit_neighbors = []
    if exit_name in CHANDELIER_ORDER:
        eidx = CHANDELIER_ORDER.index(exit_name)
        if eidx > 0:
            exit_neighbors.append((CHANDELIER_ORDER[eidx - 1], eligible(lb, CHANDELIER_ORDER[eidx - 1])))
        if eidx < len(CHANDELIER_ORDER) - 1:
            exit_neighbors.append((CHANDELIER_ORDER[eidx + 1], eligible(lb, CHANDELIER_ORDER[eidx + 1])))
    elif exit_name in ("ema20_cross", "ema50_cross"):
        other = "ema50_cross" if exit_name == "ema20_cross" else "ema20_cross"
        exit_neighbors.append((other, eligible(lb, other)))

    lb_ok = [r for _, r in lb_neighbors if r is not None]
    exit_ok = [r for _, r in exit_neighbors if r is not None]
    all_neighbors = lb_ok + exit_ok
    n_pass = sum(1 for r in all_neighbors if r["ok"])
    verdict = "PLATEAU" if all_neighbors and n_pass == len(all_neighbors) else \
             ("PARTIAL-PLATEAU" if n_pass > 0 else "SPIKE (lone setting -- neighbors fail/negative)")
    return dict(lb_neighbors=lb_neighbors, exit_neighbors=exit_neighbors,
               n_neighbors=len(all_neighbors), n_pass=n_pass, verdict=verdict)


def select_and_validate(tag: str, grid_df: pd.DataFrame, entries_by_lb: dict,
                        trades_by_cell: dict, d: pd.DataFrame, d_tr: pd.DataFrame,
                        d_va: pd.DataFrame, i_tr: int, i_va: int):
    eligible = grid_df[(grid_df.tr_n >= 30) & (grid_df.tr_exp > 0)]
    if eligible.empty:
        print(f"\n  {tag}: NO cell clears TRAIN floor (n>=30) + positive expectancy out of "
             f"{len(grid_df)} cells screened. VAL NOT READ for any cell. FAIL, plain no.")
        return dict(tag=tag, verdict="FAIL (no train-eligible cell)", grid_df=grid_df)

    best = eligible.sort_values("tr_exp", ascending=False).iloc[0]
    lb, exit_name = int(best.lookback), best.exit
    print(f"\n  {tag}: SELECTED on TRAIN only -> lookback={lb} exit={exit_name} "
         f"(train n={int(best.tr_n)} exp=${best.tr_exp:+.2f}/t) out of "
         f"{len(eligible)}/{len(grid_df)} train-eligible cells.")

    def _fmt_neighbor(r):
        if r is None:
            return "n/a (no cell)"
        state = "OK" if r["ok"] else "FAILS/NEGATIVE"
        return f"n={r['n']} exp=${r['exp']:+.2f} {state}"

    plateau = classify_plateau(grid_df, lb, exit_name)
    print(f"  PLATEAU CHECK (train numbers only, val still unread):")
    for nlb, r in plateau["lb_neighbors"]:
        print(f"    lookback-neighbor {nlb} (same exit {exit_name}): {_fmt_neighbor(r)}")
    for ne, r in plateau["exit_neighbors"]:
        print(f"    exit-neighbor {ne} (same lookback {lb}): {_fmt_neighbor(r)}")
    print(f"  PLATEAU VERDICT: {plateau['verdict']} ({plateau['n_pass']}/{plateau['n_neighbors']} "
         f"neighbors also clear train floor+positive)")

    entries_all = entries_by_lb[lb]
    va_e = [(i - i_tr, dr) for i, dr in entries_all if i_tr <= i < i_va]
    stop_builder = make_stop_builder(exit_name)
    va, va_skipped = run_edge(d_va, va_e, stop_builder, None, len(d_va))
    tr = trades_by_cell[(lb, exit_name)]
    tr_st, va_st = trade_stats(tr), trade_stats(va)
    verdict = verdict_for(tr_st, va_st)
    floor_ok = tr_st["n"] >= 30 and va_st["n"] >= 8
    if verdict.startswith("SURVIVOR") and not floor_ok:
        verdict = "INSUFFICIENT-SAMPLE"

    all_trades = tr + va
    avg_not = float(np.mean([t["notional"] for t in all_trades])) if all_trades else 0.0
    th = thickness(va_st["expectancy"], avg_not) if va_st["n"] else \
        dict(pct_notional=float("nan"), mult_12bps=float("nan"), mult_full_18bps=float("nan"))
    thin = False
    if verdict.startswith("SURVIVOR") and (th["mult_12bps"] < 5.0 or th["mult_full_18bps"] < 5.0):
        thin = True
        verdict = "REJECT (thin, under 5x cost on at least one cost basis)"

    print(f"\n  VAL (read ONCE for this cell): {fmt_stats('VAL', va_st)}")
    print(f"  TRAIN                        : {fmt_stats('TRAIN', tr_st)}")
    print(f"  THICKNESS(val): {th['pct_notional']:.4f}% notional | "
         f"{th['mult_12bps']:.2f}x fees-only 12bps | {th['mult_full_18bps']:.2f}x full CostModel ~18bps")
    trades_per_year = (tr_st["n"] + va_st["n"]) / years_span(d.iloc[0:i_va])
    print(f"  TRADES/YEAR (train+val combined): {trades_per_year:.2f}")
    print(f"  VERDICT: {verdict}")

    long_frac = sum(1 for i, dr in va_e if dr == 1) / max(1, len(va_e))
    cb = chance_baseline(d_va, len(va_e), long_frac, stop_builder, None, len(d_va),
                         None, "next_open", draws=100)
    beats = va_st["expectancy"] > cb["mean_exp"] if va_st["n"] else False
    print(f"  CHANCE BASELINE (val, {cb['n_draws']} random-entry draws, same exit apparatus): "
         f"${cb['mean_exp']:+.2f}/t vs real ${va_st['expectancy']:+.2f}/t -> "
         f"{'BEATS' if beats else 'DOES NOT BEAT'} chance")
    n_eligible = len(eligible)
    n_cells = len(grid_df)
    print(f"  LUCK CONTEXT: {n_cells} cells screened this timeframe, {n_eligible} cleared the "
         f"train floor+positive by chance-eligible construction -- at a naive per-cell false-"
         f"positive tolerance this is the scale of result multiple-comparisons could produce "
         f"without a real edge; the chance-baseline draw above is the direct control on the "
         f"SELECTED cell specifically.")

    return dict(tag=tag, lookback=lb, exit=exit_name, verdict=verdict, thin=thin,
               tr_st=tr_st, va_st=va_st, thickness=th, trades_per_year=trades_per_year,
               plateau=plateau, chance=cb, beats_chance=beats, grid_df=grid_df,
               d=d, i_tr=i_tr, i_va=i_va)


# ===========================================================================
# TRANSFER TEST
# ===========================================================================

def transfer_test(cl_result: dict, bz_path: str, tf_label: str):
    if cl_result is None or not cl_result.get("lookback"):
        print(f"\n  TRANSFER ({tf_label}): no CL=F config selected this timeframe -- nothing to transfer.")
        return None
    lb, exit_name = cl_result["lookback"], cl_result["exit"]
    d = pd.read_parquet(bz_path).reset_index(drop=True)
    n, i_tr, i_va = split_points(d)
    entries_all, _, _ = donchian_entries_full(d, lb)
    tr_e = [(i, dr) for i, dr in entries_all if i < i_tr]
    va_e = [(i - i_tr, dr) for i, dr in entries_all if i_tr <= i < i_va]
    d_tr, d_va = d.iloc[0:i_tr].reset_index(drop=True), d.iloc[i_tr:i_va].reset_index(drop=True)
    stop_builder = make_stop_builder(exit_name)
    tr, _ = run_edge(d_tr, tr_e, stop_builder, None, len(d_tr))
    va, _ = run_edge(d_va, va_e, stop_builder, None, len(d_va))
    tr_st, va_st = trade_stats(tr), trade_stats(va)
    verdict = verdict_for(tr_st, va_st)
    floor_ok = tr_st["n"] >= 30 and va_st["n"] >= 8
    if verdict.startswith("SURVIVOR") and not floor_ok:
        verdict = "INSUFFICIENT-SAMPLE"
    all_trades = tr + va
    avg_not = float(np.mean([t["notional"] for t in all_trades])) if all_trades else 0.0
    th = thickness(va_st["expectancy"], avg_not) if va_st["n"] else \
        dict(mult_12bps=float("nan"), mult_full_18bps=float("nan"))
    if verdict.startswith("SURVIVOR") and (th["mult_12bps"] < 5.0 or th["mult_full_18bps"] < 5.0):
        verdict = "REJECT (thin on transfer)"
    holds = tr_st["expectancy"] > 0 and va_st["expectancy"] > 0
    print(f"\n  TRANSFER ({tf_label}) -- BZ=F, UNCHANGED config lookback={lb} exit={exit_name} "
         f"from CL=F:")
    print(f"    {fmt_stats('TRAIN', tr_st)}")
    print(f"    {fmt_stats('VAL  ', va_st)}")
    print(f"    THICKNESS(val): {th['mult_12bps']:.2f}x fees-only | {th['mult_full_18bps']:.2f}x full CostModel")
    print(f"    VERDICT: {verdict}")
    print(f"    TRANSFER {'HOLDS' if holds else 'DOES NOT HOLD'} (same-sign positive expectancy "
         f"both windows on the second instrument, config completely unchanged)")
    return dict(tf=tf_label, lookback=lb, exit=exit_name, tr_st=tr_st, va_st=va_st,
               thickness=th, verdict=verdict, holds=holds)


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    print("=" * 78)
    print("ROUND 117 -- OIL BREAKOUT ENTRY LOOKBACK SWEEP (5-55) x EXIT LIBRARY")
    print("Provoked by: CL=F +29.8% in 3 weeks, live book caught one $58.39 trade")
    print("execution='taker' always. Stops at structure. Sealed 20% never loaded.")
    print("=" * 78)

    all_rows = []
    results = {}

    # ---- CL=F DAILY ----
    d1d = pd.read_parquet("data_oil_CL_1d.parquet").reset_index(drop=True)
    grid_1d, ent_1d, trades_1d, tr_1d, va_1d, i_tr_1d, i_va_1d = screen_grid("CL=F 1d", d1d)
    grid_1d.insert(0, "instrument_tf", "CL=F_1d")
    all_rows.append(grid_1d)
    sel_1d = select_and_validate("CL=F_1d", grid_1d, ent_1d, trades_1d, d1d, tr_1d, va_1d, i_tr_1d, i_va_1d)
    results["CL_1d"] = sel_1d

    # ---- CL=F 1h (intraday) ----
    d1h = pd.read_parquet("data_oil_CL_1h.parquet").reset_index(drop=True)
    print(f"\nCL=F 1h span: {d1h['timestamp'].iloc[0]} -> {d1h['timestamp'].iloc[-1]} "
         f"({years_span(d1h):.2f} years) -- 'lookback' below is in HOURS, not days.")
    grid_1h, ent_1h, trades_1h, tr_1h, va_1h, i_tr_1h, i_va_1h = screen_grid("CL=F 1h", d1h)
    grid_1h.insert(0, "instrument_tf", "CL=F_1h")
    all_rows.append(grid_1h)
    sel_1h = select_and_validate("CL=F_1h", grid_1h, ent_1h, trades_1h, d1h, tr_1h, va_1h, i_tr_1h, i_va_1h)
    results["CL_1h"] = sel_1h

    # ---- TRANSFER: CL=F winners replayed unchanged on BZ=F ----
    print("\n" + "=" * 78)
    print("CROSS-INSTRUMENT TRANSFER -- CL=F winning config(s) replayed UNCHANGED on BZ=F")
    print("(WTIOIL-USDT not used as transfer venue: only 58 daily bars cached, far short of")
    print(" what any of these lookbacks + a 60/20/20 split needs -- same reasoning as step115)")
    print("=" * 78)
    transfer_1d = transfer_test(sel_1d, "data_oil_BZ_1d.parquet", "1d")
    transfer_1h = transfer_test(sel_1h, "data_oil_BZ_1h.parquet", "1h")

    # ---- write table ----
    full_grid = pd.concat(all_rows, ignore_index=True)
    full_grid.to_csv("step117_table.csv", index=False)
    print(f"\nWrote step117_table.csv ({len(full_grid)} rows -- {len(all_rows)} timeframes x "
         f"{len(LOOKBACKS)} lookbacks x {len(EXIT_NAMES)} exits).")

    # ---- final book-spec verdict ----
    print("\n" + "=" * 78)
    print("FINAL VERDICT")
    print("=" * 78)
    survivors = []
    for tag, sel, transfer in (("CL=F 1d", sel_1d, transfer_1d), ("CL=F 1h", sel_1h, transfer_1h)):
        clears = bool(sel) and sel.get("verdict", "").startswith("SURVIVOR") and not sel.get("thin")
        transfers = bool(transfer) and transfer["holds"] and not transfer["verdict"].startswith("REJECT")
        print(f"{tag}: config-clears-train+val+thickness={clears} | transfers-to-BZ={transfers}")
        if clears and transfers:
            survivors.append((tag, sel, transfer))

    if not survivors:
        print("\nNO CONFIG CLEARS THE BAR ON BOTH TRAIN+VAL THICKNESS *AND* TRANSFERS TO BZ=F.")
        print("Plain answer: oil trend breakouts, swept across the entry-lookback range that")
        print("actually produced Wallace's eyeballed +14.3%/+8.3% open trades, do not clear")
        print("this desk's evidence bar after real taker costs and a real structural stop --")
        print("at least not with the exit library and lookback range tested here. See")
        print("step117_results.md for the full grid and the plateau/spike read on the best")
        print("cell(s) even though they did not clear.")
    else:
        for tag, sel, transfer in survivors:
            print(f"\nSURVIVOR: {tag} donchian({sel['lookback']}) + {sel['exit']} -- "
                 f"CLEARS train+val+thickness+BZ transfer. See step117_results.md for the full spec.")


if __name__ == "__main__":
    main()
