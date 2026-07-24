# ROUND 55 — THE GOLD SYSTEM: multi-family, multi-timeframe edge hunt

Script: `step55_gold_system.py`. Data: `data_gold_1d.parquet`,
`data_gold_1h.parquet`, `data_gold_4h.parquet`, `data_gold_xaut_1h.parquet`.
Research only — no commits, no live orders, `gold_book.py` untouched.
114 configs tested across 5 families. Verdict counts: **23 SURVIVOR, 14
INSUFFICIENT-SAMPLE (positive both windows, under the 30/8 trade floor), 77
FAIL**. GC=F's sealed 20% test window was never sliced or scored anywhere
in this round — every number below is TRAIN or VAL. The XAUT-USDT read at
the end is a whole-history compatibility check, explicitly not a look.

## Data spans

| Instrument/TF | Bars | Span | Train ends | Val ends (test sealed) | Train yrs | Val yrs | Test yrs (sealed) | Med train ATR% |
|---|---|---|---|---|---|---|---|---|
| GC=F 1d | 6,497 | 2000-08-30 → 2026-07-23 | 2016-03-21 | 2021-05-21 | 15.56 | 5.17 | 5.17 | 1.135% |
| GC=F 1h | 13,738 | 2024-02-29 → 2026-07-24 | 2025-08-05 | 2026-01-29 | 1.43 | 0.485 | 0.479 | 0.281% |
| GC=F 4h | 3,722 | 2024-02-29 → 2026-07-24 | 2025-08-05 | 2026-01-29 | 1.43 | 0.482 | 0.482 | 0.547% |
| XAUT-USDT 1h (BloFin) | 10,961 | 2025-04-23 → 2026-07-24 | — | — (no split, transfer check only) | — | — | — | — |

**1h/4h val windows are ~5 months (~176-177 days), exactly the "regime-thin
by construction" flag the task called out up front.** Both timeframes cover
the *same* ~2.4-year calendar window (2024-02-29 → 2026-07-24) since 4h is
resampled from 1h — they are not independent samples of history, just two
different lenses on one regime (a strong 2024-26 gold bull run). Daily gets
the honest 20-year, three-decade treatment.

**Gap exposure (structural, independent of any trade taken):** GC=F 1h —
only 0.5-0.6% of bars gap more than one median-ATR% past the prior close;
4h — 0.8-1.1%. This is an order of magnitude calmer than the ETF
overnight-gap exposure found in round 47/48 (there, 44/45 GLD dip-buy stops
gapped through). Gold futures trade near-continuously; the maintenance
breaks and weekend closes exist but rarely produce a gap bigger than the
instrument's own typical hourly range. Confirmed empirically below (gap-
honesty section) — realized degradation from gap-honesty correction is
small everywhere it applies.

**5m/15m: deliberately not fetched.** yfinance's free tier caps intraday
history below 1h at ~60 calendar days. A 60/20/20 split of 60 days leaves
~12 days of val — nowhere near enough to honestly clear
MIN_TRAIN_TRADES=30/MIN_VAL_TRADES=8 for gold's native entry frequency at
any of the five families below without curve-fitting to noise. **What paid
data would unlock this:** a minute-bar futures history provider with
multi-year depth — Databento, Polygon.io's futures tier, CME's own
historical data files, or a broker's stored minute bars via Alpaca/IBKR.
With ~2-5 years of 5m/15m GC=F bars, families 3 (pullback) and 4 (session
structure) in particular would get a real gauntlet instead of a starved one.

## Per-family autopsies

### Family 1 — EMA crosses (the owner's named ask)

EMA{9/21, 20/50} on 1h/4h are genuinely good. EMA{50/200} is **structurally
too slow to ever pass the trade-count floor** on the spans available here
— gold has only had a handful of true 50/200-day golden/death crosses in
20 years, so the 60/20/20 split leaves 3-4 trades in EACH window no matter
how the parameters are tuned. Those rows show wild-looking numbers ($10k-
14k/trade, 400%+ return) because 2-3 trades each caught a multi-year
secular trend on compounding equity — **not a real edge, a sample-size
artifact.** Correctly caught by the gauntlet's own floor (INSUFFICIENT-
SAMPLE, never called SURVIVOR).

