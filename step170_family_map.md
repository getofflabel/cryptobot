# step170_family_map.md — ETH family map (running log)

Per Morgan's expanded mandate (2026-07-25): build ETH a family map
comparable to BTC's ~30-family program. One line per family, appended
after every round, never edited retroactively except to fix an error.
Format: **family | status | key number | chance baseline | thickness |
transfer note (if applicable)**.

Standing figures used throughout: execution="taker" always; taker round
trip = 18bps (6bps fee + 1bp half-spread + 2bp slippage, both fills);
this program's realized blended day-trade cost ~9bps; min 30 train / 8
val trades or INSUFFICIENT-SAMPLE; sealed test untouched for anything
that involved a choice made by looking at ETH's own data; ETH's own ATR%
medians (never inherited from BTC): 1h 0.955%, 4h 2.023% (roughly 2x
BTC's current decayed-era level).

---

## ROUND 170 — the five BTC edges, transfer test (2026-07-25)
Full detail: step170_results.md / step170_table.csv / step170_transfer_tests.py.

1. **1h CHoCH k8 + confluence>=2** — DEAD (transfer). Unchanged-config
   full gauntlet on ETH: train -$70.92/t x51, val -$195.96/t x17, sealed
   -$37.90/t x23. Dose-response INVERTS vs BTC (more confluence = worse,
   not better). Thickness -1.1x to -12.5x taker cost (all negative).
   BTC number: sealed +$99.52/t x16. Transfer: unchanged-config replay,
   FAIL.
2. **4h hidden RSI(14) divergence k8 buf0.35% tgt3x hold48h** — DEAD
   (transfer). Unchanged-config full gauntlet: train -$54.24/t x63, val
   -$147.94/t x19, sealed -$8.78/t x30 (thickness -0.04x). BTC number:
   sealed +$52.03/t x24. Transfer: unchanged-config replay, FAIL.
3. **4h trend, vol_gated_ma(20,100,min_atr=1.5), -8% SL ("the ride")** —
   unchanged config FAIL (train +$375.85/t x38, val -$129.25/t x15, no
   sealed look). Re-derived (ETH-native gate min_atr_pct=2.7% matched to
   BTC's own 18.7% selectivity, structure stop 12.68% replacing the swept
   -8%): train +$214.35/t x22, val +$26.30/t x5 — both positive but
   **INSUFFICIENT-SAMPLE** (below 30/8 floor). BTC number: R54 sealed
   proof, min_atr_pct=1.5 (18.7% selectivity). ETH's re-derived number:
   min_atr_pct=2.7% (19.4% selectivity) — differs because ETH's baseline
   4h ATR% (median 2.02%) runs ~2x BTC's. FLAGGED FOR FOLLOW-UP, not a
   survivor.
4. **1h RSI(3)<15 dip-buy, champ4h gate, 48h hold** — DEAD (transfer).
   Unchanged config (swept 1.5%/4.5%): train -$32.20/t x198, val
   -$51.94/t x60, sealed -$30.27/t x64. Chance baseline (30 random-timing
   draws, same n): survivor-by-luck rate 0% — the signal is WORSE than
   random on ETH. Re-derived structure stop/target (1.54%/4.30%, nearly
   identical numbers to BTC's swept ones): same failure, train -$33.37/t,
   val -$54.45/t. BTC number: live spec (needs 48h room). Transfer: FAIL,
   both unchanged and re-derived.
5. **News momentum, WatcherGuru first-bar-move direction, 1h** — DEAD
   (transfer). Unchanged config: train +$10.49/t x202, val -$25.31/t x68
   (fails here), sealed +$10.97/t x67 — noise around zero (thickness
   0.09x to -1.47x, never clears even a loose cost bar). BTC number:
   sealed PASS +$20.81/t x67. Transfer: unchanged-config replay, FAIL.

**ROUND 170 VERDICT: 0/5 BTC edges survive an unchanged-config replay on
ETH. This is the single most important finding of the night — BTC's
current five "validated" edges look substantially BTC-specific, not a
generalizable crypto-technical library.** Escalated to morgan immediately
per standing instruction (any BTC edge failing to transfer is desk-wide
information about whether BTC's own result is fitted).
