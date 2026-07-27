# TJR: How He Manages a Trade

Transcription of TJR's own stated rules for stop placement, position size, profit
taking, and the conditions under which he stands aside. His numbers, his words.
No evaluation, no second-guessing.

**Sources read in full:** bootcamp Day 03, 11, 13, 17, 21, 25, 29, 30, 32, 33, 37,
38, 39, 41, 42, 44, 45, 46, plus `Risk_Management_and_Psychology.txt` and
`Trading_Psychology_9_Years.txt`. Supporting quotes on partial exits pulled from
his trade recaps (Day 50, 53, 54) and from `Strategy_Revealed`,
`Data_Backed_Strategy_Everyday`, `Stupid_Simple_Strategy_Backtested`,
`UPDATED_Day_Trading_Strategy_2026`.

**Units convention used throughout:** every percentage below is a **percent of the
account balance** unless it explicitly says otherwise. TJR never talks in price
moves when he talks about risk. Where he says "points" or "pips" that is a
distance on the chart, not a percentage of anything.

---

## 1. WHERE THE STOP GOES

Source: **Day 38 (Stop Losses)**, with confirmations in Day 33 and Day 37.

### 1.1 The single rule

> "I almost always put my stop loss above the liquidity sweep."

For a **short**: the stop goes **above the high that got swept**.
For a **long**: the stop goes **below the low that got swept**.

That is it. That is the whole primary rule, and he repeats it four separate times
in Day 38.

### 1.2 Why that spot and not somewhere else

> "if our bias was correct, if liquidity was actually taken out, then price has no
> reason to come back above this high... but if price ends up coming back above
> this high then that means the liquidity sweep was not valid, that means liquidity
> was not swept, that means there was not enough volume or volatility, that means
> there weren't enough orders to be filled to push price in our bias and in our
> direction."

> "our stop loss always has a purpose, our stop loss is essentially our
> invalidation area."

In plain terms: the stop sits at **the price that proves the trade idea was wrong**.
Beyond the swept high or low, the reason for the trade no longer exists.

### 1.3 The stop does NOT go at the entry

This is explicit and he calls it out as a mistake:

> "it should not be right above this high [the entry candle / order block]... why?
> because price could easily come back a little bit higher and then come back down.
> You want price to be above the liquidity sweep because that's where price would be
> invalidated for us."

So even when you enter off a fair value gap or an order block that sits well inside
the range, **the stop still goes beyond the liquidity sweep**, not just beyond your
entry structure.

> "whether you're entering off of a fair value gap or an order block, your stop loss
> should still be above the liquidity sweep."

### 1.4 Which sweep, when there are several

He anchors the stop to the sweep on **the timeframe he treated as the setup's sweep**,
not the timeframe he executed on. His own worked example from that day:

> "I put my stop loss underneath here because we had a liquidity sweep on the five
> minute right here and then a break of structure only [on the] one minute to the
> upside, so I was considering this my liquidity sweep, so that's why I put our stop
> loss right here."

So: 5-minute sweep + 1-minute break of structure means the stop goes beyond the
**5-minute** sweep.

### 1.5 The buffer, and the reason for it

He adds a small distance beyond the swept level so the broker's bid/ask difference
cannot take him out at the exact level.

> "every single time at least put it like I would like to say like five like point
> five points 0.5 points below the actual price point, or figure out what your spread
> is on your broker for the specific pair, because if you put your stop loss directly
> on this price, literally on this exact price on your brokerage, guess what, when
> price comes down to like right here you will be stopped out of the trade... you are
> going to get stopped out by spread."

On the actual trade he was reviewing that day (S&P 500):

> "for us ours was like what was it, it was four four below."

**Both numbers are his words.** The "0.5 points" figure is spoken as a minimum
general buffer; the "four" is what he used on that specific S&P trade. See the
ambiguity list at the end, the transcript garbles the exact digits.

He also states the general form of the rule instead of the number: **find your
broker's spread on that specific instrument and clear it.**

### 1.6 Explicit ban on a fixed-distance or percentage stop

This is the closest thing in the whole cluster to a direct statement of our standing
rule, and it is his:

> "your stop loss should never be like, shouldn't be based purely off of points or
> pips. It should be based off of where price is then invalidated, where your bias is
> invalidated at that point."

**He never once gives a percentage stop, a fixed point stop, or a volatility-multiple
stop.** The only numbers attached to the stop are the spread buffer. Nothing in the
cluster contradicts our standing rule.

### 1.7 The two exceptions he names (and dislikes)

**Exception A: the sweep is so far away the trade is not worth taking.**

> "if price looks like this and this is our break of structure and the liquidity
> sweep is so high up that it pretty much would give you a terrible risk reward, then
> I try and find other confluences within here... let's say there's a fair value gap
> here, an order block like right here, I would put my stop above the order block and
> I wouldn't put it above the liquidity sweep."

And immediately he qualifies it:

> "the reason why I don't necessarily like doing that is because the invalidation
> point is above the liquidity sweep, so price could still technically move up and
> take you out of the trade and still go within our bias."

**Exception B: a higher-timeframe setup with an enormous stop.**

> "you could scale into a relatively higher time frame and try and find, you know,
> maybe a low, like one scale lower, that's underneath the liquidity sweep if you
> want to be extra safe."

He caveats both with: "all of this is just purely based off of your own risk
tolerance."

### 1.8 Does the stop ever move once placed?

**It moves in exactly one direction, once, and only after a target is reached.**

> "after take profit one got hit I took off 50 of the position, my stop's [at] break
> even all the way up here" (Day 54 recap)

> "I set extended take profits, I managed my positions, when take profits were hit I
> moved my stop loss to break even" (Day 21)

Widening the stop, moving it away, or removing it is treated as a psychology failure,
not a technique:

> "wanting to win every single trade leads you to moving stop losses, revenge trading,
> and holding your losers." (Trading_Psychology_9_Years, lesson 7)

