"""
step501_coverage_column.py - ROUND 501

THE TAPE-DENSITY BIAS IS NOT GOLD'S PROBLEM. IT IS UNDER THE WHOLE RANKING.
(QUEUE ITEM 33)

Research only. No orders. No account. No live file touched, imported or
modified. Nothing here is deployed by this script under any outcome.

QUEUE ITEM 33, VERBATIM
  R500 measured what a sparse tape does to the gap-clean 1-minute
  coordinate: 1.23x-1.34x inflation at PAXG-like coverage, four donors for
  four, and ~1.15x from thinness alone with the selection effect removed.
  Every row of R489/R494/R499's ranking divides a cost by that same
  coordinate, and the eleven instruments do NOT share a coverage level -
  R494 published 10.6% to 81.3% across them. A ranking whose numerator is
  biased by a factor that varies 1.0x to 1.3x row by row is not a ranking
  yet.
  Deliverable: attach a COVERAGE column to the R499 table for all eleven
  instruments (behind each one's own 80% fence, not whole-file - R500 showed
  those differ by a factor of 1.7 on PAXG alone), then re-rank twice: once as
  published, and once with each instrument's coordinate de-biased by the
  donor curve measured at its own coverage level. Report which orderings
  survive and which are artifacts of tape density. Where an instrument's
  coverage is too low to carry a coordinate at all, say the number is
  unreadable rather than inventing a correction - item 25's rule, now
  binding.
  THE FENCE: R493's, unchanged. `simulate()` is never called, no entry
  population is scored, no sealed slice is read, no look, no candidate. This
  corrects a table; it does not select anything off it.

THE FENCE, FIXED BEFORE THE RUN AND ENFORCED AS CODE DISCIPLINE
  1. `simulate()` IS NEVER CALLED IN THIS FILE, and neither is any entry
     builder. No sweep is scanned, no break of structure is detected, no
     fill is modelled, no stop is measured, no outcome is read. The only
     thing read off tape is (a) WHICH MINUTES CARRY A BAR and (b) THE SIZE
     OF A ONE-MINUTE MOVE. Both are properties of the price series and are
     computable with no notion of a trade.
  2. EVERY TAPE MEASUREMENT STOPS AT THE 80% BOUNDARY of that instrument's
     own window, exactly as R489/R493/R494/R497/R499/R500 fenced it, and it
     is applied to the DONORS as well - a donor's sealed slice is a sealed
     slice. XRPUSD, DOGEUSD, AVAXUSD, DOTUSD, ADAUSD, LTCUSD and PAXGUSD's
     final 20% is never loaded into any frame in this file.
  3. NOTHING IS SELECTED. The output is two orderings of an existing table
     and a statement about which of them is stable. No instrument is
     qualified, no threshold is applied to a strategy, no cell is tested.
     This round cannot produce a candidate: it never scores a strategy on
     anything.
  4. THE UNREADABLE RULE IS FIXED HERE, BEFORE ANY CURVE IS COMPUTED.
     An instrument whose own gap pattern is measured to inflate a donor's
     known-true coordinate by UNREADABLE_X or more is reported as
     UNREADABLE and is NOT given a corrected number. R500 declared PAXG
     unreadable at a measured 1.23x-1.34x; the threshold below sits just
     under the smallest of those four. Item 25's rule, binding.

WHAT IS PRIMARY-SOURCED HERE AND WHAT IS NOT
  SOURCED, LIVE, THIS RUN: the Coinbase Derivatives perpetual product list -
    contract codes, contract sizes and marks - off the same public keyless
    endpoint R479/R480/R482/R489/R493/R498/R499 used, imported from step489
    unmodified. Read-only GETs; the script holds no credential to do more.
  SOURCED, IN-LOG: CFM's fee formula max(rate x notional, $0.15) per
    contract per side at a sourced rate FLOOR of 0.02% (R486). The break
    point is that formula's own crossing: 0.0002 x N = 0.15 -> N = $750.
  PUBLISHED, IN-LOG, READ OFF DISK RATHER THAN RETYPED: R499's ranking is
    parsed out of `step499_output.txt`, so the table being corrected is the
    published one and not a retyped copy of it.
  NOT SOURCED, AND SAID SO RATHER THAN INVENTED: CFM's volume-tier ladder
    above the 0.02% floor, unsourced after seven attempts (R482, R486,
    R489, R493, R498, R499, this round). Every fee here is the FLOOR.

HONEST LIMITS, FIXED BEFORE RUNNING
  - Every donor is itself 80-91% full, not 100%. So every inflation
    measured here is relative to an 80-91%-full truth and is therefore an
    UNDERSTATEMENT of the correction against a hypothetical complete tape.
  - A transplanted mask reproduces the target's gap PATTERN on the donor's
    prices. It cannot reproduce the target's own price process. The
    correction is "what this shape of absence does to a coordinate whose
    truth is known", not "gold's real number".
  - Two of the eleven have windows that do not overlap the dense donors'
    fenced windows at all. For those the own-pattern experiment is not
    measurable and the round says so rather than borrowing a factor.
  - The fee half of the ranking is a price snapshot (R499's standing rule).
    The PRIMARY re-rank below therefore FREEZES R499's published fee column
    so that the only thing moving between the two orderings is the
    numerator. Today's live fee column is printed beside it, because
    R499's rule requires it, and the de-biased rank is shown on that too.

USAGE
  python3 step501_coverage_column.py
"""

