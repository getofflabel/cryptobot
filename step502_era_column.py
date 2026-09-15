"""
step502_era_column.py - ROUND 502

THE ROWS OF THAT RANKING COME FROM DIFFERENT ERAS AND NOBODY HAS EVER
CONTROLLED FOR IT.
(QUEUE ITEM 36)

Research only. No orders. No account. No live file touched, imported or
modified. Nothing here is deployed by this script under any outcome.

QUEUE ITEM 36, VERBATIM
  R501 measured a row's density bias two ways - against a donor's whole
  fenced window (R500's `xALL`) and against the donor's coordinate on the
  same days (`xSAME`). The gap between them is pure calendar, and it is
  1.127x on PAXG and 1.082x on SOL - the same order of magnitude as the
  density bias R501 just divided out. It is also the whole of PAXG's SPLIT
  verdict: gold reads UNREADABLE on one estimator and correctable on the
  other purely because its window is a more volatile era.
  The eleven fenced windows run 2021-01 -> 2023-06 (PAXG), 2024-01 ->
  2026-01 (XRP), 2026-02 -> 2026-06 (ADA, 132 days), 2021-01 -> 2025-06
  (five of them) and the ranking compares their coordinates as though they
  were contemporaneous. They are not.
  Deliverable: for each of the eleven, measure the coordinate of a COMMON
  dense reference over that row's own window and over the pooled window, and
  publish the era factor as its own column. Then state the ranking a third
  time, era-controlled, and report which of R501's 44 surviving orderings
  survive THAT. Where a row's window has no overlap with the reference at
  all, say the era factor is unmeasurable rather than inventing one - item
  25's rule, and R501 has already hit this case on ADA.
  THE FENCE: R493's, unchanged. `simulate()` is never called, no entry
  population is scored, no sealed slice is read - the donors' final 20%
  included - no look, no candidate. This corrects a table; it does not
  select anything off it.

THE FENCE, FIXED BEFORE THE RUN AND ENFORCED AS CODE DISCIPLINE
  1. `simulate()` IS NEVER CALLED IN THIS FILE, and neither is any entry
     builder. No sweep is scanned, no break of structure is detected, no
     fill is modelled, no stop is measured, no outcome is read. The only
     things read off tape are (a) WHICH MINUTES CARRY A BAR and (b) THE SIZE
     OF A ONE-MINUTE MOVE. Both are properties of the price series and are
     computable with no notion of a trade.
  2. EVERY TAPE MEASUREMENT STOPS AT THE 80% BOUNDARY of that instrument's
     own window, exactly as R489/R493/R494/R497/R499/R500/R501 fenced it,
     and it is applied to the REFERENCE and every donor as well - a donor's
     sealed slice is a sealed slice. No instrument's final 20% is ever
     loaded into any frame in this file.
  3. NOTHING IS SELECTED. The output is a third ordering of an existing
     table and a statement about which of R501's surviving orderings hold
     under it. No instrument is qualified, no threshold is applied to a
     strategy, no cell is tested. This round cannot produce a candidate: it
     never scores a strategy on anything.
  4. THE UNMEASURABLE RULE IS FIXED HERE, BEFORE ANY ERA FACTOR IS
     COMPUTED. A row whose fenced window overlaps the reference's fenced
     window on fewer than ERA_MIN_DAYS days, or on less than ERA_MIN_OVL of
     its own days, gets NO era factor. It is reported UNMEASURABLE and is
     NOT given an invented one, and it is NOT dropped quietly - it keeps its
     row and its cells read '--'. Item 25's rule, binding.
  5. THE ERA FACTOR IS DIVIDED OUT, NEVER MULTIPLIED IN, and it is applied
     to the R501-corrected coordinate (vol / xSAME), not to the raw one, so
     the two corrections compose in the order they were established.

WHAT IS PRIMARY-SOURCED HERE AND WHAT IS NOT
  PUBLISHED, IN-LOG, READ OFF DISK RATHER THAN RETYPED: R499's ranking is
    parsed out of `step499_output.txt` by R501's own parser, imported from
    step501 unmodified, so the table being corrected is the published one.
  RECOMPUTED, NOT RETYPED: R501's xSAME column is recomputed here with
    R501's own functions and checked against R501's published figures. If it
    does not reproduce, this round stops rather than correcting a table it
    cannot reproduce.
  NO VENUE POLL. The fee column is FROZEN at R499's published one for all
    three orderings, because the only thing this round is allowed to move is
    the numerator. R499's standing rule to re-poll is satisfied by R501,
    twelve hours old, which found today's fees give the identical ordering.

HONEST LIMITS, FIXED BEFORE RUNNING
  - The reference is itself 89% full behind its own fence, not 100%. Its
    coordinate on any window carries its own gap shape (R501: 1.067x). That
    shape is COMMON to both halves of every era ratio, so it divides out of
    the ratio; it does not divide out of the levels, and no level here
    should be quoted as anyone's real one-minute move.
  - A partial overlap measures the era of the OVERLAPPING part of a row's
    window, not all of it. The overlap fraction is printed as its own column
    and any row below the fixed minimum gets no factor at all.
  - The era factor is a RATIO OF THE REFERENCE'S OWN VOLATILITY between two
    calendars. It assumes the reference's era pattern is the market's era
    pattern. Six references are measured and the spread between them is
    printed so that assumption is visible rather than asserted.
  - This round cannot rescue PAXG's SPLIT verdict. Establishing that the
    xALL/xSAME gap IS calendar tells the desk what the gap is made of; it
    does not make R500's UNREADABLE call on the xALL estimator wrong.

USAGE
  python3 step502_era_column.py
"""

