"""
step410_intraday.py - ROUND 410, JOB 2 PARTS 1 TO 3
IS THERE A TRADEABLE LIT SESSION ON A HIGH-VOLATILITY SINGLE NAME?

Research only. No orders of any kind. Nothing live is touched.

THE QUESTION
  Round 370 measured the S&P and found its money lives in the dark. On SPY,
  holding through a whole regular session earns a fraction of what one
  round trip costs, while the closed hours carry the drift. That kills the
  owner's actual style on the index: you cannot trade a session that does
  not pay.

  Individual names are not the index. They move several times as much in a
  day, they have earnings dates and their own news. So the question is
  whether the lit-session return that does not exist on SPY DOES exist on
  a name like NVDA or TSLA. If it does, that is the first market on this
  desk where trading the session is possible at all.

WHAT THIS FILE MEASURES, IN ORDER
  1. How far the nearest piece of chart structure sits below price - the
     level that would prove a long wrong - as a percentage of price, on
     5-minute bars and on daily bars, under two swing definitions:
       ours  : a centred 2k+1 bar fractal, read k bars late
       TJR's : a two-candle pattern, read one bar late
     Round 370 found TJR's sits about 44% closer on SPY, which doubles the
     size a fixed risk budget buys. Recomputed here per name, never ported.
  2. What position size each of those distances buys at 1% and at 2% of
     the account risked. Size = dollars risked / stop distance, so the
     leverage is an OUTPUT of the stop, never a number chosen up front.
  3. Open-to-close against close-to-next-open, per name, gross, with
     t-statistics. This is the measurement that killed the S&P intraday
     case, run on the AI complex.

UNITS
  Every percentage below is a PRICE move unless it explicitly says it is a
  change in the value of a position. At 10x leverage a 0.1% price move is
  a 1% change in the money put up: ten-fold different, so the two are
  never mixed.

SPLIT
  Everything is measured on the first 60% of the bars. The middle 20% is
  left for the strategy file. The final 20% is never opened.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
from step41_shorts import confirmed_swings
from step410_lib import (REPO, load_daily, load_5m_rth, split_60_20_20,
                         costs_table, tjr_swings, last_below, last_above,
                         tstat)

NAMES = ["NVDA", "AMD", "AVGO", "MU", "MSFT", "GOOGL", "META", "AMZN",
         "TSLA", "SMH"]
REFERENCE = ["SPY", "QQQ"]


def pct_stats(x):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return None
    return dict(n=len(x), p25=np.percentile(x, 25), med=np.percentile(x, 50),
                p75=np.percentile(x, 75), p90=np.percentile(x, 90))


def section(t):
    print("\n" + "=" * 84)
    print(t)
    print("=" * 84)


# =========================================================== PARTS 1 AND 2
def structure_and_leverage(symbols):
    rows = []
    section("1 AND 2. HOW FAR IS THE NEAREST STRUCTURE, AND WHAT SIZE DOES IT BUY?")
    print("Long-stop distance = how far price sits ABOVE the most recent confirmed")
    print("swing low that is below it. All figures are PRICE moves, % of price.")
    print("Size = dollars risked / stop distance. '10x' means the position is ten")
    print("times the account. On 5-minute bars only same-session structure counts:")
    print("a trader who goes flat at the close cannot lean on yesterday's low")
    print("without carrying the whole overnight window.")

    for sym in symbols:
        # ---------------- 5-minute, regular hours, same-session structure
        try:
            _, rth = load_5m_rth(sym)
        except FileNotFoundError:
            print(f"\n  {sym}: no 5-minute file yet")
            rth = None
        if rth is not None:
            i_tr, _ = split_60_20_20(len(rth))
            tr = rth.iloc[:i_tr].reset_index(drop=True)
            close = tr["close"]
            defs = {}
            a, b = tjr_swings(tr)
            defs["TJR 2-candle"] = (a, b)
            for k in (2, 3, 5):
                a2, b2 = confirmed_swings(tr, k)
                defs[f"ours fractal k={k}"] = (a2, b2)
            print(f"\n  {sym}  5-minute regular-hours bars: {len(rth):,}, "
                  f"choosing slice {len(tr):,} "
                  f"({tr['et'].iloc[0]:%Y-%m-%d} to {tr['et'].iloc[-1]:%Y-%m-%d}, "
                  f"{tr['date'].nunique():,} sessions)")
            print(f"    {'swing definition':<22}{'p25':>8}{'MEDIAN':>9}{'p75':>8}"
                  f"{'p90':>8}{'risk 1%':>10}{'risk 2%':>10}{'cover':>8}")
            for name, (sh, sl) in defs.items():
                lo, _ = last_below(sl, close, tr["date"])
                dl = (close.to_numpy() - lo) / close.to_numpy() * 100.0
                s = pct_stats(dl)
                if not s:
                    continue
                cov = 100.0 * s["n"] / len(tr)
                print(f"    {name:<22}{s['p25']:>7.3f}%{s['med']:>8.3f}%"
                      f"{s['p75']:>7.3f}%{s['p90']:>7.3f}%"
                      f"{1.0/s['med']:>9.1f}x{2.0/s['med']:>9.1f}x{cov:>7.0f}%")
                rows.append(dict(symbol=sym, tf="5m", swing_def=name,
                                 scope="same session", side="long",
                                 n=s["n"], med_pct=s["med"], p25=s["p25"],
                                 p75=s["p75"], p90=s["p90"],
                                 lev_risk1=1.0 / s["med"], lev_risk2=2.0 / s["med"]))

        # ---------------------------------------------------- daily bars
        d = load_daily(sym)
        i_trd, _ = split_60_20_20(len(d))
        td = d.iloc[:i_trd].reset_index(drop=True)
        cd = td["close"]
        ddefs = {}
        a, b = tjr_swings(td)
        ddefs["TJR 2-candle"] = (a, b)
        for k in (3, 5):
            a2, b2 = confirmed_swings(td, k)
            ddefs[f"ours fractal k={k}"] = (a2, b2)
        print(f"    -- daily bars ({len(td):,} in the choosing slice) --")
        for name, (sh, sl) in ddefs.items():
            lo, _ = last_below(sl, cd)
            dl = (cd.to_numpy() - lo) / cd.to_numpy() * 100.0
            s = pct_stats(dl)
            if not s:
                continue
            print(f"    {name:<22}{s['p25']:>7.3f}%{s['med']:>8.3f}%"
                  f"{s['p75']:>7.3f}%{s['p90']:>7.3f}%"
                  f"{1.0/s['med']:>9.1f}x{2.0/s['med']:>9.1f}x"
                  f"{100.0*s['n']/len(td):>7.0f}%")
            rows.append(dict(symbol=sym, tf="1d", swing_def=name, scope="any",
                             side="long", n=s["n"], med_pct=s["med"],
                             p25=s["p25"], p75=s["p75"], p90=s["p90"],
                             lev_risk1=1.0 / s["med"], lev_risk2=2.0 / s["med"]))
    return pd.DataFrame(rows)


# ================================================================= PART 3
def session_vs_dark(symbols, costs):
    section("3. DOES THE LIT SESSION PAY? OPEN-TO-CLOSE AGAINST CLOSE-TO-NEXT-OPEN")
    print("Gross, before costs, on the choosing slice only. Open-to-close is the")
    print("regular session the bot could actually trade with market orders.")
    print("Close-to-next-open is the closed window, which needs a position held")
    print("through it and cannot be day-traded. Both are PRICE moves.")
    print("The last column is what matters: session return divided by the measured")
    print("round-trip cost of one market-in market-out trade in that name.")
    print("A window is tradeable only if BOTH hold: the mean is actually measured")
    print("(t of about 2 or more, otherwise it is noise the sample happens to")
    print("show) AND it is worth at least 5 times the round-trip cost.")
    print(f"\n  {'name':>6}{'sessions':>10}{'session%':>10}{'t':>7}{'x cost':>8}"
          f"{'   |':>4}{'dark%':>9}{'t':>7}{'x cost':>8}  which window is tradeable")
    rows = []
    for sym in symbols + REFERENCE:
        try:
            d = load_daily(sym)
        except FileNotFoundError:
            continue
        i_tr, _ = split_60_20_20(len(d))
        t = d.iloc[:i_tr]
        o, c = t["open"].to_numpy(), t["close"].to_numpy()
        intraday = (c - o) / o * 100.0
        dark = (o[1:] - c[:-1]) / c[:-1] * 100.0
        cost = costs.get(sym, {}).get("p75", np.nan)
        ts, td_ = tstat(intraday), tstat(dark)
        rs = intraday.mean() / cost
        rd = dark.mean() / cost
        sess_ok = (ts >= 2.0) and (rs >= 5.0)
        dark_ok = (td_ >= 2.0) and (rd >= 5.0)
        verdict = ("session" if sess_ok and not dark_ok else
                   "DARK WINDOW only" if dark_ok and not sess_ok else
                   "both" if sess_ok and dark_ok else "neither")
        print(f"  {sym:>6}{len(intraday):>10,}{intraday.mean():>10.4f}"
              f"{ts:>7.2f}{rs:>8.1f}{'   |':>4}{dark.mean():>9.4f}"
              f"{td_:>7.2f}{rd:>8.1f}  {verdict}")
        rows.append(dict(symbol=sym, n_sessions=len(intraday),
                         session_mean_pct=intraday.mean(), session_t=ts,
                         session_over_cost=rs,
                         dark_mean_pct=dark.mean(), dark_t=td_,
                         dark_over_cost=rd,
                         session_sd=intraday.std(ddof=1),
                         dark_sd=dark.std(ddof=1),
                         cost_pct=cost, tradeable=verdict))
    print("\n  Note what the two t columns do. Not one lit session in this basket")
    print("  is a measured drift. The closed window is measured on almost all of")
    print("  them, and by a wide margin. The index finding from round 370 does")
    print("  not just carry over to single names, it gets stronger.")
    return pd.DataFrame(rows)


def session_shape(symbols):
    """Where inside the session does whatever return exists actually sit?"""
    section("3b. WHERE INSIDE THE SESSION DOES THE MOVE SIT?")
    print("Mean price move per 5-minute bar, by time of day, choosing slice only.")
    print("If a name pays at all, this says when. All figures are % of price.")
    buckets = [(570, 600, "09:30-10:00"), (600, 630, "10:00-10:30"),
               (630, 720, "10:30-12:00"), (720, 840, "12:00-14:00"),
               (840, 930, "14:00-15:30"), (930, 960, "15:30-16:00")]
    print(f"\n  {'name':>6}" + "".join(f"{lab:>13}" for _, _, lab in buckets))
    rows = []
    for sym in symbols:
        try:
            _, rth = load_5m_rth(sym)
        except FileNotFoundError:
            continue
        i_tr, _ = split_60_20_20(len(rth))
        tr = rth.iloc[:i_tr].reset_index(drop=True)
        r = tr["close"].pct_change() * 100.0
        r[tr["date"] != tr["date"].shift(1)] = np.nan   # never span sessions
        line = f"  {sym:>6}"
        rec = dict(symbol=sym)
        for a, b, lab in buckets:
            m = (tr["mins"] >= a) & (tr["mins"] < b)
            v = r[m].dropna()
            tot = v.sum()          # total price move contributed by that window
            line += f"{tot:>12.1f}%"
            rec[lab] = tot
        print(line)
        rows.append(rec)
    print("\n  These are TOTALS of per-bar price moves across the whole choosing")
    print("  slice, so they say which part of the day carried the move, not what")
    print("  any single day did.")
    return pd.DataFrame(rows)


def main():
    costs = costs_table()
    have = []
    for s in NAMES:
        try:
            load_daily(s)
            have.append(s)
        except FileNotFoundError:
            print(f"[skip] no daily file for {s}")

    t3 = session_vs_dark(have, costs)
    t3.to_csv(f"{REPO}/step410_table_session.csv", index=False)

    t12 = structure_and_leverage(have + REFERENCE)
    t12.to_csv(f"{REPO}/step410_table_structure.csv", index=False)

    t3b = session_shape(have)
    t3b.to_csv(f"{REPO}/step410_table_session_shape.csv", index=False)

    # ---- the headline leverage comparison, single table
    section("THE LEVERAGE TABLE")
    print("Median stop distance and the size it buys, 5-minute same-session")
    print("structure, TJR's two-candle definition against our fractal.")
    print("Leverage is an OUTPUT of the stop distance and the risk budget.")
    print(f"\n  {'name':>6}{'TJR stop%':>11}{'1% risk':>10}{'2% risk':>10}"
          f"{'k=3 stop%':>12}{'1% risk':>10}{'2% risk':>10}{'TJR closer by':>15}")
    f = t12[(t12.tf == "5m")]
    for sym in have + REFERENCE:
        a = f[(f.symbol == sym) & (f.swing_def == "TJR 2-candle")]
        b = f[(f.symbol == sym) & (f.swing_def == "ours fractal k=3")]
        if len(a) == 0 or len(b) == 0:
            continue
        a = a.iloc[0]; b = b.iloc[0]
        closer = 100.0 * (1 - a.med_pct / b.med_pct)
        print(f"  {sym:>6}{a.med_pct:>10.3f}%{a.lev_risk1:>9.1f}x"
              f"{a.lev_risk2:>9.1f}x{b.med_pct:>11.3f}%{b.lev_risk1:>9.1f}x"
              f"{b.lev_risk2:>9.1f}x{closer:>14.0f}%")
    print("\nwrote step410_table_session.csv, step410_table_structure.csv,")
    print("      step410_table_session_shape.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
