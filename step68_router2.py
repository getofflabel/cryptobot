"""
step68_router2.py — round 68: ROUTER v2 — STRICT CONSTRUCTION.

Run:  python3 step68_router2.py

THE BRIEF: round 66 proved the scenario CELLS are real (48 HOT cells, real
train+val-confirmed structure per tool) but its router construction — "OR
together every cell a tool has ever cleared train-positive on" — failed
honestly: for 7/8 tools the union of eligible cells was so permissive it
covered almost every bar the tool would have traded unconditionally anyway
(T1/T4/T5/T7's routed trade counts were IDENTICAL to their unconditional
counts), and the resulting portfolio lost to a DUMB random-cell control.
This round builds and tests STRICTER constructions on the same 8 tools /
same scenario-cell data, asking: is there a selectivity rule that actually
concentrates a tool into its real edge, and does that concentration beat
both the always-on rack AND a matched dumb-selectivity control?

Research only — no live orders, no commits. Touches only this file,
step68_results.md. Train-side selection ONLY; evaluated on val; the sealed
final 20% is never touched (this round's plumbing, inherited unchanged from
step66, only ever slices [0:i_tr] train and [i_tr:i_va] val — the same
discipline, not re-stated per call).

======================================================================
REUSE, STATED PLAINLY
======================================================================
Everything about HOW a scenario is measured (the 5-axis classifier, the 73
scenario cells, the 8 tool reconstructions, the single-slot portfolio
merge, the dumb-cell-control mechanism, the marginal-axis-removal test) is
imported directly from step66_scenario_mind.py — a pure function/data
module, safe to import — rather than re-typed, per this round's own
instruction to reuse step66's classifier/tools/plumbing by import where
clean. This file only adds NEW selectivity/weighting logic on top of that
reused plumbing:
  - top-K-cells-only masks (R2a)
  - a coarser 2-axis (CROWD x VOL, 9-cell) scenario grid (R2b)
  - a stricter train-sample floor, n>=25 instead of n>=15 (R2c)
  - graded position sizing by cell rank instead of binary fire/no-fire (R2d)
  - a dumb-control generator matched to EACH construction's own selectivity
    (not just one generic dumb control reused everywhere)
  - a trades/day frequency readout (the owner's explicit ask this round)

======================================================================
THE FOUR CONSTRUCTIONS
======================================================================
R2a TOP-CELLS-ONLY (k=1,2,3): a tool fires only in its top-k train cells,
    ranked by train expectancy, among cells clearing train n>=15 & train
    exp>0 (the SAME eligibility floor as step66's router — the union is
    just capped at k cells instead of every eligible cell, however many
    that is). Mask = union of those <=k cells (a small, concentrated OR,
    not a full-eligible-set OR) — "intersection-style" in the sense that
    capping at the best few cells forces the fired region toward the
    tool's true edge zone instead of near-unconditional coverage.
R2b AXIS-REDUCED (CROWD x VOL, 9 cells): scenario cells rebuilt from
    scratch using ONLY the two axes step66 itself flagged as load-bearing
    at the router level (its own marginal-axis-value section: CROWD and
    VOL were the only two axes whose removal hurt the router; TREND/NEWS/
    SESSION did not). Coarser cells -> fatter per-cell samples -> a tool
    fires in whichever of its (up to) 9 CROWD x VOL cells clear train
    n>=15 & train exp>0 (union of those).
R2c SIGN-GATE (fattened-cell rule): identical mechanism to step66's own
    router (union of eligible cells over the SAME 73-cell grid) but with
    the train floor raised from n>=15 to n>=25 — every other rule held
    fixed, isolating the effect of the floor alone.
R2d WEIGHTED (graded sizing): same trade SET as step66's original router
    (union of all eligible cells, n>=15 & exp>0 — deliberately, so R2d
    isolates weighting from selectivity) but each trade's contribution to
    the compounding equity curve is scaled by a weight: 1.0 if its entry
    bar falls in the tool's single best (rank-1 by train expectancy)
    eligible cell, 0.5 if it falls in any OTHER eligible cell. Tests
    whether graded sizing recovers value from an otherwise-too-permissive
    union, without touching selectivity at all.

======================================================================
CONTROLS, MANDATORY, MATCHED PER CONSTRUCTION
======================================================================
  ALWAYS-ON RACK — every tool's unconditional VAL trades, no gate at all.
    Reused directly from step66 (identical mechanism, recomputed here for
    a self-contained script).
  R66 OR-UNION (continuity) — step66's own router, recomputed here
    (identical function calls, same data) as the failed baseline every
    new construction must beat.
  DUMB-CELL CONTROL, matched per construction — NOT one generic control:
    - R2a's dumb control draws min(k, |eligible|) RANDOM cells from the
      SAME 73-cell universe (matched count to whatever k actually applied
      to that tool, since a tool with <k eligible cells uses fewer).
    - R2b's dumb control draws a random-count-matched selection from the
      SAME 9-cell CROWD x VOL universe (not the 73-cell one).
    - R2c's dumb control draws a random-count-matched selection from the
      73-cell universe, matched to R2c's own (n>=25) eligible count.
    - R2d's dumb control keeps R2d's EXACT trade set (same cells fire)
      but swaps which cell earns the 1.0 weight: a random eligible cell
      instead of the true rank-1 cell (matched count: 1 cell at weight
      1.0, the rest at 0.5) — isolates whether RANK-based weighting beats
      RANDOM weighting on the identical trade set.

Fixed seeds per tool (seed = 2000 + tool_index, distinct from step66's own
1000+ range, so this round's randomness is independently reproducible and
never accidentally collides with step66's dumb-router draws).
"""

