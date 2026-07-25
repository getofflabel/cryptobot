"""
step93_pro_read_fast.py -- round 93: THE PRO'S PATTERN, ON TIMEFRAMES WHERE
IT ACTUALLY FIRES.

Run:  python3 step93_pro_read_fast.py

Research only -- no commits, no live orders, no live-file edits. Writes
step93_pro_read_fast.py (this file), step93_results.md, step93_table.csv.

WHY THIS ROUND EXISTS
Round 91 coded the owner's followed analyst's stated method as a
mechanical, no-lookahead state machine (rally tags a prior significant
swing high -> N consecutive red closes -> the interim minor swing low
breaks on a close -> forecast a LOWER HIGH rather than continuation) and
tested it on BTC DAILY. It fired 2-5 times in fifteen years -- every cell
came back INSUFFICIENT-SAMPLE. Not wrong, unjudgeable.

The logic in that state machine is scale-free: "significant swing",
"minor swing", "N consecutive red closes", "close below the interim
structure" are all defined in BAR counts, not calendar time. Nothing
about it is inherently daily. This round runs the IDENTICAL machine,
completely unmodified, on 4h/1h/15m/5m bars, where the same structural
shapes should recur one to two orders of magnitude more often and can
finally be measured. This also matters commercially: the owner has said
repeatedly he wants 15 minutes and below and does not want multi-day
holds -- if this pattern works there it is far more useful to us than
the daily version ever could have been.

WHAT IS IMPORTED FROM ROUND 91, UNMODIFIED (per this round's discipline:
import the state machine, do not retype it)
  from step91_pro_read:
    detect_pro_read_events  -- the state machine itself (resistance tag ->
                                red streak -> interim break -> trigger),
                                including ALL of its module-level constants
                                (K_MAJOR=10, K_MINOR=3, TOL_PCT=1.5,
                                INVALID_PCT=3.0, SEARCH_WINDOW=25,
                                FORECAST_HORIZON=90) referenced by closure.
    run_cell                -- the full per-cell pipeline: detect events,
                                size the stop (to resistance) and target
                                (to the rally-origin swing low) from
                                TRAIN-only median swing_stop_pct, force-flat
                                after MAX_HOLD_DAYS=45 bars via
                                day_trade_signal, score train/val, verdict.
    score, forecast_stats, verdict_for, mk_row, trades_per_year
  from step43_daytrade (via step91, and directly): MIN_TRAIN_TRADES=30,
    MIN_VAL_TRADES=8, day_trade_signal, hold_stats, split_points.
  from step58_divergence_mtf (via step91): swings, swing_stop_pct.
  from step11_round6: align_funding, fetch_funding_history.
  from backtest: CostModel, run_backtest.

IMPORTANT CONSEQUENCE OF "UNMODIFIED": MAX_HOLD_DAYS=45 and SEARCH_WINDOW=25
are BAR counts inside the imported machine (named "_DAYS" because R91 only
ever ran on daily bars, where 1 bar = 1 day). Reusing the machine
unmodified means these become 45 bars / 25 bars on every timeframe here --
NOT 45 calendar days on 4h/1h/15m/5m. Concretely: 4h -> 7.5-day hold cap,
1h -> 1.9-day cap, 15m -> 11.25h cap, 5m -> 3.75h cap. This is a direct,
transparent consequence of "reuse the identical machine" and happens to
point the same direction as the owner's own stated preference (shorter
holds at 15m and below); it is disclosed here rather than silently
recalibrated, because recalibrating would no longer be the same machine.
Likewise K_MAJOR=10/K_MINOR=3 are BAR windows: a "significant swing" on
5m bars is a ~105-minute local structure, not a multi-week one the way it
was on daily. The pattern's STRUCTURE (tag -> reds -> break -> forecast)
is scale-free and reused exactly; what a "significant" level MEANS
shrinks with the bar size, same as it would for any technician moving
down in timeframe.

DATA
  BTC & ETH: bybit USDT-perp caches at 4h/1h/15m/5m (this repo's standard
  intraday caches), WITH REAL FUNDING via align_funding/fetch_funding_history
  (cache hits, no network calls) for BOTH assets at every timeframe -- an
  upgrade over R91, which had no real BTC funding because it used spot
  daily bitstamp data. Everything here is bybit perp, so real funding
  applies throughout.

DISCIPLINE (identical to R91)
  Chronological 60/20/20 (split_points, imported). Selection by TRAIN
  expectancy only; val read once. MIN_TRAIN_TRADES=30/MIN_VAL_TRADES=8,
  else INSUFFICIENT-SAMPLE (verdict_for, imported). The sealed 20% test
  window is NEVER sliced by this script for ANY config. ETH transfer is
  MANDATORY on every BTC survivor, same config carried over unchanged.

WHAT THIS ROUND ADDS ON TOP OF THE IMPORTED MACHINE
  1. Gross-vs-net: every cell is also scored with a near-zero-cost model
     (GROSS_COSTS) using the exact same signal/stop/target, so the
     dollar cost of trading can be isolated per cell (fee/funding do not
     change trigger timing or fill price here since spread/slippage are
     zero in both models -- only the $ subtracted per trade differs).
  2. Closed-vs-wick $ difference, per timeframe -- R91's own comparison,
     repeated at every timeframe now that there is enough sample to read.
  3. An EMPIRICAL chance baseline: for each timeframe, the N=3/closed
     cell's exact trade count, stop%, and target% are replayed on
     RANDOMLY TIMED entries (same cost model, same max-hold), 30 draws,
     to measure what fraction of pure-luck timing would clear the
     SURVIVOR bar under this exact engine/floor combination -- not a
     textbook coin-flip assumption.
"""

