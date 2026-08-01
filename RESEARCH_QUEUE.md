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

2. ~~**THE CRYPTO 1-MINUTE ARM, RE-RUN ON THE BACKFILLED HISTORY.**~~
   **DONE — R476, 2026-08-01. No look consumed.** All three deliverables
   landed. Whole window 2021-2026: **71,073 entries over 2,033 days,
   +0.1435% of price per entry, t naive 18.37, t clustered by UTC day
   13.77.** Random entry on the same stop machinery returns +0.0024% at
   t = 0.06, and the paired daily difference is **+0.1504%, t = 13.13**.
   The 1-minute trigger beats the 5-minute one by +0.0994% a day at t = 9.17.
   Gross positive in **6 of 6 years** and in all three coins (t by day 8-12),
   **and the risk multiple after costs is negative in 6 of 6 and all three**.
   Median stop 0.242% of price (4.1x at 1% risked); one Alpaca round trip is
   2.07 stop distances; the whole signal is 0.29 of one round trip.
   Two corrections recorded there: R475's "+0.1769% over 42,354 entries" was
   its **choosing slice**, not the full window (the whole window is
   +0.1435%); and the effect **decays** — 2021 +0.2908% down to the 2026 stub
   at +0.0387% — which is why every number this family has produced differs
   and all of them are consistent once the year is attached.
   Nothing is proposed for deployment and nothing could be: this family has
   no sealed slice left anywhere.

3. **HIS DAILY BIAS AS A PARTITION (step434).** Same population, same rule:
   keep only sweeps taken in the direction of the 4-hour / daily bias his
   spec defines. One partition, both directions reported, chance baseline
   stated. Runs after item 2 so both partitions are measured against the
   same unfiltered population.

4. **WHAT A CRYPTO ROUND TRIP ACTUALLY COSTS, VENUE BY VENUE.** Not a
   backtest — a table. **R476 promoted this to the only thing standing
   between the desk and a measured edge.** Measured over 5.5 years, three
   coins and 71,073 entries, his signal is 0.1435% of price per entry
   against a 0.50% Alpaca round trip: the transaction is **3.5x the size of
   the thing it collects**, or 2.07 stop distances charged before the trade
   moves. (R450's "nine times" came from its 147-day slice, which is the
   weakest window in the whole history — the real ratio is 3.5x.) The
   method does not need to get better, the venue needs to get cheaper by
   roughly a factor of four.
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
  **R476 footnote, and the ban is unchanged:** on 5.5 years of crypto this
  construction is weakly ALIVE — +0.0296%, t by day 3.30, beating a random
  entry by t = 3.61 — because R450's negative read came off the weakest
  147 days in the history. It is still five times smaller than the 1-minute
  trigger (paired difference t = 9.17), it is still net-negative at any
  venue we can reach, and it is **still barred from being tested as a
  candidate.** Recorded so nobody re-derives it and mistakes it for news.
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
NOTE (R476): on 5.5 years his crypto structural stop — the extreme traded
between the sweep and the entry, which is the stop the book would REALLY use
— has a median of **0.242% of price, or 4.1x at 1% risked** (BTC 0.185%,
ETH 0.239%, SOL 0.341%). That is the honest number for this method and it is
comfortably inside the 10x US cap. It is WIDER than R450's two-candle swing
figure below because the two measure different objects: the swing is one
structure, the stop spans the whole sweep-to-entry leg.
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
