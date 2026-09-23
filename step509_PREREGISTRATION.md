# R509 PRE-REGISTRATION — A CALENDAR THAT EXCLUDES *SOME* REFERENCE, AND WHETHER A SPLIT MOVES BY LOSING A VOTER OR BY TURNING ONE

**Queue item 44, second half, as re-scoped by R508 (2026-09-22).** Written and
committed **before `step509_exclusion_calendar.py` exists**, before it is run,
and before any exclusion calendar, A1 verdict, era factor, cell, vote, split or
ordering exists anywhere on this disk. Every constant and every construction
below is fixed here and none may be changed by this round.

---

## 1. WHAT IS LEFT OF ITEM 44, AND WHY THIS IS THE WHOLE OF IT

Item 44's **first half is ANSWERED and must not be re-run.** R508 measured how
far the era factor VALUES move under a calendar that genuinely moves the
denominator: a **common scale factor of 1.0774x**, per-row residuals
1.0000–1.0017, four of seven rows moving further than their neighbour gap in
absolute terms while the largest non-common `mult1` move is **0.003**. The
answer to *"do R503's numbers need a ±"* is **YES for the quoted value and NO
for the ordering.** Nothing in this round re-opens that.

**What is left is the second half, and R508 named it exactly:**

> build a calendar that **excludes SOME reference under A1** and confirm a
> split can move there — **by removing a voter, never by turning one.**

R507 could not exercise this: under every promotion all four references covered
**100.0%** of the promoted calendar, so A1 never excluded anybody. R508 could
not either: its three intersection calendars were **too blunt** — CAL-ALL and
CAL-TOP4 exclude everybody by being empty, CAL-DON excludes nobody. **A strict,
non-empty exclusion has never been built on this disk.** This round builds one
by rule, or reports plainly that the rule cannot produce one here.

---

## 2. THE CELLS, FIXED HERE

- **PRIMARY CELL — R503's PROPORTIONAL CELL.** Every instrument fenced at its
  own `F.fenced_at(sym)` = `PINNED[sym]["t80"]`. This is the cell R503
  published and the cell the desk quotes. **The verdict comes from this cell.**
- **DECLARED SECONDARY CELL — R506's FENCE-T.** One shared boundary
  `T_END = PINNED["BTCUSD"]["t80"]`. Reported for continuity with R506/R507/R508.
  **Nothing is adopted from it and no verdict is taken from it.**

Inherited verbatim and unmovable: `CONTAIN_MIN = 0.98`, `ERA_MIN_DAYS = 120`,
`ERA_MIN_OVL = 0.30`, `DONOR_MIN_COV = 80.0`, `TOP_N = 4`, R499's fee column
frozen. `era_matrix`, `build_rows`, `unanimity`, `profile`, `upto` and
`xsame_column` are **imported from R506 and not re-implemented**; `under()` and
`intersect()` are imported or copied from R508 unchanged. The only argument
this round varies is `pooled`.

---

## 3. THE BASELINE, FIXED HERE

The comparison baseline for an EXCLUSION is the calendar that admits the
**widest** reference set, because "exclusion" is only meaningful relative to
who would otherwise vote. R508 measured that to be **CAL-DON** (the
intersection of the donors), which admitted **6** references against CAL-BTC's
4. Therefore:

- **BASELINE = CAL-DON** = `intersect(donors)`.
- **CAL-BTC is carried in every table as the published-table control**, and as
  a reproduction check: it must reproduce R503 digit for digit or the round
  stops.

A calendar is an **EXCLUSION CELL** iff its admissible set is a **strict,
non-empty subset** of CAL-DON's admissible set.

---

## 4. THE TWO FAMILIES, FIXED HERE — BOTH DEFINED BY RULE, NEITHER CHOSEN FOR ITS ANSWER

Neither family is selected, filtered or ordered by what it produces. Both are
run in full and reported in full, including the members that are degenerate,
empty or identical to the baseline.

### FAMILY A — LEAVE-ONE-OUT OVER THE DONORS (the primary family)

For **each donor `d`**: `CAL-LOO(d)` = the intersection of the day-sets of
**every donor except `d`** — *"the calendar the other rows agree on."*

This is the natural exclusion construction and the reason is arithmetic, not
hope: dropping `d`'s constraint can only **enlarge** the intersection, and the
days it adds are exactly the days `d` lacks.

### FAMILY B — SELF-PROMOTION OVER EVERY LIVE RANKED ROW (the breadth family)

For **each live ranked row `r`** (donor or not): `CAL-SELF(r)` = that row's own
fenced day-set. `CAL-SELF(BTCUSD)` is `CAL-BTC` by construction and is the
family's own built-in reproduction control.

---

## 5. THE PREDICTIONS, COMMITTED BEFORE THE RUN — THIS ROUND CAN BE WRONG IN PUBLIC

### P-LOO — an EXACT arithmetic prediction about Family A

Let `D* = |CAL-DON|`. For `CAL-LOO(d)`:

1. For **every donor `d' ≠ d`**: `CAL-LOO(d) ⊆ d'.days` by construction, so
   `ov = npool` and **`a1_ok[d'] = (npool >= 120)` — coverage is exactly
   100.0%.**
