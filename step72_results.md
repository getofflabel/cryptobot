# step72_results.md — round 72: THE TJR 2026 STRATEGY, gauntleted

Companion files: `step72_tjr_rules.md` (transcript distillation, quotes,
mechanical-vs-discretionary table), `step72_tjr.py` (the code that
produced every number below — its module docstring is the full
formalization spec, read it for exact definitions). Raw grid:
`step72_gauntlet_full.csv` (64 rows). Session breakdown:
`step72_session_breakdown.csv`. Research only — no commits, no live
orders.

## 0. TL;DR verdict

**The mechanical core of TJR's 2026 strategy, honestly formalized and
tested, does NOT survive at his own stated parameters (1.33R target,
tight ~10:30 cutoff) on any market. A materially DIFFERENT, more
conservative version of it — extended session window (9:30-11:30 ET)
and a 1:1 R-multiple instead of his claimed 1.33 — clears the train+val
floors on NQ (7/16 configs), ES (2/16), and BTC-transfer (1/16). SPY
survives NOTHING (0/16). None of these are sealed-test-verified; they
are candidates for the lead to spend looks against, not claims of a
working live edge.** His claimed 64.29% win rate and ~1.33R never
materialize in the mechanical build anywhere — realized pooled win
rates sit in the 42-58% band, and the R-multiple that actually performs
best is 1.0, not his stated 1.33. Trade frequency in the mechanical
build (0.05-0.33 trades/day) is far sparser than what four back-to-back
"winning day" walkthroughs in the video imply. Both of TJR's own
absolute rules (index alignment, the ~10:30 cutoff) turn out to be far
softer in the honest test than he presents them: the alignment filter
HURTS ES and SPY and barely matters for NQ; extending the cutoff past
his stated time helps almost everywhere.

## 1. What he actually teaches (full distillation in step72_tjr_rules.md)

Four-step sequence, ES+NQ paired, day-trading index futures:
1. **Draw on liquidity** — price pushes through a session/1h/4h high or
   low ("push above a high" to fill resting orders).
2. **5-minute confirmation** — BOS or inverse-FVG in the reversal
   direction.
3. **5-minute continuation** — equilibrium/FVG fill, which he himself
   simplifies into...
4. **1-minute entry** — retrace BOS (against the new direction) THEN a
   continuation BOS (with it) = the actual entry.
Stop beyond the retracement swing point; target = the next draw on
liquidity, partials + move-to-breakeven. Hard filter: ES and NQ must
show the SAME 5-minute direction or no trade. Soft rule: no pre-market,
roughly done by 10:30am ET if nothing lines up (he trades past that in
at least one worked example). Claimed: 64.29% win rate, ~1.33R,
$700k+/year. No risk-per-trade %, no news filter, no day-of-week filter
anywhere in the transcript.

## 2. Formalization — the two builds and their fidelity gaps

**INDEX (NQ=F, ES=F, SPY), 1h, 730d.** yfinance caps intraday history at
~60d below 1h — an honest 60/20/20 gauntlet is only possible at 1h.
This forces the BIGGEST approximation in the whole round: steps 2, 3,
and 4 (5-minute confirm, 5-minute continuation, 1-minute entry) cannot
be separately expressed at 1h resolution and COLLAPSE into a single
event — a 1h BOS or inverse-FVG, in the reversal direction, occurring
within 48 bars after a session/1h/4h level break, IS the entry. There is
no separate retrace-then-continuation stage for index. This is stated
loudly because it is the single most consequential simplification in
the file — it plausibly both suppresses trade count (a real 5m/1m
cascade would fire more often than a 1h proxy waits for) and removes
exactly the "wait for the pullback, don't chase" discipline that is
half of TJR's own point.

**BTC (+ETH as the alignment partner), 6y deep cache.** Gets the fuller
three-tier build: 1h context (session/1h/4h levels) -> 15m structure
(his "5-minute": BOS/IFVG reversal confirm) -> 5m entry (his
"1-minute": retrace-BOS then continuation-BOS). This is a ONE-TIER-UP
transfer (his 5m -> our 15m, his 1m -> our 5m) because there is no
1-minute BTC cache — stated plainly, not hidden. Session windows are
the SAME fixed UTC clock times as index (13:30-14:30 / 13:30-15:30 UTC)
even though BTC trades 24/7 and has no real "NY session" — this is
exactly what "sessions mapped -> same UTC windows" was asked to test:
does a human session concept transfer to a market with none of its own?

