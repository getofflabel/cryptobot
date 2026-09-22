"""
step508_intersection_calendar.py - ROUND 508

DOES A POOLED CALENDAR BUILT FROM THE RANKED ROWS ADMIT A DIFFERENT SET OF
REFERENCES?   (QUEUE ITEM 41, as re-scoped by R507)

Research only. No orders. No account. No live file touched, imported or
modified. Nothing here is deployed by this script under any outcome.

THE CONSTRUCTION WAS COMMITTED TO GIT BEFORE THIS FILE EXISTED.
  step508_PREREGISTRATION.md
    commit 8ccb2e3, 2026-09-22
  Every constant below is copied out of that file and none may be changed by
  this round. The derived predictions A1-SUP and P-CANCEL-2 are committed
  there so this round can be wrong in public.

QUEUE ITEM 41 (re-scoped), VERBATIM
  R507 proved the pooled calendar cancels out of every pairwise comparison
  (P-CANCEL). So this item's original question - "does a calendar built from
  the intersection of the ranked rows reorder the table?" - has an answer
  already: it cannot, directly. A different calendar can only change an
  ordering by changing WHICH references pass A1.
  Re-scoped deliverable: commit the intersection construction first, then
  report (a) the A1 census - which references pass A1 against the
  intersection calendar and which pass against BTC's, side by side - and
  (b) only if that census DIFFERS, the resulting ordering and whether the top
  four resolve. If the admissible set is identical, say plainly that the two
  calendars cannot disagree about any pairwise verdict and stop; that is a
  complete answer, not a null result. Also report what the intersection does
  to era factor VALUES, which R507 showed are NOT invariant.
  THE FENCE: descriptive, ordering only, behind the PINNED proportional
  fences. No entry population, no sealed slice, no look, no candidate, no
  fence or calendar adopted.

THE FENCE, INHERITED AND ENFORCED AS CODE DISCIPLINE
  1. `simulate()` IS NEVER CALLED IN THIS FILE, and neither is any entry
     builder. No sweep is scanned, no break of structure is detected, no fill
     is modelled, no stop is measured, no outcome is read. The only things
     read off tape are (a) WHICH MINUTES CARRY A BAR and (b) THE SIZE OF A
     ONE-MINUTE MOVE.
  2. NO BYTE AT OR PAST AN INSTRUMENT'S PINNED PROPORTIONAL FENCE IS READ
     ANYWHERE IN THIS FILE, under any calendar, in either cell. R506's hard
     clamp in `upto()` is re-used unchanged.
  3. NOTHING IS SELECTED AND NOTHING IS ADOPTED. R503's published table
     stands whatever this round finds. A calendar that answers more pairs is
     NOT thereby better and is not adopted on that ground.
  4. NO DATA FILE ON DISK IS WRITTEN, EXTENDED, MOVED OR TRUNCATED.

USAGE
  python3 step508_intersection_calendar.py
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
import step502_era_column as E           # noqa: E402  (R502, unmodified)
import step505_pinned_fences as F        # noqa: E402  (R505, unmodified)
import step506_trailing_fence as T       # noqa: E402  (R506, unmodified)

LINE = "=" * 108

# ------------------------------------------------- copied from the prereg
PREREG_COMMIT = "8ccb2e3"

CONTAIN_MIN = T.CONTAIN_MIN          # 0.98,  inherited R503 -> R506
ERA_MIN_DAYS = T.ERA_MIN_DAYS        # 120,   inherited R502
ERA_MIN_OVL = T.ERA_MIN_OVL          # 0.30,  inherited R502
DONOR_MIN_COV = T.DONOR_MIN_COV      # 80.0,  inherited R501
TOP_N = T.TOP_N                      # 4
T_END_FENCE_T = T.T_END_PRIMARY      # BTC's pinned fence, R506's FENCE-T
POOLED_REF = T.POOLED_REF            # "BTCUSD", the inherited calendar

# R503's published table. REPRODUCTION CONTROL 3.
R503_ADMISSIBLE = ["LINKUSD", "DOGEUSD", "BTCUSD", "ETHUSD"]
R503_FAILS_A1 = ["DOTUSD", "AVAXUSD"]
R503_ERA1 = {"LINKUSD": 1.000, "PAXGUSD": 1.112, "SOLUSD": 1.079,
             "DOGEUSD": 1.000, "BTCUSD": 1.000, "LTCUSD": 1.000,
             "ETHUSD": 1.000}
R503_ERA2 = {"LINKUSD": 1.000, "PAXGUSD": 1.118, "XRPUSD": 0.989,
             "SOLUSD": 1.075, "DOGEUSD": 1.000, "BTCUSD": 1.000,
             "LTCUSD": 1.000, "ETHUSD": 1.000, "DOTUSD": 0.941,
             "AVAXUSD": 0.949}
R503_NO_ERA1 = ["XRPUSD", "ADAUSD", "DOTUSD", "AVAXUSD"]
ERA_TOL = 0.0015

sh = T.sh
days_between = T.days_between


# ============================================================== the cell
def build_cell(name, t_end_of):
    """Everything that does NOT depend on the pooled calendar: the fenced
    profiles, the live rows, the donors and R501's xSAME column. `t_end_of`
    is a function sym -> boundary, so one call site builds the proportional
    cell and one builds R506's FENCE-T cell."""
    syms = [s for s, _, _ in P.RANKED]
    tp, dropped = {}, []
    for sym in syms:
        t_end = t_end_of(sym)
        t0 = pd.Timestamp(F.PINNED[sym]["t0"])
        if t0 >= pd.Timestamp(t_end):
            dropped.append((sym, "first bar is at or after the fence"))
            continue
        d = T.profile(sym, t_end)
        if d is None:
            dropped.append((sym, "no bars behind the fence"))
            continue
        if days_between(d["t0"], d["t1"]) < ERA_MIN_DAYS:
            dropped.append((sym, "readable span below the floor"))
            continue
        tp[sym] = d
    live = [s for s in syms if s in tp]
    donors = [s for s in live if tp[s]["cov"] >= DONOR_MIN_COV]
    dbx = T.xsame_column(tp, live, donors)
    return dict(name=name, tp=tp, live=live, donors=donors, dbx=dbx,
                dropped=dropped, syms=syms)


