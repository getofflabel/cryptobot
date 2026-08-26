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

10. **WHAT DOES THE ACCOUNT PAY, NOT THE EXCHANGE?** *(new, opened by R482, and
   it is the last open cost question.)* R481 declared the cost side finished and
   R482 reopened it: the exchange fee is the SMALLER half. **Coinbase Financial
   Markets bills a percentage of notional on top of CDE's $0.10/side, and the
   only public figure is a marketing floor ("as low as 0.02%").** At that floor
   alone the commission exceeds the whole exchange fee; the standing volume-tier
   table is unpublished and coinbase.com 403s every unauthenticated request.
   Every "net" number in this log — R478's, R479's, R480's, R481's ledger and
   R482's own table — is an exchange-fee-only floor, optimistic by **at least
   0.04% of price a round trip**, which is larger than the 2026 stub of the
   signal (+0.0387%).
   Deliverable, in preference order, cheapest first:
   (a) **A published CFM fee schedule from a non-Coinbase channel** — the NFA
   BASIC record, an FCM disclosure document, a CFTC Form 1-FR, an introducing
   broker's published rate card (Lincoln Park already publishes CDE's exchange
   fee, so it may publish the commission), or Coinbase's own investor materials.
   (b) Failing that, **state the BREAK-EVEN commission** — the CFM rate at which
   the method goes negative on the full window and on the 2026 stub — so the
   unsourced number has a bar to clear rather than a guess attached.
   **Reading documents. No account, no order, no money.** If (a) turns out to
   require an account, that is itself the finding: the true cost of this venue
   is not knowable before signing up, and it goes to Wallace as such.

11. **THE LOG'S NET NUMBERS ARE RATIO-OF-MEANS. RESTATE THEM PER TRADE.**
   *(new, opened by R485, and it is an AUDIT, not a hypothesis.)* R485 found
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
   Priority note: R474's surviving cell (item 0) already reports a PER-TRADE
   net R (+0.132) — `simulate()` computes net_R per row and `summarise()`
   takes its mean — so item 0 is **not** exposed to this error. Confirm that
   in code, in writing, before touching anything else, because that is the one
   number in front of Wallace right now.
   Reading and arithmetic on data already on disk. No new backtest, no look.

12. **IF THE GROSS IS A LINEAR FUNCTION OF VOLATILITY, WHAT IS THE STOP?**
   *(new, opened by R485, and it is a DESCRIPTION with a hard fence around
   it.)* R485 established that this method's gross tracks realized 1-minute
   volatility at r = +0.92 on the index over 11 years and r = +0.93 on crypto
   over 6, and that the whole "decay" is that scale moving. It also
   established that the binding problem is the **shape of the stop
   distribution**: 12% of crypto entries and 14.5% of index entries carry a
   stop tighter than the round trip they must pay, which is what drives
   per-trade net R negative while the ratio-of-means looks positive.
   Deliverable, purely descriptive:
   (a) The joint distribution of stop size and outcome. Do the tightest-stop
       entries differ in gross R from the widest, or are they the same trade
       at a different scale? If they are the same trade, the cost problem is a
       pure SIZING fact and can be stated as one.
   (b) Is the tight-stop share itself a function of volatility? If low
       volatility manufactures unaffordable stops, then "the method degrades
       in quiet markets" and "cost eats it" are one sentence, not two.
   (c) The same two readings on the index, where volatility did not compress.
   **THE FENCE, non-negotiable:** this item may NOT propose, test or imply a
   minimum-stop filter, a volatility gate, or any threshold. Both families'
   sealed slices are spent; nothing here can become a candidate and no
   parameter may be swept. If the round finds itself wanting to cut the
   population, it has failed and must report the description only.

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
NOTE (R482, cost): every cost figure in this file is an **exchange fee**. The
retail FCM (Coinbase Financial Markets) bills a **percentage of notional** on
top, published only as a floor ("as low as 0.02%"). At that floor it exceeds the
whole exchange fee. Treat every "all-in" and "net" number above as optimistic by
**at least 0.04% of price a round trip** until item 10 sources it.
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
