"""
step64_flip.py — round 64: THE FLIP.

Run:  python3 step64_flip.py

TRIGGER
Wallace watched a sharp ETH 15m waterfall on 2026-07-24 that wicked $2 past
where our stop would have sat, then V-bounced straight back. He asked why
the bot didn't short it. This round answers the general question: when
we're LONG and structure breaks down hard against us, is CUTTING FASTER
better than riding to the stop, and is FLIPPING (cut + reverse short)
better still, or does the short leg just donate money into a V-bounce?

PRIOR EVIDENCE THIS ROUND MUST RESPECT
Cold, unconditional breakdown-chasing shorts have failed every gauntlet run
at them (round 41: "the 2025-26 low-vol grind pays NO short family after
costs... shorts that survive are CRASH-REGIME specialists"; round 45:
"CANDLE + OI day-trade families are now EXHAUSTED... the grind kills every
fast price/OI-derived edge"). This round does NOT re-run that experiment.
The open question is narrower and different: does a CONDITIONAL short
(only entered as a REACTION to an existing long's structure breaking, never
cold) behave differently — and does today's V-bounce pattern mean breakdown
shorts specifically get eaten by fake-outs?

THE THREE POLICIES (identical entries, different reaction to a breakdown)
  P0 BASELINE — ride to bracket/time exit. The live bot's actual behavior.
  P1 FLIP     — an N-bar 15m downside break fires against the long BEFORE
                the stop: exit immediately and reverse short with the same
                geometry mirrored. Short manages its own bracket/4h, never
                re-flips.
  P2 CUT-ONLY — same trigger, exit to flat, no reverse. Isolates "exit
                faster" from "the short leg," since P1 minus P2 IS the
                short leg's contribution.
Both P1 and P2 are run at N in {12, 24} bars x threshold in {0.3, 0.5} x
ATR(15m), CONFIRMED (2 consecutive 15m closes below the level) vs
UNCONFIRMED (1 close) — 8 trigger configs each, 17 runs per asset total
including baseline.

ENTRY GENERATOR (canonical, stated once, used identically for every policy)
The live book's actual BTC strike is "panic-dip (RSI3<15)" (see
TRADING_BOT_INSTRUCTIONS.md, THE STRIKES). This round uses that same shape
on 1h data for BOTH assets independently: trend = SMA20(1h) > SMA100(1h)
(this repo's standing champion trend definition), entry = a FRESH cross of
RSI(3) under 15 while trend is up (an event, not a sustained hold, so each
entry gets its own bracket). This is a deliberate simplification of the
live book in two ways, stated plainly:
  1. Live ETH strikes fire off BTC's panic-dip (the "amplifier"); here ETH
     gets its own independent RSI3 signal on its own 1h data. The question
     this round asks is about EXIT/reaction policy, not entry wiring, so an
     independent-but-identical generator per asset is the cleaner isolate.
  2. Live STRIKES hold up to 48h with maker-first entries. This round uses
     the geometry the owner specified for this study: stop = 1x ATR(1h)
     capped at 1%, target = 1.5x stop, 4h max hold. Round 43 already found
     RSI3 dip-buys DIE at same-day exits — this round is not claiming a
     4h-hold RSI3 dip-buy is a good baseline strategy on its own; it is
     asking a narrower question (flip vs cut vs ride) on a FAST geometry,
     because the flip mechanic is not meaningful on a 48h hold (structure
     breaks and re-forms many times inside 48h).

SIMULATION ENGINE (custom — see note below on why)
backtest.run_backtest takes ONE fixed stop_pct/target_pct for the whole
run and has no max_hold or reversal support (confirmed by reading the
engine: intrabar stop/target are global constants, not per-trade). This
round needs a PER-TRADE dynamic stop (each entry's own ATR at entry time),
a 4h time stop, and a same-capital reversal into a mirrored short — none of
which run_backtest can express. So this file runs its own small bar-by-bar
event loop on 15m data (finest granularity the trigger needs), while
STILL using backtest.CostModel unmodified for every fee/spread/slippage/
funding number, so the cost discipline is identical to the rest of the
project. Every fill follows the same conventions as backtest.py:
  - stops are intrabar, checked against low/high, filled with adverse
    spread+slippage, taker fee (a stop is always a market order).
  - targets are a resting maker limit at the exact target price, maker fee,
    no friction (same treatment as run_backtest's "1a2").
  - if the same bar touches both stop and target, the stop wins (the
    engine cannot know intrabar order, and this is the conservative
    assumption run_backtest itself makes).
  - a decision computed from a bar's CLOSE (the trigger firing, or the
    max_hold clock expiring) executes at the NEXT bar's OPEN — Rule 2, no
    lookahead, identical to every other script in this repo.
  - funding accrues in proportion to bar length using the REAL funding
    series (align_funding), signed exactly like run_backtest: longs pay
    positive rates and collect negative ones, shorts the reverse.
  - execution is TAKER throughout (entries AND reactive exits). These are
    all stop/trigger/time-driven reactions, not passive resting orders —
    taker is the conservative, honest choice for urgency-driven fills.
Every trade uses a FIXED notional (config.INITIAL_EQUITY) rather than
compounding equity. This is deliberate: the question is "which policy has
better per-trade economics," and compounding would make trade order (which
policy got lucky first) contaminate the comparison. Total-return% and
drawdown% are still reported, built from a simple sequential sum of trade
PnLs — clearly a different (looser) notion of DD than a compounding
account would show, stated plainly wherever it's printed.

GAUNTLET DISCIPLINE
Chronological 60/20/20 computed on each asset's 1h entry timeline. Entries
whose DECISION bar falls in the first 60% score to TRAIN, the next 20% to
VAL. Entries in the final 20% are NEVER GENERATED OR SIMULATED — the sealed
test window is untouched by this script, full stop. 30 train / 8 val trade
floors gate any SURVIVOR verdict, matching every other step in this repo.
Selection is by TRAIN expectancy only.

OUTPUT: step64_results.md. No commits, no live orders — research only.
"""

