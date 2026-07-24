# step57_results.md — round 57: price-action patterns, order blocks, volatility compression (BTC)

Companion to `step57_price_action.py`. Research only — no live orders, no
commits, nothing else touched. Standard gauntlet throughout: chronological
60/20/20 split per timeframe (train->2024-01-10, val->2025-04-16, test
sealed and never touched by this script), CostModel defaults (6bps
taker/2bps maker, 1bp half-spread, 2bp slippage), execution="maker", REAL
funding via `align_funding`. Selection is by TRAIN expectancy only; val is
reported but never tuned against. Survivor = positive expectancy on BOTH
train and val, with >=30 train trades and >=8 val trades (same bar the
whole program has used since round 41/43).

Data: BTC 1h (55,451 bars, 2020-03-25 -> 2026-07-22) and 4h (13,863 bars,
same span) from the cached Bybit deep history, plus daily bars (for the
SMA50 context level) and real Bybit funding settlements. Train+val together
span ~5.06 years on both timeframes — that denominator is used for every
trades/yr figure below.

**296 configs run.** Verdict counts: 279 FAIL, 10 SURVIVOR, 7
INSUFFICIENT-SAMPLE (positive train+val expectancy but under the 30/8
trade floor — logged, not counted as passing).

Plumbing reused by import (not reimplemented): `split_points`,
`day_trade_signal`, `score`, `mk_row`, `verdict_for`, `champ_aligned`,
`CHAMP_KW`, `bar_hours`, `hours_to_bars` from `step43_daytrade.py`;
`adaptive_vol_gate` from `step41_shorts.py` (imported per the mandate;
this round's own compression families use bespoke trailing-percentile/
trailing-median gates built to the mandate's explicit spec instead, see
FAMILY 3 below for why the fixed-window gate wasn't the right tool here).

---

## 1. Formal definitions

### FAMILY 1 — ORDER BLOCKS (completes the SMC toolset)

- **Impulse**: |close-to-close move over `bars_move` in {1,3} bars| >=
  `mult` in {2,3} x the TRAIN-only median |1-bar return|% for that
  timeframe (1h baseline 0.246%, 4h baseline 0.496%).
- **Confirmed swing break** (mandatory): the impulse must close beyond the
  most recently CONFIRMED k=5 fractal swing extreme (a centered 11-bar
  window, confirmed — i.e. knowable — 5 bars later, same construction as
  step41's `confirmed_swings`). This is what makes an "impulse" structural
  rather than just a big candle.
- **Order block**: the last opposing-color candle before the impulse
  started (last bearish candle before an up-impulse = support block; last
  bullish candle before a down-impulse = resistance block), found by
  scanning backward from the impulse's first bar.
- **Entry**: first retracement into the block's range after the impulse,
  in the impulse direction. Two touch styles: `50pct` (price reaches the
  block's midpoint) or `sweep` (price trades through the block's FAR edge
  — the deeper, "liquidity sweep" entry). Search window capped at 48h (the
  same horizon as max_hold — an order block that's never revisited within
  48h is treated as invalidated for this study).
- **Stop**: past the block's far edge; TRAIN-only median of that per-event
  distance, held fixed for the run (repo's standard stop-distance
  approximation), capped at STOP_CAP_PCT=3.0%.
- **Target**: 2x or 3x the stop distance. **Max hold**: 48h (mandate-given).
- **BREAKER variant**: if price CLOSES through the block's far edge before
  ever touching the retracement level, the block has "failed" — it flips
  role, and entry is taken on the retest from the OTHER side (continuation
  of the break), in the OPPOSITE direction from the base variant.

Grid: mult{2,3} x bars_move{1,3} x touch{50pct,sweep} x tf{1h,4h} x
target_mult{2,3} x variant{base,breaker} = **64 configs**.

### FAMILY 2 — REJECTION CANDLES

**(a) Pin bars**: wick >= `wick_mult` in {2,3} x body, closing in the
outer 33% of the bar's range (bullish: lower wick, close in top 33%;
bearish: upper wick, close in bottom 33%), AT a context level — rolling
20-bar or 55-bar extreme (shift(1)'d, donchian-style) within 0.5%, OR
daily SMA50 within 0.5% (aligned onto 1h/4h at daily close + 1 day, same
causal merge_asof pattern as `champ_aligned`). A `none` context arm (no
level requirement at all) runs alongside every wick/stop/target
combination specifically for the required context-vs-no-context
comparison — see section 4.
Grid: wick_mult{2,3} x context{roll20,roll55,sma50,none} x tf{1h,4h} x
stop_mult{1.0,1.5}xATR x target_mult{2,3}xstop = **64 configs**.

**(b) Engulfing** at the same four context arms: today's body fully
engulfs yesterday's opposite-colored body (close beyond yesterday's open,
open beyond yesterday's close).
Grid: context{4} x tf{2} x stop_mult{2} x target_mult{2} = **32 configs**.

**(c) Inside-bar breakouts**: `inside_n` in {1,2} consecutive bars fully
contained inside a single "mother" bar's range, then trade the break of
the mother bar's high/low on the very next bar. Both with-trend-gated
(4h `vol_gated_ma` champion bias, {fast:20,slow:100,min_atr_pct:1.5} — the
same standing champion config used throughout the program) and ungated
("both" directions). Stop = TRAIN-only median mother-bar-range%
(structural, not ATR-scaled); target = 2x/3x that.
Grid: inside_n{2} x gate{2} x tf{2} x target_mult{2} = **16 configs**.

### FAMILY 3 — VOLATILITY COMPRESSION ("the squeeze")

**(a) NR4/NR7**: the bar with the single narrowest high-low range among
the trailing N bars (N in {4,7}); trade the very next bar's break of that
bar's high/low. Stop = stop_mult{1.0,1.5} x median ATR% (TRAIN); target
= target_mult{2,3} x stop.
Grid: N{2} x tf{2} x gate{2} x stop_mult{2} x target_mult{2} = **32 configs**.

**(b) Bollinger-bandwidth squeeze**: 20-bar Bollinger bandwidth
((upper-lower)/sma) in its own lowest 10th/20th percentile of its trailing
365-day distribution (rolling quantile, shift(1)'d so the current bar's
own bandwidth never leaks into its own reference distribution); enter on
close beyond the bands. Exit style: fixed 2x/3x ATR-based-stop target, OR
a "trailing" arm — `run_backtest` has no native trailing-stop, so this arm
is approximated honestly as stop-only (target_pct=None), riding to the
stop or max_hold, whichever comes first; stated plainly, not disguised as
a real trailing stop.
Grid: pct{2} x tf{2} x gate{2} x exit_style{tgt2xATR,tgt3xATR,trailing}=3
= **24 configs**.

**(c) Range-compression breakout**: the L-bar (L in {12,24}) high-low
range is less than `cmult` in {0.5,0.7} x its OWN trailing 180-day
median (both quantities shift(1)'d for causality — the compression
MEASURE and the breakout LEVEL are computed from strictly-prior bars);
trade the break of that L-bar range.
Grid: L{2} x cmult{2} x tf{2} x gate{2} x stop_mult{2} x
target_mult{2} = **64 configs**.

All three compression sub-families run BOTH with-trend-gated (4h champion
bias) and ungated, per the mandate.

Max-hold choices not fixed by the mandate were set to reasonable day-trade
values and stated once here rather than gridded (to keep the total config
count in budget): pin bars/engulfing 24h, inside-bar breakout 12h, NR
squeeze 24h, BB-width squeeze 48h ("ride" implies more room), range-
compression breakout 24h.

---

## 2. Event-frequency table — are these setups rare or common?

### Order blocks (1h/4h, by impulse definition)

Impulse triggers and resulting order-block formations, pre-test region
(train+val, ~5.06y). "n_ob_formed" = impulse events where an opposing
candle was actually found backward (almost every impulse — the block
ALWAYS exists by construction, the question is whether price ever revisits
it, which n_signal_events in the full grid answers per touch/breaker
variant):

| tf   |   mult |   bars_move |   n_impulse_up |   n_impulse_down |   n_ob_formed |
|:-----|-------:|------------:|---------------:|-----------------:|--------------:|
| 1h   |      2 |           1 |           2368 |             2249 |          4617 |
| 1h   |      2 |           3 |           4900 |             4281 |          9181 |
| 1h   |      3 |           1 |           1585 |             1549 |          3134 |
| 1h   |      3 |           3 |           3879 |             3516 |          7395 |
| 4h   |      2 |           1 |            711 |              600 |          1311 |
| 4h   |      2 |           3 |           1449 |             1150 |          2599 |
| 4h   |      3 |           1 |            471 |              415 |           886 |
| 4h   |      3 |           3 |           1153 |              939 |          2092 |

Reading this: order-block-ELIGIBLE impulses are NOT rare — thousands of
them per config on 1h (up to ~9,181 combined up+down block formations for
the loosest impulse definition), hundreds on 4h. The classic SMC claim
that "clean order blocks are rare, high-quality setups" does not hold
mechanically at hourly/4h resolution once impulse is defined by a
volatility-relative threshold — what's rare is a PROFITABLE one, not a
structurally-valid one (see section 3: zero of the 64 order-block configs
survived).

### Rejection + compression families (min/median/max raw signal-event count
across each family's full grid, pre-test region)

| family               | tf   |   min |   median |   max |
|:---------------------|:-----|------:|---------:|------:|
| 2a-pin-bar           | 1h   |   206 |   1882.5 |  9638 |
| 2a-pin-bar           | 4h   |    54 |    231   |  2361 |
| 2b-engulfing         | 1h   |   469 |   2483.5 | 13912 |
| 2b-engulfing         | 4h   |   112 |    296.5 |  3549 |
| 2c-inside-bar        | 1h   |  4342 |   7426.5 | 10511 |
| 2c-inside-bar        | 4h   |  1284 |   2082   |  2880 |
| 3a-nr-squeeze        | 1h   |  9600 |  12607.5 | 15615 |
| 3a-nr-squeeze        | 4h   |  2205 |   3009   |  3813 |
| 3b-bbwidth-squeeze   | 1h   |  6386 |   9062   | 11738 |
| 3b-bbwidth-squeeze   | 4h   |  1676 |   2375   |  3074 |
| 3c-range-compression | 1h   |  6721 |  11165.5 | 15436 |
| 3c-range-compression | 4h   |  1098 |   2322.5 |  3483 |

Same story: pin bars, engulfing, inside-bar patterns, NR-squeeze bars,
BB-width squeezes and range-compression bars are all COMMON at hourly
resolution — thousands of qualifying bars over 5 years even before any
context filter. The scarcity classical price-action teaching describes is
either a daily-chart-resolution phenomenon, a much stricter definition
than these mechanical ones, or largely a narrative overlaid after the
fact on ordinary noise. The one lever that reliably makes these events
RARE is the context requirement (see next section) — and that turns out
to hurt, not help.

---

## 3. Full config table (all 296 configs, verdicts + trades/yr + median hold)

trades_per_yr = (tr_n + va_n) / 5.06 (the shared train+val span in years).

| family               | config                                             | tf   |   tr_n |   tr_exp |   va_n |   va_exp |   trades_per_yr |   med_hold_h | verdict             |
|:---------------------|:---------------------------------------------------|:-----|-------:|---------:|-------:|---------:|----------------:|-------------:|:--------------------|
| 1-order-block        | base X2x/1bar touch=50pct tgt2xstop hold48h        | 1h   |    462 |    -9.91 |    157 |   -19.67 |          122.33 |          1   | FAIL                |
| 1-order-block        | base X2x/1bar touch=50pct tgt3xstop hold48h        | 1h   |    462 |    -9.73 |    157 |   -21.25 |          122.33 |          1   | FAIL                |
| 1-order-block        | BREAKER X2x/1bar touch=50pct tgt2xstop hold48h     | 1h   |    171 |    -6.87 |     52 |    -4.59 |           44.07 |          0   | FAIL                |
| 1-order-block        | BREAKER X2x/1bar touch=50pct tgt3xstop hold48h     | 1h   |    171 |    -7.62 |     52 |     3.56 |           44.07 |          0   | FAIL                |
| 1-order-block        | base X2x/1bar touch=sweep tgt2xstop hold48h        | 1h   |    435 |   -13.59 |    149 |   -14.49 |          115.42 |          0   | FAIL                |
| 1-order-block        | base X2x/1bar touch=sweep tgt3xstop hold48h        | 1h   |    435 |   -13.02 |    149 |   -14.52 |          115.42 |          0   | FAIL                |
| 1-order-block        | BREAKER X2x/1bar touch=sweep tgt2xstop hold48h     | 1h   |    258 |   -11.76 |     87 |   -10.47 |           68.18 |          0   | FAIL                |
| 1-order-block        | BREAKER X2x/1bar touch=sweep tgt3xstop hold48h     | 1h   |    258 |   -10.56 |     87 |    -5.93 |           68.18 |          0   | FAIL                |
| 1-order-block        | base X2x/3bar touch=50pct tgt2xstop hold48h        | 1h   |    483 |   -11.17 |    168 |   -10.67 |          128.66 |          1   | FAIL                |
| 1-order-block        | base X2x/3bar touch=50pct tgt3xstop hold48h        | 1h   |    483 |    -9.82 |    168 |    -7.92 |          128.66 |          1   | FAIL                |
| 1-order-block        | BREAKER X2x/3bar touch=50pct tgt2xstop hold48h     | 1h   |    173 |    -9.56 |     60 |   -18.63 |           46.05 |          0   | FAIL                |
| 1-order-block        | BREAKER X2x/3bar touch=50pct tgt3xstop hold48h     | 1h   |    173 |   -10.2  |     60 |   -13.64 |           46.05 |          0   | FAIL                |
| 1-order-block        | base X2x/3bar touch=sweep tgt2xstop hold48h        | 1h   |    456 |   -12.69 |    153 |    -9.28 |          120.36 |          0   | FAIL                |
| 1-order-block        | base X2x/3bar touch=sweep tgt3xstop hold48h        | 1h   |    456 |   -12.01 |    153 |    -8.93 |          120.36 |          0   | FAIL                |
| 1-order-block        | BREAKER X2x/3bar touch=sweep tgt2xstop hold48h     | 1h   |    260 |   -11.63 |    100 |   -16.32 |           71.15 |          0   | FAIL                |
| 1-order-block        | BREAKER X2x/3bar touch=sweep tgt3xstop hold48h     | 1h   |    260 |   -10.5  |    100 |   -13.46 |           71.15 |          0   | FAIL                |
| 1-order-block        | base X3x/1bar touch=50pct tgt2xstop hold48h        | 1h   |    399 |   -13.57 |    131 |   -25.55 |          104.74 |          1   | FAIL                |
| 1-order-block        | base X3x/1bar touch=50pct tgt3xstop hold48h        | 1h   |    399 |   -12.59 |    131 |   -28.3  |          104.74 |          1   | FAIL                |
| 1-order-block        | BREAKER X3x/1bar touch=50pct tgt2xstop hold48h     | 1h   |    120 |    -5.11 |     39 |     1.91 |           31.42 |          0   | FAIL                |
| 1-order-block        | BREAKER X3x/1bar touch=50pct tgt3xstop hold48h     | 1h   |    120 |    -4.58 |     39 |    10.74 |           31.42 |          1   | FAIL                |
| 1-order-block        | base X3x/1bar touch=sweep tgt2xstop hold48h        | 1h   |    378 |   -14.05 |    119 |   -15.08 |           98.22 |          0   | FAIL                |
| 1-order-block        | base X3x/1bar touch=sweep tgt3xstop hold48h        | 1h   |    378 |   -13.03 |    119 |   -15.91 |           98.22 |          0   | FAIL                |
| 1-order-block        | BREAKER X3x/1bar touch=sweep tgt2xstop hold48h     | 1h   |    196 |   -14.33 |     66 |    -9.89 |           51.78 |          0   | FAIL                |
| 1-order-block        | BREAKER X3x/1bar touch=sweep tgt3xstop hold48h     | 1h   |    196 |   -12.18 |     66 |    -2.63 |           51.78 |          0   | FAIL                |
| 1-order-block        | base X3x/3bar touch=50pct tgt2xstop hold48h        | 1h   |    447 |   -12.12 |    156 |   -15.97 |          119.17 |          1   | FAIL                |
| 1-order-block        | base X3x/3bar touch=50pct tgt3xstop hold48h        | 1h   |    447 |   -10.29 |    156 |   -14.57 |          119.17 |          1   | FAIL                |
| 1-order-block        | BREAKER X3x/3bar touch=50pct tgt2xstop hold48h     | 1h   |    159 |    -8.81 |     45 |   -13.54 |           40.32 |          0   | FAIL                |
| 1-order-block        | BREAKER X3x/3bar touch=50pct tgt3xstop hold48h     | 1h   |    159 |   -10.93 |     45 |   -10.12 |           40.32 |          0   | FAIL                |
| 1-order-block        | base X3x/3bar touch=sweep tgt2xstop hold48h        | 1h   |    421 |   -13.36 |    141 |   -13.47 |          111.07 |          0   | FAIL                |
| 1-order-block        | base X3x/3bar touch=sweep tgt3xstop hold48h        | 1h   |    421 |   -13.1  |    141 |   -14.25 |          111.07 |          0   | FAIL                |
| 1-order-block        | BREAKER X3x/3bar touch=sweep tgt2xstop hold48h     | 1h   |    242 |   -12.04 |     85 |   -13.97 |           64.62 |          0   | FAIL                |
| 1-order-block        | BREAKER X3x/3bar touch=sweep tgt3xstop hold48h     | 1h   |    242 |   -10    |     85 |    -9.39 |           64.62 |          0   | FAIL                |
| 1-order-block        | base X2x/1bar touch=50pct tgt2xstop hold48h        | 4h   |    232 |   -25.73 |     79 |   -12.14 |           61.46 |          4   | FAIL                |
| 1-order-block        | base X2x/1bar touch=50pct tgt3xstop hold48h        | 4h   |    232 |   -25.28 |     79 |   -19.12 |           61.46 |          4   | FAIL                |
| 1-order-block        | BREAKER X2x/1bar touch=50pct tgt2xstop hold48h     | 4h   |     49 |   -25.13 |     14 |   -40.04 |           12.45 |          0   | FAIL                |
| 1-order-block        | BREAKER X2x/1bar touch=50pct tgt3xstop hold48h     | 4h   |     49 |   -25.71 |     14 |   -34.26 |           12.45 |          0   | FAIL                |
| 1-order-block        | base X2x/1bar touch=sweep tgt2xstop hold48h        | 4h   |    198 |   -23.08 |     66 |   -22.98 |           52.17 |          0   | FAIL                |
| 1-order-block        | base X2x/1bar touch=sweep tgt3xstop hold48h        | 4h   |    198 |   -22.83 |     66 |   -22.03 |           52.17 |          0   | FAIL                |
| 1-order-block        | BREAKER X2x/1bar touch=sweep tgt2xstop hold48h     | 4h   |     62 |   -22.19 |     20 |   -16.57 |           16.21 |          0   | FAIL                |
| 1-order-block        | BREAKER X2x/1bar touch=sweep tgt3xstop hold48h     | 4h   |     62 |   -19.34 |     20 |    -9.41 |           16.21 |          0   | FAIL                |
| 1-order-block        | base X2x/3bar touch=50pct tgt2xstop hold48h        | 4h   |    238 |   -22.77 |     75 |   -10.81 |           61.86 |          4   | FAIL                |
| 1-order-block        | base X2x/3bar touch=50pct tgt3xstop hold48h        | 4h   |    238 |   -21.12 |     75 |    -6.68 |           61.86 |          4   | FAIL                |
| 1-order-block        | BREAKER X2x/3bar touch=50pct tgt2xstop hold48h     | 4h   |     41 |   -18.61 |     15 |   -29.75 |           11.07 |          0   | FAIL                |
| 1-order-block        | BREAKER X2x/3bar touch=50pct tgt3xstop hold48h     | 4h   |     41 |   -17.85 |     15 |   -33.57 |           11.07 |          0   | FAIL                |
| 1-order-block        | base X2x/3bar touch=sweep tgt2xstop hold48h        | 4h   |    198 |   -21.71 |     64 |   -21.3  |           51.78 |          0   | FAIL                |
| 1-order-block        | base X2x/3bar touch=sweep tgt3xstop hold48h        | 4h   |    198 |   -20.95 |     64 |   -18.15 |           51.78 |          0   | FAIL                |
| 1-order-block        | BREAKER X2x/3bar touch=sweep tgt2xstop hold48h     | 4h   |     56 |   -16.06 |     23 |   -23.48 |           15.61 |          0   | FAIL                |
| 1-order-block        | BREAKER X2x/3bar touch=sweep tgt3xstop hold48h     | 4h   |     56 |   -13.35 |     23 |   -18.53 |           15.61 |          0   | FAIL                |
| 1-order-block        | base X3x/1bar touch=50pct tgt2xstop hold48h        | 4h   |    173 |   -33.97 |     48 |   -15.18 |           43.68 |          4   | FAIL                |
| 1-order-block        | base X3x/1bar touch=50pct tgt3xstop hold48h        | 4h   |    173 |   -32.69 |     48 |   -19.59 |           43.68 |          4   | FAIL                |
| 1-order-block        | BREAKER X3x/1bar touch=50pct tgt2xstop hold48h     | 4h   |     32 |   -22.24 |      9 |   -22.23 |            8.1  |          0   | FAIL                |
| 1-order-block        | BREAKER X3x/1bar touch=50pct tgt3xstop hold48h     | 4h   |     32 |   -19.92 |      9 |    -0.14 |            8.1  |          0   | FAIL                |
| 1-order-block        | base X3x/1bar touch=sweep tgt2xstop hold48h        | 4h   |    148 |   -25.02 |     41 |   -25.47 |           37.35 |          0   | FAIL                |
| 1-order-block        | base X3x/1bar touch=sweep tgt3xstop hold48h        | 4h   |    148 |   -24.31 |     41 |   -29.82 |           37.35 |          0   | FAIL                |
| 1-order-block        | BREAKER X3x/1bar touch=sweep tgt2xstop hold48h     | 4h   |     41 |   -21.19 |     12 |   -16.67 |           10.47 |          0   | FAIL                |
| 1-order-block        | BREAKER X3x/1bar touch=sweep tgt3xstop hold48h     | 4h   |     41 |   -15.78 |     12 |    -9.5  |           10.47 |          0   | FAIL                |
| 1-order-block        | base X3x/3bar touch=50pct tgt2xstop hold48h        | 4h   |    203 |   -30.11 |     62 |   -17.99 |           52.37 |          4   | FAIL                |
| 1-order-block        | base X3x/3bar touch=50pct tgt3xstop hold48h        | 4h   |    203 |   -26.28 |     62 |   -28.67 |           52.37 |          4   | FAIL                |
| 1-order-block        | BREAKER X3x/3bar touch=50pct tgt2xstop hold48h     | 4h   |     28 |    -6.87 |      9 |    13.84 |            7.31 |          0   | FAIL                |
| 1-order-block        | BREAKER X3x/3bar touch=50pct tgt3xstop hold48h     | 4h   |     28 |     4.29 |      9 |   -45.29 |            7.31 |          0   | FAIL                |
| 1-order-block        | base X3x/3bar touch=sweep tgt2xstop hold48h        | 4h   |    172 |   -23.34 |     52 |   -24.45 |           44.27 |          0   | FAIL                |
| 1-order-block        | base X3x/3bar touch=sweep tgt3xstop hold48h        | 4h   |    172 |   -22.14 |     52 |   -22.57 |           44.27 |          0   | FAIL                |
| 1-order-block        | BREAKER X3x/3bar touch=sweep tgt2xstop hold48h     | 4h   |     39 |   -22.63 |     14 |   -20.02 |           10.47 |          0   | FAIL                |
| 1-order-block        | BREAKER X3x/3bar touch=sweep tgt3xstop hold48h     | 4h   |     39 |   -17.66 |     14 |   -13.79 |           10.47 |          0   | FAIL                |
| 2a-pin-bar           | wick2x ctx=roll20 stop1.0xATR tgt2xstop hold24h    | 1h   |    697 |    -9.5  |    238 |   -18.58 |          184.78 |          4   | FAIL                |
| 2a-pin-bar           | wick2x ctx=roll20 stop1.0xATR tgt3xstop hold24h    | 1h   |    697 |   -10.21 |    238 |   -18.74 |          184.78 |          6   | FAIL                |
| 2a-pin-bar           | wick2x ctx=roll20 stop1.5xATR tgt2xstop hold24h    | 1h   |    697 |   -10.57 |    238 |   -15.56 |          184.78 |          9   | FAIL                |
| 2a-pin-bar           | wick2x ctx=roll20 stop1.5xATR tgt3xstop hold24h    | 1h   |    697 |   -10.48 |    238 |   -18.88 |          184.78 |         12   | FAIL                |
| 2a-pin-bar           | wick2x ctx=roll55 stop1.0xATR tgt2xstop hold24h    | 1h   |    414 |   -11.24 |    167 |   -17.97 |          114.82 |          4   | FAIL                |
| 2a-pin-bar           | wick2x ctx=roll55 stop1.0xATR tgt3xstop hold24h    | 1h   |    414 |    -8.52 |    167 |   -15.74 |          114.82 |          5   | FAIL                |
| 2a-pin-bar           | wick2x ctx=roll55 stop1.5xATR tgt2xstop hold24h    | 1h   |    414 |   -12.03 |    167 |   -24.08 |          114.82 |          8   | FAIL                |
| 2a-pin-bar           | wick2x ctx=roll55 stop1.5xATR tgt3xstop hold24h    | 1h   |    414 |   -10.01 |    167 |   -27.81 |          114.82 |         11   | FAIL                |
| 2a-pin-bar           | wick2x ctx=sma50 stop1.0xATR tgt2xstop hold24h     | 1h   |     60 |   -11.43 |     42 |   -30.09 |           20.16 |          5   | FAIL                |
| 2a-pin-bar           | wick2x ctx=sma50 stop1.0xATR tgt3xstop hold24h     | 1h   |     60 |   -21.23 |     42 |   -14.73 |           20.16 |          7.5 | FAIL                |
| 2a-pin-bar           | wick2x ctx=sma50 stop1.5xATR tgt2xstop hold24h     | 1h   |     60 |   -29.76 |     42 |   -12.26 |           20.16 |         10   | FAIL                |
| 2a-pin-bar           | wick2x ctx=sma50 stop1.5xATR tgt3xstop hold24h     | 1h   |     60 |   -27.38 |     42 |    -7.39 |           20.16 |         13   | FAIL                |
| 2a-pin-bar           | wick2x ctx=none stop1.0xATR tgt2xstop hold24h      | 1h   |   1127 |    -7.74 |    371 |    -9.75 |          296.05 |          4   | FAIL                |
| 2a-pin-bar           | wick2x ctx=none stop1.0xATR tgt3xstop hold24h      | 1h   |   1127 |    -7.56 |    371 |    -6.51 |          296.05 |          4   | FAIL                |
| 2a-pin-bar           | wick2x ctx=none stop1.5xATR tgt2xstop hold24h      | 1h   |   1127 |    -7.58 |    371 |    -6.31 |          296.05 |          8   | FAIL                |
| 2a-pin-bar           | wick2x ctx=none stop1.5xATR tgt3xstop hold24h      | 1h   |   1127 |    -7.04 |    371 |   -11.21 |          296.05 |          9   | FAIL                |
| 2a-pin-bar           | wick3x ctx=roll20 stop1.0xATR tgt2xstop hold24h    | 1h   |    603 |    -9.56 |    210 |   -19.46 |          160.67 |          5   | FAIL                |
| 2a-pin-bar           | wick3x ctx=roll20 stop1.0xATR tgt3xstop hold24h    | 1h   |    603 |    -9.13 |    210 |   -18.29 |          160.67 |          6   | FAIL                |
| 2a-pin-bar           | wick3x ctx=roll20 stop1.5xATR tgt2xstop hold24h    | 1h   |    603 |   -10.18 |    210 |   -17.96 |          160.67 |         10   | FAIL                |
| 2a-pin-bar           | wick3x ctx=roll20 stop1.5xATR tgt3xstop hold24h    | 1h   |    603 |   -10.37 |    210 |   -19.28 |          160.67 |         13   | FAIL                |
| 2a-pin-bar           | wick3x ctx=roll55 stop1.0xATR tgt2xstop hold24h    | 1h   |    354 |   -12.07 |    141 |   -19.64 |           97.83 |          5   | FAIL                |
| 2a-pin-bar           | wick3x ctx=roll55 stop1.0xATR tgt3xstop hold24h    | 1h   |    354 |    -8.92 |    141 |   -18.59 |           97.83 |          6   | FAIL                |
| 2a-pin-bar           | wick3x ctx=roll55 stop1.5xATR tgt2xstop hold24h    | 1h   |    354 |   -13.62 |    141 |   -26.17 |           97.83 |          9   | FAIL                |
| 2a-pin-bar           | wick3x ctx=roll55 stop1.5xATR tgt3xstop hold24h    | 1h   |    354 |   -12.27 |    141 |   -28.28 |           97.83 |         11   | FAIL                |
| 2a-pin-bar           | wick3x ctx=sma50 stop1.0xATR tgt2xstop hold24h     | 1h   |     50 |   -18.57 |     35 |   -14.57 |           16.8  |          7   | FAIL                |
| 2a-pin-bar           | wick3x ctx=sma50 stop1.0xATR tgt3xstop hold24h     | 1h   |     50 |   -25.75 |     35 |     7.78 |           16.8  |          8   | FAIL                |
| 2a-pin-bar           | wick3x ctx=sma50 stop1.5xATR tgt2xstop hold24h     | 1h   |     50 |   -39.57 |     35 |    14.43 |           16.8  |         11   | FAIL                |
| 2a-pin-bar           | wick3x ctx=sma50 stop1.5xATR tgt3xstop hold24h     | 1h   |     50 |   -34.21 |     35 |    24.54 |           16.8  |         13   | FAIL                |
| 2a-pin-bar           | wick3x ctx=none stop1.0xATR tgt2xstop hold24h      | 1h   |   1059 |    -7.91 |    350 |    -9.79 |          278.46 |          4   | FAIL                |
| 2a-pin-bar           | wick3x ctx=none stop1.0xATR tgt3xstop hold24h      | 1h   |   1059 |    -7.51 |    350 |    -8.2  |          278.46 |          4   | FAIL                |
| 2a-pin-bar           | wick3x ctx=none stop1.5xATR tgt2xstop hold24h      | 1h   |   1059 |    -8.14 |    350 |    -4.26 |          278.46 |          8   | FAIL                |
| 2a-pin-bar           | wick3x ctx=none stop1.5xATR tgt3xstop hold24h      | 1h   |   1059 |    -7.02 |    350 |    -5.26 |          278.46 |          9   | FAIL                |
| 2a-pin-bar           | wick2x ctx=roll20 stop1.0xATR tgt2xstop hold24h    | 4h   |    159 |   -19.72 |     61 |   -23.84 |           43.48 |         14   | FAIL                |
| 2a-pin-bar           | wick2x ctx=roll20 stop1.0xATR tgt3xstop hold24h    | 4h   |    159 |   -19.24 |     61 |   -25.69 |           43.48 |         16   | FAIL                |
| 2a-pin-bar           | wick2x ctx=roll20 stop1.5xATR tgt2xstop hold24h    | 4h   |    159 |   -23.66 |     61 |   -25.29 |           43.48 |         24   | FAIL                |
| 2a-pin-bar           | wick2x ctx=roll20 stop1.5xATR tgt3xstop hold24h    | 4h   |    159 |   -20.85 |     61 |   -29.4  |           43.48 |         24   | FAIL                |
| 2a-pin-bar           | wick2x ctx=roll55 stop1.0xATR tgt2xstop hold24h    | 4h   |     82 |   -22.02 |     27 |    15.66 |           21.54 |         16   | FAIL                |
| 2a-pin-bar           | wick2x ctx=roll55 stop1.0xATR tgt3xstop hold24h    | 4h   |     82 |   -27.95 |     27 |    -9.47 |           21.54 |         24   | FAIL                |
| 2a-pin-bar           | wick2x ctx=roll55 stop1.5xATR tgt2xstop hold24h    | 4h   |     82 |   -33.09 |     27 |   -17.24 |           21.54 |         24   | FAIL                |
| 2a-pin-bar           | wick2x ctx=roll55 stop1.5xATR tgt3xstop hold24h    | 4h   |     82 |   -30.21 |     27 |   -17.24 |           21.54 |         24   | FAIL                |
| 2a-pin-bar           | wick2x ctx=sma50 stop1.0xATR tgt2xstop hold24h     | 4h   |     28 |   -69.6  |     14 |    36.34 |            8.3  |         24   | FAIL                |
| 2a-pin-bar           | wick2x ctx=sma50 stop1.0xATR tgt3xstop hold24h     | 4h   |     28 |   -64.69 |     14 |    58.41 |            8.3  |         24   | FAIL                |
| 2a-pin-bar           | wick2x ctx=sma50 stop1.5xATR tgt2xstop hold24h     | 4h   |     28 |   -76.65 |     14 |    60.26 |            8.3  |         24   | FAIL                |
| 2a-pin-bar           | wick2x ctx=sma50 stop1.5xATR tgt3xstop hold24h     | 4h   |     28 |   -75.62 |     14 |    49.21 |            8.3  |         24   | FAIL                |
| 2a-pin-bar           | wick2x ctx=none stop1.0xATR tgt2xstop hold24h      | 4h   |    719 |   -11.12 |    224 |    12.48 |          186.36 |         12   | FAIL                |
| 2a-pin-bar           | wick2x ctx=none stop1.0xATR tgt3xstop hold24h      | 4h   |    719 |   -10.99 |    224 |    21.85 |          186.36 |         20   | FAIL                |
| 2a-pin-bar           | wick2x ctx=none stop1.5xATR tgt2xstop hold24h      | 4h   |    719 |   -11.11 |    224 |    22.88 |          186.36 |         24   | FAIL                |
| 2a-pin-bar           | wick2x ctx=none stop1.5xATR tgt3xstop hold24h      | 4h   |    719 |    -9.45 |    224 |    12.22 |          186.36 |         24   | FAIL                |
| 2a-pin-bar           | wick3x ctx=roll20 stop1.0xATR tgt2xstop hold24h    | 4h   |    128 |   -20.26 |     54 |   -27.06 |           35.97 |         14   | FAIL                |
| 2a-pin-bar           | wick3x ctx=roll20 stop1.0xATR tgt3xstop hold24h    | 4h   |    128 |   -21.57 |     54 |   -27.2  |           35.97 |         16   | FAIL                |
| 2a-pin-bar           | wick3x ctx=roll20 stop1.5xATR tgt2xstop hold24h    | 4h   |    128 |   -28.97 |     54 |   -28.64 |           35.97 |         24   | FAIL                |
| 2a-pin-bar           | wick3x ctx=roll20 stop1.5xATR tgt3xstop hold24h    | 4h   |    128 |   -25.82 |     54 |   -33.27 |           35.97 |         24   | FAIL                |
| 2a-pin-bar           | wick3x ctx=roll55 stop1.0xATR tgt2xstop hold24h    | 4h   |     69 |   -32.11 |     23 |    -1.93 |           18.18 |         16   | FAIL                |
| 2a-pin-bar           | wick3x ctx=roll55 stop1.0xATR tgt3xstop hold24h    | 4h   |     69 |   -39.03 |     23 |   -22.66 |           18.18 |         24   | FAIL                |
| 2a-pin-bar           | wick3x ctx=roll55 stop1.5xATR tgt2xstop hold24h    | 4h   |     69 |   -43.68 |     23 |   -27.94 |           18.18 |         24   | FAIL                |
| 2a-pin-bar           | wick3x ctx=roll55 stop1.5xATR tgt3xstop hold24h    | 4h   |     69 |   -42.05 |     23 |   -27.94 |           18.18 |         24   | FAIL                |
| 2a-pin-bar           | wick3x ctx=sma50 stop1.0xATR tgt2xstop hold24h     | 4h   |     24 |   -72.58 |     11 |    11.36 |            6.92 |         24   | FAIL                |
| 2a-pin-bar           | wick3x ctx=sma50 stop1.0xATR tgt3xstop hold24h     | 4h   |     24 |   -66.71 |     11 |    22.76 |            6.92 |         24   | FAIL                |
| 2a-pin-bar           | wick3x ctx=sma50 stop1.5xATR tgt2xstop hold24h     | 4h   |     24 |   -84.1  |     11 |    19.3  |            6.92 |         24   | FAIL                |
| 2a-pin-bar           | wick3x ctx=sma50 stop1.5xATR tgt3xstop hold24h     | 4h   |     24 |   -82.88 |     11 |    19.3  |            6.92 |         24   | FAIL                |
| 2a-pin-bar           | wick3x ctx=none stop1.0xATR tgt2xstop hold24h      | 4h   |    632 |   -11.74 |    193 |     9.8  |          163.04 |         12   | FAIL                |
| 2a-pin-bar           | wick3x ctx=none stop1.0xATR tgt3xstop hold24h      | 4h   |    632 |   -11.08 |    193 |    12.35 |          163.04 |         20   | FAIL                |
| 2a-pin-bar           | wick3x ctx=none stop1.5xATR tgt2xstop hold24h      | 4h   |    632 |   -11.55 |    193 |    14.98 |          163.04 |         24   | FAIL                |
| 2a-pin-bar           | wick3x ctx=none stop1.5xATR tgt3xstop hold24h      | 4h   |    632 |    -9.57 |    193 |     4.58 |          163.04 |         24   | FAIL                |
| 2b-engulfing         | engulf ctx=roll20 stop1.0xATR tgt2xstop hold24h    | 1h   |    714 |    -5.74 |    275 |    -2.37 |          195.45 |          4   | FAIL                |
| 2b-engulfing         | engulf ctx=roll20 stop1.0xATR tgt3xstop hold24h    | 1h   |    714 |    -5.05 |    275 |    -1.83 |          195.45 |          6   | FAIL                |
| 2b-engulfing         | engulf ctx=roll20 stop1.5xATR tgt2xstop hold24h    | 1h   |    714 |    -4.08 |    275 |    -6.24 |          195.45 |          9   | FAIL                |
| 2b-engulfing         | engulf ctx=roll20 stop1.5xATR tgt3xstop hold24h    | 1h   |    714 |    -2.52 |    275 |   -10.3  |          195.45 |         11   | FAIL                |
| 2b-engulfing         | engulf ctx=roll55 stop1.0xATR tgt2xstop hold24h    | 1h   |    405 |    -8.75 |    159 |    -6.07 |          111.46 |          5   | FAIL                |
| 2b-engulfing         | engulf ctx=roll55 stop1.0xATR tgt3xstop hold24h    | 1h   |    405 |    -6.32 |    159 |    -5.17 |          111.46 |          5   | FAIL                |
| 2b-engulfing         | engulf ctx=roll55 stop1.5xATR tgt2xstop hold24h    | 1h   |    405 |    -6.87 |    159 |    -9.82 |          111.46 |          8   | FAIL                |
| 2b-engulfing         | engulf ctx=roll55 stop1.5xATR tgt3xstop hold24h    | 1h   |    405 |    -2.99 |    159 |   -16.28 |          111.46 |          9   | FAIL                |
| 2b-engulfing         | engulf ctx=sma50 stop1.0xATR tgt2xstop hold24h     | 1h   |     72 |   -15.21 |     50 |     7.89 |           24.11 |          4   | FAIL                |
| 2b-engulfing         | engulf ctx=sma50 stop1.0xATR tgt3xstop hold24h     | 1h   |     72 |   -20.54 |     50 |    10.92 |           24.11 |          8   | FAIL                |
| 2b-engulfing         | engulf ctx=sma50 stop1.5xATR tgt2xstop hold24h     | 1h   |     72 |   -27.89 |     50 |     3.63 |           24.11 |         10   | FAIL                |
| 2b-engulfing         | engulf ctx=sma50 stop1.5xATR tgt3xstop hold24h     | 1h   |     72 |   -21.75 |     50 |    30.57 |           24.11 |         14   | FAIL                |
| 2b-engulfing         | engulf ctx=none stop1.0xATR tgt2xstop hold24h      | 1h   |   1201 |    -5.93 |    404 |    -4.34 |          317.19 |          3   | FAIL                |
| 2b-engulfing         | engulf ctx=none stop1.0xATR tgt3xstop hold24h      | 1h   |   1201 |    -6.01 |    404 |    -5.45 |          317.19 |          5   | FAIL                |
| 2b-engulfing         | engulf ctx=none stop1.5xATR tgt2xstop hold24h      | 1h   |   1201 |    -5.46 |    404 |    -6.65 |          317.19 |          7   | FAIL                |
| 2b-engulfing         | engulf ctx=none stop1.5xATR tgt3xstop hold24h      | 1h   |   1201 |    -6.1  |    404 |    -2.11 |          317.19 |         10   | FAIL                |
| 2b-engulfing         | engulf ctx=roll20 stop1.0xATR tgt2xstop hold24h    | 4h   |    166 |    12.35 |     59 |   -40.39 |           44.47 |         16   | FAIL                |
| 2b-engulfing         | engulf ctx=roll20 stop1.0xATR tgt3xstop hold24h    | 4h   |    166 |    12.62 |     59 |   -42.87 |           44.47 |         20   | FAIL                |
| 2b-engulfing         | engulf ctx=roll20 stop1.5xATR tgt2xstop hold24h    | 4h   |    166 |    10.9  |     59 |   -49.76 |           44.47 |         24   | FAIL                |
| 2b-engulfing         | engulf ctx=roll20 stop1.5xATR tgt3xstop hold24h    | 4h   |    166 |     9.86 |     59 |   -49.51 |           44.47 |         24   | FAIL                |
| 2b-engulfing         | engulf ctx=roll55 stop1.0xATR tgt2xstop hold24h    | 4h   |     86 |    14.63 |     34 |   -22.13 |           23.72 |         16   | FAIL                |
| 2b-engulfing         | engulf ctx=roll55 stop1.0xATR tgt3xstop hold24h    | 4h   |     86 |    20.78 |     34 |   -30.34 |           23.72 |         24   | FAIL                |
| 2b-engulfing         | engulf ctx=roll55 stop1.5xATR tgt2xstop hold24h    | 4h   |     86 |     6.57 |     34 |   -45.05 |           23.72 |         24   | FAIL                |
| 2b-engulfing         | engulf ctx=roll55 stop1.5xATR tgt3xstop hold24h    | 4h   |     86 |    -2.68 |     34 |   -45.36 |           23.72 |         24   | FAIL                |
| 2b-engulfing         | engulf ctx=sma50 stop1.0xATR tgt2xstop hold24h     | 4h   |     33 |   -41.76 |     30 |     4.02 |           12.45 |         20   | FAIL                |
| 2b-engulfing         | engulf ctx=sma50 stop1.0xATR tgt3xstop hold24h     | 4h   |     33 |   -39.98 |     30 |     1.61 |           12.45 |         24   | FAIL                |
| 2b-engulfing         | engulf ctx=sma50 stop1.5xATR tgt2xstop hold24h     | 4h   |     33 |   -33.25 |     30 |    -6.09 |           12.45 |         24   | FAIL                |
| 2b-engulfing         | engulf ctx=sma50 stop1.5xATR tgt3xstop hold24h     | 4h   |     33 |   -32.03 |     30 |   -30.48 |           12.45 |         24   | FAIL                |
| 2b-engulfing         | engulf ctx=none stop1.0xATR tgt2xstop hold24h      | 4h   |    851 |   -10.61 |    294 |    -7.92 |          226.28 |         16   | FAIL                |
| 2b-engulfing         | engulf ctx=none stop1.0xATR tgt3xstop hold24h      | 4h   |    851 |   -10.58 |    294 |    -8.53 |          226.28 |         20   | FAIL                |
| 2b-engulfing         | engulf ctx=none stop1.5xATR tgt2xstop hold24h      | 4h   |    851 |   -10.68 |    294 |    -6.34 |          226.28 |         24   | FAIL                |
| 2b-engulfing         | engulf ctx=none stop1.5xATR tgt3xstop hold24h      | 4h   |    851 |   -10.72 |    294 |    -5.52 |          226.28 |         24   | FAIL                |
| 2c-inside-bar        | inside1 gated tgt2xmotherrange hold12h             | 1h   |    763 |    -6.29 |    252 |    -3.24 |          200.59 |          4   | FAIL                |
| 2c-inside-bar        | inside1 gated tgt3xmotherrange hold12h             | 1h   |    763 |    -7.82 |    252 |    -2.33 |          200.59 |          6   | FAIL                |
| 2c-inside-bar        | inside1 ungated tgt2xmotherrange hold12h           | 1h   |   1211 |    -5.96 |    381 |    -6.62 |          314.62 |          4   | FAIL                |
| 2c-inside-bar        | inside1 ungated tgt3xmotherrange hold12h           | 1h   |   1211 |    -6.09 |    381 |    -6.98 |          314.62 |          6   | FAIL                |
| 2c-inside-bar        | inside2 gated tgt2xmotherrange hold12h             | 1h   |    292 |   -11.13 |     98 |    -7.82 |           77.08 |          6   | FAIL                |
| 2c-inside-bar        | inside2 gated tgt3xmotherrange hold12h             | 1h   |    292 |    -6.16 |     98 |     2.72 |           77.08 |          8   | FAIL                |
| 2c-inside-bar        | inside2 ungated tgt2xmotherrange hold12h           | 1h   |    525 |    -8.64 |    162 |   -12.48 |          135.77 |          7   | FAIL                |
| 2c-inside-bar        | inside2 ungated tgt3xmotherrange hold12h           | 1h   |    525 |    -4.89 |    162 |    -7.43 |          135.77 |          8   | FAIL                |
| 2c-inside-bar        | inside1 gated tgt2xmotherrange hold12h             | 4h   |    236 |   -11.49 |     76 |     5.43 |           61.66 |         12   | FAIL                |
| 2c-inside-bar        | inside1 gated tgt3xmotherrange hold12h             | 4h   |    236 |    -6.25 |     76 |     9.19 |           61.66 |         12   | FAIL                |
| 2c-inside-bar        | inside1 ungated tgt2xmotherrange hold12h           | 4h   |    436 |   -14.42 |    136 |    -6.98 |          113.04 |         12   | FAIL                |
| 2c-inside-bar        | inside1 ungated tgt3xmotherrange hold12h           | 4h   |    436 |   -13.87 |    136 |    -3    |          113.04 |         12   | FAIL                |
| 2c-inside-bar        | inside2 gated tgt2xmotherrange hold12h             | 4h   |     91 |   -18.7  |     20 |    79.69 |           21.94 |         12   | FAIL                |
| 2c-inside-bar        | inside2 gated tgt3xmotherrange hold12h             | 4h   |     91 |   -19.79 |     20 |    78.87 |           21.94 |         12   | FAIL                |
| 2c-inside-bar        | inside2 ungated tgt2xmotherrange hold12h           | 4h   |    178 |   -25.32 |     46 |    43.18 |           44.27 |         12   | FAIL                |
| 2c-inside-bar        | inside2 ungated tgt3xmotherrange hold12h           | 4h   |    178 |   -26.95 |     46 |    45.14 |           44.27 |         12   | FAIL                |
| 3a-nr-squeeze        | NR4 gated stop1.0xATR tgt2xstop hold24h            | 1h   |    936 |    -6.82 |    313 |   -11.19 |          246.84 |          4   | FAIL                |
| 3a-nr-squeeze        | NR4 gated stop1.0xATR tgt3xstop hold24h            | 1h   |    936 |    -6.98 |    313 |   -11.74 |          246.84 |          5   | FAIL                |
| 3a-nr-squeeze        | NR4 gated stop1.5xATR tgt2xstop hold24h            | 1h   |    936 |    -7.69 |    313 |    -7.3  |          246.84 |          8   | FAIL                |
| 3a-nr-squeeze        | NR4 gated stop1.5xATR tgt3xstop hold24h            | 1h   |    936 |    -7.99 |    313 |    -4.7  |          246.84 |         10   | FAIL                |
| 3a-nr-squeeze        | NR4 ungated stop1.0xATR tgt2xstop hold24h          | 1h   |   1129 |    -2.89 |    377 |   -10.39 |          297.63 |          4   | FAIL                |
| 3a-nr-squeeze        | NR4 ungated stop1.0xATR tgt3xstop hold24h          | 1h   |   1129 |    -3.54 |    377 |   -15.28 |          297.63 |          5   | FAIL                |
| 3a-nr-squeeze        | NR4 ungated stop1.5xATR tgt2xstop hold24h          | 1h   |   1129 |    -2.71 |    377 |   -14.18 |          297.63 |          8   | FAIL                |
| 3a-nr-squeeze        | NR4 ungated stop1.5xATR tgt3xstop hold24h          | 1h   |   1129 |     3.04 |    377 |   -12.09 |          297.63 |         11   | FAIL                |
| 3a-nr-squeeze        | NR7 gated stop1.0xATR tgt2xstop hold24h            | 1h   |    785 |    -6.84 |    262 |   -12.79 |          206.92 |          4   | FAIL                |
| 3a-nr-squeeze        | NR7 gated stop1.0xATR tgt3xstop hold24h            | 1h   |    785 |    -6.18 |    262 |   -13.02 |          206.92 |          5   | FAIL                |
| 3a-nr-squeeze        | NR7 gated stop1.5xATR tgt2xstop hold24h            | 1h   |    785 |    -7.5  |    262 |    -9.71 |          206.92 |          8   | FAIL                |
| 3a-nr-squeeze        | NR7 gated stop1.5xATR tgt3xstop hold24h            | 1h   |    785 |    -7.98 |    262 |   -12.37 |          206.92 |         10   | FAIL                |
| 3a-nr-squeeze        | NR7 ungated stop1.0xATR tgt2xstop hold24h          | 1h   |   1018 |    -6.61 |    343 |    -8.25 |          268.97 |          4   | FAIL                |
| 3a-nr-squeeze        | NR7 ungated stop1.0xATR tgt3xstop hold24h          | 1h   |   1018 |    -6.54 |    343 |   -12.42 |          268.97 |          5   | FAIL                |
| 3a-nr-squeeze        | NR7 ungated stop1.5xATR tgt2xstop hold24h          | 1h   |   1018 |    -5.45 |    343 |    -8.3  |          268.97 |          8   | FAIL                |
| 3a-nr-squeeze        | NR7 ungated stop1.5xATR tgt3xstop hold24h          | 1h   |   1018 |    -4.2  |    343 |    -6.92 |          268.97 |         10   | FAIL                |
| 3a-nr-squeeze        | NR4 gated stop1.0xATR tgt2xstop hold24h            | 4h   |    454 |   -14.19 |    145 |    -7.65 |          118.38 |         12   | FAIL                |
| 3a-nr-squeeze        | NR4 gated stop1.0xATR tgt3xstop hold24h            | 4h   |    454 |   -11.5  |    145 |     2.37 |          118.38 |         16   | FAIL                |
| 3a-nr-squeeze        | NR4 gated stop1.5xATR tgt2xstop hold24h            | 4h   |    454 |    -9.76 |    145 |    -3.03 |          118.38 |         24   | FAIL                |
| 3a-nr-squeeze        | NR4 gated stop1.5xATR tgt3xstop hold24h            | 4h   |    454 |    -8.97 |    145 |    -4.87 |          118.38 |         24   | FAIL                |
| 3a-nr-squeeze        | NR4 ungated stop1.0xATR tgt2xstop hold24h          | 4h   |    686 |   -11.58 |    233 |   -16.63 |          181.62 |         12   | FAIL                |
| 3a-nr-squeeze        | NR4 ungated stop1.0xATR tgt3xstop hold24h          | 4h   |    686 |   -10.39 |    233 |   -12.66 |          181.62 |         16   | FAIL                |
| 3a-nr-squeeze        | NR4 ungated stop1.5xATR tgt2xstop hold24h          | 4h   |    686 |   -10.71 |    233 |   -16.17 |          181.62 |         24   | FAIL                |
| 3a-nr-squeeze        | NR4 ungated stop1.5xATR tgt3xstop hold24h          | 4h   |    686 |   -10.22 |    233 |   -17.74 |          181.62 |         24   | FAIL                |
| 3a-nr-squeeze        | NR7 gated stop1.0xATR tgt2xstop hold24h            | 4h   |    303 |   -10.65 |    107 |   -23.6  |           81.03 |         12   | FAIL                |
| 3a-nr-squeeze        | NR7 gated stop1.0xATR tgt3xstop hold24h            | 4h   |    303 |    -9.28 |    107 |   -17.9  |           81.03 |         16   | FAIL                |
| 3a-nr-squeeze        | NR7 gated stop1.5xATR tgt2xstop hold24h            | 4h   |    303 |   -12.07 |    107 |   -28.02 |           81.03 |         24   | FAIL                |
| 3a-nr-squeeze        | NR7 gated stop1.5xATR tgt3xstop hold24h            | 4h   |    303 |    -9.8  |    107 |   -32.79 |           81.03 |         24   | FAIL                |
| 3a-nr-squeeze        | NR7 ungated stop1.0xATR tgt2xstop hold24h          | 4h   |    514 |   -11    |    181 |   -13.94 |          137.35 |         16   | FAIL                |
| 3a-nr-squeeze        | NR7 ungated stop1.0xATR tgt3xstop hold24h          | 4h   |    514 |    -8.14 |    181 |   -10.98 |          137.35 |         20   | FAIL                |
| 3a-nr-squeeze        | NR7 ungated stop1.5xATR tgt2xstop hold24h          | 4h   |    514 |    -8.38 |    181 |   -18.91 |          137.35 |         24   | FAIL                |
| 3a-nr-squeeze        | NR7 ungated stop1.5xATR tgt3xstop hold24h          | 4h   |    514 |    -5.87 |    181 |   -23.07 |          137.35 |         24   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct10 gated tgt2xATR stop0.81% hold48h           | 1h   |    112 |    -6.08 |     19 |    26.23 |           25.89 |          5   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct10 gated tgt3xATR stop0.81% hold48h           | 1h   |    112 |    -8.22 |     19 |    44.66 |           25.89 |          9   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct10 gated trailing stop0.81% hold48h           | 1h   |    112 |   -19.36 |     19 |   101.34 |           25.89 |         12   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct10 ungated tgt2xATR stop0.81% hold48h         | 1h   |    165 |    -9.35 |     29 |     2.29 |           38.34 |          7   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct10 ungated tgt3xATR stop0.81% hold48h         | 1h   |    165 |    -8.47 |     29 |    -3.19 |           38.34 |         10   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct10 ungated trailing stop0.81% hold48h         | 1h   |    165 |   -12.87 |     29 |    26.84 |           38.34 |         14   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct20 gated tgt2xATR stop0.81% hold48h           | 1h   |    175 |     2.83 |     32 |    25.33 |           40.91 |          4   | SURVIVOR            |
| 3b-bbwidth-squeeze   | BBpct20 gated tgt3xATR stop0.81% hold48h           | 1h   |    175 |     1.09 |     32 |    31.87 |           40.91 |          6   | SURVIVOR            |
| 3b-bbwidth-squeeze   | BBpct20 gated trailing stop0.81% hold48h           | 1h   |    175 |   -11.74 |     32 |    63.36 |           40.91 |         11   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct20 ungated tgt2xATR stop0.81% hold48h         | 1h   |    257 |    -5.06 |     57 |    -4.83 |           62.06 |          5   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct20 ungated tgt3xATR stop0.81% hold48h         | 1h   |    257 |    -5.36 |     57 |    -4.94 |           62.06 |          6   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct20 ungated trailing stop0.81% hold48h         | 1h   |    257 |    -7.64 |     57 |    12.74 |           62.06 |         10   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct10 gated tgt2xATR stop1.74% hold48h           | 4h   |     41 |   -54.95 |      3 |    67.7  |            8.7  |         18   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct10 gated tgt3xATR stop1.74% hold48h           | 4h   |     41 |   -42.83 |      3 |  -105.77 |            8.7  |         22   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct10 gated trailing stop1.74% hold48h           | 4h   |     41 |   -48.45 |      3 |  -105.77 |            8.7  |         24   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct10 ungated tgt2xATR stop1.74% hold48h         | 4h   |     76 |   -19.95 |     12 |    85.9  |           17.39 |         16   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct10 ungated tgt3xATR stop1.74% hold48h         | 4h   |     76 |    -6.46 |     12 |    45.39 |           17.39 |         20   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct10 ungated trailing stop1.74% hold48h         | 4h   |     76 |    10.92 |     12 |    45.05 |           17.39 |         32   | SURVIVOR            |
| 3b-bbwidth-squeeze   | BBpct20 gated tgt2xATR stop1.74% hold48h           | 4h   |     69 |   -27.77 |     13 |   122.72 |           16.21 |         16   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct20 gated tgt3xATR stop1.74% hold48h           | 4h   |     69 |   -21.97 |     13 |   141.96 |           16.21 |         20   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct20 gated trailing stop1.74% hold48h           | 4h   |     69 |    -8.81 |     13 |   104.48 |           16.21 |         32   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct20 ungated tgt2xATR stop1.74% hold48h         | 4h   |    122 |   -14.01 |     26 |   112.14 |           29.25 |         16   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct20 ungated tgt3xATR stop1.74% hold48h         | 4h   |    122 |    -2    |     26 |   100.13 |           29.25 |         20   | FAIL                |
| 3b-bbwidth-squeeze   | BBpct20 ungated trailing stop1.74% hold48h         | 4h   |    122 |    11.64 |     26 |    80.02 |           29.25 |         32   | SURVIVOR            |
| 3c-range-compression | L12 <0.5xmed gated stop1.0xATR tgt2xstop hold24h   | 1h   |    205 |    -7.42 |     38 |     6.14 |           48.02 |          4   | FAIL                |
| 3c-range-compression | L12 <0.5xmed gated stop1.0xATR tgt3xstop hold24h   | 1h   |    205 |    -3.3  |     38 |    -8.81 |           48.02 |          6   | FAIL                |
| 3c-range-compression | L12 <0.5xmed gated stop1.5xATR tgt2xstop hold24h   | 1h   |    205 |    -3.42 |     38 |   -14.7  |           48.02 |         11   | FAIL                |
| 3c-range-compression | L12 <0.5xmed gated stop1.5xATR tgt3xstop hold24h   | 1h   |    205 |     0.72 |     38 |    -9.95 |           48.02 |         14   | FAIL                |
| 3c-range-compression | L12 <0.5xmed ungated stop1.0xATR tgt2xstop hold24h | 1h   |    321 |    -5.66 |     60 |     3.09 |           75.3  |          4   | FAIL                |
| 3c-range-compression | L12 <0.5xmed ungated stop1.0xATR tgt3xstop hold24h | 1h   |    321 |    -1.54 |     60 |    -3.46 |           75.3  |          6   | FAIL                |
| 3c-range-compression | L12 <0.5xmed ungated stop1.5xATR tgt2xstop hold24h | 1h   |    321 |    -3.27 |     60 |    -4.68 |           75.3  |         12   | FAIL                |
| 3c-range-compression | L12 <0.5xmed ungated stop1.5xATR tgt3xstop hold24h | 1h   |    321 |    -1.36 |     60 |     6.19 |           75.3  |         15   | FAIL                |
| 3c-range-compression | L12 <0.7xmed gated stop1.0xATR tgt2xstop hold24h   | 1h   |    331 |    -3.33 |     85 |     2.38 |           82.21 |          4   | FAIL                |
| 3c-range-compression | L12 <0.7xmed gated stop1.0xATR tgt3xstop hold24h   | 1h   |    331 |    -4.16 |     85 |    -4.73 |           82.21 |          6   | FAIL                |
| 3c-range-compression | L12 <0.7xmed gated stop1.5xATR tgt2xstop hold24h   | 1h   |    331 |   -10.68 |     85 |    -0.14 |           82.21 |          9   | FAIL                |
| 3c-range-compression | L12 <0.7xmed gated stop1.5xATR tgt3xstop hold24h   | 1h   |    331 |   -10.05 |     85 |     4.11 |           82.21 |         12   | FAIL                |
| 3c-range-compression | L12 <0.7xmed ungated stop1.0xATR tgt2xstop hold24h | 1h   |    511 |    -8.96 |    135 |     3.99 |          127.67 |          4   | FAIL                |
| 3c-range-compression | L12 <0.7xmed ungated stop1.0xATR tgt3xstop hold24h | 1h   |    511 |    -9.6  |    135 |     0.44 |          127.67 |          6   | FAIL                |
| 3c-range-compression | L12 <0.7xmed ungated stop1.5xATR tgt2xstop hold24h | 1h   |    511 |   -11.93 |    135 |     8.48 |          127.67 |          9   | FAIL                |
| 3c-range-compression | L12 <0.7xmed ungated stop1.5xATR tgt3xstop hold24h | 1h   |    511 |   -11.16 |    135 |    12.39 |          127.67 |         12   | FAIL                |
| 3c-range-compression | L24 <0.5xmed gated stop1.0xATR tgt2xstop hold24h   | 1h   |    115 |   -18.3  |     21 |    12.68 |           26.88 |          4   | FAIL                |
| 3c-range-compression | L24 <0.5xmed gated stop1.0xATR tgt3xstop hold24h   | 1h   |    115 |    -8.95 |     21 |    44.77 |           26.88 |          5   | FAIL                |
| 3c-range-compression | L24 <0.5xmed gated stop1.5xATR tgt2xstop hold24h   | 1h   |    115 |    -3.03 |     21 |    35.19 |           26.88 |          9   | FAIL                |
| 3c-range-compression | L24 <0.5xmed gated stop1.5xATR tgt3xstop hold24h   | 1h   |    115 |     2.26 |     21 |    65.97 |           26.88 |         12   | SURVIVOR            |
| 3c-range-compression | L24 <0.5xmed ungated stop1.0xATR tgt2xstop hold24h | 1h   |    215 |   -12.22 |     37 |    23.15 |           49.8  |          5   | FAIL                |
| 3c-range-compression | L24 <0.5xmed ungated stop1.0xATR tgt3xstop hold24h | 1h   |    215 |    -2.98 |     37 |    53.2  |           49.8  |          6   | FAIL                |
| 3c-range-compression | L24 <0.5xmed ungated stop1.5xATR tgt2xstop hold24h | 1h   |    215 |    -2.38 |     37 |    43.95 |           49.8  |         11.5 | FAIL                |
| 3c-range-compression | L24 <0.5xmed ungated stop1.5xATR tgt3xstop hold24h | 1h   |    215 |    10.98 |     37 |    76.38 |           49.8  |         14   | SURVIVOR            |
| 3c-range-compression | L24 <0.7xmed gated stop1.0xATR tgt2xstop hold24h   | 1h   |    212 |   -18.41 |     49 |    28.7  |           51.58 |          3   | FAIL                |
| 3c-range-compression | L24 <0.7xmed gated stop1.0xATR tgt3xstop hold24h   | 1h   |    212 |   -12.97 |     49 |    25.65 |           51.58 |          5   | FAIL                |
| 3c-range-compression | L24 <0.7xmed gated stop1.5xATR tgt2xstop hold24h   | 1h   |    212 |   -10.23 |     49 |    21.82 |           51.58 |          9   | FAIL                |
| 3c-range-compression | L24 <0.7xmed gated stop1.5xATR tgt3xstop hold24h   | 1h   |    212 |    -9.57 |     49 |    39    |           51.58 |         11   | FAIL                |
| 3c-range-compression | L24 <0.7xmed ungated stop1.0xATR tgt2xstop hold24h | 1h   |    375 |   -14.22 |     88 |    25.2  |           91.5  |          4   | FAIL                |
| 3c-range-compression | L24 <0.7xmed ungated stop1.0xATR tgt3xstop hold24h | 1h   |    375 |   -11.2  |     88 |    28.53 |           91.5  |          5   | FAIL                |
| 3c-range-compression | L24 <0.7xmed ungated stop1.5xATR tgt2xstop hold24h | 1h   |    375 |   -10.69 |     88 |    23.11 |           91.5  |          9   | FAIL                |
| 3c-range-compression | L24 <0.7xmed ungated stop1.5xATR tgt3xstop hold24h | 1h   |    375 |    -5.97 |     88 |    42.31 |           91.5  |         11   | FAIL                |
| 3c-range-compression | L12 <0.5xmed gated stop1.0xATR tgt2xstop hold24h   | 4h   |     71 |   -23.63 |      9 |    90.32 |           15.81 |         16   | FAIL                |
| 3c-range-compression | L12 <0.5xmed gated stop1.0xATR tgt3xstop hold24h   | 4h   |     71 |   -11.69 |      9 |   101.75 |           15.81 |         18   | FAIL                |
| 3c-range-compression | L12 <0.5xmed gated stop1.5xATR tgt2xstop hold24h   | 4h   |     71 |   -21.6  |      9 |   122.73 |           15.81 |         24   | FAIL                |
| 3c-range-compression | L12 <0.5xmed gated stop1.5xATR tgt3xstop hold24h   | 4h   |     71 |   -37.74 |      9 |   146.09 |           15.81 |         24   | FAIL                |
| 3c-range-compression | L12 <0.5xmed ungated stop1.0xATR tgt2xstop hold24h | 4h   |    127 |   -20.98 |     16 |   115.73 |           28.26 |         16   | FAIL                |
| 3c-range-compression | L12 <0.5xmed ungated stop1.0xATR tgt3xstop hold24h | 4h   |    127 |   -14.87 |     16 |    97.26 |           28.26 |         20   | FAIL                |
| 3c-range-compression | L12 <0.5xmed ungated stop1.5xATR tgt2xstop hold24h | 4h   |    127 |   -16.99 |     16 |   106.18 |           28.26 |         24   | FAIL                |
| 3c-range-compression | L12 <0.5xmed ungated stop1.5xATR tgt3xstop hold24h | 4h   |    127 |   -23.27 |     16 |   120.03 |           28.26 |         24   | FAIL                |
| 3c-range-compression | L12 <0.7xmed gated stop1.0xATR tgt2xstop hold24h   | 4h   |    127 |   -21.3  |     31 |    72.13 |           31.23 |         16   | FAIL                |
| 3c-range-compression | L12 <0.7xmed gated stop1.0xATR tgt3xstop hold24h   | 4h   |    127 |   -18.22 |     31 |    82.74 |           31.23 |         16   | FAIL                |
| 3c-range-compression | L12 <0.7xmed gated stop1.5xATR tgt2xstop hold24h   | 4h   |    127 |   -21.75 |     31 |    93.16 |           31.23 |         24   | FAIL                |
| 3c-range-compression | L12 <0.7xmed gated stop1.5xATR tgt3xstop hold24h   | 4h   |    127 |   -27.28 |     31 |    91.19 |           31.23 |         24   | FAIL                |
| 3c-range-compression | L12 <0.7xmed ungated stop1.0xATR tgt2xstop hold24h | 4h   |    228 |   -12.14 |     46 |    91.33 |           54.15 |         16   | FAIL                |
| 3c-range-compression | L12 <0.7xmed ungated stop1.0xATR tgt3xstop hold24h | 4h   |    228 |    -8.32 |     46 |    99.21 |           54.15 |         16   | FAIL                |
| 3c-range-compression | L12 <0.7xmed ungated stop1.5xATR tgt2xstop hold24h | 4h   |    228 |    -5.22 |     46 |   105.54 |           54.15 |         24   | FAIL                |
| 3c-range-compression | L12 <0.7xmed ungated stop1.5xATR tgt3xstop hold24h | 4h   |    228 |    -3.47 |     46 |   108    |           54.15 |         24   | FAIL                |
| 3c-range-compression | L24 <0.5xmed gated stop1.0xATR tgt2xstop hold24h   | 4h   |     27 |     5.49 |      1 |   169.16 |            5.53 |         20   | INSUFFICIENT-SAMPLE |
| 3c-range-compression | L24 <0.5xmed gated stop1.0xATR tgt3xstop hold24h   | 4h   |     27 |     2.79 |      1 |   169.16 |            5.53 |         22   | INSUFFICIENT-SAMPLE |
| 3c-range-compression | L24 <0.5xmed gated stop1.5xATR tgt2xstop hold24h   | 4h   |     27 |   -22.87 |      1 |   169.16 |            5.53 |         24   | FAIL                |
| 3c-range-compression | L24 <0.5xmed gated stop1.5xATR tgt3xstop hold24h   | 4h   |     27 |     3.73 |      1 |   169.16 |            5.53 |         24   | INSUFFICIENT-SAMPLE |
| 3c-range-compression | L24 <0.5xmed ungated stop1.0xATR tgt2xstop hold24h | 4h   |     64 |    26.22 |      2 |    92.39 |           13.04 |         20   | INSUFFICIENT-SAMPLE |
| 3c-range-compression | L24 <0.5xmed ungated stop1.0xATR tgt3xstop hold24h | 4h   |     64 |    38.44 |      2 |    92.39 |           13.04 |         20   | INSUFFICIENT-SAMPLE |
| 3c-range-compression | L24 <0.5xmed ungated stop1.5xATR tgt2xstop hold24h | 4h   |     64 |    24.44 |      2 |    92.39 |           13.04 |         24   | INSUFFICIENT-SAMPLE |
| 3c-range-compression | L24 <0.5xmed ungated stop1.5xATR tgt3xstop hold24h | 4h   |     64 |    51.23 |      2 |    92.39 |           13.04 |         24   | INSUFFICIENT-SAMPLE |
| 3c-range-compression | L24 <0.7xmed gated stop1.0xATR tgt2xstop hold24h   | 4h   |     62 |    57.34 |     13 |    14.9  |           14.82 |         12   | SURVIVOR            |
| 3c-range-compression | L24 <0.7xmed gated stop1.0xATR tgt3xstop hold24h   | 4h   |     62 |    52.47 |     13 |    43.85 |           14.82 |         16   | SURVIVOR            |
| 3c-range-compression | L24 <0.7xmed gated stop1.5xATR tgt2xstop hold24h   | 4h   |     62 |    19.26 |     13 |    -5.28 |           14.82 |         20   | FAIL                |
| 3c-range-compression | L24 <0.7xmed gated stop1.5xATR tgt3xstop hold24h   | 4h   |     62 |    41.14 |     13 |     9.14 |           14.82 |         24   | SURVIVOR            |
| 3c-range-compression | L24 <0.7xmed ungated stop1.0xATR tgt2xstop hold24h | 4h   |    139 |    47.9  |     24 |    -7.31 |           32.21 |         16   | FAIL                |
| 3c-range-compression | L24 <0.7xmed ungated stop1.0xATR tgt3xstop hold24h | 4h   |    139 |    54.01 |     24 |     7.8  |           32.21 |         20   | SURVIVOR            |
| 3c-range-compression | L24 <0.7xmed ungated stop1.5xATR tgt2xstop hold24h | 4h   |    139 |    33.39 |     24 |   -11.59 |           32.21 |         24   | FAIL                |
| 3c-range-compression | L24 <0.7xmed ungated stop1.5xATR tgt3xstop hold24h | 4h   |    139 |    62.45 |     24 |    -3.94 |           32.21 |         24   | FAIL                |

---

## 4. Context-requirement analysis (family 2a pin bars + 2b engulfing)

Required question: does requiring a context level (rolling 20/55-bar
extreme or daily SMA50) actually help pin bars / engulfing candles, or is
"context is mandatory" folklore that doesn't survive contact with a
gauntlet? Every wick/stop/target combination was run FOUR times — at
roll20, roll55, sma50, and a `none` arm with no level requirement at all —
so this is a like-for-like comparison, not a cherry-pick.

By family:

| family       | context   |   n_configs |   mean_tr_exp |   median_tr_exp |   mean_tr_win |   pct_positive_tr |   survivors |   mean_events |
|:-------------|:----------|------------:|--------------:|----------------:|--------------:|------------------:|------------:|--------------:|
| 2a-pin-bar   | none      |          16 |         -9.19 |           -8.8  |         35.73 |               0   |           0 |       5249.75 |
| 2a-pin-bar   | roll20    |          16 |        -16.26 |          -14.9  |         38.22 |               0   |           0 |       1510    |
| 2a-pin-bar   | roll55    |          16 |        -22.43 |          -17.82 |         37.78 |               0   |           0 |        724    |
| 2a-pin-bar   | sma50     |          16 |        -50.05 |          -52.13 |         27.48 |               0   |           0 |        155.5  |
| 2b-engulfing | none      |           8 |         -8.26 |           -8.34 |         35.58 |               0   |           0 |       8730.5  |
| 2b-engulfing | roll20    |           8 |          3.54 |            3.67 |         41.15 |              50   |           0 |       1929.5  |
| 2b-engulfing | roll55    |           8 |          1.8  |           -2.83 |         42.33 |              37.5 |           0 |        850.5  |
| 2b-engulfing | sma50     |           8 |        -29.05 |          -29.96 |         36.43 |               0   |           0 |        290.5  |

Pooled (both families):

| context   |   n_configs |   mean_tr_exp |   median_tr_exp |   pct_positive_tr |   survivors |   mean_events |
|:----------|------------:|--------------:|----------------:|------------------:|------------:|--------------:|
| none      |          24 |         -8.88 |           -8.8  |              0    |           0 |       6410    |
| roll20    |          24 |         -9.66 |          -10.19 |             16.67 |           0 |       1649.83 |
| roll55    |          24 |        -14.35 |          -11.63 |             12.5  |           0 |        766.17 |
| sma50     |          24 |        -43.05 |          -33.73 |              0    |           0 |        200.5  |

**Answer: context did NOT help — if anything, the tighter the context
requirement, the WORSE the mean/median train expectancy got**, moving
monotonically from -8.88 (none) to -9.66 (roll20) to -14.35 (roll55) to
-43.05 (sma50). Zero survivors in ANY context arm, including bare/no-context
pins and engulfs. Two honest caveats on this finding: (1) the whole family
is negative-edge in this mechanical form regardless of context — subsetting
a broken strategy by an arbitrary filter is re-slicing noise, not proof
that "context actively hurts" as a causal mechanism; (2) the sma50 arm's
worse numbers coincide with its much smaller sample (mean ~156-291 events
vs ~5,250-8,730 for `none`), so small-sample variance inflates both its
best and worst outcomes — the roll20/roll55/sma50 progression is at least
partly a sample-size-shrinkage artifact, not purely "context makes it
worse." What the data does NOT support is the discretionary-trading premise
that requiring a level is what separates the tradeable pins/engulfs from
the noise — bare pattern recognition performed as well or better than
every context-gated version tested here.

---

## 5. Cross-family overlap — order blocks vs a simple FVG recompute (1h)

A from-scratch, threshold-free, 3-candle fair value gap on 1h (bullish FVG
at bar i if low[i] > high[i-2]; bearish if high[i] < low[i-2] — no
step56 import, recomputed here per the mandate) compared against the
flagship order-block config's entry bars (X2x/1bar impulse, 50% touch,
base variant, 1h):

- FVG-forming bars: 10,017 of 55,451 total 1h bars (18.1% of all bars).
- Order-block entries (this config): 2,553.
- Exact-bar overlap: 523 (20.5% of OB entries land ON an FVG-forming bar).
- Within +/-2 bars: 1,790 (70.1% of OB entries land near one).

Chance baseline matters here because FVGs are so common: if OB entries
were scattered independently of FVGs, exact-bar overlap would be expected
at ~18.1% (the base rate) and the +/-2-bar (5-bar window) rate at
~1-(1-0.181)^5 ~= 63.1%. Observed rates (20.5% / 70.1%) sit only modestly
above those chance baselines (~1.1x on both). **Order blocks and FVGs are
correlated but far from redundant** — both are downstream of the same
underlying "impulsive move" detector, so some clustering is mechanically
expected, but roughly 30% of order-block entries occur nowhere near a raw
FVG and the exact-bar hit rate is barely above noise. A portfolio running
both tool families would get meaningfully more diversification than "same
signal twice," but shouldn't be pitched as fully independent either.

---

## 6. Ranked candidates (train+val survivors — NO sealed test looks spent;
this script never touches the final 20%)

