# Step 438 — why the build took 2.2 trades a month, and what was misread

The question was never "does his method work". It was "where did WE misread
him". Every entry below is a specific defect with the line of his teaching
that proves it and the cost in trades.

Files touched: `tjr_bot.py`, `tjr_replay.py`, `test_tjr_bot.py`, plus the
four `step438_*.py` measuring scripts. The real release calendar from step439
is wired in (`NewsCalendar` now reads `news_calendar.py`; no call site,
signature or config field changed). No git commands. No orders. `daemon.py`
untouched. **All 43 bot tests and all 15 calendar tests pass, including all
five truncation tests.**

---

## 1. THE REJECTION LOG, RANKED

140 sessions, 280 symbol-days, January 2 to July 24 2026.

| why the step437 build stood down | symbol-days |
|---|---|
| the daily and the 4-hour disagree | **96** |
| news gate (CPI 14, PPI 14, NFP 10, FOMC 10) | 48 |
| no marked level was pushed through before 10:30 | 41 |
| a level was swept but the 5-minute never turned | 37 |
| the 1-minute never broke back with the trade | 14 |
| the two indexes never agreed on the 5-minute | 10 |
| no 5-minute pullback into the midpoint or a gap | 7 |

**Half the symbol-days died before the bell** — 144 of 280, on the news gate
and the daily/4-hour veto together.

Switching each filter off one at a time, which bounds what it costs:

| | trades |
|---|---|
| as step437 shipped | 16 |
| the news gate removed entirely | 18 |
| the daily/4-hour veto removed | 20 |
| the both-index agreement removed | 25 |
| the 09:50 earliest-entry rule removed | 17 |

---

## 2. THE DEFECTS

### D1. The 1-hour is missing from the direction read — 96 symbol-days vetoed

He does not run a two-timeframe agreement test. He runs the daily as the boss
with **two** confirmers under it, and the 1-hour stands in when the 4-hour
does not.

> "We broke structure to the downside on the daily. So, we're bearish on the
> daily. **Not necessarily bearish on the 4-hour. But the 1-hour is saying
> bearish** off this break of structure. So, I'm thinking, 'Hey, what happens
> if we sweep this and then get some conf[irmation]?' Then that looks pretty
> good." — bootcamp Day 52, and he calls it the best setup of that morning.

> "4 hours bearish, daily's bullish, weekly's bullish. **I wouldn't
> necessarily want to be looking for a trade on here until we get at least
> 1 hour bullish confirmation.**" — Day 54.

> "the four hour is like just kind of chop Central, Daily's bullish though,
> one hour broke structure the upside… **this is something that I would
> likely be willing to take**." — Day 49, on gold.

And the case he does refuse is the daily standing alone against both:

> "we're bullish on the four hour but bearish on the daily so odds that we
> take a trade off this relatively low… **this can go to the bottom of my
> list today**." — Day 49, on GBPJPY.

Across twelve worked instrument-mornings in Days 49 to 54 the rule that fits
every one is: **the daily must have a direction, and at least one of the
4-hour and the 1-hour must be with it.** Our code required the 4-hour
specifically and killed the day otherwise.

Measured: the build's rule left 136 of 232 symbol-days live. His leaves 176.

### D2. The New York session high and low were never marked — the largest cost

He names **three** session pairs. We marked two.

> "Asia session highs, Asia session lows, London session highs, London
> session lows, **New York highs, New York lows.** All of these are
> significant draws on liquidity." (`Advanced_Liquidity_Concepts`)

> "1800 to 3 is Asia session. 3 to 8:30 London session. **8:30 back to 1800
> is New York session.** And that encapsulates a full day of trading."

And he trades off this morning's part of that window by name:

> "we do have these London session highs… or **just taking out the pre-market
> New York highs would be pretty solid as well**." — bootcamp Day 53.

`session_levels` marked asia, london and prev_day and nothing else. The
previous New York session's extremes and this morning's pre-market extremes —
the two levels sitting nearest to where the open actually trades — were
absent. That is why 41 symbol-days reported "no marked level was pushed
through": the pool averaged 15.8 levels but none of them were near the money.

