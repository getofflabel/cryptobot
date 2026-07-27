# Step 457 — what the charts show

First round done with eyes instead of transcripts. Frames pulled from six videos,
read directly as images. Every finding below carries the video, the chart clock
visible in the frame, what he said, what the frame showed, and the frame path.

Frames live in
`/private/tmp/claude-501/-Users-wallacechen/f12ae3f6-df77-43bb-b438-d778ff0c328d/scratchpad/frames/`
and are named by moment (`brutal_A/f_003.png` etc). Nothing in the bot was changed.

---

## 0. THE THING THE TRANSCRIPTS COULD NOT SHOW

**He runs two of his own indicators on the chart, and they are on screen in every
live session frame.** Neither has ever appeared in any extraction we have done,
because you cannot hear an indicator.

**TJR Order Flow.** A three-row panel, top right of the chart. One row each for
1H, 5m and 1m. Each row is either green "Bullish" or red "Bearish", with a
countdown to that timeframe's candle close. He confirms it out loud:

> "Literally everything, every single order flow on NASDAQ is bullish. Shout out
> to the TJR orderflow indicator. So I don't even have to look at that."
> — `iVOjRDrjFM4` @ 00:30:36

and, on what it is:

> "it's not a buy or sell indicator. It's literally just telling you the
> confluences that I use on a daily basis. It just helps my lazy ass."
> — `mV3YFmtnRdo` @ 00:14:50

**TJR Macro Timer.** A second box, directly under the first, counting either
"Until Macro Opens" or "Until Macro Closes". Two frames pin the window exactly:

- `take_A/f_002.png` — chart clock **10:00:32 ET**, box reads **"0h 9m 26s Until Macro Closes"**
- `choppy_B/f_003.png` — chart clock **10:10:22 ET**, box reads **"23h 39m 37s Until Macro Opens"**

**The macro is 09:50 to 10:10 ET.** Our `MANIP_END_T = 09:50` is his macro OPEN,
read off his own screen rather than inferred. That is a clean confirmation.

He also narrates the boundary from the other side, in the session where he took
nothing:

> "Realistically, this was the ideal trade, the sweep of this, but then rotate
> down. But this happened **pre-macro, like seven minutes pre-macro**"
> — `2K8gXiyR3Jg` @ 00:21:15, frame `brutal_C/f_002.png`

Seven minutes before 09:50 is 09:43. He watched a setup he calls ideal, and
refused it on the clock alone.

**Measured, and this is the honest half:** splitting our 467 S&P trades on that
window shows **no edge inside it**. 235 trades entered 09:50–10:10 won 42.1% and
returned +0.01x what was risked; 232 entered 10:10–10:30 won 50.4% and returned
+0.07x. The macro window is real and it is his, but it is not the thing that
separates his winners from ours. Do not chase it.

---

## 1. WHY HE REFUSES A SETUP THAT MEETS EVERY RULE

Nine refusal moments were read across three sessions. **One reason shows up in
every single one, and it is not about the setup at all. It is about the
destination.**

He refuses when the pool of liquidity he would be aiming at has already been
taken, or is sitting too close to pay.

### 1.1 The clearest instance — all three timeframes agree, and he still says no

`ssPMxVk6B9Y` (ZERO — CHOPPY PRICE ACTION) @ 00:01:06, frame `choppy_B/f_003.png`

**Said:** "We're currently above these highs. I probably am not going to take a
trade today just to keep it completely honest with you guys."

**Showed:** NQ 1-hour. TJR Order Flow reads **1H: Bullish / 5m: Bullish / 1m:
Bullish — all three green, fully aligned.** Chart clock 10:10:22, inside his
trading hours. Price 21,305.

And above price: a band roughly 21,300 to 21,500 that is two weeks wide and made
entirely of overlapping bars crossing back and forth. His drawn levels at 21,328
and 21,441 both sit inside that band. The one clean level, 21,441, is on the far
side of the mess.

**Read:** the direction gate passes perfectly. He refuses because a long from
here walks straight back into the range it just fell out of. There is no clean
run to be had.

**Verdict: CONTRADICTS what we built.** Our alignment test would pass this and we
would fire.

### 1.2 The same refusal, said out loud, twice in one session

`2K8gXiyR3Jg` (ZERO — TODAY WAS BRUTAL)

@ 00:13:18 — "there's just not really much for us to target to the downside"

