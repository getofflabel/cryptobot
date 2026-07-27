"""
step430_levels.py - MEASURED PROPERTIES OF THE MARKET, round 430.

DESCRIPTIVE ONLY.  There is no strategy in this file, no verdict, and
nothing to pass or fail.  It measures three things our build will need
whatever the rules turn out to be:

  A. How often each kind of level gets SWEPT - price trades through it
     and closes back - versus simply BROKEN, versus never touched at all,
     within five days of the level forming.  Per week, so we can see how
     many opportunities a chart even offers.

  B. The distance from a swept level to the point where the opposite
     trend confirms (a higher low then a higher high after a swept low;
     a lower high then a lower low after a swept high).  This is the stop
     distance, and position size is dollars-risked divided by it.

  C. The distance from that confirmation point to the nearest UNSWEPT
     level ahead, and to the nearest STACKED unswept pool (two or more
     levels at the same price with none taken out).  This is what the
     chart offers as a target, in percent of price and as a multiple of
     the risk.

LEVEL KINDS MEASURED
  Two-candle swing highs and lows read off the 5-minute, 15-minute,
  1-hour and 4-hour charts; the Asia, London and New York session highs
  and lows; and the prior day's high and low.

UNITS
  Every "%" is a PRICE move - how far the price travelled - never a
  change in the value of a position.  Costs, where mentioned: round trip,
  no commission, from round 410's measurement of ~700k real quoted
  spreads, SPY 0.0035% of price.  BloFin crypto is 0.06% per side.

RESEARCH ONLY.  Touches no bot, no live file, places no order.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
from step430_lib import (REPO, htf_new_levels, load_5m, split_60_20_20,
                         tag_sessions, tjr_swings)

SWEEP_WINDOW = 12     # bars a level may stay pierced and still count as swept
CONF_WINDOW = 24      # bars allowed for the opposite trend to confirm
LIFE_DAYS = 5         # a level is followed for five days, then written off
EQ_TOL_PCT = 0.05     # two levels this close in price count as stacked


# ---------------------------------------------------------------- levels
def session_levels(d: pd.DataFrame):
    """Session and prior-day highs and lows, each stamped on the first
    5-minute bar AFTER the window that produced it has finished, so the
    level is knowable at that bar's close and never earlier."""
    d = tag_sessions(d)
    n = len(d)
    m = d["mins"].to_numpy()
    out = {}
    windows = [("asia", (m >= 1080) | (m < 180), 180),
               ("london", (m >= 180) & (m < 510), 510),
               ("ny", (m >= 570) & (m < 1020), 1020)]
    for name, mask, end_min in windows:
        hi = np.full(n, np.nan); lo = np.full(n, np.nan)
        sub = d[mask]
        g = sub.groupby("sday").agg(H=("high", "max"), L=("low", "min"))
        # first bar at or after the window's end, on the same session day
        after = d[m >= end_min] if end_min < 1440 else d.iloc[[]]
        firsts = after.groupby("sday").head(1)
        for r in firsts.itertuples():
            if r.sday in g.index:
                hi[r.Index] = g.at[r.sday, "H"]
                lo[r.Index] = g.at[r.sday, "L"]
        out[f"{name} session"] = (hi, lo)
    # prior day, stamped on the first bar of the next session day
    dayg = d.groupby("sday").agg(H=("high", "max"), L=("low", "min"))
    days = list(dayg.index)
    prevH = {days[i]: dayg["H"].iloc[i - 1] for i in range(1, len(days))}
    prevL = {days[i]: dayg["L"].iloc[i - 1] for i in range(1, len(days))}
    hi = np.full(n, np.nan); lo = np.full(n, np.nan)
    for r in d.groupby("sday").head(1).itertuples():
        if r.sday in prevH:
            hi[r.Index] = prevH[r.sday]; lo[r.Index] = prevL[r.sday]
    out["prior day"] = (hi, lo)
    return out