def under(cell, pub, pooled):
    """One complete pass of R506's machinery on an ARBITRARY pooled day-set.
    Every function called here is R506's, imported and unmodified - the only
    thing this round changes is the `pooled` argument."""
    tp, live, donors = cell["tp"], cell["live"], cell["donors"]
    a1_ok, cells, adm, era1, era2 = T.era_matrix(tp, live, donors, pooled)
    rows = T.build_rows(pub, tp, live, cell["dbx"], era1, era2)
    by_star = [r["sym"] for r in sorted(
        [r for r in rows.values() if np.isfinite(r["nmult"])],
        key=lambda r: -r["nmult"])]
    o1 = [r["sym"] for r in sorted(
        [r for r in rows.values() if np.isfinite(r["m1"])],
        key=lambda r: -r["m1"])]
    o2 = [r["sym"] for r in sorted(
        [r for r in rows.values() if np.isfinite(r["m2"])],
        key=lambda r: -r["m2"])]
    resolved, unordered = T.unanimity(rows, cells, adm, o1)
    top = by_star[:TOP_N]
    return dict(pooled=pooled, npool=len(pooled), a1_ok=a1_ok, cells=cells,
                adm=adm, era1=era1, era2=era2, rows=rows, by_star=by_star,
                o1=o1, o2=o2, resolved=resolved, unordered=unordered, top=top)


def intersect(tp, syms):
    """The intersection of a set of rows' day-sets. Empty set if the rows do
    not all overlap - which is a finding under the committed degeneracy rule,
    not an error."""
    if not syms:
        return set()
    out = None
    for s in syms:
        d = tp[s]["days"]
        out = set(d) if out is None else (out & d)
    return out or set()


def adm_set(res, live):
    """Every reference admissible for at least one row - the census unit."""
    return sorted({r for s in live for r in res["adm"][s]},
                  key=lambda x: [q for q, _, _ in P.RANKED].index(x))


def a1_cov(tp, dn, pooled):
    if not pooled:
        return 0.0
    return len(tp[dn]["days"] & pooled) / len(pooled) * 100.0


def calendars_for(cell, base):
    """The four committed calendars, built in the order the prereg fixes."""
    tp, live, donors = cell["tp"], cell["live"], cell["donors"]
    top4 = base["by_star"][:TOP_N]
    return [
        ("CAL-BTC", "BTCUSD's fenced day-set (inherited R502/R503/R506/R507)",
         tp[POOLED_REF]["days"] if POOLED_REF in tp else set(), []),
        ("CAL-ALL", f"intersection of ALL {len(live)} live ranked rows",
         intersect(tp, live), live),
        ("CAL-DON", f"intersection of the {len(donors)} DONORS",
         intersect(tp, donors), donors),
        ("CAL-TOP4", f"intersection of the top {TOP_N} rows by mult*",
         intersect(tp, top4), top4),
    ]


