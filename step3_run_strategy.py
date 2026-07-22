"""
step3_run_strategy.py — the first full loop: data -> signal -> costed result.

Run:  python3 step3_run_strategy.py

What it does:
  1. Pulls ~4 months of hourly BTC-USDT history from BloFin (paginated).
  2. Runs the MA crossover through the verified backtest engine.
  3. Shows a few parameter choices side by side, next to buy-and-hold.

A WARNING BEFORE YOU READ ANY OF ITS OUTPUT

Every number this prints is IN-SAMPLE: the strategy is being scored on the
same data we can see while choosing its parameters. In-sample results are
the strategy's audition, not its performance review. Picking whichever row
looks best here and believing it IS the overfitting trap — that is exactly
what Step 4 exists to catch. Today we learn the loop; we defer belief.
"""

import time

import pandas as pd

import config
from backtest import run_backtest
from strategy import buy_and_hold, ma_crossover


def fetch_history(n_bars: int = 3000, cache: bool = True) -> pd.DataFrame:
    """Pull n_bars of hourly history by walking backwards page by page.

    One request caps at ~1440 bars, so for months of data we paginate:
    fetch a page, note its oldest timestamp, ask for bars before that,
    repeat. Pages can overlap at the seam, so we de-duplicate on timestamp.

    Results are cached to disk: reruns get the IDENTICAL dataset instantly.
    Identical matters more than fast — comparing two runs is meaningless if
    the data quietly shifted underneath them between runs.
    """
    ex, sym = config.make_exchange("live")
    tf = config.TIMEFRAME

    import os
    cache_file = f"data_{ex.name}_{sym}_{tf}_{n_bars}.parquet"
    if cache and os.path.exists(cache_file):
        df = pd.read_parquet(cache_file)
        print(f"  (loaded {len(df)} bars from cache: {cache_file})")
        return df

    pages = []
    end_ms = None
    got = 0
    while got < n_bars:
        page = ex.get_candles(sym, tf, limit=min(n_bars - got, 1440),
                              end_ms=end_ms)
        if page.empty:
            break                               # ran out of history
        pages.append(page)
        got += len(page)
        end_ms = int(page["timestamp"].iloc[0].timestamp() * 1000)
        time.sleep(0.3)                         # be polite to the API

    df = (pd.concat(pages)
            .drop_duplicates(subset="timestamp")
            .sort_values("timestamp")
            .reset_index(drop=True))
    if cache:
        df.to_parquet(cache_file)
    return df


def main():
    print("Fetching history from BloFin (a few pages, ~10s)...")
    df = fetch_history(3000)
    days = (df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]).days
    print(f"  {len(df)} hourly bars, {df['timestamp'].iloc[0]:%Y-%m-%d} to "
          f"{df['timestamp'].iloc[-1]:%Y-%m-%d} ({days} days)\n")

    # The market's own result over this window, for context.
    px_change = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100
    print(f"  BTC itself moved {px_change:+.1f}% over this window.\n")

    # ---- candidates ------------------------------------------------------
    # A few classic fast/slow pairs. NOT tuned — chosen before looking at
    # results, which is the only honest way to pick parameters by hand.
    candidates = [(10, 50), (20, 100), (50, 200)]

    rows = []
    results = {}
    for fast, slow in candidates:
        sig = ma_crossover(df, fast, slow)
        r = run_backtest(df, sig)
        results[(fast, slow)] = r
        rows.append({
            "strategy": f"MA {fast}/{slow}",
            "trades": len(r.trades),
            "expectancy": r.expectancy,
            "win rate %": r.win_rate * 100,
            "return %": r.total_return_pct,
            "max DD %": r.max_drawdown_pct,
            "costs $": r.total_fees + r.total_friction + r.total_funding,
        })

    hold = run_backtest(df, buy_and_hold(df))
    rows.append({
        "strategy": "buy & hold",
        "trades": len(hold.trades),
        "expectancy": hold.expectancy,
        "win rate %": hold.win_rate * 100,
        "return %": hold.total_return_pct,
        "max DD %": hold.max_drawdown_pct,
        "costs $": hold.total_fees + hold.total_friction + hold.total_funding,
    })

    table = pd.DataFrame(rows)
    print("ALL RESULTS AFTER COSTS  (in-sample — auditions, not verdicts)")
    print(table.to_string(index=False,
                          float_format=lambda x: f"{x:,.2f}"))

    # Full report for one configuration so you see the whole picture once.
    fast, slow = 20, 100
    print()
    print(results[(fast, slow)].report(
        f"FULL REPORT — MA {fast}/{slow} (in-sample)"))

    print("""
HOW TO READ THIS, ONCE MORE:
  - expectancy is net dollars per trade. Negative expectancy with a decent
    win rate means the losses are bigger than the wins — the classic
    trend-follower profile is the OPPOSITE: low win rate, big avg win.
  - compare every strategy row against buy & hold before admiring it.
  - none of this is believable until it survives data it has never seen.
    That is Step 4, and it exists because of this exact table.""")


if __name__ == "__main__":
    main()