**Both builds share:** stop = nearest confirmed swing extreme opposite
the trade direction, TRAIN-median-fixed as a %, capped [0.15%, 6.0%]
(this repo's standard per-trade-dynamic-distance approximation since
round 17/41/43/56 — run_backtest takes one fixed stop_pct per run).
Target = R-multiple x stop_pct, swept over {1.0, 1.33, 2.0, 3.0} —
1.33 is his own stated realized R, the others bracket it. Max hold
fixed at 4h (every worked video example resolves same-session).
Costs: index = 2bps taker RT (step60's FUT_COSTS: 0.5bps fee + 0.5bps
slip, 0 spread/funding), SPY = 4bps RT (ETF_COSTS, its own honest ETF
cost, not force-fit down to futures pricing), BTC = 12bps taker RT +
REAL funding (fee_bps=6.0, 0 spread/slip, align_funding from
step11_round6).

## 3. Full gauntlet (64 configs — 16 per dataset x 4 datasets)

Selection rule: TRAIN expectancy > 0 AND VAL expectancy > 0, with
tr_n>=30 and va_n>=8 = SURVIVOR. The sealed 20% test window was NEVER
computed by this script for any config — score() only ever touches
[0:i_tr] and [i_tr:i_va]. `tr_exp`/`va_exp` are $/trade on the repo's
standard $10,000 paper account, full-equity size_frac=1.0 (small
absolute numbers are expected given sub-1-2% stops — read the SIGN and
the relative ranking, not the dollar magnitude, as the evidence).

### NQ (1h, 730d, 2024-03 -> 2026-07 — REGIME-THIN, one continuation regime)

| config | stop% | target% | tr_n | tr_exp | tr_win% | va_n | va_exp | va_win% | pooled_win% | pooled_RR | tr/day | verdict |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---|
| tight align=ON R1.00 | 0.68 | 0.68 | 96 | 3.81 | 52.08 | 38 | -2.79 | 50.00 | 51.49 | 1.03 | 0.19 | FAIL |
| tight align=ON R1.33 | 0.68 | 0.90 | 96 | 0.52 | 48.96 | 38 | -1.60 | 50.00 | 49.25 | 1.03 | 0.19 | FAIL |
| tight align=ON R2.00 | 0.68 | 1.36 | 96 | 2.88 | 48.96 | 38 | -2.26 | 50.00 | 49.25 | 1.10 | 0.19 | FAIL |
| tight align=ON R3.00 | 0.68 | 2.04 | 96 | 2.36 | 47.92 | 38 | -1.84 | 50.00 | 48.51 | 1.12 | 0.19 | FAIL |
| tight align=OFF R1.00 | 0.68 | 0.68 | 118 | 5.66 | 55.08 | 45 | -2.50 | 48.89 | 53.37 | 1.02 | 0.23 | FAIL |
| tight align=OFF R1.33 | 0.68 | 0.90 | 118 | 2.66 | 51.69 | 45 | -0.50 | 48.89 | 50.92 | 1.05 | 0.23 | FAIL |
| tight align=OFF R2.00 | 0.68 | 1.36 | 118 | 4.77 | 51.69 | 45 | -1.36 | 48.89 | 50.92 | 1.10 | 0.23 | FAIL |
| tight align=OFF R3.00 | 0.68 | 2.04 | 118 | 3.83 | 50.85 | 45 | -1.00 | 48.89 | 50.31 | 1.10 | 0.23 | FAIL |
| **ext align=ON R1.00** | 0.77 | 0.77 | 129 | 2.70 | 51.16 | 53 | **2.06** | 54.72 | 52.20 | 1.03 | 0.26 | **SURVIVOR** |
| **ext align=ON R1.33 (his own R)** | 0.77 | 1.03 | 129 | 0.30 | 49.61 | 53 | **3.64** | 54.72 | 51.10 | 1.02 | 0.26 | **SURVIVOR** |
| **ext align=ON R2.00** | 0.77 | 1.54 | 129 | 2.53 | 49.61 | 53 | **0.90** | 54.72 | 51.10 | 1.05 | 0.26 | **SURVIVOR** |
| **ext align=ON R3.00** | 0.77 | 2.31 | 129 | 2.41 | 48.84 | 53 | **2.33** | 54.72 | 50.55 | 1.09 | 0.26 | **SURVIVOR** |
| **ext align=OFF R1.00** | 0.76 | 0.76 | 166 | 2.52 | 52.41 | 67 | **0.16** | 50.75 | 51.93 | 1.01 | 0.33 | **SURVIVOR** |
| **ext align=OFF R1.33** | 0.76 | 1.01 | 166 | 0.78 | 50.60 | 67 | **2.15** | 50.75 | 50.64 | 1.03 | 0.33 | **SURVIVOR** |
| ext align=OFF R2.00 | 0.76 | 1.52 | 166 | 1.35 | 50.00 | 67 | -0.43 | 50.75 | 50.21 | 1.03 | 0.33 | FAIL |
| **ext align=OFF R3.00** | 0.76 | 2.28 | 166 | 0.81 | 49.40 | 67 | **0.68** | 50.75 | 49.79 | 1.04 | 0.33 | **SURVIVOR** |