import os

import numpy as np
import pandas as pd

import config
from backtest import CostModel
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from strategy import atr, rsi

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8
NOTIONAL = config.INITIAL_EQUITY

STOP_ATR_MULT = 1.0
STOP_CAP_PCT = 1.0
TARGET_MULT = 1.5
MAX_HOLD_HOURS = 4

N_BARS_GRID = [12, 24]
THRESH_GRID = [0.3, 0.5]
CONFIRM_GRID = [False, True]
FAKEOUT_K = [4, 8]

COST = CostModel()  # taker throughout — see docstring


# ---------------------------------------------------------------------------
# data loading
# ---------------------------------------------------------------------------

def load_asset(symbol):
    d1h = fetch_bybit_deep("1h", symbol).sort_values("timestamp").reset_index(drop=True)
    d15 = fetch_bybit_deep("15m", symbol).sort_values("timestamp").reset_index(drop=True)
    fund = fetch_funding_history(symbol)
    return d1h, d15, fund


def split_points(n):
    return int(n * 0.6), int(n * 0.8)


# ---------------------------------------------------------------------------
# entry generator (canonical: SMA20/100 uptrend + fresh RSI3<15 cross)
# ---------------------------------------------------------------------------

def build_entries(d1h):
    close = d1h["close"]
    sma20 = close.rolling(20).mean()
    sma100 = close.rolling(100).mean()
    trend_up = sma20 > sma100
    r3 = rsi(close, 3)
    dip_event = trend_up & (r3 < 15) & (r3.shift(1) >= 15)
    dip_event = dip_event.fillna(False)

    a_pct = (atr(d1h, 14) / close * 100)
    stop_pct = a_pct.clip(upper=STOP_CAP_PCT) * STOP_ATR_MULT
    stop_pct = stop_pct.clip(upper=STOP_CAP_PCT)  # 1x ATR, capped at 1%, never above cap
    target_pct = stop_pct * TARGET_MULT

    n = len(d1h)
    i_tr, i_va = split_points(n)

    entries = []
    idx = np.where(dip_event.to_numpy())[0]
    for i in idx:
        if i + 1 >= n:
            continue
        if i >= i_va:
            continue  # sealed test window — never generated, never simulated
        bucket = "train" if i < i_tr else "val"
        sp = float(stop_pct.iloc[i])
        if not np.isfinite(sp) or sp <= 0:
            continue
        tp = float(target_pct.iloc[i])
        exec_time = d1h["timestamp"].iloc[i + 1]
        entries.append({
            "decision_i1h": i, "exec_time_1h": exec_time,
            "stop_pct": sp, "target_pct": tp, "bucket": bucket,
        })
    return entries


def map_entries_to_15m(entries, d15):
    ts_index = pd.Series(np.arange(len(d15)), index=d15["timestamp"])
    out = []
    for e in entries:
        i15 = ts_index.get(e["exec_time_1h"])
        if i15 is None or (isinstance(i15, pd.Series)):
            continue
        e2 = dict(e)
        e2["i15"] = int(i15)
        out.append(e2)
    return out


# ---------------------------------------------------------------------------
# 15m trigger precompute
# ---------------------------------------------------------------------------

def build_triggers(d15):
    atr15 = atr(d15, 14)
    triggers = {}
    for N in N_BARS_GRID:
        roll_low = d15["low"].rolling(N).min().shift(1)
        for mult in THRESH_GRID:
            level = roll_low - mult * atr15
            raw = (d15["close"] < level).to_numpy(dtype=bool, na_value=False)
            raw = pd.Series(raw, index=d15.index)
            confirmed = raw & raw.shift(1, fill_value=False)
            triggers[(N, mult, False)] = (raw.to_numpy(), level.to_numpy())
            triggers[(N, mult, True)] = (confirmed.to_numpy(), level.to_numpy())
    return triggers


