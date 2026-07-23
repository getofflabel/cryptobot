"""
step45d_test_look.py — round 45B's authorized SEALED-TEST looks (news events).

Three survivors from step45b_news_events.py's train/val gauntlet, reconstructed
byte-for-byte (same cached news, same classification, same alignment, same
entries, same maker execution + real funding). The ONLY new thing is the slice:
the held-out final 20% [i_va:n], never touched by the search that selected them.

Survivors under examination (train/val from the 45B run, for reference):
  1. B-news-fade    15m  stop1.2% tgt3x hold24h  first_bar_move  (tr +$4.19/203, va +$8.54/70)
  2. A-news-momentum 1h  stop1.2% tgt3x hold24h  keyword         (tr +$3.98/144, va +$20.04/48)
  3. A-news-momentum 1h  stop1.2% tgt2x hold24h  first_bar_move  (tr +$23.74/200, va +$7.11/67)

Test-look protocol (identical to step43c/step45c): PASS = positive expectancy
AND >=15 test trades; THIN = positive but under the trade floor; FAIL =
negative. One look per family; logged in RESEARCH_LOG.md. If it fails it is
BURIED, never re-tuned.
"""

import numpy as np
import pandas as pd

from backtest import run_backtest
from step43_daytrade import (HARD_STOP_CAP, day_trade_signal, hours_to_bars,
                             split_points)
from step45b_news_events import (align_events, align_funding, classify_frame,
                                 fetch_bybit_deep, fetch_funding_history,
                                 harvest_history, make_bool_array)


def report(name, r):
    holds = []
    for t in r.trades:
        try:
            holds.append((t.exit_time - t.entry_time).total_seconds() / 3600)
        except Exception:
            pass
    med_hold = sorted(holds)[len(holds) // 2] if holds else 0
    verdict = ("PASS" if (r.expectancy > 0 and len(r.trades) >= 15)
               else ("THIN" if r.expectancy > 0 else "FAIL"))
    print(f"\n=== SEALED TEST — {name} ===")
    print(f"  trades {len(r.trades)} | expectancy ${r.expectancy:+,.2f}/t | "
          f"win {r.win_rate * 100:.1f}% | return {r.total_return_pct:+.1f}% | "
          f"maxDD {r.max_drawdown_pct:.1f}% | median hold {med_hold:.0f}h")
    print(f"  verdict: {verdict}")
    return verdict


def sealed_run(d, f, el, es, i_va, n, stop_pct, target_pct, max_hold_h):
    stop_use = min(stop_pct, HARD_STOP_CAP)
    sig = day_trade_signal(d, el, es, hours_to_bars(d, max_hold_h))
    return run_backtest(
        d.iloc[i_va:n].reset_index(drop=True),
        sig.iloc[i_va:n].reset_index(drop=True),
        execution="maker",
        funding_series=f.iloc[i_va:n].reset_index(drop=True),
        stop_pct=stop_use, target_pct=target_pct,
    )


def main():
    # --- rebuild the exact 45B inputs from cache ---
    news_raw, _ = harvest_history()          # cache path: no network harvest
    news = classify_frame(news_raw)
    relevant = news[news["relevant"]]
    bullish = relevant[relevant["tag"] == "BULLISH"]
    bearish = relevant[relevant["tag"] == "BEARISH"]

    frames_full = {tf: fetch_bybit_deep(tf, "BTCUSDT") for tf in ("15m", "1h")}
    funding_hist = fetch_funding_history("BTCUSDT")
    news_min, news_max = news["utc_timestamp"].min(), news["utc_timestamp"].max()

    frames, funding, splits = {}, {}, {}
    for tf in ("15m", "1h"):
        dfull = frames_full[tf]
        mask = (dfull["timestamp"] >= news_min - pd.Timedelta(hours=24)) & \
               (dfull["timestamp"] <= news_max + pd.Timedelta(hours=24))
        d = dfull[mask].reset_index(drop=True)
        fu = align_funding(d, funding_hist)
        n, i_tr, i_va = split_points(d)
        d = d.iloc[:n].reset_index(drop=True)
        fu = fu.iloc[:n].reset_index(drop=True)
        frames[tf], funding[tf], splits[tf] = d, fu, (n, i_tr, i_va)
        print(f"  {tf}: sealed test window "
              f"{d['timestamp'].iloc[i_va]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d} "
              f"({n - i_va} bars, ={100 * (n - i_va) / n:.0f}% held out)")

    def keyword_idx(tf):
        d = frames[tf]
        fb, _, vb = align_events(d, bullish["utc_timestamp"])
        fbe, _, vbe = align_events(d, bearish["utc_timestamp"])
        return fb[vb], fbe[vbe]                      # long=bull, short=bear

    def first_bar_idx(tf):
        d = frames[tf]
        _, trad, valid = align_events(d, relevant["utc_timestamp"])
        trad = trad[valid]
        trad = trad[trad < len(d)]
        opens, closes = d["open"].to_numpy(), d["close"].to_numpy()
        sign = np.sign(closes[trad] - opens[trad])
        return trad[sign > 0], trad[sign < 0]        # up_idx, down_idx

    results = {}

    # 1. B-news-fade 15m first_bar_move stop1.2% tgt3x hold24h
    #    fade => long on DOWN first-bar move, short on UP
    d, f, (n, _, i_va) = frames["15m"], funding["15m"], splits["15m"]
    up_idx, down_idx = first_bar_idx("15m")
    el = make_bool_array(len(d), down_idx)
    es = make_bool_array(len(d), up_idx)
    r = sealed_run(d, f, el, es, i_va, n, 1.2, 1.2 * 3.0, 24)
    results["B-news-fade 15m first_bar_move stop1.2/tgt3x/24h"] = report(
        "B-news-fade 15m first_bar_move stop1.2% tgt3x hold24h", r)

    # 2. A-news-momentum 1h keyword stop1.2% tgt3x hold24h
    #    momentum => long on bull headline, short on bear headline
    d, f, (n, _, i_va) = frames["1h"], funding["1h"], splits["1h"]
    bull_idx, bear_idx = keyword_idx("1h")
    el = make_bool_array(len(d), bull_idx)
    es = make_bool_array(len(d), bear_idx)
    r = sealed_run(d, f, el, es, i_va, n, 1.2, 1.2 * 3.0, 24)
    results["A-news-momentum 1h keyword stop1.2/tgt3x/24h"] = report(
        "A-news-momentum 1h keyword stop1.2% tgt3x hold24h", r)

    # 3. A-news-momentum 1h first_bar_move stop1.2% tgt2x hold24h
    #    momentum => long on UP first-bar move, short on DOWN
    up_idx, down_idx = first_bar_idx("1h")
    el = make_bool_array(len(d), up_idx)
    es = make_bool_array(len(d), down_idx)
    r = sealed_run(d, f, el, es, i_va, n, 1.2, 1.2 * 2.0, 24)
    results["A-news-momentum 1h first_bar_move stop1.2/tgt2x/24h"] = report(
        "A-news-momentum 1h first_bar_move stop1.2% tgt2x hold24h", r)

    print("\n" + "=" * 62)
    print("SEALED-TEST SUMMARY (round 45B news events)")
    print("=" * 62)
    for name, v in results.items():
        print(f"  {v:5s}  {name}")


if __name__ == "__main__":
    main()
