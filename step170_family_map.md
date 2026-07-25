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

## ROUND 171 — cross-market ports: gold's donchian + SPX's RSI2 dip-buy (2026-07-25)
Full detail: step171_table.csv / step171_crossmarket_ports.py. ETH daily
bars, 1957 bars (~5.4y, 2021-03 to 2026-07). Note up front: both source
edges are UNIT-FREE by construction (breakout vs own N-bar high, RSI 0-100,
SMA-relative position) — unlike step170 edge 3's ATR%-floor, no threshold
re-derivation was needed for a fair unchanged-config replay; this is
itself a methodological finding, stated rather than assumed.

6. **Gold's donchian20+EMA20exit, ported unchanged** — DEAD (transfer).
   train +$416.56/t x20, val -$25.21/t x6 -> FAIL. Source: GLD/GC=F
   sealed-PASS 4x, ~5.4 trades/yr at d20.
7. **Gold's donchian55+EMA20exit, ported unchanged** — INSUFFICIENT-SAMPLE.
   train +$182.41/t x12, val +$379.50/t x4 — both positive, well under the
   30/8 floor (daily crypto bars over 5.4y structurally can't produce many
   55-bar-breakout events). Flagged, not a survivor; would need much more
   history to ever clear the sample floor at this N.
8. **SPX's RSI(2)<5 dip-buy above SMA200, ported unchanged** — DEAD
   (transfer). train -$20.07/t x11, val +$353.02/t x5 (both under floor
   too) -> FAIL. Source: SPY sealed +$75.36/t x33 / ES=F sealed
   +$124.07/t x29. Context: ETH spends only 41.2% of days above its own
   SMA200 (vs SPX's long-biased, mostly-above-SMA200 personality) — the
   folklore's own precondition (a persistently long-biased index) holds
   far less often on ETH.
9. **SPX's RSI(2)<10 dip-buy above SMA200, ported unchanged** — DEAD
   (transfer). train -$29.08/t x22, val -$12.52/t x7 -> FAIL, both
   windows negative.
10. **SPX's RSI(2)<15 dip-buy above SMA200, ported unchanged** — DEAD
    (transfer). train +$8.64/t x30 (barely positive, right at the train
    floor), val -$145.13/t x8 -> FAIL at val.

**ROUND 171 VERDICT: 0/5 cross-market configs validate on ETH daily bars**
(2 outright FAIL, 3 either FAIL or INSUFFICIENT-SAMPLE with no clean
survivor). Combined with round 170: 0/10 ported edges (5 from BTC, 3 from
gold/SPX with 2 more variants) have validated on ETH so far tonight.
Structural note: ETH's ~5.4y of daily history is thin for N=55-bar or
SMA200-gated shapes that need years to accumulate 30+ events — this is a
sample-size ceiling on crypto daily-bar research generally, not evidence
the shapes are wrong, and should be revisited as more history accrues
rather than declared permanently dead.

## ROUND 172 — cheap dead-family retests on ETH (2026-07-25)
Full detail: step172_table.csv / step172_dead_family_retests.py. Lighter-
weight confirmation than BTC's own 296-config step57 grid — a cheap first
bar per the mandate ("'dead on BTC' isn't 'dead everywhere'"), not a full
re-run. All confirm DEAD, same as BTC, no differently-shaped ETH edge
found in these three shapes.

11. **Always-on shorts** — DEAD (confirmed, matches BTC's 5x). 1h stop
    1.5xATR: train n=1 (+$10.03, technically INSUFFICIENT-SAMPLE — an
    unconditional signal only produces one continuous "trade" per window
    by construction) val -$147.05; 1h stop 2.5xATR: train -$86.81, val
    +$129.12; 4h both stop variants negative both windows. Directionally
    consistent with dead, sign-unstable, no edge in any cell.
12. **Pin bar reversal** (simple wick>=2x/3x body definition, structure
    stop via confirmed_swings) — DEAD. All 8 configs (wick2.0/3.0 x
    hold24h/48h x tgt2x/3x) negative BOTH train and val, n=516-985 train /
    174-327 val — large samples, decisively dead, not a power problem.
13. **Engulfing reversal** (structure stop via confirmed_swings) — DEAD.
    All 4 configs negative both windows, n=547-1013 train / 182-341 val.
14. **Order blocks** — DEFERRED, not attempted (step57's engine is a
    stateful multi-parameter tracker not worth a partial reimplementation
    this round). Honestly marked not-yet-tested, not folded into a false
    verdict either way. Candidate for a dedicated follow-up round.

## ROUND 173 — native ETH structure: lead/lag, stress-beta, ETH/BTC ratio (2026-07-25)
Full detail: step173_table.csv / step173_eth_native_structure.py. BTC+ETH
1h data inner-joined on timestamp (46,983 overlapping bars, 2021-03 to
2026-07-24).

15. **DIAGNOSTIC — lead/lag cross-correlation** (not a tradeable family,
    a structural fact). corr(ETH return[t], BTC return[t-lag]) peaks at
    lag=0 (corr=0.848) — every other lag from -6h to +6h is under 0.02.
    **ETH does not lead or lag BTC at hourly resolution; the relationship
    is contemporaneous.** Expected given both are liquid 24/7 perps with
    near-instant cross-venue arbitrage, but now actually measured rather
    than assumed — no lag-based ETH-leads-BTC (or vice versa) signal
    exists to exploit at this timeframe.
16. **DIAGNOSTIC — stress beta vs normal beta** (not a tradeable family).
    ETH's normal |move| beta to BTC (all bars, |BTC move|>0.1%): median
    1.16x. ETH's beta specifically during BTC's own panic-dip stress
    windows (4h forward move from trigger, n=1332 events): median 1.11x.
    **STABLE — no material amplification in stress vs normal.** This
    directly informs the live amplifier book: the existing flat vol-
    scaled geometry (1.81%/5.43%) is not obviously mis-sized for a
    stress-specific overshoot, because the data doesn't show one.
17. **NEW native idea — ETH/BTC ratio mean-reversion** (fade divergences
    of ETH's own price from its trailing relationship to BTC; a
    relative-value shape that could not exist as a BTC-only test). 4-cell
    grid (window 168h/720h x z-threshold 1.5/2.0), structure stop via
    confirmed_swings. Train-best cell (720h window, z>=2.0, stop 3.01%):
    train +$336.13/t x49, val +$183.42/t x17 — legitimately SURVIVOR by
    the pre-registered train-only selection rule (this cell also had the
    best TRAIN number among the 4, not merely the best val). **Sealed
    look taken (one look spent): -$111.80/t x18, thickness -6.50x taker
    cost -> SEALED-FAIL.** Exactly the R89 lesson reproduced fresh on a
    brand-new idea: promising train+val, dies at the true out-of-sample
    test. DEAD, not a survivor. The other 3 grid cells all FAILED outright
    (negative val or both windows).
18. **Gas-fee / on-chain network-activity proxies** — INSUFFICIENT-DATA,
    not tested. No on-chain dataset exists anywhere in this repo's cache.
    Honest gap, not a silent skip.

**RUNNING TOTAL, rounds 170-173: 0 survivors on ETH tonight.** 5 BTC-edge
transfers (0/5), 5 cross-market ports (0/5, 2 outright FAIL + 3
FAIL/INSUFFICIENT-SAMPLE), 3 dead-family retests (3/3 confirmed dead,
consistent with BTC), 1 new native idea that reached sealed and failed
there. Two genuine structural findings banked (contemporaneous
correlation, stable stress-beta) that inform the live amplifier book even
without producing a new tradeable signal themselves. ETH has NOT yet
produced a single validated edge of its own beyond the pre-existing
amplifier — reported plainly, per the standing rule that negative results
are wins.