**Shorts died everywhere.** All 28 EMA-cross short-mirror configs (every
pair × every tf × every gate × every stop variant) FAILED. Reported
honestly per the task's ask: gold's secular uptrend over this data (and
over 20+ years on daily) kills the mirrored short, exactly like round 48
found for donchian shorts. Do not deploy an EMA-cross short book on gold.

**1h survivors (long only):**

| Config | Train n / exp | Val n / exp | Trades/yr (tr/va) |
|---|---|---|---|
| EMA20/50 ungated, no stop | 74 / $62.38 | 23 / $214.05 | 52 / 47 |
| EMA20/50 ungated, stop | 74 / $32.68 | 23 / $120.72 | 52 / 47 |
| EMA20/50 adaptive, no stop | 56 / $36.51 | 22 / $198.38 | 39 / 45 |
| EMA20/50 adaptive, stop | 56 / $8.48 | 22 / $131.85 | 39 / 45 |
| EMA9/21 ungated, no stop | 167 / $32.54 | 59 / $65.82 | 117 / 122 |
| EMA9/21 ungated, stop | 167 / $12.11 | 59 / $29.39 | 117 / 122 |
| EMA9/21 adaptive, no stop | 109 / $15.90 | 46 / $80.74 | 76 / 95 |
| EMA9/21 adaptive, stop | 109 / $3.54 | 46 / $29.27 | 76 / 95 |

**4h survivors:** EMA9/21 ungated no-stop (50/11, $75.36/$442.84),
EMA9/21 ungated stop (50/11, $27.63/$409.31), EMA9/21 adaptive no-stop
(30/10, $18.98/$418.34). EMA20/50 on 4h fell one val trade short of the
floor (5 vs 8 needed) — INSUFFICIENT-SAMPLE, not a fail, worth another
look once more 4h history accrues.

**Pattern across the board:** the vol gate and the ATR stop both *cost*
raw $/trade (fewer, more selective entries or an earlier exit) while val
consistently outperforms train by 2-4x. That asymmetry is the friendly
direction (no train-fit-not-generalizing smell) but it is still a
regime-thin ~5-month val window sitting inside one strong gold bull run —
treat the magnitude as optimistic, the sign and the large train-side
sample (56-167 trades) as the trustworthy part.

### Family 2 — intraday breakouts: does the daily winner fractal down? YES.

The incumbent shape (donchian{20,55} + EMA20 exit) **survives at 1h AND 4h
too**, not just daily:

| TF | Config | Train n/exp | Val n/exp | Trades/yr (tr/va) |
|---|---|---|---|---|
| 1d (incumbent-reference) | donchian20 | 89 / $57.51 | 24 / $95.09 | 5.7 / 4.6 |
| 1d (incumbent-reference) | donchian55 | 55 / $41.95 | 14 / $111.61 | 3.5 / 2.7 |
| 1h | donchian20 | 152 / $25.21 | 55 / $41.94 | 106 / 113 |
| 1h | donchian55 | 90 / $34.02 | 39 / $55.84 | 63 / 80 |
| 4h | donchian20 | 41 / $58.37 | 17 / $192.86 | 29 / 35 |
| 4h | donchian55 | 32 / $2.84 | 14 / $196.48 | 22 / 29 |

The 1d incumbent-reference rows reproduce gold_book.py's already-sealed
numbers almost exactly under this round's own harness (good sanity check
that GOLD_COSTS/split_points match the live book's convention). donchian55
on 4h is the weakest of the four fractal-down survivors — train is barely
positive ($2.84/trade over 32 trades) even though val looks great; treat
it as a marginal pass, not a strong one. donchian20 on both 1h and 4h is
solidly positive on both sides with real sample size. **Short-mirror
failed on every timeframe** (1h, 4h, and the 1d incumbent-reference row),
same pattern as family 1.

### EMA-cross vs incumbent-donchian head-to-head (identical GOLD_COSTS, identical 1d split)

