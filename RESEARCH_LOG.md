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

## ROUND 43 — the day-trade hunt (2026-07-23)
Wallace's mandate: trades in-and-out within a day, stops sized for 20x.
4 families / 98 configs (momentum burst, session breakout, washout scalp,
VWAP fade), full costs + funding, gauntlet splits. 3 two-window survivors.
TWO sealed looks spent (erosion +2, both on family 1):
- momentum burst 1h X1.8 CHAMP-gated 3xATR: test -$2.68/t x36. FAIL.
- momentum burst 1h X1.8 RAW: test -$11.02/t x55 — the +$37.90 val was
  window luck, exactly as flagged. FAIL. BURIED, never re-tune.
- session breakout survivor: NO look spent (+$1.08/t val edge with -77%
  train DD is undeployable at any size) — BURIED without look.
Other findings, now with numbers:
- RSI3 washout scalp DIES at same-day exits (all 32 configs negative, to
  -$46/t): the dip-buy edge NEEDS its 48h room. The live strikes keep it.
- 15m below cost floor for all 4 families (~9.2bps cost vs ~3bps edge).
  4th confirmation of the resolution map.
- STRUCTURAL (4th confirmation): the 2025-26 grind kills fast holds the
  same way it kills shorts. Surviving edges remain SLOW (4h trend, 48h
  dip-buys). Candle-derived day-trade families are exhausted; the
  day-trade tier now waits on NEW DATA TYPES: flow/OI era (~Aug 20) and
  news-timestamped event scalps (WatcherGuru feed gives exact event
  times — a family no candle backtest could see).

## ROUND 45A — grind-native day trades (2026-07-23)
4 families / 168 configs for the low-vol grind (calm-range fade, funding
scalp, OI-shock, breakout-failure). 4 survivors, ALL in the OI-shock-follow
family (calm-gated). ONE sealed look spent on the top pick (erosion +1):
- OI-shock 1h q90 follow calm stop1.0/tgt2.0: train +$7.56/t val +$12.28/t
  -> TEST -$5.86/t x59, -3.5%. FAIL. BURIED. The calm gate flipped train
  positive but the edge did not survive out-of-sample.
Real finding: the calm gate genuinely conditions OI-shock train profits
(-$7->+$7) but that was in-sample structure, not a durable edge. Range-fade
(the family built AROUND the calm gate) failed outright, gate or not.
CANDLE + OI day-trade families are now EXHAUSTED across rounds 43+45A: the
grind kills every fast price/OI-derived edge at the sealed test. The last
untested frontier for day trades = NEWS-TIMESTAMPED events (round 45B) and
the flow-microstructure era (~Aug 20). Test-look erosion total: +6.

