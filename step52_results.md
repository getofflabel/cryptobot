# Round 52 — BloFin synthetic TradFi perps: venue census + strategy transfer

Research only. Public BloFin market-data endpoints (PROD: `openapi.blofin.com`)
plus yfinance. No live orders. Does not touch `gold_book.py` / `daemon.py` /
`hourly.py`. Script: `step52_blofin_tradfi.py`. Data: 28 files named
`data_blofin_<SYM>_<TF>.parquet` (14 symbols x {1d, 1h}).

## Two findings that reframe the whole brief, stated up front

**1. BloFin's DEMO (paper) book cannot trade 11 of these 14 instruments at
all.** The task described these as living on "BloFin's demo exchange."
Measured directly: `XAU-USDT`, `XAG-USDT`, `MSFT-USDT`, `AAPL-USDT`,
`GOOGL-USDT`, `NVDA-USDT`, `META-USDT`, `COIN-USDT`, `AMZN-USDT`,
`MSTR-USDT`, `HOOD-USDT` all return `"Parameter instId error"` on
`demo-trading-openapi.blofin.com` — they don't exist there. `WTIOIL-USDT`
returns a live ticker on demo but **zero candles** (unusable). Only
`SPX-USDT` and `TSLA-USDT` are fully functional on demo. Every symbol below
is fully live with real history on **PROD** (`openapi.blofin.com`), which is
where all data in this round came from, via public unauthenticated
endpoints. If the owner wants to paper-test any of these before risking
real money, BloFin's own demo environment currently can't do it for most of
them — that gap needs to close (or the owner needs to accept going straight
to small real-money positions) before any of this deploys.

**2. `SPX-USDT` is not the S&P 500.** Its instrument spec marks
`assetClass: "Crypto"` (every real stock/commodity perp here is marked
`"Stocks"` or the commodities are also `"Crypto"` but at correct price
scale — see below), it trades at **$0.33–$1.30** across its full history
while the real S&P 500 traded at **~7,400–7,500** over the same dates
(confirmed via yfinance `^GSPC`), and its price range/history matches the
known SPX6900 memecoin (ticker `SPX`), not an index tracker. Daily-return
correlation to `^GSPC` is a weak 0.34 — noise, not tracking. **It is
flagged, not backtested against the real S&P 500**, because that would be
comparing two unrelated assets. Every other instrument in this round (gold,
silver, oil, and all 10 single stocks) genuinely does track its real
underlying — see the correlation column below — so this is a one-off
mislabeled listing, not a pattern.

---

## PHASE 1 — Venue census

