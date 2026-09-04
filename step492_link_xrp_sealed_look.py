"""
step492_link_xrp_sealed_look.py - ROUND 492

SPEND THE LOOK: THE FAMILY'S PARENT ON LINK AND XRP, 60/20/20, FOR REAL.
(QUEUE ITEM 16)

Research only. No orders. No account. No live file touched, imported or
modified. Nothing here is deployed by this script under any outcome; a
survivor is written up and marked AWAITING DEPLOYMENT REVIEW and nothing
more.

====================================================================
PRE-REGISTRATION. EVERY LINE BELOW WAS FIXED BEFORE ANY SLICE WAS READ.
====================================================================

(1) THE INSTRUMENT THIS ROUND IS SPENDING: **LINKUSD.**

    Item 16 requires the round to say in advance which instrument it is
    spending and why, because these are the last two clean slices this
    family owns. It is LINK, and the three reasons are all properties of
    the instrument that were on the table before a single entry was built:

    - **History.** LINK carries 2021-01-01 -> 2026-07-26, the same 1,627-day
      window BTC's evidence was built on. Its sealed 20% is roughly 406 days;
      XRP's is roughly 187. A look is worth having in proportion to what it
      can conclude, and LINK's sealed slice is more than twice XRP's.
    - **The geometry the machinery assumes.** R489(b) measured the
      structural-stop-to-one-minute-move ratio on entries only, no outcome
      read: LINK 3.57, inside the 3.57-3.83 band five crypto instruments
      share; XRP 4.50, the outlier of the group. The machinery being carried
      here is unchanged, so it is carried to the instrument whose chart
      structure matches the tape it was built on. (This is a statement about
      chart width, not about returns - R489 computed no return on either.)
    - **The cost basis this item mandates.** Item 16 fixes cost as R489's
      SOURCED per-contract figure. On that basis - fee only, the half that is
      primary-sourced - LINK is the best multiple of any instrument on this
      disk, spent or intact (1.99).

    XRPUSD is run to the 80% boundary as a companion and IS REPORTED, because
    item 16 asks for both. **Its final 20% is not read, not summarised and
    not touched under any outcome of any kind**, including the outcome where
    LINK fails and XRP's train/val look magnificent. There is no "best of"
    here and no second cell: at most ONE test look is taken, on LINK, on one
    cell, and if no LINK cell qualifies then no look is taken at all and both
    slices stay sealed.

(2) THE TRIGGER RESOLUTION: **1 MINUTE.**

    Stated here, before either slice is opened, as item 16 requires, and
    justified from HIS method and from nothing else:

      step436 s(timeframes): "**1-minute**: the entry only. Explicitly NOT
      where sweeps are hunted."
      step431 s0: "Finding the entry (confirming the reversal): the 5-minute
      and the 1-minute", and its worked example, step 5: "Wait for a break of
      structure to the downside on the 1-minute."

    He hunts the sweep on the 5-minute and triggers the entry on the
    1-minute. That is what the family's parent is (R450 arm B, re-run at full
    history as R476), and item 16 asks for the parent.

    **R490's resolution profile is not cited, was not consulted in making
    this choice, and no number from it appears anywhere in this file.** R490
    ran under an explicit fence forbidding exactly that, and a resolution
    picked off a spent population's tables would be a selected parameter
    wearing a description's clothes.

(3) THE SELECTION RULE, IF MORE THAN ONE CELL QUALIFIES.

    At most one cell may be looked at. Fixed before the run: **the look goes
    to the qualifying cell with the highest CHOOSING-slice per-trade net R
    t-statistic clustered by UTC day**, ties broken by more choosing-slice
    trades. Choosing on the choosing slice is what the choosing slice is for;
    the middle slice is the gate, not the chooser, and the sealed slice is
    never consulted about which cell to point at it.

(4) QUALIFICATION. Item 16's wording, unchanged and un-negotiated:

    positive expectancy on train AND val, minimum 30 train / 8 val trades,
    read in **per-trade net R with a t clustered by UTC day** (R487's
    statistic, never the ratio of means), AND beating the R450 random-entry
    control on the same machinery on both slices.

    The bar is not lowered and it is not raised: "positive expectancy" means
    mean per-trade net R above zero, exactly as written. The clustered t is
    printed beside every cell as the reading unit, and it is not turned into
    a threshold this round invented.

(5) COST. R489's SOURCED per-contract CDE figure for each instrument's own
    contract, and it decides nothing (owner rule, 2026-07-25):

      LINK PERP (LNP, 50 LINK, $574.85 notional)  fee round trip 0.0522%
      XRP  PERP (XPP, 500 XRP, $693.05 notional)  fee round trip 0.0433%

    Both bind on the $0.15-per-contract-per-side minimum, which is why they
    sit above the 0.04% floor. Carried beside them, as a second read only, is
    R489's ALL-IN figure (that same fee plus its seven-poll median spread
    sample): LINK 0.1043%, XRP 0.0649%. The fee is sourced; the spread is a
    sample, so the fee is the headline and the all-in is the sanity column.
    Gross sits beside every net number so the venue is always separable from
    the method. **No cost declines a trade, gates a cell or ranks an
    instrument here.**

(6) NO TUNING OF ANY KIND, and it is enforced by import rather than by
    promise. Every constant is R450's and is imported, not retyped: the
    two-candle swing, the levels marked on the high timeframes only, the
    sweep hunted on the 5-MINUTE, break of structure as a BODY close, the
    structural stop as the extreme traded between the sweep and the entry,
    the 2-hour pending expiry and the 24-hour hold cap (both OURS), the UTC
    day boundary (ours), all eight levels, all four target settings, both
    directions. Nothing in this file sweeps a parameter, and there is no
    grid beyond the 8 x 4 x 2 the item specifies.

(7) `stop/vol` IS RE-DERIVED ON EACH INSTRUMENT AND NEVER PORTED. R489's
    gold result is the reason: the crypto 3.6 is wrong by four times off
    crypto-like tape. It is measured here on each instrument's own choosing
    slice and reported, and it is used to describe, never to size or select.

(8) 60/20/20 IS CUT ON EACH INSTRUMENT'S OWN 1m/5m OVERLAP WINDOW, per item
    16. LINK's and XRP's boundaries are therefore different calendar dates,
    and both are printed before any cell is scored.

USAGE
  python3 step492_link_xrp_sealed_look.py
"""

