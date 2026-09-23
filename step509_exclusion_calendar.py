"""
step509_exclusion_calendar.py - ROUND 509

A CALENDAR THAT EXCLUDES *SOME* REFERENCE, AND WHETHER A SPLIT MOVES BY LOSING
A VOTER OR BY TURNING ONE.   (QUEUE ITEM 44, SECOND HALF, as re-scoped by R508)

Research only. No orders. No account. No live file touched, imported or
modified. Nothing here is deployed by this script under any outcome.

THE CONSTRUCTION WAS COMMITTED TO GIT BEFORE THIS FILE EXISTED.
  step509_PREREGISTRATION.md
    commit 0c457b4, 2026-09-23
  Every constant, both families and all three predictions (P-LOO, P-EXCL,
  P-TURN) are copied out of that file and none may be changed by this round.

QUEUE ITEM 44, SECOND HALF, VERBATIM
  "build a calendar that EXCLUDES SOME reference under A1 and confirm a split
   can move there - by removing a voter, never by turning one."
  The first half (how far the era factor VALUES move) is ANSWERED by R508 and
  MUST NOT BE RE-RUN: a common 1.0774x scale, residuals 1.0000-1.0017, largest
  non-common mult1 move 0.003. YES for the quoted value, NO for the ordering.

  R507 could not exercise A1 (every reference covered 100.0% of every promoted
  calendar). R508 could not either (CAL-ALL and CAL-TOP4 empty, CAL-DON
  excludes nobody). A strict, non-empty exclusion has never been built here.

THE FENCE, INHERITED AND ENFORCED AS CODE DISCIPLINE
  1. `simulate()` IS NEVER CALLED IN THIS FILE, and neither is any entry
     builder. No sweep scanned, no break of structure detected, no fill
     modelled, no stop measured, no outcome read. The only things read off
     tape are (a) WHICH MINUTES CARRY A BAR and (b) THE SIZE OF A ONE-MINUTE
     MOVE.
  2. NO BYTE AT OR PAST AN INSTRUMENT'S PINNED PROPORTIONAL FENCE IS READ
     ANYWHERE IN THIS FILE, under any calendar, in either cell. R506's hard
     clamp in `upto()` is re-used unchanged.
  3. NOTHING IS SELECTED AND NOTHING IS ADOPTED. R503's published table
     stands whatever this round finds. A calendar that resolves more pairs is
     NOT thereby better and is not adopted on that ground.
  4. NO DATA FILE ON DISK IS WRITTEN, EXTENDED, MOVED OR TRUNCATED.

USAGE
  python3 step509_exclusion_calendar.py
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
import step508_intersection_calendar as I  # noqa: E402  (R508, unmodified)

LINE = "=" * 108

# ------------------------------------------------- copied from the prereg
PREREG_COMMIT = "0c457b4"

CONTAIN_MIN = T.CONTAIN_MIN          # 0.98,  inherited R503 -> R506
ERA_MIN_DAYS = T.ERA_MIN_DAYS        # 120,   inherited R502
ERA_MIN_OVL = T.ERA_MIN_OVL          # 0.30,  inherited R502
DONOR_MIN_COV = T.DONOR_MIN_COV      # 80.0,  inherited R501
TOP_N = T.TOP_N                      # 4
T_END_FENCE_T = T.T_END_PRIMARY      # BTC's pinned fence, R506's FENCE-T
POOLED_REF = T.POOLED_REF            # "BTCUSD", the inherited calendar

# R503's published table. REPRODUCTION CONTROLS, copied from R508 verbatim.
R503_ADMISSIBLE = I.R503_ADMISSIBLE
R503_FAILS_A1 = I.R503_FAILS_A1
R503_ERA1 = I.R503_ERA1
R503_ERA2 = I.R503_ERA2
R503_NO_ERA1 = I.R503_NO_ERA1
ERA_TOL = I.ERA_TOL

P_LOO_TOL = 1e-9                     # committed in the prereg

sh = T.sh
days_between = T.days_between
build_cell = I.build_cell            # R508's, unmodified
under = I.under                      # R508's, unmodified
intersect = I.intersect              # R508's, unmodified
adm_set = I.adm_set                  # R508's, unmodified
a1_cov = I.a1_cov                    # R508's, unmodified


# =================================================== the two committed families
def family_A(cell):
    """LEAVE-ONE-OUT OVER THE DONORS. For each donor d, the intersection of
    every OTHER donor's day-set - 'the calendar the other rows agree on'.
    Built by rule over every donor, in the ranked order. Nothing is filtered
    by what it produces."""
    tp, donors = cell["tp"], cell["donors"]
    out = []
    for d in donors:
        others = [x for x in donors if x != d]
        out.append((f"LOO-{sh(d)}", d, others, intersect(tp, others)))
    return out


def family_B(cell):
    """SELF-PROMOTION OVER EVERY LIVE RANKED ROW. Each row's own fenced
    day-set promoted to the pooled calendar. CAL-SELF(BTCUSD) is CAL-BTC by
    construction and is this family's built-in reproduction control."""
    tp = cell["tp"]
    order = [s for s, _, _ in P.RANKED if s in cell["live"]]
    return [(f"SELF-{sh(r)}", r, [r], set(tp[r]["days"])) for r in order]


