# ROUND 92 — FADE THE AGED BREAKDOWN? VERDICT: **DRIFT.**

R90 found that shorting the break of an aged, well-tested level gets
monotonically worse the older the level is. The obvious hypothesis was
that the FADE is the trade — buy those breakdowns. This round tested it
with three mandatory controls, because BTC rose over most of the sample
and in a rising market every long looks like genius.

Code: `step92_fade_breakdown.py` (imports R90's event scanner, level-age
and touch-count machinery). Raw: `step92_table.csv`, 213 rows.

## THE PRIMARY RESULT LOOKS GREAT, WHICH IS WHY THE CONTROLS EXIST

Buying the breakdown of an aged structural level, BTC 1h, age>=500 bars,
touches>=1:

| split | n | expectancy | win rate | vs random |
|---|---|---|---|---|
| train | 47 | **+$86.96** | 55.3% | 93rd pctile |
| val | 21 | **+$147.71** | 76.2% | 98th pctile |

On its own that is a strategy. It is also wrong, and here is why.

## CONTROL 2 — THE MIRROR. THIS IS WHAT DECIDES IT. IT FAILS.

If aged levels genuinely mean-revert, the effect must be symmetric: aged
RESISTANCE broken to the UPSIDE should be a good short, exactly mirroring
aged support broken down being a good long.

**It is negative in all 30 mirror cells, on both timeframes, with no
exceptions:**

| tf | age cutoff | n | expectancy | vs random |
|---|---|---|---|---|
| 1h | 20 | 423 | -$20.12 | 33rd |
| 1h | 50 | 259 | -$29.35 | 17th |
| 1h | 100 | 175 | -$34.52 | 17th |
| 1h | 200 | 116 | -$43.11 | 14.5th |
| 1h | 500 | 62 | -$54.73 | 14th |
| 4h | 20 | 108 | -$74.87 | 33.5th |
| 4h | 100 | 36 | -$134.93 | 22.5th |
| 4h | 200 | 22 | -$206.29 | 14.5th |

Not merely unprofitable — **below chance**, most cells sitting at the
14th-33rd percentile of a random-entry control. And it gets monotonically
worse with age, exactly like the short side did in R90.

So the pattern is not "aged levels snap back." It is **"long works,
short does not,"** which is what an uptrending sample produces.

## THE ETH TRANSFER ALSO FAILS

Config carried over unchanged, no re-tuning:

| tf | split | n | expectancy | vs random |
|---|---|---|---|---|
| 1h | train | 45 | +$298.28 | 100th |
| 1h | **val** | 22 | **-$23.57** | 43rd |
| 4h | train | 64 | +$53.12 | 60.5th |
| 4h | **val** | 27 | **-$91.31** | 34th |

A 100th-percentile train result collapsing to negative val is the
signature of fitting, not of an edge.

## CONTROL 3 — REGIME SPLIT, the one point in its favour

| regime | tf | n | expectancy |
|---|---|---|---|
| BULL (close > 50d SMA) | 1h | 5 | +$379.64 (sample useless) |
| BEAR (close <= 50d SMA) | 1h | 63 | **+$104.11** |
| BULL | 4h | 31 | +$258.29 |
| BEAR | 4h | 68 | +$17.37 |

Buying breakdowns stayed positive in the BEAR regime on adequate sample
(n=63), which is genuine evidence against the pure-drift reading and is
recorded here rather than buried. But it is one control out of three, and
it cannot rescue a result whose mirror is below chance everywhere and
whose second asset fails validation.

## MULTIPLE COMPARISONS

60 fade cells swept. At the 90th percentile, ~6 are expected to clear by
chance. The best cell sits at the 93rd. **The headline result is inside
what luck produces**, before the mirror and transfer failures are even
considered.

## VERDICT: DRIFT

Fails the mirror (decisively, below chance in all 30 cells), fails the
ETH transfer (val negative on both timeframes), and its best cell is
within chance for the number of cells run. It passes only the random
baseline on BTC and partially the regime split.

**No deployment. No change to any live file.**

## THE FINDING THAT IS ACTUALLY WORTH KEEPING

Three independent studies tonight now say the same thing:

- **R84** (blind chart drills): my shorts went 1 win, 11 losses, -0.544R,
  while longs were +0.255R.
- **R90** (25,481 mechanical break events): structural shorts get
  monotonically worse the more significant the level, -$9 to -$89.
- **R92** (this round, 30 mirror cells): shorting aged upside breakouts is
  negative everywhere and below a random-entry control.

**Shorting BTC structurally does not work in this data.** Whether that is
a permanent property of the asset or an artifact of a 2020-2026 sample
that trended up, we cannot tell from here — and that distinction matters
enormously before it becomes a standing rule. What it justifies TODAY is
narrow and practical: stop spending research rounds hunting BTC short
setups, and treat any future short candidate as guilty until it clears a
bear-regime-only test.
