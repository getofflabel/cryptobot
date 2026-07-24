"""
step69_banking.py — round 69: BANKING THE CHART TARGET.

The owner's refinement of the news-edge exit debate (R65 gave the trade
"eyes" and found N2 structure-trailing beats the blind fixed-% incumbent —
but R65's own big-trade autopsy showed N2 turning a +$275.80 winner into a
-$69.36 loser, i.e. surviving losers while giving back real open profit on
winners). The owner's question, verbatim: "once you see the situation you
PLACE a take-profit at the structural level (the previous low for a
short). Pure trailing just gives profits back until the stop catches it —
when do you make the money?" This script tests the MIDDLE PATH: bank part
of the position at a computed structural target, let the rest ride the
same structure-trailing mechanic R65 validated.

Research only. Touches ONLY step69_banking.py (this file) and
step69_results.md (written by hand from this script's output). No live
orders, no commits. Concurrent agents own step67_scalp.py / step68_router2.py
this round — never read or imported.

======================================================================
MACHINERY REUSE (the mandate's own instruction: extend, don't reinvent)
======================================================================
Everything about the FIXED TRIGGER, the news-span train/val split, the
per-slice pivot/ATR precompute, the plain simulator (`simulate`/`_manage`),
cost conventions, and the N0/N1/N2 policy shapes is imported directly from
`step65_news_eyes.py` — not reimplemented. The only genuinely new code
here is `compute_structural_target` (the shared target-construction used
by every banking policy and B5) and `simulate_banking` (a new simulator
variant that extends `_manage`'s "trailing" branch with a partial-exit /
breakeven-stop-shift mechanic that the plain `simulate()` cannot express,
mirroring exactly why R65's own module docstring justified hand-rolling a
simulator over reusing backtest.py's continuous-signal engine).

======================================================================
THE FIXED TRIGGER AND SPLIT (identical to R65 — see step65_news_eyes.py's
own docstring for the full description). Unchanged here: same relevant
WatcherGuru headline -> first full 1h bar after it -> enter at that bar's
own close, direction = that bar's own close-vs-open sign. Same chronological
60/20/20 news-span split (step43_daytrade.split_points). TEST SEALED: this
script, like step65, only ever loads / computes on `[0:i_va]`.

======================================================================
THE SIX POLICIES
======================================================================
B0 N2 PURE TRAILING (the live incumbent) — baseline. Reproduces R65's
    N2 trail buf0.3% k=5 exactly (same builder, same simulate()), printed
    first as a harness check against R65's published numbers.
B1/B2/B3 BANKING (50/50, 75/25, 25/75) — at entry, compute a structural
    target (nearest confirmed k=5 swing on the favorable side, accepted
    only inside [1x,3x] the entry-bar-extreme stop distance -- N1's own
    band; outside the band, or no confirmed level yet, falls back to a
    SYNTHETIC 2x-stop-distance target, this repo's own established 2R
    "constructed target" convention -- NOT N1's own fallback, which
    instead reverts the WHOLE trade to the plain incumbent bracket). Bank
    {50%,75%,25%} of the position there (maker fee, resting-limit
    convention). The stop for the WHOLE position stays fixed at the
    entry-bar-extreme+buffer level (no trailing) until the bank happens --
    before banking this is mechanically a static N1-style bracket on the
    full size. Only AFTER the bank does the remainder start riding N2's
    trailing floor (ratchets on newly confirmed k=5 swings from that point
    forward). Each split run twice: WITHOUT breakeven (floor stays at the
    original entry-bar-extreme stop after the bank) and WITH breakeven
    (floor snaps to entry price at the moment of banking, but only if that
    IMPROVES the floor -- never loosens it).
B4 FULL TARGET (N1 verbatim) — N1's own best/most-comparable config
    (swing_k5, SL buffer 0.3%, the same buffer used everywhere else this
    round), called through step65's own n1_builder + simulate(), rerun
    here verbatim for continuity in the same table.
B5 OWNER'S LITERAL DESIGN — TP at the structural level (same target
    machinery as B1-B3, 2R synthetic fallback) on the FULL position + the
    structural stop, NO trailing at all. The single-leg boundary case of
    the banking family (bank_frac=1.0, conceptually) -- what the owner
    described before "middle path" was even on the table.

======================================================================
THE GIVEBACK METRIC (the owner's exact complaint, quantified)
======================================================================
For every trade under every policy: peak_open_profit = the best price the
market touched in the trade's favor during its ACTUAL realized hold window
(gross, full original notional, no fees) minus realized_pnl (the actual
net dollars booked, after every fee/funding leg). giveback = peak minus
realized. Reported as a per-trade mean for every policy so N2's own
documented failure mode (surviving losers, but giving back winners) has an
explicit number to be judged against, not just the one anecdote from R65.

Run:  python3 step69_banking.py
"""

