# Round 41 — cracking BTC shorts, four native families

Script: `step41_shorts.py`. 64 configs tested, chronological 60/20/20 split per
timeframe (train through 2024-01-10, val through 2025-04-16, **test sealed and
never touched by this script**). All numbers are AFTER FULL COSTS (CostModel
defaults: 6bps taker / 2bps maker, 1bp half-spread, 2bp slippage, real signed
funding wired via `align_funding` — shorts collect positive funding, exactly
as in `backtest.py`). Expectancy is $/trade on a $10k account. Execution is
maker throughout (matches the rest of this repo's short-family work).

Survivor bar (per the Gauntlet protocol): positive expectancy on BOTH train
and val, **>=30 train trades AND >=8 val trades**. "INSUFFICIENT-SAMPLE" =
positive on both windows but under the trade-count floor (a real finding, not
a fail of the edge itself — usually a rare-event strategy).

## Full results table

| family | config | tf | tr_n | tr_exp | tr_win% | tr_ret% | tr_dd% | va_n | va_exp | va_win% | va_ret% | va_dd% | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1-bleed-simple | dd>2% | 1h | 806 | -5.86 | 22.83 | -47.23 | -54.97 | 270 | -7.78 | 28.15 | -20.99 | -44.59 | FAIL |
| 1-bleed-simple | dd>3% | 1h | 591 | -9.20 | 23.69 | -54.35 | -61.87 | 200 | -16.66 | 27.00 | -33.33 | -46.48 | FAIL |
| 1-bleed-simple | dd>5% | 1h | 314 | -11.90 | 24.52 | -37.37 | -55.30 | 84 | -32.95 | 30.95 | -27.68 | -34.01 | FAIL |
| 1-bleed-simple | dd>2% | 4h | 282 | -20.68 | 21.63 | -58.33 | -59.29 | 90 | -31.30 | 22.22 | -28.17 | -34.49 | FAIL |
| 1-bleed-simple | dd>3% | 4h | 251 | -22.92 | 20.72 | -57.54 | -59.94 | 86 | -35.14 | 20.93 | -30.22 | -34.64 | FAIL |
| 1-bleed-simple | dd>5% | 4h | 184 | -31.90 | 23.91 | -58.70 | -61.52 | 67 | -51.36 | 22.39 | -37.80 | -34.41 | FAIL |
| 1-bleed-structural | k=5 | 1h | 147 | **11.38** | 26.53 | 16.73 | -36.43 | 40 | **26.40** | 35.00 | 10.56 | -17.25 | **SURVIVOR** |
| 1-bleed-structural | k=8 | 1h | 95 | -42.34 | 15.79 | -40.22 | -40.45 | 35 | -7.00 | 34.29 | -2.45 | -15.19 | FAIL |
| 1-bleed-structural | k=12 | 1h | 66 | -47.26 | 18.18 | -31.19 | -35.66 | 29 | -19.31 | 27.59 | -5.60 | -21.94 | FAIL |
| 1-bleed-structural | k=8 | 4h | 22 | -24.92 | 27.27 | -5.48 | -21.76 | 7 | -152.97 | 14.29 | -10.71 | -18.47 | FAIL |
| 1-bleed-structural | k=5 | 4h | 39 | -113.24 | 17.95 | -44.16 | -51.38 | 15 | -160.74 | 20.00 | -24.11 | -28.73 | FAIL |
| 1-bleed-structural | k=12 | 4h | 20 | -171.93 | 10.00 | -34.39 | -36.57 | 6 | -88.90 | 33.33 | -5.33 | -14.76 | FAIL |
| 2-persistence | N6/M8 X4.0% | 1h | 94 | 31.60 | 34.04 | 29.70 | -22.31 | 27 | -51.16 | 29.63 | -13.81 | -24.61 | FAIL |
| 2-persistence | N8/M10 X4.0% | 1h | 69 | 25.95 | 31.88 | 17.91 | -28.64 | 18 | -131.09 | 11.11 | -23.60 | -26.83 | FAIL |
| 2-persistence | N6/M8 X1.5% | 1h | 271 | 1.97 | 33.21 | 5.33 | -31.02 | 97 | -0.64 | 38.14 | -0.62 | -27.18 | FAIL |
| 2-persistence | N8/M10 X1.5% | 1h | 146 | 1.07 | 32.19 | 1.56 | -24.35 | 67 | -34.14 | 31.34 | -22.87 | -33.83 | FAIL |
| 2-persistence | N8/M10 X2.5% | 1h | 113 | -10.17 | 30.09 | -11.50 | -30.45 | 44 | 28.77 | 38.64 | 12.66 | -17.88 | FAIL |
| 2-persistence | N4/M5 X1.5% | 1h | 331 | -14.01 | 32.93 | -46.38 | -54.36 | 106 | -12.11 | 35.85 | -12.84 | -26.47 | FAIL |
| 2-persistence | N6/M8 X2.5% | 1h | 192 | -17.49 | 27.60 | -33.58 | -44.82 | 64 | -16.04 | 31.25 | -27.71 | -10.27 | FAIL |
| 2-persistence | N4/M5 X2.5% | 1h | 208 | -21.93 | 28.85 | -45.62 | -52.52 | 60 | -12.45 | 36.67 | -7.47 | -22.50 | FAIL |
| 2-persistence | N4/M5 X4.0% | 1h | 100 | -36.88 | 27.00 | -36.88 | -43.72 | 27 | -129.89 | 14.81 | -35.07 | -37.09 | FAIL |
| 2-persistence | N4/M5 X2.5% | 4h | 156 | 4.02 | 44.87 | 6.27 | -45.42 | 52 | -44.45 | 42.31 | -23.11 | -32.11 | FAIL |
| 2-persistence | N4/M5 X4.0% | 4h | 100 | -15.87 | 43.00 | -15.87 | -35.32 | 32 | -90.37 | 40.62 | -28.92 | -33.99 | FAIL |
| 2-persistence | N4/M5 X1.5% | 4h | 210 | -21.30 | 40.95 | -44.72 | -55.81 | 73 | -27.50 | 43.84 | -20.08 | -36.89 | FAIL |
| 2-persistence | N8/M10 X4.0% | 4h | 27 | -27.98 | 48.15 | -7.55 | -18.12 | 11 | 101.97 | 90.91 | 11.22 | -7.54 | FAIL |
| 2-persistence | N8/M10 X1.5% | 4h | 44 | -32.22 | 43.18 | -14.18 | -16.75 | 16 | 202.87 | 81.25 | 32.46 | -7.70 | FAIL |
| 2-persistence | N6/M8 X4.0% | 4h | 72 | -35.89 | 47.22 | -25.84 | -29.97 | 26 | 41.84 | 57.69 | 10.88 | -14.93 | FAIL |
| 2-persistence | N6/M8 X1.5% | 4h | 114 | -38.47 | 42.98 | -43.85 | -49.15 | 44 | 39.69 | 45.45 | 17.46 | -16.83 | FAIL |
| 2-persistence | N8/M10 X2.5% | 4h | 38 | -44.87 | 39.47 | -17.05 | -20.23 | 14 | 169.33 | 85.71 | 23.71 | -6.15 | FAIL |
| 2-persistence | N6/M8 X2.5% | 4h | 101 | -45.51 | 43.56 | -45.97 | -47.26 | 34 | 36.66 | 50.00 | 12.46 | -20.06 | FAIL |
| 3-breakdown | N55 gate-above-median | 1d | 6 | 30.67 | 50.00 | 1.84 | -16.86 | 3 | -771.86 | 0.00 | -23.16 | -23.16 | FAIL |
| 3-breakdown | N20 gate-above-median | 1d | 9 | -31.77 | 33.33 | -2.86 | -29.80 | 8 | -488.10 | 12.50 | -39.05 | -39.05 | FAIL |
| 3-breakdown | N55 raw | 1d | 10 | -33.52 | 50.00 | -3.35 | -32.97 | 3 | -685.22 | 0.00 | -20.56 | -20.56 | FAIL |
| 3-breakdown | N20 raw | 1d | 22 | -80.72 | 40.91 | -17.76 | -32.87 | 8 | -432.18 | 12.50 | -34.57 | -34.57 | FAIL |
| 3-breakdown | N55 gate-below-median | 1d | 5 | -120.48 | 40.00 | -6.02 | -23.68 | 1 | -628.32 | 0.00 | -6.28 | -10.78 | FAIL |
| 3-breakdown | N20 gate-below-median | 1d | 15 | -160.11 | 40.00 | -24.02 | -32.87 | 2 | 75.35 | 50.00 | 1.51 | -10.16 | FAIL |
| 3-breakdown | N20 gate-below-median | 1h | 278 | **9.84** | 29.14 | 27.35 | -16.97 | 78 | **22.79** | 29.49 | 17.77 | -11.94 | **SURVIVOR** |
| 3-breakdown | N55 gate-below-median | 1h | 125 | -3.24 | 28.00 | -4.05 | -21.12 | 34 | 72.68 | 44.12 | 24.71 | -8.34 | FAIL |
| 3-breakdown | N20 raw | 1h | 514 | -10.97 | 28.21 | -56.37 | -59.46 | 188 | -18.59 | 27.66 | -34.96 | -42.75 | FAIL |
| 3-breakdown | N55 raw | 1h | 253 | -12.16 | 28.06 | -30.75 | -45.08 | 93 | -15.52 | 33.33 | -14.43 | -24.97 | FAIL |
| 3-breakdown | N55 gate-above-median | 1h | 154 | -14.45 | 29.22 | -22.25 | -39.20 | 71 | -39.75 | 32.39 | -28.23 | -32.86 | FAIL |
| 3-breakdown | N20 gate-above-median | 1h | 279 | -20.56 | 29.39 | -57.35 | -57.35 | 125 | -31.43 | 29.60 | -39.28 | -43.36 | FAIL |
| 3-breakdown | N20 gate-below-median | 4h | 75 | **69.33** | 37.33 | 52.00 | -23.72 | 18 | **35.05** | 44.44 | 6.31 | -14.50 | **SURVIVOR** |
| 3-breakdown | N55 gate-below-median | 4h | 44 | 19.21 | 27.27 | 8.45 | -25.97 | 8 | -65.80 | 25.00 | -5.26 | -13.22 | FAIL |
| 3-breakdown | N55 gate-above-median | 4h | 26 | -21.61 | 26.92 | -5.62 | -33.13 | 17 | -177.96 | 11.76 | -30.25 | -33.86 | FAIL |
| 3-breakdown | N20 raw | 4h | 122 | -29.31 | 31.97 | -35.76 | -54.77 | 41 | -9.96 | 34.15 | -4.08 | -21.77 | FAIL |
| 3-breakdown | N55 raw | 4h | 60 | -45.54 | 23.33 | -27.33 | -42.01 | 23 | -148.91 | 13.04 | -34.25 | -37.65 | FAIL |
| 3-breakdown | N20 gate-above-median | 4h | 57 | -51.38 | 31.58 | -29.29 | -44.29 | 30 | -56.52 | 26.67 | -16.96 | -25.10 | FAIL |
| 4-forensic-widened | f>0.5bp | 1h | 150 | 35.04 | 32.67 | 52.56 | -15.57 | 30 | -60.81 | 16.67 | -18.24 | -25.78 | FAIL |
| 4-forensic-widened | f>2.0bp (orig.) | 1h | 54 | 28.91 | 29.63 | 15.61 | -24.42 | 6 | 168.96 | 50.00 | 10.14 | -4.91 | INSUFFICIENT-SAMPLE |
| 4-forensic-widened | f>1.5bp | 1h | 55 | **24.57** | 29.09 | 13.51 | -24.44 | 8 | **193.25** | 50.00 | 15.46 | -5.16 | **SURVIVOR** |
| 4-forensic-widened | f>2.0bp +retest | 1h | 57 | 10.90 | 28.07 | 6.21 | -26.81 | 6 | 49.56 | 33.33 | 2.97 | -5.70 | INSUFFICIENT-SAMPLE |
| 4-forensic-widened | f>0.5bp +retest | 1h | 170 | 7.58 | 29.41 | 12.88 | -28.75 | 34 | -11.35 | 26.47 | -3.86 | -23.93 | FAIL |
| 4-forensic-widened | f>1.0bp | 1h | 60 | **6.12** | 26.67 | 3.67 | -24.50 | 9 | **236.42** | 55.56 | 21.28 | -5.16 | **SURVIVOR** |
| 4-forensic-widened | f>1.5bp +retest | 1h | 59 | **4.14** | 27.12 | 2.44 | -26.83 | 8 | **99.38** | 37.50 | 7.95 | -5.16 | **SURVIVOR** |
| 4-forensic-widened | f>1.0bp +retest | 1h | 62 | -4.68 | 25.81 | -2.90 | -26.89 | 9 | 148.77 | 44.44 | 13.39 | -5.16 | FAIL |
| 4-forensic-widened | f>2.0bp | 2h | 77 | -4.98 | 27.27 | -3.83 | -33.15 | 14 | -1.52 | 28.57 | -0.21 | -8.97 | FAIL |
| 4-forensic-widened | f>0.5bp | 2h | 238 | -10.09 | 27.73 | -24.01 | -53.25 | 54 | -42.24 | 22.22 | -22.81 | -25.01 | FAIL |
| 4-forensic-widened | f>1.5bp | 2h | 81 | -13.11 | 25.93 | -10.62 | -35.54 | 15 | 32.52 | 33.33 | 4.88 | -8.97 | FAIL |
| 4-forensic-widened | f>1.0bp | 2h | 89 | -19.36 | 24.72 | -17.23 | -41.93 | 16 | 28.83 | 31.25 | 4.61 | -8.97 | FAIL |
| 4-forensic-widened | f>0.5bp +retest | 2h | 273 | -22.31 | 24.18 | -60.91 | -71.75 | 64 | -37.66 | 25.00 | -24.10 | -32.90 | FAIL |
| 4-forensic-widened | f>2.0bp +retest | 2h | 82 | -27.22 | 23.17 | -22.32 | -38.48 | 14 | -21.16 | 21.43 | -2.96 | -9.10 | FAIL |
| 4-forensic-widened | f>1.5bp +retest | 2h | 87 | -33.45 | 21.84 | -29.10 | -40.68 | 16 | 1.32 | 25.00 | 0.21 | -8.97 | FAIL |
| 4-forensic-widened | f>1.0bp +retest | 2h | 94 | -35.25 | 21.28 | -33.14 | -46.60 | 17 | -0.25 | 23.53 | -0.04 | -8.97 | FAIL |

64 configs. 6 SURVIVOR, 2 INSUFFICIENT-SAMPLE, 56 FAIL.

## Plain-English summary

**Family 1 (bleed rider — stacked lower highs):** the simple EMA/drawdown
variant is dead across the board (all 6 configs FAIL, badly — this is
basically "short every dip," which is exactly the naive mirror-image short
that's failed 40+ times before). The STRUCTURAL variant (real k-bar swing
detection, short only when 3 confirmed swing highs are falling AND price
breaks the last swing low) is a different animal: k=5 on 1h is a genuine
SURVIVOR (147 train / 40 val trades, +$11.38 / +$26.40 per trade). But it's
fragile — k=8 and k=12 on the same timeframe, and every k on 4h, are all
solidly negative. This smells more like one lucky parameter than a robust
edge; it did NOT generalize across its own family's neighbors, which is a
real caution flag despite passing the formal bar.

**Family 2 (persistence short):** completely dead. Every one of 18 configs
across both timeframes either fails outright or flips sign between train and
val (the classic sign of noise, not edge — e.g. N8/M10 X1.5% on 4h goes
-$32/t train but +$203/t val). "Ride the red streak" has no edge on BTC at
these timeframes once costs are paid. This family is closed.

**Family 3 (breakdown / Donchian, adaptive gates):** this is the strongest
new finding of the round. Raw Donchian breakdowns are dead (matches 40+ years
of prior short failures — breaking a low and shorting it just eats the
snap-back). The FIXED-direction adaptive gate ("only trade when ATR is ABOVE
its own trailing 365-day median," the gate direction every prior round
assumed was correct for trend-following) is also dead here. But the OPPOSITE
gate — **only take breakdown shorts when ATR is BELOW its trailing median** —
produces two genuine survivors: N20 on 1h (278 train / 78 val trades, by far
the largest sample of any survivor this round) and N20 on 4h (75 train / 18
val). The story makes sense: in a QUIET, low-vol market a fresh N-bar low is
more likely to just keep grinding down (no fuel for a violent short squeeze)
than in a loud, high-vol market where the same breakdown is more likely to be
stop-hunted and reversed. This directly matches the mission brief's own
hypothesis ("the 2025-26 regime is a low-vol grind... a surviving short must
work across regimes or explicitly gate to the regimes where it pays") — this
family found the regime and it's the quiet one, not the violent one.

**Family 4 (forensic short, widened):** the widening worked exactly as
intended. The original forensic composite (funding>2bp & 4h pop>1.5% &
ATR%>1.2%, 1h) reproduces the prior record almost exactly (train +$28.91/54t,
val +$168.96/6t) — still short 2 validation trades. Relaxing the funding
threshold to 1.5bp clears the floor cleanly: 55 train trades (+$24.57),
**8 validation trades (+$193.25)** — a genuine SURVIVOR, and the val
expectancy is even bigger than the original tight-threshold version. Two more
widened variants (f>1.0bp, f>1.5bp+retest) also clear the bar but with much
thinner train edges (+$6.12 and +$4.14/trade) — technically positive, but
thin enough that a handful of trades could flip them; treat them as weaker
siblings of the f>1.5bp result, not independent confirmations (they share
most of their trades with it). The "+retest" widening and the 2h timeframe
both failed to add value — 2h is dead across every funding threshold, and
retest entries diluted rather than helped the edge.

## Top 3 candidates for the sealed-test look

1. **Family 4 — forensic short, f>1.5bp, 1h, stop 1.69% / target 5.07% /
   48h hold, maker, real funding.** (train +$24.57/trade, 55 trades, 13.5%
   return; val +$193.25/trade, 8 trades, 15.5% return, -5.2% DD.) Strongest
   theoretical grounding of anything tested this round or in prior rounds —
   it's a direct, minimal widening of the ONE short that already had real
   forensic evidence (autopsy-derived condition enrichments) and was only
   ever blocked by sample size. This is the cleanest "the theory says this
   should work, and now it clears the bar" candidate.

2. **Family 3 — breakdown short, N20, gate BELOW trailing-median ATR%, 1h,
   stop 2x median ATR% / exit on EMA20 reclaim or 10-day time stop, maker,
   real funding.** (train +$9.84/trade, 278 trades, 27.4% return; val
   +$22.79/trade, 78 trades, 17.8% return, -11.9% DD.) By far the largest,
   most statistically solid sample of any survivor this round — 278 and 78
   trades respectively is real density, not a rare-event fluke. It's also a
   genuinely new structural finding (the adaptive gate direction inverts vs.
   every prior long-side use of the same gate), which is exactly the kind of
   regime-specific insight the mission asked for.

3. **Family 1 — bleed rider structural, k=5, 1h, stop 2x median ATR% /
   exit on structure break (new higher swing-high) or 10-day time stop,
   maker, real funding.** (train +$11.38/trade, 147 trades, 16.7% return;
   val +$26.40/trade, 40 trades, 10.6% return, -17.3% DD.) Decent sample,
   both windows solidly positive, and it's Wallace's own pattern ("one long
   bleeding leg," stacked lower highs) formalized and gauntleted. Caveat
   flagged below: this is the least robust of the three across its own
   parameter neighborhood.

**Honorable mention, NOT in the top 3:** Family 3's N20 gate-below-median on
4h (train +$69.33/75t, val +$35.05/18t) is a strong result but shares its
core signal and gate logic with the 1h pick above (same family, same
direction-of-gate finding, likely correlated trades/regime exposure) — the
1h version has 3-4x the sample and was preferred as the family's
representative.

## Caveats (read before burning a test look)

- **Sample sizes are still modest for a Bitcoin backtest.** 8-9 validation
  trades (family 4) is the bare minimum the protocol allows, not a
  comfortable margin — a couple of trades either way would flip the verdict.
  Family 3's 1h pick (78 val trades) is the one candidate with real
  statistical weight behind it.
- **Regime concentration is a real risk across all three picks.** The
  val window (2025-04 through the test boundary) covers a specific slice of
  the 2025-26 grind; none of these were stress-tested against a violent
  bear leg the way the family's train window partially was. Family 3's
  "quiet-vol-only" gate in particular means it is BY DESIGN a low-vol-regime
  strategy — expect it to go quiet or misfire if volatility character
  changes.
- **Family 1's fragility is a genuine concern, not just a footnote.** k=5
  survives, its immediate neighbors (k=8, k=12) do not, and neither does k=5
  on 4h. Nothing here is provably lookahead-biased or bugged (the swing
  detection was hand-checked for no-lookahead alignment), but a signal that
  doesn't generalize across its own parameter grid is a yellow flag for
  overfitting a lucky window, not a red line disqualifying it.
- **The stop is an approximation everywhere it's used.** The engine only
  supports a fixed stop_pct for the whole backtest, not a true per-trade
  trailing/structural stop. Families 1 and 3 use `A x median(ATR%)` measured
  on the TRAIN slice only and held fixed into val (same method round 17
  already established for this repo) — a real trailing stop to the actual
  swing high / breakdown level would likely change these numbers (probably
  for the better, since it would cut losers faster on average, but that is
  untested).
- **Families 2 (persistence) and the raw/simple variants of 1 and 3 are
  genuinely closed** — not "needs more tuning," but structurally dead the
  same way 40+ prior mirror-short attempts have been. Don't re-run persistence
  or raw-Donchian shorts without a materially different mechanism.
- Funding was real and signed throughout (shorts collect positive funding);
  family 4 is the one family where funding is load-bearing (it's a direct
  filter condition), and its edge should be understood as partly "get paid
  to hold, on top of the price move," not price alone.
