"""
step88_veto_robustness.py — ROUND 88: IS THE VETO WE SHIPPED TONIGHT REAL,
OR TWO LUCKY CELLS?

R83 tested 6 strategies x 2 assets x 3 veto variants = 36 cells against a
200-draw random-skip control. Exactly 2 cells cleared the 98th percentile:
`veto_messy` (skip the washout dip-buy when chart_reader reads the chart as
"messy") on strategy B (RSI3<10 washout dip-buy, daily_pick.py) on BTC and
on ETH. On the strength of those 2 cells, daily_pick.score_instrument now
drops the washout vote live when the eye reads "messy" (see daily_pick.py
line ~371-393, "THE EYE'S ONE SANCTIONED VETO (round 83)").

With 36 cells, ~0.7 cells are EXPECTED to clear the 98th percentile by pure
chance (36 * 0.02 = 0.72). Getting 2 is not remotely extraordinary on its
own. The only thing that argues it is real is that both hits are the SAME
strategy on two DIFFERENT assets. This script runs three independent
robustness attacks against that one shipped conclusion:

  1. THIRD+ ASSET REPLAY — same exact spec (RSI3<10, 1h, turn-candle guard,
     daily_pick.py line ~366) on every other asset with adequate cached
     Bybit history: SOL, XRP, DOGE. If the veto is real it should help on
     assets it was never selected on.

  2. FAMILY SWEEP — R83 tested ONE washout spec. This sweeps RSI period
     {2,3,5} x threshold {5,10,15,20} x with/without the turn-candle guard,
     on BTC/ETH/SOL, 1h. A real effect should show a broad plateau of
     improvement across nearby settings; a spike only at exactly RSI3<10
     is a strong fluke signal.

  3. TIME-SPLIT — the exact BTC and ETH washout trade lists R83 scored,
     split chronologically in half. Does veto_messy beat the random
     control in BOTH halves independently, or is the whole effect carried
     by one era?

DISCIPLINE: every function that already exists in step83_eye_filter.py is
IMPORTED, not retyped — frame_for/funding_hist_for/eye_for/ts_idx_for (the
eye cache + causal timestamp index), daily_trend_on_tf (the 1d trend gate),
run_split/trades_from_backtest (the exact backtest wiring B already uses),
dumb_control/summarize (the exact 200-draw random-skip control math), and
every one of B's live constants (WASHOUT_RSI_N/TH, STOP_ATR_MULT,
STOP_CAP_PCT, STOP_FLOOR_PCT, TARGET_STOP_MULT, WASHOUT_MAX_HOLD_H). The
only new code here is build_washout() — B's build_B() generalized to take
RSI period / threshold / turn-guard as parameters instead of hardcoding
them, so the family sweep doesn't retype the strategy six times — and it is
verified in main() to reproduce build_B's own BTC numbers bit-for-bit at
the default parameters before anything else runs.

The eye itself is step82_eye.label_eye_states, used exactly as R83 used
it: computed once per (asset, 1h) on the full causal history via
step83_eye_filter.eye_for(), so a trade's eye read is always looked up at
its own entry bar with no lookahead.

Same backtest engine (backtest.run_backtest, full costs, real funding,
maker execution) as R83, via the same run_split() wrapper. Same 200-draw
random-skip control on every cell (step83_eye_filter.dumb_control,
N_CONTROL_DRAWS=200). Same chronological 60/20/20 split
(step43_daytrade.split_points) with the sealed 20% test slice never
touched -- every trade list built here is train+val only, exactly as
build_B() itself already drops the test slice before returning.

RESEARCH ONLY. Writes only step88_veto_robustness.py (this file),
step88_results.md, step88_table.csv. No git commands. No live-file edits.
No orders. Sealed test never touched.
"""

from __future__ import annotations

import os
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import strategy as STRAT
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding
from step43_daytrade import day_trade_signal, hours_to_bars, split_points

# Everything below is IMPORTED from step83_eye_filter.py -- never retyped.
# This is the exact eye cache, backtest wiring, control math, and live B
# constants R83 already built and validated.
from step83_eye_filter import (
    N_CONTROL_DRAWS,
    STOP_ATR_MULT,
    STOP_CAP_PCT,
    STOP_FLOOR_PCT,
    TARGET_STOP_MULT,
    WASHOUT_MAX_HOLD_H,
    WASHOUT_RSI_N,
    WASHOUT_RSI_TH,
    build_B,
    daily_trend_on_tf,
    dumb_control,
    eye_for,
    frame_for,
    funding_hist_for,
    run_split,
    summarize,
    trades_from_backtest,
    ts_idx_for,
)

T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:8.1f}s]", *a, flush=True)


RNG_SEED = 88