| Config | Train n/exp | Val n/exp | Verdict |
|---|---|---|---|
| donchian20 EMA20exit (long) | 89 / $57.51 | 24 / $95.09 | **SURVIVOR** |
| donchian55 EMA20exit (long) | 55 / $41.95 | 14 / $111.61 | **SURVIVOR** |
| EMA50/200 long, every gate/stop combo | 3-4 trades each window | 3-4 trades each window | FAIL or INSUFFICIENT-SAMPLE |

**On daily, donchian wins outright — EMA crosses do not earn a slot.**
Not because the EMA shape is bad, but because 50/200 is the only daily
pair the task specified, and gold's daily 50/200 cross frequency is too
low for 20 years of data to ever produce a trustworthy sample on either
side of a 60/20/20 split. This is a data-availability verdict, not a
strategy-quality one.

**On 1h, the finding flips: EMA20/50 and EMA9/21 both survive, and
EMA20/50's $/trade (train $62.38, val $214.05, ungated/no-stop) is
noticeably better than donchian20's ($25.21/$41.94) or donchian55's
($34.02/$55.84) on the same timeframe.** EMA crosses earn a real slot —
just on intraday timeframes, not daily.

### Family 3 — pullback-in-trend: dead, buried

All 16 configs (RSI{2,3} × threshold{10,15} × stop{0.5,0.8}xATR ×
target{2,3}xstop, above the shift-safe-mapped daily SMA50) FAILED. The
closest to daylight — RSI2<15, stop 0.8xATR, target 3xstop — got train to
a barely-positive $1.58/trade (n=127) but val was solidly negative
(-$4.76, n=47). No variant cleared both windows. Bury this family; it does
not need a re-look with different parameters (protocol: never re-tune a
failed shape).

### Family 4 — session structure: the hypothesized "likeliest real edge" did NOT pan out (at 1h, with these definitions)

| Sub-family | Config | Train exp | Val exp | Verdict |
|---|---|---|---|---|
| London-open momentum | hold4h | -$0.86 (n=354) | -$1.43 (n=120) | FAIL |
| London-open momentum | hold8h | -$2.98 (n=354) | +$4.54 (n=120) | FAIL |
| NY-open momentum | hold4h | -$0.56 (n=358) | +$10.08 (n=120) | FAIL |
| NY-open momentum | hold8h | -$0.81 (n=358) | +$8.00 (n=120) | FAIL |
| Asia-range breakout | tgt1.5x range | +$2.08 (n=332) | -$10.63 (n=103) | FAIL |
| Asia-range breakout | tgt2.5x range | +$2.75 (n=332) | -$1.44 (n=103) | FAIL |

Every config failed the "both windows positive" bar. Two interesting
near-misses worth noting for a future round rather than a re-look on this
same window: NY-open momentum's train sits almost exactly at zero
(-$0.56 to -$0.81) while val is clearly positive ($8-10/trade, n=120) —
the opposite sign-flip pattern from Asia-range breakout, whose train is
modestly positive and val clearly negative. Neither is tradeable as
specified. **Honest verdict: on 1h GC=F over this ~2.4-year window, none
of the three session-structure hypotheses (London momentum, NY momentum,
Asia-range breakout) produced a robust edge with a straightforward
directional/timed-exit read.** This does not rule out session structure
generally — a volume/liquidity-aware version, a different hold window, or
testing across more regimes (which needs longer 1h history than yfinance
currently gives GC=F) could still find something. As tested here, it is
the round's clearest negative result for a family the task called out as
the most promising.

### Family 5 — mean reversion: the strongest NEW daily edge this round

**Daily z-score mean reversion is a genuine, decade-consistent, non-
donchian edge:**