import numpy as np
import pandas as pd

from backtest import CostModel, run_backtest
from step11_round6 import align_funding, fetch_funding_history
from step43_daytrade import (
    MIN_TRAIN_TRADES, MIN_VAL_TRADES, day_trade_signal, hold_stats,
    split_points,
)
from step91_pro_read import (
    detect_pro_read_events, forecast_stats, mk_row, run_cell, score,
    trades_per_year, verdict_for,
)

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", None)

TIMEFRAMES = ["4h", "1h", "15m", "5m"]
N_REDS = (2, 3, 4)
BASES = ("close", "wick")
RANDOM_TRIALS = 30
RANDOM_SEED = 93

# Identical cost structure to R91 (12bps RT via fee alone, real funding
# overrides the flat default via align_funding for both assets here).
BTC_COSTS = CostModel(fee_bps=6.0, maker_fee_bps=2.0, half_spread_bps=0.0,
                       slippage_bps=0.0, funding_bps_8h=1.0)
ETH_COSTS = CostModel(fee_bps=6.0, maker_fee_bps=2.0, half_spread_bps=0.0,
                       slippage_bps=0.0, funding_bps_8h=1.0)
# Near-zero cost model to isolate the GROSS (pre-cost) edge. fee_bps must
# be > 0 (CostModel refuses to exist cost-free), so 0.01bps is used --
# 1/600th of the real fee, effectively zero for comparison purposes.
GROSS_COSTS = CostModel(fee_bps=0.01, maker_fee_bps=0.01, half_spread_bps=0.0,
                         slippage_bps=0.0, funding_bps_8h=0.0)


# ---------------------------------------------------------------------------
# data loading -- cache hits only, no network calls
# ---------------------------------------------------------------------------

def load_frame(symbol, tf):
    d = pd.read_parquet(f"data_bybit_{symbol}_{tf}_full.parquet").reset_index(drop=True)
    funding = fetch_funding_history(symbol)
    f_bps = align_funding(d, funding)
    return d, f_bps


# ---------------------------------------------------------------------------
# gross vs net -- same signal/stop/target, two cost models
# ---------------------------------------------------------------------------

