# Step 458 — his levels, decoded off the screen and matched to real futures bars

Wallace's idea, and it worked:

> "this problem seems fixable tbh, this whole entire screen thing. at the end of
>  the day, anything behind the charts is just code and numbers too."

Every horizontal line he draws sits at a price. This round read those prices off
the pixels and looked them up in real ES and NQ bar data. **30 drawn lines were
decoded across 5 sessions and 4 instruments-days. 24 of them are named exactly.
6 are not, and they are listed as unidentified rather than guessed.**

Nothing in the bot was changed.

---

## 0. HOW THIS WAS DONE, SO IT CAN BE REDONE

Two things made it exact rather than approximate.

**We do not have to convert.** `data_spx_ES_1h.parquet` and
`data_spx_NQ_1h.parquet` hold real ES and NQ hourly bars from 2024-03-01 to
2026-07-24. He trades ES and NQ, so no SPY/QQQ ratio was needed for anything in
the table below. The only place a fund was used was one timing check, and it is
labelled where it appears. Our NQ feed sits about 0.25 index points below his
display (his 21,330.50 against our 21,330.25), which is a contract-roll
difference and is small enough to leave every match unambiguous.

**The price axis can be calibrated to under a point.** The axis labels are
evenly spaced, so detecting the label rows gives pixels-per-point directly, and
TradingView prints the price of some drawn lines in a tag at the right edge,
which pins the calibration. Detector and axis reader live in the scratchpad
(`hl3.py`, `match.py`). On the frame with the most printed tags the calibration
landed within 0.15 index points.

Worked example, `brutal_C/f_006.png`, NQ 5-minute, 2025-06-02 10:11 ET:
calibration `price = 21420 - 1.087 * (y - 205)`, checked against the crosshair
tag (predicted 21,177.0, printed 21,178.50) and re-derived independently on the
1-minute frame 40 seconds earlier. The two frames agreed on all five lines to
better than 1.5 points, and all five then matched real NQ bars to 0.5 points or
less.

**A colour code fell out of it and holds on all five sessions:**

| colour | what it is |
|---|---|
| red | Asia session high and Asia session low |
| blue | London session high and London session low |
| black (price tag shown) | everything else: previous day, 1-hour levels, today's own session extremes |

---

## 1. THE TABLE

Prices in the "read" column are what came off the pixels. Prices in the "is"
column are the actual bar values from our futures data.

### 2K8gXiyR3Jg "TODAY WAS BRUTAL" — Monday 2025-06-02

| frame | video ts | inst | tf | read | what it is | in our data | ours? | conf |
|---|---|---|---|---|---|---|---|---|
| brutal_C/f_006, f_002 | 21:52 / 21:15 | NQ | 5m + 1m | 21,447.25 (tag) | 1-hour swing high, 2025-05-29 15:00 ET | 21,447.25 | YES `swing_levels(60)` | high |
| " | " | NQ | " | 21,348.3 | **Asia session high** | 21,348.50 (Jun 1 18:00 bar) | YES `session_levels` asia | high |
| " | " | NQ | " | 21,291.4 | **London session high** | 21,291.50 (07:00 bar; the 08:00 hour's higher print came after 08:30, checked on QQQ 1-minute) | YES `session_levels` london | high |
| " | " | NQ | " | 21,198.5 | **Asia session low** | 21,198.00 (02:00 bar) | YES | high |
| " | " | NQ | " | 21,163.6 | **London session low** | 21,163.25 (03:00 bar) | YES | high |
| brutal_B/f_004, f_002; brutal_A/f_003 | 16:37 / 06:41 | ES | 5m + 1h | 5,909.3 | **Asia session high** | 5,909.25 | YES | high |
| " | " | ES | " | 5,900.0 | **London session high** | 5,900.00 (07:00 bar; 08:00-08:30 stayed below, checked on SPY 1-minute) | YES | high |
| " | " | ES | " | 5,877.8 | **Asia session low** | 5,877.75 | YES | high |
| " | " | ES | " | 5,867.5 | **London session low** | 5,867.50 | YES | high |
| brutal_B/f_004 | 16:37 | ES | 5m | 5,853.25 (tag) | **previous day low** (Fri 05-30, 18:00 to 18:00). Also the previous New York session low, the previous week's low, and a 1-hour swing low. | 5,853.25 | YES `session_levels` prev_day | high |
| brutal_D/f_006 | ~01:15 | NQ | **1 Day** | — | **NOTHING DRAWN.** Not one horizontal line on the daily chart, only the crosshair. | — | n/a | high |

