# Round 135 — exit-method iteration on the two already-validated SPX edges

Script: `step135_exit_variations.py`. Tables:
`step135_table_partA_dipbuy_exits.csv`, `partB_regime_exits.csv`. Full
narrative in `step130_family_map.md` rows 16-17.

First real use of `exits.py`'s composable `SeriesCtx`/`TradeCtx`/
`run_trade`/`simulate_partial_scale` engine on SPX — every prior SPX round
(R60, R77, and step130-134 tonight) used `backtest.py`'s flat
`stop_pct`/`target_pct` scalar only.

**Important caveat stated once here, applies to both tables**: these
custom simulators use FLAT, non-compounding notional per trade (each
trade sized against `INITIAL_EQUITY`, matching the "edge as % of
notional" convention the task's evidence bar asks for), while R60's own
`run_backtest`-based numbers COMPOUND equity trade-to-trade. Dollar
figures between the two are therefore not directly comparable — sign,
verdict, and thickness multiple are.

## Part A — RSI2<5 dip-buy, stop variants (same entries, same original target)

Every real stop method tested — `stop_atr(1.5)`, `stop_chandelier(3.0)`,
`stop_structure_trailing()`, `stop_breakeven_after_r` — stays SURVIVOR on
SPY (7.5x-19x train, 6.4x-9.8x val) and on ES=F except partial-scale.
**The dip-buy edge is robust to exit-method choice** — a new, useful
finding: nothing in the exits.py library breaks it, and nothing
meaningfully improves on R60's original simple exit either.

Partial-scale (50% off at 1R, move to breakeven, ride the rest) is
INSUFFICIENT-SAMPLE on ES=F specifically because the trade count drops
~48% (28 vs 43-46) — a partial, honest replication of
`step99b_exit_research.md`'s cross-market finding that scaling out costs
roughly half the profit, here manifesting as fewer completed round trips
rather than smaller per-trade dollars (this sim doesn't reduce notional
on the scaled-out leg, so it isn't a full capital-efficiency test).

## Part B — SMA200-regime + structure-trailing early-out

Adding a chart-structure early-out on top of R60's validated
continuous-membership rule **hurts**: SPY flips from SURVIVOR
(58.0x/23.7x) to FAIL (23.7x/**-3.8x**, sign flip on val); ES=F stays
SURVIVOR but far weaker (81.1x/244.1x -> 51.7x/35.3x). Confirms the
"give it room" lesson R60 found for dip-buy stops generalizes to the
slow regime backbone too.

## Chance baseline

R60's own no-stop/1.5xATR dip-buy baseline and continuous-membership
regime baseline, reproduced internally as the comparison points for
parts A and B respectively.
