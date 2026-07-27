# TJR spec: the confluences (candles, trend/order flow, fair value gaps, inverse fair value gaps, order blocks, equilibrium, index divergence)

**What this document is.** A transcription of what TJR teaches, in his own numbers, written so an engineer who has never watched a trading video can code it. No evaluation, no second-guessing, no backtesting. Where a rule depends on something only visible on his screen, it is marked **NEEDS VIDEO** with what is missing.

**Sources read in full for this document**

Newer series (recorded recently, all one series, each ends by announcing the next):
- `tjr_transcripts/Fair_Value_Gaps_Explained.txt` (= `p2p_fair_value_gaps.txt`, video xX5LTSJ5wwM)
- `tjr_transcripts/p2p_advanced_imbalance.txt` (video PlsHO33j6B8, the lesson that sits between the two below)
- `tjr_transcripts/Inverse_Fair_Value_Gaps_Explained.txt` (= `p2p_inverse_fvg.txt`, video 4sRDnVmLcMk)
- `tjr_transcripts/Equilibrium_Explained.txt` (= `p2p_equilibrium.txt`, video joe_XTCn5Bs)
- `tjr_transcripts/SMT_Divergence_Explained.txt` (= `p2p_smt_divergence.txt`, video 7dTQA0t8SH0)
- `tjr_transcripts/Order_Flow_Explained.txt`
- `tjr_transcripts/only_equilibrium_video.txt` (video wzq2AMsoJKY, standalone, most recent statement on equilibrium)

Bootcamp (3 years old, 56 days, more systematic):
- `bootcamp/Day02 Candlesticks`, `Day04 Trends`
- `bootcamp/Day14 FVG Pt.1`, `Day16 FVG Pt.2`, `Day18 FVG Pt.3`
- `bootcamp/Day20 Order Blocks`, `Day22 Order Blocks Pt.2`, `Day24 Order Blocks Pt.3`
- `bootcamp/Day26 Equilibrium`, `Day28 Equilibrium Pt.2`

**His own vocabulary, defined once.** He uses these words constantly; after this table this document uses the plain-English version.

| His word | What it means |
|---|---|
| fair value gap / imbalance / liquidity void | a three-candle price gap where one side had no orders (defined precisely below) |
| inverse fair value gap | one of those gaps that price closed straight through, against the trend |
| order block | the last push (up or down) before the trend flipped, the price range where orders got filled |
| equilibrium | the exact midpoint between the most recent swing low and swing high |
| premium | the half of that range above the midpoint, the expensive half |
| discount | the half below the midpoint, the cheap half |
| order flow | the trend, nothing more (his words: "it's literally just uptrends and downtrends") |
| break of structure | a candle closing beyond the most recent swing point, flipping the trend |
| draw on liquidity | a prior high or low that price is likely to travel to |
| confluence | one ingredient of the setup; he never trades on one alone |
| reversal confluence | the ingredient that says a turn is possible (liquidity sweep) |
| confirmation confluence | the ingredient that says the turn actually happened (break of structure, or a gap closed through) |
| continuation confluence | the ingredient that says the new trend will keep going (a gap being refilled, or the midpoint being touched) |
| SMT divergence | the difference in behaviour between two correlated markets (S&P 500 vs NASDAQ) |
| GAN box | his drawing tool for the midpoint; settings are levels 0, 0.5 and 1 only |

---

## 0. The frame everything hangs on

He classifies every ingredient into one of three roles, and states the order they must appear in. From the inverse-fair-value-gap and equilibrium videos, verbatim in structure:

1. **A prior high or low gets pushed through** (a liquidity sweep). This is the *opportunity* for a reversal. It only creates the opportunity: "price just has the opportunity to fill orders above highs and below lows. It doesn't mean that price has to."
2. **Confirmation that the turn happened.** Either a candle closes beyond the most recent swing point (break of structure), or a fair value gap gets closed through against the trend (inverse fair value gap). Those are the only two confirmation ingredients he teaches.
3. **Confirmation the new trend will continue.** Price retraces into a fair value gap, or into the midpoint of the new leg (equilibrium), and then moves back out of it. In the older bootcamp an order block also counts here.
4. **Target**: a previous high or low on the other side (a draw on liquidity), or a fair value gap, or in the bootcamp an order block.

He repeats a hard prohibition throughout: **no ingredient is tradeable on its own.** "We are unable to take trades on just a break of structure, on just price pushing above a high, on just price pushing below a low." And on equilibrium specifically: "I'm not the type of person to enter purely off equilibrium."

---

## 1. How he reads candles (bootcamp Day 2)

### 1.1 Mechanics
- A candle covers exactly one period of the chart's timeframe. On a 5-minute chart, one candle is 5 minutes of price movement.
- Body = from open to close. Green/up candle: open at the bottom of the body, close at the top. Red/down candle: open at the top, close at the bottom.
- Upper wick = the highest price reached during that period. Lower wick = the lowest price reached. A wick marks where price went but did not stay.

### 1.2 What he refuses to use
He rejects every multi-candle chart pattern by name: head and shoulders, double top, double bottom, W patterns, "mountain tops". "I really hate every single candlestick pattern that contains more than two candles." Reason given: those patterns do not tell you why price is moving.

He accepts only single-candle shapes, and names exactly this set: **doji, long-legged doji (same thing as a doji in his words), cross doji, inverse cross doji, dragonfly doji, hammer.** Everything else on a standard cheat sheet is discarded.

### 1.3 What the shapes mean to him
- **Long wick, small close in the same direction**: strength that was not strong enough. Example given: price pushed all the way up, closed well below the high, "it was not strong enough to close above whatever was residing above here, and more than likely it was taking this liquidity."
- **Small body, long wicks (doji)**: indecision. After a sustained move, a doji shows exhaustion.
- **Full body with a tiny wick on the far side**: strong conviction. His example: opens low, drops further, rallies and closes near the high with a massive lower wick and a tiny upper wick. "That candle is telling you exactly where price wants to go."
- **Losing momentum**: a long wick in the trend direction that fails to produce a full-bodied close in that direction.

