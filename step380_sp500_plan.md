# STEP 380 — THE S&P BOT ON ALPACA (`sp500.py`)

Built 2026-07-25. **Nothing has been deployed and no order has been placed.**
The Alpaca paper account still shows zero orders ever. `sp500.py` ships with
`NEW_ENTRIES_ENABLED = False`.

The deadline is real, and **this plan had the date wrong**. Corrected against
round 362's own definition (`step362_spx_round2.month_position`: fire when
`days_left == E`, where `days_left` counts the sessions that come AFTER the
signal bar inside its month and 0 means the month's last session):

| | date | why |
|---|---|---|
| signal bar | **Monday 27 July 2026, at the close** | four sessions come after it in July: the 28th, 29th, 30th and 31st |
| entry fill | **Tuesday 28 July 2026, at the open** | bar N's signal, bar N+1's open — backtest.py's own convention |
| exit fill | **Friday 7 August 2026, at the open** | eight trading sessions after the entry session |

The original line ("the close of Wednesday 29 July") counted the 28th to the
31st inclusive as "four trading days before month end". That is two sessions
late against the rule as it was measured, and it would have missed the
window. `sp500.py` implements `days_left == 4` and `test_sp500.py` pins
those three dates against the real 2026 calendar.

---

## THE ROUND-370 FINDING, WHICH LANDED AFTER THIS PLAN WAS FIRST WRITTEN

Round 370 split the turn-of-month lift into the part earned while the
market is open and the part earned while it is shut:

| | open to close | close to next open |
|---|---|---|
| SPY turn-of-month lift | +0.0176% of price = 0.44x a round trip | **+0.0468% of price = 1.17x** |
| QQQ turn-of-month lift | +0.0181% of price = 0.45x | **+0.0807% of price = 2.02x** |

The lift is 2.7 times larger in the closed hours than in the session on SPY
and 4.5 times larger on QQQ. **That is WHY the validated rule works by
holding 7 to 8 days — it is collecting overnight windows, not trading
days.** Round 370 also measured the whole session, open to close, at 0.41
times the cost of a single round trip.

Three things follow, and all three are now structural to `sp500.py`:

1. **It must hold across nights.** There is no flatten-before-the-close
   anywhere in the file. `test_sp500.py` runs the cycle through four
   session boundaries, with the market both open and shut, and asserts the
   position is still held and no sell order left the file; it also greps
   the source for the shapes a future edit would use to add one.
2. **It must be robust to the market being shut.** Decide at the close, act
   at the next open. A decision that comes due while the market is shut is
   deferred, logged and alerted, and the bar is deliberately NOT marked
   processed.
3. **No intraday behaviour, and no trading around the position.** The
   session itself does not pay for a round trip, so there is nothing
   intraday in the file on purpose.

---

## WHAT IT TRADES, AND WHERE EVERY NUMBER CAME FROM

Only the two things round 362 actually validated. Nothing else, and no
re-tuning of either.

### Rule 1 — turn-of-month (`turn_of_month`)

| setting | value | source |
|---|---|---|
| entry | at the close **4 trading days before month end** | step362_results.md, Family B, SPY's best cell |
| hold | **8 trading days**, then out | same cell |
| filter | only while price is **above its 200-day average** | same cell |
| measured | +0.5947% of the position per trade, 158 trades, 14.9x the cost of trading; middle slice +0.2601% over 71 trades | same |

It was the round's best result and the only rule that passed the coin-flip
control on all three instruments, on both scoreboards, in both pools. 51 of
70 settings survived on SPY, so this is a broad plateau, not a spike. E and H
are the exact pair the round selected. They are not re-tuned here and there
is no sweep in this file.

### Rule 2 — the RSI2 deep-dip buy (`rsi2_dip_buy`)

| setting | value | source |
|---|---|---|
| entry | 2-day RSI **below 5**, while above the 200-day average | step362_results.md, Family A and C |
| exit | close back above the **5-day average**, or the 2-day RSI **above 65** | round 60's exit, carried through 362 unchanged (`step362_spx_round2.dipbuy_exit`) |
| measured | +0.8803% of the position per trade, 22x the cost of trading, 100th out of 100 against the coin flip in both pools | step362_results.md |

