"""
step150_common.py — shared harness for ROUND 150: the taker + structure-stop
re-test of BTC's five documented "validated, live" edges (Morgan's mandate,
2026-07-25 night).

WHY THIS FILE EXISTS
Every one of the five edges (see MARKET_PLAYBOOKS.md's BITCOIN section) was
sealed under a MIX of assumptions accumulated over 50+ research rounds — some
used execution="maker" (a post-only limit that either fills passively or
CHASES with a taker order — see backtest.py's own docstring), and every one
of them used run_backtest's stop_pct/target_pct mechanism, which is a SINGLE
FIXED PERCENTAGE for the whole backtest (a train-window median or a flat
number), never a real per-trade chart level. The volume-gated Bollinger
breakout already died tonight going from maker (+$6.97/t) to taker (-$8.15/t)
— this file exists to find out whether the other four survive the same
correction, using exits.py (built earlier tonight) for real per-trade
structure stops instead.

DESIGN
This is a SINGLE-SLOT, SEQUENTIAL, EVENT-DRIVEN engine — not backtest.py's
continuous-signal engine (which cannot express a per-trade dynamic stop
level; see step59/step65's own docstrings for why this repo hand-rolls a
second engine whenever exits need to be chart-derived). It composes:
  - exits.py's SeriesCtx/TradeCtx/run_trade for NO-LOOKAHEAD stop/target
    resolution (structure pivots, trailing floors, R-multiples — never a
    swept percentage).
  - CostModel, execution="taker" ALWAYS: every entry crosses the spread +
    slippage and pays the taker fee; every exit (stop, target, structural
    break, or time cap) does too. This is the deliberate, conservative
    choice backtest.py itself documents ("We assume TAKER... it is the
    conservative choice") — restated here because tonight's whole point is
    that several of these five edges were sealed on the OPPOSITE assumption.
  - Real funding (align_funding/fetch_funding_history), signed exactly like
    backtest.py: longs pay a positive rate, shorts collect it.
  - Fixed-fractional RISK sizing: notional = RISK_PCT * equity / stop_dist_
    frac (the SAME formula daily_pick.py / tradfi_engine.py already run
    live: "size = risk$ / stop distance, leverage is an OUTPUT" — repo
    standard, not invented for this round). RISK_PCT = 2%, matching those
    two live books.

DISCIPLINE
- Every edge script built on this harness computes its entry signal and its
  exits.py SeriesCtx SEPARATELY on the TRAIN slice and the VAL slice (fresh,
  independently-sliced, index-reset frames) — never on the full series cut
  after the fact. This is the SAME convention step54/56/58/65 already use
  (their own score()/slice_meta() call run_backtest/build pivots per-slice)
  and is what keeps a pivot near the train/val boundary from silently using
  future data.
- The SEALED final 20% is never loaded by any step150 script. Train+val only.
  A train+val PASS here is evidence the edge's ECONOMICS survive taker costs
  and real structure stops — it is NOT a new sealed verdict. Spending the
  sealed look is Morgan's call, not this round's.
- verdict floor: >=30 train trades, >=8 val trades, positive expectancy BOTH
  windows to earn SURVIVOR (identical floor to every other round in this repo).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest import CostModel
import exits as E

RISK_PCT = 0.02              # repo-standard fixed-fractional risk (daily_pick.py, tradfi_engine.py)
MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8
INITIAL_EQUITY = 10_000.0
ROUND_TRIP_BPS_TASK = 12.0   # Morgan's own thickness-bar definition: taker 6bps x 2 legs
MAX_LEVERAGE = 20.0          # BloFin's own documented ceiling for this desk (tactical.py:
                              # "OWNER DIRECTIVE: minimum 10x, target 20x... every trigger
                              # runs at the max its stop geometry allows under BloFin's
                              # ~4.5% liquidation distance at 20x"). A structure stop can
                              # occasionally sit almost ON entry (a degenerate nearby wick
                              # pivot) -- size=risk$/stop_distance would then demand
                              # absurd, un-tradeable leverage. Capping at the desk's real
                              # ceiling is honest sizing, not a fudge: a real trader would
                              # either skip that trade or size it by the exchange's actual
                              # leverage limit, never by the formula alone.


def split_points(d: pd.DataFrame):
    n = len(d)
    return n, int(n * 0.6), int(n * 0.8)


def mask_to_events(mask: pd.Series, direction) -> list[tuple[int, int]]:
    """Boolean entry mask -> [(bar_idx, direction), ...]. `direction` is
    either a fixed +1/-1 int or a per-bar Series (for combined long+short
    masks where sign varies)."""
    idxs = np.flatnonzero(mask.fillna(False).to_numpy())
    if isinstance(direction, pd.Series):
        dv = direction.to_numpy()
        return [(int(i), int(dv[i])) for i in idxs]
    return [(int(i), int(direction)) for i in idxs]


def run_edge(candles: pd.DataFrame, entries: list[tuple[int, int]],
            stop_builder, target_builder, max_hold_bars: int,
            funding_bps: pd.Series | None = None,
            fill_convention: str = "next_open",
            costs: CostModel | None = None,
            risk_pct: float = RISK_PCT,
            initial_equity: float = INITIAL_EQUITY,
            k: int = 5, atr_n: int = 14, boll_n: int = 20, boll_k: float = 2.0,
            pool_tol_pct: float = 0.1):
    """The one engine every step150 edge script calls, on ONE already-sliced
    (train-only or val-only) candle frame at a time.

    entries : [(signal_bar_idx, direction), ...] — signal_bar_idx is the bar
        whose CLOSE produced the signal. fill_convention="next_open" (the
        repo-standard, used for CHoCH/divergence/trend/RSI3): fills at
        signal_bar_idx+1's OPEN. fill_convention="same_close" (the R45B/
        news-momentum convention, preserved here because it's the ONE
        documented, previously-sealed entry-timing rule, not something
        under test tonight): fills at signal_bar_idx's own CLOSE.
    stop_builder(tc) -> exits.ExitMethod (or None to skip the trade — used
        when no confirmed structure exists yet, "insufficient structure to
        place a real stop" rather than falling back to a swept percentage).
    target_builder(stop_method) -> exits.ExitMethod | None.
    Returns (trades: list[dict], skipped_no_structure: int).
    """
    if costs is None:
        costs = CostModel()          # taker 6bps fee / 1bp spread / 2bp slip — repo default
    candles = candles.reset_index(drop=True)
    s = E.build_series_ctx(candles, k=k, atr_n=atr_n, boll_n=boll_n, boll_k=boll_k,
                           pool_tol_pct=pool_tol_pct)
    o, n = s.o, s.n
    fbps = funding_bps.reset_index(drop=True).to_numpy() if funding_bps is not None else None
    t_idx = pd.DatetimeIndex(candles["timestamp"])
    bar_hours = (float((t_idx[1:] - t_idx[:-1]).total_seconds().min() / 3600)
                if n > 1 else 1.0)
    adverse = (costs.half_spread_bps + costs.slippage_bps) / 10_000
    fee_rate = costs.fee_bps / 10_000

    equity = initial_equity
    trades: list[dict] = []
    busy_until = -1
    skipped_no_structure = 0

    for sig_idx, direction in sorted(entries):
        entry_idx = sig_idx + 1 if fill_convention == "next_open" else sig_idx
        if entry_idx <= busy_until or entry_idx >= n:
            continue
        raw_entry_px = float(o[entry_idx] if fill_convention == "next_open" else s.c[entry_idx])
        entry_fill = raw_entry_px * (1 + direction * adverse)   # TAKER: cross spread+slip

        tc = E.build_trade_ctx(s, entry_idx, entry_fill, direction)
        stop = stop_builder(tc)
        if stop is None:
            skipped_no_structure += 1
            continue
        stop_level = stop.level_fn(tc, entry_idx)
        if stop_level is None:
            skipped_no_structure += 1          # no confirmed structure yet — real trader waits
            continue
        stop_dist_price = abs(entry_fill - stop_level)
        if stop_dist_price <= 0:
            skipped_no_structure += 1
            continue
        stop_dist_frac = stop_dist_price / entry_fill

        if equity <= 0:
            break     # account blown up -- no real exchange lets you keep trading past this
        risk_dollars = risk_pct * equity
        notional = risk_dollars / stop_dist_frac       # SIZE = risk$ / stop distance
        notional = min(notional, MAX_LEVERAGE * equity)   # capped at the desk's real ceiling
        leverage = notional / equity                    # leverage is an OUTPUT (now capped)

        target = target_builder(stop) if target_builder else None
        outcome = E.run_trade(tc, stop, target, max_hold_bars)
        exit_idx = outcome.exit_bar
        raw_exit_px = outcome.exit_price
        exit_fill = raw_exit_px * (1 - direction * adverse)   # TAKER exit too, always

        entry_fee = notional * fee_rate
        exit_notional = notional * exit_fill / entry_fill
        exit_fee = exit_notional * fee_rate

        hold_bars = max(1, exit_idx - entry_idx)
        hold_hours = hold_bars * bar_hours
        funding_dollars = 0.0
        if fbps is not None and exit_idx > entry_idx:
            mr = float(np.nanmean(fbps[entry_idx + 1:exit_idx + 1]))
            if mr == mr:
                funding_dollars = notional * direction * mr / 10_000 * (hold_hours / 8.0)

        gross = direction * (exit_fill / entry_fill - 1) * notional
        pnl = gross - entry_fee - exit_fee - funding_dollars
        equity += pnl

        trades.append(dict(
            entry_idx=entry_idx, exit_idx=exit_idx,
            entry_time=t_idx[entry_idx], exit_time=t_idx[exit_idx],
            direction=direction, entry_price=entry_fill, exit_price=exit_fill,
            stop_price=stop_level, stop_dist_pct=stop_dist_frac * 100,
            notional=notional, leverage=leverage, pnl=pnl,
            reason=outcome.reason, hold_hours=hold_hours,
        ))
        busy_until = exit_idx

    return trades, skipped_no_structure


def trade_stats(trades: list[dict], initial_equity: float = INITIAL_EQUITY) -> dict:
    if not trades:
        return dict(n=0, expectancy=0.0, win_rate=0.0, total_return_pct=0.0,
                   max_dd_pct=0.0, avg_notional=0.0, avg_leverage=0.0, median_hold_h=0.0)
    pnls = np.array([t["pnl"] for t in trades])
    curve = np.concatenate([[initial_equity], initial_equity + np.cumsum(pnls)])
    peaks = np.maximum.accumulate(curve)
    dd = (curve - peaks) / peaks
    return dict(
        n=len(trades), expectancy=float(pnls.mean()), win_rate=float((pnls > 0).mean()),
        total_return_pct=(curve[-1] / initial_equity - 1) * 100,
        max_dd_pct=float(dd.min() * 100),
        avg_notional=float(np.mean([t["notional"] for t in trades])),
        avg_leverage=float(np.mean([t["leverage"] for t in trades])),
        median_hold_h=float(np.median([t["hold_hours"] for t in trades])),
    )


def verdict_for(tr_stats: dict, va_stats: dict) -> str:
    if tr_stats["expectancy"] > 0 and va_stats["expectancy"] > 0:
        if tr_stats["n"] >= MIN_TRAIN_TRADES and va_stats["n"] >= MIN_VAL_TRADES:
            return "SURVIVOR (train+val — sealed look NOT spent)"
        return "INSUFFICIENT-SAMPLE"
    return "FAIL"


def thickness(expectancy_dollars: float, avg_notional: float,
             round_trip_bps: float = ROUND_TRIP_BPS_TASK) -> dict:
    """Edge as % of notional AND as a multiple of round-trip cost. Under 5x
    is a reject (Morgan's evidence bar), stated for BOTH the task's own
    12bps definition (taker 6bps x 2 legs) and this harness's fuller
    CostModel round-trip (fee+half-spread+slippage x2, ~18bps) so nothing
    is flattered by picking the smaller number."""
    if avg_notional <= 0:
        return dict(pct_notional=0.0, mult_12bps=0.0, mult_full_18bps=0.0)
    pct_notional = expectancy_dollars / avg_notional * 100
    cost_12 = avg_notional * round_trip_bps / 10_000
    cost_18 = avg_notional * CostModel().round_trip_bps() / 10_000
    return dict(
        pct_notional=pct_notional,
        mult_12bps=expectancy_dollars / cost_12 if cost_12 else 0.0,
        mult_full_18bps=expectancy_dollars / cost_18 if cost_18 else 0.0,
    )


def chance_baseline(candles: pd.DataFrame, n_events: int, direction_mix: float,
                    stop_builder, target_builder, max_hold_bars: int,
                    funding_bps: pd.Series | None, fill_convention: str,
                    costs: CostModel | None = None, seed: int = 7, draws: int = 100,
                    k: int = 5) -> dict:
    """The dumb-cell control: same event COUNT, random bar placement, random
    direction (direction_mix = fraction long), SAME exit apparatus (stop/
    target/costs) as the real edge. Mean expectancy across `draws` random
    placements = the chance baseline every result here must be judged
    against, per Morgan's evidence bar ('a best cell without it is not a
    finding')."""
    rng = np.random.default_rng(seed)
    n = len(candles)
    lo, hi = k + 5, n - 5          # leave warmup/tail room for pivots + fills
    if hi <= lo or n_events <= 0:
        return dict(mean_exp=0.0, n_draws=0, sample_events=n_events)
    exps = []
    pool = np.arange(lo, hi)
    for _ in range(draws):
        take = min(n_events, len(pool))
        idxs = rng.choice(pool, size=take, replace=False)
        dirs = (rng.random(take) < direction_mix).astype(int) * 2 - 1
        entries = list(zip(idxs.tolist(), dirs.tolist()))
        trades, _ = run_edge(candles, entries, stop_builder, target_builder, max_hold_bars,
                             funding_bps=funding_bps, fill_convention=fill_convention,
                             costs=costs, k=k)
        if trades:
            exps.append(float(np.mean([t["pnl"] for t in trades])))
    return dict(mean_exp=float(np.mean(exps)) if exps else 0.0,
               n_draws=len(exps), sample_events=n_events)


def fmt_stats(label: str, st: dict) -> str:
    return (f"{label}: n={st['n']} exp=${st['expectancy']:+,.2f} "
           f"win%={st['win_rate']*100:.1f} ret%={st['total_return_pct']:+.1f} "
           f"dd%={st['max_dd_pct']:.1f} avg_lev={st.get('avg_leverage', 0):.1f}x "
           f"med_hold_h={st.get('median_hold_h', 0):.1f}")