Cost: **15 trades → 20**, the single biggest gain of the round. With the New
York levels back, that reason falls from 90 symbol-days to 9.

### D3. A pre-market sweep was thrown away instead of carried forward

His own if/else, and the discriminator is whether price already reacted:

> "if I see that liquidity has already been swept during pre-market **and
> we're already reacting off of it**, awesome. Then this was the liquidity
> sweep for the day and I'm just going to take a trade reactive off of this.
> I'm not looking to be taking a trade off of a liquidity sweep from New York
> market open because the liquidity sweep already happened."
> (`liquidity_profitable_fast`, transcribed at step431 §5.8)

step431 §12.2 step 7 states it as a procedure: if a watchlist level was taken
between 08:30 and 09:30 and a break of structure against it has already
printed, **that is the day's sweep, jump straight to the entry stage.**

step436 recorded this as a conflict with step434's "we need to be waiting for
another form of five-minute manipulation" and resolved it toward step434.
**It is not a conflict.** step434 covers the sweep with no reaction; step431
covers the sweep with a reaction. Two branches of one rule, and we built only
the branch that removes trades.

135 of 232 symbol-days had a marked level taken in that window. Cost: 2 trades.
The entry still cannot fire before 09:50, still needs the pullback, the index
gate and the 1-minute trigger — only the sweep crosses the bell.

### D4. The trade side was never constrained to the daily bias

This one costs trades and we built it anyway, because he says it four times:

> "can we go against daily bias no… we're going to stick to this bias until
> we're proved wrong." — Day 49
> "we have to stay bullish when the daily is telling us Bulls." — Day 53
> "I'm looking for longs because that's what the daily trend is." — Day 52
> "why was it against our trading plan? Cuz we were bearish on the hourly. Um
> we were bullish on the daily, bullish on the 4-hour." — Day 54, refusing a
> gold short that had already set up.

`_direction_allowed` let either side trade on every day that was not a
continuation day. Adding the constraint removes 10 trades (30 → 20) and takes
the average win against the average loss from 1 : 0.772 to 1 : 0.979 and the
net from −$4,222 to −$190. It is the change that turns the results around,
and it is the only change here that lowers the trade count.

### D5. The both-index veto switched itself off

`run_day` fed 5-minute bars only to symbols that had passed their own context
check, so on every day the other index had stood down, `check_index_gate`
compared a symbol against itself and always passed. His rule reads the other
chart's 5-minute trend regardless of whether he would trade that chart:

> "if the S&P 500 and the NASDAQ on the five minute are not aligned, I do not
> want to be taking a trade."

Fixed. Costs 1 trade, and is correctness rather than preference.

### D6. Three plain coding bugs

- `on_5m` referenced `cfg.sweep_max_age_5m_bars`, which does not exist —
  `AttributeError` the moment a sweep aged out. It could not fire inside a
  09:30–10:30 window, so it had never been reached, but it crashed every
  counterfactual that moved the cut-off later.
- Previous-day levels used a fixed one-calendar-day step, which lands on
  Sunday every Monday and on the holiday after every holiday. On those
  mornings the previous day's high and low silently did not exist. Now it
  walks back to the last day that actually traded.
- The index gate was checked while *observing* the 5-minute pullback, so a
  retrace that happened while the two charts were briefly out of step was
  discarded and could never come back. The gate belongs at the entry, where
  `on_1m` already enforces it. His words: "if the indexes weren't aligned at
  the start of the session, that's fine. They can still get aligned later in
  the session. So, let's look for it."

---

## 3. WHAT WAS SUSPECTED AND CLEARED

**The 10:30 cut-off and the confirmation timing are not the problem.**
Removing the 09:50 earliest-entry rule entirely adds one trade, and it is a
loser. Moving to his stated exception ("I take trades at 9:45 sometimes")
changes the result by $3. The clock was not eating the setups.

