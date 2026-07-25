"""
step370_meanrev.py - ROUND 370, PART 4
GIVING THE INTRADAY THESIS ITS BEST SHOT

Research only. No orders. No live file touched. Paper-only book.

Parts 2 and 3 killed the breakout and sweep-reversal families. Before
closing the round it is only fair to test the shapes MOST likely to work
here, rather than the ones that happen to be famous:

  F4  The desk's one validated edge, ported to 5-minute bars. RSI2 deep
      dip, long only, exit when the short average is reclaimed. Constants
      RE-DERIVED on 5-minute bars, never ported from the daily version
      and never from crypto.
  F5  The opening gap, traded intraday. Buy the open after a gap down,
      sell it after a gap up, flat at the close.
  F6  The turn of month, split into its two halves. The desk's strongest
      signal fires about twelve times a year. This asks whether that
      return arrives during the session (tradeable intraday, many
      entries) or in the dark window between sessions (not tradeable
      intraday at all).

Same discipline: every signal scored independently, filters as strict
subsets, 60/20/20, final 20% never opened, costs on both ends, stops at
chart structure, leverage an output.
"""

import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
from step370_structure import split_60_20_20
from step370_intraday import prep, simulate, COST_RT, MIN_TR, MIN_VA

REPO = "/Users/wallacechen/cryptobot"


def tstat(x):
    x = np.asarray(x, dtype=float); x = x[np.isfinite(x)]
    if len(x) < 3:
        return np.nan
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))


def rsi(series, n):
    d = series.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def line(name, res, i_tr, i_va, cost=COST_RT):
    tr = res[res.sig_i < i_tr]
    va = res[(res.sig_i >= i_tr) & (res.sig_i < i_va)]
    if len(tr) < MIN_TR or len(va) < MIN_VA:
        return dict(name=name, n_tr=len(tr), n_va=len(va), verdict="NOT ENOUGH TRADES")
    g_tr = tr["gross_pct"].mean(); m_tr = tr["net_pct"].mean(); m_va = va["net_pct"].mean()
    return dict(name=name, n_tr=len(tr), n_va=len(va),
                gross_tr=g_tr, mean_tr=m_tr, mean_va=m_va,
                t_tr=tstat(tr["net_pct"]),
                stop_tr=tr["stop_dist_pct"].mean(),
                lev1=1.0 / tr["stop_dist_pct"].mean(),
                thick=m_tr / cost,
                verdict="SURVIVES" if (m_tr > 0 and m_va > 0 and m_tr / cost >= 5) else "reject")


def show(rows, title):
    print("\n" + "-" * 104)
    print(title)
    print("-" * 104)
    print(f"{'setup':<46}{'n_tr':>6}{'n_va':>6}{'gross%':>9}{'net%':>9}"
          f"{'mid%':>9}{'t':>7}{'stop%':>7}{'lev@1%':>8}{'xcost':>7}  verdict")
    for r in rows:
        if r.get("verdict") == "NOT ENOUGH TRADES":
            print(f"{r['name']:<46}{r['n_tr']:>6}{r['n_va']:>6}   NOT ENOUGH TRADES")
            continue
        print(f"{r['name']:<46}{r['n_tr']:>6}{r['n_va']:>6}{r['gross_tr']:>9.4f}"
              f"{r['mean_tr']:>9.4f}{r['mean_va']:>9.4f}{r['t_tr']:>7.2f}"
              f"{r['stop_tr']:>7.3f}{r['lev1']:>7.1f}x{r['thick']:>7.1f}  {r['verdict']}")


# --------------------------------------------------------------- F4
def family_meanrev(d, i_tr, i_va, out, sym):
    """RSI2 deep dip on 5-minute bars. The daily version's threshold (RSI2
    below 5) is NOT ported: the 5-minute distribution is re-measured and
    the sweep runs over its own range. Trend context is the 5-minute
    200-bar average, the intraday analogue of the daily SMA200 the
    validated version uses."""
    c = d["close"]
    sma200 = c.rolling(200).mean()
    sma5 = c.rolling(5).mean()
    above = (c > sma200).to_numpy()
    for rn in (2, 3):
        r = rsi(c, rn).to_numpy()
        for thr in (2, 5, 10, 15):
            for trend, tlab in ((above, "above 200-bar avg"), (np.ones(len(d), bool), "no trend filter")):
                sig = np.where((r < thr) & trend)[0]
                if len(sig) < 60:
                    continue
                stop = d["mr_sl"].to_numpy()[sig]
                res = simulate(d, sig, +1, stop, None)
                out.append(line(f"{sym} RSI{rn}<{thr} 5m dip, {tlab}", res, i_tr, i_va))


