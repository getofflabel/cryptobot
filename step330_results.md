# step330 — the Solana structure break, put to a decision

Run: `python3 step330_structure_break_audit.py`.
Data: cached Bybit 1-hour and 4-hour history, no network calls.
Solana history 2021-10-15 to 2026-07-23, 41,809 one-hour bars.
Split in date order: first 60% ends 2024-08-25, middle 20% ends 2025-08-08.

**The final untouched slice of history was NOT loaded by this script, and was
not spent.** Every number below is from the first 60% and the middle 20% only.

**Execution: market order (costs more) on entry and on every exit, always.**
Round-trip cost 18 hundredths of one percent of the position (0.06% fee plus
0.01% half-spread plus 0.02% slippage, each side).

**Stops:** the confirmed swing the entry rests on, per trade
(`exits.stop_structure`). Size = dollars risked (2% of the account) divided by
the stop distance. Leverage is an output, never an input.

---

## PART 1 — what our code actually requires, versus what a trader requires

| practitioner requirement | does our code require it? |
|---|---|
| a confirmed CLOSE beyond the level, not just a wick | **YES** — `bos_chain` compares `close` to the level |
| no entry on the signal bar itself | **YES** — the fill is the next bar's open, at market-order cost |
| the level has at least two prior touches | **NO** — one lone swing pivot is enough |
| a minimum distance travelled past the level | **NO** — any close past it by any amount counts |
| a re-test of the level before entry | **NO** — it enters immediately |

Measured on Solana, first 60% plus middle 20%, 131 signals:

- Solana's own median one-hour true range on the first 60%: **1.464% of price**.
- How far past the level the close actually got: 5th percentile 0.055% of
  price (0.04 of one median hourly range), median 0.577% (0.39 of a range),
  95th percentile 2.254% (1.54 of a range).
- **38.9% of signals cleared the level by less than a quarter of one median
  hourly range. 16.8% cleared it by less than a tenth.** Those are not breaks
  a trader would call breaks; they are the level being brushed.
- Swings actually sitting on the broken level (within 0.15% of it): 1 touch on
  100% of signals by construction, **2 or more on only 19.1%**, 3 or more on
  1.5%.

### Two problems that are bigger than the missing conditions

**1. The stop in the +$218.95 number was not a structure stop.** Round 190
used `train_median_stop_pct`: the median distance-to-structure measured on the
first 60%, collapsed to ONE fixed percentage for every trade in both windows.
On Solana that median came out at **6.12% of price and was then clipped to the
code's 6.00% hard ceiling**. So every trade in that result used a flat 6% stop
and a flat 12% target. **53.8% of the real per-trade structure distances are
wider than that 6% ceiling**, meaning on more than half the trades the stop sat
INSIDE the level where the chart says the idea is wrong. That is a swept
percentage, which the desk standard forbids. The reported worst realized move
was -6.03% in price and the MEDIAN realized move was -6.03% too, which is the
signature of a fixed stop, not of chart structure.

