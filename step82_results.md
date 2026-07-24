# Round 82 — The Eye x Indicator Matrix

Wallace's mandate, verbatim: *"Now that the eye is built, study how to use the eye better. Go back to the indicators, do the math on how exactly you can use them to your advantage, and come back with the FULL data. A full study. Not some half-assed two-word thing I don't understand."*

Round 76 tested all 53 standard indicators as lone, standalone triggers and found almost none survive alone. That was rejected as the wrong question — nobody trades an oscillator cross with no context. Round 81 built `chart_reader.py`, a deterministic, free, always-on function that reads a chart's structure/location/quality/momentum from raw OHLCV, the same way a trader's eye would. This round asks the question that actually matters: **does knowing where you are change whether a given indicator's signal is worth taking?**

## Method, in plain English

1. **The eye, made fast.** `chart_reader.read_chart()` is built to be called once, live, on the newest bar. To grade it across full history (55k BTC 1h bars, 222k BTC 15m bars, plus the ETH equivalents) it had to be rewritten as whole-series vectorized math instead of one call per bar — `step82_eye.py`. Every threshold (what counts as a 'large' body, where the range edges are, how many bars define momentum) is imported directly from `chart_reader.py`, not retyped, so the two can never silently drift apart. The one approximation this required (see Limitations) was checked against the real `read_chart()` on 600 random bars across all four datasets: **100% agreement on all four axes, every sample.** Labeling runtime: 0.08s for 55k BTC 1h bars, 0.33s for 222k BTC 15m bars — effectively free.
2. **The indicators, reused verbatim.** Every one of Round 76's 53 indicator implementations is imported unmodified from `step76_indicators.py` (via a harvest of its own `sweep()` calls — nothing was retyped). Ichimoku is excluded here because Round 76 only defined it as a 4h system, and this round's eye is labeled on 1h/15m only — **51 indicators** are in scope, each at its Round-76 'standard default' config (the first of 2-3 param sets tested per indicator, chosen before any run per R76's own discipline).
3. **Entries.** An indicator's own signal (identical to what R76 tested in 'signal' mode) is scanned for ENTRY EVENTS — bars where it freshly flips to +1 (long) or -1 (short). A gated entry is only taken when the eye's state at that bar equals the state under test.
4. **One fixed exit convention, for every cell in the matrix** — this is the whole point of gating on the eye instead of letting each indicator's own exit logic muddy the comparison:
   - stop = **1.5x the 14-period ATR%**, computed once as the median ATR% over that asset/timeframe's TRAIN slice only (a vol scale, not a fit — reused unchanged on val, so there is no leakage)
   - target = **2x the stop distance** (2R, fixed reward:risk)
   - max hold = **24 bars on 1h (1 day), 48 bars on 15m (12h)**
   - execution = **maker** (matches R76's own convention exactly, so the ungated baseline pulled from R76's own numbers is cost-comparable)
   - one trade at a time per (indicator, direction) — a new gated entry inside an existing max-hold window is skipped, not pyramided
5. **Scoring** uses the project's real `run_backtest` engine unmodified — full costs (maker fee + spread + slippage), real funding via `align_funding`, chronological 60/20/20 split, selection on TRAIN only, the sealed 20% test slice never touched. Reliability floor: **20 train / 8 val trades** — cells below that are flagged UNRELIABLE, never silently dropped.

Realized exit parameters (asset/tf-specific, derived from each asset's own train-slice ATR%):
  - BTC 1h: stop=1.215%, target=2.429%, max_hold=24 bars, train n=33295, val n=11099
  - BTC 15m: stop=0.542%, target=1.085%, max_hold=48 bars, train n=133183, val n=44394
  - ETH 1h: stop=1.466%, target=2.932%, max_hold=24 bars, train n=28189, val n=9397
  - ETH 15m: stop=0.674%, target=1.348%, max_hold=48 bars, train n=112760, val n=37587

## Part 1 — State census: what the market actually looks like

BTC 1h: 55,428 bars labeled (post-warmup), **93 distinct structure x location x quality x momentum combinations occur**, of which **36 are 'populated'** (>=1% of bars each) — this populated set is what the matrix in Part 2 is built on. The populated set covers 82.9% of all bars; the remaining ~93-36=57 combinations that occur are each individually rare (each <1% of bars) and are excluded from the matrix as too sparse to backtest meaningfully, though they are real and occasionally occupied.

BTC 15m: 221,907 bars labeled, 102 distinct combinations, **34 populated** (covering 79.0% of bars).

### BTC 1h — populated states (>=1% of bars), full table

| state | structure | location | quality | momentum | bars | share_pct |
|---|---|---|---|---|---|---|
| transition|mid range|messy|contracting | transition | mid range | messy | contracting | 3388 | 6.112 |
| transition|mid range|messy|expanding | transition | mid range | messy | expanding | 3013 | 5.436 |
| uptrend|at range high|messy|contracting | uptrend | at range high | messy | contracting | 2406 | 4.341 |
| downtrend|pulling back in trend|messy|contracting | downtrend | pulling back in trend | messy | contracting | 2266 | 4.088 |
| uptrend|pulling back in trend|messy|contracting | uptrend | pulling back in trend | messy | contracting | 2212 | 3.991 |
| uptrend|at range high|messy|expanding | uptrend | at range high | messy | expanding | 1988 | 3.587 |
| downtrend|pulling back in trend|messy|expanding | downtrend | pulling back in trend | messy | expanding | 1949 | 3.516 |
| transition|at range high|messy|contracting | transition | at range high | messy | contracting | 1947 | 3.513 |
| uptrend|pulling back in trend|messy|expanding | uptrend | pulling back in trend | messy | expanding | 1940 | 3.500 |
| transition|at range high|messy|expanding | transition | at range high | messy | expanding | 1754 | 3.164 |
| downtrend|at range low|messy|contracting | downtrend | at range low | messy | contracting | 1680 | 3.031 |
| transition|at range low|messy|contracting | transition | at range low | messy | contracting | 1478 | 2.667 |
| downtrend|at range low|messy|expanding | downtrend | at range low | messy | expanding | 1474 | 2.659 |
| transition|at range low|messy|expanding | transition | at range low | messy | expanding | 1449 | 2.614 |
| transition|mid range|clean|contracting | transition | mid range | clean | contracting | 1326 | 2.392 |
| transition|mid range|clean|expanding | transition | mid range | clean | expanding | 1162 | 2.096 |
| transition|mid range|messy|stalling | transition | mid range | messy | stalling | 980 | 1.768 |
| transition|at range high|clean|contracting | transition | at range high | clean | contracting | 896 | 1.617 |
| downtrend|pulling back in trend|clean|contracting | downtrend | pulling back in trend | clean | contracting | 891 | 1.607 |
| uptrend|pulling back in trend|clean|contracting | uptrend | pulling back in trend | clean | contracting | 855 | 1.543 |
| uptrend|at range high|clean|contracting | uptrend | at range high | clean | contracting | 838 | 1.512 |
| uptrend|pulling back in trend|clean|expanding | uptrend | pulling back in trend | clean | expanding | 791 | 1.427 |
| downtrend|pulling back in trend|clean|expanding | downtrend | pulling back in trend | clean | expanding | 785 | 1.416 |
| transition|at range high|clean|expanding | transition | at range high | clean | expanding | 729 | 1.315 |
| transition|at range low|clean|contracting | transition | at range low | clean | contracting | 721 | 1.301 |
| downtrend|at range high|messy|contracting | downtrend | at range high | messy | contracting | 703 | 1.268 |
| uptrend|at range high|clean|expanding | uptrend | at range high | clean | expanding | 681 | 1.229 |
| downtrend|at range low|clean|contracting | downtrend | at range low | clean | contracting | 672 | 1.212 |
| downtrend|pulling back in trend|messy|stalling | downtrend | pulling back in trend | messy | stalling | 671 | 1.211 |
| uptrend|at range high|messy|stalling | uptrend | at range high | messy | stalling | 665 | 1.200 |
| transition|at range low|clean|expanding | transition | at range low | clean | expanding | 662 | 1.194 |
| uptrend|pulling back in trend|messy|stalling | uptrend | pulling back in trend | messy | stalling | 629 | 1.135 |
| uptrend|at range low|messy|contracting | uptrend | at range low | messy | contracting | 629 | 1.135 |
| downtrend|at range high|messy|expanding | downtrend | at range high | messy | expanding | 595 | 1.073 |
| uptrend|at range low|messy|expanding | uptrend | at range low | messy | expanding | 581 | 1.048 |
| downtrend|at range low|clean|expanding | downtrend | at range low | clean | expanding | 558 | 1.007 |

### BTC 15m — populated states (>=1% of bars), full table

| state | structure | location | quality | momentum | bars | share_pct |
|---|---|---|---|---|---|---|
| transition|mid range|messy|contracting | transition | mid range | messy | contracting | 11960 | 5.390 |
| transition|mid range|messy|expanding | transition | mid range | messy | expanding | 10617 | 4.784 |
| downtrend|pulling back in trend|messy|contracting | downtrend | pulling back in trend | messy | contracting | 8502 | 3.831 |
| uptrend|at range high|messy|contracting | uptrend | at range high | messy | contracting | 8219 | 3.704 |
| uptrend|pulling back in trend|messy|contracting | uptrend | pulling back in trend | messy | contracting | 8184 | 3.688 |
| downtrend|pulling back in trend|messy|expanding | downtrend | pulling back in trend | messy | expanding | 7527 | 3.392 |
| uptrend|pulling back in trend|messy|expanding | uptrend | pulling back in trend | messy | expanding | 7505 | 3.382 |
| transition|at range high|messy|contracting | transition | at range high | messy | contracting | 7016 | 3.162 |
| uptrend|at range high|messy|expanding | uptrend | at range high | messy | expanding | 6683 | 3.012 |
| transition|mid range|clean|contracting | transition | mid range | clean | contracting | 6309 | 2.843 |
| downtrend|at range low|messy|contracting | downtrend | at range low | messy | contracting | 6210 | 2.798 |
| transition|at range high|messy|expanding | transition | at range high | messy | expanding | 5889 | 2.654 |
| transition|at range low|messy|contracting | transition | at range low | messy | contracting | 5619 | 2.532 |
| transition|mid range|clean|expanding | transition | mid range | clean | expanding | 5472 | 2.466 |
| downtrend|at range low|messy|expanding | downtrend | at range low | messy | expanding | 5417 | 2.441 |
| transition|at range low|messy|expanding | transition | at range low | messy | expanding | 5298 | 2.387 |
| downtrend|pulling back in trend|clean|contracting | downtrend | pulling back in trend | clean | contracting | 4639 | 2.091 |
| uptrend|pulling back in trend|clean|contracting | uptrend | pulling back in trend | clean | contracting | 4510 | 2.032 |
| uptrend|at range high|clean|contracting | uptrend | at range high | clean | contracting | 4079 | 1.838 |
| downtrend|pulling back in trend|clean|expanding | downtrend | pulling back in trend | clean | expanding | 3954 | 1.782 |
| uptrend|pulling back in trend|clean|expanding | uptrend | pulling back in trend | clean | expanding | 3941 | 1.776 |
| transition|at range high|clean|contracting | transition | at range high | clean | contracting | 3804 | 1.714 |
| transition|mid range|messy|stalling | transition | mid range | messy | stalling | 3749 | 1.689 |
| transition|at range high|clean|expanding | transition | at range high | clean | expanding | 3260 | 1.469 |
| uptrend|at range high|clean|expanding | uptrend | at range high | clean | expanding | 3229 | 1.455 |
| downtrend|at range low|clean|contracting | downtrend | at range low | clean | contracting | 3039 | 1.369 |
| transition|at range low|clean|contracting | transition | at range low | clean | contracting | 2963 | 1.335 |
| transition|at range low|clean|expanding | transition | at range low | clean | expanding | 2749 | 1.239 |
| downtrend|at range low|clean|expanding | downtrend | at range low | clean | expanding | 2674 | 1.205 |
| downtrend|pulling back in trend|messy|stalling | downtrend | pulling back in trend | messy | stalling | 2571 | 1.159 |
| downtrend|at range high|messy|contracting | downtrend | at range high | messy | contracting | 2519 | 1.135 |
| uptrend|pulling back in trend|messy|stalling | uptrend | pulling back in trend | messy | stalling | 2510 | 1.131 |
| downtrend|at range high|messy|expanding | downtrend | at range high | messy | expanding | 2377 | 1.071 |
| uptrend|at range high|messy|stalling | uptrend | at range high | messy | stalling | 2354 | 1.061 |

**Reading the census itself is already informative.** On 1h, the single most common state is *transition / mid range / messy / contracting* — the market spends more time in ambiguous, low-conviction chop than in any clean trend or range state. 'messy' quality dominates the top of the table; 'clean' states are the minority. This is the honest occupancy the matrix in Part 2 has to work with: most of the states a trading system can be gated on are NOT clean textbook trends — they are transitional, contracting, or at a range edge with noisy candles. Any indicator whose only good state is a rare, extremely clean one is an indicator that will sit idle almost all the time in practice.


ETH transfer census, for comparison — ETH 1h: 94 distinct combinations observed; ETH 15m: 97. (Full ETH census CSVs: step82_census_eth_1h.csv / _15m.csv.)

## Part 2 — The full matrix

**7,140 cells** scored (51 indicators x 2 directions x 36 states on 1h + 34 states on 15m x 2 timeframes). Full matrix, every cell including empty and losing ones: `step82_matrix.csv`.

Verdict breakdown across all 7,140 cells: **289 SURVIVOR** (positive train AND val, >=20/8 trades), **2578 UNRELIABLE** (too few trades to trust either way — flagged, not dropped), **3313 FAIL** (adequate sample, not both-splits-positive), **960 NO-TRADES** (that indicator's signal never fired inside that state at all — a real, informative zero, not a gap in the data).

### (a) Top 30 cells by validated (val) expectancy, adequate samples

| family | indicator | tf | direction | state | tr_n | tr_exp | va_n | va_exp | va_win_pct | va_ret_pct | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| trend | DEMA cross | 1h | short | uptrend|at range low|messy|expanding | 40 | 56.376 | 13 | 207.683 | 92.310 | 27.000 | SURVIVOR |
| trend | MACD line/signal cross | 1h | short | uptrend|at range low|messy|expanding | 36 | 10.930 | 14 | 180.983 | 85.710 | 25.340 | SURVIVOR |
| trend | MACD histogram 0-cross | 1h | short | uptrend|at range low|messy|expanding | 36 | 10.930 | 14 | 180.983 | 85.710 | 25.340 | SURVIVOR |
| trend | DEMA cross | 1h | long | downtrend|pulling back in trend|clean|expanding | 31 | 54.765 | 9 | 159.352 | 88.890 | 14.340 | SURVIVOR |
| trend | DEMA cross | 1h | long | transition|mid range|clean|expanding | 23 | 27.293 | 8 | 146.327 | 75.000 | 11.710 | SURVIVOR |
| levels | Williams fractals | 1h | short | downtrend|at range low|clean|contracting | 24 | -9.560 | 11 | 140.437 | 81.820 | 15.450 | FAIL |
| volatility | Bollinger breakout | 1h | short | uptrend|at range low|messy|expanding | 20 | -10.047 | 12 | 138.467 | 75.000 | 16.620 | FAIL |
| momentum | TSI 0-cross | 1h | short | uptrend|at range low|messy|contracting | 29 | 22.677 | 8 | 128.627 | 75.000 | 10.290 | SURVIVOR |
| trend | EMA cross | 1h | short | uptrend|at range low|messy|contracting | 27 | -3.346 | 11 | 128.140 | 72.730 | 14.100 | FAIL |
| momentum | Momentum 0-cross | 1h | short | uptrend|at range low|messy|expanding | 62 | 31.280 | 19 | 127.155 | 73.680 | 24.160 | SURVIVOR |
| trend | TEMA cross | 1h | short | uptrend|at range low|messy|expanding | 35 | 40.568 | 12 | 126.715 | 75.000 | 15.210 | SURVIVOR |
| momentum | ROC 0-cross | 1h | short | uptrend|at range low|messy|expanding | 62 | 6.048 | 23 | 126.082 | 73.910 | 29.000 | SURVIVOR |
| trend | ADX/DMI DI-cross+ADX>thresh | 1h | short | transition|mid range|messy|contracting | 35 | 2.893 | 8 | 121.903 | 75.000 | 9.750 | SURVIVOR |
| trend | Aroon oscillator 0-cross | 1h | short | uptrend|at range low|messy|expanding | 55 | -16.506 | 12 | 119.634 | 75.000 | 14.360 | FAIL |
| trend | Aroon up/down cross | 1h | short | uptrend|at range low|messy|expanding | 55 | -16.506 | 12 | 119.634 | 75.000 | 14.360 | FAIL |
| volume | Ease of Movement 0-cross | 1h | short | downtrend|at range high|messy|expanding | 33 | -27.899 | 12 | 119.385 | 83.330 | 14.330 | FAIL |
| trend | Parabolic SAR | 1h | short | uptrend|at range low|messy|expanding | 43 | -15.948 | 11 | 113.966 | 72.730 | 12.540 | FAIL |
| volume | CMF 0-cross | 1h | short | uptrend|at range low|messy|expanding | 37 | 20.339 | 10 | 110.780 | 70.000 | 11.080 | SURVIVOR |
| trend | Linreg slope sign | 1h | short | uptrend|at range low|messy|expanding | 29 | -3.818 | 19 | 105.259 | 63.160 | 20.000 | FAIL |
| volume | Force Index 0-cross | 1h | short | uptrend|at range low|messy|expanding | 56 | -8.667 | 18 | 104.691 | 66.670 | 18.840 | FAIL |
| momentum | ROC 0-cross | 1h | short | transition|at range high|messy|expanding | 39 | 30.487 | 17 | 104.270 | 64.710 | 17.730 | SURVIVOR |
| volume | CMF 0-cross | 1h | long | uptrend|pulling back in trend|clean|contracting | 20 | 61.892 | 10 | 99.714 | 80.000 | 9.970 | SURVIVOR |
| trend | TEMA cross | 1h | long | transition|mid range|clean|expanding | 29 | -36.203 | 13 | 98.378 | 61.540 | 12.790 | FAIL |
| trend | ADX/DMI DI-cross+ADX>thresh | 1h | long | uptrend|at range high|messy|contracting | 25 | 18.287 | 9 | 95.154 | 66.670 | 8.560 | SURVIVOR |
| volume | Volume oscillator confirm | 1h | long | transition|at range high|clean|expanding | 42 | -19.219 | 12 | 92.269 | 66.670 | 11.070 | FAIL |
| volume | Force Index 0-cross | 1h | long | downtrend|pulling back in trend|clean|expanding | 60 | -7.807 | 17 | 91.546 | 64.710 | 15.560 | FAIL |
| momentum | Fisher Transform 0-cross | 1h | short | uptrend|at range low|messy|expanding | 33 | -6.088 | 8 | 91.513 | 62.500 | 7.320 | FAIL |
| volume | A/D line trend (vs own MA) | 1h | long | transition|at range high|clean|expanding | 39 | -30.228 | 15 | 91.156 | 60.000 | 13.670 | FAIL |
| trend | MACD line/signal cross | 1h | short | transition|at range low|messy|expanding | 54 | -25.060 | 16 | 89.710 | 62.500 | 14.350 | FAIL |
| trend | MACD histogram 0-cross | 1h | short | transition|at range low|messy|expanding | 54 | -25.060 | 16 | 89.710 | 62.500 | 14.350 | FAIL |

### Bottom 10 reliable cells (worst validated expectancy)

| family | indicator | tf | direction | state | tr_n | tr_exp | va_n | va_exp | verdict |
|---|---|---|---|---|---|---|---|---|---|
| volume | A/D line trend (vs own MA) | 1h | short | transition|at range low|messy|contracting | 33 | 4.691 | 9 | -115.708 | FAIL |
| momentum | Awesome Oscillator 0-cross | 1h | short | downtrend|pulling back in trend|messy|expanding | 22 | 48.209 | 8 | -107.756 | FAIL |
| trend | KAMA cross | 1h | short | transition|at range low|messy|contracting | 32 | -11.751 | 9 | -105.366 | FAIL |
| momentum | Momentum 0-cross | 1h | short | downtrend|pulling back in trend|messy|stalling | 38 | -34.394 | 9 | -104.948 | FAIL |
| trend | TRIX 0-cross | 1h | short | downtrend|at range low|messy|contracting | 24 | -7.594 | 8 | -99.449 | FAIL |
| trend | Aroon up/down cross | 1h | long | transition|at range low|messy|expanding | 23 | -21.570 | 13 | -98.503 | FAIL |
| trend | Aroon oscillator 0-cross | 1h | long | transition|at range low|messy|expanding | 23 | -21.570 | 13 | -98.503 | FAIL |
| momentum | ROC 0-cross | 1h | short | uptrend|at range low|messy|contracting | 26 | -51.450 | 9 | -97.290 | FAIL |
| volume | Volume oscillator confirm | 1h | long | uptrend|pulling back in trend|clean|expanding | 39 | -0.932 | 14 | -94.877 | FAIL |
| momentum | Fisher Transform 0-cross | 1h | short | transition|mid range|clean|contracting | 45 | 21.856 | 9 | -93.442 | FAIL |

### (b) Per-indicator summary — best state and worst state

| family | indicator | tf | best_state | best_va_exp | worst_state | worst_va_exp | n_survivor_states | n_states_tested |
|---|---|---|---|---|---|---|---|---|
| trend | DEMA cross | 1h | short/uptrend|at range low|messy|expanding | 207.683 | short/transition|at range low|clean|expanding | -66.569 | 4 | 72 |
| trend | MACD line/signal cross | 1h | short/uptrend|at range low|messy|expanding | 180.983 | short/transition|mid range|clean|contracting | -91.892 | 6 | 72 |
| trend | MACD histogram 0-cross | 1h | short/uptrend|at range low|messy|expanding | 180.983 | short/transition|mid range|clean|contracting | -91.892 | 6 | 72 |
| levels | Williams fractals | 1h | short/downtrend|at range low|clean|contracting | 140.437 | short/downtrend|pulling back in trend|messy|stalling | -87.760 | 7 | 72 |
| volatility | Bollinger breakout | 1h | short/uptrend|at range low|messy|expanding | 138.467 | short/transition|at range low|messy|expanding | -51.165 | 0 | 72 |
| momentum | TSI 0-cross | 1h | short/uptrend|at range low|messy|contracting | 128.627 | short/transition|at range low|messy|contracting | -58.630 | 1 | 72 |
| trend | EMA cross | 1h | short/uptrend|at range low|messy|contracting | 128.140 | short/transition|at range low|messy|contracting | -88.299 | 0 | 72 |
| momentum | Momentum 0-cross | 1h | short/uptrend|at range low|messy|expanding | 127.155 | short/downtrend|pulling back in trend|messy|stalling | -104.948 | 11 | 72 |
| trend | TEMA cross | 1h | short/uptrend|at range low|messy|expanding | 126.715 | long/uptrend|at range high|messy|expanding | -56.524 | 7 | 72 |
| momentum | ROC 0-cross | 1h | short/uptrend|at range low|messy|expanding | 126.082 | short/uptrend|at range low|messy|contracting | -97.290 | 11 | 72 |
| trend | ADX/DMI DI-cross+ADX>thresh | 1h | short/transition|mid range|messy|contracting | 121.903 | short/transition|mid range|clean|expanding | -45.047 | 5 | 72 |
| trend | Aroon up/down cross | 1h | short/uptrend|at range low|messy|expanding | 119.634 | long/transition|at range low|messy|expanding | -98.503 | 4 | 72 |
| trend | Aroon oscillator 0-cross | 1h | short/uptrend|at range low|messy|expanding | 119.634 | long/transition|at range low|messy|expanding | -98.503 | 4 | 72 |
| volume | Ease of Movement 0-cross | 1h | short/downtrend|at range high|messy|expanding | 119.385 | long/downtrend|at range low|clean|contracting | -53.059 | 9 | 72 |
| trend | Parabolic SAR | 1h | short/uptrend|at range low|messy|expanding | 113.966 | long/uptrend|at range high|clean|expanding | -83.254 | 4 | 72 |
| volume | CMF 0-cross | 1h | short/uptrend|at range low|messy|expanding | 110.780 | short/uptrend|at range high|messy|contracting | -60.132 | 5 | 72 |
| trend | Linreg slope sign | 1h | short/uptrend|at range low|messy|expanding | 105.259 | long/transition|at range high|messy|contracting | -69.922 | 5 | 72 |
| volume | Force Index 0-cross | 1h | short/uptrend|at range low|messy|expanding | 104.691 | long/transition|mid range|clean|contracting | -85.897 | 6 | 72 |
| volume | Volume oscillator confirm | 1h | long/transition|at range high|clean|expanding | 92.269 | long/uptrend|pulling back in trend|clean|expanding | -94.877 | 7 | 72 |
| momentum | Fisher Transform 0-cross | 1h | short/uptrend|at range low|messy|expanding | 91.513 | short/transition|mid range|clean|contracting | -93.442 | 5 | 72 |
| volume | A/D line trend (vs own MA) | 1h | long/transition|at range high|clean|expanding | 91.156 | short/transition|at range low|messy|contracting | -115.708 | 7 | 72 |
| trend | KAMA cross | 1h | short/uptrend|at range low|messy|expanding | 88.261 | short/transition|at range low|messy|contracting | -105.366 | 6 | 72 |
| momentum | Stochastic RSI extremes | 1h | long/transition|at range low|clean|contracting | 88.148 | long/transition|at range high|messy|expanding | -76.057 | 6 | 72 |
| momentum | Ultimate Oscillator extremes | 15m | short/uptrend|at range high|clean|contracting | 85.895 | short/transition|at range high|clean|contracting | -48.360 | 0 | 68 |
| volatility | Chandelier exit | 1h | short/uptrend|at range low|messy|expanding | 83.769 | short/downtrend|pulling back in trend|clean|expanding | -90.496 | 3 | 72 |
| trend | SMA cross | 1h | long/transition|at range high|clean|expanding | 75.211 | long/downtrend|at range high|messy|contracting | -72.677 | 1 | 72 |
| volume | VWAP fade band | 1h | short/uptrend|at range high|clean|expanding | 67.276 | short/uptrend|pulling back in trend|messy|expanding | -76.277 | 2 | 72 |
| trend | TRIX 0-cross | 15m | long/transition|mid range|messy|expanding | 65.983 | long/uptrend|pulling back in trend|messy|contracting | -41.635 | 0 | 68 |
| volume | VWAP fade band | 15m | long/uptrend|pulling back in trend|messy|stalling | 65.079 | short/uptrend|at range high|clean|contracting | -47.034 | 4 | 68 |
| momentum | CCI extremes | 1h | long/transition|at range low|clean|contracting | 62.662 | long/transition|at range low|clean|expanding | -71.753 | 3 | 72 |
| volume | OBV trend (vs own MA) | 1h | short/uptrend|at range low|messy|contracting | 61.110 | short/downtrend|pulling back in trend|messy|stalling | -87.078 | 8 | 72 |
| levels | Camarilla pivots (reversion) | 1h | short/transition|at range high|clean|expanding | 58.771 | long/uptrend|at range low|messy|expanding | -56.570 | 1 | 72 |
| momentum | Awesome Oscillator 0-cross | 1h | long/transition|mid range|messy|expanding | 58.621 | short/downtrend|pulling back in trend|messy|expanding | -107.756 | 1 | 72 |
| trend | ADX/DMI DI cross | 1h | long/transition|mid range|clean|expanding | 57.372 | short/transition|mid range|clean|contracting | -75.138 | 8 | 72 |
| trend | Vortex VI+/VI- cross | 1h | short/uptrend|at range low|messy|expanding | 56.909 | long/uptrend|pulling back in trend|messy|stalling | -62.483 | 6 | 72 |
| trend | SuperTrend | 15m | long/uptrend|at range high|messy|contracting | 54.326 | short/transition|at range low|clean|expanding | -28.318 | 1 | 68 |
| momentum | RSI 50-cross | 1h | short/transition|mid range|messy|contracting | 53.471 | short/transition|at range low|messy|contracting | -88.032 | 4 | 72 |
| trend | SuperTrend | 1h | short/uptrend|at range low|messy|expanding | 52.855 | short/uptrend|at range low|messy|expanding | 52.855 | 1 | 72 |
| momentum | Awesome Oscillator 0-cross | 15m | long/transition|mid range|clean|expanding | 49.985 | short/downtrend|pulling back in trend|messy|contracting | -34.466 | 2 | 68 |
| momentum | Stochastic %K/%D cross | 1h | long/downtrend|at range high|messy|expanding | 49.964 | short/downtrend|pulling back in trend|messy|stalling | -63.243 | 4 | 72 |
| trend | Hull MA cross | 1h | short/downtrend|at range low|clean|contracting | 48.078 | short/downtrend|pulling back in trend|clean|expanding | -59.240 | 9 | 72 |
| volume | OBV trend (vs own MA) | 15m | long/downtrend|at range low|clean|expanding | 46.974 | long/downtrend|at range low|clean|contracting | -46.504 | 2 | 68 |
| momentum | Williams %R extremes | 1h | long/transition|at range low|clean|contracting | 46.473 | short/uptrend|at range high|clean|contracting | -68.967 | 4 | 72 |
| momentum | Stochastic extremes | 1h | long/transition|at range low|clean|contracting | 46.473 | short/uptrend|at range high|clean|contracting | -68.967 | 4 | 72 |
| volume | VWAP session cross | 1h | long/downtrend|pulling back in trend|clean|expanding | 43.658 | short/downtrend|pulling back in trend|messy|stalling | -88.030 | 6 | 72 |
| volatility | Bollinger mean-revert | 15m | short/transition|at range high|clean|contracting | 41.427 | long/transition|at range low|messy|contracting | -28.679 | 1 | 68 |
| momentum | Fisher Transform 0-cross | 15m | long/transition|at range low|messy|expanding | 40.926 | long/uptrend|pulling back in trend|messy|stalling | -45.657 | 3 | 68 |
| momentum | Stochastic RSI extremes | 15m | short/uptrend|pulling back in trend|messy|stalling | 40.691 | long/transition|at range high|clean|contracting | -63.221 | 2 | 68 |
| trend | ADX/DMI DI-cross+ADX>thresh | 15m | long/downtrend|pulling back in trend|clean|contracting | 40.625 | short/downtrend|pulling back in trend|clean|contracting | -58.906 | 5 | 68 |
| volume | MFI extremes | 15m | short/transition|mid range|messy|expanding | 40.302 | long/downtrend|pulling back in trend|messy|contracting | -43.647 | 2 | 68 |
| trend | EMA cross | 15m | short/transition|mid range|clean|expanding | 38.964 | long/downtrend|at range high|messy|contracting | -41.032 | 4 | 68 |
| trend | Aroon up/down cross | 15m | long/uptrend|at range high|clean|contracting | 36.663 | long/uptrend|at range high|messy|expanding | -40.618 | 3 | 68 |
| trend | Aroon oscillator 0-cross | 15m | long/uptrend|at range high|clean|contracting | 36.663 | long/uptrend|at range high|messy|expanding | -40.618 | 3 | 68 |
| momentum | TSI 0-cross | 15m | long/downtrend|pulling back in trend|messy|expanding | 35.641 | long/downtrend|pulling back in trend|clean|expanding | -45.971 | 3 | 68 |
| momentum | Connors RSI extremes | 15m | long/uptrend|pulling back in trend|messy|expanding | 35.403 | long/transition|at range low|clean|contracting | -45.637 | 1 | 68 |
| volume | A/D line trend (vs own MA) | 15m | short/transition|at range high|clean|contracting | 34.956 | long/transition|at range low|messy|contracting | -35.718 | 3 | 68 |
| trend | SMA cross | 15m | short/uptrend|pulling back in trend|messy|contracting | 34.800 | short/uptrend|pulling back in trend|clean|contracting | -38.265 | 3 | 68 |
| trend | MACD histogram 0-cross | 15m | long/transition|mid range|clean|expanding | 32.982 | long/uptrend|pulling back in trend|messy|stalling | -47.569 | 3 | 68 |
| trend | MACD line/signal cross | 15m | long/transition|mid range|clean|expanding | 32.982 | long/uptrend|pulling back in trend|messy|stalling | -47.569 | 3 | 68 |
| trend | TRIX 0-cross | 1h | long/uptrend|at range high|messy|expanding | 32.190 | short/downtrend|at range low|messy|contracting | -99.449 | 0 | 72 |
| momentum | RSI OB/OS | 1h | short/uptrend|at range high|messy|expanding | 31.774 | short/uptrend|at range high|messy|contracting | -39.628 | 0 | 72 |
| trend | Parabolic SAR | 15m | long/downtrend|at range high|messy|contracting | 30.222 | long/uptrend|pulling back in trend|clean|contracting | -38.540 | 3 | 68 |
| momentum | RSI 50-cross | 15m | short/uptrend|at range high|messy|expanding | 29.212 | long/uptrend|at range high|messy|stalling | -38.869 | 6 | 68 |
| trend | TEMA cross | 15m | long/transition|at range high|clean|contracting | 29.107 | short/downtrend|pulling back in trend|clean|contracting | -38.060 | 4 | 68 |
| volume | VWAP session cross | 15m | long/downtrend|at range low|clean|contracting | 28.890 | short/downtrend|pulling back in trend|messy|stalling | -26.273 | 4 | 68 |
| volatility | Chandelier exit | 15m | short/downtrend|pulling back in trend|messy|contracting | 26.845 | long/uptrend|at range high|messy|contracting | -31.841 | 2 | 68 |
| momentum | ROC 0-cross | 15m | short/transition|at range high|messy|expanding | 26.579 | long/transition|at range low|messy|expanding | -47.174 | 1 | 68 |
| volatility | Bollinger mean-revert | 1h | long/transition|at range low|messy|expanding | 25.139 | long/uptrend|at range low|messy|expanding | -69.213 | 0 | 72 |
| momentum | Momentum 0-cross | 15m | long/downtrend|pulling back in trend|messy|stalling | 24.173 | long/transition|at range low|clean|expanding | -41.189 | 2 | 68 |
| trend | ADX/DMI DI cross | 15m | short/uptrend|pulling back in trend|messy|contracting | 23.213 | short/uptrend|at range high|clean|contracting | -43.161 | 1 | 68 |
| volume | Force Index 0-cross | 15m | long/transition|mid range|clean|contracting | 22.572 | short/downtrend|pulling back in trend|messy|stalling | -35.080 | 3 | 68 |
| volume | MFI extremes | 1h | long/downtrend|at range low|messy|contracting | 21.425 | long/transition|at range low|messy|expanding | -40.168 | 2 | 72 |
| volume | OBV divergence | 15m | short/transition|at range high|clean|contracting | 21.052 | long/uptrend|pulling back in trend|messy|contracting | -63.906 | 1 | 68 |
| momentum | CCI extremes | 15m | short/uptrend|at range high|messy|stalling | 20.653 | short/downtrend|pulling back in trend|messy|expanding | -47.818 | 1 | 68 |
| trend | KAMA cross | 15m | short/downtrend|at range high|messy|expanding | 19.629 | short/downtrend|at range low|clean|contracting | -38.267 | 0 | 68 |
| momentum | RSI OB/OS | 15m | long/downtrend|at range low|clean|contracting | 19.235 | long/transition|at range low|messy|contracting | -35.879 | 2 | 68 |
| trend | Vortex VI+/VI- cross | 15m | long/uptrend|at range high|clean|expanding | 18.885 | long/uptrend|pulling back in trend|messy|stalling | -34.476 | 2 | 68 |
| volatility | Bollinger breakout | 15m | long/uptrend|at range high|clean|expanding | 18.526 | long/transition|at range high|clean|contracting | -43.696 | 2 | 68 |
| trend | Hull MA cross | 15m | long/transition|mid range|messy|stalling | 17.627 | long/downtrend|pulling back in trend|clean|contracting | -23.107 | 0 | 68 |
| levels | Camarilla pivots (reversion) | 15m | long/transition|at range low|messy|expanding | 16.017 | short/uptrend|at range high|messy|expanding | -50.650 | 0 | 68 |
| volume | CMF 0-cross | 15m | short/uptrend|at range high|clean|expanding | 15.067 | short/transition|at range high|clean|expanding | -43.781 | 0 | 68 |
| momentum | Williams %R extremes | 15m | long/downtrend|pulling back in trend|clean|expanding | 14.325 | short/transition|mid range|messy|stalling | -26.855 | 3 | 68 |
| momentum | Stochastic extremes | 15m | long/downtrend|pulling back in trend|clean|expanding | 14.325 | short/transition|mid range|messy|stalling | -26.855 | 3 | 68 |
| trend | Linreg slope sign | 15m | short/uptrend|pulling back in trend|messy|stalling | 14.013 | long/uptrend|pulling back in trend|clean|expanding | -46.131 | 2 | 68 |
| trend | DEMA cross | 15m | long/uptrend|at range high|messy|contracting | 13.988 | short/transition|at range high|messy|contracting | -63.474 | 3 | 68 |
| volume | Volume oscillator confirm | 15m | short/downtrend|pulling back in trend|clean|contracting | 13.921 | long/transition|mid range|messy|stalling | -31.900 | 0 | 68 |
| levels | Williams fractals | 15m | short/transition|mid range|clean|expanding | 8.308 | short/transition|at range high|clean|expanding | -39.837 | 2 | 68 |
| momentum | Stochastic %K/%D cross | 15m | long/transition|mid range|messy|stalling | 6.508 | long/transition|at range low|clean|expanding | -19.234 | 0 | 68 |
| volatility | BB-inside-KC squeeze release | 15m | long/downtrend|at range high|messy|expanding | 3.508 | short/downtrend|at range low|messy|contracting | -47.011 | 1 | 68 |
| volume | Ease of Movement 0-cross | 15m | long/uptrend|at range high|clean|expanding | 3.240 | short/downtrend|pulling back in trend|messy|stalling | -18.419 | 0 | 68 |
| volatility | Keltner mean-revert | 15m | short/transition|at range high|clean|expanding | 3.148 | long/downtrend|at range low|clean|expanding | -20.868 | 0 | 68 |
| volatility | Keltner breakout | 15m | short/downtrend|at range low|clean|expanding | 0.429 | long/transition|at range high|clean|expanding | -9.482 | 0 | 68 |
| volatility | BB-inside-KC squeeze release | 1h | long/transition|at range high|messy|contracting | -0.186 | long/transition|at range high|messy|expanding | -7.423 | 0 | 72 |
| momentum | Connors RSI extremes | 1h | short/transition|at range high|clean|expanding | -39.786 | long/transition|at range low|clean|expanding | -64.175 | 0 | 72 |
| volatility | Stdev channel mean-revert | 15m | long/transition|at range low|messy|expanding | -47.494 | long/transition|at range low|messy|expanding | -47.494 | 0 | 68 |
| volume | OBV divergence | 1h | long/transition|at range low|messy|expanding | -50.991 | short/downtrend|at range high|messy|expanding | -57.241 | 0 | 72 |
| levels | Classic pivots (reversion) | 15m | (no reliable cell) |  | (no reliable cell) |  | 0 | 68 |
| levels | Classic pivots (reversion) | 1h | (no reliable cell) |  | (no reliable cell) |  | 0 | 72 |
| momentum | Ultimate Oscillator extremes | 1h | (no reliable cell) |  | (no reliable cell) |  | 0 | 72 |
| volatility | Keltner breakout | 1h | (no reliable cell) |  | (no reliable cell) |  | 0 | 72 |
| volatility | Keltner mean-revert | 1h | (no reliable cell) |  | (no reliable cell) |  | 0 | 72 |
| volatility | Stdev channel mean-revert | 1h | (no reliable cell) |  | (no reliable cell) |  | 0 | 72 |

### (c) Per-state summary — which indicators work there, which fail

| state | n_reliable_cells | n_survivors | best_indicator | worst_indicator |
|---|---|---|---|---|
| downtrend|pulling back in trend|messy|expanding | 126 | 20 | Volume oscillator confirm (long, 1h) va_exp=61.11 | Awesome Oscillator 0-cross (short, 1h) va_exp=-107.76 |
| uptrend|at range low|messy|expanding | 44 | 18 | DEMA cross (short, 1h) va_exp=207.68 | VWAP fade band (long, 1h) va_exp=-71.53 |
| transition|at range high|messy|expanding | 126 | 16 | ROC 0-cross (short, 1h) va_exp=104.27 | Stochastic RSI extremes (long, 1h) va_exp=-76.06 |
| transition|mid range|clean|expanding | 132 | 14 | DEMA cross (long, 1h) va_exp=146.33 | Williams fractals (short, 1h) va_exp=-70.94 |
| downtrend|at range high|messy|expanding | 97 | 14 | Linreg slope sign (long, 1h) va_exp=67.65 | EMA cross (long, 1h) va_exp=-86.18 |
| downtrend|pulling back in trend|clean|expanding | 116 | 14 | DEMA cross (long, 1h) va_exp=159.35 | Chandelier exit (short, 1h) va_exp=-90.50 |
| downtrend|pulling back in trend|messy|contracting | 123 | 13 | Stochastic %K/%D cross (long, 1h) va_exp=46.47 | Chandelier exit (short, 1h) va_exp=-58.84 |
| uptrend|pulling back in trend|messy|expanding | 125 | 11 | ADX/DMI DI-cross+ADX>thresh (short, 1h) va_exp=54.56 | VWAP fade band (short, 1h) va_exp=-76.28 |
| transition|mid range|messy|contracting | 145 | 10 | ADX/DMI DI-cross+ADX>thresh (short, 1h) va_exp=121.90 | CCI extremes (short, 1h) va_exp=-66.55 |
| transition|at range high|messy|contracting | 113 | 9 | ROC 0-cross (short, 1h) va_exp=18.52 | TRIX 0-cross (long, 1h) va_exp=-87.36 |
| downtrend|pulling back in trend|clean|contracting | 102 | 9 | Fisher Transform 0-cross (long, 1h) va_exp=45.15 | RSI 50-cross (short, 1h) va_exp=-71.83 |
| uptrend|at range high|messy|expanding | 121 | 9 | Stochastic RSI extremes (short, 1h) va_exp=23.43 | ADX/DMI DI cross (long, 1h) va_exp=-62.76 |
| transition|at range high|clean|expanding | 103 | 8 | Bollinger breakout (long, 15m) va_exp=9.83 | ROC 0-cross (long, 1h) va_exp=-92.24 |
| transition|mid range|messy|stalling | 112 | 8 | RSI 50-cross (long, 1h) va_exp=37.33 | Volume oscillator confirm (long, 1h) va_exp=-62.88 |
| transition|at range high|clean|contracting | 76 | 8 | Bollinger mean-revert (short, 15m) va_exp=41.43 | Stochastic RSI extremes (long, 15m) va_exp=-63.22 |
| uptrend|pulling back in trend|clean|contracting | 95 | 7 | CMF 0-cross (long, 1h) va_exp=99.71 | KAMA cross (short, 1h) va_exp=-91.22 |
| uptrend|pulling back in trend|clean|expanding | 114 | 7 | Stochastic %K/%D cross (short, 1h) va_exp=47.57 | Volume oscillator confirm (long, 1h) va_exp=-94.88 |
| transition|mid range|clean|contracting | 119 | 7 | Ease of Movement 0-cross (short, 1h) va_exp=17.83 | Fisher Transform 0-cross (short, 1h) va_exp=-93.44 |
| uptrend|pulling back in trend|messy|contracting | 124 | 7 | Parabolic SAR (short, 1h) va_exp=68.71 | Chandelier exit (short, 1h) va_exp=-88.52 |
| uptrend|at range high|clean|contracting | 71 | 6 | Aroon up/down cross (long, 15m) va_exp=36.66 | Williams %R extremes (short, 1h) va_exp=-68.97 |
| downtrend|at range low|messy|expanding | 104 | 6 | Stochastic extremes (long, 1h) va_exp=46.39 | OBV trend (vs own MA) (short, 1h) va_exp=-65.70 |
| downtrend|at range low|messy|contracting | 90 | 6 | Fisher Transform 0-cross (short, 15m) va_exp=23.74 | TRIX 0-cross (short, 1h) va_exp=-99.45 |
| uptrend|at range high|messy|contracting | 107 | 6 | ADX/DMI DI-cross+ADX>thresh (long, 1h) va_exp=95.15 | MACD line/signal cross (short, 1h) va_exp=-67.40 |
| transition|at range low|messy|expanding | 122 | 5 | Camarilla pivots (reversion) (long, 1h) va_exp=48.64 | Aroon up/down cross (long, 1h) va_exp=-98.50 |
| uptrend|pulling back in trend|messy|stalling | 85 | 5 | Stochastic RSI extremes (short, 15m) va_exp=40.69 | Vortex VI+/VI- cross (long, 1h) va_exp=-62.48 |
| transition|mid range|messy|expanding | 147 | 5 | Awesome Oscillator 0-cross (long, 1h) va_exp=58.62 | SMA cross (short, 1h) va_exp=-54.11 |
| transition|at range low|clean|expanding | 102 | 5 | TEMA cross (short, 15m) va_exp=13.87 | CCI extremes (long, 1h) va_exp=-71.75 |
| transition|at range low|clean|contracting | 75 | 5 | Stochastic RSI extremes (long, 1h) va_exp=88.15 | EMA cross (short, 1h) va_exp=-69.96 |
| downtrend|pulling back in trend|messy|stalling | 85 | 5 | Fisher Transform 0-cross (long, 1h) va_exp=36.93 | Momentum 0-cross (short, 1h) va_exp=-104.95 |
| downtrend|at range low|clean|expanding | 86 | 5 | OBV trend (vs own MA) (long, 15m) va_exp=46.97 | TSI 0-cross (short, 15m) va_exp=-40.45 |
| downtrend|at range low|clean|contracting | 60 | 5 | Parabolic SAR (long, 15m) va_exp=27.14 | VWAP session cross (long, 1h) va_exp=-72.08 |
| uptrend|at range high|clean|expanding | 87 | 4 | Stochastic RSI extremes (short, 1h) va_exp=20.34 | Momentum 0-cross (long, 1h) va_exp=-86.73 |
| uptrend|at range high|messy|stalling | 67 | 4 | VWAP fade band (short, 15m) va_exp=45.57 | Momentum 0-cross (long, 1h) va_exp=-91.45 |
| uptrend|at range low|messy|contracting | 24 | 4 | TSI 0-cross (short, 1h) va_exp=128.63 | ROC 0-cross (short, 1h) va_exp=-97.29 |
| transition|at range low|messy|contracting | 100 | 2 | Williams fractals (long, 1h) va_exp=45.44 | A/D line trend (vs own MA) (short, 1h) va_exp=-115.71 |
| downtrend|at range high|messy|contracting | 77 | 2 | Parabolic SAR (long, 15m) va_exp=30.22 | Volume oscillator confirm (long, 1h) va_exp=-87.89 |

### 15m realized cost floor

96 15m cells clear SURVIVOR. Fee share of gross edge (fees + friction + funding, as a fraction of gross pre-cost pnl) across those survivors: mean val fee share = 44.6%, median = 44.1%, worst = 95.9%. The project's own documented ~9bps realized one-way cost floor for 15m means any survivor whose fee share is pushing toward 50%+ of its gross edge is not a real edge, it is noise that hasn't been fully eaten by costs yet.

| indicator | direction | state | va_n | va_exp | tr_fee_share | va_fee_share |
|---|---|---|---|---|---|---|
| OBV trend (vs own MA) | long | downtrend|at range low|clean|expanding | 9 | 46.974 | 0.369 | 0.117 |
| VWAP fade band | short | uptrend|at range high|messy|stalling | 8 | 45.566 | 0.615 | 0.098 |
| Bollinger mean-revert | short | transition|at range high|clean|contracting | 8 | 41.427 | 0.758 | 0.134 |
| Stochastic RSI extremes | short | uptrend|pulling back in trend|messy|stalling | 17 | 40.691 | 0.430 | 0.132 |
| ADX/DMI DI-cross+ADX>thresh | long | downtrend|pulling back in trend|clean|contracting | 8 | 40.625 | 0.242 | 0.151 |
| EMA cross | short | transition|mid range|clean|expanding | 19 | 38.964 | 0.950 | 0.132 |
| Aroon up/down cross | long | uptrend|at range high|clean|contracting | 9 | 36.663 | 0.309 | 0.160 |
| Aroon oscillator 0-cross | long | uptrend|at range high|clean|contracting | 9 | 36.663 | 0.309 | 0.160 |
| Parabolic SAR | long | downtrend|at range high|messy|contracting | 16 | 30.222 | 0.568 | 0.202 |
| TEMA cross | long | transition|at range high|clean|contracting | 19 | 29.107 | 0.984 | 0.202 |
| Stochastic RSI extremes | short | uptrend|pulling back in trend|clean|contracting | 12 | 29.018 | 0.499 | 0.187 |
| Parabolic SAR | long | downtrend|at range low|clean|contracting | 11 | 27.139 | 0.611 | 0.217 |
| Chandelier exit | short | uptrend|pulling back in trend|clean|contracting | 33 | 23.979 | 0.994 | 0.232 |
| Fisher Transform 0-cross | short | downtrend|at range low|messy|contracting | 14 | 23.740 | 0.990 | 0.208 |
| ADX/DMI DI-cross+ADX>thresh | short | uptrend|at range high|messy|contracting | 8 | 23.706 | 0.395 | 0.213 |
| SMA cross | long | downtrend|pulling back in trend|messy|expanding | 14 | 23.503 | 0.629 | 0.252 |
| Parabolic SAR | short | transition|mid range|messy|stalling | 30 | 23.172 | 0.309 | 0.231 |
| OBV divergence | short | transition|at range high|clean|contracting | 9 | 21.052 | 0.568 | 0.223 |
| VWAP fade band | short | uptrend|pulling back in trend|messy|stalling | 12 | 20.461 | 0.329 | 0.233 |
| Awesome Oscillator 0-cross | long | downtrend|pulling back in trend|clean|expanding | 18 | 20.097 | 0.399 | 0.267 |
| Connors RSI extremes | short | transition|mid range|messy|expanding | 10 | 19.552 | 0.874 | 0.281 |
| RSI OB/OS | long | downtrend|at range low|clean|contracting | 8 | 19.235 | 0.450 | 0.287 |
| Bollinger breakout | long | uptrend|at range high|clean|expanding | 17 | 18.526 | 0.721 | 0.290 |
| EMA cross | long | uptrend|at range high|clean|contracting | 11 | 17.975 | 0.675 | 0.288 |
| RSI 50-cross | short | transition|at range low|clean|contracting | 21 | 16.713 | 0.842 | 0.291 |
| SMA cross | long | uptrend|at range high|messy|expanding | 19 | 16.447 | 0.895 | 0.315 |
| TSI 0-cross | long | transition|mid range|clean|contracting | 10 | 15.649 | 0.284 | 0.348 |
| MFI extremes | short | uptrend|at range high|messy|expanding | 36 | 15.351 | 0.958 | 0.327 |
| MACD line/signal cross | long | uptrend|at range high|messy|contracting | 19 | 14.383 | 0.759 | 0.367 |
| MACD histogram 0-cross | long | uptrend|at range high|messy|contracting | 19 | 14.383 | 0.759 | 0.367 |
| Williams %R extremes | long | downtrend|pulling back in trend|clean|expanding | 12 | 14.325 | 0.952 | 0.372 |
| Stochastic extremes | long | downtrend|pulling back in trend|clean|expanding | 12 | 14.325 | 0.952 | 0.372 |
| Linreg slope sign | short | uptrend|pulling back in trend|messy|stalling | 15 | 14.013 | 0.364 | 0.347 |
| TEMA cross | short | transition|at range low|clean|expanding | 54 | 13.870 | 0.734 | 0.353 |
| VWAP session cross | short | transition|at range high|clean|contracting | 12 | 13.684 | 0.457 | 0.354 |
| EMA cross | long | uptrend|at range high|messy|expanding | 20 | 13.628 | 0.682 | 0.367 |
| OBV trend (vs own MA) | short | downtrend|at range low|clean|contracting | 10 | 12.994 | 0.857 | 0.341 |
| VWAP fade band | long | transition|mid range|messy|stalling | 19 | 12.386 | 0.410 | 0.391 |
| MACD histogram 0-cross | short | transition|at range low|messy|expanding | 63 | 11.867 | 0.849 | 0.391 |
| MACD line/signal cross | short | transition|at range low|messy|expanding | 63 | 11.867 | 0.849 | 0.391 |
| MFI extremes | short | downtrend|at range high|messy|contracting | 14 | 11.763 | 0.991 | 0.383 |
| Awesome Oscillator 0-cross | short | uptrend|pulling back in trend|messy|contracting | 34 | 11.518 | 0.658 | 0.378 |
| VWAP session cross | long | downtrend|at range low|clean|expanding | 10 | 11.419 | 0.943 | 0.401 |
| Aroon oscillator 0-cross | long | downtrend|at range low|messy|contracting | 11 | 10.916 | 0.773 | 0.439 |
| Aroon up/down cross | long | downtrend|at range low|messy|contracting | 11 | 10.916 | 0.773 | 0.439 |
| TSI 0-cross | long | downtrend|pulling back in trend|clean|contracting | 15 | 10.050 | 0.737 | 0.450 |
| TSI 0-cross | short | transition|mid range|clean|expanding | 21 | 9.948 | 0.683 | 0.409 |
| Bollinger breakout | long | transition|at range high|clean|expanding | 41 | 9.834 | 0.614 | 0.444 |
| DEMA cross | long | uptrend|at range high|messy|expanding | 27 | 9.683 | 0.351 | 0.456 |
| Force Index 0-cross | long | downtrend|pulling back in trend|clean|contracting | 42 | 9.512 | 0.895 | 0.457 |
| Vortex VI+/VI- cross | long | uptrend|pulling back in trend|clean|expanding | 37 | 9.367 | 0.814 | 0.464 |
| EMA cross | long | transition|at range high|clean|expanding | 36 | 9.278 | 0.996 | 0.463 |
| RSI 50-cross | long | transition|mid range|clean|contracting | 102 | 9.224 | 0.982 | 0.479 |
| Force Index 0-cross | short | transition|at range low|clean|contracting | 19 | 9.167 | 0.425 | 0.409 |
| TEMA cross | long | downtrend|at range low|clean|contracting | 17 | 9.098 | 0.973 | 0.465 |
| SuperTrend | short | downtrend|at range low|messy|expanding | 11 | 9.045 | 0.343 | 0.428 |
| ADX/DMI DI cross | long | transition|at range high|clean|contracting | 25 | 8.958 | 0.817 | 0.480 |
| VWAP fade band | short | transition|mid range|clean|expanding | 43 | 8.527 | 0.618 | 0.469 |
| MACD histogram 0-cross | short | transition|at range high|messy|expanding | 10 | 8.454 | 0.678 | 0.453 |
| MACD line/signal cross | short | transition|at range high|messy|expanding | 10 | 8.454 | 0.678 | 0.453 |
| RSI 50-cross | short | uptrend|at range high|messy|contracting | 13 | 8.069 | 0.474 | 0.469 |
| CCI extremes | short | uptrend|pulling back in trend|messy|expanding | 24 | 7.724 | 0.816 | 0.480 |
| ADX/DMI DI-cross+ADX>thresh | short | uptrend|pulling back in trend|clean|expanding | 36 | 7.509 | 0.297 | 0.501 |
| RSI 50-cross | long | uptrend|at range high|clean|contracting | 12 | 7.455 | 0.981 | 0.515 |
| Williams fractals | short | uptrend|at range high|messy|stalling | 48 | 7.209 | 0.930 | 0.496 |
| DEMA cross | short | transition|at range low|messy|expanding | 53 | 7.003 | 0.950 | 0.511 |
| Stochastic extremes | long | transition|mid range|messy|contracting | 53 | 6.484 | 0.585 | 0.561 |
| Williams %R extremes | long | transition|mid range|messy|contracting | 53 | 6.484 | 0.585 | 0.561 |
| Force Index 0-cross | short | uptrend|at range high|clean|expanding | 11 | 6.402 | 0.942 | 0.470 |
| Momentum 0-cross | long | downtrend|at range low|clean|expanding | 24 | 6.351 | 0.628 | 0.569 |
| VWAP session cross | short | transition|at range low|clean|expanding | 52 | 6.261 | 0.747 | 0.560 |
| Aroon up/down cross | long | transition|at range high|clean|contracting | 30 | 5.882 | 0.501 | 0.589 |
| Aroon oscillator 0-cross | long | transition|at range high|clean|contracting | 30 | 5.882 | 0.501 | 0.589 |
| A/D line trend (vs own MA) | long | transition|at range high|clean|expanding | 52 | 5.601 | 0.483 | 0.597 |
| DEMA cross | long | transition|at range high|messy|contracting | 27 | 5.597 | 0.425 | 0.587 |
| Williams fractals | long | transition|at range high|clean|expanding | 85 | 5.568 | 0.853 | 0.597 |
| RSI 50-cross | short | transition|at range high|messy|expanding | 27 | 5.449 | 0.946 | 0.584 |
| SMA cross | short | transition|mid range|clean|contracting | 25 | 5.381 | 0.425 | 0.560 |
| Linreg slope sign | short | downtrend|at range low|messy|contracting | 9 | 5.130 | 0.628 | 0.594 |
| TEMA cross | long | uptrend|at range high|clean|contracting | 12 | 4.679 | 0.247 | 0.645 |
| ROC 0-cross | short | transition|at range low|clean|expanding | 67 | 4.200 | 0.984 | 0.642 |
| RSI 50-cross | short | transition|at range low|clean|expanding | 60 | 3.928 | 0.793 | 0.649 |
| BB-inside-KC squeeze release | long | downtrend|at range high|messy|expanding | 23 | 3.508 | 0.469 | 0.703 |
| A/D line trend (vs own MA) | short | uptrend|at range high|messy|stalling | 24 | 2.867 | 0.472 | 0.725 |
| RSI OB/OS | short | uptrend|at range high|messy|stalling | 10 | 2.739 | 0.332 | 0.742 |
| Momentum 0-cross | long | transition|mid range|clean|contracting | 97 | 2.737 | 0.568 | 0.747 |
| Vortex VI+/VI- cross | short | transition|at range high|clean|expanding | 10 | 2.423 | 0.454 | 0.767 |
| ADX/DMI DI-cross+ADX>thresh | short | transition|at range high|messy|contracting | 10 | 2.322 | 0.897 | 0.782 |
| Stochastic extremes | short | transition|mid range|clean|expanding | 45 | 2.236 | 0.704 | 0.768 |
| Williams %R extremes | short | transition|mid range|clean|expanding | 45 | 2.236 | 0.704 | 0.768 |
| A/D line trend (vs own MA) | short | downtrend|at range low|clean|contracting | 25 | 2.211 | 0.996 | 0.774 |
| VWAP session cross | short | uptrend|at range high|messy|expanding | 29 | 2.101 | 0.530 | 0.782 |
| Chandelier exit | short | transition|at range low|clean|expanding | 60 | 1.764 | 0.865 | 0.812 |
| ADX/DMI DI-cross+ADX>thresh | long | uptrend|at range high|clean|contracting | 22 | 1.371 | 0.538 | 0.857 |
| Fisher Transform 0-cross | long | transition|at range high|clean|expanding | 33 | 1.237 | 0.483 | 0.871 |
| Fisher Transform 0-cross | long | transition|mid range|clean|contracting | 59 | 0.350 | 0.944 | 0.959 |

## Part 3 — Does the eye actually help? The three-way comparison

For every indicator, its single BEST eye-state (selected on TRAIN only, read on VAL, minimum 20 train trades) is compared against three alternatives: (i) the indicator UNGATED — R76's own published number for the identical config/tf; (ii) itself, this column, the eye-gated result; (iii) the SAME indicator gated by the project's existing crude proxy — `adaptive_vol_gate` (ATR% above/below its trailing 365-day median), direction also chosen on train; and (iv) a DUMB-GATE CONTROL — 20 random draws from OTHER populated states with a matched train trade count, same indicator/direction, reporting the mean/median val expectancy of the draws and what fraction of them the eye's chosen state actually beats.

| family | indicator | tf | eye_direction | eye_state | eye_va_n | eye_va_exp | eye_verdict | ungated_va_exp | ungated_verdict | atr_va_exp | control_mean_va_exp | control_pct_beat_eye | beats_ungated | beats_atr_gate | beats_control_mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| trend | MACD histogram 0-cross | 1h | long | uptrend|pulling back in trend|messy|expanding | 4 | 147.505 | UNRELIABLE | -3.865 | FAIL | 11.996 | -36.696 | 0.000 | True | True | True |
| trend | MACD line/signal cross | 1h | long | uptrend|pulling back in trend|messy|expanding | 4 | 147.505 | UNRELIABLE | -3.865 | FAIL | 11.996 | -13.739 | 0.000 | True | True | True |
| volume | CMF 0-cross | 1h | long | uptrend|pulling back in trend|clean|contracting | 10 | 99.714 | SURVIVOR | -5.175 | FAIL | -3.844 | -16.225 | 0.050 | True | True | True |
| volume | Force Index 0-cross | 1h | short | downtrend|at range low|clean|expanding | 3 | 93.725 | UNRELIABLE | -4.142 | FAIL | -10.124 | -29.708 | 0.000 | True | True | True |
| volume | VWAP session cross | 1h | short | transition|at range high|clean|contracting | 6 | 83.069 | UNRELIABLE | -2.463 | FAIL | -1.832 | -21.340 | 0.000 | True | True | True |
| trend | Linreg slope sign | 1h | long | downtrend|at range high|messy|expanding | 21 | 67.651 | SURVIVOR | 2.803 | SURVIVOR | -13.952 | 2.733 | 0.100 | True | True | True |
| trend | SuperTrend | 1h | short | uptrend|at range low|messy|expanding | 10 | 52.855 | SURVIVOR | -19.647 | FAIL | -1.649 |  |  | True | True | False |
| volatility | Chandelier exit | 15m | short | transition|at range high|messy|contracting | 3 | 47.993 | UNRELIABLE | -2.251 | FAIL | -9.526 | -1.314 | 0.000 | True | True | True |
| volume | OBV trend (vs own MA) | 15m | long | downtrend|at range low|clean|expanding | 9 | 46.974 | SURVIVOR | -1.669 | FAIL | -7.919 | -6.747 | 0.000 | True | True | True |
| momentum | RSI 50-cross | 15m | short | transition|at range high|clean|contracting | 7 | 46.356 | UNRELIABLE | -1.621 | FAIL | -7.694 | -4.229 | 0.050 | True | True | True |
| momentum | Stochastic %K/%D cross | 1h | long | downtrend|pulling back in trend|messy|expanding | 64 | 42.315 | SURVIVOR | -2.090 | FAIL | -11.257 | 0.407 | 0.100 | True | True | True |
| trend | KAMA cross | 1h | long | downtrend|at range high|messy|expanding | 21 | 40.769 | SURVIVOR | -2.886 | FAIL | 26.073 | -22.600 | 0.150 | True | True | True |
| trend | TRIX 0-cross | 1h | short | downtrend|pulling back in trend|messy|contracting | 5 | 40.742 | UNRELIABLE | -5.026 | FAIL | -6.962 | 2.579 | 0.200 | True | True | True |
| trend | ADX/DMI DI-cross+ADX>thresh | 15m | long | downtrend|pulling back in trend|clean|contracting | 8 | 40.625 | SURVIVOR | -1.456 | FAIL | -4.631 | -3.472 | 0.000 | True | True | True |
| volume | VWAP fade band | 1h | long | transition|mid range|messy|contracting | 9 | 36.925 | SURVIVOR | -6.669 | FAIL | -18.131 | -23.174 | 0.150 | True | True | True |
| volatility | Stdev channel mean-revert | 15m | short | transition|at range high|messy|expanding | 5 | 36.850 | UNRELIABLE | -4.629 | FAIL | -8.243 | -36.286 | 0.100 | True | True | True |
| trend | Aroon up/down cross | 15m | long | uptrend|at range high|clean|contracting | 9 | 36.663 | SURVIVOR | -2.517 | FAIL | -3.187 | -18.084 | 0.000 | True | True | True |
| trend | Aroon oscillator 0-cross | 15m | long | uptrend|at range high|clean|contracting | 9 | 36.663 | SURVIVOR | -2.517 | FAIL | -3.187 | -11.068 | 0.000 | True | True | True |
| volume | Ease of Movement 0-cross | 1h | long | transition|at range low|clean|expanding | 6 | 36.035 | UNRELIABLE | -1.807 | FAIL | -12.410 | -12.367 | 0.000 | True | True | True |
| volatility | Keltner breakout | 15m | long | uptrend|at range high|clean|expanding | 7 | 31.492 | UNRELIABLE | -0.544 | FAIL | -11.706 | -5.689 | 0.150 | True | True | True |
| momentum | CCI extremes | 15m | long | uptrend|pulling back in trend|clean|contracting | 7 | 31.377 | UNRELIABLE | -1.899 | FAIL | -7.653 | -18.000 | 0.000 | True | True | True |
| volume | OBV trend (vs own MA) | 1h | short | downtrend|at range low|clean|expanding | 6 | 26.861 | UNRELIABLE | -0.484 | FAIL | 1.582 | -24.740 | 0.150 | True | True | True |
| volume | Force Index 0-cross | 15m | short | uptrend|at range high|clean|contracting | 7 | 24.516 | UNRELIABLE | -1.741 | FAIL | -5.840 | -3.979 | 0.000 | True | True | True |
| trend | SMA cross | 15m | long | downtrend|pulling back in trend|clean|expanding | 7 | 22.210 | UNRELIABLE | -2.462 | FAIL | -7.242 | -5.184 | 0.000 | True | True | True |
| volume | MFI extremes | 1h | long | downtrend|at range low|messy|contracting | 12 | 21.425 | SURVIVOR | -2.313 | FAIL | -3.022 | -11.777 | 0.000 | True | True | True |
| volume | A/D line trend (vs own MA) | 1h | short | downtrend|at range low|clean|expanding | 13 | 21.080 | SURVIVOR | -5.610 | FAIL | -11.725 | -10.516 | 0.350 | True | True | True |
| volume | VWAP fade band | 15m | short | uptrend|pulling back in trend|messy|stalling | 12 | 20.461 | SURVIVOR | -3.581 | FAIL | -8.327 | -14.682 | 0.050 | True | True | True |
| momentum | Awesome Oscillator 0-cross | 15m | long | downtrend|pulling back in trend|clean|expanding | 18 | 20.097 | SURVIVOR | -1.676 | FAIL | -9.955 | -7.967 | 0.200 | True | True | True |
| momentum | ROC 0-cross | 1h | short | transition|at range high|messy|contracting | 10 | 18.519 | SURVIVOR | -1.832 | FAIL | -8.106 | 0.953 | 0.250 | True | True | True |
| momentum | Stochastic extremes | 1h | short | downtrend|pulling back in trend|clean|expanding | 10 | 15.040 | SURVIVOR | 0.796 | FAIL | 0.529 | -25.999 | 0.100 | True | True | True |
| momentum | Williams %R extremes | 1h | short | downtrend|pulling back in trend|clean|expanding | 10 | 15.040 | SURVIVOR | 0.796 | FAIL | 0.529 | -19.164 | 0.200 | True | True | True |
| trend | SMA cross | 1h | short | downtrend|pulling back in trend|messy|expanding | 3 | 12.553 | UNRELIABLE | -7.545 | FAIL | -23.200 | -6.129 | 0.200 | True | True | True |
| trend | TEMA cross | 1h | long | downtrend|pulling back in trend|messy|expanding | 29 | 10.270 | SURVIVOR | 3.760 | SURVIVOR | -3.791 | 1.749 | 0.250 | True | True | True |
| trend | DEMA cross | 15m | long | uptrend|at range high|messy|expanding | 27 | 9.683 | SURVIVOR | -2.542 | FAIL | -6.023 | -17.323 | 0.050 | True | True | True |
| trend | Vortex VI+/VI- cross | 1h | long | downtrend|pulling back in trend|clean|expanding | 17 | 6.981 | SURVIVOR | -0.953 | FAIL | -8.194 | -6.303 | 0.450 | True | True | True |
| levels | Williams fractals | 15m | long | transition|at range high|clean|expanding | 85 | 5.568 | SURVIVOR | -1.032 | FAIL | -4.539 | -8.589 | 0.150 | True | True | True |
| trend | TEMA cross | 15m | long | uptrend|at range high|clean|contracting | 12 | 4.679 | SURVIVOR | -2.384 | FAIL | -1.568 | -16.880 | 0.100 | True | True | True |
| trend | Hull MA cross | 1h | long | transition|at range high|clean|contracting | 10 | 4.575 | SURVIVOR | -2.396 | FAIL | -2.875 | -17.043 | 0.400 | True | True | True |
| trend | DEMA cross | 1h | long | downtrend|pulling back in trend|messy|contracting | 21 | 2.786 | SURVIVOR | -2.028 | FAIL | -17.146 | 2.982 | 0.100 | True | True | False |
| momentum | RSI OB/OS | 15m | short | uptrend|at range high|messy|stalling | 10 | 2.739 | SURVIVOR | -3.449 | FAIL | -17.887 | -11.950 | 0.300 | True | True | True |
| levels | Camarilla pivots (reversion) | 1h | short | uptrend|at range high|messy|expanding | 7 | 2.308 | UNRELIABLE | -9.982 | FAIL | 6.985 | -10.482 | 0.400 | True | False | True |
| trend | Parabolic SAR | 1h | long | downtrend|at range high|messy|expanding | 11 | -0.500 | FAIL | -3.910 | FAIL | -15.647 | 3.754 | 0.550 | True | True | False |
| trend | MACD histogram 0-cross | 15m | long | transition|at range high|clean|expanding | 51 | -2.144 | FAIL | -2.523 | FAIL | -3.141 | 2.219 | 0.500 | True | True | False |
| trend | MACD line/signal cross | 15m | long | transition|at range high|clean|expanding | 51 | -2.144 | FAIL | -2.523 | FAIL | -3.141 | -6.873 | 0.300 | True | True | True |
| volatility | Chandelier exit | 1h | short | transition|at range low|messy|contracting | 5 | -2.917 | UNRELIABLE | -4.333 | FAIL | -7.799 | 0.384 | 0.550 | True | True | False |
| momentum | Momentum 0-cross | 15m | short | transition|at range low|clean|expanding | 76 | -3.464 | FAIL | -1.289 | FAIL | -5.332 | -2.032 | 0.450 | False | True | False |
| volatility | Bollinger mean-revert | 15m | short | transition|at range high|messy|contracting | 7 | -6.629 | UNRELIABLE | -2.926 | FAIL | -3.578 | 12.545 | 0.650 | False | False | False |
| volume | Volume oscillator confirm | 15m | long | transition|at range high|clean|expanding | 54 | -7.603 | FAIL | -0.925 | FAIL | -5.793 | -14.863 | 0.150 | False | False | True |
| volume | A/D line trend (vs own MA) | 15m | short | transition|at range low|clean|contracting | 30 | -8.711 | FAIL | -1.672 | FAIL | -11.115 | -13.424 | 0.450 | False | True | True |
| levels | Camarilla pivots (reversion) | 15m | short | transition|at range high|messy|expanding | 6 | -8.713 | UNRELIABLE | -7.638 | FAIL | -10.619 | -20.440 | 0.200 | False | True | True |
| momentum | Stochastic %K/%D cross | 15m | long | downtrend|at range low|messy|expanding | 191 | -8.831 | FAIL | -0.550 | FAIL | -4.118 | -8.900 | 0.400 | False | False | True |
| momentum | RSI OB/OS | 1h | short | uptrend|at range high|clean|expanding | 5 | -9.160 | UNRELIABLE | -5.753 | FAIL | 4.271 | -4.821 | 0.350 | False | False | False |
| volume | Volume oscillator confirm | 1h | short | downtrend|at range low|clean|contracting | 18 | -9.703 | FAIL | -3.100 | FAIL | -3.784 | -5.075 | 0.600 | False | False | False |
| momentum | TSI 0-cross | 1h | long | downtrend|at range high|messy|expanding | 6 | -10.615 | UNRELIABLE | 3.432 | SURVIVOR | -0.096 | 30.635 | 0.650 | False | False | False |
| volume | Ease of Movement 0-cross | 15m | short | transition|at range low|clean|contracting | 102 | -11.191 | FAIL | -0.537 | FAIL | -8.430 | -8.995 | 0.400 | False | False | False |
| trend | Vortex VI+/VI- cross | 15m | short | transition|at range high|messy|contracting | 40 | -11.780 | FAIL | -1.749 | FAIL | -11.022 | -3.291 | 0.700 | False | False | False |
| levels | Williams fractals | 1h | short | transition|at range low|messy|contracting | 23 | -12.161 | FAIL | -3.422 | FAIL | -12.929 | -8.381 | 0.500 | False | True | False |
| momentum | Stochastic RSI extremes | 1h | long | uptrend|at range low|messy|contracting | 14 | -13.065 | FAIL | -2.144 | FAIL | -4.679 | -16.248 | 0.500 | False | False | True |
| trend | Linreg slope sign | 15m | short | downtrend|pulling back in trend|clean|expanding | 10 | -14.120 | FAIL | -2.647 | FAIL | -6.635 | -4.151 | 0.600 | False | False | False |
| volatility | BB-inside-KC squeeze release | 15m | long | transition|mid range|clean|contracting | 5 | -15.076 | UNRELIABLE | -3.530 | FAIL | -5.541 | -12.379 | 0.350 | False | False | False |
| trend | Hull MA cross | 15m | short | transition|at range low|clean|expanding | 68 | -15.420 | FAIL | -0.638 | FAIL | -10.356 | -6.754 | 0.900 | False | False | False |
| momentum | Stochastic extremes | 15m | long | transition|mid range|messy|stalling | 24 | -15.980 | FAIL | -1.355 | FAIL | -5.221 | -4.181 | 0.800 | False | False | False |
| momentum | Williams %R extremes | 15m | long | transition|mid range|messy|stalling | 24 | -15.980 | FAIL | -1.355 | FAIL | -5.221 | -3.584 | 0.850 | False | False | False |
| momentum | ROC 0-cross | 15m | short | uptrend|at range high|messy|stalling | 14 | -16.693 | FAIL | -1.451 | FAIL | -10.224 | -11.504 | 0.650 | False | False | False |
| momentum | TSI 0-cross | 15m | short | uptrend|pulling back in trend|clean|expanding | 10 | -17.084 | FAIL | -1.704 | FAIL | -8.195 | -11.691 | 0.550 | False | False | False |
| volume | VWAP session cross | 15m | short | uptrend|pulling back in trend|clean|expanding | 83 | -18.971 | FAIL | -1.581 | FAIL | -5.318 | -7.411 | 0.950 | False | False | False |
| momentum | CCI extremes | 1h | short | uptrend|at range high|messy|stalling | 15 | -19.052 | FAIL | -5.005 | FAIL | -9.227 | -25.662 | 0.500 | False | False | True |
| volatility | Bollinger mean-revert | 1h | long | transition|at range low|clean|expanding | 9 | -20.015 | FAIL | -8.237 | FAIL | -32.720 | 10.665 | 0.600 | False | True | False |
| volume | OBV divergence | 15m | short | downtrend|pulling back in trend|messy|contracting | 6 | -21.489 | UNRELIABLE | -3.549 | FAIL | -12.515 | -11.484 | 0.700 | False | False | False |
| volatility | Keltner mean-revert | 15m | short | transition|at range high|messy|expanding | 4 | -22.955 | UNRELIABLE | -6.272 | FAIL | -13.489 | -17.578 | 0.650 | False | False | False |
| momentum | RSI 50-cross | 1h | long | downtrend|pulling back in trend|clean|contracting | 15 | -23.234 | FAIL | -4.158 | FAIL | 7.046 | -45.338 | 0.150 | False | False | True |
| volume | MFI extremes | 15m | short | uptrend|at range high|messy|contracting | 36 | -23.436 | FAIL | -1.709 | FAIL | -12.623 | -6.986 | 0.850 | False | False | False |
| trend | Aroon up/down cross | 1h | long | transition|mid range|messy|stalling | 14 | -23.874 | FAIL | -1.783 | FAIL | -5.628 | -34.919 | 0.450 | False | False | True |
| trend | Aroon oscillator 0-cross | 1h | long | transition|mid range|messy|stalling | 14 | -23.874 | FAIL | -1.783 | FAIL | -5.628 | -8.588 | 0.850 | False | False | False |
| volatility | Bollinger breakout | 1h | long | uptrend|at range high|messy|expanding | 7 | -24.386 | UNRELIABLE | -1.850 | FAIL | -8.777 | -24.232 | 0.600 | False | False | False |
| trend | EMA cross | 15m | short | uptrend|pulling back in trend|clean|expanding | 11 | -25.092 | FAIL | -1.945 | FAIL | -11.167 | -1.477 | 0.850 | False | False | False |
| volume | CMF 0-cross | 15m | short | transition|at range low|messy|contracting | 47 | -27.868 | FAIL | -1.829 | FAIL | -8.622 | -6.111 | 1.000 | False | False | False |
| momentum | Momentum 0-cross | 1h | short | uptrend|pulling back in trend|clean|contracting | 13 | -31.163 | FAIL | -1.941 | FAIL | -8.820 | 9.874 | 0.700 | False | False | False |
| momentum | Stochastic RSI extremes | 15m | long | transition|at range high|clean|expanding | 8 | -33.729 | FAIL | -1.241 | FAIL | -2.447 | -4.791 | 1.000 | False | False | False |
| trend | KAMA cross | 15m | long | downtrend|at range low|clean|expanding | 14 | -33.980 | FAIL | -1.393 | FAIL | -5.645 | -13.220 | 0.850 | False | False | False |
| momentum | Ultimate Oscillator extremes | 15m | short | transition|at range high|clean|expanding | 8 | -34.578 | FAIL | -5.434 | FAIL | -5.181 | 26.478 | 0.950 | False | False | False |
| trend | Parabolic SAR | 15m | long | uptrend|pulling back in trend|clean|contracting | 8 | -38.540 | FAIL | -2.228 | FAIL | -3.231 | -4.930 | 1.000 | False | False | False |
| trend | ADX/DMI DI cross | 15m | short | uptrend|at range high|clean|contracting | 8 | -43.161 | FAIL | -1.965 | FAIL | -9.897 | -12.527 | 1.000 | False | False | False |
| volatility | Bollinger breakout | 15m | short | transition|at range low|clean|contracting | 8 | -43.361 | FAIL | -3.530 | FAIL | -13.121 | -29.007 | 0.600 | False | False | False |
| momentum | Connors RSI extremes | 15m | long | transition|at range low|clean|contracting | 9 | -45.637 | FAIL | -2.028 | FAIL | -7.593 | 9.078 | 1.000 | False | False | False |
| momentum | Fisher Transform 0-cross | 15m | long | uptrend|pulling back in trend|messy|stalling | 9 | -45.657 | FAIL | -2.113 | FAIL | -0.850 | -10.671 | 0.950 | False | False | False |
| momentum | Connors RSI extremes | 1h | long | uptrend|pulling back in trend|clean|expanding | 6 | -53.472 | UNRELIABLE | 4.561 | FAIL | -28.003 | -32.082 | 0.350 | False | False | False |
| trend | ADX/DMI DI cross | 1h | long | downtrend|pulling back in trend|messy|expanding | 16 | -57.425 | FAIL | -1.901 | FAIL | -3.758 | 9.208 | 0.950 | False | False | False |
| trend | TRIX 0-cross | 15m | short | uptrend|pulling back in trend|clean|contracting | 2 | -64.548 | UNRELIABLE | -2.531 | FAIL | -3.619 | -11.134 | 1.000 | False | False | False |
| trend | SuperTrend | 15m | short | downtrend|at range low|messy|contracting | 1 | -65.157 | UNRELIABLE | -2.075 | FAIL | -10.729 | 6.782 | 1.000 | False | False | False |
| momentum | Fisher Transform 0-cross | 1h | long | uptrend|at range high|messy|contracting | 8 | -66.773 | FAIL | -3.139 | FAIL | -7.837 | -19.639 | 1.000 | False | False | False |
| trend | ADX/DMI DI-cross+ADX>thresh | 1h | long | downtrend|pulling back in trend|messy|expanding | 7 | -67.986 | UNRELIABLE | -1.916 | FAIL | 2.953 | -7.660 | 0.750 | False | False | False |
| trend | EMA cross | 1h | long | downtrend|at range high|messy|expanding | 8 | -86.179 | FAIL | 2.835 | SURVIVOR | 1.556 | 12.552 | 1.000 | False | False | False |
| momentum | Awesome Oscillator 0-cross | 1h | short | downtrend|pulling back in trend|messy|expanding | 8 | -107.756 | FAIL | -4.578 | FAIL | -3.396 | -6.427 | 1.000 | False | False | False |
| volume | OBV divergence | 1h | short | transition|at range high|messy|expanding | 4 | -128.482 | UNRELIABLE | 19.259 | FAIL | -15.357 | -52.554 | 1.000 | False | False | False |
| volatility | BB-inside-KC squeeze release | 1h | short | transition|at range low|messy|contracting | 4 | -128.863 | UNRELIABLE | 0.192 | SURVIVOR | 5.271 | -7.980 | 1.000 | False | False | False |

**Verdict:** of 96 indicators compared, the eye-gated best state beats the ungated baseline in 45 cases, beats the ATR-percentile crude gate in 49 cases, and beats the random dumb-gate control's mean in 48 cases. **39 indicators beat all three** (ungated AND the crude proxy AND the random control) — this is the count that matters most: an indicator here is not just benefiting from being sliced into a smaller, cherrier sample (the control controls for that), it is being helped by KNOWING THE STATE specifically. **5 indicators beat the ungated baseline but did NOT beat the random control** — for these, the apparent improvement is most consistent with sample-slicing (any reasonably-sized subset would have looked about as good), not a genuine state-specific edge, and they are reported as such rather than counted as wins.

**The number above is inflated by tiny samples and needs one more cut.** Of the 39 that beat all three, most are riding val samples of 3-20 trades (visible in the table: eye_va_n) — exactly the regime the 20-train/8-val reliability floor exists to flag. Restricting to cells that ALSO cleared the SURVIVOR floor (not just UNRELIABLE-but-lucky): **23 of 25 SURVIVOR-grade indicators beat all three comparisons** — this smaller number is the one to actually trust, and it is the set used in 'How to use each indicator' below.


## ETH transfer — every BTC eye-gated SURVIVOR cell, replayed unchanged

289 BTC eye-gated SURVIVOR cells were replayed on ETH with the identical indicator, direction, and state definition (exit parameters recomputed from ETH's own train ATR%, exactly as R76's own ETH transfer convention does). **40 of 289 also clear SURVIVOR on ETH.** R76's own transfer check found only 2 of 94 BTC survivors transferred to ETH — this round's number is the same kind of brutal cross-asset filter, reported in full below, not cherry-picked.

| indicator | tf | direction | state | btc_tr_exp | btc_va_exp | eth_tr_n | eth_tr_exp | eth_va_n | eth_va_exp | eth_verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| DEMA cross | 1h | short | uptrend|at range low|messy|expanding | 56.376 | 207.683 | 26 | 40.796 | 13 | 52.614 | SURVIVOR |
| MACD line/signal cross | 1h | short | uptrend|at range low|messy|expanding | 10.930 | 180.983 | 31 | 51.390 | 15 | 46.764 | SURVIVOR |
| MACD histogram 0-cross | 1h | short | uptrend|at range low|messy|expanding | 10.930 | 180.983 | 31 | 51.390 | 15 | 46.764 | SURVIVOR |
| DEMA cross | 1h | long | downtrend|pulling back in trend|clean|expanding | 54.765 | 159.352 | 30 | -14.248 | 9 | 176.577 | FAIL |
| DEMA cross | 1h | long | transition|mid range|clean|expanding | 27.293 | 146.327 | 24 | -25.567 | 13 | 37.703 | FAIL |
| TSI 0-cross | 1h | short | uptrend|at range low|messy|contracting | 22.677 | 128.627 | 26 | 50.342 | 14 | 62.593 | SURVIVOR |
| Momentum 0-cross | 1h | short | uptrend|at range low|messy|expanding | 31.280 | 127.155 | 58 | 23.097 | 16 | 33.328 | SURVIVOR |
| TEMA cross | 1h | short | uptrend|at range low|messy|expanding | 40.568 | 126.715 | 23 | 14.220 | 13 | 59.042 | SURVIVOR |
| ROC 0-cross | 1h | short | uptrend|at range low|messy|expanding | 6.048 | 126.082 | 56 | 12.432 | 21 | 23.002 | SURVIVOR |
| ADX/DMI DI-cross+ADX>thresh | 1h | short | transition|mid range|messy|contracting | 2.893 | 121.903 | 29 | -22.910 | 9 | 40.115 | FAIL |
| CMF 0-cross | 1h | short | uptrend|at range low|messy|expanding | 20.339 | 110.780 | 28 | 50.935 | 17 | -15.447 | FAIL |
| ROC 0-cross | 1h | short | transition|at range high|messy|expanding | 30.487 | 104.270 | 31 | 8.269 | 7 | -31.143 | UNRELIABLE |
| CMF 0-cross | 1h | long | uptrend|pulling back in trend|clean|contracting | 61.892 | 99.714 | 24 | -58.608 | 6 | -78.026 | UNRELIABLE |
| ADX/DMI DI-cross+ADX>thresh | 1h | long | uptrend|at range high|messy|contracting | 18.287 | 95.154 | 29 | 14.970 | 8 | -27.044 | FAIL |
| KAMA cross | 1h | short | uptrend|at range low|messy|expanding | 7.254 | 88.261 | 58 | 33.706 | 21 | 16.115 | SURVIVOR |
| Stochastic RSI extremes | 1h | long | transition|at range low|clean|contracting | 15.714 | 88.148 | 15 | 13.921 | 4 | 49.944 | UNRELIABLE |
| Chandelier exit | 1h | short | uptrend|at range low|messy|expanding | 19.698 | 83.769 | 48 | 52.660 | 22 | -63.982 | FAIL |
| Aroon up/down cross | 1h | long | transition|at range high|messy|expanding | 11.658 | 73.832 | 60 | -7.393 | 22 | -63.138 | FAIL |
| Aroon oscillator 0-cross | 1h | long | transition|at range high|messy|expanding | 11.658 | 73.832 | 60 | -7.393 | 22 | -63.138 | FAIL |
| CMF 0-cross | 1h | long | transition|mid range|clean|expanding | 6.796 | 70.546 | 41 | -6.955 | 15 | 1.916 | FAIL |
| Parabolic SAR | 1h | short | uptrend|pulling back in trend|messy|contracting | 16.609 | 68.713 | 40 | 3.364 | 15 | 18.320 | SURVIVOR |
| Linreg slope sign | 1h | long | downtrend|at range high|messy|expanding | 39.907 | 67.651 | 27 | 0.191 | 10 | -74.121 | FAIL |
| Volume oscillator confirm | 1h | long | downtrend|at range high|messy|expanding | 11.701 | 63.722 | 47 | 38.123 | 15 | -80.206 | FAIL |
| Volume oscillator confirm | 1h | long | downtrend|pulling back in trend|messy|expanding | 14.266 | 61.112 | 110 | 7.403 | 38 | -38.316 | FAIL |
| Awesome Oscillator 0-cross | 1h | long | transition|mid range|messy|expanding | 26.440 | 58.621 | 34 | -41.358 | 13 | 26.811 | FAIL |
| ADX/DMI DI-cross+ADX>thresh | 1h | short | uptrend|at range low|messy|expanding | 7.378 | 57.651 | 31 | -22.863 | 18 | -41.091 | FAIL |
| ADX/DMI DI cross | 1h | long | transition|mid range|clean|expanding | 45.835 | 57.372 | 47 | -20.804 | 16 | -44.410 | FAIL |
| Fisher Transform 0-cross | 1h | long | downtrend|pulling back in trend|messy|expanding | 7.675 | 57.337 | 87 | 11.614 | 21 | 61.170 | SURVIVOR |
| Aroon oscillator 0-cross | 1h | long | downtrend|pulling back in trend|clean|expanding | 1.528 | 56.145 | 29 | -6.364 | 6 | 164.796 | UNRELIABLE |
| Aroon up/down cross | 1h | long | downtrend|pulling back in trend|clean|expanding | 1.528 | 56.145 | 29 | -6.364 | 6 | 164.796 | UNRELIABLE |
| ADX/DMI DI-cross+ADX>thresh | 1h | short | uptrend|pulling back in trend|messy|expanding | 7.914 | 54.559 | 36 | -23.270 | 13 | 23.445 | FAIL |
| OBV trend (vs own MA) | 1h | long | transition|mid range|clean|expanding | 3.014 | 53.443 | 52 | 1.005 | 15 | -3.586 | FAIL |
| SuperTrend | 1h | short | uptrend|at range low|messy|expanding | 15.117 | 52.855 | 17 | -18.491 | 9 | -47.122 | UNRELIABLE |
| A/D line trend (vs own MA) | 1h | short | uptrend|pulling back in trend|clean|contracting | 15.000 | 50.505 | 30 | -38.120 | 10 | -73.389 | FAIL |
| Camarilla pivots (reversion) | 1h | long | transition|at range low|messy|expanding | 14.338 | 48.639 | 45 | -37.714 | 15 | -3.475 | FAIL |
| RSI 50-cross | 1h | short | uptrend|at range low|messy|expanding | 7.061 | 48.289 | 56 | 25.052 | 27 | -18.172 | FAIL |
| TEMA cross | 1h | short | uptrend|pulling back in trend|messy|contracting | 30.746 | 47.589 | 64 | 0.095 | 23 | 6.896 | SURVIVOR |
| Stochastic %K/%D cross | 1h | short | uptrend|pulling back in trend|clean|expanding | 16.049 | 47.569 | 59 | 17.862 | 18 | 30.456 | SURVIVOR |
| ADX/DMI DI cross | 1h | short | uptrend|at range low|messy|expanding | 2.043 | 47.289 | 43 | -11.983 | 23 | 10.104 | FAIL |
| OBV trend (vs own MA) | 15m | long | downtrend|at range low|clean|expanding | 13.468 | 46.974 | 21 | 8.447 | 3 | -9.327 | UNRELIABLE |
| Stochastic %K/%D cross | 1h | long | downtrend|pulling back in trend|messy|contracting | 10.407 | 46.467 | 155 | -5.550 | 54 | 22.335 | FAIL |
| Stochastic extremes | 1h | long | downtrend|at range low|messy|expanding | 6.423 | 46.391 | 130 | -6.251 | 40 | 9.149 | FAIL |
| Williams %R extremes | 1h | long | downtrend|at range low|messy|expanding | 6.423 | 46.391 | 130 | -6.251 | 40 | 9.149 | FAIL |
| MACD histogram 0-cross | 1h | long | transition|mid range|messy|contracting | 15.994 | 46.265 | 60 | -7.425 | 19 | 46.128 | FAIL |
| MACD line/signal cross | 1h | long | transition|mid range|messy|contracting | 15.994 | 46.265 | 60 | -7.425 | 19 | 46.128 | FAIL |
| VWAP fade band | 15m | short | uptrend|at range high|messy|stalling | 4.675 | 45.566 | 21 | -18.494 | 11 | -57.542 | FAIL |
| Williams fractals | 1h | long | transition|at range low|messy|contracting | 2.753 | 45.442 | 116 | -35.585 | 46 | -29.528 | FAIL |
| Fisher Transform 0-cross | 1h | long | downtrend|pulling back in trend|clean|contracting | 1.544 | 45.150 | 33 | -39.398 | 8 | -46.921 | FAIL |
| Force Index 0-cross | 1h | long | uptrend|pulling back in trend|messy|expanding | 13.280 | 44.596 | 65 | -9.751 | 25 | -3.507 | FAIL |
| Fisher Transform 0-cross | 1h | short | uptrend|pulling back in trend|messy|expanding | 4.251 | 43.726 | 80 | -1.184 | 27 | -74.200 | FAIL |
| Hull MA cross | 1h | long | transition|at range low|messy|contracting | 5.176 | 43.175 | 139 | -32.268 | 49 | -51.379 | FAIL |
| Momentum 0-cross | 1h | short | downtrend|pulling back in trend|messy|expanding | 4.879 | 42.667 | 72 | -15.690 | 22 | -6.944 | FAIL |
| Stochastic %K/%D cross | 1h | long | downtrend|pulling back in trend|messy|expanding | 23.240 | 42.315 | 227 | -6.833 | 69 | 2.778 | FAIL |
| KAMA cross | 1h | long | transition|at range high|messy|expanding | 9.319 | 42.201 | 91 | -1.856 | 29 | 18.840 | FAIL |
| OBV trend (vs own MA) | 1h | short | uptrend|pulling back in trend|clean|contracting | 48.685 | 41.774 | 27 | 21.843 | 9 | 53.981 | SURVIVOR |
| Bollinger mean-revert | 15m | short | transition|at range high|clean|contracting | 2.252 | 41.427 | 26 | -21.343 | 10 | -75.665 | FAIL |
| KAMA cross | 1h | long | downtrend|at range high|messy|expanding | 43.661 | 40.769 | 61 | 3.651 | 23 | -61.130 | FAIL |
| Stochastic RSI extremes | 15m | short | uptrend|pulling back in trend|messy|stalling | 9.382 | 40.691 | 35 | -27.808 | 21 | 3.604 | FAIL |
| ADX/DMI DI-cross+ADX>thresh | 15m | long | downtrend|pulling back in trend|clean|contracting | 23.775 | 40.625 | 30 | 3.360 | 11 | -21.947 | FAIL |
| Aroon oscillator 0-cross | 1h | long | downtrend|pulling back in trend|messy|contracting | 8.391 | 39.523 | 43 | -40.303 | 18 | -38.887 | FAIL |
| Aroon up/down cross | 1h | long | downtrend|pulling back in trend|messy|contracting | 8.391 | 39.523 | 43 | -40.303 | 18 | -38.887 | FAIL |
| Stochastic extremes | 1h | long | uptrend|pulling back in trend|clean|expanding | 1.451 | 39.499 | 38 | -4.692 | 12 | -5.989 | FAIL |
| Williams %R extremes | 1h | long | uptrend|pulling back in trend|clean|expanding | 1.451 | 39.499 | 38 | -4.692 | 12 | -5.989 | FAIL |
| Chandelier exit | 1h | long | downtrend|at range high|messy|expanding | 4.139 | 39.413 | 52 | 34.198 | 10 | -12.454 | FAIL |
| EMA cross | 15m | short | transition|mid range|clean|expanding | 0.395 | 38.964 | 54 | -20.753 | 17 | -1.858 | FAIL |
| Volume oscillator confirm | 1h | short | uptrend|at range low|messy|expanding | 30.864 | 38.958 | 33 | -9.777 | 24 | -27.937 | FAIL |
| Stochastic RSI extremes | 1h | long | downtrend|pulling back in trend|clean|expanding | 10.338 | 38.791 | 9 | 57.324 | 4 | -154.038 | UNRELIABLE |
| Williams fractals | 1h | short | transition|at range high|messy|expanding | 17.594 | 37.720 | 39 | -8.698 | 20 | -10.289 | FAIL |
| RSI 50-cross | 1h | long | transition|mid range|messy|stalling | 9.443 | 37.333 | 39 | 14.698 | 17 | -22.378 | FAIL |
| Fisher Transform 0-cross | 1h | long | downtrend|pulling back in trend|messy|stalling | 33.535 | 36.925 | 26 | -12.169 | 9 | -148.409 | FAIL |
| VWAP fade band | 1h | long | transition|mid range|messy|contracting | 35.290 | 36.925 | 15 | -45.075 | 7 | 48.953 | UNRELIABLE |
| ROC 0-cross | 1h | long | transition|at range high|messy|expanding | 46.097 | 36.824 | 90 | 29.536 | 36 | -8.982 | FAIL |
| A/D line trend (vs own MA) | 1h | long | transition|mid range|messy|expanding | 15.624 | 36.761 | 127 | -15.089 | 24 | -20.380 | FAIL |
| Aroon oscillator 0-cross | 15m | long | uptrend|at range high|clean|contracting | 18.488 | 36.663 | 13 | 38.841 | 5 | 4.349 | UNRELIABLE |
| Aroon up/down cross | 15m | long | uptrend|at range high|clean|contracting | 18.488 | 36.663 | 13 | 38.841 | 5 | 4.349 | UNRELIABLE |
| OBV trend (vs own MA) | 1h | short | transition|at range high|messy|expanding | 0.220 | 36.452 | 44 | 8.101 | 15 | -44.094 | FAIL |
| Momentum 0-cross | 1h | short | transition|at range high|messy|expanding | 8.068 | 34.697 | 24 | -20.119 | 10 | -7.082 | FAIL |
| A/D line trend (vs own MA) | 1h | long | downtrend|pulling back in trend|messy|expanding | 29.380 | 34.535 | 107 | 37.490 | 37 | -48.515 | FAIL |
| VWAP session cross | 1h | long | downtrend|pulling back in trend|clean|contracting | 6.778 | 34.416 | 63 | -38.974 | 8 | 3.395 | FAIL |
| ROC 0-cross | 1h | long | downtrend|pulling back in trend|clean|expanding | 24.021 | 33.886 | 40 | -7.343 | 20 | 53.004 | FAIL |
| Ease of Movement 0-cross | 1h | short | uptrend|at range low|messy|contracting | 0.452 | 33.882 | 75 | -21.895 | 20 | -44.289 | FAIL |
| MACD histogram 0-cross | 1h | short | uptrend|pulling back in trend|clean|contracting | 59.681 | 33.212 | 23 | -9.164 | 8 | -34.512 | FAIL |
| MACD line/signal cross | 1h | short | uptrend|pulling back in trend|clean|contracting | 59.681 | 33.212 | 23 | -9.164 | 8 | -34.512 | FAIL |
| Hull MA cross | 1h | long | downtrend|at range high|messy|expanding | 3.764 | 32.759 | 65 | 22.728 | 28 | -51.029 | FAIL |
| Linreg slope sign | 1h | short | downtrend|pulling back in trend|messy|contracting | 3.073 | 31.705 | 21 | 19.762 | 4 | 60.964 | UNRELIABLE |
| VWAP session cross | 1h | short | transition|at range high|messy|expanding | 29.433 | 30.270 | 51 | 20.214 | 23 | 14.408 | SURVIVOR |
| ADX/DMI DI cross | 1h | short | transition|mid range|messy|contracting | 8.750 | 30.252 | 75 | 11.938 | 21 | -11.646 | FAIL |
| Parabolic SAR | 15m | long | downtrend|at range high|messy|contracting | 6.709 | 30.222 | 49 | 1.887 | 14 | -10.148 | FAIL |
| OBV trend (vs own MA) | 1h | long | downtrend|pulling back in trend|messy|stalling | 5.202 | 30.057 | 32 | -38.440 | 7 | -80.683 | UNRELIABLE |
| TEMA cross | 15m | long | transition|at range high|clean|contracting | 0.142 | 29.107 | 36 | 6.582 | 14 | -31.659 | FAIL |
| Stochastic RSI extremes | 15m | short | uptrend|pulling back in trend|clean|contracting | 7.659 | 29.018 | 35 | -12.033 | 10 | 0.717 | FAIL |
| ADX/DMI DI cross | 1h | long | transition|at range high|messy|expanding | 6.176 | 28.500 | 64 | 11.656 | 32 | 10.056 | SURVIVOR |
| Momentum 0-cross | 1h | long | uptrend|pulling back in trend|messy|contracting | 2.759 | 28.484 | 67 | -19.969 | 29 | -22.550 | FAIL |
| VWAP session cross | 1h | long | downtrend|pulling back in trend|messy|expanding | 6.358 | 28.274 | 203 | 9.812 | 70 | 3.616 | SURVIVOR |
| OBV trend (vs own MA) | 1h | short | uptrend|at range low|messy|expanding | 0.326 | 27.537 | 32 | -30.017 | 20 | 16.042 | FAIL |
| Force Index 0-cross | 1h | long | uptrend|pulling back in trend|messy|contracting | 9.086 | 27.298 | 29 | 44.670 | 9 | -59.508 | FAIL |
| Parabolic SAR | 15m | long | downtrend|at range low|clean|contracting | 5.138 | 27.139 | 35 | -16.531 | 15 | 4.490 | FAIL |
| MACD line/signal cross | 1h | long | downtrend|pulling back in trend|clean|contracting | 23.096 | 26.996 | 30 | -56.395 | 6 | 64.290 | UNRELIABLE |
| MACD histogram 0-cross | 1h | long | downtrend|pulling back in trend|clean|contracting | 23.096 | 26.996 | 30 | -56.395 | 6 | 64.290 | UNRELIABLE |
| Parabolic SAR | 1h | long | downtrend|pulling back in trend|messy|contracting | 10.915 | 26.859 | 63 | 15.379 | 25 | -19.880 | FAIL |
| OBV trend (vs own MA) | 1h | long | downtrend|pulling back in trend|messy|contracting | 8.076 | 26.276 | 73 | -17.843 | 16 | -6.422 | FAIL |
| A/D line trend (vs own MA) | 1h | long | downtrend|at range low|clean|expanding | 26.036 | 26.133 | 16 | -71.995 | 5 | 53.500 | UNRELIABLE |
| VWAP fade band | 1h | short | downtrend|pulling back in trend|messy|expanding | 8.781 | 25.969 | 55 | 14.257 | 17 | -34.097 | FAIL |
| Momentum 0-cross | 1h | long | downtrend|pulling back in trend|clean|expanding | 3.594 | 24.726 | 64 | -16.049 | 13 | 34.399 | FAIL |
| Parabolic SAR | 1h | long | transition|mid range|clean|expanding | 9.205 | 24.216 | 40 | -48.024 | 16 | 6.585 | FAIL |
| Chandelier exit | 15m | short | uptrend|pulling back in trend|clean|contracting | 0.043 | 23.979 | 124 | -8.346 | 18 | 13.386 | FAIL |
| Fisher Transform 0-cross | 15m | short | downtrend|at range low|messy|contracting | 0.075 | 23.740 | 37 | -33.220 | 11 | 35.986 | FAIL |
| ADX/DMI DI-cross+ADX>thresh | 15m | short | uptrend|at range high|messy|contracting | 9.710 | 23.706 | 22 | -13.518 | 7 | 41.121 | UNRELIABLE |
| SMA cross | 15m | long | downtrend|pulling back in trend|messy|expanding | 4.575 | 23.503 | 61 | 7.727 | 12 | 8.057 | SURVIVOR |
| Stochastic RSI extremes | 1h | short | uptrend|at range high|messy|expanding | 10.982 | 23.430 | 119 | -29.292 | 41 | -32.832 | FAIL |
| Parabolic SAR | 15m | short | transition|mid range|messy|stalling | 15.632 | 23.172 | 67 | -26.389 | 25 | 4.274 | FAIL |
| Stochastic %K/%D cross | 1h | short | uptrend|at range low|messy|contracting | 3.281 | 23.142 | 68 | 3.818 | 16 | 33.942 | SURVIVOR |
| ADX/DMI DI cross | 1h | long | downtrend|at range high|messy|expanding | 24.368 | 22.636 | 48 | -9.944 | 19 | -15.437 | FAIL |
| Vortex VI+/VI- cross | 1h | long | transition|mid range|clean|expanding | 2.969 | 22.322 | 58 | -51.583 | 13 | -33.273 | FAIL |
| Momentum 0-cross | 1h | long | downtrend|pulling back in trend|messy|stalling | 4.176 | 21.817 | 53 | -14.473 | 21 | -4.102 | FAIL |
| MFI extremes | 1h | long | downtrend|at range low|messy|contracting | 31.795 | 21.425 | 30 | -12.110 | 11 | 2.353 | FAIL |
| A/D line trend (vs own MA) | 1h | short | downtrend|at range low|clean|expanding | 63.827 | 21.080 | 24 | -46.689 | 10 | 29.125 | FAIL |
| OBV divergence | 15m | short | transition|at range high|clean|contracting | 5.031 | 21.052 | 24 | -10.727 | 3 | -77.675 | UNRELIABLE |
| ROC 0-cross | 1h | short | transition|mid range|messy|stalling | 4.347 | 20.524 | 55 | -4.326 | 18 | 10.949 | FAIL |
| VWAP fade band | 15m | short | uptrend|pulling back in trend|messy|stalling | 15.628 | 20.461 | 14 | -16.038 | 8 | -25.304 | UNRELIABLE |
| Stochastic RSI extremes | 1h | short | uptrend|at range high|clean|expanding | 2.526 | 20.343 | 42 | -57.521 | 15 | 55.259 | FAIL |
| Awesome Oscillator 0-cross | 15m | long | downtrend|pulling back in trend|clean|expanding | 11.537 | 20.097 | 39 | 22.135 | 13 | 17.390 | SURVIVOR |
| Connors RSI extremes | 15m | short | transition|mid range|messy|expanding | 1.083 | 19.552 | 23 | -25.923 | 7 | 11.044 | UNRELIABLE |
| RSI OB/OS | 15m | long | downtrend|at range low|clean|contracting | 10.095 | 19.235 | 32 | 12.875 | 10 | 7.950 | SURVIVOR |
| Momentum 0-cross | 1h | long | transition|mid range|messy|expanding | 0.623 | 19.200 | 168 | -12.991 | 50 | 26.745 | FAIL |
| RSI 50-cross | 1h | long | downtrend|pulling back in trend|messy|expanding | 21.388 | 18.846 | 120 | 18.689 | 39 | -30.433 | FAIL |
| Bollinger breakout | 15m | long | uptrend|at range high|clean|expanding | 3.242 | 18.526 | 51 | 5.769 | 16 | -43.506 | FAIL |
| ROC 0-cross | 1h | short | transition|at range high|messy|contracting | 66.056 | 18.519 | 33 | -38.530 | 11 | -81.399 | FAIL |
| EMA cross | 15m | long | uptrend|at range high|clean|contracting | 4.264 | 17.975 | 31 | 13.429 | 11 | 44.873 | SURVIVOR |
| Linreg slope sign | 1h | long | downtrend|pulling back in trend|messy|expanding | 5.809 | 17.848 | 14 | -4.465 | 9 | -54.657 | UNRELIABLE |
| Ease of Movement 0-cross | 1h | short | transition|mid range|clean|contracting | 1.703 | 17.828 | 140 | -4.221 | 34 | -43.679 | FAIL |
| OBV trend (vs own MA) | 1h | long | downtrend|at range high|messy|expanding | 5.336 | 17.724 | 64 | 6.851 | 14 | -25.376 | FAIL |
| Vortex VI+/VI- cross | 1h | short | uptrend|pulling back in trend|messy|contracting | 3.100 | 17.422 | 80 | -19.496 | 31 | 16.448 | FAIL |
| CMF 0-cross | 1h | long | downtrend|at range high|messy|expanding | 56.103 | 17.314 | 33 | -12.826 | 9 | -6.342 | FAIL |
| VWAP session cross | 1h | short | uptrend|at range low|messy|expanding | 7.343 | 17.310 | 45 | 23.463 | 22 | 11.675 | SURVIVOR |
| RSI 50-cross | 15m | short | transition|at range low|clean|contracting | 1.397 | 16.713 | 49 | -18.763 | 21 | -23.796 | FAIL |
| ADX/DMI DI cross | 1h | long | uptrend|pulling back in trend|messy|expanding | 25.615 | 16.619 | 29 | -43.713 | 13 | -22.283 | FAIL |
| SMA cross | 15m | long | uptrend|at range high|messy|expanding | 1.022 | 16.447 | 68 | -14.623 | 17 | -35.889 | FAIL |
| Chandelier exit | 1h | long | transition|at range high|messy|contracting | 16.270 | 16.335 | 18 | -32.851 | 8 | -34.338 | UNRELIABLE |
| Hull MA cross | 1h | long | uptrend|pulling back in trend|messy|stalling | 2.610 | 16.170 | 33 | -37.896 | 19 | -70.858 | FAIL |
| Vortex VI+/VI- cross | 1h | long | transition|at range high|messy|contracting | 16.273 | 16.107 | 29 | -48.076 | 13 | 94.497 | FAIL |
| Stochastic RSI extremes | 1h | long | transition|at range high|messy|contracting | 0.963 | 16.088 | 22 | -33.921 | 6 | 134.748 | UNRELIABLE |
| Volume oscillator confirm | 1h | short | downtrend|pulling back in trend|messy|expanding | 8.162 | 15.889 | 83 | 8.116 | 39 | -58.249 | FAIL |
| CCI extremes | 1h | short | uptrend|at range high|clean|expanding | 1.513 | 15.723 | 44 | -5.635 | 11 | 6.284 | FAIL |
| TSI 0-cross | 15m | long | transition|mid range|clean|contracting | 19.566 | 15.649 | 29 | -20.371 | 5 | -28.169 | UNRELIABLE |
| Fisher Transform 0-cross | 1h | short | transition|at range low|clean|contracting | 22.838 | 15.608 | 19 | -53.594 | 5 | 18.758 | UNRELIABLE |
| CCI extremes | 1h | long | downtrend|at range low|messy|contracting | 32.458 | 15.492 | 34 | -2.519 | 10 | 47.494 | FAIL |
| MFI extremes | 15m | short | uptrend|at range high|messy|expanding | 0.349 | 15.351 | 116 | -14.318 | 40 | -28.113 | FAIL |
| Hull MA cross | 1h | long | downtrend|pulling back in trend|messy|expanding | 21.698 | 15.186 | 216 | -14.740 | 60 | -6.099 | FAIL |
| MACD histogram 0-cross | 1h | long | downtrend|pulling back in trend|messy|contracting | 33.272 | 15.168 | 84 | 14.681 | 19 | -0.077 | FAIL |
| MACD line/signal cross | 1h | long | downtrend|pulling back in trend|messy|contracting | 33.272 | 15.168 | 84 | 14.681 | 19 | -0.077 | FAIL |
| Williams %R extremes | 1h | short | downtrend|pulling back in trend|clean|expanding | 63.190 | 15.040 | 26 | -21.231 | 7 | -30.470 | UNRELIABLE |
| Stochastic extremes | 1h | short | downtrend|pulling back in trend|clean|expanding | 63.190 | 15.040 | 26 | -21.231 | 7 | -30.470 | UNRELIABLE |
| Linreg slope sign | 1h | short | uptrend|at range low|messy|contracting | 18.435 | 14.805 | 29 | -37.066 | 5 | -67.220 | UNRELIABLE |
| Ease of Movement 0-cross | 1h | long | transition|at range high|messy|expanding | 0.022 | 14.466 | 167 | -16.933 | 50 | 42.543 | FAIL |
| MACD line/signal cross | 15m | long | uptrend|at range high|messy|contracting | 2.734 | 14.383 | 44 | 0.199 | 19 | 25.368 | SURVIVOR |
| MACD histogram 0-cross | 15m | long | uptrend|at range high|messy|contracting | 2.734 | 14.383 | 44 | 0.199 | 19 | 25.368 | SURVIVOR |
| Williams %R extremes | 15m | long | downtrend|pulling back in trend|clean|expanding | 0.415 | 14.325 | 29 | -0.907 | 4 | -51.698 | UNRELIABLE |
| Stochastic extremes | 15m | long | downtrend|pulling back in trend|clean|expanding | 0.415 | 14.325 | 29 | -0.907 | 4 | -51.698 | UNRELIABLE |
| KAMA cross | 1h | short | transition|mid range|clean|contracting | 1.004 | 14.266 | 44 | 14.447 | 10 | 5.937 | SURVIVOR |
| Williams %R extremes | 1h | short | downtrend|pulling back in trend|messy|expanding | 10.245 | 14.223 | 69 | -26.091 | 18 | 4.441 | FAIL |
| Stochastic extremes | 1h | short | downtrend|pulling back in trend|messy|expanding | 10.245 | 14.223 | 69 | -26.091 | 18 | 4.441 | FAIL |
| Momentum 0-cross | 1h | long | transition|at range high|messy|expanding | 5.006 | 14.115 | 84 | -11.330 | 33 | -64.090 | FAIL |
| Linreg slope sign | 15m | short | uptrend|pulling back in trend|messy|stalling | 11.846 | 14.013 | 40 | -28.752 | 14 | -2.703 | FAIL |
| TEMA cross | 15m | short | transition|at range low|clean|expanding | 2.729 | 13.870 | 113 | 8.918 | 40 | 17.473 | SURVIVOR |
| Ease of Movement 0-cross | 1h | short | uptrend|at range low|messy|expanding | 2.610 | 13.848 | 55 | -22.245 | 30 | 16.525 | FAIL |
| Ease of Movement 0-cross | 1h | short | downtrend|at range low|messy|expanding | 13.179 | 13.773 | 151 | -17.542 | 55 | 1.735 | FAIL |
| KAMA cross | 1h | long | downtrend|pulling back in trend|messy|expanding | 21.039 | 13.715 | 164 | -7.134 | 56 | 8.797 | FAIL |
| VWAP session cross | 15m | short | transition|at range high|clean|contracting | 7.816 | 13.684 | 43 | 18.471 | 14 | -39.509 | FAIL |
| EMA cross | 15m | long | uptrend|at range high|messy|expanding | 3.742 | 13.628 | 59 | -24.431 | 21 | -15.135 | FAIL |
| Force Index 0-cross | 1h | long | transition|mid range|clean|expanding | 1.588 | 13.565 | 66 | -23.630 | 24 | -2.785 | FAIL |
| Momentum 0-cross | 1h | long | downtrend|pulling back in trend|messy|contracting | 12.280 | 13.025 | 137 | -6.817 | 40 | -10.710 | FAIL |
| OBV trend (vs own MA) | 15m | short | downtrend|at range low|clean|contracting | 1.269 | 12.994 | 30 | 11.848 | 7 | -18.843 | UNRELIABLE |
| CCI extremes | 1h | long | transition|at range low|messy|expanding | 9.058 | 12.819 | 133 | -36.332 | 41 | -25.419 | FAIL |
| Hull MA cross | 1h | short | uptrend|at range low|messy|expanding | 10.358 | 12.625 | 62 | 11.934 | 20 | 49.165 | SURVIVOR |
| VWAP fade band | 15m | long | transition|mid range|messy|stalling | 12.089 | 12.386 | 26 | -6.271 | 12 | -45.694 | FAIL |
| MACD histogram 0-cross | 1h | short | uptrend|at range high|messy|expanding | 1.389 | 12.084 | 26 | -53.853 | 8 | -17.532 | FAIL |
| MACD line/signal cross | 1h | short | uptrend|at range high|messy|expanding | 1.389 | 12.084 | 26 | -53.853 | 8 | -17.532 | FAIL |
| MACD line/signal cross | 15m | short | transition|at range low|messy|expanding | 1.439 | 11.867 | 151 | -9.991 | 46 | 6.602 | FAIL |
| MACD histogram 0-cross | 15m | short | transition|at range low|messy|expanding | 1.439 | 11.867 | 151 | -9.991 | 46 | 6.602 | FAIL |
| MFI extremes | 15m | short | downtrend|at range high|messy|contracting | 0.064 | 11.763 | 37 | -20.776 | 13 | 21.970 | FAIL |
| Awesome Oscillator 0-cross | 15m | short | uptrend|pulling back in trend|messy|contracting | 3.923 | 11.518 | 89 | 7.004 | 26 | -0.822 | FAIL |
| VWAP session cross | 15m | long | downtrend|at range low|clean|expanding | 0.465 | 11.419 | 20 | 18.775 | 8 | -53.030 | FAIL |
| VWAP session cross | 1h | long | uptrend|pulling back in trend|messy|expanding | 0.927 | 11.364 | 115 | -3.113 | 52 | 5.536 | FAIL |
| ROC 0-cross | 1h | long | uptrend|pulling back in trend|messy|expanding | 12.347 | 11.287 | 68 | -30.148 | 29 | -0.949 | FAIL |
| ROC 0-cross | 1h | long | downtrend|pulling back in trend|messy|expanding | 6.495 | 11.012 | 152 | 34.513 | 31 | -19.640 | FAIL |
| Aroon up/down cross | 15m | long | downtrend|at range low|messy|contracting | 2.357 | 10.916 | 26 | -10.196 | 5 | -36.821 | UNRELIABLE |
| Aroon oscillator 0-cross | 15m | long | downtrend|at range low|messy|contracting | 2.357 | 10.916 | 26 | -10.196 | 5 | -36.821 | UNRELIABLE |
| Force Index 0-cross | 1h | short | uptrend|pulling back in trend|messy|expanding | 7.374 | 10.504 | 149 | 3.518 | 52 | 44.287 | SURVIVOR |
| A/D line trend (vs own MA) | 1h | long | downtrend|at range high|messy|expanding | 40.535 | 10.350 | 30 | -18.923 | 10 | -73.527 | FAIL |
| TEMA cross | 1h | long | downtrend|pulling back in trend|messy|expanding | 69.472 | 10.270 | 87 | 41.033 | 39 | -33.353 | FAIL |
| TSI 0-cross | 15m | long | downtrend|pulling back in trend|clean|contracting | 3.077 | 10.050 | 18 | 16.092 | 7 | 40.810 | UNRELIABLE |
| A/D line trend (vs own MA) | 1h | long | transition|mid range|clean|expanding | 1.666 | 9.961 | 68 | -24.997 | 21 | 16.460 | FAIL |
| TSI 0-cross | 15m | short | transition|mid range|clean|expanding | 3.569 | 9.948 | 56 | -17.258 | 15 | -5.515 | FAIL |
| ROC 0-cross | 1h | long | downtrend|pulling back in trend|messy|contracting | 0.380 | 9.838 | 102 | 11.282 | 46 | -21.115 | FAIL |
| Bollinger breakout | 15m | long | transition|at range high|clean|expanding | 5.316 | 9.834 | 76 | -4.323 | 34 | -16.033 | FAIL |
| DEMA cross | 15m | long | uptrend|at range high|messy|expanding | 14.569 | 9.683 | 74 | -21.965 | 19 | -2.079 | FAIL |
| Momentum 0-cross | 1h | long | transition|at range high|messy|contracting | 22.001 | 9.657 | 53 | -11.909 | 15 | -64.582 | FAIL |
| CMF 0-cross | 1h | short | downtrend|pulling back in trend|messy|contracting | 1.954 | 9.605 | 59 | -4.345 | 16 | 46.102 | FAIL |
| Force Index 0-cross | 15m | long | downtrend|pulling back in trend|clean|contracting | 1.011 | 9.512 | 99 | -7.072 | 36 | -3.499 | FAIL |
| ADX/DMI DI cross | 1h | short | transition|mid range|clean|expanding | 8.027 | 9.499 | 41 | 37.103 | 10 | 23.722 | SURVIVOR |
| Vortex VI+/VI- cross | 15m | long | uptrend|pulling back in trend|clean|expanding | 2.030 | 9.367 | 84 | -12.521 | 29 | -13.795 | FAIL |
| TEMA cross | 1h | long | transition|mid range|messy|contracting | 30.563 | 9.288 | 58 | -1.473 | 20 | 39.750 | FAIL |
| EMA cross | 15m | long | transition|at range high|clean|expanding | 0.034 | 9.278 | 94 | -16.695 | 35 | -34.081 | FAIL |
| RSI 50-cross | 15m | long | transition|mid range|clean|contracting | 0.154 | 9.224 | 212 | -13.773 | 76 | 7.536 | FAIL |
| Force Index 0-cross | 15m | short | transition|at range low|clean|contracting | 9.504 | 9.167 | 34 | 2.266 | 14 | -6.898 | FAIL |
| TEMA cross | 15m | long | downtrend|at range low|clean|contracting | 0.225 | 9.098 | 51 | -25.257 | 15 | -49.014 | FAIL |
| SuperTrend | 15m | short | downtrend|at range low|messy|expanding | 12.870 | 9.045 | 41 | 5.412 | 7 | 41.566 | UNRELIABLE |
| ADX/DMI DI cross | 15m | long | transition|at range high|clean|contracting | 1.912 | 8.958 | 55 | -14.294 | 20 | 12.184 | FAIL |
| Hull MA cross | 1h | long | downtrend|pulling back in trend|messy|stalling | 7.655 | 8.874 | 60 | 50.191 | 16 | 21.167 | SURVIVOR |
| Momentum 0-cross | 1h | long | downtrend|pulling back in trend|messy|expanding | 14.310 | 8.636 | 161 | 16.671 | 52 | 12.626 | SURVIVOR |
| VWAP fade band | 15m | short | transition|mid range|clean|expanding | 4.475 | 8.527 | 92 | -7.940 | 32 | -15.265 | FAIL |
| MACD line/signal cross | 15m | short | transition|at range high|messy|expanding | 3.661 | 8.454 | 43 | -29.587 | 13 | -14.221 | FAIL |
| MACD histogram 0-cross | 15m | short | transition|at range high|messy|expanding | 3.661 | 8.454 | 43 | -29.587 | 13 | -14.221 | FAIL |
| RSI 50-cross | 15m | short | uptrend|at range high|messy|contracting | 7.615 | 8.069 | 29 | -22.782 | 9 | 14.204 | FAIL |
| Volume oscillator confirm | 1h | long | downtrend|pulling back in trend|messy|contracting | 1.237 | 7.902 | 114 | -21.840 | 46 | 0.592 | FAIL |
| Hull MA cross | 1h | short | uptrend|pulling back in trend|clean|expanding | 15.483 | 7.898 | 58 | 19.856 | 17 | 21.623 | SURVIVOR |
| Williams fractals | 1h | long | downtrend|at range high|messy|expanding | 26.188 | 7.812 | 48 | 3.132 | 19 | -68.445 | FAIL |
| CCI extremes | 15m | short | uptrend|pulling back in trend|messy|expanding | 1.755 | 7.724 | 40 | 8.976 | 22 | -12.074 | FAIL |
| KAMA cross | 1h | short | uptrend|pulling back in trend|messy|expanding | 14.975 | 7.578 | 187 | -3.469 | 73 | 22.968 | FAIL |
| ADX/DMI DI-cross+ADX>thresh | 15m | short | uptrend|pulling back in trend|clean|expanding | 17.087 | 7.509 | 77 | 6.308 | 21 | 42.677 | SURVIVOR |
| RSI 50-cross | 15m | long | uptrend|at range high|clean|contracting | 0.158 | 7.455 | 28 | 10.979 | 7 | -19.272 | UNRELIABLE |
| Williams fractals | 1h | long | transition|at range high|messy|contracting | 14.652 | 7.447 | 76 | 18.963 | 32 | 32.548 | SURVIVOR |
| Volume oscillator confirm | 1h | long | uptrend|pulling back in trend|messy|expanding | 7.995 | 7.410 | 117 | -5.583 | 49 | 13.202 | FAIL |
| Williams fractals | 15m | short | uptrend|at range high|messy|stalling | 0.558 | 7.209 | 119 | -10.644 | 46 | -10.192 | FAIL |
| DEMA cross | 15m | short | transition|at range low|messy|expanding | 0.390 | 7.003 | 146 | 6.234 | 39 | 17.079 | SURVIVOR |
| Vortex VI+/VI- cross | 1h | long | downtrend|pulling back in trend|clean|expanding | 58.095 | 6.981 | 32 | 15.867 | 9 | 90.058 | SURVIVOR |
| Volume oscillator confirm | 1h | short | transition|mid range|messy|stalling | 3.851 | 6.664 | 36 | 16.616 | 15 | 50.639 | SURVIVOR |
| TEMA cross | 1h | long | downtrend|pulling back in trend|clean|expanding | 31.720 | 6.639 | 46 | -41.460 | 16 | 18.945 | FAIL |
| Williams %R extremes | 15m | long | transition|mid range|messy|contracting | 6.114 | 6.484 | 140 | -3.009 | 34 | 13.459 | FAIL |
| Stochastic extremes | 15m | long | transition|mid range|messy|contracting | 6.114 | 6.484 | 140 | -3.009 | 34 | 13.459 | FAIL |
| Force Index 0-cross | 15m | short | uptrend|at range high|clean|expanding | 0.455 | 6.402 | 32 | 9.155 | 13 | 1.645 | SURVIVOR |
| Momentum 0-cross | 15m | long | downtrend|at range low|clean|expanding | 4.944 | 6.351 | 44 | -12.748 | 11 | -21.605 | FAIL |
| VWAP session cross | 15m | short | transition|at range low|clean|expanding | 2.577 | 6.261 | 140 | -9.071 | 45 | 11.108 | FAIL |
| Aroon up/down cross | 15m | long | transition|at range high|clean|contracting | 8.385 | 5.882 | 73 | 1.567 | 24 | 21.099 | SURVIVOR |
| Aroon oscillator 0-cross | 15m | long | transition|at range high|clean|contracting | 8.385 | 5.882 | 73 | 1.567 | 24 | 21.099 | SURVIVOR |
| TEMA cross | 1h | long | downtrend|at range high|messy|expanding | 8.600 | 5.852 | 30 | 13.919 | 10 | -108.733 | FAIL |
| A/D line trend (vs own MA) | 15m | long | transition|at range high|clean|expanding | 9.328 | 5.601 | 131 | -14.760 | 52 | 2.297 | FAIL |
| DEMA cross | 15m | long | transition|at range high|messy|contracting | 11.303 | 5.597 | 66 | 8.649 | 15 | -0.627 | FAIL |
| Williams fractals | 15m | long | transition|at range high|clean|expanding | 1.559 | 5.568 | 220 | -0.522 | 69 | 2.580 | FAIL |
| Force Index 0-cross | 1h | short | uptrend|at range high|messy|expanding | 6.719 | 5.512 | 22 | 33.192 | 5 | 51.396 | UNRELIABLE |
| RSI 50-cross | 15m | short | transition|at range high|messy|expanding | 0.408 | 5.449 | 50 | -22.012 | 11 | 16.610 | FAIL |
| SMA cross | 15m | short | transition|mid range|clean|contracting | 10.358 | 5.381 | 57 | 0.390 | 17 | -10.790 | FAIL |
| Linreg slope sign | 15m | short | downtrend|at range low|messy|contracting | 4.622 | 5.130 | 30 | -20.302 | 7 | 11.023 | UNRELIABLE |
| TEMA cross | 1h | short | uptrend|pulling back in trend|messy|stalling | 9.049 | 5.092 | 34 | -37.328 | 7 | -44.690 | UNRELIABLE |
| Williams fractals | 1h | short | downtrend|at range low|messy|expanding | 0.943 | 4.971 | 86 | -45.353 | 28 | 7.949 | FAIL |
| Williams fractals | 1h | short | transition|at range low|clean|contracting | 10.034 | 4.890 | 18 | 64.305 | 11 | -47.860 | UNRELIABLE |
| TEMA cross | 15m | long | uptrend|at range high|clean|contracting | 23.565 | 4.679 | 30 | -4.527 | 6 | -53.295 | UNRELIABLE |
| Hull MA cross | 1h | long | transition|at range high|clean|contracting | 43.639 | 4.575 | 40 | -11.915 | 11 | -36.403 | FAIL |
| OBV trend (vs own MA) | 1h | short | downtrend|pulling back in trend|messy|expanding | 2.804 | 4.431 | 67 | 6.755 | 14 | -41.355 | FAIL |
| Parabolic SAR | 1h | long | downtrend|pulling back in trend|clean|expanding | 16.396 | 4.249 | 49 | -6.632 | 14 | 62.605 | FAIL |
| ROC 0-cross | 15m | short | transition|at range low|clean|expanding | 0.130 | 4.200 | 164 | -6.849 | 58 | -2.885 | FAIL |
| RSI 50-cross | 15m | short | transition|at range low|clean|expanding | 2.004 | 3.928 | 171 | -2.591 | 48 | 9.964 | FAIL |
| ADX/DMI DI-cross+ADX>thresh | 1h | long | transition|at range high|clean|expanding | 2.932 | 3.910 | 28 | 16.400 | 3 | 139.845 | UNRELIABLE |
| Vortex VI+/VI- cross | 1h | long | transition|mid range|messy|contracting | 3.874 | 3.906 | 136 | -17.020 | 41 | -9.907 | FAIL |
| Ease of Movement 0-cross | 1h | long | transition|at range high|clean|expanding | 2.283 | 3.850 | 41 | -58.741 | 13 | 36.002 | FAIL |
| Hull MA cross | 1h | short | transition|at range high|messy|contracting | 0.990 | 3.848 | 177 | -15.745 | 61 | -12.401 | FAIL |
| BB-inside-KC squeeze release | 15m | long | downtrend|at range high|messy|expanding | 9.248 | 3.508 | 43 | 35.641 | 11 | -0.742 | FAIL |
| Stochastic RSI extremes | 1h | short | downtrend|at range low|messy|expanding | 5.267 | 3.414 | 40 | -17.256 | 7 | 98.236 | UNRELIABLE |
| MFI extremes | 1h | short | transition|at range high|messy|expanding | 15.130 | 3.357 | 36 | 2.428 | 15 | -32.965 | FAIL |
| Ease of Movement 0-cross | 1h | short | transition|mid range|messy|stalling | 8.750 | 2.937 | 89 | -24.409 | 38 | 35.582 | FAIL |
| A/D line trend (vs own MA) | 15m | short | uptrend|at range high|messy|stalling | 7.774 | 2.867 | 52 | -19.425 | 27 | -4.058 | FAIL |
| Force Index 0-cross | 1h | long | downtrend|at range high|messy|expanding | 22.431 | 2.830 | 60 | 14.670 | 20 | -53.054 | FAIL |
| DEMA cross | 1h | long | downtrend|pulling back in trend|messy|contracting | 57.291 | 2.786 | 53 | -4.517 | 18 | -30.059 | FAIL |
| RSI OB/OS | 15m | short | uptrend|at range high|messy|stalling | 15.202 | 2.739 | 25 | -5.053 | 8 | -51.468 | FAIL |
| Momentum 0-cross | 15m | long | transition|mid range|clean|contracting | 6.485 | 2.737 | 240 | -13.245 | 87 | -0.396 | FAIL |
| ROC 0-cross | 1h | long | downtrend|pulling back in trend|messy|stalling | 17.111 | 2.573 | 44 | 24.848 | 11 | -40.339 | FAIL |
| ROC 0-cross | 1h | short | uptrend|pulling back in trend|messy|contracting | 15.145 | 2.465 | 95 | 7.155 | 40 | -23.142 | FAIL |
| Vortex VI+/VI- cross | 15m | short | transition|at range high|clean|expanding | 8.108 | 2.423 | 29 | -50.349 | 7 | -18.702 | UNRELIABLE |
| ADX/DMI DI-cross+ADX>thresh | 15m | short | transition|at range high|messy|contracting | 0.882 | 2.322 | 36 | 0.638 | 7 | -18.923 | UNRELIABLE |
| Stochastic extremes | 15m | short | transition|mid range|clean|expanding | 2.969 | 2.236 | 117 | -5.781 | 41 | -11.952 | FAIL |
| Williams %R extremes | 15m | short | transition|mid range|clean|expanding | 2.969 | 2.236 | 117 | -5.781 | 41 | -11.952 | FAIL |
| A/D line trend (vs own MA) | 15m | short | downtrend|at range low|clean|contracting | 0.029 | 2.211 | 67 | -9.186 | 19 | -23.146 | FAIL |
| VWAP session cross | 15m | short | uptrend|at range high|messy|expanding | 6.731 | 2.101 | 73 | 1.740 | 23 | -20.134 | FAIL |
| Chandelier exit | 15m | short | transition|at range low|clean|expanding | 1.239 | 1.764 | 168 | -0.988 | 46 | -0.258 | FAIL |
| SMA cross | 1h | long | uptrend|at range high|messy|contracting | 16.178 | 1.723 | 25 | -22.414 | 11 | 62.789 | FAIL |
| Ease of Movement 0-cross | 1h | long | downtrend|pulling back in trend|messy|expanding | 18.203 | 1.521 | 217 | -17.615 | 74 | -2.269 | FAIL |
| VWAP session cross | 1h | long | transition|mid range|messy|contracting | 10.930 | 1.407 | 170 | -5.317 | 52 | 16.228 | FAIL |
| ADX/DMI DI-cross+ADX>thresh | 15m | long | uptrend|at range high|clean|contracting | 7.649 | 1.371 | 56 | -20.296 | 15 | 15.500 | FAIL |
| Fisher Transform 0-cross | 15m | long | transition|at range high|clean|expanding | 8.927 | 1.237 | 96 | 5.509 | 39 | -6.414 | FAIL |
| Williams fractals | 1h | long | uptrend|pulling back in trend|clean|expanding | 2.802 | 1.137 | 25 | -75.938 | 6 | 10.409 | UNRELIABLE |
| Ease of Movement 0-cross | 1h | long | downtrend|pulling back in trend|clean|contracting | 21.656 | 0.832 | 90 | -28.130 | 27 | -3.355 | FAIL |
| Linreg slope sign | 1h | short | transition|mid range|messy|expanding | 8.922 | 0.773 | 64 | -36.962 | 16 | -0.579 | FAIL |
| RSI 50-cross | 1h | long | downtrend|at range high|messy|expanding | 34.157 | 0.450 | 66 | -3.200 | 25 | -44.131 | FAIL |
| Aroon oscillator 0-cross | 1h | short | transition|mid range|messy|stalling | 17.454 | 0.358 | 19 | 38.953 | 5 | -49.487 | UNRELIABLE |
| Aroon up/down cross | 1h | short | transition|mid range|messy|stalling | 17.454 | 0.358 | 19 | 38.953 | 5 | -49.487 | UNRELIABLE |
| Fisher Transform 0-cross | 15m | long | transition|mid range|clean|contracting | 0.524 | 0.350 | 148 | -18.586 | 55 | 2.503 | FAIL |
| ADX/DMI DI cross | 1h | short | uptrend|pulling back in trend|messy|expanding | 15.289 | 0.331 | 80 | -0.110 | 33 | -38.366 | FAIL |
| Vortex VI+/VI- cross | 1h | long | downtrend|pulling back in trend|clean|contracting | 43.086 | 0.316 | 28 | -54.344 | 14 | -79.798 | FAIL |

## How to use each indicator, per the evidence

Read against Part 3, not Part 2 alone (Part 2's raw best-state numbers are exactly the kind of single-cell cherry-pick the dumb-gate control exists to catch). An indicator only earns a real recommendation here if it beat ALL THREE comparisons in Part 3 AND (if it produced a BTC eye-gated SURVIVOR cell) also transferred to ETH.

- **CMF 0-cross (1h, long)** — take it only when the eye reads **uptrend|pulling back in trend|clean|contracting**. Val expectancy $99.71/trade over 10 trades, vs $-5.17 ungated and $-16.22 average random-state control. ETH UNRELIABLE (val exp $-78.03).
- **Linreg slope sign (1h, long)** — take it only when the eye reads **downtrend|at range high|messy|expanding**. Val expectancy $67.65/trade over 21 trades, vs $2.80 ungated and $2.73 average random-state control. ETH FAIL (val exp $-74.12).
- **OBV trend (vs own MA) (15m, long)** — take it only when the eye reads **downtrend|at range low|clean|expanding**. Val expectancy $46.97/trade over 9 trades, vs $-1.67 ungated and $-6.75 average random-state control. ETH UNRELIABLE (val exp $-9.33).
- **Stochastic %K/%D cross (1h, long)** — take it only when the eye reads **downtrend|pulling back in trend|messy|expanding**. Val expectancy $42.32/trade over 64 trades, vs $-2.09 ungated and $0.41 average random-state control. ETH FAIL (val exp $2.78).
- **KAMA cross (1h, long)** — take it only when the eye reads **downtrend|at range high|messy|expanding**. Val expectancy $40.77/trade over 21 trades, vs $-2.89 ungated and $-22.60 average random-state control. ETH FAIL (val exp $-61.13).
- **ADX/DMI DI-cross+ADX>thresh (15m, long)** — take it only when the eye reads **downtrend|pulling back in trend|clean|contracting**. Val expectancy $40.63/trade over 8 trades, vs $-1.46 ungated and $-3.47 average random-state control. ETH FAIL (val exp $-21.95).
- **VWAP fade band (1h, long)** — take it only when the eye reads **transition|mid range|messy|contracting**. Val expectancy $36.93/trade over 9 trades, vs $-6.67 ungated and $-23.17 average random-state control. ETH UNRELIABLE (val exp $48.95).
- **Aroon oscillator 0-cross (15m, long)** — take it only when the eye reads **uptrend|at range high|clean|contracting**. Val expectancy $36.66/trade over 9 trades, vs $-2.52 ungated and $-11.07 average random-state control. ETH UNRELIABLE (val exp $4.35).
- **Aroon up/down cross (15m, long)** — take it only when the eye reads **uptrend|at range high|clean|contracting**. Val expectancy $36.66/trade over 9 trades, vs $-2.52 ungated and $-18.08 average random-state control. ETH UNRELIABLE (val exp $4.35).
- **MFI extremes (1h, long)** — take it only when the eye reads **downtrend|at range low|messy|contracting**. Val expectancy $21.43/trade over 12 trades, vs $-2.31 ungated and $-11.78 average random-state control. ETH FAIL (val exp $2.35).
- **A/D line trend (vs own MA) (1h, short)** — take it only when the eye reads **downtrend|at range low|clean|expanding**. Val expectancy $21.08/trade over 13 trades, vs $-5.61 ungated and $-10.52 average random-state control. ETH FAIL (val exp $29.13).
- **VWAP fade band (15m, short)** — take it only when the eye reads **uptrend|pulling back in trend|messy|stalling**. Val expectancy $20.46/trade over 12 trades, vs $-3.58 ungated and $-14.68 average random-state control. ETH UNRELIABLE (val exp $-25.30).
- **Awesome Oscillator 0-cross (15m, long)** — take it only when the eye reads **downtrend|pulling back in trend|clean|expanding**. Val expectancy $20.10/trade over 18 trades, vs $-1.68 ungated and $-7.97 average random-state control. ETH SURVIVOR (val exp $17.39).
- **ROC 0-cross (1h, short)** — take it only when the eye reads **transition|at range high|messy|contracting**. Val expectancy $18.52/trade over 10 trades, vs $-1.83 ungated and $0.95 average random-state control. ETH FAIL (val exp $-81.40).
- **Williams %R extremes (1h, short)** — take it only when the eye reads **downtrend|pulling back in trend|clean|expanding**. Val expectancy $15.04/trade over 10 trades, vs $0.80 ungated and $-19.16 average random-state control. ETH UNRELIABLE (val exp $-30.47).
- **Stochastic extremes (1h, short)** — take it only when the eye reads **downtrend|pulling back in trend|clean|expanding**. Val expectancy $15.04/trade over 10 trades, vs $0.80 ungated and $-26.00 average random-state control. ETH UNRELIABLE (val exp $-30.47).
- **TEMA cross (1h, long)** — take it only when the eye reads **downtrend|pulling back in trend|messy|expanding**. Val expectancy $10.27/trade over 29 trades, vs $3.76 ungated and $1.75 average random-state control. ETH FAIL (val exp $-33.35).
- **DEMA cross (15m, long)** — take it only when the eye reads **uptrend|at range high|messy|expanding**. Val expectancy $9.68/trade over 27 trades, vs $-2.54 ungated and $-17.32 average random-state control. ETH FAIL (val exp $-2.08).
- **Vortex VI+/VI- cross (1h, long)** — take it only when the eye reads **downtrend|pulling back in trend|clean|expanding**. Val expectancy $6.98/trade over 17 trades, vs $-0.95 ungated and $-6.30 average random-state control. ETH SURVIVOR (val exp $90.06).
- **Williams fractals (15m, long)** — take it only when the eye reads **transition|at range high|clean|expanding**. Val expectancy $5.57/trade over 85 trades, vs $-1.03 ungated and $-8.59 average random-state control. ETH FAIL (val exp $2.58).
- **TEMA cross (15m, long)** — take it only when the eye reads **uptrend|at range high|clean|contracting**. Val expectancy $4.68/trade over 12 trades, vs $-2.38 ungated and $-16.88 average random-state control. ETH UNRELIABLE (val exp $-53.30).
- **Hull MA cross (1h, long)** — take it only when the eye reads **transition|at range high|clean|contracting**. Val expectancy $4.57/trade over 10 trades, vs $-2.40 ungated and $-17.04 average random-state control. ETH FAIL (val exp $-36.40).
- **RSI OB/OS (15m, short)** — take it only when the eye reads **uptrend|at range high|messy|stalling**. Val expectancy $2.74/trade over 10 trades, vs $-3.45 ungated and $-11.95 average random-state control. ETH FAIL (val exp $-51.47).

## Limitations — read before arguing with any number above

- **The vectorized eye is an approximation of the real one, not a copy.** `step82_eye.py` computes confirmed swing points ONCE across the whole series rather than re-windowing to the trailing 60 bars on every call (chart_reader's own per-bar behavior). This can only disagree at the very start of a 60-bar structure window, and it was checked directly: 600 random bars across BTC 1h, BTC 15m, ETH 1h, ETH 15m, comparing the vectorized label against the REAL `chart_reader.read_chart()` call — **100% agreement, all four axes, every sample.** Treat this as strong but not exhaustive evidence (600 samples across ~500k total bars).
- **Location was computed WITHOUT the daily/weekly cross-check** `read_chart()` uses live (prior_day/week high-low). Historical labeling here used local-range-only breakout detection. This makes 'breaking out'/'breaking down' slightly looser than the live system would call it — a real, acknowledged gap, not hidden.
- **One fixed exit convention was imposed on every indicator**, replacing each indicator's own textbook exit. This is what makes the matrix comparable cell-to-cell, but it is a real methodological choice: an indicator whose true edge is in ITS OWN exit logic (e.g. SuperTrend's trailing stop, Chandelier's ATR trail) is graded here on a DIFFERENT exit than the one that logic was designed around, and may look worse here than it did standalone in R76.
- **One config per indicator** (R76's own 'standard default'), not the full 2-3 parameter sweep — chosen for tractability given the state x direction x timeframe multiplication already produces 7,140 cells. A faster/slower parameter variant of a near-miss indicator here might behave differently gated; this was not tested.
- **The dumb-gate control draws from the SAME 51-indicator, populated-state universe** — it is a genuine multiple-comparisons control (same selection pressure the eye-gate is under), not an independent random-trading baseline.
- **Ichimoku (2 of R76's 53 indicators) is out of scope** — R76 only tested it on 4h, and this round's eye is labeled on 1h/15m only.
- **The eye itself remains ADVISORY_ONLY** (chart_reader.py's own hard safety flag) — nothing in this round changes that; this is research evidence for whether it's WORTH promoting past that gate, not a live signal.
- **Total runtime:** 1059s (17.6 min) end to end on cached data, no network calls — eye labeling is ~1s of that; the rest is the 7,140-cell backtest sweep.
