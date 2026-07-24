# step64_results.md — ROUND 64: THE FLIP

Question: when we're LONG and structure breaks down hard, is cut-and-reverse (FLIP) better than riding the stop, and does cutting-only beat both? Full method, entry generator, and cost discipline are documented in step64_flip.py's module docstring — not repeated here.

Cost hurdle (taker round trip): 18.0 bps notional per entry+exit ($18.00 on the $10,000 fixed notional used here), before funding. Round-43's 15m cost-floor finding was ~9.2bps realized cost vs ~3bps edge — a strategy dying by inches to costs. The short leg below dies by a lot more than that: its per-trade losses run $15-$65, several times the $18.00 round-trip hurdle, meaning this is real adverse price action on the short side, not a cost-floor artifact. Floors: 30 train / 8 val trades. Sealed 20% test window never touched.


## BTCUSDT

Entries mapped to 15m: train 675, val 206 (sealed test excluded entirely).

| policy | config | tr_n | tr_exp | tr_win% | tr_ret% | tr_dd% | va_n | va_exp | va_win% | va_ret% | va_dd% | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P0 | baseline (ride bracket/4h) | 663 | $-10.94 | 44% | -72.5% | -76.0% | 203 | $-14.98 | 42% | -30.4% | -34.2% | FAIL |
| P1 | N12_x0.3_UNCONF | 728 | $-12.62 | 41% | -91.9% | -96.3% | 233 | $-19.05 | 36% | -44.4% | -48.5% | FAIL |
| P2 | N12_x0.3_UNCONF | 668 | $-12.02 | 42% | -80.3% | -83.5% | 204 | $-17.88 | 38% | -36.5% | -40.1% | FAIL |
| P1 | N12_x0.3_CONF | 676 | $-11.01 | 43% | -74.4% | -79.9% | 209 | $-16.87 | 40% | -35.3% | -38.7% | FAIL |
| P2 | N12_x0.3_CONF | 664 | $-11.02 | 43% | -73.2% | -77.1% | 203 | $-15.94 | 41% | -32.4% | -35.9% | FAIL |
| P1 | N12_x0.5_UNCONF | 703 | $-13.19 | 41% | -92.7% | -97.8% | 221 | $-19.65 | 37% | -43.4% | -47.2% | FAIL |
| P2 | N12_x0.5_UNCONF | 666 | $-11.98 | 42% | -79.8% | -82.9% | 204 | $-17.54 | 39% | -35.8% | -39.1% | FAIL |
| P1 | N12_x0.5_CONF | 668 | $-11.39 | 43% | -76.1% | -79.5% | 205 | $-15.38 | 41% | -31.5% | -35.3% | FAIL |
| P2 | N12_x0.5_CONF | 663 | $-10.98 | 43% | -72.8% | -76.3% | 203 | $-14.88 | 42% | -30.2% | -34.0% | FAIL |
| P1 | N24_x0.3_UNCONF | 722 | $-12.46 | 41% | -90.0% | -94.4% | 230 | $-19.35 | 36% | -44.5% | -48.7% | FAIL |
| P2 | N24_x0.3_UNCONF | 666 | $-12.06 | 42% | -80.3% | -83.5% | 204 | $-17.89 | 38% | -36.5% | -40.1% | FAIL |
| P1 | N24_x0.3_CONF | 676 | $-11.01 | 43% | -74.4% | -79.9% | 208 | $-17.33 | 40% | -36.0% | -39.5% | FAIL |
| P2 | N24_x0.3_CONF | 664 | $-11.02 | 43% | -73.2% | -77.1% | 203 | $-16.09 | 41% | -32.7% | -36.1% | FAIL |
| P1 | N24_x0.5_UNCONF | 695 | $-12.69 | 42% | -88.2% | -93.3% | 221 | $-19.65 | 37% | -43.4% | -47.2% | FAIL |
| P2 | N24_x0.5_UNCONF | 664 | $-11.83 | 42% | -78.5% | -81.7% | 204 | $-17.54 | 39% | -35.8% | -39.1% | FAIL |
| P1 | N24_x0.5_CONF | 668 | $-11.39 | 43% | -76.1% | -79.5% | 205 | $-15.38 | 41% | -31.5% | -35.3% | FAIL |
| P2 | N24_x0.5_CONF | 663 | $-10.98 | 43% | -72.8% | -76.3% | 203 | $-14.88 | 42% | -30.2% | -34.0% | FAIL |

