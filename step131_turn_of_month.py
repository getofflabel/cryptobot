"""
step131_turn_of_month.py — ROUND 131. DELIVERABLE 2: turn-of-month, built
into a real, testable strategy (not just re-confirming the seasonality
stat).

R60 family 5 flagged turn-of-month (TOM) as the strongest untapped signal
anywhere in this program: t=2.43 vs rest-of-month's t=1.65, ~3x the mean
daily return, but explicitly "report-only, no strategy built" — the R60
write-up's own closing line names two natural next tests: "turn-of-month
timing overlaid on the family-1 dip-buy entries, or a standalone TOM long."
This script builds BOTH plus a structural-stop variant.

TOM WINDOW DEFINITION (reused VERBATIM from R60's own family5_seasonality,
via step130_common.tom_flag — same window that produced t=2.43, not a
redefinition): the classic Xu-McConnell window — the last trading day of
the month, plus the first 3 trading days of the next month (4 trading days
per occurrence, ~19% of all trading days).

THREE STRATEGIES
  A. STANDALONE TOM LONG, plain calendar hold (no stop) — signal=1 during
     the window, flat otherwise, run through run_backtest directly (a pure
     calendar rule needs no lookahead guard beyond the standard one-bar
     fill lag; see run_signal()'s docstring for the exact shift used).
  B. STANDALONE TOM LONG + STRUCTURAL STOP — same window, but a custom
     same-window simulator (SimTrade/SimResult) enters at the FIRST TOM
     day's own open and exits at whichever comes first: a chart-structure
     stop (exits.py stop_structure(k=5,n_back=1), evaluated once at entry)
     or the LAST TOM day's own close. Tests whether a real stop improves
     or hurts the calendar edge (R60's own dip-buy lesson: "give the dip
     room, tight stops kill loose shapes" — does that lesson also apply
     here?).
  C. TOM-GATED DIP-BUY — the EXACT R60 family-1a RSI2<5 signal
     (price>SMA200, exit close>SMA5 or RSI2>65, no fixed target), but the
     entry mask is ANDed with the TOM window. Tests whether restricting
     the already-validated dip-buy to the seasonally strong window
     improves selectivity (fewer, better trades) vs the unconditioned
     family-1a signal it's built from.

execution="taker". Costs: SPY 4bps RT, ES=F 2bps RT (step130_common.COSTS).
60/20/20 chronological split, train-only selection, val read once, no
sealed-test look spent anywhere in this script.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import step130_common as C
import exits as X

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", None)


# ===========================================================================
# STRATEGY A — standalone TOM long, plain calendar hold, run_backtest
# ===========================================================================

def run_signal(d: pd.DataFrame) -> pd.Series:
    """signal[t] = 1.0 iff day t+1 is a TOM day. run_backtest fills bar
    t's signal at bar t+1's OPEN, so this puts the position on at the
    FIRST TOM day's open. TOM membership is pure calendar knowledge (zero
    price data), so shifting it forward one bar to pre-position the signal
    is not a lookahead violation the way shifting a PRICE-derived signal
    would be — the calendar date is known arbitrarily far in advance.
    Exit: the signal drops to 0 the bar AFTER the window's last TOM day
    (tom[t+1] becomes False), so run_backtest flattens at the OPEN of the
    first non-TOM day — one overnight hold longer than "flat by the last
    TOM day's close" would be (the same one-bar-lag engine limitation
    step60's every family hits; see this repo's standing engine-mismatch
    discipline). Strategy B below fixes this exactly via a custom
    same-window simulator that CAN flatten at the window's own close."""
    tom = C.tom_flag(d)
    tom_next = tom.shift(-1).fillna(False)
    return tom_next.astype(float)


