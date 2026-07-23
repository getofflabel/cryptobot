# RESEARCH LOG — the ledger of looks

Every backtest look recorded here, especially SEALED TEST looks (test-window
erosion is real: each look at a spent window on the same family weakens what a
"pass" means). Format per entry: date, hypothesis, config, train/val/test
numbers, verdict, looks consumed.

Prior rounds (1-16) are documented in the step*.py files and the project memory
(`~/.claude/projects/-Users-wallacechen/memory/project-crypto-trading-bot.md`).
This file begins with the autonomous research-cycle era.

---

## 2026-07-22 — Round 17: 2h-resolution tactical entries (step22_round17.py)

**Hypothesis (RESEARCH_QUEUE.md item #1):** The live tactical book's two
triggers — panic-dip (RSI(3)<15) and flag-touch (bar dips to its 80h trend
line and closes back above it) — currently fire on 1h bars. Does the same
tactical logic carry an edge at 2h resolution (fewer, cleaner signals, wider
natural stop)?

**Config (frozen from queue, no tuning):**
- Filter: 4h champion state == long (vol-gated MA 20/100, funding<=1bp),
  mapped onto 2h bars with no lookahead (4h bar's state applies only after it
  fully closes).
- Triggers tested separately AND as the live OR-of-both:
  panic-dip = RSI(3) on 2h close < 15; flag-touch = 2h low <= 80h trend line
  (40-bar SMA at 2h) AND 2h close back above it.
- Stop = 1.85 x median(2h ATR%), median on TRAIN window only = 1.85 x 1.19%
  = **2.2%** (matches the queue's estimate exactly).
- Target = 3:1 = 6.6%. Hold = 24 bars (48h). Execution = maker. Real funding.
- 27,725 2h bars, 6.3 years, 60/20/20.

**Results (train / val / TEST, maker, full costs):**

| variant | train exp | train n | val exp | val n | verdict |
|---|---|---|---|---|---|
| panic-dip 2h | **-$20.30** | 144 | +$53.89 | 55 | FAIL train — negative, no test look |
| flag-touch 2h | +$11.34 | 155 | +$64.83 | 53 | qualified -> tested |
| panic OR flag (live) | **-$10.51** | 207 | +$83.94 | 77 | FAIL train — panic drags it negative, no test look |

**flag-touch 2h SEALED TEST (one look):** exp **+$40.23/trade**, **+11.7%**,
win **52%**, 29 trades, DD **-8.6%**.

**VERDICT: flag-touch 2h SURVIVES THE FULL GAUNTLET.** Positive on train
(+$11.34, 155t), val (+$64.83, 53t), and the sealed test (+$40.23, 29t, 52%
win, -8.6% DD). Clean sample sizes throughout. This is the second tight-stop
tactical family ever to pass the full gauntlet (after the 1h MTF-dip in round
15) and the first survivor at 2h resolution. **-> AWAITING DEPLOYMENT REVIEW.
Not auto-deployed.**

- panic-dip 2h: killed on TRAIN (negative expectancy). No test look taken.
- panic OR flag (live combo): killed on TRAIN (panic's negative train drags
  the combo under). No test look taken.

**Notes for the deployment reviewer:**
1. Flag-touch already runs LIVE at 1h in `tactical.py` (the `_signals_1h`
   flag path, 80h SMA). This 2h variant is a SLOWER cousin of an already-live
   trigger — deploying it means either a parallel 2h flag sleeve or a decision
   about overlap/correlation with the 1h flag firings (they will sometimes
   coincide). Correlation of the two sleeves' entries should be measured before
   sizing both at full tactical allocation.
2. The stop (2.2%) sits safely inside 10x liquidation (~9.5%), so this is
   10x-compatible per the standing mission — but the leverage frontier was NOT
   mapped this run (research only). Map it during deployment review.
3. Train expectancy is modest (+$11.34) vs val/test — the edge is real but not
   huge at 1x; its value is as an ADDITIONAL validated gun (more trade
   frequency), consistent with the "more sleeves, not more voltage" thesis.

**Looks consumed:** ONE sealed-test look on the 2h flag-touch family (pristine
before this — all prior tactical work was 1h). The 2h panic-dip and 2h combined
windows were NOT looked at on test (failed train) and remain unspent.

**Next in queue:** item #2 — OI-confirmed flag-touch (1h live geometry + 24h OI
change > +2%).

## 2026-07-23 — 15m forensic autopsy + composites (interactive session)
Vol-normalized geometry: stop 0.67%, tgt 2.01%, hold 96 bars. AUTOPSY (train
only, both directions): best single conditions reach just 25-26% hit rate vs
~27% breakeven — enrichments cap at 1.14-1.18x (vs 1.35x at 1h). Composites
gauntleted: long (trend+vol+6h momentum) train +$1.95 marginal, val -$18.40
FAIL; short (trend+vol+funding>2) train -$1.78 FAIL. No test looks burned.
FINDING — the resolution map: 4h strong ($401/t), 1h moderate ($40-59/t),
15m below the cost floor. Candle edges decay with resolution because
profit-per-trade shrinks into fixed costs while signal weakens. 5m fetching;
expect worse — nightly researcher to confirm cheaply for completeness.

## 2026-07-23 — credit-sprint batch (interactive)
[1] WALLACE'S HYPOTHESIS — 15m entries + WIDE stops (1.5%): VINDICATED at
two gates: train +$14.82/197t, val +$26.17/55t (tight stops had val -$18!)
-> TEST -$30.94/17t. 7th two-window winner killed by 2025-26. His stop-width
insight materially real; the modern grind regime is the killer. QUARTERLY
RE-AUDIT list. 15m wide SHORT: train +$55.60/36t but val n=2 (funding rare)
— joins shadow-watch class. [2] OI-flag-touch: FAIL train. [3] post-settle
long: FAIL train. [4] OI-breakout: FAIL train (val +). Looks burned: 5
train/val pairs + ONE 15m test look. Queue items 2-4 closed.

## 2026-07-23 — THE AMPLIFIER: BTC-signal -> ETH-trade (interactive)
BTC panic-dip (champ1h bull + rsi3<15) traded ON ETH at ETH's vol-normalized
geometry (1.81/5.43/48h maker). Train +$17.26/173t, val +$0.52/62t (thin but
positive), TEST +$50.43/23t, 43% win, DD -8.5%. FULL GAUNTLET SURVIVOR #5.
STATUS: AWAITING DEPLOYMENT — needs multi-asset tactical executor (ETH slot,
ETH contract specs, per-symbol brackets/reconcile). Build carefully in an
interactive session; zero rush while the market is chopped (no signals firing).
Also today: order-clipping shipped to the live executor (12ct = 3 maker clips,
100% maker in live drill).

## Queue additions (2026-07-23)
- DEPLOY: multi-asset tactical executor for the ETH amplifier sleeve.
- Walk-forward robustness audit of all live strategies (rolling windows, not
  one static split) — strengthens or flags every live verdict.
- FOMC/CPI-day study: known historical dates vs our triggers — veto or edge?
- Native forensic autopsies on ETH and SOL (their own paying-moments, not
  BTC's rules transferred).
- Joint-book simulation: both books on one ledger, true combined drawdown,
  validate the 60/40 weights.

## 2026-07-23 — Round 19 (win-rate filters) + Round 20 (SOL amplifier)
R19: daily-screen and confluence filters on the strikes — ALL WORSE than
baseline (daily filter deletes early-trend winners; confluence = weakness).
Nothing deployed; baseline reconfirmed. Strikes' TEST win rates already
49-52%. R20: BTC-signal->SOL at SOL geometry: train -$0.55 (miss by a hair),
val +$28 — does not qualify, NO test look burned. SOL benched again but the
miss is by $0.55/trade; quarterly re-audit list. ETH amplifier remains the
sole deployment-ready survivor.

## 2026-07-23 — ROUND 22: walk-forward audit (year-by-year, all live books)
RIDE 6/7 yrs positive (only 2022 bear -27%). panic-dip 6/7 (worst year just
-1.0% — the most robust edge we own). flag-touch 5/7. ETH amplifier 5/6.
FLAG-2H: 4/7 with profits concentrated in 2024 (+46%) and a -25% 2023 —
ERA-DEPENDENCE FLAG: keep live (passed formal gauntlet, smallest sizing 3x)
but on WATCH — bench at first live losing streak. No config changes.

## 2026-07-23 — ROUND 23: FOMC study
Decision hour = 2.55x normal violence (real, fades within 12h). BUT the
panic-dip is FOMC-NEUTRAL: 15 trades entered within 24h of a decision made
+$74.81/t at 40% win vs +$73.79/t away — statistically identical. NO VETO,
NO CALENDAR PLUMBING NEEDED: the vol/trend gates already absorb scheduled
events; the geometry survives announcement chop. Advisory keeps flagging
FOMC dates for Wallace's awareness only (next: Jul 29). ~52 FOMC dates
hardcoded from public schedule (minor date-error risk disclosed).

## 2026-07-23 — ROUND 24: native autopsies, ETH & SOL
Both coins' best native conditions (volatility regime, 1.36-1.42x) top out
at 24-25% hit rates vs ~27% breakeven; composites (volatile AND crash-zone)
failed train on both (ETH -$15/t, SOL -$40/t). NO test looks burned.
VERDICT: no native long edge on either alt at vol-normalized geometry —
alts run hotter but noisier than BTC; their validated role stays FOLLOWER
(ETH amplifier). Alt-native ideas now require flow data like everything
else fast. Queue: joint-book sim is the last pre-flow item.

## 2026-07-23 — ROUND 25: joint-fleet simulation (one ledger, live weights)
1,135 trades, 6.3yr, event-ordered compounding (approximation; no
liquidation modeling; all books assumed present from day 1; books are
SURVIVORS of ~300 candidates so forward expectation is lower — treat the
$ figure as structural, not a promise). $1k -> $831k (196% CAGR).
STRUCTURE (the real findings): worst COMBINED drawdown -72.3% (correlation
cost is real — deeper than any single book; at live aggression this WILL
recur, expect it, it is in spec); lowest-ever point $831; monthly avg
+15.5% / median 0.0% / 47% positive / worst month -45%; exposure median
2.5x when active, PEAK 7.8x equity, flat 59% of the time. Weights kept
as-is per Wallace's chosen aggression; optional exposure cap (~6x) noted
but NOT added (would alter validated behavior off an approximation).

## 2026-07-23 — ROUND 26: weekend study (measurement, no looks burned)
Weekend tape runs 0.68x weekday violence (thinner books, quieter). The
panic-dip still WINS on weekends: +$58.49/t (100 trades) vs +$80.79/t
weekday (221) — smaller but solidly positive, 39-40% win both. VERDICT:
no weekend veto (would delete profitable trades); no session filter.
Pre-flow-data docket now FULLY COMPLETE. Remaining calendar: nightly
researcher self-generates hypotheses; Oct 2026 quarterly re-audits;
~Aug 20 flow-data era opens the 15-20x tier hunt.

## 2026-07-23 — ROUND 29: GARCH method (Miles Deutscher repo)
Built walk-forward GARCH(1,1) daily vol forecasts (1,809 days, zero
lookahead, refit/21d; cached data_garch_btc_1d.parquet; reference script
vendored as garch_reference.py). Gauntlet vs champion on common window
(2021-08+): GARCH-only gate NEARLY 3x'd train (+75.3% vs +25.6% with 1/3
the trades — higher-quality entries) but val +40.2% < champion +50.5% →
NO test look, ATR keeps the belt. GARCH OR ATR: near-miss (+48.4% val).
GARCH sizing beat r10's ATR sizing on train (+35.1% vs champion +25.6%)
— forecast vol > realized vol as a sizing instrument. DISPOSITION: GARCH
enters the toolbox; queued for nightly researcher (PRE-SPECIFIED: GARCH
percentile-gate grid on train/val only; GARCH storm-veto for strikes;
GARCH gate for the 15m shadow). Caveat: common window shrinks samples
(train 32t, val 9t).

## 2026-07-23 — ROUND 30: the 15-year backtest (Bitstamp daily, 2011-2026)
5,439 daily bars ($8.88 -> $65,677). THE FINDING: Bitcoin's volatility has
structurally DECAYED era over era — a FIXED vol gate calibrated on early
eras (9.42% daily) went completely dead by 2023 (zero trades, 3 eras).
ADAPTIVE gate (ATR > 1.3x trailing-365d median) fixed it: $1k -> $187k
(42% CAGR) vs fixed's $11k, trading in EVERY era. Transferred to the live
4h gauntlet: adaptive did NOT beat the champion (val +26.4% vs +63.9%) —
belt retained, no test look — the champion's fixed 1.5% is superior in the
CURRENT era. STANDING RISK ON RECORD: the live gate will age as BTC
matures; monitor via the monthly scoreboard (if ride trade-count decays
toward zero across quarters while trends visibly run, the gate is dying —
re-derive it then). HODL's 7,400x over 15yr is the $8.88 base effect, not
a beatable benchmark for any risk-managed system at 1x.

## 2026-07-23 — ROUND 31: GARCH percentile-gate grid on the ride (step23_round31.py)

**Hypothesis (RESEARCH_QUEUE.md "GARCH era" docket, top pre-specified item):**
Replace the 4h champion's FIXED ATR vol gate (enter longs only when ATR>=1.5%
of price) with a GARCH percentile gate at the pre-specified thresholds
{50th, 60th, 70th} — "is the walk-forward GARCH daily-vol forecast in the top
X% of what we've seen so far?" Round 29's single GARCH-only gate 3x'd TRAIN
(with 1/3 the trades) but its val fell short; this is the reserved grid.

