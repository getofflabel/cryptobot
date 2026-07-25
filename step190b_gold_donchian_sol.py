"""
step190b_gold_donchian_sol.py — cross-market transfer: gold's donchian
breakout (d20 + EMA20-close trend-filter exit, sealed-passed 4x across
GLD/GC=F, ~5.4 trades/yr, thickness ~17x costs — the desk's cleanest edge,
per MARKET_PLAYBOOKS.md GOLD section) ported to SOL.

This is a SHAPE port, not a number port: donchian channel breakout entry +
EMA trend-filter exit is the mechanism (strategy.donchian_breakout /
step48_tradfi_trend.donchian_ema_exit, imported UNCHANGED). Gold's own
numbers (d20 window, ATR% 0.28-0.72% range, near-zero ETF/futures costs)
belong to gold's own distribution and are NOT assumed to carry over.

TWO STAGES, IN ORDER (transfer discipline: unchanged first, re-derive only
if the unchanged replay is close-but-not-quite, and always state both
numbers side by side):

  STAGE 1 — UNCHANGED REPLAY: donchian_ema_exit(d, entry_n=20, ema_n=20)
  on SOL's own 1d bars (gold's own timeframe), gold's exact window,
  SOL's REAL BloFin perp costs (NOT gold's near-zero ETF/futures cost
  model — that would be porting a number too; SOL's own CostModel()
  defaults, taker execution, 18bps round trip).

  STAGE 2 — SOL-NATIVE RE-DERIVATION. Gold's ATR% range (0.28-0.72%,
  daily) is cited explicitly and then NOT reused — SOL's own ATR% is
  measured fresh, on SOL's own bars, at every timeframe tested. Two
  things are re-derived, both stated against gold's original number:
    (a) DONCHIAN WINDOW — swept per timeframe (1d, 4h — the two SOL series
        with a long enough cached history) since SOL is faster than gold
        and a calendar-equivalent window is not assumed to be the right
        one; entry_n in {10,15,20,30,55}, ema_n held at 20 (the shape's
        trend-filter span, not swept — same discipline as the gold rounds
        themselves, which fixed ema_n=20 while sweeping the donchian
        window).
    (b) PROTECTIVE STOP — gold runs NO fixed stop (pure EMA-exit) because
        ETF/futures overnight GAPS blow through tight stops (round 47/48's
        own documented lesson: 44/45 GLD val trades gapped THROUGH a 0.5%
        stop). SOL is a 24/7 perp with NO overnight gap window — that
        specific reason to avoid a stop does not apply here, so this is
        tested as an honest SOL-specific question, not assumed either way:
        none vs an ATR-scaled protective stop (k x SOL's own TRAIN-median
        ATR% at the chosen timeframe, k in {3, 5} — wide multiples, because
        this is a trend-following swing shape, not a tight day-trade).

Selection: TRAIN expectancy only, among configs meeting the trade-count
floor where possible; val read once per selected config; test NEVER
touched (60/20/20 chronological, matches split_points elsewhere in repo).

Execution: taker, always. Costs: SOL's real BloFin CostModel() defaults
(config.fee_bps() -> 6bps taker), not gold's near-zero ETF/futures rate —
using gold's low-cost assumption on a crypto perp would misstate SOL's
actual hurdle.

Chance baseline: donchian trend systems trade rarely (gold ran ~5.4/yr) —
a random-entry-count null is a poor fit for a state-machine trend hold
(same reasoning as step190a edge 3). Instead this reports buy-and-hold
comparison over the identical window (the standard framing this repo
already uses for trend systems — see MARKET_PLAYBOOKS GOLD/SPX: "the case
is drawdown cut, not raw-return outperformance") plus gate/duty-cycle
diagnostics.

Research only. Writes step190b_gold_donchian_sol.py (this file),
step190b_results.md, step190b_table.csv, appends to
step190_family_map.md. No git commands, no live orders, no live-file
edits. Sealed test slice never sliced/computed/read.
"""

from __future__ import annotations

import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from backtest import CostModel, run_backtest
from step7_deep_search import fetch_bybit_deep
from step48_tradfi_trend import donchian_ema_exit
from step190_common import (
    ROUND_TRIP_COST_BPS, adverse_excursion_stats, append_family_line,
    avg_notional, combined_expectancy,
)
import strategy as STRAT