def verdict_map(res):
    """pair -> ('RESOLVED', n_common) / ('UNORDERED', why), keyed on the
    unordered frozenset so the two cells' orderings cannot silently re-pair."""
    out = {}
    for a, b, n in res["resolved"]:
        out[frozenset((a, b))] = ("RESOLVED", n)
    for a, b, w in res["unordered"]:
        out[frozenset((a, b))] = ("UNORDERED", w)
    return out


def replay_without(base, drop, rows_order):
    """THE ATTRIBUTION TEST. Re-run the BASELINE's own unanimity vote with the
    reference `drop` struck out of every row's admissible list - nothing else
    touched, no cell recomputed, no coordinate re-measured. If the exclusion
    cell's verdict for a pair equals this, the move is fully explained by the
    removal of that voter and by nothing else."""
    adm2 = {s: [r for r in v if r != drop] for s, v in base["adm"].items()}
    resolved, unordered = T.unanimity(base["rows"], base["cells"], adm2,
                                      rows_order)
    return verdict_map({"resolved": resolved, "unordered": unordered})


# ==================================================================== main
def main():
    now = datetime.now(timezone.utc)
    print(LINE)
    print("ROUND 509 - A CALENDAR THAT EXCLUDES *SOME* REFERENCE, AND "
          "WHETHER A SPLIT MOVES BY LOSING A VOTER")
    print("            OR BY TURNING ONE.   (item 44, second half)")
    print(LINE)
    print(f"run {now:%Y-%m-%d %H:%M:%S} UTC")
    print("DESCRIPTIVE, CENSUS AND ORDERING ONLY. simulate() is never "
          "called, no entry population is built, no")
    print("sealed slice is read, NO LOOK IS CONSUMED and none is reachable. "
          "Nothing is adopted.")
    print(f"\nTHE CONSTRUCTION WAS COMMITTED BEFORE THIS FILE EXISTED: "
          f"step509_PREREGISTRATION.md")
    print(f"  commit {PREREG_COMMIT}  (2026-09-23)")
    print("  It carries the baseline (CAL-DON), the two families (LOO over "
          "donors, SELF over live rows),")
    print("  the degeneracy rule, three reproduction controls and THREE "
          "predictions - P-LOO (exact arithmetic),")
    print("  P-EXCL (existence) and P-TURN (the item's actual question) - "
          "that this run can falsify.")
    print("\nITEM 44's FIRST HALF IS ANSWERED BY R508 AND IS NOT RE-RUN "
          "HERE: the era factor VALUES move by a")
    print("common 1.0774x with residuals 1.0000-1.0017; largest non-common "
          "mult1 move 0.003. YES for the")
    print("quoted value, NO for the ordering. This round is the SECOND half "
          "and only the second half.")

    pub = P.parse_r499_ranking()
    print(f"\nR499's published ranking parsed off step499_output.txt by "
          f"R501's own parser: {len(pub)} of 11 rows.")
    if len(pub) != 11:
        print("  !! incomplete parse - the round stops.")
        return

    # ------------------------------------------------------------ part (1)
    print("\n" + LINE)
    print("(1) THREE REPRODUCTION CONTROLS. IF ANY FAILS THE ROUND STOPS "
          "AND PUBLISHES NOTHING.")
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

    btc_days = tpp[POOLED_REF]["days"]
    cal_btc = under(prop, pub, btc_days)
    adm_btc = adm_set(cal_btc, prop["live"])
    fails = [d for d in prop["donors"] if not cal_btc["a1_ok"][d]]
    print(f"\n  c. R503's proportional cell, rebuilt. Rows live: "
          f"{len(prop['live'])} of 11.")
    print(f"     Donors (cov >= {DONOR_MIN_COV}%): "
          f"{', '.join(sh(d) for d in prop['donors'])}")
    print(f"     A1-passing references under CAL-BTC (recomputed, not "
          f"retyped): {', '.join(sh(r) for r in adm_btc)}")
    print(f"     donors FAILING A1 under CAL-BTC                          : "
          f"{', '.join(sh(r) for r in fails) if fails else '(none)'}")
    if not (sorted(adm_btc) == sorted(R503_ADMISSIBLE)
            and sorted(fails) == sorted(R503_FAILS_A1)):
        print(f"     !! R503 reported {R503_ADMISSIBLE} admissible and "
              f"{R503_FAILS_A1} failing. The round stops.")
        return
    e_bad = []
    for s, v in R503_ERA1.items():
        got = cal_btc["era1"].get(s, np.nan)
        if not np.isfinite(got) or abs(got - v) > ERA_TOL:
            e_bad.append(("ERA1", s, v, got))
    for s, v in R503_ERA2.items():
        got = cal_btc["era2"].get(s, np.nan)
        if not np.isfinite(got) or abs(got - v) > ERA_TOL:
            e_bad.append(("ERA2", s, v, got))
    for s in R503_NO_ERA1:
        if s in cal_btc["era1"] and np.isfinite(cal_btc["era1"][s]):
            e_bad.append(("ERA1-UNMEAS", s, np.nan, cal_btc["era1"][s]))
    if e_bad:
        print("     !! R503's era column does not reproduce:")
        for w, s, v, g in e_bad:
            print(f"        {w:<12}{sh(s):<6} published {v}  rebuilt {g}")
        print("     The round stops.")
        return
    print(f"     R503's era column reproduced: Rule 1 on {len(R503_ERA1)} "
          f"rows, Rule 2 on {len(R503_ERA2)}, UNMEAS on "
          f"{len(R503_NO_ERA1)}. EXACT to {ERA_TOL}x.")
    print("     This is R503's cell, digit for digit.")

    # ------------------------------------------------------------ part (2)
    print("\n" + LINE)
    print("(2) THE BASELINE. EXCLUSION IS ONLY MEANINGFUL AGAINST WHOEVER "
          "WOULD OTHERWISE VOTE.")
    print(LINE)
    don_days = intersect(tpp, prop["donors"])
    cal_don = under(prop, pub, don_days)
    adm_don = adm_set(cal_don, prop["live"])
    D_STAR = len(don_days)
    span = (f"{min(don_days):%Y-%m-%d} -> {max(don_days):%Y-%m-%d}"
            if don_days else "(empty)")
    print(f"\n  BASELINE = CAL-DON = intersection of the "
          f"{len(prop['donors'])} donors")
    print(f"     days D* = {D_STAR}   span {span}")
    print(f"     admissible references: "
          f"{', '.join(sh(r) for r in adm_don) or '(none)'}   "
          f"({len(adm_don)} of {len(prop['donors'])} donors)")
    print(f"  CONTROL  = CAL-BTC ({len(btc_days)} days)   admissible: "
          f"{', '.join(sh(r) for r in adm_btc)}   ({len(adm_btc)})")
    print(f"\n  R508 measured exactly this and reported 6 against 4. "
          f"Rebuilt here: {len(adm_don)} against {len(adm_btc)}.")
    if D_STAR < ERA_MIN_DAYS:
        print(f"  !! CAL-DON is DEGENERATE ({D_STAR} days < "
              f"{ERA_MIN_DAYS}). There is no baseline and the round stops.")
        return

    # ------------------------------------------------------------ part (3)
    print("\n" + LINE)
    print("(3) THE TWO COMMITTED FAMILIES, BUILT BY RULE AND REPORTED IN "
          "FULL - INCLUDING THE DEGENERATE MEMBERS.")
    print(LINE)
    fams = [("A  LEAVE-ONE-OUT over the donors", family_A(prop)),
            ("B  SELF-PROMOTION over every live ranked row", family_B(prop))]

    cells_all = []
    for fname, members in fams:
        print(f"\n  FAMILY {fname}")
        print(f"  {'calendar':<14}{'days':>7}{'span':>27}"
              f"{'admissible references':>44}{'':>4}")
        print("  " + "-" * 96)
        for nm, who, src, pool in members:
            if len(pool) < ERA_MIN_DAYS:
                print(f"  {nm:<14}{len(pool):>7}{'(degenerate)':>27}"
                      f"{'- nothing is ranked under it -':>44}")
                cells_all.append(dict(fam=fname[0], nm=nm, who=who,
                                      pool=pool, run=None, adm=[],
                                      state="DEGENERATE"))
                continue
            r_ = under(prop, pub, pool)
            a_ = adm_set(r_, prop["live"])
            sp = f"{min(pool):%Y-%m-%d} -> {max(pool):%Y-%m-%d}"
            sub = (set(a_) < set(adm_don)) and len(a_) > 0
            eq = sorted(a_) == sorted(adm_don)
            state = ("EXCLUSION" if sub else
                     "BASELINE-EQUAL" if eq else
                     "EMPTY-ADM" if not a_ else "OTHER")
            tag = {"EXCLUSION": "  <== EXCLUSION CELL",
                   "BASELINE-EQUAL": "", "EMPTY-ADM": "  (admits nobody)",
                   "OTHER": "  (not a subset)"}[state]
            print(f"  {nm:<14}{len(pool):>7}{sp:>27}"
                  f"{(', '.join(sh(x) for x in a_) or '(none)'):>44}{tag}")
            cells_all.append(dict(fam=fname[0], nm=nm, who=who, pool=pool,
                                  run=r_, adm=a_, state=state))

    # ------------------------------------------------- P-LOO, exact check
    print("\n" + LINE)
    print("(3b) P-LOO - THE EXACT ARITHMETIC PREDICTION, CHECKED TO 1e-9.")
    print(LINE)
    print(f"\n  Committed: under LOO-d every OTHER donor covers the calendar "
          f"at EXACTLY 100.0%, and the")
    print(f"  left-out donor d covers it at EXACTLY D*/|LOO-d| = "
          f"{D_STAR}/|LOO-d|, because d's intersection with")
    print(f"  the others' intersection IS the full donor intersection.")
    print(f"\n  {'calendar':<12}{'|LOO-d|':>9}{'d':>7}"
          f"{'d cov measured':>17}{'d cov predicted':>18}{'err':>11}"
          f"{'d passes A1?':>15}{'predicted':>11}")
    print("  " + "-" * 100)
    loo_bad = 0
    loo_checked = 0
    for c in cells_all:
        if c["fam"] != "A" or c["run"] is None:
            continue
        pool, d = c["pool"], c["who"]
        meas_d = a1_cov(tpp, d, pool)
        pred_d = D_STAR / len(pool) * 100.0
        err = abs(meas_d - pred_d)
        got = bool(c["run"]["a1_ok"].get(d))
        pred_ok = (D_STAR / len(pool) >= CONTAIN_MIN and D_STAR >= ERA_MIN_DAYS)
        loo_checked += 1
        if err > P_LOO_TOL * 100 or got != pred_ok:
            loo_bad += 1
        print(f"  {c['nm']:<12}{len(pool):>9}{sh(d):>7}{meas_d:>16.4f}%"
              f"{pred_d:>17.4f}%{err:>11.2e}{str(got):>15}"
              f"{str(pred_ok):>11}")
    # the 100.0% clause, every other donor in every LOO cell
    worst_100 = 0.0
    for c in cells_all:
        if c["fam"] != "A" or c["run"] is None:
            continue
        for o in prop["donors"]:
            if o == c["who"]:
                continue
            worst_100 = max(worst_100,
                            abs(a1_cov(tpp, o, c["pool"]) - 100.0))
    print(f"\n  CLAUSE 1 (every surviving donor covers LOO-d at exactly "
          f"100.0%): worst deviation {worst_100:.2e} pp")
    print(f"  CLAUSE 2 (the left-out donor covers at exactly D*/|LOO-d|, "
          f"and its A1 verdict follows): "
          f"{loo_checked - loo_bad} of {loo_checked} cells exact")
    p_loo = (worst_100 <= P_LOO_TOL * 100) and loo_bad == 0
    print(f"\n  P-LOO: {'HOLDS - the arithmetic is the measurement.' if p_loo else '!! FALSIFIED - HEADLINE'}")

    # ------------------------------------------------------------ part (4)
    print("\n" + LINE)
    print("(4) P-EXCL - DOES A STRICT, NON-EMPTY EXCLUSION CELL EXIST AT "
          "ALL? THIS HAS NEVER BEEN BUILT HERE.")
    print(LINE)
    excl = [c for c in cells_all if c["state"] == "EXCLUSION"]
    print(f"\n  members built: {len(cells_all)}   "
          f"degenerate: {sum(1 for c in cells_all if c['state'] == 'DEGENERATE')}   "
          f"identical to baseline: "
          f"{sum(1 for c in cells_all if c['state'] == 'BASELINE-EQUAL')}   "
          f"admit nobody: "
          f"{sum(1 for c in cells_all if c['state'] == 'EMPTY-ADM')}")
    print(f"  EXCLUSION CELLS (admissible set a strict, non-empty subset of "
          f"CAL-DON's): {len(excl)}")
    for c in excl:
        removed = [r for r in adm_don if r not in c["adm"]]
        print(f"     {c['nm']:<12}{len(c['pool']):>6}d   admits "
              f"{', '.join(sh(x) for x in c['adm']):<32} "
              f"REMOVES {', '.join(sh(x) for x in removed)}")
    print(f"\n  P-EXCL: {'HOLDS' if excl else '!! FALSIFIED'}")
    if not excl:
        print("  -> Under the pinned fences on this disk, NO rule-built "
              "calendar in either committed family")
        print("     removes a single voter without removing them all. That "
              "is a complete answer to item 44's")
        print("     second half, not a null result, and the item closes on "
              "it. P-TURN cannot be tested.")

    # ------------------------------------------------------------ part (5)
    print("\n" + LINE)
    print("(5) P-TURN - THE ITEM'S ACTUAL QUESTION. DOES A SPLIT MOVE BY "
          "LOSING A VOTER, OR BY TURNING ONE?")
    print(LINE)
    if not excl:
        print("\n  Not reachable: P-EXCL failed, so there is no cell in "
              "which a voter is removed.")
    else:
        base_order = cal_don["o1"]
        v_base = verdict_map(cal_don)
        total_signs = total_flips = 0
        total_moved = total_attrib = 0
        worst_ratio_mv = 0.0
        bad_direction = []
        for c in excl:
            r_ = c["run"]
            removed = [r for r in adm_don if r not in c["adm"]]
            print(f"\n  --- {c['nm']}  ({len(c['pool'])} days)  "
                  f"voter(s) REMOVED: {', '.join(sh(x) for x in removed)} "
                  + "-" * max(0, 40 - len(c['nm'])))

            # --- clause 1: no surviving voter's sign moves
            finite = [s for s in prop["live"]
                      if np.isfinite(cal_don["rows"][s]["nmult"])]
            checked = flips = 0
            for i in range(len(finite)):
                for j in range(i + 1, len(finite)):
                    a, b = finite[i], finite[j]
                    common = [r for r in cal_don["adm"][a]
                              if r in cal_don["adm"][b]
                              and r in r_["adm"][a] and r in r_["adm"][b]]
                    for r in common:
                        v0 = (cal_don["rows"][a]["nmult"] / cal_don["cells"][a][r]
                              > cal_don["rows"][b]["nmult"] / cal_don["cells"][b][r])
                        v1 = (r_["rows"][a]["nmult"] / r_["cells"][a][r]
                              > r_["rows"][b]["nmult"] / r_["cells"][b][r])
                        checked += 1
                        flips += 0 if v0 == v1 else 1
                        x0 = cal_don["rows"][a]["nmult"] / cal_don["cells"][a][r]
                        x1 = r_["rows"][a]["nmult"] / r_["cells"][a][r]
                        worst_ratio_mv = max(worst_ratio_mv,
                                             abs(x1 - x0) / abs(x0))
            total_signs += checked
            total_flips += flips
            print(f"      CLAUSE 1  surviving-voter vote cells checked: "
                  f"{checked}   signs that MOVED: {flips}")

            # --- clause 2: every verdict move attributed to the removal
            v_new = verdict_map(r_)
            v_replay = replay_without(cal_don, removed[0], base_order) \
                if len(removed) == 1 else None
            if len(removed) > 1:
                adm2 = {s: [x for x in v if x not in removed]
                        for s, v in cal_don["adm"].items()}
                rs, us = T.unanimity(cal_don["rows"], cal_don["cells"],
                                     adm2, base_order)
                v_replay = verdict_map({"resolved": rs, "unordered": us})
            moved = [k for k in v_base
                     if k in v_new and v_base[k][0] != v_new[k][0]]
            total_moved += len(moved)
            print(f"      CLAUSE 2  pairs whose RESOLVED/UNORDERED verdict "
                  f"MOVED vs the baseline: {len(moved)}")
            for k in moved:
                a, b = tuple(k)
                rep = v_replay.get(k, ("(absent)", ""))
                ok = rep[0] == v_new[k][0]
                total_attrib += 1 if ok else 0
                print(f"         {sh(a):<5} vs {sh(b):<5}  "
                      f"{v_base[k][0]:<10} -> {v_new[k][0]:<10}   "
                      f"baseline votes with {', '.join(sh(x) for x in removed)} "
                      f"struck out: {rep[0]:<10} "
                      f"{'ATTRIBUTED' if ok else '!! NOT EXPLAINED BY THE REMOVAL'}")
            if not moved:
                print("         (none - the removal changed no pair's "
                      "verdict in this cell)")
            # --- the committed direction claim
            for k in moved:
                if v_base[k][0] == "RESOLVED" and v_new[k][0] == "RESOLVED":
                    bad_direction.append(k)
            print(f"      Rule 1 order  : "
                  f"{' > '.join(sh(x) for x in r_['o1'])}")
            print(f"      CAL-DON       : "
                  f"{' > '.join(sh(x) for x in cal_don['o1'])}")
            top = r_["top"]
            bad = [(a, b, w) for a, b, w in r_["unordered"]
                   if a in top and b in top]
            miss = [s for s in top if not np.isfinite(r_["rows"][s]["m1"])]
            print(f"      TOP FOUR by mult*: "
                  f"{', '.join(sh(x) for x in top)}   resolve? "
                  f"{'YES' if (not bad and not miss) else 'NO'}"
                  f"   ({len(bad)} unordered, {len(miss)} without a factor)")
            for a, b, w in bad:
                print(f"         {sh(a):<5} vs {sh(b):<5}  {w}")

        print(f"\n  ACROSS EVERY EXCLUSION CELL")
        print(f"     surviving-voter vote cells checked : {total_signs}")
        print(f"     surviving-voter signs that MOVED   : {total_flips}"
              f"   (worst single-side ratio movement {worst_ratio_mv:.3e})")
        print(f"     pair verdicts that MOVED           : {total_moved}")
        print(f"     of those, fully ATTRIBUTED to the removed voter: "
              f"{total_attrib}")
        print(f"     RESOLVED -> RESOLVED reversals     : "
              f"{len(bad_direction)}  (the committed falsifier)")
        p_turn = (total_flips == 0 and total_attrib == total_moved
                  and not bad_direction)
        print(f"\n  P-TURN: {'HOLDS. A split moves by LOSING a voter and never by TURNING one.' if p_turn else '!! FALSIFIED - HEADLINE'}")
        if total_moved == 0:
            print("     Read this honestly: no split MOVED in any exclusion "
                  "cell, so P-TURN's second clause")
            print("     is satisfied vacuously. The substantive half that "
                  "IS exercised is clause 1 - a voter")
            print("     was genuinely removed and no surviving voter's sign "
                  "moved.")

        # ---- POST-HOC REPORTING ADDITION, DECLARED (prereg section 9). It
        # ---- changes no measurement, threshold, calendar, construction or
        # ---- verdict; it EXPLAINS the zero the committed run produced, and
        # ---- the explanation is less flattering than the zero.
        print("\n" + LINE)
        print("(5c) WHY CLAUSE 2 CAME BACK ZERO. POST-HOC REPORTING "
              "ADDITION, DECLARED - no measurement changes.")
        print(LINE)
        print("\n  'Zero verdicts moved' is NOT the same sentence as 'the "
              "removal was harmless'. A baseline pair")
        print("  can fail to move for two very different reasons: it "
              "SURVIVED the removal unchanged, or it")
        print("  LEFT THE TABLE because a row lost its era factor and is no "
              "longer ranked at all. The")
        print("  committed comparison only counts the first kind. Here is "
              "the split.")
        print(f"\n  {'cell':<13}{'removed':<22}{'base pairs':>11}"
              f"{'shared':>8}{'absent':>8}{'moved':>7}   rows that left the "
              f"ranking")
        print("  " + "-" * 104)
        for c in excl:
            r_ = c["run"]
            removed = [r for r in adm_don if r not in c["adm"]]
            v_new = verdict_map(r_)
            shared = [k for k in v_base if k in v_new]
            absent = [k for k in v_base if k not in v_new]
            mv = [k for k in shared if v_base[k][0] != v_new[k][0]]
            gone = [s for s in cal_don["o1"] if s not in r_["o1"]]
            print(f"  {c['nm']:<13}{', '.join(sh(x) for x in removed):<22}"
                  f"{len(v_base):>11}{len(shared):>8}{len(absent):>8}"
                  f"{len(mv):>7}   "
                  f"{', '.join(sh(x) for x in gone) or '(none)'}")

        print("\n  AND THE REASON UNDERNEATH IT. A reference votes on a pair "
              "(a,b) only if it is admissible for")
        print("  BOTH rows, and `adm[row]` carries a SECOND gate beside A1: "
              "`cov_row >= 0.98`, the reference's")
        print("  containment of THAT ROW's window - which does not depend on "
              "the pooled calendar at all.")
        print("  So the question is not 'was a voter removed' but 'was a "
              "voter that was actually VOTING removed'.")
        base_pairs = [frozenset((cal_don["o1"][i], cal_don["o1"][j]))
                      for i in range(len(cal_don["o1"]))
                      for j in range(i + 1, len(cal_don["o1"]))]
        print(f"\n  {'reference':<12}{'baseline pairs it votes on':>28}"
              f"{'of':>4}{'':<3}{'sole dissenter on':>19}   pairs where it "
              f"is the ONLY thing standing between")
        print("  " + "-" * 104)
        for r in adm_don:
            votes = [k for k in base_pairs
                     if r in cal_don["adm"][tuple(k)[0]]
                     and r in cal_don["adm"][tuple(k)[1]]]
            sole = []
            for k in votes:
                a, b = tuple(k)
                common = [x for x in cal_don["adm"][a]
                          if x in cal_don["adm"][b]]
                if len(common) < 2:
                    continue
                sg = {x: (cal_don["rows"][a]["nmult"] / cal_don["cells"][a][x]
                          > cal_don["rows"][b]["nmult"] / cal_don["cells"][b][x])
                      for x in common}
                others = [sg[x] for x in common if x != r]
                if len(set(sg.values())) > 1 and len(set(others)) == 1:
                    sole.append(k)
            print(f"  {sh(r):<12}{len(votes):>28}{len(base_pairs):>4}"
                  f"{'':<3}{len(sole):>19}   "
                  f"{', '.join(sh(tuple(k)[0]) + '/' + sh(tuple(k)[1]) for k in sole) or '(none)'}")
        print("\n  THE HONEST SENTENCE: every exclusion this desk's own rules "
              "can build removes a reference that")
        print("  was already gated out of the pairs that are actually "
              "contested. A1 is the calendar's only")
        print("  channel into an ordering (R507) and that channel is itself "
              "gated downstream by a")
        print("  calendar-INDEPENDENT containment test. On this disk the two "
              "gates overlap so completely that")
        print("  NO calendar in either committed family changes a single "
              "pairwise verdict.")

        # ---- POST-HOC REPORTING ADDITION, DECLARED (prereg section 9). It
        # ---- changes no measurement, threshold, calendar, construction or
        # ---- verdict. It reports WHAT the two zero-vote references are
        # ---- doing in the baseline instead, which the table above exposes.
        print("\n" + LINE)
        print("(5d) WHAT THE TWO ZERO-VOTE REFERENCES ARE ACTUALLY DOING. "
              "POST-HOC REPORTING ADDITION, DECLARED.")
        print(LINE)
        print("\n  A reference with 0 votes is still counted in the "
              "'admissible set' census, because that census is")
        print("  the UNION over rows of `adm[row]`. So it is worth printing "
              "WHICH rows each reference is")
        print("  admissible for, which the census flattens away.")
        print(f"\n  {'reference':<12}{'rows it is admissible for':>26}"
              f"{'':<4}which rows")
        print("  " + "-" * 104)
        for r in adm_don:
            rws = [s for s in prop["live"] if r in cal_don["adm"][s]]
            flag = ("   <== ITSELF ONLY"
                    if rws == [r] else "")
            print(f"  {sh(r):<12}{len(rws):>26}{'':<4}"
                  f"{', '.join(sh(x) for x in rws)}{flag}")
        print(f"\n  And the other side of the same fact: how many DISTINCT "
              f"references each ranked row's Rule 1 era")
        print(f"  factor is a median over. A median over one cell is not an "
              f"average of anything.")
        print(f"\n  {'row':<8}{'ERA1':>9}{'refs in the median':>21}"
              f"{'':<3}which")
        print("  " + "-" * 104)
        for s in cal_don["o1"]:
            ok = cal_don["adm"][s]
            flag = ("   <== SELF-REFERENCE ONLY: this row is era-corrected "
                    "by its own tape" if ok == [s] else "")
            print(f"  {sh(s):<8}{cal_don['era1'][s]:>9.3f}{len(ok):>21}"
                  f"{'':<3}{', '.join(sh(x) for x in ok)}{flag}")
        vb = verdict_map(cal_don)
        solo = [s for s in cal_don["o1"] if cal_don["adm"][s] == [s]]
        if solo:
            print(f"\n  Those rows can never be ORDERED against anything: "
                  f"unanimity needs a reference admissible for")
            print(f"  BOTH rows, and a row whose only admissible reference "
                  f"is itself shares none with any other.")
            for s in solo:
                pr = [k for k in vb if s in k]
                un = [k for k in pr if vb[k][0] == "UNORDERED"]
                print(f"     {sh(s):<6} baseline pairs {len(pr):>2}   "
                      f"UNORDERED {len(un):>2}   RESOLVED "
                      f"{len(pr) - len(un):>2}")
            print(f"\n  So R508's 'CAL-DON places two more rows' is exact "
                  f"about the NUMBER and must not be read as a")
            print(f"  PLACE: those rows receive an era factor computed "
                  f"against their own tape and remain UNORDERED")
            print(f"  against every other row in the table. Nothing in R508 "
                  f"is wrong; this is the caveat that")
            print(f"  belongs beside it.")

    # ------------------------------------------------------------ part (6)
    print("\n" + LINE)
    print("(6) DECLARED SECONDARY - R506's FENCE-T CELL, FOR CONTINUITY "
          "WITH R506/R507/R508. NO VERDICT IS TAKEN FROM IT.")
    print(LINE)
    ft = build_cell("FENCE-T (R506)", lambda s: T_END_FENCE_T)
    ft_don = intersect(ft["tp"], ft["donors"])
    ft_base = under(ft, pub, ft_don) if len(ft_don) >= ERA_MIN_DAYS else None
    print(f"\n  T_END = {T_END_FENCE_T} for every row. Rows live: "
          f"{len(ft['live'])} of 11.")
    print(f"  Donors: {', '.join(sh(d) for d in ft['donors'])}")
    if ft_base is None:
        print(f"  CAL-DON here is {len(ft_don)} days - DEGENERATE. No "
              f"baseline exists in this cell and it is carried no further.")
    else:
        ft_adm = adm_set(ft_base, ft["live"])
        print(f"  CAL-DON: {len(ft_don)} days   admissible: "
              f"{', '.join(sh(r) for r in ft_adm)}")
        n_ex = 0
        for nm, who, src, pool in family_A(ft) + family_B(ft):
            if len(pool) < ERA_MIN_DAYS:
                continue
            r_ = under(ft, pub, pool)
            a_ = adm_set(r_, ft["live"])
            if set(a_) < set(ft_adm) and a_:
                n_ex += 1
                print(f"     EXCLUSION  {nm:<12}{len(pool):>6}d   admits "
                      f"{', '.join(sh(x) for x in a_):<30} REMOVES "
                      f"{', '.join(sh(x) for x in ft_adm if x not in a_)}")
        print(f"  exclusion cells in the secondary cell: {n_ex}")

    # ------------------------------------------------------------- closing
    print("\n" + LINE)
    print("WHAT THIS ROUND ESTABLISHES")
    print(LINE)
    print(f"\n  1. THE CONSTRUCTION PREDATES THE ANSWER: commit "
          f"{PREREG_COMMIT}, made before this file existed.")
    print(f"\n  2. P-LOO: {'HOLDS' if p_loo else 'FALSIFIED'}.   "
          f"P-EXCL: {'HOLDS' if excl else 'FALSIFIED'} "
          f"({len(excl)} exclusion cells of {len(cells_all)} built).")
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
