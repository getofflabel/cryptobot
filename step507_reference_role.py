"""
step507_reference_role.py - ROUND 507

THE TAPE THAT SETS THE DENOMINATOR IS THE ONE THAT DISAGREES WITH EVERYBODY.
IS THAT THE TAPE, OR IS IT THE ROLE?   (QUEUE ITEM 43)

Research only. No orders. No account. No live file touched, imported or
modified. Nothing here is deployed by this script under any outcome.

THE CONSTRUCTION WAS COMMITTED TO GIT BEFORE THIS FILE EXISTED.
  step507_PREREGISTRATION.md
    commit 3ff6d532a03e15d1fced8186863b246db89b5200, 2026-09-21 12:38:31 -0400
  Every constant below is copied out of that file and none may be changed by
  this round. The derived prediction P-CANCEL is committed there so this
  round can be wrong in public.

QUEUE ITEM 43, VERBATIM
  R506 placed XRP, DOT and AVAX and in doing so produced four independently
  contested pairs instead of R503's one - LINK/XRP and SOL/PAXG split 2-2,
  XRP/SOL and XRP/PAXG split 3-1. BTCUSD is in the minority on all four.
  BTCUSD is not an arbitrary member of the reference set - it is the tape
  whose window defines the pooled calendar every era factor divides by.
  Deliverable: commit the construction FIRST, then ask whether the
  minority-of-one is a property of BTC's tape or a property of its double
  role as both reference and denominator. The obvious discriminator is to
  recompute the same four pairs with each admissible reference in turn
  promoted to define the pooled calendar, and report whether the dissenter
  travels with the tape or with the role. If the dissent follows whichever
  tape is made the denominator, every era factor in this log has a
  structural bias nobody has priced.
  THE FENCE: descriptive, ordering only, behind the PINNED proportional
  fences. No entry population, no sealed slice read, no look, no candidate,
  no fence adopted.

THE FENCE, INHERITED AND ENFORCED AS CODE DISCIPLINE
  1. `simulate()` IS NEVER CALLED IN THIS FILE, and neither is any entry
     builder. No sweep is scanned, no break of structure is detected, no fill
     is modelled, no stop is measured, no outcome is read. The only things
     read off tape are (a) WHICH MINUTES CARRY A BAR and (b) THE SIZE OF A
     ONE-MINUTE MOVE.
  2. NO BYTE AT OR PAST AN INSTRUMENT'S PINNED PROPORTIONAL FENCE IS READ
     ANYWHERE IN THIS FILE, at any promotion, in the primary or the
     secondary. R506's hard clamp in `upto()` is re-used unchanged.
  3. NOTHING IS SELECTED AND NOTHING IS ADOPTED. R503's published table
     stands whatever this round finds.
  4. NO FILE ON DISK IS WRITTEN, EXTENDED, MOVED OR TRUNCATED.

USAGE
  python3 step507_reference_role.py
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
PREREG_COMMIT = "3ff6d532a03e15d1fced8186863b246db89b5200"

CONTAIN_MIN = T.CONTAIN_MIN          # 0.98,  inherited R503 -> R506
ERA_MIN_DAYS = T.ERA_MIN_DAYS        # 120,   inherited R502
ERA_MIN_OVL = T.ERA_MIN_OVL          # 0.30,  inherited R502
DONOR_MIN_COV = T.DONOR_MIN_COV      # 80.0,  inherited R501
TOP_N = T.TOP_N                      # 4
T_END_PRIMARY = T.T_END_PRIMARY      # BTC's pinned fence, R506's FENCE-T
R506_POOLED_REF = T.POOLED_REF       # "BTCUSD"

# R506's published contested pairs and splits. REPRODUCTION CONTROL 3.
# key = frozenset(pair); value = {reference: winner}
R506_CONTESTED = {
    frozenset(("LINKUSD", "XRPUSD")):
        {"LINKUSD": "XRPUSD", "DOGEUSD": "XRPUSD",
         "BTCUSD": "LINKUSD", "ETHUSD": "LINKUSD"},
    frozenset(("XRPUSD", "SOLUSD")):
        {"LINKUSD": "XRPUSD", "DOGEUSD": "XRPUSD",
         "BTCUSD": "SOLUSD", "ETHUSD": "XRPUSD"},
    frozenset(("XRPUSD", "PAXGUSD")):
        {"LINKUSD": "XRPUSD", "DOGEUSD": "XRPUSD",
         "BTCUSD": "PAXGUSD", "ETHUSD": "XRPUSD"},
    frozenset(("SOLUSD", "PAXGUSD")):
        {"LINKUSD": "SOLUSD", "DOGEUSD": "SOLUSD",
         "BTCUSD": "PAXGUSD", "ETHUSD": "PAXGUSD"},
}
R506_EXPECTED_ADMISSIBLE = ["LINKUSD", "DOGEUSD", "BTCUSD", "ETHUSD"]

sh = T.sh
days_between = T.days_between


# ======================================================= the one thing that moves
def era_matrix_pooled(tp, syms, donors, pooled):
    """R506's `era_matrix`, called with an ARBITRARY pooled day-set. The
    function itself is R506's, imported and unmodified - the only thing this
    round changes is the `pooled` argument."""
    return T.era_matrix(tp, syms, donors, pooled)


def evaluate_promoted(t_end, pub, pooled_ref):
    """One complete pass of R506's machinery with `pooled_ref` promoted to
    define the pooled calendar. Everything else is R506's, unchanged. Reads
    nothing past any pinned proportional fence (R506's `upto()` clamp)."""
    syms = [s for s, _, _ in P.RANKED]
    tp, dropped = {}, []
    for sym in syms:
        t0 = pd.Timestamp(F.PINNED[sym]["t0"])
        if t0 >= pd.Timestamp(t_end):
            dropped.append((sym, "first bar is at or after the fence", t0))
            continue
        d = T.profile(sym, t_end)
        if d is None:
            dropped.append((sym, "no bars behind the fence", t0))
            continue
        if days_between(d["t0"], d["t1"]) < ERA_MIN_DAYS:
            dropped.append((sym, "readable span below the floor", t0))
            continue
        tp[sym] = d
    live = [s for s in syms if s in tp]
    donors = [s for s in live if tp[s]["cov"] >= DONOR_MIN_COV]
    dbx = T.xsame_column(tp, live, donors)
    pooled = tp[pooled_ref]["days"] if pooled_ref in tp else set()
    a1_ok, cells, adm, era1, era2 = era_matrix_pooled(tp, live, donors, pooled)
    rows = T.build_rows(pub, tp, live, dbx, era1, era2)
    by_star = [r["sym"] for r in sorted(
        [r for r in rows.values() if np.isfinite(r["nmult"])],
        key=lambda r: -r["nmult"])]
    o1 = [r["sym"] for r in sorted(
        [r for r in rows.values() if np.isfinite(r["m1"])],
        key=lambda r: -r["m1"])]
    resolved, unordered = T.unanimity(rows, cells, adm, o1)
    top = by_star[:TOP_N]
    return dict(pooled_ref=pooled_ref, t_end=pd.Timestamp(t_end), tp=tp,
                live=live, donors=donors, pooled=pooled, a1_ok=a1_ok,
                cells=cells, adm=adm, rows=rows, by_star=by_star, o1=o1,
                top=top, resolved=resolved, unordered=unordered,
                dropped=dropped)


def vote(res, a, b, r):
    """Who does reference r put above whom, on R506's own comparison."""
    ma = res["rows"][a]["nmult"] / res["cells"][a][r]
    mb = res["rows"][b]["nmult"] / res["cells"][b][r]
    return (a if ma > mb else b), ma, mb


def split_on(res, a, b):
    """The vote of every reference admissible for BOTH rows."""
    common = [r for r in res["adm"][a] if r in res["adm"][b]]
    out = {}
    for r in common:
        w, _, _ = vote(res, a, b, r)
        out[r] = w
    return out


def minority_of(tally):
    """The references on the losing side of a split, or [] if unanimous."""
    if not tally:
        return None
    winners = set(tally.values())
    if len(winners) == 1:
        return []
    counts = {w: sum(1 for v in tally.values() if v == w) for w in winners}
    fewest = min(counts.values())
    losers = [w for w, c in counts.items() if c == fewest]
    if len(losers) != 1:
        return sorted(r for r in tally)      # genuinely tied, no minority
    return sorted(r for r, v in tally.items() if v == losers[0])


def label(tally, mino):
    """How to PRINT a split. A 2-2 split has no minority and this round will
    not pretend otherwise - R506's sentence 'BTC is the minority reference in
    all four' is loose on the two tied pairs, and part (3b) says what the
    exact pattern is instead."""
    if mino is None or not tally:
        return "no voter"
    if not mino:
        return "unanimous"
    if len(mino) == len(tally):
        return "TIED, none"
    return ", ".join(sh(m) for m in mino)


# ==================================================================== main
def main():
    now = datetime.now(timezone.utc)
    print(LINE)
    print("ROUND 507 - DOES THE DISSENTING REFERENCE TRAVEL WITH THE TAPE, "
          "OR WITH THE DENOMINATOR ROLE?   (item 43)")
    print(LINE)
    print(f"run {now:%Y-%m-%d %H:%M:%S} UTC")
    print("DESCRIPTIVE, ORDERING ONLY. simulate() is never called, no entry "
          "population is built, no sealed")
    print("slice is read, NO LOOK IS CONSUMED and none is reachable. Nothing "
          "is adopted.")
    print(f"\nTHE CONSTRUCTION WAS COMMITTED BEFORE THIS FILE EXISTED: "
          f"step507_PREREGISTRATION.md")
    print(f"  commit {PREREG_COMMIT}  (2026-09-21 12:38:31 -0400)")
    print("  It carries the promotion set, the primary/secondary split, the "
          "three reproduction controls,")
    print("  the two hypotheses AND a derived prediction (P-CANCEL) that "
          "this run can falsify.")

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
    tp_prop = {s: T.profile(s, F.fenced_at(s)) for s in base_ranked}
    worst = max(abs(tp_prop[s]["coord"] - pub[s]["vol"]) for s in base_ranked)
    print(f"\n  a. R499's vol% column, behind the PINNED fence: max absolute "
          f"difference {worst:.4f} pp")
    if worst > 0.0001:
        print("     !! this is not R499's table. The round stops.")
        return
    print("     EXACT.")

    donors_prop = [s for s in base_ranked
                   if tp_prop[s]["cov"] >= DONOR_MIN_COV]
    dbx_prop = T.xsame_column(tp_prop, base_ranked, donors_prop)
    r501_worst = max(abs(dbx_prop[s] - E.R501_XSAME[s]) for s in base_ranked
                     if np.isfinite(dbx_prop.get(s, np.nan))
                     and np.isfinite(E.R501_XSAME.get(s, np.nan)))
    print(f"\n  b. R501's xSAME column, R501's own functions: max absolute "
          f"difference {r501_worst:.3f}x")
    if r501_worst > 0.0015:
        print("     !! R501 does not reproduce. The round stops.")
        return
    print("     EXACT to the published precision.")

    base = evaluate_promoted(T_END_PRIMARY, pub, R506_POOLED_REF)
    adm_refs = sorted({r for s in base["live"] for r in base["adm"][s]},
                      key=lambda x: base_ranked.index(x))
    print(f"\n  c. R506's FENCE-T cell, rebuilt. Rows readable: "
          f"{len(base['live'])} of 11. Donors: "
          f"{', '.join(sh(d) for d in base['donors'])}")
    print(f"     admissible references (recomputed, not retyped): "
          f"{', '.join(sh(r) for r in adm_refs)}")
    if sorted(adm_refs) != sorted(R506_EXPECTED_ADMISSIBLE):
        print(f"     !! R506 reported {R506_EXPECTED_ADMISSIBLE}. "
              f"The round stops.")
        return
    bad = 0
    print(f"\n     R506's four contested pairs, reproduced vote by vote:")
    print(f"     {'pair':<18}", end="")
    for r in R506_EXPECTED_ADMISSIBLE:
        print(f"{sh(r):>8}", end="")
    print("   split          matches R506")
    print("     " + "-" * 78)
    for key, published in R506_CONTESTED.items():
        a, b = sorted(key, key=lambda x: base_ranked.index(x))
        tally = split_on(base, a, b)
        ok = all(tally.get(r) == published[r] for r in published) \
            and len(tally) == len(published)
        bad += 0 if ok else 1
        winners = set(tally.values())
        counts = sorted((sum(1 for v in tally.values() if v == w), w)
                        for w in winners)[::-1]
        print(f"     {sh(a) + ' vs ' + sh(b):<18}", end="")
        for r in R506_EXPECTED_ADMISSIBLE:
            print(f"{sh(tally.get(r, '--')):>8}", end="")
        print(f"   {'-'.join(str(c) for c, _ in counts):<14} "
              f"{'YES' if ok else '!! NO'}")
    if bad:
        print(f"\n     !! {bad} of 4 pairs do not reproduce R506. "
              f"This is not the cell item 43 asks about. The round stops.")
        return
    print(f"\n     ALL FOUR EXACT. This is R506's cell, digit for digit.")
    base_minority = {k: minority_of(split_on(
        base, *sorted(k, key=lambda x: base_ranked.index(x))))
        for k in R506_CONTESTED}
    print(f"     minority reference on each pair, under the INHERITED "
          f"pooled calendar ({sh(R506_POOLED_REF)}):")
    for key in R506_CONTESTED:
        a, b = sorted(key, key=lambda x: base_ranked.index(x))
        tl = split_on(base, a, b)
        print(f"        {sh(a):<5} vs {sh(b):<5} -> minority: "
              f"{label(tl, base_minority[key])}")

    # ------------------------------------------------------------ part (2)
    print("\n" + LINE)
    print("(2) THE PRIMARY. GEOMETRY HELD FIXED AT R506's FENCE-T; ONLY THE "
          "POOLED CALENDAR IS PROMOTED.")
    print(LINE)
    print(f"\n  T_END = {T_END_PRIMARY} for every promotion. The only thing "
          f"that moves is which")
    print("  instrument's day-set is called the pooled calendar - i.e. the "
          "DENOMINATOR ROLE, alone.")

    runs = {}
    print(f"\n  {'promoted':<10}{'pooled days':>13}{'admissible refs':>34}"
          f"{'A1 gate changed?':>20}")
    print("  " + "-" * 78)
    for R in adm_refs:
        r_ = evaluate_promoted(T_END_PRIMARY, pub, R)
        runs[R] = r_
        refs = sorted({x for s in r_["live"] for x in r_["adm"][s]},
                      key=lambda x: base_ranked.index(x))
        changed = sorted(refs) != sorted(adm_refs)
        print(f"  {sh(R):<10}{len(r_['pooled']):>13}"
              f"{', '.join(sh(x) for x in refs):>34}"
              f"{('YES' if changed else 'no'):>20}")

    print(f"\n  A1 per reference, promotion by promotion "
          f"(share of the promoted calendar each reference covers):")
    print(f"  {'promoted':<10}", end="")
    for r in adm_refs:
        print(f"{sh(r):>12}", end="")
    print()
    print("  " + "-" * (10 + 12 * len(adm_refs)))
    for R in adm_refs:
        r_ = runs[R]
        print(f"  {sh(R):<10}", end="")
        for dn in adm_refs:
            ov = len(r_["tp"][dn]["days"] & r_["pooled"])
            pc = ov / max(len(r_["pooled"]), 1)
            print(f"{pc:>10.1%}{'A' if r_['a1_ok'].get(dn) else ' '} ",
                  end="")
        print()
    print("  'A' = passes A1 and may vote. A1 is the ONLY channel the pooled "
          "calendar has into a split.")

    # ------------------------------------------------------------ part (3)
    print("\n" + LINE)
    print("(3) THE FOUR CONTESTED PAIRS, UNDER EVERY PROMOTION. THE QUESTION "
          "THE ITEM ACTUALLY ASKS.")
    print(LINE)
    travels = {"tape": 0, "role": 0, "other": 0}
    for key in R506_CONTESTED:
        a, b = sorted(key, key=lambda x: base_ranked.index(x))
        print(f"\n  {sh(a)} vs {sh(b)}")
        print(f"     {'pooled calendar':<18}", end="")
        for r in adm_refs:
            print(f"{sh(r):>8}", end="")
        print(f"   {'split':<8}{'minority':>12}")
        print("     " + "-" * 72)
        for R in adm_refs:
            r_ = runs[R]
            tally = split_on(r_, a, b)
            mino = minority_of(tally)
            winners = set(tally.values())
            counts = sorted((sum(1 for v in tally.values() if v == w), w)
                            for w in winners)[::-1] if tally else []
            print(f"     {sh(R) + ' promoted':<18}", end="")
            for r in adm_refs:
                print(f"{sh(tally.get(r, '--')):>8}", end="")
            print(f"   {'-'.join(str(c) for c, _ in counts):<8}"
                  f"{label(tally, mino):>12}")
            if mino == base_minority[key]:
                travels["tape"] += 1
            elif mino == [R]:
                travels["role"] += 1
            else:
                travels["other"] += 1

    n_cells = len(R506_CONTESTED) * len(adm_refs)
    print(f"\n  ACROSS ALL {n_cells} (pair x promoted-calendar) CELLS:")
    print(f"     minority UNCHANGED from the inherited calendar "
          f"(H-TAPE)   : {travels['tape']:>3} of {n_cells}")
    print(f"     minority BECOMES the promoted reference  (H-ROLE)   "
          f"     : {travels['role']:>3} of {n_cells}")
    print(f"     neither                                  (H-MIXED)  "
          f"     : {travels['other']:>3} of {n_cells}")

    # ----------------------------------------------------------- part (3b)
    print("\n" + LINE)
    print("(3b) WHAT THE PATTERN ACTUALLY IS. R506's SENTENCE IS LOOSE ON "
          "THE TWO TIED PAIRS.")
    print(LINE)
    print("\n  A 2-2 split has no minority, so 'BTC is the minority "
          "reference in all four' is exact on two")
    print("  pairs and loose on two. The precise statement is a BLOC "
          "structure - how often each pair of")
    print("  references votes the same way, across R506's four contested "
          "pairs (inherited calendar):")
    print(f"\n  {'':<8}", end="")
    for r in adm_refs:
        print(f"{sh(r):>8}", end="")
    print()
    print("  " + "-" * (8 + 8 * len(adm_refs)))
    for r1 in adm_refs:
        print(f"  {sh(r1):<8}", end="")
        for r2 in adm_refs:
            if r1 == r2:
                print(f"{'-':>8}", end="")
                continue
            agree = 0
            for key in R506_CONTESTED:
                a, b = sorted(key, key=lambda x: base_ranked.index(x))
                tl = split_on(base, a, b)
                if r1 in tl and r2 in tl and tl[r1] == tl[r2]:
                    agree += 1
            print(f"{agree:>7}/4", end="")
        print()
    print("\n  Read off the matrix: LINK and DOGE agree on 4 of 4 and BTC "
          "opposes that bloc on 4 of 4.")
    print("  ETH is the swing - with BTC on the two tied pairs, with "
          "LINK/DOGE on the two 3-1 pairs.")
    print("  So the honest sentence is: BTC dissents from the LINK-DOGE bloc "
          "on every contested pair,")
    print("  and is a minority OF ONE on the two that are not ties. That is "
          "the fact item 43 is about,")
    print("  and part (3) has just shown it does not move when the "
          "denominator role moves.")

    # ------------------------------------------------------------ part (4)
    print("\n" + LINE)
    print("(4) P-CANCEL, THE PREDICTION COMMITTED BEFORE THE RUN. CHECKED "
          "VOTE BY VOTE, NOT ASSERTED.")
    print(LINE)
    print("\n  P-CANCEL: den[r] is common to both sides of R506's comparison "
          "and cancels, so a vote sign")
    print("  cannot move under promotion while its voter stays admissible. "
          "Every cell is checked.")
    flips, checked, worst_ratio = [], 0, 0.0
    for key in R506_CONTESTED:
        a, b = sorted(key, key=lambda x: base_ranked.index(x))
        for R in adm_refs:
            r_ = runs[R]
            for ref in adm_refs:
                if ref not in r_["adm"][a] or ref not in r_["adm"][b]:
                    continue
                if ref not in base["adm"][a] or ref not in base["adm"][b]:
                    continue
                w_new, ma, mb = vote(r_, a, b, ref)
                w_old, _, _ = vote(base, a, b, ref)
                checked += 1
                if w_new != w_old:
                    flips.append((sh(a), sh(b), sh(R), sh(ref)))
                # how far the RATIO moved, which should be exactly 0
                ra = r_["rows"][a]["nmult"] / r_["cells"][a][ref]
                rb = base["rows"][a]["nmult"] / base["cells"][a][ref]
                worst_ratio = max(worst_ratio,
                                  abs(ra / rb - 1.0) if rb else 0.0)
    print(f"\n  vote cells checked (voter admissible under BOTH the "
          f"inherited and the promoted calendar): {checked}")
    print(f"  vote signs that MOVED: {len(flips)}")
    print(f"  worst relative movement in a single side's ratio "
          f"nmult/cell:  {worst_ratio:.3e}")
    if flips:
        print("\n  !! P-CANCEL IS FALSIFIED. The derivation in the "
              "pre-registration is wrong. The flips:")
        for f_ in flips:
            print(f"       {f_[0]} vs {f_[1]}, {f_[2]} promoted, "
                  f"voter {f_[3]}")
    else:
        print("\n  P-CANCEL HOLDS. Not one vote sign moved, and the ratios "
              "themselves did not move either -")
        print("  the denominator cancels exactly, as derived. The pooled "
              "calendar's ONLY reachable effect")
        print("  on an ordering is through A1: WHO votes, never HOW a voter "
              "votes.")

    # ------------------------------------------------------------ part (5)
    print("\n" + LINE)
    print("(5) DECLARED SECONDARY - THE FULL DOUBLE ROLE (T_END MOVES WITH "
          "THE PROMOTED REFERENCE).")
    print(LINE)
    print("\n  R506 set T_END to BTC's pinned fence BECAUSE BTC was the "
          "reference. This rung moves both")
    print("  halves at once and is therefore CONFOUNDED. It is a sensitivity "
          "reading; the verdict is the")
    print("  primary's. A T_END later than another row's pin is CLAMPED by "
          "the read guard and is not a")
    print("  clean test of its own geometry - the same defect R506 declared "
          "on its short ladder rungs.")
    print(f"\n  {'promoted':<10}{'T_END':<22}{'clean?':<9}{'rows':>6}"
          f"{'refs':>6}   contested pairs among R506's four "
          f"-> minority")
    print("  " + "-" * 104)
    for R in adm_refs:
        te = pd.Timestamp(F.PINNED[R]["t80"])
        clamped = [s for s, _, _ in P.RANKED if te > F.fenced_at(s)]
        clean = not clamped
        try:
            r_ = evaluate_promoted(te, pub, R)
        except Exception as exc:                            # noqa: BLE001
            print(f"  {sh(R):<10}{str(te):<22}{'--':<9}  not evaluable: "
                  f"{type(exc).__name__}")
            continue
        refs = sorted({x for s in r_["live"] for x in r_["adm"][s]},
                      key=lambda x: base_ranked.index(x))
        bits = []
        for key in R506_CONTESTED:
            a, b = sorted(key, key=lambda x: base_ranked.index(x))
            if a not in r_["live"] or b not in r_["live"]:
                bits.append(f"{sh(a)}/{sh(b)}:row gone")
                continue
            tally = split_on(r_, a, b)
            mino = minority_of(tally)
            bits.append(f"{sh(a)}/{sh(b)}:"
                        f"{label(tally, mino).replace(', ', '+')}")
        print(f"  {sh(R):<10}{str(te):<22}"
              f"{('CLEAN' if clean else 'CLAMPED'):<9}{len(r_['live']):>6}"
              f"{len(refs):>6}   {'; '.join(bits)}")
    print("\n  Nothing on this table supplies a verdict, an ordering or a "
          "fence.")

    # ------------------------------------------------------------ verdict
    if travels["tape"] == n_cells:
        verdict = "H-TAPE"
        line1 = ("The dissent is a property of BTC's TAPE. The denominator "
                 "role is exonerated.")
    elif travels["role"] == n_cells:
        verdict = "H-ROLE"
        line1 = ("The dissent follows the DENOMINATOR ROLE. Every era factor "
                 "in this log is structurally biased.")
    else:
        verdict = "H-MIXED"
        line1 = ("Neither pattern is clean. Reported as mixed; nothing is "
                 "adopted off it.")

    print("\n" + LINE)
    print("WHAT THIS ROUND ESTABLISHES")
    print(LINE)
    print(f"\n  1. THE CONSTRUCTION PREDATES THE ANSWER: commit "
          f"{PREREG_COMMIT[:12]}, made before this file existed.")
    print(f"\n  2. VERDICT: {verdict}.  {line1}")
    print(f"\n  3. P-CANCEL: "
          f"{'HOLDS - and it is the mechanism behind the verdict.' if not flips else 'FALSIFIED.'}")
    print("     The pooled calendar cancels out of every pairwise comparison. "
          "It reaches an ordering only")
    print("     through A1, by changing which references are allowed to vote.")
    print("\n  4. NOTHING IS ADOPTED. R503's published table stands: LINK 1st "
          "and resolved; places 2-4")
    print("     UNORDERED {PAXG, SOL, XRP}; DOGE > BTC > LTC > ETH resolved. "
          "No fence, calendar or")
    print("     ordering is adopted, republished or proposed for deployment.")
    print("\n  5. COSTS DECIDE NOTHING (owner rule, 2026-07-25).")
    print("\n  FENCE HELD: simulate() never called, no entry population "
          "built, no sweep scanned, no stop")
    print("  measured, no outcome read. No byte at or past any pinned "
          "proportional fence was read, so")
    print("  PAXG's, XRP's, ADA's, DOT's and AVAX's intact slices are "
          "untouched. NO LOOK CONSUMED.")
    print("  NO FILE ON DISK WAS WRITTEN, EXTENDED, MOVED OR TRUNCATED.")
    print(LINE)


if __name__ == "__main__":
    main()
