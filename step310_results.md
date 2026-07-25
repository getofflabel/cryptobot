# ROUND 310 — did the four dead Bitcoin edges die for real, or did we measure the wrong strategy?

Morgan's mandate, 2026-07-25. Round 150 re-tested Bitcoin's five documented
edges under market orders and real chart-structure stops and four of them
died. Round 86 is the cautionary template: our "regular divergence is noise"
verdict had measured a version with no confirmation close, and the
confirmation close is the condition practitioners call mandatory. Adding it
turned a dead family into a survivor. The test had measured a different
strategy than the one people actually trade.

This round asks, for each of the four dead edges, one question: what does a
practitioner of that method require that our step150 script did not
implement? Add exactly that one condition. Re-run. Report.

## GROUND RULES, RESTATED SO NOTHING IS FLATTERED
- Market orders on entry and on every exit, always, including stops, targets
  and time-cap flattens. Cost model unchanged from round 150.
- Stops at real chart structure via exits.py. Position size = dollars risked
  divided by stop distance, 2% of equity at risk. Leverage is an output,
  capped at the desk's real 20x ceiling.
- 60/20/20 in date order. Choose on the first 60% only. The final 20% of
  history was NEVER LOADED by any script in this round.
- Floors: at least 30 trades in the first 60% and 8 in the middle 20%.
  Under that it is reported as NOT ENOUGH TRADES, not as a number.
- Every re-run scores its own BASELINE cell first, reproducing round 150's
  published numbers. All four reproduced exactly, so any difference below is
  attributable to the added condition and to nothing else.
- Engine reused verbatim from step150_common.py. If the engine had changed
  at the same time as the entry rule, no difference could be attributed to
  the entry rule.

## THE LUCK NUMBER, STATED UP FRONT
14 cells with a new condition were run across the four edges. If the sign of
the average profit per trade in each window were a coin flip, luck alone
would put 25% of cells positive in both windows, which is 3.5 of 14. Three
cells came out positive in both windows, and all three are the same edge and
the same condition at three different wait lengths. **The round produced
FEWER both-windows-positive cells than chance alone would give.** Nothing
here is a discovery. Read every section below with that number in hand.

---

## EDGE 1 — 1h structure flip with at least 2 agreeing tools
### VERDICT: DEAD FOR REAL. The retest is a real improvement and it is nowhere near enough.

What our code did: entered on the very next bar's open after the break bar,
the bar whose close finished on the far side of the last confirmed swing.

The missing condition: practitioners of structure-flip trading do not buy
the break. The break puts the level in play; the trade is the return to it.
Break, retrace to the broken level, close that holds on the breakout side,
and THAT close is the entry. Entering at the break is the most commonly
named error in this method for a mechanical reason: the break bar is the top
of an impulse leg, so you enter at the worst price in the move and your
protective swing sits a whole leg away, which makes a 2x-stop-distance
target unreachable. That is exactly the failure round 150 diagnosed in its
own words.

| Cell | first 60% | middle 20% | trades kept |
|---|---|---|---|
| break bar (round 150) | -$42.92 x74 | +$70.61 x34 | 173 signals |
| retest, wait up to 5 bars | -$35.53 x42 | +$8.42 x20 | 77 |
| retest, wait up to 10 bars | -$30.75 x44 | +$26.46 x21 | 83 |
| retest, wait up to 20 bars | -$40.63 x47 | +$26.46 x21 | 88 |

The retest helps the first 60% by about $12 per trade at its best and the
window is still deeply negative. It also cuts the sample in half, which
makes the middle 20% noisier rather than more convincing. No cell passes.

Direction split (step314), which rules out the obvious escape hatch: in the
first 60% the longs lose -$22.05 per trade and the shorts lose -$64.95. The
short side is worse, consistent with the desk's three standing studies, but
**the long side is a loser on its own**, so a long-only version does not
rescue this either. In the middle 20% the shorts are the BETTER side at
+$100.42 against the longs' +$40.79, which is the opposite ranking. A sign
that flips between windows is noise, not a property.

