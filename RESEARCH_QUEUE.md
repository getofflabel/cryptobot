# RESEARCH QUEUE — the standing hunt

Rules (non-negotiable, they are why the live books can be trusted):
- ONE hypothesis per session. Config fully specified HERE before running.
- Protocol: 6yr data, 60/20/20 train/val/test, maker/taker as honest for the
  entry type, real funding, intra-bar stops/targets via `backtest.py`.
- Qualify = positive expectancy train AND val (min 30/8 trades) -> ONE test
  look. Survivor -> propose for live deployment. Failure -> log, bury, next.
- NEVER re-tune a failed config. Never re-look a spent test window for the
  same family. Log every look in RESEARCH_LOG.md (look-count erosion is real).

## Queue (top = next)
1. [DONE 2026-07-22, round 17 / step22] 2h-resolution tactical entries.
   flag-touch 2h SURVIVED the full gauntlet (train +$11.34/155t, val
   +$64.83/53t, TEST +$40.23/29t, +11.7%, 52% win, DD -8.6%) -> AWAITING
   DEPLOYMENT REVIEW. panic-dip 2h and panic-OR-flag both died on TRAIN
   (negative), no test looks burned on them. Stop computed to exactly 2.2%
   as estimated. Full evidence in RESEARCH_LOG.md.
2. OI-confirmed flag-touch: the live flag-touch trigger PLUS 24h OI change
   > +2% (real money entering on the dip). 1h, same geometry as live.
3. Funding-settlement timing: does entering long in the 2h AFTER a negative
   funding settlement (shorts just paid) carry edge in bull state? stop
   1.5%, tgt 4.5%, hold 24h.
4. Donchian-channel tactical: buy 24h-high breakout in bull state ONLY when
   24h OI change > +3% AND ATR gate passes; stop 1%, tgt 4%, hold 48h.
   (Differs from dead r12 breakouts by the OI confirmation + bull filter.)
5. 15m FORENSIC AUTOPSY (both directions) — Wallace's method on the
   fastest tradeable resolution: label every 15m bar where a long/short at
   tactical geometry would have PAID (train years only), measure condition
   enrichments (funding, OI, pops, trend state, time-of-day), compose the
   top discriminators into ONE rule per direction, gauntlet them. Data:
   data_bybit_BTCUSDT_15m_full.parquet (fetched 2026-07-23).
6. Weekend liquidity study (measurement only, no strategy): are tactical
   trigger outcomes different Sat/Sun UTC? Informs a possible session veto.

## Quarterly re-audits (fresh live months = new unseen data; never re-tune)
- 2026-10: rollover-confirm SHORT (died on 2025-26 grind; passes if regime
  turned crashy). Config frozen in step log / memory.
- 2026-10: second-leg long (train -$0.48/t — a hair from qualifying).
- 2026-10: capitulation maker long (train -$1.01/t).

## Blocked on data (unlock ~2026-08-20, when cryptobot_snap has ~4 weeks)
- Book-imbalance entries: fade rips when bid-side depth collapses; buy dips
  when bid depth holds. The "last $1-2/trade" for shorts lives here.
- OI-flush intraday reads at snapshot resolution.

## GARCH era (round 29+, tools cached in data_garch_btc_1d.parquet)
- GARCH percentile-gate grid on the ride: thresholds {50th, 60th, 70th}
  pre-specified, train/val ONLY (champion val to beat: +50.5% common-window)
- GARCH storm-veto for strikes: skip entries when forecast > trailing p90
- GARCH gate on the 15m shadow system entry conditions

## STANDING PRIORITY (owner mandate, 2026-07-23): THE 15-20x TIER
Every future research round optimizes for methods that WORK at 10-20x —
tight-stop (<4% and ideally <2%) entries with positive expectancy after
costs. Wide-stop strategies are legacy; the flow-data era (~Aug 20) and all
nightly cycles hunt sub-2%-stop edges first. 3x-style "safe" configs are
not what the owner is paying for.
- DAY-TRADE TIER, next families (candle families exhausted in round 43):
  (1) news-event momentum: enter on WatcherGuru headline timestamp +
  first 15m direction, out within hours (needs the news table's history);
  (2) funding-settlement scalps around the 8h marks; (3) liquidation-
  cascade continuation once flow-data era matures (~Aug 20).

## OPENED BY ROUND 84 (2026-07-24) — highest priority, one of these is wrong
- **Resolve the R83/R84 clean-vs-messy contradiction.** R83 shipped a veto
  that skips washout dip-buys on "messy" tape (98th pctile vs random on
  BOTH assets). R84's blind drills found messy bars traded BETTER than
  clean ones (+0.251R vs -0.394R) and that agreeing with chart_reader's
  tradeable flag did WORSE than overriding it. Different populations, so
  not yet a refutation — but run the R83 partition-and-random-control
  method on a NON-oversold population (arbitrary stratified bars, the R84
  sample shape) at n>=200. If messy beats clean there too, the honest
  reading is "the eye's quality label is strategy-specific, not a general
  filter", and every future use must be earned per strategy.
- **Structural vs local level breaks.** R84's single winning short broke a
  multi-DAY extreme; all 11 losing shorts only cleared a multi-HOUR level
  inside a larger range. chart_reader does not currently distinguish
  these. Add the feature, then re-run the short population.
- **Distance-from-start-of-leg** as an explicit feature: consolidation at
  highs worked on fresh moves (d007/d024), failed on an extended one
  (d037). Same shape, opposite outcome, and the eye can't tell them apart.
- **Stand aside in `transition`.** -0.320R on n=12, the worst reliable
  bucket. Test a hard no-trade rule there against the random control.

## OPENED BY ROUND 90 (2026-07-24) — the inversion, and the trap in it
- **R92: fade the aged structural breakdown.** Shorting the break of an
  old, well-tested level loses monotonically more the older the level is
  (-$9 at age20 to -$89 at age500 on BTC 1h, same shape on 4h). Test the
  other side: BUY those breakdowns.
- **THE TRAP THAT MUST BE CONTROLLED FOR:** BTC rose over most of the
  sample. In an uptrending market EVERY short loses and every long wins,
  and more-aged setups may simply carry longer exposure to that drift. A
  raw "longs beat shorts" result would be worthless. R92 must therefore
  (a) benchmark against random entries at the same timestamps with the
  same holding period, (b) test the MIRROR case (aged resistance broken to
  the UPSIDE — if aged levels genuinely mean-revert, fading should work in
  both directions; if only the long side works, it is drift), and (c)
  split bull and bear sub-periods. Only a symmetric, drift-adjusted result
  counts.
- R84's freshness hypothesis deserves ONE better test: the leg-start
  definition used in R90 resets too often to capture multi-week runs.
  Re-test with a leg definition that survives minor pullbacks before
  calling the idea dead.
