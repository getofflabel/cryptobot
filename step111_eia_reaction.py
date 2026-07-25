"""
step111_eia_reaction.py — Round 111: THE EIA REACTION TEST ROUND 78 NEVER RAN.

QUESTION: does CL=F price react SYSTEMATICALLY around (a) the weekly EIA
Petroleum Status Report (official release, Wednesdays ~10:30am ET, shifted
to Thursday on weeks with a federal holiday) and (b) the unofficial API
inventory estimate (Tuesdays ~4:30pm ET, same holiday shift) — direction,
magnitude, decay — versus a randomized-timing chance baseline? This is
oil's closest analogue to the crypto desk's WatcherGuru news-reaction
study (step45b_news_events.py) — reused here, not reinvented:
`align_events` (no-lookahead: floor to the last bar whose OPEN <= event
time, trade at the NEXT bar's open) and `event_study` (mean/median |move|
at each horizon vs an UNCONDITIONAL same-window baseline, i.e. the
ratio-vs-baseline IS a chance baseline already) are IMPORTED UNCHANGED
from that file. This script adds one thing step45b didn't need: an
explicit second control (N random timestamps, same count as the real
event list, drawn from the same market-open span, re-run through the
exact same machinery) — belt-and-suspenders on top of the baked-in
baseline, because the brief asks for a randomized-timing control by name.

EVENT CALENDAR — documented approximation, stated plainly (no scraped EIA
calendar was available; built from pandas' USFederalHolidayCalendar,
which is itself a documented approximation of the real US federal holiday
set):
  EIA official report: Wednesday 10:30 ET normally; shifts to Thursday
    10:30 ET if that week's Monday OR Wednesday is a federal holiday
    (matches the real-world pattern for MLK/Presidents/Memorial/Labor/
    Columbus Day (Monday holidays) and Juneteenth/Christmas/New Year's
    when they land on a Wednesday). Thanksgiving week is NOT shifted
    under this rule (Thursday itself being the holiday, Wed is a normal
    business day) — this matches the real EIA calendar.
  API estimate: Tuesday 16:30 ET normally; shifts to Wednesday 16:30 ET
    under the same Monday/Tuesday-holiday condition.
  Wall-clock ET->UTC conversion uses zoneinfo (America/New_York, real DST
    transitions) — NOT the fixed-UTC-4 approximation tradfi_engine.py
    uses elsewhere in this repo; that approximation is fine for a coarse
    "is the market open" gate, wrong for pinning an event to the correct
    UTC hour, so it is not reused here.

DATA: data_oil_CL_1h.parquet (yfinance CL=F, 2024-03-01 -> 2026-07-24,
the same instrument/source the live book itself scores). This bounds the
event count to ~2.4 years of Wednesdays/Tuesdays (~120 of each) — stated
honestly against the 30/8 floor below.

RESEARCH ONLY. No commits, no live orders. Writes ONLY
step111_eia_reaction.py (this file), step111_results.md,
step111_table.csv.
"""

from __future__ import annotations

from datetime import datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

from step45b_news_events import align_events, event_study

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

MIN_TRAIN_TRADES = 30   # not a trade gauntlet here, but the same floor
MIN_VAL_TRADES = 8      # convention is applied to event counts for consistency


# ---------------------------------------------------------------------------
# event calendar
# ---------------------------------------------------------------------------

def _federal_holidays(start: str, end: str) -> set:
    cal = USFederalHolidayCalendar()
    return set(d.date() for d in cal.holidays(start=start, end=end))


def build_event_calendar(start: pd.Timestamp, end: pd.Timestamp):
    """Returns (eia_ts, api_ts) — UTC-aware event timestamp lists across
    [start, end], one per ISO week, with the holiday-shift rule applied
    (see module docstring)."""
    holidays = _federal_holidays(
        (start - timedelta(days=10)).strftime("%Y-%m-%d"),
        (end + timedelta(days=10)).strftime("%Y-%m-%d"))

    eia_ts, api_ts = [], []
    # walk week by week from the Monday on/before `start`
    monday = (start - timedelta(days=start.weekday())).normalize()
    cur = monday
    while cur <= end:
        mon, tue, wed, thu = [(cur + timedelta(days=k)).date() for k in (0, 1, 2, 3)]
        eia_day = thu if (mon in holidays or wed in holidays) else wed
        api_day = wed if (mon in holidays or tue in holidays) else tue
        eia_dt = datetime.combine(eia_day, dtime(10, 30), tzinfo=ET).astimezone(UTC)
        api_dt = datetime.combine(api_day, dtime(16, 30), tzinfo=ET).astimezone(UTC)
        eia_ts.append(pd.Timestamp(eia_dt))
        api_ts.append(pd.Timestamp(api_dt))
        cur += timedelta(days=7)
    eia_ts = [t for t in eia_ts if start <= t <= end]
    api_ts = [t for t in api_ts if start <= t <= end]
    return eia_ts, api_ts


