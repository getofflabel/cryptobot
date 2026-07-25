# Round 340 — GOLD: pushing the one survivor (the channel breakout)

Script: `step340_donchian_audit.py`. Tables: `step340_table.csv` (36 cells),
`step340_table_control.csv` (16 control rows).

Market orders throughout (execution="taker"). 60/20/20 in date order, every
choice made on the first 60% only, the middle 20% read exactly once, the
final untouched slice never loaded by this file. At least 30 trades in the
first slice and 8 in the middle slice or the cell is marked NOT ENOUGH
TRADES.

Windows: GLD daily 2004-11-18 to 2026-07-23 (choose on 2004-11-18..2017-11-14,
read once 2017-11-15..2022-03-16). Gold future daily 2000-08-30 to 2026-07-23
(choose on 2000-08-30..2016-03-18, read once 2016-03-21..2021-05-20).

---

## THE HEADLINE, STATED FIRST

**Gold's "17 times the cost of trading" figure is measured against the wrong
cost.** It is measured against the exchange-traded fund's 0.04% round trip.
The bot would trade XAUT on BloFin with market orders, which costs **0.18%
for a round trip** (0.06% fee + 0.01% half-spread + 0.02% slippage, each
side). Against the cost the bot would really pay:

| shape | instrument | middle 20%: profit per trade as a percent of the full position | times the RESEARCH instrument's cost | times the LIVE VENUE'S cost | trades a year |
|---|---|---|---|---|---|
| break of prior 20-day high | GLD | +0.644% | 16.1x | **3.58x** | 5.3 |
| break of prior 20-day high | gold future | +0.952% | 47.6x | **5.29x** | 4.7 |
| break of prior 55-day high | GLD | +1.834% | 45.9x | **10.19x** | 2.5 |
| break of prior 55-day high | gold future | +1.096% | 54.8x | **6.09x** | 2.7 |

The 20-day version, the one the desk quotes at 5.4 trades a year, sits at
**3.6x on GLD and 5.3x on the gold future** once the live venue's cost is
charged. That straddles the 5-times bar rather than clearing it. The 55-day
version does clear it comfortably (6.1x and 10.2x) but fires only 2.5 to 2.7
times a year.

---

## JOB 1a — the audit against what a practitioner actually requires

Four conditions practitioners call mandatory on a channel breakout, and what
our version does about each:

| condition | does our version require it? |
|---|---|
| a CONFIRMED CLOSE beyond the channel, not a wick poking through | **YES, already.** `donchian_ema_exit` compares the bar's CLOSE to the prior N-bar high. A wick that pokes above and closes back inside never triggers. |
| NO ENTRY ON THE SIGNAL BAR ITSELF | **YES, already.** `run_backtest` fills at the NEXT bar's open by construction. |
| a filter on the direction of the LONGER trend | **NO. Was missing.** Added and tested below. |
| a MINIMUM CHANNEL WIDTH (do not buy the break of a dead-flat range) | **NO. Was missing.** Added and tested below. |

Two of four were already right, which is worth saying plainly rather than
claiming the family was untested. The two missing ones were added.

### The longer-trend filter is the load-bearing one, but only on the first 60%

Requiring the close to also be above its own 200-day average, on top of the
breakout:

| instrument | shape | first 60%, unchanged | first 60%, plus the 200-day filter | middle 20%, unchanged | middle 20%, plus the filter | trades a year |
|---|---|---|---|---|---|---|
| GLD | 20-day channel | +0.725% x67t | **+1.196% x47t** | +0.644% x23t | +0.354% x20t | 5.2 -> 3.6 |
| gold future | 20-day channel | +0.544% x89t | **+0.833% x72t** | +0.952% x24t | +0.776% x20t | 5.7 -> 4.6 |
| GLD | 55-day channel | +0.901% x39t | **+1.071% x35t** | +1.834% x11t | +1.524% x11t | 3.0 -> 2.7 |
| gold future | 55-day channel | +0.466% x55t | +0.434% x53t (the only one it does not lift) | +1.096% x14t | +1.124% x12t | 3.5 -> 3.4 |

The filter lifts profit per trade on the first 60% on **three of the four
combinations** (the gold future's 55-day channel is the exception, edging down
from +0.466% to +0.434%). On the middle 20% it improves two and worsens two, and on GLD
it nearly halves the 20-day version (+0.644% down to +0.354%). It also costs
roughly a third of the trade count, which gold cannot spare.

**Verdict: do NOT adopt it.** A condition that helps where we chose and is a
coin flip where we did not is exactly the shape of a fitted improvement. It
also makes gold's worst problem, frequency, worse.

### The minimum-channel-width filter is actively harmful. Clean negative.

Gold's own channel widths, re-derived on each instrument's own first 60% and
never carried between them:

| instrument | 20-day channel width, median | 20-day, upper quarter starts at | 55-day, median | 55-day, upper quarter |
|---|---|---|---|---|
| GLD | 6.68% of price | 8.94% | 11.59% | 15.81% |
| gold future | 6.37% of price | 8.47% | 11.07% | 14.58% |

Every single cell with a width floor is worse than the same cell without one,
on both instruments, and **all 12 of them fall below the 30-trade minimum**.
Several go outright negative on the first 60% (the 55-day channel with a width
floor: -0.21% to -1.20% per trade). Requiring the range to be wide before
buying the break simply deletes gold's good trades.

This is a genuine negative result and it goes in the playbook: **a practitioner
condition that is real elsewhere does not apply to gold's breakout.**

---

## JOB 1b — the entry-versus-exit control (round 117's control)

