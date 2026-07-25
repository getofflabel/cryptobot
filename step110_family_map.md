# Oil Family Map (running log, appended through the night per Morgan's
2026-07-25 expanded mandate — "match the work put into Bitcoin itself")

Goal: comparable to BTC's ~30-family program (5 survivors, ~25 confirmed
dead). Every entry below carries: family name, verdict (SURVIVOR / FAIL /
INSUFFICIENT-SAMPLE), the key number, its chance baseline, and its
thickness multiple — no bare "best cell."

## Pre-sweep: the two mandatory deliverables

- **0. Live oil book audit** (`step110_livebook_audit.py`/`step110_results.md`)
  — the EXACT rule set currently live (`daily_pick.score_instrument` +
  `daily_pick._stop_target_pct` via `tradfi_engine.py`) — **FAIL**. Train
  1,132t -$37.10/t, val 378t -$54.05/t (taker, 10bps r/t), thickness
  -0.96x/-1.47x. Chance baseline: train 81st pctile of randomized-timing
  control (mildly beats noise in-sample), val 8th pctile (worse than
  noise out-of-sample) — classic in-sample-only signature. Structural
  violation independent of P&L: 19% of trades stopped by a flat 1.0% cap
  ported from crypto, not by chart structure. **Recommendation: stand
  down now**, sent to Morgan.
- **1. EIA/API inventory reaction study** (`step111_eia_reaction.py`/
  `step111_results.md`) — descriptive diagnostic, not a costed strategy.
  EIA release hour: real reaction (0.570% mean|move|, 1.75x the same-
  window baseline, 2.2x the randomized-timing control), decays smoothly
  to 1.07x by 24h, shape = CONTINUATION (corr +0.298 reaction-vs-next-4h).
  Flags an apparent conflict with round 78's "EIA reversal, all 12
  continuation configs failed" finding — not reconciled yet, so NO
  strategy sealed-tested on this finding this round (round 78 already
  spent 2 sealed looks on EIA topics). API (Tuesday estimate): NO
  detectable reaction at any horizon, below its own baseline throughout —
  clean negative result.

## Family sweep 1 — crypto/gold/SPX shapes ported, oil-derived thresholds
(`step112_oil_family_sweep.py`, `step112_results.md`, `step112_table.csv`)

**Two corrections applied by hand to this round's raw script output**,
because `step150_common.verdict_for` (built for the BTC re-test) applies
a looser bar than this desk's own evidence standard on two points: (1)
it labels SURVIVOR on sign+floor alone, without checking the 5x-thickness
reject line; (2) it only emits INSUFFICIENT-SAMPLE when BOTH windows are
positive but under-floor, so a negative tiny-n result prints as a bare
FAIL. Both are corrected below — the underlying numbers are unchanged,
only the verdict label is.