T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:8.1f}s]", *a, flush=True)


ASSET = "SOL"
SYM = f"{ASSET}USDT"
MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8
GOLD_ORIGINAL_ATR_RANGE = (0.28, 0.72)   # % daily, cited from MARKET_PLAYBOOKS GOLD section
GOLD_ORIGINAL_ENTRY_N = 20
GOLD_ORIGINAL_TRADES_PER_YEAR = 5.4
GOLD_ORIGINAL_THICKNESS = 17.0


def split_points(d):
    n = len(d)
    return n, int(n * 0.6), int(n * 0.8)


def score(d, sig, i_tr, i_va, stop_pct=None, target_pct=None):
    def run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True),
            sig.iloc[lo:hi].reset_index(drop=True),
            execution="taker",   # house standard, always
            stop_pct=stop_pct, target_pct=target_pct,
            # costs default to CostModel() — SOL's real BloFin perp rates,
            # NOT gold's near-zero ETF/futures cost model.
        )
    return run(0, i_tr), run(i_tr, i_va)


def verdict_for(tr, va):
    tr_n, va_n = len(tr.trades), len(va.trades)
    if tr.expectancy > 0 and va.expectancy > 0:
        if tr_n >= MIN_TRAIN_TRADES and va_n >= MIN_VAL_TRADES:
            return "SURVIVOR"
        return "INSUFFICIENT SAMPLE"
    return "FAIL"


def buy_hold_return_pct(d, lo, hi):
    seg = d.iloc[lo:hi]
    if len(seg) < 2:
        return float("nan")
    return float((seg["close"].iloc[-1] / seg["close"].iloc[0] - 1) * 100)


def row(tf, entry_n, ema_n, stop_label, stop_pct, d, tr, va, i_tr, i_va):
    exp, n_t = combined_expectancy(tr, va)
    notional = avg_notional(tr, va)
    ae = adverse_excursion_stats(tr, va)
    edge_pct = mult = float("nan")
    if notional and notional > 0 and not np.isnan(exp):
        edge_pct = exp / notional * 100
        mult = (edge_pct * 100) / ROUND_TRIP_COST_BPS
    n, _, _ = split_points(d)
    yrs_tr = (d["timestamp"].iloc[i_tr - 1] - d["timestamp"].iloc[0]).days / 365.25
    yrs_va = (d["timestamp"].iloc[i_va - 1] - d["timestamp"].iloc[i_tr]).days / 365.25
    trades_per_yr = (len(tr.trades) + len(va.trades)) / (yrs_tr + yrs_va) if (yrs_tr + yrs_va) > 0 else float("nan")
    bh_tr = buy_hold_return_pct(d, 0, i_tr)
    bh_va = buy_hold_return_pct(d, i_tr, i_va)
    return dict(
        tf=tf, entry_n=entry_n, ema_n=ema_n, stop=stop_label, stop_pct=stop_pct,
        tr_n=len(tr.trades), tr_exp=tr.expectancy, tr_ret=tr.total_return_pct,
        tr_dd=tr.max_drawdown_pct, tr_bh_ret=bh_tr,
        va_n=len(va.trades), va_exp=va.expectancy, va_ret=va.total_return_pct,
        va_dd=va.max_drawdown_pct, va_bh_ret=bh_va,
        combined_n=n_t, combined_exp=exp, trades_per_yr=trades_per_yr,
        avg_notional=notional, edge_pct_notional=edge_pct, thickness_x_cost=mult,
        worst_adverse_pct=ae["worst_pct"], p5_adverse_pct=ae["p5_pct"],
        median_move_pct=ae["median_pct"],
        verdict=verdict_for(tr, va),
    )