Random entry bars, the identical exit rule (first close below the 20-day
exponential average), the identical window, the identical costs, 500 draws.
Reported as: where does the real breakout entry sit in the distribution that
luck alone produces?

| instrument | shape | window | real entries | random entries with the same exit | where the real entry sits |
|---|---|---|---|---|---|
| GLD | 20-day | first 60% (13.0y, gold rose 173.6% in price) | +0.725% x67t | mean +0.140% | **96.6th percentile** |
| GLD | 20-day | middle 20% (4.3y, gold rose 47.4%) | +0.644% x23t | mean +0.267% | 78.0th percentile |
| GLD | 55-day | first 60% | +0.901% x39t | mean +0.133% | **96.2nd percentile** |
| GLD | 55-day | middle 20% | +1.834% x11t | mean +0.253% | **96.6th percentile** |
| gold future | 20-day | first 60% (15.5y, gold rose 357.8%) | +0.544% x89t | mean +0.046% | **93.6th percentile** |
| gold future | 20-day | middle 20% (5.2y, gold rose 49.8%) | +0.952% x24t | mean +0.565% | 75.2nd percentile |
| gold future | 55-day | first 60% | +0.466% x55t | mean +0.024% | 87.6th percentile |
| gold future | 55-day | middle 20% | +1.096% x14t | mean +0.642% | 74.2nd percentile |

**The entry is real, and it is not the whole story.** On the long first-60%
windows the breakout entry beats 88 to 97 draws out of 100. That is the answer
to "is this just the exit riding a rising gold market": no, not over 13 to 15
years.

But on the middle 20% the picture thins to the 74th-78th percentile for three
of four cells, and the reason is visible in the same table: **random entries
with this exit are themselves worth +0.27% to +0.64% per trade in the modern
window, versus +0.02% to +0.14% in the older one.** In the 2016-2022 stretch
gold rose hard enough that almost any entry with a trend-following exit made
money. A meaningful part of the recent performance IS the exit riding the
rise. Morgan's suspicion was correct in direction, wrong in degree.

### The second control: hold the trend regime constant

If the 200-day filter helps, is that the breakout or just being in the market
during rising stretches? Random entries drawn **only from bars that already
pass the 200-day filter**:

| instrument | shape | window | real | random inside the same regime | where the real entry sits |
|---|---|---|---|---|---|
| GLD | 20-day + filter | first 60% | +1.196% | mean +0.245% | **97.8th percentile** |
| GLD | 20-day + filter | middle 20% | +0.354% | mean +0.219% | 61.4th percentile |
| GLD | 55-day + filter | first 60% | +1.071% | mean +0.233% | 93.2nd percentile |
| GLD | 55-day + filter | middle 20% | +1.524% | mean +0.224% | 92.2nd percentile |
| gold future | 20-day + filter | first 60% | +0.833% | mean +0.098% | **97.4th percentile** |
| gold future | 20-day + filter | middle 20% | +0.776% | mean +0.553% | 64.6th percentile |
| gold future | 55-day + filter | first 60% | +0.434% | mean +0.078% | 80.0th percentile |
| gold future | 55-day + filter | middle 20% | +1.124% | mean +0.634% | 71.4th percentile |

Same story, sharper. Once the trend regime is held constant, the 20-day
breakout on the middle 20% drops to the 61st-65th percentile of luck. The
55-day breakout on GLD holds at the 92nd. **The slower channel is the one
carrying real entry information into the recent window.**

---

## JOB 1c — the same rule on the other instrument

The two conditions were re-derived separately on each instrument (the width
numbers above differ by instrument and were never copied). Four configurations
survive on both GLD and the gold future:

| configuration | GLD first 60% / middle 20% | gold future first 60% / middle 20% |
|---|---|---|
| 20-day channel + close above 100-day average | +1.046% x55t / +0.480% x20t (2.7x live cost) | +0.758% x77t / +0.681% x22t (3.8x) |
| 20-day channel + close above 200-day average | +1.196% x47t / +0.354% x20t (2.0x) | +0.833% x72t / +0.776% x20t (4.3x) |
| 55-day channel + close above 100-day average | +0.901% x39t / +1.834% x11t (10.2x) | +0.466% x55t / +1.096% x14t (6.1x) |
| 55-day channel + close above 200-day average | +1.071% x35t / +1.524% x11t (8.5x) | +0.434% x53t / +1.124% x12t (6.2x) |

Note the 55-day rows: the 100-day-average filter changes nothing on GLD
(identical numbers to unchanged) because a 55-day breakout is almost always
already above its 100-day average. That is a useful fact in itself — the
slower channel already contains a trend filter implicitly, which is probably
why adding an explicit one helps it least.

---

## DECISION ON THE FAMILY

1. **Keep the breakout unchanged.** Neither missing practitioner condition
   earns its place: the trend filter helps where we chose and is a coin flip
   where we did not, and costs a third of the frequency; the minimum channel
   width is harmful on both instruments and drops every cell below the trade
   minimum.
2. **The entry is real, but less real recently.** 88th-97th percentile against
   luck on 13-15 year windows, 74th-78th on the modern window. The recent
   performance is partly the exit riding gold's rise.
3. **The 55-day channel is the better live candidate, not the 20-day.** It is
   the one that clears 5 times the live venue's cost (6.1x and 10.2x on the
   middle 20%), and the one that still beats luck at the 92nd percentile in
   the modern window. It fires 2.5-2.7 times a year, which is worse than 5.4.
4. **No sealed look was spent this round.** Round 48 already spent two on this
   family and this round changed nothing that would justify a third.
5. **Nothing here is a deployment proposal.** The frequency problem is not
   solved by this round and the live-venue cost correction makes it worse, not
   better.
