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

3. ~~**HIS DAILY BIAS AS A PARTITION (step434).**~~
   **DONE — R477, 2026-08-05. No look consumed.** Bias built from step434
   §1D's Procedure B, the one he PERFORMS: most recent body-close break of
   the most recent confirmed two-candle swing, held until it flips; daily
   sets it, the 4-hour must agree, daily wins conflicts. Procedure A not
   built (he teaches it, doesn't perform it, and it needs a London session
   crypto hasn't got).
   **VERDICT: NO.** Kept by his rule **+0.1200%** of price per entry against
   thrown away **+0.1507%** (parent +0.1435%). All three partitions are worse
   than their own complement. Paired by UTC day the primary filter reads
   **+0.0570%, t = 1.59**, unpaired it reads **−0.0307%, t = −1.63** — the
   two poolings **disagree in sign** and neither reaches 2. By asset the whole
   positive is one coin: BTC −0.0075% (t −0.21), ETH −0.0003% (t −0.01), SOL
   +0.2295% (t 1.96). Worse than its complement on longs AND shorts.
   **The one real result: it keeps 23.0% of entries** — the first partition
   in this family at his own stated trading frequency (R475's confluences
   kept 48-53%). And **the 42.4% of entries his stand-down rule discards
   wholesale return +0.1337%**, essentially the parent. So his bias is a
   SIZE rule that cuts exposure by three quarters at no measurable cost to
   the average entry, not a selection rule.
   Censuses: 0 of 96 on net (that census measures Alpaca's fee schedule, not
   the bias); 12 of 96 on gross against ~1.5 by luck, which collapses to **5
   of 24 distinct level × filter populations** once the four target settings
   and the AGREE ⊂ DAILY ∩ H4 nesting are accounted for. **Barred from
   follow-up** — chasing that cluster would be re-tuning after seeing the
   clears, on slices R450 and R475 have already read.

4. ~~**WHAT A CRYPTO ROUND TRIP ACTUALLY COSTS, VENUE BY VENUE.**~~
   **DONE — R478, 2026-08-06. No look consumed.** The queue asked the venue
   to get cheaper by a factor of four. **It can get cheaper by 9.4**, on a
   CFTC-regulated venue a US person can legally use.
   The premise had gone stale in the desk's favour: **crypto perpetuals now
   exist onshore** (Coinbase Financial Markets 2025-07-21, Kraken Derivatives
   US 2026-06-15) and **futures bill PER CONTRACT, not as a percentage.**
   Kraken Derivatives US charges a flat **$0.15/contract/side all-in** on
   contracts sized 0.01 BTC / 0.5 ETH / 5 SOL — a $370-$960 notional band, so
   the round trip is **0.0463% BTC, 0.0314% ETH, 0.0811% SOL, 0.0529% avg**
   against Alpaca taker's 0.50%. R476's average entry flips from **−0.3565%
   to +0.0906% of price on the venue change alone**, method untouched.
   **Second finding, free and available today: Alpaca's own MAKER rate is
   0.15%/side, not 0.25%.** Every backtest in this log charged taker on both
   legs. Posting both legs on the venue the desk already has is 0.30% round
   trip, a 1.67x cut, at the price of missed fills (`backtest.py`'s
   `execution="maker"` already models the chase).
   **NOT A GREEN LIGHT.** R476's decay stands untouched: the 2026 stub of the
   signal is +0.0387% against the new 0.0529% cost — **the same size**. The
   venue removes the COST objection and does nothing to the DECAY objection.
   **The 10x ceiling is not binding and never was:** the method needs 2.9x
   SOL / 4.2x ETH / 5.4x BTC off its own structural stops at 1% risked.
   Full table, the unavailable-to-US list, and the honest limits in R478.

5. **HOW WIDE IS THE BOOK ON A US PERPETUAL CONTRACT?** *(new, opened by
   R478 — it is now the only thing standing between the desk and a measured
   edge, and it inherits that title directly from the venue question.)*
   R478 priced the FEE and deliberately refused to guess the SPREAD. On a
   $370-$960 contract in a US perp market that is weeks-to-months old, the
   spread can plausibly exceed the fee outright: **a 1-tick spread on a thin
   book can be 0.1435% of price on its own — the entire signal.** Every
   number in R478 is therefore an upper bound on how good the venue is.
   Deliverable: top-of-book bid/ask and depth for PBTCUCZ50 / PETHIUZ50 /
   PSOLUZ50 (and the Coinbase nano perps), sampled across the 24h clock,
   recorded to a file the way `cryptobot_snap` already records book data.
   Median and tail spread in % of price, beside R478's fee table.
   **Read-only market data. No account, no order, no money.** If the venue
   cannot be polled without an account, say so and stop — do not open one.

6. **WHAT DOES FUNDING COST A 24-HOUR HOLD?** *(new, opened by R478.)*
   Perps pay/receive funding; spot does not. Kraken US settles it as one cash
   adjustment at 3:00pm CT daily and the method holds 24 hours, so it eats a
   settlement essentially every trade. Sign and magnitude both unknown, and
   `backtest.py` already has `funding_series` machinery plus cached
   `data_bybit_*_funding.parquet` to measure it against. Note the honest
   caveat before running: Bybit funding is a PROXY for Bitnomial funding, not
   the same series, so this bounds the magnitude rather than pricing the
   venue. Runs after item 5 — spread is the larger unknown.

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
- **HIS DAILY / 4-HOUR BIAS AS AN ENTRY FILTER: dead (R477).** All three
  partitions (daily, 4-hour, both-agreeing) are WORSE than the entries they
  throw away, on both directions, over 5.5 years and 71,073 entries. The
  paired-by-day and unpaired readings disagree in sign and neither reaches 2,
  and the positive one is SOL alone (BTC and ETH are exact zeros). Do not
  re-test this partition and do not re-tune the bias definition — a different
  timeframe cut, a tiebreak rule or a "strength of bias" threshold to rescue
  it would all be swept parameters. **Do not chase the gross-census cluster
  either** (prev day low / prev day high / last session high): that is
  re-tuning after seeing which cells cleared, on spent slices.
  **What SURVIVES from R477 and is worth keeping:** his bias is a real
  exposure rule. It keeps 23% of entries, his own stated frequency, and the
  77% it discards perform the same as the ones it keeps — so it cuts size by
  three quarters at no measurable cost to the average entry. That is a
  finding about how much to have on, not about which trade to take.
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
NOTE (R478): **the cost constraint that made this tier look necessary is
gone, and the tier itself is not.** On CFTC-regulated US perpetuals a round
trip is 0.031-0.081% of price (flat $0.15/contract/side) against Alpaca's
0.50%, so cost is no longer 2.0-2.7 stop distances but 0.13-0.25. With that
gone, the method's OWN structural stops ask for **2.9x on SOL, 4.2x on ETH
and 5.4x on BTC at 1% risked** — all comfortably inside the 10x US perp
ceiling, none of them anywhere near 15-20x. Recorded, not decided: the
mandate is Wallace's and stands until he changes it. What R478 establishes
is that **nothing in the measured structure of this method requires 15-20x,
and reaching for it would mean setting stops tighter than chart structure
supports** — which the rule directly above forbids. The binding constraint
was always cost, and cost now has an answer.
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
