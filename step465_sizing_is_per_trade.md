# step465 — sizing is per trade now. It did not fix the money, and here is why.

Window: the most recent 12 months, **2025-07-25 to 2026-07-24**, 251 real
sessions, SPY and QQQ. Same harness and same profit-and-loss basis as step461
(`step456_baseline.run`), so the numbers below sit directly beside its table.
Nothing here goes back further than a year.

---

## 1. The number, first

| | trades | days traded | win rate | sum R | money |
|---|---|---|---|---|---|
| what was running before this round | 209 | 128 | 45.5% | +19.34 | **−$7,110** |
| **per trade, top of his band — SHIPS** | **347** | **128** | **45.5%** | **+16.94** | **−$9,320** |

**It got worse by $2,210 over the year.** That is the answer and it is not a
good one.

**One correction to the number the brief carried.** step461's −$10,362 row is
its "bias + clock" line. The bias switches all ship OFF; only the clock change
shipped. So the build that was actually running is step461's row C, −$7,110.
−$10,362 is what the bot would do if the daily-lean change were also switched
on, and it is not. Both are in step461's own table.

**Agreement with his 73 dated recaps did not move at all: 50.0% (36 of 72)
before and after, the same days and the same directions.** Sizing decides how
big, never whether. This round is purely about money.

---

## 2. Why it got worse, and it is not the sizing rule

**At the top of his band the bot is asking for more leverage than Alpaca will
carry, on nine trades in ten.**

Leverage is an output of where the chart put the stop, never a dial:

    leverage = what the trade may lose, over the stop distance as a move in
               the PRICE

His stops on SPY and QQQ run about a third of one per cent of price. At the top
of his band that arithmetic asks for **a median of 10.6x**. Alpaca's day-trade
buying power gives **4x**.

| the dial | leverage ASKED, median | leverage ACTUALLY USED, median | range used | the venue could not deliver on | money |
|---|---|---|---|---|---|
| quietest | 1.8x | **1.8x** | 0.2x – 4.1x | 15% of trades | **+$258** |
| quiet | 3.6x | **3.6x** | 0.4x – 4.2x | 44% of trades | **+$1,099** |
| middle | 7.1x | **4.0x** | 0.9x – 4.3x | 77% of trades | **−$7,114** |
| **top of his band — SHIPS** | **10.6x** | **4.0x** | **1.3x – 4.4x** | **90% of trades** | **−$9,320** |

**The money turns negative exactly where the 4x ceiling starts to bite, and
for a mechanical reason.** When the venue caps the position, the position stops
being "a fixed amount at risk" and becomes "a fixed 4x of equity" — and at a
fixed 4x, what the trade stands to lose goes straight back to being
proportional to how wide the stop is. That is the precise thing per-trade
sizing was built to remove. Above 4x it comes back.

The two quiet settings are on the table because the brief required the band he
did **not** pick to be visible in one line. They are not a recommendation and
nothing was changed on their account.

---

## 3. The diagnosis that was asked for: are losses sized bigger than wins?

**No. They never were, and after the change they are smaller.**

| | stop distance, a move in the PRICE | what the trade stood to lose | leverage used, median | average result |
|---|---|---|---|---|
| **before** — winners | 0.387% | $857 | 2.4x | +$668 |
| **before** — losers | 0.398% | $872 | 2.5x | −$619 |
| **after** — winners | 0.338% | $1,151 | 4.0x | +$910 |
| **after** — losers | 0.309% | $1,073 | 4.0x | −$810 |

A loser was 1.02 times a winner before and is 0.93 times a winner now. On
averages there was never an asymmetry worth $7,000 a year.

**So the day budget was not the cause, and neither is stop distance in the way
the brief guessed. The cause is the SPREAD of position sizes, not their
average.** Before this round the dollars behind a trade ran from $22 to $3,082
on the same account — a 140-fold spread — while the allowance itself only moved
8-fold. The rest came from holding the set size still, so a wide stop bought a
bigger position. And wide-stop trades are structurally the LOW-reward ones,
because the targets are drawn levels that do not move further away when the
stop widens.

Sort the year's trades into four groups by how much each stood to lose:

| quarter, by what the trade stood to lose | average result per trade | total |
|---|---|---|
| smallest | +$52 | **+$2,704** |
| second | −$38 | −$1,996 |
| third | +$54 | +$2,819 |
| **largest** | **−$201** | **−$10,638** |

