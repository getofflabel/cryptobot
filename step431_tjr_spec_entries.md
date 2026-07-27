# TJR Specification: Liquidity, Liquidity Sweeps, and Break of Structure

**What this document is.** A transcription of what TJR says, in his own words, turned into
rules an engineer can implement. Nothing here is my judgement, my inference dressed as his
rule, or a suggestion. Where he does not say something, I say that he does not say it.

**Sources (all read in full).** All paths relative to `/Users/wallacechen/cryptobot/tjr_transcripts/`

| File | Words | Timestamps available? |
|---|---|---|
| `only_liquidity_guide.txt` | 9,706 | no |
| `ONLY_Liquidity_Sweeps_Video.txt` (video `_Fkofoggjv4`) | 10,120 | no |
| `Liquidity_Explained.txt` (video `crMqxB_nHhk`) | 5,736 | yes, via `p2p_liquidity.txt` |
| `Advanced_Liquidity_Concepts.txt` (video `AGmAVyAuBE0`) | 7,765 | yes, via `p2p_advanced_liquidity.txt` |
| `ONLY_Break_Of_Structure_Video.txt` (video `jeewXSLHt2g`) | 3,781 | no |
| `Break_of_Structure_Explained.txt` (video `Zzk864cVJek`) | 2,410 | yes, via `p2p_break_of_structure.txt` |

**One file added to the cluster.** `liquidity_profitable_fast.txt` (video `pKIo-aVic-c`, 6,300
words, fully timestamped). It is a pure liquidity video and falls in no other agent's cluster
(the other two agents have the confluences and the framing). It contains the single most
build-critical scope rule in the whole set (which timeframes he pulls levels from, and what
disqualifies a sweep), so leaving it out would have shipped an incomplete spec. Quotes from it
carry timestamps.

**Note on the `p2p_` files.** `p2p_liquidity`, `p2p_advanced_liquidity` and
`p2p_break_of_structure` are the same three videos as `Liquidity_Explained`,
`Advanced_Liquidity_Concepts` and `Break_of_Structure_Explained`, transcribed again with
timestamps. Same words. Used only to timestamp the ambiguous moments.

---

## 0. Scope: what he trades, when, and on what

Every rule below sits inside this box. He states the box repeatedly and without hedging.

**Instrument.** US stock index futures. He names the S&P 500 and the NASDAQ.

> "Me personally, I trade US indexes, so the S&P 500 and NASDAQ, but this still applies to
> foreign exchange." (`ONLY_Liquidity_Sweeps_Video`)

He demonstrates the same rules on EUR/USD and says they hold there. He does not claim to trade
it. He never mentions crypto in any of the six videos.

**Session.** New York market open only.

> "I personally only trade during US market open, during New York market open because I'm
> trading a US index. It would be stupid for me to be trading a U index during Asia session or
> during London session. The US index is going to move during the New York open because that's
> when the actual stock market is open." (`only_liquidity_guide`)

> "as you guys know, I pretty much only trade session open. So, I only trade US market open.
> I'm really never going to be trading an hour after New York market opens"
> (`ONLY_Liquidity_Sweeps_Video`) — see Ambiguity A1, the wording is genuinely two-way.

**Timezone.** All clock times are New York time (US Eastern). He requires the charting platform
be set to it before anything else.

> "we need to make sure that we are on Eastern time. Okay, we need to make sure that we're on
> New York time." (`Advanced_Liquidity_Concepts`, `p2p_advanced_liquidity` [0:11:30] region)

**Timeframe split.** Two different jobs, two different sets of timeframes. This is the most
often-missed part of the method.

- **Finding the levels (where liquidity sits):** the 4-hour and the 1-hour.
  > "the best time frames or at least for the way that I trade to be able to identify liquidity
  > on for me is going to be the 4 hour and the 1 hour." (`liquidity_profitable_fast` [0:15:24])
  > "I get on, I mark out the 4hour highs and lows" (`liquidity_profitable_fast` [0:18:45])

- **Finding the entry (confirming the reversal):** the 5-minute and the 1-minute.
  > "I'm looking to execute my trades on like the 5m minute or the one minute time frames."
  > (`only_liquidity_guide`)
  > "we get boom a one minute break of structure right here" (`ONLY_Liquidity_Sweeps_Video`)
  > "a low time frame 5-minute change in trend" (`Break_of_Structure_Explained`)

He is explicit that you should not hunt the sweep itself on the 1-minute:

> "are we going to try and catch liquidity sweeps on the one minute time frame? Is that really
> optimal for us? Probably not... if you're trying to take a liquidity sweep off the one
> minute, by the time price moves in the direction, it's it's already said and done. Okay?
> So, that's why we want to be looking at the high time frames to find our draws on liquidity."
> (`ONLY_Liquidity_Sweeps_Video`)

And why the high timeframe pool matters more than a low timeframe one:

> "if a 5m minute high gets gets pushed above and then we see like a downtrend form out of
> that, is that going to be longived? Probably not. So we need to know that the higher time
> frames hold higher power." (`only_liquidity_guide`)

---

## 1. Vocabulary, defined once in his words

| His word | His definition, quoted | Plain language used below |
|---|---|---|
| liquidity | "Liquidity is just resting orders on a chart" | orders sitting unfilled at a price |
| liquidity sweep | "when we go and take out and fill those pending orders to be able to move price in the opposite direction" | price trades through a level and then turns back |
| draw on liquidity | highs and lows: "draws on liquidity are highs and lows within the market" | a price level the market is pulled toward |
| break of structure (BOS) | "It's a trend change... the current market structure breaking" | the trend flips, proven by a candle body close |
| low resistance liquidity | "just stacked up highs and lows... trend line liquidity" | several unswept levels in a row |
| high resistance liquidity | "a liquidity sweep that price is currently trading away from" | a level already swept and reversed off |
| confirmation confluence | "it confirms that orders have been filled" | the proof step, which is break of structure |
| continuation confluence | his word for the fair value gap step | the entry trigger, after the proof |
| invalidation | "where that trade would get invalidated" | the price that proves the idea wrong |

---

## 2. Rule: how to identify a high and a low

**The rule.**

> "a high consists of an up candle, then a down candle. And a low consists of a down candle
> followed by an up candle... we're looking for the highest wick of those two candlesticks, and
> that is going to be our high... When we're looking to identify lows, we're looking for the
> move down, then the move up, and we're looking for the lowest point of those two
> candlesticks." (`only_liquidity_guide`)

Restated in `ONLY_Break_Of_Structure_Video` with the wick-or-body point made explicit:

> "What is a high within the market? It is a move up and then a move down. So that means it's a
> green candle followed by a red candle. What is a low within the market? It is a move down then
> a move up. A red candle then a green candle. And we take the lowest point of those two
> candlesticks. Whichever wick or body that the lowest point gets to and then whichever the
> highest point that either the body or those two candlesticks formed gets to, that's a high and
> that's a low."

**Exact specification.**
- A **high** exists at bar `i` when bar `i` closes above its open (up candle) and bar `i+1`
  closes below its open (down candle). The level is `max(high[i], high[i+1])`, using the full
  wick, not the body.
- A **low** exists at bar `i` when bar `i` closes below its open (down candle) and bar `i+1`
  closes above its open (up candle). The level is `min(low[i], low[i+1])`, using the full wick.

**What does NOT count.** He says this twice, in two videos, because his students get it wrong.

