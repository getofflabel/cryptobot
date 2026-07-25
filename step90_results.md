# Round 90 — Mechanizing Round 84's Level-Significance Hypothesis

Round 84's 40 blind chart drills found shorts went 1W/11L (-0.544R avg), and
every losing short broke a NEARBY (local, multi-hour) level after a sharp
move — read as "momentum confirming down," but really the extreme of the
move, not the middle. The one winning short (d018) broke to a genuine new
multi-day low outside the whole prior range. Separately, consolidation near
highs only worked as a continuation setup (d007/d024) when the move
producing it was FRESH, not already extended (d037).

This round tests both ideas MECHANICALLY: every level break on BTC + ETH,
1h + 4h, full cached history, real costs, real funding, chronological
60/20/20 discipline. No commits, no live orders, no network calls, no file
touched outside `step90_level_significance.py` / `step90_results.md` /
`step90_table.csv`.

## Exact operational definitions

**Swing detection.** `step41_shorts.confirmed_swings(d, k)`, reused
verbatim (already this project's standing fractal-swing convention, and
the same helper `chart_reader.py` itself uses). `k=SWING_K=3`: a swing at
bar `i` needs bars `i-3..i+3` and is only knowable starting bar `i+3`
(built into `confirmed_swings`' own `shift(k)`).

**Level tracking / break events** (`scan_structure()`, one causal forward
pass). At every bar `t`: (1) check `t`'s CLOSE against every ACTIVE level
known as of `t-1`'s close — a close beyond it is a BREAK EVENT (long =
close above an active swing high, short = close below an active swing
low); broken levels are removed, never re-broken. (2) for surviving active
levels, a TOUCH is counted if `t`'s high/low came within
`0.25 x ATR14[t]` of the level without closing through it. (3) any swing
newly confirmed at bar `t` joins the active pool for bar `t+1` onward — one
bar more conservative than strictly required, to remove any same-bar
ambiguity. `age_bars = break_idx - formation_idx`; `touches` = count of
qualifying touches between formation and break. Multiple levels can
legitimately break the same bar (a big move can clear several nested local
levels at once); each is its own event with its own age/touch profile.

**Touch tolerance:** `0.25 x ATR14` at the touching bar, chosen over a flat
%-of-price tolerance because BTC traded ~$5k in 2020 and >$100k in 2025 on
this same cached series — a flat tolerance would be far too tight early and
far too loose late. A quarter of the bar's own typical range scales with
the regime.

**No-lookahead, verified by construction AND by test:** `scan_structure()`
and `detect_consolidations()` were run on a 5,000-bar BTC 1h slice and
separately on that slice truncated to 3,000 bars; every event with
`idx < 3000` was byte-for-byte identical between the two runs (`.equals()`
== `True` on both the break-events frame and the consolidation-events
frame, plus the `leg_start_idx`/`atr` arrays). If any future bar leaked
into swing confirmation, touch counting, or leg tracking, truncating the
series would have changed the earlier events; it didn't.

**LOCAL vs STRUCTURAL classification:** `STRUCTURAL` if
`age_bars >= age_cutoff AND touches >= touch_cutoff`, else `LOCAL`. Swept:
`age_cutoff in {20, 50, 100, 200, 500}` x `touch_cutoff in {1, 2, 3}` = 15
combos, independently per (timeframe, direction), selected on **BTC TRAIN
ONLY** by maximizing `(STRUCTURAL expectancy - LOCAL expectancy)` subject
to both buckets clearing `MIN_TRAIN_TRADES=30`. Confirmed once on BTC val.
Any cell that survives BTC (positive expectancy train AND val, `>=30`
train / `>=8` val trades) is mandatorily replayed **unchanged** on ETH.

**Exit rule (one rule, chosen up front, not swept):** pure time exit,
force flat after `MAX_HOLD_BARS = 24` bars on both 1h (24h) and 4h (4
days), per the brief's own suggestion. No stop_pct/target_pct. Rationale:
this round's question is about the entry signal; layering a stop/target
sweep on top would let exit-rule tuning contaminate the level-significance
answer. Costs/execution/funding are otherwise identical to every other
round: `run_backtest(execution="maker", funding_series=<real aligned
funding>)`, `CostModel` defaults untouched.

**Freshness / "consolidation near highs" (fixed definition, NOT swept —
only the cutoff is swept):**
- "Leg start" = formation bar of the most recently formed, still-unbroken
  swing LOW as of bar `t` — literally the same active-low bookkeeping
  `scan_structure()` already tracks for short-side breaks, reused for its
  long-side complement.