from __future__ import annotations

import bisect

import numpy as np
import pandas as pd

from step65_news_eyes import (
    INITIAL_EQUITY, TARGET_FEE_BPS, STOP_FEE_BPS, N1_BAND, MIN_TRAIN_TRADES,
    MIN_VAL_TRADES, bar_hours_of, entry_bar_extreme_stop, nearest_favorable_swing,
    band_accept, _gap_or_level, simulate, trades_to_stats, verdict_for,
    build_news_entries, slice_meta, n0_builder, n1_builder, n2_builder,
    fetch_bybit_deep, fetch_funding_history, align_funding, split_points,
)

pd.set_option("display.width", 240)
pd.set_option("display.max_columns", None)

SL_BUFFER_BANK = 0.3       # N2's own winning buffer (R65) -- reused, not re-swept;
                            # the split ratio / breakeven axis is THIS round's question
BANK_SPLITS = [
    ("B1 bank-half", 0.5),
    ("B2 bank-75/25", 0.75),
    ("B3 bank-25/75", 0.25),
]
N1_CONFIG_FOR_B4 = ("swing_k5", 0.3)


# ===========================================================================
# NEW: shared structural-target machinery (B1-B3, B5)
# ===========================================================================

def compute_structural_target(meta, entry_idx, entry_price, direction, sl_buffer=SL_BUFFER_BANK):
    """SL = entry-bar-extreme + buffer (identical construction to N1/N2,
    imported verbatim as entry_bar_extreme_stop). TP = nearest confirmed
    k=5 swing on the favorable side, accepted only inside [1x,3x] the stop
    distance (N1's own band_accept, imported verbatim). Outside the band,
    or no confirmed level exists yet, falls back to a SYNTHETIC 2x-stop-
    distance target -- this repo's established 2R "constructed target"
    convention (step45b/step59's E4, also how R65's N3 built a reference
    distance for N2). This is a DIFFERENT fallback than N1's own (which
    reverts the whole trade to the plain incumbent bracket) -- deliberate,
    so a banking policy never silently turns into "sometimes N0" mid-table.
    Returns (stop_px, stop_dist_pct, target_px, target_dist_pct, tagged_real)."""
    o, h, l, c = meta["o"], meta["h"], meta["l"], meta["c"]
    stop_px = entry_bar_extreme_stop(o, h, l, c, entry_idx, direction, sl_buffer)
    stop_dist_pct = abs(entry_price - stop_px) / entry_price * 100
    piv = meta["piv_high5"] if direction > 0 else meta["piv_low5"]
    raw = nearest_favorable_swing(piv, entry_idx, entry_price, direction)
    accepted = band_accept(raw, entry_price, stop_dist_pct, direction, band=N1_BAND)
    if accepted is not None:
        return (stop_px, stop_dist_pct, accepted,
               abs(accepted - entry_price) / entry_price * 100, True)
    target_px = entry_price * (1 + direction * 2 * stop_dist_pct / 100)
    return stop_px, stop_dist_pct, target_px, 2 * stop_dist_pct, False


