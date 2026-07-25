# Round 117 — Oil breakout entry-lookback sweep (5–55) x exit library

**Trigger:** CL=F ran +29.8% in three weeks; the live oil book (`tradfi_engine`
running `daily_pick`'s 2-hour-slot CRYPTO scorer, borrowed rules never
certified on oil) caught one 135-minute trade worth $58.39. Round 110
already proved that borrowed-rules book negative on oil and it is stood
down — **that question is closed, not reopened here.** This round answers
the follow-on: was the miss a wrong-tool problem specifically fixable by a
trend-following breakout system at a SHORTER lookback than the donchian(55)
round 116 already found a near-miss (2.36x cost)? Wallace's own eyeball
(explicitly flagged as not evidence) pointed at donchian-10/donchian-20 with
an EMA20 exit, both showing open gains right now.

`execution="taker"` throughout. All stops are `exits.py` structural levels
(never a swept percentage); size = risk$/stop distance, leverage an output
(capped at the desk's 20x ceiling). 60/20/20 chronological split,
train-only selection, val read exactly once per timeframe, sealed 20%
never loaded by this file.

**Important context on the split:** on CL=F daily, train = 2000-08-23 to
2016-03-16, val = 2016-03-17 to 2021-05-19 (includes the April 2020
negative-WTI-price event), sealed = 2021-05-20 to 2026-07-24 — **the
actual +29.8% three-week move that provoked this round sits entirely
inside the sealed 20% and was never touched by selection.** That is
correct discipline, not an oversight: this round tests whether the
SYSTEM has a real edge, not whether it would have caught that one
specific move.

## The grid

11 lookbacks (5,10,15,20,25,30,35,40,45,50,55) x 7 exits
(`structure_trail`, `ema20_cross`, `ema50_cross`, `chandelier2.5`,
`chandelier3.0`, `chandelier3.5`, `chandelier4.0`) = 77 cells per
timeframe, run on CL=F 1d and CL=F 1h (intraday — note "55" there means
55 HOURS, not days; 1h data only spans 2024-03→2026-07, 2.40 years).
Full grid: `step117_table.csv` (154 rows).

### CL=F daily — top cells by TRAIN expectancy

| lookback | exit | train n | train exp/t |
|---|---|---|---|
| 20 | chandelier2.5 | 152 | +$23.19 |
| 25 | chandelier2.5 | 133 | +$22.13 |
| 45 | chandelier2.5 | 98 | +$21.20 |
| 40 | chandelier2.5 | 104 | +$18.73 |
| 5 | chandelier3.0 | 186 | +$17.32 |
| 15 | chandelier2.5 | 171 | +$17.26 |
| 35 | structure_trail | 71 | +$15.69 |
| 50 | chandelier2.5 | 96 | +$14.64 |

**The clean, unambiguous shape in this grid: `ema20_cross` and
`ema50_cross` are NEGATIVE on TRAIN at every one of the 11 lookbacks
tested, no exceptions.** Wallace's eyeballed EMA20-exit trades
(donchian-10 and donchian-20, both currently open and green) are real
individual trades sitting inside a system that is expectancy-negative on
average across its full 26-year train history. A currently-winning trade
is not evidence the system is positive expectancy — this grid is the
direct, sobering check on that eyeball, and it fails.

`structure_trail` and `chandelier2.5` are the two exits that show a
genuine positive shelf, starting around lookback 15–20 and holding through
55. `chandelier3.0`/`3.5`/`4.0` are mixed (positive at very short
lookbacks, negative in the middle, occasionally positive again).

**Selected on TRAIN only:** donchian(20) + chandelier(2.5x ATR), train
n=152 exp=+$23.19/t.

**Plateau check (train numbers, val still unread at this point):**
- lookback 15 (same exit): n=171, +$17.26 — OK
- lookback 25 (same exit): n=133, +$22.13 — OK
- chandelier3.0 (same lookback): n=130, +$5.58 — OK

**Verdict: PLATEAU**, not a spike. This is a real, structurally broad
result on train — round 88's "lone-setting" failure mode does not apply
here. It still does not survive what comes next.

**VAL (read once):** n=48, exp=+$21.02/t, win%=43.8, hold≈252h (median),
avg leverage 0.4x.

**Thickness (val):** 0.46% of notional | **3.85x fees-only 12bps** |
**2.56x full CostModel ~18bps**. Both readings are **under the 5x bar —
REJECT.** This is a real improvement over round 116's donchian(55) near-miss
(2.36x on the full CostModel basis) but still doesn't clear.

**Chance baseline (val, 100 random-entry draws, identical exit apparatus,
identical event count and direction mix):** mean **+$56.30/t** — HIGHER
than the real signal's +$21.02/t. **The donchian entry does not beat
random entry under the same trailing-stop exit.** This is the single most
important finding of the round: most of what looked like "edge" in this
cell is coming from the EXIT apparatus (a wide chandelier trail that lets
big oil trend legs run) riding a long-run generally-rising commodity
series, not from the donchian breakout's entry TIMING. A dumb, randomly-
timed entry with the same trailing stop does at least as well. That is
not a tradeable signal, that is regime drift.

**Data-quality note:** one of the 48 val trades (2020-04-20 short, exit
2020-04-21) touches the historic negative-WTI-settlement day; entry/exit
prices go negative, producing a mathematically valid but non-repeatable
+$163 trade (16% of total val P&L; excluding it, val expectancy drops to
≈+$18/t, still thin, still fails the chance/thickness bars — this does not
change the verdict). That specific price mechanic cannot recur on
BloFin's perpetual, USDT-margined WTIOIL-USDT — flagged for completeness,
not because it drives the result.

**Trades/year (train+val combined): 9.64/yr.** Even if this had cleared,
it is a slow trend book (~1 trade every 5 weeks), not a system that would
routinely catch a three-week spike — it would catch SOME of them, on a
lag, roughly 10x a year.

### CL=F 1h (intraday) — top cells by TRAIN expectancy

| lookback (hrs) | exit | train n | train exp/t |
|---|---|---|---|
| 35 | chandelier3.0 | 237 | +$42.77 |
| 30 | chandelier3.0 | 245 | +$40.19 |
| 25 | chandelier3.0 | 260 | +$25.67 |
| 20 | chandelier3.0 | 313 | +$16.79 |
| 15 | chandelier3.0 | 377 | +$11.39 |

Only `chandelier3.0` shows any train-side life, and only at 15–35 hours;
every other exit (`structure_trail`, `ema20/50_cross`, `chandelier2.5`,
`3.5`, `4.0`) is negative at every intraday lookback tested. Only 9 of 77
cells cleared the train floor+positive filter (vs 30/77 on daily) — the
intraday signal is much thinner ground to begin with.

**Selected on TRAIN only:** donchian(35h) + chandelier(3.0x ATR), train
n=237 exp=+$42.77/t.

**Plateau check:** lookback 30 (same exit) OK (+$40.19); lookback 40 same
exit FAILS (-$15.14); chandelier2.5 same lookback FAILS (-$8.36);
chandelier3.5 same lookback FAILS (-$8.02). **Verdict: PARTIAL-PLATEAU
(1/4 neighbors pass)** — meaningfully more fragile than the daily result;
this is close to the "effect exists at exactly one setting" pattern round
88 killed a live change for.

**VAL (read once):** n=64, exp=**-$35.00/t** — sign-flips negative.
**Verdict: FAIL.** Thickness is negative (-1.72x fees-only /
-1.15x full CostModel). Chance baseline for context: -$24.76/t (the real
signal is WORSE than random entry with the same exit, not just failing to
beat it). Trades/year would have been 155.95/yr — the exact opposite
problem from the daily result: this is a fast, choppy, over-trading
system, not remotely capable of holding a multi-week directional move
either.

## Cross-instrument transfer (mandatory for any survivor; run here on
both near-misses even though neither cleared, per house discipline of
running the check whenever a candidate exists)

