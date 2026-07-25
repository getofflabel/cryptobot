# Round 94 — The Quiet-Day Playbook

Run: `python3 step94_quiet_day.py` — full source in `step94_quiet_day.py`,
raw grid in `step94_table.csv`. Research only, no live orders, no live-file
edits, sealed test (final 20%) never touched.

## 0. The premise this round tested

We own one sealed-passed strategy (volume-gated Bollinger breakout) that
*by construction* cannot fire on a quiet day — its entry gate requires the
breakout bar's own volume to clear 1.2x its trailing 20-bar average. The
owner's point: quiet days (little news) are often the *easiest* to trade,
even if the dollars on offer per trade are smaller, and we have nothing
built for that regime. Pre-measured opportunity size on BTC daily bars:
quiet-tercile median range 2.25%, cost floor 0.044% round trip — over 50x
headroom. This round built three mean-reversion setups (the deliberate
mirror of our one loud-day winner) and tested whether any mechanical
version of "fade the quiet range" survives train, val, ETH transfer, and
real costs.

**Bottom line: nothing survived. 0/36 BTC cells net-SURVIVOR, and — more
telling than a bare zero — that is *below* the 5.6 survivors pure luck
would produce testing this many cells, not merely "no better than chance."
Section 6 explains why in plain terms: the mechanism is fighting a real,
if modest, directional continuation on the very days it's supposed to be
range-bound.** ETH transfer was not run (nothing to transfer). One cell is
a genuine FAILS-ON-COSTS case and is reported in full below.

## 1. The three families tested

| Setup | Mechanism |
|---|---|
| S1 fade-prior-range | Price touches/exceeds yesterday's high or low on a quiet day → fade back into the range. No volume condition. |
| S2 bb-midline-reversion | Price closes outside the SAME Bollinger(20, 2.5σ) band family C's breakout uses → fade back to the midline instead of riding the break. The literal mirror of our one sealed-passed strategy. |
| S3 failed-breakout-fade | Price wicks through a Bollinger edge but closes back inside on the same bar, AND that bar's volume is below its trailing 20-bar average (low volume = the poke wasn't real) → fade. Mirror image of family C's gate, which requires HIGH volume to let a breakout through. |

Two independent, causal "quiet" definitions (both bottom-tercile, both
decided using only fully-closed prior days — see `build_quiet_flags()` in
`step94_quiet_day.py` for the exact `.shift(1)` discipline):
- **quiet_A** — trailing 20-day volume, percentile-ranked against its own
  trailing 180-day distribution.
- **quiet_B** — trailing 20-day realized volatility (stdev of daily log
  returns), ranked the same way.

Sizing: every cell's stop_pct/target_pct is `STOP_FRAC`/`TARGET_FRAC` (swept
0.4/0.6 and 0.3/0.5/0.8 respectively) of a single TRAIN-only number —
the median day-range% across TRAIN-split quiet days under that cell's own
quiet definition (this project's standard "TRAIN-only median, held fixed,
hard-capped" approximation, applied to the regime's own measured range
instead of ATR). No fixed dollar/percent constants. Grid: 3 setups × 2
quiet-defs × 2 stop_fracs × 3 target_fracs = **36 BTC cells**.

## 2. Sanity check — our own quiet-day range vs the pre-measured figure

Resampling this project's own cached BTC 1h bars to daily (not the
Bitstamp source the pre-measurement used) and applying quiet_A over the
train+val calendar: **n=505 quiet days, median range 3.58%** (25th pct
2.26%, 75th pct 5.25%, 95.6% of quiet days range >1%). This is *larger*
than the 2.25% cited in the brief, not smaller — the opportunity is real
and if anything bigger than advertised by this measurement. The gap is
explained honestly, not glossed over: the brief's figure was a **global,
all-time tercile** split; this round's quiet flag is a **rolling,
180-day-relative** tercile (required for causality — a live system can
never know the all-time tercile boundary in real time). BTC's volatility
structurally decayed over the 6-year window (MARKET_PLAYBOOKS.md: hourly
ATR medians ~0.9%→~0.45%), so a rolling-relative "quiet" day drawn mostly
from later, calmer eras still carries a wider ABSOLUTE range than an
early-era loud day would have. Both readings are correct; they answer
slightly different questions, and this round's causal version is the one
that matters for a deployable rule. **This is not why the strategies
failed** — if anything a bigger range should have made harvesting EASIER,
which sharpens the finding in §6: the range is there, but the path inside
it doesn't cooperate.

## 3. Gross vs net, every cell — full table in `step94_table.csv`

Per-setup summary (pooled across the 12 cells each; full 36-row detail in
the CSV):

