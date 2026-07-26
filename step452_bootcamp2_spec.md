# Step 452 — Boot Camp 2.0: the spec, and what it settles

Source: `tjr_transcripts/bootcamp2/`, 14 files, ~40,500 words. Every file read in full.
Compared against the original 56-day course in `tjr_transcripts/bootcamp/` and the
standalone videos in `tjr_transcripts/`.

Governing rule, already in force from `step436_spec_conflicts_resolved.md`: **where the
newer teaching contradicts the older course, the newer wins.** Boot Camp 2.0 is the newer
teaching. This document is transcription of what he says, not a judgement of it.

Filenames are offset by one from the day numbers he speaks. Throughout this document the
day number is HIS, and the file is named next to it the first time each is cited.

A note on the word "leverage". Day 9 is titled "Leveraging Risk" and it is **not** about
exchange leverage. He uses "leverage" to mean "make the most of". The lesson is about
spreading the day's risk budget across more than one trade. He says nothing anywhere in
Boot Camp 2.0 about how much margin to post or what leverage number to select. See item 2.

---

## PART A — the six things we invented, checked one at a time

---

### 1. What fraction comes off at each target

**HIS RULE, now stated: 50% of the position at target 1, then 50% of what is STILL OPEN at
target 2, then the remainder is closed by hand on an opposite break of structure on the
1-minute chart.**

The anchor, Day 9 "Leveraging Risk" (`Day10_...Day 9： Leveraging Risk.txt`):

> "we had take profit one right here where I managed 50 of the position we had take
> profit two right here where I managed another fifty percent of the open position and
> then I closed the rest of the trade out once we broke structure to the downside on the
> one minute"

"Of the open position" is said twice more, in the same words:

Day 7 "Risk Management and Probabilities" (`Day08_...`):
> "first take profit was just like a simple one-to-one RR off that I closed fifty percent
> of the open position there and move stop to break even"

Day 5.5 "Second Trade" (`Day06_...`):
> "I've already taken half of this position off and stops at break even so this is a
> risk-free trade now"

So the ladder, in shares of the ORIGINAL position:

| Target | Share of what is open | Share of the original position |
|---|---|---|
| 1 | 50% | 50% |
| 2 | 50% | 25% |
| 3+ | closed by hand, or stopped at break even | 25% |

**VERDICT: FILLS A GAP, and CONTRADICTS what we built.**

Ours today, `/Users/wallacechen/cryptobot/tjr_bot.py` `target_fractions()` line 1294:

```python
rest = (1.0 - cfg.partial_fraction) / (n - 1)
return [cfg.partial_fraction] + [rest] * (n - 1)
```

With 4 targets that is 50%, 16.7%, 16.7%, 16.7% of the original. His is 50%, 25%, then a
managed 25%. The docstring at line 1300 already flags the tail as ours and a guess. It is
answered now.

Two further points from Day 9 that our exit path does not do:

- The last piece is **not** left sitting on a resting target. He closes it manually when
  the 1-minute breaks structure against him. His stated reason is partly convenience
  ("I just didn't want to sit on the Discord call much longer"), and he judges it right
  after the fact. This is the same manual-close behaviour the old course described in
  `step433_tjr_spec_management.md` section 3.8.
- He runs **four and sometimes five** targets, not three. Day 9: "we have take profit
  three right here and then take profit four all the way up here". Day 11 "Where to Take
  Profit" (`Day12_...`): "I also had several other take profits like four and five all the
  way up here if it wanted to hit some high time frame highs".

---

### 2. Leverage, and how much margin to post

**HE STILL SAYS NOTHING.** Day 9 "Leveraging Risk" does not contain a margin rule, a
leverage number, or a position-notional rule. Day 3 "Risk" does not either.

The only two places the word appears in its exchange sense:

Day 4 "Best Forex Broker" (`Day04_...`), on the broker's 100% deposit match:
> "they're just giving you extra liquidity to put in your account so they're just giving
> you more money to play with more money to trade with to give you guys more leverage
> okay and whether that's a good thing or a bad thing you decide me personally I'm not
> going to do this because I'm trading with a lot of money anyways"

Day 3 "Risk", used only as a criticism:
> "when you enter a trade and you're over risk and you're over leveraged and you lose and
> you get emotional that means that you were emotionally attached to that money"

