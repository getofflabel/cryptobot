"""
step410_setups.py - ROUND 410, JOB 2 PART 4
INTRADAY BREAKOUT SETUPS ON THE AI COMPLEX, COIN-FLIP CONTROLLED.

Research only. No orders of any kind. Nothing live is touched.

WHY THE COIN FLIP IS UNUSUALLY CLEAN HERE
  Part 3 measured that not one name in this basket has a regular-session
  drift worth calling measured - every t-statistic is under 1.1, and two
  are negative. That is a problem for making money and a gift for testing.
  On a daily-bar trend rule the market's own rise floods the result and the
  control has to fight it. Inside the session there is no rise to inherit,
  so if a breakout entry beats random entries here, the entry itself did
  it. Nothing else is available to do it.

THE TRADE
  5-minute bars, regular hours only, long only, ONE trade per session.
  Enter with a market order at the open of the bar after the close breaks
  above the highest high of the last N bars of the same session. Exit at a
  stop placed at chart structure, or flat at the session's last bar,
  whichever comes first. Nothing is ever carried overnight, so the gap
  never touches this trade - which is the one honest advantage a day trade
  has on an instrument that gaps as much as these do.

  One trade per session, always the first signal of the day. That keeps the
  real population and the random population exactly comparable: both take
  one trade per session, from the same set of sessions.

WHAT IS SWEPT AND WHAT LUCK WOULD GIVE
  3 breakout lengths x 2 swing definitions = 6 settings per name. With 6
  settings, roughly 0.3 of them clear the plain 95th percentile of chance
  by luck, and the odds of at least one false winner are about 26%. The bar
  used is therefore the 99.17th percentile of the control, which is the
  95th stretched to cover 6 looks.

  An earlier draft also swept the earliest-entry time, but a breakout
  window of N bars already forbids entries before the session is N bars
  old, so 10:00 and 10:30 gave byte-identical results for every N of 12 or
  more. Sweeping a dimension that does nothing inflates the count of looks
  without buying anything, so it was dropped rather than reported.

SPLIT
  Chosen on the first 60% of sessions. Middle 20% read once, and only for
  the setting that won on the choosing slice. Final 20% never opened.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
from step41_shorts import confirmed_swings
from step410_lib import (REPO, load_5m_rth, split_60_20_20, costs_table,
                         tjr_swings, tstat)

NAMES = ["NVDA", "AMD", "AVGO", "MU", "MSFT", "GOOGL", "META", "AMZN",
         "TSLA", "SMH", "SPY", "QQQ"]
BREAK_N = [6, 12, 24]            # 30, 60, 120 minutes of 5-minute bars
SWINGS = ["TJR", "k3"]
EARLIEST = [600]                 # no entry before 10:00 ET
N_CONFIGS = len(BREAK_N) * len(SWINGS) * len(EARLIEST)
N_FLIPS = 1000
ADJ_BAR = 100.0 * (1 - 0.05 / N_CONFIGS)


def section(t):
    print("\n" + "=" * 88)
    print(t)
    print("=" * 88)


def session_bounds(d):
    """Start and end row index of each session, plus a session id per bar."""
    sid = (d["date"] != d["date"].shift(1)).cumsum().to_numpy() - 1
    n_sess = sid.max() + 1
    starts = np.zeros(n_sess, dtype=int)
    ends = np.zeros(n_sess, dtype=int)
    for s in range(n_sess):
        idx = np.flatnonzero(sid == s)
        starts[s], ends[s] = idx[0], idx[-1]
    return sid, starts, ends


def same_session_stop(d, sid, kind):
    """For every bar t, the most recent confirmed swing low of the SAME
    session that sits below the close of bar t. A day trader who goes flat
    cannot lean on yesterday's low."""
    if kind == "TJR":
        _, sl = tjr_swings(d)
    else:
        _, sl = confirmed_swings(d, 3)
    lv = sl.to_numpy()
    close = d["close"].to_numpy()
    n = len(d)
    out = np.full(n, np.nan)
    hist_p, hist_i = [], []
    cur = -1
    for t in range(n):
        if sid[t] != cur:
            cur = sid[t]; hist_p, hist_i = [], []
        p = close[t]
        for j in range(len(hist_p) - 1, -1, -1):
            if hist_p[j] < p:
                out[t] = hist_p[j]
                break
        if not np.isnan(lv[t]):
            hist_p.append(lv[t]); hist_i.append(t)
    return out


