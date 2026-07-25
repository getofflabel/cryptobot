"""
step172_dead_family_retests.py — ETH-trader, round 172: cheap confirmation
retests of families BTC proved DEAD (order blocks 0/64, pin bars/
engulfing/inside-bars 0/112, ALL always-on shorts 5x confirmed —
MARKET_PLAYBOOKS.md's BTC section). Per Morgan: "'dead on BTC' isn't
'dead everywhere' — ETH's higher volatility profile is exactly where a
differently-shaped edge might live."

Run:  python3 step172_dead_family_retests.py

SCOPE, STATED PLAINLY: this is a LIGHTER-WEIGHT confirmation than BTC's
own step57_price_action.py grid (296 configs across context/gate
variants) — a cheap first bar, not the full grid. If any shape here shows
signs of life, it earns a full BTC-style grid as a proper follow-up round;
if it's dead here too (as expected, going in), a light touch is
appropriate and honest, not a shortcut that hides anything.

Families tested: (A) always-on shorts, (B) pin bar reversal, (C)
engulfing reversal. Order blocks are DEFERRED this round (step57's
order_block_engine is a stateful multi-parameter tracker not worth a
half-reimplementation) — noted honestly as not-yet-attempted, not folded
into a false verdict.

COSTS: execution="taker" throughout. Structure stops via confirmed_swings
(k5, train-median distance + buffer) for B/C; A (always-on shorts) uses
ATR-multiple stops since there is no entry-adjacent swing to reference
for an unconditional always-in-market signal (stated as the one place
this round uses ATR instead of a swing distance, consistent with exits.py
offering stop_atr as a legitimate structure-adjacent method, not a swept
percentage of price).
"""

import numpy as np
import pandas as pd

import step170_eth_lib as lib
from step170_eth_lib import (
    MIN_TRAIN_TRADES, MIN_VAL_TRADES, TAKER_RT_BPS, champ_aligned,
    day_trade_signal, hours_to_bars, load_frames, mk_row, score,
    score_sealed, split_points, swing_stop_pct, thickness, verdict_for,
)
from step41_shorts import confirmed_swings, last_n_confirmed
from strategy import atr, vol_gated_ma

pd.set_option("display.width", 220)
ALL_ROWS = []


def log_row(row):
    ALL_ROWS.append(row)


CHAMP_KW = dict(fast=20, slow=100, min_atr_pct=1.5)


# ===========================================================================
# FAMILY A — always-on shorts
# ===========================================================================

def family_a_always_short(frames, funding, meta):
    print("\n" + "=" * 78)
    print("FAMILY A — always-on shorts (BTC: 5x confirmed dead)")
    print("=" * 78)
    for tf in ("1h", "4h"):
        d, f = frames[tf], funding[tf]
        n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]
        a_pct = atr(d, 14) / d["close"] * 100
        med_atr_train = float(a_pct.iloc[:i_tr].median())
        sig = pd.Series(-1.0, index=d.index)
        for stop_mult in (1.5, 2.5):
            stop_pct = min(stop_mult * med_atr_train, 6.0)
            tr, va = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct)
            v = verdict_for(tr, va)
            print(f"  {tf} stop={stop_mult}xATR({stop_pct:.2f}%): train n={len(tr.trades)} "
                  f"exp=${tr.expectancy:+.2f} ret={tr.total_return_pct:+.2f}% | "
                  f"val n={len(va.trades)} exp=${va.expectancy:+.2f} ret={va.total_return_pct:+.2f}% -> {v}")
            log_row(mk_row("A-always-short", f"unconditional short stop{stop_mult}xATR({stop_pct:.2f}%)",
                            tf, tr, va, stop_pct, None, None,
                            extra={"edge": "A-always-short", "transfer_type": "native-eth-retest",
                                   "btc_number": "5x confirmed dead"}))


# ===========================================================================
# FAMILY B — pin bar reversal (simple wick-ratio definition)
# ===========================================================================

def pin_bar_signals(d, wick_mult):
    body = (d["close"] - d["open"]).abs()
    upper_wick = d["high"] - d[["open", "close"]].max(axis=1)
    lower_wick = d[["open", "close"]].min(axis=1) - d["low"]
    bull_pin = (lower_wick >= wick_mult * body.clip(lower=1e-9)) & (d["close"] > d["open"])
    bear_pin = (upper_wick >= wick_mult * body.clip(lower=1e-9)) & (d["close"] < d["open"])
    return bull_pin.fillna(False), bear_pin.fillna(False)


