# ROUND 87 — THE SEALED EXAM: volume-gated Bollinger breakout

**This was a one-shot, irreversible look at the sealed test split (final 20% of
history, chronological) for the config selected in round 86. It has now been
looked at once. It can never be a clean test again for this strategy.**

## Config under test (frozen, unchanged from round 86)

- Signal: Bollinger Band breakout, period 20, 2.5 standard deviations
- Entry gate: the breakout bar's OWN volume >= 1.2x its trailing 20-bar
  average volume, checked only at the flat->nonzero transition bar
- Exit: close back through the band's midline (no fixed stop/target)
- Timeframe: 1h
- Assets: BTC and ETH — one candidate on two assets, not two candidates
- Costs: CostModel defaults (6bps taker / 2bps maker, 1bp half-spread, 2bp
  slippage), execution="maker", real funding via `align_funding` — identical
  to round 86, always on

No parameter was touched. Zero variants were tried on the sealed slice.

## Code provenance (hard rule 1)

`step87_sealed_breakout.py` imports, and does not retype:
- `bollinger_breakout_signal`, `volume_gate_entry`, `BREAKOUT_CONFIGS`,
  `load_frames`, `build_meta` — all from `step86_specified.py`
- `score`, `split_points` — from `step43_daytrade.py` (step86's own import
  source), used to reproduce the identical train/val split and scoring call
- `run_backtest` — from `backtest.py`, called with the same argument shape
  `score()` uses internally (`execution="maker"`, `stop_pct=None,
  target_pct=None`, real `funding_series`), just pointed at the sealed slice
  `[i_va:n]` instead of `[0:i_tr]` / `[i_tr:i_va]`

The only new code is the reproduction check and the test-slice runner
(`run_test_slice`), which is a verbatim copy of `score()`'s inner `run()`
closure retargeted at the sealed index range.

## Reproduction check (hard rule 2) — MUST PASS before trusting the sealed numbers

Re-ran round 86's exact train and val numbers for this exact config, same
cached data, same split:

| Asset | Split | Reproduced | R86 reported | Result |
|---|---|---|---|---|
| BTC | train | $14.87/trade (n=772) | $14.87/trade | **MATCH** |
| BTC | val   | $5.21/trade (n=254)  | $5.21/trade  | **MATCH** |
| ETH | train | $39.59/trade (n=647) | $39.59/trade | **MATCH** |
| ETH | val   | $26.01/trade (n=195) | $26.01/trade | **MATCH** |

Trades/year (train+val pooled): BTC 202.6 (reported ~203), ETH 196.4
(reported ~196) — also match.

**REPRODUCTION CHECK: PASSED.** The split and the signal did not drift.
Proceeding to report the sealed slice as a clean read.

## Sealed test result — the headline

### BTC

| Metric | Value |
|---|---|
| Trades | 242 |
| Calendar span | 2025-04-18 to 2026-07-24 (~15.3 months) |
| Expectancy/trade (after costs) | **+$6.97** |
| Total PnL | +$1,687.38 |
| Win rate | 36.4% |
| Avg win | +$196.81 |
| Avg loss | -$101.51 |
| Trades/year | 191.2 |
| Max drawdown | -23.33% |
| Longest losing streak | 11 trades |
| **Verdict** | **PASS** |

### ETH

| Metric | Value |
|---|---|
| Trades | 226 |
| Calendar span | 2025-06-28 to 2026-07-24 (~13.0 months) |
| Expectancy/trade (after costs) | **+$9.68** |
| Total PnL | +$2,188.75 |
| Win rate | 37.6% |
| Avg win | +$319.61 |
| Avg loss | -$177.15 |
| Trades/year | 210.9 |
| Max drawdown | -35.01% |
| Longest losing streak | 6 trades |
| **Verdict** | **PASS** |

### Pooled (BTC + ETH)

| Metric | Value |
|---|---|
| Trades | 468 |
| Total PnL | +$3,876.13 |
| Expectancy/trade (after costs) | **+$8.28** |
| Win rate | 37.0% |
| **Verdict** | **PASS** |