import sys

import numpy as np
import pandas as pd

import step450_tjr_crypto_1m as R

REPO = "/Users/wallacechen/cryptobot"
LINE = "=" * 118

# R489 (a1), primary-sourced fee arithmetic. Charged for honest P&L only.
FEE_RT = {"LINKUSD": 0.0522, "XRPUSD": 0.0433}
ALLIN_RT = {"LINKUSD": 0.1043, "XRPUSD": 0.0649}

SPEND = "LINKUSD"           # declared above, before any slice was read
COMPANION = "XRPUSD"        # train/val only, sealed slice never touched
CONTROL_SPACING_MIN = 300   # R450's every-60th-5-minute-bar, expressed in time


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
    """R487's statistic. One mean per UTC day, then t across days. Entries
    that overlap inside a day are ONE draw of the market, not thirty."""
    if not len(res):
        return np.nan, 0
    v = res[col].replace([np.inf, -np.inf], np.nan)
    d = v.groupby(utc_day(res)).mean().dropna()
    return tstat(d)


def fmean(res, col):
    if not len(res):
        return np.nan
    return res[col].replace([np.inf, -np.inf], np.nan).mean()


def daily_vol(sym):
    """R488's yardstick, unchanged: mean |1-minute return| per UTC day, %."""
    b = pd.read_parquet(f"{REPO}/data_alpaca_{sym}_1m.parquet",
                        columns=["t", "close"])
    t = pd.to_datetime(b["t"])
    r = b["close"].pct_change().abs() * 100.0
    f = pd.DataFrame({"t": t, "r": r}).dropna()
    return f.groupby(f["t"].dt.floor("D"))["r"].mean()


