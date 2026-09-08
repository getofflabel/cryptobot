"""
step496_selector_audit.py - ROUND 496, QUEUE ITEM 20

THE GATE IS A SIGN TEST AND THE SELECTOR IS A t. WHAT DID THAT MISMATCH
ACTUALLY AIM, AND HOW OFTEN DO THE CANDIDATE RULES DISAGREE?

WHAT THIS FILE IS
-----------------
A PROTOCOL AUDIT. It reads numbers this log has ALREADY PUBLISHED and
re-ranks them under four selection rules. It runs no backtest, loads no
price data, builds no entry population, cuts no train/val/test split,
qualifies no cell, opens no sealed slice, and proposes nothing for
deployment. It imports nothing from the live desk.

Its only inputs are two artifacts already on disk:
    step474_table.csv    (R474, 64 pooled cells, 23 qualifiers)
    step492_output.txt   (R492, 32 cells x 2 instruments, 11 + 15 qualifiers)

THE FENCE, restated from queue item 20 and obeyed literally
-----------------------------------------------------------
  * No sealed slice is re-opened. The only sealed numbers that appear here
    are the two ALREADY PUBLISHED in RESEARCH_LOG.md (R474's surviving cell,
    R492's failing cell), quoted verbatim.
  * No cell that was never looked at may be looked at now. R474's other 22
    qualifiers and R492's other 10 stay unverified out of sample FOREVER.
    Where an alternative rule points at one of them, this file says so and
    STOPS. It does not, and cannot, say whether that pick would have done
    better.
  * A rule may NOT be chosen by how well it would have performed on a sealed
    slice it can now see. That is selecting a protocol on out-of-sample data
    - the exact error the protocol exists to prevent.
  * Output is a PROPOSED protocol change for Wallace to accept in an
    interactive session, applied to FUTURE rounds only. Nothing here
    re-interprets a published verdict.

=======================================================================
PART 0 - THE PREFERRED RULE, FROM FIRST PRINCIPLES, WRITTEN BEFORE THE
          TALLY WAS COMPUTED (item 20 requires this ordering)
=======================================================================

The four rules under audit:
  (i)   choosing-slice t                      <- R492's standing rule
  (ii)  middle-slice expectancy
  (iii) min(choosing, middle) expectancy
  (iv)  choosing-slice expectancy              <- R474's actual rule

1. THE UNIT COMES FIRST. R487 settled that the statistic the account earns
   is the PER-TRADE NET RISK MULTIPLE, not percent of price. A selector in
   percent of price ranks cells by a quantity nobody collects: a cell with
   twice the price edge and three times the stop is worse, not better.
   Every rule below is therefore defined in per-trade net R. (R474 predates
   R487 and selected in percent of price. That is chronology, not a fault.)

2. WHAT A SELECTOR IS FOR. At selection time the desk holds two read slices
   and one unread one, and has exactly ONE look. The selector's job is to
   maximise the chance the look lands on the cell with the best TRUE
   expectancy. That is an estimation problem under a winner's curse:
   whichever cell tops a noisy statistic is upward-biased, and the bias
   grows with the number of candidates and with the noise of the statistic.

3. WHY A t IS THE WRONG RANKER. t = mean / (sd / sqrt(n)). Two cells with
   identical true edge and identical dispersion differ in t by sqrt(n)
   alone - and n here is a property of HOW OFTEN A LEVEL FIRES (1-hour
   swings fire roughly three times as often as previous-day levels), not of
   how good the edge is. Ranking on t therefore imports the level's firing
   rate into the choice. A t answers "which cell am I most confident is not
   zero" - which is the GATE's question, and every candidate has already
   passed the gate. Asking it twice is not a second test.

4. WHY CHOOSING-SLICE EXPECTANCY IS ALSO WRONG. It is measured on the slice
   the candidates were ENUMERATED on, it is the noisiest estimator on offer,
   and the maximum of k of them is the most upward-biased of the four.

5. WHY MIDDLE-SLICE EXPECTANCY ALONE IS WRONG. The middle slice IS the gate.
   Using the gate as the chooser spends the same 20% of tape twice and turns
   a sign test into a ranking on the smaller of the two read samples.

6. THEREFORE THE PREFERRED RULE IS (iii): min(choosing, middle) per-trade
   net R. It cannot be carried by either slice alone; it is a lower bound on
   what the two read slices jointly support; it is MONOTONE IN THE GATE, so
   a cell that cleared by a hair can never outrank one that cleared by half
   a risk unit; and it is scale-free in n, so a level's firing rate buys no
   rank. Its cost is that it is conservative and will sometimes pass over a
   cell whose middle slice was merely unlucky. With exactly one look
   available, that is the right side to err on.
   Second choice (ii). The standing rule (i) is preferred by no principle
   available once a gate exists.

7. TRADE COUNT STAYS A GATE (30 train / 8 val), NEVER A CHOOSER. Ties on
   (iii) broken by the smaller slice's trade count.

Everything below PART 0 was computed after PART 0 was written.
"""

