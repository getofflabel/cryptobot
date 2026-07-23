# Round 43 — BTC day-trade hunt (step43_daytrade.py)

Research only. No file touched besides this one and step43_daytrade.py. No
live orders. Test slice (final 20% per timeframe) was never touched — every
number below is TRAIN or VAL.

## Setup

- **Data spans (actual, from the cached parquets — all three full 6+ years,
  not truncated):**
  - 15m: `data_bybit_BTCUSDT_15m_full.parquet` — 221,823 bars, 2020-03-25 to
    2026-07-23
  - 1h: `data_bybit_BTCUSDT_1h_full.parquet` — 55,451 bars, 2020-03-25 to
    2026-07-22
  - 4h (champion-trend source only): `data_bybit_BTCUSDT_4h_full.parquet` —
    13,863 bars, 2020-03-25 to 2026-07-22
  - Funding: `data_bybit_BTCUSDT_funding.parquet` — 6,931 settlements
  - **Caveat resolved**: the task brief flagged that 15m "may cover a
    shorter span" — it does not; it matches 1h/4h almost exactly.
- **Split**: chronological 60/20/20 per timeframe. 15m: train ends
  2024-01-10, val ends 2025-04-16 (test sealed). 1h: identical dates.
- **Costs**: `CostModel()` defaults (6bps taker / 2bps maker, 1bp
  half-spread, 2bp slippage), `execution="maker"`, real funding via
  `align_funding` (imported from step11/step41's canonical helpers).
- **4h champion trend** (direction filter for families 1 & 3, gate for
  family 4): `vol_gated_ma(fast=20, slow=100, min_atr_pct=1.5)` — the
  standing champion. In-market (champ==1) 39.9% of all 4h bars.
- **Survivor bar**: positive expectancy train AND val, >=30 train trades,
  >=8 val trades. Selected by TRAIN only; val checked once.
- **98 configs run in 16.5 seconds.** Verdict counts: 95 FAIL, 3 SURVIVOR,
  0 INSUFFICIENT-SAMPLE.
- **Approximations forced by the engine** (backtest.py takes ONE fixed
  `stop_pct`/`target_pct` per run, not a per-trade dynamic level — same
  limitation step41 documents): every family that calls for an ATR-scaled,
  range-scaled, or VWAP-distance-scaled stop/target instead uses a
  TRAIN-only median of that distance, held fixed across train and val, and
  **every stop is hard-capped at 1.7%** (the mandate's "ideal" ceiling —
  nothing here needed the looser 2.0% allowance). Stated per-family below.
- **max_hold** is not an engine parameter; it's enforced inside each
  family's own signal state machine (a bidirectional generalization of
  `strategy.event_short`), which forces flat after N bars regardless of
  whether a stop/target has fired. Every family's max_hold is <=24h in
  bars, verified by construction and by the reported hold-time stats below.
- **Drawdown caveat**: all `dd%` figures are on the engine's 1x, fully
  compounded equity curve (100% of equity re-risked every trade) — they are
  NOT leverage-adjusted. A tight per-trade stop caps single-trade
  liquidation risk at whatever the dial is set to, but it does not cap
  *sequence* risk (several losing stops in a row). Treat the dd% column as
  "how painful this book is to hold," not as "what leverage this survives."

## Full results (98 configs, train + val, full costs, test sealed)