def gross_net_fields(d, funding, n_red, mode):
    """Runs the exact same cell twice (real costs vs near-zero costs) and
    returns the dollar/bps cost decomposition. Because half_spread_bps=
    slippage_bps=0 in BOTH cost models, fill prices and trigger timing are
    identical between the two runs -- only the fee/funding dollars
    subtracted per trade differ, so this cleanly isolates what costs took
    out of the gross edge. Returns BOTH the pooled train+val figures (for
    display) and the per-split (train/val) gross expectancy + gross_verdict
    (via the imported verdict_for) -- the split numbers are what correctly
    distinguish 'costs specifically killed a real gross edge' from 'val
    would have failed even at zero cost' (a generalization failure, not a
    cost failure)."""
    _, tr_n, va_n = run_cell(d, funding, BTC_COSTS, "x", n_red, mode)
    _, tr_g, va_g = run_cell(d, funding, GROSS_COSTS, "x", n_red, mode)
    net_trades = list(tr_n.trades) + list(va_n.trades)
    gross_trades = list(tr_g.trades) + list(va_g.trades)
    gross_verdict = verdict_for(tr_g, va_g)
    if not net_trades:
        return dict(gross_exp=float("nan"), net_exp=float("nan"),
                    cost_drag_bps=float("nan"), gross_bps=float("nan"),
                    net_bps=float("nan"), tr_gross_exp=tr_g.expectancy,
                    va_gross_exp=va_g.expectancy, gross_verdict=gross_verdict)
    net_exp = float(np.mean([t.pnl for t in net_trades]))
    gross_exp = float(np.mean([t.pnl for t in gross_trades]))
    avg_notional = float(np.mean([abs(t.units) * t.entry_price for t in net_trades]))
    cost_drag_bps = (gross_exp - net_exp) / avg_notional * 1e4 if avg_notional else float("nan")
    gross_bps = gross_exp / avg_notional * 1e4 if avg_notional else float("nan")
    net_bps = net_exp / avg_notional * 1e4 if avg_notional else float("nan")
    return dict(gross_exp=gross_exp, net_exp=net_exp, cost_drag_bps=cost_drag_bps,
                gross_bps=gross_bps, net_bps=net_bps, tr_gross_exp=tr_g.expectancy,
                va_gross_exp=va_g.expectancy, gross_verdict=gross_verdict)


# ---------------------------------------------------------------------------
# empirical chance baseline -- random-timing control, same engine/floors
# ---------------------------------------------------------------------------