Both CL=F configs replayed **UNCHANGED** (same lookback, same exit, no
re-optimization) on BZ=F (Brent), BZ's own 60/20/20 split points.
WTIOIL-USDT was **not** used as the transfer venue — only 58 daily bars
cached, far short of what a 20–35 bar/hour lookback plus a 60/20/20 split
needs (same reasoning step115 documented).

- **1d transfer** (donchian20+chandelier2.5): BZ train n=111 +$63.27/t,
  BZ val n=38 **-$10.93/t**. Sign flips. **TRANSFER DOES NOT HOLD.**
- **1h transfer** (donchian35h+chandelier3.0): BZ train n=216 -$2.57/t,
  BZ val n=51 -$10.93/t → -$10.77/t. Already negative on BZ train.
  **TRANSFER DOES NOT HOLD.**

Neither near-miss is a real cross-instrument edge — both are
instrument-specific noise, exactly the failure mode round 116's Brent
result (which passed 15.87x on BZ but failed on CL) already warned this
desk about, mirrored in the opposite direction.

## Luck / multiple-comparisons context

77 cells were screened per timeframe (154 total). On daily, 30/77 cells
cleared the naive train-floor+positive filter (n≥30, exp>0) — nothing
close to "1 in 20," this is a market that trended for large stretches of
its 16-year train window, so a fairly loose filter (positive expectancy,
30-trade floor, no cost/chance test yet) lets roughly 4 in 10 cells
through by construction. That is exactly why thickness, the chance
baseline, and the transfer test exist as SEPARATE, harder gates after
selection — and why this round leans on the chance-baseline draw (random
entries through the identical exit apparatus) as the real control on the
one selected cell, not on "how many cells looked positive." On 1h, only
9/77 cleared the same filter — the intraday signal is much weaker ground
to begin with, and the winner still failed val outright.

