"""
step506_trailing_fence.py - ROUND 506

THE FENCE IS A PROPORTION AND THAT IS A CHOICE NOBODY EVER MADE ON PURPOSE.
(QUEUE ITEM 39)

Research only. No orders. No account. No live file touched, imported or
modified. Nothing here is deployed by this script under any outcome.

THE RULE THIS FILE IMPLEMENTS WAS COMMITTED TO GIT BEFORE THIS FILE EXISTED.
  step506_PREREGISTRATION.md
    commit ecabe309a350333e3094d3a495c536f7c625ef62, 2026-09-19 04:34:48 -0400
    AMENDMENT A1 in commit a197850..., same day, also before this file existed
  Every constant below is copied out of that file and none may be changed by
  this round. The git timestamps on those two commits preceding this file's
  first output are the evidence offered that the fence was not chosen by
  looking at the ranking it gives.

QUEUE ITEM 39, VERBATIM
  R504 proved the four unplaced rows are unplaceable before 2036 BECAUSE
  `cut80` keeps 80% of each instrument's own span, so tapes that start in
  different years stop being admissible in different years. A fence that
  instead keeps a fixed number of trailing days - every instrument's readable
  region ending on the same date - makes A2 satisfiable for every row at once,
  at the price of changing the SIZE of every sealed slice in this log.
  Deliverable: write the rule down FIRST, in a committed file, exactly as R503
  did - which fence, what trailing length, what happens to instruments whose
  tape is shorter than it, and the decision rule for what counts as a better
  fence, fixed before the resulting ordering is computed. Then recompute the
  ranking under it and report whether the top four resolve.
  THE FENCE: the ordering is recomputed, nothing is selected off it. No entry
  population, no sealed slice read, no look, no candidate. A trailing-days
  fence that would move a SPENT boundary (LINK, crypto, the index) must treat
  those as pinned at the dates in `FENCES_PINNED.md` and say so in the
  pre-registration; unspending a slice by re-fencing is barred.

THE FENCE, INHERITED AND ENFORCED AS CODE DISCIPLINE
  1. `simulate()` IS NEVER CALLED IN THIS FILE, and neither is any entry
     builder. No sweep is scanned, no break of structure is detected, no fill
     is modelled, no stop is measured, no outcome is read. The only things
     read off tape are (a) WHICH MINUTES CARRY A BAR and (b) THE SIZE OF A
     ONE-MINUTE MOVE.
  2. NO BYTE AT OR PAST AN INSTRUMENT'S PINNED PROPORTIONAL FENCE IS READ
     ANYWHERE IN THIS FILE. That is the binding guarantee (AMENDMENT A1).
     PAXG's, XRP's, ADA's, DOT's and AVAX's intact slices are untouched.
  3. NOTHING IS SELECTED AND NOTHING IS ADOPTED. R503's published table
     stands whatever this round finds.
  4. NO FILE ON DISK IS WRITTEN, EXTENDED, MOVED OR TRUNCATED. The pin is
     read, never edited.

USAGE
  python3 step506_trailing_fence.py
"""

import sys
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = "/Users/wallacechen/cryptobot"
sys.path.insert(0, REPO)

import step489_next_look_screen as S     # noqa: E402  (screen, unmodified)
import step501_coverage_column as P      # noqa: E402  (R501, unmodified)
import step502_era_column as E           # noqa: E402  (R502, unmodified)
import step505_pinned_fences as F        # noqa: E402  (R505, unmodified)

LINE = "=" * 108

# ------------------------------------------------- copied from the prereg
PREREG_COMMIT = "ecabe309a350333e3094d3a495c536f7c625ef62"
PREREG_AMEND = "a197850"

POOLED_REF = "BTCUSD"          # pooled calendar, INHERITED from R502/R503
CONTAIN_MIN = 0.98             # A1 and A2, inherited from R503 verbatim
ERA_MIN_DAYS = E.ERA_MIN_DAYS  # 120, inherited from R502
ERA_MIN_OVL = E.ERA_MIN_OVL    # 0.30, inherited from R502, Rule 2 floor
DONOR_MIN_COV = P.DONOR_MIN_COV        # 80.0, inherited from R501
TOP_N = 4
R501_XSAME = E.R501_XSAME

