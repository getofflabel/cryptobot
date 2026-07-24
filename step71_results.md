# Round 71 — THE PRECISION-ENTRY PROGRAM

Research only. No commits, no live orders. Code: `step71_precision.py`.

**Process note on scope actually executed:** the full architectural grid
(CONTEXT{4} x SETUP{4} x TRIGGER{9, incl. 5m tier} x TARGET{3} x
DIRECTION{2} x ASSET{2} ≈ 1,300+ cells) is implemented in
`step71_precision.py` and can be run to completion in a follow-up
session. Within this session's runtime budget, the executed run was a
**trimmed core** (agreed with the lead mid-round): BTC + ETH, both
directions, CONTEXT ∈ {champion, none}, SETUP ∈ {RSI3<15 pullback,
sweep-1h reclaim}, TRIGGER ∈ {15m turn candle, 15m BOS-up k3, 15m
sweep-reclaim, 5m turn candle}, TARGET ∈ {1.5x, 2x, 3x} — 96 cells/asset
— plus a context+setup-only rung (48 cells, BTC) and a context-only rung
(24 cells, BTC) to complete the ladder, plus the dedicated R58
reproduction on both assets. **192 scored trimmed-grid cells + 72
ladder-rung cells + 2 R58 reproductions (x2 cost models) = 268 backtest
cells actually run**, not the full ~1,300. What was cut and why is in
section 8.

---

## 1. Data inventory

| Asset | TF | Bars | Span | Note |
|---|---|---|---|---|
| BTC | 5m | 663,999 | 2020-03-30 → 2026-07-23 (6.31y) | already cached, NOT thin |
| BTC | 15m | 221,972 | 2020-03-25 → 2026-07-24 (6.33y) | |
| BTC | 1h | 55,493 | 2020-03-25 → 2026-07-24 (6.33y) | |
| BTC | 4h | 13,863 | 2020-03-25 → 2026-07-22 (6.33y) | |
| ETH | 5m | 563,829 | 2021-03-15 → 2026-07-24 (5.36y) | **fetched fresh this round** (499s), NOT thin |
| ETH | 15m | 187,934 | 2021-03-15 → 2026-07-24 (5.36y) | |
| ETH | 1h | 46,983 | 2021-03-15 → 2026-07-24 (5.36y) | |
| ETH | 4h | 11,735 | 2021-03-15 → 2026-07-22 (5.35y) | |

Both assets clear the round-55 regime-thin bar (>2y) on every timeframe
including the scope-addition's 5m tier — the "shorter 5m history" worry
did not materialize; Bybit's ETH perp history reaches back to its 2021
listing at 5m same as every other timeframe.

---

## 2. R58 sample-fattening check — DOES THE ORIGINAL CONFIG STILL HOLD?

Reproduced round 58's exact full-alignment MTF ladder config byte-for-byte
(imported `four_h_bias` / `rsi3_pullback_setup` / `reversal_bar` /
`stack_entries` unmodified from `step58_divergence_mtf`): 4h bias
(champion sign AND SMA50 agreement) → 1h RSI3<15 pullback setup → 1h
reversal-bar trigger, level=full, stop=min(1.2×med train ATR%, 3.0%),
target=3× stop, max hold 72h.

