# ROUND 93 -- the pro's pattern, on timeframes where it actually fires

R91 coded the owner's followed analyst's stated method (rally tags a prior significant swing high -> N consecutive red closes -> the interim minor swing low breaks on a close -> forecast a LOWER HIGH rather than continuation) as a mechanical state machine and found it fires 2-5 times in fifteen years on BTC DAILY -- unjudgeable, zero cells cleared the sample floor. The state machine is scale-free (everything is defined in bar counts, nothing is inherently daily). This round runs the IDENTICAL machine, unmodified, on 4h/1h/15m/5m, where the same structural shape should recur far more often.

## What was imported from R91 (not retyped)

`detect_pro_read_events` (the state machine itself, including all of its module-level constants K_MAJOR=10, K_MINOR=3, TOL_PCT=1.5%, INVALID_PCT=3%, SEARCH_WINDOW=25, FORECAST_HORIZON=90, referenced by closure), `run_cell` (the full per-cell pipeline: detect -> size stop/target from TRAIN-only median swing distance -> force-flat at MAX_HOLD_DAYS=45 bars -> score train/val -> verdict), plus `score`, `forecast_stats`, `mk_row`, `trades_per_year`, `verdict_for` -- all from `step91_pro_read`, all called unmodified. `split_points`, `day_trade_signal`, `hold_stats`, `MIN_TRAIN_TRADES`/`MIN_VAL_TRADES` from `step43_daytrade`. `swings`/`swing_stop_pct` from `step58_divergence_mtf` (via R91). `align_funding`/`fetch_funding_history` from `step11_round6`. `CostModel`/`run_backtest` from `backtest`.

**Consequence of reusing the machine unmodified:** MAX_HOLD_DAYS=45 and SEARCH_WINDOW=25 are BAR counts inside the imported code (named "_DAYS" because R91 only ran on daily bars). On 4h that is a 7.5-day hold cap; 1h, 1.9 days; 15m, 11.25 hours; 5m, 3.75 hours -- not recalibrated per timeframe, because recalibrating would no longer be the same machine. This happens to point the same direction as the owner's own stated preference for shorter holds at 15m and below. Likewise K_MAJOR=10/K_MINOR=3 are BAR windows, so "significant resistance" on 5m bars means a ~105-minute local structure, not a multi-week one -- the pattern's STRUCTURE is reused exactly; what counts as "significant" shrinks with the bar size, as it would for any technician moving down in timeframe.

## Data

- BTC 4h: 13863 bars 2020-03-25 -> 2026-07-22 | train ends 2024-01-10, val ends 2025-04-16 (test sealed)
- BTC 1h: 55493 bars 2020-03-25 -> 2026-07-24 | train ends 2024-01-11, val ends 2025-04-18 (test sealed)
- BTC 15m: 221972 bars 2020-03-25 -> 2026-07-24 | train ends 2024-01-11, val ends 2025-04-18 (test sealed)
- BTC 5m: 663999 bars 2020-03-30 -> 2026-07-23 | train ends 2024-01-12, val ends 2025-04-17 (test sealed)

