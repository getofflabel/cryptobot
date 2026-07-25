# STEP 362 — THE S&P BOT'S SECOND RESEARCH ROUND (2026-07-25)

Research only. No orders. No live bot file touched. **Paper only: there is
no account anywhere that can place these trades today** (see
step360_results.md). That does not lower the evidence bar, it decides
which of these is worth a venue.

Everything below: market orders on every fill, both ends, every time. 60%
of history to choose on, the next 20% read exactly once, the final 20%
never loaded. At least 30 trades in the choosing slice and 8 in the middle
slice, else the cell is reported as NOT ENOUGH TRADES.

Files: `step362_spx_round2.py`, `step362_table.csv` (471 settings),
`step362_random_control_table.csv` (29 coin-flip comparisons).

Data spans:

| | daily bars | choosing slice | middle slice | untouched |
|---|---|---|---|---|
| SPY | 8,427 (1993-01-29 to 2026-07-23) | first 5,056 days | 5,056 to 6,741 | 1,686 days |
| ES=F | 6,526 (2000-09-18 to 2026-07-24) | first 3,915 | 3,915 to 5,220 | 1,306 |
| QQQ | 6,886 (1999-03-10 to 2026-07-24) | first 4,131 | 4,131 to 5,508 | 1,378 |

---

## THE HEADLINE: WE RAN THE COIN-FLIP TEST AND ONE OF OUR TWO EDGES FAILED

The index has gone up for most of its history. So a rule whose exit just
sits in a rising market will look profitable even if the entry days are
picked by coin flip. Round 117 killed two strategies on other markets with
exactly this test.

Method: keep the exit, the dates, the costs and the number of entries
identical, and pick the entry days at random instead. 400 draws. Two
random pools: any day at all, and only days when price is already above
the 200-day average (the harsh one, because it asks whether the DIP part
adds anything on top of the TREND part).

Two scoreboards, because the coin-flip version sometimes ends up taking a
very different number of trades:
- **average profit per trade** (the fair one when trade counts match)
- **total grown over the window** (the fair one when they do not)

A rule has to land in the top 5 out of 100 random tries to count.

### Result 1 — the RSI2 deep-dip buy: PASSES on the ETFs, FAILS on futures

| market | pool | real, per trade | coin flip, per trade | where the real rule placed (per trade) | where it placed (total grown) |
|---|---|---|---|---|---|
| SPY | any day | +0.8803% of position | +0.1846% | **100th** | **99.5th** |
| SPY | uptrend days only | +0.8803% | +0.1448% | **100th** | **100th** |
| QQQ | any day | +0.6721% | +0.2285% | 95.3th | 84.0th |
| QQQ | uptrend days only | +0.6721% | +0.1552% | **100th** | **97.0th** |
| ES=F | any day | +0.3450% | +0.1411% | 78.5th | 61.3th |
| ES=F | uptrend days only | +0.3450% | +0.1228% | 95.8th | 78.5th |

**On SPY this is a decisive pass.** The dip-buy makes roughly six times
what a coin flip makes per trade, and it does it against the harsh pool
that already knows to be long in an uptrend. The dip itself is carrying
real information.

**On ES=F it is not distinguishable from luck.** Round 60 reported the
dip-buy as "12 out of 12 settings survived on BOTH SPY and ES=F" and
treated that as the round's cleanest cross-market result. That claim needs
downgrading. The futures version survives the survivor test but does not
survive the coin-flip test, on either scoreboard, in either pool. What
looked like the same edge on two instruments is one real edge on the ETF
and one exit riding a trend on the futures.

**QQQ passes in the harsh pool and is borderline in the loose one.** Call
it a pass with a note.

### Result 2 — "stay long above the 200-day average": DEMOTED, this is not an entry edge

| market | real, per trade | coin flip, per trade | per trade | total grown |
|---|---|---|---|---|
| SPY | +1.7989% of position | **+4.2197%** | **6.8th** | 97.2th |
| ES=F | +1.3742% | **+2.7167%** | **16.2th** | 97.8th |
| QQQ | +1.3718% | **+3.5730%** | **13.8th** | 77.2th |

**Per trade this rule loses to a coin flip on all three markets, badly.**
A random day picked out of an existing uptrend, held to the same exit,
earns more than two and a half times per trade what waiting for the actual
cross earns. The reason is straightforward once you see it: entering
exactly at the cross means eating every whipsaw, where price pokes above
the average and drops straight back under.

It beats the coin flip on total growth on SPY and ES=F, because it takes
three to four times as many trades. But on SPY it still does not beat
simply buying once and never selling (+186.3% for the rule against +240.4%
for buy-and-hold over the same choosing window).

