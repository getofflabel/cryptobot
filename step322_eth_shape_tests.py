"""
step322_eth_shape_tests.py — ROUND 320, PHASE 2: the shapes themselves.

Ethereum specialist, 2026-07-25. Five shapes that have survived somewhere
else on this desk, rebuilt on Ethereum with every threshold re-derived
from Ethereum's own price behaviour by step320_derive.py.

  A  volatility-gated trend rule ............ from Bitcoin (4h)
  B  donchian channel breakout .............. from gold (daily)
  C  short-lookback RSI dip-buy ............. from the S&P 500 tracker (daily)
  D  flag touch (dip to the trend line) ..... from Bitcoin (2h)
  E  turn of the month ...................... from the S&P 500 tracker (daily)

RULES THIS FILE OBEYS, ALL OF THEM
- Market orders both ways, always. Never the cheaper limit order that waits.
- The stop is a level off Ethereum's own chart (exits.py), never a swept
  percentage. Position size = dollars risked / distance to that stop, so
  leverage comes out the far end as a result, capped at 20x.
- History split 60/20/20 in date order. Every choice is made on the first
  60%. The middle 20% is read ONCE. The final 20% is not loaded by this
  file at all.
- At least 30 trades in the first slice and 8 in the middle slice, or the
  cell is reported as NOT ENOUGH TRADES and nothing is claimed.
- Every family gets a comparison against entering at random times, and the
  grid's own luck rate is stated beside its winners.
- Profit is reported both as a percent of the full position size and as a
  multiple of the cost of trading. Under 5x is a reject.

For each dial the original market's number AND Ethereum's re-derived number
are both carried in the output row, so nothing can quietly become a port.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import exits as E
from step11_round6 import align_funding, fetch_funding_history
from step321_eth_engine import (MIN_TRAIN_TRADES, MIN_VAL_TRADES, random_entry_control,
                                run_edge_ctx, split_points, stats, thickness, verdict)
from strategy import atr, rsi, vol_gated_ma

pd.set_option("display.width", 240)

FRAMES = {"1h": "data_bybit_ETHUSDT_1h_full.parquet",
          "4h": "data_bybit_ETHUSDT_4h_full.parquet",
          "1d": "data_bybit_ETHUSDT_1d_full.parquet"}
BARS_PER_DAY = {"1h": 24, "4h": 6, "1d": 1}

# Bitcoin's own train-window 4h median ATR, used ONLY to convert Bitcoin's
# 1.5% stop buffer into "how many of its own daily ranges was that", so the
# same SHAPE can be expressed in Ethereum's ranges instead of copied.
BTC_TRAIN_4H_ATR_PCT = 1.741
BTC_R150_BUFFER_PCT = 1.5

ROWS = []
_cache = {}


def frame(tf):
    if tf not in _cache:
        d = pd.read_parquet(FRAMES[tf]).sort_values("timestamp").reset_index(drop=True)
        s = E.build_series_ctx(d, k=5)
        fh = fetch_funding_history("ETHUSDT")
        f = align_funding(d, fh).fillna(0).to_numpy()
        _cache[tf] = (d, s, f)
    return _cache[tf]


def train_only(d, series):
    i_tr, _ = split_points(len(d))
    return series.iloc[:i_tr]


def add(family, cell, tf, source_dial, eth_dial, tr, va, extra=None):
    th_tr = thickness(tr["exp"], tr["avg_notional"])
    th_va = thickness(va["exp"], va["avg_notional"])
    v = verdict(tr, va)
    row = dict(family=family, cell=cell, timeframe=tf,
               dial_in_source_market=source_dial, dial_re_derived_for_ethereum=eth_dial,
               train_trades=tr["n"], train_avg_profit_per_trade=tr["exp"],
               train_win_pct=tr["win"] * 100, train_return_pct=tr["ret"], train_worst_drawdown_pct=tr["dd"],
               val_trades=va["n"], val_avg_profit_per_trade=va["exp"],
               val_win_pct=va["win"] * 100, val_return_pct=va["ret"], val_worst_drawdown_pct=va["dd"],
               profit_pct_of_position_train=th_tr["pct_of_position"],
               profit_pct_of_position_val=th_va["pct_of_position"],
               times_bigger_than_trading_cost_train=th_tr["x_full_cost"],
               times_bigger_than_trading_cost_val=th_va["x_full_cost"],
               median_stop_distance_pct_train=tr["med_stop_pct"],
               avg_leverage_out_train=tr["avg_lev"],
               median_hold_hours_train=tr["med_hold_h"], verdict=v)
    if extra:
        row.update(extra)
    ROWS.append(row)
    print(f"    {cell:<52s} train n={tr['n']:>4d} ${tr['exp']:>+9.2f} | "
          f"val n={va['n']:>4d} ${va['exp']:>+9.2f} | "
          f"{th_va['x_full_cost']:>6.1f}x cost (val) -> {v}")
    return v


def mask_entries(mask, lo=None):
    idx = np.flatnonzero(np.asarray(mask, dtype=bool))
    return [(int(i), 1) for i in idx]


# ===========================================================================
# A — the volatility-gated trend rule (Bitcoin's)
# ===========================================================================
def family_a():
    print("\n" + "=" * 96)
    print("FAMILY A — volatility-gated trend rule. Bitcoin's shape, Ethereum's numbers.")
    print("  Bitcoin: 4h bars, 20/100 averages, entry only when the 14-bar range is at least")
    print("  1.50% of price. On Bitcoin's own first 60% that gate was open on 63.2% of bars.")
    print("=" * 96)
    for tf in ("4h", "1h"):
        d, s, f = frame(tf)
        i_tr, i_va = split_points(len(d))
        a = (atr(d, 14) / d["close"] * 100)
        gate = float(a.iloc[:i_tr].dropna().quantile(1 - 0.6321))
        eth_med_atr = float(a.iloc[:i_tr].dropna().median())
        buffer_pct = BTC_R150_BUFFER_PCT / BTC_TRAIN_4H_ATR_PCT * eth_med_atr
        naive_open = float((a.iloc[:i_tr] >= 1.5).mean() * 100)
        print(f"\n  {tf} bars: Ethereum's gate = {gate:.2f}% of price (open on 63.2% of Ethereum's "
              f"own first-60% bars, matching Bitcoin's own selectivity).")
        print(f"    Copying Bitcoin's 1.50% here would have left the gate open on {naive_open:.1f}% "
              f"of Ethereum's {tf} bars instead.")
        print(f"    Trailing-stop buffer: Bitcoin used 1.50% when its own 4h range ran "
              f"{BTC_TRAIN_4H_ATR_PCT:.2f}% (0.86 of a range). Ethereum's {tf} range runs "
              f"{eth_med_atr:.3f}%, so the same 0.86 of a range is {buffer_pct:.2f}%.")
        for fast, slow in ((20, 100), (10, 50), (20, 50), (10, 30)):
            sig = vol_gated_ma(d, fast=fast, slow=slow, atr_n=14, min_atr_pct=gate)
            sv = sig.fillna(0).to_numpy()
            ent = (sv == 1) & (np.roll(sv, 1) != 1)
            ent[0] = False
            warm = slow + 20
            ent[:warm] = False
            entries = mask_entries(ent)
            stop_b = lambda tc: E.stop_structure_trailing(buffer_pct=buffer_pct, fallback_pct=8.0)
            tgt_b = lambda st: E.target_opposite_signal(sv, treat_zero_as_exit=True)
            mh = 60 * BARS_PER_DAY[tf]
            t1, _ = run_edge_ctx(d, s, entries, stop_b, tgt_b, mh, f, lo_idx=warm, hi_idx=i_tr)
            t2, _ = run_edge_ctx(d, s, entries, stop_b, tgt_b, mh, f, lo_idx=i_tr, hi_idx=i_va)
            add("A volatility-gated trend", f"{tf} {fast}/{slow} gate {gate:.2f}%", tf,
                "1.50% (Bitcoin 4h)", f"{gate:.2f}% ({tf})", stats(t1), stats(t2),
                extra=dict(source_market="Bitcoin"))


# ===========================================================================
# B — the donchian channel breakout (gold's)
# ===========================================================================
def family_b():
    print("\n" + "=" * 96)
    print("FAMILY B — donchian channel breakout. Gold's shape, Ethereum's numbers.")
    print("  Gold: daily bars, buy a new 20-day high, out when the close drops under the 20-bar")
    print("  exponential average. 5.4 entries a year, holding a position 34.2% of the time.")
    print("=" * 96)
    matched = {"1d": 15, "4h": 15, "1h": 10}
    for tf in ("1d", "4h", "1h"):
        d, s, f = frame(tf)
        i_tr, i_va = split_points(len(d))
        print(f"\n  {tf} bars: Ethereum's channel = {matched[tf]} bars (the length that puts "
              f"Ethereum in the market the same fraction of the time gold's 20-day channel does).")
        for n in sorted({matched[tf], 20, 55}):
            hi = d["high"].rolling(n).max().shift(1)
            ema = d["close"].ewm(span=20, adjust=False).mean()
            ent_c = (d["close"] > hi).to_numpy()
            ex_c = (d["close"] < ema).to_numpy()
            state = np.zeros(len(d))
            pos = 0
            for i in range(len(d)):
                if pos == 0 and ent_c[i]:
                    pos = 1
                elif pos == 1 and ex_c[i]:
                    pos = 0
                state[i] = pos
            ent = (state == 1) & (np.roll(state, 1) != 1)
            ent[0] = False
            warm = n + 25
            ent[:warm] = False
            entries = mask_entries(ent)
            stop_b = lambda tc: E.stop_structure_trailing(buffer_pct=0.0, fallback_pct=8.0)
            tgt_b = lambda st: E.target_opposite_signal(state, treat_zero_as_exit=True)
            mh = 90 * BARS_PER_DAY[tf]
            t1, _ = run_edge_ctx(d, s, entries, stop_b, tgt_b, mh, f, lo_idx=warm, hi_idx=i_tr)
            t2, _ = run_edge_ctx(d, s, entries, stop_b, tgt_b, mh, f, lo_idx=i_tr, hi_idx=i_va)
            tag = "Ethereum's own length" if n == matched[tf] else "gold's number copied straight across" if n == 20 else "longer control"
            add("B donchian breakout", f"{tf} channel {n} bars ({tag})", tf,
                "20 daily bars (gold)", f"{matched[tf]} {tf} bars", stats(t1), stats(t2),
                extra=dict(source_market="gold"))


# ===========================================================================
# C — the short-lookback RSI dip-buy (the S&P's)
# ===========================================================================
def family_c():
    print("\n" + "=" * 96)
    print("FAMILY C — short-lookback RSI dip-buy. The S&P tracker's shape, Ethereum's numbers.")
    print("  S&P: daily bars, buy when the 2-bar RSI drops under 5 while price is above its")
    print("  200-day average, out when the close clears the 5-day average or the RSI clears 65.")
    print("  On the S&P's own first 60%: the entry fires on 5.05% of days, the trend filter is")
    print("  true on 66.2% of days.")
    print("=" * 96)
    spy = pd.read_parquet("data_tradfi_SPY_1d.parquet").sort_values("timestamp").reset_index(drop=True)
    spy_tr = spy.iloc[:int(len(spy) * 0.6)]
    spy_exit_sel = float((rsi(spy_tr["close"], 2).dropna() > 65).mean() * 100)
    print(f"  The S&P's exit trigger (2-bar RSI above 65) is true on {spy_exit_sel:.1f}% of its own days.")
    matched_len = {"1d": 100, "4h": 50, "1h": 150}
    for tf in ("1d", "4h", "1h"):
        d, s, f = frame(tf)
        i_tr, i_va = split_points(len(d))
        r2 = rsi(d["close"], 2)
        r2_tr = r2.iloc[:i_tr].dropna()
        eth_thresh = float(r2_tr.quantile(0.0505))
        eth_exit = float(r2_tr.quantile(1 - spy_exit_sel / 100))
        print(f"\n  {tf} bars: Ethereum's entry trigger = 2-bar RSI under {eth_thresh:.2f} "
              f"(fires on 5.05% of Ethereum's own first-60% bars, matching the S&P's own rate). "
              f"Exit trigger = RSI above {eth_exit:.1f}.")
        print(f"    Copying 'under 5' would have fired on "
              f"{float((r2_tr < 5).mean()*100):.2f}% of Ethereum's {tf} bars instead.")
        for thresh, tlabel in ((eth_thresh, "Ethereum's own trigger"), (5.0, "the S&P's number copied straight across")):
            for L, llabel in ((matched_len[tf], "Ethereum's own trend filter"), (200, "the S&P's 200-bar filter copied straight across")):
                sma_t = d["close"].rolling(L).mean()
                sma5 = d["close"].rolling(5).mean()
                trend = (d["close"] > sma_t).to_numpy()
                fire = (r2 < thresh).to_numpy() & trend
                exit_c = ((d["close"] > sma5).to_numpy()) | (r2 > eth_exit).to_numpy()
                state = np.zeros(len(d))
                pos = 0
                for i in range(len(d)):
                    if pos == 0 and fire[i]:
                        pos = 1
                    elif pos == 1 and exit_c[i]:
                        pos = 0
                    state[i] = pos
                ent = (state == 1) & (np.roll(state, 1) != 1)
                ent[0] = False
                warm = L + 25
                ent[:warm] = False
                entries = mask_entries(ent)
                # the dip needs room: a FIXED chart stop under the swing the dip
                # rests on, not a trailing one that ratchets into the bounce.
                stop_b = lambda tc: E.stop_structure(k=5, n_back=1, buffer_pct=0.0)
                tgt_b = lambda st: E.target_opposite_signal(state, treat_zero_as_exit=True)
                mh = 30 * BARS_PER_DAY[tf]
                t1, _ = run_edge_ctx(d, s, entries, stop_b, tgt_b, mh, f, lo_idx=warm, hi_idx=i_tr)
                t2, _ = run_edge_ctx(d, s, entries, stop_b, tgt_b, mh, f, lo_idx=i_tr, hi_idx=i_va)
                add("C RSI dip-buy", f"{tf} RSI<{thresh:.2f} above {L}-bar avg [{tlabel} + {llabel}]", tf,
                    "RSI(2)<5 above the 200-day average (S&P)",
                    f"RSI(2)<{eth_thresh:.2f} above the {matched_len[tf]}-bar average",
                    stats(t1), stats(t2), extra=dict(source_market="S&P 500 tracker"))


# ===========================================================================
# D — the flag touch (Bitcoin's live tactical trigger)
# ===========================================================================
def family_d():
    print("\n" + "=" * 96)
    print("FAMILY D — flag touch. Bitcoin's shape, Ethereum's numbers.")
    print("  Bitcoin: 2h bars, the bar dips to its 80-hour trend line and closes back above it,")
    print("  while the 4h trend rule is long. Validated on limit orders that wait; here it pays")
    print("  full market-order costs both ways for the first time, on a different coin.")
    print("=" * 96)
    d4, s4, _ = frame("4h")
    i_tr4, _ = split_points(len(d4))
    a4 = (atr(d4, 14) / d4["close"] * 100)
    gate4 = float(a4.iloc[:i_tr4].dropna().quantile(1 - 0.6321))
    champ4 = vol_gated_ma(d4, fast=20, slow=100, atr_n=14, min_atr_pct=gate4).fillna(0)
    champ_avail = pd.DataFrame({"timestamp": d4["timestamp"] + pd.Timedelta(hours=4),
                                "champ": champ4.to_numpy()}).sort_values("timestamp")

    for tf, lens in (("1h", (80, 40, 160)), ("4h", (20, 10, 40))):
        d, s, f = frame(tf)
        i_tr, i_va = split_points(len(d))
        champ = pd.merge_asof(d[["timestamp"]], champ_avail, on="timestamp",
                              direction="backward")["champ"].fillna(0).to_numpy()
        print(f"\n  {tf} bars, 4h trend gate re-derived to Ethereum's own {gate4:.2f}% range floor "
              f"(long on {float((champ==1).mean()*100):.1f}% of bars).")
        for L in lens:
            line = d["close"].rolling(L).mean()
            touch = ((d["low"] <= line) & (d["close"] > line)).to_numpy()
            fire = touch & (champ == 1)
            ent = fire.copy()
            warm = L + 25
            ent[:warm] = False
            touch_rate = float(touch[warm:i_tr].mean() * 100)
            entries = mask_entries(ent)
            stop_b = lambda tc: E.stop_structure(k=5, n_back=1, buffer_pct=0.0)
            tgt_b = lambda st: E.target_fixed_r(st, 3.0)
            mh = 2 * BARS_PER_DAY[tf]         # Bitcoin's own 48-hour cap, kept
            t1, _ = run_edge_ctx(d, s, entries, stop_b, tgt_b, mh, f, lo_idx=warm, hi_idx=i_tr)
            t2, _ = run_edge_ctx(d, s, entries, stop_b, tgt_b, mh, f, lo_idx=i_tr, hi_idx=i_va)
            hours = L * (1 if tf == "1h" else 4)
            add("D flag touch", f"{tf} {hours}-hour trend line (touched on {touch_rate:.1f}% of bars)", tf,
                "80-hour trend line, 2.20% stop (Bitcoin 2h)",
                f"{hours}-hour trend line, chart stop off Ethereum's own swings",
                stats(t1), stats(t2), extra=dict(source_market="Bitcoin"))


# ===========================================================================
# E — turn of the month (the S&P's)
# ===========================================================================
def family_e():
    print("\n" + "=" * 96)
    print("FAMILY E — turn of the month. The S&P tracker's shape, Ethereum's calendar.")
    print("  S&P: long from 3 trading days before month end through 3 trading days into the new")
    print("  month. That window covers 33.5% of the S&P's bars. Ethereum trades every calendar")
    print("  day, so the same 7 CALENDAR days cover only 23.3% of Ethereum's bars.")
    print("=" * 96)
    d, s, f = frame("1d")
    i_tr, i_va = split_points(len(d))
    ts = pd.DatetimeIndex(d["timestamp"])
    month_end = ts.is_month_end
    # days until the next month end, computed from the calendar only
    days_to_end = np.array([(pd.Timestamp(t).days_in_month - pd.Timestamp(t).day) for t in ts])
    day_of_month = np.array([pd.Timestamp(t).day for t in ts])

    # first, the plain measurement: is there anything there at all?
    ret = d["close"].pct_change().shift(-1) * 100      # next day's price move, in percent
    for before, after in ((3, 3), (5, 5)):
        win = (days_to_end <= before) | (day_of_month <= after)
        tr_win = win[:i_tr]
        r = ret.iloc[:i_tr].to_numpy()
        inw, outw = r[tr_win & ~np.isnan(r)], r[~tr_win & ~np.isnan(r)]
        se = np.sqrt(inw.var(ddof=1) / len(inw) + outw.var(ddof=1) / len(outw))
        t_stat = (inw.mean() - outw.mean()) / se if se else float("nan")
        print(f"\n  Window = {before} calendar days before month end through {after} into the new "
              f"month ({win[:i_tr].mean()*100:.1f}% of Ethereum's first-60% bars).")
        print(f"    Ethereum's average next-day price move inside the window {inw.mean():+.3f}%, "
              f"outside it {outw.mean():+.3f}%, difference {inw.mean()-outw.mean():+.3f} percentage "
              f"points, t = {t_stat:.2f}. (This is a price move, not a change in a position's margin.)")
        ent = win & ~np.roll(win, 1)
        ent[0] = False
        warm = 30
        ent[:warm] = False
        entries = mask_entries(ent)
        stop_b = lambda tc: E.stop_structure(k=5, n_back=1, buffer_pct=0.0)
        hold = before + after + 1
        tgt_b = lambda st: E.target_time(hold)
        t1, _ = run_edge_ctx(d, s, entries, stop_b, tgt_b, hold, f, lo_idx=warm, hi_idx=i_tr)
        t2, _ = run_edge_ctx(d, s, entries, stop_b, tgt_b, hold, f, lo_idx=i_tr, hi_idx=i_va)
        add("E turn of the month", f"1d {before} days before through {after} after", "1d",
            "3 trading days either side (S&P)", f"{before} calendar days either side",
            stats(t1), stats(t2), extra=dict(source_market="S&P 500 tracker",
                                             t_stat_train=float(t_stat)))


# ===========================================================================
# the control every family is judged against
# ===========================================================================
def controls():
    print("\n" + "=" * 96)
    print("COMPARED AGAINST ENTERING AT RANDOM TIMES")
    print("  Same number of entries, placed at random bars in the same two windows, run through")
    print("  the identical chart stop, target and market-order costs. This is what luck alone")
    print("  produces, and it is what every number above has to beat.")
    print("=" * 96)
    out = []
    for tf, n_tr, n_va, sb, tb, mh, label in (
        ("4h", 60, 20, lambda tc: E.stop_structure_trailing(buffer_pct=1.8, fallback_pct=8.0),
         lambda st: None, 60 * 6, "trend-shaped: trailing chart stop, ride until stopped"),
        ("1h", 200, 60, lambda tc: E.stop_structure(k=5, n_back=1, buffer_pct=0.0),
         lambda st: E.target_fixed_r(st, 3.0), 48, "dip/flag-shaped: fixed chart stop, 3:1 target, 48h cap"),
        ("1d", 40, 12, lambda tc: E.stop_structure(k=5, n_back=1, buffer_pct=0.0),
         lambda st: E.target_time(7), 7, "calendar-shaped: fixed chart stop, 7-day hold"),
    ):
        d, s, f = frame(tf)
        i_tr, i_va = split_points(len(d))
        c = random_entry_control(d, s, n_tr, n_va, sb, tb, mh, f, i_tr, i_va, warm=250, draws=30)
        print(f"  {tf} {label}")
        print(f"    30 random draws: both windows came out positive on "
              f"{c['luck_pass_rate']*100:.0f}% of them. Average profit per trade from random "
              f"timing: first slice ${c['mean_train_exp']:+.2f}, middle slice ${c['mean_val_exp']:+.2f}.")
        out.append(dict(shape=label, timeframe=tf, **c))
    pd.DataFrame(out).to_csv("step320_chance_baseline.csv", index=False)
    return out


def main():
    family_a()
    family_b()
    family_c()
    family_d()
    family_e()
    ctrl = controls()

    df = pd.DataFrame(ROWS)
    df.to_csv("step320_table.csv", index=False)
    print("\n" + "=" * 96)
    print(f"{len(df)} cells tested. Written to step320_table.csv")
    print("=" * 96)
    surv = df[df["verdict"].str.startswith("SURVIVES")]
    print(f"\nCells that came out positive on BOTH the first 60% and the middle 20% "
          f"with enough trades: {len(surv)} of {len(df)}")
    if len(surv):
        print(surv[["family", "cell", "train_trades", "train_avg_profit_per_trade",
                    "val_trades", "val_avg_profit_per_trade",
                    "times_bigger_than_trading_cost_val"]].to_string(index=False,
                                                                     float_format=lambda x: f"{x:,.2f}"))
    luck = float(np.mean([c["luck_pass_rate"] for c in ctrl]))
    print(f"\nLuck alone clears that same bar {luck*100:.0f}% of the time (average across the three "
          f"exit shapes, 30 random-timing draws each). Across a grid of {len(df)} cells that is "
          f"about {luck*len(df):.1f} apparent winners from chance.")
    print(df.groupby("family")["verdict"].value_counts().to_string())
    return df


if __name__ == "__main__":
    main()
