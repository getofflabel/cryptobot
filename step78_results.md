# Round 78 — An Oil Playbook From Zero

Research only. No commits, no live orders. Produced by `step78_oil_playbook.py`
(script + full docstring), this file, and `step78_full_table.csv` (all 290
configs, nothing omitted). Data cached as `data_oil_{CL,BZ,USO}_{1d,1h}.parquet`.

## 0. Why this round existed

Going in, we had **zero strategies validated on oil itself**. The two tools
running on oil in the live paper engine (per `step70_replay.py`'s own
`[transfer-assumption]` tag) are:

- **donchian(20) + a gold-validated structure-trailing exit** — proven on
  GOLD (`gold_book.py`, R59), never independently tested on oil.
- **RSI2 dip-buy** — proven on the S&P (R60's `rsi2_dipbuy_sealed`), never
  independently tested on oil.

R70's own replay explicitly refused to certify either on oil for exactly
this reason. This round builds six families around oil's *actual* character
(inventory cycle, spike-and-reversion, session structure, the Brent-WTI
spread) from zero, gauntlets all of them honestly, and answers the overdue
question directly at the end.

## 1. Data — honest spans

| dataset | bars | span | note |
|---|---|---|---|
| CL=F (WTI) 1d | 6,507 | 2000-08-23 → 2026-07-24 | 26 years, yfinance `max` |
| CL=F 1h | 13,527 | 2024-03-01 → 2026-07-24 | ~2.4 years — yfinance's hard 730d cap on hourly bars |
| BZ=F (Brent) 1d | 4,725 | 2007-07-30 → 2026-07-24 | 19 years |
| BZ=F 1h | 13,559 | 2024-03-01 → 2026-07-24 | ~2.4 years, same cap |
| USO (ETF) 1d | 5,104 | 2006-04-10 → 2026-07-24 | 20 years |

Sub-hourly (15m/5m) was **not** fetched — yfinance caps intraday-below-1h
history at ~60 calendar days, too shallow to clear this round's 30-train/
8-val floors on anything but the noisiest triggers. Stated honestly rather
than faked. USO gets no 1h pull (no claimed 1h edge for the ETF instrument).

Gauntlet: chronological 60/20/20 per dataset, floors 30 train / 8 val trades,
select by train+val expectancy both positive, **sealed 20% test window never
sliced or scored anywhere in the script**. Costs: futures (CL/BZ) 2bps round
trip, ETF (USO) 4bps round trip (`step48_tradfi_trend.py`'s established
TradFi convention), funding=0 (no perpetual-funding analogue on dated
futures/ETFs). Every row also carries `tr_per_yr`; **under 10 trades/year is
flagged TOO-RARE regardless of expectancy** — a real finding, not a passing
grade, since a strategy that fires 2-4x/year cannot be sanity-checked by a
human trader inside a normal career, let alone run as a "playbook."

## 2. Verdict counts

290 configs total. 37 SURVIVOR / 73 INSUFFICIENT-SAMPLE / 180 FAIL.
168 clear the 10 trades/year cadence bar, 122 don't.

| family | FAIL | INSUFFICIENT | SURVIVOR |
|---|---|---|---|
| 1-trend (donchian+structure-trail) | 29 | 24 | 7 |
| 2-meanrev (z-score/RSI2 spike-fade) | 78 | 49 | 13 |
| 3a-dow (day-of-week) | 15 | 0 | 5 |
| 3b-release-hour (EIA/API) | 19 | 0 | 5 |
| 4a-structure-retest (BOS+retest+engulf) | 24 | 0 | 6 |
| 4b-sweep-reclaim (prior-day extremes) | 12 | 0 | **0** |
| 5-spread-reversion (Brent-WTI) | 3 | 0 | 1 |

By symbol: **CL 84F/20I/23S, BZ 79F/30I/14S, USO 17F/23I/0S — USO (the
instrument a retail account can actually hold) has zero survivors anywhere
in this entire round.**

## 3. Family-by-family findings

### Family 1 — TREND (donchian 20/55 + real structure-trailing exit, both directions)

The exit is a genuine ratcheting confirmed-swing floor/ceiling (k=5) — the
literal shape `gold_book.py` validated on gold — reimplemented to run
through the standard signal engine instead of gold_book's own trade-list
bookkeeping, so it gets real costs and next-bar-open fills like everything
else this round.

- **Long side works, short side doesn't.** On DAILY bars, donchian20/55
  long clears both windows on CL and BZ (train exp $28-$335, val exp
  $80-$540) — but **every mirrored short config on daily CL/BZ either
  FAILS outright or lands in single-digit-trade INSUFFICIENT-SAMPLE with
  noisy, inconsistent sign.** Oil's structural trend edge, at least in this
  shape, is long-biased despite oil having real bear markets on paper.
- **1h kills it completely.** All 24 hourly donchian+structure-trail
  configs (CL and BZ, both directions, all three vol gates) FAIL. This
  shape needs daily bars to breathe; forcing it onto 1h destroys it.
- **Cadence is the real problem.** Every single daily SURVIVOR fires
  2.1-3.6 trades/year — TOO-RARE by the round's own 10/yr bar. This is
  the headline finding for family 1: **the gold-shape donchian is
  directionally real on oil daily data, but too rare to be a playbook
  piece on its own.**
- Vol-regime gate (family 6, folded in here): low-vol and ungated
  outperform high-vol on the daily long side — donchian breakouts on oil
  do *not* need a live tape to fire (unlike the "oil trends hard when
  supply is threatened" framing might suggest); if anything a quiet
  regime is slightly cleaner.

### Family 2 — MEAN REVERSION AFTER SPIKES (z-score/RSI2, both directions, trend+vol gated)

This is the round's cleanest, most transferable finding.

- **RSI2 SHORT (fade the pop, RSI2>95) is the standout signal**, and it
  clears the 10/yr cadence bar in FOUR separate configs: `rsi2>5 short
  trend=none vol=none` on **CL 1h** (264 train / 86 val, 181 tr/yr, val
  exp $14.40), `rsi2>5 short trend=none vol=high-vol` on **CL 1h** (138/43,
  94 tr/yr, val exp $20.33) and on **BZ 1h** (141/31, 89 tr/yr, val exp
  $39.03), and `rsi2>5 long trend=none vol=high-vol` on CL 1h (155/43,
  103 tr/yr, val exp $14.58).
- **This is the direct opposite of the strategy we currently run.** The
  live "index dip-buy shape" is RSI2 **long** (buy the dip). Tested head
  to head on oil's own data (see section 5), the long side loses on every
  single dataset while the short side (fade the spike UP, not buy the
  spike DOWN) survives repeatedly and transfers CL↔BZ. Oil's post-spike
  reversion, as the task's own framing predicted, is real — but the
  *direction* the currently-running strategy assumes is backwards for the
  short-vol side of the trade.
- Vol-gate result: **high-vol gate is where the real edge concentrates**
  (5 of 8 vol=high-vol/trend=none configs are FAIL but the survivors
  cluster there disproportionately vs vol=low-vol, which produced ZERO
  survivors across 20 configs). Mean reversion on oil wants a live tape,
  the opposite of family 1's trend result — a genuine, useful split.
- with-trend gating mostly starves the sample (16 of 24 with-trend/high-
  or-low-vol combos land INSUFFICIENT-SAMPLE) rather than improving it.
  counter-trend gating is a clean sweep of 20/20 FAIL — worth ruling out
  explicitly, not just skipping.

### Family 3a — day-of-week (next-session drift, daily)

- 5 SURVIVOR configs, but **no cross-symbol agreement**: CL's survivors are
  short-after-Friday, short-after-Monday, long-after-Wednesday; BZ's are
  long-after-Tuesday, long-after-Thursday. WTI and Brent do not agree on
  which weekday pays or which direction. That is the twin-check FAILING —
  treat day-of-week seasonality as noise dressed up as a pattern, not a
  playbook piece, despite technically clearing both floors (n≈550-800
  train trades — the floor was never the problem; consistency was).
- Also worth naming: this "signal" is in a position essentially every
  week (49-52 trades/year is just "52 weeks/year minus gaps"), so a
  SURVIVOR verdict here is a much weaker claim than the same verdict on a
  sparser, more selective family.

### Family 3b — EIA-Wednesday / API-Tuesday release-hour reaction, 1h

**The clearest single answer this round produced.** Every one of the 12
CONTINUATION configs (both reports, both symbols, all three hold windows)
**FAILED**. Every SURVIVOR in this family is a REVERSAL config:
EIA-Wed reversal hold4h on BZ (val exp $17.20) and CL (val exp $6.85),
EIA-Wed reversal hold2h on BZ (val exp $9.95), API-Tue reversal hold1h and
hold4h on BZ (val exp $7.42 / $2.42).

**Direct answer to the task's question: no, the first hour after the EIA/
API release does NOT continue like our validated crypto news edge — it
tends to FADE.** Oil's report-hour reaction is a spike to fade, not a move
to ride. This is the opposite mechanism from the crypto news edge and
should not be built as if it were the same shape. Best cluster is on BZ,
not CL (worth flagging: the twin check here favors Brent, not WTI).

### Family 4 — STRUCTURE, 1h (step56/step73 toolkit reused verbatim)

- **4a (break-of-structure + retest + engulf, plus the no-engulf and
  breakout ablations)**: 6 SURVIVORs, but **every one is on CL — zero
  survive on BZ** (24 BZ configs, all FAIL). The best cluster is the
  breakout-no-retest ablation (mode=both, stop≈1.05%): all 3 R-multiples
  SURVIVOR on CL with 98 train / 34 val trades (68/yr, val exp
  $10.66-$25.84) — a real, fast-cadence structural edge, but it **fails
  the Brent twin check outright**, meaning this reads more like a CL-
  specific quirk of this 2.4-year window than a durable oil-structure
  edge. The literal full-stack config (retest AND engulf both required)
  produced only 2 thin SURVIVORs, echoing round 74's own finding on FX
  that the "retest AND engulf together" combination is a choke point.
- **4b (sweep-and-reclaim of the prior calendar day's high/low)**:
  **0 of 12 configs survived — a clean, total negative result.** Every
  config FAILED on both CL and BZ, both hold windows, all three R-
  multiples. The toolkit that produced our best crypto edge does not
  transfer to oil's session structure in this shape. Worth stating
  plainly rather than burying: this was the family with the strongest a
  priori case ("oil has real session structure, unlike 24/7 crypto") and
  it is the family's flattest failure.

### Family 5 — the Brent-WTI spread

- Spread sits at -8.04% today (WTI cheaper than Brent), vs a train-period
  median of -5.84% — currently in an unusually wide (negative) regime,
  consistent with the round brief's "90th percentile stress" framing.
- **Spread-reversion as an outright single-leg CL bet**: only 1 of 4
  configs SURVIVOR (extreme≥80/≤20, 10-day hold: 168 train/71 val, val
  exp $26.50, 15.7 tr/yr — clears cadence). The tighter/longer variants
  are not just FAIL but catastrophically negative in validation (extreme
  ≥90/≤10 hold20d: val exp **-$650**) — this family is fragile, sign-
  flips hard under small parameter changes, and is explicitly a stated
  approximation (single-leg CL directional bet standing in for a true
  dollar-neutral pairs trade the engine can't express). Treat the one
  survivor as a lead worth a real pairs-trade build, not a playbook piece
  as-is.
- **Regime breakdown** (family 1's CL-daily donchian20-long and family
  2's CL-daily RSI2-long, trades tagged by spread-percentile regime at
  entry, TRAIN+VAL only): donchian trend trades taken while the spread
  sits in a NORMAL regime average **+$404/trade**, but while the spread
  is EXTREME (≥80th/≤20th pctile) average **-$19/trade** (n=20 vs n=27).
  RSI2 dip-buys are negative in both regimes but worse when extreme
  (-$134 vs -$83). **The spread-extreme regime is a headwind for both
  currently-borrowed shapes, not a tailwind** — a useful filter candidate
  even though the trend-following config itself is too rare to be a
  playbook piece (see family 1).

## 4. Ranked survivors (playbook-viable: SURVIVOR + clears 10 tr/yr)

27 of the 37 SURVIVORs clear cadence. Top by validation expectancy:

| rank | family | config | symbol/tf | tr_n/va_n | va_exp | tr/yr | Brent twin |
|---|---|---|---|---|---|---|---|
| 1 | 3a-dow | next-session-after-Friday **short** | CL 1d | 774/260 | $67.29 | 49.9 | FAILS (no BZ agreement) |
| 2 | 2-meanrev | rsi2>5 **short** trend=none vol=high-vol | BZ 1h | 141/31 | $39.03 | 89.2 | **PASSES** (also CL 1h) |
| 3 | 5-spread-reversion | extreme≥80/≤20 hold10d (CL, single-leg approx) | CL 1d | 168/71 | $26.50 | 15.7 | N/A (spread-defined) |
| 4 | 4a-structure | breakout-no-retest R=4.0 | CL 1h | 98/34 | $25.84 | 68.4 | FAILS (0/24 on BZ) |
| 5 | 4a-structure | breakout-no-retest R=3.0 | CL 1h | 98/34 | $25.81 | 68.4 | FAILS (0/24 on BZ) |
| 6 | 2-meanrev | rsi2>5 **long** trend=with-trend vol=high-vol | CL 1h | 42/8 | $21.53 | 25.9 | not tested on BZ (rep. point) |
| 7 | 2-meanrev | rsi2>5 **short** trend=none vol=high-vol | CL 1h | 138/43 | $20.33 | 93.8 | **PASSES** (also BZ 1h) |
| 8 | 3b-release | EIA-Wed **reversal** hold4h | BZ 1h | 70/25 | $17.20 | 49.3 | **PASSES** (also CL 1h, smaller) |
| 9 | 4a-structure | BOS+retest+engulf continuation R=2.0 | CL 1h | 56/18 | $14.71 | 38.3 | FAILS (0/24 on BZ) |
| 10 | 2-meanrev | rsi2>5 **long** trend=none vol=high-vol | CL 1h | 155/43 | $14.58 | 102.6 | not clean on BZ |

**Only two shapes genuinely pass the Brent-WTI twin check with matching
direction and comparable numbers on both symbols: RSI2-short-fade
(family 2, rows 2/7) and EIA-Wednesday-reversal (family 3b, row 8).**
Everything CL-only in this list (family 4a's structure survivors, the
day-of-week survivor) should be read as "real on this window, unconfirmed
as a durable oil edge" until it either survives a look at the sealed test
or shows up on Brent too.

## 5. What an oil trading week looks like (descriptive, from the same data)

- **Monday** carries the fattest tail by far (daily open-close std 9.26%
  on CL vs 2.2-2.5% every other weekday) — driven in large part by the
  April 20, 2020 negative-price event, which landed on a Monday. Real,
  not a data bug, but a single outlier inflates that number; don't read
  "Monday is wild" as a stable weekly fact.
- **Tuesday afternoon → Wednesday** is the inventory corridor: the API
  estimate lands ~4:30pm ET Tuesday, the official EIA number ~10:30am ET
  Wednesday. Intraday volatility (avg |1h return| on CL) peaks at the
  9-11am ET window (0.52-0.58%, roughly double the overnight-hours
  average of 0.15-0.25%) — the EIA release sits right inside oil's
  already-most-active hour, not a separate spike on top of a quiet base.
- **The release itself is a fade, not a trend continuation** (family 3b,
  section above) — the tradeable behavior around 10:30am ET Wednesday is
  "let the initial print happen, then take the other side," not "jump on
  the print."
- **Thursday/Friday are the calmest, most positively-drifting sessions**
  in the raw descriptive stats (smallest std, only positive mean
  open-close return of the five weekdays on both CL and BZ) — consistent
  with the inventory-driven uncertainty of Tue/Wed unwinding into the
  week's back half, though family 3a's own gauntlet found this doesn't
  cleanly convert into a tradeable, twin-confirmed edge.
- **Brent tracks WTI closely but with roughly half the daily-return
  volatility** in the weekday breakdown (std 2.0-2.2% vs CL's 2.2-9.3%) —
  Brent is the steadier of the two on a raw-return basis, separate from
  which one's *strategies* transfer better.

## 6. The overdue verdict — do the currently-running strategies hold up?

Tested literally, head to head, on oil's own data (see `step78_full_table.csv`,
rows tagged in the script's own explicit "current strategy" filter):

| strategy (as currently run on oil) | CL 1d | CL 1h | BZ 1d | BZ 1h | USO 1d |
|---|---|---|---|---|---|
| donchian20+structure-trail **long**, ungated (gold's shape) | SURVIVOR¹ | FAIL | SURVIVOR¹ | FAIL | FAIL |
| RSI2 dip-buy **long**, no gates (the index's shape) | FAIL | FAIL | FAIL | FAIL | FAIL |

¹ SURVIVOR but **TOO-RARE** (3.4/yr on CL, 3.4/yr on BZ) — clears the
expectancy bar, fails the cadence bar.

**Verdict: NEITHER strategy holds up as currently run.**

- The **gold donchian shape** is directionally real on oil's own DAILY
  data (positive train AND val expectancy, transfers CL↔BZ) but fires
  roughly once per quarter — too rare to be the thing generating the bulk
  of trade volume in a live paper engine that presumably expects more
  frequent signals. On the 1h timeframe it currently ALSO runs on, it is
  an outright loser on both CL and BZ. **If this shape stays in the
  live book at all, it should be daily-only, long-only, and reported by
  its true annual cadence — not run on 1h.**
- The **RSI2 dip-buy (long) shape** fails everywhere it was tested on
  oil — all five datasets, both timeframes. There is no honest reading of
  this round's results that keeps it running as-is. The mirror-image
  short (fade the pop) is the one that actually works and transfers — see
  family 2 above. **This is the clearest actionable fix from the round:
  the dip-buy direction on oil should be flipped, not kept.**

## 7. Biggest caveat

Every number above is TRAIN+VAL only; the sealed 20% test window (2019-05
→ 2026-07 territory on CL daily, later still on 1h) has never been sliced
or scored by this script, on purpose, per the round's own discipline —
these are candidates for the lead to spend real looks against, not a
finished, test-confirmed playbook. Second caveat, stated throughout above
but worth repeating once at the end: most of family 4a's CL survivors and
all of family 3a's day-of-week survivors **fail the Brent twin check** —
treat those as "real on this specific CL 2.4-year/26-year window,"
not yet as "a durable oil-structure fact," until Brent (or the sealed
test) confirms them.