| family | config | tf | stop% | target% | max_hold_h | tr_n | tr_exp | tr_win% | tr_ret% | tr_dd% | va_n | va_exp | va_win% | va_ret% | va_dd% | med_hold_h | mean_hold_h | verdict |
|:-------------------|:---------------------------------|:-----|--------:|----------:|-------------:|-------:|---------:|----------:|----------:|---------:|-------:|---------:|----------:|----------:|---------:|-------------:|--------------:|:--|
| 1-momentum-burst   | X0.8% champ tgt2xATR hold8h      | 1h   |    0.81 |      1.62 |            8 |   1198 |    -5.72 |     34.97 |    -68.53 |   -70.59 |    346 |     5.95 |     41.62 |     20.58 |   -14.82 |         1    |          2.35 | FAIL      |
| 1-momentum-burst   | X0.8% champ tgt2xATR hold24h     | 1h   |    0.81 |      1.62 |           24 |    706 |    -7.12 |     33.29 |    -50.23 |   -56.68 |    220 |    10.13 |     41.36 |     22.28 |   -13.16 |         2    |          3.63 | FAIL      |
| 1-momentum-burst   | X0.8% champ tgt3xATR hold8h      | 1h   |    0.81 |      2.43 |            8 |   1198 |    -3.68 |     31.8  |    -44.08 |   -56.72 |    346 |     0.04 |     36.42 |      0.13 |   -16.61 |         2    |          3    | FAIL      |
| 1-momentum-burst   | X0.8% champ tgt3xATR hold24h     | 1h   |    0.81 |      2.43 |           24 |    706 |    -1.89 |     28.9  |    -13.35 |   -42.95 |    220 |    -1.16 |     29.55 |     -2.54 |   -18.15 |         2    |          5.21 | FAIL      |
| 1-momentum-burst   | X0.8% raw tgt2xATR hold8h        | 1h   |    0.81 |      1.62 |            8 |   1744 |    -3.93 |     36.35 |    -68.52 |   -77.15 |    517 |    -1.63 |     39.46 |     -8.44 |   -24.57 |         1    |          2.55 | FAIL      |
| 1-momentum-burst   | X0.8% raw tgt2xATR hold24h       | 1h   |    0.81 |      1.62 |           24 |    894 |    -3.2  |     35.79 |    -28.64 |   -53.13 |    286 |     0.1  |     37.76 |      0.29 |   -19.01 |         2    |          3.96 | FAIL      |
| 1-momentum-burst   | X0.8% raw tgt3xATR hold8h        | 1h   |    0.81 |      2.43 |            8 |   1744 |    -2.35 |     32.97 |    -41.05 |   -61.48 |    517 |    -1.24 |     37.14 |     -6.41 |   -28.68 |         2    |          3.18 | FAIL      |
| 1-momentum-burst   | X0.8% raw tgt3xATR hold24h       | 1h   |    0.81 |      2.43 |           24 |    894 |    -1.49 |     29.42 |    -13.32 |   -45.39 |    286 |    -1.54 |     29.72 |     -4.4  |   -23.81 |         2    |          5.51 | FAIL      |
| 1-momentum-burst   | X1.2% champ tgt2xATR hold8h      | 1h   |    0.81 |      1.62 |            8 |    714 |    -6.01 |     34.73 |    -42.92 |   -46.75 |    191 |     2.98 |     40.84 |      5.68 |    -9.6  |         1    |          1.78 | FAIL      |
| 1-momentum-burst   | X1.2% champ tgt2xATR hold24h     | 1h   |    0.81 |      1.62 |           24 |    467 |    -3.7  |     36.19 |    -17.28 |   -25.74 |    137 |    23.85 |     46.72 |     32.67 |    -5.8  |         1    |          2.7  | FAIL      |
| 1-momentum-burst   | X1.2% champ tgt3xATR hold8h      | 1h   |    0.81 |      2.43 |            8 |    714 |    -4.65 |     30.11 |    -33.18 |   -39.06 |    191 |     1.93 |     36.13 |      3.69 |   -14.89 |         1    |          2.43 | FAIL      |
| 1-momentum-burst   | X1.2% champ tgt3xATR hold24h     | 1h   |    0.81 |      2.43 |           24 |    467 |    -3.62 |     28.27 |    -16.89 |   -25.75 |    137 |    19.46 |     36.5  |     26.66 |    -8.53 |         1    |          4.15 | FAIL      |
| 1-momentum-burst   | X1.2% raw tgt2xATR hold8h        | 1h   |    0.81 |      1.62 |            8 |   1117 |    -4.83 |     35.63 |    -54    |   -57.49 |    300 |     5.9  |     42    |     17.69 |   -14.04 |         1    |          2.05 | FAIL      |
| 1-momentum-burst   | X1.2% raw tgt2xATR hold24h       | 1h   |    0.81 |      1.62 |           24 |    661 |    -5.52 |     34.8  |    -36.52 |   -46.79 |    203 |     3.61 |     39.9  |      7.32 |   -13.42 |         1    |          3.18 | FAIL      |
| 1-momentum-burst   | X1.2% raw tgt3xATR hold8h        | 1h   |    0.81 |      2.43 |            8 |   1117 |    -4.8  |     30.8  |    -53.63 |   -58    |    300 |     8.26 |     38.33 |     24.77 |   -15.56 |         1    |          2.72 | FAIL      |
| 1-momentum-burst   | X1.2% raw tgt3xATR hold24h       | 1h   |    0.81 |      2.43 |           24 |    661 |    -4.68 |     27.84 |    -30.95 |   -47.71 |    203 |    -0.89 |     31.53 |     -1.8  |   -19.72 |         2    |          4.79 | FAIL      |
| 1-momentum-burst   | X1.8% champ tgt2xATR hold8h      | 1h   |    0.81 |      1.62 |            8 |    343 |    -5    |     35.28 |    -17.16 |   -25.05 |     76 |    14.26 |     44.74 |     10.83 |    -5.29 |         0    |          1.16 | FAIL      |
| 1-momentum-burst   | X1.8% champ tgt2xATR hold24h     | 1h   |    0.81 |      1.62 |           24 |    257 |    -1.18 |     36.96 |     -3.02 |   -20.41 |     61 |    12.03 |     44.26 |      7.34 |    -6.28 |         0    |          1.71 | FAIL      |
| 1-momentum-burst   | X1.8% champ tgt3xATR hold8h      | 1h   |    0.81 |      2.43 |            8 |    343 |    -5.09 |     29.74 |    -17.44 |   -23.94 |     76 |     5.26 |     34.21 |      3.99 |    -8.65 |         0    |          1.81 | FAIL      |
| **1-momentum-burst** | **X1.8% champ tgt3xATR hold24h** | **1h** | **0.81** | **2.43** | **24** | **257** | **7.20** | **30.74** | **18.51** | **-17.72** | **61** | **8.74** | **34.43** | **5.33** | **-8.07** | **1** | **2.92** | **SURVIVOR** |
| 1-momentum-burst   | X1.8% raw tgt2xATR hold8h        | 1h   |    0.81 |      1.62 |            8 |    568 |    -5.88 |     34.86 |    -33.39 |   -41.38 |    134 |    43.1  |     52.24 |     57.75 |    -6.09 |         0    |          1.31 | FAIL      |
| 1-momentum-burst   | X1.8% raw tgt2xATR hold24h       | 1h   |    0.81 |      1.62 |           24 |    389 |    -1.14 |     37.02 |     -4.43 |   -26.25 |    100 |    36.07 |     51    |     36.07 |    -6.09 |         0    |          1.84 | FAIL      |
| 1-momentum-burst   | X1.8% raw tgt3xATR hold8h        | 1h   |    0.81 |      2.43 |            8 |    568 |    -6.06 |     29.75 |    -34.44 |   -42    |    134 |    55.53 |     46.27 |     74.41 |    -6.57 |         1    |          2.01 | FAIL      |
| **1-momentum-burst** | **X1.8% raw tgt3xATR hold24h** | **1h** | **0.81** | **2.43** | **24** | **389** | **7.13** | **31.11** | **27.74** | **-26.23** | **100** | **37.90** | **42.00** | **37.90** | **-6.68** | **1** | **3.32** | **SURVIVOR** |
| 1-momentum-burst   | X0.8% champ tgt2xATR hold8h      | 15m  |    0.36 |      0.72 |            8 |   1706 |    -4.63 |     33.29 |    -78.91 |   -79.31 |    506 |    -8.2  |     31.82 |    -41.52 |   -42.2  |         0.25 |          0.57 | FAIL      |
| 1-momentum-burst   | X0.8% champ tgt2xATR hold24h     | 15m  |    0.36 |      0.72 |           24 |    878 |    -5.79 |     34.05 |    -50.83 |   -52.7  |    285 |   -11.07 |     29.47 |    -31.55 |   -31.55 |         0.25 |          0.64 | FAIL      |
| 1-momentum-burst   | X0.8% champ tgt3xATR hold8h      | 15m  |    0.36 |      1.08 |            8 |   1706 |    -4.71 |     25.67 |    -80.28 |   -81.5  |    506 |    -7.7  |     25.3  |    -38.94 |   -39.96 |         0.25 |          0.87 | FAIL      |
| 1-momentum-burst   | X0.8% champ tgt3xATR hold24h     | 15m  |    0.36 |      1.08 |           24 |    878 |    -6.16 |     25.51 |    -54.04 |   -57.45 |    285 |   -12.17 |     21.4  |    -34.69 |   -35.55 |         0.25 |          1.07 | FAIL      |
| 1-momentum-burst   | X0.8% raw tgt2xATR hold8h        | 15m  |    0.36 |      0.72 |            8 |   2261 |    -3.85 |     33.35 |    -87.1  |   -87.33 |    678 |    -8.01 |     30.97 |    -54.3  |   -54.4  |         0.25 |          0.57 | FAIL      |
| 1-momentum-burst   | X0.8% raw tgt2xATR hold24h       | 15m  |    0.36 |      0.72 |           24 |   1037 |    -5.01 |     34.91 |    -51.91 |   -53.82 |    343 |    -7.94 |     32.94 |    -27.24 |   -27.89 |         0.25 |          0.73 | FAIL      |
| 1-momentum-burst   | X0.8% raw tgt3xATR hold8h        | 15m  |    0.36 |      1.08 |            8 |   2261 |    -3.89 |     25.79 |    -87.87 |   -88.69 |    678 |    -6.91 |     25.37 |    -46.87 |   -46.97 |         0.25 |          0.88 | FAIL      |
| 1-momentum-burst   | X0.8% raw tgt3xATR hold24h       | 15m  |    0.36 |      1.08 |           24 |   1037 |    -5.1  |     26.52 |    -52.88 |   -57.61 |    343 |    -7.37 |     25.66 |    -25.28 |   -26.92 |         0.25 |          1.09 | FAIL      |
| 1-momentum-burst   | X1.2% champ tgt2xATR hold8h      | 15m  |    0.36 |      0.72 |            8 |   1066 |    -5.48 |     33.96 |    -58.39 |   -58.96 |    288 |    -7.61 |     33.68 |    -21.91 |   -24.08 |         0    |          0.33 | FAIL      |
| 1-momentum-burst   | X1.2% champ tgt2xATR hold24h     | 15m  |    0.36 |      0.72 |           24 |    626 |    -4.81 |     36.1  |    -30.08 |   -31.85 |    192 |    -7.11 |     34.38 |    -13.65 |   -15.03 |         0    |          0.39 | FAIL      |
| 1-momentum-burst   | X1.2% champ tgt3xATR hold8h      | 15m  |    0.36 |      1.08 |            8 |   1066 |    -4.91 |     27.2  |    -52.37 |   -53.26 |    288 |    -8.05 |     25.69 |    -23.19 |   -26.45 |         0.25 |          0.56 | FAIL      |
| 1-momentum-burst   | X1.2% champ tgt3xATR hold24h     | 15m  |    0.36 |      1.08 |           24 |    626 |    -3.47 |     28.75 |    -21.71 |   -26.56 |    192 |    -8.68 |     25    |    -16.67 |   -19.07 |         0.25 |          0.7  | FAIL      |
| 1-momentum-burst   | X1.2% raw tgt2xATR hold8h        | 15m  |    0.36 |      0.72 |            8 |   1562 |    -4.41 |     34.57 |    -68.84 |   -69.24 |    428 |    -6.29 |     34.81 |    -26.94 |   -31.04 |         0    |          0.36 | FAIL      |
| 1-momentum-burst   | X1.2% raw tgt2xATR hold24h       | 15m  |    0.36 |      0.72 |           24 |    814 |    -4.79 |     35.75 |    -39.02 |   -40.74 |    259 |    -5.81 |     35.52 |    -15.04 |   -17.19 |         0    |          0.43 | FAIL      |
| 1-momentum-burst   | X1.2% raw tgt3xATR hold8h        | 15m  |    0.36 |      1.08 |            8 |   1562 |    -3.75 |     28.04 |    -58.5  |   -60.2  |    428 |    -5.87 |     27.34 |    -25.12 |   -31.31 |         0.25 |          0.61 | FAIL      |
| 1-momentum-burst   | X1.2% raw tgt3xATR hold24h       | 15m  |    0.36 |      1.08 |           24 |    814 |    -2.74 |     29.24 |    -22.27 |   -29.21 |    259 |    -3.86 |     28.57 |    -10    |   -13.34 |         0.25 |          0.77 | FAIL      |
| 1-momentum-burst   | X1.8% champ tgt2xATR hold8h      | 15m  |    0.36 |      0.72 |            8 |    549 |    -9.11 |     30.05 |    -50.04 |   -50.14 |    144 |   -11.72 |     29.86 |    -16.87 |   -17.44 |         0    |          0.19 | FAIL      |
| 1-momentum-burst   | X1.8% champ tgt2xATR hold24h     | 15m  |    0.36 |      0.72 |           24 |    365 |    -6.55 |     34.52 |    -23.92 |   -23.92 |    108 |    -9.39 |     32.41 |    -10.14 |   -11.47 |         0    |          0.22 | FAIL      |
| 1-momentum-burst   | X1.8% champ tgt3xATR hold8h      | 15m  |    0.36 |      1.08 |            8 |    549 |    -8.61 |     23.68 |    -47.25 |   -47.55 |    144 |   -14.12 |     20.83 |    -20.33 |   -20.33 |         0    |          0.34 | FAIL      |
| 1-momentum-burst   | X1.8% champ tgt3xATR hold24h     | 15m  |    0.36 |      1.08 |           24 |    365 |    -5.31 |     27.4  |    -19.39 |   -19.39 |    108 |   -12.72 |     22.22 |    -13.73 |   -14.99 |         0    |          0.4  | FAIL      |
| 1-momentum-burst   | X1.8% raw tgt2xATR hold8h        | 15m  |    0.36 |      0.72 |            8 |    861 |    -7    |     31.71 |    -60.24 |   -60.24 |    217 |    -9.24 |     32.26 |    -20.05 |   -22.59 |         0    |          0.21 | FAIL      |
| 1-momentum-burst   | X1.8% raw tgt2xATR hold24h       | 15m  |    0.36 |      0.72 |           24 |    526 |    -4.7  |     36.31 |    -24.72 |   -24.72 |    150 |    -8.26 |     33.33 |    -12.4  |   -14.56 |         0    |          0.25 | FAIL      |
| 1-momentum-burst   | X1.8% raw tgt3xATR hold8h        | 15m  |    0.36 |      1.08 |            8 |    861 |    -5.38 |     26.6  |    -46.29 |   -46.7  |    217 |    -7.12 |     26.73 |    -15.45 |   -20.1  |         0    |          0.4  | FAIL      |
| 1-momentum-burst   | X1.8% raw tgt3xATR hold24h       | 15m  |    0.36 |      1.08 |           24 |    526 |    -0.71 |     30.8  |     -3.72 |   -15.2  |    150 |    -6.6  |     26.67 |     -9.9  |   -14.37 |         0    |          0.51 | FAIL      |
| 2-session-breakout | H4h long tgt1.5xrange            | 15m  |    1.49 |      2.24 |           20 |    882 |     4.26 |     44.56 |     37.57 |   -46.56 |    308 |    -5.51 |     44.16 |    -16.97 |   -28.82 |         7.75 |          9.87 | FAIL      |
| 2-session-breakout | H4h long tgt2.5xrange            | 15m  |    1.49 |      3.73 |           20 |    882 |     7.6  |     40.14 |     67.08 |   -57.91 |    308 |    -0.43 |     41.88 |     -1.33 |   -27.16 |        12    |         11.93 | FAIL      |
| 2-session-breakout | H4h short tgt1.5xrange           | 15m  |    1.49 |      2.24 |           20 |    846 |    -5.24 |     40.9  |    -44.32 |   -49.21 |    293 |    -4.5  |     44.37 |    -13.18 |   -31.23 |         8.75 |         10.2  | FAIL      |
| 2-session-breakout | H4h short tgt2.5xrange           | 15m  |    1.49 |      3.73 |           20 |    846 |    -5.35 |     36.17 |    -45.28 |   -52.85 |    293 |     0.56 |     41.3  |      1.63 |   -35.24 |        12    |         11.97 | FAIL      |
| 2-session-breakout | H8h long tgt1.5xrange            | 15m  |    1.7  |      2.97 |           16 |    775 |    11.06 |     44.9  |     85.73 |   -60.55 |    276 |    -3.31 |     43.12 |     -9.13 |   -35.87 |        10.75 |          9.89 | FAIL      |
| 2-session-breakout | H8h long tgt2.5xrange            | 15m  |    1.7  |      4.95 |           16 |    775 |    15.58 |     43.1  |    120.77 |   -64.86 |    276 |    -8.27 |     41.67 |    -22.83 |   -38.24 |        16    |         11.22 | FAIL      |
| 2-session-breakout | H8h short tgt1.5xrange           | 15m  |    1.7  |      2.97 |           16 |    729 |    -6.15 |     39.37 |    -44.8  |   -56.94 |    265 |   -10.23 |     42.26 |    -27.12 |   -44.74 |        11    |          9.95 | FAIL      |
| 2-session-breakout | H8h short tgt2.5xrange           | 15m  |    1.7  |      4.95 |           16 |    729 |    -6.3  |     37.31 |    -45.92 |   -52.33 |    265 |   -11.88 |     40.75 |    -31.49 |   -46    |        16    |         11.08 | FAIL      |
| 2-session-breakout | H4h long tgt1.5xrange            | 1h   |    1.49 |      2.24 |           20 |    813 |    -1.41 |     43.54 |    -11.47 |   -68.25 |    286 |    -7.58 |     42.31 |    -21.67 |   -33.19 |         8    |          9.85 | FAIL      |
| **2-session-breakout** | **H4h long tgt2.5xrange** | **1h** | **1.49** | **3.73** | **20** | **813** | **2.51** | **39.48** | **20.41** | **-76.63** | **286** | **1.08** | **39.86** | **3.09** | **-23.20** | **13** | **11.85** | **SURVIVOR** |
| 2-session-breakout | H4h short tgt1.5xrange           | 1h   |    1.49 |      2.24 |           20 |    779 |    -7.53 |     39.67 |    -58.68 |   -63.21 |    263 |    -4.72 |     44.87 |    -12.41 |   -30.24 |         8    |         10    | FAIL      |
| 2-session-breakout | H4h short tgt2.5xrange           | 1h   |    1.49 |      3.73 |           20 |    779 |    -7.1  |     35.17 |    -55.33 |   -60.51 |    263 |    -0.13 |     41.83 |     -0.34 |   -29.84 |        12    |         11.74 | FAIL      |
| 2-session-breakout | H8h long tgt1.5xrange            | 1h   |    1.7  |      2.97 |           16 |    715 |     3.44 |     42.38 |     24.6  |   -63.88 |    252 |    -8.09 |     43.25 |    -20.38 |   -40.2  |        11    |          9.95 | FAIL      |
| 2-session-breakout | H8h long tgt2.5xrange            | 1h   |    1.7  |      4.95 |           16 |    715 |     3.91 |     40.7  |     27.96 |   -69.54 |    252 |   -13.79 |     41.67 |    -34.76 |   -47.54 |        16    |         11.23 | FAIL      |
| 2-session-breakout | H8h short tgt1.5xrange           | 1h   |    1.7  |      2.97 |           16 |    660 |    -6.41 |     39.55 |    -42.31 |   -47.99 |    232 |    -5.62 |     44.83 |    -13.04 |   -30.99 |        12    |         10.05 | FAIL      |
| 2-session-breakout | H8h short tgt2.5xrange           | 1h   |    1.7  |      4.95 |           16 |    660 |    -6.56 |     37.58 |    -43.29 |   -50.96 |    232 |    -7.14 |     43.53 |    -16.57 |   -36.59 |        16    |         11.13 | FAIL      |
| 3-washout-scalp    | RSI3<5 stop1.0% tgt2.0% hold12h  | 1h   |    1    |      2    |           12 |    111 |   -29.94 |     31.53 |    -33.24 |   -33.24 |     33 |   -40.11 |     27.27 |    -13.24 |   -16.31 |         2.5  |          4.73 | FAIL      |
| 3-washout-scalp    | RSI3<5 stop1.0% tgt2.0% hold24h  | 1h   |    1    |      2    |           24 |    102 |   -27.86 |     29.41 |    -28.42 |   -30.55 |     32 |   -50.51 |     18.75 |    -16.16 |   -18.18 |         3    |          6.01 | FAIL      |
| 3-washout-scalp    | RSI3<5 stop1.0% tgt3.0% hold12h  | 1h   |    1    |      3    |           12 |    111 |   -31.9  |     29.73 |    -35.41 |   -35.41 |     33 |   -37.79 |     27.27 |    -12.47 |   -15.24 |         3    |          5.24 | FAIL      |
| 3-washout-scalp    | RSI3<5 stop1.0% tgt3.0% hold24h  | 1h   |    1    |      3    |           24 |    102 |   -30.9  |     25.49 |    -31.52 |   -33.96 |     32 |   -40.37 |     18.75 |    -12.92 |   -16.6  |         3    |          7.36 | FAIL      |
| 3-washout-scalp    | RSI3<5 stop1.5% tgt2.0% hold12h  | 1h   |    1.5  |      2    |           12 |    111 |   -39.03 |     36.94 |    -43.32 |   -43.96 |     33 |   -38.43 |     39.39 |    -12.68 |   -18.13 |         6    |          6.08 | FAIL      |
| 3-washout-scalp    | RSI3<5 stop1.5% tgt2.0% hold24h  | 1h   |    1.5  |      2    |           24 |    102 |   -39.57 |     35.29 |    -40.36 |   -43.5  |     32 |   -34.46 |     37.5  |    -11.03 |   -18.54 |         5.5  |          8.29 | FAIL      |
| 3-washout-scalp    | RSI3<5 stop1.5% tgt3.0% hold12h  | 1h   |    1.5  |      3    |           12 |    111 |   -42.91 |     34.23 |    -47.63 |   -48.1  |     33 |   -34.45 |     39.39 |    -11.37 |   -17.89 |         7    |          6.69 | FAIL      |
| 3-washout-scalp    | RSI3<5 stop1.5% tgt3.0% hold24h  | 1h   |    1.5  |      3    |           24 |    102 |   -45.93 |     29.41 |    -46.85 |   -48.79 |     32 |   -20.94 |     37.5  |     -6.7  |   -17.74 |         7    |          9.88 | FAIL      |
| 3-washout-scalp    | RSI3<10 stop1.0% tgt2.0% hold12h | 1h   |    1    |      2    |           12 |    270 |   -11.24 |     38.89 |    -30.34 |   -35.63 |     91 |    -5.43 |     39.56 |     -4.94 |   -11.68 |         3    |          5.03 | FAIL      |
| 3-washout-scalp    | RSI3<10 stop1.0% tgt2.0% hold24h | 1h   |    1    |      2    |           24 |    221 |   -12.2  |     33.94 |    -26.96 |   -30.72 |     78 |    -5.96 |     34.62 |     -4.65 |   -16.22 |         3    |          6.52 | FAIL      |
| 3-washout-scalp    | RSI3<10 stop1.0% tgt3.0% hold12h | 1h   |    1    |      3    |           12 |    270 |   -12.87 |     36.3  |    -34.74 |   -38.31 |     91 |   -10.45 |     35.16 |     -9.51 |   -18.58 |         5    |          5.81 | FAIL      |
| 3-washout-scalp    | RSI3<10 stop1.0% tgt3.0% hold24h | 1h   |    1    |      3    |           24 |    221 |   -12.5  |     29.41 |    -27.62 |   -33.85 |     78 |     1.43 |     32.05 |      1.11 |   -16.11 |         5    |          8.4  | FAIL      |
| 3-washout-scalp    | RSI3<10 stop1.5% tgt2.0% hold12h | 1h   |    1.5  |      2    |           12 |    270 |    -8.24 |     47.78 |    -22.24 |   -33.45 |     91 |    -5.12 |     48.35 |     -4.66 |   -13.51 |         6    |          6.45 | FAIL      |
| 3-washout-scalp    | RSI3<10 stop1.5% tgt2.0% hold24h | 1h   |    1.5  |      2    |           24 |    221 |    -8.51 |     44.8  |    -18.81 |   -30.07 |     78 |    -0.87 |     44.87 |     -0.67 |   -17.41 |         6    |          8.8  | FAIL      |
| 3-washout-scalp    | RSI3<10 stop1.5% tgt3.0% hold12h | 1h   |    1.5  |      3    |           12 |    270 |   -10.67 |     44.44 |    -28.82 |   -35.52 |     91 |    -7.76 |     46.15 |     -7.06 |   -16.7  |         9    |          7.41 | FAIL      |
| 3-washout-scalp    | RSI3<10 stop1.5% tgt3.0% hold24h | 1h   |    1.5  |      3    |           24 |    221 |    -9.61 |     38.91 |    -21.25 |   -36.16 |     78 |     6.79 |     43.59 |      5.3  |   -14.51 |         9    |         11.21 | FAIL      |
| 3-washout-scalp    | RSI3<5 stop1.0% tgt2.0% hold12h  | 15m  |    1    |      2    |           12 |    331 |   -10.59 |     40.18 |    -35.05 |   -44.6  |    118 |     2.71 |     49.15 |      3.2  |   -10.07 |         3.75 |          5.17 | FAIL      |
| 3-washout-scalp    | RSI3<5 stop1.0% tgt2.0% hold24h  | 15m  |    1    |      2    |           24 |    267 |   -13.43 |     33.33 |    -35.85 |   -43.22 |     94 |     1.43 |     40.43 |      1.34 |   -11.6  |         3.75 |          6.91 | FAIL      |
| 3-washout-scalp    | RSI3<5 stop1.0% tgt3.0% hold12h  | 15m  |    1    |      3    |           12 |    331 |    -8.79 |     38.07 |    -29.09 |   -37.58 |    118 |    10.27 |     48.31 |     12.12 |   -10.64 |         4.75 |          5.85 | FAIL      |
| 3-washout-scalp    | RSI3<5 stop1.0% tgt3.0% hold24h  | 15m  |    1    |      3    |           24 |    267 |    -8.92 |     30.71 |    -23.81 |   -31.82 |     94 |     2.35 |     36.17 |      2.21 |   -10.95 |         4.5  |          8.47 | FAIL      |
| 3-washout-scalp    | RSI3<5 stop1.5% tgt2.0% hold12h  | 15m  |    1.5  |      2    |           12 |    331 |    -5.93 |     50.45 |    -19.63 |   -34.6  |    118 |     3.76 |     56.78 |      4.43 |    -9.99 |         6.25 |          6.59 | FAIL      |
| 3-washout-scalp    | RSI3<5 stop1.5% tgt2.0% hold24h  | 15m  |    1.5  |      2    |           24 |    267 |    -9.76 |     44.19 |    -26.07 |   -31.74 |     94 |     7.48 |     50    |      7.03 |   -11.3  |         6    |          8.93 | FAIL      |
| 3-washout-scalp    | RSI3<5 stop1.5% tgt3.0% hold12h  | 15m  |    1.5  |      3    |           12 |    331 |    -3.01 |     48.04 |     -9.97 |   -30.43 |    118 |    12.69 |     56.78 |     14.97 |    -9.76 |         8.25 |          7.48 | FAIL      |
| 3-washout-scalp    | RSI3<5 stop1.5% tgt3.0% hold24h  | 15m  |    1.5  |      3    |           24 |    267 |    -3.89 |     40.82 |    -10.4  |   -31.36 |     94 |     9.33 |     45.74 |      8.77 |    -9.65 |         8.25 |         11.11 | FAIL      |
| 3-washout-scalp    | RSI3<10 stop1.0% tgt2.0% hold12h | 15m  |    1    |      2    |           12 |    641 |    -6.65 |     40.41 |    -42.66 |   -51.32 |    232 |     0.58 |     46.55 |      1.34 |   -19.56 |         4.75 |          5.77 | FAIL      |
| 3-washout-scalp    | RSI3<10 stop1.0% tgt2.0% hold24h | 15m  |    1    |      2    |           24 |    420 |    -7.9  |     35.95 |    -33.16 |   -40.07 |    154 |   -16.27 |     35.71 |    -25.05 |   -27.44 |         5    |          7.84 | FAIL      |
| 3-washout-scalp    | RSI3<10 stop1.0% tgt3.0% hold12h | 15m  |    1    |      3    |           12 |    641 |    -6.55 |     37.75 |    -41.97 |   -49.87 |    232 |     4.24 |     46.12 |      9.83 |   -17.55 |         6    |          6.5  | FAIL      |
| 3-washout-scalp    | RSI3<10 stop1.0% tgt3.0% hold24h | 15m  |    1    |      3    |           24 |    420 |   -10.61 |     30    |    -44.57 |   -49.94 |    154 |   -13.55 |     33.12 |    -20.86 |   -24.6  |         6.25 |          9.31 | FAIL      |
| 3-washout-scalp    | RSI3<10 stop1.5% tgt2.0% hold12h | 15m  |    1.5  |      2    |           12 |    641 |    -1.91 |     50.55 |    -12.26 |   -26.53 |    232 |    -1.58 |     51.29 |     -3.66 |   -21.09 |         7    |          7.05 | FAIL      |
| 3-washout-scalp    | RSI3<10 stop1.5% tgt2.0% hold24h | 15m  |    1.5  |      2    |           24 |    420 |     0.44 |     47.86 |      1.83 |   -26.04 |    154 |   -16.64 |     45.45 |    -25.62 |   -31.9  |         8    |         10.16 | FAIL      |
| 3-washout-scalp    | RSI3<10 stop1.5% tgt3.0% hold12h | 15m  |    1.5  |      3    |           12 |    641 |    -0.38 |     47.74 |     -2.45 |   -27.46 |    232 |     2.97 |     50.86 |      6.88 |   -18.87 |         9.75 |          7.92 | FAIL      |
| 3-washout-scalp    | RSI3<10 stop1.5% tgt3.0% hold24h | 15m  |    1.5  |      3    |           24 |    420 |    -0.81 |     41.67 |     -3.4  |   -26.65 |    154 |   -12.83 |     42.86 |    -19.76 |   -27.95 |        10    |         12.14 | FAIL      |
| 4-vwap-fade        | k=1.5xATR both-directions        | 1h   |    0.97 |      1.94 |           24 |    629 |    -7.94 |     36.57 |    -49.95 |   -50.88 |    215 |    -4.61 |     38.14 |     -9.9  |   -15.5  |         5    |          7.75 | FAIL      |
| 4-vwap-fade        | k=2.5xATR both-directions        | 1h   |    0.97 |      2.84 |           24 |    333 |   -14.91 |     29.43 |    -49.65 |   -54.2  |    115 |    -3.74 |     31.3  |     -4.3  |   -16.62 |         5    |          8.59 | FAIL      |

