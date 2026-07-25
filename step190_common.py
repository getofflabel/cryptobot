"""
step190_common.py — shared plumbing for the SOL research program (steps
190-209, sol-trader's block per morgan's allocation 2026-07-25 night).

Every function here is used across step190a/190b and the follow-on rounds
so the same discipline (taker execution, chance baseline, thickness bar)
never has to be retyped or drift between files.

HOUSE STANDARD DEVIATIONS FROM THE SOURCE BTC ROUNDS, STATED ONCE HERE:
  - execution="taker" ALWAYS. Several source BTC rounds (step43/45b/54/56/
    58) used execution="maker" as their repo-wide day-trade convention.
    The sol-trader desk standard is taker always, stated beside every
    number. Taker (6bps) costs MORE than maker (2bps) per side, so this is
    a STRICTER bar than the original BTC rounds cleared, never a laxer one
    — a config that passes here would have passed even more easily under
    the original maker convention.
  - SOL's own taker fee is read from exchange.BlofinExchange.TAKER_FEE_BPS
    via config.fee_bps() — BloFin publishes ONE taker rate (6bps) across
    its standard perpetual contracts, SOL included; this is not computed,
    it is the same published constant the rest of the repo already reads.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest import CostModel, run_backtest

ROUND_TRIP_COST_BPS = CostModel().round_trip_bps()   # taker round trip, both fills


# ---------------------------------------------------------------------------
# scoring — taker execution, always
# ---------------------------------------------------------------------------

def score_taker(d, sig, f, i_tr, i_va, stop_pct=None, target_pct=None):
    """train/val split, execution='taker' always (see module docstring).
    Mirrors every score()/run_split() helper elsewhere in this repo, just
    with the execution mode pinned rather than defaulted to maker."""
    def run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True),
            sig.iloc[lo:hi].reset_index(drop=True),
            execution="taker",
            funding_series=f.iloc[lo:hi].reset_index(drop=True),
            stop_pct=stop_pct, target_pct=target_pct,
        )
    return run(0, i_tr), run(i_tr, i_va)


def combined_expectancy(tr, va):
    trades = list(tr.trades) + list(va.trades)
    if not trades:
        return float("nan"), 0
    return float(np.mean([t.pnl for t in trades])), len(trades)


# ---------------------------------------------------------------------------
# CHANCE BASELINE — random-entry null distribution.
#
# For a directional entry-timing edge (not a veto/filter on an existing
# signal — dumb_control from step83/step88 already covers that case), the
# fair chance question is: "if I fired the SAME NUMBER of long/short
# entries at RANDOM bars instead of the strategy's chosen bars, holding
# the SAME stop/target/max-hold geometry under the SAME cost model, how
# often would I do this well or better?" This isolates the value of ENTRY
# TIMING from the value of the stop/target/hold geometry and cost
# structure, which are held fixed and thus cannot inflate the strategy's
# apparent edge over its own null.
# ---------------------------------------------------------------------------

def random_entry_baseline(d, f, i_tr, i_va, n_long, n_short, mh_bars,
                          stop_pct, target_pct, rng, n_draws=100,
                          day_trade_signal=None):
    """Returns (actual_beats_pct, draws) where draws is the array of
    combined train+val expectancies from n_draws random-entry portfolios
    of the same size/direction-mix as the real strategy, same stop/target/
    hold, same taker costs. actual_beats_pct is filled in by the caller
    (it needs the real expectancy to compare)."""
    if day_trade_signal is None:
        from step43_daytrade import day_trade_signal
    n = len(d)
    eligible = np.arange(mh_bars, n - mh_bars)  # leave room for a full hold
    draws = []
    for _ in range(n_draws):
        if len(eligible) < (n_long + n_short):
            draws.append(float("nan"))
            continue
        picks = rng.choice(eligible, size=n_long + n_short, replace=False)
        long_idx = picks[:n_long]
        short_idx = picks[n_long:]
        el = pd.Series(False, index=d.index)
        es = pd.Series(False, index=d.index)
        el.iloc[long_idx] = True
        es.iloc[short_idx] = True
        sig = day_trade_signal(d, el, es, mh_bars)
        tr, va = score_taker(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
        exp, n_t = combined_expectancy(tr, va)
        draws.append(exp)
    draws = np.array(draws, dtype=float)
    return draws


def chance_percentile(actual_exp, draws):
    """% of random draws the actual result BEATS — >=90 = clears the 90th
    percentile of luck; ~50 = indistinguishable from a random-timed
    portfolio in the exact same cost/geometry box."""
    valid = draws[~np.isnan(draws)]
    if len(valid) == 0 or np.isnan(actual_exp):
        return float("nan")
    return float(np.mean(actual_exp > valid)) * 100


# ---------------------------------------------------------------------------
# THICKNESS BAR — edge as % of notional AND as a multiple of round-trip cost
# ---------------------------------------------------------------------------

def thickness(expectancy_dollars, avg_notional_dollars):
    """Returns (edge_pct_of_notional, thickness_multiple_of_cost).
    Under 5x round-trip cost = REJECT per house standard."""
    if avg_notional_dollars in (0, None) or (isinstance(avg_notional_dollars, float)
                                              and np.isnan(avg_notional_dollars)):
        return float("nan"), float("nan")
    edge_pct = expectancy_dollars / avg_notional_dollars * 100
    edge_bps = edge_pct * 100
    mult = edge_bps / ROUND_TRIP_COST_BPS
    return edge_pct, mult


def avg_notional(tr, va, initial_equity=None):
    """Trade.units * Trade.entry_price = the actual notional put on for
    that fill (engine field, not derived/guessed)."""
    trades = list(tr.trades) + list(va.trades)
    if not trades:
        return float("nan")
    vals = [abs(t.units * t.entry_price) for t in trades]
    return float(np.mean(vals)) if vals else float("nan")


# ---------------------------------------------------------------------------
# ADVERSE EXCURSION — SOL's tail is fatter than BTC's; always report it.
# CAVEAT stated once here: Trade does not carry an intrabar path, so this is
# the realized price move at EXIT (direction-adjusted, stop-slippage
# included when a stop was hit), not a true bar-by-bar max-adverse-
# excursion. For a stop-bounded strategy this is close to (but not
# identical to) the true MAE; it is a lower bound, stated honestly, never
# presented as more than it is.
# ---------------------------------------------------------------------------

def adverse_excursion_stats(tr, va):
    trades = list(tr.trades) + list(va.trades)
    if not trades:
        return dict(n=0, worst_pct=float("nan"), p5_pct=float("nan"), median_pct=float("nan"))
    pct = [float(t.direction * (t.exit_price - t.entry_price) / t.entry_price * 100)
           for t in trades]
    arr = np.array(pct)
    return dict(n=len(arr), worst_pct=float(arr.min()), p5_pct=float(np.percentile(arr, 5)),
                median_pct=float(np.median(arr)))


# ---------------------------------------------------------------------------
# family map appender
# ---------------------------------------------------------------------------

FAMILY_MAP_PATH = "step190_family_map.md"


def append_family_line(line: str):
    with open(FAMILY_MAP_PATH, "a") as fh:
        fh.write(line.rstrip("\n") + "\n")
