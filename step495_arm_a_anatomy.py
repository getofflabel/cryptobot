"""
step495_arm_a_anatomy.py - ROUND 495

ONE RULE IN R450's ARM A IS WORTH 3.5x ON GROSS. NOBODY DERIVED IT.
(QUEUE ITEM 19)

Research only. No orders. No account. No live file touched, imported or
modified. Nothing here is deployed by this script under any outcome.

QUEUE ITEM 19, VERBATIM
  R490 ran one uniform construction at four trigger frames and printed R450's
  native arm A beside the 5-minute row. They differ in exactly one rule -
  arm A's `scan_sweeps` will not let a bar that RE-SWEEPS the level also be
  the break of structure, and it measures the stop from the sweep bar itself
  rather than from its close. Arm A reads gross +0.0296% of price; the same
  frame under arm B's construction reads +0.1045%, three and a half times it,
  on 70,194 entries against 75,023. That single rule is bigger than the
  entire 1m-vs-5m resolution effect it has been credited to since R476.
  A bar that trades through the level and closes back through structure is
  the textbook sweep-and-reclaim candle; arm A discards it by construction
  and nobody ever asked what it was discarding.
  Deliverable, purely descriptive: isolate the two differences (the re-sweep
  exclusion, and whether the stop starts at the sweep bar or at its close),
  score each separately at all four resolutions, and report the population and
  the per-trade net R of the entries arm A throws away. Say plainly whether
  R450's arm A was ever justified from his teaching or was an implementation
  accident - read step431/step436, do not infer it.
  THE FENCE: the crypto and index slices are both spent, so this can describe
  and cannot select. No construction may be "chosen" here and nothing in it
  may be cited by item 16 as a reason - same rule R490 ran under. If it turns
  out arm A was an accident, that is a fact about how this log should READ its
  own back catalogue, not a licence to pick a winner.

THE FENCE, RESTATED AS CODE DISCIPLINE
  `slice_by_time` is NEVER called in this file. No train/val/test split is
  cut, no cell is qualified, there is no `verdict` anywhere, and no
  construction is ranked into a "best". The whole spent window is read at
  once, which is the only honest thing to do with a family that has no sealed
  slice left on these three coins. The two rules are printed as a 2x2
  FACTORIAL at four resolutions so that neither can be quietly credited with
  the other's effect.

THIS ROUND CONSUMES NO LOOK, AND CANNOT
  BTC/ETH/SOL 1-minute sweep-to-break-of-structure has no sealed slice
  anywhere (R450 and R475 have read inside every boundary of the 2021-2026
  window; R475 spent the one look). Every number below is a re-reading of an
  already-published population under a construction switch it was never read
  under.

WHAT IS BEING ISOLATED, PRECISELY
  R450's `scan_sweeps` walks the 5-minute chart. For a long:

      if lo[t] < L:                 # this bar trades through the level
          pend = t if pend < 0 else pend
          continue                  # <-- RULE 1, and it is a `continue`
      if pend >= 0 and c[t] > mr_sh[t]:
          confirm the sweep at bar t

  The `continue` means a bar whose wick takes the level can never be the bar
  whose body closes through structure. Call that RULE 1, the RE-SWEEP
  EXCLUSION. It applies to the sweep bar itself and to every later bar in the
  pending window that dips back through the level.

  RULE 1 LIVES IN TWO PLACES AND THEY ARE NOT THE SAME THING.
    (i) in the BREAK-OF-STRUCTURE test - which bar is allowed to be the
        trigger. This is the difference R490 named between its generalised
        tf=5 row and R450's native arm A, and it is what the 2x2 below
        switches.
    (ii) in the SWEEP SCAN's pending bookkeeping - a confirmation clears the
        pending state, so a permissive scan confirms sooner and opens the
        next pending sweep sooner. R450's arm B calls `scan_sweeps` UNCHANGED
        and replaces only the trigger, so every round in this family has run
        (ii) ON. It is held ON for the whole 2x2 so the four cells share one
        sweep list, and lifted only in a separately labelled sensitivity,
        where it turns out to be the larger of the two by a wide margin.

  R450's arm A then measures the stop as the extreme traded from the SWEEP
  BAR (index `sw`) through the signal bar. R490's generalised arm B measures
  it from the first trigger bar at or after the sweep bar's CLOSE. Call that
  RULE 2, the STOP ORIGIN.

  This file makes both switches parameters and runs the 2x2 at 1 / 5 / 15 /
  60 minutes. Nothing else moves. Everything else is R450's, imported and
  not retyped: the two-candle swing, levels on the high timeframes only, the
  sweep hunted on the 5-MINUTE chart at every resolution, break of structure
  as a BODY close, the 2-hour pending expiry and the 24-hour hold cap (both
  OURS), the UTC day boundary (ours), R476's dedupe.

HOW RULE 1 GENERALISES OFF THE 5-MINUTE FRAME
  On the 5-minute frame the sweep scan and the break-of-structure scan are
  the same loop, so the rule is exact. At 1 / 15 / 60 minutes the sweep is
  still hunted on the 5-minute chart (he is explicit) and the break is read
  on the trigger frame, so the faithful analogue is: a TRIGGER bar whose wick
  is through the level cannot be the break-of-structure bar. The level is
  carried onto the trigger frame by forward-fill from the 5-minute chart,
  which is the identity at tf=5.
  Rule 1 also changes the SWEEP SEQUENCE, not only the entry: a confirmation
  clears the pending state, so a permissive scan can confirm earlier and open
  the next pending sweep sooner. Part A therefore runs each construction
  end to end. Part B holds the sweep list FIXED at arm A's own, so that the
  entries arm A throws away are counted against a common denominator.

HOW RULE 2 GENERALISES OFF THE 5-MINUTE FRAME
  "From the sweep bar" is `min(trigger-frame extreme from the sweep bar's
  close to the entry, the 5-MINUTE sweep bar's own low)` for a long, and the
  max of the mirror for a short. At tf=5 that is identical to R450's arm A
  by construction. At every other frame it adds exactly the extreme printed
  while the level was being taken and nothing else - it never drags in a
  coarse bar that began before the sweep.

COSTS
  Charged so the P&L is honest and used for NOTHING else (owner rule,
  2026-07-25). They decline nothing, gate nothing and rank nothing here.
  R486's corrected all-in Coinbase round trip per coin, the same figures
  R490 used: BTC 0.0556% / ETH 0.1463% / SOL 0.0816% of price. Gross sits
  beside every net number.

BASELINE STATED IN THE SAME BREATH (R88/R100)
  R450's chance control is run at every resolution on that resolution's own
  frame, spaced by TIME (300 minutes = R450's every-60th-5-minute-bar), with
  the same stop machinery - R490's convention, imported in spirit and
  re-derived here so the four constructions are compared against something.

REPRODUCTION CONTROLS
  1. tf=5 with (rule 1 ON, rule 2 ON) is printed beside R450's native arm A
     run exactly as R490 ran it. They should differ only by the one-bar
     pending-window offset described in the honest limits.
  2. tf=1 with (rule 1 OFF, rule 2 OFF) is printed against R476's published
     population: 71,073 entries, +0.1435% of price, t by day 13.77.
  3. tf=5 with (rule 1 OFF, rule 2 OFF) is printed against R490's published
     tf=5 row: 75,023 entries, +0.1045% of price.

HONEST LIMITS, FIXED BEFORE RUNNING
  - R450's native arm A checks for the break inside [pend, pend+24] on the
    5-minute chart; the generalised scan checks [pend+1, pend+1+24]. The bar
    at `pend` is excluded by rule 1 anyway, so the difference is ONE extra
    bar at the far end of the window. It is R490's convention and is kept so
    this file's tf=5 rows are directly comparable to R490's published ones.
  - The 15m and 60m frames are resampled from the 5-minute parquet on a UTC
    grid (R450's `resample`), so a period with no 5-minute bars is absent
    rather than zero-volume.
  - The 24-hour cap is counted in BARS at every resolution (R450's
    convention) and Alpaca's tape has gaps (R481); median wall-clock hold is
    printed beside it.
  - Coarser frames produce fewer entries, so their t values rest on fewer
    days. Day counts are printed in every table.
  - This is the SPENT crypto population. Nothing here is out-of-sample.

USAGE
  python3 step495_arm_a_anatomy.py
"""

