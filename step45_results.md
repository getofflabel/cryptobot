# Round 45A, grind-native day-trades (step45_grind_daytrades.py)

Wallace's mandate: stop building day-trade families that fight the 2025-26
low-vol grind (rounds 41 + 43 both confirmed momentum/breakout/short shapes
die in it) and instead build families STRUCTURED to profit from it, ranges,
mean-reversion, the 8h funding cycle, failed breakouts. Every family is
tested at day-trade geometry: hold <=24h, stop <=1.7% (the 20x-leverage
ceiling), full costs, real funding, `execution="maker"`.

Script: `step45_grind_daytrades.py`. **168 configs**, chronological 60/20/20
split (train through 2024-01-10, val through 2025-04-16 on the 1h frame;
train through 2024-01-10, val through 2025-04-16 on the 2h frame too (same
calendar dates, different bar counts). **Test sealed and never touched by
this script.** All numbers are AFTER FULL COSTS (CostModel defaults: 6bps
taker / 2bps maker, 1bp half-spread, 2bp slippage, real signed funding via
`align_funding`). Expectancy is $/trade on a $10k account, `execution=
"maker"` throughout.

Survivor bar (Gauntlet protocol, unchanged): positive expectancy on BOTH
train and val, **>=30 train trades AND >=8 val trades**, selected by TRAIN
expectancy only. "INSUFFICIENT-SAMPLE" = positive both windows but under the
trade-count floor, a real finding (usually a rare-event config), not a
fail of the edge itself.

**No 15m configs this round.** 15m is 4x-confirmed dead (round 4-8 lineage
+ round 43's direct cost-floor measurement: ~9.2bps realized cost vs ~3bps
gross edge at that resolution): the edge doesn't exist at a size that
clears even a maker-heavy cost structure. Nothing in this round's family
shapes gives any reason that pattern would suddenly break, so no cost-floor
analysis was needed here; 15m simply wasn't run.

**Reused, not reimplemented**: `split_points`, `day_trade_signal`, `score`,
`verdict_for`, `hold_stats`, `mk_row`, `hours_to_bars`, `bar_hours`,
`MIN_TRAIN_TRADES`, `MIN_VAL_TRADES`, `HARD_STOP_CAP` all imported directly
from `step43_daytrade.py`; `adaptive_vol_gate` imported directly from
`step41_shorts.py` (used with `direction="below"` throughout, the QUIET
gate, current ATR% below its own trailing-365d median, the one gate that
ever helped anything in round 41). Only one new signal state machine was
needed: `range_fade_signal` (family 1), a bidirectional generalization of
`day_trade_signal` that adds a "z crosses back through 0" exit on top of
the existing max-hold-forces-flat logic, because the range-fade spec calls
for a mean-touch exit a plain time-stop can't express.

**Approximation note (same convention as step41/step43)**: wherever a
family calls for a per-trade dynamic exit distance (distance-to-mean,
distance-to-wick, distance-to-midpoint) instead of run_backtest's one fixed
stop_pct/target_pct, we use a TRAIN-only median of that distance at
qualifying entries, held fixed across train and val, capped per the
family's own spec, and additionally hard-capped at 1.7% (`HARD_STOP_CAP`)
for every stop. Stated per family below.

**Calm-gate discipline**: families 1, 2, 3 and 4 were ALL run BOTH
calm-gated (`adaptive_vol_gate(..., direction="below")`, i.e. current ATR%
below its own trailing-365d median) and ungated, on IDENTICAL entry/exit
geometry, so the results table itself carries the "does the calm gate
genuinely help" comparison for every family, not just family 1; see the
per-family autopsy below for what that comparison actually shows (the
answer is not the same in every family, and in one case the gate makes
things measurably WORSE).

**OI data span found**: `data_bybit_BTCUSDT_oi_1h.parquet`, hourly Bybit
open interest, **2020-07-20 to 2026-07-23** (52,290 rows), effectively
continuous (one 15-day gap, otherwise exactly hourly). Aligned onto the 1h
price frame with `merge_asof`/2h tolerance: 52,288 of 55,451 bars have OI
(the 3,163 NaN are almost entirely the March-July 2020 warmup, before OI
history starts, which only nibbles the very front of a 6-year train
window, not a floor problem). **Verdict: fully usable for the gauntlet,
not too short.** Family 3 ran the full grid.

**Funding data used**: `data_bybit_BTCUSDT_funding.parquet`, **6,931 real
settlements**, 2020-03-25 to 2026-07-22, confirmed all landing exactly on
the 00:00 / 08:00 / 16:00 UTC marks (2,310-2,311 each). Family 2's entries
use only the MOST RECENTLY SETTLED rate via `align_funding`'s backward
as-of merge (already-known information as of the entry bar's close), never
an unknowable future settlement's realized rate (see the file header for
the full no-lookahead reasoning on this point).

## Full results (168 configs, train + val, full costs, test sealed)

| family | config | tf | gate | stop% | target% | max_hold_h | tr_n | tr_exp | tr_win% | tr_ret% | tr_dd% | va_n | va_exp | va_win% | va_ret% | va_dd% | med_hold_h | mean_hold_h | verdict |
|:--|:--|:--|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--|
| 1-calm-range-fade | N24 z1.5 calm-gated stop1.5% | 1h | calm-gated | 1.50 | 1.21 | 24 | 930 | -5.73 | 60.65 | -53.27 | -54.93 | 240 | -14.09 | 57.08 | -33.81 | -38.35 | 5.00 | 6.96 | FAIL |
| 1-calm-range-fade | N24 z2.0 calm-gated stop1.5% | 1h | calm-gated | 1.50 | 1.41 | 24 | 668 | -5.98 | 59.43 | -39.96 | -41.97 | 158 | -16.92 | 55.06 | -26.73 | -31.50 | 6.00 | 7.59 | FAIL |
| 1-calm-range-fade | N24 z1.5 calm-gated stop1.0% | 1h | calm-gated | 1.00 | 1.21 | 24 | 930 | -6.13 | 53.01 | -57.04 | -57.04 | 240 | -13.72 | 50.00 | -32.93 | -34.45 | 4.00 | 5.49 | FAIL |
| 1-calm-range-fade | N24 z2.0 calm-gated stop1.0% | 1h | calm-gated | 1.00 | 1.41 | 24 | 668 | -6.85 | 51.05 | -45.76 | -47.78 | 158 | -18.62 | 44.94 | -29.42 | -31.28 | 4.00 | 5.92 | FAIL |
| 1-calm-range-fade | N48 z2.0 calm-gated stop1.5% | 1h | calm-gated | 1.50 | 1.91 | 24 | 426 | -7.05 | 50.23 | -30.01 | -32.14 | 107 | -8.36 | 53.27 | -8.95 | -30.49 | 8.00 | 9.79 | FAIL |
| 1-calm-range-fade | N48 z1.5 calm-gated stop1.0% | 1h | calm-gated | 1.00 | 1.74 | 24 | 648 | -7.64 | 44.91 | -49.51 | -53.57 | 150 | -17.64 | 41.33 | -26.46 | -33.20 | 5.00 | 7.38 | FAIL |
| 1-calm-range-fade | N48 z2.0 calm-gated stop1.0% | 1h | calm-gated | 1.00 | 1.91 | 24 | 426 | -8.14 | 41.31 | -34.66 | -37.21 | 107 | -16.40 | 41.12 | -17.54 | -32.77 | 5.00 | 7.64 | FAIL |
| 1-calm-range-fade | N48 z1.5 calm-gated stop1.5% | 1h | calm-gated | 1.50 | 1.74 | 24 | 648 | -8.48 | 52.16 | -54.94 | -64.06 | 150 | -10.57 | 54.00 | -15.86 | -27.66 | 7.00 | 9.42 | FAIL |
| 1-calm-range-fade | N24 z1.5 ungated stop1.0% | 1h | ungated | 1.00 | 1.85 | 24 | 1533 | -5.82 | 44.36 | -89.26 | -89.29 | 544 | -10.21 | 45.04 | -55.53 | -58.31 | 3.00 | 5.11 | FAIL |
| 1-calm-range-fade | N24 z1.5 ungated stop1.5% | 1h | ungated | 1.50 | 1.85 | 24 | 1533 | -5.93 | 52.45 | -90.91 | -90.93 | 544 | -9.88 | 54.04 | -53.77 | -58.05 | 5.00 | 6.80 | FAIL |
| 1-calm-range-fade | N48 z1.5 ungated stop1.0% | 1h | ungated | 1.00 | 2.50 | 24 | 1045 | -7.12 | 38.56 | -74.45 | -74.45 | 351 | -13.20 | 35.61 | -46.34 | -50.87 | 4.00 | 6.84 | FAIL |
| 1-calm-range-fade | N24 z2.0 ungated stop1.5% | 1h | ungated | 1.50 | 2.11 | 24 | 1156 | -7.46 | 50.95 | -86.21 | -86.49 | 396 | -11.52 | 51.52 | -45.62 | -50.30 | 6.00 | 7.46 | FAIL |
| 1-calm-range-fade | N24 z2.0 ungated stop1.0% | 1h | ungated | 1.00 | 2.11 | 24 | 1156 | -7.59 | 41.70 | -87.70 | -87.95 | 396 | -13.12 | 41.16 | -51.94 | -55.33 | 4.00 | 5.49 | FAIL |
| 1-calm-range-fade | N48 z1.5 ungated stop1.5% | 1h | ungated | 1.50 | 2.50 | 24 | 1045 | -8.37 | 45.07 | -87.47 | -87.47 | 351 | -9.88 | 47.01 | -34.67 | -44.47 | 7.00 | 8.89 | FAIL |
| 1-calm-range-fade | N48 z2.0 ungated stop1.0% | 1h | ungated | 1.00 | 2.50 | 24 | 738 | -10.32 | 33.88 | -76.15 | -76.58 | 263 | -10.66 | 38.02 | -28.03 | -42.36 | 4.00 | 6.86 | FAIL |
| 1-calm-range-fade | N48 z2.0 ungated stop1.5% | 1h | ungated | 1.50 | 2.50 | 24 | 738 | -11.24 | 41.73 | -82.92 | -83.00 | 263 | -1.98 | 49.05 | -5.21 | -41.66 | 7.00 | 9.09 | FAIL |
| 1-calm-range-fade | N24 z1.5 calm-gated stop1.5% | 2h | calm-gated | 1.50 | 1.86 | 24 | 548 | -4.93 | 50.91 | -27.01 | -49.41 | 134 | -12.24 | 52.99 | -16.40 | -31.50 | 8.00 | 10.42 | FAIL |
| 1-calm-range-fade | N24 z2.0 calm-gated stop1.5% | 2h | calm-gated | 1.50 | 2.08 | 24 | 377 | -6.78 | 48.54 | -25.55 | -38.03 | 89 | -22.75 | 46.07 | -20.25 | -28.79 | 10.00 | 10.88 | FAIL |
| 1-calm-range-fade | N48 z1.5 calm-gated stop1.5% | 2h | calm-gated | 1.50 | 2.50 | 24 | 409 | -7.09 | 45.23 | -28.98 | -44.74 | 94 | -31.51 | 36.17 | -29.62 | -33.06 | 10.00 | 11.96 | FAIL |
| 1-calm-range-fade | N48 z2.0 calm-gated stop1.5% | 2h | calm-gated | 1.50 | 2.50 | 24 | 237 | -7.35 | 44.30 | -17.43 | -37.15 | 55 | -41.41 | 32.73 | -22.78 | -22.99 | 10.00 | 12.18 | FAIL |
| 1-calm-range-fade | N24 z1.5 calm-gated stop1.0% | 2h | calm-gated | 1.00 | 1.86 | 24 | 548 | -9.55 | 40.88 | -52.36 | -57.32 | 134 | -18.14 | 41.79 | -24.31 | -34.36 | 6.00 | 8.03 | FAIL |
| 1-calm-range-fade | N48 z1.5 calm-gated stop1.0% | 2h | calm-gated | 1.00 | 2.50 | 24 | 409 | -12.64 | 33.99 | -51.70 | -56.29 | 94 | -28.54 | 26.60 | -26.83 | -30.41 | 6.00 | 9.02 | FAIL |
| 1-calm-range-fade | N24 z2.0 calm-gated stop1.0% | 2h | calm-gated | 1.00 | 2.08 | 24 | 377 | -14.18 | 36.87 | -53.44 | -56.62 | 89 | -30.26 | 31.46 | -26.93 | -31.72 | 6.00 | 7.85 | FAIL |
| 1-calm-range-fade | N48 z2.0 calm-gated stop1.0% | 2h | calm-gated | 1.00 | 2.50 | 24 | 237 | -16.08 | 32.07 | -38.11 | -44.80 | 55 | -36.22 | 23.64 | -19.92 | -21.24 | 6.00 | 9.08 | FAIL |
| 1-calm-range-fade | N48 z1.5 ungated stop1.5% | 2h | ungated | 1.50 | 2.50 | 24 | 708 | -8.73 | 42.51 | -61.80 | -67.95 | 243 | -11.66 | 41.15 | -28.32 | -34.62 | 8.00 | 10.26 | FAIL |
| 1-calm-range-fade | N24 z1.5 ungated stop1.5% | 2h | ungated | 1.50 | 2.50 | 24 | 907 | -8.76 | 43.22 | -79.48 | -82.82 | 322 | -3.54 | 48.45 | -11.39 | -37.00 | 8.00 | 9.51 | FAIL |
| 1-calm-range-fade | N24 z1.5 ungated stop1.0% | 2h | ungated | 1.00 | 2.50 | 24 | 907 | -8.81 | 34.73 | -79.91 | -80.97 | 322 | -8.51 | 37.89 | -27.39 | -40.06 | 4.00 | 7.16 | FAIL |
| 1-calm-range-fade | N48 z1.5 ungated stop1.0% | 2h | ungated | 1.00 | 2.50 | 24 | 708 | -9.68 | 32.77 | -68.53 | -70.86 | 243 | -18.18 | 28.81 | -44.18 | -47.21 | 4.00 | 7.47 | FAIL |
| 1-calm-range-fade | N24 z2.0 ungated stop1.5% | 2h | ungated | 1.50 | 2.50 | 24 | 651 | -9.96 | 42.70 | -64.84 | -70.80 | 217 | -10.81 | 45.16 | -23.45 | -29.41 | 7.00 | 9.47 | FAIL |
| 1-calm-range-fade | N24 z2.0 ungated stop1.0% | 2h | ungated | 1.00 | 2.50 | 24 | 651 | -10.77 | 33.33 | -70.10 | -70.55 | 217 | -14.82 | 33.64 | -32.15 | -34.45 | 4.00 | 6.75 | FAIL |
| 1-calm-range-fade | N48 z2.0 ungated stop1.5% | 2h | ungated | 1.50 | 2.50 | 24 | 430 | -15.10 | 39.07 | -64.93 | -69.70 | 154 | -22.70 | 35.71 | -34.96 | -35.29 | 8.00 | 10.12 | FAIL |
| 1-calm-range-fade | N48 z2.0 ungated stop1.0% | 2h | ungated | 1.00 | 2.50 | 24 | 430 | -16.33 | 28.84 | -70.23 | -72.05 | 154 | -26.92 | 24.68 | -41.46 | -42.05 | 4.00 | 7.34 | FAIL |
| 2-funding-post | B f>2.5bp calm-gated tgt2.0% | 1h | calm-gated | 1.00 | 2.00 | 6 | 224 | -2.91 | 48.66 | -6.53 | -20.24 | 31 | 3.23 | 48.39 | 1.00 | -3.75 | 6.00 | 4.29 | FAIL |
| 2-funding-post | B f>1.5bp calm-gated tgtnone | 1h | calm-gated | 1.00 |  | 6 | 318 | -4.04 | 44.97 | -12.85 | -26.58 | 44 | 10.04 | 47.73 | 4.42 | -4.37 | 6.00 | 4.64 | FAIL |
| 2-funding-post | B f>2.5bp calm-gated tgtnone | 1h | calm-gated | 1.00 |  | 6 | 224 | -4.09 | 47.77 | -9.16 | -21.06 | 31 | 6.78 | 48.39 | 2.10 | -3.77 | 6.00 | 4.61 | FAIL |
| 2-funding-post | B f>1.5bp calm-gated tgt2.0% | 1h | calm-gated | 1.00 | 2.00 | 6 | 318 | -6.39 | 45.91 | -20.31 | -25.81 | 44 | 5.68 | 47.73 | 2.50 | -4.35 | 6.00 | 4.33 | FAIL |
| 2-funding-post | B f>2.5bp calm-gated tgt1.0% | 1h | calm-gated | 1.00 | 1.00 | 6 | 224 | -6.59 | 51.34 | -14.77 | -21.43 | 31 | 0.05 | 48.39 | 0.02 | -3.75 | 4.00 | 3.50 | FAIL |
| 2-funding-post | B f>1.5bp calm-gated tgt1.0% | 1h | calm-gated | 1.00 | 1.00 | 6 | 318 | -9.09 | 48.43 | -28.91 | -29.34 | 44 | 0.79 | 47.73 | 0.35 | -4.35 | 4.00 | 3.59 | FAIL |
| 2-funding-post | B f>1.5bp ungated tgtnone | 1h | ungated | 1.00 |  | 6 | 842 | -6.77 | 39.55 | -57.03 | -63.76 | 152 | -1.51 | 41.45 | -2.29 | -16.90 | 6.00 | 3.95 | FAIL |
| 2-funding-post | B f>2.5bp ungated tgtnone | 1h | ungated | 1.00 |  | 6 | 638 | -6.94 | 40.60 | -44.26 | -51.28 | 106 | -4.62 | 40.57 | -4.89 | -15.62 | 6.00 | 3.90 | FAIL |
| 2-funding-post | B f>2.5bp ungated tgt2.0% | 1h | ungated | 1.00 | 2.00 | 6 | 638 | -7.31 | 42.32 | -46.67 | -51.44 | 106 | -2.34 | 43.40 | -2.48 | -14.19 | 3.00 | 3.36 | FAIL |
| 2-funding-post | B f>2.5bp ungated tgt1.0% | 1h | ungated | 1.00 | 1.00 | 6 | 638 | -7.56 | 49.06 | -48.26 | -49.66 | 106 | -9.47 | 46.23 | -10.04 | -15.08 | 2.00 | 2.40 | FAIL |
| 2-funding-post | B f>1.5bp ungated tgt2.0% | 1h | ungated | 1.00 | 2.00 | 6 | 842 | -7.60 | 41.21 | -63.98 | -66.34 | 152 | -0.56 | 43.42 | -0.85 | -15.23 | 4.00 | 3.44 | FAIL |
| 2-funding-post | B f>1.5bp ungated tgt1.0% | 1h | ungated | 1.00 | 1.00 | 6 | 842 | -7.81 | 47.51 | -65.76 | -67.08 | 152 | -7.31 | 46.71 | -11.11 | -15.20 | 2.00 | 2.54 | FAIL |
| 2-funding-pre | A f>1.5bp before4 exit+1 calm-gated tgtnone | 1h | calm-gated | 1.00 |  | 5 | 319 | 5.44 | 46.08 | 17.34 | -11.92 | 48 | -12.40 | 39.58 | -5.95 | -7.76 | 5.00 | 4.08 | FAIL |
| 2-funding-pre | A f>1.5bp before4 exit+2 calm-gated tgtnone | 1h | calm-gated | 1.00 |  | 6 | 319 | 4.58 | 41.69 | 14.60 | -13.03 | 48 | -13.79 | 39.58 | -6.62 | -8.02 | 6.00 | 4.75 | FAIL |
| 2-funding-pre | A f>1.5bp before2 exit+2 calm-gated tgtnone | 1h | calm-gated | 1.00 |  | 4 | 322 | 3.06 | 46.89 | 9.85 | -17.68 | 41 | -3.63 | 51.22 | -1.49 | -5.16 | 4.00 | 3.41 | FAIL |
| 2-funding-pre | A f>2.5bp before2 exit+2 calm-gated tgtnone | 1h | calm-gated | 1.00 |  | 4 | 226 | 1.38 | 46.46 | 3.11 | -17.09 | 28 | -9.32 | 46.43 | -2.61 | -3.98 | 4.00 | 3.42 | FAIL |
| 2-funding-pre | A f>1.5bp before2 exit+2 calm-gated tgt2.0% | 1h | calm-gated | 1.00 | 2.00 | 4 | 322 | 0.72 | 47.52 | 2.32 | -14.00 | 41 | -3.63 | 51.22 | -1.49 | -5.16 | 4.00 | 3.26 | FAIL |
| 2-funding-pre | A f>1.5bp before2 exit+1 calm-gated tgtnone | 1h | calm-gated | 1.00 |  | 3 | 322 | 0.12 | 46.58 | 0.37 | -17.65 | 41 | -2.82 | 41.46 | -1.16 | -4.85 | 3.00 | 2.63 | FAIL |
| 2-funding-pre | A f>1.5bp before4 exit+1 calm-gated tgt2.0% | 1h | calm-gated | 1.00 | 2.00 | 5 | 319 | -0.25 | 46.08 | -0.78 | -15.26 | 48 | -12.93 | 39.58 | -6.21 | -8.01 | 5.00 | 3.77 | FAIL |
| 2-funding-pre | A f>1.5bp before2 exit+2 calm-gated tgt1.0% | 1h | calm-gated | 1.00 | 1.00 | 4 | 322 | -0.35 | 49.69 | -1.14 | -13.78 | 41 | 5.19 | 53.66 | 2.13 | -5.16 | 4.00 | 2.76 | FAIL |
| 2-funding-pre | A f>2.5bp before2 exit+2 calm-gated tgt2.0% | 1h | calm-gated | 1.00 | 2.00 | 4 | 226 | -0.80 | 46.90 | -1.82 | -13.15 | 28 | -9.32 | 46.43 | -2.61 | -3.98 | 4.00 | 3.28 | FAIL |
| 2-funding-pre | A f>1.5bp before2 exit+1 calm-gated tgt1.0% | 1h | calm-gated | 1.00 | 1.00 | 3 | 322 | -1.49 | 50.00 | -4.78 | -11.54 | 41 | 0.71 | 41.46 | 0.29 | -4.85 | 3.00 | 2.24 | FAIL |
| 2-funding-pre | A f>1.5bp before4 exit+2 calm-gated tgt2.0% | 1h | calm-gated | 1.00 | 2.00 | 6 | 319 | -1.71 | 42.32 | -5.46 | -18.23 | 48 | -14.10 | 39.58 | -6.77 | -8.16 | 6.00 | 4.32 | FAIL |
| 2-funding-pre | A f>2.5bp before2 exit+2 calm-gated tgt1.0% | 1h | calm-gated | 1.00 | 1.00 | 4 | 226 | -1.71 | 48.67 | -3.87 | -11.96 | 28 | 2.54 | 50.00 | 0.71 | -3.95 | 4.00 | 2.78 | FAIL |
| 2-funding-pre | A f>2.5bp before4 exit+1 calm-gated tgtnone | 1h | calm-gated | 1.00 |  | 5 | 223 | -2.08 | 44.39 | -4.64 | -20.33 | 34 | -12.90 | 41.18 | -4.39 | -5.29 | 5.00 | 4.01 | FAIL |
| 2-funding-pre | A f>1.5bp before2 exit+1 calm-gated tgt2.0% | 1h | calm-gated | 1.00 | 2.00 | 3 | 322 | -2.15 | 47.20 | -6.91 | -16.23 | 41 | -2.82 | 41.46 | -1.16 | -4.85 | 3.00 | 2.55 | FAIL |
| 2-funding-pre | A f>2.5bp before2 exit+1 calm-gated tgtnone | 1h | calm-gated | 1.00 |  | 3 | 226 | -2.67 | 43.36 | -6.03 | -19.06 | 28 | -4.49 | 39.29 | -1.26 | -4.21 | 3.00 | 2.64 | FAIL |
| 2-funding-pre | A f>1.5bp before4 exit+1 calm-gated tgt1.0% | 1h | calm-gated | 1.00 | 1.00 | 5 | 319 | -2.92 | 49.22 | -9.31 | -16.79 | 48 | -3.30 | 45.83 | -1.58 | -5.19 | 3.00 | 3.14 | FAIL |
| 2-funding-pre | A f>2.5bp before4 exit+2 calm-gated tgtnone | 1h | calm-gated | 1.00 |  | 6 | 223 | -3.22 | 40.36 | -7.18 | -23.65 | 34 | -18.96 | 35.29 | -6.45 | -7.53 | 6.00 | 4.65 | FAIL |
| 2-funding-pre | A f>2.5bp before2 exit+1 calm-gated tgt1.0% | 1h | calm-gated | 1.00 | 1.00 | 3 | 226 | -3.57 | 46.90 | -8.06 | -13.70 | 28 | -1.80 | 39.29 | -0.50 | -4.21 | 3.00 | 2.26 | FAIL |
| 2-funding-pre | A f>1.5bp before4 exit+2 calm-gated tgt1.0% | 1h | calm-gated | 1.00 | 1.00 | 6 | 319 | -3.96 | 46.08 | -12.64 | -18.55 | 48 | -3.05 | 47.92 | -1.46 | -5.31 | 3.00 | 3.50 | FAIL |
| 2-funding-pre | A f>2.5bp before2 exit+1 calm-gated tgt2.0% | 1h | calm-gated | 1.00 | 2.00 | 3 | 226 | -4.73 | 43.81 | -10.70 | -16.47 | 28 | -4.49 | 39.29 | -1.26 | -4.21 | 3.00 | 2.57 | FAIL |
| 2-funding-pre | A f>2.5bp before4 exit+1 calm-gated tgt1.0% | 1h | calm-gated | 1.00 | 1.00 | 5 | 223 | -7.47 | 47.98 | -16.66 | -22.30 | 34 | 0.26 | 50.00 | 0.09 | -3.83 | 3.00 | 3.11 | FAIL |
| 2-funding-pre | A f>2.5bp before4 exit+1 calm-gated tgt2.0% | 1h | calm-gated | 1.00 | 2.00 | 5 | 223 | -7.69 | 44.39 | -17.16 | -24.41 | 34 | -13.67 | 41.18 | -4.65 | -5.55 | 5.00 | 3.76 | FAIL |
| 2-funding-pre | A f>2.5bp before4 exit+2 calm-gated tgt1.0% | 1h | calm-gated | 1.00 | 1.00 | 6 | 223 | -8.39 | 43.95 | -18.71 | -23.92 | 34 | -2.18 | 47.06 | -0.74 | -4.61 | 3.00 | 3.46 | FAIL |
| 2-funding-pre | A f>2.5bp before4 exit+2 calm-gated tgt2.0% | 1h | calm-gated | 1.00 | 2.00 | 6 | 223 | -9.05 | 40.81 | -20.17 | -27.42 | 34 | -19.39 | 35.29 | -6.59 | -7.68 | 6.00 | 4.30 | FAIL |
| 2-funding-pre | A f>1.5bp before2 exit+1 ungated tgtnone | 1h | ungated | 1.00 |  | 3 | 842 | -0.40 | 42.28 | -3.36 | -34.61 | 152 | -9.88 | 43.42 | -15.02 | -16.85 | 3.00 | 2.25 | FAIL |
| 2-funding-pre | A f>1.5bp before2 exit+2 ungated tgtnone | 1h | ungated | 1.00 |  | 4 | 842 | -0.88 | 42.76 | -7.39 | -38.47 | 152 | -5.75 | 43.42 | -8.75 | -12.35 | 4.00 | 2.88 | FAIL |
| 2-funding-pre | A f>1.5bp before2 exit+2 ungated tgt2.0% | 1h | ungated | 1.00 | 2.00 | 4 | 842 | -1.82 | 44.66 | -15.31 | -33.31 | 152 | -8.15 | 43.42 | -12.38 | -14.27 | 3.00 | 2.49 | FAIL |
| 2-funding-pre | A f>1.5bp before4 exit+1 ungated tgtnone | 1h | ungated | 1.00 |  | 5 | 842 | -1.83 | 39.90 | -15.45 | -58.37 | 152 | -7.97 | 44.08 | -12.12 | -16.82 | 5.00 | 3.47 | FAIL |
| 2-funding-pre | A f>1.5bp before2 exit+1 ungated tgt2.0% | 1h | ungated | 1.00 | 2.00 | 3 | 842 | -2.10 | 43.59 | -17.71 | -37.84 | 152 | -8.37 | 43.42 | -12.73 | -14.71 | 3.00 | 2.00 | FAIL |
| 2-funding-pre | A f>1.5bp before4 exit+1 ungated tgt2.0% | 1h | ungated | 1.00 | 2.00 | 5 | 842 | -2.64 | 41.69 | -22.23 | -45.28 | 152 | -2.40 | 44.08 | -3.65 | -14.47 | 3.00 | 2.91 | FAIL |
| 2-funding-pre | A f>1.5bp before2 exit+1 ungated tgt1.0% | 1h | ungated | 1.00 | 1.00 | 3 | 842 | -2.75 | 50.00 | -23.17 | -35.40 | 152 | -5.72 | 45.39 | -8.70 | -14.06 | 1.00 | 1.55 | FAIL |
| 2-funding-pre | A f>1.5bp before2 exit+2 ungated tgt1.0% | 1h | ungated | 1.00 | 1.00 | 4 | 842 | -2.90 | 50.83 | -24.40 | -37.86 | 152 | -4.09 | 49.34 | -6.21 | -14.05 | 1.00 | 1.87 | FAIL |
| 2-funding-pre | A f>1.5bp before4 exit+2 ungated tgt2.0% | 1h | ungated | 1.00 | 2.00 | 6 | 842 | -3.16 | 40.14 | -26.58 | -47.05 | 152 | -5.39 | 42.76 | -8.20 | -16.95 | 3.00 | 3.27 | FAIL |
| 2-funding-pre | A f>1.5bp before4 exit+2 ungated tgtnone | 1h | ungated | 1.00 |  | 6 | 842 | -3.50 | 37.05 | -29.47 | -58.85 | 152 | -6.99 | 42.76 | -10.62 | -18.92 | 6.00 | 4.01 | FAIL |
| 2-funding-pre | A f>1.5bp before4 exit+1 ungated tgt1.0% | 1h | ungated | 1.00 | 1.00 | 5 | 842 | -4.31 | 49.41 | -36.26 | -48.98 | 152 | 1.74 | 51.97 | 2.65 | -15.46 | 2.00 | 2.18 | FAIL |
| 2-funding-pre | A f>1.5bp before4 exit+2 ungated tgt1.0% | 1h | ungated | 1.00 | 1.00 | 6 | 842 | -4.53 | 48.46 | -38.12 | -49.66 | 152 | 3.16 | 53.29 | 4.80 | -15.33 | 2.00 | 2.39 | FAIL |
| 2-funding-pre | A f>2.5bp before2 exit+1 ungated tgtnone | 1h | ungated | 1.00 |  | 3 | 638 | -4.66 | 39.50 | -29.71 | -39.86 | 106 | -10.74 | 39.62 | -11.39 | -13.54 | 3.00 | 2.22 | FAIL |
| 2-funding-pre | A f>2.5bp before2 exit+2 ungated tgtnone | 1h | ungated | 1.00 |  | 4 | 638 | -4.91 | 41.54 | -31.34 | -39.61 | 106 | -8.98 | 38.68 | -9.52 | -12.42 | 4.00 | 2.82 | FAIL |
| 2-funding-pre | A f>2.5bp before2 exit+2 ungated tgt2.0% | 1h | ungated | 1.00 | 2.00 | 4 | 638 | -4.95 | 43.26 | -31.61 | -35.03 | 106 | -12.51 | 38.68 | -13.26 | -14.24 | 3.00 | 2.44 | FAIL |
| 2-funding-pre | A f>2.5bp before2 exit+1 ungated tgt2.0% | 1h | ungated | 1.00 | 2.00 | 3 | 638 | -5.22 | 40.75 | -33.31 | -37.76 | 106 | -9.44 | 39.62 | -10.01 | -11.33 | 3.00 | 1.96 | FAIL |
| 2-funding-pre | A f>2.5bp before2 exit+1 ungated tgt1.0% | 1h | ungated | 1.00 | 1.00 | 3 | 638 | -5.32 | 47.34 | -33.94 | -36.62 | 106 | -7.28 | 42.45 | -7.72 | -12.07 | 1.00 | 1.53 | FAIL |
| 2-funding-pre | A f>2.5bp before2 exit+2 ungated tgt1.0% | 1h | ungated | 1.00 | 1.00 | 4 | 638 | -5.42 | 49.37 | -34.59 | -38.47 | 106 | -6.23 | 47.17 | -6.60 | -11.72 | 1.00 | 1.84 | FAIL |
| 2-funding-pre | A f>2.5bp before4 exit+1 ungated tgtnone | 1h | ungated | 1.00 |  | 5 | 638 | -5.56 | 38.24 | -35.45 | -54.33 | 106 | -14.32 | 41.51 | -15.18 | -17.46 | 5.00 | 3.40 | FAIL |
| 2-funding-pre | A f>2.5bp before4 exit+1 ungated tgt2.0% | 1h | ungated | 1.00 | 2.00 | 5 | 638 | -5.66 | 40.44 | -36.11 | -46.03 | 106 | -7.47 | 41.51 | -7.91 | -13.39 | 3.00 | 2.84 | FAIL |
| 2-funding-pre | A f>2.5bp before4 exit+1 ungated tgt1.0% | 1h | ungated | 1.00 | 1.00 | 5 | 638 | -6.02 | 48.90 | -38.40 | -46.36 | 106 | 2.81 | 52.83 | 2.97 | -15.15 | 2.00 | 2.11 | FAIL |
| 2-funding-pre | A f>2.5bp before4 exit+2 ungated tgt2.0% | 1h | ungated | 1.00 | 2.00 | 6 | 638 | -6.16 | 38.71 | -39.33 | -46.37 | 106 | -14.82 | 37.74 | -15.71 | -19.35 | 3.00 | 3.18 | FAIL |
| 2-funding-pre | A f>2.5bp before4 exit+2 ungated tgt1.0% | 1h | ungated | 1.00 | 1.00 | 6 | 638 | -6.16 | 47.65 | -39.33 | -45.76 | 106 | 2.36 | 52.83 | 2.51 | -15.20 | 2.00 | 2.30 | FAIL |
| 2-funding-pre | A f>2.5bp before4 exit+2 ungated tgtnone | 1h | ungated | 1.00 |  | 6 | 638 | -7.24 | 35.27 | -46.16 | -57.34 | 106 | -17.74 | 37.74 | -18.80 | -21.73 | 6.00 | 3.90 | FAIL |
| 3-oi-shock | dOI1h q95 follow calm-gated stop1.0% tgt3.0% | 1h | calm-gated | 1.00 | 3.00 | 24 | 208 | 21.49 | 40.87 | 44.70 | -13.91 | 4 | -110.97 | 0.00 | -4.44 | -4.44 | 10.00 | 11.37 | FAIL |
| 3-oi-shock | dOI4h q95 follow calm-gated stop1.0% tgt3.0% | 1h | calm-gated | 1.00 | 3.00 | 24 | 119 | 18.30 | 38.66 | 21.78 | -15.32 | 2 | 165.72 | 100.00 | 3.31 | -1.71 | 9.00 | 10.86 | INSUFFICIENT-SAMPLE |
| 3-oi-shock | dOI1h q90 follow calm-gated stop1.0% tgt3.0% | 1h | calm-gated | 1.00 | 3.00 | 24 | 358 | 17.04 | 40.78 | 61.00 | -22.53 | 20 | -12.87 | 35.00 | -2.57 | -11.39 | 8.50 | 11.18 | FAIL |
| 3-oi-shock | dOI1h q95 follow calm-gated stop1.5% tgt3.0% | 1h | calm-gated | 1.50 | 3.00 | 24 | 208 | 14.99 | 46.63 | 31.18 | -16.56 | 4 | -50.22 | 25.00 | -2.01 | -5.14 | 13.00 | 13.75 | FAIL |
| 3-oi-shock | dOI4h q95 follow calm-gated stop1.5% tgt3.0% | 1h | calm-gated | 1.50 | 3.00 | 24 | 119 | 14.72 | 44.54 | 17.52 | -20.35 | 2 | 165.72 | 100.00 | 3.31 | -1.71 | 13.00 | 12.69 | INSUFFICIENT-SAMPLE |
| 3-oi-shock | dOI1h q95 follow calm-gated stop1.0% tgt2.0% | 1h | calm-gated | 1.00 | 2.00 | 24 | 208 | 11.85 | 44.71 | 24.65 | -11.60 | 4 | -36.23 | 25.00 | -1.45 | -2.42 | 7.00 | 9.44 | FAIL |
| 3-oi-shock | dOI4h q95 follow calm-gated stop1.0% tgt2.0% | 1h | calm-gated | 1.00 | 2.00 | 24 | 119 | 8.51 | 42.86 | 10.13 | -14.14 | 2 | 197.51 | 100.00 | 3.95 | -0.55 | 6.00 | 8.51 | INSUFFICIENT-SAMPLE |
| 3-oi-shock | dOI1h q90 follow calm-gated stop1.0% tgt2.0% | 1h | calm-gated | 1.00 | 2.00 | 24 | 358 | 7.56 | 44.41 | 27.07 | -20.81 | 20 | 12.28 | 45.00 | 2.46 | -7.53 | 6.00 | 9.22 | SURVIVOR |
| 3-oi-shock | dOI1h q90 follow calm-gated stop1.5% tgt3.0% | 1h | calm-gated | 1.50 | 3.00 | 24 | 358 | 7.06 | 46.37 | 25.29 | -26.56 | 20 | 3.92 | 45.00 | 0.78 | -10.63 | 13.00 | 13.52 | SURVIVOR |
| 3-oi-shock | dOI1h q95 follow calm-gated stop1.5% tgt2.0% | 1h | calm-gated | 1.50 | 2.00 | 24 | 208 | 5.21 | 50.00 | 10.84 | -14.95 | 4 | 14.68 | 50.00 | 0.59 | -1.82 | 10.00 | 11.47 | INSUFFICIENT-SAMPLE |
| 3-oi-shock | dOI1h q95 fade calm-gated stop1.0% tgt3.0% | 1h | calm-gated | 1.00 | 3.00 | 24 | 208 | 4.79 | 36.06 | 9.97 | -19.31 | 4 | 91.37 | 50.00 | 3.65 | -2.01 | 8.50 | 10.49 | INSUFFICIENT-SAMPLE |
| 3-oi-shock | dOI4h q95 follow calm-gated stop1.5% tgt2.0% | 1h | calm-gated | 1.50 | 2.00 | 24 | 119 | 4.03 | 48.74 | 4.79 | -18.00 | 2 | 197.51 | 100.00 | 3.95 | -0.55 | 8.00 | 10.00 | INSUFFICIENT-SAMPLE |
| 3-oi-shock | dOI1h q95 fade calm-gated stop1.5% tgt3.0% | 1h | calm-gated | 1.50 | 3.00 | 24 | 208 | 3.16 | 41.35 | 6.57 | -19.85 | 4 | 65.23 | 50.00 | 2.61 | -2.50 | 12.00 | 13.02 | INSUFFICIENT-SAMPLE |
| 3-oi-shock | dOI4h q90 fade calm-gated stop1.5% tgt2.0% | 1h | calm-gated | 1.50 | 2.00 | 24 | 245 | 1.77 | 47.35 | 4.33 | -16.62 | 9 | -75.36 | 22.22 | -6.78 | -9.66 | 8.50 | 10.82 | FAIL |
| 3-oi-shock | dOI4h q90 follow calm-gated stop1.0% tgt3.0% | 1h | calm-gated | 1.00 | 3.00 | 24 | 245 | 0.61 | 33.47 | 1.49 | -21.22 | 9 | 87.00 | 66.67 | 7.83 | -2.29 | 7.50 | 9.88 | SURVIVOR |
| 3-oi-shock | dOI1h q90 follow calm-gated stop1.5% tgt2.0% | 1h | calm-gated | 1.50 | 2.00 | 24 | 358 | 0.11 | 50.28 | 0.40 | -31.64 | 20 | 20.45 | 55.00 | 4.09 | -7.04 | 9.00 | 11.34 | SURVIVOR |
| 3-oi-shock | dOI4h q90 fade calm-gated stop1.0% tgt2.0% | 1h | calm-gated | 1.00 | 2.00 | 24 | 245 | -0.44 | 39.18 | -1.09 | -18.24 | 9 | -65.96 | 11.11 | -5.94 | -6.75 | 6.00 | 8.60 | FAIL |
| 3-oi-shock | dOI4h q90 fade calm-gated stop1.5% tgt3.0% | 1h | calm-gated | 1.50 | 3.00 | 24 | 245 | -2.61 | 41.63 | -6.40 | -24.22 | 9 | -111.62 | 11.11 | -10.05 | -12.82 | 11.00 | 12.87 | FAIL |
| 3-oi-shock | dOI4h q90 fade calm-gated stop1.0% tgt3.0% | 1h | calm-gated | 1.00 | 3.00 | 24 | 245 | -3.42 | 33.47 | -8.37 | -20.86 | 9 | -97.43 | 0.00 | -8.77 | -9.56 | 8.00 | 10.10 | FAIL |
| 3-oi-shock | dOI1h q90 fade calm-gated stop1.0% tgt2.0% | 1h | calm-gated | 1.00 | 2.00 | 24 | 358 | -4.26 | 36.31 | -15.26 | -39.43 | 20 | -2.39 | 35.00 | -0.48 | -6.16 | 6.00 | 8.98 | FAIL |
| 3-oi-shock | dOI4h q90 follow calm-gated stop1.5% tgt3.0% | 1h | calm-gated | 1.50 | 3.00 | 24 | 245 | -4.33 | 39.18 | -10.62 | -24.89 | 9 | 123.72 | 77.78 | 11.13 | -2.79 | 12.00 | 12.80 | FAIL |
| 3-oi-shock | dOI1h q95 fade calm-gated stop1.0% tgt2.0% | 1h | calm-gated | 1.00 | 2.00 | 24 | 208 | -4.74 | 37.98 | -9.86 | -22.70 | 4 | 41.68 | 50.00 | 1.67 | -2.01 | 6.00 | 8.92 | FAIL |
| 3-oi-shock | dOI1h q90 fade calm-gated stop1.5% tgt2.0% | 1h | calm-gated | 1.50 | 2.00 | 24 | 358 | -5.70 | 42.74 | -20.39 | -39.92 | 20 | 2.54 | 45.00 | 0.51 | -7.16 | 10.00 | 11.51 | FAIL |
| 3-oi-shock | dOI1h q90 fade calm-gated stop1.0% tgt3.0% | 1h | calm-gated | 1.00 | 3.00 | 24 | 358 | -6.57 | 31.84 | -23.54 | -46.11 | 20 | 14.31 | 35.00 | 2.86 | -6.09 | 9.00 | 10.94 | FAIL |
| 3-oi-shock | dOI1h q95 fade calm-gated stop1.5% tgt2.0% | 1h | calm-gated | 1.50 | 2.00 | 24 | 208 | -6.90 | 44.23 | -14.35 | -27.22 | 4 | 16.04 | 50.00 | 0.64 | -2.50 | 9.50 | 11.11 | FAIL |
| 3-oi-shock | dOI1h q90 fade calm-gated stop1.5% tgt3.0% | 1h | calm-gated | 1.50 | 3.00 | 24 | 358 | -7.99 | 37.99 | -28.61 | -49.05 | 20 | 29.63 | 45.00 | 5.93 | -7.06 | 14.00 | 13.76 | FAIL |
| 3-oi-shock | dOI4h q90 follow calm-gated stop1.0% tgt2.0% | 1h | calm-gated | 1.00 | 2.00 | 24 | 245 | -8.24 | 35.51 | -20.19 | -28.33 | 9 | 69.84 | 66.67 | 6.29 | -2.29 | 6.00 | 8.06 | FAIL |
| 3-oi-shock | dOI4h q90 follow calm-gated stop1.5% tgt2.0% | 1h | calm-gated | 1.50 | 2.00 | 24 | 245 | -13.66 | 41.22 | -33.46 | -37.22 | 9 | 94.20 | 77.78 | 8.48 | -2.79 | 9.00 | 10.76 | FAIL |
| 3-oi-shock | dOI4h q95 fade calm-gated stop1.0% tgt3.0% | 1h | calm-gated | 1.00 | 3.00 | 24 | 119 | -18.01 | 26.89 | -21.44 | -31.43 | 2 | -110.16 | 0.00 | -2.20 | -2.70 | 7.00 | 8.40 | FAIL |
| 3-oi-shock | dOI4h q95 fade calm-gated stop1.0% tgt2.0% | 1h | calm-gated | 1.00 | 2.00 | 24 | 119 | -20.80 | 31.09 | -24.76 | -32.18 | 2 | -110.16 | 0.00 | -2.20 | -2.70 | 6.00 | 7.10 | FAIL |
| 3-oi-shock | dOI4h q95 fade calm-gated stop1.5% tgt3.0% | 1h | calm-gated | 1.50 | 3.00 | 24 | 119 | -24.20 | 35.29 | -28.80 | -41.24 | 2 | -159.48 | 0.00 | -3.19 | -3.68 | 9.00 | 11.20 | FAIL |
| 3-oi-shock | dOI4h q95 fade calm-gated stop1.5% tgt2.0% | 1h | calm-gated | 1.50 | 2.00 | 24 | 119 | -24.21 | 39.50 | -28.81 | -40.15 | 2 | -159.48 | 0.00 | -3.19 | -3.68 | 7.00 | 9.48 | FAIL |
| 3-oi-shock | dOI1h q90 fade ungated stop1.5% tgt2.0% | 1h | ungated | 1.50 | 2.00 | 24 | 732 | -2.40 | 44.95 | -17.59 | -39.92 | 119 | -11.05 | 42.86 | -13.15 | -20.06 | 6.00 | 8.93 | FAIL |
| 3-oi-shock | dOI4h q90 follow ungated stop1.0% tgt2.0% | 1h | ungated | 1.00 | 2.00 | 24 | 552 | -2.51 | 36.96 | -13.87 | -36.24 | 60 | 38.04 | 51.67 | 22.82 | -5.03 | 3.00 | 5.76 | FAIL |
| 3-oi-shock | dOI4h q90 follow ungated stop1.0% tgt3.0% | 1h | ungated | 1.00 | 3.00 | 24 | 552 | -2.89 | 30.62 | -15.98 | -39.64 | 60 | 40.15 | 43.33 | 24.09 | -9.56 | 4.00 | 7.49 | FAIL |
| 3-oi-shock | dOI1h q90 fade ungated stop1.5% tgt3.0% | 1h | ungated | 1.50 | 3.00 | 24 | 732 | -3.91 | 39.07 | -28.60 | -48.44 | 119 | -12.54 | 37.82 | -14.92 | -24.26 | 9.00 | 10.98 | FAIL |
| 3-oi-shock | dOI1h q95 fade ungated stop1.5% tgt3.0% | 1h | ungated | 1.50 | 3.00 | 24 | 535 | -4.08 | 37.76 | -21.81 | -35.05 | 56 | -32.20 | 30.36 | -18.03 | -21.44 | 7.00 | 9.84 | FAIL |
| 3-oi-shock | dOI4h q95 follow ungated stop1.0% tgt3.0% | 1h | ungated | 1.00 | 3.00 | 24 | 357 | -4.14 | 30.25 | -14.77 | -39.73 | 18 | 47.68 | 44.44 | 8.58 | -5.31 | 3.00 | 6.82 | FAIL |
| 3-oi-shock | dOI4h q90 follow ungated stop1.5% tgt2.0% | 1h | ungated | 1.50 | 2.00 | 24 | 552 | -4.18 | 44.57 | -23.07 | -44.88 | 60 | 36.03 | 55.00 | 21.62 | -5.14 | 5.00 | 7.90 | FAIL |
| 3-oi-shock | dOI1h q90 follow ungated stop1.0% tgt3.0% | 1h | ungated | 1.00 | 3.00 | 24 | 732 | -4.77 | 31.42 | -34.89 | -50.61 | 119 | 16.36 | 36.13 | 19.47 | -11.91 | 4.00 | 8.11 | FAIL |
| 3-oi-shock | dOI1h q90 fade ungated stop1.0% tgt2.0% | 1h | ungated | 1.00 | 2.00 | 24 | 732 | -4.94 | 35.66 | -36.19 | -47.77 | 119 | -16.00 | 32.77 | -19.04 | -25.31 | 4.00 | 6.82 | FAIL |
| 3-oi-shock | dOI4h q90 follow ungated stop1.5% tgt3.0% | 1h | ungated | 1.50 | 3.00 | 24 | 552 | -5.32 | 37.50 | -29.37 | -47.84 | 60 | 31.56 | 45.00 | 18.93 | -9.21 | 7.00 | 10.10 | FAIL |
| 3-oi-shock | dOI1h q90 fade ungated stop1.0% tgt3.0% | 1h | ungated | 1.00 | 3.00 | 24 | 732 | -5.40 | 30.46 | -39.56 | -55.29 | 119 | -14.01 | 29.41 | -16.67 | -25.64 | 5.00 | 8.48 | FAIL |
| 3-oi-shock | dOI4h q95 follow ungated stop1.0% tgt2.0% | 1h | ungated | 1.00 | 2.00 | 24 | 357 | -5.64 | 36.41 | -20.14 | -39.76 | 18 | 24.59 | 44.44 | 4.43 | -6.23 | 2.00 | 5.07 | FAIL |
| 3-oi-shock | dOI1h q95 fade ungated stop1.5% tgt2.0% | 1h | ungated | 1.50 | 2.00 | 24 | 535 | -5.96 | 43.55 | -31.89 | -40.17 | 56 | -43.74 | 32.14 | -24.49 | -24.49 | 5.00 | 7.97 | FAIL |
| 3-oi-shock | dOI1h q95 follow ungated stop1.0% tgt2.0% | 1h | ungated | 1.00 | 2.00 | 24 | 535 | -6.03 | 36.45 | -32.26 | -37.58 | 56 | 34.24 | 50.00 | 19.18 | -11.09 | 3.00 | 6.19 | FAIL |
| 3-oi-shock | dOI4h q95 follow ungated stop1.5% tgt3.0% | 1h | ungated | 1.50 | 3.00 | 24 | 357 | -6.67 | 37.54 | -23.80 | -48.52 | 18 | 30.08 | 50.00 | 5.41 | -6.79 | 6.00 | 9.12 | FAIL |
| 3-oi-shock | dOI1h q90 follow ungated stop1.0% tgt2.0% | 1h | ungated | 1.00 | 2.00 | 24 | 732 | -7.10 | 36.07 | -51.98 | -57.04 | 119 | 9.38 | 41.18 | 11.16 | -9.41 | 3.00 | 6.50 | FAIL |
| 3-oi-shock | dOI1h q95 fade ungated stop1.0% tgt3.0% | 1h | ungated | 1.00 | 3.00 | 24 | 535 | -7.48 | 28.97 | -40.02 | -50.01 | 56 | -7.51 | 28.57 | -4.21 | -15.18 | 4.00 | 7.39 | FAIL |
| 3-oi-shock | dOI1h q90 follow ungated stop1.5% tgt3.0% | 1h | ungated | 1.50 | 3.00 | 24 | 732 | -7.49 | 38.93 | -54.84 | -66.36 | 119 | 12.68 | 43.70 | 15.09 | -14.17 | 8.00 | 10.87 | FAIL |
| 3-oi-shock | dOI4h q95 follow ungated stop1.5% tgt2.0% | 1h | ungated | 1.50 | 2.00 | 24 | 357 | -7.58 | 44.26 | -27.04 | -48.67 | 18 | 16.05 | 50.00 | 2.89 | -6.91 | 4.00 | 6.81 | FAIL |
| 3-oi-shock | dOI1h q95 follow ungated stop1.0% tgt3.0% | 1h | ungated | 1.00 | 3.00 | 24 | 535 | -7.88 | 29.91 | -42.15 | -48.58 | 56 | 26.84 | 41.07 | 15.03 | -11.15 | 4.00 | 7.79 | FAIL |
| 3-oi-shock | dOI1h q95 fade ungated stop1.0% tgt2.0% | 1h | ungated | 1.00 | 2.00 | 24 | 535 | -8.23 | 34.21 | -44.05 | -51.33 | 56 | -20.45 | 30.36 | -11.45 | -15.18 | 3.00 | 6.01 | FAIL |
| 3-oi-shock | dOI1h q90 follow ungated stop1.5% tgt2.0% | 1h | ungated | 1.50 | 2.00 | 24 | 732 | -8.30 | 44.26 | -60.73 | -65.64 | 119 | 4.77 | 47.90 | 5.68 | -11.41 | 5.00 | 8.84 | FAIL |
| 3-oi-shock | dOI1h q95 follow ungated stop1.5% tgt2.0% | 1h | ungated | 1.50 | 2.00 | 24 | 535 | -9.16 | 43.74 | -48.98 | -58.79 | 56 | 62.42 | 62.50 | 34.96 | -7.42 | 5.00 | 8.24 | FAIL |
| 3-oi-shock | dOI4h q90 fade ungated stop1.0% tgt2.0% | 1h | ungated | 1.00 | 2.00 | 24 | 552 | -9.89 | 33.33 | -54.59 | -59.92 | 60 | -25.41 | 28.33 | -15.24 | -17.22 | 3.00 | 6.01 | FAIL |
| 3-oi-shock | dOI4h q90 fade ungated stop1.5% tgt2.0% | 1h | ungated | 1.50 | 2.00 | 24 | 552 | -10.26 | 42.39 | -56.64 | -65.50 | 60 | -32.68 | 36.67 | -19.61 | -21.41 | 5.00 | 7.97 | FAIL |
| 3-oi-shock | dOI4h q95 fade ungated stop1.0% tgt2.0% | 1h | ungated | 1.00 | 2.00 | 24 | 357 | -10.37 | 33.33 | -37.02 | -45.81 | 18 | -9.61 | 33.33 | -1.73 | -5.22 | 2.00 | 4.70 | FAIL |
| 3-oi-shock | dOI4h q95 fade ungated stop1.5% tgt2.0% | 1h | ungated | 1.50 | 2.00 | 24 | 357 | -10.38 | 42.58 | -37.05 | -46.94 | 18 | -23.16 | 38.89 | -4.17 | -7.36 | 4.00 | 6.53 | FAIL |
| 3-oi-shock | dOI1h q95 follow ungated stop1.5% tgt3.0% | 1h | ungated | 1.50 | 3.00 | 24 | 535 | -11.26 | 36.82 | -60.26 | -65.71 | 56 | 47.34 | 53.57 | 26.51 | -10.91 | 7.00 | 10.32 | FAIL |
| 3-oi-shock | dOI4h q90 fade ungated stop1.0% tgt3.0% | 1h | ungated | 1.00 | 3.00 | 24 | 552 | -11.37 | 27.17 | -62.75 | -68.78 | 60 | -25.67 | 25.00 | -15.40 | -16.58 | 4.00 | 7.24 | FAIL |
| 3-oi-shock | dOI4h q90 fade ungated stop1.5% tgt3.0% | 1h | ungated | 1.50 | 3.00 | 24 | 552 | -11.52 | 35.87 | -63.61 | -72.30 | 60 | -32.64 | 33.33 | -19.58 | -21.39 | 7.00 | 9.66 | FAIL |
| 3-oi-shock | dOI4h q95 fade ungated stop1.5% tgt3.0% | 1h | ungated | 1.50 | 3.00 | 24 | 357 | -13.26 | 34.45 | -47.33 | -50.52 | 18 | -10.75 | 33.33 | -1.94 | -5.64 | 5.00 | 8.25 | FAIL |
| 3-oi-shock | dOI4h q95 fade ungated stop1.0% tgt3.0% | 1h | ungated | 1.00 | 3.00 | 24 | 357 | -13.28 | 25.49 | -47.41 | -48.34 | 18 | 0.51 | 27.78 | 0.09 | -5.81 | 3.00 | 5.91 | FAIL |
| 4-breakout-failure | N48 X0.10% calm-gated | 1h | calm-gated | 0.49 | 1.94 | 24 | 260 | -2.65 | 26.15 | -6.90 | -24.78 | 61 | 0.11 | 26.23 | 0.07 | -7.51 | 3.00 | 5.74 | FAIL |
| 4-breakout-failure | N24 X0.15% calm-gated | 1h | calm-gated | 0.48 | 1.37 | 24 | 348 | -3.05 | 30.46 | -10.61 | -24.66 | 82 | -9.40 | 25.61 | -7.71 | -11.48 | 2.00 | 4.66 | FAIL |
| 4-breakout-failure | N24 X0.20% calm-gated | 1h | calm-gated | 0.48 | 1.40 | 24 | 322 | -3.73 | 29.81 | -12.03 | -23.89 | 78 | -6.48 | 26.92 | -5.06 | -10.14 | 2.00 | 4.64 | FAIL |
| 4-breakout-failure | N24 X0.10% calm-gated | 1h | calm-gated | 0.47 | 1.33 | 24 | 370 | -3.97 | 30.81 | -14.68 | -27.01 | 92 | -10.95 | 25.00 | -10.07 | -12.66 | 2.00 | 4.81 | FAIL |
| 4-breakout-failure | N48 X0.15% calm-gated | 1h | calm-gated | 0.49 | 1.96 | 24 | 246 | -6.00 | 24.39 | -14.76 | -26.62 | 53 | -4.49 | 24.53 | -2.38 | -9.27 | 2.00 | 5.58 | FAIL |
| 4-breakout-failure | N48 X0.20% calm-gated | 1h | calm-gated | 0.49 | 2.00 | 24 | 235 | -8.05 | 23.40 | -18.91 | -26.78 | 51 | -7.29 | 23.53 | -3.72 | -10.77 | 2.00 | 5.60 | FAIL |
| 4-breakout-failure | N24 X0.20% ungated | 1h | ungated | 0.66 | 2.03 | 24 | 653 | -4.18 | 28.64 | -27.31 | -42.53 | 230 | -12.66 | 26.09 | -29.12 | -34.53 | 2.00 | 5.60 | FAIL |
| 4-breakout-failure | N24 X0.15% ungated | 1h | ungated | 0.64 | 1.99 | 24 | 683 | -5.14 | 28.11 | -35.08 | -46.20 | 244 | -13.73 | 24.59 | -33.51 | -36.03 | 2.00 | 5.41 | FAIL |
| 4-breakout-failure | N24 X0.10% ungated | 1h | ungated | 0.63 | 1.94 | 24 | 710 | -5.32 | 28.03 | -37.75 | -46.14 | 250 | -13.52 | 24.40 | -33.80 | -36.24 | 2.00 | 5.50 | FAIL |
| 4-breakout-failure | N48 X0.20% ungated | 1h | ungated | 0.71 | 2.94 | 24 | 479 | -7.88 | 23.80 | -37.72 | -51.03 | 167 | -4.62 | 26.95 | -7.72 | -25.21 | 3.00 | 6.22 | FAIL |
| 4-breakout-failure | N48 X0.10% ungated | 1h | ungated | 0.69 | 2.85 | 24 | 515 | -8.28 | 24.08 | -42.66 | -50.66 | 183 | -6.76 | 25.68 | -12.38 | -26.37 | 3.00 | 6.34 | FAIL |
| 4-breakout-failure | N48 X0.15% ungated | 1h | ungated | 0.70 | 2.91 | 24 | 496 | -8.78 | 23.39 | -43.55 | -51.19 | 173 | -3.57 | 26.59 | -6.17 | -22.24 | 3.00 | 6.23 | FAIL |

## Verdict counts

| verdict | count |
|:--|--:|
| FAIL | 157 |
| INSUFFICIENT-SAMPLE | 7 |
| SURVIVOR | 4 |
| **total** | **168** |

All 4 survivors and all 7 insufficient-sample configs belong to **family 3
(OI-shock fade/follow)**. Families 1, 2, and 4 are a clean sweep of FAIL:
32/32, 60/60, and 12/12 respectively. No look was spent on any of them
(nothing in this round touches the sealed 20% test slice).

## Per-family autopsy

### Family 1, calm-gated range fade: FAILED, and the calm gate makes it WORSE

All 32 configs (N in {24,48} x z-threshold in {1.5,2.0} x stop in {1.0,1.5}%
x tf in {1h,2h} x gate in {calm,ungated}) lost money on train, val, or both.
Every single row is FAIL. The best train number in the whole family is
still -$4.93/trade (2h, N24, z1.5, calm-gated, stop 1.5%), and its val is
-$12.24/trade. This is the mean-reversion shape most directly aimed at
"grind = ranges," and it simply does not clear costs at 1h/2h resolution:
the z-score extremes it fades revert too slowly/shallowly relative to the
18bps-ish round-trip hurdle plus the stop discipline required for 20x.

**Does the calm gate help here? No: it measurably hurts, on val
specifically.** Pairing every calm-gated config against its identical
ungated twin (16 pairs, same N/z-threshold/stop/tf, gate is the only
difference):

- Train: calm-gated wins 10/16 pairs (mean tr_exp: calm -$8.41 vs ungated
  -$9.50, a marginal edge for the gate).
- **Val: calm-gated wins 0/16 pairs, none.** Mean va_exp: calm -$21.09
  vs ungated -$12.35. Restricting entries to quiet-regime bars nearly
  DOUBLED the average val loss per trade for this family.

Read plainly: in the val window, filtering range-fade entries down to only
the quietest bars did not improve the edge; it concentrated the losses.
The likely mechanism (not proven, flagging for the queue if this family is
ever revisited): quiet-regime ranges are quiet because they're NOT
mean-reverting in a tradeable way. Price can sit 1.5-2 std devs from a
short rolling mean for a long time in a genuinely low-vol drift, and a
tight 1.0-1.5% stop gets clipped on the way to a touch that arrives late
or never (median hold 4-10h against a 24h cap; most trades were closed by
stop or time-out, not by reaching the mean). This is the opposite dynamic
from breakdown-N20 in round 41, where the calm gate correctly identified
"boring bars are the ones where a real breakdown still means something."

### Family 2, funding-settlement scalp: FAILED both hypotheses, but hypothesis A shows a real near-miss

**Hypothesis A (pre-settlement drift, fade the currently-crowded side
2-4 bars before an 00/08/16 UTC settlement)**: 48 configs, all FAIL, but
the best train number is genuinely interesting: `A f>1.5bp before4 exit+1
calm-gated tgtnone`, **train $5.44/trade over 319 trades (46.1% win)**,
died only on val (-$12.40/trade, 48 trades). Its close neighbor `before2
exit+2 calm-gated tgt2.0%` also had a clean positive train ($0.72/319... 
322 trades) with a small negative val (-$3.63/41 trades), small enough
that it reads as noise rather than a structural miss. This is NOT a
random one-off: 3 of the top 5 train configs in this family are
calm-gated variants of the SAME core idea (fade crowded funding ahead of
settlement), which is a better fragility signature than round 41's buried
bleed-rider (whose neighbors all failed together). Flagging for the queue,
not claiming an edge exists: it needs a genuinely fresh val-style check
(more settlements, not a re-tune) before it deserves a test look.

**Hypothesis B (post-settlement snap, opposite the prior 8h drift, AT the
settlement bar)**: 12 configs, all FAIL on train (best: -$2.91/trade), so
none of them are even candidates regardless of val: this shape doesn't
have an edge as specified.

**Does the calm gate help here?**
- Hypothesis A: calm-gated wins train 19/24 pairs (mean tr_exp: calm
  -$2.04 vs ungated -$4.09, a real, consistent improvement) but val is a
  coin flip (12/24, mean va_exp calm -$6.68 vs ungated -$6.84, a wash).
  The gate helps the entry quality but doesn't rescue the val failure.
- Hypothesis B: calm-gated wins train 5/6 and **val 6/6**, every single
  gated config beats its ungated twin on val (mean va_exp: calm +$4.43 vs
  ungated -$4.30). But hypothesis B never clears train positive to begin
  with, so this is a case of "the gate helps a genuinely bad idea lose
  less," not a rescued edge.

### Family 3, OI-shock fade/follow: 4 SURVIVORS, all the same core shape, and the calm gate is doing real, measurable work

This is the round's one real finding. All 4 survivors share the identical
entry condition: **dOI over a matched window >= its train-only 90th
percentile (2.32% for the 1h window, 4.93% for the 4h window), price moved
WITH the OI shock (the "follow" variant, not "fade"), and the calm gate
on**, differing only in stop/target:

| config | tr_n | tr_exp | va_n | va_exp | med hold h | mean hold h |
|:--|--:|--:|--:|--:|--:|--:|
| dOI1h q90 follow calm-gated stop1.0% tgt2.0% | 358 | $7.56 | 20 | $12.28 | 6.0 | 9.2 |
| dOI1h q90 follow calm-gated stop1.5% tgt2.0% | 358 | $0.11 | 20 | $20.45 | 9.0 | 11.3 |
| dOI1h q90 follow calm-gated stop1.5% tgt3.0% | 358 | $7.06 | 20 | $3.92 | 13.0 | 13.5 |
| dOI4h q90 follow calm-gated stop1.0% tgt3.0% | 245 | $0.61 | 9 | $87.00 | 7.5 | 9.9 |

Grid-neighbor check (the round 41 lesson: a real edge has survivor
neighbors, an overfit one has a fragile island): of the 4 stop/target
combinations for `dOI1h q90 follow calm-gated`, **3 of 4 survive**; the
4th (stop1.0/tgt3.0) is train-positive at $17.04/trade but died on val
(-$12.87/20 trades, likely one bad tail trade skewing a 20-trade sample,
since 3.0% targets held a median 8.5h and only 35% won). That's a
reasonably dense neighborhood, not an island. The `dOI4h` survivor is
thinner: only 1 of its 4 stop/target combinations survives, val is 9
trades, and its 3 non-surviving neighbors show wildly unstable val numbers
(+$69 to +$123/trade on only 9 trades), directionally consistent
(all positive) but not something to trust the magnitude of. Treat the
`dOI1h` shape as the real candidate and the `dOI4h` one as a weaker,
same-family echo.

**Does the calm gate help here? Yes, dramatically, and this is the
cleanest before/after in the whole round.** Take the exact winning shape
and strip the gate:

| | tr_n | tr_exp | va_n | va_exp |
|:--|--:|--:|--:|--:|
| dOI1h q90 follow **calm-gated** stop1.0% tgt2.0% | 358 | **+$7.56** | 20 | +$12.28 |
| dOI1h q90 follow **ungated** stop1.0% tgt2.0% | 732 | **-$7.10** | 119 | +$9.38 |
| dOI1h q90 follow **calm-gated** stop1.5% tgt3.0% | 358 | **+$7.06** | 20 | +$3.92 |
| dOI1h q90 follow **ungated** stop1.5% tgt3.0% | 732 | **-$7.49** | 119 | +$12.68 |

Restricting the identical OI-shock-follow entry to quiet-regime bars
roughly HALVES the trade count (358 vs 732, consistent with the gate
being active ~51.6% of train+val bars) and **flips train expectancy from
solidly negative to solidly positive** on both stop/target pairs shown
(and the pattern holds across the other two survivor pairs too, see the
full table). Pooled across all 32 family-3 pairs: calm-gated wins train
22/32 (mean tr_exp -$0.47 vs ungated -$7.30) and val 18/32 (mean va_exp
+$9.72 vs ungated +$5.04). This is the family where the round's central
thesis, "the quiet gate conditions profitability," actually holds up
under a same-config, gate-only comparison, not just in aggregate.

**Autopsy of the shape itself**: "follow" (trade WITH the price move that
accompanied the OI shock) beat "fade" (trade against it) everywhere in
this family: every single fade variant that reached FAIL/SURVIVOR
territory (as opposed to insufficient-sample) lost money. Read plainly:
when open interest surges alongside a price move DURING an already-quiet
regime, that's new conviction entering a market with no crowd already
positioned against it: a shape closer to "confirmed breakout" than
"overextended, fade it." The q95 (rarer) threshold configs are directionally
consistent (all train-positive, several dramatically so) but fall into
INSUFFICIENT-SAMPLE (2-4 val trades): a real finding, not a fail, but not
deployable at this sample size either.

### Family 4, quiet-range breakout-failure: FAILED, calm gate helps but never enough

All 12 configs (N in {24,48} x X in {0.10,0.15,0.20}% x gate) are FAIL. Best
train number: -$2.65/trade (N48, X0.10%, calm-gated, 260 trades), best val:
+$0.11/trade on the same config (61 trades), genuinely close to
break-even but never crosses zero on both windows simultaneously. The
"failed breakout snaps back to the range" intuition is directionally
real (win rates cluster 23-31%, low as expected for a reversion-to-midpoint
target, but the wins/losses ratio never quite clears the ~18bps hurdle
plus a wick-distance stop that's often tight: median stop computed at
only ~0.47-0.49% train-derived, well under the 1.5% family cap, because
failed-breakout wicks in the grind are short).

**Does the calm gate help?** Yes, consistently but not enough: calm-gated
beats ungated on train in 5/6 pairs (mean tr_exp -$4.58 vs -$6.60) and val
in 4/6 pairs (mean va_exp -$6.42 vs -$9.15); every calm-gated config in
the family sits above its ungated twin on train, and the calm-gated
versions occupy the top 5 of 6 rows in the full family ranking by tr_exp.
The gate is doing real, directionally-correct work here (fewer, better
entries), it just isn't enough to overcome the geometry: the train-derived
stop is too tight relative to the target for the win rate this shape
produces.

## Top-3 sealed-look candidates

Selection is by TRAIN expectancy only, per protocol; val is reported but
was never tuned against. All 3 below sit inside family 3 (the only family
with any survivors); see the per-family autopsy above for why they're a
correlated family, not 3 independent discoveries.

1. **`dOI1h q90 follow calm-gated stop1.0% tgt2.0%`**, train $7.56/trade
   x 358 trades (44.4% win, -20.8% train DD), val $12.28/trade x 20 trades
   (45.0% win, -7.5% val DD). Median hold **6.0h**, mean **9.2h**, the
   fastest of the three, comfortably inside the 24h ceiling with room to
   spare. Strongest single train number with a full, credible val sample.
   **Top pick.**
2. **`dOI1h q90 follow calm-gated stop1.5% tgt3.0%`**, train $7.06/trade
   x 358 trades (46.4% win, -26.6% train DD), val $3.92/trade x 20 trades
   (45.0% win, -10.6% val DD). Same 358/20 trade population as #1 (same
   entries, wider stop/target), median hold **13.0h**, mean **13.5h**, or
   about 2x the hold time of #1 for a similar train edge and a weaker val
   number. Worth a look mainly to test whether the wider geometry is more
   robust out of sample than #1's tighter one, not because its own numbers
   are stronger.
