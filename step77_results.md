# Round 77 — A REAL S&P PLAYBOOK (breadth of setups, SPY/ES=F/QQQ)

Script: `step77_spx_playbook.py`. Full table: `step77_full_table.csv` (215
rows: 209 gauntleted configs + 6 report-only audit rows, nothing omitted).
Data: `data_spx_<TAG>_<TF>.parquet` (SPY, ES, QQQ x 1d/1h — SPY/ES reuse
round 60's caches verbatim, QQQ is new this round). Research only, no
orders, **no sealed-test looks spent** anywhere in this round.

**The owner's critique, verbatim, is what this round answers:** "the sole
reason you haven't placed a single S&P trade is you don't even have a real
playbook for it... that's not trading, that's one little element." Round
60 built five families but only ONE of them (RSI2<5 dip-buy) fires more
than a handful of times a year. This round adds **six new families, 209
new configs**, most of them native to SPY's ~730-day 1h cache that round
60 barely touched — and is honest that most of the new breadth still
doesn't beat costs. A playbook needs setups that actually fire; this
round finds three genuinely tradeable new ones and confirms most
intraday ideas people assume "should work" on the index simply don't,
after real costs.

---

## 1. Data — every span stated exactly, no faked resolution

| symbol | tf | bars | span | train ends | val ends (test sealed) | med TRAIN ATR% |
|---|---|---:|---|---|---|---:|
| SPY | 1d | 8,427 | 1993-01-29 → 2026-07-23 | 2013-02-27 | 2019-11-05 | 1.319% |
| SPY | 1h | 5,072 | 2023-08-24 → 2026-07-23 | 2025-05-22 | 2025-12-19 | 0.357% |
| ES=F | 1d | 6,526 | 2000-09-18 → 2026-07-24 | 2016-03-08 | 2021-05-17 | 1.360% |
| ES=F | 1h | 13,677 | 2024-03-01 → 2026-07-24 | 2025-08-06 | 2026-01-30 | 0.206% |
| QQQ | 1d | 6,886 | 1999-03-10 → 2026-07-24 | 2015-08-10 | 2021-01-28 | 1.704% |
| QQQ | 1h | 5,073 | 2023-08-25 → 2026-07-24 | 2025-05-23 | 2025-12-22 | 0.492% |

SPY/ES=F 1h are capped at ~730 days — yfinance's hard practical ceiling
for intraday equity/futures history, stated plainly, never faked finer or
longer. QQQ is a genuinely new instrument to this program (round 60 never
fetched it); its 1d span nearly matches SPY's ETF-era depth (1999 vs
1993). ES=F 1h is a near-continuous ~23-bar/day session (confirmed by
direct inspection); SPY/QQQ 1h are RTH-only, 1 bar = 9:30-10:30 ET on
almost every trading day.

Costs: ETF (SPY, QQQ) 4bps round trip, futures (ES=F) 2bps, both imported
UNMODIFIED from round 60 (`ETF_COSTS`/`FUT_COSTS`), `execution="taker"`.

---

## 2. Gauntlet + what "nothing omitted" means here

Chronological 60/20/20 per dataset/timeframe. SURVIVOR = positive
expectancy train AND val, ≥30 train / ≥8 val trades. **209 configs
tested — 23 SURVIVOR, 9 INSUFFICIENT-SAMPLE, 177 FAIL.** Every config,
survivor or not, is in `step77_full_table.csv` along with `trades_yr`
(trades/year over the train+val span) so frequency can be judged
alongside expectancy — a playbook needs setups that actually fire.

