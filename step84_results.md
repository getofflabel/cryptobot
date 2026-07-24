# Round 84 — The Blind Chart Drill

Wallace's method, mechanized and measured: look at a chart with the second half
blurred, decide what trade you'd place, only then unblur and see if you were
right. This round builds the harness (`step84_blind_drill.py`), runs 40 real
drills, and grades the one question that matters — does looking at a chart
produce a judgment with predictive power, and where does that judgment break
down.

**Discipline actually followed:** all 40 "before" images were rendered first
(`step84_blind_drill.py generate`). I then looked at each before-image, one at
a time, and recorded a structured call (`step84_blind_drill.py record`) before
looking at any after-image — the after-images did not exist on disk yet at
that point, so there was no way to peek even by accident. Only once all 40
calls were locked in did `step84_blind_drill.py reveal` render the after-images
and score every call against real forward data. No call was revised after
seeing an outcome.

## Causality check (explicitly verified, as asked)

The "before" renderer (`render_before()`) is only ever handed
`candles.iloc[:decision_idx+1]` — there is no parameter through which a future
bar could reach it, and its y-axis is `nanmin`/`nanmax` of exactly that slice
(+6% padding). `self_test_causality()` proves this on real data: it renders
the same BTC 1h decision point twice — once from the full cached series (which
has ~50,000 future bars available) and once from a copy of the DataFrame
physically truncated one bar past the decision bar — and asserts the two PNGs
are **byte-identical**. Run via `python3 step84_blind_drill.py causality_test`:

```
causality self-test PASSED (before-image bytes identical with/without future data)
```

If a future bar were leaking into the axis range or the moving averages, the
two renders would differ. They don't, by construction.

## The setup

- 40 drills: BTC 1h (14), BTC 15m (13), ETH 1h (13).
- Decision points were stratified by `step82_eye.label_eye_states()` — one
  pass tried to grab one example of each (structure × quality) combo per
  series, a second pass filled the remainder while capping any one structure
  at roughly `n/5 + 1` so no single regime dominated. Minimum spacing between
  decision points (`lookback/2` bars) so drills aren't near-duplicates of each
  other.
