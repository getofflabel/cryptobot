# Step 422 — the liquidity framework, and why it answers Wallace's question

Source: TJR, "The ONLY Liquidity Guide You'll Ever Need", 22 July 2026.
Wallace sent it 25 July 2026, right after telling me a fade has to have a
reason. **This is the reason.** Full auto-transcript pulled and read; the
mechanics below are my own restatement, not a copy of the video.

## Why this arrives at exactly the right moment

Wallace, an hour earlier:

> "sometimes when it dips it keeps dipping because thats the trend, you must
> have a reason for it to be a mean reversion"

Everything I had was a description of the stretch: price is far from its
average, the push is losing steam, it stopped at an old level. All of that
describes the *shape* and none of it supplies a *mechanism*. This framework
supplies the mechanism, and it is a specific, checkable event rather than a
feeling.

## The claim, in plain terms

**Resting orders sit above highs and below lows, and there are two separate
piles of them at each.**

Above a high, in an uptrend:
1. Traders buying the break of that high, expecting the uptrend to continue.
2. Traders who are short and whose stop sits above that high — when it goes,
   they are **forced to buy** to close.

Both are buy orders, and they are triggered by the same event. Below a low
the mirror holds: breakdown sellers, plus longs stopped out and forced to
sell.

**So price pushing past a high is the moment a large pile of buying gets
filled all at once — which is exactly the moment anyone wanting to sell size
can do it.** Selling size requires buyers. The sweep manufactures them.

Whether the intent story about market makers is literally true does not
matter to us and I am not going to pretend to know. What matters is that it
predicts a testable thing: **the bar that takes out a prior swing level is a
better place to look for a reversal than a random bar.** That is a
measurable claim and it is the one we will measure.

## What counts as a high or a low

Two candles. A high is an up candle followed by a down candle, and the level
is the higher of the two wicks. A low is a down candle followed by an up
candle, at the lower of the two wicks.

We already own this. Round 370 measured this definition against the fractal
swing we had been using and found it sits **44% closer to price**, which
roughly doubles the position size a fixed dollar risk allows. It has been
sitting unused. It stops sitting unused now.

## THE PART THAT MAKES IT A DISCIPLINE RATHER THAN A GUESS

He says it three separate times, and it is the load-bearing sentence of the
whole method:

**A sweep creates the OPPORTUNITY for a reversal. It does not create the
reversal.** Buying blindly because a low got taken out is how you sit in a
losing trade all the way down.

The confirmation is that **the opposite trend actually forms out of the
sweep**. After a low is swept: wait for a higher low and then a higher high.
After a high is swept: wait for a lower high and then a lower low. Only then
is there a trade.

This is precisely the "you must have a reason" bar, and it is the reason our
own dip-buying work kept coming out weak. We were entering on the stretch.
The framework enters on the stretch **plus proof the reversal started**.

## Where the meaningful liquidity sits (his ranking, to be tested not assumed)

1. **Higher-timeframe highs and lows** — 1-hour and 4-hour, not 5-minute.
   His argument: sweeping a 4-hour level releases a far bigger pile than
   sweeping a 5-minute one, so the move that follows is bigger. A 5-minute
   sweep gives a 5-minute move, which after costs is nothing.
2. **Session highs and lows.** Asia 18:00–03:00 New York time, London
   03:00–08:30, New York 09:30–17:00. The specific claim: **the New York
   open frequently sweeps the London session high or low first, and then
   makes the day's move in the other direction.** He shows consecutive days
   and says it happens "almost every single day". That is a strong, dated,
   directly falsifiable claim and it is the first thing we test.
3. **News-candle highs and lows.** He flags this as advanced and low
   priority. We deprioritise it too.

## The two states of a liquidity pool

**Low-resistance liquidity** — several highs (or lows) stacked at similar
levels, none yet taken out. A magnet. Price actively seeks it. Use it as a
**target**, not an entry.

**High-resistance liquidity** — a pool already swept, which price has
reversed away from. Price has no reason to return soon, because it needs the
opposite side to close its position at a profit.

So the trade shape is: **enter away from what was just swept, target what
has not been swept yet.** Both ends of the trade come from the chart, which
is what we need anyway — a target from structure rather than an invented
multiple of risk.

We already have the machinery for the stacked case: `step56_smc_toolkit`
finds equal highs and lows. It has never been used as a target.

## The reconciliation with our own dead ends — read this before objecting

Rounds 84, 90 and 92 killed shorting crypto: 1 win in 12 blind drills, worse
than random entry in all 30 mirror cells, and monotonically worse the more
significant the level that broke.

**Those were shorts entered ON the break — betting the break continues.
TJR's short is the opposite trade: he shorts AFTER a high is taken out and
the downtrend forms.** Our tests do not cover it. They are not evidence for
it and they are not evidence against it.

And round 90's finding points the same way this framework does. We measured
that breaking an **aged, well-defended level is a WORSE short than breaking
a fresh one, monotonically across 25,481 events**. An aged, well-defended
level is precisely where the most orders have piled up. So the more
liquidity sat at the level, the more the break failed and price came back.
We measured that while testing the opposite trade and wrote it down as a
dead end.

So our own data already leans this way, found by accident while we were
testing its opposite and filed as a dead end.

## HOW THIS MATERIAL IS TREATED — read before designing any test

Wallace, 2026-07-25:

> "anything that i am feeding you from professional traders, always take it
> serious, they are not ideas for you. you and i are not professionals. tjr
> is. if you were a professional you would be profitable already. there is
> no disagreeing with him, only testing it when you find the opputunity"

He is right, and the first version of this document got it wrong — it
described the framework as "a hypothesis, not a result", which is the
posture of someone judging a professional's method from a desk with no
profitable live strategy on it.

**The purpose of a test changes. The rigour does not.**

We are not determining whether this works. We are determining **WHERE it
applies**: which market, which timeframe, which session, which levels, and
what the numbers are for that chart rather than the ones in the video. A
negative cell means "this is not where it lives" and sends us looking for
the configuration where it does. It never means "this does not work", and no
professional's method gets written up here as a dead end.

Every measurement standard stays exactly as it is. Sloppy measurement is not
respect, it is a different way of getting it wrong.

## What gets tested, in order

1. **The New York / London sweep.** Does the New York open take out the
   London session high or low before the day's move, and how often? He says
   almost daily. Ten years of 5-minute index data can answer this exactly.
   Chance baseline stated up front.
2. **Sweep plus confirmed reversal versus random entry**, same exit, same
   costs, both directions, per market, thresholds re-derived per market.
3. **Does the timeframe of the swept level predict the size of the move?**
   His central claim for why he only trades higher-timeframe sweeps. If a
   4-hour sweep does not pay more than a 5-minute sweep, the ranking is
   decoration.
4. **Stacked unswept levels as a target** versus a fixed multiple of risk.
5. **The 2-candle swing versus our fractal**, as the stop, at real costs —
   finishing what round 370 started.

Standing bars, unchanged: profit at least 5x the round trip, beat random
entry timing, minimum 30 trades in the first window, state what luck alone
produces, 60/20/20 with the last slice never opened, and no constant ported
between markets.