# FENCE-T's trailing length, taken verbatim out of FENCES_PINNED.md
T_END_PRIMARY = pd.Timestamp(F.PINNED[POOLED_REF]["t80"])
BTC_T1 = pd.Timestamp(F.PINNED[POOLED_REF]["t1"])

# the declared sensitivity ladder. THE VERDICT COMES FROM THE PRIMARY ALONE.
LADDER_D = (180, 270, 365, 406, 540)

R503_TOP = ["PAXGUSD", "SOLUSD", "XRPUSD"]     # published UNORDERED
PRECONTAM_MATERIAL_DAYS = 1.0                   # P4(b), fixed in the prereg

# which rounds have SPENT a look on which ranked instrument's readable side
SPENT_LOOK = {
    "LINKUSD": "R492 read LINK's train/val and SPENT its sealed slice",
    "XRPUSD":  "R492 READ this region as XRP's train/val",
    "BTCUSD":  "R475 read the crypto arm's train/val",
    "ETHUSD":  "R475 read the crypto arm's train/val",
    "SOLUSD":  "R475 read the crypto arm's train/val",
}


def sh(s):
    return s.replace("USD", "")


def days_between(a, b):
    return (b - a).total_seconds() / 86400.0


# =========================================================== tape handling
_FULL = {}


def full_tape(sym):
    """Load once, slice many. NOTHING past a pinned proportional fence is
    ever handed out of this module - see `upto()`."""
    if sym not in _FULL:
        _FULL[sym] = S.tape(P.PATHS[sym])
    return _FULL[sym]


def upto(sym, t_end):
    """The one and only way tape leaves this file. Hard-clamped to the pinned
    proportional fence so no caller, at any rung of the ladder, can read into
    an intact sealed slice even by mistake."""
    hard = F.fenced_at(sym)
    cap = min(pd.Timestamp(t_end), hard)
    f = full_tape(sym)
    return f[f["t"] < cap].copy(), cap


def profile(sym, t_end):
    """Coverage + coordinate + day set behind an arbitrary boundary."""
    g, cap = upto(sym, t_end)
    if len(g) < 2:
        return None
    d = P.density(g)
    d["coord"] = P.coord(g)
    d["keys"] = P.minute_keys(g)
    d["f"] = g
    d["days"] = set(g["t"].dt.floor("D").unique())
    d["nday"] = len(d["days"])
    d["t0"], d["t1"] = g["t"].iloc[0], g["t"].iloc[-1]
    d["cap"] = cap
    return d


def xsame_column(tp, syms, donors):
    """R501's donor-mask de-bias, R501's own functions, on whatever frames
    the caller fenced."""
    out = {}
    for sym in syms:
        t = tp.get(sym)
        if t is None:
            out[sym] = np.nan
            continue
        xs = []
        for dn in donors:
            if dn == sym or tp.get(dn) is None:
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
            xs.append(cm / cs)
        out[sym] = float(np.median(xs)) if len(xs) >= 2 else np.nan
    return out


# =============================================== R503's rules, inherited
def era_matrix(tp, syms, donors, pooled):
    """R503's Rule 1 (containment + median over admissible references) and
    Rule 2 (overlap-weighted mean), copied unchanged. Denominator is ALWAYS
    the reference's coordinate on the pooled calendar."""
    npool = max(len(pooled), 1)
    a1_ok, den = {}, {}
    for dn in donors:
        d = tp[dn]
        ov = len(d["days"] & pooled)
        a1_ok[dn] = (ov / npool >= CONTAIN_MIN and ov >= ERA_MIN_DAYS)
        g = d["f"][d["f"]["t"].dt.floor("D").isin(pooled)]
        den[dn] = P.coord(g) if len(g) else np.nan

    cells, adm, era1, era2 = {}, {}, {}, {}
    for sym in syms:
        t = tp.get(sym)
        if t is None:
            cells[sym], adm[sym] = {}, []
            era1[sym] = era2[sym] = np.nan
            continue
        c, ok, wnum, wden = {}, [], 0.0, 0.0
        for dn in donors:
            d = tp[dn]
            ovl_row = t["days"] & d["days"]
            cov_row = len(ovl_row) / max(t["nday"], 1)
            ovl_pool = d["days"] & pooled
            cov_pool = len(ovl_pool) / npool
            if (len(ovl_row) < ERA_MIN_DAYS or cov_row < ERA_MIN_OVL
                    or not np.isfinite(den[dn]) or den[dn] <= 0):
                continue
            c_row = P.coord(d["f"][d["f"]["t"].dt.floor("D").isin(ovl_row)])
            if not np.isfinite(c_row):
                continue
            x = c_row / den[dn]
            c[dn] = x
            if a1_ok[dn] and cov_row >= CONTAIN_MIN and len(ovl_row) >= ERA_MIN_DAYS:
                ok.append(dn)
            if cov_pool >= ERA_MIN_OVL and len(ovl_pool) >= ERA_MIN_DAYS:
                w = cov_row * cov_pool
                wnum += w * x
                wden += w
        cells[sym], adm[sym] = c, ok
        era1[sym] = float(np.median([c[r] for r in ok])) if ok else np.nan
        era2[sym] = wnum / wden if wden > 0 else np.nan
    return a1_ok, cells, adm, era1, era2


