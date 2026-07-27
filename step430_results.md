# Step 430 — measured properties of the market

**Descriptive only. There is no strategy in this file and no verdict in it.**
Everything below is a property of the chart that stays true whatever rules we
end up building. It exists so that when the stated specification comes out of
the transcripts (step431–434), we already know how many setups a chart
actually offers, how far the stops sit, and how far the chart's own targets
are.

Written 25 July 2026. Files: `step430_lib.py`, `step430_t1_sessions.py`,
`step430_levels.py`, `step430_causality.py`. Data: `step430_t1_sessions.csv`,
`step430_level_frequency.csv`, `step430_level_distances.csv`.

## Ground rules used

- **Units.** Every "%" here is a **price move** — how far the price
  travelled. It is never a change in the value of a position. Position value
  moves by the price move times the leverage, and leverage is an output of
  (dollars risked ÷ stop distance), never an input.
- **Costs**, where mentioned: round trip, no commission, measured in round 410
  from about 700,000 real quoted spreads 2016–2026. **SPY 0.0035% of price,
  QQQ 0.0055%.** The playbook's old 0.04% for SPY was a crypto-shaped fee
  model on a commission-free venue and is 11 times too expensive. Crypto on
  BloFin is 0.06% per side.
- **Split.** Everything is measured on the first 80% of each history. The
  final 20% is not opened. For SPY that means nothing from 8 July 2024
  onward was read; for QQQ nothing from 2 August 2024; for Bitcoin nothing
  from 17 April 2025.
- **Definitions.** A **high** is an up candle then a down candle, level at the
  higher of the two wicks; a **low** is a down candle then an up candle, at
  the lower wick — TJR's two-candle definition, not our fractal. A **sweep**
  is price trading through a level and closing back on the original side
  within an hour; if it does not close back, the level is counted as
  **broken**, not swept.

## 0. The confirmation chain does not use tomorrow's prices

Before any number below is worth reading: 80 signals (40 SPY, 40 Bitcoin)
were rebuilt from histories truncated at the signal bar, with nothing after
it in memory — higher-timeframe levels, the live pool of unswept levels, the
sweep, the higher low, the higher high, all recomputed from scratch. **All 80
reproduced exactly: same bar, same side, same stop.** The two-candle swing is
stamped on the second candle and the higher low is only known some bars after
it forms, and both delays survive the rebuild. `step430_causality_out.txt`.

The trade engine used for the distance work was separately checked against a
slow bar-by-bar walk on 575 events across three target sizes and both
position modes — identical to the last decimal place.

## 1. How often the New York open takes out the London session high or low

Sessions on the New York clock as stated: Asia 18:00–03:00, London
03:00–08:30, New York 09:30–17:00. Days where the 09:30 open was already
outside the London range are excluded, because a level already behind price
is taken out for free (that is 26% of SPY days in the early window, 41% in
the later one).

**The measured frequency, SPY, 1,171 days, 2016 to April 2022:**

| | whole NY session | first 60 minutes |
|---|---|---|
| real London high or low taken out | **97.5%** | **84.6%** |
| a level the same distance away, same day's range width | 98.1% | 85.1% |

QQQ: 97.0% real against 96.4% for the matched level. Bitcoin, which has the
full 03:00 London hour we are missing on the index: 87.1% real against 91.5%
matched.

So the frequency itself is real and large — **the London high or low goes on
roughly 97 days out of 100 on SPY** — but a level placed at a random split of
that same day's range width goes just as often. The chance baseline sits on
top of the measurement. What this says, plainly, is that the frequency number
alone cannot tell us the London level is special; it tells us the New York
session normally travels further than the London range. Both facts are worth
knowing and the second one is the one that sizes a day.

One earlier baseline I ran was wrong and I am flagging it so nobody quotes
it: borrowing the distances whole from a random *other* day gives 86.5%,
which makes the real 97.5% look like a large excess. It is not — that placebo
also breaks the link between a wide London range and a wide New York range,
and mismatching the day's own volatility lowers the hit rate by itself. The
volatility-matched number in the table is the honest one.

**Which way price went afterwards**, measured from the close of the bar that
did the taking-out, over the rest of the session:

| | SPY first 60% | SPY middle 20% | QQQ first 60% | QQQ middle 20% |
|---|---|---|---|---|
| bigger remaining move was the other way | 52.1% | 48.7% | 51.0% | 49.7% |
| session closed the other way | 50.1% | 44.5% | 49.8% | 46.7% |

Chance is 50.0% — from any point in a driftless walk the larger remaining
excursion is up or down with equal probability, wherever you are standing.
Bitcoin: 51.2% then 50.9%.

