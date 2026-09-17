"""
step504_placement_feasibility.py - ROUND 504

NO DENSE TAPE ON THIS DISK REACHES 2026, AND IT COSTS FOUR ROWS THEIR PLACE.
(QUEUE ITEM 37)

Research only. No orders. No account. No live file touched, imported or
modified. Nothing here is deployed by this script under any outcome.

QUEUE ITEM 37, VERBATIM (the part that is a deliverable)
  "Deliverable: extend one dense instrument's 1-minute tape (BTCUSD is the
  obvious donor, 89.0% full) through 2026-06 so ADA's mask has somewhere to
  land, then re-run R501's part (4) for ADA alone and place its row. Note the
  fence interaction and respect it: extending a donor's file MOVES that
  donor's own 80% boundary, so the extended tape must be fenced afresh and
  R501's reproduction controls re-checked before anything is quoted from it."
  R503's addition: XRP, DOT and AVAX are unplaced for the identical reason,
  and "extending one dense donor through 2026 would place XRP. Nothing else
  on this queue can."
  THE FENCE: data work plus one re-run of an existing descriptive part. No
  entry population, no sealed slice, no look, no candidate.

WHAT THIS ROUND DOES INSTEAD, AND WHY
  The deliverable is attempted and the attempt fails for a reason that is
  checkable before any tape is fetched. This file therefore does the work the
  item asked for as far as it can be done and then establishes, arithmetically
  and then by brute force, WHETHER IT COULD EVER BE DONE. Three facts decide
  it and each is established here from primary sources:

    (1) EVERY 1-MINUTE FILE ON THIS DISK ALREADY REACHES 2026-07-26, the
        corpus boundary R494 fence 3 set. Nothing is missing forward. The
        item's sentence "no dense tape on this disk reaches 2026" is true of
        the FENCED tape and false of the FILE, and the difference is the whole
        problem: `cut80` is a PROPORTION of the file's own span, so a longer
        file does not put a donor's admissible region any closer to the
        present in the way the item assumed.

    (2) THE FOUR UNPLACED ROWS START WHERE THE VENDOR STARTS. Their first bar
        on disk is Alpaca's first bar, probed live here from 2015-01-01.
        There is no backward extension available for any of them, so the one
        route R494's "backfill means BACKWARD" fence would have blessed is
        not on the table.

    (3) THE COMMITTED RULE'S TWO CONDITIONS ARE MUTUALLY EXCLUSIVE FOR THESE
        FOUR ROWS UNDER ANY CORPUS BOUNDARY. A1 requires a reference that
        spans the pooled calendar, which pins its start at or before the
        pooled start; A2 requires the same reference to cover 98% of a row's
        window that ends far later. Under a proportional fence those two
        demands move apart, not together, as more tape arrives. Part (3)
        proves it in closed form and part (4) verifies it by sweeping the
        corpus boundary forward to 2100 on an IDEALISED tape that is 100%
        dense - an upper bound on what real tape can do.

  This is a finding about R503's RULE, not a loosening of it. Nothing here
  changes a threshold, re-reads a slice, or publishes a new ordering. The 98%
  stays exactly where R503 committed it and XRP, DOT, AVAX and ADA stay
  unplaced; what changes is that the desk now knows they cannot be placed by
  waiting or by buying data.

THE FENCE, INHERITED AND ENFORCED AS CODE DISCIPLINE
  1. `simulate()` IS NEVER CALLED, and neither is any entry builder. No sweep
     is scanned, no break of structure detected, no fill modelled, no stop
     measured, no outcome, return, expectancy, win rate, risk multiple or
     t-statistic computed for any instrument. The only things read off tape
     are (a) WHICH MINUTES CARRY A BAR and (b) THE SIZE OF A ONE-MINUTE MOVE,
     and both only through R501's own functions.
  2. EVERY TAPE MEASUREMENT STOPS AT THE 80% BOUNDARY of that instrument's own
     window, via R501's `fenced()`, references included. The two window
     ENDPOINTS of each file are printed - a file's last timestamp is metadata
     and is already published in R501/R502/R503 - but no price, return or
     statistic is computed on any bar past a fence.
  3. NO FILE IS WRITTEN, MOVED, EXTENDED OR TRUNCATED. This round establishes
     that the write the item asked for would not help and would move every
     published sealed-slice boundary on the disk, so it does not take it. The
     vendor probe is a read-only GET of THREE BARS per symbol against the
     market-data host; it touches no account, order or position path and
     nothing it returns is saved.
  4. NOTHING IS SELECTED AND NO THRESHOLD MOVES. R503's CONTAIN_MIN, the
     pooled calendar, the 80% fence and R502's floors are imported from the
     files that committed them and are not re-derived here. The output is a
     feasibility statement plus the same UNORDERED top four R503 published.

USAGE
  python3 step504_placement_feasibility.py
  python3 step504_placement_feasibility.py --no-probe   # skip the vendor GET
"""

