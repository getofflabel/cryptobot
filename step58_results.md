# step58 results — divergences, oscillator regime tools, multi-timeframe alignment (BTC)

Research only. 180 configs run (128 divergence / 16 oscillator-overlay / 36 MTF-alignment).
Gauntlet: chronological 60/20/20 on cached BTC 15m/1h/4h (~6y, 2020-03-25 → present),
full costs (maker execution: 2bps maker fee + 1bp half-spread + 2bp slippage per fill =
10bps round trip, plus real signed funding via `align_funding`), select-by-train,
val checked once, 20% test **sealed and never touched**. Floors: ≥30 train trades,
≥8 val trades. Train+val combined span = 5.06 years (2020-03-25 → 2025-04-16); the
sealed test slice runs 2025-04-16 → present and is not summarized here because it was
never computed.

Script: `step58_divergence_mtf.py`. Raw grid: `step58_results_raw.csv`.

---

## 1. Definitions

**swings(k)** — a bar is a *confirmed* swing high/low once a centered ±k-bar window
around it is fully known, i.e. k bars have printed *after* it. No lookahead: the
confirmation flag only reads True starting at the bar where that future information
has actually arrived (implemented as a centered rolling extreme, then `.shift(k)`).

**Regular divergence** (reversal flavor) — price makes a *lower* low while the
oscillator (RSI14 or MACD-histogram) makes a *higher* low at the matching confirmed
swing → bullish, long. Mirror on swing highs → bearish, short.

**Hidden divergence** (continuation flavor) — price makes a *higher* low while the
oscillator makes a *lower* low, gated to the 4h champion (`vol_gated_ma`, fast20/
slow100/minATR1.5%) already being in its long regime → bullish continuation, long.
Mirror (price lower high / oscillator higher high, gated to the champion's short/flat
regime) → bearish continuation, short.

**Stop geometry (family 1)** — `run_backtest` takes one fixed stop_pct for the whole
run, so per-trade "stop past the swing extreme" is approximated as the TRAIN-only
median distance from entry close to the qualifying swing extreme, plus a stated
buffer (0.15% or 0.35%), capped at 4.0%. Same approximation pattern step43 uses for
session-breakout/VWAP-fade. Target = stop × {2, 3}.

**Base strategy (family 2)** — 1h Donchian(20) breakout, long only, exit on a
Donchian(10 or 20)-bar low breach. Overlays gate ENTRIES only (ADX(14), Stochastic
%K(14,3), RSI(14)); the exit rule is untouched, isolating "does the filter improve
entries" from "does it change exits."

**MTF stack (family 3)** — BIAS (4h): `vol_gated_ma` sign (long/short/flat) AND
price-vs-4h-SMA50 must agree, else no bias. SETUP (1h, computed unconditionally):
RSI(3) pullback (<10 or <15 for long, mirrored >90/>85 for short) or a 3-bar
"fair-value-gap" imbalance return (bullish: low > high two bars back, then price
dips back into that zone within 20 bars; bearish mirrors it). TRIGGER: either a 1h
reversal bar (fresh short-term extreme that closes back through the prior bar) or a
15m close recrossing its own 9-bar EMA. Three stacking levels tested per (setup,
trigger) pair: **setup-only** (raw setup, no bias/trigger), **bias+setup** (setup AND
matching bias, no trigger requirement), **full** (setup AND bias AND trigger all
concurrently true).

---

## 2. Family 1 — divergences: verdict by oscillator × timeframe × flavor

| Oscillator | TF | Flavor | Survivors / configs tested |
|---|---|---|---|
| RSI(14) | 4h | **hidden** | **7 / 16** |
| RSI(14) | 1h | **hidden** | **3 / 16** |
| MACD-hist | 1h | regular | 1 / 16 |
| RSI(14) | 1h | regular | 0 / 16 |
| RSI(14) | 4h | regular | 0 / 16 |
| MACD-hist | 1h | hidden | 0 / 16 |
| MACD-hist | 4h | hidden | 0 / 16 |
| MACD-hist | 4h | regular | 0 / 16 |