# --------------------------------------------------------------- F5
def family_gap(d, i_tr, i_va, out, sym):
    """The opening gap, traded inside the session and flat at the close."""
    g = d.groupby("sid")
    first_i = g.apply(lambda x: x.index[0], include_groups=False).to_numpy()
    op = d["open"].to_numpy()[first_i]
    prev_c = np.r_[np.nan, d["close"].to_numpy()[d["last_idx"].to_numpy()[first_i][:-1]]]
    gap = (op - prev_c) / prev_c * 100.0
    for lo, hi, lab in ((-99, -0.3, "gap DOWN more than 0.3%"),
                        (-99, -0.5, "gap DOWN more than 0.5%"),
                        (0.3, 99, "gap UP more than 0.3%"),
                        (0.5, 99, "gap UP more than 0.5%")):
        sel = np.where((gap > lo) & (gap < hi))[0]
        if len(sel) < 40:
            continue
        idx = first_i[sel]
        for dirn, dlab in ((+1, "buy"), (-1, "sell")):
            stop = (d["mr_sl"] if dirn > 0 else d["mr_sh"]).to_numpy()[idx]
            res = simulate(d, idx, dirn, stop, None)
            out.append(line(f"{sym} {lab}, {dlab} at open, flat at close", res, i_tr, i_va))


# --------------------------------------------------------------- F6
def family_turn_of_month(d, i_tr, sym):
    """Where does the turn-of-month return actually arrive? Split each
    session into its lit part (open to close) and its dark part (close to
    next open) and compare turn-of-month sessions with the rest. Gross of
    costs, choosing slice only."""
    g = d.groupby("sid")
    o = g["open"].first(); c = g["close"].last()
    dates = g["date"].first()
    sess = pd.DataFrame(dict(date=dates.values, open=o.values, close=c.values),
                        index=o.index)
    sess["intraday"] = (sess["close"] - sess["open"]) / sess["open"] * 100.0
    sess["overnight"] = (sess["open"].shift(-1) - sess["close"]) / sess["close"] * 100.0
    ym = pd.to_datetime(sess["date"]).dt.to_period("M")
    sess["from_end"] = sess.groupby(ym).cumcount(ascending=False)   # 0 = last session of month
    tr = sess.iloc[:int(len(sess) * 0.60)]
    print("\n" + "=" * 104)
    print(f"F6  {sym}: the turn-of-month return, split into the lit session and the dark window")
    print("Choosing slice only, gross of costs, % of PRICE. A round trip costs 0.0400% of notional.")
    print("=" * 104)
    print(f"{'window':<34}{'sessions':>10}{'open->close':>14}{'t':>7}"
          f"{'close->next open':>19}{'t':>7}")
    tom = tr[tr["from_end"] <= 3]
    rest = tr[tr["from_end"] > 3]
    for lab, sub in (("last 4 sessions of the month", tom),
                     ("every other session", rest)):
        print(f"{lab:<34}{len(sub):>10}{sub['intraday'].mean():>14.4f}"
              f"{tstat(sub['intraday']):>7.2f}{sub['overnight'].mean():>19.4f}"
              f"{tstat(sub['overnight'].dropna()):>7.2f}")
    lift_i = tom["intraday"].mean() - rest["intraday"].mean()
    lift_o = tom["overnight"].mean() - rest["overnight"].mean()
    print(f"\n  turn-of-month lift, lit session : {lift_i:+.4f}% of price per session "
          f"= {lift_i/0.04:+.2f}x one round trip")
    print(f"  turn-of-month lift, dark window : {lift_o:+.4f}% of price per session "
          f"= {lift_o/0.04:+.2f}x one round trip")


def main():
    allrows = []
    for sym in ("SPY", "QQQ"):
        try:
            d = prep(sym, "5m")
        except FileNotFoundError:
            continue
        i_tr, i_va = split_60_20_20(len(d))
        out = []
        family_meanrev(d, i_tr, i_va, out, sym)
        show(out, f"FAMILY 4 - {sym}: the desk's validated dip-buy shape, on 5-minute bars, "
                  f"constants re-derived")
        n = len(out)
        family_gap(d, i_tr, i_va, out, sym)
        show(out[n:], f"FAMILY 5 - {sym}: the opening gap, traded inside the session")
        family_turn_of_month(d, i_tr, sym)
        allrows += out
    df = pd.DataFrame(allrows)
    df.to_csv(f"{REPO}/step370_table_meanrev.csv", index=False)
    ok = df[df.verdict == "SURVIVES"] if "verdict" in df else df.iloc[:0]
    print(f"\n{len(df)} settings tested across both instruments, {len(ok)} survive.")
    if len(ok):
        print(ok.to_string(index=False))


if __name__ == "__main__":
    main()