And he explicitly refuses to close a runner manually just because it is deep in
profit, once the stop is at break even:

> "there was days where I had $330,000 floating in profit where my stop loss was at
> break even and I could have closed it and I didn't because I had to stick to my
> plan." (Day 21)

---

## 2. HOW POSITION SIZE IS CALCULATED

Source: **Day 39 (Calculating Lot Size)** and **Day 13 (Risk Management)**, updated
in `Risk_Management_and_Psychology.txt`.

### 2.1 The three methods he names

> "there's three different ways that you can do this. You can use a set lot size,
> that's what I use, and I use a range of set lot sizes... you can also calculate your
> lot size every single time... and then you can also full port, which you will never
> do, and if you do I will be very upset. So third option is completely out of the
> picture."

- **Method 1: set lot size** (what he personally uses)
- **Method 2: calculate every trade** (what he tells unprofitable traders to use)
- **Method 3: entire account on one trade** (forbidden outright)

### 2.2 Method 2, calculate every trade: the exact arithmetic

Four inputs, one output.

| Input | Where it comes from |
|---|---|
| Account balance | your account |
| Risk percent **of the account** | your plan (see 2.3) |
| Stop distance in pips/points | measured on the chart |
| Contract size (units per lot) | your broker's instrument details page |

> "let's say we have a 1,000 account, you type in a thousand up there, and then let's
> say we want to risk one percent, we type one in there, and then let's say our stop
> loss is 30 pips, we type 30 in there... and it tells you the exact lot size that you
> should use to risk that amount for your account size."

Worked example he runs on screen: **$1,000 account, 1% of account, 30-pip stop, GBP/USD
gives 0.03 lots, which is $10 risked.**

How he reads the stop distance off the chart, with no calculator:

> "if you don't know what your stop loss is in pips, we'll make this really easy...
> when you set up your short position tool, see this number right here, that is it,
> that's your stop loss in pips."

The contract-size warning, which is the one input people get wrong:

> "you're going to open up your little MetaTrader and then you're going to click on
> SPX... you are going to click details, and then from there you are going to find the
> line where it says contract size. See on mine where it says contract size and then
> to the right of it it says 10, okay, that means it's contract size 10 units per lot...
> most offshore brokerages are 100 units per lot... a lot of prop firms, their units
> per lot is going to be 10. So make sure whenever you open a new account with a
> different brokerage, with any different firm, with anything, you check this, because
> this could really mess you up."

**Does this match our engine?** Yes. `size = dollars risked / stop distance` is
mathematically identical to what the calculator he demonstrates does. The only extra
term is the instrument's units-per-lot, which is a venue-specific unit conversion, not
a different formula.

### 2.3 The risk percent of the account

**Day 13, the baseline rule:**

> "risk one to three percent of your account, and that's it. You're risking one to
> three percent of your account size per trade."

And restated as a per-day cap rather than per-trade:

> "risk one to three percent of your account per day. That just makes it easy... then
> it's like okay, I can take two trades with 1.5 risk, or I can take one trade with one
> percent risk, I can take one trade with three percent risk, I can take three trades
> with one percent risk. Either way you're still within that threshold."

**Day 46, restated as a hard check when journaling:**

> "what was your risk on the trade? Ideally, it's 1 to 3%. If it's anything more,
> you're immediately doing something wrong. If it's anything less, that's completely
> fine. Ideally, it's 1 to 3%, ideally just 1% per trade."

**His own base number: 1% of the account.**

> "my normal risk is just one percent."

The arithmetic he uses to justify 1%:

> "if we are risking one percent of our account per trade that means we would have to
> lose a hundred trades in a row to lose that account completely."

### 2.4 Method 1, set lot size: how he derives the fixed number

This is the part where his method **differs from a pure risk-per-trade engine** and it
matters for implementation.

He does not resize per trade. He picks a lot size once, calibrated to his **narrowest
typical stop**, and then lets the realized risk float upward when the stop is wider
that day.

> "most of the time my stop loss on the S&P 500 is anywhere from... four points to,
> we'll say like, seven points. So what do you do, you go in here... you're going to
> set your minimum, like what's usually the lowest your stop loss will be during a
> trade. For me it's usually 400 [pips, which is 4 points]. We calculate that, boom,
> 25 lots. That is going to be our set lot size."

Worked example, stated fully: **$100,000 account, 4-point (400-pip) stop, 1% of the
account, contract size 10 units per lot, gives 25 lots.**

Then the consequence, which he accepts on purpose:

> "that means I'm going to be risking one percent if price hits stop right here. That
> also means I'll be risking two percent of my account if we have a larger stop loss and
> price goes to eight points... that is two times my regular one percent risk... and if
> it goes 3x that, cool, I'll be risking three percent of my account. This is why I like
> this so good, because I have a great feel of what my average stop loss is going to be...
> most of the time it never goes to three percent risk, which is why I like using set
> [lot] size."

**Summary of the difference from our engine:**

| | our engine | TJR's set-lot method | TJR's calculate-every-time method |
|---|---|---|---|
| Size formula | risk$ / stop distance | fixed, calibrated once to the **narrowest** typical stop | risk$ / stop distance |
| Realized risk when stop is wide | constant | scales up: 2x stop = 2% of account, 3x stop = 3% of account | constant |
| Cap | our own | ~3% of the account in practice, he says it "never" goes past that | 1% to 3% of the account |

He says outright that **beginners should use the calculate-every-time method**, which
is the one that matches our engine:

> "a lot of you guys should use a calculated lot size, a lot of you guys shouldn't use
> a predetermined lot size because you won't know what you're risking." (Day 29)

### 2.5 The three-tier size ladder

> "my normal risk is 25 lots... what's the second option, de-risk, my de-risk day, 50
> [percent] of my normal... and then we have the confident lot size, which is I double
> it."