All spans are the FULL history available from BloFin PROD as of 2026-07-23,
paginated via `exchange.py`'s `BlofinExchange` adapter to the venue's true
listing date (confirmed: pagination always bottoms out exactly at each
instrument's `listTime`, not at some arbitrary API cap).

| Symbol | Class | 1d span | 1h bars | Contract val | Max lev | 24h vol (USDT) | Funding/8h | Demo status |
|---|---|---|---|---|---|---|---|---|
| XAU-USDT | commodity (gold) | 193b, 2026-01-12→07-23 | 4,624 | 0.001 | 100x | $5.38M | −0.002% | **NOT on demo** |
| XAG-USDT | commodity (silver) | 197b, 2026-01-08→07-23 | 4,723 | 0.01 | 100x | $2.20M | +0.019% | **NOT on demo** |
| WTIOIL-USDT | commodity (oil) | 58b, 2026-05-27→07-23 | 1,386 | 0.01 | 20x | $2.48M | +0.018% | ticker OK, **0 candles** |
| SPX-USDT | *memecoin, see above* | 632b, 2024-10-30→07-23 | 15,159 | 10 | 75x | $0.11M | +0.004% | full |
| MSFT-USDT | single stock | 95b, 2026-04-20→07-23 | 2,267 | 0.01 | 20x | $0.38M | +0.002% | **NOT on demo** |
| AAPL-USDT | single stock | 109b, 2026-04-06→07-23 | 2,603 | 0.01 | 20x | $0.19M | −0.021% | **NOT on demo** |
| GOOGL-USDT | single stock | 120b, 2026-03-26→07-23 | 2,866 | 0.01 | 20x | $0.75M | +0.021% | **NOT on demo** |
| NVDA-USDT | single stock | 120b, 2026-03-26→07-23 | 2,866 | 0.01 | 20x | $0.38M | −0.001% | **NOT on demo** |
| META-USDT | single stock | 120b, 2026-03-26→07-23 | 2,866 | 0.01 | 20x | $0.31M | −0.020% | **NOT on demo** |
| COIN-USDT | single stock | 165b, 2026-02-09→07-23 | 3,946 | 0.01 | 20x | $0.17M | +0.019% | **NOT on demo** |
| AMZN-USDT | single stock | 165b, 2026-02-09→07-23 | 3,946 | 0.01 | 20x | $0.11M | −0.001% | **NOT on demo** |
| MSTR-USDT | single stock | 165b, 2026-02-09→07-23 | 3,946 | 0.01 | 20x | $0.40M | −0.001% | **NOT on demo** |
| HOOD-USDT | single stock | 172b, 2026-02-02→07-23 | 4,114 | 0.01 | 20x | $0.08M | −0.002% | **NOT on demo** |
| TSLA-USDT | single stock | 177b, 2026-01-28→07-23 | 4,234 | 0.01 | 20x | $1.09M | −0.000% | full |

**These listings are YOUNG.** Everything except `SPX-USDT` (Oct 2024, ~1.75y)
has 2–7 MONTHS of history, not years. `WTIOIL-USDT` is the youngest at
58 daily bars (~2 months). Any strategy that needs a real train/val/test
split (the repo's 60/20/20 with ≥30/≥8 trade minimums) is currently
data-starved on every BloFin-native TradFi perp except SPX — that's why
Phase 2 runs the actual gauntlets on 20 years of the REAL underlying
(yfinance) and only uses BloFin's own short history for the gold transfer
check and the census above.

**Funding is not negligible on the newer/thinner listings.** Annualizing the
observed 8h rate (×3/day ×365): XAG ≈ **+21%/yr**, WTIOIL ≈ **+20%/yr**,
GOOGL ≈ **+23%/yr** paid by longs — 2x the repo's flat 1bp/8h backtest
default. XAU/stocks mostly sit near zero. Any strategy holding these perps
for weeks (the breakout family below typically holds 10–40+ days) should be
re-costed with the REAL observed funding, not the flat default, before
sizing a live position.

### Tracking fidelity (BloFin perp vs real underlying, yfinance)

| Symbol | vs | Overlap (days) | Corr(daily ret) | Mean basis | Max basis |
|---|---|---|---|---|---|
| XAU-USDT | GC=F | 133 | **0.814** | +0.19% | 4.05% |
| XAG-USDT | SI=F | 135 | **0.764** | +0.30% | 12.29%* |
| WTIOIL-USDT | CL=F | 40 | **0.894** | −0.06% | 3.39% |
| SPX-USDT | ^GSPC | 432 | 0.336 (garbage — see flag above) | −99.99% | 100.0% |
| MSFT-USDT | MSFT | 66 | **0.961** | +0.01% | 1.67% |
| AAPL-USDT | AAPL | 76 | **0.924** | +0.05% | 2.20% |
| GOOGL-USDT | GOOGL | 82 | **0.795** | +0.14% | 7.25% |
| NVDA-USDT | NVDA | 82 | **0.946** | −0.03% | 2.98% |
| META-USDT | META | 82 | **0.877** | +0.02% | 6.94% |
| COIN-USDT | COIN | 114 | **0.962** | +0.03% | 5.07% |
| AMZN-USDT | AMZN | 114 | **0.901** | +0.06% | 3.70% |
| MSTR-USDT | MSTR | 114 | **0.949** | +0.09% | 6.00% |
| HOOD-USDT | HOOD | 119 | **0.904** | −0.14% | 9.19% |
| TSLA-USDT | TSLA | 122 | **0.933** | −0.06% | 4.21% |

*XAG's 12.29% max basis is a single-day outlier, not sustained drift (mean
basis is +0.30%, tight). Correlation and mean basis are the reliable
columns; max basis on any thin/new listing will show occasional spikes from
timestamp misalignment (BloFin's daily bar closes at UTC midnight; US
equity/futures daily bars close at US market close, ~6-8h earlier) as much
as real divergence — this is a measurement-alignment artifact worth
knowing about, not proof of a bad tracker. **Every non-memecoin instrument
tracks its underlying tightly (corr 0.76–0.96, mean basis under 0.3%).**
Liquidity correlates with tracking tightness: `HOOD` (lowest 24h volume,
$85K) has the widest max-basis noise (9.19%); `MSFT`/`COIN` (deeper books)
are tightest.

### Weekend behavior (1h bars: does the copy freeze while the real market is shut?)

Every instrument keeps trading through weekends with **zero dead/frozen
bars** (0.0% zero-range weekend bars across all 14 symbols) — BloFin is not
just holding the last print. But the market is meaningfully quieter:
average hourly range shrinks **60–75%** on Sat/Sun vs weekdays (e.g. XAU
0.48%→0.13%, AAPL 0.41%→0.19%, SPX 2.61%→2.08%). Read: these are
continuously-quoted synthetic trackers (likely maker/oracle-driven, not a
literal weekend freeze), but weekend fills would be into much thinner
liquidity than the weekday number suggests — a real consideration for any
strategy that would enter or exit on a weekend bar.

---

## PHASE 2a — Gold transfer check (donchian55+EMA20, round-48 sealed-PASS champion)

XAU-USDT's own history (193 daily bars) overlaps GLD from 2026-01-12 onward
(133 GLD bars in the same window). Running the validated shape on both:

**XAU-USDT: 0 trades. GLD: 0 trades**, in the overlap window.

Not a scripting bug — verified directly: XAU-USDT's all-time high in this
window (close $5,516 on 2026-01-28) occurred DURING the 55-bar warmup
period itself, so it's baked into the rolling 55-day-high the strategy
compares against, and price never cleared that bar again in the following
~130 days (138 post-warmup bars, 0 breakouts). **This is a data-starvation
result, not a strategy failure**: donchian55+EMA20 needs ~76 bars of warmup
before it can even emit a signal, and XAU-USDT's entire history is only
193 bars. The transfer check cannot be meaningfully run until XAU-USDT has
accumulated enough history for the channel to reset past its own early
spike — worth re-running in a few months, not concluding anything from now.

---

## PHASE 2b — Silver full gauntlet (SLV + SI=F, 20y daily, never tested before)

60/20/20 split, ≥30 train / ≥8 val trades required. 20 configs tested.

| Verdict | Count |
|---|---|
| SURVIVOR | 3 |
| INSUFFICIENT-SAMPLE | 4 |
| FAIL | 13 |

**All 3 survivors are the donchian breakout family — the SAME shape
validated on gold in round 48 — and it survives on BOTH silver instruments
independently:**

| Config | Symbol | Train (n / exp) | Val (n / exp) |
|---|---|---|---|
| donchian20 EMA20exit | SI=F | 86 / **+$97.91** | 32 / **+$157.23** |
| donchian55 EMA20exit | SI=F | 54 / **+$21.02** | 19 / **+$139.56** |
| donchian20 EMA20exit | SLV | 58 / **+$25.60** | 20 / **+$148.96** |

Val expectancy is HIGHER than train in all three — no in-sample decay. The
1-trend (MA crossover) family FAILED across the board on both silver
instruments (13/16 configs negative in train, val, or both) — exactly the
round-48 pattern where the breakout shape works on commodities and the MA
cross doesn't. **Caveat**: SLV's split lands train=2006-2018 (silver's dead
decade post-2011 crash) / val=2018-2022 (includes the 2020 COVID squeeze
and 2021 silver-squeeze meme rally) — val's strength partly reflects that
specific real rally, not proof the edge holds in a flat-silver regime. This
is a legitimate candidate for a lead-agent sealed look, with that caveat
attached.

---

## PHASE 2c — Single stocks full gauntlet (7 megacaps, 20y yfinance daily)

Same two families (1-trend MA cross + donchian breakout), same split/costs
convention as round 48's ETFs (1bp fee + 1bp slippage each side, no
funding — these are yfinance backtests of the real equity, not the BloFin
perp). 70 configs tested.