(Bold rows = the 3 SURVIVORs. Raw CSV: `step43_results_raw.csv`.)

## Plain-English summary

**Family 1 — Momentum burst: the only family with real, tradeable life.**
Two survivors, both 1h, both requiring the STRONGEST impulse tested (1.8%
close-to-close move) with the WIDEST target (3x ATR) and the FULL 24h
window — the 8h-hold and smaller-impulse variants all failed. That's a
consistent, sensible shape: a genuinely strong 1h impulse bar has real
follow-through, but it takes most of a day to travel 3x ATR, and a weaker
0.8-1.2% impulse is mostly noise that the champ filter and tight stop can't
rescue. The 15m variant (impulse over 4 bars) failed completely — see cost
floor below.

**Family 2 — Session breakout: one thin survivor, real drawdown risk.**
Only the 4h-window, long-only, 2.5x-range-target 1h config survives, with
the largest trade count of any config here (813 train / 286 val) but a
much thinner edge ($2.51 train / $1.08 val) and by far the worst
drawdowns in the whole grid (-76.6% train, -23.2% val, on the 1x equity
curve). The short mirror never worked in either window at either
timeframe — this regime has been dominated by upside breakouts, not
downside ones. The H8h-window long variants show huge TRAIN numbers
($11-15/trade, +85-121% return) that completely reverse to negative in
val — a clean overfitting tell that the train/val discipline correctly
caught and killed.