### ssPMxVk6B9Y "CHOPPY PRICE ACTION" — Thursday 2025-05-22

| frame | video ts | inst | tf | read | what it is | in our data | ours? | conf |
|---|---|---|---|---|---|---|---|---|
| choppy_B/f_003 | 01:06 | NQ | 1h | 21,441.25 (tag) | **CANNOT TELL.** Exactly the high of the 2025-05-20 14:00 hourly bar (ours 21,441.50), but the 13:00 bar is higher, so it is not a two-candle swing high, and it is not any session or previous-day extreme. | 21,441.50 | **NO** | low |
| " | " | NQ | 1h | 21,328.00 (tag) | **CANNOT TELL.** Exactly the low of the 2025-05-15 11:00 hourly bar (ours 21,327.75), but the 10:00 bar is lower, so not a two-candle swing low, and not a session extreme. | 21,327.75 | **NO** | low |
| " | " | NQ | 1h | ~21,244 | London session high | 21,243.50 | YES | medium (1 px = 3.1 pts at this zoom) |
| " | " | NQ | 1h | ~21,208 | Asia session high | 21,208.50 | YES | medium |
| " | " | NQ | 1h | ~21,113 | Asia session low | 21,113.75 | YES | medium |
| " | " | NQ | 1h | ~21,038 | London session low | 21,040.00 | YES | medium |
| choppy_A/f_004 | 02:36 | ES | 5m | 5,876.88 | **London session high** | 5,876.75 | YES | high |
| " | " | ES | 5m | 5,874.34 | **Asia session high** | 5,874.25 | YES | high |
| " | " | ES | 5m | 5,851.19 | **Asia session low** | 5,851.00 | YES | high |
| " | " | ES | 5m | 5,829.04 | **London session low** | 5,828.75 | YES | high |
| " | " | ES | 5m | 5,835.75 (tag) | 1-hour swing low, 2025-05-13 00:00 ET. Nine days old, and already swept by London that morning, and still on his chart. | 5,835.75 | YES, but at the edge of `level_lookback_days = 10` | high |
| " | " | ES | 5m | 5,815.75 (tag) | 1-hour swing low, 2025-05-12 12:00 ET. **Ten days old.** | 5,815.75 | **BORDERLINE**: our 10-day window starts at 05-12 00:00, so this one only just survives, and one more day and it would not | high |

### mV3YFmtnRdo — Tuesday 2025-05-20

