"""
step113_oil_family_sweep2.py — Round 113: (a) cheap confirmation tests of
patterns BTC proved DEAD (order blocks, pin bars, engulfing — "dead on
BTC" isn't "dead everywhere", per Morgan's mandate), and (b) oil's NATIVE
session structure (Asia/London/NY), the one piece of "oil-specific"
character round 78 never touched.

SOURCE OF THE BTC-DEAD SHAPES (RESEARCH_LOG.md "ROUND 57 — price-action
patterns"): "order blocks 0/64 (base+breaker, broad clean negative),
pin bars/engulfing/inside-bars 0/112". Entry-signal functions
(order_block_engine, pin_bar_signals, engulfing_signals) imported
UNCHANGED from step57_price_action.py — pure OHLC functions, no
crypto-specific assumption baked in. Exit apparatus swapped to
exits.py's real structural stop (step57's own order_block_engine
returns a train-median-% stop; that return value is DISCARDED here in
favor of exits.stop_structure, per this desk's evidence bar) via
step150_common.run_edge, taker cost, one clean config each (not a grid
— the brief asks for "one clean test each, not a deep dig").

SESSION TEST: does CL=F show a systematic reaction confined to a
trading session (Asia 00:00-07:00 UTC / London 07:00-12:00 UTC /
NY 12:00-21:00 UTC — coarse, stated boundaries, not exchange-official
cutoffs) the way round 63 found session effects mattered for BTC
patterns? Descriptive diagnostic (same event_study shape as step111's
EIA test), not a costed strategy, with an explicit randomized-label
chance baseline (shuffle each bar's session label, keep timestamps
fixed).

RESEARCH ONLY. No commits, no live orders, no live-file edits. Writes
step113_oil_family_sweep2.py (this file), step113_results.md,
step113_table.csv, and appends to step110_family_map.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import exits as E
from step57_price_action import (engulfing_signals, order_block_engine,
                                 pin_bar_signals)
from step150_common import (chance_baseline, fmt_stats, mask_to_events,
                            run_edge, split_points, thickness, trade_stats,
                            verdict_for)

FAMILY_MAP_PATH = "step110_family_map.md"


def append_family_line(line: str):
    with open(FAMILY_MAP_PATH, "a") as fh:
        fh.write(line.rstrip("\n") + "\n")


def log_family_map(idx, name, verdict, key_number, chance_note, thickness_note):
    append_family_line(
        f"- **{idx}. {name}** — {verdict} | {key_number} | chance baseline: "
        f"{chance_note} | thickness: {thickness_note}")


def days_to_bars_generic(d, days):
    t = pd.DatetimeIndex(d["timestamp"])
    bar_h = float((t[1:] - t[:-1]).total_seconds().min() / 3600) if len(t) > 1 else 1.0
    return max(1, round(days * 24 / bar_h))


def run_family(idx, name, d, el, es, k, max_hold_bars, r_mult, replaced_note):
    n, i_tr, i_va = split_points(d)
    direction = pd.Series(np.where(el, 1, np.where(es, -1, 0)))
    entries_all = mask_to_events(el | es, direction)
    n_tv = sum(1 for i, _ in entries_all if i < i_va)
    if n_tv == 0:
        print(f"\n--- {name}: ZERO events on oil train+val ---")
        log_family_map(idx, name, "FAIL", "0 qualifying events on oil train+val", "n/a", "n/a")
        return None

    def stop_builder(tc):
        return E.stop_structure(k=k, n_back=1, buffer_pct=0.0, use="wick")

    def target_builder(stop):
        return E.target_fixed_r(stop, r_multiple=r_mult)

    tr_e = [(i, dr) for i, dr in entries_all if i < i_tr]
    va_e = [(i - i_tr, dr) for i, dr in entries_all if i_tr <= i < i_va]
    tr_c, va_c = d.iloc[0:i_tr].reset_index(drop=True), d.iloc[i_tr:i_va].reset_index(drop=True)
    tr, _ = run_edge(tr_c, tr_e, stop_builder, target_builder, max_hold_bars, k=k)
    va, _ = run_edge(va_c, va_e, stop_builder, target_builder, max_hold_bars, k=k)
    tr_st, va_st = trade_stats(tr), trade_stats(va)
    verdict = verdict_for(tr_st, va_st)
    floor_ok = tr_st["n"] >= 30 and va_st["n"] >= 8
    if verdict.startswith("SURVIVOR") and not floor_ok:
        verdict = "INSUFFICIENT-SAMPLE"

    all_trades = tr + va
    avg_not = float(np.mean([t["notional"] for t in all_trades])) if all_trades else 0.0
    th = thickness(va_st["expectancy"], avg_not) if va_st["n"] else \
        dict(pct_notional=float("nan"), mult_12bps=float("nan"), mult_full_18bps=float("nan"))
    if verdict.startswith("SURVIVOR") and th["mult_full_18bps"] < 5.0:
        verdict = "REJECT (thin, under 5x cost)"

    print(f"\n--- {name} ---")
    print(f"  numbers replaced: {replaced_note}")
    print(" ", fmt_stats("TRAIN", tr_st))
    print(" ", fmt_stats("VAL  ", va_st))
    print(f"  THICKNESS(val): {th['mult_full_18bps']:.2f}x full round-trip cost")
    print(f"  VERDICT: {verdict}")

    long_frac = sum(1 for i, dr in va_e if dr == 1) / max(1, len(va_e))
    cb = chance_baseline(va_c, len(va_e), long_frac, stop_builder, target_builder,
                         max_hold_bars, None, "next_open", k=k, draws=100)
    beats = va_st["expectancy"] > cb["mean_exp"] if va_st["n"] else False
    print(f"  CHANCE (val, {cb['n_draws']} draws): ${cb['mean_exp']:+.2f}/t vs real "
         f"${va_st['expectancy']:+.2f}/t -> {'BEATS' if beats else 'DOES NOT BEAT'} chance")

    log_family_map(idx, name, verdict,
                   f"val {va_st['n']}t ${va_st['expectancy']:+.2f}/t (train {tr_st['n']}t "
                   f"${tr_st['expectancy']:+.2f}/t)",
                   f"random-entry mean ${cb['mean_exp']:+.2f}/t -> real "
                   f"{'beats' if beats else 'does NOT beat'} chance",
                   f"{th['mult_full_18bps']:+.2f}x full round-trip cost")
    return dict(family=name, tr_n=tr_st["n"], tr_exp=tr_st["expectancy"],
               va_n=va_st["n"], va_exp=va_st["expectancy"],
               thickness=th["mult_full_18bps"], verdict=verdict)


# ===========================================================================
# FAMILY 7 — order blocks (base, mult=2, 50pct touch), 1h
# ===========================================================================

def family7(d1h):
    n, i_tr, i_va = split_points(d1h)
    ret1 = (d1h["close"] / d1h["close"].shift(1) - 1).abs() * 100
    med_baseline = float(ret1.iloc[:i_tr].median())   # RE-DERIVED (oil's own train median 1-bar |ret|%)
    max_wait_bars = days_to_bars_generic(d1h, 2)
    el, es, stop_pct_discarded, events = order_block_engine(
        d1h, i_tr, med_baseline, mult=2, bars_move=4, touch="50pct",
        breaker=False, max_wait_bars=max_wait_bars, k_swing=5)
    print(f"  order-block diagnostics: {events}")
    return run_family("7", "Order blocks (base, mult2, 50pct touch) — BTC-dead confirmation",
                      d1h, el, es, k=5, max_hold_bars=days_to_bars_generic(d1h, 5), r_mult=2.0,
                      replaced_note=f"impulse threshold mult=2 x oil's own TRAIN median 1-bar "
                      f"|ret|%={med_baseline:.4f}% (was BTC's own train-median baseline too — "
                      f"same shape, oil's own number substituted). stop: exits.stop_structure "
                      f"(order_block_engine's own train-median-% stop DISCARDED).")


# ===========================================================================
# FAMILY 8 — pin bars (wick_mult=2, roll20 context), 1h
# ===========================================================================

def family8(d1h):
    el, es = pin_bar_signals(d1h, wick_mult=2.0, context_type="roll20", daily_sma_al=None)
    return run_family("8", "Pin bars (wick2x, roll20 context) — BTC-dead confirmation",
                      d1h, el, es, k=5, max_hold_bars=days_to_bars_generic(d1h, 5), r_mult=2.0,
                      replaced_note="wick_mult=2.0 and roll20 context kept as pattern-shape "
                      "design (not a P&L threshold). stop: exits.stop_structure.")


# ===========================================================================
# FAMILY 9 — engulfing (roll20 context), 1h
# ===========================================================================

def family9(d1h):
    el, es = engulfing_signals(d1h, context_type="roll20", daily_sma_al=None)
    return run_family("9", "Engulfing (roll20 context) — BTC-dead confirmation",
                      d1h, el, es, k=5, max_hold_bars=days_to_bars_generic(d1h, 5), r_mult=2.0,
                      replaced_note="roll20 context kept as pattern-shape design. "
                      "stop: exits.stop_structure.")


# ===========================================================================
# FAMILY 10 — oil session structure (Asia/London/NY), descriptive
# ===========================================================================

SESSIONS = {"Asia": (0, 7), "London": (7, 12), "NY": (12, 21), "Off/maintenance": (21, 24)}


def session_of(hour: int) -> str:
    for name, (lo, hi) in SESSIONS.items():
        if lo <= hour < hi:
            return name
    return "Off/maintenance"


def family10(d1h):
    hours = d1h["timestamp"].dt.hour
    sess = hours.map(session_of)
    ret = (d1h["close"] / d1h["open"] - 1) * 100
    real = pd.DataFrame({"session": sess, "ret": ret, "abs_ret": ret.abs()})
    real_stats = real.groupby("session").agg(n=("ret", "size"), mean_ret=("ret", "mean"),
                                              mean_abs=("abs_ret", "mean"),
                                              std_ret=("ret", "std")).reset_index()
    print("\n--- FAMILY 10: oil session structure (Asia/London/NY/off), 1h bars ---")
    print(real_stats.to_string(index=False))

    rng = np.random.default_rng(113)
    n_draws = 200
    boot_means = {s: [] for s in SESSIONS}
    sess_arr = sess.to_numpy()
    ret_arr = ret.to_numpy()
    for _ in range(n_draws):
        shuffled = rng.permutation(sess_arr)
        for s in SESSIONS:
            m = ret_arr[shuffled == s]
            if len(m):
                boot_means[s].append(float(np.mean(np.abs(m))))
    print("\n  chance baseline (200 label-shuffles, mean|ret| per session):")
    rows = []
    for s in SESSIONS:
        real_row = real_stats[real_stats["session"] == s]
        if real_row.empty:
            continue
        real_mean_abs = float(real_row["mean_abs"].iloc[0])
        boot = np.array(boot_means[s])
        pctile = float((boot < real_mean_abs).mean() * 100) if len(boot) else float("nan")
        print(f"    {s:16s}: real mean|ret|={real_mean_abs:.4f}% vs shuffle-mean "
             f"{boot.mean():.4f}% (std {boot.std():.4f}) -> {pctile:.0f}th percentile")
        rows.append(dict(session=s, n=int(real_row["n"].iloc[0]),
                         mean_ret=float(real_row["mean_ret"].iloc[0]),
                         mean_abs_ret=real_mean_abs, shuffle_mean=float(boot.mean()),
                         percentile=pctile))
    log_family_map("10", "Oil session structure (Asia/London/NY/off, descriptive)",
                   "DESCRIPTIVE (not a strategy)",
                   ", ".join(f"{r['session']}: {r['mean_abs_ret']:.3f}%|ret| "
                            f"({r['percentile']:.0f}th pctile vs shuffle)" for r in rows),
                   "200 label-shuffle draws per session (see numbers above)", "n/a — descriptive only")
    return pd.DataFrame(rows)


def main():
    print("=" * 78)
    print("ROUND 113 — BTC-dead pattern confirmation + oil session structure")
    print("=" * 78)
    d1h = pd.read_parquet("data_oil_CL_1h.parquet").reset_index(drop=True)
    print(f"CL=F 1h: {len(d1h)} bars {d1h['timestamp'].iloc[0]}->{d1h['timestamp'].iloc[-1]}")

    rows = []
    for fn in (family7, family8, family9):
        r = fn(d1h)
        if r:
            rows.append(r)
    sess_df = family10(d1h)

    pd.DataFrame(rows).to_csv("step113_table.csv", index=False)
    sess_df.to_csv("step113_session_table.csv", index=False)
    print(f"\nWrote step113_table.csv ({len(rows)} rows), step113_session_table.csv. "
         f"Appended {len(rows) + 1} lines to {FAMILY_MAP_PATH}.")


if __name__ == "__main__":
    main()