NQ is the strongest dataset by far: 7 of 16 survive, ALL in the
extended session window, split roughly evenly across alignment on/off
and across R-multiples.

### ES (1h, 730d, 2024-03 -> 2026-07 — same window as NQ, REGIME-THIN)

| config | stop% | target% | tr_n | tr_exp | tr_win% | va_n | va_exp | va_win% | pooled_win% | pooled_RR | tr/day | verdict |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---|
| tight align=ON R1.00 | 0.52 | 0.52 | 97 | -2.23 | 47.42 | 28 | -0.09 | 57.14 | 49.60 | 0.91 | 0.18 | FAIL |
| tight align=ON R1.33 | 0.52 | 0.69 | 97 | -4.84 | 43.30 | 28 | 1.85 | 57.14 | 46.40 | 0.95 | 0.18 | FAIL |
| tight align=ON R2.00 | 0.52 | 1.04 | 97 | -4.97 | 42.27 | 28 | 0.44 | 57.14 | 45.60 | 0.95 | 0.18 | FAIL |
| tight align=ON R3.00 | 0.52 | 1.57 | 97 | -4.47 | 42.27 | 28 | 2.29 | 57.14 | 45.60 | 1.00 | 0.18 | FAIL |
| **tight align=OFF R1.00** | 0.52 | 0.52 | 121 | 0.47 | 50.41 | 41 | **1.69** | 56.10 | 51.85 | 0.97 | 0.23 | **SURVIVOR** |
| tight align=OFF R1.33 | 0.52 | 0.69 | 121 | -1.61 | 47.11 | 41 | 4.30 | 56.10 | 49.38 | 1.02 | 0.23 | FAIL |
| tight align=OFF R2.00 | 0.52 | 1.04 | 121 | -2.78 | 46.28 | 41 | 4.52 | 56.10 | 48.77 | 0.99 | 0.23 | FAIL |
| tight align=OFF R3.00 | 0.52 | 1.56 | 121 | -2.37 | 46.28 | 41 | 4.53 | 56.10 | 48.77 | 1.01 | 0.23 | FAIL |
| ext align=ON R1.00 | 0.53 | 0.53 | 132 | -0.71 | 51.52 | 43 | 2.30 | 58.14 | 53.14 | 0.88 | 0.25 | FAIL |
| ext align=ON R1.33 | 0.53 | 0.70 | 132 | -3.58 | 47.73 | 43 | 3.28 | 58.14 | 50.29 | 0.88 | 0.25 | FAIL |
| ext align=ON R2.00 | 0.53 | 1.05 | 132 | -3.18 | 46.97 | 43 | 2.31 | 58.14 | 49.71 | 0.90 | 0.25 | FAIL |
| ext align=ON R3.00 | 0.53 | 1.58 | 132 | -2.94 | 46.97 | 43 | 3.54 | 58.14 | 49.71 | 0.93 | 0.25 | FAIL |
| **ext align=OFF R1.00** | 0.53 | 0.53 | 171 | 1.83 | 54.39 | 58 | **4.20** | 58.62 | 55.46 | 0.93 | 0.33 | **SURVIVOR** |
| ext align=OFF R1.33 | 0.53 | 0.70 | 171 | -0.97 | 51.46 | 58 | 6.16 | 58.62 | 53.28 | 0.92 | 0.33 | FAIL |
| ext align=OFF R2.00 | 0.53 | 1.05 | 171 | -1.76 | 50.29 | 58 | 4.35 | 56.90 | 51.97 | 0.91 | 0.33 | FAIL |
| ext align=OFF R3.00 | 0.53 | 1.58 | 171 | -1.58 | 50.29 | 58 | 4.99 | 56.90 | 51.97 | 0.93 | 0.33 | FAIL |