@ 00:21:52, frame `brutal_C/f_006.png` — "**there's nothing to target to the
upside because we already swept all of it out.** There's nothing to target to the
upside because we already swept all of it out. The targets to the downside are I
mean are like okay I guess."

**Showed:** NQ 5-minute, price 21,284.75. Above price his drawn red level sits at
~21,345 and a black one at 21,447 — and the frame shows a spike five bars earlier
that reached 21,447 and came straight back. Both upside pools consumed. Below,
unswept, a red line at ~21,207 and a blue at ~21,178, roughly 78 and 107 points
away.

**Read:** he inventories what is left and how far it is, on the levels he has
personally drawn, and that inventory is the gate.

### 1.3 Refused because the target was too close

`2K8gXiyR3Jg` @ 00:16:37, frames `brutal_B/f_002.png` and `brutal_B/f_004.png`

**Said:** "I wouldn't really want to be looking for longs here **because we're so
close to these London session lows.** I would be trying to find a reason to go
short down to the London session lows. But even that dude, I don't know, man."

**Showed:** ES 5-minute, price 5,880.25. His blue London-low line is at
**5,867.75** — about 12 index points below, roughly 0.2% of the price. That is
the whole trade.

**Read:** distance-to-target is an explicit, spoken refusal criterion, and the
frame confirms he means the number he can see, not a feeling.

### 1.4 Refused a short into a live up-leg

`ssPMxVk6B9Y` @ 00:02:36, frames `choppy_A/f_002.png` (NQ) and `choppy_A/f_004.png` (ES)

**Said:** "I don't really want to take shorts here just because it's pretty much
like catching a — I guess not falling knife but **rising knife** in this scenario.
Because this very well could just be a 5-minute retrace."

**Showed:** NQ panel reads 1H Bullish / 5m Bullish / **1m Bearish**. ES panel
reads 1H Bearish / 5m Bullish / **1m Bearish**. On both charts a single tall
blue candle has just torn upward through his drawn level (NQ 21,200→21,328;
ES through 5,876).

**Read:** the only thing supporting his short is the 1-minute, the shortest and
freshest row. He will not trade off the 1-minute alone against a 5-minute that
just broke the other way. Note this is not a blanket alignment rule — see 1.6.

### 1.5 The pools got taken before he could use them

`mV3YFmtnRdo` @ 00:24:07, frame `refuse_E/f_003.png`

**Said:** "That sucks that we came down and took out the [levels he names by his
own nicknames] lows. Now it's like **what do we even do from here?** Macro just
opened... Oh, am I seriously not going to take a trade today, dude?"

**Showed:** ES 1-minute, chart clock **09:50:39** — macro literally just opened,
box reads "0h 19m 19s Until Macro Closes". Order Flow: 1H Bearish / 5m Bearish /
1m Bearish — **all three aligned bearish.** Price 5,953.25 after a vertical drop.
His remaining drawn lines below sit at 5,947.50 and 5,946.50, about 6 points away.

**Read:** perfect alignment, perfect timing, and his complaint is entirely about
the fact that the move already happened and the pools are gone. Same refusal as
1.2 and 1.3, third session, third instrument state.

### 1.6 What he DOES take — and it breaks the alignment story

Nine minutes later in that same session, he enters.

`mV3YFmtnRdo` @ 00:33:48, frame `take_C/f_002.png`

**Said:** "Okay, we closed above that. I'm going to enter with the rest of my
position." Then: "Please burn up. Please burn up. Turn up." (he is long)

**Showed:** NQ 1-minute, chart clock 09:59:45, inside macro. Order Flow reads 1H
**Bearish** / 5m **Bearish** / 1m **Bullish** — he is entering *against* two of
the three rows. On the chart: a GAN box drawn over the down-leg with its midpoint
line at roughly 21,394, a fair-value-gap rectangle drawn at 21,378–21,400, the
macro window shaded pale blue, and price sitting on the midpoint at 21,394.

Earlier in the same session, @ 00:14:58: "We took out these lows. Now I'll be
comfortable... **ES made lower lows right here.** That would be fire if we could
make a little SMT."

**Read:** in 1.4 he refused a short with 5m against him; here he takes a long with
5m *and* 1H against him. The difference is not the panel. It is that here a
liquidity sweep had completed on both indexes with a divergence between them, and
the retrace came back into a drawn gap. **The Order Flow panel is his continuation
aid, not his entry gate.**