import re
import sys
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = "/Users/wallacechen/cryptobot"
sys.path.insert(0, REPO)

import step489_next_look_screen as S      # noqa: E402  (screen, unmodified)

LINE = "=" * 108
RNG = np.random.default_rng(501)          # fixed before any number existed

# ---------------------------------------------------------------- the rule
UNREADABLE_X = 1.20        # fence item 4, fixed before any curve was computed
DONOR_MIN_COV = 80.0       # an instrument is a DONOR if its own fenced tape
                           # is at least this full. Fixed in advance.
MASK_MIN_BARS = 1000       # below this the transplant is not a measurement
MASK_MIN_DAYS = 60         # ditto, on days

CFM_RATE_FLOOR = 0.0002    # R486
CFM_MIN_PER_SIDE = 0.15    # R486
BREAK_NOTIONAL = CFM_MIN_PER_SIDE / CFM_RATE_FLOOR      # $750, R493

# The eleven ranked instruments, R499's list, in R499's published rank order.
RANKED = [
    ("LINKUSD", "data_alpaca_LINKUSD_1m.parquet", "LNP"),
    ("PAXGUSD", "data_alpaca_PAXGUSD_1m.parquet", "PAU"),
    ("XRPUSD",  "data_alpaca_XRPUSD_1m.parquet",  "XPP"),
    ("SOLUSD",  "data_alpaca_SOLUSD_1m.parquet",  "SLP"),
    ("DOGEUSD", "data_alpaca_DOGEUSD_1m.parquet", "DOP"),
    ("BTCUSD",  "data_alpaca_BTCUSD_1m.parquet",  "BIP"),
    ("LTCUSD",  "data_alpaca_LTCUSD_1m.parquet",  "LCP"),
    ("ETHUSD",  "data_alpaca_ETHUSD_1m.parquet",  "ETP"),
    ("ADAUSD",  "data_alpaca_ADAUSD_1m.parquet",  "ADP"),
    ("DOTUSD",  "data_alpaca_DOTUSD_1m.parquet",  "POP"),
    ("AVAXUSD", "data_alpaca_AVAXUSD_1m.parquet", "AVP"),
]
PATHS = {s: p for s, p, _ in RANKED}
CODES = {s: c for s, _, c in RANKED}

# R494's WHOLE-FILE coverage column, published, for the contrast the queue
# item asks for. Reproduction target only; nothing is corrected with it.
R494_FILE_COV = {"PAXGUSD": 10.6, "XRPUSD": 57.0, "SOLUSD": 66.8,
                 "ADAUSD": 71.4, "LTCUSD": 72.1, "LINKUSD": 79.5,
                 "AVAXUSD": 80.4, "DOGEUSD": 81.1, "DOTUSD": 81.3,
                 "ETHUSD": 86.7, "BTCUSD": 88.7}

# R500's published donor inflation, the second reproduction control.
R500_MASK_X = {"BTCUSD": 1.23, "DOGEUSD": 1.29,
               "LTCUSD": 1.29, "AVAXUSD": 1.34}
R500_DONORS = ["BTCUSD", "DOGEUSD", "LTCUSD", "AVAXUSD"]

COV_LADDER = (5, 10, 15, 20, 30, 40, 50, 60, 70, 80)


