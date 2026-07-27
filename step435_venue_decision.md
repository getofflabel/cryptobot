# Step 435 — the new build trades Alpaca. BloFin is out.

Wallace, 2026-07-25:

> "we are not using blofin anymore for this, just use alpaca so you have
> access to everything and stop bugging out"

Done. The whole new build points at Alpaca paper. BloFin is retired along
with the ten old bots.

## Why this is the right venue for THIS method, not just a preference

**The costs are not close.** Measured from about 700,000 real quotes across
2016-2026, a round trip on SPY costs **0.0035%** of the position, with no
commission. BloFin charges **0.06% per side, so 0.12% round trip** — about
34 times more. For a method that trades several times a day off small
intraday moves, that difference is the difference between a strategy and a
donation. Round 360 already measured the effect on our own settings: of 314
that survived testing, 272 clear our profit bar at stock-broker costs and
only 52 clear it on the crypto venue. Same strategy, same market, opposite
verdict.

**The market hours match the method exactly.** He trades the New York
session and goes home flat. Alpaca's one real restriction — market orders
are rejected outside regular trading hours — is a restriction we never hit,
because we are not trading outside them. On BloFin, a 24/7 market, "the New
York session" is a thing we would have to simulate.

**The account is clean.** Zero orders ever placed, zero positions, $100,000
paper. Every fill that appears on it from now on is the new build's, which
means the week Wallace wants to watch is unambiguous. BloFin's account has
months of ten bots' history tangled through it and Wallace's own trades on
top.

**The data comes from the same place we trade.** 487,235 five-minute SPY
bars going back 10.6 years, free, from the venue that will fill the orders.
No more scraping, and no gap between what we test on and what we trade on.

## The one real difference, stated plainly

**He trades index futures. Alpaca does not offer futures.** We trade SPY and
QQQ, which are funds that track the same two indexes he trades. The charts
are effectively the same shape and the levels sit in the same places, but
they are not literally the same instrument.

What actually changes:
- **Position size gets easier, not harder.** Futures come in fixed lumps.
  Alpaca does fractional shares, so size can be exactly dollars-risked
  divided by stop distance, down to the cent. That is our sizing rule
  working properly for the first time.
- **No overnight session.** Futures trade nearly around the clock; the funds
  do not. Since the method is flat by the close, this costs us nothing.
- **The opening gap is real here.** A fund that stops trading at 16:00 and
  reopens at 09:30 can open away from where it closed. Levels marked
  overnight need to account for that.

## What this does NOT change

The method is the method. Levels off the 4-hour and 1-hour, confirmation and
entry on the 5-minute and 1-minute, stop at chart structure, size out of the
stop, flat by the close. Nothing about the venue touches any of that.

## Status

BloFin account was flat when this was decided — 0 open positions, $1,314.22
— so nothing was stranded. The daemon no longer runs any bot that touches
it. The keys stay in place, unused, rather than being deleted.
