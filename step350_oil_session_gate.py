"""
step350_oil_session_gate.py -- ROUND 350 (oil-trader, 2026-07-25).

THE QUESTION, IN ONE SENTENCE
Oil's London and New York hours are the only oil-specific, statistically
real thing this desk has ever measured about oil. Does restricting entries
to those hours turn a simple losing entry shape into a working one on
CL=F 1-hour bars, or does it just concentrate the same nothing?

WHY THIS ROUND EXISTS
RESEARCH_QUEUE.md, "OPEN AND UNRESOLVED": "Session structure on oil:
London/NY hours sit at the 100th percentile of realized |return| against a
200-draw shuffle control, Asia/off-hours at the 0th. Real, oil-specific,
and nothing has been built on it." Round 113 measured it and stopped.
Rounds 116 and 117 swept entries and exits with no session gate at all.
Nobody has ever asked whether the gate PAYS.

A session restriction is not a strategy on its own -- it is a filter with
no entry rule and no exit rule. So it is paired here with three simple
entry shapes and two chart-structure exits, and the whole thing is run
three ways: all hours, London+New York only, and Asia+off-hours only.
That third arm is the placebo. If the effect is real and useful, the
London/NY arm should beat the all-hours arm and the Asia arm should be the
worst of the three. If the three arms look the same, the gate does nothing
and this line of enquiry is finished.

EVERY CONSTANT RE-DERIVED ON OIL'S OWN TRAIN SLICE (nothing carried)
Measured on CL=F 1h, TRAIN WINDOW ONLY (2024-03-01 -> 2025-08-11, 8,116
bars), before a single backtest was run:
  - 1h bar range, high minus low, as a percent of price: median 0.4301,
    75th percentile 0.6748, 90th percentile 0.9897.
  - RSI(2) on 1h closes: 10th percentile 7.3, 90th percentile 93.4.
    (WHAT IT WAS BEFORE: the S&P book used RSI(2) below 10 and BTC's
    step150d used an RSI(3) washout level -- both derived on those
    markets. Neither number is used here.)
  - ATR(14) on 1h as a percent of price: median 0.4909.
    (WHAT IT WAS BEFORE: BTC's volatility gate is a 1.5% ATR threshold.
    The research queue already records that carrying it to SOL left the
    gate open on 96.7% of bars versus 18-53% on BTC -- the selectivity
    WAS the edge. It is not carried here.)
  - Session realized movement, train slice only, 200-draw label-shuffle
    control: Asia (00-07 UTC) mean absolute 1h move 0.1676% of price,
    0th percentile of the shuffle. London (07-12 UTC) 0.3132%, 100th
    percentile. New York (12-21 UTC) 0.3548%, 100th percentile.
    Off/maintenance (21-24 UTC) 0.1780%, 0th percentile. The queue's
    finding reproduces on the train slice alone.

DATA AND SPLIT
CL=F 1h, 13,527 bars, 2024-03-01 05:00 UTC -> 2026-07-24 20:00 UTC (2.40
years -- the only intraday oil history this repo holds). Chronological
60/20/20:
  train  8,116 bars  2024-03-01 05:00 -> 2025-08-11 18:00
  val    2,705 bars  2025-08-11 19:00 -> 2026-02-04 04:00
  sealed 2,706 bars  2026-02-04 05:00 -> 2026-07-24 20:00
THE SEALED SLICE IS TRUNCATED OFF THE DATAFRAME IN load_oil() BEFORE ANY
OTHER CODE SEES IT. It is not read, not scored, not plotted.

DISCIPLINE
- Market orders only. Every entry and every exit crosses the spread and
  pays the taker fee (step150_common.run_edge, CostModel default).
- Stops are chart levels from exits.py -- the confirmed swing low for a
  long, the confirmed swing high for a short, or a ratcheting floor made
  of those same confirmed swings. Never a swept percentage. Size =
  dollars risked / stop distance; leverage is an output, capped at the
  desk's real 20x ceiling.
- All 18 cells are screened on TRAIN ONLY. The three-arm session
  comparison -- which is this round's actual headline -- is decided
  entirely on train numbers and costs no validation look.
- Validation is read exactly ONCE, for the single best train cell only.
- Random-entry controls run with the SAME exit apparatus and the SAME
  costs, in two flavours: entries scattered across ALL hours, and entries
  scattered across LONDON/NY HOURS ONLY. The second one is the control
  that matters -- if random entries confined to the same hours do as well
  as the entry shape, then the shape contributes nothing and only the
  clock was ever doing any work.
- Cross-instrument replay of the selected cell, unchanged, on BZ=F
  (Brent) 1h with Brent's own 60/20/20 split points. WTIOIL-USDT is NOT
  the replay venue: only 1,386 hourly bars are cached (about 58 days),
  which cannot support a 60/20/20 split with a 30-trade floor.

SESSION BOUNDARIES ARE IN UTC AND FIXED YEAR-ROUND. Real New York hours
shift by one hour across US daylight-saving changes, so the 12:00-21:00
UTC block is a documented approximation, the same one round 113 used.
It is a coarse "is this the active part of oil's day" gate, not an
order router.

RESEARCH ONLY. No live orders. No live bot file is imported for writing or
edited by this script. Outputs: step350_table.csv, step350_results.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import exits as E
from backtest import CostModel
from step150_common import (fmt_stats, mask_to_events, run_edge,
                            split_points, thickness, trade_stats)

# ---------------------------------------------------------------------------
# constants re-derived on oil's own TRAIN slice (see module docstring)
# ---------------------------------------------------------------------------

OIL_TRAIN_RANGE_MEDIAN_PCT = 0.4301   # CL=F 1h high-low as % of price, train median
OIL_TRAIN_RSI2_P10 = 7.3              # CL=F 1h RSI(2) 10th percentile, train
OIL_TRAIN_RSI2_P90 = 93.4             # CL=F 1h RSI(2) 90th percentile, train

BREAKOUT_LOOKBACK_H = 24              # one full oil trading day, structural not swept
MAX_HOLD_BARS = 24                    # one full oil trading day
RANGE_EXPANSION_MULT = 2.0            # "twice a normal oil hour", applied to oil's own median
CLOSE_LOCATION_FRAC = 0.25            # close in the top/bottom quarter of the bar

# session blocks, UTC, from round 113's own oil-specific definition
SESSION_FILTERS = {
    "all_hours":  None,
    "london_ny":  set(range(7, 21)),   # London 07-12 + New York 12-21 UTC
    "asia_off":   set(list(range(0, 7)) + [21, 22, 23]),   # the placebo arm
}

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

def load_oil(path: str = "data_oil_CL_1h.parquet") -> tuple[pd.DataFrame, int, int]:
    """Loads CL=F 1h and IMMEDIATELY DROPS THE SEALED FINAL 20%. Nothing
    downstream of this function can see the sealed slice."""
    d = pd.read_parquet(path)
    d["timestamp"] = pd.to_datetime(d["timestamp"], utc=True)
    d = d.sort_values("timestamp").reset_index(drop=True)
    n_full, i_tr, i_va = split_points(d)
    sealed_n = n_full - i_va
    d = d.iloc[:i_va].reset_index(drop=True)      # sealed slice gone, permanently
    return d, i_tr, sealed_n


def load_generic(path: str) -> tuple[pd.DataFrame, int, int]:
    d = pd.read_parquet(path)
    d["timestamp"] = pd.to_datetime(d["timestamp"], utc=True)
    d = d.sort_values("timestamp").reset_index(drop=True)
    n_full, i_tr, i_va = split_points(d)
    sealed_n = n_full - i_va
    d = d.iloc[:i_va].reset_index(drop=True)
    return d, i_tr, sealed_n


# ---------------------------------------------------------------------------
# entry shapes -- each returns a (bar_idx, direction) event list on the
# frame it is handed. All are computed on the ALREADY-SLICED frame so no
# indicator can see across the train/val boundary.
# ---------------------------------------------------------------------------

def _rsi(s: pd.Series, n: int) -> pd.Series:
    delta = s.diff()
    up = delta.clip(lower=0)
    dn = (-delta).clip(lower=0)
    ru = up.ewm(alpha=1 / n, adjust=False).mean()
    rd = dn.ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + ru / rd.replace(0, np.nan))


def shape_breakout_24h(d: pd.DataFrame):
    hi = d["high"].rolling(BREAKOUT_LOOKBACK_H).max().shift(1)
    lo = d["low"].rolling(BREAKOUT_LOOKBACK_H).min().shift(1)
    el = (d["close"] > hi).fillna(False)
    es = (d["close"] < lo).fillna(False)
    return el, es


def shape_rsi2_reversion(d: pd.DataFrame):
    sma100 = d["close"].rolling(100).mean()
    r2 = _rsi(d["close"], 2)
    el = ((r2 < OIL_TRAIN_RSI2_P10) & (d["close"] > sma100)).fillna(False)
    es = ((r2 > OIL_TRAIN_RSI2_P90) & (d["close"] < sma100)).fillna(False)
    return el, es


def shape_range_expansion(d: pd.DataFrame):
    rng_pct = (d["high"] - d["low"]) / d["close"] * 100
    gate = RANGE_EXPANSION_MULT * OIL_TRAIN_RANGE_MEDIAN_PCT
    wide = rng_pct > gate
    span = (d["high"] - d["low"]).replace(0, np.nan)
    loc = (d["close"] - d["low"]) / span              # 1.0 = closed on the high
    el = (wide & (loc >= 1 - CLOSE_LOCATION_FRAC)).fillna(False)
    es = (wide & (loc <= CLOSE_LOCATION_FRAC)).fillna(False)
    return el, es


SHAPES = {
    "breakout_24h":     shape_breakout_24h,
    "rsi2_reversion":   shape_rsi2_reversion,
    "range_expansion":  shape_range_expansion,
}


def entries_for(d: pd.DataFrame, shape: str, session: str) -> list[tuple[int, int]]:
    el, es = SHAPES[shape](d)
    hours = SESSION_FILTERS[session]
    if hours is not None:
        hr = pd.DatetimeIndex(d["timestamp"]).hour
        ok = pd.Series([h in hours for h in hr], index=d.index)
        el = el & ok
        es = es & ok
    both = el | es
    direction = pd.Series(np.where(el, 1, np.where(es, -1, 0)), index=d.index)
    return mask_to_events(both, direction)


# ---------------------------------------------------------------------------
# exits -- chart structure only
# ---------------------------------------------------------------------------

def stop_builder_trail(tc):
    """Ratcheting floor made of confirmed swings; rides until the chart
    says stop."""
    return E.stop_structure_trailing(buffer_pct=0.0, fallback_pct=5.0)


def stop_builder_fixed(tc):
    """Parked beyond the confirmed swing low (long) / swing high (short)
    the entry rests on. Returns None when no confirmed swing exists yet,
    which run_edge counts as 'no real stop available, do not trade'."""
    return E.stop_structure(k=5, n_back=1, buffer_pct=0.0, use="wick")


def target_2r(stop):
    return E.target_fixed_r(stop, 2.0)


EXITS = {
    # name: (stop_builder, target_builder)
    "structure_trail_only": (stop_builder_trail, None),
    "structure_stop_2R":    (stop_builder_fixed, target_2r),
}


# ---------------------------------------------------------------------------
# random-entry controls
# ---------------------------------------------------------------------------

def random_control(d: pd.DataFrame, n_events: int, direction_mix: float,
                   stop_builder, target_builder, session: str,
                   draws: int = 100, seed: int = 350, k: int = 5) -> dict:
    """Entries at random times, same exit apparatus, same costs, same trade
    count. `session` restricts which bars the random entries may land on,
    so the London/New-York arm can be compared against random entries in
    THE SAME HOURS -- the only control that separates 'the entry shape
    works' from 'those hours simply move more'."""
    rng = np.random.default_rng(seed)
    n = len(d)
    lo, hi = k + 5, n - 5
    if hi <= lo or n_events <= 0:
        return dict(mean_exp=0.0, n_draws=0, sample_events=n_events, pool=0)
    pool = np.arange(lo, hi)
    hours = SESSION_FILTERS[session]
    if hours is not None:
        hr = pd.DatetimeIndex(d["timestamp"]).hour.to_numpy()
        pool = pool[np.isin(hr[pool], list(hours))]
    if len(pool) == 0:
        return dict(mean_exp=0.0, n_draws=0, sample_events=n_events, pool=0)
    exps = []
    for _ in range(draws):
        take = min(n_events, len(pool))
        idxs = rng.choice(pool, size=take, replace=False)
        dirs = (rng.random(take) < direction_mix).astype(int) * 2 - 1
        trades, _ = run_edge(d, list(zip(idxs.tolist(), dirs.tolist())),
                             stop_builder, target_builder, MAX_HOLD_BARS, k=k)
        if trades:
            exps.append(float(np.mean([t["pnl"] for t in trades])))
    arr = np.array(exps) if exps else np.array([0.0])
    return dict(mean_exp=float(arr.mean()), p90=float(np.percentile(arr, 90)),
                n_draws=len(exps), sample_events=n_events, pool=int(len(pool)))