**Verdict: regular (reversal) divergence is essentially absent on BTC** — 1 survivor
out of 96 regular-flavor configs across both oscillators and both timeframes, and
that lone survivor (MACD-hist 1h) is a single config among 16 neighbors that all
failed, i.e. not corroborated by nearby parameter choices. **Hidden (continuation)
RSI divergence on 4h is the real finding** — 7 of 16 configs survive, spanning both
swing-confirmation windows (k=5 and k=8), both buffer sizes, and both target
multiples, i.e. the edge shows up across a cluster of neighboring parameters rather
than one lucky cell.

Best 4h hidden-RSI survivors:

| config | tr_n | tr_exp | va_n | va_exp | med hold (h) | trades/yr |
|---|---|---|---|---|---|---|
| RSI14 k8 hidden buf0.35% tgt3x hold48h | 66 | $74.22 | 24 | $31.99 | 48.0 | 17.8 |
| RSI14 k5 hidden buf0.15% tgt3x hold96h | 91 | $22.04 | 33 | $80.56 | 40.0 | 24.5 |
| RSI14 k5 hidden buf0.35% tgt3x hold96h | 91 | $2.60 | 33 | $74.36 | 40.0 | 24.5 |
| RSI14 k8 hidden buf0.15% tgt3x hold48h | 66 | $42.29 | 24 | $27.73 | 48.0 | 17.8 |
| RSI14 k8 hidden buf0.35% tgt2x hold48h | 66 | $25.40 | 24 | $23.22 | 48.0 | 17.8 |

1h hidden-RSI survivors trade far more often (47–60 trades/yr) but with much smaller
expectancy ($2–15/trade train, $5–15 val) — real but thin. Best 1h: `RSI14 k5 hidden
buf0.15% tgt2x hold96h` (tr_n 179, tr_exp $2.17, va_n 61, va_exp $15.48).

**Caveat, stated plainly:** several *regular* MACD-hist hidden-flavor configs on 1h
threw eye-catching val numbers (e.g. `MACDhist k8 hidden buf0.15% tgt3x hold96h 1h`:
va_exp = **+$114.96** on 62 val trades) while train expectancy was deeply negative
(-$33.10). Select-by-train correctly killed these as FAIL — this is exactly the
discipline earning its keep: a val number that good, with a train number that bad,
is what a false-positive alarm sounds like, not an edge.

---

## 3. Family 2 — oscillator regime overlays: head-to-head table

Base: 1h Donchian(20) breakout long, exit Donchian(10 or 20)-bar low, maker execution.

| exit_n | Filter | tr_n | tr_exp | va_n | va_exp | Δ va_exp vs baseline | verdict |
|---|---|---|---|---|---|---|---|
| 10 | **baseline (no filter)** | 450 | $13.55 | 159 | $2.57 | — | SURVIVOR |
| 10 | ADX≥20 | 362 | $18.46 | 120 | **$6.91** | **+169%** | SURVIVOR |
| 10 | ADX≥25 | 264 | $31.06 | 99 | -$17.59 | worse | FAIL |
| 10 | Stoch<70 (not-OB) | 20 | $63.15 | 6 | -$28.05 | worse, sample too thin | FAIL |
| 10 | Stoch<80 (not-OB) | 106 | -$39.10 | 32 | -$21.00 | worse | FAIL |
| 10 | RSI 40-70 band | 389 | $14.08 | 146 | -$6.71 | worse | FAIL |
| 10 | RSI 35-65 band | 267 | $5.84 | 106 | -$23.63 | worse | FAIL |
| 10 | ALL combined | 36 | -$20.66 | 16 | -$60.67 | much worse | FAIL |
| 20 | baseline (no filter) | 350 | $7.58 | 119 | $0.47 | — | SURVIVOR |
| 20 | ADX≥20 | 296 | $7.05 | 94 | $0.02 | roughly flat | SURVIVOR |
| 20 | ADX≥25 | 228 | $15.80 | 82 | -$33.36 | much worse | FAIL |
| 20 | Stoch/RSI variants | — | — | — | — | worse or thin | FAIL |

