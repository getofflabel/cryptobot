# Round 400 — the gate-measurement audit, starting with the one live Bitcoin edge

2026-07-25. Triggered by round 352's finding that a filter measured as
"run with it" against "run without it" is not measured cleanly in an engine
that holds one position at a time.

Market orders on both legs throughout. Every stop is a chart level. On the
Bitcoin work it is the live one:
`exits.stop_structure_trailing(buffer_pct=1.5, fallback_pct=8.0)`, a
ratcheting floor built from confirmed swings, never a swept percentage.
Size = dollars risked / stop distance, leverage an output, capped at the
desk's 20x ceiling. **The final untouched 20% of every dataset stayed
untouched.** On Bitcoin it is cut inside `load()` before any other code sees
it; on gold and on the breakout re-checks, each study's own loader does the
cutting and this round only read train and validation.

---

## THE THREE ANSWERS, FIRST

**1. Does the live volatility gate's benefit survive a clean test?**
**No.** On the same trend legs the gate costs money. It was never compared
against the same trades without it; it was compared against a different run.

**2. How many past studies used the bad shape?**
Nine were examined. **Six used filtered-run-against-unfiltered-run** — the
live volatility gate (rounds 54 and 150), round 63's session axis, two of
round 60's families, round 100's gold session filter, round 86's volume
gate, and the unlocatable "round 79" study's best match. **Two were already
clean partitions** (rounds 83 and 88). **Two carry no comparison at all**
(round 60's live dip-buy shape, and `daily_pick`'s calm gate, which has no
study of any kind behind it).