## EDGE 2 — 4h hidden RSI divergence
### VERDICT: NOT ENOUGH TRADES TO SAY. The confirmation close does the same thing round 86 said it would, and Bitcoin does not produce enough of them to prove it.

What our code did: entered on the very next bar's open after the divergence
bar itself.

The missing condition: the confirmation close, which this desk already
proved. Round 86 tested it on the REGULAR flavour of divergence and it was
the only one of three candidate gates that carried signal beyond Bitcoin.
It was never applied to the HIDDEN flavour, because at the time hidden
divergence was a live sealed edge and nobody re-opened it. For a hidden
bullish divergence the intervening level is the highest high between the two
swing lows, meaning the top of the pullback; a close above it says the
pullback is finished and the trend has actually resumed, which is the entire
premise of a continuation pattern.

| Cell | first 60% | middle 20% | win rate mid | trades kept |
|---|---|---|---|---|
| divergence bar (round 150) | +$15.20 x66 | -$9.30 x25 | 44.0% | 92 signals |
| confirming close, wait 3 bars | +$21.88 x14 | -$20.24 x3 | 33.3% | 17 |
| confirming close, wait 6 bars | +$24.22 x22 | +$21.87 x7 | 57.1% | 29 |
| confirming close, wait 12 bars | +$15.72 x26 | +$93.52 x8 | 62.5% | 34 |
| confirming close, wait 24 bars | +$2.89 x32 | +$88.53 x10 | 70.0% | 43 |
| confirming close, wait 48 bars | -$2.27 x33 | +$63.78 x15 | 60.0% | 50 |

The direction is consistent with round 86: the gate lifts the win rate from
44% to 57-70% and flips the middle 20% from a loss to a profit in four of
five cells. Only ONE cell clears both trade floors, the 24-bar wait, and it
clears them by 2 trades. On that cell the profit per trade in the middle 20%
is 2.77% of the full position size, which is 23 times the market-order
round-trip cost of 0.12%, against a random-entry control of -$12.97 per
trade. That looks strong and it rests on 10 trades. At the same time its
first-60% profit has shrunk to +$2.89 per trade, and one more notch of
patience (48 bars) flips that window negative.

The honest reading is that this is round 74's selectivity trap again: the
condition that makes the setup good is also the condition that makes it
almost never happen. **I am not calling this a survivor.** Ten trades in the
middle window and a first-60% edge of three dollars is not a result, it is a
direction. The correct next step is a different asset or a longer history,
not a sealed look.

Why it never had a real exit (step314): 64-90% of these trades end by
running out of time and only 3-10% ever reach the 3x target. A 3x-stop
target with 12 bars to reach it is not a target, it is decoration. Whatever
this edge is measuring, it is measuring 48 hours of drift, not a plan.

## EDGE 3 — 1h RSI(3) dip-buy in a 4h uptrend
### VERDICT: DEAD FOR REAL, and now confirmed dead in two independent spellings of the fix.

What our code did: bought the next bar's open after RSI(3) fell below 15,
while the dip was still in progress with no evidence it had stopped falling.

The missing condition: do not buy while it is still falling. Every version
of dip-buying that is taught with a protective stop attached requires
evidence the fall has stopped: a close back above the prior bar's high, the
oscillator turning back up through its threshold, a higher low printing.
Round 150's own autopsy named the consequence: buying while price is still
making new lows leaves the nearest confirmed swing low inches behind you, so
a structure stop sits inside the noise and gets clipped, and the win rate
collapsed to 41%.

| Cell | first 60% | middle 20% | win rate mid |
|---|---|---|---|
| falling bar (round 150) | -$70.09 x167 | -$69.54 x139 | 41.0% |
| close above the signal bar's high, wait 3 | -$30.66 x216 | -$46.01 x69 | 36.2% |
| close above the signal bar's high, wait 6 | -$25.47 x279 | -$56.42 x87 | 33.3% |
| close above the signal bar's high, wait 12 | -$23.09 x302 | -$43.18 x99 | 36.4% |
| RSI(3) back above 25, wait 6 | -$25.84 x375 | -$34.84 x124 | 36.3% |

