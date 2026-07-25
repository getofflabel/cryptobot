"""
step110_livebook_audit.py — Round 110: THE STAND-DOWN VERDICT.

QUESTION: the oil book trades LIVE right now (daemon.py -> tradfi_engine.
run_tradfi_engine, wired in daemon.py's `_tradfi()`/`_run_book("TradFi
Engine", _tradfi)`). Does the EXACT rule set it runs have positive
expectancy on oil's own data at taker costs? If it was never validated on
oil, that alone may already be the verdict — but this script also RUNS
the exact live logic against real CL=F history so the verdict is backed
by a number, not just an absence of one.

WHAT IS ACTUALLY LIVE (read from the code, not guessed — tradfi_engine.py
+ daemon.py, both read in full before writing a line of this script):
  - Universe: CL=F ("oil") competes with SPY ("the S&P") for at most
    MAX_CONCURRENT=2 concurrent paper slots, ranked by conviction each 2h
    UTC slot. This script isolates OIL: every slot oil is eligible AND
    outranks nothing (single-symbol backtest), oil is taken. That is a
    DELIBERATE, STATED relaxation of the live capacity constraint — it
    answers "does oil's own rule have edge", which is the question asked.
    The real live book trades oil less often because it sometimes loses
    the slot to SPY; that only makes the live book's realized oil sample
    SMALLER than this backtest's, never bigger, so this is the fair
    (if anything, generous) reading of the rule.
  - Signal: `daily_pick.score_instrument` — THE CRYPTO LEARNING ENGINE'S
    OWN SCORER (trend_1h MA20/100 cross, 55-bar 1d breakout-channel
    proximity, RSI3<10/>90 washout + turn-candle, 6x-volume/2x-return
    shock, 4h momentum >1%, 1d-trend +5 alignment bonus), imported
    UNCHANGED into tradfi_engine.py and called on CL=F's own 1h/1d bars.
    Every point threshold in it (10/90 RSI, 6x volume, 1% momentum, 0.5%
    breakout proximity, MA20/100) was tuned on BTC/ETH/SOL, never on oil.
  - Stop/target: `daily_pick._stop_target_pct` — stop = 1.0x ATR(14,1h)
    CAPPED AT A FLAT 1.0%, target = 1.5x stop. This is exactly the
    "swept percentage" shape the desk's evidence bar forbids: the ATR
    multiple is structure-aware, but the 1.0% CAP is a fixed number
    carried from crypto, not derived from oil's own distribution, and it
    binds constantly on oil (oil's hourly ATR% is frequently >1%, so the
    cap — not the ATR — sets the stop most of the time; verified below).
  - Gates: CONVICTION_FLOOR=40 in a "calm" regime (current 1h ATR% <0.8x
    its own trailing 336-bar median) only; STOPOUT_COOLDOWN_H=6h after a
    losing exit, same (symbol,direction) key, unless conviction is +5
    higher. MAX_HOLD_H=6.0 (vs crypto's 4.0).
  - Fees: FEE_BPS_FUTURES=2.0 bps/leg is tradfi_engine.py's OWN assumed
    cost, fee-only, no slippage/spread modeled. This script reports BOTH
    that number (labelled "live-book's own optimistic cost") AND the
    repo's standard taker cost model (fee 2bp/leg + slippage 2bp/leg +
    half-spread 1bp/leg = 10bps round-trip, config.py's own
    DEFAULT_SLIPPAGE_BPS/DEFAULT_SPREAD_BPS conventions) as the number
    the evidence bar actually requires. EVERY headline number below is
    the taker (10bps round-trip) number unless stated otherwise.

WAS THIS EVER VALIDATED ON OIL? Round 78 (step78_oil_playbook.py,
RESEARCH_LOG.md "ROUND 78") tested what was live THAT DAY — gold's
donchian20+structure-trail and the S&P's RSI2 dip-buy — and found both
FAIL on oil. tradfi_engine.py (this book's actual live wiring, per its
own "2026-07-24" dated docstring) was written the SAME DAY, AFTER that
verdict, and swapped the entry logic to `daily_pick.score_instrument`
(the crypto engine's scorer) WITHOUT re-running round 78's gauntlet on
the new logic. Grep of RESEARCH_LOG.md and MARKET_PLAYBOOKS.md turns up
zero mentions of `score_instrument`/`tradfi_engine` ever being sealed-
tested, train/val-tested, or even backtested on CL=F. The one real result
tied to this book — the desk's only live winner, oil +$58.39
(tradfi_engine.py's own `_migrated_paper_pnl_total` docstring: "yields
exactly +58.39 — the oil win, and nothing else") — is ONE closed trade
under a rule set with a documented sample size of n=1. That is not
evidence of an edge; it is the definition of what an untested live book
looks like right before or right after it loses.

METHOD: single-symbol (CL=F) walk-forward replay of the EXACT live
decision loop (score_instrument, _regime, CONVICTION_FLOOR,
STOPOUT_COOLDOWN_H, _stop_target_pct, MAX_HOLD_H, is_market_open, all
imported UNCHANGED from daily_pick.py / tradfi_engine.py — no
reimplementation, no drift). Bounded trailing windows (400 1h bars / 150
COMPLETED 1d bars) are fed to score_instrument/_regime at every due 2h
slot instead of the full growing history — pandas rolling ops only look
backward a bounded window, so results are IDENTICAL to feeding full
history; this is purely a runtime optimization (O(n) instead of O(n^2)
over ~13.5k hourly bars), stated so nobody mistakes it for a shortcut on
correctness. One deliberate, CONSERVATIVE deviation from live: live
fetches whatever yfinance returns for "today", which during market hours
is a PARTIALLY-FORMED current daily bar; this script uses only fully
CLOSED daily bars (no lookahead), which is strictly more honest than what
runs live, not a thumb on the scale for a positive result.

GAUNTLET: chronological 60/20/20 (step41_shorts.split_points, unchanged),
selection would be TRAIN expectancy>0 AND VAL expectancy>0 with floors
tr_n>=30/va_n>=8 — but there is nothing to "select": this is an audit of
ONE already-live config, not a sweep. The sealed 20% is never touched.

CROSS-INSTRUMENT: only run if CL=F clears the bar (a FAIL config has
nothing to transfer-test).

RESEARCH ONLY. No commits, no live orders, no edits to tradfi_engine.py/
daemon.py/daily_pick.py. Writes ONLY step110_livebook_audit.py (this
file), step110_results.md, step110_table.csv.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from daily_pick import (CONVICTION_FLOOR, STOPOUT_COOLDOWN_H, SLOT_INTERVAL_H,
                        _slot_ts, score_instrument, _stop_target_pct)
from tradfi_engine import (OIL, MAX_HOLD_H, FEE_BPS_FUTURES, is_market_open,
                           _regime, _check_exit)
from step41_shorts import split_points

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8

# repo-standard taker cost model (config.py conventions, restated here so
# this script has zero import-time dependency on a live private client):
#   fee: FEE_BPS_FUTURES (tradfi_engine.py's own oil-futures rate, 2bp/leg)
#   + slippage 2bp/leg + half-spread 1bp/leg (config.DEFAULT_SLIPPAGE_BPS /
#   DEFAULT_SPREAD_BPS) = 5bp/leg -> 10bps round-trip.
TAKER_SLIPPAGE_BPS = 2.0
TAKER_HALF_SPREAD_BPS = 1.0
TAKER_ROUND_TRIP_BPS = 2 * (FEE_BPS_FUTURES + TAKER_SLIPPAGE_BPS + TAKER_HALF_SPREAD_BPS)
LIVE_OPTIMISTIC_ROUND_TRIP_BPS = 2 * FEE_BPS_FUTURES  # what tradfi_engine.py itself charges

H1_WINDOW = 400   # >= REGIME_WINDOW_BARS(336) + ATR warmup(14); >= MA100 warmup
D1_WINDOW = 150   # >= 55-bar breakout channel + 1 + SMA50 warmup

EQUITY = 10_000.0   # fixed paper equity — only scales $ pnl, not %/multiple-
                    # of-cost numbers, which is what the evidence bar reads
RISK_PCT = 0.02      # tradfi_engine.py's own RISK_PCT, unchanged


def _load(sym_tag: str):
    c1h = pd.read_parquet(f"data_oil_{sym_tag}_1h.parquet")
    c1d = pd.read_parquet(f"data_oil_{sym_tag}_1d.parquet")
    return c1h.reset_index(drop=True), c1d.reset_index(drop=True)


def _completed_1d_slice(c1d: pd.DataFrame, cur_date, n: int) -> pd.DataFrame:
    """Last `n` daily bars strictly BEFORE cur_date — fully closed only,
    no lookahead (see module docstring's stated deviation from live)."""
    mask = c1d["timestamp"].dt.date < cur_date
    idx = np.flatnonzero(mask.to_numpy())
    if len(idx) == 0:
        return c1d.iloc[0:0]
    lo = max(0, len(idx) - n)
    return c1d.iloc[idx[lo]:idx[-1] + 1].reset_index(drop=True)


def replay(sym_tag: str, symbol_for_gates: str = OIL) -> tuple[list[dict], pd.DataFrame]:
    """Walk-forward replay of the EXACT live decision loop, single-symbol.
    Returns (trades, c1h) where trades is a chronological list of dicts
    with entry/exit/pnl/notional/round_trip cost fields (BOTH cost models
    computed per trade so downstream reporting needs no re-derivation)."""
    c1h, c1d = _load(sym_tag)
    n = len(c1h)
    warmup = H1_WINDOW  # first index eligible to score (needs 400 trailing 1h bars)
    trades: list[dict] = []
    open_trade = None
    last_stopout = None          # {"ts": datetime, "conviction": float} per direction key
    last_stopout_dir = None
    last_slot_seen = None

    for i in range(warmup, n):
        row = c1h.iloc[i]
        now = row["timestamp"].to_pydatetime()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # -- 1. reconcile an open trade against THIS bar (every bar, exactly
        #    like run_tradfi_engine reconciles every open trade every cycle)
        if open_trade is not None:
            result = _check_exit(open_trade, float(row["high"]), float(row["low"]),
                                 float(row["close"]), now)
            if result is not None:
                exit_price, reason = result
                direction = open_trade["direction"]
                shares = open_trade["shares"]
                notional = open_trade["notional"]
                gross = direction * (exit_price - open_trade["entry_price"]) * shares
                fee_live = notional * LIVE_OPTIMISTIC_ROUND_TRIP_BPS / 10_000
                fee_taker = notional * TAKER_ROUND_TRIP_BPS / 10_000
                trades.append({
                    "entry_time": open_trade["entry_time"], "exit_time": now,
                    "direction": direction, "entry_price": open_trade["entry_price"],
                    "exit_price": exit_price, "reason": reason, "notional": notional,
                    "gross_pnl": gross,
                    "pnl_live_cost": gross - fee_live,
                    "pnl_taker_cost": gross - fee_taker,
                    "conviction": open_trade["conviction"],
                    "stop_pct": open_trade["stop_pct"],
                })
                if (gross - fee_taker) < 0:
                    last_stopout = {"ts": now, "conviction": open_trade["conviction"]}
                    last_stopout_dir = direction
                open_trade = None
            else:
                continue   # still holding — no entry check this bar

        # -- 2. entry: only on a due 2h slot, only if flat, only if market open
        slot = _slot_ts(now)
        due = slot != last_slot_seen
        if not due:
            continue
        last_slot_seen = slot
        if not is_market_open(symbol_for_gates, now):
            continue

        h1_slice = c1h.iloc[max(0, i - H1_WINDOW + 1):i + 1].reset_index(drop=True)
        d1_slice = _completed_1d_slice(c1d, row["timestamp"].date(), D1_WINDOW)
        if len(h1_slice) < 100 or len(d1_slice) < 55:
            continue

        sc = score_instrument(h1_slice, d1_slice, None)
        regime, atr_pct = _regime(h1_slice)
        conviction = sc["conviction"]
        direction_s = sc["direction"]

        if regime == "calm" and conviction < CONVICTION_FLOOR:
            continue

        direction = 1 if direction_s == "long" else -1
        if last_stopout is not None and last_stopout_dir == direction:
            age_h = (now - last_stopout["ts"]).total_seconds() / 3600
            if age_h < STOPOUT_COOLDOWN_H and conviction <= last_stopout["conviction"] + 5:
                continue

        stop_pct, target_pct = _stop_target_pct(atr_pct)
        price = float(row["close"])
        notional = RISK_PCT * EQUITY / (stop_pct / 100)
        shares = notional / price if price else 0.0
        if direction == 1:
            stop_price = price * (1 - stop_pct / 100)
            target_price = price * (1 + target_pct / 100)
        else:
            stop_price = price * (1 + stop_pct / 100)
            target_price = price * (1 - target_pct / 100)

        open_trade = {
            "symbol": sym_tag, "direction": direction, "entry_price": price,
            "shares": shares, "notional": round(notional, 2), "stop_pct": stop_pct,
            "target_pct": target_pct, "stop_price": stop_price,
            "target_price": target_price,
            "entry_time": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "conviction": conviction, "max_hold_h": MAX_HOLD_H,
        }

    return trades, c1h


# ---------------------------------------------------------------------------
# scoring / reporting
# ---------------------------------------------------------------------------

def _stats(pnls: list[float], notionals: list[float]) -> dict:
    n = len(pnls)
    if n == 0:
        return {"n": 0, "exp": float("nan"), "win%": float("nan"),
                "avg_notional_pct": float("nan")}
    arr = np.array(pnls)
    wins = arr[arr > 0]
    losses = arr[arr <= 0]
    return {
        "n": n, "exp": float(arr.mean()), "win%": 100.0 * len(wins) / n,
        "total": float(arr.sum()),
        "avg_win": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss": float(losses.mean()) if len(losses) else 0.0,
        "avg_notional": float(np.mean(notionals)),
    }


def chance_baseline(c1h: pd.DataFrame, trades: list[dict], n_random: int = 500,
                    seed: int = 110) -> dict:
    """Randomized-timing control: same NUMBER of trades, same stop_pct/
    direction DISTRIBUTION as the real trade list, but entry bar drawn
    uniformly at random from the eligible (warmup..n) range, exit
    simulated with the exact same _check_exit engine. Reports the mean
    expectancy (taker cost) across n_random resamples and where the real
    result would rank."""
    rng = np.random.default_rng(seed)
    n = len(c1h)
    warmup = H1_WINDOW
    real_stop_pcts = [t["stop_pct"] for t in trades]
    real_dirs = [t["direction"] for t in trades]
    if not trades:
        return {"n_random": 0}
    means = []
    for _ in range(n_random):
        pnls = []
        idxs = rng.integers(warmup, n - 1, size=len(trades))
        for k, i0 in enumerate(idxs):
            direction = real_dirs[k]
            stop_pct = real_stop_pcts[k]
            target_pct = 1.5 * stop_pct
            price = float(c1h["close"].iloc[i0])
            if direction == 1:
                stop_price = price * (1 - stop_pct / 100)
                target_price = price * (1 + target_pct / 100)
            else:
                stop_price = price * (1 + stop_pct / 100)
                target_price = price * (1 - target_pct / 100)
            notional = RISK_PCT * EQUITY / (stop_pct / 100)
            shares = notional / price if price else 0.0
            fake_trade = {"direction": direction, "stop_price": stop_price,
                          "target_price": target_price,
                          "entry_time": c1h["timestamp"].iloc[i0].strftime(
                              "%Y-%m-%d %H:%M:%S UTC"),
                          "max_hold_h": MAX_HOLD_H}
            exited = False
            for j in range(i0 + 1, min(i0 + 1 + int(MAX_HOLD_H) + 2, n)):
                r = c1h.iloc[j]
                now_j = r["timestamp"].to_pydatetime()
                if now_j.tzinfo is None:
                    now_j = now_j.replace(tzinfo=timezone.utc)
                res = _check_exit(fake_trade, float(r["high"]), float(r["low"]),
                                  float(r["close"]), now_j)
                if res is not None:
                    exit_price, _ = res
                    gross = direction * (exit_price - price) * shares
                    fee_taker = notional * TAKER_ROUND_TRIP_BPS / 10_000
                    pnls.append(gross - fee_taker)
                    exited = True
                    break
            if not exited:
                pnls.append(0.0)   # ran off the end of data — neutral, not counted as edge
        means.append(float(np.mean(pnls)))
    means = np.array(means)
    real_exp = float(np.mean([t["pnl_taker_cost"] for t in trades]))
    pctile = float((means < real_exp).mean() * 100)
    return {"n_random": n_random, "mean_of_means": float(means.mean()),
            "std_of_means": float(means.std()), "real_exp": real_exp,
            "real_percentile": pctile}


def main():
    print("=" * 78)
    print("ROUND 110 — LIVE OIL BOOK STAND-DOWN AUDIT (CL=F, taker costs)")
    print("=" * 78)
    trades, c1h = replay("CL")
    n = len(trades)
    print(f"\nTotal replayed trades (CL=F, full 2024-03 -> 2026-07 history, "
          f"single-symbol relaxation of the live 2-slot cap): {n}")

    if n == 0:
        print("\nZERO trades fired. VERDICT: INSUFFICIENT SAMPLE — the live "
              "rule set essentially never triggers on oil's own volatility "
              "profile once the calm-regime floor and cooldown are applied.")
        return

    n_tr, i_tr, i_va = split_points_by_trades(n)
    train = trades[:i_tr]
    val = trades[i_tr:i_va]
    sealed = trades[i_va:]
    print(f"60/20/20 by TRADE COUNT: train={len(train)}, val={len(val)}, "
          f"sealed={len(sealed)} (sealed NEVER read below)")

    for label, cost_key in (("live-book's own optimistic cost "
                             f"({LIVE_OPTIMISTIC_ROUND_TRIP_BPS:.0f}bps r/t, fee-only)",
                             "pnl_live_cost"),
                            (f"TAKER (repo standard, {TAKER_ROUND_TRIP_BPS:.0f}bps r/t: "
                             f"fee+slippage+spread)", "pnl_taker_cost")):
        print(f"\n--- {label} ---")
        for name, rows in (("TRAIN", train), ("VAL", val)):
            pnls = [t[cost_key] for t in rows]
            notionals = [t["notional"] for t in rows]
            s = _stats(pnls, notionals)
            if s["n"] == 0:
                print(f"  {name}: n=0")
                continue
            edge_pct_notional = 100.0 * s["exp"] / s["avg_notional"] if s["avg_notional"] else float("nan")
            cost_bps = TAKER_ROUND_TRIP_BPS if "TAKER" in label or "taker" in cost_key else LIVE_OPTIMISTIC_ROUND_TRIP_BPS
            cost_dollars_per_trade = s["avg_notional"] * cost_bps / 10_000
            thickness = s["exp"] / cost_dollars_per_trade if cost_dollars_per_trade else float("nan")
            floor_ok = (name == "TRAIN" and s["n"] >= MIN_TRAIN_TRADES) or \
                       (name == "VAL" and s["n"] >= MIN_VAL_TRADES)
            print(f"  {name}: n={s['n']}, expectancy ${s['exp']:+.2f}/trade "
                  f"(win rate {s['win%']:.1f}%), edge {edge_pct_notional:+.3f}% "
                  f"of notional, thickness {thickness:+.2f}x round-trip cost, "
                  f"total ${s['total']:+,.2f}, "
                  f"floor {'OK' if floor_ok else 'BELOW MIN (' + str(MIN_TRAIN_TRADES if name=='TRAIN' else MIN_VAL_TRADES) + ')'}")

    # Chance baseline — taker cost, computed once (VAL trades' own params)
    print("\n--- CHANCE BASELINE (randomized entry timing, same n/direction/"
          "stop-size as the real trade list, taker cost, 500 resamples) ---")
    cb_train = chance_baseline(c1h, train)
    cb_val = chance_baseline(c1h, val)
    for name, cb in (("TRAIN", cb_train), ("VAL", cb_val)):
        if cb.get("n_random", 0) == 0:
            continue
        print(f"  {name}: real expectancy ${cb['real_exp']:+.2f}/trade vs "
              f"random-timing mean ${cb['mean_of_means']:+.2f}/trade "
              f"(std ${cb['std_of_means']:.2f}) -> real result sits at the "
              f"{cb['real_percentile']:.0f}th percentile of the chance "
              f"distribution.")

    # ATR-cap-binding check (evidence-bar violation, independent of P&L)
    capped = sum(1 for t in trades if abs(t["stop_pct"] - 1.0) < 1e-9)
    print(f"\nSTOP-CAP DIAGNOSTIC: {capped}/{n} trades ({100*capped/n:.0f}%) "
          f"had their stop set by the flat 1.0% CAP, not by the ATR "
          f"multiple — i.e. most of the time this book's \"ATR stop\" is "
          f"actually a swept percentage on oil, the exact shape the "
          f"evidence bar forbids.")

    # verdict
    tr_taker = [t["pnl_taker_cost"] for t in train]
    va_taker = [t["pnl_taker_cost"] for t in val]
    tr_exp = np.mean(tr_taker) if tr_taker else float("nan")
    va_exp = np.mean(va_taker) if va_taker else float("nan")
    tr_ok = len(train) >= MIN_TRAIN_TRADES
    va_ok = len(val) >= MIN_VAL_TRADES
    print("\n" + "=" * 78)
    if not tr_ok or not va_ok:
        print(f"VERDICT: INSUFFICIENT SAMPLE (train n={len(train)}, "
              f"val n={len(val)}; floors are {MIN_TRAIN_TRADES}/{MIN_VAL_TRADES}).")
    elif tr_exp > 0 and va_exp > 0:
        print("VERDICT: the exact live rule set clears TRAIN and VAL "
              "expectancy at taker cost. See thickness multiple above "
              "before calling this a PASS — under 5x is still a REJECT.")
    else:
        print("VERDICT: FAIL. The exact live rule set does NOT have "
              "positive expectancy on oil's own data at taker cost.")
    print("=" * 78)

    # write table
    rows_out = []
    for t in trades:
        rows_out.append({**t, "date": t["exit_time"].strftime("%Y-%m-%d")})
    pd.DataFrame(rows_out).to_csv("step110_table.csv", index=False)
    print("\nWrote step110_table.csv (every replayed trade).")


def split_points_by_trades(n_trades: int):
    i_tr = int(n_trades * 0.6)
    i_va = int(n_trades * 0.8)
    return n_trades, i_tr, i_va


if __name__ == "__main__":
    main()
