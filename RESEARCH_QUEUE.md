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

5. ~~**HOW WIDE IS THE BOOK ON A US PERPETUAL CONTRACT?**~~
   **CLOSED — R480, 2026-08-12. No look consumed.** Full 24/24-hour clock read,
   5,064 samples over 2026-08-11 06:43 → 2026-08-12 06:36 UTC.
   **R479's 06-08 window was representative, and pessimistic.** In 5 of 6 series
   it quoted a WIDER book than the clock really has (by up to 29%); the one
   optimistic case is 3.8%. Full-clock spreads: Bitnomial **0.0444 / 0.0539 /
   0.0511%**, Coinbase **0.0147 / 0.0427 / 0.0275%** (BTC/ETH/SOL), all-in
   **0.0610-0.1322%**, still **0.31-0.49 stop distances**.
   **The hour is real but shapeless.** 4 of 6 series beat a 500-draw label
   shuffle (p 0.002-0.026), worst/best hour 1.5-3.0x, but best and worst hours
   agree across neither coin nor venue and the US session does not tighten
   these books. **No "trade at hour X" finding exists here and hunting one in
   144 cells would be re-tuning after seeing the clears — barred.**
   **R479's verdict is untouched: on the 2026 stub every coin on every US venue
   is still NEGATIVE after fee and spread** (−0.022% to −0.094%). The clock
   corrected cost by hundredths of a percent; decay did not move.
   Coinbase is tighter than Bitnomial in 24/24 hours on BTC, 23/24 on SOL,
   18/24 on ETH — R479's better-venue call holds hour by hour.
   **NEW, UNASKED-FOR, AND THE ROUND'S REAL OUTPUT: Coinbase's book empties for
   one documented hour EVERY DAY.** At 21:00-22:00 UTC depth is **5-11%** of the
   other 23 hours on all three coins at once. Mechanism primary-sourced: CDE
   runs 24x7 but **non-24x7 participants break daily 16:00-17:00 CT**; the
   market stays open, the quoting goes home. 2026-08-11 was a Tuesday so the
   weekly Friday halt does not explain it. **Bitnomial has no such hole.**
   The method holds 24h, so every position spans it: **R479's "Coinbase supports
   ~$300k of equity" is a 23-hour number; the exitable-at-all-times ceiling is
   $17k-$26k** — Bitnomial's order of magnitude, the one R479 called too thin.
   That is an operational cap on ACCOUNT SIZE and it belongs in front of any
   deployment conversation. See new item 8.
   Honest limits: one day of clock, so the 21:00 hole's mechanism is
   established and its magnitude is indicative; cost is clock-weighted, not
   weighted by when the method actually enters (R476 did not persist its entry
   timestamps).

