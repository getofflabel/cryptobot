"""
step23_round31.py — round 31: the GARCH percentile-gate grid on the ride.

Run:  python3 step23_round31.py

HYPOTHESIS (RESEARCH_QUEUE.md, "GARCH era" docket, top pre-specified item):
The live core book is the 4h vol-gated MA champion — a trend follower whose
only regime filter is a FIXED ATR gate (enter longs only when ATR >= 1.5% of
price). Round 29 built walk-forward GARCH(1,1) daily vol FORECASTS (zero
lookahead, refit every 21d; cached in data_garch_btc_1d.parquet) and found a
single GARCH-only gate nearly 3x'd train return with 1/3 the trades
(higher-quality entries) but its val (+40.2%) fell short of the champion's
common-window val (+50.5%) -> no test look, belt retained. This round runs the
PRE-SPECIFIED grid the queue reserved: replace the champion's fixed ATR vol
gate with a GARCH percentile gate at thresholds {50th, 60th, 70th}. A forecast
of high vol is a forward-looking claim that the trend has fuel; a percentile
gate asks "is forecast vol in the top X% of what we've seen so far?"

DISCIPLINE:
- Train/val ONLY. NO test look this round (pre-specified: the GARCH grid is a
  train/val screen; a survivor earns ONE sealed-test look in a LATER round).
- Config frozen HERE, no tuning: three thresholds, gate direction fixed
  (enter only when forecast vol >= threshold — trends want vol), champion's
  funding filter (funding<=1bp) retained, ONLY the ATR gate swapped out.
- No lookahead: the GARCH forecast for day D was built from returns through
  D-1 (round 29). The percentile threshold is a TRAILING expanding quantile
  (min 180 days of history) — it only ever sees the past. Daily gate mapped
  onto 4h bars backward (a day's forecast applies to that day's 4h bars).
- Common window = bars where BOTH the forecast and its trailing threshold
  exist (~2022-02 onward). The champion is RE-SCORED on this exact window as
  the honest benchmark — round 29's +50.5% used a longer (2021-08) window and
  is NOT reused as the bar here.
- Qualify (to earn a future test look) = positive expectancy AND higher val
  return than the champion on the SAME common window, min 30 train / 8 val
  trades. This is a screen, not a deployment.
"""

import numpy as np
import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from strategy import vol_gated_ma


def garch_gate_on_4h(d4, thresh_q, min_periods=180):
    """Boolean per 4h bar: is the walk-forward GARCH daily-vol forecast at or
    above its TRAILING expanding `thresh_q` quantile? Trailing = the quantile
    at day D uses only forecasts up to and including day D, so no lookahead.
    Daily gate mapped onto 4h bars backward (day D's forecast covers day D's
    4h bars). Returns a bool Series indexed like d4, plus the daily threshold
    availability start for windowing."""
    g = pd.read_parquet("data_garch_btc_1d.parquet").dropna(
        subset=["garch_daily_vol"]).reset_index(drop=True)
    v = g["garch_daily_vol"]
    # trailing expanding quantile (min_periods days of baseline before it counts)
    thr = v.expanding(min_periods=min_periods).quantile(thresh_q)
    daily = pd.DataFrame({
        "effective": g["timestamp"],           # forecast known at start of day D
        "gpass": (v >= thr),
        "thr_ok": thr.notna(),
    })
    merged = pd.merge_asof(d4[["timestamp"]], daily,
                           left_on="timestamp", right_on="effective",
                           direction="backward")
    gpass = merged["gpass"].fillna(False).to_numpy()
    thr_ok = merged["thr_ok"].fillna(False).to_numpy()
    return pd.Series(gpass, index=d4.index), pd.Series(thr_ok, index=d4.index)


def score_window(d4, sig, f4, lo, hi):
    return run_backtest(d4.iloc[lo:hi].reset_index(drop=True),
                        sig.iloc[lo:hi].reset_index(drop=True),
                        execution="taker",
                        funding_series=f4.iloc[lo:hi].reset_index(drop=True))