So the honest description is: **this is not an edge, it is a drawdown
blanket.** It cut the worst fall from -56.5% to -29.7% on SPY and from
-57.1% to -20.1% on ES=F. That is worth something, and Round 60 said as
much. What it is not is a validated entry signal, and it should stop being
listed next to the dip-buy as if it were one.

---

## FAMILY B — TURN OF MONTH, BUILT INTO A STRATEGY. THE ROUND'S BEST RESULT.

Round 60 measured this and stopped there. Measuring is not trading. Here
it is a costed rule: buy at the close E trading days before the month
ends, hold H trading days, market order both ends.

70 settings per market. It is a **broad plateau, not a spike**: 51 of 70
on SPY, 57 of 70 on ES=F and 56 of 70 on QQQ kept working on the middle
slice.

Best per market (choosing slice, then the middle slice read once):

| market | rule | choosing slice | middle slice |
|---|---|---|---|
| SPY | buy 4 days before month end, hold 8 days, only when above the 200-day average | +0.5947% of position per trade, **14.9x the cost of trading**, 158 trades | +0.2601% of position, 71 trades |
| ES=F | buy 4 days before month end, hold 7 days, no filter | +0.5243%, **26.2x cost**, 175 trades | +0.7032%, 62 trades |
| QQQ | buy 2 days before month end, hold 6 days, only when above the 200-day average | +0.6642%, **16.6x cost**, 123 trades | +0.6283%, 54 trades |

**Coin-flip test: passes everywhere, on both scoreboards, in both pools.**

| market | per trade | total grown |
|---|---|---|
| SPY, any day | 96.0th | 99.5th |
| SPY, uptrend days only | 97.8th | **100th** |
| ES=F, any day | 98.2th | 99.8th |
| ES=F, uptrend days only | 99.2th | **100th** |
| QQQ, any day | 97.2th | 98.0th |
| QQQ, uptrend days only | 98.8th | **99.8th** |

This is the cleanest thing the index has produced. It fires about twelve
times a year, which is roughly three times as often as the dip-buy, it
works on all three instruments, it sits on a wide plateau of settings, and
it beats a coin flip on every measure we have.

**The catch is the cost bar.** At a stock broker's 0.04% round trip it
clears our "at least five times the cost of trading" rule with enormous
room. On BloFin's SPY-USDT perpetual, the only venue our bot could
technically reach today, a round trip costs 0.1413% and the SPY version
earns only **4.2 times** the cost of trading. **It fails the bar on that
venue.** See the venue section below.

---

## FAMILY C — IS THE DIP-BUY A PLATEAU OR A LUCKY SPIKE? PLATEAU.

Average profit per trade in the choosing window, as a percent of the full
position size. A star means fewer than 30 trades, not enough to judge.

**SPY, above the 200-day average:**

| RSI length | <2 | <5 | <8 | <10 | <15 | <20 |
|---|---|---|---|---|---|---|
| 2 | 0.921* | **0.880** | 0.765 | 0.639 | 0.449 | 0.337 |
| 3 | 0.675* | 0.402* | 0.912* | 0.984 | 0.816 | 0.649 |
| 4 | 0.000* | 0.033* | -0.045* | 1.311* | 0.893 | 0.829 |

Every cell with enough trades is positive, and the value falls off
smoothly as the threshold loosens, exactly the way a real effect should.
**RSI2 below 5 is not a lucky spike, it sits on a smooth slope.** Same
shape on ES=F and QQQ.

One thing worth a round of its own: **removing the trend filter makes the
per-trade profit larger, not smaller.** SPY RSI2 below 2 with no filter
earns +1.698% of position across 45 trades against +0.921% with the
filter, and QQQ RSI2 below 2 with no filter earns +2.368% across 42
trades. That is the rule catching crash bottoms. It will also have a far
uglier worst-fall number, which this round did not properly measure, so it
is a lead and not a finding.

---

## FAMILY D — SHAPES BORROWED FROM OTHER MARKETS, EVERY NUMBER RE-DERIVED

The rule the desk keeps having to relearn: constants do not travel. The
S&P's own average daily range in the choosing window is **1.319% of price
on SPY, 1.360% on ES=F, 1.704% on QQQ**. Bitcoin's vol gate of 1.5% was
set on FOUR-HOUR bars and gold's hourly range runs 0.28% to 0.72%.
Dropping Bitcoin's 1.5% onto daily S&P bars would gate on a level SPY
already clears on 41% of days, ES=F on 44% and QQQ on 60%. That is not the
same rule, it is a different rule wearing the same number. Every gate
below is set as a multiple of each market's own median.