What he DOES give is size in broker units, twice, which tells us the shape of his sizing
but not our margin question. Day 3:

> "for me I have a fixed lot size for me I'm usually trading like a hundred to like 150
> Lots on a Forex trade right how much should I do on this I did 25. 25 Lots"

**VERDICT: NO CHANGE. Our 10% margin share stays OURS.**
`/Users/wallacechen/cryptobot/venue.py` `BlofinVenue.PER_TRADE_MARGIN_SHARE = 0.10` and
the note in `tjr_alerts.py` `margin_share()` that he never specifies it both remain
accurate. Leverage as an output of size divided by margin budget, per
`step446_leverage.md`, is untouched by Boot Camp 2.0.

**However — item 4 below settles the thing Day 9 IS actually about, and that is the more
valuable answer.**

---

### 3. The ceiling on how much one trade may cost

**HIS BAND IS CONFIRMED, AND THE UNIT IS CORRECTED: 1% to 3% of the account is a
PER-DAY budget, not a per-trade ceiling.**

Day 8 "How to split positions" (`Day09_...`), talking about a day where he lost on one
trade and won on another:

> "I only lost 50 percent of what I was willing to risk on the day that's better than a
> full you know like one percent down on the day two percent down or three percent down
> on the day"

The 1%, 2% and 3% figures are all attached to "on the day". This matches the old course
exactly, Day 13 "Risk Management": *"risk one to three percent of your account per day
that just makes it easy"*. Boot Camp 2.0 does not contradict it, it uses it operationally.

**His own daily budget can be recovered from the numbers he says out loud.** Day 8:

> "I lost 10 10 grand on gu like that's that's around like 50 of what I'm willing to lose
> in a day"

and later the same video, on where the day finished net:

> "ended up losing like 0.25 percent um lost like five grand"

A quarter of one percent of the account being five thousand dollars puts the account near
two million dollars. His daily budget of twenty thousand dollars is then one percent of
the account. Day 3 independently gives the same twenty thousand: *"my usual risk tolerance
is around like 20 grand"*. **So his own working number is the bottom of the band: about 1%
of the account at risk per day, with the band's top of 3% as the outer limit.**

Also from Day 3, the de-risked size he actually used that day, and the fact that he treats
sub-1% trades as practice:

> "I did 0.25 risk on this because we had a bunch of U.S news"
> "anything lower than a one percent trade I'm like all right like we're just doing this
> to get reps in"

**VERDICT: CONFIRMS the 1-3% band. CONTRADICTS the unit we implemented it in.**

Ours today, `/Users/wallacechen/cryptobot/tjr_alerts.py` line 190:

```python
MAX_RISK_SHARE_OF_ACCOUNT = 0.03
```

enforced per trade in `position_size()` lines 276-282. The block comment there says the
cap is ours and he has not answered on it. He has now answered, and the answer is that
3% is a day budget. Our cap has the right number on the wrong axis: it lets a single
trade spend the entire day's outer limit, which is the exact mistake Day 8 and Day 9 are
warning against.

---

### 4. More than one trade in a day — THE BIGGEST FILL IN THIS COURSE

**HIS RULE, stated as an explicit procedure across Day 8 and Day 9.**

Step one, Day 8 "How to split positions". When you can see a second setup forming, you
cut the first trade's size so the two together spend one day's budget:

> "if you do have two trades that you are able to take during the day make sure your risk
> plan is like set up and ready for that so for me when I see like two or three trade
> setups for the day like today right I lost 10 grand on gu like that's around like 50 of
> what I'm willing to lose in a day so I pretty much was like okay cool like I'm going to
> go in with like half of what I would want to risk on the day knowing damn well that I'm
> probably going to take a second trade"

and the summary line for the whole lesson:

> "how to leverage your risk management so you're able to take two positions a day like I
> did today and still be risking the same amount as if it were one trade"

Step two, Day 9 "Leveraging Risk". Once target 1 hits on the first trade and the stop is
at break even, the first trade can no longer cost the full amount, so the budget it was
holding is released:

