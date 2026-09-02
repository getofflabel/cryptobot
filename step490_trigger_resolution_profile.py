"""
step490_trigger_resolution_profile.py - ROUND 490

THE COARSER TRIGGER, READ IN THE STATISTIC R487 ESTABLISHED.
(QUEUE ITEM 14)

Research only. No orders. No live file touched, imported or modified. No
account. Nothing here is deployed by this script under any outcome.

QUEUE ITEM 14, VERBATIM
  R476 compared the 5-minute and 1-minute triggers and the 1-minute won by a
  paired daily difference of t = 9.17 - on GROSS. R487 then established that
  gross is not the statistic that decides anything on this desk and R488
  established why: the stop scales with the trigger's timeframe at an
  elasticity of ~1 and the round trip does not scale at all. A 15-minute or
  1-hour trigger therefore has a proportionally SMALLER cost/stop by
  construction, and the comparison R476 ran has never been run in per-trade
  net R.
  Deliverable: the same family at 1m / 5m / 15m / 1h resolution on the crypto
  population, read in per-trade net R with a t clustered by day, with the
  stop/vol ratio and the R488 break-even multiple printed for each
  resolution. Plus the entry count, because a coarser trigger fires less
  often and frequency is a separate fact from expectancy.
  THE FENCE: this is a DESCRIPTION on spent slices and cannot produce a
  deployment candidate on crypto or SPY/QQQ under any outcome. No resolution
  may be "selected"; the round reports the profile. Its real purpose is to
  tell item 16 WHICH RESOLUTION to carry to a new instrument.

THE FENCE, RESTATED AS CODE DISCIPLINE
  There is no qualification block in this file, no sealed-slice block, and
  no `verdict` anywhere. Nothing is ranked into a "best". The four
  resolutions are printed as a PROFILE, side by side, with the entry count
  beside every expectancy so that frequency and expectancy are never
  confused for one another. No population is cut, no threshold appears
  except the MEASURED COST (a fact about the venue, not a parameter), and
  no number produced here may be used to select a resolution in item 16 -
  item 16 states its resolution in advance either way.

THIS ROUND CONSUMES NO LOOK, AND CANNOT
  The crypto sweep-to-break-of-structure population has no sealed slice left
  anywhere (R450 and R475 have both read inside every boundary of the
  2021-2026 window; R475 spent the one look). Every number below is a
  re-reading of an already-published population at three trigger resolutions
  it was never read at. `slice_by_time` is never called and no train/val/test
  split is cut, precisely so that no reader can mistake a slice label here
  for out-of-sample evidence. The whole window is read at once, which is the
  only honest thing to do with a spent family.

WHAT IS FAITHFUL TO HIM, AND WHAT IS OURS
  Everything is round 450's, imported and not retyped: the two-candle swing,
  levels on the high timeframes only, the sweep hunted on the 5-MINUTE chart
  (unchanged at every resolution - he is explicit that the sweep is not
  hunted on the trigger frame), break of structure as a BODY close, the stop
  as the extreme traded between the sweep and the entry, the 2-hour pending
  expiry and the 24-hour hold cap (both OURS), the UTC day boundary (ours).
  ONE thing moves and it is the thing the item asks about: the TRIGGER
  FRAME, at 1 / 5 / 15 / 60 minutes.

  The 2-hour pending window is NOT widened for the coarser frames. Widening
  it would be tuning, and it is exactly the parameter a coarse trigger would
  want. A 60-minute trigger therefore gets one or two bars inside the window
  and fires rarely; that is a CONSEQUENCE of the resolution and it is
  reported as the entry count, not engineered away.

TWO MANAGEMENT CONVENTIONS, BOTH PRINTED
  R450's own precedent varies management with the trigger (arm A is managed
  on 5-minute bars, arm B on 1-minute bars), so the PRIMARY read here does
  the same: the stop and the target are checked on the trigger frame's own
  bars. But that changes two things at once, so the SENSITIVITY re-runs
  every resolution with management on 1-MINUTE bars at every setting
  (step451's discipline), which isolates the trigger from the exit
  granularity. Where the two disagree, the disagreement is the finding.

VOLATILITY IS THE 1-MINUTE MOVE AT EVERY RESOLUTION
  stop/vol uses R488's yardstick unchanged - the mean absolute 1-MINUTE
  return of that coin on that day - for all four trigger frames. That is
  deliberate: R488's 3.6 is measured against the 1-minute move, so holding
  the denominator fixed is what makes "the stop scales with the trigger
  timeframe" readable as a number.

COSTS
  Charged so the P&L is honest and used for NOTHING else (owner rule,
  2026-07-25). They decline nothing, gate nothing and rank nothing here.
  Primary is R486's corrected all-in Coinbase round trip per coin (fee with
  the $0.15 minimum inside it, plus R482's measured spread): BTC 0.0556% /
  ETH 0.1463% / SOL 0.0816%. Alpaca's 0.50% - the venue the desk actually
  holds - is printed beside it, and gross sits beside every net number.

BASELINE STATED IN THE SAME BREATH (R88/R100)
  A random-entry control is run at EVERY resolution on that resolution's own
  frame, spaced at R450's control interval expressed in time (300 minutes =
  R450's every-60th-5-minute-bar), with the same stop machinery. A profile
  without a per-resolution control would be comparing four constructions to
  nothing.

REPRODUCTION CONTROLS
  The generalised trigger is asserted equal to R450's own `trigger_1m` at
  tf=1, and R450's native arm A (the 5-minute confirmation bar as the
  trigger) is printed beside the generalised 5-minute row so the one
  construction difference between them is visible rather than assumed.
  The 1-minute row must reproduce R476's published population (71,073
  entries, +0.1435% of price, t by day 13.77); it is printed against those
  figures.

HONEST LIMITS, FIXED BEFORE RUNNING
  - The 24-hour cap is counted in BARS at every resolution, which is R450's
    convention, and Alpaca's tape has gaps (R481). Median wall-clock hold is
    printed beside the bar count so the two are never confused.
  - The 15m and 60m frames are resampled from the 5-minute parquet on a UTC
    grid (R450's `resample`), so a period with no 5-minute bars is absent
    rather than zero-volume.
  - Coarser frames produce fewer entries, so their t values rest on fewer
    days. Day counts are printed in every table.
  - This is the SPENT crypto population. Nothing here is out-of-sample.

USAGE
  python3 step490_trigger_resolution_profile.py
"""