But shape alone does not decide harm — the wiring does. Of the six,
**two are confirmed contaminated by measurement** (the live Bitcoin ride and
round 63), **two are confirmed strict subsets by a trade-by-trade check and
so are contaminated only in a second, much milder way** (rounds 100 and 86),
and **two were not verified here** (round 60's families 2c and 4).

**3. Which believed results change?**

| result | before | after a clean test |
|---|---|---|
| the live 1.5% volatility gate on the 4h Bitcoin trend | "the gate's selectivity IS the edge" | **the gate costs $136.34 per trend leg and is the better choice on 5 of 59 legs** |
| round 63's "sessions pull real weight, triple the base rate" | 12.0% of session cells passed against a 6.3% base rate | **every session cell manufactured trades; the five exhaustive cells hold 29-256% MORE trades than the single baseline they were carved out of, in 10 of 10 tools** |
| round 100's gold session filter ("a real, if modest, quality improvement") | GLD 1h donchian $30.25 -> $50.84 per trade | **survives on GLD train (98.8th percentile) but produces ZERO London-hour trades because the ETF does not trade then, and does not reproduce on GC=F at all (34th-76th percentile)** — an instrument fact, not a session edge |
| round 86's volume gate on the breakout | turned an ETH failure into a pass | **the information is real but much thinner than advertised, and one of four cells points the wrong way** |
| round 83 / round 88's chart-read veto | partitioned realized trades | **unchanged — the correct shape, and the code says so explicitly** |
| round 60's SMA200 condition inside the live S&P dip-buy | part of the strategy's definition | **unchanged — no ungated arm was ever run, so nothing was inflated by a comparison that was never made** |

---

# PART 1 — THE LIVE VOLATILITY GATE

`step400_vol_gate_likeforlike.py`, Bitcoin 4h, train+val only.

## Why the ride is the worst case, not the mildest

The gate is built into the signal's state machine, not applied as a veto
afterwards. `strategy.vol_gated_ma` / `vol_filtered_ma` sits FLAT while the
4h trend points up but the market is quiet, and enters on the first bar the
market becomes lively. So the gate does not remove a trade. **It delays
one.** The gated run's entry for a given trend leg is a bar the ungated run
was never at liberty to take, because the ungated run was already holding
the position from that leg's crossover.

That is round 352's artifact in its strongest form: the two runs do not
share a single delayed trade.

| slice | gated run (live) | ungated run | gated trades entered on a bar the ungated run never entered on |
|---|---|---|---|
| train | 44 trades, +$17.15/trade | 55 trades, +$188.63/trade | **13 of 44 (30%)** |
| validation | 14 trades, +$99.37/trade | 17 trades, +$54.97/trade | **8 of 14 (57%)** |

**Roughly two to three times oil's 16-17%.**

The published numbers, train +$17.15 and validation +$99.37, are exactly
what `bitcoin.py`'s own docstring quotes, and this round reproduced both to
the penny against `step150f_recovery_checks.py` before touching anything
else. What changes is what they are evidence *of*.

Note also what the contaminated comparison says once an ungated arm is
actually run: on train the gate looks catastrophic, on validation it looks
like a winner. Two adjacent windows, opposite signs, on a comparison shape
that cannot separate the filter from the reshuffled trade population. The
disagreement is the tell.

## The like-for-like split

One population: every SMA20/100 long crossover, no volatility condition at
all, same structural trailing stop, same market-order costs. Label each
realized trade by whether the market was lively (ATR at least 1.5% of price)
at its own signal bar.

| slice | lively-entry | quiet-entry | gap | percentile vs 2,000 label shuffles |
|---|---|---|---|---|
| train | 31 trades, **+$25.00** | 24 trades, **+$399.99** | -$374.99 | 4.5th |
| validation | 6 trades, +$67.67 | 11 trades, +$48.04 | +$19.62 | 57.6th |
| pooled | 37 trades, **+$31.92** | 35 trades, **+$289.38** | -$257.46 | 7.4th |

**Read this with its tail attached.** Pooled medians are -$63.19 for lively
entries and -$56.16 for quiet ones — effectively identical, so the typical
trade is the same either way. Remove each group's single biggest winner and
the quiet group still leads (+$189.75 against +$1.01), so it is not one
trade doing the work, but it is a handful. The validation slice on its own
is a coin flip on 6 trades against 11 and should not be asked to decide
anything.

## Matched pairs — the question the live rule actually poses

The gate rarely deletes a trend leg. It changes *when* the leg is entered.
So pair each leg with itself: enter at the crossover, or enter at the first
lively bar. Same leg, same exit, same costs, each trade evaluated from the
same starting equity so a per-trade average is not an artifact of which arm
compounded first.

| slice | matched legs | enter at crossover | wait for lively | gate adds | percentile vs 2,000 sign flips | gate better on |
|---|---|---|---|---|---|---|
| train | 45 | +$214.50/leg | +$27.51/leg | **-$186.99** | 0.3rd | 2 of 45 |
| validation | 14 | +$75.88/leg | +$102.36/leg | +$26.48 | 51.5th | 3 of 14 |
| pooled | 59 | **+$181.61/leg** | **+$45.27/leg** | **-$136.34** | **1.1st** | **5 of 59** |

On 38 of the 59 legs the market was already lively at the crossover, so the
gate did nothing and the two arms are literally the same trade. Strip those
out and look only at the legs where the gate acted:

| | legs | enter at crossover | wait for lively | gate adds | gate better on |
|---|---|---|---|---|---|
| gate actually delayed entry | **21** | **+$439.93/leg** | **+$56.89/leg** | **-$383.05** | **5 of 21** |
| — train | 13 | | | -$647.28 | |
| — validation | 8 | | | +$46.34 | |

Median delay before entry on those legs is 10 bars, which is 40 hours. The
median cost of waiting is -$130.14 per leg. The sign-flip test on this
subset alone puts the damage at the **1.6th percentile**.

**The one thing genuinely in the gate's favour.** 14 legs never became
lively at all and the gate skips those entirely. Entered at the crossover
they would have averaged **-$96.44 per leg**. So the gate does avoid a
losing subset. It is simply far smaller than what the delay costs:

| | |
|---|---|
| cost of delaying entry on 21 legs | **-$8,044** |
| benefit of skipping 14 never-lively legs | **+$1,350** |
| **net effect over train+val** | **-$6,694**, which is 71% of the ungated system's total money |
| ungated | 73 trades, +$128.29/trade |
| gated | 59 trades, +$45.27/trade |

(All at $200 risked per trade, the harness's 2% of a $10,000 starting
equity.) The pairing is complete: 73 trend legs exist, 59 had a lively bar
and are matched, 14 never did, and **zero legs were dropped from either arm
for want of a confirmed structural stop** — so no leg is counted on one side
and missing on the other.

## Is it one lucky era?

No. The legs where the gate acted, by year:

| year | legs | enter now | wait | gate adds | gate better on |
|---|---|---|---|---|---|
| 2020 | 5 | +$966 | +$49 | **-$917** | 0 of 5 |
| 2021 | 1 | -$52 | -$100 | -$48 | 0 of 1 |
| 2022 | 1 | +$236 | -$207 | -$443 | 0 of 1 |
| 2023 | 5 | +$749 | +$19 | **-$730** | 1 of 5 |
| 2024 | 6 | +$119 | +$251 | **+$132** | 2 of 6 |
| 2025 | 3 | -$78 | -$115 | -$37 | 2 of 3 |

Five of six years negative. The one positive year is 2024 and its entire
result is a single leg (2024-01-29: waiting 17 bars turned +$516 into
+$1,562). One trade is not an edge.

## The floor

Random long entries through the same exits at the same costs: **+$34.83 per
trade on train and +$4.34 on validation**, 100 draws each. Both arms beat
that. **The trend-following shape is doing real work. The volatility
condition on top of it is not.**

## What this does not settle, stated plainly

Round 54's evidence for the gate — 8 trades at +$401.30 each against an
adaptive gate's 11 trades at +$137.19 — was measured on a window that now
sits **inside the sealed final 20%**. This round did not load that data and
could not re-measure that specific claim. Doing so means spending a sealed
look, which is not this round's call.

What can be said without spending it: **round 54 used the contaminated
shape.** `step54_adaptive_ride.py`'s `build_signal()` produces a different
signal per gate mode (`min_atr_pct=0.0` for none, `1.5` for fixed, a
trailing-median condition for adaptive) and feeds each into a separate
`run_backtest` call. Different signals, different trade counts, one position
at a time.

Two other honest limits. The samples are small by construction — the ride is
a deliberately low-frequency edge and 21 acted legs is 21 acted legs, stated
with its count attached. And this compares "gate at 1.5%" against "no gate
at all", which is the question about the gate's own contribution; it does
not test any other threshold.

---

# PART 2 — THE CATALOG

`step400b_other_gates.py` for the two re-measurements; the rest by reading
each study's code.

**The wiring, not the shape, decides whether the artifact bites.** Two
patterns exist on this desk:

- **Shape 1, the gate lives inside a state machine.** `vol_gated_ma` /
  `vol_filtered_ma`, or an `entry_mask & condition` fed to step43's
  `day_trade_signal`. The machine stays flat while the condition is false
  and enters later, or a suppressed trigger frees the slot for a different
  trigger downstream. This **delays and reschedules** trades. Contaminated.
- **Shape 2, the gate suppresses a whole excursion of a continuous
  indicator signal.** `step86.volume_gate_entry`, aliased in step100 as
  `gate_entry`. The excursions are fixed by price and indicators alone and
  `run_backtest` blocks re-entry after a stop until the signal itself resets
  to flat, so a suppressed excursion cannot be replaced by a later one. The
  filtered run is a **strict subset**. Verified here trade by trade, not
  assumed.

| study | file | comparison shape | wiring | verdict |
|---|---|---|---|---|
| the live 1.5% vol gate (R54, R150) | `step54_adaptive_ride.py`, `step150c_vol_gated_trend.py` | **separate runs** | shape 1 | **CONTAMINATED — 30-57% novel trades, re-measured above** |
| R63 session axis / graveyard rehab | `step63_rehab.py` | **separate runs** | shape 1 | **CONTAMINATED — 29-256% trade inflation, measured below** |
| R60 first-hour breakout, unconditioned vs with-trend | `step60_spx_system.py` family 2c | **separate runs** | shape 1 (`day_trade_signal`) | exposed in principle, **not verified here** — train counts move 227 -> 201, which is consistent with removal only, and R60's own text notes the trend filter excluded no long entry at all on validation (79 against 79) |
| R60 regime-split centerpiece | `step60_spx_system.py` family 4 | **separate runs**, cell against cell | shape 1 | exposed in principle, **not verified here** |
| R60 SMA200 inside the live dip-buy | `step60_spx_system.py` family 1 | **no comparison ever made** — `close > sma200` is always in the entry mask | n/a | **CLEAN of this artifact.** Nothing was inflated by a comparison that was never run. It is part of the strategy's definition and was sealed as a whole |
| R60 overnight drift | `step60_spx_system.py` family 2b | **like-for-like partition** of a raw paired-returns array, bypasses the engine entirely | n/a | **CLEAN** |
| R100 gold session filter | `step100_gold_port.py` family 8 | **separate runs** | shape 2 | **strict subset — 0% novel trades in all 16 cells.** Re-measured below; the finding does not hold up for a different reason |
| R86 volume-gated breakout | `step86_specified.py` family C | **separate runs** | shape 2 | **strict subset — 0% novel trades in all 8 cells.** Re-measured below; thinner than advertised |
| R83 chart-read veto | `step83_eye_filter.py` | **like-for-like partition** of realized trades against a 200-draw random-removal control | n/a | **CLEAN.** Its own docstring names and rejects this exact artifact a day before it was formally discovered |
| R88 veto re-test | `step88_veto_robustness.py` | **like-for-like partition**, reuses R83's wiring | n/a | **CLEAN** |
| the calm-regime gate in `daily_pick` | live in `daily_pick.py` | **no study of any shape** | n/a | see below |

**Two entries in the brief need corrections of fact.**

*"R79's news relevance gate" could not be located.* There is no `step79*`
file, no `## ROUND 79` heading in `RESEARCH_LOG.md`, and no round-79 entry
anywhere. The only file matching the description is
`step49_ai_classifier.py`, which calls itself ROUND 49 throughout, has no
results file, and has no log entry — so it may never have been completed.
Its structure is separate runs on three genuinely different event sets
(keyword-relevant, AI-relevant, AI high/medium) through `day_trade_signal`,
which is shape 1 and therefore exposed, and worse than a simple filter pair
because the event sets are not nested. **Flagging rather than asserting: the
round number should be confirmed before anyone acts on this line.**

*The calm-regime gate in `daily_pick` has no study behind it at all.* It is
an owner directive from 2026-07-24 shipped straight to live code
(`daily_pick.py`: skip a C-grade pick when ATR is below 0.8x its own
trailing 14-day median). Nothing measured it in either shape. The two rounds
that did test calm gating on other strategies both came back negative: R45A
found the calm gate did turn an OI-shock family's train profit from -$7 to
+$7 per trade but the sealed test then failed at -$5.86 per trade over 59
trades, and R67 found gating made three scalping families **worse**. That is
not evidence
against the live rule, which is a different rule on a different book — it is
a statement that the live rule is untested, which is a different and
smaller problem than being wrongly tested.

*One live book is not mentioned in the brief but should be:* `spx_book.py`
runs R60's RSI2-below-5-above-SMA200 dip-buy, and `gold_book.py` runs the
donchian breakout with no session gate at all. Neither carries a gate
measured with the bad shape.

---

# PART 3 — THE RE-MEASUREMENTS

## R63's session axis: the artifact in its purest measurable form

`step63_rehab.py` builds an UNCONDITIONAL baseline run, then a separate run
per scenario cell with the cell mask ANDed into the entry mask and fed to
`day_trade_signal`, a single-slot `pos == 0` state machine.

The session axis (`build_session_axis`) maps every bar to exactly one of
asia / london / newyork / off-hours / weekend. **Mutually exclusive and
exhaustive**, so the five cells' trade counts must sum to the baseline's.
They do not:

| tool | baseline trades | sum of the 5 session cells | extra | inflation |
|---|---|---|---|---|
| G1-LONG | 191 | 256 | +65 | **34%** |
| G1-SHORT | 408 | 528 | +120 | 29% |
| G2 | 462 | 902 | +440 | **95%** |
| G3 | 260 | 349 | +89 | 34% |
| G4 | 311 | 1,107 | +796 | **256%** |
| G5 | 257 | 354 | +97 | 38% |
| G6-k1.5 | 629 | 1,341 | +712 | 113% |
| G6-k2.5 | 333 | 609 | +276 | 83% |
| G7-donchian10 | 264 | 449 | +185 | 70% |
| G7-donchian20 | 228 | 422 | +194 | 85% |

**10 of 10 inflated, median 76%.** Every session cell is manufacturing
trades the unconditional run never took, because narrowing the entry mask
frees the single slot. R63's headline — "SESSION cells alone 12.0% pass,
triple the base rate, sessions pull real weight" — is a statement about
that manufacturing, not about sessions. Its dumb-cell control (an hour-parity
mask) was also a separate run and inflates the same way, so it does not
rescue the comparison.

Nothing from R63 was ever deployed, so no live book changes. What changes is
the standing claim that the session axis carries triple weight.

## R100's gold session filter: clean of the artifact, dead for another reason

Trade-by-trade check on entry timestamps, all 16 cells (2 instruments x 2
sessions x 2 window lengths x train/val): **0% of the filtered run's trades
were trades the unfiltered run never took.** Shape 2 behaves as predicted.
After aligning the label to the signal bar rather than the fill bar, the
partition's in-session group matches the filtered run's trade count exactly
in every cell, which is the integrity check that proves it.

So filtered-against-unfiltered here is not contaminated by rescheduling. It
is still the wrong comparison, because it compares the passing group against
the whole population that contains it rather than against the failing group.
Doing it properly:

| cell | in-session | out-of-session | gap | percentile vs 2,000 label shuffles |
|---|---|---|---|---|
| GLD NY+2h, train | 39 trades, **+$50.10** | 16 trades, **-$18.14** | +$68.24 | **98.8th** |
| GLD NY+2h, validation | 16 trades, +$14.57 | **3 trades**, +$97.27 | -$82.70 | 14.9th |
| GLD NY+4h, train | 47 trades, +$40.21 | 8 trades, -$28.28 | +$68.49 | 97.3rd |
| GLD NY+4h, validation | 17 trades, +$19.13 | **2 trades**, +$99.83 | -$80.69 | 13.7th |
| GLD London+2h and +4h | **0 trades** | 55 / 19 | n/a | no comparison possible |
| GC=F London+2h, train | 10, +$32.85 | 142, +$14.23 | +$18.62 | 76.3rd |
| GC=F London+4h, train | 26, +$25.04 | 126, +$13.48 | +$11.56 | 74.3rd |
| GC=F NY+2h, train | 24, +$25.28 | 128, +$13.61 | +$11.67 | 75.5th |
| GC=F NY+4h, train | 36, +$10.40 | 116, +$17.02 | -$6.62 | 34.0th |
| GC=F, all four cells, validation | | | -$8.80 to -$19.01 | 36th-53rd |

Three things fall out, and the third is the one that matters.

1. **GLD's train result is real by the shuffle test** (98.8th and 97.3rd
   percentile) and its validation slice cannot test it — 3 and 2
   out-of-session trades is not a sample.