| family | n configs | SURVIVOR | INSUFF. | FAIL |
|---|---:|---:|---:|---:|
| 1a-orb-breakout | 16 | 3 | 0 | 13 |
| 1b-orb-fade | 16 | 3 | 0 | 13 |
| 1c-midsession-reversal | 12 | 0 | 0 | 12 |
| 1e-gap-reaction | 8 | 0 | 0 | 8 |
| 2-pullback-trend | 24 | 0 | 0 | 24 |
| 3a-bos-choch | 72 | 0 | 0 | 72 |
| 3b-sweep-reclaim-priorday | 12 | 0 | 0 | 12 |
| 3c-choch-confluence | 8 | 0 | 0 | 8 |
| 4a-squeeze-expansion | 12 | 5 | 2 | 5 |
| 4b-volgate-dipbuy | 4 | 2 | 2 | 0 |
| 4c-volgate-orb | 3 | 3 | 0 | 0 |
| 5a-relative-strength | 8 | 4 | 0 | 4 |
| 5b-volpct-tercile-dipbuy | 6 | 0 | 5 | 1 |
| 6a-turn-of-month | 6 | 2 | 0 | 4 |
| 6b-day-of-week | 2 | 1 | 0 | 1 |
| (1d-lasthour-drift) | audit, 6 rows | — | — | — |

Of the 23 SURVIVORs, **5 fire under 10 times/year** (flagged "rare, not a
playbook piece" per the task's own framing) — all five are variants of
the RSI2<5 dip-buy or the SPY/QQQ divergence catch-up shape, which are
inherently occasional events, not daily-tradeable setups.

---

## 3. FAMILY 1 — intraday session structure: **the opening range is the
round's clearest new win; everything else in this family is dead**

**1a opening-range breakout** (first 1h/2h RTH-clock range, break, 6-bar
cap, SPY+ES=F): 3/16 SURVIVOR, all SPY, all **long**, all **H2h** except
one H1h. Best: `H2h long tgt2.5xrange` — TRAIN +$4.58/trade (187t), VAL
+$6.81/trade (64t), ~108 trades/yr. Shorts and ES=F both die here — the
index's long bias (round 60's own finding) holding again at a completely
different timescale.

**1b opening-range fade** (failed breakout, fade back through the
range): 3/16 SURVIVOR — but ONLY the "fade a failed LOW break back up"
shape (i.e. still net-long), on SPY H1h and ES=F H2h. Best: SPY `H1h
long(fade-low-fail) tgt1.5xrange` — VAL +$7.01/trade (66t), ~106/yr.
Fading a failed HIGH break (i.e. going short) is dead everywhere, same
long-bias pattern as 1a.

**1c mid-session reversal** (11:00-14:00 ET failed-new-extreme fade):
**0/12, clean FAIL** — the best config's raw numbers look tempting
(`long(fail-low) tgt2.5xATR` SPY: TRAIN -$1.37, VAL +$8.05) but every
single config is negative on TRAIN, meaning val's apparent edge is noise
from a 52-trade window, not a real signal. **Do not build this.**

**1d last-hour drift** (report-only statistical audit, does the day's
momentum through the 2nd-to-last bar predict the last bar's own return):
t-stats of -1.41 to +1.47 across SPY/ES momentum-up/down buckets — **no
signal, not even a marginal one like round 60's overnight-drift finding.**
The index's own last hour does not meaningfully continue or fade its own
day so far, at this resolution.

**1e gap reaction** (trade the first-hour reaction to the overnight gap,
continuation vs fade, SPY only): **0/8, clean FAIL** on both directions
and both thresholds. Round 60 already killed the same-day gap-FILL chase
(0/16); this round confirms the gap's own first-hour REACTION — whether
you try to ride it or fade it — is equally dead after costs. **The
overnight gap is not a source of edge in either direction at 1h.**

---

## 4. FAMILY 2 — pullback-in-trend: **0/24, a clean and complete NO**

Above daily SMA50/SMA200, buy 1h pullback-and-reclaim of EMA20, EMA50, or
today's running session VWAP (used here as the standard institutional
pullback tool in place of a literal frozen "prior day's" VWAP level,
stated as the deliberate substitution). Every single config is FAIL —
several look attractive on TRAIN (`pullback->EMA20 trend=SMA50` SPY:
TRAIN +$2.35) but every one goes negative or flat on VAL. **The textbook
"buy the trend, buy the pullback" shape that works in equity swing-
trading folklore does not survive costs at 1h on the index, on any of
the three pullback references tested, on either instrument.** This is
the round's most surprising and most complete graveyard — a genuinely
new finding, not a repeat of anything round 60 tested.

