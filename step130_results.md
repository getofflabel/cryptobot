# Round 130 — Deliverable 1: intraday structure (opening range, gap, first hour)

Scripts: `step130_intraday_structure.py`, shared plumbing `step130_common.py`.
Data: `data_spx_SPY_1d/1h.parquet`, `data_spx_ES_1d/1h.parquet`,
`data_spx72_ES_15m_smoke.parquet`. Tables: `step130_table_partA_gap_audit.csv`,
`step130_table_partB_gapday.csv`, `step130_table_partC_firsthour_gapcond.csv`,
`step130_table_partD_firsthour_fade.csv`. Full narrative and every number
lives in `step130_family_map.md` rows 1-5 — this file is the short version.

## What was tested and killed

- **Gap-day CONTINUATION and REVERSAL** (custom same-day simulator, entry
  at the gap day's own open, structural stop via `exits.py` or the prior
  close, flatten at the day's own close — explicitly distinct from R60's
  already-dead gap-FILL chase). Both shapes show real-looking, thick
  (5x-42x cost) positive expectancy **on ES=F only**. The identical config
  **fails on SPY** every time except one thin near-miss. Since the
  mandate requires unchanged cross-instrument transfer before anything
  is called validated, and SPY is the deeper, more trusted instrument
  (33y history, the real ETF with a genuine 17.5h dark overnight window),
  both families are marked **DEAD**. Likely explanation: ES=F's own
  unconditioned rest-of-day drift already carries t=2.49 (its
  maintenance-break gap isn't the same phenomenon as SPY's real overnight
  information window, exactly R60's family-2b finding) — the gap-day
  signal is largely riding that baseline drift, not a real gap-direction
  edge.
- **First-hour opening-range breakout, gap-conditioned** (new axis on top
  of R60's own already-partially-validated 2c family): 0/12 SURVIVOR.
  Splitting the sample by gap bucket kills what little edge existed.
- **First-hour range as a fade reference**: 0/2, dies as predicted by
  house doctrine and step99b_exit_research.md's cross-market finding
  that fading a range that's secretly trending gets steamrolled.
- **15m opening range** (ES smoke file, 73 days, ES-only): honestly
  INSUFFICIENT-SAMPLE, not forced into a verdict.

## Chance baselines used

Gap audit unconditioned rest-of-day mean: SPY +0.0024%/day gross (t=0.20),
ES +0.0420%/day gross (t=2.49). Breakout/fade direction: 50/50 coin flip.

## Bottom line

Nothing in this deliverable cleared the bar as a validated, deployable
family. The most useful output is negative: gap DIRECTION does not
predict the rest of the day on the real ETF after costs, extending R60's
gap-fill kill and R77's gap-reaction kill into a third gap-shape grave.