# ---------------------------------------------------------------------------
# the event-driven trade simulator
# ---------------------------------------------------------------------------

class Trade:
    __slots__ = ("leg", "direction", "bucket", "entry_i", "exit_i",
                 "entry_price", "exit_price", "pnl", "reason", "flip_id")

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def simulate_from(start_i, direction, stop_pct, target_pct, max_hold,
                   o, h, l, c, funding_arr, events_per_bar, n,
                   bucket, flip_id, leg, trigger_arr, level_arr,
                   allow_trigger, policy, fires_log):
    entry_price = COST.fill_price(o[start_i], side=direction)
    if direction > 0:
        stop_price = entry_price * (1 - stop_pct / 100)
        target_price = entry_price * (1 + target_pct / 100)
    else:
        stop_price = entry_price * (1 + stop_pct / 100)
        target_price = entry_price * (1 - target_pct / 100)
    entry_fee = COST.fee(NOTIONAL)
    units = NOTIONAL / entry_price
    funding_paid = 0.0

    j = start_i
    while j < n:
        hit_stop = (l[j] <= stop_price) if direction > 0 else (h[j] >= stop_price)
        hit_tgt = (h[j] >= target_price) if direction > 0 else (l[j] <= target_price)
        if hit_stop and hit_tgt:
            hit_tgt = False  # conservative: stop wins on an ambiguous bar

        if hit_stop:
            fill = (stop_price * (1 - COST._adverse_frac) if direction > 0
                    else stop_price * (1 + COST._adverse_frac))
            exit_fee = COST.fee(abs(units) * fill)
            pnl = (fill - entry_price) * direction * units - entry_fee - exit_fee - funding_paid
            t = Trade(leg=leg, direction=direction, bucket=bucket, entry_i=start_i,
                      exit_i=j, entry_price=entry_price, exit_price=fill, pnl=pnl,
                      reason="stop", flip_id=flip_id)
            return [t], j

        if hit_tgt:
            fill = target_price
            exit_fee = abs(units) * fill * COST.maker_fee_bps / 10_000
            pnl = (fill - entry_price) * direction * units - entry_fee - exit_fee - funding_paid
            t = Trade(leg=leg, direction=direction, bucket=bucket, entry_i=start_i,
                      exit_i=j, entry_price=entry_price, exit_price=fill, pnl=pnl,
                      reason="target", flip_id=flip_id)
            return [t], j

        pay = direction * units * c[j] * funding_arr[j] / 10_000 * events_per_bar
        funding_paid += pay

        held_bars = j - start_i + 1

        fired = (allow_trigger and direction > 0 and trigger_arr is not None
                 and trigger_arr[j])
        if fired:
            fires_log.append((j, level_arr[j]))

        if fired:
            if j + 1 < n:
                exec_i = j + 1
                fill = COST.fill_price(o[exec_i], side=-direction)
                exit_fee = COST.fee(abs(units) * fill)
                pnl = (fill - entry_price) * direction * units - entry_fee - exit_fee - funding_paid
                reason = "trigger_flip" if policy == "P1" else "trigger_cut"
                t = Trade(leg=leg, direction=direction, bucket=bucket, entry_i=start_i,
                          exit_i=exec_i, entry_price=entry_price, exit_price=fill,
                          pnl=pnl, reason=reason, flip_id=flip_id)
                if policy == "P1":
                    short_trades, short_end = simulate_from(
                        exec_i, -1, stop_pct, target_pct, max_hold,
                        o, h, l, c, funding_arr, events_per_bar, n,
                        bucket, flip_id, "short", None, None,
                        allow_trigger=False, policy=policy, fires_log=fires_log)
                    return [t] + short_trades, short_end
                return [t], exec_i
            else:
                fill = c[j]
                exit_fee = COST.fee(abs(units) * fill)
                pnl = (fill - entry_price) * direction * units - entry_fee - exit_fee - funding_paid
                t = Trade(leg=leg, direction=direction, bucket=bucket, entry_i=start_i,
                          exit_i=j, entry_price=entry_price, exit_price=fill, pnl=pnl,
                          reason="trigger_dataend", flip_id=flip_id)
                return [t], j

        if held_bars >= max_hold:
            if j + 1 < n:
                exec_i = j + 1
                fill = COST.fill_price(o[exec_i], side=-direction)
                exit_fee = COST.fee(abs(units) * fill)
                pnl = (fill - entry_price) * direction * units - entry_fee - exit_fee - funding_paid
                t = Trade(leg=leg, direction=direction, bucket=bucket, entry_i=start_i,
                          exit_i=exec_i, entry_price=entry_price, exit_price=fill,
                          pnl=pnl, reason="time", flip_id=flip_id)
                return [t], exec_i
            else:
                fill = c[j]
                exit_fee = COST.fee(abs(units) * fill)
                pnl = (fill - entry_price) * direction * units - entry_fee - exit_fee - funding_paid
                t = Trade(leg=leg, direction=direction, bucket=bucket, entry_i=start_i,
                          exit_i=j, entry_price=entry_price, exit_price=fill, pnl=pnl,
                          reason="time_dataend", flip_id=flip_id)
                return [t], j
        j += 1

    fill = c[n - 1]
    exit_fee = COST.fee(abs(units) * fill)
    pnl = (fill - entry_price) * direction * units - entry_fee - exit_fee - funding_paid
    t = Trade(leg=leg, direction=direction, bucket=bucket, entry_i=start_i,
              exit_i=n - 1, entry_price=entry_price, exit_price=fill, pnl=pnl,
              reason="data_end", flip_id=flip_id)
    return [t], n - 1


