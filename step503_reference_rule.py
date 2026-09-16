"""
step503_reference_rule.py - ROUND 503

THE TOP FOUR ROWS OF THAT RANKING DO NOT HAVE A STABLE ORDER, AND THE DESK
READS THEM TO DECIDE WHERE A SEALED LOOK GOES.
(QUEUE ITEM 38)

Research only. No orders. No account. No live file touched, imported or
modified. Nothing here is deployed by this script under any outcome.

THE RULE THIS FILE IMPLEMENTS WAS COMMITTED TO GIT BEFORE THIS FILE EXISTED.
  step503_PREREGISTRATION.md, commit 2deb2fc6aa4a7c9e9c8f7f03d64f66a1e019dc15,
  2026-09-16 03:26:06 -0400. Every constant below is copied out of that file
  and none of them may be changed by this round. The queue item's whole point
  is that the rule cannot have been chosen by looking at the order it gives,
  and the git timestamp on that commit preceding this file's first output is
  the evidence offered for it.

QUEUE ITEM 38, VERBATIM
  R502 stated the ranking a third time and got two different answers out of
  the same correction. On the single named reference (BTCUSD) 45 of 45
  orderings survive; on the median of the six dense references - the
  estimator that matches how R501's own gap was computed - 42 of 45 survive
  and every reversal is in the top four: PAXG 2nd or 4th, XRP 2nd or 4th,
  SOL between them either way. Rows 5-10 (DOGE > BTC > LTC > ETH > DOT >
  AVAX) are identical under every correction R500/R501/R502 have applied.
  Two of the unstable four are INTACT (PAXG, XRP), which is precisely why
  this is not cosmetic.
  The cause is measured and is not a mystery: the reference-to-reference
  spread of the era factor is 0.232 on PAXG and 0.197 on XRP against 0.019
  on the five rows that share the pooled calendar, so the rows that need an
  era factor are exactly the rows where naming the reference decides the
  answer.
  Deliverable, and the item will accept EITHER: (a) a principled reference
  rule fixed in advance and defended on something other than the answer it
  gives - e.g. weight each reference by its overlap with the row's window,
  or require a reference whose own window CONTAINS the row's, and show the
  rule was not chosen by looking at the resulting order; or (b) the finding
  that no such rule is available on this disk, in which case publish the
  ranking with rows 1-4 explicitly marked UNORDERED and stop the desk
  quoting an order among them. Report which it is. An estimator picked
  because it put a particular instrument on top is the failure mode this
  item exists to prevent, so the rule is written down before the ordering is
  recomputed.
  THE FENCE: R493's, unchanged. `simulate()` is never called, no entry
  population is scored, no sealed slice is read - the references' final 20%
  included - no look, no candidate. This corrects a table; it does not
  select anything off it, and it explicitly does not spend PAXG's or XRP's
  slice.

THE FENCE, INHERITED AND ENFORCED AS CODE DISCIPLINE
  1. `simulate()` IS NEVER CALLED IN THIS FILE, and neither is any entry
     builder. No sweep is scanned, no break of structure is detected, no
     fill is modelled, no stop is measured, no outcome is read. The only
     things read off tape are (a) WHICH MINUTES CARRY A BAR and (b) THE SIZE
     OF A ONE-MINUTE MOVE.
  2. EVERY TAPE MEASUREMENT STOPS AT THE 80% BOUNDARY of that instrument's
     own window, via R501's `fenced()`, references included.
  3. NOTHING IS SELECTED. The output is a fourth statement of an existing
     ordering plus a list of pairs the desk may no longer quote an order
     for. No instrument is qualified and no cell is tested.
  4. THE RULE IS THE COMMITTED ONE. Admissibility, the unanimity criterion,
     the weighting and the three-part decision are copied from the
     pre-registration and are not re-derived here.

WHAT IS PRIMARY-SOURCED HERE AND WHAT IS NOT
  PUBLISHED, IN-LOG, READ OFF DISK RATHER THAN RETYPED: R499's ranking is
    parsed out of `step499_output.txt` by R501's own parser, imported
    unmodified, so the table being corrected is the published one.
  RECOMPUTED, NOT RETYPED: R499's vol column and R501's xSAME column are
    rebuilt here with their own functions and checked against their
    published figures. If either fails to reproduce the round stops.
  NO VENUE POLL. R499's fee column is FROZEN, as in R501 and R502, because
    the only thing this round is allowed to move is the era factor.

USAGE
  python3 step503_reference_rule.py
"""

