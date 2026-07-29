# RESEARCH QUEUE — the standing hunt

Rules (non-negotiable, they are why anything here can be trusted):
- ONE hypothesis per session. Config fully specified HERE before running.
- Protocol: 60/20/20 train/val/test, execution honest for how the book
  would really fill, intra-bar stops and targets, real costs charged.
- Qualify = positive expectancy train AND val (min 30/8 trades) -> ONE test
  look. Failure -> log, bury, next.
- NEVER re-tune a failed config. Never re-look a spent test window for the
  same family. Log every look in RESEARCH_LOG.md.
- State the expected-by-chance baseline in the same breath as any winner
  (R88). Beat a random control, not just zero (R100). Two assets agreeing
  is a hypothesis; test a third (R88/R170/R190/R450).
- **Costs are charged for honest P&L and used for nothing else** (owner
  rule, 2026-07-25). They never decline a trade, gate a config or rank an
  instrument. "The signal is smaller than the transaction" is a finding
  about size; "fees make this fail our bar" is a retired sentence.
- **He is instruction, not a hypothesis** (owner rule, 2026-07-25). Research
  finds WHERE his method applies and at what resolution. It never asks
  whether it works.

## Queue (top = next)

0. **⚠️ AWAITING DEPLOYMENT REVIEW — NOT A RESEARCH ITEM. Wallace decides
   this in an interactive session; the nightly researcher must not touch it.**
   R474's `prev day low → 1m BOS, hold to close` on SPY + QQQ passed all
   three windows: choosing net +0.0582%, middle +0.0032%, **sealed +0.0326%
   of price per trade (net R +0.132), positive on both assets.** ~103 trades
   a year per asset, stop 0.150% of price = 6.7x at 1% risked, flat by the
   close, fill no earlier than 09:50. Read the "honest limits" paragraph in
   RESEARCH_LOG.md R474 before sizing anything: the arm as a whole has
   NEGATIVE net R, QQQ's sealed net is a third of SPY's, and the tight tail
   of the stop distribution sits at the scale of the spread.

2. **THE CRYPTO 1-MINUTE ARM, RE-RUN ON THE BACKFILLED HISTORY (R475's
   by-product, and it is the biggest unclaimed number on the desk).**
   R450 ran on 147 days because that was all the 1-minute data there was.
   The parquet files now hold **2021-01-01 → 2026-07-26** — 2.6M BTC
   1-minute bars against R450's 208k. R475 replayed the bare parent over
   that window as a side effect and got **+0.1769% of price per entry over
   42,354 entries, t = 15.33**, against R450's +0.0551% at t = 2.63. Three
   times the effect, six times the t, fourteen times the sample.
   What is owed: the t clustered BY DAY (R474 showed clustering roughly
   halves a t of this shape), the year-by-year read that R450 could not do,
   and the arm-A/arm-B/random-control comparison redone at this sample size.
   **There is no clean sealed slice left on this family** (see below), so
   this round produces a description, not a qualification, and it must say
   so at the top. A candidate out of it needs a NEW instrument or NEW data
   to verify on.

3. **HIS DAILY BIAS AS A PARTITION (step434).** Same population, same rule:
   keep only sweeps taken in the direction of the 4-hour / daily bias his
   spec defines. One partition, both directions reported, chance baseline
   stated. Runs after item 2 so both partitions are measured against the
   same unfiltered population.

4. **WHAT A CRYPTO ROUND TRIP ACTUALLY COSTS, VENUE BY VENUE.** Not a
   backtest — a table. R450's signal is 0.055% of price per trade and one
   Alpaca crypto round trip is 0.50% of notional, so the transaction is
   nine times the size of the thing it collects. This is the single highest
   leverage number on the desk right now: the method does not need to get
   better, the venue needs to get cheaper by roughly a factor of ten.
   Deliverable: taker and maker rates, US-person availability, and the 10x
   legal leverage ceiling, for every venue a US person can actually use.
   **No account is opened and no money moves — this is a written table for
   Wallace to decide from.**

## Obsoleted by the 2026-07-25 strategy pivot — DO NOT RUN
Wallace retired every self-derived strategy and rebuilt the desk on TJR's
method; BloFin was dropped. The four items that topped this queue on
2026-07-25 all measure books that no longer exist, on a venue we no longer
use. They are recorded, not deleted, so nobody re-opens them by accident.
- **The panic-dip exit question** (R150 vs R194 contradiction). The book is
  retired and the venue is gone. The contradiction is unresolved and will
  stay that way; nothing depends on it.
- **GARCH gate on the 15m shadow system.** The shadow system is retired.
  GARCH is closed as an entry filter on the evidence already in the log
  (R29/R31/R194: two constructions failed, one was actively harmful with a
  monotone dose-response in the wrong direction). Docket closed, not
  abandoned mid-question.
- **Funding-settlement scalps around the 8h marks.** Perpetual funding does
  not exist on the venue we trade. Unrunnable, not unresolved.
- **Stand aside in `transition`.** The regime machine that produced that
  state is retired with the champion book.