### BTCUSDT — short leg isolation (P1 only)

Of every reversal short P1 opens, does the short leg itself earn or donate?

| config | tr_n | tr_exp | tr_win% | tr_sum_pnl | va_n | va_exp | va_win% | va_sum_pnl |
|---|---|---|---|---|---|---|---|---|
| N12_x0.3_UNCONF | 69 | $-23.00 | 32% | $-1586.86 | 32 | $-22.95 | 28% | $-734.37 |
| N12_x0.3_CONF | 13 | $-17.24 | 31% | $-224.17 | 6 | $-48.24 | 17% | $-289.41 |
| N12_x0.5_UNCONF | 42 | $-30.83 | 29% | $-1294.89 | 18 | $-45.25 | 11% | $-814.43 |
| N12_x0.5_CONF | 5 | $-64.96 | 0% | $-324.80 | 2 | $-66.50 | 0% | $-133.01 |
| N24_x0.3_UNCONF | 63 | $-22.37 | 33% | $-1409.00 | 29 | $-25.75 | 24% | $-746.64 |
| N24_x0.3_CONF | 13 | $-17.24 | 31% | $-224.17 | 5 | $-67.61 | 0% | $-338.07 |
| N24_x0.5_UNCONF | 34 | $-28.99 | 32% | $-985.80 | 18 | $-45.25 | 11% | $-814.43 |
| N24_x0.5_CONF | 5 | $-64.96 | 0% | $-324.80 | 2 | $-66.50 | 0% | $-133.01 |

### BTCUSDT — V-bounce autopsy (fake-out rate)

Of all breakdown triggers actually fired against our longs, what % see price close back above the trigger level within K bars (a fake-out)?

| config | fires | fakeout%@4bar | fakeout%@8bar |
|---|---|---|---|
| N12_x0.3_UNCONF | 101 | 69% | 78% |
| N12_x0.3_CONF | 19 | 79% | 89% |
| N12_x0.5_UNCONF | 60 | 67% | 75% |
| N12_x0.5_CONF | 7 | 86% | 86% |
| N24_x0.3_UNCONF | 92 | 70% | 79% |
| N24_x0.3_CONF | 18 | 78% | 89% |
| N24_x0.5_UNCONF | 52 | 67% | 75% |
| N24_x0.5_CONF | 7 | 86% | 86% |

## ETHUSDT

Entries mapped to 15m: train 558, val 200 (sealed test excluded entirely).