import contextlib
import io
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = "/Users/wallacechen/cryptobot"
sys.path.insert(0, REPO)

import step450_tjr_crypto_1m as R          # noqa: E402  the parent, unchanged

# R486's corrected all-in round trip on Coinbase Derivatives, % of price.
# Charged for honest P&L; decides nothing.
COST_ALLIN = {"BTCUSD": 0.0556, "ETHUSD": 0.1463, "SOLUSD": 0.0816}
COST_ALPACA = 0.50

RESOLUTIONS = [1, 5, 15, 60]
PENDING_MIN = R.PENDING_BARS_5M * 5         # 120 minutes, OURS, never swept
CONTROL_SPACING_MIN = 300                   # R450's every-60th-5m-bar, in time
PARQUET_1M = {s: f"data_alpaca_{s}_1m.parquet" for s in R.PRIMARY}
DEDUPE_KEY = ["sig_i", "sig_t", "stop_pct"]
LINE = "=" * 112


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
    if not len(res):
        return np.nan, 0
    v = res[col].replace([np.inf, -np.inf], np.nan)
    d = v.groupby(utc_day(res)).mean().dropna()
    return tstat(d)


def finite_mean(res, col):
    if not len(res):
        return np.nan
    return res[col].replace([np.inf, -np.inf], np.nan).mean()


def daily_vol(path):
    """R488's yardstick, unchanged: mean |1-minute return| per UTC day, %."""
    b = pd.read_parquet(f"{REPO}/{path}")
    t = pd.to_datetime(b["t"])
    r = b["close"].pct_change().abs() * 100.0
    f = pd.DataFrame({"t": t, "r": r}).dropna()
    return f.groupby(f["t"].dt.floor("D"))["r"].mean()


def attach_vol(d, vols):
    if not len(d):
        return d
    idx = pd.MultiIndex.from_arrays([d["sym"], utc_day(d)])
    ser = pd.concat({s: v for s, v in vols.items()}, names=["sym", "day"])
    d = d.copy()
    d["vol"] = ser.reindex(idx).to_numpy()
    return d


