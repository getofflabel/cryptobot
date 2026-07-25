# step191 — SPX's RSI2<5 dip-buy shape ported to SOL

Run: `python3 step191_spx_dipbuy_sol.py` (1.1s, cached data). Shape:
RSI(2)<5 & close>SMA200 daily, exit close>SMA5 or RSI2>65, no fixed target
— `step60_spx_system.py`'s exact sealed-passed winner
(`1a-rsi2<5 stop=none hold=nocap`: SPY +$75.36/t x33 +24.9% DD-8.8%, ES=F
+$124.07/t x29 +36.0% DD-4.6%, 12/12 config-variant SURVIVOR). Execution:
taker, always. Costs: SOL's own real BloFin perp costs (18bps round trip),
NOT SPX's near-zero ETF/futures rate. 60/20/20, sealed test never touched.

SOL's own daily median train ATR% (8.125%) vs SPX's cited 1.3-1.4% is
measured fresh, not reused (see step190b for the same measurement).

## Stage 1 — unchanged replay (stop=none, exact SPX config)

RSI2<5 & close>SMA200 fires on only **14 events** across train+val (8
train, 6 val) — SOL's 4.75-year cached daily history is much shorter than
SPX's 6.7-year window, and this is a naturally low-frequency signal.
Train exp $0.75/t (essentially flat), val exp $270.88/t (+16.3% return,
beats buy&hold's +14.6%), combined chance percentile 71 (unremarkable).
Thickness 5.9x — technically clears the 5x floor, but **VERDICT:
INSUFFICIENT SAMPLE**, stated honestly — 8 train / 6 val trades are both
below this desk's 30/8 floor, and train's near-zero expectancy means the
positive combined number is really "one good val stretch," not a proven
edge.

## Stage 2 — SOL-native re-derivation (ATR-scaled protective stop)

Gold/SPX's no-stop convention carries real tail risk on SOL specifically
(SOL fell ~97% peak-to-trough in 2022; a naive RSI2<5-and->SMA200 entry
during a choppy decline could get caught before SMA200 flips down). Tested
stop = {1.0x, 1.5x, 2.5x} SOL's own train-median ATR% (8.13%, 12.19%,
20.31% respectively — explicitly NOT gold's or SPX's ATR numbers).

| stop | train n/exp | val n/exp | combined | chance pctile | thickness | verdict |
|---|---|---|---|---|---|---|
| 1.0xATR (8.13%) | 8t / $76.40 | 6t / -$25.39 | $32.78/t | 61st | 1.7x | FAIL |
| 1.5xATR (12.19%) | 8t / -$38.80 | 6t / $270.88 | $93.92/t | 69th | 4.8x | FAIL |
| 2.5xATR (20.31%) | 8t / -$253.14 | 6t / $270.88 | -$28.56/t | 53rd | -1.5x | FAIL |

No stop variant clears train+val both positive with the trade-count floor.
All three chance percentiles sit near 50-70 — no strong information
content either direction, consistent with a genuinely thin, inconclusive
sample rather than a clean pass or a clean anti-signal (contrast with
step190a's RSI3 washout edge, which was actively anti-signal at the 1st
percentile — this is a different, more honest "we don't know yet" result).

## Bottom line

**14 events over 4.75 years is not enough sample to judge this shape on
SOL either way.** The unchanged replay's raw numbers are not bad (beats
buy-and-hold in val, clears 5x thickness on a technicality) but train is
flat and the count is far under floor. Re-test as SOL's own daily history
grows — WATCH LIST, not dead, not validated.

## Files
- `/Users/wallacechen/cryptobot/step191_spx_dipbuy_sol.py`
- `/Users/wallacechen/cryptobot/step191_results.md` (this file)
- `/Users/wallacechen/cryptobot/step191_table.csv`