**Config (frozen, no tuning):** champion = vol_gated_ma(4h, 20/100,
funding<=1bp). GARCH variant swaps min_atr_pct=1.5 -> 0 (ATR gate OFF) and adds
entry_filter = funding<=1bp AND garch_vol >= trailing-expanding-quantile(q),
q in {0.50,0.60,0.70}. Threshold is a TRAILING expanding quantile (min 180 days)
of the round-29 walk-forward forecast (built from returns through D-1) — no
lookahead. Daily gate mapped onto 4h bars backward. Common window = where the
trailing threshold exists: **2022-02-03 -> 2026-07-22, 9785 4h bars**, 60/20/20.
Champion RE-SCORED on this exact window as the honest benchmark (round 29's
+50.5% used a longer 2021-08 window and is NOT reused as the bar).

**Results (train / val, taker, real funding — TEST HELD BACK, NOT LOOKED AT):**

| config | tr n | tr exp | tr ret% | val n | val exp | val ret% |
|---|---|---|---|---|---|---|
| CHAMPION (ATR 1.5 gate) | 27 | +$81.88 | +22.1% | 6 | +$979 | **+58.8%** |
| GARCH p50 gate | 15 | **-$182** | **-27.3%** | 3 | +$1,673 | +50.2% |
| GARCH p60 gate | 12 | **-$230** | **-27.6%** | 3 | +$966 | +29.0% |
| GARCH p70 gate | 9 | **-$222** | **-20.0%** | 2 | +$1,551 | +31.0% |