**2. Bitcoin's 1.5% volatility gate is buried inside this survivor.** One of
the five confluence votes is the 4-hour bias, and that vote calls
`vol_gated_ma(min_atr_pct=1.5)`. On Solana that gate is **open on 98.3% of
4-hour bars** (Solana's own median 4-hour true range is 2.852% of price). The
vote is therefore not a volatility-gated trend on Solana at all; it degenerates
into a plain 20/100 moving-average cross agreeing with the 4-hour structure
chain. This is the same porting failure the desk already documented for the
standalone trend edge, and it was living inside the survivor unnoticed.

### The comparison to Bitcoin was never apples-to-apples

Round 150 scored Bitcoin's version with real per-trade structure stops and
risk-based sizing. Round 190 scored Solana's version with the flat 6% stop and
full-account sizing that compounds. **The two numbers were produced by two
different measurement systems.** The "$218 on Solana, Bitcoin could not hold
it" asymmetry could not be read off those two runs. Part 2 fixes that.

---

## PART 2 — the same entry, scored the way Bitcoin was scored

Real per-trade structure stop, size = risk / stop distance, market orders.
Percent-of-position is the size-independent number; the dollar figure moves
with account size and should not be compared across measurement systems.

### Bitcoin's 1.5% gate ported unchanged (exactly as Round 190 ran it)

| variant | first 60% | middle 20% | how many times bigger than the cost of trading (middle 20%) | verdict |
|---|---|---|---|---|
| as shipped | 60 trades, +$62.87/trade, +1.551% of position | 25 trades, +$96.44/trade, +1.860% of position | 10.3x | survivor |
| + close must clear the level by 1/4 of a median hourly range | 43 trades, +$132.90, +3.699% | 18 trades, +$112.36, +2.530% | 14.1x | survivor |
| + clear by 1/2 a median hourly range | 31 trades, +$135.09, +4.032% | 11 trades, +$86.35, +2.339% | 13.0x | survivor |
| + level must have 2 swings on it | 14 trades, +$17.23 | 6 trades, +$312.63 | 47.5x | **NOT ENOUGH TRADES** |
| + wait for a re-test | 50 trades, +$48.04, +1.120% | 21 trades, +$60.59, +1.273% | 7.1x | survivor |
| + clear by 1/4 range AND re-tested | 33 trades, +$44.53 | 14 trades, +$111.29 | 13.3x | survivor |

**The $218.95 was mostly a sizing artifact.** Under honest risk sizing the
same entry pays +$62.87 and +$96.44 per trade, because the position is only
about a third of the account (average leverage 0.4x) once the stop is where the
chart puts it. The size-independent number is close to unchanged: 1.55% and
1.86% of the position, against Round 190's 1.51%. The edge did not shrink; the
dollar headline did.

**Adding the missing practitioner condition helps, it does not hurt.**
Requiring the close to clear the level by a quarter of a median hourly range
cuts the trade count from 60 to 43 on the first 60% and roughly doubles the
profit per trade. That is the Round 86 pattern repeating: the condition
practitioners insist on was missing, and adding it improves the family.

**The two-touches requirement runs out of sample.** Only 19.1% of signals have
a second swing on the level, which leaves 14 and 6 trades. Under the floor of
30 and 8, so it is reported as not enough trades, not as a 47x edge.

### The gate re-derived on Solana's own history (2.85%)

| variant | first 60% | middle 20% | verdict |
|---|---|---|---|
| as shipped | 52 trades, +$30.67, +0.865% of position (4.8x cost) | 18 trades, +$114.50 | thin on the first 60% |
| + clear by 1/4 range | 37 trades, +$93.65, +2.903% | 14 trades, +$166.69, +3.963% | survivor, 22.0x cost |
| + clear by 1/2 range | 27 trades, +$116.34 | 8 trades, +$46.89 | NOT ENOUGH TRADES |
| + 2 swings on the level | 14 trades | 5 trades | NOT ENOUGH TRADES |
| + re-test | 42 trades, +$5.79 (0.9x cost) | 14 trades, +$67.88 | too thin on the first 60% |
| + 1/4 range AND re-test | 28 trades, +$0.95 | 11 trades, +$146.69 | NOT ENOUGH TRADES |

The as-shipped version is **noticeably weaker once Bitcoin's constant is
replaced by Solana's own** (+0.865% of position on the first 60%, 4.8x the cost
of trading, below the 5x bar). The version with the minimum-distance condition
holds up under both gate choices, which is the more robust of the two.

---

## PART 3 — is the money in the entry or in the exit?

Round 117 on oil found an apparent breakout edge was really the exit riding a
rising market: random entries with the same exit did better. Same control here.
Random entry bars, same stop and target and time cap, same window, same costs,
same number of trades, same long/short mix, 200 runs.

| variant | window | real | random-entry average | beats |
|---|---|---|---|---|
| as shipped | first 60% | +$62.87/trade | **-$21.84/trade** | 97.5% of 200 runs |
| as shipped | middle 20% | +$96.44/trade | **-$27.93/trade** | 96.5% of 200 runs |
| + clear by 1/4 range | first 60% | +$132.90/trade | **-$15.21/trade** | **100% of 200 runs** |
| + clear by 1/4 range | middle 20% | +$112.36/trade | **-$20.11/trade** | 96.0% of 200 runs |
| + clear by 1/2 range | first 60% | +$135.09/trade | **-$17.94/trade** | 98.0% of 200 runs |

**This is the opposite of the oil result.** The exit apparatus on its own
LOSES money on Solana in both windows. Random entries into the same stop, the
same 2-to-1 target and the same 10-day time cap average roughly -$20 to -$28
per trade. Every dollar of the result is coming from WHEN it enters, not from
how it gets out. The entry has information.

Luck accounting: with six variants judged against a 95th-percentile bar,
expect 0.30 of them to clear it by luck alone, and there is a 26.5% chance at
least one does. Two of the cells above beat 98% or more of random runs and one
beat 100% of 200 runs, which is beyond what six draws of luck produces.

---

Every variant beat its own random-entry control in both windows, and the
random control never made money in any variant, in either window. The exit
apparatus is not the source of the result.

---

## PART 4 — does the same rule still work on a different coin?

Ten other coins with cached history. The shape of the rule is UNCHANGED. The
one volatility number in it (the 1.5% gate inside the 4-hour bias vote) is
RE-DERIVED on each coin as that coin's own median 4-hour true range, and the
minimum-distance condition is expressed in multiples of that coin's own median
hourly range, so nothing is copied. Same market orders, same per-trade
structure stop, same risk sizing, same 200-run random-entry control (120 runs
per coin here).

Chosen on Solana's first 60% only: require the close to clear the level by a
quarter of a median hourly range.