def trade_outcomes(d, sid, ends, stop_lvl, cost_pct):
    """For EVERY bar t, what a long entered at the open of bar t+1 would
    have returned: stopped out at the structural level, or flat at the
    session's last bar. Returned as a percentage of price after costs.
    NaN where the trade is not possible (no structure below, or bar t is
    the last of its session)."""
    o = d["open"].to_numpy(); l = d["low"].to_numpy(); c = d["close"].to_numpy()
    n = len(d)
    half = cost_pct / 2.0 / 100.0
    ret = np.full(n, np.nan)
    stopd = np.full(n, np.nan)
    held = np.full(n, np.nan)
    for t in range(n - 1):
        if sid[t + 1] != sid[t]:
            continue                       # entry would land next session
        stop = stop_lvl[t]
        if np.isnan(stop):
            continue
        entry = o[t + 1]
        if stop >= entry:
            continue
        e = ends[sid[t]]
        exit_px = None
        for j in range(t + 1, e + 1):
            if o[j] <= stop:
                exit_px = o[j]; break      # gapped through: fill at the open
            if l[j] <= stop:
                exit_px = stop; break
        if exit_px is None:
            exit_px = c[e]; j = e
        ret[t] = ((exit_px * (1 - half)) / (entry * (1 + half)) - 1) * 100.0
        stopd[t] = (entry - stop) / entry * 100.0
        held[t] = j - t
    return ret, stopd, held


def first_signal_per_session(sig, eligible, sid, n_sess):
    """Row index of the first bar in each session where the signal fires and
    a trade is possible; -1 if none."""
    out = np.full(n_sess, -1, dtype=int)
    ok = sig & eligible
    idx = np.flatnonzero(ok)
    for i in idx:
        s = sid[i]
        if out[s] == -1:
            out[s] = i
    return out


