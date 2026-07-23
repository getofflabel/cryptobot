"""
step45b_test_look.py — the sealed-test look at round 45B's strongest news
survivor. Replicates main()'s exact data prep (news-span slice, split, no-
lookahead alignment); the only new thing is scoring on iloc[i_va:n].

Config: A-news-momentum, FIRST-BAR-MOVE direction, 1h, stop 1.2% / target
2.4% (2x), hold 24h. Train +$23.74/t x200, val +$7.11/t x67.
"""

import pandas as pd, numpy as np
from step45b_news_events import (
    classify_frame, fetch_bybit_deep, fetch_funding_history, align_funding,
    split_points, align_events, make_bool_array, day_trade_signal,
    hours_to_bars, HARD_STOP_CAP,
)
from backtest import run_backtest

news = classify_frame(pd.read_parquet("data_watcherguru_history.parquet"))
relevant = news[news["relevant"]]
nmin, nmax = news["utc_timestamp"].min(), news["utc_timestamp"].max()

dfull = fetch_bybit_deep("1h", "BTCUSDT")
fh = fetch_funding_history("BTCUSDT")
mask = (dfull["timestamp"] >= nmin - pd.Timedelta(hours=24)) & \
       (dfull["timestamp"] <= nmax + pd.Timedelta(hours=24))
d = dfull[mask].reset_index(drop=True)
f = align_funding(d, fh)
n, i_tr, i_va = split_points(d)

floor, trad, valid = align_events(d, relevant["utc_timestamp"])
trad = trad[valid]; trad = trad[trad < len(d)]
opens, closes = d["open"].to_numpy(), d["close"].to_numpy()
sign = np.sign(closes[trad] - opens[trad])
up_idx, down_idx = trad[sign > 0], trad[sign < 0]         # momentum: follow

el = make_bool_array(len(d), up_idx)
es = make_bool_array(len(d), down_idx)
sig = day_trade_signal(d, el, es, hours_to_bars(d, 24))

r = run_backtest(d.iloc[i_va:n].reset_index(drop=True),
                 sig.iloc[i_va:n].reset_index(drop=True),
                 execution="maker",
                 funding_series=f.iloc[i_va:n].reset_index(drop=True),
                 stop_pct=min(1.2, HARD_STOP_CAP), target_pct=2.4)

holds = []
for t in r.trades:
    try: holds.append((t.exit_time - t.entry_time).total_seconds() / 3600)
    except Exception: pass
med = sorted(holds)[len(holds)//2] if holds else 0
print(f"\n=== SEALED TEST — news momentum 1h first-bar-move stop1.2/tgt2.4 ===")
print(f"  test window {d['timestamp'].iloc[i_va]:%Y-%m-%d} -> "
      f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | {len(trad)} total news entries in-sample")
print(f"  trades {len(r.trades)} | expectancy ${r.expectancy:+,.2f}/t | "
      f"win {r.win_rate*100:.1f}% | return {r.total_return_pct:+.1f}% | "
      f"maxDD {r.max_drawdown_pct:.1f}% | median hold {med:.0f}h")
v = "PASS" if (r.expectancy > 0 and len(r.trades) >= 8) else \
    ("THIN" if r.expectancy > 0 else "FAIL")
print(f"  VERDICT: {v}")
