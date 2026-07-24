# step47 results — round 47: does the WatcherGuru news edge transfer to TradFi?

**Mandate:** take the program's one sealed-test-PASS edge (news momentum off
WatcherGuru headlines, round 45B: A-news-momentum FIRST-BAR-MOVE direction,
BTC 1h, stop 1.2%/target 2.4%, hold 24h — TEST +$20.81/t x67, +13.9%, 52.2%
win) and test the owner's thesis that macro news should move GOLD / OIL /
NASDAQ / S&P **harder** than crypto. Research only. Files touched: this
file, `step47_multimarket_news.py`, and `data_news_mkts_<SYM>.parquet` for
GLD/USO/QQQ/SPY/GC=F/CL=F. No live orders, no commits, no test-slice looks
spent (that budget belongs to the lead agent).

## Bottom line up front

**The owner's thesis is not confirmed once the data is read honestly.**
Pooled (session + off-hours events blended) ratios for GLD/QQQ/SPY (1.31–1.40x)
do look bigger than BTC's 1.31x reference. But almost all of that apparent
edge evaporates the moment events are split into SESSION (market was live)
vs OFF-HOURS (market was closed, "reaction" = overnight/weekend gap) — the
split the mandate specifically demanded. Session-only ratios for every ETF
collapse to ~1.0–1.03x (no measurable live reaction above baseline noise),
while off-hours-only ratios balloon to 1.3–1.8x (ordinary overnight-gap
volatility, not a news reaction). Crypto has almost no "off-hours" to hide
in — its 1.31x is nearly all genuine live reaction. The two futures
contracts (which DO trade near-24h, like crypto) sit right where that
theory predicts: session-only ratios of 1.03–1.09x, much closer to BTC's
own live number than the ETFs' pooled numbers suggested. **24/7-ness, not
asset class, is what was actually driving BTC's edge.**

At the strategy level: **zero survivors on all four ETFs** (256 configs run,
0 with positive train AND val expectancy). Gold futures (GC=F) produced
9 raw survivors, 4 of which hold up after gap-adjustment — the one
genuinely interesting result, flagged below as sealed-look candidates.
Oil futures (CL=F) produced 2 raw survivors, both of which **die** under
gap-adjustment. The tight fixed/ATR-scaled stops this round used turn out
to be badly mismatched to ETF overnight-gap risk — see the gap-adjustment
section, it is a genuinely ugly number.

---

## 1. Data pulled

1h bars via yfinance, cached to `data_news_mkts_<SYM>.parquet` (re-run makes
zero network calls once cached):

| symbol | bars | span | median gap | max gap | gaps >3h |
|---|---|---|---|---|---|
| GLD | 5,071 | 2023-08-24 13:30 → 2026-07-23 19:30 UTC (1,064d) | 60min | 94.0h (weekend) | 729 |
| USO | 5,072 | same | 60min | 94.0h | 729 |
| QQQ | 5,073 | same | 60min | 94.0h | 729 |
| SPY | 5,072 | same | 60min | 94.0h | 729 |
| GC=F | 13,738 | 2024-02-29 05:00 → 2026-07-24 00:00 UTC (875d) | 60min | 80.0h (rare extended closure) | 148 |
| CL=F | 13,530 | same | 60min | 80.0h | 164 |

yfinance quirks handled: `Ticker.history()` (single symbol) returned clean
non-MultiIndex columns in this environment, but the fetch code defensively
flattens MultiIndex columns anyway (untested-but-safe path, since other
yfinance versions/paths do return MultiIndex for this call). Intraday
timestamps come back tz-aware in `America/New_York`, converted explicitly
to UTC to match every other file in this repo. yfinance's 1h history limit
(~730 days for the ETFs; the two continuous-futures symbols went back
further, ~875 days) comfortably covers the whole WatcherGuru news span
(2025-06-18 → 2026-07-23) with a year-plus of pre-news runway for warmup
(ATR, etc.) — no missing-coverage problem. Missing bars (exchange closures)
are reported, not filled/interpolated — filling would fabricate no-lookahead
violations.

