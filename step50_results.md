# Round 50 — Volume Absorption / Effort-vs-Result Divergence (BTC day-trade)

Formalizing and gauntlet-testing the owner's own chart read: *"if the
volume candle is exponentially long compared to the others but the price
candle doesn't match it — that's a very strong sign it's going the other
way."* Classic absorption / stopping-volume. First volume-shape family
ever tested in this repo — every prior fast family (round 43/45) was
price/OI-only and died to the 2025-26 grind's cost floor.

Script: `step50_volume_absorption.py`. Full raw grid:
`step50_results_raw.csv` (240 rows). Full event-study raw:
`step50_event_study_raw.csv`. Research only — no commits, no live orders,
no other step*.py file touched.

---

## 1. Volume-data sanity

| tf | bars | mean vol | median vol | min | max | zeros | NaNs |
|---|---|---|---|---|---|---|---|
| 15m | 221,823 | 966.85 | 494.06 | 0.0000 | 86,368.51 | 2 | 0 |
| 1h | 55,451 | 3,867.60 | 2,226.40 | 0.0040 | 170,105.79 | 0 | 0 |

Both timeframes are **clean and usable** — 2 zero-volume bars out of
221,823 on 15m (both at the very start of the series, 2020-03-25, before
the pair had real liquidity), zero NaNs anywhere, sane BTC-unit
magnitudes, and a plausible right-skewed distribution (mean >> median,
consistent with real volume having occasional huge prints — exactly the
shape a volume-shock family needs). No workaround was needed; both
timeframes ran the full grid.

Gauntlet splits (chronological 60/20/20, test never touched):

| tf | n bars | train ends | val ends (test sealed) | median train ATR% |
|---|---|---|---|---|
| 15m | 221,823 | 2024-01-10 | 2025-04-16 | 0.361% |
| 1h | 55,451 | 2024-01-10 | 2025-04-16 | 0.809% |

---

## 2. Event counts — how rare is a true absorption print?

Counted over train+val only (the sealed test window is never touched),
using family A's entry condition (volume shock AND small bar return),
`m` fixed at 1.0 for this count:

| tf | K | long events | short events | total | % of bars | ~1 event every |
|---|---|---|---|---|---|---|
| 15m | 4 | 950 | 940 | 1,890 | 1.065% | ~94 bars (~23.5h) |
| 15m | 6 | 334 | 350 | 684 | 0.385% | ~259 bars (~2.7 days) |
| 15m | 10 | 84 | 87 | 171 | 0.096% | ~1,038 bars (~10.8 days) |
| 1h | 4 | 143 | 191 | 334 | 0.753% | ~133 bars (~5.5 days) |
| 1h | 6 | 42 | 59 | 101 | 0.228% | ~439 bars (~18.3 days) |
| 1h | 10 | 6 | 15 | 21 | 0.047% | ~2,112 bars (~88 days) |

Absorption prints are genuinely rare, and rarity compounds fast with K —
at K=10 on 1h there are only 21 qualifying bars across 5.75 years of
train+val (~one every three months). That is too thin to trust on its
own no matter what the backtest number says, which is exactly what the
grid shows below (K=10 configs bounce between huge wins and huge losses
depending on geometry — classic small-sample noise, not signal).

---

## 3. Event study — does the owner's eye see something real?

Independent of any stop/target geometry: forward {4, 24}-bar raw price
return after a family-A event (K in {4,6,10}, m=1.0), long and short
sides separate, vs the unconditional baseline over the same train+val
slice. LONG = huge red-candle volume + tiny drop (thesis: selling got
absorbed, price bounces — forward return should be POSITIVE). SHORT =
huge green-candle volume + tiny rise (thesis: buying got absorbed, price
fades — forward return should be NEGATIVE, i.e. below baseline / below 0).

| tf | K | horizon | side | n | mean fwd ret% | median fwd ret% | % positive | baseline mean% |
|---|---|---|---|---|---|---|---|---|
| 15m | 4 | 4 | LONG | 950 | 0.019 | 0.032 | 53.4% | 0.008 |
| 15m | 4 | 4 | SHORT | 940 | 0.037 | 0.017 | 52.4% | 0.008 |
| 15m | 4 | 24 | LONG | 950 | 0.100 | 0.105 | 54.1% | 0.047 |
| 15m | 4 | 24 | SHORT | 940 | 0.137 | 0.088 | 53.1% | 0.047 |
| 15m | 6 | 4 | LONG | 334 | 0.000 | 0.008 | 50.3% | 0.008 |
| 15m | 6 | 4 | SHORT | 350 | 0.053 | 0.027 | 54.0% | 0.008 |
| 15m | 6 | 24 | LONG | 334 | 0.070 | 0.094 | 53.0% | 0.047 |
| 15m | 6 | 24 | SHORT | 350 | 0.140 | 0.068 | 52.0% | 0.047 |
| 15m | 10 | 4 | LONG | 84 | -0.034 | 0.046 | 54.8% | 0.008 |
| 15m | 10 | 4 | SHORT | 87 | -0.054 | 0.011 | 54.0% | 0.008 |
| 15m | 10 | 24 | LONG | 84 | -0.028 | 0.051 | 54.8% | 0.047 |
| 15m | 10 | 24 | SHORT | 87 | 0.168 | -0.006 | 48.3% | 0.047 |
| 1h | 4 | 4 | LONG | 143 | 0.076 | 0.087 | 53.1% | 0.032 |
| 1h | 4 | 4 | SHORT | 191 | 0.053 | 0.040 | 51.8% | 0.032 |
| 1h | 4 | 24 | LONG | 143 | 0.162 | 0.325 | 56.6% | 0.189 |
| 1h | 4 | 24 | SHORT | 191 | 0.184 | 0.106 | 52.4% | 0.189 |
| 1h | 6 | 4 | LONG | 42 | 0.364 | 0.401 | 71.4% | 0.032 |
| 1h | 6 | 4 | SHORT | 59 | **-0.197** | -0.140 | 42.4% | 0.032 |
| 1h | 6 | 24 | LONG | 42 | 0.262 | 0.475 | 64.3% | 0.189 |
| 1h | 6 | 24 | SHORT | 59 | 0.507 | 0.278 | 55.9% | 0.189 |
| 1h | 10 | 4 | LONG | 6 | 1.164 | 0.634 | 83.3% | 0.032 |
| 1h | 10 | 4 | SHORT | 15 | 0.090 | 0.075 | 53.3% | 0.032 |
| 1h | 10 | 24 | LONG | 6 | 1.471 | 0.863 | 83.3% | 0.189 |
| 1h | 10 | 24 | SHORT | 15 | 1.350 | 0.563 | 66.7% | 0.189 |

**Reading it plainly:**

- **LONG side (fading a huge red-volume, tiny-drop bar by buying)** shows
  a small, fairly consistent positive tilt above baseline across almost
  every K/timeframe/horizon (14 of 16 non-K=10-15m rows beat baseline;
  the two 15m K=10 misses are the thin n=84 cell). This is the half of
  the owner's read that the data actually supports — modestly. The
  magnitudes are small (tenths of a percent over 4-24 bars) and n gets
  thin fast as K rises, but the DIRECTION is consistent.
- **SHORT side (fading a huge green-volume, tiny-rise bar by selling)**
  does **not** hold up. Forward returns after these events are mostly
  ABOVE baseline (bad for the fade-short thesis — price kept drifting up,
  not down) at every K and both horizons, except one cell: 1h K=6 at the
  4-bar horizon (-0.197%, n=59) — and even that flips sign by the
  24-bar horizon (+0.507%) in the very same sample. That is not a
  reversal that survives its own follow-through window; it reads as
  noise on a 59-trade sample, not a real short edge.
- **Net honest answer: the owner's eye is seeing something real, but only
  on the LONG (buy the absorbed dip) half.** The SHORT (fade the absorbed
  rip) half of the same intuition does not show up in the raw, geometry-
  free numbers. This is a genuinely useful, falsifiable finding — the
  "exponentially long volume, tiny price move" tell works better as a
  dip-buy signal than as a rip-fade signal in BTC's actual history.

---

## 4. Full config table (240 configs)

Geometry grid: stop = {1.0, 1.5}xATR(14) (TRAIN-median ATR%, held fixed,
capped at 1.7% — this repo's established stop approximation, see step41/
step43 headers), target = {2, 3}x stop, max_hold in {8h, 24h}. A: K in
{4,6,10} x m in {1.0,1.5}. B: K in {4,6,10} x wick-upper{40,50}%.
C: K in {4,6,10} (m fixed at 2.0 for the "moved with it" gate).

**Verdict counts:**