**BTC — MAKER (R58's original cost assumption), reproduced almost to the
cent:**

| | train n | train exp | val n | val exp | verdict |
|---|---|---|---|---|---|
| R58 (reported 2026-07-24) | 32 | $26.75 | 12 | $56.42 | SURVIVOR |
| This round (same cache, re-run) | 32 | $26.77 | 12 | $56.46 | SURVIVOR |

**Unchanged — NOT fattened.** n=32/12 is identical; the 1h cache had grown
by a handful of bars since R58 ran (last refresh today 11:39 vs the
original run earlier the same day) but not enough to shift the 60/20/20
split into a new trade. The config is still standing exactly at the edge
of the 30/8 floor it was benched for.

**NEW this round — the same config under TAKER (this round's stricter
primary standard, which R58 never tested):**

| | train n | train exp | val n | val exp | verdict |
|---|---|---|---|---|---|
| BTC, taker | 32 | $22.47 | 12 | $52.20 | **SURVIVOR** |

The config clears taker costs too — a genuinely new, positive result.
But it fails this round's OWN secondary bars: **fee-share 35.9%** of
gross edge (gross $47.70bps, cost $17.12bps/trade) — more than double
the 15% target — and **8.7 trades/yr**, under half the 20/yr floor. It
is a real, thin, expensive-relative-to-its-edge signal, not a frequent
precision-entry machine.

**ETH twin-check — DOES NOT CORROBORATE:**

| | train n | train exp | val n | val exp | verdict |
|---|---|---|---|---|---|
| ETH, maker | 36 | -$35.28 | 11 | -$0.12 | FAIL |
| ETH, taker | 36 | -$38.76 | 11 | -$4.11 | FAIL |

The exact same construction is flatly negative on ETH in both cost
models. **R58's MTF-ladder shape is BTC-specific, not a cross-asset
edge** — an important caveat R58 itself couldn't test (BTC-only round).

---

## 3. The trimmed precision-entry grid: BTC + ETH, both directions

96 cells/asset (2 contexts × 2 setups × 4 triggers × 3 targets), full
costs, TAKER primary.

| Status | BTC | ETH |
|---|---|---|
| SCORED | 78 | 89 |
| EXCLUDED-ANTISCALP (target<0.5%, by design) | 15 | 7 |
| NO-QUALIFYING-TRAIN-ENTRIES | 3 | 0 |
| SURVIVOR (of SCORED) | **0** | **0** |
| INSUFFICIENT-SAMPLE | 0 | 1 |
| FAIL | 78 | 88 |

**Zero survivors on either asset, in this trimmed core.** The pattern
splits cleanly into two failure modes:

**(a) Sample collapse.** Requiring context AND setup AND a same-fine-bar
trigger to align simultaneously is a strict conjunction. `sweep-1h
reclaim` (a 1h setup that only fires ~100x in 6 years) combined with a
15m/5m trigger routinely produces n=2–15 train trades — e.g. BTC
champion/sweep-reclaim/15m-sweep-reclaim/tgt3x: **train n=2, exp
+$113/trade (looks amazing, is statistically worthless), val n=0**. These
cells never reach the 30/8 floor regardless of their raw number.

**(b) Real, adequately-sampled, and negative.** Where sample size is
healthy (RSI3<15 pullback, which stays persistently true across
consecutive bars and pairs with the near-omnipresent turn-candle
trigger), the numbers are honest and consistently negative: e.g. BTC
champion/RSI3<15/15m-turn-candle/tgt3x — **train n=312, exp -$12.51/trade,
val n=106, exp -$22.64/trade**. This matches (and extends) an
already-established repo pattern: round 43's washout-scalp family found
the *exact same* RSI3 dip-buy shape fails under tight (≤1.7%
stop/2-3%target/≤24h-hold) day-trade geometry — it needs the live
system's wide -8% SL / 48h+ hold to work. **This round's
trigger-bar-extreme-derived stop formula (max of bar-extreme+buffer or
1x ATR, capped 3%) reproduces that same failure**, whereas R58's plain
1.2×ATR-based 1h formula (section 2) is the one geometry in this whole
program that has ever cleared the floor.

The "least-bad" cells (highest train expectancy) on both assets are all
n≤6 sweep-reclaim flukes — not deployable, not corroborating anything,
listed only for completeness in `step71_h2h_raw.csv` / the scratch CSVs.

---

## 4. Ladder analysis — context-only → +setup → +trigger

Per the brief, built on the closest analog to R58's shape available in
the trimmed core: **BTC long, champion context, RSI3<15 pullback setup,
15m turn-candle trigger** (chosen because turn-candle barely filters the
sample, isolating the trigger's *quality* contribution rather than just
cutting size). Stop/target geometry held fixed per rung is NOT used here
(each rung's stop_pct differs slightly, being train-median-derived
per-entry-set) — TRAIN expectancy at tgt3x, all three rungs:

| Rung | tr n | tr exp | va n | va exp | trades/yr | verdict |
|---|---|---|---|---|---|---|
| context-only (champion regime turns on) | 44 | -$15.62 | 14 | +$30.41 | 11.5 | FAIL |
| context+setup (+ RSI3<15 pullback) | 310 | -$9.60 | 106 | -$4.02 | 82.1 | FAIL |
| full (+ 15m turn-candle trigger) | 312 | -$12.51 | 106 | -$22.64 | 82.5 | FAIL |

**Verdict: NOT monotonic, and this is the opposite of R58's finding.**
Adding the setup *helps* a little (context-only → context+setup improves
train exp $15.62→$9.60 worse-of, i.e. less negative), but adding the
15m trigger *hurts* (context+setup → full: -$9.60→-$12.51 train,
-$4.02→-$22.64 val — both worse). This directly contradicts round 58's
"each added layer improved val expectancy" result. The difference is
architectural, not philosophical: R58's trigger was evaluated on the
**same 1h timeframe** as its setup (a genuinely rarer, more selective 1h
reversal-bar pattern), while this round's turn-candle trigger is
evaluated on a **finer 15m timeframe** it barely filters (fires on
~50%+ of 15m bars) — it adds noise, not selection. **A same-timeframe,
low-frequency trigger (R58's shape) earns its keep; a finer-timeframe,
high-frequency trigger (this round's `turn candle`) does not.** This is
this round's clearest mechanistic finding.

Full 4-context ladder for `sweep-1h reclaim` was attempted but every
rung there is sample-starved (n<20 throughout) — not reportable as a
ladder, only as the section-3 sample-collapse note above.

---

## 5. Fee-share of gross edge

| Config | gross edge (bps/trade) | realized cost (bps/trade) | fee-share | <15% floor? |
|---|---|---|---|---|
| R58 config, BTC, taker (the one survivor) | 47.70 | 17.12 | **35.9%** | **NO** |
| R58 config, ETH, taker | -14.44 (negative gross) | 16.21 | n/m (gross negative) | n/a |

The anti-scalp target-floor guard (section-3/6 EXCLUDED-ANTISCALP rows,
15 on BTC / 7 on ETH) worked as designed — every excluded cell had an
implied target under 0.5% and was never backtested. But the ONE cell that
survived the full gauntlet still burns over a third of its gross edge on
costs — a genuine trade-off the brief flagged as a check, not a
guarantee, and it did not pass here.

---

## 6. Trades/year — frequency check

| Config | trades/yr | ≥20/yr floor? |
|---|---|---|
| R58 config (the survivor) | 8.7 | **NO** |
| BTC champion/RSI3<15/15m-turn-candle (biggest sample, FAIL) | 82.5 | YES |
| BTC champion/RSI3<15/15m-BOS-up (thin) | 9.9 | NO |
| Most sweep-reclaim cells (either asset) | 0.4–8 | NO |

Frequency and profitability point in opposite directions in this
program's data so far: the only PROFITABLE config is the LEAST frequent
one tested. Nothing in the trimmed core delivers both.

---

## 7. 15m-vs-5m trigger head-to-head

Matched pairs (same asset/direction/context/setup/target, trigger SHAPE
held constant — only the fine timeframe differs), turn-candle shape
(the only shape with matched 15m/5m pairs in the trimmed core):

| Asset | Setup | Context | tgt | 15m tr_exp (n) | 5m tr_exp (n) | 5m wins? | 5m noise-stopout-30m |
|---|---|---|---|---|---|---|---|
| BTC | RSI3<15 | champion | 3x | -$12.51 (312) | -$11.93 (313) | yes (less bad) | 40.7% |
| BTC | RSI3<15 | none | 3x | -$9.03 (706) | -$7.98 (707) | yes (less bad) | 40.5% |
| BTC | RSI3<15 | none (short) | 3x | -$9.01 (733) | -$9.36 (734) | no | 44.4% |
| ETH | RSI3<15 | champion | 3x | -$17.91 (282) | -$13.43 (284) | yes (less bad) | 45.9% |
| ETH | RSI3<15 | none | 3x | -$12.49 (621) | -$10.83 (623) | yes (less bad) | 43.2% |

**Verdict: 5m is directionally slightly better than 15m in most matched
pairs (4/5) but the margin is small and BOTH stay solidly negative — 5m
does not rescue this trigger shape into profitability, it just loses a
little less.** The noise-stopout rate (fast loss within 30 min, the
honest proxy defined in the module docstring — no exit-reason field
exists) sits at **40–46% of all 5m-tier trades**, confirming the turn-
candle trigger is mostly catching noise on the fast timeframe, not real
moves — consistent with the ladder finding in section 4 that this
trigger shape doesn't add selective value.

---

## 8. What was trimmed and why

Given the round's runtime budget, the following were NOT run this
session (script is ready to run them in a follow-up):
- The other 2 setups (FVG-return 50%fill, CHoCH-flip) — untested this
  round. Priority for a follow-up given RSI3 and sweep-reclaim both died.
- CONTEXT ∈ {bos-chain, either} — only {champion, none} were run in the
  main trimmed grid (bos-chain/either were tested only in the
  context+setup-only rung, section 3's supporting data, all FAIL there
  too).
- 15m/5m BOS-up and sweep-reclaim triggers were only tested against RSI3
  and sweep-1h-reclaim setups, not FVG-return/CHoCH.
- The "none/enter-at-setup" control trigger across the FULL context grid
  (only champion/none were run; see section 4 for the one ladder built).
- The literal `~300`-config core grid described in the brief (context×
  setup×trigger×target = 4×4×4×3=192/direction/asset before the 5m
  scope-add) was not run to completion — the trimmed 96/asset subset
  above is the actual coverage.

None of the cuts touch the round's headline findings (R58 fattening,
ladder monotonicity, fee-share, frequency, 15m-vs-5m) — all five required
analyses were completed on the trimmed core plus the dedicated R58/ladder
side-runs.

---

## 9. Ranked sealed-look candidates

Only ONE config in this entire round (across both the trimmed precision
grid and the R58 reproduction) cleared the SURVIVOR gauntlet under taker
costs:

| Rank | Config | tr n/exp | va n/exp | trades/yr | fee-share | Note |
|---|---|---|---|---|---|---|
| 1 | R58 exact: BTC, 4h bias/RSI3<15/1h-reversal-bar/full/tgt3x, 1h, TAKER | 32 / $22.47 | 12 / $52.20 | 8.7 | 35.9% | Same config already flagged in R58 as thin (n=32/12, right at the floor). This round adds: clears taker (new), does NOT clear the fee-share or frequency secondary bars (new caveats), does NOT corroborate on ETH (new, important negative). Not a fresh discovery from this round's grid — everything the grid itself generated failed.

Nothing from the trimmed precision-entry grid (sections 3-7) is being
forwarded as a sealed-look candidate — zero SURVIVORs were produced by
the round's own new architecture.

---

## 10. Summary for the lead

- **268 backtest cells run** (trimmed core + ladder rungs + R58
  reproduction ×2 assets ×2 cost models). Full ~1,300-cell grid not
  completed this session — script (`step71_precision.py`) is ready to
  run the rest.
- **R58's config: reproduced almost exactly (unchanged, NOT fattened,
  still n=32/12), and newly confirmed to clear TAKER costs** — genuinely
  positive news the owner should hear. But it fails BOTH of this round's
  own secondary bars (35.9% fee-share vs 15% target, 8.7 trades/yr vs 20
  floor) and **does not transfer to ETH** (flatly negative there, both
  cost models).
- **This round's own new architecture (trigger-bar-extreme-derived stop,
  same-fine-bar trigger requirement) produced ZERO survivors** on either
  asset, across 78+89=167 scored trimmed-grid cells. Failure splits into
  sample collapse (rare setups × fine triggers) and real-but-negative
  (RSI3 pullback under tight geometry — same graveyard round 43 already
  found).