**VERDICT: FAIL — belt retained.** All three GARCH percentile gates go
NEGATIVE on train (-20% to -27.6%) and none beats the champion's val return
(+58.8%). They are also sample-starved (train 9-15, val 2-3 trades — below the
30/8 minimum), so they could not qualify even setting the negative train aside.
The ride simply doesn't fire often enough on a ~4.4yr window to validate any
gate swap with confidence — that thinness is itself a finding.

WHY THIS DIVERGES FROM ROUND 29'S OPTIMISTIC TRAIN: round 29 REPLACED the ATR
gate differently (its "GARCH-only gate" behaved as a near-champion-return
selector on the longer 2021-08 window). This round's pure percentile-REPLACEMENT
of the ATR gate on the honest common window fails: a high GARCH forecast (top
50/60/70% of history) is NOT the same as the instantaneous ATR being live at
the moment of a 4h trend entry, and the ATR gate is doing real work the GARCH
percentile does not replicate. The champion's fixed 1.5% ATR gate stands.

**Looks consumed:** THREE train/val screens (p50/p60/p70). ZERO test looks
(none was on the table — this item was a train/val screen by design). The GARCH
percentile-gate-REPLACEMENT family is now CLOSED.

**Also closed this file (queue hygiene):** the credit-sprint batch (see above,
2026-07-23) already closed queue items #2 OI-flag-touch, #3 post-settle long,
#4 OI-breakout (all FAIL train); the 15m forensic autopsy closed item #5; and
Round 26 closed item #6 (weekend). The queue file lagged reality and is now
reconciled — do NOT re-run items 2-6 (burned).