# ===========================================================================
# NEW: the banking simulator (extends _manage's "trailing" branch with a
# partial-exit + post-bank breakeven-shift mechanic the plain simulate()
# has no vocabulary for -- same justification R65 itself gave for hand-
# rolling a simulator instead of reusing backtest.py's continuous engine)
# ===========================================================================

def simulate_banking(candles, entries, meta, bank_frac, use_be,
                     sl_buffer=SL_BUFFER_BANK, funding=None):
    o = candles["open"].to_numpy(); h = candles["high"].to_numpy()
    l = candles["low"].to_numpy(); c = candles["close"].to_numpy()
    t = pd.DatetimeIndex(candles["timestamp"]); n = len(candles)
    fund = funding.to_numpy() if funding is not None else None
    bh = bar_hours_of(candles)
    max_hold_bars = meta["max_hold_bars"]

    equity = INITIAL_EQUITY
    trades, busy_until = [], -1

    for entry_idx, direction in entries:
        if entry_idx <= busy_until or entry_idx >= n - 1:
            continue
        entry_price = float(c[entry_idx])
        stop_px, stop_dist_pct, target_px, target_dist_pct, tagged_real = \
            compute_structural_target(meta, entry_idx, entry_price, direction, sl_buffer)
        floor_px = stop_px
        floor_pivots = meta["piv_low5"] if direction > 0 else meta["piv_high5"]
        last_i = min(n - 1, entry_idx + max_hold_bars)

        banked = False
        bank_idx = bank_price = None
        seen_upto = None
        final_idx = final_price = final_reason = final_fee_bps = None

        for i in range(entry_idx + 1, last_i + 1):
            if not banked:
                # pre-bank: stop is FIXED at the entry-bar extreme (no
                # trailing yet -- mechanically an N1-style static bracket
                # on the full position until the bank actually happens).
                hit_floor = (l[i] <= floor_px) if direction > 0 else (h[i] >= floor_px)
                hit_target = (h[i] >= target_px) if direction > 0 else (l[i] <= target_px)
                if hit_floor:          # stop wins ties -- never banked, full exit
                    final_idx = i
                    final_price = _gap_or_level(o[i], floor_px, direction, "stop")
                    final_reason, final_fee_bps = "stop (never tagged)", STOP_FEE_BPS
                    break
                if hit_target:
                    bank_idx = i
                    bank_price = _gap_or_level(o[i], target_px, direction, "target")
                    banked = True
                    seen_upto = i
                    if use_be:
                        be = entry_price
                        floor_px = max(floor_px, be) if direction > 0 else min(floor_px, be)
                    if i == last_i:
                        final_idx, final_price = i, float(c[i])
                        final_reason, final_fee_bps = "time", STOP_FEE_BPS
                        break
                    continue
                if i == last_i:
                    final_idx, final_price = i, float(c[i])
                    final_reason, final_fee_bps = "time", STOP_FEE_BPS
                    break
                continue

            # post-bank: remainder rides N2's trailing floor, ratcheting on
            # newly confirmed k=5 swings from the bank point forward only
            # (pre-bank pivots deliberately never applied -- the floor was
            # static by design until the bank).
            lo_ = bisect.bisect_right(floor_pivots["confirm_idx"], seen_upto)
            hi_ = bisect.bisect_right(floor_pivots["confirm_idx"], i)
            for p in floor_pivots["price"][lo_:hi_]:
                if direction > 0 and p > floor_px:
                    floor_px = float(p)
                elif direction < 0 and p < floor_px:
                    floor_px = float(p)
            seen_upto = i

            hit_floor = (l[i] <= floor_px) if direction > 0 else (h[i] >= floor_px)
            if hit_floor:
                final_idx = i
                final_price = _gap_or_level(o[i], floor_px, direction, "stop")
                final_reason, final_fee_bps = "structure stop", STOP_FEE_BPS
                break
            broke_close = (c[i] < floor_px) if direction > 0 else (c[i] > floor_px)
            if broke_close:
                final_idx, final_price = i, float(c[i])
                final_reason, final_fee_bps = "structure break", STOP_FEE_BPS
                break
            if i == last_i:
                final_idx, final_price = i, float(c[i])
                final_reason, final_fee_bps = "time", STOP_FEE_BPS
                break

        if final_idx is None:      # defensive -- max_hold clamp should always break the loop
            final_idx, final_price = last_i, float(c[last_i])
            final_reason, final_fee_bps = "time", STOP_FEE_BPS

        exit_idx = final_idx
        bank_frac_realized = bank_frac if banked else 0.0
        remain_frac = 1.0 - bank_frac_realized

        entry_fee = equity * TARGET_FEE_BPS / 10_000
        pnl = -entry_fee

        if banked:
            notional_bank = equity * bank_frac
            gross_bank = direction * (bank_price / entry_price - 1) * notional_bank
            fee_bank = notional_bank * bank_price / entry_price * TARGET_FEE_BPS / 10_000
            funding_bank = 0.0
            if fund is not None and bank_idx > entry_idx:
                mr = float(np.nanmean(fund[entry_idx + 1:bank_idx + 1]))
                if mr == mr:
                    funding_bank = notional_bank * direction * mr / 10_000 * ((bank_idx - entry_idx) * bh / 8.0)
            pnl_bank = gross_bank - fee_bank - funding_bank
            pnl += pnl_bank

            notional_rem = equity * remain_frac
            gross_rem = direction * (final_price / entry_price - 1) * notional_rem
            fee_rem = notional_rem * final_price / entry_price * final_fee_bps / 10_000
            funding_rem = 0.0
            if fund is not None and final_idx > bank_idx:
                mr = float(np.nanmean(fund[bank_idx + 1:final_idx + 1]))
                if mr == mr:
                    funding_rem = notional_rem * direction * mr / 10_000 * ((final_idx - bank_idx) * bh / 8.0)
            pnl_rem = gross_rem - fee_rem - funding_rem
            pnl += pnl_rem
        else:
            notional = equity
            gross = direction * (final_price / entry_price - 1) * notional
            fee = notional * final_price / entry_price * final_fee_bps / 10_000
            funding_dollars = 0.0
            if fund is not None and final_idx > entry_idx:
                mr = float(np.nanmean(fund[entry_idx + 1:final_idx + 1]))
                if mr == mr:
                    funding_dollars = notional * direction * mr / 10_000 * ((final_idx - entry_idx) * bh / 8.0)
            pnl += gross - fee - funding_dollars
            pnl_bank = None

        favorable = h[entry_idx + 1: exit_idx + 1] if direction > 0 else l[entry_idx + 1: exit_idx + 1]
        if len(favorable) == 0:
            peak_price = entry_price
        else:
            peak_price = float(favorable.max()) if direction > 0 else float(favorable.min())
        peak_open_profit = direction * (peak_price / entry_price - 1) * equity
        giveback = peak_open_profit - pnl

        hold_bars = exit_idx - entry_idx
        hold_hours = hold_bars * bh if hold_bars > 0 else bh

        trades.append(dict(
            entry_idx=entry_idx, exit_idx=exit_idx, entry_time=t[entry_idx], exit_time=t[exit_idx],
            entry_price=entry_price, direction=direction, pnl=pnl, hold_hours=hold_hours,
            banked=banked, bank_frac=bank_frac_realized, tagged_real=tagged_real,
            bank_idx=bank_idx, bank_price=bank_price,
            pnl_bank=(pnl_bank if banked else None),
            final_price=final_price, final_reason=final_reason,
            peak_open_profit=peak_open_profit, giveback=giveback,
            reason=(f"bank->{final_reason}" if banked else final_reason),
        ))
        equity += pnl
        busy_until = exit_idx

    return trades