# ------------------------------------------------------- level outcomes
def level_outcomes(d, new_high, new_low, life_bars, sweep_window=SWEEP_WINDOW):
    """What happens to every level that forms, followed for life_bars.

    SWEPT    price traded through it and closed back on the original side
             within sweep_window bars
    BROKEN   price traded through and did NOT close back inside the window
    UNTOUCHED price never reached it while we followed it
    """
    hi = d["high"].to_numpy(); lo = d["low"].to_numpy()
    cl = d["close"].to_numpy()
    n = len(d)
    recs = []
    live_lo, live_hi = [], []          # [price, born_bar]
    pier_lo, pier_hi = [], []          # [price, born, pierce_bar, extreme]
    for t in range(n):
        # resolve levels currently pierced
        keep = []
        for st in pier_lo:
            st[3] = min(st[3], lo[t])
            if cl[t] > st[0]:
                recs.append(("low", st[0], st[1], st[2], "swept",
                             (st[0] - st[3]) / st[0] * 100.0))
            elif t - st[2] >= sweep_window:
                recs.append(("low", st[0], st[1], st[2], "broken",
                             (st[0] - st[3]) / st[0] * 100.0))
            else:
                keep.append(st)
        pier_lo = keep
        keep = []
        for st in pier_hi:
            st[3] = max(st[3], hi[t])
            if cl[t] < st[0]:
                recs.append(("high", st[0], st[1], st[2], "swept",
                             (st[3] - st[0]) / st[0] * 100.0))
            elif t - st[2] >= sweep_window:
                recs.append(("high", st[0], st[1], st[2], "broken",
                             (st[3] - st[0]) / st[0] * 100.0))
            else:
                keep.append(st)
        pier_hi = keep
        # new pierces, and expiries
        keep = []
        for st in live_lo:
            if lo[t] < st[0]:
                pier_lo.append([st[0], st[1], t, lo[t]])
            elif t - st[1] >= life_bars:
                recs.append(("low", st[0], st[1], -1, "untouched", np.nan))
            else:
                keep.append(st)
        live_lo = keep
        keep = []
        for st in live_hi:
            if hi[t] > st[0]:
                pier_hi.append([st[0], st[1], t, hi[t]])
            elif t - st[1] >= life_bars:
                recs.append(("high", st[0], st[1], -1, "untouched", np.nan))
            else:
                keep.append(st)
        live_hi = keep
        v = new_low[t]
        if not np.isnan(v) and v < cl[t]:
            live_lo.append([v, t])
        v = new_high[t]
        if not np.isnan(v) and v > cl[t]:
            live_hi.append([v, t])
    return pd.DataFrame(recs, columns=["kind", "price", "born", "pierce",
                                       "outcome", "overshoot_pct"])