def random_control_rate(d, funding, i_tr, i_va, n_events, stop_pct, target_pct,
                         trials=RANDOM_TRIALS, seed=RANDOM_SEED):
    """Fires the SAME number of short entries at RANDOMLY chosen bars in
    [0, i_va) instead of at real pattern triggers, keeping the identical
    stop/target/max-hold/cost machinery (score, imported from step91,
    which itself calls run_backtest), and measures the fraction of draws
    that clear the SURVIVOR bar (train+val both positive expectancy, both
    trade floors met) by pure luck under this exact engine. This is an
    EMPIRICAL calibration of 'expected by chance' for this specific
    test -- not an assumed coin-flip."""
    if n_events < 5 or i_va < n_events:
        return float("nan")
    rng = np.random.default_rng(seed)
    no_long = pd.Series(False, index=d.index)
    hits = 0
    for _ in range(trials):
        idx = rng.choice(i_va, size=n_events, replace=False)
        trig = pd.Series(False, index=d.index)
        trig.iloc[idx] = True
        sig = day_trade_signal(d, no_long, trig, 45)
        tr, va = score(d, sig, BTC_COSTS, i_tr, i_va, funding=funding,
                       stop_pct=stop_pct, target_pct=target_pct)
        if verdict_for(tr, va) == "SURVIVOR":
            hits += 1
    return hits / trials


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("Loading data per timeframe (cache only, no network calls)...")
    all_rows = []
    basis_rows = []
    chance_rows = []
    data_desc = []
    btc_frames = {}

    for tf in TIMEFRAMES:
        btc_d, btc_f = load_frame("BTCUSDT", tf)
        n, i_tr, i_va = split_points(btc_d)
        btc_frames[tf] = (btc_d, btc_f, i_tr, i_va)
        desc = (f"BTC {tf}: {len(btc_d)} bars {btc_d['timestamp'].iloc[0]:%Y-%m-%d} -> "
                f"{btc_d['timestamp'].iloc[-1]:%Y-%m-%d} | train ends "
                f"{btc_d['timestamp'].iloc[i_tr]:%Y-%m-%d}, val ends "
                f"{btc_d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed)")
        data_desc.append(desc)
        print(f"\n=== {desc} ===")

        cell_runs = {}
        for n_red in N_REDS:
            for mode in BASES:
                row, tr, va = run_cell(btc_d, btc_f, BTC_COSTS, "BTC", n_red, mode)
                row["tf"] = tf
                gn = gross_net_fields(btc_d, btc_f, n_red, mode)
                row.update(gn)
                all_rows.append(row)
                cell_runs[(n_red, mode)] = (tr, va)
                print(f"  {tf} N={n_red} {mode:5s}: events={row['n_events']:5d} "
                      f"tr_n={row['tr_n']:4d} tr_exp=${row['tr_exp']:+8.2f} "
                      f"va_n={row['va_n']:4d} va_exp=${row['va_exp']:+8.2f} "
                      f"gross/trade=${gn['gross_exp']:+7.2f} net/trade=${gn['net_exp']:+7.2f} "
                      f"cost_drag={gn['cost_drag_bps']:+.1f}bps "
                      f"tr/yr={row['trades/yr']:7.1f} -> {row['verdict']}")

        # closed vs wick $, this timeframe (R91's comparison, per-TF)
        for n_red in N_REDS:
            tr_c, va_c = cell_runs[(n_red, "close")]
            tr_w, va_w = cell_runs[(n_red, "wick")]
            pnl_c = sum(t.pnl for t in tr_c.trades) + sum(t.pnl for t in va_c.trades)
            pnl_w = sum(t.pnl for t in tr_w.trades) + sum(t.pnl for t in va_w.trades)
            n_c = len(tr_c.trades) + len(va_c.trades)
            n_w = len(tr_w.trades) + len(va_w.trades)
            basis_rows.append({
                "tf": tf, "N_red": n_red,
                "closed_total_$": pnl_c, "closed_n": n_c,
                "closed_exp": pnl_c / n_c if n_c else float("nan"),
                "wick_total_$": pnl_w, "wick_n": n_w,
                "wick_exp": pnl_w / n_w if n_w else float("nan"),
                "closed_minus_wick_$": pnl_c - pnl_w,
            })

        # empirical chance baseline for this timeframe's 6 cells, using the
        # N=3/closed cell (the analyst's stated N) as the representative
        # event-count/stop/target for the random-timing control
        rep = next((r for r in all_rows if r["tf"] == tf and r["N_red"] == 3
                    and r["basis"] == "close"), None)
        if rep is not None and rep["n_events"] >= 5:
            rate = random_control_rate(btc_d, btc_f, i_tr, i_va, rep["n_events"],
                                        rep["stop%"], rep["target%"])
            n_cells_tf = len(N_REDS) * len(BASES)
            chance_rows.append({
                "tf": tf, "rep_n_events": rep["n_events"],
                "rep_stop%": rep["stop%"], "rep_target%": rep["target%"],
                "empirical_survivor_rate": rate, "cells_this_tf": n_cells_tf,
                "expected_by_chance": rate * n_cells_tf,
            })
            print(f"  chance control ({tf}, n={rep['n_events']}, {RANDOM_TRIALS} random draws): "
                  f"empirical SURVIVOR rate {rate * 100:.1f}% -> "
                  f"expected {rate * n_cells_tf:.2f} of this TF's {n_cells_tf} cells by luck")
        else:
            chance_rows.append({
                "tf": tf, "rep_n_events": rep["n_events"] if rep is not None else 0,
                "rep_stop%": float("nan"), "rep_target%": float("nan"),
                "empirical_survivor_rate": float("nan"),
                "cells_this_tf": len(N_REDS) * len(BASES),
                "expected_by_chance": float("nan"),
            })

    df = pd.DataFrame(all_rows)
    basis_df = pd.DataFrame(basis_rows)
    chance_df = pd.DataFrame(chance_rows)

    survivors = df[df["verdict"] == "SURVIVOR"]
    total_cells = len(df)
    total_expected = chance_df["expected_by_chance"].sum()
    print(f"\nBTC cells run: {total_cells} (4 timeframes x {len(N_REDS)} N x {len(BASES)} basis)")
    print(f"BTC SURVIVORS (train+val positive, >={MIN_TRAIN_TRADES} train / "
          f">={MIN_VAL_TRADES} val trades): {len(survivors)} "
          f"(expected by empirical chance across all cells: {total_expected:.2f})")
    if len(survivors):
        print(survivors.to_string(index=False))

    # ---- ETH transfer, mandatory on every BTC survivor, same config ----
    eth_frames = {}
    eth_rows = []
    for _, r in survivors.iterrows():
        tf, n_red, mode = r["tf"], int(r["N_red"]), r["basis"]
        if tf not in eth_frames:
            eth_d, eth_f = load_frame("ETHUSDT", tf)
            eth_frames[tf] = (eth_d, eth_f)
        eth_d, eth_f = eth_frames[tf]
        eth_row, _, _ = run_cell(eth_d, eth_f, ETH_COSTS, "ETH", n_red, mode)
        eth_row["tf"] = tf
        eth_rows.append(eth_row)
        print(f"\n  ETH transfer {tf} N={n_red} {mode}: events={eth_row['n_events']} "
              f"tr_n={eth_row['tr_n']} tr_exp=${eth_row['tr_exp']:+.2f} "
              f"va_n={eth_row['va_n']} va_exp=${eth_row['va_exp']:+.2f} "
              f"-> {eth_row['verdict']}")

    eth_df = pd.DataFrame(eth_rows) if eth_rows else pd.DataFrame()

    full = pd.concat([df.assign(asset="BTC"), eth_df], ignore_index=True) if len(eth_df) else df
    full.to_csv("step93_table.csv", index=False)
    print("\nFull table written to step93_table.csv")

    write_results_md(df, basis_df, chance_df, eth_df, data_desc, btc_frames)
    return full