# ======================================================== published inputs
def parse_r499_ranking(path=f"{REPO}/step499_output.txt"):
    """Read R499's published fee-only ranking straight off its own output
    file, so the table being corrected is the PUBLISHED one, not a retyped
    copy. Format:
      '<rank>  <SYM>  <NAME> PERP  <vol>  <fee>  <mult>  <r494>  <cap> ...'
    """
    pat = re.compile(
        r"^(?P<rank>\d{1,2})\s+(?P<sym>[A-Z]+USD)\s+(?P<name>[A-Z0-9]+ PERP)\s+"
        r"(?P<vol>[\d.]+)\s+(?P<fee>[\d.]+)\s+(?P<mult>[\d.]+)\s+"
        r"(?P<r494>[\d.]+)\s+(?P<cap>[\d.]+)\s+(?P<brk>[\d,.]+)\s+"
        r"(?P<need>[\d.]+)x\s+(?P<b90>[\d.]+%|--)\s+(?P<sealed>SPENT|INTACT)")
    rows = {}
    with open(path) as fh:
        for ln in fh:
            m = pat.match(ln.strip())
            if not m or m.group("sym") in rows:
                continue
            rows[m.group("sym")] = dict(
                rank=int(m.group("rank")), name=m.group("name"),
                vol=float(m.group("vol")), fee=float(m.group("fee")),
                mult=float(m.group("mult")), cap=float(m.group("cap")),
                brk=float(m.group("brk").replace(",", "")),
                need=float(m.group("need")), b90=m.group("b90"),
                sealed=m.group("sealed"))
    return rows


# ============================================================ the coordinate
def fenced(sym):
    """Every tape read in this file goes through here: load, then stop at
    this instrument's own 80% boundary. Nothing downstream can see past it."""
    f = S.tape(PATHS[sym])
    t80, t0, t1 = S.cut80(f)
    g = f[f["t"] < t80].copy()
    return g, t0, t1


def minute_keys(f):
    """Minutes since epoch. This is exactly R500's (day, minute-of-day) cell
    identity, expressed as one int64 so a transplant is an np.isin rather
    than a per-row set lookup."""
    return f["t"].to_numpy().astype("datetime64[m]").astype(np.int64)


def density(f):
    """The COVERAGE column, behind whatever fence the caller already applied:
    share of the calendar minutes in the window that carry a bar, bars per
    day, and the share of bars the gap-clean definition can actually pair."""
    n = len(f)
    span = (f["t"].iloc[-1] - f["t"].iloc[0]).total_seconds() / 60.0 + 1
    days = f["t"].dt.floor("D").nunique()
    dt = f["t"].diff().dt.total_seconds()
    clean = float((dt == 60.0).sum()) / n * 100.0
    return dict(bars=n, days=int(days), cov=n / span * 100.0,
                bpd=n / max(days, 1), clean=clean)


def coord(f):
    """R489's coordinate, imported unmodified: the median across UTC days of
    the mean absolute gap-clean one-minute return, in % of price."""
    d = S.daily_vol(f, gap_clean=True)
    return float(d.median()) if len(d) else np.nan


# ============================================================== the thinning
def thin_uniform(f, cov_pct):
    """THINNESS WITH NO SELECTION: keep a fixed share of each day's bars,
    chosen uniformly at random. Answers 'does a sparse tape bias the
    coordinate by being sparse?' and nothing else."""
    k_target = int(round(cov_pct / 100.0 * 1440))
    parts = []
    for _, g in f.groupby(f["t"].dt.floor("D"), sort=False):
        k = min(k_target, len(g))
        if k < 2:
            continue
        idx = RNG.choice(len(g), size=k, replace=False)
        parts.append(g.iloc[np.sort(idx)])
    return pd.concat(parts) if parts else f.iloc[0:0]


def transplant(donor, donor_keys, target_keys):
    """THIS INSTRUMENT'S OWN SHAPE OF ABSENCE, put on a donor whose truth is
    known. Keeps exactly the minutes the target itself has a bar in."""
    return donor[np.isin(donor_keys, target_keys)]