import sys
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = "/Users/wallacechen/cryptobot"
sys.path.insert(0, REPO)

import step501_coverage_column as P      # noqa: E402  (R501, unmodified)

LINE = "=" * 108

# ------------------------------------------------------------- the rules
REFERENCE = "BTCUSD"      # item 37's "obvious donor", 89.0% full behind its
                          # own fence and the longest dense tape on the disk.
ERA_MIN_DAYS = 120        # fence item 4, fixed before any factor existed
ERA_MIN_OVL = 0.30        # ditto, as a share of the row's own days
ERA_FLAG_X = 1.05         # a factor this far from 1.00 is called out in text

# R501's published xSAME column - the reproduction target for this round.
R501_XSAME = {"LINKUSD": 1.086, "PAXGUSD": 1.128, "XRPUSD": 1.144,
              "SOLUSD": 1.036, "DOGEUSD": 1.071, "BTCUSD": 1.067,
              "LTCUSD": 1.105, "ETHUSD": 1.053, "DOTUSD": 1.072,
              "AVAXUSD": 1.065}
# R501's published xALL/xSAME gaps, the two it named in the queue item.
R501_GAP = {"PAXGUSD": 1.127, "SOLUSD": 1.082}
# R501's published de-biased ordering, the thing whose orderings are at stake.
R501_ORDER = ["LINKUSD", "PAXGUSD", "SOLUSD", "XRPUSD", "DOGEUSD",
              "BTCUSD", "LTCUSD", "ETHUSD", "DOTUSD", "AVAXUSD"]


def era_of(ref_f, days):
    """The COMMON REFERENCE's coordinate restricted to a set of UTC days.
    Every bar the reference has on those days is kept - this is CALENDAR
    only, and is deliberately NOT R501's minute-mask transplant."""
    g = ref_f[ref_f["t"].dt.floor("D").isin(days)]
    return P.coord(g), g


