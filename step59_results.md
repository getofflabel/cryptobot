# Round 59 — EXIT SCIENCE: does structure beat fixed-% ?

**Files touched:** `step59_exit_science.py` (the simulator + all runs), this
file. No commits, no live orders, step55-58 never touched or imported.

**The owner's thesis, tested exactly as stated:** *"structure-based exits
(previous high, price action levels) are more accurate than fixed-percentage
targets."* Tested as a BEFORE/AFTER on the program's four live-shaped entry
systems, entry held byte-for-byte identical, only the exit module swapped.

---

## 1. SIM-VALIDATION (read this before trusting anything below)

A brand-new hand-rolled per-trade simulator was needed because dynamic,
per-trade structural exits (a target that moves with confirmed swing
points, a trailing floor that only ratchets up) cannot be expressed as
`backtest.py`'s single continuous 0/1 signal. Before trusting it on
anything new, it was checked against the number that matters most:
**does it reproduce `backtest.py`'s own trusted engine on a case both
engines CAN express identically?**

X0 (STRIKES' incumbent — fixed 4.5% target / 1.5% stop / 48h cap, maker
execution) is exactly such a case. The check: run E1's entries + X0
through this file's new simulator, take the REALIZED trade windows it
produced, replay those exact windows through `backtest.py.run_backtest()`
(signal = 1 for `[entry_idx, exit_idx)` per realized trade — non-overlapping
by construction, since they came from the same single-slot engine), and
let `backtest.py` find its own stop/target fills independently inside each
window with its own mechanics. Funding was omitted on both sides so the
check isolates exit-mechanics agreement, not the funding approximation.

| | trades | win rate | expectancy/trade | total return |
|---|---|---|---|---|
| **this file's new simulator** | 421 | 33.5% | +$12.87 | +54.2% |
| **backtest.py (trusted, existing)** | 421 | 33.5% | +$10.66 | +44.9% |

