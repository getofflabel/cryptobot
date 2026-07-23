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