**Family 3 — Washout scalp: decisively FAILED, and that's the finding.**
This directly answers the brief's question — "does shortening the hold
from 48h to same-day kill the live dip-buy's edge?" — and the answer is
yes, badly. Every one of 32 configs failed, most with deeply negative
train expectancy (as bad as -$46/trade on RSI3<5, 1.5% stop). The proven
live shape needs the extra room the 48h hold gives it for the bounce to
develop; forcing an exit within 12-24h means most of these trades are
getting stopped out or timed out before the mean-reversion that makes the
live version work has a chance to play out.

**Family 4 — VWAP fade: FAILED at both k values.** Both the 1.5x-ATR and
2.5x-ATR overextension thresholds lost money in both windows. Not
promising as tested; if this family is revisited, splitting the combined
long+short signal into separate long-only and short-only runs would be
the first thing to try (this round tested them as one mirror-image
strategy per the brief's spec, so a directionally-asymmetric edge inside
it could be getting averaged away — flagging for the queue, not claiming
it exists).

## Cost-floor analysis for the 15m configs

Every single 15m config in this grid failed, and the reason is
structural, not a tuning miss. Measured directly from one representative
15m config (family 1, X1.8% champ, tgt3xATR, hold24h, train window):

- Realized cost per trade (fees + friction + funding, `execution="maker"`)
  averaged **$7.89**, or **~9.2 bps of notional** — about half the
  theoretical worst-case 18bps taker round-trip hurdle (`CostModel().
  round_trip_bps()`), because maker fills capture most trades.