ES survives only twice, both at R1.00 with alignment OFF — the exact
OPPOSITE of TJR's stated hard rule. Every ES config with alignment ON
fails TRAIN outright.

### SPY (1h, RTH-only, 2023-08 -> 2026-07 — the ETF sibling)

| config | stop% | target% | tr_n | tr_exp | tr_win% | va_n | va_exp | va_win% | pooled_win% | pooled_RR | tr/day | verdict |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---|
| tight align=ON R1.00 | 1.18 | 1.18 | 36 | 0.01 | 52.78 | 18 | -18.65 | 27.78 | 44.44 | 0.93 | 0.06 | FAIL |
| tight align=ON R1.33 | 1.18 | 1.57 | 36 | -0.23 | 52.78 | 18 | -18.65 | 27.78 | 44.44 | 0.92 | 0.06 | FAIL |
| tight align=ON R2.00 | 1.18 | 2.36 | 36 | -0.23 | 52.78 | 18 | -18.65 | 27.78 | 44.44 | 0.92 | 0.06 | FAIL |
| tight align=ON R3.00 | 1.18 | 3.55 | 36 | -0.23 | 52.78 | 18 | -18.65 | 27.78 | 44.44 | 0.92 | 0.06 | FAIL |
| tight align=OFF R1.00 | 1.23 | 1.23 | 83 | -6.71 | 49.40 | 39 | -5.84 | 48.72 | 49.18 | 0.75 | 0.14 | FAIL |
| tight align=OFF R1.33 | 1.23 | 1.64 | 83 | -6.87 | 49.40 | 39 | -5.84 | 48.72 | 49.18 | 0.74 | 0.14 | FAIL |
| tight align=OFF R2.00 | 1.23 | 2.46 | 83 | -6.87 | 49.40 | 39 | -5.84 | 48.72 | 49.18 | 0.74 | 0.14 | FAIL |
| tight align=OFF R3.00 | 1.23 | 3.70 | 83 | -6.87 | 49.40 | 39 | -5.84 | 48.72 | 49.18 | 0.74 | 0.14 | FAIL |
| ext align=ON R1.00 | 1.17 | 1.17 | 62 | -4.40 | 48.39 | 32 | -12.39 | 37.50 | 44.68 | 0.87 | 0.11 | FAIL |
| ext align=ON R1.33 | 1.17 | 1.56 | 62 | -4.80 | 48.39 | 32 | -12.39 | 37.50 | 44.68 | 0.86 | 0.11 | FAIL |
| ext align=ON R2.00 | 1.17 | 2.35 | 62 | -4.80 | 48.39 | 32 | -12.39 | 37.50 | 44.68 | 0.86 | 0.11 | FAIL |
| ext align=ON R3.00 | 1.17 | 3.52 | 62 | -4.80 | 48.39 | 32 | -12.39 | 37.50 | 44.68 | 0.86 | 0.11 | FAIL |
| ext align=OFF R1.00 | 1.12 | 1.12 | 174 | -4.06 | 47.70 | 62 | -5.59 | 48.39 | 47.88 | 0.85 | 0.28 | FAIL |
| ext align=OFF R1.33 | 1.12 | 1.48 | 174 | -4.14 | 47.70 | 62 | -5.59 | 48.39 | 47.88 | 0.84 | 0.28 | FAIL |
| ext align=OFF R2.00 | 1.12 | 2.23 | 174 | -4.14 | 47.70 | 62 | -5.59 | 48.39 | 47.88 | 0.84 | 0.28 | FAIL |
| ext align=OFF R3.00 | 1.12 | 3.35 | 174 | -4.14 | 47.70 | 62 | -5.59 | 48.39 | 47.88 | 0.84 | 0.28 | FAIL |

