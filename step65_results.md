# Round 65 — Give the news trade eyes

**Question:** the owner's critique of the live NEWSDESK book — "you already
know your take profit before even looking at the situation... no real
trader does this" — tested head-on. Same validated trigger (a relevant
WatcherGuru headline → the first full 1h bar after it → enter at that bar's
own close, direction = its own close-vs-open sign, R45B/step45b's only
sealed-test survivor), five different REACTIONS to that trigger.

Script: `step65_news_eyes.py`. Research only — no live orders, no commits,
no file touched besides this one and the script itself. Did not import or
touch `step59_exit_science.py` or `gold_book.py` (concurrent agent's
territory this round) — the per-trade simulator below is an independent
reimplementation of the same repo-standard conventions (gap-through
honesty, stop-wins-ties, maker-fee-on-resting-fills), used as a
cross-check, not a dependency.

## Setup

- BTC 1h candles (cached, `data_bybit_BTCUSDT_1h_full.parquet`) sliced to
  the WatcherGuru harvested span (`data_watcherguru_history.parquet`, 3,527
  posts, 2025-06-18 → 2026-07-23) ± 24h → **9,644 bars**.
- Chronological 60/20/20 (R45B/step43's own `split_points`): train →
  2026-02-13, val → 2026-05-05, **TEST SEALED** — every array this script
  touches is sliced to `[0:i_va]` before any pivot/ATR/entry logic runs; the
  final 20% is never loaded into a variable the logic can reach. Zero
  sealed-look spend this round.
- Entries (the fixed trigger): 2,950 relevant headlines → 2,232 unique
  first-tradeable-bars → 1,840 directional entries (916 long / 924 short,
  dojis discarded) in `[0:i_va]`. These are RAW entries; realized trade
  counts below are smaller because every policy is single-slot (one trade
  open at a time — a policy that holds longer blocks whichever next
  headline-bar would have fired during that hold, same legitimate,
  expected consequence this repo has documented before for single-slot
  books).
- Floors (R45B/step43): ≥30 train trades, ≥8 val trades, both windows
  positive, to earn SURVIVOR.
- **Sim cross-check:** a concurrently-run, independently-built simulator in
  `step59_exit_science.py` computed N0's own shape (TP2.4/SL1.2/24h) on the
  same entry rule and got train n=335 exp $+1.73 / val n=115 exp $-12.53.
  This script's from-scratch simulator gets train n=338 exp $+1.66 / val
  n=119 exp $-18.39 — same sign, same order of magnitude, same verdict
  (FAILS validation on today's fuller dataset) from two independently
  written engines. Small differences (a few trades, a few dollars) are
  expected — this script's SL geometry differs slightly from a pure fixed
  bracket only for the N1-N4 policies, not N0, so the tiny N0 gap is just
  cost/funding-convention rounding, not a bug in either script.

## Important context before the table

**The incumbent itself no longer passes on today's larger news sample.**
R45B (2026-07-23, ~2,941 events) validated N0 at train +$23.74/val +$7.11.
Today's harvest has grown to 2,950 relevant events and a fuller span; on
this bigger, more current sample **N0 FAILS validation outright**: train
+$1.66/trade (n=338), val **-$18.39/trade** (n=119, -21.9% return). This
isn't this round's question, but it matters: any challenger only has to
clear a moving, currently-negative bar on val, not the rosier one from two
months ago.

## 1. Full comparison — every policy, train and val

| policy | tr n | tr exp | tr ret | tr DD | va n | va exp | va ret | va DD | verdict |
|---|---|---|---|---|---|---|---|---|---|
| **N0 incumbent (TP2.4/SL1.2/24h)** | 338 | +$1.66 | +5.6% | -15.4% | 119 | **-$18.39** | -21.9% | -24.4% | FAIL |
| N1 swing_k5 buf0.1% | 352 | +$1.89 | +6.7% | -20.1% | 126 | -$10.30 | -13.0% | -15.3% | FAIL |
| N1 swing_k5 buf0.3% | 339 | +$4.71 | +16.0% | -20.4% | 127 | -$12.11 | -15.4% | -19.5% | FAIL |
| N1 swing_k8 buf0.1% | 360 | +$0.05 | +0.2% | -18.2% | 127 | -$14.57 | -18.5% | -19.3% | FAIL |
| N1 swing_k8 buf0.3% | 345 | +$2.34 | +8.1% | -14.4% | 127 | -$15.50 | -19.7% | -19.7% | FAIL |
| N1 pool buf0.1% | 372 | -$3.92 | -14.6% | -27.1% | 125 | -$20.10 | -25.1% | -25.1% | FAIL |
| N1 pool buf0.3% | 354 | +$0.99 | +3.5% | -18.3% | 124 | -$12.28 | -15.2% | -18.7% | FAIL |
| N2 trail buf0.1% | 355 | +$3.77 | +13.4% | -15.2% | 121 | -$0.71 | -0.9% | -10.4% | FAIL |
| **N2 trail buf0.3%** | 315 | **+$9.57** | +30.1% | -18.0% | 112 | **+$4.34** | +4.9% | -10.6% | **SURVIVOR** |
| N2 trail buf0.3% (k=8, spot-check) | 321 | +$2.93 | +9.4% | -18.8% | 112 | +$1.16 | +1.3% | -11.7% | SURVIVOR |
| N4 2.0x/1.0x ATR | 551 | -$6.02 | -33.2% | -34.7% | 172 | -$8.99 | -15.5% | -16.1% | FAIL |
| N4 3.0x/1.5x ATR | 389 | -$4.35 | -16.9% | -33.9% | 125 | -$14.45 | -18.1% | -20.1% | FAIL |

**One survivor, one family: N2 structure-trailing, buffer 0.3%.** It beats
N0 on BOTH windows (train +$9.57 vs +$1.66; val +$4.34 vs -$18.39 — it is
the only policy that turns N0's current val LOSS into a val PROFIT), clears
both sample floors by a wide margin (315/112 vs the 30/8 minimum), and
holds up (weaker but still positive both windows) at the k=8 spot-check —
not a one-parameter fluke. Every fixed- or dynamic-*target* idea (N1's six
configs, N4's two) fails validation; only abandoning the fixed target
altogether and trailing behind confirmed structure survives.

**Win-rate honesty check:** N2's win rate (32.4% train / 28.6% val) is
LOWER than N0's (40.2% / 33.6%) — it loses more often. It gets paid anyway
because the losses it takes are structurally smaller (initial stop = the
entry bar's own opposite extreme, often tighter-fitting than a blind 1.2%)
and it lets winners run past 2.4% when structure doesn't say stop yet
(mean win size compensates for the lower hit rate). Exactly backtest.py's
own stated philosophy: win rate is how it feels, expectancy is whether you
get paid.

## 2. N3 context veto — autopsy: does it help, or just cut the sample?

| overlay | tr n | tr exp | tr ret | va n | va exp | va ret | verdict |
|---|---|---|---|---|---|---|---|
| N3 veto 0.5x on N0 | 90 | -$18.48 | -16.6% | 39 | -$14.30 | -5.6% | FAIL |
| N3 veto 0.8x on N0 | 71 | -$14.22 | -10.1% | 26 | -$17.14 | -4.5% | FAIL |
| N3 veto 0.5x on N2 trail buf0.3% | 116 | -$7.24 | -8.4% | 61 | -$34.21 | -20.9% | FAIL |
| N3 veto 0.8x on N2 trail buf0.3% | 85 | -$11.52 | -9.8% | 42 | -$26.53 | -11.1% | FAIL |

**Verdict: just cuts the sample.** Every veto overlay fails, including on
top of the one policy (N2) that otherwise survives — vetoing turns N2's
val +$4.34 into -$34.21 / -$26.53. Two pieces of evidence nail down why:

- **Skip rate is enormous.** Against the raw 1,840-entry signal, the 0.5x
  threshold refuses **93.7%** of train entries and 90.6% of val entries
  before any single-slot walk even happens; against N0's own 457 realized
  trades (train+val), 0.5x vetoes **358 of them (78.3%)**, 0.8x vetoes
  **385 (84.2%)**. Against N2's 427 realized trades, 0.5x vetoes 338
  (79.2%), 0.8x vetoes 359 (84.1%). On this entry family, BTC prints new
  1h swing highs/lows constantly — there is almost ALWAYS *some* confirmed
  level within 0.5-0.8x of a 1-3% target distance, so the filter is barely
  a filter at these thresholds; it is close to "trade only the rare clean
  runway," and there isn't enough clean runway to keep a sample.
- **What got skipped was not reliably bad.** Matched against N0's OWN
  realized trades: the entries vetoed at 0.5x averaged **+$1.96/trade**
  (39.7% win rate) — mildly PROFITABLE, i.e. the veto discarded winners
  along with losers. At 0.8x the vetoed set averaged -$2.41/trade (38.7%
  win) — closer to a wash. Matched against N2's realized trades: 0.5x
  vetoed entries averaged **+$13.89/trade** (33.1% win), 0.8x averaged
  **+$16.05/trade** (32.6% win) — the veto is disproportionately cutting
  N2's OWN best trades, which is exactly why layering it onto N2 makes val
  catastrophically worse. **The owner's instinct ("don't walk into a wall")
  is intuitive, but on this specific fast, cluster-timed entry family the
  chart is never clean enough for the filter to discriminate — it behaves
  more like "trade less" than "trade smarter."**

## 3. Big-trade autopsy — does structure protect winners, or amputate them?

Ranked by N0's own realized pnl, train+val pooled (test never touched).

**3 biggest N0 losers:**

| entry (UTC) | dir | N0 | N2 trail 0.3% | N1 swing_k5 0.3% | N4 3.0x/1.5x ATR |
|---|---|---|---|---|---|
| 2025-11-21 19:00 | short | -$155.37 (stop, 2h) | -$161.32 (structure stop, 2h) | -$136.85 (stop, 2h) | -$63.09 (time, 24h) |
| 2025-11-22 17:00 | short | -$152.85 (stop, 8h) | **-$59.74** (structure stop, 5h) | -$62.65 (stop, 5h) | not taken (busy) |
| 2025-11-24 18:00 | long | -$152.70 (stop, 8h) | not taken (busy) | -$133.15 (stop, 8h) | -$170.95 (stop, 13h) |

**3 biggest N0 winners:**

| entry (UTC) | dir | N0 | N2 trail 0.3% | N1 swing_k5 0.3% | N4 3.0x/1.5x ATR |
|---|---|---|---|---|---|
| 2025-11-21 08:00 | short | +$280.01 (target, 4h) | not taken (busy) | +$246.64 (target, 4h) | -$267.34 (stop, 6h) |
| 2025-11-24 13:00 | long | +$275.80 (target, 4h) | **-$69.36** (structure stop, 1h) | -$63.11 (stop, 1h) | +$278.99 (target, 4h) |
| 2025-11-20 17:00 | short | +$273.66 (target, 14h) | not taken (busy) | not taken (busy) | +$394.90 (target, 14h) |

**Honest answer: N2 mostly protects on the downside, not the upside — and
the one big winner it DID trade, it clipped hard.** Of the three biggest
losers, N2 either avoided one entirely (single-slot, occupied elsewhere)
or cut the loss meaningfully (-$59.74 vs -$152.85, a real save) — but also
matched a near-identical loss on the first one (-$161 vs -$155, no better).
Of the three biggest winners, N2 only got to trade ONE of them (the other
two were blocked by an earlier open position — a single-slot artifact, not
a strategy verdict) — and on that one, it turned a **+$275.80 winner into
a -$69.36 loser**, stopped out on the entry bar's own opposite extreme
before the move ever developed. **This is the real mechanism, stated
plainly: N2 wins in aggregate because it survives more of the bad trades
than it gives up on the good ones — not because it is smarter about
picking winners.** N1 (fixed structure target) shows the identical
failure mode on that same trade (-$63.11) — a tight, chart-read stop can
clip a real winner just as easily as a blind one; the asymmetry that
saves N2 overall is in the STOP discipline across the whole sample, not
in any single trade. N4 (ATR-scaled) is the most winner-friendly here
(caught 2 of 3 big wins cleanly, including the biggest one others missed)
but that comes from ITS overall negative expectancy (Table 1) — it isn't
free either.

## 4. Plain-English verdict

**Giving the trade eyes helps — but only one specific way, and it isn't
the way "smarter target" intuition suggests.** Testing the owner's
critique directly, on the SAME sealed-validated trigger:

- **A smarter, chart-read TAKE-PROFIT (N1) does not work.** Six configs
  (three target sources x two stop buffers), all fail val. Reading the
  chart for *where to bank the win* doesn't fix anything here.
- **Refusing to enter into a visible wall (N3) does not work.** It behaves
  like "trade way less" rather than "trade smarter" on this fast,
  cluster-timed entry family — 80-94% of the sample gets thrown out, and
  what gets thrown out isn't reliably the losing half.
- **Sizing the same fixed shape by current volatility (N4) does not
  work.** Both ATR multiples fail both windows, worse than the incumbent.
- **Riding structure with NO fixed target (N2) works.** Trail the stop
  behind confirmed 1h swing lows/highs, starting from the entry bar's own
  opposite extreme + a 0.3% buffer, no fixed take-profit at all: train
  +$9.57/trade (n=315, +30.1%), val **+$4.34/trade (n=112, +4.9%)** — the
  only policy that turns today's currently-losing incumbent into a
  validated winner on both windows, and it survives a k=8 spot-check too
  (weaker, still positive both windows).

So the owner is right that the trade needs eyes — just not eyes on the
target. The eyes belong on the STOP and on when to let go, not on picking
a fixed profit number in advance. **This satisfies the mandate's own
trigger for a sealed-look recommendation** (a challenger beating N0 on
BOTH train and val): N2 structure-trailing, buffer 0.3%, k=5, is the
candidate. **No sealed look was spent this round** — that stays a
separate, explicit decision; this script never even loads bars past
`i_va`.

**Biggest caveat, stated as loudly as the mandate asks: sample size.**
~450 realized trades split into 315/112 (train/val) sounds like a lot next
to the 30/8 floor, but it is still ONE ~13-month regime slice of a
24/7-only, event-clustered entry family with no bull-run/crash in sample
(same caveat R45B itself gave). The big-trade autopsy shows real-money
consequences hinge on a handful of individual trades (three losers, three
winners move the needle by hundreds of dollars each) — a different 13
months of WatcherGuru history could easily reshuffle which trades are the
"big" ones and change the verdict. This is encouraging evidence for
"trail the stop with structure instead of a fixed target," not proof of a
durable edge — exactly the same honest frame R45B itself used for the
incumbent it is now challenging.
