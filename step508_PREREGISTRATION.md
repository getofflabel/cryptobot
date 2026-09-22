# R508 PRE-REGISTRATION — DOES A POOLED CALENDAR BUILT FROM THE RANKED ROWS ADMIT A DIFFERENT SET OF REFERENCES?

**Queue item 41, as re-scoped by R507 (2026-09-21).** Written and committed
**before `step508_intersection_calendar.py` exists**, before it is run, and
before any intersection calendar, A1 verdict, era factor, cell, vote, split or
ordering exists anywhere on this disk. Every constant below is fixed here and
none may be changed by this round.

---

## 1. WHY THIS ITEM SHRANK, AND WHAT IS LEFT OF IT

R507 proved **P-CANCEL**: `den[r]`, the only term the pooled calendar enters,
is common to both sides of the pairwise comparison
`nmult[a]/cells[a][r] > nmult[b]/cells[b][r]` and cancels exactly (64 vote
cells, 0 sign changes, worst ratio movement 0.000e+00).

So item 41's original question — *"does a calendar built from the intersection
of the ranked rows reorder the table?"* — **already has an answer: it cannot,
directly.** A different calendar reaches an ordering through exactly one
channel, the **A1 admissibility gate**: it changes **WHO votes**, never **HOW a
voter votes**.

What is left is a census, and one thing R507 could not do. R507's honest limit
was that under every promotion all four references covered **100.0%** of the
promoted calendar, so **A1 never excluded anybody and the one channel by which
the calendar could matter was never exercised.** This round exercises it.

---

## 2. THE CELLS, FIXED HERE

- **PRIMARY CELL — R503's PROPORTIONAL CELL.** Every instrument fenced at its
  own `F.fenced_at(sym)` = `PINNED[sym]["t80"]`. This is the cell R503
  published, the cell the desk quotes, and the cell item 41 was written about
  ("the pooled calendar is BTCUSD's fenced window, inherited from R502 through
  R503"). **The verdict comes from this cell.**
- **DECLARED SECONDARY CELL — R506's FENCE-T.** One shared boundary
  `T_END = PINNED["BTCUSD"]["t80"] = 2025-06-15 06:33:36`, R507's primary
  geometry, reported for continuity with R506/R507's four contested pairs.
  **Nothing is adopted from it and no verdict is taken from it.**

Inherited verbatim and unmovable: `CONTAIN_MIN = 0.98`, `ERA_MIN_DAYS = 120`,
`ERA_MIN_OVL = 0.30`, `DONOR_MIN_COV = 80.0`, `TOP_N = 4`, R499's fee column
frozen. `era_matrix`, `build_rows`, `unanimity`, `profile`, `upto` and
`xsame_column` are **imported from R506 and not re-implemented**; the only
argument this round changes is `pooled`.

---

## 3. THE CALENDARS, FIXED HERE

Within each cell, four pooled calendars are built and compared:

| name | pooled day-set |
|---|---|
| **CAL-BTC** | BTCUSD's day-set behind its fence — the inherited calendar (R502/R503/R506/R507) |
| **CAL-ALL** | the **intersection** of the day-sets of **every live ranked row** in the cell — item 41's literal construction, and the PRIMARY intersection |
| **CAL-DON** | the intersection of the day-sets of the **DONORS** (`cov >= 80.0`) — the rows that can actually serve as references |
| **CAL-TOP4** | the intersection of the day-sets of the **top `TOP_N` rows by `mult*`** — the cell an operational decision is read out of |

A row is "live" exactly as R506 defines it: it has a readable profile behind
its fence and a readable span of at least `ERA_MIN_DAYS`.

### 3.1 THE DEGENERACY RULE, COMMITTED BEFORE ANY SIZE IS KNOWN
A1 is `ov / npool >= 0.98 AND ov >= 120`. For a calendar built as an
intersection over a set containing the donor, `ov = npool`, so A1 collapses to
`npool >= 120`. Therefore:

> Any intersection calendar with **fewer than `ERA_MIN_DAYS` = 120 days** —
> including an **EMPTY** one — is **DEGENERATE**: no donor can pass A1, the
> admissible set is empty, no row carries a Rule 1 era factor and no Rule 1
> ordering exists under it. This is **reported as the census answer** for that
> calendar. Nothing is ranked under a degenerate calendar and the round does
> not fall back to another one to rescue it.

An empty intersection is the extreme case of the same rule and is reported as
a finding, not as an error.

---

## 4. TWO DERIVED PREDICTIONS, COMMITTED BEFORE THE RUN

Both are checked numerically, cell by cell, not asserted.

> **A1-SUP.** For a calendar built as the intersection over a row set `S`,
> every donor **in `S`** covers 100% of pooled by construction, so A1 on those
> donors reduces to the single global test `npool >= 120`. Under **CAL-ALL**
> and **CAL-DON** — where `S` contains every donor — the census is therefore
> **ALL-OR-NOTHING**: every donor passes, or none does. **A partial census
> under either FALSIFIES A1-SUP and is this round's headline.**
> CAL-TOP4 carries no such guarantee (a donor need not be in the top four), so
> a partial census there is expected behaviour, not a falsification.

> **P-CANCEL-2.** For every reference admissible under **both** CAL-BTC and an
> intersection calendar, its vote on every pair is unchanged and the ratio
> `nmult/cell` moves by exactly 0. **Any sign flip in a surviving voter
> falsifies R507's P-CANCEL** and is reported as such.

---

## 5. THE DELIVERABLE, IN THE ORDER IT WILL BE WRITTEN

**(a) THE A1 CENSUS, SIDE BY SIDE.** For each cell: every donor, its coverage
of each calendar, and its A1 verdict, in one table. This is the item's core
deliverable and it is reported whatever it says.

**(b) ONLY IF THE ADMISSIBLE SET DIFFERS** from CAL-BTC's: the resulting Rule 1
and Rule 2 orderings, whether the **top four resolve**, the resolved/unordered
pair list, and an explicit numerical attribution of every change to **ADDED or
REMOVED voters** — never to turned ones, per P-CANCEL-2.
**IF THE ADMISSIBLE SET IS IDENTICAL:** the round says plainly that the two
calendars **cannot** disagree about any pairwise verdict, and stops there.
**That is a complete answer, not a null result** — R507's re-scoping says so in
as many words.

**(c) WHAT THE INTERSECTION DOES TO ERA FACTOR VALUES.** R507 showed the values
are **not** invariant. The full Rule 1 and Rule 2 column under every calendar,
each row's spread (max − min) in R503's own units, set beside **R503's own
adjacent-row gaps in `mult1`**, with an explicit sentence on whether any
published era factor moves by more than the gap that separates its row from
its neighbour. If it does, this round says so and the queue is told that
R503's quotable numbers need a ± attached (item 44's first half).

