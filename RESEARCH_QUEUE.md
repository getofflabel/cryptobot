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

1. **THE 1-MINUTE TRIGGER ON THE INDEX — does R450's finding transfer?**
   R450 found that moving his entry trigger from the 5-minute bar to the
   1-minute bar (the resolution he actually specifies) flips the gross sign
   on crypto: −0.0352% to +0.0551% of price per trade, t = 2.76 for the
   difference, t = 3.05 against a random control. Round 370 rejected the
   same shape 72/72 on SPY **with the 5-minute trigger**, and named this
   exact limit as the reason its rejection might be wrong.
   **We already hold `data_alpaca_SPY_1m.parquet` and
   `data_alpaca_QQQ_1m.parquet`. No purchase needed.**
   Config: replay `step450_tjr_crypto_1m.py` arm A vs arm B unchanged on
   SPY and QQQ, regular hours only, entry no earlier than 09:50 (step436
   §4), flat by the close (R370 part 1: a 0.10% stop is gapped through on
   41.5% of nights). Same levels, same 2-hour pending expiry, same
   two-candle swing. **Nothing re-tuned. Report the difference between the
   arms, its t, and the random control — that is the whole question.**
   If the sign flips on the index too, the trigger resolution is a general
   fact about his method and round 370's verdict is formally overturned.
   If it does not, R450's result is crypto-specific and must be said so.
   Train/val only unless it qualifies.

2. **HIS CONFLUENCES, AS PARTITIONS OF THE POPULATION R450 ALREADY BUILT.**
   R450 tested his ENTRY sequence bare. step432/step436 §1 say the
   continuation confluences are **equilibrium and fair value gaps, and
   nothing else** — order blocks and breaker blocks are retired and a test
   fails the build if they reappear. Question: does requiring price to be
   at the equilibrium of the sweep leg, or to be filling a fair value gap,
   partition the 1-minute-trigger population into a materially better
   subset?
   **A partition, never a re-run** (the round-400 lesson): every candidate
   is scored independently, the filtered set must be a strict subset of the
   same entries by timestamp, and the script asserts it. FVG definition is
   fixed by step436 §5 — three candles, low of the third above the high of
   the first, dies on a body close through it, never on a wick. No grid.

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
- **Sweep -> BOS with a 5-MINUTE trigger: dead twice.** 72/72 negative on
  SPY (R370), and on crypto its gross mean is −0.0352% with t = −1.40,
  worse than a random control (R450). Do not test this construction again
  on any instrument. The 1-minute trigger is a different object.

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