| family | tf | FAIL | SURVIVOR | INSUFFICIENT-SAMPLE |
|---|---|---|---|---|
| A-absorption-fade | 15m | 48 | 0 | 0 |
| A-absorption-fade | 1h | 34 | 12 | 2 |
| B-stopping-volume | 15m | 48 | 0 | 0 |
| B-stopping-volume | 1h | 48 | 0 | 0 |
| C-shock-continuation | 15m | 21 | 3 | 0 |
| C-shock-continuation | 1h | 13 | 11 | 0 |

**240 configs total: 212 FAIL, 26 SURVIVOR, 2 INSUFFICIENT-SAMPLE.**

Full 240-row grid (stop%/target% are the actual fixed percentages used;
`config` encodes K, m/wick-frac, stop mult, target mult, hold hours):

```
              family  tf                                            config  stop%  target%  max_hold_h  tr_n  tr_exp  tr_win%  va_n  va_exp  va_win%  med_hold_h             verdict
   A-absorption-fade 15m        K>=10 m<=1.0 stop1.0xATR tgt2xstop hold24h   0.36     0.72          24   113  -15.98    25.66    25  -14.79    28.00        0.25                FAIL
   A-absorption-fade 15m         K>=10 m<=1.0 stop1.0xATR tgt2xstop hold8h   0.36     0.72           8   125  -15.77    27.20    24  -15.21    29.17        0.25                FAIL
   A-absorption-fade 15m        K>=10 m<=1.0 stop1.0xATR tgt3xstop hold24h   0.36     1.08          24   113  -17.11    19.47    25  -16.78    20.00        0.38                FAIL
   A-absorption-fade 15m         K>=10 m<=1.0 stop1.0xATR tgt3xstop hold8h   0.36     1.08           8   125  -15.63    23.20    24  -18.07    20.83        0.50                FAIL
   A-absorption-fade 15m        K>=10 m<=1.0 stop1.5xATR tgt2xstop hold24h   0.54     1.08          24   113  -10.95    32.74    25  -15.21    28.00        0.88                FAIL
   A-absorption-fade 15m         K>=10 m<=1.0 stop1.5xATR tgt2xstop hold8h   0.54     1.08           8   125  -12.18    33.60    24  -17.56    29.17        1.00                FAIL
   A-absorption-fade 15m        K>=10 m<=1.0 stop1.5xATR tgt3xstop hold24h   0.54     1.63          24   113   -7.38    29.20    25  -17.89    20.00        1.12                FAIL
   A-absorption-fade 15m         K>=10 m<=1.0 stop1.5xATR tgt3xstop hold8h   0.54     1.63           8   125  -11.40    30.40    24  -17.67    29.17        1.25                FAIL
   A-absorption-fade 15m        K>=10 m<=1.5 stop1.0xATR tgt2xstop hold24h   0.36     0.72          24   155  -15.89    25.16    42  -13.99    28.57        0.25                FAIL
   A-absorption-fade 15m         K>=10 m<=1.5 stop1.0xATR tgt2xstop hold8h   0.36     0.72           8   176  -11.62    30.11    45  -12.10    31.11        0.25                FAIL
   A-absorption-fade 15m        K>=10 m<=1.5 stop1.0xATR tgt3xstop hold24h   0.36     1.08          24   155  -18.30    17.42    42   -7.67    26.19        0.50                FAIL
   A-absorption-fade 15m         K>=10 m<=1.5 stop1.0xATR tgt3xstop hold8h   0.36     1.08           8   176  -12.81    23.86    45   -8.30    26.67        0.50                FAIL
   A-absorption-fade 15m        K>=10 m<=1.5 stop1.5xATR tgt2xstop hold24h   0.54     1.08          24   155  -13.96    30.32    42   -7.42    33.33        1.00                FAIL
   A-absorption-fade 15m         K>=10 m<=1.5 stop1.5xATR tgt2xstop hold8h   0.54     1.08           8   176   -9.82    33.52    45   -5.31    35.56        1.00                FAIL
   A-absorption-fade 15m        K>=10 m<=1.5 stop1.5xATR tgt3xstop hold24h   0.54     1.63          24   155  -11.12    26.45    42  -13.94    23.81        1.25                FAIL
   A-absorption-fade 15m         K>=10 m<=1.5 stop1.5xATR tgt3xstop hold8h   0.54     1.63           8   176   -7.06    31.25    45   -5.23    33.33        1.25                FAIL
   A-absorption-fade 15m         K>=4 m<=1.0 stop1.0xATR tgt2xstop hold24h   0.36     0.72          24   628   -8.84    29.94   221   -8.28    33.03        0.50                FAIL
   A-absorption-fade 15m          K>=4 m<=1.0 stop1.0xATR tgt2xstop hold8h   0.36     0.72           8   909   -7.00    32.34   292   -8.69    32.53        0.50                FAIL
   A-absorption-fade 15m         K>=4 m<=1.0 stop1.0xATR tgt3xstop hold24h   0.36     1.08          24   628   -7.84    24.52   221  -10.20    23.98        0.50                FAIL
   A-absorption-fade 15m          K>=4 m<=1.0 stop1.0xATR tgt3xstop hold8h   0.36     1.08           8   909   -6.53    27.61   292   -9.62    25.34        0.75                FAIL
   A-absorption-fade 15m         K>=4 m<=1.0 stop1.5xATR tgt2xstop hold24h   0.54     1.08          24   628   -5.90    34.87   221  -12.78    29.86        1.25                FAIL
   A-absorption-fade 15m          K>=4 m<=1.0 stop1.5xATR tgt2xstop hold8h   0.54     1.08           8   909   -5.91    36.63   292  -10.45    32.53        1.25                FAIL
   A-absorption-fade 15m         K>=4 m<=1.0 stop1.5xATR tgt3xstop hold24h   0.54     1.63          24   628   -2.48    30.25   221  -12.20    23.98        1.50                FAIL
   A-absorption-fade 15m          K>=4 m<=1.0 stop1.5xATR tgt3xstop hold8h   0.54     1.63           8   909   -4.76    33.22   292  -11.05    29.11        1.75                FAIL
   A-absorption-fade 15m         K>=4 m<=1.5 stop1.0xATR tgt2xstop hold24h   0.36     0.72          24   764   -8.54    29.06   265  -10.88    29.81        0.50                FAIL
   A-absorption-fade 15m          K>=4 m<=1.5 stop1.0xATR tgt2xstop hold8h   0.36     0.72           8  1164   -5.85    33.16   381   -8.26    32.55        0.50                FAIL
   A-absorption-fade 15m         K>=4 m<=1.5 stop1.0xATR tgt3xstop hold24h   0.36     1.08          24   764   -8.00    23.30   265  -12.09    21.89        0.50                FAIL
   A-absorption-fade 15m          K>=4 m<=1.5 stop1.0xATR tgt3xstop hold8h   0.36     1.08           8  1164   -5.62    28.01   381   -9.43    25.20        0.75                FAIL
   A-absorption-fade 15m         K>=4 m<=1.5 stop1.5xATR tgt2xstop hold24h   0.54     1.08          24   764   -7.59    31.94   265  -11.88    30.57        1.00                FAIL
   A-absorption-fade 15m          K>=4 m<=1.5 stop1.5xATR tgt2xstop hold8h   0.54     1.08           8  1164   -5.00    37.11   381   -9.39    33.07        1.25                FAIL
   A-absorption-fade 15m         K>=4 m<=1.5 stop1.5xATR tgt3xstop hold24h   0.54     1.63          24   764   -6.58    26.96   265  -10.42    25.28        1.50                FAIL
   A-absorption-fade 15m          K>=4 m<=1.5 stop1.5xATR tgt3xstop hold8h   0.54     1.63           8  1164   -4.10    33.59   381   -8.40    29.92        1.75                FAIL
   A-absorption-fade 15m         K>=6 m<=1.0 stop1.0xATR tgt2xstop hold24h   0.36     0.72          24   337  -10.56    29.97   109  -12.48    29.36        0.25                FAIL
   A-absorption-fade 15m          K>=6 m<=1.0 stop1.0xATR tgt2xstop hold8h   0.36     0.72           8   415   -9.56    31.33   126  -14.71    27.78        0.25                FAIL
   A-absorption-fade 15m         K>=6 m<=1.0 stop1.0xATR tgt3xstop hold24h   0.36     1.08          24   337   -9.97    24.04   109  -11.77    22.94        0.50                FAIL
   A-absorption-fade 15m          K>=6 m<=1.0 stop1.0xATR tgt3xstop hold8h   0.36     1.08           8   415   -9.69    26.75   126  -13.40    23.02        0.50                FAIL
   A-absorption-fade 15m         K>=6 m<=1.0 stop1.5xATR tgt2xstop hold24h   0.54     1.08          24   337   -7.70    34.12   109  -16.54    27.52        1.00                FAIL
   A-absorption-fade 15m          K>=6 m<=1.0 stop1.5xATR tgt2xstop hold8h   0.54     1.08           8   415   -8.64    35.66   126  -16.23    29.37        1.00                FAIL
   A-absorption-fade 15m         K>=6 m<=1.0 stop1.5xATR tgt3xstop hold24h   0.54     1.63          24   337   -1.73    30.56   109  -11.62    23.85        1.25                FAIL
   A-absorption-fade 15m          K>=6 m<=1.0 stop1.5xATR tgt3xstop hold8h   0.54     1.63           8   415   -6.21    33.01   126  -14.61    27.78        1.25                FAIL
   A-absorption-fade 15m         K>=6 m<=1.5 stop1.0xATR tgt2xstop hold24h   0.36     0.72          24   440   -8.40    31.82   162  -12.37    29.01        0.25                FAIL
   A-absorption-fade 15m          K>=6 m<=1.5 stop1.0xATR tgt2xstop hold8h   0.36     0.72           8   570   -6.16    35.09   201  -13.49    27.86        0.25                FAIL
   A-absorption-fade 15m         K>=6 m<=1.5 stop1.0xATR tgt3xstop hold24h   0.36     1.08          24   440   -7.47    25.68   162  -13.72    20.99        0.50                FAIL
   A-absorption-fade 15m          K>=6 m<=1.5 stop1.0xATR tgt3xstop hold8h   0.36     1.08           8   570   -5.95    30.00   201  -12.99    22.39        0.50                FAIL
   A-absorption-fade 15m         K>=6 m<=1.5 stop1.5xATR tgt2xstop hold24h   0.54     1.08          24   440   -6.87    34.09   162  -14.84    28.40        1.00                FAIL
   A-absorption-fade 15m          K>=6 m<=1.5 stop1.5xATR tgt2xstop hold8h   0.54     1.08           8   570   -5.45    38.07   201  -13.48    30.35        1.00                FAIL
   A-absorption-fade 15m         K>=6 m<=1.5 stop1.5xATR tgt3xstop hold24h   0.54     1.63          24   440   -3.82    29.55   162  -11.56    24.07        1.25                FAIL
   A-absorption-fade 15m          K>=6 m<=1.5 stop1.5xATR tgt3xstop hold8h   0.54     1.63           8   570   -3.66    34.91   201  -11.10    28.86        1.50                FAIL
   A-absorption-fade  1h        K>=10 m<=1.0 stop1.0xATR tgt2xstop hold24h   0.81     1.62          24    17   33.36    52.94     4  -30.02    25.00        2.00                FAIL
   A-absorption-fade  1h         K>=10 m<=1.0 stop1.0xATR tgt2xstop hold8h   0.81     1.62           8    17   32.38    52.94     4  -30.02    25.00        2.00                FAIL
   A-absorption-fade  1h        K>=10 m<=1.0 stop1.0xATR tgt3xstop hold24h   0.81     2.43          24    17   -2.19    41.18     4  -10.35    25.00        4.00                FAIL
   A-absorption-fade  1h         K>=10 m<=1.0 stop1.0xATR tgt3xstop hold8h   0.81     2.43           8    17   -2.12    41.18     4  -10.35    25.00        4.00                FAIL
   A-absorption-fade  1h        K>=10 m<=1.0 stop1.5xATR tgt2xstop hold24h   1.21     2.43          24    17  -17.55    41.18     4  -40.67    25.00        4.00                FAIL
   A-absorption-fade  1h         K>=10 m<=1.0 stop1.5xATR tgt2xstop hold8h   1.21     2.43           8    17  -15.30    47.06     4  -40.67    25.00        4.00                FAIL
   A-absorption-fade  1h        K>=10 m<=1.0 stop1.5xATR tgt3xstop hold24h   1.21     3.64          24    17   -4.01    41.18     4  -11.53    25.00        4.00                FAIL
   A-absorption-fade  1h         K>=10 m<=1.0 stop1.5xATR tgt3xstop hold8h   1.21     3.64           8    17  -11.06    47.06     4  -11.53    25.00        4.00                FAIL
   A-absorption-fade  1h        K>=10 m<=1.5 stop1.0xATR tgt2xstop hold24h   0.81     1.62          24    20   17.43    45.00     5    7.15    40.00        2.00 INSUFFICIENT-SAMPLE
   A-absorption-fade  1h         K>=10 m<=1.5 stop1.0xATR tgt2xstop hold8h   0.81     1.62           8    20   21.63    45.00     5    7.15    40.00        2.00 INSUFFICIENT-SAMPLE
   A-absorption-fade  1h        K>=10 m<=1.5 stop1.0xATR tgt3xstop hold24h   0.81     2.43          24    20  -12.16    35.00     5   39.22    40.00        4.00                FAIL
   A-absorption-fade  1h         K>=10 m<=1.5 stop1.0xATR tgt3xstop hold8h   0.81     2.43           8    20   -7.37    35.00     5   39.22    40.00        4.00                FAIL
   A-absorption-fade  1h        K>=10 m<=1.5 stop1.5xATR tgt2xstop hold24h   1.21     2.43          24    20  -23.75    35.00     5   14.38    40.00        4.00                FAIL
   A-absorption-fade  1h         K>=10 m<=1.5 stop1.5xATR tgt2xstop hold8h   1.21     2.43           8    20  -20.42    40.00     5   14.38    40.00        4.00                FAIL
   A-absorption-fade  1h        K>=10 m<=1.5 stop1.5xATR tgt3xstop hold24h   1.21     3.64          24    20  -12.45    35.00     5  -35.90    20.00        6.00                FAIL
   A-absorption-fade  1h         K>=10 m<=1.5 stop1.5xATR tgt3xstop hold8h   1.21     3.64           8    20  -16.86    40.00     5  -17.91    20.00        6.00                FAIL
   A-absorption-fade  1h         K>=4 m<=1.0 stop1.0xATR tgt2xstop hold24h   0.81     1.62          24   180   -0.75    37.78    72   10.47    41.67        2.00                FAIL
   A-absorption-fade  1h          K>=4 m<=1.0 stop1.0xATR tgt2xstop hold8h   0.81     1.62           8   204    0.53    44.12    81   14.65    46.91        2.00            SURVIVOR
   A-absorption-fade  1h         K>=4 m<=1.0 stop1.0xATR tgt3xstop hold24h   0.81     2.43          24   180   -5.91    30.56    72   -2.06    29.17        3.00                FAIL
   A-absorption-fade  1h          K>=4 m<=1.0 stop1.0xATR tgt3xstop hold8h   0.81     2.43           8   204   -5.08    39.22    81    6.50    38.27        3.00                FAIL
   A-absorption-fade  1h         K>=4 m<=1.0 stop1.5xATR tgt2xstop hold24h   1.21     2.43          24   180   -0.50    41.11    72   -5.78    37.50        6.00                FAIL
   A-absorption-fade  1h          K>=4 m<=1.0 stop1.5xATR tgt2xstop hold8h   1.21     2.43           8   204   -2.95    47.06    81    3.99    45.68        6.00                FAIL
   A-absorption-fade  1h         K>=4 m<=1.0 stop1.5xATR tgt3xstop hold24h   1.21     3.64          24   180   -2.78    38.33    72   15.96    37.50       10.00                FAIL
   A-absorption-fade  1h          K>=4 m<=1.0 stop1.5xATR tgt3xstop hold8h   1.21     3.64           8   204   -5.41    46.57    81    9.22    45.68        8.00                FAIL
   A-absorption-fade  1h         K>=4 m<=1.5 stop1.0xATR tgt2xstop hold24h   0.81     1.62          24   239   -7.30    35.15    91    8.19    40.66        2.00                FAIL
   A-absorption-fade  1h          K>=4 m<=1.5 stop1.0xATR tgt2xstop hold8h   0.81     1.62           8   285   -6.88    39.65   110   10.16    46.36        2.00                FAIL
   A-absorption-fade  1h         K>=4 m<=1.5 stop1.0xATR tgt3xstop hold24h   0.81     2.43          24   239   -8.01    30.13    91   -5.93    28.57        3.00                FAIL
   A-absorption-fade  1h          K>=4 m<=1.5 stop1.0xATR tgt3xstop hold8h   0.81     2.43           8   285   -8.55    36.49   110    5.14    40.91        3.00                FAIL
   A-absorption-fade  1h         K>=4 m<=1.5 stop1.5xATR tgt2xstop hold24h   1.21     2.43          24   239   -7.64    38.91    91  -11.75    35.16        5.00                FAIL
   A-absorption-fade  1h          K>=4 m<=1.5 stop1.5xATR tgt2xstop hold8h   1.21     2.43           8   285   -7.30    43.16   110    2.70    47.27        5.00                FAIL
   A-absorption-fade  1h         K>=4 m<=1.5 stop1.5xATR tgt3xstop hold24h   1.21     3.64          24   239  -11.35    35.56    91    2.42    34.07        9.00                FAIL
   A-absorption-fade  1h          K>=4 m<=1.5 stop1.5xATR tgt3xstop hold8h   1.21     3.64           8   285   -7.96    42.81   110    2.78    45.45        8.00                FAIL
   A-absorption-fade  1h         K>=6 m<=1.0 stop1.0xATR tgt2xstop hold24h   0.81     1.62          24    65   23.64    47.69    23   63.04    60.87        3.00            SURVIVOR
   A-absorption-fade  1h          K>=6 m<=1.0 stop1.0xATR tgt2xstop hold8h   0.81     1.62           8    69   26.62    56.52    23   67.03    65.22        3.00            SURVIVOR
   A-absorption-fade  1h         K>=6 m<=1.0 stop1.0xATR tgt3xstop hold24h   0.81     2.43          24    65    5.68    36.92    23   75.68    52.17        4.50            SURVIVOR
   A-absorption-fade  1h          K>=6 m<=1.0 stop1.0xATR tgt3xstop hold8h   0.81     2.43           8    69   14.84    50.72    23   68.31    56.52        4.50            SURVIVOR
   A-absorption-fade  1h         K>=6 m<=1.0 stop1.5xATR tgt2xstop hold24h   1.21     2.43          24    65   -4.58    41.54    23   61.35    56.52        6.00                FAIL
   A-absorption-fade  1h          K>=6 m<=1.0 stop1.5xATR tgt2xstop hold8h   1.21     2.43           8    69    7.81    55.07    23   50.12    56.52        6.00            SURVIVOR
   A-absorption-fade  1h         K>=6 m<=1.0 stop1.5xATR tgt3xstop hold24h   1.21     3.64          24    65  -10.60    36.92    23   81.68    52.17        9.00                FAIL
   A-absorption-fade  1h          K>=6 m<=1.0 stop1.5xATR tgt3xstop hold8h   1.21     3.64           8    69    7.77    53.62    23   70.46    56.52        8.00            SURVIVOR
   A-absorption-fade  1h         K>=6 m<=1.5 stop1.0xATR tgt2xstop hold24h   0.81     1.62          24    89   10.96    42.70    31   47.09    54.84        2.50            SURVIVOR
   A-absorption-fade  1h          K>=6 m<=1.5 stop1.0xATR tgt2xstop hold8h   0.81     1.62           8    98   14.30    48.98    31   50.06    58.06        3.00            SURVIVOR
   A-absorption-fade  1h         K>=6 m<=1.5 stop1.0xATR tgt3xstop hold24h   0.81     2.43          24    89   -2.03    33.71    31   44.03    41.94        4.00                FAIL
   A-absorption-fade  1h          K>=6 m<=1.5 stop1.0xATR tgt3xstop hold8h   0.81     2.43           8    98    7.39    43.88    31   43.71    51.61        4.00            SURVIVOR
   A-absorption-fade  1h         K>=6 m<=1.5 stop1.5xATR tgt2xstop hold24h   1.21     2.43          24    89   -3.92    40.45    31   45.19    48.39        7.00                FAIL
   A-absorption-fade  1h          K>=6 m<=1.5 stop1.5xATR tgt2xstop hold8h   1.21     2.43           8    98    6.31    50.00    31   42.91    58.06        6.00            SURVIVOR
   A-absorption-fade  1h         K>=6 m<=1.5 stop1.5xATR tgt3xstop hold24h   1.21     3.64          24    89  -10.20    35.96    31   69.00    45.16       10.50                FAIL
   A-absorption-fade  1h          K>=6 m<=1.5 stop1.5xATR tgt3xstop hold8h   1.21     3.64           8    98    9.15    48.98    31   57.69    54.84        8.00            SURVIVOR
   B-stopping-volume 15m K>=10 wick-upper40% stop1.0xATR tgt2xstop hold24h   0.36     0.72          24   309   -9.36    31.72    72  -20.01    22.22        0.25                FAIL
   B-stopping-volume 15m  K>=10 wick-upper40% stop1.0xATR tgt2xstop hold8h   0.36     0.72           8   372   -8.88    32.80    77  -22.39    19.48        0.25                FAIL
   B-stopping-volume 15m K>=10 wick-upper40% stop1.0xATR tgt3xstop hold24h   0.36     1.08          24   309   -9.85    24.27    72  -22.16    15.28        0.25                FAIL
   B-stopping-volume 15m  K>=10 wick-upper40% stop1.0xATR tgt3xstop hold8h   0.36     1.08           8   372   -9.09    26.88    77  -24.53    12.99        0.25                FAIL
   B-stopping-volume 15m K>=10 wick-upper40% stop1.5xATR tgt2xstop hold24h   0.54     1.08          24   309  -13.31    29.77    72  -25.16    22.22        0.75                FAIL
   B-stopping-volume 15m  K>=10 wick-upper40% stop1.5xATR tgt2xstop hold8h   0.54     1.08           8   372  -11.12    33.33    77  -25.39    22.08        0.75                FAIL
   B-stopping-volume 15m K>=10 wick-upper40% stop1.5xATR tgt3xstop hold24h   0.54     1.63          24   309  -11.79    25.57    72  -17.72    20.83        1.00                FAIL
   B-stopping-volume 15m  K>=10 wick-upper40% stop1.5xATR tgt3xstop hold8h   0.54     1.63           8   372   -9.89    30.91    77  -18.56    20.78        1.00                FAIL
   B-stopping-volume 15m K>=10 wick-upper50% stop1.0xATR tgt2xstop hold24h   0.36     0.72          24   384  -11.07    28.65   103  -10.81    31.07        0.25                FAIL
   B-stopping-volume 15m  K>=10 wick-upper50% stop1.0xATR tgt2xstop hold8h   0.36     0.72           8   486   -9.05    31.89   115  -12.49    29.57        0.25                FAIL
   B-stopping-volume 15m K>=10 wick-upper50% stop1.0xATR tgt3xstop hold24h   0.36     1.08          24   384  -11.61    21.61   103  -12.65    22.33        0.25                FAIL
   B-stopping-volume 15m  K>=10 wick-upper50% stop1.0xATR tgt3xstop hold8h   0.36     1.08           8   486   -9.23    26.34   115  -12.83    22.61        0.25                FAIL
   B-stopping-volume 15m K>=10 wick-upper50% stop1.5xATR tgt2xstop hold24h   0.54     1.08          24   384  -12.92    29.17   103  -14.88    29.13        0.75                FAIL
   B-stopping-volume 15m  K>=10 wick-upper50% stop1.5xATR tgt2xstop hold8h   0.54     1.08           8   486   -9.94    33.95   115  -13.75    30.43        0.75                FAIL
   B-stopping-volume 15m K>=10 wick-upper50% stop1.5xATR tgt3xstop hold24h   0.54     1.63          24   384  -11.77    24.74   103  -10.76    24.27        1.00                FAIL
   B-stopping-volume 15m  K>=10 wick-upper50% stop1.5xATR tgt3xstop hold8h   0.54     1.63           8   486   -9.14    31.48   115  -12.75    25.22        1.00                FAIL
   B-stopping-volume 15m  K>=4 wick-upper40% stop1.0xATR tgt2xstop hold24h   0.36     0.72          24   796   -8.37    29.27   270  -11.91    28.52        0.50                FAIL
   B-stopping-volume 15m   K>=4 wick-upper40% stop1.0xATR tgt2xstop hold8h   0.36     0.72           8  1216   -6.29    31.58   409  -10.31    29.83        0.50                FAIL
   B-stopping-volume 15m  K>=4 wick-upper40% stop1.0xATR tgt3xstop hold24h   0.36     1.08          24   796   -8.16    23.12   270  -10.83    22.96        0.50                FAIL
   B-stopping-volume 15m   K>=4 wick-upper40% stop1.0xATR tgt3xstop hold8h   0.36     1.08           8  1216   -5.99    26.97   409   -9.19    25.18        0.50                FAIL
   B-stopping-volume 15m  K>=4 wick-upper40% stop1.5xATR tgt2xstop hold24h   0.54     1.08          24   796   -9.50    28.77   270   -9.26    32.59        1.00                FAIL
   B-stopping-volume 15m   K>=4 wick-upper40% stop1.5xATR tgt2xstop hold8h   0.54     1.08           8  1216   -6.64    33.47   409   -8.81    33.99        1.25                FAIL
   B-stopping-volume 15m  K>=4 wick-upper40% stop1.5xATR tgt3xstop hold24h   0.54     1.63          24   796   -9.26    23.74   270   -7.45    26.67        1.50                FAIL
   B-stopping-volume 15m   K>=4 wick-upper40% stop1.5xATR tgt3xstop hold8h   0.54     1.63           8  1216   -6.41    30.18   409   -8.86    29.83        1.50                FAIL
   B-stopping-volume 15m  K>=4 wick-upper50% stop1.0xATR tgt2xstop hold24h   0.36     0.72          24   866   -8.30    28.52   302  -11.93    28.15        0.25                FAIL
   B-stopping-volume 15m   K>=4 wick-upper50% stop1.0xATR tgt2xstop hold8h   0.36     0.72           8  1406   -5.74    31.86   464   -8.33    32.33        0.50                FAIL
   B-stopping-volume 15m  K>=4 wick-upper50% stop1.0xATR tgt3xstop hold24h   0.36     1.08          24   866   -8.29    22.06   302  -10.72    22.85        0.50                FAIL
   B-stopping-volume 15m   K>=4 wick-upper50% stop1.0xATR tgt3xstop hold8h   0.36     1.08           8  1406   -5.62    26.88   464   -6.68    27.59        0.50                FAIL
   B-stopping-volume 15m  K>=4 wick-upper50% stop1.5xATR tgt2xstop hold24h   0.54     1.08          24   866   -9.24    28.06   302   -8.43    33.11        1.00                FAIL
   B-stopping-volume 15m   K>=4 wick-upper50% stop1.5xATR tgt2xstop hold8h   0.54     1.08           8  1406   -6.02    33.85   464   -5.59    36.85        1.25                FAIL
   B-stopping-volume 15m  K>=4 wick-upper50% stop1.5xATR tgt3xstop hold24h   0.54     1.63          24   866   -9.36    22.40   302   -6.84    27.15        1.25                FAIL
   B-stopping-volume 15m   K>=4 wick-upper50% stop1.5xATR tgt3xstop hold8h   0.54     1.63           8  1406   -6.02    30.16   464   -7.43    30.82        1.50                FAIL
   B-stopping-volume 15m  K>=6 wick-upper40% stop1.0xATR tgt2xstop hold24h   0.36     0.72          24   569   -7.23    33.22   184  -14.34    26.63        0.25                FAIL
   B-stopping-volume 15m   K>=6 wick-upper40% stop1.0xATR tgt2xstop hold8h   0.36     0.72           8   771   -7.34    32.56   241  -14.55    25.31        0.25                FAIL
   B-stopping-volume 15m  K>=6 wick-upper40% stop1.0xATR tgt3xstop hold24h   0.36     1.08          24   569   -6.69    26.54   184  -14.11    20.65        0.50                FAIL
   B-stopping-volume 15m   K>=6 wick-upper40% stop1.0xATR tgt3xstop hold8h   0.36     1.08           8   771   -6.74    28.15   241  -13.64    20.75        0.50                FAIL
   B-stopping-volume 15m  K>=6 wick-upper40% stop1.5xATR tgt2xstop hold24h   0.54     1.08          24   569   -9.33    31.81   184  -15.48    28.26        1.00                FAIL
   B-stopping-volume 15m   K>=6 wick-upper40% stop1.5xATR tgt2xstop hold8h   0.54     1.08           8   771   -7.36    35.80   241  -13.82    29.05        1.12                FAIL
   B-stopping-volume 15m  K>=6 wick-upper40% stop1.5xATR tgt3xstop hold24h   0.54     1.63          24   569   -9.96    25.31   184  -11.43    24.46        1.25                FAIL
   B-stopping-volume 15m   K>=6 wick-upper40% stop1.5xATR tgt3xstop hold8h   0.54     1.63           8   771   -7.45    32.17   241  -13.20    24.90        1.50                FAIL
   B-stopping-volume 15m  K>=6 wick-upper50% stop1.0xATR tgt2xstop hold24h   0.36     0.72          24   665   -8.95    29.47   215  -11.36    29.77        0.25                FAIL
   B-stopping-volume 15m   K>=6 wick-upper50% stop1.0xATR tgt2xstop hold8h   0.36     0.72           8   942   -7.10    31.95   292  -11.44    29.45        0.25                FAIL
   B-stopping-volume 15m  K>=6 wick-upper50% stop1.0xATR tgt3xstop hold24h   0.36     1.08          24   665   -9.09    22.71   215   -9.77    24.19        0.25                FAIL
   B-stopping-volume 15m   K>=6 wick-upper50% stop1.0xATR tgt3xstop hold8h   0.36     1.08           8   942   -6.89    27.28   292  -10.12    24.66        0.50                FAIL
   B-stopping-volume 15m  K>=6 wick-upper50% stop1.5xATR tgt2xstop hold24h   0.54     1.08          24   665  -10.62    28.57   215  -11.16    31.63        1.00                FAIL
   B-stopping-volume 15m   K>=6 wick-upper50% stop1.5xATR tgt2xstop hold8h   0.54     1.08           8   942   -7.51    34.50   292   -9.94    33.22        1.00                FAIL
   B-stopping-volume 15m  K>=6 wick-upper50% stop1.5xATR tgt3xstop hold24h   0.54     1.63          24   665  -11.23    22.41   215   -5.77    27.91        1.25                FAIL
   B-stopping-volume 15m   K>=6 wick-upper50% stop1.5xATR tgt3xstop hold8h   0.54     1.63           8   942   -7.75    31.00   292  -10.41    27.74        1.50                FAIL
   B-stopping-volume  1h K>=10 wick-upper40% stop1.0xATR tgt2xstop hold24h   0.81     1.62          24    67  -24.40    28.36    19   54.63    57.89        1.00                FAIL
   B-stopping-volume  1h  K>=10 wick-upper40% stop1.0xATR tgt2xstop hold8h   0.81     1.62           8    70  -24.30    28.57    18   57.05    61.11        1.00                FAIL
   B-stopping-volume  1h K>=10 wick-upper40% stop1.0xATR tgt3xstop hold24h   0.81     2.43          24    67  -24.98    23.88    19   40.74    42.11        1.00                FAIL
   B-stopping-volume  1h  K>=10 wick-upper40% stop1.0xATR tgt3xstop hold8h   0.81     2.43           8    70  -25.17    25.71    18   55.06    50.00        1.00                FAIL
   B-stopping-volume  1h K>=10 wick-upper40% stop1.5xATR tgt2xstop hold24h   1.21     2.43          24    67  -23.47    34.33    19   47.59    52.63        4.00                FAIL
   B-stopping-volume  1h  K>=10 wick-upper40% stop1.5xATR tgt2xstop hold8h   1.21     2.43           8    70  -31.57    32.86    18   69.83    55.56        4.00                FAIL
   B-stopping-volume  1h K>=10 wick-upper40% stop1.5xATR tgt3xstop hold24h   1.21     3.64          24    67  -19.71    31.34    19   58.21    47.37        5.00                FAIL
   B-stopping-volume  1h  K>=10 wick-upper40% stop1.5xATR tgt3xstop hold8h   1.21     3.64           8    70  -31.41    31.43    18   61.54    50.00        5.00                FAIL
   B-stopping-volume  1h K>=10 wick-upper50% stop1.0xATR tgt2xstop hold24h   0.81     1.62          24    84  -17.76    32.14    20   33.36    50.00        1.00                FAIL
   B-stopping-volume  1h  K>=10 wick-upper50% stop1.0xATR tgt2xstop hold8h   0.81     1.62           8    91  -19.58    31.87    19   34.55    52.63        1.00                FAIL
   B-stopping-volume  1h K>=10 wick-upper50% stop1.0xATR tgt3xstop hold24h   0.81     2.43          24    84  -21.14    26.19    20   16.48    35.00        1.00                FAIL
   B-stopping-volume  1h  K>=10 wick-upper50% stop1.0xATR tgt3xstop hold8h   0.81     2.43           8    91  -24.01    27.47    19   28.30    42.11        1.00                FAIL
   B-stopping-volume  1h K>=10 wick-upper50% stop1.5xATR tgt2xstop hold24h   1.21     2.43          24    84  -25.61    33.33    20   18.47    45.00        4.50                FAIL
   B-stopping-volume  1h  K>=10 wick-upper50% stop1.5xATR tgt2xstop hold8h   1.21     2.43           8    91  -30.85    34.07    19   37.09    47.37        4.00                FAIL
   B-stopping-volume  1h K>=10 wick-upper50% stop1.5xATR tgt3xstop hold24h   1.21     3.64          24    84  -26.46    29.76    20   47.84    45.00        5.00                FAIL
   B-stopping-volume  1h  K>=10 wick-upper50% stop1.5xATR tgt3xstop hold8h   1.21     3.64           8    91  -31.13    32.97    19   53.30    47.37        5.00                FAIL
   B-stopping-volume  1h  K>=4 wick-upper40% stop1.0xATR tgt2xstop hold24h   0.81     1.62          24   288  -13.21    33.68   104    7.98    41.35        2.00                FAIL
   B-stopping-volume  1h   K>=4 wick-upper40% stop1.0xATR tgt2xstop hold8h   0.81     1.62           8   353  -10.37    37.68   128   -4.14    38.28        2.00                FAIL
   B-stopping-volume  1h  K>=4 wick-upper40% stop1.0xATR tgt3xstop hold24h   0.81     2.43          24   288  -11.86    30.21   104   -5.70    30.77        3.00                FAIL
   B-stopping-volume  1h   K>=4 wick-upper40% stop1.0xATR tgt3xstop hold8h   0.81     2.43           8   353  -11.69    35.13   128   -5.94    35.16        3.00                FAIL
   B-stopping-volume  1h  K>=4 wick-upper40% stop1.5xATR tgt2xstop hold24h   1.21     2.43          24   288  -16.31    37.50   104  -16.12    35.58        6.00                FAIL
   B-stopping-volume  1h   K>=4 wick-upper40% stop1.5xATR tgt2xstop hold8h   1.21     2.43           8   353  -13.91    41.36   128   -5.90    42.97        6.00                FAIL
   B-stopping-volume  1h  K>=4 wick-upper40% stop1.5xATR tgt3xstop hold24h   1.21     3.64          24   288  -15.13    35.76   104   -8.12    33.65        7.00                FAIL
   B-stopping-volume  1h   K>=4 wick-upper40% stop1.5xATR tgt3xstop hold8h   1.21     3.64           8   353  -12.05    40.79   128   -8.03    40.62        7.00                FAIL
   B-stopping-volume  1h  K>=4 wick-upper50% stop1.0xATR tgt2xstop hold24h   0.81     1.62          24   360   -9.74    35.28   117   -0.05    38.46        2.00                FAIL
   B-stopping-volume  1h   K>=4 wick-upper50% stop1.0xATR tgt2xstop hold8h   0.81     1.62           8   452   -8.97    38.94   150   -8.52    37.33        2.00                FAIL
   B-stopping-volume  1h  K>=4 wick-upper50% stop1.0xATR tgt3xstop hold24h   0.81     2.43          24   360   -9.20    31.39   117  -14.01    28.21        3.00                FAIL
   B-stopping-volume  1h   K>=4 wick-upper50% stop1.0xATR tgt3xstop hold8h   0.81     2.43           8   452  -10.42    35.84   150   -9.49    34.67        3.00                FAIL
   B-stopping-volume  1h  K>=4 wick-upper50% stop1.5xATR tgt2xstop hold24h   1.21     2.43          24   360  -14.60    38.06   117  -25.29    32.48        5.00                FAIL
   B-stopping-volume  1h   K>=4 wick-upper50% stop1.5xATR tgt2xstop hold8h   1.21     2.43           8   452  -13.03    41.59   150  -13.21    40.67        6.00                FAIL
   B-stopping-volume  1h  K>=4 wick-upper50% stop1.5xATR tgt3xstop hold24h   1.21     3.64          24   360  -13.20    36.11   117  -13.36    32.48        6.00                FAIL
   B-stopping-volume  1h   K>=4 wick-upper50% stop1.5xATR tgt3xstop hold8h   1.21     3.64           8   452  -11.36    41.15   150  -12.11    39.33        6.00                FAIL
   B-stopping-volume  1h  K>=6 wick-upper40% stop1.0xATR tgt2xstop hold24h   0.81     1.62          24   159  -15.25    32.70    55    2.65    38.18        1.00                FAIL
   B-stopping-volume  1h   K>=6 wick-upper40% stop1.0xATR tgt2xstop hold8h   0.81     1.62           8   182  -11.49    36.81    58    0.86    37.93        1.00                FAIL
   B-stopping-volume  1h  K>=6 wick-upper40% stop1.0xATR tgt3xstop hold24h   0.81     2.43          24   159  -15.79    29.56    55  -16.88    25.45        2.00                FAIL
   B-stopping-volume  1h   K>=6 wick-upper40% stop1.0xATR tgt3xstop hold8h   0.81     2.43           8   182  -11.97    34.07    58   -3.65    32.76        2.00                FAIL
   B-stopping-volume  1h  K>=6 wick-upper40% stop1.5xATR tgt2xstop hold24h   1.21     2.43          24   159  -13.74    40.88    55  -19.37    32.73        5.00                FAIL
   B-stopping-volume  1h   K>=6 wick-upper40% stop1.5xATR tgt2xstop hold8h   1.21     2.43           8   182  -13.51    42.31    58   -8.00    36.21        5.00                FAIL
   B-stopping-volume  1h  K>=6 wick-upper40% stop1.5xATR tgt3xstop hold24h   1.21     3.64          24   159   -9.98    39.62    55   -9.40    30.91        6.00                FAIL
   B-stopping-volume  1h   K>=6 wick-upper40% stop1.5xATR tgt3xstop hold8h   1.21     3.64           8   182   -9.48    41.76    58  -10.72    34.48        6.00                FAIL
   B-stopping-volume  1h  K>=6 wick-upper50% stop1.0xATR tgt2xstop hold24h   0.81     1.62          24   200  -13.35    34.00    65   -0.47    36.92        1.00                FAIL
   B-stopping-volume  1h   K>=6 wick-upper50% stop1.0xATR tgt2xstop hold8h   0.81     1.62           8   235   -8.56    39.57    69   -3.35    37.68        1.00                FAIL
   B-stopping-volume  1h  K>=6 wick-upper50% stop1.0xATR tgt3xstop hold24h   0.81     2.43          24   200  -14.60    30.50    65  -21.38    23.08        2.00                FAIL
   B-stopping-volume  1h   K>=6 wick-upper50% stop1.0xATR tgt3xstop hold8h   0.81     2.43           8   235   -7.87    37.02    69   -5.94    33.33        2.00                FAIL
   B-stopping-volume  1h  K>=6 wick-upper50% stop1.5xATR tgt2xstop hold24h   1.21     2.43          24   200  -15.83    40.00    65  -27.19    30.77        5.00                FAIL
   B-stopping-volume  1h   K>=6 wick-upper50% stop1.5xATR tgt2xstop hold8h   1.21     2.43           8   235  -10.73    44.26    69  -12.74    36.23        5.00                FAIL
   B-stopping-volume  1h  K>=6 wick-upper50% stop1.5xATR tgt3xstop hold24h   1.21     3.64          24   200  -12.24    39.00    65  -11.03    30.77        6.00                FAIL
   B-stopping-volume  1h   K>=6 wick-upper50% stop1.5xATR tgt3xstop hold8h   1.21     3.64           8   235   -6.15    43.83    69   -6.82    36.23        6.00                FAIL
C-shock-continuation 15m  K>=10 continuation stop1.0xATR tgt2xstop hold24h   0.36     0.72          24   588   -2.20    38.95   171   -2.68    38.60        0.25                FAIL
C-shock-continuation 15m   K>=10 continuation stop1.0xATR tgt2xstop hold8h   0.36     0.72           8   839   -4.15    36.47   223   -4.18    37.67        0.25                FAIL
C-shock-continuation 15m  K>=10 continuation stop1.0xATR tgt3xstop hold24h   0.36     1.08          24   588   -1.28    30.95   171    0.49    31.58        0.25                FAIL
C-shock-continuation 15m   K>=10 continuation stop1.0xATR tgt3xstop hold8h   0.36     1.08           8   839   -3.04    30.15   223    0.11    32.29        0.25                FAIL
C-shock-continuation 15m  K>=10 continuation stop1.5xATR tgt2xstop hold24h   0.54     1.08          24   588    2.94    40.82   171    5.09    41.52        0.50            SURVIVOR
C-shock-continuation 15m   K>=10 continuation stop1.5xATR tgt2xstop hold8h   0.54     1.08           8   839   -0.51    38.86   223    2.59    40.81        0.75                FAIL
C-shock-continuation 15m  K>=10 continuation stop1.5xATR tgt3xstop hold24h   0.54     1.63          24   588    4.64    32.65   171   12.68    34.50        1.00            SURVIVOR
C-shock-continuation 15m   K>=10 continuation stop1.5xATR tgt3xstop hold8h   0.54     1.63           8   839   -1.10    32.78   223    8.52    35.43        1.00                FAIL
C-shock-continuation 15m   K>=4 continuation stop1.0xATR tgt2xstop hold24h   0.36     0.72          24  1054   -4.46    35.77   359   -8.40    32.31        0.25                FAIL
C-shock-continuation 15m    K>=4 continuation stop1.0xATR tgt2xstop hold8h   0.36     0.72           8  1947   -3.68    35.70   607   -6.86    33.28        0.25                FAIL
C-shock-continuation 15m   K>=4 continuation stop1.0xATR tgt3xstop hold24h   0.36     1.08          24  1054   -3.99    27.99   359   -7.95    25.07        0.50                FAIL
C-shock-continuation 15m    K>=4 continuation stop1.0xATR tgt3xstop hold8h   0.36     1.08           8  1947   -3.09    29.74   607   -5.41    28.01        0.50                FAIL
C-shock-continuation 15m   K>=4 continuation stop1.5xATR tgt2xstop hold24h   0.54     1.08          24  1054   -3.60    36.15   359   -5.13    35.38        1.00                FAIL
C-shock-continuation 15m    K>=4 continuation stop1.5xATR tgt2xstop hold8h   0.54     1.08           8  1947   -2.79    37.24   607   -3.23    37.40        1.00                FAIL
C-shock-continuation 15m   K>=4 continuation stop1.5xATR tgt3xstop hold24h   0.54     1.63          24  1054   -1.76    29.51   359   -1.40    29.25        1.50                FAIL
C-shock-continuation 15m    K>=4 continuation stop1.5xATR tgt3xstop hold8h   0.54     1.63           8  1947   -1.96    32.00   607   -1.11    32.29        1.50                FAIL
C-shock-continuation 15m   K>=6 continuation stop1.0xATR tgt2xstop hold24h   0.36     0.72          24   876   -3.61    37.33   294   -7.15    34.01        0.25                FAIL
C-shock-continuation 15m    K>=6 continuation stop1.0xATR tgt2xstop hold8h   0.36     0.72           8  1437   -3.93    36.12   453   -7.52    33.33        0.25                FAIL
C-shock-continuation 15m   K>=6 continuation stop1.0xATR tgt3xstop hold24h   0.36     1.08          24   876   -1.26    30.82   294   -4.29    28.23        0.50                FAIL
C-shock-continuation 15m    K>=6 continuation stop1.0xATR tgt3xstop hold8h   0.36     1.08           8  1437   -2.45    30.97   453   -6.41    27.59        0.50                FAIL
C-shock-continuation 15m   K>=6 continuation stop1.5xATR tgt2xstop hold24h   0.54     1.08          24   876   -0.18    38.93   294   -0.34    38.44        0.75                FAIL
C-shock-continuation 15m    K>=6 continuation stop1.5xATR tgt2xstop hold8h   0.54     1.08           8  1437   -2.17    38.41   453   -3.72    37.31        1.00                FAIL
C-shock-continuation 15m   K>=6 continuation stop1.5xATR tgt3xstop hold24h   0.54     1.63          24   876    2.12    31.16   294    2.27    30.27        1.25            SURVIVOR
C-shock-continuation 15m    K>=6 continuation stop1.5xATR tgt3xstop hold8h   0.54     1.63           8  1437   -1.66    32.92   453   -1.90    32.45        1.25                FAIL
C-shock-continuation  1h  K>=10 continuation stop1.0xATR tgt2xstop hold24h   0.81     1.62          24   168  -11.02    33.33    47   19.58    44.68        1.00                FAIL
C-shock-continuation  1h   K>=10 continuation stop1.0xATR tgt2xstop hold8h   0.81     1.62           8   200   -9.98    35.00    54   26.09    48.15        2.00                FAIL
C-shock-continuation  1h  K>=10 continuation stop1.0xATR tgt3xstop hold24h   0.81     2.43          24   168   -4.95    29.76    47   25.09    36.17        2.00                FAIL
C-shock-continuation  1h   K>=10 continuation stop1.0xATR tgt3xstop hold8h   0.81     2.43           8   200   -4.33    33.50    54   30.31    44.44        2.00                FAIL
C-shock-continuation  1h  K>=10 continuation stop1.5xATR tgt2xstop hold24h   1.21     2.43          24   168   -7.58    36.31    47   32.32    44.68        5.00                FAIL
C-shock-continuation  1h   K>=10 continuation stop1.5xATR tgt2xstop hold8h   1.21     2.43           8   200    1.21    39.50    54   35.81    51.85        5.00            SURVIVOR
C-shock-continuation  1h  K>=10 continuation stop1.5xATR tgt3xstop hold24h   1.21     3.64          24   168   -7.56    32.74    47   66.96    44.68        8.00                FAIL
C-shock-continuation  1h   K>=10 continuation stop1.5xATR tgt3xstop hold8h   1.21     3.64           8   200    1.59    37.50    54   48.73    51.85        8.00            SURVIVOR
C-shock-continuation  1h   K>=4 continuation stop1.0xATR tgt2xstop hold24h   0.81     1.62          24   569   -4.46    36.03   199   26.74    46.73        2.00                FAIL
C-shock-continuation  1h    K>=4 continuation stop1.0xATR tgt2xstop hold8h   0.81     1.62           8   872   -4.94    36.58   287   17.22    45.64        2.00                FAIL
C-shock-continuation  1h   K>=4 continuation stop1.0xATR tgt3xstop hold24h   0.81     2.43          24   569   -0.74    31.11   199   36.49    40.20        3.00                FAIL
C-shock-continuation  1h    K>=4 continuation stop1.0xATR tgt3xstop hold8h   0.81     2.43           8   872   -4.09    33.83   287   23.67    43.21        3.00                FAIL
C-shock-continuation  1h   K>=4 continuation stop1.5xATR tgt2xstop hold24h   1.21     2.43          24   569   -1.48    38.14   199   40.64    47.74        5.00                FAIL
C-shock-continuation  1h    K>=4 continuation stop1.5xATR tgt2xstop hold8h   1.21     2.43           8   872   -3.83    38.76   287   27.38    48.08        5.00                FAIL
C-shock-continuation  1h   K>=4 continuation stop1.5xATR tgt3xstop hold24h   1.21     3.64          24   569    5.74    34.80   199   59.23    44.72        9.00            SURVIVOR
C-shock-continuation  1h    K>=4 continuation stop1.5xATR tgt3xstop hold8h   1.21     3.64           8   872   -0.74    37.84   287   29.85    45.64        8.00                FAIL
C-shock-continuation  1h   K>=6 continuation stop1.0xATR tgt2xstop hold24h   0.81     1.62          24   351    5.95    40.74   126   27.91    47.62        2.00            SURVIVOR
C-shock-continuation  1h    K>=6 continuation stop1.0xATR tgt2xstop hold8h   0.81     1.62           8   483    1.42    40.58   159   20.65    46.54        2.00            SURVIVOR
C-shock-continuation  1h   K>=6 continuation stop1.0xATR tgt3xstop hold24h   0.81     2.43          24   351   16.48    35.90   126   30.50    38.89        3.00            SURVIVOR
C-shock-continuation  1h    K>=6 continuation stop1.0xATR tgt3xstop hold8h   0.81     2.43           8   483    8.08    38.72   159   23.21    43.40        3.00            SURVIVOR
C-shock-continuation  1h   K>=6 continuation stop1.5xATR tgt2xstop hold24h   1.21     2.43          24   351   16.33    42.74   126   44.85    49.21        5.00            SURVIVOR
C-shock-continuation  1h    K>=6 continuation stop1.5xATR tgt2xstop hold8h   1.21     2.43           8   483   10.05    44.10   159   37.08    52.20        5.00            SURVIVOR
C-shock-continuation  1h   K>=6 continuation stop1.5xATR tgt3xstop hold24h   1.21     3.64          24   351   25.52    39.32   126   56.34    45.24        8.00            SURVIVOR
C-shock-continuation  1h    K>=6 continuation stop1.5xATR tgt3xstop hold8h   1.21     3.64           8   483   16.45    42.86   159   33.58    49.69        8.00            SURVIVOR
```