| Tier | Multiplier of normal | Risk at his minimum stop | When he uses it |
|---|---|---|---|
| **De-risk** | 0.5x | 0.5% of the account | high-impact news day; bank holiday; anything he expects to make the market choppy or low volatility |
| **Normal** | 1.0x | 1% of the account | a day with no news, or news that will not move the market much |
| **Confident** | 2.0x | 2% of the account | no news, he likes the setup, all the timeframe biases are in line |

The confident tier's ceiling in his own words:

> "that pretty much is putting me at risk to starting off at two percent, potential to
> go to four percent, and then potential to even go to up to what even would it be,
> six percent or eight percent."

And the ban attached to it:

> "you guys should never use a confident lot size, you guys feel free to use normal or
> de-risk, never use confident, because you guys don't have proof in the market that
> you have the ability to be confident."

Real example of him applying the de-risk tier, from Day 38:

> "today for example I risked half of my usual lot size... why? we had high impact news
> and we also have a bank holiday tomorrow, so odds are we were going to have relatively
> low volatility, kind of choppy market conditions... I'll probably de-risk myself this
> entire week."

### 2.6 The set size is per instrument

> "your set stop loss is going to be different for every single pair, so that's
> something you have to figure out... every pair's stop loss is going to be wider,
> smaller, based on the volatility and the volume."

### 2.7 His later, simplified version

In `Risk_Management_and_Psychology.txt` (recorded later, he is on futures by then) he
has dropped the percent calculation entirely in favor of a fixed contract count:

> "I moved away from doing like, hey, I'm going to be risking only 1% of my account
> balance per trade, and I just went to I'm going to risk this amount of contracts per
> trade... whenever I press buy, whenever I press sell, it's going to be the same amount
> of contracts for NASDAQ, and then I have the number of contracts on ES that I'm going
> to be using."

Same 1% to 3% of the account target band:

> "that doesn't mean you're risking 10% of your account balance per trade... usually the
> sweet spot is anywhere between like 1 to 3%."

Same two triggers to halve it:

> "there's a couple times when I change the contract size. So one time is if the stop
> loss is very drastically larger than usual, then I'm going to just cut the contract
> size in half. And then the other times are when we see fundamental data... I don't
> really like the way that the fundamentals are looking on the news, so what am I going
> to do? I'm just going to cut my contract size in half."

He explicitly accepts a wide-stop trade running to 3% or 4% of the account:

> "us going up to 35 ticks, that could potentially be risking like 3 or 4% of the
> account, but I'm willing to do that."

---

## 3. WHERE PROFIT IS TAKEN

Source: **Day 37 (Taking Profits)**, with the partial-exit mechanics confirmed across
his trade recaps.

### 3.1 Targets are chart levels, not a fixed multiple of the risk

> "where are we looking to take profit at? It's at our building blocks."

The "building blocks" (from Day 30) are: **liquidity (previous highs and lows), order
blocks, fair value gaps, equilibrium.** Every take profit is placed at one of those,
in the direction of the trade.

Why:

> "those are price magnets... if we see a liquidity void, price is probably going to
> draw towards there. If we see liquidity, price is probably going to draw towards
> there. Why? To fill orders. We've already proven that these price ranges are high
> confluence for price to draw towards, so why wouldn't you want to set that as your
> take profit?"

### 3.2 The first target, stated as a rule

> "I do the one higher time frame draw on liquidity on whatever execution time frame
> I'm on... let's say we take a short position on the five minute, I would probably
> scale up to the 15 minute and find the first draw on liquidity within the direction
> that we're taking the trade. That would be my first take profit."

**Rule: first take profit = the first pool of liquidity (previous high or low) on one
timeframe above the execution timeframe, in the trade's direction.**

And a floor on it:

> "most of the time my first take profit is going to be minimum one to one, okay,
> that's kind of the goal."

Then he matches the 1:1 distance to whatever chart level sits near it:

> "boom, one to one, what kind of matches up with that? Cool, this high, draw on
> liquidity, perfect, first take profit."

### 3.3 The rest of the targets

> "second take profit could literally just be this fair value gap... I usually set like
> three or four take profits. That's not really necessary, you guys can put that into
> your trading plan however many take profits you guys want. You guys can set it to,
> you know, I'm only going to have three take profits, the first take profit is going
> to be the one higher time frame draw on liquidity and then I'm going to use building
> blocks for the rest of it."

So: **3 or 4 targets typical. Target 1 is defined by rule. Targets 2 through 4 are the
next building blocks up the chart.**

Worked four-target example he draws out on a forex chart in Day 37:
1. top of the imbalance (fair value gap)
2. base of the 4-hour order block
3. the 1-hour order block
4. the liquidity high above everything

### 3.4 Do not set targets off a lower timeframe than the break of structure

> "our entry was up here, stop was slightly above here, our first take profit was this
> five minute order block, because we entered off of a five minute break of structure
> and then a one minute order block... ideally I'd like to set take profits not based
> off of one minute confluences, because higher time frame holds higher power."

**Rule: the target's timeframe must be at least the timeframe of the break of structure,
never the timeframe of the fine entry.**

### 3.5 Scaling out, in order

This is the sequence, and it is consistent across every recap in the corpus:

1. **Target 1 is reached.**
2. **Take partial profit.** The one time he states the fraction: *"after take profit one
   got hit I took off 50 of the position"* (Day 54 recap). Other recaps say "take
   partial profits off at take profit one" without a number.
3. **Move the stop to break even.** *"take profit one gets hit, we can go ahead and move
   stop loss to break even, take partial profits off at take profit one."*
   (`Data_Backed_Strategy_Everyday`)
4. **Let the remainder run to targets 2, 3, 4.**
5. **If it turns, the remainder is stopped out at break even, and that is a normal and
   acceptable outcome.** *"take profit one gets hit, take profit two gets hit, take
   profit three gets hit, we miss out on take profit four, and then the rest of our
   position gets stopped out at break even."* (`Strategy_Revealed`)

