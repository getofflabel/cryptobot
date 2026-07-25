"""
step193_candle_patterns_confirmation_sol.py — cheap dead-family
confirmation: pin bars / engulfing patterns are BTC-dead (0/112, and
"adding context made them WORSE": -8.9 bare -> -43.1 with SMA50 context,
per MARKET_PLAYBOOKS). Per morgan's expanded mandate, tested on SOL before
being filed dead here too — same discipline as step192.

SHAPE (unchanged, imported verbatim from step57_price_action.py):
pin_bar_signals(d, wick_mult, context_type, daily_sma_al) and
engulfing_signals(d, context_type, daily_sma_al) — wick_mult in {2,3},
context_type in {roll20, roll55, sma50, none} (the exact grid that showed
context made things WORSE on BTC), stop = stop_mult x TRAIN-median ATR%
(stop_mult in {1.0,1.5}, capped [0.30,3.0]%), target = target_mult x stop
(target_mult in {2.0,3.0}), hold 24h. 1h and 4h SOL (BTC's own testbed).

Execution: taker, always (source used maker — see step190_common docstring
for the stricter-bar rationale, same as every step190a edge). This is a
CONFIRMATION test at BTC's own scale (2 wick_mults x 4 contexts x 2 stops x
2 targets x 2tf = 64 pin-bar cells, 4 contexts x 2 stops x 2 targets x 2tf
= 32 engulfing cells -- 96 cells total, same order of magnitude as BTC's
own 112), not a fishing trip -- reported as a clean confirm/refute, no
chance baseline needed for an expected-negative family at this scale.

Research only. Writes step193_candle_patterns_confirmation_sol.py (this
file), step193_results.md, step193_table.csv, appends to
step190_family_map.md. No git commands, no live orders, no live-file
edits.
"""

from __future__ import annotations

import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step43_daytrade import CHAMP_KW, champ_aligned, day_trade_signal, hours_to_bars, split_points
from step57_price_action import (
    STOP_CAP_PCT, STOP_FLOOR_PCT, daily_sma_aligned, engulfing_signals, pin_bar_signals,
)
from step190_common import (
    ROUND_TRIP_COST_BPS, adverse_excursion_stats, append_family_line, avg_notional,
    combined_expectancy, score_taker,
)
import strategy as STRAT

T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:8.1f}s]", *a, flush=True)


SYM = "SOLUSDT"
MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8
TIMEFRAMES = ("1h", "4h")


def verdict_for(tr, va, thickness):
    tr_n, va_n = len(tr.trades), len(va.trades)
    if tr.expectancy > 0 and va.expectancy > 0:
        if tr_n >= MIN_TRAIN_TRADES and va_n >= MIN_VAL_TRADES:
            return "SURVIVOR" if (thickness == thickness and thickness >= 5.0) else "REJECT (thin, <5x cost)"
        return "INSUFFICIENT SAMPLE"
    return "FAIL"


def mk_row(family, cfg, tf, tr, va, stop_pct, target_pct):
    exp, n_t = combined_expectancy(tr, va)
    notional = avg_notional(tr, va)
    thick = (exp / notional * 100 * 100 / ROUND_TRIP_COST_BPS) if notional else float("nan")
    ae = adverse_excursion_stats(tr, va)
    return dict(family=family, config=cfg, tf=tf,
               tr_n=len(tr.trades), tr_exp=tr.expectancy,
               va_n=len(va.trades), va_exp=va.expectancy,
               combined_n=n_t, combined_exp=exp, stop_pct=stop_pct, target_pct=target_pct,
               thickness_x_cost=thick, worst_adverse_pct=ae["worst_pct"],
               verdict=verdict_for(tr, va, thick))