10 configs cleared the 30-train/8-val positive-both-windows bar, but they
collapse into 4 genuinely distinct SIGNALS once target/stop-multiplier
siblings are grouped (spending a sealed look on both the 2x and 3x target
variant of the same base signal would burn two looks for one idea — the
program's "never re-look" discipline argues for judging by base signal,
not raw config count):

| family               | config                                             | tf   |   tr_n |   tr_exp |   tr_win% |   va_n |   va_exp |   va_win% |   trades_per_yr |   med_hold_h |   tr_dd% |   va_dd% |   stop% |   target% |
|:---------------------|:---------------------------------------------------|:-----|-------:|---------:|----------:|-------:|---------:|----------:|----------------:|-------------:|---------:|---------:|--------:|----------:|
| 3b-bbwidth-squeeze   | BBpct20 gated tgt2xATR stop0.81% hold48h           | 1h   |    175 |     2.83 |     37.71 |     32 |    25.33 |     46.88 |           40.91 |            4 |   -15.07 |    -3.63 |    0.81 |      1.62 |
| 3b-bbwidth-squeeze   | BBpct20 gated tgt3xATR stop0.81% hold48h           | 1h   |    175 |     1.09 |     30.29 |     32 |    31.87 |     37.5  |           40.91 |            6 |   -19.73 |    -4.98 |    0.81 |      2.43 |
| 3b-bbwidth-squeeze   | BBpct10 ungated trailing stop1.74% hold48h         | 4h   |     76 |    10.92 |     35.53 |     12 |    45.05 |     50    |           17.39 |           32 |   -17.96 |    -5.79 |    1.74 |    nan    |
| 3b-bbwidth-squeeze   | BBpct20 ungated trailing stop1.74% hold48h         | 4h   |    122 |    11.64 |     35.25 |     26 |    80.02 |     46.15 |           29.25 |           32 |   -15.5  |   -11.51 |    1.74 |    nan    |
| 3c-range-compression | L24 <0.5xmed gated stop1.5xATR tgt3xstop hold24h   | 1h   |    115 |     2.26 |     35.65 |     21 |    65.97 |     47.62 |           26.88 |           12 |   -14.79 |    -3.74 |    1.21 |      3.64 |
| 3c-range-compression | L24 <0.5xmed ungated stop1.5xATR tgt3xstop hold24h | 1h   |    215 |    10.98 |     36.28 |     37 |    76.38 |     48.65 |           49.8  |           14 |   -18.05 |    -9.16 |    1.21 |      3.64 |
| 3c-range-compression | L24 <0.7xmed gated stop1.0xATR tgt2xstop hold24h   | 4h   |     62 |    57.34 |     51.61 |     13 |    14.9  |     46.15 |           14.82 |           12 |    -6.45 |   -10.12 |    1.74 |      3.48 |
| 3c-range-compression | L24 <0.7xmed gated stop1.0xATR tgt3xstop hold24h   | 4h   |     62 |    52.47 |     46.77 |     13 |    43.85 |     46.15 |           14.82 |           16 |   -20.86 |   -10.12 |    1.74 |      5.22 |
| 3c-range-compression | L24 <0.7xmed gated stop1.5xATR tgt3xstop hold24h   | 4h   |     62 |    41.14 |     46.77 |     13 |     9.14 |     46.15 |           14.82 |           24 |   -27.84 |   -16.2  |    2.61 |      7.83 |
| 3c-range-compression | L24 <0.7xmed ungated stop1.0xATR tgt3xstop hold24h | 4h   |    139 |    54.01 |     46.04 |     24 |     7.8  |     45.83 |           32.21 |           20 |   -12.98 |   -14.54 |    1.74 |      5.22 |