import sys
import warnings
from datetime import datetime, timezone

import numpy as np

warnings.filterwarnings("ignore")

REPO = "/Users/wallacechen/cryptobot"
sys.path.insert(0, REPO)

import step501_coverage_column as P      # noqa: E402  (R501, unmodified)
import step502_era_column as E           # noqa: E402  (R502, unmodified)

LINE = "=" * 108

# ---------------------------------------------------------------- the rule
# Every constant below is copied from step503_PREREGISTRATION.md, committed
# 2026-09-16 03:26:06 -0400 as 2deb2fc, before this file existed.
PREREG_COMMIT = "2deb2fc6aa4a7c9e9c8f7f03d64f66a1e019dc15"
POOLED_REF = "BTCUSD"     # pooled calendar, INHERITED from R502 unchanged
CONTAIN_MIN = 0.98        # A1 and A2, containment threshold
ERA_MIN_DAYS = E.ERA_MIN_DAYS      # 120, inherited from R502
ERA_MIN_OVL = E.ERA_MIN_OVL        # 0.30, inherited from R502, Rule 2 floor
TOP_N = 4                 # "the top four", the item's subject

R501_XSAME = E.R501_XSAME          # reproduction target, published
R502_ORDER_REF = ["LINKUSD", "PAXGUSD", "SOLUSD", "XRPUSD", "DOGEUSD",
                  "BTCUSD", "LTCUSD", "ETHUSD", "DOTUSD", "AVAXUSD"]
R502_ORDER_MED = ["LINKUSD", "XRPUSD", "SOLUSD", "PAXGUSD", "DOGEUSD",
                  "BTCUSD", "LTCUSD", "ETHUSD", "DOTUSD", "AVAXUSD"]


def sh(s):
    return s.replace("USD", "")