2. For **the left-out donor `d` itself**: `d.days ∩ CAL-LOO(d)` is the
   intersection of **all** donors, which is `CAL-DON`. Therefore its coverage
   is **exactly `D* / |CAL-LOO(d)|`**, and
   **`a1_ok[d] = (D*/|CAL-LOO(d)| >= 0.98 AND D* >= 120)`.**

**P-LOO is falsified** if any donor's measured A1 coverage under any
`CAL-LOO(d)` differs from the two formulas above by more than 1e-9.

### P-EXCL — the existence claim

**At least one member of Family A or Family B is an EXCLUSION CELL** (admissible
set a strict, non-empty subset of CAL-DON's). **Falsified** if every member is
either identical to the baseline, empty, or degenerate. A falsification is a
complete and publishable answer — it would say that under the pinned fences on
this disk **no rule-built calendar can remove a single voter without removing
them all**, and item 44 would close on that.

### P-TURN — the item's actual question, and the one that matters

In **every** exclusion cell, for **every** ordered pair `(a,b)` and **every**
reference `r` admissible for both rows under **both** the baseline and the
exclusion cell:

- **the vote sign is unchanged** (this is P-CANCEL, now exercised against a
  calendar that genuinely removes a voter rather than one that only rescales
  the denominator), **and**
- **every change in a pair's RESOLVED/UNORDERED verdict is fully attributed to
  the removed reference** — i.e. re-running the baseline's own vote set with
  the removed reference struck out reproduces the exclusion cell's verdict for
  that pair, exactly.

**P-TURN is falsified** by a single surviving voter's sign changing, or by a
single pair whose verdict moves in a way that striking the removed voter out of
the baseline's votes does not reproduce.

### The direction claim, committed so it cannot be discovered afterwards

Removing a voter can move a pair only in these ways, and no others:
`UNORDERED → RESOLVED` (the removed voter was a dissenter),
`RESOLVED → UNORDERED` (the removal left **no** reference admissible for both
rows), or no change. **A pair that goes `RESOLVED(direction X) → RESOLVED(direction
not-X)` falsifies P-TURN** and is a headline.

---

## 6. THE DEGENERACY RULE, COMMITTED BEFORE ANY SIZE IS KNOWN

Inherited unchanged from R508. A1 is `ov/npool >= 0.98 AND ov >= 120`. Any
calendar with **fewer than `ERA_MIN_DAYS` = 120 days** cannot admit any donor
whose day-set contains it, so **nothing is ranked under it and nothing falls
back to rescue it.** Degenerate members are reported with their day counts and
carried no further.

---

## 7. REPRODUCTION CONTROLS — IF ANY FAILS THE ROUND STOPS AND PUBLISHES NOTHING

1. R499's `vol%` column rebuilt behind the pinned fence, max absolute
   difference `<= 0.0001` pp.
2. R501's `xSAME` column rebuilt with R501's own functions, max absolute
   difference `<= 0.0015x`.
3. R503's proportional cell under CAL-BTC: admissible set exactly
   `{LINK, DOGE, BTC, ETH}`, donors failing A1 exactly `{DOT, AVAX}`, and
   R503's full published era column reproduced to `1.5e-3`.

---

## 8. THE FENCE — INHERITED, AND ENFORCED AS CODE DISCIPLINE

1. **`simulate()` IS NEVER CALLED** in this round, and neither is any entry
   builder. No sweep is scanned, no break of structure detected, no fill
   modelled, no stop measured, no outcome, return, expectancy, win rate, risk
   multiple or t-statistic computed for anything. The only things read off tape
   are **(a) which minutes carry a bar** and **(b) the size of a one-minute
   move**.
2. **NO BYTE AT OR PAST AN INSTRUMENT'S PINNED PROPORTIONAL FENCE IS READ**
   anywhere in this file, under any calendar, in either cell. R506's hard clamp
   in `upto()` is re-used unchanged. PAXG's, XRP's, ADA's, DOT's and AVAX's
   intact sealed slices stay intact.
3. **NOTHING IS SELECTED AND NOTHING IS ADOPTED.** R503's published table
   stands whatever this round finds: **LINK 1st and resolved; places 2–4
   UNORDERED {PAXG, SOL, XRP}; DOGE > BTC > LTC > ETH resolved.** A calendar
   that resolves more pairs is **not** thereby better and is not adopted on
   that ground. No ordering is republished, no fence moves, no threshold moves.
4. **NO DATA FILE ON DISK IS WRITTEN, EXTENDED, MOVED OR TRUNCATED.**
5. **NO LOOK IS CONSUMED** and none is reachable.
6. **Costs decide nothing** (owner rule, 2026-07-25).
7. **Nothing is proposed for deployment** under any outcome.

---

## 9. DECLARED IN ADVANCE

Any block added to the output after the committed run has produced its numbers
will be marked **POST-HOC REPORTING ADDITION, DECLARED** in both the output and
the log entry, and may only **explain** a number the committed run already
produced. It may not change a measurement, threshold, calendar, construction or
verdict.
