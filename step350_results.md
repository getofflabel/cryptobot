# Round 350 — oil's session clock, tested for money instead of movement

Oil specialist, 2026-07-25. Three parts, one question, plus a live-exposure
audit that came first because it was the only urgent thing on the list.

Market orders on both legs throughout ("taker"). Every stop is a chart level
from `exits.py` — the confirmed swing low for a long, the confirmed swing
high for a short, or a ratcheting floor built from those same confirmed
swings. Never a swept percentage. Size = dollars risked / stop distance, so
leverage is an output, capped at the desk's real 20x ceiling.

---

## PART 0 — what oil is actually trading live right now

**Answer: nothing. Oil is not live anywhere in this repo.**

Read (not edited): `daemon.py`, `tradfi_engine.py`, `daily_pick.py`,
`breakout_book.py`, `gold_book.py`, `spx_book.py`, `news_book.py`,
`morning_read.py`, `config.py`, `exits.py`.

| surface | what it trades | oil? |
|---|---|---|
| `tradfi_engine.py` | `UNIVERSE = [SPX]` | oil removed |
| `daily_pick.py` | BTC-USDT, ETH-USDT, SOL-USDT, XAUT-USDT | no |
| `breakout_book.py` | `SYMBOL = "BTC-USDT"` | no |
| `gold_book.py` | XAUT-USDT | no |
| `spx_book.py` | S&P proxy | no |
| `morning_read.py` | reads CL=F for a macro report; WTIOIL-USDT on a listing watchlist | read-only, places no orders |

The removal is dated and reasoned in `tradfi_engine.py` (lines 148–181),
"OIL STOOD DOWN 2026-07-25 (round 110, oil-trader)". The engine still
defines `OIL = "CL=F"` and still puts it in the futures fee tier, but it is
absent from `UNIVERSE`, so no new oil trade can be scored or opened. The
reconcile loop (line 669) walks `open_trades` regardless of `UNIVERSE`, so
any position still open at stand-down time is exit-managed to completion
rather than orphaned. That is the correct shape for a stand-down.

**Where the numbers that were running came from, for the record.** The rule
set was `daily_pick.py`'s 2-hour-slot crypto scorer imported unchanged —
`score_instrument`, `_stop_target_pct`, `CONVICTION_FLOOR = 40`,
`STOPOUT_COOLDOWN_H = 6`. Every threshold in it was fitted on BTC, ETH and
SOL. None was ever re-derived on oil. Round 110 replayed that exact
decision loop on CL=F's own history (1,888 trades, 2024-03 to 2026-07) and
got **-$37.10 per trade on the first 60% and -$54.05 per trade on the middle
20%, at market-order costs**, sitting at the 81st percentile of a
500-draw random-timing control on the first slice and the 8th on the middle
one — worse than noise out of sample. It also found 19% of trades had their
stop set by a flat 1.0% cap inherited from crypto rather than by oil's own
volatility, which is a swept percentage by construction.

**So the +$58.39 is n=1 under a rule set measured negative on oil.** It is
luck on the scoreboard. Nothing in this round changes that and nothing in
this round rescues it.

---

## PART 1 — does the clock convert a losing shape into a working one?
`step350_oil_session_gate.py` → `step350_table.csv`

The research queue's one unbuilt oil lead: London and New York hours sit at
the 100th percentile of realized absolute price movement against a 200-draw
shuffled control, Asia and off-hours at the 0th. **It reproduces on the
first 60% of the data alone**, so it is not a product of the recent tape:

| session (UTC) | bars | mean absolute 1h move, % of price | percentile vs 200 shuffles |
|---|---|---|---|
| Asia 00–07 | 2,389 | 0.1676 | 0th |
| London 07–12 | 1,800 | 0.3132 | 100th |
| New York 12–21 | 3,238 | 0.3548 | 100th |
| off / maintenance 21–24 | 688 | 0.1780 | 0th |

