# Round 131 — Deliverable 2: turn-of-month, built into a real strategy

Script: `step131_turn_of_month.py`. Tables: `step131_table_strategyA/B/C/D/D2.csv`.
Full narrative and every number lives in `step130_family_map.md` rows 6-9.

## The headline result

**Turn-of-month IS now a validated, cross-instrument-confirmed strategy —
but only with the WIDER window, not the textbook one.**

- The standard Xu-McConnell window (last trading day of month + first 3 of
  the new month — what R60 audited at t=2.43, and what this task asked me
  to build first) **fails on SPY val** (train looks great, val flips
  negative, -1.6x thickness) despite passing on ES=F and QQQ. Since SPY
  is the primary, deepest-history instrument, this is marked DEAD. This
  independently reproduces almost exactly a config already in
  `step77_spx_playbook.py` (its "N=2d" row, val expectancy -6.260437 vs
  this script's -6.260 — a coincidence-proof cross-check that the
  negative result is real, not a bug).
- Mid-session discovery: **`step77_spx_playbook.py` (an earlier SPX round
  not mentioned in tonight's brief) already found a WIDER window (3
  trading days before month-end through 3 into the new month) survives
  on SPY** — but never tested it on ES=F or QQQ. Strategy D replays that
  exact config, unchanged, on both. **It transfers cleanly**: SPY
  6.6x-12.8x thickness, ES=F 6.9x-42x, QQQ 10.3x-26.3x, all comfortably
  above the 5x bar, all comfortably above the 30/8 trade minimum (SPY
  240/81, ES 186/62, QQQ 197/65). Strategy D2 adds a literal
  `exits.py stop_structure(k=5)` chart-structure stop (R77's own version
  only used "none" or a flat 2xATR) — the edge survives on all three
  instruments, though the structural stop thins SPY's val thickness to
  3.95x (just under the reject line) while leaving ES/QQQ thick.
- Overlaying TOM onto the already-validated RSI2<5 dip-buy (Strategy C,
  R60's own suggested next test) does **not** help — it either shrinks
  the sample below the trade minimum or flips negative on SPY; the one
  promising cell fails cross-instrument transfer.

## Chance baseline

Unconditioned SPY daily mean: +0.0257%/day, t=1.65 (R60). The narrow
window's own audit t-stat was 2.43 — real, but the strategy built on it
literally doesn't survive an honest forward split on the ETF.

## Recommendation

The **wide TOM window (3 days before month-end through 3 into the new
month), no stop or a 2xATR stop**, SPY+ES=F+QQQ, is this round's strongest
deployable candidate — cross-instrument confirmed, thick, well above the
minimum sample bar, ~12 trades/yr per instrument. Still knowledge-banked
only (no venue exists yet), but it is the first genuinely validated
NEW-frequency addition to the book beyond the original panic-buy trigger.