- `CONSOL_N=5` consecutive bars, each `(high-low) <= 0.7 x ATR14` ("tight"),
  each bar's LOW within 3% of the leg's rolling high-so-far
  (`CONSOL_NEAR_HIGH_PCT=3.0`).
- The leg itself must be real: `leg_high - low_at_leg_start >= 2.0 x ATR14`
  at the consolidation's start bar (`MIN_LEG_ATR_MULT`), so flat chop never
  qualifies.
- `distance_bars = consolidation_start_idx - leg_start_idx`.
- `distance_atr = (close_at_consolidation_start - low_at_leg_start) /
  ATR14_at_consolidation_start`.
- Entry: long, first bar the window qualifies (`day_trade_signal`'s own
  "ignore repeats while in position" state machine dedupes a persisting
  consolidation exactly like every other signal in this codebase).
- Cutoffs swept independently: bars `{10, 20, 40, 80, 150}`, ATR
  `{2, 4, 6, 10, 15}`; selected on BTC train only (same rule as above),
  confirmed on val, mandatory ETH transfer if it survives.

**Discipline:** `split_points(d)` (step43_daytrade, imported) for the
60/20/20 split. All threshold selection via a dedicated `run_train()` that
only ever slices `[0:i_tr]` — val is not even computed during sweeps. Val
read exactly once per selected config via `score()` (step43_daytrade,
imported). **Test (`[i_va:n]`) is never sliced, scored, or referenced
anywhere in `step90_level_significance.py`** — confirmed by grep, the only
occurrences of `i_va` are the split-point tuple unpack and the docstring.
`MIN_TRAIN_TRADES=30` / `MIN_VAL_TRADES=8`, imported from `step43_daytrade`
— identical floors to every prior round.

## Break-event / consolidation-event volume (sanity check)

| asset | tf | break events (long/short) | consolidation events |
|---|---|---|---|
| BTC | 1h | 11,060 (5,693 / 5,367) | 1,042 |
| ETH | 1h | 9,449 (4,706 / 4,743) | 785 |
| BTC | 4h | 2,684 (1,390 / 1,294) | 274 |
| ETH | 4h | 2,288 (1,142 / 1,146) | 117 |

Plenty of raw events; sample size problems below are about the SWEPT
thresholds cutting into these pools, not data scarcity.

## LOCAL vs STRUCTURAL — full result, split by direction, never pooled

### BTC (selection happened here — train picks the threshold, val confirms once)

| tf | direction | selected threshold | bucket | split | n | expectancy/trade | win% | trades/yr |
|---|---|---|---|---|---|---|---|---|
| 1h | **long** | age>=50, touches>=1 | STRUCTURAL | train | 259 | **+$57.63** | 48.6% | 68.2 |
| 1h | long | | STRUCTURAL | val | 86 | **+$13.85** | 47.7% | 67.9 |
| 1h | long | | LOCAL | train | 742 | -$0.55 | 44.2% | 195.4 |
| 1h | long | | LOCAL | val | 258 | -$2.00 | 43.0% | 203.8 |
| 1h | **short** | age>=20, touches>=2 | STRUCTURAL | train | 340 | -$8.91 | 46.2% | 89.5 |
| 1h | short | | STRUCTURAL | val | 124 | -$7.32 | 46.8% | 97.9 |
| 1h | short | | LOCAL | train | 686 | -$12.91 | 42.6% | 180.6 |
| 1h | short | | LOCAL | val | 223 | -$23.06 | 48.9% | 176.1 |
| 4h | **long** | age>=20, touches>=3 | STRUCTURAL | train | 77 | **+$254.57** | 57.1% | 20.3 |
| 4h | long | | STRUCTURAL | val | 29 | **+$126.10** | 55.2% | 22.9 |
| 4h | long | | LOCAL | train | 190 | -$4.57 | 42.6% | 50.1 |
| 4h | long | | LOCAL | val | 62 | +$109.72 | 54.8% | 49.0 |
| 4h | **short** | age>=20, touches>=1 | STRUCTURAL | train | 95 | -$73.86 | 41.1% | 25.0 |
| 4h | short | | STRUCTURAL | val | 27 | +$68.95 | 55.6% | 21.4 |
| 4h | short | | LOCAL | train | 164 | -$41.00 | 43.3% | 43.2 |
| 4h | short | | LOCAL | val | 58 | -$23.55 | 50.0% | 45.9 |

