# Round 134 — cheap dead-confirmation tests: order blocks, candle patterns

Script: `step134_dead_confirmations.py`. Tables:
`step134_table_partA_orderblocks.csv`, `partB_engulfing.csv`. Full
narrative in `step130_family_map.md` rows 18-19.

Already-dead-on-SPX-itself families (always-on shorts, BOS/CHoCH/
sweep-reclaim/confluence) are cited from R60/R77/step130/step132 rather
than re-run — six independent confirmations across two full rounds plus
tonight's own work is stronger evidence than one more cheap test would
add. See this script's module docstring for the exact accounting.

## Results

- **Order blocks** (last down-candle before an ATR-scaled up-impulse, buy
  the return-touch — re-derived, not step57's crypto-wired
  `order_block_engine`): **DEAD**, 15/16 FAIL, 1 INSUFFICIENT-SAMPLE,
  several deeply negative on val (SPY as low as -$51/22t, ES as low as
  -$198/10t).
- **Candle patterns** (bullish/bearish engulfing at a confirmed-swing
  context): bearish engulfing is uniformly dead (0/8 FAIL) — the
  long-bias doctrine's third independent confirmation tonight. Bullish
  engulfing shows a thin SURVIVOR on SPY (0.6x thickness, reject) and a
  thick one on ES (6.1x/23.6x) — but the identical config fails to
  transfer between the two instruments, so the family is marked
  **DEAD** overall per the mandatory cross-instrument-transfer rule.

## Chance baseline

50/50 for both parts (no directional prior).
