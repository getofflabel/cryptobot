# R506 — PRE-REGISTRATION OF THE TRAILING-DAYS FENCE (queue item 39)

**This file is committed to git BEFORE `step506_trailing_fence.py` is written,
run or debugged, and before any fenced window, coverage figure, coordinate,
era factor or ordering computed under the rule below exists anywhere on this
disk.** Its whole purpose is that the git timestamp on this commit precedes
the timestamp on the first output file, so the fence demonstrably was not
chosen by looking at the ranking it gives. This is R503's shape, deliberately,
and queue item 39 asks for exactly it: *"write the rule down FIRST, in a
committed file, exactly as R503 did — which fence, what trailing length, what
happens to instruments whose tape is shorter than it, and the decision rule
for what counts as a better fence, fixed before the resulting ordering is
computed."*

## What is being fixed

`step489.cut80` fences a tape at `t0 + (t1 − t0) × 0.80` — it keeps a fixed
**PROPORTION** of each instrument's own span. R504 proved that this shape, and
not the disk, is why four rows of the ranking (XRP, DOT, AVAX, ADA) carry no
era factor: R503's Rule 1 needs one reference to cover ≥98% of the pooled
calendar (A1) **and** ≥98% of the row's own fenced days (A2), and under a
proportional fence a reference that starts earlier than a row also *fences*
earlier than it, by `(1 − f)` of its head start. The two demands name disjoint
sets of start dates and stay disjoint until 2036 (AVAX), 2061 (XRP, DOT) and
2100 (ADA) even on a perfectly dense idealised tape.

R504 named three routes out and exercised none. This is route (a):

> *"a fence that keeps a fixed number of trailing DAYS instead of a fixed
> proportion, which makes every tape's admissible region end on the same date
> — and changes the size of every sealed slice in this log."*

A2 becomes satisfiable by construction under such a fence, because every
instrument's readable region ends at the same instant, so any reference that
starts before a row covers the row's window entirely. Whether that **resolves
the top four** is a different question and is the one this round answers.

## THE FENCE, FIXED HERE

**FENCE-T (trailing-days).** The readable region of instrument *i* is

        [ t0_i , T_END )        with T_END the SAME instant for every i.

`t0_i` is that instrument's own first bar, unchanged. Nothing else about
R501's `fenced()` changes: same `<` comparison, same columns, same order.

**THE TRAILING LENGTH, and why this one.**

        T_END := PINNED["BTCUSD"]["t80"]  =  2025-06-15 06:33:36 UTC

taken verbatim out of `FENCES_PINNED.md` (R505, committed 2026-09-18), which
is a **date on disk and not a formula**, so it cannot move under the fence
being tested. Equivalently, the trailing length is

        D := BTCUSD's file end − T_END  =  2026-07-26 18:42:00 − T_END
          =  406 days 12:08:24,  i.e. **406 trailing days**,