---

## 6. REPRODUCTION CONTROLS — THREE, ALL MANDATORY

1. R499's `vol%` behind the pinned proportional fence: max abs diff
   ≤ **0.0001 pp**.
2. R501's `xSAME`, R501's own functions: max abs diff ≤ **0.0015x**.
3. **R503's published A1 table and era column, rebuilt in the primary cell**:
   admissible references exactly `LINK, DOGE, BTC, ETH`; `DOT` and `AVAX`
   failing A1; and the Rule 1 / Rule 2 factors
   `PAXG 1.112 / 1.118`, `SOL 1.079 / 1.075`, `XRP UNMEAS / 0.989`,
   `DOT UNMEAS / 0.941`, `AVAX UNMEAS / 0.949`, tolerance **0.0015x**.
   Any mismatch and the round stops: it would not be reading the cell item 41
   asks about.

---

## 7. THE FENCE

- **Descriptive, census and ordering only.** `simulate()` is never called and
  neither is any entry builder. No entry population, no sweep, no break of
  structure, no fill, no stop, no outcome, no return, expectancy, win rate,
  risk multiple or t-statistic for any instrument.
- **NO BYTE AT OR PAST AN INSTRUMENT'S PINNED PROPORTIONAL FENCE IS READ**, in
  either cell, under any calendar. Enforced in code by R506's hard clamp in
  `upto()`. PAXG's, XRP's, ADA's, DOT's and AVAX's intact slices stay unread.
- **NO LOOK CONSUMED** and none reachable.
- **NOTHING IS ADOPTED.** R503's published table stands whatever this round
  finds: LINK 1st and resolved; places 2–4 UNORDERED {PAXG, SOL, XRP};
  DOGE > BTC > LTC > ETH resolved. **No calendar is adopted**, no fence is
  adopted, no ordering is republished, no candidate is proposed, nothing is
  deployed. A calendar that "answers" more pairs is **not** thereby better and
  will not be adopted on that ground.
- **NO DATA FILE IS WRITTEN, EXTENDED, MOVED OR TRUNCATED.**
  `FENCES_PINNED.md` is read, never edited. The only files this round creates
  are its own step file and its own output transcript.
- **Costs decide nothing** (owner rule, 2026-07-25).

---

## 8. WHAT COUNTS AS THE ANSWER

| observation | conclusion to be written |
|---|---|
| admissible set identical under every intersection calendar | the two calendars **cannot** disagree about any pairwise verdict; the census is the complete answer and the ordering half of item 41 is closed without being run |
| admissible set DIFFERS | report the census, then the ordering and the top-four resolution under it, with every change attributed to an added/removed voter and verified numerically |
| a partial census under CAL-ALL or CAL-DON | **A1-SUP FALSIFIED** — headline, and the derivation in §4 is wrong |
| a surviving voter's sign moves | **P-CANCEL FALSIFIED** — headline, and R507's mechanism is wrong |
| an intersection with < 120 days | **DEGENERATE**, reported as the census answer under §3.1, nothing ranked under it |

An admissibility change and an ordering change are **not the same result** and
will not be written as though they were.
