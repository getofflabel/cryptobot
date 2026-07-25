"""
step191_spx_dipbuy_sol.py — cross-market transfer: the S&P system's RSI2<5
dip-buy (price>SMA200, exit close>SMA5 or RSI2>65, NO fixed target, stop=
none — step60_spx_system.py's exact sealed-passed winner, `1a-rsi2<5
stop=none hold=nocap`: SPY +$75.36/t x33 +24.9% DD-8.8%, ES=F +$124.07/t
x29 +36.0% DD-4.6%, 12/12 config-variant SURVIVOR, the fifth validated edge)
ported to SOL, per morgan's expanded mandate (2026-07-25 night) to test
every named family group, not just BTC's own.

STAGE 1 — UNCHANGED REPLAY: identical shape/thresholds (RSI(2)<5, daily
close>SMA200, exit on close>SMA5 or RSI2>65, no stop, no target, no hold
cap), on SOL's own 1d bars, SOL's REAL BloFin perp costs (taker, 18bps
round trip) — NOT SPX's near-zero ETF/futures cost assumption.

STAGE 2 — SOL-NATIVE RE-DERIVATION: SPX's median daily ATR% (~1.3-1.4%,
MARKET_PLAYBOOKS S&P section) is cited and NOT reused; SOL's own is
measured fresh. The no-stop version carries obvious tail risk on an asset
whose daily ATR runs ~6x SPX's and which fell ~97% peak-to-trough in 2022
— tested here as an explicit ATR-stop sweep (1.0x/1.5x/2.5x SOL's own
TRAIN-median ATR%, the first two matching the SPX family's own tested
grid, the third widened for SOL's fatter tail) rather than assumed either
way.

Execution: taker, always. Chance baseline: 100-draw random-entry null
(same event-triggered state machine, same exit condition, same random
entry count, same costs) — same discipline as step190a/step190_common.

Research only. Writes step191_spx_dipbuy_sol.py (this file),
step191_results.md, step191_table.csv, appends to step190_family_map.md.
No git commands, no live orders, no live-file edits. Sealed test slice
never sliced/computed/read.
"""

from __future__ import annotations

import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step48_tradfi_trend import event_long
from step60_spx_system import down_streak, dipbuy_exit, sma  # noqa: F401 (down_streak avail for later)
from step190_common import (
    ROUND_TRIP_COST_BPS, adverse_excursion_stats, append_family_line,
    avg_notional, chance_percentile, combined_expectancy,
)
import strategy as STRAT

T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:8.1f}s]", *a, flush=True)


ASSET = "SOL"
SYM = f"{ASSET}USDT"
MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8
RNG_SEED = 191
N_DRAWS = 100
SPX_ORIGINAL_ATR_PCT = (1.3, 1.4)   # daily, SPY/ES=F, MARKET_PLAYBOOKS S&P section


def split_points(d):
    n = len(d)
    return n, int(n * 0.6), int(n * 0.8)


def score(d, sig, i_tr, i_va, stop_pct=None):
    def run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True), sig.iloc[lo:hi].reset_index(drop=True),
            execution="taker", stop_pct=stop_pct, target_pct=None,
        )
    return run(0, i_tr), run(i_tr, i_va)


def verdict_for(tr, va):
    tr_n, va_n = len(tr.trades), len(va.trades)
    if tr.expectancy > 0 and va.expectancy > 0:
        if tr_n >= MIN_TRAIN_TRADES and va_n >= MIN_VAL_TRADES:
            return "SURVIVOR"
        return "INSUFFICIENT SAMPLE"
    return "FAIL"


def buy_hold_return_pct(d, lo, hi):
    seg = d.iloc[lo:hi]
    if len(seg) < 2:
        return float("nan")
    return float((seg["close"].iloc[-1] / seg["close"].iloc[0] - 1) * 100)


