"""
step12_round7.py — round 7: a SHORT-SPECIFIC strategy family.

Run:  python3 step12_round7.py

WALLACE'S PRINCIPLE, NOW THE SELECTION RULE
"Shorts don't have to be better than longs, they just have to win."
So the bar here is NOT beating the long champion. A short book qualifies by
having POSITIVE STANDALONE EXPECTANCY (train AND validation, enough trades)
— any winning sleeve compounds the account, whatever its size.

WHY THESE ARE NOT MIRRORED LONGS
MA-cross shorts died 12/12 because they're slow: BTC downmoves are crashes,
and the squeeze arrives before a slow exit reacts. Native short weapons:
  breakdown   : short a fresh N-bar low (momentum, not confirmation-lagged)
  bounce-fade : downtrend + RSI bounce = short the lower high
  cascade     : crowd paying to be long (funding > cap) + price breaking
                down = liquidation fuel
  crash-cont  : a violent down bar tends to be continued briefly — short
                it with a HARD TIME STOP, take the continuation, leave
All exits are fast: recovery highs or hard time stops. Costs: full maker
model, same 60/20/20 windows, test sealed until qualification.
"""

import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from strategy import atr, event_short, rsi

MIN_TRADES = {"1h": 25, "2h": 15, "4h": 10}


def hi_n(d, n):
    return d["high"].rolling(n).max().shift(1)


def lo_n(d, n):
    return d["low"].rolling(n).min().shift(1)


def build(d, f_bps):
    """(tag, enter, exit, max_hold) candidates for one timeframe frame."""
    sma20 = d["close"].rolling(20).mean()
    sma100 = d["close"].rolling(100).mean()
    downtrend = sma20 < sma100
    r = rsi(d["close"], 14)
    atr_pct = atr(d, 14) / d["close"] * 100
    lively = atr_pct >= 1.0
    bar_ret = d["close"].pct_change() * 100

    return [
        ("breakdown 55/10", d["close"] < lo_n(d, 55),
         d["close"] > hi_n(d, 10), 0),
        ("breakdown 20/10 lively", (d["close"] < lo_n(d, 20)) & lively,
         d["close"] > hi_n(d, 10), 0),
        ("bounce-fade rsi55", downtrend & (r > 55),
         (r < 35) | ~downtrend, 30),
        ("cascade f>1.5", (f_bps > 1.5) & (d["close"] < lo_n(d, 20)),
         d["close"] > hi_n(d, 10), 30),
        ("crash-cont 2%/6", (bar_ret < -2.0) & lively,
         pd.Series(False, index=d.index), 6),
        ("crash-cont 3%/12", (bar_ret < -3.0) & lively,
         pd.Series(False, index=d.index), 12),
    ]


def score(df, sig):
    n = len(df)
    i_tr, i_va = int(n * 0.6), int(n * 0.8)

    def run(lo, hi):
        return run_backtest(df.iloc[lo:hi].reset_index(drop=True),
                            sig.iloc[lo:hi].reset_index(drop=True),
                            execution="maker")
    return run(0, i_tr), run(i_tr, i_va), run(i_va, n)


def main():
    funding = fetch_funding_history()
    frames = {tf: fetch_bybit_deep(tf, "BTCUSDT") for tf in ["1h", "2h", "4h"]}

    rows, keep = [], {}
    for tf, d in frames.items():
        f_bps = align_funding(d, funding)
        for tag, enter, exit_, hold in build(d, f_bps):
            sig = event_short(d, enter, exit_, hold)
            runs = score(d, sig)
            r_tr, r_va, _ = runs
            full = f"{tf} {tag}"
            keep[full] = runs
            rows.append({
                "config": full,
                "tr_n": len(r_tr.trades), "tr_exp": r_tr.expectancy,
                "tr_ret%": r_tr.total_return_pct,
                "va_n": len(r_va.trades), "va_exp": r_va.expectancy,
                "va_ret%": r_va.total_return_pct,
                "va_dd%": r_va.max_drawdown_pct,
            })

    res = pd.DataFrame(rows)
    print("\nSHORT-ONLY BOOKS (train + validation, maker exec, full costs):")
    print(res.sort_values("va_exp", ascending=False)
          .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    # Wallace's rule: they just have to WIN. Positive on both windows.
    qual = res[(res["tr_exp"] > 0) & (res["va_exp"] > 0)
               & res.apply(lambda r: r["tr_n"] >=
                           MIN_TRADES[r["config"].split()[0]], axis=1)
               & res.apply(lambda r: r["va_n"] >=
                           MIN_TRADES[r["config"].split()[0]] // 3, axis=1)]
    qual = qual.sort_values("va_exp", ascending=False)
    print(f"\nqualified short books (win on BOTH windows): "
          f"{list(qual['config']) or 'NONE'}")

    if qual.empty:
        print("\n" + "=" * 70)
        print("ROUND 7 vs ROUND 6 — the before/after")
        print("=" * 70)
        print("  BEFORE: champion test $+356.87/trade, +28.5%, DD -12.9%")
        print("  AFTER : unchanged. No short family earned a sleeve; the")
        print("          test window stays sealed for future short research.")
        return

    print("\nFINAL TEST — qualified short books, one look:")
    out = []
    for cfg in qual["config"].head(3):
        r_te = keep[cfg][2]
        out.append({"config": cfg, "te_n": len(r_te.trades),
                    "te_exp": r_te.expectancy,
                    "te_ret%": r_te.total_return_pct,
                    "te_dd%": r_te.max_drawdown_pct,
                    "te_win%": r_te.win_rate * 100})
    t = pd.DataFrame(out)
    print(t.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    print("\n" + "=" * 70)
    print("ROUND 7 vs ROUND 6 — the before/after")
    print("=" * 70)
    print("  BEFORE: long champion only — test +28.5%, DD -12.9%")
    winners = t[t["te_exp"] > 0]
    if winners.empty:
        print("  AFTER : unchanged — short books died on the test window.")
        print("          Sleeve denied; ledger stays long-only.")
    else:
        for _, w in winners.iterrows():
            print(f"  AFTER : + short sleeve {w['config']} — standalone test "
                  f"${w['te_exp']:+,.2f}/trade, {w['te_ret%']:+.1f}%, "
                  f"DD {w['te_dd%']:.1f}%")
        print("          A winning short book ADDS to the snowball per")
        print("          Wallace's rule: it doesn't have to beat the longs.")


if __name__ == "__main__":
    main()
