"""
step7_deep_search.py — round 2 of the hunt: six YEARS of data, not one.

Run:  python3 step7_deep_search.py

WHY THE DATA SOURCE CHANGES (and why that is honest)

Round 1's finding was regime-dependence: everything lost in the chop and
shone in the spring trend. One year of BloFin history contains roughly one
regime and a half — not enough to tell "works" from "worked lately".
Bybit's public API serves BTC perp candles back to March 2020: COVID crash,
2020-21 mania, 2022 collapse, 2023 grind, 2024-25 cycle, and today. BTC is
BTC; the candles describe the same asset the bot trades on BloFin, and we
still charge BloFin's OWN fees (6 bps taker) on every simulated fill.

Discipline unchanged from step 6, windows now measured in YEARS:
  TRAIN  oldest 60%  (~2020-2023)  rank everything
  VAL    next  20%   (~2023-2025)  selection happens here
  TEST   newest 20%  (~2025-2026)  ONE look, finalists only

New this round: long/short variants of the trend systems. These are
perpetual futures — shorting costs nothing extra, and a trend follower that
can short earns in bear years instead of sitting flat.
"""

import os
import time

import pandas as pd

from backtest import run_backtest
from exchange import BybitExchange
from strategy import (bollinger_meanrev, buy_and_hold, donchian_breakout,
                      ma_crossover, ma_regime, momentum_roc, resample_4h,
                      rsi_meanrev)


def fetch_bybit_deep(timeframe: str = "4h",
                     symbol: str = "BTCUSDT") -> pd.DataFrame:
    """Full perp history for any symbol from Bybit mainnet public data."""
    cache = f"data_bybit_{symbol}_{timeframe}_full.parquet"
    if os.path.exists(cache):
        df = pd.read_parquet(cache)
        print(f"  {symbol} {timeframe}: {len(df)} bars from cache")
        return df

    ex = BybitExchange(env="mainnet")
    pages, end_ms = [], None
    while True:
        page = ex.get_candles(symbol, timeframe, limit=1000, end_ms=end_ms)
        if page.empty:
            break
        pages.append(page)
        oldest = page["timestamp"].iloc[0]
        end_ms = int(oldest.timestamp() * 1000) - 1
        if len(pages) % 10 == 0:
            print(f"    ...back to {oldest:%Y-%m-%d} "
                  f"({sum(len(p) for p in pages)} bars)")
        if oldest.year <= 2020 and oldest.month <= 3:
            break
        time.sleep(0.25)

    df = (pd.concat(pages).drop_duplicates(subset="timestamp")
          .sort_values("timestamp").reset_index(drop=True))
    df.to_parquet(cache)
    print(f"  {symbol} {timeframe}: fetched {len(df)} bars "
          f"({df['timestamp'].iloc[0]:%Y-%m-%d} to "
          f"{df['timestamp'].iloc[-1]:%Y-%m-%d})")
    return df


def build_candidates():
    cands = []
    for f, s in [(20, 50), (30, 50), (20, 100), (50, 200)]:
        cands.append((f"ma {f}/{s} L", ma_crossover,
                      {"fast": f, "slow": s}))
        cands.append((f"ma {f}/{s} LS", ma_crossover,
                      {"fast": f, "slow": s, "allow_short": True}))
    for f, s, r in [(20, 50, 200), (30, 50, 400), (20, 100, 400)]:
        cands.append((f"ma_regime {f}/{s}/r{r}", ma_regime,
                      {"fast": f, "slow": s, "regime": r}))
    for e, x in [(55, 20), (100, 50), (30, 15)]:
        cands.append((f"donchian {e}/{x}", donchian_breakout,
                      {"entry_n": e, "exit_n": x}))
    for b, x in [(30, 55), (25, 50)]:
        cands.append((f"rsi_mr <{b}>{x}", rsi_meanrev,
                      {"buy_below": b, "exit_above": x}))
    for n in [42, 90, 180]:          # in 4h bars: 1 week, 2 weeks, 1 month
        cands.append((f"momentum {n}", momentum_roc, {"n": n}))
    for n, k in [(20, 2.0), (48, 2.5)]:
        cands.append((f"boll_mr {n}/{k}", bollinger_meanrev,
                      {"n": n, "k": k}))
    return cands


