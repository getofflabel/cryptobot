# step170 — the mandatory BTC->ETH transfer test, all five edges

Run: `python3 step170_transfer_tests.py` (uses `step170_eth_lib.py`, imports
signal-construction code UNCHANGED from step56/step58/step45b/step54/
step43/strategy.py — see script docstring for exactly what was reused vs
written fresh). Output table: `step170_table.csv`.

**HEADLINE: 0 of 5 BTC edges survive an unchanged-config replay on ETH.**
One re-derived variant (edge 3, the vol-gated trend) shows a promising but
statistically thin signal — correctly marked INSUFFICIENT-SAMPLE, not a
survivor. This is the single most important finding of the round: BTC's
current five "validated" edges look substantially BTC-specific, not a
generalizable crypto-technical library. Full detail per edge below.

Data: ETH-USDT via bybit mainnet cache (`data_bybit_ETHUSDT_{1h,4h,15m}_
full.parquet` + funding), 2021-03-15 -> 2026-07-24 (~5.4y, comparable
depth to BTC's own cached history). Costs: execution="taker" throughout
(BloFin: 6bps taker fee + 1bp half-spread + 2bp slippage/fill = **18bps
round-trip worst case**; this program's realized blended day-trade cost
has run closer to ~9bps). This is a DELIBERATELY STRICTER replay than the
BTC rounds that produced these five edges — step43/step54/step56/step58
all default `execution="maker"`. Stated plainly: some of the gap between
BTC's numbers and ETH's is execution assumption, not just asset. Where a
config is close, that matters; where ETH goes deeply negative (edges 1,
2, 4 below), it doesn't move the verdict.

ETH's own ATR% medians (recomputed fresh, never inherited from BTC):
1h median 0.955% (p25 0.714 / p75 1.282), 4h median 2.023% (p25 1.572 /
p75 2.629). MARKET_PLAYBOOKS.md's BTC figure: hourly ATR medians decayed
era-over-era from ~0.9% to ~0.45%. **ETH runs roughly 2x BTC's current
absolute volatility** — this single fact is the root cause behind edge 3's
divergence below and is worth remembering for every future ETH round.

Sealed-test protocol used here (stated once, applies to every edge): a
config that underwent **zero selection on ETH's own data** is not
"burning a look" by viewing its sealed test slice, because nothing was
chosen based on what that slice contains — this matches the precedent set
by the 2026-07-23 BTC-signal->ETH-trade amplifier round and R89's nine-
asset sealed replay, both of which reported train/val/test in one shot
for a pre-fixed config. Any RE-DERIVED variant (a genuine in-market choice
made by looking at ETH's own distribution) is held to the full standard
instead: train-only selection, val read once, **sealed never touched** —
enforced in code, not just stated.

---

## EDGE 1 — 1h CHoCH k8 + confluence>=2 (BTC sealed +$99.52/t, step56)

Unchanged config: k=8, tool=CHoCH, confluence threshold>=2, target=2x the
train-median structural stop distance, hold 10 days. Code reused verbatim
from step56_smc_toolkit.py (`bos_chain`, `equilibrium`, `liquidity_pools`,
`sweep_events`, `fvg_signals`, `leg_tracker`, `fib_entries`,
`bias_series_4h`, `train_median_stop_pct`).

**Dose-response check first** (BTC showed a monotonic improvement as the
confluence threshold rose 0->1->2: train -29.82 -> +1.54 -> +15.45; val
-77.04 -> +7.64 -> +72.51). ETH shows the OPPOSITE shape — flat-to-worse
as threshold rises:

| threshold | n events (tr+va) | train exp | val exp |
|---|---|---|---|
| 0 | 848 | -$65.07 | +$4.62 |
| 1 | 593 | -$69.51 | -$17.78 |
| 2 | 141 | -$70.92 | -$195.96 |
| 3 | 0 | — no qualifying train entries — | |

The confluence stack's own central claim — "does requiring agreement
beat the single tool" — does not just fail to replicate on ETH, it
**inverts**: more confluence makes it worse, not better.

**Unchanged-config full gauntlet** (threshold>=2, stop=train-median
structural distance 4.72%, target=9.43%, structure stop per the standing
rule, not a swept percentage):

| window | n | expectancy/t | win% | return% | DD% | thickness (x 18bps taker) |
|---|---|---|---|---|---|---|
| train | 51 | -$70.92 | 31.4% | -36.17% | -55.14% | -3.81x |
| val | 17 | -$195.96 | 23.5% | -33.31% | -37.58% | -12.50x |
| test (sealed) | 23 | -$37.90 | 30.4% | -8.72% | -29.13% | -1.10x |

**TRANSFER VERDICT: FAIL.** Deeply negative in every window, on both a
dollar and a cost-multiple basis. No re-derivation attempted — the shape
itself (dose-response inverted) says this isn't a threshold-tuning
problem, it's a different mechanism not operating the same way on ETH.

---

## EDGE 2 — 4h hidden RSI(14) divergence, k8, buf0.35%, tgt3x, hold48h (BTC sealed +$52.03/t, step58)

Unchanged config, code reused verbatim from step58_divergence_mtf.py
(`divergence_events`, `swings`). Gate: ETH's own 4h champion trend
(`vol_gated_ma(fast=20,slow=100,min_atr_pct=1.5)`, same params as BTC's).

ETH's own structure-derived stop distance (train-median distance to the
qualifying swing extreme + 0.35% buffer — same RECIPE as BTC, naturally a
different NUMBER because it's read off ETH's own swings): **4.00%** stop,
12.00% target (3x).

| window | n | expectancy/t | win% | return% | DD% | thickness |
|---|---|---|---|---|---|---|
| train | 63 | -$54.24 | 38.1% | -34.17% | -48.18% | -3.13x |
| val | 19 | -$147.94 | 21.1% | -28.11% | -38.15% | -9.11x |
| test (sealed) | 30 | -$8.78 | 50.0% | -2.63% | -21.76% | **-0.04x** |

**TRANSFER VERDICT: FAIL.** All three windows negative. The sealed-test
thickness is effectively flat-to-negative against the 18bps taker floor —
not a "close but under 5x" case, a genuine miss.

---

## EDGE 3 — 4h trend champion, vol_gated_ma(20,100,min_atr_pct=1.5), live -8% SL ("the ride", R54 sealed proof)

### (a) Unchanged config
BTC's literal min_atr_pct=1.5 gate, applied to ETH's own 4h bars, -8%
swept-percentage stop (unchanged, this is the live book's actual stop —
stated plainly that this specific edge's own BTC form is percentage-
based, not structure-based, which is why a re-derived variant below
replaces it).

**Critical selectivity finding**: BTC's gate was open ~18.7% of bars
(R54, at the time of that round). The SAME 1.5% number on ETH is open
**45.0%** of bars — because ETH's own 4h ATR% median (2.02%) already sits
above 1.5%, the floor barely filters anything. R54's own thesis was "the
gate's selectivity IS the edge in grinds" — porting the literal number
does not preserve that selectivity on an asset with different baseline
volatility.

| window | n | expectancy/t | verdict |
|---|---|---|---|
| train | 38 | +$375.85 | |
| val | 15 | -$129.25 | |

**Verdict: FAIL** at val — no sealed look taken (protocol: fails before
reaching test).

### (b) Re-derived ETH-native version
Grid-searched ETH's own min_atr_pct for the value that reproduces BTC's
~18.7% gate-open selectivity: **min_atr_pct=2.7%** (19.4% time-in-market).
BTC's number was 1.5%; ETH's re-derived number is 2.7% — nearly double,
directly reflecting ETH running ~2x BTC's baseline ATR%.

Also replaced the swept -8% SL with a genuine structure stop (most recent
confirmed k8 swing low + 0.35% buffer, train-median distance): **12.68%**.

| window | n | expectancy/t |
|---|---|---|
| train | 22 | +$214.35 |
| val | 5 | +$26.30 |

Both windows positive, but **below the 30-train/8-val floor** ->
**INSUFFICIENT-SAMPLE**, not a survivor. Per the desk standard, sealed
stays untouched (this variant made two genuine in-market choices on ETH:
the gate level and the stop). This is the one genuinely promising thread
in the whole round — worth a dedicated follow-up (loosen the trend-cross
MA pair or extend to more history to clear the sample floor) — but it is
NOT validated, and reporting it as anything more would be exactly the
mistake R89 warned against.

---

## EDGE 4 — 1h RSI(3)<15 dip-buy, champ4h gate, stop1.5%/tgt4.5%/hold48h (R43 / tactical.py live spec)

This is the literal live BTC tactical-book panic-dip trigger (`champ4h==1
and rsi3(1h)<15`, 48h max hold, +4.5%/-1.5% bracket) computed on ETH's own
candles instead of BTC's — distinct from the ALREADY-VALIDATED ETH
amplifier (which trades ETH off BTC's signal, at ETH's own vol-scaled
geometry, 1.81/5.43/48h — that one is not being re-litigated here).

### (a) Unchanged config (swept 1.5%/4.5%, BTC's literal numbers)

| window | n | expectancy/t | win% | thickness |
|---|---|---|---|---|
| train | 198 | -$32.20 | 23.7% | -2.70x |
| val | 60 | -$51.94 | 21.7% | -3.32x |
| test (sealed) | 64 | -$30.27 | 25.0% | -1.72x |

**Chance baseline** (30 random-timing draws, same n=1760 total entries,
identical engine/costs/stop/target): survivor-by-luck rate **0.0%**, mean
random train exp -$12.06, mean random val exp -$20.29. So the RSI3<15
signal is actually WORSE than random timing on ETH — not merely "no
edge", an actively adverse selection.

### (b) Re-derived (structure stop/target via confirmed_swings)
Structure stop (most recent confirmed swing low, k5, +0.20% buffer,
train-median distance): 1.54% — coincidentally almost identical to BTC's
swept 1.5%. Structure target (nearest confirmed swing high, same method):
4.30% vs BTC's swept 4.5%. The near-match in numbers makes this a clean
test of whether the STOP TYPE (structure vs swept) was masking anything —
it wasn't:

| window | n | expectancy/t |
|---|---|---|
| train | 198 | -$33.37 |
| val | 60 | -$54.45 |

**TRANSFER VERDICT: FAIL**, both variants, decisively. The washout-buy
shape that works on BTC (needing its 48h room) does not transfer to
ETH's own RSI(3) washouts at all.

---

## EDGE 5 — news momentum, WatcherGuru first-post-news-bar-move direction, 1h, stop1.2%/tgt2.4%/hold24h (BTC sealed PASS +$20.81/t, step45b)

Same harvested WatcherGuru feed as BTC's round (it is a general crypto/
macro news feed, not BTC-specific) — 2950 relevant posts, 2025-06-18 to
2026-07-23 (400 days). Code reused verbatim (`align_events`,
`classify_frame`) from step45b_news_events.py. 1452 up / 1495 down
first-bar-move events on ETH's own 1h candles.

| window | n | expectancy/t | win% |
|---|---|---|---|
| train | 202 | +$10.49 | 42.1% |
| val | 68 | -$25.31 | 30.9% |
| test (sealed) | 67 | +$10.97 | 47.8% |

**TRANSFER VERDICT: FAIL** — fails at val (negative), which is where a
real train->val selection process would have stopped regardless of the
test window's own sign. The train/test positive-negative-positive pattern
is not evidence of a real edge; it is closer to noise around zero (train
thickness 0.61x, val -1.47x, test 0.66x — none clear even a loose cost
bar, let alone 5x). Also worth noting for BTC's own record: this is the
program's only sealed-pass edge so far and the sole survivor of 45 prior
rounds — ETH's failure here is the single strongest signal in this whole
round that BTC's news-momentum result may be a regime-specific fit rather
than "news carries tradeable energy," full stop.

---

## SUMMARY TABLE

| # | edge | BTC number | unchanged-config ETH verdict | re-derived ETH verdict |
|---|---|---|---|---|
| 1 | 1h CHoCH+confluence>=2 | sealed +$99.52/t | **FAIL** (all windows negative, dose-response inverted) | not attempted (shape itself broke) |
| 2 | 4h hidden RSI divergence | sealed +$52.03/t | **FAIL** (all windows negative) | not attempted (no close-miss to re-derive from) |
| 3 | 4h trend, vol-gated, -8% SL | R54 sealed proof | **FAIL** (val negative) | **INSUFFICIENT-SAMPLE** (train+val both positive, n=22/5, below 30/8 floor) — the one live thread |
| 4 | 1h RSI3 dip-buy 48h | live spec | **FAIL** (chance-baseline: 0% survivor-by-luck, i.e. worse than random) | **FAIL** (structure stop ~= BTC's swept number, same failure) |
| 5 | news momentum first-bar-move | sealed PASS +$20.81/t | **FAIL** (fails at val) | n/a |

**0 of 5 pass an unchanged-config replay. 0 of 5 are validated on ETH.**
One (#3) has a genuinely promising but sample-starved re-derived variant
flagged for follow-up, not deployment.

Files: `/Users/wallacechen/cryptobot/step170_eth_lib.py`,
`/Users/wallacechen/cryptobot/step170_transfer_tests.py`,
`/Users/wallacechen/cryptobot/step170_table.csv`,
`/Users/wallacechen/cryptobot/step170_results.md` (this file).
