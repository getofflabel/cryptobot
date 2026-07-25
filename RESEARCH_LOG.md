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