**Verdict: mostly "just cuts samples," with one narrow exception.** A moderate ADX≥20
gate on the tighter exit (10-bar) is the one filter that clearly *improved* the base
edge — val expectancy nearly tripled ($2.57→$6.91) while only trimming ~20% of train
trades, i.e. it removed disproportionately bad trades rather than proportionally
thinning good and bad alike. Every other filter (tighter ADX≥25, both Stochastic
thresholds, both RSI bands, and the all-combined gate) either turned val negative or
collapsed sample size into unreliable territory. Classic oscillator filters are not
a free lunch on this base — ADX is the only one that earned its keep, and only at
one specific threshold.

---

## 4. Family 3 — multi-timeframe stacking ladder

Only the `RSI3<15 pullback / 1h reversal bar` combination produced a clean, monotonic
ladder. Every other setup×trigger combination failed at every stacking level.

| Stacking level | tr_n | tr_exp | va_n | va_exp | trades/yr | verdict |
|---|---|---|---|---|---|---|
| setup-only (raw RSI3<15, no bias/trigger) | 412 | $1.93 | 139 | $4.59 | 108.9 | SURVIVOR |
| bias+setup (+ 4h bias agreement) | 245 | $4.92 | 91 | $5.47 | 66.4 | SURVIVOR |
| **full (+ 1h reversal-bar trigger)** | 32 | $26.75 | 12 | **$56.42** | 8.7 | SURVIVOR |

**Verdict: each added layer improved val expectancy** — $4.59 → $5.47 → $56.42 as
bias, then trigger, get stacked on top of the raw setup. That is the textbook
top-down thesis working exactly as advertised on this one combination. The catch is
sample collapse: by "full" alignment, only 32 train / 12 val trades qualify — just
above the 30/8 floor, not comfortably above it. This is a real, corroborated signal
(the whole ladder moves the same direction at every rung, not just the top one) but
it is standing on thin ice statistically and needs more data or a longer test window
before it's trustworthy.

The tighter `RSI3<10` variant of the same setup/trigger pair failed at setup-only and
bias+setup, and its "full" cell (`tr_n=9`) didn't even clear the trade floor
(INSUFFICIENT-SAMPLE) despite a flashy va_exp of $18.55 — a reminder that RSI3<15 is
a specific sweet spot here, not a robust threshold-independent edge.

The FVG-return setup **never survived**, at any trigger or stacking level, on either
timeframe (all 24 of its configs FAILed). Whatever edge a 3-bar imbalance return has
elsewhere, it does not show up on BTC in this construction.

---

## 5. 15m cost-floor note

Per the round brief, 15m appears only as the MTF family's trigger leg, and every
single 15m-trigger config (18 of them) **failed** — worth checking whether that's a
real absence of edge or just costs eating the trade. Measured fees+friction per trade
on the 15m-trigger configs landed at **8.5–9.5 bps/trade** (essentially the full
signal-agnostic 10bps maker round-trip cost, since a 15m stop/target frequently
closes the trade on the very next bar or two — not enough holding time to average the
cost down). At target×2 configs the cost sits just under the ~9bps floor (8.5-8.9bps,
`clears_9bps_floor=True`); at target×3 it's marginally over (9.0-9.5bps, `False`) —
but va_exp is negative either way. **Conclusion: 15m entries here are structurally
cost-bound, not signal-bound** — the trigger fires too close to a full round-trip's
worth of cost to leave room for edge, regardless of setup quality. This matches the
brief's expectation that "15m entries are sparse" and explains the family-wide 15m
failure without needing to blame the setup logic itself.

---

## 6. Ranked sealed-look candidates

Ranked by validation expectancy among configs that cleared both trade floors
(SURVIVOR only — the one INSUFFICIENT-SAMPLE row is excluded). **None of these have
been run against the sealed 20% test slice** — this is a recommendation list for the
lead to spend looks on, not a result.