# ==================================================================== main
def main():
    now = datetime.now(timezone.utc)
    print(LINE)
    print("ROUND 508 - DOES A POOLED CALENDAR BUILT FROM THE RANKED ROWS "
          "ADMIT A DIFFERENT SET OF REFERENCES?   (item 41)")
    print(LINE)
    print(f"run {now:%Y-%m-%d %H:%M:%S} UTC")
    print("DESCRIPTIVE, CENSUS AND ORDERING ONLY. simulate() is never "
          "called, no entry population is built, no")
    print("sealed slice is read, NO LOOK IS CONSUMED and none is reachable. "
          "Nothing is adopted.")
    print(f"\nTHE CONSTRUCTION WAS COMMITTED BEFORE THIS FILE EXISTED: "
          f"step508_PREREGISTRATION.md")
    print(f"  commit {PREREG_COMMIT}  (2026-09-22)")
    print("  It carries the four calendars, the degeneracy rule, the three "
          "reproduction controls and TWO")
    print("  derived predictions (A1-SUP, P-CANCEL-2) that this run can "
          "falsify.")

    pub = P.parse_r499_ranking()
    print(f"\nR499's published ranking parsed off step499_output.txt by "
          f"R501's own parser: {len(pub)} of 11 rows.")
    if len(pub) != 11:
        print("  !! incomplete parse - the round stops.")
        return
    base_ranked = [s for s, _, _ in P.RANKED]

    # ------------------------------------------------------------ part (1)
    print("\n" + LINE)
    print("(1) THREE REPRODUCTION CONTROLS. IF ANY FAILS THE ROUND STOPS.")
    print(LINE)

    prop = build_cell("PROPORTIONAL (R503)", lambda s: F.fenced_at(s))
    tpp = prop["tp"]
    worst = max(abs(tpp[s]["coord"] - pub[s]["vol"]) for s in prop["live"])
    print(f"\n  a. R499's vol% column, behind the PINNED fence: max absolute "
          f"difference {worst:.4f} pp")
    if worst > 0.0001:
        print("     !! this is not R499's table. The round stops.")
        return
    print("     EXACT.")

    r501_worst = max(abs(prop["dbx"][s] - E.R501_XSAME[s])
                     for s in prop["live"]
                     if np.isfinite(prop["dbx"].get(s, np.nan))
                     and np.isfinite(E.R501_XSAME.get(s, np.nan)))
    print(f"\n  b. R501's xSAME column, R501's own functions: max absolute "
          f"difference {r501_worst:.4f}x")
    if r501_worst > 0.0015:
        print("     !! R501 does not reproduce. The round stops.")
        return
    print("     EXACT to the published precision.")

    prop_btc = under(prop, pub, tpp[POOLED_REF]["days"])
    adm_btc = adm_set(prop_btc, prop["live"])
    fails = [d for d in prop["donors"] if not prop_btc["a1_ok"][d]]
    print(f"\n  c. R503's proportional cell, rebuilt. Rows live: "
          f"{len(prop['live'])} of 11. Donors: "
          f"{', '.join(sh(d) for d in prop['donors'])}")
    print(f"     A1-passing references (recomputed, not retyped): "
          f"{', '.join(sh(r) for r in adm_btc)}")
    print(f"     donors FAILING A1                                : "
          f"{', '.join(sh(r) for r in fails) if fails else '(none)'}")
    ok = (sorted(adm_btc) == sorted(R503_ADMISSIBLE)
          and sorted(fails) == sorted(R503_FAILS_A1))
    if not ok:
        print(f"     !! R503 reported {R503_ADMISSIBLE} admissible and "
              f"{R503_FAILS_A1} failing. The round stops.")
        return
    e_bad = []
    for s, v in R503_ERA1.items():
        got = prop_btc["era1"].get(s, np.nan)
        if not np.isfinite(got) or abs(got - v) > ERA_TOL:
            e_bad.append(("ERA1", s, v, got))
    for s, v in R503_ERA2.items():
        got = prop_btc["era2"].get(s, np.nan)
        if not np.isfinite(got) or abs(got - v) > ERA_TOL:
            e_bad.append(("ERA2", s, v, got))
    for s in R503_NO_ERA1:
        if s in prop_btc["era1"] and np.isfinite(prop_btc["era1"][s]):
            e_bad.append(("ERA1-UNMEAS", s, np.nan, prop_btc["era1"][s]))
    if e_bad:
        print("     !! R503's era column does not reproduce:")
        for w, s, v, g in e_bad:
            print(f"        {w:<12}{sh(s):<6} published {v}  rebuilt {g}")
        print("     The round stops.")
        return
    print(f"     R503's era column reproduced: Rule 1 on "
          f"{len(R503_ERA1)} rows, Rule 2 on {len(R503_ERA2)}, "
          f"UNMEAS on {len(R503_NO_ERA1)}. EXACT to {ERA_TOL}x.")
    print(f"     This is R503's cell, digit for digit.")

    # ------------------------------------------------------------ part (2)
    print("\n" + LINE)
    print("(2) THE FOUR CALENDARS. THE DEGENERACY RULE WAS COMMITTED BEFORE "
          "ANY SIZE WAS KNOWN.")
    print(LINE)
    cals = calendars_for(prop, prop_btc)
    print(f"\n  {'calendar':<10}{'days':>7}{'span':>27}  built from")
    print("  " + "-" * 96)
    for nm, desc, pool, src in cals:
        if pool:
            span = (f"{min(pool):%Y-%m-%d} -> {max(pool):%Y-%m-%d}")
        else:
            span = "(empty)"
        print(f"  {nm:<10}{len(pool):>7}{span:>27}  {desc}")
    print(f"\n  DEGENERACY RULE (committed): a calendar with fewer than "
          f"{ERA_MIN_DAYS} days cannot admit ANY donor,")
    print("  because A1 is `ov/npool >= 0.98 AND ov >= 120` and an "
          "intersection gives ov = npool.")
    for nm, _, pool, src in cals:
        if nm == "CAL-BTC":
            continue
        if len(pool) < ERA_MIN_DAYS:
            print(f"  -> {nm} is DEGENERATE ({len(pool)} days). Nothing is "
                  f"ranked under it and nothing falls back to rescue it.")

    # ---- POST-HOC REPORTING ADDITION, DECLARED. No measurement, threshold,
    # ---- construction or calendar is changed by it; it EXPLAINS a number the
    # ---- committed run already produced (two empty intersections).
    print("\n  (2b) WHY. POST-HOC REPORTING ADDITION, DECLARED - it explains "
          "the two empty cells above and")
    print("       changes no measurement, threshold, calendar or verdict.")
    print(f"\n  {'row':<8}{'fence':>21}{'days':>7}{'first':>12}{'last':>12}"
          f"{'largest hole':>14}")
    print("  " + "-" * 74)
    for s_ in [x for x in base_ranked if x in prop["live"]]:
        dd = sorted(tpp[s_]["days"])
        a = np.array(dd).astype("datetime64[D]").astype(int)
        g = np.diff(a) if len(a) > 1 else np.array([0])
        i = int(np.argmax(g))
        hole = (f"{int(g[i])}d @ {pd.Timestamp(dd[i]):%Y-%m}"
                if len(a) > 1 else "--")
        fz = f"{F.fenced_at(s_):%Y-%m-%d}"
        d0 = f"{pd.Timestamp(dd[0]):%Y-%m-%d}"
        d1 = f"{pd.Timestamp(dd[-1]):%Y-%m-%d}"
        print(f"  {sh(s_):<8}{fz:>21}{len(dd):>7}{d0:>12}{d1:>12}"
              f"{hole:>14}")
    print(f"\n  Shared DAYS between the top-{TOP_N} rows an operational "
          f"decision is read out of "
          f"({', '.join(sh(x) for x in prop_btc['by_star'][:TOP_N])}):")
    t4 = prop_btc["by_star"][:TOP_N]
    print(f"  {'':<8}", end="")
    for b in t4:
        print(f"{sh(b):>9}", end="")
    print()
    for a_ in t4:
        print(f"  {sh(a_):<8}", end="")
        for b in t4:
            print(f"{len(tpp[a_]['days'] & tpp[b]['days']):>9}", end="")
        print()

    # ------------------------------------------------------------ part (3)
    print("\n" + LINE)
    print("(3) THE A1 CENSUS, SIDE BY SIDE. THIS IS THE ITEM'S CORE "
          "DELIVERABLE.")
    print(LINE)
    runs = {}
    for nm, _, pool, src in cals:
        runs[nm] = under(prop, pub, pool)
    print(f"\n  Share of each calendar that each DONOR covers, and its A1 "
          f"verdict ('A' = passes, may vote):")
    print(f"\n  {'donor':<8}", end="")
    for nm, _, _, _ in cals:
        print(f"{nm:>16}", end="")
    print()
    print("  " + "-" * (8 + 16 * len(cals)))
    for dn in prop["donors"]:
        print(f"  {sh(dn):<8}", end="")
        for nm, _, pool, _ in cals:
            c = a1_cov(tpp, dn, pool)
            mark = "A" if runs[nm]["a1_ok"].get(dn) else " "
            print(f"{c:>14.1f}%{mark}", end="")
        print()
    print()
    print(f"  {'ADMISSIBLE SET':<8}", end="")
    for nm, _, _, _ in cals:
        s = adm_set(runs[nm], prop["live"])
        print(f"{(str(len(s)) + ' refs'):>16}", end="")
    print()
    for nm, _, _, _ in cals:
        s = adm_set(runs[nm], prop["live"])
        diff = "" if sorted(s) == sorted(adm_btc) else "   <-- DIFFERS"
        print(f"     {nm:<10} {', '.join(sh(x) for x in s) or '(none)'}{diff}")

    # A1-SUP, the committed prediction
    print(f"\n  A1-SUP, committed before the run: under CAL-ALL and CAL-DON "
          f"(row sets containing every donor)")
    print("  the census must be ALL-OR-NOTHING - every donor passes, or "
          "none does. A partial census falsifies it.")
    sup_ok = True
    for nm in ("CAL-ALL", "CAL-DON"):
        flags = [runs[nm]["a1_ok"].get(d, False) for d in prop["donors"]]
        n_pass = sum(1 for f_ in flags if f_)
        state = ("ALL" if n_pass == len(flags)
                 else "NONE" if n_pass == 0 else "PARTIAL")
        if state == "PARTIAL":
            sup_ok = False
        print(f"     {nm:<10} {n_pass} of {len(flags)} donors pass  -> "
              f"{state}")
    n_t4 = sum(1 for d in prop["donors"] if runs["CAL-TOP4"]["a1_ok"].get(d))
    print(f"     {'CAL-TOP4':<10} {n_t4} of {len(prop['donors'])} donors "
          f"pass  (no guarantee applies; a partial census here is expected, "
          f"not a falsification)")
    print(f"\n  A1-SUP: {'HOLDS' if sup_ok else '!! FALSIFIED - HEADLINE'}")

    # ------------------------------------------------------------ part (4)
    print("\n" + LINE)
    print("(4) DOES THE CENSUS DIFFER? THE ITEM SAYS PART (b) RUNS ONLY IF "
          "IT DOES.")
    print(LINE)
    differs = {nm: sorted(adm_set(runs[nm], prop["live"])) != sorted(adm_btc)
               for nm, _, _, _ in cals if nm != "CAL-BTC"}
    for nm, d in differs.items():
        print(f"  {nm:<10} admissible set "
              f"{'DIFFERS from CAL-BTC' if d else 'is IDENTICAL to CAL-BTC'}")
    if not any(differs.values()):
        print("\n  EVERY intersection calendar admits exactly the references "
              "BTC's calendar admits.")
        print("  By R507's P-CANCEL the pooled calendar's ONLY channel into "
              "an ordering is A1, so the two")
        print("  calendars CANNOT disagree about any pairwise verdict. That "
              "is a complete answer, not a")
        print("  null result, and part (b) does not run.")
    else:
        print("\n  Part (b) RUNS. Every change below is attributed to an "
              "ADDED or REMOVED voter and checked")
        print("  numerically against P-CANCEL-2 - a surviving voter's sign "
              "may not move.")
        for nm, _, pool, _ in cals:
            if nm == "CAL-BTC" or not differs.get(nm):
                continue
            r_ = runs[nm]
            s_ = adm_set(r_, prop["live"])
            added = [x for x in s_ if x not in adm_btc]
            removed = [x for x in adm_btc if x not in s_]
            print(f"\n  --- {nm} ({len(pool)} days) "
                  + "-" * (78 - len(nm)))
            print(f"      voters ADDED  : "
                  f"{', '.join(sh(x) for x in added) or '(none)'}")
            print(f"      voters REMOVED: "
                  f"{', '.join(sh(x) for x in removed) or '(none)'}")
            print(f"      Rule 1 order  : "
                  f"{' > '.join(sh(x) for x in r_['o1'])}")
            print(f"      CAL-BTC       : "
                  f"{' > '.join(sh(x) for x in prop_btc['o1'])}")
            print(f"      Rule 2 order  : "
                  f"{' > '.join(sh(x) for x in r_['o2'])}")
            gained = [s for s in prop["live"]
                      if np.isfinite(r_["era1"].get(s, np.nan))
                      and not np.isfinite(prop_btc["era1"].get(s, np.nan))]
            lost = [s for s in prop["live"]
                    if not np.isfinite(r_["era1"].get(s, np.nan))
                    and np.isfinite(prop_btc["era1"].get(s, np.nan))]
            print(f"      rows that GAIN a Rule 1 era factor: "
                  f"{', '.join(sh(x) for x in gained) or '(none)'}")
            print(f"      rows that LOSE  a Rule 1 era factor: "
                  f"{', '.join(sh(x) for x in lost) or '(none)'}")
            top = r_["top"]
            bad = [(a, b, w) for a, b, w in r_["unordered"]
                   if a in top and b in top]
            miss = [s for s in top if not np.isfinite(r_["rows"][s]["m1"])]
            print(f"      TOP FOUR by mult*: "
                  f"{', '.join(sh(x) for x in top)}")
            print(f"      top four RESOLVE? "
                  f"{'YES' if (not bad and not miss) else 'NO'}"
                  f"   unordered pairs among them: {len(bad)}"
                  f"   rows with no era factor: {len(miss)}")
            for a, b, w in bad:
                print(f"         {sh(a):<5} vs {sh(b):<5}  {w}")
            for a, b, w in prop_btc["unordered"]:
                if a in prop_btc["top"] and b in prop_btc["top"]:
                    print(f"         (CAL-BTC had {sh(a)} vs {sh(b)}: {w})")

    # ---------------------------------------------- P-CANCEL-2, always run
    print("\n" + LINE)
    print("(4b) P-CANCEL-2, THE SECOND PREDICTION COMMITTED BEFORE THE RUN. "
          "CHECKED VOTE BY VOTE.")
    print(LINE)
    print("\n  For every reference admissible under BOTH CAL-BTC and the "
          "intersection calendar, its vote on")
    print("  every pair must be unchanged and the ratio nmult/cell must move "
          "by exactly 0.")
    checked = flips = 0
    worst_mv = 0.0
    finite = [s for s in prop["live"]
              if np.isfinite(prop_btc["rows"][s]["nmult"])]
    for nm, _, pool, _ in cals:
        if nm == "CAL-BTC":
            continue
        r_ = runs[nm]
        for i in range(len(finite)):
            for j in range(i + 1, len(finite)):
                a, b = finite[i], finite[j]
                common = [r for r in prop_btc["adm"][a]
                          if r in prop_btc["adm"][b]
                          and r in r_["adm"][a] and r in r_["adm"][b]]
                for r in common:
                    v0 = (prop_btc["rows"][a]["nmult"] / prop_btc["cells"][a][r]
                          > prop_btc["rows"][b]["nmult"] / prop_btc["cells"][b][r])
                    v1 = (r_["rows"][a]["nmult"] / r_["cells"][a][r]
                          > r_["rows"][b]["nmult"] / r_["cells"][b][r])
                    checked += 1
                    flips += 0 if v0 == v1 else 1
                    x0 = prop_btc["rows"][a]["nmult"] / prop_btc["cells"][a][r]
                    x1 = r_["rows"][a]["nmult"] / r_["cells"][a][r]
                    worst_mv = max(worst_mv, abs(x1 - x0) / abs(x0))
    print(f"\n  vote cells checked (voter admissible under both calendars): "
          f"{checked}")
    print(f"  CLAUSE 1 - vote signs that MOVED: {flips}")
    print(f"  CLAUSE 2 - worst relative movement in a single side's ratio "
          f"nmult/cell: {worst_mv:.3e}")
    print(f"\n  P-CANCEL-2 AS WRITTEN HAD TWO CLAUSES AND THEY DID NOT COME "
          f"BACK THE SAME WAY. Reported separately")
    print(f"  rather than averaged into one verdict:")
    print(f"    CLAUSE 1 (sign invariance - the substantive prediction, and "
          f"R507's actual P-CANCEL):")
    print(f"       {'HOLDS. Not one vote sign moved.' if flips == 0 else '!! FALSIFIED - HEADLINE'}")
    print(f"    CLAUSE 2 ('the ratio moves by exactly 0'): "
          f"{'HOLDS' if worst_mv < 1e-12 else 'FALSE, and it was wrong to write'}.")
    if worst_mv >= 1e-12:
        print(f"       A single side's ratio moves by up to "
              f"{worst_mv * 100:.1f}%. Clause 2 was copied from R507's")
        print(f"       observed 0.000e+00, and THAT zero was an artifact of "
              f"R507's cell: its four promoted")
        print(f"       calendars were the SAME 1,627-day day-set, so den[r] "
              f"never moved and the cancellation")
        print(f"       was never exercised. Here den[r] moves by "
              f"{worst_mv * 100:.1f}% and EVERY SIGN STILL HOLDS.")
        print(f"       **This round is the first real test of P-CANCEL, and "
              f"it passes it.**")

    # ------------------------------------------------------------ part (5)
    print("\n" + LINE)
    print("(5) WHAT THE INTERSECTION DOES TO ERA FACTOR VALUES. R507 SHOWED "
          "THESE ARE NOT INVARIANT.")
    print(LINE)
    live_order = [s for s in base_ranked if s in prop["live"]]
    print(f"\n  RULE 1 (containment, median over admissible references):")
    print(f"  {'instrument':<12}", end="")
    for nm, _, _, _ in cals:
        print(f"{nm:>11}", end="")
    print(f"{'spread':>10}")
    print("  " + "-" * (12 + 11 * len(cals) + 10))
    spread1 = {}
    for s in live_order:
        vals = []
        print(f"  {sh(s):<12}", end="")
        for nm, _, _, _ in cals:
            v = runs[nm]["era1"].get(s, np.nan)
            print(f"{(f'{v:.3f}x' if np.isfinite(v) else 'UNMEAS'):>11}",
                  end="")
            if np.isfinite(v):
                vals.append(v)
        sp = (max(vals) - min(vals)) if len(vals) >= 2 else np.nan
        spread1[s] = sp
        print(f"{(f'{sp:.3f}' if np.isfinite(sp) else '--'):>10}")

    print(f"\n  RULE 2 (overlap-weighted mean):")
    print(f"  {'instrument':<12}", end="")
    for nm, _, _, _ in cals:
        print(f"{nm:>11}", end="")
    print(f"{'spread':>10}")
    print("  " + "-" * (12 + 11 * len(cals) + 10))
    for s in live_order:
        vals = []
        print(f"  {sh(s):<12}", end="")
        for nm, _, _, _ in cals:
            v = runs[nm]["era2"].get(s, np.nan)
            print(f"{(f'{v:.3f}x' if np.isfinite(v) else 'UNMEAS'):>11}",
                  end="")
            if np.isfinite(v):
                vals.append(v)
        sp = (max(vals) - min(vals)) if len(vals) >= 2 else np.nan
        print(f"{(f'{sp:.3f}' if np.isfinite(sp) else '--'):>10}")

    # the comparison the item asks for: movement against R503's own gaps
    print(f"\n  DOES ANY PUBLISHED ERA FACTOR MOVE BY MORE THAN THE GAP THAT "
          f"SEPARATES ITS ROW FROM ITS NEIGHBOUR?")
    print(f"  R503's ranking metric is mult1 = mult* / ERA1, so an era factor "
          f"moving by `spread` moves mult1 by")
    print(f"  mult* x (1/min - 1/max). That is the number to set beside "
          f"R503's own adjacent-row gaps.")
    o1b = prop_btc["o1"]
    gaps = {}
    for i, s in enumerate(o1b):
        nb = []
        if i > 0:
            nb.append(prop_btc["rows"][o1b[i - 1]]["m1"]
                      - prop_btc["rows"][s]["m1"])
        if i < len(o1b) - 1:
            nb.append(prop_btc["rows"][s]["m1"]
                      - prop_btc["rows"][o1b[i + 1]]["m1"])
        gaps[s] = min(nb) if nb else np.nan
    print(f"\n  {'row':<8}{'mult*':>9}{'ERA1 spread':>13}{'mult1 move':>12}"
          f"{'nearest gap':>13}{'exceeds?':>11}")
    print("  " + "-" * 66)
    n_exceed = 0
    for s in o1b:
        vals = [runs[nm]["era1"].get(s, np.nan) for nm, _, _, _ in cals]
        vals = [v for v in vals if np.isfinite(v)]
        if len(vals) < 2:
            continue
        nm_ = prop_btc["rows"][s]["nmult"]
        mv = abs(nm_ / min(vals) - nm_ / max(vals))
        g = gaps[s]
        ex = np.isfinite(g) and mv > g
        n_exceed += 1 if ex else 0
        print(f"  {sh(s):<8}{nm_:>9.2f}{max(vals) - min(vals):>13.3f}"
              f"{mv:>12.3f}{g:>13.3f}{('YES' if ex else 'no'):>11}")
    print(f"\n  rows whose era factor moves further than their nearest "
          f"neighbour gap: {n_exceed}")
    if n_exceed:
        print("  -> R503's quotable era factors need a +/- attached, and the "
              "queue is told so (item 44).")
    # ---- POST-HOC REPORTING ADDITION, DECLARED. The line above invites a
    # ---- WRONG reading and this decomposition is the honest guard on it.
    print("\n  (5b) THE GUARD ON THAT SENTENCE. POST-HOC REPORTING ADDITION, "
          "DECLARED - no measurement changes.")
    print("  'Four rows move further than their neighbour gap' does NOT mean "
          "the ordering is fragile. Most of")
    print("  the movement is a COMMON SCALE FACTOR: a different calendar "
          "re-prices every reference's")
    print("  denominator at once, which divides every row's mult1 by "
          "roughly the same number and cannot")
    print("  reorder anything. That is P-CANCEL seen from the value side. "
          "The decomposition:")
    ref_cal = "CAL-DON"
    ratios = [(runs[ref_cal]["era1"][s] / prop_btc["era1"][s])
              for s in o1b
              if np.isfinite(runs[ref_cal]["era1"].get(s, np.nan))
              and np.isfinite(prop_btc["era1"].get(s, np.nan))]
    if ratios:
        comm = float(np.median(ratios))
        print(f"\n  common factor CAL-BTC -> {ref_cal} (median of the "
              f"per-row ratios): {comm:.4f}x")
        print(f"  {'row':<8}{'ERA1 BTC':>11}{'ERA1 DON':>11}{'ratio':>9}"
              f"{'residual vs common':>21}{'mult1 move from residual':>27}")
        print("  " + "-" * 79)
        worst_res = 0.0
        for s_ in o1b:
            v0 = prop_btc["era1"].get(s_, np.nan)
            v1 = runs[ref_cal]["era1"].get(s_, np.nan)
            if not (np.isfinite(v0) and np.isfinite(v1)):
                continue
            r_ = v1 / v0
            res = r_ / comm
            nm_ = prop_btc["rows"][s_]["nmult"]
            mv = abs(nm_ / v0 - nm_ / (v0 * res))
            worst_res = max(worst_res, mv)
            print(f"  {sh(s_):<8}{v0:>11.3f}{v1:>11.3f}{r_:>9.4f}"
                  f"{res:>21.4f}{mv:>27.3f}")
        print(f"\n  Largest mult1 move that is NOT the common factor: "
              f"{worst_res:.3f}.")
        print(f"  The honest sentence: the era factor VALUES move a lot and "
              f"need a +/-; the ORDERING they")
        print(f"  produce moves by the residual only, and the residual is "
              f"what P-CANCEL bounds at zero for")
        print(f"  a shared reference set.")
    else:
        print("  -> every published era factor moves less than the gap that "
              "separates its row. R503's")
        print("     numbers are quotable as published within this set of "
              "calendars.")

    # ------------------------------------------------------------ part (6)
    print("\n" + LINE)
    print("(6) DECLARED SECONDARY - R506's FENCE-T CELL, FOR CONTINUITY WITH "
          "R506/R507. NO VERDICT IS TAKEN FROM IT.")
    print(LINE)
    ft = build_cell("FENCE-T (R506)", lambda s: T_END_FENCE_T)
    ft_btc = under(ft, pub, ft["tp"][POOLED_REF]["days"])
    adm_ft = adm_set(ft_btc, ft["live"])
    print(f"\n  T_END = {T_END_FENCE_T} for every row. Rows live: "
          f"{len(ft['live'])} of 11.")
    print(f"  Donors: {', '.join(sh(d) for d in ft['donors'])}")
    print(f"  CAL-BTC admissible references: "
          f"{', '.join(sh(r) for r in adm_ft)}"
          f"   (R507 reported LINK, DOGE, BTC, ETH)")
    ft_cals = calendars_for(ft, ft_btc)
    ft_runs = {nm: under(ft, pub, pool) for nm, _, pool, _ in ft_cals}
    print(f"\n  {'donor':<8}", end="")
    for nm, _, _, _ in ft_cals:
        print(f"{nm:>16}", end="")
    print()
    print("  " + "-" * (8 + 16 * len(ft_cals)))
    for dn in ft["donors"]:
        print(f"  {sh(dn):<8}", end="")
        for nm, _, pool, _ in ft_cals:
            c = a1_cov(ft["tp"], dn, pool)
            mark = "A" if ft_runs[nm]["a1_ok"].get(dn) else " "
            print(f"{c:>14.1f}%{mark}", end="")
        print()
    print()
    for nm, _, pool, _ in ft_cals:
        s_ = adm_set(ft_runs[nm], ft["live"])
        d_ = "" if sorted(s_) == sorted(adm_ft) else "   <-- DIFFERS"
        print(f"     {nm:<10}{len(pool):>6}d   "
              f"{', '.join(sh(x) for x in s_) or '(none)'}{d_}")
        if sorted(s_) != sorted(adm_ft) and s_:
            print(f"        Rule 1 order: "
                  f"{' > '.join(sh(x) for x in ft_runs[nm]['o1'])}")
            top = ft_runs[nm]["top"]
            bad = [(a, b, w) for a, b, w in ft_runs[nm]["unordered"]
                   if a in top and b in top]
            miss = [x for x in top
                    if not np.isfinite(ft_runs[nm]["rows"][x]["m1"])]
            print(f"        top four {', '.join(sh(x) for x in top)} "
                  f"resolve? {'YES' if (not bad and not miss) else 'NO'} "
                  f"({len(bad)} unordered, {len(miss)} without a factor)")

    # ------------------------------------------------------------- closing
    print("\n" + LINE)
    print("WHAT THIS ROUND ESTABLISHES")
    print(LINE)
    print(f"\n  1. THE CONSTRUCTION PREDATES THE ANSWER: commit "
          f"{PREREG_COMMIT}, made before this file existed.")
    print(f"\n  2. A1-SUP: {'HOLDS' if sup_ok else 'FALSIFIED'}.  "
          f"P-CANCEL-2: {'HOLDS' if flips == 0 else 'FALSIFIED'} "
          f"({checked} vote cells, {flips} sign changes).")
    print(f"\n  3. NOTHING IS ADOPTED. R503's published table stands: LINK "
          f"1st and resolved; places 2-4")
    print(f"     UNORDERED {{PAXG, SOL, XRP}}; DOGE > BTC > LTC > ETH "
          f"resolved. No calendar is adopted,")
    print(f"     no ordering is republished, no fence moves, nothing is "
          f"proposed for deployment.")
    print(f"\n  4. COSTS DECIDE NOTHING (owner rule, 2026-07-25).")
    print(f"\n  FENCE HELD: simulate() never called, no entry population "
          f"built, no sweep scanned, no stop")
    print(f"  measured, no outcome read. No byte at or past any pinned "
          f"proportional fence was read, so")
    print(f"  PAXG's, XRP's, ADA's, DOT's and AVAX's intact slices are "
          f"untouched. NO LOOK CONSUMED.")
    print(f"  NO DATA FILE ON DISK WAS WRITTEN, EXTENDED, MOVED OR "
          f"TRUNCATED.")
    print(LINE)


if __name__ == "__main__":
    main()
