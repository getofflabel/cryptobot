# ROUND 83 — DOES THE EYE IMPROVE THE STRATEGIES WE ALREADY OWN?

Research only. Code: `step83_eye_filter.py`. Full data: `step83_table.csv`
(108 rows: 6 strategies x 2 assets x 3 splits x 3 veto variants, minus a
few empty cells) and `step83_live_anecdote.json` (the 9 live trades).

## METHOD, IN ONE PARAGRAPH

For each of the six strategies below, the entry logic and the exit
convention were both imported directly from the file that already owns
them (never retyped) and run through the project's real `backtest.
run_backtest` engine (full costs, real funding, maker execution) or, for
strategy A, `step65_news_eyes.simulate` — the same event-driven simulator
newsdesk's live N2 exit already uses. That produced each strategy's
REALIZED trade list, chronological 60/20/20, sealed test never touched.
Every realized trade was then looked up against `step82_eye.
label_eye_states`'s vectorized eye read AT THAT TRADE'S OWN ENTRY BAR
(computed once per asset/timeframe on the full causal history, so slicing
elsewhere never changes what the eye saw). Three veto rules partition the
realized trades into KEPT/SKIPPED:

- **veto_tradeable** — skip if `eye.tradeable == False`
- **veto_messy** — skip if `eye.quality == "messy"`
- **routed** — skip UNLESS `eye.best_tool` matches the strategy's assigned
  tool (ROUTE_MAP, argued in the code's docstring: breakout->A/C/E,
  trend-follow->D/F, range-fade->B)

This is a **partition of realized trades**, not a re-simulation with
freed-up capacity — it directly answers "would the eye have caught the
losers", the round's actual question, without the confound of a gated
state machine rescheduling into a different trade later. Stated once,
here, honestly.

**Dumb-veto control**: for every veto rule, 200 draws of "remove this many
trades at random from the same realized list" — reported as the
percentile the eye's actual result falls at. >=90th percentile = the eye
is clearly better than chance at finding losers / clearly better than
chance at keeping a winning subset. <=10th percentile = the eye is
**actively worse than chance** — an anti-signal. Anything in between: **no
information content**, and is reported as such, per the mandate.

## THREE HONEST RECONSTRUCTION NOTES

1. **B's actual live threshold is RSI3 < 10**, not "< 15" as the round
   brief remembered it — `daily_pick.py` line 366 is ground truth
   ("reconstructed exactly as it trades today" overrides the brief's
   memory). Used 10.
2. **D reproduces round 58's own published numbers EXACTLY**: this
   script's BTC hidden-divergence rebuild gets 66 train trades at
   $74.22/t and 24 val trades at $31.99/t — bit-for-bit the numbers in
   `RESEARCH_LOG.md`'s round 58 entry. Strong confirmation the
   reconstruction is faithful.
3. **E is a near-exact, not bit-identical, reproduction**: train matches
   round 56's published number exactly (52 trades, $15.45/t); val is 25
   trades at $68.26/t here vs. the published 24 trades at $72.51/t. The
   one-trade drift is explained by data-cache growth (more BTC bars have
   accumulated since round 56/58 ran, which shifts the exact 60/20/20
   split point by a bar or two) — not a reconstruction error.
4. **B's "routed" variant is undefined (NaN)** on both assets: in this
   dataset, the eye's `best_tool` **never once** reads "range-fade" at any
   of B's washout entry bars. That's itself a finding about the eye's own
   vocabulary, not a bug — see verdict.
5. Strategy A was run on **BTC's own 1h candles for the BTC leg and ETH's
   own 1h candles for the ETH leg** (WatcherGuru headlines are market-wide;
   the live newsdesk book currently only trades BTC — this reuses the
   identical trigger logic on ETH's own candles as the natural
   generalization the round asked for).

---

## PER-STRATEGY RESULTS (pooled train+val, sealed test never touched)

Values are **expectancy $/trade after full costs**. "Skipped PnL" is the
aggregate realized PnL of the trades each veto would have removed —
negative is good (it means the eye correctly found losers).

### A. News momentum + live N2 structure-trailing exit (1h)

| Asset | Before (n) | Veto: tradeable | Veto: messy | Routed (breakout) |
|---|---|---|---|---|
| BTC | $8.19 (427) | after $8.05 (129 kept) · skip PnL **+$2,461** · control pctile **54%** | after **-$4.18** (151 kept) · skip PnL +$4,129 · control pctile 20% | after $10.00 (57 kept) · skip PnL +$2,929 · control pctile 53% |
| ETH | $5.19 (470) | after $16.15 (126 kept) · skip PnL +$406 · control pctile 71% | after $23.67 (157 kept) · skip PnL **-$1,274** · control pctile **86%** | after $29.00 (43 kept) · skip PnL +$1,194 · control pctile 74% |

**Verdict: no clean signal.** BTC's messy-veto is actively counter-
productive (skips a NET-POSITIVE set of trades, 20th percentile — worse
than 80% of random draws). ETH's messy-veto looks decent (86th
percentile) but doesn't clear the 90% bar either asset. None of the three
BTC variants beat random; only the messy-veto on ETH comes close.

### B. RSI3<10 washout dip-buy + turn-candle (1h) — daily_pick.py

| Asset | Before (n) | Veto: tradeable | Veto: messy | Routed (range-fade) |
|---|---|---|---|---|
| BTC | -$6.42 (47) | after $5.09 (14 kept) · skip PnL -$373 · control pctile 69% | after **+$24.87** (20 kept) · skip PnL **-$799** · control pctile **98%** | n/a — eye never tags a washout entry "range-fade" |
| ETH | $9.78 (47) | after $35.58 (10 kept) · skip PnL +$104 · control pctile 81% | after **+$54.26** (15 kept) · skip PnL **-$354** · control pctile **98%** | n/a |

**Verdict: THE ONE CLEAR WIN.** `veto_messy` clears the 98th percentile
against 200 random-skip draws on **both** assets — the eye's skipped
trades are net losers on both books, and what's left is a materially
better strategy: BTC flips from a loser (-$6.42/t) to a real winner
(+$24.87/t); ETH nearly 6x's its expectancy ($9.78 -> $54.26/t). This is
not noise — it clears the bar the dumb control was built to test.

### C. Donchian-20 breakout long (1h)

| Asset | Before (n) | Veto: tradeable | Veto: messy | Routed (breakout) |
|---|---|---|---|---|
| BTC | $5.88 (470) | after $46.41 (192 kept) · skip PnL -$6,146 · control pctile 83% | after $32.56 (195 kept) · skip PnL -$3,585 · control pctile 78% | after **$70.49** (132 kept) · skip PnL -$6,540 · control pctile **90%** |
| ETH | -$17.54 (420) | after **$35.63** (161 kept) · skip PnL **-$13,102** · control pctile **93%** | after $29.53 (168 kept) · skip PnL -$12,326 · control pctile 85% | after -$2.38 (109 kept) · skip PnL -$7,105 · control pctile 53% |

**Verdict: real signal, asset-dependent.** ETH's tradeable-veto and BTC's
routed-veto both clear 90%+ — the eye materially improves donchian-20 on
each asset via a DIFFERENT variant, which is itself informative (no
single veto rule is universally best; asset regime matters). Genuinely
promising but not consistent enough across assets/variants to call a slam
dunk.

### D. Hidden RSI(14) divergence, 4h (diver.py's frozen k=8/3.54%/3x/48h)

| Asset | Before (n) | Veto: tradeable | Veto: messy | Routed (trend-follow) |
|---|---|---|---|---|
| BTC | **$62.96 (90)** | after **-$95.78** (14 kept) · skip PnL **+$7,007** · control pctile **8%** | after $92.67 (18 kept) · skip PnL +$3,998 · control pctile 58% | after -$71.81 (6 kept) · skip PnL +$6,097 · control pctile 33% |
| ETH | -$75.02 (84) | after -$123.87 (18 kept) · skip PnL -$4,072 · control pctile 25% | after -$10.10 (19 kept) · skip PnL -$6,110 · control pctile 84% | after -$132.75 (7 kept) · skip PnL -$5,373 · control pctile 35% |

**Verdict: the eye actively HURTS this strategy on BTC.** The
tradeable-veto sits at the 8th percentile — worse than 92% of random
skips — because it disproportionately removes BTC's *winning* trades
(skip-PnL is **positive** $7,007, meaning the vetoed set was a net
winner). D is already gated to the 4h vol_gated_ma trend champion in its
own entry logic; layering the eye's independent "tradeable" read on top
doesn't add information, it subtracts a profitable subset. Live BTC hidden
divergence should NOT get an eye gate.

### E. CHoCH + confluence>=2, 1h (step56's sealed k=8/tgt2x config)

| Asset | Before (n) | Veto: tradeable | Veto: messy | Routed (breakout) |
|---|---|---|---|---|
| BTC | **$32.60 (77)** | after -$15.63 (29 kept) · skip PnL +$2,963 · control pctile 32% | after **-$67.31** (39 kept) · skip PnL +$5,135 · control pctile **6.5%** | after $106.41 (14 kept) · skip PnL +$1,020 · control pctile 67% |
| ETH | -$98.96 (68) | after -$44.67 (35 kept) · skip PnL -$5,166 · control pctile 79% | after -$93.79 (35 kept) · skip PnL -$3,447 · control pctile 56% | after **$150.41** (20 kept) · skip PnL **-$9,738** · control pctile **99.5%** |

**Verdict: mixed, with one loud warning.** BTC's messy-veto is at the
6.5th percentile — actively harmful, removing a strongly net-positive
subset ($5,135 skip-PnL). This makes structural sense: CHoCH is a
structure-break strategy, and "messy" compression is frequently the setup
*right before* the break that pays off — vetoing chop cuts the winners,
not the losers. ETH's routed-veto, by contrast, is the single strongest
result in the whole study (99.5th percentile) — but that's one cell, on a
strategy that was already negative-expectancy before the filter (-$98.96
on 68 trades), so treat it as a promising lead, not a standing result.

### F. Vol-gated 4h trend champion (vol_gated_ma 20/100, gate 1.5)

| Asset | Before (n) | Veto: tradeable | Veto: messy | Routed (trend-follow) |
|---|---|---|---|---|
| BTC | **$304.69 (60)** | after $316.11 (17 kept) · skip PnL +$12,907 · control pctile 44% | after $785.98 (18 kept) · skip PnL +$4,134 · control pctile 80% | after $640.21 (9 kept) · skip PnL +$12,519 · control pctile 72% |
| ETH | $163.17 (53) | after $105.25 (20 kept) · skip PnL +$6,543 · control pctile 49% | after -$109.65 (20 kept) · skip PnL +$10,841 · control pctile 26% | after **-$775.75** (10 kept) · skip PnL +$16,405 · control pctile **8.5%** |

**Verdict: the eye is redundant-to-harmful here.** F is already a
trend/volatility filter by construction; every one of the eye's veto
variants removes trades with POSITIVE aggregate PnL on both assets (every
skip-PnL in this row is positive), and ETH's routed-veto is actively
harmful at the 8.5th percentile. The eye's structure read is highly
correlated with what vol_gated_ma already encodes — there's nothing left
for it to add, and the redundant filter mostly just shrinks the sample.

---

## SCOREBOARD: WHICH VETO VARIANT WINS?

Across the 12 (strategy x asset) pooled pairs where the comparison is
defined (B's routed variant is undefined — see note 4 above):

| Variant | Mean control percentile | Median | Strong pass (>=90th pctile) | Actively harmful (<=10th pctile) |
|---|---|---|---|---|
| `veto_tradeable` | 57.2% | 61.5% | 1 / 12 (C-ETH) | 1 / 12 (D-BTC) |
| `veto_messy` | 64.3% | **78.8%** | 2 / 12 (B-BTC, B-ETH) | 1 / 12 (E-BTC) |
| `routed` | 58.3% | 59.5% | 2 / 10 (C-BTC, E-ETH) | 1 / 10 (F-ETH) |

`veto_messy` has the best average and median — **but that entire edge is
carried by strategy B alone.** Drop B and veto_messy's median on the
remaining 10 pairs falls to roughly the same no-signal band as the other
two variants. There is no single veto rule that reliably beats random
skipping across the board; the honest reading is "the eye's information
content is real but concentrated in one strategy type", not "wire the eye
in everywhere."

---

## THE LIVE-TRADE ANECDOTE (9 closed Supabase trades, all July 2026)

**Anecdote, not evidence** — n=9 (8 real trades + 1 pipeline smoke test),
included because the owner will want to see it.

Pulled from the real Supabase event log (`cryptobot_log_tail` RPC) and
matched entry<->exit by book/symbol/timing. `chart_reader.read_chart()`
(the real per-bar reference implementation, not the vectorized copy) was
run on live candle history up to each trade's own entry moment.

| Book | Symbol | Entry (UTC) | Real PnL | Eye read at entry | Would `veto_messy` skip it? |
|---|---|---|---|---|---|
| shorts_lab | BTC | 07-23 18:07 | **-$31.34** | clean downtrend, at range low, expanding — trend-follow | No |
| newsdesk | BTC | 07-24 02:21 | **-$58.16** | **messy** downtrend, pulling back — stand aside | **Yes** |
| daily_pick | SOL short | 07-24 06:03 | **-$5.37** | clean uptrend, pulling back, expanding — trend-follow | No |
| daily_pick | ETH long | 07-24 08:00 | **-$17.80** | **messy** downtrend, pulling back — stand aside | **Yes** |
| daily_pick | ETH long | 07-24 10:00 | **-$18.39** | **messy** downtrend, pulling back — stand aside | **Yes** |
| daily_pick (washout) | ETH long | 07-24 14:00 | +$6.97 | clean downtrend, at range low, expanding — trend-follow | No |
| tradfi_engine | oil (proxy)* | 07-24 18:28 | +$58.39 | **messy** uptrend, at range high, contracting — stand aside | **Yes** |
| daily_pick | SOL short | 07-24 18:00 | +$8.57 | clean uptrend, pulling back, expanding — trend-follow | No |
| amp (pipeline test) | ETH | 07-24 02:55 | +$0.44 (test, not a real signal) | messy — stand aside | Yes |

\* CL=F isn't in this repo's cache; the read used BloFin's WTIOIL-USDT 1h
candles as the closest available proxy — flagged, not claimed exact.

**On the 8 real trades**, total PnL was **-$57.13**. The messy-veto would
have skipped 4: three real losers (newsdesk BTC -$58.16, ETH -$17.80, ETH
-$18.39 — three of the book's four worst trades) at the cost of the
single biggest winner (oil +$58.39, proxy-asset caveat applies). Net:
skipped-set PnL = **-$35.96** (correctly loss-heavy), and the retained set
improves from -$7.14/trade to -$5.29/trade. Directionally consistent with
this round's headline finding (the veto is real but imperfect, and it can
cost you your best trade along with your worst ones) — but n=9 is far too
small to be anything but a corroborating anecdote.

---

## HONEST VERDICT: SHOULD THE EYE BE WIRED INTO THE LIVE BOOKS?

**Selectively yes, not broadly.**

1. **Wire `veto_messy` into daily_pick's washout trigger (strategy B).**
   This is the one result in the whole study that clears the dumb-control
   bar on both assets (98th percentile each) — the eye correctly
   identifies which washout dip-buys are firing into unreadable chop, and
   cutting them turns a marginal/losing setup into a clearly profitable
   one on both BTC and ETH. Small, cheap, targeted change with real
   evidence behind it. This also matches the live anecdote: the ONE
   strategy-B trade in the 9-trade sample (the washout ETH long) was
   already in the eye's "clean, tradeable" bucket and was a winner.

2. **Do NOT gate news momentum (A), CHoCH (E), hidden divergence (D), or
   the vol-gated trend champion (F) on the eye as a blanket rule.** On
   every one of these, at least one veto variant is statistically
   indistinguishable from randomly skipping the same number of trades,
   and three specific cells are actively harmful (D-BTC tradeable-veto,
   E-BTC messy-veto, F-ETH routed-veto) — each because the strategy
   already encodes trend/structure context in its own entry logic (a
   trend-alignment gate, a structure-break definition, a volatility
   filter), so the eye's read is redundant with what these strategies
   already require, and "messy" specifically tends to fire on the
   COMPRESSION that precedes a breakout strategy's biggest winners —
   exactly the setups worth taking.

3. **Donchian-20 (C) is the one open lead worth a follow-up round**: two
   different veto variants (tradeable on ETH, routed on BTC) clear 90%+,
   which is promising but not the same variant on both assets — before
   shipping this, a next round should test whether ONE fixed veto rule
   (not "whichever wins on this asset") still beats random out-of-sample.

4. **This confirms, and sharpens, R82's structural finding.** The eye
   does carry real information about when trading works — but that
   information is not evenly useful. It helps most on a strategy that
   trades a raw oscillator threshold with NO structural context of its
   own (B). It adds little-to-nothing, and sometimes actively hurts, on
   strategies that already have trend/structure/volatility gates baked
   into their own entry rule (D, E, F) or that are inherently a
   sudden-event trigger the eye's trailing-window read can't anticipate
   (A). The lesson for the live books isn't "add the eye everywhere" —
   it's "add the eye where the strategy doesn't already have eyes of its
   own."