## FINAL VERDICT

**Nothing clears the bar.** Both near-misses (donchian(20)+chandelier2.5
on 1d, donchian(35h)+chandelier3.0 on 1h) are rejected: the daily one on
thickness (2.56–3.85x, under 5x) AND on failing to beat its own chance
baseline; the intraday one on a straight val sign-flip. Neither transfers
to Brent unchanged.

**Plain answer, as instructed if nothing clears:** oil trend breakouts,
swept across the exact entry-lookback range that produced Wallace's
eyeballed +14.3%/+8.3% open trades, and paired with the exit library this
round tested (structure-trailing, EMA/MA cross, chandelier at four ATR
multiples), do not clear this desk's evidence bar after real taker costs
and a real structural stop. The clearest sub-finding: **the EMA20/EMA50
cross exit Wallace actually eyeballed is negative expectancy on TRAIN at
every lookback from 5 to 55 — the two open trades he's watching are live
individual outcomes of a system that loses money on average across 26
years of oil data.** The closest thing to a real shape (chandelier2.5x/
structure-trail exits, lookback 15–55) improves modestly on round 116's
donchian(55) near-miss but still fails thickness, fails to beat a
random-entry chance control using the identical exit, and does not
transfer to Brent. "Oil trends are real but not harvestable after costs
at any lookback tested here" is the honest read — it is also the most
coherent explanation yet for why the book's one live winner (+$58.39) sat
on a borrowed 2-hour mean-reversion scorer that was never supposed to be
a trend system in the first place: there may simply not be a clean,
transferable, cost-surviving breakout edge in this data, at these
timeframes, with this exit library.

## No book spec

Per the round's own instruction: since nothing cleared train+val+
thickness+transfer, no book spec is written. **Recommendation to Morgan:
do not stand up a donchian-breakout oil book on this evidence.** If this
family is revisited, the highest-value untested lever is not another
lookback or exit — it is the weekly EIA inventory report (Wednesdays
~15:30 UTC), oil's own genuine scheduled-event structure that this round
deliberately did not touch (round 111 was supposed to test it and never
did; that remains open and separate from this breakout-lookback question).

## Files

- `step117_oil_breakout_lookback_sweep.py` — this round's script
  (train-only 77-cell grid per timeframe, val read once, chance baseline,
  thickness both ways, cross-instrument transfer)
- `step117_table.csv` — full 154-row grid (2 timeframes x 11 lookbacks x
  7 exits), train stats for every cell
- `step117_results.md` — this file