## Side-by-side: train vs val vs SEALED

| Asset | Train $/trade (n) | Val $/trade (n) | **SEALED $/trade (n)** | Trades/yr (test) |
|---|---|---|---|---|
| BTC | $14.87 (772) | $5.21 (254) | **$6.97 (242)** | 191.2 |
| ETH | $39.59 (647) | $26.01 (195) | **$9.68 (226)** | 210.9 |

## Verdicts

- BTC: **PASS** — positive expectancy after costs on the sealed slice
  ($6.97/trade).
- ETH: **PASS** — positive expectancy after costs on the sealed slice
  ($9.68/trade).
- Overall / pooled: **PASS** ($8.28/trade pooled, both legs individually
  positive).

## Honest read on the degradation

BTC and ETH degraded in genuinely different ways, and it's worth being
precise about each rather than averaging them into one story.

**BTC looks like normal shrinkage, arguably even reassuring.** Train
$14.87 -> val $5.21 -> test $6.97. The big drop already happened between
train and val — that's the round-86 selection event doing what train/val
splits are supposed to do (punish overfitting to the training window). From
val to test the number actually held roughly steady, even ticked up
slightly ($5.21 -> $6.97). Two out-of-sample-in-a-row readings landing in
the same $5-7/trade neighborhood, on 242 sealed trades, is the kind of
consistency you want to see before trusting a number. Win rate (36.4%) and
avg win/avg loss shape are plausible for a breakout system (small edge in
frequency of losses, offset by larger average wins) — nothing here smells
like a fluke concentrated in a handful of trades. Max drawdown -23.3% and
an 11-trade losing streak are real and would need to be sized for, but nothing
about the shape screams broken.

**ETH is a genuinely worse story and deserves to be called that plainly.**
Train $39.59 -> val $26.01 -> test $9.68. That is two consecutive halvings.
Unlike BTC, where the big drop was between train and val (the expected
place for it) and the val->test step was flat, ETH kept bleeding through
val into test — the edge is on a visible downward trend across all three
windows, not settling into a plateau. $9.68/trade on ETH is still positive
and clears both the sample-size floor and the exam's PASS bar, but it is
close enough to zero, and moving in the wrong direction fast enough, that I
would not be surprised if the next unseen window is a loser. -35% max
drawdown on ETH is also materially worse than BTC's, on a strategy with no
fixed stop (exits purely on the midline cross) — this is a genuinely painful
ride, not a smooth one.

**Bottom line:** BTC passes cleanly and looks durable — two independent
out-of-sample reads agree. ETH passes on paper but the trend line points at
zero, and I would treat the ETH leg as fragile rather than validated; if
this were sized for live capital I would weight BTC more heavily than ETH,
or watch the next few months of ETH performance closely before trusting
$9.68/trade as the number to plan around, since the sequence (val to test)
looks like the edge evaporating slowly rather than shrinking-then-stabilizing.

## Future proposals (NOT tested — sealed data was not touched for these)

Per hard rule 4, no variant was run on the sealed slice. If a next round is
warranted, these are candidates to test cleanly on fresh/rolled-forward data
rather than by re-touching this now-burned test window:
- A trailing/ATR-based stop on top of the midline exit, given the -23%/-35%
  drawdowns with no fixed stop currently in place
- Re-running this exact frozen config on a rolled-forward window (new bars
  accumulated since this test was sealed) to get a second, still-clean read
  on ETH specifically
- Position-size weighting BTC vs ETH unequally given the divergent
  degradation pattern, decided on economics/risk grounds rather than by
  re-selecting on this test slice

## Files

- `step87_sealed_breakout.py` — the exam script (imports step86's signal/gate
  functions and step43's score/split_points; only new code is the
  reproduction check and the sealed-slice runner)
- `step87_results.md` — this write-up
- `step87_table.csv` — every individual trade (train + val + test, both
  assets, 2,336 rows), tagged by `asset` and `split` column