def main():
    now = datetime.now(timezone.utc)
    print(LINE)
    print("ROUND 503 - THE TOP FOUR ROWS DO NOT HAVE A STABLE ORDER, AND THE "
          "DESK READS THEM.   (item 38)")
    print(LINE)
    print(f"run {now:%Y-%m-%d %H:%M:%S} UTC")
    print("A CORRECTION to a table this desk reuses, not a hypothesis. "
          "simulate() is never called, no")
    print("entry population is built, no sealed slice is read, NO LOOK IS "
          "CONSUMED and none could be.")
    print(f"\nTHE RULE WAS COMMITTED BEFORE THIS FILE EXISTED: "
          f"step503_PREREGISTRATION.md")
    print(f"  commit {PREREG_COMMIT}  (2026-09-16 03:26:06 -0400)")
    print("  Every threshold below is copied out of it. The git timestamp "
          "on that commit precedes this")
    print("  file's first output, which is the evidence this round offers "
          "that the rule was not chosen by")
    print("  looking at the order it gives.")
    print(f"\nTHE A-PRIORI OBJECTION THAT GENERATES THE RULE, established "
          f"from the WINDOWS alone:")
    print("  ERA(row|ref) is one tape's volatility on the ROW's calendar "
          "over the same tape's volatility on")
    print("  the POOLED calendar. It is a measurement only where that tape "
          "spans both. R502's median-of-six")
    print("  divides each reference by ITS OWN whole window, and the six "
          "windows are not the same window -")
    print("  six ratios against six different denominators are not on a "
          "common scale and must not be medianed.")

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
    print("(1) REPRODUCTION CONTROLS - the same two R502 ran. If either "
          "fails the round stops.")
    print(LINE)
    worst = max(abs(tp[s]["coord"] - pub[s]["vol"]) for s, _, _ in P.RANKED)
    print(f"\n  a. R499's vol% column, recomputed behind the same fence: "
          f"max absolute difference {worst:.4f} pp")
    if worst > 0.0001:
        print("     !! this is not R499's table. The round stops.")
        return
    print("     EXACT. The table being corrected is the published one.")

    donors = [s for s, _, _ in P.RANKED if tp[s]["cov"] >= P.DONOR_MIN_COV]
    print(f"\n  b. R501's xSAME column, recomputed with R501's own "
          f"functions. Donors (>= {P.DONOR_MIN_COV:.0f}% full): "
          f"{', '.join(sh(d) for d in donors)}")
    dbx = {}
    r501_worst = 0.0
    for sym, _, _ in P.RANKED:
        t = tp[sym]
        xsame = []
        for dn in donors:
            if dn == sym:
                continue
            d = tp[dn]
            fm = P.transplant(d["f"], d["keys"], t["keys"])
            if len(fm) < P.MASK_MIN_BARS:
                continue
            days = set(fm["t"].dt.floor("D").unique())
            if len(days) < P.MASK_MIN_DAYS:
                continue
            same = d["f"][d["f"]["t"].dt.floor("D").isin(days)]
            cm, cs = P.coord(fm), P.coord(same)
            if not (np.isfinite(cm) and np.isfinite(cs) and cs > 0):
                continue
            xsame.append(cm / cs)
        if len(xsame) < 2:
            dbx[sym] = np.nan
            continue
        dbx[sym] = float(np.median(xsame))
        ref = R501_XSAME.get(sym, np.nan)
        if np.isfinite(ref):
            r501_worst = max(r501_worst, abs(dbx[sym] - ref))
    print(f"     max absolute difference against R501's published xSAME: "
          f"{r501_worst:.3f}x")
    if r501_worst > 0.0015:
        print("     !! R501 does not reproduce. The round stops.")
        return
    print("     EXACT to the published precision. The era correction layers "
          "onto R501's own numbers.")

    # ------------------------------------------------------------ part (2)
    print("\n" + LINE)
    print("(2) ADMISSIBILITY UNDER THE COMMITTED RULE - WHICH REFERENCES "
          "ACTUALLY SPAN BOTH CALENDARS")
    print(LINE)
    pooled = tp[POOLED_REF]["days"]
    npool = len(pooled)
    print(f"\n  POOLED CALENDAR (inherited from R502, unchanged): "
          f"{POOLED_REF}'s fenced window, "
          f"{tp[POOLED_REF]['t0']:%Y-%m-%d} -> "
          f"{tp[POOLED_REF]['t1']:%Y-%m-%d}, {npool} days.")
    print(f"  RULE 1 admissibility: a reference must carry "
          f">= {CONTAIN_MIN:.0%} of POOLED_DAYS (A1) AND "
          f">= {CONTAIN_MIN:.0%} of the")
    print(f"  row's own days (A2), both overlaps >= {ERA_MIN_DAYS} days. "
          f"DENOMINATOR IS ALWAYS THE POOLED CALENDAR,")
    print("  never the reference's private window - that is the defect the "
          "rule exists to remove.")

    # A1 is a property of the reference alone. Print it first.
    print(f"\n  A1, the reference's own coverage of the pooled calendar:")
    print(f"     {'reference':<11}{'its fenced window':<26}{'ovl days':>10}"
          f"{'A1 cov':>9}   verdict")
    print("     " + "-" * 64)
    a1_ok = {}
    for dn in donors:
        ov = len(tp[dn]["days"] & pooled)
        c = ov / npool
        ok = (c >= CONTAIN_MIN and ov >= ERA_MIN_DAYS)
        a1_ok[dn] = ok
        w = f"{tp[dn]['t0']:%Y-%m-%d} -> {tp[dn]['t1']:%Y-%m-%d}"
        print(f"     {sh(dn):<11}{w:<26}{ov:>10}{c:>8.0%}   "
              f"{'ADMISSIBLE denominator' if ok else 'FAILS A1 - excluded'}")
    print(f"\n     {sum(a1_ok.values())} of {len(donors)} dense references "
          f"can carry a pooled-calendar denominator at all.")
    print("     This is decided by the windows and nothing else; no era "
          "factor has been computed yet.")

    # -------- the per-reference era matrix, denominator on POOLED always
    den = {}
    for dn in donors:
        f = tp[dn]["f"]
        g = f[f["t"].dt.floor("D").isin(pooled)]
        den[dn] = P.coord(g) if len(g) else np.nan

    era_cell = {}          # era_cell[row][ref] = era factor
    adm = {}               # adm[row] = [refs admissible for that row]
    wsum = {}
    print(f"\n  THE ERA MATRIX. Every cell divides by the reference's "
          f"coordinate ON THE POOLED CALENDAR.")
    print(f"  'A' marks a cell ADMISSIBLE under Rule 1; a bare number is "
          f"computable but not admissible.")
    print(f"\n  {'instrument':<11}", end="")
    for dn in donors:
        print(f"{sh(dn):>10}", end="")
    print(f"{'RULE1 med':>11}{'n adm':>7}{'RULE2 wtd':>11}")
    print("  " + "-" * (11 + 10 * len(donors) + 29))
    era1, era2 = {}, {}
    for sym, _, _ in P.RANKED:
        t = tp[sym]
        cells, ok_refs, wnum, wden = {}, [], 0.0, 0.0
        print(f"  {sym:<11}", end="")
        for dn in donors:
            d = tp[dn]
            ovl_row = t["days"] & d["days"]
            c_row_cov = len(ovl_row) / max(t["nday"], 1)
            ovl_pool = d["days"] & pooled
            c_pool_cov = len(ovl_pool) / npool
            if (len(ovl_row) < ERA_MIN_DAYS or c_row_cov < ERA_MIN_OVL
                    or not np.isfinite(den[dn]) or den[dn] <= 0):
                print(f"{'--':>10}", end="")
                continue
            c_row = P.coord(d["f"][d["f"]["t"].dt.floor("D").isin(ovl_row)])
            if not np.isfinite(c_row):
                print(f"{'--':>10}", end="")
                continue
            x = c_row / den[dn]
            cells[dn] = x
            is_adm = (a1_ok[dn] and c_row_cov >= CONTAIN_MIN
                      and len(ovl_row) >= ERA_MIN_DAYS)
            if is_adm:
                ok_refs.append(dn)
            w = c_row_cov * c_pool_cov
            if c_pool_cov >= ERA_MIN_OVL and len(ovl_pool) >= ERA_MIN_DAYS:
                wnum += w * x
                wden += w
            print(f"{x:>9.3f}{'A' if is_adm else ' '}", end="")
        era_cell[sym] = cells
        adm[sym] = ok_refs
        era1[sym] = (float(np.median([cells[r] for r in ok_refs]))
                     if ok_refs else np.nan)
        era2[sym] = wnum / wden if wden > 0 else np.nan
        wsum[sym] = wden
        m1 = f"{era1[sym]:.3f}x" if np.isfinite(era1[sym]) else "UNMEAS"
        m2 = f"{era2[sym]:.3f}x" if np.isfinite(era2[sym]) else "--"
        print(f"{m1:>11}{len(ok_refs):>7}{m2:>11}")

    unmeas = [s for s in era1 if not np.isfinite(era1[s])]
    print(f"\n  Rows with NO admissible reference, given NO era factor "
          f"(item 25's rule): "
          f"{', '.join(sh(s) for s in unmeas) if unmeas else 'none'}")
    for s in unmeas:
        t = tp[s]
        best = max(((len(t['days'] & tp[dn]['days']) / max(t['nday'], 1), dn)
                    for dn in donors if a1_ok[dn]), default=(0.0, None))
        if best[1] is not None:
            print(f"    {sh(s):<6} its window {t['t0']:%Y-%m-%d} -> "
                  f"{t['t1']:%Y-%m-%d}; the best A1-passing reference covers "
                  f"{best[0]:.0%} of it ({sh(best[1])}), under "
                  f"{CONTAIN_MIN:.0%}.")

    # ------------------------------------------------------------ part (3)
    print("\n" + LINE)
    print("(3) THE RANKING UNDER EACH COMMITTED RULE. R499's FEE COLUMN "
          "STAYS FROZEN.")
    print(LINE)
    rows = []
    for sym, _, _ in P.RANKED:
        p_ = pub[sym]
        x = dbx.get(sym, np.nan)
        nv = p_["vol"] / x if np.isfinite(x) else np.nan
        r = dict(sym=sym, vol=p_["vol"], fee=p_["fee"], xsame=x, nvol=nv,
                 nmult=nv / p_["fee"] if np.isfinite(nv) else np.nan,
                 sealed=p_["sealed"], e1=era1.get(sym, np.nan),
                 e2=era2.get(sym, np.nan))
        r["m1"] = (r["nmult"] / r["e1"]
                   if np.isfinite(r["nmult"]) and np.isfinite(r["e1"])
                   else np.nan)
        r["m2"] = (r["nmult"] / r["e2"]
                   if np.isfinite(r["nmult"]) and np.isfinite(r["e2"])
                   else np.nan)
        rows.append(r)
    byname = {r["sym"]: r for r in rows}

    print(f"\n  {'#':<4}{'instrument':<10}{'vol%':>9}{'/xSAME':>9}"
          f"{'vol* %':>9}{'fee%RT':>9}{'mult*':>8}{'ERA1':>9}{'mult1':>8}"
          f"{'ERA2':>9}{'mult2':>8}   sealed")
    print("  " + "-" * 100)
    o1 = [r["sym"] for r in sorted([r for r in rows if np.isfinite(r["m1"])],
                                   key=lambda r: -r["m1"])]
    o2 = [r["sym"] for r in sorted([r for r in rows if np.isfinite(r["m2"])],
                                   key=lambda r: -r["m2"])]
    for i, r in enumerate(sorted(
            rows, key=lambda r: -(r["nmult"] if np.isfinite(r["nmult"])
                                  else -1)), 1):
        f2 = lambda v, s="": (f"{v:.3f}x" if np.isfinite(v) else s)   # noqa
        f3 = lambda v, s="": (f"{v:.2f}" if np.isfinite(v) else s)    # noqa
        f4 = lambda v, s="": (f"{v:.4f}" if np.isfinite(v) else s)    # noqa
        print(f"  {i:<4}{r['sym']:<10}{r['vol']:>9.4f}"
              f"{f2(r['xsame'],'--'):>9}"
              f"{f4(r['nvol'],'--'):>9}"
              f"{r['fee']:>9.4f}{f3(r['nmult'],'--'):>8}"
              f"{f2(r['e1'],'UNMEAS'):>9}{f3(r['m1'],'--'):>8}"
              f"{f2(r['e2'],'--'):>9}{f3(r['m2'],'--'):>8}   {r['sealed']}")

    print(f"\n  R501 de-biased order (published) : "
          f"{' > '.join(sh(s) for s in R502_ORDER_REF)}")
    print(f"  R502 single-reference order      : "
          f"{' > '.join(sh(s) for s in R502_ORDER_REF)}")
    print(f"  R502 median-of-six order         : "
          f"{' > '.join(sh(s) for s in R502_ORDER_MED)}")
    print(f"  RULE 1 (containment, median adm) : "
          f"{' > '.join(sh(s) for s in o1)}")
    print(f"  RULE 2 (overlap-weighted)        : "
          f"{' > '.join(sh(s) for s in o2)}")
    miss1 = [r["sym"] for r in rows if not np.isfinite(r["m1"])]
    if miss1:
        print(f"  absent from RULE 1's ordering, having no admissible "
              f"reference: {', '.join(sh(s) for s in miss1)}")

    # ------------------------------------------------------------ part (4)
    print("\n" + LINE)
    print("(4) THE UNANIMITY CRITERION - AN ORDERING THAT DEPENDS ON WHICH "
          "ADMISSIBLE TAPE WAS NAMED IS NOT")
    print("    AN ORDERING. Every pair is re-decided with each admissible "
          "reference alone, one at a time.")
    print(LINE)
    readable = [s for s in o1]
    resolved, unordered = [], []
    for i in range(len(readable)):
        for j in range(i + 1, len(readable)):
            a, b = readable[i], readable[j]
            common = [r for r in adm[a] if r in adm[b]]
            if not common:
                unordered.append((a, b, "no reference admissible for both"))
                continue
            signs = set()
            for r_ in common:
                ma = byname[a]["nmult"] / era_cell[a][r_]
                mb = byname[b]["nmult"] / era_cell[b][r_]
                signs.add(ma > mb)
            if len(signs) == 1:
                resolved.append((a, b, len(common)))
            else:
                unordered.append((a, b, f"{len(common)} admissible "
                                        f"references disagree"))
    npairs = len(resolved) + len(unordered)
    print(f"\n  Rows carrying a Rule 1 era factor: {len(readable)} of 11. "
          f"Ordered pairs among them: {npairs}.")
    print(f"    RESOLVED (every admissible reference agrees) : "
          f"{len(resolved)}")
    print(f"    UNORDERED                                    : "
          f"{len(unordered)}")
    if unordered:
        print("\n  The pairs the desk may no longer quote an order for, and "
              "why each one failed:")
        for a, b, why in unordered:
            print(f"    {sh(a):<6} vs {sh(b):<6}  {why}")
            for r_ in [r for r in adm[a] if r in adm[b]]:
                ma = byname[a]["nmult"] / era_cell[a][r_]
                mb = byname[b]["nmult"] / era_cell[b][r_]
                print(f"        on {sh(r_):<5}: {sh(a)} {ma:.3f} vs "
                      f"{sh(b)} {mb:.3f}  -> "
                      f"{sh(a) if ma > mb else sh(b)} above")

    # ---------------------------------------------- the top four, by name
    print("\n  THE TOP FOUR OF THE PUBLISHED TABLE, WHICH IS THE CELL AN "
          "OPERATIONAL DECISION IS READ OUT OF:")
    top = [r["sym"] for r in sorted(rows, key=lambda r: -(
        r["nmult"] if np.isfinite(r["nmult"]) else -1))][:TOP_N]
    print(f"    {', '.join(sh(s) + ' (' + byname[s]['sealed'] + ')' for s in top)}")
    top_bad = [(a, b, w) for a, b, w in unordered if a in top and b in top]
    top_miss = [s for s in top if not np.isfinite(byname[s]["m1"])]
    top_pairs = [(a, b) for i, a in enumerate(top) for b in top[i + 1:]]
    print(f"    pairs among them: {len(top_pairs)};  "
          f"UNORDERED under Rule 1: {len(top_bad)};  "
          f"rows with no era factor at all: {len(top_miss)}"
          f"{' (' + ', '.join(sh(s) for s in top_miss) + ')' if top_miss else ''}")

    # ------------------------------------------------------------ part (5)
    print("\n" + LINE)
    print("(5) THE COMMITTED DECISION. THREE CONDITIONS, ALL FIXED BEFORE "
          "ANY NUMBER EXISTED.")
    print(LINE)
    c1 = all(np.isfinite(byname[s]["m1"]) for s in top)
    c2 = len(top_bad) == 0
    o1t = [s for s in o1 if s in top]
    o2t = [s for s in o2 if s in top]
    c3 = (o1t == o2t) and len(o1t) == len(top)
    print(f"\n  1. every top-four row has a computable era factor under "
          f"Rule 1            : {'PASS' if c1 else 'FAIL'}")
    print(f"  2. unanimity leaves the top four fully ordered                "
          f"          : {'PASS' if c2 else 'FAIL'}")
    print(f"  3. Rule 2's order of the top four is identical to Rule 1's    "
          f"          : {'PASS' if c3 else 'FAIL'}")
    print(f"       Rule 1 top four : "
          f"{' > '.join(sh(s) for s in o1t) if o1t else '(none)'}")
    print(f"       Rule 2 top four : "
          f"{' > '.join(sh(s) for s in o2t) if o2t else '(none)'}")
    verdict = "(a)" if (c1 and c2 and c3) else "(b)"
    print(f"\n  VERDICT: the round reports {verdict}.")
    if verdict == "(a)":
        print("  A PRINCIPLED REFERENCE RULE IS AVAILABLE ON THIS DISK and "
              "the ordering below is the one the")
        print(f"  desk should quote: "
              f"{' > '.join(sh(s) for s in o1)}")
    else:
        print("  NO PRINCIPLED REFERENCE RULE RESOLVES THE TOP FOUR ON THIS "
              "DISK. The rows below are published")
        print("  UNORDERED and the desk stops quoting an order among them.")
        for a, b, why in top_bad:
            print(f"    UNORDERED: {sh(a)} vs {sh(b)}   ({why})")
        for s in top_miss:
            print(f"    UNORDERED: {sh(s)} against everything - no "
                  f"admissible reference exists for its window")

    print("\n  WHAT IS STILL ORDERED, AND IT IS MOST OF THE TABLE:")
    stable = [s for s in o1 if s not in [x for p in top_bad for x in p[:2]]
              and s not in top_miss]
    print(f"    {' > '.join(sh(s) for s in stable)}")
    print(f"    {len(resolved)} of {npairs} pairs are RESOLVED - unanimous "
          f"across every reference the rule admits.")

    # ------------------------------------------------------------ verdict
    print("\n" + LINE)
    print("WHAT THIS ROUND ESTABLISHES")
    print(LINE)
    print(f"\n  1. THE RULE PREDATES THE ANSWER, and that is checkable: "
          f"commit {PREREG_COMMIT[:12]} carries")
    print("     every threshold used above and was made before this file "
          "existed.")
    print(f"\n  2. R502's median-of-six had a construction defect visible "
          f"from the windows alone: it divided")
    print(f"     six references by six different denominators. "
          f"{sum(a1_ok.values())} of {len(donors)} references can carry a "
          f"pooled-calendar")
    print("     denominator at all; the rest were excluded before any era "
          "factor was read.")
    print(f"\n  3. THE ANSWER IS {verdict}. "
          f"{len(resolved)} of {npairs} pairwise orderings are RESOLVED; "
          f"{len(unordered)} are UNORDERED,")
    print(f"     of which {len(top_bad)} sit in the top four.")
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