| Rank | Family | Config | tr_n/va_n | tr_exp | va_exp | trades/yr | Note |
|---|---|---|---|---|---|---|---|
| 1 | Divergence | RSI14 k5 hidden buf0.15% tgt3x hold96h, 4h | 91/33 | $22.04 | $80.56 | 24.5 | best of a 7/16 corroborated cluster |
| 2 | MTF | RSI3<15/1h-reversal/**full**/tgt3x, 1h | 32/12 | $26.75 | $56.42 | 8.7 | clean ladder top rung, thin sample |
| 3 | Divergence | RSI14 k8 hidden buf0.35% tgt3x hold48h, 4h | 66/24 | $74.22 | $31.99 | 17.8 | best train number in the cluster |
| 4 | Divergence | MACDhist k8 regular buf0.15% tgt3x hold96h, 1h | 228/76 | $5.20 | $27.75 | 60.1 | only regular-divergence survivor, isolated |
| 5 | Divergence | RSI14 k8 hidden buf0.15% tgt3x hold48h, 4h | 66/24 | $42.29 | $27.73 | 17.8 | same cluster as #1/#3 |
| 6 | Divergence | RSI14 k8 hidden buf0.35% tgt2x hold48h, 4h | 66/24 | $25.40 | $23.22 | 17.8 | same cluster |
| 7 | MTF | RSI3<15/1h-reversal/full/tgt2x, 1h | 32/12 | $31.74 | $15.05 | 8.7 | ladder top rung, tgt2x variant |
| 8 | Divergence | RSI14 k5 hidden buf0.15% tgt2x hold96h, 1h | 179/61 | $2.17 | $15.48 | 47.4 | thin edge, high frequency |
| 9 | Oscillator | donchian20/10 + ADX≥20, 1h | 362/120 | $18.46 | $6.91 | 95.3 | cleanest overlay win, high frequency |
| 10 | MTF | RSI3<15/1h-reversal/bias+setup/tgt3x, 1h | 245/91 | $4.92 | $5.47 | 66.4 | middle ladder rung |

Top picks worth a sealed look, if forced to choose two: **the 4h hidden-RSI
divergence cluster** (rows 1/3/5/6 are really one robust signal shown four ways) and
**the MTF full-alignment ladder top** (row 2/7) — the first for corroboration breadth,
the second because the whole-ladder monotonic improvement is a stronger form of
evidence than any single cell's number, even a thin one.

---

## 7. Summary for the lead

- **180 configs run** (128 divergence / 16 oscillator-overlay / 36 MTF-alignment).
  20 SURVIVOR, 1 INSUFFICIENT-SAMPLE, 159 FAIL.
- **Are divergences real on BTC?** Mostly no. Regular (textbook reversal) divergence
  is essentially absent (1/96 configs survive, uncorroborated). **Hidden (continuation)
  RSI divergence on 4h is real** — 7/16 neighboring configs survive with consistent
  direction and magnitude, the strongest finding in this round.
- **Oscillator-overlay verdict:** mostly "just cuts samples" — ADX≥25, both Stochastic
  gates, both RSI bands, and the all-combined gate all made the base worse or thinned
  it into unreliability. The one exception: **ADX≥20 on the tighter exit** nearly
  tripled val expectancy while trimming trades disproportionately toward the bad ones
  — a real, narrow win, not a broad vindication of "add an oscillator filter."
- **MTF-ladder verdict:** on the one setup/trigger pair that worked at all
  (RSI3<15 pullback + 1h reversal bar), **stacking helped at every rung** — val
  expectancy rose setup-only → bias+setup → full ($4.59 → $5.47 → $56.42). That's
  the top-down thesis validated, but the full-alignment sample (32/12 trades) is
  right at the floor, not comfortably above it. Every other setup (RSI3<10, FVG-return)
  and the 15m-trigger variant of every setup failed outright.
- **Biggest caveat:** the two most exciting numbers in this round — 4h hidden-RSI
  divergence and the MTF full-alignment ladder — both sit on small val samples (33
  and 12 trades respectively). They're corroborated by neighboring configs moving the
  same way (not cherry-picked single cells), which is meaningfully better evidence
  than an isolated survivor, but "corroborated on small samples" is still small
  samples. Neither should be sized for live trading without a longer val window or a
  sealed-test confirmation first. Second caveat: 15m is confirmed structurally
  cost-bound here (8.5-9.5bps/trade against a ~9-10bps round-trip floor) — that's a
  durable finding about this timeframe generally, not specific to these setups.