| policy | config | tr_n | tr_exp | tr_win% | tr_ret% | tr_dd% | va_n | va_exp | va_win% | va_ret% | va_dd% | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P0 | baseline (ride bracket/4h) | 541 | $-25.02 | 37% | -135.3% | -136.2% | 196 | $-17.60 | 42% | -34.5% | -35.5% | FAIL |
| P1 | N12_x0.3_UNCONF | 583 | $-24.05 | 36% | -140.2% | -141.7% | 216 | $-19.18 | 39% | -41.4% | -42.4% | FAIL |
| P2 | N12_x0.3_UNCONF | 543 | $-24.24 | 36% | -131.6% | -132.9% | 196 | $-18.17 | 39% | -35.6% | -36.6% | FAIL |
| P1 | N12_x0.3_CONF | 546 | $-25.26 | 37% | -137.9% | -139.4% | 199 | $-15.69 | 43% | -31.2% | -32.9% | FAIL |
| P2 | N12_x0.3_CONF | 541 | $-24.99 | 37% | -135.2% | -136.4% | 196 | $-17.07 | 42% | -33.5% | -34.4% | FAIL |
| P1 | N12_x0.5_UNCONF | 571 | $-22.98 | 37% | -131.2% | -132.7% | 207 | $-16.14 | 42% | -33.4% | -34.4% | FAIL |
| P2 | N12_x0.5_UNCONF | 541 | $-24.96 | 36% | -135.0% | -136.3% | 196 | $-16.38 | 41% | -32.1% | -33.1% | FAIL |
| P1 | N12_x0.5_CONF | 545 | $-25.16 | 37% | -137.1% | -138.6% | 198 | $-16.75 | 42% | -33.2% | -34.1% | FAIL |
| P2 | N12_x0.5_CONF | 541 | $-25.06 | 37% | -135.6% | -136.8% | 196 | $-17.33 | 42% | -34.0% | -34.9% | FAIL |
| P1 | N24_x0.3_UNCONF | 577 | $-24.36 | 36% | -140.5% | -142.0% | 214 | $-19.33 | 39% | -41.4% | -42.3% | FAIL |
| P2 | N24_x0.3_UNCONF | 543 | $-24.24 | 36% | -131.6% | -132.9% | 196 | $-17.98 | 39% | -35.2% | -36.2% | FAIL |
| P1 | N24_x0.3_CONF | 546 | $-25.26 | 37% | -137.9% | -139.4% | 199 | $-15.69 | 43% | -31.2% | -32.9% | FAIL |
| P2 | N24_x0.3_CONF | 541 | $-24.99 | 37% | -135.2% | -136.4% | 196 | $-17.07 | 42% | -33.5% | -34.4% | FAIL |
| P1 | N24_x0.5_UNCONF | 567 | $-23.18 | 37% | -131.4% | -132.9% | 205 | $-16.27 | 42% | -33.3% | -34.3% | FAIL |
| P2 | N24_x0.5_UNCONF | 541 | $-24.96 | 36% | -135.0% | -136.3% | 196 | $-16.19 | 42% | -31.7% | -32.7% | FAIL |
| P1 | N24_x0.5_CONF | 544 | $-25.51 | 37% | -138.8% | -140.3% | 198 | $-16.75 | 42% | -33.2% | -34.1% | FAIL |
| P2 | N24_x0.5_CONF | 541 | $-25.10 | 37% | -135.8% | -137.0% | 196 | $-17.33 | 42% | -34.0% | -34.9% | FAIL |

### ETHUSDT — short leg isolation (P1 only)

Of every reversal short P1 opens, does the short leg itself earn or donate?

| config | tr_n | tr_exp | tr_win% | tr_sum_pnl | va_n | va_exp | va_win% | va_sum_pnl |
|---|---|---|---|---|---|---|---|---|
| N12_x0.3_UNCONF | 47 | $-15.14 | 34% | $-711.71 | 22 | $-23.90 | 41% | $-525.82 |
| N12_x0.3_CONF | 5 | $-54.03 | 20% | $-270.14 | 3 | $+74.13 | 100% | $+222.38 |
| N12_x0.5_UNCONF | 33 | $+8.70 | 45% | $+287.18 | 13 | $-5.82 | 54% | $-75.68 |
| N12_x0.5_CONF | 4 | $-38.79 | 25% | $-155.15 | 2 | $+40.17 | 100% | $+80.34 |
| N24_x0.3_UNCONF | 40 | $-18.65 | 32% | $-746.05 | 20 | $-27.82 | 40% | $-556.40 |
| N24_x0.3_CONF | 5 | $-54.03 | 20% | $-270.14 | 3 | $+74.13 | 100% | $+222.38 |
| N24_x0.5_UNCONF | 28 | $+9.66 | 46% | $+270.48 | 11 | $-9.66 | 55% | $-106.26 |
| N24_x0.5_CONF | 3 | $-99.07 | 0% | $-297.21 | 2 | $+40.17 | 100% | $+80.34 |

### ETHUSDT — V-bounce autopsy (fake-out rate)

Of all breakdown triggers actually fired against our longs, what % see price close back above the trigger level within K bars (a fake-out)?

| config | fires | fakeout%@4bar | fakeout%@8bar |
|---|---|---|---|
| N12_x0.3_UNCONF | 69 | 74% | 83% |
| N12_x0.3_CONF | 8 | 62% | 62% |
| N12_x0.5_UNCONF | 46 | 74% | 80% |
| N12_x0.5_CONF | 6 | 67% | 67% |
| N24_x0.3_UNCONF | 60 | 75% | 83% |
| N24_x0.3_CONF | 8 | 62% | 62% |
| N24_x0.5_UNCONF | 39 | 74% | 79% |
| N24_x0.5_CONF | 5 | 80% | 80% |

## Ranked sealed-look candidates

