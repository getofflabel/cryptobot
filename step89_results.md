# ROUND 89 — DOES THE SEALED-PASSED BREAKOUT GENERALIZE? NO.

The frozen R86/R87 config (Bollinger 20/2.5, breakout bar volume >= 1.2x
its trailing 20-bar average, exit on the band midline, 1h) replayed with
ZERO tuning on nine assets it had never been selected on: SOL, XRP, DOGE,
BNB, ADA, LINK, AVAX, LTC, DOT. Every one of these histories was
genuinely unseen, so nothing was burned by looking.

Code: `step89_breakout_transfer.py` (imports `bollinger_breakout_signal`,
`volume_gate_entry`, `BREAKOUT_CONFIGS` from step86, `score` /
`split_points` from step43, `run_backtest` from backtest.py — none
retyped). Raw: `step89_table.csv`, 8,149 per-trade rows. Log:
`step89_run.log`.

## THE HEADLINE NUMBER IS A TRAP — READ THE SPLITS, NOT THE POOL

The run's own summary says "5 of 11 assets PASS, 927.7 trades/year if
every passer were run." **That framing is misleading and this section
exists to say so before anyone quotes it.** "PASS" there means pooled
full-history expectancy > 0, which hides wildly unstable behaviour across
the chronological windows.

| Asset | train | val | test | pooled | all 3 positive? |
|---|---|---|---|---|---|
| **BTC** (R87 sealed) | +$14.87 | +$5.21 | **+$6.97** | — | **YES** |
| **ETH** (R87 sealed) | +$39.59 | +$26.01 | **+$9.68** | — | **YES** |
| **AVAX** | +$13.83 | +$2.63 | +$12.19 | +$13.89 | **YES** |
| SOL | +$25.27 | **-$1.96** | +$11.86 | +$20.10 | no |
| XRP | **-$10.78** | +$84.83 | +$18.88 | +$2.89 | no |
| DOGE | -$12.21 | +$82.15 | **-$17.11** | -$5.80 | no |
| DOT | -$14.51 | +$8.57 | +$12.65 | -$7.82 | no |
| LINK | -$14.33 | -$9.37 | +$11.30 | -$8.31 | no |
| BNB | -$11.43 | -$25.49 | +$8.88 | -$8.44 | no |
| LTC | -$7.70 | +$1.87 | -$5.28 | -$5.20 | no |
| ADA | -$7.36 | -$10.65 | -$11.39 | -$6.85 | no |

Look at XRP: **-$10.78 train, +$84.83 val, +$18.88 test.** It "passes" on
the pool. That is not an edge, that is a number wandering. DOGE swings
-$12 / +$82 / -$17 and lands at FAIL. Any asset whose splits behave like
that is telling us the config has no stable relationship with it.

## THE VERDICT: 6 OF 9 FRESH ASSETS FAIL OUTRIGHT

Only **AVAX** joins BTC and ETH in having all three windows positive.

**And AVAX is exactly what chance predicts.** With nine assets and three
windows each, if the config had no real edge and each window were a coin
flip, ~1.1 assets would show all-three-positive by luck. We observed 1.
**AVAX therefore adds no evidence.** This is the same discipline that
killed the eye veto earlier tonight (R88), applied to a result that
happens to be in our favour — one hit where one is expected is not a
finding.

**Conclusion: the volume-gated Bollinger breakout is NOT a general
crypto market-structure edge.** It is a BTC edge that also worked on ETH.
BTC's own sealed pass stands untouched by this round — it had a
reproduction check and val->test consistency ($5.21 -> $6.97 on 242
trades), and nothing here weakens it. What this round kills is the
*expansion* story: we cannot bolt on seven more coins and call it 900
trades a year.

## THE OTHER REASON NOT TO RUN THE ALTCOINS: RUIN-LEVEL DRAWDOWN

| Asset | max drawdown | worst single-trade adverse move |
|---|---|---|
| BTC | -23.3% | **-3.93%** |
| ETH | -35.0% | **-7.19%** |
| AVAX | -43.7% | -16.6% |
| SOL | -43.2% | -27.9% |
| XRP | -81.3% | -28.9% |
| BNB | -86.9% | -25.1% |
| LINK | -85.7% | -29.4% |
| DOGE | -84.3% | -32.1% |

This strategy has **no fixed stop** — it exits on the midline. On BTC the
worst any trade ever went against us was 3.93%, which is why a 6% disaster
stop is non-binding there. On the altcoins single trades run **16% to 32%**
against the position. The stops that make BTC safe would fire constantly
on these assets and destroy the strategy, and the stops that would NOT
fire leave 30% of position value exposed with no protection. Even the
"passing" XRP carries an 81% peak-to-trough drawdown for +$2.89 a trade.

## WHAT WE DO WITH THIS

1. **Run it on BTC.** Sealed-passed, val->test consistent, tightest
   adverse excursion, smallest drawdown, ~191 trades/year.
2. **ETH stays flagged fragile** (R87: two consecutive halvings, no
   plateau). Smaller size if run at all.
3. **Do not add the altcoins.** Not AVAX either, on the chance argument
   above — if we want AVAX it needs its own clean evidence, and the way to
   get that is to let it accumulate forward data, not to re-read this one.
4. **The 927 trades/year figure must not be quoted.** The honest number
   from this family is ~191/year on BTC, or ~400 if ETH is included at
   reduced size.

## WHAT THIS ROUND WAS WORTH

It cost nothing (no sealed data existed to burn on these assets) and it
stopped us from deploying a seven-coin system on the strength of a pooled
average. That is the third confident expansion story tonight to die on
contact with proper testing, and the cheapest of the three.
