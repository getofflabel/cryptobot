# RESEARCH QUEUE — the standing hunt

Rules (non-negotiable, they are why the live books can be trusted):
- ONE hypothesis per session. Config fully specified HERE before running.
- Protocol: 6yr data, 60/20/20 train/val/test, execution honest for how the
  LIVE book actually fills (taker unless the book truly posts), real funding,
  intra-bar stops/targets via `backtest.py`.
- Qualify = positive expectancy train AND val (min 30/8 trades) -> ONE test
  look. Survivor -> propose for live deployment. Failure -> log, bury, next.
- NEVER re-tune a failed config. Never re-look a spent test window for the
  same family. Log every look in RESEARCH_LOG.md (look-count erosion is real).
- State the expected-by-chance baseline in the same breath as any winner
  (rule earned in R88). Beat a random control, not just zero (rule earned in
  R100). Two assets agreeing is a hypothesis; test a third (R88/R170/R190).

## Queue (top = next)
1. **THE PANIC-DIP EXIT QUESTION (opened by R194).** Two measurements of the
   same book disagree and the exit is the only difference. R150: flat bracket
   swapped for real `exits.py` chart-structure stops, full history -> -$70.09
   train / -$69.54 val, and the book was stood down. R194: the LIVE flat
   ±1.5%/+4.5% bracket on the 2022-02+ window -> +$9.64 train / +$35.20 val at
   taker. Run BOTH exits on the SAME window and the SAME entries, plus a
   chandelier and a structure-trailing variant, and report which exit the
   entry actually wants. Train/val ONLY, no test look — this is a screen to
   settle a contradiction, not a redeployment case. Thickness must be stated
   against round-trip cost in the same table (R194's best cell was 0.54x).
2. **GARCH gate on the 15m shadow system's entry conditions** (last live item
   on the GARCH docket). Pre-specified in R29. Given R31 and R194 both found
   the forecast loses to instantaneous ATR, the honest prior is FAIL — run it
   to close the docket, and if it fails, retire GARCH as an entry filter
   entirely rather than trying a fourth construction.
3. **Funding-settlement scalps around the 8h marks** (DAY-TRADE TIER item 2;
   item 1 news-momentum was done in R45B, item 3 liquidation-cascade is still
   blocked on flow data). Distinct from the buried queue item #3: that was a
   directional post-settle LONG; this is a tight-stop scalp in BOTH directions
   in the window straddling each settlement. Specify stop/target from
   train-only ATR before running.
4. **Stand aside in `transition`** (opened by R84, still unrun). -0.320R on
   n=12 was the worst reliable bucket in the blind drills. Test a hard
   no-trade rule in that state against a random control. n is small — this is
   a measurement, and it must say so.

## Closed / burned — DO NOT RE-RUN
- Items 1-6 of the old numbered queue are ALL SPENT. #1 2h tactical entries
  (R17/step22, flag-touch 2h SURVIVED the full gauntlet). #2 OI-confirmed
  flag-touch, #3 funding-settlement post-settle long, #4 OI-confirmed donchian
  breakout — all FAIL train, closed by the 2026-07-23 credit-sprint batch. #5
  15m forensic autopsy — closed by the 2026-07-23 autopsy round. #6 weekend
  liquidity study — closed by Round 26.
- GARCH docket #1, the percentile-gate grid on the ride {p50,p60,p70}: FAIL,
  belt retained (R31). GARCH docket #2, the storm-veto on the strikes: FAIL
  and actively harmful, monotone dose-response in the wrong direction (R194).

## Quarterly re-audits (fresh live months = new unseen data; never re-tune)
- 2026-10: rollover-confirm SHORT (died on 2025-26 grind; passes if regime
  turned crashy). Config frozen in step log / memory.
- 2026-10: second-leg long (train -$0.48/t — a hair from qualifying).
- 2026-10: capitulation maker long (train -$1.01/t).
- 2026-10: 15m entries + WIDE stops (Wallace's hypothesis; train/val both
  positive, killed by the 2025-26 grind on test).

## Blocked on data (unlock ~2026-08-20, when cryptobot_snap has ~4 weeks)
- Book-imbalance entries: fade rips when bid-side depth collapses; buy dips
  when bid depth holds. The "last $1-2/trade" for shorts lives here.
- OI-flush intraday reads at snapshot resolution.
- Liquidation-cascade continuation (DAY-TRADE TIER item 3).

## STANDING PRIORITY (owner mandate, 2026-07-23): THE 15-20x TIER
Every future research round optimizes for methods that WORK at 10-20x —
tight-stop (<4% and ideally <2%) entries with positive expectancy after
costs. Wide-stop strategies are legacy; the flow-data era (~Aug 20) and all
nightly cycles hunt sub-2%-stop edges first. 3x-style "safe" configs are
not what the owner is paying for.
NOTE (R150/R194): a tight stop only counts if it is the stop the book would
REALLY use. Stops belong at chart structure; a swept flat percentage that
happens to be small is not a tight-stop edge, it is an assumption.

## STANDING RULE (earned R89/R100/R170/R190): TRANSFER IS PART OF VALIDATION
Single-asset sealed tests do not catch asset-specific overfitting. Any
candidate proposed for deployment must be replayed on at least two other
assets before the proposal counts, and any ported CONSTANT (a vol gate, an
ATR threshold) must be RE-DERIVED on the new asset, never copied — BTC's
1.5% ATR gate is open on 96.7% of SOL's bars versus 18-53% of BTC's, and the
selectivity was the entire edge.

## OPEN AND UNRESOLVED (carried, lower priority than the queue above)
- Structural vs local level breaks: R84's lesson was REFUTED and inverted by
  R90; R92 then showed the inversion is DRIFT, not an edge. The remaining
  live question is whether a leg definition that survives minor pullbacks
  changes R84's freshness result. One test, then bury it either way.
- Session structure on oil: London/NY hours sit at the 100th percentile of
  realized |return| against a 200-draw shuffle control, Asia/off-hours at the
  0th. Real, oil-specific, and nothing has been built on it.
- The best two edges on the desk (S&P turn-of-month, RSI2/RSI3 dip-buy) are
  in a market we have no demo venue for. Finding a venue is worth more than
  another research round.
