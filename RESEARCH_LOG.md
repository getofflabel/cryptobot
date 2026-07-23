# RESEARCH LOG — the ledger of looks

Every backtest look recorded here, especially SEALED TEST looks (test-window
erosion is real: each look at a spent window on the same family weakens what a
"pass" means). Format per entry: date, hypothesis, config, train/val/test
numbers, verdict, looks consumed.

Prior rounds (1-16) are documented in the step*.py files and the project memory
(`~/.claude/projects/-Users-wallacechen/memory/project-crypto-trading-bot.md`).
This file begins with the autonomous research-cycle era.

---

## 2026-07-22 — Round 17: 2h-resolution tactical entries (step22_round17.py)

**Hypothesis (RESEARCH_QUEUE.md item #1):** The live tactical book's two
triggers — panic-dip (RSI(3)<15) and flag-touch (bar dips to its 80h trend
line and closes back above it) — currently fire on 1h bars. Does the same
tactical logic carry an edge at 2h resolution (fewer, cleaner signals, wider
natural stop)?

**Config (frozen from queue, no tuning):**
- Filter: 4h champion state == long (vol-gated MA 20/100, funding<=1bp),
  mapped onto 2h bars with no lookahead (4h bar's state applies only after it
  fully closes).
- Triggers tested separately AND as the live OR-of-both:
  panic-dip = RSI(3) on 2h close < 15; flag-touch = 2h low <= 80h trend line
  (40-bar SMA at 2h) AND 2h close back above it.
- Stop = 1.85 x median(2h ATR%), median on TRAIN window only = 1.85 x 1.19%
  = **2.2%** (matches the queue's estimate exactly).
- Target = 3:1 = 6.6%. Hold = 24 bars (48h). Execution = maker. Real funding.
- 27,725 2h bars, 6.3 years, 60/20/20.

**Results (train / val / TEST, maker, full costs):**

| variant | train exp | train n | val exp | val n | verdict |
|---|---|---|---|---|---|
| panic-dip 2h | **-$20.30** | 144 | +$53.89 | 55 | FAIL train — negative, no test look |
| flag-touch 2h | +$11.34 | 155 | +$64.83 | 53 | qualified -> tested |
| panic OR flag (live) | **-$10.51** | 207 | +$83.94 | 77 | FAIL train — panic drags it negative, no test look |

**flag-touch 2h SEALED TEST (one look):** exp **+$40.23/trade**, **+11.7%**,
win **52%**, 29 trades, DD **-8.6%**.

**VERDICT: flag-touch 2h SURVIVES THE FULL GAUNTLET.** Positive on train
(+$11.34, 155t), val (+$64.83, 53t), and the sealed test (+$40.23, 29t, 52%
win, -8.6% DD). Clean sample sizes throughout. This is the second tight-stop
tactical family ever to pass the full gauntlet (after the 1h MTF-dip in round
15) and the first survivor at 2h resolution. **-> AWAITING DEPLOYMENT REVIEW.
Not auto-deployed.**

- panic-dip 2h: killed on TRAIN (negative expectancy). No test look taken.
- panic OR flag (live combo): killed on TRAIN (panic's negative train drags
  the combo under). No test look taken.

**Notes for the deployment reviewer:**
1. Flag-touch already runs LIVE at 1h in `tactical.py` (the `_signals_1h`
   flag path, 80h SMA). This 2h variant is a SLOWER cousin of an already-live
   trigger — deploying it means either a parallel 2h flag sleeve or a decision
   about overlap/correlation with the 1h flag firings (they will sometimes
   coincide). Correlation of the two sleeves' entries should be measured before
   sizing both at full tactical allocation.
2. The stop (2.2%) sits safely inside 10x liquidation (~9.5%), so this is
   10x-compatible per the standing mission — but the leverage frontier was NOT
   mapped this run (research only). Map it during deployment review.
3. Train expectancy is modest (+$11.34) vs val/test — the edge is real but not
   huge at 1x; its value is as an ADDITIONAL validated gun (more trade
   frequency), consistent with the "more sleeves, not more voltage" thesis.

**Looks consumed:** ONE sealed-test look on the 2h flag-touch family (pristine
before this — all prior tactical work was 1h). The 2h panic-dip and 2h combined
windows were NOT looked at on test (failed train) and remain unspent.

**Next in queue:** item #2 — OI-confirmed flag-touch (1h live geometry + 24h OI
change > +2%).

## 2026-07-23 — 15m forensic autopsy + composites (interactive session)
Vol-normalized geometry: stop 0.67%, tgt 2.01%, hold 96 bars. AUTOPSY (train
only, both directions): best single conditions reach just 25-26% hit rate vs
~27% breakeven — enrichments cap at 1.14-1.18x (vs 1.35x at 1h). Composites
gauntleted: long (trend+vol+6h momentum) train +$1.95 marginal, val -$18.40
FAIL; short (trend+vol+funding>2) train -$1.78 FAIL. No test looks burned.
FINDING — the resolution map: 4h strong ($401/t), 1h moderate ($40-59/t),
15m below the cost floor. Candle edges decay with resolution because
profit-per-trade shrinks into fixed costs while signal weakens. 5m fetching;
expect worse — nightly researcher to confirm cheaply for completeness.