**ETF bars ONLY exist during the regular NYSE session** (09:30–16:00 ET,
7 bars/day; yfinance's default 1h interval does not include pre/post
market). **Futures bars exist nearly 24h** with one ~1h daily maintenance
gap (16:00–18:00 ET) and a weekend closure (Fri ~17:00 → Sun ~18:00 ET).
This structural difference is exactly why the pooled-vs-session-vs-off-hours
split below matters — see §3.

News dataset: `data_watcherguru_history.parquet`, 3,527 posts (the cache has
grown since round 45B's 674-post snapshot), 2,950 relevant (83.6%) by the
reused `classify_headline()` keyword classifier, span 2025-06-18 →
2026-07-23. Tag distribution (relevant only): NEUTRAL 2,255, BEARISH 548,
BULLISH 138, MIXED 9. **Caveat worth flagging plainly**: `classify_headline`'s
relevance keyword list is broad crypto+macro/political (bitcoin, fed, cpi,
trump, war, sanctions, gold, oil price, nasdaq, s&p...) — reused verbatim
per the mandate, so this is a faithful test of "does the SAME event set that
worked for BTC also move TradFi," but it means 76% of "relevant" events are
tagged NEUTRAL (no bull/bear keyword hit) — mostly crypto-flavored posts
that only incidentally mention macro terms, not curated gold/oil/equity news.

## 2. Cost model (stated explicitly)

- **ETF_COSTS** (GLD/USO/QQQ/SPY, commission-free/tight-spread assumption):
  fee 1.0bp (maker=taker, no discount tier modeled) + 0.5bp half-spread +
  0.5bp slippage → **taker round trip = 4.0 bps**.
- **FUT_COSTS** (GC=F/CL=F, robustness only): fee 0.5bp + 0.25bp half-spread
  + 0.25bp slippage → **taker round trip = 2.0 bps** (hits the mandate's
  "2bp round trip" target exactly).
- No funding series exists for either market type (no perpetual-funding
  mechanic in equities/ETFs/futures). Passing `funding_series=None` to
  `run_backtest` would trigger `backtest.py`'s conservative "always pay the
  flat crypto-perp rate" fallback — a real cost for BTC perps that simply
  does not exist here — so an explicit all-zero `funding_series` is passed
  instead, correctly zeroing that leg while leaving fees/spread/slippage/
  stop/target mechanics untouched.
- Execution: `maker` (post-only-then-chase), same convention as
  step43/step45b, reused unchanged.

## 3. THE central finding — session vs off-hours (the honest split)

Ratio_vs_baseline, ALL_RELEVANT tag, 1h horizon (the money number):

| market | pooled (blended) | session-only (live) | off-hours-only (gap) | n events (pooled) |
|---|---|---|---|---|
| **BTC (reference, recomputed)** | **1.308** | *(~= pooled — BTC has no off-hours)* | — | 2,941 |
| GLD | 1.404 | **1.016** | 1.770 | 2,948 |
| USO | 1.120 | 0.932 | 1.297 | 2,948 |
| QQQ | 1.385 | **1.026** | 1.725 | 2,948 |
| SPY | 1.311 | **1.031** | 1.575 | 2,948 |
| GC=F (futures) | 1.126 | 1.089 | 1.270 | 2,950 |
| CL=F (futures) | 1.054 | 1.027 | 1.158 | 2,950 |

Read naively (pooled column only), GLD/QQQ/SPY beat or match BTC's 1.308 —
exactly what the owner's thesis predicted. **Read honestly (session-only
column, the only one measuring an actual live reaction to news), every
single ETF collapses to ~1.0–1.03x — statistically indistinguishable from
"no reaction beyond ordinary noise."** The entire apparent edge in the
pooled number comes from the off-hours column (1.3–1.8x), which is not a
news reaction at all — it is the ordinary size of an overnight/weekend gap
being misattributed to whatever headline happened to print during market
close. Session coverage explains why: ETF events split ~48.6% session /
51.4% off-hours (WatcherGuru posts around the clock; equities are open
~28% of the week), so more than half of every ETF's "pooled" sample is
gap-noise. The two futures contracts, which trade ~80% session-covered
(near-24h with just the daily maintenance gap and weekend), sit MUCH closer
to BTC's own number even pooled (1.05–1.13x) and show the smallest
session/off-hours divergence of any market tested — consistent with "being
open 24/7 is what let BTC's edge show up," not something intrinsic to
crypto as an asset class.

