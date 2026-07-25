"""
step324_eth_gate_ladder.py — ROUND 320, PHASE 4: which of Bitcoin's OWN
selectivities should Ethereum's volatility gate be matched to?

This exists because "Bitcoin's number" turned out not to be one number.
Bitcoin's 1.50% floor on the 14-bar range let entries through on:

    63.2% of its bars in the first 60% of its history  (where the rule was chosen)
    53.5% of its bars over its whole history
    24.3% of its bars in the most recent fifth
    18.7% is the figure written into round 170's own notes

Bitcoin's volatility fell steadily across its history, so the same constant
grew steadily pickier over time. Matching Ethereum to "Bitcoin's
selectivity" therefore has four defensible answers, and round 170 left an
explicit open item: retest this with a faster pair of averages so the
sample floor is actually cleared.

All four rungs are declared here BEFORE the middle 20% is read, and the
pick is the best rung on the FIRST 60% with at least 30 trades there. The
final untouched slice is not loaded.

Everything else is identical to step322: market orders both ways, a
ratcheting chart stop off Ethereum's own confirmed swings, size = dollars
risked / distance to that stop, real funding.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import exits as E
from step321_eth_engine import run_edge_ctx, split_points, stats, thickness, verdict
from step322_eth_shape_tests import BTC_R150_BUFFER_PCT, BTC_TRAIN_4H_ATR_PCT, frame
from strategy import atr, vol_gated_ma

pd.set_option("display.width", 240)

RUNGS = {"Bitcoin's first-60% window (63.2% of bars)": 0.632,
         "Bitcoin's whole history (53.5% of bars)": 0.535,
         "Bitcoin's most recent fifth (24.3% of bars)": 0.243,
         "the 18.7% figure in round 170's notes": 0.187}

ROWS = []


def main():
    for tf in ("4h", "1h"):
        d, s, f = frame(tf)
        i_tr, i_va = split_points(len(d))
        a = (atr(d, 14) / d["close"] * 100)
        atr_tr = a.iloc[:i_tr].dropna()
        buf = BTC_R150_BUFFER_PCT / BTC_TRAIN_4H_ATR_PCT * float(atr_tr.median())
        print("\n" + "=" * 96)
        print(f"ETHEREUM {tf} BARS — Ethereum's own 14-bar range runs a median "
              f"{float(atr_tr.median()):.3f}% of price on the first 60%.")
        print("=" * 96)
        for rung, frac in RUNGS.items():
            gate = float(atr_tr.quantile(1 - frac))
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
                mh = 60 * (6 if tf == "4h" else 24)
                t1, _ = run_edge_ctx(d, s, entries, sb, tb, mh, f, lo_idx=warm, hi_idx=i_tr)
                t2, _ = run_edge_ctx(d, s, entries, sb, tb, mh, f, lo_idx=i_tr, hi_idx=i_va)
                tr, va = stats(t1), stats(t2)
                th_tr, th_va = thickness(tr["exp"], tr["avg_notional"]), thickness(va["exp"], va["avg_notional"])
                v = verdict(tr, va)
                print(f"  gate {gate:>5.2f}% [{rung:<44s}] {fast:>2d}/{slow:<3d} "
                      f"train n={tr['n']:>4d} ${tr['exp']:>+8.2f} | val n={va['n']:>4d} "
                      f"${va['exp']:>+8.2f} | {th_va['x_full_cost']:>6.1f}x cost -> {v}")
                ROWS.append(dict(family="A2 volatility gate ladder",
                                 cell=f"{tf} {fast}/{slow} gate {gate:.2f}% matched to {rung}",
                                 timeframe=tf,
                                 dial_in_source_market="1.50% on Bitcoin 4h",
                                 dial_re_derived_for_ethereum=f"{gate:.2f}% on Ethereum {tf}",
                                 train_trades=tr["n"], train_avg_profit_per_trade=tr["exp"],
                                 train_win_pct=tr["win"] * 100, train_return_pct=tr["ret"],
                                 train_worst_drawdown_pct=tr["dd"],
                                 val_trades=va["n"], val_avg_profit_per_trade=va["exp"],
                                 val_win_pct=va["win"] * 100, val_return_pct=va["ret"],
                                 val_worst_drawdown_pct=va["dd"],
                                 profit_pct_of_position_train=th_tr["pct_of_position"],
                                 profit_pct_of_position_val=th_va["pct_of_position"],
                                 times_bigger_than_trading_cost_train=th_tr["x_full_cost"],
                                 times_bigger_than_trading_cost_val=th_va["x_full_cost"],
                                 median_stop_distance_pct_train=tr["med_stop_pct"],
                                 avg_leverage_out_train=tr["avg_lev"],
                                 median_hold_hours_train=tr["med_hold_h"],
                                 verdict=v, source_market="Bitcoin"))

    df = pd.DataFrame(ROWS)
    df.to_csv("step320_gate_ladder_table.csv", index=False)
    ok = df[df["train_trades"] >= 30]
    print("\n" + "=" * 96)
    if len(ok):
        pick = ok.loc[ok["train_avg_profit_per_trade"].idxmax()]
        print("THE PICK (best on the first 60% with at least 30 trades there):")
        print(f"  {pick['cell']}")
        print(f"  first 60%:  {int(pick['train_trades'])} trades, "
              f"${pick['train_avg_profit_per_trade']:+.2f} average profit per trade, "
              f"{pick['times_bigger_than_trading_cost_train']:.2f} times the cost of trading")
        print(f"  middle 20%: {int(pick['val_trades'])} trades, "
              f"${pick['val_avg_profit_per_trade']:+.2f} average profit per trade, "
              f"{pick['times_bigger_than_trading_cost_val']:.2f} times the cost of trading")
        print(f"  -> {pick['verdict']}")
    surv = df[df["verdict"].str.startswith("SURVIVES")]
    print(f"\n{len(surv)} of {len(df)} cells came out positive on both windows with enough trades.")
    return df


if __name__ == "__main__":
    main()