**Verdicts:** 1h long = SURVIVOR on BTC. 4h long = SURVIVOR on BTC. 1h
short = FAIL (structural never turns positive). 4h short = FAIL
(train/val sign flips — not a real edge, noise).

### The short-side sweep is the important number here — it goes the WRONG way

The brief exists to test R84's claim that aged, well-tested levels are the
*good* shorts and fresh local ones are the noisy ones. Looking at the FULL
BTC 1h short sweep (train), not just the selected combo:

| age_cutoff | touch_cutoff | STRUCTURAL n | STRUCTURAL exp/trade |
|---|---|---|---|
| 20 | 1 | 380 | -$9.23 |
| 50 | 1 | 228 | -$26.21 |
| 100 | 1 | 142 | -$35.49 |
| 200 | 1 | 95 | -$57.70 |
| 500 | 1 | 47 | -$89.12 |

LOCAL shorts hover flat around -$12 to -$13/trade regardless of the
cutoff. **STRUCTURAL shorts get monotonically WORSE as the broken level
gets older and more tested** — the exact opposite of R84's hypothesis. BTC
4h shorts show the identical monotonic pattern (age20/touch1 STRUCTURAL
-$73.86 -> age500/touch1 -$180.15... continuing the same direction as the
cutoff tightens). This is not a threshold-selection artifact; it holds
across the ENTIRE swept grid, both timeframes, both directions of the same
finding: **on this mechanical sample, a well-aged, well-tested support
level finally breaking down is a WORSE short than a level that just formed
and broke immediately, not a better one.**

A plausible reading (speculative, not tested this round): a level that has
been approached and defended multiple times over a long stretch and THEN
finally gives way looks less like "confirmed momentum" and more like
capitulation/exhaustion — structurally close to round 84's own d002
post-mortem ("the picture I was reading as momentum confirming down was,
in hindsight, indistinguishable from a capitulation candle right before a
reversal"). That would flip the intended production rule on its head (fade
the aged structural breakdown rather than trade it), but that is its own
hypothesis and its own round — not something this round tested or is
claiming to have proven.

### Mandatory ETH transfer (only for the two BTC survivors: 1h long, 4h long)

| tf | direction | bucket | split | n | expectancy/trade | win% | trades/yr |
|---|---|---|---|---|---|---|---|
| 1h | long | STRUCTURAL | train | 219 | +$36.99 | 48.4% | 68.1 |
| 1h | long | STRUCTURAL | val | 70 | **-$30.32** | 34.3% | 65.3 |
| 1h | long | LOCAL | train | 617 | -$4.08 | 45.7% | 191.9 |
| 1h | long | LOCAL | val | 217 | -$31.23 | 45.6% | 202.5 |
| 4h | long | STRUCTURAL | train | 63 | +$417.89 | 60.3% | 19.6 |
| 4h | long | STRUCTURAL | val | 23 | **-$85.77** | 34.8% | 21.5 |
| 4h | long | LOCAL | train | 151 | +$93.95 | 55.0% | 47.0 |
| 4h | long | LOCAL | val | 51 | -$54.53 | 37.3% | 47.6 |