# ===========================================================================
# NEW: single-leg static-bracket builder for B5 (owner's literal design --
# same target machinery as banking, no bank, no trail)
# ===========================================================================

def b5_builder(meta, sl_buffer=SL_BUFFER_BANK):
    def build(entry_idx, entry_price, direction):
        stop_px, stop_dist_pct, target_px, target_dist_pct, tagged_real = \
            compute_structural_target(meta, entry_idx, entry_price, direction, sl_buffer)
        return dict(stop_from_pct=False, stop_px=stop_px, target_pct=target_dist_pct,
                   max_hold_bars=meta["max_hold_bars"], tagged_real=tagged_real)
    return "static", build


# ===========================================================================
# giveback / target-tag post-processing for plain simulate() output
# (B0 / B4 / B5, whose trade dicts come straight from step65's simulate())
# ===========================================================================

def add_giveback(trades, candles):
    h = candles["high"].to_numpy(); l = candles["low"].to_numpy()
    equity = INITIAL_EQUITY
    for tr in trades:
        direction = tr["direction"]
        entry_idx, exit_idx = tr["entry_idx"], tr["exit_idx"]
        favorable = h[entry_idx + 1: exit_idx + 1] if direction > 0 else l[entry_idx + 1: exit_idx + 1]
        if len(favorable) == 0:
            peak_price = tr["entry_price"]
        else:
            peak_price = float(favorable.max()) if direction > 0 else float(favorable.min())
        peak_open_profit = direction * (peak_price / tr["entry_price"] - 1) * equity
        tr["peak_open_profit"] = peak_open_profit
        tr["giveback"] = peak_open_profit - tr["pnl"]
        equity += tr["pnl"]
    return trades