# ============================================================ the population
def build(sym):
    """R450's parent, arm B, imported unchanged: sweep hunted on the
    5-minute, entry on the first 1-minute BODY close through the most recent
    confirmed 1-minute swing, stop at the extreme traded between the sweep
    and that entry. Returns one frame per (level, target) cell."""
    d5, d1 = R.prep(sym)
    lo1 = d1["low"].to_numpy()
    hi1 = d1["high"].to_numpy()
    i1n = d5["i1_next"].to_numpy()
    fee = FEE_RT[sym]
    cells = {}
    for col, dirn, lab in R.LEVELS:
        sw, sig5 = R.scan_sweeps(d5, col, dirn)
        if len(sig5) == 0:
            continue
        ent1, swB = R.trigger_1m(d5, d1, sw, dirn)
        if not len(ent1):
            continue
        a1 = i1n[swB]
        stopB = np.array([lo1[max(0, a):b + 1].min() if dirn > 0
                          else hi1[max(0, a):b + 1].max()
                          for a, b in zip(a1, ent1)])
        for rt, rlab in R.TARGETS:
            res = R.simulate(d1, ent1, dirn, stopB, rt, R.MAX_HOLD_MIN,
                             cost=fee)
            if not len(res):
                continue
            # R476's dedupe: two levels can be swept into the SAME entry with
            # the same structural stop, and that is one trade, not two. Within
            # a single (level, target) cell it is a no-op; kept so the cell
            # frames concatenate honestly.
            res = res.drop_duplicates(subset=["sig_i", "sig_t", "stop_pct"])
            res = res.assign(sym=sym, level=lab, dirn=dirn, target=rlab)
            res["allin_pct"] = res["gross_pct"] - ALLIN_RT[sym]
            res["allin_R"] = (res["allin_pct"] / res["stop_pct"]).replace(
                [np.inf, -np.inf], np.nan)
            cells[f"{lab} -> 1m BOS, {rlab}"] = res
    return d5, d1, cells


def control(d1, sym):
    """R450's chance control on the same machinery, spaced by TIME so it is
    as frequent on the 1-minute frame as R450's was on the 5-minute: an
    entry every 300 minutes, stop at the most recent confirmed 1-minute
    swing, both directions, 24-hour hold."""
    fee = FEE_RT[sym]
    out = []
    for dirn in (+1, -1):
        idx = np.arange(0, len(d1) - 1, CONTROL_SPACING_MIN)
        stop = (d1["mr_sl"].to_numpy() if dirn > 0
                else d1["mr_sh"].to_numpy())[idx]
        r = R.simulate(d1, idx, dirn, stop, None, R.MAX_HOLD_MIN, cost=fee)
        if len(r):
            out.append(r.assign(sym=sym, dirn=dirn))
    return pd.concat(out) if out else pd.DataFrame()


# =================================================================== reading
def read_cell(name, res, t_tr, t_va):
    tr, va, te = R.slice_by_time(res, t_tr, t_va)
    t_tr_c, d_tr = clustered(tr, "net_R")
    t_va_c, d_va = clustered(va, "net_R")
    return dict(name=name, n_tr=len(tr), n_va=len(va),
                gross_tr=fmean(tr, "gross_pct"), gross_va=fmean(va, "gross_pct"),
                net_tr=fmean(tr, "net_pct"), net_va=fmean(va, "net_pct"),
                R_tr=fmean(tr, "net_R"), R_va=fmean(va, "net_R"),
                allinR_tr=fmean(tr, "allin_R"), allinR_va=fmean(va, "allin_R"),
                t_tr=t_tr_c, t_va=t_va_c, days_tr=d_tr, days_va=d_va,
                stop_tr=tr["stop_pct"].median() if len(tr) else np.nan,
                win_tr=(tr["net_pct"] > 0).mean() * 100 if len(tr) else np.nan,
                thin=(len(tr) < R.MIN_TR or len(va) < R.MIN_VA))