import numpy as np
import pandas as pd

from step43_daytrade import champ_aligned, day_trade_signal
from step56_smc_toolkit import bias_series_4h
from step66_scenario_mind import (
    INITIAL_EQUITY, MIN_TRAIN_TRADES, MIN_VAL_TRADES, TOOL_NAMES,
    _run, build_axes, build_cells, build_t1, build_t2, build_t3, build_t4,
    build_t5, build_t6, build_t7, build_t8, dumb_mask_for, eligible_cells,
    eval_tool_cells, load_data, merge_portfolio, portfolio_stats,
    trades_to_pct, union_mask, val_trades_for_mask,
)

pd.set_option("display.width", 240)
pd.set_option("display.max_columns", None)

SEED_BASE = 2000


# ===========================================================================
# GENERIC ELIGIBILITY / RANKING (parameterized floor, unlike step66's fixed
# module-global MIN_TRAIN_TRADES=15)
# ===========================================================================

def eligible_cells_n(cell_results, axes_of, min_n, exclude_axis=None):
    names = [name for name, r in cell_results.items()
             if r["tr_exp"] > 0 and r["tr_n"] >= min_n
             and (exclude_axis is None or exclude_axis not in axes_of.get(name, set()))]
    return names


def rank_by_train_exp(cell_results, names):
    """Deterministic ranking: train expectancy descending, name ascending
    as tie-break (reproducible, no hidden dict-order dependence)."""
    return sorted(names, key=lambda n: (-cell_results[n]["tr_exp"], n))


# ===========================================================================
# AXIS-REDUCED (CROWD x VOL, 9 cells) — R2b's own coarser scenario grid
# ===========================================================================

def build_cells_crowdvol(crowd, vol):
    cells, axes_of = {}, {}
    crowds = ("crowded-long", "crowded-short", "neutral")
    vols = ("quiet", "normal", "violent")
    for c in crowds:
        for v in vols:
            name = f"crowd={c}×vol={v}"
            cells[name] = ((crowd == c) & (vol == v)).reset_index(drop=True)
            axes_of[name] = {"crowd", "vol"}
    return cells, axes_of


def eval_tool_on_cells(spec, cells):
    """Same per-cell train/val evaluation loop as step66's eval_tool_cells,
    but against an ARBITRARY cell set (here: the 9-cell CROWD x VOL grid)
    instead of the tool's own baked-in 73-cell spec['cells']. Returns
    cell_results only (no baseline re-run — the UNCONDITIONAL baseline is
    identical to whatever step66 already computed for that tool, no need
    to recompute)."""
    from step66_scenario_mind import eval_cell
    d, f, i_tr, i_va = spec["d"], spec["f"], spec["i_tr"], spec["i_va"]
    el0, es0 = spec["enter_long"], spec["enter_short"]
    stop_pct, target_pct, mh_bars = spec["stop_pct"], spec["target_pct"], spec["mh_bars"]
    cell_results = {}
    for cname, cmask in cells.items():
        elc = el0 & cmask.reindex(d.index).fillna(False)
        esc = es0 & cmask.reindex(d.index).fillna(False)
        sig = day_trade_signal(d, elc, esc, mh_bars)
        cell_results[cname] = eval_cell(d, f, i_tr, i_va, sig, stop_pct, target_pct)
    return cell_results


# ===========================================================================
# WEIGHTED (R2d) MERGE PLUMBING
# ===========================================================================