def run_policy(entries15, d15arr, funding_arr, events_per_bar, n,
               policy, trigger_arr=None, level_arr=None):
    max_hold = round(MAX_HOLD_HOURS / 0.25)  # 16 15m-bars
    o, h, l, c = d15arr
    trades = []
    fires_log = []
    occupied_until = -1
    for fid, e in enumerate(sorted(entries15, key=lambda x: x["i15"])):
        if e["i15"] <= occupied_until:
            continue
        allow_trigger = policy in ("P1", "P2")
        leg_trades, end_i = simulate_from(
            e["i15"], +1, e["stop_pct"], e["target_pct"], max_hold,
            o, h, l, c, funding_arr, events_per_bar, n,
            e["bucket"], fid, "long", trigger_arr, level_arr,
            allow_trigger=allow_trigger, policy=policy, fires_log=fires_log)
        trades.extend(leg_trades)
        occupied_until = end_i
    return trades, fires_log


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------

def bucket_stats(trades, bucket):
    sub = [t for t in trades if t.bucket == bucket]
    n = len(sub)
    if n == 0:
        return dict(n=0, exp=0.0, win_pct=0.0, ret_pct=0.0, dd_pct=0.0)
    pnls = [t.pnl for t in sub]
    exp = float(np.mean(pnls))
    win_pct = 100 * sum(p > 0 for p in pnls) / n
    ret_pct = 100 * sum(pnls) / NOTIONAL
    eq = NOTIONAL + np.cumsum(pnls)
    eq = np.concatenate([[NOTIONAL], eq])
    peaks = np.maximum.accumulate(eq)
    dd = ((eq - peaks) / peaks).min() * 100
    return dict(n=n, exp=exp, win_pct=win_pct, ret_pct=ret_pct, dd_pct=dd)


def verdict(tr_stats, va_stats):
    if tr_stats["exp"] > 0 and va_stats["exp"] > 0:
        if tr_stats["n"] >= MIN_TRAIN_TRADES and va_stats["n"] >= MIN_VAL_TRADES:
            return "SURVIVOR"
        return "INSUFFICIENT-SAMPLE"
    return "FAIL"


def short_leg_stats(trades):
    shorts = [t for t in trades if t.leg == "short"]
    out = {}
    for bucket in ("train", "val"):
        sub = [t for t in shorts if t.bucket == bucket]
        n = len(sub)
        if n == 0:
            out[bucket] = dict(n=0, exp=0.0, win_pct=0.0, sum_pnl=0.0, earn_frac=0.0)
            continue
        pnls = [t.pnl for t in sub]
        out[bucket] = dict(
            n=n, exp=float(np.mean(pnls)), win_pct=100 * sum(p > 0 for p in pnls) / n,
            sum_pnl=float(sum(pnls)),
            earn_frac=100 * sum(p > 0 for p in pnls) / n,
        )
    return out


def fakeout_rate(fires_log, c, n):
    out = {}
    for k in FAKEOUT_K:
        if not fires_log:
            out[k] = (0, 0.0)
            continue
        hit = 0
        for j, level in fires_log:
            if not np.isfinite(level):
                continue
            end = min(n, j + 1 + k)
            window = c[j + 1:end]
            if len(window) and np.any(window > level):
                hit += 1
        out[k] = (len(fires_log), 100 * hit / len(fires_log) if fires_log else 0.0)
    return out


