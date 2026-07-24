# Round 68 — ROUTER v2: STRICT CONSTRUCTION

R66 proved the scenario CELLS are real (48 HOT cells, train+val-confirmed)
but its OR-union router failed honestly: it was too permissive to actually
concentrate 7/8 tools, and lost to a dumb random-cell control. This round
builds and tests four STRICTER constructions on the SAME 8 tools / same
scenario-cell machinery, reused by import from `step66_scenario_mind.py`
(classifier, 73-cell grid, tool reconstructions, single-slot portfolio
merge, dumb-control mechanism — see that file's own docstring; not
re-typed here). New code lives entirely in `step68_router2.py`: top-K-cell
selection, a 9-cell axis-reduced grid, a stricter sample floor, and
graded-weight sizing, each with its OWN matched dumb-cell control.

Research only — no live orders, no commits. Train-side selection only,
evaluated on val; the sealed final 20% is never touched (inherited
plumbing, same as step66). VAL window: 2024-01-11 → 2025-04-18 (462.5
calendar days, the reference span used for every trades/day figure below).

Outputs: `step68_router2.py` (script), `step68_summary.csv` (portfolio-level
numbers for every construction), `step68_unmerged_detail.csv` (per-tool,
no-slot-competition detail for every construction).

---

## 1. THE REFERENCES (recomputed here, continuity check against R66)

| portfolio | n | exp/t | total return | max DD | trades/day |
|---|---:|---:|---:|---:|---:|
| ALWAYS-ON RACK (unconditional, all 8 tools) | 273 | +$18.67 | +51.0% | -23.2% | 0.590 |
| R66 OR-UNION (train n>=15, exp>0, no cap) | 276 | +$18.62 | +51.4% | -17.9% | 0.597 |

These numbers reproduce R66's own reported figures exactly (n=276,
+$18.62/t, +51.4%, -17.9% for the OR-union; n=273/+$18.67/+51.0%/-23.2%
for the rack) — the reused plumbing is behaving identically, so every
delta below is attributable to this round's NEW construction logic, not
to drift in the underlying engine.

---

## 2. CONSTRUCTION COMPARISON — REAL vs matched DUMB control

| construction | n | exp/t | total return | max DD | trades/day | beats RACK? | beats DUMB? |
|---|---:|---:|---:|---:|---:|---|---|
| **R2a top-1** REAL | 55 | **+$95.30** | +52.4% | **-11.3%** | 0.119 | yes (exp 5x, DD -12pp, ret flat) | **yes, decisively (dumb is negative)** |
| R2a top-1 DUMB | 44 | -$56.46 | -24.8% | -24.8% | 0.095 | — | — |
| R2a top-2 REAL | 78 | +$89.37 | **+69.7%** | -14.3% | 0.169 | yes (ret, exp, DD all better) | mixed (see §2.1) |
| R2a top-2 DUMB | 37 | +$116.61 | +43.1% | -9.3% | 0.080 | — | — |
| R2a top-3 REAL | 98 | +$47.35 | +46.4% | -21.6% | 0.212 | no (ret slightly below rack) | yes (both exp & ret) |
| R2a top-3 DUMB | 104 | +$19.49 | +20.3% | -19.8% | 0.225 | — | — |
| R2b axis-reduced REAL | 212 | +$27.76 | +58.9% | **-24.5%** | 0.458 | yes (ret) | mixed (see §2.2) |
| R2b axis-reduced DUMB | 188 | +$29.97 | +56.3% | -12.2% | 0.407 | — | — |
| R2c sign-gate (n>=25) REAL | 277 | +$26.82 | +74.3% | -17.9% | 0.599 | yes (ret) | **no — loses to dumb on both exp & ret** |
| R2c sign-gate DUMB | 260 | +$34.98 | +91.0% | -18.8% | 0.562 | — | — |
| R2d weighted REAL | 276 | +$12.33 | +34.0% | -19.6% | 0.597 | **no — worse than rack AND R66** | yes (beats its own dumb) |
| R2d weighted DUMB | 276 | +$4.66 | +12.9% | -25.8% | 0.597 | no | — |

