# Step 86 — Retest the Families We Under-Specified

**Round 86.** R85 collected 36 documented winning-trade setups and the
conditions each one required (`step85_setups.csv` / `step85_winning_trades.md`).
Comparing that checklist to this project's own prior tests found several
"this doesn't work" verdicts measured tests that omitted conditions
practitioners treat as mandatory — most concretely R58's regular RSI
divergence test (1 survivor in 96 configs), which fired on ANY confirmed
swing with no level gate, no confirmation candle, and no trend-extreme
restriction, while R58's HIDDEN divergence test implemented its one
required gate (trend alignment) and sealed-PASSED. This round codes all
eight proposals from step85 §5 and runs each ALONGSIDE its under-specified
predecessor.

**Files:** `step86_specified.py` (this round's code), `step86_results.md`
(this file), `step86_table.csv` (405 rows: every BTC config x every ETH
transfer replay of a BTC survivor).

**Discipline, unchanged from every prior round:** cached BTC + ETH 1h/15m/4h
via `fetch_bybit_deep` (no network calls). Chronological 60/20/20 split per
timeframe; the sealed final 20% (test) was **never** sliced by this script —
only train (0:i_tr) and val (i_tr:i_va) were computed. Selection by TRAIN
expectancy only, val read once. MIN_TRAIN_TRADES=30, MIN_VAL_TRADES=8. Costs
always on (CostModel defaults, execution="maker", real funding).
**ETH transfer is mandatory on every BTC SURVIVOR** — 41 configs cleared the
BTC bar; all 41 were replayed on ETH.

---

## 1. Headline before/after table (BTC)

| Family | Proposal | Before: configs / survivors | After: configs / survivors | Best train exp (after) |
|---|---|---|---|---|
| A — regular divergence | 1: level-gated | 16 / 2 | 144 / 8 | $61.42 |
| A — regular divergence | 2: confirmation-gated | 16 / 2 | 32 / **11** | $120.90 |
| A — regular divergence | 3: trend-extreme-restricted | 16 / 2 | 32 / **0** | $26.51 (still FAIL) |
| A — regular divergence | 4: all three combined | 16 / 2 | 32 / 7 | $118.21 |
| B — MACD crossover | 5: structural confirmation | 4 / 0 | 8 / **0** | $2.89 (still FAIL) |
| C — breakout | 6: volume-gated | 2 / 2 | 4 / 3 | $17.73 |
| D — liquidity sweep | 7: sweep→MSS→displacement | 16 / 0 (5 insufficient-sample) | 42 / **0** (6 insufficient-sample) | best FAIL row $248.59 (n too small to count) |
| E — opening-range breakout | 8: stricter confirmation | 16 / 1 | 16 / 7 | $31.23 |

**And the row that matters most — ETH transfer, mandatory on all 41 BTC survivors:**

| Family | Proposal | BTC survivors queued | ETH transfers PASS |
|---|---|---|---|
| A before (unconditional) | — | 2 | **0** |
| A after-level | 1 | 8 | **0** |
| A after-confirm | 2 | 11 | **3** |
| A after-extreme | 3 | 0 | n/a (nothing to test) |
| A after-all3 | 4 | 7 | **0** |
| C before (R76 exact) | — | 2 | 1 |
| C after (volume-gated) | 6 | 4 | **3** |
| E before | — | 1 | 0 |
| E after (strict ORB) | 8 | 7 | **0** |

**Read plainly:** adding the practitioners' conditions materially changed
which configs clear the BTC bar in every family except B (MACD) and D
(sweep), which stayed dead or under-sampled either way. But BTC survival and
real transfer are two different bars — of 41 BTC survivors across the whole
round, only **7 (17%)** hold up on ETH, and they cluster in exactly two
places: **confirmation-gated regular divergence** (proposal 2) and
**volume-gated breakout** (proposal 6). Level-gating, trend-extreme
restriction, the full three-way combination, structural MACD confirmation,
sweep→MSS→displacement, and stricter ORB confirmation each produced either
zero BTC survivors or zero ETH transfers — real, reportable negative
findings, not oversights.

---

## 2. Family A — regular RSI/MACD-hist divergence

Base signal is R58's own regular-divergence event definition, reused
verbatim (`swings()`, the same confirmed-swing no-lookahead discipline,
RSI14 and MACD-hist, k∈{5,8}, 1h and 4h). Secondary params held fixed across
all four proposals at R58's own settings (buffer 0.15%, hold 96h) so the
ONLY thing that changes between rows is the gate — apples to apples.

### Proposal 1 — level-gated. **My stated level definition:**
a "significant level" = the nearer of (a) any OTHER confirmed swing high or
low (same `swings()` definition the divergence itself uses) that is at
least **M** bars OLDER than the current divergence event, or (b) the
step56 equal-highs/equal-lows liquidity pool value active at that bar
(`liquidity_pools`, tol=0.1%, already historical by construction). Swept
N∈{0.5%,1%,2%} x M∈{50,100,200} per the brief.
**Result:** 8/144 gated configs clear BTC (all MACDhist k8 1h), retaining
54-58 trades/year against the baseline's 60.2/year — i.e. the level gate is
**nearly a no-op** for this oscillator/timeframe (almost every regular
divergence swing already sits within 2% of SOME prior swing or pool, so the
filter barely bites). Zero of the 8 transferred to ETH. **Verdict: level
gating alone does not rescue regular divergence, and barely filters
anything on the one config where it does clear the bar.**

### Proposal 2 — confirmation-gated. Entry shifts from the divergence bar
to the first bar (within a wait window of 10 or 30 bars) that closes back
through the intervening structural swing between the two divergence points
— the literal "confirmation candle" every literature source with a concrete
rule required. **This is the gate that actually works:** 11/32 BTC
survivors, and it is the ONLY Family-A gate with ANY ETH transfer at all —
**3 of 11 survive on ETH**, all MACDhist on 4h:

| Config | BTC train / val | ETH train / val | ETH trades/yr |
|---|---|---|---|
| MACDhist k5, wait30, tgt3x, 4h | n=81, $6.38 / n=24, $212.65 | n=71, $94.06 / n=23, $62.88 | 21.9 |
| MACDhist k5, wait10, tgt3x, 4h | n=64, $20.31 / n=16, $78.39 | n=52, $185.85 / n=13, $45.40 | 15.2 |
| MACDhist k8, wait10, tgt3x, 4h | n=42, $47.74 / n=10, $169.25 | n=34, $12.82 / n=13, $71.91 | 11.0 |

RSI14's confirm-gated variants (11 of the 32) also clear BTC handily (up to
$120.90/trade train on 4h) but **none transfer** — RSI14 confirm-gate is a
BTC-only artifact, MACDhist confirm-gate is the real one.