def stats_with_extras(trades, tag_field="reason", tag_value="target"):
    base = trades_to_stats(trades)
    if not trades:
        base.update(mean_giveback=0.0, target_tag_rate=float("nan"), pct_real_target=float("nan"))
        return base
    giveback_arr = np.array([tr["giveback"] for tr in trades])
    if tag_field == "banked":
        tagged = np.array([bool(tr["banked"]) for tr in trades])
    else:
        tagged = np.array([tr[tag_field] == tag_value for tr in trades])
    base["mean_giveback"] = float(giveback_arr.mean())
    base["target_tag_rate"] = float(tagged.mean()) * 100
    if trades and "tagged_real" in trades[0]:
        real = np.array([tr["tagged_real"] for tr in trades])
        base["pct_real_target"] = float(real.mean()) * 100
    else:
        base["pct_real_target"] = float("nan")
    return base


# ===========================================================================
# driver
# ===========================================================================

def load_data():
    """Mirrors step65_news_eyes.main()'s setup section exactly (news-span
    slice, 60/20/20 split, per-slice pivot/ATR precompute) -- data-loading
    orchestration only, not simulator logic, so this is not a re-invention
    of the mandate's protected machinery."""
    btc1h_full = fetch_bybit_deep("1h", "BTCUSDT")
    funding_hist = fetch_funding_history("BTCUSDT")
    news = pd.read_parquet("data_watcherguru_history.parquet")

    news_min, news_max = news["utc_timestamp"].min(), news["utc_timestamp"].max()
    mask = ((btc1h_full["timestamp"] >= news_min - pd.Timedelta(hours=24)) &
           (btc1h_full["timestamp"] <= news_max + pd.Timedelta(hours=24)))
    d_span = btc1h_full[mask].reset_index(drop=True)
    n, i_tr, i_va = split_points(d_span)

    d = d_span.iloc[:i_va].reset_index(drop=True)      # test rows dropped from memory entirely
    entries_all = build_news_entries(d, news)
    funding_full = align_funding(d, funding_hist)

    train_c = d.iloc[0:i_tr].reset_index(drop=True)
    val_c = d.iloc[i_tr:i_va].reset_index(drop=True)
    train_entries = [(i, dd) for i, dd in entries_all if i < i_tr]
    val_entries = [(i - i_tr, dd) for i, dd in entries_all if i_tr <= i < i_va]
    fund_train = funding_full.iloc[0:i_tr].reset_index(drop=True)
    fund_val = funding_full.iloc[i_tr:i_va].reset_index(drop=True)

    meta_train = slice_meta(train_c)
    meta_val = slice_meta(val_c)

    print(f"  news-span slice: {len(d_span)} bars "
         f"({d_span['timestamp'].iloc[0]:%Y-%m-%d} -> {d_span['timestamp'].iloc[-1]:%Y-%m-%d}) "
         f"| train->{d_span['timestamp'].iloc[i_tr]:%Y-%m-%d} "
         f"val->{d_span['timestamp'].iloc[i_va]:%Y-%m-%d} (TEST SEALED)")
    print(f"  {len(entries_all)} directional entries over [0:i_va] "
         f"({sum(1 for _, dd in entries_all if dd > 0)} long / "
         f"{sum(1 for _, dd in entries_all if dd < 0)} short)")
    print(f"  train: {len(train_entries)} entries, {i_tr} bars | "
         f"val: {len(val_entries)} entries, {i_va - i_tr} bars")

    return dict(train_c=train_c, val_c=val_c, train_entries=train_entries, val_entries=val_entries,
               fund_train=fund_train, fund_val=fund_val, meta_train=meta_train, meta_val=meta_val)


