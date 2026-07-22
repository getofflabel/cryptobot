"""
step11_round6.py — round 6: sentiment via funding rates ("qualitative,
quantified").

Run:  python3 step11_round6.py

THE IDEA
Perpetual funding is a direct reading of crowd positioning. Strongly
positive funding = longs so crowded they pay to stay in = euphoria, which
historically precedes poor forward returns. Strongly negative = crowd
short = squeeze fuel. This is "market mood" — the qualitative thing —
except it comes as a number with six years of history, so it can face the
same gauntlet as everything else instead of being a vibe we trust on faith.

NO-LOOKAHEAD NOTE
We align each 4h bar with the most recent SETTLED funding rate (paid at
00/08/16 UTC, public the moment it settles). A bar never sees a funding
value that wasn't already published.

VARIANTS THIS ROUND (all entry-door filters on the champion; positions,
once open, are managed by the trend exactly as before)
  euphoria cap  : block entries while funding > +X bps/8h  (crowd max long)
  squeeze boost : ALSO allow entries when trend is up and funding is deeply
                  negative even if ATR gate says the market is quiet
                  (crowd short + rising price = fuel)

CHAMPION TO BEAT (round 5): vol-gated MA 20/100 4h L-only, maker exec —
validation +57.7% | test $+356.87/trade, +28.5%, DD -12.9%
"""

import os
import time

import numpy as np
import pandas as pd

from backtest import run_backtest
from exchange import BybitExchange
from step7_deep_search import fetch_bybit_deep
from strategy import atr, ma_crossover, vol_gated_ma

CHAMP_KW = {"fast": 20, "slow": 100, "min_atr_pct": 1.5}


def fetch_funding_history(symbol: str = "BTCUSDT") -> pd.DataFrame:
    """All funding settlements for a symbol from Bybit, cached. ~3/day."""
    cache = f"data_bybit_{symbol}_funding.parquet"
    if os.path.exists(cache):
        df = pd.read_parquet(cache)
        print(f"  {symbol} funding: {len(df)} settlements from cache")
        return df

    ex = BybitExchange(env="mainnet")
    rows, end = [], None
    while True:
        params = {"category": "linear", "symbol": symbol, "limit": 200}
        if end:
            params["endTime"] = end
        result = ex._get("/v5/market/funding/history", params)
        batch = result.get("list", [])
        if not batch:
            break
        for r in batch:
            rows.append({
                "timestamp": pd.Timestamp(int(r["fundingRateTimestamp"]),
                                          unit="ms", tz="UTC"),
                "funding_bps": float(r["fundingRate"]) * 10_000,
            })
        oldest = min(int(r["fundingRateTimestamp"]) for r in batch)
        if end is not None and oldest >= end:
            break
        end = oldest - 1
        if pd.Timestamp(oldest, unit="ms", tz="UTC").year <= 2020 and \
           pd.Timestamp(oldest, unit="ms", tz="UTC").month <= 3:
            break
        time.sleep(0.15)

    df = (pd.DataFrame(rows).drop_duplicates(subset="timestamp")
          .sort_values("timestamp").reset_index(drop=True))
    df.to_parquet(cache)
    print(f"  funding: fetched {len(df)} settlements "
          f"({df['timestamp'].iloc[0]:%Y-%m-%d} to "
          f"{df['timestamp'].iloc[-1]:%Y-%m-%d})")
    return df


def align_funding(candles: pd.DataFrame, funding: pd.DataFrame) -> pd.Series:
    """Most recent SETTLED funding rate as of each bar's close. merge_asof
    is exactly this: for each bar, the last funding row at or before it."""
    bars = candles[["timestamp"]].copy()
    merged = pd.merge_asof(bars, funding, on="timestamp",
                           direction="backward")
    return merged["funding_bps"]


def score(df, sig):
    n = len(df)
    i_tr, i_va = int(n * 0.6), int(n * 0.8)

    def run(lo, hi):
        return run_backtest(df.iloc[lo:hi].reset_index(drop=True),
                            sig.iloc[lo:hi].reset_index(drop=True),
                            execution="maker")
    return run(0, i_tr), run(i_tr, i_va), run(i_va, n)