and because all eleven ranked 1-minute files end on the same day
(2026-07-26 — R504's table, re-verified by this round from the pin), a common
`T_END` and a fixed trailing day-count are the same fence here. Both forms are
printed; if they ever disagree the common-`T_END` form is primary, because the
item's stated aim is *"every instrument's readable region ending on the same
date."*

**The a-priori reason for THIS length, and it is not about the answer.**
BTCUSD's fenced window **is** the pooled calendar. R502 chose it, R503
inherited it unchanged, R504 inherited it again, and every era factor in the
ranking is a ratio whose denominator is a reference's coordinate on it.
Setting `T_END` to BTC's own pinned fence leaves the **pooled calendar
literally unchanged, to the second**. The denominator every row is divided by
therefore does not move at all, and any change in the ordering comes from the
ROWS and from nothing else. A trailing length picked anywhere else would move
the denominator and the rows at the same time, and no one could say which did
the work. This is a property of the estimator, it is checkable before any
number exists, and it is the entire justification.

**Scope, and it is narrow.** FENCE-T is pre-registered for ONE call site: the
eleven-instrument ranking screen (`step489.cut80` as used by R499/R501/R502/
R503/R504). **The two arm clocks are NOT re-fenced** — `crypto_1m_R476`,
`crypto_1m_R450` and `index_1m_R474` keep the dates pinned in
`FENCES_PINNED.md`, SPY and QQQ are out of scope entirely, and this round does
not touch, import or recompute them.

## WHAT HAPPENS TO AN INSTRUMENT WHOSE TAPE IS SHORTER THAN THE FENCE

Fixed here, before it is known which rows this catches:

1. **`t0_i ≥ T_END` → UNFENCEABLE.** The readable region is empty. The row
   carries no coverage, no coordinate, no era factor and **no rank**, and it
   is reported as dropped by name with its first bar printed. It is not
   quietly omitted and it is not given a shorter fence of its own — a
   per-instrument exception is the proportional fence again.
2. **readable span < `ERA_MIN_DAYS` (120 days, R502's floor, inherited) →
   UNFENCEABLE**, same treatment.
3. **A reference must clear the same bars.** The donor set is R501's rule
   inherited unchanged (`DONOR_MIN_COV` = 80.0, i.e. the reference's own
   fenced tape is ≥80% full) and is **recomputed behind FENCE-T**. Any change
   of membership is reported before any era factor is read.
4. Everything else in R503's Rules 1 and 2 — A1 = 98%, A2 = 98%, both
   overlaps ≥120 days, the median over admissible references, the
   overlap-weighted mean, `ERA_MIN_OVL` = 0.30 — is **inherited verbatim** and
   may not be changed by this round. R504's bar stands: loosening 98% after
   seeing which rows drop out is barred.

## THE READ BOUNDARY — WHY NO LOOK IS REACHABLE UNDER EITHER FENCE

Every tape read in this round stops at

        READ_BOUNDARY(i) := min( pinned proportional fence(i) , T_END )

so no byte past **either** fence is read on any instrument. PAXG's, XRP's,
ADA's, DOT's and AVAX's intact slices stay intact under the proportional
fence, and FENCE-T is nowhere later than it (verified in part 2, not
assumed). `simulate()` is never called and neither is any entry builder: no
entry population is built, no sweep scanned, no break of structure detected,
no fill modelled, no stop measured, no outcome, return, expectancy, win rate,
risk multiple or t-statistic computed for any instrument. **No look is
consumed and none is reachable.**

## THE DECISION RULE — WHAT COUNTS AS A BETTER FENCE

Fixed here, before the ordering under FENCE-T exists. FENCE-T is reported
**BETTER** than the proportional fence if and only if **all four** hold.

**P1 — PLACEMENT.** Every one of the top four rows of the FENCE-T ranking
carries a Rule 1 era factor. *(R503's condition 1, verbatim.)*

**P2 — RESOLUTION.** R503's unanimity criterion — the pair holds under every
admissible reference taken one at a time — leaves the top four fully ordered.
*(R503's condition 2, verbatim.)*

**P3 — AGREEMENT.** Rule 2's top four is identical to Rule 1's.
*(R503's condition 3, verbatim.)*

**P4 — ADMISSIBILITY OF THE FENCE ITSELF.** All three of:

* **(a) NO UN-SPENDING.** FENCE-T moves no pinned boundary LATER into a region
  a round has SPENT. Un-spending a slice by re-fencing is barred by queue item
  39's own clause and by `FENCES_PINNED.md`. Checked instrument by instrument
  against the pin and reported in days, never assumed.
* **(b) NO MATERIAL PRE-CONTAMINATION.** Where FENCE-T moves a boundary
  EARLIER, tape that was readable becomes "sealed". That is false labelling
  wherever a round has already **spent a look** on the re-sealed region —
  R492 on LINK and XRP, R475 on the crypto arm, R474 on the index. Measured
  in DAYS of re-sealed tape per instrument and **material at ≥ 1 day**. A
  boundary that slips by minutes is reported and is not material; a boundary
  that re-seals weeks of a window a sealed-look round already READ is.
* **(c) NO ROW LOST.** No instrument that carries a rank under the
  proportional fence becomes UNFENCEABLE under FENCE-T.

**The verdicts, and all three are fixed here:**

| outcome | verdict |
|---|---|
| P1 ∧ P2 ∧ P3 ∧ P4 | **BETTER** — FENCE-T resolves the top four at no bookkeeping cost. |
| P1 ∧ P2 ∧ P3, ¬P4 | **ORDERING IMPROVED, FENCE INADMISSIBLE** — the fence buys an order by re-labelling read tape or losing a row, and is **not** adopted. Named explicitly so a good answer cannot buy a bad fence. |
| ¬(P1 ∧ P2 ∧ P3) | **NOT BETTER** — the proportional fence stands and places 2–4 stay UNORDERED. |

**NOTHING IS ADOPTED BY THIS ROUND UNDER ANY OUTCOME.** The item's own fence
says *"the ordering is recomputed, nothing is selected off it."* R503's
published table — LINK 1st, {PAXG, SOL, XRP} unordered, DOGE > BTC > LTC >
ETH resolved — **stands as the desk's table whatever this round finds.**
Adopting a fence is a separate decision, it would move sealed-slice sizes
across the whole log, and it is not on this round's ticket.

## THE SENSITIVITY LADDER — DECLARED HERE, AND IT IS NOT A SELECTOR

The verdict above is taken from the primary `T_END` **and from nothing else.**
To show whether it is knife-edge, the same machinery is run at a fixed,
declared ladder of trailing lengths

        D ∈ { 180, 270, 365, **406 (primary)**, 540 } days

measured back from BTCUSD's file end, with `D = 406` being the primary by
construction. The ladder is printed with P1–P4 evaluated at each rung. **No
rung other than the primary may supply a verdict, an ordering the desk
quotes, or a fence anyone adopts**, and a rung that "works better" is a
finding about sensitivity, not a licence to move the primary. Picking the D
that answers is precisely the failure mode items 38 and 39 exist to prevent.

## REPRODUCTION CONTROLS, BOTH REQUIRED BEFORE ANYTHING NEW IS COMPUTED

As in R502, R503, R504 and R505, and the round **stops** if either fails:

* R499's `vol%` column recomputed behind the pinned proportional fence: max
  absolute difference must be ≤ 0.0001 pp on all eleven rows.
* R501's `xSAME` column recomputed with R501's own functions: max absolute
  difference must be ≤ 0.0015x.

If the disk is not the one R501/R502/R503 read, nothing below it means
anything.

## HONEST LIMITS, ALSO FIXED BEFORE RUNNING

* **A common end date is a choice, not a neutral act.** It equalises the
  END of every readable region and leaves the START alone, so it makes rows
  comparable in one direction only. A fence equalising both would be a third
  question and is not asked here.
* **FENCE-T shortens tape; it never lengthens it.** Because `T_END` is the
  earliest pinned crypto fence by construction, every row either keeps its
  window or loses the tail of it. Rows that lose a lot lose statistical
  precision that this round does not attempt to price.
* **The trailing length is defended on the estimator, not on the ordering,**
  and that is the most this round can offer. It is not proof that 406 days is
  the right length; it is proof that 406 days was not chosen by looking.
* **A fence that places a row is not a fence that measures it well.** A2
  passing by construction means every reference now spans every row — which
  is exactly what makes the era factor computable, and exactly why the
  resulting factors deserve less credit than a reference that spanned the row
  because the tape really overlapped.
* **The ranking's fee column is R499's, frozen**, as in R501, R502 and R503.
  The only thing this round is allowed to move is the fence.
* **Costs decide nothing** (owner rule, 2026-07-25). Nothing here declines a
  trade, gates a strategy or ranks an instrument for trading.