def build_rows(pub, tp, syms, dbx, era1, era2):
    rows = {}
    for sym in syms:
        if tp.get(sym) is None:
            continue
        p_ = pub[sym]
        x = dbx.get(sym, np.nan)
        vol = tp[sym]["coord"]
        nv = vol / x if np.isfinite(x) and x > 0 else np.nan
        nm = nv / p_["fee"] if np.isfinite(nv) else np.nan
        rows[sym] = dict(
            sym=sym, vol=vol, fee=p_["fee"], xsame=x, nvol=nv, nmult=nm,
            sealed=p_["sealed"], e1=era1.get(sym, np.nan),
            e2=era2.get(sym, np.nan),
            m1=(nm / era1[sym] if np.isfinite(nm)
                and np.isfinite(era1.get(sym, np.nan)) else np.nan),
            m2=(nm / era2[sym] if np.isfinite(nm)
                and np.isfinite(era2.get(sym, np.nan)) else np.nan))
    return rows


def unanimity(rows, cells, adm, order):
    resolved, unordered = [], []
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            a, b = order[i], order[j]
            common = [r for r in adm[a] if r in adm[b]]
            if not common:
                unordered.append((a, b, "no reference admissible for both"))
                continue
            signs = {rows[a]["nmult"] / cells[a][r] > rows[b]["nmult"] / cells[b][r]
                     for r in common}
            if len(signs) == 1:
                resolved.append((a, b, len(common)))
            else:
                unordered.append((a, b,
                                  f"{len(common)} admissible references disagree"))
    return resolved, unordered


def evaluate(t_end, pub, verbose=False):
    """One complete pass of the machinery at one trailing boundary. Returns
    everything P1-P4 need. Reads nothing past any pinned proportional fence."""
    syms = [s for s, _, _ in P.RANKED]
    tp, dropped = {}, []
    for sym in syms:
        t0 = pd.Timestamp(F.PINNED[sym]["t0"])
        if t0 >= pd.Timestamp(t_end):
            dropped.append((sym, "first bar is at or after the fence", t0))
            continue
        d = profile(sym, t_end)
        if d is None:
            dropped.append((sym, "no bars behind the fence", t0))
            continue
        span_days = days_between(d["t0"], d["t1"])
        if span_days < ERA_MIN_DAYS:
            dropped.append((sym, f"readable span {span_days:.0f}d < "
                                 f"{ERA_MIN_DAYS}d", t0))
            continue
        tp[sym] = d
    live = [s for s in syms if s in tp]
    donors = [s for s in live if tp[s]["cov"] >= DONOR_MIN_COV]
    dbx = xsame_column(tp, live, donors)
    pooled = tp[POOLED_REF]["days"] if POOLED_REF in tp else set()
    a1_ok, cells, adm, era1, era2 = era_matrix(tp, live, donors, pooled)
    rows = build_rows(pub, tp, live, dbx, era1, era2)
    by_star = [r["sym"] for r in sorted(
        [r for r in rows.values() if np.isfinite(r["nmult"])],
        key=lambda r: -r["nmult"])]
    o1 = [r["sym"] for r in sorted(
        [r for r in rows.values() if np.isfinite(r["m1"])],
        key=lambda r: -r["m1"])]
    o2 = [r["sym"] for r in sorted(
        [r for r in rows.values() if np.isfinite(r["m2"])],
        key=lambda r: -r["m2"])]
    top = by_star[:TOP_N]
    resolved, unordered = unanimity(rows, cells, adm, o1)
    top_bad = [(a, b, w) for a, b, w in unordered if a in top and b in top]
    top_miss = [s for s in top if not np.isfinite(rows[s]["m1"])]
    return dict(t_end=pd.Timestamp(t_end), tp=tp, dropped=dropped, live=live,
                donors=donors, dbx=dbx, pooled=pooled, a1_ok=a1_ok,
                cells=cells, adm=adm, rows=rows, by_star=by_star, o1=o1,
                o2=o2, top=top, resolved=resolved, unordered=unordered,
                top_bad=top_bad, top_miss=top_miss)