# --------------------------------------------- confirmation + targets
def confirm_and_targets(d, new_high, new_low, sh5, sl5, life_bars,
                        sweep_window=SWEEP_WINDOW, conf_window=CONF_WINDOW,
                        eq_tol=EQ_TOL_PCT):
    """For every swept level, walk forward for the opposite trend to form
    and record the distances the chart offers.

    Replays the live pool of unswept levels bar by bar, so the "nearest
    unswept level ahead" at the confirmation bar uses only levels that had
    formed and had NOT been taken out by that bar.  Nothing here reads a
    price printed after the bar it is stamped on.
    """
    hi = d["high"].to_numpy(); lo = d["low"].to_numpy()
    cl = d["close"].to_numpy(); op = d["open"].to_numpy()
    n = len(d)
    # live levels carry their birth bar so they can be written off after
    # life_bars, exactly as in the outcome table.  Without that, a level
    # from years ago stays "unswept" for ever and the nearest-target
    # distances become meaningless.
    live_lo, live_hi = [], []      # [price, born]
    pier_lo, pier_hi = {}, {}
    sweeps = []
    snap = {}                      # bar -> (unswept lows, unswept highs)
    for t in range(n):
        for L in list(pier_lo):
            st = pier_lo[L]; st[1] = min(st[1], lo[t])
            if cl[t] > L:
                sweeps.append((t, 1, L, st[1])); del pier_lo[L]
            elif t - st[0] >= sweep_window:
                del pier_lo[L]
        for L in list(pier_hi):
            st = pier_hi[L]; st[1] = max(st[1], hi[t])
            if cl[t] < L:
                sweeps.append((t, -1, L, st[1])); del pier_hi[L]
            elif t - st[0] >= sweep_window:
                del pier_hi[L]
        pierced = [e for e in live_lo if lo[t] < e[0]]
        keep = [e for e in live_lo if not (lo[t] < e[0])
                and t - e[1] < life_bars]
        live_lo = keep
        if pierced:
            L = max(e[0] for e in pierced)
            if cl[t] > L:
                sweeps.append((t, 1, L, lo[t]))
            else:
                pier_lo[L] = [t, lo[t]]
        pierced = [e for e in live_hi if hi[t] > e[0]]
        keep = [e for e in live_hi if not (hi[t] > e[0])
                and t - e[1] < life_bars]
        live_hi = keep
        if pierced:
            L = min(e[0] for e in pierced)
            if cl[t] < L:
                sweeps.append((t, -1, L, hi[t]))
            else:
                pier_hi[L] = [t, hi[t]]
        v = new_low[t]
        if not np.isnan(v) and v < cl[t]:
            live_lo.append([v, t])
        v = new_high[t]
        if not np.isnan(v) and v > cl[t]:
            live_hi.append([v, t])
        snap[t] = (tuple(e[0] for e in live_lo),
                   tuple(e[0] for e in live_hi))

    rows = []
    for (s, side, level, extreme) in sweeps:
        rec = dict(sweep_bar=s, side=side, level=level, extreme=extreme,
                   confirmed=False)
        found_hl = False; ref = np.nan
        best = -np.inf if side > 0 else np.inf
        run = -np.inf if side > 0 else np.inf
        j = s + 1
        while j < n and (j - s) <= conf_window:
            if side > 0:
                if lo[j] < extreme:
                    break
                run = max(run, hi[j])
                if not np.isnan(sh5[j]):
                    best = max(best, sh5[j])
                if not found_hl:
                    if not np.isnan(sl5[j]) and sl5[j] > extreme:
                        found_hl = True
                        ref = best if np.isfinite(best) else run
                elif cl[j] > ref:
                    rec.update(confirmed=True, conf_bar=j, wait=j - s)
                    break
            else:
                if hi[j] > extreme:
                    break
                run = min(run, lo[j])
                if not np.isnan(sl5[j]):
                    best = min(best, sl5[j])
                if not found_hl:
                    if not np.isnan(sh5[j]) and sh5[j] < extreme:
                        found_hl = True
                        ref = best if np.isfinite(best) else run
                elif cl[j] < ref:
                    rec.update(confirmed=True, conf_bar=j, wait=j - s)
                    break
            j += 1
        if not rec["confirmed"]:
            rows.append(rec); continue
        cb = rec["conf_bar"]
        fill = op[min(cb + 1, n - 1)]           # the order fills next open
        risk = abs(fill - extreme) / fill * 100.0
        rec["fill"] = fill
        rec["risk_pct"] = risk
        rec["level_to_conf_pct"] = abs(fill - level) / fill * 100.0
        lows_, highs_ = snap[cb]
        ahead = ([p for p in highs_ if p > fill] if side > 0
                 else [p for p in lows_ if p < fill])
        if ahead:
            nearest = min(ahead) if side > 0 else max(ahead)
            rec["target_pct"] = abs(nearest - fill) / fill * 100.0
            rec["target_r"] = (rec["target_pct"] / risk) if risk > 0 else np.nan
        # stacked pool: two or more unswept levels within eq_tol of each other
        arr = np.sort(np.array(ahead)) if ahead else np.array([])
        stacked = []
        i = 0
        while i < len(arr):
            k = i
            while (k + 1 < len(arr) and
                   abs(arr[k + 1] - arr[i]) / arr[i] * 100.0 <= eq_tol):
                k += 1
            if k > i:
                stacked.append(float(np.mean(arr[i:k + 1])))
            i = k + 1
        if stacked:
            ns = min(stacked) if side > 0 else max(stacked)
            rec["stack_pct"] = abs(ns - fill) / fill * 100.0
            rec["stack_r"] = (rec["stack_pct"] / risk) if risk > 0 else np.nan
            rec["n_stacked_pools"] = len(stacked)
        rows.append(rec)
    cols = ["sweep_bar", "side", "level", "extreme", "confirmed", "conf_bar",
            "wait", "fill", "risk_pct", "level_to_conf_pct", "target_pct",
            "target_r", "stack_pct", "stack_r", "n_stacked_pools"]
    return pd.DataFrame(rows).reindex(columns=cols)