def family_b_pin_bars(frames, funding, meta):
    print("\n" + "=" * 78)
    print("FAMILY B — pin bar reversal (BTC: 0/112 combined with engulfing/inside-bars)")
    print("=" * 78)
    tf = "1h"
    d, f = frames[tf], funding[tf]
    n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]
    sh_price, sl_price = confirmed_swings(d, 5)
    (sl1,) = last_n_confirmed(sl_price, 1)
    (sh1,) = last_n_confirmed(sh_price, 1)
    for wick_mult in (2.0, 3.0):
        el, es = pin_bar_signals(d, wick_mult)
        n_events = int((el | es).iloc[:i_va].sum())
        if n_events == 0:
            print(f"  wick_mult={wick_mult}: no qualifying events")
            continue
        dist = pd.Series(np.nan, index=d.index)
        dist = dist.mask(el, (d["close"] - sl1) / d["close"] * 100)
        dist = dist.mask(es, (sh1 - d["close"]) / d["close"] * 100)
        stop_pct = swing_stop_pct(d["close"], sl1.where(el, sh1), el | es, i_tr, 0.2, cap=4.0)
        for hold_h in (24, 48):
            mh_bars = hours_to_bars(d, hold_h)
            sig = day_trade_signal(d, el, es, mh_bars)
            for tmult in (2.0, 3.0):
                target_pct = stop_pct * tmult
                tr, va = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
                v = verdict_for(tr, va)
                print(f"  wick{wick_mult} hold{hold_h}h tgt{tmult}x stop{stop_pct:.2f}%: "
                      f"train n={len(tr.trades)} exp=${tr.expectancy:+.2f} | "
                      f"val n={len(va.trades)} exp=${va.expectancy:+.2f} -> {v}")
                log_row(mk_row("B-pin-bar", f"wick{wick_mult}x hold{hold_h}h tgt{tmult}x", tf,
                                tr, va, stop_pct, target_pct, hold_h,
                                extra={"edge": "B-pin-bar", "transfer_type": "native-eth-retest",
                                       "btc_number": "0/112 (combined pin/engulf/inside)"}))


# ===========================================================================
# FAMILY C — engulfing reversal
# ===========================================================================

def engulfing_signals(d):
    o, c = d["open"], d["close"]
    po, pc = o.shift(1), c.shift(1)
    bull = (c > o) & (pc < po) & (c >= po) & (o <= pc)
    bear = (c < o) & (pc > po) & (c <= po) & (o >= pc)
    return bull.fillna(False), bear.fillna(False)


def family_c_engulfing(frames, funding, meta):
    print("\n" + "=" * 78)
    print("FAMILY C — engulfing reversal (BTC: 0/112 combined)")
    print("=" * 78)
    tf = "1h"
    d, f = frames[tf], funding[tf]
    n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]
    el, es = engulfing_signals(d)
    n_events = int((el | es).iloc[:i_va].sum())
    print(f"  qualifying events (train+val): {n_events}")
    sh_price, sl_price = confirmed_swings(d, 5)
    (sl1,) = last_n_confirmed(sl_price, 1)
    (sh1,) = last_n_confirmed(sh_price, 1)
    stop_pct = swing_stop_pct(d["close"], sl1.where(el, sh1), el | es, i_tr, 0.2, cap=4.0)
    for hold_h in (24, 48):
        mh_bars = hours_to_bars(d, hold_h)
        sig = day_trade_signal(d, el, es, mh_bars)
        for tmult in (2.0, 3.0):
            target_pct = stop_pct * tmult
            tr, va = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
            v = verdict_for(tr, va)
            print(f"  hold{hold_h}h tgt{tmult}x stop{stop_pct:.2f}%: train n={len(tr.trades)} "
                  f"exp=${tr.expectancy:+.2f} | val n={len(va.trades)} exp=${va.expectancy:+.2f} -> {v}")
            log_row(mk_row("C-engulfing", f"hold{hold_h}h tgt{tmult}x", tf, tr, va,
                            stop_pct, target_pct, hold_h,
                            extra={"edge": "C-engulfing", "transfer_type": "native-eth-retest",
                                   "btc_number": "0/112 (combined pin/engulf/inside)"}))


def main():
    print("Loading ETH-USDT data...")
    frames, funding, funding_hist = load_frames(("1h", "4h"))
    meta = {}
    for tf in ("1h", "4h"):
        d = frames[tf]
        n, i_tr, i_va = split_points(d)
        meta[tf] = {"n": n, "i_tr": i_tr, "i_va": i_va}

    family_a_always_short(frames, funding, meta)
    family_b_pin_bars(frames, funding, meta)
    family_c_engulfing(frames, funding, meta)

    print("\nORDER BLOCKS: DEFERRED this round (step57's order_block_engine is a stateful, "
          "multi-parameter tracker — worth a dedicated follow-up, not a shortcut here). "
          "Not scored as DEAD or SURVIVOR; simply not yet attempted for ETH.")

    df = pd.DataFrame(ALL_ROWS)
    df.to_csv("step172_table.csv", index=False)
    print(f"\n\n{len(df)} rows written to step172_table.csv")
    survivors = df[df["verdict"] == "SURVIVOR"]
    print(f"SURVIVORS: {len(survivors)}")
    if len(survivors):
        print(survivors.to_string(index=False))
    print(df["verdict"].value_counts().to_string())
    return df


if __name__ == "__main__":
    main()