---

## 5. A vs B vs C — plain English

**C (continuation, the control/falsification arm) beats A and B, decisively.**

- **Family B (stopping volume at extremes) is a clean, total bust: 0
  survivors out of 96 configs, on either timeframe.** Every single
  config's TRAIN expectancy is negative (best is -5.62/trade — never
  crosses zero). Adding the local-extreme + wick-rejection refinement to
  the volume shock did not just fail to help, it actively killed the
  signal. This is the cleanest possible falsification result in the
  whole round: the "textbook stopping volume" pattern (shock volume at a
  fresh high/low with a rejecting wick) does not predict a BTC reversal
  in this data, at any K, wick threshold, or geometry.
- **Family A (absorption fade, the owner's literal read) survives, but
  narrowly and fragile.** 12 of 48 1h configs survive (0 of 48 on 15m).
  The survivors cluster almost entirely at **K=6** (m=1.0 or 1.5, mostly
  the 8h max-hold variants) — K=4 is essentially flat/negative noise
  (mean train expectancy across its 16 configs: -1.82/trade) and K=10
  collapses into wild, sample-starved swings (mean: -5.33/trade, and its
  two best rows are the INSUFFICIENT-SAMPLE pair at n=20/5). A signal
  that only works at one K value, with its neighbors on both sides
  failing, is the same "grid fragility" flag this repo flagged and
  buried in round 41 (bleed-rider structural) — worth real caution.
- **Family C (continuation, the arm built specifically to falsify the
  owner's read) is the strongest and most internally consistent family
  in the round.** On 1h, **all 8 of the K=6 geometry configs survive**
  (every single stop/target/hold combination positive on both train AND
  val — no fragility flag at all), train expectancy $1.42-$25.52/trade,
  val $20.65-$56.34/trade, on samples of 351-483 train / 126-159 val
  trades. K=4 and K=10 on 1h are much weaker (K=4: 1/8 survive; K=10:
  2/8 survive, both thin), so the pattern is still K-specific, but the
  K=6 island is far more *complete* than family A's — every geometry
  variant agrees, not just a handful.

**Verdict: the data says the owner's eye is picking up something real in
the tape (BTC volume shocks at 5-15x normal ARE informative, not
random), but the informed reaction most of the time is CONTINUATION, not
absorption/reversal.** The exception is the narrow long-side dip-buy
read from the event study (section 3) — that direction shows a small,
real tilt that the geometry grid's family-A K=6 survivors partly
capture. The short/fade-the-rip half of his intuition is not supported;
volume-confirmed rallies in this data statistically tend to keep running,
not reverse.

Mean TRAIN expectancy across each family's full shared grid (the honest
apples-to-apples number, selection-blind):

| family | tf | mean TRAIN exp/trade |
|---|---|---|
| A-absorption-fade | 15m | -$8.74 |
| A-absorption-fade | 1h | -$0.52 |
| B-stopping-volume | 15m | -$8.72 |
| B-stopping-volume | 1h | -$16.40 |
| C-shock-continuation | 15m | -$1.80 |
| C-shock-continuation | 1h | **+$1.80** |

C is the only family with a positive grid-wide mean on either timeframe.

---

## 6. Cost-floor analysis for 15m

Empirical realized cost per trade (fees + friction + funding, pooled
train+val, execution=maker, real funding via `align_funding`) expressed
in bps of the account's starting notional — same convention this repo
used for the round-43 "~9.2bps 15m cost floor" finding. `gross_edge_bps`
adds the realized cost back onto net expectancy, i.e. what the edge
would have looked like before costs.

**Family A / B on 15m fail BEFORE costs, not because of them.** Gross
edge is negative in nearly every 15m row for both families (e.g. family
A 15m K=4 m=1.0: gross edge ranges -2.33 to +3.44bps against realized
costs of 5.85-8.45bps — several cells are gross-negative outright, the
rest are gross-positive but smaller than the cost floor). This is a
DIFFERENT failure mode than round 43's dense day-trade families, which
had a real gross edge that costs simply outran. Here there frequently
is no real gross edge to begin with on 15m — the absorption/stopping-
volume read just doesn't show up at 15-minute resolution.

**Family C on 15m is the one place absorption-family entries clear the
cost floor, exactly as the mandate predicted for a sparse signal:**

| config | tf | realized cost (bps) | gross edge (bps) | net edge (bps) | tr_n+va_n |
|---|---|---|---|---|---|
| K>=6 continuation stop1.5xATR tgt3xstop hold24h | 15m | 9.25 | 11.41 | 2.12 (net) | 1,170 |
| K>=10 continuation stop1.5xATR tgt2xstop hold24h | 15m | 8.88 | 12.30 | 2.94 (net) | 759 |
| K>=10 continuation stop1.5xATR tgt3xstop hold24h | 15m | 10.15 | 16.61 | 4.64 (net) | 759 |

These three configs are sparse enough (event-gated, not every-bar) that
the realized cost (8.9-10.2bps) sits comfortably under the gross edge
(11.4-16.6bps), leaving 2-6bps net — thin, but real, and the pattern
matches the mandate's hypothesis exactly: **sparsity is what let a 15m
config clear the floor that killed every dense 15m family in round 43.**
That said, these three are single-K, single-target-side survivors
within a much larger 15m grid where the other 21 C configs and all 96
A/B configs failed — treat as a genuine but fragile pocket, not a broad
15m win.

---

## 7. Top sealed-look candidates, with reasoning

Ranked by robustness (internal grid consistency > raw train expectancy —
the round-41/43 lesson that a config whose neighbors all fail is noise
wearing a costume):

1. **★ C-shock-continuation, 1h, K>=6, stop1.5xATR / tgt3xstop /
   hold24h** — train $25.52/trade x351, val $56.34/trade x126, 8.0h
   median hold. Best single config in the round AND sits inside the
   fully-consistent 8/8 K=6 island (every stop/target/hold combination
   at K=6 on 1h survives). This is the strongest robustness signature in
   the whole grid — no fragility flag at all. **Primary recommendation
   for a sealed test.** Caveat: val ($56.34) more than 2x train ($25.52)
   — the same "val >> train" shape that flagged window luck in round 43
   before a sealed look proved it real; only the sealed test resolves
   this honestly.
2. **C-shock-continuation, 1h, K>=6, stop1.0xATR / tgt3xstop / hold24h**
   — train $16.48/trade x351, val $30.50/trade x126, 3.0h median hold.
   Same K=6/1h island, tighter stop (0.81% vs 1.21%) — a good second
   angle on the same underlying signal if the wider-stop variant's
   sealed result is ambiguous, since it shares the entry condition but
   not the exit geometry (a genuinely different risk profile, not a
   re-look of the same bet).
3. **A-absorption-fade, 1h, K>=6 m<=1.0, stop1.0xATR / tgt2xstop /
   hold8h** — train $26.62/trade x69, val $67.03/trade x23. The
   strongest single family-A number in the round, and the one that would
   validate the owner's LITERAL read (fade, not continue) if it survives
   sealed. Real caution: K=4 (0/16 meaningfully positive) and K=10 (2/16,
   both thin) do not corroborate — this is an island, not a trend. Worth
   a look specifically BECAUSE it is the direct test of his stated
   hypothesis, but go in expecting a real chance it does not hold
   (smaller n=69/23 than the C candidates, and no neighboring-K support).
4. **C-shock-continuation, 15m, K>=10, stop1.5xATR / tgt3xstop /
   hold24h** — train $4.64/trade x588, val $12.68/trade x171. The
   strongest 15m survivor in the round and the cleanest evidence that
   sparse absorption-family signals CAN clear the 15m cost floor. Small
   edge ($4.64/trade net of ~9-10bps realized cost) — likely too thin to
   size meaningfully even if it survives, but valuable as the 15m
   proof-of-concept the mandate asked to check for.

**Not recommended for a look:** all of Family B (0/96, no ambiguity —
buried outright), Family A on 15m (0/48, uniformly negative including
gross edge), and every K=10 config in either A or C (21-171 total events
across 5.75 years of train+val is too thin to trust regardless of the
backtest number — several of these already show train/val sign flips or
were tagged INSUFFICIENT-SAMPLE).

---

## Methodology notes / approximations (for the record)

- Stop = TRAIN-only median ATR% x multiplier, held fixed for the whole
  run, capped at 1.7% — this repo's established stop approximation
  (step41/step43), not a per-trade dynamic distance. Target = a fixed
  multiplier of THAT stop (not of ATR directly), per the round-50 brief.
- Volume/return baselines are `rolling(48).shift(1)` — strictly prior
  bars only, so a shock bar's own extreme values never inflate the
  baseline it is being judged against.
- `realized_cost_bps` / `gross_edge_bps` divide pooled train+val dollar
  costs/edge by a FIXED notional (config.INITIAL_EQUITY = $10,000), not
  compounding equity — a scale approximation, consistent with how this
  repo has quoted "~Xbps cost floor" numbers since round 43. Directionally
  reliable, not cent-accurate.
- Engine plumbing (`split_points`, `day_trade_signal`, `score`,
  `verdict_for`, `mk_row`, `hours_to_bars`, `HARD_STOP_CAP`) is imported
  unmodified from `step43_daytrade.py`, per the round-50 brief — no
  duplicate logic, no drift risk from a second copy.
- Costs always on (CostModel defaults), execution="maker", real funding
  via `align_funding`. Gauntlet: chronological 60/20/20 per timeframe;
  this script computes ONLY train [0:i_tr] and val [i_tr:i_va]. The
  sealed final 20% test window was NEVER read, sliced, or scored by this
  script — that look belongs to the lead agent.