> "I only risked 50 of what I was willing to risk for the day"
> "we lost 50 of what we were willing to lose once take profit one got hit okay now we're
> down to like 25 of what we were willing to lose for the day"
> "that gives me the ability to now know that hey the most I'm going to lose on the day is
> going to be 25 I can now risk an extra 75 of whatever I'm willing to risk on the day"
> "if I risk 75 of what I'm willing to risk on the day and I'm only down 25 of what I'm
> willing to risk on the day with stop loss at break even on this s p trade cool then if
> this one hits stop loss then I'll lose 100 of what I'm willing to risk on the day"

So the accounting is: **committed-plus-realized loss on the day may never exceed the day's
budget, and a trade that has taken profit at target 1 and moved its stop to break even
stops consuming budget.**

Step three, Day 8, how to CHOOSE when several setups compete. He names three tests and
gives them in order:

> "you want to choose whichever trades give you the best risk to reward have the most
> Confluence and whichever one is you like fully within the the daily bias"
> "which one has more confluences which one is more in line with your daily bias and which
> one gives a better risk reward those are kind of the top three ones that I would cycle
> through in my head"

The worked example is arithmetic on the reward, not on feel. He dropped one setup because
its first target was under a one-to-one:

> "the best it was going to give me was a one to one or actually when I mapped it out it
> was like a one to like 0.7... that's not worth it to me when gu is giving me like a one
> two 1.5 on my first take profit and these are practically the same trade setups I'm just
> taking the one that's giving me a better RR"

