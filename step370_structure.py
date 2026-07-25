"""
step370_structure.py - ROUND 370, PART 1
HOW FAR AWAY DOES CHART STRUCTURE SIT ON 5-MINUTE S&P BARS?

Research only. No orders, paper or otherwise. No live file touched.
The bot cannot trade this book anywhere today; Alpaca paper is the first
venue that could hold it. That does not lower the evidence bar.

WHAT THIS FILE DOES
  1. Loads the Alpaca 5-minute bars, keeps only regular trading hours
     (09:30 to 16:00 New York), and splits 60/20/20 in time. Only the
     first 60% is read here. The middle 20% is read once by the strategy
     file. The final 20% is never opened.
  2. For every bar it measures how far the nearest piece of chart
     structure sits - the level that would say "this long idea was
     wrong" - under TWO different definitions of a swing point:
       OURS: confirmed_swings(d, k), a centred 2k+1 bar fractal read k
             bars late. Round 362 used k=3 on daily bars.
       TJR'S: a two-candle pattern (up candle then down candle for a
             high) read ONE bar late, from step301_tjr_rules.md 2.1.
     These are different objects and they give different stop distances.
  3. Converts each stop distance into a position size at a fixed
     fraction of the account risked. Size = dollars risked / stop
     distance, so leverage is an OUTPUT, never an input.
  4. Checks whether an intraday-sized stop could survive SPY's 17.5 hour
     overnight window.

Every distance is a PRICE move (how far the price has to travel), never
a change in margin. At 20 times leverage a 0.1% price move is a 2%
change in margin - twenty-fold different, so the units are stated every
time.
"""

import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
from step41_shorts import confirmed_swings

REPO = "/Users/wallacechen/cryptobot"
NY = "America/New_York"


# ----------------------------------------------------------------- data
def load_rth(symbol="SPY", tf="5m"):
    df = pd.read_parquet(f"{REPO}/data_alpaca_{symbol}_{tf}.parquet")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    et = df["timestamp"].dt.tz_convert(NY)
    df["et"] = et
    df["date"] = et.dt.date
    df["mins"] = et.dt.hour * 60 + et.dt.minute
    # regular trading hours only: a bar STAMPED 09:30 covers 09:30-09:35,
    # a bar stamped 15:55 is the last one that closes at 16:00.
    rth = df[(df["mins"] >= 570) & (df["mins"] <= 955)].copy()
    rth = rth.reset_index(drop=True)
    return df.reset_index(drop=True), rth


def split_60_20_20(n):
    return int(n * 0.60), int(n * 0.80)


# --------------------------------------------------- swing definitions
def tjr_swings(d):
    """TJR's two-candle swing, step301_tjr_rules.md section 2.1.

    Swing HIGH  = an up candle (close>open) immediately followed by a
                  down candle (close<open). Level = the higher of the two
                  HIGHS (the highest wick of the pair).
    Swing LOW   = a down candle followed by an up candle. Level = the
                  lower of the two LOWS.
    Confirmed ONE bar after the pivot: the pattern at bars (t-1, t) is
    known at the close of bar t, so the value is stamped at t.
    No lookahead: nothing after bar t is used.
    """
    o, h, l, c = d["open"].to_numpy(), d["high"].to_numpy(), d["low"].to_numpy(), d["close"].to_numpy()
    up = c > o
    dn = c < o
    n = len(d)
    sh = np.full(n, np.nan)
    sl = np.full(n, np.nan)
    # pattern at (t-1, t) -> stamped at t
    a_up, a_dn = up[:-1], dn[:-1]
    b_up, b_dn = up[1:], dn[1:]
    is_h = a_up & b_dn
    is_l = a_dn & b_up
    pair_hi = np.maximum(h[:-1], h[1:])
    pair_lo = np.minimum(l[:-1], l[1:])
    sh[1:] = np.where(is_h, pair_hi, np.nan)
    sl[1:] = np.where(is_l, pair_lo, np.nan)
    return pd.Series(sh, index=d.index), pd.Series(sl, index=d.index)


