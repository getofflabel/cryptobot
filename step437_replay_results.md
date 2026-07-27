# Step 437 — the new bot, and what a stretch of trading his way looks like

Three files, and nothing else was touched:

| file | what it is |
|---|---|
| `tjr_bot.py` | the method as one causal decision function, plus `live_step()` for the live loop |
| `test_tjr_bot.py` | 36 tests, plain asserts, `main()` runner, no pytest, no network — **all passing** |
| `tjr_replay.py` | walks real SPY and QQQ sessions through the bot, bar by bar, and writes `step437_trades.csv` |

No git commands were run. No order was placed. `daemon.py` and every existing
bot are untouched. The full repo suite still passes.

---

## 1. THE ANSWER TO THE CHECK THAT MATTERS MOST

He states 64.29% wins and average reward against risk of 1 : 1.233, over
January to June 2026, on roughly 7 to 15 trading days a month.

We now hold minute data for the same months, so the replay was run over his
own window. **Caveat first, because it decides how much the comparison is
worth: he traded index FUTURES. We are on the two funds that track those
indexes. This is the closest instrument we can actually trade, not the same
instrument.** So the line below is "over the same months, on the closest
thing we can trade, our build produced this" — never "we reproduced his
results."

### January 2 to June 30 2026, his stated window

| | his number | ours |
|---|---|---|
| trades per month | 7 to 15 | **2.2** |
| win rate | 64.29% | **23.08%** |
| average win vs average loss | 1 : 1.233 | **1 : 0.613** |
| share of sessions traded | a third to two thirds | **11%** |
| net | no losing month | **−$6,217** on $100,000 |

### January 2 to July 24, everything we hold

123 sessions becomes 140. 16 trades, 25.00% win rate, 1 : 0.667, net −$7,285,
account $100,000 → $92,715.

**We did not beat him on any axis, which is the direction the brief said to
want.** The trade count came in far UNDER his range rather than over it, so
the failure here is over-filtering, not a dropped stand-down. Section 4 says
exactly which choices cause it.

Trade count was checked first, as instructed. At 11% of sessions the bot
stands aside far more than he does. Nothing was tuned to move that number
toward his; the changes in section 4 were made because the spec said so, and
their effect on the count is reported rather than targeted.

---

## 2. DOES THE TRUNCATION TEST PASS

**Yes.** Five separate tests, all green:

- a 4-hour candle starting at 08:00 does not exist to the bot at 10:00, and
  today's daily candle does not exist at all during today
- a two-candle pivot is stamped on the SECOND candle and does not move when
  the bars after it are deleted
- **every one of the 16 real entries was re-decided with every later bar
  deleted from memory, and all 16 came back identical** — same symbol, same
  side, same entry price, same stop, same swept level, same bar
- twelve stand-down days re-decided at 10:29 with the future deleted returned
  the identical reason
- four sampled decision moments through the entry window (09:55, 10:05,
  10:15, 10:25) were unchanged by deleting the future

This is the defect he objects to in ordinary historical replay, and he is
right about it. The guarantee is one line — a higher-timeframe bar is only
visible once its `close_t` has passed — plus the fact that every tracker in
the file is fed bars one at a time, forward only.

---

## 3. THE REGIME SPLIT

Recorded on every trade, computed only from closed daily bars: the daily
trend state plus where the last close sits against a 50-day average.

Under size = dollars risked / stop distance, **raw volatility cancels** — a
market moving three times as much puts its structure three times further
away, so the same risk buys a third of the position. What does not cancel is
how far price runs before the next untaken level stops it. So a trend should
show as better reward against risk at the same risk per trade.

| regime the day opened in | trades | win rate | avg win vs avg loss | mean result |
|---|---|---|---|---|
| trending up | 6 | 33.3% | 1 : 0.576 | −0.497x what was risked |
| trending down | 8 | 25.0% | 1 : 0.741 | −0.491x |
| no trend | 2 | 0.0% | — | −0.781x |

**Sixteen trades cannot answer the question.** The direction is what you
would expect — the two trending buckets beat the flat one — but with 2 trades
in the flat bucket that is noise, not a result. The instrumentation is in
place, which is what was asked for; the answer needs more trades, and the
honest place to get them is forward on the paper account.

---

## 4. EVERY PLACE THE SPEC WAS AMBIGUOUS, AND WHAT I CHOSE

Ordered by how much each one moves the trade count.

**1. Is "the daily and the 4-hour must agree" a veto on the DAY, or a
constraint on which WAY the trade goes?**
step434 §1D and step433 CB-12 read like the latter. step436 §10 settles it
explicitly: the taught method (the previous-session profile) sets the
direction, and the multi-timeframe agreement is a veto on trading at all.
**Chose step436**, because it overrides where the others disagree. Building
it the other way first produced 1.2 trades a month instead of 2.2 — it was
the single most expensive misreading.