- Backed-out average GROSS move per trade (before any cost) was only
  **~$2.57**.
- Net result: **-$5.31/trade**. The realized cost (~9bps) is roughly 3x
  the gross edge (~3bps) at 15m resolution — the edge simply does not
  exist at a size that clears even a maker-heavy cost structure.

This matches the resolution map already on record in RESEARCH_LOG.md
(2026-07-23 forensic autopsy): 4h edges are strong, 1h edges are moderate,
15m edges are consistently below the cost floor. Nothing in this round's
four NEW family shapes broke that pattern — it held for momentum-burst,
session-breakout, and washout-scalp alike at 15m.

## Top 3 candidates for the sealed-test look

Ranked by robustness, not just raw expectancy — reasoning follows each.

**#1 — Momentum burst, 1h, champ-gated, X=1.8%, target=3x ATR (0.81%
stop / 2.43% target), max_hold 24h.**
Train $7.20/trade (n=257, 30.7% win), val $8.74/trade (n=61, 34.4% win).
Train and val expectancy are close in magnitude (not a blowout gap that
screams overfit), the stop is the tightest of any survivor (0.81% —
extremely leverage-friendly, nowhere near the 1.7% ceiling), the trend
filter keeps it out of counter-trend chop, and the hold-time profile
(median 1h, mean 2.9h, p90 9h, hard cap 24h) is a clean day-trade. **This
is the strongest pick.**