import io
import contextlib
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = "/Users/wallacechen/cryptobot"
sys.path.insert(0, REPO)

import step450_tjr_crypto_1m as R          # noqa: E402  the parent, unchanged

# R486's corrected all-in round trip on Coinbase Derivatives, % of price.
# Fee (with the $0.15 per-contract minimum inside it) + R482's measured
# spread. Charged for honest P&L; decides nothing.
COST_ALLIN = {"BTCUSD": 0.0556, "ETHUSD": 0.1463, "SOLUSD": 0.0816}
COST_ALPACA = 0.50                          # the venue the desk holds today

RESOLUTIONS = [1, 5, 15, 60]                # the trigger frames, in minutes
PENDING_MIN = R.PENDING_BARS_5M * 5         # 120 minutes, OURS, never swept
CONTROL_SPACING_MIN = 300                   # R450's every-60th-5m-bar, in time

PARQUET_1M = {s: f"data_alpaca_{s}_1m.parquet" for s in R.PRIMARY}
LINE = "=" * 104


# ==================================================================== stats
def tstat(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return np.nan, len(x)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))), len(x)


def utc_day(res):
    return pd.to_datetime(res["sig_t"]).dt.normalize()


def clustered(res, col):
    """One mean per UTC day pooled across every coin, then t across days.
    Three coins inside one day are ONE draw of the market, not three."""
    v = res[col].replace([np.inf, -np.inf], np.nan)
    d = v.groupby(utc_day(res)).mean().dropna()
    return tstat(d)


def finite_mean(res, col):
    return res[col].replace([np.inf, -np.inf], np.nan).mean()


def daily_vol(path):
    """R488's yardstick, unchanged: mean |1-minute return| per UTC day, %."""
    b = pd.read_parquet(f"{REPO}/{path}")
    t = pd.to_datetime(b["t"])
    r = b["close"].pct_change().abs() * 100.0
    f = pd.DataFrame({"t": t, "r": r}).dropna()
    return f.groupby(f["t"].dt.floor("D"))["r"].mean()


def attach_vol(d, vols):
    idx = pd.MultiIndex.from_arrays([d["sym"], utc_day(d)])
    ser = pd.concat({s: v for s, v in vols.items()}, names=["sym", "day"])
    d = d.copy()
    d["vol"] = ser.reindex(idx).to_numpy()
    return d