| frame | video ts | inst | tf | read | what it is | in our data | ours? | conf |
|---|---|---|---|---|---|---|---|---|
| refuse_E/f_003 | 24:07 | ES | 1m | 5,956.96 | **London session low** | 5,957.00 | YES | high |
| " | " | ES | 1m | 5,955.20 | **Asia session low** | 5,955.25 | YES | high |
| " | " | ES | 1m | 5,947.50 (tag) | **CANNOT TELL.** Searched every hourly and 4-hour bar back to 2025-03-01 and every session, previous-day and previous-week extreme. Nothing within 0.25. | no match | **NO** | — |
| " | " | ES | 1m | 5,946.50 (tag) | **CANNOT TELL.** Same, and it sits exactly 1.00 point under the line above, which is why the pair reads more like the two edges of a small zone than like two separate levels. | no match | **NO** | — |
| take_C/f_002 | 33:48 | NQ | 1m | 21,487.00 (tag) | 1-hour swing high, 2025-05-20 01:00 ET | 21,487.00 | YES | high |
| " | " | NQ | 1m | 21,483.75 (tag) | **London session high**, and also a 1-hour swing high at 07:00 | 21,483.75 | YES | high |
| " | " | NQ | 1m | 21,376.50 (tag) | **CANNOT TELL.** Not a session extreme, not a previous-day extreme, not a 1-hour or 4-hour swing. Lives below hourly resolution. | no match | **NO** | — |
| " | " | NQ | 1m | 21,354.25 (grey tag) | **CANNOT TELL.** Sits 0.75 above today's 09:00 hourly low (21,355.00), so "today's session low so far" is possible but not confirmable at hourly resolution. | near 21,355.00 | unclear | low |
| " | " | NQ | 1m | 21,341.50 (tag) | 1-hour swing high, 2025-05-13 15:00 ET. Seven days old. | 21,341.50 | YES | medium-high |
| " | " | NQ | 1m | box 0 ≈ 21,351, 1 ≈ 21,431, 0.5 ≈ 21,391 | equilibrium box over the down-leg, midpoint where he enters | — | YES `TrendTracker.equilibrium` | medium |

### iVOjRDrjFM4 — Wednesday 2025-05-21

| frame | video ts | inst | tf | read | what it is | in our data | ours? | conf |
|---|---|---|---|---|---|---|---|---|
| take_A/f_002, f_006 | 30:36 / 31:14 | ES | 5m + 1m | 5,958.27 | **Asia session high** | 5,958.25 | YES | high |
| " | " | ES | " | 5,934.25 | **London session high** | 5,934.25 | YES | high |
| " | " | ES | " | 5,934.00 (tag) | 1-hour swing high, 2025-05-21 07:00 ET. He draws it even though it sits 0.25 under the London high he has already drawn. | 5,934.00 | YES | high |
| " | " | ES | " | 5,923.05 | **Asia session low** | 5,923.00 | YES | high |
| " | " | ES | " | 5,908.75 (tag) | **today's own session low**, made in the first minutes after the 09:30 open | 5,908.75 | **PARTIAL**, see 3A | high |
| " | " | ES | " | 5,905.00 | **London session low** | 5,905.00 | YES | high |
| take_A/f_006 | 31:14 | ES | 1m | shaded box 5,931.6 to 5,932.85 | the fair value gap he retraces into and enters on. **1.25 index points, 0.02% of the price**, hand-drawn on the 1-minute. | — | **PARTIAL**, see 3D | medium |
| take_B/f_004 | ~31:40 | ES | 1m | 5,934.0 / 5,922.3 | London session high / Asia session low, same two lines | 5,934.25 / 5,923.00 | YES | high |
| " | " | ES | 1m | 5,935.75 (tag) | **today's own session high so far** (our 09:00 hourly bar high is 5,935.25) | ~5,935.25 | **PARTIAL**, see 3A | medium |

---

## 2. WHAT THE TABLE SAYS ABOUT HIS LEVEL SET

**It is small, and it is mostly ours.** Across 30 lines there are exactly four
level families doing almost all the work:

1. Asia session high and low, red, drawn every day, on every instrument.
2. London session high and low, blue, same.
3. Previous day high and low, black.
4. 1-hour swing highs and lows, black, kept for up to ten days.

Plus today's own session extremes, re-marked as the day goes.

**He draws nothing on the daily chart.** `brutal_D/f_006` is an NQ daily with a
two-month range on screen and not one horizontal line on it. The daily is where
he reads direction and how clean the market is, not where he marks price.

**No line in the set needed a 4-hour swing to explain it.** Every level that
matched a 4-hour swing also matched a 1-hour swing or a session extreme. Our
`level_minutes = (60, 240)` is not wrong, but the 240 half never had to earn its
place in these frames.

