# step193 — pin bar / engulfing candle patterns, dead-family confirmation on SOL

Run: `python3 step193_candle_patterns_confirmation_sol.py` (3.7s, cached
data). Shapes imported unchanged from `step57_price_action.py`
(`pin_bar_signals`, `engulfing_signals`, `daily_sma_aligned`). Grid: pin
bar wick_mult {2,3} x context {roll20, roll55, sma50, none} x stop {1.0,
1.5}xATR x target {2.0,3.0}x-stop = 64 cells; engulfing context {roll20,
roll55, sma50, none} x same stop/target grid = 32 cells. 1h + 4h SOL, 96
cells total — the same order of magnitude as BTC's own 112-cell test.
Execution: taker, always. 60/20/20, sealed test never touched.

## Result: CONFIRMED DEAD on SOL too

**0 of 96 cells** clear the full bar. Only 2 of 96 are even both-windows-
positive by raw sign, and both of those (best: engulfing ctx=roll55
stop1.0xATR tgt2xstop, 4h, combined $40.66/t) top out at 2.3x round-trip
cost — well under the 5x floor. Best pin-bar cell nets essentially zero
after costs ($5.55/t combined, 0.3x thickness). Worst combined cell:
-$50.90/t. Full table in `step193_table.csv`.

**Reconfirms BTC's own finding on a second, structurally different asset**:
these classic candle-reversal patterns carry no exploitable edge once real
costs are applied, on SOL any more than on BTC. This is the kind of cheap,
high-value negative this desk exists to produce — a family two different
assets both reject at meaningful scale (96+112 cells) is a much stronger
"stay dead" signal than either asset alone.

## Files
- `/Users/wallacechen/cryptobot/step193_candle_patterns_confirmation_sol.py`
- `/Users/wallacechen/cryptobot/step193_results.md` (this file)
- `/Users/wallacechen/cryptobot/step193_table.csv`