def val_trades_weighted(spec, top_mask, other_mask):
    """Trade SET = union(top_mask, other_mask) — identical mechanism to
    step66's val_trades_for_mask. Each resulting trade is tagged with a
    weight (1.0 if its entry bar is in top_mask, else 0.5 if in
    other_mask) by mapping entry_time back to a bar index in the tool's
    OWN full frame (timestamps are unique per bar, exact lookup, no
    fuzzy matching needed)."""
    d, f, i_tr, i_va = spec["d"], spec["f"], spec["i_tr"], spec["i_va"]
    el0, es0 = spec["enter_long"], spec["enter_short"]
    full_mask = None
    if top_mask is not None:
        full_mask = top_mask.copy()
    if other_mask is not None:
        full_mask = other_mask.copy() if full_mask is None else (full_mask | other_mask)
    if full_mask is None:
        return []
    elc = el0 & full_mask.reindex(d.index).fillna(False)
    esc = es0 & full_mask.reindex(d.index).fillna(False)
    sig = day_trade_signal(d, elc, esc, spec["mh_bars"])
    va = _run(d, sig, f, i_tr, i_va, spec["stop_pct"], spec["target_pct"])

    tm = top_mask.reindex(d.index).fillna(False) if top_mask is not None else pd.Series(False, index=d.index)
    om = other_mask.reindex(d.index).fillna(False) if other_mask is not None else pd.Series(False, index=d.index)
    ts_to_idx = {ts: i for i, ts in zip(d.index, d["timestamp"])}

    out = []
    for t in va.trades:
        idx = ts_to_idx.get(t.entry_time)
        if idx is not None and bool(tm.iloc[idx]):
            w = 1.0
        elif idx is not None and bool(om.iloc[idx]):
            w = 0.5
        else:
            w = 0.0   # should not occur by construction; kept for safety
        notional = abs(t.units) * t.entry_price
        r = t.pnl / notional if notional else 0.0
        out.append((t.entry_time, t.exit_time, r, w))
    return out


def merge_portfolio_weighted(trade_lists):
    allc = []
    for lst in trade_lists:
        allc.extend(lst)
    allc.sort(key=lambda x: x[0])
    accepted = []
    busy_until = None
    for et, xt, r, w in allc:
        if busy_until is None or et >= busy_until:
            accepted.append((et, xt, r, w))
            busy_until = xt
    return accepted


def portfolio_stats_weighted(accepted, initial_equity=INITIAL_EQUITY):
    if not accepted:
        return dict(n=0, expectancy=0.0, total_return_pct=0.0, max_dd_pct=0.0)
    equity = initial_equity
    curve = [equity]
    pnls = []
    for et, xt, r, w in accepted:
        pnl = equity * r * w
        equity += pnl
        pnls.append(pnl)
        curve.append(equity)
    arr = np.array(pnls)
    curve_arr = np.array(curve)
    peaks = np.maximum.accumulate(curve_arr)
    dd = (curve_arr - peaks) / peaks
    return dict(n=len(accepted), expectancy=float(arr.mean()),
                total_return_pct=(equity / initial_equity - 1) * 100,
                max_dd_pct=float(dd.min() * 100))


# ===========================================================================
# CONSTRUCTION RUNNERS
# ===========================================================================

def run_topk_construction(specs, cell_results_by_tool, axes_of, k, seed_offset):
    """R2a: union of top-k eligible cells (train n>=15, exp>0), ranked by
    train expectancy. Dumb control: same-count random cells from the same
    73-cell universe."""
    per_tool = {}
    for i, spec in enumerate(specs):
        name = spec["name"]
        cr = cell_results_by_tool[name]
        elig = eligible_cells(cr, axes_of)          # n>=15, exp>0 (step66's own floor)
        ranked = rank_by_train_exp(cr, elig)
        chosen = ranked[:k]
        mask = union_mask(spec["cells"], chosen)
        trades = val_trades_for_mask(spec, mask)
        dmask, dnames = dumb_mask_for(spec["cells"], len(chosen), seed=SEED_BASE + seed_offset + i)
        dtrades = val_trades_for_mask(spec, dmask)
        per_tool[name] = dict(chosen=chosen, trades=trades, dumb_names=dnames, dumb_trades=dtrades,
                               n_eligible=len(elig))
    return per_tool