2. **GC=F shows nothing.** Same metal, an instrument that trades nearly
   round the clock, four cells at the 34th-76th percentile on train and all
   four pointing the wrong way on validation. That is ordinary chance.
3. **GLD produces literally zero trades in the London window.** The ETF is
   not open then. That is the mechanical proof of what R100's own write-up
   already suspected in words: for an ETF that trades about six and a half
   hours a day, "NY session" is not a session filter, it is a restatement of
   when the instrument exists. The 98.8th percentile is measuring the
   difference between trades placed during GLD's trading day and trades
   placed at its edges.

**Verdict: the gold session filter is not contaminated by round 352's
artifact, and it is still not a session edge.** It is an instrument fact
that does not transfer to the same metal's other instrument. Nothing is
live, so nothing changes operationally.

## R86's volume gate: real information, thinner than advertised

Same trade-by-trade check, all 8 cells: **0% novel trades.** Strict subset,
shape 2, as predicted. Counts match the partition exactly in 7 of 8 cells
and by one trade in the eighth.

The like-for-like partition of the bare Bollinger 20/2.5 population, labelled
by the breakout bar's own volume:

| cell | high-volume | low-volume | gap | percentile vs 2,000 label shuffles |
|---|---|---|---|---|
| BTC 1.2x, train | 772 trades, +$16.04 | **47 trades**, -$7.13 | +$23.17 | **61.6th** |
| BTC 1.2x, validation | 254, +$5.52 | **6 trades**, -$169.63 | +$175.15 | 97.4th |
| BTC 1.5x, train | 726, +$11.41 | 93, **+$40.52** | **-$29.11** | **27.1st** |
| BTC 1.5x, validation | 244, +$6.78 | 16, -$79.40 | +$86.18 | 91.6th |
| ETH 1.2x, train | 647, +$39.65 | 20, -$167.64 | +$207.29 | 91.0th |
| ETH 1.2x, validation | 195, +$24.71 | 15, -$77.86 | +$102.57 | 85.5th |
| ETH 1.5x, train | 607, +$53.57 | 60, -$170.31 | +$223.89 | **99.4th** |
| ETH 1.5x, validation | 179, +$18.49 | 31, +$10.96 | +$7.54 | **51.6th** |