def last_below(level_series, ref_price, session=None):
    """At each bar t, the most recent CONFIRMED swing level whose price is
    strictly below ref_price[t]. Walks backwards through the confirmed
    history, so a swing low that sits ABOVE current price is skipped and
    an older one is used - that is what a stop has to do.

    If `session` is given, only levels stamped in the SAME session count
    (a day-trader who goes flat cannot lean on yesterday's structure
    without carrying the overnight gap).
    Returns (level, bars_ago).
    """
    lv = level_series.to_numpy()
    ref = ref_price.to_numpy()
    sess = None if session is None else session.to_numpy()
    n = len(lv)
    out = np.full(n, np.nan)
    ago = np.full(n, np.nan)
    hist_p, hist_i = [], []
    for t in range(n):
        p = ref[t]
        # search newest-first
        for j in range(len(hist_p) - 1, -1, -1):
            if sess is not None and sess[hist_i[j]] != sess[t]:
                break
            if hist_p[j] < p:
                out[t] = hist_p[j]
                ago[t] = t - hist_i[j]
                break
        if not np.isnan(lv[t]):
            hist_p.append(lv[t])
            hist_i.append(t)
            if len(hist_p) > 400:
                hist_p = hist_p[-400:]
                hist_i = hist_i[-400:]
    return out, ago


def last_above(level_series, ref_price, session=None):
    lv = level_series.to_numpy()
    ref = ref_price.to_numpy()
    sess = None if session is None else session.to_numpy()
    n = len(lv)
    out = np.full(n, np.nan)
    ago = np.full(n, np.nan)
    hist_p, hist_i = [], []
    for t in range(n):
        p = ref[t]
        for j in range(len(hist_p) - 1, -1, -1):
            if sess is not None and sess[hist_i[j]] != sess[t]:
                break
            if hist_p[j] > p:
                out[t] = hist_p[j]
                ago[t] = t - hist_i[j]
                break
        if not np.isnan(lv[t]):
            hist_p.append(lv[t])
            hist_i.append(t)
            if len(hist_p) > 400:
                hist_p = hist_p[-400:]
                hist_i = hist_i[-400:]
    return out, ago


def pct_stats(x):
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return dict(n=0)
    return dict(
        n=len(x),
        p10=np.percentile(x, 10), p25=np.percentile(x, 25),
        med=np.percentile(x, 50),
        p75=np.percentile(x, 75), p90=np.percentile(x, 90),
        mean=x.mean(),
    )


def fmt(s):
    if s["n"] == 0:
        return "no data"
    return (f"n={s['n']:>7,}  p10 {s['p10']:.3f}  p25 {s['p25']:.3f}  "
            f"MED {s['med']:.3f}  p75 {s['p75']:.3f}  p90 {s['p90']:.3f}")


