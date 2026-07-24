# step74_results.md — round 74: the fair test of Alex Gonzalez's structure -> retest -> engulfing system

Companion to `step74_structure.py` (read that file's module docstring for
the exact formalization + attribution) and `step73_rules.md` (the source
transcript distillation, unchanged from round 73). Research only — no
commits, no live orders.

## 0. Why this round exists

Round 73 gauntleted this trader's system on a **daily-context -> 4h-entry**
two-tier collapse because yfinance caps sub-hourly bars at ~60 days,
making an honest 60/20/20 gauntlet at his real 15m/30m/1h entry
resolution impossible. Result: **85% of round 73's 108 configs came back
INSUFFICIENT-SAMPLE** — a ~2-year intraday-derived history never
accumulates the 30-train/8-val trade floors when a system fires roughly
once a month. That was flagged explicitly as a data-depth verdict, not a
strategy verdict, because his own structure work is stated as weekly/
daily anyway.

This round drops the two-tier collapse and tests the system on **one
timeframe: daily structure, daily retest, daily engulfing**, against
**20-33 years of free yfinance daily history** for six forex majors, gold,
and SPY, plus this repo's own 14.9-year BTC daily cache. If his system
has real signal, this much history should let it clear the floors.

## 1. True data spans (do not assume — verified)

| Instrument | Bars | Start | End | Years |
|---|---|---|---|---|
| GBPUSD | 5,888 | 2003-12-01 | 2026-07-23 | 22.6 |
| USDJPY | 7,709 | 1996-10-30 | 2026-07-22 | 29.7 |
| EURUSD | 5,876 | 2003-12-01 | 2026-07-23 | 22.6 |
| USDCAD | 5,944 | 2003-09-16 | 2026-07-23 | 22.9 |
| USDCHF | 5,942 | 2003-09-16 | 2026-07-23 | 22.9 |
| GBPJPY | 5,891 | 2003-12-01 | 2026-07-22 | 22.6 |
| GOLD (GC=F) | 6,498 | 2000-08-30 | 2026-07-24 | 25.9 |
| SPY | 8,428 | 1993-01-29 | 2026-07-24 | 33.5 |
| BTC (bitstamp) | 5,439 | 2011-09-02 | 2026-07-23 | 14.9 |

Every forex pair and gold clears 20+ years; SPY clears 33; BTC (never
demonstrated live by this trader) is naturally capped at its own
14.9-year existence. Train/val/test splits (60/20/20, chronological) land
around **12-20 years of TRAIN data per instrument** — more than enough
runway for his claimed 4-14 trades/yr to clear a 30-trade floor, if the
claim holds.

## 2. THE HEADLINE FINDING: his literal full-stack system never fires
   often enough to be tested — even on 20-33 years of daily data

The "main" grid (structure -> retest [5 or 10 bars] -> engulf-confirm,
his literal stack, k in {2,3}, buffer in {0.1%,0.2%}, R in {2,3,4}, mode
in {reversal, continuation, both} = **648 configs across 9 instruments**)
produced:

- **max trades in ANY train window: 26** (need 30)
- **max trades in ANY val window: 7** (need 8)
- **0 of 648 main-stack configs cleared BOTH floors.** Every single one
  is INSUFFICIENT-SAMPLE.
- Mean realized frequency: **0.48 trades/yr** (median 0.42) across all
  648 main configs — nowhere near his stated "roughly once every 25-90
  days" (4-14/yr). Per-instrument average frequency ranged from 0.22/yr
  (GBPJPY) to 0.85/yr (BTC) — all far below his claim, on every single
  instrument, forex home-turf included.

This is the round's most important, most honest result: **the data-depth
excuse from round 73 is now closed, and the system STILL doesn't clear
the floors.** With 12-30 years of TRAIN data alone, a system firing even
2-3x/yr would clear 30 trades easily. This one doesn't come close. Two
readings, both consistent with step73_rules.md's own findings:

