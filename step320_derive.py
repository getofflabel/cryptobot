"""
step320_derive.py — ROUND 320, PHASE 1: THE DIAL DERIVATION.

Ethereum specialist, 2026-07-25. Morgan's mandate: port SHAPES that have
survived somewhere else on this desk and RE-DERIVE EVERY THRESHOLD from
Ethereum's own price behaviour.

This file computes nothing but numbers. It answers, for each shape:
  - what was the threshold in the market where the shape survived?
  - how OFTEN did that threshold fire there (its selectivity)?
  - what threshold gives Ethereum the SAME selectivity on Ethereum's own
    bars?

Round 190's lesson with a number attached: Bitcoin's 1.5% volatility gate
is open on 96.7% of Solana's bars but only 18-53% of Bitcoin's. The
selectivity WAS the edge. Copying the constant destroyed it. So the
constant is never copied here; the SELECTIVITY is what gets matched, and
the resulting Ethereum number is written down beside the original.

Every derivation below is computed on the TRAIN slice only (first 60% of
Ethereum's history in date order). Nothing here looks at the middle 20%
or the final untouched slice.

No trading, no costs, no verdicts. Just the dials.
"""

import numpy as np
import pandas as pd

from strategy import atr, rsi

pd.set_option("display.width", 200)

ETH_1H = "data_bybit_ETHUSDT_1h_full.parquet"
ETH_4H = "data_bybit_ETHUSDT_4h_full.parquet"
ETH_1D = "data_bybit_ETHUSDT_1d_full.parquet"
BTC_4H = "data_bybit_BTCUSDT_4h_full.parquet"
SPY_1D = "data_tradfi_SPY_1d.parquet"
GLD_1D = "data_tradfi_GLD_1d.parquet"
GCF_1D = "data_tradfi_GCF_1d.parquet"

ROWS = []


def load(path):
    return pd.read_parquet(path).sort_values("timestamp").reset_index(drop=True)


def train_slice(d):
    """First 60% in date order. Every dial below is derived here and only here."""
    return d.iloc[: int(len(d) * 0.6)].reset_index(drop=True)


def rec(shape, dial, source_market, source_value, source_selectivity,
        eth_value, eth_selectivity, note):
    ROWS.append(dict(shape=shape, dial=dial, source_market=source_market,
                     source_value=source_value,
                     source_selectivity_pct=source_selectivity,
                     eth_value=eth_value, eth_selectivity_pct=eth_selectivity,
                     note=note))
    print(f"  {dial}")
    print(f"    {source_market}: {source_value}  -> fires on {source_selectivity:.2f}% of its own bars")
    print(f"    ETHEREUM:        {eth_value}  -> fires on {eth_selectivity:.2f}% of Ethereum's own bars")
    print(f"    {note}")


# ===========================================================================
# SHAPE A — the volatility-gated trend rule (Bitcoin's, the one live edge
# that got STRONGER under honest re-testing in round 150)
# ===========================================================================
def derive_vol_gate():
    print("\n" + "=" * 78)
    print("SHAPE A — volatility-gated trend rule. Source market: Bitcoin, 4h bars.")
    print("=" * 78)
    btc_full = load(BTC_4H)
    btc = train_slice(btc_full)
    eth4 = train_slice(load(ETH_4H))
    eth1 = train_slice(load(ETH_1H))

    btc_atr = (atr(btc, 14) / btc["close"] * 100).dropna()
    btc_sel = float((btc_atr >= 1.5).mean() * 100)
    a_all = (atr(btc_full, 14) / btc_full["close"] * 100).dropna()
    nb = len(btc_full)
    print(f"  Bitcoin's own 1.50% gate, window by window: "
          f"train {float((a_all.iloc[:int(nb*.6)] >= 1.5).mean()*100):.1f}% of bars open, "
          f"middle-20% {float((a_all.iloc[int(nb*.6):int(nb*.8)] >= 1.5).mean()*100):.1f}%, "
          f"final-20% {float((a_all.iloc[int(nb*.8):] >= 1.5).mean()*100):.1f}%.")
    print("  That is not one number. Bitcoin's volatility decayed across its own history, so the "
          "same constant grew steadily pickier over time. Ethereum's gate is matched to the "
          "TRAIN-window figure, which is the window where the rule was chosen.")

    for label, d in (("4h", eth4), ("1h", eth1)):
        a = (atr(d, 14) / d["close"] * 100).dropna()
        # the Ethereum number is the ATR% level that leaves the gate open on
        # the SAME fraction of Ethereum's bars as 1.5% leaves it open on
        # Bitcoin's. quantile of the complement, train window only.
        eth_gate = float(a.quantile(1 - btc_sel / 100))
        eth_sel = float((a >= eth_gate).mean() * 100)
        rec("A vol-gated trend", f"minimum ATR% to allow an entry ({label} bars)",
            "Bitcoin 4h", "1.50%", btc_sel, f"{eth_gate:.2f}%", eth_sel,
            f"Ethereum's own median ATR on {label} bars is {a.median():.3f}% of price; "
            f"Bitcoin's 4h median is {btc_atr.median():.3f}%. Copying 1.50% straight across "
            f"would have left the gate open on {float((a >= 1.5).mean()*100):.1f}% of Ethereum's "
            f"{label} bars instead of {btc_sel:.1f}% — the selectivity would have been thrown away.")
    return btc_sel