# ========================================== the two rules, made parameters
def scan_sweeps_flag(d5, level_col, direction, resweep_excluded):
    """R450's `scan_sweeps` with RULE 1 made a parameter and nothing else
    changed. When `resweep_excluded` is False a bar that trades through the
    level may ALSO be the bar whose body closes through structure - the
    sweep-and-reclaim candle arm A discards.

    Returns (pending sweep 5-minute indices, confirming 5-minute indices).
    """
    lo = d5["low"].to_numpy()
    hi = d5["high"].to_numpy()
    c = d5["close"].to_numpy()
    lvl = d5[level_col].to_numpy()
    mr_sh = d5["mr_sh"].to_numpy()
    mr_sl = d5["mr_sl"].to_numpy()
    n = len(d5)
    sweeps, sigs = [], []
    pend = -1
    for t in range(n):
        L = lvl[t]
        if pend >= 0 and t - pend > R.PENDING_BARS_5M:
            pend = -1
        if not np.isfinite(L):
            continue
        if direction > 0:
            if lo[t] < L:
                pend = t if pend < 0 else pend
                if resweep_excluded:
                    continue
            if pend >= 0 and np.isfinite(mr_sh[t]) and c[t] > mr_sh[t]:
                sweeps.append(pend)
                sigs.append(t)
                pend = -1
        else:
            if hi[t] > L:
                pend = t if pend < 0 else pend
                if resweep_excluded:
                    continue
            if pend >= 0 and np.isfinite(mr_sl[t]) and c[t] < mr_sl[t]:
                sweeps.append(pend)
                sigs.append(t)
                pend = -1
    return np.array(sweeps, dtype=int), np.array(sigs, dtype=int)


def tf_frame(d5, d1, tf):
    """The trigger chart at `tf` minutes with his two-candle swing on it.
    R490's function, re-derived so this file stands alone."""
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


def level_on_tf(d5, dtf, level_col):
    """The 5-minute level column carried onto the trigger frame by
    forward-fill (the most recent 5-minute bar at or before each trigger
    bar's start). Identity at tf=5."""
    t5 = d5["t"].to_numpy()
    ttf = dtf["t"].to_numpy()
    j = np.searchsorted(t5, ttf, side="right") - 1
    out = np.full(len(ttf), np.nan)
    ok = j >= 0
    out[ok] = d5[level_col].to_numpy()[j[ok]]
    return out


def first_bar_after_close(d5, dtf):
    """Index of the first trigger bar STARTING at or after each 5-minute
    bar's close - R450's `i1_next`, frame made a parameter."""
    close_t = (d5["t"] + pd.Timedelta(minutes=5)).to_numpy()
    return np.searchsorted(dtf["t"].to_numpy(), close_t, side="left")