def main():
    costs = costs_table()
    all_rows = []

    section("INTRADAY BREAKOUT, ONE TRADE PER SESSION, AGAINST A COIN FLIP")
    print("Entry: close breaks the highest high of the last N bars of the same")
    print("session. Stop: last same-session swing low below the entry. Exit:")
    print("stop, or flat at the session close. Never held overnight.")
    print("The control takes ONE random eligible bar in the SAME session, with")
    print("the same stop rule and the same flat-at-the-close exit, so the two")
    print("populations cover exactly the same sessions.")
    print(f"Chance baseline: {N_CONFIGS} settings per name, so about "
          f"{0.05*N_CONFIGS:.1f} of them clear the")
    print(f"plain 95th percentile by luck; the bar used is the {ADJ_BAR:.2f}th.")

    for sym in NAMES:
        try:
            _, rth = load_5m_rth(sym)
        except FileNotFoundError:
            print(f"\n  {sym}: no 5-minute file")
            continue
        cost = costs[sym]["p75"]
        i_tr, i_va = split_60_20_20(len(rth))
        # snap the split to session boundaries
        sid_all, st_all, en_all = session_bounds(rth)
        s_tr, s_va = sid_all[i_tr], sid_all[i_va]

        d = rth
        sid, starts, ends = sid_all, st_all, en_all
        n_sess = sid.max() + 1
        mins = d["mins"].to_numpy()
        high = d["high"].to_numpy()
        close = d["close"].to_numpy()

        print(f"\n  {sym}  5-minute regular-hours bars {len(d):,}, "
              f"{n_sess:,} sessions, round-trip cost {cost:.4f}% of price")
        print(f"    choosing: sessions 0-{s_tr:,}   middle: {s_tr:,}-{s_va:,}   "
              f"final {s_va:,}+ NEVER OPENED")
        print(f"    {'N':>4}{'swing':>7}{'from':>7}{'trades':>8}{'mean%':>9}"
              f"{'t':>7}{'win%':>7}{'stop%':>8}{'chance%':>9}{'pctile':>8}"
              f"{'xcost':>7}")

        best = None
        for kind in SWINGS:
            stop_lvl = same_session_stop(d, sid, kind)
            ret, stopd, held = trade_outcomes(d, sid, ends, stop_lvl, cost)
            possible = ~np.isnan(ret)
            for N in BREAK_N:
                # rolling session-local high of the last N bars, shifted 1
                roll = pd.Series(high).rolling(N).max().shift(1).to_numpy()
                # invalidate where the window crosses a session boundary
                bar_of_sess = np.arange(len(d)) - starts[sid]
                valid = bar_of_sess >= N
                brk = (close > roll) & valid
                for early in EARLIEST:
                    ok_time = mins >= early
                    sig = brk & ok_time
                    elig = possible & ok_time & valid
                    tr_sess = np.arange(n_sess) < s_tr
                    picks = first_signal_per_session(sig, elig, sid, n_sess)
                    real_idx = picks[(picks >= 0) & tr_sess]
                    if len(real_idx) < 30:
                        continue
                    r = ret[real_idx]
                    # ---- coin flip: one random eligible bar in the SAME sessions
                    rng = np.random.default_rng(101)
                    sess_of = sid[real_idx]
                    pool = {}
                    for s in np.unique(sess_of):
                        rows = np.flatnonzero((sid == s) & elig)
                        if len(rows):
                            pool[s] = rows
                    usable = [s for s in sess_of if s in pool]
                    cf_means = np.empty(N_FLIPS)
                    for q in range(N_FLIPS):
                        pick = [pool[s][rng.integers(len(pool[s]))] for s in usable]
                        cf_means[q] = np.nanmean(ret[pick])
                    p = 100.0 * (cf_means < r.mean()).mean()
                    row = dict(symbol=sym, break_n=N, swing=kind, earliest=early,
                               n=len(r), mean_pct=r.mean(), t=tstat(r),
                               win_pct=100 * (r > 0).mean(),
                               stop_pct=np.nanmean(stopd[real_idx]),
                               cf_mean=cf_means.mean(),
                               cf_p95=float(np.percentile(cf_means, 95)),
                               chance_pctile=p, cost_pct=cost,
                               thickness=r.mean() / cost,
                               mean_hold=np.nanmean(held[real_idx]))
                    all_rows.append(row)
                    print(f"    {N:>4}{kind:>7}{early//60:>4}:{early%60:02d}"
                          f"{len(r):>8}{r.mean():>9.4f}{tstat(r):>7.2f}"
                          f"{100*(r>0).mean():>7.1f}{np.nanmean(stopd[real_idx]):>8.3f}"
                          f"{cf_means.mean():>9.4f}{p:>8.1f}"
                          f"{r.mean()/cost:>7.1f}")
                    if best is None or r.mean() > best["mean_pct"]:
                        best = dict(row, kind=kind, N=N, early=early)

        # ------------------------------------------- read the middle once
        if best is None:
            print("    INSUFFICIENT SAMPLE: no setting reached 30 trades")
            continue
        stop_lvl = same_session_stop(d, sid, best["kind"])
        ret, stopd, held = trade_outcomes(d, sid, ends, stop_lvl, cost)
        possible = ~np.isnan(ret)
        roll = pd.Series(high).rolling(best["N"]).max().shift(1).to_numpy()
        bar_of_sess = np.arange(len(d)) - starts[sid]
        valid = bar_of_sess >= best["N"]
        ok_time = mins >= best["early"]
        sig = (close > roll) & valid & ok_time
        elig = possible & ok_time & valid
        picks = first_signal_per_session(sig, elig, sid, n_sess)
        va_sess = (np.arange(n_sess) >= s_tr) & (np.arange(n_sess) < s_va)
        vi = picks[(picks >= 0) & va_sess]
        chosen = (f"N={best['N']} {best['kind']} from "
                  f"{best['early']//60}:{best['early']%60:02d}")
        if len(vi) >= 8:
            rv = ret[vi]
            rng = np.random.default_rng(202)
            sess_of = sid[vi]
            pool = {}
            for s in np.unique(sess_of):
                rows = np.flatnonzero((sid == s) & elig)
                if len(rows):
                    pool[s] = rows
            usable = [s for s in sess_of if s in pool]
            cfm = np.empty(N_FLIPS)
            for q in range(N_FLIPS):
                pick = [pool[s][rng.integers(len(pool[s]))] for s in usable]
                cfm[q] = np.nanmean(ret[pick])
            p = 100.0 * (cfm < rv.mean()).mean()
            verdict = ("SURVIVES" if p >= ADJ_BAR and rv.mean() / cost >= 5
                       else "fails the coin flip" if p < ADJ_BAR else "too thin")
            print(f"    middle slice, chosen setting {chosen}: "
                  f"n={len(rv)} mean {rv.mean():+.4f}% t={tstat(rv):.2f} "
                  f"chance {cfm.mean():+.4f}% -> {p:.1f}th percentile, "
                  f"{rv.mean()/cost:.1f}x cost   {verdict}")
            all_rows.append(dict(symbol=sym, break_n=best["N"], swing=best["kind"],
                                 earliest=best["early"], slice="MIDDLE",
                                 n=len(rv), mean_pct=rv.mean(), t=tstat(rv),
                                 cf_mean=cfm.mean(), chance_pctile=p,
                                 cost_pct=cost, thickness=rv.mean() / cost,
                                 verdict=verdict))
        else:
            print(f"    middle slice: INSUFFICIENT SAMPLE ({len(vi)} trades)")

    out = pd.DataFrame(all_rows)
    out.to_csv(f"{REPO}/step410_table_setups.csv", index=False)

    section("SUMMARY")
    ch = out[out.get("slice").isna()] if "slice" in out.columns else out
    print(f"settings run across all names: {len(ch)}")
    print(f"settings with a positive mean after costs: {(ch.mean_pct > 0).sum()}")
    print(f"settings clearing 5 times the round-trip cost: "
          f"{(ch.thickness >= 5).sum()}")
    print(f"settings clearing the sweep-adjusted {ADJ_BAR:.2f}th percentile of the")
    print(f"coin flip: {(ch.chance_pctile >= ADJ_BAR).sum()}")
    print(f"expected by luck alone at that bar across {len(ch)} settings: "
          f"{len(ch)*0.05/N_CONFIGS:.2f}")
    print("\nwrote step410_table_setups.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