# ===========================================================================
# SHAPE B — the donchian channel breakout (gold's one validated edge)
# ===========================================================================
def donchian_state(d, entry_n, exit_ema=20):
    """Gold's validated shape as an actual state machine: go long on a new
    entry_n-bar high, exit when the close falls under the 20-bar exponential
    average. Returns (entries_per_year, fraction of bars holding a position)."""
    hi = d["high"].rolling(entry_n).max().shift(1)
    ema = d["close"].ewm(span=exit_ema, adjust=False).mean()
    ent = (d["close"] > hi).to_numpy()
    ex = (d["close"] < ema).to_numpy()
    pos, entries = 0, 0
    held = np.zeros(len(d), dtype=bool)
    for i in range(len(d)):
        if pos == 0 and ent[i]:
            pos, entries = 1, entries + 1
        elif pos == 1 and ex[i]:
            pos = 0
        held[i] = bool(pos)
    yrs = (d["timestamp"].iloc[-1] - d["timestamp"].iloc[0]).days / 365.25
    return entries / yrs, float(held.mean() * 100)


def derive_donchian():
    print("\n" + "=" * 78)
    print("SHAPE B — donchian channel breakout. Source market: gold, daily bars.")
    print("=" * 78)
    out = {}
    for tag, path in (("GLD", GLD_1D), ("GC=F", GCF_1D)):
        g = train_slice(load(path))
        epy, held = donchian_state(g, 20)
        out[tag] = dict(entries_per_year=epy, held_pct=held)
        print(f"  {tag} daily, 20-bar channel + 20-bar average exit: {epy:.1f} entries a year, "
              f"holding a position on {held:.1f}% of bars")

    gold_epy = float(np.mean([out[t]["entries_per_year"] for t in out]))
    gold_held = float(np.mean([out[t]["held_pct"] for t in out]))

    for label, path in (("1d", ETH_1D), ("4h", ETH_4H), ("1h", ETH_1H)):
        d = train_slice(load(path))
        table = []
        for n in (10, 15, 20, 30, 40, 55, 80, 120, 160, 240):
            epy, held = donchian_state(d, n)
            table.append((n, epy, held))
        best_n, _, best_held = min(table, key=lambda t: abs(t[2] - gold_held))
        best_epy = [t[1] for t in table if t[0] == best_n][0]
        n20 = [t for t in table if t[0] == 20][0]
        print(f"  Ethereum {label}: " + "  ".join(f"N={n}:{held:.0f}%held/{epy:.0f}per-yr"
                                                  for n, epy, held in table))
        rec("B donchian breakout", f"channel length ({label} bars)",
            "gold daily (GLD + GC=F)", "20 bars", gold_held,
            f"{best_n} bars", best_held,
            f"Gold's rule holds a position {gold_held:.1f}% of the time and enters {gold_epy:.1f} "
            f"times a year. Ethereum's {best_n}-bar channel on {label} bars is the length that "
            f"reproduces gold's fraction-of-time-in-the-market ({best_held:.1f}%), and it enters "
            f"{best_epy:.0f} times a year. Copying N=20 onto Ethereum {label} bars would have held "
            f"a position {n20[2]:.1f}% of the time at {n20[1]:.0f} entries a year instead.")