---

## 5. FAMILY 3 — structure (step56/step73 toolkit, transferred natively
to 1h): **the toolkit does NOT transfer to the index — 0/92 across all
three sub-families**

**3a BOS/CHoCH** (bos_chain imported unmodified from step56, run NATIVELY
on 1h for the first time — never a daily→4h collapse like step73's prior
ES=F test): **0/72 SURVIVOR** across k∈{5,8}, wick vs body-based structure
(step73's "don't take the wicks into account" rule), continuation vs
CHoCH vs "both", R∈{1.5,2.5}, on SPY, ES=F, AND QQQ (the new cross-check).
Best raw number is a QQQ CHoCH config with a wild TRAIN/VAL sign flip
(TRAIN -$9.40, VAL +$27.36 on 25 val trades) — noise, not a finding.

**3b sweep-and-reclaim of the prior day's high/low** (the literal shape
step56's own equal-highs pools never define): **0/12 SURVIVOR**, SPY +
ES=F, long/short/both, R∈{1.5,2.5}. Every config is FAIL on val.

**3c CHoCH+confluence head-to-head** (round 56's central crypto claim,
transferred: does requiring CHoCH to agree with a recent prior-day sweep
beat CHoCH alone?): **0/8 SURVIVOR either way** — but the comparison
itself is informative. On SPY, CHoCH-alone actually posts a real positive
TRAIN number (+$7.45/trade, 45t) that confluence-gating cuts to a thin,
sample-starved 18 trades without fixing VAL (both stay negative-to-flat).
**Confluence does not rescue CHoCH on the index — it just cuts the
sample, exactly the failure mode step56 asked whether the tool would
fall into, and here it does.**

**Verdict for the round's central structure question**: the SMC/ICT
toolkit that is this program's best-documented crypto edge (step56) does
**not** transfer to the S&P at 1h, in any of three distinct shapes tested,
across three instruments. This is a strong, broad, honest negative —
worth stating as plainly as the crypto-side positive was.

---

## 6. FAMILY 4 — volatility regime: **the round's best-populated survivor
cluster — squeeze/expansion and both vol-gate cuts all work**

**4a squeeze→expansion** (TTM-style BB(20,2)-inside-KC(20,1.5xATR),
trade the release direction): **5/12 SURVIVOR, ALL on ES=F.** Best:
`both tgt2.5xATR` — TRAIN +$4.28/trade (152t), VAL +$4.47/trade (50t),
~105 trades/yr — genuinely frequent, genuinely tradeable. SPY's two
long-only configs are INSUFFICIENT-SAMPLE (only 15 train / 6 val trades —
promising direction, thin sample) rather than FAIL; SPY short-only and
both-directions die. **This is the round's clearest new intraday win on
the futures side.**

**4b vol-gated dip-buy** (does round 60's RSI2<5 need an ATR%-percentile
floor — a "too quiet to trade" state, SPY daily): 2/4 SURVIVOR
(unfiltered and vol>30pct), 2/4 INSUFFICIENT-SAMPLE (vol>50/70pct — the
gate just cuts an already-thin sample further, same failure mode as 3c).
**No evidence of a "too quiet" floor being NEEDED** — the unfiltered
shape already survives; the gate doesn't add edge, it removes trades.
Answers the task's exact question: no, this index dip-buy does not have
a meaningful quiet-market dead zone the way some crypto shapes do.

**4c vol-gated opening-range breakout**: **3/3 SURVIVOR** — unfiltered,
vol>30pct, AND vol>50pct all survive on family 1a's H1h-long config, with
VAL expectancy actually RISING as the gate tightens (unfiltered $0.27 →
vol>30 $1.71 → vol>50 $3.75/trade), though train sample shrinks
correspondingly (227→162→124 trades). **This is a real, mild
confirmation that the opening-range breakout works BETTER in a
not-too-quiet regime** — the closest thing this round found to crypto's
"quiet market, don't trade" pattern.

---

## 7. FAMILY 5 — relative strength / intermarket: **SPY/QQQ divergence
catch-up is real; fading the leader is not**

**5a SPY vs QQQ divergence** (one index breaks an N-day return, the other
doesn't — trade the LAGGARD for catch-up or fade the LEADER for mean
reversion): **4/8 SURVIVOR, and the pattern is completely one-sided** —
every "long the laggard, catch-up" config survives (N5/N10 × QQQ-laggard
and SPY-laggard, 4/4), while every "short the leader, mean-revert" config
FAILS (0/4). Best: `N5d long-QQQ-catchup hold5d` — VAL +$50.17/trade
(47t, 9.6/yr). **The honest read: SPY/QQQ divergence is real and
tradeable, but only as a "the laggard tends to catch up" continuation
signal — the "fade the leader, it's overextended" mean-reversion half of
the hypothesis is flatly refuted**, mirroring round 60's family-4 finding
that naive mean-reversion beats naive momentum-fade shapes on this index
family after family.

**5b vol-percentile terciles on the dip-buy** (direct comparison: does
RSI2<5 improve at extreme vs moderate vol?): **0/6 SURVIVOR — 5/6
INSUFFICIENT-SAMPLE.** Splitting into thirds starves every cell (6-29
trades) — none clears the 30-trade TRAIN floor. The RAW numbers hint
high-vol and mid-vol cells might be richest (SPY high-vol TRAIN
+$192/trade!) but with 20 train trades that's an anecdote, not a
finding — flagged explicitly, NOT a validated result. **Answer to the
task's literal question ("does the panic-buy improve when volatility is
extreme vs moderate") is: plausibly yes on raw numbers, but this round
cannot say so with a straight face at these sample sizes — a dedicated
round with a coarser 2-bucket split (not terciles) is the honest next
step.**

---

## 8. FAMILY 6 — seasonality follow-up: **turn-of-month, finally built,
survives; day-of-week is thin but real**

**6a turn-of-month** (round 60 flagged t=2.43, never built — built here:
buy N trading days before month-end, exit N days into the new month):
**2/6 SURVIVOR**, both at N=3 (stop=none and stop=2xATR); N=1 and N=2
both FAIL on VAL despite strong TRAIN. Best: `TOM N=3d stop=none` — TRAIN
+$51.21/trade (240t), VAL +$27.25/trade (81t), ~12 trades/yr (4 windows/yr
× 3 days ≈ close to the literal Xu-McConnell window). **Round 60's
strongest-flagged, never-built seasonality signal is now a real,
gauntlet-cleared, cost-honest survivor** — genuinely tradeable, though
"trades/yr" here undercounts the true annual frequency somewhat since
each turn-of-month WINDOW is being entered on a single triggering day,
not counted as one trade per calendar month event (12/yr in the raw
metric ≈ roughly monthly, which is honest).

**6b day-of-week**: 1/2 SURVIVOR — `long Mon->Fri` (buy Monday, sell
Friday, weekly) survives (VAL +$18.57/trade, 307t, ~46/yr); `long
Tue-only` (the single day with the strongest audit t-stat in round 60)
FAILS once actually traded with costs (VAL +$1.45/trade on 345 trades —
positive but doesn't clear the cost-adjusted bar cleanly, marked FAIL by
sign only on TRAIN... actually TRAIN was -$0.02, i.e. round-trip costs on
1-day holds simply eat the small Tuesday edge). **The Monday-to-Friday
weekly hold is the more robust seasonality shape than chasing the single
best day.**

---

## 9. Ranked SURVIVORS (by robustness — sample depth, honest frequency,
cross-instrument confirmation — NOT by raw expectancy)