**The news calendar is not the problem either, in trade-count terms.** It
blocks 48 symbol-days, but removing it entirely adds **zero** trades — every
blocked day fails another filter anyway. Swapping the invented rhythm for
step439's real BLS/Fed dates is worth **+1 trade** (19 → 20) and moves the win
rate from 47.4% to 50.0%: it was a genuine correctness bug (seven days stood
down for nothing, seven traded blind into a live release) and it recovers
almost nothing. That is exactly what step439 predicted.

**The 1-hour and 4-hour level pools are right.** "I kind of like using hourly
building blocks compared to 15 minute building blocks on the S&P" (Day 49).
The missing levels were the session ones, not the pivot timeframes.

---

## 4. BEFORE AND AFTER

January 2 to July 24 2026, 140 sessions, SPY and QQQ, costs charged at the
measured 0.0035% round trip.

| | his | step437 | now |
|---|---|---|---|
| trades per month | 7 to 15 days | 2.3 | **2.9** |
| win rate | 64.29% | 25.0% | **50.0%** |
| average win vs average loss | 1 : 1.233 | 1 : 0.646 | **1 : 0.979** |
| net on $100,000 | no losing month | −$7,343 | **−$190** |
| share of sessions traded | a third to two thirds | 11% | **14%** |

What each change is worth, from the final build backwards
(`step438_grid.py`):

| take this back out | trades | win rate | avg win : avg loss | net |
|---|---|---|---|---|
| nothing — as it stands | 20 | 50.0% | 1 : 0.979 | −$190 |
| the 1-hour in the direction read | 19 | 47.4% | 1 : 0.969 | −$1,129 |
| the pre-market carve-out | 18 | 50.0% | 1 : 1.073 | +$580 |
| the daily-bias side rule | 30 | 46.7% | 1 : 0.772 | −$4,222 |
| the New York session levels | 15 | 40.0% | 1 : 0.841 | −$3,486 |
| all three spec readings at once | 24 | 37.5% | 1 : 0.927 | −$5,226 |

Trades are in `step438_trades.csv`; the step437 baseline is regenerated into
`step437_trades.csv` by reverting the three spec readings.

**We are still far under 7 to 15, and one structural reason is nameable.**
He watches four markets and takes at most one trade a day:

> "do I trade a GBP a Great British pound pair yes I do I trade GBP USD and
> I trade GBP JPY… I trade gold and then I also trade the S P 500" (Day 19)
> "how many trades are you taking? I recommend one trade a day, that's what I
> do, one trade a day, sometimes I'll take two" (Day 29)

So "7 to 15 trading days a month" counts a day on which he traded **any** of
four markets. Our two symbols are the same index twice, and the both-index
veto makes them one decision rather than two. On his own numbers the S&P
alone would be a fraction of 7 to 15. That does not excuse 2.7 — it means the
7-to-15 figure was never a like-for-like check on a two-index bot, and the
honest version of that check needs either his other markets or his own
per-instrument counts.

---

## 5. WHAT IS STILL OPEN

- **Profile 2 implies a direction we do not use.** step434 1A: London pushed
  through a level and did not turn back → New York delivers *that* reversal.
  `london_profile` returns `("manipulation", 0)` and constrains nothing. 97 of
  136 symbol-days carry that profile. Building it would remove trades, not add
  them, so it was left alone rather than guessed at.
- **56 symbol-days now stand down as "a level was pushed through, but only on
  the side the day's bias forbids."** That is D4 working as he states it. It
  is the single largest remaining bucket and worth re-reading him on before
  anyone loosens it.
- **27 symbol-days die on the 1-minute trigger.** Faithful to his verbatim
  sequence; not yet checked bar by bar against a worked example.
- The real release calendar, and a measured SPY/QQQ spread instead of the
  0.01%-of-price stop buffer.

Nothing above was chosen to move a number. Every switch in `Config` carries
the sentence of his it came from, and `step438_grid.py` prints what each one
is worth in both directions.