| Setup | cells | gross SURVIVORs | net SURVIVORs | best train gross exp | worst train gross exp | best train net exp | cost drag range (bps) | complementarity range | trades/yr |
|---|---|---|---|---|---|---|---|---|---|
| S1 fade-prior-range | 12 | 0 | 0 | $+0.18 | $−16.88 | $−4.75 | 4.90–5.69 | 0.311–0.330 | 43.8 |
| S2 bb-midline-reversion | 12 | 0 | 0 | $−2.24 | $−19.76 | $−8.10 | 4.79–6.21 | 0.100–0.135 | 35.5 |
| S3 failed-breakout-fade | 12 | 1 | 0 | $+1.49 | $−44.81 | $−3.55 | 4.76–6.11 | 0.314–0.354 | 10.1 |

**S1 and S2: FAIL, no gross edge to lose.** 23 of the 24 combined cells
are train-gross-NEGATIVE — costs (4.8–6.2bps round trip) are a rounding
error next to train losses of $5–50/trade. This is not a costs story on
these two setups; the mean-reversion mechanism itself has no edge here,
gross or net.

**S3: FAIL overall, but one genuine FAILS-ON-COSTS cell.** quiet_B,
stop_frac=0.6, target_frac=0.3 (stop_pct=2.18%, target_pct=1.09%,
range_pct_train=3.63%):

| split | n | gross exp/trade | net exp/trade | gross bps | net bps | drag |
|---|---|---|---|---|---|---|
| train | 53 | $+1.49 | $−3.55 | +1.43bps | −3.39bps | 4.82bps |
| val | 12 | $+84.15 | $+79.43 | +79.95bps | +75.45bps | 4.49bps |

Both train and val are gross-positive (gross_verdict = SURVIVOR), and this
is the round's one clean **break-even-bps** number: this cell's own gross
edge was 1.43bps on train — it needed to clear the ~4.8bps round-trip cost
before any of the val split's much larger (and, on n=12, much less
certain) edge would matter. It didn't. **This is the one cell in the
entire grid where costs, not the mechanism, are the reason it isn't
live**, and it should be read as thin regardless: val's $79/trade on 12
trades is "real direction, uncertain magnitude," the same caveat this
project has applied to every low-n val split before.

## 4. Complementarity — does this trade the OTHER two-thirds of the calendar?

Fraction of each setup's train+val trades whose entry day did NOT also see
R87's sealed volume-gated breakout (Bollinger 20/2.5 + vol≥1.2x) fire:

| Setup | quiet_A complementarity | quiet_B complementarity |
|---|---|---|
| S1 fade-prior-range | 0.311 | 0.330 |
| S2 bb-midline-reversion | 0.100 | 0.135 |
| S3 failed-breakout-fade | 0.314 | 0.354 |

**Lower than expected, and worth stating plainly: only 10–35% of these
setups' trade-days are free of the breakout strategy also firing that
day.** The reason is itself informative — the breakout's volume gate
compares an hourly bar's volume to its own trailing 20-HOUR average, while
"quiet" here is a whole-day, 180-day-relative classification. A day can be
quiet in aggregate and still contain a single news-driven hourly volume
spike that clears the local 20-bar bar, so the two strategies' calendars
overlap far more than a naive "quiet days = no breakouts" intuition would
suggest. Since nothing here survived, complementarity is informational
only — reported per the brief's instruction, not as a reason to ship
anything.

## 5. Cells run vs expected by chance

One representative cell per setup (quiet_A, stop_frac=0.4, target_frac=0.5)
replayed with the identical trade count/stop%/target%/max-hold/cost engine
at 30 RANDOMLY-TIMED quiet-day entries (same technique as R93's
`random_control_rate`):

| Setup | rep. n_events | rep. stop% | rep. target% | empirical survivor rate | cells this setup | expected by chance |
|---|---|---|---|---|---|---|
| S1-fade-prior-range | 222 | 1.403 | 1.754 | 0.167 | 12 | 2.0 |
| S2-bb-midline-reversion | 180 | 1.403 | 1.754 | 0.200 | 12 | 2.4 |
| S3-failed-breakout-fade | 51 | 1.403 | 1.754 | 0.100 | 12 | 1.2 |

**Total: 36 cells run, 5.6 SURVIVORs expected by pure luck, 0 net
SURVIVORs actually found (1 gross SURVIVOR, also below the 5.6 chance
baseline).** This empirical baseline is itself notably high (the standing
rule from R83/R90/R93 exists precisely because 2 winners out of 36 cells
once shipped live against ~0.7 expected by chance) — under this specific
engine/floor combination, random quiet-day timing clears the SURVIVOR bar
10–20% of the time on its own, meaning a small handful of positive cells
here would have been *unremarkable*. Getting **zero**, on a grid where
5.6 were expected, is itself a signal in the negative direction, not
merely "no signal."