| Config | Train n/exp | Val n/exp | Trades/yr | 2000s / 2010s / 2020s expectancy |
|---|---|---|---|---|
| z24<-1.5, ungated | 98 / $32.40 | 37 / $41.34 | 6.3 / 7.2 | +$62.14 / +$23.69 / +$18.01 |
| z24<-1.5, calm-gated | 41 / $47.17 | 24 / $55.18 | 2.6 / 4.6 | +$114.71 / +$22.66 / +$261.12 |
| z48<-1.5, ungated | 66 / $22.48 | 29 / $22.88 | 4.2 / 5.6 | +$58.27 / +$3.93 / +$46.35 |
| z48<-1.5, calm-gated | 38 / $43.93 | 19 / $5.77 | 2.4 / 3.7 | +$151.64 / **-$15.00** / +$227.94 |
| z24<-2.0, ungated | 59 / $15.02 | 24 / $2.61 | 3.8 / 4.6 | +$40.80 / **-$1.58** / **-$16.00** |

**z24<-1.5 ungated is the standout**: biggest sample (98/37 trades),
positive expectancy in all three decades with no exceptions, and val
confirms train almost exactly ($41.34 vs $32.40 — the healthy, boring
kind of consistency, not a dramatic val outperformance to be suspicious
of). z24<-1.5 calm-gated (the `adaptive_vol_gate(direction="below")`
filter, i.e. only take mean-reversion entries when vol is BELOW its own
trailing median — the mirror-image of the trend family's "above" lively
gate) roughly *raises $/trade by 40-50%* at the cost of *less than half
the trade count* — a real, sensible signal (mean reversion works better
away from chaos), but z48<-1.5 calm-gated's 2010s decade goes solidly
negative (-$15.00), and z24<-2.0 ungated is negative in 2 of 3 decades
despite technically clearing the SURVIVOR bar overall — both of those are
demoted below the two z24<-1.5 configs in the ranking below.

**Intraday mean reversion also produced one small, clean survivor:**
z48<-2.0 ungated on 1h (target 1.23%, stop 0.42% = 1.5x median train
ATR%): train 62 trades/$3.42, val 19 trades/$8.80. Small $/trade but
gap-honesty confirms ZERO gapped-through stops in either window — a
clean, if modest, intraday complement. 4h mean reversion did not survive
anywhere (sample too thin at that resolution for a z-score entry that's
already fairly rare).

## Gap-honesty (stops on GC=F 1h/4h)

Applied to every stop-bearing 1h/4h config (`step48`'s
`gap_honesty_correction`, imported verbatim — fills AT THE OPEN when a
bar's open had already gapped through the stop level before the bar
started). **The effect is small everywhere it applies**: most configs show
ZERO gapped-through trades in either window; where gaps did occur (mostly
the FAILED short-side EMA configs), the degradation tops out around
-$1.7/trade (EMA20/50 short, 4h, train side) and is usually under
-$0.5/trade. None of the 23 SURVIVORs flip sign or lose SURVIVOR status
under gap-honesty. This is the opposite finding from round 47/48's ETF
overnight-gap blowups — gold futures' near-continuous session structure
just doesn't produce large stop-busting gaps at the 1h/4h resolution,
confirmed empirically rather than assumed.

## XAUT-USDT venue-transfer check (survivors only, whole-history read, NOT a validation split)

10,961 1h bars, 2025-04-23 → 2026-07-24 (BloFin's actual listing history —
a young venue). BLOFIN_COSTS (repo default: 6bp taker/2bp maker/1bp
spread/2bp slippage/1bp funding), not GOLD_COSTS — this is what the real
position would actually cost on that venue.

| Family | Config | XAUT n / exp | GC=F train exp | GC=F val exp | Transfer? |
|---|---|---|---|---|---|
| 1-ema-cross | EMA20/50 adaptive, no stop | 63 / **+$26.07** | $36.51 | $198.38 | **HOLDS** |
| 1-ema-cross | EMA20/50 ungated, no stop | 98 / **+$9.92** | $62.38 | $214.05 | **HOLDS** |
| 1-ema-cross | EMA20/50 adaptive, stop | 63 / **+$17.18** | $8.48 | $131.85 | **HOLDS** |
| 1-ema-cross | EMA20/50 ungated, stop | 98 / **+$7.89** | $32.68 | $120.72 | **HOLDS** |
| 1-ema-cross | EMA9/21 adaptive, no stop | 133 / **+$3.39** | $15.90 | $80.74 | HOLDS (thin) |
| 1-ema-cross | EMA9/21 adaptive, stop | 133 / -$11.25 | $3.54 | $29.27 | fails |
| 1-ema-cross | EMA9/21 ungated, no stop | 230 / -$5.20 | $32.54 | $65.82 | fails |
| 1-ema-cross | EMA9/21 ungated, stop | 230 / -$10.03 | $12.11 | $29.39 | fails |
| 2-breakout | donchian20 EMA20exit long | 215 / -$9.98 | $25.21 | $41.94 | fails |
| 2-breakout | donchian55 EMA20exit long | 125 / -$3.81 | $34.02 | $55.84 | fails |
| 5-meanrev | z48<-2.0 ungated 1h | 93 / -$9.89 | $3.42 | $8.80 | fails |