**Our session windows check out, including the 08:30 boundary.** Two of the days
discriminate: ES on 06-02 and NQ on 06-02 both have an hourly bar spanning 08:30
whose high is above his drawn London high. Reading QQQ and SPY 1-minute bars for
those two hours shows the higher print landed after 08:30 in both cases, so his
London high really is the 08:30 cut and our `prior_session_window = (3, 8.5)` is
right. That was worth checking, because an hourly-only test looks like it
disagrees.

---

## 3. THE LEVEL TYPES WE DO NOT COMPUTE

### 3A. Today's own session high and low, updated live — the biggest one

He marks the current session's extreme in black and re-marks it as the session
extends. On 2025-05-21 at 10:00 the black line is at 5,908.75, the low made just
after the open. Eleven minutes later a second black line is at 5,935.75, the
high made since.

Our `ctx.levels` is built once, in `build_context`, using only bars closed before
09:30 (`tjr_bot.py` line 1218), and is then frozen for the day. `session_levels`
does compute a `premarket_ny` pair, but that window ends at the bell. A level
made at 09:35 is never a marked level.

`building_blocks` can pick it up second-hand, through
`swing_levels(d5, 15, now, ...)` on line 2023, but only if that extreme happens
to be a two-candle 15-minute swing, and only after the 15-minute bar containing
it has closed. An opening drive low made in the first fifteen minutes is
frequently neither.

### 3B. 1-hour bar extremes that are not two-candle swings

`21,441.25` and `21,328.00` on his NQ 1-hour chart on 05-22 are both exact
hourly bar extremes in our data, and neither is a two-candle swing because the
neighbouring bar reaches further. `two_candle_swings` (line 498) is our only
generator of 1-hour levels, so both are invisible to us.

I do not know what rule puts them there, and I am not going to invent one. The
three unidentified lines below hourly resolution (`5,947.50`, `5,946.50`,
`21,376.50`) may be the same thing one or two timeframes down, or may be
something else entirely.

### 3C. Order blocks

Already written down as a known hole, in the docstring of `building_blocks` at
line 2007: "ORDER BLOCKS ARE NOT [here] — nothing in this bot finds one, so every
target he would place at an order block is a target we cannot see." Nothing in
these frames confirms or denies it, because an order block drawn as a plain
horizontal line is indistinguishable from any other horizontal line. It stays on
the list.

### 3D. Fair value gaps on the 1-minute

The gap he actually enters on 2025-05-21 is 1.25 index points tall on a 1-minute
chart, which is 0.02% of the price. Our target gaps come from
`gaps_at(..., cfg.instrument.target1_minutes, ...)` with `target1_minutes = 15`.
We are looking for gaps roughly an order of magnitude bigger than the one he
traded.

### 3E. Levels older than ten days

`5,815.75` on his 05-22 chart is the low of the 2025-05-12 12:00 hourly bar, ten
calendar days old. `cfg.level_lookback_days = 10` puts that exactly on the
boundary. One long weekend and a level he is still watching is one our
`build_context` has already dropped.

---

## 4. THE STRAIGHT ANSWER ON "NOTHING AHEAD TO AIM AT"

**No. Our test is not measuring what he means, and it misses in both directions
at once, which is exactly the shape of a change that makes results worse instead
of better.**

Here is the evidence, on the day he says it most clearly.

`2K8gXiyR3Jg` at 21:52, NQ 5-minute, 2025-06-02 10:11 ET, price 21,284.75. He
says: *"there's nothing to target to the upside because we already swept all of
it out."*

Decoded, he has exactly two levels above price: the Asia high at 21,348.50 and
the 1-hour swing high at 21,447.25. **We compute both.** And NQ's 09:00 hourly
bar that morning reached 21,458.00, above both of them. So on his screen there is
nothing left up there, and on our data there is nothing left up there either.