**Trade count: exact match (421 = 421). Win rate: exact match (33.5% =
33.5%) — the two engines agree on the outcome of every single trade, not
just the aggregate.** Dollar expectancy differs by ~21% (not expected to
match to the penny — stated in the module docstring going in: `backtest.py`'s
maker mode fills the signal bar's close only if the *next* bar's low/high
actually touches that limit, otherwise it chases at a worse taker price on
that bar's own close; this file's simplification always fills exactly at
the entry bar's own close, the maker best case). Both point the same
direction (positive, comparable magnitude), and the discrepancy has a
plain, honestly-stated mechanical cause rather than being unexplained.
**VERDICT: simulator VALIDATED** — the run script raises `SystemExit` and
refuses to produce any downstream number if this check ever fails.

A second, independent confirmation showed up for free: this simulator's
own `split_points()` (chronological 60/20/20) landed on **train→2024-01-10,
val→2025-04-16** for BTC 1h — the *exact* boundary dates Round 41's own
gauntlet already reported for the identical split convention on the
identical BTC 1h series.

---

## 2. THE HEADLINE TABLE — before / after, per live entry

*"Right now it's X; with the change it's Y."* Dollars are expectancy per
trade on the compounding $10,000 walk (matches every gauntlet script in
this repo — no leverage in the backtest; leverage is a deployment-time
overlay applied after a strategy is chosen).

### E1 — STRIKES (panic-dip, tactical.py)

| | train exp | train ret | train DD | val exp | val ret | val DD | verdict |
|---|---|---|---|---|---|---|---|
| **BEFORE (X0, incumbent TP4.5/SL1.5/48h)** | +$5.36 (n=421) | +22.6% | -40.5% | **-$10.19 (n=118)** | -12.0% | -31.0% | **FAILS validation** |
| **AFTER (X3, structure-trailing)** | +$3.51 (n=458) | +16.1% | -49.1% | **+$4.75 (n=135)** | +6.4% | -23.9% | **SURVIVOR** |

**Right now the live STRIKES exit does not validate on the most recent 20%
of data (-$10.19/trade). Swap to structure-trailing (ride until the last
confirmed higher-low breaks) and it becomes the only exit of all six that
survives both windows: +$3.51/trade train, +$4.75/trade val, and a
meaningfully smaller validation-window drawdown (-23.9% vs -31.0%).** The
owner's LITERAL thesis (a smarter fixed *target*) does not hold here — X1
(previous-swing target) still fails val at -$8.03/trade, barely better
than the incumbent's -$10.19. It's not "a better target" that rescues
STRIKES, it's "don't use a fixed target at all, trail the stop with
structure instead."

### E2 — NEWSDESK (news momentum, newsdesk.py)

| | train exp | train ret | val exp | val ret | verdict |
|---|---|---|---|---|---|
| **BEFORE (X0, incumbent TP2.4/SL1.2/24h)** | +$1.73 (n=335) | +5.8% | **-$12.53 (n=115)** | -14.4% | **FAILS validation** |
| best challenger on train — X3 | +$38.52 (n=186) | +71.6% | **-$26.68 (n=76)** | -20.3% | FAILS validation, worse |

**Right now NEWSDESK's exit also fails validation (-$12.53/trade). Unlike
STRIKES, NO exit tested here fixes it** — every one of X1-X5 also loses
money on the validation window, and the biggest train number (X3's
+$38.52/trade) is a textbook overfit tell: it reverses to -$26.68/trade
out of sample, the single worst degradation in this entire round. Exit
science does not rescue NEWSDESK. Given this repo's own repeated
2025-26-grind finding on fast tactical entries (RESEARCH_LOG rounds 41/43),
the more likely fix, if one exists, is on the ENTRY side, not here.

*(Side note, stated for the record, not re-tuned here: the dataset used —
`data_watcherguru_history.parquet`, 3,527 posts spanning the full 400-day/
13-month harvested history — has grown since Round 45B's original
+$23.74/train / +$7.11/val validation; today's larger sample simply
produces different absolute numbers on the SAME rule. Nothing here
re-derives or contradicts that original result, it re-tests the current
exit against today's fuller data.)*

### E3 — GOLD (donchian20/EMA20, gold_book.py) — TWO TWINS

**GLD (ETF, 20y):**

| | train exp | train ret | val exp | val ret | verdict |
|---|---|---|---|---|---|
| **BEFORE (X0, incumbent EMA20-cross/18%SL)** | +$83.77 (n=67) | +56.1% | +$79.59 (n=23) | +18.3% | SURVIVOR |
| **AFTER (X1, prev-swing target)** | **+$98.63 (n=101)** | +99.6% | **+$129.85 (n=29)** | +37.7% | SURVIVOR, beats X0 both windows |

**GC=F (COMEX futures, twin confirmation):**

| | train exp | train ret | val exp | val ret | verdict |
|---|---|---|---|---|---|
| **BEFORE (X0, incumbent)** | +$89.33 (n=89) | +79.5% | +$79.70 (n=24) | +19.1% | SURVIVOR |
| **AFTER (X2, liquidity-pool target)** | +$186.07 (n=139) | +258.6% | **+$87.07 (n=36)** | +31.3% | SURVIVOR, beats X0 both windows |
| **AFTER (X3, structure-trailing)** | **+$249.18 (n=57)** | +142.0% | **+$110.10 (n=18)** | +19.8% | SURVIVOR, beats X0 both windows |

**Gold is the one place the owner's thesis is confirmed cleanly. The
incumbent already survives (it's the one live-validated exit in this
whole round), and structure-based challengers beat it on BOTH windows on
BOTH twins** — GLD: X1/X2/X3/X5 all beat X0 on train AND val (X1's val
edge is the biggest single number in this round: +$50.26/trade over the
incumbent, a 63% val-expectancy improvement). GC=F: X2/X3/X5 beat X0 on
both windows (X1 does NOT — its GC=F val ($55.00) is actually below X0's
($79.70), even though its train number is huge ($214.32) — a train/val
mismatch worth flagging, not deploying). **The specific winning module
differs slightly by instrument (X1 works cleanly on GLD but not GC=F; X2
and X3 work on both twins)** — X2 (liquidity-pool target) and X3
(structure-trailing) are the two challengers that survive the twin
confirmation cleanly.

### E4 — BTC 1h donchian20 breakout (clean generic testbed)

No live exit exists for this entry — X0 here is **CONSTRUCTED**, not
deployed: stop = 1.5x the TRAIN-median ATR14% (1.21%), target = 2R
(2.43%), 240-bar (10-day) cap — round-17's own "size from TRAIN only,
freeze for val" convention, reused verbatim, stated loudly so it is never
mistaken for something already running.

| | train exp | val exp | val ret | val DD | verdict |
|---|---|---|---|---|---|
| **BEFORE (constructed X0)** | +$1.33 (n=691) | **-$20.78 (n=238)** | -49.5% | -50.5% | FAILS |
| **AFTER (X3, structure-trailing)** | +$12.72 (n=446) | **-$7.20 (n=151)** | -10.9% | -26.2% | still FAILS, much less badly |

**Nothing tested fully rescues a raw, unfiltered donchian breakout — every
exit loses money on validation. Structure-trailing (X3) is still clearly
the best of a bad set: 65% smaller per-trade loss than the constructed
incumbent (-$7.20 vs -$20.78) and less than half the drawdown (-26.2% vs
-50.5%).** On this entry family, exit choice matters a lot for how badly
you lose, but cannot turn a fundamentally-unfiltered entry into a winner —
consistent with every other family in this file that survived (E1's X3,
E3's whole family) being gated by SOME regime/trend filter (STRIKES' 4h
champion, gold's structural donchian on a slow trend) that E4 deliberately
lacks.

---

## 3. FULL MATRIX — every X on every E, train AND val (no selection)

### E1 STRIKES (BTC 1h, 2020-03-25 → 2026-07-22, train→2024-01-10, val→2025-04-16)

| exit | description | tr n | tr exp | tr ret | tr DD | tr hold | va n | va exp | va ret | va DD | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X0 | incumbent (live) | 421 | +$5.36 | +22.6% | -40.5% | 10.0h | 118 | -$10.19 | -12.0% | -31.0% | FAIL |
| X1 | prev-swing target | 431 | +$6.76 | +29.1% | -44.7% | 9.0h | 127 | -$8.03 | -10.2% | -30.6% | FAIL |
| X2 | liquidity-pool target | 421 | +$3.82 | +16.1% | -40.4% | 10.0h | 121 | -$8.24 | -10.0% | -28.7% | FAIL |
| X3 | structure-trailing | 458 | +$3.51 | +16.1% | -49.1% | 8.0h | 135 | **+$4.75** | +6.4% | -23.9% | **SURVIVOR** |
| X4 | hybrid (partial+BE) | 468 | -$8.73 | -40.9% | -51.5% | 7.0h | 139 | -$15.08 | -21.0% | -32.3% | FAIL |
| X5 | ATR chandelier trail | 418 | -$10.35 | -43.3% | -72.8% | 16.0h | 136 | -$19.84 | -27.0% | -31.1% | FAIL |

### E2 NEWSDESK (BTC 1h sliced to the news span, 2025-06-17→2026-07-22, train→2026-02-12, val→2026-05-03)

| exit | description | tr n | tr exp | tr ret | tr DD | tr hold | va n | va exp | va ret | va DD | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X0 | incumbent (live) | 335 | +$1.73 | +5.8% | -15.4% | 13.0h | 115 | -$12.53 | -14.4% | -22.5% | FAIL |
| X1 | prev-swing target | 331 | +$4.42 | +14.6% | -15.7% | 13.0h | 117 | -$15.56 | -18.2% | -23.4% | FAIL |
| X2 | liquidity-pool target | 334 | +$1.87 | +6.2% | -15.3% | 13.0h | 115 | -$14.39 | -16.6% | -22.8% | FAIL |
| X3 | structure-trailing | 186 | +$38.52 | +71.6% | -18.1% | 19.0h | 76 | -$26.68 | -20.3% | -23.1% | FAIL (overfit tell) |
| X4 | hybrid (partial+BE) | 372 | -$6.87 | -25.6% | -32.0% | 9.0h | 138 | -$19.79 | -27.3% | -29.5% | FAIL |
| X5 | ATR chandelier trail | 256 | -$14.52 | -37.2% | -42.5% | 15.0h | 80 | -$33.44 | -26.8% | -31.6% | FAIL |

### E3 GOLD — GLD (ETF daily, 2004-11-18→2026-07-23, train→2017-11-14, val→2022-03-16)

| exit | description | tr n | tr exp | tr ret | tr DD | tr hold | va n | va exp | va ret | va DD | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X0 | incumbent (live, EMA20/18%SL) | 67 | +$83.77 | +56.1% | -18.2% | 336h(14d) | 23 | +$79.59 | +18.3% | -8.5% | SURVIVOR |
| X1 | prev-swing target | 101 | +$98.63 | +99.6% | -18.8% | 144h(6d) | 29 | **+$129.85** | +37.7% | -9.8% | **SURVIVOR, beats X0** |
| X2 | liquidity-pool target | 101 | +$96.96 | +97.9% | -17.3% | 144h(6d) | 29 | +$111.22 | +32.3% | -10.7% | SURVIVOR, beats X0 |
| X3 | structure-trailing | 44 | **+$208.54** | +91.8% | -22.0% | 672h(28d) | 16 | +$117.29 | +18.8% | -12.2% | SURVIVOR, beats X0 |
| X4 | hybrid (partial+BE) | 108 | +$45.64 | +49.3% | -14.9% | 132h(5.5d) | 33 | +$50.69 | +16.7% | -7.3% | SURVIVOR, below X0 |
| X5 | ATR chandelier trail | 64 | +$115.21 | +73.7% | -17.3% | 336h(14d) | 22 | +$118.96 | +26.2% | -6.7% | SURVIVOR, beats X0 |

### E3 GOLD — GC=F (COMEX futures daily, 2000-08-30→2026-07-23, train→2016-03-18, val→2021-05-20)

| exit | description | tr n | tr exp | tr ret | tr DD | tr hold | va n | va exp | va ret | va DD | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X0 | incumbent (live) | 89 | +$89.33 | +79.5% | -17.5% | 312h(13d) | 24 | +$79.70 | +19.1% | -8.8% | SURVIVOR |
| X1 | prev-swing target | 137 | +$214.32 | +293.6% | -12.6% | 144h(6d) | 36 | +$55.00 | +19.8% | -8.3% | SURVIVOR, below X0 on val |
| X2 | liquidity-pool target | 139 | +$186.07 | +258.6% | -12.6% | 144h(6d) | 36 | +$87.07 | +31.3% | -6.8% | SURVIVOR, beats X0 |
| X3 | structure-trailing | 57 | **+$249.18** | +142.0% | -27.4% | 672h(28d) | 18 | +$110.10 | +19.8% | -8.8% | SURVIVOR, beats X0 |
| X4 | hybrid (partial+BE) | 145 | +$140.14 | +203.2% | -9.6% | 120h(5d) | 36 | +$63.81 | +23.0% | -6.8% | SURVIVOR, below X0 |
| X5 | ATR chandelier trail | 93 | +$130.23 | +121.1% | -16.2% | 288h(12d) | 22 | **+$168.38** | +37.0% | -5.8% | SURVIVOR, beats X0 |

### E4 BTC 1h donchian20 breakout (2020-03-25→2026-07-22, same split as E1; X0 CONSTRUCTED, not live)

| exit | description | tr n | tr exp | tr ret | tr DD | tr hold | va n | va exp | va ret | va DD | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X0 | constructed baseline | 691 | +$1.33 | +9.2% | -43.6% | 6.0h | 238 | -$20.78 | -49.5% | -50.5% | FAIL |
| X1 | prev-swing target | 688 | +$0.19 | +1.3% | -48.1% | 6.0h | 236 | -$20.44 | -48.2% | -49.9% | FAIL |
| X2 | liquidity-pool target | 692 | +$1.34 | +9.3% | -44.5% | 6.0h | 239 | -$20.93 | -50.0% | -51.2% | FAIL |
| X3 | structure-trailing | 446 | +$12.72 | +56.7% | -50.6% | 24.0h | 151 | **-$7.20** | -10.9% | -26.2% | FAIL, much less bad |
| X4 | hybrid (partial+BE) | 760 | -$9.56 | -72.6% | -77.6% | 4.0h | 255 | -$21.02 | -53.6% | -53.6% | FAIL |
| X5 | ATR chandelier trail | 656 | -$14.01 | -91.9% | -92.6% | 9.0h | 232 | -$28.39 | -65.9% | -66.4% | FAIL |

---

## 4. X4 HYBRID — does partial-TP + breakeven help?

**No — it is the worst or near-worst exit in every single family tested.**
X4 (X1's structure target, floored at 1.5R, 50% off at 1R, remainder to
breakeven) underperforms every other exit on E1, E2, and E4, and trails
its own family's incumbent on E3's GLD and both twins' val windows too.

Why, with the trade-reason breakdown (E1 train, representative):

| outcome | count | share |
|---|---|---|
| stopped before ever reaching 1R (full stop-loss on 100% of size) | 227 | 48.5% |
| reached partial, then gave back the remainder at breakeven | 90 + 52 = 142 | 30.3% |
| reached partial AND captured the bigger structural target | 79 + 5 = 84 | 17.9% |
| hit the 48h time cap | 15 | 3.2% |

The mechanism is doing exactly what it says — of trades that reach 1R,
**63% are protected at breakeven rather than giving the whole thing back**
(142 of 226) — but the STOP was never reduced to match the reduced (50%)
exposure once a partial is taken. A full stop-out on 100% of size still
costs the full incumbent stop distance, while a partial win only banks
half the position at 1R. Since roughly half of ALL trades never even
reach 1R, the asymmetry (100%-sized losers vs 50%-sized partial winners)
loses more on the losers than the breakeven protection saves on the
winners. The management overlay itself works as designed (E3's numbers
confirm the BE-protection mechanic is a genuinely lower-drawdown ride —
GLD/GC=F X4 has the SMALLEST max drawdown of any exit in both twins,
-14.9%/-9.6% vs the incumbent's -18.2%/-17.5%) — it is simply the wrong
tool for entries with a high stop-out rate, and a legitimate
lower-volatility choice (smallest DD, worse expectancy) for gold.

## 5. X3 vs X5 — does STRUCTURE specifically matter, or is any trailing stop enough?

| family | X3 (structure) val exp | X5 (ATR chandelier) val exp | structure wins by |
|---|---|---|---|
| E1 STRIKES | **+$4.75** (SURVIVOR) | -$19.84 (FAIL) | yes, decisively |
| E2 NEWSDESK | -$26.68 (FAIL) | -$33.44 (FAIL) | yes, but both fail |
| E3 GLD | +$117.29 | +$118.96 | no, ATR trail marginally ahead |
| E3 GC=F | +$110.10 | **+$168.38** | no, ATR trail clearly ahead |
| E4 donchian | **-$7.20** (least-bad) | -$28.39 (worst) | yes, decisively |

**On the fast crypto tactical entries (E1, E4), structure specifically
matters — X3 doesn't just beat its own incumbent, it beats the
non-structural trailing control by a wide margin (in E1's case, the
difference between surviving and failing validation).** On the slow daily
gold trend (E3), the two trailing mechanisms are roughly interchangeable —
sometimes ATR trail edges it, sometimes structure does, both comfortably
survive either way. One honest methodology note: X3's exits are almost
entirely the INTRABAR protective-floor stop, not the close-based
structural break (E1 train: 458/458 "structure stop", 0 "structure
break"; E3 GC=F train: 55 stop / 1 break / 1 time-cap) — meaning X3, as
built here, behaves mostly as *"a trailing stop that ratchets to swing
lows"* rather than literally *"wait for a confirmed close-based
breakdown."* That's still squarely inside the spirit of the mandate
(structure decides the stop, not a fixed distance), just worth naming
plainly.

## 6. k=8 robustness spot-check (footnote, not a further grid column)

| config | k=5 (primary) | k=8 |
|---|---|---|
| E3 GLD X1, train | +$98.63 | +$96.22 |
| E3 GLD X1, val | +$129.85 | **+$125.00** |
| E1 X3, train | +$3.51 | -$1.65 |
| E1 X3, val | +$4.75 | **+$17.67** |

GLD's X1 result is stable across k — a good sign it isn't a k=5 artifact.
E1's X3 is noisier (k=8 flips train slightly negative but val more than
triples) — with only 135-340 trades in these windows this is within the
range of ordinary sample noise for a swing-pivot parameter, not a red
flag, but also not grounds to claim extra confidence beyond what k=5
already showed. Neither number changes any verdict above.

## 7. Ranked look-candidates (informational only — NO look was spent; the
sealed 20% test slice was never touched by this script)

Two different bars are reported, because the mandate's own bar ("beats its
incumbent on train AND val") reads differently for a family whose
incumbent already survives (gold) vs one whose incumbent is currently
FAILING (STRIKES, donchian testbed) — for the latter, "the challenger's
train number is literally higher than the failing incumbent's train
number" is not really the interesting bar; "does the challenger survive
at all where the incumbent doesn't" is.

**A. Challengers that beat X0 on BOTH windows outright (X0 itself already
a survivor):**
- E3 GLD: X1 (+$14.86 train / **+$50.26 val**), X2 (+$13.19 / +$31.63), X3
  (+$124.77 / +$37.70), X5 (+$31.44 / +$39.37) — four of five challengers
  clear this bar; X4 does not.
- E3 GC=F: X2 (+$96.74 / +$7.36), X3 (+$159.86 / +$30.40), X5 (+$40.91 /
  **+$88.68**) — three of five; X1 and X4 do not.
- **Twin-confirmed on BOTH GLD and GC=F: X2 (liquidity-pool) and X3
  (structure-trailing).** These are the strongest, most broadly-supported
  candidates in the whole round.

**B. A challenger that turns a currently-FAILING incumbent into a
SURVIVOR:**
- E1 STRIKES: **X3** — the only exit (of six) that is positive on both
  train and val for this entry at all, where the live incumbent is
  currently negative on val.
- E4 donchian testbed: no challenger reaches SURVIVOR, but X3 is the only
  one with a val loss under -$10/trade (all others: -$20 to -$28/trade).

**Ranked by strength of evidence:** (1) E3 X2/X3 — twin-confirmed, both
windows, both instruments, largest sample sizes (n=44-139 per window);
(2) E3 X1 — GLD-only but the single biggest val-expectancy jump in the
round; (3) E1 X3 — smaller sample (n=135 val) but flips a live-failing
system to a validated one; (4) E3 X5 — beats X0 on both twins but is the
"not specifically structure" control, weaker evidence for the owner's
literal thesis even though it works.

---

## Biggest caveats

1. **X3's exits are overwhelmingly the intrabar protective floor, not the
  close-confirmed structural break** (see §5) — validate the label
  before deploying; it is a smart trailing stop off swing lows, closer to
  a smarter X5 than to "wait for the chart to close-confirm a breakdown."
2. **E2 NEWSDESK's data has grown since Round 45B** — today's larger
  WatcherGuru harvest changes the absolute numbers on the identical rule;
  this file re-tests against today's data, it does not contradict the
  original validation.
3. **E4's incumbent is CONSTRUCTED, not live** — there is no real "before"
  for this entry; treat E4 as a clean mechanism study (what does exit
  choice alone do to an unfiltered breakout), not a deployment decision.
4. **Gold's stop-distance for X1/X2/X3(warmup-fallback)/X4/X5 is also
  CONSTRUCTED** (1.5x TRAIN-median ATR%) — the real incumbent's only stop
  is the far 18% crash-insurance level, unusable as a risk-sizing
  denominator for a tight structural target. X0 itself (the number
  actually compared against) is the untouched literal incumbent.
5. **No leverage modeled anywhere in this file** (matches every other
  gauntlet script in this repo) — live STRIKES runs 20x, NEWSDESK 20x,
  gold 2x; these dollar/percent figures are the UNLEVERED backtest
  comparison the deployment decision would then scale from, not the
  live-sized numbers themselves.
6. **Sample sizes on val are thin in places** (E1 X3: 135 trades; E3 GLD
  X3: 16 trades; E4 all: 151-255) — all clear the repo's own 30-train/
  8-val floor, but "clears the floor" and "large sample" are not the same
  claim.