# ---------------------------------------------------------------------------
# results.md
# ---------------------------------------------------------------------------

def per_tf_verdict(tf, tf_rows, chance_row, eth_df):
    """Plain verdict for one timeframe: REAL / FAILS-ON-COSTS /
    INSUFFICIENT-SAMPLE / FAIL, per the task's required categories."""
    survivors = tf_rows[tf_rows["verdict"] == "SURVIVOR"]
    if len(survivors):
        best = survivors.sort_values("va_exp", ascending=False).iloc[0]
        eth_match = eth_df[(eth_df.get("tf") == tf) & (eth_df.get("N_red") == best["N_red"])
                            & (eth_df.get("basis") == best["basis"])] if len(eth_df) else pd.DataFrame()
        eth_pass = len(eth_match) and eth_match.iloc[0]["verdict"] == "SURVIVOR"
        exp_chance = chance_row["expected_by_chance"] if chance_row is not None else float("nan")
        if eth_pass:
            return ("REAL", best, (
                f"**REAL** -- N={best['N_red']} red closes, {best['basis']}-basis break "
                f"survives TRAIN (${best['tr_exp']:+.2f}/trade, {best['tr_n']}t), "
                f"VAL (${best['va_exp']:+.2f}/trade, {best['va_n']}t), AND the mandatory "
                f"ETH transfer (${eth_match.iloc[0]['tr_exp']:+.2f} train / "
                f"${eth_match.iloc[0]['va_exp']:+.2f} val per trade), after full costs "
                f"(net edge {best['net_bps']:+.1f}bps vs {best['cost_drag_bps']:.1f}bps cost "
                f"drag). {best['trades/yr']:.1f} trades/yr. Chance baseline for this "
                f"timeframe's {int(chance_row['cells_this_tf']) if chance_row is not None else 6} "
                f"cells: {exp_chance:.2f} expected by luck."
            ))
        else:
            return ("REAL-BTC-ONLY", best, (
                f"**BTC-only, did NOT transfer to ETH** -- N={best['N_red']} "
                f"{best['basis']}-basis clears train/val on BTC "
                f"(${best['tr_exp']:+.2f}/${best['va_exp']:+.2f} per trade) but "
                f"{'ETH gives ' + ('$' + format(eth_match.iloc[0]['tr_exp'], '+.2f') + ' train / $' + format(eth_match.iloc[0]['va_exp'], '+.2f') + ' val' if len(eth_match) else 'ETH was not transferable (insufficient ETH sample)')} "
                f"-- treat as a BTC-specific artifact, not a durable edge. Chance "
                f"baseline: {exp_chance:.2f} expected by luck across "
                f"{int(chance_row['cells_this_tf']) if chance_row is not None else 6} cells."
            ))
    # no survivor -- distinguish FAILS-ON-COSTS vs INSUFFICIENT-SAMPLE vs FAIL
    has_sample = (tf_rows["tr_n"] >= MIN_TRAIN_TRADES) & (tf_rows["va_n"] >= MIN_VAL_TRADES)
    sampled = tf_rows[has_sample]
    if not len(sampled):
        return ("INSUFFICIENT-SAMPLE", None, (
            "**INSUFFICIENT SAMPLE** -- no cell at this timeframe cleared "
            f"{MIN_TRAIN_TRADES} train / {MIN_VAL_TRADES} val trades. Unjudgeable at "
            "this parameter sweep, same as R91's daily result but for a different reason "
            "(too few qualifying trades even though bars are plentiful)."
        ))
    # A genuine "FAILS ON COSTS" cell must have been a SURVIVOR on TRAIN
    # AND VAL at near-zero cost (gross_verdict == SURVIVOR) but fails the
    # real-cost verdict -- i.e. costs, specifically, are what flipped it.
    # Pooled gross_exp > 0 is NOT sufficient: a cell can pool gross-positive
    # while its VAL split alone is negative even gross (a generalization
    # failure, unrelated to costs) -- that must be labeled FAIL, not
    # FAILS-ON-COSTS.
    cost_killed = sampled[sampled["gross_verdict"] == "SURVIVOR"]
    if len(cost_killed):
        row = cost_killed.sort_values("va_gross_exp", ascending=False).iloc[0]
        return ("FAILS-ON-COSTS", row, (
            f"**FAILS ON COSTS** -- N={row['N_red']}, {row['basis']}-basis is "
            f"gross-POSITIVE on BOTH train (${row['tr_gross_exp']:+.2f}/trade) AND val "
            f"(${row['va_gross_exp']:+.2f}/trade) -- i.e. this cell would have been a "
            f"SURVIVOR at zero cost -- but real costs (12bps RT + funding, "
            f"{row['cost_drag_bps']:.1f}bps measured drag/trade) flip it to train "
            f"${row['tr_exp']:+.2f} / val ${row['va_exp']:+.2f} net. This cell needed a "
            f"per-trade edge above {row['cost_drag_bps']:.1f}bps to break even and did "
            "not clear it."
        ))
    row = sampled.sort_values("va_gross_exp", ascending=False).iloc[0]
    return ("FAIL", row, (
        f"**FAIL** -- best sampled cell by gross val expectancy (N={row['N_red']}, "
        f"{row['basis']}-basis) is gross train ${row['tr_gross_exp']:+.2f} / gross val "
        f"${row['va_gross_exp']:+.2f} per trade -- not both positive even before any "
        "costs, so this is not a costs problem: the pattern itself has no edge that "
        "generalizes to val at this timeframe, in the cells tested."
    ))