**EMA20/50 is the only shape that holds up across every one of its
variants (4/4 positive on XAUT).** EMA9/21 is a mixed bag (only the
adaptive/no-stop variant holds). Both donchian-1h configs and the intraday
mean-reversion survivor flip negative on XAUT. Read this as a genuine,
if small-sample, differentiator — not as a condemnation of the configs
that "failed" here, since XAUT-USDT is a young synthetic listing with its
own (still-thin) liquidity and cost structure, and this is explicitly a
compatibility check, never a validation.

## Full config table

Complete 114-row table with every stop/target/verdict is in this round's
stdout capture; the actionable subset (23 SURVIVOR + 14 INSUFFICIENT-
SAMPLE = 37 rows) is reproduced in full below with trades/yr added.
Constants used: 1d train=15.56yr/val=5.17yr; 1h & 4h train=1.43yr,
1h val=0.485yr, 4h val=0.482yr.

**SURVIVORS (23):**

| Family | Config | TF | Stop% | Target% | Train n/exp/yr | Val n/exp/yr | Med hold (h) |
|---|---|---|---|---|---|---|---|
| 1-ema-cross | EMA9/21 long adaptive stop | 1h | 0.421 | — | 109/$3.54/76 | 46/$29.27/95 | 9 |
| 1-ema-cross | EMA9/21 long adaptive nostop | 1h | — | — | 109/$15.90/76 | 46/$80.74/95 | 27 |
| 1-ema-cross | EMA9/21 long ungated stop | 1h | 0.421 | — | 167/$12.11/117 | 59/$29.39/122 | 10 |
| 1-ema-cross | EMA9/21 long ungated nostop | 1h | — | — | 167/$32.54/117 | 59/$65.82/122 | 25 |
| 1-ema-cross | EMA20/50 long adaptive stop | 1h | 0.421 | — | 56/$8.48/39 | 22/$131.85/45 | 13 |
| 1-ema-cross | EMA20/50 long adaptive nostop | 1h | — | — | 56/$36.51/39 | 22/$198.38/45 | 78 |
| 1-ema-cross | EMA20/50 long ungated stop | 1h | 0.421 | — | 74/$32.68/52 | 23/$120.72/47 | 20 |
| 1-ema-cross | EMA20/50 long ungated nostop | 1h | — | — | 74/$62.38/52 | 23/$214.05/47 | 84 |
| 1-ema-cross | EMA9/21 long adaptive nostop | 4h | — | — | 30/$18.98/21 | 10/$418.34/21 | 140 |
| 1-ema-cross | EMA9/21 long ungated stop | 4h | 0.821 | — | 50/$27.63/35 | 11/$409.31/23 | 60 |
| 1-ema-cross | EMA9/21 long ungated nostop | 4h | — | — | 50/$75.36/35 | 11/$442.84/23 | 140 |
| 2-breakout | donchian20 EMA20exit long | 1h | — | — | 152/$25.21/106 | 55/$41.94/113 | 17 |
| 2-breakout | donchian55 EMA20exit long | 1h | — | — | 90/$34.02/63 | 39/$55.84/80 | 25 |
| 2-breakout | donchian20 EMA20exit long | 4h | — | — | 41/$58.37/29 | 17/$192.86/35 | 96 |
| 2-breakout | donchian55 EMA20exit long | 4h | — | — | 32/$2.84/22 | 14/$196.48/29 | 92 |
| 2-breakout | donchian20 EMA20exit (incumbent-ref) | 1d | — | — | 89/$57.51/5.7 | 24/$95.09/4.6 | 456 |
| 2-breakout | donchian55 EMA20exit (incumbent-ref) | 1d | — | — | 55/$41.95/3.5 | 14/$111.61/2.7 | 456 |
| 5-meanrev | z48<-2.0 ungated tgt1.23% stop0.42% | 1h | 0.421 | 1.232 | 62/$3.42/43 | 19/$8.80/39 | 4 |
| 5-meanrev | z24<-1.5 calm-gated tgt2% stop1.70% | 1d | 1.702 | 2.0 | 41/$47.17/2.6 | 24/$55.18/4.6 | 192 |
| 5-meanrev | z24<-1.5 ungated tgt2% stop1.70% | 1d | 1.702 | 2.0 | 98/$32.40/6.3 | 37/$41.34/7.2 | 120 |
| 5-meanrev | z24<-2.0 ungated tgt2% stop1.70% | 1d | 1.702 | 2.0 | 59/$15.02/3.8 | 24/$2.61/4.6 | 120 |
| 5-meanrev | z48<-1.5 calm-gated tgt2% stop1.70% | 1d | 1.702 | 2.0 | 38/$43.93/2.4 | 19/$5.77/3.7 | 168 |
| 5-meanrev | z48<-1.5 ungated tgt2% stop1.70% | 1d | 1.702 | 2.0 | 66/$22.48/4.2 | 29/$22.88/5.6 | 144 |