| coin | first 60% | middle 20% | % of position (middle 20%) | times the cost of trading | beats random | verdict |
|---|---|---|---|---|---|---|
| **SOL** | 43 trades, **+$132.90** | 18 trades, **+$112.36** | **+2.530%** | **14.1x** | 96.0% | survivor |
| BTC | 66 trades, -$45.31 | 22 trades, +$44.12 | +0.681% | 3.8x | 90.8% | **FAIL** |
| ETH | 47 trades, -$43.42 | 11 trades, +$8.82 | +0.216% | 1.2x | 67.5% | **FAIL** |
| ADA | 57 trades, +$9.80 | 14 trades, -$29.35 | -0.784% | -4.4x | 50.0% | **FAIL** |
| AVAX | 47 trades, +$59.25 | 7 trades, -$125.90 | -3.513% | -19.5x | 11.7% | NOT ENOUGH TRADES |
| BNB | 49 trades, +$55.73 | 9 trades, +$66.27 | +1.322% | 7.3x | 85.8% | survivor |
| DOGE | 48 trades, -$27.92 | 15 trades, +$63.74 | +1.997% | 11.1x | 85.0% | **FAIL** |
| LINK | 52 trades, -$27.98 | 7 trades, -$117.98 | -3.635% | -20.2x | 16.7% | NOT ENOUGH TRADES |
| LTC | 54 trades, -$16.23 | 10 trades, -$18.13 | -0.546% | -3.0x | 62.5% | **FAIL** |
| XRP | 41 trades, +$3.25 | 10 trades, -$1.04 | -0.039% | -0.2x | 66.7% | **FAIL** |
| DOT | 57 trades, -$6.93 | 12 trades, +$101.86 | +3.203% | 17.8x | 96.7% | **FAIL** (first 60% negative) |

The as-shipped version transfers no better: 2 of 10 coins positive in both
windows, neither of them clearing the 5x cost bar.

### What luck alone would produce, and why this is a failure

If the rule had no edge and each window were a coin flip, **2.5 of 10 coins
would show both windows positive by luck**. We observed **1** with the chosen
variant and **2** with the as-shipped variant. **The transfer produced fewer
passing coins than coin-flipping would.** The one pass, BNB, sits at 9 trades
in the middle 20% against a floor of 8, and beats only 85.8% of random runs,
which is inside what one lucky draw out of ten looks like.

Two further details that matter more than the headline:

- **The two coins Solana is most correlated with, Bitcoin and Ethereum, both
  fail on the FIRST 60%** with clearly negative profit per trade (-$45.31 and
  -$43.42). This is not a close call that a different threshold rescues.
- **DOT looks great and is a trap.** +$101.86 per trade in the middle 20%,
  17.8x the cost of trading, beating 96.7% of random runs, and its first 60%
  is negative. That is a number wandering, and it is what the Solana cell
  would look like if we only ever read one window.
- Solana has the best first-60% profit per trade of all eleven coins tested.
  Being best of eleven is what a fitted result looks like when you have eleven
  draws.

---

## THE FINAL UNTOUCHED SLICE OF HISTORY WAS NOT SPENT

Morgan's instruction was to look only if parts 1 to 3 all passed cleanly. Part
1 found the stop in the original number was a swept flat percentage rather
than chart structure, and found Bitcoin's volatility constant living unnoticed
inside the rule. Part 3 (does it work elsewhere) failed. **The look was not
spent and remains available.**

---

## WHAT IS TRUE AND WHAT IS NOT

**True:** on Solana, and only on Solana, this entry carries real information.
It beats a random-entry control using the identical exit in both windows, and
the random control loses money on its own, so this is not the oil case where
the exit was doing the work. Adding the missing practitioner condition (make
the close clear the level by a real distance) improves it rather than harming
it, and it survives replacing Bitcoin's ported volatility constant with
Solana's own.

**Not true:** the "+$218.95 per trade" headline. That number came from a flat
6% stop, a flat 12% target, and full-account sizing that compounds. Measured
the way the desk actually measures, with the stop where the chart puts it and
size set by dollars risked, the same entry pays +$62.87 and +$96.44 per trade,
or 1.55% and 1.86% of the position.

**Not established:** that this is a Solana property rather than fitting. Ten
fresh coins say no, and they say no more emphatically than chance would.

**A separate problem for the desk's standing 15-20x priority:** the honest
stop on this rule averages 6.8% to 7.5% of price. Dollars risked divided by
that distance gives an average leverage of **0.3x to 0.4x** — the position is
smaller than the account. This is a wide-stop, low-leverage, ten-day-hold
strategy, which is the opposite of the tight-stop tier the owner asked every
round to optimize for. Worst single-trade move against the position was
**-17.99% in price** and the 5th percentile was -11.4% in price, so a tighter
stop is not available here without changing the idea.