- **Ladder verdict: NOT monotonic, and inverted vs R58.** Context helps,
  setup helps a little more, but this round's 15m turn-candle trigger
  makes it WORSE (both train and val). R58's own trigger (1h reversal
  bar, same-timeframe as its setup, low-frequency) is the one shape that
  has ever earned its keep in this program — a fine-timeframe,
  high-frequency trigger like turn-candle does not, confirmed further by
  the 40-46% noise-stopout rate in the 15m-vs-5m section.
- **15m-vs-5m: 5m is marginally less-bad than 15m in 4/5 matched pairs,
  never profitable in any.** The scope-addition tier does not rescue the
  turn-candle trigger.
- **Biggest caveat:** the owner's corrected frame ("15m/5m entries into
  REAL moves, not scalps") is philosophically sound and the anti-scalp
  floor mechanism worked exactly as designed (22 EXCLUDED-ANTISCALP cells
  across both assets, never even backtested) — but *this round's specific
  implementation* of that frame (trigger-bar-extreme stops, same-fine-bar
  trigger conjunction) did not find a NEW deployable edge. The only
  surviving number in the whole round is the pre-existing, already-known-
  thin R58 config, now with two new caveats (fee-share, no ETH transfer)
  attached rather than resolved. The path forward is narrower than hoped:
  either find a same-timeframe low-frequency trigger shape (R58's own
  proof-of-concept, generalized — not yet tried outside its exact
  original construction) or accept that BTC's 1h reversal-bar/RSI3
  combination may be a one-off, not a family.