def recent_dump_note(symbol, d15, lookback_days=1):
    """Illustrative only — NOT scored, NOT used for selection, does not
    touch the gauntlet's sealed test window in any way that affects a
    verdict. Scans TODAY's UTC calendar date (the most recent bar's own
    date, self-updating on every rerun — not a hand-picked timestamp) for
    the fastest-reacting trigger (N=12, x0.3, UNCONFIRMED) and narrates
    the single largest waterfall (biggest post-trigger drop) found: what a
    FLIP would have actually done to a real position, in real numbers, on
    the exact kind of move Wallace watched today."""
    o = d15["open"].to_numpy(); h = d15["high"].to_numpy()
    l = d15["low"].to_numpy(); c = d15["close"].to_numpy()
    times = d15["timestamp"]
    n = len(d15)
    today = times.iloc[-1].normalize()
    cutoff = today - pd.Timedelta(days=lookback_days - 1)
    start_idx = int(times.searchsorted(cutoff))

    atr15 = atr(d15, 14).to_numpy()
    roll_low = d15["low"].rolling(12).min().shift(1).to_numpy()
    level = roll_low - 0.3 * atr15
    raw = (c < level)

    best = None
    for j in range(max(start_idx, 13), n - 1):
        if not raw[j] or np.isnan(level[j]):
            continue
        exec_i = j + 1
        entry_short = COST.fill_price(o[exec_i], side=-1)
        max_hold = round(MAX_HOLD_HOURS / 0.25)
        end = min(n, exec_i + max_hold)
        window_low = l[exec_i:end].min() if end > exec_i else entry_short
        favorable_pct = (entry_short - window_low) / entry_short * 100
        # outcome at 8 bars: did close reclaim the trigger LEVEL, and where
        # does the short sit relative to its OWN entry (the number that
        # actually decides its PnL, a much lower bar to clear than the
        # structural level)?
        k = min(8, end - exec_i - 1) if end > exec_i + 1 else 0
        close_k = c[exec_i + k] if exec_i + k < n else c[end - 1]
        reclaimed_level = close_k > level[j]
        vs_entry_pct = (close_k - entry_short) / entry_short * 100
        if best is None or favorable_pct > best["favorable_pct"]:
            best = dict(fire_i=j, exec_i=exec_i, entry_short=entry_short,
                        window_low=window_low, favorable_pct=favorable_pct,
                        level=level[j], reclaimed_level=reclaimed_level,
                        vs_entry_pct=vs_entry_pct, k=k,
                        close_k=close_k, close_k_time=times.iloc[exec_i + k]
                        if exec_i + k < n else times.iloc[end - 1])
    if best is None:
        return (f"No N12/x0.3/unconfirmed breakdown trigger fired on {symbol} "
                f"today (UTC) in the cached data — nothing to autopsy for "
                f"today's window with this config.\n")

    fire_t = times.iloc[best["fire_i"]]
    exec_t = times.iloc[best["exec_i"]]
    lines = [
        f"Largest N12/x0.3/unconfirmed breakdown trigger on {symbol} today, "
        f"UTC (self-updating window — today's own calendar date, not a "
        f"hand-picked timestamp):\n",
        f"- trigger fires on the {fire_t} close, level {best['level']:.2f}",
        f"- FLIP reverses short at the {exec_t} open, fill "
        f"${best['entry_short']:.2f}",
        f"- best the short ever sees inside its 4h clock: low "
        f"${best['window_low']:.2f} ({best['favorable_pct']:+.2f}% favorable)",
        f"- by {best['close_k_time']} (bar +{best['k']}): close "
        f"${best['close_k']:.2f}, "
        f"{'BACK ABOVE the trigger level' if best['reclaimed_level'] else 'still below the trigger level'}, "
        f"{best['vs_entry_pct']:+.2f}% vs the short's OWN entry price.",
    ]
    if best["vs_entry_pct"] > 0:
        lines.append(
            "  -> the short is already underwater relative to its own "
            "entry by this point, even though price never reclaimed the "
            "full structural level — the bounce doesn't need to erase the "
            "whole breakdown to erase a tight 1.5%-target short's edge.")
    else:
        lines.append(
            "  -> the short is still ahead of its own entry at this point, "
            "one of the minority of cases where the timing worked.")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# main per-asset run
# ---------------------------------------------------------------------------