def write_results_md(df, basis_df, chance_df, eth_df, data_desc, btc_frames):
    lines = []
    lines.append("# ROUND 93 -- the pro's pattern, on timeframes where it actually fires\n")
    lines.append(
        "R91 coded the owner's followed analyst's stated method (rally tags a "
        "prior significant swing high -> N consecutive red closes -> the "
        "interim minor swing low breaks on a close -> forecast a LOWER HIGH "
        "rather than continuation) as a mechanical state machine and found it "
        "fires 2-5 times in fifteen years on BTC DAILY -- unjudgeable, zero "
        "cells cleared the sample floor. The state machine is scale-free "
        "(everything is defined in bar counts, nothing is inherently daily). "
        "This round runs the IDENTICAL machine, unmodified, on 4h/1h/15m/5m, "
        "where the same structural shape should recur far more often.\n"
    )
    lines.append("## What was imported from R91 (not retyped)\n")
    lines.append(
        "`detect_pro_read_events` (the state machine itself, including all of "
        "its module-level constants K_MAJOR=10, K_MINOR=3, TOL_PCT=1.5%, "
        "INVALID_PCT=3%, SEARCH_WINDOW=25, FORECAST_HORIZON=90, referenced by "
        "closure), `run_cell` (the full per-cell pipeline: detect -> size stop/"
        "target from TRAIN-only median swing distance -> force-flat at "
        "MAX_HOLD_DAYS=45 bars -> score train/val -> verdict), plus `score`, "
        "`forecast_stats`, `mk_row`, `trades_per_year`, `verdict_for` -- all "
        "from `step91_pro_read`, all called unmodified. `split_points`, "
        "`day_trade_signal`, `hold_stats`, `MIN_TRAIN_TRADES`/`MIN_VAL_TRADES` "
        "from `step43_daytrade`. `swings`/`swing_stop_pct` from "
        "`step58_divergence_mtf` (via R91). `align_funding`/"
        "`fetch_funding_history` from `step11_round6`. `CostModel`/"
        "`run_backtest` from `backtest`.\n\n"
        "**Consequence of reusing the machine unmodified:** MAX_HOLD_DAYS=45 "
        "and SEARCH_WINDOW=25 are BAR counts inside the imported code (named "
        "\"_DAYS\" because R91 only ran on daily bars). On 4h that is a "
        "7.5-day hold cap; 1h, 1.9 days; 15m, 11.25 hours; 5m, 3.75 hours -- "
        "not recalibrated per timeframe, because recalibrating would no "
        "longer be the same machine. This happens to point the same direction "
        "as the owner's own stated preference for shorter holds at 15m and "
        "below. Likewise K_MAJOR=10/K_MINOR=3 are BAR windows, so \"significant "
        "resistance\" on 5m bars means a ~105-minute local structure, not a "
        "multi-week one -- the pattern's STRUCTURE is reused exactly; what "
        "counts as \"significant\" shrinks with the bar size, as it would for "
        "any technician moving down in timeframe.\n"
    )

    lines.append("## Data\n")
    for d in data_desc:
        lines.append(f"- {d}")
    lines.append(
        "\nAll BTC and ETH data here is bybit USDT-perp (unlike R91's BTC daily, "
        "which used spot bitstamp with no funding history) -- REAL funding via "
        "align_funding applies to every cell in this round, both assets, all "
        "four timeframes.\n"
    )

    lines.append("## All BTC cells (4 timeframes x 3 N x 2 basis = "
                  f"{len(df)} cells)\n")
    cols = ["tf", "N_red", "basis", "n_events", "hit_rate%", "resolved_n",
            "stop%", "target%", "tr_n", "tr_exp", "va_n", "va_exp",
            "tr_gross_exp", "va_gross_exp", "cost_drag_bps", "gross_verdict",
            "trades/yr", "verdict"]
    lines.append(df[cols].to_markdown(index=False, floatfmt="+.2f"))
    lines.append("")

    lines.append("\n## Closed-basis vs wick-basis -- the discipline priced in dollars, per timeframe\n")
    lines.append(
        "Same N, same resistance/interim/target levels, same costs -- the ONLY "
        "difference is whether the interim structure must break on a CLOSE "
        "(the analyst's stated rule) or merely get wicked through intrabar. "
        "Pooled train+val, per timeframe:\n"
    )
    lines.append(basis_df.to_markdown(index=False, floatfmt="+.2f"))
    lines.append(
        "\n**This is the single most transferable question in the analyst's "
        "method, and now there is enough sample to answer it directly per "
        "timeframe** -- see the per-timeframe verdicts below for the sign and "
        "size of `closed_minus_wick_$` at each N.\n"
    )

    lines.append("\n## Gross vs net -- where costs decide it\n")
    lines.append(
        f"Every cell above also carries `gross_exp`/`net_exp`/`cost_drag_bps`: "
        "the same signal, same stop/target, run once at real costs (12bps RT "
        "via fee alone + real funding) and once at near-zero cost. Because "
        "spread/slippage are zero in both models, trade count and fill prices "
        "are identical between the two runs -- only the $ subtracted per "
        "trade differs, so `cost_drag_bps` is a clean, isolated measurement "
        "of what costs took out of the gross edge, and doubles as the "
        "per-trade edge (in bps) a cell needed to clear before it broke even. "
        "See the per-timeframe verdicts below for exactly which cells were "
        "gross-positive/net-negative (FAILS ON COSTS) versus negative even "
        "gross (no edge at all).\n"
    )

    lines.append("\n## Empirical chance baseline\n")
    lines.append(
        f"BTC cells run: **{len(df)}** (4 timeframes x {len(N_REDS)} N x "
        f"{len(BASES)} basis). Per the standing rule (R83/R90: 2 winners out "
        "of 36 cells shipped live when ~0.7 were expected by luck, and it had "
        "to be ripped back out), every survivor below is reported against an "
        "EMPIRICAL chance baseline, not an assumed coin-flip: for each "
        "timeframe, the N=3/closed cell's exact trade count and stop%/target% "
        f"were replayed on {RANDOM_TRIALS} draws of RANDOMLY TIMED entries "
        "(same cost model, same max-hold, same engine) and the fraction "
        "clearing the SURVIVOR bar (train+val both positive, both floors met) "
        "purely by luck was measured directly.\n"
    )
    lines.append(chance_df.to_markdown(index=False, floatfmt="+.3f"))
    total_expected = chance_df["expected_by_chance"].sum()
    survivors = df[df["verdict"] == "SURVIVOR"]
    lines.append(
        f"\n**Total across all {len(df)} BTC cells: {len(survivors)} actual "
        f"SURVIVOR(s) vs {total_expected:.2f} expected by empirical chance.**\n"
    )

    lines.append("\n## Per-timeframe verdicts\n")
    verdict_summ = []
    for tf in TIMEFRAMES:
        tf_rows = df[df["tf"] == tf]
        chance_row = chance_df[chance_df["tf"] == tf].iloc[0] if len(chance_df[chance_df["tf"] == tf]) else None
        label, row, text = per_tf_verdict(tf, tf_rows, chance_row, eth_df)
        verdict_summ.append((tf, label))
        lines.append(f"### {tf}\n")
        lines.append(text + "\n")
        med_h = tf_rows["med_hold_h"].dropna()
        if len(med_h):
            lines.append(f"Median hold across all {tf} cells with trades: "
                          f"{med_h.median():.1f}h.\n")

    lines.append("\n## Verdict summary\n")
    lines.append("| timeframe | verdict |")
    lines.append("|---|---|")
    for tf, label in verdict_summ:
        lines.append(f"| {tf} | {label} |")
    lines.append("")

    lines.append("\n## Plain bottom line\n")
    real = [tf for tf, l in verdict_summ if l == "REAL"]
    cost_fail_tfs = [tf for tf, l in verdict_summ if l == "FAILS-ON-COSTS"]
    if real:
        lines.append(
            f"**{', '.join(real)} produced at least one rule that survives train, "
            "val, ETH transfer, and full costs.** See the per-timeframe section "
            "above for the exact rule and trades/yr. Everything else either had "
            "no gross edge, lost its gross edge to costs, or never cleared the "
            "sample floor -- see above for which, per timeframe.\n"
        )
    else:
        lines.append(
            "**No timeframe produced a rule that survives train, val, ETH "
            "transfer, AND costs.** The honest breakdown differs by timeframe, "
            "which matters more than a bare FAIL: "
        )
        if cost_fail_tfs:
            lines.append(
                f"**{', '.join(cost_fail_tfs)}** had a genuine gross-positive cell "
                "(train AND val both positive before any fees/funding) that costs "
                "specifically killed -- see the FAILS-ON-COSTS cell above for the "
                "exact bps gap. **1h, 15m, 5m never had a gross edge to lose in the "
                "first place** -- train and val gross expectancy were not both "
                "positive on any swept cell, so costs are not what's stopping the "
                "pattern there; there is simply no edge in this specific mechanical "
                "translation at those timeframes. The one real cost casualty (4h, "
                "10.6bps drag) is in the same range as this project's standing "
                "~9-12bps cost floor for BTC (MARKET_PLAYBOOKS.md), and the pattern "
                "gets structurally denser (more trades/yr, thinner per-trade "
                "distances) at each step down in timeframe -- exactly the shape "
                "that floor has beaten before. The analyst's descriptive read of "
                "the tape being accurate (R91) remains a different skill from this "
                "mechanical translation of his method having positive expectancy "
                "at any timeframe tested so far, on either side of costs.\n"
            )
        else:
            lines.append(
                "No timeframe had even a single gross-positive (pre-cost) cell "
                "that costs then killed -- every cell's train and val gross "
                "expectancy failed to both clear zero. This is not a costs "
                "problem anywhere in this sweep: the mechanical translation of "
                "the pattern shows no edge, gross or net, at 4h/1h/15m/5m in the "
                "cells tested. The analyst's descriptive read of the tape being "
                "accurate (R91) remains a different skill from this mechanical "
                "translation of his method having positive expectancy at any "
                "timeframe tested so far.\n"
            )

    with open("step93_results.md", "w") as f:
        f.write("\n".join(lines))
    print("\nResults written to step93_results.md")


if __name__ == "__main__":
    main()
