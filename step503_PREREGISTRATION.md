# R503 — PRE-REGISTRATION OF THE REFERENCE RULE (queue item 38)

**This file is committed to git BEFORE step503_reference_rule.py is written,
run, or debugged, and before any era factor or ordering computed under these
rules exists anywhere on this disk.** Its whole purpose is that the git
timestamp on this commit precedes the timestamp on the first output file, so
the rule below demonstrably was not chosen by looking at the order it gives.
The queue item requires exactly that: *"An estimator picked because it put a
particular instrument on top is the failure mode this item exists to prevent,
so the rule is written down before the ordering is recomputed."*

## What is being fixed

R502 computed an era factor two ways and got two different orderings of the
ranking's top four. The era factor of a row is

        ERA(row | ref) = coord(ref restricted to the ROW's calendar)
                         ---------------------------------------------
                         coord(ref restricted to the POOLED calendar)

R502 named one reference (BTCUSD) for its primary column and took a median
over six dense references for its sensitivity column. The two disagree by up
to 0.126x, every disagreement lands in the top four, and the desk has no
stated reason to prefer either. This round fixes the reference rule in
advance and reports what it gives — whatever it gives.

## The a-priori objection that generates the rule

The estimator above is a ratio of ONE tape's volatility on TWO calendars. It
is a measurement only when that tape actually spans both calendars. Where it
does not, the numerator or the denominator silently becomes a coordinate on
some *other*, shorter calendar, and the ratio stops being an era factor.

R502's median-of-six has this defect in the denominator and it is visible
without computing anything: `era_multi` divides each reference's row-calendar
coordinate by **that reference's own whole fenced window**, and the six
windows are not the same window (DOTUSD runs 2023-08 → 2025-12, AVAXUSD
2021-11 → 2025-08, the other four 2021-01 → 2025-06). Six ratios measured
against six different denominators are not on a common scale and must not be
medianed. That is a defect of construction, established from the windows
alone, and it is the reason a rule is needed. It is not an observation about
which instrument comes out on top.

## THE RULE, FIXED HERE

**Pooled calendar.** `POOLED_DAYS` = the set of UTC days in BTCUSD's fenced
window, R502's definition, inherited unchanged so that this round's ordering
is comparable with R502's. Inherited, not chosen: nothing below may redefine
it.

**Denominator.** For every reference, the denominator is that reference's
coordinate on `POOLED_DAYS`, never on its own private window. This applies to
both rules below.

**RULE 1 — CONTAINMENT (admissibility, then unanimity).**
A reference is ADMISSIBLE for a row when it spans both calendars:

* `A1` it carries bars on ≥ **98%** of `POOLED_DAYS`, and
* `A2` it carries bars on ≥ **98%** of that row's own fenced days,
* and both overlaps are ≥ **120 days** (R502's `ERA_MIN_DAYS`, inherited).

The row's era factor is the **median over its admissible references**.
A row with **no** admissible reference is **UNMEASURABLE** and is given no
era factor at all — item 25's rule, as R502 applied it to ADAUSD.

**The unanimity criterion, part of Rule 1 and fixed here.** A pairwise
ordering between two rows is reported **RESOLVED** only if it holds when the
era factor is taken from **every admissible reference individually**, one
reference at a time. If admissible references disagree about the pair, the
pair is **UNORDERED**. Reason, a priori: an ordering that depends on which
equally-admissible tape was named is not an ordering, and the median would
hide that dependence behind a single number.

**RULE 2 — OVERLAP-WEIGHTED (continuous, no cliff).**
Every dense reference gets weight

        w = (share of the ROW's days it carries)
          x (share of POOLED_DAYS it carries)

and the era factor is the weighted mean. References below R502's inherited
floors (< 120 overlapping days or < 30% of the row's days, either calendar)
get weight zero. Reason, a priori: it makes the same judgement as Rule 1 —
less spanning means less trust — without a threshold that could be tuned.

**Both rules use the SIX dense references R501 already defined**
(`DONOR_MIN_COV` = 80% full behind their own fence). The reference set is
inherited, not selected here.

## THE DECISION, FIXED HERE, BEFORE ANY NUMBER

The queue item accepts either a principled rule (a) or the finding that none
is available (b). The round reports **(a)** if and only if **all three** hold:

1. every one of the ranking's top four rows has a computable era factor
   under Rule 1, **and**
2. Rule 1's unanimity criterion leaves the top four fully ordered, **and**
3. Rule 2's ordering of the top four is **identical** to Rule 1's.

If any of the three fails, the round reports **(b)**: the affected pairs are
published **UNORDERED**, the desk stops quoting an order among them, and the
reason each pair failed is printed. Partial results are reported as partial —
a pair that resolves is published resolved even if its neighbour does not.

## The fence

R493's, unchanged and inherited. `simulate()` is never called, no entry
population is built, no sweep is scanned, no stop is measured, no outcome is
read, and every tape read stops at that instrument's own 80% boundary, the
references' included. No look is consumed and none can be. This corrects a
table; it does not select anything off it, and it does not spend PAXG's or
XRP's intact slice.

## Honest limits, also fixed before running

* The pooled calendar is still BTCUSD's window. Inheriting it keeps this
  round comparable with R502 and does not make it neutral; a different pooled
  calendar is a different question and is not asked here.
* Rules 1 and 2 are two reasonable rules, not the only two. Agreement between
  them is evidence, not proof, that the ordering is reference-free.
* 98% and the weighting form are choices. They are defended above on the
  construction of the estimator, and they are committed here before the
  answer exists, which is the most this round can offer.
* Every reference is itself 80–91% full behind its own fence. That gap shape
  is common to numerator and denominator and divides out of the ratio; it
  does not divide out of the levels, and no level here is anyone's real
  one-minute move.