- **1. CHoCH k8 + confluence>=2 (1h/4h)** — **INSUFFICIENT SAMPLE** (train n=6, val n=2 — both far under the 30/8 floor; raw numbers: val 2t $+81.14/t, train 6t $-17.41/t) | chance baseline: random-entry mean $-43.56/t (n=2 val draws, itself too small to trust) | thickness: 4.89x full round-trip cost (also not meaningful at n=2)
- **2. 4h hidden RSI(14) divergence k8** — **INSUFFICIENT SAMPLE** (train n=10, val n=2 — both far under floor; raw: val 2t $+71.04/t, train 10t $-51.62/t) | chance baseline: random-entry mean $-9.24/t (n=2, not trustworthy) | thickness: 2.97x full round-trip cost (not meaningful at n=2)
- **3. 4h vol-gated trend MA20/100 (chandelier exit)** — **INSUFFICIENT SAMPLE** (train n=16, val n=6 — both under floor; raw: val 6t $-53.90/t, train 16t $-76.68/t, both negative so directionally a likely FAIL, but sample too thin to certify) | chance baseline: N/A (trend state-machine; time-in-market 32.8%) | thickness: -3.27x full round-trip cost
- **4. 1h RSI3 washout dip-buy (pure ATR stop, cap dropped)** — **INSUFFICIENT SAMPLE** (train n=14, val n=1 — both far under floor; raw: val 1t $-172.85/t, train 14t $-109.03/t, both negative) | chance baseline: random-entry mean $-90.88/t (n=1, not trustworthy) | thickness: -2.52x full round-trip cost
- **5-1d-20. Donchian(20) + structure-trail (1d)** — **REJECT — thin edge, under 5x cost bar** (floors cleared: train n=88, val n=20, BOTH windows positive: val 30t $+6.04/t, train 88t $+9.02/t — a real, sample-adequate positive result, but thickness 1.64x full round-trip cost is under the house 5x-reject line) | chance baseline: N/A (trend/breakout state-machine, see family 3) | thickness: **1.64x — REJECT** (task's 12bps definition: 2.46x, also under 5x)
- **5-1d-55. Donchian(55) + structure-trail (1d)** — **REJECT — thin edge, under 5x cost bar** (floors cleared: train n=61, val n=20, BOTH windows positive: val 20t $+7.35/t, train 61t $+11.75/t) | chance baseline: N/A (trend/breakout state-machine, see family 3) | thickness: **2.36x — REJECT** (task's 12bps definition: 3.54x, also under 5x) — closest thing to a real edge in this batch; worth a dedicated exit-variation round (step11x) before writing it off entirely, since the trail-only exit here is unmodified gold_book.py geometry, not yet oil-optimized
- **5-1h-20. Donchian(20) + structure-trail (1h)** — FAIL (floors cleared: train n=198, val n=72; val 72t $-45.65/t, train 198t $-10.37/t, both negative) | chance baseline: N/A (trend/breakout state-machine) | thickness: -2.65x full round-trip cost
- **6. RSI2<5 dip-buy above SMA200 (SPX shape)** — FAIL (floors cleared: train n=51, val n=19; val 19t $-120.78/t, train 51t $-141.66/t, both negative, confirms round 78's original finding under a stricter structural-stop harness) | chance baseline: N/A — signal-exit family | thickness: -6.45x full round-trip cost

**Batch 1 summary: 0 survivors, 2 near-misses worth an exit-variation follow-up (donchian 1d, both lookbacks — real positive edge, real sample size, but under the 5x thickness bar as-is), 4 insufficient-sample, 3 clean FAILs.** Every ported crypto-shock/divergence-style family (1, 2, 4) starved for sample on oil's ~2.4y history at these gate conditions — oil's own event frequency for these specific triggers is simply much lower than BTC's; that itself is a finding (stated, not hidden).
- **7. Order blocks (base, mult2, 50pct touch) — BTC-dead confirmation** — FAIL | val 57t $-72.11/t (train 165t $-41.01/t) | chance baseline: random-entry mean $-61.79/t -> real does NOT beat chance | thickness: -1.76x full round-trip cost
- **8. Pin bars (wick2x, roll20 context) — BTC-dead confirmation** — FAIL | val 89t $-86.16/t (train 200t $-47.14/t) | chance baseline: random-entry mean $-60.86/t -> real does NOT beat chance | thickness: -2.07x full round-trip cost
- **9. Engulfing (roll20 context) — BTC-dead confirmation** — FAIL | val 100t $-72.29/t (train 239t $-40.55/t) | chance baseline: random-entry mean $-56.66/t -> real does NOT beat chance | thickness: -1.72x full round-trip cost
- **10. Oil session structure (Asia/London/NY/off, descriptive)** — DESCRIPTIVE (not a strategy) | Asia: 0.209%|ret| (0th pctile vs shuffle), London: 0.380%|ret| (100th pctile vs shuffle), NY: 0.407%|ret| (100th pctile vs shuffle), Off/maintenance: 0.212%|ret| (0th pctile vs shuffle) | chance baseline: 200 label-shuffle draws per session (see numbers above) | thickness: n/a — descriptive only
- **11. EIA-continuation strategy (costed, TRAIN+VAL ONLY, sealed untouched)** — FAIL | val 25t $-43.76/t (train 75t $-95.02/t) | chance baseline: random-entry mean $-56.44/t -> real beats chance (chance itself is negative here too — exit geometry loses money at 4h holds regardless of direction) | thickness: -1.18x full round-trip cost | NOTE: RESOLVES round 78's flagged conflict rather than deepening it — round 78's sealed "EIA reversal" FAILED and this "EIA continuation" also FAILS; the raw directional tendency step111 measured in price is real but too small to survive a real stop/cost structure either way. See step114_results.md.
- **12. OPEC meeting reactions** — NOT TESTED (no reliable local OPEC/OPEC+ meeting calendar available in this repo or session; fabricating dates from memory risks a wrong calendar masquerading as a real one — flagged as an open data gap rather than guessed)
- **13. Contango/backwardation front-month roll effect** — NOT TESTABLE with available data (only a single front-month CL=F/BZ=F series is cached — no second contract month or futures curve data exists in this repo to compute an actual term-structure signal; stated honestly per the round's own instruction rather than faked)
- **14. BZ=F transfer check — Donchian(55)+structure-trail, UNCHANGED config from family 5-1d-55** — REJECT (thin, under 5x cost) | val 17t $+14.42/t (train 40t $+96.54/t) | thickness: +3.58x full round-trip cost | CL=F val: n=20, +$7.35/t, 2.36x cost (family 5-1d-55, this same map) | transfer HOLDS (same sign, same-shape edge on the second instrument) | WTIOIL-USDT not used (only 58 daily bars cached — far short of what a 55-bar Donchian + 60/20/20 split needs)
- **15-CL=F. Exit-variation screen — Donchian(55)** — REJECT (thin, under 5x cost) | selected on TRAIN only: `chandelier2.5_r3` (train 105t $+56.66/t) | VAL READ ONCE: 35t $+37.12/t | chance baseline: random-entry mean $+47.99/t -> real does NOT beat chance | thickness: +3.92x full round-trip cost | baseline for comparison (gold's unmodified trail-only exit): CL 2.36x / BZ 3.58x cost (families 5-1d-55 and 14)
- **15-BZ=F. Exit-variation screen — Donchian(55)** — SURVIVOR (train+val — sealed look NOT spent) | selected on TRAIN only: `chandelier3.5_trail` (train 47t $+160.34/t) | VAL READ ONCE: 17t $+101.13/t | chance baseline: random-entry mean $+87.88/t -> real beats chance | thickness: +15.87x full round-trip cost | baseline for comparison (gold's unmodified trail-only exit): CL 2.36x / BZ 3.58x cost (families 5-1d-55 and 14) | **CAVEAT 1 (multiple comparisons): this config was the best of 9 TRAIN-screened candidates on BZ specifically — a real risk of picking the in-sample-lucky one out of 9, which is exactly why this is NOT called validated and a sealed look is Morgan's call, not mine, before any deployment.** **CAVEAT 2 (does NOT transfer to WTI): the SAME unchanged config (chandelian3.5x trail on Donchian(55)) replayed on CL=F is ALREADY NEGATIVE on CL's own TRAIN window (-$14.65/t, n=74 — visible in this round's own CL grid, no extra script needed) — this is a Brent-specific result, not yet a WTI-tradeable one, and the live/paper venue (WTIOIL-USDT, CL=F) is WTI. Practical relevance to the actual book is open until a WTI-specific equivalent is found.**
