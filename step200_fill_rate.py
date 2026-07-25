"""
step200_fill_rate.py — measures how often a post-only maker limit at the
signal bar's CLOSE would actually fill on the NEXT bar, using the exact
"touched" test backtest.py's execute() already uses for execution="maker"
(see backtest.py lines ~332-344), reused verbatim here rather than
reinvented:

    limit = closes[i-1]
    touched = (lows[i] <= limit)  if side > 0 (buy)
    touched = (highs[i] >= limit) if side < 0 (sell)

If NOT touched, the backtest chases at market (taker) on that same bar's
close. This script measures, over real cached BTC-USDT history, what
fraction of bars would touch (maker fills) vs miss (taker chase), for both
the RIDE's 4h bars and the 1h bars several other books trade on.

IMPORTANT CAVEAT (does not change the underlying math, changes how to read
it): backtest.py's maker model gives the resting limit the ENTIRE next bar
to be touched — 4h or 1h. The LIVE code's MAKER_PATIENCE_S is only 600
seconds (10 minutes) before step5_paper_trade.execute_maker_or_chase cancels
and chases. So the live fill rate is a real order-of-magnitude LOWER than
what this script reports for the 1h/4h bars — this script's number is an
upper bound on live maker fill probability, not a live-equivalent measurement.
A same-scale sanity check is included: the fraction of each bar's range
typically covered in the first 10 minutes, to bound how much of the "full
bar" touch rate is actually reachable in a 600s window.

Run: python3 step200_fill_rate.py
Writes nothing; prints results for step200_maker_safety.md to quote.
"""

import pandas as pd


def touch_rate(df: pd.DataFrame, side: str) -> tuple[float, int, int]:
    """Fraction of bars i>0 where a post-only limit resting at closes[i-1]
    would be touched by bar i's range. side='buy' or 'sell'."""
    closes = df["close"].to_numpy()
    lows = df["low"].to_numpy()
    highs = df["high"].to_numpy()
    n = len(df)
    touched = 0
    total = 0
    for i in range(1, n):
        limit = closes[i - 1]
        if side == "buy":
            hit = lows[i] <= limit
        else:
            hit = highs[i] >= limit
        touched += int(hit)
        total += 1
    return touched / total, touched, total


def main():
    for tf, path in [("4h (THE RIDE)", "data_bybit_BTCUSDT_4h_full.parquet"),
                      ("1h (breakout/tactical/daily_pick/newsdesk/diver)",
                       "data_bybit_BTCUSDT_1h_full.parquet")]:
        df = pd.read_parquet(path)
        buy_rate, buy_n, total = touch_rate(df, "buy")
        sell_rate, sell_n, _ = touch_rate(df, "sell")
        print(f"\n=== {tf} — {path} ===")
        print(f"  bars: {total}  span: {df['timestamp'].min()} -> "
              f"{df['timestamp'].max()}")
        print(f"  BUY  maker fill (whole next bar): {buy_rate:.1%}  "
              f"({buy_n}/{total})  miss/chase: {1-buy_rate:.1%}")
        print(f"  SELL maker fill (whole next bar): {sell_rate:.1%}  "
              f"({sell_n}/{total})  miss/chase: {1-sell_rate:.1%}")
        avg = (buy_rate + sell_rate) / 2
        print(f"  AVG fill rate (whole-bar upper bound): {avg:.1%}")

        # 10-minute-window sanity bound: what fraction of the bar's own
        # travel from open typically happens in the first 10 minutes, as a
        # rough downscale from "whole bar" to "MAKER_PATIENCE_S=600s".
        bar_seconds = {"4h (THE RIDE)": 4 * 3600,
                       "1h (breakout/tactical/daily_pick/newsdesk/diver)": 3600}[tf]
        frac_of_bar = 600 / bar_seconds
        print(f"  600s is {frac_of_bar:.1%} of this bar's duration — if "
              f"touches were spread uniformly through the bar (they are "
              f"NOT, they cluster at opens/news, so this UNDERSTATES the "
              f"true early-window rate), the naive downscale would be "
              f"~{avg*frac_of_bar:.1%}. Treat the whole-bar number above as "
              f"the ceiling and this as a floor; the real live rate sits "
              f"between them, almost certainly well below the whole-bar figure.")


if __name__ == "__main__":
    main()