def random_entry_baseline_event(d, exit_cond, i_tr, i_va, n_events, stop_pct, rng, n_draws=N_DRAWS):
    n = len(d)
    eligible = np.arange(200, n - 5)   # SMA200 warmup floor
    draws = []
    for _ in range(n_draws):
        if len(eligible) < n_events:
            draws.append(float("nan"))
            continue
        picks = rng.choice(eligible, size=n_events, replace=False)
        enter = pd.Series(False, index=d.index)
        enter.iloc[picks] = True
        sig = event_long(d, enter, exit_cond, 0)
        tr, va = score(d, sig, i_tr, i_va, stop_pct=stop_pct)
        exp, _ = combined_expectancy(tr, va)
        draws.append(exp)
    return np.array(draws, dtype=float)


def row(cfg, stop_pct, d, tr, va, i_tr, i_va, pctile=None):
    exp, n_t = combined_expectancy(tr, va)
    notional = avg_notional(tr, va)
    ae = adverse_excursion_stats(tr, va)
    edge_pct = mult = float("nan")
    if notional and notional > 0 and not np.isnan(exp):
        edge_pct = exp / notional * 100
        mult = (edge_pct * 100) / ROUND_TRIP_COST_BPS
    yrs_tr = (d["timestamp"].iloc[i_tr - 1] - d["timestamp"].iloc[0]).days / 365.25
    yrs_va = (d["timestamp"].iloc[i_va - 1] - d["timestamp"].iloc[i_tr]).days / 365.25
    trades_per_yr = (len(tr.trades) + len(va.trades)) / (yrs_tr + yrs_va) if (yrs_tr + yrs_va) > 0 else float("nan")
    return dict(
        config=cfg, stop_pct=stop_pct,
        tr_n=len(tr.trades), tr_exp=tr.expectancy, tr_ret=tr.total_return_pct, tr_dd=tr.max_drawdown_pct,
        tr_bh=buy_hold_return_pct(d, 0, i_tr),
        va_n=len(va.trades), va_exp=va.expectancy, va_ret=va.total_return_pct, va_dd=va.max_drawdown_pct,
        va_bh=buy_hold_return_pct(d, i_tr, i_va),
        combined_n=n_t, combined_exp=exp, trades_per_yr=trades_per_yr,
        avg_notional=notional, edge_pct_notional=edge_pct, thickness_x_cost=mult,
        worst_adverse_pct=ae["worst_pct"], p5_adverse_pct=ae["p5_pct"], median_move_pct=ae["median_pct"],
        chance_pctile=pctile, verdict=verdict_for(tr, va),
    )