Step four, the cap on count. He gives no hard number, but the counts he actually ran are
on the record: two on Day 8, **three on Day 9** ("we took three trades today, absurd for
me"), and **four on Day 12 "Red Day"**. Day 8 phrases the split for three:

> "let's say you got like three and two of them are higher probability than the other
> there's no reason to take all three just split those positions up amongst those two
> trades"

**VERDICT: FILLS A GAP AND CONTRADICTS what we built.**

Ours today: a hard one-trade-per-day, not a named constant but a structural consequence of
`/Users/wallacechen/cryptobot/tjr_bot.py` `run_day()` lines 1388-1442 (single `trade`
variable, `break` on outcome), plus `tjr_gold.py` line 525 and `tjr_crypto.py` line 587.
There is no daily risk budget anywhere in the codebase, and no halving of size when a
second setup is expected. Spec item CB-2 in `step433_tjr_spec_management.md` line 1027
describes the budget but nothing implements it.

Note this does **not** contradict the old course as much as it looks. Old Day 29
"Trading Plan" already said: *"I recommend one trade a day, that's what I do, one trade a
day, sometimes I'll take two, but when I take two I also understand my risk, I usually
know that I'm willing to take two that day and I de-risk on both those trades so it pretty
much equals out to the risk of one trade."* Boot Camp 2.0 quantifies that sentence and
adds the budget-release step. **Boot Camp 2.0 governs.**

---

### 5. What to do after a losing day

**HIS RULE: nothing. A red day changes no setting. He kept trading the same day, at the
same size, and would have accepted a fourth loss.**

Day 12 "Red Day" (`Day13_...`) is the file, and it is the opposite of a stand-down rule.
He took three losses, then took a fourth trade:

> "if this was a fourth loss I would have been completely okay with it on my side"
> "I'm able to deal with four losses because I know how much I'm risking and I understand
> risk management"

The only thing he changed was that he did not post the fourth trade to the paid Discord,
and he says plainly this is a signal-group concern and not a trading rule:

> "you got to understand like I got to keep you guys in mind... a lot of these people who
> are in Signal groups or live trading rooms are very stupid when it comes to risk
> management so if anything I'm protecting the stupid people"

And on the following week, no tightening, no size cut:

> "starting off the week not so great but over the past three weeks been killing it
> looking to eat back all these Ls that we took today"

Day 3 "Risk" says the same about longer runs:

> "I could have three losing months in a row and still feel completely fine and completely
> satisfied with my win rate"

**VERDICT: CONFIRMS what we have. No change.**

Our losing-WEEKS escalation survives untouched:
`/Users/wallacechen/cryptobot/tjr_bot.py` line 175
`losing_weeks_to_escalate: int = 2`, which flips the 5-minute pullback requirement from
midpoint-or-gap to midpoint-and-gap at `SymbolDay.on_5m` line 1132. Boot Camp 2.0 gives no
newer teaching on losing weeks, so the old-course source ("two losing weeks or like three
losing weeks", old Day 41) stands.

And confirming the absence: we have **no** red-day halt in code, and Boot Camp 2.0 says we
should not add one. The thing that ends his day is the risk budget from item 4, not the
count of losses.

**One real stand-down rule does appear, and it is about news, not losses.** Day 13
"I Made $ on a Bad Trade" (`Day14_...`), standing down for a whole week in advance:

> "make sure you don't trade tomorrow or the following day we have CPI tomorrow we got PPI
> on Thursday and we got heavy news on Friday... we got news an hour before Market open 15
> minute before Market open and 30 minutes in the market open I might not trade for the
> rest of this week"

Day 5 "How to find Trade Bias" (`Day05_...`) walks the same week ahead in advance and
marks each day:

> "on Tuesday we have a bunch of US news, I probably will not end up trading that day"
> "Wednesday... it's NFP week... all happening an hour before market open... I will
> probably end up taking a trade on this day just because all the big news is happening an
> hour before market open"
> "Friday... non-farm employment change... unemployment rate an hour before market open,
> and then ISM manufacturing PMI and then ISM manufacturing prices 30 minutes into market
> open. That's just too much high impact news on the day for me to be willing to trade."

The discriminator is stated exactly: **news released an hour or more before the open is
tradeable, news released inside the session is not.**

---

### 6. Where profit is taken

**CONFIRMED: chart levels, no fixed multiple. Plus two new details.**

Day 11 "Where to Take Profit" is unambiguous:

> "sometimes I see Traders setting like take profits based off of Fibonacci levels set off
> of like random [stuff] I like to set take profits based off of high Confluence areas
> where price will, if it hits that price, it could cause a reaction back down in the
> other direction"
> "we don't know exactly where it's going to want to reject off of or turn around or
> change direction which is why we set multiple take profits"

**New detail A — where a target sits relative to a swept high.** This is a placement rule
we do not have. If a high was swept and a leg down followed, the orders were filled ABOVE
that high, so the target goes above the high, not at it:

> "this was a liquidity sweep then a leg down so technically this high is not where orders
> were filled, orders were filled above this high so with that in mind it's just an easier
> way for me to be able to set take profits... because sometimes you'll see hey why didn't
> price come up and sweep this high, it's because everything from this high and above is
> where previous downward orders were able to get filled"

**New detail B — the reason for multiple targets is timeframe mismatch, and he states the
beginner rule.** Executing on a small chart inside a large-chart move means the large
chart's levels will cause swings you cannot sit through:

> "this is why I highly recommend early and beginner traders to set multiple take profits
> and move their stop-loss break even as much as possible"
> "if you get good risks rewards secure some profit and move your stop to break even so
> you don't give any money back to the market"

**On 1:1 as the first target.** Day 7 "Risk Management and Probabilities" shows him doing
exactly what our code does:

> "first take profit was just like a simple one-to-one RR off that I closed fifty percent
> of the open position there and move stop to break even"

Our `build_targets()` in `tjr_bot.py` lines 1236-1292 uses one-to-one as a floor and then
picks the first real chart level at or past it, refusing to invent a price. That behaviour
is confirmed, including the refusal: if nothing sits at or past one-to-one it returns
nothing and no trade is taken, which matches him dropping the setup whose best first target
was "a one to like 0.7".

**VERDICT: CONFIRMS. Two placement details to add.**

---

## PART B — also captured

### Which broker, and why (Day 4 "Best Forex Broker")

He moved off Hankotrade to **AirFX**, on **MetaTrader 5**. His stated reasons, in his own
order:

1. **Offshore and unregulated is deliberate, not a compromise.**
   > "it's an unregulated offshore brokerage. Newsflash, literally every single foreign
   > exchange brokerage that allows you to trade Majors, miners, indexes, Futures,
   > Commodities, energies, literally all that stuff, crypto, on your foreign exchange
   > brokerage, it has to be offshore and it has to be unregulated. And also on top of
   > that, regulated Forex Brokers suck. You have to follow U.S rules."

2. **Raw spreads with a commission, over zero commission.** He picks paying the fee to get
   the fill:
   > "you either have to choose between a raw spread account or a zero commission account.
   > I'll probably go with raw spreads just because I would much rather have money get
   > taken out from commission rather than getting a trash fill. I would rather get filled
   > at the point where I actually enter versus having zero commission and then getting a
   > bad fill."

3. **Withdrawal speed.** 15-minute crypto withdrawals versus a day and a half at his
   previous broker.

4. **One account covering everything.** Majors, minors, exotics, energies, indexes,
   futures, metals, stocks and crypto on one platform:
   > "let's say I want to day trade crypto now, boom, I can just do it on the same account
   > that I trade Forex on"
   He also says he keeps long-term holdings somewhere separate from the trading account.

5. **MetaTrader 5 for two specific mechanics.** Buy and sell from the chart itself so you
   never leave the 5-minute view, and **drag the stop to break even with the mouse and let
   the platform compute the price**:
   > "when you move your stop loss to break even, instead of having to figure out where was
   > my entry price, you literally click on your stop loss and then you can drag it to your
   > break even, it does all the numbers for you"

6. **Bots are allowed.** "you can use EAs, trading Bots, whatever you guys want."

**Bearing on our venue choice.** We currently arm crypto on BloFin demo and leave Alpaca
paper unarmed for stocks and gold (`/Users/wallacechen/cryptobot/tjr_desk.py` lines 137,
269, 309, 340), while `step435_venue_decision.md` says the opposite. Boot Camp 2.0 does not
name BloFin or Alpaca. What it does supply is his ranking of what matters in a venue:
**fill quality first and pay the fee for it, then withdrawal speed, then one account for
all instruments, then a platform that makes moving the stop to break even a single action.**
Fill quality ranking above fee is directly relevant, and it points the same way as the
standing instruction to charge real costs but never let cost decide a trade.

### What a GOOD loss looks like (Day 6 "Best Loss to Take", Day 10, Day 1)

This gives us a scoring rule for our own losing trades. Day 6 (`Day07_...`):

> "these are the trades that we want to lose, when market literally just changes direction.
> We did everything to our knowledge correctly, we waited for all of our confluences, we
> waited for price to come into this accumulation area, we waited for price to break
> structure to the upside, we waited for price to come back into this area, we waited for
> price to react off it, we actually waited an extra two candles to get an actual reaction,
> and then we targeted highs... however what did price do, it dumped"
> "probably the best loss that I've taken in a while"

Day 10 "Trade Recaps" (`Day11_...`) states it as a checklist:

> "if you can execute and have all of your confluences get hit within your same bias, you
> execute off of it, you have a good risk to reward, you have a good trade set up,
> everything looks good, and then the one thing that goes wrong isn't a stupid mistake,
> isn't a stop-loss placement mistake, it's literally just price changing direction, those
> are the losses that you want to take"

Day 1 names the counterpart, the BAD loss:

> "the losses that you don't want to be taking are the ones where you're like, damn, should
> have waited for an extra Confluence, or, damn, I shouldn't have taken this because the
> daily wasn't in line with my bias and the hourly wasn't in line with my bias but the four
> hour was and the 15 minute was, it was mixed biases on multiple time frames"

So a loss is **bad** if any of these is true, and each appears as a named self-criticism in
2.0:
- entered on two confluences without the third (Day 9, Day 12, Day 13)
- the stop was not under a real invalidation point (Day 9: "I didn't place my stop loss
  completely under an invalidation point"; Day 8: he widened the stop mid-trade and calls
  it "added a little bit more risk on the table")
- entered into consolidation rather than after a break out of it (Day 1, Day 13)
- the high that was broken was not a **prominent** high (Day 8)
- biases disagreed across timeframes (Day 1)

### Winning can also be a bad trade (Day 13 "I Made $ on a Bad Trade")

The judgement is on the process, not the money. He took profit and still grades the trade
down, and grades the LOSING trade of the same day higher:

> "even though we hit take profit and even though I covered for the loss that I took on the
> s p, I was more satisfied with my bias on the S P than the winning trade that I took on
> gu"
> "would I want to take that type of trade again, probably not"
> "I was stuck in drawdown and just sitting in this trade for like an hour 30 minutes... in
> reality I could have literally just logged off the charts and not have taken this and
> still been equally satisfied with my day"

And the ordering of what matters, which matches the old course:

> "the hardest part in trading, it's the execution and then stop loss, but bias, that's
> something that if you can get right then you should be a profitable Trader, because
> executions you'll hit and you'll miss sometimes, but if you can get the bias down every
> single day then that's how you're going to be a profitable Trader"

---

## PART C — every number he says out loud

| Number | Where | What it is |
|---|---|---|
| 50% of the position | Day 5.5, 7, 9, 10, 12 | closed at target 1 |
| 50% of the **open** position | Day 7, Day 9 | closed at target 2, so 25% of the original |
| 4, sometimes 5 targets | Day 9, Day 11 | how many take profits he sets |
| 1% to 3% of the account | Day 8 | risk **per day**, not per trade |
| about 1% of the account | Day 3, Day 8 (arithmetic) | his own working daily budget; $20k on roughly a $2M account |
| 50% of the day's budget | Day 8, Day 9 | size of trade 1 when a second setup is expected |
| 25% of the day's budget | Day 9 | exposure left after trade 1 takes target 1 and stops to break even |
| 75% of the day's budget | Day 9 | what is then free for trade 2 |
| 100% of the day's budget | Day 9 | the ceiling the two trades together may reach |
| 0.25% of the account | Day 3, Day 8 | de-risked size on a heavy news day; also the size of a net losing day |
| 0.5% of the account | Day 7 | size when there is no news but he is unsure of the chart |
| 50% of usual size | Day 7 | high impact news released inside the session |
| 75% of usual size | Day 7 | one release, an hour before the open |
| more than usual size | Day 7 | no news, all biases agree, clean setup |
| 100 to 150 lots | Day 3 | his normal forex size |
| 25 lots | Day 3 | the de-risked version of it |
| 4 pips | Day 1, Day 3, Day 13 | buffer beyond the swept level for the stop, forex |
| 2 pips | Day 13 | extra buffer "for comfort" on a wider structural stop |
| 5 points | Day 9 | a stop he calls too tight and blames for the loss, S&P |
| 2.7 points | Day 13 | the distance by which a correct-bias trade missed |
| 24 pips | Day 2 | full stop distance on a forex trade |
| 11 pips | Day 2 | how far into that stop the move went before people panicked, under half |
| 3 confluences | Day 1, 9, 12, 13 | the entry requirement; entering on 2 is the named mistake |
| 1 to 1 | Day 7, Day 8 | first target when a chart level sits there |
| 1 to 1.5 | Day 8 | first target on the setup he chose over a 1-to-0.7 |
| 1 to 0.7 | Day 8 | the reward that made him drop a setup |
| 1 to 5.8 | Day 9 | full ladder on the trade he liked most |
| 3 trades | Day 9 | count he took, and calls "absurd for me" |
| 4 trades | Day 12 | count he took on a losing day |
| 09:30 | Day 5 | he does not trade before the New York open |
| 1 hour before the open | Day 5, Day 7 | news released this early is tradeable |
| 15 and 30 minutes into the open | Day 5, Day 13 | news released this late means stand down |
| 2 or 3 losing weeks | old Day 41, unchanged in 2.0 | what counts as a losing streak |
| 3 losing months | Day 3 | what he says he could absorb without changing anything |
| 98%, 99%, 99.5% | Day 1, Day 11, Day 12 | his shifting figure for how many traders fail; rhetorical, not a parameter |

---

## PART D — NEEDS VIDEO

These rules depend on something drawn on screen and cannot be pinned from the text.

1. **"Prominent high."** Day 8 turns on it entirely: *"technically I would have wanted to
   wait for this high, this prominent High, to get pushed above. This high that we pushed
   above technically wasn't a prominent High."* The distinction decides whether a break of
   structure counts. He points at four highs on screen and calls three of them prominent.
   The word appears nowhere in our codebase. **NEEDS VIDEO.**

2. **"Area of accumulation" as the new entry basis.** Every 2.0 recap uses it in place of
   the order block, and he defers the definition to a separate video four separate times
   ("I'll make a video on this later", "that new strategy video should be coming out to you
   guys today"). His verbal definition is *"the leg down that was able to fill those orders
   prior to that move up"*, which is close to an order block but not identical, and he says
   so: *"this order block or this area of accumulation, whatever you'd like to call it."*
   **NEEDS VIDEO** for the exact marking rule. Note `step436` section 1 retired order
   blocks; whether that retirement extends to this needs the video.

3. **Where targets 3, 4 and 5 sat on the Day 11 chart.** He says he had them and points at
   them, but never names the level type for anything past target 2.

4. **The stop buffer outside forex.** 4 pips is stated for forex. The S&P example is given
   only as a mistake ("just a five point stop loss... this loss could have been avoided if
   I set my stop loss all the way under here"). No number is given for what it should have
   been.

---

## PART E — what must change in our code, in priority order

1. **`/Users/wallacechen/cryptobot/tjr_bot.py` `run_day()` (lines 1388-1442), plus
   `tjr_gold.py` line 525 and `tjr_crypto.py` line 587.**
   Replaces: the hard one-trade-per-day stop, which is a structural consequence of the
   single `trade` variable and the `break` on outcome.
   With: a per-day risk budget. Trades continue while committed-plus-realized loss stays
   inside the day's budget. First trade takes half the budget when a second setup is
   plausible; a trade whose stop has moved to break even after target 1 stops consuming
   budget. Source: Day 8 and Day 9, quoted in item 4.

2. **`/Users/wallacechen/cryptobot/tjr_bot.py` `target_fractions()` (lines 1294-1313).**
   Replaces: `[0.50, 0.1667, 0.1667, 0.1667]`, the even spread of the tail, marked in the
   docstring as ours and a guess.
   With: 50% of the position at target 1, then 50% of what is still open at each target
   after it, so 50 / 25 / 12.5 / 12.5 of the original. Source: Day 9, "another fifty
   percent of the open position".

3. **`/Users/wallacechen/cryptobot/tjr_alerts.py` line 190,
   `MAX_RISK_SHARE_OF_ACCOUNT = 0.03`, enforced in `position_size()` lines 276-282.**
   Replaces: a 3%-of-account ceiling applied to each trade independently.
   With: the same 3% as a ceiling on the DAY, with about 1% as the normal daily figure.
   Per-trade size then falls out of the day budget and how many setups are expected.
   Source: Day 8, "one percent down on the day, two percent down or three percent down on
   the day".

4. **`/Users/wallacechen/cryptobot/tjr_desk.py` `_manage()` (lines 585-605).**
   Replaces: a two-leg exit only, half at target 1 and the entire remainder at target 2.
   Targets 3 and 4 never fire on the live path.
   With: the full ladder from change 2, plus the manual close of the last piece on an
   opposite break of structure on the 1-minute. Source: Day 9, "I closed the rest of the
   trade out once we broke structure to the downside on the one minute".

5. **`/Users/wallacechen/cryptobot/tjr_bot.py` `build_targets()` (lines 1236-1292).**
   Adds, does not replace: when the level being targeted is a high that was itself swept
   before a leg down, place the target ABOVE that high rather than at it, because that is
   where the fills sat. Mirror for lows. Source: Day 11, "orders were filled above this
   high". Everything else in this function is confirmed as written.

6. **`/Users/wallacechen/cryptobot/tjr_bot.py` `Config` news tier and
   `news_calendar.py`.**
   Adds: the release-time discriminator. News an hour or more before the open leaves the
   day tradeable at reduced size; news 15 or 30 minutes before, or inside the session,
   stands the day down. Our current `derisks()` / `blocks()` split is by event type, not by
   clock time. Also consider the week-ahead stand-down: he calls a whole week off in
   advance when three heavy days sit in it. Source: Day 5, Day 7, Day 13.

7. **NO CHANGE, confirmed by 2.0. Do not add a red-day halt.**
   `tjr_bot.py` line 175 `losing_weeks_to_escalate = 2` and the pullback tightening at
   `SymbolDay.on_5m` line 1132 both stand. There is deliberately no per-day loss halt in
   the code and Day 12 says there should not be one.

8. **Flag, not a Boot Camp 2.0 finding, surfaced while checking item 3.**
   The bot has two different sizing rules. `tjr_bot.py` `_open()` lines 1486-1487 sizes
   fresh at 1% every trade for replay and backtest, while the live path in
   `tjr_alerts.py` `position_size()` uses the fixed set-size capped at 3%. Whatever we do
   for change 3, these two should end up on the same rule or every backtest number we have
   describes a bot we are not running.