He confirms he never holds the whole thing to the last target:

> "all the way down here with our multiple take profits that would be a one to 13.5
> risk reward... would I do that? Hell no, because I take partials, because I like to
> take profits." (Day 36)

### 3.6 Realized risk-to-reward after partials

> "after taking partial profits, that would probably put us at around, I would like to
> say, like a 1 to 2 point something risk-to-reward ratio. And funny enough, that is
> pretty much what I was averaging over the last 6 months on my trades."
> (`Strategy_Revealed`)

Range he names as normal for a first target: **1:1, 1:1.5, 1:2, 1:3, 1:4, 1:5** (Day 37).

### 3.7 Where profit taking ranks

> "I think the largest thing would be daily bias, and then following that would be
> execution, and then following that it would be stop loss, and then following that it
> would be taking profits. This is kind of the least of your worries, because if you're
> getting a good execution point, odds are price is going to go in your favor."

### 3.8 Manually closing a stalled trade

He does do this, but he never states a rule with a number. The one worked example:

> "price has been consolidating for literally 2 hours, 2 and 1/2 hours now, so I'm done
> with this, so I got out of that... I'm glad that I closed out at break even essentially
> because this isn't even a trade that I would have wanted to take in the first place and
> the fact that it took so damn long..." (Day 53 recap, exited +$199)

And on holding through a weekend:

> "this is probably something we could have held over the weekend but I just don't like
> doing that, because guess what, what are the odds that this thing ends up turning
> around." (Day 36)

**No numeric rule stated. See ambiguity list.**

---

## 4. WHEN NOT TO TRADE

Source: **Day 44 (Try Not to Trade)** as the spine, plus Day 29, Day 25, Day 38,
Day 11, Day 41.

His framing, which is the whole point of the lesson:

> "go into the market not wanting to trade, and make it so in order for you to take a
> trade the market is pretty much giving you no other option but to take a trade,
> because you know so damn well that it's going to make you money. No reason to force a
> trade at all."

> "the best traders take the most days off in the market... the more days that you are
> in this market, the higher probability it is that you will lose, statistically
> speaking. So why, if my probability is already so low of me winning, why would I take
> a trade in low probability conditions in an already low probability market?"

### The stand-aside conditions, each one a hard gate

**4.1 The setup disagrees with the daily bias.** This is the headline rule of Day 44.

> "that's literally all it is, that's what we're trying to stop you guys from going
> against: trading in bad price action, and then also trading against your daily bias.
> If your daily bias says bullish but a bearish setup shows up, are you going to take
> it? Most beginners end up taking those trades and those are the losing trades that end
> up stacking up and causing them to be unprofitable."

**4.2 The higher timeframes disagree with each other.**

> "the daily is bullish but the four hour is bearish and the hourly looks like [garbage],
> don't even look at it."

> "if you look at this pair on the daily you're like oh we are bearish, but all the lower
> timeframes are saying bullish, that's probably not going to be a high probability
> trade."

**4.3 The market has no direction. Chop.**

> "when there's no sense of direction in the market... look at this, that's garbage, you
> know, that's just a whole bunch of nothing."

> "the easiest and the best and the highest probability markets that you are going to be
> trading are trending markets."

He describes the chop pattern he refuses in Day 44: break of structure that turns out to
be a sweep, then the reverse, repeatedly. *"Oh, is this gonna be a break of structure?
Nope, it's a liquidity sweep, falls. Oh, we broke structure back to the upside, psych,
gets another liquidity sweep, falls. Chop chop chop."*

**4.4 A lower timeframe move tries to change the bias.** Do not let it.

> "if a smaller time frame move changes that decision in your head, you're [messed] up,
> because the higher time frames hold higher power. Why are you switching your decision
> based on where you think market's going to go on the day because of a one minute break
> of structure, because of a five minute break of structure? A five minute break of
> structure could very well just be a 15 minute retrace. A 15 minute break of structure
> can very well just be an hourly retrace."

**4.5 High-impact news.** Named instruments of destruction, verbatim:

> "not CPI, not NFP, not FOMC, not PPI, not the high impact news, not the news that
> [messes] up the market." (Day 29)

> "that's why I don't trade news... I'm increasing my probability, I'm increasing my
> chances." (Day 44)

> "Federal chairman Powell is going up on the pulpit tomorrow, tomorrow is probably going
> to be one of the most volatile days... don't trade tomorrow and don't trade on
> Thursday." (Day 25, so the ban covers the day of AND the day after a Fed speech)

He does distinguish this from ordinary scheduled news:

> "we're talking about just like the regular red or orange folder news that you read the
> bias on. Figure it out, and if it plays into your bias you can take a trade. Or do you
> want to just be a super probable and high profitability trader and not trade on high
> impact news at all? Maybe you're still learning and you just want to completely avoid
> news altogether. That will keep your win rate very high when you're starting, that will
> give you an insane win rate." (Day 29)

**4.6 Bank holidays.**

> "don't trade tomorrow, if you trade you're literally stupid, it's a bank holiday, don't
> trade... and don't trade some random foreign exchange pair. The U.S. bank holidays
> typically slow all the markets." (Day 38)

Also, the day before a bank holiday is a de-risk day, not a normal day (Day 38, see 2.5).

**4.7 Outside your session window.**

> "if it's not during New York Stock Exchange open within that first hour and a half,
> we're not taking the trade." (Day 29)

**4.8 You already took your trade for the day.**

> "if you already took your trade for the day, leave." (Day 29)

**4.9 You already spent your daily risk budget.**

> "if you already maxed out your pre-designated risk for the day, leave." (Day 29)

**4.10 It is not your instrument.**

> "if it's not on the S&P 500 we're not taking the trade... stop looking at other forex
> pairs, stop looking at crypto, stop looking at commodities." (Day 29)