### D1, the vol-gated trend (from Bitcoin, 4-hour bars, 1.5% gate). REJECTED.

Re-derived gate: multiples of 1.319% (SPY), 1.360% (ES=F), 1.704% (QQQ).

It looks spectacular and it is an illusion. SPY's best setting earns
+3.2836% of position per trade, 82 times the cost of trading. Then the
coin-flip test: **79.8th place on SPY, 40.2th on ES=F, 16.2th on QQQ,
per trade.** It fails on QQQ on total growth too (54.5th).

This is the exact Round 117 failure mode: very few, very long trades in a
market that went up. The per-trade number is enormous because the rule
holds for years, not because it picks anything. Rejected.

### D2, breakouts (gold's one validated edge, 20-day channel, 20-day exit). NOT CONFIRMED.

Re-derived by sweeping the channel over 10/20/30/40/55 days and the exit
average over 10/20/40 days. SPY's best is a new 40-day high with an exit
below the 40-day average: +1.1340% of position per trade, 28.4 times the
cost of trading, 64 trades, middle slice +0.6379% over 26 trades.

Coin-flip test: passes on profit per trade everywhere (99.8th to 100th)
but **fails on total growth on all three markets** (89.5th SPY, 75.5th
ES=F, 75.0th QQQ). Split verdict, so it does not pass. Gold's edge does
not obviously transfer to the index. Worth one more look with the trade
count matched properly, not a survivor yet.

### D3, hidden bullish divergence (from Bitcoin, 4-hour bars). NEW CANDIDATE.

Price makes a higher low while the RSI makes a lower low, inside an
uptrend. Re-derived by sweeping RSI length 7/14 and lookback 10/20/40 days
on daily bars instead of Bitcoin's 4-hour bars.

| market | best setting | choosing slice | middle slice | coin flip, per trade | coin flip, total grown |
|---|---|---|---|---|---|
| SPY | higher low with RSI7 lower low over 40 days | +0.7969% of position, 19.9x cost, 59 trades | +0.0113%, 21 trades | 99.8th / **100th** | 98.0th / **100th** |
| ES=F | RSI14 over 40 days | +0.6784%, 33.9x cost, 47 trades | +0.3618%, 25 trades | 99.0th / **100th** | 95.3th / **100th** |
| QQQ | RSI7 over 40 days | +0.7855%, 19.6x cost, 52 trades | +0.3828%, 22 trades | 97.0th / **100th** | 87.8th / **99.3th** |

(two numbers per cell: the loose pool, then the harsh uptrend-only pool)

Every setting tested survived on ES=F and QQQ (6 of 6) and 5 of 6 on SPY.
It passes the coin-flip test on all three markets in the harsh pool. This
is the best crypto-to-index transfer the desk has found. The weak point is
SPY's middle slice, where it barely stays positive (+0.0113% of position
over 21 trades), so it needs another round before anyone calls it
validated.

---

## FAMILY F — WHERE THE STOP GOES, AND A CORRECTION TO THE PLAYBOOK

The stop belongs under the last confirmed swing low, not at a swept
percentage. The backtest engine only accepts one stop distance, so the
distance was **read off the chart**: measure how far the last confirmed
swing low actually sat below the entry price on the days each rule fires,
in the choosing slice only, and take the middle of that distribution.

**SPY, dip-buy entries:** the last confirmed swing low sat a middle
distance of **1.84% below entry** using 3-bar swings (quarter-way 0.77%,
three-quarter-way 2.79%), or **2.26%** using 5-bar swings.

**SPY, turn-of-month entries:** **3.12% below entry** using 3-bar swings,
**4.24%** using 5-bar swings.

### The correction: the structure stop DOES survive the overnight gap

The playbook says the ETF's 17.5-hour dark window makes stops dangerous,
and points at the fact that SPY's price gaps more than 0.3% on 46.6% of
days. That is true and I re-measured it: 46.4% of days in the choosing
window, average overnight move 0.42% of price. On ES=F it is 4.6% of days
and 0.08% average, and on QQQ 59.2% and 0.60%.

**But a stop placed at chart structure is far wider than a typical gap.**
On SPY, the overnight fall alone was bigger than the 1.84% dip-buy stop on
only **1.3% of days**, and bigger than the 3.12% turn-of-month stop on
only **0.2% of days**. With 5-bar swings it is 0.8% and 0.1%.

What died in Round 60 was the tight stop at one times the average daily
range, roughly 1.3% of price, and that verdict stands. A structure stop is
not that. **The index's own chart gives the trade enough room to survive
its own overnight window.** Adding the structure stop costs some profit
but keeps every SPY cell a survivor (dip-buy +0.8803% to +0.5805% of
position, turn-of-month +0.5810% to +0.4229%), and it buys a defined loss.
The one place it broke was ES=F's dip-buy with a 3-bar swing stop, where
the middle slice flipped negative.