**Zero survivors on SPY, every single config, both train and val
negative almost everywhere.** SPY's RTH-only 1h bars (no overnight/
pre-market bars at all) mean the session-level and 1h-swing geometry
built for a near-continuous futures tape behaves differently on an ETF
with a hard daily gap — the sibling instrument TJR's own audience would
actually be able to trade (via options/shares) shows no honest edge
under this formalization, in contrast to the futures proxy.

### BTC (3-tier: 1h context/15m structure/5m entry, ETH partner, 6y deep cache)

| config | stop% | target% | tr_n | tr_exp | tr_win% | va_n | va_exp | va_win% | pooled_win% | pooled_RR | tr/day | verdict |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---|
| tight align=ON R1.00 | 0.56 | 0.56 | 60 | 4.85 | 60.00 | 28 | -7.11 | 50.00 | 56.82 | 0.79 | 0.05 | FAIL |
| tight align=ON R1.33 | 0.56 | 0.74 | 60 | 2.49 | 50.00 | 28 | -18.41 | 35.71 | 45.45 | 1.04 | 0.05 | FAIL |
| tight align=ON R2.00 | 0.56 | 1.11 | 60 | 11.51 | 46.67 | 28 | -9.89 | 35.71 | 43.18 | 1.50 | 0.05 | FAIL |
| tight align=ON R3.00 | 0.56 | 1.67 | 60 | 7.26 | 38.33 | 28 | -15.14 | 28.57 | 35.23 | 1.85 | 0.05 | FAIL |
| tight align=OFF R1.00 | 0.51 | 0.51 | 118 | -4.02 | 52.54 | 42 | -2.26 | 54.76 | 53.13 | 0.76 | 0.09 | FAIL |
| tight align=OFF R1.33 | 0.51 | 0.68 | 118 | -5.67 | 44.07 | 42 | -7.10 | 45.24 | 44.38 | 1.00 | 0.09 | FAIL |
| tight align=OFF R2.00 | 0.51 | 1.02 | 118 | -3.24 | 38.98 | 42 | -13.03 | 33.33 | 37.50 | 1.38 | 0.09 | FAIL |
| tight align=OFF R3.00 | 0.51 | 1.52 | 118 | -0.55 | 34.75 | 42 | -12.87 | 28.57 | 33.13 | 1.81 | 0.09 | FAIL |
| ext align=ON R1.00 | 0.56 | 0.56 | 114 | 6.12 | 61.40 | 52 | -6.53 | 50.00 | 57.83 | 0.79 | 0.09 | FAIL |
| ext align=ON R1.33 (his own R) | 0.56 | 0.74 | 114 | 3.68 | 51.75 | 52 | -8.54 | 42.31 | 48.80 | 1.04 | 0.09 | FAIL |
| **ext align=ON R2.00** | 0.56 | 1.11 | 114 | 1.88 | 42.98 | 52 | **3.06** | 42.31 | 42.77 | 1.43 | 0.09 | **SURVIVOR** |
| ext align=ON R3.00 | 0.56 | 1.67 | 114 | 0.58 | 37.72 | 52 | -4.07 | 32.69 | 36.14 | 1.72 | 0.09 | FAIL |
| ext align=OFF R1.00 | 0.55 | 0.55 | 220 | -2.66 | 53.64 | 77 | -5.35 | 51.95 | 53.20 | 0.77 | 0.16 | FAIL |
| ext align=OFF R1.33 | 0.55 | 0.74 | 220 | -5.36 | 45.00 | 77 | -7.54 | 44.16 | 44.78 | 0.99 | 0.16 | FAIL |
| ext align=OFF R2.00 | 0.55 | 1.11 | 220 | -6.78 | 37.73 | 77 | -3.83 | 38.96 | 38.05 | 1.34 | 0.16 | FAIL |
| ext align=OFF R3.00 | 0.55 | 1.66 | 220 | -7.07 | 33.64 | 77 | -4.34 | 32.47 | 33.33 | 1.65 | 0.16 | FAIL |