# ------------------------------------------------------------------ run
def main():
    rows = []
    for sym, tf in (("SPY", "5m"), ("SPY", "15m")):
        try:
            full, rth = load_rth(sym, tf)
        except FileNotFoundError:
            print(f"[skip] no {sym} {tf} file yet")
            continue
        i_tr, i_va = split_60_20_20(len(rth))
        tr = rth.iloc[:i_tr].reset_index(drop=True)
        print("=" * 78)
        print(f"{sym} {tf}  regular-hours bars: {len(rth):,}  "
              f"({rth['et'].iloc[0]:%Y-%m-%d} to {rth['et'].iloc[-1]:%Y-%m-%d})")
        print(f"   choosing slice (first 60%): {len(tr):,} bars, "
              f"{tr['et'].iloc[0]:%Y-%m-%d} to {tr['et'].iloc[-1]:%Y-%m-%d}, "
              f"{tr['date'].nunique():,} sessions")
        print(f"   middle slice: bars {i_tr:,}-{i_va:,}   final slice NEVER OPENED")

        close = tr["close"]

        defs = {}
        sh_t, sl_t = tjr_swings(tr)
        defs["TJR 2-candle (1 bar late)"] = (sh_t, sl_t)
        for k in (2, 3, 5):
            a, b = confirmed_swings(tr, k)
            defs[f"ours fractal k={k} ({2*k+1} bar, {k} late)"] = (a, b)

        for name, (sh, sl) in defs.items():
            for scope, sess in (("any", None), ("same session only", tr["date"])):
                lo, ago_lo = last_below(sl, close, sess)
                hi, ago_hi = last_above(sh, close, sess)
                d_long = (close.to_numpy() - lo) / close.to_numpy() * 100.0
                d_short = (hi - close.to_numpy()) / close.to_numpy() * 100.0
                sL, sS = pct_stats(d_long), pct_stats(d_short)
                cov = 100.0 * sL["n"] / len(tr) if sL["n"] else 0
                print(f"\n  {name}  [{scope}]   long-stop coverage {cov:.1f}% of bars")
                print(f"    long  (dist below to last swing LOW , % of price): {fmt(sL)}")
                print(f"    short (dist above to last swing HIGH, % of price): {fmt(sS)}")
                if sL["n"]:
                    rows.append(dict(symbol=sym, tf=tf, swing_def=name, scope=scope,
                                     side="long", n=sL["n"], med_pct=sL["med"],
                                     p25=sL["p25"], p75=sL["p75"], p10=sL["p10"], p90=sL["p90"],
                                     med_bars_ago=np.nanmedian(ago_lo)))
                if sS["n"]:
                    rows.append(dict(symbol=sym, tf=tf, swing_def=name, scope=scope,
                                     side="short", n=sS["n"], med_pct=sS["med"],
                                     p25=sS["p25"], p75=sS["p75"], p10=sS["p10"], p90=sS["p90"],
                                     med_bars_ago=np.nanmedian(ago_hi)))

        # ---- time of day: does structure sit closer at the open?
        if tf == "5m":
            sh, sl = defs["TJR 2-candle (1 bar late)"]
            lo, _ = last_below(sl, close, tr["date"])
            d_long = (close.to_numpy() - lo) / close.to_numpy() * 100.0
            print("\n  --- TJR long-stop distance by time of day (same session, % of price) ---")
            buckets = [(570, 600, "09:30-10:00"), (600, 630, "10:00-10:30"),
                       (630, 720, "10:30-12:00"), (720, 840, "12:00-14:00"),
                       (840, 930, "14:00-15:30"), (930, 960, "15:30-16:00")]
            for a, b, lab in buckets:
                m = (tr["mins"] >= a) & (tr["mins"] < b)
                s = pct_stats(d_long[m.to_numpy()])
                if s["n"]:
                    print(f"    {lab}  MED {s['med']:.3f}%  p25 {s['p25']:.3f}  "
                          f"p75 {s['p75']:.3f}   n={s['n']:,}")

            # ---- overnight gap versus an intraday-sized stop
            print("\n  --- can an intraday stop survive the overnight window? ---")
            daily_last = tr.groupby("date")["close"].last()
            daily_first_low = tr.groupby("date")["low"].first()
            daily_open = tr.groupby("date")["open"].first()
            prev_close = daily_last.shift(1)
            gap_down = (prev_close - daily_open) / prev_close * 100.0
            overnight_low = (prev_close - daily_first_low) / prev_close * 100.0
            gd = gap_down.dropna().to_numpy()
            on = overnight_low.dropna().to_numpy()
            print(f"    sessions measured: {len(gd):,}")
            print(f"    overnight DOWN move at the open, median {np.median(np.abs(gd)):.3f}% of price, "
                  f"p90 {np.percentile(np.abs(gd),90):.3f}%")
            for stop in (0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 1.00, 1.84):
                pct = 100.0 * (on > stop).mean()
                print(f"    a {stop:.2f}%-of-price stop would be gapped through on "
                      f"{pct:5.1f}% of sessions if held overnight")

    if rows:
        out = pd.DataFrame(rows)
        out.to_csv(f"{REPO}/step370_table.csv", index=False)
        print(f"\nwrote step370_table.csv  ({len(out)} rows)")

        # ------------------------------------------------ leverage table
        print("\n" + "=" * 78)
        print("LEVERAGE THAT EACH STOP DISTANCE PERMITS")
        print("size = dollars risked / stop distance. Leverage is the OUTPUT.")
        print("'0.5x' means the position is half the account, '10x' means ten times it.")
        print("=" * 78)
        print(f"{'setup / stop basis':<52}{'stop %':>9}{'risk 1%':>10}{'risk 2%':>10}")
        ref = [
            ("DAILY bars, SPY dip-buy, 3-bar swings (round 362)", 1.84),
            ("DAILY bars, SPY dip-buy, 5-bar swings (round 362)", 2.26),
            ("DAILY bars, SPY turn-of-month, 3-bar (round 362)", 3.12),
            ("DAILY bars, SPY turn-of-month, 5-bar (round 362)", 4.24),
        ]
        sub = out[(out.tf == "5m") & (out.side == "long") & (out.scope == "same session only")]
        for _, r in sub.iterrows():
            ref.append((f"5-MIN bars, {r.swing_def}", r.med_pct))
        for lab, s in ref:
            print(f"{lab:<52}{s:>8.3f}%{1.0/s:>9.1f}x{2.0/s:>9.1f}x")


if __name__ == "__main__":
    main()