## ROUND 45B — NEWS-EVENT day trades — FIRST SEALED-TEST SURVIVOR (2026-07-23)
Harvested WatcherGuru Telegram public history: ~400 days (2025-06-18 ->
2026-07-23), 2941 relevant BTC/macro events. EVENT STUDY (the scientific
core): BTC's |1h move| after a relevant WatcherGuru post = 1.33x the
unconditional baseline (BEARISH-tagged: 1.44x). Wallace's thesis CONFIRMED —
his trusted source carries measurable tradeable energy that no candle
backtest can see.
Backtest: 64 configs, 3 two-window survivors. ONE sealed look spent
(erosion +1) on the strongest 1h config:
- A-news-momentum, FIRST-BAR-MOVE direction, 1h, stop 1.2%/target 2.4%,
  hold 24h (follow the sign of the first post-news hour's move):
  train +$23.74/t x200, val +$7.11/t x67 -> **TEST +$20.81/t x67, +13.9%,
  52.2% win, median hold 15h. PASS.** ★ FIRST STRATEGY EVER TO PASS THE
  SEALED TEST in the whole program (rounds 1-45).
CAVEATS (honest): only ~13mo of news history total (vs 6yr candles) — one
regime slice, no bull-run/crash in sample; test window is ~2.5mo / 67
trades; keyword classifier is crude (live AI judges may do better OR
differently). ONE sealed pass is encouraging, NOT proof of a durable edge.
NEXT: forward-paper-test on demo before any real-money consideration; the
live Situation Room already ingests WatcherGuru — wire a "news momentum"
book that follows the first-hour move after a relevant headline (GATED
profitability work -> Fable). Also worth: re-run the event study with the
AI classifier instead of keywords; extend the harvest as more history
accrues.

## ROUND 45B — ADDENDUM: two sibling sealed looks (2026-07-23, later)
Owner asked to sealed-test the OTHER two 45B survivors alongside the already-
spent strongest config. Reproduced via step45d_test_look.py (byte-for-byte
same entries as step45b, slice [i_va:n]):
- A-news-momentum FIRST-BAR-MOVE 1h stop1.2/tgt2.4 hold24h (the already-logged
  winner): reconfirmed TEST +$20.81/t x67, +13.9%, 52.2% win. No new erosion.
- B-news-fade FIRST-BAR-MOVE 15m stop1.2/tgt3.6 hold24h: TEST +$6.62/t x67,
  +4.4%, 46.3% win, median hold 21h. PASS — but a NEW look (family B's first),
  erosion +1.
- A-news-momentum KEYWORD 1h stop1.2/tgt3.6 hold24h: TEST -$13.37/t x42, FAIL,
  BURIED. A second look inside family A (protocol stretch: "never re-look a
  spent family"). erosion +1.
Net: 2 additional sealed peeks spent this addendum (family-B first look +
family-A second config). Test-look erosion total now +8. Takeaway reinforced:
the FIRST-BAR-MOVE direction (follow price's own first reaction) is what
carries; the KEYWORD classifier direction does NOT survive out-of-sample —
consistent with keeping the live book direction-agnostic (follow the move,
don't trust the word-reading).

## ROUND 47 — the news edge tested on TradFi (2026-07-24)
Does the WatcherGuru edge port to gold/oil/QQQ/SPY? 1h yfinance bars over
the 13mo news span, session-aware alignment, honest gap-adjusted stops.
EVENT-STUDY (ratio vs baseline; BTC reference 1.31x): pooled numbers LOOKED
bigger (GLD 1.40, QQQ 1.39) but that is overnight-gap contamination —
SESSION-ONLY (market actually live): GLD 1.02, USO 0.93, QQQ 1.03, SPY 1.03
= NO measurable live reaction to WatcherGuru posts in TradFi sessions.
BTC's 1.31x is genuine because crypto has no off-hours to hide gaps in.
CONCLUSION: the 24/7-ness IS the edge carrier; our news edge's home arena
is crypto. (Honest limit: WatcherGuru is crypto-centric news — this does
NOT prove "news can't move gold", only that OUR feed's edge doesn't port.)
STRATEGY GRID: 336 configs. ETFs: 0 survivors. GC=F (gold futures): one
gap-adjusted survivor — session-only news momentum stop0.8/tgt2.4/24h,
train +$9.28/t x157, val +$10.48/t (gap-adj) x54. SEALED LOOK DEFERRED:
no execution path (futures broker) exists yet; looks are spent when a
candidate is deployable. KEY PORTING LESSON with numbers: ETF overnight
gaps destroy tight stops (GLD near-miss: 44/45 val trades gapped THROUGH
the 0.5% stop; -$0.19/t raw -> -$37.81/t honest). The crypto tight-stop
playbook does not port to session markets unmodified.

## ROUND 48 — TradFi trend gauntlet — SECOND VALIDATED EDGE (2026-07-24)
20y daily gold/QQQ/SPY/oil through the crypto-proven shapes. 200 configs,
14 survivors — 8 of them the Donchian-breakout family. TWO sealed looks
spent on the twin flagship (erosion +2), BOTH PASS:
- GLD donchian55+EMA20exit 1d: TEST +$199.41/t x16, +31.9%, DD -13.9% (4.4y)
- GC=F same shape:            TEST +$145.10/t x18, +26.1%, DD -13.0% (5.2y)
Cross-instrument + all-decades-positive + sealed pass = the program's most
robust edge. ★ Second validated edge (after BTC news momentum).
Other findings: BTC's fixed 1.5% ATR gate produces ZERO trades on gold/QQQ
hourly (native ATR 0.28-0.72%) — thresholds never port blind; RSI3 dip-buy
does NOT transfer to TradFi (1/72); mirrored shorts die on secular uptrends
(0/20); backtest.py charges default FUNDING unless CostModel funding_bps_8h=0
— set explicitly for all TradFi (latent-bias catch); ETF overnight gaps blow
tight stops (44/45 gap-throughs on a 0.5% GLD stop; round 47 same lesson).
HONEST FRAME: long-only trend systems did NOT beat buy-and-hold raw return
over these decades — the case is validated edge + ~14% DD vs B&H's much
deeper. Turnover ~3-6 trades/yr = a slow compounder, portfolio ballast
beside the fast crypto books, not a replacement.
EXECUTION PATH: GLD via Alpaca paper (Wallace signup pending) → deployable.
Deferred: GC=F news-momentum candidate (round 47) until a futures venue.

## ROUND 54 — adaptive-gate ride revalidation: INCUMBENT DEFENDED (2026-07-24)
Dormancy audit motivated testing whether the ride's fixed 1.5% ATR gate
(open only 18.7% of recent bars) should migrate to the adaptive gate.
Train/val with the live -8% SL: statistical wash (~100% vs ~101% train,
57.0% vs 54.6% val). TWO sealed looks spent on the drought window itself
(erosion +2), the decisive comparison:
- FIXED 1.5 (live):   8t, +$401.30/t, +32.1%, DD -12.3%, last entry 06-18
- ADAPTIVE 1.0x:     11t, +$137.19/t, +15.1%, DD -24.0%
VERDICT: KEEP THE FIXED GATE. In the grind, selectivity IS the edge —
the strict gate marks only real vol expansions; adaptivity trades the
noise for half the money at 2x the drawdown. The round-30 "fixed gates
die" prescription does NOT apply to this strategy's sealed-era behavior.
The ride's honest modern cadence: ~6-7 entries/yr, each heavily paid.
Owner's activity mandate is served by the other books, not by loosening
the sniper. Gold book separately fixed this session (donchian 55->20,
sealed-passed on both instruments — see commit).

## ROUND 55 — the Gold System (2026-07-24)
5 families / 114 configs on GC=F 20y-daily + 2.4y-1h/4h + XAUT venue
checks. 23 two-window survivors. TWO sealed looks spent (erosion ~+17):
- daily z-MR z24<-1.5 ungated: train $32.40/val $41.34, all decades
  positive -> SEALED -$45.80/t x26 (5.2y) FAIL. The sealed slice IS
  gold's 2021-26 supertrend; reversion dies against it. BURIED.
- 1h EMA20/50 long (owner's named indicator; beat donchian on 1h, 4/4
  XAUT venue-transfer): SEALED (5.8mo thin) -$61.86/t x30 FAIL ->
  WATCH LIST, re-examine when hourly history matures. Not re-tuned.
Sessions (London/NY/Asia) 0/6; pullback-in-trend 0/16; shorts 0/36.
Bonus: donchian+EMA20exit fractals to 1h (152/55t) and 4h (41/17t)
two-window — un-looked (thin-window discipline). GOLD PLAYBOOK STANDS:
breakout trend-following is gold's one proven native language.

## ROUND 58 — divergences/oscillators/MTF (2026-07-24)
180 configs. ★ THIRD VALIDATED EDGE: 4h HIDDEN RSI divergence (RSI14, k8
swings, buf 0.35%, tgt 3x, hold 48h; champion-gated continuation longs+
shorts-mirror-in-downtrend): train $74.22/t x66, val $31.99/t x24, 7/16
neighbor cluster -> ONE sealed look (erosion ~+18): 24t, +$52.03/t,
+12.5%, DD -15.5% ACROSS THE DROUGHT WINDOW. PASS. Deploying as a live
book. Regular (reversal) divergences: 1/96 = noise, buried. Oscillator
overlays on donchian: mostly sample-cutters (ADX>=20 tight-exit variant
the lone narrow win). MTF ladder: monotonic improvement (val $4.59 ->
$5.47 -> $56.42 stacking bias+trigger) but full-alignment n=12 val =
floor-thin -> WATCH LIST, no look spent. 15m cost floor reconfirmed
structural (8.5-9.5bps realized vs ~9-10 floor).

## ROUND 57 — price-action patterns (2026-07-24)
296 configs. THE CLASSIC PATTERN CANON DIES ON BTC AFTER COSTS:
order blocks 0/64 (base+breaker, broad clean negative), pin bars/
engulfing/inside-bars 0/112 (and CONTEXT FILTERS MADE PINS WORSE:
-8.9 bare -> -43.1 with SMA50 context), NR-squeeze 0/32. Sole life:
statistical vol-compression (BB-width squeeze + range-compression
breakouts, 10/88; best 4h BB-squeeze val $80.02/t x26 BUT val=7x train
= regime-flatter signature; runner-up range-compression gated has the
grid's tightest DDs). NO looks spent — family to WATCH LIST pending
neighbor-cluster scrutiny (the val>>train shape has failed sealed 2x
historically). FVG/order-block overlap only ~1.1x chance = tools are
distinct, not redundant.

## ROUND 56 — SMC toolkit (2026-07-24)
274 configs. ★ FOURTH VALIDATED EDGE: CHoCH k8 + CONFLUENCE>=2 (1h,
tgt 2x, train-median structural stop): train $15.45/t x52, val $72.51/t
x24, MONOTONIC dose-response in BOTH windows (thresh 0->1->2: train
-29.82->+1.54->+15.45; val -77.04->+7.64->+72.51) + neighbor island ->
SEALED (erosion ~+19): 16t, +$99.52/t, +15.9%, DD -11.4% through the
drought. PASS. Build queued after the Diver. Standalone tools DIED:
sweeps 0/96, FVG 0/24, fib 0/48 — they earn their living only as
confluence VOTES. "ANY-tool" pooling never survived (dilution) =
owner's "different weapons" framing confirmed over "everything always".
15m floor never cleared (FVG turned out DENSE ~1/2h, not sparse).
Caveat on 4h BOS/fib: wild train/val sign flips = overfit terrain.

## ROUND 60 — the S&P system (2026-07-24)
186 configs, 91 two-window survivors. ★ FIFTH VALIDATED EDGE (knowledge-
banked, no demo venue): RSI2<5 dip-buy above SMA200, exit close>SMA5 or
RSI2>65, no target — TWO sealed looks (erosion ~+21), BOTH PASS:
SPY +$75.36/t x33, +24.9%, DD -8.8% (6.7y); ES +$124.07/t x29, +36.0%,
DD -4.6% (5.2y). The index's mean-reversion personality is real, robust
(12/12 config variants), gap-honest. Regime finding: MR dominates BOTH
calm AND crash regimes; naive momentum failed 24/24 — the S&P mean-
reverts, period. Graveyard: gap-fill 0/16, overnight drift real (t=4.4)
but under costs, golden cross too slow, first-hour shorts dead. Trend =
DD-reduction-not-outperformance (matches gold). Turn-of-month t=2.43
flagged for a dedicated round. Venue: SPY-USDT prod tracks real S&P
(0.08% basis) but absent on demo + thin — deploy when venue exists.

## ROUND 63 — graveyard rehabilitation + SESSION axis (2026-07-24)
Owner doctrine tested: "known indicators are known for a reason — find
the right scenario." VERDICT: CONFIRMED. 12 of 10-tool-variants x 19
scenario/session cells rehabilitated (6.3% pass vs controls; SESSION
cells alone 12.0% — triple base rate, sessions pull real weight):
- Pin bars: violent markets + LONGS in off-hours + SHORTS in Asia
- Momentum bursts: calm trends + Asia + NY sessions (sealed burial of
  the unconditional config stands)
- VWAP fades: violent downtrends + WEEKENDS (owner folklore confirmed)
- ADX filter: ranging markets; donchian20 in LONDON val +$125.77/t x23
  (control-weak — needs confirmation before any deployment)
- EMA cross: quiet ranges only; ZERO session effect (folklore refuted)
STAYS FULLY BURIED: order blocks, reversal RSI divergence, tight VWAP.
5/6 original + 4/6 session claims beat dumb-cell controls; the 2 weak
ones flagged. News-heat axis structurally untestable (13mo news vs old
train window). NEXT: these conditional rules feed the scenario router +
Learning Engine components — deployment only via train/val+sealed per
rule, never straight from a rehab cell.

## ROUND 64 — the flip (2026-07-24)
Owner's live challenge ("clearly a short opportunity") tested: on
identical live-shape long entries, P0 ride-bracket vs P1 flip-and-reverse
vs P2 cut-only (34 configs, BTC+ETH, 15m breakdown triggers ±confirm).
VERDICT: BASELINE WINS. Flip reliably worst; cut-only marginally
least-bad but no edge; reversal short leg DONATES on BTC (-$17 to -$65/t
all 8 configs both windows), noise on ETH. FAKE-OUT RATE 62-89%: most
15m waterfalls close back above the broken level within 8 bars — they
are sweep-and-reclaims, not trend starts. Today's ETH dump autopsied:
flip enters 1871, wicks +1.31%, bounce eats it by 15:00 ≈ flat, while
the "wrong" long survived to green. SIXTH burial of breakdown-chasing
(first in conditional-flip form). Rule stands: honor the stop, never
reverse into a waterfall. The pattern's real value is the OTHER side —
sweep-fade longs, already a confluence vote in the sealed CHoCH edge.

## ROUND 65 — the news trade gets eyes (2026-07-24)
Owner critique ("you pre-know your TP — no real trader does this") tested
on the validated news trigger: N0 incumbent vs structure targets vs
structure trailing vs context veto vs ATR brackets. FINDINGS:
- INCUMBENT GONE STALE: N0 fails val on grown data (-$18.39/t) AND the
  SEALED slice (2026-05->07): -$14.93/t x105, -15.7%. The live config
  was bleeding in the current regime.
- ★ N2 STRUCTURE-TRAILING (stop = entry-bar extreme ±0.3%, trail
  confirmed k=5 swing lows, no TP, 24h cap): train +$9.57 x315, val
  +$4.34 x112, SEALED +$10.35/t x104, +10.8% — PASS on all three
  windows. Deployed to the live newsdesk (build + review same day).
- Structure TARGETS (N1) all fail; ATR brackets fail; CONTEXT VETO
  fails (refuses 78-94% of sample; vetoed trades were often mildly
  profitable — location-veto cuts sample, doesn't sharpen it).
- Big-trade autopsy: N2's edge is aggregate stop discipline (surviving
  losers), not single-trade brilliance; it clipped one +$276 winner
  to -$69. Caveat: one 13mo regime, a handful of trades swing totals.
Erosion ~+25. Owner's exit philosophy now sealed-validated on TWO live
books (gold R59 4x, news R65 sign-flip); "pre-known % targets" retired
from both.

## ROUND 66 — the scenario mind (2026-07-24)
5-axis classifier x 8 tools x 6y. CELL FINDINGS (train/val, floors met):
T6 forensic-short EXISTS ONLY in violent+crowded-long (val +$193.25/t
n=8 — the tool IS the scenario); T3 CHoCH concentrates in NY session
(val +$383.85/t n=13, round's biggest); T4 donchian20 rehabilitated in
ranging+normal+London/NY (val +$93.11 n=15) though dead overall; T7
vol-shock is scenario-AGNOSTIC (17/26 cells hot); T5 strikes = trending
-up + weekends, FADES in NY/London sessions. ROUTER v1 FAILED HONESTLY:
OR-union construction too permissive (cut ~0 trades for 7/8 tools),
beaten by the dumb-cell control — construction artifact, cells remain
real. AXES: CROWD & VOL load-bearing (-$4.04/-$3.71 per trade when
removed); SESSION dilutes routing despite big single cells; TREND/NEWS
negligible marginal router value. NO looks spent (cells n=8-15 = too
thin for sealed verdicts — quarantined until they fatten). NEXT: R68
router v2 (intersection/single-best-cell construction).

## ROUND 67 — calm-tape scalping (2026-07-24)
SIXTH BURIAL of fast trading on costs: 0/112 taker configs positive
train+val (S2 micro-MR, S3 VWAP magnet, S4 compression — hundreds-to-
thousands of trades each = well-powered no); maker escape evaporates
under chase-aware fills (best case +$0.43 fantasy -> -$1.25 honest);
CALM-GATE NOT CONFIRMED (gating made S2/S3/S4 WORSE). Frequency was
never the problem (1.4-6+ trades/calm-day — all losers after costs).
S1 range-edge-fade: real ~28bps gross edge but the range-width filter
was mis-scaled (no sqrt-N) -> 7-9 fires/6y = noise; ONE honest re-
attempt permitted with a corrected filter before the family is closed.
Quiet tape stays "A-setups only."

## ROUND 69 — banking the chart target (2026-07-24, late)
Owner's design (TP at the structural level once seen) tested vs the live
trailing config on identical news entries. NO CHALLENGER BEAT B0 on both
windows (bank-half +$5.19/+$2.05; bank-quarter +$7.37/+$4.73; full
target +$4.71/-$12.11; owner's literal TP+SL-no-trail -$0.51/-$6.95 vs
B0 +$9.57/+$4.34). WHY: ~70% of trades never reach the target (the
tight entry-bar stop resolves them first); the ~31% that tag it are the
runners — trailing banks MORE on exactly those ($198-204 vs $157-185
matched). The +$276 clip: caused by the TIGHT INITIAL STOP, not absent
banking — no variant rescued it. NEXT LEVER: the entry-bar-extreme stop
geometry itself (R70 candidate). No looks spent. Harness reproduced
R65's numbers bit-for-bit before testing.

## ROUND 70 — the walk-forward replay exam (2026-07-24)
The full frozen brain replayed blind through ~a decade, 3 markets,
$250/trade at 10-20x, 15m fill fidelity (0 ambiguous fills at our stop
widths; resolver stress-verified): BTC $33,421.52 all-years / $2,036.41
HONEST (clean+sealed, 149t, DD $3,056); OIL $4,706.62 all-years / $0
certifiable (pure transfer book); SPX $5,685.97 / $435.34 honest ($174
at realistic 4x lev). VERDICT on the owner's thesis: forward
profitability SUPPORTED at a modest blind baseline (~$13.7/trade on
$250 margin, BTC); the all-years ceiling is in-sample-flattered.
Discrepancy caught: live strikes trigger is RSI3<10 (code) vs <15
(docs) — ported as-code. Caveats: thin correlated data; every donchian
transfer rests on gold's validation. NEXT: the replay TOURNAMENT
(thousands of runs on this harness) + blind-slice as the standing
benchmark all future brain versions must beat.

## ROUND 71 — precision entries, iteration 1 (2026-07-24)
Trimmed core (96 cells/asset, BTC+ETH incl. fresh 5.4y ETH 5m): the new
architecture produced ZERO survivors — root cause identified: the fine
triggers (15m turn candle fires on ~50% of bars) ADD noise instead of
selecting (40-46% noise-stopout rate in the 15m/5m head-to-head); the
ladder was NOT monotonic with common triggers (inverts R58, whose 1h
reversal-bar trigger was RARE — rarity was the active ingredient).
R58's exact config re-confirmed under TAKER costs on BTC (train $22.47
x32 / val $52.20 x12) but did NOT fatten, FAILS ETH transfer, 35.9%
fee-share, 8.7 tr/yr. ITERATION 2 DESIGN (make-it-work): triggers must
be EVENTS not candle colors — level-anchored setups (range edges,
prior-day extremes, pools) + structural sweep-reclaim/displacement
triggers on 15m/5m; full 1,300-cell grid ready per results section 8.

## ROUND 72 — TJR 2026 strategy (2026-07-24)
Distilled from his own 58-min video: sweep session/1h/4h liquidity ->
5m BOS/IFVG confirm -> 5m continuation -> 1m retrace-entry, partials to
the next pool; ES+NQ alignment filter. GAUNTLET: NQ 1h 7/16 survive
(extended window), ES 2/16 (only with HIS alignment filter OFF), SPY
0/16, BTC full-cascade transfer 1/16. Claimed 64.29% WR never
reproduces (42-58% everywhere); flat 1.0R beats his stated 1.33R.
CAVEAT: index legs tested at 1h only (yfinance 60d cap below) — the
real 5m/1m cascade untested on home turf; paid intraday index data =
the unlock. KEEP: his sweep->confirm->retrace sequencing matches our
R64 fake-out finding — feeds R71-iter2 as first-class configs on deep
BTC 5m. No sealed looks (survivors are loosened-rule variants on thin
regimes).

## ROUND 73 — Alex Gonzalez (fxalexg) 10h course (2026-07-24)
Distilled: body-close market structure (wicks excluded) -> break of a
structure point -> retest -> ENGULFING confirmation (his stricter rule:
must engulf the prior TWO bodies) -> stop beyond the invalidating wick,
min 1:2 R:R. Same mechanism for his "reversal" and "continuation"
chapters. He trades FOREX on camera exclusively (GBPCHF/USDJPY/GBPJPY/
EURUSD/USDCAD/NZDCAD/USDCHF) despite claiming indices/commodities/crypto.
CLAIMED vs REALIZED: claims 60-70% swing win rate; pooled realized at his
own 1:2 floor = 0-59%, MEAN 35.2%. His "$100 -> $1M" is walked back on
camera to "$300k -> $1M" with a mid-challenge account blow-up; risk
sizing is gut feel (100% of account on trade 1, "never below 35%").
GAUNTLET: 0 survivors / 106 configs — BUT 90 (85%) = INSUFFICIENT-SAMPLE
(his ~1 trade per 25-90 days vs our 2y intraday-derived depth). The one
deep dataset (BTC) cleared floors on 15/18 and FAILED all 15.
GAP NAMED: his real stack is W/D/4H context -> 1H/30m/15m entries; our
daily->4h approximation is shallower. FOLLOW-UP (R74): the DAILY-ONLY
version on 20+ years of free forex dailies — the honest test his
frequency actually deserves.