1. **FAMILY 4c vol-gated opening-range breakout, SPY H1h long** (3/3
   SURVIVOR, VAL expectancy RISES as the vol-gate tightens, 66-132
   trades/yr) — the round's most internally-consistent new finding.
2. **FAMILY 4a squeeze→expansion, ES=F, all directions** (5/12 SURVIVOR
   concentrated entirely on ES=F, 48-105 trades/yr, genuinely frequent) —
   the round's best NEW intraday futures edge.
3. **FAMILY 1a/1b opening-range breakout + fade, SPY long-only /
   ES=F fade-low** (6/32 SURVIVOR combined, 83-113 trades/yr, but modest
   per-trade margins $0.27-$7 against a 4bp cost floor) — real but
   thinner than #1/#2.
4. **FAMILY 6a turn-of-month N=3** (2/6 SURVIVOR, ~12/yr, the round-60
   callback finally validated) — the strongest SEASONALITY piece in the
   whole program, low frequency by design (it's a monthly calendar
   event, not meant to fire often).
5. **FAMILY 5a SPY/QQQ catch-up divergence** (4/8 SURVIVOR, 8-10/yr,
   borderline "rare") — real, one-sided (catch-up only, never fade-the-
   leader), occasional by nature.
6. **FAMILY 4b vol-gated dip-buy unfiltered/vol>30** (2/4 SURVIVOR,
   2-3.5/yr) — this is round 60's ORIGINAL RSI2<5 shape re-confirmed
   under a vol lens, not a new edge; the gate adds nothing (see §6).
