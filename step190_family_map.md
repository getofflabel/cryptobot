# SOL FAMILY MAP — sol-trader, steps 190-209

Running log, appended to after every family tested (never hand-edited
after the fact — corrections are done by removing and re-appending, see
step192's history if you check git-blame-style diffs). Status as of this
update: **9 distinct family shapes tested (13 reported cells, ~220
individual backtest configs underneath them)**, all against SOL's own
data, taker execution, SOL's own real BloFin costs throughout, sealed test
never touched anywhere. This is short of the 20-30 target — honest
progress report, not a finished map. See step190a/190b/191/192/193
_results.md for full per-family writeups; the SendMessage to morgan has
the executive summary and the honest list of what's still open.

**Headline finding (own the third-asset-check role):** of the 5 currently-
"validated" BTC edges, only 1 shows real two-window information on SOL
(CHoCH+confluence, 1_CHoCH_confluence>=2 below) and it is UNSEALED — the
other 4 fail, two of them for structurally informative reasons (the vol
gate's selectivity mechanism breaks on SOL's higher ATR; the RSI3 washout
is actively anti-signal, not just neutral, a second independent
confirmation after round 88). The gold donchian shape and the SPX RSI2
dip-buy shape both show promising unchanged-replay numbers but neither
clears the 30/8 trade-count floor yet (SOL's cached history is shorter
than gold's/SPX's decades). Two dead-BTC-family confirmations (always-on
shorts, pin-bar/engulfing) reconfirm dead on SOL too, at BTC's own testing
scale.

- **1_CHoCH_confluence>=2** [1h, unchanged-config replay] `k8 thresh>=2 tgt2x` — SURVIVOR | combined 71t $218.95/t (train 51t $165.11, val 20t $356.22) | chance baseline: 95th pctile | thickness 8.4x of 18bps taker cost | worst realized move -6.03% | source: BTC's own sealed/validated number in MARKET_PLAYBOOKS.md, config unchanged
- **2_4h_hidden_RSI_divergence** [4h, unchanged-config replay] `RSI14 k8 buf0.35% tgt3x hold48h` — FAIL | combined 72t $12.59/t (train 55t $-13.13, val 17t $95.82) | chance baseline: 72th pctile | thickness 0.6x of 18bps taker cost | worst realized move -4.03% | source: BTC's own sealed/validated number in MARKET_PLAYBOOKS.md, config unchanged
- **3_4h_vol_gated_trend** [4h, unchanged-config replay] `fast20/slow100 gate1.5% -8%SL` — FAIL | combined 52t $-31.71/t (train 40t $-72.13, val 12t $103.02) | chance baseline: N/A (see note) | thickness -2.5x of 18bps taker cost | worst realized move -8.03% | source: BTC's own sealed/validated number in MARKET_PLAYBOOKS.md, config unchanged
- **4_1h_RSI3_washout_dipbuy** [1h, unchanged-config replay] `RSI3<10 1d-trend-gate turn-guard hold4h` — FAIL | combined 27t $-51.51/t (train 22t $-84.06, val 5t $91.72) | chance baseline: 1th pctile | thickness -3.1x of 18bps taker cost | worst realized move -1.03% | source: BTC's own sealed/validated number in MARKET_PLAYBOOKS.md, config unchanged
- **5_1h_news_momentum_firstbar** [1h, unchanged-config replay] `stop1.2% tgt2.4% hold24h` — FAIL | combined 268t $-11.82/t (train 201t $-5.99, val 67t $-29.33) | chance baseline: 66th pctile | thickness -0.7x of 18bps taker cost | worst realized move -1.23% | source: BTC's own sealed/validated number in MARKET_PLAYBOOKS.md, config unchanged
- **gold_donchian_port(1_unchanged_replay)** [1d, d20+EMA20exit, unchanged-config replay of gold's exact window] — INSUFFICIENT SAMPLE | combined 22t $1561.04/t (train 16t $1977.24, val 6t $451.19) | 5.8t/yr | thickness 64.8x | buy&hold train -2.7% / val 14.6% | source: gold's original d20+EMA20exit sealed-passed 4x, ~5.4t/yr, ~17x thickness
- **gold_donchian_port(2_SOL_native_derivation)** [1d, donchian55+EMA20exit stop=3xATR, TRAIN-selected from a 5-window x 2tf x 3-stop sweep] — FAIL | train 6t $5947.85/t, val 5t $-191.73/t | 2.9t/yr | thickness 108.9x | gold's original entry_n=20/ATR%=(0.28, 0.72) vs SOL's own (see step190b_results.md for the per-tf median) -> re-derived per this desk's own distribution, not ported
- **spx_rsi2dipbuy_port(1_unchanged_replay)** [1d, rsi2<5 SMA200 stop=none (unchanged SPX config)] — INSUFFICIENT SAMPLE | combined 14t $116.52/t (train 8t $0.75, val 6t $270.88) | chance 71th pctile | thickness 5.9x | worst move -13.78% | buy&hold train -2.7% / val 14.6% | source: SPX's original rsi2<5 stop=none sealed-PASS SPY+$75.36/t ES+$124.07/t, 12/12 SURVIVOR
- **spx_rsi2dipbuy_port(2_native_stop_sweep)** [1d, rsi2<5 SMA200 stop=1.0xATR(8.13%)] — FAIL | combined 14t $32.78/t (train 8t $76.40, val 6t $-25.39) | chance 61th pctile | thickness 1.7x | worst move -8.15% | buy&hold train -2.7% / val 14.6% | source: SPX's original rsi2<5 stop=none sealed-PASS SPY+$75.36/t ES+$124.07/t, 12/12 SURVIVOR
- **spx_rsi2dipbuy_port(2_native_stop_sweep)** [1d, rsi2<5 SMA200 stop=1.5xATR(12.19%)] — FAIL | combined 14t $93.92/t (train 8t $-38.80, val 6t $270.88) | chance 69th pctile | thickness 4.8x | worst move -12.21% | buy&hold train -2.7% / val 14.6% | source: SPX's original rsi2<5 stop=none sealed-PASS SPY+$75.36/t ES+$124.07/t, 12/12 SURVIVOR
- **spx_rsi2dipbuy_port(2_native_stop_sweep)** [1d, rsi2<5 SMA200 stop=2.5xATR(20.31%)] — FAIL | combined 14t $-28.56/t (train 8t $-253.14, val 6t $270.88) | chance 53th pctile | thickness -1.5x | worst move -20.34% | buy&hold train -2.7% / val 14.6% | source: SPX's original rsi2<5 stop=none sealed-PASS SPY+$75.36/t ES+$124.07/t, 12/12 SURVIVOR
- **always_on_shorts_confirmation** [1h+4h, 8 configs x 2tf=16 cells, shape unchanged from step48_tradfi_trend.trend_short_signal] — CONFIRMED DEAD on SOL too (0 true survivors; 2 thin cells cleared train/val/count but REJECTED on the 5x-cost thickness floor) | 2/16 both-windows-positive by raw sign | worst combined $-299.46/t, best combined $164.48/t (best 2 cells cleared count/positivity but only 4.4x and 2.2x cost — both under the 5x floor) | source: BTC's always-on-shorts, 5x confirmed dead
- **candle_patterns_confirmation(pin_bar+engulfing)** [1h+4h, 96 cells, shape unchanged from step57_price_action.py] — CONFIRMED DEAD on SOL too (0/96 true survivors) | 2/96 both-windows-positive by raw sign, 2 thin-rejected (<5x cost) | worst combined $-50.90/t, best combined $40.66/t | source: BTC's pin-bar/engulfing family, 0/112 dead, context made it worse
