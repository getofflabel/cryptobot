# STEP150 — taker + structure-stop re-test of BTC's five documented edges
Morgan's mandate, 2026-07-25 night. Every edge here was sealed under a MIX
of maker-fill and/or swept-percentage-stop assumptions built up over 50+
rounds. This file re-tests each one at execution="taker" (always) with
stops placed at real per-trade chart structure via exits.py (never a swept
percentage), on the SAME train/val slices as the original (60/20/20
chronological, select on train only). **The sealed final 20% is NEVER
loaded by any script in this round** — a PASS here means the edge's
economics survive taker+structure on train+val; it is NOT a new sealed
verdict (that is Morgan's call, a separate look to spend).

Engine: step150_common.py (exits.py TradeCtx/run_trade + CostModel taker +
RISK_PCT=2% fixed-fractional sizing, size=risk$/stop_distance, leverage
capped at 20x — BloFin's own documented ceiling per tactical.py, added
after an uncapped near-zero-stop-distance trade produced an absurd
leveraged blowup in edge 4's first run). Cost convention: taker 6bps fee
both legs (Morgan's own thickness-bar definition, 12bps round trip) AND
the fuller CostModel round-trip (fee+half-spread+slippage x2, ~18bps) both
reported. Chance baseline = mean expectancy of 100 random-entry draws
(same event count, same direction mix, SAME stop/target/cost apparatus) on
the same val window.

## RESULT SUMMARY

| # | Edge | Original sealed | Retest verdict | Recovery (wider stop) |
|---|---|---|---|---|
| 1 | 1h CHoCH + confluence>=2 | +$99.52/t (maker, swept-% stop) | **DIED** | did not recover (n_back=2) |
| 2 | 4h hidden RSI divergence | +$52.03/t (maker, swept-% stop) | **DIED** | did not recover (n_back=2) |
| 3 | 4h trend, 1.5% vol gate | +$401.30/t (maker, flat -8% SL) | DIED at buffer=0 | **RECOVERED** at buffer=1.5% — SURVIVOR, thick |
| 4 | 1h RSI3 dip-buy, 48h room | live (mixed fills, flat 1.5%/4.5%) | **DIED, decisively** | did not recover (n_back=2), got WORSE |
| 5 | News momentum, first-hour dir. | +$10.35/t (blended fee, no spread modeled) | DIED at buffer=0 | technically positive at buffer=1.0% but **thickness 0.03x — REJECT** |

**Bottom line: three of five die outright (1, 2, 4). One (3, the 4h vol-gated
trend/"ride") recovers cleanly with more room on the trailing structural
stop and is the strongest survivor of the night. One (5, news momentum)
recovers on paper but the edge is razor-thin — under the 5x-cost floor,
still a practical death.** Only edge 3 is worth carrying forward as-is.

---

## Edge 1 — 1h CHoCH + confluence>=2
Original (R56): sealed +$99.52/t x16, **execution="maker"**, stop =
train-window MEDIAN % distance to the broken swing (swept, not per-trade).

**Retest (taker + exits.stop_structure(k=8,n_back=1,use=wick) + target_fixed_r(r=2)):**
- TRAIN: n=74, exp=**-$42.92/t**, win 31.1%, ret -31.8%, DD -41.0%
- VAL:   n=34, exp=**+$70.61/t**, win 47.1%, ret +24.0%, DD -9.9%
- Chance baseline (val, 100 draws, 52% long mix): mean exp -$34.88/t (val beats chance)
- Thickness (val): 1.26% of notional, 10.5x the 12bps round-trip, 7.0x the full 18bps — clears 5x on val alone
- **VERDICT: DIED.** Train flips negative under a real per-trade structure
  stop even though val stays strongly positive. The original train-median
  swept-% stop was averaging away exactly the variance a genuine per-trade
  stop must respect — some CHoCH entries have their protective swing much
  farther away than the median implied, and the 2x-R target isn't reached
  before max_hold on those. The monotonic train/val dose-response R56
  found does not survive: it was a property of the swept stop, not the
  setup.
- **Recovery check (n_back=2, one level further out):** TRAIN n=76 exp
  -$6.20/t, VAL n=33 exp +$3.39/t. Train still negative (though much
  closer to zero) — **does not recover.** DEATH CONFIRMED.
- Files: step150a_choch_confluence.py, step150a_table.csv

## Edge 2 — 4h hidden RSI divergence
Original (R58): sealed +$52.03/t x24, ~18/yr, **execution="maker"**, stop
= train-window MEDIAN % distance to the qualifying swing (buffer 0.35%,
capped 4.0%).

**Retest (taker + exits.stop_structure(k=8,buffer_pct=0.35,use=wick) + target_fixed_r(r=3)):**
- TRAIN: n=66, exp=**+$15.20/t**, win 45.5%, ret +10.0%, DD -14.0%
- VAL:   n=25, exp=**-$9.30/t**, win 44.0%, ret -2.3%, DD -10.6%
- Chance baseline (val, 100 draws, 50% long mix): mean exp -$9.90/t (barely beats chance — both near zero)
- Thickness (val): -0.15% of notional, -1.24x the 12bps round-trip — reject on sign alone
- **VERDICT: DIED.** Original train $74.22/t collapses to $15.20/t and val
  flips from $31.99/t to -$9.30/t. The un-capped, per-trade structural
  stop is on average WIDER than the original's 4.0%-capped median (many
  trades now run the full 48h hold without hitting stop or target — median
  hold = the max_hold cap exactly, in BOTH windows), turning what should
  be a directional edge into something close to an uncosted random walk.
- **Recovery check (n_back=2, one level further out):** TRAIN n=66 exp
  -$0.30/t, VAL n=24 exp -$13.57/t. Worse, not better. **Does not recover.**
  DEATH CONFIRMED.
- Files: step150b_hidden_divergence.py, step150b_table.csv

## Edge 3 — 4h trend w/ strict 1.5% vol gate (the "ride")
Original (R54): sealed +$401.30/t x8 on the "drought window," **execution=
"maker"**, stop = flat -8% SL (a swept round number, rarely the actual
exit mechanism — trend-flip usually closes the trade first).

**Retest (taker + exits.stop_structure_trailing(buffer_pct=0, fallback_pct=8) + trend-flip exit):**
- TRAIN: n=44, exp=**-$12.18/t**, win 36.4%, ret -5.4%, DD -20.6%
- VAL:   n=14, exp=**+$328.69/t**, win 50.0%, ret +46.0%, DD -4.3%
- Chance baseline (val, 100 draws, 100% long): mean exp +$30.43/t (edge crushes chance)
- Thickness (val): 6.22% of notional, 51.8x the 12bps round-trip, 34.5x the full 18bps — very thick
- VERDICT at buffer=0: FAIL (train negative). Note this uses the STANDARD
  chronological 60/20/20 split, not R54's special "drought window" sealed
  slice — not a literal replay of that exact test, stated plainly.
- **RECOVERY CHECK (buffer_pct=1.5%, more room on the ratcheting floor):**
  TRAIN n=44 exp **+$17.15/t** (ret +7.5%, DD -7.0%), VAL n=14 exp
  **+$99.37/t** (ret +13.9%, DD -4.5%). **BOTH POSITIVE — SURVIVOR.**
  Chance baseline (val): mean exp +$7.24/t — edge beats chance by ~13.7x.
  Thickness (val): 3.16% of notional, **26.4x the 12bps round-trip, 17.6x
  the full 18bps round-trip** — comfortably clears the 5x floor.
- **VERDICT: RECOVERS.** A tight (0%-buffer) trailing floor was whipsawing
  train out of winning trades on routine pullbacks that the trend later
  resumed from; giving the floor 1.5% of breathing room (still a REAL
  structural stop, still ratcheting only in the trade's favor, never a
  flat percentage substituting for structure) turns this back into the
  desk's thickest surviving edge tonight, on both windows, well above
  chance and well above the cost floor.
- Files: step150c_vol_gated_trend.py, step150c_table.csv, recovery in step150f_recovery_checks.py

## Edge 4 — 1h RSI3 dip-buy in uptrends (needs 48h room)
Original (live tactical.py "panic-dip" / R43): STOP_PCT=1.5%,
TARGET_PCT=4.5% (3:1), MAX_HOLD_H=48, live fills blend 2bp (TP) / 6bp (SL).

**Retest (taker + exits.stop_structure(k=5,n_back=1,use=wick) + target_fixed_r(r=3), leverage capped at 20x):**
- TRAIN: n=167, exp=**-$70.09/t**, win 40.7%, ret -117.1%, DD -111.6%
- VAL:   n=139, exp=**-$69.54/t**, win 41.0%, ret -96.7%, DD -97.8%
- Chance baseline (val, 100 draws, 100% long): mean exp -$28.22/t — the
  real edge is WORSE than a random-entry control in the same window
- Thickness (val): -0.29% of notional, -2.45x the 12bps round-trip — reject
- **VERDICT: DIED, decisively, and does not beat chance.** This is the
  cleanest kill of the night. The live book's flat 1.5%/4.5% bracket
  (with flat 20x sizing) was flattering a setup whose REAL nearest 1h
  swing structure sits close enough that a k=5 stop clips it constantly
  (win rate 41% vs. the ~57% the live-fill-convention numbers implied);
  once sized honestly (risk$/real-stop-distance instead of a fixed
  leverage number) the edge is a net loser even before judging it against
  chance.
- **Recovery check (n_back=2, one level further out):** TRAIN n=366 exp
  -$24.78/t, VAL n=115 exp -$68.88/t. **Worse, not better — does not
  recover.** DEATH CONFIRMED, and flagged as the strongest candidate for
  RETIREMENT from tactical.py's live trigger set (see note to Morgan).
- Files: step150d_rsi3_dipbuy.py, step150d_table.csv

## Edge 5 — News momentum, first-hour direction (N2 structure-trailing)
Original (R45B sealed +$20.81/t fixed bracket; R65 N2 structure-trailing —
the LIVE version — sealed +$10.35/t x104): entry-bar's-own-extreme initial
floor + k=5 confirmed-swing ratchet, blended maker-entry (2bp)/taker-exit
(6bp) fee convention, **no spread/slippage modeled at all**.

**Retest (taker throughout, standardized onto exits.stop_structure_trailing(buffer_pct=0, fallback_pct=8), trail-only target):**
- TRAIN: n=284, exp=**-$8.88/t**, win 32.7%, ret -25.2%, DD -66.0%
- VAL:   n=96, exp=**-$15.25/t**, win 27.1%, ret -14.6%, DD -41.0%
- Chance baseline (val, 100 draws, 52% long mix): mean exp -$37.56/t (edge beats chance, both negative)
- Thickness (val): -0.08% of notional, -0.70x the 12bps round-trip — reject
- **VERDICT: DIED.** Note an honest confound: this substitutes exits.py's
  GENERIC trailing floor (initialized at the most recent confirmed swing)
  for N2's bespoke "entry bar's own opposite extreme" floor — a deliberate
  standardization onto the shared toolkit, but it is NOT a pure taker-cost
  isolation the way edges 1-4 are. Win rate drops hard (27-33% vs N2's
  live win profile) — the generic floor is initializing tighter/more
  erratically than the bar-calibrated original on event-driven entries
  that can land anywhere on the chart, not just at structure.
- **Recovery check (buffer_pct=1.0%, more room):** TRAIN n=228 exp
  +$5.82/t, VAL n=78 exp **+$0.32/t**. Technically both positive —
  **but thickness (val): 0.0036% of notional, 0.03x the 12bps round-trip,
  0.02x the full round-trip — three orders of magnitude under the 5x
  floor.** This is noise, not an edge. **REJECT per the thickness rule
  ("under 5x is a reject no matter the dollar figure") — practical death
  confirmed even though the sign flipped positive.**
- Files: step150e_news_momentum.py, step150e_table.csv, recovery in step150f_recovery_checks.py

---

## WHAT KILLED WHAT — pattern across all five
Every edge that died did so primarily because a genuine PER-TRADE
structure stop has real variance a train-window MEDIAN (or a flat
percentage) silently erases: sometimes the nearest confirmed swing sits
much closer than the average implied (edges 4, 5 — tight, choppy stop-outs,
win rate collapses), sometimes much farther (edges 1, 2 — the R-multiple
target stops being reachable inside the hold window, trades drift to
time_cap). Taker execution (vs. maker) is a real but SECONDARY cost on top
of that — none of the five failed purely on the fee/spread delta the way
the Bollinger breakout did earlier tonight; the stop-mechanism change is
the dominant driver everywhere. Edge 3 is the one case where the
structural stop just needed more room (a wider buffer, still real
structure, never a swept percentage) to stop clipping normal pullbacks —
that fix worked because the underlying trend-following edge was real and
the tight floor was the only problem. Edges 1/2/4/5 did not respond the
same way to more room, which is the honest signal their problem is deeper
than stop placement.

## RECOMMENDATION FOR THE LIVE BOOK (Morgan's call, not mine to execute)
- Edge 4 (RSI3 dip-buy, tactical.py's panic-dip trigger) is the strongest
  candidate for retirement/rebuild — it is now a confirmed net loser under
  honest sizing and beats neither zero nor chance, on both windows, twice.
- Edge 3 (the "ride") should have its live stop widened from the flat -8%
  SL to a real structural trailing floor with ~1.5% buffer — this
  retest suggests it would be net POSITIVE for it, not just safer.
- Edges 1, 2, 5 need real rework (not a stop-parameter tweak) before
  they can be trusted at taker costs — see individual sections above for
  the specific mechanism that broke in each case.