**#2 — Momentum burst, 1h, UNCONDITIONED (no champ filter), same X=1.8% /
3x ATR / 24h geometry.**
Train $7.13/trade (n=389, 31.1% win), val $37.90/trade (n=100, 42.0%
win). Larger sample, same tight stop/target, but flag this clearly: val
expectancy is >5x the train expectancy, and this config's entries are a
STRICT SUPERSET of #1's (same impulse rule, minus the trend gate, so it
includes everything #1 trades plus additional counter-trend-filter
trades). The two are correlated hypotheses, not independent ones — worth
a test look because of the large sample and because it's cheap to check
alongside #1, but the 5x train-to-val jump is the kind of pattern that
sometimes means the val window happened to contain a few outsized winners
rather than a structurally stronger edge. Treat #1 as the "real" version
of this idea and #2 as a robustness check on it, not a separate strategy.

**#3 — Session breakout, 1h, first-4h UTC range, long only, target=2.5x
range height (1.49% stop / 3.73% target), max_hold 20h (24h minus the 4h
window).**
Train $2.51/trade (n=813, 39.5% win), val $1.08/trade (n=286, 39.9% win).
The edge is thin and the drawdown is the worst in the survivor set
(-76.6% train / -23.2% val on the 1x curve) — this is the weakest of the
three. It earns a test look anyway because it is a genuinely different
entry shape (no momentum/trend dependency, pure session-structure) with
by far the largest and most consistent sample size of anything in this
round, and a positive-both-windows result at that scale is not nothing.
Go in expecting a possible miss and treat the drawdown as disqualifying
for anything beyond a very small allocation even if test passes.