| Verdict | Count |
|---|---|
| SURVIVOR | 19 |
| INSUFFICIENT-SAMPLE | 48 |
| FAIL | 3 |

**GOOGL is the honest single-stock failure**: both donchian20 and
donchian55 breakout configs turned NEGATIVE in validation (−$4.46/t and
−$11.01/t) despite being positive in train — the only stock where the
breakout family didn't survive. Every 1-trend config on GOOGL landed
INSUFFICIENT-SAMPLE (too few MA crossovers over 20y to hit 30 train
trades). The other 6 stocks all produced at least one SURVIVOR.

Most trend-family (1-trend) configs across NVDA/TSLA/AMZN/META landed
**INSUFFICIENT-SAMPLE**, not FAIL — expectancy was positive but a slow
20/100 or 50/200 MA cross only fires 9–26 times over 20 years, under the
30-trade train bar. This is a sample-size ceiling of the shape on these
symbols, not a sign the edge is fake.

### The honest reframe: buy-and-hold and drawdown

Task-mandated check, and it matters. Buy-and-hold (same window, costs
included) dwarfs every trend/breakout expectancy number in raw return
terms — unsurprising for megacaps in a 20-year bull market:

| Symbol | Years | B&H return | B&H CAGR | B&H max DD |
|---|---|---|---|---|
| AMZN | 23.3y | +159,164% | +37.2% | −94.4% |
| MSFT | 32.3y | +102,747% | +24.0% | −74.6% |
| AAPL | 36.5y | +31,278% | +17.1% | −82.2% |
| NVDA | 22.0y | +29,774% | +29.6% | −89.7% |
| TSLA | 12.8y | +9,388% | +42.6% | −73.6% |
| GOOGL | 17.5y | +5,182% | +25.4% | −65.3% |
| META | 11.3y | +716% | +20.3% | −76.7% |

