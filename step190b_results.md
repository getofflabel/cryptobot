# step190b — gold's donchian breakout SHAPE ported to SOL

Run: `python3 step190b_gold_donchian_sol.py` (0.3s, cached data only).
Data: `data_bybit_SOLUSDT_{1d,4h}_full.parquet`. Execution: taker, always.
Costs: SOL's own real BloFin perp `CostModel()` defaults (18.0bps round trip:
6bps taker fee + 1bp half-spread + 2bp slippage, both fills) — **explicitly
NOT** gold's near-zero ETF/futures cost model (`costs_for()` in
step48_tradfi_trend.py uses 0.5-1bps fee/spread/slippage for GLD/GC=F, which
would badly understate SOL's real hurdle). 60/20/20 chronological split;
sealed test slice never sliced, computed, or read anywhere in this script.

## SOL's own ATR%, measured fresh (not ported from gold)

| timeframe | SOL median train ATR% | SOL 10th-90th pctile | gold's cited range (MARKET_PLAYBOOKS) |
|---|---|---|---|
| 1d | **8.125%** | 5.10 - 10.86% | 0.28 - 0.72% |
| 4h | **3.069%** | 1.77 - 4.46% | 0.28 - 0.72% |

SOL's daily ATR% runs **roughly 11-29x gold's** — confirms in numbers what the
desk already knows qualitatively (SOL moves far faster than any TradFi
instrument gold research has touched). This is why gold's own ATR-based
numbers were never plugged in anywhere below.

## Stage 1 — unchanged replay: donchian20 + EMA20-close exit, SOL 1d, no stop

Gold's exact shape and window (`step48_tradfi_trend.donchian_ema_exit`,
imported unmodified, entry_n=20, ema_n=20), no protective stop (pure
EMA-exit — gold's own mechanism exactly, since gold avoids stops specifically
because ETF/futures overnight gaps blow through them, round 47/48's own
documented lesson).

| | n | expectancy | return | vs buy&hold | max DD |
|---|---|---|---|---|---|
| train | 16 | **+$1,977.24/t** | +316.4% | buy&hold **-2.7%** | -51.5% |
| val | 6 | **+$451.19/t** | +27.1% | buy&hold +14.6% | -26.5% |

Trade cadence: **5.8/yr — remarkably close to gold's own ~5.4/yr**, a genuine
structural match (the donchian-breakout-plus-trend-exit shape naturally
produces a low-frequency signal on both instruments even though SOL is far
more volatile day-to-day). Thickness: **64.8x** SOL's 18bps round-trip cost
(edge = 11.67% of notional per trade) — far above the 5x reject floor.
Worst single realized move -19.85% (SOL's fat tail, unmuted by any stop
here — see Stage 2 for the stop question). Both windows positive and both
beat buy-and-hold (train dramatically — SOL's buy-and-hold LOST money
2021-10 to 2024-08 while this system was up 316%, because donchian only
enters on NEW HIGHS and thus mostly sat out the 2022 crash).

**VERDICT: INSUFFICIENT SAMPLE, stated honestly, NOT a pass.** 16 train / 6
val trades are both below this desk's 30/8 floor. The numbers themselves are
the most gold-like, cleanest-looking result in tonight's whole SOL program —
but a floor is a floor; this is flagged as the standing WATCH-LIST candidate
(re-test as SOL's own history accrues, same as gold's own EMA20/50 1h watch-
list item from R55), not deployed or promoted.

## Stage 2 — SOL-native re-derivation sweep

Swept entry_n in {10,15,20,30,55} x timeframe {1d, 4h} x stop in
{none, 3xATR, 5xATR — ATR is SOL's OWN train-median at that timeframe, not
gold's}. ema_n held fixed at 20 (the shape's trend-filter constant, not
swept — same discipline the gold rounds themselves used). 30 configs,
selection by TRAIN expectancy only, one val read spent on the winner.

TRAIN-selected winner: **1d donchian55 EMA20exit, stop=3xATR (=24.4%,
capped at 30%)** — train 6t **+$5,947.85/t** (+357% return!) but **val 5t
-$191.73/t, -9.6% return, UNDERPERFORMS buy&hold's +14.6%.** VERDICT: FAIL.

**This is the discipline working exactly as intended, stated plainly**: the
single best-looking TRAIN number (d55, nearly 6x gold's own window) was a
train-only mirage — n=6 is far too thin to mean anything, and the one
honest val look immediately punished it. Every wider/thinner variant at 1d
(entry_n 30, 55) shares this same thin-sample trap. The ATR-based stop
variants (3x/5x) produced IDENTICAL results to "no stop" at every entry_n
tested — SOL's trend runs in this window never drew down past even a 3xATR
distance before the EMA exit fired, so the stop dimension is currently
un-informative here (not proof it's harmless, just untested by this
particular history — noted, not overclaimed).

**No config in the native sweep clears both the profit bar AND the 30/8
trade floor.** The gold-shape port's only defensible result is Stage 1's
INSUFFICIENT-SAMPLE unchanged replay — genuinely promising, structurally
matched to gold's own trade cadence, but not yet a survivor by this desk's
own honest floor.

## Bottom line for morgan

The donchian-breakout + EMA-trend-exit SHAPE plausibly generalizes to SOL —
Stage 1's numbers (thickness 64.8x, beats buy-and-hold in both windows,
trade cadence within 10% of gold's own) are the single most encouraging
result in tonight's SOL program alongside step190a's CHoCH+confluence edge.
Neither is a SURVIVOR by this desk's own floor yet: CHoCH+confluence has the
trade count (71t) but hasn't had a sealed look spent; the donchian port has
gold-like thickness but only 22 combined trades against a 38-trade floor.
**Both are WATCH-LIST, not deployable, and both deserve a dedicated re-look
as SOL's own history accrues rather than being buried** — this is
structurally different from the four failed BTC-edge transfers in
step190a, which failed on their own merits (train-negative, anti-signal, or
gate-mechanism breakdown), not on sample size alone.

## Files
- `/Users/wallacechen/cryptobot/step190b_gold_donchian_sol.py`
- `/Users/wallacechen/cryptobot/step190b_results.md` (this file)
- `/Users/wallacechen/cryptobot/step190b_table.csv` (31 rows: 1 unchanged + 30-config sweep, full audit trail)