**Next in queue:** GARCH STORM-VETO for the strikes (skip entries when forecast
> trailing p90) — the next GARCH-era item, and a fresh, unexplored construction
(veto on the fast tactical entries, not a gate on the slow ride).

## ROUND 41 — the shorts offensive (2026-07-23)
Wallace's mandate: crack shorts. Four native families, 64 configs, full costs
+ real funding, gauntlet splits (train->2024-01-10, val->2025-04-16).
6 two-window survivors emerged — the most short life ever seen. THREE sealed
test looks were spent (erosion ledger: +3):
- forensic widened f>1.5bp 1h: test 0 TRADES. The 2025-26 grind never once
  produced its euphoric-funding + live-ATR entry condition. Not a loser — a
  SLEEPER. It cannot pay in a grind but also cannot bleed. Reclassified
  DORMANT-BY-DESIGN; deployed to the live demo Shorts Lab where forward
  trades (whenever regime turns violent) build its real sample.
- breakdown N20 gate-below-median 1h: test -$0.17/t x108. Train/val edge was
  regime coincidence; in the true out-of-sample grind it nets to costs.
  BURIED. Never re-tune.
- bleed-rider structural k=5 1h: test -$25.81/t x52, -13.4%. The grid
  fragility flag (k=8/k=12/4h all negative) was the tell — this was
  overfit to historical bleed shapes. BURIED. Lesson reconfirmed: a config
  whose parameter neighbors all fail is noise wearing a costume.
KEY STRUCTURAL FINDING (now 3x confirmed: rounds 4-8, round 39 sealed
deaths, round 41): the 2025-26 low-vol grind pays NO short family after
costs. Shorts that survive are CRASH-REGIME specialists that must sit
dormant through grinds. Correct architecture = dormant crash-catchers with
strict regime gates (funding euphoria, live ATR), NOT always-on shorts.
Demo Shorts Lab (per Wallace's sandbox doctrine) carries forensic_short +
cascade_short live; auto-bench judges them on real forward trades.
