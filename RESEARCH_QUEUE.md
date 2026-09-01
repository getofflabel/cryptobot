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
   **R487 ADDITION (2026-08-29), and it belongs in the review:** the foursome was
   recomputed digit for digit and **stands exactly as published** — it is a
   per-trade statistic and is not exposed to the ratio-of-means error (computed
   the wrong way it would have read BETTER, +0.255, not worse). What R474 never
   published is a t clustered by day for anything but the gross (+2.41): the
   sealed **net is t +0.83 and the sealed per-trade net R is t −0.27**, on 155
   days. **The cell's gross edge separates from zero on the sealed slice; its
   after-cost result does not, in either unit.** Not a new look and the verdict
   is unchanged — but size it knowing the sealed net is one standard error from
   zero.

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

7. ~~**WHAT DOES COINBASE DERIVATIVES ACTUALLY CHARGE?**~~
   **DONE — R482, 2026-08-20. CLOSED. No look consumed. No account, no order.**
   **$0.10 per contract PER SIDE, electronic, STANDING**, effective trade date
   2025-12-15, primary-sourced from **CFTC submission #2025-75** (filed
   2025-11-26, Appendix A) and corroborated independently by Lincoln Park
   Financial's BIP page. **The promotional component the item asked to separate
   DOES NOT EXIST** — no waiver, no expiry, nothing. R478's remembered
   "promotional 0.00%/0.03%" is the **INTERNATIONAL (INTX)** book a US person
   cannot trade; struck from the log. Tier is moot: the filing's "not using a
   fully automated order generating computer system" makes a bot user a
   **Professional**, and band 2 charges Professional and Non-Professional the
   same $0.10. Contract sizes confirmed live: **0.01 BTC / 0.1 ETH / 5 SOL**.
   As a percentage: **BTC 0.0276%, ETH 0.0859%, SOL 0.0460% round trip**, avg
   0.0532% against R478's Kraken stand-in avg of 0.0529%. **The averages match
   and the per-coin order REVERSES** — Coinbase's ETH contract is a fifth of
   Kraken's, so ETH goes from R478's cheapest coin to the most expensive.
   R478's average survived by coincidence; its per-coin Coinbase figures were
   all wrong. `step479_us_perp_spread_snap.py` now carries a venue-aware
   `fee_rt()`; **the Kraken stand-in is gone from the Coinbase rows.**
   Re-run all-in (fee + spread, 9-day sample): Coinbase **BTC 0.0432% / 0.23x**,
   **ETH 0.1126% / 0.47x**, **SOL 0.0724% / 0.21x**. Coinbase still wins on BTC
   and SOL and **LOSES ON ETH** (0.47x vs Bitnomial's 0.35x) — the opposite of
   R478's table.
   **THE ROUND'S REAL OUTPUT, AND IT REOPENS THE COST QUESTION R481 CLOSED:**
   R478's "futures bill PER CONTRACT, not as a percentage" is true of the
   EXCHANGE and **false of the ACCOUNT**. A US person faces **Coinbase Financial
   Markets (CFM)**, an FCM that charges its own commission on top, and **CFM
   bills a PERCENTAGE of notional** — "as low as 0.02%", a volume-tier FLOOR,
   not a rate. **At that floor the commission EXCEEDS the entire exchange fee it
   sits on.** The standing tier table is behind coinbase.com, which 403s every
   unauthenticated request, so it is **UNSOURCED** and no value was invented for
   it. Every net number in this log is an **exchange-fee-only floor, optimistic
   by at least 0.04% of price a round trip.** See new item 10.
   Trading hours primary-sourced (R480's addendum): **Friday 16:00-16:50 CT
   all-markets halt CONFIRMED**; **non-24x7 daily break 16:00-17:00 CT** —
   R480's hole exactly, mechanism confirmed; quarterly 3-4h weekend window.
   **DST TRAP:** the hole is fixed in CHICAGO time, so it is 21:00-22:00 UTC in
   summer and **22:00-23:00 UTC in winter**. Item 8(a) must bucket in CT.
   Two unasked-for findings, both live off the public product endpoint:
   **(a) CDE funding settles HOURLY (3600s), not 8-hourly.** R481's "68.4% of
   entries straddle no settlement" is a Bybit fact wearing a Coinbase label and
   is false here. R481's ZERO survives — the 49.6/50.4 long/short split cancels
   the flows whatever the cadence; the cadence moves the variance, not the mean.
   **(b) THE 10x CAP IS INTRADAY ONLY.** Overnight margin is **24.6% BTC (4.07x),
   24.5% ETH (4.08x), 36.6% SOL (2.73x)**, and SOL is **5x even intraday**.
   R478 said the method needs 5.4x BTC / 4.2x ETH / 2.9x SOL and called that
   comfortably inside 10x. **BTC and ETH are BELOW their overnight ceiling.**
   It bites exactly the 9.7% of positions that run the 24h cap — per R481, the
   tail that produces the ENTIRE gross at +4.13% each. **The margin schedule is
   hostile to the only positions that make the money.** Belongs in front of
   item 9.

8. ~~**WHAT DOES A HOLD DO WHEN THE BOOK IS NOT THERE?**~~
   **DONE — R483, 2026-08-25. CLOSED, both legs. No look consumed. No order,
   no account, no re-recording.**
   **(a) THE EXPOSURE IS CHANCE AND NOTHING ELSE.** Bucketed in CHICAGO time per
   R482's fix: **4.170% of the 68,992 exits land in the 16:00-17:00 CT break
   against a flat clock's 4.167%, z = +0.04**, and the break hour ranks **12th of
   24** by exit count. That is a strong read, not a weak one, because **the CT
   clock is violently lumpy elsewhere** — hours 07-09 CT run 5.7-6.1% of exits
   (z +19.9 / +25.9 / +19.7) and 21-23 CT run 2.8-3.2% (z −12.6 / −15.5 / −18.2).
   Holds across every split: stops 4.151%, cap-runners 4.350%, BTC/ETH/SOL
   4.147-4.191%, and all six years inside 4.021-4.311% with every z under ±0.8.
   The hole exits are **ordinary trades** — gross +0.1333% in vs +0.1308% out,
   **t = +0.07**.
   **R480's premise was wrong by 5x and the correction favours the desk: not 100%
   of positions straddle a break — 19.4% do** (23.1% touch it at all).
   **(b) THE HOLE IS REAL AND DAILY.** 13 days (2026-08-11 → 08-25, 18,451
   samples) against R480's one, recorder untouched. Coinbase break-hour depth is
   **11.0% BTC / 5.7% ETH / 13.2% SOL** of the other 23 hours pooled, **10.4% /
   5.4% / 12.8% weekday-only** — R480's single-Tuesday 5-11% confirmed. Under 25%
   on 8-9 of 11 covered days; **all three exception days are weekend days**, when
   the other 23 hours are already thin. **Bitnomial 105-111% and the offshore
   Kraken control 69-112% — no hole on either.** Spread widens **2.01x BTC /
   1.32x ETH / 1.99x SOL on Coinbase only.**
   **(c) PRICED IT IS A ROUNDING ERROR: 0.00027-0.00055% of price per entry**
   (0.001-0.002 stop distances), about **1.5% of the 2026 stub** of the signal.
   **R480's $17k-$26k CEILING, RE-DERIVED:** it stays TRUE as a book fact and
   **stops being the binding constraint on account size for this method.** 95.83%
   of exits meet the normal book (~$300k), 4.17% meet the thin one; an account
   above the thin-book ceiling is not broken, it pays the surcharge above on that
   share.
   **TWO THINGS THIS ROUND ADDS, and they belong to item 9:**
   (i) **312 exits over 5.5 years (~57/yr) land inside the Friday 16:00-16:50 CT
   all-markets halt** — a CLOSED market, not a thin one. Those stops cannot fire.
   (ii) **The 9.7% cap-runner tail straddles a break 6,711 times out of 6,712 =
   99.985%**, and that tail carries **307% of the population's total gross** at
   +4.13% each (the stopped 90.3% are collectively negative). **R482's overnight
   margin constraint and this one land on the SAME trades.**
   Honest limits: exits are the backtest's, on Alpaca's tape, not observed US
   fills; 13 days is not a year; the surcharge uses the median SPREAD and does not
   model walking a book at 5-13% depth, so it is a floor for a small account.

9. ~~**THE DECAY IS NOW THE WHOLE ARGUMENT. NOBODY HAS MEASURED IT.**~~
   **DONE — R485, 2026-08-26. CLOSED, all three legs. No look consumed.**
   **THE DECAY IS THE PRICE SCALE, NOT THE EDGE.** In % of price the method is
   at **0.15** of its 2021 self; in **risk multiples it is at 0.92** (mean R
   0.664 -> 0.610, daily trend **t = -1.15, flat**), while gross% trends at
   **t = -6.05** and the median stop at **t = -7.87**. The exact identity
   `mean gross% = p*W - (1-p)*L` (a stopped entry loses exactly its stop,
   verified) decomposes the -0.2079% fall with **zero residual**: winners'
   SIZE **103%**, win rate 37%, smaller losses give back 40%. **Entry count
   went UP 10%.**
   **(a) R482's feared scenario is REFUTED — the tail did not thin.** p fell
   only 15.4% (10.33% -> 8.74%) and per unit of risk the winners got **BIGGER,
   15.12R -> 17.42R**; the two cancel. Winners are smaller in % of price
   because their stops are (0.641% -> 0.461%). The venue's overnight margin
   constraint and the decay are **not** pointed at the same trades.
   **(b) NOT monotone, and 2026 is not a stub artifact.** Every year cut to
   Jan 1 -> Jul 26: 0.299 / 0.185 / **0.051** / 0.150 / 0.125 / **0.036**.
   2023 was already this low and 2024 recovered to 2.9x it. In per-trade net R
   2026 is the **second-best** of the six years.
   **(c) THE INDEX DOES NOT DECAY. Volatility story, not crowding.** SPY/QQQ
   2016-2026 sits in 0.043-0.119% with no trend; over the crypto window it goes
   1.00 / 1.46 / 1.11 / 0.99 / 1.01 / 0.77 against crypto's 1.00 / 0.74 / 0.15
   / 0.54 / 0.45 / 0.15. Crypto's 1-minute volatility fell to **0.52** of 2021;
   **SPY's did not fall at all** (0.0177 -> 0.0190). And the gross is a
   near-linear function of that scale on both asset classes: **index r = +0.915
   (11 years, p 0.000), crypto r = +0.933 (6 years, p 0.007).**
   **THE ROUND'S REAL OUTPUT, AND IT IS A CORRECTION TO THIS LOG:** R481's
   "+0.196 stop distances left over" is a **ratio of means** (mean net% over
   MEDIAN stop). A book sized off each trade's OWN stop earns the per-trade
   mean, which is **-0.346, t by day -3.18, negative in ALL SIX YEARS.** The
   two statistics of the same population **disagree in sign.** Cause: `1/stop`
   has a heavy right tail and **12.14% of entries have a stop tighter than the
   whole round trip.** Same check on the index: ratio of means +0.402, per
   trade **-0.024** (t -1.23), 14.53% of entries under the 0.04% round trip —
   which corroborates R474's own "the arm as a whole has NEGATIVE net R" and
   supplies the mechanism.
   **Barred from follow-up: no minimum-stop filter.** A stop threshold is a
   swept parameter and this family has no sealed slice left anywhere to test
   one on. The fact is recorded; it is not to be acted on as a selection rule.

10. ~~**WHAT DOES THE ACCOUNT PAY, NOT THE EXCHANGE?**~~
   **DONE — R486, 2026-08-27. CLOSED. No look consumed. No account, no order.**
   **THE ITEM'S PREMISE WAS WRONG: CFM's fee is INCLUSIVE of the exchange's, not
   on top of it.** Primary-sourced from Coinbase's own launch announcement
   ("Perpetual futures have arrived in the U.S.", 2025-07-21), read via the
   **Internet Archive** because coinbase.com and help.coinbase.com still 403 every
   unauthenticated request. Verbatim: *"fees as low as 0.02%\* per contract"* and
   *"\*Trading fees are inclusive of exchange, clearing, and NFA fees. A minimum of
   $0.15 is charged per contract to cover these fixed costs."* So the account pays
   **max(rate x notional, $0.15) per side**, with CDE's $0.10 INSIDE it — CFM's own
   take over the exchange fee is **five cents a side**, not a percentage on top.
   **The thing that actually bites is the $0.15 MINIMUM, which no percentage-based
   cost model in this log could see.** At live notionals (0.01 BTC / 0.1 ETH /
   5 SOL = $801 / $251 / $544) **the minimum binds on ETH and SOL**, where the
   account pays $0.15 whatever the rate says — **including at a rate of zero.**
   Corrected all-in: **BTC 0.0556% / ETH 0.1463% / SOL 0.0816%.** The item's
   "optimistic by at least 0.04% a round trip" is **overstated 2-3x on BTC and SOL
   (+0.0150 / +0.0184) and correct on ETH (+0.0399).**
   **(a) PARTIALLY MET, and the fallback clause is now answered: the full schedule
   is NOT knowable before signing up.** CFM's mandatory **CFTC Rule 1.55(k)
   disclosure (2026-05-21, 12pp) was fetched and text-extracted in full and
   contains NO FEE SCHEDULE**; NFA BASIC publishes registration only; Lincoln Park
   publishes the exchange fee ($.10, corroborating R482 a second time) and no
   commission; Tradovate is a different FCM whose fee is additive. **The standing
   volume-tier ladder above the 0.02% floor is UNSOURCED and no value was invented
   for it.** Bonus: the docs' "0.00%/0.03%" is re-confirmed as the INTERNATIONAL
   book (it sits next to a "10 USDC min notional"), independently re-striking it.
   **(b) THE BAR, and it is two different answers per R485.** Break-even all-in
   round trip, whole 68,992-entry population: **mean-net 0.1309%, per-trade R
   0.0448%.**
   - **On mean-net the sourced 0.02% floor CLEARS all three coins**, and the ladder
     now has a number to beat: the method goes negative above **0.0355%/side on
     BTC, 0.0637% on ETH, 0.0672% on SOL.** At the one published CFM rate above the
     floor (0.05%, the older futures' intro tier) **BTC goes negative** and ETH is
     untouched because its minimum binds at both rates.
   - **On per-trade R NO BAR EXISTS TO CLEAR. The $0.15 minimum ALONE exceeds the
     entire fee budget on all three coins; a commission of zero still leaves it
     negative.** Budgets are $0.048 / $0.032 / $0.146 a side against a $0.15 floor.
   **The constraint has a PRICE attached, which is the most useful number here:**
   the minimum becomes payable at **BTC $251,590 / ETH $11,621 / SOL $112.** SOL is
   at $108.74 — **within 4%.** That is a finding about the size of the CONTRACT
   against the size of the signal, per the owner's cost rule.
   **2026 IS THE STRONGEST YEAR ON THE PER-TRADE STATISTIC, NOT THE WEAKEST:** its
   break-even is **0.0581%**, above the full window's 0.0448%. **"The 2026 stub
   cannot pay for itself" is true of the mean-net statistic only** — qualify it
   everywhere this file uses it.
   Honest limits: every percentage is a **price snapshot** (2026-08-27, BTC
   $80,130) because a fixed-dollar fee over a moving notional re-prices with the
   coin — quote the dollar figures and the price thresholds, not the percentages;
   and **"per side" is an inference, not a quotation** (the footnote says "per
   contract"), with the alternative halving every fee figure.

11. ~~**THE LOG'S NET NUMBERS ARE RATIO-OF-MEANS. RESTATE THEM PER TRADE.**~~
   **DONE — R487, 2026-08-29. CLOSED. No look consumed.**
   58 claim lines across 15 rounds collapse to **14 claim families: 5
   PER-TRADE, 9 RATIO-OF-MEANS.** **Every ratio-of-means figure in this log is
   UNDERSTATED, never overstated — 2.94-3.19x on crypto, 1.64x on the index**
   (mean of 1/stop is 13.49 against 1/median of 4.23). The factor is a property
   of the STOP DISTRIBUTION, not the cost model, so it is the same multiplier on
   every row of a population — **which is why it was invisible: it never changed
   the RANKING of two venues, only the level of all of them at once. Every venue
   comparison in R478-R486 survives intact.**
   **R481's "the whole cost stack is 0.358 stop distances" is really 0.95-1.20:
   the stack is ONE ENTIRE STOP, not a third of one.** R474's 0.48 on the index
   is 0.698. R483's surcharge 0.0015 -> 0.0047 (still a rounding error).
   **NO PER-TRADE FIGURE IN THIS LOG IS WRONG** — all five reproduce, and the
   script reproduces R485's -0.346 / t -3.18 to three decimals as its control.
   **ITEM 0 RECOMPUTED DIGIT FOR DIGIT AND IT STANDS**: 371 trades, 155 days,
   gross +0.0726%, net +0.0326%, gross R +0.6179, net R **+0.1324** against the
   published +0.132. Had it been computed the wrong way it would have read
   BETTER (+0.255), not worse. Verified two independent ways now.
   **ONE THING THE RECOMPUTATION ADDS AND IT BELONGS IN FRONT OF THE DEPLOYMENT
   REVIEW:** R474 published a t by day for the sealed GROSS (+2.41) and none for
   the net. They are **net +0.83 and per-trade net R -0.27 on 155 days** — the
   cell's gross edge separates from zero on the sealed slice and **its
   after-cost result does not, in either unit.** Not a new look (same 371 rows,
   already-published result) and the round's verdict is unchanged; but "positive
   on all three windows" is a statement about the sign of a mean, and the honest
   sentence beside it is that the sealed net is one standard error from zero.
   Four claims marked **UNVERIFIED rather than quietly kept**: R370's 0.44/2.17
   (a swing-width census, no trade population, no per-trade version exists),
   R450's 2.4 on its own 147 days (per-entry frame gone; restated on a superset
   as 6.746), R478's fee-only 0.13-0.25 (superseded twice), and every pre-R450
   stop-distance sentence (retired books, frames not on disk).
   By coin the per-trade damage is uneven: **ETH -1.092 (t -5.80), BTC -0.520
   (t -2.08), SOL -0.013 (t +0.19)** — SOL is the only coin not distinguishable
   from zero, and it is the one R486 showed is about to become unaffordable on
   the $0.15 minimum.

11b. *(historical, the item as written, kept so the closure is readable)*
   *(opened by R485, an AUDIT, not a hypothesis.)* R485 found
   that the desk's headline risk-multiple statistic and the number a
   risk-sized book actually earns **disagree in sign** on the crypto 1-minute
   family (+0.230 vs -0.346, t -3.18). The same discrepancy can be sitting
   under any "x stop distances" or "net R" sentence in this log that was
   computed as (mean net %) / (a median or mean stop) rather than as the mean
   of per-trade net/stop.
   Deliverable: grep the log and the step files for every risk-multiple claim,
   classify each as ratio-of-means or per-trade, and **restate the
   ratio-of-means ones per trade with a t clustered by day.** Where a
   per-trade recomputation is impossible because the per-entry data is gone,
   say so and mark the number unverified rather than quietly keeping it.
   **ITEM 0 IS NOT EXPOSED, CONFIRMED IN R485 — this was checked first because
   it is the one number in front of Wallace right now.** `simulate()` computes
   `net_R` per row and `summarise()` takes its mean, so R474's +0.132 is
   already a per-trade figure. Independently confirmed by arithmetic on R474's
   own published foursome: if its net R were a ratio-of-means sharing a stop
   divisor with its gross R, then grossR/netR would equal gross%/net%. It does
   not (4.68 against 2.23), and the implied mean cost-over-stop of 0.486
   matches the reported 0.084% median stop. **R474's sealed numbers stand as
   published.**
   Reading and arithmetic on data already on disk. No new backtest, no look.

12. ~~**IF THE GROSS IS A LINEAR FUNCTION OF VOLATILITY, WHAT IS THE STOP?**~~
   **DONE — R488, 2026-08-30. CLOSED, all three legs. No look consumed. The
   fence held.**
   **THE STOP IS A LINEAR FUNCTION OF VOLATILITY TOO, AND THAT IS THE WHOLE
   ANSWER.** Log-log elasticity of the structural stop to the realized
   1-minute move is **0.876 on crypto (R2 0.769, 2,030 days) and 0.973 on the
   index (R2 0.650, 2,280 days, NOT distinguishable from 1.0 at t -1.82)**.
   The ratio is the same number on five instruments in two asset classes over
   eleven years: **per-entry stop/vol median 3.60 crypto, 3.67 index**, by
   year 2.94-3.61 and 2.97-3.58. **His structural stop is about three and a
   half 1-minute moves, everywhere, always.**
   **This EXPLAINS R485's headline rather than adding to it.** If the stop is
   a fixed multiple of volatility then gross R = gross%/stop is scale-free by
   construction, which is exactly why R485 found gross% decaying at t -6.05
   while mean R sat flat at t -1.15. "The gross is a linear function of
   volatility" and "the stop is a linear function of volatility" are one fact
   seen twice; their ratio is the constant.
   **(a) SPLIT, AND THE RAW MEANS WERE A TRAP.** In % of price the stop
   deciles ARE the same trade at a different scale (Spearman rho **+0.988** on
   both asset classes). In risk multiples the raw means say the tightest
   decile is the best in the population (+1.574 gross R) and **that reading is
   false**: its median is **-1.000**, its skew 39.1, and **73.6% of its entire
   gross R is carried by its top 0.1% of entries** — about seven trades. It is
   R487's `1/stop` tail arriving on the GROSS side. **Winsorised at each
   decile's own p99 the picture inverts and flattens: deciles 2-10 sit in a
   band (crypto 0.275-0.450, index 0.476-0.741) and the tightest tenth is the
   only one outside it, on the wrong side** — on crypto it is the only
   negative decile before a cent of cost. Two of the four decile relationships
   are perfect monotone MECHANICS and are recorded as such, not as findings:
   win rate rises with the stop (rho +1.000, 1.80% -> 21.60%) and winner size
   in R falls (rho -1.000, 142R -> 5.2R).
   Cost/stop runs **6.311 in D1 against 0.092 in D10** — a 69x spread inside
   one population paying one fee schedule. Net R **-4.736 -> +0.244**; D10-D1
   paired by day **+6.405, t +2.98** (1,362 days).
   **(b) YES, DECISIVELY.** Monthly, volatility vs median stop r **+0.960**
   (crypto) / **+0.980** (index); volatility vs tight share rho **-0.914** /
   **-0.899**. Quietest fifth of months vs wildest: tight share **21.90% ->
   6.47%** (crypto) and **29.51% -> 3.90%** (index), net R **-0.967 ->
   +0.273** and **-0.343 -> +0.333**.
   **(c) ON THE INDEX THEY ARE ONE SENTENCE.** Index net R is **perfectly
   monotone** across the five volatility fifths while its gross R is **flat
   (r -0.053)** — "the method degrades in quiet markets" IS "cost eats it"
   there, and nothing about the trade changes. **On crypto it is one and a
   half sentences**: the same cost channel PLUS a real gross-side degradation
   (monthly r +0.493).
   **THE ROUND'S MOST USEFUL NUMBER, and it is one coordinate:** solving the
   fitted elasticity for where the median stop equals the round trip gives
   **BTC 0.0098% / SOL 0.0108% / SPY 0.0103% / QQQ 0.0102%** — **four of five
   instruments converge on a 1-minute move of about 0.010% of price.** ETH is
   **0.0293%, three times the others**, entirely because R486's $0.15 contract
   minimum makes its round trip three times BTC's. Median days sit at **5.29x
   (BTC), 8.34x (SOL), 2.88x (QQQ), 2.31x (ETH), 2.07x (SPY)** of their own
   break-even move. **ETH is the coin R487 found is worst per trade (-1.092,
   t -5.80) and this is the mechanism** — three rounds now point at the same
   coin for the same reason.
   Honest limits: the decile effect is a POOLED reading — per-symbol D10-D1
   paired tests reach significance on none of the five (BTC t -1.44, ETH
   -0.12, SOL -0.99, QQQ -0.43, SPY -0.68); daily tight shares are ratios of
   small counts, so the MONTHLY correlations are the ones to trust.
   **THE FENCE HELD AND IT MATTERED.** Every table in this round points at a
   minimum-stop rule and **none was made**. Barred permanently: both families'
   sealed slices are spent (crypto R475, index R474), so a stop threshold
   chosen after seeing these tables could never be validated out of sample on
   either population. **No number produced in R488 may be used to cut a
   population in any future round.**

13. ~~**WHICH INSTRUMENT SHOULD THE DESK SPEND ITS NEXT SEALED LOOK ON?**~~
   **DONE — R489, 2026-09-01. CLOSED, all three legs. No look consumed, and
   none could be: `simulate()` is never called in the file and every
   measurement stops at the 80% boundary of each instrument's own window.**
   **THE ANSWER IS XRP AND LINK, AND THEY ARE NOT A STEP DOWN FROM WHAT THE
   DESK ALREADY HAS.** On the R488 coordinate (median day's 1-minute move /
   all-in round trip) **XRPUSD reads 1.28 and LINKUSD 0.99 against the spent
   incumbents SOL 1.22, BTC 1.04, ETH 0.49, QQQ 0.59, SPY 0.43.** On the
   fee-only read — fully sourced, sample-free, a hard floor on cost — **LINK
   is the best multiple of ANY instrument on this disk, spent or not (1.99),
   XRP second (1.91).** The top two swap on which cost read is used; every
   rank below them is identical in all three reads. Both carry a **genuinely
   unread final 20%** and LINK carries the SAME 1,627-day 2021-2026 window
   BTC does, at 2.3M 1-minute bars.
   **(a) THE US PERPETUAL UNIVERSE IS 29 CONTRACTS, NOT 3**, polled live and
   keyless. LINK, XRP, LTC, ADA, DOT, DOGE, AVAX, BCH, BNB, **PAXG (gold),
   US 500, TECH (Nasdaq-like)**, plus 14 more. This desk spent R478-R488
   reasoning as though CDE listed three coins.
   **AND R486'S FEE COLLAPSES TO ONE RULE: the $0.15 minimum binds below a
   contract notional of $750; above $750 the round trip is a flat 0.04% of
   price on every contract, whatever the coin is.** R486's three per-coin
   numbers are one rule read at three notionals. **CONTRACT SIZE, NOT COIN,
   IS THE COST VARIABLE** — and it is what kills LTC (a $245 contract, 0.12%
   in fees on a 0.0923% tape that is otherwise SOL's) and DOT ($86.50,
   0.35%). Nothing about either INSTRUMENT disqualifies it.
   **(b) `stop/vol ~ 3.6` IS A PROPERTY OF CRYPTO-LIKE TAPE, NOT A CONSTANT
   OF THE METHOD.** Five crypto instruments over 87,000 entries sit in
   **3.57-3.83** astride R488's 3.60 (LINK 3.57, DOT 3.59, LTC 3.76, ADA
   3.78, BTC control 3.83); XRP 4.50 is a modest outlier; **GOLD (PAXG) sits
   at 13.35 — four times the constant**, on 871 entries. Direct vindication
   of the standing transfer rule: **the ratio must be RE-DERIVED on any new
   instrument, never ported.** Sizing a gold book off a crypto 3.6 would have
   been wrong by 4x.
   **(c) TEN INSTRUMENTS HAVE AN INTACT SEALED SLICE** — LINK, LTC, XRP, ADA,
   DOT, PAXG, GLD, IAU, GBPUSD, GBPJPY. Established by READING the step
   files: every round in this family iterates `R.PRIMARY` = BTC/ETH/SOL or
   SPY/QQQ, and R450's eight-pair table is a swing-width census with no
   entries, no fills and no outcomes, so it spent nothing.
   **UNRANKED, NOT RANKED LAST: GLD, IAU, GBPUSD, GBPJPY.** No primary-sourced
   round trip exists for any of them on a venue the desk can reach and none
   was invented. For context and not as a ranking: **GBPUSD's median 1-minute
   move is 0.0075%, UNDER R488's ~0.010% break-even coordinate before a single
   cost is named.** FX is the lowest-volatility instrument on this disk by a
   factor of two, and item 13's FX leg is answered by that number rather than
   by a missing venue.
   Honest limits: the spread half is a seven-poll one-minute median (a single
   poll disagreed by 2x on BTC PERP ten minutes later), calibrated at
   0.86-1.05x of R480's full-clock figures; every CFM number is the UNSOURCED
   ladder's FLOOR, so every multiple is the best case that can exist; ADA,
   DOT, PAXG, GLD, IAU and FX are ranked off 81-138 days; **AVAX and DOGE have
   live contracts and four days of tape each.** See new items 16, 17, 18.

13b. *(historical, the item as written, kept so the closure is readable)*
   *(opened by R488, and it was the highest-value item on this queue
   because it is the only path to a result that could ever be deployed.)*
   The standing position of this family is a dead end BY CONSTRUCTION, not by
   evidence: the method reads positive gross on 5.5 years of crypto and 11 of
   the index, and **neither population has a sealed slice left anywhere**
   (R474 spent SPY/QQQ, R475 spent crypto). Per the standing transfer rule a
   future candidate needs a NEW instrument or NEW data. Nobody has asked which
   one.
   R488 supplies the screen and it costs nothing to run. Its coordinate is
   **the realized 1-minute move divided by the all-in round trip** — the
   median day sits at 5.29x that break-even on BTC, 8.34x on SOL, 2.88x on
   QQQ, 2.31x on ETH and 2.07x on SPY, and the per-trade net R ranking of
   those five (R487: SOL -0.013, BTC -0.520, ETH -1.092) follows it.
   Deliverable, and NO LOOK IS CONSUMED BY ANY PART OF IT:
   (a) For every instrument this desk can actually reach and price — the
       specialists' markets (gold XAUT/GLD/GC=F, oil CL=F/WTIOIL-USDT, index
       ES=F/SPY/QQQ, FX if a venue exists per R484), more coins, and any US
       perpetual on R482's CDE product list — measure the realized 1-minute
       move on whatever history is on disk and pair it with a PRIMARY-SOURCED
       all-in round trip. Rank by the R488 multiple. Say plainly where the
       cost figure is unsourced rather than inventing one (R482/R486
       discipline).
   (b) Does **stop/vol ~ 3.6** transfer? Build the sweep-to-1m-BOS structural
       stop on the top-ranked instruments and read the ratio. R488 has it on
       five instruments in two asset classes; a sixth and seventh either make
       it a constant of the method or expose it as a property of these five.
   (c) Data honesty: for each ranked instrument, state whether a 60/20/20
       split with an UNREAD final 20% actually exists, or whether the desk has
       already read inside that window in some earlier round. An instrument
       with a great multiple and no clean slice is not a candidate either.
   Output is a RANKED SHORTLIST and nothing else. **No entry population is
   qualified and no cell is tested in this round** — the point is to decide
   where the one remaining look gets spent, before spending it.

14. **THE COARSER TRIGGER, READ IN THE STATISTIC R487 ESTABLISHED.**
   *(new, opened by R488.)* R476 compared the 5-minute and 1-minute triggers
   and the 1-minute won by a paired daily difference of t = 9.17 — **on
   GROSS**. R487 then established that gross is not the statistic that decides
   anything on this desk and R488 established why: **the stop scales with the
   trigger's timeframe at an elasticity of ~1 and the round trip does not
   scale at all.** A 15-minute or 1-hour trigger therefore has a
   proportionally SMALLER cost/stop by construction, and the comparison R476
   ran has never been run in per-trade net R.
   Deliverable: the same family at 1m / 5m / 15m / 1h resolution on the crypto
   population, read in **per-trade net R with a t clustered by day**, with the
   stop/vol ratio and the R488 break-even multiple printed for each
   resolution. Plus the entry count, because a coarser trigger fires less
   often and frequency is a separate fact from expectancy.
   **THE FENCE:** this is a DESCRIPTION on spent slices and **cannot produce a
   deployment candidate on crypto or SPY/QQQ under any outcome.** No
   resolution may be "selected"; the round reports the profile. Its real
   purpose is to tell item 13 **which resolution to carry to a new
   instrument** — so it should run AFTER 13 has named the instrument, or
   before it if 13 stalls on sourcing.
   **R489 UPDATE (2026-09-01): item 13 is CLOSED and has named the
   instruments — XRPUSD and LINKUSD.** This item is now unblocked and should
   run BEFORE item 16 spends either slice, because its whole purpose is to
   say WHICH RESOLUTION the one look carries. Reading the resolution profile
   on the spent crypto population costs nothing; spending a clean slice at
   the wrong resolution costs everything. **The fence is unchanged: it
   describes, it cannot select, and no resolution may be "chosen" on the
   strength of its own numbers — item 16 states its resolution in advance
   either way.**

15. **WHERE IN THE HOLD DOES THE GROSS ACTUALLY COME FROM?**
   *(new, opened by R488, carried from R481/R482/R483.)* Three separate rounds
   have landed on the same 9.7% of positions — the cap-runners — from three
   directions: R481 (they produce the entire gross at +4.13% each, the stopped
   90.3% are collectively negative), R482 (BTC and ETH are BELOW their
   overnight margin ceiling, which bites exactly these), R483 (they straddle a
   venue break 99.985% of the time, and ~57 exits a year land inside the
   CLOSED Friday halt). **Nobody has read the gross as a function of how long
   the position actually ran.**
   Deliverable, purely descriptive: cumulative gross and cumulative net R as a
   function of hold length across the whole 68,992-entry population; the R
   distribution of the cap-runners by how many hours they ran; and the share
   of total gross that is already banked before the first overnight boundary
   and before the Friday halt. If most of the money is made in the first few
   hours, R482's and R483's constraints bite the noise; if it is made in the
   last few, they bite the money and this family is finished on venue grounds
   independent of everything else.
   **THE FENCE:** no exit rule, no hold cap and no time-of-day gate may be
   proposed or implied. The 24-hour cap is the population's existing
   construction and is not a parameter to be swept. This round describes where
   the money sits inside a published population; it cuts nothing.

16. **SPEND THE LOOK: THE FAMILY'S PARENT ON LINK AND XRP, 60/20/20, FOR REAL.**
   *(new, opened by R489, and it is now the highest-value item on this queue
   — it is the first item since R474 that CAN produce a deployment candidate.)*
   R489 answered "which instrument" and the answer is XRPUSD and LINKUSD:
   they sit in the same R488 band as the spent incumbents (XRP 1.28 all-in /
   1.91 fee-only, LINK 0.99 / 1.99 against SOL 1.22, BTC 1.04), and **both
   have an unread final 20%.** LINK carries BTC's own 1,627-day window at
   2.3M 1-minute bars; XRP carries 751 days.
   Deliverable: run the family's PARENT — R450/R476's sweep -> 1-minute break
   of structure, the machinery imported unchanged, all eight levels, all four
   target settings, both directions — on LINKUSD and XRPUSD under the full
   protocol. 60/20/20 on each instrument's OWN window. Qualification is
   positive expectancy on train AND val with min 30 train / 8 val trades,
   read in **per-trade net R with a t clustered by UTC day** (R487's
   statistic, not the ratio of means), against the R450 random-entry control
   on the same machinery. Only then ONE test look.
   **NO TUNING OF ANY KIND.** Not the pending expiry, not the hold cap, not
   the swing definition, not the level set, not the stop. Every constant is
   R450's and is imported, not retyped. **Cost is R489's sourced per-contract
   figure for that instrument's own CDE contract** (XRP PERP, LINK PERP),
   charged for honest P&L and used to decide nothing.
   **THE FENCE, AND IT IS THE WHOLE POINT OF THE ITEM:** these are the last
   two clean slices this family has on instruments with real history. If a
   cell qualifies, ONE look is taken and the slice is spent forever. If none
   qualifies, the slice stays sealed and the round logs the failure. **No
   second cell, no re-cut, no "best of" across the two instruments** — a
   result on LINK does not license a second look on XRP for the same cell
   family, and the round must say in advance which instrument it is spending
   and why. **`stop/vol` must be RE-DERIVED on each, never ported** (R489's
   gold result: the crypto 3.6 is wrong by 4x off crypto-like tape).

17. **THE CONTRACT-SIZE FINDING IS A DESK-WIDE COST RULE. WHO ELSE DOES IT MOVE?**
   *(new, opened by R489.)* R489 collapsed R486's per-coin fee arithmetic into
   one rule: **the $0.15 minimum binds below a $750 contract notional; above
   it the round trip is a flat 0.04% on every contract.** Two consequences
   nobody has priced.
   (a) **The cost of an instrument on this venue moves with its PRICE**, and
   a contract can cross the break point without anything about the method
   changing. LTC at $245 notional pays 0.12%; the same contract at a coin
   price 3.1x higher pays 0.04%. **Compute, for every one of the 29 CDE
   perpetuals, the coin price at which its contract crosses $750**, and say
   which are within a plausible move of it in either direction. R486 did this
   for three coins ("BTC $251,590 / ETH $11,621 / SOL $112") as a fee-minimum
   threshold; R489's rule makes it computable for all 29 in one line.
   (b) **PAXG PERP, US 500 PERP and TECH PERP all sit above the break point
   and pay the floor 0.04%** — the cheapest fee on the venue, on gold and two
   index-like instruments. The gold and index specialists have never had a
   sourced US perpetual cost. **Hand them one.**
   Reading and arithmetic on a live public endpoint plus data already on
   disk. **No backtest, no entry population, no look**, and no candidate may
   be proposed by this item under any outcome.

18. **BACKFILL THE TAPE THAT THE SCREEN SAYS IS MISSING.**
   *(new, opened by R489, and it is plumbing, not a hypothesis.)*
   R489's screen was limited by data, not by ideas, in four places:
   **AVAXUSD and DOGEUSD have live CDE perpetuals and about four days of
   1-minute tape each** (DOGE's $418 contract puts it in SOL's fee band);
   **ADAUSD, DOTUSD and PAXGUSD are ranked off 118-132 days**; GLD/IAU off
   81; the FX pairs off 138. Alpaca served 5.5 years of BTC/ETH/SOL/LINK/LTC
   1-minute bars to this repo already, so the history very likely exists for
   the rest.
   Deliverable: backfill 1-minute and 5-minute tape as far back as the source
   will serve for AVAXUSD, DOGEUSD, ADAUSD, DOTUSD and PAXGUSD, write the
   parquets in the existing `data_alpaca_<SYM>_<tf>.parquet` convention, and
   **re-run `step489_next_look_screen.py` unchanged** to see whether the
   ranking moves. **No look, no entry population, no candidate** — the screen
   consumes nothing by construction and re-running it is free.
   **THE FENCE:** backfilling data for an instrument does NOT reset a spent
   slice and must never be used to argue that it does. This item may only
   touch instruments R489 marked INTACT.

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
NOTE (R482): **the 10x ceiling this desk has been planning against is an
INTRADAY ceiling.** Coinbase's own live margin schedule gives 10.00x BTC / 9.99x
ETH but only **5.00x SOL** intraday, and **overnight it drops to 4.07x BTC /
4.08x ETH / 2.73x SOL.** R478 measured the method's own structural requirement at
5.4x BTC / 4.2x ETH / 2.9x SOL at 1% risked and called it comfortably inside 10x.
**BTC and ETH are BELOW their overnight ceiling.** The 15-20x tier is not merely
unrequired — on this venue, for any position held past 16:00 CT, **even the
method's own modest requirement is not financed.** It bites precisely the 9.7% of
positions that run the 24-hour cap, which per R481 produce the entire gross. The
owner mandate stands until Wallace changes it; what is recorded here is that the
venue will not lend at the tier the mandate asks for, overnight, at any account
size.
NOTE (R482, cost, SUPERSEDED BY R486 — kept so the correction is readable): every
cost figure in this file is an **exchange fee**. The retail FCM (Coinbase
Financial Markets) bills a **percentage of notional** on top, published only as a
floor ("as low as 0.02%"). At that floor it exceeds the whole exchange fee. Treat
every "all-in" and "net" number above as optimistic by **at least 0.04% of price
a round trip** until item 10 sources it.
NOTE (R486, cost, and it REPLACES the note above): **CFM's fee is INCLUSIVE of the
exchange, clearing and NFA fees, not charged on top of them.** The account pays
**max(rate x notional, $0.15) per contract per side**, with CDE's $0.10 inside it,
so CFM's own take is **five cents a side**. The corrected all-in round trips are
**BTC 0.0556% / ETH 0.1463% / SOL 0.0816%** (spread term unchanged from R482), and
R482's "at least 0.04%" is **overstated 2-3x on BTC and SOL, correct on ETH.**
**The binding term is not a percentage at all — it is the $0.15 MINIMUM**, which
binds on ETH and SOL at today's contract notionals and is what the account pays
even at a commission rate of zero. **Cost in this family is now a function of the
PRICE OF THE COIN**, because a fixed-dollar fee over a moving notional re-prices
every time the coin does. Quote the dollar figures, not the percentages, and
re-run `step486_cfm_commission.py` whenever prices have moved materially.
NOTE (R486, the bar): break-even all-in round trip on the whole 68,992-entry
population is **0.1309% on the mean-net statistic and 0.0448% per trade.** The
sourced 0.02% floor clears the first on all three coins (the method goes negative
above **0.0355%/side BTC, 0.0637% ETH, 0.0672% SOL**) and **cannot clear the
second at any rate including zero**, because the $0.15 minimum alone exceeds the
per-trade budget. The minimum becomes payable at **BTC $251,590 / ETH $11,621 /
SOL $112** — SOL is within 4% of it. And **2026 is the STRONGEST year on the
per-trade statistic** (break-even 0.0581% against the window's 0.0448%), so
"the 2026 stub cannot pay for itself" is a mean-net sentence only.
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

NOTE (R485): **the desk has been quoting the wrong statistic.** "0.358 stop
distances" and "+0.196 left over" are ratios of means; the number a book sized
off each trade's own stop earns is the **per-trade mean, and it is -0.346 with
t = -3.18, negative in all six years.** The cause is not the decay: `1/stop` has
a heavy right tail and **12.14% of crypto entries (14.53% of index entries)
carry a stop tighter than the entire round trip.** This is the strongest
argument yet that the binding constraint on this desk is neither leverage nor
account size but the **shape of the stop distribution** — and it cuts against
the 15-20x mandate from the opposite direction to R478's: the tier is not merely
unrequired, the entries whose structure would ALLOW it are precisely the ones
that cannot pay for themselves. Owner mandate stands until Wallace changes it.
NOTE (R487, and it REPLACES every "stop distances" figure quoted above): the
cost stack on Coinbase is **0.95-1.20 stop distances PER TRADE, not 0.358.** Every
ratio-of-means figure in this file is understated by ~3x on crypto and 1.64x on
the index, because the mean of 1/stop is 13.49 against the median stop's
reciprocal of 4.23. **The venue rankings are all unaffected** — the same
multiplier applies to every row — so R478-R486's venue conclusions stand exactly
as written; what changes is the LEVEL. When quoting a risk multiple from this
file, quote the per-trade one or say which it is. **84.17% of entries carry a
stop tighter than one Alpaca round trip and 16.65% tighter than the R486
Coinbase all-in.**

NOTE (R488): **the structural stop is not a fixed percentage of price, it is a
fixed multiple of VOLATILITY — about 3.6 one-minute moves, on five instruments in
two asset classes over eleven years** (log-log elasticity to realized 1-minute
vol 0.876 on crypto, 0.973 on the index and not distinguishable from 1.0). Two
consequences for this mandate. **First, the leverage the method asks for is not a
constant** — R478's "5.4x BTC / 4.2x ETH / 2.9x SOL at 1% risked" is a reading
taken at one volatility level, and in the quietest fifth of months the stop is
roughly a third of what it is in the wildest, so the same risk budget asks for
roughly three times the leverage. **A quiet market is where the 15-20x tier
becomes REQUIRED rather than optional, and it is also where R488 shows the method
is least able to pay for itself** (net R -0.967 in the quietest fifth against
+0.273 in the wildest on crypto; -0.343 against +0.333 on the index). The tier
and the unaffordability arrive together. **Second, the tightest tenth of entries
is not the tier's opportunity — it is a worse trade.** Winsorised at its own p99
it is the ONLY negative decile on crypto before a cent of cost, and its headline
+1.574 gross R is 73.6% carried by seven entries. **Barred: none of this may
become a stop-size or volatility filter** (R488's fence; both families' sealed
slices are spent). Owner mandate stands until Wallace changes it.

NOTE (R485, decay): the decay this desk has been treating as a fact about the
method is a fact about the MARKET. In risk multiples the crypto 1-minute method
is at 0.92 of its 2021 self with a flat trend (t = -1.15); the index does not
decay at all; and gross tracks realized 1-minute volatility at r = +0.92 / +0.93
on the two asset classes. **Stop reasoning from "the signal decayed."**

NOTE (R483): **the account-size ceiling R479/R480 raised is not binding on this
method and the daily book hole is not a reason it fails.** The method's exits sit
on the 16:00-17:00 CT break at exactly the flat-clock rate (4.170% vs 4.167%,
z +0.04) on a clock that is ±26 sigma lumpy elsewhere, only 19.4% of positions
straddle a break at all, and the priced surcharge is 0.0003-0.0006% of price per
entry — 1.5% of the 2026 stub. The hole itself is confirmed on 13 days (5.4-12.8%
of normal weekday depth, Coinbase only). What survives as a constraint is not
size: it is (i) ~57 exits a year into the CLOSED Friday 16:00-16:50 CT halt, and
(ii) the fact that the 9.7% cap-runner tail — which carries the entire gross —
straddles a break 99.985% of the time, the same trades R482's overnight margin
schedule will not finance. Two independent constraints, one population.

NOTE (R489): **the venue is nine times larger than this file has assumed, and
the cost variable is CONTRACT SIZE, not the coin.** Coinbase Derivatives lists
**29 US perpetuals**, not three — LINK, XRP, LTC, ADA, DOT, DOGE, AVAX, BCH,
BNB, **PAXG (gold), US 500 and TECH** among them. And R486's per-coin fee
arithmetic collapses to one rule: **the $0.15 minimum binds below a $750
contract notional; above $750 the round trip is a flat 0.04% of price on every
contract, whatever the coin is.** Consequences for this mandate. **The
leverage question and the cost question are now separable in a way they were
not**: cost is set by the contract's notional and leverage by the venue's
margin schedule (R482), and an instrument can be cheap and unfinanced or
expensive and financed independently. **LTC is the clean case** — its
1-minute tape is essentially SOL's (0.0923% vs 0.1059%) and it ranks 4th of 6
purely because its contract is $245. Nothing about the instrument is the
problem. Owner mandate stands until Wallace changes it; what is recorded here
is that **the desk should read a candidate's cost off its CONTRACT, and
re-read it whenever the coin's price moves**, because a fixed-dollar minimum
over a moving notional re-prices without anything about the method changing.
NOTE (R489, transfer): **`stop/vol ~ 3.6` is a property of crypto-like tape,
not a constant of the method.** Five crypto instruments over 87,000 entries
sit in 3.57-3.83 astride R488's 3.60, and **gold (PAXG) sits at 13.35 — four
times it.** Any risk budget that ports the crypto ratio to a new asset class
would have been wrong by 4x. The ratio is RE-DERIVED, never copied.

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