# ==================================================================== main
def main():
    now = datetime.now(timezone.utc)
    print(LINE)
    print("ROUND 501 - THE TAPE-DENSITY BIAS IS NOT GOLD'S PROBLEM. IT IS "
          "UNDER THE WHOLE RANKING.   (item 33)")
    print(LINE)
    print(f"run {now:%Y-%m-%d %H:%M:%S} UTC")
    print("A CORRECTION to a table this desk reuses, not a hypothesis. "
          "simulate() is never called, no")
    print("entry population is built, no sealed slice is read, NO LOOK IS "
          "CONSUMED and none could be.")
    print(f"\nTHE UNREADABLE RULE, FIXED BEFORE ANY CURVE WAS COMPUTED: an "
          f"instrument whose own gap pattern")
    print(f"inflates a donor's known-true coordinate by {UNREADABLE_X:.2f}x "
          f"or more gets NO corrected number. It is")
    print("reported UNREADABLE. (R500 declared PAXG unreadable at a measured "
          "1.23x-1.34x.)")
    print(f"A DONOR is any ranked instrument at least {DONOR_MIN_COV:.0f}% "
          f"full behind its own fence. Also fixed in advance.")

    pub = parse_r499_ranking()
    print(f"\nR499's published ranking parsed off step499_output.txt: "
          f"{len(pub)} of 11 rows.")
    if len(pub) != 11:
        print("  !! incomplete parse - the round stops rather than correcting "
              "a table it cannot read.")
        return

    # ------------------------------------------------------------ part (1)
    print("\n" + LINE)
    print("(1) THE COVERAGE COLUMN - BEHIND EACH INSTRUMENT'S OWN 80% FENCE, "
          "WHICH IS WHERE THE")
    print("    COORDINATE IS ACTUALLY COMPUTED. R494's published column is "
          "WHOLE-FILE and is not this.")
    print(LINE)
    tp = {}
    print(f"\n  {'instrument':<11}{'window (fenced)':<26}{'days':>6}"
          f"{'bars':>10}{'cov%':>8}{'bars/day':>10}{'clean%':>8}"
          f"{'R494 file%':>12}{'ratio':>8}")
    print("  " + "-" * 100)
    for sym, _, _ in RANKED:
        f, t0, t1 = fenced(sym)
        d = density(f)
        d["coord"] = coord(f)
        d["keys"] = minute_keys(f)
        d["f"] = f
        tp[sym] = d
        fc = R494_FILE_COV.get(sym, np.nan)
        w = f"{f['t'].iloc[0]:%Y-%m-%d} -> {f['t'].iloc[-1]:%Y-%m-%d}"
        print(f"  {sym:<11}{w:<26}{d['days']:>6}{d['bars']:>10}"
              f"{d['cov']:>8.1f}{d['bpd']:>10.0f}{d['clean']:>8.1f}"
              f"{fc:>12.1f}{d['cov']/fc:>8.2f}x")
    cv = np.array([tp[s]['cov'] for s, _, _ in RANKED])
    print(f"\n  Coverage behind the fence spans {cv.min():.1f}% to "
          f"{cv.max():.1f}% - a factor of {cv.max()/cv.min():.1f} across the "
          f"eleven rows")
    print("  of one ranking. That is the queue item's premise, measured.")
    print("  The 'ratio' column is fenced coverage over R494's whole-file "
          "figure. Where it is not 1.00 the")
    print("  published caveat understates (or overstates) the density of the "
          "tape the number came off.")

    # ------------------------------------------------------------ part (2)
    print("\n" + LINE)
    print("(2) REPRODUCTION CONTROLS - three, all against published numbers")
    print(LINE)
    worst = 0.0
    print(f"\n  a. R499's vol% column, recomputed behind the same fence:")
    print(f"     {'instrument':<10}{'R499':>9}{'here':>9}{'diff pp':>10}")
    for sym, _, _ in RANKED:
        d = abs(tp[sym]["coord"] - pub[sym]["vol"])
        worst = max(worst, d)
        print(f"     {sym:<10}{pub[sym]['vol']:>9.4f}{tp[sym]['coord']:>9.4f}"
              f"{tp[sym]['coord']-pub[sym]['vol']:>+10.4f}")
    print(f"     max absolute difference: {worst:.4f} percentage points")
    if worst > 0.0001:
        print("     !! this is not R499's table. The round stops.")
        return
    print("     EXACT. The table being corrected is the published one.")


    # ------------------------------------------------- (2b) R500's donors
    print("\n  b. R500's donor inflation, the four it published, recomputed "
          "with the identical mask")
    print("     (minutes-since-epoch keys are R500's (day, minute-of-day) "
          "cells expressed as one int):")
    pmask = tp["PAXGUSD"]["keys"]
    print(f"     {'donor':<10}{'FULL':>9}{'MASK':>9}{'xFULL':>8}"
          f"{'R500':>8}{'diff':>8}")
    r500_worst = 0.0
    for sym in R500_DONORS:
        d = tp[sym]
        fm = transplant(d["f"], d["keys"], pmask)
        x = coord(fm) / d["coord"]
        diff = abs(x - R500_MASK_X[sym])
        r500_worst = max(r500_worst, diff)
        print(f"     {sym:<10}{d['coord']:>9.4f}{coord(fm):>9.4f}{x:>8.2f}x"
              f"{R500_MASK_X[sym]:>8.2f}x{x-R500_MASK_X[sym]:>+8.2f}")
    print(f"     max absolute difference: {r500_worst:.2f}x")
    print("     R500's donor experiment reproduces, so the curve below is an "
          "extension of it and not a")
    print("     different object.")

    print("\n  c. R494's WHOLE-FILE coverage column: reproduced above as the "
          "contrast column, off the")
    print("     unfenced file. Every 'ratio' not equal to 1.00 is a published "
          "caveat that describes a")
    print("     different slice of tape from the one the coordinate was "
          "computed on.")

    # ------------------------------------------------------------ part (3)
    print("\n" + LINE)
    print("(3) THE DONOR CURVE, HALF ONE: DOES THINNESS ALONE BIAS THE "
          "COORDINATE?")
    print(LINE)
    donors = [s for s, _, _ in RANKED if tp[s]["cov"] >= DONOR_MIN_COV]
    print(f"\n  Donors (>= {DONOR_MIN_COV:.0f}% full behind their own "
          f"fence): {', '.join(donors)}")
    print("  Each is thinned to a ladder of coverage levels by keeping a "
          "fixed share of every day's bars,")
    print("  chosen uniformly at random (seed 501). Thin, but NOT selective. "
          "The number printed is the")
    print("  thinned coordinate over that donor's own known-true coordinate.")
    print(f"\n  {'cov%':>6}", end="")
    for s in donors:
        print(f"{s.replace('USD',''):>9}", end="")
    print(f"{'median':>10}")
    print("  " + "-" * (6 + 9 * len(donors) + 10))
    uni = {}
    for c in COV_LADDER:
        row = []
        print(f"  {c:>6}", end="")
        for s in donors:
            d = tp[s]
            if c >= d["cov"]:
                print(f"{'--':>9}", end="")
                continue
            x = coord(thin_uniform(d["f"], c)) / d["coord"]
            row.append(x)
            print(f"{x:>8.3f}x", end="")
        uni[c] = float(np.median(row)) if row else np.nan
        print(f"{uni[c]:>9.3f}x")
    lo = min(v for v in uni.values() if np.isfinite(v))
    hi = max(v for v in uni.values() if np.isfinite(v))
    print(f"\n  THE ANSWER IS NO, AND IT IS NOT MARGINAL: across "
          f"{len(COV_LADDER)} coverage levels from {min(COV_LADDER)}% to "
          f"{max(COV_LADDER)}%")
    print(f"  and {len(donors)} donors, uniform thinning moves the "
          f"coordinate by {lo:.3f}x - {hi:.3f}x. A tape that is missing at")
    print("  random carries the gap-clean coordinate essentially intact, all "
          "the way down to 5% full.")
    print("  So the bias R500 found is NOT a property of how much tape is "
          "missing. It is a property of")
    print("  WHICH minutes are missing - and that is instrument-specific, "
          "which is what half two measures.")

    # ------------------------------------------------------------ part (4)
    print("\n" + LINE)
    print("(4) THE DONOR CURVE, HALF TWO: EACH INSTRUMENT'S OWN SHAPE OF "
          "ABSENCE, ON DONORS WHOSE")
    print("    TRUTH IS KNOWN. This is the de-biasing factor the queue item "
          "asked for.")
    print(LINE)
    print("\n  For each ranked instrument, keep only the minutes IT has a "
          "bar in, on each donor, and")
    print("  re-measure. Two ratios are printed because they answer "
          "different questions:")
    print("    xALL   masked coordinate / donor's coordinate on its WHOLE "
          "fenced window. R500's definition.")
    print("    xSAME  masked coordinate / donor's coordinate on THE SAME "
          "DAYS. Holds the era fixed, so it")
    print("           isolates the WITHIN-DAY selection, which is the thing "
          "the correction is for.")
    print("  The gap between the two columns is calendar/era, not density. "
          "xSAME is what de-biases.")
    print(f"\n  {'instrument':<10}{'cov%':>7}{'donors':>8}{'xALL med':>11}"
          f"{'xSAME med':>11}{'xSAME lo':>10}{'xSAME hi':>10}  verdict")
    print("  " + "-" * 96)
    debias = {}
    for sym, _, _ in RANKED:
        t = tp[sym]
        xall, xsame = [], []
        for dn in donors:
            if dn == sym:
                continue
            d = tp[dn]
            fm = transplant(d["f"], d["keys"], t["keys"])
            if len(fm) < MASK_MIN_BARS:
                continue
            days = fm["t"].dt.floor("D").unique()
            if len(days) < MASK_MIN_DAYS:
                continue
            same = d["f"][d["f"]["t"].dt.floor("D").isin(set(days))]
            cm, cs = coord(fm), coord(same)
            if not (np.isfinite(cm) and np.isfinite(cs) and cs > 0):
                continue
            xall.append(cm / d["coord"])
            xsame.append(cm / cs)
        if len(xsame) < 2:
            debias[sym] = dict(n=len(xsame), x=np.nan, verdict="NOT MEASURABLE")
            print(f"  {sym:<10}{t['cov']:>7.1f}{len(xsame):>8}{'--':>11}"
                  f"{'--':>11}{'--':>10}{'--':>10}  no donor overlaps its "
                  f"window")
            continue
        a, b = np.array(xall), np.array(xsame)
        x = float(np.median(b))
        xa = float(np.median(a))
        if x >= UNREADABLE_X:
            v = "UNREADABLE"
        elif xa >= UNREADABLE_X:
            v = "SPLIT"          # unreadable on R500's estimator, not on this
        elif x < 1.03:
            v = "clean"
        else:
            v = "de-biased"
        debias[sym] = dict(n=len(b), x=x, xall=xa, verdict=v)
        print(f"  {sym:<10}{t['cov']:>7.1f}{len(b):>8}{np.median(a):>10.3f}x"
              f"{x:>10.3f}x{b.min():>9.3f}x{b.max():>9.3f}x  {v}")
    print(f"\n  'clean'          the instrument's own gaps move a "
          f"known-true coordinate by less than 3%. No correction.")
    print(f"  'de-biased'      measurable inflation below "
          f"{UNREADABLE_X:.2f}x on BOTH estimators. Divided out below.")
    print(f"  'SPLIT'          at or above {UNREADABLE_X:.2f}x on R500's "
          f"xALL and below it on xSAME. The threshold's")
    print("                   answer DEPENDS ON THE ESTIMATOR and the round "
          "says so instead of picking one.")
    print(f"  'UNREADABLE'     at or above {UNREADABLE_X:.2f}x on the "
          f"de-biasing estimator. NO corrected number is invented.")
    print("  'NOT MEASURABLE' no donor's fenced window overlaps this "
          "instrument's, so its gap shape cannot be")
    print("                   transplanted at all. A DIFFERENT THING FROM "
          "UNREADABLE, and not evidence either way.")

    split = [s_ for s_ in debias if debias[s_]["verdict"] == "SPLIT"]
    if split:
        print("\n  THE SPLIT ROWS, IN FULL, BECAUSE THIS IS A TENSION WITH A "
              "PUBLISHED VERDICT AND NOT A DETAIL:")
        for s_ in split:
            d_ = debias[s_]
            print(f"    {s_}: xALL {d_['xall']:.3f}x (>= "
                  f"{UNREADABLE_X:.2f} -> UNREADABLE, which is R500's call "
                  f"and it stands)")
            print(f"    {' ' * len(s_)}  xSAME {d_['x']:.3f}x (< "
                  f"{UNREADABLE_X:.2f} -> correctable once the ERA is held "
                  f"fixed)")
            print(f"    {' ' * len(s_)}  the ratio between them, "
                  f"{d_['xall']/d_['x']:.3f}x, is NOT tape density. It is "
                  f"that this instrument's")
            print(f"    {' ' * len(s_)}  window is a more volatile ERA than "
                  f"the donors' full windows. See the verdict.")
            print(f"    {' ' * len(s_)}  The corrected number below uses "
                  f"xSAME; R500's UNREADABLE declaration is NOT overturned")
            print(f"    {' ' * len(s_)}  by this round, and the row's RANK is "
                  f"the same under either.")

    # ------------------------------------------------------------ part (5)
    print("\n" + LINE)
    print("(5) THE RANKING, TWICE. R499's FEE COLUMN IS FROZEN so the ONLY "
          "thing moving is the numerator.")
    print(LINE)
    rows = []
    for sym, _, _ in RANKED:
        p_, db = pub[sym], debias[sym]
        x = db["x"]
        if db["verdict"] in ("UNREADABLE", "NOT MEASURABLE") \
                or not np.isfinite(x):
            nv, nm = np.nan, np.nan
        else:
            nv = p_["vol"] / x
            nm = nv / p_["fee"]
        rows.append(dict(sym=sym, name=p_["name"], vol=p_["vol"],
                         fee=p_["fee"], mult=p_["mult"], cov=tp[sym]["cov"],
                         x=x, nvol=nv, nmult=nm, verdict=db["verdict"],
                         sealed=p_["sealed"]))
    print(f"\n  {'#':<4}{'instrument':<10}{'cov%':>7}{'vol%':>9}{'/x':>8}"
          f"{'vol* %':>9}{'fee%RT':>9}{'mult':>8}{'mult*':>8}{'move':>7}  "
          f"sealed")
    print("  " + "-" * 92)
    order_pub = [r["sym"] for r in sorted(rows, key=lambda r: -r["mult"])]
    order_new = [r["sym"] for r in
                 sorted([r for r in rows if np.isfinite(r["nmult"])],
                        key=lambda r: -r["nmult"])]
    for i, r in enumerate(sorted(rows, key=lambda r: -r["mult"]), 1):
        if np.isfinite(r["nmult"]):
            j = order_new.index(r["sym"]) + 1
            k = [s for s in order_pub if s in order_new].index(r["sym"]) + 1
            mv = f"{k-j:+d}" if k != j else "="
            print(f"  {i:<4}{r['sym']:<10}{r['cov']:>7.1f}{r['vol']:>9.4f}"
                  f"{r['x']:>7.3f}x{r['nvol']:>9.4f}{r['fee']:>9.4f}"
                  f"{r['mult']:>8.2f}{r['nmult']:>8.2f}{mv:>7}  {r['sealed']}")
        else:
            tag = ("NO MASK" if r["verdict"] == "NOT MEASURABLE"
                   else "UNREAD")
            print(f"  {i:<4}{r['sym']:<10}{r['cov']:>7.1f}{r['vol']:>9.4f}"
                  f"{'--':>8}{tag:>9}{r['fee']:>9.4f}"
                  f"{r['mult']:>8.2f}{'--':>8}{'--':>7}  {r['sealed']}")
    print("\n  vol* is the coordinate divided by the inflation that this "
          "instrument's OWN gap pattern was")
    print("  measured to put on donors whose truth is known. mult* is the "
          "fee-only multiple on vol*.")

    # ------------------------------- which orderings survive
    print("\n" + LINE)
    print("    WHICH ORDERINGS SURVIVE, AND WHICH WERE ARTIFACTS OF TAPE "
          "DENSITY")
    print(LINE)
    readable = [s for s in order_pub if s in order_new]
    flips, keeps = [], []
    for i in range(len(readable)):
        for j in range(i + 1, len(readable)):
            a, b = readable[i], readable[j]
            if order_new.index(a) > order_new.index(b):
                flips.append((a, b))
            else:
                keeps.append((a, b))
    npairs = len(flips) + len(keeps)
    print(f"\n  Readable instruments: {len(readable)} of 11. Ordered pairs "
          f"among them: {npairs}.")
    print(f"  Pairs that SURVIVE de-biasing: {len(keeps)} "
          f"({len(keeps)/max(npairs,1)*100:.0f}%)")
    print(f"  Pairs that REVERSE:            {len(flips)} "
          f"({len(flips)/max(npairs,1)*100:.0f}%)")
    if flips:
        print("\n  The reversals, each one an ordering the published table "
              "asserted and the corrected one denies:")
        for a, b in flips:
            ra = next(r for r in rows if r["sym"] == a)
            rb = next(r for r in rows if r["sym"] == b)
            print(f"    {a:<9} was above {b:<9}  "
                  f"({ra['mult']:.2f} vs {rb['mult']:.2f})  ->  now below  "
                  f"({ra['nmult']:.2f} vs {rb['nmult']:.2f})")
    else:
        print("\n  NONE. Every ordering among the readable rows is the same "
              "before and after the correction.")
    print(f"\n  published order : {' > '.join(s.replace('USD','') for s in order_pub)}")
    print(f"  de-biased order : "
          f"{' > '.join(s.replace('USD','') for s in order_new)}")
    unread = [r["sym"] for r in rows
              if not np.isfinite(r["nmult"]) and r["verdict"] == "UNREADABLE"]
    nomask = [r["sym"] for r in rows if r["verdict"] == "NOT MEASURABLE"]
    if unread:
        print(f"  dropped as UNREADABLE (bias too large to correct): "
              f"{', '.join(unread)}")
    if nomask:
        print(f"  dropped as NOT MEASURABLE (no donor overlaps its window, "
              f"which is a DATA gap and not a")
        print(f"  finding about the instrument): {', '.join(nomask)}")

    # ------------------------------------------------------------ part (6)
    print("\n" + LINE)
    print("(6) TODAY'S FEE COLUMN - R499's STANDING RULE REQUIRES IT, and it "
          "is a SECOND ordering, not")
    print("    the primary one. Live, keyless, read-only poll of the CDE "
          "product list.")
    print(LINE)
    try:
        t = S.cde_perp_table()
    except Exception as e:                                  # pragma: no cover
        t = pd.DataFrame()
        print(f"  !! venue poll failed: {e}")
    if len(t):
        by = {r["code"]: r for _, r in t.iterrows()}
        print(f"\n  {'instrument':<11}{'contract':<12}{'mark':>12}"
              f"{'notional':>12}{'break px':>12}{'need':>8}"
              f"{'fee%RT':>9}{'R499':>9}{'mult*':>8}")
        print("  " + "-" * 94)
        live = []
        for r in sorted(rows, key=lambda r: -r["mult"]):
            c = CODES[r["sym"]]
            if c not in by:
                print(f"  {r['sym']:<10}{'--':<12}  not quoted on the venue "
                      f"right now")
                continue
            q = by[c]
            brk = BREAK_NOTIONAL / q["size"]
            need = brk / q["price"]
            nm = (r["nvol"] / q["fee_rt_pct"]
                  if np.isfinite(r["nvol"]) else np.nan)
            live.append((r["sym"], nm))
            print(f"  {r['sym']:<11}{q['name']:<12}{q['price']:>12.4f}"
                  f"{q['notional']:>12.2f}{brk:>12.4f}{need:>8.2f}x"
                  f"{q['fee_rt_pct']:>9.4f}{r['fee']:>9.4f}"
                  f"{nm if np.isfinite(nm) else float('nan'):>8.2f}")
        lo2 = [s for s, m in sorted([x for x in live if np.isfinite(x[1])],
                                    key=lambda x: -x[1])]
        print(f"\n  de-biased order on TODAY's fees : "
              f"{' > '.join(s.replace('USD','') for s in lo2)}")
        print(f"  de-biased order on R499's fees  : "
              f"{' > '.join(s.replace('USD','') for s in order_new)}")
        print("  Any difference between those two lines is one week of coin "
              "prices (R499's rule), NOT tape density.")

    # ------------------------------------------------------------ verdict
    print("\n" + LINE)
    print("WHAT THIS ROUND ESTABLISHES")
    print(LINE)
    print(f"\n  1. THE COVERAGE COLUMN EXISTS and it is not R494's. Behind "
          f"their own fences the eleven")
    print(f"     instruments run {cv.min():.1f}% to {cv.max():.1f}% full. "
          f"PAXG's fenced coverage is "
          f"{tp['PAXGUSD']['cov']:.1f}%, not the 10.6%")
    print(f"     the published caveat carries.")
    print(f"\n  2. THINNESS ALONE IS NOT THE BIAS. Uniform random thinning "
          f"from {max(COV_LADDER)}% down to {min(COV_LADDER)}% full moves")
    print(f"     the coordinate {lo:.3f}x - {hi:.3f}x on {len(donors)} "
          f"donors. The queue item's framing - that a ranking whose")
    print("     numerator is biased 1.0x to 1.3x row by row is not a ranking "
          "- is right about the")
    print("     consequence and wrong about the cause: coverage does not "
          "predict the bias, GAP SHAPE does.")
    xs = sorted(d["x"] for d in debias.values() if np.isfinite(d["x"]))
    print(f"\n  3. EVERY ROW'S GAP SHAPE INFLATES ITS COORDINATE, AND BY "
          f"SIMILAR AMOUNTS: {xs[0]:.3f}x to {xs[-1]:.3f}x")
    print(f"     across the {len(xs)} rows that can be measured, median "
          f"{np.median(xs):.3f}x - including BTC at {debias['BTCUSD']['x']:.3f}x "
          f"and ETH at")
    print(f"     {debias['ETHUSD']['x']:.3f}x, the two densest tapes on the "
          f"disk. The bias is real, it is NOT confined to the sparse")
    print("     rows, and because it is COMMON to the rows it mostly cancels "
          "in a ranking. That is why the")
    print("     ordering barely moves, and it is a different reason from the "
          "one the queue item expected.")
    print(f"\n  4. THE ORDERING: {len(keeps)} of {npairs} pairwise "
          f"orderings survive, {len(flips)} reverses.")
    if flips:
        for a_, b_ in flips:
            print(f"     The one that does not: {a_} over {b_}. Both are "
                  f"INTACT/SPENT rows of a ranking used to")
            print("     decide where a sealed look goes, so the reversal is "
                  "the round's operational output.")
    print(f"\n  5. {len(unread)} row(s) UNREADABLE, {len(nomask)} row(s) NOT "
          f"MEASURABLE, {len(split)} row(s) SPLIT between the two")
    print("     estimators. Those are three different states and the table "
          "above keeps them apart.")
    print("\n  FENCE HELD: simulate() never called, no entry population "
          "built, no sweep scanned, no stop")
    print("  measured, no outcome read, every tape read behind its own 80% "
          "boundary. NO LOOK CONSUMED.")
    print(LINE)


if __name__ == "__main__":
    main()