def main():
    log("STEP 193 — pin bar / engulfing candle patterns, dead-family confirmation on SOL")
    frames = {tf: fetch_bybit_deep(tf, SYM) for tf in TIMEFRAMES}
    daily = fetch_bybit_deep("1d", SYM)
    funding_hist = fetch_funding_history(SYM)
    funding = {tf: align_funding(frames[tf], funding_hist) for tf in TIMEFRAMES}

    meta = {}
    for tf in TIMEFRAMES:
        d = frames[tf]
        n, i_tr, i_va = split_points(d)
        atr_pct = STRAT.atr(d, 14) / d["close"] * 100
        med_atr_train = float(atr_pct.iloc[:i_tr].median())
        meta[tf] = {"i_tr": i_tr, "i_va": i_va, "med_atr": med_atr_train}
        log(f"  SOL {tf}: {n} bars, train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
           f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed), med train ATR%={med_atr_train:.3f}%")

    daily_sma50 = daily["close"].rolling(50).mean()
    daily_sma_al = {tf: daily_sma_aligned(daily, daily_sma50, frames[tf]) for tf in TIMEFRAMES}

    rows = []
    log("\nFAMILY 2a — pin bars (unchanged shape, all 4 context variants incl. the one that hurt BTC)...")
    for tf in TIMEFRAMES:
        d, f = frames[tf], funding[tf]
        i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
        med_atr = meta[tf]["med_atr"]
        mh_bars = hours_to_bars(d, 24)
        for wick_mult in (2, 3):
            for context_type in ("roll20", "roll55", "sma50", "none"):
                el, es = pin_bar_signals(d, wick_mult, context_type, daily_sma_al[tf])
                for stop_mult in (1.0, 1.5):
                    stop_pct = min(max(stop_mult * med_atr, STOP_FLOOR_PCT), STOP_CAP_PCT)
                    for target_mult in (2.0, 3.0):
                        target_pct = target_mult * stop_pct
                        sig = day_trade_signal(d, el, es, mh_bars)
                        tr, va = score_taker(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
                        cfg = f"wick{wick_mult}x ctx={context_type} stop{stop_mult:.1f}xATR tgt{target_mult:.0f}xstop"
                        rows.append(mk_row("2a-pin-bar", cfg, tf, tr, va, stop_pct, target_pct))
    log(f"  {sum(1 for r in rows if r['family']=='2a-pin-bar')} pin-bar cells done")

    log("FAMILY 2b — engulfing (unchanged shape)...")
    n_before = len(rows)
    for tf in TIMEFRAMES:
        d, f = frames[tf], funding[tf]
        i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
        med_atr = meta[tf]["med_atr"]
        mh_bars = hours_to_bars(d, 24)
        for context_type in ("roll20", "roll55", "sma50", "none"):
            el, es = engulfing_signals(d, context_type, daily_sma_al[tf])
            for stop_mult in (1.0, 1.5):
                stop_pct = min(max(stop_mult * med_atr, STOP_FLOOR_PCT), STOP_CAP_PCT)
                for target_mult in (2.0, 3.0):
                    target_pct = target_mult * stop_pct
                    sig = day_trade_signal(d, el, es, mh_bars)
                    tr, va = score_taker(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
                    cfg = f"engulf ctx={context_type} stop{stop_mult:.1f}xATR tgt{target_mult:.0f}xstop"
                    rows.append(mk_row("2b-engulfing", cfg, tf, tr, va, stop_pct, target_pct))
    log(f"  {len(rows) - n_before} engulfing cells done")

    table = pd.DataFrame(rows)
    table.to_csv("step193_table.csv", index=False)
    n_survivors = int((table["verdict"] == "SURVIVOR").sum())
    n_thin = int(table["verdict"].str.startswith("REJECT").sum())
    n_pos_both = int(((table["tr_exp"] > 0) & (table["va_exp"] > 0)).sum())
    log(f"\n{len(table)} configs total. SURVIVOR: {n_survivors}. Thin-rejected: {n_thin}. "
       f"Both-windows-positive: {n_pos_both}/{len(table)}.")
    for fam in ("2a-pin-bar", "2b-engulfing"):
        sub = table[table["family"] == fam]
        best = sub.loc[sub["combined_exp"].idxmax()]
        log(f"  {fam} best cell: {best['config']} [{best['tf']}] combined ${best['combined_exp']:.2f}/t "
           f"(train {best['tr_n']}t ${best['tr_exp']:.2f}, val {best['va_n']}t ${best['va_exp']:.2f}) "
           f"thickness {best['thickness_x_cost']:.1f}x verdict {best['verdict']}")

    if n_survivors == 0:
        verdict_line = f"CONFIRMED DEAD on SOL too (0/{len(table)} true survivors)"
    else:
        verdict_line = f"NOT confirmed dead — {n_survivors} true survivor(s), re-examine before filing dead"
    append_family_line(
        f"- **candle_patterns_confirmation(pin_bar+engulfing)** [1h+4h, {len(table)} cells, shape "
        f"unchanged from step57_price_action.py] — {verdict_line} | {n_pos_both}/{len(table)} "
        f"both-windows-positive by raw sign, {n_thin} thin-rejected (<5x cost) | worst combined "
        f"${table['combined_exp'].min():.2f}/t, best combined ${table['combined_exp'].max():.2f}/t "
        f"| source: BTC's pin-bar/engulfing family, 0/112 dead, context made it worse"
    )
    log("appended 1 line to step190_family_map.md")
    log(f"total runtime: {round(time.time() - T0, 1)}s")


if __name__ == "__main__":
    main()
