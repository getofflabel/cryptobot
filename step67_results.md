# Round 67 — Scalping the Quiet Tape (research only, no commits, no live orders)

**Owner's synthesis:** "swing trading needs market action; right now BTC has
none; look into scalping." **Thesis under test:** range scalping is the calm
regime's native family — it should fire ONLY when the tape is calm (the
mirror image of every trend tool's vol gate) — and it should be evaluated
under the same cost discipline that has killed this family five times before
(rounds 4-8, 39, 41, 43, 45A).

**Bottom line up front:** the cost floor killed it a **sixth time**. Zero
configs clear the deployable taker-taker bar. Zero configs clear the
aspirational maker-maker bar with an adequate sample. One family
(range-edge fade) shows a real gross edge before costs, but on a sample so
thin (7-9 trades per asset over 6 years) that it collapses on validation —
a methodology flaw in this round's "real range" filter, diagnosed below, not
a genuine edge. The calm gate did **not** help — on the two well-sampled
families (S2, S3, S4; hundreds to thousands of trades each) calm-gated
expectancy was *worse* than ungated in every single case. The owner's
regime-router thesis, as specifically implemented here, is **not confirmed**
by this round's evidence.

Script: `step67_scalp.py`. Raw grid: `step67_results_raw.csv` (224 rows) +
`step67_touch_proxy_raw.csv` (fill-probability proxy, 56 rows).

---

## 1. Data

- BTC-USDT and ETH-USDT, Bybit perp history, all from cache (no network
  calls): 15m (BTC 221,972 bars back to 2020-03-25; ETH 187,934 bars back to
  2021-03-15), 1h (context/gate), funding settlements (both symbols).
- BTC 5m is *also* cached back to 2020-03-30 (~6.3 years, far beyond the
  18-24mo ask), but this round's four families are specified at 15m
  resolution per the brief. **A 5m variant was not built this round** — see
  Caveats §7 for why (the repo's own prior finding: candle edges decay with
  resolution, "profit-per-trade shrinks into fixed costs while signal
  weakens" — RESEARCH_LOG round "15m forensic autopsy," ~9.2bps cost vs
  ~3bps edge at 15m already; 5m would be worse before even running it,
  and this round's 15m results already show no edge clearing costs, so a
  5m pass would only confirm the same floor at a steeper angle).
- Gauntlet: chronological 60/20/20 per asset. Train→2024-01-11 (BTC) /
  2024-06-01 (ETH). Val→2025-04-18 (BTC) / 2025-06-28 (ETH). **Test (final
  20%) was never touched** — this script only ever computes train
  `[0:i_tr]` and val `[i_tr:i_va]`. Floors: ≥30 train trades / ≥8 val
  trades = SURVIVOR; below that but train+val both positive =
  INSUFFICIENT-SAMPLE; anything else = FAIL. Selection is by train
  expectancy only (never tuned on val).

## 2. The calm gate (mirrors the LIVE engine exactly)

`daily_pick.py` (lines ~505-524) already runs a live calm-regime gate:
current 1h ATR14% vs its own trailing 336-bar (14-day) median, `ratio <
0.8` = calm. This round reimplements that exact definition
(`calm_gate_1h()` in step67_scalp.py) rather than inventing a new one, then
merges it onto the 15m signal frame with a forward-shifted join key so a
15m bar only ever sees a **closed** 1h bar's regime (no lookahead — see
`merge_htf_onto_ltf()`). Calm bars covered 26.1% of BTC's train+val window
(483 of 1,853 days) and 24.3% of ETH's (381 of 1,568 days) — a meaningful,
not-rare regime.

## 3. The cost floor — the villain, modeled explicitly