**Ranked by strength (reasoning, not just headline numbers):**

1. **3b-bbwidth-squeeze, 4h, BBpct20 ungated, trailing exit, stop 1.74%**
   — train $11.64/t x122, val $80.02/t x26, win 35%/46%, DD -15.5%/-11.5%,
   ~29 trades/yr, median hold 32h. Strongest candidate: consistent sign and
   magnitude across train AND val (val isn't wildly out of family with
   train the way some others are), the largest val trade count of the
   BB-width survivors, and a real mechanism (volatility contraction ->
   expansion is the most textbook-legitimate of the three families tested).
   The sibling BBpct10/ungated/trailing config (train $10.92/t x76, val
   $45.05/t x12) is the same underlying signal at a stricter percentile —
   corroborating, not a separate idea.
2. **3c-range-compression, 4h, L24<0.7x-trailing-median, gated, stop
   1.0xATR, target 2xstop** — train $57.34/t x62, val $14.90/t x13, by far
   the SMALLEST drawdown of any survivor (-6.45% train / -10.12% val),
   ~15 trades/yr. Second-strongest: the tightest risk profile in the whole
   grid, though val's 13 trades sits close to the 8-trade floor and the
   val edge, while positive, is much thinner than train's — normal
   regression, but worth a wider look before weighting this heavily.
