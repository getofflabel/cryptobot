"""
step150e_news_momentum.py — ROUND 150, edge 5/5: news momentum, first-hour
direction.

ORIGINAL VALIDATION:
  R45B (step45b_news_events.py): fixed trigger — a relevant WatcherGuru
    headline -> first full 1h bar after the event -> enter at THAT bar's
    own close, direction = that bar's own close-vs-open sign. Bracket:
    TP+2.4%/SL-1.2%/24h cap. SEALED +$20.81/t x67. First strategy ever to
    pass a sealed test in this program.
  R65 (step65_news_eyes.py) N2 STRUCTURE TRAILING: SAME fixed trigger, no
    fixed TP; initial floor = entry-bar's own opposite extreme + buffer,
    ratcheting favorably as new confirmed k=5 swing lows/highs print,
    "ride until the chart says stop." SEALED +$10.35/t x104, the version
    now DEPLOYED LIVE (playbook's "news momentum, first-hour direction,
    sealed PASS"). Costs: step65's OWN bespoke simulator used maker 2bp on
    EVERY entry fill (blended, not taker) and modeled NO spread/slippage
    at all (docstring: "no extra spread/slippage -- already at the exact
    level").

TONIGHT'S CHANGE
  N2 is already the closest thing to a genuine per-trade structure stop of
  all five edges (an actual OHLC level, ratcheting on confirmed swings, not
  a swept round-number %) -- so this retest is the most surgical: same
  entry trigger, same "ride the trailing floor" shape, standardized onto
  exits.py's stop_structure_trailing() (initial floor = the most recent
  CONFIRMED swing as of entry, or an 8% fallback if none exists yet --
  exits.py's own generic construction, a small, documented departure from
  N2's bespoke "entry-bar's own extreme" floor) with NO fixed target
  (target=None, matching N2's trail-only philosophy exactly).
  execution: "taker", ALWAYS -- fixing the one real assumption gap: every
  entry pays the taker fee + crosses the spread/slippage (step65's sim
  charged a flat maker fee on every entry and modeled no spread/slippage
  at all).
Entry signal (classify_headline + align_events + first-bar-move direction)
is REUSED VERBATIM from step45b_news_events.py / step65_news_eyes.py's
build_news_entries().
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import exits as E
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step65_news_eyes import MAX_HOLD_H, build_news_entries, split_points
from step150_common import (chance_baseline, fmt_stats, mask_to_events,
                            run_edge, thickness, trade_stats, verdict_for)

K = 5
FALLBACK_PCT = 8.0


def stop_builder(tc):
    return E.stop_structure_trailing(buffer_pct=0.0, fallback_pct=FALLBACK_PCT)


def target_builder(stop):
    return None    # trail-only, exactly N2's philosophy: no fixed profit target


def main():
    print("=" * 70)
    print("STEP150e — News momentum (N2 structure-trailing) — TAKER RE-TEST")
    print("=" * 70)
    btc1h_full = fetch_bybit_deep("1h", "BTCUSDT")
    funding_hist = fetch_funding_history("BTCUSDT")
    news = pd.read_parquet("data_watcherguru_history.parquet")
    print(f"BTC 1h: {len(btc1h_full)} bars | WatcherGuru: {len(news)} posts, "
         f"{news['utc_timestamp'].min():%Y-%m-%d} -> {news['utc_timestamp'].max():%Y-%m-%d}")

    news_min, news_max = news["utc_timestamp"].min(), news["utc_timestamp"].max()
    mask = ((btc1h_full["timestamp"] >= news_min - pd.Timedelta(hours=24)) &
           (btc1h_full["timestamp"] <= news_max + pd.Timedelta(hours=24)))
    d_span = btc1h_full[mask].reset_index(drop=True)
    n, i_tr, i_va = split_points(d_span)
    print(f"news-span slice: {len(d_span)} bars | train->{i_tr} val->{i_va} "
         f"(sealed {n - i_va} bars NEVER LOADED)")

    d = d_span.iloc[:i_va].reset_index(drop=True)     # sealed rows dropped entirely, R45B/R65 convention
    entries_all = build_news_entries(d, news)
    funding_full = align_funding(d, funding_hist)
    print(f"entries (train+val window): {len(entries_all)} "
         f"(long {sum(1 for _, dd in entries_all if dd > 0)} / "
         f"short {sum(1 for _, dd in entries_all if dd < 0)})")

    def slice_entries(lo, hi):
        return [(i - lo, dr) for i, dr in entries_all if lo <= i < hi]

    tr_candles, tr_fund = d.iloc[0:i_tr].reset_index(drop=True), funding_full.iloc[0:i_tr].reset_index(drop=True)
    va_candles, va_fund = d.iloc[i_tr:i_va].reset_index(drop=True), funding_full.iloc[i_tr:i_va].reset_index(drop=True)
    tr_entries, va_entries = slice_entries(0, i_tr), slice_entries(i_tr, i_va)
    max_hold_bars = MAX_HOLD_H     # 1h bars, 24h cap

    tr_trades, tr_skip = run_edge(tr_candles, tr_entries, stop_builder, target_builder,
                                  max_hold_bars, funding_bps=tr_fund,
                                  fill_convention="same_close", k=K)
    va_trades, va_skip = run_edge(va_candles, va_entries, stop_builder, target_builder,
                                  max_hold_bars, funding_bps=va_fund,
                                  fill_convention="same_close", k=K)
    tr_st, va_st = trade_stats(tr_trades), trade_stats(va_trades)

    print(fmt_stats("TRAIN", tr_st), f"| skipped(no structure)={tr_skip}")
    print(fmt_stats("VAL  ", va_st), f"| skipped(no structure)={va_skip}")
    verdict = verdict_for(tr_st, va_st)
    print(f"VERDICT: {verdict}")

    all_trades = tr_trades + va_trades
    avg_notional = float(np.mean([t["notional"] for t in all_trades])) if all_trades else 0.0
    th = thickness(va_st["expectancy"], avg_notional)
    print(f"THICKNESS (val): {th['pct_notional']:.4f}% of notional | "
         f"{th['mult_12bps']:.2f}x task's 12bps round-trip | "
         f"{th['mult_full_18bps']:.2f}x full 18bps CostModel round-trip")

    long_n = sum(1 for _, dr in va_entries if dr > 0)
    long_frac = long_n / max(1, len(va_entries))
    cb = chance_baseline(va_candles, len(va_entries), long_frac, stop_builder, target_builder,
                         max_hold_bars, va_fund, "same_close", k=K, draws=100)
    print(f"CHANCE BASELINE (val window, {cb['n_draws']} random-entry draws, "
         f"n={cb['sample_events']} each, {long_frac*100:.0f}% long mix): "
         f"mean exp ${cb['mean_exp']:+,.2f}/trade")
    print(f"EDGE vs CHANCE: ${va_st['expectancy']:+,.2f} vs ${cb['mean_exp']:+,.2f} "
         f"-> {'BEATS' if va_st['expectancy'] > cb['mean_exp'] else 'DOES NOT BEAT'} chance")

    pd.DataFrame(tr_trades + va_trades).to_csv("step150e_table.csv", index=False)
    print("wrote step150e_table.csv")
    return dict(tr=tr_st, va=va_st, verdict=verdict, thickness=th, chance=cb,
               avg_notional=avg_notional)


if __name__ == "__main__":
    main()
