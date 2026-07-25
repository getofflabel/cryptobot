# Round 341 — GOLD: six new strategy families on the map

Script: `step341_gold_family_ports.py`. Table: `step341_table.csv` (139 cells).

Market orders throughout (execution="taker"). 60/20/20 in date order, choices
on the first 60% only, middle 20% read once, final untouched slice never
loaded. At least 30 trades in the first slice and 8 in the middle slice or
the cell reads NOT ENOUGH TRADES.

Instruments: GLD daily (2004-11-18 on), the gold future daily (2000-08-30 on),
and IAU daily (2005-01-28 on) added this round as a second gold
exchange-traded fund so the volume-based family has a second instrument at
all. IAU is a WEAK second opinion because it holds the same metal as GLD; the
gold future is the real independent check and is used wherever it can be.

Costs: GLD and IAU 0.04% for a round trip, gold future 0.02%. **Every profit
is also expressed against the live venue's cost, 0.18% for a round trip
(BloFin XAUT, market order).** That is what the bot would really pay and it
is the number that decides things.

---

## THE HEADLINE

**Six families added. Five of them contain configurations that survive on two
or three gold instruments. Not one of them clears 5 times the live venue's
cost of trading on both windows.** Gold is full of statistically real,
cross-instrument-confirmed signals that are too thin to trade at 0.18% a
round trip. The thickness and the frequency move in opposite directions, and
the 5-times bar bites right where the frequency becomes useful.