def run_strategy_a(frames, meta) -> list[dict]:
    rows = []
    for tag in ("SPY", "ES", "QQQ"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = C.COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        sig = run_signal(d)
        tr, va = C.score(d, sig, costs, i_tr, i_va)
        rows.append(C.mk_row("A-tom-calendar", "tom long, no stop, calendar exit", tag, "1d", tr, va))
    return rows


# ===========================================================================
# STRATEGY B — TOM long + structural stop, custom same-window simulator
# ===========================================================================

def tom_occurrences(d: pd.DataFrame) -> list[tuple[int, int]]:
    """(start_idx, end_idx) inclusive, one per contiguous TOM run."""
    tom = C.tom_flag(d).to_numpy()
    runs = []
    i = 0
    n = len(tom)
    while i < n:
        if tom[i]:
            j = i
            while j + 1 < n and tom[j + 1]:
                j += 1
            runs.append((i, j))
            i = j + 1
        else:
            i += 1
    return runs


def simulate_tom_window(d: pd.DataFrame, s_ctx, occurrences: list[tuple[int, int]],
                        lo: int, hi: int, stop_style: str, costs) -> C.SimResult:
    """Enter at the occurrence's FIRST bar's own open, exit at whichever
    comes first: the structural stop (breached intrabar using that day's
    own low, gap-through-honesty priced via exits.py's _gap_or_level) or
    the occurrence's LAST bar's own close. stop_style: 'none' (plain
    calendar hold, the SAME exit point strategy A approximates one bar
    later) or 'structure_k5' (exits.py stop_structure(k=5,n_back=1)) or
    'atr1.0x'/'atr1.5x' (SPX's own daily ATR, secondary comparison only,
    per house discipline: never a swept %, ATR is the one allowed
    volatility-scaled exception, same convention R60 used)."""
    opens, highs, lows, closes = (d["open"].to_numpy(), d["high"].to_numpy(),
                                   d["low"].to_numpy(), d["close"].to_numpy())
    times = pd.DatetimeIndex(d["timestamp"])
    adv = costs._adverse_frac
    direction = X.LONG
    trades = []
    for start, end in occurrences:
        if start < lo or start >= hi:
            continue
        entry_raw = opens[start]
        stop_level = None
        if stop_style == "structure_k5":
            tc = X.build_trade_ctx(s_ctx, start, entry_raw, direction)
            stop_level = X.stop_structure(k=5, n_back=1).level_fn(tc, start)
        elif stop_style.startswith("atr"):
            mult = float(stop_style[3:].rstrip("x"))
            a = s_ctx.atr_arr[start]
            if np.isfinite(a) and a > 0:
                stop_level = entry_raw - direction * mult * a

        entry = entry_raw * (1 + direction * adv)
        exit_price, reason = None, None
        for i in range(start, end + 1):
            if stop_level is not None:
                breached = lows[i] <= stop_level
                if breached:
                    fill = X._gap_or_level(opens[i], stop_level, direction, "stop")
                    exit_price = fill * (1 - direction * adv)
                    reason = "stop"
                    break
        if exit_price is None:
            exit_price = closes[end] * (1 - direction * adv)
            reason = "window_close"

        notional_in = C.INITIAL_EQUITY
        entry_fee = costs.fee(notional_in)
        ret_frac = direction * (exit_price - entry) / entry
        gross = notional_in * ret_frac
        exit_fee = costs.fee(abs(notional_in + gross))
        pnl = gross - entry_fee - exit_fee
        trades.append(C.SimTrade(times[start], times[end], pnl, reason))
    return C.SimResult(trades)


def run_strategy_b(frames, meta) -> list[dict]:
    rows = []
    for tag in ("SPY", "ES", "QQQ"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = C.COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        s_ctx = X.build_series_ctx(d, k=5, atr_n=14)
        occ = tom_occurrences(d)
        for stop_style in ("none", "structure_k5", "atr1.0x", "atr1.5x"):
            tr = simulate_tom_window(d, s_ctx, occ, 0, i_tr, stop_style, costs)
            va = simulate_tom_window(d, s_ctx, occ, i_tr, i_va, stop_style, costs)
            rows.append(C.mk_sim_row("B-tom-structural-stop", f"stop={stop_style}", tag, "1d", tr, va))
    return rows


# ===========================================================================
# STRATEGY C — TOM-gated RSI2<5 dip-buy (R60 family-1a entry, TOM-masked)
# ===========================================================================

def run_strategy_c(frames, meta) -> list[dict]:
    rows = []
    for tag in ("SPY", "ES", "QQQ"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = C.COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        close = d["close"]
        sma200 = C.sma(close, 200)
        exit_cond = C.dipbuy_exit_mask(d).fillna(False)
        tom = C.tom_flag(d)
        for rsi_th in (5, 10):
            r2 = C.rsi(close, 2)
            base_enter = ((r2 < rsi_th) & (close > sma200)).fillna(False)
            for label, entry_mask in (
                ("unconditioned (baseline, = R60 1a)", base_enter),
                ("TOM-gated", base_enter & tom),
            ):
                sig = C.event_long(d, entry_mask, exit_cond, 0)
                tr, va = C.score(d, sig, costs, i_tr, i_va)
                cfg = f"rsi2<{rsi_th} {label}"
                rows.append(C.mk_row("C-tom-gated-dipbuy", cfg, tag, "1d", tr, va))
    return rows


# ===========================================================================
# STRATEGY D — R77's WIDER "N days before/after" TOM window, cross-
# instrument transfer test (the piece R77 never ran)
# ===========================================================================
# step77_spx_playbook.py (an EARLIER SPX round, found mid-session tonight —
# see step131_results.md for the full reconciliation) already built TWO
# turn-of-month strategies: its "N=2d" window (enter 2 days before month-
# end, exit 2 days into the new month) landed WITHIN THOUSANDTHS of this
# script's own Strategy A on SPY val (-6.260437 vs -6.260, tr_n 240 vs 241)
# — independent confirmation the standard Xu-McConnell window really does
# flip negative on SPY val, not a bug in either script. R77's WIDER "N=3d"
# window (3 trading days before month-end THROUGH 3 trading days into the
# new month, a 6-trading-day span vs the standard window's 4) DID survive
# on SPY (TRAIN +$51.21/240t, VAL +$27.25/81t) and was ranked its #4
# candidate — but R77 tested it ONLY on SPY, never confirmed cross-
# instrument transfer (its own "honest gaps" section doesn't even flag
# this as missing). That is the one concrete gap this script closes:
# replay R77's exact N=3d config, unchanged, on ES=F and QQQ.

def tom_signal_n(d: pd.DataFrame, N: int) -> tuple[pd.Series, pd.Series]:
    """VERBATIM port of step77_spx_playbook.tom_signal(): enter N trading
    days before month-end (rev_rank==N-1, rev_rank counts backward from
    the last trading day of the month, 0-indexed), exit N trading days
    into the new month (fwd_rank==N)."""
    month = d["timestamp"].dt.tz_convert("America/New_York").dt.to_period("M")
    rev_rank = d.groupby(month).cumcount(ascending=False)
    fwd_rank = d.groupby(month).cumcount()
    enter_long = (rev_rank == (N - 1))
    exit_ = (fwd_rank == N)
    return enter_long.fillna(False), exit_.fillna(False)


def occurrences_from_pulses(enter_mask: pd.Series, exit_mask: pd.Series) -> list[tuple[int, int]]:
    """Pairs single-day entry/exit PULSES (each fires once per month, R77's
    tom_signal_n shape) into (start_idx, end_idx) occurrences, for reuse
    with simulate_tom_window()'s structural-stop simulator — the one piece
    R77's own event_long/run_backtest version could not add (run_backtest
    has no structural-stop slot, only a flat stop_pct)."""
    e = enter_mask.to_numpy()
    x = exit_mask.to_numpy()
    n = len(e)
    occ = []
    i = 0
    while i < n:
        if e[i]:
            j = i
            while j < n and not x[j]:
                j += 1
            if j < n:
                occ.append((i, j))
                i = j + 1
            else:
                break
        else:
            i += 1
    return occ


def run_strategy_d_structural(frames, meta) -> list[dict]:
    """Same R77 N=3d window, but with a LITERAL chart-structure stop
    (exits.py stop_structure(k=5,n_back=1)) instead of R77's flat-percentage
    2xATR — closes the one house-standard gap ('none'/'2xATR' are both
    percentage-flavored; this is the confirmed-swing version the task's
    own evidence bar asks for)."""
    rows = []
    for tag in ("SPY", "ES", "QQQ"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = C.COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        s_ctx = X.build_series_ctx(d, k=5, atr_n=14)
        enter_long, exit_ = tom_signal_n(d, 3)
        occ = occurrences_from_pulses(enter_long, exit_)
        for stop_style in ("structure_k5",):
            tr = simulate_tom_window(d, s_ctx, occ, 0, i_tr, stop_style, costs)
            va = simulate_tom_window(d, s_ctx, occ, i_tr, i_va, stop_style, costs)
            rows.append(C.mk_sim_row("D2-tom-r77-structural", f"N=3d stop={stop_style}", tag, "1d", tr, va))
    return rows


def run_strategy_d(frames, meta) -> list[dict]:
    rows = []
    for tag in ("SPY", "ES", "QQQ"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = C.COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        atr_pct = C.atr(d, 14) / d["close"] * 100
        med_atr_tr = float(atr_pct.iloc[:m["i_tr"]].median())
        for N in (3,):   # R77's one SURVIVOR config only, replayed UNCHANGED
            enter_long, exit_ = tom_signal_n(d, N)
            for stop_name, stop_pct in (("none", None), ("2xATR", min(2.0 * med_atr_tr, 5.0))):
                sig = C.event_long(d, enter_long, exit_, C.days_to_bars(d, 40))
                tr, va = C.score(d, sig, costs, i_tr, i_va, stop_pct, None)
                cfg = f"R77-replay TOM N={N}d stop={stop_name}"
                rows.append(C.mk_row("D-tom-r77-transfer", cfg, tag, "1d", tr, va, stop_pct, None))
    return rows


# ===========================================================================
# main
# ===========================================================================

def main():
    print("=" * 78)
    print("ROUND 131 — DELIVERABLE 2: TURN-OF-MONTH, BUILT INTO A REAL STRATEGY")
    print("=" * 78)

    frames = {tag: {} for tag in ("SPY", "ES", "QQQ")}
    meta = {tag: {} for tag in ("SPY", "ES", "QQQ")}
    for tag in ("SPY", "ES", "QQQ"):
        frames[tag]["1d"] = C.load_symbol(tag, "1d")
        meta[tag]["1d"] = C.span_meta(frames[tag]["1d"])
        m = meta[tag]["1d"]
        occ = tom_occurrences(frames[tag]["1d"])
        n_tr_occ = sum(1 for s, e in occ if s < m["i_tr"])
        n_va_occ = sum(1 for s, e in occ if m["i_tr"] <= s < m["i_va"])
        print(f"  {tag} 1d: {m['n']} bars, i_tr={m['i_tr']} i_va={m['i_va']} | "
              f"{len(occ)} TOM occurrences total ({n_tr_occ} train / {n_va_occ} val)")

    print("\n" + "=" * 78)
    print("STRATEGY A — standalone TOM long, calendar hold, no stop (run_backtest)")
    print("=" * 78)
    a_rows = run_strategy_a(frames, meta)
    a_df = pd.DataFrame(a_rows)
    cols = ["config", "symbol", "tr_n", "tr_exp", "tr_win%", "tr_ret%", "va_n", "va_exp", "va_win%", "va_ret%", "verdict"]
    print(a_df[cols].to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\n" + "=" * 78)
    print("STRATEGY B — TOM long + structural stop (custom same-window simulator)")
    print("=" * 78)
    b_rows = run_strategy_b(frames, meta)
    b_df = pd.DataFrame(b_rows)
    print(b_df[cols].to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\n" + "=" * 78)
    print("STRATEGY C — TOM-gated RSI2<5 dip-buy vs unconditioned R60 baseline")
    print("=" * 78)
    c_rows = run_strategy_c(frames, meta)
    c_df = pd.DataFrame(c_rows)
    print(c_df[cols].to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\n" + "=" * 78)
    print("STRATEGY D — R77's wider N=3d TOM window, replayed UNCHANGED on ES=F/QQQ")
    print("(the cross-instrument transfer test R77 never ran on its own #4 SURVIVOR)")
    print("=" * 78)
    d_rows = run_strategy_d(frames, meta)
    d_df = pd.DataFrame(d_rows)
    print(d_df[cols].to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\nSTRATEGY D2 — same N=3d window, LITERAL chart-structure stop (exits.py)")
    d2_rows = run_strategy_d_structural(frames, meta)
    d2_df = pd.DataFrame(d2_rows)
    print(d2_df[cols].to_string(index=False, float_format=lambda x: f"{x:,.3f}"))
    d2_df.to_csv("step131_table_strategyD2.csv", index=False)

    a_df.to_csv("step131_table_strategyA.csv", index=False)
    b_df.to_csv("step131_table_strategyB.csv", index=False)
    c_df.to_csv("step131_table_strategyC.csv", index=False)
    d_df.to_csv("step131_table_strategyD.csv", index=False)

    print("\nDone. No sealed-test window touched.")
    return a_df, b_df, c_df, d_df


if __name__ == "__main__":
    main()