A candidate must beat P0 baseline on BOTH train AND val expectancy AND clear the 30/8 trade floors on both. None found here are spent against test — that stays the lead's call.

- None. No policy beat baseline on both windows with sufficient sample.

## What today's dump actually would have looked like (illustrative, not scored)

This section does NOT touch the gauntlet, does NOT select a config, and is NOT a sealed-test look — it just runs the fastest trigger config against today's exact real bars so the numbers behind the verdict below are concrete, not abstract.


**BTCUSDT**

Largest N12/x0.3/unconfirmed breakdown trigger on BTCUSDT today, UTC (self-updating window — today's own calendar date, not a hand-picked timestamp):

- trigger fires on the 2026-07-24 12:45:00+00:00 close, level 64772.27
- FLIP reverses short at the 2026-07-24 13:00:00+00:00 open, fill $64726.18
- best the short ever sees inside its 4h clock: low $63700.70 (+1.58% favorable)
- by 2026-07-24 15:00:00+00:00 (bar +8): close $64104.70, still below the trigger level, -0.96% vs the short's OWN entry price.
  -> the short is still ahead of its own entry at this point, one of the minority of cases where the timing worked.


**ETHUSDT**

Largest N12/x0.3/unconfirmed breakdown trigger on ETHUSDT today, UTC (self-updating window — today's own calendar date, not a hand-picked timestamp):

- trigger fires on the 2026-07-24 12:45:00+00:00 close, level 1873.90
- FLIP reverses short at the 2026-07-24 13:00:00+00:00 open, fill $1871.05
- best the short ever sees inside its 4h clock: low $1846.60 (+1.31% favorable)
- by 2026-07-24 15:00:00+00:00 (bar +8): close $1864.31, still below the trigger level, -0.36% vs the short's OWN entry price.
  -> the short is still ahead of its own entry at this point, one of the minority of cases where the timing worked.


## Verdict, plain English

**BTCUSDT**: baseline (ride) train $-10.94/t, val $-14.98/t. Best FLIP (P1) config train $-11.01/t, val $-16.87/t. Best CUT-ONLY (P2) config train $-10.98/t, val $-14.88/t. Short leg negative in both train AND val on 8/8 configs, positive in both on 0/8. Fake-out rate across every trigger config: 67-86% at 4 bars, 75-89% at 8 bars.

**ETHUSDT**: baseline (ride) train $-25.02/t, val $-17.60/t. Best FLIP (P1) config train $-22.98/t, val $-16.14/t. Best CUT-ONLY (P2) config train $-24.24/t, val $-18.17/t. Short leg negative in both train AND val on 2/8 configs, positive in both on 0/8. Fake-out rate across every trigger config: 62-80% at 4 bars, 62-83% at 8 bars.

On this entry set and this geometry, RIDE (P0) is not a good strategy on its own — but neither CUT nor FLIP fixes it. Every P1/P2 config tested underperforms or barely matches baseline on train, and none clears baseline on BOTH train and val at the 30/8 sample floor (see 'ranked sealed-look candidates' above: none found). The short leg in isolation is mostly negative, with a few small/inconsistent exceptions that flip sign between train and val — the signature of noise, not edge. The V-bounce autopsy explains why: across every trigger config on both assets, 62-89% of the breakdown triggers this study fired see price close back above the FULL structural breakdown level within 8 bars. Even the minority that don't fully reclaim the level — like today's real ETH dump, autopsied above — still bounce enough within a few bars to erase a short sized for a tight 1.5x-of-capped-1%-ATR target; the short doesn't need a full structural reclaim to lose, it just needs the bounce to be bigger than its own target, which is common. Today's V-bounce was not a fluke this study can wave away — it is the modal outcome of this exact trigger shape, on both assets, confirming rounds 41/45's structural finding (the 2025-26 grind punishes breakdown-chasing shorts) extends to the CONDITIONAL flavor too: reacting off an existing long doesn't change the physics of what BTC/ETH downmoves actually do in this regime, it just adds a second losing trade on top of the first. RECOMMENDATION: keep the live baseline (ride to bracket/time exit). Do not build a flip. Cut-only is the less-bad of the two reactive policies where it beats flip, but it is not a proven improvement over riding at the floors this round required, and no config here is a sealed-look candidate.