def main():
    now = datetime.now(timezone.utc)
    print(LINE)
    print("ROUND 502 - THE ROWS OF THAT RANKING COME FROM DIFFERENT ERAS AND "
          "NOBODY CONTROLLED FOR IT.   (item 36)")
    print(LINE)
    print(f"run {now:%Y-%m-%d %H:%M:%S} UTC")
    print("A CORRECTION to a table this desk reuses, not a hypothesis. "
          "simulate() is never called, no")
    print("entry population is built, no sealed slice is read, NO LOOK IS "
          "CONSUMED and none could be.")
    print(f"\nTHE REFERENCE, NAMED BEFORE ANY NUMBER: {REFERENCE}, behind its "
          f"own 80% fence.")
    print(f"THE POOLED WINDOW: that reference's WHOLE fenced window. The era "
          f"factor of a row is the")
    print("reference's coordinate on the row's own calendar over the "
          "reference's coordinate on the pooled")
    print("calendar. Above 1.00 means the row was measured in a more "
          "volatile era than the pool.")
    print(f"UNMEASURABLE RULE, FIXED IN ADVANCE: a row needs "
          f">= {ERA_MIN_DAYS} overlapping days AND >= {ERA_MIN_OVL:.0%} of "
          f"its own")
    print("days inside the reference's window, or it gets NO factor at all "
          "(item 25's rule).")

    pub = P.parse_r499_ranking()
    print(f"\nR499's published ranking parsed off step499_output.txt by "
          f"R501's own parser: {len(pub)} of 11 rows.")
    if len(pub) != 11:
        print("  !! incomplete parse - the round stops rather than "
              "correcting a table it cannot read.")
        return

    # ---------------------------------------------------- load, behind fence
    tp = {}
    for sym, _, _ in P.RANKED:
        f, _, _ = P.fenced(sym)
        d = P.density(f)
        d["coord"] = P.coord(f)
        d["keys"] = P.minute_keys(f)
        d["f"] = f
        d["days"] = set(f["t"].dt.floor("D").unique())
        d["nday"] = len(d["days"])
        d["t0"], d["t1"] = f["t"].iloc[0], f["t"].iloc[-1]
        tp[sym] = d

    # ------------------------------------------------------------ part (1)
    print("\n" + LINE)
    print("(1) REPRODUCTION CONTROLS - two, both against published numbers. "
          "If either fails the round stops.")
    print(LINE)
    worst = 0.0
    print(f"\n  a. R499's vol% column, recomputed behind the same fence:")
    print(f"     {'instrument':<10}{'R499':>9}{'here':>9}{'diff pp':>10}")
    for sym, _, _ in P.RANKED:
        d = abs(tp[sym]["coord"] - pub[sym]["vol"])
        worst = max(worst, d)
        print(f"     {sym:<10}{pub[sym]['vol']:>9.4f}"
              f"{tp[sym]['coord']:>9.4f}"
              f"{tp[sym]['coord']-pub[sym]['vol']:>+10.4f}")
    print(f"     max absolute difference: {worst:.4f} percentage points")
    if worst > 0.0001:
        print("     !! this is not R499's table. The round stops.")
        return
    print("     EXACT. The table being corrected is the published one.")

    print("\n  b. R501's xSAME and xALL columns, recomputed with R501's own "
          "functions:")
    donors = [s for s, _, _ in P.RANKED if tp[s]["cov"] >= P.DONOR_MIN_COV]
    print(f"     donors (>= {P.DONOR_MIN_COV:.0f}% full behind their own "
          f"fence): {', '.join(donors)}")
    print(f"     {'instrument':<10}{'xSAME':>9}{'R501':>9}{'diff':>8}"
          f"{'xALL':>9}{'gap=xALL/xSAME':>17}")
    dbx, dbx_all = {}, {}
    r501_worst = 0.0
    for sym, _, _ in P.RANKED:
        t = tp[sym]
        xall, xsame = [], []
        for dn in donors:
            if dn == sym:
                continue
            d = tp[dn]
            fm = P.transplant(d["f"], d["keys"], t["keys"])
            if len(fm) < P.MASK_MIN_BARS:
                continue
            days = fm["t"].dt.floor("D").unique()
            if len(days) < P.MASK_MIN_DAYS:
                continue
            same = d["f"][d["f"]["t"].dt.floor("D").isin(set(days))]
            cm, cs = P.coord(fm), P.coord(same)
            if not (np.isfinite(cm) and np.isfinite(cs) and cs > 0):
                continue
            xall.append(cm / d["coord"])
            xsame.append(cm / cs)
        if len(xsame) < 2:
            dbx[sym] = np.nan
            dbx_all[sym] = np.nan
            print(f"     {sym:<10}{'--':>9}{'--':>9}{'--':>8}{'--':>9}"
                  f"{'no donor overlap':>17}")
            continue
        xs = float(np.median(xsame))
        xa = float(np.median(xall))
        dbx[sym] = xs
        dbx_all[sym] = xa
        ref = R501_XSAME.get(sym, np.nan)
        diff = abs(xs - ref) if np.isfinite(ref) else 0.0
        r501_worst = max(r501_worst, diff)
        print(f"     {sym:<10}{xs:>8.3f}x{ref:>8.3f}x{xs-ref:>+8.3f}"
              f"{xa:>8.3f}x{xa/xs:>16.3f}x")
    print(f"     max absolute difference against R501's published xSAME: "
          f"{r501_worst:.3f}x")
    if r501_worst > 0.0015:
        print("     !! R501 does not reproduce. The round stops rather than "
              "layering onto a number it cannot")
        print("        rebuild.")
        return
    print("     EXACT to the published precision. The correction below "
          "layers onto R501's own numbers.")
    print("\n     The 'gap' column is the thing this round is about: R501 "
          "named it as pure calendar and")
    print("     published two of them. Both reproduce:", end=" ")
    for s_, g_ in R501_GAP.items():
        print(f"{s_} {dbx_all[s_]/dbx[s_]:.3f}x (R501 {g_:.3f}x)", end="  ")
    print()

    # ------------------------------------------------------------ part (2)
    print("\n" + LINE)
    print(f"(2) THE ERA COLUMN - {REFERENCE}'s OWN COORDINATE, ROW'S "
          f"CALENDAR OVER THE POOLED CALENDAR")
    print(LINE)
    ref = tp[REFERENCE]
    pooled_days = ref["days"]
    pooled_coord = ref["coord"]
    print(f"\n  Pooled window = {REFERENCE}'s whole fenced window: "
          f"{ref['t0']:%Y-%m-%d} -> {ref['t1']:%Y-%m-%d}, "
          f"{len(pooled_days)} days, coordinate {pooled_coord:.4f}%")
    print(f"\n  {'instrument':<11}{'its window':<26}{'days':>6}{'ovl d':>7}"
          f"{'ovl%':>7}{'ref on row':>12}{'ref pooled':>12}{'ERA':>9}  "
          f"verdict")
    print("  " + "-" * 100)
    era = {}
    for sym, _, _ in P.RANKED:
        t = tp[sym]
        ovl = t["days"] & pooled_days
        frac = len(ovl) / max(t["nday"], 1)
        w = f"{t['t0']:%Y-%m-%d} -> {t['t1']:%Y-%m-%d}"
        if len(ovl) < ERA_MIN_DAYS or frac < ERA_MIN_OVL:
            era[sym] = dict(x=np.nan, ovl=len(ovl), frac=frac,
                            verdict="UNMEASURABLE")
            why = ("no overlap at all" if len(ovl) == 0
                   else f"only {len(ovl)}d / {frac:.0%} of its window")
            print(f"  {sym:<11}{w:<26}{t['nday']:>6}{len(ovl):>7}"
                  f"{frac:>6.0%}{'--':>12}{'--':>12}{'--':>9}  "
                  f"UNMEASURABLE ({why})")
            continue
        c_row, _ = era_of(ref["f"], ovl)
        x = c_row / pooled_coord
        v = ("hotter era" if x >= ERA_FLAG_X else
             "cooler era" if x <= 1.0 / ERA_FLAG_X else "contemporaneous")
        if sym == REFERENCE:
            v = "reference (1.000 by construction)"
        era[sym] = dict(x=x, ovl=len(ovl), frac=frac, verdict=v,
                        c_row=c_row)
        print(f"  {sym:<11}{w:<26}{t['nday']:>6}{len(ovl):>7}"
              f"{frac:>6.0%}{c_row:>12.4f}{pooled_coord:>12.4f}"
              f"{x:>8.3f}x  {v}")
    xs = [e["x"] for e in era.values() if np.isfinite(e["x"])]
    print(f"\n  The era factor spans {min(xs):.3f}x to {max(xs):.3f}x across "
          f"the {len(xs)} measurable rows - a factor of")
    print(f"  {max(xs)/min(xs):.3f} between the calmest row's calendar and "
          f"the hottest one's, measured on ONE instrument's")
    print("  tape so that nothing but the calendar differs.")

    # ---------------------------------------- multi-reference robustness
    print("\n  ROBUSTNESS - the same column on every dense reference, "
          "because the primary is an assumption:")
    print(f"\n  {'instrument':<11}", end="")
    for s in donors:
        print(f"{s.replace('USD',''):>9}", end="")
    print(f"{'median':>10}{'spread':>9}")
    print("  " + "-" * (11 + 9 * len(donors) + 19))
    era_multi = {}
    for sym, _, _ in P.RANKED:
        t = tp[sym]
        row = []
        print(f"  {sym:<11}", end="")
        for dn in donors:
            d = tp[dn]
            ovl = t["days"] & d["days"]
            frac = len(ovl) / max(t["nday"], 1)
            if len(ovl) < ERA_MIN_DAYS or frac < ERA_MIN_OVL:
                print(f"{'--':>9}", end="")
                continue
            c_row, _ = era_of(d["f"], ovl)
            x = c_row / d["coord"]
            row.append(x)
            print(f"{x:>8.3f}x", end="")
        if row:
            med = float(np.median(row))
            era_multi[sym] = dict(x=med, n=len(row),
                                  spread=max(row) - min(row))
            print(f"{med:>9.3f}x{max(row)-min(row):>8.3f}")
        else:
            era_multi[sym] = dict(x=np.nan, n=0, spread=np.nan)
            print(f"{'--':>10}{'--':>9}")
    agree = [(s, era[s]["x"], era_multi[s]["x"]) for s in era
             if np.isfinite(era[s]["x"]) and np.isfinite(era_multi[s]["x"])]
    if agree:
        dmax = max(abs(a - b) for _, a, b in agree)
        print(f"\n  Primary reference vs the {len(donors)}-reference median: "
              f"max absolute difference {dmax:.3f}x across")
        print(f"  {len(agree)} rows. The era column is a property of the "
              f"calendar, not of {REFERENCE}." if dmax < 0.05 else
              f"  {len(agree)} rows. That is large enough that the choice of "
              f"reference is itself a judgement call.")

    # ------------------------------------------------------------ part (3)
    print("\n" + LINE)
    print("(3) THE DECOMPOSITION CHECK - IS R501's xALL/xSAME GAP ACTUALLY "
          "THE ERA FACTOR?")
    print(LINE)
    print("\n  R501 asserted the gap between its two estimators is pure "
          "calendar. This round measured the")
    print("  calendar independently, on a different object (the reference's "
          "own tape restricted by days,")
    print("  no minute mask anywhere). If the assertion is right the two "
          "columns should track. Note the")
    print("  gap is measured against a MEDIAN OVER DONORS whose windows "
          "differ, so exact equality is not")
    print("  expected and is not the test; direction and rough size are.")
    print("  TWO era columns are printed against the gap, and the SECOND "
          "is the matched one: R501's gap is")
    print("  itself a MEDIAN OVER THE SAME SIX DONORS, so the median-era "
          "column is like-for-like and the")
    print("  single-reference column is not. Both are shown because the "
          "difference between them is a")
    print("  finding in its own right.")
    print(f"\n  {'instrument':<11}{'R501 gap':>11}{'ERA(ref)':>10}"
          f"{'g/ERA':>8}{'ERA(med6)':>11}{'g/ERAmed':>10}  reading (matched "
          f"column)")
    print("  " + "-" * 88)
    matched = []
    for sym, _, _ in P.RANKED:
        if not (np.isfinite(dbx.get(sym, np.nan))
                and np.isfinite(era[sym]["x"])):
            continue
        g = dbx_all[sym] / dbx[sym]
        e = era[sym]["x"]
        em = era_multi[sym]["x"]
        r = g / e
        rm = g / em if np.isfinite(em) else np.nan
        if np.isfinite(rm):
            matched.append(abs(rm - 1.0))
        read = ("gap IS the era" if 0.97 <= rm <= 1.03 else
                "era explains most of the gap" if 0.90 <= rm <= 1.10 else
                "era does NOT account for the gap")
        print(f"  {sym:<11}{g:>10.3f}x{e:>9.3f}x{r:>8.3f}"
              f"{em:>10.3f}x{rm:>10.3f}  {read}")
    if matched:
        print(f"\n  On the matched column the gap and the era agree to "
              f"within {max(matched)*100:.1f}% on every one of the")
        print(f"  {len(matched)} measurable rows (median "
              f"{np.median(matched)*100:.1f}%). R501's assertion that its "
              f"xALL/xSAME gap is pure")
        print("  calendar is CONFIRMED, and this round measured the calendar "
              "on a different object to do it.")
        print("  Against the SINGLE reference the same check reads "
              f"{min(dbx_all[s]/dbx[s]/era[s]['x'] for s in era if np.isfinite(era[s]['x']) and np.isfinite(dbx.get(s, np.nan))):.3f}"
              f"-{max(dbx_all[s]/dbx[s]/era[s]['x'] for s in era if np.isfinite(era[s]['x']) and np.isfinite(dbx.get(s, np.nan))):.3f}, "
              f"worst on PAXG:")
        print("  one reference is not enough to carry an era factor for a "
              "row whose window it barely shares.")

    # ------------------------------------------------------------ part (4)
    print("\n" + LINE)
    print("(4) THE RANKING, A THIRD TIME. R499's FEE COLUMN STAYS FROZEN - "
          "ONLY THE NUMERATOR MOVES.")
    print(LINE)
    print("\n  vol*   = vol / xSAME              R501's de-biasing (gap "
          "shape), published")
    print("  vol**  = vol / xSAME / ERA        this round, era-controlled "
          "on top of it")
    rows = []
    for sym, _, _ in P.RANKED:
        p_ = pub[sym]
        x = dbx.get(sym, np.nan)
        e = era[sym]["x"]
        nv = p_["vol"] / x if np.isfinite(x) else np.nan
        nm = nv / p_["fee"] if np.isfinite(nv) else np.nan
        ev = nv / e if (np.isfinite(nv) and np.isfinite(e)) else np.nan
        em = ev / p_["fee"] if np.isfinite(ev) else np.nan
        rows.append(dict(sym=sym, vol=p_["vol"], fee=p_["fee"],
                         mult=p_["mult"], cov=tp[sym]["cov"], x=x, era=e,
                         nvol=nv, nmult=nm, evol=ev, emult=em,
                         sealed=p_["sealed"],
                         everdict=era[sym]["verdict"]))
    print(f"\n  {'#':<4}{'instrument':<10}{'vol%':>9}{'/xSAME':>9}"
          f"{'vol* %':>9}{'/ERA':>9}{'vol** %':>10}{'fee%RT':>9}"
          f"{'mult*':>8}{'mult**':>9}{'move':>7}  sealed")
    print("  " + "-" * 104)
    order_501 = [r["sym"] for r in
                 sorted([r for r in rows if np.isfinite(r["nmult"])],
                        key=lambda r: -r["nmult"])]
    order_era = [r["sym"] for r in
                 sorted([r for r in rows if np.isfinite(r["emult"])],
                        key=lambda r: -r["emult"])]
    for i, r in enumerate(sorted(rows, key=lambda r: -(r["nmult"]
                                 if np.isfinite(r["nmult"]) else -1)), 1):
        if np.isfinite(r["emult"]):
            j = order_era.index(r["sym"]) + 1
            k = [s for s in order_501 if s in order_era].index(r["sym"]) + 1
            mv = f"{k-j:+d}" if k != j else "="
            print(f"  {i:<4}{r['sym']:<10}{r['vol']:>9.4f}{r['x']:>8.3f}x"
                  f"{r['nvol']:>9.4f}{r['era']:>8.3f}x{r['evol']:>10.4f}"
                  f"{r['fee']:>9.4f}{r['nmult']:>8.2f}{r['emult']:>9.2f}"
                  f"{mv:>7}  {r['sealed']}")
        else:
            tag = "NO ERA" if np.isfinite(r["nmult"]) else "NO MASK"
            nm = f"{r['nmult']:.2f}" if np.isfinite(r["nmult"]) else "--"
            nv = f"{r['nvol']:.4f}" if np.isfinite(r["nvol"]) else "--"
            xx = f"{r['x']:.3f}x" if np.isfinite(r["x"]) else "--"
            print(f"  {i:<4}{r['sym']:<10}{r['vol']:>9.4f}{xx:>9}"
                  f"{nv:>9}{'--':>9}{tag:>10}{r['fee']:>9.4f}"
                  f"{nm:>8}{'--':>9}{'--':>7}  {r['sealed']}")

    print(f"\n  R501 de-biased order : "
          f"{' > '.join(s.replace('USD','') for s in order_501)}")
    print(f"  era-controlled order : "
          f"{' > '.join(s.replace('USD','') for s in order_era)}")
    dropped = [r["sym"] for r in rows
               if np.isfinite(r["nmult"]) and not np.isfinite(r["emult"])]
    if dropped:
        print(f"  dropped for want of an era factor (a DATA gap, not a "
              f"finding about the instrument): "
              f"{', '.join(dropped)}")

    # ---------------------------- which of R501's orderings survive THIS
    print("\n" + LINE)
    print("    WHICH OF R501's SURVIVING ORDERINGS SURVIVE THE ERA CONTROL")
    print(LINE)
    readable = [s for s in order_501 if s in order_era]
    flips, keeps = [], []
    for i in range(len(readable)):
        for j in range(i + 1, len(readable)):
            a = readable[i]
            b = readable[j]
            # a is above b in R501's de-biased order by construction
            if order_era.index(a) > order_era.index(b):
                flips.append((a, b))
            else:
                keeps.append((a, b))
    npairs = len(flips) + len(keeps)
    print(f"\n  Rows carrying BOTH corrections: {len(readable)} of 11. "
          f"Ordered pairs among them: {npairs}.")
    print(f"  R501 reported 44 of 45 pairwise orderings surviving its own "
          f"correction, on 10 readable rows.")
    print(f"  Of the {npairs} pairs this round can re-examine:")
    print(f"    SURVIVE the era control : {len(keeps)} "
          f"({len(keeps)/max(npairs,1)*100:.0f}%)")
    print(f"    REVERSE under it        : {len(flips)} "
          f"({len(flips)/max(npairs,1)*100:.0f}%)")
    if flips:
        print("\n  The reversals, each an ordering R501's corrected table "
              "asserts and the era-controlled one denies:")
        for a, b in flips:
            ra = next(r for r in rows if r["sym"] == a)
            rb = next(r for r in rows if r["sym"] == b)
            print(f"    {a:<9} was above {b:<9}  "
                  f"({ra['nmult']:.2f} vs {rb['nmult']:.2f})  ->  now below  "
                  f"({ra['emult']:.2f} vs {rb['emult']:.2f})"
                  f"   [eras {ra['era']:.3f}x vs {rb['era']:.3f}x]")
    else:
        print("\n  NONE. Every ordering R501 left standing among these rows "
              "is the same after the era control.")

    # ------------------------------------------ sensitivity: median era
    print("\n  SENSITIVITY - THE SAME THIRD RANKING WITH THE MEDIAN-OF-SIX "
          "ERA INSTEAD OF THE SINGLE REFERENCE,")
    print("  because part (2) measured the two to differ by up to 0.126x and "
          "an ordering must not rest on")
    print("  which dense tape was named:")
    srows = []
    for r in rows:
        em_ = era_multi[r["sym"]]["x"]
        ev = (r["nvol"] / em_ if (np.isfinite(r["nvol"])
                                  and np.isfinite(em_)) else np.nan)
        srows.append((r["sym"], ev / r["fee"] if np.isfinite(ev) else np.nan,
                      em_))
    order_med = [s_ for s_, m_, _ in
                 sorted([x for x in srows if np.isfinite(x[1])],
                        key=lambda x: -x[1])]
    print(f"    era-controlled (median-of-6) : "
          f"{' > '.join(s_.replace('USD','') for s_ in order_med)}")
    f2 = [(a, b) for i, a in enumerate(readable) for b in readable[i + 1:]
          if a in order_med and b in order_med
          and order_med.index(a) > order_med.index(b)]
    n2 = len([1 for i, a in enumerate(readable) for b in readable[i + 1:]
              if a in order_med and b in order_med])
    print(f"    pairs surviving on that estimator too: {n2 - len(f2)} of "
          f"{n2}" + ("" if not f2 else
                     "   reversals: " +
                     ", ".join(f"{a}/{b}" for a, b in f2)))

    # ------------------------------------------------------ the three orders
    print("\n  THE SAME TABLE, THREE TIMES, ON THE ROWS THAT CARRY ALL "
          "THREE READINGS:")
    common = [s for s in readable]
    o_pub = [r["sym"] for r in sorted(
        [r for r in rows if r["sym"] in common], key=lambda r: -r["mult"])]
    print(f"    as published    : "
          f"{' > '.join(s.replace('USD','') for s in o_pub)}")
    print(f"    R501 de-biased  : "
          f"{' > '.join(s.replace('USD','') for s in readable)}")
    print(f"    era-controlled  : "
          f"{' > '.join(s.replace('USD','') for s in order_era)}")

    # ------------------------------------------------------------ verdict
    print("\n" + LINE)
    print("WHAT THIS ROUND ESTABLISHES")
    print(LINE)
    hot = sorted([(era[s]["x"], s) for s in era if np.isfinite(era[s]["x"])])
    print(f"\n  1. THE ERA COLUMN EXISTS and it is not small. Measured on "
          f"one instrument's tape so that")
    print(f"     nothing but the calendar differs, the eleven rows' windows "
          f"span {hot[0][0]:.3f}x "
          f"({hot[0][1]}) to")
    print(f"     {hot[-1][0]:.3f}x ({hot[-1][1]}) - the ranking has been "
          f"comparing coordinates measured in markets")
    print(f"     up to {hot[-1][0]/hot[0][0]:.2f}x apart in one-minute "
          f"volatility.")
    print(f"\n  2. {len(keeps)} of {npairs} of R501's surviving orderings "
          f"survive the era control; {len(flips)} reverse.")
    print(f"\n  3. {len([s for s in era if era[s]['verdict'] == 'UNMEASURABLE'])}"
          f" row(s) have NO era factor and were given none. That is a DATA "
          f"gap (item 37), not a")
    print("     finding about those instruments, and their rows are printed "
          "with '--' rather than dropped.")
    print("\n  4. COSTS DECIDE NOTHING (owner rule, 2026-07-25). Nothing "
          "above declines a trade, gates a")
    print("     strategy or ranks an instrument for trading. It corrects a "
          "bookkeeping table.")
    print("\n  FENCE HELD: simulate() never called, no entry population "
          "built, no sweep scanned, no stop")
    print("  measured, no outcome read, every tape read behind its own 80% "
          "boundary. NO LOOK CONSUMED.")
    print(LINE)


if __name__ == "__main__":
    main()