### Proposal 3 — trend-extreme-restricted. **My stated definition** (chosen
over the step85 draft's ambiguous "champion regime age" phrasing, per the
round-86 brief's own suggested objective alternative): extension =
|close − SMA(100)| / ATR(14) at the divergence bar, thresholds 2.0 and 3.0
ATR-units. **Result: 0 of 32 configs survive on BTC** — train expectancy is
occasionally positive but validation is deeply negative almost everywhere
(4h val expectancy runs −140 to −220/trade). This is a clean, honest
negative: this particular objective operationalization of "at a trend's
exhaustion" does not rescue regular divergence. It does not disprove the
literature's underlying claim — a different operationalization (the
original "champion-regime age" reading, or a raw N-bar-move magnitude
instead of ATR-distance-from-SMA) was not tested here and remains open.

### Proposal 4 — all three combined (the headline practitioner stack).
Fixed the level gate at the grid's middle (M=100, N=1%) and confirm wait at
30, swept only the extension threshold. **7 BTC survivors** (best:
MACDhist k8 1h, $118.21 train / $34.68 val, tgt3x, ext≥3.0 ATR) but **0
transfer to ETH**. Since proposal 2 alone is the only gate carrying real
transferable signal, stacking level + extreme on top of it does not add
edge — it mostly just re-confirms proposal-2's BTC-only RSI14 rows and
narrows the MACDhist rows further without improving them.

**Plain English — what the one surviving regular-divergence setup actually
requires:** MACD-histogram prints a lower low (bearish) or higher low
(bullish) at a NEW confirmed swing than the histogram's own reading at the
PRIOR confirmed swing of the same type, on the 4-hour chart. Do NOT enter on
that bar. Wait (up to 30 bars, ~5 days on 4h) for price to close back
through the price extreme that sat BETWEEN the two divergent swings — that
close is the entry. Stop beyond the divergence's own swing extreme (median
~0.15% buffer, capped 4%), target 3x that distance, flatten after 96 hours
if neither hits. Fires **11-22 times a year**. This is a materially
different trade than "short as soon as you see the divergence" — it is
specifically the confirmation-candle discipline the literature (Pipcy,
LuxAlgo) called the "#1 failure mode when skipped," now shown to be the
one condition in this family that is not BTC-only noise.

---

## 3. Family B — MACD crossover with structural confirmation (proposal 5)