### The leverage question, answered, and the answer is no

The brief hypothesised that because the index moves a fraction of what
crypto moves, it could carry far more leverage for the same real risk.
Measured, with size = dollars risked divided by stop distance:

| rule | stop distance | risking 1% of the account | risking 2% |
|---|---|---|---|
| SPY dip-buy, 3-bar swings | 1.84% of price | position **0.5x** the account | **1.1x** |
| SPY dip-buy, 5-bar swings | 2.26% | 0.4x | 0.9x |
| SPY turn-of-month, 3-bar swings | 3.12% | 0.3x | 0.6x |
| SPY turn-of-month, 5-bar swings | 4.24% | 0.2x | 0.5x |

**These are not high-leverage setups. They are below one times the
account.** The index moves less per day than crypto, but its chart
structure is proportionally just as far away, so the stop distance in
percent of price lands in the same neighbourhood and the leverage falls
out the same. The high-leverage thesis is not supported on daily bars. It
could still be true on intraday bars where structure sits closer, and this
round did not test that. That is the open question, not a settled one.

---

## FAMILY E — WHAT SURVIVES AT THE ONLY VENUE WE COULD ACTUALLY REACH

Round-trip cost of one entry plus one exit, as a percent of the full
position size:

- US stock broker on the ETF: **0.0400%**
- CME futures: **0.0200%**
- BloFin's SPY-USDT perpetual, measured live 2026-07-25: **0.1413%**

Our bar is profit at least five times the cost of trading, so a rule needs
**0.2000% of position per trade at a stock broker** and **0.7065% on the
BloFin perpetual**.

314 settings survived both slices across this round. 272 of them clear the
bar at stock-broker costs. **Only 52 clear it on the BloFin perpetual.**

The two that matter:

| edge | profit per trade | at a stock broker | on the BloFin perpetual |
|---|---|---|---|
| SPY RSI2 dip-buy | +0.8803% of position | 22.0x cost — **passes** | **6.2x — passes** |
| SPY turn-of-month | +0.5947% | 14.9x cost — **passes** | **4.2x — FAILS** |
| SPY hidden divergence | +0.7969% | 19.9x cost — **passes** | **5.6x — passes** |

**The venue decides which edge is tradeable.** On a stock broker both
work. On the crypto perpetual the turn-of-month edge, the best result of
this entire round, does not clear the cost bar.

---

## VERDICTS

| what | before this round | after |
|---|---|---|
| RSI2 dip-buy on SPY | validated | **validated and now coin-flip-proof.** Sits on a plateau, not a spike |
| RSI2 dip-buy on ES=F | validated, "12 of 12 settings" | **DOWNGRADED.** Does not beat a coin flip on either scoreboard |
| RSI2 dip-buy on QQQ | untested | passes in the harsh pool, borderline in the loose one |
| stay long above the 200-day average | validated | **DEMOTED to a drawdown blanket.** Loses to a coin flip per trade on all three markets |
| turn-of-month | measured, never built | **NEW SURVIVOR and the round's best result.** Passes every coin-flip test on all three markets, wide plateau, about 12 trades a year |
| hidden bullish divergence (from Bitcoin) | untested here | **NEW CANDIDATE.** Passes the coin-flip test on all three markets; SPY's middle slice is thin |
| vol-gated trend (from Bitcoin) | untested here | **REJECTED.** Classic Round 117 failure: few long trades in a rising market |
| breakouts (from gold) | untested here | **NOT CONFIRMED.** Passes per trade, fails on total growth on all three |
| the overnight gap kills ETF stops | believed | **CORRECTED.** True for a tight one-times-range stop, false for a stop at chart structure, which the gap clears on 0.1% to 1.9% of days |
| the index can carry more leverage | hypothesis | **NOT SUPPORTED on daily bars.** Structure stops of 1.8% to 4.2% put position size below one times the account |

## WHAT THIS ROUND DID NOT DO

- **Intraday structure is still untested.** Opening range, first hour and
  session dynamics remain the biggest hole, and they are where the
  leverage question would actually be settled. We only hold about 730 days
  of hourly bars, which is thin for a 60/20/20 split, and that is the next
  thing to solve.
- **The final untouched slice of history was not opened.** Nothing here
  has been through it.
- The no-trend-filter dip-buy lead in Family C was not measured for its
  worst fall.
- The breakout family needs a coin-flip test with the trade count matched
  before it is closed out.