And if it is a US bank holiday and the S&P is your only instrument, that means you sit out
entirely rather than substituting another market.

**4.11 Not every confluence in the plan is present.**

> "if you don't get a liquidity sweep and a break of structure and all your confluences
> getting hit, don't take a trade." (Day 29)

**4.12 You are emotionally compromised.**

> "you're going to start to understand why you would rather take days off when you're
> least probable to actually win a trade that day, whether it's from news, whether it's
> from you breaking up with your girlfriend and it's actually emotionally bad, and if you
> lose that day you'll probably actually react to it." (Day 11)

Also: "if you've been up late." (Day 11)

**4.13 You are trying to make back money you lost.**

> "the worst thing that you can do when you're on a losing streak is to continuously try
> and make back your money. That will put you in a terrible position." (Day 41)

**4.14 If none of the boxes tick, the answer is not a smaller trade, it is no trade.**

> "if none of those things are hit, that's when you say okay, we're not trading this pair
> today, or okay we're just not trading today, because when you have a day where not every
> single one of those is checked off the list, you're trading with way lower probability."

> "stop trying to force a trade on a pair when you can cycle over to another one, and if
> you're only trading one pair, don't trade that day."

---

## 5. THE TRADING PLAN (Day 29)

He gives this as a written checklist and says to keep the sheet physically in front of
you every trading day. Structure preserved in his order.

### Section 1: Pre-designated risk

- **Are you using a set lot size, or calculating the lot size every trade?**
  He uses a set size, three tiers (2.5 above). He tells the audience to calculate.
- **What is the monetary amount you are willing to lose each day?**
  > "we know exactly how much we're losing, we know exactly how much we're going to lose,
  > so when we lose it we're not crying."
- **How many trades per day?**
  > "I recommend one trade a day, that's what I do, one trade a day. Sometimes I'll take
  > two, but when I take two I also understand my risk, I usually know that I'm willing to
  > take two that day and I de-risk on both those trades, so it pretty much equals out to
  > the risk of one trade."
  > "I would say one to two trades a day that are high probability quality setups."
  > "you guys should literally just stick to one for now."

  The sentence he tells you to literally write down:
  > "I am risking $100 every day while taking one trade a day. Period. Move on."

### Section 2: When are you trading

- **Which session.** Name it and treat it as a job.
  > "I trade New York Stock Exchange open... I take a trade within the first hour and a
  > half of New York Stock Exchange, and if I can't find a trade I'm not taking it."
- **Important distinction he draws:** the time window gates the **entry**, not the exit.
  > "that doesn't mean I close my trade after the first hour and a half of the session,
  > that just means I have to be in a trade or else I'm done."
- The options he lists: New York open (his), New York PM, London open, London close into
  New York open, Asian session (which he calls a terrible session).
  > "understand what works for your time zone, what works for your sleep schedule, what
  > works for your work schedule, and treat this like a job."

### Section 3: The news rule

- **Do you trade after news, on news, or not at all?** Written down in advance.
- He gives an example of the *form* of the rule and explicitly flags that the number is
  invented and you must choose your own:
  > "if news causes like a five point spike within a five minute candle on news, and also
  > this is just like me saying this randomly, okay, you determine this yourself because I
  > don't even know... are you going to be willing to trade that day or are you going to
  > opt out? Write that down."
- His own version: *"if news [messes] up the market I'm done for the day."*

### Section 4: What are you trading

- **One instrument. Only one, until profitable.**
  > "choose one and leave it at that, and once you turn profitable, that one, add another,
  > because anything on top of one you're adding lower probability, you're adding risk."
  > "delete your whole watch list."
- His own history, given as the reason: 5 years on GBP/USD, 4 years on GBP/JPY, 3 years on
  gold, 4 years on the S&P, and he added each one only after being profitable on the
  previous one.

### Section 5: The confluences (which combination triggers an entry)

From Day 30, ranked by his own safety ordering:

| Combination | His label |
|---|---|
| liquidity sweep + break of structure | most risky, lowest confluence |
| liquidity sweep + break of structure + order block entry | middle |
| liquidity sweep + break of structure + fair value gap entry | middle |
| liquidity sweep + break of structure + (order block OR fair value gap) + equilibrium | most safe, "foolproof plan to enter if you are a beginner" |

> "I want you to figure out what confluences you want to use, and this may take time, this
> may take backtesting... write down your win rate, write down your emotions for it."

### Section 6: Execute

> "the rest is just press the damn button... you follow every single step in your trading
> plan to the point where you are a robot, where you don't enter off anything else."

> "does it follow your trading plan? If no, leave."

---

## 6. THE LOSS AND WIN RULES

### 6.1 The hard daily stop

**One trade per day. Win or lose, the day is over.**

> "this is why just taking one trade a day is so beneficial. It's like boom, take one
> trade and just go home. Take one trade, whether it's a win or a loss, you're done,
> you're just done for the day. It makes it so much easier instead of saying, well I won
> today, I don't want to give profits back, or, oh I won today and I bet I could win more,
> and that's greed talking... instead, okay, I took my trade and I'm done, whether it's a
> win or a loss I don't give a [damn] and I'm just done." (Day 21)

The alternative form of the same limit, expressed as money instead of trade count:

> "risk one to three percent of your account per day." (Day 13)

Once that budget is spent, whether on one trade or three, the day is over.

### 6.2 After a loss

**No re-entry, no revenge trade, no size increase.** He describes his own behavior after
a $9,000 loss on the day he recorded Day 11:

> "I took a loss today, I lost nine thousand dollars today trading GU... and did I revenge
> trade, did I try and trade again, did I over leverage? No, I stuck to my rules, I stuck
> to how much I wanted to risk."

> "when I lose I don't revenge trade, I don't over trade, I don't react."

What he does instead: study the loss.

