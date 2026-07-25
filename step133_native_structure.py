"""
step133_native_structure.py — ROUND 133. More of SPX's own native calendar
structure, beyond what R60/R77/step131 already covered.

ALREADY COVERED, NOT REPEATED HERE:
  - day-of-week: step77 family 6b (Mon->Fri weekly hold SURVIVOR, Tue-only
    FAIL) — cited, not re-run.
  - turn-of-month: R60 (audit) + step131 (this round's own two windows,
    the wide N=3d one now cross-instrument-validated).

NEW HERE:
  PART A — OPTIONS-EXPIRY WEEK (the week containing the month's third
    Friday — the standard monthly-equity-options-expiry convention;
    quarterly quad-witching months Mar/Jun/Sep/Dec flagged separately).
    Never tested anywhere in this program. Audit first (report-only, chance
    baseline = the unconditioned weekly mean), then built into a real
    long-during-expiry-week strategy, SPY+ES+QQQ.
  PART B — GAP MAGNITUDE vs INTRADAY RANGE (report-only audit): does a
    LARGE gap (either direction) predict a wider realized range for the
    REST of that same day — i.e. is a big gap a volatility-expansion
    signal that should widen a same-day stop, distinct from step130's
    gap-DIRECTION test. Practical output: a stop-sizing input, not a
    standalone entry.

execution="taker". Costs from step130_common.COSTS. No sealed-test look
spent.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import step130_common as C

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", None)


# ===========================================================================
# PART A — options-expiry week
# ===========================================================================

def expiry_week_flag(d: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """(is_expiry_week, is_quad_witching_week). Monthly equity-options
    expiry = the third Friday of each calendar month; 'expiry week' = the
    Mon-Fri calendar week containing that Friday (trading days only, so a
    holiday-shortened week is naturally handled by just checking calendar
    week number). Quad-witching = the same week in Mar/Jun/Sep/Dec."""
    ts_et = d["timestamp"].dt.tz_convert("America/New_York")
    dates = ts_et.dt.date
    # third Friday per (year, month)
    third_fridays = {}
    for y in range(ts_et.dt.year.min(), ts_et.dt.year.max() + 1):
        for m in range(1, 13):
            fridays = pd.date_range(f"{y}-{m:02d}-01", periods=31, freq="D")
            fridays = fridays[(fridays.month == m) & (fridays.weekday == 4)]
            if len(fridays) >= 3:
                third_fridays[(y, m)] = fridays[2].date()
    iso = pd.DatetimeIndex(dates).isocalendar()
    week_key = list(zip(iso["year"], iso["week"]))
    target_week = {}
    for (y, m), fri in third_fridays.items():
        iso_f = pd.Timestamp(fri).isocalendar()
        target_week[(y, m)] = (iso_f.year, iso_f.week)
    is_expiry = pd.Series([wk in target_week.values() for wk in week_key], index=d.index)
    quad_months = {3, 6, 9, 12}
    quad_weeks = {v for (y, m), v in target_week.items() if m in quad_months}
    is_quad = pd.Series([wk in quad_weeks for wk in week_key], index=d.index)
    return is_expiry.fillna(False), is_quad.fillna(False)


def run_part_a_audit(frames, meta) -> list[dict]:
    rows = []
    for tag in ("SPY", "ES", "QQQ"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        i_va = m["i_va"]
        ret = d["close"].pct_change() * 100
        is_expiry, is_quad = expiry_week_flag(d)
        for label, mask in (
            ("expiry-week (monthly)", is_expiry),
            ("quad-witching-week (quarterly)", is_quad),
            ("non-expiry-week (baseline)", ~is_expiry),
        ):
            sub = ret.iloc[:i_va][mask.iloc[:i_va]].dropna()
            rows.append({"symbol": tag, "bucket": label, "n": len(sub),
                        "mean_ret_pct": float(sub.mean()) if len(sub) else np.nan,
                        "tstat": C.tstat_1samp(sub.to_numpy()), "win_pct": float((sub > 0).mean() * 100) if len(sub) else np.nan})
    return rows


def run_part_a_strategy(frames, meta) -> list[dict]:
    rows = []
    for tag in ("SPY", "ES", "QQQ"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = C.COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        med_atr = m["med_atr"]
        is_expiry, is_quad = expiry_week_flag(d)
        for label, mask in (("monthly-expiry-week", is_expiry), ("quad-witching-week", is_quad)):
            mask_next = mask.shift(-1).fillna(False).astype(float)
            tr, va = C.score(d, mask_next, costs, i_tr, i_va)
            rows.append(C.mk_row("A-options-expiry-week", f"long {label}, calendar exit", tag, "1d", tr, va))
            stop_pct = min(1.0 * med_atr, 3.0)
            tr2, va2 = C.score(d, mask_next, costs, i_tr, i_va, stop_pct=stop_pct)
            rows.append(C.mk_row("A-options-expiry-week", f"long {label}, stop=1.0xATR", tag, "1d", tr2, va2, stop_pct))
    return rows


# ===========================================================================
# PART B — gap magnitude vs intraday range (report-only, stop-sizing input)
# ===========================================================================

def run_part_b(frames, meta) -> list[dict]:
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        i_va = m["i_va"]
        opens = d["open"].to_numpy()[1:i_va]
        closes_prior = d["close"].to_numpy()[0:i_va - 1]
        highs = d["high"].to_numpy()[1:i_va]
        lows = d["low"].to_numpy()[1:i_va]
        gap_abs_pct = np.abs((opens - closes_prior) / closes_prior * 100)
        range_pct = (highs - lows) / opens * 100
        # correlation + a coarse 2-bucket comparison (big gap vs small gap)
        corr = float(np.corrcoef(gap_abs_pct, range_pct)[0, 1])
        median_gap = float(np.median(gap_abs_pct))
        big = range_pct[gap_abs_pct >= median_gap]
        small = range_pct[gap_abs_pct < median_gap]
        rows.append({"symbol": tag, "n": len(gap_abs_pct), "corr_gapabs_vs_range": corr,
                    "median_gap_pct": median_gap,
                    "mean_range_pct_big_gap_days": float(np.mean(big)),
                    "mean_range_pct_small_gap_days": float(np.mean(small)),
                    "ratio_big_over_small": float(np.mean(big) / np.mean(small))})
    return rows


# ===========================================================================
# main
# ===========================================================================

def main():
    print("=" * 78)
    print("ROUND 133 — MORE SPX NATIVE STRUCTURE: OPTIONS-EXPIRY WEEK, GAP MAGNITUDE")
    print("=" * 78)

    frames = {tag: {} for tag in ("SPY", "ES", "QQQ")}
    meta = {tag: {} for tag in ("SPY", "ES", "QQQ")}
    for tag in ("SPY", "ES", "QQQ"):
        frames[tag]["1d"] = C.load_symbol(tag, "1d")
        meta[tag]["1d"] = C.span_meta(frames[tag]["1d"])

    print("\nPART A1 — options-expiry-week AUDIT (report-only, train+val, test sealed)")
    a1_df = pd.DataFrame(run_part_a_audit(frames, meta))
    print(a1_df.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))

    print("\nPART A2 — options-expiry-week STRATEGY")
    a2_df = pd.DataFrame(run_part_a_strategy(frames, meta))
    cols = ["config", "symbol", "tr_n", "tr_exp", "tr_win%", "va_n", "va_exp", "va_win%", "verdict"]
    print(a2_df[cols].to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\nPART B — gap magnitude vs same-day intraday range (report-only, stop-sizing input)")
    b_df = pd.DataFrame(run_part_b(frames, meta))
    print(b_df.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))

    a1_df.to_csv("step133_table_partA1_expiry_audit.csv", index=False)
    a2_df.to_csv("step133_table_partA2_expiry_strategy.csv", index=False)
    b_df.to_csv("step133_table_partB_gap_range.csv", index=False)

    print("\nDone. No sealed-test window touched.")
    return a1_df, a2_df, b_df


if __name__ == "__main__":
    main()