**Honest caveat:** I am reading "burn up / turn up" as wanting price higher, and
the box label at the right edge could be 0.5 or 0.6 — the resolution is not
conclusive. The panel colours and the box geometry are unambiguous; the direction
is a strong inference, not a certainty.

### 1.7 The other confirmed take, and what it looked like

`iVOjRDrjFM4` @ 00:30:36–00:31:14, frames `take_A/f_002.png` and `take_A/f_006.png`

**Said:** "Literally everything, every single order flow on NASDAQ is bullish...
**But on ES, we're bearish.** I would love to just see us sweep these highs and
then rotator cuff straight down here... I'm going to enter right here on ES."

**Showed:** ES panel 1H Bearish / 5m Bullish / 1m Bearish while (per his words)
NQ is all-bullish. That gap between the two indexes IS the trade. On the ES
1-minute at entry: price had swept the blue line at 5,934, rolled over, and
retraced into a hand-drawn grey box about 2 points tall at 5,930–5,932. Entry
5,929.25. Risk to above the gap is roughly 5 points; the nearest unswept pool
below is ~10 points. Better than 2:1 before he clicks.

Second entry, `take_B/f_004.png`, chart clock 10:11:02 — same shape, and note
the Macro Timer already reads "Until Macro Opens", i.e. he entered **after** the
macro closed. The macro is a preference, not a fence.

### 1.8 What this costs us, in our own numbers

`build_targets` in `tjr_bot.py` (line 2045) is already correct on this: it
returns nothing when no drawn block sits at or beyond 1:1. The comment even says
so — "NEVER AN INVENTED PRICE."

But at line 2779 the caller does this:

```python
        if not targets:
            # He never says what to do here and this is not an entry rule, so
            # nothing is refused: the position simply has no place to take
            # profit and runs to its stop or to the close.
```

**We take the trade anyway.** That comment says "he never says what to do here."
He does. He says it on camera, pointing at the chart, at least four separate
times across three sessions, and then he closes the laptop.

The shadow of it is already in our results. Of 467 S&P trades in
`step455_sp_trades.csv`, **203 (43%) end "flat by the close"** — they never reach
a target and never get stopped, they just drift to the bell, returning +0.62x what
was risked. By contrast the 58 that travelled far enough to bank take-profits
before the 1-minute turned against them returned +1.57x, and the 199 that got
stopped returned -1.01x. Those 203 drifters are, on this reading, trades into a
destination that was not there.

**This is the single highest-value finding in this round.** Same setup count as
him, worse hit rate, and the mechanism is visible: we fire at setups whose
destination has already been consumed or is too close to pay for the stop.
Confirming it needs a measurement round, not this one.

---

## 2. CLEAN VERSUS MESSY, AS SEEN

He uses the words constantly. The frames make them concrete.

`2K8gXiyR3Jg` @ 00:06:41, frame `brutal_A/f_003.png`

**Said:** "What's better price action to trade — **the this**, or when we're like
**moving cleanly and smoothly to the upside?** It's almost never going to be this.
From like Thursday up until today is pretty freaking nasty."

**Showed:** one ES 1-hour chart containing both halves side by side.

*The clean half* (left two-thirds): an ascending staircase from ~5,860 to ~6,000.
Bars are mostly one colour, bodies large relative to the whole bar, each bar's
body clearing the previous bar's body. Pullbacks last three to five bars and are
shallow.

*The messy half* (right, the two days he is complaining about): a sharp drop, then
a dense knot of small bars in a band about 30 to 40 points wide. Bodies are small,
bars overlap almost completely, colours alternate, and price crosses the same
horizontal levels repeatedly.

He then makes the same contrast on the daily, `brutal_D/f_006.png`: big-bodied
daily bars stepping cleanly up the left side, small overlapping ones at the right
edge.

And on the retrace shapes, `brutal_D/f_003.png` @ 00:01:15:

> "Retraces tend to be super sloppy... Either make a move down like this — this is
> a good example of a downwards retrace — **or we consolidate and it looks like
> this**. But then **on the high time frames it looks like a clean retrace.**"

**What I see, stated as description not metric:** the difference is
*displacement per bar versus overlap between bars.* Clean = each bar's body
extends the move and sits mostly outside the previous bar's body. Messy = bodies
are small, ranges are mostly wick, and consecutive bars occupy the same price
band.