def trigger_flag(dtf, tf, sweeps, direction, lvl_tf, first, resweep_excluded):
    """R450's `trigger_1m` with the frame made a parameter (R490) and RULE 1
    made a parameter (this round). Returns (entry index on the trigger frame,
    sweep 5-minute index) pairs."""
    c = dtf["close"].to_numpy()
    sh = dtf["mr_sh"].to_numpy()
    sl = dtf["mr_sl"].to_numpy()
    lo = dtf["low"].to_numpy()
    hi = dtf["high"].to_numpy()
    n = len(dtf)
    span = max(1, PENDING_MIN // tf)         # never widened
    ent, sw = [], []
    for s in sweeps:
        a = first[s]
        if a >= n:
            continue
        b = min(n - 1, a + span)
        if direction > 0:
            m = (c[a:b + 1] > sh[a:b + 1]) & np.isfinite(sh[a:b + 1])
            if resweep_excluded:
                L = lvl_tf[a:b + 1]
                m = m & ~((lo[a:b + 1] < L) & np.isfinite(L))
        else:
            m = (c[a:b + 1] < sl[a:b + 1]) & np.isfinite(sl[a:b + 1])
            if resweep_excluded:
                L = lvl_tf[a:b + 1]
                m = m & ~((hi[a:b + 1] > L) & np.isfinite(L))
        k = np.flatnonzero(m)
        if len(k) == 0:
            continue
        ent.append(a + k[0])
        sw.append(s)
    return np.array(ent, dtype=int), np.array(sw, dtype=int)


def structural_stop(dtf, d5, first, sw, ent, direction, from_sweep_bar):
    """RULE 2. The extreme traded on the trigger frame between the sweep
    bar's CLOSE and the entry (R490's arm-B stop); and, when
    `from_sweep_bar`, the 5-MINUTE sweep bar's own extreme folded in - the
    extreme printed WHILE the level was being taken, which is R450's arm-A
    stop and, per step431 section 9.1, the one he states.
    """
    lo = dtf["low"].to_numpy()
    hi = dtf["high"].to_numpy()
    a = first[sw]
    if direction > 0:
        s = np.array([lo[max(0, x):y + 1].min() if y >= max(0, x) else np.nan
                      for x, y in zip(a, ent)])
        if from_sweep_bar:
            s = np.minimum(s, d5["low"].to_numpy()[sw])
        return s
    s = np.array([hi[max(0, x):y + 1].max() if y >= max(0, x) else np.nan
                  for x, y in zip(a, ent)])
    if from_sweep_bar:
        s = np.maximum(s, d5["high"].to_numpy()[sw])
    return s


# ================================================================= part A
def run_cell(sym, d5, d1, tf, trig_excluded, from_sweep_bar, cache,
             sweep_excluded=True):
    """One construction, end to end, on one coin at one resolution.

    `sweep_excluded` is the rule as it acts in the 5-MINUTE SWEEP SCAN, where
    it also governs when a pending state is cleared and the next sweep can
    open. Every round in this family since R450 has run it ON there - R450's
    arm B calls `scan_sweeps` unchanged and only replaces the trigger - so it
    is held ON for the whole 2x2 and lifted only in the clearly labelled
    sensitivity below.
    `trig_excluded` is RULE 1 proper: the rule as it acts on the bar that
    carries the break of structure. That is the one difference R490 named
    between its generalised tf=5 row and R450's native arm A.
    """
    dtf = cache["frames"][tf]
    first = cache["first"][tf]
    cost = COST_ALLIN[sym]
    out = []
    for col, dirn, lab in R.LEVELS:
        sw5, _ = cache["sweeps"][(col, dirn, sweep_excluded)]
        if not len(sw5):
            continue
        lvl_tf = cache["levels"][(tf, col)]
        ent, sw = trigger_flag(dtf, tf, sw5, dirn, lvl_tf, first,
                               trig_excluded)
        if not len(ent):
            continue
        stop_px = structural_stop(dtf, d5, first, sw, ent, dirn,
                                  from_sweep_bar)
        r = R.simulate(dtf, ent, dirn, stop_px, None, R.MAX_HOLD_MIN // tf,
                       cost=cost)
        if len(r):
            out.append(r.assign(sym=sym, tf=tf, mtf=tf, level=lab, dirn=dirn))
    if not out:
        return pd.DataFrame()
    # R476's dedupe, unchanged: two levels can be swept into the SAME entry
    # with the same structural stop, and that is one trade, not two.
    return pd.concat(out).drop_duplicates(subset=DEDUPE_KEY)


def control_at(dtf, tf, sym):
    """R450's chance control, generalised by TIME so the four resolutions are
    compared against equally frequent randomness (R490's convention)."""
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
    return np.nan if not len(d) else float(
        (d["bars_held"] * d["mtf"]).median() / 60.0)


def profile_row(d, label):
    if not len(d):
        return dict(label=label, entries=0, days=0)
    tg, _ = clustered(d, "gross_pct")
    tc, nd = clustered(d, "net_R")
    stop = d["stop_pct"].median()
    cs = (d["cost_pct"] / d["stop_pct"]).replace([np.inf, -np.inf], np.nan)
    return dict(
        label=label, entries=len(d), days=nd,
        gross=d["gross_pct"].mean(), t_gross_day=tg,
        grossR=(d["gross_pct"] / d["stop_pct"]).replace(
            [np.inf, -np.inf], np.nan).mean(),
        netR=finite_mean(d, "net_R"), t_netR_day=tc,
        stop=stop,
        stop_vol=(d["stop_pct"] / d["vol"]).median(),
        cost_over_stop=cs.mean(),
        tight=float((d["stop_pct"] < d["cost_pct"]).mean() * 100),
        hold_h=hold_hours(d))


HDR = (f"{'construction':<44}{'entries':>9}{'days':>7}{'gross%':>9}"
       f"{'tG/day':>8}{'grossR':>8}{'netR':>8}{'t/day':>8}{'stop%':>8}"
       f"{'st/vol':>8}{'cost/st':>8}{'tight%':>8}{'hold h':>8}")


def show(rows, title, note=""):
    print("\n" + LINE)
    print(title)
    print(LINE)
    if note:
        print(note)
    print("\n" + HDR)
    for r in rows:
        if not r.get("entries"):
            print(f"{r['label']:<44}{0:>9}   (no entries)")
            continue
        print(f"{r['label']:<44}{r['entries']:>9,}{r['days']:>7,}"
              f"{r['gross']:>9.4f}{r['t_gross_day']:>8.2f}{r['grossR']:>8.3f}"
              f"{r['netR']:>8.3f}{r['t_netR_day']:>8.2f}{r['stop']:>8.3f}"
              f"{r['stop_vol']:>8.2f}{r['cost_over_stop']:>8.3f}"
              f"{r['tight']:>7.1f}%{r['hold_h']:>8.2f}")


# ================================================================= part B
def discarded_population(sym, d5, d1, tf, cache):
    """What arm A throws away, against a COMMON denominator.

    The sweep list is held FIXED at arm A's own (rule 1 ON), so both trigger
    rules see exactly the same pending windows. Inside each window:
      identical  - the permissive rule finds the same entry bar
      earlier    - the permissive rule enters sooner; arm A takes a later bar
      only_B     - the permissive rule enters and arm A never does at all
    The permissive entry is scored under BOTH stop conventions.
    """
    dtf = cache["frames"][tf]
    first = cache["first"][tf]
    cost = COST_ALLIN[sym]
    rows_B, rows_A, tally = [], [], dict(sweeps=0, identical=0, earlier=0,
                                         only_B=0, only_A=0, neither=0)
    for col, dirn, lab in R.LEVELS:
        sw5, _ = cache["sweeps"][(col, dirn, True)]     # ARM A's sweeps
        if not len(sw5):
            continue
        lvl_tf = cache["levels"][(tf, col)]
        eA, sA = trigger_flag(dtf, tf, sw5, dirn, lvl_tf, first, True)
        eB, sB = trigger_flag(dtf, tf, sw5, dirn, lvl_tf, first, False)
        mapA = dict(zip(sA.tolist(), eA.tolist()))
        mapB = dict(zip(sB.tolist(), eB.tolist()))
        tally["sweeps"] += len(sw5)
        only_sw, only_ent = [], []
        for s in sw5.tolist():
            a, b = mapA.get(s), mapB.get(s)
            if a is None and b is None:
                tally["neither"] += 1
            elif b is None:
                tally["only_A"] += 1
            elif a is None:
                tally["only_B"] += 1
                only_sw.append(s)
                only_ent.append(b)
            elif a == b:
                tally["identical"] += 1
            else:
                tally["earlier"] += 1
                only_sw.append(s)
                only_ent.append(b)
        if not only_ent:
            continue
        only_sw = np.array(only_sw, dtype=int)
        only_ent = np.array(only_ent, dtype=int)
        for from_sweep, bag in ((False, rows_B), (True, rows_A)):
            stop_px = structural_stop(dtf, d5, first, only_sw, only_ent, dirn,
                                      from_sweep)
            r = R.simulate(dtf, only_ent, dirn, stop_px, None,
                           R.MAX_HOLD_MIN // tf, cost=cost)
            if len(r):
                bag.append(r.assign(sym=sym, tf=tf, mtf=tf, level=lab,
                                    dirn=dirn))
    B = (pd.concat(rows_B).drop_duplicates(subset=DEDUPE_KEY)
         if rows_B else pd.DataFrame())
    A = (pd.concat(rows_A).drop_duplicates(subset=DEDUPE_KEY)
         if rows_A else pd.DataFrame())
    return B, A, tally


# ===================================================================== main
def main():
    print(LINE)
    print("ROUND 495 - THE ANATOMY OF R450's ARM A: TWO RULES, FOUR "
          "RESOLUTIONS, NOTHING SELECTED")
    print(LINE)
    print("QUEUE ITEM 19. THIS ROUND CANNOT QUALIFY ANYTHING AND CANNOT "
          "SELECT A CONSTRUCTION.")
    print("The crypto sweep-to-break-of-structure population has no sealed "
          "slice left anywhere")
    print("(R450 and R475 read inside every boundary of this window; R475 "
          "spent the one look).")
    print("`slice_by_time` is never called in this file, no split is cut, no "
          "cell is qualified,")
    print("and nothing here may be cited by item 16 as a reason to prefer a "
          "construction.")
    print(f"\ncost charged: R486 all-in per coin, "
          f"BTC {COST_ALLIN['BTCUSD']}% / ETH {COST_ALLIN['ETHUSD']}% / "
          f"SOL {COST_ALLIN['SOLUSD']}% of price, round trip. "
          f"Alpaca's {COST_ALPACA}% noted, not used.")
    print(f"pending window fixed at {PENDING_MIN} minutes at EVERY resolution "
          "(OURS, never swept, never widened).")

    print("\nattaching realized 1-minute volatility, per coin per day "
          "(R488's yardstick, held fixed across all four frames) ...")
    vols = {s: daily_vol(p) for s, p in PARQUET_1M.items()}

    cells = {}          # (tf, trig_excluded, from_sweep_bar) -> [frames]
    sens = {}           # (tf, from_sweep_bar) -> [frames], exclusion
                        # lifted in the sweep scan too
    disc_B, disc_A, ctl, native_A = {}, {}, [], []
    tallies = {}

    for sym in R.PRIMARY:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            d5, d1 = R.prep(sym)
        print(f"\n  {sym}: {len(d5):,} 5-minute bars, {len(d1):,} 1-minute "
              f"bars, {d5['t'].iloc[0]:%Y-%m-%d} -> {d5['t'].iloc[-1]:%Y-%m-%d}")
        sys.stdout.flush()

        cache = dict(frames={}, first={}, levels={}, sweeps={})
        for tf in RESOLUTIONS:
            dtf = tf_frame(d5, d1, tf)
            cache["frames"][tf] = dtf
            cache["first"][tf] = first_bar_after_close(d5, dtf)
            for col, _, _ in R.LEVELS:
                cache["levels"][(tf, col)] = level_on_tf(d5, dtf, col)
        for col, dirn, lab in R.LEVELS:
            for excl in (True, False):
                cache["sweeps"][(col, dirn, excl)] = scan_sweeps_flag(
                    d5, col, dirn, excl)
        nA = sum(len(cache["sweeps"][(c, d, True)][0]) for c, d, _ in R.LEVELS)
        nB = sum(len(cache["sweeps"][(c, d, False)][0]) for c, d, _ in R.LEVELS)
        print(f"     pending sweeps found on the 5-minute chart: "
              f"rule 1 ON {nA:,}   rule 1 OFF {nB:,}")
        sys.stdout.flush()

        # ------------------- reproduction control: R450's native arm A
        lo5, hi5 = d5["low"].to_numpy(), d5["high"].to_numpy()
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

        # ------------------------------------------------ the 2x2 x 4 grid
        for tf in RESOLUTIONS:
            for excl in (True, False):
                for fsb in (True, False):
                    r = run_cell(sym, d5, d1, tf, excl, fsb, cache)
                    if len(r):
                        cells.setdefault((tf, excl, fsb), []).append(r)
            # SENSITIVITY: the exclusion lifted in the sweep scan's pending
            # bookkeeping as well. Labelled separately, never mixed into the
            # 2x2, because it changes the sweep list and not just the entry.
            for fsb in (True, False):
                r = run_cell(sym, d5, d1, tf, False, fsb, cache,
                             sweep_excluded=False)
                if len(r):
                    sens.setdefault((tf, fsb), []).append(r)
            B, A, tal = discarded_population(sym, d5, d1, tf, cache)
            if len(B):
                disc_B.setdefault(tf, []).append(B)
            if len(A):
                disc_A.setdefault(tf, []).append(A)
            for k, v in tal.items():
                tallies.setdefault(tf, dict()).setdefault(k, 0)
                tallies[tf][k] += v
            c = control_at(cache["frames"][tf], tf, sym)
            if len(c):
                ctl.append(c)
            n_on = len(cells.get((tf, True, True), [pd.DataFrame()])[-1]) \
                if cells.get((tf, True, True)) else 0
            n_off = len(cells.get((tf, False, False), [pd.DataFrame()])[-1]) \
                if cells.get((tf, False, False)) else 0
            print(f"     tf={tf:>2}m  frame {len(cache['frames'][tf]):>9,} bars"
                  f"   armA-style {n_on:>7,} entries   armB-style {n_off:>7,}"
                  f"   discarded-by-armA {len(B):>6,}")
            sys.stdout.flush()

    # ------------------------------------------------------------- assemble
    def pool(parts):
        return pd.concat(parts) if parts else pd.DataFrame()

    NA = pd.concat([g.drop_duplicates(subset=DEDUPE_KEY)
                    for _, g in pd.concat(native_A).groupby("sym")])
    C = pool(ctl)
    grid = {k: pool(v) for k, v in cells.items()}
    SENS = {k: pool(v) for k, v in sens.items()}
    DB = {k: pool(v) for k, v in disc_B.items()}
    DA = {k: pool(v) for k, v in disc_A.items()}

    for f in (list(grid.values()) + list(SENS.values()) + list(DB.values())
              + list(DA.values()) + [C, NA]):
        if len(f):
            f["cost_pct"] = f["sym"].map(COST_ALLIN)
    grid = {k: attach_vol(v, vols) for k, v in grid.items()}
    SENS = {k: attach_vol(v, vols) for k, v in SENS.items()}
    DB = {k: attach_vol(v, vols) for k, v in DB.items()}
    DA = {k: attach_vol(v, vols) for k, v in DA.items()}
    C, NA = attach_vol(C, vols), attach_vol(NA, vols)

    # -------------------------------------------------- reproduction controls
    print("\n" + LINE)
    print("REPRODUCTION CONTROLS - is this the same machinery the log "
          "published?")
    print(LINE)
    g1 = grid.get((1, False, False), pd.DataFrame())
    t1, d1n = clustered(g1, "gross_pct")
    print(f"R476 published (tf=1, rule 1 OFF, rule 2 OFF): 71,073 entries, "
          f"+0.1435% of price, t by day 13.77")
    print(f"this file reads:                              {len(g1):,} entries, "
          f"{g1['gross_pct'].mean():+.4f}%, t by day {t1:.2f} over {d1n:,} days")
    g5 = grid.get((5, False, False), pd.DataFrame())
    print(f"\nR490 published (tf=5, arm-B construction):    75,023 entries, "
          f"+0.1045% of price")
    print(f"this file reads:                              {len(g5):,} entries, "
          f"{g5['gross_pct'].mean():+.4f}%")
    g5a = grid.get((5, True, True), pd.DataFrame())
    print(f"\nR450's NATIVE arm A, run unchanged:           {len(NA):,} "
          f"entries, {NA['gross_pct'].mean():+.4f}% of price")
    print(f"tf=5 with rule 1 ON and rule 2 ON:            {len(g5a):,} "
          f"entries, {g5a['gross_pct'].mean():+.4f}%")
    print("  the residual is the ONE-BAR pending-window offset described in "
          "the honest limits;")
    print("  R490's convention is kept so these rows stay comparable to "
          "R490's published ones.")

    # ------------------------------------------------------- PART A: the 2x2
    labels = {(True, True): "rule1 ON  + rule2 ON   (= arm A)",
              (True, False): "rule1 ON  + rule2 OFF",
              (False, True): "rule1 OFF + rule2 ON",
              (False, False): "rule1 OFF + rule2 OFF  (= arm B)"}
    all_rows = []
    for tf in RESOLUTIONS:
        rows = []
        for excl in (True, False):
            for fsb in (True, False):
                d = grid.get((tf, excl, fsb), pd.DataFrame())
                rows.append(profile_row(d, f"{tf:>2}m  {labels[(excl, fsb)]}"))
        rows.append(profile_row(C[C.tf == tf] if len(C) else pd.DataFrame(),
                                f"{tf:>2}m  [random entry control]"))
        show(rows,
             f"PART A - THE 2x2 AT A {tf}-MINUTE TRIGGER",
             "rule 1 = the re-sweep exclusion (a bar through the level cannot "
             "be the break of structure).\nrule 2 = the stop origin (ON = "
             "from the sweep bar, the extreme printed while taking the "
             "level).\nnetR is the mean of PER-TRADE net/stop (R487's "
             "statistic, not a ratio of means); t/day pools\nBTC+ETH+SOL into "
             "one observation per UTC day.")
        all_rows.extend(rows)
    if len(NA):
        show([profile_row(NA, " 5m  [R450 native arm A, verbatim]")],
             "PART A - R450's ARM A EXACTLY AS THE LOG RAN IT")
        all_rows.append(profile_row(NA, "5m R450 native arm A verbatim"))
    pd.DataFrame(all_rows).to_csv(f"{REPO}/step495_table_factorial.csv",
                                  index=False)

    # ---------------------------------------- PART A2: each rule's own effect
    print("\n" + LINE)
    print("PART A2 - EACH RULE'S OWN EFFECT, HELD AGAINST THE OTHER RULE'S "
          "TWO SETTINGS")
    print(LINE)
    print("A main effect that flips sign when the other rule moves is an "
          "interaction, not an effect.")
    print(f"\n{'':<10}{'rule':<14}{'other rule':<14}{'d entries':>11}"
          f"{'d gross%':>11}{'d netR':>10}{'d stop%':>10}")
    eff_rows = []
    for tf in RESOLUTIONS:
        for held in (True, False):
            a = grid.get((tf, True, held), pd.DataFrame())
            b = grid.get((tf, False, held), pd.DataFrame())
            if len(a) and len(b):
                row = dict(tf=tf, rule="rule 1 (re-sweep)",
                           other=f"rule 2 {'ON' if held else 'OFF'}",
                           d_entries=len(b) - len(a),
                           d_gross=b["gross_pct"].mean() - a["gross_pct"].mean(),
                           d_netR=finite_mean(b, "net_R") - finite_mean(a, "net_R"),
                           d_stop=b["stop_pct"].median() - a["stop_pct"].median())
                eff_rows.append(row)
                print(f"{f'tf={tf}m':<10}{row['rule']:<14}{row['other']:<14}"
                      f"{row['d_entries']:>+11,}{row['d_gross']:>+11.4f}"
                      f"{row['d_netR']:>+10.3f}{row['d_stop']:>+10.3f}")
        for held in (True, False):
            a = grid.get((tf, held, True), pd.DataFrame())
            b = grid.get((tf, held, False), pd.DataFrame())
            if len(a) and len(b):
                row = dict(tf=tf, rule="rule 2 (stop)",
                           other=f"rule 1 {'ON' if held else 'OFF'}",
                           d_entries=len(b) - len(a),
                           d_gross=b["gross_pct"].mean() - a["gross_pct"].mean(),
                           d_netR=finite_mean(b, "net_R") - finite_mean(a, "net_R"),
                           d_stop=b["stop_pct"].median() - a["stop_pct"].median())
                eff_rows.append(row)
                print(f"{f'tf={tf}m':<10}{row['rule']:<14}{row['other']:<14}"
                      f"{row['d_entries']:>+11,}{row['d_gross']:>+11.4f}"
                      f"{row['d_netR']:>+10.3f}{row['d_stop']:>+10.3f}")
    print("\n(d = the OFF setting minus the ON setting, so a positive number "
          "means turning the rule OFF raised it.)")
    pd.DataFrame(eff_rows).to_csv(f"{REPO}/step495_table_rule_effects.csv",
                                  index=False)

    # ------------------------- PART A3: the rule's OTHER home, the sweep scan
    rows = []
    for tf in RESOLUTIONS:
        rows.append(profile_row(grid.get((tf, False, False), pd.DataFrame()),
                                f"{tf:>2}m  2x2 arm B (sweep scan strict)"))
        rows.append(profile_row(SENS.get((tf, False), pd.DataFrame()),
                                f"{tf:>2}m  + exclusion lifted in sweep scan"))
        rows.append(profile_row(SENS.get((tf, True), pd.DataFrame()),
                                f"{tf:>2}m  + same, stop from sweep bar"))
    show(rows,
         "PART A3 - SENSITIVITY: THE EXCLUSION'S OTHER HOME, THE SWEEP "
         "SCAN'S PENDING BOOKKEEPING",
         "Held OUT of the 2x2 on purpose: lifting it here changes the SWEEP "
         "LIST, not just which bar\ntriggers, because a confirmation clears "
         "the pending state and lets the next sweep open\nsooner. Every "
         "round in this family since R450 has run this half ON. Reported so "
         "the full\ncost of the `continue` is on the record; NOT a "
         "construction and NOT selectable.")
    pd.DataFrame(rows).to_csv(f"{REPO}/step495_table_sweepscan.csv",
                              index=False)

    # -------------------------------------- PART B: what arm A throws away
    print("\n" + LINE)
    print("PART B - THE ENTRIES ARM A THROWS AWAY, ON A COMMON DENOMINATOR")
    print(LINE)
    print("The sweep list is held FIXED at arm A's own, so both trigger rules "
          "see the SAME pending")
    print("windows. `earlier` = the permissive rule fires sooner inside the "
          "window; `only_B` = arm A")
    print("never fires in that window at all. The discarded entries are "
          "scored under both stop rules.")
    print(f"\n{'frame':<8}{'sweeps':>10}{'identical':>11}{'earlier':>10}"
          f"{'only_B':>9}{'only_A':>9}{'neither':>10}{'% touched':>11}")
    for tf in RESOLUTIONS:
        t = tallies.get(tf, {})
        n = t.get("sweeps", 0)
        touched = (t.get("earlier", 0) + t.get("only_B", 0)) / n * 100 if n else np.nan
        print(f"{f'{tf}m':<8}{n:>10,}{t.get('identical', 0):>11,}"
              f"{t.get('earlier', 0):>10,}{t.get('only_B', 0):>9,}"
              f"{t.get('only_A', 0):>9,}{t.get('neither', 0):>10,}"
              f"{touched:>10.1f}%")
    rows = []
    for tf in RESOLUTIONS:
        rows.append(profile_row(DB.get(tf, pd.DataFrame()),
                                f"{tf:>2}m  discarded, stop from close"))
        rows.append(profile_row(DA.get(tf, pd.DataFrame()),
                                f"{tf:>2}m  discarded, stop from sweep bar"))
        rows.append(profile_row(grid.get((tf, True, True), pd.DataFrame()),
                                f"{tf:>2}m    [arm A, for reference]"))
    show(rows, "PART B - HOW THE DISCARDED ENTRIES ACTUALLY SCORED")
    pd.DataFrame(rows).to_csv(f"{REPO}/step495_table_discarded.csv",
                              index=False)

    # ------------------------------------------- PART B2: matched by the day
    print("\n" + LINE)
    print("PART B2 - THE DISCARDED ENTRIES AGAINST ARM A's OWN, PAIRED BY "
          "UTC DAY")
    print(LINE)
    print("A pooled difference of two populations is not a test; the paired "
          "one is.")
    print(f"\n{'frame':<8}{'shared days':>13}{'d gross%':>11}{'t':>8}"
          f"{'d netR':>10}{'t':>8}")
    pair_rows = []
    for tf in RESOLUTIONS:
        d = DB.get(tf, pd.DataFrame())
        a = grid.get((tf, True, True), pd.DataFrame())
        if not len(d) or not len(a):
            continue
        for col in ("gross_pct", "net_R"):
            pass
        dg = d.groupby(utc_day(d))["gross_pct"].mean()
        ag = a.groupby(utc_day(a))["gross_pct"].mean()
        dn = d["net_R"].replace([np.inf, -np.inf], np.nan)
        an = a["net_R"].replace([np.inf, -np.inf], np.nan)
        dnd = dn.groupby(utc_day(d)).mean()
        and_ = an.groupby(utc_day(a)).mean()
        jg = pd.concat([dg, ag], axis=1, join="inner").dropna()
        jn = pd.concat([dnd, and_], axis=1, join="inner").dropna()
        tg, ng = tstat(jg.iloc[:, 0] - jg.iloc[:, 1])
        tn, nn = tstat(jn.iloc[:, 0] - jn.iloc[:, 1])
        print(f"{f'{tf}m':<8}{ng:>13,}"
              f"{(jg.iloc[:, 0] - jg.iloc[:, 1]).mean():>+11.4f}{tg:>8.2f}"
              f"{(jn.iloc[:, 0] - jn.iloc[:, 1]).mean():>+10.3f}{tn:>8.2f}")
        pair_rows.append(dict(tf=tf, days=ng,
                              d_gross=(jg.iloc[:, 0] - jg.iloc[:, 1]).mean(),
                              t_gross=tg,
                              d_netR=(jn.iloc[:, 0] - jn.iloc[:, 1]).mean(),
                              t_netR=tn))
    print("\n(positive = the entries arm A discards did BETTER than the ones "
          "it keeps, on the same days.)")
    pd.DataFrame(pair_rows).to_csv(f"{REPO}/step495_table_paired.csv",
                                   index=False)

    # ------------------------------------------------- PART C: by coin, tf=5
    print("\n" + LINE)
    print("PART C - THE 5-MINUTE FRAME BY COIN, SO ONE COIN CANNOT CARRY THE "
          "RESULT")
    print(LINE)
    print(f"\n{'coin':<10}{'construction':<28}{'entries':>9}{'gross%':>10}"
          f"{'netR':>9}{'t/day':>8}{'stop%':>9}")
    by_coin = []
    for sym in R.PRIMARY:
        for (excl, fsb), lab in labels.items():
            d = grid.get((5, excl, fsb), pd.DataFrame())
            if not len(d):
                continue
            s = d[d["sym"] == sym]
            if not len(s):
                continue
            t, _ = clustered(s, "net_R")
            print(f"{sym:<10}{lab:<28}{len(s):>9,}"
                  f"{s['gross_pct'].mean():>10.4f}"
                  f"{finite_mean(s, 'net_R'):>9.3f}{t:>8.2f}"
                  f"{s['stop_pct'].median():>9.3f}")
            by_coin.append(dict(sym=sym, construction=lab, entries=len(s),
                                gross=s["gross_pct"].mean(),
                                netR=finite_mean(s, "net_R"), t_netR_day=t,
                                stop=s["stop_pct"].median()))
    pd.DataFrame(by_coin).to_csv(f"{REPO}/step495_table_by_coin.csv",
                                 index=False)

    # ----------------------------------------------- PART D: the spec reading
    print("\n" + LINE)
    print("PART D - WAS ARM A EVER JUSTIFIED FROM HIS TEACHING? (READ, NOT "
          "INFERRED)")
    print(LINE)
    print("""
RULE 1, the re-sweep exclusion. NOT IN THE SPEC, ANYWHERE.
  step431 section 7.4 tabulates sweep against break of structure and the only
  thing it says about the candle is which part of it counts: "trading through
  with a wick is enough to open the pending state" for the sweep, "wick is
  never enough, body close required" for the break. Nothing forbids one
  candle from doing both. step431 section 4b defines the disqualifier and it
  is about REACTION, not about candle bookkeeping: a level traded through
  with no subsequent break of structure "is not a sweep and never becomes
  one". step436 section 4 assigns the timeframes and says nothing about it.
  His own worked short (step431 section 8.1) is a sequence of events, not a
  constraint on which bar may carry them.
  VERDICT: an implementation accident. It is a `continue` statement whose
  position in R450's loop skips the break-of-structure test for any bar that
  is through the level. Nobody wrote it down as a rule because it was never
  read as one.

RULE 2, the stop origin. THE SPEC IS EXPLICIT, AND IT IS ARM A's SIDE.
  step431 section 9.1: "For a short taken after a high was swept: the
  protective exit sits above the extreme reached during the sweep, that is
  above the highest price printed while taking the level. For a long after a
  low was swept: below the lowest price printed while taking the level."
  Arm A measures from the sweep bar and therefore contains the extreme
  printed while taking the level. Arm B starts at the sweep bar's CLOSE and
  can miss it entirely.
  VERDICT: arm A is FAITHFUL here and arm B is not. Every round in this
  family since R450 - R475, R476, R477, R485, R487, R488, R490, R491, R492 -
  has scored arm B's stop. That is recorded as a fact about the back
  catalogue; the table above prices it.

NEITHER VERDICT SELECTS ANYTHING. The crypto slices are spent, so a
construction preferred on the strength of these tables could never be
validated out of sample. Item 16 states its construction in advance.
""")

    print(LINE)
    print("LOOKS CONSUMED: NONE, AND NONE COULD BE. `slice_by_time` is never")
    print("called in this file, no train/val/test split is cut, no cell is")
    print("qualified and no construction is selected. No order was placed, no")
    print("account touched, no live file imported or edited.")
    print(LINE)


if __name__ == "__main__":
    main()
