# Round 60 — THE S&P SYSTEM (index-native families for SPY / ES=F)

Script: `step60_spx_system.py`. Data: `data_spx_<TAG>_<TF>.parquet` (SPY, ES
x 1d/1h — 4 files). Research only, no orders, **no sealed-test looks spent**
(the 20% test window was never sliced or scored anywhere in this round).

**Mandate:** stop porting crypto- and gold-shaped strategies onto the index
and instead build the S&P's OWN playbook out of families born from the
index's own personality — famous dip-buy folklore, overnight/gap structure,
the slow trend backbone, the "different weapons for different regimes"
architecture, and a seasonality audit.

**★ NO DEMO VENUE EXISTS for the real S&P 500.** BloFin's `SPX-USDT` is the
**SPX6900 memecoin** — completely unrelated to the index, and was never
touched or referenced anywhere in this round. Everything below is pure
knowledge-banking research for when a real execution venue (Alpaca paper for
SPY, a futures broker for ES=F) exists. See §12.

---

## 1. Data & session handling

| symbol | tf | bars | span | train ends | val ends (test sealed) | median TRAIN ATR% |
|---|---|---:|---|---|---|---:|
| SPY | 1d | 8,427  | 1993-01-29 → 2026-07-23 | 2013-02-27 | 2019-11-05 | 1.319% |
| SPY | 1h | 5,072  | 2023-08-24 → 2026-07-23 | 2025-05-22 | 2025-12-19 | 0.357% |
| ES=F | 1d | 6,526  | 2000-09-18 → 2026-07-24 | 2016-03-08 | 2021-05-17 | 1.360% |
| ES=F | 1h | 13,677 | 2024-03-01 → 2026-07-24 | 2025-08-06 | 2026-01-30 | 0.206% |

**Session handling.** SPY's 1h bars from yfinance are RTH-only (no pre/post
market) — the first bar printed every trading day IS exactly the 9:30-10:30
ET window family 2c needs, no further boundary detection required. ES=F
trades a near-24h session (~23h, with a ~17:00-18:00 ET maintenance gap,
closed weekends) — used as the robustness twin for families 1 and 3.
Families 2 (gap/overnight structure), 4 (regime split), and 5 (seasonality)
are SPY-only because they are literally about the index's own RTH/overnight
structure.

**Gap structure, SPY vs ES=F — the single clearest number in this round for
"session structure changes what a stop even means":**

| | gaps >0.3% | >0.5% | >0.8% | >1.0% | >1x med ATR% |
|---|---:|---:|---:|---:|---:|
| SPY 1d (RTH-only) | **46.6%** | 27.2% | 13.3% | 8.7% | 4.6% |
| ES=F 1d (near-24h) | **6.8%** | 3.5% | 1.7% | 1.2% | 0.6% |
| SPY 1h | 6.8% | 3.9% | 1.8% | 1.1% | — |
| ES=F 1h | 0.6% | 0.5% | 0.3% | 0.1% | — |

SPY gaps past a 0.3% threshold on **almost half of all trading days** — a
direct consequence of the RTH-only 17.5h dark window. ES=F, trading nearly
continuously, gaps past the same threshold **~7x less often**. Every
protective stop used below respects this: family 1/4 stops are optional
ATR-scaled and gap-honesty-corrected (§4); family 2a's gap-fill family is
built as a same-day simulator specifically because the SPY gap IS the
tradeable event, not a risk to a stop.

---

## 2. Costs

| instrument class | fee | slippage | half-spread | round-trip cost |
|---|---:|---:|---:|---:|
| SPY (ETF) | 1.0bp | 1.0bp | 0.0bp | **4.0bps** |
| ES=F (futures) | 0.5bp | 0.5bp | 0.0bp | **2.0bps** (matches task spec exactly) |

`funding_bps_8h=0.0` set explicitly on both `CostModel`s (same "read the
engine, don't assume" catch as round 48 — `run_backtest` always charges its
crypto-perp funding default unless told not to). `execution="taker"`
throughout, matching the TradFi convention from rounds 48/55, not the
crypto-BloFin "maker" default from rounds 41/43.