- Horizon: 24 bars on 1h, 48 bars on 15m (per the brief).
- Each "before" image: 120 bars, dark theme, OHLC candles, MA20/MA50 (computed
  causally over the full history up to the decision bar, not just the visible
  window, so there's no MA warm-up gap at the left edge), fixed y-axis from
  the visible window only.
- `chart_reader.read_chart()` was computed at the same decision bar and
  recorded in the CSV, but I never looked at those columns while forming a
  call — only the PNG. The eye's read was compared to my call only after the
  fact, in the analysis below.

### Composition (structure × quality actually drawn)

| structure  | clean | messy | total |
|------------|-------|-------|-------|
| uptrend    | 4     | 7     | 11    |
| downtrend  | 8     | 5     | 13    |
| transition | 5     | 7     | 12    |
| range      | 2     | 0     | 2     |
| chop       | 0     | 2     | 2     |
| **total**  | 19    | 21    | **40**|

Trends and transitions are well represented; range and chop are thin (2 each)
— across six years of hourly/15m BTC and ETH, sustained clean sideways range
and outright chop are simply rarer than trending/transitional bars once you
also require enough forward horizon and spacing between samples. Honest
limitation: **don't generalize the range/chop numbers below** — n=2 each,
effectively single data points once one of the two is a "no trade."

## Scoring rules (`score_call`)

- "no trade" → `flat`, R=0, recorded but not entered.
- Entry within 0.05% of the decision bar's close = immediate market fill.
  Otherwise it's a resting limit/stop and future bars are scanned in order
  for the first touch; never filled within the horizon → `no_fill`, R=0.
- Once filled, stop/target are checked starting the bar **after** the fill
  bar (conservative — fill and exit are never resolved off the same
  intrabar range).
- **Stop wins on a tie** if one bar's range touches both stop and target.
- No stop/target hit inside the horizon → `time` exit at the horizon's final
  close.
- R = (exit − entry) / |entry − stop| × direction.

## Headline numbers

| | n | avg R | W / L / flat|
|---|---|---|---|
| **All 40 drills** | 40 | **−0.056** | 12 / 20 / 8 |
| Long calls | 19 | **+0.255** | 8 / 9 / 2 |
| Short calls | 13 | **−0.544** | 1 / 11 / 1 |
| No-trade calls | 8 | 0.000 (by definition) | — |
| Entered trades only (excl. 3 no-fills) | 29 | −0.077 | 9 / 20 hit rate **31.0%** |

Outcome mix: 16 stop, 8 flat (no-trade), 7 target, 6 time-exit, 3 no-fill.

**The single biggest number here: shorts lost, longs roughly broke even.**
Longs went 8W/9L for +0.255R average — a real, if modest, edge. Shorts went
1W/11L for −0.544R average — a systematic problem, not noise. Stop-out rate
tells the same story directly: longs got stopped 8/19 (42%), shorts got
stopped 8/13 (**62%**). I was reading "decisive breakdown" candles as
continuation far more often than the market agreed with me.

## Performance by market state

| structure | n | avg R | W/L/flat |
|---|---|---|---|
| uptrend | 11 | −0.097 | 3/6/2 |
| downtrend | 13 | +0.005 | 3/6/4 |
| transition | 12 | **−0.320** | 2/7/3 |
| range | 2 | −0.500 | 0/1/1 (n too small) |
| chop | 2 | +1.808 | 1/0/1 (n too small, one big winner) |

| quality | n | avg R | W/L/flat |
|---|---|---|---|
| clean | 19 | **−0.394** | 2/12/5 |
| messy | 21 | **+0.251** | 7/8/6 |

**Where judgment held up:** trending regimes (uptrend + downtrend combined,
n=24) were close to breakeven, avg R ≈ −0.04 — not a real edge, but not a real
leak either. **Where it broke down:** `transition` bars (n=12, a real sample)
were clearly the worst reliable category at −0.320 avg R with only 2 wins in
9 trades taken. That's the state where structure is actively changing and the
direction isn't confirmed yet — exactly where a human eye should expect to be
guessing, and the numbers now confirm it. **The counter-intuitive result:**
"clean"-labeled setups (obvious trend, tidy candles, well-separated MAs) did
*worse* (−0.394 avg R, 10 stops out of 16 trades) than "messy" ones (+0.251
avg R, only 6 stops out of 16). Clean/obvious setups also look obvious to
every other trader watching the same chart — several of the clean-trend
longs and shorts here were stopped out by a sharp reversal right after entry
(see the post-mortems below), consistent with "the obvious trade is crowded
and gets faded."

## Head-to-head: my visual judgment vs. the computed eye

`chart_reader.read_chart()`'s `tradeable` flag is its stand-aside/trade
signal at the same decision bar. I never looked at it before calling.

| bucket | n | avg R |
|---|---|---|
| **Agree — both said trade, I took it** | 14 | **−0.200** |
| **Disagree — eye said stand aside, I traded anyway** | 18 | **+0.032** |
| Disagree — eye said tradeable, I stood aside | 2 | 0.000 |
| Agree — both said stand aside | 6 | 0.000 |

This is the finding I'd least have predicted: when the computed eye and I
**agreed** there was a trade, those trades did *worse* (−0.200 avg R) than
the trades I took when the eye said **stand aside** and I overrode it
(+0.032 avg R). Reading the eye's `best_tool` breakdown explains a chunk of
this — the eye's `tradeable=True` calls fire almost entirely off
`trend-follow` (a clean uptrend/downtrend) or `range-fade`/`breakout`
mechanically, the same "obvious, clean, everyone sees it" setups that
underperformed above. Its `stand aside` bucket, by contrast, is a mixed bag
that includes plenty of situations that were genuinely tradeable to a human
eye (a fresh breakout candle inside an otherwise "messy" reading, a bull flag
a few bars into forming) but that the eye's structure/quality thresholds
hadn't caught up to yet. The eye is not wrong to be conservative — but this
round's evidence is that its conservatism and my independent read are not
capturing the same information, and blindly agreeing with it would have cost
more than blindly ignoring it, on this sample.

**Caveat:** n=14/18/2/6 across four buckets is not enough to trust the sign
of this on its own; it's a hypothesis this drill format is well-suited to
re-test at larger scale, not a verdict on `chart_reader.py`.

## 5 best calls

| drill | call | R | outcome | image |
|---|---|---|---|---|
| d022_BTCUSDT_15m | long | **+3.62** | target | `step84_drill_images/d022_BTCUSDT_15m_{before,after}.png` |
| d024_BTCUSDT_15m | long | +2.33 | target | `step84_drill_images/d024_BTCUSDT_15m_{before,after}.png` |
| d007_BTCUSDT_1h | long | +1.75 | target | `step84_drill_images/d007_BTCUSDT_1h_{before,after}.png` |
| d018_BTCUSDT_15m | short | +1.71 | target | `step84_drill_images/d018_BTCUSDT_15m_{before,after}.png` |
| d013_BTCUSDT_1h | long | +1.67 | target | `step84_drill_images/d013_BTCUSDT_1h_{before,after}.png` |

**d022 (2024-01-28, BTC 15m)** — before-image showed a wide round-trip swing
(42200→41380→42200) but the most recent leg was a clean, strong impulsive
rally pulling back only mildly to MA20. Call was long the shallow pullback.
After-image: price resumed immediately, tearing from ~42000 to a high near
42750 within the next dozen bars — the pullback really was just a pause, not
a reversal. Best call of the round, and notably it's flagged `chop|messy` by
the labeler — a reminder that the label on the whole trailing window and the
tradeable structure of the last few bars aren't always the same thing.

**d024 (2024-07-06, BTC 15m)** — a fresh breakout to new highs after a
mid-chart consolidation, taken right on the breakout candle. After-image:
clean continuation to ~58500, no meaningful pullback first. What made this
one easy: the breakout candle was large-bodied and the breakout base held
throughout the prior consolidation (price never gave back into the
pre-breakout range) — the cleanest possible "buy strength" tell.

**d007 (2023-04-26, BTC 1h)** — breakout from a multi-day range, followed by
tight small-bodied consolidation right at the highs (not selling off). Called
it a bull flag, not exhaustion. After-image confirmed continuation to target.
The tell that made this call correctly, in hindsight: consolidation candles
that stay *small and tight*, not retracing meaningfully into the breakout
base, are a genuinely different picture from consolidation candles that give
back 30-50% of the move (which is closer to what happened in the d037 loss
below).

**d018 (2022-07-23, BTC 15m)** — a decisive breakdown through a multi-hour
chop range with two large expanding-range red candles. Short worked cleanly
to target. What separated this from the shorts that failed: the breakdown
candle here made a genuinely new multi-hour low outside the whole prior
range, not just a dip within noise.

**d013 (2026-02-25, BTC 1h)** — a violent V-recovery breaking back into the
exact zone where a prior selloff had originated, on a huge green candle. This
was a contrarian-feeling long (buying right into old resistance) that worked
because the velocity of the reclaim (not a grind, a single outsized bar) read
as real conviction, not a slow fade.

## 5 worst calls

| drill | call | R | outcome | image |
|---|---|---|---|---|
| d002_BTCUSDT_1h | short | −1.00 | stop | `step84_drill_images/d002_BTCUSDT_1h_{before,after}.png` |
| d029_ETHUSDT_1h | long | −1.00 | stop | `step84_drill_images/d029_ETHUSDT_1h_{before,after}.png` |
| d037_ETHUSDT_1h | long | −1.00 | stop | `step84_drill_images/d037_ETHUSDT_1h_{before,after}.png` |
| d040_ETHUSDT_1h | short | −1.00 | stop | `step84_drill_images/d040_ETHUSDT_1h_{before,after}.png` |
| d017_BTCUSDT_15m | long | −1.00 | stop | `step84_drill_images/d017_BTCUSDT_15m_{before,after}.png` |

(16 calls tied at exactly −1.00R via a clean stop-out; these 5 are chosen for
how differently they failed, not because they're uniquely "worse.")

**d002 (2020-10-08, BTC 1h)** — read two large red candles breaking a
consolidation low as a decisive breakdown, shorted it. After-image: that was
the exact low. Price reversed within 1-2 bars and rocketed from ~10570 to
above 10900 — a violent bear trap. The picture I was reading as "momentum
confirming down" was, in hindsight, indistinguishable from "capitulation
candle right before a reversal" — I had no way in the before-image to tell
those apart, and I didn't wait for confirmation that the breakdown would
actually follow through (e.g., a failed bounce) before entering.

**d029 (2021-11-27, ETH 1h)** — after a severe 14.6% crash, a few green
candles pushing back above MA20 read to me like an early bounce worth buying.
After-image: the bounce immediately failed, price rolled back over and never
threatened my target — a 3-4 candle green stretch after a crash of that size
just wasn't enough evidence of a real reversal.

**d037 (2025-07-18, ETH 1h)** — a long, clean staircase uptrend consolidating
tightly right at fresh multi-day highs; I called it a flag and bought
continuation. After-image: it topped exactly there and chopped/faded for the
next 24 bars, tagging my stop. Contrast with d007 above (which had the
*same* surface pattern — tight consolidation at highs — and worked): the
difference I can point to only in hindsight is that d037's uptrend had
already run much longer and further (2930→3670, a huge multi-day advance)
before this consolidation, versus d007's shorter, fresher breakout. Length
and extension of the prior move matters and I wasn't weighing it.

**d040 (2026-06-14, ETH 1h)** — a shallow dip below flattening MAs after a
choppy range read to me as "momentum shift down." After-image: it was the
literal low before an +11% vertical breakout the other way. This is the same
shape of mistake as d002 — treating a modest move below a flat MA cluster in
low-conviction chop as directional information, when it's exactly the kind
of noise a spring/shakeout produces right before the real move.

**d017 (2022-01-15, BTC 15m)** — bought a pullback to MA support in what
looked like a recovery uptrend. After-image: price undercut my stop by one
more leg down before turning around and rallying hard to new highs — the
directional read was right, the stop placement was one shakeout too tight.
This is a risk-management miss, not a directional one.

## What I learned to look for / what fooled me

1. **A single breakdown or breakdown-looking candle right after a sharp prior
   move is unreliable as a standalone continuation signal — it's just as
   often the shakeout right before the reversal.** d002, d017, and d040 all
   have this exact shape: a modest move through a nearby level, read by me as
   "momentum confirming," that turned out to be the extreme of the move, not
   the middle of it. The distinguishing tell I didn't have and should build
   into the next round: whether the breakdown/breakout candle makes a genuine
   new multi-*day* extreme (like d018's winning short) versus just clearing a
   multi-*hour* local level inside a bigger range (like d002's and d040's
   losses). Local-level breaks are noisy; structural-level breaks aren't.

2. **Consolidation at highs is not automatically a bull flag — the length and
   size of the move that produced it matters.** d007 and d024 (fresh,
   shorter breakouts holding tight near the highs) worked; d037 (a
   consolidation at the end of a long, already-extended staircase run) didn't.
   I was pattern-matching on the *shape* of the consolidation (tight,
   small-bodied, not giving back gains) without weighing how far the move had
   already traveled before that consolidation started. Next round should
   explicitly measure/label "distance from the start of the current leg" as
   a feature, not just eyeball it.

3. **"Obvious, clean, textbook" setups underperformed messier ones in this
   sample, and agreeing with the computed eye did worse than overriding it.**
   Clean-labeled trades were stopped out at nearly double the rate of messy
   ones (10/16 vs 6/16), and the 14 trades where I agreed with `chart_reader`
   that something was tradeable averaged −0.200R versus +0.032R when I traded
   through its "stand aside." The working hypothesis: a setup that looks
   obviously tradeable to a simple rule-based eye also looks obvious to every
   other participant, and crowded, obvious trades are the ones that get
   faded. This doesn't mean "always fade the obvious trade" — the sample is
   too small and this round didn't test that as its own strategy — but it
   does mean obviousness alone is not the edge I intuitively treated it as,
   and the next drill round should test a deliberate contrarian variant.

## Files

- `step84_blind_drill.py` — the harness (generate / record / reveal / causality_test CLI).
- `step84_drills.csv` — all 40 drills: decision metadata, my structured calls
  (recorded blind), the computed eye's read at the same bar, and the scored
  outcome.
- `step84_drill_images/` — 80 PNGs (`{drill_id}_before.png` /
  `{drill_id}_after.png`), 40 before/after pairs.

No commits made, no live orders placed — research only, per the brief.