def main():
    log("STEP 191 — SPX's RSI2<5 dip-buy shape ported to SOL")
    d = fetch_bybit_deep("1d", SYM)
    n, i_tr, i_va = split_points(d)
    atr_pct = STRAT.atr(d, 14) / d["close"] * 100
    med_atr_train = float(atr_pct.iloc[:i_tr].median())
    log(f"SOL 1d: {n} bars {d['timestamp'].iloc[0]:%Y-%m-%d}->{d['timestamp'].iloc[-1]:%Y-%m-%d} "
       f"| train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed) "
       f"| SOL median train ATR%={med_atr_train:.3f}% vs SPX's cited {SPX_ORIGINAL_ATR_PCT}")
    log(f"SOL taker round-trip cost = {ROUND_TRIP_COST_BPS:.1f}bps (SOL's own real BloFin perp costs, "
       f"NOT SPX's near-zero ETF/futures rate)")

    close = d["close"]
    sma200 = sma(close, 200)
    r2 = STRAT.rsi(close, 2)
    exit_cond = dipbuy_exit(d).fillna(False)
    enter = ((r2 < 5) & (close > sma200)).fillna(False)
    n_events = int(enter.iloc[:i_va].sum())
    log(f"RSI2<5 & close>SMA200 fires on {n_events} of {i_va} bars in train+val")

    rows = []
    log("\nSTAGE 1 -- unchanged replay: rsi2<5, SMA200 filter, exit SMA5/RSI2>65, no stop")
    sig = event_long(d, enter, exit_cond, 0)
    tr, va = score(d, sig, i_tr, i_va, stop_pct=None)
    n_long = len(tr.trades) + len(va.trades)
    rng = np.random.default_rng(RNG_SEED)
    draws = random_entry_baseline_event(d, exit_cond, i_tr, i_va, n_long, None, rng, N_DRAWS)
    exp, _ = combined_expectancy(tr, va)
    pctile = chance_percentile(exp, draws)
    r1 = row("rsi2<5 SMA200 stop=none (unchanged SPX config)", None, d, tr, va, i_tr, i_va, pctile)
    r1["stage"] = "1_unchanged_replay"
    rows.append(r1)
    log(f"  train n={len(tr.trades)} exp=${tr.expectancy:.2f} ret={tr.total_return_pct:.1f}% "
       f"(buy&hold {r1['tr_bh']:.1f}%) DD={tr.max_drawdown_pct:.1f}% | val n={len(va.trades)} "
       f"exp=${va.expectancy:.2f} ret={va.total_return_pct:.1f}% (buy&hold {r1['va_bh']:.1f}%) "
       f"DD={va.max_drawdown_pct:.1f}% | chance pctile {pctile:.1f} | "
       f"thickness {r1['thickness_x_cost']:.1f}x | worst move {r1['worst_adverse_pct']:.2f}% | "
       f"verdict {r1['verdict']}")

    log("\nSTAGE 2 -- SOL-native re-derivation: ATR-stop sweep (1.0x/1.5x/2.5x SOL's own train-median ATR)")
    for mult in (1.0, 1.5, 2.5):
        stop_pct = mult * med_atr_train
        tr2, va2 = score(d, sig, i_tr, i_va, stop_pct=stop_pct)
        exp2, _ = combined_expectancy(tr2, va2)
        draws2 = random_entry_baseline_event(d, exit_cond, i_tr, i_va, n_long, stop_pct, rng, N_DRAWS)
        pctile2 = chance_percentile(exp2, draws2)
        r = row(f"rsi2<5 SMA200 stop={mult:.1f}xATR({stop_pct:.2f}%)", stop_pct, d, tr2, va2, i_tr, i_va, pctile2)
        r["stage"] = "2_native_stop_sweep"
        rows.append(r)
        log(f"  stop={mult:.1f}xATR={stop_pct:.2f}%: train n={len(tr2.trades)} exp=${tr2.expectancy:.2f} "
           f"| val n={len(va2.trades)} exp=${va2.expectancy:.2f} | combined ${exp2:.2f}/t | "
           f"chance pctile {pctile2:.1f} | thickness {r['thickness_x_cost']:.1f}x | "
           f"worst move {r['worst_adverse_pct']:.2f}% | verdict {r['verdict']}")

    table = pd.DataFrame(rows)
    table.to_csv("step191_table.csv", index=False)
    log(f"\nwrote step191_table.csv ({len(table)} rows)")

    for r in rows:
        pct = r.get("chance_pctile")
        pct_str = f"{pct:.0f}th pctile" if pct is not None and pct == pct else "n/a"
        append_family_line(
            f"- **spx_rsi2dipbuy_port({r['stage']})** [1d, {r['config']}] — {r['verdict']} | "
            f"combined {r['combined_n']}t ${r['combined_exp']:.2f}/t (train {r['tr_n']}t "
            f"${r['tr_exp']:.2f}, val {r['va_n']}t ${r['va_exp']:.2f}) | chance {pct_str} | "
            f"thickness {r['thickness_x_cost']:.1f}x | worst move {r['worst_adverse_pct']:.2f}% "
            f"| buy&hold train {r['tr_bh']:.1f}% / val {r['va_bh']:.1f}% | source: SPX's original "
            f"rsi2<5 stop=none sealed-PASS SPY+$75.36/t ES+$124.07/t, 12/12 SURVIVOR"
        )
    log(f"appended {len(rows)} lines to step190_family_map.md")
    log(f"total runtime: {round(time.time() - T0, 1)}s")


if __name__ == "__main__":
    main()