**INSUFFICIENT-SAMPLE (14, positive both windows, under the 30/8 floor):**
EMA50/200 in every tf (1h/4h/1d, all gate/stop combos that had positive
both sides) — structurally sample-starved, see Family 1 autopsy. EMA20/50
4h (3 of its 4 combos, one val trade short of the floor). Three thin
mean-reversion configs (z24<-2.0 calm-gated 1h, z48<-2.0 calm-gated 1h,
z24<-1.5 calm-gated 4h, z24<-2.0 calm-gated 1d) — the calm-gate's
selectivity pushed sample size just under the bar in the smaller-history
timeframes; worth a re-look once more calendar time accrues, not a
re-tune.

**FAIL (77):** every family-1 short-mirror config (28), every family-2
short-mirror config (8), all 16 family-3 pullback configs, all 6 family-4
session-structure configs, the remaining EMA-cross/mean-reversion combos
that didn't clear both windows. Full per-row numbers are in the script's
stdout; nothing here needs re-tuning per protocol (never re-tune a failed
shape with different parameters on the same window).

## Ranked sealed-look candidates

1. **5-meanrev z24<-1.5 ungated, daily (GC=F).** The round's strongest
   genuinely NEW gold edge. Biggest sample of any non-donchian survivor
   (98 train / 37 val), positive in all three decades with no exceptions,
   train and val agree closely ($32.40 vs $41.34 — healthy, not
   suspicious). Structurally different from the incumbent (reversion, not
   breakout) — real portfolio diversification, not a restatement of the
   same edge. **Top candidate for a sealed look.**
2. **5-meanrev z24<-1.5 calm-gated, daily (GC=F).** Same core edge as #1
   with the below-median-vol filter applied: $/trade jumps ~45% (to
   $47.17/$55.18) at the cost of more than half the sample (41/24 vs
   98/37). Worth a look as a refinement, but rank it behind #1 given the
   thinner sample — if the lead only spends one look on mean reversion,
   spend it on #1.
3. **1-ema-cross EMA20/50 long, 1h, ungated, no stop.** Best $/trade in
   the whole EMA-cross family (train $62.38/74t, val $214.05/23t) AND the
   only shape that survived venue-transfer to XAUT-USDT across all four of
   its stop/gate variants. The clearest answer to "did EMA crosses earn a
   slot" — yes, on 1h, convincingly.
