# ROUND 88 — IS THE VETO WE SHIPPED TONIGHT REAL, OR TWO LUCKY CELLS?

Research only. Code: `step88_veto_robustness.py`. Full data:
`step88_table.csv` (127 rows: 3 third-asset cells + 115 scored family-sweep
cells [+5 too-thin-to-score] + 4 time-split cells).

**Target of this round**: `daily_pick.py`'s live washout veto (line
~371-393) — RSI3(1h)<10 dip-buy, gated by a turn-candle guard, skipped
whenever `chart_reader.read_chart()` reads `quality == "messy"`. Shipped on
the strength of exactly 2 cells in round 83 (BTC 98th percentile, ETH 98th
percentile against a 200-draw random-skip control) out of that round's 36
total cells.

## METHOD

Every piece of R83's own machinery is imported from `step83_eye_filter.py`,
not retyped: `frame_for` / `funding_hist_for` / `eye_for` / `ts_idx_for`
(the eye cache + causal timestamp index built on `step82_eye.
label_eye_states`, full history, no lookahead), `daily_trend_on_tf` (the 1d
trend gate), `run_split` / `trades_from_backtest` (the exact
`backtest.run_backtest` wiring, full costs, real funding, maker execution),
`dumb_control` / `summarize` (the exact 200-draw random-skip control math,
`N_CONTROL_DRAWS=200`), and every one of B's live constants
(`WASHOUT_RSI_N`, `WASHOUT_RSI_TH`, `STOP_ATR_MULT`, `STOP_CAP_PCT`,
`STOP_FLOOR_PCT`, `TARGET_STOP_MULT`, `WASHOUT_MAX_HOLD_H`). The only new
code is `build_washout()` — `step83_eye_filter.build_B()` generalized to
take RSI period / threshold / turn-guard as parameters instead of
hardcoding them. **Verified in `main()` before anything else runs**:
`build_washout("BTC"/"ETH", WASHOUT_RSI_N, WASHOUT_RSI_TH, True)`
reproduces `build_B()`'s trade list bit-for-bit (same n=47/47, same PnLs,
same entry timestamps) on both assets — the generalization did not drift
from the live spec.

Same chronological 60/20/20 split (`step43_daytrade.split_points`), sealed
test slice never touched — every trade list here is train+val only, same
as R83. Control-percentile definition is identical to R83's "control
pctile": the fraction of 200 random same-size-skip draws whose removed PnL
is *less* negative (worse at finding losers) than the eye's actual removed
PnL. >=90th = clearly better than chance at finding losers, <=10th =
actively worse than chance (anti-signal), in between = no information
content — same bands R83 used.

**Data note**: SOL had 1h/4h/funding already cached; its 1d frame (needed
for the daily-trend gate) and XRP/DOGE's full 1h/1d/funding histories were
fetched fresh from Bybit for this round (now cached on disk for any future
round).

---

## ATTACK 1 — THIRD+ ASSET REPLAY (the cleanest test)

Exact live spec (RSI3<10, 1h, turn-candle guard) replayed on every asset
with adequate cached history beyond BTC/ETH: SOL, XRP, DOGE.

| Asset | Before (n) | After veto_messy (n kept) | Skip PnL | Control pctile |
|---|---|---|---|---|
| SOL | -$47.13/t (27) | -$35.35/t (9) | -$954 | **68.0%** — no information content |
| XRP | $6.39/t (30) | $29.25/t (19) | -$364 | **92.0%** — clears the bar |
| DOGE | -$25.18/t (21) | **-$38.33/t** (7) | -$261 | **36.0%** — no information content, and the "after" set got *worse* |

**2 of 3 new assets fail.** SOL sits in the dead zone (68th percentile, and
remains a loser either way, -$47->-$35). DOGE is the clearest failure in
this whole round: the veto's control percentile (36th) shows no
information content, and unlike every other passing cell in this study,
the retained set is *worse* than what was thrown out — the eye's "messy"
read on DOGE skips a net-*less-bad* subset than removing trades at random
would, the opposite of what a real edge should do. Only XRP clears the
90th-percentile bar, and even that pass is a modest, un-dramatic
improvement ($6.39 -> $29.25) next to BTC's and ETH's original 3-6x
swings ($-6.42->$24.87, $9.78->$54.26). **This is the round's single most
damaging result**: the one asset variable R83's evidential case rested on
("two different assets agree") does not hold up when a third, fourth, and
fifth are added.