CostModel (unchanged project-wide, BloFin's real published rates): 6bps
taker fee, 2bps maker fee, 1bp half-spread, 2bps slippage.

| Model | Fee-only RT | All-in RT (fee+spread+slippage) | How it's computed |
|---|---|---|---|
| **(a) TAKER-TAKER** — deployable today | 12bps | **18bps** | Engine-native: `execution="taker"` on entry AND every signal-driven exit. The hard stop is *always* a taker fill in this engine by construction (a stop is a market order), so this model is honest end to end — no hidden maker assumptions anywhere. |
| **(b) MAKER-ENTRY + TAKER-EXIT** — aspirational, "needs execution work" tier | 8bps | 11bps | Not directly expressible as one engine flag (the engine's hard stop is always taker, and its "maker" mode applies the same passive-then-chase logic to both legs). Computed **analytically** from the taker-taker trade list: swap only the entry leg's cost from taker to maker, ASSUME it fills at the posted limit (upper bound). |
| **(c) MAKER-MAKER** — aspirational ceiling | 4bps | 4bps | Two versions: **ENGINE-SIMULATED** (`execution="maker"` end to end — realistic, posts a limit at the prior bar's close, fills passively only if the next bar trades through it, else CHASES at full taker cost) and **THEORETICAL** best case (both legs assumed to touch, no chase — computed analytically the same way as (b)). |

A config only counts **DEPLOYABLE** if it survives (a). Aspirational
survivors that fail (a) go on the "needs execution work" list, never the
deploy list. **Result: nothing survives (a). Nothing survives (c) engine-
simulated with an adequate sample either** (see §5).

## 4. Families run (all built calm-gated AND ungated)

- **S1 range-edge-fade**: 1h range from the last {24,48} bars' high/low,
  gated to a "real range" (`width < K × ATR1h`, K∈{1.5,2.5}); fade 15m
  touches of the edges; stop `S × range-width%` beyond the edge (S∈
  {0.3,0.5}, train-median-derived and held fixed); structural exit at
  mid-range; max hold {2,4}h. 16 base configs × 2 assets.
- **S2 micro-mean-reversion**: 15m z-score(close, {48,96}) beyond ±{2.0,2.5}
  fades to the mean (z crosses back through 0); stop = 1×ATR15m
  (train-median); max hold 2h. 4 base configs × 2 assets.
- **S3 VWAP magnet**: session-anchored VWAP (00:00 UTC), expanding
  within-session stdev bands at ±{1.5,2.0}; fade back to VWAP; two
  variants — all-week and weekend-only (R63 rehabbed weekend VWAP fades in
  *violent* markets; this round tests the calm-gated version). Stop =
  1×ATR15m; max hold 4h. 4 base configs × 2 assets.
- **S4 compression-edge scalp**: inside a compressed 1h 12-bar range
  (`width < 0.6 × its own trailing-90d median`, shift(1)'d, same adaptive-
  baseline convention as step41's `adaptive_vol_gate`); enter on a 15m
  close that reclaims back INSIDE after a wick beyond an edge (the R64
  sweep-and-reclaim finding — the reclaim is the tradeable side, not the
  break); stop = `S × compression-width%` (S∈{0.3,0.5}); max hold {2,4}h.
  4 base configs × 2 assets.

28 base configs × 2 assets × 2 gates × 2 execution models = **224 scored
rows**, each with train+val expectancy, win rate, drawdown, and (for the
taker row) two analytical alternate-cost re-pricings.

## 5. Full results

### 5a. Verdict counts

| Execution model | SURVIVOR | INSUFFICIENT-SAMPLE | FAIL |
|---|---|---|---|
| (a) TAKER-TAKER | **0** | **0** | 112 |
| (c) MAKER-MAKER, engine-simulated (chase-aware) | **0** | 2 | 110 |

The 2 INSUFFICIENT-SAMPLE maker-maker rows are both S1-range-edge-fade,
BTC, `W24 K2.5 S0.5 hold2h` (ungated: 9 train / 13 val trades; calm-gated:
4 train / 11 val trades) — both far under the 30-train floor. **Not
promotable.**

### 5b. Cost floor in numbers: gross edge vs cost hurdle, by family (mean across all configs/assets/gates, TRAIN window)

| Family | Execution | Mean gross edge/trade | Mean cost paid/trade | Mean NET expectancy/trade | n configs |
|---|---|---|---|---|---|
| S1-range-edge-fade | taker | $28.09 | $18.09 | **$2.50** | 64 |
| S1-range-edge-fade | maker | $28.10 | $4.37 | $5.93 | 64 |
| S2-micro-meanrev | taker | -$1.09 | $5.65 | -$6.74 | 16 |
| S2-micro-meanrev | maker | -$1.56 | $3.77 | -$5.33 | 16 |
| S3-vwap-magnet | taker | $0.005 | $5.54 | -$5.53 | 16 |
| S3-vwap-magnet | maker | -$0.06 | $3.91 | -$3.97 | 16 |
| S4-compression-edge | taker | -$0.27 | $11.25 | -$11.51 | 16 |
| S4-compression-edge | maker | -$0.55 | $4.67 | -$5.22 | 16 |

Reading this: S2, S3, S4 have **no real edge even before costs** (gross
edge ≈ $0 or negative) — for those three families the cost floor isn't
even the primary killer, the entry logic itself doesn't find anything.
**S1 is the one family with a real positive gross edge** (~28bps, well
above even the 18bps taker-taker hurdle) — but see §5c for why that
number is a mirage of sample size, not a tradeable edge.

Sanity check on the cost model itself: measured avg cost/trade under taker
execution ≈ $18.09 against a $10k position — exactly matches the engine's
18bps all-in taker RT hurdle. Under maker execution, measured avg cost ≈
$4.37-4.67 — close to the 4bps maker-maker fee floor, confirming most
maker legs DO touch (little aggregate chase penalty on average), which
makes the S4 case study in §6 (theoretical vs realized maker-maker) all the
more informative.

### 5c. Why S1's gross edge doesn't survive validation — a methodology finding, not a fluke

| Config | K | W | train n | train exp | val n | val exp |
|---|---|---|---|---|---|---|
| best BTC | 2.5 | 24 | 9 | +$47.58 | 13 | **-$34.91** |
| 2nd best BTC | 2.5 | 24 | 9 | +$33.81 | 13 | **-$31.23** |
| best ETH | 2.5 | 24 | 9 | +$20.65 | 3 | **-$33.92** |

Every single S1 configuration at **K=1.5 produced ZERO trades**, and every
config at **W=48 (2-day range) produced ZERO trades regardless of K**. Only
W=24 (1-day range) at the loosest K=2.5 ever fires — and only 7-9 times
per asset across 6+ years of history. That is not enough sample to mean
anything, and the validation collapse (every single S1 config goes deeply
negative on val, -8 to -87 dollars/trade) confirms it: the train wins were
noise fit to a handful of trades.

**Root cause, precisely diagnosed:** comparing an N-bar range's high-low
width against a *single-bar* ATR is the wrong baseline. Under a random-walk
approximation, an N-bar range's expected width scales with `ATR × √N`, not
with `1 × ATR`. At W=24 that's `√24 ≈ 4.9×` ATR; at W=48 it's `√48 ≈
6.9×` ATR. K=2.5 is roughly **half** the random-walk-expected multiple at
W=24 and **a third** of it at W=48 — so the "real range" filter as
literally specified in this round's brief (`width < K × ATR1h`) was
demanding a range far tighter than even a calm, non-trending random walk
would typically produce. That's why it almost never fires. **Lesson for
any future S1 attempt:** either scale K by `√W` (e.g., require width < 
`K × ATR1h × √W` with K in a more permissive range), or calibrate the
"real range" threshold empirically from the train distribution of realized
N-bar widths rather than a fixed ATR multiple.

### 5d. Gate head-to-head — does the calm gate earn its keep? (mean train/val expectancy, taker-taker model)

| Family | Gate | mean train exp | mean val exp | pass rate | n configs |
|---|---|---|---|---|---|
| S1-range-edge-fade | calm-gated | -$1.60 | -$15.32 | 0% | 32 |
| S1-range-edge-fade | ungated | +$6.60 | -$8.66 | 0% | 32 |
| S2-micro-meanrev | calm-gated | **-$9.75** | -$14.78 | 0% | 8 |
| S2-micro-meanrev | ungated | -$3.73 | -$8.78 | 0% | 8 |
| S3-vwap-magnet | calm-gated | **-$7.44** | -$13.25 | 0% | 8 |
| S3-vwap-magnet | ungated | -$3.63 | -$8.19 | 0% | 8 |
| S4-compression-edge | calm-gated | **-$13.12** | -$17.93 | 0% | 8 |
| S4-compression-edge | ungated | -$9.91 | -$15.71 | 0% | 8 |

**Verdict on the owner's regime thesis: NOT CONFIRMED by this test.** On
the three well-sampled families (S2, S3, S4 — hundreds to thousands of
trades each, not a small-sample artifact), calm-gating made average
expectancy *worse*, not better, in every case. S1's comparison is
underpowered either way (both cells single-digit-to-low-teens trades) so
it isn't strong evidence in either direction. The honest read: **cutting
to the calm 26%/24% of the tape did not turn range-scalping into an edge**
— it mostly just threw away 3/4 of the (still unprofitable) trades. This
doesn't rule out that SOME calm-specific range-scalp exists, but S1-S4 as
built this round did not find it.

### 5e. Trades/day realized in calm windows (frequency check, from the well-sampled families)

| Family | Config | Trades/calm-day |
|---|---|---|
| S3-vwap-magnet | band1.5 allweek | 6.24 |
| S3-vwap-magnet | band2.0 allweek | 4.66 |
| S2-micro-meanrev | win48 Z2.0 | 3.94 |
| S3-vwap-magnet | band1.5 weekend | 3.31 |
| S2-micro-meanrev | win96 Z2.0 | 3.01 |
| S3-vwap-magnet | band2.0 weekend | 2.42 |
| S2-micro-meanrev | win48 Z2.5 | 2.45 |
| S4-compression-edge | S0.3/S0.5 hold2h | 1.58 |
| S2-micro-meanrev | win96 Z2.5 | 1.82 |
| S4-compression-edge | S0.3/S0.5 hold4h | 1.39 |
| S1-range-edge-fade | W24 K2.5 (any) | 0.03 |

**Frequency is not the problem** — S2/S3/S4 deliver 1.4 to 6+ trades per
calm day, comfortably meeting a "the tape needs action" goal. The problem
is every one of those trades is negative-expectancy after costs. S1's
0.03/day (about one trade per month) confirms §5c's sample-starvation
diagnosis independently.

## 6. The adverse-selection caveat, made concrete

Per the brief: a limit resting at a range edge fills MORE often exactly
when the edge is about to break — that's adverse selection, and "assume it
always fills at the limit" is not modeling it. Two things this round
measured directly:

**(i) The touch/chase-vs-adverse-run proxy** (winners only, `n_winners≥10`
configs, full table in `step67_touch_proxy_raw.csv`): the maker limit
(prior bar's close) got **touched 100% of the time** across every family
tested — at 15m resolution there's essentially always enough intrabar
range for the next bar to trade through a limit posted one bar back, so
raw fill probability is not the binding constraint here (this also matches
§5b's finding that measured maker cost stayed close to the pure 4bps
fee floor). But among those winners, price ran **more than 2bps beyond**
the limit before the trade turned in **75-90% of cases**, consistently
across S1-S4. That means even the trades that ultimately worked usually
did NOT get a clean touch-and-bounce fill — they got filled mid-move,
during an already-active swing, and only later reverted. **Caveat on the
caveat:** 15m bars are coarse enough that "touched" fires almost trivially;
this backtest cannot see WITHIN the bar, so it cannot tell you whether a
real resting order would have had queue priority ahead of everyone else
sitting at that exact price — that risk is real and completely unmodeled
here.

**(ii) A concrete before/after example — the closest thing to a near-miss
this round produced**, BTC S4-compression-edge `S0.5 hold4h` ungated
(786 train / 263 val trades, a well-sampled config):

| Model | train $/trade | val $/trade |
|---|---|---|
| taker-taker (real) | -$8.79 | -$12.06 |
| **theoretical** maker-maker (best case, assumes every leg touches, no chase) | **+$0.43** | **+$0.12** |
| **engine-simulated** maker-maker (realistic, chase-on-miss included) | **-$1.25** | **-$1.32** |

The fantasy version (both legs always fill at the limit) is barely
breakeven. The realistic, chase-aware engine simulation — which is the
SAME config, same trades, just honest about the fraction of fills that
missed and had to chase at taker cost — is solidly negative. **This is the
whole "cost floor is the villain" thesis in one row of a table**: the gap
between what a backtest can be tempted to assume about maker fills and
what the engine actually simulates once it accounts for misses is bigger
than the entire edge.

## 7. Ranked candidates

**Taker-clearing (deployable) list: EMPTY.** Zero of 112 taker-taker
configs cleared train+val positive at any sample size, let alone the
30/8 floor.

**Maker-clearing ("needs execution work") list: EMPTY at adequate sample.**
The only maker-maker survivors (2 rows, both S1, both under 15 total
trades) are too thin to promote. The one well-sampled near-miss (§6(ii))
nets negative even in its own best-case execution model. **No sealed test
look was spent — nothing qualified to spend one on**, consistent with the
gauntlet rule (a look is earned by train+val passing, not by "closest to
passing").

**If a live maker scalper were built anyway** (hypothetically, informed by
the repo's execution discipline — `blofin_private.py` already reads
position state FROM the exchange rather than tracking it locally, the
right instinct to extend here): single tracked order per side (never more
than one resting limit per direction), a hard TTL cancel-and-reprice if
untouched within N bars (this repo's own "maker chases at bar close if
missed" convention, made explicit rather than implicit), and one-in-flight
discipline (no new entry order posted while a prior exit is still
resolving) — same shape as the stop-then-flat discipline already enforced
inside `backtest.py`'s `execute()`. Note: a targeted search of
`TRADING_BOT_INSTRUCTIONS.md` and `RESEARCH_LOG.md` for a specific
stray/orphaned-order incident this round could reference came up empty —
these are general best-practice safeguards, not lessons from a documented
past failure.

## 8. Honest caveats

- **This is 4 families, 28 base configs, 2 assets, one 6-year history per
  asset.** Absence of an edge in this grid is evidence against these
  specific implementations, not proof no calm-regime scalp exists anywhere
  in signal-space.
- **S1's structural filter was mis-calibrated** (§5c) — the near-zero
  incidence rate means this round cannot actually say whether range-edge
  fading works or not; it says the specific "real range" definition used
  was too tight to generate a testable sample. This is the one family
  worth a proper re-attempt (with the `√W`-scaled or empirically-calibrated
  threshold) before writing off range-edge fading entirely.
- **The maker-maker "theoretical" numbers are upper bounds by
  construction** (assume 100% fill at the posted limit) — always prefer
  the engine-simulated maker-maker column when it exists; the theoretical
  column exists only to quantify the size of the assumption being avoided.
- **Touch rate at 15m is close to uninformative** (100% across the board)
  — it cannot substitute for real queue-position data. Nothing here should
  be read as "maker fills are safe because they always touch."
- **No 5m variant was built** (see §1) given the 15m result already shows
  no edge clearing costs and the repo's own prior finding that resolution
  below 15m makes the cost-vs-edge ratio worse, not better.
- **Calm-gate verdict is family-dependent in sample size, not just in
  sign** — S2/S3/S4's negative-gate-effect result is well-powered and
  should be trusted; S1's comparison is not (§5d).
- Costs, funding, and no-lookahead discipline are unchanged from every
  other step-file in this repo (CostModel defaults, `merge_asof`
  backward-only joins, shift(1)'d adaptive baselines). No cost-free mode
  exists in this engine by construction.
