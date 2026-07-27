# Step 421 — the allocator: how the bots stop competing for the same money

Wallace, 2026-07-25:

> "your bots need to work together to identify how to trade the situation,
> sometimes you have to give up small trades to get into bigger trades. its
> important that they are together for the sole purpose of being harmonized"

This is the half of the rebuild that `trader.py` does not cover. The brain
answers "is there a trade on THIS chart." The allocator answers "given every
chart at once, and one pot of money, what do we actually do."

## The problem, concretely

Six markets. One account, about $1,339 today. Every bot that finds something
wants capital. Today they take it first-come-first-served: whoever's cycle
fires first gets the slot, and a mediocre Bitcoin trade at 09:00 can block an
excellent gold trade at 09:40 for no reason other than the clock.

That is the opposite of harmonised. It is six people grabbing at one wallet.

## The shape

Bots **propose**. They do not execute. The allocator executes.

    each market bot ->  Proposal | None
    allocator       ->  ranks, sizes, and issues the orders

A proposal carries what the brain already produces: direction, the stop level
and what chart feature it rests on, the reason in one line, and — the new
part — **the two numbers that make proposals comparable across markets.**

## The two comparable numbers

Everything else is market-specific and cannot be ranked against anything.
These two can:

**1. Reward against risk.** How far to the next real level in our favour,
divided by how far to the stop. This is unitless, so Bitcoin's 4,200-point
move and gold's 18-dollar move land on the same scale. Both distances come
from chart structure, so this is not a made-up target.

**2. How many times the trade clears its own cost.** Expected profit divided
by the round trip. Our bar has been 5x and it stays 5x. This one is what
kills most proposals, and it is market-specific in a way that matters:
BloFin charges 0.06% each way, so 0.12% round trip on crypto and gold. The
S&P on Alpaca costs about 0.02% to 0.04% round trip. **The same setup can be
a reject on crypto and a comfortable pass on the index.** That is not a
rounding difference, it is 4 to 6 times cheaper, and round 360 already found
it flips the verdict on 220 of 314 settings.

Conviction from the brain is a third input, but it ranks and never rescues:
a high-conviction read that only makes 3x its cost is still a reject.

## What "give up a small trade to get a bigger one" actually means in code

This is the instruction, and it needs a mechanism rather than a slogan.

**Reserve.** The allocator never commits the last slot to a proposal that
merely passes. If a proposal clears the bar by a little and nothing else is
on the table, it can have the slot. If it clears by a little and the
allocator can see a setup forming elsewhere — a level about to be tested, a
range about to resolve — it holds the money.

**"About to" has to be measurable, not a feeling.** The brain already
computes distance to the nearest untested level. A market whose price sits
inside a small fraction of its own recent range from a significant level is
"loaded"; one that just moved away from everything is not. That number is
re-derived per market from its own recent bars, never a copied constant —
the 1.5% volatility number that reads as normal on Bitcoin's early history
and passes 98% of Solana's bars is the standing warning here.

**The trade-off is explicit and logged.** Every time the allocator declines
a passing proposal to hold capital, it writes down what it declined, what it
was holding for, and whether that better setup ever arrived. After a few
weeks that log answers the question honestly: does waiting pay, or is it
just missing trades with extra steps? If the held-for setup arrives less
than half the time and the declined trades were profitable, the reserve rule
is wrong and comes out.

## Correlation, which is the part that actually blows accounts up

Bitcoin, Ethereum and Solana are not three markets. On a bad day they are one
market with three tickers. Five slots all long crypto is one position at 5x
the size, and the account finds that out at the worst possible moment.

The allocator measures the recent co-movement between open positions and any
new proposal from that market's own recent bars, and counts anything tightly
co-moving as **partly the same position** for the purpose of how much is at
risk. The index and gold usually earn their own slots. Ethereum alongside
Bitcoin usually does not.

This also cuts the other way and is worth saying: two proposals pointing
opposite ways on tightly-linked markets are mostly cancelling each other out
while paying two round trips for the privilege.

## What it does NOT do

- It does not override a stop. The stop is the brain's, from the chart.
- It does not resize a proposal upward. Size is risk divided by stop
  distance, always, so leverage stays an output.
- It does not invent trades. If nothing proposes, nothing happens, and days
  with no trades are expected and fine.
- It does not touch an open position's exit. Once a trade is on, the market
  bot manages it out.

## The honest caveat

The reserve rule is the one part of this with no measurement behind it. It
comes from Wallace's own trading, where it is real: he passes on small setups
to keep powder for the ones he wants. I have not tested it here and I am not
going to pretend the number of times it should decline is known. It ships
logging its own decisions from day one specifically so it can be judged
rather than believed, and it is written so it can be switched off without
touching anything else.

## Order of work

1. `trader.py` — the brain. In progress.
2. Market bots become thin: fetch chart, call brain, return a proposal.
3. `allocator.py` — ranks, applies the cost bar, applies correlation,
   decides, executes, logs the trade-offs.
4. Only then does anything go near the live loop.