> "Is a high a green candle, then a green candle? No, because there hasn't been a move down
> yet... is a low a move down and then another move down? No, because there needs to be an up
> candle to form the low." (`ONLY_Break_Of_Structure_Video`)

> "they think a move down and then a move down is a low. No, Timmy, we need to move up because
> it causes the peaks and the valleys." (`liquidity_profitable_fast` [0:11:14])

**Timeframe dependence, stated explicitly.** The same visual pivot is a high on one timeframe
and not a high on another. When walking a 4-hour chart he points at a swing and says:

> "Is this a high on the current time frame that we're on? No. No. No, it's not. It is not a
> high. Maybe on the lower time frames it is a high. Actually, I'm sure of it on lower time
> frames that it's a high. But on the current time frame that we're in, the 4hour time frame,
> this is not a high. Why? Because this is a move down then a move down."
> (`ONLY_Break_Of_Structure_Video`)

So: the two-candle test runs separately on each timeframe's candles. Never mix.

**Confirms the prior.** The assumption I was given ("A high = up candle then down candle, level
at the HIGHER of the two wicks. A low = down candle then up candle, at the LOWER wick") is
correct and is stated in exactly those terms.

**Where it applies.** Every instrument, every timeframe. He says the concepts hold "on every
single time frame" more than a dozen times across the six files, and demonstrates on monthly,
daily, 4-hour, 1-hour, 30-minute, 15-minute, 5-minute and 1-minute charts.

---

## 3. Rule: where the resting orders are, and why there are two piles

**The rule.** Orders rest above highs and below lows. Two separate groups at each.

> "there's two sets of buy orders, above highs... In an uptrend, there's two sets of buy orders
> sitting above highs. And in a downtrend, there's two sets of sell orders sitting underneath
> lows." (`only_liquidity_guide`)

**Above a high, the two piles are:**
1. Traders entering long on the break, expecting the uptrend to continue.
   > "I'm going to press buy when we push past this high"
2. Traders who shorted the pullback and placed their protective exit above the high. When it
   trades through, they are forced to buy back.
   > "where does that trade get invalidated? Above the high... they are going to have resting
   > buy orders above highs."

**Below a low, the two piles are:**
1. Traders entering short on the break, expecting the downtrend to continue.
2. Traders who bought the bounce and placed their protective exit below the low. When it trades
   through, they are forced to sell.

**Why the big players need it.** He grounds this in an exchange-mechanics story he tells in four
of the six videos (buying a share of Apple requires somebody willing to sell it to you). The
operative consequence:

> "the market makers can't just place a massive short position right here because that would
> cause the market to fall... they want the best price possible, and they want to fill all their
> orders at in the exact position that they plan on... So, how are they able to do that? by
> waiting or pushing price above a high where they know that there's going to be a massive
> amount of buy orders entering into the market at this point in time."
> (`liquidity_profitable_fast` [0:07:00] to [0:08:04])

**Confirms the prior.** "Resting orders sit above highs and below lows, two piles at each" is
correct and is his exact framing.

**Build note.** This section is the reasoning, not a computable rule. No code comes from it. It
matters only because it tells you the levels are meaningful because of the two order piles, so a
level that has already been traded through has spent its piles. That is what makes the
low-resistance / high-resistance distinction in section 6 real.

---

## 4. Rule: a sweep creates the OPPORTUNITY, never the reversal

This is the single most repeated rule in the cluster. He states it in all six files, usually
several times, and he flags the word "opportunity" as the load-bearing word.

> "Notice when I was explaining when we push above a high, I didn't say the market makers always
> are going to reverse price. I say that they had the opportunity to reverse price when we push
> above a high." (`only_liquidity_guide`)

> "it gives the market the opportunity. This is the key key key word. It gives it the
> opportunity because we know uptrends, we move in higher highs and higher lows. So, every time
> we push above a high, does that mean the market is going to reverse? No. Does it have the
> opportunity to reverse? Yes." (`liquidity_profitable_fast` [0:05:06] to [0:05:21])

> "There was an opportunity for price to reverse here. Did it happen? No. There was an
> opportunity for price to reverse here. Did it happen? No. There was an opportunity for price
> to reverse here. Did it happen? Yes." (`Liquidity_Explained`)

**Therefore: entering on the sweep alone is forbidden.** He says this as an instruction, not an
observation:

> "Do we just blindly press buy when a low gets pushed underneath? No. Because if we did that,
> then we would boom press buy right here and then what would happen? Oh no, we're stuck in draw
> down forever." (`only_liquidity_guide`)

> "just because we're moving above a session high doesn't mean we can just boom instantly press
> sell. Just because we move underneath low resistance draws on liquidity doesn't mean we can
> press buy. We have to wait for confirmation." (`ONLY_Liquidity_Sweeps_Video`)

**And: he does not claim to know which level will be the one.** This is a scope limit on the
whole method and he is blunt about it.

> "you're probably saying, 'How do we know what draw what high or what low price is going to
> reverse off of?' That's the thing. We do not know."
> (`ONLY_Liquidity_Sweeps_Video`)

> "how am I able to actually like identify which high or low it's going to push above to end up
> causing the reversal? Well, that's the nice thing. It's going to sound bad, but you don't need
> to know." (`only_liquidity_guide`)

The operational answer is: mark all of them, wait, react.

> "that's why you guys will see me in my trade recaps marking out multiple highs and lows on
> every single session open. Why? Because I don't know the exact high that's going to get swept.
> ...And that's all that we need because when we can mark out those high potential highs and
> lows, from there, we just sit back and we wait for those levels to get hit."
> (`ONLY_Liquidity_Sweeps_Video`)

**Confirms the prior.** "A sweep creates the OPPORTUNITY to reverse, never the reversal itself.
Confirmation is mandatory" is correct and is the backbone of everything he teaches.

---

## 4b. Rule: what disqualifies a sweep

This is the sharpest single line in the cluster for a bot, and it comes from
`liquidity_profitable_fast`. A level being traded through is not a sweep. A sweep is only a
sweep once price has turned.

> "How do we know that orders were filled? Dude, look at the chart. If price comes down and
> takes out a low and keeps going down, is it a liquidity sweep? No. Because it's not reacting
> to it. That's why we want to mark out all the lows and all the highs. Look at these highs...
> We very well could have swept liquidity from these highs. But did the market react to these
> highs once we pushed through them? No, we didn't. We pushed higher. So, we're we're not
> looking to press short. **We wait for reaction.**"
> (`liquidity_profitable_fast` [0:16:38] to [0:17:13])

> "How do we know that it's a proper liquidity sweep? Because we literally see the reversal on
> the low time frames. We see a change in trend. We see a change in market structure on the
> lower time frames." (`liquidity_profitable_fast` [0:18:12])

**Exact specification.** "Reaction" is not left vague. He defines it in the same breath as a
change in market structure on the lower timeframe, which is the break of structure of section 7.
So a level being traded through opens a pending state, and the break of structure closes it into
a confirmed sweep. A level traded through with no subsequent break of structure in the opposite
direction is not a sweep and never becomes one.

---

## 5. Rule: which highs and lows actually count

Not every high and low is worth marking. `Advanced_Liquidity_Concepts` is dedicated to this. He
opens by saying there are seven forms and then enumerates the following (see Ambiguity A6 on the
count).

### 5.1 Session highs and lows
The highest and lowest price reached inside each session window. Marked for Asia, London and
New York. Full clock in section 5.6.

> "Asia session highs, Asia session lows, London session highs, London session lows, New York
> highs, New York lows. All of these are significant draws on liquidity."
> (`Advanced_Liquidity_Concepts`)

Method for computing them, stated as a procedure:

> "Where is London session high? Well, from 3 to 8:30, where's the highest point that we got to?
> Boom. Right here. Where's Asian session high? From 1,800 to three. The highest point that we
> got to was up here. Where is Asian session low? From 1,800 to three. Where is the lowest point
> that we got to? Right here. Where is London session low? From 3 to 8:30. Where's the lowest
> point we got to? Right here." (`p2p_advanced_liquidity` [0:12:20] to [0:12:44])

Note this is the running extreme of the session, not a two-candle pivot. Different definition
from section 2, and he uses both. Section 2 defines pivots; a session high is simply the highest
traded price in the window.

### 5.2 Previous day high and previous day low
> "previous day highs and previous day lows. Now this is the same exact thing but just all of
> those sessions encapsulated into one... we're looking at all of those sessions combined,
> finding the highest point and the lowest point of all three of those sessions combined."
> (`Advanced_Liquidity_Concepts`)

So: highest and lowest traded price across the full previous 18:00-to-18:00 trading day.

### 5.3 High timeframe highs and lows
> "High time frame liquidity for me is like 1 hour lows or 4hour lows, right?...if I'm entering
> trades on the low on the lower time frame, I'm going to want to take trades based off of high
> time frame liquidity sweeps. Why? Because I know that the moves are going to be a lot larger"
> (`only_liquidity_guide`)

Confirmed as the 4-hour and 1-hour in `liquidity_profitable_fast` (see section 0).

### 5.4 Low resistance liquidity (stacked / trendline)
Several unswept highs, or several unswept lows, close together and in a row.

> "Low resistance liquidity is when we have a bunch of stacked up highs or a bunch of stacked up
> lows that have not been swept out yet." (`only_liquidity_guide`)

> "Would it make sense for price to just go down and only fill one set of those sell orders? Or
> would it be super freaking easy for price to just say, 'Hey, we could literally get four times
> the amount of sell orders by just taking out all of these lows that are stacked up really
> freaking close to each other'" (`ONLY_Liquidity_Sweeps_Video`)

He counts examples of four and of five stacked levels. He never states a minimum count or a
maximum spacing. See Ambiguity A3.

### 5.5 Relative equal, and dead equal, highs and lows
> "relative equal highs and lows. What does this mean? You ever see on the chart when we make a
> high like this and then there's another high that doesn't quite go above this high, but it's
> super freaking close." (`ONLY_Liquidity_Sweeps_Video`)

Dead equal is treated as a stronger version of the same thing:

> "when we have dead ass like dead equal highs and lows as well. That's super super good draw on
> liquidity... equal highs and lows are just as good if not better."
> (`ONLY_Liquidity_Sweeps_Video`)

> "if we have the same exact price for both of these highs, there's four times the amount of buy
> orders." (`Advanced_Liquidity_Concepts`)

The only numeric example of "relative equal" he ever gives:

> "Low right here. Literally 50 cents apart." (`Advanced_Liquidity_Concepts`, on a 15-minute S&P
> chart)

That is one observed instance on one instrument, not a stated threshold. See Ambiguity A3.

### 5.6 News data candle highs and lows
The high and the low of the candle that prints when a high-impact economic release lands.

> "Data highs and data lows are news data highs and news data lows... this is coming after high
> impact news events. So, what we can do is we can go on to this handy dandy website called
> Forex Factory and what we are going to look for is red news folders."
> (`Advanced_Liquidity_Concepts`)

> "the highs of the news candles and the lows of the news candles are very very beneficial for
> us and serve as high probability draws in liquidity... We would mark out the high and the low
> of the news data candle." (`Advanced_Liquidity_Concepts`)

Named releases in the transcripts: CPI (8:30 a.m. New York time), PPI, unemployment claims, ISM
manufacturing PMI (10:00 a.m. New York time), non-farm payrolls.

He downgrades this one himself in the earlier video:

> "That's a little bit advanced. That's like advanced advanced. You guys aren't going to be
> using that all the freaking time. So, I would just stay focused on just high time frame highs
> and lows and session highs and lows." (`only_liquidity_guide`)

**Which candle** is ambiguous. See Ambiguity A4.

### 5.7 The session clock, exactly as he gives it

All times New York time.

| Session | Window he gives | Source |
|---|---|---|
| Asia | 18:00 to 03:00 | both videos, identical |
| London | 03:00 to 08:30 | both videos, identical |
| New York | see conflict below | conflict |
| Untradeable gap | 17:00 to 18:00 | `only_liquidity_guide` only |

Full quote from `only_liquidity_guide`:

> "there's three sessions that happen within the market. There are New York session which is
> 9:30 a.m. Eastern time till 5:00 p.m. Eastern time. Okay. Then there's London session which is
> from 3 a.m. Eastern time all the way until it technically ends at 11:00 a.m. Eastern time. But
> because it overlaps with New York session, I say that it ends at 8:30 a.m. Eastern time, which
> is when New York pre-market starts... And then there's Asia session. And Asia session starts
> at 6:00 p.m. Eastern time and goes all the way till 300 a.m. Eastern time... Then Asia
> session, there's a 1h hour gap where it's untradeable, okay? From 5:00 p.m. to 6 p.m. So
> there's like from like 501 to 559, you can't trade, okay? It's called like spread hour."

Full quote from `Advanced_Liquidity_Concepts` (`p2p_advanced_liquidity` [0:11:43] to [0:12:00]
and [0:20:05] to [0:20:33]):

> "Asia session starts at 1,800. London session starts at 3:00 a.m. New York session starts at
> 9:30 and New York premarket starts at 8:30. So, we can kind of group both of these together."

> "so again remember these numbers 1,800 Asian persuasion to three. 1800 to 3 is Asia session.
> 3 to 8:30 London session. 8:30 back to 1800 is New York session. So this is Asian. Boom.
> London. Boom. New York. Boom. And that encapsulates a full day of trading."

**The conflict, stated plainly.** For measuring the New York session high and low, `only_liquidity_guide`
implies 09:30 to 17:00 while `Advanced_Liquidity_Concepts` explicitly says 08:30 to 18:00 and
says that partition covers the whole day with no gap. The Asia and London windows are identical
in both, so the London high/low and Asia high/low (the two levels he actually trades off at the
New York open) are unaffected by this conflict. See Ambiguity A2.

**Corrects the prior.** The assumption I was given ("New York 09:30-17:00, with 17:00-18:00
untradeable") matches `only_liquidity_guide` but misses that `Advanced_Liquidity_Concepts` gives
08:30 to 18:00, and that the second video is the one where he actually walks through marking the
levels. For the levels that matter at the New York open, use 18:00-03:00 Asia and 03:00-08:30
London. Both videos agree on those.

### 5.8 Rule: the New York open takes the previous session's levels

He states this as a strong daily tendency and demonstrates it on consecutive trading days.

> "Right when New York session opens, what do we see? Where are London session lows? The New
> York traders say, 'Fuck those guys from London. We're going to stop all of them out so we can
> move the market where we want to move it.' Price comes down and sweeps out these London
> session lows and then makes the move for the day. That is not a coincidence. This happens
> almost every single day." (`only_liquidity_guide`)

> "It is not a coincidence. I just showed you back to back days. This was not planned. This was
> literally the last two trading days where New York session opens, we take out London session
> low, and then we end up going higher." (`only_liquidity_guide`)

He also shows London doing the same thing to Asia, one session earlier:

> "Right when London session opens, boom... they take out the lowest point of Asia session. And
> then what happens after that? London session moves higher." (`only_liquidity_guide`)

And he caps it himself:

> "It doesn't happen every single day. And matter of fact, I just chose this day at random."
> (`Advanced_Liquidity_Concepts`)

**Confirms the prior.** "The New York open frequently sweeps the London session high or low
first, then makes the day's move the other way" is correct, and he extends it: London does the
same to Asia, and the direction is not fixed. Both directions occur, sometimes both in one
session. On one day he shows New York sweeping the London high, reversing down, then sweeping
the London low and reversing back up.

**Timing.** The sweep is not required to land at the opening bell.

> "we're looking for draws on liquidity to get hit. Not right when market opens, okay? It's not
> always going to happen like right when New York market opens is like boom liquidity sweep.
> Sometimes it takes time. Okay, just like how we identified with EuroUSD right here. We can see
> that market opened and then we didn't sweep out this liquidity until 30 minutes into market
> open." (`ONLY_Liquidity_Sweeps_Video`)

**The pre-market carve-out.** If the sweep already happened before the bell and price is already
turning, that was the day's sweep. Do not wait for another one.

> "if I see that liquidity has already been swept during pre-market and we're already reacting
> off of it, awesome. Then this was the liquidity sweep for the day and I'm just going to take a
> trade reactive off of this. Okay, I'm not looking to be taking a trade off of a liquidity
> sweep from New York market open because the liquidity sweep already happened."
> (`liquidity_profitable_fast` [0:19:06] to [0:19:25])

Stated as an if/else in the same passage:

> "I mark out the 4hour highs and lows that the market could be able to sweep or has swept
> either during the previous session, during pre-market or London session. And if liquidity
> hasn't been swept during those sessions, then awesome. I'm expecting New York market to open
> and then for us to sweep out liquidity during the current session and then I'm going to take a
> trade off of it." (`liquidity_profitable_fast` [0:18:45] to [0:19:06])

---

## 6. Rule: low resistance versus high resistance, and which way to trade

**Low resistance liquidity.** Unswept, stacked levels. Price is pulled toward them. Use as a
**target**, and also as an entry level if price sweeps them and turns.

> "Low resistance liquidity is liquidity that price is going to want to actively trade towards."
> (`only_liquidity_guide`)

> "we can use this not only if we're looking to enter into a sell position up here as targets
> where we can target all of these cookies. But also we can use it as [an entry]"
> (`Advanced_Liquidity_Concepts`)

**High resistance liquidity.** A level that has already been swept and that price has turned
away from. Trade away from it, not back toward it.

> "High resistance liquidity is just this. Okay, it's the most recent or a liquidity sweep that
> price is currently trading away from... once we take that out, this becomes high resistance
> liquidity. This high right here. Why is it high resistance liquidity? Because why would price
> or why would the market makers want to sweep out all these highs, push price lower, and then
> go back up to target these highs again? It makes no sense." (`only_liquidity_guide`)

> "we want to trade towards low resistance liquidity. Why? Because we know that the market is
> actively going to want to seek that out and we want to trade away from high resistance
> liquidity." (`only_liquidity_guide`)

**The exit logic, in one line.** He compresses the whole method to this at the end of
`Advanced_Liquidity_Concepts`:

> "we sweep out highs to then target lows. That is the forefront of our strategy. We're using
> draws on liquidity to target other draws. Okay? So, we sweep out highs, we're looking for
> sells down to lows. We sweep out lows, we're looking for buys up to highs."

**Confirms the prior.** "Low-resistance liquidity = stacked unswept levels, a magnet, use as a
TARGET. High-resistance liquidity = already swept and reversed away from; trade away from it" is
correct and is his exact framing.

**One verbal slip to ignore.** In `only_liquidity_guide` he says "Currently, we actually have
good good high resistance liquidity to the upside" and then describes four stacked unswept highs
and says price will seek them out. By his own definitions that is low resistance liquidity. It
is a slip of the tongue in the middle of an otherwise consistent passage; the definitions he
gives before and after it are unambiguous. Do not encode the slip.

---

## 7. Rule: break of structure, in full

This is the confirmation step and it is the part that must be exactly right, because it is what
separates a sweep from noise.

### 7.1 What it is

> "What is it? It is a trend change. It's a confluence that shows us when the trend is changing
> and when the current trend that we're in is changing and breaking structure into a new trend."
> (`ONLY_Break_Of_Structure_Video`)

> "Break of structure is a confirmation confluence. Why do I call it a confirmation confluence?
> It's because it confirms that orders have been filled."
> (`Break_of_Structure_Explained`)

### 7.2 The trend definitions it depends on

- Uptrend: higher highs and higher lows.
- Downtrend: lower highs and lower lows.
- Consolidation: sideways, no identifiable trend. Named as a third state but never given a rule.
  See Ambiguity A5.

### 7.3 The break rule, exactly

**In an uptrend, you watch only the lows. In a downtrend, you watch only the highs.**

> "within an uptrend, how can we identify when the uptrend is broken or changes? when a low gets
> closed underneath... Now, within a downtrend, we're making lower highs and lower lows. When
> does this trend change or when does this trend break structure? When we close above the most
> recent high within the trend." (`ONLY_Break_Of_Structure_Video`)

**Only the MOST RECENT one.** Emphasised repeatedly.

> "we are looking at the most recent high that has been created and we are looking for a
> candlestick to close above it. That is the only way that we are going to be able to break
> structure. Okay. And within an uptrend, we are looking at the most recent low that has been
> created and we are looking for a candlestick closure underneath it. That is the only way that
> we can change the trend." (`ONLY_Break_Of_Structure_Video`)

The monitored level moves forward every time a new qualifying pivot forms:

> "So move down, then a move up. That's a low. We take the lowest point of those two candles.
> This is the new low that we're monitoring." (`ONLY_Break_Of_Structure_Video`, repeated for
> five consecutive lows in one walkthrough)

**It must be a body close, not a wick.** This is the rule he shouts.

> "Was it on this candlestick right here? This one. Is this a break of structure? Well, price
> pushed above here for a quick second, right? No, it's not a break of structure. This is a
> candlestick wick. **We need a full candlestick body close above a high or underneath a low**
> depending on what trend we're in in order for price to break structure."
> (`ONLY_Break_Of_Structure_Video`)

> "Look at this candlestick wick. It comes all the way down here. Is this a break of structure?
> NO! WHY IS IT not a break of structure? Because we don't get a candlestick closure underneath
> this low." (`Break_of_Structure_Explained`)

> "If we see candlestick wicks that go above these highs, are we immediately pressing buy?
> Absolutely not. We need to wait until a full candlestick closes above the most recent high."
> (`Break_of_Structure_Explained`)

**Strictly beyond, not equal to.** He hits a bar where the body bottom sits exactly on the level
and rules it not a break.

> "This is a very difficult one to read because we don't actually close underneath the low right
> here because the candle body is equal with this low. We need the candle body to close
> underneath the lowest point of the most recent low."
> (`Break_of_Structure_Explained`; `p2p_break_of_structure` [0:04:48] to [0:04:56])

**Exact specification.**
- The **level** is defined by the full wick extreme of the two-candle pivot (section 2).
- The **break** requires `close < level` for a downside break, `close > level` for an upside
  break. Strict inequality. `close == level` is not a break.
- The comparison uses only the candle's close. The candle's low or high going past the level
  does nothing.
- The asymmetry is deliberate: the level is set by a wick, the break is judged by a close.

**A higher low in a downtrend changes nothing. A lower high in an uptrend changes nothing.**
He spends a full minute on this because his students flip their bias on it.

> "something that can happen within trends is that we will make a higher low and a lower high.
> You're like, 'Wait a second. What trend has a lower high, lower high, but also a higher low?'
> ...Still a downtrend. Why? Because the most recent high has not been closed above yet...
> even though we make a higher low right here, that doesn't change the current downtrend
> structure that we're in." (`ONLY_Break_Of_Structure_Video`)

> "this is where a lot of people can get confused is they keep flipping their bias. They're
> like, 'Oh, we broke structure to the downside.' And then, 'Oh, we broke structure to the
> upside.' These are candlestick wicks, not candlestick closures. So, we are still in the
> uptrend that was formed on this break of structure right here."
> (`ONLY_Break_Of_Structure_Video`)

**How to read the current trend from cold, when you have no history.** He gives a procedure:

> "All I do is I look to the left and I look at what previous candle's price action was...
> That's the easiest way to be able to identify a trend. You look at the most recent high and
> you look at the most recent low and you see if the most recent high has been closed above and
> you look at the most recent low and you see if the most recent low has been closed
> underneath." (`ONLY_Break_Of_Structure_Video`)

**On which timeframe.** He demonstrates the mechanics on the 4-hour, but for entries he uses the
5-minute and the 1-minute (section 0). He does not say the break must be on both. See Ambiguity A7.

### 7.4 How a break of structure differs from a sweep

They are different events and the distinction is the heart of the method.

| | Liquidity sweep | Break of structure |
|---|---|---|
| What happens | price trades through a level | a candle body closes past a level |
| Which level | a significant high or low from section 5 | the most recent pivot inside the current trend |
| Wick or body | trading through with a wick is enough to open the pending state | wick is never enough, body close required |
| Direction | the level is taken in the direction of the existing move | the close is against the existing trend |
| What it means | orders MAY have been filled | orders WERE filled |
| Tradeable alone | no, forbidden | no, forbidden |

His own compression:

> "price comes up, takes out high time frame draws on liquidity, a bunch of highs. What can we
> do? We can scale down to the lower time frame, and we can see that those orders are getting
> filled. How? Through a low time frame 5-minute change in trend. How can we identify change in
> trend? By spotting break of structure."
> (`Break_of_Structure_Explained`)

### 7.5 The warning attached to it

> "if you just try and use it on your own by pressing buy when we break structure to the upside
> or pressing sell when we break structure to the downside, you are going to lose all of your
> money. This needs to be in combination with a bunch of other confluences."
> (`ONLY_Break_Of_Structure_Video`)

> "this is why we don't want to be entering and pressing sell right when we get a break
> structure to the downside because there's other confluences that are necessary in order to
> understand where price wants to go." (`ONLY_Break_Of_Structure_Video`)

---

## 8. The assembled sequence, in his order

He states the three-stage architecture in one sentence:

> "My strategy is as follows. We look for potential for orders to be filled, confirmation that
> orders are filled, and then a continuation of the current trend that is now being created."
> (`Break_of_Structure_Explained`)

Mapped:
1. **Potential** = a significant level gets swept.
2. **Confirmation** = break of structure on the low timeframe.
3. **Continuation** = the entry trigger (a fair value gap fill, or equilibrium). This is the
   other agents' cluster; captured here only where he states it inside my videos.

### 8.1 The worked short, quoted end to end

From `ONLY_Liquidity_Sweeps_Video`, walking a real S&P 500 session:

> "New York market opens at 9:30 a.m. How could we have executed on something like this? Well,
> we have London session highs. We have Asian session highs. These are our key levels. One of
> our key levels got hit. Boom. From there, what can I do? I can scale down to the lower time
> frames... We push above London highs. We push above Asian session highs. Then from there, what
> do we get? we get boom a one minute break of structure right here. And then from there, what
> else am I going to wait for? I'm going to wait for a fair value gap to get filled. Boom. This
> fair value gap gets filled. We get a down candle closing out of that. What can we do? We can
> take a short position there. We can put our stop loss above these highs. And then from there,
> what are we going to target? How can we exit off of these trades? By simply targeting other
> draws on liquidity."

Ordered:
1. Before the open, mark London session high/low and Asia session high/low.
2. Wait for New York open (09:30).
3. Price trades above London session high, then above Asia session high. (Sweep opened.)
4. Drop to the 1-minute.
5. Wait for a break of structure to the downside on the 1-minute. (Sweep confirmed.)
6. Wait for a fair value gap to be filled.
7. Wait for a **down candle to close** out of that gap. **This close is the entry trigger.**
8. Enter short on that close.
9. Protective exit placed **above the swept highs**.
10. Targets: the next draws on liquidity below, first one landing at roughly 1:1 (see 9.2).

### 8.2 The second worked short, London open

Same file, different session, same skeleton:

> "London session opens. Where do we immediately go? We immediately go up to do what? Sweep out
> Asian session highs... When we get above these highs, what does price immediately end up
> doing? It starts reversing... When do we get a break of structure? We get a break of structure
> right here. And then from there, again, because this is a US index, not really too many
> confluences, but we do come up and we fill equilibrium. And then boom, we get a down candle out
> of that. Can put our stops above these highs right here. And then boom, what can we do as our
> targets? We can target [relative equal lows]"

Note the substitution: where the first example used a fair value gap, this one used equilibrium.
The step is "wait for the continuation confluence to be filled, then a candle closing in your
direction out of it." Which confluence fills that slot on any given day is the other agents'
territory.

### 8.3 The stripped-down version, liquidity only

`only_liquidity_guide` gives a version with no other confluences at all, for people who have
only learned liquidity:

> "when we push underneath this low and we have the opportunity to activate buy orders, what do
> we do? we just wait for confirmation... We take out these lows and we say, okay, what does
> price have the opportunity to do? Reverse... How can we confirm that buy orders were filled?
> Well, we just look for an uptrend to form. So, what do we have right here? We have a high. We
> have a low right here. Then we make a higher low. Then we make a higher high. Awesome. Boom.
> Average entry could be right here."

And the mirror, for shorts, with a mid-sentence self-correction that matters:

> "We know that market has the opportunity to fill sell orders. How do we know that opportunity
> was taken? Well, we have a high, we have a low, **we make a lower high or sorry, we make a
> lower low, then we make a lower high.** What does that mean? There's it's a start of a
> downtrend. Average entry right here"

Repeated a moment later without the correction needed:

> "We push above this high. Okay? What happens? We have high, low, lower low, lower high.
> Average entry right here."

**Corrects the prior.** The assumption I was given said "after a high is swept, a lower high then
a lower low." That order is inverted. He says, and self-corrects to say, **lower low then lower
high**. The break of structure definition settles it independently: in an uptrend the break is a
body close below the most recent low, which by definition creates the lower low first; the lower
high is the pullback that follows and is where you enter. The prior's long side ("higher low then
higher high") is also loosely stated in one place by TJR himself but his second telling of the
same setup is "We push above this high. We make a higher high. We make a higher low," which
matches the break-of-structure definition. **Use: break first (new extreme in the new direction),
pullback second, entry on the pullback.**

---

## 9. Rule: where the protective exit goes, and where the targets go

### 9.1 The protective exit (the price that proves the idea wrong)

Both worked examples place it at chart structure, beyond the swept level. Never a distance,
never a percentage. He never once states a percentage stop in any of the six files.

> "We can put our stop loss above these highs." (short entered after a high was swept)
> "Can put our stops above these highs right here." (same, second example)

**Exact specification.** For a short taken after a high was swept: the protective exit sits above
the extreme reached during the sweep, that is above the highest price printed while taking the
level. For a long after a low was swept: below the lowest price printed while taking the level.
He says "these highs" while pointing at the swept highs on screen, so the level is the swept
structure itself. He does not state a buffer. See Ambiguity A8.

### 9.2 The targets

Targets are other draws on liquidity, and only that. He rejects the alternatives by name:

> "We're not just taking profits off of random draws, okay? We're not just taking profits off of
> Fibonacci extensions. Again, I like to have reasoning for why price is moving in the
> direction that it's going... So just like how we enter on liquidity sweeps, I'm exiting on
> liquidity sweeps as well." (`ONLY_Liquidity_Sweeps_Video`)

Reason given: the target level is itself a place where price can reverse, which is exactly why
it is a good place to be flat.

> "we want to be exiting when we're taking out draws on liquidity. Why? Because that gives price
> the opportunity to reverse. It's a profit-taking area where price has the opportunity to be
> able to fill orders to push price in the other direction."

**Multiple targets, scaled out.** He marks several and takes profit progressively.

> "So this can be your take-profit one. Boom. Perfect. A 1:1 risk-to-reward ratio. Boom. This can
> be take profit two." (`ONLY_Liquidity_Sweeps_Video`)

> "ideally we're taking profits as price is going down because ideally our first take profit
> isn't like a 1:9 risk-to-reward ratio. Obviously, that would be nice, but I don't want to sell
> you guys on a freaking dream." (`ONLY_Liquidity_Sweeps_Video`)

Note the 1:1 is an observation about where the first liquidity level happened to sit on that
chart, not a rule that the first target is placed at 1:1. The rule is: the target is the next
draw on liquidity. Its distance is whatever it is.

**When entering after a sweep of one kind of level, the opposite kind is the target.** He states
the pairing several times:

> "if New York session comes up, sweeps out Central C's highs, what's a good exit point? Central
> C's lows... So these are not only good entry points, they're also good exit points."
> (`Advanced_Liquidity_Concepts`)

> "we sweep out highs, we're looking for sells down to lows. We sweep out lows, we're looking
> for buys up to highs." (`Advanced_Liquidity_Concepts`)

---

## 10. Everything he explicitly forbids

Collected from all seven files. These are rules, not commentary, and he states them as
instructions.

1. **Never enter on a sweep alone.** "Do we just blindly press buy when a low gets pushed
   underneath? No." / "just because we're moving above a session high doesn't mean we can just
   boom instantly press sell."
2. **Never enter on a break of structure alone.** "you are going to lose all of your money."
3. **Never treat a wick past a level as a break of structure.** "These are candlestick wicks,
   not candlestick closures."
4. **Never treat a body closing exactly on the level as a break.** It must close strictly beyond.
5. **Never call it a sweep if price keeps going.** "If price comes down and takes out a low and
   keeps going down, is it a liquidity sweep? No. Because it's not reacting to it."
6. **Never trade a US index during Asia or London session.** "It would be stupid for me to be
   trading a U index during Asia session or during London session."
7. **Never trade Asia session at all.** "I would suggest against trading Asian session just
   because there's not that much volume."
8. **Never trade 17:00 to 18:00 New York time.** "you can't trade, okay? It's called like
   spread hour."
9. **Never hunt the sweep itself on the 1-minute.** "by the time price moves in the direction,
   it's already said and done."
10. **Never take profit at a Fibonacci extension or any level that is not a draw on liquidity.**
11. **Never trade like the retail crowd, i.e. never buy the break of a high or sell the break of
    a low as a continuation.** "we don't want to be following the method of pressing buy when
    highs get pushed above or pressing sell when lows get pushed underneath because that is how
    retail traders are trading... We want to be trading in the opposite direction."
12. **Never chase a trend late.** "we don't want to be pressing buy right here because we're
    already pretty deep into this uptrend... We want to be pressing buy down here when this
    uptrend gets created." / "We're not trying to be trend traders. We're trying to be reversal
    traders."
13. **Never flip bias on a higher low inside a downtrend or a lower high inside an uptrend.**
    Only the monitored extreme matters.
14. **Never wait for a fresh sweep at 09:30 if the sweep already happened in pre-market and
    price is already turning.** That was the day's sweep.
15. **Never assume you know which level will be the one.** "That's the thing. We do not know."
16. **Never run the chart in a timezone other than New York.**

---

## 11. Corrections and extensions to what was already assumed

| Prior assumption | Verdict | Detail |
|---|---|---|
| High = up candle then down candle, level at higher wick; low = down then up, at lower wick | **Confirmed, verbatim** | Section 2 |
| Two piles of resting orders at each level | **Confirmed, verbatim** | Section 3 |
| A sweep is opportunity only; confirmation mandatory | **Confirmed, and it is the backbone** | Section 4 |
| After a low is swept: higher low then higher high | **Loosely stated by him once, but inverted relative to his own break rule** | Section 8.3. Correct order is the break first (higher high), then the pullback (higher low), then entry |
| After a high is swept: lower high then lower low | **Inverted. He self-corrects on tape to lower LOW then lower HIGH** | Section 8.3 |
| Significant pools: 1-hour and 4-hour highs/lows, session highs/lows, news candle highs/lows | **Confirmed, and incomplete** | He adds previous day high/low, low resistance stacks, and relative-equal / dead-equal levels. Six or seven categories total. Section 5 |
| Sessions NY time: Asia 18:00-03:00, London 03:00-08:30, NY 09:30-17:00, 17:00-18:00 untradeable | **Asia and London confirmed in both videos. NY window conflicts between videos** | Section 5.7 and Ambiguity A2. `Advanced_Liquidity_Concepts` gives NY as 08:30 to 18:00 |
| NY open frequently sweeps London high or low first, then makes the day's move the other way | **Confirmed, and extended** | London does the same to Asia. Both directions occur, sometimes both in one session. Sweep can land up to 30 minutes or more after the bell. Pre-market sweeps count and pre-empt |
| Low resistance = stacked unswept, use as target. High resistance = already swept, trade away | **Confirmed, verbatim** | Section 6. Low resistance also serves as an entry level when swept |

**Biggest thing missing from the prior:** the split between the timeframe you find levels on
(4-hour and 1-hour) and the timeframe you confirm and enter on (5-minute and 1-minute), plus the
disqualifier that a level traded through without a reaction was never a sweep. Both come from
`liquidity_profitable_fast` and both are load-bearing for a bot.

---

## 12. The bar-by-bar checklist a bot would run

Written so an engineer who has never watched a trading video can implement it without a single
judgement call. Where he gives no number, the checklist says NEEDS VIDEO rather than inventing
one.

### 12.1 Inputs required

| Input | Value | Source |
|---|---|---|
| Instrument | US index futures (S&P 500, NASDAQ) | Section 0 |
| Chart timezone | America/New_York for all timestamps | Section 0 |
| Level timeframes | 4-hour candles, 1-hour candles | Section 0 |
| Entry timeframes | 5-minute candles, 1-minute candles | Section 0 |
| Asia window | 18:00 to 03:00 New York time | Section 5.7 |
| London window | 03:00 to 08:30 New York time | Section 5.7 |
| New York pre-market start | 08:30 New York time | Section 5.7 |
| New York open | 09:30 New York time | Section 5.7 |
| New York session window for level marking | 08:30 to 18:00 (`Advanced_Liquidity_Concepts`) OR 09:30 to 17:00 (`only_liquidity_guide`) | Ambiguity A2 |
| Blackout | 17:00 to 18:00 New York time, no trading | Section 5.7 |
| Trading window | New York open onward, see Ambiguity A1 for the end | Section 0 |
| News calendar | Forex Factory red-folder events | Section 5.6 |

### 12.2 Once per day, before 09:30 New York time

**Step 1. Build the pivot set.** On the 4-hour series and the 1-hour series independently, walk
every adjacent pair of candles:
- If `close[i] > open[i]` and `close[i+1] < open[i+1]`, record a HIGH at `max(high[i], high[i+1])`.
- If `close[i] < open[i]` and `close[i+1] > open[i+1]`, record a LOW at `min(low[i], low[i+1])`.

**Step 2. Compute the session extremes.** From the 1-minute (or finest available) series:
- Asia high = max traded price 18:00 to 03:00. Asia low = min over the same window.
- London high = max traded price 03:00 to 08:30. London low = min over the same window.
- Previous day high = max traded price over the previous full 18:00-to-18:00 day.
  Previous day low = min over the same.

**Step 3. Mark the news candle levels.** For each red-folder release in the last N days
(N NEEDS VIDEO), take the candle covering the release time and record its high and its low.
Which timeframe's candle is NEEDS VIDEO, see Ambiguity A4.

**Step 4. Tag stacked levels.** Group consecutive same-side unswept levels that sit close
together into a low-resistance cluster. The spacing threshold and the minimum count are NEEDS
VIDEO, see Ambiguity A3.

**Step 5. Mark each level swept or unswept.** A level is already-swept if price has traded past
it at any point since it formed. Already-swept levels that price then reversed away from are
high resistance: do not trade toward them. Unswept levels are low resistance: they are both
candidate sweep sites and candidate targets.

**Step 6. Assemble the watchlist.** The union of steps 1 to 4, restricted to unswept levels.
Every one is a candidate. The bot does not rank them and does not predict which one fires. It
watches all of them.

**Step 7. Check the pre-market carve-out.** If, between 08:30 and 09:30, price traded past one
of the watchlist levels AND a break of structure in the opposite direction has already printed
on the 5-minute or 1-minute, then that is the day's sweep. Jump straight to step 12 with that
level as the swept level. Do not wait for a new sweep after the bell.

### 12.3 On every closed bar during the trading window

**Step 8. Update the pivot set.** Re-run the two-candle test on the newest closed candles of
every timeframe in use. Update the "most recent high" and "most recent low" pointers for each
timeframe.

**Step 9. Update trend state per timeframe.** For each of the 5-minute and 1-minute series
maintain a state of UPTREND, DOWNTREND or UNKNOWN.
- If state is UPTREND and `close < most_recent_low_level` (strictly), set state to DOWNTREND and
  emit a downside break-of-structure event.
- If state is DOWNTREND and `close > most_recent_high_level` (strictly), set state to UPTREND
  and emit an upside break-of-structure event.
- Equality is not a break.
- A wick past the level with the close on the wrong side does nothing at all: do not update
  state, do not emit.
- A higher low inside a downtrend does not change state. A lower high inside an uptrend does not
  change state. Only the monitored extreme matters.
- To initialise from cold: look back, find the most recent high and the most recent low, check
  which one has been closed past most recently, and set state accordingly.

**Step 10. Detect a sweep opening.** On each closed bar, for every unswept watchlist level:
- If the bar's high went above an unswept HIGH level, mark that level PENDING-SWEEP-DOWN, record
  the extreme price reached (`sweep_extreme = max high while past the level`), record the bar
  time.
- If the bar's low went below an unswept LOW level, mark it PENDING-SWEEP-UP, record
  `sweep_extreme = min low while past the level`, record the bar time.
- Trading past the level with only a wick is sufficient to open the pending state. Section 4b
  requires the reaction, not a close, to open it.

**Step 11. Kill or confirm the pending sweep.**
- **Kill:** if price continues in the sweep direction without a break of structure against it,
  the pending state is not a sweep. He gives no bar count or distance for how long you wait
  before discarding. NEEDS VIDEO, see Ambiguity A9. A defensible mechanical proxy that follows
  from his own words: discard when a break of structure prints in the SAME direction as the
  sweep on the entry timeframe, because that is the trend continuing rather than reversing.
- **Confirm:** the pending state becomes a confirmed sweep the moment step 9 emits a
  break-of-structure event on the 5-minute or 1-minute in the direction OPPOSITE to the sweep.
  - PENDING-SWEEP-DOWN (a high was taken) is confirmed by a downside break of structure.
  - PENDING-SWEEP-UP (a low was taken) is confirmed by an upside break of structure.

**Step 12. Wait for the continuation confluence.** After confirmation, wait for the entry trigger
in the direction of the confirmed reversal. Per section 8.1 and 8.2 this is:
- a fair value gap (or, on a US index where fewer are available, equilibrium) inside the leg that
  produced the break of structure, being filled by price returning into it, THEN
- a candle **closing** out of that zone in the trade direction.
- The definition of the gap and of equilibrium is the other agents' cluster. This spec records
  only that the slot exists, that something must fill it, and that the trigger is a close.

**Step 13. Place the order.** On the close of the candle in step 12. Market or limit is not
stated; he says "we can take a short position there" pointing at that closed candle.
- Direction: opposite to the sweep. High swept, go short. Low swept, go long.
- Protective exit: beyond `sweep_extreme` from step 10. Above it for a short, below it for a
  long. Buffer size NEEDS VIDEO, see Ambiguity A8.
- Position size: `risk_dollars / distance_from_entry_to_protective_exit`. He does not state this
  formula in these six videos; it is the standard consequence of a structure-placed exit and is
  the framing agent's cluster.

**Step 14. Set the targets.** Take the unswept watchlist levels lying in the trade direction,
nearest first. Target 1 is the nearest, target 2 the next, and so on. Scale out progressively.
Do not use any level that is not on the watchlist. Do not use a ratio, an extension, or a fixed
distance.

**Step 15. Stop looking for the day.** He takes his setup at the session open. Once the day's
sweep has fired and been traded, and certainly once past the end of his trading window (Ambiguity
A1), stand down. No trading 17:00 to 18:00 under any circumstances.

### 12.4 The whole thing in nine lines

```
1  timezone = New York
2  before 09:30 : mark 4H + 1H highs/lows, Asia H/L, London H/L, prev-day H/L,
                  news-candle H/L, stacked clusters. keep only the unswept ones.
3  if a level was already taken in pre-market AND a break of structure has already
   printed against it -> that is today's sweep, go to 7
4  wait for price to trade past one of those levels          (opens PENDING)
5  wait for a body close past the most recent opposite pivot,
   on the 5-minute or the 1-minute, AGAINST the sweep         (PENDING -> CONFIRMED)
6  if price just keeps going instead, it was never a sweep. discard.
7  wait for the continuation zone to be filled
8  wait for a candle to CLOSE out of that zone in the trade direction  -> ORDER HERE
9  protective exit beyond the sweep extreme. targets = the next unswept levels.
```

---

## 13. What is genuinely ambiguous and needs the video re-watched

Honest gaps. Each one is something a bot must decide and he does not decide it in these
transcripts.

**A1. "Never trading an hour after New York market opens."**
`ONLY_Liquidity_Sweeps_Video`, in the timing section. Full context: "as you guys know, I pretty
much only trade session open. So, I only trade US market open. I'm really never going to be
trading an hour after New York market opens because there's almost always going to be a form of
manipulation taking out either session highs and lows... at session and market opens."
Two readings: (a) he never trades LATER than one hour after the open, so his window is 09:30 to
10:30, or (b) he never trades DURING the hour after the open. The "because" clause supports (a),
since the reason given is that the manipulation happens at the open. But (b) is grammatically the
more natural reading of the sentence. This sets the bot's trading window and cannot be guessed.
No timestamps exist for this video (`_Fkofoggjv4`); the passage sits shortly after the
relative-equal-highs section and immediately before the "timing is a huge, huge, huge thing"
passage, roughly two thirds of the way through.

**A2. The New York session window used for marking its high and low.**
`only_liquidity_guide` says New York is 09:30 to 17:00 with 17:00 to 18:00 untradeable.
`Advanced_Liquidity_Concepts` (`p2p_advanced_liquidity` [0:20:12] to [0:20:33]) says "8:30 back
to 1800 is New York session" and that the three windows encapsulate a full day with no gap. This
does not affect the Asia or London levels (identical in both), so it does not affect the setup he
actually trades at the open. It does affect the previous-day New York session high and low if you
use those as levels. Re-watch `AGmAVyAuBE0` at 20:00 to 20:35 and `only_liquidity_guide`'s
session section together.

**A3. "Relative equal" and "stacked": no threshold, no minimum count.**
He never gives a maximum price distance for two levels to count as relatively equal, and never a
minimum number of levels to count as a stack. His only concrete number is one observation:
"Literally 50 cents apart" on a 15-minute S&P chart (`Advanced_Liquidity_Concepts`, around
[0:39:00] to [0:41:00] in `p2p_advanced_liquidity`, in the search for a dead-equal example). His
stack examples contain four and five levels. A bot needs a numeric tolerance, probably scaled to
recent volatility, and he supplies none.

**A4. Which timeframe's candle is the "news data candle."**
He says to mark the high and low of the candle that prints on the release. He is looking at a
chart while saying it but the transcript never names the timeframe. He does say the effect shows
up "on the low time frames." Given his level timeframes are 4-hour and 1-hour and his entry
timeframes are 5-minute and 1-minute, this could be any of four. Re-watch `AGmAVyAuBE0` from
roughly [0:44:00] to [0:52:00] (`p2p_advanced_liquidity` lines covering CPI on the 13th and
December 18th, PPI on November 25th, unemployment claims on November 20th) and read the timeframe
selector on screen.

**A5. Breakouts from consolidation.**
In `ONLY_Break_Of_Structure_Video` he promises the rule and never delivers it: "The third way
that the market can move is through consolidation where we are pretty much just moving
sideways... And that is where we will be able to identify breakouts in which is a form of a
breakup structure, but it's a little bit different than how we identify a breakup structure
within these current trends. But I'm going to show you guys how to identify a break of structure
within an uptrend, within a downtrend, and then also how to spot a breakout from consolidation."
He then covers uptrends and downtrends and ends the video. The consolidation rule is missing
entirely. A bot's trend state will sit in UNKNOWN during sideways price and this spec has no rule
for exiting that state other than the normal break rule. Either re-watch `jeewXSLHt2g` in full in
case it is shown visually without narration, or find it in another video.

**A6. "There's 1 2 3 4 5 6 7 forms of advanced draws on liquidity."**
`Advanced_Liquidity_Concepts` opens with that count. Counting what he actually delivers: session
highs/lows, previous day high/low, low resistance stacks, relative equal, dead equal, news data
highs/lows. That is five or six depending on whether relative-equal and dead-equal count
separately. He also skips one on purpose in `ONLY_Liquidity_Sweeps_Video`: "the other good um I
don't even want to mention that in this video because it doesn't really even happen that often."
There may be a seventh category he names on screen and skips verbally. Re-watch `AGmAVyAuBE0` for
an on-screen list.

**A7. Which entry timeframe the break of structure must print on.**
He uses the 1-minute in one worked example and the 5-minute in another, and in
`Break_of_Structure_Explained` describes it generically as "a low time frame 5-minute change in
trend." He never says whether both must agree, whether the 1-minute is used only when the
5-minute is too slow, or whether it is discretionary. A bot must pick one or define a precedence
rule. Re-watch `_Fkofoggjv4` (the two worked entries near the end) and `Zzk864cVJek` (the live
S&P walkthrough at the end, roughly [0:11:30] onward in `p2p_break_of_structure`) with the
timeframe selector visible.

**A8. Buffer on the protective exit.**
"We can put our stop loss above these highs." Above by how much is never said and cannot be read
off the transcript. He is pointing at a level on a chart. Needs the video paused on the order
ticket, or another source.

**A9. How long a pending sweep stays alive before it is discarded.**
Section 4b tells you a sweep with no reaction is not a sweep. It does not tell you how many bars
or how far to let price run before you declare no reaction. Without this, a bot will hold stale
pending states indefinitely. He never gives a number in any of the seven files.

**A10. Order type at entry.**
"We can take a short position there" on the close of the trigger candle. Market order on the
close, or a limit resting at the zone, is not stated.

**A11. Whether every level on the watchlist is equally tradeable, or whether some are for
targets only.**
He says session highs/lows, previous day levels and stacked levels serve as both entries and
exits ("these are not only good entry points, they're also good exit points"). But he also says
in `only_liquidity_guide` that news data levels are "advanced advanced" and to stay focused on
high timeframe and session levels. Whether a bot should trade off news candle levels at all, or
only target them, is not resolved.

---

## 14. Cross-references out of this cluster (noted, not chased)

These are named inside my six files but belong to the other agents:

- **Fair value gaps** and **inverse fair value gaps**: the continuation confluence in step 12.
  "It's going to be break of structure, fair value gaps, and inverse fair value gaps. Those are
  by far some of the best confluences" (`only_liquidity_guide`).
- **Equilibrium**: substituted for the fair value gap in the second worked entry
  (`ONLY_Liquidity_Sweeps_Video`).
- **Breaker blocks** and **order blocks**: named once as additional confirmation options
  (`ONLY_Liquidity_Sweeps_Video`).
- **Internal versus external liquidity**: "price is always either looking to take out external
  liquidity, which is highs and lows, or fill imbalances, which is internal liquidity"
  (`Advanced_Liquidity_Concepts`). External liquidity is this whole document. Internal liquidity
  is the fair value gap agent's cluster.
- **Daily bias**, **time theory**, **risk management**: named, deferred to the framing agent.
- The **five and a half hour full guide** he points at repeatedly is `full_tutorial_2026.txt`
  (82,772 words) in the same directory.