The 4h-horizon numbers reinforce this (full per-tag/per-horizon table is
printed by the script; not reproduced in full here for length) — by 4h,
even the pooled ratios for GLD/QQQ/SPY fall to 0.90–1.01x: the entire
"news moves TradFi harder" signal is a same-bar overnight-gap artifact
that has already washed out four hours later, not a slow-building macro
reaction.

BULLISH/BEARISH tag breakdown (pooled, 1h): BEARISH-tagged headlines carry
the strongest ratio on every symbol (GLD 1.55x, USO 1.20x, QQQ 1.37x, SPY
1.30x, GC=F 1.39x, CL=F 1.10x — vs BTC's BEARISH 1.41x), matching BTC's own
pattern (bearish news hits harder than bullish) but the session/off-hours
contamination applies to these splits too, so the same "read the
session-only column" caution applies.

**Known blind spot in the session/off-hours split**: it is empirical (gap
from event-time to the next tradable bar's open vs a 75-minute threshold,
chosen to sit safely above the ~60min hourly cadence and safely below the
~120min futures maintenance-break/2h-gap cases) — it does NOT hardcode a
market-holiday calendar, so a handful of events during the futures'
17:00–18:00 ET daily maintenance window could theoretically misclassify
either way; this is a small, stated, non-material edge case, not a
systematic bias (the maintenance gap is ~1h, indistinguishable in principle
from the normal cadence, but there are only 148–164 gaps >3h total across
each futures dataset, so the affected event count is tiny).

## 4. Strategy grid — gauntlet results

Reused (verbatim from step43_daytrade/step45b_news_events): `split_points`
(chronological 60/20/20), `verdict_for`/`mk_row` (>=30 train / >=8 val
trades, positive both = SURVIVOR), `align_events`, `event_study`,
`classify_headline`. New for this round: `day_trade_signal_wallclock`
(real elapsed-time exit, not bar-count — a QQQ "24 bars" would span ~3.4
TRADING DAYS since only 7 bars print per session day; wall-clock is the
correct tool) and `day_trade_signal_session_close` (never carry a position
overnight — ETFs only, since futures don't have a clean daily "close").
Families: **A-news-momentum** (long the up-move / short the down-move of
the first tradable post-news bar) and **B-news-fade** (opposite) — the
FIRST-BAR-MOVE direction convention specifically, since round 45B/45B-
addendum already established that the KEYWORD-tag direction does not
survive out-of-sample; this round does not re-spend grid budget re-testing
a direction convention already shown to fail.

**Stop candidates** — owner-given fixed {0.5, 0.8, 1.2}% UNION each
market's own TRAIN-only median-ATR%-scaled pair (0.75x/1.25x med ATR),
deduped/clipped [0.15%, 2.0%]:

| market | train median 1h ATR% | stop candidates used |
|---|---|---|
| GLD | 0.419% | 0.31, 0.5, 0.8, 1.2 % |
| USO | 0.660% | 0.5, 0.8, 1.2 % *(ATR-scaled pair collapsed into the fixed set)* |
| QQQ | 0.396% | 0.3, 0.5, 0.8, 1.2 % |
| SPY | 0.297% | 0.22, 0.37, 0.5, 0.8, 1.2 % |
| GC=F | 0.342% | 0.26, 0.43, 0.5, 0.8, 1.2 % |
| CL=F | 0.519% | 0.39, 0.5, 0.65, 0.8, 1.2 % |

TradFi ATR% sits well below BTC's — every ETF's own natural stop distance
sits at or below 0.5%, confirming the mandate's suspicion that BTC's 1.2%
stop is oversized here; the grid used both anyway so the fixed candidates
serve as an honest "what if we just ported BTC's numbers" control.

Targets: {2x, 3x} x stop (owner-given). Holds: 24h wall-clock (all 6
symbols) + exit-by-session-close (all 4 ETFs — mandate asked for QQQ/SPY
specifically; extended to GLD/USO too since it's the same mechanism and the
extra 32 configs/market cost nothing). Config counts: GLD/QQQ 64 each,
USO 48, SPY 80 (its extra ATR-scaled stop widened the grid by one), GC=F/
CL=F 40 each (no session-close variant) = **336 configs total**.

**Sample-size honesty, inverted from expectation**: the mandate anticipated
"many configs will be INSUFFICIENT-SAMPLE." That did not happen — **zero**
INSUFFICIENT-SAMPLE verdicts across all 336 configs. Every train slice
produced ~143–164 trades and every val slice ~45–55, comfortably clearing
the 30/8 floor. Reason: the classifier's broad relevance keywords make
~1,300–1,700 up-events and ~1,100–1,500 down-events per market per split
window — so dense that with a 24h hold, the signal is essentially always
in a position and immediately re-enters when flat; train-trade count (~157
for most 24h-wallclock configs) is set by **train-window-length ÷
avg-hold-length**, not by event scarcity, and barely varies across
different stop/target combinations. This means grid configs did not fail
for lack of data — every FAIL below is a genuine negative-expectancy
result, not a starved one.

**Verdict counts per market (raw engine numbers):**

| market | configs | SURVIVOR | FAIL | best near-miss (train-positive, ranked by val_exp) |
|---|---|---|---|---|
| GLD | 64 | 0 | 64 | session-only B-fade stop0.5%/tgt3x/wallclock24h: train +$1.92/t x143, val **−$0.19/t** x45 |
| USO | 48 | 0 | 48 | session-only B-fade stop0.5%/tgt3x/wallclock24h: train +$0.08/t x143, val **−$12.72/t** x45 |
| QQQ | 64 | 0 | 64 | **none train-positive at all** |
| SPY | 80 | 0 | 80 | **none train-positive at all** |
| GC=F | 40 | 9 | 31 | see survivors table below |
| CL=F | 40 | 2 | 38 | see survivors table below |

QQQ and SPY are the cleanest possible negative result: not one of the 64/80
configs even cleared train expectancy, let alone val — the fastest,
most-widely-quoted "macro-news-moves-stocks" instruments in the test show
**no exploitable news-momentum edge of this shape whatsoever**.

## 5. Gap-adjustment — the honesty check that mattered most

`backtest.py`'s intra-bar hard stop fires on a low/high touch and fills AT
the stop price — correct when the stop was touched mid-bar, but a fiction
if the bar's OPEN had already gapped through the stop (overnight/weekend
close-to-open jump, rare in 24/7 crypto, common here). `gap_adjust()`
(new this round, verified byte-for-byte against a direct engine re-run on
a synthetic gap during development — see the function's docstring in
`step47_multimarket_news.py`) detects exactly this per stop-exit trade and
recomputes the honest worse fill.

**The ugliest, most important number in this round**: for GLD's best
near-miss config above (session-only B-fade, stop 0.5%), **44 of its 45
validation trades were gap-adjusted** — essentially every single stop-loss
in that config gapped through its trigger level rather than being touched
cleanly intrabar. The honest post-adjustment number: val expectancy falls
from a modest −$0.19/trade to **−$37.81/trade**. USO's best near-miss
similarly falls from train +$0.08/val −$12.72 (raw) to train **−$24.04**/val
**−$31.43** (gap-adjusted). A 0.5% stop is simply too tight for how ETFs
actually gap overnight when held through a close — this is the single
clearest piece of evidence in this round for why the crypto-tuned tight-
stop playbook does not port to session-based markets as-is.

Futures fared much better (near-24h trading means far fewer real gaps to
adjust): GC=F's 9 survivors saw only 3–5 gap-adjusted trades each (out of
~157 train + 54 val), and CL=F's 2 survivors saw 3–8. This is itself a
finding: **futures' near-continuous session is what makes the tight-stop
geometry survivable at all** — the same 24/7-ness insight from §3, now
showing up in the cost/risk math too, not just the event-study ratio.