def main():
    print("=" * 78)
    print("ROUND 69 — BANKING THE CHART TARGET")
    print("=" * 78)
    print("\nLoading cached data (no network calls)...")
    ctx = load_data()
    train_c, val_c = ctx["train_c"], ctx["val_c"]
    train_entries, val_entries = ctx["train_entries"], ctx["val_entries"]
    fund_train, fund_val = ctx["fund_train"], ctx["fund_val"]
    meta_train, meta_val = ctx["meta_train"], ctx["meta_val"]

    results = {}

    def register(label, tr_trades, va_trades, tag_field="reason", tag_value="target"):
        tr_stats = stats_with_extras(tr_trades, tag_field, tag_value)
        va_stats = stats_with_extras(va_trades, tag_field, tag_value)
        results[label] = dict(train=tr_stats, val=va_stats,
                              verdict=verdict_for(tr_stats, va_stats),
                              raw_train=tr_trades, raw_val=va_trades)
        print(f"  {label:<26} train n={tr_stats['n']:>4} exp ${tr_stats['expectancy']:>8,.2f} "
             f"giveback ${tr_stats['mean_giveback']:>7,.2f} tag {tr_stats['target_tag_rate']:>5.1f}%  ||  "
             f"val n={va_stats['n']:>4} exp ${va_stats['expectancy']:>8,.2f} "
             f"giveback ${va_stats['mean_giveback']:>7,.2f} tag {va_stats['target_tag_rate']:>5.1f}%  "
             f"[{results[label]['verdict']}]")

    print("\n" + "=" * 78)
    print("B0 — N2 PURE TRAILING (live incumbent, buf0.3% k=5) — HARNESS CHECK")
    print("=" * 78)
    kind0, b0_tr = n2_builder(meta_train, SL_BUFFER_BANK)
    _, b0_va = n2_builder(meta_val, SL_BUFFER_BANK)
    b0_tr_trades = add_giveback(simulate(train_c, train_entries, kind0, b0_tr, funding=fund_train), train_c)
    b0_va_trades = add_giveback(simulate(val_c, val_entries, kind0, b0_va, funding=fund_val), val_c)
    register("B0 N2 pure trail", b0_tr_trades, b0_va_trades,
             tag_field="reason", tag_value="__never__")   # N2 has no fixed target -- tag rate n/a below
    print("  (R65 published: train n=315 exp $+9.57 | val n=112 exp $+4.34 -- "
         "compare above; small drift expected, one more day of news harvested since R65)")

    print("\n" + "=" * 78)
    print("B4 — FULL TARGET, N1 VERBATIM (swing_k5, buf0.3%)")
    print("=" * 78)
    kind4, b4_tr = n1_builder(meta_train, *N1_CONFIG_FOR_B4)
    _, b4_va = n1_builder(meta_val, *N1_CONFIG_FOR_B4)
    b4_tr_trades = add_giveback(simulate(train_c, train_entries, kind4, b4_tr, funding=fund_train), train_c)
    b4_va_trades = add_giveback(simulate(val_c, val_entries, kind4, b4_va, funding=fund_val), val_c)
    register("B4 N1 full target", b4_tr_trades, b4_va_trades)

    print("\n" + "=" * 78)
    print("B5 — OWNER'S LITERAL DESIGN (structural TP, full position, no trail)")
    print("=" * 78)
    kind5, b5_tr = b5_builder(meta_train)
    _, b5_va = b5_builder(meta_val)
    b5_tr_trades = add_giveback(simulate(train_c, train_entries, kind5, b5_tr, funding=fund_train), train_c)
    b5_va_trades = add_giveback(simulate(val_c, val_entries, kind5, b5_va, funding=fund_val), val_c)
    register("B5 structural TP full", b5_tr_trades, b5_va_trades)

    print("\n" + "=" * 78)
    print("B1/B2/B3 — BANKING (split ratio x with/without breakeven)")
    print("=" * 78)
    for label, frac in BANK_SPLITS:
        for be_tag, use_be in (("noBE", False), ("BE", True)):
            full_label = f"{label} {be_tag}"
            tr_trades = simulate_banking(train_c, train_entries, meta_train, frac, use_be, funding=fund_train)
            va_trades = simulate_banking(val_c, val_entries, meta_val, frac, use_be, funding=fund_val)
            register(full_label, tr_trades, va_trades, tag_field="banked")

    print("\n" + "=" * 78)
    print("VERDICT SUMMARY — beats B0 on both windows?")
    print("=" * 78)
    b0_tr_exp = results["B0 N2 pure trail"]["train"]["expectancy"]
    b0_va_exp = results["B0 N2 pure trail"]["val"]["expectancy"]
    for label, res in results.items():
        beats_both = (res["train"]["expectancy"] > b0_tr_exp and res["val"]["expectancy"] > b0_va_exp)
        print(f"  {label:<26} verdict={res['verdict']:<20} beats B0 both windows: {beats_both}")

    # ---- big-winner autopsy: locate R65's own +$275.80 giveback trade and
    # the other two biggest N0 winners/losers, show every policy's outcome ----
    print("\n" + "=" * 78)
    print("BIG-TRADE AUTOPSY — N0's biggest winners/losers, every policy's outcome")
    print("=" * 78)
    kind_n0_tr, n0_tr_b = n0_builder(meta_train["max_hold_bars"])
    _, n0_va_b = n0_builder(meta_val["max_hold_bars"])
    n0_tr_trades = simulate(train_c, train_entries, kind_n0_tr, n0_tr_b, funding=fund_train)
    n0_va_trades = simulate(val_c, val_entries, kind_n0_tr, n0_va_b, funding=fund_val)
    n0_all = n0_tr_trades + n0_va_trades
    n0_sorted = sorted(n0_all, key=lambda tr: tr["pnl"])
    big_losers = n0_sorted[:3]
    big_winners = n0_sorted[-3:][::-1]

    autopsy_labels = ["B0 N2 pure trail", "B1 bank-half noBE", "B1 bank-half BE",
                      "B2 bank-75/25 BE", "B3 bank-25/75 BE", "B4 N1 full target", "B5 structural TP full"]

    def find_match(label, entry_time, direction):
        pool = results[label]["raw_train"] + results[label]["raw_val"]
        for tr in pool:
            if tr["entry_time"] == entry_time and tr["direction"] == direction:
                return tr
        return None

    autopsy_report = {"losers": [], "winners": []}
    for tag, group, bucket in (("BIGGEST LOSERS", big_losers, "losers"), ("BIGGEST WINNERS", big_winners, "winners")):
        print(f"\n  --- {tag} (ranked by N0 pnl) ---")
        for tr in group:
            row = {"entry_time": str(tr["entry_time"]), "direction": tr["direction"],
                  "N0": tr["pnl"], "N0_reason": tr["reason"]}
            print(f"  entry {tr['entry_time']} dir={tr['direction']:+d}  N0: "
                 f"${tr['pnl']:+,.2f} ({tr['reason']}, {tr['hold_hours']:.1f}h)")
            for label in autopsy_labels:
                m = find_match(label, tr["entry_time"], tr["direction"])
                if m is None:
                    print(f"      {label:<24} -> not taken (single-slot busy)")
                    row[label] = None
                else:
                    extra = f", banked {m['bank_frac']*100:.0f}%" if "bank_frac" in m and m["bank_frac"] else ""
                    print(f"      {label:<24} -> ${m['pnl']:+,.2f} ({m['reason']}, {m['hold_hours']:.1f}h{extra})")
                    row[label] = m["pnl"]
            autopsy_report[bucket].append(row)

    # ---- conditional giveback: does banking actually help WHEN it gets to
    # fire, or is the flat aggregate giveback above just the ~70% "never
    # tagged" cohort (identical to B0 by construction) drowning out the
    # ~30% that actually banked? Matched against B0's OWN giveback on the
    # exact same entries, so this isolates the mechanism honestly. ----
    print("\n" + "=" * 78)
    print("CONDITIONAL GIVEBACK — banked subset vs B0 on the SAME entries")
    print("=" * 78)
    b0_by_key = {(tr["entry_time"], tr["direction"]): tr
                for tr in results["B0 N2 pure trail"]["raw_train"] + results["B0 N2 pure trail"]["raw_val"]}
    conditional_report = {}
    for label, frac in BANK_SPLITS:
        for be_tag in ("noBE", "BE"):
            full_label = f"{label} {be_tag}"
            pool = results[full_label]["raw_train"] + results[full_label]["raw_val"]
            banked_trs = [tr for tr in pool if tr["banked"]]
            never_trs = [tr for tr in pool if not tr["banked"]]
            b0_matched = [b0_by_key[(tr["entry_time"], tr["direction"])] for tr in banked_trs
                         if (tr["entry_time"], tr["direction"]) in b0_by_key]
            gb_banked = float(np.mean([tr["giveback"] for tr in banked_trs])) if banked_trs else float("nan")
            gb_never = float(np.mean([tr["giveback"] for tr in never_trs])) if never_trs else float("nan")
            gb_b0_matched = float(np.mean([tr["giveback"] for tr in b0_matched])) if b0_matched else float("nan")
            pnl_policy_matched = float(np.mean([tr["pnl"] for tr in banked_trs])) if banked_trs else float("nan")
            pnl_b0_matched = float(np.mean([tr["pnl"] for tr in b0_matched])) if b0_matched else float("nan")
            conditional_report[full_label] = dict(
                n_banked=len(banked_trs), n_never=len(never_trs),
                gb_banked=gb_banked, gb_never=gb_never, gb_b0_matched=gb_b0_matched,
                pnl_policy_matched=pnl_policy_matched, pnl_b0_matched=pnl_b0_matched,
            )
            print(f"  {full_label:<20} n_banked={len(banked_trs):>3} (giveback ${gb_banked:>7,.2f}, "
                 f"pnl ${pnl_policy_matched:>7,.2f})  vs B0 on SAME entries (giveback ${gb_b0_matched:>7,.2f}, "
                 f"pnl ${pnl_b0_matched:>7,.2f})  |  n_never_tagged={len(never_trs):>4} "
                 f"(giveback ${gb_never:>7,.2f} -- NOT identical to B0's own exit on these entries: "
                 f"pre-bank floor is static while B0 trails from bar 1, per-trade exits differ, "
                 f"aggregate pnl gap is small but real, see step69_results.md)")

    return dict(results=results, big_losers=big_losers, big_winners=big_winners,
               autopsy_report=autopsy_report, n0_tr_trades=n0_tr_trades, n0_va_trades=n0_va_trades,
               conditional_report=conditional_report)


if __name__ == "__main__":
    main()