3. **3c-range-compression, 1h, L24<0.5x-trailing-median, ungated, stop
   1.5xATR, target 3xstop** — train $10.98/t x215, val $76.38/t x37, the
   LARGEST combined sample of any survivor (252 trades total), ~50
   trades/yr. Third: most statistically convincing on sample size alone,
   highest turnover (fits the program's activity mandate), but the
   largest drawdown of the group (-18.05% train).
4. **3b-bbwidth-squeeze, 1h, BBpct20 gated, tgt2xATR, stop 0.81%** — train
   only $2.83/t (barely positive) against val $25.33/t x32. Flagged as
   WEAK/marginal: a train edge this thin next to a val edge nearly 9x
   larger is the signature of a val-window regime fluke more than a
   durable edge — worth watching, not worth prioritizing for a sealed look
   ahead of 1-3.
   
   Remaining survivors (4h gated stop1.0x/tgt3x, 4h gated stop1.5x/tgt3x,
   4h ungated stop1.0x/tgt3x under 3c range-compression) are the same base
   signals as #2/#3 at different stop/target multipliers — listed in the
   table for completeness but not separately ranked.

INSUFFICIENT-SAMPLE (7 configs, all 3c-range-compression 4h
L24<0.5x-trailing-median, both gated and ungated): positive train+val
expectancy but val_n of 1-2 trades — not enough to mean anything (one
config's val "edge" is a single $169/t trade). Logged, not treated as
evidence either way; worth revisiting only if the trailing-median window
choice (180d, not spec-fixed) is deliberately widened in a future round.

---

## 7. Honest summary

- **Order blocks (64 configs): zero survivors.** Neither the base
  retracement-entry variant nor the breaker/failed-block variant produced
  a single train+val-positive config on either timeframe, across both
  impulse definitions, both touch styles, both target multipliers. This is
  a clean, broad negative result for the last piece of the program's SMC
  toolset (FVGs presumably tested in round 56; order blocks now tested
  here) — not a near-miss, not a sample-size problem (thousands of trades
  per config), a real structural failure to find edge in the mechanical
  form tested.
- **Rejection candles (112 configs across pin bars/engulfing/inside-bar):
  zero survivors.** Context requirement made train expectancy WORSE, not
  better (section 4) — the opposite of the discretionary-trading premise
  that a level is what makes a rejection candle tradeable.
- **NR squeeze (32 configs): zero survivors.** The simplest compression
  family (narrowest-range-bar breakout) never cleared train+val positive.
- **BB-width squeeze and range-compression breakout (88 configs
  combined): 10 of the program's 296 configs survived**, all from these
  two families — both explicitly STATISTICAL volatility-regime gates
  (percentile-of-own-trailing-distribution), not pattern-recognition
  rules. The through-line across this round's only real edge: comparing
  CURRENT volatility to its OWN recent history beats reading candle
  shapes or fixed structural levels.
- **Biggest caveat**: several of the 10 survivors show val expectancy
  MUCH larger than train (e.g. 3b 4h ungated trailing: train $11.64/t ->
  val $80.02/t; 3b 1h gated tgt2xATR: train $2.83/t -> val $25.33/t). That
  asymmetry is a flag, not a bonus — it usually means the val window
  (2025-04-16 onward) contains a specific regime (a strong trending or
  volatility-expansion stretch) that flatters these configs rather than a
  durable edge that would repeat in any window. None of this round's
  candidates should be treated as sealed-look-ready without first checking
  whether that val-window flattery pattern holds up under a wider
  train/val boundary sensitivity check — this script deliberately did NOT
  spend any of the program's sealed test looks; that decision is the
  lead's to make.