> "I love when I take a loss because I can learn from it. I get to study the market after
> my loss, say okay, why did it move the way that it moved, why did it go against me."

And the framing he insists on:

> "it's not the market's fault, it's your fault... it's never your strategy's fault, it's
> your fault, you just did not execute correctly." (Day 41)

### 6.3 What counts as a losing streak

He defines this explicitly, and his number is much larger than most people's:

> "I've lost two days this week and you guys think it's a losing streak. Definitely not a
> losing streak by all means. I would consider like two losing weeks or like three losing
> weeks a losing streak." (Day 41)

> "if you lose just like two trades, that's normal." (Day 41)

### 6.4 What he changes when a real losing streak happens

**Rule one: do not change the strategy.**

> "the first thing is you don't want to change your strategy, definitely don't change your
> strategy, because you already have this one down and you've proven to yourself that it
> works. Why would I change my strategy if it's been working for all these years? There's
> no reason to change it."

> "we're not saying the strategy doesn't work anymore, we're not saying the strategy got
> patched, because that doesn't happen. We're just saying, all right, we know what we're
> doing wrong, we see a pattern of us doing the same thing over and over and it's giving us
> bad results, so how can we tweak it a little bit."

**Rule two: make one small adjustment, and pick it by diagnosing the pattern.** He gives
two real examples of the adjustments he has actually made:

- **Adjustment A, when the instrument's price action is bad:**
  > "there was a period in time like two months ago when the S&P 500 wasn't trading that
  > well, and I was like, dude, I might just go back to forex. I went back to forex, had
  > 100K week."
- **Adjustment B, when the bias keeps being right but the entries keep getting stopped:**
  > "I'm entering on a low time frame liquidity sweep break of structure and that's it, I
  > wasn't using any extra confluence to enter, and price was usually just liquidity
  > sweeping, breaking structure, and then boom, stopping me out, and then ended up going
  > back in my direction. So what have I decided to do? Now I'm only going to take liquidity
  > sweep, break of structure, order block entry; liquidity sweep, break of structure, fair
  > value gap entry; liquidity sweep, break of structure, order block, fair value gap,
  > equilibrium entry."

  **This is a direct rule for a bot: on a losing streak, require MORE confluence before
  entering, not fewer trades of the same quality.** He confirmed the result the following
  week in Day 46: *"last week I was only taking like liquidity sweep break of structure and
  we lost literally every single trade that we took last week, but this week I was waiting
  for a liquidity sweep break of structure order block entry, fair value gap entry, to give
  me more confluence... and that helped us one, avoid a loss today, and two, make me a lot
  of money today."*

**Rule three: be more patient while it lasts.**

> "I want to be patient, I don't want to force a trade, I want to let the trades come to me,
> and if I don't see anything I'm not going to take it."

### 6.5 After a win, and after a win streak

**A win does not earn another trade.** Same one-trade rule as a loss (6.1).

**Expect a loss immediately after a run of wins.**

> "when I'm on a win streak, I almost am encouraging a loss, I almost want to see a loss
> come, because it'll prove to me that I'm human again. When I'm on a win streak and I'm
> winning trade, winning trade, winning trade, lots of money, lots of money, that can get
> into your head really really quick. So if anything, when that's happening, I'm like, I
> know a loss is coming, I know a loss is coming, I'm realistic, I know a loss is coming,
> I'm not perfect in these markets... so I can't get ahead of myself." (Day 25)

**Never increase size after a win.** He names this as the exact mistake he made:

> "I was profitable on demo and then boom, go into a live account and just get screwed
> because I knew I was using real money and I wanted to make a lot of money, so I was like,
> well, I already know how to trade, I was profitable on demo, let me just up my leverage a
> little bit and we'll do it a lot faster. No. Remember what got you to the point that
> you're at." (Day 25)

> "why would you change anything once you've proven to yourself that you're profitable? ...
> why would you stray away from the [stuff] that got you there?" (Day 25)

**Review the win the same way you review a loss.**

> "on wins it's a lot harder to find areas for improvement, but that's what I'm encouraging
> you guys to look for. If you guys can sit down and be like, yeah I won, but I could have
> done this better, it'll only make your wins a lot better and your losses will be even more
> minimal." (Day 46)

### 6.6 Take every valid setup

The counterweight to all the stand-aside rules. Skipping a valid signal is itself a failure:

> "follow your process without hesitation. You have to define your strategy specifically and
> you have to take every single valid setup, because if you don't take every single valid
> setup, then you are losing probability that your strategy gives you. You have to manage
> your risk identically each time." (Trading_Psychology_9_Years, lesson 9)

> "every single trade that you take is unique. Even if the setup looks identical, the
> participants, the orders, and the order flow are different. Never assume that the next
> trade must behave like the last one." (lesson 8)

---

## 7. HOW HE BACKTESTS (Day 42)

### 7.1 He rejects bar replay, and says why

> "if I'm being real, bar replay is not necessarily the best way to backtest. In my eyes the
> best way to backtest is just purely going back on a full chart, just going back to a random
> day, scrolling down and saying, boom, let's start here, and let's just analyze top down."

His stated reason, which is a **look-ahead problem**:

> "on bar replay you are pretty much set to one time frame, because let's say you go bar
> replay on the 15 minute... if we go to daily and want to see the daily bias it shows you the
> full daily candle. If we want to go to the four hour and see what our four hour bias should
> be, it's going to show you the full four hour candle. If we even want to go to the hourly and
> see our hourly bias, it shows you the full hourly candle... that's the issue with bar replay,
> it's not live data."

Consequence he draws from it:

> "odds are, when you go back on bar replay you're probably going to get a worse win rate on
> bar replay than you would in live markets."

### 7.2 What he counts as evidence

**Live market results. Demo if you cannot go live. Not replay.**

> "the best way to test your strategy is through live market."

> "I always like to judge my trading ability based purely off of live markets. If you want to
> test, live test on demo using your strategy, but when you're backtesting, just do target
> practice."

