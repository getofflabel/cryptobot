"""
step314_diagnostics.py — ROUND 310 diagnostics.

Not new strategies. This decomposes the trade lists the four re-runs
already produced, to answer "what were those numbers actually made of":

  A. Edge 1 (structure flip): long trades versus short trades, separately.
     The desk has three independent studies saying shorting Bitcoin does
     not work here, and this edge is roughly half shorts. If the whole
     first-60% loss lives on the short side, the diagnosis "the retest
     doesn't help" is incomplete and should say so.
  B. Edge 2 (hidden divergence): why every cell's median hold sat EXACTLY
     on the 48-hour cap. Counts of how each trade actually ended.
  C. Edge 3 (RSI dip-buy): the same count, to see whether confirming the
     turn changed how trades end or only how many there are.

Everything reads the same engine, the same market-order cost model and the
same stops as the four re-runs. No selection happens here.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd

import exits as E
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import days_to_bars, split_points
from step43_daytrade import champ_aligned
from step56_smc_toolkit import bos_chain
from step58_divergence_mtf import hours_to_bars
from strategy import rsi, vol_gated_ma
from step150_common import mask_to_events, run_edge, trade_stats
from step150a_choch_confluence import CONF_HOLD_DAYS, K as K1, TARGET_MULT as T1, build_entries
from step150b_hidden_divergence import BUFFER_PCT, CHAMP_KW, K as K2, MAX_HOLD_H as MH2, TARGET_MULT as T2
from step150d_rsi3_dipbuy import K as K4, MAX_HOLD_H as MH4, RSI_THRESH, TARGET_MULT as T4
from step310_common import wait_for_close_through, wait_for_touch_then_close_back
from step311_hidden_div_confirm import hidden_events_with_confirm_level

OUT = []


def by_direction(label, trades, window):
    for d, name in ((1, "long"), (-1, "short")):
        sub = [t for t in trades if t["direction"] == d]
        st = trade_stats(sub)
        print(f"  {label} | {window} | {name}: n={st['n']} "
              f"profit per trade ${st['expectancy']:+,.2f} win%={st['win_rate']*100:.1f}")
        OUT.append(dict(section="A direction split", cell=label, window=window,
                        side=name, n=st["n"], exp=st["expectancy"],
                        win_rate=st["win_rate"]))


def how_trades_ended(label, trades, window):
    c = Counter()
    for t in trades:
        r = t["reason"]
        c["hit the stop" if r.startswith("stop") else
          "reached the target" if r.startswith("target") else
          "ran out of time"] += 1
    tot = max(1, len(trades))
    parts = ", ".join(f"{k} {v} ({v/tot*100:.0f}%)" for k, v in sorted(c.items()))
    print(f"  {label} | {window} | n={len(trades)}: {parts}")
    for k, v in c.items():
        OUT.append(dict(section="ending mix", cell=label, window=window,
                        side=k, n=v, exp=float("nan"), win_rate=v / tot))


def main():
    d1h_full = fetch_bybit_deep("1h", "BTCUSDT")
    d4h_full = fetch_bybit_deep("4h", "BTCUSDT")
    fh = fetch_funding_history("BTCUSDT")
    f1h_full = align_funding(d1h_full, fh)

    # ================= A. edge 1, long versus short =================
    print("\n" + "=" * 74)
    print("A. STRUCTURE FLIP — is the loss on the long side or the short side?")
    print("=" * 74)
    n, i_tr, i_va = split_points(d1h_full)
    d1h = d1h_full.iloc[:i_va].reset_index(drop=True)
    f1h = f1h_full.iloc[:i_va].reset_index(drop=True)
    d4h = d4h_full[d4h_full["timestamp"] <= d1h["timestamp"].iloc[-1]].reset_index(drop=True)
    el, es = build_entries(d1h, d4h)
    mh1 = days_to_bars(d1h, CONF_HOLD_DAYS)
    sb1 = lambda tc: E.stop_structure(k=K1, n_back=1, buffer_pct=0.0, use="wick")
    tb1 = lambda s: E.target_fixed_r(s, r_multiple=T1)

    bos = bos_chain(d1h, K1)
    hi, lo, cl = d1h["high"].to_numpy(), d1h["low"].to_numpy(), d1h["close"].to_numpy()
    tl, _ = wait_for_touch_then_close_back(el, bos["lsh"].to_numpy(), hi, lo, cl, "long", 10)
    ts, _ = wait_for_touch_then_close_back(es, bos["lsl"].to_numpy(), hi, lo, cl, "short", 10)
    tl.index, ts.index = d1h.index, d1h.index

    for cell, (ml, ms) in (("break bar", (el, es)), ("retest, 10-bar wait", (tl, ts))):
        dirn = pd.Series(np.where(ml, 1, np.where(ms, -1, 0)), index=d1h.index)
        ents = mask_to_events(ml | ms, dirn)
        for wname, a, b in (("first 60%", 0, i_tr), ("middle 20%", i_tr, i_va)):
            c = d1h.iloc[a:b].reset_index(drop=True)
            f = f1h.iloc[a:b].reset_index(drop=True)
            e = [(i - a, dd) for i, dd in ents if a <= i < b]
            tr, _ = run_edge(c, e, sb1, tb1, mh1, funding_bps=f, k=K1)
            by_direction(cell, tr, wname)

    # ================= B. edge 2, how trades ended =================
    print("\n" + "=" * 74)
    print("B. HIDDEN DIVERGENCE — how did the trades actually end?")
    print("=" * 74)
    f4h_full = align_funding(d4h_full, fh)
    n2, j_tr, j_va = split_points(d4h_full)
    d4 = d4h_full.iloc[:j_va].reset_index(drop=True)
    f4 = f4h_full.iloc[:j_va].reset_index(drop=True)
    champ = vol_gated_ma(d4, **CHAMP_KW)
    osc = rsi(d4["close"], 14)
    lh, sh, lvl_l, lvl_s = hidden_events_with_confirm_level(d4, osc, K2, champ)
    mh2 = hours_to_bars(d4, MH2)
    sb2 = lambda tc: E.stop_structure(k=K2, n_back=1, buffer_pct=BUFFER_PCT, use="wick")
    tb2 = lambda s: E.target_fixed_r(s, r_multiple=T2)
    c4 = d4["close"].to_numpy()
    ctl, _ = wait_for_close_through(lh, lvl_l, c4, "long", 24)
    cts, _ = wait_for_close_through(sh, lvl_s, c4, "short", 24)
    ctl.index, cts.index = d4.index, d4.index
    for cell, (ml, ms) in (("divergence bar", (lh, sh)),
                           ("confirming close, 24-bar wait", (ctl, cts))):
        dirn = pd.Series(np.where(ml, 1, np.where(ms, -1, 0)), index=d4.index)
        ents = mask_to_events(ml | ms, dirn)
        for wname, a, b in (("first 60%", 0, j_tr), ("middle 20%", j_tr, j_va)):
            c = d4.iloc[a:b].reset_index(drop=True)
            f = f4.iloc[a:b].reset_index(drop=True)
            e = [(i - a, dd) for i, dd in ents if a <= i < b]
            tr, _ = run_edge(c, e, sb2, tb2, mh2, funding_bps=f, k=K2)
            how_trades_ended(cell, tr, wname)

    # ================= C. edge 3, how trades ended =================
    print("\n" + "=" * 74)
    print("C. RSI DIP-BUY — how did the trades actually end?")
    print("=" * 74)
    champ4 = vol_gated_ma(d4h, **CHAMP_KW)
    d4c = d4h_full[d4h_full["timestamp"] <= d1h["timestamp"].iloc[-1]].reset_index(drop=True)
    champ4c = vol_gated_ma(d4c, **CHAMP_KW)
    champ_1h = champ_aligned(d4c, champ4c, d1h)
    r3 = rsi(d1h["close"], 3)
    sig = ((champ_1h == 1) & (r3 < RSI_THRESH)).fillna(False)
    trig, _ = wait_for_close_through(sig, hi, cl, "long", 6)
    trig.index = d1h.index
    sb4 = lambda tc: E.stop_structure(k=K4, n_back=1, buffer_pct=0.0, use="wick")
    tb4 = lambda s: E.target_fixed_r(s, r_multiple=T4)
    for cell, m in (("falling bar", sig), ("turn confirmed, 6-bar wait", trig)):
        ents = mask_to_events(m, 1)
        for wname, a, b in (("first 60%", 0, i_tr), ("middle 20%", i_tr, i_va)):
            c = d1h.iloc[a:b].reset_index(drop=True)
            f = f1h.iloc[a:b].reset_index(drop=True)
            e = [(i - a, dd) for i, dd in ents if a <= i < b]
            tr, _ = run_edge(c, e, sb4, tb4, MH4, funding_bps=f, k=K4)
            how_trades_ended(cell, tr, wname)

    pd.DataFrame(OUT).to_csv("step314_table.csv", index=False)
    print("\nwrote step314_table.csv")


if __name__ == "__main__":
    main()