I want to be exact about what this does and does not measure. This counts
**any touch** of the London level, which is not the same thing as a sweep —
through *and back*. The rejection case is the one the framework is actually
about, and separating it is the obvious next measurement. What is in the
table is the touch, and the touch carries no directional information.

**Data limitation, stated plainly:** Alpaca's extended session starts at
04:00 New York time, so on SPY and QQQ the London window measured is
04:00–08:30 and not 03:00–08:30. We are missing the London cash open hour.
Bitcoin has the full window and lands in the same place, so the missing hour
is not what produced these numbers — but the index numbers are on a
four-and-a-half hour London, not five and a half.

## 2. What happens to a level once it forms

Every level is followed for five days and then written off. **SPY, first 80%
of the history:**

| level kind | formed/week | swept | broken | never touched | sweeps/week | median hours to sweep |
|---|---|---|---|---|---|---|
| 5-minute swing | 379 | 76.0% | 20.4% | 3.6% | 288.0 | 0.3 |
| 15-minute swing | 142 | 72.3% | 21.4% | 6.2% | 102.8 | 0.8 |
| 1-hour swing | 36.6 | 64.4% | 22.7% | 12.9% | 23.6 | 2.2 |
| 4-hour swing | 9.9 | 55.5% | 20.4% | 24.1% | 5.5 | 5.2 |
| Asia session | 7.9 | 53.7% | 38.1% | 8.3% | 4.2 | 5.0 |
| London session | 8.0 | 69.3% | 18.8% | 11.9% | 5.6 | 6.5 |
| New York session | 8.3 | 56.2% | 23.1% | 20.7% | 4.7 | 15.4 |
| prior day | 9.7 | 46.9% | 21.9% | 31.2% | 4.5 | 7.7 |

QQQ is within a point or two of SPY on every row. Bitcoin runs hotter
everywhere — 5-minute swings 1,010 formed per week and 78.8% swept, 4-hour
60.3% swept, London session 80.0% swept, prior day 51.2%.

Two things fall out of this table.

**The higher the timeframe, the less often the level gets taken out and the
longer it takes.** A 5-minute level is swept three quarters of the time
within twenty minutes; a 4-hour level a bit over half the time and it takes
five hours; a prior-day level under half the time. That is the shape you
would expect if bigger levels are harder to reach, and it means higher
timeframes buy patience, not certainty.

**A level is far more likely to be swept than broken, at every timeframe.**
On SPY a 1-hour level is swept 64.4% of the time and broken 22.7% — nearly
three to one. That is the raw frequency, with no claim attached about what
price does next.

## 3. How many setups this would actually put in front of us

This is the number Wallace most wants. A sweep is not a trade; the framework
requires the opposite trend to actually form afterwards — a higher low then a
higher high after a swept low, the mirror after a swept high, within two
hours. Counting only those:

| level kind | share of sweeps that confirm | confirmed setups per week | per trading day |
|---|---|---|---|
| **SPY** 5-minute swing | 33.3% | 69.8 | **14.0** |
| SPY 15-minute swing | 35.0% | 28.7 | 5.7 |
| SPY 1-hour swing | 38.0% | 8.1 | 1.6 |
| SPY 4-hour swing | 39.4% | 2.1 | 0.43 |
| SPY prior day | 38.3% | 1.7 | 0.34 |
| **QQQ** 5-minute swing | 33.8% | 67.2 | 13.4 |
| QQQ 1-hour swing | 38.2% | 7.9 | 1.6 |
| **Bitcoin** 5-minute swing | 37.9% | 206.2 | 41.2 |
| Bitcoin 1-hour swing | 42.0% | 22.2 | 4.4 |
| Bitcoin 4-hour swing | 45.3% | 5.7 | 1.1 |

About **a third of sweeps go on to confirm**, and the share rises gently with
the timeframe of the level and is a few points higher on Bitcoin than on the
index. Two thirds of sweeps never produce the reversal sequence at all, which
is the arithmetic behind "a sweep is the opportunity, not the reversal".

On trade count: **5-minute levels on SPY give about 14 confirmed setups a
trading day, which is the ballpark of trading roughly ten times a day.**
1-hour levels give 1.6 a day. 4-hour levels give one every two or three days.
Counting one instrument only — running SPY and QQQ together roughly doubles
it, and these counts are before any additional filter, session restriction or
bias rule from the stated specification, every one of which cuts them.

## 4. Stop distances, and what the chart offers ahead

The stop sits at the swept extreme. "Risk" is the distance from the fill —
the next open after the confirmation — to that extreme, as a price move.

