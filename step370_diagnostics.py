"""
step370_diagnostics.py - ROUND 370, PART 3
WHY THE INTRADAY SETUPS FAILED, AND WHERE THE INDEX'S RETURN ACTUALLY LIVES

Research only. No orders. No live file touched. Paper-only book.

Part 2 rejected essentially everything. Before writing that up, three
questions have to be separated, because they have different answers and
different consequences:

  Q1  Do the signals carry NO directional information at all, or do they
      carry a little and the stop-plus-cost machinery eats it? Answered
      by scoring the same signals with NO stop and NO target, held to the
      session close, against the same population of all eligible bars.
  Q2  Where inside the day does the index's return actually sit? A
      minute-by-minute drift profile with a t-statistic.
  Q3  How much of the cost bar can a tight stop ever clear? The
      arithmetic of "profit must be 5x the round-trip cost" when the
      round trip is a fixed share of notional and the stop is 0.09%.

Plus a cross-instrument replay on QQQ, unchanged.

Units, always: a distance in "% of price" is how far the PRICE has to
move. A change in margin at 20 times leverage is twenty times that. The
two are never mixed here.
"""

import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
from step370_structure import load_rth, tjr_swings, split_60_20_20
from step370_intraday import prep, simulate, sweep_reversal, COST_RT

REPO = "/Users/wallacechen/cryptobot"


def tstat(x):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return np.nan
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))


# ---------------------------------------------------------------- Q1
def signal_edge_no_stop(d, i_tr, i_va, sym):
    """Score every signal with NO stop and NO target - buy the next open,
    sell at the session's last close. Compare to the SAME machinery run
    on every eligible bar in the same clock window. This is a like-for-
    like partition, not a filtered re-run: the signal set is a strict
    subset of the eligible set, verified by entry timestamp.
    """
    print("\n" + "=" * 96)
    print(f"Q1  {sym}: do the signals carry direction at all? "
          f"No stop, no target, buy next open, sell at the session close.")
    print("Gross of costs, in % of PRICE. A round trip costs 0.04% of notional.")
    print("=" * 96)
    o = d["open"].to_numpy(); c = d["close"].to_numpy()
    lastix = d["last_idx"].to_numpy(); mins = d["mins"].to_numpy()

    def hold_to_close(idx, direction):
        idx = np.asarray(idx, dtype=int)
        j = idx + 1
        ok = j <= lastix[idx]
        j = j[ok]; ii = idx[ok]
        ret = direction * (c[lastix[ii]] - o[j]) / o[j] * 100.0
        return ii, ret

    rows = []
    combos = [("pdl", +1, "prev day low sweep -> BOS up"),
              ("pdh", -1, "prev day high sweep -> BOS down"),
              ("onl", +1, "overnight low sweep -> BOS up"),
              ("onh", -1, "overnight high sweep -> BOS down"),
              ("or30l", +1, "opening-range low sweep -> BOS up"),
              ("or30h", -1, "opening-range high sweep -> BOS down")]
    for col, dirn, lab in combos:
        for (a, b, wlab) in ((570, 630, "09:30-10:30"), (570, 955, "all session")):
            sig, stop, sw = sweep_reversal(d, col, dirn, a, b)
            if len(sig) < 40:
                continue
            si, sret = hold_to_close(sig, dirn)
            elig = np.where((mins >= a) & (mins < b))[0]
            ei, eret = hold_to_close(elig, dirn)
            assert set(si.tolist()) <= set(ei.tolist()), "signal set is not a subset"
            m_tr = si < i_tr; m_va = (si >= i_tr) & (si < i_va)
            b_tr = ei < i_tr
            rows.append(dict(sym=sym, setup=f"{lab} [{wlab}]",
                             n_tr=int(m_tr.sum()), n_va=int(m_va.sum()),
                             sig_gross_tr=sret[m_tr].mean(),
                             base_gross_tr=eret[b_tr].mean(),
                             lift=sret[m_tr].mean() - eret[b_tr].mean(),
                             t=tstat(sret[m_tr]),
                             sig_gross_va=sret[m_va].mean() if m_va.sum() else np.nan))
    df = pd.DataFrame(rows)
    print(f"{'setup':<48}{'n_tr':>6}{'sig gross':>11}{'base gross':>12}"
          f"{'lift':>9}{'t':>7}{'mid gross':>11}")
    for _, r in df.iterrows():
        print(f"{r.setup:<48}{r.n_tr:>6}{r.sig_gross_tr:>11.4f}"
              f"{r.base_gross_tr:>12.4f}{r.lift:>9.4f}{r.t:>7.2f}{r.sig_gross_va:>11.4f}")
    return df


