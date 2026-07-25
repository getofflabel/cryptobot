# Round 111 — EIA / API Inventory Reaction Test

**Finding: the EIA release-hour reaction is REAL, decays over the trading
day, and is a CONTINUATION (not a fade) — but this is a descriptive
diagnostic, not a costed strategy verdict. The unofficial Tuesday API
estimate shows NO detectable reaction.**

## Method

`step111_eia_reaction.py`. Event calendar built from
`pandas.tseries.holiday.USFederalHolidayCalendar` (documented
approximation — no scraped official EIA calendar was available): EIA
official report Wednesday 10:30am ET, shifted to Thursday on weeks where
Monday or Wednesday is a federal holiday (15/125 weeks shifted in this
data span); API estimate Tuesday 4:30pm ET, shifted to Wednesday under
the same condition (13/125 weeks). ET->UTC uses real DST-aware
`zoneinfo`, not the fixed-offset approximation `tradfi_engine.py` uses
elsewhere. Data: `data_oil_CL_1h.parquet` (CL=F, 2024-03-01 → 2026-07-24,
125 weekly events of each type in span).

Reused UNCHANGED from `step45b_news_events.py` (the desk's own BTC news-
reaction methodology): `align_events` (no-lookahead — floors to the last
bar whose OPEN is <= the event time, trades at the NEXT bar's open) and
`event_study` (mean/median |move| at each horizon vs the UNCONDITIONAL
same-window baseline — this ratio-vs-baseline is itself a chance
baseline). On top of that, per the brief's explicit ask, an EXPLICIT
second **randomized-timing control**: the same count of random UTC
timestamps, drawn from the same span, each kept >=4h clear of any real
EIA/API event, run through the identical machinery.

## EIA — magnitude, decay, chance baseline

| horizon | real mean\|move\| | baseline (same window) | ratio vs baseline | random-timing control mean\|move\| |
|---|---|---|---|---|
| 1h  | **0.570%** | 0.325% | **1.75x** | 0.263% |
| 2h  | 0.725% | 0.477% | 1.52x | 0.341% |
| 4h  | 0.933% | 0.693% | 1.35x | 0.537% |
| 24h | 2.011% | 1.875% | 1.07x | 1.806% |

n=125 events at every horizon (>= the 30/8 floor by a wide margin — this
is a descriptive diagnostic over the full available span, not a
train/val/test-split strategy gauntlet, so those floors are shown for
context, not as a pass/fail gate here).

The real EIA reaction bar (1h) averages **0.570%**, more than double the
matched random-timing control's **0.263%**, and 1.75x the same-window
unconditional baseline. **The effect decays smoothly toward baseline as
the horizon widens** — 1.75x → 1.52x → 1.35x → 1.07x — i.e. essentially
all of it is concentrated in the release hour and the few hours after;
by 24h it is statistically indistinguishable from an ordinary day. That
decay shape is exactly what a real, tradeable, short-horizon information
event should look like.

## Direction: continuation, not fade

Conditioning the next-4h return on the SIGN of the release-hour reaction
bar itself (n=125, 66 positive / 58 negative reaction bars):

- After a **positive** reaction bar: next 4h averages **+0.255%**
- After a **negative** reaction bar: next 4h averages **-0.099%**
- Unconditional next-4h average: +0.081%
- corr(reaction bar return, next-4h return) = **+0.298**

Shape: **CONTINUATION** — the initial post-release move tends to keep
going in the same direction over the next several hours, not reverse.

**This appears to conflict with round 78's finding** (RESEARCH_LOG.md,
"EIA-Wednesday REVERSAL (the release-hour reaction is a fade, not a
continuation: all 12 continuation configs failed)"). Two things are
different, not one: (1) round 78 tested a COSTED STRATEGY (stops,
targets, taker fees, sealed-tested — and it already burned 2 of its
sealed looks on exactly this topic, "erosion ~+29"), while this round is
a raw price-reaction diagnostic with no stops/costs attached; a real
directional tendency in price does not automatically survive stop
placement and cost once you build a strategy around it. (2) the exact
event-timestamp source differs (round 78's own calendar vs this round's
holiday-rule reconstruction) — worth reconciling before either number is
trusted over the other. **Flagging the conflict rather than picking a
winner** is the honest move here; it is also why this round does NOT
attempt to build and sealed-test a strategy off today's continuation
finding — that sealed-test budget on this exact topic (EIA release-hour
reaction) has already been spent twice by round 78, and a third look
without reconciling the two studies first would be spending it blind.

## API (Tuesday estimate): no detectable reaction

| horizon | real mean\|move\| | baseline | ratio vs baseline | random-timing control |
|---|---|---|---|---|
| 1h  | 0.258% | 0.325% | 0.79x | 0.263% |
| 2h  | 0.328% | 0.477% | 0.69x | 0.341% |
| 4h  | 0.524% | 0.693% | 0.76x | 0.537% |
| 24h | 1.809% | 1.875% | 0.96x | 1.806% |

Every horizon sits BELOW its own baseline and is statistically
indistinguishable from the random-timing control at every horizon. The
unofficial Tuesday-evening API estimate shows **no systematic price
reaction on CL=F** in this data — a clean negative result, consistent
with it being an unofficial, lower-confidence number that the market
does not treat as new information the way it treats Wednesday's official
release. Direction test on API also shows no clear sign pattern
(corr +0.239 but positive-reaction and negative-reaction next-4h returns
are both negative, -0.063% and -0.215% — no continuation, no fade,
just noise).

## What this does and doesn't establish

**Does establish:** a real, decaying, continuation-shaped volatility and
directional signature around the OFFICIAL EIA release hour on CL=F, and
the absence of one around the unofficial API estimate. Both are useful,
oil-specific, previously-untested findings — exactly the "highest-value
untested idea" flagged going into this round.

**Does not establish:** a tradeable strategy. No stops, no costs, no
train/val/sealed split were run here (this is `step45b`'s descriptive
event-study shape, not `step41_shorts`'s strategy gauntlet). Building and
sealed-testing an EIA-continuation strategy is queued into the family map
(`step110_family_map.md`) as its own family, with the round-78 conflict
noted as something to resolve first rather than paper over.

Full per-horizon table: `step111_table.csv`.