**SPY only.** Round 362 placed the futures version 78.5th against the coin
flip, so round 60's "12 of 12 on both instruments" was one real edge on the
ETF and one exit riding a trend on the futures. This file trades SPY and only
SPY, and the docstring says why so nobody ports it later by accident.

It is a plateau: 0.921% at threshold 2, 0.880% at 5, 0.765% at 8, falling off
smoothly. Threshold 5 is the round's own cell.

### What is deliberately NOT in here

- **The SMA200 regime rule** ("stay long above the 200-day average") —
  demoted. Per trade it loses to a coin flip on all three markets, 6.8th out
  of 100 on SPY. It is a drawdown blanket, not an entry edge. It survives in
  this file only as a *filter* on the two rules above, which is what round
  362 validated it inside.
- **The vol-gated trend** — rejected (79.8th / 40.2th / 16.2th).
- **The breakout port** — split verdict, not confirmed.
- **Hidden bullish divergence** — a candidate, not validated: it passes the
  coin-flip test on all three markets but SPY's middle slice is +0.0113% over
  21 trades, which is barely positive. **It is the first thing that gets
  added if it clears another round**, and `sp500.py` says so at the registry
  where it would be appended.

---

## FILE STRUCTURE

`sp500.py`, in order:

1. **Constants** — the two rules' exact parameters, the venue's real cost,
   the risk budget, the memory-loop thresholds.
2. **`NEW_ENTRIES_ENABLED = False`** and the reasoning for where the gate sits.
3. **Formatting helpers** — every percentage carries its base
   (`price_move_pct`, `position_value_pct`, `account_pct`).
4. **The memory loop** — `RuleMemory`, `read_ledger_trades`, `read_lessons`,
   `_parse_learnings_md`, `_count_rule`, `load_memory`,
   `apply_memory_stand_downs`, `clear_rule_stand_down`. Copied in shape from
   `bitcoin.py` (built the same day) and pointed at the same
   `data/ledger.csv` and `data/learnings.md`.
5. **The trading calendar** — `us_market_holidays`, `venue_sessions`,
   `trading_days_left_in_month`. Turn-of-month needs to know how many
   sessions are LEFT in the month, which is forward-looking information; the
   venue's own calendar is asked first and a computed NYSE calendar is the
   fallback, with the source named in the log.
6. **The rules** — `RuleSignal`, `EntryRule`, `anchor_swing`,
   `structure_stop`, `rule_turn_of_month`, `rule_rsi2_dip_buy`,
   `ENTRY_RULES`, `evaluate_rules`. (Built as ONE public `structure_stop`
   returning both the level and the swing it rests on, rather than the
   planned private `_structural_stop` plus a separate provenance call — a
   stop and the swing it is traceable to should not be two functions that
   can disagree.)
7. **The arbiter** — `arbitrate`, memory-aware, never takes a flagged rule
   silently.
8. **State and venue reads** — `account_snapshot`, `position_snapshot`.
9. **The market-hours gate** — `market_gate`, `send_market_order`,
   `make_client_order_id`.
10. **Sizing** — `size_from_risk`; size = dollars risked / stop distance.
11. **The close** — `write_lesson`, `close_trade`.
12. **The exit logic** — `exit_due`, the one place a held trade is judged.
13. **The cycle** — `run_sp500(venue, state, dry=False)`.

`test_sp500.py` sits beside it, repo style: plain asserts, a `main()` runner,
no pytest, no network.

---

## HOW THE MARKET-HOURS GUARD WORKS

Round 360 found that **Alpaca rejects market orders outside regular trading
hours**. Both rules decide at a daily close and fill at the next open, which
is inside the session, so the strategy survives — but the bot must never
discover the rule by having an order bounced.

- `market_gate(venue)` calls `venue.clock()` and returns
  `{"open": bool, "why": ..., "next_open": ..., "session_date": ...,
  "clock_ok": bool}`. `session_date` is the session the bot would act in:
  today while the market is open, otherwise the day it next opens. That one
  value is what makes the hold countable in sessions and what tells
  `load_daily` which partial bar to drop.
- **A clock that cannot be read counts as shut.** Not knowing is not a
  reason to fire.
- **Every order in the file goes through one function**, `send_market_order`,
  and that function raises `MarketClosed` if the gate is shut. There is no
  second path to the venue.