# ---------------------------------------------------------------- Q2
def intraday_drift_profile(d, i_tr, sym):
    print("\n" + "=" * 96)
    print(f"Q2  {sym}: where inside the session does the return live? "
          f"Choosing slice only, gross of costs.")
    print("=" * 96)
    tr = d.iloc[:i_tr]
    r = tr["close"].pct_change() * 100.0
    r[tr["sid"].diff() != 0] = np.nan          # never span a session boundary
    tr = tr.assign(ret=r)
    buckets = [(570, 600, "09:30-10:00"), (600, 630, "10:00-10:30"),
               (630, 660, "10:30-11:00"), (660, 720, "11:00-12:00"),
               (720, 780, "12:00-13:00"), (780, 840, "13:00-14:00"),
               (840, 900, "14:00-15:00"), (900, 930, "15:00-15:30"),
               (930, 960, "15:30-16:00")]
    print(f"{'window':<14}{'bars':>9}{'mean % of price':>18}{'sum over window':>18}{'t':>8}")
    for a, b, lab in buckets:
        m = (tr["mins"] >= a) & (tr["mins"] < b)
        x = tr.loc[m, "ret"].dropna()
        print(f"{lab:<14}{len(x):>9,}{x.mean():>18.5f}{x.sum()/tr['sid'].nunique():>18.5f}"
              f"{tstat(x):>8.2f}")

    # open-to-close versus close-to-open
    g = tr.groupby("sid")
    o = g["open"].first(); c = g["close"].last()
    intraday = (c - o) / o * 100.0
    overnight = (o.shift(-1) - c) / c * 100.0
    print(f"\n  open-to-close (the whole session, gross): mean {intraday.mean():.4f}% of price, "
          f"t={tstat(intraday):.2f}, over {len(intraday):,} sessions")
    print(f"  close-to-next-open (the dark window, gross): mean {overnight.dropna().mean():.4f}% of price, "
          f"t={tstat(overnight.dropna()):.2f}")
    print(f"  a SPY round trip costs 0.0400% of notional. The dark window's gross "
          f"is {overnight.dropna().mean()/0.04:.2f}x that cost, the session's is "
          f"{intraday.mean()/0.04:.2f}x.")


# ---------------------------------------------------------------- Q3
def cost_arithmetic():
    print("\n" + "=" * 96)
    print("Q3  WHAT A TIGHT STOP DOES TO THE COST BAR")
    print("The desk's bar is: profit per trade must be at least 5 times the "
          "round-trip cost, as a % of notional.")
    print("Leverage does NOT help clear it - both sides scale with notional.")
    print("=" * 96)
    print(f"{'stop distance (% of price)':<30}{'cost in R':>12}{'profit needed':>16}"
          f"{'= in R':>10}{'lev @1% risk':>14}")
    for stop in (0.092, 0.137, 0.165, 0.213, 0.50, 1.00, 1.84, 3.12):
        for cost in (0.04,):
            need = 5 * cost
            print(f"{stop:<30.3f}{cost/stop:>12.2f}{need:>15.3f}%{need/stop:>10.2f}"
                  f"{1.0/stop:>13.1f}x")
    print("\nRead the '= in R' column. A 0.092% structural stop, the tightest "
          "the 5-minute chart offers,")
    print("needs the average trade to make 2.17 times its own stop distance, "
          "NET, just to clear the bar.")


# ---------------------------------------------------------------- main
def main():
    for sym in ("SPY", "QQQ"):
        try:
            d = prep(sym, "5m")
        except FileNotFoundError:
            print(f"[skip] no {sym} 5m file")
            continue
        i_tr, i_va = split_60_20_20(len(d))
        print("\n" + "#" * 96)
        print(f"# {sym}  5-minute regular hours: {len(d):,} bars, "
              f"{d['sid'].nunique():,} sessions, "
              f"{d['et'].iloc[0]:%Y-%m-%d} to {d['et'].iloc[-1]:%Y-%m-%d}")
        print(f"# choosing 0-{i_tr:,}   middle {i_tr:,}-{i_va:,}   final 20% never opened")
        print("#" * 96)
        df = signal_edge_no_stop(d, i_tr, i_va, sym)
        df.to_csv(f"{REPO}/step370_table_{sym}_nostop.csv", index=False)
        intraday_drift_profile(d, i_tr, sym)
    cost_arithmetic()


if __name__ == "__main__":
    main()