# Assets with adequate cached Bybit 1h/1d/funding history as of this run
# (BTC/ETH always available; SOL/XRP/DOGE fetched+cached for this round --
# see the round's own note in step88_results.md for what was pulled).
THIRD_ASSET_CANDIDATES = ["SOL", "XRP", "DOGE"]


def asset_available(asset: str) -> bool:
    sym = f"{asset}USDT"
    need = [
        f"data_bybit_{sym}_1h_full.parquet",
        f"data_bybit_{sym}_1d_full.parquet",
        f"data_bybit_{sym}_funding.parquet",
    ]
    return all(os.path.exists(f) for f in need)


# ===========================================================================
# 1. GENERALIZED WASHOUT BUILDER -- build_B() from step83_eye_filter.py,
#    parameterized over RSI period / threshold / turn-candle guard instead
#    of hardcoding WASHOUT_RSI_N=3 / WASHOUT_RSI_TH=10 / guard-always-on.
#    Every other piece (1d trend gate, ATR-scaled stop/target frozen off
#    the TRAIN slice, max-hold, backtest engine call) is IDENTICAL to
#    build_B, reusing the same imported helpers. Verified against build_B
#    bit-for-bit at the default parameters in main() before anything else
#    runs.
# ===========================================================================

def build_washout(asset: str, rsi_n: int = WASHOUT_RSI_N, rsi_th: int = WASHOUT_RSI_TH,
                  use_guard: bool = True, tf: str = "1h") -> pd.DataFrame:
    d = frame_for(asset, tf)
    c1d = fetch_bybit_deep("1d", f"{asset}USDT")
    funding = align_funding(d, funding_hist_for(asset))

    r = STRAT.rsi(d["close"], rsi_n)
    trend1d = daily_trend_on_tf(c1d, d)

    if use_guard:
        turn_up = (d["close"] > d["open"]) & (d["close"] > d["close"].shift(1))
        turn_down = (d["close"] < d["open"]) & (d["close"] < d["close"].shift(1))
    else:
        turn_up = pd.Series(True, index=d.index)
        turn_down = pd.Series(True, index=d.index)

    el = (r < rsi_th) & (trend1d == "up") & turn_up
    es = (r > (100 - rsi_th)) & (trend1d == "down") & turn_down
    el = el.fillna(False)
    es = es.fillna(False)

    n, i_tr, i_va = split_points(d)
    atr_pct = STRAT.atr(d, 14) / d["close"] * 100
    med_atr_train = float(atr_pct.iloc[:i_tr].median())
    stop_pct = min(STOP_ATR_MULT * med_atr_train, STOP_CAP_PCT)
    stop_pct = max(stop_pct, STOP_FLOOR_PCT)
    target_pct = TARGET_STOP_MULT * stop_pct
    mh_bars = hours_to_bars(d, WASHOUT_MAX_HOLD_H)

    sig = day_trade_signal(d, el, es, mh_bars)
    tr, va = run_split(d, sig, funding, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
    return trades_from_backtest(tr, va)


def verify_build_washout_matches_build_B():
    """build_washout(asset, WASHOUT_RSI_N, WASHOUT_RSI_TH, True) must
    reproduce build_B(asset) bit-for-bit -- this is the one honesty check
    that the generalization didn't silently drift from the live spec."""
    for asset in ("BTC", "ETH"):
        a = build_B(asset)
        b = build_washout(asset, WASHOUT_RSI_N, WASHOUT_RSI_TH, True)
        ok = (len(a) == len(b) and np.allclose(a["pnl"].to_numpy(), b["pnl"].to_numpy())
              and (a["entry_time"].to_numpy() == b["entry_time"].to_numpy()).all())
        log(f"verify build_washout == build_B on {asset}: "
           f"{'MATCH' if ok else 'MISMATCH'} (n={len(a)} vs {len(b)})")
        assert ok, f"build_washout does not reproduce build_B on {asset} -- generalization drifted"


# ===========================================================================
# 2. EYE ATTACHMENT + VETO_MESSY SCORING -- same lookup step83_eye_filter.
#    analyze_strategy_asset() performs (trade entry_time -> eye frame row
#    index -> quality at that bar), and the same control-percentile
#    definition R83 reported as "control pctile": the fraction of 200
#    random same-size-skip draws whose removed PnL is LESS negative (worse
#    at finding losers) than the eye's actual removed PnL. >=90% = clearly
#    better than chance at finding losers; <=10% = actively worse than
#    chance (anti-signal); in between = no information content.
# ===========================================================================

def attach_eye(trades: pd.DataFrame, eye_df: pd.DataFrame, ts_idx: dict) -> pd.DataFrame:
    if trades.empty:
        return trades
    idx = trades["entry_time"].map(ts_idx)
    ok = idx.notna()
    if not ok.all():
        log(f"    {(~ok).sum()} trade(s) entry_time not found in eye frame -- dropped")
    trades = trades[ok].copy()
    idx = idx[ok].astype(int)
    eye_rows = eye_df.iloc[idx.to_numpy()].reset_index(drop=True)
    trades = trades.reset_index(drop=True)
    trades["quality"] = eye_rows["quality"].to_numpy()
    return trades


def veto_messy_stats(trades: pd.DataFrame, rng: np.random.Generator,
                     n_draws: int = N_CONTROL_DRAWS) -> dict | None:
    if trades.empty or "quality" not in trades.columns:
        return None
    all_pnl = trades["pnl"].to_numpy()
    keep_mask = (trades["quality"] != "messy").to_numpy()
    kept_pnl = all_pnl[keep_mask]
    skipped_pnl = all_pnl[~keep_mask]
    before = summarize(all_pnl)
    after = summarize(kept_pnl)
    n_skip = len(skipped_pnl)
    skipped_total = float(skipped_pnl.sum()) if n_skip else 0.0

    ctl = dumb_control(all_pnl, n_skip, rng, n_draws=n_draws)
    if ctl is None:
        pctile = None
    else:
        removed = np.array(ctl["removed_pnl_dist"])
        pctile = float(np.mean(removed > skipped_total)) * 100

    return dict(
        n_total=before["n"], before_exp=before["expectancy"],
        n_kept=after["n"], after_exp=after["expectancy"],
        n_skipped=n_skip, skipped_total_pnl=skipped_total, control_pctile=pctile,
    )


# ===========================================================================
# 3. ATTACK 1 -- THIRD+ ASSET REPLAY
# ===========================================================================

def attack1_third_asset(rng: np.random.Generator) -> list[dict]:
    log("ATTACK 1: third+ asset replay (exact live spec: RSI3<10, 1h, turn guard)")
    assets = [a for a in THIRD_ASSET_CANDIDATES if asset_available(a)]
    log(f"  assets with cached history: {assets}")
    rows = []
    for asset in assets:
        log(f"  building washout on {asset} ...")
        try:
            trades = build_washout(asset, WASHOUT_RSI_N, WASHOUT_RSI_TH, True)
        except Exception as e:
            log(f"  ERROR building washout {asset}: {e!r}")
            continue
        eye_df = eye_for(asset, "1h")
        ts_idx = ts_idx_for(asset, "1h")
        trades = attach_eye(trades, eye_df, ts_idx)
        stats = veto_messy_stats(trades, rng)
        if stats is None:
            log(f"  {asset}: no trades / no eye match")
            continue
        stats["asset"] = asset
        rows.append(stats)
        be = stats["before_exp"]
        ae = stats["after_exp"]
        pc = stats["control_pctile"]
        log(f"  {asset}: before ${be:.2f}/t (n={stats['n_total']}) -> "
           f"after ${ae:.2f}/t (n={stats['n_kept']}), skip PnL "
           f"${stats['skipped_total_pnl']:.0f}, control pctile "
           f"{pc:.1f}%" if pc is not None else f"  {asset}: control undefined")
    return rows


# ===========================================================================
# 4. ATTACK 2 -- FAMILY SWEEP (RSI period x threshold x guard)
# ===========================================================================

RSI_PERIODS = [2, 3, 5]
RSI_THRESHOLDS = [5, 10, 15, 20]
GUARDS = [True, False]
MIN_TRADES_FOR_CONTROL = 8   # below this, control percentile is too noisy to trust


def attack2_family_sweep(rng: np.random.Generator, assets: tuple[str, ...]) -> list[dict]:
    log(f"ATTACK 2: family sweep, RSI period {RSI_PERIODS} x threshold {RSI_THRESHOLDS} "
       f"x guard {GUARDS}, assets={assets}")
    rows = []
    n_configs = len(RSI_PERIODS) * len(RSI_THRESHOLDS) * len(GUARDS) * len(assets)
    i = 0
    for asset in assets:
        eye_df = eye_for(asset, "1h")
        ts_idx = ts_idx_for(asset, "1h")
        for n in RSI_PERIODS:
            for th in RSI_THRESHOLDS:
                for guard in GUARDS:
                    i += 1
                    try:
                        trades = build_washout(asset, n, th, guard)
                    except Exception as e:
                        log(f"  [{i}/{n_configs}] ERROR {asset} RSI{n}<{th} "
                           f"guard={guard}: {e!r}")
                        continue
                    trades = attach_eye(trades, eye_df, ts_idx)
                    stats = veto_messy_stats(trades, rng)
                    row = dict(asset=asset, rsi_n=n, rsi_th=th, guard=guard)
                    if stats is None:
                        row.update(n_total=0, note="no trades")
                    elif stats["n_total"] < MIN_TRADES_FOR_CONTROL:
                        row.update(**stats, note=f"thin sample (<{MIN_TRADES_FOR_CONTROL})")
                    else:
                        row.update(**stats, note="")
                    rows.append(row)
                    if i % 12 == 0 or i == n_configs:
                        log(f"  [{i}/{n_configs}] {asset} RSI{n}<{th} guard={guard}: "
                           f"n={row.get('n_total', 0)}, pctile="
                           f"{row.get('control_pctile')}")
    return rows


# ===========================================================================
# 5. ATTACK 3 -- TIME-SPLIT (the exact R83 BTC/ETH trade lists, chrono
#    halved)
# ===========================================================================

def attack3_time_split(rng: np.random.Generator) -> list[dict]:
    log("ATTACK 3: time-split of the exact R83 BTC/ETH washout trade lists")
    rows = []
    for asset in ("BTC", "ETH"):
        trades = build_washout(asset, WASHOUT_RSI_N, WASHOUT_RSI_TH, True)
        eye_df = eye_for(asset, "1h")
        ts_idx = ts_idx_for(asset, "1h")
        trades = attach_eye(trades, eye_df, ts_idx)
        trades = trades.sort_values("entry_time").reset_index(drop=True)
        n = len(trades)
        mid = n // 2
        halves = [("first_half", trades.iloc[:mid].reset_index(drop=True)),
                 ("second_half", trades.iloc[mid:].reset_index(drop=True))]
        for half_label, half in halves:
            stats = veto_messy_stats(half, rng)
            row = dict(asset=asset, half=half_label)
            if half.empty:
                row.update(n_total=0, note="empty half")
            else:
                lo, hi = half["entry_time"].min(), half["entry_time"].max()
                row["date_range"] = f"{lo:%Y-%m-%d} to {hi:%Y-%m-%d}"
                if stats is None:
                    row.update(n_total=0, note="no eye match")
                else:
                    row.update(**stats, note="")
            rows.append(row)
            log(f"  {asset} {half_label} ({row.get('date_range', '?')}): "
               f"n={row.get('n_total', 0)}, before=${row.get('before_exp')}, "
               f"after=${row.get('after_exp')}, pctile={row.get('control_pctile')}")
    return rows


# ===========================================================================
# 6. MAIN
# ===========================================================================

def main():
    log("ROUND 88 -- is the veto we shipped tonight real, or two lucky cells?")
    verify_build_washout_matches_build_B()

    rng = np.random.default_rng(RNG_SEED)

    a1 = attack1_third_asset(rng)
    for r in a1:
        r["attack"] = "1_third_asset"

    sweep_assets = tuple(["BTC", "ETH"] + [a for a in THIRD_ASSET_CANDIDATES if asset_available(a)])
    a2 = attack2_family_sweep(rng, sweep_assets)
    for r in a2:
        r["attack"] = "2_family_sweep"

    a3 = attack3_time_split(rng)
    for r in a3:
        r["attack"] = "3_time_split"

    all_rows = a1 + a2 + a3
    table = pd.DataFrame(all_rows)
    cols = ["attack", "asset", "rsi_n", "rsi_th", "guard", "half", "date_range",
           "n_total", "before_exp", "n_kept", "after_exp", "n_skipped",
           "skipped_total_pnl", "control_pctile", "note"]
    cols = [c for c in cols if c in table.columns] + [c for c in table.columns if c not in cols]
    table = table[cols]
    table.to_csv("step88_table.csv", index=False)
    log(f"wrote step88_table.csv: {len(table)} rows")

    # multiple-comparisons baseline
    n_a2_scored = sum(1 for r in a2 if r.get("control_pctile") is not None)
    exp_90_a2 = n_a2_scored * 0.10
    exp_98_a2 = n_a2_scored * 0.02
    n_hit_90_a2 = sum(1 for r in a2 if (r.get("control_pctile") or -1) >= 90)
    n_hit_98_a2 = sum(1 for r in a2 if (r.get("control_pctile") or -1) >= 98)
    n_harm_10_a2 = sum(1 for r in a2 if r.get("control_pctile") is not None and r["control_pctile"] <= 10)

    log("DONE")
    log(f"attack2 scored cells: {n_a2_scored}, expected>=90th by chance: {exp_90_a2:.1f}, "
       f"observed: {n_hit_90_a2}; expected>=98th: {exp_98_a2:.1f}, observed: {n_hit_98_a2}; "
       f"actively-harmful(<=10th): {n_harm_10_a2}")
    log(f"total runtime: {round(time.time() - T0, 1)}s")


if __name__ == "__main__":
    main()