Bare MACD-histogram 0-line crossover (event-entry, ATR-based stop/target,
72h max hold) is **already FAIL** on both BTC 1h and 4h (train expectancy
negative in 3 of 4 base configs). Gating the crossover to require a
Donchian(20) breakout confirming within 0 or 5 bars **does not rescue it** —
12 gated configs, 0 survivors, train expectancy stays negative or barely
positive in every row. **Honest verdict: this specific MACD family is dead
on BTC regardless of confirmation, at least in this event-entry geometry.**
Caveat worth stating plainly: this is a different signal shape than R76's
own MACD-hist 0-cross test (which used a persistent hold-until-flip state
machine with no fixed stop/target, not this round's discrete event-entry +
ATR-stop geometry) — the literature's "crossover needs confirmation" claim
was tested honestly here, but not exhaustively across every possible base
geometry.

---

## 4. Family C — volume-gated breakout (proposal 6). **The round's strongest finding.**

R76's exact two BTC 1h SIGNAL-mode survivors (Bollinger breakout 20/2.5;
BB-in-KC squeeze release BB20/2 KC20/1.5) re-tested with an added gate: the
breakout (or squeeze-release) bar's own volume must clear 1.2x or 1.5x its
own trailing 20-bar average, checked ONLY at the entry transition bar (once
in position, the trade rides to the base signal's own exit regardless of
later volume — a filter permits entries, it does not intra-trade flatten,
same convention R76 used).