# ---------------------------------------------------------------------------
# randomized-timing control
# ---------------------------------------------------------------------------

def random_control_ts(candles: pd.DataFrame, n: int, exclude_ts: list,
                       seed: int = 111) -> list:
    """n random UTC timestamps drawn uniformly from the candle span,
    excluding any hour within 4h of a real event (so the control isn't
    accidentally contaminated by the very reaction it's supposed to be
    the baseline for)."""
    rng = np.random.default_rng(seed)
    ts_all = candles["timestamp"]
    lo, hi = ts_all.iloc[24], ts_all.iloc[-25]   # keep clear of series edges
    exclude = pd.DatetimeIndex(exclude_ts)
    out = []
    tries = 0
    while len(out) < n and tries < n * 50:
        tries += 1
        offset_h = rng.integers(0, int((hi - lo).total_seconds() // 3600))
        cand = lo + timedelta(hours=int(offset_h))
        if (np.abs((exclude - cand).total_seconds()) < 4 * 3600).any():
            continue
        out.append(cand)
    return out


# ---------------------------------------------------------------------------
# direction / momentum-vs-fade test
# ---------------------------------------------------------------------------

def direction_test(d: pd.DataFrame, trading_idx: np.ndarray, valid: np.ndarray,
                   follow_bars: int = 4) -> dict:
    """Does the SIGN of the immediate reaction bar (trading_idx's own
    open->close) predict the next `follow_bars` bars' cumulative return
    (continuation) or its opposite (fade)? Reports conditional mean
    returns by reaction-bar sign, plus the unconditional mean for
    comparison — the chance-level expectation if sign carried no
    information."""
    opens, closes = d["open"].to_numpy(), d["close"].to_numpy()
    n = len(d)
    idxs = trading_idx[valid]
    idxs = idxs[(idxs >= 0) & (idxs + follow_bars < n)]
    if len(idxs) == 0:
        return {"n": 0}
    react_ret = (closes[idxs] / opens[idxs] - 1) * 100
    fwd_ret = (closes[idxs + follow_bars] / closes[idxs] - 1) * 100
    pos = react_ret > 0
    neg = react_ret < 0
    return {
        "n": len(idxs),
        "n_pos_reaction": int(pos.sum()), "n_neg_reaction": int(neg.sum()),
        "fwd_ret_after_pos_%": float(fwd_ret[pos].mean()) if pos.any() else float("nan"),
        "fwd_ret_after_neg_%": float(fwd_ret[neg].mean()) if neg.any() else float("nan"),
        "fwd_ret_unconditional_%": float(fwd_ret.mean()),
        "corr_react_vs_fwd": float(np.corrcoef(react_ret, fwd_ret)[0, 1]) if len(idxs) > 2 else float("nan"),
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

HORIZONS = {"1h": 1, "2h": 2, "4h": 4, "24h": 24}


def run_one(label: str, d: pd.DataFrame, event_ts: list, control_ts: list) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    floor_idx, trading_idx, valid = align_events(d, event_ts)
    tag_masks = {label: np.ones(len(event_ts), dtype=bool)}
    real_study = event_study(d, trading_idx, valid, tag_masks, HORIZONS)

    cfloor_idx, ctrading_idx, cvalid = align_events(d, control_ts)
    ctag_masks = {f"{label}_random_control": np.ones(len(control_ts), dtype=bool)}
    control_study = event_study(d, ctrading_idx, cvalid, ctag_masks, HORIZONS)

    dirn = direction_test(d, trading_idx, valid, follow_bars=4)
    return real_study, control_study, dirn


def main():
    d = pd.read_parquet("data_oil_CL_1h.parquet").reset_index(drop=True)
    start, end = d["timestamp"].iloc[0], d["timestamp"].iloc[-1]
    eia_ts, api_ts = build_event_calendar(start, end)
    print("=" * 78)
    print("ROUND 111 — EIA / API INVENTORY REACTION TEST (CL=F, 1h bars)")
    print("=" * 78)
    print(f"\nData span: {start} -> {end}")
    print(f"EIA events in span: {len(eia_ts)} | API events in span: {len(api_ts)}")
    if len(eia_ts) < MIN_VAL_TRADES:
        print("INSUFFICIENT SAMPLE on EIA events outright — stopping.")
        return

    n_shift_eia = sum(1 for t in eia_ts if t.tz_convert(ET).weekday() == 3)
    n_shift_api = sum(1 for t in api_ts if t.tz_convert(ET).weekday() == 2)
    print(f"Holiday-shifted to Thursday: {n_shift_eia}/{len(eia_ts)} EIA events | "
          f"shifted to Wednesday: {n_shift_api}/{len(api_ts)} API events")

    control_ts = random_control_ts(d, max(len(eia_ts), len(api_ts)) * 2,
                                   exclude_ts=eia_ts + api_ts)
    print(f"Randomized-timing control pool: {len(control_ts)} timestamps "
          f"(>=4h clear of any real EIA/API event)")

    all_rows = []
    for label, ts_list in (("EIA", eia_ts), ("API", api_ts)):
        ctrl = control_ts[: len(ts_list)]
        real_study, control_study, dirn = run_one(label, d, ts_list, ctrl)
        print(f"\n--- {label} (n_events={len(ts_list)}) ---")
        print(real_study.to_string(index=False))
        print(f"  [chance: same n random timestamps, same machinery]")
        print(control_study.to_string(index=False))
        all_rows.append(real_study.assign(source=label))
        all_rows.append(control_study.assign(source=f"{label}_control"))

        print(f"\n  DIRECTION/DECAY test (reaction-bar sign vs next-4h return, "
              f"n={dirn.get('n', 0)}):")
        if dirn.get("n", 0) >= MIN_VAL_TRADES:
            print(f"    after a POSITIVE reaction bar (n={dirn['n_pos_reaction']}): "
                  f"next 4h avg {dirn['fwd_ret_after_pos_%']:+.3f}%")
            print(f"    after a NEGATIVE reaction bar (n={dirn['n_neg_reaction']}): "
                  f"next 4h avg {dirn['fwd_ret_after_neg_%']:+.3f}%")
            print(f"    unconditional next-4h avg: {dirn['fwd_ret_unconditional_%']:+.3f}% "
                  f"| corr(reaction, next-4h) = {dirn['corr_react_vs_fwd']:+.3f}")
            if dirn['fwd_ret_after_pos_%'] > 0 and dirn['fwd_ret_after_neg_%'] < 0:
                print("    -> shape: CONTINUATION (reaction direction persists)")
            elif dirn['fwd_ret_after_pos_%'] < 0 and dirn['fwd_ret_after_neg_%'] > 0:
                print("    -> shape: FADE (reaction direction reverses)")
            else:
                print("    -> shape: NO CLEAR SIGN PATTERN")
        else:
            print(f"    INSUFFICIENT SAMPLE (n={dirn.get('n', 0)} < {MIN_VAL_TRADES})")

    # decay: ratio_vs_baseline across horizons for EIA
    eia_real, _, _ = run_one("EIA", d, eia_ts, control_ts[:len(eia_ts)])
    print("\n--- DECAY (EIA real events, ratio_vs_baseline across horizons) ---")
    for _, row in eia_real.iterrows():
        print(f"  {row['horizon']:>4}: mean|move|={row['mean_abs_move_%']:.3f}% "
              f"vs baseline {row['baseline_mean_abs_%']:.3f}% "
              f"-> ratio {row['ratio_vs_baseline']:.2f}x")

    out = pd.concat(all_rows, ignore_index=True)
    out.to_csv("step111_table.csv", index=False)
    print("\nWrote step111_table.csv.")


if __name__ == "__main__":
    main()