def show(rows, title, note=""):
    print("\n" + LINE)
    print(title)
    print(LINE)
    if note:
        print(note)
    print(f"\n{'cell':<40}{'n_tr':>7}{'n_va':>6}{'grossTR%':>10}{'netTR%':>9}"
          f"{'netVA%':>9}{'R_tr':>8}{'t_tr/day':>10}{'R_va':>8}{'t_va/day':>10}"
          f"{'stop%':>8}{'win%':>7}  status")
    for r in rows:
        if r["thin"]:
            print(f"{r['name']:<40}{r['n_tr']:>7,}{r['n_va']:>6,}"
                  f"{'':>10}{'':>9}{'':>9}{'':>8}{'':>10}{'':>8}{'':>10}"
                  f"{'':>8}{'':>7}  too few trades")
            continue
        print(f"{r['name']:<40}{r['n_tr']:>7,}{r['n_va']:>6,}"
              f"{r['gross_tr']:>10.4f}{r['net_tr']:>9.4f}{r['net_va']:>9.4f}"
              f"{r['R_tr']:>8.3f}{r['t_tr']:>10.2f}{r['R_va']:>8.3f}"
              f"{r['t_va']:>10.2f}{r['stop_tr']:>8.3f}{r['win_tr']:>7.1f}"
              f"  {r['status']}")


def boundaries(sym):
    """60/20/20 on this instrument's OWN 1m/5m overlap window (item 16)."""
    b5 = R.load(sym, "5m")
    b1 = R.load(sym, "1m")
    t0 = max(b5["t"].iloc[0], b1["t"].iloc[0])
    t1 = min(b5["t"].iloc[-1], b1["t"].iloc[-1])
    span = t1 - t0
    return t0, t0 + span * 0.60, t0 + span * 0.80, t1