Every cell loses money in both windows. The loss per trade roughly halves,
which is the honest thing to note, but halving a $70 loss leaves a $23 to
$56 loss. The two independent spellings of "it turned back up", one in price
and one in the oscillator, agree with each other, which is what makes this
decisive rather than a single failed parameter.

The win rate goes DOWN, not up, which is the tell. Step314's ending mix
explains it: with the confirmation the stop-out rate rises from 56% to 58-61%
and the target-reached rate falls from 26% to 13-18%. Waiting for the turn
costs you entry price while the stop stays anchored at the same swing low,
so the stop gets wider and the 3x target moves further away. The confirmation
that fixes a divergence setup makes a mean-reversion setup strictly worse,
because in a mean-reversion trade the discount IS the edge.

## EDGE 4 — news momentum, first-hour direction
### VERDICT: DEAD FOR REAL. Round 150 measured a different stop than the live version, and the live version is WORSE, not better.

What our code did: used exits.py's generic structure-trailing floor, which
starts at the most recent confirmed swing as of entry or 8% away if none
exists. Round 150 flagged this substitution as a confound in its own results
section and reported the verdict anyway.

The missing condition: the live version, round 65's N2, starts the floor
just beyond the entry bar's OWN opposite extreme, the far side of the
reaction candle, and only then ratchets on confirmed swings. For an event
trade the reaction candle IS the structure, because a headline can land
anywhere on the chart and the level at which the market's reaction to that
headline is proven wrong is the far side of the candle that reacted.

| Cell | first 60% | middle 20% | win rate mid |
|---|---|---|---|
| generic swing floor (round 150) | -$8.88 x284 | -$15.25 x96 | 27.1% |
| reaction bar's far side, cushion 0.1% | -$19.97 x355 | -$42.82 x121 | 20.7% |
| reaction bar's far side, cushion 0.3% | -$6.39 x315 | -$28.23 x112 | 25.9% |

Restoring the strategy's real stop makes it worse in three of four window
readings and cuts the win rate further, to 21-26%. The reaction-bar floor is
TIGHTER than the generic swing floor on most news bars, so it gets clipped
more often. Round 150's confound was real and it ran in the direction of
flattering the strategy.

This closes the one honest question round 150 left open. Round 65's original
simulator charged the cheaper resting-limit-order fee on every entry and
modelled no spread and no slippage at all. Charge market orders on both
legs and the version that is actually deployed loses money in both windows.
**News momentum is dead at real trading costs, and it is the live spec that
is dead, not a substitute for it.**

---

## WHAT THIS ROUND ACTUALLY ESTABLISHED
1. Round 86 was a real correction and it is not a general-purpose rescue.
   Applying the same class of fix to four more edges produced fewer
   both-windows-positive cells than luck alone would give.
2. The confirmation close is setup-specific, not universal. It helps a
   continuation pattern (edge 2, directionally) and it strictly HURTS a
   mean-reversion pattern (edge 3), for the concrete reason that a
   mean-reversion trade's edge lives in the discount that waiting destroys.
   That is a rule worth carrying forward.
3. Two of these edges never had a working exit. Edge 2 ends 64-90% of trades
   on the clock; edge 1's targets were unreachable for the same reason. A
   fixed multiple of a real structure stop, on a short hold cap, is not a
   target. That is a specification problem across the toolkit, not a
   property of any one signal.
4. Long-only does not rescue edge 1. Its long side loses money on its own in
   the first 60%, and the two sides swap ranking between windows.
5. Nothing here justifies spending a look at the final untouched slice of
   history, and none was spent.

## FILES
step310_common.py (shared harness), step310_choch_retest.py,
step311_hidden_div_confirm.py, step312_rsi3_confirm.py,
step313_news_native_floor.py, step314_diagnostics.py,
step310_table.csv (all 18 cells), step311/312/313_table.csv (per edge),
step314_table.csv (decompositions).
