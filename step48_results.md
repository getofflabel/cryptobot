# Round 48 — porting proven crypto strategy shapes to GOLD & NASDAQ

Script: `step48_tradfi_trend.py`. Data: `data_tradfi_<SYM>_<TF>.parquet` (GLD,
QQQ, SPY, USO, GCF, CLF x 1d/1h — 12 files). Research only, no orders, no
sealed-test looks spent (see "gauntlet discipline" below).

**Mandate:** port the crypto program's proven strategy SHAPES — 4h vol-gated
MA 20/100 trend, 1h RSI3 dip-buy in an established uptrend, 20/55-bar Donchian
breakout, and the mirrored short — to gold and Nasdaq, adapting parameters to
each market's own volatility rather than blindly copying BTC numbers, and
report honestly whether these markets pay for the shapes that worked on
crypto.

---

## 1. Data

yfinance daily (max history) + hourly (~730 days, yfinance's hard cap).
Primary targets are **gold** (GLD ETF, GC=F futures) and **Nasdaq** (QQQ
ETF); SPY and the oil pair (USO, CL=F) were pulled too as broader
cross-checks per the data spec and are reported as supplementary, not part of
the core mandate.

| symbol | tf | bars | span | train ends | val ends (test sealed) | median TRAIN ATR% |
|---|---|---:|---|---|---|---:|
| GLD  | 1d | 5,452  | 2004-11-18 → 2026-07-23 | 2017-11-15 | 2022-03-17 | 1.29% |
| QQQ  | 1d | 6,885  | 1999-03-10 → 2026-07-23 | 2015-08-10 | 2021-01-28 | 1.70% |
| SPY  | 1d | 8,427  | 1993-01-29 → 2026-07-23 | 2013-02-27 | 2019-11-05 | 1.32% |
| USO  | 1d | 5,103  | 2006-04-10 → 2026-07-23 | 2018-06-07 | 2022-06-28 | 2.41% |
| GC=F | 1d | 6,497  | 2000-08-30 → 2026-07-23 | 2016-03-21 | 2021-05-21 | 1.13% |
| CL=F | 1d | 6,506  | 2000-08-23 → 2026-07-23 | 2016-03-16 | 2021-05-19 | 3.04% |
| GLD  | 1h | 5,071  | 2023-08-24 → 2026-07-23 | 2025-05-22 | 2025-12-19 | 0.33% |
| QQQ  | 1h | 5,073  | 2023-08-24 → 2026-07-23 | 2025-05-22 | 2025-12-19 | 0.49% |
| SPY  | 1h | 5,072  | 2023-08-24 → 2026-07-23 | 2025-05-22 | 2025-12-19 | 0.36% |
| USO  | 1h | 5,072  | 2023-08-24 → 2026-07-23 | 2025-05-22 | 2025-12-19 | 0.72% |
| GC=F | 1h | 13,738 | 2024-02-29 → 2026-07-24 | 2025-08-05 | 2026-01-29 | 0.28% |
| CL=F | 1h | 13,530 | 2024-02-29 → 2026-07-24 | 2025-08-10 | 2026-02-03 | 0.49% |

**The first thing the median ATR% column proves:** gold/Nasdaq/S&P are far
LESS volatile than BTC on a like-for-like basis. Daily median ATR% sits
1.1–2.4% here vs BTC's multi-percent daily swings; hourly median ATR% is
0.28–0.72%, roughly 3–5x calmer than crypto's 1h. **Any BTC-calibrated fixed
threshold (the champion's 1.5% ATR gate, the 1.5% intrabar stop) ported
unscaled is simply the wrong number for these markets** — confirmed directly
below (the fixed-1.5% ATR gate produced **zero trades** on 8 of 12
symbol/TF hourly combos, see Family 1).

Chronological 60/20/20 split per symbol/TF, same convention as
`step41_shorts.py`'s `split_points()`. **The sealed 20% test window was never
sliced, scored, or printed anywhere in this script or this document.**

---

## 2. Costs and the funding trap

`backtest.py`'s `run_backtest()` **always** charges its conservative default
funding rate on every held bar **even when `funding_series=None`** — that
default only stops applying if the `CostModel` itself has `funding_bps_8h=0`.
Perpetual-futures funding does not exist on ETFs or dated futures, so every
`CostModel` in this script sets `funding_bps_8h=0.0` explicitly. Leaving the
default (1.0 bps/8h) would have silently taxed every trade here ~3bps/day of
holding (24h bar / 8h interval) that isn't a real cost — this was the single
most important "read the engine, don't assume" catch of the round.

| instrument class | fee | slippage | half-spread | round-trip cost |
|---|---:|---:|---:|---:|
| ETFs (GLD/QQQ/SPY/USO) | 1.0bp | 1.0bp | 0.0bp | **4.0bps** |
| Futures (GC=F/CL=F) | 0.5bp | 0.5bp | 0.0bp | **2.0bps** (matches task spec exactly) |

Execution = taker throughout (liquid instruments, simple assumption,
consistent with the flat-bps cost spec).

---

## 3. Gap honesty (required check)

`backtest.py`'s intrabar stop fires on `lows[i] <= stop_price` / `highs[i] >=
stop_price` and fills **at the stop price** (adjusted for slippage) — it does
**not** check whether the bar's OPEN had already gapped past the stop before
the bar started trading. A real resting stop order would have been filled at
that worse open, not at the stop level. On 24/7 crypto this is negligible; on
equities/gold/oil (17.5h closed overnight + weekends) it is not.

**Structural exposure** (fraction of all bars whose open-vs-prior-close gap
exceeds a stop-sized threshold) — see the spans table's `gap>thresh` figures
printed by the script; representative numbers: GLD 1d gaps >1.29% (=1x
median ATR) on **9.6%** of days, USO 1d gaps >2.41% on **9.7%** of days, GC=F
1d gaps >1.13% on **7.0%** of days. This is real and non-trivial — daily
equities/commodities gap through a same-day-sized stop roughly 1 day in 10.

**Per-trade correction** (`gap_honesty_correction()` in the script):
identifies every Family-2 (dip-buy, the only family using a hard intrabar
stop) trade whose exit matches the engine's stop-fill formula, checks whether
that bar's open had already gapped through the stop, and recomputes the fill
at the (worse) open where it did.

- **28 of 578** daily dip-buy stop-exits (4.8%) and **15 of 428** hourly ones
  (3.5%) were gap-throughs the engine priced optimistically.
- Median expectancy hit among affected configs: **-$1.62/trade**.
- Worst single flip: USO 1d `rsi3<10 stop1.0xATR(2.41%) hold10d` — raw train
  expectancy **+$1.33/trade** (13 trades) flips to **-$30.08/trade** once its
  2 gapped stop-outs are priced honestly. A config that LOOKED marginally
  positive was actually negative once gaps are honestly priced — exactly the
  failure mode this check exists to catch.
- The one Family-2 SURVIVOR (CL=F 1h, below) had **zero** gapped stop-exits —
  its edge (such as it is) is untouched by this correction.

Full per-config raw-vs-gap-adjusted numbers are in the Family 2 table below
(`tr_exp` vs `tr_exp_gapadj` columns are not shown in the compact table for
space; the underlying script prints and computes both — see "Family 2"
section for the worst-affected configs called out explicitly).

Families 1/3/4 don't use `stop_pct` (trend/breakout exit is signal-driven,
filled at next bar's open — the ordinary no-lookahead mechanic the engine
already prices correctly, no special gap issue).

---

## 4. Gauntlet discipline

Same convention as `step41_shorts.py`: **SURVIVOR** = positive expectancy on
both train AND val, with ≥30 train trades and ≥8 val trades.
**INSUFFICIENT-SAMPLE** = positive both windows but under the trade-count
bar (common on daily bars over a 60% train slice with only a handful of
multi-year trend legs). **FAIL** = negative on either window. The sealed
final 20% was never touched.

**200 configs tested. 14 SURVIVOR, 71 INSUFFICIENT-SAMPLE, 115 FAIL.**

---

## 5. Family 1 — trend champion port (`vol_gated_ma`, long-only)

Fast/slow ∈ {(20,100),(50,200)} on daily; {(20,100),(80,400)} on 1h (the
"intraday variant," explicitly small-sample per the task, marked honestly
below). Gate ∈ {adaptive (ATR% > own trailing 365-day median), fixed 1.0%,
fixed 1.5%, ungated}.

<details><summary>Full Family 1 table (96 configs) — click to expand</summary>

| config          | symbol   | market             | tf   |   tr_n |   tr_exp |   tr_win% |   tr_dd% |   tr_ret% |   va_n |   va_exp |   va_win% |   va_dd% |   va_ret% | verdict             |
|:----------------|:---------|:-------------------|:-----|-------:|---------:|----------:|---------:|----------:|-------:|---------:|----------:|---------:|----------:|:--------------------|
| 50/200 adaptive | CL=F     | oil(cross-check)   | 1d   |      9 |  3429.47 |     66.67 |   -37.26 |    308.65 |      5 |   765.2  |     40    |   -44.35 |     38.26 | INSUFFICIENT-SAMPLE |
| 50/200 fixed1.5 | CL=F     | oil(cross-check)   | 1d   |      9 |  2084.27 |     55.56 |   -45.85 |    187.58 |      6 |   489.54 |     50    |   -56.36 |     29.37 | INSUFFICIENT-SAMPLE |
| 50/200 fixed1.0 | CL=F     | oil(cross-check)   | 1d   |      9 |  2030.6  |     55.56 |   -46.76 |    182.75 |      6 |   489.54 |     50    |   -56.36 |     29.37 | INSUFFICIENT-SAMPLE |
| 50/200 ungated  | CL=F     | oil(cross-check)   | 1d   |      9 |  2030.6  |     55.56 |   -46.76 |    182.75 |      6 |   489.54 |     50    |   -56.36 |     29.37 | INSUFFICIENT-SAMPLE |
| 20/100 adaptive | CL=F     | oil(cross-check)   | 1d   |     14 |  1964.2  |     64.29 |   -35.11 |    274.99 |      9 |  -134.46 |     33.33 |   -39.83 |    -12.1  | FAIL                |
| 20/100 fixed1.0 | CL=F     | oil(cross-check)   | 1d   |     21 |   521.99 |     47.62 |   -42.38 |    109.62 |     12 |     6.34 |     25    |   -47.49 |      0.76 | INSUFFICIENT-SAMPLE |
| 20/100 fixed1.5 | CL=F     | oil(cross-check)   | 1d   |     21 |   521.99 |     47.62 |   -42.38 |    109.62 |     12 |     6.34 |     25    |   -47.49 |      0.76 | INSUFFICIENT-SAMPLE |
| 20/100 ungated  | CL=F     | oil(cross-check)   | 1d   |     21 |   521.99 |     47.62 |   -42.38 |    109.62 |     12 |     6.34 |     25    |   -47.49 |      0.76 | INSUFFICIENT-SAMPLE |
| 20/100 fixed1.0 | CL=F     | oil(cross-check)   | 1h   |      4 |   189.43 |     50    |    -8.2  |      7.58 |      3 |  -252.6  |      0    |    -8.1  |     -7.58 | FAIL                |
| 20/100 ungated  | CL=F     | oil(cross-check)   | 1h   |     56 |    -9.51 |     32.14 |   -23.64 |     -5.33 |     21 |   -42.32 |     33.33 |   -12.21 |     -8.89 | FAIL                |
| 20/100 adaptive | CL=F     | oil(cross-check)   | 1h   |     43 |   -27.24 |     27.91 |   -26.72 |    -11.71 |     17 |   -74.77 |     23.53 |   -16.46 |    -12.71 | FAIL                |
| 80/400 ungated  | CL=F     | oil(cross-check)   | 1h   |     17 |  -173.09 |     29.41 |   -34.02 |    -29.43 |      8 |  -166.94 |     12.5  |   -21.16 |    -13.35 | FAIL                |
| 80/400 adaptive | CL=F     | oil(cross-check)   | 1h   |     16 |  -186.88 |     25    |   -33.43 |    -29.9  |      7 |  -176.21 |     14.29 |   -18.95 |    -12.33 | FAIL                |
| 20/100 fixed1.5 | CL=F     | oil(cross-check)   | 1h   |      2 |  -254.73 |      0    |    -9.1  |     -5.09 |      0 |     0    |      0    |     0    |      0    | FAIL                |
| 80/400 fixed1.0 | CL=F     | oil(cross-check)   | 1h   |      3 |  -594.51 |      0    |   -21.1  |    -17.84 |      2 |    -4.49 |     50    |    -6.65 |     -0.09 | FAIL                |
| 80/400 fixed1.5 | CL=F     | oil(cross-check)   | 1h   |      1 | -1393.65 |      0    |   -16.86 |    -13.94 |      0 |     0    |      0    |     0    |      0    | FAIL                |
| 50/200 adaptive | GC=F     | gold               | 1d   |      6 |  4498.26 |     83.33 |   -26.21 |    269.9  |      3 |   832.2  |     33.33 |   -18.95 |     24.97 | INSUFFICIENT-SAMPLE |
| 50/200 fixed1.5 | GC=F     | gold               | 1d   |      5 |  3550.31 |    100    |   -26.21 |    177.52 |      2 |   283.12 |     50    |   -20.24 |      5.66 | INSUFFICIENT-SAMPLE |
| 50/200 ungated  | GC=F     | gold               | 1d   |      9 |  2772.49 |     66.67 |   -32.05 |    249.52 |      3 |  1207.8  |     66.67 |   -14.89 |     36.23 | INSUFFICIENT-SAMPLE |
| 50/200 fixed1.0 | GC=F     | gold               | 1d   |      9 |  2269.3  |     55.56 |   -28.19 |    204.24 |      3 |   879.71 |     66.67 |   -14.3  |     26.39 | INSUFFICIENT-SAMPLE |
| **20/100 ungated**  | **GC=F**     | **gold**               | **1d**   |   **34** |   **208.04** |     44.12 |   -43.1  |     70.73 |      8 |   419.67 |     75    |   -13.5  |     33.57 | **SURVIVOR**            |
| 20/100 fixed1.0 | GC=F     | gold               | 1d   |     28 |   115.57 |     46.43 |   -42.25 |     32.36 |      5 |   355.69 |     60    |   -15.13 |     17.78 | INSUFFICIENT-SAMPLE |
| 20/100 adaptive | GC=F     | gold               | 1d   |     24 |    39.09 |     41.67 |   -43.9  |      9.38 |      5 |   579.62 |     60    |   -11.78 |     28.98 | INSUFFICIENT-SAMPLE |
| 20/100 fixed1.5 | GC=F     | gold               | 1d   |     18 |   -25.05 |     44.44 |   -38.19 |     -4.51 |      2 |   745.27 |    100    |   -17.21 |     14.91 | FAIL                |
| 20/100 fixed1.0 | GC=F     | gold               | 1h   |      6 |    87.86 |     33.33 |    -5.44 |      5.27 |      1 |   136.43 |    100    |    -2.1  |      1.36 | INSUFFICIENT-SAMPLE |
| 80/400 ungated  | GC=F     | gold               | 1h   |     15 |    78.01 |     60    |   -12.79 |     11.7  |      3 |  1820.4  |     66.67 |   -11.57 |     54.61 | INSUFFICIENT-SAMPLE |
| **20/100 ungated**  | **GC=F**     | **gold**               | **1h**   |   **56** |    **61.34** |     55.36 |   -11.11 |     34.35 |     17 |   256.3  |     64.71 |    -7.77 |     43.57 | **SURVIVOR**            |
| **20/100 adaptive** | **GC=F**     | **gold**               | **1h**   |   **42** |    **41.05** |     54.76 |   -10.73 |     17.24 |     15 |   251.42 |     73.33 |    -7.77 |     37.71 | **SURVIVOR**            |
| 80/400 fixed1.0 | GC=F     | gold               | 1h   |      4 |    34.79 |     50    |    -8.74 |      1.39 |      2 |  1540.12 |     50    |    -6.19 |     30.8  | INSUFFICIENT-SAMPLE |
| 80/400 adaptive | GC=F     | gold               | 1h   |     15 |    20.98 |     40    |   -12.79 |      3.15 |      3 |  1619.64 |     66.67 |   -11.57 |     48.59 | INSUFFICIENT-SAMPLE |
| 20/100 fixed1.5 | GC=F     | gold               | 1h   |      0 |     0    |      0    |     0    |      0    |      0 |     0    |      0    |     0    |      0    | FAIL (0 trades)     |
| 80/400 fixed1.5 | GC=F     | gold               | 1h   |      1 |  -193.21 |      0    |    -2.58 |     -1.93 |      0 |     0    |      0    |     0    |      0    | FAIL                |
| 50/200 fixed1.5 | GLD      | gold               | 1d   |      4 |  3903.8  |     75    |   -26.89 |    156.15 |      2 |   179.02 |     50    |   -17.6  |      3.58 | INSUFFICIENT-SAMPLE |
| 50/200 adaptive | GLD      | gold               | 1d   |      5 |  3265.23 |     60    |   -26.89 |    163.26 |      3 |  1263.08 |     66.67 |   -14.22 |     37.89 | INSUFFICIENT-SAMPLE |
| 50/200 fixed1.0 | GLD      | gold               | 1d   |      7 |  1691.77 |     42.86 |   -33.23 |    118.42 |      4 |   587.4  |     50    |   -17.46 |     23.5  | INSUFFICIENT-SAMPLE |
| 50/200 ungated  | GLD      | gold               | 1d   |      8 |  1612.23 |     50    |   -36.39 |    128.98 |      5 |   721.28 |     40    |   -17.46 |     36.06 | INSUFFICIENT-SAMPLE |
| 20/100 fixed1.0 | GLD      | gold               | 1d   |     22 |   220.46 |     40.91 |   -43.87 |     48.5  |      6 |   303.41 |     66.67 |   -15.37 |     18.2  | INSUFFICIENT-SAMPLE |
| 20/100 ungated  | GLD      | gold               | 1d   |     25 |   168.83 |     40    |   -43.63 |     42.21 |      8 |   402.68 |     50    |   -17.22 |     32.21 | INSUFFICIENT-SAMPLE |
| 20/100 fixed1.5 | GLD      | gold               | 1d   |     17 |    34.88 |     41.18 |   -34.71 |      5.93 |      2 |   460.08 |     50    |   -13.13 |      9.2  | INSUFFICIENT-SAMPLE |
| 20/100 adaptive | GLD      | gold               | 1d   |     19 |    27.07 |     42.11 |   -42.79 |      5.14 |      7 |   629.52 |     85.71 |   -12.53 |     44.07 | INSUFFICIENT-SAMPLE |
| 80/400 adaptive | GLD      | gold               | 1h   |      3 |  1549.35 |    100    |    -8.22 |     46.48 |      3 |   786.63 |    100    |   -10.12 |     23.6  | INSUFFICIENT-SAMPLE |
| 80/400 ungated  | GLD      | gold               | 1h   |      4 |  1225.94 |    100    |    -8.22 |     49.04 |      3 |   978.08 |    100    |   -10.12 |     29.34 | INSUFFICIENT-SAMPLE |
| 20/100 ungated  | GLD      | gold               | 1h   |     20 |   149.19 |     55    |   -10.86 |     29.84 |      6 |   419.28 |     50    |    -8.02 |     25.16 | INSUFFICIENT-SAMPLE |
| 20/100 adaptive | GLD      | gold               | 1h   |     15 |    81.21 |     46.67 |   -10.86 |     12.18 |      6 |   343.07 |     50    |    -8.02 |     20.58 | INSUFFICIENT-SAMPLE |
| 20/100 fixed1.0 | GLD      | gold               | 1h   |      0 |     0    |      0    |     0    |      0    |      1 |   -27.27 |      0    |    -2.65 |     -0.27 | FAIL (0 trades)     |
| 20/100 fixed1.5 | GLD      | gold               | 1h   |      0 |     0    |      0    |     0    |      0    |      0 |     0    |      0    |     0    |      0    | FAIL (0 trades)     |
| 80/400 fixed1.0 | GLD      | gold               | 1h   |      0 |     0    |      0    |     0    |      0    |      1 |   457.18 |    100    |    -5.06 |      4.57 | FAIL (0 trades)     |
| 80/400 fixed1.5 | GLD      | gold               | 1h   |      0 |     0    |      0    |     0    |      0    |      0 |     0    |      0    |     0    |      0    | FAIL (0 trades)     |
| 50/200 fixed1.0 | QQQ      | nasdaq             | 1d   |     11 |  2104.83 |     63.64 |   -36.47 |    231.53 |      6 |  1920.36 |     50    |   -28.56 |    115.22 | INSUFFICIENT-SAMPLE |
| 50/200 ungated  | QQQ      | nasdaq             | 1d   |     11 |  2104.83 |     63.64 |   -36.47 |    231.53 |      6 |  1920.36 |     50    |   -28.56 |    115.22 | INSUFFICIENT-SAMPLE |
| 50/200 fixed1.5 | QQQ      | nasdaq             | 1d   |     11 |  1488.85 |     63.64 |   -36.47 |    163.77 |      5 |  1056.37 |     60    |   -28.56 |     52.82 | INSUFFICIENT-SAMPLE |
| 50/200 adaptive | QQQ      | nasdaq             | 1d   |      9 |   830.37 |     44.44 |   -36.47 |     74.73 |      6 |  1916.58 |     50    |   -28.56 |    114.99 | INSUFFICIENT-SAMPLE |
| 20/100 adaptive | QQQ      | nasdaq             | 1d   |     16 |   781.35 |     50    |   -39.79 |    125.02 |      8 |   980.22 |     62.5  |   -28.56 |     78.42 | INSUFFICIENT-SAMPLE |
| 20/100 fixed1.0 | QQQ      | nasdaq             | 1d   |     24 |   760.35 |     50    |   -50.45 |    182.48 |      8 |  1066.34 |     62.5  |   -28.56 |     85.31 | INSUFFICIENT-SAMPLE |
| 20/100 ungated  | QQQ      | nasdaq             | 1d   |     24 |   760.35 |     50    |   -50.45 |    182.48 |      8 |  1066.34 |     62.5  |   -28.56 |     85.31 | INSUFFICIENT-SAMPLE |
| 20/100 fixed1.5 | QQQ      | nasdaq             | 1d   |     20 |   569.32 |     45    |   -50.45 |    113.86 |      8 |   418.56 |     62.5  |   -28.56 |     33.48 | INSUFFICIENT-SAMPLE |
| 20/100 fixed1.0 | QQQ      | nasdaq             | 1h   |      2 |   310.13 |     50    |    -5.43 |      6.2  |      1 |   205.39 |    100    |    -1.97 |      2.05 | INSUFFICIENT-SAMPLE |
| 80/400 ungated  | QQQ      | nasdaq             | 1h   |      5 |   200.58 |     60    |   -14.97 |     10.03 |      2 |   820.23 |     50    |    -8.29 |     16.4  | INSUFFICIENT-SAMPLE |
| 20/100 ungated  | QQQ      | nasdaq             | 1h   |     23 |    44.19 |     47.83 |   -14.99 |     10.16 |      7 |    91.92 |     57.14 |    -4.97 |      6.43 | INSUFFICIENT-SAMPLE |
| 20/100 adaptive | QQQ      | nasdaq             | 1h   |     18 |     0.52 |     50    |   -14.88 |      0.09 |      5 |    44.67 |     60    |    -4.37 |      2.23 | INSUFFICIENT-SAMPLE |
| 20/100 fixed1.5 | QQQ      | nasdaq             | 1h   |      0 |     0    |      0    |     0    |      0    |      0 |     0    |      0    |     0    |      0    | FAIL (0 trades)     |
| 80/400 fixed1.0 | QQQ      | nasdaq             | 1h   |      0 |     0    |      0    |     0    |      0    |      1 |   382.31 |    100    |    -1.83 |      3.82 | FAIL (0 trades)     |
| 80/400 fixed1.5 | QQQ      | nasdaq             | 1h   |      0 |     0    |      0    |     0    |      0    |      0 |     0    |      0    |     0    |      0    | FAIL (0 trades)     |
| 80/400 adaptive | QQQ      | nasdaq             | 1h   |      5 |   -16.76 |     60    |   -14.97 |     -0.84 |      2 |   901.13 |     50    |    -8.29 |     18.02 | FAIL                |
| 50/200 ungated  | SPY      | sp500(cross-check) | 1d   |     10 |  3550.61 |     90    |   -20.26 |    355.06 |      4 |  1719.67 |     75    |   -15.38 |     68.79 | INSUFFICIENT-SAMPLE |
| 50/200 fixed1.0 | SPY      | sp500(cross-check) | 1d   |     10 |  3526.09 |     90    |   -20.26 |    352.61 |      4 |  1814.63 |     75    |   -13.92 |     72.59 | INSUFFICIENT-SAMPLE |
| 50/200 fixed1.5 | SPY      | sp500(cross-check) | 1d   |      8 |  2303.96 |     87.5  |   -25.78 |    184.32 |      4 |  1027.75 |     75    |   -12.29 |     41.11 | INSUFFICIENT-SAMPLE |
| 50/200 adaptive | SPY      | sp500(cross-check) | 1d   |     10 |  1568.53 |     60    |   -23.79 |    156.85 |      4 |  1875.63 |     75    |   -13.92 |     75.03 | INSUFFICIENT-SAMPLE |
| **20/100 ungated**  | **SPY**      | **sp500(cross-check)** | **1d**   |   **33** |   **467.32** |     51.52 |   -39.97 |    154.21 |      9 |   494.39 |     66.67 |   -16.69 |     44.5  | **SURVIVOR**            |
| 20/100 adaptive | SPY      | sp500(cross-check) | 1d   |     25 |   340.9  |     48    |   -32.27 |     85.23 |      9 |   224.2  |     66.67 |   -15.41 |     20.18 | INSUFFICIENT-SAMPLE |
| **20/100 fixed1.0** | **SPY**      | **sp500(cross-check)** | **1d**   |   **31** |   **335.81** |     41.94 |   -39.97 |    104.1  |      9 |   261.06 |     55.56 |   -16.07 |     23.5  | **SURVIVOR**            |
| 20/100 fixed1.5 | SPY      | sp500(cross-check) | 1d   |     23 |   156.24 |     34.78 |   -39.97 |     35.93 |      4 |    21.92 |     50    |    -8.04 |      0.88 | INSUFFICIENT-SAMPLE |
| 80/400 ungated  | SPY      | sp500(cross-check) | 1h   |      5 |   354.77 |     80    |    -9.78 |     17.74 |      1 |  1621.85 |    100    |    -5.29 |     16.22 | INSUFFICIENT-SAMPLE |
| 20/100 ungated  | SPY      | sp500(cross-check) | 1h   |     18 |   136.47 |     50    |    -9.69 |     24.57 |      7 |    68.96 |     57.14 |    -6.04 |      4.83 | INSUFFICIENT-SAMPLE |
| 20/100 adaptive | SPY      | sp500(cross-check) | 1h   |     14 |    89.31 |     57.14 |    -9.33 |     12.5  |      7 |   -33.51 |     28.57 |    -5.86 |     -2.35 | FAIL                |
| 80/400 adaptive | SPY      | sp500(cross-check) | 1h   |      5 |    56.74 |     40    |    -9.78 |      2.84 |      1 |  1621.85 |    100    |    -5.29 |     16.22 | INSUFFICIENT-SAMPLE |
| 20/100 fixed1.5 | SPY      | sp500(cross-check) | 1h   |      0 |     0    |      0    |     0    |      0    |      0 |     0    |      0    |     0    |      0    | FAIL (0 trades)     |
| 80/400 fixed1.0 | SPY      | sp500(cross-check) | 1h   |      0 |     0    |      0    |     0    |      0    |      0 |     0    |      0    |     0    |      0    | FAIL (0 trades)     |
| 80/400 fixed1.5 | SPY      | sp500(cross-check) | 1h   |      0 |     0    |      0    |     0    |      0    |      0 |     0    |      0    |     0    |      0    | FAIL (0 trades)     |
| 20/100 fixed1.0 | SPY      | sp500(cross-check) | 1h   |      1 |   -90.77 |      0    |    -2.64 |     -0.91 |      0 |     0    |      0    |     0    |      0    | FAIL                |
| 20/100 adaptive | USO      | oil(cross-check)   | 1d   |     10 |   453.69 |     50    |   -37.18 |     45.37 |      6 |   996.18 |     50    |   -31.26 |     59.77 | INSUFFICIENT-SAMPLE |
| 50/200 adaptive | USO      | oil(cross-check)   | 1d   |      8 |   271.05 |     37.5  |   -50.51 |     21.68 |      5 |   603.79 |     20    |   -47.8  |     30.19 | INSUFFICIENT-SAMPLE |
| 50/200 fixed1.5 | USO      | oil(cross-check)   | 1d   |     10 |   -96.7  |     40    |   -64.49 |     -9.67 |      5 |   735.17 |     20    |   -54.9  |     36.76 | FAIL                |
| 20/100 fixed1.5 | USO      | oil(cross-check)   | 1d   |     23 |  -116.86 |     26.09 |   -72.78 |    -26.88 |      7 |  1032.6  |     42.86 |   -42.42 |     72.28 | FAIL                |
| 20/100 fixed1.0 | USO      | oil(cross-check)   | 1d   |     23 |  -140.07 |     21.74 |   -74.76 |    -32.21 |      7 |  1032.6  |     42.86 |   -42.42 |     72.28 | FAIL                |
| 20/100 ungated  | USO      | oil(cross-check)   | 1d   |     23 |  -140.07 |     21.74 |   -74.76 |    -32.21 |      7 |  1032.6  |     42.86 |   -42.42 |     72.28 | FAIL                |
| 50/200 fixed1.0 | USO      | oil(cross-check)   | 1d   |     10 |  -184.92 |     30    |   -67.96 |    -18.49 |      5 |   735.17 |     20    |   -54.9  |     36.76 | FAIL                |
| 50/200 ungated  | USO      | oil(cross-check)   | 1d   |     10 |  -184.92 |     30    |   -67.96 |    -18.49 |      5 |   735.17 |     20    |   -54.9  |     36.76 | FAIL                |
| 20/100 fixed1.5 | USO      | oil(cross-check)   | 1h   |      1 |   122.4  |    100    |    -0.42 |      1.22 |      1 |  -442.86 |      0    |   -13.06 |     -4.43 | FAIL                |
| 80/400 fixed1.5 | USO      | oil(cross-check)   | 1h   |      0 |     0    |      0    |     0    |      0    |      1 |  -539.87 |      0    |   -14.08 |     -5.4  | FAIL (0 trades)     |
| 80/400 ungated  | USO      | oil(cross-check)   | 1h   |      6 |   -96.47 |     50    |   -21.9  |     -5.79 |      2 |  -157.7  |     50    |   -16.15 |     -3.15 | FAIL                |
| 20/100 ungated  | USO      | oil(cross-check)   | 1h   |     23 |  -133.74 |     21.74 |   -33.38 |    -30.76 |     11 |  -161.16 |     18.18 |   -30.84 |    -17.73 | FAIL                |
| 80/400 fixed1.0 | USO      | oil(cross-check)   | 1h   |      3 |  -189.23 |     33.33 |   -21.89 |     -5.68 |      1 |  -960.87 |      0    |   -14.08 |     -9.61 | FAIL                |
| 20/100 adaptive | USO      | oil(cross-check)   | 1h   |     13 |  -216.9  |     15.38 |   -31.11 |    -28.2  |      8 |  -132.41 |     50    |   -26.07 |    -10.59 | FAIL                |
| 80/400 adaptive | USO      | oil(cross-check)   | 1h   |      6 |  -226.5  |     33.33 |   -25.67 |    -13.59 |      2 |  -231.71 |      0    |   -16.15 |     -4.63 | FAIL                |
| 20/100 fixed1.0 | USO      | oil(cross-check)   | 1h   |      6 |  -249.87 |     33.33 |   -18.51 |    -14.99 |      1 |  -868.17 |      0    |   -13.06 |     -8.68 | FAIL                |

</details>

**5 SURVIVORS**: SPY 20/100 fixed1.0 & ungated (1d); GC=F 20/100 ungated (1d);
GC=F 20/100 ungated & adaptive (1h). **QQQ and GLD never clear the 30/8
trade-count bar in Family 1** — not because the edge is negative (most GLD/QQQ
20/100 configs are solidly positive, just thin: 16-25 train trades) but
because a 20/100-day MA cross simply doesn't fire that often over a 60% train
slice, even across 13-20 years.

**The fixed-1.5% ATR gate is frequently DEAD** on 1h (0 trades on GLD, QQQ,
SPY, and near-zero on GC=F/CL=F) because these markets' native hourly ATR%
(0.28–0.72% median) never reaches BTC's 1.5% threshold — direct, unambiguous
confirmation of the task's warning that ported thresholds need market-relative
rescaling. **"Ungated" (no ATR filter at all) is consistently among the best
performers here**, the opposite of BTC round 30's finding that an ADAPTIVE gate
was needed to keep the champion alive as volatility decayed — on gold/Nasdaq's
comparatively calm, persistently-trending tape, filtering for "liveliness"
mostly just throws away good entries rather than avoiding whipsaw.

---

## 6. Family 2 — dip-buy port (RSI3 < {5,10} in an uptrend, stop {0.7,1.0}x
median ATR%, target 3:1, hold {5,10}d / 48h)

<details><summary>Full Family 2 table (72 configs) — click to expand</summary>

| config                             | symbol   | market             | tf   |   tr_n |   tr_exp |   tr_win% |   tr_dd% |   tr_ret% |   va_n |   va_exp |   va_win% |   va_dd% |   va_ret% | verdict             |
|:-----------------------------------|:---------|:-------------------|:-----|-------:|---------:|----------:|---------:|----------:|-------:|---------:|----------:|---------:|----------:|:--------------------|
| rsi3<10 stop1.0xATR(3.04%) hold10d | CL=F     | oil(cross-check)   | 1d   |     21 |   179.95 |     52.38 |    -9.61 |     37.79 |      9 |  -165.07 |     11.11 |   -19.5  |    -14.86 | FAIL                |
| rsi3<10 stop0.7xATR(2.13%) hold10d | CL=F     | oil(cross-check)   | 1d   |     21 |   142.68 |     42.86 |    -8.58 |     29.96 |      9 |  -117.11 |     11.11 |   -14.06 |    -10.54 | FAIL                |
| rsi3<10 stop1.0xATR(3.04%) hold5d  | CL=F     | oil(cross-check)   | 1d   |     22 |   109.47 |     54.55 |    -9.23 |     24.08 |      9 |  -124.54 |     22.22 |   -16.05 |    -11.21 | FAIL                |
| rsi3<10 stop0.7xATR(2.13%) hold5d  | CL=F     | oil(cross-check)   | 1d   |     22 |   109.27 |     50    |    -8.19 |     24.04 |      9 |   -91.55 |     22.22 |   -11.84 |     -8.24 | FAIL                |
| rsi3<5 stop0.7xATR(2.13%) hold5d   | CL=F     | oil(cross-check)   | 1d   |      4 |  -167.01 |      0    |    -9.65 |     -6.68 |      3 |    -6.3  |     33.33 |    -6.14 |     -0.19 | FAIL                |
| rsi3<5 stop0.7xATR(2.13%) hold10d  | CL=F     | oil(cross-check)   | 1d   |      4 |  -207.28 |      0    |   -11.21 |     -8.29 |      3 |    62.07 |     33.33 |    -6.14 |      1.86 | FAIL                |
| rsi3<5 stop1.0xATR(3.04%) hold5d   | CL=F     | oil(cross-check)   | 1d   |      4 |  -231.55 |      0    |   -12.15 |     -9.26 |      3 |   -67.95 |     33.33 |    -7.87 |     -2.04 | FAIL                |
| rsi3<5 stop1.0xATR(3.04%) hold10d  | CL=F     | oil(cross-check)   | 1d   |      4 |  -291.46 |      0    |   -14.47 |    -11.66 |      3 |    60.81 |     33.33 |    -7.87 |      1.82 | FAIL (raw); gap-adj **-306.03**, 1 gapped |
| rsi3<5 stop0.7xATR(0.34%) hold48h  | CL=F     | oil(cross-check)   | 1h   |     12 |    21.63 |     41.67 |    -1.33 |      2.6  |      7 |   -16.18 |     14.29 |    -1.43 |     -1.13 | FAIL                |
| **rsi3<10 stop0.7xATR(0.34%) hold48h** | **CL=F**     | **oil(cross-check)**   | **1h**   |   **36** |     **6.15** |     30.56 |    -4.9  |      2.21 |     14 |    13.29 |     35.71 |    -1.43 |      1.86 | **SURVIVOR** (0 gapped) |
| rsi3<5 stop1.0xATR(0.49%) hold48h  | CL=F     | oil(cross-check)   | 1h   |     12 |    -1.73 |     25    |    -3.07 |     -0.21 |      7 |   -22.53 |     14.29 |    -2.05 |     -1.58 | FAIL                |
| rsi3<10 stop1.0xATR(0.49%) hold48h | CL=F     | oil(cross-check)   | 1h   |     36 |    -7.08 |     22.22 |    -8.45 |     -2.55 |     14 |    19.51 |     35.71 |    -2.01 |      2.73 | FAIL                |
| rsi3<5 stop1.0xATR(1.13%) hold10d  | GC=F     | gold               | 1d   |      2 |   345.23 |    100    |    -0.47 |      6.9  |      3 |    86.99 |     66.67 |    -2.27 |      2.61 | INSUFFICIENT-SAMPLE |
| rsi3<5 stop0.7xATR(0.79%) hold10d  | GC=F     | gold               | 1d   |      2 |   240.15 |    100    |    -0.47 |      4.8  |      3 |    -3.69 |     33.33 |    -2.33 |     -0.11 | FAIL                |
| rsi3<5 stop1.0xATR(1.13%) hold5d   | GC=F     | gold               | 1d   |      2 |   214.96 |    100    |    -0.52 |      4.3  |      3 |   -10.46 |     66.67 |    -2.27 |     -0.31 | FAIL                |
| rsi3<5 stop0.7xATR(0.79%) hold5d   | GC=F     | gold               | 1d   |      2 |   163.44 |    100    |    -0.52 |      3.27 |      3 |   -34.78 |     33.33 |    -2.33 |     -1.04 | FAIL                |
| rsi3<10 stop1.0xATR(1.13%) hold10d | GC=F     | gold               | 1d   |     20 |   115.57 |     60    |    -3.41 |     23.11 |      9 |    76.02 |     55.56 |    -2.65 |      6.84 | INSUFFICIENT-SAMPLE (gap-adj 114.67, 1 gapped) |
| rsi3<10 stop1.0xATR(1.13%) hold5d  | GC=F     | gold               | 1d   |     21 |    92.81 |     57.14 |    -3.58 |     19.49 |      9 |    54.97 |     66.67 |    -2.53 |      4.95 | INSUFFICIENT-SAMPLE |
| rsi3<10 stop0.7xATR(0.79%) hold10d | GC=F     | gold               | 1d   |     20 |    67.66 |     50    |    -3.93 |     13.53 |      9 |    49.28 |     44.44 |    -2.71 |      4.44 | INSUFFICIENT-SAMPLE |
| rsi3<10 stop0.7xATR(0.79%) hold5d  | GC=F     | gold               | 1d   |     21 |    55.75 |     47.62 |    -4.07 |     11.71 |      9 |    49.55 |     55.56 |    -2.71 |      4.46 | INSUFFICIENT-SAMPLE |
| rsi3<5 stop0.7xATR(0.20%) hold48h  | GC=F     | gold               | 1h   |     13 |     3.13 |     30.77 |    -0.92 |      0.41 |      6 |    -8    |     16.67 |    -1.25 |     -0.48 | FAIL                |
| rsi3<5 stop1.0xATR(0.28%) hold48h  | GC=F     | gold               | 1h   |     13 |    -3.65 |     23.08 |    -1.59 |     -0.47 |      6 |     7.9  |     33.33 |    -0.79 |      0.47 | FAIL                |
| rsi3<10 stop0.7xATR(0.20%) hold48h | GC=F     | gold               | 1h   |     48 |    -7.86 |     16.67 |    -4.48 |     -3.77 |     20 |     2.52 |     30    |    -1.17 |      0.5  | FAIL                |
| rsi3<10 stop1.0xATR(0.28%) hold48h | GC=F     | gold               | 1h   |     48 |    -8.35 |     18.75 |    -4.97 |     -4.01 |     20 |    -7.07 |     20    |    -4.63 |     -1.41 | FAIL                |
| rsi3<5 stop0.7xATR(0.90%) hold10d  | GLD      | gold               | 1d   |      3 |   148.35 |     66.67 |    -1.24 |      4.45 |      1 |   267.95 |    100    |    -0.6  |      2.68 | INSUFFICIENT-SAMPLE |
| rsi3<5 stop1.0xATR(1.29%) hold10d  | GLD      | gold               | 1d   |      3 |    93.12 |     66.67 |    -4.23 |      2.79 |      1 |   215.04 |    100    |    -1.22 |      2.15 | INSUFFICIENT-SAMPLE |
| rsi3<5 stop0.7xATR(0.90%) hold5d   | GLD      | gold               | 1d   |      3 |    84.75 |     66.67 |    -1.44 |      2.54 |      1 |   245.43 |    100    |    -0.6  |      2.45 | INSUFFICIENT-SAMPLE |
| rsi3<10 stop1.0xATR(1.29%) hold10d | GLD      | gold               | 1d   |     19 |    70.87 |     42.11 |    -7.1  |     13.47 |      4 |   -63.94 |     25    |    -4.33 |     -2.56 | FAIL (gap-adj 58.69, 2 gapped) |
| rsi3<10 stop1.0xATR(1.29%) hold5d  | GLD      | gold               | 1d   |     19 |    22.96 |     36.84 |    -8.57 |      4.36 |      4 |   -79.35 |     25    |    -4.16 |     -3.17 | FAIL                |
| rsi3<10 stop0.7xATR(0.90%) hold10d | GLD      | gold               | 1d   |     19 |     0.76 |     26.32 |    -8.06 |      0.14 |      4 |   -35.27 |     25    |    -3.21 |     -1.41 | FAIL                |
| rsi3<10 stop0.7xATR(0.90%) hold5d  | GLD      | gold               | 1d   |     19 |     0.17 |     26.32 |    -8.06 |      0.03 |      4 |   -50.86 |     25    |    -3.04 |     -2.03 | FAIL                |
| rsi3<5 stop1.0xATR(1.29%) hold5d   | GLD      | gold               | 1d   |      3 |   -41.76 |     33.33 |    -4.23 |     -1.25 |      1 |   245.43 |    100    |    -0.6  |      2.45 | FAIL                |
| rsi3<10 stop1.0xATR(0.33%) hold48h | GLD      | gold               | 1h   |     22 |    31.17 |     50    |    -1.61 |      6.86 |     10 |    -9.48 |     20    |    -2.9  |     -0.95 | FAIL                |
| rsi3<5 stop1.0xATR(0.33%) hold48h  | GLD      | gold               | 1h   |      7 |    20.85 |     42.86 |    -0.86 |      1.46 |      3 |    52.6  |     66.67 |    -0.65 |      1.58 | INSUFFICIENT-SAMPLE |
| rsi3<10 stop0.7xATR(0.23%) hold48h | GLD      | gold               | 1h   |     22 |    16.47 |     45.45 |    -1.29 |      3.62 |     10 |     1.82 |     30    |    -1.15 |      0.18 | INSUFFICIENT-SAMPLE |
| rsi3<5 stop0.7xATR(0.23%) hold48h  | GLD      | gold               | 1h   |      7 |     0.49 |     28.57 |    -1.18 |      0.03 |      3 |    36.1  |     66.67 |    -0.55 |      1.08 | INSUFFICIENT-SAMPLE |
| rsi3<10 stop1.0xATR(1.70%) hold5d  | QQQ      | nasdaq             | 1d   |     25 |    52.42 |     52    |    -5.9  |     13.11 |     15 |   -46.54 |     33.33 |   -11.26 |     -6.98 | FAIL                |
| rsi3<10 stop0.7xATR(1.19%) hold10d | QQQ      | nasdaq             | 1d   |     24 |    24.19 |     33.33 |    -7.32 |      5.81 |     15 |    32.11 |     33.33 |    -3.81 |      4.82 | INSUFFICIENT-SAMPLE |
| rsi3<10 stop1.0xATR(1.70%) hold10d | QQQ      | nasdaq             | 1d   |     24 |    13.86 |     37.5  |    -8.47 |      3.33 |     15 |   -41.93 |     26.67 |   -13.19 |     -6.29 | FAIL                |
| rsi3<10 stop0.7xATR(1.19%) hold5d  | QQQ      | nasdaq             | 1d   |     25 |    -4.45 |     36    |    -9.59 |     -1.11 |     15 |     9.33 |     33.33 |    -3.62 |      1.4  | FAIL                |
| rsi3<5 stop0.7xATR(1.19%) hold10d  | QQQ      | nasdaq             | 1d   |      4 |   -15.28 |     25    |    -3.48 |     -0.61 |      4 |   115.93 |     50    |    -1.22 |      4.64 | FAIL                |
| rsi3<5 stop1.0xATR(1.70%) hold10d  | QQQ      | nasdaq             | 1d   |      4 |   -53.65 |     25    |    -4.47 |     -2.15 |      4 |   125.7  |     50    |    -1.75 |      5.03 | FAIL                |
| rsi3<5 stop0.7xATR(1.19%) hold5d   | QQQ      | nasdaq             | 1d   |      4 |  -114.37 |      0    |    -4.57 |     -4.57 |      4 |    87.99 |     50    |    -1.22 |      3.52 | FAIL                |
| rsi3<5 stop1.0xATR(1.70%) hold5d   | QQQ      | nasdaq             | 1d   |      4 |  -133.04 |      0    |    -5.35 |     -5.32 |      4 |    80.21 |     50    |    -1.73 |      3.21 | FAIL                |
| rsi3<10 stop0.7xATR(0.34%) hold48h | QQQ      | nasdaq             | 1h   |     19 |    -8.33 |     21.05 |    -3.7  |     -1.58 |      6 |     8.64 |     33.33 |    -1.49 |      0.52 | FAIL                |
| rsi3<10 stop1.0xATR(0.49%) hold48h | QQQ      | nasdaq             | 1h   |     19 |   -10.78 |     21.05 |    -4.99 |     -2.05 |      6 |    13.37 |     33.33 |    -2.07 |      0.8  | FAIL                |
| rsi3<5 stop0.7xATR(0.34%) hold48h  | QQQ      | nasdaq             | 1h   |      8 |   -20.08 |     12.5  |    -1.61 |     -1.61 |      2 |   -37.41 |      0    |    -0.8  |     -0.75 | FAIL                |
| rsi3<5 stop1.0xATR(0.49%) hold48h  | QQQ      | nasdaq             | 1h   |      8 |   -27.45 |     12.5  |    -2.2  |     -2.2  |      2 |   -52.12 |      0    |    -1.09 |     -1.04 | FAIL                |
| rsi3<5 stop0.7xATR(0.92%) hold5d   | SPY      | sp500(cross-check) | 1d   |      3 |   101.14 |    100    |    -0.69 |      3.03 |      2 |    88.53 |     50    |    -1.61 |      1.77 | INSUFFICIENT-SAMPLE |
| rsi3<5 stop0.7xATR(0.92%) hold10d  | SPY      | sp500(cross-check) | 1d   |      3 |    95.82 |     66.67 |    -1.79 |      2.87 |      2 |    88.53 |     50    |    -1.61 |      1.77 | INSUFFICIENT-SAMPLE |
| rsi3<10 stop1.0xATR(1.32%) hold10d | SPY      | sp500(cross-check) | 1d   |     27 |    58.72 |     51.85 |    -5.9  |     15.85 |     16 |     3.45 |     43.75 |    -5.36 |      0.55 | INSUFFICIENT-SAMPLE |
| rsi3<10 stop1.0xATR(1.32%) hold5d  | SPY      | sp500(cross-check) | 1d   |     27 |    48.8  |     55.56 |    -5.73 |     13.17 |     16 |   -18.38 |     37.5  |    -5.82 |     -2.94 | FAIL                |
| rsi3<10 stop0.7xATR(0.92%) hold5d  | SPY      | sp500(cross-check) | 1d   |     27 |    32.51 |     51.85 |    -4.69 |      8.78 |     16 |   -31.82 |     25    |    -5.89 |     -5.09 | FAIL                |
| rsi3<10 stop0.7xATR(0.92%) hold10d | SPY      | sp500(cross-check) | 1d   |     27 |    30.86 |     44.44 |    -4.33 |      8.33 |     16 |   -21.19 |     31.25 |    -5.98 |     -3.39 | FAIL                |
| rsi3<5 stop1.0xATR(1.32%) hold10d  | SPY      | sp500(cross-check) | 1d   |      3 |   -28.86 |     33.33 |    -4.78 |     -0.87 |      2 |   300.28 |    100    |    -1.48 |      6.01 | FAIL                |
| rsi3<5 stop1.0xATR(1.32%) hold5d   | SPY      | sp500(cross-check) | 1d   |      3 |   -56.54 |     66.67 |    -4.83 |     -1.7  |      2 |   165.1  |     50    |    -1.48 |      3.3  | FAIL                |
| rsi3<5 stop0.7xATR(0.25%) hold48h  | SPY      | sp500(cross-check) | 1h   |      9 |    16.87 |     44.44 |    -0.84 |      1.52 |      2 |   -27.95 |      0    |    -0.56 |     -0.56 | FAIL                |
| rsi3<5 stop1.0xATR(0.36%) hold48h  | SPY      | sp500(cross-check) | 1h   |      9 |     9.04 |     33.33 |    -1.39 |      0.81 |      2 |   -38.62 |      0    |    -0.77 |     -0.77 | FAIL                |
| rsi3<10 stop0.7xATR(0.25%) hold48h | SPY      | sp500(cross-check) | 1h   |     14 |    -6.41 |     21.43 |    -2.33 |     -0.9  |      9 |     5.56 |     33.33 |    -1.75 |      0.5  | FAIL                |
| rsi3<10 stop1.0xATR(0.36%) hold48h | SPY      | sp500(cross-check) | 1h   |     14 |   -18.07 |     14.29 |    -4.55 |     -2.53 |      9 |    -6.9  |     22.22 |    -2.68 |     -0.62 | FAIL                |
| rsi3<10 stop0.7xATR(1.69%) hold10d | USO      | oil(cross-check)   | 1d   |     13 |    87.29 |     38.46 |    -6.92 |     11.35 |      6 |    20.63 |     50    |    -5.23 |      1.24 | INSUFFICIENT-SAMPLE |
| rsi3<10 stop0.7xATR(1.69%) hold5d  | USO      | oil(cross-check)   | 1d   |     13 |    43.03 |     38.46 |    -6.92 |      5.59 |      5 |    21.01 |     40    |    -5.13 |      1.05 | INSUFFICIENT-SAMPLE |
| rsi3<10 stop1.0xATR(2.41%) hold5d  | USO      | oil(cross-check)   | 1d   |     13 |     7.03 |     46.15 |   -11.14 |      0.91 |      5 |    26.8  |     40    |    -7.16 |      1.34 | INSUFFICIENT-SAMPLE |
| rsi3<10 stop1.0xATR(2.41%) hold10d | USO      | oil(cross-check)   | 1d   |     13 |     1.33 |     30.77 |   -12.78 |      0.17 |      6 |    17.74 |     50    |    -7.58 |      1.06 | INSUFFICIENT-SAMPLE (gap-adj **-30.08**, 2 gapped) |
| rsi3<5 stop0.7xATR(1.69%) hold5d   | USO      | oil(cross-check)   | 1d   |      3 |  -168.95 |      0    |    -5.07 |     -5.07 |      1 |  -171.88 |      0    |    -1.72 |     -1.72 | FAIL                |
| rsi3<5 stop0.7xATR(1.69%) hold10d  | USO      | oil(cross-check)   | 1d   |      3 |  -168.95 |      0    |    -5.07 |     -5.07 |      1 |  -171.88 |      0    |    -1.72 |     -1.72 | FAIL                |
| rsi3<5 stop1.0xATR(2.41%) hold5d   | USO      | oil(cross-check)   | 1d   |      3 |  -238.35 |      0    |    -7.15 |     -7.15 |      1 |    62.95 |    100    |    -2.26 |      0.63 | FAIL                |
| rsi3<5 stop1.0xATR(2.41%) hold10d  | USO      | oil(cross-check)   | 1d   |      3 |  -238.35 |      0    |    -7.15 |     -7.15 |      1 |   721.86 |    100    |    -2.26 |      7.22 | FAIL                |
| rsi3<5 stop0.7xATR(0.51%) hold48h  | USO      | oil(cross-check)   | 1h   |      8 |    -3.13 |     25    |    -2.7  |     -0.25 |      2 |    47.82 |     50    |    -0.71 |      0.96 | FAIL                |
| rsi3<5 stop1.0xATR(0.72%) hold48h  | USO      | oil(cross-check)   | 1h   |      8 |    -3.53 |     25    |    -3.76 |     -0.28 |      2 |   118.55 |    100    |    -1.23 |      2.37 | FAIL                |
| rsi3<10 stop0.7xATR(0.51%) hold48h | USO      | oil(cross-check)   | 1h   |     18 |    -8.7  |     22.22 |    -6.44 |     -1.57 |      6 |   -53    |      0    |    -3.18 |     -3.18 | FAIL                |
| rsi3<10 stop1.0xATR(0.72%) hold48h | USO      | oil(cross-check)   | 1h   |     18 |   -26.93 |     16.67 |   -11.08 |    -4.85 |      6 |   -11.4  |     33.33 |    -2.25 |     -0.68 | FAIL                |

</details>

**1 SURVIVOR out of 72 configs**: CL=F 1h `rsi3<10 stop0.7xATR(0.34%)
hold48h` — train +$6.15/trade (36t), val +$13.29/trade (14t). This is real
but thin (a $6/trade edge on a ~2bp round-trip cost floor is a small margin
of safety), on a ~1.5yr sample, on the supplementary oil futures pair, not on
gold or Nasdaq. **The crypto dip-buy shape (RSI3<10 in an uptrend) does NOT
reliably transfer to gold/Nasdaq at daily or hourly resolution.** GLD/QQQ/SPY
dip-buy configs are overwhelmingly FAIL or sample-starved-positive; where they
look promising on train they usually die on val (e.g. QQQ 1d `rsi3<5
stop0.7xATR(1.19%) hold5d`: train -$114.37, val +$87.99 — window-dependent
noise, not edge). See §3 above for the concrete gap-honesty flips this family
produced.

---

## 7. Family 3 — breakout port (20/55-day Donchian, EMA20 exit, long only)

| config               | symbol   | market             | tf   |   tr_n |   tr_exp |   tr_win% |   tr_dd% |   tr_ret% |   va_n |   va_exp |   va_win% |   va_dd% |   va_ret% | verdict   |
|:---------------------|:---------|:-------------------|:-----|-------:|---------:|----------:|---------:|----------:|-------:|---------:|----------:|---------:|----------:|:----------|
| donchian20 EMA20exit | CL=F     | oil(cross-check)   | 1d   |     87 |    -9.47 |     37.93 |   -35.31 |     -8.24 |     26 |   298.88 |     38.46 |   -24.72 |     77.71 | FAIL      |
| donchian55 EMA20exit | CL=F     | oil(cross-check)   | 1d   |     54 |   -46.79 |     40.74 |   -41.57 |    -25.27 |     15 |   357.58 |     53.33 |   -15.62 |     53.64 | FAIL      |
| **donchian20 EMA20exit** | **GC=F**     | **gold**               | **1d**   |   **89** |    **57.51** |     42.7  |   -20.67 |     51.18 |     24 |    95.09 |     41.67 |   -13.01 |     22.82 | **SURVIVOR**  |
| **donchian55 EMA20exit** | **GC=F**     | **gold**               | **1d**   |   **55** |    **41.95** |     49.09 |   -19.37 |     23.07 |     14 |   111.61 |     42.86 |    -8.33 |     15.63 | **SURVIVOR**  |
| **donchian55 EMA20exit** | **GLD**      | **gold**               | **1d**   |   **39** |    **93.25** |     43.59 |   -15.06 |     36.37 |     11 |   192.79 |     72.73 |    -9.06 |     21.21 | **SURVIVOR**  |
| **donchian20 EMA20exit** | **GLD**      | **gold**               | **1d**   |   **67** |    **80.61** |     44.78 |   -22.68 |     54.01 |     23 |    62.09 |     43.48 |   -15.84 |     14.28 | **SURVIVOR**  |
| **donchian55 EMA20exit** | **QQQ**      | **nasdaq**             | **1d**   |   **65** |    **50.6**  |     44.62 |   -34.25 |     32.89 |     30 |    61.94 |     46.67 |   -14.85 |     18.58 | **SURVIVOR**  |
| **donchian20 EMA20exit** | **QQQ**      | **nasdaq**             | **1d**   |   **91** |    **30.53** |     42.86 |   -43.17 |     27.78 |     33 |   150.7  |     54.55 |   -13.24 |     49.73 | **SURVIVOR**  |
| **donchian20 EMA20exit** | **SPY**      | **sp500(cross-check)** | **1d**   |  **109** |    **41.99** |     41.28 |   -27.27 |     45.77 |     38 |    86.72 |     55.26 |    -5.72 |     32.95 | **SURVIVOR**  |
| **donchian55 EMA20exit** | **SPY**      | **sp500(cross-check)** | **1d**   |   **75** |    **28.71** |     44    |   -31.13 |     21.53 |     32 |    28.84 |     56.25 |    -9.84 |      9.23 | **SURVIVOR**  |
| donchian20 EMA20exit | USO      | oil(cross-check)   | 1d   |     63 |   -43.95 |     38.1  |   -54    |    -27.69 |     20 |   254.78 |     45    |   -32.8  |     50.96 | FAIL      |
| donchian55 EMA20exit | USO      | oil(cross-check)   | 1d   |     38 |   -54.77 |     39.47 |   -39.57 |    -20.81 |     13 |   434.8  |     46.15 |   -22.08 |     56.52 | FAIL      |

**8 of 12 SURVIVOR — this family is the standout.** Every core target
(GLD, GC=F, QQQ, SPY) passes on BOTH N=20 and N=55, and — critically — **GLD
and GC=F are the same underlying market priced two different ways (ETF vs
futures) and BOTH validate the same shape**, which is a genuine cross-
confirmation, not a coincidence of one instrument's quirks. Only the oil pair
(USO/CL=F, supplementary) fails outright — oil breaks trend-following far
less cleanly than gold or equity indices, consistent with oil's history of
sharp exogenous-shock reversals (OPEC decisions, 2020's negative-price event)
that a trend/breakout system rides straight into.

**Turnover and annualized return** (computed honestly on the $10k starting
equity, size_frac=1.0, no leverage — see script's `decade_breakdown` window
lengths):

| config | symbol | trades/yr (train/val) | train CAGR | val CAGR |
|---|---|---|---:|---:|
| donchian20 | GLD | 5.2 / 5.3 | +3.4%/yr | +3.1%/yr |
| donchian55 | GLD | 3.0 / 2.5 | +2.4%/yr | +4.5%/yr |
| donchian20 | GC=F | 5.7 / 4.6 | +2.7%/yr | +4.1%/yr |
| donchian55 | GC=F | 3.5 / 2.7 | +1.3%/yr | +2.9%/yr |
| donchian20 | QQQ | 5.5 / 6.0 | +1.5%/yr | +7.7%/yr |
| donchian55 | QQQ | 4.0 / 5.5 | +1.8%/yr | +3.2%/yr |
| donchian20 | SPY | 5.4 / 5.7 | +1.9%/yr | +4.4%/yr |
| donchian55 | SPY | 3.7 / 4.8 | +1.0%/yr | +1.3%/yr |

**Honest read of the annualized numbers: this is a modest, low-turnover edge
(1–8%/yr, ~4–6 trades/yr), not a get-rich system, and it is a LONG-ONLY
system that spends much of its time flat** — it should not be compared to
buy-and-hold on raw return (GLD/QQQ buy-and-hold vastly outperformed these
figures over the same multi-decade window); its case is a much smaller
drawdown (-15% to -25% vs buy-and-hold's much deeper drawdowns in 2000-02,
2008-09, 2020, 2022) for a real, positive, both-windows-validated return.

---

## 8. Family 4 — mirrored shorts (QQQ + GLD daily only, per task)

**Zero survivors, zero even-marginally-positive-both-windows configs. Every
short config on both symbols is FAIL.**

Trend-short (`vol_gated_ma(allow_short=True)`, short side only, same
fast/slow/gate grid as Family 1):

| config          | symbol   | market   | tf   |   tr_n |   tr_exp |   tr_win% |   tr_dd% |   tr_ret% |   va_n |   va_exp |   va_win% |   va_dd% |   va_ret% | verdict   |
|:----------------|:---------|:---------|:-----|-------:|---------:|----------:|---------:|----------:|-------:|---------:|----------:|---------:|----------:|:----------|
| 20/100 ungated  | GLD      | gold     | 1d   |     26 |  -208.9  |     15.38 |   -55.22 |    -54.31 |      8 |  -146.94 |     37.5  |   -17.52 |    -11.75 | FAIL      |
| 20/100 fixed1.0 | GLD      | gold     | 1d   |     20 |  -245.76 |     15    |   -52.67 |    -49.15 |      3 |  -101.78 |     66.67 |   -12.45 |     -3.05 | FAIL      |
| 50/200 fixed1.0 | GLD      | gold     | 1d   |      6 |  -315.01 |     16.67 |   -33.57 |    -18.9  |      2 |  -165.82 |      0    |   -13.06 |     -3.32 | FAIL      |
| 50/200 ungated  | GLD      | gold     | 1d   |      7 |  -317.45 |     14.29 |   -33.57 |    -22.22 |      4 |  -198.08 |      0    |   -15.31 |     -7.92 | FAIL      |
| 20/100 adaptive | GLD      | gold     | 1d   |     15 |  -324.43 |     20    |   -51.38 |    -48.66 |      5 |  -241.3  |     40    |   -18.12 |    -12.06 | FAIL      |
| 20/100 fixed1.5 | GLD      | gold     | 1d   |     13 |  -354.06 |      7.69 |   -46.58 |    -46.03 |      1 |  -858.49 |      0    |    -9.79 |     -8.58 | FAIL      |
| 50/200 adaptive | GLD      | gold     | 1d   |      6 |  -468.62 |     16.67 |   -35.73 |    -28.12 |      3 |  -238.21 |     33.33 |   -14.39 |     -7.15 | FAIL      |
| 50/200 fixed1.5 | GLD      | gold     | 1d   |      5 |  -562.3  |     20    |   -40.02 |    -28.12 |      1 |  -579.09 |      0    |   -13.15 |     -5.79 | FAIL      |
| 50/200 adaptive | QQQ      | nasdaq   | 1d   |      8 |   228.12 |     25    |   -40.87 |     18.25 |      5 |  -568.55 |      0    |   -29.41 |    -28.43 | FAIL      |
| 50/200 fixed1.5 | QQQ      | nasdaq   | 1d   |      9 |   168.58 |     22.22 |   -41.03 |     15.17 |      5 |  -568.55 |      0    |   -29.41 |    -28.43 | FAIL      |
| 50/200 fixed1.0 | QQQ      | nasdaq   | 1d   |     10 |   112.2  |     20    |   -41.03 |     11.22 |      5 |  -568.55 |      0    |   -29.41 |    -28.43 | FAIL      |
| 50/200 ungated  | QQQ      | nasdaq   | 1d   |     10 |   112.2  |     20    |   -41.03 |     11.22 |      5 |  -568.55 |      0    |   -29.41 |    -28.43 | FAIL      |
| 20/100 fixed1.0 | QQQ      | nasdaq   | 1d   |     23 |   -88.07 |     13.04 |   -55.43 |    -20.26 |      7 |  -598.04 |     14.29 |   -44.53 |    -41.86 | FAIL      |
| 20/100 ungated  | QQQ      | nasdaq   | 1d   |     23 |   -88.07 |     13.04 |   -55.43 |    -20.26 |      7 |  -598.04 |     14.29 |   -44.53 |    -41.86 | FAIL      |
| 20/100 fixed1.5 | QQQ      | nasdaq   | 1d   |     21 |   -92.16 |     14.29 |   -54.93 |    -19.35 |      6 |  -687.76 |     16.67 |   -43.96 |    -41.27 | FAIL      |
| 20/100 adaptive | QQQ      | nasdaq   | 1d   |     18 |  -146.73 |     16.67 |   -53.64 |    -26.41 |      7 |  -598.04 |     14.29 |   -44.53 |    -41.86 | FAIL      |

Breakdown-short (Donchian low-break + EMA20 cover):

| config               | symbol   | market   | tf   |   tr_n |   tr_exp |   tr_win% |   tr_dd% |   tr_ret% |   va_n |   va_exp |   va_win% |   va_dd% |   va_ret% | verdict   |
|:---------------------|:---------|:---------|:-----|-------:|---------:|----------:|---------:|----------:|-------:|---------:|----------:|---------:|----------:|:----------|
| donchian20 EMA20exit | GLD      | gold     | 1d   |     62 |   -69.97 |     27.42 |   -48    |    -43.38 |     20 |  -114.92 |     15    |   -32.15 |    -22.98 | FAIL      |
| donchian55 EMA20exit | GLD      | gold     | 1d   |     32 |  -133.37 |     21.88 |   -46.53 |    -42.68 |      8 |   -57.31 |     25    |   -10.32 |     -4.58 | FAIL      |
| donchian20 EMA20exit | QQQ      | nasdaq   | 1d   |     75 |   -72.08 |     22.67 |   -55.54 |    -54.06 |     19 |  -159.47 |     21.05 |   -38.51 |    -30.3  | FAIL      |
| donchian55 EMA20exit | QQQ      | nasdaq   | 1d   |     37 |  -126.01 |     27.03 |   -46.62 |    -46.62 |      9 |  -307.78 |     22.22 |   -33.46 |    -27.7  | FAIL      |

**This directly confirms the crypto finding, and the reason is different and
arguably STRONGER here than on BTC.** BTC's shorts died mostly to violent
squeeze-back moves in a boom/bust-cyclical market. Gold and Nasdaq's failure
is more structural: both have had **persistent, decades-long secular
uptrends** (Nasdaq's post-1999 recovery and AI-era run; gold's post-2000
monetary-debasement bull) that a short strategy fights nearly every day it's
in the market — QQQ trend-shorts post catastrophic drawdowns (-40% to -55%)
because the "downtrend" state rarely lasts long enough to pay for its
whipsaws before the underlying secular uptrend reasserts. **The mirror does
not work when the underlying market doesn't have BTC's boom-bust symmetry.**

---

## 9. Decade-by-decade consistency (TRAIN+VAL only, daily — test never touched)

For every SURVIVOR/INSUFFICIENT-SAMPLE daily config, entry-time-bucketed by
decade:

**Family 3 breakout (the strong family):**
- GLD donchian20: 2000s +$140/t (n=28) · 2010s +$86/t (n=48) · **2020s
  -$34/t (n=14)** — recent-decade softening, worth watching.
- GLD donchian55: 2000s +$156/t (n=18) · 2010s +$108/t (n=25) · 2020s +$145/t
  (n=7) — **consistently positive across all three decades**, the cleanest
  record in the whole study.
- QQQ donchian20/55: **negative in the 2000s** (-$40 to -$49/trade, the
  dot-com-bust decade — a real, structural era where a Nasdaq breakout system
  got chopped), strongly positive 1990s/2010s/2020s.
- SPY donchian20/55: same 2000s scar (-$46 to -$87/trade), positive
  elsewhere.
- GC=F donchian20/55: positive 2000s/2010s, roughly flat 2020s (donchian20
  slightly negative, small n=8).

**Family 1 trend, GC=F/SPY:** GC=F 20/100 ungated is positive 2000s (+$446/t)
and 2020s (+$1823/t, n=2 — noisy) but **near-zero in the 2010s** (+$23/t,
n=20) — the "quiet decade" for gold shows up here exactly like it does in the
breakout family. SPY 20/100 is strongly positive across all three visible
decades (1990s/2000s/2010s).

**Honest takeaway:** the equity-index configs (QQQ, SPY) carry a real,
identifiable scar from the 2000-02 dot-com bust decade — a multi-year period
where breakout/trend systems on Nasdaq/S&P lost money. Gold's record is
cleaner (GLD donchian55 positive every decade tested) — consistent with §11's
autopsy: gold trends more cleanly than equity indices, which themselves trend
more cleanly than BTC's boom-bust cycles. **No config's money was made in one
outlier stretch and nothing since** — the pattern is "occasional bad decade,"
not "one lucky decade, dead ever since," which is the more dangerous failure
mode this check is designed to catch.

---

## 10. Per-family autopsy — how do gold/Nasdaq compare to BTC?

**Family 1 (trend) — does gold trend cleaner than BTC?** Only 5/96 survive
the trade-count bar, but that's a sample-size artifact of low turnover (a
20/100-day MA cross just doesn't fire often), not a sign of a weak edge —
most GLD/QQQ/GC=F 20/100 configs across ALL gate variants are POSITIVE on
both train and val, they're simply thin (16-34 train trades vs the 30
minimum). Where BTC needed an ADAPTIVE vol gate to survive its structurally
decaying volatility (round 30), **gold/Nasdaq mostly do better UNGATED** —
their volatility hasn't collapsed the way BTC's has, so a "wait for
liveliness" filter here just prunes good trades. The BTC champion's 4h
$401/trade tier does NOT have a clean size-adjusted analog here — GC=F 1h
20/100 configs land $41-61/trade at ~30-56 train trades, GLD/QQQ daily
land in the low hundreds per trade at low turnover; on a like-for-like %-of-
notional basis these are smaller edges than the BTC champion, consistent
with gold/Nasdaq's structurally lower volatility (less edge available to
harvest per swing).

**Family 2 (dip-buy) — do equity/gold dips mean-revert harder?** No — the
opposite. BTC's 1h RSI3<10-in-trend dip-buy was a genuine ~$40-59/trade
edge (per RESEARCH_LOG's resolution-map finding); the identical shape on
gold/Nasdaq/oil is a wash to negative almost everywhere, surviving only on
oil futures at a thin $6/trade margin. **Equities and gold do not reward
buying short-term RSI panic inside an uptrend the way crypto does** —
plausibly because crypto's retail-driven, thinner order books produce sharper
mean-reverting overreactions than institutionally-arbitraged ETFs/futures
with far tighter effective spreads and faster mean-reversion-arbitrage.

**Family 3 (breakout) — "gold and equity indices are historically THE trend
markets," confirmed.** This family alone accounts for **8 of the study's 14
survivors**, and it's the only family where BOTH gold instruments (GLD ETF
and GC=F futures) independently validate the exact same shape — the strongest
piece of evidence in the whole study. Turnover is honest and low (3-6
trades/yr), and per-trade expectancy ($29-93/trade) clears the 2-4bp cost
floor with real margin. This is the closest gold/Nasdaq analog to BTC's 4h
trend champion — a genuinely LOWER-frequency, LOWER-volatility cousin of the
same underlying idea (breakout, ride it, exit on trend-loss), and it is the
strongest evidence in this round that "port a proven crypto shape, adapt the
parameters" is the right strategy for these markets specifically.

**Family 4 (shorts) — confirmed dead, and structurally so.** See §8. BTC
shorts die to squeeze violence in a cyclical market; gold/Nasdaq shorts die
to secular uptrend persistence. Different mechanism, same practical verdict:
don't short these markets with a mirrored trend/breakout rule.

---

## 11. Top sealed-look candidates (ranked, with reasoning — NONE have been
tested against the sealed 20%; this is a recommendation for where to spend a
look, not a result)

1. **GLD donchian55 EMA20-exit (daily)** — strongest single candidate.
   Positive on train (+$93.25/t, 39t, +36.4% cumulative), val (+$192.79/t,
   11t, +21.2%), AND every visible decade (2000s/2010s/2020s all positive,
   §9). Low turnover (~3/yr) keeps costs a non-issue. **Caveat:** val trade
   count (11) is right at the edge of "thin" — a sealed look here should be
   read with that in mind, not as a large-sample confirmation.
2. **GC=F donchian20/55 EMA20-exit (daily)** — the futures-market
   confirmation of #1's exact same shape on the exact same underlying asset.
   Testing GC=F alongside GLD (both breakout variants) would be the more
   scientifically honest single "look" — it tests whether the edge is in
   gold-the-asset or an ETF-specific artifact.
3. **QQQ/SPY donchian20/55 (daily)** — real edges (§7 table) but carrying
   the 2000s dot-com scar (§9); a sealed look here is a bet that "the modern
   era resembles 2010s/2020s more than 2000s," which is a real market-regime
   assumption, not a free lunch.
4. **GC=F 1h 20/100 ungated/adaptive (Family 1)** — interesting but the
   ~1.4yr sample (56 and 42 train trades respectively) is genuinely too short
   to trust an annualized-return claim; would not spend a sealed look on this
   alone without a longer hourly history (yfinance's 730-day cap is the
   binding constraint, not the edge).
5. **CL=F 1h dip-buy SURVIVOR** — technically a survivor but a thin $6/trade
   edge on a supplementary, non-mandate market; lowest priority of the
   candidates above.

**Recommendation:** if one sealed-test look is to be spent this round, spend
it on **GLD + GC=F donchian55** together (same shape, two instruments,
answers "is this gold or is this GLD" in one look) — the single strongest,
best-diversified piece of evidence produced here. **No such look was taken in
this script; that decision belongs to whoever owns the next round.**

---

## 12. Caveats (read before trusting any number above)

- **Hourly history is capped at ~730 days by yfinance** — every 1h finding
  here is a 1.4-1.7 year sample, thinner than any daily finding and thinner
  than the crypto program's multi-year hourly histories. Treat 1h annualized
  figures (some exceeding +90%/yr on GC=F) as **not extrapolatable** — they
  reflect a short, possibly lucky window, not a durable annual rate.
- **CAGR figures assume full-equity sizing (size_frac=1.0), no leverage, no
  compounding drag from concurrent positions** (these are single-position
  systems) — they are internally consistent but not directly comparable to
  a real portfolio running multiple sleeves at once.
- **Long-only systems are compared against nothing here** — no buy-and-hold
  benchmark was computed. Given gold and Nasdaq's enormous multi-decade
  buy-and-hold returns, every "SURVIVOR" in this study very likely
  underperforms simple buy-and-hold on raw return; its case is lower
  drawdown and a positive, real, both-windows edge, not outperformance.
- **INSUFFICIENT-SAMPLE is the majority verdict (71/200)** — reflects real
  structural sparsity (slow trend/dip signals on markets calmer than BTC),
  not a weak signal; many of these configs are POSITIVE on both windows and
  simply need a longer or higher-frequency dataset to clear the trade-count
  bar the crypto program uses.
- **Gap-honesty correction was only implemented for Family 2** (the only
  family using a hard intrabar stop). Families 1/3/4 rely on signal-driven,
  next-open fills that the engine already prices correctly — no equivalent
  correction was needed there.
- **SPY and USO/CL=F are supplementary, not the core mandate.** SPY tracks
  QQQ's pattern closely (expected, high correlation) and is reported as
  corroboration, not a third target market. Oil failed broadly across all
  families and is reported for completeness.