All BTC and ETH data here is bybit USDT-perp (unlike R91's BTC daily, which used spot bitstamp with no funding history) -- REAL funding via align_funding applies to every cell in this round, both assets, all four timeframes.

## All BTC cells (4 timeframes x 3 N x 2 basis = 24 cells)

| tf   |   N_red | basis   |   n_events |   hit_rate% |   resolved_n |   stop% |   target% |   tr_n |   tr_exp |   va_n |   va_exp |   tr_gross_exp |   va_gross_exp |   cost_drag_bps | gross_verdict       |   trades/yr | verdict             |
|:-----|--------:|:--------|-----------:|------------:|-------------:|--------:|----------:|-------:|---------:|-------:|---------:|---------------:|---------------:|----------------:|:--------------------|------------:|:--------------------|
| 4h   |       2 | close   |         66 |      +80.30 |           66 |   +4.43 |     +2.10 |     37 |   +33.78 |     12 |   -18.10 |         +44.34 |          -8.79 |          +10.08 | FAIL                |       +9.68 | FAIL                |
| 4h   |       2 | wick    |         85 |      +81.18 |           85 |   +4.13 |     +2.18 |     44 |    +5.21 |     15 |    -2.42 |         +15.17 |          +7.04 |          +10.61 | SURVIVOR            |      +11.66 | FAIL                |
| 4h   |       3 | close   |         52 |      +88.46 |           52 |   +5.01 |     +2.04 |     32 |    +3.77 |     12 |   -96.01 |         +13.36 |         -87.18 |           +9.45 | FAIL                |       +8.70 | FAIL                |
| 4h   |       3 | wick    |         62 |      +87.10 |           62 |   +4.56 |     +2.12 |     36 |   +30.41 |     15 |   -63.40 |         +40.75 |         -54.47 |          +10.14 | FAIL                |      +10.08 | FAIL                |
| 4h   |       4 | close   |         35 |      +91.43 |           35 |   +5.34 |     +2.34 |     24 |   +33.65 |      9 |   -31.62 |         +43.73 |         -22.36 |           +9.59 | INSUFFICIENT-SAMPLE |       +6.52 | INSUFFICIENT-SAMPLE |
| 4h   |       4 | wick    |         38 |      +92.11 |           38 |   +5.27 |     +2.34 |     26 |    -1.13 |     10 |    -4.24 |          +8.45 |          +5.08 |           +9.67 | INSUFFICIENT-SAMPLE |       +7.11 | INSUFFICIENT-SAMPLE |
| 1h   |       2 | close   |        565 |      +82.65 |          565 |   +2.53 |     +0.80 |    241 |    -9.30 |     89 |   -12.30 |          -1.38 |          -3.84 |           +9.04 | FAIL                |      +65.16 | FAIL                |
| 1h   |       2 | wick    |        735 |      +78.78 |          735 |   +2.28 |     +1.03 |    278 |   -10.65 |     98 |   -15.85 |          -3.01 |          -7.45 |           +9.03 | FAIL                |      +74.25 | FAIL                |
| 1h   |       3 | close   |        403 |      +86.35 |          403 |   +2.85 |     +0.80 |    203 |    -7.79 |     75 |   -25.73 |          +0.60 |         -18.01 |           +8.48 | FAIL                |      +54.89 | FAIL                |
| 1h   |       3 | wick    |        485 |      +81.65 |          485 |   +2.57 |     +0.94 |    227 |    -9.34 |     86 |   -21.64 |          -1.15 |         -13.70 |           +8.93 | FAIL                |      +61.81 | FAIL                |
| 1h   |       4 | close   |        223 |      +89.69 |          223 |   +2.98 |     +0.82 |    131 |   -12.76 |     58 |   -10.41 |          -4.64 |          -1.73 |           +8.64 | FAIL                |      +37.32 | FAIL                |
| 1h   |       4 | wick    |        249 |      +86.75 |          249 |   +2.83 |     +1.00 |    143 |   -10.62 |     63 |   -14.65 |          -2.23 |          -5.99 |           +8.95 | FAIL                |      +40.68 | FAIL                |
| 15m  |       2 | close   |       4747 |      +87.28 |         4747 |   +1.68 |     +0.43 |   1415 |    -5.80 |    470 |    -6.11 |          -2.38 |          +2.03 |           +8.33 | FAIL                |     +372.21 | FAIL                |
| 15m  |       2 | wick    |       5688 |      +85.39 |         5688 |   +1.61 |     +0.47 |   1544 |    -5.46 |    516 |    -7.76 |          -2.18 |          -0.61 |           +8.32 | FAIL                |     +406.77 | FAIL                |
| 15m  |       3 | close   |       2909 |      +87.76 |         2909 |   +1.84 |     +0.46 |   1210 |    -6.64 |    397 |    -8.32 |          -3.26 |          -0.81 |           +7.80 | FAIL                |     +317.32 | FAIL                |
| 15m  |       3 | wick    |       3320 |      +85.69 |         3320 |   +1.76 |     +0.49 |   1304 |    -6.10 |    439 |    -9.21 |          -2.38 |          -2.32 |           +8.42 | FAIL                |     +344.17 | FAIL                |
| 15m  |       4 | close   |       1453 |      +89.33 |         1453 |   +2.00 |     +0.50 |    776 |    -8.21 |    282 |    -8.91 |          -3.27 |          -0.96 |           +9.14 | FAIL                |     +208.91 | FAIL                |
| 15m  |       4 | wick    |       1606 |      +87.61 |         1606 |   +1.90 |     +0.52 |    834 |    -8.09 |    302 |    -8.80 |          -3.48 |          -0.87 |           +8.92 | FAIL                |     +224.31 | FAIL                |
| 5m   |       2 | close   |      19723 |      +87.81 |        19723 |   +1.28 |     +0.27 |   4801 |    -2.08 |   1613 |    -5.20 |          -1.39 |          -1.70 |           +6.04 | FAIL                |    +1270.15 | FAIL                |
| 5m   |       2 | wick    |      22338 |      +86.17 |        22338 |   +1.24 |     +0.29 |   5085 |    -1.96 |   1740 |    -4.79 |          -1.38 |          -0.87 |           +6.33 | FAIL                |    +1351.54 | FAIL                |
| 5m   |       3 | close   |      11393 |      +87.57 |        11393 |   +1.32 |     +0.28 |   4082 |    -2.42 |   1419 |    -5.79 |          -1.31 |          -2.28 |           +6.49 | FAIL                |    +1089.35 | FAIL                |
| 5m   |       3 | wick    |      12393 |      +86.06 |        12393 |   +1.28 |     +0.30 |   4279 |    -2.31 |   1497 |    -5.28 |          -1.06 |          -0.99 |           +7.43 | FAIL                |    +1143.81 | FAIL                |
| 5m   |       4 | close   |       5750 |      +87.91 |         5750 |   +1.37 |     +0.29 |   2786 |    -3.38 |   1000 |    -6.15 |          -0.73 |          -0.27 |           +8.93 | FAIL                |     +749.73 | FAIL                |
| 5m   |       4 | wick    |       6128 |      +86.52 |         6128 |   +1.33 |     +0.31 |   2918 |    -3.24 |   1048 |    -6.35 |          -0.47 |          -1.00 |           +8.89 | FAIL                |     +785.38 | FAIL                |


## Closed-basis vs wick-basis -- the discipline priced in dollars, per timeframe

Same N, same resistance/interim/target levels, same costs -- the ONLY difference is whether the interim structure must break on a CLOSE (the analyst's stated rule) or merely get wicked through intrabar. Pooled train+val, per timeframe:

| tf   |   N_red |   closed_total_$ |   closed_n |   closed_exp |   wick_total_$ |   wick_n |   wick_exp |   closed_minus_wick_$ |
|:-----|--------:|-----------------:|-----------:|-------------:|---------------:|---------:|-----------:|----------------------:|
| 4h   |       2 |         +1032.70 |         49 |       +21.08 |        +193.03 |       59 |      +3.27 |               +839.67 |
| 4h   |       3 |         -1031.44 |         44 |       -23.44 |        +143.90 |       51 |      +2.82 |              -1175.34 |
| 4h   |       4 |          +523.10 |         33 |       +15.85 |         -71.77 |       36 |      -1.99 |               +594.87 |
| 1h   |       2 |         -3337.04 |        330 |       -10.11 |       -4512.90 |      376 |     -12.00 |              +1175.85 |
| 1h   |       3 |         -3512.15 |        278 |       -12.63 |       -3981.10 |      313 |     -12.72 |               +468.95 |
| 1h   |       4 |         -2275.69 |        189 |       -12.04 |       -2440.82 |      206 |     -11.85 |               +165.13 |
| 15m  |       2 |        -11076.90 |       1885 |        -5.88 |      -12429.63 |     2060 |      -6.03 |              +1352.73 |
| 15m  |       3 |        -11337.99 |       1607 |        -7.06 |      -11999.32 |     1743 |      -6.88 |               +661.33 |
| 15m  |       4 |         -8888.37 |       1058 |        -8.40 |       -9404.87 |     1136 |      -8.28 |               +516.50 |
| 5m   |       2 |        -18345.78 |       6414 |        -2.86 |      -18306.20 |     6825 |      -2.68 |                -39.58 |
| 5m   |       3 |        -18107.59 |       5501 |        -3.29 |      -17808.45 |     5776 |      -3.08 |               -299.14 |
| 5m   |       4 |        -15564.15 |       3786 |        -4.11 |      -16096.71 |     3966 |      -4.06 |               +532.57 |

**This is the single most transferable question in the analyst's method, and now there is enough sample to answer it directly per timeframe** -- see the per-timeframe verdicts below for the sign and size of `closed_minus_wick_$` at each N.


## Gross vs net -- where costs decide it

Every cell above also carries `gross_exp`/`net_exp`/`cost_drag_bps`: the same signal, same stop/target, run once at real costs (12bps RT via fee alone + real funding) and once at near-zero cost. Because spread/slippage are zero in both models, trade count and fill prices are identical between the two runs -- only the $ subtracted per trade differs, so `cost_drag_bps` is a clean, isolated measurement of what costs took out of the gross edge, and doubles as the per-trade edge (in bps) a cell needed to clear before it broke even. See the per-timeframe verdicts below for exactly which cells were gross-positive/net-negative (FAILS ON COSTS) versus negative even gross (no edge at all).


## Empirical chance baseline

BTC cells run: **24** (4 timeframes x 3 N x 2 basis). Per the standing rule (R83/R90: 2 winners out of 36 cells shipped live when ~0.7 were expected by luck, and it had to be ripped back out), every survivor below is reported against an EMPIRICAL chance baseline, not an assumed coin-flip: for each timeframe, the N=3/closed cell's exact trade count and stop%/target% were replayed on 30 draws of RANDOMLY TIMED entries (same cost model, same max-hold, same engine) and the fraction clearing the SURVIVOR bar (train+val both positive, both floors met) purely by luck was measured directly.

| tf   |   rep_n_events |   rep_stop% |   rep_target% |   empirical_survivor_rate |   cells_this_tf |   expected_by_chance |
|:-----|---------------:|------------:|--------------:|--------------------------:|----------------:|---------------------:|
| 4h   |             52 |      +5.006 |        +2.037 |                    +0.067 |               6 |               +0.400 |
| 1h   |            403 |      +2.855 |        +0.805 |                    +0.033 |               6 |               +0.200 |
| 15m  |           2909 |      +1.837 |        +0.464 |                    +0.000 |               6 |               +0.000 |
| 5m   |          11393 |      +1.315 |        +0.277 |                    +0.000 |               6 |               +0.000 |

**Total across all 24 BTC cells: 0 actual SURVIVOR(s) vs 0.60 expected by empirical chance.**


## Per-timeframe verdicts

### 4h

**FAILS ON COSTS** -- N=2, wick-basis is gross-POSITIVE on BOTH train ($+15.17/trade) AND val ($+7.04/trade) -- i.e. this cell would have been a SURVIVOR at zero cost -- but real costs (12bps RT + funding, 10.6bps measured drag/trade) flip it to train $+5.21 / val $-2.42 net. This cell needed a per-trade edge above 10.6bps to break even and did not clear it.

Median hold across all 4h cells with trades: 34.0h.

### 1h

**FAIL** -- best sampled cell by gross val expectancy (N=4, close-basis) is gross train $-4.64 / gross val $-1.73 per trade -- not both positive even before any costs, so this is not a costs problem: the pattern itself has no edge that generalizes to val at this timeframe, in the cells tested.

Median hold across all 1h cells with trades: 5.0h.

### 15m

**FAIL** -- best sampled cell by gross val expectancy (N=2, close-basis) is gross train $-2.38 / gross val $+2.03 per trade -- not both positive even before any costs, so this is not a costs problem: the pattern itself has no edge that generalizes to val at this timeframe, in the cells tested.

Median hold across all 15m cells with trades: 2.2h.

### 5m

**FAIL** -- best sampled cell by gross val expectancy (N=4, close-basis) is gross train $-0.73 / gross val $-0.27 per trade -- not both positive even before any costs, so this is not a costs problem: the pattern itself has no edge that generalizes to val at this timeframe, in the cells tested.

Median hold across all 5m cells with trades: 1.0h.


## Verdict summary

| timeframe | verdict |
|---|---|
| 4h | FAILS-ON-COSTS |
| 1h | FAIL |
| 15m | FAIL |
| 5m | FAIL |


## Plain bottom line

**No timeframe produced a rule that survives train, val, ETH transfer, AND costs.** The honest breakdown differs by timeframe, which matters more than a bare FAIL: 
**4h** had a genuine gross-positive cell (train AND val both positive before any fees/funding) that costs specifically killed -- see the FAILS-ON-COSTS cell above for the exact bps gap. **1h, 15m, 5m never had a gross edge to lose in the first place** -- train and val gross expectancy were not both positive on any swept cell, so costs are not what's stopping the pattern there; there is simply no edge in this specific mechanical translation at those timeframes. The one real cost casualty (4h, 10.6bps drag) is in the same range as this project's standing ~9-12bps cost floor for BTC (MARKET_PLAYBOOKS.md), and the pattern gets structurally denser (more trades/yr, thinner per-trade distances) at each step down in timeframe -- exactly the shape that floor has beaten before. The analyst's descriptive read of the tape being accurate (R91) remains a different skill from this mechanical translation of his method having positive expectancy at any timeframe tested so far, on either side of costs.