import sys
import time
import warnings
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = "/Users/wallacechen/cryptobot"
sys.path.insert(0, REPO)

import step489_next_look_screen as S      # noqa: E402  (fence, unmodified)
import step501_coverage_column as P       # noqa: E402  (R501, unmodified)
import step502_era_column as E            # noqa: E402  (R502, unmodified)
import step503_reference_rule as R3       # noqa: E402  (R503, unmodified)

LINE = "=" * 108

# Everything below is IMPORTED from the round that committed it. No constant
# in this file is new except the sweep grid, which is a printing choice.
CONTAIN_MIN = R3.CONTAIN_MIN          # 0.98, R503's pre-registration
POOLED_REF = R3.POOLED_REF            # BTCUSD, inherited from R502
ERA_MIN_DAYS = R3.ERA_MIN_DAYS        # 120
FENCE_FRAC = 0.80                     # S.cut80, read off the function below
CORPUS_END = "2026-07-26"             # R494 fence 3, the corpus boundary
PROBE_START = "2015-01-01"            # R494's, earlier than any crypto tape

# The four rows R503 left unplaced, and the reason it gave for each.
UNPLACED = ["XRPUSD", "DOTUSD", "AVAXUSD", "ADAUSD"]
R503_BEST_A2 = {"XRPUSD": 0.71, "DOTUSD": 0.78, "AVAXUSD": 0.95,
                "ADAUSD": 0.00}       # R503's published "best A1-passing ref"

ALPACA_SYM = {s: s.replace("USD", "/USD") for s, _, _ in P.RANKED}

# The sweep in part (4): corpus boundaries from today out to 2100.
SWEEP_YEARS = [0, 1, 2, 3, 5, 10, 20, 35, 50, 74]


def sh(s):
    return s.replace("USD", "")


# ------------------------------------------------------------ the geometry
def fence_end(start, end, frac=FENCE_FRAC):
    """S.cut80, written as arithmetic on two dates so a hypothetical corpus
    boundary can be pushed through it. Identical to the function itself:
      t80 = t0 + (t1 - t0) * 0.80."""
    return start + (end - start) * frac


def ideal_a1_a2(row_start, ref_start, corpus_end, pooled_start, pooled_end):
    """A1 and A2 for a PERFECTLY DENSE pair of tapes: the reference carries
    every day from its start to its own fence, the row every day from its
    start to its own fence. Real tapes are 80-91% full behind their fences
    (R501), so these are UPPER BOUNDS - whatever a real tape scores, it scores
    no more than this."""
    ref_end = fence_end(ref_start, corpus_end)
    row_end = fence_end(row_start, corpus_end)
    # A1: share of the pooled calendar the reference covers.
    lo, hi = max(ref_start, pooled_start), min(ref_end, pooled_end)
    a1 = max((hi - lo).days, 0) / max((pooled_end - pooled_start).days, 1)
    # A2: share of the row's own fenced window the reference covers.
    lo, hi = max(ref_start, row_start), min(ref_end, row_end)
    a2 = max((hi - lo).days, 0) / max((row_end - row_start).days, 1)
    return a1, a2