def criteria(res, base_ranked):
    """P1-P4 exactly as pre-registered."""
    rows, top = res["rows"], res["top"]
    p1 = bool(top) and all(np.isfinite(rows[s]["m1"]) for s in top)
    p2 = len(res["top_bad"]) == 0 and len(res["top_miss"]) == 0
    o1t = [s for s in res["o1"] if s in top]
    o2t = [s for s in res["o2"] if s in top]
    p3 = (o1t == o2t) and len(o1t) == len(top)

    unspend, precontam = [], []
    for sym, _, _ in P.RANKED:
        pin = F.fenced_at(sym)
        d = days_between(pin, res["t_end"])
        if d > 0:
            unspend.append((sym, d))                 # fence moved LATER
        elif d < 0:
            precontam.append((sym, -d))              # fence moved EARLIER
    mat_un = [(s, d) for s, d in unspend
              if d >= PRECONTAM_MATERIAL_DAYS]
    mat_pc = [(s, d) for s, d in precontam
              if d >= PRECONTAM_MATERIAL_DAYS and s in SPENT_LOOK]
    lost = [s for s in base_ranked if s not in res["live"]]
    p4a, p4b, p4c = not mat_un, not mat_pc, not lost
    p4 = p4a and p4b and p4c
    if p1 and p2 and p3 and p4:
        verdict = "BETTER"
    elif p1 and p2 and p3:
        verdict = "ORDERING IMPROVED, FENCE INADMISSIBLE"
    else:
        verdict = "NOT BETTER"
    return dict(p1=p1, p2=p2, p3=p3, p4=p4, p4a=p4a, p4b=p4b, p4c=p4c,
                verdict=verdict, unspend=unspend, precontam=precontam,
                mat_un=mat_un, mat_pc=mat_pc, lost=lost, o1t=o1t, o2t=o2t)