# ===========================================================================
# SHAPE C — the short-lookback RSI dip-buy (the S&P's cleanest edge)
# ===========================================================================
def derive_rsi_dip():
    print("\n" + "=" * 78)
    print("SHAPE C — short-lookback RSI dip-buy. Source market: the S&P 500 tracker, daily bars.")
    print("=" * 78)
    spy = train_slice(load(SPY_1D))
    r2 = rsi(spy["close"], 2).dropna()
    spy_sel = float((r2 < 5).mean() * 100)
    sma200 = spy["close"].rolling(200).mean()
    spy_above = float((spy["close"] > sma200).mean() * 100)
    print(f"  S&P tracker: RSI(2) below 5 on {spy_sel:.2f}% of its own days; "
          f"price above its 200-day average on {spy_above:.1f}% of days")

    for label, path, per_day in (("1d", ETH_1D, 1), ("4h", ETH_4H, 6), ("1h", ETH_1H, 24)):
        d = train_slice(load(path))
        er2 = rsi(d["close"], 2).dropna()
        eth_thresh = float(er2.quantile(spy_sel / 100))
        eth_sel = float((er2 < eth_thresh).mean() * 100)
        naive = float((er2 < 5).mean() * 100)
        rec("C RSI dip-buy", f"RSI(2) entry threshold ({label} bars)",
            "S&P tracker daily", "below 5", spy_sel,
            f"below {eth_thresh:.2f}", eth_sel,
            f"Copying 'below 5' straight onto Ethereum {label} bars would have fired on "
            f"{naive:.2f}% of them, {'more' if naive > spy_sel else 'less'} often than on the "
            f"S&P ({spy_sel:.2f}%) — a {naive/spy_sel if spy_sel else 0:.2f}x change in how "
            f"picky the rule is.")
        # trend filter: the length of average that Ethereum sits above as
        # often as the S&P sits above its own 200-day
        best_len, best_gap, best_frac = None, 1e9, None
        fracs = {}
        for L in (20, 50, 100, 150, 200, 300, 400, 600, 900, 1400, 2000):
            if L >= len(d) * 0.5:
                continue
            sm = d["close"].rolling(L).mean()
            fr = float((d["close"] > sm).mean() * 100)
            fracs[L] = fr
            gap = abs(fr - spy_above)
            if gap < best_gap:
                best_len, best_gap, best_frac = L, gap, fr
        if best_len:
            rec("C RSI dip-buy", f"trend filter length ({label} bars)",
                "S&P tracker daily", "200-day average", spy_above,
                f"{best_len}-bar average", best_frac,
                f"The S&P sits above its 200-day average {spy_above:.1f}% of the time — the rule's "
                f"'only buy dips in an uptrend' precondition is nearly always true there. Ethereum "
                f"sits above its own 200-bar average on {label} bars only {fracs.get(200, float('nan')):.1f}% "
                f"of the time, so the ported filter would be a far harsher gate than the one that was "
                f"validated. {best_len} bars is the length that reproduces the S&P's own permissiveness "
                f"on Ethereum. BOTH are carried into the test as separate cells, chosen on train only.")


# ===========================================================================
# SHAPE D — the flag touch (Bitcoin's live tactical trigger, never yet
# transfer-tested and originally validated on limit orders that wait)
# ===========================================================================
def derive_flag_touch():
    print("\n" + "=" * 78)
    print("SHAPE D — flag touch (dip to the trend line, close back above). Source: Bitcoin 2h bars.")
    print("=" * 78)
    for label, path in (("1h", ETH_1H), ("4h", ETH_4H)):
        d = train_slice(load(path))
        a = (atr(d, 14) / d["close"] * 100).dropna()
        med = float(a.median())
        rec("D flag touch", f"protective stop distance ({label} bars)",
            "Bitcoin 2h", "1.85 x 1.19% median ATR = 2.20%", float("nan"),
            f"1.85 x {med:.3f}% median ATR = {1.85*med:.2f}%", float("nan"),
            f"Bitcoin's 2h median ATR was 1.19% of price when this was set. Ethereum's {label} "
            f"median is {med:.3f}%. The multiplier is the shape; the distance is Ethereum's own. "
            f"NOTE: the real test below replaces even this with a per-trade chart-structure stop "
            f"from exits.py — the ATR figure is recorded only to show how far the ported constant "
            f"would have been from Ethereum's own geometry.")


# ===========================================================================
# SHAPE E — turn of the month (the strongest seasonality on the desk)
# ===========================================================================
def derive_turn_of_month():
    print("\n" + "=" * 78)
    print("SHAPE E — turn of the month. Source market: the S&P 500 tracker, daily bars.")
    print("=" * 78)
    spy = train_slice(load(SPY_1D))
    # the S&P window is in TRADING days; Ethereum trades every calendar day,
    # so the same window is a different fraction of the year in each market.
    spy_days = len(spy)
    spy_months = len(pd.PeriodIndex(spy["timestamp"], freq="M").unique())
    spy_window_frac = spy_months * 7 / spy_days * 100    # 3 before + last + 3 after
    eth = train_slice(load(ETH_1D))
    eth_days = len(eth)
    eth_months = len(pd.PeriodIndex(eth["timestamp"], freq="M").unique())
    eth_window_frac = eth_months * 7 / eth_days * 100
    rec("E turn of the month", "window width",
        "S&P tracker daily", "3 trading days before month end through 3 into the new month",
        spy_window_frac,
        "3 calendar days before month end through 3 into the new month", eth_window_frac,
        f"The S&P's 7-trading-day window covers {spy_window_frac:.1f}% of its bars. Ethereum "
        f"trades every calendar day, so the same 7 CALENDAR days cover only "
        f"{eth_window_frac:.1f}% of Ethereum's bars — a narrower slice of the year. The window "
        f"is therefore also tested widened to the same fraction of the year the S&P version "
        f"covers, so the shape is compared like for like rather than by its label.")


def main():
    derive_vol_gate()
    derive_donchian()
    derive_rsi_dip()
    derive_flag_touch()
    derive_turn_of_month()
    df = pd.DataFrame(ROWS)
    df.to_csv("step320_derivation_table.csv", index=False)
    print(f"\n{len(df)} dials written to step320_derivation_table.csv")


if __name__ == "__main__":
    main()
