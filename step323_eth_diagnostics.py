"""
step323_eth_diagnostics.py — ROUND 320, PHASE 3.

Three things the pass/fail table cannot say on its own:

  1. THE PRE-REGISTERED PICK. Per family, the cell with the best average
     profit per trade on the FIRST 60% (and enough trades there) is the
     one the round is entitled to carry forward. This prints that pick and
     its one reading on the middle 20%, so nobody can later point at a
     different cell that happened to look better in the middle and call it
     the result.

  2. WHY the surviving cells look the way they do: how the trades ended,
     how far the chart stop sat from entry, what leverage the risk-sizing
     formula produced.

  3. ETHEREUM'S OWN PERSONALITY — a hypothesis with a measurement attached,
     not a conclusion. Round 173 already established that Ethereum does not
     lead or lag Bitcoin at hourly resolution and does not amplify Bitcoin's
     moves during Bitcoin's own panic windows. This asks a different
     question: does Ethereum's recent strength RELATIVE to Bitcoin change
     whether Ethereum's own trend entries pay? That conditioning variable
     cannot exist for Bitcoin, which has no "relative to itself".

Measured on the FIRST 60% only, except the one middle-20% reading already
spent in step322. The final untouched slice is not loaded anywhere here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import exits as E
from step11_round6 import align_funding, fetch_funding_history
from step321_eth_engine import run_edge_ctx, split_points, stats, thickness
from step322_eth_shape_tests import BTC_R150_BUFFER_PCT, BTC_TRAIN_4H_ATR_PCT, frame
from strategy import atr, vol_gated_ma

pd.set_option("display.width", 240)


def pre_registered_picks():
    print("=" * 96)
    print("1. THE PRE-REGISTERED PICK PER FAMILY")
    print("   Rule, fixed before the middle 20% was read: take the cell with the highest average")
    print("   profit per trade on the FIRST 60% that also has at least 30 trades there. That cell,")
    print("   and only that cell, is what the family is judged on.")
    print("=" * 96)
    df = pd.read_csv("step320_table.csv")
    out = []
    for fam, g in df.groupby("family"):
        ok = g[g["train_trades"] >= 30]
        if not len(ok):
            print(f"\n  {fam}: no cell reached 30 trades on the first 60%. NOT ENOUGH TRADES, "
                  f"nothing carried forward.")
            out.append(dict(family=fam, pick="none", outcome="NOT ENOUGH TRADES"))
            continue
        pick = ok.loc[ok["train_avg_profit_per_trade"].idxmax()]
        thick = pick["times_bigger_than_trading_cost_val"]
        if pick["train_avg_profit_per_trade"] <= 0:
            outcome = "DIES (the best cell on the first 60% still loses money there)"
        elif pick["val_avg_profit_per_trade"] <= 0:
            outcome = "DIES (profitable on the first 60%, loses on the middle 20%)"
        elif pick["val_trades"] < 8:
            outcome = "NOT ENOUGH TRADES on the middle 20%"
        elif thick < 5:
            outcome = (f"REJECTED ON THICKNESS: positive both windows but the profit is only "
                       f"{thick:.2f} times the cost of trading, under the 5x bar")
        else:
            outcome = "SURVIVES the first two windows and clears the 5x cost bar"
        print(f"\n  {fam}")
        print(f"    pick: {pick['cell']}")
        print(f"    first 60%:  {int(pick['train_trades'])} trades, ${pick['train_avg_profit_per_trade']:+.2f} "
              f"average profit per trade, {pick['train_win_pct']:.0f}% of them winners, "
              f"worst drawdown {pick['train_worst_drawdown_pct']:.1f}% of the account")
        print(f"    middle 20%: {int(pick['val_trades'])} trades, ${pick['val_avg_profit_per_trade']:+.2f} "
              f"average profit per trade, {pick['val_win_pct']:.0f}% of them winners")
        print(f"    profit as a share of the full position size: "
              f"{pick['profit_pct_of_position_train']:+.3f}% on the first 60%, "
              f"{pick['profit_pct_of_position_val']:+.3f}% on the middle 20%")
        print(f"    profit next to the cost of trading: "
              f"{pick['times_bigger_than_trading_cost_train']:.2f}x and {thick:.2f}x")
        print(f"    -> {outcome}")
        out.append(dict(family=fam, pick=pick["cell"], outcome=outcome,
                        train_trades=int(pick["train_trades"]),
                        train_avg_profit=pick["train_avg_profit_per_trade"],
                        val_trades=int(pick["val_trades"]),
                        val_avg_profit=pick["val_avg_profit_per_trade"],
                        times_cost_val=thick))
    pd.DataFrame(out).to_csv("step320_picks.csv", index=False)
    return out


def anatomy():
    print("\n" + "=" * 96)
    print("2. ANATOMY OF FAMILY A's PICK — the volatility-gated trend rule on 4h bars, 20/100")
    print("=" * 96)
    d, s, f = frame("4h")
    i_tr, i_va = split_points(len(d))
    a = (atr(d, 14) / d["close"] * 100)
    gate = float(a.iloc[:i_tr].dropna().quantile(1 - 0.6321))
    buf = BTC_R150_BUFFER_PCT / BTC_TRAIN_4H_ATR_PCT * float(a.iloc[:i_tr].dropna().median())
    for fast, slow in ((20, 100), (10, 50)):
        sig = vol_gated_ma(d, fast=fast, slow=slow, atr_n=14, min_atr_pct=gate)
        sv = sig.fillna(0).to_numpy()
        ent = (sv == 1) & (np.roll(sv, 1) != 1)
        ent[0] = False
        warm = slow + 20
        ent[:warm] = False
        entries = [(int(i), 1) for i in np.flatnonzero(ent)]
        sb = lambda tc: E.stop_structure_trailing(buffer_pct=buf, fallback_pct=8.0)
        tb = lambda st: E.target_opposite_signal(sv, treat_zero_as_exit=True)
        t1, skip = run_edge_ctx(d, s, entries, sb, tb, 60 * 6, f, lo_idx=warm, hi_idx=i_tr)
        st = stats(t1)
        reasons = pd.Series([t["reason"] for t in t1]).value_counts()
        pnl_by_reason = pd.Series({r: float(np.mean([t["pnl"] for t in t1 if t["reason"] == r]))
                                   for r in reasons.index})
        print(f"\n  {fast}/{slow} on the first 60%: {st['n']} trades, ${st['exp']:+.2f} average, "
              f"{st['win']*100:.0f}% winners, {skip} entries skipped because no confirmed swing "
              f"existed yet to hang a stop on.")
        print(f"    chart stop sat a median {st['med_stop_pct']:.2f}% of price away from entry; "
              f"risking 2% of the account at that distance produced {st['avg_lev']:.1f}x leverage "
              f"on average (leverage is the output, not the dial).")
        print(f"    median time in a trade: {st['med_hold_h']:.0f} hours "
              f"({st['med_hold_h']/24:.1f} days)")
        for r in reasons.index:
            print(f"    ended by {r}: {reasons[r]} trades, ${pnl_by_reason[r]:+.2f} average")
        wins = [t["pnl"] for t in t1 if t["pnl"] > 0]
        losses = [t["pnl"] for t in t1 if t["pnl"] <= 0]
        if wins and losses:
            wpct = np.mean([(t["exit_price"] / t["entry_price"] - 1) * 100 for t in t1 if t["pnl"] > 0])
            lpct = np.mean([(t["exit_price"] / t["entry_price"] - 1) * 100 for t in t1 if t["pnl"] <= 0])
            print(f"    winners captured {wpct:+.2f}% of price on average; losers gave back "
                  f"{lpct:+.2f}% of price. (Price moves, not changes in a position's margin.)")


def turn_of_month_measurement():
    print("\n" + "=" * 96)
    print("3. TURN OF THE MONTH — is the tendency itself real on Ethereum, separate from whether")
    print("   a costed trade can harvest it?")
    print("=" * 96)
    d, _, _ = frame("1d")
    i_tr, i_va = split_points(len(d))
    ts = pd.DatetimeIndex(d["timestamp"])
    days_to_end = np.array([(pd.Timestamp(t).days_in_month - pd.Timestamp(t).day) for t in ts])
    dom = np.array([pd.Timestamp(t).day for t in ts])
    ret = (d["close"].pct_change().shift(-1) * 100).to_numpy()
    win = (days_to_end <= 3) | (dom <= 3)
    for label, lo, hi in (("first 60%", 0, i_tr), ("middle 20%", i_tr, i_va)):
        r = ret[lo:hi]
        w = win[lo:hi]
        m = ~np.isnan(r)
        inw, outw = r[w & m], r[~w & m]
        se = np.sqrt(inw.var(ddof=1) / len(inw) + outw.var(ddof=1) / len(outw))
        t = (inw.mean() - outw.mean()) / se
        # simple buy-and-hold-the-window total, no costs, purely descriptive
        print(f"  {label}: {len(inw)} days inside the window averaging {inw.mean():+.3f}% price move, "
              f"{len(outw)} days outside averaging {outw.mean():+.3f}%, t = {t:.2f}. "
              f"Compounded price move from holding only the window days: "
              f"{(np.prod(1 + inw/100) - 1)*100:+.1f}%; holding only the days outside it: "
              f"{(np.prod(1 + outw/100) - 1)*100:+.1f}%.")
    print("  Both are price moves on an unlevered holding with no costs charged. They say whether")
    print("  the tendency exists, not whether it is tradeable.")


def relative_strength_hypothesis():
    print("\n" + "=" * 96)
    print("4. ETHEREUM'S OWN PERSONALITY — a hypothesis with a measurement, not a conclusion.")
    print("   HYPOTHESIS: Ethereum's trend entries pay better when Ethereum has recently been")
    print("   STRONGER than Bitcoin, and worse when it has been weaker. Bitcoin cannot have this")
    print("   conditioning variable at all, so if it holds it is Ethereum's own, not a port.")
    print("   Measured on the FIRST 60% only. No extra reading of the middle 20% is spent here.")
    print("=" * 96)
    d, s, f = frame("4h")
    i_tr, i_va = split_points(len(d))
    btc = pd.read_parquet("data_bybit_BTCUSDT_4h_full.parquet").sort_values("timestamp").reset_index(drop=True)
    m = pd.merge_asof(d[["timestamp", "close"]].rename(columns={"close": "eth"}),
                      btc[["timestamp", "close"]].rename(columns={"close": "btc"}),
                      on="timestamp", direction="backward")
    ratio = (m["eth"] / m["btc"]).to_numpy()
    for lookback_days in (7, 30, 90):
        lb = lookback_days * 6      # 4h bars
        rel = np.full(len(ratio), np.nan)
        rel[lb:] = ratio[lb:] / ratio[:-lb] - 1        # backward-looking only
        a = (atr(d, 14) / d["close"] * 100)
        gate = float(a.iloc[:i_tr].dropna().quantile(1 - 0.6321))
        buf = BTC_R150_BUFFER_PCT / BTC_TRAIN_4H_ATR_PCT * float(a.iloc[:i_tr].dropna().median())
        sig = vol_gated_ma(d, fast=10, slow=50, atr_n=14, min_atr_pct=gate)
        sv = sig.fillna(0).to_numpy()
        ent = (sv == 1) & (np.roll(sv, 1) != 1)
        ent[0] = False
        warm = 70
        ent[:warm] = False
        entries = [(int(i), 1) for i in np.flatnonzero(ent)]
        sb = lambda tc: E.stop_structure_trailing(buffer_pct=buf, fallback_pct=8.0)
        tb = lambda st: E.target_opposite_signal(sv, treat_zero_as_exit=True)
        t1, _ = run_edge_ctx(d, s, entries, sb, tb, 60 * 6, f, lo_idx=warm, hi_idx=i_tr)
        if not t1:
            continue
        strong = [t for t in t1 if rel[t["entry_idx"] - 1] == rel[t["entry_idx"] - 1] and rel[t["entry_idx"] - 1] > 0]
        weak = [t for t in t1 if rel[t["entry_idx"] - 1] == rel[t["entry_idx"] - 1] and rel[t["entry_idx"] - 1] <= 0]
        if len(strong) < 10 or len(weak) < 10:
            print(f"  {lookback_days}-day relative strength: only {len(strong)} / {len(weak)} trades "
                  f"per side, too thin to say anything.")
            continue
        sp = np.array([t["pnl"] for t in strong])
        wp = np.array([t["pnl"] for t in weak])
        se = np.sqrt(sp.var(ddof=1) / len(sp) + wp.var(ddof=1) / len(wp))
        tstat = (sp.mean() - wp.mean()) / se if se else float("nan")
        print(f"  Ethereum stronger than Bitcoin over the trailing {lookback_days} days: "
              f"{len(strong)} trades, ${sp.mean():+.2f} average profit per trade "
              f"({(sp > 0).mean()*100:.0f}% winners)")
        print(f"  Ethereum weaker: {len(weak)} trades, ${wp.mean():+.2f} average "
              f"({(wp > 0).mean()*100:.0f}% winners).  Difference t = {tstat:.2f}")
    print("\n  Read this as a hypothesis with a first measurement attached. Two windows agreeing")
    print("  would be a hypothesis; a third and fourth market decide it. Nothing here is a finding")
    print("  yet, and no cell above was selected using it.")


def main():
    pre_registered_picks()
    anatomy()
    turn_of_month_measurement()
    relative_strength_hypothesis()


if __name__ == "__main__":
    main()