1. The literal conjunction (body-close break -> retest within a tight
   window -> a candle that engulfs BOTH prior candles' full bodies) is
   simply a much rarer daily-bar event than his narration implies — the
   TOL_PCT=0.35% retest tolerance and the strict two-candle engulf test
   compound multiplicatively into a very low hit rate.
2. His own transcript already told us his real trading is more
   discretionary than this: "there's never going to be like a proper
   black or white textbook," swing-point ("snake trick") validity calls
   are made "by eye," and he admits breaking his own rules on camera
   multiple times. A strict, honest mechanization of his STATED rules
   may simply be stricter than what he ACTUALLY trades off in practice.

Either way: **the "structure -> retest -> engulf" system, taken exactly
as he states it, cannot be evaluated on real trade counts on any
dataset tested here** — not a rejection of edge, but a rejection of
testability as literally specified.

## 3. Component ablation — which part of the stack is choking frequency

This is where the round earns its keep. Three ablations, all run at a
fixed representative point (k=3, w=10 where applicable, buffer=0.1%,
mode=both, R swept {2,3,4}) to isolate one change at a time:

| Ablation | Mean trades/yr | vs main (0.48/yr) | Survivors | FAILs | Insufficient |
|---|---|---|---|---|---|
| (a) drop ENGULF, keep retest | 3.39 | **7x more frequent** | 5 | 19 | 3 |
| (b) drop RETEST entirely (enter at break) | 3.90 | **8x more frequent** | 7 | 20 | 0 |
| (c) keep full stack, ADD 200-SMA trend filter | 0.51 | ~same as main | 0 | 0 | 27 (all) |
| main (full stack, no trend filter) | 0.48 | baseline | 0 | 39 | 609 |

**Verdict: the RETEST requirement is the single biggest frequency
choke point**, followed closely by the ENGULF requirement — dropping
either one roughly 7-8x's the trade count and is what makes the system
testable at all. Dropping BOTH (ablation b, enter directly at the body-
close break) is the single most testable variant and also the one with
the most survivors (7 of 12 total). The 200-SMA trend filter (ablation c)
changes almost nothing about frequency on its own (0.51 vs 0.48/yr)
because it's layered ON TOP of the already-starving full stack — it
never got a chance to prove anything; every one of its 27 configs is
still INSUFFICIENT-SAMPLE.

**Does the engulfing confirmation "earn its keep"?** Comparing ablation
(a) (no engulf) against the main stack isn't a clean apples-to-apples
comparison because the main stack couldn't even generate a train sample
to compare against. What IS clean: ablation (a) vs ablation (b) — both
run at the identical rep point, differing only in whether the retest
step exists. Ablation (b) (no retest, no engulf) has *slightly* higher
frequency (3.90 vs 3.39/yr) and *slightly* better positive-expectancy
share (56% vs 44% of traded configs having positive val expectancy) than
ablation (a) (retest kept, engulf dropped). That's weak evidence, not
strong: **the retest step is not clearly adding value over just trading
the break directly**, at least in this single-timeframe daily
formalization. The genuinely strong claim this round CAN make: **the
combination of retest+engulf together is what kills the system's
testability** — whichever one you drop, frequency and clearability both
improve substantially.

## 4. Win-rate reality check — the headline honesty check

His stated claim: **"swing trader's win rate tends to be anywhere from
60 to 65%"** (later restated inconsistently as "70 to 65%").

Realized, on adequate samples this time:

| Population | n configs | Mean pooled win% | Median | Min | Max |
|---|---|---|---|---|---|
| ALL 729 configs (any trades) | 729 | 38.9% | 40.0% | 0.0% | 75.0% |
| Main full-stack configs only | 648 | 38.8% | 40.0% | 0.0% | 75.0% |
| **The 12 SURVIVORS** (floors cleared, train+val both positive) | 12 | **42.8%** | 43.1% | 34.9% | 51.7% |

**His claimed 60-70% win rate does not hold up anywhere in this test.**
Every survivor's realized win rate sits in the 35-52% band, roughly
20-30 percentage points below his stated figure, and the grid-wide
average (38.9%) is even lower. This is NOT necessarily damning on its
own — the survivors are all profitable specifically BECAUSE their
pooled reward:risk ratio (1.3-2.5x) more than compensates for a sub-50%
win rate, which is the normal, healthy shape of a breakout/R-multiple
system (fewer, bigger wins). But it flatly contradicts the specific
number he states on camera. Combined with his own admission that the
video's headline "$100 to a million" claim is walked back, and that his
in-platform week-6 stat snapshot (n=7 trades, self-reported 70% win
rate) is far too small a sample to mean anything, the pattern across
every round of this ingestion pipeline (round 72's TJR, this round's
Gonzalez) is the same: **stated win-rate claims consistently run well
above what a disciplined, cost-inclusive backtest recovers.**

## 5. Per-instrument verdict — home turf vs elsewhere

| Instrument | He actually traded it live? | Survivors (of 81 configs) | Best val expectancy config | Verdict |
|---|---|---|---|---|
| GBPJPY | Yes (his first live trade) | 3 | ablation(a) no-engulf R2.0: $73.76/trade, 47.6% win, 17 val trades | Works, but only with engulf dropped |
| BTC | **No** (claimed, never shown live) | 3 | ablation(b) breakout R4.0: $316/trade, 43.3% win, 15 val trades | Works — best of ANY instrument, and he never traded it |
| GBPUSD | Substitute for his GBPCHF (his most-traded pair) | 2 | ablation(b) breakout R3.0: $197.73/trade, 61.1% win, 18 val trades | Works, only with retest dropped |
| EURUSD | Yes (once, a self-admitted rule-breaking loss) | 2 | ablation(b) breakout R3.0: $30.46/trade, 47.4% win, 19 val trades | Works, modestly, retest dropped |
| USDCAD | Yes | 1 | ablation(a) no-engulf R2.0: $9.23/trade, 50.0% win, 16 val trades | Barely works |
| SPY | **No** (claimed cross-market, never shown live) | 1 | ablation(b) breakout R2.0: $72.97/trade, 56.0% win, 25 val trades | Works, retest dropped |
| USDCHF | Yes | 0 | best is ablation(b) R2.0: -$22.65/trade val | **Never clears floors as a survivor** |
| USDJPY | Yes | 0 | best is ablation(b) R3.0: -$48.70/trade val | **Never clears floors as a survivor** |
| GOLD | **No** (claimed, never shown live) | 0 | main mode=reversal R4.0: only 1 val trade, INSUFFICIENT-SAMPLE everywhere | Untestable — never enough trades |

**No clean "works on home turf, fails elsewhere" pattern.** Two of his
actually-traded pairs (USDCHF, USDJPY) produced zero survivors despite
being real trades in the source video; meanwhile BTC and SPY — both
markets he explicitly claimed to trade but never demonstrated on
camera — produced 3 and 1 survivors respectively, with BTC's breakout
config posting the single best expectancy of the entire round. This
does not support "his forex specialization carries the edge." If
anything, it weakly suggests the edge (where it exists at all) is a
generic break-and-continuation effect that shows up wherever there's
enough volatility and history, not something specific to his forex
pairs or his named setup.

GOLD is the one outright failure of testability: not one of its 81
configs (main + all three ablations) ever reached even the val floor —
its retest+touch geometry at TOL_PCT=0.35% apparently almost never
lines up on this dataset.

## 6. Trades/year actually realized — the honest counts

| Stage | Mean trades/yr | vs his claim (4-14/yr) |
|---|---|---|
| Main (full stack, his literal system) | 0.48 | **8-30x too infrequent** |
| Ablation (a) no-engulf | 3.39 | Still below his low end, but in the right order of magnitude |
| Ablation (b) breakout/no-retest | 3.90 | Closest to his stated range, still below the 4/yr floor on average |
| Ablation (c) trend-filter + full stack | 0.51 | Same problem as main — the filter never got a chance |

Only the two ablated (simplified) variants get anywhere near his stated
firing rate, and even then average out just under his stated floor of
4/yr. The literal full system, exactly as narrated, fires roughly once
every 2 years per instrument on average — an order of magnitude below
his own claim.

## 7. Ranked survivors (sealed test NEVER touched — lead spends looks)

All 12 configs that cleared BOTH floors with positive train AND val
expectancy, ranked by val expectancy:

| # | Instrument | Config | Stop% | Target% | Train n / exp | Val n / exp | Val win% | Pooled RR | Trades/yr |
|---|---|---|---|---|---|---|---|---|---|
| 1 | BTC | ablation(b) breakout, R=4.0 | 6.00% | 24.00% | 45 / $2,711.16 | 15 / $316.29 | 33.3% | 2.48 | 5.04 |
| 2 | GBPUSD | ablation(b) breakout, R=3.0 | 1.97% | 5.92% | 52 / $2.02 | 18 / $197.73 | 61.1% | 2.06 | 3.86 |
| 3 | BTC | ablation(b) breakout, R=3.0 | 6.00% | 18.00% | 45 / $2,158.40 | 15 / $101.54 | 33.3% | 2.09 | 5.04 |
| 4 | GBPJPY | ablation(a) no-engulf, R=2.0 | 1.79% | 3.59% | 46 / $72.57 | 17 / $73.76 | 47.1% | 1.87 | 3.48 |
| 5 | GBPUSD | ablation(a) no-engulf, R=2.0 | 1.69% | 3.39% | 46 / $27.73 | 17 / $73.62 | 41.2% | 1.93 | 3.48 |
| 6 | SPY | ablation(b) breakout, R=2.0 | 3.90% | 7.79% | 73 / $15.65 | 25 / $72.97 | 56.0% | 1.33 | 3.66 |
| 7 | GBPJPY | ablation(a) no-engulf, R=3.0 | 1.79% | 5.38% | 46 / $32.98 | 17 / $58.57 | 41.2% | 2.33 | 3.48 |
| 8 | GBPJPY | ablation(a) no-engulf, R=4.0 | 1.79% | 7.17% | 46 / $33.93 | 17 / $46.71 | 41.2% | 2.45 | 3.48 |
| 9 | BTC | ablation(b) breakout, R=2.0 | 6.00% | 12.00% | 45 / $640.33 | 15 / $44.65 | 40.0% | 1.59 | 5.04 |
| 10 | EURUSD | ablation(b) breakout, R=3.0 | 2.12% | 6.37% | 52 / $2.70 | 19 / $30.46 | 47.4% | 1.76 | 3.92 |
| 11 | EURUSD | ablation(b) breakout, R=4.0 | 2.12% | 8.10% | 52 / $25.27 | 19 / $12.32 | 41.2% | 1.90 | 3.86 |
| 12 | USDCAD | ablation(a) no-engulf, R=2.0 | 1.67% | 3.33% | 49 / $37.64 | 16 / $9.23 | 50.0% | 1.62 | 3.56 |

**Every single survivor is an ABLATED variant.** Zero survivors come
from the literal full-stack ("main") system — consistent with section 2,
none of those 648 configs ever had enough trades to even be eligible.
All 12 survivors either drop the engulf confirmation (ablation a, 5
configs) or drop retest entirely and enter at the break (ablation b, 7
configs). None survive with the trend filter (ablation c) — that stage
never generated a single eligible config.

## 8. Honest caveats

- **Zero survivors from his literally-stated system.** Every candidate
  above is a simplified, ablated version of what he teaches — this round
  answers "does SOME version of break-and-continuation work" more than
  it validates HIS specific engulf-and-retest recipe.
- **BTC's numbers are compounding-inflated.** $2,711/trade train
  expectancy reflects full-equity (size_frac=1.0) compounding through
  BTC's 2011-2020ish bull run inside the train window, not a
  per-trade-comparable dollar figure against the forex/SPY rows. Treat
  BTC's RANK (strong, real edge in % terms) as meaningful; treat its
  raw dollar expectancy as an artifact of the compounding convention
  every round in this repo uses, not something special to BTC.
- **Train n=52 for several forex "breakout" survivors is right at the
  floor** (30 minimum) — thin margin, not a deep confirmation.
- **TOL_PCT (0.35% retest tolerance) and MAX_HOLD (60 trading days) are
  both new, reasoned choices for this round, not values stated in the
  source** — see step74_structure.py's docstring for the reasoning.
  Different choices here would move trade counts and could plausibly
  pull more (or fewer) main-stack configs across the floor.
  TOL_PCT in particular is suspected as a major contributor to GOLD's
  complete failure to generate testable samples anywhere.
- **The stop convention changed from round 73** (wick-based + explicit
  buffer here, vs. round 73's body-swing approximation) — the two
  rounds' dollar figures are not directly comparable to each other.
  This was a deliberate, task-specified change toward fidelity to his
  one stated numeric example ("10 to 15 pips above this wick"), not an
  inconsistency.
- **GBPCHF and NZDCAD (his most-frequently and first-alternately traded
  live pairs) could not be tested** — not liquid enough on yfinance for
  deep daily history; GBPUSD and USDCAD stand in as his other traded
  majors per the round's task spec.
- **200-SMA trend filter (ablation c) is untested, not falsified.**
  Every one of its 27 configs is INSUFFICIENT-SAMPLE — it was layered
  on the already-starved full stack, so this round cannot say whether
  with-trend-only entries help or hurt. A fair test of that specific
  question would need to apply the SMA200 filter to one of the
  ABLATED (higher-frequency) entry styles instead — not done here,
  flagged as a natural next step, not run without being asked.
- **Sealed test (20%) genuinely never touched** by this script — `score()`
  only ever slices `[0:i_tr]` and `[i_tr:i_va]`, verified in
  step74_structure.py's `gauntlet_instrument`/`score` functions.