---

## ATTACK 2 — FAMILY SWEEP (RSI period x threshold x turn-guard)

RSI period {2,3,5} x threshold {5,10,15,20} x guard {on,off}, 1h, on all 5
assets (BTC/ETH/SOL/XRP/DOGE) = 120 cells, 115 scored (5 too-thin to score,
<8 trades).

**Chance baseline for this attack alone**: 115 scored cells -> expect
**11.5** to clear the 90th percentile and **2.3** to clear the 98th by pure
chance if the veto carried zero information. Observed: **24** cleared the
90th (~2x chance), **12** cleared the 98th (~5x chance) — but also **45**
landed at or below the 10th percentile (**~4x** the 11.5 expected by
chance) — i.e. the family sweep as a whole shows *more* structure than
random in *both* directions, not a clean one-sided edge.

### The split that actually explains the family: the turn-candle guard, not the RSI config

| Guard | n scored | Clear >=90th (chance: 10%) | Clear >=98th (chance: 2%) | Actively harmful <=10th (chance: 10%) |
|---|---|---|---|---|
| **ON** (live setting) | 55 | 23 (**42%**) | 12 (22%) | 3 (5%) |
| **OFF** | 60 | 1 (2%) | 0 (0%) | **42 (70%)** |

Turning the guard off doesn't just weaken the effect — it **inverts** it.
With the guard off, `veto_messy` is actively harmful on 70% of cells
(versus 10% expected by chance): removing "messy" trades from an
unguarded oversold-bounce population disproportionately strips out
*winners*, not losers. With the guard on (the live setting), the picture
flips to a genuine broad plateau — **not** a single spike at exactly
RSI3<10 (see full table below: BTC clears >=90th at 10 of its 11 scorable
guard-on configs, not just the one shipped). **This answers the family-
sweep's own question cleanly: the effect is not a knife-edge parameter
fluke.** It is, however, entirely contingent on one binary design choice
(the guard) rather than being a standalone property of "messy" itself —
which matters for how much credit "messy" alone deserves versus the
turn-candle logic already doing most of the work.

### But the guard-on plateau does not travel to the new assets nearly as well

| Guard=ON subset | n scored | Clear >=90th | Actively harmful <=10th |
|---|---|---|---|
| BTC + ETH (the 2 original assets) | 22 | **11/22 (50%)** | 0/22 |
| SOL + XRP + DOGE (the 3 new assets) | 33 | 12/33 (36%, still above the 10% chance rate) | 3/33 |

Aggregated across the whole neighborhood, the new assets do show
*some* above-chance signal (36% vs. 10% expected) — there may be a real
kernel here. But that aggregate is carried by *different* RSI
period/threshold combinations succeeding on each asset, not by the
specific live rule. **At the exact live spec (RSI3<10, guard on)**, the
per-asset picture is:

| Asset | RSI3<10, guard ON | Verdict |
|---|---|---|
| BTC | 96.5th | pass (original) |
| ETH | 99.5th | pass (original) |
| SOL | 65.5th | **fails — no signal** |
| XRP | 92.0th | pass |
| DOGE | 39.5th | **fails — no signal** |

Same conclusion as Attack 1, from an independent angle: the *specific*
rule wired into `daily_pick.py` — not "some washout+eye combination
somewhere in the neighborhood" — reproduces on 3 of 5 assets, 2 of them
being the exact 2 it was fitted on.

*(Full 120-row sweep, every RSI/threshold/guard combination on all 5
assets, is in `step88_table.csv`.)*

---

## ATTACK 3 — TIME-SPLIT (does one era carry the whole BTC/ETH result?)

The exact R83 BTC and ETH washout trade lists (RSI3<10, guard on, n=47
each), split chronologically at the midpoint.

| Asset | Half | Date range | Before | After veto_messy | Control pctile |
|---|---|---|---|---|---|
| BTC | first | 2020-05-21 to 2022-05-30 | -$7.69/t (23) | $16.14/t | **90.0%** — pass |
| BTC | second | 2022-10-25 to 2025-03-05 | -$5.21/t (24) | $41.08/t | **96.5%** — pass |
| ETH | first | 2021-06-12 to 2023-05-06 | $30.21/t (23) | $68.02/t | 87.0% — just under the bar, still solidly positive |
| ETH | second | 2023-05-22 to 2025-04-21 | -$9.80/t (24) | $42.21/t | **95.0%** — pass |