The direction is mostly right — low-volume breakouts really are worse — but
**one of eight cells points the wrong way (BTC at 1.5x on train, 27.1st
percentile) and one is a dead coin flip (ETH 1.5x on validation, 51.6th).**
And the reason R86's before/after looked so clean is visible here: at 1.2x
the gate excludes 47 of 819 BTC trades (6%) and 20 of 667 ETH trades (3%).
**A condition that removes 3-6% of trades was reported as flipping an ETH
verdict from fail to pass.** That is a fragility signal, not a strong filter.

This one is moot operationally: `breakout_book.py` has `ENABLED = False`,
stood down hours after going live, and round 150 killed the whole strategy
when maker execution (+$6.97/trade) was replaced with market orders
(-$8.15/trade). The volume gate's information content is real; the strategy
it gates is not tradeable at what it costs to trade.

---

# THE STANDING CORRECTION

Round 352 wrote the caveat. This round adds the numbers and one important
refinement.

**The refinement: the artifact's size is set by the wiring, and it is worth
checking rather than assuming in either direction.** A gate wired into a
signal's state machine, or ANDed into an entry mask feeding a single-slot
event engine, reschedules trades and contaminates badly — 30-57% on the live
Bitcoin ride, 29-256% on round 63's session cells. A gate that suppresses a
whole excursion of a continuous indicator signal produces a strict subset
and contaminates only through equity compounding, which here was worth
under a dollar per trade. **Both were verified by diffing entry timestamps,
which costs almost nothing and settles the question outright.**

The rule for every future filter, gate, regime condition or session study:
**partition one realized trade population, or pair legs with themselves, and
diff the entry timestamps to prove which you have.** Two runs with different
trade counts is not a test of a filter.

And one more, earned twice in this round: **when a filter's apparent benefit
comes from excluding 3-6% of trades, or from a window in which the
instrument does not trade, the number is about the sample, not the filter.**

---

## Files
- `step400_vol_gate_likeforlike.py` — the live gate: artifact count, like-for-like split, matched pairs, random-entry floor
- `step400_table.csv` — every number from part 1
- `step400_matched_pairs.csv` — the 59 matched legs with the delay in bars
- `step400b_other_gates.py` — the trade-by-trade subset checks and like-for-like partitions for R100 and R86
- `step400b_table.csv` — every number from part 3
- `step400_gate_artifact_audit.md` — this file