def slice_run(df, sig, lo, hi):
    return run_backtest(df.iloc[lo:hi].reset_index(drop=True),
                        sig.iloc[lo:hi].reset_index(drop=True))


def main():
    print("Loading deep history from Bybit (public mainnet data)...")
    frames = {"4h": fetch_bybit_deep("4h"), "1d": fetch_bybit_deep("1d")}

    cands = build_candidates()
    min_trades = {"4h": 40, "1d": 15}   # years of data: demand real samples
    print(f"\n{len(cands)} configs x {len(frames)} timeframes\n")

    rows = []
    for tf, d in frames.items():
        n = len(d)
        i_tr, i_va = int(n * 0.6), int(n * 0.8)
        print(f"  {tf}: TRAIN to {d['timestamp'].iloc[i_tr]:%Y-%m}, "
              f"VAL to {d['timestamp'].iloc[i_va]:%Y-%m}, "
              f"TEST to {d['timestamp'].iloc[-1]:%Y-%m}")
        for name, fn, kw in cands:
            sig = fn(d, **kw)
            r_tr = slice_run(d, sig, 0, i_tr)
            r_va = slice_run(d, sig, i_tr, i_va)
            rows.append({
                "tf": tf, "strategy": name,
                "tr_n": len(r_tr.trades), "tr_exp": r_tr.expectancy,
                "tr_ret%": r_tr.total_return_pct,
                "va_n": len(r_va.trades), "va_exp": r_va.expectancy,
                "va_ret%": r_va.total_return_pct,
                "va_dd%": r_va.max_drawdown_pct,
            })

    res = pd.DataFrame(rows)
    ok = res[
        (res["tr_exp"] > 0) & (res["va_exp"] > 0)
        & (res.apply(lambda r: r["tr_n"] >= min_trades[r["tf"]], axis=1))
        & (res.apply(lambda r: r["va_n"] >= min_trades[r["tf"]] // 3, axis=1))
    ].sort_values("va_exp", ascending=False)

    print("\nTOP 12 BY VALIDATION EXPECTANCY (after full BloFin costs):")
    print(res.sort_values("va_exp", ascending=False).head(12)
          .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    print(f"\nsurvivors (positive train AND val, enough trades): {len(ok)}")

    if ok.empty:
        print("\nVERDICT: NO SURVIVORS on six years either. Test stays sealed.")
        return

    print("\nFINAL TEST — one look, top 3 finalists:")
    out = []
    for _, row in ok.head(3).iterrows():
        d = frames[row["tf"]]
        fn, kw = next((f, k) for nm, f, k in cands if nm == row["strategy"])
        sig = fn(d, **kw)
        r_te = slice_run(d, sig, int(len(d) * 0.8), len(d))
        out.append({"tf": row["tf"], "strategy": row["strategy"],
                    "tr_exp": row["tr_exp"], "va_exp": row["va_exp"],
                    "te_n": len(r_te.trades), "te_exp": r_te.expectancy,
                    "te_ret%": r_te.total_return_pct,
                    "te_dd%": r_te.max_drawdown_pct})
    fin = pd.DataFrame(out)
    print(fin.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    d = frames["1d"]
    r_bh = slice_run(d, buy_and_hold(d), int(len(d) * 0.8), len(d))
    print(f"\nbuy & hold, same test window: {r_bh.total_return_pct:+.2f}% "
          f"(DD {r_bh.max_drawdown_pct:.1f}%)")

    print("\n" + "=" * 64)
    print("VERDICT")
    print("=" * 64)
    good = fin[fin["te_exp"] > 0]
    if good.empty:
        print("Validation winners died on test. Selection was fitting noise.")
    else:
        for _, g in good.iterrows():
            print(f"  CANDIDATE: {g['strategy']} on {g['tf']} — positive on")
            print(f"  ALL THREE windows across six years "
                  f"(test: ${g['te_exp']:+,.2f}/trade, {g['te_n']:.0f} trades,")
            print(f"  {g['te_ret%']:+.1f}%, DD {g['te_dd%']:.1f}%). Next judge:")
            print("  live paper trading on the demo account.")


if __name__ == "__main__":
    main()