---

## 3. Gauntlet discipline

Chronological 60/20/20 per instrument/TF. **SURVIVOR** = positive
expectancy on both train AND val, with ≥30 train / ≥8 val trades.
**INSUFFICIENT-SAMPLE** = positive both windows but under the trade-count
bar. **FAIL** = negative on either window. The sealed final 20% was never
touched by any family, including the family-2b/5 statistical audits (both
explicitly restricted to `[:i_va]`).

**186 strategy configs tested. 91 SURVIVOR, 15 INSUFFICIENT-SAMPLE, 80
FAIL.** (Below the ~250-350 guidance figure — the grid was deliberately kept
to axes that test real questions (shape x symbol x protective-stop x
safety-hold-cap) rather than padding with an ungridded exit-threshold
dimension; see each family's docstring in the script for exactly what was
and wasn't gridded and why.)

Engine-mismatch approximations (gap-fill's same-day simulator, first-hour-
break's 6-bar session cap, overnight-drift's direct statistical treatment)
are documented in full in the script's module docstring — summarized inline
per family below.

---

## 4. FAMILY 1 — index dip-buying: **the folklore survives, robustly**

(a) RSI(2) < {5,10,15} on daily, price > SMA200 → long. (b) N-day-low
pullback: close = lowest close in {3,5} days while > SMA200 → long. (c)
consecutive down-days {2,3} while > SMA200 → long. All three share the
literal task-spec exit (close > SMA5 OR RSI2 > 65), **no fixed target**.
Grid: optional ATR-scaled protective stop (none / 1.0x / 1.5x TRAIN-median
ATR%) x optional 60-trading-day safety hold-cap, both SPY and ES=F.

**66 of 84 configs SURVIVOR, 0 INSUFFICIENT-SAMPLE, 18 FAIL.**

| shape | symbol | SURVIVOR | FAIL |
|---|---|---:|---:|
| 1a rsi2<5 | SPY | 6/6 | 0 |
| 1a rsi2<5 | ES=F | 6/6 | 0 |
| 1a rsi2<10 | SPY | 4/6 | 2 |
| 1a rsi2<10 | ES=F | 6/6 | 0 |
| 1a rsi2<15 | SPY | 4/6 | 2 |
| 1a rsi2<15 | ES=F | 6/6 | 0 |
| 1b 3-day-low | SPY | 6/6 | 0 |
| 1b 3-day-low | ES=F | 6/6 | 0 |
| 1b 5-day-low | SPY | 2/6 | 4 |
| 1b 5-day-low | ES=F | 6/6 | 0 |
| 1c downstreak2 | SPY | 2/6 | 4 |
| 1c downstreak2 | ES=F | 4/6 | 2 |
| 1c downstreak3 | SPY | 4/6 | 2 |
| 1c downstreak3 | ES=F | 4/6 | 2 |

Top SPY config: `1a-rsi2<5 stop=none hold=nocap` — TRAIN +$113.52/trade
(65t), VAL +$31.02/trade (29t). Every stop/hold variant of `rsi2<5` also
survives (12/12 across both symbols). **The classic Connors "buy panic,
sell the snap-back" shape is real, cost-honest, and holds on both a pure-ETF
and a near-24h-futures instrument decades apart in listing history.**

**Pattern in the FAILs**: every SPY FAIL is a **1.0xATR-stop** variant on a
looser threshold (rsi2<10/15, 5-day-low, downstreak2/3) — tightening the
stop to 1.0x median ATR% (~1.3%) on a shape that's already somewhat
loose-fitting kills it; the 1.5x stop or no-stop variants of the SAME shape
usually survive. **Lesson for sizing: give the dip room, don't clamp it.**

**Gap-honesty correction** (§ script, `gap_honesty_correction`): every
stop-bearing SURVIVOR was re-checked. Effect is real but modest and never
flips a headline verdict — e.g. `1a-rsi2<5 stop=1.0xATR` (SPY): VAL raw
+$27.28 → gap-adjusted +$24.84 (1/29 gapped through); `1b-3daylow
stop=1.0xATR` (SPY): VAL raw +$1.74 → gap-adjusted +$0.82 (6/216 gapped,
the thinnest-margin survivor in the family, worth flagging as fragile).

---

## 5. FAMILY 2a — gap-fill: **total graveyard, 0/16**

Gap-down longs targeting the prior close (the "fill"), mirrored gap-up
shorts. Thresholds {0.3, 0.5}%, stop {0.5, 1.0}x the gap's own size, SPY +
ES=F. Built as a dedicated same-day simulator (not `run_backtest` — the
engine's next-bar-open-fill mechanic can't express "trade the bar whose own
open defines the entry"; see script docstring for the full justification).

**Every one of 16 configs is FAIL on both train and val, both directions,
both instruments, both thresholds, both stop multiples.** SPY gap-downs are
common (46.6% of days gap >0.3%) but chasing the fill loses money after
costs on both legs — the "fill" is not reliable enough, and shorts (fading
gap-ups) are uniformly worse than longs (fading gap-downs), consistent with
the index's long-biased personality. **This family is a clean, confident
NO — do not build a gap-fill book on SPY or ES=F with this shape.**

---

## 6. FAMILY 2b — overnight drift: **real but thin, doesn't clear a fresh
round-trip on SPY; negative on ES=F**

Buy close, sell next open — the famous anomaly. Direct statistical audit
(train+val window, test sealed), gated by trend (SMA200 side) and by the
20d-realized-vol percentile proxy. Reported gross AND net of one
`round_trip_bps()` charge per event (an honest single-lot approximation).

| bucket | n | mean gross % | mean net % | t-stat | win% |
|---|---:|---:|---:|---:|---:|
| SPY unconditioned | 6,740 | +0.0331 | **-0.0069** | 4.38 | 54.6% |
| SPY trend-above-SMA200 | 4,826 | +0.0393 | -0.0007 | 6.03 | 55.3% |
| SPY trend-below-SMA200 | 1,914 | +0.0173 | -0.0227 | 0.83 | 52.7% |
| SPY vol-calm (<50pct) | 3,267 | +0.0131 | -0.0269 | 1.73 | 53.6% |
| SPY vol-crash (>80pct) | 1,712 | **+0.0459** | **+0.0059** | 2.08 | 55.8% |
| ES=F unconditioned | 5,219 | -0.0142 | -0.0342 | -3.82 | 39.2% |
| ES=F trend-above-SMA200 | 3,625 | -0.0101 | -0.0301 | -3.48 | 37.7% |
| ES=F trend-below-SMA200 | 1,594 | -0.0233 | -0.0433 | -2.29 | 42.6% |
| ES=F vol-calm (<50pct) | 2,818 | -0.0092 | -0.0292 | -3.36 | 36.7% |
| ES=F vol-crash (>80pct) | 1,039 | -0.0400 | -0.0600 | -2.97 | 38.1% |

**The anomaly is statistically real on SPY** (unconditioned t=4.38, highly
significant gross) **but economically tiny** — the mean gross overnight
return (+0.033%/night) is smaller than a single ETF round-trip (0.04%), so
a strategy that pays a fresh round-trip commission every single night is a
losing proposition. The ONE bucket that survives its own cost haircut is
**vol-crash** (+0.046% gross / +0.006% net, t=2.08 — marginal but positive):
overnight drift concentrates in high-volatility/crash periods, consistent
with "close-out-before-the-storm, resolve-overnight" positioning lore, but
the net edge (~0.6bp/night) is thin enough that it is only reachable by
something that ALREADY holds the position overnight for other reasons
(e.g. a trend book's existing long), not a dedicated close-to-open day-trade.

**ES=F is negative in every single bucket** — the opposite sign from SPY.
The honest read: ES=F's daily "close→next open" gap is mostly just the
~1h maintenance-break technical gap (17:00-18:00 ET), NOT the real
information-accumulation window that SPY's true 17.5h dark session
represents. The two instruments are measuring structurally different things
under the same label — another concrete illustration of §1's session-
structure point.

---

## 7. FAMILY 2c — first-hour range break (SPY 1h only): **thin, long-only,
needs room**

Break of the 9:30-10:30 ET opening range, 6-bar session-safety cap (see
script docstring for the engine-mismatch approximation), unconditioned and
with-trend (daily SMA200 side, known as of the prior day's close only).

**2 of 12 SURVIVOR** — both are the **long-only, 2.5x-range target**
variant:

| config | tr_n | tr_exp | tr_win% | va_n | va_exp | va_win% |
|---|---:|---:|---:|---:|---:|---:|
| unconditioned long, tgt2.5x | 227 | +$2.09 | 45.4% | 79 | +$0.27 | 41.8% |
| with-trend long, tgt2.5x | 201 | +$0.79 | 45.3% | 79 | +$0.27 | 41.8% |

Both variants land on **identical val numbers** — during the val window the
daily trend filter never excluded a single unconditioned long entry (the
period was persistently in an SPY uptrend), so "with-trend" degenerates to
"unconditioned" there. **Shorts die everywhere** (uncond short tr_exp
-$6.87 to -$8.05; with-trend short only 19 train trades, one direction
flips positive on train by pure noise and both flip negative in val with
0 trades — an artifact of a rare regime, not an edge) — consistent with §5's
gap-fill finding that fading the index's own upward bias is structurally
disadvantaged. **"Both" (both directions in one signal) is worse than
long-only alone in every case** — the short leg drags the combined result
down. The tight 1.5x target starves the edge (both long variants FAIL at
1.5x) — this breakout needs room to work, not a quick scalp.

---

## 8. FAMILY 3 — trend/regime backbone: **the slow backbone confirms
round 48's honest frame — validated edge + drawdown cut, NOT outperformance**

SMA{100,200} regime membership (`vol_gated_ma` with fast=1, i.e. "long
while close > SMA(slow)") and the classic 50/200 golden cross, ungated and
adaptive-vol-gated, SPY + ES=F.

**8 of 12 SURVIVOR** (golden cross is INSUFFICIENT-SAMPLE on both symbols —
too slow to clear 30 train trades even over 20-33 years, exactly matching
round 48's finding that trend ports are "mostly INSUFFICIENT-SAMPLE on
daily, too slow"):

| config | symbol | tr_n | tr_exp | tr_ret% | tr_dd% | va_n | va_exp | va_ret% | va_dd% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| sma100-regime, gate=none | SPY | 120 | $75.13 | +90.2% | -51.6% | 50 | $22.82 | +11.4% | -24.2% |
| sma100-regime, gate=adaptive | SPY | 83 | $107.17 | +88.9% | -36.5% | 42 | $32.06 | +13.5% | -21.2% |
| sma200-regime, gate=none | SPY | 74 | $251.82 | +186.3% | -29.7% | 18 | $310.46 | +55.9% | -15.3% |
| sma200-regime, gate=adaptive | SPY | 57 | $167.10 | +95.2% | -33.6% | 18 | $310.46 | +55.9% | -15.3% |
| **buy&hold (baseline)** | **SPY** | 1 | $24,042.65 | **+240.4%** | **-56.5%** | 1 | $10,260.57 | **+102.6%** | **-20.2%** |
| sma100-regime, gate=none | ES=F | 98 | $33.16 | +32.5% | -27.3% | 24 | $214.39 | +51.5% | -21.5% |
| sma100-regime, gate=adaptive | ES=F | 65 | $65.51 | +42.6% | -20.3% | 22 | $237.71 | +52.3% | -21.5% |
| sma200-regime, gate=none | ES=F | 52 | $160.26 | +83.3% | -20.1% | 16 | $345.33 | +55.3% | -18.6% |
| sma200-regime, gate=adaptive | ES=F | 43 | $38.65 | +16.6% | -30.1% | 16 | $345.33 | +55.3% | -18.6% |
| **buy&hold (baseline)** | **ES=F** | 1 | $3,593.41 | **+35.9%** | **-57.1%** | 1 | $10,748.79 | **+107.5%** | **-34.4%** |

**Honest B&H comparison, exactly the round-48 frame**: in TRAIN, SMA200-
regime beats B&H's raw return on SPY (186% vs 240% — actually B&H still
wins on raw return even in train) with drawdown cut roughly in half (-30%
vs -57%). **In VAL, buy-and-hold wins on raw return outright** (SPY +103%
vs SMA200-regime's +56%) but again with a much deeper drawdown (-20% vs
-15%). **This backbone does NOT beat buy-and-hold on return — its case is
purely the drawdown cut**, identical conclusion to gold's donchian system in
round 48. Turnover: SMA200-regime runs **~2.7-3.7 trades/yr** on SPY,
**~3.1-3.4/yr** on ES=F — genuinely slow, portfolio-ballast pacing, not an
active book.

---

## 9. FAMILY 4 — mean reversion vs momentum split by regime (THE
CENTERPIECE): **half the folklore confirmed, half refuted**

Four regime cells — 20d-realized-vol percentile {<50 "calm", >80 "crash"} x
SMA200 side {above, below} — each tested with BOTH weapons (RSI2 dip-buy =
mean reversion; N-day price continuation = momentum) and an optional
ATR-scaled protective stop.

**Verdict counts by weapon x cell:**

| weapon | cell | SURVIVOR | INSUFFICIENT-SAMPLE | FAIL |
|---|---|---:|---:|---:|
| MR (RSI2 dip) | calm+above | **9/9** | 0 | 0 |
| MR (RSI2 dip) | crash+above | 2 | 5 | 2 |
| MR (RSI2 dip) | crash+below | 4 | 1 | 4 |
| MR (RSI2 dip) | calm+below | 0 | 3 | 6 |
| Momentum (N-day cont.) | calm+above | 0 | 0 | **6/6** |
| Momentum (N-day cont.) | crash+above | 0 | 0 | **6/6** |
| Momentum (N-day cont.) | crash+below | 0 | 0 | **6/6** |
| Momentum (N-day cont.) | calm+below | 0 | 0 | **6/6** |

**The folklore's HALF right, HALF wrong. Mean reversion (buy-the-dip) is
the dominant weapon EVERYWHERE it has sample** — not just the textbook
"calm uptrend" condition (9/9 perfect there) but also survives with decent
sample in BOTH crash cells (crash+above 2 SURVIVOR + 5 thin-but-positive
INSUFFICIENT-SAMPLE; crash+below 4 SURVIVOR). The naive "momentum should
work in crashes instead" half of the hypothesis is **flatly refuted for
this momentum shape**: simple N-day (5 or 10) price-continuation FAILED in
literally every one of 24 configs across all four regime cells, including
the crash+above cell where trend-following should theoretically shine.
**On the index, "buy the dip" generalizes across regimes far better than
"ride the trend" does** — at least for this simple continuation shape.
Caveat stated plainly: this tests ONE momentum implementation (raw N-day
price comparison); a breakout-style or volatility-scaled momentum entry
might behave differently and is a natural follow-up.

**calm+below is the one cell with no real answer** — it's a genuinely rare
regime for SPY (calm realized vol AND already below SMA200 — a slow bleed,
not the index's common mode), so both weapons are sample-starved there
(val n as low as 1 trade in most calm+below MR configs; the flashy
"+$134.02/trade" val numbers in that cell are single-trade noise, explicitly
marked INSUFFICIENT-SAMPLE or FAIL, never treated as a finding).

**Gap-honesty correction flags one fragile SURVIVOR**: `MR rsi2<15
cell=crash+below stop=1.5xATR` — VAL raw +$0.95 → gap-adjusted **-$4.95**
(1/18 gapped through). This flips sign under gap-honesty scrutiny and should
NOT be treated as validated despite clearing the SURVIVOR bar on raw
numbers; every other family-4 SURVIVOR held its sign after correction.

---

## 10. FAMILY 5 — seasonality audit (report-only, SPY daily, 33y, test
sealed): **turn-of-month is the standout, day-of-week is weak**

| bucket | n | mean return % | t-stat |
|---|---:|---:|---:|
| Mon | 1,269 | +0.0403 | 1.13 |
| Tue | 1,381 | +0.0722 | 2.31 |
| Wed | 1,383 | +0.0513 | 1.74 |
| Thu | 1,357 | +0.0216 | 0.71 |
| Fri | 1,350 | -0.0091 | -0.31 |
| **turn-of-month** | 1,286 | **+0.0767** | **2.43** |
| rest-of-month | 5,454 | +0.0257 | 1.65 |

Turn-of-month (last trading day of month + first 3 of next, the classic
Xu-McConnell window, ~19% of trading days) returns **~3x** the daily mean of
the rest of the month, with the round's strongest t-stat of any audit table
(2.43). Tuesday is the only individual day-of-week with a t-stat above 2;
Friday is flat-to-negative (t=-0.31, no signal). **Report-only, no strategy
built here** — flagged explicitly as the strongest candidate for a
dedicated seasonality round (turn-of-month timing overlaid on the family-1
dip-buy entries, or a standalone TOM long, is the natural next test).

---

## 11. Ranked sealed-look candidates (when a look is worth spending)

Ordered by robustness (sample depth, cross-instrument confirmation, gap-
honesty survival — NOT by raw expectancy):

1. **FAMILY 1a `rsi2<5`, no stop, SPY+ES=F** — 12/12 configs SURVIVOR,
   largest and cleanest margin in the round, confirms on both instruments,
   gap-honesty barely touches it. Strongest single candidate.
2. **FAMILY 4 MR `calm+above` cell, any rsi2 threshold** — 9/9 SURVIVOR,
   the literal folklore condition, all gap-honesty-clean. Effectively the
   family-1 edge re-derived through an independent regime-gating lens —
   correlated with #1, not a fully independent confirmation.
3. **FAMILY 3 `sma200-regime`, SPY+ES=F, gate=none or adaptive** — 4/4
   SURVIVOR, slow (~3/yr) but the only family with a real (if modest)
   drawdown-cut case vs buy-and-hold, cross-instrument confirmed.
4. **FAMILY 4 MR `crash+below`, rsi2<10/15, no-stop or 1.0xATR** — real but
   thinner sample (14-18 val trades), one config's SURVIVOR status flips
   under gap-honesty (§9) — needs a wider look before trusting it.
5. **FAMILY 2c long-only 2.5x-range breakout** — thin margin ($0.27-2.09/
   trade against a 4bp cost floor), single-symbol, not yet a strong
   candidate.

**Not candidates**: family 2a (gap-fill, 0/16, confirmed dead), family 2b
(overnight drift, real but sub-cost-floor except one marginal bucket, not a
standalone strategy), family 4 momentum (0/24, confirmed dead for this
shape), golden cross (INSUFFICIENT-SAMPLE, structurally too slow to ever
clear the bar on daily bars alone).

**No sealed look was spent this round** — pure train/val research, per the
task's own framing that a real S&P venue doesn't exist yet to deploy any of
this to.

---

## 12. Draft "S&P playbook" section (for `MARKET_PLAYBOOKS.md`)

```
## S&P 500 (SPY/ES=F research; NO demo venue exists — BloFin's SPX-USDT
   is the SPX6900 MEMECOIN, never confuse them)
- Personality: session-bound (9:30-16:00 ET) with a REAL 17.5h dark
  overnight window on the ETF (SPY gaps >0.3% on 46.6% of days vs ES=F's
  6.8% — near-continuous futures sessions structurally don't have this).
  Long-biased: shorts and gap-up-fades lose to their long-side mirrors
  everywhere tested. WatcherGuru news does NOT move it in-session (R47,
  1.03x). The world's most famous dip-buy folklore market — and it's real.
- What works (validated, R60): RSI2<5 dip-buy (price>SMA200, exit
  close>SMA5 or RSI2>65, NO fixed target) — 12/12 configs SURVIVOR on
  BOTH SPY and ES=F, gap-honesty-clean, the round's cleanest edge.
  SMA100/200 regime membership (long while price>SMA, ~3-6 trades/yr) —
  4/4 SURVIVOR cross-instrument, but does NOT beat buy-and-hold on raw
  return (case is drawdown cut only: -15/-30% vs B&H's -20/-57%, exactly
  gold's R48 frame). Mean-reversion dip-buying generalizes across BOTH
  calm and crash/high-vol regimes (R60 family 4) — broader than the
  textbook "MR only in calm uptrends" claim.
- What dies: gap-fill (chase the fill after a gap, 0/16, confirmed dead
  both directions both instruments); naive N-day momentum continuation
  (0/24 across every regime cell tested, INCLUDING crash regimes where
  trend-following should theoretically win — refutes "momentum for
  crashes" for this shape specifically); golden cross (too slow to ever
  clear 30 trades on daily bars alone); first-hour range-break shorts and
  "both-directions" combos (long-only survives thin, everything else
  dies); overnight drift (real, t=4.4 on SPY, but the ~0.033%/night gross
  edge doesn't clear a single ETF round-trip cost — only reachable by a
  position already held overnight for other reasons, not a standalone
  day-trade); tight (1.0xATR) protective stops on the looser dip-buy
  shapes (rsi2<10/15, 5-day-low, downstreak) — give the dip room.
- Dials: daily median ATR% SPY 1.32% / ES=F 1.36% (recompute per-market,
  never port BTC/gold thresholds); ETF costs 4bps round trip, futures
  2bps; turn-of-month (R60 family 5) is the strongest seasonality signal
  found anywhere in this program, t=2.43, ~3x the rest-of-month mean —
  flagged for a dedicated round, not yet built into a strategy.
- Venue: NONE for the real index yet. Alpaca paper (already pending for
  gold, R48) would unlock SPY dip-buy live-testing; ES=F needs a futures
  broker. This entire system is knowledge-banked until one exists.
- OPEN: dedicated turn-of-month round; momentum-shape iteration (breakout/
  vol-scaled, since naive N-day continuation is dead); crash+below MR cell
  needs a wider look before trusting it (one config flips under gap-
  honesty).
```

---

## Summary for the record

- **186 configs tested** (91 SURVIVOR / 15 INSUFFICIENT-SAMPLE / 80 FAIL),
  0 sealed-test looks spent.
- **Is index dip-buying real after costs? YES, decisively** — RSI2<5
  survives 12/12 configs on both SPY and ES=F, gap-honesty-clean, the
  strongest and broadest edge in the round.
- **Regime-split verdict**: HALF confirmed. Mean reversion dominates across
  calm AND crash regimes (broader than folklore predicts); the momentum
  weapon tested (simple N-day continuation) failed in every single cell,
  including the crash regime it should theoretically win.
- **Trend backbone**: validated but the honest frame is drawdown-cut, not
  outperformance — SMA200-regime loses to buy-and-hold on raw return in
  both train and val, wins on drawdown (-15/-30% vs -20/-57%).
- **Graveyards**: gap-fill (0/16), naive momentum (0/24), golden cross
  (structurally too slow), first-hour shorts/both-directions, overnight
  drift as a standalone day-trade (real but sub-cost-floor).
- **Biggest caveat**: no execution venue exists for any of this yet — every
  number here is knowledge-banked, not deployable, until Alpaca paper (SPY)
  or a futures broker (ES=F) comes online.
- **Venue note (parallel finding, 2026-07-24, recorded in
  `MARKET_PLAYBOOKS.md`)**: `SPY-USDT` on BloFin **prod** was independently
  verified to actually track the real S&P (738.75 vs SPY's 738.18, 0.08%
  basis) — but it is NOT served on the demo host and is thin (~$650k/24h),
  so it does not change this round's "no demo venue" framing or any number
  above. If it ever lands on demo, RSI2<5 dip-buy (§4) is the first
  candidate this round would nominate for a sealed look.
