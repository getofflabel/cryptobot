# step73_results.md — round 73: Alex Gonzalez ("fxalexg") market-structure
# / break-and-retest strategy, gauntleted

Companion files: `step73_rules.md` (transcript distillation, quotes,
mechanical-vs-discretionary table), `step73_video.py` (the code that
produced every number below — its module docstring is the full
formalization spec, read it for exact definitions). Raw grid:
`step73_gauntlet_full.csv` (106 rows). Research only — no commits, no
live orders.

## 0. TL;DR verdict

**Zero survivors. Out of 106 configs across 6 datasets, NOT ONE clears
train+val positive expectancy at the repo's floors (>=30 train / >=8 val
trades). Ninety configs (85%) can't even be evaluated at those floors —
2 years of cached hourly history, resampled to a 4h entry frame, simply
doesn't produce enough qualifying trades under this formalization on
forex/gold/index. The one dataset with enough deep history to get a fair
test at all, BTC (6-year cache), clears the sample floors on 15/18
configs and FAILS on every single one of them.** This is a materially
weaker result than round 72's TJR strategy, which had real (if modest)
survivors on NQ/ES/BTC. Here, most of the grid isn't even a fair fight —
the honest finding is as much "this system's own two-tier signature is
too sparse to test cleanly on the history available" as it is "this
system doesn't have an edge." His stated win-rate/R:R claims (60-70%
swing-trader win rate, 1:2 minimum R:R) don't hold up in the part of the
grid that DID run: pooled win rate at his own stated 1:2 target
(R2.00 configs) ranges 0-59% with a 35.2% mean, nowhere close. His
headline "$100 into a million" narrative is explicitly walked back on
camera as really "$300,000 into a million" with at least one mid-
challenge account blow-up — it was never a testable mechanical claim to
begin with, since the risk-per-trade behind it is narrated as pure gut
feel (100% of the account on trade 1, stepping down to "never below
35%... maybe 30%, 27%").

## 1. Who he is and what he teaches (full distillation in step73_rules.md)

Alex Gonzalez ("fxalexg," Swing Trading Lab LLC, 1.31M YouTube
subscribers). The video, "The Trading Industry Will Hate Me for This
FREE 10+ Hour Course" (10h35m59s, uploaded 2025-09-28, 2.14M views), is
a full beginner-to-advanced course, not a single-strategy reveal like
round 72's TJR video. Underneath the platform tutorials and backstory,
it teaches ONE consistent mechanical core, used for both his "reversal"
and "trend continuation" chapters:

1. **Top-down market structure** — HH/HL (bullish) / LH/LL (bearish),
   built from candle BODIES only ("do not take the wicks into account"),
   a body close beyond the prior confirmed swing = break of structure.
2. **Area of interest (AOI)** — his umbrella term for support/
   resistance/supply-demand/order-block, drawn only on weekly/daily,
   >=3 touches, 5-60 pip zones (20-35 "sweet spot") — admittedly
   discretionary in his own touch-counting practice.
3. **Break and retest** — price breaks the structure point, retraces
   back to retest it, then a candlestick pattern confirms (his own,
   stricter-than-textbook engulfing rule: must engulf the prior TWO
   candles' bodies; his named "morning star"/"evening star" patterns
   numerically reduce to this same test).
4. **Stop** beyond the invalidating wick + an unstated buffer. **Target**
   stated floor "a minimum of a one to two risk-to-reward," "always aim
   for... a potential of a one to 4" — holding past that is an explicit,
   admitted judgment call, not a rule.
5. **Risk per trade**: never given a formula anywhere in the teaching
   chapters. Confirmed by exhaustive transcript search.

Claimed markets: "Forex, indices, commodities, and cryptocurrencies."
**Actually traded on screen: 100% forex** — GBPCHF (most frequent),
USDJPY, GBPJPY, EURUSD (once, a self-admitted rule-breaking loss),
USDCAD, NZDCAD, USDCHF. No crypto, gold, or index trade is ever executed
in the video despite the course description's claim.

## 2. Formalization — the two-tier collapse (the single biggest fidelity gap)

His full stack is 4-6 timeframes: weekly/daily/4H for trend + AOI, then
1H/30min/15min for the entry-confirmation candle. yfinance's ~60d cap on
sub-hourly bars (identical constraint to round 72) makes an honest
60/20/20 gauntlet at 30m/15m impossible for forex/gold/index — only BTC
has a deep sub-hourly cache, and his own real trades never touch BTC
anyway. This script tests a **two-tier approximation**: DAILY context
(trend + the broken structure level, standing in for his weekly+daily
AOI stage) -> **4H entry** (retest + candlestick confirmation, standing
in for his 4H/1H/30m/15m confirmation stack).

Other stated simplifications:
- **AOI zone-building skipped.** His own multi-touch S/R zone
  construction is already admittedly discretionary in practice ("I
  would not count that one because the candlestick isn't that clean").
  This script anchors the retest directly to the broken structure level
  itself (bos_chain's own lsh/lsl), the mechanical part he actually
  trades off, rather than reconstructing a discretionary zone.
- **Morning-star/evening-star collapsed into the engulfing test.** His
  own description of these patterns (a small indecision candle
  immediately followed by an engulfing candle that eats the prior two
  bodies) reduces numerically to the same "engulf prior 2 candle
  bodies" rule — avoids inventing an arbitrary, never-stated doji-size
  threshold.
- **Retest tolerance fixed at 0.35% of price** — a stated, cross-
  instrument-portable approximation of his pip-based "20-35 pip sweet
  spot" AOI width (pips don't translate across BTC/gold/index/forex).
- **Max hold fixed at 240h (10 trading days)**, not swept — longer than
  round 72's 4h day-trade cap because his own worked examples (the
  1:5 and 1:11 R:R closes) both took multi-day moves; a tight cap would
  truncate exactly the trades his numbers lean on.

**Instruments tested:** his two most-traded actual pairs (USDJPY,
GBPCHF), EURUSD as a generic liquid-forex proxy, gold (XAU, cached
1h/1d), ES=F (index), and BTC (crypto, 6y deep cache) — covering his
claimed "forex/indices/commodities/crypto" span even though only the
forex leg has any live-trading precedent in the video itself.

**Costs**: FOREX (USDJPY/GBPCHF/EURUSD) = FOREX_COSTS, a stated retail
approximation (~1.8bps RT, roughly 2 pips round-trip on a major pair —
no measured forex venue data exists in this repo, so this is reasoned,
not measured, and flagged as such). GOLD/ES = the repo's standard 2bps
RT futures convention (round 55/72). BTC = 12bps RT + real funding
(round 72's convention, unmodified).

## 3. Full gauntlet (106 configs — 18 per dataset x 5 datasets + BTC)

Selection rule: TRAIN expectancy > 0 AND VAL expectancy > 0, with
tr_n>=30 and va_n>=8 = SURVIVOR. The sealed 20% test window was NEVER
computed by this script for any config. Grid: MODE in {reversal,
continuation, both} x ENTRY_STYLE in {breakout, retest} x R-multiple in
{1.0, 2.0, 4.0} (bracketing his stated "minimum 1:2" and "potential
1:4"). Read the SIGN and relative ranking, not the dollar magnitude
($10,000 paper account, full-equity size_frac=1.0, small absolute
numbers expected given sub-2% stops).

### USDJPY (his 2nd most-traded pair — daily context, 4h entry, 730d/1h resample)

| config | stop% | target% | tr_n | tr_exp | tr_win% | va_n | va_exp | va_win% | pooled_win% | pooled_RR | tr/day | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| reversal breakout R1.00 | 1.63 | 1.63 | 15 | 33.02 | 66.67 | 5 | -72.24 | 20.00 | 55.00 | 0.90 | 0.02 | INSUFFICIENT-SAMPLE |
| reversal breakout R2.00 | 1.63 | 3.26 | 15 | 29.34 | 66.67 | 5 | -134.31 | 0.00 | 50.00 | 0.85 | 0.02 | INSUFFICIENT-SAMPLE |
| reversal breakout R4.00 | 1.63 | 6.53 | 15 | 26.52 | 66.67 | 5 | -134.31 | 0.00 | 50.00 | 0.82 | 0.02 | INSUFFICIENT-SAMPLE |
| reversal retest R1.00 | 0.57 | 0.57 | 6 | -19.71 | 33.33 | 3 | 18.36 | 66.67 | 44.44 | 0.98 | 0.01 | INSUFFICIENT-SAMPLE |
| reversal retest R2.00 | 0.57 | 1.14 | 6 | -1.06 | 33.33 | 3 | -1.05 | 33.33 | 33.33 | 1.95 | 0.01 | INSUFFICIENT-SAMPLE |
| reversal retest R4.00 | 0.57 | 2.27 | 6 | 36.56 | 33.33 | 3 | -57.46 | 0.00 | 22.22 | 3.90 | 0.01 | INSUFFICIENT-SAMPLE |
| continuation breakout R1.00 | 0.84 | 0.84 | 15 | 16.16 | 60.00 | 7 | 27.19 | 71.43 | 63.64 | 0.93 | 0.03 | INSUFFICIENT-SAMPLE |
| continuation breakout R2.00 | 0.84 | 1.68 | 15 | 48.57 | 53.33 | 7 | 47.50 | 71.43 | 59.09 | 1.69 | 0.03 | INSUFFICIENT-SAMPLE |
| continuation breakout R4.00 | 0.84 | 3.37 | 15 | 43.08 | 46.67 | 7 | 17.23 | 71.43 | 54.55 | 1.60 | 0.03 | INSUFFICIENT-SAMPLE |
| continuation retest R1.00 | 0.54 | 0.54 | 9 | -6.74 | 44.44 | 4 | 53.99 | 100.00 | 61.54 | 0.98 | 0.02 | INSUFFICIENT-SAMPLE |
| continuation retest R2.00 | 0.54 | 1.08 | 9 | -1.02 | 33.33 | 4 | 89.21 | 100.00 | 53.85 | 1.76 | 0.02 | INSUFFICIENT-SAMPLE |
| continuation retest R4.00 | 0.54 | 2.15 | 9 | 28.22 | 33.33 | 4 | 44.80 | 75.00 | 46.15 | 2.65 | 0.02 | INSUFFICIENT-SAMPLE |
| both breakout R1.00 | 0.93 | 0.93 | 25 | 18.05 | 60.00 | 9 | 9.39 | 55.56 | 58.82 | 0.98 | 0.04 | INSUFFICIENT-SAMPLE |
| both breakout R2.00 | 0.93 | 1.86 | 25 | 32.13 | 48.00 | 9 | 35.47 | 55.56 | 50.00 | 1.70 | 0.04 | INSUFFICIENT-SAMPLE |
| both breakout R4.00 | 0.93 | 3.72 | 25 | 14.90 | 44.00 | 9 | -22.71 | 44.44 | 44.12 | 1.39 | 0.04 | INSUFFICIENT-SAMPLE |
| both retest R1.00 | 0.57 | 0.57 | 14 | -16.90 | 35.71 | 7 | 36.84 | 85.71 | 52.38 | 0.94 | 0.03 | INSUFFICIENT-SAMPLE |
| both retest R2.00 | 0.57 | 1.14 | 14 | -9.13 | 28.57 | 7 | 53.18 | 71.43 | 42.86 | 1.80 | 0.03 | INSUFFICIENT-SAMPLE |
| both retest R4.00 | 0.57 | 2.27 | 14 | 18.00 | 28.57 | 7 | 0.53 | 42.86 | 33.33 | 2.67 | 0.03 | INSUFFICIENT-SAMPLE |

Not one USDJPY config reaches 30 train trades — the "continuation
breakout" family looks the most promising directionally (train AND val
both positive at R1/R2), but tr_n tops out at 25, short of the floor.

### GBPCHF (his single most-frequently-traded pair)

| config | stop% | target% | tr_n | tr_exp | tr_win% | va_n | va_exp | va_win% | pooled_win% | pooled_RR | tr/day | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| reversal breakout R1.00 | 0.28 | 0.28 | 17 | 7.68 | 64.71 | 4 | 13.46 | 75.00 | 66.67 | 0.95 | 0.03 | INSUFFICIENT-SAMPLE |
| reversal breakout R2.00 | 0.28 | 0.55 | 17 | 5.79 | 41.18 | 4 | 34.37 | 75.00 | 47.62 | 1.91 | 0.03 | INSUFFICIENT-SAMPLE |
| reversal breakout R4.00 | 0.28 | 1.11 | 17 | -8.84 | 17.65 | 4 | 8.11 | 50.00 | 23.81 | 2.38 | 0.03 | INSUFFICIENT-SAMPLE |
| reversal retest R1.00 | 0.27 | 0.27 | 9 | 2.36 | 55.56 | 1 | -27.59 | 0.00 | 50.00 | 0.95 | 0.01 | INSUFFICIENT-SAMPLE |
| reversal retest R2.00 | 0.27 | 0.53 | 9 | -9.71 | 22.22 | 1 | -27.59 | 0.00 | 20.00 | 1.92 | 0.01 | INSUFFICIENT-SAMPLE |
| reversal retest R4.00 | 0.27 | 1.06 | 9 | 1.98 | 22.22 | 1 | -27.59 | 0.00 | 20.00 | 3.82 | 0.01 | INSUFFICIENT-SAMPLE |
| continuation breakout R1.00 | 0.35 | 0.35 | 15 | -7.73 | 40.00 | 6 | -0.66 | 50.00 | 42.86 | 0.97 | 0.03 | INSUFFICIENT-SAMPLE |
| continuation breakout R2.00 | 0.35 | 0.70 | 15 | 5.43 | 40.00 | 6 | 16.92 | 50.00 | 42.86 | 1.89 | 0.03 | INSUFFICIENT-SAMPLE |
| continuation breakout R4.00 | 0.35 | 1.41 | 15 | 2.28 | 26.67 | 6 | 11.33 | 33.33 | 28.57 | 2.96 | 0.03 | INSUFFICIENT-SAMPLE |
| continuation retest R1.00 | 0.28 | 0.28 | 7 | -12.65 | 28.57 | 6 | 18.24 | 83.33 | 53.85 | 0.96 | 0.02 | INSUFFICIENT-SAMPLE |
| continuation retest R2.00 | 0.28 | 0.56 | 7 | -16.71 | 14.29 | 6 | 13.24 | 50.00 | 30.77 | 1.92 | 0.02 | INSUFFICIENT-SAMPLE |
| continuation retest R4.00 | 0.28 | 1.11 | 7 | -22.69 | 14.29 | 6 | 17.64 | 33.33 | 23.08 | 2.71 | 0.02 | INSUFFICIENT-SAMPLE |
| both breakout R1.00 | 0.30 | 0.30 | 24 | 1.85 | 54.17 | 8 | 14.39 | 75.00 | 59.38 | 0.96 | 0.04 | INSUFFICIENT-SAMPLE |
| both breakout R2.00 | 0.30 | 0.59 | 24 | 2.91 | 37.50 | 8 | 25.45 | 62.50 | 43.75 | 1.92 | 0.04 | INSUFFICIENT-SAMPLE |
| both breakout R4.00 | 0.30 | 1.18 | 24 | -7.16 | 16.67 | 8 | 18.45 | 50.00 | 25.00 | 2.90 | 0.04 | INSUFFICIENT-SAMPLE |
| both retest R1.00 | 0.27 | 0.27 | 14 | -8.44 | 35.71 | 7 | 11.18 | 71.43 | 47.62 | 0.96 | 0.03 | INSUFFICIENT-SAMPLE |
| both retest R2.00 | 0.27 | 0.54 | 14 | -10.48 | 21.43 | 7 | 7.01 | 42.86 | 28.57 | 1.92 | 0.03 | INSUFFICIENT-SAMPLE |
| both retest R4.00 | 0.27 | 1.08 | 14 | -5.80 | 21.43 | 7 | 10.68 | 28.57 | 23.81 | 3.15 | 0.03 | INSUFFICIENT-SAMPLE |

Same story on the pair he trades most: closest to a floor is "both
breakout" at 24 train trades, still short of 30.

### EURUSD (generic liquid-forex proxy — not one of his real traded pairs)

| config | stop% | target% | tr_n | tr_exp | tr_win% | va_n | va_exp | va_win% | pooled_win% | pooled_RR | tr/day | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| reversal breakout R1.00 | 0.54 | 0.54 | 18 | 5.34 | 55.56 | 4 | 26.68 | 75.00 | 59.09 | 0.97 | 0.03 | INSUFFICIENT-SAMPLE |
| reversal breakout R2.00 | 0.54 | 1.08 | 18 | -0.12 | 38.89 | 4 | 67.74 | 75.00 | 45.45 | 1.68 | 0.03 | INSUFFICIENT-SAMPLE |
| reversal breakout R4.00 | 0.54 | 2.17 | 18 | -17.32 | 27.78 | 4 | 41.26 | 50.00 | 31.82 | 1.76 | 0.03 | INSUFFICIENT-SAMPLE |
| reversal retest R1.00 | 0.29 | 0.29 | 8 | 14.21 | 75.00 | 3 | 9.22 | 66.67 | 72.73 | 0.96 | 0.01 | INSUFFICIENT-SAMPLE |
| reversal retest R2.00 | 0.29 | 0.58 | 8 | 2.86 | 37.50 | 3 | 28.68 | 66.67 | 45.45 | 1.92 | 0.01 | INSUFFICIENT-SAMPLE |
| reversal retest R4.00 | 0.29 | 1.17 | 8 | 2.18 | 25.00 | 3 | 18.49 | 33.33 | 27.27 | 3.48 | 0.01 | INSUFFICIENT-SAMPLE |
| continuation breakout R1.00 | 0.59 | 0.59 | 19 | -3.89 | 47.37 | 7 | 42.31 | 85.71 | 57.69 | 0.98 | 0.03 | INSUFFICIENT-SAMPLE |
| continuation breakout R2.00 | 0.59 | 1.18 | 19 | -13.37 | 26.32 | 7 | -2.79 | 42.86 | 30.77 | 1.65 | 0.03 | INSUFFICIENT-SAMPLE |
| continuation breakout R4.00 | 0.59 | 2.36 | 19 | -13.43 | 21.05 | 7 | -6.67 | 42.86 | 26.92 | 1.97 | 0.03 | INSUFFICIENT-SAMPLE |
| continuation retest R1.00 | 0.42 | 0.42 | 12 | -21.43 | 25.00 | 4 | 20.42 | 75.00 | 37.50 | 0.97 | 0.02 | INSUFFICIENT-SAMPLE |
| continuation retest R2.00 | 0.42 | 0.83 | 12 | -14.56 | 25.00 | 4 | 20.09 | 50.00 | 31.25 | 1.76 | 0.02 | INSUFFICIENT-SAMPLE |
| continuation retest R4.00 | 0.42 | 1.67 | 12 | -14.02 | 25.00 | 4 | -42.37 | 0.00 | 18.75 | 1.67 | 0.02 | INSUFFICIENT-SAMPLE |
| both breakout R1.00 | 0.58 | 0.58 | 25 | 1.57 | 52.00 | 8 | 13.91 | 62.50 | 54.55 | 0.97 | 0.04 | INSUFFICIENT-SAMPLE |
| both breakout R2.00 | 0.58 | 1.16 | 25 | -8.89 | 32.00 | 8 | 12.25 | 37.50 | 33.33 | 1.80 | 0.04 | INSUFFICIENT-SAMPLE |
| both breakout R4.00 | 0.58 | 2.32 | 25 | -16.31 | 28.00 | 8 | -19.46 | 25.00 | 27.27 | 1.56 | 0.04 | INSUFFICIENT-SAMPLE |
| both retest R1.00 | 0.35 | 0.35 | 17 | -2.71 | 47.06 | 5 | 20.39 | 80.00 | 54.55 | 0.96 | 0.03 | INSUFFICIENT-SAMPLE |
| both retest R2.00 | 0.35 | 0.69 | 17 | 1.19 | 35.29 | 5 | 48.33 | 80.00 | 45.45 | 1.93 | 0.03 | INSUFFICIENT-SAMPLE |
| both retest R4.00 | 0.35 | 1.38 | 17 | 3.49 | 29.41 | 5 | 52.30 | 60.00 | 36.36 | 2.88 | 0.03 | INSUFFICIENT-SAMPLE |

### GOLD (claimed market, never demonstrated live)

| config | stop% | target% | tr_n | tr_exp | tr_win% | va_n | va_exp | va_win% | pooled_win% | pooled_RR | tr/day | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| reversal breakout R1.00 | 1.81 | 1.81 | 13 | -69.31 | 30.77 | 2 | -2.90 | 50.00 | 33.33 | 0.99 | 0.02 | INSUFFICIENT-SAMPLE |
| reversal breakout R2.00 | 1.81 | 3.62 | 13 | -63.27 | 23.08 | 2 | 85.96 | 50.00 | 26.67 | 1.86 | 0.02 | INSUFFICIENT-SAMPLE |
| reversal breakout R4.00 | 1.81 | 7.24 | 13 | -58.03 | 23.08 | 2 | 159.99 | 50.00 | 26.67 | 2.16 | 0.02 | INSUFFICIENT-SAMPLE |
| reversal retest R1.00 | 1.04 | 1.04 | 7 | -32.00 | 28.57 | 1 | -105.76 | 0.00 | 25.00 | 1.14 | 0.01 | INSUFFICIENT-SAMPLE |
| reversal retest R2.00 | 1.04 | 2.09 | 7 | -89.18 | 0.00 | 1 | -105.76 | 0.00 | 0.00 | -- | 0.01 | INSUFFICIENT-SAMPLE |
| reversal retest R4.00 | 1.04 | 4.17 | 7 | -89.18 | 0.00 | 1 | -105.76 | 0.00 | 0.00 | -- | 0.01 | INSUFFICIENT-SAMPLE |
| continuation breakout R1.00 | 2.21 | 2.21 | 14 | 81.99 | 71.43 | 4 | 227.42 | 100.00 | 77.78 | 0.86 | 0.03 | INSUFFICIENT-SAMPLE |
| continuation breakout R2.00 | 2.21 | 4.42 | 14 | 57.97 | 50.00 | 4 | 215.30 | 75.00 | 55.56 | 1.53 | 0.03 | INSUFFICIENT-SAMPLE |
| continuation breakout R4.00 | 2.21 | 8.84 | 14 | 47.16 | 50.00 | 4 | 343.84 | 75.00 | 55.56 | 1.69 | 0.03 | INSUFFICIENT-SAMPLE |
| continuation retest | -- | -- | 0 | -- | -- | 0 | -- | -- | -- | -- | -- | NO-ENTRIES |
| both breakout R1.00 | 2.15 | 2.15 | 21 | -2.07 | 52.38 | 5 | 223.44 | 100.00 | 61.54 | 0.92 | 0.04 | INSUFFICIENT-SAMPLE |
| both breakout R2.00 | 2.15 | 4.30 | 21 | -14.36 | 38.10 | 5 | 261.66 | 80.00 | 46.15 | 1.54 | 0.04 | INSUFFICIENT-SAMPLE |
| both breakout R4.00 | 2.15 | 8.60 | 21 | 1.17 | 38.10 | 5 | 387.73 | 80.00 | 46.15 | 1.90 | 0.04 | INSUFFICIENT-SAMPLE |
| both retest R1.00 | 1.04 | 1.04 | 7 | -32.00 | 28.57 | 1 | -105.76 | 0.00 | 25.00 | 1.14 | 0.01 | INSUFFICIENT-SAMPLE |
| both retest R2.00 | 1.04 | 2.09 | 7 | -89.18 | 0.00 | 1 | -105.76 | 0.00 | 0.00 | -- | 0.01 | INSUFFICIENT-SAMPLE |
| both retest R4.00 | 1.04 | 4.17 | 7 | -89.18 | 0.00 | 1 | -105.76 | 0.00 | 0.00 | -- | 0.01 | INSUFFICIENT-SAMPLE |

The eye-catching +200 to +390 va_exp numbers here ("continuation
breakout," "both breakout") are 4-5 trade samples — exactly the kind of
train-only/tiny-val mirage this repo's floors exist to catch, not
evidence of anything. Correctly flagged INSUFFICIENT-SAMPLE, not
SURVIVOR.

### ES=F index (claimed market, never demonstrated live)

| config | stop% | target% | tr_n | tr_exp | tr_win% | va_n | va_exp | va_win% | pooled_win% | pooled_RR | tr/day | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| reversal breakout R1.00 | 1.61 | 1.61 | 12 | -5.15 | 50.00 | 6 | -125.92 | 16.67 | 38.89 | 0.86 | 0.03 | INSUFFICIENT-SAMPLE |
| reversal breakout R2.00 | 1.61 | 3.22 | 12 | -10.86 | 33.33 | 6 | -125.92 | 16.67 | 27.78 | 1.43 | 0.03 | INSUFFICIENT-SAMPLE |
| reversal breakout R4.00 | 1.61 | 6.44 | 12 | -54.38 | 25.00 | 6 | -125.92 | 16.67 | 22.22 | 1.12 | 0.03 | INSUFFICIENT-SAMPLE |
| reversal retest R1.00 | 0.92 | 0.92 | 7 | -57.11 | 14.29 | 4 | -1.68 | 50.00 | 27.27 | 1.06 | 0.02 | INSUFFICIENT-SAMPLE |
| reversal retest R2.00 | 0.92 | 1.85 | 7 | -82.27 | 0.00 | 4 | -25.07 | 25.00 | 9.09 | 2.12 | 0.02 | INSUFFICIENT-SAMPLE |
| reversal retest R4.00 | 0.92 | 3.69 | 7 | -82.27 | 0.00 | 4 | -92.48 | 0.00 | 0.00 | -- | 0.02 | INSUFFICIENT-SAMPLE |
| continuation breakout R1.00 | 1.13 | 1.13 | 12 | 76.74 | 83.33 | 5 | -68.46 | 20.00 | 64.71 | 1.01 | 0.02 | INSUFFICIENT-SAMPLE |
| continuation breakout R2.00 | 1.13 | 2.25 | 12 | 73.21 | 75.00 | 5 | -111.60 | 0.00 | 52.94 | 1.20 | 0.02 | INSUFFICIENT-SAMPLE |
| continuation breakout R4.00 | 1.13 | 4.51 | 12 | 61.83 | 66.67 | 5 | -111.60 | 0.00 | 47.06 | 1.33 | 0.02 | INSUFFICIENT-SAMPLE |
| continuation retest R1.00 | 1.06 | 1.06 | 8 | 25.12 | 62.50 | 3 | -106.81 | 0.00 | 45.45 | 0.98 | 0.02 | INSUFFICIENT-SAMPLE |
| continuation retest R2.00 | 1.06 | 2.13 | 8 | 24.19 | 37.50 | 3 | -106.81 | 0.00 | 27.27 | 2.22 | 0.02 | INSUFFICIENT-SAMPLE |
| continuation retest R4.00 | 1.06 | 4.26 | 8 | 78.90 | 37.50 | 3 | -106.81 | 0.00 | 27.27 | 3.74 | 0.02 | INSUFFICIENT-SAMPLE |
| both breakout R1.00 | 1.28 | 1.28 | 23 | 26.68 | 60.87 | 8 | -105.49 | 12.50 | 48.39 | 0.95 | 0.04 | INSUFFICIENT-SAMPLE |
| both breakout R2.00 | 1.28 | 2.57 | 23 | 28.12 | 52.17 | 8 | -105.49 | 12.50 | 41.94 | 1.26 | 0.04 | INSUFFICIENT-SAMPLE |
| both breakout R4.00 | 1.28 | 5.14 | 23 | 2.17 | 43.48 | 8 | -105.49 | 12.50 | 35.48 | 1.24 | 0.04 | INSUFFICIENT-SAMPLE |
| both retest R1.00 | 1.02 | 1.02 | 14 | 3.69 | 50.00 | 5 | -62.18 | 20.00 | 42.11 | 1.04 | 0.03 | INSUFFICIENT-SAMPLE |
| both retest R2.00 | 1.02 | 2.04 | 14 | -32.49 | 21.43 | 5 | -101.44 | 0.00 | 15.79 | 2.05 | 0.03 | INSUFFICIENT-SAMPLE |
| both retest R4.00 | 1.02 | 4.08 | 14 | -2.58 | 21.43 | 5 | -101.44 | 0.00 | 15.79 | 3.51 | 0.03 | INSUFFICIENT-SAMPLE |

Every single ES val bucket is deeply negative, unlike GOLD/forex's noisy
mixed picture — the weakest dataset even before floors are applied.

### BTC (claimed market, never demonstrated live — the only dataset with enough history for a fair test)

| config | stop% | target% | tr_n | tr_exp | tr_win% | va_n | va_exp | va_win% | pooled_win% | pooled_RR | tr/day | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| reversal breakout R1.00 | 4.76 | 4.76 | 51 | -45.94 | 47.06 | 19 | 220.18 | 73.68 | 54.29 | 0.94 | 0.04 | FAIL |
| reversal breakout R2.00 | 4.76 | 9.52 | 51 | -79.93 | 31.37 | 19 | 77.75 | 52.63 | 37.14 | 1.46 | 0.04 | FAIL |
| reversal breakout R4.00 | 4.76 | 19.04 | 51 | -90.15 | 27.45 | 19 | 154.08 | 52.63 | 34.29 | 1.76 | 0.04 | FAIL |
| reversal retest R1.00 | 1.32 | 1.32 | 32 | -48.62 | 34.38 | 14 | -10.89 | 50.00 | 39.13 | 0.84 | 0.02 | FAIL |
| reversal retest R2.00 | 1.32 | 2.65 | 32 | -72.89 | 15.62 | 14 | -3.05 | 35.71 | 21.74 | 1.78 | 0.02 | FAIL |
| reversal retest R4.00 | 1.32 | 5.29 | 32 | -103.43 | 3.12 | 14 | 42.22 | 28.57 | 10.87 | 3.87 | 0.02 | FAIL |
| continuation breakout R1.00 | 4.31 | 4.31 | 51 | 24.16 | 52.94 | 18 | -165.62 | 27.78 | 46.38 | 1.03 | 0.04 | FAIL |
| continuation breakout R2.00 | 4.31 | 8.62 | 51 | 17.02 | 39.22 | 18 | -194.35 | 22.22 | 34.78 | 1.62 | 0.04 | FAIL |
| continuation breakout R4.00 | 4.31 | 17.25 | 51 | 177.78 | 39.22 | 18 | -224.82 | 16.67 | 33.33 | 2.39 | 0.04 | FAIL |
| continuation retest R1.00 | 1.46 | 1.46 | 29 | -25.71 | 44.83 | 11 | 30.36 | 63.64 | 50.00 | 0.87 | 0.02 | INSUFFICIENT-SAMPLE |
| continuation retest R2.00 | 1.46 | 2.92 | 29 | -8.78 | 34.48 | 11 | -38.73 | 27.27 | 32.50 | 1.73 | 0.02 | INSUFFICIENT-SAMPLE |
| continuation retest R4.00 | 1.46 | 5.85 | 29 | 8.92 | 24.14 | 11 | -88.93 | 9.09 | 20.00 | 3.43 | 0.02 | INSUFFICIENT-SAMPLE |
| both breakout R1.00 | 4.76 | 4.76 | 79 | -17.04 | 49.37 | 27 | 87.14 | 59.26 | 51.89 | 0.96 | 0.06 | FAIL |
| both breakout R2.00 | 4.76 | 9.52 | 79 | -11.22 | 36.71 | 27 | 4.10 | 48.15 | 39.62 | 1.49 | 0.06 | FAIL |
| both breakout R4.00 | 4.76 | 19.04 | 79 | 54.00 | 34.18 | 27 | -17.97 | 44.44 | 36.79 | 1.85 | 0.06 | FAIL |
| both retest R1.00 | 1.40 | 1.40 | 55 | -31.42 | 41.82 | 20 | 17.78 | 60.00 | 46.67 | 0.86 | 0.04 | FAIL |
| both retest R2.00 | 1.40 | 2.80 | 55 | -35.02 | 27.27 | 20 | -5.70 | 35.00 | 29.33 | 1.74 | 0.04 | FAIL |
| both retest R4.00 | 1.40 | 5.60 | 55 | -28.12 | 18.18 | 20 | -14.09 | 20.00 | 18.67 | 3.44 | 0.04 | FAIL |

BTC clears the sample floors on 15/18 configs (train has plenty of
history) — and every one of those 15 FAILs on train, val, or both. The
"reversal breakout R1.00" line has an eye-catching +220 va_exp, but its
own train leg is -45.94 with a 47% win rate — dead on TRAIN before val
even runs, exactly the failure mode round 72 flagged as "the discipline
this repo's floors exist to catch."

## 4. Required analysis 1 — mode (reversal vs. continuation vs. "both")

His two chapters (Reversal Patterns, Trend Continuation) describe the
identical mechanism gated by opposite trend-agreement conditions. Mean
val expectancy by mode:

| dataset | reversal | continuation | both |
|---|---:|---:|---:|
| USDJPY | -63.51 | +46.65 | +18.78 |
| GBPCHF | -4.47 | +12.78 | +14.53 |
| EURUSD | +32.01 | +5.16 | +21.29 |
| GOLD | -12.37 | +262.19 | +92.59 |
| ES | -82.83 | -102.01 | -96.92 |
| BTC | +80.05 | -113.68 | +11.88 |

No consistent winner: continuation beats reversal on USDJPY/GBPCHF/GOLD,
reversal beats continuation on EURUSD/BTC, and ES is deeply negative
regardless of mode. There is no honest evidence his split between
"reversal" and "trend continuation" setups behaves as two meaningfully
different systems — the sign flips dataset by dataset, which is what
you'd expect from the SAME underlying mechanism (as formalized here)
being sampled differently by each trend-agreement filter, not from two
genuinely different edges.

## 5. Required analysis 2 — entry style (his stated preference: retest+confirm)

He states a clear preference: "you can only enter properly on the
retest and then you need proper body rejections," vs. entering at the
raw breakout close ("maybe 30%" of the time). Mean val expectancy:

| dataset | breakout | retest |
|---|---:|---:|
| USDJPY | -25.20 | +26.49 |
| GBPCHF | +15.76 | -0.53 |
| EURUSD | +19.47 | +19.50 |
| GOLD | +211.38 | -105.76 |
| ES | -109.54 | -78.30 |
| BTC | -6.61 | -7.89 |

Mixed, not supportive of his stated preference as a clean rule: retest
helps on USDJPY, is a wash on EURUSD/BTC, and is clearly WORSE on
GBPCHF and GOLD (though GOLD's retest bucket is 1-trade noise, see
section 3). His one explicitly stated hard preference does not survive
an honest on/off comparison any better than round 72's TJR's
cross-index alignment filter did — both this round and last round found
the trader's single most emphasized rule to be the weakest link once
tested with, not just quoted.

## 6. Required analysis 3 — realized win-rate/R:R vs. his claims

At his own stated 1:2 R:R floor (the R2.00 configs, all datasets, all
modes/entry-styles pooled):

- Pooled win rate range: **0% - 59.1%**, mean **35.2%**.
- His taxonomy claims (not necessarily HIS OWN stats): "swing trader's
  win rate tends to be anywhere from 60 to 65%" / "day traders...
  anywhere from a 40 to 50% win rate."
- His self-reported live-challenge stat (n=7 trades, one week's
  snapshot): "win rate is currently a 70%."

**None of his stated win-rate ranges are approached anywhere in this
grid** — the mechanized version of his system realizes win rates
clustered well below even his day-trader floor (40%), let alone his
swing-trader claim. This mirrors round 72's identical finding for TJR
(realized win rates 42-58% vs. his claimed 64.29%) — a second straight
round where a trader's stated win-rate claim doesn't survive honest
mechanization, though this round's gap is larger and the sample sizes
behind it are much thinner.

## 7. Required analysis 4 — trade frequency

| dataset | tr/day min | tr/day mean | tr/day max |
|---|---:|---:|---:|
| BTC | 0.022 | 0.037 | 0.057 |
| ES | 0.016 | 0.026 | 0.044 |
| EURUSD | 0.013 | 0.027 | 0.040 |
| GBPCHF | 0.012 | 0.024 | 0.039 |
| GOLD | 0.011 | 0.021 | 0.037 |
| USDJPY | 0.011 | 0.024 | 0.042 |

Roughly **one trade every 25-90 days** per instrument/config — sparser
even than round 72's already-sparse TJR index result (0.19-0.33/day).
This is a direct, expected consequence of the two-tier collapse: a
daily-context break, THEN an armed retest window, THEN an engulfing
confirmation candle, compounds three separate gates into a rare event.
His own live challenge narrates roughly one trade per WEEK across
several pairs simultaneously — consistent in order of magnitude with a
single-pair rate this sparse, so the frequency gap here is smaller and
more plausible than round 72's index-collapse gap was, but it directly
explains why 85% of this grid can't clear the 30-trade training floor
on ~2 years of available intraday-derived history.

## 8. Verdict

**Does the mechanical core of his market-structure system survive
honest testing?** No — and for a large fraction of the grid, it's not
even a clean "no," it's "not enough data to say yes or no."

- **His own most-traded pairs (GBPCHF, USDJPY)**: every single config
  is INSUFFICIENT-SAMPLE. Two years of available hourly-derived history
  on a daily-context/4h-entry system that gates through three sequential
  filters simply doesn't produce 30 clean train trades. No verdict
  possible either way from this data.
- **EURUSD (generic forex proxy)**: same story, INSUFFICIENT-SAMPLE
  across the board.
- **GOLD**: INSUFFICIENT-SAMPLE everywhere, though several 4-5-trade
  buckets show large positive numbers — explicitly flagged here as
  noise, not evidence, exactly the shape this repo's floors exist to
  reject.
- **ES=F index**: the one dataset where every evaluable val bucket is
  deeply negative regardless of sample size — the closest thing to a
  clean "doesn't work" read in the whole grid, though still short of
  the train floor everywhere.
- **BTC (deep 6-year cache, the only fair test)**: 15/18 configs clear
  the sample floors, and every one of them FAILS train, val, or both.
  This is the round's one genuinely conclusive result: on the dataset
  with enough history to test this system honestly, it does not show a
  survivable edge in any of the 18 configuration variants tried.

The strategy's testable content — body-based market structure, break-
and-retest, engulfing-candle confirmation — is a coherent, codeable
system, more internally consistent than round 72's TJR video in terms
of having ONE mechanism instead of several loosely related steps. But
it is also a system whose author demonstrates it exclusively on forex
pairs this repo has only ~2 years of history for, which is not enough
history for its own natural trade frequency to clear an honest
train/val floor. The one market where a fair test WAS possible (BTC)
returned a clean, uniform FAIL. Nothing here should feed the live
program or an R71-style iteration without either (a) a paid intraday
data source that would let a truer 3-4 tier version of his system run
on his actual forex pairs, or (b) accepting the BTC transfer result as
the best available signal, which points away from this system, not
toward it.

## 9. Biggest caveats (read before acting on anything above)

1. **The sample-size problem is the headline finding, not a footnote.**
   90 of 106 configs (85%) are INSUFFICIENT-SAMPLE. This is fundamentally
   different from round 72, where every dataset had at least a partial
   fair test. Here, only BTC does — and his own real trades never touch
   BTC.
2. **The two-tier daily/4h collapse is the dominant source of
   uncertainty**, same category of gap as round 72's index collapse but
   compounded: his real stack (weekly/daily/4H context, then 1H/30m/15m
   entry) has FOUR MORE stages than what's tested here. A true replicate
   would very plausibly trade more often and could behave differently.
3. **His two most-traded real pairs (GBPCHF, USDJPY) got the LEAST
   conclusive test of anything in this round** — the instruments with
   the strongest claim to being "his actual system" are exactly the ones
   this repo's data depth cannot honestly evaluate.
4. **No looks were spent on the sealed 20% test slice for ANY config** —
   moot here since there are zero survivors to spend a look on.
5. **The AOI multi-touch zone-construction stage is skipped entirely**,
   anchored instead to the raw broken structure level. His own
   description of AOI touch-counting is already discretionary in
   practice, so this is a reasonable simplification, but it is still a
   real, stated gap from his full method.
6. **Retest tolerance (0.35%), armed window (36 4h bars / ~6 days), and
   max hold (240h) are all fixed, stated approximations**, not swept —
   none of them are numbers he ever states himself (pips don't translate
   across instruments; his own retest/hold timing is never given a
   general rule).
7. **His "$100 into a million" narrative was never a testable claim in
   the first place** — it is a narrated account-flip with a gut-feel,
   non-formulaic, escalating-then-de-escalating risk-per-trade schedule
   (100% down to "never below 35%"), and he himself walks back the
   literal framing on camera ("I technically took $300,000 into a
   million"), including at least one mid-challenge account blow-up. No
   formalization of "risk per trade" was attempted for this reason —
   flagged UNSPECIFIED, not guessed, same discipline as round 72's
   identical gap for TJR.
8. **Costs for the forex leg are a reasoned approximation
   (~1.8bps RT), not a measured one** — no forex venue cost data exists
   anywhere in this repo. If real retail spreads run wider (market-maker
   brokers, off-hours, minor crosses), the already-sparse forex results
   above would only get worse, never better.
