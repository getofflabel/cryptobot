"""
step135_exit_variations.py — ROUND 135. EXIT-METHOD ITERATION on the two
edges this program has already validated (R60's RSI2<5 dip-buy and
SMA200-regime membership) — neither has had a real exits.py pass yet,
exactly the gap morgan's mandate calls out as "your best current base to
extend."

Uses exits.py's composable stop/target library (build_series_ctx, TradeCtx,
run_trade, simulate_partial_scale) properly for the first time in this
program's SPX line — R60/R77/step130-133 all used run_backtest's flat
stop_pct/target_pct scalar, never the real ExitMethod composition engine.

BASE SHAPE (unchanged from R60 family 1a, the program's cleanest edge):
  entry: RSI2<5 AND close>SMA200, daily, SPY+ES=F.
  ORIGINAL exit (R60's literal spec): close>SMA5 OR RSI2>65 — reproduced
  here as a plain event ExitMethod (make_event_exit) so it can sit in the
  TARGET slot of run_trade exactly like any other ExitMethod, letting every
  variant below swap ONLY the stop underneath the same original target,
  which is the fair, controlled way to ask "does a real structural/
  trailing stop change the outcome" without also changing what "done"
  means.

VARIANTS TESTED (all vs the R60 baseline, same entries, same original
target):
  1. no stop (reproduces R60's own "stop=none" cell — sanity check the
     harness matches).
  2. stop_atr(1.5) — reproduces R60's "1.5xATR" cell as a second sanity
     check (R60 found this survives; 1.0xATR was the one that killed
     several loose shapes — "give the dip room").
  3. stop_chandelier(3.0) — a RATCHETING ATR trail, never tested on SPX.
  4. stop_structure_trailing() — the ratcheting confirmed-swing floor
     (gold_book.py's LIVE exit shape), never tested on SPX.
  5. stop_breakeven_after_r(stop_atr(1.5), r_multiple=1.0) — move to
     breakeven after +1R, composed on top of the R60-validated 1.5xATR
     stop.
  6. simulate_partial_scale — take half off at 1R, move remainder to
     breakeven, ride the rest to the original target — direct SPX test of
     step99b_exit_research.md's cross-market finding that scaling out
     costs roughly half the profit.

Second base shape: SMA200-regime membership (R60 family 3) — tests whether
a structure-trailing exit beats the plain "stay long while price>SMA200"
continuous-membership rule R60 validated (drawdown-cut case, not
outperformance).

execution="taker". Costs from step130_common.COSTS. No sealed-test look
spent.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import step130_common as C
import exits as X

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", None)


def make_event_exit(name: str, cond_arr: np.ndarray) -> X.ExitMethod:
    def event_fn(tc, i):
        return bool(cond_arr[i]) if i < len(cond_arr) else False
    return X.ExitMethod(name, level_fn=lambda tc, i: None, event_fn=event_fn)


def simulate_dipbuy_exit_variant(d: pd.DataFrame, s_ctx, entries: np.ndarray, exit_cond: np.ndarray,
                                 lo: int, hi: int, stop, target, max_hold_bars: int,
                                 costs) -> C.SimResult:
    """Sequential, no-overlap (matches R60's event_long state machine: a
    new entry signal while already in a trade is ignored). Fill at the
    signal bar's NEXT open (run_backtest's own one-bar-lag convention).
    stop=None means trail-only (target alone can close the trade)."""
    opens = d["open"].to_numpy()
    n = len(d)
    times = pd.DatetimeIndex(d["timestamp"])
    adv = costs._adverse_frac
    trades = []
    i = lo
    while i < hi:
        if not entries[i] or i + 1 >= n:
            i += 1
            continue
        entry_idx = i + 1
        entry_raw = opens[entry_idx]
        tc = X.build_trade_ctx(s_ctx, entry_idx, entry_raw, X.LONG)
        outcome = X.run_trade(tc, stop, target, max_hold_bars)
        exit_raw = outcome.exit_price
        entry_px = entry_raw * (1 + adv)
        exit_px = exit_raw * (1 - adv)
        notional_in = C.INITIAL_EQUITY
        entry_fee = costs.fee(notional_in)
        ret_frac = (exit_px - entry_px) / entry_px
        gross = notional_in * ret_frac
        exit_fee = costs.fee(abs(notional_in + gross))
        pnl = gross - entry_fee - exit_fee
        trades.append(C.SimTrade(times[entry_idx], times[outcome.exit_bar], pnl, outcome.reason))
        i = outcome.exit_bar + 1
    return C.SimResult(trades)


def simulate_dipbuy_partial(d: pd.DataFrame, s_ctx, entries: np.ndarray, lo: int, hi: int,
                            stop, final_target, max_hold_bars: int, costs) -> C.SimResult:
    """Same sequential/no-overlap/one-bar-lag discipline, but uses
    exits.py's simulate_partial_scale (take 50% at 1R, move remainder to
    breakeven, ride the rest to final_target). blended_price() gives the
    size-weighted average fill for the whole position."""
    opens = d["open"].to_numpy()
    n = len(d)
    times = pd.DatetimeIndex(d["timestamp"])
    adv = costs._adverse_frac
    trades = []
    i = lo
    while i < hi:
        if not entries[i] or i + 1 >= n:
            i += 1
            continue
        entry_idx = i + 1
        entry_raw = opens[entry_idx]
        tc = X.build_trade_ctx(s_ctx, entry_idx, entry_raw, X.LONG)
        outcome = X.simulate_partial_scale(tc, stop, final_target, max_hold_bars,
                                           r_multiple=1.0, frac=0.5, move_to_breakeven=True)
        if outcome is None:
            i += 1
            continue
        entry_px = entry_raw * (1 + adv)
        blended_raw = outcome.blended_price()
        exit_px = blended_raw * (1 - adv)
        notional_in = C.INITIAL_EQUITY
        entry_fee = costs.fee(notional_in)
        ret_frac = (exit_px - entry_px) / entry_px
        gross = notional_in * ret_frac
        exit_fee = costs.fee(abs(notional_in + gross)) * len(outcome.legs)   # one fee per leg, both sides
        pnl = gross - entry_fee - exit_fee
        trades.append(C.SimTrade(times[entry_idx], times[outcome.exit_bar], pnl, outcome.reason))
        i = outcome.exit_bar + 1
    return C.SimResult(trades)


def run_dipbuy_exit_variants(frames, meta) -> list[dict]:
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = C.COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        s_ctx = X.build_series_ctx(d, k=5, atr_n=14)
        close = d["close"]
        sma200 = C.sma(close, 200)
        r2 = C.rsi(close, 2)
        entries = ((r2 < 5) & (close > sma200)).fillna(False).to_numpy()
        exit_cond = C.dipbuy_exit_mask(d).fillna(False).to_numpy()
        target = make_event_exit("original_dipbuy_exit(close>SMA5 or RSI2>65)", exit_cond)
        max_hold = 250   # generous cap standing in for R60's true "nocap"

        variants = [
            ("1-no-stop (R60 sanity check)", None),
            ("2-stop_atr(1.5) (R60 sanity check)", X.stop_atr(1.5)),
            ("3-stop_chandelier(3.0)", X.stop_chandelier(3.0)),
            ("4-stop_structure_trailing()", X.stop_structure_trailing()),
            ("5-breakeven_after_1R(atr1.5)", X.stop_breakeven_after_r(X.stop_atr(1.5), 1.0)),
        ]
        for label, stop in variants:
            tr = simulate_dipbuy_exit_variant(d, s_ctx, entries, exit_cond, 0, i_tr, stop, target, max_hold, costs)
            va = simulate_dipbuy_exit_variant(d, s_ctx, entries, exit_cond, i_tr, i_va, stop, target, max_hold, costs)
            rows.append(C.mk_sim_row("dipbuy-exit-variant", label, tag, "1d", tr, va))

        # partial-scale: half off at 1R (R = stop_atr(1.5)'s own distance),
        # remainder to breakeven then rides to the SAME original target.
        tr = simulate_dipbuy_partial(d, s_ctx, entries, 0, i_tr, X.stop_atr(1.5), target, max_hold, costs)
        va = simulate_dipbuy_partial(d, s_ctx, entries, i_tr, i_va, X.stop_atr(1.5), target, max_hold, costs)
        rows.append(C.mk_sim_row("dipbuy-exit-variant", "6-partial_scale(50%@1R,BE,ride)", tag, "1d", tr, va))
    return rows


# ===========================================================================
# SMA200-regime + structure-trailing exit (second base shape)
# ===========================================================================

def run_regime_exit_variant(frames, meta) -> list[dict]:
    """R60 family 3's baseline: continuous membership (long the whole time
    price>SMA200, no independent 'exit' beyond the regime flipping). This
    tests substituting exits.py's stop_structure_trailing() as an EARLY-OUT
    on top of the SAME entry condition, riding out early on a confirmed
    swing-low break rather than waiting for the SMA200 cross itself, then
    re-entering the next time the regime condition is true again."""
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = C.COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        s_ctx = X.build_series_ctx(d, k=5, atr_n=14)
        close = d["close"]
        sma200 = C.sma(close, 200)
        regime_up = (close > sma200).fillna(False).to_numpy()
        # entries: the day the regime FLIPS from down to up (fresh cross)
        entries = regime_up & ~np.roll(regime_up, 1)
        entries[0] = False
        regime_down_event = (~regime_up).astype(bool)
        baseline_target = make_event_exit("regime flips below SMA200", regime_down_event)
        max_hold = 2000

        for label, stop in (
            ("A-continuous-membership (R60 baseline, no early stop)", None),
            ("B-structure_trailing early-out", X.stop_structure_trailing()),
        ):
            tr = simulate_dipbuy_exit_variant(d, s_ctx, entries, regime_down_event, 0, i_tr,
                                              stop, baseline_target, max_hold, costs)
            va = simulate_dipbuy_exit_variant(d, s_ctx, entries, regime_down_event, i_tr, i_va,
                                              stop, baseline_target, max_hold, costs)
            rows.append(C.mk_sim_row("regime-exit-variant", label, tag, "1d", tr, va))
    return rows


# ===========================================================================
# main
# ===========================================================================

def main():
    print("=" * 78)
    print("ROUND 135 — EXIT-METHOD ITERATION ON THE TWO ALREADY-VALIDATED SPX EDGES")
    print("=" * 78)

    frames = {tag: {} for tag in ("SPY", "ES")}
    meta = {tag: {} for tag in ("SPY", "ES")}
    for tag in ("SPY", "ES"):
        frames[tag]["1d"] = C.load_symbol(tag, "1d")
        meta[tag]["1d"] = C.span_meta(frames[tag]["1d"])

    cols = ["config", "symbol", "tr_n", "tr_exp", "tr_win%", "va_n", "va_exp", "va_win%", "verdict"]

    print("\nPART A — RSI2<5 dip-buy, stop variants (same entries, same original target)")
    a_df = pd.DataFrame(run_dipbuy_exit_variants(frames, meta))
    print(a_df[cols].to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\nPART B — SMA200-regime, structure-trailing early-out vs continuous membership")
    b_df = pd.DataFrame(run_regime_exit_variant(frames, meta))
    print(b_df[cols].to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    a_df.to_csv("step135_table_partA_dipbuy_exits.csv", index=False)
    b_df.to_csv("step135_table_partB_regime_exits.csv", index=False)

    print("\nDone. No sealed-test window touched.")
    return a_df, b_df


if __name__ == "__main__":
    main()