**PROPOSAL, clearly marked as ours and not measured:** over the last N bars on the
timeframe he is looking at, compute (a) the fraction of each bar's range that is
body, and (b) the fraction of each bar's range that overlaps the previous bar's
range. "Clean" is high body fraction and low overlap; "messy" is the reverse. A
third candidate is net travel divided by total travel over the window — the
messy right-hand side of `brutal_A/f_003.png` clearly has a low ratio and the
clean left side a high one. **None of these has been tested. Do not implement any
of them on the strength of this document.**

Worth noting: this may be the *same* finding as section 1 wearing different words.
In a messy band every drawn level has already been crossed several times, so
there is nothing unswept left to aim at. If a target-availability test is built
first, a separate cleanliness test may turn out to be unnecessary.

---

## 3. CONFIRMING WHAT WE BUILT, BY EYE

### 3.1 Equilibrium — CONFIRMS

`wzq2AMsoJKY` @ 00:13:25, frame `eq_A/f_004.png`

**Said:** "We take it from the most recent low up to the most recent high."

**Showed:** ES 1-hour in replay. A GAN box anchored with "0" at the swing low
(~6,822) and "1" at the swing high (~6,905), with the 0.5 line drawn across at
about 6,863. The impulse candle that made the leg is the tall blue one inside the
box. Price then retraces into it.

Our definition — midpoint of the leg that made the structure break, on the
timeframe of that break — matches the drawn box. Also confirms he uses it on low
timeframes for execution, not only on the high timeframes.

### 3.2 Break of structure on a body close — CONFIRMS

`wzq2AMsoJKY` @ 00:13:09: "We **close above this high** right here on the hourly
time frame." Frame `eq_A/f_004.png` shows the tall blue candle closing above the
prior high, not merely wicking through it.

He also draws the full sequence by hand on a blank chart, `eq_B/f_002.png` @
00:15:38:

> "I'm looking for price to push above a high, and then I'm going to be looking
> for a change in order flow or a change of structure, a break of structure. Then
> from there... I'm looking for price to show me a **continuation** of the new
> trend. So I've already labeled **two confluences that I need on top of the fact
> of equilibrium** in order to actually take a trade."

The drawing shows: rally into a horizontal line, a spike above it, a sharp
reversal down through the line. Sweep, then break, then continuation, with
equilibrium as a third requirement. That is the sequence we implemented.

### 3.3 Fair value gaps — REFINES

Frames `take_A/f_006.png` and `take_B/f_004.png` show the gaps he actually trades
into. They are small. The ES gap in `take_A/f_006.png` spans roughly 5,930 to
5,932 — about **two index points, 0.03% of price** — hand-drawn on the 1-minute.

If our gap detector carries any minimum size, or works off 5-minute bars for the
entry retrace, it is looking for something bigger than what he uses. Worth a
direct check against `tjr_bot.py`; I did not verify our threshold this round.

### 3.4 Two-candle swing — NOT CONFIRMED THIS ROUND

I did not find a frame where he counts candles to mark a swing point. His swing
highs and lows in every frame arrive as already-drawn horizontal lines, placed
before the session. Nothing here contradicts the two-candle definition; nothing
here supports it either. It stays where it was.

---

## 4. WHAT NOT TO DO WITH THIS

- **No code was changed.** Every proposal above is marked as a proposal.
- **The cleanliness metrics in section 2 are untested guesses.** The description
  of what the charts look like is solid; the arithmetic is not.
- **Do not build a macro-window filter.** His screen proves the window is real and
  proves our 09:50 is right. Our own 467 trades say entering inside it is
  slightly *worse*. Both things are true.
- **Prominent high / area of accumulation stay dead.** Nothing in any frame
  revived them, and nothing here should be read as doing so.

---

## 5. THE ONE THING WORTH ACTING ON

Everything above narrows to one sentence.

**He checks where the trade is going before he checks whether the setup is valid,
and we do the reverse.** Nine refusals, three sessions, and in every one the
complaint is that the destination has already been taken or is too close to be
worth the stop. Our `build_targets` already knows how to find that out and already
returns empty when the answer is "nowhere" — and then we open the position anyway.
43% of our S&P trades drift to the close for +0.62x what was risked, against
+1.57x for the ones that actually travelled.

The next round is a measurement: for every trade we took, how far was the nearest
unswept drawn level in units of the stop, and does refusing the thin ones move the
hit rate toward his 64%. That is a backtest, not a rewrite, and the plumbing to
run it already exists.