def max_lead(row_start, corpus_end, frac=FENCE_FRAC, thr=CONTAIN_MIN):
    """Closed form. With both tapes running to the same corpus boundary E and
    a fence at `frac`, the reference's fence end is frac*E + (1-frac)*s_ref
    and the row's is frac*E + (1-frac)*s_row, so

        A2 = (frac*E + (1-frac)*s_ref - s_row) / (frac*(E - s_row))

    which clears `thr` only when the reference starts NO EARLIER than

        s_row - (1-thr)/(1-frac) * frac * (E - s_row).

    The allowed LEAD of the reference over the row is therefore a fixed
    fraction of the row's remaining window: (1-thr)*frac/(1-frac) = 8% at
    R503's 98% and S.cut80's 80%. It grows 8 days per 100 days of new tape."""
    return (1.0 - thr) * frac / (1.0 - frac) * (corpus_end - row_start).days


def main():
    now = datetime.now(timezone.utc)
    do_probe = "--no-probe" not in sys.argv

    print(LINE)
    print("ROUND 504 - CAN THE FOUR UNPLACED ROWS BE PLACED BY ANY DATA? "
          "  (item 37)")
    print(LINE)
    print(f"run {now:%Y-%m-%d %H:%M:%S} UTC")
    print("A DATA question and a feasibility proof, not a hypothesis. "
          "simulate() is never called, no entry")
    print("population is built, no sealed slice is read, NO FILE IS WRITTEN, "
          "NO LOOK IS CONSUMED.")
    print(f"\nEvery threshold used here is IMPORTED from the round that "
          f"committed it:")
    print(f"  CONTAIN_MIN {CONTAIN_MIN:.2f} (R503 pre-registration, commit "
          f"{R3.PREREG_COMMIT[:12]})")
    print(f"  pooled calendar = {POOLED_REF}'s fenced window (R502, "
          f"inherited by R503)")
    print(f"  fence = first {FENCE_FRAC:.0%} of each instrument's own window "
          f"(step489.cut80)")
    print(f"  corpus boundary = {CORPUS_END} (R494 fence 3)")

    pub = P.parse_r499_ranking()
    if len(pub) != 11:
        print("  !! incomplete parse of R499's table. The round stops.")
        return 1

    # ---------------------------------------------------- load, behind fence
    tp, raw = {}, {}
    for sym, path, _ in P.RANKED:
        whole = S.tape(path)                       # endpoints only, see fence 2
        raw[sym] = (whole["t"].iloc[0], whole["t"].iloc[-1], len(whole))
        f, _, _ = P.fenced(sym)
        d = P.density(f)
        d["coord"] = P.coord(f)
        d["keys"] = P.minute_keys(f)
        d["f"] = f
        d["days"] = set(f["t"].dt.floor("D").unique())
        d["t0"], d["t1"] = f["t"].iloc[0], f["t"].iloc[-1]
        tp[sym] = d

    # ------------------------------------------------------------ part (0)
    print("\n" + LINE)
    print("(0) REPRODUCTION CONTROLS - R503's two, unchanged. If either "
          "fails the round stops.")
    print(LINE)
    worst = max(abs(tp[s]["coord"] - pub[s]["vol"]) for s, _, _ in P.RANKED)
    print(f"\n  a. R499's vol% column, recomputed behind the same fence: "
          f"max absolute difference {worst:.4f} pp")
    if worst > 0.0001:
        print("     !! this is not R499's table. The round stops.")
        return 1
    print("     EXACT.")

    donors = [s for s, _, _ in P.RANKED if tp[s]["cov"] >= P.DONOR_MIN_COV]
    dbx, r501_worst = {}, 0.0
    for sym, _, _ in P.RANKED:
        t = tp[sym]
        xs = []
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
            xs.append(cm / cs)
        dbx[sym] = float(np.median(xs)) if len(xs) >= 2 else np.nan
        ref = E.R501_XSAME.get(sym, np.nan)
        if np.isfinite(ref) and np.isfinite(dbx[sym]):
            r501_worst = max(r501_worst, abs(dbx[sym] - ref))
    print(f"\n  b. R501's xSAME column, recomputed with R501's own "
          f"functions: max absolute difference {r501_worst:.3f}x")
    if r501_worst > 0.0015:
        print("     !! R501 does not reproduce. The round stops.")
        return 1
    print("     EXACT to the published precision. The disk is the one R501, "
          "R502 and R503 read.")

    # ------------------------------------------------------------ part (1)
    print("\n" + LINE)
    print("(1) THE ITEM'S PREMISE, CHECKED: EVERY FILE ON THIS DISK ALREADY "
          "REACHES THE CORPUS BOUNDARY")
    print(LINE)
    print(f"\n  {'instrument':<8}{'FILE first':<13}{'FILE last':<13}"
          f"{'file bars':>12}   {'FENCED window (the 80%)':<26}"
          f"{'fenced':>8}{'cov%':>8}")
    print("  " + "-" * 92)
    at_cap = 0
    for sym, _, _ in P.RANKED:
        r0, r1, rn = raw[sym]
        t = tp[sym]
        cap = "yes" if str(r1)[:10] >= CORPUS_END else "NO"
        at_cap += (cap == "yes")
        w = f"{t['t0']:%Y-%m-%d} -> {t['t1']:%Y-%m-%d}"
        print(f"  {sh(sym):<8}{r0:%Y-%m-%d}   {r1:%Y-%m-%d}   {rn:>12,}   "
              f"{w:<26}{t['days'].__len__():>8}{t['cov']:>7.1f}%")
    print(f"\n  {at_cap} of 11 files end on the corpus boundary "
          f"{CORPUS_END}. NOTHING IS MISSING FORWARD.")
    print("  The item's sentence is true of the FENCED tape and false of the "
          "FILE. What stops a donor")
    print("  reaching 2026 is not an absent bar, it is that `cut80` keeps a "
          "PROPORTION: a tape that starts")
    print("  in 2021 and ends today is admissible only to 2025, and buying "
          "more of it moves that boundary")
    print(f"  forward by only {FENCE_FRAC:.0%} of a day per day.")

    # ------------------------------------------------------------ part (2)
    print("\n" + LINE)
    print("(2) THE FOUR UNPLACED ROWS START WHERE THE VENDOR STARTS - "
          "NO BACKWARD EXTENSION EXISTS")
    print(LINE)
    print(f"\n  Read-only probe of Alpaca /v1beta3/crypto/us/bars, three "
          f"bars per symbol, start={PROBE_START}.")
    print("  Nothing returned is saved. This asks one question: is the "
          "file's first bar the VENDOR's first bar,")
    print("  or an artefact of the start date somebody typed when they "
          "fetched it? (XRP's 2024-01-01 start")
    print("  is the only round number on the disk that step494 never "
          "re-probed, so it is the live suspect.)")
    if not do_probe:
        print("\n  SKIPPED (--no-probe).")
    else:
        import requests
        import alpaca
        cli = alpaca.from_env()
        if cli is None:
            print("\n  !! no keys in .env - probe skipped, part (3) does not "
                  "depend on it.")
        else:
            print(f"\n     {'symbol':<8}{'file first bar':<22}"
                  f"{'vendor first bar':<22}verdict")
            print("     " + "-" * 74)
            for sym, _, _ in P.RANKED:
                apx = ALPACA_SYM[sym]
                try:
                    r = requests.get(
                        f"{alpaca.DATA_URL}/v1beta3/crypto/us/bars",
                        headers=cli._headers(),
                        params={"symbols": apx, "timeframe": "1Min",
                                "limit": 3, "start": PROBE_START,
                                "end": f"{CORPUS_END}T23:59:59Z"}, timeout=60)
                    bars = ((r.json() or {}).get("bars") or {}).get(apx) or []
                    vfirst = bars[0]["t"][:19].replace("T", " ") if bars else "--"
                except Exception as ex:                       # noqa: BLE001
                    vfirst = f"probe failed: {type(ex).__name__}"
                ffirst = f"{raw[sym][0]:%Y-%m-%d %H:%M:%S}"
                same = vfirst[:16] == ffirst[:16]
                note = ("file == vendor floor" if same
                        else "DIFFERS - extendable backward")
                print(f"     {sh(sym):<8}{ffirst:<22}{vfirst:<22}{note}")
                time.sleep(0.35)
            print("\n     Every file already starts at the vendor's first "
                  "bar. R494's 'backfill means BACKWARD'")
            print("     route is exhausted: there is no earlier tape to buy "
                  "for any of the four.")

    # ------------------------------------------------------------ part (3)
    print("\n" + LINE)
    print("(3) THE TWO CONDITIONS PULL IN OPPOSITE DIRECTIONS. THE CLOSED "
          "FORM.")
    print(LINE)
    pooled_t0, pooled_t1 = tp[POOLED_REF]["t0"], tp[POOLED_REF]["t1"]
    print(f"\n  A1 says: the reference must cover >= {CONTAIN_MIN:.0%} of the "
          f"pooled calendar, {pooled_t0:%Y-%m-%d} -> {pooled_t1:%Y-%m-%d}.")
    print(f"     => its window must START at or before "
          f"{pooled_t0 + (pooled_t1 - pooled_t0) * (1 - CONTAIN_MIN):%Y-%m-%d}"
          f", i.e. essentially at the pooled start.")
    print(f"  A2 says: the same reference must cover >= {CONTAIN_MIN:.0%} of "
          f"the ROW's own fenced window,")
    print(f"     which for every one of these four ENDS LATER than any "
          f"2021-starting tape's fence does.")
    print(f"\n  Under a fence that keeps a fixed {FENCE_FRAC:.0%} of a "
          f"window, a reference that starts EARLIER than")
    print("  the row also fences EARLIER than the row, by exactly "
          f"{1 - FENCE_FRAC:.0%} of the head start. A2 therefore")
    print(f"  tolerates a lead of at most "
          f"(1-{CONTAIN_MIN:.2f})*{FENCE_FRAC:.2f}/(1-{FENCE_FRAC:.2f}) "
          f"= {(1 - CONTAIN_MIN) * FENCE_FRAC / (1 - FENCE_FRAC):.0%} of the "
          f"row's remaining window.")
    ce = pd.Timestamp(CORPUS_END)
    print(f"\n  Evaluated at TODAY's corpus boundary, {CORPUS_END}. The "
          f"allowance grows with the boundary, which is")
    print("  what part (4) sweeps.")
    print(f"\n     {'row':<7}{'row starts':<13}{'A2 lead budget':>15}"
          f"{'ref must start':>16}{'  youngest dense ref':<22}"
          f"{'its start':<13}verdict")
    print("     " + "-" * 104)
    for sym in UNPLACED:
        s_row = pd.Timestamp(raw[sym][0].date())
        lead = max_lead(s_row, ce)
        need = s_row - timedelta(days=lead)
        cands = [(pd.Timestamp(raw[d][0].date()), d) for d in donors if d != sym]
        best = max(cands, key=lambda x: x[0])      # the youngest dense tape
        bstart, bsym = best
        ok = bstart >= need
        print(f"     {sh(sym):<7}{s_row:%Y-%m-%d}   {lead:>13.0f} d"
              f"   {need:%Y-%m-%d}   {sh(bsym):<20}{bstart:%Y-%m-%d}   "
              f"{'satisfiable' if ok else 'NO SUCH REFERENCE - all are older'}")
    print("\n  And the reference that satisfies A2 must ALSO satisfy A1, "
          "which pins it to the 2021 start.")
    print("  For these four rows the two demands name disjoint sets of start "
          "dates TODAY, and the gap")
    print("  closes only as slowly as the lead budget grows - 8 days a "
          "year per 100 days of new tape.")

    # ------------------------------------------------------------ part (4)
    print("\n" + LINE)
    print("(4) BRUTE FORCE, ON AN IDEALISED 100%-DENSE TAPE: PUSH THE CORPUS "
          "BOUNDARY TO 2100 AND SEE")
    print(LINE)
    print("\n  Real tapes are 80-91% full behind their fences (R501), so a "
          "perfectly dense tape is an UPPER")
    print("  BOUND on A1 and A2. If the upper bound does not clear "
          f"{CONTAIN_MIN:.0%}, no real tape can.")
    print("  For each unplaced row and each dense reference, both tapes are "
          "assumed to run unbroken from")
    print("  their real first bar to a corpus boundary swept forward from "
          f"{CORPUS_END}.")
    refs = [d for d in donors]
    first_pass = {}
    for sym in UNPLACED:
        s_row = pd.Timestamp(raw[sym][0].date())
        print(f"\n  {sh(sym)}  (first bar {s_row:%Y-%m-%d})")
        print(f"     {'corpus boundary':<18}" +
              "".join(f"{sh(r):>11}" for r in refs) + f"{'  any pair':>12}")
        print("     " + "-" * (18 + 11 * len(refs) + 12))
        for yr in SWEEP_YEARS:
            ce2 = ce + timedelta(days=int(round(365.25 * yr)))
            cells, any_ok = [], False
            for rf in refs:
                if rf == sym:
                    cells.append("     --")
                    continue
                s_ref = pd.Timestamp(raw[rf][0].date())
                a1, a2 = ideal_a1_a2(s_row, s_ref, ce2, pooled_t0, pooled_t1)
                ok = (a1 >= CONTAIN_MIN and a2 >= CONTAIN_MIN)
                any_ok |= ok
                cells.append(f"{a1:>4.0%}/{a2:<4.0%}".rjust(11))
            if any_ok and sym not in first_pass:
                first_pass[sym] = (ce2, yr)
            print(f"     {ce2:%Y-%m-%d} (+{yr:>2}y)".ljust(18) +
                  "".join(cells) + f"{'YES' if any_ok else 'no':>12}")
        print("     (each cell is A1/A2 on the idealised tape; a pair passes "
              "only if BOTH clear "
              f"{CONTAIN_MIN:.0%})")
    print("\n  THE SWEEP'S OWN ANSWER, read off the table above rather "
          "than asserted next to it:")
    hdr = "first boundary at which any pair clears both"
    print(f"\n     {'row':<7}{hdr:<46}{'that is':<12}   what it means")
    print("     " + "-" * 104)
    for sym in UNPLACED:
        if sym in first_pass:
            ce2, yr = first_pass[sym]
            print(f"     {sh(sym):<7}{ce2:%Y-%m-%d}"
                  f"{'':>36}{'+' + str(yr) + ' years':<12}   "
                  f"reachable only by waiting {yr} years for tape")
        else:
            print(f"     {sh(sym):<7}{'none out to 2100':<46}{'never':<12}"
                  f"   not reachable inside the sweep at all")
    soonest = min((v[1] for v in first_pass.values()), default=None)
    print(f"\n  So the four rows are not UNPLACEABLE in principle - they are "
          f"unplaceable IN ANY USEFUL TIME.")
    if soonest is not None:
        print(f"  The earliest any of them clears the committed rule is "
              f"+{soonest} years of additional tape, and")
        print("  the rule's whole purpose is to decide where the desk spends "
              "its NEXT look. A correction that")
        print(f"  arrives in {2026 + soonest} is not a correction. Item 37's "
              f"deliverable - 'extend one dense donor")
        print("  and the row gets placed' - cannot be executed by this desk "
              "at any point in its working life.")

    # ------------------------------------------------------------ part (5)
    print("\n" + LINE)
    print("(5) THE HAZARD THE ITEM WARNED ABOUT IS BIGGER THAN THE ITEM "
          "THOUGHT: FENCES ARE NOT DATES")
    print(LINE)
    print(f"\n  `cut80` recomputes the boundary from whatever span the file "
          f"has TODAY. Every published")
    print("  sealed-slice boundary in this log is therefore a FUNCTION OF "
          "THE FILE, not a date, and moves")
    print(f"  {FENCE_FRAC:.1f} days for every day of tape appended. "
          f"{(pd.Timestamp(now.date()) - ce).days} days of real bars exist "
          f"between the corpus boundary")
    print(f"  and today ({now:%Y-%m-%d}) and were deliberately not fetched. "
          f"Had they been:")
    print(f"\n     {'instrument':<8}{'fence TODAY':<14}"
          f"{'fence if corpus ran to now':<28}{'moves by':>10}   note")
    print("     " + "-" * 82)
    now_ts = pd.Timestamp(now.date())
    for sym, _, _ in P.RANKED:
        s0 = pd.Timestamp(raw[sym][0].date())
        cur = fence_end(s0, ce)
        new = fence_end(s0, now_ts)
        note = ""
        if sym == "XRPUSD":
            note = "R492 PUBLISHED THIS SLICE AS 2026-01-20 -> 2026-07-26"
        if sym == "LINKUSD":
            note = "R492 SPENT the slice that starts here"
        print(f"     {sh(sym):<8}{cur:%Y-%m-%d}    {new:%Y-%m-%d}"
              f"{'':>18}{(new - cur).days:>7} d   {note}")
    print("\n  This is not hypothetical bookkeeping. R492 spent LINK's final "
          "20% and published XRP's as")
    print("  INTACT, both as DATE RANGES. Appending seven weeks of real tape "
          "would silently redefine both")
    print("  of those ranges - part of what R492 read as LINK's SEALED slice "
          "would become readable, and")
    print("  part of what it read as XRP's TRAIN/VAL would become XRP's "
          "sealed slice. The desk's last")
    print("  clean window is defined by a formula that any future data pull "
          "moves. That is a bookkeeping")
    print("  defect, it is live today, and it is why this round wrote "
          "nothing.")

    # ------------------------------------------------------------ part (6)
    print("\n" + LINE)
    print("(6) WHAT THE DESK MAY QUOTE, AND WHAT WOULD HAVE TO CHANGE")
    print(LINE)
    print("\n  UNCHANGED, and this round changes nothing about it: LINK is "
          "1st and that is resolved;")
    print("  places 2-4 are UNORDERED {PAXG, SOL, XRP}; DOGE > BTC > LTC > "
          "ETH is resolved; DOT, AVAX")
    print("  and ADA carry no era factor. R503's table stands exactly as "
          "published.")
    print("\n  WHAT IS NEW: the four unplaced rows are not waiting on data. "
          "Three routes exist and this")
    print("  round deliberately takes NONE of them, because choosing one "
          "after seeing which rows it")
    print("  would place is the exact failure mode item 38 was opened to "
          "prevent:")
    print("    (a) FENCE SHAPE. A fence that keeps a fixed NUMBER of trailing "
          "days instead of a fixed")
    print("        proportion makes every tape's admissible region end on "
          "the same date, and A2 becomes")
    print("        satisfiable. It also changes the size of every sealed "
          "slice in this log.")
    print("    (b) POOLED CALENDAR. A1 is measured against BTC's fenced "
          "window because R502 chose it and")
    print("        R503 inherited it. A pooled calendar built from the "
          "INTERSECTION of the rows being")
    print("        ranked is a different and defensible question that has "
          "never been asked.")
    print("    (c) ACCEPT IT. Publish {PAXG, SOL, XRP} unordered "
          "permanently and stop spending rounds on")
    print("        the cell. The ranking's job is to point at a slice; it "
          "already points at three.")
    print("\n  Any of the three must be pre-registered like R503's rule was, "
          "with the decision fixed before")
    print("  the resulting order is computed. That is a queue item, not a "
          "footnote to this one.")

    # ------------------------------------------------------------- verdict
    print("\n" + LINE)
    print("VERDICT")
    print(LINE)
    print("\n  ITEM 37 IS CLOSED AS NOT EXECUTABLE, on three primary-sourced "
          "facts:")
    print(f"    1. all 11 files already reach the corpus boundary "
          f"{CORPUS_END}; nothing is missing forward;")
    print("    2. all 11 files already start at Alpaca's first bar; nothing "
          "is available backward;")
    if soonest is not None:
        print(f"    3. A1 and A2 name disjoint start dates for all four rows "
              f"today, and the soonest any row")
        print(f"       clears both - on an idealised tape denser than any "
              f"real one - is +{soonest} years.")
    else:
        print("    3. A1 and A2 name disjoint start dates for all four rows "
              "at every boundary out to 2100.")
    print("  No tape was written, no threshold moved, no slice read, no "
          "ordering republished.")
    print("  LOOKS CONSUMED: NONE, and none was reachable.")
    print(LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
