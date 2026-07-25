# Round 133 — more SPX native calendar structure

Script: `step133_native_structure.py`. Tables:
`step133_table_partA1_expiry_audit.csv`, `partA2_expiry_strategy.csv`,
`partB_gap_range.csv`. Full narrative in `step130_family_map.md` rows 14-15.

## Results

- **Options-expiry week** (week containing the month's third Friday;
  quarterly quad-witching flagged separately) — genuinely new to this
  program. Audit: the expiry week's own t-stat is actually WEAKER than
  the non-expiry-week baseline on SPY (1.13 vs 2.28) — no standout
  signal. Strategy: inconsistent cross-instrument transfer (monthly
  window SURVIVOR on SPY+QQQ but FAILS on ES with a calendar exit; adding
  a 1.0xATR stop flips ES to SURVIVOR but flips QQQ to FAIL). No single
  config clears 5x thickness on both windows for all three instruments.
  **DEAD as a standalone strategy.**
- **Gap magnitude vs same-day intraday range** (report-only, distinct
  from step130's gap-DIRECTION test): a real, simple, useful finding —
  correlation 0.52 on SPY / 0.26 on ES between |gap%| and the day's own
  realized range; big-gap days run ~1.3-1.5x wider than small-gap days.
  Not a standalone trade — a stop-sizing input, marked SURVIVOR in that
  narrower sense.

## Chance baselines

Unconditioned daily mean (R60: +0.0257%/day, t=1.65) and the directly
computed non-expiry-week baseline (t=2.28, stronger than expiry week
itself) for part A; corr=0 (no relationship) for part B.