**The biggest positions sat on the worst trades.** That is the whole of how a
book with a positive sum of R loses money, and it is why R and dollars
disagreed. Per-trade sizing collapses that spread — and it does, whenever the
venue can deliver the size. At the quiet setting the ceiling binds on 44% of
trades and the book makes money on a +24.37 sum of R. At the top of the band
the ceiling binds on 90% and the spread comes back through the clamp.

---

## 4. The dial

One value, in `tjr_bot.Config`, and it is the only thing to touch:

    risk_pct_per_trade = 0.03

Wallace set it at the top of his stated band, knowingly, on paper money, after
being told the band is aimed at a book with a high win rate and a low
reward-to-risk, and that this book is the other kind. **That is his decision,
recorded as his decision and not as a finding of ours.**

Everything else is an output: the leverage the bot actually uses comes from
where the chart put the stop, and the table in section 2 is what it came to.

---

## 5. What was retired, and what it was

Every part of the machinery that made one trade's size depend on the rest of
the day is off. All of it is still reachable, whole, behind
`size_per_trade=False` — which is how the recorded baseline is reproduced, and
`step456_baseline.py --check` still prints **identical**.

| retired | what it was |
|---|---|
| the day's allocation (`DayBudget`) | **OURS.** Every sentence behind it is real, but he says all of it narrating one day, not stating a rule |
| the half-share when a second setup is forming | **OURS**, same source |
| the floor below which the day was over | **OURS, and marked ours at the time** — "he gives no floor" |
| the outer ceiling being a pot the day drew down | **OURS** — the number is his, attaching it to the day was not |
| holding the set size still off the tightest stop | **HIS**, and retired for another of his: "1 to 3% of my account per trade". He has moved the same way himself — 2026-01-16, cut the contract size when the stop is drastically wider |

---

## 6. OURS, NOT HIS — what this round had to invent

- **The equity a trade is sized off is the session's OPENING equity**, not
  marked to the minute. He never says which. Opening equity is what makes one
  trade's size independent of every other trade that day, which is the
  property that was asked for.
- **The news-day half size carried across to the per-trade number**
  (`news_day_halves_the_trade`). Halving on a news day is his; he says it about
  a day's risk and not explicitly about a per-trade number.
- **The per-trade outer ceiling is set equal to the dial itself** rather than
  to a second number. With the size worked out off today's own stop the
  allowance is spent exactly, so it never binds — it is a guard against a
  future change, not a dial.
- **The 3.5x day-loss tripwire** is inherited unchanged from step461 and now
  only guards the old path. He gives no ceiling on a day's realised loss at all.

---

## 7. What was not closed, stated rather than buried

- **`tjr_desk._size_for` does not say which sizing rule it wants**, so an order
  it re-sizes uses the old one. Measured: it lands on **exactly** the replay's
  size on every trade in the record, and it is bounded so it can only ever come
  in at or under, never over. `test_the_desk_can_only_ever_under_size` holds
  both. Closing it properly means the desk forwarding one more field, and
  `tjr_desk.py` was out of bounds this round.
- **Gold and currencies are pinned to the old ledger**, with the reasoning
  written at the line in `tjr_gold.gold_config` and `tjr_forex`. This was
  measured on the index book and nowhere else, and the venue ceiling that
  turned out to dominate the answer is Alpaca's 4x on shares — a different
  number on other venues.
- **`tjr_crypto.py` was not opened.** The concurrent crypto round picked the
  change up on its own, attributed it to step465 by name, and re-recorded its
  setup count with the reason written down. Nothing was tangled.

---

## 8. Safety

`test_tjr_bot.py` **87 passed**. `test_tjr_crypto`, `test_tjr_desk`,
`test_tjr_forex`, `test_tjr_gold`, `test_paper`, `test_exits`,
`test_stand_down_gates`, `test_live_imports` — **228 passed**. Causality and
truncation tests unchanged and passing. `step456_baseline.py --check` prints
**identical**.

The 11 pre-existing failures step461 recorded in the retired BloFin-era books
are untouched and still theirs.

Files changed: `tjr_bot.py`, `tjr_alerts.py`, `test_tjr_bot.py`,
`step456_baseline.py` (one flag), `tjr_gold.py` and `tjr_forex.py` (one pinning
line each, to PREVENT a change rather than make one). **No git commands of any
kind. No orders. The Alpaca account still has zero orders ever placed.**
