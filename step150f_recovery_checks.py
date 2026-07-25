"""
step150f_recovery_checks.py — ROUND 150, recovery pass.

Morgan's mandate (second half): for every edge that died specifically from
the maker-to-taker / percent-to-structure change, run ONE clean test of a
LESS AGGRESSIVE exits.py structural stop (one level further out) to see if
it recovers the edge. Not a fishing expedition -- one variant per edge,
reusing each edge's own entry construction from step150a-e unchanged.

Variants tested (the "wider" analog for each edge's original stop shape):
  a) CHoCH+confluence   : stop_structure(k=8, n_back=2)  [was n_back=1]
  b) hidden divergence  : stop_structure(k=8, n_back=2, buffer_pct=0.35)
  c) 4h vol-gated trend : stop_structure_trailing(buffer_pct=1.5%)  [was 0%]
  d) RSI3 dip-buy       : stop_structure(k=5, n_back=2)  [was n_back=1]
  e) news momentum      : stop_structure_trailing(buffer_pct=1.0%)  [was 0%]
Same entries, same targets, same taker costs, same train/val slices as the
step150a-e scripts. If train+val don't BOTH turn positive, that's a fine,
final, honest answer -- no further tuning past this one look per edge.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import exits as E
from step150_common import fmt_stats, run_edge, trade_stats, verdict_for

import step150a_choch_confluence as A
import step150b_hidden_divergence as B
import step150c_vol_gated_trend as C
import step150d_rsi3_dipbuy as D
import step150e_news_momentum as N


def report(tag, tr_st, va_st):
    verdict = verdict_for(tr_st, va_st)
    print(fmt_stats(f"  {tag} TRAIN", tr_st))
    print(fmt_stats(f"  {tag} VAL  ", va_st))
    print(f"  {tag} VERDICT: {verdict}\n")
    return verdict


def recovery_a():
    print("=" * 70); print("RECOVERY a) CHoCH+confluence -- stop_structure(k=8, n_back=2)")
    d1h_full = A.fetch_bybit_deep("1h", "BTCUSDT")
    d4h_full = A.fetch_bybit_deep("4h", "BTCUSDT")
    funding_hist = A.fetch_funding_history("BTCUSDT")
    f1h_full = A.align_funding(d1h_full, funding_hist)
    n, i_tr, i_va = A.split_points(d1h_full)
    d1h = d1h_full.iloc[:i_va].reset_index(drop=True)
    f1h = f1h_full.iloc[:i_va].reset_index(drop=True)
    d4h = d4h_full[d4h_full["timestamp"] <= d1h["timestamp"].iloc[-1]].reset_index(drop=True)
    el, es = A.build_entries(d1h, d4h)
    direction = pd.Series(np.where(el, 1, np.where(es, -1, 0)), index=d1h.index)
    entries_all = A.mask_to_events(el | es, direction)
    max_hold_bars = A.days_to_bars(d1h, A.CONF_HOLD_DAYS)

    def stop_wide(tc):
        return E.stop_structure(k=A.K, n_back=2, buffer_pct=0.0, use="wick")
    target_wide = lambda stop: E.target_fixed_r(stop, r_multiple=A.TARGET_MULT)

    def sl(lo, hi): return [(i - lo, dr) for i, dr in entries_all if lo <= i < hi]
    tr_c, tr_e, tr_f = d1h.iloc[:i_tr].reset_index(drop=True), sl(0, i_tr), f1h.iloc[:i_tr].reset_index(drop=True)
    va_c, va_e, va_f = d1h.iloc[i_tr:i_va].reset_index(drop=True), sl(i_tr, i_va), f1h.iloc[i_tr:i_va].reset_index(drop=True)
    tr_tr, _ = run_edge(tr_c, tr_e, stop_wide, target_wide, max_hold_bars, funding_bps=tr_f, k=A.K)
    va_tr, _ = run_edge(va_c, va_e, stop_wide, target_wide, max_hold_bars, funding_bps=va_f, k=A.K)
    return report("a", trade_stats(tr_tr), trade_stats(va_tr))


def recovery_b():
    print("=" * 70); print("RECOVERY b) hidden divergence -- stop_structure(k=8, n_back=2, buf=0.35)")
    d4h_full = B.fetch_bybit_deep("4h", "BTCUSDT")
    funding_hist = B.fetch_funding_history("BTCUSDT")
    f4h_full = B.align_funding(d4h_full, funding_hist)
    n, i_tr, i_va = B.split_points(d4h_full)
    d4h = d4h_full.iloc[:i_va].reset_index(drop=True)
    f4h = f4h_full.iloc[:i_va].reset_index(drop=True)
    champ4h = B.vol_gated_ma(d4h, **B.CHAMP_KW)
    osc = B.rsi(d4h["close"], 14)
    long_reg, short_reg, long_hid, short_hid, low_ext, high_ext = B.divergence_events(d4h, osc, B.K, champ4h)
    direction = pd.Series(np.where(long_hid, 1, np.where(short_hid, -1, 0)), index=d4h.index)
    entries_all = B.mask_to_events(long_hid | short_hid, direction)
    max_hold_bars = B.hours_to_bars(d4h, B.MAX_HOLD_H)

    def stop_wide(tc):
        return E.stop_structure(k=B.K, n_back=2, buffer_pct=B.BUFFER_PCT, use="wick")
    target_wide = lambda stop: E.target_fixed_r(stop, r_multiple=B.TARGET_MULT)

    def sl(lo, hi): return [(i - lo, dr) for i, dr in entries_all if lo <= i < hi]
    tr_c, tr_e, tr_f = d4h.iloc[:i_tr].reset_index(drop=True), sl(0, i_tr), f4h.iloc[:i_tr].reset_index(drop=True)
    va_c, va_e, va_f = d4h.iloc[i_tr:i_va].reset_index(drop=True), sl(i_tr, i_va), f4h.iloc[i_tr:i_va].reset_index(drop=True)
    tr_tr, _ = run_edge(tr_c, tr_e, stop_wide, target_wide, max_hold_bars, funding_bps=tr_f, k=B.K)
    va_tr, _ = run_edge(va_c, va_e, stop_wide, target_wide, max_hold_bars, funding_bps=va_f, k=B.K)
    return report("b", trade_stats(tr_tr), trade_stats(va_tr))


def recovery_c():
    print("=" * 70); print("RECOVERY c) 4h vol-gated trend -- stop_structure_trailing(buffer_pct=1.5)")
    d4h_full = C.fetch_bybit_deep("4h", "BTCUSDT")
    funding_hist = C.fetch_funding_history("BTCUSDT")
    f4h_full = C.align_funding(d4h_full, funding_hist)
    n, i_tr, i_va = C.split_points(d4h_full)
    d4h = d4h_full.iloc[:i_va].reset_index(drop=True)
    f4h = f4h_full.iloc[:i_va].reset_index(drop=True)
    champ = C.vol_gated_ma(d4h, **C.CHAMP_KW).fillna(0.0)
    entries_mask = C.rising_edges(champ)
    entries_all = C.mask_to_events(entries_mask, 1)

    def stop_wide(tc):
        return E.stop_structure_trailing(buffer_pct=1.5, fallback_pct=C.FALLBACK_PCT)

    def sl(lo, hi): return [(i - lo, dr) for i, dr in entries_all if lo <= i < hi]
    tr_c, tr_f = d4h.iloc[:i_tr].reset_index(drop=True), f4h.iloc[:i_tr].reset_index(drop=True)
    va_c, va_f = d4h.iloc[i_tr:i_va].reset_index(drop=True), f4h.iloc[i_tr:i_va].reset_index(drop=True)
    tr_e, va_e = sl(0, i_tr), sl(i_tr, i_va)
    tr_sig = champ.iloc[:i_tr].reset_index(drop=True).to_numpy()
    va_sig = champ.iloc[i_tr:i_va].reset_index(drop=True).to_numpy()
    tr_tr, _ = run_edge(tr_c, tr_e, stop_wide, C.make_target_builder(tr_sig), len(tr_c), funding_bps=tr_f, k=C.K)
    va_tr, _ = run_edge(va_c, va_e, stop_wide, C.make_target_builder(va_sig), len(va_c), funding_bps=va_f, k=C.K)
    return report("c", trade_stats(tr_tr), trade_stats(va_tr))


def recovery_d():
    print("=" * 70); print("RECOVERY d) RSI3 dip-buy -- stop_structure(k=5, n_back=2)")
    d1h_full = D.fetch_bybit_deep("1h", "BTCUSDT")
    d4h_full = D.fetch_bybit_deep("4h", "BTCUSDT")
    funding_hist = D.fetch_funding_history("BTCUSDT")
    f1h_full = D.align_funding(d1h_full, funding_hist)
    n, i_tr, i_va = D.split_points(d1h_full)
    d1h = d1h_full.iloc[:i_va].reset_index(drop=True)
    f1h = f1h_full.iloc[:i_va].reset_index(drop=True)
    d4h = d4h_full[d4h_full["timestamp"] <= d1h["timestamp"].iloc[-1]].reset_index(drop=True)
    champ4h = D.vol_gated_ma(d4h, **D.CHAMP_KW)
    champ_1h = D.champ_aligned(d4h, champ4h, d1h)
    r3 = D.rsi(d1h["close"], 3)
    entries_mask = ((champ_1h == 1) & (r3 < D.RSI_THRESH)).fillna(False)
    entries_all = D.mask_to_events(entries_mask, 1)

    def stop_wide(tc):
        return E.stop_structure(k=D.K, n_back=2, buffer_pct=0.0, use="wick")
    target_wide = lambda stop: E.target_fixed_r(stop, r_multiple=D.TARGET_MULT)

    def sl(lo, hi): return [(i - lo, dr) for i, dr in entries_all if lo <= i < hi]
    tr_c, tr_e, tr_f = d1h.iloc[:i_tr].reset_index(drop=True), sl(0, i_tr), f1h.iloc[:i_tr].reset_index(drop=True)
    va_c, va_e, va_f = d1h.iloc[i_tr:i_va].reset_index(drop=True), sl(i_tr, i_va), f1h.iloc[i_tr:i_va].reset_index(drop=True)
    tr_tr, _ = run_edge(tr_c, tr_e, stop_wide, target_wide, D.MAX_HOLD_H, funding_bps=tr_f, k=D.K)
    va_tr, _ = run_edge(va_c, va_e, stop_wide, target_wide, D.MAX_HOLD_H, funding_bps=va_f, k=D.K)
    return report("d", trade_stats(tr_tr), trade_stats(va_tr))


def recovery_e():
    print("=" * 70); print("RECOVERY e) news momentum -- stop_structure_trailing(buffer_pct=1.0)")
    btc1h_full = N.fetch_bybit_deep("1h", "BTCUSDT")
    funding_hist = N.fetch_funding_history("BTCUSDT")
    news = pd.read_parquet("data_watcherguru_history.parquet")
    news_min, news_max = news["utc_timestamp"].min(), news["utc_timestamp"].max()
    mask = ((btc1h_full["timestamp"] >= news_min - pd.Timedelta(hours=24)) &
           (btc1h_full["timestamp"] <= news_max + pd.Timedelta(hours=24)))
    d_span = btc1h_full[mask].reset_index(drop=True)
    n, i_tr, i_va = N.split_points(d_span)
    d = d_span.iloc[:i_va].reset_index(drop=True)
    entries_all = N.build_news_entries(d, news)
    funding_full = N.align_funding(d, funding_hist)

    def stop_wide(tc):
        return E.stop_structure_trailing(buffer_pct=1.0, fallback_pct=N.FALLBACK_PCT)

    def sl(lo, hi): return [(i - lo, dr) for i, dr in entries_all if lo <= i < hi]
    tr_c, tr_f = d.iloc[:i_tr].reset_index(drop=True), funding_full.iloc[:i_tr].reset_index(drop=True)
    va_c, va_f = d.iloc[i_tr:i_va].reset_index(drop=True), funding_full.iloc[i_tr:i_va].reset_index(drop=True)
    tr_e, va_e = sl(0, i_tr), sl(i_tr, i_va)
    tr_tr, _ = run_edge(tr_c, tr_e, stop_wide, N.target_builder, N.MAX_HOLD_H, funding_bps=tr_f,
                        fill_convention="same_close", k=N.K)
    va_tr, _ = run_edge(va_c, va_e, stop_wide, N.target_builder, N.MAX_HOLD_H, funding_bps=va_f,
                        fill_convention="same_close", k=N.K)
    return report("e", trade_stats(tr_tr), trade_stats(va_tr))


if __name__ == "__main__":
    verdicts = {}
    verdicts["a"] = recovery_a()
    verdicts["b"] = recovery_b()
    verdicts["c"] = recovery_c()
    verdicts["d"] = recovery_d()
    verdicts["e"] = recovery_e()
    print("=" * 70)
    print("RECOVERY SUMMARY:", verdicts)