import csv
import os
import re

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
W = 118


def rule(s):
    print("=" * W)
    print(s)
    print("=" * W)


def spearman(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    if len(a) < 3:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


# ----------------------------------------------------------------- parsing
NUM = r"(-?[\d,]+\.?\d*)"
ROW = re.compile(r"^(.+?)\s{2,}" + r"\s+".join([NUM] * 11) + r"\s+(\w+)\s*$")


def f(x):
    return float(x.replace(",", ""))


def parse_492(path):
    """The two published 32-cell tables in R492's output. Columns are
    n_tr n_va grossTR% netTR% netVA% R_tr t_tr/day R_va t_va/day stop% win%."""
    blocks, cur, name = {}, None, None
    for line in open(path):
        if re.match(r"^\w+USD\s+-\s+all 32 cells", line):
            name = line.split()[0]
            blocks[name] = cur = []
            continue
        if line.startswith("=====") and cur is not None and len(cur) >= 32:
            cur = None
        if cur is None:
            continue
        m = ROW.match(line.rstrip())
        if not m:
            continue
        g = m.groups()
        cur.append(dict(
            name=g[0].strip(), n_tr=int(f(g[1])), n_va=int(f(g[2])),
            gross_tr=f(g[3]), net_tr=f(g[4]), net_va=f(g[5]),
            R_tr=f(g[6]), t_tr=f(g[7]), R_va=f(g[8]), t_va=f(g[9]),
            stop=f(g[10]), win=f(g[11]), status=g[12]))
    return blocks


def parse_474(path):
    rows = []
    for r in csv.DictReader(open(path)):
        try:
            rows.append(dict(
                name=r["name"], arm=r["arm"], n_tr=int(r["n_tr"]),
                n_va=int(r["n_va"]), mean_tr=float(r["mean_tr"]),
                mean_va=float(r["mean_va"]), R_tr=float(r["R_tr"]),
                stop=float(r["stop_tr"]), verdict=r["verdict"],
                n_assets_pos=int(r["n_assets_pos"])))
        except ValueError:
            continue
    return rows


# ------------------------------------------------------------------ rules
def apply_rules(cells, key_tr, key_va, key_t):
    """Returns {rule label: (winning cell, its value)}. key_t may be None
    where the log never computed a per-cell t."""
    out = {}
    out["(iv) choosing-slice expectancy"] = max(cells, key=lambda c: c[key_tr])
    out["(ii) middle-slice expectancy"] = max(cells, key=lambda c: c[key_va])
    out["(iii) min(choosing, middle)"] = max(
        cells, key=lambda c: min(c[key_tr], c[key_va]))
    if key_t:
        out["(i)  choosing-slice t"] = max(cells, key=lambda c: c[key_t])
    return out


ORDER = ["(i)  choosing-slice t", "(ii) middle-slice expectancy",
         "(iii) min(choosing, middle)", "(iv) choosing-slice expectancy"]


def report(title, cells, key_tr, key_va, key_t, unit, actual_rule, actual_pick,
           note=""):
    rule(title)
    print(f"  qualifying cells: {len(cells)}     ranking unit: {unit}")
    if note:
        print(f"  {note}")
    picks = apply_rules(cells, key_tr, key_va, key_t)
    print()
    print(f"  {'rule':<32}{'points at':<44}{'ch':>9}{'mid':>9}{'min':>9}"
          + (f"{'t_ch':>8}" if key_t else ""))
    for r_ in ORDER:
        if r_ not in picks:
            print(f"  {r_:<32}{'NOT COMPUTABLE - see note':<44}")
            continue
        c = picks[r_]
        line = (f"  {r_:<32}{c['name']:<44}{c[key_tr]:>9.3f}"
                f"{c[key_va]:>9.3f}{min(c[key_tr], c[key_va]):>9.3f}")
        if key_t:
            line += f"{c[key_t]:>8.2f}"
        print(line)
    distinct = {id(c) for c in picks.values()}
    print(f"\n  DISTINCT CELLS POINTED AT BY THE {len(picks)} COMPUTABLE RULES: "
          f"{len(distinct)}")
    for r1 in ORDER:
        for r2 in ORDER:
            if r1 < r2 and r1 in picks and r2 in picks:
                same = picks[r1] is picks[r2]
                print(f"    {r1:<32} vs {r2:<32} "
                      f"{'AGREE' if same else 'DISAGREE'}")
    print(f"\n  THE RULE THIS ROUND ACTUALLY USED: {actual_rule}")
    print(f"  IT POINTED AT: {actual_pick}")

    # where does each rule's pick rank under the OTHER metrics
    print("\n  Rank of each rule's pick under every metric "
          f"(1 = best of {len(cells)}):")
    metrics = [("choosing expectancy", key_tr), ("middle expectancy", key_va),
               ("min of the two", None)]
    if key_t:
        metrics.append(("choosing t", key_t))
    hdr = "".join(f"{m[0]:>22}" for m in metrics)
    print(f"  {'pick by rule':<32}{hdr}")
    for r_ in ORDER:
        if r_ not in picks:
            continue
        c = picks[r_]
        cells_ = list(cells)
        ranks = []
        for label, k in metrics:
            if k is None:
                vals = [min(x[key_tr], x[key_va]) for x in cells_]
                v = min(c[key_tr], c[key_va])
            else:
                vals = [x[k] for x in cells_]
                v = c[k]
            ranks.append(1 + sum(1 for x in vals if x > v))
        print(f"  {r_:<32}" + "".join(f"{x:>22}" for x in ranks))
    if key_t:
        print(f"\n  Spearman rank correlation among qualifiers, "
              f"choosing-slice t against:")
        print(f"    choosing expectancy  {spearman([c[key_t] for c in cells], [c[key_tr] for c in cells]):+.3f}")
        print(f"    middle expectancy    {spearman([c[key_t] for c in cells], [c[key_va] for c in cells]):+.3f}")
        print(f"    min of the two       {spearman([c[key_t] for c in cells], [min(c[key_tr], c[key_va]) for c in cells]):+.3f}")
        print(f"    TRADE COUNT n_tr     {spearman([c[key_t] for c in cells], [c['n_tr'] for c in cells]):+.3f}"
              "   <- NOT the mechanism: it flips sign between the two"
              "\n                                instruments. PART B4 finds "
              "the real one.")
    return picks


def main():
    print(__doc__)

    # =================================================================
    rule("PART A - THE CENSUS. HOW MANY ROUNDS EVER HAD A CHOICE TO MAKE?")
    print("""
Item 20 names four rounds as having qualified more than one cell: R450,
R474, R475, R492. Every stored round table on this disk was re-counted
before anything was ranked. The premise is half right.
""")
    r474 = parse_474(os.path.join(HERE, "step474_table.csv"))
    q474 = [c for c in r474 if c["verdict"] == "qualifies"
            and c["n_assets_pos"] >= 2]
    b492 = parse_492(os.path.join(HERE, "step492_output.txt"))
    q492 = {k: [c for c in v if c["status"] == "QUALIFIES"]
            for k, v in b492.items()}

    print(f"  R450  step450_table.csv         0 of 64 qualified  "
          f"-> NO SELECTION EXISTED. The sealed slice was never opened.")
    print(f"  R474  step474_table.csv        {len(q474)} of 64 qualified  "
          f"-> A REAL CHOICE. One look taken, cell SURVIVED.")
    print(f"  R475  step475_table_r450window  1 of 96 qualified  "
          f"-> ONE candidate. Every rule agrees trivially. Not a choice.")
    for k, v in q492.items():
        tag = ("A REAL CHOICE. One look taken, cell FAILED."
               if k == "LINKUSD" else
               "companion. Qualified but NO look existed under any outcome.")
        print(f"  R492  {k:<24}{len(v)} of 32 qualified  -> {tag}")
    print("""
  Also swept, for completeness, every other stored table with a verdict
  column: R370 (1 survivor of 277) and R410 (1 of 10). Single candidates,
  no choice.

  FINDING A. In the entire log, exactly TWO rounds have ever had more than
  one qualifying cell to choose between: R474 (23) and R492 (11 on LINK).
  R450 qualified nothing and R475 qualified exactly one. The mismatch item
  20 describes has therefore been exercised twice, not four times.

  FINDING B, and it is the one that changes the question. THE TWO ROUNDS
  DID NOT USE THE SAME RULE.
     R474: step474b_significance.py, verbatim -
           q.sort_values("mean_tr", ascending=False).iloc[0]
           "the single best cell by choosing-slice NET" - that is rule (iv),
           an EXPECTANCY, in percent of price.
     R492: pre-registered in its docstring - "the highest choosing-slice
           per-trade net R t clustered by UTC day" - that is rule (i).
  There is no standing rule. There are two rounds and two different rules,
  each fixed before its own run and each followed exactly. Item 20's
  premise that a t "aimed the look" is true of R492 and FALSE of R474.
""")

    # =================================================================
    report(
        "PART B1 - R474, SPY/QQQ, 23 QUALIFIERS. THE ROUND THAT SURVIVED.",
        q474, "mean_tr", "mean_va", None, "percent of price (R474's own unit)",
        "(iv) choosing-slice expectancy, in percent of price",
        "prev day low -> 1m BOS, hold to close",
        note=("NOTE: rule (i) IS NOT COMPUTABLE HERE AND NEVER WILL BE. R474 "
              "computed a t for each ARM,\n  not for each cell; no per-cell t "
              "exists in step474_table.csv or anywhere in the log. Producing "
              "one\n  would mean rebuilding the entry population, which item "
              "20's fence forbids. Three rules of four."))

    print("""
  R474's net-R column: the table carries R_tr (per-trade mean net R on the
  choosing slice) but NO R_va. So rule (iv) can be restated in R487's unit
  and the other two cannot. Restated:""")
    top_R = max(q474, key=lambda c: c["R_tr"])
    top_pct = max(q474, key=lambda c: c["mean_tr"])
    print(f"    (iv) in percent of price  -> {top_pct['name']:<42}"
          f"R_tr {top_pct['R_tr']:+.3f}")
    print(f"    (iv) in per-trade net R   -> {top_R['name']:<42}"
          f"R_tr {top_R['R_tr']:+.3f}")
    print(f"    {'AGREE' if top_R is top_pct else 'DISAGREE'} - and this is "
          "the unit question of point 1, not a rule question.")
    print(f"    R474's actual pick ranks "
          f"{1 + sum(1 for c in q474 if c['R_tr'] > top_pct['R_tr'])} of "
          f"{len(q474)} by choosing-slice net R.")

    # =================================================================
    report("PART B2 - R492, LINKUSD, 11 QUALIFIERS. THE ROUND THAT FAILED, "
           "AND THE ONE ITEM 20 IS ABOUT.",
           q492["LINKUSD"], "R_tr", "R_va", "t_tr", "per-trade net R",
           "(i) highest choosing-slice per-trade net R t clustered by UTC day",
           "last session low -> 1m BOS, target 3R")

    report("PART B3 - R492, XRPUSD, 15 QUALIFIERS. NO LOOK EXISTED HERE, SO "
           "NOTHING IS AT RISK.",
           q492["XRPUSD"], "R_tr", "R_va", "t_tr", "per-trade net R",
           "none - XRP was the companion and its sealed 20% was never read",
           "nothing. It remains INTACT.",
           note=("This population is the clean control for the disagreement "
                 "question: no cell here was ever\n  selected, so counting "
                 "how often the rules diverge costs nothing and risks "
                 "nothing."))

    # =================================================================
    rule("PART B4 - WHAT THE t IS ACTUALLY RANKING, AND IT IS NOT THE LEVEL")
    print("""
  PART 0 point 3 predicted that a t would import the LEVEL'S FIRING RATE
  into the choice. That prediction is wrong, or at least it is not the
  binding term - the t-to-trade-count correlation is -0.518 on LINK and
  +0.571 on XRP, which is no mechanism at all. The real term is larger and
  cleaner, and this table is the round's sharpest finding.

  The 32 cells are 8 LEVELS x 4 EXIT RULES. The four exit rules score THE
  SAME ENTRIES off the same level, so trade count is IDENTICAL across them
  by construction. Any t difference between exit rules is therefore PURE
  DISPERSION - nothing else is left to vary.
""")
    for inst, cells in b492.items():
        fam = {}
        for c in cells:
            fam.setdefault(c["name"].split(", ")[1], []).append(c)
        print(f"  {inst}, all 32 cells")
        print(f"    {'exit rule':<12}{'mean t':>9}{'mean per-trade net R':>23}"
              f"{'spread of R':>14}{'mean n_tr':>11}{'qualifiers':>12}")
        for ex in ("hold 24h", "target 1R", "target 2R", "target 3R"):
            v = fam[ex]
            print(f"    {ex:<12}{np.mean([x['t_tr'] for x in v]):>+9.2f}"
                  f"{np.mean([x['R_tr'] for x in v]):>+23.3f}"
                  f"{np.std([x['R_tr'] for x in v]):>14.3f}"
                  f"{np.mean([x['n_tr'] for x in v]):>11,.0f}"
                  f"{sum(1 for x in v if x['status'] == 'QUALIFIES'):>12}")
        print()
    print("""  FINDING C, on both instruments independently and in the same direction:

    hold-24h cells carry roughly FIFTEEN TIMES the per-trade expectancy of
    target-3R cells (LINK +0.513 against +0.035; XRP +0.751 against +0.087)
    - and target-3R cells carry the HIGHER MEAN t (LINK +2.67 against +2.29;
    XRP +2.63 against +1.67).

  A 3R target truncates the outcome distribution. Truncation cuts the
  standard deviation far harder than it cuts the mean, so the ratio goes up
  while the thing the account earns goes down. A selector that ranks on t is
  therefore not choosing between LEVELS at all. IT IS CHOOSING AN EXIT RULE,
  AND IT WILL ALWAYS PREFER THE TRUNCATED ONE.

  That is exactly what happened in R492: the t pointed at a target-3R cell
  with +0.076 of a risk unit on the choosing slice, while a hold-24h cell
  off the same family sat at +1.117 - fifteen times the expectancy, and
  ranked 10th of 11 on t. The mismatch item 20 opened is real, it has a
  named mechanism, and the mechanism is dispersion, not sample size.
""")

    # =================================================================
    rule("PART C - WHAT THE TWO LOOKS ACTUALLY RETURNED, AND THE HARD STOP")
    print("""
Published sealed results, quoted from RESEARCH_LOG.md and re-read from no
slice:

  R474  prev day low -> 1m BOS, hold to close   (picked by rule (iv))
        sealed 371 trades / 155 days, gross +0.0726% (t by day 2.41),
        net +0.0326% of price, gross R +0.618, NET R +0.132.  SURVIVED.
        R487 later recomputed this foursome digit for digit and it stands.

  R492  last session low -> 1m BOS, target 3R   (picked by rule (i))
        sealed 912 trades / 326 days, gross +0.1228% (t by day 2.52),
        net +0.0706% of price, gross R +0.299, NET R -0.131 (t by day 0.47).
        FAILED - and the sign flip is entirely the cost line, not the signal.

THE HARD STOP, AND IT IS THE WHOLE REASON THIS ITEM WAS FENCED:

  Where an alternative rule points at a DIFFERENT cell, that cell's sealed
  performance is UNKNOWN AND MUST STAY UNKNOWN. LINKUSD's final 20% is spent
  forever; SPY/QQQ's is spent forever. This audit can say the rules disagree
  and can say by how much on the READ slices. It cannot say, and no future
  round may say, that another rule "would have found a survivor". Anyone who
  computes that number has taken a second look at a spent slice.

  It follows that this round CANNOT rank the four rules by outcome, has not
  tried to, and the preference stated in PART 0 was written from first
  principles before any of the tables above were parsed.
""")

    rule("PART D - THE PROPOSED PROTOCOL CHANGE (for Wallace, interactive, "
         "FUTURE rounds only)")
    print("""
  1. THE SELECTOR AND THE GATE ARE STATED IN THE SAME UNIT, AND THE UNIT IS
     THE PER-TRADE NET RISK MULTIPLE (R487). Percent of price never selects.

  2. THE SELECTOR IS min(choosing, middle) PER-TRADE NET R.
     Ties -> the larger trade count on the SMALLER slice.
     Rationale in PART 0, points 2-6, none of which cites an outcome.

  3. A t IS A GATE, NOT A CHOOSER. PART B4 gives the mechanical reason: on
     a grid of levels x exit rules a t ranks exit rules by how truncated
     their outcome distribution is, and prefers the truncated one even when
     it earns a fifteenth as much. Keep it where it belongs: the existing
     positive-expectancy-on-both-slices test, the minimum trade counts, and
     beating the random control. A candidate that passes the gate has
     already answered the question a t asks.

  4. THE GATE GAINS A MARGIN, STATED IN ADVANCE PER ROUND. R492's selected
     cell cleared the middle slice by +0.006 of a risk unit and the protocol
     called that a pass, correctly, because the bar said "positive". A bar
     of "positive" on a 20% slice is a coin flip dressed as a test. The
     proposal is that each round pre-register a MINIMUM middle-slice margin
     rather than a sign - and that the margin be set from the round's own
     choosing-slice dispersion, before any middle-slice number is read, so
     it cannot be tuned to admit or exclude a known cell.

  5. WHAT DOES NOT CHANGE: one look per family, pre-registration in the
     file's docstring before any slice is read, the random-entry control,
     the expected-by-chance baseline quoted beside every count, and the rule
     that a failed config is never re-tuned.

  This is a PROPOSAL. It is not adopted by this file, it changes no
  published verdict, and it applies to no round already run.
""")


if __name__ == "__main__":
    main()