**Passes, with one asterisk.** BTC clears the 90th-percentile bar
comfortably in both halves; ETH's second half clears easily; ETH's first
half lands just under the strict 90th-percentile cutoff (87th) but is
nowhere near the no-signal/harmful zone and still shows a large before-
>after improvement. **The BTC/ETH effect is not carried by a single era**
— it shows up whether you look at 2020-2022 or 2022-2025. This addresses
the "was it luck from one regime" concern directly, but only for the 2
assets already in question — it says nothing about whether the effect
generalizes, which is exactly where Attacks 1 and 2 found the trouble.

---

## MULTIPLE-COMPARISONS BASELINE, STATED PLAINLY

Total cells with a defined control percentile across all three attacks:
**3 (attack 1) + 115 (attack 2) + 4 (attack 3) = 122.** Under the null
(the veto carries zero information), pure chance predicts:

- **~12.2 cells** clear the 90th percentile
- **~2.4 cells** clear the 98th percentile

Observed: **28 cells** clear the 90th percentile (~2.3x chance) and
**~12 cells** clear the 98th (~5x chance) — genuinely more than noise,
confirming R82/R83's structural claim that the eye's chart read does carry
real information overall. But **45 cells (versus ~12 expected)** land at
or below the 10th percentile — an equally strong *anti-signal* rate,
concentrated almost entirely in the guard-off half of the family sweep.
The honest reading: **the eye's "messy" read is informative, but its sign
and magnitude depend heavily on what it's layered onto** (the turn-guard
being the clearest driver found here) — it is not a context-free "messy =
skip it" rule, and the specific RSI3<10+guard rule now live is validated
on 2 assets, contradicted or silent on 2 of the next 3 tested, and shows
no sign the shipped parameterization itself (as opposed to the general
family) is the right pick outside BTC and ETH.

---

## VERDICT: RIP IT OUT

**2 of the 3 attacks fail** by the round's own decision rule (third asset:
FAIL, 2/3 new assets show no signal or a reversal; family neighborhood:
real-but-confined-to-BTC/ETH, which is not independent confirmation of
anything Attack 1 didn't already show; time-split: PASS, but only tells us
BTC/ETH's own effect isn't a one-era fluke, which was never really the
open question).

The entire evidential weight behind shipping this veto was R83's own
sentence: *"the one thing that argues it is real is that both hits are the
SAME strategy on two DIFFERENT assets, which is not independent noise."*
That argument does not survive contact with a third, fourth, and fifth
asset. SOL and DOGE — run through the identical live spec, identical
control methodology — show no information content, and DOGE's retained
set is actively *worse* than what the veto threw away. Only XRP passes,
and its pass is far more modest than the dramatic BTC/ETH swings that
justified shipping in the first place. BTC and ETH are also not
independent draws in the way R83's framing implicitly assumed — they are
two of the most correlated instruments in crypto, and both lived through
the same 2022 chop/bear regime that plausibly generated a shared,
non-generalizable pattern in "messy" reads rather than two truly
independent confirmations.

**Recommendation: remove the eye veto from `daily_pick.py`'s washout
trigger** (the block at line ~371-393, `"THE EYE'S ONE SANCTIONED VETO
(round 83)"`) and let washout trade on its RSI3<10 + trend + turn-candle
rule alone, unchanged from before R83. This is a good outcome, not a bad
one: `daily_pick` already trades assets beyond BTC/ETH (SOL appears
directly in R83's own 9-trade live anecdote), so the live code was
applying an eye gate with real evidence on 2 of however-many assets it
actually trades, and no evidence — or negative evidence — on the rest.
Ripping it out removes a rule that was one bad SOL/DOGE-style stretch away
from quietly costing money on exactly the assets it was never tested on
before going live.

**Not a dead end — a sharper follow-up lead.** The guard-on family sweep
shows real, above-chance signal on SOL/XRP/DOGE too (36% of guard-on cells
clear the 90th percentile vs. 10% expected by chance) — just not at
RSI3<10 specifically. A future round could search each asset's own best
RSI period/threshold under the guard, with a proper walk-forward
validation (fit on one window, confirm on a later one) rather than
picking whichever cell won this round's snapshot — SOL, XRP, and DOGE's
full histories are now cached locally, so that round doesn't need any new
data. Until that round runs and clears its own out-of-sample bar, the live
book should trade washout without the eye gate.