Then look at what our code does with the same facts:

- `ctx.levels` is filtered by `_unswept` at 08:30 and again at 09:30
  (lines 1217 to 1218) **and never again**. At 09:30 neither level had been taken
  yet, so both are still in the marked set at 10:11.
- `building_blocks` iterates `marked_levels` at line 2029 **with no unswept
  test at all**.
- `_orders_filled_beyond` (line 1957) then deliberately relocates the target to
  the far side of the sweep, returning 21,458.00.

So at the exact moment he says there is nothing to aim at, our `build_targets`
hands back a target at 21,458.00 and the refusal does not fire. **On the clearest
example we have of his rule, our implementation of his rule does the opposite.**

`_orders_filled_beyond` is not wrong on its own terms. It encodes a real thing he
says on Day 11 about orders being filled above a swept high. But it is being
applied in the one place where he is on camera saying the level is gone, and the
result is that "already swept" makes a target more attractive to us and makes it
disappear for him.

And in the other direction, the four gaps in section 3 all remove destinations we
should be able to see. A day where the only thing left ahead is the session's own
high made at 09:40 is a day where he has a target and we report none, and the
refusal fires on our blindness rather than on his rule.

That is how the same switch can delete 15 trades worth $271 on Wallace's real
account: it refuses the wrong days and permits the wrong days.

**What this does not say:** it does not say the refusal is a bad idea. Every one
of the nine refusals in step457 is still a refusal about the destination. It says
the test as coded is not the test he runs, so the July result is not evidence
about his rule. It is evidence about ours.

---

## 5. WHAT WOULD SETTLE IT, AND IT IS NOT A REWRITE

Four things, in order of how much they are likely to move:

1. Re-apply `_unswept` to `marked_levels` inside `building_blocks`, so a level
   taken out during the session stops counting as a destination, and put
   `_orders_filled_beyond` behind that switch instead of in front of it. Then
   re-run July with the refusal both on and off. This is a handful of lines and
   it is the one that touches the clearest quoted example.
2. Add today's own session high and low to the destination set and keep them
   current through the day, rather than freezing at 09:30.
3. Measure, do not assume: for every trade in `step455_sp_trades.csv`, record the
   distance to the nearest unswept destination in units of the stop, under both
   the old and the new destination set, and look at whether the split predicts
   the outcome before touching the entry rule at all.
4. Leave the four unidentified level types alone until there is a frame that
   explains them. Building a wrong level type into the bot is exactly the thing
   that would take weeks to find.

---

## 6. HONEST LIMITS

- Six lines are unidentified and are marked as such in the table. Three of them
  (`5,947.50`, `5,946.50`, `21,376.50`) sit below the resolution of the only
  ES/NQ data we hold, which is hourly. A 1-minute or 5-minute ES/NQ feed would
  settle them, and nothing else will.
- `21,354.25` and `21,388.00` on the NQ 05-20 frame carry grey price tags rather
  than black ones, which in TradingView usually means a different kind of line.
  I do not know which kind. Frame: `take_C/f_002.png`.
- The `choppy_B/f_003` readings for the red and blue lines carry about 6 points
  of systematic offset because a 1-hour NQ chart at that zoom is 3.1 index points
  per pixel. The four identifications hold, the exact prices in that block do not.
- The colour code (red Asia, blue London) is consistent across all five sessions
  and both instruments, which is 20 lines. It is still an inference from
  consistency, not something he says out loud in these frames.
- Nothing here revives prominent high or area of accumulation, and nothing here
  should be read as doing so.
- **No code was changed. No git command was run. Nothing was traded.**

Frames and tooling:
`/private/tmp/claude-501/-Users-wallacechen/f12ae3f6-df77-43bb-b438-d778ff0c328d/scratchpad/`
(`frames/`, `up/` for the upscaled reads, `hl3.py` line detector, `match.py`
level classifier, `ax_*.png` axis crops).