**Frequency check (owner's mandate: fails if it fires ~twice a month):**
every construction above clears that bar by a wide margin — even the
sparsest (R2a top-1, 0.119 trades/day) is **~3.6 trades/month**, and top-2/
top-3/R2b/R2c range from ~5 to ~18 trades/month. Frequency is NOT the
limiting factor for any construction tested this round; expectancy/
robustness is.

### 2.1 Why R2a top-2's "beats dumb" call is ambiguous

DUMB's per-trade expectancy ($116.61) is numerically higher than REAL's
($89.37) — but DUMB's dumb draw (fixed seed, matched count=cell-count)
happened to land on only 37 trades vs REAL's 78, so DUMB's total dollar
return (+43.1%) trails REAL's (+69.7%). This is the SAME small-sample
variance mechanism R66 itself flagged for its own dumb-router control
(a lucky narrow draw can concentrate into a few big winners and post a
higher per-trade average on a much smaller n). Read plainly: REAL wins on
the number an owner actually banks (total return), DUMB "wins" on a
thinner, noisier per-trade average. Not a clean pass either way — flagged
honestly rather than rounded to a verdict.

### 2.2 Why R2b's "beats dumb" call is also mixed

REAL edges DUMB on total return (58.9% vs 56.3%) but DUMB has both a
higher per-trade expectancy ($29.97 vs $27.76) AND a much better max
drawdown (-12.2% vs -24.5%, REAL's is the WORST drawdown of every
construction tested this round, worse even than the rack). R2b is not a
clean win over its control.

---

## 3. WHICH CELLS TOP-1 ACTUALLY PICKS (train-ranked, verified against R66's own playbook)

| tool | top-1 cell (by train exp) | train n / exp | val n / exp | holds on val? |
|---|---|---:|---:|---|
| T1 news-momentum | trending-down×violent | 23 / +$49.91 | 6 / **-$50.72** | **FADES** |
| T2 hidden-div | ALL-violent (=vol=violent) | 15 / +$192.83 | 5 / +$145.65 | holds, thin (n<8) |
| T3 CHoCH | trend=trending-down | 26 / +$93.54 | 12 / +$89.52 | **holds, floor-cleared** |
| T4 donchian20 | ranging×normal×newyork | 47 / +$94.34 | 15 / +$93.11 | **holds, floor-cleared** (R66's own flagship cell, exact match) |
| T5 STRIKES | trending-up×violent×asia | 24 / +$163.96 | 6 / +$36.59 | holds, thin (n<8) |
| T6 forensic-short | ALL-violent (=crowded-long×violent) | 48 / +$25.14 | 8 / +$193.25 | **holds, floor-cleared** (R66's own most-concentrated tool, exact match) |
| T7 volshock | crowd=crowded-short | 42 / +$143.79 | 4 / **-$10.78** | **FADES** |
| T8 BB-squeeze | trend=ranging | 66 / +$69.61 | 7 / +$270.20 | holds, thin (n<8, close) |

Every top-1 cell for T2/T3/T4/T6/T8 matches or directly overlaps R66's own
section-3 playbook cells (donchian's ranging+normal+newyork, forensic's
violent+crowded-long, CHoCH's trending-down) — this round's ranking
mechanism independently rediscovers R66's hand-narrated findings, which is
a real cross-check, not a new coincidence.

**The honest catch: 2 of 8 tools' train-BEST cell actively loses on val**
(T1, T7). Both had large, confident-looking train numbers ($49.91/t and
$143.79/t) that did not replicate — textbook train-noise overfitting from
picking "the single best number" without any val-side confirmation baked
into the selection rule itself (train-only selection is the mandate, so
this is expected and disclosed, not a bug). The portfolio-level R2a top-1
win happens DESPITE these two losers, carried by T3/T4/T6/T8's real,
floor-adjacent-or-clearing cells and the merge mechanism naturally giving
more slot-time to bigger, more frequent winners. **A live top-1 router
should drop T1 and T7 from this specific construction** (or require the
picked cell's historical val-analogue, not just train rank, before
trusting it) rather than trust train-rank blindly.

---

## 4. PER-TOOL UNMERGED DETAIL (no slot competition — full table in `step68_unmerged_detail.csv`)

Selected rows (R2a-top1, the round's leading candidate) — solo, no
cross-tool competition for the single slot:

| tool | n_eligible (train) | val n | val exp/t | val ret | val maxDD |
|---|---:|---:|---:|---:|---:|
| T1 | 20 | 6 | -$50.72 | -3.0% | -3.0% |
| T2 | 8 | 5 | +$145.65 | +7.3% | -2.6% |
| T3 | 4 | 12 | +$89.52 | +10.7% | -16.0% |
| T4 | 19 | 15 | +$93.11 | +14.0% | -2.6% |
| T5 | 19 | 6 | +$36.59 | +2.2% | -4.8% |
| T6 | 5 | 8 | +$193.25 | +15.5% | -1.9% |
| T7 | 26 | 4 | -$10.78 | -0.4% | -2.6% |
| T8 | 13 | 7 | +$270.20 | +18.9% | -1.9% |

**Only T4 (n=15) and T6 (n=8) individually clear the program's own
MIN_VAL_TRADES=8 reliability floor with the sign that matters; T3 (n=12)
also clears it and holds positive.** Five of eight tools (T1, T2, T5, T7,
T8) post val samples below or right at that floor under top-1 — the
portfolio number is real (55 merged trades, decisively ahead of a
NEGATIVE dumb control) but its per-tool foundation is currently
concentrated in 3 of 8 tools, not spread evenly across all 8. This is the
single most important caveat for anyone about to spend a sealed look on
this construction.

Full per-tool detail for every construction (R66 baseline, R2a-top1/2/3,
R2b, R2c, R2d) is in `step68_unmerged_detail.csv` — 64 rows, one per
(construction, tool) pair, including n_eligible, val n, expectancy, total
return, max DD, and trades/day.

---

## 5. AXIS RE-TEST AT v2 STRICTNESS

R66's own marginal-axis test (drop every cell referencing one axis, rerun
the router) is repeated here using R2c's mechanism (union of eligible
cells, but with the train floor raised to n>=25 — "v2 strictness"):

| axis removed | n | exp/t | delta vs full R2c | R66's own delta (n>=15) | verdict |
|---|---:|---:|---:|---:|---|
| full R2c (baseline) | 277 | +$26.82 | — | — | — |
| −TREND | 275 | +$38.98 | **+$12.16** | +$0.81 | removal helps MUCH more at v2 strictness than it did in R66 |
| −VOL | 276 | +$22.59 | -$4.23 | -$3.71 | still hurts, near-identical magnitude to R66 |
| −CROWD | 274 | +$16.85 | **-$9.97** | -$4.04 | still the single most load-bearing axis, and hurts MORE at v2 strictness |
| −NEWS | 277 | +$26.82 | $0.00 | $0.00 | zero effect, unchanged (news-hot is one thin cell either way) |
| −SESSION | 278 | +$27.62 | +$0.80 | +$9.00 | **still hurts on net, but the effect shrinks to near-noise (was the single biggest effect in R66, now the smallest non-zero one)** |

**Answer to "does SESSION help or hurt when cells are strict": it still
hurts on net (removing SESSION still improves the router slightly), but
the effect is nearly ELEVEN TIMES smaller than it was at R66's looser
n>=15 floor** ($0.80 vs $9.00). Read together with CROWD's effect getting
STRONGER (not weaker) at the stricter floor, this round's finding
sharpens R66's own conclusion rather than overturning it: **CROWD is the
single most load-bearing axis at every strictness level tested so far**,
VOL is a consistent secondary contributor, NEWS is irrelevant at
portfolio scale, TREND's marginal value flips from negligible to
meaningfully positive-on-removal once the floor tightens (worth a closer
look next round — it may be adding noise specifically in the smaller,
fatter-floor cell population), and SESSION's known "hurts the router
despite carrying real single-cell signal" finding survives but weakens
substantially once cells are forced to be fatter. **This whole axis
re-test is run on R2c, which itself does not beat its dumb control** (see
§2) — so treat these deltas as describing how the axes interact with a
union-style mechanism, not as evidence for R2c's own deployability.

---

## 6. WHY EACH FAILING CONSTRUCTION FAILED, PLAIN ENGLISH

- **R2c (sign-gate, n>=25) barely moved the needle on selectivity** — per-
  tool eligible-cell counts dropped only modestly (T1 20→15, T4 19→13,
  T5 19→15, T7 26→23), so the union still covers nearly the SAME footprint
  as the rack (277 routed trades vs 273 unconditional — a smaller cut than
  even R66's already-too-permissive 276). Raising the floor alone, without
  also capping HOW MANY cells a tool can qualify through, does not fix the
  over-permissiveness R66 diagnosed. This is the clearest confirmation
  that **selectivity has to come from LIMITING THE NUMBER OF CELLS
  (R2a's approach), not from raising the per-cell sample bar (R2c's
  approach)** — the two are not equivalent.
- **R2b (axis-reduced, 9 cells) traded coverage for coarseness the wrong
  way for T3.** Collapsing to CROWD×VOL only strips out T3's entire real
  edge, which R66 and this round's own §3 both show concentrates in
  SESSION (newyork) and TREND (trending-down) — axes this construction
  doesn't have. T3 gets 0/9 eligible cells and is cut completely. The
  construction "wins" its portfolio-return comparison mostly by keeping
  T7's broad, scenario-independent edge (5/9 cells, 94 routed trades) —
  not by concentrating anyone the way R66's playbook says would work.
- **R2d (weighted) actively hurt vs an unweighted OR-union on the SAME
  trade set**, because half-weighting every non-rank-1 trade cuts T7's
  125-trade contribution (the portfolio's single biggest, most reliable
  solo performer, $58.63/t → $27.24/t once halved) far more than it helps
  anyone else. Graded sizing by simple rank does beat RANDOM graded
  sizing (its own dumb control, $12.33 vs $4.66) — rank carries SOME
  information — but the fundamental problem is inherited: R2d never
  changes WHICH trades fire, only how big they are, so it cannot fix a
  trade set that was already too permissive to begin with. Weighting is
  not a substitute for selectivity; it has to be paired with a selective
  trade set (like R2a's), not R66's original union.

---

## 7. VERDICT — RANKED SEALED-LOOK CANDIDATE

**R2a TOP-1-CELL is the one construction that clearly beats both the rack
and its own matched dumb control, with adequate portfolio-level sample
size (n=55) and comfortable frequency (~3.6 trades/month)** — dumb's
matched control is outright NEGATIVE (-$56.46/t, -24.8% return), so this
is not a close call at the portfolio level. Runner-up: **R2a TOP-2**, which
posts this round's best total return (69.7%) and also beats the rack, but
its "beats dumb" claim is muddied by the dumb control's own small-sample
luck (§2.1) — worth a second look, not a clean recommendation on its own.
R2a TOP-3, R2b, R2c, and R2d all fail at least one leg of "beats both rack
and dumb" and are not recommended for a sealed look as built.

**Before spending a sealed look on R2a top-1, the biggest fix to make
first:** drop T1 and T7 from the construction (their train-best cells
demonstrably faded on val, §3) and treat T2/T5/T8's thin (n<8) val
contributions as unconfirmed rather than load-bearing — a version of
top-1 restricted to {T3, T4, T6} (its three individually floor-clearing,
val-confirmed components) is the more defensible next research step
before any live-adjacent test, even though the 8-tool version already
clears the bar this round set out to test.

---

## 8. Caveats, stated plainly

- **This is still train-side selection scored once on one val slice** —
  none of these numbers are sealed-test results. R2a top-1's win is real
  by this round's own floor discipline, but "beats a dumb control on one
  val window" is not the same evidentiary weight as a sealed pass.
- **The per-tool foundation under R2a top-1 is currently narrow** (§4):
  only T3/T4/T6 individually clear MIN_VAL_TRADES=8 with a value that's
  fully consistent with R66's own hand-narrated playbook; the portfolio
  number leans on the merge mechanism smoothing over five thinner or
  negative per-tool contributions.
- **T6's val edge still rides on 8 trades** (identical caveat to R66 —
  unchanged here since top-1 didn't concentrate T6 any further than R66's
  own union already did; ALL-violent/crowded-long/vol=violent are the
  same 48 train bars under either construction).
- **Small-sample dumb-control variance is real and cuts both ways** (§2.1,
  §2.2) — a fixed-seed random draw of a handful of cells can, by chance,
  land on a favorable subset and post numbers that rival or beat the real
  construction on SOME metrics even when it loses on others. Every "beats
  dumb" claim in §2 was checked against BOTH expectancy and total return,
  not just one, specifically to catch this.
- **The axis re-test (§5) is built on R2c, a construction this round
  itself does not recommend** — its deltas describe axis behavior inside
  a union mechanism, not a statement about R2c's own live-worthiness.
- **All 8 tools still run through the ONE shared engine** (day_trade_signal
  + run_backtest, maker execution, real funding) inherited from step66,
  not each tool's own original hand-rolled simulator — same stated
  normalization tradeoff as R66, unchanged here.
- **No sealed test in this round** (train/val only, per the mandate) —
  R2a top-1 is this round's recommended candidate for the NEXT sealed
  look, not a claim that it is already proven.