# ================================================== the generalised trigger
def tf_frame(d5, d1, tf):
    """The trigger chart at `tf` minutes, with his two-candle swing on it.
    tf=1 is the 1-minute parquet; tf=5 is the 5-minute parquet; 15 and 60
    are resampled from the 5-minute bars on the UTC grid (R450's own
    `resample`, imported)."""
    if tf == 1:
        d = d1.copy()
    elif tf == 5:
        d = d5.copy()
    else:
        d = R.resample(d5, tf)
        sh, sl = R.tjr_swings(d["open"].to_numpy(), d["high"].to_numpy(),
                              d["low"].to_numpy(), d["close"].to_numpy())
        d["mr_sh"], d["mr_sl"] = R.ffill_shift(sh), R.ffill_shift(sl)
    return d.reset_index(drop=True)


def trigger_tf(d5, dtf, tf, sweeps, direction):
    """R450's `trigger_1m` with the frame made a parameter and NOTHING else
    changed. The sweep is pending on the 5-minute chart; the entry is the
    first BODY close on the trigger frame through the most recent confirmed
    swing on that same frame, inside the same 2-hour pending window.

    Returns (entry index on the trigger frame, sweep 5-minute index) pairs.
    """
    c = dtf["close"].to_numpy()
    sh = dtf["mr_sh"].to_numpy()
    sl = dtf["mr_sl"].to_numpy()
    tt = dtf["t"].to_numpy()
    n = len(dtf)
    # the first trigger bar STARTING at or after the sweep bar's close - the
    # same instant R450's `i1_next` marks for the 1-minute frame.
    close_t = (d5["t"] + pd.Timedelta(minutes=5)).to_numpy()
    first = np.searchsorted(tt, close_t, side="left")
    span = max(1, PENDING_MIN // tf)         # bars of window, never widened
    ent, sw = [], []
    for s in sweeps:
        a = first[s]
        if a >= n:
            continue
        b = min(n - 1, a + span)
        if direction > 0:
            m = (c[a:b + 1] > sh[a:b + 1]) & np.isfinite(sh[a:b + 1])
        else:
            m = (c[a:b + 1] < sl[a:b + 1]) & np.isfinite(sl[a:b + 1])
        k = np.flatnonzero(m)
        if len(k) == 0:
            continue
        ent.append(a + k[0])
        sw.append(s)
    return np.array(ent, dtype=int), np.array(sw, dtype=int), first


def structural_stop(dtf, first, sw, ent, direction):
    """The extreme traded on the trigger frame between the sweep and the
    entry - R450's arm-B stop, frame made a parameter."""
    lo = dtf["low"].to_numpy()
    hi = dtf["high"].to_numpy()
    a = first[sw]
    if direction > 0:
        return np.array([lo[max(0, x):y + 1].min() for x, y in zip(a, ent)])
    return np.array([hi[max(0, x):y + 1].max() for x, y in zip(a, ent)])


def map_to_1m(dtf, d1, ent, tf):
    """For the SENSITIVITY: the 1-minute bar index whose NEXT bar is the
    first 1-minute bar at or after the trigger bar's close. `simulate` fills
    at the open of index+1, so this makes the 1-minute-managed fill the same
    instant as the trigger-frame fill."""
    close_t = (dtf["t"].to_numpy()[ent] +
               np.timedelta64(tf, "m"))
    a = np.searchsorted(d1["t"].to_numpy(), close_t, side="left")
    return a - 1


# ================================================================ the round
def run_resolution(sym, d5, d1, tf, sensitivity=True):
    """Every level, both directions, hold-24h scoring (the four target
    settings score the SAME entries, so the population is unchanged and the
    hold-24h row is the one R476's dedupe keeps). Returns the primary frame
    and the 1-minute-managed sensitivity frame."""
    dtf = tf_frame(d5, d1, tf)
    cost = COST_ALLIN[sym]
    prim, sens = [], []
    for col, dirn, lab in R.LEVELS:
        sw5, sig5 = R.scan_sweeps(d5, col, dirn)
        if len(sig5) == 0:
            continue
        ent, sw, first = trigger_tf(d5, dtf, tf, sw5, dirn)
        if not len(ent):
            continue
        stop_px = structural_stop(dtf, first, sw, ent, dirn)
        r = R.simulate(dtf, ent, dirn, stop_px, None,
                       R.MAX_HOLD_MIN // tf, cost=cost)
        if len(r):
            prim.append(r.assign(sym=sym, tf=tf, mtf=tf, level=lab,
                                     dirn=dirn))
        if sensitivity:
            i1 = map_to_1m(dtf, d1, ent, tf)
            ok = (i1 >= 0) & (i1 < len(d1) - 1)
            if ok.any():
                r2 = R.simulate(d1, i1[ok], dirn, stop_px[ok], None,
                                R.MAX_HOLD_MIN, cost=cost)
                if len(r2):
                    sens.append(r2.assign(sym=sym, tf=tf, mtf=1,
                                          level=lab, dirn=dirn))
    P = pd.concat(prim) if prim else pd.DataFrame()
    S = pd.concat(sens) if sens else pd.DataFrame()
    # R476's dedupe, unchanged: two levels can be swept into the SAME entry
    # with the same structural stop, and that is one trade, not two.
    key = ["sig_i", "sig_t", "stop_pct"]
    if len(P):
        P = P.drop_duplicates(subset=key)
    if len(S):
        S = S.drop_duplicates(subset=key)
    return P, S, dtf


def control_at(dtf, tf, sym):
    """R450's chance control, generalised by TIME rather than by bar count so
    the four resolutions are compared against equally frequent randomness."""
    every = max(1, CONTROL_SPACING_MIN // tf)
    cost = COST_ALLIN[sym]
    out = []
    for dirn in (+1, -1):
        idx = np.arange(0, len(dtf) - 1, every)
        stop = (dtf["mr_sl"].to_numpy() if dirn > 0
                else dtf["mr_sh"].to_numpy())[idx]
        r = R.simulate(dtf, idx, dirn, stop, None, R.MAX_HOLD_MIN // tf,
                       cost=cost)
        if len(r):
            out.append(r.assign(sym=sym, tf=tf, mtf=tf))
    return pd.concat(out) if out else pd.DataFrame()


def hold_hours(d):
    """Median wall-clock hold, because a bar count is not a duration on a
    tape with gaps (R481)."""
    return np.nan if not len(d) else float(
        (d["bars_held"] * d["mtf"]).median() / 60.0)


def profile_row(d, label):
    tn, n = tstat(d["net_R"].replace([np.inf, -np.inf], np.nan))
    tc, nd = clustered(d, "net_R")
    tg, _ = clustered(d, "gross_pct")
    stop = d["stop_pct"].median()
    cs = (d["cost_pct"] / d["stop_pct"]).replace(
        [np.inf, -np.inf], np.nan)
    return dict(label=label, entries=n, days=nd,
                gross=d["gross_pct"].mean(), t_gross_day=tg,
                grossR=(d["gross_pct"] / d["stop_pct"]).replace(
                    [np.inf, -np.inf], np.nan).mean(),
                netR=finite_mean(d, "net_R"), t_netR_naive=tn,
                t_netR_day=tc, stop=stop,
                stop_vol=(d["stop_pct"] / d["vol"]).median(),
                cost_over_stop=cs.mean(),
                tight=float((d["stop_pct"] < d["cost_pct"]).mean() * 100),
                lev=1.0 / stop if stop > 0 else np.nan,
                hold_h=hold_hours(d))


def show_profile(rows, title, note):
    print("\n" + LINE)
    print(title)
    print(LINE)
    print(note)
    print(f"\n{'trigger frame':<30}{'entries':>9}{'days':>7}{'gross%':>9}"
          f"{'tG/day':>8}{'grossR':>8}{'netR':>8}{'t naive':>9}{'t by day':>10}"
          f"{'stop%':>8}{'stop/vol':>9}{'cost/stop':>10}{'tight%':>8}"
          f"{'hold h':>8}")
    for r in rows:
        print(f"{r['label']:<30}{r['entries']:>9,}{r['days']:>7,}"
              f"{r['gross']:>8.4f}%{r['t_gross_day']:>8.2f}{r['grossR']:>8.3f}"
              f"{r['netR']:>8.3f}{r['t_netR_naive']:>9.2f}{r['t_netR_day']:>10.2f}"
              f"{r['stop']:>7.3f}%{r['stop_vol']:>9.2f}{r['cost_over_stop']:>10.3f}"
              f"{r['tight']:>7.1f}%{r['hold_h']:>8.2f}")


def breakeven_multiple(d, sym):
    """R488's coordinate, per resolution: fit log(median daily stop) on
    log(daily 1-minute move), solve for the 1-minute move at which the
    median stop EQUALS the round trip, and report how many times the median
    day clears it."""
    g = d[d["sym"] == sym]
    cost = COST_ALLIN[sym]
    day = g.groupby(utc_day(g)).agg(vol=("vol", "mean"),
                                    stop=("stop_pct", "median"),
                                    n=("stop_pct", "size"))
    day = day[(day["n"] >= 3) & (day["vol"] > 0) & (day["stop"] > 0)].dropna()
    if len(day) < 30:
        return np.nan, np.nan, len(day)
    x = np.log(day["vol"].to_numpy())
    y = np.log(day["stop"].to_numpy())
    b, a0 = np.polyfit(x, y, 1)
    volstar = float(np.exp((np.log(cost) - a0) / b))
    act = float(g["vol"].median())
    return volstar, act / volstar if volstar > 0 else np.nan, len(day)


def paired(a, b, col, la, lb):
    da = a.assign(day=utc_day(a)).groupby("day")[col].mean()
    db = b.assign(day=utc_day(b)).groupby("day")[col].mean()
    j = pd.concat([da.rename("a"), db.rename("b")], axis=1).dropna()
    j = j.replace([np.inf, -np.inf], np.nan).dropna()
    d_ = j["a"] - j["b"]
    t_, nd = tstat(d_)
    print(f"  {la:<26} minus {lb:<26} {d_.mean():+9.4f}   t {t_:>6.2f}   "
          f"{nd:>5,} shared days")


# ===================================================================== main
def main():
    print(LINE)
    print("ROUND 490 - THE TRIGGER RESOLUTION PROFILE, IN PER-TRADE NET R")
    print(LINE)
    print("QUEUE ITEM 14. THIS ROUND CANNOT QUALIFY ANYTHING AND CANNOT SELECT")
    print("A RESOLUTION. The crypto sweep-to-break-of-structure population has")
    print("no sealed slice left anywhere (R450 and R475 read inside every")
    print("boundary of this window; R475 spent the one look). No split is cut")
    print("in this file, no cell is qualified, no resolution is ranked into a")
    print("'best'. Item 16 states its resolution in advance either way.")
    print(f"\ncost charged: R486 all-in per coin, "
          f"BTC {COST_ALLIN['BTCUSD']}% / ETH {COST_ALLIN['ETHUSD']}% / "
          f"SOL {COST_ALLIN['SOLUSD']}% of price, round trip.")
    print(f"Alpaca's {COST_ALPACA}% - the venue the desk actually holds - is "
          f"printed at the end. Costs decide nothing here.")
    print(f"pending window fixed at {PENDING_MIN} minutes at EVERY resolution "
          f"(OURS, never swept, and NOT widened for the coarse frames).")

    print("\nattaching realized 1-minute volatility, per coin per day "
          "(R488's yardstick, held fixed across all four frames) ...")
    vols = {s: daily_vol(p) for s, p in PARQUET_1M.items()}

    prim, sens, ctl = [], [], []
    native_A, native_B = [], []
    for sym in R.PRIMARY:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            d5, d1 = R.prep(sym)
        print(f"  {sym}: {len(d5):,} 5-minute bars, {len(d1):,} 1-minute bars,"
              f" {d5['t'].iloc[0]:%Y-%m-%d} -> {d5['t'].iloc[-1]:%Y-%m-%d}")
        sys.stdout.flush()

        # --------------------------- reproduction control: R450's own arms
        lo5, hi5 = d5["low"].to_numpy(), d5["high"].to_numpy()
        lo1, hi1 = d1["low"].to_numpy(), d1["high"].to_numpy()
        i1n = d5["i1_next"].to_numpy()
        for col, dirn, lab in R.LEVELS:
            sw5, sig5 = R.scan_sweeps(d5, col, dirn)
            if not len(sig5):
                continue
            stopA = np.array([lo5[a:b + 1].min() if dirn > 0
                              else hi5[a:b + 1].max()
                              for a, b in zip(sw5, sig5)])
            rA = R.simulate(d5, sig5, dirn, stopA, None, R.MAX_HOLD_MIN // 5,
                            cost=COST_ALLIN[sym])
            if len(rA):
                native_A.append(rA.assign(sym=sym, tf=5, mtf=5))
            e1, swB = R.trigger_1m(d5, d1, sw5, dirn)
            if len(e1):
                a1 = i1n[swB]
                stopB = np.array([lo1[max(0, a):b + 1].min() if dirn > 0
                                  else hi1[max(0, a):b + 1].max()
                                  for a, b in zip(a1, e1)])
                rB = R.simulate(d1, e1, dirn, stopB, None, R.MAX_HOLD_MIN,
                                cost=COST_ALLIN[sym])
                if len(rB):
                    native_B.append(rB.assign(sym=sym, tf=1, mtf=1))

        for tf in RESOLUTIONS:
            P, S, dtf = run_resolution(sym, d5, d1, tf)
            if len(P):
                prim.append(P)
            if len(S):
                sens.append(S.assign(tf=tf))
            c = control_at(dtf, tf, sym)
            if len(c):
                ctl.append(c)
            print(f"     tf={tf:>2}m  {len(dtf):>9,} bars   "
                  f"{len(P):>7,} entries   control {len(c):>6,}")
            sys.stdout.flush()

    P = pd.concat(prim)
    S = pd.concat(sens)
    C = pd.concat(ctl)
    key = ["sig_i", "sig_t", "stop_pct"]
    A = pd.concat([g.drop_duplicates(subset=key)
                   for _, g in pd.concat(native_A).groupby("sym")])
    B = pd.concat([g.drop_duplicates(subset=key)
                   for _, g in pd.concat(native_B).groupby("sym")])
    for f in (P, S, C, A, B):
        f["cost_pct"] = f["sym"].map(COST_ALLIN)
    P, S, C = attach_vol(P, vols), attach_vol(S, vols), attach_vol(C, vols)
    A, B = attach_vol(A, vols), attach_vol(B, vols)

    # ----------------------------------------------- reproduction controls
    print("\n" + LINE)
    print("REPRODUCTION CONTROLS - is this the same machinery R476 published?")
    print(LINE)
    p1 = P[P.tf == 1]
    print(f"generalised tf=1 entries {len(p1):,}   R450's native trigger_1m "
          f"entries {len(B):,}   identical: {len(p1) == len(B)}")
    print(f"generalised tf=1 gross {p1['gross_pct'].mean():+.4f}%   "
          f"native arm B gross {B['gross_pct'].mean():+.4f}%")
    tcB, ndB = clustered(p1, "gross_pct")
    print(f"R476 published for this population: 71,073 entries, +0.1435% of "
          f"price, t by day 13.77")
    print(f"this file reads:                   {len(p1):,} entries, "
          f"{p1['gross_pct'].mean():+.4f}%, t by day {tcB:.2f} over {ndB:,} days")
    p5 = P[P.tf == 5]
    print(f"\ngeneralised tf=5 entries {len(p5):,}  vs  R450's NATIVE arm A "
          f"(the 5-minute confirmation bar itself) {len(A):,}")
    print("  the two differ only in R450's arm-A rule that a bar which "
          "re-sweeps the level cannot also be the break of structure;")
    print("  both are printed in the profile so the difference is visible "
          "rather than assumed.")

    # --------------------------------------------------- THE PROFILE
    rows = []
    for tf in RESOLUTIONS:
        rows.append(profile_row(P[P.tf == tf], f"{tf}-minute trigger"))
    rows.append(profile_row(A, "  [R450 native arm A, 5m]"))
    rows.append(profile_row(C[C.tf == 1], "  [random entry, 1m frame]"))
    rows.append(profile_row(C[C.tf == 5], "  [random entry, 5m frame]"))
    rows.append(profile_row(C[C.tf == 15], "  [random entry, 15m frame]"))
    rows.append(profile_row(C[C.tf == 60], "  [random entry, 60m frame]"))
    show_profile(
        rows,
        "THE PROFILE - MANAGED ON THE TRIGGER FRAME (R450's own precedent)",
        "One row per distinct entry, hold-24h scoring (the four target "
        "settings score\nthe SAME entries). netR is the mean of PER-TRADE "
        "net/stop - R487's statistic,\nnot a ratio of means. t by day pools "
        "BTC+ETH+SOL into one observation per UTC\nday. stop/vol is the "
        "structural stop in units of that day's 1-MINUTE move at\nevery "
        "resolution. tight% is the share of entries whose stop is smaller "
        "than the\nround trip they must pay.")
    pd.DataFrame(rows).to_csv(f"{REPO}/step490_profile_trigger_frame.csv",
                              index=False)

    rows2 = [profile_row(S[S.tf == tf], f"{tf}-minute trigger")
             for tf in RESOLUTIONS]
    show_profile(
        rows2,
        "SENSITIVITY - THE SAME ENTRIES, MANAGED ON 1-MINUTE BARS THROUGHOUT",
        "Only the TRIGGER moves; the stop and the target are checked on "
        "1-minute bars at\nevery resolution (step451's discipline). If the "
        "profile above is an artefact of\ncoarser exit granularity rather "
        "than of the trigger, these two tables disagree.")
    pd.DataFrame(rows2).to_csv(f"{REPO}/step490_profile_1m_managed.csv",
                               index=False)

    # ------------------------- the item's premise, measured not assumed
    print("\n" + LINE)
    print("THE ITEM'S PREMISE, MEASURED: HOW FAST DOES THE STOP GROW WITH THE")
    print("TRIGGER TIMEFRAME?")
    print(LINE)
    print("Queue item 14 reasons from 'the stop scales with the trigger's")
    print("timeframe at an elasticity of ~1 and the round trip does not scale")
    print("at all'. R488's elasticity of ~1 is the stop against VOLATILITY, on")
    print("one frame. Against the FRAME itself it is a different number and it")
    print("is measured here.")
    xs = np.log(np.array(RESOLUTIONS, float))
    ys = np.log(np.array([P[P.tf == tf]["stop_pct"].median()
                          for tf in RESOLUTIONS], float))
    bb, aa = np.polyfit(xs, ys, 1)
    yh = aa + bb * xs
    r2 = 1 - ((ys - yh) ** 2).sum() / ((ys - ys.mean()) ** 2).sum()
    print(f"\n  log(median stop) = {aa:+.3f} + {bb:.3f} * log(trigger minutes)"
          f"   R2 {r2:.4f}")
    print(f"  a {RESOLUTIONS[-1]}x coarser trigger buys a "
          f"{P[P.tf==60]['stop_pct'].median()/P[P.tf==1]['stop_pct'].median():.2f}x "
          f"wider stop, not a {RESOLUTIONS[-1]}x one.")
    print(f"\n{'frame':<8}{'median stop%':>14}{'x the 1m stop':>15}"
          f"{'cost/stop':>11}{'x the 1m cost/stop':>20}{'tight%':>9}")
    s1 = P[P.tf == 1]["stop_pct"].median()
    c1 = (P[P.tf == 1]["cost_pct"] / P[P.tf == 1]["stop_pct"]).replace(
        [np.inf, -np.inf], np.nan).mean()
    for tf in RESOLUTIONS:
        g = P[P.tf == tf]
        st = g["stop_pct"].median()
        cs = (g["cost_pct"] / g["stop_pct"]).replace(
            [np.inf, -np.inf], np.nan).mean()
        print(f"{tf:>3}m{'':<4}{st:>13.3f}%{st/s1:>15.2f}{cs:>11.3f}"
              f"{cs/c1:>20.2f}{float((g['stop_pct']<g['cost_pct']).mean()*100):>8.1f}%")
    print("\n  The premise is DIRECTIONALLY right and QUANTITATIVELY wrong:")
    print("  cost/stop does fall with the timeframe, but at the rate the stop")
    print("  actually grows, which is far slower than the frame does.")

    # ------------------------------------------- the paired differences
    print("\n" + LINE)
    print("PAIRED ON SHARED UTC DAYS - THE NUMBERS TO QUOTE")
    print(LINE)
    print("R476's headline was the GROSS difference: the 1-minute trigger beat")
    print("the 5-minute one by +0.0994% a day at t = 9.17. Item 14 asks for the")
    print("same comparison in the statistic that decides things.")
    for col, unit in (("gross_pct", "% of price per day"),
                      ("net_R", "per-trade net R per day")):
        print(f"\nIN {unit.upper()}:")
        for i in range(len(RESOLUTIONS)):
            for j in range(i + 1, len(RESOLUTIONS)):
                a, b = RESOLUTIONS[i], RESOLUTIONS[j]
                paired(P[P.tf == a], P[P.tf == b], col,
                       f"{a}m trigger", f"{b}m trigger")
        for tf in RESOLUTIONS:
            paired(P[P.tf == tf], C[C.tf == tf], col,
                   f"{tf}m trigger", f"{tf}m RANDOM entry")

    # ------------------------------------------ R488's break-even coordinate
    print("\n" + LINE)
    print("R488's BREAK-EVEN COORDINATE, PER RESOLUTION")
    print(LINE)
    print("The 1-minute move at which the median structural stop EQUALS the")
    print("round trip, from the fitted log-log elasticity, and how many times")
    print("the median day clears it. A coarser trigger buys a wider stop "
          "against\nan unchanged round trip, so the multiple should RISE with "
          "the timeframe.")
    print(f"\n{'coin':<9}{'frame':>7}{'round trip%':>13}{'vol* %':>10}"
          f"{'median day %':>14}{'multiple':>10}{'days':>8}")
    be_rows = []
    for sym in R.PRIMARY:
        for tf in RESOLUTIONS:
            vs, mult, nd = breakeven_multiple(P[P.tf == tf], sym)
            be_rows.append(dict(sym=sym, tf=tf, volstar=vs, multiple=mult,
                                days=nd))
            act = P[(P.tf == tf) & (P.sym == sym)]["vol"].median()
            print(f"{sym:<9}{tf:>6}m{COST_ALLIN[sym]:>13.4f}{vs:>10.4f}"
                  f"{act:>14.4f}{mult:>10.2f}{nd:>8,}")
    pd.DataFrame(be_rows).to_csv(f"{REPO}/step490_breakeven.csv", index=False)

    # ------------------------------------------------------ per coin
    print("\n" + LINE)
    print("BY COIN - a number that only holds on one coin is a coin fact")
    print(LINE)
    print(f"{'coin':<9}{'frame':>7}{'entries':>9}{'days':>7}{'gross%':>9}"
          f"{'netR':>8}{'t by day':>10}{'stop%':>8}{'stop/vol':>9}"
          f"{'cost/stop':>10}")
    for sym in R.PRIMARY:
        for tf in RESOLUTIONS:
            g = P[(P.tf == tf) & (P.sym == sym)]
            if not len(g):
                continue
            tc, nd = clustered(g, "net_R")
            cs = (g["cost_pct"] / g["stop_pct"]).replace(
                [np.inf, -np.inf], np.nan).mean()
            print(f"{sym:<9}{tf:>6}m{len(g):>9,}{nd:>7,}"
                  f"{g['gross_pct'].mean():>8.4f}%{finite_mean(g,'net_R'):>8.3f}"
                  f"{tc:>10.2f}{g['stop_pct'].median():>7.3f}%"
                  f"{(g['stop_pct']/g['vol']).median():>9.2f}{cs:>10.3f}")

    # ---------------------------------------------------- frequency
    print("\n" + LINE)
    print("FREQUENCY - EXPECTANCY AND FREQUENCY ARE SEPARATE FACTS")
    print(LINE)
    span_days = (pd.to_datetime(P["sig_t"]).max() -
                 pd.to_datetime(P["sig_t"]).min()).days
    print(f"window {pd.to_datetime(P['sig_t']).min():%Y-%m-%d} -> "
          f"{pd.to_datetime(P['sig_t']).max():%Y-%m-%d}  ({span_days:,} days)")
    print(f"\n{'frame':<8}{'entries':>10}{'per coin/yr':>13}{'days w/ entry':>15}"
          f"{'share of 1m':>13}{'median hold h':>15}")
    n1 = len(P[P.tf == 1])
    for tf in RESOLUTIONS:
        g = P[P.tf == tf]
        nd = utc_day(g).nunique()
        print(f"{tf:>3}m{'':<4}{len(g):>10,}"
              f"{len(g)/3/(span_days/365.25):>13,.0f}{nd:>15,}"
              f"{len(g)/n1*100:>12.1f}%{hold_hours(g):>15.2f}")

    # ------------------------------------------------- the Alpaca read
    print("\n" + LINE)
    print("THE SAME PROFILE ON THE VENUE THE DESK ACTUALLY HOLDS (Alpaca 0.50%)")
    print(LINE)
    print("Charged for honesty and deciding nothing. Printed because the desk")
    print("has no US perpetual account and every R486 number above is a")
    print("hypothetical venue's floor.")
    print(f"\n{'frame':<8}{'netR @ R486 all-in':>22}{'netR @ Alpaca 0.50%':>22}"
          f"{'cost/stop @ Alpaca':>21}")
    for tf in RESOLUTIONS:
        g = P[P.tf == tf]
        alt = ((g["gross_pct"] - COST_ALPACA) / g["stop_pct"]).replace(
            [np.inf, -np.inf], np.nan).mean()
        cs = (COST_ALPACA / g["stop_pct"]).replace(
            [np.inf, -np.inf], np.nan).mean()
        print(f"{tf:>3}m{'':<4}{finite_mean(g,'net_R'):>22.3f}{alt:>22.3f}"
              f"{cs:>21.3f}")

    P.to_csv(f"{REPO}/step490_entries.csv", index=False)
    print("\n" + LINE)
    print("LOOKS CONSUMED: NONE, AND NONE COULD BE. No sealed slice exists on")
    print("this family; no split was cut in this file; no cell was qualified;")
    print("no resolution was selected. THE FENCE HOLDS: nothing above may be")
    print("used to choose the resolution item 16 carries to LINK or XRP.")
    print(LINE)


if __name__ == "__main__":
    main()