**2. The pre-market carve-out, which he states both ways.**
step431 §5.8 and forbidden-rule 14 say a pre-market sweep IS the day's sweep
and you trade off it. step434 STEP 1 says a pre-market push-through does not
count and you need a fresh one after the open. **Chose step434's reconciling
sentence**, which is his own: "we need to be waiting for another form of
five-minute manipulation." So on a day whose marked level was already taken
before the bell, the pool after the open becomes the 15-minute levels rather
than the day being skipped. This is worth about a third of our trades.

**3. Which timeframe supplies the pool on a continuation day.**
He says "five minute lows and like 15 minute lows". Round 430 measured that
on a 5-minute pool the nearest target sits CLOSER than the stop, so such a
setup structurally cannot pay. **Kept the 15-minute half of his sentence,
dropped the 5-minute half.** A test fails if a 5-minute-sourced level is ever
traded.

**4. When two levels are taken on the same bar, which is the setup?**
He never says. **Chose: the higher timeframe wins** (prior-day and 4-hour
above 1-hour and the sessions, above 15-minute), and within a tier the level
pushed furthest. His own "higher time frames hold higher power."

**5. What the losing-streak escalation escalates TO.**
step436 §8 says promote from "sweep + break of structure" to "sweep + break
of structure + a midpoint or a fair value gap". But the current method's
step 3 already requires one of those, so that promotion is a no-op. **Chose:
require BOTH the midpoint AND a live fair value gap** on the pullback. It
never fired in this window because there were never two consecutive losing
weeks with trades in both.

**6. Does a wick past the midpoint count, or must a body close past it?**
step432 §12.8 flags this as unresolved. His language is "poke our head" and
"barely taps". **Chose the wick.**

**7. How long a pending sweep stays alive with no reaction.**
He never gives a number. **Chose 12 five-minute bars**, an hour — round 430
put the median sweep-to-signal gap at 6 bars, so this is a generous ceiling,
and a same-direction break of structure kills it earlier anyway. A guess.

**8. Asia and London on a fund that does not trade at night.**
His Asia window is 18:00–03:00 and London 03:00–08:30. SPY and QQQ do not
trade 20:00–04:00, so we can only measure 18:00–20:00 of Asia and
04:00–08:30 of London. **Chose to keep his windows and take whatever traded
inside them**, rather than invent replacement hours. This is a genuine venue
difference, not a modelling choice, and it makes our session levels different
objects from his.

**9. Where the 4-hour and daily candles start.**
Boundaries are floored in New York local time (00/04/08/12/16/20) so the
4-hour sits where a chart set to New York time draws it, and the daily candle
is the regular session 09:30–16:00, which is what a daily chart of a fund
shows. Tested the alternative (higher timeframes from regular-session bars
only): the daily/4-hour disagreement rate fell from 33% to 26% of
symbol-days, but fewer 1-hour bars meant fewer marked levels and the trade
count did not move. **Kept the extended-hours version.**

**10. The economic calendar.**
He reads Forex Factory. We have no calendar file and no network in this
build, so CPI, PPI, FOMC and NFP are generated from their published rhythms
— NFP the first Friday, CPI the first Tue/Wed/Thu on or after the 10th, PPI
the next business day, FOMC eight Wednesdays a year. **That is ours and it is
approximate.** It blocks 46 symbol-days across the window. The real feed drops
into `NewsCalendar(extra_block=...)`, which is empty by default rather than
invented. **This is the largest single piece of guesswork in the build.**

**11. The spread buffer on the stop.**
He says clear your broker's spread and gives 0.5 points on an index quoted
near 5,000, which is 0.01% of price. **Chose that same ratio.** A guess; a
measured SPY/QQQ spread would be better.

**12. Half size on news days and holidays.**
The mechanism is built and tested, but with no calendar feed the only days it
can currently fire on are ones passed in explicitly. It fired zero times in
this replay. Not silently baked in.

**13. Targets.**
Target 1 is the first 15-minute pool at least 1:1 away — that reconciles his
"one higher time frame draw on liquidity" with his "minimum one to one". If
no such pool exists, the 1:1 floor itself. Target 2 is the next marked
higher-timeframe level beyond it, or twice what was risked if there is none.
50% off at target 1, stop to break even, the rest runs. **No logic anywhere
tries to avoid a runner stopping at break even** — it happened once and is
recorded as a normal outcome.

---

## 5. THE SIZE, AND THE CEILING THE VENUE IMPOSES

Risk 1% of equity, position = dollars risked / stop distance, then clamped to
buying power. **The clamp bound on 4 of 16 trades**, and when it binds it is
logged with what we wanted against what we took. Actual risk ranged from
0.27% to 1.00% of the account; the largest position was $393,940. The tight
end is not the clamp — trade 6 had a 41-cent stop, so 1% of equity wanted
2,437 shares and buying power allowed 639.

Costs are charged at the measured 0.0035% round trip and consulted by
nothing. There is no cost filter anywhere in the build.