BTC survives exactly ONCE (extended window, alignment=ON, R2.00) out of
16 — the weakest transfer of the four datasets, and TRAIN win rate is
already under 50% before val even runs, propped up by the R:R (1.43)
rather than hit rate. Interesting note: TRAIN expectancy is
POSITIVE in 10/16 BTC configs (mostly the tight-align=ON block) but VAL
almost always flips negative — a classic small-sample train-only mirage
this repo's discipline exists to catch.

## 4. Required analysis 1 — performance by session window

If TJR's edge really lives in his stated hours, the TIGHT window
(9:30-10:30 ET, his literal "by 10:30 I'm done") should be at least as
strong as the extended one. It is not, anywhere:

| dataset | mean va_exp, TIGHT | mean va_exp, EXTENDED |
|---|---:|---:|
| NQ | -1.73 | +1.44 |
| ES | +2.44 | +3.89 |
| SPY | -12.25 | -8.99 |
| BTC | -10.73 | -4.64 |

Every single dataset does better (or less bad) in the EXTENDED window.
The entry-hour histogram (`step72_session_breakdown.csv`) explains why:
actual entries cluster almost entirely in UTC hour 15 (fills land
14:30-15:30 UTC, i.e. ~10:00-11:00am ET — the SECOND half of his own
extended window), not right at the open. Because the mechanical build
requires the full break -> confirm -> (retrace+continuation, for BTC)
cascade to resolve, most valid setups simply haven't finished forming
by 10:30 ET. **His edge, as best we can mechanize it, does NOT live
concentrated in his own stated hours — it needs the extra hour he
treats as an exception, not the rule.**

## 5. Required analysis 2 — discretionary-gap sensitivity (the honesty measure)

The cross-index/cross-instrument alignment filter is the ONE rule TJR
states as an absolute ("I don't want anything to do with this today").
Testing it on/off:

| dataset | mean va_exp, align=ON | mean va_exp, align=OFF |
|---|---:|---:|
| NQ | +0.06 | -0.35 |
| ES | +1.99 | +4.34 |
| SPY | -15.52 | -5.72 |
| BTC | -8.33 | -7.04 |

Alignment ON is the WORSE choice on 3 of 4 datasets (ES, SPY, and BTC
by a smaller margin) and only marginally better on NQ. On SPY
specifically, requiring alignment is catastrophic (-15.52 vs -5.72
mean). **The single hardest rule in the transcript does not survive
contact with an honest gate/no-gate comparison** — it is not obviously
adding real signal in this formalization; it mostly just cuts sample
size on markets where the un-gated version was already the stronger
config. This is the discretionary-sensitivity finding the round asked
for: his one "always" rule swings outcomes by more than most of the
swept parameters, and swings them in the WRONG direction more often
than the right one.

## 6. Required analysis 3 — trades/day vs. his claimed cadence

Realized trade frequency in the mechanical build, pooled train+val:

| dataset | tr/day range | tr/day mean |
|---|---:|---:|
| NQ | 0.19 - 0.33 | 0.25 |
| ES | 0.18 - 0.33 | 0.25 |
| SPY | 0.06 - 0.28 | 0.15 |
| BTC | 0.05 - 0.16 | 0.10 |