def row(tag, runs, with_test=False):
    r_tr, r_va, r_te = runs
    d = {"config": tag, "tr_ret%": r_tr.total_return_pct,
         "va_n": len(r_va.trades), "va_exp": r_va.expectancy,
         "va_ret%": r_va.total_return_pct, "va_dd%": r_va.max_drawdown_pct}
    if with_test:
        d.update({"te_n": len(r_te.trades), "te_exp": r_te.expectancy,
                  "te_ret%": r_te.total_return_pct,
                  "te_dd%": r_te.max_drawdown_pct})
    return d


def main():
    print("Loading data...")
    btc = fetch_bybit_deep("4h", "BTCUSDT")
    funding = fetch_funding_history()
    f_bps = align_funding(btc, funding)

    print(f"\n  funding distribution (bps/8h): "
          f"p10 {f_bps.quantile(.1):+.2f}  median {f_bps.median():+.2f}  "
          f"p90 {f_bps.quantile(.9):+.2f}  p99 {f_bps.quantile(.99):+.2f}")

    champ = score(btc, vol_gated_ma(btc, **CHAMP_KW))

    # ---- euphoria caps ---------------------------------------------------
    print("\n[1] EUPHORIA CAP — block entries when the crowd is max long")
    rows = [row("champion (no sentiment)", champ)]
    results = {}
    for cap in [1.0, 2.0, 3.0]:
        filt = f_bps <= cap
        sig = vol_gated_ma(btc, **CHAMP_KW, entry_filter=filt)
        runs = score(btc, sig)
        results[f"cap {cap:.0f}bp"] = runs
        rows.append(row(f"cap {cap:.0f}bp", runs))

    # ---- squeeze boost ---------------------------------------------------
    # trend up + deeply negative funding => enter even if ATR gate is quiet.
    # Implemented as: the champion signal OR the squeeze condition.
    print("    ...plus the squeeze-boost variant")
    base = ma_crossover(btc, 20, 100)
    for thresh in [-1.0, -2.0]:
        squeeze = (base == 1) & (f_bps <= thresh)
        champ_sig = vol_gated_ma(btc, **CHAMP_KW)
        boosted = champ_sig.copy()
        boosted[(boosted == 0) & squeeze] = 1.0
        runs = score(btc, boosted)
        results[f"squeeze {thresh:.0f}bp"] = runs
        rows.append(row(f"squeeze {thresh:.0f}bp", runs))

    print(pd.DataFrame(rows).to_string(index=False,
                                       float_format=lambda x: f"{x:,.2f}"))

    # ---- selection + one test look --------------------------------------
    champ_va = champ[1].total_return_pct
    qualified = [t for t, r in results.items()
                 if r[0].expectancy > 0 and len(r[1].trades) >= 5
                 and r[1].total_return_pct > champ_va]
    print(f"\nbeat the champion's validation (+{champ_va:.1f}%): "
          f"{qualified or 'NONE'}")

    finals = [row("champion (r5 baseline)", champ, with_test=True)]
    for t in qualified[:2]:
        finals.append(row(t, results[t], with_test=True))
    print("\nFINAL TEST:")
    print(pd.DataFrame(finals).to_string(index=False,
                                         float_format=lambda x: f"{x:,.2f}"))

    print("\n" + "=" * 70)
    print("ROUND 6 vs ROUND 5 — the before/after")
    print("=" * 70)
    b = champ[2]
    print(f"  BEFORE: test ${b.expectancy:+,.2f}/trade, "
          f"{b.total_return_pct:+.1f}%, DD {b.max_drawdown_pct:.1f}%")
    winner = None
    for f in finals[1:]:
        if f["te_ret%"] > b.total_return_pct and f["te_exp"] > 0:
            print(f"  AFTER : {f['config']} — test ${f['te_exp']:+,.2f}/trade, "
                  f"{f['te_ret%']:+.1f}%, DD {f['te_dd%']:.1f}%  <- NEW CHAMPION")
            winner = f["config"]
    if not winner:
        print("  AFTER : sentiment variants did not beat the champion on test.")
        print("          Belt retained; ledger unchanged.")


if __name__ == "__main__":
    main()