| # | family | ported from | best cross-instrument result | trades a year | times the LIVE venue's cost |
|---|---|---|---|---|---|
| 1 | volume-gated Bollinger-band breakout | round 87 (Bitcoin/Ethereum) | ungated 20/2.0 bands: GLD +0.857%/+0.773%, IAU +0.784%/+0.880% | 4.2 | 4.8x / 4.3x |
| 2 | turn of the month | round 130 (S&P) | 3 days before through 3 days after, SURVIVOR on all three instruments | 12.0 | 1.8x-3.1x |
| 3 | very-short-term dip-buy, properly specified | round 60 (S&P) | 2-day reading under 5 + above the 200-day average, SURVIVOR on all three | 2.9-3.2 | 1.7x-2.7x first 60%, 4.8x-5.1x middle 20% |
| 4 | trend with a volatility gate | round 54 (Bitcoin) | nothing clears the trade minimum except one cell | 0.4-2.2 | n/a |
| 5 | the overnight gap (gold's own) | new | gap-down continuation short, SURVIVOR on GLD and IAU | 12-29 | 0.4x-1.2x |
| 6 | the proven breakout shape on intraday bars | gold's own, round 55 left it un-looked | break of the prior 20-bar high, hourly, SURVIVOR on three intraday series | **28.6-106** | 1.1x-3.1x first 60% |

What luck alone would produce is stated per family below.

---

## FAMILY 1 — volume-gated Bollinger-band breakout

**The desk's flagship port hypothesis, and the gate itself fails.**

The original (round 87, Bitcoin and Ethereum hourly): bands 20 bars wide at
2.5 standard deviations, entry only when the breakout bar's volume is at least
1.2x or 1.5x its own 20-bar average.

Gold's own volume behaviour, re-derived on each instrument's own first 60%:
GLD's volume against its own 20-day average has a median of 0.90x, a 70th
percentile of 1.16x and an 85th percentile of 1.44x. IAU: 0.87x, 1.13x,
1.55x. So Bitcoin's literal 1.2x gate happens to keep the top 27% of gold
days, which is close to gold's own 70th percentile — the numbers nearly
coincide here, which is the exception, not the rule, and it is stated because
it was checked rather than assumed.

The gold FUTURE is excluded from this family entirely: its volume series from
the data provider has 382 zero-volume days inside the first 60% and a median
of 78 contracts. That is front-month roll noise, not real traded volume. This
is why IAU was added.

Result: **the volume gate does not help.** The best cell on both instruments
is the UNGATED 20/2.0 band breakout:

| instrument | first 60% | middle 20% | trades a year | times live venue cost |
|---|---|---|---|---|
| GLD, no volume gate | +0.857% x54t | +0.773% x22t | 4.2 | 4.8x / 4.3x |
| IAU, no volume gate | +0.784% x55t | +0.880% x20t | 4.3 | 4.3x / 4.9x |
| GLD, volume at least 1.16x | +1.136% x40t | +0.258% x14t | 3.1 | 6.3x / 1.4x |
| IAU, volume at least 1.13x | +0.479% x30t | +1.075% x14t | 2.3 | 2.7x / 6.0x |

The gate lifts the first 60% on GLD and then collapses the middle 20% from
+0.773% to +0.258%; on IAU it does the opposite. That is noise, not a gate.
At the wider 2.5-standard-deviation setting every gated cell falls under the
30-trade minimum.

The short mirror is buried again, emphatically: -2.14% per trade on GLD,
-2.09% on IAU. Gold shorts are now 0/58 across this program.

**Verdict: the gate is DEAD on gold. The ungated band breakout survives on
two instruments at 4.3x-4.9x the live venue's cost, just under the bar, and
it is very likely the same edge as the channel breakout wearing a different
hat (4.2 trades a year, same shape, same market).** It does not add frequency
and it does not add a new answer.

---

## FAMILY 2 — turn of the month

The original (round 130, S&P): long from 3 trading days before month end
through 3 trading days into the new month. This is a **calendar** rule. There
is no volatility number in it, so there is nothing to re-derive — stated
explicitly so nobody assumes a threshold was carried over. Five window widths
were tested on gold's own bars in case gold's month-end flows have a
different shape.

**SURVIVOR on all three gold instruments, at every window width tested.** The
S&P's own 3-and-3 window is also gold's best:

| instrument | first 60% | middle 20% | trades a year | times live venue cost |
|---|---|---|---|---|
| GLD | +0.369% x157t | +0.503% x52t | 12.1 | 2.0x / 2.8x |
| gold future | +0.321% x187t | +0.329% x62t | 12.0 | 1.8x / 1.8x |
| IAU | +0.382% x155t | +0.566% x52t | 12.0 | 2.1x / 3.1x |

What luck would produce: the comparison point is gold's own unconditioned
daily drift over the same window, which the round-340 control measured
directly — random entries with a trend-following exit earned +0.13% to +0.64%
per trade depending on era. The turn-of-month window's +0.32% to +0.57% sits
inside that band, which is the honest reading: **this is a real and highly
consistent calendar tilt (three instruments, five window widths, both windows,
2000-2022) that is not distinguishable from gold's general drift and is far
too thin to pay 0.18% a round trip.**

**Verdict: real, confirmed across instruments, REJECTED on thickness at
1.8x-3.1x.** It is worth keeping as a sizing tilt on a position held for other
reasons, not as a standalone trade.

---

## FAMILY 3 — very-short-term dip-buy, properly specified. THE ROUND-86 PATTERN REPEATS.

Round 48 buried the dip-buy on gold at 1 survivor out of 72. **That version
had a fixed hold, a fixed target, and no longer-trend condition.** The S&P's
round-60 version is a different shape: buy when the 2-day relative-strength
reading drops under 5 **AND the price is above its own 200-day average**;
leave when the close gets back above its own 5-day average or the 2-day
reading rises above 65. No target, no clock.

Gold's own thresholds, re-derived: the 2-day reading's 5th percentile is 4.2
on GLD, 4.4 on the gold future, 4.1 on IAU. The S&P's literal "under 5" fires
on 5.7%-6.3% of gold days, which is close enough to gold's own 5th percentile
that both were tested and both were reported.

**The longer-trend condition is load-bearing, and its absence is exactly what
buried the family before:**

| instrument | with the 200-day condition | WITHOUT it (the round-48 shape) |
|---|---|---|
| GLD | **+0.302% x37t / +0.885% x12t, SURVIVOR** | +0.061% x87t / +0.701% x25t, barely positive |
| gold future | **+0.379% x50t / +0.920% x15t, SURVIVOR** | +0.242% x99t / +0.506% x31t |
| IAU | **+0.488% x39t / +0.858% x12t, SURVIVOR** | +0.073% x87t / +0.648% x24t |

And at the looser thresholds the version without the trend condition goes
outright negative on the first 60% on GLD (-0.027%) and IAU (-0.034%) while
the gated version stays positive. **Round 86's lesson repeats on gold: a
family was buried because the version we measured was missing the condition
practitioners call mandatory.**

Thickness: 1.7x-2.7x the live venue's cost on the first 60%, 4.8x-5.1x on the
middle 20%. Frequency 2.9-3.2 trades a year.

**Verdict: a GENUINELY NEW gold family, confirmed on three instruments,
REJECTED on thickness and frequency.** The dip-buy shape is no longer "dead on
gold" — it is "alive but too thin and too rare." That correction belongs in
the playbook.

---

## FAMILY 4 — trend with a volatility gate

The original (round 54, Bitcoin): a fixed 1.5% average-true-range gate. Round
48 already proved that number produces zero trades on gold. Re-derived here as
gold's own trailing one-year median range, recomputed bar by bar.

Gold's own average true range on the first 60%, measured fresh: **1.29% of
price on GLD's daily bars, 1.13% on the gold future's, 1.26% on IAU's.**
Bitcoin's fixed 1.5% gate would be open on 33.0% of GLD days, 23.0% of the
future's and 31.3% of IAU's.

This is worth stating precisely, because it corrects a loose reading of round
48. Round 48's "Bitcoin's 1.5% gate produces zero trades on gold" was about
**hourly** bars, where gold's range runs 0.28%-0.72% and 1.5% essentially
never happens (family 6 below re-measures that at 0.281%-0.547%). On **daily**
bars gold's range is 1.13%-1.29%, so the same gate is open roughly a quarter
to a third of the time. Same market, same threshold, completely different
selectivity depending on the bar size — which is the reason the gate is
re-derived here as gold's own trailing one-year median rather than any fixed
number at all.

Result: **the whole family fails the trade minimum.** The 50/200 average cross
produces 5 to 9 trades in fifteen to twenty years. The 20/100 cross produces
18 to 34. Exactly one cell clears both minimums (the gold future's ungated
20/100 cross, 34 and 8 trades), which is not enough to call anything. The
volatility gate, in either direction, only makes the counts worse.

**Verdict: NOT ENOUGH TRADES. Moving-average crosses are too slow to be a
strategy on gold's daily bars, the same finding the S&P produced for its
golden cross.** The volatility gate itself is untestable here because the
underlying trend shape never fires often enough.

---

## FAMILY 5 — the overnight gap as a tradeable event (gold's own family, new)

Buy or sell at the open the morning after a gap, flat at the close. Nothing is
held overnight, which means **gold's defining risk cannot touch this family at
all** — the overnight gap that blew through 44 of 45 stops in round 48 is the
signal here, not the hazard. Simulated with its own same-day simulator (the
shared engine fills at the next bar's open, which makes a same-day trade
impossible to express); flat $10,000 position, not compounded, so only the
percent figures and verdicts are comparable with the rest of this round.

Gold's own gap distribution, re-derived: GLD's median overnight gap is 0.442%
of price (75th percentile 0.808%, 90th 1.310%), the gold future's is 0.262%
(0.577%, 1.047%), IAU's is 0.444%. The S&P's own gap work used 0.3%/0.5%/0.8%;
**44.3% of GLD days gap more than the S&P's 0.5% threshold versus the S&P's
own 46.6%, but the gold future gaps that much on only 29.3% of days** — the
futures-style near-continuous session is structurally different and that shows
up in the numbers.

Chance baseline: a coin flip on direction, 50%.

Result: 4 survivors out of 36 cells, and **every single one is a SHORT**:

| instrument | configuration | first 60% | middle 20% | trades a year | times live venue cost |
|---|---|---|---|---|---|
| GLD | gap down at least 1.310%, continuation short | +0.119% x165t | +0.070% x31t | 12.7 | 0.66x / 0.39x |
| GLD | gap down at least 0.808%, continuation short | +0.020% x378t | +0.079% x95t | 29.1 | 0.11x / 0.44x |
| IAU | gap down at least 1.328%, continuation short | +0.216% x159t | +0.038% x32t | 12.4 | 1.20x / 0.21x |
| IAU | gap down at least 0.824%, continuation short | +0.069% x365t | +0.049% x94t | 28.4 | 0.38x / 0.27x |

4 survivors out of 36 against 50/50 direction is roughly what luck produces
once you allow four shapes at three thresholds on three instruments. The
consistent direction (all shorts, all after a gap DOWN, on both funds) is
mildly interesting, and the gold future does not confirm it.

**Verdict: DEAD on thickness. 0.11x to 1.20x the live venue's cost is not a
trade, it is a rounding error.** The family has the frequency gold needs
(12-29 trades a year) and none of the thickness. Mapped, closed.

---

## FAMILY 6 — the proven shape on intraday bars (the direct attack on frequency)

Gold's constraint is frequency, not thickness. Round 55 built these signals
and correctly declined to look at them because the hourly history is thin. It
is still thin, so these are **leads, not verdicts**, and the window lengths
are stated next to everything.

Gold's own hourly range, re-derived: GLD hourly median 0.329% of price, gold
future hourly 0.281%, gold future 4-hour 0.547%. Bitcoin's hourly runs about
0.45%. This confirms the playbook's stated 0.28%-0.72% band on fresh data.

| series | history in the first 60% | shape | first 60% | middle 20% | trades a year | times live venue cost |
|---|---|---|---|---|---|---|
| GLD hourly | 1.74 years | prior 20-bar high | +0.568% x55t | +0.426% x19t | **31.6** | 3.15x / 2.37x |
| gold future hourly | 1.43 years | prior 20-bar high | +0.199% x152t | +0.368% x55t | **106.1** | 1.11x / 2.04x |
| gold future 4-hour | 1.43 years | prior 20-bar high | +0.521% x41t | +1.723% x17t | **28.6** | 2.90x / 9.57x |
| gold future hourly | 1.43 years | prior 55-bar high | +0.284% x90t | +0.497% x39t | 62.8 | 1.58x / 2.76x |
| gold future 4-hour | 1.43 years | prior 55-bar high | +0.022% x32t | +1.804% x14t | 22.3 | 0.12x / 10.02x |

**This is the clearest statement of gold's real problem this round produces.**
The same proven shape, moved to hourly bars, fires 32 to 106 times a year and
still has positive expectancy on both windows on three separate intraday
series. It just gets thinner exactly as fast as it gets more frequent: 0.20%
to 0.57% per trade against a 0.18% round trip is 1.1x to 3.2x, under the bar.

The 4-hour gold future is the interesting exception (28.6 trades a year, 2.9x
on the first 60% and 9.6x on the middle 20%) and it is the single most
promising lead in this round, with the honest caveat that its first 60% is
1.43 years and 41 trades.

**Verdict: LEAD, not a verdict. The thin-window rule applies and no sealed
look was spent. Re-run when the hourly history reaches four years.**

---

## WHAT GOES IN THE PLAYBOOK

1. **Gold's thickness figures must be quoted against 0.18%, the live venue's
   market-order round trip, not against the exchange-traded fund's 0.04%.**
   This changes the family verdicts, not just the decimals.
2. **The dip-buy is NOT dead on gold.** The round-48 burial measured a shape
   without the mandatory longer-trend condition. The properly specified
   version survives on three instruments. It is rejected on thickness and
   frequency, not on sign.
3. **A volume gate on a gold breakout is dead**, matching the S&P's round-130
   finding on the same axis.
4. **Moving-average crosses cannot generate enough trades on gold's daily
   bars** to be tested at all.
5. **The overnight gap is mapped and closed**: real frequency, no thickness.
6. **Gold shorts are now 0/58.**
7. **The frequency answer, if there is one, is on 1-hour and 4-hour bars**,
   and it is blocked on history rather than on ideas.