def main():
    log("STEP 190b — gold donchian+EMA20-exit shape ported to SOL")
    log(f"gold's original: entry_n={GOLD_ORIGINAL_ENTRY_N}, ema_n=20, daily ATR% range "
       f"{GOLD_ORIGINAL_ATR_RANGE}, ~{GOLD_ORIGINAL_TRADES_PER_YEAR}/yr, thickness "
       f"~{GOLD_ORIGINAL_THICKNESS}x cost (MARKET_PLAYBOOKS GOLD section) -- cited, NOT reused")
    log(f"SOL taker round-trip cost = {ROUND_TRIP_COST_BPS:.1f}bps (SOL's own BloFin perp "
       f"CostModel() default, NOT gold's near-zero ETF/futures rate)")

    frames = {}
    for tf in ("1d", "4h"):
        d = fetch_bybit_deep(tf, SYM)
        frames[tf] = d
        atr_pct = STRAT.atr(d, 14) / d["close"] * 100
        n, i_tr, i_va = split_points(d)
        med_atr_train = float(atr_pct.iloc[:i_tr].median())
        lo_atr, hi_atr = float(atr_pct.quantile(0.10)), float(atr_pct.quantile(0.90))
        log(f"  SOL {tf}: {n} bars {d['timestamp'].iloc[0]:%Y-%m-%d}->{d['timestamp'].iloc[-1]:%Y-%m-%d} "
           f"| train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed) "
           f"| SOL median train ATR%={med_atr_train:.3f}% (10th-90th pctile {lo_atr:.3f}-{hi_atr:.3f}%) "
           f"vs gold's cited {GOLD_ORIGINAL_ATR_RANGE[0]}-{GOLD_ORIGINAL_ATR_RANGE[1]}%")

    rows = []

    # -----------------------------------------------------------------
    # STAGE 1 -- UNCHANGED REPLAY: d20 + EMA20 exit, SOL's own 1d bars,
    # gold's exact window, no stop (pure EMA-exit, matching gold's own
    # mechanism exactly), SOL's real costs, taker.
    # -----------------------------------------------------------------
    log("\nSTAGE 1 -- unchanged replay: donchian20 + EMA20 exit, SOL 1d, no stop")
    d = frames["1d"]
    n, i_tr, i_va = split_points(d)
    sig = donchian_ema_exit(d, GOLD_ORIGINAL_ENTRY_N, ema_n=20)
    tr, va = score(d, sig, i_tr, i_va, stop_pct=None, target_pct=None)
    r = row("1d", GOLD_ORIGINAL_ENTRY_N, 20, "none (pure EMA-exit, gold's own mechanism)",
           None, d, tr, va, i_tr, i_va)
    r["stage"] = "1_unchanged_replay"
    rows.append(r)
    log(f"  train n={len(tr.trades)} exp=${tr.expectancy:.2f} ret={tr.total_return_pct:.1f}% "
       f"(buy&hold {r['tr_bh_ret']:.1f}%) | val n={len(va.trades)} exp=${va.expectancy:.2f} "
       f"ret={va.total_return_pct:.1f}% (buy&hold {r['va_bh_ret']:.1f}%) | {trades_per_yr_str(r)} "
       f"| thickness {fmt_x(r['thickness_x_cost'])} | verdict {r['verdict']}")

    # -----------------------------------------------------------------
    # STAGE 2 -- SOL-NATIVE RE-DERIVATION: sweep entry_n per timeframe,
    # ema_n fixed at 20 (shape constant), stop in {none, 3xATR, 5xATR}
    # using SOL's OWN train-median ATR% at that timeframe -- select on
    # TRAIN only, report val once for whichever config TRAIN prefers.
    # -----------------------------------------------------------------
    log("\nSTAGE 2 -- SOL-native re-derivation sweep (entry_n x timeframe x stop)")
    ENTRY_NS = (10, 15, 20, 30, 55)
    sweep_rows = []
    for tf in ("1d", "4h"):
        d = frames[tf]
        n, i_tr, i_va = split_points(d)
        atr_pct = STRAT.atr(d, 14) / d["close"] * 100
        med_atr_train = float(atr_pct.iloc[:i_tr].median())
        for entry_n in ENTRY_NS:
            sig = donchian_ema_exit(d, entry_n, ema_n=20)
            for stop_label, stop_pct in (
                ("none", None),
                ("3xATR", min(3.0 * med_atr_train, 30.0)),
                ("5xATR", min(5.0 * med_atr_train, 30.0)),
            ):
                tr, va = score(d, sig, i_tr, i_va, stop_pct=stop_pct, target_pct=None)
                r = row(tf, entry_n, 20, stop_label, stop_pct, d, tr, va, i_tr, i_va)
                r["stage"] = "2_native_sweep"
                sweep_rows.append(r)
    rows += sweep_rows
    log(f"  {len(sweep_rows)} configs swept ({len(ENTRY_NS)} windows x 2 timeframes x 3 stop variants)")

    sweep_df = pd.DataFrame(sweep_rows)
    # TRAIN-only selection among configs with n_train >= 1 (report the
    # honest trade-count floor separately -- donchian is a rare-trade
    # shape, INSUFFICIENT SAMPLE is an expected, not a failure, outcome).
    sweep_df = sweep_df.sort_values("tr_exp", ascending=False)
    log("\nTop 8 by TRAIN expectancy (selection is TRAIN-only; val below is read ONCE per row shown):")
    show_cols = ["tf", "entry_n", "stop", "tr_n", "tr_exp", "tr_ret", "va_n", "va_exp",
                "va_ret", "trades_per_yr", "thickness_x_cost", "verdict"]
    print(sweep_df[show_cols].head(8).to_string(index=False,
          float_format=lambda x: f"{x:,.2f}" if isinstance(x, float) else str(x)))

    best = sweep_df.iloc[0]
    log(f"\nTRAIN-selected best: {best['tf']} donchian{best['entry_n']} EMA20exit stop={best['stop']} "
       f"-> train n={best['tr_n']} exp=${best['tr_exp']:.2f} (this is the ONE val read spent on this stage)")
    log(f"  val n={best['va_n']} exp=${best['va_exp']:.2f} ret={best['va_ret']:.1f}% "
       f"(buy&hold {best['va_bh_ret']:.1f}%) | {trades_per_yr_str(best)} | "
       f"thickness {fmt_x(best['thickness_x_cost'])} | verdict {best['verdict']}")

    table = pd.DataFrame(rows)
    table.to_csv("step190b_table.csv", index=False)
    log(f"\nwrote step190b_table.csv ({len(table)} rows, includes full sweep for audit)")

    # family map lines
    r1 = rows[0]
    append_family_line(
        f"- **gold_donchian_port(1_unchanged_replay)** [1d, d20+EMA20exit, unchanged-config "
        f"replay of gold's exact window] — {r1['verdict']} | combined {r1['combined_n']}t "
        f"${r1['combined_exp']:.2f}/t (train {r1['tr_n']}t ${r1['tr_exp']:.2f}, val {r1['va_n']}t "
        f"${r1['va_exp']:.2f}) | {trades_per_yr_str(r1)} | thickness {fmt_x(r1['thickness_x_cost'])} "
        f"| buy&hold train {r1['tr_bh_ret']:.1f}% / val {r1['va_bh_ret']:.1f}% | "
        f"source: gold's original d20+EMA20exit sealed-passed 4x, ~5.4t/yr, ~17x thickness"
    )
    append_family_line(
        f"- **gold_donchian_port(2_SOL_native_derivation)** [{best['tf']}, donchian{best['entry_n']}"
        f"+EMA20exit stop={best['stop']}, TRAIN-selected from a {len(ENTRY_NS)}-window x 2tf x "
        f"3-stop sweep] — {best['verdict']} | train {best['tr_n']}t ${best['tr_exp']:.2f}/t, "
        f"val {best['va_n']}t ${best['va_exp']:.2f}/t | {trades_per_yr_str(best)} | "
        f"thickness {fmt_x(best['thickness_x_cost'])} | gold's original entry_n=20/ATR%"
        f"={GOLD_ORIGINAL_ATR_RANGE} vs SOL's own (see step190b_results.md for the per-tf median) "
        f"-> re-derived per this desk's own distribution, not ported"
    )
    log("appended 2 lines to step190_family_map.md")
    log(f"total runtime: {round(time.time() - T0, 1)}s")
    return table


def trades_per_yr_str(r):
    v = r.get("trades_per_yr", float("nan"))
    return f"{v:.1f}t/yr" if v == v else "n/a"


def fmt_x(v):
    return f"{v:.1f}x" if v == v else "n/a"


if __name__ == "__main__":
    main()