- An exit that comes due while the market is closed is **deferred, logged and
  alerted**, never sent. The next cycle inside the session takes it.
- Entries are the same: the signal is recorded, the bar is NOT marked
  processed, and the entry is taken at the next cycle inside the session.

The daily frame is built so the decision bar is always a **closed** one: any
bar dated on the current New York session date is dropped. So the bot decides
on yesterday's close and fills inside today's session, which is exactly the
fill convention `backtest.py` uses (bar N's signal, bar N+1's open).

---

## THE STOP, THE SIZE, AND THE OVERNIGHT GAP

- The stop is **chart structure**, computed per trade:
  `exits.stop_structure(k=5, n_back=1, use="wick")` on the daily frame — the
  last confirmed swing low below the entry, via the same fractal pivots
  `step41_shorts.confirmed_swings()` defines. Two different entries produce
  two different stop distances; there is no swept percentage anywhere.
- **No trailing.** `bitcoin.py`'s ratcheting floor and its 1.5%-of-price
  buffer were validated on BTC 4-hour bars. Round 362 measured a stop that
  sits at the structure level as of entry and stays there. Constants do not
  travel; neither do mechanisms.
- **Fallback only when no confirmed swing exists yet**: 2.26% of price under
  entry for the dip-buy, 4.24% for turn-of-month — round 362's own measured
  middle distances with 5-bar swings, so the fallback is the same magnitude
  the mechanism produces rather than an invented number.
- **The overnight gap does not threaten these stops.** Round 362 measured it:
  the overnight move alone exceeded the 1.84% dip-buy stop on 1.3% of days
  and the 3.12% turn-of-month stop on 0.2% (0.8% and 0.1% with 5-bar swings).
  What died in round 60 was a tight ~1.3% stop at one times the average daily
  range. That is not this. **The code says so where the stop is defined so
  nobody re-tightens it.**
- **Size = dollars risked / stop distance.** Risk is 2.0% of the account's
  equity, read from the venue. Leverage is an output: round 362 measured this
  lands at roughly 0.9x the account for the dip-buy and 0.5x for
  turn-of-month, both below 1x, so the bot never borrows. Two caps shrink the
  position rather than widening the risk budget: never more than the
  account's own equity, and never more than the buying power the venue
  reports.
- Fractional shares are supported, so the size that falls out of the stop is
  taken as-is down to 0.001 of a share.

---

## THE STOP'S ONE REAL WEAKNESS, STATED PLAINLY

On BloFin the stop is placed **on the exchange**, so it survives this process
being dead. Here it is **evaluated by the bot**: `alpaca.py` exposes market
orders and position-close only, and this task was not allowed to modify it.

Consequences, all of them written into the file:

- The stop fires on the next cycle that runs **inside a session**, not
  instantly.
- It is checked against both the last closed bar's LOW (so a level touched
  intraday still counts) and the live price.
- The measured exposure this leaves is the gap number above: 0.1% to 1.3% of
  days. It is small, it is measured, and it is not zero.
- **The first improvement to make** is a native Alpaca stop order, which
  needs one new method on `alpaca.py` and is out of scope here.

---

## ATTRIBUTION

The account has **zero orders ever**. Every order this file sends carries a
`client_order_id` beginning `CBOT_`, built by `make_client_order_id()`, which
is the only place an id is made. That keeps a perfect line between the bot
and any manual trade Wallace places later. `position_snapshot` reads shares,
average entry, market value and unrealized profit straight from Alpaca —
none of them is derived here.

A position the bot did not record is **not adopted and not flattened**: it
alerts once and keeps operating.

---

## THE MEMORY LOOP

Same shape as `bitcoin.py`, same files:

- **Before deciding**, `load_memory()` reads the last 20 closed trades from
  `data/ledger.csv`, this bot's own closed trades from state, and every
  lesson in `data/learnings.md` plus `state["lessons"]`.
- **Two** consecutive losses on a rule FLAGS it — the arbiter can still take
  it but must attach the note to the record.
- **Three** consecutive losses that all ended the same way STAND IT DOWN,
  latched in state until a human calls `clear_rule_stand_down()`.
- **One plain-English lesson is written on every close**, wins included, in
  the exact schema `export_journal.write_learnings()` renders.