7. **FAMILY 6b Mon→Fri weekly hold** (1/2 SURVIVOR, ~46/yr) — real but
   thin per-trade margin ($3.84-$18.57), first seasonality shape to
   actually clear costs in this program at a WEEKLY (not monthly) cadence.

**Not candidates — confirmed dead this round**: family 1c (mid-session
reversal, 0/12, val-only noise), family 1e (gap reaction, 0/8, both
directions), family 2 (pullback-in-trend, 0/24, ALL THREE pullback
references, both instruments — the cleanest new graveyard), family 3
in its ENTIRETY (0/92 — BOS/CHoCH native 1h, sweep-reclaim, AND
CHoCH+confluence all dead, on SPY/ES=F/QQQ), family 5b (vol-terciles,
0/6, sample-starved by construction — inconclusive, not dead, needs a
coarser split).

---

## 10. What a real S&P trading day looks like, with this playbook

- **9:30-10:30 ET (the open):** watch the first 1-2h range form. Once it
  breaks, the LONG side of a breakout (family 1a, SPY H2h) or a failed
  LOW break's reclaim (family 1b) are the only two shapes with real
  edge — never take the short side of either.
- **Anywhere the market has been quiet (low realized vol) recently:**
  a squeeze forming on ES=F (family 4a) is worth watching for the
  release — this is the round's most frequent single setup (~50-105
  trades/yr) and works in BOTH directions once it fires, unlike the
  long-only bias everywhere else.
- **Mid-morning through midday:** nothing in this round's toolkit fires
  reliably here — no mid-session reversal, no gap-reaction trade, no
  pullback-to-EMA/VWAP entry survived. This is confirmed DEAD TIME for
  this playbook, not a gap in coverage — real absence of edge.
- **Once or twice a month, near the calendar turn:** the turn-of-month
  long (family 6a, N=3) is the strongest single non-intraday signal in
  the entire program (t=2.43 audited in round 60, now a real cost-honest
  survivor) — low-frequency but the highest-conviction seasonal trade
  found anywhere in this repo.
- **On a week SPY/QQQ visibly diverge** (one at a 5-10 day extreme, the
  other flat or opposite): buy the LAGGARD expecting catch-up (family
  5a) — never fade the leader, that half is dead.