# ------------------------------------------------------------------ main
def q(series, p):
    s = pd.Series(series).dropna()
    return float(np.percentile(s, p)) if len(s) else np.nan


def main():
    fh = open(f"{REPO}/step430_levels_out.txt", "w")
    W = lambda s: (print(s), fh.write(s + "\n"))
    freq_rows, dist_rows = [], []

    specs = [("SPY", "alpaca"), ("QQQ", "alpaca"), ("BTCUSDT", "bybit")]
    for sym, src in specs:
        d = load_5m(sym, src)
        n = len(d)
        i_val, i_seal = split_60_20_20(n)
        days = max((d["et"].max() - d["et"].min()).days, 1)
        bars_per_day = n / days
        life = int(bars_per_day * LIFE_DAYS)
        sh5, sl5 = tjr_swings(d)
        W("")
        W("=" * 76)
        W(f"{sym} ({src})   5-minute bars {n:,}   "
          f"{d['et'].min().date()} .. {d['et'].max().date()}")
        W(f"  a level is followed for {LIFE_DAYS} days "
          f"({life:,} five-minute bars) and then written off")
        W(f"  measured on the first 80% of the data only; the last 20% "
          f"({d['et'].iloc[i_seal].date()} onward) is not opened")
        W("=" * 76)

        kinds = {}
        for tf, lbl in [(5, "5-minute swing"), (15, "15-minute swing"),
                        (60, "1-hour swing"), (240, "4-hour swing")]:
            kinds[lbl] = (htf_new_levels(d, tf) if tf > 5
                          else (np.where(np.isnan(sh5), np.nan, sh5),
                                np.where(np.isnan(sl5), np.nan, sl5)))
        kinds.update(session_levels(d))

        W("")
        W("A. WHAT HAPPENS TO A LEVEL ONCE IT FORMS")
        W(f"   {'level kind':<18} {'formed':>8} {'/week':>7} "
          f"{'swept':>7} {'broken':>7} {'untouched':>10} "
          f"{'sweeps/wk':>10} {'median hrs':>11}")
        weeks = days / 7.0 * 0.8          # we only read the first 80%
        for lbl, (nh, nl) in kinds.items():
            nh2 = nh.copy(); nl2 = nl.copy()
            nh2[i_seal:] = np.nan; nl2[i_seal:] = np.nan
            oc = level_outcomes(d.iloc[:i_seal], nh2[:i_seal], nl2[:i_seal],
                                life)
            tot = len(oc)
            if tot == 0:
                continue
            sw = (oc["outcome"] == "swept").mean() * 100
            br = (oc["outcome"] == "broken").mean() * 100
            un = (oc["outcome"] == "untouched").mean() * 100
            swept = oc[oc["outcome"] == "swept"]
            age_h = ((swept["pierce"] - swept["born"]) * 5 / 60.0).median()
            W(f"   {lbl:<18} {tot:>8,} {tot/weeks:>7.1f} "
              f"{sw:>6.1f}% {br:>6.1f}% {un:>9.1f}% "
              f"{len(swept)/weeks:>10.1f} {age_h:>11.1f}")
            freq_rows.append(dict(symbol=sym, level_kind=lbl, n_formed=tot,
                                  formed_per_week=tot / weeks,
                                  pct_swept=sw, pct_broken=br,
                                  pct_untouched=un,
                                  sweeps_per_week=len(swept) / weeks,
                                  median_hours_to_sweep=age_h,
                                  median_overshoot_pct=swept["overshoot_pct"].median()))

        W("")
        W("B + C. DISTANCES, in percent of PRICE (a price move, not a")
        W("       change in position value).  'risk' is the distance from")
        W("       the fill to the swept extreme - the stop.  'nearest")
        W("       unswept' and 'nearest stacked pool' are what the chart")
        W("       offers ahead of the fill at the moment it confirms.")
        W(f"   {'level kind':<18} {'sweeps':>7} {'conf%':>6} "
          f"{'risk med':>9} {'risk p25-p75':>14} {'wait':>6} "
          f"{'unswept med':>12} {'as xrisk':>9} {'stack med':>10} "
          f"{'as xrisk':>9} {'has stack':>10}")
        for lbl, (nh, nl) in kinds.items():
            nh2 = nh[:i_seal].copy(); nl2 = nl[:i_seal].copy()
            ct = confirm_and_targets(d.iloc[:i_seal], nh2, nl2,
                                     sh5[:i_seal], sl5[:i_seal], life)
            if len(ct) == 0:
                continue
            c = ct[ct["confirmed"]]
            if len(c) < 30:
                W(f"   {lbl:<18} {len(ct):>7,}  only {len(c)} confirmations "
                  f"- INSUFFICIENT SAMPLE, not reported")
                continue
            W(f"   {lbl:<18} {len(ct):>7,} {len(c)/len(ct)*100:>5.1f}% "
              f"{c['risk_pct'].median():>8.3f}% "
              f"{q(c['risk_pct'],25):>6.3f}-{q(c['risk_pct'],75):<7.3f} "
              f"{c['wait'].median():>5.0f}b "
              f"{c['target_pct'].median():>11.3f}% "
              f"{c['target_r'].median():>8.2f}x "
              f"{c['stack_pct'].median():>9.3f}% "
              f"{c['stack_r'].median():>8.2f}x "
              f"{c['stack_pct'].notna().mean()*100:>9.1f}%")
            dist_rows.append(dict(
                symbol=sym, level_kind=lbl, n_sweeps=len(ct),
                pct_confirmed=len(c) / len(ct) * 100.0,
                risk_med_pct=c["risk_pct"].median(),
                risk_p25=q(c["risk_pct"], 25), risk_p75=q(c["risk_pct"], 75),
                level_to_conf_med_pct=c["level_to_conf_pct"].median(),
                wait_bars_med=c["wait"].median(),
                nearest_unswept_med_pct=c["target_pct"].median(),
                nearest_unswept_med_xrisk=c["target_r"].median(),
                stacked_pool_med_pct=c["stack_pct"].median(),
                stacked_pool_med_xrisk=c["stack_r"].median(),
                pct_with_stack=c["stack_pct"].notna().mean() * 100.0))

    pd.DataFrame(freq_rows).to_csv(f"{REPO}/step430_level_frequency.csv",
                                   index=False)
    pd.DataFrame(dist_rows).to_csv(f"{REPO}/step430_level_distances.csv",
                                   index=False)
    W("")
    W("wrote step430_level_frequency.csv and step430_level_distances.csv")
    fh.close()


if __name__ == "__main__":
    main()
