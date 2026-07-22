"""
step1_market_check.py — prove we can read the market before we do anything else.

Run it:
    python3 step1_market_check.py

It reads whatever venue config.py points at, so it works unchanged on BloFin,
Bybit, or anything you add later.

What it checks:
    1. Can we reach the live venue and get a price?
    2. Can we reach the demo venue? (we need it for Step 5)
    3. Can we pull historical candles we could actually backtest on?
    4. Is that data CLEAN?
    5. How far back does history go?

Point 4 is the one people skip, and it is the one that silently ruins
backtests. A strategy tested on bad data produces a confident, meaningless
number. We check the data before we ever trust a result from it.
"""

import config
from exchange import TIMEFRAME_MS


def check_ticker(exchange, symbol):
    """Fetch one live quote and report the spread."""
    t = exchange.get_ticker(symbol)
    print(f"  {exchange.name:<15} last={t.last:>10,.1f}  bid={t.bid:>10,.1f}  "
          f"ask={t.ask:>10,.1f}  spread={t.spread:>6.2f} ({t.spread_bps:.3f} bps)")
    return t


def audit_candles(df, timeframe):
    """Look for the data problems that quietly break backtests.

    Returns a list of human-readable problems. Empty list means clean.
    """
    problems = []
    if df.empty:
        return ["no candles returned at all"]

    # 1. Zero-volume bars. Nothing traded, so the "price" is fictional.
    #    You cannot fill an order against a bar nobody traded in.
    zero_vol = int((df["volume"] == 0).sum())
    if zero_vol:
        problems.append(f"{zero_vol} zero-volume bars "
                        f"({zero_vol / len(df) * 100:.1f}% of data)")

    # 2. Impossible OHLC. high must be the highest value, low the lowest.
    #    If this fails the feed is corrupt and nothing downstream is safe.
    bad = int((df["high"] < df[["open", "close"]].max(axis=1)).sum())
    bad += int((df["low"] > df[["open", "close"]].min(axis=1)).sum())
    if bad:
        problems.append(f"{bad} bars with impossible OHLC values")

    # 3. Time gaps. A missing hour means the venue was down or nothing traded.
    #    Your strategy would "hold through" a period it never actually saw.
    expected_ms = TIMEFRAME_MS[timeframe]
    gaps = df["timestamp"].diff().dropna()
    n_gaps = int((gaps.dt.total_seconds() * 1000 > expected_ms).sum())
    if n_gaps:
        problems.append(f"{n_gaps} time gaps (largest {gaps.max()})")

    # 4. Duplicate timestamps would double-count a bar.
    dupes = int(df["timestamp"].duplicated().sum())
    if dupes:
        problems.append(f"{dupes} duplicate timestamps")

    return problems


def check_candles(exchange, symbol, timeframe, limit=500):
    df = exchange.get_candles(symbol, timeframe, limit)

    print(f"\n  {exchange.name} {symbol} {timeframe}: {len(df)} closed bars")
    if df.empty:
        print("    !! nothing returned")
        return df

    first, last = df["timestamp"].iloc[0], df["timestamp"].iloc[-1]
    print(f"    from {first:%Y-%m-%d %H:%M} UTC  to  {last:%Y-%m-%d %H:%M} UTC")
    print(f"    span: {(last - first).days} days")
    print(f"    price range: {df['low'].min():,.1f} to {df['high'].max():,.1f}")

    problems = audit_candles(df, timeframe)
    if problems:
        print("    DATA WARNINGS:")
        for p in problems:
            print(f"      - {p}")
    else:
        print("    data quality: clean (no gaps, dupes, or zero-volume bars)")
    return df


def main():
    tf = config.TIMEFRAME
    live, symbol = config.make_exchange("live")
    demo, _ = config.make_exchange("demo")

    print("=" * 78)
    print(f"STEP 1: CAN WE READ THE MARKET?   [venue: {config.EXCHANGE}]")
    print("=" * 78)

    # ---- 1. live quotes ---------------------------------------------------
    print(f"\n[1] LIVE QUOTE for {symbol}")
    t_live = check_ticker(live, symbol)
    try:
        t_demo = check_ticker(demo, symbol)
        drift_bps = abs(t_live.last - t_demo.last) / t_live.last * 10_000
        print(f"\n  demo differs from real market by {drift_bps:,.1f} bps "
              f"(it has its own order book)")
    except Exception as e:
        print(f"  demo unreachable: {str(e)[:110]}")

    # ---- 2. historical data ----------------------------------------------
    print(f"\n[2] HISTORICAL DATA ({tf}, what we will backtest on)")
    df = check_candles(live, symbol, tf, limit=500)
    if df.empty:
        print("\nFAILED. Do not continue to Step 2 until this passes.")
        return

    # ---- 3. how far back can we go? --------------------------------------
    print(f"\n[3] HISTORY DEPTH — enough for out-of-sample testing?")
    oldest_ms = int(df["timestamp"].iloc[0].timestamp() * 1000)
    try:
        deep = live.get_candles(symbol, tf, limit=500, end_ms=oldest_ms)
        if not deep.empty and deep["timestamp"].iloc[0] < df["timestamp"].iloc[0]:
            print(f"  paginating backwards works: reached "
                  f"{deep['timestamp'].iloc[0]:%Y-%m-%d}")
            print(f"  we can keep walking back to build a multi-month dataset,")
            print(f"  which is what Step 4 needs to split tuning from validation.")
        else:
            print("  pagination returned nothing older — worth investigating "
                  "before Step 4.")
    except Exception as e:
        print(f"  pagination failed: {str(e)[:110]}")

    # ---- 4. contract specs -----------------------------------------------
    print(f"\n[4] CONTRACT SPECS (needed to place real orders in Step 5)")
    try:
        spec = live.get_instrument(symbol)
        interesting = ["tickSize", "minSize", "lotSize", "contractValue",
                       "maxLeverage", "instId", "instType"]
        for k in interesting:
            if k in spec:
                print(f"  {k:<16} {spec[k]}")
    except Exception as e:
        print(f"  could not fetch specs: {str(e)[:110]}")

    # ---- verdict ----------------------------------------------------------
    print("\n" + "=" * 78)
    print("VERDICT")
    print("=" * 78)
    print(f"Market reads work on {config.EXCHANGE}. You can see the market.")
    print()
    print("Setup for this project:")
    print(f"  - BACKTEST on {config.EXCHANGE} live data  (real prices, no API key)")
    print(f"  - PAPER TRADE on {config.EXCHANGE} demo    (fake money, real mechanics)")
    print()
    print("Costs you will be charged starting in Step 2:")
    taker = config.fee_bps()
    print(f"  taker fee:  {taker} bps per side ({taker / 100:.3f}%)")
    print(f"  maker fee:  {config.fee_bps(maker=True)} bps per side")
    print(f"  spread now: {t_live.spread_bps:.3f} bps")
    print()
    ratio = taker / max(t_live.spread_bps, 0.001)
    print(f"The taker fee is ~{ratio:,.0f}x the current spread. Fees, not spread,")
    print("are what will eat your edge. Step 2 charges you for both.")


if __name__ == "__main__":
    main()