It is a loss counter with a latch on it. It does not learn and nothing in the
file calls it intelligence.

---

## LANGUAGE RULES ENFORCED BY TESTS

- No bare percentage anywhere: every one says "of price", "of the account",
  "of the position's own value" or "of the position".
- The word "book" does not appear in this file at all. It says **bot**.
- Plain English in every log line and alert; the jargon is spelled out rather
  than named.

---

## WHAT IS HARDER THAN IT LOOKS

1. **Turn-of-month needs the future.** "Four trading days before month end"
   cannot be counted from history alone — you have to know how many sessions
   are left, including holidays. The venue's calendar is asked first; the
   computed NYSE calendar (including Good Friday via the Easter calculation)
   is the fallback and is unit-tested against known dates.
2. **The still-forming daily bar.** Alpaca serves today's partial bar during
   the session. Acting on it would be lookahead. It is dropped.
3. **The stop is bot-side**, not venue-side. See above.
4. **Fill prices are not in the order response.** Alpaca returns a market
   order with `filled_avg_price` empty; the bot records the reference price
   and then corrects the entry to the venue's own `avg_entry_price` on the
   next cycle, so the record converges on what the venue says rather than on
   what we guessed.
5. **A deferred order must not mark the bar processed**, or a signal blocked
   by a shut market would be silently skipped forever. Handled explicitly.
6. **`alpaca.py`'s `bars()` needs a `start` date, and this is not
   documented anywhere in the repo.** Verified live on 2026-07-25 and found
   only because the first end-to-end dry run reported "0 closed daily
   bars":
     - A daily-bar request with **no `start`** comes back `"bars": null`.
       Not an error, not an empty list — null. Every such request silently
       reads as "no history at all".
     - `start` plus `limit` returns the **OLDEST** `limit` bars from that
       date forward, not the newest. Asking for 800 bars from 2023-01-01
       hands back 2023-01-03 to 2026-03-12 and stops four months short of
       today.
   So `load_daily()` asks for the window **by date** (640 calendar days,
   about 440 sessions) with a count high enough that it never binds, and
   takes the tail. `test_sp500.py`'s fake venue reproduces the null answer
   exactly, so an edit that drops the start date fails in the test rather
   than reading as an empty market on the live venue.
   **This affects `alpaca.py`'s own `verify()`**, which calls `bars()`
   without a start in three of its four checks and would therefore report
   0 daily bars, 0 five-minute bars and a `latest_close` of None. That file
   was out of scope for this task and was not touched.

---

## STATUS

- `sp500.py`, `test_sp500.py`, `step380_sp500_plan.md` written. Nothing else
  touched. `daemon.py` is untouched, so the file is inert until a human wires
  it in and flips the flag.
- `test_sp500.py`: 16 tests, all passing. Full repo suite green, including
  `test_live_imports.py` and `test_stand_down_gates.py`.
- **No order placed, paper or otherwise. The account has zero orders.**

## THE THREE FOLLOW-UPS, IN ORDER

1. **A native stop order at the venue.** Today the stop is evaluated by this
   bot, so it fires on the next cycle inside a session rather than
   instantly. That needs one new method on `alpaca.py` (a stop or bracket
   order), which this task was not allowed to add. The exposure it leaves
   is measured, not guessed: round 362 put it at 0.1% to 1.3% of days.
2. **A first-class `calendar()` method on `alpaca.py`.** `venue_sessions()`
   asks the venue first and falls back to a computed New York Stock
   Exchange calendar, naming the source in the log every cycle. `alpaca.py`
   has no `calendar()` method, so `venue_sessions()` reaches for the
   client's generic reader instead — and that works: a live read on
   2026-07-25 came back "source: venue calendar" with the correct count.
   Making it a real method would stop that depending on an internal name.
   The computed fallback handles the fixed holidays, the weekend
   observation rule and Good Friday, but it cannot know about an
   unscheduled closure, which is why the venue is asked first.
3. **Add `("sp500", "test_sp500")` to `test_stand_down_gates.GATED_BOOKS`**
   when the file is wired in. `test_sp500.py` already asserts the same
   invariant on its own (the gate's code sits below every path that can
   close a position), but that shared guard is where a stood-down bot is
   proved not to crash, and this task was not allowed to edit it.