His second reason for preferring live is that replay strips out the thing that actually breaks
traders:

> "another thing with backtesting, it doesn't bring the emotions in, because candles as they're
> forming, it's going up down up down, creating its wicks and it's scaring you. That's causing
> emotions... versus on bar replay it's going bar, next bar, next bar."

### 7.3 What his "backtest" actually is

Pattern-recognition drilling, not a statistical run.

> "just do target practice, right, boom, go on the daily, what, break of structure, cool,
> what's this, order block, cool, enter... it's these types of things that you just want to get
> good at."

The concrete homework standard he sets, repeated across Day 32, Day 33 and Day 42:

> "find 10 examples of a liquidity sweep and break of structure and just look at what happens
> afterwards... then I want you to find liquidity sweep, break of structure, order block entry,
> [10 examples]... you're going to find ten examples of liquidity sweep, break of structure,
> fair value gap... and then ten examples of [the equilibrium version]."

Weekend routine:

> "go back over the previous week, every single day, find one or two good trades that you could
> have taken on a pair, and then find all of our building blocks throughout those days."

The purpose he assigns to it is not a win rate. It is confidence:

> "this is all I want you guys to be doing, just building the confidence that these things work
> day in and day out and they are on every single time frame."

### 7.4 The record he actually keeps: the journal (Day 46)

Columns, in his order:

1. **Pair** (one only)
2. **Session** (New York or London; he discourages Asian)
3. **Confluences** written out in sentence form, including what the daily, 4-hour, 1-hour, and
   15-minute were each saying, and which building block on which timeframe he entered off
4. **Risk** as percent of the account. *"Ideally, it's 1 to 3%. If it's anything more, you're
   immediately doing something wrong."*
5. **Did you follow your plan?** Yes or no, written out with the reason
6. **Emotions** you felt, and **why** you felt them
7. **How could you improve?** Filled in on wins as well as losses

> "if you didn't follow your plan, write down what you didn't follow, and odds are if you didn't
> follow your plan, you probably lost."

### 7.5 The measurement standard he names elsewhere

From `Trading_Psychology_9_Years`, the two conditions he says make a strategy worth trading:

> "our strategy gives us a higher probability of being right than being wrong... and when we
> win, we are making more than when we lose."

> "if I have a strategy that I know for a fact gives me a 70% win rate and a 1:1.5
> risk-to-reward ratio every single time I take those trades, then as long as I take that
> strategy word for word, bar for bar, step by step every single time, I know for an absolute
> fact that those probabilities are going to play out over a long period of time and I will be
> net positive."