def main():
    d4 = fetch_bybit_deep("4h", "BTCUSDT")
    funding = fetch_funding_history("BTCUSDT")
    f4 = align_funding(d4, funding)
    fund_ok = (f4 <= 1.0)

    # trailing-quantile availability defines the common window start (same for
    # all variants). Use the 0.5 gate just to find where the threshold exists.
    _, thr_ok = garch_gate_on_4h(d4, 0.5)
    common_mask = thr_ok.to_numpy()
    first_common = int(np.argmax(common_mask)) if common_mask.any() else len(d4)
    dc = d4.iloc[first_common:].reset_index(drop=True)
    fc = f4.iloc[first_common:].reset_index(drop=True)
    fund_c = fund_ok.iloc[first_common:].reset_index(drop=True)
    n = len(dc)
    i_tr, i_va = int(n * 0.6), int(n * 0.8)
    print(f"Common window: {dc['timestamp'].iloc[0]:%Y-%m-%d} -> "
          f"{dc['timestamp'].iloc[-1]:%Y-%m-%d}  ({n} 4h bars)")
    print(f"  train {dc['timestamp'].iloc[0]:%Y-%m-%d}..{dc['timestamp'].iloc[i_tr-1]:%Y-%m-%d}"
          f" | val ..{dc['timestamp'].iloc[i_va-1]:%Y-%m-%d}"
          f" | (test held back, NOT looked at)")

    # --- benchmark: the live champion, re-scored on the common window ---
    champ = vol_gated_ma(dc, fast=20, slow=100, min_atr_pct=1.5,
                         entry_filter=fund_c)
    c_tr = score_window(dc, champ, fc, 0, i_tr)
    c_va = score_window(dc, champ, fc, i_tr, i_va)
    champ_val_ret = c_va.total_return_pct

    rows = [{
        "config": "CHAMPION (ATR1.5 gate)",
        "tr_n": len(c_tr.trades), "tr_exp": c_tr.expectancy,
        "tr_ret%": c_tr.total_return_pct,
        "va_n": len(c_va.trades), "va_exp": c_va.expectancy,
        "va_ret%": c_va.total_return_pct,
    }]

    keep = {}
    for q in (0.50, 0.60, 0.70):
        gpass_full, _ = garch_gate_on_4h(d4, q)
        gpass_c = gpass_full.iloc[first_common:].reset_index(drop=True)
        # swap the ATR gate OUT (min_atr_pct=0) and gate on GARCH instead,
        # keeping the champion's funding filter.
        entry = fund_c & gpass_c
        sig = vol_gated_ma(dc, fast=20, slow=100, min_atr_pct=0.0,
                           entry_filter=entry)
        g_tr = score_window(dc, sig, fc, 0, i_tr)
        g_va = score_window(dc, sig, fc, i_tr, i_va)
        keep[q] = (g_tr, g_va)
        rows.append({
            "config": f"GARCH p{int(q*100)} gate",
            "tr_n": len(g_tr.trades), "tr_exp": g_tr.expectancy,
            "tr_ret%": g_tr.total_return_pct,
            "va_n": len(g_va.trades), "va_exp": g_va.expectancy,
            "va_ret%": g_va.total_return_pct,
        })

    print("\nROUND 31 — GARCH percentile-gate grid on the ride "
          "(train + val, common window, full costs):")
    print(pd.DataFrame(rows).to_string(
        index=False, float_format=lambda x: f"{x:,.2f}"))
    print(f"\nChampion val return to beat (this window): {champ_val_ret:+.1f}%")

    survivors = []
    for q, (g_tr, g_va) in keep.items():
        ok = (g_tr.expectancy > 0 and g_va.expectancy > 0
              and len(g_tr.trades) >= 30 and len(g_va.trades) >= 8
              and g_va.total_return_pct > champ_val_ret)
        tag = f"GARCH p{int(q*100)}"
        verdict = ("QUALIFIES (beats champion val)" if ok else
                   "does not beat champion / bar")
        print(f"  {tag}: {verdict} "
              f"(val {g_va.total_return_pct:+.1f}% vs champ {champ_val_ret:+.1f}%, "
              f"{len(g_va.trades)} val trades)")
        if ok:
            survivors.append(tag)

    print(f"\nSurvivors earning a FUTURE sealed-test look: {survivors or 'NONE'}")
    if not survivors:
        print("Belt retained: the champion's fixed ATR gate is not beaten by "
              "any GARCH percentile gate on this window. NO test look taken "
              "(and none was available to take this round by design).")


if __name__ == "__main__":
    main()