**The 1-trend family does NOT clear this bar as a genuine edge** — it's
mostly the same beta with turnover drag. Example: AAPL's 20/100-trend
survivor has a worst-window drawdown of −78.7%, barely better than B&H's
−82.2%. It's long ~most of the time on a stock that mostly only goes up;
that's exposure, not skill, and its train→val expectancy ratio is weak
(val is 6–49% of train across the 1-trend survivors — real decay).

**The donchian-breakout family is a genuinely different, and better,
story** — it trades far less and exits when price falls under its EMA20,
which means it sits out the worst crashes instead of riding them:

| Symbol | Breakout worst-window DD | B&H DD | Val/train exp ratio |
|---|---|---|---|
| META | −29.8% | −76.7% | 1.69 (val > train) |
| MSFT | −40.7% | −74.6% | 0.06 (heavy decay) |
| TSLA | −36.4% | −73.6% | 0.49 |
| AAPL | −53.5% | −82.2% | 0.26 |
| NVDA | −63.1% | −89.7% | **1.10 (no decay)** |
| AMZN | −89.8% | −94.4% | 1.05 (but DD barely improved) |

This is the same "crash insurance, not skill" shape round 48 validated for
gold — real drawdown reduction (27–47 percentage points shallower than
buy-and-hold on 4 of 6 names) in exchange for giving up some upside, at a
genuinely positive expectancy per trade. **NVDA is the cleanest**: DD cut
from −89.7% to −63%/−35% AND val expectancy is essentially equal to (even
slightly above) train — the strongest sign of a real, non-decaying edge in
this whole batch. AMZN barely improves on drawdown at all (donchian20 train
DD −89.8% vs B&H −94.4%) — worth noting that the shape doesn't reliably
work on every name.

### Decade-by-decade consistency (train+val only, test sealed)