def run_axisreduced_construction(specs, cell_results9_by_tool, axes_of9, cells9_by_res, seed_offset):
    """R2b: union of eligible cells (n>=15, exp>0) on the 9-cell CROWD x
    VOL grid. Dumb control: same-count random cells from the SAME 9-cell
    universe."""
    per_tool = {}
    for i, spec in enumerate(specs):
        name = spec["name"]
        cr = cell_results9_by_tool[name]
        cells9 = cells9_by_res[name]
        elig = eligible_cells_n(cr, axes_of9, min_n=MIN_TRAIN_TRADES)
        mask = union_mask(cells9, elig)
        trades = val_trades_for_mask(spec, mask)
        dmask, dnames = dumb_mask_for(cells9, len(elig), seed=SEED_BASE + seed_offset + i)
        dtrades = val_trades_for_mask(spec, dmask)
        per_tool[name] = dict(chosen=elig, trades=trades, dumb_names=dnames, dumb_trades=dtrades,
                               n_eligible=len(elig))
    return per_tool


def run_signgate_construction(specs, cell_results_by_tool, axes_of, min_n, seed_offset, exclude_axis=None):
    """R2c: union of eligible cells (n>=min_n, exp>0) on the 73-cell grid
    — same mechanism as step66's router, stricter floor. Dumb control:
    same-count random cells from the 73-cell universe. exclude_axis is
    used ONLY by the v2-strictness axis re-test (section 5 analogue)."""
    per_tool = {}
    for i, spec in enumerate(specs):
        name = spec["name"]
        cr = cell_results_by_tool[name]
        elig = eligible_cells_n(cr, axes_of, min_n=min_n, exclude_axis=exclude_axis)
        mask = union_mask(spec["cells"], elig)
        trades = val_trades_for_mask(spec, mask)
        dmask, dnames = dumb_mask_for(spec["cells"], len(elig), seed=SEED_BASE + seed_offset + i)
        dtrades = val_trades_for_mask(spec, dmask)
        per_tool[name] = dict(chosen=elig, trades=trades, dumb_names=dnames, dumb_trades=dtrades,
                               n_eligible=len(elig))
    return per_tool


def run_weighted_construction(specs, cell_results_by_tool, axes_of, seed_offset):
    """R2d: trade SET identical to step66's router (union of eligible
    cells, n>=15/exp>0); weight = 1.0 in the rank-1 cell, 0.5 elsewhere.
    Dumb control: SAME trade set, but the 1.0-weight cell is a random
    eligible cell instead of the true rank-1 one."""
    per_tool = {}
    for i, spec in enumerate(specs):
        name = spec["name"]
        cr = cell_results_by_tool[name]
        elig = eligible_cells(cr, axes_of)
        ranked = rank_by_train_exp(cr, elig)
        if not ranked:
            per_tool[name] = dict(chosen=[], trades=[], dumb_names=[], dumb_trades=[], n_eligible=0)
            continue
        top1 = ranked[0]
        others = ranked[1:]
        top_mask = spec["cells"][top1]
        other_mask = union_mask(spec["cells"], others) if others else None
        trades = val_trades_weighted(spec, top_mask, other_mask)

        rng = np.random.RandomState(SEED_BASE + seed_offset + i)
        rand_top_name = ranked[int(rng.randint(0, len(ranked)))]
        rand_others = [n for n in ranked if n != rand_top_name]
        rand_top_mask = spec["cells"][rand_top_name]
        rand_other_mask = union_mask(spec["cells"], rand_others) if rand_others else None
        dtrades = val_trades_weighted(spec, rand_top_mask, rand_other_mask)

        per_tool[name] = dict(chosen=elig, top1=top1, trades=trades,
                               dumb_names=[rand_top_name], dumb_trades=dtrades, n_eligible=len(elig))
    return per_tool


# ===========================================================================
# AGGREGATION HELPERS
# ===========================================================================

def merged_stats_binary(per_tool, key):
    lists = [trades_to_pct(per_tool[n][key]) for n in TOOL_NAMES]
    accepted = merge_portfolio(lists)
    return portfolio_stats(accepted)


def merged_stats_weighted(per_tool, key):
    lists = [per_tool[n][key] for n in TOOL_NAMES]
    accepted = merge_portfolio_weighted(lists)
    return portfolio_stats_weighted(accepted)


def solo_stats_binary(trades):
    return portfolio_stats(trades_to_pct(trades))


def solo_stats_weighted(trades):
    return portfolio_stats_weighted(trades)


# ===========================================================================
# main
# ===========================================================================

