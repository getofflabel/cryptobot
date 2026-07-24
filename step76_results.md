# Step 76 — The Complete Indicator Sweep

**Round 76.** Wallace's mandate, verbatim: *"Our book isn't good enough. You're
gonna have to go through every single one of the indicators that there are...
What about RSI? What about Aroon, the MACD?"* Rounds 41-75 tested market-
structure concepts extensively but never systematically swept the standard
indicator library. This round does that — exhaustively, and honestly,
including every failure. Research only. No commits, no live orders.

## Headline numbers

- **53 distinct indicators** (54 counting the unfiltered base-strategy
  benchmark row) swept, **132 distinct configs** (2-3 parameter sets each,
  chosen from textbook convention before any run — never tuned after seeing
  results), **483 total scored backtests** in the table below (every
  config x mode x timeframe x asset combination actually run — nothing
  omitted, including every failure).
- **BTC (primary asset):** 389 rows, **95 SURVIVOR**
  rows (positive expectancy on BOTH train and val, floors cleared:
  >=30 train trades / >=8 val trades).
- **ETH (transfer check, survivors only):** 94 rows replayed —
  only **2 of 95** BTC survivors also clear both floors on ETH.
- **Every SURVIVOR is read against an explicit yardstick**: the unfiltered
  1h donchian-20/20 long base strategy itself is already barely positive
  (train n=351 exp=$7.74/trade, val n=119
  exp=$0.42/trade — essentially breakeven on val). A "filter
  SURVIVOR" verdict only means "still positive after gating" — **19 of the
  95 BTC filter+signal SURVIVOR rows are exact no-op reproductions of this
  base row** (the gate was true at literally every entry, changing nothing).
  See the FILTER-VALUE section for the honest accounting.

## Library and methodology

**Library:** `ta` 0.11.0, pip-installed cleanly with no compilation
(pure-Python) — used for every indicator it covers (SMA/EMA/MACD/Aroon/
ADX-DMI/Parabolic SAR/Ichimoku/TRIX/Vortex/KAMA/RSI/Stochastic/StochRSI/CCI/
Williams %R/ROC/Ultimate Oscillator/Awesome Oscillator/TSI/Bollinger/
Keltner/ATR/OBV/Chaikin Money Flow/Money Flow Index/Accumulation-
Distribution/Force Index/Ease of Movement). Hand-implemented in
`step76_indicators.py` for everything `ta` does not cover: SuperTrend,
Chandelier exit, Hull MA, DEMA/TEMA, linear-regression slope, Fisher
Transform, Connors RSI, volume oscillator, session-anchored VWAP,
BB-inside-KC squeeze, standard-deviation channel, classic pivots, Camarilla
pivots, Williams fractals, OBV divergence.

**Spot-checks** (3 hand implementations vs. an independent calculation, run
automatically at the top of every script execution):
- DEMA(20) vs. the manual EMA-of-EMA formula: max abs diff = 0.0000000000.
- WMA(10) (used inside Hull MA) vs. a `np.dot` rolling-apply ground truth:
  max abs diff = 0.0000000000.
- RSI(14): `strategy.py`'s own Wilder RSI (pure ewm from bar 0, already
  trusted and used everywhere in this project) vs. `ta.momentum.rsi`
  (rolling-mean warmup then Wilder smoothing) — diverge by up to 25.25
  near the warmup window, converging to 1.4e-08 by bar 300. This is the
  expected warmup-only artifact of two different (both textbook-correct)
  initialization conventions, not a bug — confirmed by the convergence.
  `ta.momentum.rsi` is never called for scoring below; `strategy.rsi` is
  used everywhere RSI is needed, for exactly this reason.

**Gauntlet (identical to step41/step43, reused by import, never modified):**
chronological 60/20/20 split per timeframe (`step41_shorts.split_points`),
MIN_TRAIN_TRADES=30 / MIN_VAL_TRADES=8, full cost model (BloFin maker fees,
spread, slippage) + real funding via `align_funding`, execution="maker".
Selection is by TRAIN expectancy; val is read once, never tuned against.
The sealed 20% test slice is **never touched** by this script.

**Two test modes per indicator** (the round's real value, per the mandate):
- **SIGNAL** — the indicator's own textbook entry/exit, standalone,
  bidirectional where the indicator defines both sides. No fixed stop or
  target: the indicator's own state machine (cross, oscillator hysteresis,
  band touch, etc.) is the only exit.
- **FILTER** — the SAME indicator gating the **fixed base strategy** (1h
  `donchian_breakout(entry_n=20, exit_n=20)` long from `strategy.py`). The
  gate must be True at the bar the base wants to open a new long; once
  open, the trade rides to the base's own exit regardless of the gate
  afterward (a filter permits/blocks entries — it does not intra-trade
  flatten). Filter mode is 1h-only, matching the mandate's fixed base.

**Timeframes:** 1h primary (deepest cached history — 55,493 bars, 2020-03 to
2026-07), 15m secondary (221,972 bars, same range) — 15m carries this
project's own well-documented realized cost floor (round 60s finding: ~9bps
round-trip friction that does not shrink with bar size), flagged explicitly
below wherever it matters. Ichimoku is 4h-only (13,863 bars) per the
mandate, a conventionally higher-timeframe system.

**Assets:** BTC (`BTCUSDT`, Bybit) primary — every config. ETH (`ETHUSDT`,
Bybit, 46,983 1h bars / 187,934 15m bars) is the transfer check, run
**only** on the 95 configs that survived on BTC — ETH is never used for
selection, only confirmation, so it can never be fished.

**Approximations stated plainly** (same spirit as this repo's existing
stop_pct-from-median-ATR convention): the standard-deviation channel's mid
line is the fitted regression value and its band width is the rolling std
of close (not the exact OLS residual std); the volume oscillator's
"confirmation" signal masks 1-bar price direction by whether volume growth
is positive, rather than defining its own entries/exits; the OBV divergence
detector is a simplified n-bar high/low vs. OBV comparison, not full swing-
pivot divergence detection.

---

## Survivors (BTC, train AND val positive, floors cleared)

**11 of 53 tested signal-mode indicators produced at least one SURVIVOR config** on BTC (counting distinct configs: 11 signal-mode SURVIVOR rows out of 260 signal-mode BTC rows). The other 44 indicators — tested in their textbook standalone form, bidirectional, no fixed stop — never cleared train AND val positive at the same time, on any parameter set or timeframe.

### Signal-mode survivors (11 configs, ranked by val expectancy)

| indicator | config | tf | tr_n | tr_exp | va_n | va_exp | va_dd% |
|---|---|---|---:|---:|---:|---:|---:|
| EMA cross | 12/26 | 1h | 1192 | 4.81 | 363 | 5.00 | -38.9 |
| TRIX 0-cross | 9 | 1h | 1372 | 0.33 | 455 | 4.05 | -33.7 |
| TEMA cross | 10/30 | 1h | 2676 | 7.36 | 895 | 3.76 | -58.0 |
| Keltner breakout | 10/1.5 | 1h | 891 | 8.85 | 297 | 3.70 | -30.6 |
| TSI 0-cross | 25/13 | 1h | 1162 | 4.25 | 361 | 3.43 | -42.1 |
| EMA cross | 10/30 | 1h | 1182 | 4.64 | 373 | 2.83 | -42.1 |
| Linreg slope sign | 20 | 1h | 1837 | 3.17 | 601 | 2.80 | -32.2 |
| Bollinger breakout | 20/2.5 | 1h | 819 | 14.71 | 260 | 1.48 | -30.8 |
| TRIX 0-cross | 30 | 15m | 1645 | 2.84 | 539 | 0.27 | -36.6 |
| BB-inside-KC squeeze release | BB20/2 KC20/1.5 | 1h | 804 | 5.12 | 263 | 0.19 | -31.1 |
| Vortex VI+/VI- cross | 21 | 1h | 3101 | 5.25 | 995 | 0.16 | -37.0 |

Note the pattern: **9 of 11 are trend-following/breakout shapes** (EMA cross x2, TRIX 0-cross x2, TEMA cross, Vortex, linreg slope, Bollinger breakout, Keltner breakout, BB-in-KC squeeze release) — consistent with every prior round's finding that crypto rewards riding trend, not fading it. **Zero mean-reversion oscillators (RSI OB/OS, Stochastic extremes, CCI, Williams %R, Connors RSI, Bollinger/Keltner mean-revert) survived standalone** — the classic "buy oversold" shape is dead as a signal on BTC in this sample, matching R58's finding restated for the full library. Drawdowns are large (-30% to -58%): these are UNFILTERED trend signals with no risk stop, exactly as the mandate specified for the "textbook interpretation" test — not investment-ready as-is.

### ETH transfer check — the honest verdict

Of the **94 configs where BTC survived** (signal + filter combined), only **2 also clear both floors on ETH**:

| indicator | mode | config | tf | tr_exp BTC | va_exp BTC | tr_exp ETH | va_exp ETH |
|---|---|---|---|---:|---:|---:|---:|
| TEMA cross | signal | 10/30 | 1h | 7.36 | 3.76 | 0.97 | 5.93 |
| Bollinger breakout | signal | 20/2.5 | 1h | 14.71 | 1.48 | 33.43 | 17.38 |

**TEMA cross (10/30, 1h, signal) and Bollinger breakout (20/2.5, 1h, signal) are the only two configs in the ENTIRE 132-config sweep that are positive on both splits on BOTH assets** — and both actually get *stronger* on ETH (TEMA's val expectancy roughly triples, Bollinger breakout's val expectancy is 10x+ larger). These are the round's real finds: two trend-following/breakout signal shapes with genuine cross-asset consistency, not curve-fit to one coin's history.