# ====================================================================== main
def main():
    print(LINE)
    print("ROUND 492 - QUEUE ITEM 16: THE FAMILY'S PARENT ON LINK AND XRP, "
          "60/20/20, FOR REAL")
    print(LINE)
    print("PRE-REGISTERED BEFORE ANY SLICE WAS READ (full text in the "
          "docstring):")
    print(f"  instrument being SPENT      : {SPEND}   "
          f"(history / stop-vol geometry / sourced-fee multiple)")
    print(f"  companion, train+val ONLY   : {COMPANION}   "
          f"(final 20% not read under ANY outcome)")
    print("  trigger resolution          : 1 MINUTE, from step436 "
          "('1-minute: the entry only') and step431 s0. R490 not cited.")
    print("  selection if >1 qualifies   : highest CHOOSING-slice per-trade "
          "net R t clustered by UTC day; ties -> more trades")
    print("  qualification               : mean per-trade net R > 0 on train "
          "AND val, >=30 train / >=8 val trades, and")
    print("                                beating the R450 random-entry "
          "control on the same machinery on BOTH slices")
    print("  cost (decides nothing)      : sourced CDE fee round trip "
          f"LINK {FEE_RT['LINKUSD']}% / XRP {FEE_RT['XRPUSD']}%;  all-in "
          f"{ALLIN_RT['LINKUSD']}% / {ALLIN_RT['XRPUSD']}% carried beside it")
    print("  tuning                      : none. Every constant imported "
          "from step450 (pending 2h, hold 24h, 8 levels, 4 targets).")

    vols = {}
    store = {}
    bounds = {}
    controls = {}

    for sym in (SPEND, COMPANION):
        t0, t_tr, t_va, t1 = boundaries(sym)
        bounds[sym] = (t0, t_tr, t_va, t1)
        print("\n" + "-" * 118)
        print(f"{sym}  own window {t0:%Y-%m-%d} -> {t1:%Y-%m-%d} UTC   "
              f"({(t1 - t0).days:,} days)")
        print(f"   choosing 60%  {t0:%Y-%m-%d} -> {t_tr:%Y-%m-%d}")
        print(f"   middle   20%  {t_tr:%Y-%m-%d} -> {t_va:%Y-%m-%d}   read once")
        seal = "SEALED - opened only if a cell qualifies" if sym == SPEND \
            else "SEALED - NOT OPENED UNDER ANY OUTCOME (companion)"
        print(f"   final    20%  {t_va:%Y-%m-%d} -> {t1:%Y-%m-%d}   {seal}")

        d5, d1, cells = build(sym)
        store[sym] = cells
        controls[sym] = control(d1, sym)
        vols[sym] = daily_vol(sym)
        print(f"   5m bars {len(d5):,}   1m bars {len(d1):,}   "
              f"cells built {len(cells)}")

    # -------------------------------------------------- stop/vol, re-derived
    print("\n" + LINE)
    print("stop/vol RE-DERIVED ON EACH INSTRUMENT'S OWN CHOOSING SLICE "
          "(never ported - R489's gold result)")
    print(LINE)
    print(f"{'instrument':<14}{'entries':>10}{'days':>8}{'stop%med':>11}"
          f"{'vol%med':>10}{'stop/vol':>11}{'p25':>8}{'p75':>8}")
    for sym in (SPEND, COMPANION):
        t0, t_tr, t_va, t1 = bounds[sym]
        allc = pd.concat([c for c in store[sym].values()])
        allc = allc.drop_duplicates(subset=["sig_i", "sig_t", "stop_pct"])
        tr = allc[allc.sig_t < t_tr]
        day = utc_day(tr)
        v = vols[sym].reindex(day).to_numpy()
        ratio = pd.Series(tr["stop_pct"].to_numpy() / v).replace(
            [np.inf, -np.inf], np.nan).dropna()
        print(f"{sym:<14}{len(tr):>10,}{day.nunique():>8,}"
              f"{tr['stop_pct'].median():>11.4f}{np.nanmedian(v):>10.4f}"
              f"{ratio.median():>11.2f}{ratio.quantile(.25):>8.2f}"
              f"{ratio.quantile(.75):>8.2f}")

    # ------------------------------------------------------- the two tables
    qualifiers = {}
    for sym in (SPEND, COMPANION):
        t0, t_tr, t_va, t1 = bounds[sym]
        ctl = controls[sym]
        ctr, cva, _ = R.slice_by_time(ctl, t_tr, t_va)
        c_tr, c_va = fmean(ctr, "net_R"), fmean(cva, "net_R")
        ct_tr, _ = clustered(ctr, "net_R")
        ct_va, _ = clustered(cva, "net_R")

        rows = []
        for nm, res in store[sym].items():
            r = read_cell(nm, res, t_tr, t_va)
            if r["thin"]:
                r["status"] = "thin"
            else:
                pos = (r["R_tr"] > 0) and (r["R_va"] > 0)
                beats = (r["R_tr"] > c_tr) and (r["R_va"] > c_va)
                r["status"] = ("QUALIFIES" if (pos and beats) else
                               "reject (below control)" if pos else "reject")
            rows.append(r)
        rows.sort(key=lambda r: -(r["t_tr"] if np.isfinite(r.get("t_tr", np.nan))
                                  else -99))
        seal = ("this instrument's sealed slice may be opened for ONE cell"
                if sym == SPEND else
                "COMPANION - no look is available here under any outcome")
        show(rows, f"{sym}  -  all {len(rows)} cells, choosing and middle "
                   f"slices only", seal)
        print(f"\n  R450 RANDOM-ENTRY CONTROL, same machinery, {sym}: "
              f"choosing per-trade net R {c_tr:+.3f} (t/day {ct_tr:+.2f}, "
              f"n {len(ctr):,})   middle {c_va:+.3f} "
              f"(t/day {ct_va:+.2f}, n {len(cva):,})")
        q = [r for r in rows if r["status"] == "QUALIFIES"]
        n_scored = len([r for r in rows if not r["thin"]])
        print(f"  {n_scored} cells scored, {len(q)} qualify.")
        print(f"  EXPECTED BY CHANCE (R88/R100): a zero-edge symmetric cell "
              f"clears two slices about 1 time in 4, so roughly "
              f"{n_scored / 4:.0f} of {n_scored} would qualify on luck alone. "
              f"Read {len(q)} against that number, not against zero.")
        qualifiers[sym] = q

    # ------------------------------------------------------------- the look
    print("\n" + LINE)
    print("THE LOOK")
    print(LINE)
    q = qualifiers[SPEND]
    print(f"The declared spend is {SPEND}. {COMPANION}'s final 20% is not "
          f"read here and is not read below, whatever {COMPANION}'s table "
          f"says above.")
    if not q:
        print(f"\nNO CELL QUALIFIES ON {SPEND}. **NO LOOK IS TAKEN.** Both "
              f"instruments' final 20% remain SEALED and INTACT. The round "
              f"logs the failure, which is the outcome the protocol is "
              f"built to make cheap.")
        return

    q.sort(key=lambda r: (-(r["t_tr"] if np.isfinite(r["t_tr"]) else -99),
                          -r["n_tr"]))
    pick = q[0]
    print(f"\n{len(q)} cell(s) qualified. The pre-registered selection rule "
          f"(highest choosing-slice per-trade net R t clustered by UTC day) "
          f"points at exactly one:")
    print(f"\n    {pick['name']}   on {SPEND}")
    print(f"    choosing: n {pick['n_tr']:,}  per-trade net R "
          f"{pick['R_tr']:+.3f}  t/day {pick['t_tr']:+.2f}  over "
          f"{pick['days_tr']:,} days")
    print(f"    middle  : n {pick['n_va']:,}  per-trade net R "
          f"{pick['R_va']:+.3f}  t/day {pick['t_va']:+.2f}  over "
          f"{pick['days_va']:,} days")
    print("\n>>> OPENING THE SEALED 20% OF LINKUSD, ONCE, FOR THIS ONE CELL. "
          "THE SLICE IS SPENT FROM THIS LINE ON. <<<")

    t0, t_tr, t_va, t1 = bounds[SPEND]
    res = store[SPEND][pick["name"]]
    _, _, te = R.slice_by_time(res, t_tr, t_va)
    tR, dR = clustered(te, "net_R")
    tG, _ = clustered(te, "gross_pct")
    ctl = controls[SPEND]
    _, _, cte = R.slice_by_time(ctl, t_tr, t_va)
    ct, _ = clustered(cte, "net_R")

    print(f"\n{'':<4}{'slice':<12}{'n':>8}{'days':>7}{'gross%':>10}"
          f"{'net%':>10}{'net R':>9}{'t/day':>8}{'allin R':>10}"
          f"{'stop%':>9}{'win%':>7}")
    for lab, d in (("choosing", res[res.sig_t < t_tr]),
                   ("middle", res[(res.sig_t >= t_tr) & (res.sig_t < t_va)]),
                   ("SEALED", te)):
        tt, dd = clustered(d, "net_R")
        print(f"{'':<4}{lab:<12}{len(d):>8,}{dd:>7,}"
              f"{fmean(d,'gross_pct'):>10.4f}{fmean(d,'net_pct'):>10.4f}"
              f"{fmean(d,'net_R'):>9.3f}{tt:>8.2f}{fmean(d,'allin_R'):>10.3f}"
              f"{d['stop_pct'].median():>9.3f}"
              f"{(d['net_pct']>0).mean()*100:>7.1f}")

    print(f"\n    sealed slice {t_va:%Y-%m-%d} -> {t1:%Y-%m-%d}   "
          f"{(t1 - t_va).days:,} days, {dR:,} of them with an entry")
    print(f"    sealed gross t clustered by UTC day : {tG:+.2f}")
    print(f"    sealed per-trade net R t by day     : {tR:+.2f}")
    print(f"    same-machinery random control there : per-trade net R "
          f"{fmean(cte,'net_R'):+.3f}  (t/day {ct:+.2f}, n {len(cte):,})")

    survived = (fmean(te, "net_R") > 0) and (fmean(te, "net_R") > fmean(cte, "net_R"))
    print("\n" + "-" * 118)
    if survived:
        print("VERDICT: the cell is POSITIVE on all three windows and beats "
              "the random control on the sealed slice.")
        print("*** AWAITING DEPLOYMENT REVIEW. NOTHING IS DEPLOYED BY THIS "
              "SCRIPT. Wallace decides this in an interactive session. ***")
    else:
        print("VERDICT: the cell FAILS on the sealed slice. Nothing is "
              "proposed and nothing could be.")
    print(f"THE LOOK IS SPENT. {SPEND}'s final 20% is now closed to this "
          f"family forever. {COMPANION}'s remains INTACT and unread.")
    print("-" * 118)


if __name__ == "__main__":
    main()