The double-size tier ships disabled, nothing reads it, and a test fails if
anything ever does.

---

## 6. WHAT THE STAND-DOWN DAYS LOOKED LIKE

124 of 140 sessions produced no trade. Every reason is recorded per day in
the replay output. Across the window, by symbol-day:

| why he would have sat out | count |
|---|---|
| the daily and the 4-hour disagree | 91 |
| no marked level was pushed through before 10:30 | 41 |
| CPI / PPI / FOMC / NFP blocks the whole day | 46 |
| a level was swept but the 5-minute never turned | 38 |
| the 1-minute never broke back with the trade before 10:30 | 14 |
| the two indexes never agreed on the 5-minute | 11 |
| no 5-minute pullback into the midpoint or a gap | 7 |

Every one of those is tested to actually fire. The funnel, per tradeable
symbol-day: about half get a push-through after the open, about half of those
confirm on the 5-minute, about two thirds of those reach the pullback, and
about half of those trigger before 10:30.

Median push-through 09:40, median confirmation 10:00, median pullback 10:05,
against a hard 10:30. **The clock is what kills most of them, and that is the
method working as stated.**

---

## 7. THE TRADES

All 16 are in `step437_trades.csv` with the date and time, the swept level
and its timeframe, what confirmed it, the entry, the stop and the chart
feature it rests on, both targets, what happened, and the result in dollars
and as a percent of the account. Two examples:

- **2026-07-20 SPY short.** The London session high at 744.83 was pushed
  through in the first five minutes. A 5-minute break of structure down
  confirmed it, both indexes were bearish on the 5-minute, price pulled back
  into a fair value gap, the 1-minute broke up then back down, in at 10:17 at
  744.83. Stop at 748.80, which is above the furthest price reached while
  that high was being taken, plus the spread buffer — $3.97 a share, 236
  shares. Neither target nor stop was reached; flat by the close at 741.91
  for **+$683, +0.68% of the account**.

- **2026-05-07 SPY long.** A 1-hour low swept at 09:45, confirmed, in at
  10:20 with a $1.31 stop. Target 1 was reached, half came off, the stop went
  to break even, and the runner was stopped at break even. **+$338.** That is
  a normal outcome, not a failure.

---

## 8. READY TO WIRE — exactly what the live runner calls

Two functions. Neither can reach a broker; both return an intention.

**Once a minute, from 09:30 to 10:30 New York, while flat:**

```python
out = tjr_bot.live_step(
    data,                     # {"SPY": {"5m": frame, "1m": frame}, "QQQ": {...}}
    now,                      # pd.Timestamp, US Eastern, naive: the CLOSE time
                              #   of the last COMPLETED 1-minute bar
    account=float(acct["equity"]),          # read it from Alpaca, do not compute it
    buying_power=float(acct["buying_power"]),
    clock=cli.clock(),        # /v2/clock. Missing or shut -> it refuses.
    week_pnl=week_pnl)        # {monday_timestamp: pnl} so the escalation works
```

`data` frames need columns `t, open, high, low, close` with `t` = the bar's
START in US Eastern, naive. `tjr_bot.to_et_frame()` converts an Alpaca frame.
The 5-minute frame needs about 95 days of history (the daily and 4-hour
direction); the 1-minute frame needs today from 08:00. Anything after `now`
must be absent — that is the whole point.

Returns `{"action": "stand_down" | "wait" | "enter", "reason": ...}`. On
`enter` it also carries `symbol`, `direction` (+1 long, −1 short),
`reference_price`, `stop`, `shares`, `target1`, `target2`,
`partial_fraction`, `risk_dollars`, `risk_wanted`, `clamped`, and a plain
sentence explaining the setup. One call takes 0.03 seconds.

**Once a minute while a position is open:**

```python
act = tjr_bot.manage_step(pos, last_1m_bar)   # pos = tjr_bot.LivePosition(...)
```

Returns `hold`, `take_partial` (half off, move the stop to `new_stop`), or
`close`. The runner applies the result and updates `pos` — `manage_step`
mutates nothing.

**What the runner must enforce that the bot does not:** one trade per day
(stop calling `live_step` once a position has been opened, win or lose),
persistence of `week_pnl` across restarts, and market orders only inside
regular hours.

**Not yet wired, deliberately:** no order has been placed on the Alpaca
account and none will be from this code.

---

## 9. WHAT IS STILL A TODO

- the real Forex Factory calendar, replacing the rhythm-generated one
- a measured SPY/QQQ spread, replacing the 0.01%-of-price buffer
- the half-size tier has no days to fire on until the calendar arrives
- the regime split needs far more than 16 trades to say anything
- crypto: the `Instrument` config already makes every time rule optional and
  absent by default, so "keep the method, throw away the times" is a config,
  not a code change. The 24/7 day boundary defaults to UTC midnight. Not
  built, not measured, deliberately.