**Every constant re-derived on oil's own first-60% slice before any backtest
ran**, with what it was elsewhere stated:

| constant | oil's own value (first 60%) | what it was before |
|---|---|---|
| 1h bar range, % of price | median 0.4301, 75th 0.6748, 90th 0.9897 | n/a, new |
| RSI(2) on 1h | 10th pct 7.3, 90th pct 93.4 | S&P book used below 10; BTC step150d used an RSI(3) level |
| ATR(14) 1h, % of price | median 0.4909 | BTC's volatility gate is 1.5%, explicitly not carried |

**Data and split.** CL=F 1h, 13,527 bars, 2024-03-01 → 2026-07-24 (2.40
years, the only intraday oil history this repo holds). Chronological
60/20/20: first slice 8,116 bars (2024-03-01 → 2025-08-11), middle slice
2,705 bars (→ 2026-02-04), final untouched slice 2,706 bars. **The final
slice is truncated off the dataframe inside `load_oil()` before any other
code sees it.**

**Grid**: 3 entry shapes x 3 session arms x 2 chart-structure exits = 18
cells, all screened on the first 60% only. The third arm (Asia + off-hours)
is the placebo: if the clock is real and useful it should be the worst of
the three.

| shape | exit | all hours | London/NY | Asia/off |
|---|---|---|---|---|
| 24h breakout | trailing structure | 271t / **-$11.89** | 241t / **-$9.07** | 109t / -$21.18 |
| 24h breakout | swing stop + 2R target | 268t / -$14.07 | 241t / -$15.11 | 106t / -$23.93 |
| RSI(2) reversion | trailing structure | 212t / -$38.35 | 150t / -$52.05 | 96t / -$47.54 |
| RSI(2) reversion | swing stop + 2R target | 199t / -$42.77 | 140t / -$51.49 | 95t / -$66.95 |
| range expansion | trailing structure | 259t / -$27.84 | 251t / -$24.26 | 38t / -$9.27 |
| range expansion | swing stop + 2R target | 252t / -$23.79 | 244t / -$20.36 | 39t / -$35.85 |

**All 18 cells negative.** London/NY beat all-hours in exactly **3 of 6**
shape-and-exit pairs; a coin flip is 3 of 6. The Asia placebo was worst in
4 of 6 against a 2-of-6 coin flip.

**No cell cleared the floor (at least 30 trades and positive average profit
per trade, losers included), so the middle 20% was never read for anything
and the look budget is intact.**

---

## PART 2 — the floor and the leash
`step351_oil_session_controls.py` → `step351_table.csv`

**The floor: what entering at random times earns**, same chart-structure
exits, same market-order costs, first 60% only, 60 draws of 250 trades each:

| exit | all hours | London/NY | Asia/off |
|---|---|---|---|
| trailing structure | -$33.59 | **-$38.38** | -$25.76 |
| swing stop + 2R | -$36.03 | -$38.70 | -$30.15 |

Two things fall out. First, this is a punishing tape for any single-slot
system: random entries lose $26–$39 per trade after costs. Second, the
24-hour breakout in London/NY hours at -$9.07 **beats random entries in the
same hours by about $29 per trade**. The shape is doing real work. It is
just not doing enough work to cross zero.

**The leash**: part 1 capped holds at 24 hours. Repeating the three-arm
comparison at 24, 48 and 72 hours, first 60% only, nothing selectable:

| leash | exit | all hours | London/NY | Asia/off |
|---|---|---|---|---|
| 24h | trailing structure | -$11.89 | -$9.07 | -$21.18 |
| 48h | trailing structure | -$10.39 | **-$2.41** | -$15.09 |
| 72h | trailing structure | -$10.41 | **-$1.27** | -$12.09 |
| 24h | swing stop + 2R | -$14.07 | -$15.11 | -$23.93 |
| 48h | swing stop + 2R | -$26.07 | -$28.20 | -$27.75 |
| 72h | swing stop + 2R | -$17.35 | -$8.89 | -$37.77 |