4. **2-breakout donchian20 EMA20exit, 1h (GC=F).** Not a new edge, but
   proof the incumbent's exact shape fractals down to hourly with a real
   sample (152/55 trades) and strong economics. A faster companion book
   trading the identical, already-trusted logic at higher turnover — lower
   research risk than any brand-new family, since the shape is already
   sealed-validated once on daily.
5. **1-ema-cross EMA9/21 long, 1h, ungated, no stop.** Weaker $/trade
   than #3 but by far the largest sample in the whole round (167 train /
   59 val trades) — the config to trust most on statistical grounds alone,
   and it also transfers positively to XAUT (thin, +$3.39/trade).
6. **2-breakout donchian20 EMA20exit, 4h (GC=F).** Second fractal-down
   confirmation, smaller sample (41/17) but both windows strongly
   positive — a lower-turnover alternative to #4 if the lead wants less
   trading frequency than 1h.
7. **5-meanrev z48<-2.0 ungated, 1h (GC=F).** Small but clean intraday
   mean-reversion complement (62/19 trades, gap-honesty confirms zero
   gapped stops). Lowest priority of the survivors — modest $/trade and
   it did not transfer to XAUT — but a legitimate third timeframe/edge-type
   diversifier if the lead wants one.

**Explicitly NOT recommended for a look:** every EMA-cross and donchian
short-mirror (0/36 combined survived — gold's uptrend kills them cleanly,
confirmed exactly as the task asked); family 3 pullback-in-trend (0/16);
family 4 session structure (0/6); EMA50/200 on any timeframe (structurally
sample-starved, not a real verdict either way); donchian55 EMA20exit 4h
(technically SURVIVOR but train barely positive at $2.84/trade — the
weakest pass in the whole table).

## Plain-English: what the Gold System should look like

The existing live book (donchian20/55 + EMA20 exit, daily) stays the
foundation — this round didn't dethrone it, it reproduced its numbers
almost exactly and then found it generalizes further than anyone had
checked. The system this round argues for is **three layers stacked by
speed, not one book replaced by another:**

- **The slow layer (already live):** daily donchian breakout. ~3-6
  trades/year, multi-month holds, the steadiest of everything tested.
  Unchanged.
- **A new slow layer (this round's headline find):** daily z-score mean
  reversion (z24<-1.5, buy the dip back toward a 24-day mean). ~6-7
  trades/year, much shorter holds (~120h median vs the breakout's ~456h),
  and — this is the point — it makes money in *different* conditions than
  a breakout does (reversion profits from chop the breakout gets whipsawed
  by). Two slow daily books that are genuinely uncorrelated in *shape*,
  not just in timing, is a better daily portfolio than one.
- **A new fast layer (the actual surprise of this round):** the same
  donchian shape AND a fast EMA20/50 cross, both running on 1h gold with
  10-50x the trade count of the daily books and holds measured in single-
  digit to low-double-digit hours instead of weeks. This is the piece the
  owner's "EMA crosses" ask actually earns: not as a daily replacement (it
  loses that fight to donchian outright) but as an intraday activity
  engine that the daily books structurally cannot be, since they only
  fire a handful of times a year.

**What did NOT pan out**, said plainly so it isn't quietly re-tried:
pullback-in-trend (RSI dip below a daily trend filter) is dead on gold at
1h, and the session-structure hypothesis — the family flagged going in as
"the likeliest real intraday edge" — produced no surviving config across
London-open, NY-open, or Asia-range breakout at 1h. Shorts, in every
family that tried them, lose money on gold over this data; the metal's
uptrend is real and mirroring the long side into it does not work.

**Biggest caveat, stated once and not softened:** every intraday number
in this report (1h and 4h) comes from one continuous ~2.4-year window
that is mostly one strong gold bull market. The val slices are ~5 months
each — not a second, independently-drawn regime. If gold chops or reverses
for an extended stretch, none of the 1h/4h survivors have been tested
against that yet; only the daily families, with their full 20-year,
three-decade span, have earned that kind of confidence. Treat every
intraday number here as "the shape works in the regime we have," not yet
"the shape works in general," until it either survives a sealed test or a
different regime shows up in fresh data.