### 1.4 The rules inside this section
- **Never take a trade off a candle shape alone.** "This is why we cannot be taking trades purely off of candlestick patterns, this is only one confluence."
- **Only closed candles count.** "We can only make bias and decision on candles that have formed, not candles that are forming. That's why we always wait for a close for a break of structure."

### 1.5 Where it applies
Any market, any timeframe. His examples in this lesson are on the S&P 500 5-minute and on gold daily and weekly.

---

## 2. Trend, which he also calls order flow (bootcamp Day 4 + Order Flow Explained)

### 2.1 Definition
- **Uptrend / bullish order flow**: higher highs and higher lows.
- **Downtrend / bearish order flow**: lower highs and lower lows.
- **Third state: consolidation.** He states explicitly there are three types, not two: "uptrend, downtrend, consolidation." Consolidation is when a higher high and higher low appear but price does not continue, it just goes sideways.

How to identify it: "just look at the most recent break of structure, or just look at the most recent highs and lows."

### 2.2 The three ways a trend is broken (Order Flow Explained, stated as a list)
He calls this "disrespecting order flow." Three ways, in his order:
1. **Break of structure.** In an uptrend: find the most recent low, require a candle to *close* below it. In a downtrend: find the most recent high, require a candle to *close* above it.
2. **Inverse fair value gap.** A bullish gap that gets closed below (in an uptrend), or a bearish gap that gets closed above (in a downtrend). Full definition in section 5.
3. **The 79% extension on the Fibonacci.** Drawn "just like we were to draw out equilibrium." If price moves past the 79% level, he treats the trend as disrespected and expects a break of structure or a gap inversion to follow. He adds: "I rarely use this one, you guys can very well do without this."

### 2.3 The ways a trend is confirmed to be continuing
"Respecting order flow": price fills a fair value gap, touches the midpoint (equilibrium), fills an order block, or fills a breaker block, and then continues in the trend direction. (Breaker block is named here but is not defined anywhere in this cluster. See ambiguities.)

### 2.4 His actual trade logic in one sentence
Verbatim: "I look for the previous order flow to get disrespected, then I look for new order flow to get respected."

### 2.5 WHERE IT APPLIES: the timeframes he names out loud

This is the most specific timeframe statement in the whole cluster (Order Flow Explained):

- **5-minute is the decision timeframe.** "I'm mainly looking at the 5-minute timeframe. 5-minute order flow for the most part dictates like everything for me in terms of where I'm looking to trade, in terms of where I'm entering."
- **1-minute is the entry timeframe.** "Then I scale down to the 1-minute timeframe to look for an entry."
- **The 1-minute usually flips against you first.** "A 5-minute retrace typically makes the 1-minute order flow turn into the other direction." So when the 5-minute is bullish and pulling back, the 1-minute is usually bearish during the pullback.
- **The entry trigger on the 1-minute**: a break of structure or a gap inversion in the direction of the 5-minute trend, taken at a 5-minute ingredient (gap, midpoint, order block, breaker block). Once that happens he does **not** wait for a 1-minute gap or 1-minute midpoint: "I'm not looking for order flow to get respected on the 1-minute timeframe... I'm okay taking that trade without needing to wait for a 1-minute fair value gap or a 1-minute equilibrium."
- **4-hour and daily are for direction only.** The job on those is to locate where in the trend you are: has the extension already happened (so the next move is a pullback into a 4-hour gap / midpoint / order block), or has the pullback already happened (so the next move is the extension that takes out the prior high).
- **Targets come from the higher timeframe highs and lows.** "Now what can we use these highs as? Take profits."
- **Timing within the day**: he does not trade the first five minutes of the open. In his walkthrough the market opens, breaks 5-minute structure down within 5 minutes, and he says "that's like 5 minutes into market open, we obviously want to wait for market to move into the macro, move into an optimal time to trade, when this happens at around 9:50." Bootcamp Day 18 states the same rule harder: "we're not going to take any trades that aren't off of market open." (Session and time-of-day rules belong to the execution agent; noted here only because he says them inside these lessons.)

### 2.6 What he warns against on trend
- **Higher timeframes outrank lower ones.** "If the 4-hour is saying we're bearish and the 15-minute just broke structure, why do we care what the 15-minute is saying?" Use the lower timeframe only to get a better entry into the higher timeframe's direction.
- **Never trade against the trend.** "Going against the trend is never smart." He names this as his own biggest personal weakness.
- **Do not trade the tiny counter-moves.** "I could go on the 1-minute timeframe and find a million liquidity sweeps and breaks of structure... some of you guys are entering off of these little ticky tack things."
- Note for the direction of moves: in a downtrend the up moves are always smaller than the down moves, and vice versa.
- Practical tip he gives: switch to a line chart to see the trend without candle noise.

---

## 3. Fair value gaps (the imbalance)

### 3.1 The definition, mechanically
A **three consecutive candle** relationship. Call them candle 1, candle 2 (the middle, "expansionary" candle) and candle 3.

**Bullish fair value gap**
- Condition: `low of candle 3 > high of candle 1`. In his words: "a gap between the first candle's top wick and the third candle's bottom wick."
- Middle candle is the one that pushed price up fast.
- Meaning he assigns: there were no sell orders inside that gap.

**Bearish fair value gap**
- Condition: `high of candle 3 < low of candle 1`. In his words: "from the bottom wick of the first candle and the top wick of the third candle."
- Middle candle is the one that pushed price down fast.
- Meaning he assigns: there were no buy orders inside that gap.

**Colours.** The colours of candle 1 and candle 3 are irrelevant. He says it four separate ways, including "fair value gaps, we do not see colour, we are not racist, we do not care what colour the first or the third candlesticks are." He does say the middle candle's colour matters: "really the only candlestick colour that matters is the one in the middle." For a bullish gap the middle candle is the big up candle, for a bearish gap the big down candle. Note that the geometric condition already forces this in practice.

**What is NOT a gap.** If the wicks overlap, there is no gap: "because the wicks are overlapping, meaning there was enough buy orders down here to push price back up... this is not an imbalance of price action." A bullish setup where candle 3's lower wick reaches down past candle 1's high is not a gap.