**NVDA donchian20+EMA20exit: positive in EVERY decade with data** —
1990s +$314/t (n=5), 2000s +$1,144/t (n=49), 2010s +$2,078/t (n=51), 2020s
+$21,387/t (n=4). Clean.

**AAPL donchian20/55+EMA20exit: positive in EVERY decade** — 1980s
+$590/+$957, 1990s +$3,574/+$1,113, 2000s +$11,328/+$4,967, 2010s
+$51,181/+$14,666 (donchian20 / donchian55). Clean, but note the 1-trend
AAPL family shares this all-decades-positive pattern too — for AAPL
specifically, this reads more like "AAPL basically never had a bad decade
long," consistent with the beta-not-skill caution above.

**MSFT breakout: ONE bad decade.** 2000s is negative for both donchian20
(−$1,096/t) and donchian55 (−$988/t) — the dot-com bust and 2000s chop hurt
MSFT specifically. Not all-decades-clean.

**AMZN donchian20: ONE bad decade** (2000s, −$428/t); donchian55 AMZN is
clean across all 4 decades (+$3,032/+$1,285/+$1,368/+$11,788). The N=55
variant is the more robust AMZN config.

**META/TSLA**: only 2010s+2020s exist in the data (both listed after
2010); both decades positive for both, but that's only 2 decades of
evidence — thinner support than NVDA/AAPL.

---

## PHASE 2d — Oil (WTIOIL-USDT): census/tracking only, per task

Round 48 already killed oil strategies (0 survivors on USO/CL=F across many
configs) — not re-run. Venue facts: 58 daily bars (youngest listing in this
batch, ~2 months), corr to CL=F 0.894, mean basis −0.06% (tight), but
**demo trading has zero candle history for this symbol** despite a live
ticker — the most broken demo entry in the batch.

---

## Verdicts and candidates for a lead-agent sealed look

Ranked by strength of evidence (none of these are sealed-test PASSes — that
requires a lead-agent decision to spend a test-window look):

1. **NVDA donchian20+EMA20exit — strongest new candidate.** SURVIVOR with
   comfortable sample (81 train / 28 val), val expectancy slightly EXCEEDS
   train ($881 vs $799 — no decay), all 4 decades with data are positive,
   and a real drawdown cut vs buy-and-hold (−63%/−35% vs B&H's −89.7%).
   This is the same donchian+EMA20-exit shape already sealed-PASS on gold —
   now showing the identical "less DD, real edge, no decay" signature on a
   completely different asset class independently.
2. **AAPL donchian20/55+EMA20exit** — SURVIVOR, all-decades-positive, big
   n (132/41 and 89/31), meaningful DD cut (−53.5% vs B&H −82.2%) — but
   weaker train→val consistency (26% ratio) than NVDA, so second in line.
3. **Silver donchian20+EMA20exit (SI=F AND SLV independently)** — same
   validated shape surviving on BOTH silver instruments with val > train
   expectancy on both, matching gold's cross-instrument robustness pattern
   from round 48. Caveat: val window benefits from the real 2020-21 silver
   squeeze, so the edge is less regime-tested than NVDA's.
4. Everything else SURVIVOR (MSFT, AMZN, META breakout family) is real but
   has at least one honest wrinkle (a negative decade, weak DD improvement,
   or heavier train→val decay) — logged, not promoted ahead of the above.

**Biggest venue risk found this round**: not tracking fidelity (that's
good — 0.76–0.96 correlation on every real instrument) — it's that
**BloFin's demo/paper environment doesn't have most of these listings at
all**. Any deployment plan needs to either accept trading real (if small)
size on PROD from day one, or wait for BloFin to finish provisioning demo
for XAU/XAG/single-stocks. Second risk: these are 2–7 month-old listings —
every number in the "PROD-native" gold transfer check and the venue census
itself is thin-sample by definition; the silver and stock gauntlet numbers
above are trustworthy because they ran on 20 years of the REAL underlying,
not BloFin's own short history, but the actual BloFin perps have not yet
been tested through a full market cycle themselves.