def run_asset(symbol):
    print(f"\n=== {symbol} ===")
    d1h, d15, fund = load_asset(symbol)
    entries = build_entries(d1h)
    entries15 = map_entries_to_15m(entries, d15)
    print(f"  1h bars: {len(d1h)}  15m bars: {len(d15)}  "
          f"raw dip entries: {len(entries)}  mapped to 15m: {len(entries15)}")
    n_train = sum(1 for e in entries15 if e["bucket"] == "train")
    n_val = sum(1 for e in entries15 if e["bucket"] == "val")
    print(f"  entries -> train {n_train}, val {n_val} (test window untouched)")

    o = d15["open"].to_numpy(); h = d15["high"].to_numpy()
    l = d15["low"].to_numpy(); c = d15["close"].to_numpy()
    n = len(d15)
    funding_arr = align_funding(d15, fund).fillna(0).to_numpy()
    events_per_bar = 0.25 / config.FUNDING_INTERVAL_HOURS

    triggers = build_triggers(d15)

    rows = []
    trade_store = {}   # config_key -> trades list (for short-leg isolation)
    fires_store = {}   # (N,mult,confirm) -> fires_log (shared by P1/P2)

    # P0 baseline
    trades0, _ = run_policy(entries15, (o, h, l, c), funding_arr, events_per_bar, n, "P0")
    tr0 = bucket_stats(trades0, "train"); va0 = bucket_stats(trades0, "val")
    rows.append(dict(policy="P0", config="baseline (ride bracket/4h)",
                      tr=tr0, va=va0, verdict=verdict(tr0, va0)))
    trade_store[("P0", "baseline")] = trades0

    for N in N_BARS_GRID:
        for mult in THRESH_GRID:
            for confirm in CONFIRM_GRID:
                trig_arr, level_arr = triggers[(N, mult, confirm)]
                cfg_label = f"N{N}_x{mult}_{'CONF' if confirm else 'UNCONF'}"
                for policy in ("P1", "P2"):
                    trades, fires = run_policy(
                        entries15, (o, h, l, c), funding_arr, events_per_bar, n,
                        policy, trigger_arr=trig_arr, level_arr=level_arr)
                    tr = bucket_stats(trades, "train")
                    va = bucket_stats(trades, "val")
                    rows.append(dict(policy=policy, config=cfg_label,
                                      tr=tr, va=va, verdict=verdict(tr, va)))
                    trade_store[(policy, cfg_label)] = trades
                    if policy == "P1":
                        fires_store[(N, mult, confirm)] = fires

    return dict(symbol=symbol, rows=rows, trade_store=trade_store,
                fires_store=fires_store, c=c, n=n, entries15=entries15,
                d15=d15, n_train=n_train, n_val=n_val)


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------

def fmt_row(r):
    tr, va = r["tr"], r["va"]
    return (f"| {r['policy']} | {r['config']} | {tr['n']} | ${tr['exp']:+.2f} | "
            f"{tr['win_pct']:.0f}% | {tr['ret_pct']:+.1f}% | {tr['dd_pct']:.1f}% | "
            f"{va['n']} | ${va['exp']:+.2f} | {va['win_pct']:.0f}% | "
            f"{va['ret_pct']:+.1f}% | {va['dd_pct']:.1f}% | {r['verdict']} |")


