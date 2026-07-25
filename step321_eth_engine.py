"""
step321_eth_engine.py — ROUND 320/321 shared engine for the Ethereum
shape-port round.

This is step150_common.run_edge with two changes and nothing else:
  1. it accepts an ALREADY-BUILT exits.py SeriesCtx, so the same frame's
     pivot/ATR arrays can be reused across dozens of grid cells and across
     the random-entry control draws instead of being rebuilt every call
     (rebuilding them for every draw is what makes an honest control
     unaffordable, and an unaffordable control is one that does not get
     run);
  2. it takes a warm-up offset, so a window can carry real indicator and
     pivot history from BEFORE its own first bar without any bar after the
     window ever being visible. Nothing reads forward: pivots are confirmed
     k bars late by construction and averages only look back.

Everything that decides money is unchanged from step150_common:
  - market orders both ways, always (execution is never the cheaper
    limit-order-that-waits);
  - the stop is a chart level from exits.py, never a swept percentage;
  - position size = dollars risked / distance to the stop, so leverage is
    an OUTPUT, capped at the desk's real 20x ceiling;
  - real funding, signed the way a real perpetual-futures account pays it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest import CostModel
import exits as E

RISK_PCT = 0.02
MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8
INITIAL_EQUITY = 10_000.0
MAX_LEVERAGE = 20.0


def split_points(n: int):
    return int(n * 0.6), int(n * 0.8)


def run_edge_ctx(candles: pd.DataFrame, s: "E.SeriesCtx",
                 entries: list[tuple[int, int]],
                 stop_builder, target_builder, max_hold_bars: int,
                 funding_bps: np.ndarray | None = None,
                 lo_idx: int = 0, hi_idx: int | None = None,
                 costs: CostModel | None = None,
                 risk_pct: float = RISK_PCT,
                 initial_equity: float = INITIAL_EQUITY):
    """entries are (signal_bar_index, direction) on the FULL frame. Only
    entries whose fill bar falls inside [lo_idx, hi_idx) are taken; a trade
    that opens inside the window is allowed to finish naturally."""
    if costs is None:
        costs = CostModel()
    n = s.n
    if hi_idx is None:
        hi_idx = n
    o = s.o
    t_idx = pd.DatetimeIndex(candles["timestamp"])
    bar_hours = float((t_idx[1:] - t_idx[:-1]).total_seconds().min() / 3600) if n > 1 else 1.0
    adverse = (costs.half_spread_bps + costs.slippage_bps) / 10_000
    fee_rate = costs.fee_bps / 10_000

    equity = initial_equity
    trades: list[dict] = []
    busy_until = -1
    skipped = 0

    for sig_idx, direction in entries:
        entry_idx = sig_idx + 1
        if entry_idx < lo_idx or entry_idx >= hi_idx or entry_idx <= busy_until or entry_idx >= n:
            continue
        raw = float(o[entry_idx])
        entry_fill = raw * (1 + direction * adverse)          # market order, costs more
        tc = E.build_trade_ctx(s, entry_idx, entry_fill, direction)
        stop = stop_builder(tc)
        if stop is None:
            skipped += 1
            continue
        stop_level = stop.level_fn(tc, entry_idx)
        if stop_level is None:
            skipped += 1               # no confirmed chart structure yet: a real trader waits
            continue
        dist = abs(entry_fill - stop_level)
        if dist <= 0:
            skipped += 1
            continue
        stop_dist_frac = dist / entry_fill
        if equity <= 0:
            break
        notional = min(risk_pct * equity / stop_dist_frac, MAX_LEVERAGE * equity)
        leverage = notional / equity

        target = target_builder(stop) if target_builder else None
        outcome = E.run_trade(tc, stop, target, max_hold_bars)
        exit_fill = float(outcome.exit_price) * (1 - direction * adverse)

        entry_fee = notional * fee_rate
        exit_fee = notional * exit_fill / entry_fill * fee_rate
        hold_bars = max(1, outcome.exit_bar - entry_idx)
        hold_hours = hold_bars * bar_hours
        funding_dollars = 0.0
        if funding_bps is not None and outcome.exit_bar > entry_idx:
            mr = float(np.nanmean(funding_bps[entry_idx + 1:outcome.exit_bar + 1]))
            if mr == mr:
                funding_dollars = notional * direction * mr / 10_000 * (hold_hours / 8.0)
        gross = direction * (exit_fill / entry_fill - 1) * notional
        pnl = gross - entry_fee - exit_fee - funding_dollars
        equity += pnl
        trades.append(dict(entry_idx=entry_idx, exit_idx=outcome.exit_bar,
                           entry_time=t_idx[entry_idx], exit_time=t_idx[outcome.exit_bar],
                           direction=direction, entry_price=entry_fill, exit_price=exit_fill,
                           stop_price=stop_level, stop_dist_pct=stop_dist_frac * 100,
                           notional=notional, leverage=leverage, pnl=pnl,
                           reason=outcome.reason, hold_hours=hold_hours))
        busy_until = outcome.exit_bar
    return trades, skipped


def stats(trades, initial_equity: float = INITIAL_EQUITY) -> dict:
    if not trades:
        return dict(n=0, exp=0.0, win=0.0, ret=0.0, dd=0.0, avg_notional=0.0,
                    avg_lev=0.0, med_hold_h=0.0, med_stop_pct=0.0)
    p = np.array([t["pnl"] for t in trades])
    curve = np.concatenate([[initial_equity], initial_equity + np.cumsum(p)])
    peaks = np.maximum.accumulate(curve)
    return dict(n=len(trades), exp=float(p.mean()), win=float((p > 0).mean()),
                ret=(curve[-1] / initial_equity - 1) * 100,
                dd=float(((curve - peaks) / peaks).min() * 100),
                avg_notional=float(np.mean([t["notional"] for t in trades])),
                avg_lev=float(np.mean([t["leverage"] for t in trades])),
                med_hold_h=float(np.median([t["hold_hours"] for t in trades])),
                med_stop_pct=float(np.median([t["stop_dist_pct"] for t in trades])))


def verdict(tr: dict, va: dict) -> str:
    if tr["n"] < MIN_TRAIN_TRADES or va["n"] < MIN_VAL_TRADES:
        return "NOT ENOUGH TRADES"
    if tr["exp"] > 0 and va["exp"] > 0:
        return "SURVIVES (first 60% + middle 20%; final slice untouched)"
    return "DIES"


def thickness(exp_dollars: float, avg_notional: float) -> dict:
    """How big the average profit per trade is next to the cost of trading.
    Reported two ways so nothing is flattered by picking the smaller cost:
    the exchange fee alone on both fills (0.06% x 2 = 0.12% of the full
    position size), and the full round trip this repo charges everywhere
    (fee + half the quoted spread + slippage, on both fills = 0.18%)."""
    if avg_notional <= 0:
        return dict(pct_of_position=0.0, x_fees_only=0.0, x_full_cost=0.0)
    return dict(pct_of_position=exp_dollars / avg_notional * 100,
                x_fees_only=exp_dollars / (avg_notional * 12.0 / 10_000),
                x_full_cost=exp_dollars / (avg_notional * CostModel().round_trip_bps() / 10_000))


def random_entry_control(candles, s, n_train_entries, n_val_entries,
                         stop_builder, target_builder, max_hold_bars,
                         funding_bps, i_tr, i_va, warm, draws=30, seed=321):
    """Compared against entering at random times: the same NUMBER of long
    entries, placed at random bars inside the same two windows, run through
    the identical stop/target/cost machinery. Reports how often pure luck
    would have cleared the bar this round uses to say an idea survived."""
    rng = np.random.default_rng(seed)
    hits, tr_exps, va_exps = 0, [], []
    for _ in range(draws):
        tr_idx = rng.choice(np.arange(warm, i_tr - 2), size=min(n_train_entries, max(1, i_tr - warm - 3)), replace=False)
        va_idx = rng.choice(np.arange(i_tr, i_va - 2), size=min(n_val_entries, max(1, i_va - i_tr - 3)), replace=False)
        ent_tr = sorted((int(i), 1) for i in tr_idx)
        ent_va = sorted((int(i), 1) for i in va_idx)
        t1, _ = run_edge_ctx(candles, s, ent_tr, stop_builder, target_builder, max_hold_bars,
                             funding_bps, lo_idx=warm, hi_idx=i_tr)
        t2, _ = run_edge_ctx(candles, s, ent_va, stop_builder, target_builder, max_hold_bars,
                             funding_bps, lo_idx=i_tr, hi_idx=i_va)
        a, b = stats(t1), stats(t2)
        tr_exps.append(a["exp"])
        va_exps.append(b["exp"])
        if a["exp"] > 0 and b["exp"] > 0:
            hits += 1
    return dict(draws=draws, luck_pass_rate=hits / draws,
                mean_train_exp=float(np.mean(tr_exps)), mean_val_exp=float(np.mean(va_exps)))