## 6. Survivors and sealed-look candidates

**GC=F (gold futures) — 9 raw survivors, 4 gap-adjusted survivors:**

| split | family | config | train | val (raw) | gap-adj n | val (gap-adj) | gap-adj verdict |
|---|---|---|---|---|---|---|---|
| session-only | A-news-momentum | stop0.80%/tgt3x/wallclock24h | +$9.28/t x157 | +$16.02/t x54 | 4 | **+$10.48/t** | SURVIVOR |
| pooled | A-news-momentum | stop0.80%/tgt3x/wallclock24h | +$10.52/t x157 | +$8.93/t x54 | 4 | **+$3.59/t** | SURVIVOR |
| session-only | A-news-momentum | stop1.20%/tgt2x/wallclock24h | +$13.00/t x157 | +$8.98/t x54 | 3 | **+$4.98/t** | SURVIVOR |
| session-only | A-news-momentum | stop1.20%/tgt3x/wallclock24h | +$11.58/t x157 | +$8.42/t x54 | 3 | **+$4.37/t** | SURVIVOR |

(5 more raw survivors — stop1.20% pooled x2, stop0.50%/stop0.80% session-only
x2 — do not survive gap-adjustment; val expectancy flips negative once
their handful of gapped stops are honestly repriced.)

**Reasoning for flagging these as the round's sealed-look candidates**: all
four are the SAME family/direction that already passed BTC's own sealed
test (A-news-momentum, first-bar-move), all four clear the 30/8 sample
floor comfortably (157/54), all four stay positive train+val even after
gap-adjustment (the honest number, not the flattering one), and the
0.8–1.2% stops used sit inside the owner's tight-stop-tier mandate. The
strongest single candidate by gap-adjusted val expectancy is **session-only
A-news-momentum, stop 0.80%, target 3x (2.4%), hold 24h wall-clock: train
+$9.28/t x157, val +$16.02/t raw → +$10.48/t gap-adjusted x54** — structurally
the closest analog to BTC's own passing config (same family, same
direction convention, comparable stop/target ratio) transplanted onto the
one TradFi instrument that actually behaves enough like crypto (near-24h
session) to carry it.

