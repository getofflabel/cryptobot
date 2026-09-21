# R507 PRE-REGISTRATION — DOES THE DISSENTING REFERENCE TRAVEL WITH THE TAPE, OR WITH THE DENOMINATOR ROLE?

**Queue item 43.** Written and committed **before `step507_reference_role.py`
exists**, before it is run, and before any promoted-calendar era factor, cell,
vote, split or ordering exists anywhere on this disk. Every constant below is
fixed here and none may be changed by this round.

---

## 1. WHAT R506 LEFT ON THE TABLE

R506 placed XRP, DOT and AVAX under FENCE-T and produced **four independently
contested pairs** among the top four, with these splits (copied verbatim out
of R506's published table, and a reproduction target below):

| pair | LINK | DOGE | BTC | ETH | split |
|---|---|---|---|---|---|
| LINK vs XRP | XRP | XRP | **LINK** | **LINK** | 2–2 |
| XRP vs SOL | XRP | XRP | **SOL** | XRP | 3–1 |
| XRP vs PAXG | XRP | XRP | **PAXG** | XRP | 3–1 |
| SOL vs PAXG | SOL | SOL | **PAXG** | **PAXG** | 2–2 |

**BTCUSD is in the minority on all four.** BTCUSD is also the tape whose
fenced window **defines the pooled calendar** that every era factor's
denominator is computed on. That is a double role, and the question is which
half of it produces the dissent.

---

## 2. THE TWO HYPOTHESES, STATED BEFORE THE ANSWER EXISTS

- **H-TAPE:** the dissent is a property of BTC's own tape. Promote any other
  reference to define the pooled calendar and **BTC stays the dissenter**.
- **H-ROLE:** the dissent is a property of being the denominator. Promote
  reference *R* and **_R_ becomes the dissenter**, BTC stops being one.
  *If H-ROLE holds, every era factor published in this log carries a
  structural bias nobody has priced, and item 41 is uninterpretable.*
- **H-MIXED:** neither clean pattern. Reported as mixed, with no adoption.

---

## 3. THE CONSTRUCTION, FIXED HERE

### 3.1 Geometry — INHERITED FROM R506, NOT RE-CHOSEN
The primary reads **FENCE-T exactly as R506 committed it**:
`T_END = PINNED["BTCUSD"]["t80"] = 2025-06-15 06:33:36`, trailing length
**D = 406 days**, one call site (the eleven-instrument ranking screen).
The geometry is held **fixed** across every promotion in the primary, so the
only thing that moves is **which day-set is called the pooled calendar**.
`CONTAIN_MIN = 0.98`, `ERA_MIN_DAYS = 120`, `ERA_MIN_OVL = 0.30`,
`DONOR_MIN_COV = 80.0`, `TOP_N = 4`, R499's fee column frozen — all inherited
verbatim from R501/R502/R503/R506 and none may move.

### 3.2 The promotion set
**Every reference admissible under FENCE-T with BTC pooled** — R506 reports
these as **LINK, DOGE, BTC, ETH** — is promoted in turn. The set is
recomputed in code, not retyped; if the recomputed set differs from those
four the round reports the discrepancy and stops.

### 3.3 The primary swap (ROLE-ONLY)
For each promoted reference *R*: `pooled = tp[R]["days"]`, everything else
byte-identical to R506's `era_matrix`. For each of R506's four contested
pairs, report the admissible-reference set, the per-reference pairwise vote,
the split, and **who is in the minority**.

### 3.4 A DERIVED PREDICTION, COMMITTED BEFORE RUNNING
R506's pairwise comparison for pair (a, b) under reference *r* is
`nmult[a] / cells[a][r] > nmult[b] / cells[b][r]`, and
`cells[x][r] = coord(r on x's overlap) / den[r]`, where `den[r]` is the only
term the pooled calendar enters. **`den[r]` is common to both sides and
cancels.** So the derivation predicts:

> **P-CANCEL:** every pairwise vote sign is INVARIANT to which reference
> defines the pooled calendar. The pooled calendar's only channel into a
> split is the **A1 admissibility gate** — it changes *who is allowed to
> vote*, never *how an allowed voter votes*.

This prediction is committed so the round can be **wrong in public**. It is
checked numerically, cell by cell, not asserted. If any vote sign moves under
promotion while the voter stays admissible, P-CANCEL is **FALSIFIED** and
that is the round's headline.

### 3.5 Declared secondary — THE FULL DOUBLE ROLE
R506 set `T_END` to BTC's pinned fence *because* BTC was the reference. So a
second, confounded swap is reported: promote *R* by **also** setting
`T_END = PINNED[R]["t80"]`. This is a **sensitivity reading only**. Any
promotion whose `T_END` sits later than another row's pin is **clamped by the
read guard and is therefore NOT a clean test of its own geometry** — the same
defect R506 declared on its three short ladder rungs — and must be printed as
unclean. **The verdict comes from the primary alone.**

### 3.6 Reproduction controls — three, all mandatory
1. R499's `vol%` behind the pinned proportional fence: max abs diff
   ≤ 0.0001 pp.
2. R501's `xSAME`, R501's own functions: max abs diff ≤ 0.0015x.
3. **NEW — R506's four contested pairs and their four splits, reproduced
   exactly** from the table in §1. Any mismatch and the round stops: it would
   not be reading the cell item 43 asks about.

---

## 4. THE FENCE

- **Descriptive, ordering only.** `simulate()` is never called and neither is
  any entry builder. No entry population, no sweep, no break of structure, no
  fill, no stop, no outcome, no return, expectancy, win rate, risk multiple or
  t-statistic for any instrument.
- **NO BYTE AT OR PAST AN INSTRUMENT'S PINNED PROPORTIONAL FENCE IS READ**, at
  any promotion, in either the primary or the secondary. Enforced in code by
  R506's hard clamp in `upto()`. PAXG's, XRP's, ADA's, DOT's and AVAX's intact
  slices stay unread.
- **NO LOOK CONSUMED** and none reachable.
- **NOTHING IS ADOPTED.** R503's published table stands whatever this round
  finds: LINK 1st and resolved; places 2–4 UNORDERED {PAXG, SOL, XRP};
  DOGE > BTC > LTC > ETH resolved. No fence is adopted, no calendar is
  adopted, no ordering is republished, no candidate is proposed and nothing is
  deployed.
- **NO FILE ON DISK IS WRITTEN, EXTENDED, MOVED OR TRUNCATED.**
  `FENCES_PINNED.md` is read, never edited.
- **Costs decide nothing** (owner rule, 2026-07-25).

---

## 5. WHAT COUNTS AS THE ANSWER

| observation | conclusion to be written |
|---|---|
| BTC is the minority on all four pairs under **every** promotion | **H-TAPE.** The dissent is BTC's tape. The denominator role is exonerated. |
| the promoted reference becomes the minority | **H-ROLE.** Every era factor in this log is structurally biased; item 41 must not proceed until it is priced. |
| splits change but no clean pattern | **H-MIXED**, reported as such, nothing adopted |
| a vote sign moves while its voter stays admissible | **P-CANCEL FALSIFIED** — headline, and the derivation in §3.4 is wrong |

A promotion that changes the **admissible set** is reported as an
admissibility finding, explicitly distinguished from a change in how a voter
votes. The two are not the same result and will not be written as though they
were.