That is roughly **one trade every 3-5 trading days** on the index
futures, and rarer still on the BTC transfer — nothing close to a
setup most days, which is the impression four back-to-back "winning
day" chart walkthroughs in the video leave (he does show one explicit
no-trade day and one where alignment never resolves, so SOME skip days
are expected, but not this many). The INDEX 15m/60d SMOKE check
(`step72_tjr.py`'s `smoke_index_15m`, NOT gauntleted) supports that
this gap is largely a resolution artifact of the 1h collapse, not
necessarily a fact about the real strategy: at 15m resolution the RAW
level-break+BOS/IFVG event rate is ~350-360 events over 72.6 days on
both NQ=F and ES=F (~5/day raw), collapsing to ~43-46 events after the
session-window filter (~0.6/day) — an order of magnitude denser than
the 1h gauntlet's ~0.25/day. A true 5m/1m build (which we cannot
gauntlet honestly — yfinance's 60d cap) would very plausibly trade
closer to his implied cadence; the 1h collapse is the likely main
cause of the gap, not proof his real cadence is fictional.

## 7. Required analysis 4 — R:R / win-rate profile vs. his claims

Claimed: 64.29% win rate, ~1.33R. Pooled (train+val) at his own R1.33
configs, across all 4 datasets and both filter dimensions:

| dataset | pooled_win% range at R1.33 | pooled_RR range at R1.33 |
|---|---:|---:|
| NQ | 49.3 - 51.1 | 1.02 - 1.05 |
| ES | 46.4 - 53.3 | 0.92 - 1.02 |
| SPY | 44.4 - 49.2 | 0.74 - 0.92 |
| BTC | 44.4 - 48.8 | 1.00 - 1.04 |

**No dataset, no config, at any point in the grid gets within 6 points
of his 64.29% win rate.** Realized win rates cluster tightly around
42-58% everywhere — a coin flip with a small edge, not the strongly
favorable coin he describes. Realized R:R at the R1.33 TARGET setting
comes in BELOW 1.33 almost everywhere (0.74-1.05), because the
train-median-fixed stop is wider or the target is missed more often
than his per-trade dynamic version would be — expected, given the
stated stop-sizing approximation. More strikingly, **R1.33 is not even
the best-performing R-multiple in this grid** — R1.00 (a flat 1:1) is
the single most common survivor configuration across NQ, ES, and BTC.
If the mechanical core has real edge, it is concentrated in low-R,
higher-frequency-ish exits, not the extended 1.33R holds he describes
verbally.

## 8. Verdict

**Does the mechanical core of TJR-2026 survive honest testing?**
Partially, and only after moving away from his own literal parameters.
- **NQ futures**: the strongest result — 7/16 configs clear train+val,
  concentrated in the extended session window, spanning both alignment
  settings and R1.00/1.33/2.00/3.00. This is the one dataset worth a
  sealed test look.
- **ES futures**: 2/16 survive, both at R1.00 with alignment OFF —
  directly contradicting his stated hard rule. Weaker but present.
- **SPY (the ETF a retail viewer could actually trade)**: 0/16. No
  honest edge in this formalization at all.
- **BTC transfer**: 1/16, propped up by R:R not win rate, TRAIN win
  rate already under 50%. Weakest of the four — the strategy does not
  meaningfully transfer to crypto under the same UTC session windows.

The strategy's genuine, testable content — session/HTF liquidity levels
+ lower-timeframe BOS/IFVG reversal confirmation — shows SOME honest
signal on index futures, but not at the win rate, R:R, cadence, or
exact rule-set (especially the cross-index alignment filter and the
~10:30 cutoff) he describes on camera. The version that survives is a
materially loosened one.

## 9. Biggest caveats (read before acting on anything above)

1. **The index collapse is the dominant source of uncertainty.** Steps
   3+4 (the 5m continuation and 1m retrace-then-entry) are NOT modeled
   separately for NQ/ES/SPY — only for BTC. Everything measured on
   index futures here is really testing "level break + lower-TF BOS/
   IFVG reversal," a SUBSET of his full stack, not the whole thing.
2. **730d of 1h index data is regime-thin** (R55 convention) — one
   continuation-ish 2.4-year window, no full bear-market index test.
3. **No looks were spent on the sealed 20% test slice for ANY config**
   — every survivor above is a train+val candidate, not a validated
   edge. The lead should pick at most the NQ extended-window family for
   a sealed look, per this repo's look-discipline.
4. Session windows are FIXED UTC, not DST-adjusted — drift up to 1h
   against real ET across the year, spreading real 9:30-11:30 ET
   entries across a wider or narrower actual local window depending on
   season.
5. Stop/target are TRAIN-median-FIXED per config, not his actual
   per-trade dynamic "beyond the second high/low" — a known, stated
   repo-wide approximation, not unique to this round.
6. Risk-per-trade was never stated in the transcript and is not
   testable from this source; nothing here says anything about his
   real position sizing or the account-level drawdown that sizing
   would produce.