def main():
    data = load_data()
    d1h, frame4h = data["d1h"], data["frame4h"]
    funding1h, funding4h = data["funding1h"], data["funding4h"]
    news, span_start, span_end = data["news_tagged"], data["news_span_start"], data["news_span_end"]
    i_tr1, i_va1 = data["i_tr1"], data["i_va1"]

    val_days = (d1h["timestamp"].iloc[i_va1] - d1h["timestamp"].iloc[i_tr1]).total_seconds() / 86400.0
    print(f"Reference VAL window (main 1h frame): {d1h['timestamp'].iloc[i_tr1]} -> "
          f"{d1h['timestamp'].iloc[i_va1]}  ({val_days:.1f} calendar days)")

    print("\nBuilding 1h/4h scenario axes (73-cell grid, step66-identical)...")
    axes_1h = build_axes(d1h, funding1h, news, span_start, span_end, native_trend=False, frame4h=frame4h, d1h=d1h)
    cells_1h, axes_of = build_cells(**axes_1h)
    axes_4h = build_axes(frame4h, funding4h, news, span_start, span_end, native_trend=True)
    cells_4h, axes_of_4h = build_cells(**axes_4h)
    assert set(axes_of.keys()) == set(axes_of_4h.keys())  # same 73 names both resolutions

    print("Building the 9-cell CROWD x VOL axis-reduced grid (R2b)...")
    cells9_1h, axes_of9 = build_cells_crowdvol(axes_1h["crowd"], axes_1h["vol"])
    cells9_4h, axes_of9_4h = build_cells_crowdvol(axes_4h["crowd"], axes_4h["vol"])
    assert set(axes_of9.keys()) == set(axes_of9_4h.keys())

    print("\nBuilding T3's 4h bias (step56 bias_series_4h -> champ_aligned onto 1h)...")
    bias4h = bias_series_4h(frame4h)
    bias_1h = champ_aligned(frame4h, bias4h, d1h)

    print("\nReconstructing all 8 tools (identical to step66)...")
    specs = [
        build_t1(data, cells_1h),
        build_t2(data, cells_4h),
        build_t3(data, cells_1h, bias_1h),
        build_t4(data, cells_1h),
        build_t5(data, cells_1h),
        build_t6(data, cells_1h),
        build_t7(data, cells_1h),
        build_t8(data, cells_4h),
    ]
    for s in specs:
        print(f"  {s['name']:26s} n={len(s['d']):6d} bars | i_tr={s['i_tr']} i_va={s['i_va']}")

    # ---- which 9-cell grid applies to which tool (1h-native vs 4h-native) ----
    fourh_tools = {"T2-hidden-div-4h", "T8-bbwidth-squeeze-4h"}
    cells9_by_tool = {s["name"]: (cells9_4h if s["name"] in fourh_tools else cells9_1h) for s in specs}

    print("\n" + "=" * 78)
    print("PER-TOOL x PER-CELL EVALUATION — 73-cell grid (identical to step66)")
    print("=" * 78)
    baselines = {}
    cell_results_by_tool = {}
    for spec in specs:
        baseline, cell_results, _rows = eval_tool_cells(spec)
        baselines[spec["name"]] = baseline
        cell_results_by_tool[spec["name"]] = cell_results
        b_tr, b_va = baseline["tr"], baseline["va"]
        print(f"  {spec['name']:26s} UNCOND train ${b_tr.expectancy:+8.2f}/t n={len(b_tr.trades):4d} | "
              f"val ${b_va.expectancy:+8.2f}/t n={len(b_va.trades):4d}")

    print("\n" + "=" * 78)
    print("PER-TOOL x PER-CELL EVALUATION — 9-cell CROWD x VOL grid (R2b)")
    print("=" * 78)
    cell_results9_by_tool = {}
    for spec in specs:
        cr9 = eval_tool_on_cells(spec, cells9_by_tool[spec["name"]])
        cell_results9_by_tool[spec["name"]] = cr9
        n_pos = sum(1 for r in cr9.values() if r["tr_exp"] > 0 and r["tr_n"] >= MIN_TRAIN_TRADES)
        print(f"  {spec['name']:26s} {n_pos}/9 cells train-positive (n>={MIN_TRAIN_TRADES})")

    # ======================================================================
    # ALWAYS-ON RACK + R66 OR-UNION (continuity references, recomputed here)
    # ======================================================================
    print("\n" + "=" * 78)
    print("REFERENCES: ALWAYS-ON RACK + R66 OR-UNION (recomputed, continuity)")
    print("=" * 78)
    rack_trades = {s["name"]: list(baselines[s["name"]]["va"].trades) for s in specs}
    rack_lists = [trades_to_pct(rack_trades[n]) for n in TOOL_NAMES]
    rack_accepted = merge_portfolio(rack_lists)
    rack_stats = portfolio_stats(rack_accepted)

    r66_per_tool = run_signgate_construction(specs, cell_results_by_tool, axes_of,
                                              min_n=MIN_TRAIN_TRADES, seed_offset=0)
    r66_stats = merged_stats_binary(r66_per_tool, "trades")
    print(f"  ALWAYS-ON RACK        n={rack_stats['n']:4d}  exp ${rack_stats['expectancy']:+8.2f}/t  "
          f"ret {rack_stats['total_return_pct']:+7.1f}%  maxDD {rack_stats['max_dd_pct']:6.1f}%  "
          f"trades/day {rack_stats['n']/val_days:.3f}")
    print(f"  R66 OR-UNION (n>=15)  n={r66_stats['n']:4d}  exp ${r66_stats['expectancy']:+8.2f}/t  "
          f"ret {r66_stats['total_return_pct']:+7.1f}%  maxDD {r66_stats['max_dd_pct']:6.1f}%  "
          f"trades/day {r66_stats['n']/val_days:.3f}")

    # ======================================================================
    # R2a — TOP-K-CELLS-ONLY, k=1,2,3
    # ======================================================================
    print("\n" + "=" * 78)
    print("R2a — TOP-K-CELLS-ONLY")
    print("=" * 78)
    r2a_results = {}
    for k in (1, 2, 3):
        per_tool = run_topk_construction(specs, cell_results_by_tool, axes_of, k, seed_offset=100 * k)
        real_stats = merged_stats_binary(per_tool, "trades")
        dumb_stats = merged_stats_binary(per_tool, "dumb_trades")
        r2a_results[k] = dict(per_tool=per_tool, real=real_stats, dumb=dumb_stats)
        print(f"  k={k}  REAL  n={real_stats['n']:4d}  exp ${real_stats['expectancy']:+8.2f}/t  "
              f"ret {real_stats['total_return_pct']:+7.1f}%  maxDD {real_stats['max_dd_pct']:6.1f}%  "
              f"t/day {real_stats['n']/val_days:.3f}")
        print(f"  k={k}  DUMB  n={dumb_stats['n']:4d}  exp ${dumb_stats['expectancy']:+8.2f}/t  "
              f"ret {dumb_stats['total_return_pct']:+7.1f}%  maxDD {dumb_stats['max_dd_pct']:6.1f}%  "
              f"t/day {dumb_stats['n']/val_days:.3f}")

    # ======================================================================
    # R2b — AXIS-REDUCED (CROWD x VOL, 9 cells)
    # ======================================================================
    print("\n" + "=" * 78)
    print("R2b — AXIS-REDUCED (CROWD x VOL, 9 cells)")
    print("=" * 78)
    r2b_per_tool = run_axisreduced_construction(specs, cell_results9_by_tool, axes_of9, cells9_by_tool,
                                                 seed_offset=200)
    r2b_real = merged_stats_binary(r2b_per_tool, "trades")
    r2b_dumb = merged_stats_binary(r2b_per_tool, "dumb_trades")
    print(f"  REAL  n={r2b_real['n']:4d}  exp ${r2b_real['expectancy']:+8.2f}/t  "
          f"ret {r2b_real['total_return_pct']:+7.1f}%  maxDD {r2b_real['max_dd_pct']:6.1f}%  "
          f"t/day {r2b_real['n']/val_days:.3f}")
    print(f"  DUMB  n={r2b_dumb['n']:4d}  exp ${r2b_dumb['expectancy']:+8.2f}/t  "
          f"ret {r2b_dumb['total_return_pct']:+7.1f}%  maxDD {r2b_dumb['max_dd_pct']:6.1f}%  "
          f"t/day {r2b_dumb['n']/val_days:.3f}")

    # ======================================================================
    # R2c — SIGN-GATE (n>=25, fattened-cell rule)
    # ======================================================================
    print("\n" + "=" * 78)
    print("R2c — SIGN-GATE (train n>=25 & train exp>0)")
    print("=" * 78)
    r2c_per_tool = run_signgate_construction(specs, cell_results_by_tool, axes_of, min_n=25, seed_offset=300)
    r2c_real = merged_stats_binary(r2c_per_tool, "trades")
    r2c_dumb = merged_stats_binary(r2c_per_tool, "dumb_trades")
    print(f"  REAL  n={r2c_real['n']:4d}  exp ${r2c_real['expectancy']:+8.2f}/t  "
          f"ret {r2c_real['total_return_pct']:+7.1f}%  maxDD {r2c_real['max_dd_pct']:6.1f}%  "
          f"t/day {r2c_real['n']/val_days:.3f}")
    print(f"  DUMB  n={r2c_dumb['n']:4d}  exp ${r2c_dumb['expectancy']:+8.2f}/t  "
          f"ret {r2c_dumb['total_return_pct']:+7.1f}%  maxDD {r2c_dumb['max_dd_pct']:6.1f}%  "
          f"t/day {r2c_dumb['n']/val_days:.3f}")

    # ======================================================================
    # R2d — WEIGHTED (graded sizing by cell rank)
    # ======================================================================
    print("\n" + "=" * 78)
    print("R2d — WEIGHTED (rank-1 cell = 1.0x, other eligible cells = 0.5x)")
    print("=" * 78)
    r2d_per_tool = run_weighted_construction(specs, cell_results_by_tool, axes_of, seed_offset=400)
    r2d_real = merged_stats_weighted(r2d_per_tool, "trades")
    r2d_dumb = merged_stats_weighted(r2d_per_tool, "dumb_trades")
    print(f"  REAL  n={r2d_real['n']:4d}  exp ${r2d_real['expectancy']:+8.2f}/t  "
          f"ret {r2d_real['total_return_pct']:+7.1f}%  maxDD {r2d_real['max_dd_pct']:6.1f}%  "
          f"t/day {r2d_real['n']/val_days:.3f}")
    print(f"  DUMB  n={r2d_dumb['n']:4d}  exp ${r2d_dumb['expectancy']:+8.2f}/t  "
          f"ret {r2d_dumb['total_return_pct']:+7.1f}%  maxDD {r2d_dumb['max_dd_pct']:6.1f}%  "
          f"t/day {r2d_dumb['n']/val_days:.3f}")

    # ======================================================================
    # PER-TOOL UNMERGED (no slot competition) DETAIL — every construction
    # ======================================================================
    print("\n" + "=" * 78)
    print("PER-TOOL UNMERGED DETAIL (solo, no cross-tool slot competition)")
    print("=" * 78)
    unmerged_rows = []
    def add_unmerged(cons_name, per_tool, weighted=False):
        for name in TOOL_NAMES:
            info = per_tool[name]
            trades = info["trades"]
            if weighted:
                st = solo_stats_weighted(trades)
            else:
                st = solo_stats_binary(trades)
            unmerged_rows.append(dict(construction=cons_name, tool=name, n_eligible=info["n_eligible"],
                                       n=st["n"], expectancy=st["expectancy"],
                                       total_return_pct=st["total_return_pct"], max_dd_pct=st["max_dd_pct"],
                                       trades_per_day=st["n"] / val_days))

    add_unmerged("R66-OR-UNION", r66_per_tool)
    for k in (1, 2, 3):
        add_unmerged(f"R2a-top{k}", r2a_results[k]["per_tool"])
    add_unmerged("R2b-axisreduced", r2b_per_tool)
    add_unmerged("R2c-signgate-n25", r2c_per_tool)
    add_unmerged("R2d-weighted", r2d_per_tool, weighted=True)

    unmerged_df = pd.DataFrame(unmerged_rows)
    unmerged_df.to_csv("step68_unmerged_detail.csv", index=False)
    print(unmerged_df.to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    # ======================================================================
    # AXIS RE-TEST AT v2 STRICTNESS (R2c mechanism, n>=25, each axis dropped)
    # ======================================================================
    print("\n" + "=" * 78)
    print("AXIS RE-TEST AT v2 STRICTNESS (R2c's n>=25 sign-gate, one axis dropped at a time)")
    print("=" * 78)
    axis_retest = {}
    for axis in ("trend", "vol", "crowd", "news", "session"):
        per_tool_ax = run_signgate_construction(specs, cell_results_by_tool, axes_of, min_n=25,
                                                  seed_offset=500, exclude_axis=axis)
        stats_ax = merged_stats_binary(per_tool_ax, "trades")
        axis_retest[axis] = stats_ax
        delta = stats_ax["expectancy"] - r2c_real["expectancy"]
        print(f"  R2c-no{axis.upper():8s} n={stats_ax['n']:4d}  exp ${stats_ax['expectancy']:+8.2f}/t "
              f"(full R2c ${r2c_real['expectancy']:+.2f}/t, delta {delta:+.2f})  "
              f"ret {stats_ax['total_return_pct']:+7.1f}%  t/day {stats_ax['n']/val_days:.3f}")

    # ======================================================================
    # WRITE SUMMARY CSV + hand back everything results.md needs
    # ======================================================================
    summary_rows = [
        dict(construction="ALWAYS-ON-RACK", n=rack_stats["n"], expectancy=rack_stats["expectancy"],
             total_return_pct=rack_stats["total_return_pct"], max_dd_pct=rack_stats["max_dd_pct"],
             trades_per_day=rack_stats["n"] / val_days),
        dict(construction="R66-OR-UNION", n=r66_stats["n"], expectancy=r66_stats["expectancy"],
             total_return_pct=r66_stats["total_return_pct"], max_dd_pct=r66_stats["max_dd_pct"],
             trades_per_day=r66_stats["n"] / val_days),
    ]
    for k in (1, 2, 3):
        summary_rows.append(dict(construction=f"R2a-top{k}-REAL", n=r2a_results[k]["real"]["n"],
                                  expectancy=r2a_results[k]["real"]["expectancy"],
                                  total_return_pct=r2a_results[k]["real"]["total_return_pct"],
                                  max_dd_pct=r2a_results[k]["real"]["max_dd_pct"],
                                  trades_per_day=r2a_results[k]["real"]["n"] / val_days))
        summary_rows.append(dict(construction=f"R2a-top{k}-DUMB", n=r2a_results[k]["dumb"]["n"],
                                  expectancy=r2a_results[k]["dumb"]["expectancy"],
                                  total_return_pct=r2a_results[k]["dumb"]["total_return_pct"],
                                  max_dd_pct=r2a_results[k]["dumb"]["max_dd_pct"],
                                  trades_per_day=r2a_results[k]["dumb"]["n"] / val_days))
    summary_rows += [
        dict(construction="R2b-REAL", n=r2b_real["n"], expectancy=r2b_real["expectancy"],
             total_return_pct=r2b_real["total_return_pct"], max_dd_pct=r2b_real["max_dd_pct"],
             trades_per_day=r2b_real["n"] / val_days),
        dict(construction="R2b-DUMB", n=r2b_dumb["n"], expectancy=r2b_dumb["expectancy"],
             total_return_pct=r2b_dumb["total_return_pct"], max_dd_pct=r2b_dumb["max_dd_pct"],
             trades_per_day=r2b_dumb["n"] / val_days),
        dict(construction="R2c-REAL", n=r2c_real["n"], expectancy=r2c_real["expectancy"],
             total_return_pct=r2c_real["total_return_pct"], max_dd_pct=r2c_real["max_dd_pct"],
             trades_per_day=r2c_real["n"] / val_days),
        dict(construction="R2c-DUMB", n=r2c_dumb["n"], expectancy=r2c_dumb["expectancy"],
             total_return_pct=r2c_dumb["total_return_pct"], max_dd_pct=r2c_dumb["max_dd_pct"],
             trades_per_day=r2c_dumb["n"] / val_days),
        dict(construction="R2d-REAL", n=r2d_real["n"], expectancy=r2d_real["expectancy"],
             total_return_pct=r2d_real["total_return_pct"], max_dd_pct=r2d_real["max_dd_pct"],
             trades_per_day=r2d_real["n"] / val_days),
        dict(construction="R2d-DUMB", n=r2d_dumb["n"], expectancy=r2d_dumb["expectancy"],
             total_return_pct=r2d_dumb["total_return_pct"], max_dd_pct=r2d_dumb["max_dd_pct"],
             trades_per_day=r2d_dumb["n"] / val_days),
    ]
    for axis, st in axis_retest.items():
        summary_rows.append(dict(construction=f"R2c-no{axis}", n=st["n"], expectancy=st["expectancy"],
                                  total_return_pct=st["total_return_pct"], max_dd_pct=st["max_dd_pct"],
                                  trades_per_day=st["n"] / val_days))
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv("step68_summary.csv", index=False)
    print("\nWritten: step68_summary.csv, step68_unmerged_detail.csv")

    print("\n" + "=" * 78)
    print("FINAL COMPARISON TABLE (val, merged single-slot portfolio)")
    print("=" * 78)
    print(summary_df.to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    return dict(val_days=val_days, rack_stats=rack_stats, r66_stats=r66_stats,
                r2a_results=r2a_results, r2b_real=r2b_real, r2b_dumb=r2b_dumb,
                r2c_real=r2c_real, r2c_dumb=r2c_dumb, r2d_real=r2d_real, r2d_dumb=r2d_dumb,
                axis_retest=axis_retest, unmerged_df=unmerged_df, summary_df=summary_df,
                cell_results_by_tool=cell_results_by_tool, cell_results9_by_tool=cell_results9_by_tool)


if __name__ == "__main__":
    main()
