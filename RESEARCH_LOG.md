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

## ROUND 74 — the fair test: structure->retest->engulf on 20-33y dailies
The R73 "not enough data" objection is CLOSED: all 9 instruments got
20-33 years (train windows alone 12-20y). VERDICT: his LITERAL full
stack never cleared 30/8 floors in 648 configs (max 26 train / 7 val);
realized frequency 0.48 trades/yr vs his stated 4-14/yr — as taught,
the system is nearly untestable through rarity, not breadth.
WIN RATE: pooled 38.9% (median 40%), survivors 42.8% — his 60-65%
claim holds NOWHERE; the survivors earn via R:R (1.3-2.5x), not hit
rate. ABLATION (the real finding): dropping the RETEST or dropping the
ENGULFING each 7-8x'd frequency and produced ALL 12 survivors — the
"retest AND engulf together" pair is the choke point. Per-instrument
irony: his own live pairs (USDCHF, USDJPY) = 0 survivors; BTC and SPY
(claimed but never traded on camera) = 3 and 1, BTC's break config the
round's best expectancy. CAVEAT: every survivor is an ABLATED cousin —
this validates generic break-and-continuation, not his recipe.
SYNTHESIS w/ R71-iter1 (rare triggers were R58's magic) — the program's
working rule: there is a SELECTIVITY SWEET SPOT; too little confirmation
= noise, too much = never trades. 12 candidates banked, no look spent.

## ROUND 77 — the real S&P playbook (2026-07-24)
209 configs, six new families on SPY/ES/QQQ 1h+1d. FROM 1 RARE SETUP TO A
PLAYBOOK: tradeable survivors — vol-gated opening-range breakout (SPY 1h,
3/3, val edge RISES as the gate tightens $0.27->$1.71->$3.75/t, 66-132
tr/yr); squeeze->expansion (ES, 5/12, both directions, 48-105 tr/yr);
opening-range breakout+fade (6/32, 83-113 tr/yr); Mon->Fri weekly hold
(~46 tr/yr). Rare-but-real: turn-of-month N=3 (R60's flagged t=2.43,
now built, ~12/yr); SPY/QQQ catch-up divergence (one-sided: buy the
laggard only); vol-gated dip-buy (gating adds nothing to R60's config).
GRAVEYARDS: pullback-in-trend 0/24; THE STRUCTURE TOOLKIT 0/92 — our
best crypto edge does NOT transfer to the index, decisively; mid-session
reversal 0/12; gap-reaction 0/8. All train+val only; sealed looks not
yet spent; still no venue.

## ROUND 78 — the oil playbook (2026-07-24)
290 configs on CL/BZ/USO. THE OVERDUE VERDICT ON WHAT WE WERE RUNNING:
gold's donchian+structure-trail is directionally real on oil DAILY
(transfers CL<->BZ) but fires 3.4/yr AND LOSES on the 1h timeframe we
were also running it on; the index RSI2 dip-buy FAILS on all 5 datasets
both timeframes. Neither was ever oil-validated. Train/val surfaced two
candidates — the RSI2 spike-FADE short and an EIA-Wednesday REVERSAL
(the release-hour reaction is a fade, not a continuation: all 12
continuation configs failed) — and TWO SEALED LOOKS WERE SPENT ON EACH
(erosion ~+29): EIA-Wed reversal 4h: CL -$4.99/t x25, BZ -$4.16/t x25
FAIL; RSI2 spike-fade short: CL -$21.47/t x86, BZ -$22.65/t x76 FAIL
(ungated -$20.67 / -$17.69, also FAIL). CAVEAT: the 1h sealed window is
only 0.5y and coincides with a hard oil rally, which is brutal to any
short — but the rule stands. OIL STILL HAS ZERO VALIDATED STRATEGIES,
and now we also know the borrowed ones don't hold up. Also dead: sweep-
and-reclaim 0/12, USO 0/40 (the retail-tradeable instrument).

## ROUND 85 — what real winning trades required (2026-07-24)
36 documented setups from 24 sources, recording THE CONTEXT EACH TRADER
REQUIRED before a setup counts. ★ THE FINDING, and it is a correction of
our own work: R58 concluded REGULAR RSI divergence is noise (1 survivor
in 96). But R58's regular-divergence definition fired on ANY confirmed
swing with NO level-significance gate, NO confirmation candle, and NO
trend-extreme restriction — while its HIDDEN-divergence definition DID
implement the one condition the literature calls mandatory (trend-intact
gating). So the asymmetry in our own results (regular = noise, hidden =
sealed PASS +$52.03/t, live) is explained by TEST SPECIFICATION, not by
the patterns. We measured an under-specified test and reported it as a
dead pattern. Wallace was right that "it's famous for a reason."
Also omitted across R76: MACD crossovers never gated on structural
confirmation; breakout survivors never volume-gated; pivot/range
reversion tested with no regime gate. 8 precise testable proposals
produced -> R86.

## ROUND 83 — does the eye improve the strategies we already own? (2026-07-24)

Question: now that the machine can read a chart, does that read make our
EXISTING live strategies better? Tested as a veto — take each strategy's
real backtested trade list, partition it by what the eye saw at each
trade's own entry bar, and compare against 200 random skips of the same
size (the "dumb control"). 6 strategies x 2 assets x 3 veto rules.
Sealed test never touched. Full write-up: step83_results.md.

**One clear win, and it is now LIVE.** daily_pick's washout dip-buy is the
only trigger in the whole book that reads a bare oscillator with no
structural context of its own. Skipping the washouts that fire while the
eye reads "messy" beat the random control at the **98th percentile on
BOTH BTC and ETH**:

| Asset | washout before | after messy-veto |
|---|---|---|
| BTC | **-$6.42/trade** (47) | **+$24.87/trade** (20 kept) |
| ETH | $9.78/trade (47) | **+$54.26/trade** (15 kept) |

The skipped trades were net losers on both assets (-$799 BTC, -$354 ETH),
which is the whole point: the eye found the losers, not just fewer trades.

**Five strategies REJECTED the eye, three of them actively harmful.** News
momentum, hidden divergence, CHoCH+confluence and the vol-gated trend
champion all already encode trend/structure/volatility in their own entry
rules, so the eye's read is redundant — and worse, "messy" often fires on
the compression right BEFORE a breakout's biggest winners. D-BTC
tradeable-veto (8th pctile), E-BTC messy-veto (6.5th) and F-ETH routed
(8.5th) are all worse than random. The rule that came out of this:
**add the eye where the strategy doesn't already have eyes of its own.**

Live anecdote (n=9, corroboration only): the messy-veto would have caught
three of the book's four worst July losers, at the cost of its single best
winner (oil +$58.39). Retained set improves -$7.14 -> -$5.29/trade.

Open lead: donchian-20 (C) clears 90% via a DIFFERENT veto variant on each
asset — needs a round proving ONE fixed rule holds out-of-sample.

SHIPPED: `daily_pick.score_instrument` calls `chart_reader.read_chart` and
drops the washout vote on "messy" — washout only, fails OPEN if the reader
errors (a broken eye must never silently kill a live trigger).
`test_q_eye_vetoes_messy_washout` pins all four behaviours, including that
no other trigger got gated. chart_reader's matplotlib import was moved
inside the renderer: it is a local-only dev dependency and a module-scope
import on the live path would have taken the worker down on deploy.

## ROUND 84 — the blind chart drill (2026-07-24)

Wallace's own training method, mechanized: render a chart up to a decision
bar, decide the trade BEFORE the future exists, then reveal and score.
Harness `step84_blind_drill.py` (generate / record / reveal /
causality_test). Discipline was real: all 40 before-images rendered first,
after-images did not exist on disk until every call was locked. Causality
proven, not asserted — the same decision bar renders BYTE-IDENTICAL with
and without ~50,000 future bars available.

40 drills, BTC 1h/15m + ETH 1h, stratified across market states.

**Headline: a chart read alone is not an edge.** Overall **-0.056R**,
12W/20L/8 no-trade. Broken down, one leak dominates:

| | n | avg R | record |
|---|---|---|---|
| Longs | 19 | **+0.255R** | 8W/9L |
| Shorts | 13 | **-0.544R** | **1W/11L** |

Shorts stopped out 62% of the time vs 42% for longs. The specific error,
visible across d002/d017/d040: a candle breaking a nearby level after a
sharp move was read as "momentum confirming down" when it was the
shakeout at the extreme. The tell that separated the ONE winning short
(d018) from the eleven losers: d018 broke to a genuine new multi-DAY
extreme, the losers only cleared a multi-HOUR local level inside a bigger
range. **Local-level breaks are noise; structural-level breaks are not.**
This is a concrete, testable feature the eye does not currently compute.

**Worst reliable state: `transition`** (n=12) at **-0.320R**, 2 wins in 9
trades. Exactly where structure is mid-change and direction is honestly
undetermined. Trending states were ~breakeven (-0.04R, n=24).

**Second lesson (d007/d024 won, d037 lost on the SAME surface pattern):**
consolidation at highs is only a flag if the move that produced it is
FRESH. d037's had already run 2930->3670 before consolidating and it
topped exactly there. Distance-from-start-of-leg is a feature I was
eyeballing and not weighing.

**THE TENSION WITH ROUND 83, stated loudly rather than buried.** In this
sample "clean" setups did WORSE (-0.394R, 10/16 stopped) than "messy"
ones (+0.251R, 6/16), and the 14 trades where I AGREED with
chart_reader's tradeable flag averaged -0.200R versus +0.032R on the 18
where I overrode its "stand aside." That is the opposite sign to R83,
which is why the shipped veto stays for now: the two rounds measure
different populations (R83 = one mechanical oversold dip-buy strategy,
n=94 trades, 200-draw random control, 98th pctile on BOTH assets; R84 =
discretionary calls at 40 stratified arbitrary bars, four buckets of
n=14/18/2/6). "Messy is bad for oversold dip-buying" and "messy bars are
fine to trade in general" can both be true. But this is now a live
question, queued below, and the answer decides whether the veto stays.

Working hypothesis for why obvious setups underperformed: a setup that
looks tradeable to a simple rule-based eye looks obvious to everyone
watching the same chart, and crowded obvious trades get faded.

Files: step84_blind_drill.py, step84_drills.csv, step84_results.md,
step84_drill_images/ (80 PNGs).

## ROUND 86 — the properly-specified retests (2026-07-24)

R85 showed several of our "this doesn't work" verdicts had measured tests
missing conditions practitioners treat as mandatory. This round re-ran all
8 corrected specifications ALONGSIDE their under-specified predecessors,
same data, same costs, only the gate changing. ETH transfer MANDATORY on
every BTC survivor. Sealed test never touched.

| Family | Before survivors | After survivors | ETH transfers |
|---|---|---|---|
| A1 divergence, level-gated | 2 | 8 | **0** |
| A2 divergence, CONFIRMATION-gated | 2 | 11 | **3** |
| A3 divergence, trend-extreme | 2 | **0** | n/a |
| A4 all three combined | 2 | 7 | **0** |
| B MACD + structural confirm | 0 | **0** | n/a |
| C breakout, VOLUME-gated | 2 | 3 | **3** |
| D sweep->MSS->displacement | 0 | 0 (sample-starved) | n/a |
| E stricter ORB | 1 | 7 | **0** |

**Does properly-specified regular divergence survive? YES, via exactly one
gate: the confirmation candle.** Do not enter on the divergence bar. Wait
(up to 30 bars) for price to close back through the swing sitting BETWEEN
the two divergent points; that close is the entry. MACD-histogram on 4h,
3 configs clear BTC and transfer to ETH ($45-72/trade ETH val). This is
the single condition the literature called the #1 failure mode when
skipped, and it is the only Family-A gate carrying non-BTC-only signal.
Level-gating was nearly a no-op (0 transfers). Trend-extreme restriction,
as operationalized here (ATR-distance from SMA100), killed the family
outright. Stacking all three added NOTHING beyond confirmation alone.

**STRONGEST CANDIDATE — volume-gated breakout, and it is the first thing
we have ever found that matches the owner's frequency demand:**

| Config | BTC train/val | ETH train/val | trades/yr |
|---|---|---|---|
| Bollinger 20/2.5 bare (R76) | $14.71 / $1.48 | $33.43 / $17.38 | 213 |
| **Bollinger 20/2.5 + vol>=1.2x** | **$14.87 / $5.21** | **$39.59 / $26.01** | **203** |
| Bollinger 20/2.5 + vol>=1.5x | $9.39 / $7.17 | $61.26 / $18.15 | 191 |
| BB-in-KC squeeze bare | $5.12 / $0.19 | $2.70 / **-$7.55 FAIL** | 211 |
| **BB-in-KC squeeze + vol>=1.2x** | $17.73 / $9.87 | $9.37 / **+$4.04 PASS** | 114 |

The cleanest before/after in the round: requiring the breakout bar's own
volume to beat 1.2x its 20-bar average turned BB-in-KC squeeze release
from an ETH-transfer FAILURE into a PASS. Volume separating real breakouts
from false ones, demonstrated as an actual flip rather than a wash. At the
tighter 1.5x threshold it cut the sample enough to flip BB-in-KC to FAIL,
the "no-op or hurts" possibility R85 flagged, realized on 1 of 4 configs.

**The discipline this round exists to enforce, working: only 7 of 41 BTC
survivors (17%) transferred to ETH.** Stricter ORB looked like a big BTC
win (1 -> 7 survivors) and ALL 8 ETH replays failed. Family D is honestly
sample-starved (median 3 train trades/config), not disproven.

Sample quality: breakout survivors carry 150-260 trades per split; the
divergence-confirm survivors carry 13-24 (real direction, uncertain
magnitude — read those big per-trade figures with that caveat).

NEXT: one sealed look on Bollinger 20/2.5 + vol>=1.2x, BTC and ETH.
GATED on the owner (profitability-affecting work, standing rule
2026-07-22) — flagged, holding.

## ROUND 87 — THE SEALED EXAM: volume-gated Bollinger breakout (2026-07-24)

One-shot irreversible look, config frozen by R86 on TRAIN only. Sealed
look spent (erosion counter +1). Signal/gate code IMPORTED from
step86_specified.py, not retyped.

**Reproduction check passed to the penny before the sealed slice was
touched** — BTC train $14.87 / val $5.21, ETH train $39.59 / val $26.01,
all four reproduced exactly, so the split and signal had not drifted.

### RESULT: PASS on both assets. Our first sealed graduate that trades often.

| Asset | Train | Val | **SEALED** | n (sealed) | trades/yr | win rate | max DD |
|---|---|---|---|---|---|---|---|
| BTC | $14.87 | $5.21 | **+$6.97** | 242 | 191 | 36.4% | -23.3% |
| ETH | $39.59 | $26.01 | **+$9.68** | 226 | 211 | 37.6% | -35.0% |
| Pooled | | | **+$8.28** | 468 | ~400 | 37.0% | |

Pooled sealed PnL +$3,876 over ~15 months.

**BTC is the durable leg.** The big drop happened at train->val, which is
exactly where selection is supposed to punish overfitting; val->test then
held flat ($5.21 -> $6.97) on 242 trades. Two independent out-of-sample
windows agreeing in the same $5-7 band is the shape you want.

**ETH is fragile and is labeled that way, not averaged into the good
news.** $39.59 -> $26.01 -> $9.68 is two consecutive halvings with no
plateau. Still positive, still passes, but the trend points at zero. Size
BTC heavier than ETH; do not plan around $9.68.

### RISK PROFILE measured for deployment (adverse excursion, sealed trades)

Computed per trade as the worst move against the position while it was
open, since this strategy has NO fixed stop (exit is the band midline):

| | BTC | ETH |
|---|---|---|
| 90% of trades never went worse than | -2.19% | -3.48% |
| 99% never went worse than | -3.78% | -6.61% |
| WORST single trade | **-3.93%** | **-7.19%** |
| hold time median / p95 / max | 15h / 38h / 65h | 14h / 40h / 81h |

This gives a disaster stop that is provably NON-BINDING on the sealed
sample: **BTC 6%, ETH 11%** (roughly 1.5x the worst observed excursion).
Neither would have triggered on a single one of the 468 sealed trades, so
they do not alter the tested strategy — they exist only to survive a
worker outage or an exchange gap, satisfying the standing "stops always
live on the exchange" rule without changing what was validated.

### TWO HONEST DEPLOYMENT PROBLEMS, both unsolved as of this entry

1. **Book collision.** daily_pick already trades BTC-USDT and ETH-USDT on
   the same netted BloFin account. A second book on the same symbols is
   the exact failure mode that produced the gold false-alarm loop. Needs
   real attribution through book_ledger plus a contradiction rule, not a
   hope that they never disagree.
2. **Hold time vs the owner's stated identity.** Median hold is ~15h,
   max 81h (3.4 days). Wallace: "I heavily fancy fifteen minutes and
   below... I don't like four hours whatsoever," because 4h meant
   multi-day holds. This validated edge is a multi-hour-to-multi-day
   system. That tension is real and is his call, not mine to quietly
   average away.

## ROUND 88 — the veto we shipped tonight does NOT hold. Reverted. (2026-07-24)

R83's one shipped conclusion, attacked deliberately. The live change had
rested on 2 cells out of 36 clearing the 98th percentile — and with 36
cells, ~0.7 are EXPECTED to clear it by luck. The only real argument was
"two different assets agree." R88 tested whether that survives contact
with a third. It did not.

**Attack 1, a third asset (the cleanest test):**

| Asset | before | after messy-veto | control pctile |
|---|---|---|---|
| SOL | -$47.13/t (27) | -$35.35/t (9) | **68.0% — no signal** |
| XRP | $6.39/t (30) | $29.25/t (19) | 92.0% — passes |
| DOGE | -$25.18/t (21) | **-$38.33/t** (7) | **36.0% — the kept set got WORSE** |

1 of 3. And **SOL is a symbol daily_pick actually trades** (UNIVERSE =
BTC, ETH, SOL, XAUT). We had shipped a filter onto SOL with no evidence
and onto XAUT with none at all.

**Attack 2, the parameter neighbourhood:** genuinely not a knife-edge —
with the turn-candle guard on, BTC clears the 90th at 10 of 11 nearby
configs, a real plateau. But the plateau is entirely conditional on the
guard (guard off flips 70% of cells actively harmful) and does NOT
reproduce on the new assets: the exact live config lands 65.5th on SOL
and 39.5th on DOGE.

**Attack 3, time-split:** BTC and ETH both hold across chronological
halves (87th-96.5th). Real for those two. But that was never the open
question.

**The number that decided it:** across 122 scored cells, 28 cleared the
90th percentile where ~12 are expected by chance — but **45 landed at or
below the 10th where ~12 are expected.** The eye's read carries real
information and it is DOUBLE-EDGED, and we cannot predict in advance
which edge a given symbol gets. That makes it undeployable as a blanket
filter no matter how good the best cell looks.

**ACTION TAKEN: the veto is out of daily_pick.** Washout trades its own
rule again (oversold + daily trend + turn candle). `test_q` was rewritten
from "the veto works" into a REGRESSION GUARD that fails if any eye gate
is re-added. chart_reader's ADVISORY_ONLY exception was revoked.

**STANDING RULE EARNED HERE: two assets agreeing is a hypothesis, not
evidence. Test a third and a fourth before anything ships.** R83 was not
sloppy about its method — the random control, the causality, the
partitioning were all sound. It was sloppy about MULTIPLE COMPARISONS:
36 cells were run and the 2 best were treated as a finding. Every future
round that sweeps many cells must state its expected-by-chance baseline
in the same breath as its winners.

## ROUND 90 — R84's level-significance lesson is REFUTED, and inverted (2026-07-24)

R84's blind drills produced a confident lesson: the one winning short broke
a multi-DAY extreme, all eleven losers only cleared multi-HOUR local
levels, therefore "local breaks are noise, structural breaks are
tradeable." R90 tested that mechanically on 25,481 real break events (BTC
+ ETH, 1h + 4h, full history, no-lookahead verified by a truncation test
producing byte-identical events).

**It is not just unsupported, it is BACKWARDS on the short side.** BTC 1h
shorts, full train sweep:

| level age cutoff | n | expectancy/trade |
|---|---|---|
| 20 bars | 380 | -$9.23 |
| 50 | 228 | -$26.21 |
| 100 | 142 | -$35.49 |
| 200 | 95 | -$57.70 |
| 500 | 47 | **-$89.12** |

LOCAL shorts sit flat at -$12 to -$13 regardless of cutoff. **Structural
shorts get monotonically WORSE the older and more-tested the broken level
is** — 10x worse from the loosest to the tightest cutoff, monotonic across
every step, and BTC 4h reproduces the identical pattern (-$73.86 ->
-$180.15). This is not threshold-selection: it holds across the ENTIRE
swept grid on both timeframes.

Long side: BTC structural longs looked strong (1h +$57.63 train / +$13.85
val; 4h +$254.57 / +$126.10) and **FAILED the mandatory ETH transfer** on
both timeframes (val -$30.32 and -$85.77, config carried over unchanged).
Reported FAIL. Honest caveat recorded by the round: ETH's LOCAL bucket
also went negative in that same val window, so it may be a bad ETH stretch
for long breakout entries generally rather than proof the idea is fake.

Freshness hypothesis (R84's second lesson, "consolidation at highs only
works if the prior move is fresh"): NO SUPPORT. The only adequately
sampled cell was unprofitable in both fresh and extended buckets and the
train-favorable gap reversed on val. Also flagged a real limitation: the
leg-start definition resets too often to capture genuinely extended
multi-week runs like d037's, so this is a weak test, not a strong refutation.

**RECOMMENDATION TAKEN: no change to chart_reader.py.** Do not add a
structural-favors-shorts heuristic (the data says the reverse), do not add
the long-side version (BTC-only, failed transfer), do not add a freshness
gate (unsupported).

**THIS IS THE SECOND TIME TONIGHT a confident lesson from a small sample
died under mechanical testing** (R83's veto was the first). R84's story was
built on 12 discretionary shorts. Twelve trades produce a compelling
narrative and no evidence. The pattern to remember: a vivid post-mortem is
a hypothesis generator, never a finding.

**WHAT IT HANDED US INSTEAD:** if breaking an aged, well-defended level is
a progressively WORSE short, the fade may be the trade. Queued as R92 with
the drift control that decides whether it is real — see RESEARCH_QUEUE.

## ROUND 91 — the pro's read is too RARE to mechanize on the daily (2026-07-24)

The owner posted a Friday review from an analyst he follows (Prof Michael,
TRW). I fact-checked every checkable claim against real market data first
and all of them held (SPY's squeeze to 743.72 then a full round-trip to
738.93, QQQ closing at new lows, BTC's 3 red days and close below 65K,
oil's retrace, the dollar's grind). Descriptive accuracy verified, so his
METHOD was worth testing mechanically.

Coded as a no-lookahead state machine on BTC daily (Bitstamp spot, 14.9
years) and ETH daily: rally tags a prior significant swing high -> N
consecutive red closes -> the interim minor swing low breaks -> forecast a
LOWER HIGH rather than continuation. Swept N in {2,3,4} x closed-basis vs
wick-basis.

**VERDICT: INSUFFICIENT SAMPLE, not FAIL.** At the loosest defensible
settings this exact pattern fires **2 to 5 times in fifteen years**
(0.17-0.34 per year). Zero of 6 BTC cells cleared the 30-train/8-val
floor, so the ETH transfer never ran — there was nothing to transfer.

The detector is not broken: its N=3 closed-basis triggers are real,
identifiable BTC events (Jun 2020, the Apr 2021 top, Aug 2022, Apr 2024,
Feb 2025). The forecast resolved correctly 5 of 5. That is a 100% hit rate
on five events across fifteen years, which is a nice anecdote and not an
estimate of anything.

**The closed-basis discipline did NOT pay in dollars here** (wick-basis
matched or beat it at every N; at N=4 closed-basis was -$2,301 worse). But
at n=2-5 per cell this means nothing in either direction, and it should
not be quoted as evidence against him.

**What this actually teaches:** his edge is not a mechanical rule we can
lift. It is judgment applied to a rare, high-context situation, and the
thing worth copying is the DISCIPLINE (a specific invalidation level
stated in advance, closed-basis confirmation, a forecast that can be
scored) rather than the pattern. The pattern itself, at daily resolution,
is a once-every-three-years event.

Follow-up queued as R93: run the identical state machine on 4h and 1h,
where the same logic should fire 20-50x more often and can actually be
judged. That also moves it toward the timeframes the owner prefers, since
he has said repeatedly he does not want daily/4h multi-day holds.

## ROUND 89 — the breakout does NOT generalize. It is a BTC edge. (2026-07-24)

The frozen R86/R87 config replayed with zero tuning on nine never-seen
assets (SOL, XRP, DOGE, BNB, ADA, LINK, AVAX, LTC, DOT). Free evidence —
no sealed data existed on these to burn.

**6 of 9 fresh assets FAIL outright.** The run's own summary line reads
"5/11 PASS, 927.7 trades/year" — that is a POOLED full-history number and
it is a trap. Read the windows instead:

| Asset | train | val | test | all 3 positive |
|---|---|---|---|---|
| BTC (sealed) | +$14.87 | +$5.21 | +$6.97 | YES |
| ETH (sealed) | +$39.59 | +$26.01 | +$9.68 | YES |
| AVAX | +$13.83 | +$2.63 | +$12.19 | YES |
| SOL | +$25.27 | -$1.96 | +$11.86 | no |
| XRP | -$10.78 | +$84.83 | +$18.88 | no |
| DOGE | -$12.21 | +$82.15 | -$17.11 | no |
| DOT/LINK/BNB/LTC/ADA | all negative pooled | | | no |

XRP swings -$10.78 / +$84.83 / +$18.88 and "passes" on the pool. That is
a number wandering, not an edge.

**AVAX is exactly what luck predicts and therefore counts for nothing.**
Nine assets x three windows: if the config had no edge and each window
were a coin flip, ~1.1 assets show all-three-positive by chance. We
observed 1. Same multiple-comparisons discipline that killed the eye veto
tonight, applied to a result that happened to favour us.

**Second, independent reason not to run the altcoins: ruin-level risk.**
This strategy has no fixed stop. Worst single-trade adverse move: BTC
-3.93%, ETH -7.19%, but SOL -27.9%, XRP -28.9%, LINK -29.4%, DOGE -32.1%.
Max drawdowns of -81% to -87% on five of the nine. The 6% disaster stop
that is provably non-binding on BTC would fire constantly on these; a stop
loose enough not to fire leaves ~30% of position value unprotected. XRP
"passes" at +$2.89/trade with an 81% peak-to-trough drawdown.

**DECISION: deploy on BTC only.** ETH stays flagged fragile at reduced
size. The honest frequency for this family is **~191 trades/year on BTC**,
~400 with ETH — NOT 927. BTC's sealed pass is untouched by this round; what
died is the expansion story, not the edge.

## ROUND 93 — the pro's pattern on fast timeframes: 0 survivors (2026-07-24)

R91 found the analyst's setup fires only 2-5 times in 15 years on the
daily. R93 ran the identical imported state machine on 4h, 1h, 15m and 5m,
where sample finally exists. 24 BTC cells (4 timeframes x N in {2,3,4} x
closed-vs-wick basis). **0 SURVIVORS**, against 0.60 expected by an
empirical randomized-timing control computed per timeframe (not an assumed
coin flip) — the chance-baseline discipline is now standard in every round.

**4h: FAILS ON COSTS, and this is the interesting one.** N=2 wick-basis
was gross-positive on BOTH train (+$15.17/trade) and val (+$7.04/trade) —
a genuine survivor at zero cost. Real costs (12bps round trip plus
funding, 10.6bps measured drag) flipped val to **-$2.42 net**. The pattern
needed more than 10.6bps of edge per trade and did not clear it. The edge
is REAL and too SMALL, which is a materially different finding from "the
idea is wrong."

**1h, 15m, 5m: FAIL outright** — no gross edge to lose in the first place.
Not a cost problem at those speeds; the pattern simply does not
generalize down there in the cells tested.

**Closed-basis vs wick-basis, finally with real sample:** the sign flips
inconsistently across N and timeframe (4h N=2 closed beats wick by +$840;
4h N=3 wick beats closed by +$1,175; 5m mixed). **No durable evidence
either basis is worth money.** Worth stating carefully: this does not make
the analyst wrong. Demanding a close is a discipline that reduces
false signals for a discretionary trader managing risk in real time; our
test only shows it does not by itself produce a mechanical edge.

This is the fourth independent confirmation of the project's oldest
finding: **dense intraday rules die on the ~9-12bps cost floor.** Every
future fast-timeframe candidate must be judged gross AND net from the
start, with the break-even bps stated up front.

Design note recorded honestly by the round: R91's MAX_HOLD_DAYS=45 /
SEARCH_WINDOW=25 were carried over as literal BAR counts rather than
recalibrated per timeframe, so holds scale with the timeframe (5m -> 3.75h
cap, 4h -> 7.5 days). Defensible and stated, not hidden.

## ROUND 92 — fade the aged breakdown: DRIFT, not an edge (2026-07-24)

R90's inversion tested with three mandatory controls. The primary result
looked excellent: buying the breakdown of an aged structural level (BTC
1h, age>=500) returned **+$86.96/trade train (93rd pctile vs random) and
+$147.71 val (98th pctile, 76% win rate)**. That is exactly why the
controls exist.

**CONTROL 2, THE MIRROR — FAILS, decisively.** If aged levels genuinely
mean-revert, shorting aged RESISTANCE broken upward must work too. It is
negative in **all 30 mirror cells across both timeframes**, and mostly
BELOW chance (14th-33rd percentile of a random-entry control), getting
monotonically worse with level age. The pattern is not "aged levels snap
back", it is "long works, short does not" — which is what an uptrending
sample manufactures.

**ETH TRANSFER — FAILS.** 1h train +$298.28 (100th pctile) -> val
**-$23.57**. 4h train +$53.12 -> val **-$91.31**. A 100th-percentile train
collapsing to negative val is the signature of fitting.

**CONTROL 3, regime split — the one point in its favour, recorded not
buried:** buying breakdowns stayed positive in the BEAR regime on adequate
sample (1h, n=63, +$104.11). Genuine evidence against pure drift. Not
enough to survive the other two failures.

**Multiple comparisons:** 60 cells swept, ~6 expected above the 90th
percentile by chance, best cell at the 93rd. The headline was inside luck
before the mirror even spoke.

**VERDICT: DRIFT. No deployment, no live change.**

### THE CONVERGENT FINDING WORTH KEEPING

Three independent studies tonight, three methods, same answer:
- R84 (40 blind chart drills): shorts 1W/11L, -0.544R; longs +0.255R
- R90 (25,481 mechanical break events): structural shorts monotonically
  worse with level significance, -$9 -> -$89/trade
- R92 (30 mirror cells): shorting aged upside breakouts negative
  everywhere, below a random-entry control

**Shorting BTC structurally does not work in this data.** Honest limit on
that claim: we cannot distinguish a permanent property of the asset from
an artifact of a 2020-2026 sample that trended up, and that distinction
matters before it becomes doctrine. What it justifies today: stop
spending rounds hunting BTC short setups, and treat every future short
candidate as guilty until it clears a bear-regime-only test.

## ROUND 110 — the live oil book was never validated. STOOD DOWN. (2026-07-25)

First finding from the new per-market desk (oil-trader, under morgan).

**What was actually running:** daemon -> tradfi_engine, a paper book on
CL=F. Its entry/exit logic was `daily_pick.score_instrument` — the CRYPTO
learning engine's scorer — imported unchanged, plus `_stop_target_pct`
(stop = 1.0x ATR capped at a flat 1.0%), CONVICTION_FLOOR 40, 6h cooldown.
**Every threshold in it was tuned on BTC/ETH/SOL and none was re-derived
for oil.**

**How it got there:** R78 tested the rules live that MORNING (gold's
donchian, the S&P's RSI2 dip) and both FAILED on oil. tradfi_engine.py was
written LATER THE SAME DAY with a different rule set, and that swap was
never re-gauntleted. No mention of it being backtested on oil exists
anywhere in this log or MARKET_PLAYBOOKS.md.

**The replay** (walk-forward of the EXACT live decision loop, every
function imported not reimplemented, CL=F 2024-03 to 2026-07, 1,888
trades, 60/20/20 with the sealed 378 untouched, taker 10bps round trip):

| split | n | expectancy | vs 500-resample random-timing control |
|---|---|---|---|
| train | 1,132 | **-$37.10/trade** | 81st pctile |
| val | 378 | **-$54.05/trade** | **8th pctile** |

Negative on both. Thickness -0.96x and -1.47x round-trip cost — below the
5x bar by being NEGATIVE, not merely thin. Train-good/val-worse-than-noise
is the textbook signature of an in-sample-only fit.

**Structural violation independent of P&L:** 19% of its trades had the
stop set by the flat 1.0% cap inherited from crypto rather than by oil's
own ATR. A swept percentage on oil by construction — precisely what the
owner ruled out ("the stop loss is supposed to be based on the chart").

**The +$58.39 that has been sitting on our scoreboard as the only real
winner is n=1 under this rule set.** Confirmed luck, not skill.

**ACTION: oil removed from tradfi_engine's UNIVERSE.** Exits reconcile
from open trades independently of UNIVERSE, so the one open CL=F position
still closes normally on its own stop/target — standing an instrument down
must never orphan a live position, and `test_m_oil_is_stood_down` asserts
both that oil stays out AND that the exit path is not gated on membership.

**THE S&P LEG OF THE SAME ENGINE RESTS ON THE SAME UNVALIDATED BASIS** —
same crypto scorer, same crypto constants, never tested on SPY. It remains
only because it has not yet been DISPROVEN. spx-trader is testing it as
priority one; if it fails the same way, the engine stops entirely.

## ROUND 170 — 0 of 5 BTC edges survive on ETH (2026-07-25)

eth-trader's first round, and the most uncomfortable result of the night.
Every one of BTC's five validated edges replayed on ETH with the config
UNCHANGED, at taker costs, using the BTC signal code imported directly
(step56/step58/step45b) rather than reimplemented. ETH's own ATR was
recomputed fresh: 1h median 0.955%, 4h median 2.023% — roughly **2x BTC's
current decayed-era level**, which is the root cause of at least one
failure and probably a factor in others.

| BTC edge | BTC sealed | ETH result |
|---|---|---|
| 1h CHoCH k8 + confluence>=2 | +$99.52/t | **FAIL** all windows (train -$70.92, val -$195.96, sealed -$37.90) |
| 4h hidden RSI divergence | +$52.03/t | **FAIL** all windows (train -$54.24, val -$147.94, sealed -$8.78) |
| 4h vol-gated trend ("the ride") | live | **FAIL** unchanged at val |
| 1h RSI3 dip-buy | live | **FAIL**, and WORSE than random timing (0% survivor-by-luck in 30 draws) |
| News momentum | +$10.35/t | **FAIL** at val (train +$10.49, val -$25.31, sealed +$10.97) |

**The single most damning detail:** on CHoCH the dose-response INVERTS.
On BTC, more confluence agreement means better results. On ETH, more
confluence means WORSE. A real structural effect does not reverse sign
across two highly correlated assets; a fitted one does.

**The one live thread:** the vol-gated trend re-derived on ETH's OWN
numbers (min_atr_pct 2.7% vs BTC's 1.5%, structure stop 12.68% replacing
the swept -8%) went train +$214/t and val +$26/t — BOTH POSITIVE, but on
22 and 5 trades, under the 30/8 floor. Correctly reported INSUFFICIENT
SAMPLE rather than dressed up as a survivor. Worth a dedicated round with
a looser MA pair to clear the sample floor.

**News momentum deserves its own note:** it was BTC's only sealed-pass
edge across the whole 45-round history, and it does not generalize even
to ETH.

### THE PATTERN THIS COMPLETES, AND IT IS THE NIGHT'S BIGGEST FINDING

Four independent results now say the same thing about our BTC work:
- R88: the shipped chart-read veto failed on a third asset (SOL showed no
  information content, DOGE was harmful) and had to be reverted.
- R89: a sealed-passed config replayed on nine fresh assets — 6 of 9
  failed outright, and the one apparent survivor was exactly what chance
  predicts from nine coin flips.
- R100: gold's own chance baseline showed most big-dollar "survivors" had
  16-32% odds of clearing the bar from RANDOM entries during a bull run.
- R170: 5 of 5 BTC edges fail on ETH, one with an inverted dose-response.

**Our BTC results are systematically more fitted than 50 rounds of
apparent rigour suggested.** The sealed-test discipline was real, but it
was applied one asset at a time, and single-asset sealed tests do not
catch asset-specific overfitting. Transfer does.

This does NOT automatically condemn the live BTC books — genuine
asset-specific edges exist (gold's donchian does not work on crypto and
nobody thinks that makes it fake). But it changes the prior sharply, and
it means **cross-asset transfer must become part of validation, not a
post-hoc check.** Recorded as a standing rule.

## ROUND 150 — 3 of BTC's 5 edges die at taker + structure stops (2026-07-25)

btc-trader re-tested all five documented BTC edges under the conditions we
ACTUALLY trade: execution="taker" always, and real per-trade chart-
structure stops via exits.py instead of the swept percentages and maker
fills they were originally validated under. Sealed slice never loaded —
these are train+val verdicts.

| Edge | Original sealed | Retest train / val | Verdict |
|---|---|---|---|
| 1h CHoCH + confluence>=2 | +$99.52/t | -$42.92 / +$70.61 | **DIED** |
| 4h hidden RSI divergence | +$52.03/t | +$15.20 / **-$9.30** | **DIED** |
| 4h vol-gated trend | +$401.30/t | -$12.18 / +$328.69 at buffer 0 | **RECOVERED** at 1.5% buffer: +$17.15 / +$99.37, **26.4x / 17.6x thickness — the night's strongest survivor** |
| 1h RSI3 dip-buy | live | **-$70.09 / -$69.54** | **DIED, worse than chance, twice** |
| News momentum | +$10.35/t | -$8.88 / -$15.25 | **DIED** (recovery is +$5.82/+$0.32 at **0.03x** thickness — an edge 3% the size of its trading cost) |

**Taker fees were secondary here.** Unlike the Bollinger breakout, these
did not die on the fee delta — they died on the STOP. A real per-trade
structure stop has variance that a train-median or flat percentage
silently erased: sometimes tighter than assumed (edges 4 and 5, win rates
collapsing to 27-41%), sometimes wider (edges 1 and 2, R-multiple targets
no longer reachable inside the hold window so trades drift to the time cap).

**ACTION TAKEN — three live books stood down for NEW ENTRIES ONLY:**
`tactical.py` (the strikes / RSI3 panic-dip), `diver.py` (hidden
divergence), `newsdesk.py` (news momentum). Each gate sits AFTER all
exit/reconcile logic, so open positions still close normally and the
would-be trade is still logged — standing a book down must never orphan a
live position. `test_z` guards in test_diver.py and test_newsdesk_exit.py
assert both the flag and the gate's position relative to the exit path.

`the ride` (edge 3) stays live and is the one edge that got STRONGER under
honest testing. Its flat -8% stop should become a structural trailing floor
with a ~1.5% buffer — a strategy change, so it needs its own round first.

## ROUND 190 — SOL: the edge that died at home survives abroad (2026-07-25)

sol-trader replayed the same five BTC edges on SOL at taker costs:

- **1h CHoCH + confluence>=2: SURVIVOR (unsealed)** — $218.95/trade over
  71 trades, 95th percentile against a random-entry control, **8.4x
  thickness.** This edge DIED on BTC under honest retest and DIED on ETH,
  and it is alive on SOL. Exactly the asymmetry worth hunting.
- 1h RSI3 washout: **1st percentile — an ANTI-signal**, second independent
  confirmation after R88 that it is actively harmful on SOL.
- Hidden divergence, vol-gated trend, news momentum: all FAIL.

**The mechanistic finding of the night:** SOL's median ATR is 3.07%, so
BTC's fixed 1.5% volatility gate is open on **96.7% of SOL's bars** versus
18-53% on BTC. The gate's SELECTIVITY is the entire edge, and it silently
evaporates when the constant is ported instead of re-derived. That is the
"never port a constant" rule with a number attached.

## ROUNDS 111-116 — the oil family map: 20 entries, zero WTI survivors (2026-07-25)

**The EIA inventory report reaction is REAL and NOT TRADEABLE.** R78 was
supposed to test this and never did; oil-trader finally ran it. At the
official Wednesday release hour: mean |move| **0.570%**, which is **1.75x
the same-window baseline and 2.2x a randomized-timing control**, decaying
to 1.07x by 24h. Continuation-shaped. The unofficial Tuesday API estimate
shows no detectable reaction at all — a clean negative.

Then it was built into an actual costed strategy (R114) and **it fails
train+val.** That RESOLVES rather than deepens the apparent conflict with
R78's sealed "EIA reversal" failure: both directions lose after real
costs. The price tendency is genuine; it is simply smaller than the cost
of harvesting it. Fifth confirmation of this program's oldest finding.

**The one real lead, and why it is not a green light.** Donchian(55) on
daily oil with a chandelier(3.5x ATR) trail-only exit, selected TRAIN-only
from a 9-exit screen, val read once:

- **BZ=F (Brent): train +$160.34/t (n=47), val +$101.13/t (n=17),
  thickness 15.87x** — the strongest number the oil map has produced, and
  it beats its chance baseline (val $101.13 vs random-entry mean $87.88).
- **CL=F (WTI): the identical config is NEGATIVE on its own train window
  (-$14.65/t, n=74).**

**WTI is the venue we can actually trade. Brent is not.** So this is a
disciplined, honest Brent-specific result that does not transfer to
anything executable. Sealed look NOT spent, correctly.

**LEAD AGENT'S CALL: do not spend the sealed look here.** It is best-of-9
on one instrument (expect ~0.9 cells to clear a 90th-percentile bar by luck
alone), and it fails on the only instrument we can execute. Spending an
irreversible look to confirm something untradeable is the worst available
use of that budget. Correct next move is the agent's own proposal: run the
identical 9-exit screen on CL=F. If the SAME chandelier pairing wins there
too, that is far stronger evidence than either instrument alone, because
the pairing would have transferred rather than been fitted to one
instrument's noise. And report whether the winning exit is a PLATEAU
across adjacent multiples or a lone spike — R88 killed a live change whose
effect existed at exactly one setting and nowhere in the neighbourhood.

**Other entries:** four ported crypto shapes (CHoCH+confluence, hidden
divergence, vol-gated trend, RSI3 washout) all INSUFFICIENT SAMPLE — oil's
event frequency for these triggers is far below BTC's on the ~2.4y of
intraday history available, itself a finding. SPX's RSI2 shape re-confirmed
FAIL under a real structural stop. Order blocks, pin bars and engulfing
confirmed dead on oil too — no BTC-dead-but-oil-alive asymmetry found.

**Session structure is a clean real diagnostic, not yet a strategy:**
London and NY hours sit at the **100th percentile** of realized |return|
against a 200-draw label-shuffle control; Asia and off-hours at the
**0th**. Real, oil-specific, structural. Nothing built on it yet.

OPEC meetings and contango/backwardation logged honestly as NOT TESTED /
NOT TESTABLE (no reliable meeting calendar, no futures-curve data in this
repo) rather than guessed at.

**HARNESS BUG FOUND:** `step150_common.verdict_for` does not enforce the
5x thickness bar, and would have mis-labelled two cells SURVIVOR.
oil-trader caught and hand-corrected them. A verdict function that
silently over-promotes is exactly how a fitted result reaches a live book
— fix before any other round reuses that harness.

## ROUNDS 130-135 — the S&P has REAL, TRANSFERRING edges (2026-07-25)

**First, a correction to my own brief.** I told spx-trader the index had
had 1 round and ~6 families. It found two prior rounds I had missed —
`step48_tradfi_trend.py` (donchian, already validated on SPY/QQQ) and
`step77_spx_playbook.py` (16 more families). True starting point was **~23
families across 3 rounds**, not 6. It added 19 more tonight, verified
against both prior rounds to avoid duplication: **~42 documented S&P
families**, which is now the deepest map on the desk after BTC. My
briefing error, caught by the specialist, exactly as intended.

**THE HEADLINE — turn-of-month, and it TRANSFERS.** The textbook
Xu-McConnell window (last day of month + first 3) FAILS on SPY val
(-1.6x thickness) despite passing on ES=F and QQQ. But R77 had already
found a **wider** window (3 days before month-end through 3 into the new
month) survives on SPY, and had never transfer-tested it. Replayed
unchanged:

| instrument | result |
|---|---|
| SPY | survives |
| ES=F | survives |
| QQQ | survives |
| thickness | **6.6x to 42x** round-trip cost, all three, both windows |
| sample | comfortably above the 30/8 floor |

Adding a real `exits.py` chart-structure stop on top (R77 used flat
percentages) it STILL survives on all three, though SPY's val thins to
3.95x — just under the 5x bar. **This is the strongest deployable
candidate on the desk, second only to RSI2<5.**

**RSI(3) dip-buy extends R60's RSI(2) plateau**, cross-instrument
confirmed at 7-28x thickness. That answers the "plateau or lucky spike"
question we have been asking all night with the good answer: **plateau.**
And the RSI2<5 edge proved robust to exit-method choice — chandelier,
structure-trailing and breakeven-after-1R all survive. An edge that
survives changing its exit is a real edge.

**A "give it room" result that generalizes:** adding a structural early-out
to the SMA200 regime backbone HURTS (SPY flips negative). The lesson
already known for stops applies to regime rules too.

**Gap magnitude (not direction) predicts ~1.3-1.5x wider intraday range** —
a genuinely useful stop-sizing input, not a strategy.

**13 families died tonight**, honestly: gap-day continuation and reversal,
gap-conditioned first-hour breakout, first-hour fade, turn-of-month-gated
dip overlay, ES=F donchian transfer, RSI divergence, volume-gated
breakout, options-expiry week, order blocks, candle patterns.

**A recurring transfer failure with a mechanism:** several families looked
thick (5x-40x) on ES=F ALONE and failed to transfer to SPY **every time**.
Likely cause, already flagged by R60 for overnight drift: ES=F's "gap" is
dominated by its ~1h maintenance-break print, while SPY's is a real 17.5h
information window. They are not the same event, so an edge fitted to one
is not an edge on the other. **ES=F-only results should be treated as
suspect by default.**

### THE UNCOMFORTABLE PART

The two best edges on the entire desk right now — turn-of-month and the
RSI2/RSI3 dip-buy family — are both in the ONE market we have no venue
for. BloFin serves no honest S&P instrument on demo (SPY-USDT exists on
prod, is the real tracker at 0.08% basis, but is thin at ~$650k/24h and is
not on the demo host). Finding a venue is now a higher-value action than
another research round.

## ROUND 194 — the GARCH storm-veto is ACTIVELY HARMFUL. Buried. (2026-07-25)

Nightly researcher. Queue item: the "GARCH era" docket's second
pre-specified entry — *"GARCH storm-veto for strikes: skip entries when
forecast > trailing p90"* — the item Round 31's own log entry named as
"next in queue" and which had never been run. Script:
`step194_garch_storm_veto.py`.

**Queue hygiene first.** RESEARCH_QUEUE.md's numbered list 1-6 was stale:
the 2026-07-23 credit-sprint batch closed items #2 (OI-flag-touch), #3
(post-settle long) and #4 (OI-breakout) — all FAIL train — the 15m
forensic autopsy closed #5, and Round 26 closed #6. The log had already
recorded this reconciliation; the file had not. Items 1-6 are BURNED and
the file is now corrected. The quarterly re-audits are dated 2026-10 and
are not due. That made the GARCH docket the top live section.

**Config (frozen from the queue, no tuning):** BTCUSDT 1h. Filter = 4h
champion bull state (vol_gated_ma 20/100, ATR gate 1.5%, funding<=1bp)
mapped onto 1h with no lookahead. Trigger = RSI(3)<15. Veto = skip when
the walk-forward GARCH(1,1) daily-vol forecast is at or above its
TRAILING EXPANDING p90 (min 180d baseline, no lookahead), same
construction Round 31 used on 4h. Bracket = the live one, stop 1.5% /
target 4.5% / hold 48h — flat percentages are FAITHFUL here because
tactical.py literally places a fixed ±% TP/SL bracket; Round 150's
structure-stop retest asked a different question. Execution = **taker**,
which is what the live book actually pays (execute_market_clips places
market orders). Real funding. Common window 2022-02-03 -> 2026-07-24
(39,183 bars, 4.5 yrs) so veto and baseline score identical bars.

**Declared before running (Round 88's rule):** exactly ONE cell decides —
p90, taker. ~0.1 cells expected to clear a 90th-percentile chance bar by
luck. The maker frame and the p80/p95 neighbourhood were reported as
robustness only and barred from qualifying anything.

### RESULT — fails three of four gates

| config (taker) | train n | train $/t | thickness | val n | val $/t | thickness |
|---|---|---|---|---|---|---|
| baseline, no veto | 139 | **+$9.64** | 0.54x | 43 | **+$35.20** | 1.96x |
| STORM-VETO p90 | 134 | **+$5.12** | 0.28x | 43 | +$35.20 | 1.96x |

- positive train AND val — PASS
- sample >=30 / >=8 — PASS (134 / 43)
- **beats the un-vetoed baseline — FAIL.** It nearly HALVES train
  expectancy and changes val by exactly nothing.
- **beats chance — FAIL.** 400 random draws dropping the same number of
  trades at random: the veto's train lands at the **18.5th percentile**
  and its val at the **28.7th**. Dropping trades with a coin would have
  done better than dropping them with the GARCH forecast.

### The two things that make this a real finding, not just a null

**1. A dose-response in the WRONG direction.** The neighbourhood is
monotone: the MORE the veto fires, the worse the book gets.

| threshold | signals killed | train $/t |
|---|---|---|
| p80 | most | **-$0.98** (negative) |
| p90 | 27 (2.7%) | +$5.12 |
| p95 | fewest | +$8.56 |

Extrapolate the line and it lands on the baseline's +$9.64 at "veto
nothing." That is not a lone spike and it is not noise around zero — it
is a clean monotone gradient saying the veto is *actively harmful*, and
harmfulness scales with how often it fires. Round 88 taught us to ask
"plateau or spike"; this one answers with a third and more damning shape.

**2. The veto is nearly inert, which is itself the mechanism.** The p90
storm filter kills only **27 of 983** panic-dip signals (2.7%) and
**zero** val signals. GARCH forecast-vol storms and 1h RSI(3) washouts
inside a 4h bull state barely co-occur — the champion's own 1.5% ATR gate
has already spent the volatility budget, so by the time a dip fires, "is
today forecast to be violent" carries almost no marginal information. A
filter that cannot fire cannot rescue anything. This is the same lesson
as Round 31 from the other side: **the GARCH forecast keeps failing
against instantaneous ATR because the ATR gate is already doing the work,
on both the slow book and the fast one.**

**VERDICT: FAIL. The GARCH storm-veto family is CLOSED. The stood-down
strikes stay stood down — this was their pre-specified rescue attempt and
it made them worse.** Sealed test window NOT opened. **Looks consumed
this round: 0.**

### An honest side-observation that must NOT be misread as a reprieve

On this window and with the LIVE flat bracket, the un-vetoed strikes score
**+$9.64/t train and +$35.20/t val at taker** — not the -$70.09 / -$69.54
Round 150 reported. Before anyone reads that as "R150 was wrong": the two
runs are not the same test. R150 replaced the flat bracket with real
`exits.py` chart-structure stops and used the full history; this round
reproduces the live fixed ±% bracket on the shorter GARCH common window
(2022-02+). R150's own conclusion was that these edges "died on the STOP,
not the fee" — this result is *consistent with* that, and isolates the
exit as the whole story. It is emphatically **not** grounds to restart the
book: thickness is 0.54x round-trip cost on train (an edge roughly half
the size of its own trading cost), it is train/val only, and it is one
window. Queued below as its own properly-controlled round, because
"which exit is right for the panic-dip" is now a well-posed question with
two contradicting measurements pointing at it.

**HOUSEKEEPING FLAGGED BY THIS ROUND (not research — live-bot hygiene).**
`python3 -m pytest` on the working tree is **13 failed / 181 passed**. Every
failure is a STALE ASSERTION left behind by the Round 150 stand-downs, not a
regression: test_breakout_book (6), test_diver (2), test_newsdesk_exit (2),
test_newsdesk_timing (1) all still assert `action == "entered"` on books whose
committed gate now correctly returns `stood_down`, plus 2 in test_state_save.
The stand-down behaviour itself is right; the tests were never updated to
expect it. A red suite on live-bot code is how a real regression hides, so
these want rewriting into stand-down guards (the way `test_q` was rewritten
into a regression guard in R88). Left untouched here — the nightly researcher
does not edit live-book code or its tests.

## ROUND 117 — the oil breakout: plain no, and my eyeball was the error (2026-07-25)

Wallace: "looks like you missed an oil trade" — oil ran +29.8% in three
weeks while the book caught one 135-minute trade. I diagnosed it as a
wrong-tool problem (a 2h crypto scorer cannot hold a three-week move, which
is true) and showed him donchian-10 and donchian-20 with an EMA20 exit
sitting on +14.3% and +8.3% open profits as evidence a breakout book would
have caught it.

**That evidence was worthless and the round proves it.**

77 cells (11 lookbacks 5-55 x 7 exits) on CL=F daily and 1h, train-only
selection, val read once, sealed 20% never loaded — and the sealed slice
happens to contain the actual +29.8% move, correctly untouched.

**1. The exit I eyeballed is negative expectancy on TRAIN at EVERY single
lookback from 5 to 55, no exceptions, on daily data.** The two green open
trades I showed him are individual live outcomes inside a system that loses
money on average across CL=F's full 2000-2016 train window. Showing an open
winner as proof of an edge is precisely the error this desk exists to catch,
and I made it.

**2. The best config's edge is mostly not the entry.** donchian(20) +
chandelier(2.5x ATR): train n=152 +$23.19/t, val n=48 +$21.02/t, and it is
a genuine PLATEAU (lookbacks 15/25 and chandelier 3.0 all clear too, so
R88's lone-spike failure mode does not apply). It still rejects on two
counts: thickness 3.85x fees-only / 2.56x full CostModel, under the 5x bar
— and, the kill shot, **a random-entry baseline using the IDENTICAL
trailing exit earns +$56.30/trade, more than double the real signal.** The
apparent edge is the chandelier riding a generally-rising commodity, not
donchian timing anything. 9.64 trades/year.

**3. Intraday is worse:** only chandelier3.0 shows life at 15-35h; the
winner trains +$42.77/t and val flips to **-$35.00/t**, with 3 of 4
neighbours failing. Clean FAIL, and at 156 trades/year it is the opposite
problem from the one we set out to fix.

**4. Neither near-miss transfers to BZ=F.** Daily goes negative on Brent
val (-$10.93/t); the 1h config is already negative on Brent train.
WTIOIL-USDT was unusable as a transfer venue — 58 daily bars.

**VERDICT: no oil breakout book. Oil has nothing that clears our bar at any
lookback or exit we have tested.**

**One correction to the round's own recommendation:** it proposes the EIA
inventory report as "the highest-value untested lever, round 111 never ran
it." That is wrong — R111 DID run it (mean |move| 0.570% at the release
hour, 1.75x baseline, 2.2x a randomized-timing control) and R114 built it
into a costed strategy where it FAILED train+val in both the continuation
and reversal directions. EIA is tested and closed.

**What this round is really worth:** the random-entry baseline. It is now
the single most valuable gate we run, because it separates "this signal
picks good moments" from "this exit rides a market that went up." Two
rounds tonight have been killed by it (gold's big-dollar survivors, and
this) and both looked like winners without it.

## ROUND 301 — we tested a different method than TJR's, four ways (2026-07-25)

Wallace: *"if you are not using his strategies and teaching because you
think they don't work through your backtesting, you have simply done the
wrong back testing."* He was right. Four specific, checkable errors, all in
OUR code, not in his teaching.

Rounds 72/73/75 also read the wrong source: a single 59-minute strategy
video. He has a 13-part structured course ("Path to Profitability") where
he defines one concept per episode with formal precision. This round pulled
30 videos, 237k words. **84 rules extracted: 61 mechanical, 12
discretionary, 4 gaps he never specifies, 5 places he contradicts himself.
73% mechanical** — far more codifiable than R72 concluded.

**1. Our stop floor excluded every stop he actually uses.** `step72_tjr.py`
line 152 sets `STOP_FLOOR_PCT = 0.15`. His real stops are 16 to 35 ticks on
ES = 0.067% to 0.146% of price. **Our minimum allowed stop was wider than
his widest real stop.** The test could not have placed a stop where he
places one even by accident. It also used ONE constant train-median stop
while his varies per trade by 2x, because he reads it off structure — and
it computed `target = stop_pct x rmult` when his target is a price LEVEL
and the reward-to-risk ratio is an OUTPUT of where that level sits.

**2. Our swing points are a different object.** His swing high is a
2-candle pattern (up candle, down candle, take the wick), confirmed 1 bar
later. We used `confirmed_swings(k=3)`: a centered 7-bar fractal confirmed
3 bars late. Different level set, three times the latency, and the latency
itself re-inflates the stop.

**3. Our cross-index filter was backwards.** R72's `partner_alignment`
required ES and NQ to AGREE. At the sweep his rule requires them to
DISAGREE — that is what the divergence IS — and he trades the index that
FAILED to sweep. Our filter deleted his highest-conviction setup by
construction. R72 found ES survivors only with that filter switched off,
which fits exactly.

**4. The 1h timeframe deleted the setup.** His manipulation window is 20
minutes and his entry window is 20 minutes, inside a 60-minute stand-down.
That is all one 1h bar. The entire time structure was invisible.

**The headline is the stop, and it confirms what Wallace has said twice:**
we swept percentages where he places a structural level. The level he uses
is the retrace swing the entry broke away from, because that is the price
that proves the idea wrong. He states it in three separate videos. The stop
and the entry trigger are the SAME object — which is why taking the earlier
entry halves the stop and turns his own worked example from 1:0.45 into
1:1.3.

**Runnable by a bot today, no judgment needed:** the session clock, all
level types, 2-candle swings, break of structure (body close past the most
recent swing with the wick rejected), fair-value gaps and their inversions,
equilibrium, the cross-index divergence and leading-index selection, the
full 4-step state machine, the structural stop, time gates, fixed-contract
sizing. That is the whole primary setup.

**Needs a number he never gives (must be labelled OURS, not his):** minimum
gap size, equal-highs tolerance, which target is "the" one, cluster size,
the take-profit split.

**Needs Wallace:** the timeframe drop-down call, choosing the earlier vs
later entry, closing a winner early, conviction sizing, the news call.

**Blocker: intraday index futures data.** Not a research problem, a
purchase decision.

Files: step301_tjr_rules.md, step301_tjr_rules.csv.

## ROUND 310 — three of the four dead Bitcoin edges stay dead (2026-07-25)

Wallace's point was that our testing, not the methods, might be wrong. R301
proved that for TJR. This round applied the same question to our OWN four
dead Bitcoin edges: add the single most load-bearing condition practitioners
require, and re-run.

**The honest frame first.** 14 configurations tried. If the sign of the
average profit per trade in each window were a coin flip, luck alone gives
3.5 configurations positive in both windows. **We got 3** — and all 3 are
the same edge at three settings of one dial. **This round produced fewer
both-windows-positive results than pure chance would.** Round 86 was a real,
specific correction, not a general-purpose rescue button. That boundary is
worth as much as any verdict here.

Every re-run reproduced its R150 baseline to the penny first, so any
difference is the added condition and nothing else. Market orders both
ways, stops at real chart structure, size = dollars risked / stop distance,
leverage an output, final untouched slice never loaded.

**1h structure flip + 2 agreeing tools — DEAD.** Our code bought the break
bar; practitioners buy the RETURN to the broken level. Moving entry to the
first later bar that trades back to the level and closes back above it takes
the first-60% loss from -$42.92 to -$30.75 per trade and it stays deeply
negative at every wait length. Long-only does not rescue it (longs -$22.05,
shorts -$64.95 in the first window) and in the middle window the shorts are
the BETTER side. A sign that flips between windows is noise.

**4h hidden RSI divergence — NOT ENOUGH TRADES TO SAY.** R86 proved the
confirmation close on the REGULAR flavour and nobody ever applied it to the
HIDDEN flavour, because at the time hidden divergence was a working live
edge. Applying it: win rate 44% -> 57-70%, and the middle window flips from
-$9.30 to positive at four of five settings. But only one setting clears the
trade floors (32 and 10 trades, clearing by two), and its first-window edge
has shrunk to +$2.89 per trade. **Ten trades and a three-dollar edge is a
direction, not a result.** This is R74's selectivity trap: the condition
that makes the setup good is the condition that makes it almost never
happen. Next step is a different coin or longer history, NOT a look at the
final slice.

**1h RSI(3) dip-buy — DEAD, now in two independent spellings.** Waiting for
the turn (close back above the signal bar's high, and separately the
oscillator crossing back up through 25) halves the loss from -$70 to
-$23/-$56 per trade and it is still a loss. The tell: **win rate goes DOWN**,
41% -> 33-36%. Waiting costs entry price while the stop stays anchored at
the same swing low, so the stop widens and the target moves further away.
Stop-outs rise 56% -> 58-61%; targets reached fall 26% -> 13-18%.

**News momentum — DEAD, and R150 had measured the flattering version.**
R150 substituted a generic swing trailing stop for the live one, flagged it
as a confound in its own write-up, and reported the verdict anyway.
Restoring the ACTUAL live stop (just beyond the reaction candle's far side)
makes it WORSE: -$19.97/-$42.82 at a 0.1% cushion. Tighter floor, more
clipping, win rate down to 21-26%. This closes the question honestly — the
original validation charged the cheaper resting-limit-order fee on every
entry and modelled no spread or slippage at all.

### THE RULE WORTH BANKING

**The confirmation close is setup-specific, not universal.** It helps a
CONTINUATION pattern (hidden divergence) and STRICTLY HURTS a MEAN-REVERSION
pattern (the dip-buy), and the mechanism is concrete: in a mean-reversion
trade the discount IS the edge, so waiting destroys the thing you came for.
That is more useful than any of the four verdicts.

### A SPECIFICATION PROBLEM ACROSS THE TOOLKIT

Two of these edges never had a working exit. Hidden divergence ends 64-90%
of its trades on the clock and only 3-10% ever reach the target. **A fixed
multiple of a structure stop, under a 12-bar hold cap, is decoration rather
than a target.** That is a problem with how we specify exits generally, not
a property of any one signal, and it deserves its own round.

## ROUNDS 350-352 — oil parked, and a measurement bug that flatters every gate study (2026-07-25)

**Oil confirmed not live**, verified by reading daemon.py, tradfi_engine.py
and every book file rather than trusting the note. `UNIVERSE = [SPX]`, oil
removed. The reconcile loop walks open trades regardless of UNIVERSE, so a
position open at stand-down still gets exit-managed rather than orphaned —
the right shape.

**The session finding is real and does not convert into an edge.** An oil
hour in New York moves 0.3548% of price on average versus 0.1676% in Asia,
at the 100th and 0th percentile of a 200-draw shuffled control. Every
constant re-derived on oil's own first-60% slice first (oil's own 1h range
median 0.4301%; oil's own RSI(2) 10th/90th at 7.3/93.4 — the S&P bot's
below-10 and BTC's RSI(3) level both explicitly not carried). 18 cells, all
negative; best was a 24h breakout in London/NY hours through a trailing
structure stop at an average loss of $9.07 per trade over 241 trades. 18
more cells at longer leashes, none positive. Nothing cleared the floor so
the middle 20% was never read and the final slice never loaded.

Random entries through the same exits at the same costs lose $26-$39 per
trade, so the shape beats random by ~$29 and still never crosses zero.
**More movement is not more edge. It is more movement at the same cost.**

### THE FINDING THAT MATTERS BEYOND OIL

**Comparing a filtered run against an unfiltered run is not a clean test of
a filter, in a single-position engine.** Filtering entries out does not
merely delete them — it FREES THE SLOT and lets different, later trades
happen. Measured: **16-17% of the filtered run's trades are trades the
unfiltered run never took.**

The like-for-like test nobody had run: take ONE trade population and split
it by the hour each trade was entered. On the same trades, **London/NY
entries lost $17.76 each and Asia entries MADE $19.01 each** — the opposite
of the hypothesis, and at the 17th percentile of 2,000 label shuffles,
i.e. ordinary chance.

**Every regime gate, volatility gate and session study on this desk that
used the filtered-vs-unfiltered shape is flattered by this.** That includes
things we currently believe. Audit queued.

### OIL: PARKED

6 rounds, ~20 families, zero survivors. R78's playbook, the borrowed rules
(R110), exit variations (R116), the Brent transfer, the full breakout
lookback sweep (R117), and now the last unbuilt lead. No queued oil idea
has evidence behind it. The remaining ones — the weekly inventory calendar,
futures-curve data, meeting dates — are blocked on DATA WE DO NOT HAVE, and
a research round cannot solve a procurement problem. The only instrument
that passed anything was Brent, which we cannot trade.

Honest summary: **oil trends and oil moves, both genuinely, and neither has
survived contact with what it costs to trade them.** That is a finding about
a market, not a failure to find one.

## ROUND 340-341 — gold's "17x" was measured against the wrong cost (2026-07-25)

**CORRECTION TO A NUMBER THIS DESK HAS QUOTED ALL NIGHT.** Gold's donchian
breakout has been described as "17 times the cost of trading". That figure
used GLD's 0.04% round trip. **The bot would trade XAUT on BloFin with
market orders: 0.18% round trip.** Re-priced against what we would actually
pay, middle 20% read once:

| shape | instrument | profit/trade as % of position | x the cost | trades/yr |
|---|---|---|---|---|
| 20-day break | GLD | +0.644% | **3.6x** | 5.3 |
| 20-day break | gold future | +0.952% | **5.3x** | 4.7 |
| 55-day break | GLD | +1.834% | **10.2x** | 2.5 |
| 55-day break | gold future | +1.096% | **6.1x** | 2.7 |

The version everyone quotes STRADDLES the 5x bar rather than clearing it.
The one that clears fires 2.5 times a year.

**The audit was fairer to our own code than expected:** two of the four
practitioner conditions were already implemented (confirmed close beyond the
channel; fill at the next bar's open). The missing longer-trend filter helps
on the window we chose and is a coin flip on the one we did not — the shape
of a fitted improvement — so it was NOT adopted. A minimum-channel-width
filter is actively harmful in all 12 cells.

**Against random entry timing, 500 draws:** the breakout entry beats 88-97
of 100 draws over 13-15 years, so **the entry is real**. On the middle 20%
it falls to the 74th-78th percentile, and the table shows why: random
entries with this exit are worth +0.27% to +0.64% per trade in the modern
window versus +0.02% to +0.14% in the older one. **A meaningful part of
recent performance IS the exit riding gold's rise.** Holding the trend
regime constant sharpens it further: the 20-day falls to the 61st-65th
percentile while the 55-day holds at the 92nd. The slower channel is the
one carrying real entry information into the recent window.

### THE ROUND-86 PATTERN, A THIRD TIME

**Gold's dip-buy is not dead.** R48 buried it 1 out of 72 using a version
with a fixed hold, a fixed target and **no longer-trend condition**. With
that mandatory condition added it SURVIVES on all three gold instruments
(GLD +0.302%/37 trades then +0.885%/12). Without it, it goes outright
negative on two instruments. It is alive, too thin (1.7x-2.7x) and too rare
(3/yr) — but the playbook entry saying it is dead is wrong.

**My flagship port hypothesis failed.** The volume gate on the Bollinger
breakout is DEAD on gold: it lifts one window and collapses the other, in
opposite directions on the two instruments. The ungated band breakout
survives at 4.3x-4.9x, just under the bar, and at 4.2 trades a year is
probably the channel breakout wearing a different hat.

**Also corrected:** R48's "Bitcoin's 1.5% gate gives zero trades on gold"
is true on HOURLY bars (gold 0.28%-0.72%) but false on DAILY, where gold's
range is 1.13%-1.29% and the same gate is open 23%-33% of days.

**Best lead: the 4-hour gold future — 28.6 trades/year, 2.9x then 9.6x**,
with the honest caveat that its first window is only 1.43 years and 41
trades. Thin-window rule applies.

**Gold shorts now 0 for 58.** Overnight gap family mapped and closed.

### THE HIGHEST-LEVERAGE QUESTION ON THE GOLD DESK IS PLUMBING, NOT RESEARCH

Dropping XAUT's round trip from 0.18% toward 0.06% would flip turn-of-month,
the dip-buy AND the hourly breakout from rejects to candidates in one
stroke. That is the limit-order question, and it is now load-bearing for two
markets rather than one.

## ROUND 320 — Ethereum: five ported shapes, all die, and two live-code corrections (2026-07-25)

49 cells, every dial re-derived from Ethereum's own bars with the original
number printed beside it. All five families die or reject. **Luck alone
would produce ~7.8 winners on this grid; it produced 4. Below chance.**
Nothing claimed. Two cells were positive in both windows and cleared the
cost bar, but neither was the pre-registered pick and reaching for them is
exactly the move that causes this problem — logged as replication
candidates only.

**Correction 1: "Bitcoin's 1.5% volatility gate" is not one number.**
Measured on Bitcoin's own 4h bars it let entries through on **63.2% of the
first window, 53.5% of the middle, and 24.3% of the final fifth.** Bitcoin's
volatility decayed across its own history, so the constant grew steadily
pickier with nobody changing it. R170's note of 18.7% matches none of those
windows. This feeds directly into the R400 audit of our one live edge.

**Correction 2: the flag-touch shape was sealed on limit orders and never
tested on another coin.** At market-order costs on Ethereum it loses in all
six cells.

**Ethereum's turn-of-month does not merely fail, the tendency INVERTS.**
First window: +0.743% inside the window versus -0.027% outside (t=3.01).
Middle window: -0.766% inside versus +0.160% outside (t=-2.10). Those are
price moves on an unlevered holding. Sign reversal, not a costing problem.

25 Ethereum families now mapped, zero validated edges of its own.

## ROUNDS 360-362 — the S&P venue answer, and the control killed one of our two edges (2026-07-25)

### THE VENUE

**SPX-USDT is settled: it is the SPX6900 memecoin.** Queried BloFin's own
price endpoint: $0.3366, contract size 10, listed 2024-10-30, and our
cached file shows it has only ever traded between $0.33 and $0.96. It IS
tradeable on our practice account and must never be pointed at for index
exposure.

**The practice host has no S&P anything.** 88 contracts, all crypto plus
tokenized gold. Nothing hidden.

**The real host has SPY-USDT, QQQ-USDT and IWM-USDT.** SPY-USDT genuinely
tracks the index (742.25 against the real tracker's 738.18 two sessions
earlier), 20x max, $652,638 turnover in 24h, buy/sell gap 0.0013% of price.
IWM-USDT is unusable at eighty times that gap.

**And SPY-USDT never closes.** 500 hourly bars over three weeks: all 500
traded, all 24 hours, all 140 weekend hours. **Our playbook's claim that
the ETF's 17.5-hour dark window makes index stops awkward does not apply on
this venue.** It is a continuous instrument wearing the ETF's name.

Cost there: 0.06% per fill, so ~0.1413% round trip, roughly 3.5x a stock
broker. The holding charge has averaged -0.0182% per settlement over 100
settlements, meaning longs get PAID ~0.055% of position per day — but
that is only ~33 days of data, do not build on it.

**BLOCKER: BloFin's terms prohibit US persons.** Wallace is a US person and
the Costa Rica routing does not help, because venues match on the identity
collected at account opening. Documented consequences elsewhere: trading
switched off, withdrawal-only, or funds frozen pending review. Factual, not
legal advice. So SPY-USDT is simultaneously the fastest path our code could
reach and the one with the worst standing problem.

**RANKED ALTERNATIVES, shortest path first:**
1. **Alpaca paper** — free, unfunded, plain web API of the same shape as our
   BloFin client, trades SPY and QQQ, fractional shares, **7+ years of free
   historical bars** which also kills our dependence on the unofficial
   Yahoo scraper. Our edges fire 4-15 times a year against a
   200-requests-per-minute ceiling. One real catch: market orders are
   rejected outside regular hours; both our rules decide at a daily close
   and fill at the next open, which is inside the session. **Needs a
   sign-up — not created, Wallace's call.**
2. Tradier sandbox — no minimum, delayed prices, fine for daily-close rules.
3. IBKR paper then micro futures — the only real-futures route, but the
   E-mini controls ~$340,000 and the Micro ~$34,000 near a 6800 index.
   Against a few hundred dollars of position, even the micro is far too big.
4. BloFin SPY-USDT real host — closest to plug-and-play, 24h, our code
   already speaks it, but real money from the first order and the US-person
   restriction.

**Ruled out:** Schwab, Robinhood, TradeStation, tastytrade sandbox (wipes
positions every 24h, our trades hold 1-10 days), E*TRADE sandbox, and every
offshore crypto venue listing an S&P product. Ostium has a real S&P
perpetual but suffered an $18m oracle exploit on 2026-07-15.
**Worth a look another day:** Dinari, a Delaware-registered broker-dealer
issuing tokenized US shares to US persons — a licensed US path rather than
an offshore workaround.

### THE RESEARCH — 495 settings, and two corrections to what we believed

**RSI2 deep-dip buy: CONFIRMED on SPY, and R60's cross-market claim needs
downgrading.** On SPY it earns +0.8803% of position per trade against a
coin flip's +0.1448% in a pool that already knows to be long in an uptrend
— **100th out of 100 on both scoreboards.** On ES=F it places 78.5th and
61.3th. R60 called "12 of 12 on both SPY and ES=F" its cleanest
cross-market result. **It is one real edge on the ETF and one exit riding a
trend on the futures.**

**"Stay long above the 200-day average": DEMOTED, it is not an entry
edge.** Per trade it LOSES to a coin flip on all three markets: SPY real
+1.7989% against random **+4.2197%**, placing **6.8th out of 100**. A random
day picked from an existing uptrend, held to the same exit, earns two and a
half times more per trade than waiting for the actual cross. Entering at
the cross means eating every whipsaw. It beats the coin flip on total
growth only by taking 3-4x as many trades, and on SPY it still loses to
buying once and never selling (+186.3% against +240.4%). **It is a
drawdown blanket (worst fall -56.5% to -29.7%), not an edge**, and should
stop being listed beside the dip-buy.

**Turn-of-month: NEW SURVIVOR and the best result of the round.** Broad
plateau (51/70, 57/70, 56/70 settings survive), passes the coin-flip test
on all three markets on both scoreboards in both pools (96th-100th), ~12
trades/year — three times the dip-buy's frequency. SPY: +0.5947% of
position per trade, 14.9x the cost of trading, 158 trades.

**Hidden divergence ported from Bitcoin: NEW CANDIDATE.** 100th place on
both scoreboards on SPY, ES=F and QQQ, every setting surviving on two of
three. Weak point is SPY's middle slice at +0.0113% over 21 trades.

**Vol-gated trend ported from Bitcoin: REJECTED** — 82x the cost of trading
and then 79.8th/40.2th/16.2th against the coin flip. Textbook R117: very
few, very long trades in a market that went up.

### TWO PLAYBOOK CORRECTIONS

**The overnight gap does not threaten a structure stop.** The gap is real
(SPY moves >0.3% overnight on 46.4% of days) but **the overnight fall alone
exceeded the 1.84% dip-buy structure stop on only 1.3% of days**, and the
3.12% turn-of-month stop on 0.2%. What died in R60 was a TIGHT stop at ~1.3%
of price. Adding a structure stop kept every SPY cell a survivor.

**The 15-20x leverage thesis is NOT supported on daily index bars.** Size =
risk / stop distance, so leverage is an output: SPY dip-buy gives **0.5x at
1% risk, 1.1x at 2%**. Turn-of-month 0.3x-0.6x. The index moves less per day
than crypto but its structure sits proportionally just as far away. **It
could still hold on intraday bars where structure sits closer — that is now
the biggest open question and it was not tested.**

### THE VENUE DECIDES WHICH EDGE IS TRADEABLE

Our bar is profit at least 5x the cost of trading. That needs 0.2000% of
position at a stock broker and **0.7065% on BloFin's perpetual.**

| edge | profit/trade | stock broker | BloFin perpetual |
|---|---|---|---|
| SPY RSI2 dip-buy | +0.8803% | 22.0x, passes | 6.2x, passes |
| SPY turn-of-month | +0.5947% | 14.9x, passes | **4.2x, FAILS** |
| SPY hidden divergence | +0.7969% | 19.9x, passes | 5.6x, passes |

**Of 314 survivors, 272 clear the bar at stock-broker costs and only 52
clear it on the BloFin perpetual.** The best result of the round does not
survive the only venue our bot can technically reach today.

Final untouched slice never opened.

## ROUND 400 — the last live edge fails a clean test. Ride stood down. (2026-07-25)

The audit triggered by oil's R352 finding. **Our one surviving live edge, the
1.5% minimum-volatility condition on the 4h Bitcoin trend, does not survive
an honest measurement.**

**It is the worst case for the artifact, not the mildest.** The condition
sits inside the signal's own state machine, so it does not SKIP a trade, it
DELAYS one. **30% of the gated run's first-window trades and 57% of its
middle-window trades entered on a bar the ungated run could never have
entered on**, because it was already holding. Oil's version was 16-17%.

**Three independent clean tests, all agreeing:**
- one crossover population split by entry condition: quiet entries
  **+$289.38** per trade, lively entries **+$31.92**, gap at the 7.4th
  percentile of 2,000 label shuffles (medians identical — a tail effect,
  said plainly)
- the same 59 trend legs, matched pairs: entering at the crossover
  **+$181.61/leg**, waiting for lively **+$45.27/leg**. The condition was
  the better choice on **5 of 59 legs**, 1.1st percentile of 2,000 sign flips
- the 21 legs where it actually acted: it **cost $383.05 each**, median wait
  40 hours, 1.6th percentile

It does avoid one genuinely losing subset (14 legs that never turned lively,
worth +$1,350) and the delay costs -$8,044. **Net -$6,694, which is 71% of
the ungated system's money.** Negative in 2020, 2021, 2022, 2023 and 2025;
positive only in 2024, where one trade carries the year.

R150's published +$17.15 / +$99.37 reproduced to the penny first, so the
harness is verified.

**Honest limit:** R54's sealed evidence for this condition sits inside the
final untouched slice and could not be re-measured without spending that
look. R54 did use the contaminated comparison shape.

**ACTION: the ride is STOOD DOWN for new entries.** Not because the trend
rule is condemned — ungated is BETTER on the same legs — but because ungated
has never been tested as its own thing with a structural stop at
market-order costs. Switching the condition off would be deploying an
untested variant. Re-test first.

### THE REFINEMENT WORTH KEEPING: THE WIRING DECIDES THE HARM

Nine studies examined. **Six used the contaminated shape**, two were already
clean partitions (R83 and R88 — R83's own docstring names and rejects this
exact artifact a day before it was formally found), two carry no comparison
at all.

**A gate wired into a state machine reschedules trades and contaminates
badly. A gate that suppresses a whole excursion of a continuous indicator
produces a strict subset and is clean** — verified by diffing entry
timestamps: **0% novel trades in all 24 cells** across R100 and R86. That
check is cheap and settles it.

**Results that change:**
- **R63's session axis is the artifact in its purest form.** Its five
  session cells are mutually exclusive and exhaustive so they must sum to
  the baseline. They sum to **29-256% more, in 10 of 10 tools, median 76%**.
  Its headline was measuring manufactured trades. Nothing was deployed.
- **R100's gold session filter: clean of the artifact, dead for another
  reason.** GLD produces ZERO trades in the London window because the fund
  is not open then. An instrument fact, not a session edge.
- **R86's volume gate: real information, thinner than advertised.** At 1.2x
  it removes only 3-6% of trades. Moot — the bot is stood down anyway.
- **R83, R88 and R60's SMA200 inside the live S&P dip-buy: unchanged.**

**Two corrections of fact:** "R79" does not exist — no file, no log entry.
And **daily_pick's calm gate has no study behind it at all**; it is an owner
directive shipped straight to live code. Untested is a smaller and different
problem than wrongly tested, but it should be recorded as untested.

## ROUND 370 — the leverage thesis is confirmed, the intraday thesis is dead (2026-07-25)

206,955 regular-hours 5-minute SPY bars, 2,654 sessions, 2016-2026. Plus
QQQ 5m and SPY 15m. Choosing slice only for selection, middle read once,
**final 20% never opened.**

### THE LEVERAGE HALF: CONFIRMED

Distance from price to the nearest confirmed swing that would prove a long
wrong, as a percentage of price (how far price must travel, not a change in
margin):

| swing definition | median |
|---|---|
| **TJR's 2-candle, confirmed 1 bar later** | **0.092%** |
| ours, 5-bar fractal | 0.137% |
| ours, 7-bar fractal (R362's setting) | 0.165% |
| ours, 11-bar fractal | 0.213% |

**His swing sits 44% closer than ours. That single definition choice
roughly doubles the leverage before any strategy exists.**

Converted, size = risk / stop distance:

| bars | stop | risk 1% | risk 2% |
|---|---|---|---|
| daily (R362) | 1.840% | 0.5x | 1.1x |
| **5-minute, TJR swing** | **0.092%** | **10.9x** | **21.7x** |

**R362's "below one times the account, not twenty" was a statement about
DAILY bars only.** On 5-minute bars the index structurally supports 11x at
1% risked and 22x at 2%, arrived at through chart structure rather than
chosen. Wallace's shape works arithmetically: a $300 slot at 20x is $6,000,
a 0.092% adverse move is $5.52, which is 1.84% of that slot's margin.

**TJR corroborated independently.** He states his real ES stops run 16-35
ticks = 0.058%-0.146% of price. Our measured SPY 5-minute 2-candle
distribution puts p25 at 0.044% and p75 at 0.180%. **His stated range sits
almost exactly inside our measured interquartile range on a different
instrument.** He is describing something real and reproducible.

### THE TRADING HALF: REJECTED, AND NOT MARGINALLY

**There is almost no intraday return to win.** Choosing slice, gross:

- SPY **open to close**, the whole 6.5-hour session as one trade:
  **+0.0163% of price, t=0.80. That is 0.41x the cost of ONE round trip.**
- SPY **close to next open**, the dark window: +0.0363%, t=1.86.
- QQQ session +0.0239% (t=0.89); dark window +0.0514% (t=2.40).

**Holding SPY through an entire trading day earns less than half the cost
of the single round trip needed to do it.** No 5-minute window inside the
session has a t above 1.85.

**And a tight stop makes the cost bar nineteen times harder on the same
instrument**, because profit and cost both scale with size while the stop
shrinks:

| stop | one round trip costs | must make, to clear 5x cost |
|---|---|---|
| 0.092% (TJR swing) | **0.44 of the stop** | **2.17 stop distances** |
| 1.840% (daily dip-buy) | 0.02 | 0.11 (it delivers 0.48) |

**277 settings, four families, one survivor — and that is below chance**
(luck alone would hand you ~8 of the 169 partition cells).

- opening range break: 12 of 12 negative, both directions, all three ranges
- **sweep then break of structure (TJR-shaped): 72 of 72 negative.** And
  scored with **no stop and no target at all**, it shows no directional lift
  (|t| < 1.9) and **the QQQ replay flips the sign on five of six.** The stops
  were not the problem — there was nothing to protect.
- RSI2 dip-buy ported to 5-minute bars: **gross -0.0005% per trade** against
  the daily version's +0.8803%. Not a constant needing re-tuning; the effect
  does not exist at this resolution.
- gap-down buy: after a >0.3% gap the last confirmed swing low sits below
  the open on only **4.7% of sessions** — there is no structure to stop
  against 95% of the time.

**Intraday stops cannot be held overnight anyway:** a 0.10% stop is gapped
straight through on **41.5% of sessions**; the 1.84% daily stop survives
98.2% of nights.

### THE NEW FINDING: TURN-OF-MONTH LIVES OVERNIGHT

| | open to close | close to next open |
|---|---|---|
| SPY turn-of-month lift | +0.0176% = 0.44x a round trip | **+0.0468% = 1.17x** |
| QQQ turn-of-month lift | +0.0181% = 0.45x | **+0.0807% = 2.02x** |

**The lift is 2.7x larger in the dark window than in the session on SPY and
4.5x on QQQ.** That is WHY R362's version works by holding 7-8 days: it is
collecting overnight windows, not trading days. It also means this edge is
structurally unavailable to an intraday bot.

### THE STRATEGIC READ

**The index's edges are real, slow, and they live overnight.** The correct
way to trade it is small size held across nights, not big size held across
minutes. The 20x style is not wrong — it is asking this instrument for the
one thing it does not have.

**Honest limit:** TJR's entry trigger is a 1-minute break of structure and
we hold no 1-minute bars, so the trigger was collapsed onto the same
5-minute bar as the confirmation. Flagged, not buried. But the signal showed
no directional lift with the stop removed entirely, so 1-minute data is
unlikely to reverse the sign. Closing it properly is a data purchase, not a
research question.

## ROUND 450 — his 1-minute trigger is the whole difference, and the venue eats it (2026-07-26)

**What was tested.** TJR's sweep → break-of-structure entry on the market
the desk is actually armed in (crypto), at the resolution he actually
specifies. Round 370 rejected this shape 72 cells out of 72 on 5-minute
SPY and closed with one named limit: **his confirmation is on the 5-minute
and his ENTRY TRIGGER is on the 1-MINUTE** (step431 §0, step436 §4), and
the project held no 1-minute data, so the trigger was collapsed onto the
5-minute confirmation bar. We now hold Alpaca 1-minute bars on eight crypto
pairs from 2026-03-01, so both halves of that limit — the resolution and
the instrument — are closed at once.

Files: `step450_tjr_crypto_1m.py`, `step450b_significance.py`.
Window: 2026-03-01 → 2026-07-26 UTC, 147 days, the overlap where both
charts exist so the two arms score the same tape. BTC 42,386 5-minute bars
and 208,210 1-minute bars, ETH and SOL alongside.
**60/20/20. The final 20% was NEVER OPENED — nothing qualified.**

**Faithful to him:** the two-candle swing everywhere; levels marked only on
the high timeframes (previous day, session highs and lows, 1-hour and
4-hour swings); a level traded through is not a sweep until price reacts,
and the reaction IS the break of structure (§4b) — no reaction, no trade;
break of structure is a body close, never a wick; the sweep hunted on the
5-minute and never on the 1-minute; the stop at the extreme traded between
the sweep and the entry.
**Ours, and labelled:** UTC midnight day boundary (the live desk's own
decision), a 2-hour pending-sweep expiry, a 24-hour hold cap. All three
fixed before the run and never swept.

### The verdict, at the top: REJECT on net, and below chance

**0 of 64 pooled cells** are positive on both the choosing and the middle
slice with at least 2 of 3 assets agreeing. **Luck alone would have handed
us about 16.** Same shape as round 370 — not a near miss, a zero.

### But the trigger resolution is real, and it is the round's finding

Choosing slice, one row per entry, gross, pooled across BTC + ETH + SOL:

| construction | trades | mean gross | t | median stop | lev @1% risked |
|---|---|---|---|---|---|
| 5-minute trigger (round 370's) | 3,376 | **−0.0352%** | −1.40 | 0.507% | 2.0x |
| **1-MINUTE trigger (his)** | 3,119 | **+0.0551%** | **+2.63** | **0.211%** | **4.7x** |
| control, random entry, same stop machinery | 702 | −0.0514% | −1.85 | 0.162% | 6.2x |

- 1-minute minus 5-minute: **+0.0903% of price per trade, t = 2.76**
- 1-minute minus random entry: **+0.1066% of price per trade, t = 3.05**

**Moving the trigger from the 5-minute bar to the 1-minute bar flips the
sign of the gross edge and beats a random control at t = 3.** Round 370's
rejection was made with the wrong trigger, and it said so at the time. On
30 of 32 one-minute cells the gross mean is positive; on the five-minute
arm only 13 of 32 are. He is describing something that exists, and the
resolution he states is load-bearing rather than decorative.

### And the same choice is what makes it unaffordable here

The tighter trigger cuts the structural stop by roughly 60%, from 0.507%
of price to 0.211%. That is the leverage win. It is also the problem:

- one Alpaca crypto round trip at taker rates is **0.50% of notional**
- the whole signal is **0.055% of price per trade** — **0.11x one round trip**
- against a 0.211% stop, that round trip costs **2.4 stop distances**

This is round 370's arithmetic reappearing on a different instrument: the
tighter the stop, the larger the trading cost becomes relative to the thing
being protected. Charged for honesty, used to decide nothing (owner rule,
2026-07-25) — and it does not need to decide anything, because the point
is not that fees disqualify the method. **The point is that the measured
signal is one ninth of the size of the transaction needed to collect it.**
At literally zero cost this is +0.055% of price per trade and would be
worth building. At Alpaca crypto's rates it is not reachable from here.

**So this is a venue finding, not a method finding**, and it lands on the
same line `alpaca.py` already carries: cheaper trading multiplies every
edge we own rather than adding one. The number to hunt is a crypto venue
whose round trip is a small fraction of 0.055% of notional — which is
roughly a tenth of what we pay now.

### The leverage census, all eight pairs

Distance from price to the structure that would prove a long wrong, as a
price move (not a change in the position's value):

| pair | 5m swing | 1m swing | ratio | lev @1% risked, 1m |
|---|---|---|---|---|
| BTCUSD | 0.167% | **0.077%** | 0.46 | 13.1x |
| ETHUSD | 0.210% | 0.159% | 0.76 | 6.3x |
| SOLUSD | 0.261% | 0.190% | 0.73 | 5.3x |
| LINKUSD | 0.257% | 0.202% | 0.78 | 5.0x |
| LTCUSD | 0.229% | 0.218% | 0.95 | 4.6x |
| DOTUSD | 0.298% | 0.206% | 0.69 | 4.8x |
| XRPUSD | 0.243% | 0.199% | 0.82 | 5.0x |
| ADAUSD | 0.284% | 0.212% | 0.75 | 4.7x |

Structure alone supports 4.6x to 13.1x at 1% risked on every pair we hold,
arrived at by reading the chart rather than by choosing a number. **US law
caps it at 10x regardless**, so only BTC's 1-minute structure is tighter
than the legal ceiling. This extends round 370's confirmed leverage finding
from the index onto crypto: it holds on eight more instruments.

### Honest limits

- **147 days, one regime.** The 1-minute history starts 2026-03-01. This is
  a five-month read, not a six-year one, and it cannot see a regime change.
- The signal is small and its t of 2.6 comes from 3,119 trades. A single
  window at that size is a hypothesis with a pulse, not a validated edge.
- The pending-sweep expiry and the hold cap are ours. Different numbers
  would give different populations; they were not swept, and they should
  not be swept later to rescue this.

### Looks consumed

**None.** No cell qualified, so the final 20% of the crypto 1-minute window
is still sealed for this family.

## ROUND 474 — the 1-minute trigger transfers to the index. Round 370 is overturned, and one cell survived the sealed slice. (2026-07-27)

**What was tested.** Queue item 1, exactly as written: replay round 450's arm A
(5-minute trigger, round 370's construction) against arm B (his 1-minute
trigger) on SPY and QQQ, nothing re-tuned. Round 370 rejected this shape
**72 cells out of 72** on 5-minute SPY and closed by naming the reason its
rejection might be wrong: his confirmation is on the 5-minute and his ENTRY
TRIGGER is on the 1-MINUTE (step431 §0, step436 §4), and the project held no
1-minute index bars. We now hold `data_alpaca_SPY_1m.parquet` and
`data_alpaca_QQQ_1m.parquet`, 2016-2026. No purchase, no new data.

Files: `step474_tjr_index_1m.py`, `step474b_significance.py`.
Window 2016-01-01 → 2026-07-24, regular hours only, 205k SPY 5-minute and
1.03M SPY 1-minute session bars. **60/20/20 — choosing ends 2022-05-03,
middle ends 2024-06-13.**

**Forced by the instrument, all fixed before the run and never swept:**
regular hours only (market orders are rejected outside them, R360); fill no
earlier than 09:50 New York (step436 §4), applied to the fill bar and
verified — zero fills before it; **flat by the close**, every position and
every pending sweep, verified — every exit lands inside its own session;
structure read within the session, so the two-candle swing never pairs a
15:55 bar with the next 09:30 bar. Cost is the index cost, 0.04% of notional
round trip (R370's headline), 0.02% also carried. Everything else — the
two-candle swing, the level set, the sweep-then-reaction sequence, the body
close, the structural stop, the 2-hour pending expiry — is R450's, unchanged.

### The verdict: THE TRIGGER RESOLUTION IS A GENERAL FACT ABOUT HIS METHOD

Choosing slice, gross, one row per distinct entry, **clustered by trading
day** because eight levels firing inside one session are not eight
independent draws:

| construction | entries | days | mean gross | t naive | **t by day** | median stop | lev @1% |
|---|---|---|---|---|---|---|---|
| 5-minute trigger (R370's) | 12,795 | 1,575 | +0.0055% | 1.13 | 1.81 | 0.283% | 3.5x |
| **1-MINUTE trigger (his)** | 10,180 | 1,555 | **+0.0654%** | 14.65 | **9.82** | **0.084%** | 12.0x |
| control, random entry, same machinery | 6,013 | 1,595 | +0.0146% | 2.78 | 2.76 | 0.111% | 9.0x |

Paired on the same trading days:
- 1-minute minus 5-minute: **+0.0626% of price per day, t = 7.88** over 1,554 shared days
- 1-minute minus random entry: **+0.0608% of price per day, t = 7.34** over 1,555 shared days

Both assets independently, choosing slice gross: **SPY +0.0599% against
+0.0089%; QQQ +0.0707% against +0.0023%.** The difference is +0.0511% on SPY
and +0.0685% on QQQ.

**The cleanest form of the result: 23 of the 32 one-minute cells qualify —
positive net on the choosing AND middle slice AND on both assets — and 0 of
the 32 five-minute cells do.** Luck alone would hand you about 4 per arm.
Every survivor in this round is an arm-B cell.

**And it is not one regime.** Gross mean of the 1-minute arm, by year:
2016 +0.0507%, 2017 +0.0316%, 2018 +0.0779%, 2019 +0.0580%, 2020 +0.0981%,
2021 +0.0574% (choosing), 2022 +0.0856%, 2023 +0.0649% (middle). Eight of
eight opened years positive. The five-minute arm over the same years runs
−0.0427% to +0.0237% and never separates from zero.

**Round 370's 72-of-72 rejection is formally overturned.** It was made with
the wrong trigger, it said so at the time, and the trigger was the whole
difference. R450 found the same flip on crypto (BTC, ETH, SOL); this round
adds SPY and QQQ. Five instruments, two asset classes, same sign — the
standing transfer rule is satisfied by some distance.

### THE CATCH, AND IT IS THE ONE THAT DECIDES MONEY

The desk sizes by risk: size = risk / stop distance, so the money follows the
RISK MULTIPLE, not the price move. Pooled across the 1-minute arm on the
choosing slice: **gross R +0.584, net R −0.238.** At a 0.084% median stop, a
0.04% round trip is **0.48 of the stop distance**. This is R370's arithmetic
reappearing: the tighter the stop, the larger the transaction becomes
relative to the thing it protects. The signal is real in price terms and the
cheapest-stop cells hand all of it to the cost. Only the wider-stop cells
clear — which is why the cell that survived below has a 0.150% stop, not a
0.084% one. Charged for honesty, used to decide nothing (owner rule).

### THE SEALED SLICE — ONE LOOK TAKEN, AND IT SURVIVED

23 cells qualified. The rule fixed before the run allows ONE test look on the
single best cell by choosing-slice net. That cell is
**`prev day low → 1m BOS, hold to close`** (choosing net +0.0582%, middle net
+0.0032%, stop 0.150%, 6.7x at 1% risked). Sealed slice opened once:

| | trades | days | gross | net | gross R | net R |
|---|---|---|---|---|---|---|
| **sealed 2024-06 → 2026-07** | 371 | 155 | **+0.0726%** (t by day 2.41) | **+0.0326%** | **+0.618** | **+0.132** |
| SPY | 196 | | +0.0897% | +0.0497% | | |
| QQQ | 175 | | +0.0535% | +0.0135% | | |

**Positive on all three windows and on both assets. Net R positive after
costs. This SURVIVES the full gauntlet — AWAITING DEPLOYMENT REVIEW.**
It is roughly 103 trades a year per asset, exits 67% by stop / 33% at the
close, wins about a third of the time.

### Honest limits

- **The tightest stops sit at the scale of the spread.** The tested cell's
  5th-percentile stop is 0.0252% of price, about ten cents on SPY. Fills are
  modelled as the bar open with a flat 0.04% round trip; that tail is not
  something this harness can price honestly, and the pooled arm's 0.084%
  median stop is thinner still. A deployment review should look at the
  distribution, not the median.
- **Net R is negative for the arm as a whole.** One cell surviving is not the
  family surviving. The other 22 qualifiers are unverified out of sample and
  must stay that way — the family's sealed window is now spent.
- **QQQ's sealed net is +0.0135%**, a third of SPY's. Both positive, but the
  second asset is thin, not a strong independent confirmation.
- 09:50, flat-by-close, the 2-hour expiry and within-session structure are
  ours. Not swept, and they should not be swept later to improve this.

### The leverage census on the index

Distance from price to the structure that would prove a long wrong, as a
price move (not a change in the position's value), regular hours:

| symbol | 5m swing | 1m swing | ratio | lev @1% risked, 1m |
|---|---|---|---|---|
| SPY | 0.104% | **0.046%** | 0.44 | 21.6x |
| QQQ | 0.143% | 0.063% | 0.44 | 15.8x |

R370 measured the SPY 5-minute two-candle swing at 0.092%; 0.104% here on a
longer window and a session-scoped definition. **The 1-minute-to-5-minute
ratio is 0.44 on both index instruments and was 0.46 on BTC** — the same
number on three instruments in two asset classes. US law caps leverage at 10x
regardless of what the structure permits.

### Looks consumed

**ONE.** The final 20% of the SPY/QQQ 1-minute sweep-to-break-of-structure
family is now spent and must never be re-opened for this family. The crypto
1-minute family's sealed window (R450) is still untouched.

## ROUND 475 — his confluences do NOT partition his own entries into a better subset, and the crypto sealed window is now spent (2026-07-29)

**What was tested.** Queue item 2, exactly as written: does requiring price
to be at his equilibrium, or to be filling a fair value gap, partition round
450's 1-minute-trigger population into a materially better subset? A
partition, never a re-run — the parent is round 450's arm B imported from
`step450_tjr_crypto_1m` unchanged, one simulation per cell, and every
filtered set is rows of that same frame. The script asserts strict-subset
and no-leak on every cell.

File: `step475_tjr_confluence_partition.py`, output `step475_output.txt`.

**Faithful to him.** The confluence is read on the FIVE-minute chart, not
the one-minute — his own instruction (step432 §2: the 1-minute trigger is
"taken at a 5-minute ingredient… I'm not looking for order flow to get
respected on the 1-minute timeframe"). Equilibrium is step436 §6: the exact
midpoint of the most recent confirmed 5-minute swing low and swing high,
long below it, short above it. Fair value gap is step436 §5: three candles,
low of the third above the high of the first, dies on a body close through
it and never on a wick. EITHER is his own escalation rule (§8). **Order
blocks and breaker blocks are not built — he retired them (§1) and there is
no order-block code in the file.**
**Ours:** the confluence is evaluated at the close of the 1-minute trigger
bar off the last 5-minute bar that had already closed, read one bar staler
still. Strictly causal, deliberately conservative.

### THE DATA MOVED UNDER THIS ROUND, AND IT CHANGES WHAT R450 MEANS

Round 450 ran on 147 days — "the 1-minute history starts 2026-03-01",
42,386 BTC 5-minute bars and 208,210 1-minute bars. **The parquet files now
hold 2021-01-01 → 2026-07-26: 578,831 BTC 5-minute bars and 2,597,036
1-minute bars.** The crypto 1-minute history was backfilled after R450 ran,
the data files are gitignored, and nothing recorded it. R450's honest limit
number one — "147 days, one regime" — is closed by the data itself.

So the round ran TWICE, same partition, same code, no tuning between them:
round 450's own 147-day window (the queue item as literally written, and the
only run permitted to spend a sealed look, because those are the boundaries
R450 defined), and the full 5.5 years. **The full window was barred from
spending a look before the run**, because R450's whole 147 days now sit
inside that window's final 20% and it is therefore not a clean slice.

### THE VERDICT: NO. THE CONFLUENCES DO NOT SELECT A BETTER SUBSET.

Cell counting, both windows: **1 of 96 partition cells cleared the bar on
the 147-day window and 0 of 96 on the 5.5-year window. Luck alone would hand
us about 6 of 96.** Below chance on one window and a zero on the other.

The pooled read is where the answer actually lives. Choosing slice, gross,
one row per distinct entry:

| | 147-day window | | 5.5-year window | |
|---|---|---|---|---|
| population | entries | mean gross | entries | mean gross |
| parent, bare sweep → 1m BOS | 3,140 | +0.0538% (t 2.58) | 42,354 | **+0.1769% (t 15.33)** |
| kept by EQUILIBRIUM | 1,421 | +0.0779% | 25,684 | +0.1912% |
| thrown away by EQUILIBRIUM | 1,719 | +0.0339% | 16,670 | +0.1549% |
| kept by FAIR VALUE GAP | 437 | **+0.2265%** | 5,962 | +0.1445% |
| thrown away by FAIR VALUE GAP | 2,703 | +0.0259% | 36,392 | **+0.1822%** |
| kept by EITHER | 1,593 | +0.0959% | 27,136 | +0.1870% |
| thrown away by EITHER | 1,547 | +0.0105% | 15,218 | +0.1588% |

Kept minus thrown away — the only comparison that tests a partition:

| filter | 147 days | 5.5 years |
|---|---|---|
| equilibrium | +0.0440%, t = 1.06 | +0.0363%, t = 1.49 |
| **fair value gap** | **+0.2007%, t = 2.61** | **−0.0377%, t = −1.36** |
| either | +0.0854%, t = 2.05 | +0.0282%, t = 1.12 |
| sweep-leg equilibrium (barred) | +0.0103%, t = 0.25 | +0.0061%, t = 0.25 |

**The fair value gap looked like a real partition on 147 days at t = 2.6 and
REVERSES SIGN on fourteen times the data.** On 42,354 entries the gap-filling
subset is worse than the entries the filter throws away. Equilibrium is
nothing on both windows. This is the shape of a short-window artifact, and
the only reason we can see it is that the backfill arrived.

**Read against his own check (step436 §11 — he trades a third to two thirds
of days), none of these filters is doing his job anyway.** Equilibrium keeps
48% of entries and EITHER keeps 53%, which is a coin flip dressed as a
filter; the gap keeps 14%, which is the right order of magnitude, and it is
the one that inverts.

### THE BY-PRODUCT, AND IT IS BIGGER THAN THE QUEUE ITEM

The parent on 5.5 years: **+0.1769% of price per entry over 42,354 entries,
t = 15.33.** Round 450 measured +0.0551% at t = 2.63 on 3,119. Same
construction, fourteen times the sample, **three times the effect size and
six times the t.** R450's "a hypothesis with a pulse, not a validated edge"
is no longer the right description of the bare 1-minute trigger on crypto.

The venue arithmetic is unchanged and gets larger, not smaller: median stop
0.240% of price, one Alpaca crypto round trip 0.50% of notional, so the
transaction is **2.1 stop distances** and the whole signal is about a third
of one round trip. Charged for honesty, deciding nothing (owner rule). The
number to hunt is still a cheaper venue — queue item 4.

### THE SEALED SLICE — ONE LOOK TAKEN, AND IT IS NOT A CANDIDATE

One cell cleared the full bar on R450's window: `4h swing low → 1m BOS, hold
24h` with the fair value gap filter (50 choosing / 21 middle trades,
choosing net +0.0079% against its parent's −0.3474%). The rule fixed before
the run allowed ONE look. Taken:

| sealed 2026-06-27 → 2026-07-26 | trades | gross | net | net R | win |
|---|---|---|---|---|---|
| pooled | 24 | +0.7244% | +0.2244% | **−1.984** | 20.8% |
| BTCUSD | 4 | +0.6078% | +0.1078% | | |
| ETHUSD | 10 | +0.8173% | +0.3173% | | |
| SOLUSD | 10 | +0.6782% | +0.1782% | | |

**This is NOT proposed for deployment and must not be treated as a survivor.**
Positive in price terms on all three windows, and disqualified by everything
else in the round: 24 sealed trades on a 30-day slice; **net risk multiple
−1.98**, because at a 0.245% stop the 0.50% round trip is two stop distances
before the trade starts; and the identical filter on fourteen times the data
has the opposite sign, which is the round's main finding. One cell surviving
out of 96 when chance gives 6 is not a survivor, it is the expected tail.

### Looks consumed

**ONE, and it is spent.** The final 20% of the CRYPTO 1-minute
sweep-to-break-of-structure family is now consumed and must never be
re-opened for this family. Both sealed windows this family had — SPY/QQQ
(R474) and crypto (this round) — are now gone.
**Note for whoever runs the next crypto 1-minute round:** the backfilled
2021-2026 window has slice boundaries that R450 and R475 have both already
read inside. There is no clean out-of-sample slice left on this family
without new data or a new instrument.

### Honest limits

- The 147-day window's slices are ~88 / ~30 / ~30 days. Cells that thin were
  always going to throw a tail cell, which is exactly what happened.
- The 5.5-year window's parent t of 15.33 is computed across entries, not
  clustered by day. R474 showed day-clustering roughly halves a t of this
  shape on the index; the crypto number is not clustered here and should be
  before anything is built on it.
- The gap kill rule implemented is the settled one (a body close through
  it). His softer "spent once the trend continued past it" kill (step432
  line 165) is not built, because it has no mechanical definition in the
  spec and inventing one would be a swept parameter.

## ROUND 476 — his 1-minute trigger beats a random entry by 13 standard errors over 5.5 years, and still loses money at Alpaca's toll (2026-08-01)

**What was tested.** Queue item 2, exactly as written: the crypto 1-minute
arm re-run on the backfilled 2021-01-01 → 2026-07-26 history, delivering the
three things owed — the t **clustered by day**, the **year-by-year** read
R450 could not do, and the **arm-A / arm-B / random-control** comparison
redone at the new sample size.

File: `step476_crypto_1m_full_history.py`, output `step476_output.txt`,
tables `step476_arms.csv`, `step476_by_year.csv`, `step476_cells.csv`.

**No new construction, no grid, no tuning.** Round 450's module is imported
and its `run_asset` called unchanged — same two-candle swings, same sweep
scan, same 1-minute body-close trigger, same structural stop (the extreme
traded between the sweep and the entry), same 2-hour pending expiry, same
24-hour hold cap, same 0.50% round trip charged for honesty and used to
decide nothing. This round measures a population; it does not propose one.

**THIS ROUND COULD NOT QUALIFY ANYTHING, AND THE SCRIPT HAS NO QUALIFICATION
BLOCK.** Both sealed windows on this family are spent — SPY/QQQ in R474,
crypto in R475 — and the backfilled window has boundaries R450 and R475 have
both already read inside. Stated at the top of the file and at the top of the
output. **Looks consumed: NONE.**

### A correction to how R475's headline number is recorded

RESEARCH_LOG describes R475's by-product as "the parent on 5.5 years:
+0.1769% of price per entry over 42,354 entries, t = 15.33." That number is
R475's **choosing slice only** — `partition_effect` filters `sig_t < t_tr`
before it counts. It is 2021-01-01 → 2024-05-04, not the full window.

The whole 5.5 years holds **71,073 arm-B entries**, and the choosing slice is
~60% of 2,032 days at the same rate, which lands on ~42,800 — R475's 42,354.
Weighting this round's per-year grosses across those same dates reproduces
+0.174% against R475's +0.1769%. The two runs agree exactly; only the label
was wrong. **The whole-window figure is +0.1435%, not +0.1769%**, and the gap
between them is not noise — it is the decay documented below.

### DELIVERABLE 3 — the three constructions, whole window

| construction | entries | days | gross % of price | t naive | **t by day** | gross R | net R | median stop | lev @1% |
|---|---|---|---|---|---|---|---|---|---|
| 5-minute trigger (R370's) | 75,023 | 2,033 | +0.0296% | 3.11 | **3.30** | 0.080 | −0.982 | 0.663% | 1.5x |
| **1-MINUTE trigger (his)** | 71,073 | 2,033 | **+0.1435%** | 18.37 | **13.77** | 0.640 | **−6.041** | 0.242% | 4.1x |
| RANDOM entry, same stop machinery | 41,623 | 2,033 | +0.0024% | 0.26 | **0.06** | 0.149 | −7.741 | 0.267% | 3.7x |

Clustering unit is the **UTC calendar day** — the live desk's boundary, and
OURS, because crypto has no session. Every entry on BTC, ETH and SOL inside
one day collapses to one observation, because three coins on one day are one
draw of the market and not three. That is the most conservative reading
available and it is the one quoted.

**Day-clustering costs 25% of the t here, not the ~50% R474 found on the
index.** t naive 18.37 → t by day 13.77. R474's warning was correct in
direction and roughly twice too pessimistic for this population: index
entries pile into a handful of hours a session, crypto entries spread across
2,033 unbroken days at ~35 a day.

**The control is clean, and that matters more than the headline.** A random
entry with the identical stop machinery returns +0.0024% at t = 0.06 — not
approximately zero, zero. Whatever arm B is measuring, it is not an artifact
of the stop construction, the hold cap or the cost model, because all three
are shared with a control that returns nothing.

Paired on shared UTC days, which is the comparison to quote:

| difference | per day | t | shared days |
|---|---|---|---|
| 1-minute trigger − 5-minute trigger | +0.0994% | **9.17** | 2,033 |
| **1-minute trigger − RANDOM entry** | **+0.1504%** | **13.13** | 2,033 |
| 5-minute trigger − RANDOM entry | +0.0510% | 3.61 | 2,033 |

**R370's question is answered at scale: his 1-minute trigger is not a
refinement of the 5-minute one, it is five times the effect.** And the
5-minute construction, dead on SPY 72 cells out of 72 and negative on
crypto's 147 days (−0.0352%, t = −1.40 in R450), is weakly ALIVE on 5.5 years
of crypto — +0.0296%, beating random by t = 3.61. Reported because the queue
asked for this comparison. It is not a candidate and the standing ban on
re-testing that construction is untouched.

### DELIVERABLE 2 — year by year, the read R450 could not do

| year | slice label | 1m entries | days | 1m gross | t by day | 1m gross R | 1m net R | 5m gross | control gross |
|---|---|---|---|---|---|---|---|---|---|
| 2021 | choosing | 13,890 | 365 | **+0.2908%** | 8.46 | 0.832 | −7.880 | +0.1640% | +0.0604% |
| 2022 | choosing | 13,956 | 365 | +0.1800% | 8.12 | 0.814 | −5.338 | +0.1062% | +0.0418% |
| 2023 | choosing | 11,314 | 365 | +0.0371% | 1.87 | 0.319 | −6.306 | −0.1066% | −0.0535% |
| 2024 | middle | 10,863 | 366 | +0.1320% | 5.58 | 0.603 | −6.199 | +0.0108% | +0.0046% |
| 2025 | late | 13,609 | 365 | +0.1106% | 6.10 | 0.572 | −5.313 | +0.0103% | −0.0290% |
| 2026 | late | 7,441 | 207 | +0.0387% | 2.09 | 0.619 | −4.624 | −0.0922% | −0.0350% |

Slice labels are R450's boundaries carried for continuity only. No slice here
is sealed and none was spent.

**Gross is positive in 6 of 6 years and the risk multiple after costs is
positive in 0 of 6.** That single line is the round.

**It is not one regime, and it is not stationary either.** The two strongest
years are the two oldest (2021, 2022) and the two weakest are 2023 and the
2026 stub — 2026 being the seven months the desk actually lives in, at
+0.0387% and t = 2.09. The effect never changes sign, and it is about a
seventh the size today that it was in 2021. R450's 147 days sat inside that
2026 stub, which is why R450 measured +0.0551% and R475's choosing slice,
weighted to 2021-2022, measured +0.1769%. Every number this family has
produced is consistent once the year is attached to it.

### Arm B by asset — three coins agree

| asset | entries | days | gross | t naive | t by day | net | gross R | net R | median stop |
|---|---|---|---|---|---|---|---|---|---|
| BTCUSD | 25,443 | 2,033 | +0.0865% | 10.21 | 9.42 | −0.4135% | 0.509 | −8.744 | 0.185% |
| ETHUSD | 25,415 | 2,033 | +0.1545% | 13.77 | 12.00 | −0.3455% | 0.614 | −5.203 | 0.239% |
| SOLUSD | 20,215 | 1,615 | +0.2014% | 9.59 | 8.05 | −0.2986% | 0.836 | −3.692 | 0.341% |

Positive gross on all three with day-clustered t of 8 to 12, so this is not a
coin fact (SOL's Alpaca history is shorter, hence 1,615 days). Under the
standing transfer rule that is three assets agreeing — **but agreement is a
hypothesis, not validation, and there is no clean out-of-sample slice left on
this family to validate it against.** The effect size also tracks the stop
size across the three coins almost exactly, which is what a signal
proportional to volatility looks like: gross R is far flatter (0.51 / 0.61 /
0.84) than gross % of price.

### The cell census, and why 0 of 32 does NOT mean the signal failed

| arm | cells | positive on both labelled slices and 2+ assets | expected by luck | median gross choosing | median net choosing | median stop |
|---|---|---|---|---|---|---|
| 5-minute | 32 | 0 | ~4 | +0.0013% | −0.4987% | 1.253% → 0.8x |
| 1-minute | 32 | 0 | ~4 | **+0.1388%** | **−0.3612%** | 0.406% → 2.5x |

**Read that pair of columns before reading the zero.** The cell machinery
scores on NET, and at a 0.50% round trip against a median gross of +0.1388%
nothing can pass arithmetically — the census is measuring Alpaca's fee
schedule, not his method. It is printed so the shape of the population is on
the record and for no other use, and it cannot promote anything regardless,
because the slices it is cut on have already been read by R450 and R475.

### The whole round in one paragraph

His sweep → 1-minute break of structure is a **real, six-year, three-coin,
day-clustered, control-beating signal of about +0.14% of price per entry**,
and at Alpaca's crypto rates it is **worth −6 times the risked amount per
trade**. Median structural stop 0.242% of price (4.1x at 1% risked, inside
the 10x US cap); one round trip 0.50% of notional, which is **2.07 stop
distances charged before the trade moves**; the entire signal is **0.29 of
one round trip**. The method does not need to get better. The venue needs to
get roughly ten times cheaper. **Queue item 4 — the venue table — is now the
only thing standing between this desk and a measured edge**, and it is a
written table, not a backtest.

### Honest limits

- **Nothing here is out-of-sample.** Every number is a description of tape
  R450 and R475 have already read. A candidate off this family needs a NEW
  instrument or NEW data, and no amount of sample size substitutes for that.
- The UTC day is our clustering unit and our day boundary. A different
  boundary would redistribute entries across clusters and move the clustered
  t somewhat; it would not touch the naive t or any mean.
- The decay from 2021 to 2026 is measured, not explained. It could be the
  market, or it could be that Alpaca's early crypto tape is thinner and its
  bars noisier. This round does not distinguish those.
- The random control enters every 60th 5-minute bar, so it holds 41,623
  entries against arm B's 71,073 and its days are the same 2,033. Paired
  daily differencing handles the count mismatch; a control matched entry-for
  -entry was not built.
- Arm A's revival on the long window is reported, not investigated. It is
  still barred from testing as a candidate.

### Looks consumed

**NONE.** No sealed slice exists on this family and none was opened.

## ROUND 477 — his daily bias is the first partition that keeps the right share of the entries, and it does not make them better (2026-08-05)

**What was tested.** Queue item 3, exactly as written: his daily / 4-hour
bias as a PARTITION of the population R450 built, one partition, both
directions reported, chance baseline stated. Run after item 2 (R476) so both
partitions are measured against the same unfiltered population.

File: `step477_tjr_daily_bias_partition.py`, output `step477_output.txt`,
tables `step477_populations.csv`, `step477_partition_effect.csv`,
`step477_by_direction.csv`, `step477_by_year.csv`, `step477_counts.csv`,
`step477_table.csv`, `step477_gross_clears.csv`.

**THIS ROUND COULD NOT QUALIFY ANYTHING AND OPENED NO LOOK.** Both sealed
windows on this family are spent (R474 SPY/QQQ, R475 crypto) and the
backfilled 2021-2026 window has boundaries R450 and R475 have both already
read inside. Stated at the top of the file and the top of the output.
**Looks consumed: NONE.**

**The bias definition, and it is his.** step434 §1D settles which procedure he
actually runs: on every live bootcamp morning he runs **Procedure B**, nested
trend, not the previous-session profile method he teaches. So the bias on a
timeframe is the direction of the most recent **body-close break of the most
recent confirmed two-candle swing**, held until it flips ("we're going to
stick to this bias until we're proved wrong", Day50). **Daily sets it, the
4-hour must agree** ("at least I need the daily and the four hour to be in
confluence", Day50), daily wins conflicts (Day49). Structure is read with
R450's own `tjr_swings`, so nothing new was invented. Procedure A is NOT
built: he teaches it and does not perform it, it needs a London session a
24/7 market does not have, and the spec itself flags merging the two as our
reconstruction he never endorsed.

Three partitions, each one a sentence of his: **DAILY** (trade runs with the
daily bias), **H4** (with the 4-hour), **AGREE** (both, and they agree — his
live rule, and the primary). Reported beside them: the **STAND-DOWN set**,
the entries taken on days the two timeframes disagree, which his instruction
discards wholesale.

### THE ONE THING THAT WORKED: the filter is finally the right SIZE

| population | entries kept | share of parent |
|---|---|---|
| parent, bare sweep → 1m BOS | 96,528 | 100.0% |
| with the DAILY bias | 48,110 | 49.8% |
| with the 4-HOUR bias | 37,374 | 38.7% |
| **with BOTH, and the two agree** | **22,244** | **23.0%** |
| days the two DISAGREE (he sits out) | 40,917 | 42.4% |

**AGREE is the first partition this family has produced that lands at his own
stated trading frequency.** He trades a minority of sessions, 7-15 days a
month (step434 §6F). R475's confluences kept 48% and 53% — a coin flip
dressed as a filter — and only its fair value gap kept the right order of
magnitude, and that one inverted. This keeps 23%. The shape is right.

### THE VERDICT: NO. THE BIAS DOES NOT SELECT A BETTER SUBSET.

Whole window, gross, one row per distinct entry, t clustered by UTC day
(R476's unit — three coins inside one day are ONE observation):

| population | entries | days | mean gross | t naive | **t by day** | median stop |
|---|---|---|---|---|---|---|
| parent, bare sweep → 1m BOS | 71,073 | 2,033 | **+0.1435%** | 18.37 | **13.77** | 0.242% |
| kept by DAILY | 35,264 | 2,029 | +0.1287% | 10.90 | 8.77 | 0.239% |
| thrown away by DAILY | 35,809 | 2,031 | +0.1580% | 15.43 | 11.64 | 0.244% |
| kept by H4 | 27,986 | 2,031 | +0.1252% | 10.48 | 9.08 | 0.242% |
| thrown away by H4 | 43,087 | 2,033 | +0.1554% | 15.10 | 10.94 | 0.241% |
| **kept by AGREE** | 16,608 | 1,859 | **+0.1200%** | 7.19 | 7.17 | 0.249% |
| **thrown away by AGREE** | 54,465 | 2,033 | **+0.1507%** | 17.06 | 12.52 | 0.240% |
| **STAND-DOWN set (he sits these out)** | 29,977 | 1,739 | **+0.1337%** | 11.11 | 6.44 | 0.232% |

**Every kept set is worse than the set it threw away, on all three
partitions.** And the cleanest line in the round: **the 42% of entries his
rule discards wholesale return +0.1337% against the parent's +0.1435%.** The
days he sits out are not worse days.

Kept minus thrown away — the only comparison that tests a partition:

| filter | unpaired | t | **paired by day** | **t** | shared days |
|---|---|---|---|---|---|
| DAILY | −0.0293% | −1.87 | −0.0215% | −0.60 | 2,027 |
| H4 | −0.0302% | −1.91 | +0.0303% | 1.01 | 2,031 |
| **AGREE** | **−0.0307%** | **−1.63** | **+0.0570%** | **1.59** | 1,859 |

**The two readings of the primary partition disagree in SIGN and neither is
significant.** Unpaired says the kept set is worse; paired-by-day says
slightly better. The gap is structural, not noise: AGREE's entries live on
1,859 days against the complement's 2,033, so the paired comparison silently
drops the 174 days on which his rule would have had nobody in the market at
all. When a partition's answer depends on which of two defensible poolings
you choose, there is no answer.

### Both directions, as the queue required

| population | LONG n | LONG gross | t/day | SHORT n | SHORT gross | t/day |
|---|---|---|---|---|---|---|
| parent | 35,201 | +0.1809% | 11.67 | 35,872 | +0.1068% | 9.43 |
| kept by DAILY | 18,958 | +0.1613% | 8.19 | 16,306 | +0.0909% | 5.55 |
| kept by H4 | 14,305 | +0.1509% | 6.92 | 13,681 | +0.0983% | 5.43 |
| **kept by AGREE** | 9,032 | +0.1560% | 5.73 | 7,576 | **+0.0770%** | 3.98 |
| thrown away by AGREE | 26,169 | +0.1895% | 9.88 | 28,296 | +0.1147% | 9.73 |

**The filter is worse than its own complement on BOTH sides**, so it is not a
hidden directional bet that happens to have paid — it is just weaker. Noted
separately: the parent's longs are 1.7x its shorts (+0.1809% vs +0.1068%),
which is this family's own long bias and belongs to the population, not to
the filter.

### The primary partition by asset — and this is where it dies

| asset | kept n | kept gross | thrown n | thrown gross | **paired diff** | **t** |
|---|---|---|---|---|---|---|
| BTCUSD | 5,897 | +0.0382% | 19,546 | +0.1010% | **−0.0075%** | **−0.21** |
| ETHUSD | 6,018 | +0.1280% | 19,397 | +0.1627% | **−0.0003%** | **−0.01** |
| SOLUSD | 4,693 | +0.2125% | 15,522 | +0.1981% | **+0.2295%** | **1.96** |

**Two exact zeros and one coin.** The entire paired-by-day positive is SOL,
and even SOL does not reach 2. Under the standing transfer rule (R89/R100/
R170/R190) that is a coin fact, not a finding — and this is precisely the
failure mode the rule was written to catch.

### Year by year — the only thing pointing the other way, and it is thin

| year | parent n | parent gross | AGREE n | AGREE gross | kept share | paired diff | t |
|---|---|---|---|---|---|---|---|
| 2021 | 13,890 | +0.2908% | 3,118 | +0.3046% | 22.4% | +0.0308% | 0.29 |
| 2022 | 13,956 | +0.1800% | 3,037 | +0.1614% | 21.8% | +0.0919% | 0.89 |
| 2023 | 11,314 | +0.0371% | 2,862 | +0.0359% | 25.3% | +0.0382% | 0.65 |
| 2024 | 10,863 | +0.1320% | 2,488 | +0.1293% | 22.9% | +0.1003% | 1.24 |
| 2025 | 13,609 | +0.1106% | 3,298 | +0.0353% | 24.2% | +0.0147% | 0.19 |
| 2026 | 7,441 | +0.0387% | 1,805 | +0.0064% | 24.3% | +0.0770% | 0.89 |

The paired difference is positive in **6 of 6 years**, which a sign test puts
at about 1 in 32 — the strongest thing in the round pointing in the bias's
favour, and it is recorded rather than buried. It does not survive contact
with the rest: **every one of the six t values is below 1.25**, the pooled
paired t is 1.59, and the by-asset table shows the whole effect is SOL. The
kept share is also stable at 22-25% across all six years, which is a good
sign about the *definition* and says nothing about the *edge*.

### The two cell censuses, and why the first one is worthless here

**On NET: 0 of 96 cells clear, against ~6 expected by luck.** That number is
measuring Alpaca's fee schedule and nothing else — at a 0.50% round trip
against a ~0.14% gross, no cell can pass arithmetically. R476 made this point
and it applies with full force. Letting that census stand alone would also
let costs gate a config, which the owner rule forbids outright. It is
recorded for continuity and is not evidence about the bias.

**On GROSS — the census that actually tests the partition — 12 of 96 clear,
against ~1.5 expected by luck** (a cell clears when the kept set is positive,
beats its parent AND beats its complement, on both labelled slices).

That 8x is an **upper bound on the surprise, not a p-value**, and the script
says so. The 96 are not 96 independent draws: the four target settings score
the SAME entries so each population is counted up to four times, and AGREE is
a strict subset of both DAILY and H4. Collapsed to distinct level × filter
populations — the honest unit — it is **5 of the 24 that exist**, and they
cluster on three levels: `prev day low`, `prev day high`, `last session
high`. Ten of the twelve raw clears are SHORT cells, while the pooled short
read above is *worse* under the filter, which is what it looks like when a
handful of mid-sized cells drift up against a population dominated by the 1h
swing levels going the other way.

**Nothing here can be pursued anyway.** Any follow-up on that cluster would
be re-tuning a partition after seeing which cells cleared, on slices R450 and
R475 have already read, in a family with no sealed window left on any
instrument. It is recorded so nobody re-derives it and mistakes it for news.

### The whole round in one paragraph

His daily/4-hour bias is the first filter this family has produced that keeps
the right **share** of the entries — 23%, his own stated frequency, where
R475's confluences kept a coin flip. It does not improve the entries it
keeps. Kept +0.1200% against thrown-away +0.1507%; the paired and unpaired
readings disagree in sign and neither reaches 2; the positive one is entirely
SOL, with BTC at −0.0075% and ETH at −0.0003%; and the 42% of entries his
stand-down rule discards outright return +0.1337% against the parent's
+0.1435%. **The bias is a real risk-management rule that cuts exposure by
three quarters at no measurable cost to the average entry — which is a
finding about SIZE, not about selection.** Queue item 4, the venue table,
remains the only thing standing between this desk and a measured edge.

### Honest limits

- **Nothing here is out-of-sample.** Every number describes tape R450 and
  R475 have already read. No amount of sample size substitutes for that.
- The bias is read on UTC-cut daily and 4-hour candles. Crypto has no session
  and nothing decides the boundary for us; a different cut would move which
  side of a marginal close the bias sits on. Not tested, and it should not be
  swept as a parameter.
- A candle closing through both the recent swing high and the recent swing
  low leaves the bias unchanged rather than picking a side. Stated before the
  run; a tiebreak would have been a hidden parameter.
- 270 entries (0.3%) landed before either timeframe had formed a bias and are
  in neither the kept nor the thrown-away set.
- Procedure A is untested here, not refuted. Testing it would need a session
  structure this market does not have, so it is closed on this instrument
  rather than open.
- The gross census bar ("beats parent and complement on both slices") is six
  conditions and its 1-in-64 baseline assumes independence, which these cells
  do not have. The collapsed count is the number to read.

### Looks consumed

**NONE.** No sealed slice exists on this family and none was opened.

---

## ROUND 478 — the venue can get 9.4x cheaper on a US-legal CFTC venue, and that flips the average entry positive without touching the method (2026-08-06)

**Hypothesis / queue item 4.** "What a crypto round trip actually costs, venue
by venue. Not a backtest — a table." Deliverable: taker and maker rates,
US-person availability, and the 10x legal leverage ceiling, for every venue a
US person can actually use. Built in `step478_venue_cost_table.py`. No orders,
no live file touched, no account opened, no money moved.

**Looks consumed: NONE.** This round fits nothing, sweeps nothing and reads no
out-of-sample slice. It is arithmetic on published fee schedules against
numbers R476 already established. No test window was touched.

### The premise of the queue item had gone stale, in the desk's favour

The item assumed the US menu is spot venues charging tens of basis points,
under a 10x legal leverage ceiling. Both halves are now out of date:

1. **CFTC-regulated crypto PERPETUALS exist onshore.** Coinbase Financial
   Markets listed nano perpetual-style futures to US persons on 2025-07-21;
   Kraken Derivatives US launched Bitnomial-listed perps on 2026-06-15.
2. **Futures bill PER CONTRACT, not as a percentage of notional.** That single
   fact is what closes the gap, and it is why the answer was never "shop for a
   lower percentage."

Kraken Derivatives US charges a flat **$0.15 per contract per side, all-in**
($0.03 commission + $0.10 exchange/clearing + $0.02 NFA). Contracts are sized
0.01 BTC / 0.5 ETH / 5 SOL, which at 2026-08-06 marks (BTC $64,771, ETH
$1,911, SOL $73.99) puts notional in a $370–$960 band. That band is the whole
mechanism, and it is also the fragility: the percentage moves **inversely with
price**. If BTC halves, the BTC round trip doubles.

### The table

| venue / execution | round trip | vs Alpaca taker | net per entry | cost / signal |
|---|---|---|---|---|
| Alpaca spot, TAKER (base) | 0.5000% | — | **−0.3565%** | 3.48x |
| Alpaca spot, MAKER (base) | 0.3000% | 1.7x cheaper | **−0.1565%** | 2.09x |
| Kraken Derivatives US, SOL | 0.0811% | 6.2x cheaper | **+0.0624%** | 0.57x |
| Kraken Derivatives US, BTC | 0.0463% | 10.8x cheaper | **+0.0972%** | 0.32x |
| Kraken Derivatives US, ETH | 0.0314% | 15.9x cheaper | **+0.1121%** | 0.22x |
| **Kraken Derivatives US, 3-coin avg** | **0.0529%** | **9.4x cheaper** | **+0.0906%** | **0.37x** |

Charged against R476's signal: **+0.1435% of price per entry, gross, 71,073
entries, 3 coins, 2021–2026.**

### Two findings, and they must not be merged

**FINDING A — Alpaca's own maker rate is 0.15% a side, not 0.25%.** Every
backtest in this log has been charged 0.50% round trip, i.e. taker on both
legs. Posting both legs on the venue the desk **already has** takes the round
trip to 0.30%, a **1.67x cut, no new account, no new venue, available today.**
It is not free — a post-only entry that does not fill is a missed trade, and
`backtest.py` already models exactly that (`execution="maker"` chases at the
close on a miss). This is a change to how the desk FILLS.

**FINDING B — US perps are a 9.4x cut.** The queue asked for a factor of four.
This is **9.4**. The sign of the average entry flips from −0.3565% to +0.0906%
of price **on the venue change alone, with no change whatsoever to the
method.** Worth roughly 0.45% of price per entry, the largest single
improvement available to this desk.

### The catch, and it is a real one

R476 established that this effect **decays**: 2021 +0.2908% → the 2026 stub at
+0.0387%. Charging the new venue against the most recent year:

| venue | 2021 net | 2026 net |
|---|---|---|
| Alpaca taker | −0.2092% | −0.4613% |
| Kraken US, ETH | +0.2594% | **+0.0073%** |
| Kraken US, BTC | +0.2445% | **−0.0076%** |
| Kraken US, 3-coin avg | +0.2379% | **−0.0142%** |

**The 2026 signal (0.0387%) and the new cost (0.0529% avg) are the same
size.** On the most recent year the average entry is at or below break-even
even after the venue is fixed. Stated plainly: **the venue change removes the
COST objection and does nothing at all to the DECAY objection.** It does not
make the 1-minute sweep-to-BOS family tradeable. Nothing is proposed for
deployment by this round.

### Stop distances, and the leverage ceiling is not binding

Per coin, on each coin's own R476 structural stop (never a pooled one):

| coin | stop % | Alpaca RT | Kraken US RT | leverage @ 1% risked |
|---|---|---|---|---|
| BTC | 0.185% | 2.70x | 0.25x | 5.41x |
| ETH | 0.239% | 2.09x | 0.13x | 4.18x |
| SOL | 0.341% | 1.47x | 0.24x | 2.93x |

Alpaca charges 2.0–2.7 stop distances before the trade moves; the US perp
venues charge 0.13–0.25.

**On the "10x legal ceiling": it is not binding and it never was.** Coinbase's
US perps allow up to 10x; Kraken Derivatives US sets margin per contract. The
method needs **2.9x on SOL, 4.2x on ETH, 5.4x on BTC**, read off its own
structural stop at 1% risked. All three fit inside 10x with room. **The
STANDING PRIORITY's 15–20x tier is asking for leverage this method does not
need and cannot justify from chart structure.** The binding constraint was
never leverage. It was cost.

### Contract granularity — the cost nobody quotes

Futures trade in whole contracts; a percentage venue lets any size through, a
contract venue rounds, and rounding is real tracking error. At 1% risked on
R476's pooled 0.242% stop, position notional is 4.13x equity. The coarsest
contract is ETH at $955.60. To hold ≥20 of them (rounding under ~2.5% of
position) the account needs about **$4,625 of equity**. **Below roughly $5,000
the rounding error on the coarsest leg is larger than the fee saving being
chased, and the venue change stops being worth it.**

### Every venue a US person can actually use

**Perpetual futures, CFTC-regulated, US persons eligible**
- **Kraken Derivatives US** — $0.15/contract/side all-in, flat. Bitnomial-listed,
  16 perps at launch 2026-06-15. Sizes 0.01 BTC / 0.5 ETH / 5 SOL. Leverage set
  by per-contract margin. **Primary-sourced; this is the figure the round leans on.**
- **Coinbase Financial Markets** — 0.00% maker / 0.03% taker, *promotional*, plus
  a per-contract fixed component reported at $0.10–$0.15 (**secondary source —
  verify before sizing on it**). Nano sizes 0.01 BTC / 0.10 ETH. Up to 10x.

**Spot, US persons eligible** (maker / taker, base tier, per side)
- Alpaca 0.15 / 0.25 ← what the desk uses now
- Kraken Pro 0.25 / 0.40
- Gemini ActiveTrader 0.00–0.20 / 0.03–0.40, volume-tiered
- Coinbase Advanced 0.40 / 0.60 — the most expensive retail venue on the list
- Robinhood — no explicit commission, paid through the spread. **A desk that
  charges honest costs cannot use a venue that will not state them.**

**NOT available to US persons — recorded so nobody re-proposes them**
- BloFin (the desk's old venue, dropped 2026-07-25), Bybit (Excluded
  Jurisdiction, KYC-enforced), Hyperliquid (front-end geo-blocked).
- **Kraken Derivatives INTERNATIONAL** (PF_XBTUSD, 0.02%/0.05%, up to 100x) is
  **NOT the US product.** Anyone quoting 100x leverage or a 0.05% taker rate for
  a US account has read the wrong page. This round refuses to blur the two.
- A VPN does not make any of these available; it is a terms-of-service breach
  with frozen-funds and clawback risk.

### Honest limits

Three costs are real, unmeasured here, and **every one cuts against the
conclusion.** None are estimated — guessing them would be the same sin as
tuning a parameter after seeing a test.

1. **SPREAD.** The fee is not the round trip; the spread is the other half. On
   a $370–$960 contract in a US perp market weeks-to-months old it could exceed
   the fee outright — a 1-tick spread on a thin book can be 0.1435% on its own,
   the entire signal. **This is now the open question, and it can only be
   answered by recording the book, not by reading a fee page.**
2. **FUNDING.** Perps pay/receive funding; spot does not. Kraken US settles it
   as one cash adjustment at 3:00pm CT daily, and the method holds 24 hours, so
   it eats a settlement essentially every trade. Sign and magnitude unknown.
   `backtest.py` already has `funding_series` machinery that could measure it.
3. **PROMOTIONAL RATES EXPIRE.** Coinbase's 0.00%/0.03% is explicitly
   promotional. Kraken US's $0.15 is a standing published schedule with a
   stated right to change.
4. Marks are a 2026-08-06 snapshot. The flat-fee venues' cost-as-a-percentage
   is a function of price and will drift with it.

### Verdict

**The venue can get cheaper by a factor of 9.4 on a CFTC-regulated,
US-person-legal venue, at leverage the method's own stops already justify.**
Two things are actionable with no further research: Alpaca maker-both-legs
(1.67x, today), and US perps (9.4x). One thing is true and is **not** a green
light: the 2026 stub of the signal is still eaten by the new cost. **No
strategy is proposed for deployment. NOTHING DEPLOYED, NO LOOK CONSUMED, NO
ORDER PLACED.**

### Looks consumed

**NONE.** Not a backtest. No sealed slice opened, none exists to open.

---

## ROUND 479 — the spread on the US perp book is the same size as the fee, so R478's cost table was optimistic by about half (2026-08-11)

**Queue item 5.** R478 priced the FEE on the US perpetual venues and refused to
guess the SPREAD, which made every number it published an upper bound on how
good the venue is. This round measures the spread off the live book.

### Looks consumed

**NONE.** Not a backtest. Nothing is fitted, nothing is swept, no sealed slice
is opened. This is a recording of a public order book. **No account was
opened, no API key used, no order placed, no money moved.**

### First: both venues CAN be polled with no account, so the queue's stop-rule never triggered

The item said "if the venue cannot be polled without an account, say so and
stop — do not open one." It can be, on both:

- **Bitnomial** (the exchange that lists Kraken Derivatives US's perps) serves
  an unauthenticated WebSocket at `wss://bitnomial.com/exchange/ws` with a
  `book` channel: full snapshot on subscribe, level updates after. Its product
  specs are public REST at `bitnomial.com/exchange/api/v1/prod/product/specs/`.
- **Coinbase Derivatives** serves an unauthenticated REST book at
  `api.coinbase.com/api/v3/brokerage/market/product_book`.

**Symbol correction.** The queue wrote PETHIUZ50 / PSOLUZ50. The live symbols
are **PETHUIZ50** (id 5608) and **PSOLUSZ50** (id 5609). PBTCUCZ50 (5614) was
right. Confirmed off the public spec endpoint, not guessed.

### The specific fear in the queue item is REFUTED, and a different one replaces it

The item's worry was that "a 1-tick spread on a thin book can be 0.1435% of
price on its own — the entire signal." **It cannot.** One tick, measured:

| contract | tick | tick as % of price |
|---|---|---|
| PBTCUCZ50 | $5.00 | **0.0078%** |
| PETHUIZ50 | $0.20 | **0.0107%** |
| PSOLUSZ50 | $0.01 | **0.0132%** |

One tick is a **ninth to an eighteenth** of R476's signal. Tick granularity was
never the risk. **The risk is how many ticks wide the book actually sits**, and
that is the thing worth measuring: Bitnomial rests **5–6 ticks wide**, Coinbase
**2 ticks wide.**

### The measurement

1,728 samples, every 20 seconds, 2026-08-11 06:43–08:40 UTC, written to
`data_usperp_book.jsonl` by `step479_us_perp_spread_snap.py`.

**Median spread, % of price. One full spread is paid per round trip if both
legs cross.**

| venue | BTC | ETH | SOL | 3-coin avg |
|---|---|---|---|---|
| Bitnomial / Kraken US | 0.0470% | 0.0641% | 0.0661% | **0.0591%** |
| Coinbase Derivatives | 0.0156% | 0.0533% | 0.0264% | **0.0318%** |
| *Kraken INTERNATIONAL (control, NOT US-eligible)* | *0.0016%* | *0.0053%* | *0.0132%* | *0.0067%* |

Tails are well behaved on Coinbase (p99 = median) and not on Bitnomial, whose
BTC book reached 0.4382% and ETH 0.5242% at their worst — three to eight times
the median, and three times the whole signal.

### THE ANSWER TO THE QUEUE ITEM: fee + spread, against the signal

| venue | coin | R478 fee RT | spread | **ALL-IN** | vs full signal | vs 2026 signal |
|---|---|---|---|---|---|---|
| Bitnomial/Kraken US | BTC | 0.0463% | 0.0470% | **0.0933%** | +0.0502% | −0.0546% |
| Bitnomial/Kraken US | ETH | 0.0314% | 0.0641% | **0.0955%** | +0.0480% | −0.0568% |
| Bitnomial/Kraken US | SOL | 0.0811% | 0.0661% | **0.1472%** | **−0.0037%** | −0.1085% |
| Coinbase CDE | BTC | 0.0463% | 0.0156% | **0.0619%** | +0.0816% | −0.0232% |
| Coinbase CDE | ETH | 0.0314% | 0.0533% | **0.0847%** | +0.0588% | −0.0460% |
| Coinbase CDE | SOL | 0.0811% | 0.0264% | **0.1075%** | +0.0360% | −0.0688% |

Signal is R476's: **+0.1435%** of price per entry over 2021–2026, **+0.0387%**
on the 2026 stub. Coinbase's fee is carried at the Kraken US rate because R478
could only source Coinbase's per-contract component secondarily; its **spread**
is measured here, not assumed.

**The headline correction to R478.** R478 published a 3-coin average cost of
0.0529% and a net entry of **+0.0906%**. With the spread included the average
cost is **0.1120% on Bitnomial** and **0.0847% on Coinbase**, so the net entry
is **+0.0315%** and **+0.0588%**. **R478 was optimistic by 2–3x on the net, and
by roughly 2x on the cost.** It said so itself — it labelled the spread the
open question — but the corrected numbers belong on the record next to the
originals.

**What does NOT change: the venue is still much cheaper than Alpaca.** Against
Alpaca taker's 0.50% the US perps are **4.5x cheaper (Bitnomial) and 5.9x
cheaper (Coinbase)** all-in, not R478's 9.4x. **That comparison is unfair to
the US venue in a way worth naming: 0.50% is Alpaca's FEE, and Alpaca's spot
spread has never been measured by this desk either.** The honest statement is
that the US perp venues cost 0.085–0.112% all-in, and the true multiple against
Alpaca is at least 4.5x and probably better. It is not measured, so it is not
claimed.

### The same cost in stop distances, which is the unit that decides anything

| venue | coin | stop (R476) | all-in | in stop distances |
|---|---|---|---|---|
| Bitnomial | BTC | 0.185% | 0.0933% | 0.50x |
| Bitnomial | ETH | 0.239% | 0.0955% | 0.40x |
| Bitnomial | SOL | 0.341% | 0.1472% | 0.43x |
| Coinbase | BTC | 0.185% | 0.0619% | 0.33x |
| Coinbase | ETH | 0.239% | 0.0847% | 0.35x |
| Coinbase | SOL | 0.341% | 0.1075% | 0.32x |

R478 reported 0.13–0.25 stop distances on fee alone against Alpaca's 2.0–2.7.
The honest figure with the spread is **0.32–0.50**. Still transformative next
to Alpaca. Roughly double what R478 implied.

### THE FINDING NOBODY ASKED FOR: Bitnomial's book is too thin for a real account

Median resting notional:

| venue | coin | top of book | within 5 levels | equity that consumes 5 levels at 4.13x |
|---|---|---|---|---|
| Bitnomial | BTC | $31,978 | $50,449 | **$12,215** |
| Bitnomial | ETH | $23,418 | $43,097 | **$10,435** |
| Bitnomial | SOL | $3,775 | $11,704 | **$2,834** |
| Coinbase | BTC | $25,600 | $1,210,524 | $293,105 |
| Coinbase | ETH | $175,500 | $1,430,941 | $346,475 |
| Coinbase | SOL | $1,515 | $210,518 | $50,973 |

At R478's 4.13x position-to-equity, **Bitnomial has a usable window of roughly
$5,000 to $10,000 of equity** — floored by R478's contract-rounding limit and
capped by its own depth. **On Bitnomial SOL the window does not exist at all:**
its 5-level depth is consumed by a $2,834 account, which is below the $5,000
rounding floor. There is no account size that both clears the rounding and
fits inside the book.

Walking the book confirms it. Round-trip cost for a real order, VWAP against
mid, with the share of samples where the order did not fit inside 5 levels:

| venue | coin | $10k | $50k | $100k | didn't fit (10k / 50k / 100k) |
|---|---|---|---|---|---|
| Bitnomial | BTC | 0.0469% | 0.0527% | 0.0731% | 1% / 54% / 86% |
| Bitnomial | ETH | 0.0641% | 0.0760% | 0.0909% | 0% / 49% / 99% |
| Bitnomial | SOL | 0.1253% | n/a | n/a | 18% / 100% / 100% |
| Coinbase | BTC | 0.0156% | 0.0178% | 0.0228% | 0% / 0% / 0% |
| Coinbase | ETH | 0.0533% | 0.0533% | 0.0533% | 0% / 0% / 0% |
| Coinbase | SOL | 0.0419% | 0.0543% | 0.0685% | 0% / 0% / 0% |

The medians EXCLUDE the samples that didn't fit, so each one is optimistic by
exactly the percentage beside it. Only 5 levels a side were recorded, so this
sees nothing past level 5 — it is a floor on the cost, not a ceiling.

**Coinbase Derivatives is the better venue on both axes measured here** —
tighter on all three coins and one to two orders of magnitude deeper. R478
leaned on Kraken US because its fee schedule was primary-sourced and
Coinbase's was not. On the evidence of the book, Coinbase's fee is the number
worth chasing down properly.

### The control, and what it says about waiting

Kraken INTERNATIONAL is **not available to US persons and is not a candidate.**
It is here only to separate "young venue" from "this is what a perp costs":

| coin | US (Bitnomial) | offshore | ratio |
|---|---|---|---|
| BTC | 0.0470% | 0.0016% | **30.1x** |
| ETH | 0.0641% | 0.0053% | **12.0x** |
| SOL | 0.0661% | 0.0132% | **5.0x** |

A mature perp book is 5 to 30 times tighter than the US one. **Almost all of
the US spread is the venue's age, not the instrument.** That is a reason to
RE-MEASURE these venues periodically, not a reason to assume they will
converge — the offshore number is what is possible, not what is promised.

### Honest limits

1. **COVERAGE. 3 of 24 UTC hours (06–08).** The queue asked for the 24-hour
   clock and this is one slice of it, sitting in the Asia/early-London window.
   US-listed venues plausibly tighten during US hours and widen overnight, and
   this sample cannot see either. A launch agent
   (`com.wallace.usperp-book-snap`) now records 6 minutes at :30 past every
   hour into the same file, so **full-clock coverage exists from 2026-08-12**
   and the item stays open for that read.
2. **FUNDING is still unmeasured** and is queue item 6.
3. Marks are 2026-08-11 (BTC ~$63.9k). Flat per-contract fees move inversely
   with price; spread in % of price does too.
4. Only the top 5 levels a side were recorded.
5. Alpaca's own spot spread remains unmeasured, so the multiple against the
   incumbent venue is a lower bound.

### Two bugs in the recorder, found by running it, both of which would have flattered the answer

Recorded because a measurement round is only worth its instrument.

1. **The drain loop never sampled a busy book.** It continued on every
   websocket message, so it only reached its sample instant when the market
   went quiet — it would have measured spreads **exclusively during lulls**,
   which is the narrow half of the distribution and the wrong half.
2. **A dropped socket silently ended the recording** rather than
   re-subscribing, losing 47 minutes of the first run.

Both fixed. `step479b_book_validation.py` independently checks the third risk:
the Bitnomial book is maintained incrementally (snapshot + level updates), so a
bug in the apply loop would produce a stale book and an invented spread without
crashing. A second, independent websocket snapshot agrees with the running
recorder's top of book to within a few ticks.

### Verdict

**The spread does NOT eat the signal, and it is not negligible either — it is
the same size as the fee.** R478's cost figures roughly double once the book is
included, and its net-per-entry roughly halves. Every conclusion R478 reached
about DIRECTION survives; every number it attached to that direction was
optimistic.

**And the decay objection is now worse, not better. On the 2026 stub of the
signal, every coin on every US venue is NEGATIVE after fee and spread**
(−0.023% to −0.109% of price per entry). R478 said the venue removes the cost
objection and does nothing to the decay objection. With the spread measured,
the cost objection is **not fully removed either**.

**NOTHING PROPOSED FOR DEPLOYMENT. NOTHING DEPLOYED. NO LOOK CONSUMED. NO ORDER
PLACED. NO ACCOUNT OPENED.**

---

## ROUND 480 — the 24-hour clock closes queue item 5: the hour barely moves the spread, but one documented hour a day removes 90% of Coinbase's book (2026-08-12)

**Queue item 5, the leftover.** R479 measured the US perpetual book on 3 of 24
UTC hours (06–08) and left the item open for one thing only: read the same
recorder's output once the launch agent had covered the full clock. That read
is this round. `step479_us_perp_spread_snap.py --report` was run as the queue
instructed, and `step480_us_perp_spread_clock.py` does the part a pooled report
cannot — the hour-by-hour breakdown the item was actually asking for.

**NO LOOK CONSUMED.** Same standing as R479. This is a measurement of a
recorded order book. It fits nothing, sweeps nothing, and reads no
out-of-sample slice. No account, no key, no order, no money. Nothing in the
live bot touched.

**Data:** 5,064 samples, 2026-08-11 06:43 UTC → 2026-08-12 06:36 UTC, 24/24 UTC
hours on all three venues (Bitnomial/Kraken-US, Coinbase CDE, Kraken
International as the offshore control). 3,351 of those are US-venue rows.

### First, an honesty correction on the sample itself

R479's own recording is still in the file and **all of it sits in hours 06–08**,
so those three hours hold **38.9% of the samples against the 12.5% a flat clock
would give them**. The pooled median is therefore weighted toward exactly the
slice whose representativeness was the open question. Every number below is
reported **hour-equal-weighted** (mean of the 24 hourly medians) as well as
pooled. Two hours are thin (02 and 13 have 15 samples across all six US
series); their medians are printed with counts beside them and are not leaned
on.

### The open question, answered: R479's window was representative, and it erred toward pessimism

| venue | coin | R479's 06–08 | other 21 hrs | full-clock | R479's error |
|---|---|---|---|---|---|
| Bitnomial | BTC | 0.0470% | 0.0467% | 0.0444% | **+5.8%** |
| Bitnomial | ETH | 0.0641% | 0.0532% | 0.0539% | **+18.9%** |
| Bitnomial | SOL | 0.0661% | 0.0525% | 0.0511% | **+29.3%** |
| Coinbase | BTC | 0.0156% | 0.0156% | 0.0147% | **+6.3%** |
| Coinbase | ETH | 0.0533% | 0.0529% | 0.0427% | **+24.8%** |
| Coinbase | SOL | 0.0264% | 0.0264% | 0.0275% | −3.8% |

**Positive = R479 quoted a WIDER book than the clock really has.** In 5 of 6
series R479 was pessimistic, by up to 29%, and the one optimistic case is 3.8%.
This is the good direction to be wrong in and it is worth saying plainly:
**R479's conclusions do not need revising, they need loosening slightly in the
desk's favour.** No number here rescues the signal, and none was going to — the
corrections are hundredths of a percent against a decay problem measured in
tenths.

### Does the book have a time of day at all?

Yes, but weakly, and it is not the effect anyone expected.

| venue | coin | pooled | clock-wt | best hour | worst hour | worst/best | p (shuffle) |
|---|---|---|---|---|---|---|---|
| Bitnomial | BTC | 0.0469% | 0.0444% | 0.0352%@13 | 0.0546%@09 | 1.55x | 0.076 |
| Bitnomial | ETH | 0.0537% | 0.0539% | 0.0318%@05 | 0.0744%@13 | 2.34x | **0.018** |
| Bitnomial | SOL | 0.0529% | 0.0511% | 0.0263%@21 | 0.0792%@12 | 3.01x | **0.026** |
| Coinbase | BTC | 0.0156% | 0.0147% | 0.0078%@11 | 0.0236%@21 | 3.03x | **0.002** |
| Coinbase | ETH | 0.0529% | 0.0427% | 0.0265%@10 | 0.0537%@18 | 2.02x | 0.261 |
| Coinbase | SOL | 0.0264% | 0.0275% | 0.0262%@02 | 0.0396%@13 | 1.51x | **0.008** |

Control (R100's rule — beat luck, not zero): the hour labels were shuffled 500
times preserving each hour's sample count, and the statistic is the spread of
the 24 hourly medians. **4 of 6 series clear p < 0.05.** So the hour is real on
most series — but the honest reading is that **the effect is small and has no
usable shape**. The best and worst hours do not agree across coins or venues,
the US session does not systematically tighten these books, and the worst-to-
best ratio of 1.5–3x is applied to a number that is a third of a stop distance.
**There is no "trade at hour X" finding here and nobody should go looking for
one** — six series, 24 hours each, is 144 cells, and picking the good ones after
seeing them is the exact re-tuning this queue forbids.

### R479's headline holds hour by hour

Coinbase is tighter than Bitnomial in **24/24 hours on BTC, 23/24 on SOL, and
18/24 on ETH**, with median gaps of 0.0313% / 0.0263% / 0.0146%. R479 called
Coinbase the better venue on an average; it is the better venue on the clock.

### The corrected all-in table

Only the spread column changes — fee is R478's, quoted not re-derived.

| venue | coin | fee | spread (clock-wt) | ALL-IN | in stop distances | vs full signal | vs 2026 signal |
|---|---|---|---|---|---|---|---|
| Bitnomial | BTC | 0.0463% | 0.0444% | 0.0907% | 0.49x | +0.0528% | **−0.0520%** |
| Bitnomial | ETH | 0.0314% | 0.0539% | 0.0853% | 0.36x | +0.0582% | **−0.0466%** |
| Bitnomial | SOL | 0.0811% | 0.0511% | 0.1322% | 0.39x | +0.0113% | **−0.0935%** |
| Coinbase | BTC | 0.0463% | 0.0147% | 0.0610% | 0.33x | +0.0825% | **−0.0223%** |
| Coinbase | ETH | 0.0314% | 0.0427% | 0.0741% | 0.31x | +0.0694% | **−0.0354%** |
| Coinbase | SOL | 0.0811% | 0.0275% | 0.1086% | 0.32x | +0.0349% | **−0.0699%** |

**R479's central verdict is unchanged: on the 2026 stub of the signal, every
coin on every US venue is still NEGATIVE after fee and spread.** The full-clock
correction improves the numbers by 0.001–0.010% of price and the gap it needs to
close is 0.022–0.094%. Cost got slightly cheaper; decay did not move.

### The finding nobody asked for: Coinbase's book empties out for one hour, every day

The hour-21 column is not an outlier. At 21:30–21:36 UTC the Coinbase book
collapses **on all three coins simultaneously**, sustained across every sample
in the window, and it is the widest hour of the clock for BTC and SOL:

| venue | coin | depth @21:00 | depth other 23h | @21 as share |
|---|---|---|---|---|
| Bitnomial | BTC | $76,299 | $52,455 | 145% |
| Bitnomial | ETH | $60,102 | $45,768 | 131% |
| Bitnomial | SOL | $11,394 | $12,847 | 89% |
| Coinbase | BTC | $108,094 | $1,349,801 | **8%** |
| Coinbase | ETH | $68,584 | $1,422,206 | **5%** |
| Coinbase | SOL | $23,186 | $207,301 | **11%** |

**Mechanism, primary-sourced** (`docs.cdp.coinbase.com/derivatives/introduction/
market-hours`, read 2026-08-12): Coinbase Derivatives runs 24x7 for 24x7-enabled
products and halts only Fridays 16:00–16:50 CT — but **non-24x7 participants
take "a one-hour break each day from 4:00 PM – 5:00 PM CT."** That is
21:00–22:00 UTC, exactly the measured hour. The market stays OPEN; a large part
of who quotes it goes home. **2026-08-11 was a Tuesday**, so the weekly Friday
halt cannot explain it. Bitnomial shows no such hole, which is a real point in
its favour: it is continuous.

**Why this outranks the spread correction.** The method holds 24 hours, so
**every position spans this hour**. If a stop triggers inside it, the book
absorbing the exit is the thin one. R479's headline — Coinbase supports roughly
$300k of equity — is a **23-hour** number:

| venue | coin | R479 ceiling | 21:00 ceiling | cut |
|---|---|---|---|---|
| Coinbase | BTC | $326,828 | $26,173 | **0.08x** |
| Coinbase | ETH | $344,360 | $16,606 | **0.05x** |
| Coinbase | SOL | $50,194 | $5,614 | **0.11x** |
| Bitnomial | BTC | $12,701 | $18,474 | 1.45x |
| Bitnomial | ETH | $11,082 | $14,553 | 1.31x |
| Bitnomial | SOL | $3,111 | $2,759 | 0.89x |

**The exitable-at-all-times ceiling on Coinbase is $17k–$26k, not $300k** — the
same order of magnitude as Bitnomial's, which R479 rejected as too thin for a
real account. Coinbase remains the better venue on spread and on 23 of 24
hours of depth. It is not the order of magnitude roomier venue R479 described,
once the requirement is that a 24-hour position can be exited whenever it needs
to be.

### Honest limits

1. **ONE DAY.** The clock is fully covered; it is covered once. Hour effects on
   a book are the sort of thing that is stable day to day, but a single wide
   print in a thin hour moves that hour. Sample counts are printed beside every
   hour in `step480_output.txt`.
2. The 21:00 hole: the **mechanism is documented and recurs daily**, so it will
   be there tomorrow. The **magnitude** is one observation. Existence
   established, size indicative.
3. **The cost is clock-weighted, not entry-weighted.** R476 did not persist its
   71,073 entry timestamps, only its aggregates, so this assumes entries spread
   evenly over the 24 hours. Given how weak and shapeless the hour effect turned
   out to be, this matters little for the spread — but it matters for the 21:00
   hour, and that is now a queue item rather than something improvised here.
4. Only the top 5 levels a side are recorded, so every depth figure is a lower
   bound on the venue and the walk-the-book costs exclude the samples that did
   not fit.
5. Coinbase's fee is still carried at Kraken US's rate. That is queue item 7 and
   it is now the last unsourced number in the venue decision, alongside funding.

### Verdict

**Queue item 5 is CLOSED.** The 24-hour clock says R479's three-hour window was
representative and slightly pessimistic; the spread is real but has no usable
time-of-day shape; and R479's every DIRECTIONAL conclusion survives the full
clock. The cost picture moved in the desk's favour by hundredths of a percent
and the decay objection is untouched, so **nothing here changes the standing
answer: this method is not deployable on a US perpetual venue on its 2026
behaviour.**

The round's real output is the one it was not looking for: **the better venue
has a documented daily hour in which 90–95% of its book is absent**, and that
converts R479's "Coinbase supports ~$300k" into "~$20k if you require to be
able to get out at any moment." That is an operational constraint on account
size, and it belongs in front of any future deployment conversation.

**NOTHING PROPOSED FOR DEPLOYMENT. NOTHING DEPLOYED. NO LOOK CONSUMED. NO ORDER
PLACED. NO ACCOUNT OPENED.**

---

## ROUND 481 — funding is the one cost that is not a cost, and the reason is that the method does not actually hold 24 hours (2026-08-18)

**Queue item 6. The last unmeasured cost.** Research only. No orders, no
account, no live file touched. **No look consumed** — this is a cost laid over
an entry population the desk has already fully described (R476), not a
qualification of anything.

Script: `step481_funding_on_24h_hold.py`. Output: `step481_output.txt`.
Data out: `step481_entries_funding.csv` (68,992 chargeable entries with entry
AND exit timestamps), `step481_cadence.csv`, `step481_by_year.csv`.

### The caveat, fixed before the run

Bybit funding is a **proxy**. It is not Kraken's series, not Coinbase's, not
Bitnomial's. This round **bounds the magnitude and establishes the sign of the
mechanism** on the same three coins in the same hours. Nothing here may be
quoted as "US perp funding".

### The premise of the queue item is wrong, and that is the finding

Queue item 6 says: *"the method holds 24 hours, so it eats a settlement
essentially every trade."* It does not.

**24 hours is the CAP, not the hold.** The stop is the sweep-to-entry extreme
and it is tight, so the position is usually gone long before any settlement:

| hold length | p25 | **median** | p75 | p90 |
|---|---|---|---|---|
| hours | 0.13 | **0.72** | 4.43 | 24.00 |

**90.3% are stopped out; 9.7% run the cap out.** The median position lives
**43 minutes**. So:

- 8-hourly settlements straddled: **mean 0.68, median 0, and 68.4% of entries
  straddle none at all.**
- On a once-daily 3:00pm CT mark (Kraken US's cadence), **81% of entries miss
  the settlement entirely** — mean 0.21 per trade.

### The sign and the size

Sign convention stated once: positive funding means longs pay shorts, so the
charge is `-direction × rate` and **positive below = money in**.

| cadence | mean | median | t naive | t by day | stop distances |
|---|---|---|---|---|---|
| Bybit 8-hourly (the real series) | **+0.0001%** | +0.0000% | 0.27 | 0.64 | **+0.000x** |
| once-daily mark 20:00 UTC | −0.0003% | +0.0000% | −0.74 | −0.53 | −0.001x |
| once-daily mark 21:00 UTC | −0.0002% | +0.0000% | −0.55 | −0.37 | −0.001x |
| Bybit 8-hourly, gap-clean holds only | +0.0003% | +0.0000% | 1.67 | 2.17 | +0.001x |

**Funding is zero to three decimal places of a stop distance.** Against the
0.237% median structural stop it is 0.000–0.001x; against R478's 0.0529%
three-coin US round trip it is under 1% of the fee. Every cadence agrees, the
sign flips between them, and no reading reaches t = 2.2 even when it is helped.

### Why it is zero — and it is not because funding is small

The underlying rate straddled per hold averages **+0.0056% of price**, which is
real money. It nets out because **the method is direction-balanced**:

| side | entries | share | raw rate straddled | funding P&L | t by day |
|---|---|---|---|---|---|
| LONG | 34,208 | 49.6% | +0.0056% | **−0.0056%** | −13.54 |
| SHORT | 34,784 | 50.4% | +0.0056% | **+0.0056%** | +6.88 |

Each side individually pays or collects at high significance. The book takes
sweeps of lows and sweeps of highs in **almost exactly equal number**, so the
charge and the credit cancel. This is a structural property of the
construction — eight levels, four long and four high, scanned symmetrically —
not an accident of the window.

By asset: BTC +0.0004%, ETH +0.0000%, SOL −0.0003% (t by day 1.26 / 0.13 /
0.52). By year: a net credit in 2 of 6 and a net charge in 4, largest reading
+0.0019% (2023), the two significant years (2025 t −2.93, 2026 t −3.32) both
at **−0.0003%** — significance without magnitude, which is what 13,000 entries
buys you on a number that is genuinely near zero.

### The ledger, complete for the first time

Gross reproduces R476 **exactly** (all 71,073 entries, +0.1435%), which is the
check that matters — this round regenerated the population rather than trusting
a cache. The ledger runs on the 68,992 that sit inside funding coverage
(+0.1309%); the 2,081 dropped are early SOL from before Bybit listed the perp,
and they are the most volatile entries in the set.

| line | % of price | stop distances |
|---|---|---|
| gross per entry (arm B, hold-24h) | +0.1309% | +0.553x |
| fee + spread, Coinbase (R479) | −0.0847% | −0.358x |
| fee + spread, Bitnomial (R479) | −0.1120% | −0.473x |
| **funding, this round** | **+0.0001%** | **+0.000x** |
| *(Alpaca taker, what the log charged for a year)* | *−0.5000%* | *−2.114x* |
| **net, Coinbase, all three costs in** | **+0.0463%** | **+0.196x** |
| **net, Bitnomial, all three costs in** | **+0.0190%** | **+0.080x** |

**And the 2026 stub, which is the number that has been deciding this family:**
gross +0.0358%, funding −0.0003%, fee+spread −0.0847% → **net −0.0492%.**

### Verdict

**Queue item 6 is CLOSED. Funding does not move this decision in either
direction.** R479 was right that it was the one cost that could come back
positive; the honest answer is that it comes back at **zero**, because the
method's own symmetry cancels it. The last unmeasured cost is now measured and
it changes nothing.

**The cost side of this argument is finished.** Fee is sourced (R478), spread
is measured on the full clock (R479/R480), funding is measured here. The whole
cost stack on the better venue is **0.358 stop distances**, and on the whole
5.5-year window the method clears it with +0.196x left over. **On 2026 it does
not clear it, and that was true before this round and is true after it. Decay,
not cost, is the entire remaining objection — and nothing in the queue is
currently pointed at decay.**

### Two things found that were not asked for

1. **The "24-hour hold" premise is false everywhere it appears in this log,
   including in R480's conclusion.** R480 argued the daily 21:00–22:00 UTC
   Coinbase liquidity hole bites *"every position, because the method holds 24
   hours"*, and set the exitable-at-all-times account ceiling at $17k–$26k on
   that basis. The median position lives **43 minutes** and 90% are stopped out
   before the cap. That does not refute item 8 — a 43-minute position opened at
   20:50 UTC is still exposed, and the stop that fires inside the hole is still
   filled into a book at 5–11% of normal depth — but it **changes the arithmetic
   from "all of them" to a share that must now be counted.** Item 8(a) is the
   right way to count it, and it is now cheap: **entry and exit timestamps for
   all 68,992 entries are persisted in `step481_entries_funding.csv`**, so the
   regeneration that item 8(a) budgeted for is already done.
2. **Alpaca's 1-minute tape has gaps, and the 24-hour cap is counted in BARS.**
   8.0% of holds therefore span more than 24 hours of wall clock, the worst a
   single 18-bar "hold" spanning 10,013 hours. It does not move this round's
   answer (the gap-clean sensitivity is in the table above and reads the same
   zero), but it is a property of the tape every 1-minute round in this log has
   been running on without recording it, and it is recorded now.

### Honest limits

1. **Bybit is a proxy.** Sign and order of magnitude, not a venue price.
2. **The once-daily US cadence is modelled**, not observed: the same 8-hourly
   economics accumulated and paid at one mark. It answers "how often would a
   hold be exposed", not "what would Kraken have charged".
3. The population is R476's, on a window every slice of which has been read.
   **This round qualifies nothing and could not.**
4. The direction balance that produces the zero is a property of *this*
   construction. Any future variant that leans long or short **re-opens this
   question**, and at +0.0056% of price per hold on the exposed side it would
   not be a rounding error.

**NOTHING PROPOSED FOR DEPLOYMENT. NOTHING DEPLOYED. NO LOOK CONSUMED. NO ORDER
PLACED. NO ACCOUNT OPENED.**

---

## ROUND 482 — the exchange fee is $0.10 a side and sourced at last, and it is the smaller half of what the account actually pays (2026-08-20)

**Queue item 7**, opened by R479 and extended by R480. A page read and the
arithmetic it feeds. **No slice read. No look consumed. No account, no order, no
money.** `step482_coinbase_fee_source.py`, output persisted to
`step482_cde_fee_table.json`.

### What the item asked for, and the answer

R478 built its entire venue case on Kraken Derivatives US because that fee was
primary-sourced, and flagged Coinbase's per-contract component as SECONDARY.
R479/R480 then measured the books and found Coinbase is the better venue on both
spread and depth by a wide margin — which left the decision resting on the one
number nobody had sourced.

**It is sourced now, and from a regulatory filing rather than a marketing page:**

> Coinbase Derivatives, LLC, CFTC Regulation 40.6(a) self-certification,
> Submission **#2025-75**, "Modifications to the Fee Schedule", filed
> 2025-11-26, Appendix A (Clean): *"Effective Trade Date December 15, 2025 …
> Fees are charged per side (both the buy and the sell side) per contract."*

The schedule has two product bands. Every contract this desk would trade sits in
band 2 (nano and perp-style, **BIP / ETP / SLP** named explicitly):

| tier | electronic | block |
|---|---|---|
| Market Maker | $0.07 | $0.05 |
| Non-Professional | **$0.10** | $0.05 |
| Professional | **$0.10** | $0.05 |

Corroborated independently of Coinbase by Lincoln Park Financial, an unaffiliated
introducing broker, which publishes "Exchange Fee: $0.10/contract" on its BIP
page. Two sources, same number.

**The promotional component the item asked to separate does not exist.** There is
no promotional line, no waiver and no expiry anywhere in the perp-style band. The
whole $0.10 is standing. R478's remembered "promotional 0.00%/0.03%" belongs to
the **INTERNATIONAL (INTX) perp book, which a US person cannot trade**. It was
never a CDE rate and it is struck from this log.

**Which tier applies, and why it is free to know:** the filing defines
Non-Professional as an account that is, among other things, *"(C) Not using a
fully automated order generating computer system"*. **A bot disqualifies him** —
he is a Professional Trader by the exchange's own definition. Band 2 charges
Professional and Non-Professional **the same $0.10**. The disqualification costs
nothing. Recorded because it is expensive to discover late and free to know now.

### The fee as a percentage, on live contract sizes

A per-contract fee means nothing until it is divided by notional, and R478's
error was carrying one venue's contract sizes onto another's. Sizes and prices
read live off Coinbase's **public** product endpoint (no key, no account):
**BIP 0.01 BTC, ETP 0.1 ETH, SLP 5 SOL** — confirmed, not assumed.

| coin | notional | **CDE fee, round trip** | R478's Kraken US stand-in |
|---|---|---|---|
| BTC | $712 | **0.0276%** | 0.0463% |
| ETH | $226 | **0.0859%** | 0.0314% |
| SOL | $431 | **0.0460%** | 0.0811% |
| **average** | | **0.0532%** | 0.0529% |

**The averages are all but identical and the per-coin order is completely
reversed.** Coinbase's ETH contract is **0.1 ETH against Kraken's 0.5 ETH** —
five times smaller, so the same flat fee lands on a fifth of the notional. **ETH
goes from R478's cheapest coin to this table's most expensive, by 2.7x.**
R478's average survived by coincidence; every per-coin figure it attached to
Coinbase was wrong, and the cheap-venue conclusion it drew from them was right
for the wrong reasons.

### THE ROUND'S REAL OUTPUT: R478's framing is structurally wrong for a real account

R478's headline claim was that **"futures bill PER CONTRACT, not as a
percentage."** For the *exchange* that is true and is now sourced. **For the
retail path it is false.**

A US person does not face CDE directly. Derivatives balances are held with
**Coinbase Financial Markets (CFM)**, a CFTC-registered FCM and NFA member, and
**CFM charges its own commission on top of the exchange fee**. Every public
Coinbase statement about US perp pricing quotes CFM's number, and CFM's number is
**a percentage of notional**: *"fees as low as 0.02%"* (launch communications,
2025-07-21).

**"As low as" is a volume-tier floor, not a rate.** The standing retail tier table
is behind coinbase.com, which refuses unauthenticated requests — HTTP 403 on the
fee page, the overview page and the product page alike. **It is UNSOURCED and this
round does not invent a value for it.**

What it does to the arithmetic, average round trip across the three coins:

| stack | avg RT | BTC | ETH | SOL |
|---|---|---|---|---|
| exchange fee only (a floor nobody can reach) | 0.0532% | 0.0276 | 0.0859 | 0.0460 |
| **+ CFM at its own advertised 0.02% floor** | **0.0932%** | 0.0676 | 0.1259 | 0.0860 |
| + CFM at 0.05% | 0.1532% | 0.1276 | 0.1859 | 0.1460 |
| + CFM at 0.10% | 0.2532% | 0.2276 | 0.2859 | 0.2460 |

**At CFM's own advertised floor the commission is larger than the entire exchange
fee it sits on top of.** The number R478 sourced, and the better number this round
sourced, is **the smaller half of what a retail account pays**. Three rounds of
this log have been arguing about the half that doesn't decide anything.

### The corrected all-in table — and the stand-in is gone from the code

`step479_us_perp_spread_snap.py` applied **one venue's fee to both venues'
rows**, because at the time there was nothing better to use. It now carries a
venue-aware `fee_rt()`: Coinbase rows get the sourced $0.10/side, Bitnomial rows
keep R478's Kraken $0.15/side (correct — Bitnomial is the venue Kraken US's perps
list on). Re-run, exchange fee + measured median spread:

| venue | coin | fee RT | spread | ALL-IN | in stops | vs full sig | vs 2026 sig |
|---|---|---|---|---|---|---|---|
| bitnomial/krakenUS | BTC | 0.0463 | 0.0430 | 0.0893 | 0.48x | +0.0542 | −0.0506 |
| bitnomial/krakenUS | ETH | 0.0314 | 0.0529 | 0.0843 | 0.35x | +0.0592 | −0.0456 |
| bitnomial/krakenUS | SOL | 0.0811 | 0.0529 | 0.1340 | 0.39x | +0.0095 | −0.0953 |
| **coinbase_CDE** | BTC | 0.0276 | 0.0156 | **0.0432** | **0.23x** | +0.1003 | −0.0045 |
| **coinbase_CDE** | ETH | 0.0859 | 0.0267 | **0.1126** | **0.47x** | +0.0309 | −0.0739 |
| **coinbase_CDE** | SOL | 0.0460 | 0.0264 | **0.0724** | **0.21x** | +0.0711 | −0.0337 |

Coinbase is still the better venue, and on BTC and SOL it is now dramatically so
(0.21–0.23 stop distances against Bitnomial's 0.39–0.48). **On ETH the corrected
fee costs Coinbase its advantage** — 0.47x against Bitnomial's 0.35x — the exact
opposite of what R478's table said. **Coinbase's ETH contract is the wrong size
for this method** and that is a per-coin fact, not a venue verdict.

**The 2026 stub is negative on every coin on every venue, on the exchange fee
alone, before CFM's commission is added.** R479's verdict is untouched and is now
harder: adding CFM's 0.02% floor pushes BTC from −0.0045% to −0.0445%.

**Sample note, and it is an improvement, not a caveat:** the recorder R479 left
running has accumulated **9 days (12,407 samples, 2026-08-11 → 2026-08-20)**
against R480's one. The spreads above are that larger sample, which is why they
differ from R480's quoted constants. **R480's one-day ETH figure was pessimistic
by 60%** (0.0427% → 0.0267%); BTC and SOL moved by hundredths. This does **not**
answer item 8(b), which asks about the *depth* hole, not the spread.

### The trading-hours schedule, now primary-sourced (R480's addendum)

Source: `docs.cdp.coinbase.com/derivatives/introduction/market-hours`.

- **24x7 participants:** open Sunday 17:00 CT → Friday 16:00 CT, continuous.
- **Weekly halt, ALL markets closed: Friday 16:00–16:50 CT.** Pre-open 16:50,
  no-cancel window 16:59:30, reopen 17:00 CT. R480 had this secondary. **Confirmed.**
- **Non-24x7 participants: a one-hour break EVERY DAY, 16:00–17:00 CT.** This is
  **R480's measured hole, exactly**, and the mechanism is confirmed in the
  primary source: the market stays open, a class of participant goes home.
- **Quarterly maintenance:** a 3–4 hour weekend window, announced in advance.

**A DST trap nobody had noticed:** the hole is fixed in **Chicago** time, so it
**moves by an hour in UTC twice a year** — 21:00–22:00 UTC under CDT,
**22:00–23:00 UTC under CST**. R480 measured it in August and recorded it as a
UTC fact. **Any rule written against "21:00 UTC" will be an hour wrong for four
months a year**, and item 8(a)'s census must bucket in CT, not UTC.

### Two more things found on the same page-read, neither asked for

**(a) Funding on CDE settles HOURLY, not 8-hourly.** `funding_interval` is
`3600s` on all three perps; live rates 0.0015%/h BTC, 0.0014%/h ETH, 0.0018%/h
SOL (0.034–0.043% a day). **R481 modelled Bybit's 8-hourly cadence and a
once-daily US mark, and reported that 68.4% of entries straddle no settlement at
all. On an hourly clock that statistic is false for this venue** — a 43-minute
median hold straddles roughly one, and the 9.7% that run the 24h cap straddle
twenty-four. **R481's conclusion survives, for the reason R481 itself gave:** the
book is 49.6% long / 50.4% short, so charge and credit cancel whatever the
cadence — **the cadence changes the variance, not the mean.** But R481's straddle
census is a Bybit fact wearing a Coinbase label, and it is corrected here.
R481's standing warning is now sharper: **any variant that leans one way pays
this hourly, not three times a day.**

**(b) The 10x cap is an INTRADAY cap, and this is the finding with teeth.**

| coin | intraday margin | = leverage | overnight margin | = leverage |
|---|---|---|---|---|
| BTC | 10.00% | 10.00x | 24.56% | **4.07x** |
| ETH | 10.01% | 9.99x | 24.52% | **4.08x** |
| SOL | 20.00% | **5.00x** | 36.60% | **2.73x** |

R478 established that the method needs **2.9x SOL / 4.2x ETH / 5.4x BTC** at 1%
risked, off its own structural stops, and called that *"comfortably inside the
10x US ceiling."* **It is not inside the OVERNIGHT ceiling. BTC needs 5.4x and
gets 4.07x. ETH needs 4.2x and gets 4.08x.** Both are **below** requirement, and
SOL is capped at 5x even intraday.

This bites **exactly the 9.7% of positions that run the 24-hour cap** — which is,
per R481, the tail that produces **the entire +0.1309% gross, at +4.13% each**.
**The margin schedule is hostile to the only positions that make the money.** Not
a verdict, and not a backtest: a constraint nobody in this log had written down,
on the record now, and it belongs in front of item 9.

### Honest limits

1. **CFM's retail commission is UNSOURCED and it is the larger component.** Every
   net figure in this round is an **exchange-fee-only floor** — optimistic by
   construction, by at least 0.04% of price a round trip. Getting the real number
   appears to require an account, which this desk does not have and did not open.
2. Live prices are one snapshot (BTC $712 notional, ETH $226, SOL $431). Notional
   moves with price, so the fee-as-a-percentage moves inversely with it. **A 30%
   drawdown in ETH makes the ETH fee 30% more expensive in percentage terms.**
3. The fee schedule is the one effective 2025-12-15. Nothing here monitors it for
   change; a later submission would supersede it.
4. Margin rates are read live and are the exchange's; **an FCM may require more
   than the exchange does, never less.** 4.07x overnight is a ceiling, not a promise.
5. This round measures COST and VENUE MECHANICS. **It says nothing about decay,
   which R481 established is the entire remaining objection.**

### Verdict

**QUEUE ITEM 7 IS CLOSED.** The fee is $0.10 per contract per side, electronic,
standing, effective 2025-12-15, primary-sourced and independently corroborated.
The promotional component asked about does not exist. The trading-hours schedule
is primary-sourced and confirms R480's mechanism exactly.

**And the item's premise is retired with it: the exchange fee is not the number
the decision rests on.** The retail path bills a percentage through CFM, that
percentage exceeds the whole exchange fee at its own advertised floor, and it
cannot be read without an account. **The cost side of this argument, which R481
declared finished, has one component left and it is the biggest one.**

**NOTHING PROPOSED FOR DEPLOYMENT. NOTHING DEPLOYED. NO LOOK CONSUMED. NO ORDER
PLACED. NO ACCOUNT OPENED.**

---

## ROUND 483 — the break is real, recurs daily, and the method walks straight through the middle of it at exactly the rate of chance (2026-08-25)

**Queue item 8, verbatim, with R481's premise correction and R482's DST fix.
`step483_hole_exposure.py`. Research only. No orders, no live file, no account,
no re-recording, NO LOOK CONSUMED and none could be** — part (a) reads
timestamps off a population R476 has already fully described, part (b) reads a
recorder's own log, part (c) charges a cost onto a published aggregate. No cell
qualified, no partition proposed, no slice opened.

### The question

R480 measured a documented, daily, one-hour window in which Coinbase's book is
5-11% of normal depth, and concluded that **because the method holds 24 hours,
every position spans it** — putting the exitable-at-all-times account ceiling at
$17k-$26k. R481 refuted the premise (median hold **43 minutes**, 90.3% stopped
out). The item asked for the exposure to be **counted, not assumed**, and for
R480's ceiling to be **re-derived, not quoted**.

### (a) Where on the Chicago clock does this method actually trade?

68,992 entries, 2021-01-01 → 2026-07-24, bucketed in **CT** (R482: the break is
fixed in Chicago time, so a UTC census smears it across two hours).

| | count | share | flat clock | z |
|---|---|---|---|---|
| **exits landing in the break** | 2,877 | **4.170%** | 4.167% | **+0.04** |
| entries landing in the break | 2,883 | 4.179% | 4.167% | +0.16 |
| **positions straddling a break** | 13,385 | **19.401%** | — | *(R480 assumed 100%)* |
| touching the break at all | 15,943 | 23.108% | — | — |
| exits inside the **Friday all-markets halt** | 312 | 0.452% | 0.496% | −1.64 |

**The exit share is the flat-clock rate to three decimal places.** That is not a
weak result dressed up — it is a strong one, because **the CT clock is violently
lumpy everywhere else.** Hours 07-09 CT run 5.7-6.1% of exits (z = +19.9, +25.9,
+19.7); hours 21-23 CT run 2.8-3.2% (z = −12.6, −15.5, −18.2). Against a clock
with ±26 sigma structure in it, **the break hour reads +0.04 and ranks 12th of
24.** The method has no opinion about 16:00 CT whatsoever.

It holds everywhere it was checked and nothing moves: by exit reason (stops
4.151%, z −0.20; cap-runners 4.350%, z +0.75), by coin (BTC 4.178%, ETH 4.147%,
SOL 4.191%), and by year in all six (4.021% to 4.311%, every z inside ±0.8).

**The hole exits are ordinary trades.** Mean gross in the hole **+0.1333%** of
price against **+0.1308%** outside — difference +0.0024%, **t = +0.07**. Stop
distance, net, and the cap-runner share all read the same both sides. There is
no version of this where the money is concentrated in the window.

**R480's premise was wrong by a factor of five and the correction runs in the
desk's favour.** Not 100% of positions span a break — **19.4%** do.

**Two things that did NOT come back clean, and they belong together:**

1. **312 exits over 5.5 years land inside the Friday 16:00-16:50 CT all-markets
   halt** (R482, primary-sourced). ~57 a year. That is not a thin book, it is a
   **closed** one: those stops cannot fire at all and the position carries to the
   reopen. Small, real, and a different kind of problem from a spread surcharge.
2. **The 9.7% tail straddles a break essentially always: 6,711 of 6,712 =
   99.985%.** They run the 24-hour cap, so of course they do. And that tail
   carries the entire gross — at **+4.13% each**, it is **307% of the
   population's total gross**, i.e. the stopped 90.3% are collectively negative
   and the cap-runners are the whole number. **R482's constraint and this one
   now point at the same trades**: the positions that make all the money are the
   ones the venue will not finance overnight (4.07x BTC / 4.08x ETH / 2.73x SOL
   against a 5.4x / 4.2x / 2.9x requirement) **and** the ones that sit through
   the empty hour every single time.

### (b) The hole recurs. R480's one-day number was right.

18,451 samples, **13 calendar days** (2026-08-11 → 2026-08-25) against R480's
one. Recorder untouched; this is whatever accumulated on its own.

Median 5-level notional in the break hour as a share of the other 23 hours:

| venue | BTC | ETH | SOL |
|---|---|---|---|
| **Coinbase CDE** | **11.0%** | **5.7%** | **13.2%** |
| Bitnomial | 110.9% | 105.5% | 106.6% |
| Kraken INTL *(offshore control)* | 94.6% | 111.7% | 69.3% |

**R480 read "5-11% on all three coins at once" off a single Tuesday. On thirteen
days it reads 5.7-13.2%.** The magnitude is now measured, not indicative. Day by
day, Coinbase is under 25% of normal depth on **8/11 (BTC), 9/11 (ETH), 8/11
(SOL)** days with coverage — and **all three exception days are weekend days**
(08-16 Sun, 08-22 Sat, 08-23 Sun), where the other 23 hours are already thin so
the ratio rises without the break-hour book improving. **Weekday-only: 10.4% BTC
/ 5.4% ETH / 12.8% SOL.** Bitnomial still has no such hole, and neither does the
offshore control — this is a Coinbase-specific, weekday, mechanism-explained
event, exactly as R482's CFTC sourcing says it should be.

The spread widens with it, and only on Coinbase: **2.01x BTC, 1.32x ETH, 1.99x
SOL** (0.0154% → 0.0310%, 0.0397% → 0.0525%, 0.0264% → 0.0527%). Bitnomial 0.89-
1.08x, Kraken 0.99-1.00x.

### (c) Priced

Charge the exit leg the break-hour half-spread instead of the normal one, on the
4.170% of exits that land there. Median structural stop 0.237% of price.

| venue | coin | extra per leg | × share = per entry | in stop distances |
|---|---|---|---|---|
| Coinbase | BTC | 0.0078% | **0.00032%** | 0.0014 |
| Coinbase | ETH | 0.0064% | **0.00027%** | 0.0011 |
| Coinbase | SOL | 0.0131% | **0.00055%** | 0.0023 |

**Three to six ten-thousandths of a percent of price per entry, one to two
thousandths of a stop distance.** Against a whole-window gross of +0.1309% and a
2026 stub of +0.0360%, the break costs **about 1.5% of what is left of the
signal.** It is a rounding error and it is now measured rather than feared.

### R480's account ceiling, re-derived

R480's **$17k-$26k is a property of the BOOK** — the equity whose stop can cross
the break-hour book without walking it — and it does not move, because the book
does not care why you are there. What the census changes is the **obligation**.
R480 said every position spans the hole, which made exitable-at-all-times the
only ceiling. On the measured clock:

- **95.83% of exits meet the normal book** (R479's ~$300k)
- **4.17% meet the thin one** ($17k-$26k)

An account sized above the thin-book ceiling is not broken; it pays a worse fill
on that share, and that fill is the surcharge above. **R480's sentence stays true
as a book fact and stops being the binding constraint on account size for this
method.** The binding constraint on this venue is back to being R482's overnight
margin schedule, and behind it, decay.

### Honest limits

1. The exit timestamps are the **backtest's** exits on Alpaca's 1-minute tape —
   when the stop or cap *would* fire, not fills observed on a US venue. Right
   object for "which hour does the method ask to trade in", not a fill study.
2. **13 days is 13 days.** The mechanism is primary-sourced (R482, CFTC
   submission #2025-75) and the magnitude is now measured across two weeks. It is
   not a year, and nothing here reads seasonality.
3. R481's gap finding stands: Alpaca's tape has gaps and the 24h cap is counted
   in bars, so 8.0% of holds span more than 24h of wall clock. The straddle count
   here is computed on **wall clock**, so those holds correctly straddle more
   breaks — which is why the cap-runner straddle rate is 99.985% and not lower.
4. The surcharge assumes the break-hour **spread** is what a stop pays. At 5-13%
   of normal depth a large order also **walks the book**, which the median spread
   does not capture. The number above is a floor for a small account and
   understates it for one near the ceiling.
5. Every cost figure here is an **exchange-fee-only** world (R482 item 10): CFM's
   percentage commission is still unsourced and is larger than everything in this
   round put together.

### Verdict

**QUEUE ITEM 8 IS CLOSED, both legs.**

(a) **The exposure is chance and nothing else.** 4.170% of exits against a
4.167% flat clock, z = +0.04, on a clock that is ±26 sigma lumpy elsewhere.
Stable across every reason, coin and year. The hole exits are worth the same as
the rest (t = +0.07). **R480's "every position spans it" was wrong by 5x — the
real straddle rate is 19.4%.**

(b) **The hole is real and daily.** 13 days confirm R480's one: 5.4-12.8% of
normal weekday depth on Coinbase, none on Bitnomial, none offshore.

(c) **Priced, it is 0.0003-0.0006% of price per entry** — 1.5% of the 2026 stub
of the signal. **The break is not a reason this method fails.**

**What this round removes from the argument:** an account-size ceiling that was
never binding, built on a hold assumption R481 had already refuted.

**What it adds:** 57 exits a year into a closed Friday market, and a second,
independent constraint landing on the same 9.7% of trades that R482's margin
schedule already hits and that carry 100% of the gross. **Decay (item 9) is
still the whole argument, and item 10's unsourced FCM commission is still the
larger cost.**

**NOTHING PROPOSED FOR DEPLOYMENT. NOTHING DEPLOYED. NO LOOK CONSUMED. NO ORDER
PLACED. NO ACCOUNT OPENED. NO RECORDING RESTARTED.**

## ROUND 485 — the decay is real in price terms, is not a decay in the edge, and does not exist on the index at all (2026-08-26)

**QUEUE ITEM 9.** Research only. No orders. No live file touched. No account.
**NO LOOK CONSUMED, and none could be** — parts (a) and (b) decompose a mean the
desk has already published (R476, whole window, no sealed slice left anywhere on
this family) into arithmetic parts; part (c) rebuilds R474's index population
with R474's own code and reads it by calendar year. Nothing qualified. Nothing
proposed. `step485_decay_anatomy.py`, full console output in
`step485_output.txt`, index population persisted to `step485_index_entries.csv`.

### The question

Every "not deployable" verdict since R478 rests on one number: R476's gross fell
from +0.2908% of price (2021) to +0.0387% (2026), 7.5x. Cost has been driven to
a finish across three rounds and is no longer what kills this family. **Nobody
had ever interrogated the decay itself.**

### The handle, and it is exact arithmetic with no residual

In this construction a stopped entry loses **exactly** its stop (verified in
code: `np.allclose(gross, -stop)` is True on all 62,280 stopped rows). So with
p = the share running the 24h cap, W = their mean gross, L = the mean stop of
the stopped:

    mean gross%  =  p*W − (1−p)*L
    mean R       =  p*W_R − (1−p)        (a stop is −1.000R, always)

That turns "why did the gross fall" into three numbers and no residual, and the
three are exactly the queue's own candidates: how many, how often they win, how
big the winners are.

### (a) THE DECAY IS THE PRICE SCALE. IT IS NOT THE EDGE, AND IT IS NOT THE TAIL

| year | n | n/day | p_win% | W% | L% | gross% | stop med% | W_R | mean R | t/day |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 11,893 | 32.6 | 10.33 | 5.659 | 0.380 | 0.2437 | 0.307 | 15.12 | 0.664 | 9.29 |
| 2022 | 13,956 | 38.2 | 10.05 | 4.645 | 0.319 | 0.1800 | 0.246 | 17.06 | 0.814 | 8.12 |
| 2023 | 11,314 | 31.0 | 9.50 | 2.642 | 0.236 | 0.0371 | 0.159 | 12.88 | 0.319 | 1.87 |
| 2024 | 10,863 | 29.7 | 10.02 | 3.710 | 0.267 | 0.1320 | 0.230 | 14.99 | 0.603 | 5.58 |
| 2025 | 13,609 | 37.3 | 9.37 | 4.084 | 0.300 | 0.1106 | 0.256 | 15.77 | 0.572 | 6.10 |
| 2026 | 7,357 | 35.9 | 8.74 | 3.420 | 0.288 | 0.0358 | 0.224 | 17.42 | 0.610 | 1.85 |

The `check` column reproduces every gross to four decimals from p, W and L.

**Shift-share, 2021 → 2026, total fall −0.2079% of price, residual 0.0000:**

- **the WINNERS' SIZE, W 5.659% → 3.420%: −0.2134 (103% of the fall)**
- the WIN RATE, p 10.33% → 8.74%: −0.0773 (37%)
- the LOSERS' SIZE, L 0.380% → 0.288%: **+0.0828 (−40%, it gives back)**
- entry count is not in the identity at all, and it went **UP**: 32.6 → 35.9 a
  day, +10.1%.

**And now the same years with the price scale divided out** (ratio to 2021):

| year | gross% | ×2021 | mean R | ×2021 | stop med% | ×2021 |
|---|---|---|---|---|---|---|
| 2021 | 0.2437 | 1.00 | 0.664 | 1.00 | 0.307 | 1.00 |
| 2022 | 0.1800 | 0.74 | 0.814 | 1.23 | 0.246 | 0.80 |
| 2023 | 0.0371 | **0.15** | 0.319 | 0.48 | 0.159 | 0.52 |
| 2024 | 0.1320 | 0.54 | 0.603 | 0.91 | 0.230 | 0.75 |
| 2025 | 0.1106 | 0.45 | 0.572 | 0.86 | 0.256 | 0.83 |
| 2026 | 0.0358 | **0.15** | 0.610 | **0.92** | 0.224 | 0.73 |

**In % of price the method is at 0.15 of its 2021 self. In risk multiples it is
at 0.92.** The daily-series trend confirms it and the three tests separate
cleanly:

- gross% of price: **−0.038 per year, t = −6.05** — DECAYING
- stop median%: **−0.022 per year, t = −7.87** — DECAYING
- risk multiple R: −0.047 per year, **t = −1.15 — FLAT**

**R482's feared scenario does not happen.** It warned that if the decay were the
9.7% cap-runner tail thinning, the venue's overnight margin schedule and the
decay would land on the same trades and the family would be finished on two
independent grounds. The tail did not thin: p fell 15.4% (10.33% → 8.74%) and
**per unit of risk the winners got BIGGER, 15.12R → 17.42R**, the two almost
exactly cancelling in `mean R = p*W_R − (1−p)`. The winners are smaller in % of
price **because their stops are smaller**: mean stop of a cap-runner 0.641% →
0.461%.

All three coins agree in direction. BTC is the weakest — 2026 gross **−0.0079%**,
mean R 0.146 — ETH holds at +0.0805% / 0.484R, SOL at +0.0358% / 1.227R.

### (b) IT IS NOT MONOTONE, AND 2026 IS NOT A STUB ARTIFACT

Every year cut to 2026's own calendar window (Jan 1 → Jul 26), so stubs are
compared to stubs:

| year (Jan 1 → Jul 26) | n | p_win% | W% | gross% | mean R | stop med% | t/day |
|---|---|---|---|---|---|---|---|
| 2021 | 5,567 | 10.53 | 6.396 | 0.2989 | 0.768 | 0.338 | 7.19 |
| 2022 | 7,904 | 9.68 | 5.139 | 0.1847 | 0.939 | 0.274 | 6.10 |
| 2023 | 7,387 | 9.65 | 3.135 | **0.0513** | 0.394 | 0.181 | 1.71 |
| 2024 | 5,190 | 10.42 | 3.530 | 0.1496 | 0.661 | 0.210 | 4.77 |
| 2025 | 7,761 | 9.37 | 4.362 | 0.1251 | 0.721 | 0.267 | 4.89 |
| 2026 | 7,357 | 8.74 | 3.420 | **0.0358** | 0.610 | 0.224 | 1.85 |

**2026's low reading survives the stub correction** — it is not an artifact of a
short year. But **the series is not monotone**: 2023 was already at 0.051% on
the same calendar cut, and the very next year recovered to 0.150%. 2026 looks
like 2023, and 2023 was followed by a recovery. Quarterly, 2026 reads +0.004% /
+0.063% / +0.053% against 2023's +0.144% / −0.039% / +0.009%.

Spearman on the six year means: rho −0.829, p 0.042 for gross%; **rho −0.429,
p 0.397 for mean R**. Six points is six points and this is weak by construction,
stated so nobody quotes it as a trend test.

### (c) THE INDEX DOES NOT DECAY — AND ITS GROSS TRACKS ITS OWN VOLATILITY AT r = +0.92

R474's population rebuilt with R474's own functions: 23,318 entries, 1-minute
trigger, hold to close, eight levels pooled, SPY + QQQ, 2016-2026.

| year | n | gross% | mean R | stop med% | t/day |
|---|---|---|---|---|---|
| 2016 | 2,314 | 0.0626 | 0.570 | 0.082 | 4.07 |
| 2017 | 2,242 | 0.0427 | 0.600 | 0.055 | 5.06 |
| 2018 | 2,462 | 0.0984 | 0.802 | 0.107 | 4.73 |
| 2019 | 2,061 | 0.0723 | 0.841 | 0.079 | 4.95 |
| 2020 | 2,192 | 0.1187 | 0.636 | 0.137 | 4.00 |
| 2021 | 2,096 | 0.0707 | 0.629 | 0.082 | 4.56 |
| 2022 | 2,209 | 0.1029 | 0.607 | 0.166 | 4.02 |
| 2023 | 2,322 | 0.0781 | 0.673 | 0.096 | 4.40 |
| 2024 | 2,249 | 0.0703 | 0.883 | 0.084 | 3.75 |
| 2025 | 2,064 | 0.0714 | 0.561 | 0.100 | 4.04 |
| 2026 | 1,107 | 0.0542 | 0.526 | 0.106 | 2.64 |

Over the crypto window the index goes 1.00 / 1.46 / 1.11 / 0.99 / 1.01 / **0.77**
against crypto's 1.00 / 0.74 / 0.15 / 0.54 / 0.45 / **0.15**. **The index has no
7.5x decay and no decay at all outside 2026's partial year.**

**Realized 1-minute volatility, mean |1-minute return| as % of price:**

| year | BTC | ETH | SOL | SPY | QQQ |
|---|---|---|---|---|---|
| 2021 | 0.0825 | 0.1053 | 0.1844 | 0.0177 | 0.0242 |
| 2022 | 0.0563 | 0.0787 | 0.1213 | 0.0314 | 0.0406 |
| 2023 | 0.0384 | 0.0421 | 0.0969 | 0.0193 | 0.0254 |
| 2024 | 0.0598 | 0.0709 | 0.0949 | 0.0169 | 0.0229 |
| 2025 | 0.0522 | 0.0804 | 0.0906 | 0.0209 | 0.0255 |
| 2026 | 0.0445 | 0.0717 | 0.0764 | 0.0190 | 0.0262 |

**Crypto's 1-minute volatility fell to 0.52 of its 2021 level. SPY's did not
fall at all (0.0177 → 0.0190).** The instrument that did not compress is the
instrument whose method did not decay.

**And the gross is a near-linear function of that scale on both asset classes:**

- **INDEX, gross% vs SPY 1-minute vol, 11 years: r = +0.915 (p 0.000),
  rho = +0.755 (p 0.007)**
- **CRYPTO, gross% vs 3-coin 1-minute vol, 6 years: r = +0.933 (p 0.007),
  rho = +0.943 (p 0.005)**

Eleven points and six points respectively — a description, not a test. But it is
the same description on two asset classes, ten years apart, and it answers the
queue's own either/or: **this is a volatility story, not a crowding story.**

### THE CORRECTION THIS ROUND FORCES, AND IT IS THE MOST CONSEQUENTIAL THING IN IT

R481 closed the cost side by reporting that the 5.5-year window clears the whole
Coinbase stack with **"+0.196 stop distances left over."** That number is a
**ratio of means** — mean net % of price divided by the *median* stop. A book
sized off each trade's **own** stop does not earn it.

    ratio of means   0.0545 / 0.2366  =  +0.230
    mean per trade   mean( net% / that trade's own stop% )  =  −0.346
                     t clustered by UTC day = −3.18  (2,031 days)

**The two statistics of the same population disagree in sign, and the per-trade
one is significantly negative.** Per-trade net R is negative in **all six
years** — 2021 −0.394, 2022 −0.039, 2023 −0.675, 2024 −0.471, 2025 −0.343,
**2026 −0.161, the second-best year of the six.**

The reason is the shape of the stop distribution, not the decay: `1/stop` has a
heavy right tail (stop deciles p10 0.065%, p25 0.128%, p50 0.237%, p75 0.395%,
p90 0.611%), and **12.14% of all entries have a stop tighter than the entire
round trip.** A fixed percentage cost against a stop that can be a twentieth of
a percent is not a rounding error; it is the trade.

Stated and not acted on: **no filter is proposed and none may be.** A minimum-
stop threshold is a swept parameter and this family has no sealed slice left
anywhere to test one on.

**The same check on the index**, whole 2016-2026 population: ratio of means
+0.402, **mean per trade −0.024, t by day −1.23**, with **14.53%** of entries
carrying a stop tighter than the 0.04% round trip. This corroborates rather than
contradicts R474, which already recorded that the arm as a whole has negative
net R; what is new is the mechanism.

### Honest limits

1. The crypto population is step481's 68,992 funding-covered entries, not
   R476's 71,073. Five of six years match R476's gross to four decimals; **2021
   does not** (0.2437 here against R476's 0.2908) because only 85.6% of 2021's
   entries have funding coverage. Where 2021 anchors a ratio in this round, it
   anchors it at the more conservative number — the decay measured here (0.15x)
   is therefore *smaller* than R476's headline (0.13x), not larger.
2. Realized volatility is the mean absolute 1-minute return. It is a scale, not
   a volatility model, and it is measured on Alpaca's tape with R481's known
   gaps.
3. Six years and eleven years are small samples for a correlation. Both r values
   are reported with their Spearman companions and neither is offered as a test.
4. The index population is pooled over eight levels un-deduped, exactly as the
   crypto one is (pooled gross +0.0778% vs deduped +0.0611% — the dedupe moves
   the level, not the year profile). Its 2026 is 134 days.
5. Every cost figure remains **exchange-fee-only** on the crypto side (queue
   item 10): CFM's percentage commission is still unsourced and is larger than
   the entire per-year cost charged above.

### Verdict

**QUEUE ITEM 9 IS CLOSED. The decay is real in price terms, is not a decay in
the edge, and is not the tail.**

(a) **103% of the fall is the winners getting smaller in % of price, and they
got smaller because their stops did.** Per unit of risk the winners got *bigger*
(15.12R → 17.42R), the win rate fell 15%, and the two cancel: **mean R is
0.664 → 0.610, daily trend t = −1.15, flat.** Entry count rose 10%.

(b) **Not monotone.** 2023 sat at the same level on a matched calendar cut and
2024 recovered to 2.9x it. 2026's low is real, not a stub artifact, and it is
the second-*best* of the six years in per-trade net R.

(c) **The index does not decay, and the gross of this method is a near-linear
function of realized volatility on both asset classes (r = +0.92 / +0.93).**
Crypto's 1-minute volatility halved; SPY's did not move. **Volatility story.
Not crowding.**

**What this removes from the argument:** "the signal decayed 7.5x" as a reason
this family is not deployable. In the units a risk-sized book actually earns,
it did not decay at all. R482's two-independent-grounds scenario is refuted.

**What it adds, and it is worse:** the family's net problem was never the decay
and is not fixed by a better year. **Per-trade net R is −0.346 (t = −3.18) and
negative in every one of the six years**, because 12% of entries carry a stop
tighter than the round trip. The desk has been quoting a ratio-of-means that
flatters this population by a full sign.

**NOTHING PROPOSED FOR DEPLOYMENT. NOTHING DEPLOYED. NO LOOK CONSUMED. NO ORDER
PLACED. NO ACCOUNT OPENED.**

## ROUND 486 — the account's fee is INCLUSIVE of the exchange's, not on top of it, and the thing that actually bites is a fifteen-cent minimum (2026-08-27)

**QUEUE ITEM 10.** Research only. No orders. No account opened. No live file
touched, imported or modified. **NO LOOK CONSUMED, and none could be** — Section 4
solves an equation on the mean of a population the desk has already fully
published (step481's 68,992 funding-covered entries; no sealed slice left
anywhere on this family). No partition proposed, no parameter swept, no cell
qualified. `step486_cfm_commission.py`, full console output in
`step486_output.txt`, table persisted to `step486_cfm_breakeven.json`.

### The question

R481 declared the cost side finished; R482 reopened it. The exchange fee is the
smaller half: **Coinbase Financial Markets (CFM), the FCM a US person actually
faces, bills a percentage of notional on top of CDE's $0.10/side**, published
only as a marketing floor ("as low as 0.02%"). At that floor alone the
commission exceeds the whole exchange fee it sits on. Every "net" number in this
log was therefore an exchange-fee-only floor, **optimistic by at least 0.04% of
price a round trip** — larger than the 2026 stub of the signal. Deliverable:
(a) source the schedule from a non-Coinbase channel; failing that, (b) state the
**break-even commission** so the unsourced number has a bar to clear.

### (a) THE PREMISE IN THE SENTENCE ABOVE IS FALSE, AND THAT IS THE ROUND'S FIRST OUTPUT

`www.coinbase.com` and `help.coinbase.com` still 403 every unauthenticated
request (R482's finding, re-confirmed). The page was read instead from the
**Internet Archive**, snapshot `20251117042013` of Coinbase's own launch
announcement *"Perpetual futures have arrived in the U.S."* (published
2025-07-21). Verbatim, body and footnote:

> "Low trading fees: We're making derivatives trading more accessible with fees
> as low as 0.02%\* per contract."
>
> "\*Trading fees are inclusive of exchange, clearing, and NFA fees. A minimum of
> $0.15 is charged per contract to cover these fixed costs."

**The commission is not additive. It is INCLUSIVE**, and it carries a
**per-contract MINIMUM the item never knew existed.** What the account pays is

    per side  =  max( rate × notional , $0.15 )

with CDE's sourced $0.10/side living **inside** it. Where the minimum binds,
**CFM's own take over the exchange fee it collects is exactly five cents a
side** — the number item 10 was trying to bound is a nickel, not a percentage.

Base case is **per side**, on three grounds stated in the file: the exchange fee
this figure is inclusive of is explicitly per side (CFTC submission #2025-75,
R482); Coinbase's US futures documentation describes the older CFM futures fee as
"per contract, per side"; and it is the conservative reading. **If it is per
round turn instead, every fee number in this round halves** — stated, not buried.

**Still UNSOURCED and given no invented value: the standing volume-tier ladder
above the 0.02% floor.** Channels tried and what each gave, in full:

| channel | result |
|---|---|
| Coinbase blog, via Internet Archive | **HIT** — floor rate, the $0.15 minimum, the inclusive footnote |
| **CFTC Rule 1.55(k) FCM Specific Disclosure**, CFM, dated 2026-05-21, 12pp | fetched and text-extracted in full: **NO FEE SCHEDULE.** The only "charged" in the document is interest on account balances |
| NFA BASIC record for CFM | registration and disciplinary record only; BASIC does not publish fees |
| Lincoln Park Financial, BIP contract page | publishes the **exchange** fee ($.10/contract, independently corroborating R482 a second time) and margins; no FCM commission |
| Tradovate, CDE nano page | "Exchange, clearing and NFA fees still apply" — a **different FCM's structure, additive not inclusive**; own commission not published |
| docs.cdp.coinbase.com, US futures | "the same fee structure [as Advanced Trade]. During the introductory beta period, we are only charging **0.05%** (the lowest Advanced Trade tier)" — the older CFM futures, and the only published CFM percentage **above** the floor |
| docs.cdp.coinbase.com, perpetuals | "0.00% maker and 0.03% taker" **plus a "10 USDC min notional"** — the INTERNATIONAL book. Independently re-confirms R482's strike of that figure from the US table |

**Deliverable (a) is PARTIALLY met, and the item's own fallback clause is now
answered: the full schedule is not knowable before signing up.** The FCM's
mandatory public regulatory disclosure does not carry a rate card, and no
third-party channel publishes CFM's commission.

### The item's own bound, tested at live notional (BTC $80,130 / ETH $2,507.50 / SOL $108.74)

Contract sizes read live off the public product endpoint: **0.01 BTC / 0.1 ETH /
5 SOL** → notionals **$801 / $251 / $544**.

| coin | 0.02% × N | what binds | $/side | fee RT % | exchange-only RT % | **CFM increment** | item said ≥0.04% |
|---|---|---|---|---|---|---|---|
| BTC | $0.160 | the **rate** | $0.160 | 0.0400 | 0.0250 | **+0.0150** | overstated |
| ETH | $0.050 | the **MINIMUM** | $0.150 | 0.1196 | 0.0798 | **+0.0399** | right on this coin |
| SOL | $0.109 | the **MINIMUM** | $0.150 | 0.0552 | 0.0368 | **+0.0184** | overstated |

**On two coins of three the minimum binds, and there the 0.02% floor rate is
irrelevant — the account pays $0.15 whatever the rate says, and would pay $0.15
at a rate of zero.** The item's "optimistic by at least 0.04%" is **overstated
by 2-3x on BTC and SOL and correct on ETH**.

All-in, keeping this log's spread term exactly as published (R482's 9-day
sample) and changing only the fee: **BTC 0.0556%, ETH 0.1463%, SOL 0.0816%**
against R482's 0.0432 / 0.1126 / 0.0724. Part of each delta is the coin being
cheaper today than on R482's day, not the fee changing — a fixed-dollar minimum
is a percentage that **moves with the price of the coin**, and no round in this
log had treated cost that way before.

### (b) THE BREAK-EVEN COMMISSION — and it is two different answers, per R485

    MEAN NET %      c* = mean(gross)                        ← the log's headline statistic
    PER-TRADE R     c* = mean(gross/stop) / mean(1/stop)    ← what a risk-sized book earns

| window | n | gross % | t by day | **BE, mean-net** | **BE, per-trade R** |
|---|---|---|---|---|---|
| FULL | 68,992 | +0.1309 | 14.14 | **0.1309%** | **0.0448%** |
| 2021 | 11,893 | +0.2437 | 9.29 | 0.2437 | 0.0353 |
| 2022 | 13,956 | +0.1800 | 8.12 | 0.1800 | 0.0662 |
| 2023 | 11,314 | +0.0371 | 1.87 | 0.0371 | 0.0241 |
| 2024 | 10,863 | +0.1320 | 5.58 | 0.1320 | 0.0443 |
| 2025 | 13,609 | +0.1106 | 6.10 | 0.1106 | 0.0486 |
| **2026** | 7,357 | +0.0358 | 1.85 | **0.0358** | **0.0581** |

**Read the 2026 row before any other. On the per-trade statistic the 2026 stub's
break-even is HIGHER than the full window's — 0.0581% against 0.0448%.** 2026 can
afford *more* cost per trade than the average year of this method, not less. That
is R485's "2026 is the second-best of the six years in per-trade net R" arriving
from the opposite direction, and it means **"the 2026 stub cannot pay for
itself" is a fact about the mean-net statistic only.** Anywhere this log uses
that sentence, it needs the qualifier.

**Per coin — the bar the unsourced tier ladder has to clear.** Subtract the
spread from the break-even to get the fee budget; halve it for one side; price
that side against the sourced $0.15 minimum. **If the budget is under $0.15, no
commission rate clears — not even zero.**

**On MEAN NET %:**

| coin | BE all-in | spread | fee budget | $/side max | vs $0.15 | **max rate/side** | price needed |
|---|---|---|---|---|---|---|---|
| BTC | 0.0865% | 0.0156 | 0.0709% | $0.284 | CLEARS | **0.0355%** | $42,309 |
| ETH | 0.1540% | 0.0267 | 0.1273% | $0.160 | CLEARS | **0.0637%** | $2,357 |
| SOL | 0.1608% | 0.0264 | 0.1344% | $0.365 | CLEARS | **0.0672%** | $45 |

**On PER-TRADE NET R:**

| coin | BE all-in | spread | fee budget | $/side max | vs $0.15 | max rate/side | price needed |
|---|---|---|---|---|---|---|---|
| BTC | 0.0275% | 0.0156 | 0.0119% | $0.048 | **FAILS** | **none exists** | $251,590 |
| ETH | 0.0525% | 0.0267 | 0.0258% | $0.032 | **FAILS** | **none exists** | $11,621 |
| SOL | 0.0802% | 0.0264 | 0.0538% | $0.146 | **FAILS** | **none exists** | $112 |

**THIS IS THE ROUND'S REAL OUTPUT.** In the units a risk-sized book actually
earns, **the break-even commission does not exist on any of the three coins at
today's prices.** The **$0.15 minimum alone**, before a single basis point of
commission and before the exchange's own $0.10 is even considered separately,
exceeds the whole per-trade fee budget. A CFM rate of **zero** would not save it.

And because the minimum is a fixed dollar amount, the constraint has a price
attached, which is the most useful single number this round produces: the
minimum becomes payable at **BTC $251,590, ETH $11,621, or SOL $112.** SOL is at
$108.74 — **within 4% of the level at which its own contract can carry the
charge.** That is a fact about the SIZE of the contract relative to the size of
the signal, which is exactly the shape the owner rule says a cost finding takes.

### The one published CFM percentage above the floor, against the bar

0.05% (the lowest Advanced Trade tier, quoted for the older CFM futures) —
not the perp schedule, but the right order of magnitude for a real tier:

| coin | $/side @0.02% | $/side @0.05% | all-in @0.02% | all-in @0.05% | BE mean-net | BE per-trade R |
|---|---|---|---|---|---|---|
| BTC | $0.160 | $0.401 | 0.0556% | **0.1156%** | 0.0865% | 0.0275% |
| ETH | $0.150 | $0.150 | 0.1463% | 0.1463% | 0.1540% | 0.0525% |
| SOL | $0.150 | $0.272 | 0.0816% | **0.1264%** | 0.1608% | 0.0802% |

On the mean-net statistic the 0.02% floor tier clears on all three coins.
**At 0.05% BTC goes negative** (0.1156% against a 0.0865% break-even) and SOL
survives; **ETH is untouched by the rate change entirely, because the minimum
binds at both rates.** On the per-trade statistic nothing clears at either rate,
per the table above.

### Honest limits

1. **Every percentage here is a price snapshot** (2026-08-27, BTC $80,130). The
   fee is a fixed dollar amount over a moving notional, so all of Section 3 and
   the "$/side max" columns re-price whenever the coins do. The dollar figures
   ($0.15, $0.10, $0.05 increment) and the "price needed" thresholds are the
   stable ones; quote those, not the percentages.
2. **Per side is an inference, not a quotation.** Coinbase's footnote says "per
   contract" and does not say "per side". The three grounds for the base case are
   in the file; the alternative halves every fee figure and is stated explicitly.
3. **The tier ladder is still unsourced.** 0.02% is a floor, and the 0.05% used
   as a probe belongs to a different CFM product. Nothing above the floor is
   asserted as CFM's actual perp rate.
4. The spread term is R482's 9-day sample, carried unchanged so that only the fee
   moves. R480's full-clock medians are reported alongside as a sensitivity and
   shift the all-in by hundredths of a percent.
5. The break-evens are solved on step481's 68,992-entry population, which is
   R476's family with funding coverage — five of six years match R476's gross to
   four decimals and 2021 does not (85.6% coverage), exactly as R485 recorded.

### Verdict

**QUEUE ITEM 10 IS CLOSED. The cost side of this family is finished for the
second time, and this time the account is in the number.**

1. **The item's premise was wrong in the desk's favour on the structure and
   against it on the mechanism.** CFM's fee is inclusive of the exchange's, not
   additive, so the increment is a nickel a side rather than a percentage on top;
   but it carries a **$0.15 per-contract minimum** that binds on two of three
   coins and is invisible to every percentage-based cost model in this log.
2. **"Optimistic by at least 0.04% a round trip" is overstated by 2-3x on BTC and
   SOL and correct on ETH.** The corrected all-in is 0.0556 / 0.1463 / 0.0816%.
3. **On the mean-net statistic there is a real bar and the sourced floor clears
   it**: the method goes negative above roughly **0.036%/side on BTC, 0.064% on
   ETH, 0.067% on SOL**. The unsourced ladder now has a number to beat.
4. **On the per-trade statistic no bar exists to clear.** The $0.15 minimum alone
   exceeds the fee budget on all three coins; a zero commission still leaves it
   negative. The constraint is the **size of the contract against the size of the
   signal**, and it prices out at BTC $251,590 / ETH $11,621 / SOL $112.
5. **2026 is not the weak year on this statistic — it is the strongest of the
   six.** Its per-trade break-even, 0.0581%, is above the full window's 0.0448%.

Nothing here declines a trade, gates a strategy or ranks an instrument, and
nothing here is offered as a reason this family is or is not deployable — it has
no sealed slice left anywhere and cannot be a candidate on any evidence.

**NOTHING PROPOSED FOR DEPLOYMENT. NOTHING DEPLOYED. NO LOOK CONSUMED. NO ORDER
PLACED. NO ACCOUNT OPENED.**

## ROUND 487 — the log's risk multiples audited: every ratio-of-means figure is understated by ~3x, every per-trade figure is right, and item 0 survives the recomputation (2026-08-29)

**What was tested.** Queue item 11, exactly as written, and it is an AUDIT not
a hypothesis. R485 found the desk's headline risk-multiple statistic and the
number a risk-sized book actually earns disagree in sign on the crypto
1-minute family (+0.230 vs −0.346). This round finds every other place that
error could be hiding, classifies each claim, and restates the bad ones.

File: `step487_ratio_of_means_audit.py`, output `step487_output.txt`.

**No look consumed, and none could be.** Every number is a re-reading of a
population already fully published — the crypto 1-minute entries
(`step481_entries_funding.csv`, 68,992 rows, no sealed slice left on this
family) and R474's index population as rebuilt by R485
(`step485_index_entries.csv`, 23,318 rows). No backtest re-run, no cell
qualified, no partition proposed, no parameter swept. The one sealed number
touched is a RECOMPUTATION of a result already in the log.

### The mechanism, stated once

A book sized by risk puts `risk$ / stop_i` on, so it pays `cost / stop_i` risk
units on trade i. What it experiences is the **mean over trades of that
ratio**. `mean(net%) / median(stop%)` is a different number, because
E[X/Y] ≠ E[X]/E[Y] and `1/stop` has a heavy right tail:

| crypto book | value |
|---|---|
| median stop | 0.2366% → 1/median = **4.23** |
| **mean of 1/stop** | **13.49** |
| p90 of 1/stop | 15.47 |
| p99 of 1/stop | 88.13 |

**13.49 / 4.23 = 3.19. That ratio is the whole audit.**

### The inventory and the classification

58 lines in RESEARCH_LOG.md carry a risk-multiple claim, across 15 rounds.
They collapse to **14 distinct claim families: 5 PER-TRADE, 9
RATIO-OF-MEANS.** Each classification is evidenced by the line of code that
computes it, grepped live so the table cannot drift.

PER-TRADE (correct as published): R450/R474/R475/R476's `net R`/`gross R`
columns (`simulate()` writes `net_R` per row, `summarise()`/`mean_R` take its
mean — identical code in all three files), R475's sealed −1.98, R485's −0.346,
R486's `BE per-trade R` column (R486 self-corrected and publishes both).

RATIO-OF-MEANS (restated below): R450's 2.4, R474's 0.48, R476's 2.1, R478's
0.13–0.25, R479/R480's 0.31–0.50, R481's 0.358 and +0.196, R482's 0.21–0.47,
R483's 0.0011–0.0023, R370's 0.44/2.17.

### The restatement — crypto, 68,992 entries, 2,031 UTC days

| cost model | PUBLISHED | PER TRADE | ×under | net R rm | **net R pt** | t/day |
|---|---|---|---|---|---|---|
| Alpaca taker (R450/R475/R476) | 2.114 | **6.746** | 3.19 | −1.560 | **−6.142** | −6.40 |
| Bitnomial all-in (R480 clock) | 0.421 | **1.300** | 3.09 | +0.132 | **−0.696** | −3.81 |
| Coinbase all-in (R480 clock) | 0.331 | **0.993** | 3.00 | +0.222 | **−0.389** | −2.93 |
| Coinbase all-in (R482 fee) | 0.323 | **0.950** | 2.94 | +0.230 | **−0.346** | −3.18 |
| Coinbase all-in (R486 CFM) | 0.405 | **1.201** | 2.96 | +0.148 | **−0.597** | −4.55 |

**R481's "the whole cost stack is 0.358 stop distances" is really 0.95–1.20 —
the cost stack is ONE ENTIRE STOP, not a third of one.** And **84.17% of
entries carry a stop tighter than one Alpaca round trip**; 16.65% carry one
tighter than the R486 Coinbase all-in (R485's 12.14% was measured against the
R482 cost model).

R483's break-hour surcharge: published 0.0015 stop distances, per trade
**0.0047** (3.04x). Still a rounding error — but understated like every
other one, which is the point.

By year, R486 Coinbase all-in — **per-trade net R is negative in all six**
(rm positive in four of six):

| year | n | gross% | net% | stop med% | net R rm | **net R pt** | t/day |
|---|---|---|---|---|---|---|---|
| 2021 | 11,893 | +0.2437 | +0.1476 | 0.3066 | +0.481 | **−0.683** | −1.46 |
| 2022 | 13,956 | +0.1800 | +0.0861 | 0.2460 | +0.350 | **−0.247** | −1.04 |
| 2023 | 11,314 | +0.0371 | −0.0602 | 0.1589 | −0.379 | **−0.946** | −8.08 |
| 2024 | 10,863 | +0.1320 | +0.0336 | 0.2298 | +0.146 | **−0.777** | −2.78 |
| 2025 | 13,609 | +0.1106 | +0.0156 | 0.2560 | +0.061 | **−0.577** | −3.01 |
| 2026 | 7,357 | +0.0358 | −0.0585 | 0.2240 | −0.261 | **−0.351** | −0.81 |

By coin the damage is not evenly spread: **ETH −1.092 (t −5.80), BTC −0.520
(t −2.08), SOL −0.013 (t +0.19).** SOL is the only coin whose per-trade net R
is not distinguishable from zero, and it is the coin whose contract R486
showed is about to become unaffordable on the $0.15 minimum.

### The index

| round trip | cost rm | cost pt | ×under | net R rm | **net R pt** | t/day |
|---|---|---|---|---|---|---|
| 0.04% (headline) | 0.425 | 0.698 | 1.64 | +0.402 | **−0.024** | −1.23 |
| 0.02% (optimistic) | 0.213 | 0.349 | 1.64 | +0.615 | **+0.325** | +5.60 |

**R474's "0.48 of the stop distance" is 0.698 per trade.** The index factor is
1.64x against crypto's ~3x — its stop distribution is less skewed. 14.53% of
index entries carry a stop tighter than the 0.04% round trip.

### ITEM 0 — RECOMPUTED DIGIT FOR DIGIT, AND IT STANDS

R485 confirmed by reading the code that R474's net R is per-trade. This round
rebuilt R474's own slice boundaries from the SPY parquets (choosing → 2022-05-03,
middle → 2024-06-13) and recomputed the published foursome from the entry
population:

| statistic | PUBLISHED (R474) | RECOMPUTED | as ratio-of-means |
|---|---|---|---|
| trades | 371 | **371** | — |
| days | 155 | **155** | — |
| gross % of price | +0.0726 | **+0.0726** | — |
| net % of price | +0.0326 | **+0.0326** | — |
| gross R | +0.618 | **+0.6179** | +0.568 |
| net R | +0.132 | **+0.1324** | +0.255 |

**Item 0's sealed numbers stand exactly as published. They are per-trade, they
are not exposed to this error, and had they been computed the wrong way they
would have read BETTER (+0.255), not worse.** This is now verified two
independent ways.

**ONE THING THIS RECOMPUTATION ADDS, AND IT BELONGS IN FRONT OF THE
DEPLOYMENT REVIEW.** R474 published a t clustered by day for the sealed
GROSS (+2.41) and did not publish one for the net or for net R. They are
**net +0.83 and per-trade net R −0.27, on 155 days.** So the cell's *gross*
edge separates from zero on the sealed slice and **its after-cost result does
not, in either unit.** Nothing here is a new look — it is a further statistic
on a result already published, computed from the same 371 rows — and nothing
about the round's verdict changes. But "positive on all three windows" is a
statement about the sign of a mean, and the honest sentence next to it is that
the sealed net is one standard error from zero and the sealed net R is on the
wrong side of it. A deployment review should see both numbers.

### The ones that cannot be restated, marked unverified

- **R370's 0.44 / 2.17** — built on a CENSUS of SPY 5-minute swing widths, not
  a trade population. No per-entry net exists to average, so no per-trade
  version of the statistic exists. It was never a P&L claim. **No restatement
  exists**; it is a correct sizing illustration.
- **R450's 2.4 on its own 3,119-entry, 147-day frame** — step450 saved
  aggregate tables only; the per-entry frame is gone. Restated on the full
  R476 window (a superset) as 6.746. **Unverified on R450's own 147 days.**
- **R478's 0.13–0.25 (fee only)** — superseded twice (R479 spread, R486 CFM)
  and its per-coin fees were corrected by R482. **Superseded, not restated**;
  use the R486 row.
- **Every pre-R450 "stop distance" sentence (R310/R340/R360/R400)** — retired
  books, venues the desk no longer uses, per-entry frames not on disk.
  **Historical, unverified, load-bearing on nothing.**

### Control

The script reproduces R485's published per-trade net R to three decimals
(−0.346, t −3.18) before any other number is trusted. An audit has no edge to
beat; the control is the identity, and it holds.

### Verdict

1. **Every ratio-of-means cost figure in this log is UNDERSTATED, never
   overstated** — 2.94–3.19x on crypto, 1.64x on the index. The factor is a
   property of the stop distribution, not the cost model, so it is the same
   multiplier on every row of a population. **That is exactly why it was
   invisible: it never changed the RANKING of two venues, only the level of
   all of them at once.** Every venue comparison in R478–R486 survives intact.
2. **No per-trade figure in this log is wrong.** All five reproduce.
3. **The sign flips on the crypto family and only there.** Every crypto cost
   model reads positive net R as a ratio-of-means and negative per trade. On
   the index at 0.04% the flip is +0.402 → −0.024 (t −1.23, not separable from
   zero either way); at 0.02% both statistics are positive.

### Looks consumed

**NONE.** This round reads only published populations and recomputes published
statistics. No sealed window was opened, and item 0's slice was re-read, not
re-looked.