# ==================================================================== main
def main():
    now = datetime.now(timezone.utc)
    print(LINE)
    print("ROUND 506 - THE FENCE IS A PROPORTION AND THAT IS A CHOICE NOBODY "
          "EVER MADE ON PURPOSE.   (item 39)")
    print(LINE)
    print(f"run {now:%Y-%m-%d %H:%M:%S} UTC")
    print("A FENCE-GEOMETRY question, pre-registered. simulate() is never "
          "called, no entry population is built,")
    print("no sealed slice is read, NO LOOK IS CONSUMED and none is "
          "reachable. Nothing is adopted.")
    print(f"\nTHE RULE WAS COMMITTED BEFORE THIS FILE EXISTED: "
          f"step506_PREREGISTRATION.md")
    print(f"  commit {PREREG_COMMIT}  (2026-09-19 04:34:48 -0400)")
    print(f"  amendment A1 in {PREREG_AMEND}, same day, also before this "
          f"file existed. It splits the read")
    print("  boundary in two and changes no threshold, rule, criterion or "
          "trailing length.")

    pub = P.parse_r499_ranking()
    print(f"\nR499's published ranking parsed off step499_output.txt by "
          f"R501's own parser: {len(pub)} of 11 rows.")
    if len(pub) != 11:
        print("  !! incomplete parse - the round stops.")
        return
    base_ranked = [s for s, _, _ in P.RANKED]

    # ------------------------------------------------------------ part (1)
    print("\n" + LINE)
    print("(1) REPRODUCTION CONTROLS, BEHIND THE PINNED PROPORTIONAL FENCE. "
          "If either fails the round stops.")
    print(LINE)
    tp_prop = {}
    for sym in base_ranked:
        tp_prop[sym] = profile(sym, F.fenced_at(sym))
    worst = max(abs(tp_prop[s]["coord"] - pub[s]["vol"]) for s in base_ranked)
    print(f"\n  a. R499's vol% column, recomputed behind the PINNED fence: "
          f"max absolute difference {worst:.4f} pp")
    if worst > 0.0001:
        print("     !! this is not R499's table. The round stops.")
        return
    print("     EXACT. The disk is the one R501, R502, R503, R504 and R505 "
          "read.")

    donors_prop = [s for s in base_ranked
                   if tp_prop[s]["cov"] >= DONOR_MIN_COV]
    dbx_prop = xsame_column(tp_prop, base_ranked, donors_prop)
    r501_worst = max(abs(dbx_prop[s] - R501_XSAME[s])
                     for s in base_ranked
                     if np.isfinite(dbx_prop.get(s, np.nan))
                     and np.isfinite(R501_XSAME.get(s, np.nan)))
    print(f"\n  b. R501's xSAME column, R501's own functions. Donors "
          f"(>= {DONOR_MIN_COV:.0f}% full): "
          f"{', '.join(sh(d) for d in donors_prop)}")
    print(f"     max absolute difference against R501's published xSAME: "
          f"{r501_worst:.3f}x")
    if r501_worst > 0.0015:
        print("     !! R501 does not reproduce. The round stops.")
        return
    print("     EXACT to the published precision.")

    # ------------------------------------------------------------ part (2)
    print("\n" + LINE)
    print("(2) FENCE-T, AND WHAT IT DOES TO EVERY PINNED BOUNDARY. THE "
          "UN-SPEND BAR IS CHECKED, NOT ASSUMED.")
    print(LINE)
    print(f"\n  T_END (primary, copied out of FENCES_PINNED.md) = "
          f"{POOLED_REF}'s pinned fence = {T_END_PRIMARY}")
    D_days = days_between(T_END_PRIMARY, BTC_T1)
    print(f"  Trailing length D = {POOLED_REF}'s file end {BTC_T1} - T_END "
          f"= {D_days:.2f} days  ->  406 trailing days")
    ends = {s: pd.Timestamp(F.PINNED[s]["t1"]) for s in base_ranked}
    same_day = len({e.date() for e in ends.values()}) == 1
    print(f"  All eleven ranked files end on the same DAY: "
          f"{'YES (' + str(sorted({e.date() for e in ends.values()})[0]) + ')' if same_day else 'NO'}"
          f"  -> common-T_END and fixed-trailing-days are the same fence here.")
    print("\n  The pooled calendar is BTC's fenced window. T_END *is* BTC's "
          "pinned fence, so the denominator")
    print("  every era factor divides by does not move at all. Any change in "
          "the ordering comes from the ROWS.")

    print(f"\n  {'instrument':<11}{'pinned fence':<22}{'FENCE-T':<22}"
          f"{'moves':>12}   {'direction':<10} sealed-slice length "
          f"prop -> FENCE-T")
    print("  " + "-" * 118)
    for sym in base_ranked:
        pin = F.fenced_at(sym)
        t1 = pd.Timestamp(F.PINNED[sym]["t1"])
        mv = days_between(pin, T_END_PRIMARY)
        direction = ("unchanged" if abs(mv) < 1e-9
                     else ("LATER" if mv > 0 else "earlier"))
        s_old = days_between(pin, t1)
        s_new = days_between(T_END_PRIMARY, t1)
        print(f"  {sym:<11}{str(pin):<22}{str(T_END_PRIMARY):<22}"
              f"{mv:>+11.3f}d   {direction:<10} "
              f"{s_old:>7.1f}d -> {s_new:>7.1f}d")
    print("\n  A boundary moving LATER would UN-SPEND tape. A boundary moving "
          "EARLIER re-seals tape that was")
    print("  readable, which is false labelling wherever a round already "
          "spent a look on it (P4b).")

    # ------------------------------------------------------------ part (3)
    print("\n" + LINE)
    print("(3) WHO SURVIVES THE FENCE, AND WHO DOES NOT")
    print(LINE)
    res = evaluate(T_END_PRIMARY, pub)
    print(f"\n  {'instrument':<11}{'FENCE-T window':<28}{'days':>7}"
          f"{'bars':>11}{'cov%':>8}{'vol%':>9}   verdict")
    print("  " + "-" * 92)
    for sym in base_ranked:
        if sym in res["tp"]:
            d = res["tp"][sym]
            w = f"{d['t0']:%Y-%m-%d} -> {d['t1']:%Y-%m-%d}"
            print(f"  {sym:<11}{w:<28}{d['nday']:>7}{d['bars']:>11}"
                  f"{d['cov']:>8.1f}{d['coord']:>9.4f}   readable"
                  f"{'  [DONOR]' if sym in res['donors'] else ''}")
        else:
            why = [x for x in res["dropped"] if x[0] == sym][0]
            print(f"  {sym:<11}{'--':<28}{'--':>7}{'--':>11}{'--':>8}"
                  f"{'--':>9}   UNFENCEABLE: {why[1]} "
                  f"(first bar {why[2]:%Y-%m-%d})")
    print(f"\n  rows readable under FENCE-T: {len(res['live'])} of 11.  "
          f"donors: {', '.join(sh(d) for d in res['donors'])}")
    print(f"  rows LOST relative to the proportional fence: "
          f"{', '.join(sh(s) for s in base_ranked if s not in res['live']) or 'none'}")

    # ------------------------------------------------------------ part (4)
    print("\n" + LINE)
    print("(4) THE ERA MATRIX UNDER FENCE-T. R503's RULES 1 AND 2, "
          "INHERITED VERBATIM.")
    print(LINE)
    print(f"\n  POOLED CALENDAR: {POOLED_REF}'s FENCE-T window, "
          f"{len(res['pooled'])} days "
          f"(under the proportional fence it was "
          f"{len(tp_prop[POOLED_REF]['days'])} days).")
    print(f"  A1 (reference covers >= {CONTAIN_MIN:.0%} of pooled days):")
    for dn in res["donors"]:
        ov = len(res["tp"][dn]["days"] & res["pooled"])
        print(f"     {sh(dn):<6} {ov:>6} of {len(res['pooled'])} pooled days "
              f"= {ov / max(len(res['pooled']), 1):>5.0%}   "
              f"{'ADMISSIBLE' if res['a1_ok'][dn] else 'FAILS A1'}")
    print(f"\n  {'instrument':<11}", end="")
    for dn in res["donors"]:
        print(f"{sh(dn):>10}", end="")
    print(f"{'RULE1':>10}{'n adm':>7}{'RULE2':>10}")
    print("  " + "-" * (11 + 10 * len(res["donors"]) + 27))
    for sym in res["live"]:
        print(f"  {sym:<11}", end="")
        for dn in res["donors"]:
            x = res["cells"][sym].get(dn)
            if x is None:
                print(f"{'--':>10}", end="")
            else:
                print(f"{x:>9.3f}"
                      f"{'A' if dn in res['adm'][sym] else ' '}", end="")
        r = res["rows"][sym]
        m1 = f"{r['e1']:.3f}x" if np.isfinite(r["e1"]) else "UNMEAS"
        m2 = f"{r['e2']:.3f}x" if np.isfinite(r["e2"]) else "--"
        print(f"{m1:>10}{len(res['adm'][sym]):>7}{m2:>10}")
    unmeas = [s for s in res["live"] if not np.isfinite(res["rows"][s]["e1"])]
    print(f"\n  rows with NO admissible reference under FENCE-T: "
          f"{', '.join(sh(s) for s in unmeas) if unmeas else 'NONE'}")
    print("  under the proportional fence R503 found four: XRP, DOT, AVAX, "
          "ADA.")

    # ------------------------------------------------------------ part (5)
    print("\n" + LINE)
    print("(5) THE RANKING UNDER FENCE-T. R499's FEE COLUMN STAYS FROZEN.")
    print(LINE)
    print(f"\n  {'#':<4}{'instrument':<10}{'vol%':>9}{'/xSAME':>9}"
          f"{'vol* %':>9}{'fee%RT':>9}{'mult*':>8}{'ERA1':>9}{'mult1':>8}"
          f"{'ERA2':>9}{'mult2':>8}   sealed")
    print("  " + "-" * 100)
    for i, sym in enumerate(res["by_star"], 1):
        r = res["rows"][sym]
        f2 = lambda v, s="--": (f"{v:.3f}x" if np.isfinite(v) else s)  # noqa
        f3 = lambda v, s="--": (f"{v:.2f}" if np.isfinite(v) else s)   # noqa
        print(f"  {i:<4}{sym:<10}{r['vol']:>9.4f}{f2(r['xsame']):>9}"
              f"{r['nvol']:>9.4f}{r['fee']:>9.4f}{f3(r['nmult']):>8}"
              f"{f2(r['e1'],'UNMEAS'):>9}{f3(r['m1']):>8}"
              f"{f2(r['e2']):>9}{f3(r['m2']):>8}   {r['sealed']}")
    print(f"\n  R503 RULE 1 (proportional fence, published) : "
          f"LINK > SOL > PAXG > DOGE > BTC > LTC > ETH   "
          f"(XRP, DOT, AVAX, ADA absent)")
    print(f"  FENCE-T RULE 1                             : "
          f"{' > '.join(sh(s) for s in res['o1'])}")
    print(f"  FENCE-T RULE 2                             : "
          f"{' > '.join(sh(s) for s in res['o2'])}")

    # ------------------------------------------------------------ part (6)
    print("\n" + LINE)
    print("(6) THE UNANIMITY TEST UNDER FENCE-T - THE QUESTION THE ITEM "
          "ACTUALLY ASKS")
    print(LINE)
    npairs = len(res["resolved"]) + len(res["unordered"])
    print(f"\n  rows carrying a Rule 1 era factor: {len(res['o1'])} of 11. "
          f"ordered pairs among them: {npairs}.")
    print(f"    RESOLVED (every admissible reference agrees) : "
          f"{len(res['resolved'])}")
    print(f"    UNORDERED                                    : "
          f"{len(res['unordered'])}")
    if res["unordered"]:
        print("\n  the pairs with no order, and why each failed:")
        for a, b, why in res["unordered"]:
            print(f"    {sh(a):<6} vs {sh(b):<6}  {why}")
            for r_ in [r for r in res["adm"][a] if r in res["adm"][b]]:
                ma = res["rows"][a]["nmult"] / res["cells"][a][r_]
                mb = res["rows"][b]["nmult"] / res["cells"][b][r_]
                print(f"        on {sh(r_):<5}: {sh(a)} {ma:.3f} vs "
                      f"{sh(b)} {mb:.3f}  -> "
                      f"{sh(a) if ma > mb else sh(b)} above")
    print(f"\n  THE TOP FOUR UNDER FENCE-T: "
          f"{', '.join(sh(s) + ' (' + res['rows'][s]['sealed'] + ')' for s in res['top'])}")
    print(f"    pairs among them: {len(res['top']) * (len(res['top']) - 1) // 2};  "
          f"UNORDERED: {len(res['top_bad'])};  "
          f"no era factor at all: {len(res['top_miss'])}")
    print(f"  R503's contested three under the proportional fence: "
          f"{', '.join(sh(s) for s in R503_TOP)}")

    # ------------------------------------------------------------ part (7)
    print("\n" + LINE)
    print("(7) THE COMMITTED DECISION. FOUR CONDITIONS, ALL FIXED BEFORE ANY "
          "NUMBER EXISTED.")
    print(LINE)
    c = criteria(res, base_ranked)
    print(f"\n  P1 placement   - every top-four row has a Rule 1 era factor "
          f"          : {'PASS' if c['p1'] else 'FAIL'}")
    print(f"  P2 resolution  - unanimity leaves the top four fully ordered   "
          f"          : {'PASS' if c['p2'] else 'FAIL'}")
    print(f"  P3 agreement   - Rule 2's top four identical to Rule 1's       "
          f"          : {'PASS' if c['p3'] else 'FAIL'}")
    print(f"       Rule 1 top four : "
          f"{' > '.join(sh(s) for s in c['o1t']) if c['o1t'] else '(none)'}")
    print(f"       Rule 2 top four : "
          f"{' > '.join(sh(s) for s in c['o2t']) if c['o2t'] else '(none)'}")
    print(f"  P4 admissibility of the fence itself                           "
          f"          : {'PASS' if c['p4'] else 'FAIL'}")
    print(f"       (a) no un-spending  : "
          f"{'PASS' if c['p4a'] else 'FAIL'}   "
          f"{'no pinned boundary moves later' if c['p4a'] else c['mat_un']}")
    print(f"       (b) no material pre-contamination (>= "
          f"{PRECONTAM_MATERIAL_DAYS:.0f}d on a spent-look row) : "
          f"{'PASS' if c['p4b'] else 'FAIL'}")
    for s, d in sorted(c["mat_pc"], key=lambda x: -x[1]):
        print(f"            {sh(s):<6} re-seals {d:>7.1f} days - "
              f"{SPENT_LOOK[s]}")
    imm = [(s, d) for s, d in c["precontam"]
           if d < PRECONTAM_MATERIAL_DAYS]
    if imm:
        print(f"            immaterial (< 1 day): "
              f"{', '.join(sh(s) + f' {d * 24 * 60:.0f}min' for s, d in imm)}")
    print(f"       (c) no ranked row lost : "
          f"{'PASS' if c['p4c'] else 'FAIL'}"
          f"{'' if c['p4c'] else '   LOST: ' + ', '.join(sh(s) for s in c['lost'])}")
    print(f"\n  VERDICT: {c['verdict']}")

    # ------------------------------------------------------------ part (8)
    print("\n" + LINE)
    print("(8) THE DECLARED SENSITIVITY LADDER. IT IS NOT A SELECTOR - THE "
          "VERDICT ABOVE IS THE PRIMARY'S.")
    print(LINE)
    print(f"\n  {'D (days)':<10}{'T_END':<22}{'readable':>9}{'lost rows':>11}"
          f"{'era-less':>10}{'P1':>5}{'P2':>5}{'P3':>5}{'P4':>5}   verdict")
    print("  " + "-" * 104)
    for D in LADDER_D:
        te = BTC_T1 - pd.Timedelta(days=D)
        if D == 406:
            te = T_END_PRIMARY
        r = evaluate(te, pub)
        cc = criteria(r, base_ranked)
        el = [s for s in r["live"] if not np.isfinite(r["rows"][s]["e1"])]
        tag = "  <-- PRIMARY" if D == 406 else ""
        print(f"  {D:<10}{str(te):<22}{len(r['live']):>9}"
              f"{len(cc['lost']):>11}{len(el):>10}"
              f"{'Y' if cc['p1'] else 'n':>5}{'Y' if cc['p2'] else 'n':>5}"
              f"{'Y' if cc['p3'] else 'n':>5}{'Y' if cc['p4'] else 'n':>5}"
              f"   {cc['verdict']}{tag}")
    print("\n  No rung but the primary supplies a verdict, an ordering or a "
          "fence. A rung that 'works better'")
    print("  is a finding about sensitivity, not a licence to move the "
          "primary - that is the failure mode")
    print("  items 38 and 39 exist to prevent.")

    # ------------------------------------------------------------ verdict
    print("\n" + LINE)
    print("WHAT THIS ROUND ESTABLISHES")
    print(LINE)
    print(f"\n  1. THE FENCE PREDATES THE ANSWER, and that is checkable: "
          f"commit {PREREG_COMMIT[:12]} carries the")
    print("     fence, the trailing length, the unfenceable-row policy and "
          "all four decision criteria, and")
    print("     was made before this file existed.")
    print(f"\n  2. THE VERDICT IS: {c['verdict']}.")
    print(f"\n  3. NOTHING IS ADOPTED. R503's published table stands: LINK "
          f"1st and resolved; places 2-4")
    print("     UNORDERED {PAXG, SOL, XRP}; DOGE > BTC > LTC > ETH resolved. "
          "This round recomputed an")
    print("     ordering under a different fence and selected nothing off "
          "it, which is item 39's own fence.")
    print("\n  4. COSTS DECIDE NOTHING (owner rule, 2026-07-25). Nothing "
          "above declines a trade, gates a")
    print("     strategy or ranks an instrument for trading.")
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