## Closed / burned — DO NOT RE-RUN
- Old numbered queue items 1-6: all spent (2h tactical entries SURVIVED in
  R17/step22; OI-confirmed flag-touch, post-settle long and OI-confirmed
  donchian all FAIL train; 15m autopsy closed; weekend liquidity closed).
- GARCH docket #1 percentile gate: FAIL, belt retained (R31). Docket #2
  storm-veto: FAIL and harmful (R194).
- **Sweep -> BOS with a 5-MINUTE trigger: dead three times.** 72/72 negative
  on SPY (R370); on crypto its gross mean is −0.0352%, t = −1.40, worse than
  a random control (R450); and on SPY + QQQ 2016-2026 it is +0.0055% with
  t = 1.81 clustered by day and **0 of 32 cells qualify** (R474). Do not
  test this construction again on any instrument. The 1-minute trigger is a
  different object and is the opposite result.
- **SPY/QQQ 1-minute sweep-to-BOS: the sealed 20% is SPENT (R474).** One
  look, taken on `prev day low → 1m BOS, hold to close`, which survived. The
  other 22 qualifying cells of that round are unverified out of sample and
  must stay that way. **Never re-open the SPY/QQQ 1-minute final window for
  this family.**
- **CRYPTO 1-minute sweep-to-BOS: the sealed 20% is now SPENT TOO (R475).**
  One look, taken on `4h swing low → 1m BOS, hold 24h` + fair value gap.
  Positive in price terms (+0.0726% gross per trade... 24 trades, net R
  −1.98) and **explicitly NOT a deployment candidate** — read R475's sealed
  paragraph before anyone revives it. **Both of this family's sealed windows
  are now gone.** The backfilled 2021-2026 crypto window has boundaries that
  R450 and R475 have both already read inside, so a future candidate on this
  family needs a NEW instrument or NEW data, not a new slice.
- **HIS CONTINUATION CONFLUENCES AS AN ENTRY FILTER: dead (R475).**
  Equilibrium is nothing on both windows (t = 1.06 on 147 days, 1.49 on 5.5
  years). The fair value gap looked real on 147 days (+0.2007%, t = 2.61)
  and **reverses sign on fourteen times the data** (−0.0377%, t = −1.36):
  the gap-filling subset is worse than the entries it throws away. 1 of 96
  cells cleared on the short window and 0 of 96 on the long one, against ~6
  by chance. Do not re-test this partition, and do not re-tune the gap or
  equilibrium definitions to rescue it.

## Blocked on data (unlock ~2026-08-20, when cryptobot_snap has ~4 weeks)
- Book-imbalance entries: fade rips when bid-side depth collapses; buy dips
  when bid depth holds.
- Liquidation-cascade continuation.

## STANDING PRIORITY (owner mandate, 2026-07-23): THE 15-20x TIER
Optimize for methods that work at 10-20x — tight-stop entries with positive
expectancy after costs. **A tight stop only counts if it is the stop the
book would REALLY use** (R150/R194): stops belong at chart structure, and a
swept flat percentage that happens to be small is an assumption, not an
edge.
NOTE (R450): the structure supports it. His 1-minute two-candle swing sits
at 0.077% of price on BTC and 0.16-0.22% on the other seven pairs, which is
4.6x to 13.1x at 1% risked, read off the chart rather than chosen. **US law
caps it at 10x**, so only BTC's 1-minute structure is tighter than the
ceiling. The binding constraint is no longer the stop — it is that a round
trip costs 2.4 stop distances at Alpaca crypto rates. See queue item 4.
NOTE (R474): on the index the 1-minute swing is **0.046% of price on SPY
(21.6x at 1% risked) and 0.063% on QQQ (15.8x)** — the tightest structure
this desk has measured anywhere, and the index costs 0.04% a round trip
against crypto's 0.50%. **The 1m/5m stop ratio is 0.44 on SPY, 0.44 on QQQ
and 0.46 on BTC** — the same number on three instruments in two asset
classes. The catch is the same one in a different place: at a 0.084% stop a
0.04% round trip is still 0.48 stop distances, so the arm's net risk
multiple is negative and only the wider-stop cells clear. Wider stop, not
tighter, is where the money is on the index.

## STANDING RULE (R89/R100/R170/R190): TRANSFER IS PART OF VALIDATION
Single-asset sealed tests do not catch asset-specific overfitting. Any
candidate proposed for deployment must be replayed on at least two other
assets, and any ported CONSTANT must be RE-DERIVED on the new asset, never
copied.

## OPEN AND UNRESOLVED (carried, lower priority than the queue above)
- Structural vs local level breaks: R84 refuted and inverted by R90; R92
  showed the inversion is DRIFT. The live question is whether a leg
  definition that survives minor pullbacks changes R84's freshness result.
- Session structure on oil: London/NY hours sit at the 100th percentile of
  realized |return| against a 200-draw shuffle control, Asia at the 0th.
  Real, oil-specific, and nothing has been built on it.
- The two best edges ever measured on this desk (S&P turn-of-month, RSI2/3
  dip-buy) live overnight in a market we hold no armed venue for. R370
  showed the turn-of-month lift is 2.7x larger in the dark window than in
  the session, so it is structurally unavailable to an intraday bot.