**0 of 18 positive.** The closest approach to break-even, -$1.27 per trade,
came from lengthening the leash *after* seeing the first result, which makes
it a weaker piece of evidence, not a stronger one.

---

## PART 3 — is the clock's effect on money bigger than luck?
`step352_oil_clock_significance.py` → `step352_table.csv`

Parts 1 and 2 compared *separate backtest runs*. That comparison is
contaminated, and part 3 is where the round found its most useful thing.

**Apples-to-apples test.** Take one trade population — every 24-hour
breakout on the first 60%, no session filter, same trailing structure stop —
label each trade by the hour it was entered, and compare groups. Then
shuffle the labels 2,000 times.

| leash | all trades | London/NY-entered | Asia/off-entered | gap | percentile vs 2,000 shuffles |
|---|---|---|---|---|---|
| 24h | 271t, -$11.89 | 212t, **-$15.70** | 59t, **+$1.79** | -$17.49 | 22.3rd |
| 48h | 209t, -$10.39 | 169t, -$16.65 | 40t, +$16.07 | -$32.73 | 17.6th |
| 72h | 195t, -$10.41 | 156t, **-$17.76** | 39t, **+$19.01** | -$36.77 | 16.8th |

**On the same trades, London/NY entries did WORSE, not better** — and the
gap is unremarkable against the shuffle (16th–22nd percentile, i.e. the
observed difference sits on the ordinary side of chance, in the opposite
direction to the hypothesis).

**Why parts 1–2 said the opposite: a sequencing artifact.** The engine holds
one position at a time. Filtering Asia-hour entries out does not merely
remove those trades, it frees the slot so *different, later* trades get
taken instead. Measured directly:

| leash | all-hours run | filtered run | filtered-run trades the all-hours run never took |
|---|---|---|---|
| 24h | 271 trades | 241 trades | 41 (17%) |
| 72h | 195 trades | 179 trades | 28 (16%) |

At a 72-hour leash the London-hour trades *inside* the all-hours run average
-$17.76, while the filtered run averages -$1.27. Roughly one trade in six in
the filtered run is a trade the unfiltered run never took. **The apparent
improvement from the session gate is substantially a different trade
population, not the same trades filtered.**

This is a harness caveat every future session, regime or filter study on
this desk needs to know about: **in a single-position engine, adding an
entry filter changes which later trades exist, so filtered-versus-unfiltered
run comparisons are not clean.** The clean version is to run once unfiltered
and split the resulting trades by label, which is what part 3 does.

---

## VERDICT

**The session clock is real for price movement and worthless for money.**
Oil's London and New York hours genuinely move about twice as much per hour
as Asia hours, confirmed again here on the first 60% of the data alone. But
across 18 screened cells plus 18 more at longer leashes, **not one had
positive average profit per trade, losers included**, and on a like-for-like
split of a single trade population the high-movement hours were the *worse*
half by an amount well inside shuffle noise.

More movement is not more edge. It is more movement and the same costs.

No cell cleared the first-slice floor, so **the middle 20% was never read
and the final untouched slice was never loaded.** The look budget for this
family is fully intact, which matters only if someone later has a better
idea to spend it on.

The one thing genuinely worth keeping from this round is not about oil at
all: it is the single-position sequencing artifact in part 3, which would
silently flatter any entry filter tested by comparing two separate runs.

## Files
- `step350_oil_session_gate.py` — part 1, the 18-cell three-arm screen
- `step350_table.csv` — all 18 cells, first-60% statistics
- `step351_oil_session_controls.py` — part 2, random-entry floor and leash check
- `step351_table.csv` — 24 rows
- `step352_oil_clock_significance.py` — part 3, the like-for-like split and 2,000-shuffle test
- `step352_table.csv` — 3 rows
- `step350_results.md` — this file