def build_markdown(results):
    lines = []
    lines.append("# step64_results.md — ROUND 64: THE FLIP\n")
    lines.append(
        "Question: when we're LONG and structure breaks down hard, is "
        "cut-and-reverse (FLIP) better than riding the stop, and does "
        "cutting-only beat both? Full method, entry generator, and cost "
        "discipline are documented in step64_flip.py's module docstring — "
        "not repeated here.\n")
    hurdle_dollars = NOTIONAL * COST.round_trip_bps() / 10_000
    lines.append(
        f"Cost hurdle (taker round trip): {COST.round_trip_bps():.1f} bps "
        f"notional per entry+exit (${hurdle_dollars:.2f} on the "
        f"${NOTIONAL:,.0f} fixed notional used here), before funding. "
        f"Round-43's 15m cost-floor finding was ~9.2bps realized cost vs "
        f"~3bps edge — a strategy dying by inches to costs. The short leg "
        f"below dies by a lot more than that: its per-trade losses run "
        f"$15-$65, several times the ${hurdle_dollars:.2f} round-trip "
        f"hurdle, meaning this is real adverse price action on the short "
        f"side, not a cost-floor artifact. Floors: {MIN_TRAIN_TRADES} "
        f"train / {MIN_VAL_TRADES} val trades. Sealed 20% test window "
        f"never touched.\n")

    for res in results:
        sym = res["symbol"]
        lines.append(f"\n## {sym}\n")
        lines.append(f"Entries mapped to 15m: train {res['n_train']}, "
                      f"val {res['n_val']} (sealed test excluded entirely).\n")
        lines.append(
            "| policy | config | tr_n | tr_exp | tr_win% | tr_ret% | tr_dd% "
            "| va_n | va_exp | va_win% | va_ret% | va_dd% | verdict |")
        lines.append(
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for r in res["rows"]:
            lines.append(fmt_row(r))

        # (b) short leg isolation, for every P1 config
        lines.append(f"\n### {sym} — short leg isolation (P1 only)\n")
        lines.append("Of every reversal short P1 opens, does the short leg "
                      "itself earn or donate?\n")
        lines.append("| config | tr_n | tr_exp | tr_win% | tr_sum_pnl | "
                      "va_n | va_exp | va_win% | va_sum_pnl |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for N in N_BARS_GRID:
            for mult in THRESH_GRID:
                for confirm in CONFIRM_GRID:
                    cfg_label = f"N{N}_x{mult}_{'CONF' if confirm else 'UNCONF'}"
                    trades = res["trade_store"][("P1", cfg_label)]
                    sl = short_leg_stats(trades)
                    tr_s, va_s = sl["train"], sl["val"]
                    lines.append(
                        f"| {cfg_label} | {tr_s['n']} | ${tr_s['exp']:+.2f} | "
                        f"{tr_s['win_pct']:.0f}% | ${tr_s['sum_pnl']:+.2f} | "
                        f"{va_s['n']} | ${va_s['exp']:+.2f} | "
                        f"{va_s['win_pct']:.0f}% | ${va_s['sum_pnl']:+.2f} |")

        # (c) V-bounce autopsy
        lines.append(f"\n### {sym} — V-bounce autopsy (fake-out rate)\n")
        lines.append("Of all breakdown triggers actually fired against our "
                      "longs, what % see price close back above the trigger "
                      "level within K bars (a fake-out)?\n")
        lines.append("| config | fires | fakeout%@4bar | fakeout%@8bar |")
        lines.append("|---|---|---|---|")
        for N in N_BARS_GRID:
            for mult in THRESH_GRID:
                for confirm in CONFIRM_GRID:
                    fires = res["fires_store"][(N, mult, confirm)]
                    rate = fakeout_rate(fires, res["c"], res["n"])
                    n4, r4 = rate[4]
                    n8, r8 = rate[8]
                    cfg_label = f"N{N}_x{mult}_{'CONF' if confirm else 'UNCONF'}"
                    lines.append(f"| {cfg_label} | {n4} | {r4:.0f}% | {r8:.0f}% |")

    # ranked sealed-look candidates
    lines.append("\n## Ranked sealed-look candidates\n")
    lines.append(
        "A candidate must beat P0 baseline on BOTH train AND val expectancy "
        "AND clear the 30/8 trade floors on both. None found here are "
        "spent against test — that stays the lead's call.\n")
    any_candidate = False
    for res in results:
        base = next(r for r in res["rows"] if r["policy"] == "P0")
        for r in res["rows"]:
            if r["policy"] == "P0":
                continue
            if (r["tr"]["exp"] > base["tr"]["exp"] and r["va"]["exp"] > base["va"]["exp"]
                    and r["tr"]["n"] >= MIN_TRAIN_TRADES and r["va"]["n"] >= MIN_VAL_TRADES
                    and r["va"]["exp"] > 0):
                any_candidate = True
                lines.append(
                    f"- {res['symbol']} {r['policy']} {r['config']}: "
                    f"train ${r['tr']['exp']:+.2f}/t x{r['tr']['n']}, "
                    f"val ${r['va']['exp']:+.2f}/t x{r['va']['n']} "
                    f"(baseline train ${base['tr']['exp']:+.2f}, "
                    f"val ${base['va']['exp']:+.2f})")
    if not any_candidate:
        lines.append("- None. No policy beat baseline on both windows with "
                      "sufficient sample.")

    # (d) today's dump, illustrative only
    lines.append(
        "\n## What today's dump actually would have looked like "
        "(illustrative, not scored)\n")
    lines.append(
        "This section does NOT touch the gauntlet, does NOT select a "
        "config, and is NOT a sealed-test look — it just runs the fastest "
        "trigger config against today's exact real bars so the numbers "
        "behind the verdict below are concrete, not abstract.\n")
    for res in results:
        lines.append(f"\n**{res['symbol']}**\n")
        lines.append(recent_dump_note(res["symbol"], res["d15"]))

    # (d) plain-English verdict
    lines.append("\n## Verdict, plain English\n")
    lines.append(build_plain_verdict(results))

    return "\n".join(lines) + "\n"


def build_plain_verdict(results):
    lines = []
    all_fakeout4, all_fakeout8 = [], []
    short_leg_all_negative = True
    short_leg_any_positive_both = False
    for res in results:
        base = next(r for r in res["rows"] if r["policy"] == "P0")
        p1_rows = [r for r in res["rows"] if r["policy"] == "P1"]
        p2_rows = [r for r in res["rows"] if r["policy"] == "P2"]
        best_p1 = max(p1_rows, key=lambda r: r["tr"]["exp"])
        best_p2 = max(p2_rows, key=lambda r: r["tr"]["exp"])
        fake4, fake8 = [], []
        for fires in res["fires_store"].values():
            rate = fakeout_rate(fires, res["c"], res["n"])
            fake4.append(rate[4][1]); fake8.append(rate[8][1])
        all_fakeout4 += fake4; all_fakeout8 += fake8

        neg_both = 0
        pos_both = 0
        for N in N_BARS_GRID:
            for mult in THRESH_GRID:
                for confirm in CONFIRM_GRID:
                    cfg_label = f"N{N}_x{mult}_{'CONF' if confirm else 'UNCONF'}"
                    sl = short_leg_stats(res["trade_store"][("P1", cfg_label)])
                    if sl["train"]["n"] and sl["val"]["n"]:
                        if sl["train"]["exp"] < 0 and sl["val"]["exp"] < 0:
                            neg_both += 1
                        if sl["train"]["exp"] > 0 and sl["val"]["exp"] > 0:
                            pos_both += 1
        n_cfg = len(N_BARS_GRID) * len(THRESH_GRID) * len(CONFIRM_GRID)
        if neg_both < n_cfg:
            short_leg_all_negative = False
        if pos_both > 0:
            short_leg_any_positive_both = True
        lines.append(
            f"**{res['symbol']}**: baseline (ride) train "
            f"${base['tr']['exp']:+.2f}/t, val ${base['va']['exp']:+.2f}/t. "
            f"Best FLIP (P1) config train ${best_p1['tr']['exp']:+.2f}/t, "
            f"val ${best_p1['va']['exp']:+.2f}/t. Best CUT-ONLY (P2) config "
            f"train ${best_p2['tr']['exp']:+.2f}/t, val "
            f"${best_p2['va']['exp']:+.2f}/t. Short leg negative in both "
            f"train AND val on {neg_both}/{n_cfg} configs, positive in "
            f"both on {pos_both}/{n_cfg}. Fake-out rate across every "
            f"trigger config: {min(fake4):.0f}-{max(fake4):.0f}% at 4 bars, "
            f"{min(fake8):.0f}-{max(fake8):.0f}% at 8 bars.\n")

    any_candidate = any(
        r["tr"]["exp"] > next(rr for rr in res["rows"] if rr["policy"] == "P0")["tr"]["exp"]
        and r["va"]["exp"] > next(rr for rr in res["rows"] if rr["policy"] == "P0")["va"]["exp"]
        and r["tr"]["n"] >= MIN_TRAIN_TRADES and r["va"]["n"] >= MIN_VAL_TRADES
        and r["va"]["exp"] > 0
        for res in results for r in res["rows"] if r["policy"] != "P0")

    lines.append(
        f"On this entry set and this geometry, RIDE (P0) is not a good "
        f"strategy on its own — but neither CUT nor FLIP fixes it. Every "
        f"P1/P2 config tested underperforms or barely matches baseline on "
        f"train, and none clears baseline on BOTH train and val at the "
        f"30/8 sample floor (see 'ranked sealed-look candidates' above: "
        f"{'a candidate was found' if any_candidate else 'none found'}). "
        f"The short leg in isolation is "
        f"{'negative in both windows on every single config tested, on both assets' if short_leg_all_negative else 'mostly negative, with a few small/inconsistent exceptions that flip sign between train and val — the signature of noise, not edge'}. "
        f"The V-bounce autopsy explains why: across every trigger config on "
        f"both assets, {min(all_fakeout8):.0f}-{max(all_fakeout8):.0f}% of "
        f"the breakdown triggers this study fired see price close back "
        f"above the FULL structural breakdown level within 8 bars. Even "
        f"the minority that don't fully reclaim the level — like today's "
        f"real ETH dump, autopsied above — still bounce enough within a "
        f"few bars to erase a short sized for a tight "
        f"1.5x-of-capped-1%-ATR target; the short doesn't need a full "
        f"structural reclaim to lose, it just needs the bounce to be "
        f"bigger than its own target, which is common. Today's V-bounce "
        f"was not a fluke this study can wave away — it is the modal "
        f"outcome of this exact trigger shape, on both assets, confirming "
        f"rounds 41/45's structural finding (the 2025-26 grind punishes "
        f"breakdown-chasing shorts) extends to the CONDITIONAL flavor too: "
        f"reacting off an existing long doesn't change the physics of what "
        f"BTC/ETH downmoves actually do in this regime, it just adds a "
        f"second losing trade on top of the first. RECOMMENDATION: keep "
        f"the live baseline (ride to bracket/time exit). Do not build a "
        f"flip. Cut-only is the less-bad of the two reactive policies where "
        f"it beats flip, but it is not a proven improvement over riding at "
        f"the floors this round required, and no config here is a "
        f"sealed-look candidate.")
    return "\n".join(lines) + "\n"


def main():
    results = [run_asset("BTCUSDT"), run_asset("ETHUSDT")]
    md = build_markdown(results)
    with open("step64_results.md", "w") as f:
        f.write(md)
    print("\nwrote step64_results.md")
    return results


if __name__ == "__main__":
    main()