**CL=F (oil futures) — 2 raw survivors, 0 gap-adjusted survivors.** Both
(B-news-fade, stop 0.80%/tgt2x, pooled and session-only) flip negative on
val once gap-adjusted (val +$3.70→−$7.58 and +$2.91→−$8.70 respectively).
Not recommended for a sealed look.

**GLD/USO/QQQ/SPY — no candidates.** Zero raw survivors on any of the 256
ETF configs; the closest near-misses are already negative on val before
gap-adjustment even applies, and catastrophically negative after. No
sealed-look budget should be spent on any ETF config from this grid.

## 7. Caveats (most important first)

1. **The session/off-hours split is the whole story, and it says the
   owner's thesis is false for the ETFs as tested.** The apparent
   "TradFi ratio > BTC ratio" only exists in the pooled number, which is
   contaminated by ordinary overnight-gap noise on markets that are closed
   16.5+ hours a day. Read only the session-only column for something
   comparable to BTC's always-live 1.31x, and every ETF sits at ~1.0x —
   no measurable live news reaction.
2. Gold futures (GC=F) is the one genuinely promising result, and even
   that is a robustness/proxy instrument (continuous futures contract,
   not the same vehicle as GLD) with a still-short news history (~13
   months) — one gauntlet pass, zero sealed looks spent, nowhere near
   "durable edge" territory yet.
3. The classifier's relevance keywords are broad crypto+macro (not
   curated for gold/oil/equity impact specifically) — 76% of qualifying
   events are tagged NEUTRAL. A gold/oil/equity-tuned classifier might
   produce a cleaner, smaller, higher-signal event set; this round
   deliberately reused the BTC classifier unchanged per the mandate, so
   this is a faithful transfer test, not a best-possible one.
4. High event density means every 24h-wallclock config in this grid
   trades near-continuously (train_n ≈ train_bars ÷ avg_hold, largely
   independent of which stop/target was chosen) — config differentiation
   here comes almost entirely from stop/target geometry interacting with
   entry timing, not from event selectivity. A sparser/stricter event
   filter (e.g., BEARISH-only, which showed the strongest ratios
   everywhere) was not separately gridded this round and is a reasonable
   next step.
5. Exit-by-session-close (all ETF configs) was uniformly and badly
   negative everywhere it was tried — forcing flat every day, at this
   event density, means near-continuous position churn and the ETF cost
   floor (4bps) compounds fast. Not a viable variant as specified.
6. Session/off-hours classification is empirical (75-minute gap
   threshold), not calendar-aware — see the stated blind spot in §3
   around futures' ~1h daily maintenance window; material impact judged
   negligible given the tiny affected event count.