**Both BTC long survivors FAIL the ETH transfer** — val goes negative on
ETH for both timeframes, with no re-tuning applied (identical age/touch
cutoffs carried over exactly as required). Worth noting honestly: ETH's
LOCAL bucket *also* goes negative in the same val window on both
timeframes (-$31.23 on 1h, -$54.53 on 4h) — this looks like a bad stretch
for long breakout entries on ETH generally in that window (roughly
mid-2025 to mid/late-2025, ETH's val period), not necessarily proof the
level-significance idea itself is fake. But per this round's discipline
("no re-tuning, report plainly"), the verdict is FAIL regardless of the
hypothesis about cause.

## Freshness result — distance from leg start

| tf | selected cutoff | bucket | split | n | expectancy/trade | win% | trades/yr |
|---|---|---|---|---|---|---|---|
| 1h | distance_atr < 4.0 | FRESH | train | 193 | -$6.76 | 54.4% | 50.8 |
| 1h | | FRESH | val | 85 | -$37.15 | 47.1% | 67.1 |
| 1h | | EXTENDED | train | 39 | -$38.19 | 41.0% | 10.3 |
| 1h | | EXTENDED | val | 12 | -$0.22 | 50.0% | 9.5 |
| 4h | — | **INSUFFICIENT SAMPLE (train)** | | | | | |

On BTC 1h train, the selected cutoff DOES show the hypothesized direction
(fresh -$6.76 beats extended -$38.19) — but neither bucket is ever
profitable, and on val the sign of the gap **reverses** (fresh -$37.15,
worse than extended -$0.22), though the extended-val sample is thin
(n=12, right at the `MIN_VAL_TRADES` floor, not enough to trust the sign).
BTC 4h never cleared 30 trades in both buckets simultaneously at ANY swept
cutoff (best case: 41 fresh trades but 0-9 extended trades — the "extended"
bucket essentially doesn't exist at 4h resolution with this leg
definition) — reported as INSUFFICIENT SAMPLE, not papered over. Since
neither BTC cell survived (positive train AND val), **no ETH transfer was
run for freshness** — there was nothing to transfer.

**A real methodological limitation, stated plainly, not spun:** "leg
start" here is defined as the most recently formed still-active swing low
(reusing the short-side active-level bookkeeping). That level resets very
frequently — a new local low forms and immediately becomes the leg's
reference point even without much structural significance — so the
resulting legs skew short in both bars and ATR-distance, giving very
little dynamic range to actually separate "fresh" from "genuinely
extended, multi-week" moves the way d037's 2930->3670 run was extended.
The bar-distance sweep in particular is nearly useless as constructed:
`EXTENDED` (bar cutoff) drops to 0 samples by cutoff=40 on both timeframes
because almost every qualifying leg is younger than 40 bars under this
leg-start definition. A future round wanting to test this properly should
likely define "leg start" against a longer-horizon or larger-magnitude
swing (e.g. the lowest confirmed swing low in some multi-week lookback,
not just "the most recent unbroken one"), not the level-significance
machinery this round reused for convenience.

## Trades/year — every proposed rule, stated plainly

| rule | trades/yr (train) | trades/yr (val) | thin (<~20-30/yr)? |
|---|---|---|---|
| BTC 1h long STRUCTURAL (age>=50,touch>=1) | 68.2 | 67.9 | no |
| BTC 1h short STRUCTURAL (age>=20,touch>=2) | 89.5 | 97.9 | no (but FAILED anyway) |
| BTC 4h long STRUCTURAL (age>=20,touch>=3) | 20.3 | 22.9 | **yes, borderline** |
| BTC 4h short STRUCTURAL (age>=20,touch>=1) | 25.0 | 21.4 | **yes, borderline** (FAILED anyway) |
| ETH 1h long STRUCTURAL (transfer) | 68.1 | 65.3 | no (but FAILED val) |
| ETH 4h long STRUCTURAL (transfer) | 19.6 | 21.5 | **yes, borderline** (FAILED val) |
| BTC 1h freshness FRESH (distance_atr<4) | 50.8 | 67.1 | no (but never profitable) |
| BTC 1h freshness EXTENDED (distance_atr<4) | 10.3 | 9.5 | **yes, thin** (but never profitable) |

The only rule that would have been deployable on trade frequency AND
expectancy grounds — BTC 1h long, STRUCTURAL breaks, age>=50/touches>=1 —
is exactly the one that fails the mandatory ETH check.

## Final verdict

**Does the STRUCTURAL-vs-LOCAL distinction measurably beat, mechanically,
at scale, after costs? Direction-dependent, and the answer for the
direction R84 actually flagged is a clean NO.**

- **Long side:** yes on BTC, both timeframes, with a clean monotonic
  pattern across nearly the whole sweep grid (STRUCTURAL longs positive,
  LOCAL longs roughly flat-to-slightly-negative) — but it does **not**
  survive the mandatory, no-re-tuning ETH transfer on either timeframe.
  Per this round's discipline that is a FAIL, full stop, not a "soft
  positive." It's a real BTC-specific pattern worth another look with a
  longer ETH history or a third asset before it's trusted, but it is NOT
  ready to hardcode.
- **Short side (the one R84 was actually about):** REFUTED. Aged,
  well-touched broken support is a *worse* short than a fresh local break
  on this mechanical sample, monotonically, on both BTC timeframes. R84's
  40-drill read ("local breaks are noise, structural breaks are
  tradeable") does not generalize to shorts at scale — if anything the
  data points the opposite direction for shorts specifically.
- **Freshness (distance from leg start):** no support. Never profitable in
  either bucket on the only cell with enough sample to even test (BTC 1h),
  and the one train-favorable gap reverses on val. BTC 4h couldn't be
  tested at all — the leg-start definition produced too few "extended"
  events to clear the sample floor.

**Recommendation for `chart_reader.py`: do not implement any change this
round.** Concretely, for `_location()` / `read_chart()`:

1. **Do NOT add a "structural break = tradeable short" heuristic.** The
   mechanical evidence says the opposite for shorts on this sample — adding
   it would encode a directionally wrong bias into the eye.
2. **Do NOT add a "structural break = tradeable long" heuristic either**,
   despite the promising BTC-only numbers, because it failed the ETH
   transfer this round is required to run before anything graduates. If a
   future round wants to revisit it, the exact spec to re-test is: a new
   `_level_age_bars(closed_df, level_price, k=3)` helper reporting
   `(age_bars, touches)` for whichever swing high/low is currently being
   broken (reusing `confirmed_swings` exactly as this file did), with
   `STRUCTURAL = age_bars >= 50 and touches >= 1` gating the existing
   `"breaking out"` location label to a new `"breaking out (structural)"`
   vs `"breaking out (local)"` split — but only after it clears a second
   independent asset or a longer OOS window than this round had, since ETH
   ran cold here.
3. **Do NOT add a freshness/distance-from-leg-start gate** to the bull-flag
   read. No mechanical support was found, and the one cell with enough
   sample to test showed no profitable bucket in either direction.

## Honesty notes / limitations

- The age/touch threshold selection rule (maximize train
  `STRUCTURAL - LOCAL` expectancy gap, subject to both clearing 30 trades)
  is one reasonable choice, not the only one; a different selection
  objective (e.g. maximize absolute STRUCTURAL expectancy alone, or
  require LOCAL to be strictly negative) could plausibly have picked
  different cutoffs. Restated: the full sweep grid is in `step90_table.csv`
  (`section == "level_sweep"`) for anyone who wants to re-derive under a
  different selection rule.
- BTC 4h cells are thin by construction (13,863 total 4h bars vs 55,493 1h
  bars) — the 4h long "survivor" (77 train / 29 val trades) clears the
  floors but only barely, and its trades/year (~20-23) is genuinely on the
  thin side even before considering it failed ETH.
- The touch tolerance (0.25xATR) and the freshness/consolidation
  definition (N=5, 0.7xATR tight, 3% near-high, 2xATR minimum leg) are
  judgment calls, stated explicitly per the brief's instruction, and were
  NOT themselves swept — only the classification cutoffs were, exactly as
  the brief specified.
- Level-break events on the SAME bar are recorded as independent events
  even when multiple nested levels break simultaneously (documented
  behavior in `scan_structure()`'s docstring, not a bug) — this means a
  single violent bar can contribute several correlated observations to the
  break-event population, a mild form of non-independence across events
  that this round did not attempt to correct for (matches how the rest of
  this codebase's event-based signals already work, e.g. multiple stacked
  swing levels in `step86_specified.py`'s `swing_level_pool`).
- Every backtest in this file uses `execution="maker"` and real funding
  (`align_funding`), matching this project's established convention —
  nothing here uses a cost-free or simplified fill model.
- Test (`[i_va:n]`) was never touched by any line of this file — confirmed
  both by design (only `run_train`/`score` calls appear, both bounded by
  `i_tr`/`i_va`) and by grep (the only `i_va` occurrences are the
  split-point unpack and this file's own docstring).

## Files

- `step90_level_significance.py` — the harness: `scan_structure()` (level/
  break/touch/leg-start tracking, one causal forward pass, no-lookahead
  verified by truncation test), `detect_consolidations()` (freshness
  feature), the train-only sweep + val-confirm + ETH-transfer pipeline for
  both hypotheses.
- `step90_table.csv` — every row: the full 15-combo x 2-direction x
  2-timeframe level-significance sweep (train only, `section ==
  "level_sweep"`), the selected configs' train+val (`level_selected`), the
  mandatory ETH replay (`level_eth_transfer`), the freshness sweep
  (`fresh_sweep`), its selected config (`fresh_selected`) — 188 rows total.

No commits made, no live orders placed, no network calls made (all four
candle parquets and both funding parquets loaded from existing cache,
confirmed via the loader print lines showing "from cache" for every file)
— research only, per the brief.