| | risk, median | risk, quarter to three-quarter range | bars from sweep to confirmation |
|---|---|---|---|
| SPY 5-minute swing | 0.216% | 0.126 – 0.381% | 6 |
| SPY 1-hour swing | 0.259% | 0.150 – 0.459% | 6 |
| SPY 4-hour swing | 0.282% | 0.159 – 0.511% | 6 |
| SPY prior day | 0.254% | 0.148 – 0.446% | 6 |
| QQQ 1-hour swing | 0.371% | 0.211 – 0.638% | 6 |
| Bitcoin 1-hour swing | 0.642% | 0.393 – 1.029% | 6 |
| Bitcoin 4-hour swing | 0.848% | 0.550 – 1.362% | 6 |

**Three practical readings.**

*The stops are reachable and they are small.* A typical SPY stop is about a
quarter of one percent of price. At $740 a share that is roughly $1.85 of
stop per share. Risking $100 on a trade means about 54 shares, roughly
$40,000 of position — so this setup asks for leverage on a small account, and
the leverage is an output of that stop, not a dial. On Bitcoin the same setup
carries two to four times the stop distance, so the same dollar risk buys
roughly a third of the position.

*Against costs, the stop is enormous.* SPY's round trip is 0.0035% of price
and the median stop is 0.216% — the stop is about **62 times the cost of
getting in and out**. Costs are not what decides this setup on the index.
That is a different world from crypto, where BloFin's 0.06% per side against
a 0.64% stop is about 5 times.

*The confirmation is quick.* Median six 5-minute bars from the sweep
completing to the entry signal, at every level timeframe and on every
instrument. That is a half-hour decision, not an all-day wait.

**What the chart offers ahead of the fill**, measured at the confirmation
bar, using only levels that had formed and had not been taken out by then:

| | nearest unswept level ahead | as a multiple of the risk | share of setups with a stacked pool ahead |
|---|---|---|---|
| SPY 5-minute swing | 0.078% | 0.36x | 75.4% |
| SPY 1-hour swing | 0.264% | 1.10x | 29.8% |
| SPY 4-hour swing | 0.646% | 2.60x | 7.8% |
| SPY New York session | 0.649% | 2.95x | 7.2% |
| SPY prior day | 0.904% | 3.87x | 7.8% |
| Bitcoin 1-hour swing | 0.657% | 1.09x | 24.3% |
| Bitcoin prior day | 3.383% | 3.46x | 2.8% |

This is the most useful column in the round. **The target the chart offers
scales with the timeframe of the level, and it scales faster than the stop
does.** Going from 5-minute levels to prior-day levels on SPY multiplies the
stop by 1.2 but multiplies the distance to the next untaken level by 11.6 —
0.36 times the risk becomes 3.87 times the risk. On 5-minute levels the
nearest untaken level is *closer than the stop*, so a chart-derived target
there is structurally worse than one-to-one before anything else is
considered.

The stacked-pool column carries a caveat that matters: pools are counted
within a single level kind, so higher-timeframe rows look sparse (7.8% of
4-hour setups have one) simply because few 4-hour levels are alive at once.
A real implementation would pool levels across timeframes and these shares
would rise. Do not read 7.8% as "stacked pools are rare on the 4-hour" —
read it as "this measurement did not look across timeframes yet".

## 5. What I did not finish, and what is worth measuring next

Stopped mid-round when the method changed, so stating the state honestly:

- **The rejection case is not separated from the touch case.** Section 1
  counts any touch of the London level. The framework is about price going
  through and coming back. Splitting section 1 by whether the bar closed back
  inside the London range is a small change to `step430_t1_sessions.py` and
  it is the single measurement I would add first.
- **Stacked pools across timeframes** — merging 5-minute, 15-minute, 1-hour,
  4-hour and session levels into one pool before clustering, as above.
- **Session-restricted counts.** Every count in sections 3 and 4 is over all
  hours including extended. Restricting to the New York cash session, which
  is where he trades, will cut them and is a one-line filter.
- **The Asia and New York session levels are measured but their sweep
  timing is not** — median 15.4 hours from a New York session level forming
  to it being swept means most of those sweeps land in the next day's
  overnight, not the next day's session.
- **Nothing was run on a trade population**, so there is no profit figure in
  this file and there should not be one. The engine and the random-entry
  control are built, verified and ready in `step430_lib.py` for whenever the
  stated specification arrives.

## Files

| file | what is in it |
|---|---|
| `step430_lib.py` | loaders, two-candle and fractal swings, higher-timeframe level mapping, sweep and confirmation scanners, a vectorised trade engine verified against a bar-by-bar walk, random-entry control |
| `step430_t1_sessions.py` / `.csv` / `_out.txt` | section 1, both chance baselines |
| `step430_levels.py` / `step430_level_frequency.csv` / `step430_level_distances.csv` / `_out.txt` | sections 2, 3, 4 |
| `step430_causality.py` / `_out.txt` | the truncation test |

No git commands were run, no live file was touched, no order was placed.