# ---------------------------------------------------------------------------
# the grid
# ---------------------------------------------------------------------------

def screen_train(d: pd.DataFrame, i_tr: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    d_tr = d.iloc[:i_tr].reset_index(drop=True)
    d_va = d.iloc[i_tr:].reset_index(drop=True)
    rows = []
    print("\n" + "=" * 78)
    print("TRAIN-ONLY SCREEN -- 3 entry shapes x 3 session arms x 2 chart-structure exits")
    print("=" * 78)
    for shape in SHAPES:
        for exit_name, (sb, tb) in EXITS.items():
            line = []
            for session in SESSION_FILTERS:
                ev = entries_for(d_tr, shape, session)
                trades, skipped = run_edge(d_tr, ev, sb, tb, MAX_HOLD_BARS)
                st = trade_stats(trades)
                th = thickness(st["expectancy"], st["avg_notional"])
                rows.append(dict(
                    shape=shape, exit=exit_name, session=session,
                    signals=len(ev), tr_n=st["n"], tr_exp=st["expectancy"],
                    tr_win_pct=st["win_rate"] * 100, tr_avg_lev=st["avg_leverage"],
                    tr_med_hold_h=st["median_hold_h"],
                    tr_pct_of_position=th["pct_notional"],
                    tr_cost_multiple_12bps=th["mult_12bps"],
                    skipped_no_structure=skipped))
                line.append(f"{session}:{st['n']}t/${st['expectancy']:+.2f}")
            print(f"  {shape:16s} {exit_name:22s} " + " | ".join(line))
    return pd.DataFrame(rows), d_tr, d_va


def main():
    d, i_tr, sealed_n = load_oil()
    t = pd.DatetimeIndex(d["timestamp"])
    print(f"CL=F 1h -- loaded {len(d)} bars {t[0]} -> {t[-1]}")
    print(f"  train {i_tr} bars | val {len(d) - i_tr} bars | "
          f"sealed {sealed_n} bars TRUNCATED AT LOAD, never seen by this script")

    grid, d_tr, d_va = screen_train(d, i_tr)
    grid.to_csv("step350_table.csv", index=False)

    # ---- the headline comparison, decided on TRAIN only, no validation look
    print("\n" + "=" * 78)
    print("DOES THE CLOCK PAY? per (shape, exit): London/NY vs all hours vs Asia/off")
    print("=" * 78)
    verdicts = []
    for shape in SHAPES:
        for exit_name in EXITS:
            sub = grid[(grid["shape"] == shape) & (grid["exit"] == exit_name)]
            g = {r["session"]: r for _, r in sub.iterrows()}
            a, l, z = g["all_hours"], g["london_ny"], g["asia_off"]
            better = l["tr_exp"] > a["tr_exp"]
            placebo_worst = z["tr_exp"] <= min(a["tr_exp"], l["tr_exp"])
            verdicts.append(dict(shape=shape, exit=exit_name,
                                 all_exp=a["tr_exp"], ldn_exp=l["tr_exp"], asia_exp=z["tr_exp"],
                                 london_beats_all=better, asia_is_worst=placebo_worst))
            print(f"  {shape:16s} {exit_name:22s} all=${a['tr_exp']:+7.2f}({int(a['tr_n'])}t)  "
                  f"ldn/ny=${l['tr_exp']:+7.2f}({int(l['tr_n'])}t)  asia/off=${z['tr_exp']:+7.2f}({int(z['tr_n'])}t)  "
                  f"-> gate helps: {better} | placebo worst: {placebo_worst}")
    vdf = pd.DataFrame(verdicts)
    print(f"\n  London/NY beat all-hours in {int(vdf.london_beats_all.sum())}/{len(vdf)} of the "
          f"(shape, exit) pairs; the Asia/off placebo arm was the worst of the three in "
          f"{int(vdf.asia_is_worst.sum())}/{len(vdf)}.")
    print("  Coin-flip expectation if the clock did nothing: 3/6 and 2/6 respectively.")

    # ---- selection, TRAIN only, London/NY arm only (that is the hypothesis)
    print("\n" + "=" * 78)
    print("SELECTION (train only, London/NY arm -- that is the hypothesis under test)")
    print("=" * 78)
    pool = grid[(grid["session"] == "london_ny") & (grid["tr_n"] >= MIN_TRAIN_TRADES)
                & (grid["tr_exp"] > 0)]
    if pool.empty:
        print(f"  NO London/NY cell clears the train floor (at least {MIN_TRAIN_TRADES} trades "
              f"AND positive average profit per trade, losers included) out of "
              f"{len(grid[grid['session'] == 'london_ny'])} screened.")
        print("  VALIDATION SLICE NOT READ FOR ANY CELL. Plain answer: the session gate does "
              "not convert any of these shapes into a working one.")
        return grid, vdf, None
    best = pool.sort_values("tr_exp", ascending=False).iloc[0]
    shape, exit_name = best["shape"], best["exit"]
    sb, tb = EXITS[exit_name]
    print(f"  SELECTED: {shape} + {exit_name} + london_ny  "
          f"(train n={int(best.tr_n)}, avg profit per trade ${best.tr_exp:+.2f}, "
          f"{best.tr_cost_multiple_12bps:.2f}x round-trip cost)")
    print(f"  Cleared the train floor: {len(pool)}/{len(grid[grid['session'] == 'london_ny'])} "
          f"London/NY cells.")

    # train-window random controls (free -- no validation look)
    tr_events = entries_for(d_tr, shape, "london_ny")
    tr_trades, _ = run_edge(d_tr, tr_events, sb, tb, MAX_HOLD_BARS)
    dmix = float(np.mean([1 if t["direction"] > 0 else 0 for t in tr_trades])) if tr_trades else 0.5
    ctl_tr_ldn = random_control(d_tr, len(tr_trades), dmix, sb, tb, "london_ny", draws=100)
    ctl_tr_all = random_control(d_tr, len(tr_trades), dmix, sb, tb, "all_hours", draws=100, seed=351)
    print(f"  TRAIN control, entries at random times inside London/NY hours, same exit: "
          f"${ctl_tr_ldn['mean_exp']:+.2f}/trade over {ctl_tr_ldn['n_draws']} draws")
    print(f"  TRAIN control, entries at random times across all hours, same exit: "
          f"${ctl_tr_all['mean_exp']:+.2f}/trade over {ctl_tr_all['n_draws']} draws")

    # ---- VALIDATION, READ ONCE
    print("\n" + "=" * 78)
    print("VALIDATION SLICE -- READ ONCE, FOR THIS ONE CELL ONLY")
    print("=" * 78)
    va_events = entries_for(d_va, shape, "london_ny")
    va_trades, va_skipped = run_edge(d_va, va_events, sb, tb, MAX_HOLD_BARS)
    va = trade_stats(va_trades)
    th = thickness(va["expectancy"], va["avg_notional"])
    print("  " + fmt_stats("val", va))
    print(f"  profit per trade as a share of the full position size: {th['pct_notional']:+.3f}%")
    print(f"  how many times bigger the profit is than the cost of trading: "
          f"{th['mult_12bps']:.2f}x (fees only, market orders both legs) / "
          f"{th['mult_full_18bps']:.2f}x (fees + spread + slippage)")
    dmix_v = float(np.mean([1 if t["direction"] > 0 else 0 for t in va_trades])) if va_trades else 0.5
    ctl_va_ldn = random_control(d_va, len(va_trades), dmix_v, sb, tb, "london_ny", draws=200, seed=352)
    ctl_va_all = random_control(d_va, len(va_trades), dmix_v, sb, tb, "all_hours", draws=200, seed=353)
    print(f"  VAL control, random times inside London/NY hours: ${ctl_va_ldn['mean_exp']:+.2f}/trade "
          f"(90th percentile of draws ${ctl_va_ldn.get('p90', 0):+.2f})")
    print(f"  VAL control, random times across all hours:       ${ctl_va_all['mean_exp']:+.2f}/trade "
          f"(90th percentile of draws ${ctl_va_all.get('p90', 0):+.2f})")

    passed = (best.tr_exp > 0 and va["expectancy"] > 0 and int(best.tr_n) >= MIN_TRAIN_TRADES
              and va["n"] >= MIN_VAL_TRADES and th["mult_12bps"] >= 5.0
              and va["expectancy"] > ctl_va_ldn["mean_exp"])
    print(f"\n  VERDICT: {'PASS all four gates' if passed else 'FAIL'} "
          f"(positive both windows, enough trades, at least 5x the cost of trading, "
          f"and beats random entries in the same hours)")

    # ---- cross-instrument replay, unchanged
    print("\n" + "=" * 78)
    print("SAME RULE ON A DIFFERENT MARKET -- BZ=F (Brent) 1h, unchanged, own 60/20/20")
    print("=" * 78)
    try:
        db, ib_tr, _ = load_generic("data_oil_BZ_1h.parquet")
        db_tr = db.iloc[:ib_tr].reset_index(drop=True)
        db_va = db.iloc[ib_tr:].reset_index(drop=True)
        for lbl, frame in (("train", db_tr), ("val", db_va)):
            ev = entries_for(frame, shape, "london_ny")
            trs, _ = run_edge(frame, ev, sb, tb, MAX_HOLD_BARS)
            stb = trade_stats(trs)
            thb = thickness(stb["expectancy"], stb["avg_notional"])
            print("  Brent " + fmt_stats(lbl, stb) +
                  f" | {thb['mult_12bps']:.2f}x cost")
    except Exception as e:
        print(f"  Brent replay unavailable: {e}")

    return grid, vdf, dict(shape=shape, exit=exit_name, val=va, thickness=th,
                           ctl_va_ldn=ctl_va_ldn, ctl_va_all=ctl_va_all, passed=passed)


if __name__ == "__main__":
    main()