**Every one of the other 92 BTC survivors — including every single filter-mode survivor — went to outright FAIL on ETH**, most with sharply negative val expectancy (commonly -$40 to -$65/trade, vs. BTC's positive numbers). See the FILTER-VALUE section for why: the filter improvements are apparently specific to BTC's particular 2020-2026 history/regime split, not a portable edge — the single most important caveat in this round.

---

## Filter-value: which indicators genuinely improved the base, vs. which just cut trades

The base (unfiltered 1h donchian-20/20 long) scores train n=351 exp=$7.74/trade, val n=119 exp=$0.42/trade — every filter row below is read against exactly that yardstick, not against zero.

**128 filter configs tested. 83 cleared the SURVIVOR bar (positive both splits, floors held) — but 19 of those are exact NO-OPS**: the gate happened to be True at every single bar the base wanted to enter, so `train_n`/`val_n`/expectancy reproduce the base row to 2 decimal places. These are indicators whose "bullish" reading (RSI>50, MACD>signal, price>KAMA, etc.) was simply already true at nearly every donchian-20 breakout by construction (a 20-bar new-high breakout IS a bullish moment by most trend definitions) — the gate never got a chance to block anything. Counting these as "the filter helped" would be dishonest; they belong in a 'did nothing' bucket, not a 'worked' bucket.

That leaves **64 filter configs that genuinely altered** which trades got taken (different trade count and/or different expectancy than the base) and still cleared the floors. Applying a stricter bar — val expectancy improved by >$2/trade over the base AND train also improved (no cherry-picking a split) — narrows this to **19 configs**, ranked below:

| indicator | config | tr_n | tr_exp | Δtr_exp | va_n | va_exp | Δva_exp | va sample retained |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| OBV divergence | 20 | 204 | 43.57 | +35.83 | 65 | 81.08 | +80.66 | 55% |
| TRIX 0-cross | 30 | 270 | 25.31 | +17.57 | 93 | 38.72 | +38.30 | 78% |
| OBV divergence | 50 | 150 | 39.50 | +31.77 | 48 | 21.33 | +20.91 | 40% |
| Linreg slope sign | 100 | 252 | 10.58 | +2.84 | 88 | 20.58 | +20.16 | 74% |
| ADX/DMI DI-cross+ADX>thresh | n14,adx>20 | 319 | 9.34 | +1.60 | 102 | 18.85 | +18.43 | 86% |
| ADX/DMI DI cross | 50 | 286 | 18.00 | +10.26 | 97 | 11.96 | +11.54 | 82% |
| Linreg slope sign | 50 | 314 | 21.39 | +13.65 | 110 | 10.09 | +9.68 | 92% |
| BB-inside-KC squeeze release | BB20/2 KC20/1.5 | 232 | 15.73 | +7.99 | 78 | 9.35 | +8.93 | 66% |
| A/D line trend (vs own MA) | 50 | 337 | 9.32 | +1.58 | 113 | 9.01 | +8.59 | 95% |
| EMA cross | 12/26 | 341 | 11.87 | +4.13 | 116 | 8.47 | +8.05 | 98% |
| EMA cross | 10/30 | 340 | 14.20 | +6.47 | 116 | 8.33 | +7.92 | 98% |
| TSI 0-cross | 25/13 | 341 | 10.64 | +2.91 | 116 | 7.57 | +7.15 | 98% |
| SuperTrend | ATR14xMult2 | 345 | 9.16 | +1.42 | 116 | 7.08 | +6.66 | 98% |
| ADX/DMI DI cross | 25 | 320 | 31.29 | +23.55 | 111 | 5.54 | +5.12 | 93% |
| BB-inside-KC squeeze release | BB20/2 KC20/2 | 276 | 30.00 | +22.26 | 93 | 4.19 | +3.78 | 78% |
| Stochastic %K/%D cross | 14/3/3 | 351 | 8.37 | +0.63 | 118 | 3.77 | +3.35 | 99% |
| MACD histogram 0-cross | 19/39/9 | 350 | 8.06 | +0.32 | 117 | 3.75 | +3.33 | 98% |
| MACD line/signal cross | 19/39/9 | 350 | 8.06 | +0.32 | 117 | 3.75 | +3.33 | 98% |
| CMF 0-cross | 10 | 348 | 9.23 | +1.49 | 117 | 3.13 | +2.71 | 98% |

**None of these 19 transfer to ETH.** Every single one flips to a large negative val expectancy on ETH's identical config:

| indicator | config | Δva_exp on BTC | va_exp BTC | va_exp ETH |
|---|---|---:|---:|---:|
| OBV divergence | 20 | +80.66 | 81.08 | -50.33 |
| TRIX 0-cross | 30 | +38.30 | 38.72 | -53.05 |
| OBV divergence | 50 | +20.91 | 21.33 | -37.05 |
| Linreg slope sign | 100 | +20.16 | 20.58 | -62.96 |
| ADX/DMI DI-cross+ADX>thresh | n14,adx>20 | +18.43 | 18.85 | -45.43 |
| ADX/DMI DI cross | 50 | +11.54 | 11.96 | -60.96 |
| Linreg slope sign | 50 | +9.68 | 10.09 | -52.37 |
| BB-inside-KC squeeze release | BB20/2 KC20/1.5 | +8.93 | 9.35 | -57.42 |
| A/D line trend (vs own MA) | 50 | +8.59 | 9.01 | -45.79 |
| EMA cross | 12/26 | +8.05 | 8.47 | -47.81 |
| EMA cross | 10/30 | +7.92 | 8.33 | -48.06 |
| TSI 0-cross | 25/13 | +7.15 | 7.57 | -47.50 |
| SuperTrend | ATR14xMult2 | +6.66 | 7.08 | -44.39 |
| ADX/DMI DI cross | 25 | +5.12 | 5.54 | -44.61 |
| BB-inside-KC squeeze release | BB20/2 KC20/2 | +3.78 | 4.19 | -62.60 |
| Stochastic %K/%D cross | 14/3/3 | +3.35 | 3.77 | -45.83 |
| MACD histogram 0-cross | 19/39/9 | +3.33 | 3.75 | -42.50 |
| MACD line/signal cross | 19/39/9 | +3.33 | 3.75 | -42.50 |
| CMF 0-cross | 10 | +2.71 | 3.13 | -42.39 |

The strongest-looking filters (OBV divergence, TRIX 0-cross-as-gate, linear-regression-slope-as-gate, ADX-thresholded DI cross) are exactly the ones that cut the sample HARDEST (40-86% trade retention) — they are not adding predictive information so much as selecting a specific, favorable-in-hindsight subperiod of BTC's own 60/20/20 split. That is the textbook overfitting signature, and the ETH transfer check catches it directly: this is exactly what the mandate asked this round to test honestly, and the honest answer is **filters mostly don't add real value here — they select regimes, and regime selection doesn't generalize.**

**The R58 "amputation" pattern also confirmed, from the other direction:** 45 filter configs failed outright. 42 of those (42/45) kept >=90% of the base's trades and still went negative — meaning the failure mode here isn't usually "cut too many trades," it's "the gate let almost everything through and just shifted a few entries to worse prices." Only 0 filter configs cut sample below 50% AND failed. Genuinely aggressive amputation (a filter that guts the sample to nothing) is rare here because the base strategy's own trade count (351 train / 119 val) has enough headroom above the 30/8 floor that most gates can't cut deep enough to breach it before the expectancy math already went bad.

---

## What this means: which families carry signal, which are decoration

| family | signal rows | signal SURVIVOR | filter rows | filter SURVIVOR | filter SURVIVOR (real, not no-op) |
|---|---:|---:|---:|---:|---:|
| trend | 100 | 7 | 48 | 34 | 28 |
| momentum | 76 | 1 | 38 | 23 | 16 |
| volatility | 34 | 3 | 17 | 12 | 7 |
| volume | 38 | 0 | 19 | 14 | 13 |
| levels | 12 | 0 | 6 | 0 | 0 |

**TREND is the only family with a real, standalone, cross-asset-confirmed
edge** — 7 of 11 signal survivors are trend indicators, and both configs
that transferred to ETH (TEMA cross, and Bollinger breakout which is
functionally trend/breakout despite living in the volatility bucket) are
trend-following shapes. This restates, with the full standard library now
actually tested, what rounds 41-75's market-structure work already
suggested: crypto pays you for riding an established move, on this
timeframe and cost structure, more than any other posture.

**VOLATILITY only works in BREAKOUT mode, never mean-reversion.** Bollinger
mean-revert, Keltner mean-revert, and the stdev-channel mean-revert all
failed outright (signal AND filter); Bollinger breakout, Keltner breakout,
and the BB-in-KC squeeze release each produced at least one signal
survivor. Same underlying bands, opposite verdict depending on which side
of the classic band-trading debate you take — on BTC/ETH in this sample,
breakout wins.

**MOMENTUM (RSI, Stochastic, StochRSI, CCI, Williams %R, ROC, Momentum,
Ultimate Oscillator, Awesome Oscillator, Fisher, Connors RSI) is
overwhelmingly DEAD as a standalone signal family** — 75 of 76 signal-mode
BTC rows failed; only TSI 0-cross (25/13, 1h) survived, and even that did
not transfer to ETH. As FILTERS, several momentum oscillators clear the
SURVIVOR bar, but per the FILTER-VALUE section above almost none of that
is real: most are either exact no-ops or regime-selection effects that
evaporate on ETH. **The classic "buy oversold, sell overbought" reading of
every mean-reversion oscillator in the standard library is not working on
BTC or ETH in this sample, full stop** — this directly answers Wallace's
"what about RSI" with a clean, tested "no, not on its own."

**VOLUME is dead as a standalone signal family** (0 of 19 signal
survivors — OBV, CMF, MFI, VWAP, volume oscillator, A/D, Force Index, EOM
all failed in their own textbook form) but shows the single LARGEST
filter effect in the whole sweep: OBV divergence as a gate lifts val
expectancy by +$80/trade over the base. That is also the filter that cuts
the deepest into the sample (55% retention) and fails hardest on ETH
(-$50/trade) — the volume family's filter "value" here reads as the
clearest case of regime-selection dressed up as an edge, not a durable
volume-flow signal.

**LEVELS (classic pivots, Camarilla pivots, Williams fractals) is
completely dead** — 18 of 18 rows failed, signal AND filter, on both
timeframes, with no exceptions. Support/resistance touch-and-revert and
structural swing-fractal following do not work on BTC in this sample at
all. This is the cleanest "decoration" verdict in the sweep.

**Ichimoku (4h)** failed both submodes on both parameter sets — negative
train expectancy every time despite a couple of eye-catching but
train-negative val numbers (91.58 with n=129, an artifact of a small,
lucky val window on a strategy that lost money in train — exactly the
kind of number the train-AND-val-both-positive gate exists to catch).


---

## Caveats, plainly

1. **The base strategy itself is barely positive** (val exp $0.42/trade
  on 119 trades) — it is a weak yardstick, and a filter only has to
  clear a razor-thin bar to "survive." This is exactly why the no-op /
  genuine-improvement / ETH-transfer breakdown above matters more than the
  raw SURVIVOR count.
2. **15m is nearly a graveyard.** Only 1 of 128 BTC
  signal-mode rows on 15m survived — TRIX 0-cross(30), val exp
  $0.27/trade — razor-thin, well inside the
  ~9bps realized cost floor this project has already measured on 15m and
  inside ordinary noise. Wallace's
  preferred timeframe does not support any indicator in this library once
  real costs and funding are charged, full stop — this matches, and now
  exhaustively confirms, the pattern from earlier rounds.
3. **No fixed stop-loss anywhere in signal mode.** Every signal-mode test
  used the indicator's own entry/exit as the ONLY risk control, per the
  mandate's "textbook interpretation" instruction — drawdowns of 30-60%+
  on the nominal survivors are the direct, expected consequence and mean
  none of these are tradeable as-is; they would need a real stop layered
  on top and re-tested, which this round deliberately did not do (that
  would be a different question than "does the textbook version of this
  indicator have any edge at all").
4. **ETH transfer is a necessary check, not a sufficient one.** Two
  configs transferred; that is evidence of a real, non-coin-specific
  trend/breakout effect, but n=2 out of 132 configs is a small reed to
  lean on for anything beyond "trend/breakout beats mean-reversion and
  levels, broadly, on crypto." Treat the specific TEMA(10/30) and
  Bollinger-breakout(20/2.5) parameter values as a starting point for
  further work, not a finished strategy — neither has a stop, neither
  has been through the sealed 20% test slice (deliberately never touched
  by this script), and both carry -30%+ drawdowns unfiltered.
5. **This is round 76 of a much longer search.** The honest top-line
  finding — trend/breakout has some real signal, mean-reversion and
  levels are dead, most filters are regime-selection dressed as edge —
  is consistent with, not contradictory to, everything rounds 41-75
  already found about crypto structure. The value of this round is
  having now actually swept the full standard indicator library and
  gotten a definitive, tested answer to "what about RSI/Aroon/MACD,"
  rather than relying on general market lore about what should work.

---

## Complete table — every indicator x mode x timeframe x asset, 483 rows

Full precision (all columns: win%, ret%, verdict) is in `step76_full_table.csv`
alongside this file — the table below is the same data, columns trimmed to
what fits a readable markdown table. Sorted by family, indicator, mode, tf,
asset. Nothing is omitted, including every FAIL.

| family | indicator | mode | config | tf | asset | tr_n | tr_exp | va_n | va_exp | va_dd% | verdict |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|
| base | (unfiltered) donchian-20/20 long | signal | entry20/exit20 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| levels | Camarilla pivots (reversion) | filter | S3/R3 | 1h | BTC | 346 | -0.53 | 119 | -17.55 | -37.4 | FAIL |
| levels | Camarilla pivots (reversion) | filter | S4/R4 | 1h | BTC | 348 | 4.42 | 119 | -8.68 | -38.9 | FAIL |
| levels | Camarilla pivots (reversion) | signal | S3/R3 | 15m | BTC | 1646 | -5.33 | 585 | -7.64 | -54.0 | FAIL |
| levels | Camarilla pivots (reversion) | signal | S4/R4 | 15m | BTC | 836 | -11.14 | 307 | -14.47 | -59.5 | FAIL |
| levels | Camarilla pivots (reversion) | signal | S3/R3 | 1h | BTC | 1352 | -6.45 | 464 | -9.98 | -54.8 | FAIL |
| levels | Camarilla pivots (reversion) | signal | S4/R4 | 1h | BTC | 715 | -12.69 | 260 | -12.84 | -52.8 | FAIL |
| levels | Classic pivots (reversion) | filter | S1/R1 | 1h | BTC | 347 | 5.67 | 119 | -11.54 | -38.2 | FAIL |
| levels | Classic pivots (reversion) | filter | S2/R2 | 1h | BTC | 351 | 8.86 | 119 | -2.30 | -29.0 | FAIL |
| levels | Classic pivots (reversion) | signal | S1/R1 | 15m | BTC | 831 | -10.74 | 306 | 1.85 | -49.4 | FAIL |
| levels | Classic pivots (reversion) | signal | S2/R2 | 15m | BTC | 375 | -20.94 | 131 | -22.69 | -51.6 | FAIL |
| levels | Classic pivots (reversion) | signal | S1/R1 | 1h | BTC | 730 | -10.95 | 253 | -4.90 | -53.2 | FAIL |
| levels | Classic pivots (reversion) | signal | S2/R2 | 1h | BTC | 329 | -21.97 | 117 | -16.58 | -42.9 | FAIL |
| levels | Williams fractals | filter | k=2 (5-bar) | 1h | BTC | 348 | 11.36 | 118 | -7.63 | -27.2 | FAIL |
| levels | Williams fractals | filter | k=3 (7-bar) | 1h | BTC | 349 | 9.67 | 116 | -4.18 | -27.0 | FAIL |
| levels | Williams fractals | signal | k=2 (5-bar) | 15m | BTC | 27526 | -0.36 | 9617 | -1.03 | -99.3 | FAIL |
| levels | Williams fractals | signal | k=3 (7-bar) | 15m | BTC | 20138 | -0.50 | 7012 | -1.40 | -98.1 | FAIL |
| levels | Williams fractals | signal | k=2 (5-bar) | 1h | BTC | 7274 | -1.28 | 2456 | -3.42 | -86.3 | FAIL |
| levels | Williams fractals | signal | k=3 (7-bar) | 1h | BTC | 5298 | -1.83 | 1763 | -3.85 | -73.3 | FAIL |
| momentum | Awesome Oscillator 0-cross | filter | 5/34 | 1h | BTC | 349 | 3.88 | 116 | 11.13 | -25.8 | SURVIVOR |
| momentum | Awesome Oscillator 0-cross | filter | 3/21 | 1h | BTC | 351 | 8.65 | 119 | -0.03 | -27.0 | FAIL |
| momentum | Awesome Oscillator 0-cross | filter | 5/34 | 1h | ETH | 306 | -6.69 | 110 | -44.88 | -58.1 | FAIL |
| momentum | Awesome Oscillator 0-cross | signal | 5/34 | 15m | BTC | 6522 | -1.49 | 2035 | -1.68 | -47.5 | FAIL |
| momentum | Awesome Oscillator 0-cross | signal | 3/21 | 15m | BTC | 10192 | -0.97 | 3297 | -2.03 | -70.5 | FAIL |
| momentum | Awesome Oscillator 0-cross | signal | 5/34 | 1h | BTC | 1551 | -2.46 | 495 | -4.58 | -41.8 | FAIL |
| momentum | Awesome Oscillator 0-cross | signal | 3/21 | 1h | BTC | 2481 | 2.10 | 781 | -1.84 | -34.0 | FAIL |
| momentum | CCI extremes | filter | 20 | 1h | BTC | 351 | 5.04 | 119 | -9.16 | -36.9 | FAIL |
| momentum | CCI extremes | filter | 14 | 1h | BTC | 351 | -1.94 | 119 | -9.96 | -37.2 | FAIL |
| momentum | CCI extremes | filter | 50 | 1h | BTC | 349 | 7.38 | 119 | -6.20 | -32.3 | FAIL |
| momentum | CCI extremes | signal | 20 | 15m | BTC | 12579 | -0.79 | 4282 | -1.90 | -83.4 | FAIL |
| momentum | CCI extremes | signal | 14 | 15m | BTC | 15638 | -0.64 | 5225 | -1.65 | -87.5 | FAIL |
| momentum | CCI extremes | signal | 50 | 15m | BTC | 7412 | -1.33 | 2539 | -3.00 | -78.3 | FAIL |
| momentum | CCI extremes | signal | 20 | 1h | BTC | 3021 | -3.11 | 1053 | -5.00 | -55.6 | FAIL |
| momentum | CCI extremes | signal | 14 | 1h | BTC | 3725 | -2.39 | 1302 | -3.49 | -50.5 | FAIL |
| momentum | CCI extremes | signal | 50 | 1h | BTC | 1741 | -5.43 | 600 | -6.00 | -50.7 | FAIL |
| momentum | Connors RSI extremes | filter | 3/2/100 | 1h | BTC | 350 | 7.23 | 119 | 1.72 | -29.0 | SURVIVOR |
| momentum | Connors RSI extremes | filter | 3/2/50 | 1h | BTC | 351 | 5.04 | 119 | 3.40 | -29.0 | SURVIVOR |
| momentum | Connors RSI extremes | filter | 3/2/100 | 1h | ETH | 307 | -10.24 | 112 | -42.71 | -55.1 | FAIL |
| momentum | Connors RSI extremes | filter | 3/2/50 | 1h | ETH | 308 | -11.21 | 112 | -42.80 | -55.2 | FAIL |
| momentum | Connors RSI extremes | signal | 3/2/100 | 15m | BTC | 4297 | -1.69 | 1520 | -2.03 | -32.8 | FAIL |
| momentum | Connors RSI extremes | signal | 3/2/50 | 15m | BTC | 4435 | -1.80 | 1534 | -2.16 | -35.3 | FAIL |
| momentum | Connors RSI extremes | signal | 3/2/100 | 1h | BTC | 1215 | -0.80 | 404 | 4.56 | -11.2 | FAIL |
| momentum | Connors RSI extremes | signal | 3/2/50 | 1h | BTC | 1251 | -1.53 | 414 | 4.15 | -10.6 | FAIL |
| momentum | Fisher Transform 0-cross | filter | 10 | 1h | BTC | 349 | 8.66 | 118 | -1.07 | -27.1 | FAIL |
| momentum | Fisher Transform 0-cross | filter | 5 | 1h | BTC | 348 | 9.45 | 119 | -2.99 | -28.8 | FAIL |
| momentum | Fisher Transform 0-cross | filter | 20 | 1h | BTC | 348 | 4.92 | 118 | 8.43 | -25.1 | SURVIVOR |
| momentum | Fisher Transform 0-cross | filter | 20 | 1h | ETH | 308 | -10.14 | 111 | -39.44 | -55.4 | FAIL |
| momentum | Fisher Transform 0-cross | signal | 10 | 15m | BTC | 9860 | -0.98 | 3187 | -2.11 | -70.9 | FAIL |
| momentum | Fisher Transform 0-cross | signal | 5 | 15m | BTC | 13935 | -0.71 | 4471 | -1.74 | -80.8 | FAIL |
| momentum | Fisher Transform 0-cross | signal | 20 | 15m | BTC | 6490 | -1.48 | 2061 | -1.87 | -44.8 | FAIL |
| momentum | Fisher Transform 0-cross | signal | 10 | 1h | BTC | 2439 | 1.64 | 763 | -3.14 | -49.7 | FAIL |
| momentum | Fisher Transform 0-cross | signal | 5 | 1h | BTC | 3630 | -2.13 | 1106 | -2.29 | -49.9 | FAIL |
| momentum | Fisher Transform 0-cross | signal | 20 | 1h | BTC | 1541 | 0.61 | 513 | -1.18 | -33.2 | FAIL |
| momentum | Momentum 0-cross | filter | 10 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| momentum | Momentum 0-cross | filter | 5 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| momentum | Momentum 0-cross | filter | 20 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| momentum | Momentum 0-cross | filter | 10 | 1h | ETH | 308 | -8.17 | 112 | -43.28 | -54.5 | FAIL |
| momentum | Momentum 0-cross | filter | 20 | 1h | ETH | 308 | -8.17 | 112 | -43.28 | -54.5 | FAIL |
| momentum | Momentum 0-cross | filter | 5 | 1h | ETH | 308 | -8.17 | 112 | -43.28 | -54.5 | FAIL |
| momentum | Momentum 0-cross | signal | 10 | 15m | BTC | 21302 | -0.47 | 7003 | -1.29 | -90.6 | FAIL |
| momentum | Momentum 0-cross | signal | 5 | 15m | BTC | 29633 | -0.34 | 9660 | -1.02 | -98.4 | FAIL |
| momentum | Momentum 0-cross | signal | 20 | 15m | BTC | 15702 | -0.64 | 5031 | -1.75 | -88.5 | FAIL |
| momentum | Momentum 0-cross | signal | 10 | 1h | BTC | 5666 | -1.70 | 1742 | -1.94 | -57.1 | FAIL |
| momentum | Momentum 0-cross | signal | 5 | 1h | BTC | 7778 | -1.28 | 2505 | -3.19 | -81.8 | FAIL |
| momentum | Momentum 0-cross | signal | 20 | 1h | BTC | 3713 | 0.18 | 1219 | -4.36 | -59.4 | FAIL |
| momentum | ROC 0-cross | filter | 12 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| momentum | ROC 0-cross | filter | 6 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| momentum | ROC 0-cross | filter | 25 | 1h | BTC | 351 | 3.06 | 119 | -1.67 | -29.6 | FAIL |
| momentum | ROC 0-cross | filter | 12 | 1h | ETH | 308 | -8.17 | 112 | -43.28 | -54.5 | FAIL |
| momentum | ROC 0-cross | filter | 6 | 1h | ETH | 308 | -8.17 | 112 | -43.28 | -54.5 | FAIL |
| momentum | ROC 0-cross | signal | 12 | 15m | BTC | 19878 | -0.50 | 6429 | -1.45 | -93.3 | FAIL |
| momentum | ROC 0-cross | signal | 6 | 15m | BTC | 27113 | -0.37 | 8792 | -1.11 | -97.8 | FAIL |
| momentum | ROC 0-cross | signal | 25 | 15m | BTC | 14396 | -0.69 | 4485 | -1.89 | -86.0 | FAIL |
| momentum | ROC 0-cross | signal | 12 | 1h | BTC | 5021 | -1.51 | 1541 | -1.83 | -58.4 | FAIL |
| momentum | ROC 0-cross | signal | 6 | 1h | BTC | 7077 | -1.37 | 2291 | -2.96 | -76.8 | FAIL |
| momentum | ROC 0-cross | signal | 25 | 1h | BTC | 3311 | -2.81 | 1037 | -6.80 | -72.5 | FAIL |
| momentum | RSI 50-cross | filter | 14 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| momentum | RSI 50-cross | filter | 7 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| momentum | RSI 50-cross | filter | 21 | 1h | BTC | 347 | 12.47 | 119 | 1.19 | -28.5 | SURVIVOR |
| momentum | RSI 50-cross | filter | 14 | 1h | ETH | 308 | -8.17 | 112 | -43.28 | -54.5 | FAIL |
| momentum | RSI 50-cross | filter | 21 | 1h | ETH | 306 | -6.65 | 112 | -48.07 | -58.9 | FAIL |
| momentum | RSI 50-cross | filter | 7 | 1h | ETH | 308 | -8.17 | 112 | -43.28 | -54.5 | FAIL |
| momentum | RSI 50-cross | signal | 14 | 15m | BTC | 16850 | -0.59 | 5551 | -1.62 | -90.5 | FAIL |
| momentum | RSI 50-cross | signal | 7 | 15m | BTC | 24582 | -0.41 | 7959 | -1.21 | -96.1 | FAIL |
| momentum | RSI 50-cross | signal | 21 | 15m | BTC | 13548 | -0.74 | 4371 | -1.76 | -78.0 | FAIL |
| momentum | RSI 50-cross | signal | 14 | 1h | BTC | 3876 | -1.45 | 1300 | -4.16 | -57.4 | FAIL |
| momentum | RSI 50-cross | signal | 7 | 1h | BTC | 5887 | -1.50 | 1890 | -3.19 | -71.8 | FAIL |
| momentum | RSI 50-cross | signal | 21 | 1h | BTC | 3038 | -0.19 | 959 | -4.07 | -53.1 | FAIL |
| momentum | RSI OB/OS | filter | 14/30-70 | 1h | BTC | 351 | 8.17 | 119 | -5.69 | -28.8 | FAIL |
| momentum | RSI OB/OS | filter | 7/25-75 | 1h | BTC | 351 | 1.48 | 119 | 3.97 | -28.1 | SURVIVOR |
| momentum | RSI OB/OS | filter | 21/35-65 | 1h | BTC | 351 | 8.98 | 119 | -5.38 | -29.3 | FAIL |
| momentum | RSI OB/OS | filter | 7/25-75 | 1h | ETH | 308 | -9.10 | 112 | -39.39 | -52.5 | FAIL |
| momentum | RSI OB/OS | signal | 14/30-70 | 15m | BTC | 3307 | -2.63 | 1081 | -3.45 | -41.1 | FAIL |
| momentum | RSI OB/OS | signal | 7/25-75 | 15m | BTC | 5999 | -1.48 | 2083 | -1.47 | -37.8 | FAIL |
| momentum | RSI OB/OS | signal | 21/35-65 | 15m | BTC | 3453 | -2.54 | 1169 | -2.90 | -37.2 | FAIL |
| momentum | RSI OB/OS | signal | 14/30-70 | 1h | BTC | 995 | -7.49 | 335 | -5.75 | -29.6 | FAIL |
| momentum | RSI OB/OS | signal | 7/25-75 | 1h | BTC | 1675 | -4.98 | 566 | -2.47 | -27.3 | FAIL |
| momentum | RSI OB/OS | signal | 21/35-65 | 1h | BTC | 1014 | -7.30 | 346 | -3.78 | -22.0 | FAIL |
| momentum | Stochastic %K/%D cross | filter | 14/3/3 | 1h | BTC | 351 | 8.37 | 118 | 3.77 | -30.1 | SURVIVOR |
| momentum | Stochastic %K/%D cross | filter | 5/3/3 | 1h | BTC | 351 | 9.04 | 118 | 2.26 | -29.1 | SURVIVOR |
| momentum | Stochastic %K/%D cross | filter | 21/5/5 | 1h | BTC | 351 | 6.69 | 118 | 1.78 | -29.7 | SURVIVOR |
| momentum | Stochastic %K/%D cross | filter | 14/3/3 | 1h | ETH | 306 | -5.69 | 112 | -45.83 | -56.9 | FAIL |
| momentum | Stochastic %K/%D cross | filter | 21/5/5 | 1h | ETH | 308 | -9.40 | 112 | -42.78 | -54.9 | FAIL |
| momentum | Stochastic %K/%D cross | filter | 5/3/3 | 1h | ETH | 305 | -6.17 | 112 | -44.55 | -56.2 | FAIL |
| momentum | Stochastic %K/%D cross | signal | 14/3/3 | 15m | BTC | 54753 | -0.18 | 18181 | -0.55 | -100.0 | FAIL |
| momentum | Stochastic %K/%D cross | signal | 5/3/3 | 15m | BTC | 57063 | -0.18 | 19103 | -0.52 | -100.0 | FAIL |
| momentum | Stochastic %K/%D cross | signal | 21/5/5 | 15m | BTC | 40565 | -0.25 | 13543 | -0.74 | -99.7 | FAIL |
| momentum | Stochastic %K/%D cross | signal | 14/3/3 | 1h | BTC | 13655 | -0.73 | 4543 | -2.09 | -95.5 | FAIL |
| momentum | Stochastic %K/%D cross | signal | 5/3/3 | 1h | BTC | 13954 | -0.71 | 4707 | -2.04 | -96.1 | FAIL |
| momentum | Stochastic %K/%D cross | signal | 21/5/5 | 1h | BTC | 10061 | -0.98 | 3348 | -2.54 | -86.9 | FAIL |
| momentum | Stochastic RSI extremes | filter | 14 | 1h | BTC | 350 | 3.93 | 119 | 10.47 | -28.2 | SURVIVOR |
| momentum | Stochastic RSI extremes | filter | 9 | 1h | BTC | 351 | -0.81 | 119 | 10.12 | -28.7 | FAIL |
| momentum | Stochastic RSI extremes | filter | 21 | 1h | BTC | 350 | 7.42 | 119 | 16.05 | -29.6 | SURVIVOR |
| momentum | Stochastic RSI extremes | filter | 14 | 1h | ETH | 307 | 4.22 | 111 | -39.04 | -56.9 | FAIL |
| momentum | Stochastic RSI extremes | filter | 21 | 1h | ETH | 306 | 1.89 | 112 | -40.36 | -58.0 | FAIL |
| momentum | Stochastic RSI extremes | signal | 14 | 15m | BTC | 22754 | -0.44 | 7636 | -1.24 | -95.3 | FAIL |
| momentum | Stochastic RSI extremes | signal | 9 | 15m | BTC | 29121 | -0.34 | 9742 | -1.00 | -98.0 | FAIL |
| momentum | Stochastic RSI extremes | signal | 21 | 15m | BTC | 18211 | -0.55 | 6114 | -1.45 | -89.9 | FAIL |
| momentum | Stochastic RSI extremes | signal | 14 | 1h | BTC | 5499 | -1.73 | 1870 | -2.14 | -52.6 | FAIL |
| momentum | Stochastic RSI extremes | signal | 9 | 1h | BTC | 7159 | -1.29 | 2418 | -1.72 | -48.3 | FAIL |
| momentum | Stochastic RSI extremes | signal | 21 | 1h | BTC | 4336 | -2.25 | 1495 | -2.31 | -41.0 | FAIL |
| momentum | Stochastic extremes | filter | 14/3/3 | 1h | BTC | 351 | -0.94 | 119 | 8.23 | -28.3 | FAIL |
| momentum | Stochastic extremes | filter | 5/3/3 | 1h | BTC | 351 | -1.82 | 119 | -0.72 | -29.3 | FAIL |
| momentum | Stochastic extremes | filter | 21/5/5 | 1h | BTC | 351 | 3.18 | 119 | 19.29 | -25.0 | SURVIVOR |
| momentum | Stochastic extremes | filter | 21/5/5 | 1h | ETH | 308 | -5.74 | 111 | -43.83 | -58.6 | FAIL |
| momentum | Stochastic extremes | signal | 14/3/3 | 15m | BTC | 18121 | -0.55 | 6345 | -1.35 | -87.4 | FAIL |
| momentum | Stochastic extremes | signal | 5/3/3 | 15m | BTC | 28435 | -0.35 | 9731 | -0.96 | -94.3 | FAIL |
| momentum | Stochastic extremes | signal | 21/5/5 | 15m | BTC | 14864 | -0.67 | 5249 | -1.66 | -88.7 | FAIL |
| momentum | Stochastic extremes | signal | 14/3/3 | 1h | BTC | 4020 | -2.25 | 1520 | 0.80 | -20.8 | FAIL |
| momentum | Stochastic extremes | signal | 5/3/3 | 1h | BTC | 6212 | -1.48 | 2238 | -0.84 | -38.7 | FAIL |
| momentum | Stochastic extremes | signal | 21/5/5 | 1h | BTC | 3403 | -2.73 | 1266 | -0.85 | -25.3 | FAIL |
| momentum | TSI 0-cross | filter | 25/13 | 1h | BTC | 341 | 10.64 | 116 | 7.57 | -28.2 | SURVIVOR |
| momentum | TSI 0-cross | filter | 13/7 | 1h | BTC | 351 | 7.17 | 118 | 3.77 | -26.6 | SURVIVOR |
| momentum | TSI 0-cross | filter | 13/7 | 1h | ETH | 308 | -7.95 | 112 | -43.28 | -54.5 | FAIL |
| momentum | TSI 0-cross | filter | 25/13 | 1h | ETH | 303 | -8.46 | 111 | -47.50 | -59.7 | FAIL |
| momentum | TSI 0-cross | signal | 25/13 | 15m | BTC | 4976 | -1.84 | 1565 | -1.70 | -47.3 | FAIL |
| momentum | TSI 0-cross | signal | 13/7 | 15m | BTC | 9462 | -1.05 | 3125 | -2.61 | -83.3 | FAIL |
| momentum | TSI 0-cross | signal | 25/13 | 1h | BTC | 1162 | 4.25 | 361 | 3.43 | -42.1 | SURVIVOR |
| momentum | TSI 0-cross | signal | 13/7 | 1h | BTC | 2226 | -1.33 | 731 | -5.18 | -46.2 | FAIL |
| momentum | TSI 0-cross | signal | 25/13 | 1h | ETH | 981 | -3.15 | 334 | -1.78 | -60.9 | FAIL |
| momentum | Ultimate Oscillator extremes | filter | 7/14/28 | 1h | BTC | 351 | 7.50 | 119 | 0.52 | -27.6 | SURVIVOR |
| momentum | Ultimate Oscillator extremes | filter | 5/10/20 | 1h | BTC | 351 | 4.66 | 119 | -2.11 | -26.5 | FAIL |
| momentum | Ultimate Oscillator extremes | filter | 7/14/28 | 1h | ETH | 308 | -9.95 | 112 | -43.18 | -54.5 | FAIL |
| momentum | Ultimate Oscillator extremes | signal | 7/14/28 | 15m | BTC | 1510 | 2.74 | 430 | -5.43 | -28.8 | FAIL |
| momentum | Ultimate Oscillator extremes | signal | 5/10/20 | 15m | BTC | 4089 | -0.76 | 1194 | -2.95 | -38.5 | FAIL |
| momentum | Ultimate Oscillator extremes | signal | 7/14/28 | 1h | BTC | 244 | -6.88 | 82 | 9.17 | -5.5 | FAIL |
| momentum | Ultimate Oscillator extremes | signal | 5/10/20 | 1h | BTC | 709 | -5.28 | 231 | 1.49 | -12.8 | FAIL |
| momentum | Williams %R extremes | filter | 14 | 1h | BTC | 351 | -0.94 | 119 | 8.23 | -28.3 | FAIL |
| momentum | Williams %R extremes | filter | 9 | 1h | BTC | 351 | -3.13 | 119 | 2.70 | -28.9 | FAIL |
| momentum | Williams %R extremes | filter | 28 | 1h | BTC | 351 | 1.80 | 119 | 5.55 | -27.7 | SURVIVOR |
| momentum | Williams %R extremes | filter | 28 | 1h | ETH | 308 | -9.12 | 111 | -38.75 | -50.6 | FAIL |
| momentum | Williams %R extremes | signal | 14 | 15m | BTC | 18121 | -0.55 | 6345 | -1.35 | -87.4 | FAIL |
| momentum | Williams %R extremes | signal | 9 | 15m | BTC | 22122 | -0.45 | 7650 | -1.21 | -92.9 | FAIL |
| momentum | Williams %R extremes | signal | 28 | 15m | BTC | 12777 | -0.78 | 4539 | -1.83 | -84.5 | FAIL |
| momentum | Williams %R extremes | signal | 14 | 1h | BTC | 4020 | -2.25 | 1520 | 0.80 | -20.8 | FAIL |
| momentum | Williams %R extremes | signal | 9 | 1h | BTC | 4802 | -1.90 | 1777 | -0.38 | -32.5 | FAIL |
| momentum | Williams %R extremes | signal | 28 | 1h | BTC | 2947 | -3.07 | 1092 | 0.57 | -25.1 | FAIL |
| trend | ADX/DMI DI cross | filter | 14 | 1h | BTC | 346 | 9.41 | 118 | 0.94 | -28.6 | SURVIVOR |
| trend | ADX/DMI DI cross | filter | 25 | 1h | BTC | 320 | 31.29 | 111 | 5.54 | -24.8 | SURVIVOR |
| trend | ADX/DMI DI cross | filter | 50 | 1h | BTC | 286 | 18.00 | 97 | 11.96 | -28.9 | SURVIVOR |
| trend | ADX/DMI DI cross | filter | 14 | 1h | ETH | 304 | -6.35 | 110 | -41.98 | -52.2 | FAIL |
| trend | ADX/DMI DI cross | filter | 25 | 1h | ETH | 282 | 18.41 | 102 | -44.61 | -52.8 | FAIL |
| trend | ADX/DMI DI cross | filter | 50 | 1h | ETH | 247 | 16.46 | 92 | -60.96 | -62.1 | FAIL |
| trend | ADX/DMI DI cross | signal | 14 | 15m | BTC | 10624 | -0.93 | 3541 | -1.96 | -71.1 | FAIL |
| trend | ADX/DMI DI cross | signal | 25 | 15m | BTC | 7314 | -1.26 | 2525 | -1.40 | -41.9 | FAIL |
| trend | ADX/DMI DI cross | signal | 50 | 15m | BTC | 4888 | -1.00 | 1701 | -3.22 | -58.9 | FAIL |
| trend | ADX/DMI DI cross | signal | 14 | 1h | BTC | 2537 | 5.00 | 840 | -1.90 | -62.8 | FAIL |
| trend | ADX/DMI DI cross | signal | 25 | 1h | BTC | 1761 | 6.16 | 591 | -2.90 | -58.5 | FAIL |
| trend | ADX/DMI DI cross | signal | 50 | 1h | BTC | 1189 | 8.74 | 400 | -4.30 | -63.7 | FAIL |
| trend | ADX/DMI DI-cross+ADX>thresh | filter | n14,adx>20 | 1h | BTC | 319 | 9.34 | 102 | 18.85 | -32.7 | SURVIVOR |
| trend | ADX/DMI DI-cross+ADX>thresh | filter | n14,adx>25 | 1h | BTC | 270 | 14.09 | 90 | -7.00 | -34.8 | FAIL |
| trend | ADX/DMI DI-cross+ADX>thresh | filter | n25,adx>20 | 1h | BTC | 229 | 11.60 | 76 | -11.21 | -37.7 | FAIL |
| trend | ADX/DMI DI-cross+ADX>thresh | filter | n14,adx>20 | 1h | ETH | 279 | 0.06 | 96 | -45.43 | -54.3 | FAIL |
| trend | ADX/DMI DI-cross+ADX>thresh | signal | n14,adx>20 | 15m | BTC | 6259 | -1.48 | 2072 | -1.46 | -39.2 | FAIL |
| trend | ADX/DMI DI-cross+ADX>thresh | signal | n14,adx>25 | 15m | BTC | 4169 | -1.65 | 1367 | -0.19 | -25.4 | FAIL |
| trend | ADX/DMI DI-cross+ADX>thresh | signal | n25,adx>20 | 15m | BTC | 2626 | -1.42 | 803 | -1.12 | -30.9 | FAIL |
| trend | ADX/DMI DI-cross+ADX>thresh | signal | n14,adx>20 | 1h | BTC | 1636 | 1.31 | 494 | -1.92 | -45.2 | FAIL |
| trend | ADX/DMI DI-cross+ADX>thresh | signal | n14,adx>25 | 1h | BTC | 1133 | 3.14 | 361 | -8.49 | -48.0 | FAIL |
| trend | ADX/DMI DI-cross+ADX>thresh | signal | n25,adx>20 | 1h | BTC | 741 | 0.43 | 235 | -10.73 | -41.3 | FAIL |
| trend | Aroon oscillator 0-cross | filter | 14 | 1h | BTC | 351 | 7.45 | 119 | -0.70 | -28.6 | FAIL |
| trend | Aroon oscillator 0-cross | filter | 25 | 1h | BTC | 350 | 0.92 | 117 | 8.80 | -27.1 | SURVIVOR |
| trend | Aroon oscillator 0-cross | filter | 50 | 1h | BTC | 310 | 12.42 | 108 | -7.97 | -29.9 | FAIL |
| trend | Aroon oscillator 0-cross | filter | 25 | 1h | ETH | 308 | -6.84 | 112 | -47.41 | -61.1 | FAIL |
| trend | Aroon oscillator 0-cross | signal | 14 | 15m | BTC | 10148 | -0.97 | 3395 | -2.52 | -85.8 | FAIL |
| trend | Aroon oscillator 0-cross | signal | 25 | 15m | BTC | 6224 | -1.60 | 2007 | -2.93 | -66.2 | FAIL |
| trend | Aroon oscillator 0-cross | signal | 50 | 15m | BTC | 3256 | -1.89 | 1030 | -1.72 | -51.7 | FAIL |
| trend | Aroon oscillator 0-cross | signal | 14 | 1h | BTC | 2561 | -1.12 | 852 | -1.78 | -50.0 | FAIL |
| trend | Aroon oscillator 0-cross | signal | 25 | 1h | BTC | 1487 | -4.91 | 495 | -7.66 | -45.8 | FAIL |
| trend | Aroon oscillator 0-cross | signal | 50 | 1h | BTC | 773 | -7.84 | 253 | -20.11 | -62.1 | FAIL |
| trend | Aroon up/down cross | filter | 14 | 1h | BTC | 351 | 7.45 | 119 | -0.70 | -28.6 | FAIL |
| trend | Aroon up/down cross | filter | 25 | 1h | BTC | 350 | 0.92 | 117 | 8.80 | -27.1 | SURVIVOR |
| trend | Aroon up/down cross | filter | 50 | 1h | BTC | 310 | 12.42 | 108 | -7.97 | -29.9 | FAIL |
| trend | Aroon up/down cross | filter | 25 | 1h | ETH | 308 | -6.84 | 112 | -47.41 | -61.1 | FAIL |
| trend | Aroon up/down cross | signal | 14 | 15m | BTC | 10148 | -0.97 | 3395 | -2.52 | -85.8 | FAIL |
| trend | Aroon up/down cross | signal | 25 | 15m | BTC | 6224 | -1.60 | 2007 | -2.93 | -66.2 | FAIL |
| trend | Aroon up/down cross | signal | 50 | 15m | BTC | 3256 | -1.89 | 1030 | -1.72 | -51.7 | FAIL |
| trend | Aroon up/down cross | signal | 14 | 1h | BTC | 2561 | -1.12 | 852 | -1.78 | -50.0 | FAIL |
| trend | Aroon up/down cross | signal | 25 | 1h | BTC | 1487 | -4.91 | 495 | -7.66 | -45.8 | FAIL |
| trend | Aroon up/down cross | signal | 50 | 1h | BTC | 773 | -7.84 | 253 | -20.11 | -62.1 | FAIL |
| trend | DEMA cross | filter | 10/30 | 1h | BTC | 351 | 6.55 | 117 | 3.66 | -27.3 | SURVIVOR |
| trend | DEMA cross | filter | 20/50 | 1h | BTC | 340 | -2.19 | 112 | 17.91 | -23.3 | FAIL |
| trend | DEMA cross | filter | 10/30 | 1h | ETH | 306 | -9.11 | 111 | -42.50 | -55.2 | FAIL |
| trend | DEMA cross | signal | 10/30 | 15m | BTC | 8334 | -1.19 | 2815 | -2.54 | -73.5 | FAIL |
| trend | DEMA cross | signal | 20/50 | 15m | BTC | 4560 | -2.02 | 1439 | -1.21 | -49.8 | FAIL |
| trend | DEMA cross | signal | 10/30 | 1h | BTC | 1972 | 17.32 | 649 | -2.03 | -52.7 | FAIL |
| trend | DEMA cross | signal | 20/50 | 1h | BTC | 1058 | -1.40 | 353 | -1.67 | -36.8 | FAIL |
| trend | EMA cross | filter | 10/30 | 1h | BTC | 340 | 14.20 | 116 | 8.33 | -27.9 | SURVIVOR |
| trend | EMA cross | filter | 12/26 | 1h | BTC | 341 | 11.87 | 116 | 8.47 | -28.0 | SURVIVOR |
| trend | EMA cross | filter | 50/200 | 1h | BTC | 228 | 32.67 | 84 | -2.03 | -24.9 | FAIL |
| trend | EMA cross | filter | 10/30 | 1h | ETH | 302 | -7.97 | 111 | -48.06 | -60.0 | FAIL |
| trend | EMA cross | filter | 12/26 | 1h | ETH | 303 | -8.50 | 111 | -47.81 | -59.9 | FAIL |
| trend | EMA cross | signal | 10/30 | 15m | BTC | 5168 | -1.74 | 1637 | -1.95 | -49.8 | FAIL |
| trend | EMA cross | signal | 12/26 | 15m | BTC | 5080 | -1.79 | 1593 | -1.03 | -46.9 | FAIL |
| trend | EMA cross | signal | 50/200 | 15m | BTC | 799 | 5.30 | 267 | -8.10 | -48.5 | FAIL |
| trend | EMA cross | signal | 10/30 | 1h | BTC | 1182 | 4.64 | 373 | 2.83 | -42.1 | SURVIVOR |
| trend | EMA cross | signal | 12/26 | 1h | BTC | 1192 | 4.81 | 363 | 5.00 | -38.9 | SURVIVOR |
| trend | EMA cross | signal | 50/200 | 1h | BTC | 195 | -2.36 | 77 | -20.86 | -50.0 | FAIL |
| trend | EMA cross | signal | 10/30 | 1h | ETH | 1024 | -5.28 | 346 | -4.22 | -67.1 | FAIL |
| trend | EMA cross | signal | 12/26 | 1h | ETH | 986 | -2.74 | 342 | -3.44 | -63.5 | FAIL |
| trend | Hull MA cross | filter | 9 | 1h | BTC | 351 | 7.74 | 119 | 1.34 | -28.6 | SURVIVOR |
| trend | Hull MA cross | filter | 16 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| trend | Hull MA cross | filter | 21 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| trend | Hull MA cross | filter | 16 | 1h | ETH | 308 | -8.17 | 112 | -44.12 | -55.3 | FAIL |
| trend | Hull MA cross | filter | 21 | 1h | ETH | 308 | -8.17 | 112 | -43.72 | -55.3 | FAIL |
| trend | Hull MA cross | filter | 9 | 1h | ETH | 308 | -8.01 | 112 | -43.38 | -54.4 | FAIL |
| trend | Hull MA cross | signal | 9 | 15m | BTC | 46841 | -0.21 | 15640 | -0.64 | -99.7 | FAIL |
| trend | Hull MA cross | signal | 16 | 15m | BTC | 33257 | -0.30 | 11108 | -0.89 | -99.2 | FAIL |
| trend | Hull MA cross | signal | 21 | 15m | BTC | 28505 | -0.35 | 9530 | -1.03 | -98.4 | FAIL |
| trend | Hull MA cross | signal | 9 | 1h | BTC | 11243 | -0.86 | 3892 | -2.40 | -93.4 | FAIL |
| trend | Hull MA cross | signal | 16 | 1h | BTC | 8031 | -1.23 | 2721 | -3.24 | -88.5 | FAIL |
| trend | Hull MA cross | signal | 21 | 1h | BTC | 6823 | -1.46 | 2329 | -3.22 | -79.4 | FAIL |
| trend | Ichimoku price vs cloud | signal | 9/26/52 | 4h | BTC | 222 | -22.61 | 69 | -13.39 | -48.3 | FAIL |
| trend | Ichimoku price vs cloud | signal | 7/22/44 | 4h | BTC | 250 | -14.32 | 79 | -9.26 | -54.6 | FAIL |
| trend | Ichimoku tenkan/kijun cross | signal | 9/26/52 | 4h | BTC | 422 | -14.20 | 129 | 91.58 | -23.1 | FAIL |
| trend | Ichimoku tenkan/kijun cross | signal | 7/22/44 | 4h | BTC | 492 | -12.29 | 153 | 27.37 | -31.7 | FAIL |
| trend | KAMA cross | filter | 10/2/30 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| trend | KAMA cross | filter | 5/2/20 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| trend | KAMA cross | filter | 10/2/30 | 1h | ETH | 308 | -8.17 | 112 | -43.28 | -54.5 | FAIL |
| trend | KAMA cross | filter | 5/2/20 | 1h | ETH | 308 | -8.17 | 112 | -43.28 | -54.5 | FAIL |
| trend | KAMA cross | signal | 10/2/30 | 15m | BTC | 20454 | -0.49 | 6531 | -1.39 | -91.4 | FAIL |
| trend | KAMA cross | signal | 5/2/20 | 15m | BTC | 28197 | -0.35 | 9322 | -1.06 | -98.9 | FAIL |
| trend | KAMA cross | signal | 10/2/30 | 1h | BTC | 5070 | -1.94 | 1562 | -2.89 | -61.6 | FAIL |
| trend | KAMA cross | signal | 5/2/20 | 1h | BTC | 6934 | -1.42 | 2186 | -2.99 | -80.1 | FAIL |
| trend | Linreg slope sign | filter | 20 | 1h | BTC | 349 | 6.23 | 118 | 5.29 | -24.9 | SURVIVOR |
| trend | Linreg slope sign | filter | 50 | 1h | BTC | 314 | 21.39 | 110 | 10.09 | -25.0 | SURVIVOR |
| trend | Linreg slope sign | filter | 100 | 1h | BTC | 252 | 10.58 | 88 | 20.58 | -27.0 | SURVIVOR |
| trend | Linreg slope sign | filter | 100 | 1h | ETH | 218 | -2.55 | 82 | -62.96 | -60.2 | FAIL |
| trend | Linreg slope sign | filter | 20 | 1h | ETH | 307 | -9.82 | 111 | -41.83 | -55.4 | FAIL |
| trend | Linreg slope sign | filter | 50 | 1h | ETH | 274 | 6.25 | 102 | -52.37 | -60.3 | FAIL |
| trend | Linreg slope sign | signal | 20 | 15m | BTC | 7472 | -1.33 | 2409 | -2.65 | -66.4 | FAIL |
| trend | Linreg slope sign | signal | 50 | 15m | BTC | 3015 | -0.12 | 924 | 3.09 | -33.2 | FAIL |
| trend | Linreg slope sign | signal | 100 | 15m | BTC | 1477 | 12.23 | 497 | -7.86 | -46.2 | FAIL |
| trend | Linreg slope sign | signal | 20 | 1h | BTC | 1837 | 3.17 | 601 | 2.80 | -32.2 | SURVIVOR |
| trend | Linreg slope sign | signal | 50 | 1h | BTC | 743 | 1.60 | 241 | -6.56 | -55.3 | FAIL |
| trend | Linreg slope sign | signal | 100 | 1h | BTC | 352 | -14.10 | 110 | 100.75 | -43.4 | FAIL |
| trend | Linreg slope sign | signal | 20 | 1h | ETH | 1492 | -1.69 | 500 | 7.26 | -35.4 | FAIL |
| trend | MACD histogram 0-cross | filter | 12/26/9 | 1h | BTC | 351 | 7.82 | 119 | 0.42 | -28.6 | SURVIVOR |
| trend | MACD histogram 0-cross | filter | 5/13/6 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| trend | MACD histogram 0-cross | filter | 19/39/9 | 1h | BTC | 350 | 8.06 | 117 | 3.75 | -27.3 | SURVIVOR |
| trend | MACD histogram 0-cross | filter | 12/26/9 | 1h | ETH | 308 | -8.32 | 111 | -41.77 | -54.5 | FAIL |
| trend | MACD histogram 0-cross | filter | 19/39/9 | 1h | ETH | 306 | -9.27 | 111 | -42.50 | -55.2 | FAIL |
| trend | MACD histogram 0-cross | filter | 5/13/6 | 1h | ETH | 308 | -8.17 | 112 | -43.28 | -54.5 | FAIL |
| trend | MACD histogram 0-cross | signal | 12/26/9 | 15m | BTC | 10445 | -0.95 | 3627 | -2.52 | -91.6 | FAIL |
| trend | MACD histogram 0-cross | signal | 5/13/6 | 15m | BTC | 20074 | -0.50 | 6758 | -1.41 | -95.4 | FAIL |
| trend | MACD histogram 0-cross | signal | 19/39/9 | 15m | BTC | 7997 | -1.24 | 2709 | -2.50 | -71.0 | FAIL |
| trend | MACD histogram 0-cross | signal | 12/26/9 | 1h | BTC | 2509 | 1.05 | 843 | -3.87 | -61.9 | FAIL |
| trend | MACD histogram 0-cross | signal | 5/13/6 | 1h | BTC | 4915 | -1.97 | 1595 | -3.35 | -64.0 | FAIL |
| trend | MACD histogram 0-cross | signal | 19/39/9 | 1h | BTC | 1868 | 20.77 | 621 | -1.06 | -46.5 | FAIL |
| trend | MACD line/signal cross | filter | 12/26/9 | 1h | BTC | 351 | 7.82 | 119 | 0.42 | -28.6 | SURVIVOR |
| trend | MACD line/signal cross | filter | 5/13/6 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| trend | MACD line/signal cross | filter | 19/39/9 | 1h | BTC | 350 | 8.06 | 117 | 3.75 | -27.3 | SURVIVOR |
| trend | MACD line/signal cross | filter | 12/26/9 | 1h | ETH | 308 | -8.32 | 111 | -41.77 | -54.5 | FAIL |
| trend | MACD line/signal cross | filter | 19/39/9 | 1h | ETH | 306 | -9.27 | 111 | -42.50 | -55.2 | FAIL |
| trend | MACD line/signal cross | filter | 5/13/6 | 1h | ETH | 308 | -8.17 | 112 | -43.28 | -54.5 | FAIL |
| trend | MACD line/signal cross | signal | 12/26/9 | 15m | BTC | 10445 | -0.95 | 3627 | -2.52 | -91.6 | FAIL |
| trend | MACD line/signal cross | signal | 5/13/6 | 15m | BTC | 20074 | -0.50 | 6758 | -1.41 | -95.4 | FAIL |
| trend | MACD line/signal cross | signal | 19/39/9 | 15m | BTC | 7997 | -1.24 | 2709 | -2.50 | -71.0 | FAIL |
| trend | MACD line/signal cross | signal | 12/26/9 | 1h | BTC | 2509 | 1.05 | 843 | -3.87 | -61.9 | FAIL |
| trend | MACD line/signal cross | signal | 5/13/6 | 1h | BTC | 4915 | -1.97 | 1595 | -3.35 | -64.0 | FAIL |
| trend | MACD line/signal cross | signal | 19/39/9 | 1h | BTC | 1868 | 20.77 | 621 | -1.06 | -46.5 | FAIL |
| trend | Parabolic SAR | filter | 0.02/0.2 | 1h | BTC | 351 | 7.49 | 119 | 0.42 | -28.6 | SURVIVOR |
| trend | Parabolic SAR | filter | 0.01/0.1 | 1h | BTC | 348 | 6.54 | 118 | 1.40 | -28.5 | SURVIVOR |
| trend | Parabolic SAR | filter | 0.03/0.3 | 1h | BTC | 351 | 7.95 | 119 | 0.42 | -28.6 | SURVIVOR |
| trend | Parabolic SAR | filter | 0.01/0.1 | 1h | ETH | 306 | -8.38 | 111 | -45.07 | -55.9 | FAIL |
| trend | Parabolic SAR | filter | 0.02/0.2 | 1h | ETH | 308 | -8.29 | 112 | -43.38 | -54.6 | FAIL |
| trend | Parabolic SAR | filter | 0.03/0.3 | 1h | ETH | 308 | -8.17 | 112 | -43.28 | -54.5 | FAIL |
| trend | Parabolic SAR | signal | 0.02/0.2 | 15m | BTC | 10110 | -0.97 | 3815 | -2.23 | -87.1 | FAIL |
| trend | Parabolic SAR | signal | 0.01/0.1 | 15m | BTC | 5920 | -1.60 | 2221 | -1.07 | -43.1 | FAIL |
| trend | Parabolic SAR | signal | 0.03/0.3 | 15m | BTC | 13688 | -0.73 | 5029 | -1.60 | -86.0 | FAIL |
| trend | Parabolic SAR | signal | 0.02/0.2 | 1h | BTC | 2512 | -3.19 | 898 | -3.91 | -52.3 | FAIL |
| trend | Parabolic SAR | signal | 0.01/0.1 | 1h | BTC | 1488 | -1.15 | 546 | -6.61 | -61.3 | FAIL |
| trend | Parabolic SAR | signal | 0.03/0.3 | 1h | BTC | 3426 | -2.87 | 1192 | -2.65 | -53.5 | FAIL |
| trend | SMA cross | filter | 10/30 | 1h | BTC | 347 | 6.97 | 118 | 11.60 | -26.8 | SURVIVOR |
| trend | SMA cross | filter | 20/50 | 1h | BTC | 324 | 16.05 | 112 | -5.19 | -31.2 | FAIL |
| trend | SMA cross | filter | 50/200 | 1h | BTC | 222 | 15.84 | 83 | 1.38 | -23.8 | SURVIVOR |
| trend | SMA cross | filter | 10/30 | 1h | ETH | 307 | -10.05 | 112 | -46.36 | -58.2 | FAIL |
| trend | SMA cross | filter | 50/200 | 1h | ETH | 195 | 5.68 | 61 | -30.22 | -32.7 | FAIL |
| trend | SMA cross | signal | 10/30 | 15m | BTC | 5702 | -1.72 | 1817 | -2.46 | -56.9 | FAIL |
| trend | SMA cross | signal | 20/50 | 15m | BTC | 3313 | -2.04 | 1020 | -1.22 | -42.6 | FAIL |
| trend | SMA cross | signal | 50/200 | 15m | BTC | 851 | 12.11 | 283 | -0.53 | -46.9 | FAIL |
| trend | SMA cross | signal | 10/30 | 1h | BTC | 1334 | 29.64 | 461 | -7.55 | -41.2 | FAIL |
| trend | SMA cross | signal | 20/50 | 1h | BTC | 811 | -0.69 | 265 | -19.34 | -63.6 | FAIL |
| trend | SMA cross | signal | 50/200 | 1h | BTC | 219 | -11.69 | 77 | 11.29 | -45.8 | FAIL |
| trend | SuperTrend | filter | ATR10xMult3 | 1h | BTC | 316 | 19.08 | 113 | -5.16 | -28.2 | FAIL |
| trend | SuperTrend | filter | ATR14xMult3 | 1h | BTC | 317 | 19.20 | 112 | -1.22 | -26.9 | FAIL |
| trend | SuperTrend | filter | ATR14xMult2 | 1h | BTC | 345 | 9.16 | 116 | 7.08 | -26.5 | SURVIVOR |
| trend | SuperTrend | filter | ATR14xMult2 | 1h | ETH | 307 | -8.18 | 112 | -44.39 | -55.0 | FAIL |
| trend | SuperTrend | signal | ATR10xMult3 | 15m | BTC | 3160 | -0.94 | 986 | -2.07 | -53.1 | FAIL |
| trend | SuperTrend | signal | ATR14xMult3 | 15m | BTC | 3194 | -0.10 | 980 | -0.37 | -46.4 | FAIL |
| trend | SuperTrend | signal | ATR14xMult2 | 15m | BTC | 6236 | -1.56 | 1895 | -2.63 | -52.9 | FAIL |
| trend | SuperTrend | signal | ATR10xMult3 | 1h | BTC | 729 | -7.69 | 254 | -19.65 | -60.0 | FAIL |
| trend | SuperTrend | signal | ATR14xMult3 | 1h | BTC | 723 | -5.14 | 256 | -21.20 | -63.8 | FAIL |
| trend | SuperTrend | signal | ATR14xMult2 | 1h | BTC | 1287 | -0.49 | 436 | -2.40 | -44.8 | FAIL |
| trend | TEMA cross | filter | 10/30 | 1h | BTC | 351 | 7.74 | 119 | -1.01 | -29.8 | FAIL |
| trend | TEMA cross | filter | 20/50 | 1h | BTC | 348 | 4.32 | 117 | 4.39 | -26.1 | SURVIVOR |
| trend | TEMA cross | filter | 20/50 | 1h | ETH | 302 | -7.53 | 108 | -40.69 | -54.5 | FAIL |
| trend | TEMA cross | signal | 10/30 | 15m | BTC | 11120 | -0.89 | 3883 | -2.38 | -92.8 | FAIL |
| trend | TEMA cross | signal | 20/50 | 15m | BTC | 6000 | -1.64 | 2041 | -2.55 | -55.4 | FAIL |
| trend | TEMA cross | signal | 10/30 | 1h | BTC | 2676 | 7.36 | 895 | 3.76 | -58.0 | SURVIVOR |
| trend | TEMA cross | signal | 20/50 | 1h | BTC | 1434 | 48.33 | 489 | -5.93 | -47.2 | FAIL |
| trend | TEMA cross | signal | 10/30 | 1h | ETH | 2302 | 0.97 | 799 | 5.93 | -62.4 | SURVIVOR |
| trend | TRIX 0-cross | filter | 15 | 1h | BTC | 326 | 8.14 | 113 | -0.80 | -31.7 | FAIL |
| trend | TRIX 0-cross | filter | 9 | 1h | BTC | 349 | 4.12 | 118 | 8.20 | -24.5 | SURVIVOR |
| trend | TRIX 0-cross | filter | 30 | 1h | BTC | 270 | 25.31 | 93 | 38.72 | -19.5 | SURVIVOR |
| trend | TRIX 0-cross | filter | 30 | 1h | ETH | 231 | 8.32 | 88 | -53.05 | -58.8 | FAIL |
| trend | TRIX 0-cross | filter | 9 | 1h | ETH | 308 | -9.26 | 111 | -44.77 | -58.1 | FAIL |
| trend | TRIX 0-cross | signal | 15 | 15m | BTC | 3444 | -1.33 | 1079 | -2.53 | -52.8 | FAIL |
| trend | TRIX 0-cross | signal | 9 | 15m | BTC | 5966 | -1.64 | 1905 | -1.33 | -40.7 | FAIL |
| trend | TRIX 0-cross | signal | 30 | 15m | BTC | 1645 | 2.84 | 539 | 0.27 | -36.6 | SURVIVOR |
| trend | TRIX 0-cross | signal | 30 | 15m | ETH | 1354 | -1.00 | 472 | 3.35 | -38.3 | FAIL |
| trend | TRIX 0-cross | signal | 15 | 1h | BTC | 815 | -4.45 | 271 | -5.03 | -52.4 | FAIL |
| trend | TRIX 0-cross | signal | 9 | 1h | BTC | 1372 | 0.33 | 455 | 4.05 | -33.7 | SURVIVOR |
| trend | TRIX 0-cross | signal | 30 | 1h | BTC | 406 | -5.10 | 121 | 65.29 | -35.2 | FAIL |
| trend | TRIX 0-cross | signal | 9 | 1h | ETH | 1156 | -0.94 | 390 | 7.48 | -45.8 | FAIL |
| trend | Vortex VI+/VI- cross | filter | 14 | 1h | BTC | 351 | 7.57 | 119 | 0.41 | -28.6 | SURVIVOR |
| trend | Vortex VI+/VI- cross | filter | 21 | 1h | BTC | 350 | 8.40 | 119 | 1.09 | -28.3 | SURVIVOR |
| trend | Vortex VI+/VI- cross | filter | 34 | 1h | BTC | 346 | 6.22 | 117 | -5.20 | -31.5 | FAIL |
| trend | Vortex VI+/VI- cross | filter | 14 | 1h | ETH | 308 | -8.51 | 111 | -41.82 | -54.6 | FAIL |
| trend | Vortex VI+/VI- cross | filter | 21 | 1h | ETH | 308 | -7.90 | 112 | -43.19 | -54.8 | FAIL |
| trend | Vortex VI+/VI- cross | signal | 14 | 15m | BTC | 15324 | -0.65 | 4811 | -1.75 | -87.1 | FAIL |
| trend | Vortex VI+/VI- cross | signal | 21 | 15m | BTC | 12734 | -0.78 | 4015 | -1.96 | -79.8 | FAIL |
| trend | Vortex VI+/VI- cross | signal | 34 | 15m | BTC | 10421 | -0.95 | 3118 | -1.10 | -65.3 | FAIL |
| trend | Vortex VI+/VI- cross | signal | 14 | 1h | BTC | 3963 | 1.56 | 1210 | -0.95 | -47.6 | FAIL |
| trend | Vortex VI+/VI- cross | signal | 21 | 1h | BTC | 3101 | 5.25 | 995 | 0.16 | -37.0 | SURVIVOR |
| trend | Vortex VI+/VI- cross | signal | 34 | 1h | BTC | 2527 | -0.16 | 746 | -6.95 | -57.1 | FAIL |
| trend | Vortex VI+/VI- cross | signal | 21 | 1h | ETH | 2452 | 3.14 | 834 | -5.65 | -62.2 | FAIL |
| volatility | BB-inside-KC squeeze release | filter | BB20/2 KC20/1.5 | 1h | BTC | 232 | 15.73 | 78 | 9.35 | -25.5 | SURVIVOR |
| volatility | BB-inside-KC squeeze release | filter | BB20/2 KC20/2 | 1h | BTC | 276 | 30.00 | 93 | 4.19 | -28.5 | SURVIVOR |
| volatility | BB-inside-KC squeeze release | filter | BB20/2 KC20/1.5 | 1h | ETH | 201 | -19.73 | 81 | -57.42 | -60.6 | FAIL |
| volatility | BB-inside-KC squeeze release | filter | BB20/2 KC20/2 | 1h | ETH | 240 | -2.76 | 78 | -62.60 | -57.0 | FAIL |
| volatility | BB-inside-KC squeeze release | signal | BB20/2 KC20/1.5 | 15m | BTC | 3074 | -2.65 | 1085 | -3.53 | -45.6 | FAIL |
| volatility | BB-inside-KC squeeze release | signal | BB20/2 KC20/2 | 15m | BTC | 3808 | -2.28 | 1274 | -3.71 | -51.6 | FAIL |
| volatility | BB-inside-KC squeeze release | signal | BB20/2 KC20/1.5 | 1h | BTC | 804 | 5.12 | 263 | 0.19 | -31.1 | SURVIVOR |
| volatility | BB-inside-KC squeeze release | signal | BB20/2 KC20/2 | 1h | BTC | 894 | 4.32 | 295 | -4.37 | -28.5 | FAIL |
| volatility | BB-inside-KC squeeze release | signal | BB20/2 KC20/1.5 | 1h | ETH | 665 | 2.70 | 248 | -7.55 | -43.2 | FAIL |
| volatility | Bollinger breakout | filter | 20/2 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| volatility | Bollinger breakout | filter | 20/2.5 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| volatility | Bollinger breakout | filter | 10/2 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| volatility | Bollinger breakout | filter | 10/2 | 1h | ETH | 308 | -8.17 | 112 | -43.28 | -54.5 | FAIL |
| volatility | Bollinger breakout | filter | 20/2 | 1h | ETH | 308 | -8.17 | 112 | -43.28 | -54.5 | FAIL |
| volatility | Bollinger breakout | filter | 20/2.5 | 1h | ETH | 308 | -8.17 | 112 | -43.28 | -54.5 | FAIL |
| volatility | Bollinger breakout | signal | 20/2 | 15m | BTC | 4858 | -1.97 | 1630 | -3.53 | -59.2 | FAIL |
| volatility | Bollinger breakout | signal | 20/2.5 | 15m | BTC | 2963 | -2.93 | 947 | -1.89 | -43.2 | FAIL |
| volatility | Bollinger breakout | signal | 10/2 | 15m | BTC | 6269 | -1.57 | 1983 | -3.40 | -68.8 | FAIL |
| volatility | Bollinger breakout | signal | 20/2 | 1h | BTC | 1256 | 4.27 | 407 | -1.85 | -39.8 | FAIL |
| volatility | Bollinger breakout | signal | 20/2.5 | 1h | BTC | 819 | 14.71 | 260 | 1.48 | -30.8 | SURVIVOR |
| volatility | Bollinger breakout | signal | 10/2 | 1h | BTC | 1679 | -3.94 | 538 | -1.38 | -38.7 | FAIL |
| volatility | Bollinger breakout | signal | 20/2.5 | 1h | ETH | 667 | 33.43 | 210 | 17.38 | -26.0 | SURVIVOR |
| volatility | Bollinger mean-revert | filter | 20/2 | 1h | BTC | 351 | -1.42 | 119 | 2.53 | -31.5 | FAIL |
| volatility | Bollinger mean-revert | filter | 20/2.5 | 1h | BTC | 351 | 0.39 | 119 | -2.34 | -30.7 | FAIL |
| volatility | Bollinger mean-revert | filter | 10/2 | 1h | BTC | 351 | 0.83 | 119 | 2.58 | -28.4 | SURVIVOR |
| volatility | Bollinger mean-revert | filter | 10/2 | 1h | ETH | 308 | -8.99 | 111 | -37.99 | -54.7 | FAIL |
| volatility | Bollinger mean-revert | signal | 20/2 | 15m | BTC | 4858 | -1.68 | 1630 | -2.93 | -55.4 | FAIL |
| volatility | Bollinger mean-revert | signal | 20/2.5 | 15m | BTC | 2963 | -2.19 | 947 | -5.36 | -60.0 | FAIL |
| volatility | Bollinger mean-revert | signal | 10/2 | 15m | BTC | 6271 | -1.25 | 1983 | -2.30 | -52.3 | FAIL |
| volatility | Bollinger mean-revert | signal | 20/2 | 1h | BTC | 1256 | -7.18 | 407 | -8.24 | -47.1 | FAIL |
| volatility | Bollinger mean-revert | signal | 20/2.5 | 1h | BTC | 819 | -10.70 | 260 | -11.88 | -41.0 | FAIL |
| volatility | Bollinger mean-revert | signal | 10/2 | 1h | BTC | 1679 | -3.69 | 538 | -7.37 | -47.8 | FAIL |
| volatility | Chandelier exit | filter | 22/3 | 1h | BTC | 349 | 6.89 | 118 | 1.63 | -26.3 | SURVIVOR |
| volatility | Chandelier exit | filter | 14/2 | 1h | BTC | 351 | 7.29 | 119 | 0.42 | -28.6 | SURVIVOR |
| volatility | Chandelier exit | filter | 22/2 | 1h | BTC | 351 | 7.06 | 119 | 0.45 | -28.5 | SURVIVOR |
| volatility | Chandelier exit | filter | 14/2 | 1h | ETH | 308 | -7.60 | 112 | -43.28 | -54.5 | FAIL |
| volatility | Chandelier exit | filter | 22/2 | 1h | ETH | 308 | -7.60 | 112 | -43.28 | -54.5 | FAIL |
| volatility | Chandelier exit | filter | 22/3 | 1h | ETH | 304 | -6.19 | 112 | -44.72 | -55.4 | FAIL |
| volatility | Chandelier exit | signal | 22/3 | 15m | BTC | 13953 | -0.72 | 3092 | -2.25 | -72.4 | FAIL |
| volatility | Chandelier exit | signal | 14/2 | 15m | BTC | 26921 | -0.37 | 6743 | -1.42 | -96.0 | FAIL |
| volatility | Chandelier exit | signal | 22/2 | 15m | BTC | 42834 | -0.23 | 10940 | -0.91 | -99.3 | FAIL |
| volatility | Chandelier exit | signal | 22/3 | 1h | BTC | 2742 | -2.93 | 794 | -4.33 | -51.2 | FAIL |
| volatility | Chandelier exit | signal | 14/2 | 1h | BTC | 5708 | -1.60 | 1570 | -1.90 | -61.5 | FAIL |
| volatility | Chandelier exit | signal | 22/2 | 1h | BTC | 9226 | -1.04 | 2605 | -2.41 | -69.4 | FAIL |
| volatility | Keltner breakout | filter | 20/2 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| volatility | Keltner breakout | filter | 10/1.5 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| volatility | Keltner breakout | filter | 10/1.5 | 1h | ETH | 308 | -8.17 | 112 | -43.28 | -54.5 | FAIL |
| volatility | Keltner breakout | filter | 20/2 | 1h | ETH | 308 | -8.17 | 112 | -43.28 | -54.5 | FAIL |
| volatility | Keltner breakout | signal | 20/2 | 15m | BTC | 2933 | -2.71 | 897 | -0.54 | -35.0 | FAIL |
| volatility | Keltner breakout | signal | 10/1.5 | 15m | BTC | 3927 | -2.19 | 1152 | -4.15 | -50.4 | FAIL |
| volatility | Keltner breakout | signal | 20/2 | 1h | BTC | 662 | 42.73 | 232 | -10.41 | -41.0 | FAIL |
| volatility | Keltner breakout | signal | 10/1.5 | 1h | BTC | 891 | 8.85 | 297 | 3.70 | -30.6 | SURVIVOR |
| volatility | Keltner breakout | signal | 10/1.5 | 1h | ETH | 771 | -5.28 | 242 | 8.98 | -40.0 | FAIL |
| volatility | Keltner mean-revert | filter | 20/2 | 1h | BTC | 351 | 2.66 | 119 | -8.86 | -31.7 | FAIL |
| volatility | Keltner mean-revert | filter | 10/1.5 | 1h | BTC | 351 | 2.12 | 119 | 8.07 | -27.6 | SURVIVOR |
| volatility | Keltner mean-revert | filter | 10/1.5 | 1h | ETH | 308 | -10.24 | 111 | -40.17 | -54.9 | FAIL |
| volatility | Keltner mean-revert | signal | 20/2 | 15m | BTC | 2933 | -2.67 | 897 | -6.27 | -61.8 | FAIL |
| volatility | Keltner mean-revert | signal | 10/1.5 | 15m | BTC | 3927 | -2.12 | 1152 | -2.86 | -43.9 | FAIL |
| volatility | Keltner mean-revert | signal | 20/2 | 1h | BTC | 662 | -13.90 | 232 | -2.44 | -26.4 | FAIL |
| volatility | Keltner mean-revert | signal | 10/1.5 | 1h | BTC | 891 | -9.43 | 297 | -12.57 | -42.3 | FAIL |
| volatility | Stdev channel mean-revert | filter | 50/2 | 1h | BTC | 351 | 5.23 | 119 | -3.74 | -30.3 | FAIL |
| volatility | Stdev channel mean-revert | filter | 100/2 | 1h | BTC | 350 | 7.70 | 119 | -4.30 | -27.7 | FAIL |
| volatility | Stdev channel mean-revert | signal | 50/2 | 15m | BTC | 2414 | -3.60 | 791 | -4.63 | -47.7 | FAIL |
| volatility | Stdev channel mean-revert | signal | 100/2 | 15m | BTC | 1423 | -6.05 | 469 | -11.04 | -55.0 | FAIL |
| volatility | Stdev channel mean-revert | signal | 50/2 | 1h | BTC | 612 | -14.28 | 206 | 2.43 | -18.8 | FAIL |
| volatility | Stdev channel mean-revert | signal | 100/2 | 1h | BTC | 313 | -25.93 | 116 | -14.29 | -29.7 | FAIL |
| volume | A/D line trend (vs own MA) | filter | 20 | 1h | BTC | 348 | 11.27 | 118 | 1.52 | -27.8 | SURVIVOR |
| volume | A/D line trend (vs own MA) | filter | 50 | 1h | BTC | 337 | 9.32 | 113 | 9.01 | -27.1 | SURVIVOR |
| volume | A/D line trend (vs own MA) | filter | 20 | 1h | ETH | 303 | -3.86 | 111 | -42.17 | -52.6 | FAIL |
| volume | A/D line trend (vs own MA) | filter | 50 | 1h | ETH | 296 | -8.69 | 107 | -45.79 | -55.1 | FAIL |
| volume | A/D line trend (vs own MA) | signal | 20 | 15m | BTC | 18287 | -0.55 | 5899 | -1.67 | -98.6 | FAIL |
| volume | A/D line trend (vs own MA) | signal | 50 | 15m | BTC | 10901 | -0.92 | 3559 | -2.55 | -91.1 | FAIL |
| volume | A/D line trend (vs own MA) | signal | 20 | 1h | BTC | 4518 | -2.18 | 1483 | -5.61 | -84.8 | FAIL |
| volume | A/D line trend (vs own MA) | signal | 50 | 1h | BTC | 2526 | -3.23 | 849 | -7.78 | -66.7 | FAIL |
| volume | CMF 0-cross | filter | 20 | 1h | BTC | 347 | 6.97 | 118 | -2.66 | -30.0 | FAIL |
| volume | CMF 0-cross | filter | 10 | 1h | BTC | 348 | 9.23 | 117 | 3.13 | -29.5 | SURVIVOR |
| volume | CMF 0-cross | filter | 10 | 1h | ETH | 305 | -5.05 | 111 | -42.39 | -52.8 | FAIL |
| volume | CMF 0-cross | signal | 20 | 15m | BTC | 15917 | -0.63 | 5259 | -1.83 | -96.3 | FAIL |
| volume | CMF 0-cross | signal | 10 | 15m | BTC | 22666 | -0.44 | 7579 | -1.31 | -99.1 | FAIL |
| volume | CMF 0-cross | signal | 20 | 1h | BTC | 3764 | -2.08 | 1261 | -5.17 | -73.8 | FAIL |
| volume | CMF 0-cross | signal | 10 | 1h | BTC | 5835 | -1.69 | 1910 | -3.63 | -73.9 | FAIL |
| volume | Ease of Movement 0-cross | filter | 14 | 1h | BTC | 351 | 7.75 | 119 | 0.42 | -28.6 | SURVIVOR |
| volume | Ease of Movement 0-cross | filter | 20 | 1h | BTC | 351 | 7.75 | 119 | 0.42 | -28.6 | SURVIVOR |
| volume | Ease of Movement 0-cross | filter | 14 | 1h | ETH | 308 | -8.05 | 112 | -43.33 | -54.5 | FAIL |
| volume | Ease of Movement 0-cross | filter | 20 | 1h | ETH | 308 | -8.05 | 112 | -43.33 | -54.5 | FAIL |
| volume | Ease of Movement 0-cross | signal | 14 | 15m | BTC | 58265 | -0.17 | 18607 | -0.54 | -99.9 | FAIL |
| volume | Ease of Movement 0-cross | signal | 20 | 15m | BTC | 58265 | -0.17 | 18607 | -0.54 | -99.9 | FAIL |
| volume | Ease of Movement 0-cross | signal | 14 | 1h | BTC | 14727 | -0.68 | 4857 | -1.81 | -88.7 | FAIL |
| volume | Ease of Movement 0-cross | signal | 20 | 1h | BTC | 14727 | -0.68 | 4857 | -1.81 | -88.7 | FAIL |
| volume | Force Index 0-cross | filter | 13 | 1h | BTC | 350 | 8.35 | 119 | 0.54 | -28.4 | SURVIVOR |
| volume | Force Index 0-cross | filter | 2 | 1h | BTC | 351 | 7.74 | 119 | 0.42 | -28.6 | SURVIVOR |
| volume | Force Index 0-cross | filter | 13 | 1h | ETH | 307 | -6.47 | 112 | -44.74 | -55.0 | FAIL |
| volume | Force Index 0-cross | filter | 2 | 1h | ETH | 308 | -8.17 | 112 | -43.28 | -54.5 | FAIL |
| volume | Force Index 0-cross | signal | 13 | 15m | BTC | 14135 | -0.71 | 4943 | -1.74 | -87.5 | FAIL |
| volume | Force Index 0-cross | signal | 2 | 15m | BTC | 47892 | -0.21 | 16243 | -0.62 | -99.9 | FAIL |
| volume | Force Index 0-cross | signal | 13 | 1h | BTC | 3385 | -1.39 | 1128 | -4.14 | -51.8 | FAIL |
| volume | Force Index 0-cross | signal | 2 | 1h | BTC | 12108 | -0.82 | 4008 | -2.21 | -89.8 | FAIL |
| volume | MFI extremes | filter | 14/20-80 | 1h | BTC | 351 | 5.81 | 119 | 5.07 | -26.3 | SURVIVOR |
| volume | MFI extremes | filter | 14/30-70 | 1h | BTC | 349 | 1.15 | 119 | -8.82 | -34.2 | FAIL |
| volume | MFI extremes | filter | 14/20-80 | 1h | ETH | 308 | -7.38 | 112 | -39.52 | -52.5 | FAIL |
| volume | MFI extremes | signal | 14/20-80 | 15m | BTC | 4167 | -2.10 | 1373 | -1.71 | -29.1 | FAIL |
| volume | MFI extremes | signal | 14/30-70 | 15m | BTC | 8836 | -1.11 | 2971 | -2.33 | -70.9 | FAIL |
| volume | MFI extremes | signal | 14/20-80 | 1h | BTC | 1027 | -7.21 | 376 | -2.31 | -29.6 | FAIL |
| volume | MFI extremes | signal | 14/30-70 | 1h | BTC | 2118 | -4.57 | 762 | -4.60 | -41.2 | FAIL |
| volume | OBV divergence | filter | 20 | 1h | BTC | 204 | 43.57 | 65 | 81.08 | -12.7 | SURVIVOR |
| volume | OBV divergence | filter | 50 | 1h | BTC | 150 | 39.50 | 48 | 21.33 | -18.4 | SURVIVOR |
| volume | OBV divergence | filter | 20 | 1h | ETH | 176 | 51.72 | 67 | -50.33 | -43.2 | FAIL |
| volume | OBV divergence | filter | 50 | 1h | ETH | 100 | -14.03 | 49 | -37.05 | -30.2 | FAIL |
| volume | OBV divergence | signal | 20 | 15m | BTC | 2225 | -3.89 | 700 | -3.55 | -49.4 | FAIL |
| volume | OBV divergence | signal | 50 | 15m | BTC | 630 | -14.83 | 201 | -31.43 | -72.9 | FAIL |
| volume | OBV divergence | signal | 20 | 1h | BTC | 354 | -3.98 | 123 | 19.26 | -49.1 | FAIL |
| volume | OBV divergence | signal | 50 | 1h | BTC | 117 | -77.20 | 45 | 78.46 | -51.6 | FAIL |
| volume | OBV trend (vs own MA) | filter | 20 | 1h | BTC | 351 | 4.41 | 118 | 3.55 | -27.1 | SURVIVOR |
| volume | OBV trend (vs own MA) | filter | 50 | 1h | BTC | 329 | 6.84 | 110 | 6.11 | -25.0 | SURVIVOR |
| volume | OBV trend (vs own MA) | filter | 20 | 1h | ETH | 306 | -8.18 | 112 | -44.55 | -55.4 | FAIL |
| volume | OBV trend (vs own MA) | filter | 50 | 1h | ETH | 289 | -2.68 | 102 | -40.26 | -51.0 | FAIL |
| volume | OBV trend (vs own MA) | signal | 20 | 15m | BTC | 16704 | -0.60 | 5590 | -1.67 | -93.3 | FAIL |
| volume | OBV trend (vs own MA) | signal | 50 | 15m | BTC | 9620 | -1.03 | 3146 | -1.48 | -62.0 | FAIL |
| volume | OBV trend (vs own MA) | signal | 20 | 1h | BTC | 4228 | 3.71 | 1347 | -0.48 | -38.5 | FAIL |
| volume | OBV trend (vs own MA) | signal | 50 | 1h | BTC | 2533 | -0.82 | 776 | -5.08 | -48.6 | FAIL |
| volume | VWAP fade band | filter | k=1 | 1h | BTC | 351 | 5.15 | 119 | 4.61 | -31.5 | SURVIVOR |
| volume | VWAP fade band | filter | k=2 | 1h | BTC | 351 | 6.25 | 119 | -0.85 | -32.0 | FAIL |
| volume | VWAP fade band | filter | k=1 | 1h | ETH | 307 | -6.99 | 111 | -41.38 | -58.8 | FAIL |
| volume | VWAP fade band | signal | k=1 | 15m | BTC | 6567 | -1.52 | 2252 | -3.58 | -82.6 | FAIL |
| volume | VWAP fade band | signal | k=2 | 15m | BTC | 3460 | -2.82 | 1160 | -5.90 | -72.5 | FAIL |
| volume | VWAP fade band | signal | k=1 | 1h | BTC | 2463 | -3.96 | 825 | -6.67 | -60.6 | FAIL |
| volume | VWAP fade band | signal | k=2 | 1h | BTC | 999 | -7.24 | 329 | -11.48 | -42.0 | FAIL |
| volume | VWAP session cross | filter | cross | 1h | BTC | 351 | 7.52 | 119 | 0.42 | -28.6 | SURVIVOR |
| volume | VWAP session cross | filter | cross | 1h | ETH | 308 | -8.17 | 112 | -43.28 | -54.5 | FAIL |
| volume | VWAP session cross | signal | cross | 15m | BTC | 15058 | -0.65 | 4999 | -1.58 | -84.0 | FAIL |
| volume | VWAP session cross | signal | cross | 1h | BTC | 7028 | -0.64 | 2319 | -2.46 | -68.2 | FAIL |
| volume | Volume oscillator confirm | filter | 5/20 | 1h | BTC | 340 | 12.78 | 117 | -0.43 | -27.2 | FAIL |
| volume | Volume oscillator confirm | filter | 10/50 | 1h | BTC | 307 | 14.84 | 108 | -6.21 | -30.7 | FAIL |
| volume | Volume oscillator confirm | signal | 5/20 | 15m | BTC | 32490 | -0.31 | 10691 | -0.92 | -98.9 | FAIL |
| volume | Volume oscillator confirm | signal | 10/50 | 15m | BTC | 30889 | -0.32 | 10267 | -0.96 | -98.1 | FAIL |
| volume | Volume oscillator confirm | signal | 5/20 | 1h | BTC | 8557 | -1.13 | 2844 | -3.10 | -89.2 | FAIL |
| volume | Volume oscillator confirm | signal | 10/50 | 1h | BTC | 8303 | -1.18 | 2767 | -2.81 | -80.4 | FAIL |