## 6. Why the range is not harvestable this way — the actual finding

The range is real (§2 confirms it, even larger than pre-measured). The
mechanism tested — fade the extremes back toward the middle — is not what
converts that range into money. Two concrete, measured reasons:

1. **Win rates sit below the breakeven line these R:Rs require, and it's
   not close.** Representative cell (S1, quiet_A, stop 1.403%/target
   1.754%, R:R≈0.80): win rate 41.0% against an implied breakeven of
   ~44.4% at that R:R. Losses aren't fat-tailed outliers dragging an
   otherwise-good hit rate down — avg win ($150) and avg loss (−$133) are
   the same order of magnitude the stop/target geometry implies. The
   setup just doesn't reverse often enough.
2. **Fades fight a real, if modest, directional continuation — and quiet
   days specifically don't remove it.** Same S1 cell: long trades (fading
   BELOW yesterday's low, i.e. buying the dip) expectancy −$32.40/trade,
   short trades (fading ABOVE yesterday's high) expectancy −$1.38/trade —
   a stark asymmetry. quiet_A days pooled show a slightly NEGATIVE mean
   daily return (−0.06%) versus the full sample's +0.14%, and skew hard
   toward 2025 (228 of 754 quiet_A days, nearly a third, are from a single
   recent low-vol year). **This lines up exactly with MARKET_PLAYBOOKS.md's
   own R54 finding: low-vol "grind" regimes are where the 4h trend system
   with a strict volatility gate earns its keep — because grinds are
   still trends, just quiet ones, and fading them is betting against the
   thing that actually works there.** The mirror-image logic that made
   sense on paper (family C rides breakouts on loud days; fade them on
   quiet days) runs into the fact that "quiet" and "range-bound chop" are
   not the same thing — a day can have low relative volume/volatility and
   still be a slow, grinding trend day, which is precisely what this
   round's fades kept losing money to.

Real transaction costs (4.8–6.2bps) are a genuine but MINOR contributor —
only 1 of 36 cells had a gross edge large enough for costs to be the
deciding factor (§3). The honest verdict is that the mechanism itself,
not the cost structure, is what's missing. **The quiet-day opportunity is
real; "fade the extremes" is not the way to take it. The natural next
step — not tested here, to keep this round's grid honest to its own
brief — is a quiet-day CONTINUATION shape (small pullback entries inside
the day's own drift, sized off the same regime range), which is the
direction R54's grind-trend finding actually points.**

## 7. Verdict summary

| Family | Verdict | Note |
|---|---|---|
| S1 fade-prior-range | **FAIL** | No gross edge on any of 12 cells; directional bias (long fades far worse than short fades) is the measured cause. |
| S2 bb-midline-reversion | **FAIL** | No gross edge on any of 12 cells — the mirror of our one sealed winner does not mirror its success. |
| S3 failed-breakout-fade | **FAIL** (1 cell FAILS-ON-COSTS) | 11/12 cells gross-negative; quiet_B/stop0.6/target0.3 was gross-positive both splits (train +1.43bps, val +79.95bps) but a 4.8bps cost drag flipped train net-negative — see §3 for the exact bps gap. Val's edge is thin (n=12) regardless. |

**ETH transfer: not run — zero BTC net survivors, nothing queued.**
Per standing discipline, ETH transfer is only mandatory on what clears
BTC train+val+floors; nothing here did.

**Trades/year (for reference, all FAILED):** S1 ≈ 43.8/yr, S2 ≈ 35.5/yr,
S3 ≈ 10.1/yr (train+val pooled, BTC 1h). None of these numbers matter
operationally since nothing survived, but they're reported per the
brief's standing requirement.

## 8. What this round adds to the project's knowledge

This is a genuinely valuable negative result, not a shrug. It closes off
the most obvious mechanical answer to a real, correctly-identified gap
(we had nothing for quiet days) and — more usefully — it POINTS at the
right answer instead of leaving a blank: MARKET_PLAYBOOKS.md already has
the strategy that works in low-vol regimes (the 4h trend system with a
strict vol gate, R54 sealed), and this round's own diagnostic (quiet days
skew slightly trend-continuation, not mean-reverting) explains WHY that
strategy works and this round's mirror-image bet doesn't. The owner's
instinct that quiet days are tradeable was correct; the specific
mechanism guessed here (fade the range) was not the right one, and now
that's known rather than assumed.