### 3.2 How it is drawn, and where its boundaries are
- Bullish gap: **bottom = high of candle 1**, **top = low of candle 3**. Draw a box between those two prices, extended to the right.
- Bearish gap: **top = low of candle 1**, **bottom = high of candle 3**.
- He does not use a midpoint of the gap for entries in these lessons. He mentions "50% of the imbalance" once, only as a possible take-profit level (bootcamp Day 18). No rule attached.

### 3.3 When it is VALID and when it is DEAD

**Alive**: from the moment candle 3 closes, until one of the two kill conditions below.

**Kill condition 1: a candle closes through it.**
- A bullish gap dies when a candle **closes below the bottom of the gap** (below candle 1's high).
- A bearish gap dies when a candle **closes above the top of the gap** (above candle 3's... no: above the top, which is candle 1's low).
- **A wick through is not enough.** Explicit: "if we see a candlestick wick that goes all the way down here but we still do not close underneath the gap, it has not been disrespected yet." And: "it's just like break of structure where we need to see a candlestick closure underneath this line in order for the gap to be invalidated."
- When this happens the gap is not merely dead, it becomes the opposite signal. See section 5.

**Kill condition 2: price continued the trend without needing the gap.**
- In an uptrend: price retraces, does *not* reach the gap, then closes above the prior swing high. The gap is deleted. "Price does not have any obligation to us or the chart to have to fill this gap... we can get rid of it from my chart."
- In a downtrend: price retraces up, does not reach the gap, then closes below the prior swing low. Delete it.
- Same rule after a gap IS used: once price has tapped the gap and then broken the prior high (uptrend) or low (downtrend), remove that gap **and every gap below it in the stack**.

**Kill condition 3, implicit: the gap has been filled and the move continued.** He treats a filled gap as spent. "Once we push above the high in a bullish scenario, then we no longer need to have these fair value gaps on our chart."

**They are never dragged forward in time.** This is one of his loudest warnings. "You're not going to drag it all the way over and say, yeah, this is going to be valid somewhere over here in like 3 years." His stated failure mode: a trader leaves a dead gap on the chart, sees price come back to it months later, shorts it, and gets stopped out, "when that's the stupidest thing ever."

**They are not required to be filled.** Stated directly in the advanced imbalance lesson: "fair value gaps are not required to get filled." They are not a target that price owes you.

### 3.4 Stacked gaps (gaps on top of each other)
This is a full sub-rule set, taught twice.

**Grouping test**: consecutive gaps count as one group when there is **no retracement between them**. His two phrasings: "with no form of a retrace in between these fair value gaps that are stacked up. So no down candles" and "there's no black candle in between it."

**While the group is alive:**
- **All of them are valid.** Price may tap any one of them and move on.
- Treat the whole span, from the bottom of the lowest gap to the top of the highest, as one imbalanced range.
- If price fills the top gap and moves on, the lower ones did not need to be filled.
- If price closes below the top gap, that alone means nothing, because the lower gaps can still support the trend.

**Which one kills the trend**: **the bottom gap of a bullish stack** (for a downside inversion), **the top gap of a bearish stack** (for an upside inversion). Verbatim: "the bottom fair value gap when we have multiple fair value gaps stacked up on top of each other needs to be inversed... because this is the last fair value gap that is holding up the trend."

**Clean-up**: once price taps into the group and then closes beyond the prior swing high (uptrend) or low (downtrend), delete the entire group from the chart.

### 3.5 WHERE IT APPLIES
- Any market, any timeframe. He is emphatic and repeats it: "you can trade this on any timeframe, you can trade this with any pair, you can literally apply these concepts to every financial market."
- Chart examples in these lessons: hourly, 4-hour, 15-minute, 5-minute, daily.
- His own working combination, from the lessons: mark the gap on the 15-minute or 5-minute, scale to the 1-minute or 5-minute for the entry trigger. Bootcamp Day 18 walks a live trade: 15-minute break of structure, 5-minute gap filled at the open, 1-minute break of structure = entry.

### 3.6 How it is USED
- **Primary role: a continuation ingredient and a retracement map.** "Fair value gaps are used for retracements. I don't use fair value gaps for entries necessarily... I use it more as a confirmation rather than an entry."
- **Never enter on the fill alone.** "The issue that I have with this is when people execute purely off just the fair value gap getting hit and without a reaction. Wait for a reaction, or scale down to a lower timeframe, see a break of structure."
- **Not a reversal tool.** "Fair value gaps are not used for reversals." In an uptrend you look for *bullish* gaps to hold, you do not look for bearish gaps to turn price around.
- **Can be a target.** He names the start of the gap, the 50% of the gap, or the end of the gap as possible take-profit levels (bootcamp Day 18).
- **Required partners**: a prior high or low taken out, plus a confirmation (break of structure or gap inversion), before the gap matters. And a lower-timeframe trigger inside the gap before entering.

### 3.7 What he warns against on gaps
- Leaving used or dead gaps on the chart. (His single most repeated gap warning.)
- Entering the moment price touches a gap, with no reaction and no lower-timeframe trigger.
- Believing a rally into an old zone was "filling the gap" when that range was already balanced earlier. His example: the move up was for the sweep of the highs, not for the gap.
- Using a bearish gap to try to reverse an uptrend.
- Getting caught in the number of gaps on the chart: "you can find these literally everywhere on charts... not all of them are going to work."

---

## 4. The other imbalances he teaches (advanced imbalance lesson)

Included because it is the same concept family and sits between his gap and gap-inversion lessons. He rates their usefulness himself, and the ratings are part of the spec.

### 4.1 New day opening gap
- **Definition**: the gap between the previous day's closing price and the new day's opening price, created by the ~1 hour the market is not trading.
- **Boundaries**: previous day close to new day open.
- **Behaviour he assigns**: price actively seeks it out to fill it, then continues in its intended direction. "Price more often than not has a very high probability of actively wanting to seek out these gaps."
- **Not required to be filled.** He says this explicitly.
- **Use**: as a target, or as an entry area.
- **His rating**: usable but rare, and it usually fills during the Asian session, which he does not trade.

### 4.2 New week opening gap
- **Definition**: same thing between Friday's close and Sunday's open, spanning two days of no trading.
- **His rating**: the most useful of the three, because the gaps are bigger, and because if it has not filled by Monday's open it becomes a good target for the week.

### 4.3 New candle opening gap
- **Definition**: a gap between one candle's close and the next candle's open on any timeframe.
- **His rating, verbatim**: "to keep it a buck, it's useless." He teaches it only for completeness. Do not build on it.

### 4.4 BPR (a swift move up and a swift move back down through the same range)
- **Definition**: a price range that price ripped through in one direction, then ripped back through in the other. He treats the whole overlapping span as one illiquid range.
- **Behaviour he assigns**: the instant price re-enters that range, it travels through it just as fast as it originally moved, all the way to the far side. Then it continues in the direction it was going.
- **Use**: as a target ("once we enter back into this range we are going to move very swiftly to the bottom of the range"), or as an entry with a continuation out the other side.
- He states he took a real NASDAQ short on this (Tuesday, 10:41) on the basis that price entering an illiquid range would travel all the way through it.
- **NEEDS VIDEO**: he never gives a numeric definition of "swift" or "rapid", and never states how far the two moves must overlap for the range to qualify. Everything is done by eye on the chart.

---

## 5. Inverse fair value gaps (a gap that gets closed through)

### 5.1 Definition, mechanically
A fair value gap that price closes straight through, in the direction opposite to the trend the gap was supposed to support.

- **Bearish signal**: in an uptrend, a **bullish** gap gets a candle **close below the bottom of the gap** (below candle 1's high).
- **Bullish signal**: in a downtrend, a **bearish** gap gets a candle **close above the top of the gap** (above candle 1's low).

The logic he gives: a fair value gap is a continuation ingredient; price entering it should push the trend onward. If instead price closes clean through it, the trend itself has been disrespected.

### 5.2 Validity rules
- **A full candle close is required.** "Even though we pushed a wick above this fair value gap, it is not an inverse fair value gap until we get a full candlestick closure above the gap. Just like with break of structure, we need to wait for a full candlestick closure."
- **On a stack of gaps, only the last gap counts.** For a downside signal in an uptrend, the close must be below the **bottom** gap of the stack. Closing below any higher gap in the stack "doesn't mean anything, because we can still come down and fill this gap to push price higher."
- The mirror applies for an upside signal in a downtrend: the close must be above the **top** gap of a bearish stack.

### 5.3 How it is USED
- **It is a confirmation ingredient, interchangeable with a break of structure.** He has exactly two confirmation ingredients: break of structure, and this.
- **Its whole value is that it fires earlier.** "More often than not it happens before break of structure even does." He quantifies the benefit twice with real numbers from the chart:
  - Example A: entering on the gap inversion instead of waiting for the break of structure saved 68 ticks, and turned a reward-to-risk of under 1:0.5 into 1:1.3 and 1:2. He spells the money out: "if I'm risking $1,000 I'll only be able to make $450... versus if I take this trade up here, if I'm risking $1,000 I'll be able to make $1,300."
  - Example B: 123 ticks saved on a different setup.
  - Also stated: waiting for the break of structure instead "makes my stop loss literally two times the size."
- **Frequency claim**: "I use this confluence almost every single day, almost more than break of structure."
- **Cannot be traded alone.** "We can't just be taking sell positions on inverse fair value gaps to the downside and taking buy positions to the upside willy-nilly."

### 5.4 WHERE IT APPLIES
- Chart examples in the lesson: 4-hour, hourly. In Order Flow Explained it is one of the three trend-break tests applied on the 5-minute and 1-minute as well. Any timeframe.

### 5.5 Sequence he shows after the inversion
Once a bearish gap has been closed above (bullish signal), price then comes back down, fills the gaps created on the way up, and moves higher each time. He walks it: "we see price come down, fill this gap and then move higher, come down, fill this gap, move higher, come down, fill this gap, move higher."

---

## 6. Order blocks (bootcamp Days 20, 22, 24)

**Read the retirement note in 6.7 before building this.** It matters.

### 6.1 Definition, mechanically
An order block is **the entire leg of price movement immediately before the break of structure, the leg that caused the liquidity sweep.**

- Uptrend flipping to a downtrend: the **leg up** that pushed above the prior high, taken as a whole, ending where the downside break of structure begins.
- Downtrend flipping to an uptrend: the **leg down** that pushed below the prior low, ending where the upside break of structure begins.

His phrasings, both used: "it is the move prior to the liquidity sweep, or the move that causes the liquidity sweep, and prior to the break of structure" and "it's the leg up or the leg down prior to the break of structure."

**One per trend.** "There's only one order block within a whole trend." A new one is only created when the trend flips again. There can be one on each timeframe simultaneously.

### 6.2 How it is drawn, and where its boundaries are
He gives two ways and recommends the first for anyone still learning:

1. **The whole leg.** Box the entire move from its start to the extreme it reached. "This is probably going to be your best bet. There's no reason to get advanced with it, just box off the entire thing." He tells beginners explicitly to use this: "if I'm you guys I'm marking out the entire leg down prior to the move up."
2. **His own version: the wick zone of the single candle.** "I literally just do it off the wick of the candle. I just box off the wick... from the wick down to the start of the body." So the box runs from the candle's extreme (the wick tip) to where the body begins (the open or close on that side).

Why he uses version 2: "oftentimes it'll tap into just the wick area and then respond, or it'll tap just the base... touch the base of the body, right where the body starts, usually that's like the reaction point. I don't know why, it's just a common theme, this is just market experience me talking."

**NEEDS VIDEO**: where a multi-candle "leg" starts is decided visually on his chart every time. There is no stated rule for the first candle of the leg.

### 6.3 When it is VALID and when it is DEAD
- Created at the moment of the break of structure that follows the sweep.
- Replaced when the next trend flip creates a new one.
- He never states an explicit kill condition for an order block. He does show price trading through them without reacting and shrugs: "sometimes it's just not going to hit, it's going to fill off of other things and other reasons, and that's something you just have to be okay with." **NEEDS VIDEO** for whether a close beyond an order block invalidates it.

### 6.4 WHERE IT APPLIES
- Every timeframe: 1-minute up to daily and monthly, and he shows daily, 4-hour, hourly and 15-minute examples in the same walkthrough.
- Instruments in these lessons: S&P 500, gold, GBP/USD, GBP/JPY.

### 6.5 How it is USED
- **First choice for a re-entry after missing the initial move.** He ranks the retracement tools explicitly: **order block first, then fair value gap, then equilibrium.** Reason given: "it's still at the top of the move and oftentimes you can get even a better entry than off of just the liquidity sweep and the break of structure."
- **Also usable as a take-profit target.** "I sometimes use order blocks as take profit."
- **Requires a lower-timeframe trigger inside it.** Every worked example: price enters the order block, then he waits for a break of structure on a lower timeframe, then enters.
- **Match your stop to the timeframe of the leg.** This is a stated rule with a warning attached: a 4-hour order block is a 4-hour move, so "what makes you think that when you just see a break of structure on the hourly time frame off of this, you can keep your stop loss super tight? You're going to get stopped out. Understand what timeframe you're playing off of."
- Stops in his examples go above/below the order block itself, or above/below the lower-timeframe swing inside it. Targets are previous highs and lows.

### 6.6 What he warns against
- Trading the order block on a stop sized for the wrong timeframe (above).
- Trying to be precise before you are competent: "don't try to be a pro at something that you suck at. If you're playing basketball and you can't even make a layup, why are you shooting threes?" That is his argument for using the whole-leg box rather than his wick box.

### 6.7 The direct contradiction between the two eras. FLAGGED.
The bootcamp (3 years old) teaches order blocks as the **first** retracement choice, ahead of gaps and equilibrium, across three full days.

The recent standalone equilibrium video says the opposite, verbatim:

> "I no longer use order blocks. I no longer use breaker blocks. The only continuation confluences that I need and that I use are equilibrium and fair value gaps because simplicity is key."

with the reasoning and a test he assigns:

> "Whenever you see a potential order block or breaker block entry, go ahead and mark out equilibrium and let me know if equilibrium gets filled when that order block or breaker block is getting hit. More often than not, equilibrium is getting filled, which pretty much renders order blocks and breaker blocks completely useless."

Note that the *other* recent video, Order Flow Explained, still lists order blocks and breaker blocks among the things that show a trend being respected, and he draws a 4-hour order block on the chart there ("4-hour order block literally right at equilibrium"), which is itself an instance of the overlap he describes. Both statements are his. The newest, most explicit statement is the retirement.

---

## 7. Equilibrium (the midpoint)

He is angriest about this one and repeats the measurement more times than any other rule in the cluster, because students anchor it wrong.

### 7.1 The exact measurement
- **In an uptrend**: measure from the **most recent swing low** up to the **most recent swing high**. Equilibrium is the **50% point** of that distance.
- **In a downtrend**: measure from the **most recent swing high** down to the **most recent swing low**. Equilibrium is the 50% point.

**Most recent, not any earlier swing.** This is the entire point of his rant. "If there's a low right here that's connected to this high, do we draw equilibrium from this low up to this high? No. We draw it from the most recent low up to the most recent high." And from the newer video, with an extra case: drawing from a low that has two more lows in front of it is wrong, "because there's two more lows in front of it."

### 7.2 What the midpoint means
- **Above the midpoint = premium**, the expensive half.
- **Below the midpoint = discount**, the cheap half.
- **You buy in the discount and you sell short in the premium.** In an uptrend you want price to fall below the midpoint before buying. In a downtrend you want price to rally above the midpoint before shorting. His grocery analogy: nobody buys the $10 bag of Doritos when the normal price is $5.
- The wording flips confusingly in one bootcamp passage where he calls the shorting zone "a discount to go short". The operative rule, stated consistently everywhere else and in both recent videos, is: **buy below the midpoint, short above it.**
- He frames it as what the market makers do: "are they going to be looking to top blast their own positions up here and take longs right there? No."

### 7.3 When it can be drawn, and when it is redrawn
- You can place it as soon as the new swing extreme is in. His live walkthrough: in a downtrend, once the most recent high is in and the retracement has started (he waits for the opposite-colour candle to appear), he anchors high-to-low and watches.
- **If price never reaches the midpoint and instead makes a new extreme, re-anchor to the new most recent swing.** He demonstrates this repeatedly: "does this get hit? No. Okay, we've got to go higher, all the way up here. Boom, price finally comes down low enough."

### 7.4 When it counts as reached
- **Touching or poking past the 50% level counts.** His examples: "we come down, poke our head underneath the discounted price range", "we poke our head just barely underneath", "price barely taps equilibrium, rallies higher". Two of his shown examples are literally price stopping at or a tick past the level.
- **NEEDS VIDEO**: he never says whether a wick past the midpoint is enough or whether a body must close past it. His language ("poke our head") and his chart examples suggest the wick suffices, but he never states it as a rule.

### 7.5 WHERE IT APPLIES
- Every timeframe, and he shows it on more timeframes than any other ingredient: weekly, monthly, daily, 4-hour, hourly, 15-minute. "It happens on literally every single timeframe."
- Both for high-timeframe direction and for low-timeframe execution: "I frequently use equilibrium not only on the high timeframes but also on the low timeframes to look for execution."
- Instruments shown: S&P 500, NASDAQ, gold, GBP pairs.

### 7.6 How it is USED
- **A continuation ingredient and a retracement map.** It tells you where a pullback is likely to end.
- **Never on its own.** "I'm not the type of person to enter purely off equilibrium." And: "these confluences are literally nothing without context."
- **Best paired with a gap.** "We can pair it together with a fair value gap, which is honestly the perfect tools to combine for a retracement. If you can find a fair value gap that's within a discounted price and then you get a reaction, let's enter."
- **Then scale down for the trigger.** "We can scale down to a lower timeframe and we can see a change in order flow on that, whether it's a break of structure or an inverse fair value gap. And then boom, that's a prime time spot for us to enter."
- Full sequence he states around it: a prior high or low gets taken out, then a break of structure confirms, then price retraces into the premium (for a short) or discount (for a long), then a lower-timeframe trigger, then target the opposite side's prior high or low.

### 7.7 Tool settings he gives out
He uses TradingView's GAN box with **only the levels 0, 0.5 and 1 enabled** (everything else turned off). A Fibonacci retracement tool with only the 0.5 level shown is equivalent, and he says so: the reason people love the 50% and 62% Fibonacci retracement levels "is because it's equilibrium, they're just too stupid to realise that."

### 7.8 What he warns against
- Anchoring to anything except the most recent swing low and most recent swing high. This is the whole rant.
- Buying in the premium, shorting in the discount.
- Entering on the midpoint alone.

---

## 8. Divergence between two correlated markets (his "SMT divergence")

### 8.1 Instruments
**S&P 500 (he trades ES) and NASDAQ.** Stated at the top: "for the Forex and Commodities people, unfortunately this is not going to be as beneficial for you guys, because this is specifically talking about the divergence between the S&P 500 and the NASDAQ."

He does not know what the acronym stands for and says so.

### 8.2 Definition, mechanically
Compare the two charts side by side over the same time window, at the same swing points.

**Bearish divergence** (bearish for BOTH markets):
- One index makes a high, then a **lower** high.
- The other index, over the same two moments, makes a high, then a **higher** high (usually pushing past a notable prior high).
- Either index can be the one making the lower high.

**Bullish divergence** (bullish for BOTH markets):
- One index makes a low, then a **higher** low.
- The other, over the same two moments, makes a low, then a **lower** low.

### 8.3 The condition that makes it valid
**It only counts when it happens while a significant prior high or low is being taken out.** Stated twice as a limiter: "SMT divergences are very powerful when used when sweeping out draws on liquidity. However, outside of sweeping out draws on liquidity, these things will show up all the time and will be pretty much useless to us."

### 8.4 Which one to trade
**Trade the leading index, not the lagging one.**
- Bearish divergence: the leading index is the one making the **lower** high, the one already turning down. "I'm not going to want to take a short position on the bullish index, which is NASDAQ, because it pushed above this high. I want to take it on the S&P 500, the one that is leading the move to the downside."
- Bullish divergence: the leading index is the one making the **higher** low.

His stated reason for the leading index in the bullish example: it expanded further and faster afterwards, past highs the lagging index never reached.

### 8.5 How it is USED
- **Primarily for direction/bias, especially on higher timeframes.** "This is really going to be used for bias, especially on the high timeframes."
- **Also usable on low timeframes as one ingredient of an entry**, and he shows a 5-minute example, while noting his full setup was not present there.
- **It can fire before a break of structure or a gap inversion**, which is its value: "that will help us dictate whether or not the trend is going to change before even being able to see a break of structure or an inverse fair value gap."

### 8.6 WHERE IT APPLIES
- Chart examples: 4-hour and 5-minute, and he mentions daily and hourly. Any timeframe.
- Only for correlated pairs. He splits the screen to compare.
- He explicitly notes the two indices "are not going to perfectly align with each other and be perfectly correlated 24/7, 365", which is why the liquidity-sweep condition exists.

---

## 9. What he requires TOGETHER versus what stands alone

**Nothing stands alone.** He states this in four separate lessons. The full sentence from the fair value gap lesson: "we are unable to take trades on just a break of structure to the upside, on just a break of structure to the downside, on just price pushing above a high, on just price pushing below a low. We are slowly but surely learning all of the confluences that we need in order to put them all together."

His assembled sequence, stated identically in the inverse-gap, equilibrium and order-flow lessons:

| Step | Role | Ingredients that satisfy it |
|---|---|---|
| 1 | Opportunity for a turn | a prior high or low gets pushed through (liquidity sweep). Optionally reinforced by a divergence between the two indices at that same moment |
| 2 | Confirmation the turn happened | break of structure **or** a fair value gap closed through (either one, whichever fires first, and the gap usually fires first) |
| 3 | Confirmation the new trend continues | price retraces into a fair value gap **or** past the midpoint of the new leg (equilibrium). In the bootcamp era, an order block also qualifies and was ranked first |
| 4 | Trigger | a break of structure on a lower timeframe, inside the step-3 area |
| 5 | Target | a previous high or low in the trade's direction. Also: a fair value gap, the 50% of a gap, an order block, or the far side of a fast-move range (BPR) |

The order-flow lesson compresses all of it to: "I look for the previous order flow to get disrespected, then I look for new order flow to get respected."

---

## 10. Everything he tells you NOT to do (these are rules too)

1. Do not trade any single ingredient alone. Repeated in five lessons.
2. Do not act on a candle that has not closed. Bias comes only from closed candles.
3. Do not trade multi-candle chart patterns (head and shoulders, double tops, W's, mountain tops). He calls them worthless.
4. Do not leave used or dead fair value gaps on the chart, and never drag one forward in time to a later part of the chart.
5. Do not treat a wick through a gap, or through a structure level, as a break. Wait for the close.
6. Do not call it a gap when the outer wicks overlap.
7. Do not enter the instant a gap or midpoint is touched. Wait for the reaction or the lower-timeframe break.
8. Do not anchor the midpoint to anything but the most recent swing low and most recent swing high.
9. Do not buy in the premium half or short in the discount half.
10. Do not use a bearish gap to try to reverse an uptrend. Gaps are continuation, not reversal.
11. Do not fight the higher timeframe with a lower-timeframe signal.
12. Do not enter off tiny 1-minute sweeps and structure breaks with no higher-timeframe context.
13. Do not use a tight stop on a setup whose leg belongs to a higher timeframe.
14. Do not read a divergence between the two indices unless a significant prior high or low is being taken out at that moment.
15. Do not take the divergence trade on the lagging index.
16. Do not trade the first five minutes of the open; wait for the proper window (he cites around 9:50 in his example).
17. Do not trade on heavy news days. He shows a day with PPI and an FOMC meeting where GBP/JPY, "an extremely volatile pair", moved 34 pips in the whole US session, as the argument.
18. Do not build on new-candle opening gaps. He calls them useless himself.
19. Do not treat gaps as something price owes you. They are not required to be filled.

---

## 11. The bar-by-bar checklist a bot would run

Notation: `H[i]`, `L[i]`, `O[i]`, `C[i]` are the high, low, open and close of the candle `i` bars ago, `i=0` being the just-closed candle. Every rule runs on candle **close** only.

### 11.1 Candle classification (feeds everything else, no trades of its own)
```
inputs: O, H, L, C for the closed candle
body      = |C - O|
range     = H - L
upperWick = H - max(O,C)
lowerWick = min(O,C) - L
classify:
  if range == 0                      -> flat, ignore
  if body <= small_fraction * range  -> DOJI (indecision)          [threshold NOT stated by him]
  if body >= large_fraction * range  -> STRONG CLOSE (conviction)  [threshold NOT stated by him]
  if lowerWick >= k * body           -> rejection from below       [k NOT stated]
  if upperWick >= k * body           -> rejection from above       [k NOT stated]
never emits a trade signal on its own.
```

### 11.2 Trend state (order flow) per timeframe
```
maintain, per timeframe: lastSwingHigh, lastSwingLow, trend in {UP, DOWN, CONSOLIDATION}
on each closed candle:
  if trend == UP  and C[0] < lastSwingLow   -> trend = DOWN, emit BREAK_OF_STRUCTURE(down)
  if trend == DOWN and C[0] > lastSwingHigh -> trend = UP,   emit BREAK_OF_STRUCTURE(up)
  update swings when a new high/low is confirmed  [swing confirmation rule NOT stated: see 12.1]
  UP   is also confirmed by the pattern: higher high AND higher low
  DOWN is also confirmed by the pattern: lower high AND lower low
  CONSOLIDATION: a higher high and higher low occurred but price did not extend
                 [no numeric definition given: see 12.2]
```
Additional trend-break tests, both equivalent to a break of structure:
```
  gap inversion (11.4)
  price passing the 79% level of the current leg  [anchor unclear: see 12.7]
```

### 11.3 Fair value gap: detect, maintain, retire
```
DETECT (runs on the close of every candle, using the last three closed candles c1=[2], c2=[1], c3=[0]):
  if L[0] > H[2]:
      create BULLISH_GAP { bottom = H[2], top = L[0], created_at = t }
  if H[0] < L[2]:
      create BEARISH_GAP { top = L[2], bottom = H[0], created_at = t }
  (colours of c1 and c3 are ignored; c2 is the expansion candle and its direction
   is already implied by the geometry)

GROUP INTO STACKS:
  a newly created gap joins the previous gap's stack if there was no retracement
  between them, i.e. no opposite-direction candle between the two gaps
  [exact test = "no black candle in between": see 12.5]
  stack.bottomGap = the lowest bullish gap / stack.topGap = the highest bearish gap

MAINTAIN, each closed candle, for every live gap:
  # touched
  if BULLISH_GAP and L[0] <= top      -> mark touched
  if BEARISH_GAP and H[0] >= bottom   -> mark touched

  # killed by a close through it -> this is the inversion signal
  if BULLISH_GAP and C[0] < bottom    -> kill; if it is stack.bottomGap, emit INVERSE_GAP(bearish)
  if BEARISH_GAP and C[0] > top       -> kill; if it is stack.topGap,    emit INVERSE_GAP(bullish)
  # a wick through with no close through does NOTHING

  # killed by the trend continuing without it
  if trend == UP   and C[0] > priorSwingHigh -> kill every live bullish gap below priorSwingHigh
  if trend == DOWN and C[0] < priorSwingLow  -> kill every live bearish gap above priorSwingLow
  (this covers both the "used" case and the "never needed" case; he treats them identically)

  # gaps are NEVER extended into a later regime and NEVER revived
USE:
  a live, untouched gap in the direction of the current trend is a valid
  step-3 continuation area. Entry requires a lower-timeframe trigger inside it (11.7).
  a live gap may also be registered as a take-profit level (its near edge, its
  midpoint, or its far edge).
```

### 11.4 Gap inversion signal (emitted above; consumed here)
```
INVERSE_GAP(bearish) fires when, inside an uptrend, a candle CLOSES below the bottom
  of the lowest live bullish gap of the active stack.
INVERSE_GAP(bullish) fires when, inside a downtrend, a candle CLOSES above the top
  of the highest live bearish gap of the active stack.
Effect: identical to a break of structure. Flip the trend state, mark step 2 satisfied.
Wick-only penetration: no effect, no state change.
```

### 11.5 Order block (bootcamp era; see the retirement note)
```
ON every BREAK_OF_STRUCTURE:
  look back to the leg immediately before the break:
    down-break: the last leg UP, which should have taken out a prior high
    up-break:   the last leg DOWN, which should have taken out a prior low
  require that leg to have swept a prior high (for a down-break) or low (for an up-break)
  record ONE order block for this trend:
     wide  box = [leg start price, leg extreme price]                    (recommended)
     tight box = [extreme wick tip, the body edge on that side of the
                  extreme candle]                                        (his own version)
  discard the previous trend's order block: only one is live per trend per timeframe.
USE:
  first-choice retracement area when the initial entry was missed
  entry requires a lower-timeframe trigger inside the box (11.7)
  stop must be sized to the timeframe of the leg, not the trigger timeframe
  may also be registered as a take-profit level
NO invalidation rule is stated. [see 12.9]
```

### 11.6 Equilibrium (midpoint)
```
maintain per timeframe:
  if trend == UP:
     anchorLow  = most recent swing low
     anchorHigh = most recent swing high (must be later than anchorLow)
     eq = (anchorLow + anchorHigh) / 2
     discount zone = [anchorLow, eq)      -> the only place to buy
     premium  zone = (eq, anchorHigh]     -> do not buy here
  if trend == DOWN:
     anchorHigh = most recent swing high
     anchorLow  = most recent swing low (must be later than anchorHigh)
     eq = (anchorHigh + anchorLow) / 2
     premium  zone = (eq, anchorHigh]     -> the only place to short
     discount zone = [anchorLow, eq)      -> do not short here
RE-ANCHOR: whenever a new most-recent swing extreme forms, recompute immediately.
           never keep an older anchor pair.
REACHED:   uptrend  -> L[0] <= eq
           downtrend-> H[0] >= eq
           (touch/wick treated as sufficient; see 12.8)
USE:       step-3 continuation area, never an entry on its own.
           strongest when it overlaps a live fair value gap in the same direction.
           entry requires a lower-timeframe trigger (11.7).
```

### 11.7 The lower-timeframe trigger (what actually fires the entry)
```
preconditions, all on the decision timeframe (his default: 5-minute):
  step 1: a prior high or low was taken out
  step 2: BREAK_OF_STRUCTURE or INVERSE_GAP in the new direction
  step 3: price is currently inside a live continuation area
          (fair value gap, and/or past the midpoint, and/or the order block)
trigger, on the entry timeframe (his default: 1-minute):
  BREAK_OF_STRUCTURE or INVERSE_GAP in the direction of the decision timeframe's trend
  no further confirmation required on the entry timeframe
  (he explicitly does NOT wait for a 1-minute gap or 1-minute midpoint after this)
targets: prior highs/lows in the trade's direction (higher-timeframe ones for the
         later take-profits)
```

### 11.8 Divergence between the two indices
```
inputs: aligned bars for two correlated instruments (his pair: S&P 500 and NASDAQ)
condition gate: a significant prior high or low is being taken out RIGHT NOW on at
                least one of the two instruments. If not, do not emit anything.
bearish:
  instrument A: swingHigh(t1), then swingHigh(t2) < swingHigh(t1)
  instrument B: swingHigh(t1), then swingHigh(t2) > swingHigh(t1)
  -> bearish for BOTH; the tradeable instrument is A (the one with the lower high)
bullish:
  instrument A: swingLow(t1), then swingLow(t2) > swingLow(t1)
  instrument B: swingLow(t1), then swingLow(t2) < swingLow(t1)
  -> bullish for BOTH; the tradeable instrument is A (the one with the higher low)
role: bias ingredient, and it may substitute for early warning ahead of step 2.
      never an entry on its own.
```

### 11.9 Other imbalances
```
NEW DAY OPENING GAP:
  gap = [previous day's close, new day's open] when they differ
  role: target, or entry area. Not required to fill. Low priority (fills in Asian session).
NEW WEEK OPENING GAP:
  gap = [Friday's close, Sunday's open]
  role: target, or entry area. Highest value of the three, especially if unfilled at Monday's open.
NEW CANDLE OPENING GAP:
  gap between one candle's close and the next candle's open, same timeframe
  role: he calls it useless. DO NOT BUILD ON THIS.
FAST-MOVE RANGE (BPR):
  a range crossed rapidly in one direction and then rapidly back in the other
  role: once price re-enters the range, expect it to travel to the far side. Use as a
        target, or as an entry with continuation out the far side.
  [no numeric definition of "rapid" or of the required overlap: see 12.10]
```

---

## 12. Genuinely ambiguous, needs the video re-watched

1. **What confirms a swing high or a swing low.** Every single concept in this document is anchored to "the most recent swing high / low", and he never once defines mechanically when a swing point is confirmed (how many candles either side, whether it needs a close beyond, etc.). He does it by eye on the chart. This is the single biggest gap in the spec and it affects trend state, the midpoint anchors, and the break-of-structure test. Re-watch the break-of-structure videos (another agent's cluster) before implementing anything here.
2. **Consolidation.** He names it as the third trend state but gives no numeric test for when a market is in it rather than trending.
3. **"Expansionary candle".** No size threshold is ever given for the middle candle of a three-candle gap. The geometric gap condition may be the whole test, or he may be filtering visually for a large candle. Re-watch the gap lessons at the chart segments.
4. **Two phrasings of the gap test.** The rule he repeats everywhere compares candle 1's wick to candle 3's wick. In bootcamp Day 16 he once phrases it as "the first and third candles' wicks do not fill the second candle's body." These are not identical tests. Confirm which one he draws on the chart.
5. **The stacking test.** "No retrace in between" and "no black candle in between it" need to be resolved into one rule: is the test literally "no opposite-colour candle between the two gaps", or "no candle that partially fills the first gap"?
6. **Deleting gaps: which high.** "Once we push above this high" almost certainly means the swing high that preceded the retracement, but it is never named. Confirm against the chart.
7. **The 79% level.** He calls it "the 79% extension on the fib", says to draw it "just like equilibrium" (swing low to swing high), and then says price coming *down* past it disrespects an uptrend. That is a 79% retracement of the leg, not an extension. Confirm the anchor points and which direction the level sits from them. He also says this ingredient is optional.
8. **Midpoint reached: wick or close?** His language ("poke our head", "barely taps") and his shown examples suggest a wick past the 50% level is enough, but he never states it. This changes a lot of signals.
9. **Order block invalidation.** No kill condition is ever stated. Does a close beyond the order block kill it, or does it survive until the next trend flip?
10. **Fast-move range (BPR).** No definition of "rapid", and no rule for how much the up-move and the down-move must overlap.
11. **Aligning two instruments for the divergence test.** He compares "the same moment" across two charts by eye. A bot needs an explicit bar-alignment and swing-matching rule, and he gives none.
12. **Order blocks: retired or not.** Section 6.7. The newest video retires them; a different recent video still draws one. A judgement call is needed here and it is not mine to make. Recommendation for whoever decides: treat it as a switch, defaulting to the newest statement (off), so both eras can be tested.
13. **Breaker blocks.** Named twice in Order Flow Explained as something that shows a trend being respected, and named again in the retirement sentence, but never defined anywhere in this cluster. Source video unknown.
14. **The multi-candle order block boundary.** Where a "leg" begins is decided visually. Needs a rule.
15. **Which timeframes carry the gaps and midpoints in the live bot.** He says all timeframes work, and separately gives his own working set (4-hour and daily for direction, 5-minute for the decision, 1-minute for the trigger, with 15-minute appearing in bootcamp examples). Which set the bot tracks is a build decision, not something he states as a rule.

---

## 13. Cross-references out of this cluster (noted, not chased)

- **Liquidity, sweeps, and break of structure**: step 1 and half of step 2 of his sequence live there. This document takes the break-of-structure definition he restates inside these videos (a candle closing beyond the most recent swing point) and no more.
- **Daily bias, stops, targets, position size, sessions**: the timing details he mentions in passing here (waiting for the open, the ~9:50 window, avoiding news days, sizing the stop to the leg's timeframe, targeting prior highs and lows) belong to the execution spec. They are recorded here only because he says them inside these lessons.
- **Time theory**: announced at the end of the divergence video as the next lesson. Not in this cluster.