*(The 70% and 1:1.5 are given as an illustration of the arithmetic, not as a claim about his
actual numbers. His actual stated average from `Strategy_Revealed` is "around 1 to 2 point
something risk-to-reward" over six months after partials.)*

He also names the tool he uses to get the statistics: a trading journal service that connects
to the broker (he names TradeZella).

---

## 8. BAR-BY-BAR CHECKLIST FOR AN OPEN POSITION

Everything below runs **after** a position is open. Entry logic belongs to the other briefs.

### 8.0 Set at fill time, once

```
entry            = fill price
sweep_extreme    = the high (short) or low (long) of the swept level,
                   on the timeframe that was treated as the setup's sweep
buffer           = broker spread on this instrument, cleared
                   (he names "0.5 points" as a floor; "4" on his S&P example)
stop             = sweep_extreme + buffer   (short)
                 = sweep_extreme - buffer   (long)
risk_per_unit    = |entry - stop|
size             = (account * risk_pct) / risk_per_unit
                   where risk_pct = 1% of the account on a normal day
                                    0.5% of the account on a de-risk day
                   (see 8.6 for what makes it a de-risk day)
tp1              = first liquidity pool on ONE timeframe above the execution
                   timeframe, in the trade's direction, floor of 1:1
tp2..tp4         = the next building blocks (liquidity, order block, fair value
                   gap) beyond tp1, on the break-of-structure timeframe or higher
be_moved         = false
partial_taken    = false
```

### 8.1 On every closed bar, in this order

```
1.  if stop is hit
        -> position closed. Go to 8.4 (post-loss) or 8.5 if be_moved was true.

2.  if tp1 is reached AND partial_taken == false
        -> close 50% of the position          [his stated fraction, Day 54]
        -> move stop to entry (break even)
        -> partial_taken = true; be_moved = true
        -> continue holding the remaining 50%

3.  if tp2 / tp3 / tp4 is reached
        -> close the planned fraction of the remainder at each
        -> stop stays at break even; it is NOT trailed further
           (no trailing rule is stated anywhere in the corpus)

4.  if the final target is reached
        -> position closed flat. Go to 8.5.

5.  otherwise
        -> hold. Do not close for being in profit. Do not close for being in
           drawdown. The stop and the targets are the only exits.
```

### 8.2 Things that must NEVER happen while the position is open

- The stop is never widened, moved away, or removed. Ever. (`Trading_Psychology_9_Years`,
  lesson 7.)
- The stop is never moved to break even *before* tp1 is reached.
- Size is never added to an open position. No averaging in, no scaling up.
- The position is never closed early because it is a large dollar number. *"I had $330,000
  floating in profit where my stop loss was at break even and I could have closed it and I
  didn't because I had to stick to my plan."*
- The targets are never extended while the trade is live. Day 46 lists *"did you keep
  extending your take profit"* as an emotion failure to journal.

### 8.3 The one discretionary exit he actually uses (no numeric rule stated)

He has closed a trade manually when it consolidated for 2 to 2.5 hours without resolving, and
he refuses to hold a position over a weekend. **NEEDS VIDEO for a bar count or a clock time.**
If a time-based exit is implemented, it must be flagged as our parameter, not his.

### 8.4 Circuit breakers, with exact triggers

| # | Trigger | Action | Source |
|---|---|---|---|
| CB-1 | 1 trade has been opened today | No further entries today, win or lose | Day 21, Day 29 |
| CB-2 | Cumulative risk committed today reaches 1% to 3% of the account (the plan's chosen number) | No further entries today | Day 13 |
| CB-3 | A position closed at a loss today | No re-entry, no revenge trade, no size increase. Day is over per CB-1 | Day 11 |
| CB-4 | A position closed at a win today | No second trade, no size increase | Day 21, Day 25 |
| CB-5 | Two or more consecutive **losing weeks** | Declare a losing streak. Do NOT change strategy. Require MORE confluence on entries: from (sweep + break of structure) up to (sweep + break of structure + order block or fair value gap), and optionally + equilibrium | Day 41, Day 46 |
| CB-6 | The instrument's price action has been unreadable/choppy for a sustained period | Stand the instrument down, move to another instrument you already know, or do not trade | Day 41, Day 44 |
| CB-7 | High-impact news scheduled today (CPI, NFP, FOMC, PPI, Fed chair speaking) | No trade | Day 29, Day 25 |
| CB-8 | The day AFTER a Fed chair speech | No trade | Day 25 |
| CB-9 | US bank holiday | No trade on any instrument | Day 38 |
| CB-10 | Day before a bank holiday, or any day with high-impact news where a trade is still allowed | Size drops to 0.5x normal (de-risk tier) | Day 38, Day 39 |
| CB-11 | Outside the session window (his: first 90 minutes of the New York open) | No new entry. Existing positions are NOT closed by the clock | Day 29 |
| CB-12 | The setup disagrees with the daily bias | No trade | Day 44 |
| CB-13 | The daily, 4-hour and 1-hour disagree with each other | No trade | Day 44 |
| CB-14 | Any required confluence in the plan is missing | No trade | Day 29 |
| CB-15 | Not the instrument in the plan | No trade. Do not substitute another market | Day 29 |

### 8.5 After the position closes (either outcome)

```
1.  Journal the trade with all seven Day-46 fields.
2.  Record risk as a percent OF THE ACCOUNT, not a dollar amount.
3.  Record: did it follow the plan, yes or no, and which step failed if no.
4.  Score by win rate and by average risk-to-reward across many trades,
    never by the outcome of the single trade.
5.  Do not re-enter today (CB-1).
```

### 8.6 The size ladder as a lookup

```
de_risk    = 0.5 x normal   -> high-impact news day, bank-holiday-adjacent day,
                               expected chop or low volume
normal     = 1.0 x normal   -> no news, or news that will not move the market
confident  = 2.0 x normal   -> no news, setup he likes, every timeframe bias
                               aligned. He forbids this tier to anyone not
                               already proven profitable.
```

If the set-lot method is used instead of resizing per trade, the fixed size is calibrated to
the **narrowest** typical stop for that instrument at 1% of the account, and the realized risk
is allowed to float upward with a wider stop: 2x the stop distance means 2% of the account,
3x means 3% of the account. He states that in practice it "never" reaches 3%.

---

## 9. WHAT IS GENUINELY AMBIGUOUS AND NEEDS THE VIDEO RE-WATCHED

Machine transcripts of a man talking over a chart. These are the places where the rule is
real but the number or the pixel is not recoverable from text.

1. **The spread buffer number (Day 38).** The transcript reads *"like five like point five
   points 0.5 points below"* and then *"ours was like what was it, it was four four below."*
   Whether the general floor is 0.5 points and the S&P example was 4 points, or whether he said
   0.4, cannot be resolved from the text. **The rule is not in doubt (clear the broker's spread);
   the number is.** Watch Day 38 around the trade review.

2. **Wick or body at the swept level.** He says "above the liquidity sweep" and "above the
   highs" and never says the word "body." A liquidity sweep is by definition a wick beyond a
   prior extreme, so the extreme reached is almost certainly the reference. But he never states
   it, and he draws it on screen. **Day 38 needs watching to confirm whether the stop sits
   beyond the wick tip of the sweep candle or beyond the swept prior high itself.** Those are
   different prices.

3. **Which prior high is "the liquidity sweep" when several were taken.** In the Day 38 example
   he identifies "the 5-minute sweep" by pointing. With multiple nested sweeps a bot needs a
   selection rule and he does not state one in words.

4. **The partial fraction at each target.** 50% at target 1 is stated once, in the Day 54 recap.
   Every other recap says "take partial profits" with no number. **What comes off at targets 2,
   3 and 4 is never stated.** Watch a full recap start to finish.

5. **How many targets, and whether 3 or 4 is his default.** He says *"I usually set like three
   or four take profits"* and then says it is up to your plan. No fixed answer.

6. **The stalled-trade exit.** He closed a trade after 2 to 2.5 hours of consolidation and calls
   holding over a weekend something he "just doesn't like doing." No bar count, no clock time,
   no structural trigger. This is the biggest genuine hole for automation.

7. **His news threshold.** He tells you to write down a rule of the form "if news causes an X
   point spike inside a five-minute candle, I am out for the day" and says outright *"this is
   just like me saying this randomly, you determine this yourself because I don't even know."*
   **There is no TJR number here to copy. Ours will be ours.**

8. **Percent-of-account risk per trade vs per day.** Day 13 states 1% to 3% of the account both
   ways in the same lesson. With his one-trade-per-day rule the two collapse to the same thing,
   but if a bot takes two trades in a day the interpretation matters.

9. **The set-lot method versus a fixed 1% of the account.** These are two different sizing
   engines and he uses the first while telling the audience to use the second. Which one we
   implement is our call; both are his.

10. **Whether the stop trails past break even.** Nothing in the corpus says it does, and several
    recaps end with *"the rest of our position got stopped out at break even"* after the trade
    ran through multiple targets, which implies it does not. But he never says "I do not trail"
    out loud. Worth confirming on a long-runner recap.