## Hold-time proof (these are genuinely day trades)

| candidate | median hold | mean hold | p90 hold | hard cap |
|---|---|---|---|---|
| #1 momentum burst champ | 1.0h | 2.92h | 9.0h | 24h |
| #2 momentum burst raw | 1.0h | 3.32h | 11.0h | 24h |
| #3 session breakout H4 long | 13.0h | 11.85h | 20.0h | 20h |

Momentum burst resolves FAST — most trades are decided (stopped or
targeted) within the first hour or two, with a long right tail running out
to the 24h cap. Session breakout runs closer to its cap by design (it's
meant to ride the day's move, not scalp it) but every single trade is
still flat well before the next UTC day begins, confirmed by the p90 and
max both sitting at or under the 20h engineered ceiling.

## Ambiguous calls made along the way

- **Family 1 "champ" gating on the short side**: the brief only specified
  "long when champ=1" explicitly; I extended the same logic symmetrically
  to shorts (short only when champ=0, i.e. not in the confirmed 4h
  uptrend) rather than leaving shorts always unconditioned. This is a
  reasonable reading but not the only one.
- **Family 2 max_hold approximation**: used a fixed `24h - window_hours`
  bars for every entry that day, exactly as the brief pre-authorized
  ("if the engine only supports fixed max_hold, use max_hold =
  24h-minus-range-window and state the approximation"). A real
  bars-to-midnight per entry would tighten this further (shrinking hold
  time, likely modestly hurting the marginal survivor's edge since it
  would sometimes cut trades earlier than 20h).
- **Family 2 range-height-based stop/target**: "stop = opposite side of
  the range" was read as the FULL range height (entry near one edge,
  opposite side is the whole range away), not half — this is the more
  conservative (wider, though still capped at 1.7%) reading.
- **Family 4 stop/target as train-only medians**: "exit at VWAP touch" and
  "1.2x ATR" are inherently per-trade dynamic; both were converted to
  fixed train-derived medians per this repo's established approximation
  pattern (same one step41 documents for its ATR-based stops). Both
  configs failed regardless of this simplification (both windows solidly
  negative), so the approximation isn't masking a live edge here.
- **All stops hard-capped at 1.7%**, not the looser 2.0% the mandate
  allows — every family's natural computed value already landed at or
  under this except family 2's H8h variant (1.70% exactly at the cap) and
  family 4 (0.97%, well under) — so the cap was rarely binding in
  practice; noted per-row in the stop% column above.