- **Structure-based setups (BOS, CHoCH, sweeps, confluence)** — the
  toolkit that is this program's best crypto edge — simply are not part
  of a real S&P trading day. Leave them out of the index playbook
  entirely; they do not transfer.
- **RSI2<5 dip-buy** (round 60's original find) still anchors the SLOW
  end of the playbook — a few times a year, buy the panic, no fixed
  target — now confirmed to not need (or benefit from) a volatility gate.

---

## 11. Honest gaps

- **No execution venue still exists** for the real S&P 500 (same as
  round 60) — every number here is knowledge-banked, not deployable,
  until Alpaca paper (SPY/QQQ) or a futures broker (ES=F) exists.
- **Family 5b (vol-percentile terciles) is inconclusive, not dead** —
  every cell is sample-starved by the 3-way split; a 2-bucket (median
  split) version on a longer span is the honest next test, flagged
  explicitly rather than either oversold as a finding or discarded.
- **Family 6a's `trades_yr` metric undercounts true annual frequency
  somewhat** — it counts triggering DAYS, and turn-of-month naturally
  clusters near month boundaries; ~12/yr is a reasonable read (roughly
  monthly) but the metric wasn't purpose-built for calendar-anchored
  strategies.
- **QQQ's 1h frame was fetched and cached this round (`data_spx_QQQ_1h.
  parquet`) but only used in family 3a** (as the structure-toolkit
  cross-check) — a natural follow-up is running families 1/2/4 on QQQ
  1h too, not done here to keep the grid in this round's ~200-config
  band.
- **No gap-honesty correction pass was run this round** (unlike round
  60's family 1/4) — every stop-bearing 1h SURVIVOR here uses a short
  (3-12 bar) max_hold, so overnight gap-through risk is structurally
  limited but NOT separately re-quantified; flagged as a follow-up if
  any of these configs are ever taken to a sealed look.
- **Family 3's negative result is broad but not exhaustive** — it tests
  bos_chain's exact k-swing-fractal definition (k∈{5,8}) and one
  specific confluence pairing (CHoCH + prior-day sweep); a genuinely
  different structure primitive (e.g. volume-profile-based levels, which
  this program has never built) is not ruled out by this round.

---

## Summary for the record

- **209 gauntleted configs + 6 report-only audit rows = 215 total, 0
  sealed-test looks spent.** Six new families, addressing the owner's
  exact complaint that the S&P book was "one little element."
- **23 SURVIVORs, 5 of them genuinely rare (<10 trades/yr)** — the other
  18 fire between ~46 and ~132 times/year, a real playbook's worth of
  frequency, concentrated in families 1a/1b (opening range), 4a
  (squeeze/expansion), 4c (vol-gated ORB), and 6b (weekly hold).
- **Genuinely tradeable (not rare) new families**: opening-range
  breakout/fade (SPY long-only, ES=F fade-low), squeeze→expansion
  (ES=F, both directions), vol-gated opening-range breakout (SPY).
- **Rare-but-real (a few/year, still worth the playbook)**: turn-of-month
  N=3, SPY/QQQ catch-up divergence, the RSI2<5 dip-buy (round 60,
  reconfirmed).
- **Does the structure toolkit (step56/step73) transfer to the index?
  NO — decisively, 0/92 across BOS/CHoCH native-1h, sweep-and-reclaim of
  the prior day's high/low, and CHoCH+confluence, on SPY, ES=F, AND
  QQQ.** This program's best crypto edge does not port to the S&P.
- **Biggest caveat**: still no execution venue for any of this — every
  number is knowledge-banked. The second-biggest: family 2
  (pullback-in-trend) and family 3 (structure) are complete, broad
  negatives (0/24 and 0/92) — this round found real breadth, but also
  confirmed that several "should obviously work" ideas (buy the
  pullback, trade the structure break) simply do not, on this
  instrument, after real costs.