| Config | Variant | BTC train / val | ETH train / val | trades/yr (BTC) |
|---|---|---|---|---|
| Bollinger breakout 20/2.5 | before (bare) | $14.71 / $1.48 | $33.43 / $17.38 | 213.1 |
| Bollinger breakout 20/2.5 | + vol≥1.2x | **$14.87 / $5.21** | **$39.59 / $26.01** | 202.6 |
| Bollinger breakout 20/2.5 | + vol≥1.5x | $9.39 / **$7.17** | **$61.26 / $18.15** | 191.3 |
| BB-in-KC squeeze release | before (bare) | $5.12 / $0.19 | $2.70 / **−$7.55 (FAIL)** | 210.7 |
| BB-in-KC squeeze release | + vol≥1.2x | **$17.73 / $9.87** | **$9.37 / $4.04 (PASS)** | 113.7 |
| BB-in-KC squeeze release | + vol≥1.5x | $8.21 / −$1.02 (FAIL) | not tested (BTC didn't survive) | 94.8 |

**This is the cleanest before/after story in the round.** The volume gate
did three distinct, honest things depending on config: (a) modestly
improved Bollinger breakout's already-passing numbers on both assets, (b)
**turned BB-in-KC squeeze release from an ETH-transfer FAILURE into an
ETH-transfer PASS** — exactly the literature's claim that volume separates
real breakouts from false ones, demonstrated as a genuine before→after flip
rather than a wash, and (c) at the tighter 1.5x threshold, cut BB-in-KC's
sample enough to flip it to FAIL — the "no-op or hurts" possibility the
step85 proposal explicitly flagged as worth checking, realized on one of
the four configs.

**Plain English — what this setup requires:** price closes outside a 20-bar
Bollinger Band (2.5 std, or the BB-inside-Keltner squeeze release variant),
AND that breakout bar's own trading volume is at least 1.2x its trailing
20-bar average. Exit when price closes back through the band's own midline.
No fixed stop/target — the band midline is the exit. Fires **113-213 times
a year** depending on config — the single highest-frequency survivor in
this whole round, and the one with the deepest, most consistent BTC-and-ETH
agreement.

---

## 5. Family D — liquidity sweep → MSS → displacement (proposal 7)

A genuinely new signal family (not a filter on an existing base): sweep a
step56 equal-highs/equal-lows pool (wick through by ≤0.3%, close back
inside), THEN wait (10 or 20 bars) for the market to break the nearest
OPPOSING confirmed swing point with a displacement bar (range > 1.5x or 2x
ATR14) — entry there, never at the sweep. Stop beyond the sweep wick,
target the opposing liquidity pool (falling back to 2x/3x stop when no pool
is active).

**Result: not a single BTC survivor, before OR after — but this is a
sample-floor story, not a clean failure.** 11 of 58 configs (5 before, 6
after) land in INSUFFICIENT-SAMPLE (both train and val expectancy positive,
but too few trades to clear the 30-train/8-val floor) — e.g. the naive
"before" sweep-entry baseline on 4h k5 clears only 5 train / 2 val trades
per config across a 5+ year dataset. The FAIL rows aren't much bigger:
median train-trade count across all 47 FAIL rows is **3**, mean **10.2** —
this project's own liquidity-pool definition (2+ equal swings within 0.1%)
is already a stringent gate, and stacking sweep → structure-break →
displacement on top of it is asking three rare events to co-occur in
sequence. **Honest verdict: this is not "the trap doesn't exist," it's "we
do not have enough sample on BTC/ETH cached history to judge this exact
three-stage sequence."** A looser pool tolerance or a longer lookback
(neither swept here, to keep the grid honest to the brief's stated
dimensions) is the natural next step, not a verdict that the family is
dead.

---

## 6. Family E — opening-range breakout, stricter confirmation (proposal 8)

step43's exact session-breakout base (first-4h or first-8h UTC range, level
cross entry) gains a second gate: the breakout bar's range must exceed the
average of the prior 5 bars' range AND its body must occupy ≥70% of its own
range. **On BTC this looks like a strong win** — 1 survivor before, **7
survivors after**, best train expectancy $31.23 (vs $14.56 bare) — but
**0 of the 7 (plus the 1 before-survivor) transfer to ETH**, all 8 ETH
replays FAIL, several with clearly negative val expectancy (−$11 to −$22).
**Honest verdict: the stricter confirmation bar is a genuine BTC-only
improvement over the bare level-cross, but neither the before nor the after
version of this family holds up cross-asset** — exactly the discipline this
round's ETH-mandatory rule exists to catch, and a reminder that a striking
BTC-only table (as in §1's "after" column) is not itself the finish line.

---

## 7. Trades/year — every ETH-transfer survivor, together

| Setup | tf | trades/yr (BTC) | trades/yr (ETH) | BTC val exp | ETH val exp |
|---|---|---|---|---|---|
| Bollinger breakout 20/2.5 + vol≥1.2x | 1h | 202.6 | 196.4 | $5.21 | $26.01 |
| Bollinger breakout 20/2.5 + vol≥1.5x | 1h | 191.3 | 183.3 | $7.17 | $18.15 |
| Bollinger breakout 20/2.5 (bare, R76) | 1h | 213.1 | 204.5 | $1.48 | $17.38 |
| BB-in-KC squeeze release + vol≥1.2x | 1h | 113.7 | 115.7 | $9.87 | $4.04 |
| MACDhist k5 regular div, confirm-gate wait30 tgt3x | 4h | 20.8 | 21.9 | $212.65 | $62.88 |
| MACDhist k5 regular div, confirm-gate wait10 tgt3x | 4h | 15.8 | 15.2 | $78.39 | $45.40 |
| MACDhist k8 regular div, confirm-gate wait10 tgt3x | 4h | 10.3 | 11.0 | $169.25 | $71.91 |

**Frequency reality check:** the volume-gated breakout family trades **10x
more often** than the confirmation-gated divergence family. Both are real,
but they occupy very different roles — breakout is a bread-and-butter
weekly-frequency system, divergence-confirm is a once-a-month reversal
play with much larger per-trade expectancy and correspondingly higher
variance (val sample sizes of 13-24 trades on both assets are thin enough
that the very large val-expectancy numbers, e.g. $212.65/trade BTC, should
be read as "real direction, uncertain magnitude," not as a precise
forecast).

---

## 8. Biggest caveats

1. **17% ETH-transfer rate overall (7/41).** Most of this round's proposals
   — level-gating, trend-extreme-restriction (as objectively operationalized
   here), the full 3-way combination, MACD structural confirmation,
   sweep→MSS→displacement, and stricter ORB confirmation — produced BTC-only
   results that did not generalize. Two did: confirmation-gated divergence
   (MACDhist/4h specifically) and volume-gated breakout. This is the honest
   shape of the round, not a uniform vindication of R85's checklist.
2. **Proposal 3's failure is about the operationalization, not necessarily
   the underlying claim.** The step85 draft's own phrasing ("champion
   regime age") was ambiguous; this round tested the round-86 brief's own
   suggested objective alternative (ATR-distance-from-SMA) and it did not
   work. Whether the original ambiguous reading, or a raw N-bar-move
   magnitude, would fare better is untested and open.
3. **Family D is a real "insufficient sample," not a real "FAIL."** No
   config reached the trade-count floor cleanly; the honest conclusion is
   "we don't yet know," not "the trap doesn't exist."
4. **Sealed test (final 20%) was never touched**, per standing discipline —
   every number above is train/val. Before any of these seven ETH-transfer
   survivors goes anywhere near live capital, the lead spends a sealed look.
5. **Val sample sizes on the divergence-confirm survivors are thin** (13-24
   trades per split, both assets) — real, but the per-trade dollar figures
   will move a lot as more data accumulates. The volume-gated breakout
   family's samples (150-260 trades per split) are far more solid.