3. **`dOI4h q90 follow calm-gated stop1.0% tgt3.0%`**, train $0.61/trade
   x 245 trades (33.5% win, -21.2% train DD), val $87.00/trade x **9
   trades only** (66.7% win, -2.3% val DD). Median hold **7.5h**, mean
   **9.9h**. Weakest train edge of the three and the val number is not to
   be trusted at face value (9 trades, and its 3 stop/target neighbors
   swing from -$76 to +$124/trade on similarly thin samples). Include
   this one to test the SAME underlying OI-shock-follow thesis on the 4h
   window, explicitly flagged as the lowest-confidence pick of the three,
   not because it's a strong candidate on its own numbers.

**Recommendation if only one look is spent**: #1. It has the best
train/val agreement, the tightest stop (best 20x-leverage fit), the
shortest hold time, and is the least likely of the three to be a
stop/target-selection artifact of the same underlying signal.

## Ambiguous calls made this round (stated plainly, per protocol)

- **Family 1's z-score extra shift(1)**: the brief specified "z ... 
  shift(1)'d," which is one bar more conservative than the engine's own
  bar-close/next-open mechanic strictly requires (the rolling mean/std at
  bar N's close only ever uses already-printed bars). Implemented exactly
  as specified rather than the more aggressive unshifted version: this
  round's numbers are, if anything, slightly pessimistic on family 1's
  entry timing, not optimistic.
- **Family 2 hypothesis A's "funding is extreme" signal** uses the
  MOST RECENTLY SETTLED rate (the prior period's, via `align_funding`),
  never the upcoming settlement's realized rate; the latter would be
  lookahead since the upcoming rate isn't locked until it settles. This is
  the standard "funding is persistent/autocorrelated, so fade the
  currently-crowded side ahead of the next settlement" reading of the
  brief, not a shortcut.
- **Family 3's dOI "extreme" threshold** is a TRAIN-only fixed quantile
  (90th/95th of |dOI%| over the train slice), held constant across
  train/val (same convention as every other train-derived threshold in
  this repo). The window (1h/4h) is
  expressed as a bar count on the 1h price/OI frame rather than as
  separate 2h/4h frames, matching the brief's "dOI = OI change over
  {1h, 4h}" wording directly.
- **Family 4's stop/target distances** (to the breakout wick, to the range
  midpoint) are TRAIN-only medians pooled across both directions'
  qualifying entries, exactly mirroring step43 family 4's VWAP-fade
  approximation (same repo convention, restated per family rather than
  re-derived).
- **No CSV or other file was written by this run**: per this round's
  "touch NOTHING else" instruction, the working DataFrame was captured to
  a scratch path outside the repo for this write-up's analysis, not
  committed anywhere in `~/cryptobot`.