5b. *(historical, R479's own summary, kept so the closure above is readable)*
   Both venues poll fine with **no account** (Bitnomial public websocket book,
   Coinbase public REST book), so the item's stop-rule never triggered and
   nothing was signed up for. Symbols corrected: **PETHUIZ50 / PSOLUSZ50**.
   **The item's specific fear is refuted.** One tick is **0.0078% (BTC),
   0.0107% (ETH), 0.0132% (SOL)** of price — a ninth to an eighteenth of the
   signal, not the whole thing. But the book rests **5-6 ticks wide** on
   Bitnomial and 2 on Coinbase, so median spread is **0.0470 / 0.0641 /
   0.0661%** (Bitnomial) and **0.0156 / 0.0533 / 0.0264%** (Coinbase).
   **The spread is the same size as the fee.** All-in, R478's 3-coin average
   cost goes 0.0529% → **0.1120% (Bitnomial) / 0.0847% (Coinbase)**, and its
   net entry goes +0.0906% → **+0.0315% / +0.0588%**. R478's DIRECTION
   survives, every NUMBER it attached was optimistic by 2-3x. In stop
   distances the honest figure is **0.32-0.50x**, not 0.13-0.25x.
   **On the 2026 stub every coin on every US venue is now NEGATIVE after fee
   and spread.** Cost is no longer fully answered, and decay never was.
   **New, unasked-for finding: Bitnomial's book is too thin for a real
   account.** Usable equity window ~$5k-$10k (R478's rounding floor below,
   its own depth above); **on Bitnomial SOL the window does not exist** —
   5-level depth is consumed by a $2,834 account, under the $5,000 floor.
   **Coinbase Derivatives is the better venue on both axes** (tighter on all
   three coins, 1-2 orders of magnitude deeper). R478 leaned on Kraken US
   because its fee was primary-sourced; on the book evidence, **Coinbase's
   fee is now the number worth sourcing properly** — see item 7.
   WHAT WAS LEFT: coverage was **3 of 24 UTC hours** (06-08). **Done in R480 —
   see the closure at the top of item 5.** The launch agent
   `com.wallace.usperp-book-snap` is still recording into
   `data_usperp_book.jsonl`; it can be left running (it costs nothing and a
   second day would upgrade the 21:00 hole from indicative to measured) or
   stopped. Nothing in the queue depends on it.

6. ~~**WHAT DOES FUNDING COST A 24-HOUR HOLD?**~~
   **DONE — R481, 2026-08-18. CLOSED. No look consumed.**
   **Funding costs nothing: +0.0001% of price per entry, t by day 0.64,
   0.000 stop distances, under 1% of the fee.** Every cadence agrees (Bybit
   8-hourly, once-daily 3pm CT at both DST offsets, gap-clean subset); the
   sign flips between them and no reading reaches 2.2.
   R479 was right that this was the one cost that could come back positive.
   It comes back at **zero**, and the reason is structural, not small:
   the rate straddled per hold is a real **+0.0056% of price**, but the book
   is **49.6% long / 50.4% short** — eight levels, four each way — so the
   charge and the credit cancel. Longs pay −0.0056% (t by day −13.54),
   shorts collect +0.0056% (t +6.88). **Any future variant that leans one
   way re-opens this question and it would not be a rounding error then.**
   **THE ITEM'S PREMISE WAS FALSE AND THAT IS THE ROUND'S REAL OUTPUT.**
   The method does NOT hold 24 hours. 24h is the CAP: **median hold 43
   minutes**, p75 4.4h, **90.3% stopped out, 9.7% run the cap**, and
   **68.4% of entries straddle no settlement at all** (81% miss a once-daily
   mark). See the correction to item 8 below.
   **The cost side of this family's argument is now FINISHED** — fee sourced
   (R478), spread measured on the full clock (R479/R480), funding measured
   here. Whole stack on Coinbase = 0.358 stop distances; the 5.5-year window
   clears it (+0.0463% net, +0.196x). **The 2026 stub does not (−0.0492%).**
   **Decay is the entire remaining objection and nothing in this queue is
   pointed at it.** See new item 9.
   Second, unasked-for: **Alpaca's 1-minute tape has GAPS** and the 24h cap
   is counted in BARS, so 8.0% of holds span more than 24h of wall clock
   (worst: an 18-bar hold spanning 10,013h). Doesn't move R481's answer
   (gap-clean sensitivity reads the same zero); does apply to every
   1-minute round in this log, and is on the record now.

7. **WHAT DOES COINBASE DERIVATIVES ACTUALLY CHARGE?** *(new, opened by R479.)*
   R478 leaned its whole table on Kraken Derivatives US because that fee
   schedule was primary-sourced, and flagged Coinbase's per-contract
   component ($0.10-$0.15, plus a promotional 0.00%/0.03%) as SECONDARY.
   R479 then measured the books and found Coinbase is the better venue on
   both spread and depth, by a wide margin — which makes the one number
   nobody has sourced properly the number the decision now rests on.
   Deliverable: Coinbase Derivatives' fee schedule for the CDE perps
   (BIP/ETP/SLP), primary-sourced, with the promotional component separated
   from the standing one and its expiry stated. Nano contract sizes are
   already confirmed from the public product endpoint (0.01 BTC / 0.1 ETH /
   5 SOL). Re-run `step479_us_perp_spread_snap.py --report` afterwards with
   the corrected fee so the all-in table stops carrying Kraken's rate as a
   stand-in. **Reading a fee page. No account, no order, no money.**
   **R480 addition, same page-read, no extra work:** while on Coinbase's docs,
   capture the **trading-hours schedule** properly too. R480 sourced the daily
   16:00-17:00 CT non-24x7 participant break from
   `docs.cdp.coinbase.com/derivatives/introduction/market-hours` and it explains
   the measured hole exactly, but the quarterly three-hour maintenance window
   and the Friday 16:00-16:50 CT halt are secondary in this log, and both bite
   a 24-hour hold.

8. **WHAT DOES A HOLD DO WHEN THE BOOK IS NOT THERE?** *(opened by R480,
   PREMISE CORRECTED BY R481 — read this before running it.)*
   R480 measured a **documented, daily, one-hour window (21:00-22:00 UTC) in
   which Coinbase's book is 5-11% of its normal depth**, and concluded that
   because the method holds 24 hours **every position spans it**.
   **R481 refutes the premise: the median position lives 43 MINUTES and 90.3%
   are stopped out before the 24h cap.** The exposure is therefore a SHARE to
   be counted, not "all of them" — and it is still real, because a stop that
   fires inside the hole is filled into a book at 5-11% of normal depth.
   **R480's $17k-$26k exitable-at-all-times ceiling is built on the false
   premise and must be re-derived, not quoted, until (a) is answered.**
   Two questions, cheap, and neither is a backtest of the strategy:
   (a) **What share of the method's stops and exits land inside 21:00-22:00
   UTC?** **The regeneration this item budgeted for is already DONE:** entry
   AND exit timestamps for all 68,992 chargeable entries are persisted in
   `step481_entries_funding.csv` (R481). Read that file; regenerate nothing.
   Aggregate only, no new slice read, no look consumed. If exits land there at
   ~1/24 the constraint is priced by charging a wider spread on that fraction;
   if they CLUSTER there it is a different and worse problem. Note the 43-minute
   median cuts both ways — fewer positions span the hole, but entries taken in
   the hours before it are exposed at exactly the wrong resolution.
   (b) **Does the 21:00 hole recur?** The recorder is still running. One more
   day upgrades the magnitude from indicative to measured, at the cost of
   re-running `step480_us_perp_spread_clock.py`. **Do not re-record; just read
   whatever has accumulated.**
   This also settles the ACCOUNT SIZE question, which is now the binding
   constraint on this venue rather than leverage: **$17k-$26k exitable-at-all-
   times on Coinbase against $300k+ at the median hour.**

9. **THE DECAY IS NOW THE WHOLE ARGUMENT. NOBODY HAS MEASURED IT.** *(new,
   opened by R481.)* Three rounds have been spent driving the cost side of
   this family to a finish (R478 fee, R479/R480 spread, R481 funding), and
   the answer is that **cost is no longer what kills it.** On the full 5.5
   years the method clears the whole Coinbase stack with +0.196 stop
   distances left over. On the 2026 stub it does not, because the GROSS fell
   from +0.2908% (2021) to +0.0387% (R476's year table) — **a 7.5x decay in
   the signal itself.** Every "not deployable" verdict since R478 rests on
   that one number and no round has ever interrogated it.
   Deliverable, and it is a DESCRIPTION not a candidate (this family has no
   sealed slice anywhere, so nothing here can qualify):
   (a) Is the decay in the ENTRY COUNT, the WIN RATE, or the SIZE of the
   winners? R481's split is the handle — 90.3% stopped / 9.7% run the cap,
   and the whole +0.1309% comes from that 9.7% at +4.13% each. If the decay
   is the tail thinning, that is a different fact about the market than if
   the stops got worse.
   (b) Is it monotone or is 2026 a stub? 2026 is a partial year ending
   2026-07-26 and is being quoted as if it were a regime.
   (c) Does the same decay show on the INDEX over the same calendar years?
   R474's SPY/QQQ population is already built. If the decay is crypto-only
   it is a crowding story; if it is both, it is a volatility story.
   `step481_entries_funding.csv` already holds the crypto side of this.

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
NOTE (R479): **cost has HALF an answer.** With the measured spread added, the
all-in charge is 0.32-0.50 stop distances, not R478's 0.13-0.25 — still a
transformation against Alpaca's 2.0-2.7, still nowhere near needing 15-20x.
The tier remains unrequired by anything in this method's measured structure.
A second, harder constraint arrived with it: **Bitnomial's book only supports
about $5k-$10k of equity**, so on that venue the ceiling is account SIZE, not
leverage. Coinbase's book supports roughly $300k.
NOTE (R480): the full 24-hour clock leaves the cost conclusion where R479 put
it — all-in is **0.31-0.49 stop distances**, so the tier is still unrequired by
anything in this method's measured structure. But **Coinbase's $300k is a
23-hour number.** For one documented hour a day (21:00-22:00 UTC, the daily
non-24x7 participant break) its book is 5-11% of normal, which puts the
exitable-at-all-times ceiling at **$17k-$26k** — the same order as Bitnomial's,
the figure R479 rejected as too thin. On a 24-hour hold that spans the window
every single trade, **account SIZE is now the binding constraint on both US
venues, and it binds an order of magnitude tighter than leverage does.**
NOTE (R474): on the index the 1-minute swing is **0.046% of price on SPY
(21.6x at 1% risked) and 0.063% on QQQ (15.8x)** — the tightest structure
this desk has measured anywhere, and the index costs 0.04% a round trip
against crypto's 0.50%. **The 1m/5m stop ratio is 0.44 on SPY, 0.44 on QQQ
and 0.46 on BTC** — the same number on three instruments in two asset
classes. The catch is the same one in a different place: at a 0.084% stop a
0.04% round trip is still 0.48 stop distances, so the arm's net risk
multiple is negative and only the wider-stop cells clear. Wider stop, not
tighter, is where the money is on the index.

NOTE (R481): **the cost side is finished and the tier is still unrequired.**
Funding, the last unmeasured cost, is **+0.0001% of price — zero**, because the
book is 49.6% long / 50.4% short and the charge cancels against the credit.
Whole stack on Coinbase = **0.358 stop distances** off a 0.237% median
structural stop (4.2x at 1% risked). Nothing in this method's measured
structure asks for 15-20x, and the mandate stands until Wallace changes it.
R481 also corrects an assumption every round since R478 has carried: **the
method does not hold 24 hours — the median position lives 43 minutes** and 90%
are stopped out. Anywhere this log reasons from "a 24-hour hold", check it.

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
