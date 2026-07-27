# TJR: Daily Bias, Timing, and the Assembled Strategy
## A build specification, transcribed from his own words

**What this is.** A transcription of what TJR says he does. Not an evaluation. Where he
states a number, the number is here. Where a rule depends on something only visible on
screen, it is marked **NEEDS VIDEO** rather than guessed at.

**Sources (this file's cluster only).** All under `/Users/wallacechen/cryptobot/tjr_transcripts/`:

| Short name used below | File |
|---|---|
| **UPDATED-2026** | `UPDATED_Day_Trading_Strategy_2026.txt` (also timestamped as `updated_strategy_2026.txt`, video `8PYgFVB0GHE`), **the current version, wins all conflicts** |
| **BIAS-STEPS** | `How_To_Find_Daily_Bias_Step_By_Step.txt` (video `e_FV0Q14k8E`) |
| **BIAS-P2P** | `How_To_Find_Daily_Bias.txt` (video `ironJFzNBic`) |
| **TIME** | `Time_Theory_Explained.txt` (video `L4xz2o23aPQ`, timestamped twin `p2p_time_theory.txt`) |
| **STRAT-P2P** | `TJR_Strategy_Explained.txt` (video `TEp3a-7GUds`), the older Path-to-Profitability strategy video |
| **Day34/35/36** | `bootcamp/Day34…Daily Bias.txt`, `Day35…Daily Bias pt. 2.txt`, `Day36…Daily Bias pt. 3.txt` |

Entries, sweeps, break of structure, fair value gaps, order blocks, equilibrium, stops,
targets and position size are **other agents' spec files**, this one says *where each of
those slots into the day*, not how each is drawn.

**All times below are US Eastern.** He states this explicitly:
> "we have open, right, which is at 9:30 a.m. Eastern time. Again, we're operating on
> Eastern time, okay?" (TIME, ~[0:03:22])

---

# 1. DAILY BIAS: the procedure

There are **two different procedures** in the cluster. They are not versions of one
another with a clean winner: the newer one is his stated everyday method, the older one
is the bootcamp top-down method. Both are recorded. A bot should implement **Procedure A**
as primary, because it is the one he describes as "how I've been finding my daily bias
recently" and it is the one he actually runs in the live worked examples.

## 1A. PROCEDURE A: the previous-session profile method (current, primary)

Source: BIAS-STEPS. His own summary of the whole thing:

> "I look at the daily profile. I look at the previous session. I identify my high time
> frame draws on liquidity and then from there I'm looking at what daily profile happens
> out of these draws and liquidity and then from there all I do is target the draws in the
> other direction."

**The ordered checklist:**

**Step 1: Mark the levels that price gets pulled toward.** These are highs and lows on
higher timeframes plus session extremes. He lists exactly:
- 1-hour highs and 1-hour lows
- 4-hour highs and 4-hour lows
- Session highs and session lows, specifically **Asia session high/low** and
  **London session high/low** (he uses a session high/low indicator; red lines = Asia,
  blue lines = London)
- Previous day high and previous day low

> "We're going to mark out the highs and lows on the 1 hour, on the 4 hour, and the session
> highs and lows. So, for me, since I'm trading New York session, I'm marking out London
> session highs and lows. I'm marking out Asian session highs and lows. And then we can
> also mark out previous day previous day highs and lows as well."

A level that has already been pushed through with no reaction is dead and should be
dropped:
> "Asia session high had already been pushed past London session highs and there was no
> reaction off of it. So, in turn, that draw on liquidity is pretty useless for us."
> (STRAT-P2P)

**Step 2: Classify what the PREVIOUS session did.** For a New York trader the previous
session is **London**. He insists there are only three possibilities, and calls them daily
profiles:

| # | Profile | What it means | What you then expect New York to do |
|---|---|---|---|
| 1 | **Previous session consolidation** | London did **not** push through any of the marked higher-timeframe levels | New York **manipulates** (pushes through a level) **and then reverses** |
| 2 | **Previous session manipulation, no reversal yet** | London pushed through a marked level but did not turn back | New York delivers the **reversal** |
| 3 | **Previous session manipulation + reversal** | London pushed through a level AND already turned back off it | New York **continues** that same direction |

> "Did the previous session consolidate? And by consolidation, it doesn't mean it just has
> to go sideways. It just means there's no form of manipulation."

> "It's literally it's one per session." So classify exactly one profile per session, and
> do not re-label it mid-session.

**Step 3: The direction of the bias falls out of the profile.**
- Profile 1 or 2 (a reversal is expected): once New York pushes through a level, bias is
  **the opposite way**, targeting the marked levels on the other side.
- Profile 3 (continuation expected): bias is **the same way London was already going**.

> "obviously if we're getting manipulation of lows in a reversal, we're going to want to
> target what? Highs."

**Step 4: on a CONTINUATION day, still require a smaller-timeframe push-through before
entering.** This is the exception he says he almost forgot and calls "super important":

> "If we're in a London session manipulation reversal, we still have to expect some form of
> manipulation… because new money is coming into the market during New York session…
> There still has to be manipulation. It's just going to be on the lower time frames. So,
> we're going to look to mark out five minute lows and like 15 minute lows."

So on a continuation day: mark **5-minute and 15-minute** highs/lows and wait for one of
those to get pushed through before entering, instead of waiting for a session-level
push-through.

> "I'm not just pressing buy right here because I know that new money is coming into the
> market and we're going to have to manipulate."

**Step 5: Targets are the marked levels in the opposite direction.**
> "target the draws in the other direction."

### What makes there be NO bias / no trade under Procedure A
Procedure A itself does not produce a "no bias" state, one of the three profiles always
applies ("there's literally no other way that price could move"). The **no-trade** filters
live in the strategy (section 5) and in news (section 3), not in the bias step. The two
he states in this cluster:
- High-impact news day → he tries not to trade (section 3).
- The two indexes disagreeing → no trade (section 5, UPDATED-2026).

## 1B. PROCEDURE B: the top-down trend method (bootcamp, older)

Source: Day34, Day35, Day36. This is a different mechanism: it reads **trend / market
structure on descending timeframes** rather than previous-session profiles.

**Order of timeframes, explicitly stated:**

1. **Weekly**, "start on the weekly time frame figure out where is Price going on the
   weekly." He is explicit this is orientation only for a day trader: "that's just giving
   US Weekly bias and we don't really care about that because we're trading day to day…
   for me I don't care about that too much." Its one real job: if the daily has broken
   down but the weekly is still going up, treat the daily move as a pullback inside the
   weekly move.
2. **Daily: this is where the bias is set.** "I like to use the daily current market
   structure to figure out my daily bias." Up-structure on the daily → look for buys.
   Down-structure on the daily → look for sells. A structure break on the daily flips it:
   "we get a breaker structure to the downside so I'm bearish on the daily prior to this
   candle to the downside I would have been bullish not anymore."
3. **4-hour**, agreement check. Where the daily and the 4-hour disagree he says the day
   gets tricky and he restrains his targets: "we cannot Target these absurd long time
   frame take profits because we haven't been proved to the downside on the four hour…
   we need to be tentative with our take profits."
4. **1-hour**, where he looks for the levels/confluences to act on.
5. **15-minute then 5-minute**, execution. "find that liquidity sweep on the 15 minute
   find the break of structure on the five minute."

**The nesting rule he repeats** (needed so a bot doesn't flip bias on noise):
> "15 minute break of structure one hour retrace, one hour regular structure four hour
> retrace, four hour break of structure daily retrace, daily breakup structure weekly
> retrace, higher time frame holds higher power."
> "a one minute break of structure could very well just be a five minute retrace bro."

**Aligned-timeframes is his best case** (Day35, on his live bullish S&P read:)
> "the hourly's in an uptrend the four hour's in an uptrend the daily is in an uptrend the
> Weekly's in an uptrend 15 minutes in an uptrend."

**Where the two procedures differ** (record both, do not merge):
- A: previous-session behaviour vs the marked levels. B: nested trend direction.
- A never yields "no bias". B does, when the daily and the 4-hour point opposite ways he
  either stands down or shrinks the target ("today is a perfect example of when we probably
  wouldn't want to trade the S&P 500 unless we can find some sort of bearish confirmation").
- B uses the weekly and monthly; A does not mention them at all.

## 1C. The mid-era bias reasoning (BIAS-P2P)

BIAS-P2P sits between the two. It uses higher-timeframe trend + where the marked levels
are + whether continuation levels get respected. Two rules from it worth having:

- **Respect vs disrespect of a continuation level is the bias switch.** If the market is
  falling and comes back up into an hourly gap, then *respects* it and turns down, bias
  stays down. If it *closes through* it instead, bias flips.
  > "It closed above this gap, signaling to me, hey, price wants to go higher. We just
  > invalidated this hourly gap. And if we wanted to go lower, we would have respected it."
- **The rhythm he expects all day**: "we move from external to internal, external to
  internal", push through a high/low, pull back into a gap or the midpoint, push again.

**Bias can be wrong and that is allowed.** From STRAT-P2P, a day where he came in bullish
and the market went the other way:
> "I did have a bullish bias today, but what did the market do? The market proved me wrong
> and instead did what it wanted to do… we can let the market prove us wrong and we can
> still make money."
A bot must therefore treat the bias as a lean, and let the entry sequence (section 5)
override it, not as a hard direction lock.

---

## 1D. What he ACTUALLY did on real mornings (Days 47–55): and how it differs

This matters, because the mandate is to check the stated procedure against live behaviour.
**On every live morning in the bootcamp files he runs Procedure B, not Procedure A.** He
does not once say "London consolidated, so New York manipulates and reverses." He walks
weekly → daily → 4-hour → 1-hour per instrument and reports whether they agree.

The live pattern, repeated almost word-for-word across five mornings:

| Morning | What he actually said |
|---|---|
| Day49 (PPI) | S&P: "weekly bullish, daily bullish… 4-hour bullish, 1-hour bullish" → mock long. GJ: "bullish on the weekly. However, we are bearish on the daily" → "I wouldn't necessarily want to take a trade off of this." Gold: daily bullish but 1-hour and 4-hour broke down → "This is a day where we wouldn't want to trade gold." |
| Day50 | S&P: "bullish on the daily bullish on the weekly bullish on the four hour… one hour is bullish." GJ: "bullish on the four hour but bearish on the daily so odds that we take a trade off this relatively low" → "this can go to the bottom of my list today." |
| Day53 | S&P: "daily in an uptrend, but the 4-hour in a downtrend… ideally, we kind of just sit this one out." Gold: "daily's bullish, weekly's bearish, 4-hour's bearish, 1-hour's bearish. I'm not looking to really take a trade on this." |
| Day54 | GJ: "bearish on the daily still bearish on the weekly… reacting off this bearish order block right now so ideally we're looking for shorts" → the $19k trade. |
| Day55 | S&P: "we're bullish on the 1-hour and the 4-hour… everything's saying bullish. So, we'll look for buys." GU: "4 hours bearish, daily's bullish, weekly's bullish… this is probably one that I'll just completely avoid altogether." |

### The live agreement rule: the real no-bias / no-trade test
This is the rule the live mornings actually turn on, and it is stated plainly:

> "ideally we see daily and the four hour in confluence and the one hour, but most of the
> time **at least I need the daily and the four hour to be in confluence**." (Day50)

And when the daily and 4-hour disagree, he stands down or downgrades the instrument. Day55
is the cleanest statement of it, where he talks himself out of a gold short:
> "I said, 'Wait, that would be breaking our trading plan.'… why was it against our trading
> plan? Cuz we were bearish on the hourly. We were bullish on the daily, bullish on the
> 4-hour. **No reason to take a trade that's purely based off of our hourly price action**
> when we can just wait for something better to show up."

### Which timeframe wins when they conflict
The **daily** sets the bias, because the daily is the move he is trying to capture:
> "bearish on the weekly, but bullish on the daily, so what bias are we going to be using?
> We're going to be using the **daily bias** because we are trying to predict the daily
> moves… We're not swing trading, we're doing intraday trades." (Day49)

And a lower-timeframe break against the daily is read as a pullback, not a flip:
> "if the 15 minute is breaking structure to the downside and the hourly is bullish it's
> probably going to be a retrace… **higher time frames hold higher power**." (Day47)
> "we never want to trade retraces unless it's on like the weekly time frame… most of our
> trades are in line with the daily." (Day49)

### Bias is held until price breaks it, and losing that way is the intended way to lose
> "we're going to stick to this bias until we're proved wrong and that's really when you
> should be losing trades, your goal should be to lose trades based on **high time frame
> reversals**, not based off of **execution errors**." (Day50)

He also names the conditions that would flip a bias intraday, which a bot can use:
> "I would be willing to flip my bias if we get 15 minute high formed and then a close
> above, that's when I would be looking for a trade to enter." (Day54)

### Levels marked on the live mornings
Consistent with Procedure A's list, even though the reasoning is Procedure B's: London
session high/low, Asia session high/low, previous-day levels, 1-hour and 4-hour highs/lows,
15-minute levels, plus the confluence areas that belong to the other spec files (order
blocks, gaps, equilibrium). Day50 records a working preference:
> "what I've been noticing lately I kind of like using **hourly** building blocks compared
> to **15 minute** building blocks on the S&P, tends to work out a bit better."

### How to reconcile the two for a build
They are not actually contradictory in effect; they answer different questions.
- **Procedure B answers "am I allowed to trade this instrument today, and which way."**
  (daily and 4-hour must agree; daily wins; disagreement = stand down)
- **Procedure A answers "what is New York specifically going to do off the levels this
  morning."** (previous-session profile → manipulate-and-reverse vs continue)

Recommended build: run **both**, and require them not to contradict. That is a
reconstruction on our part and is flagged as such, **he never says to combine them.**

---

# 2. SESSION AND TIMING RULES

All Eastern. Source: TIME unless noted.

## 2A. The session clock

| Session | Hours (Eastern) | His words |
|---|---|---|
| Asia | **18:00 → 03:00** | "It starts at 1800, and it goes till 3:00" |
| London pre-market | **02:00** | "London session pre-market actually opens at 2:00" |
| London | **03:00 → 08:30** | "London session goes from 3:00 till 8:30" |
| New York pre-market | **08:30 → 09:30** | "New York pre-market opens at 8:30" |
| New York regular | **09:30 → 17:00** | "we go from 9:30 all the way to 1700" |
| Spread hour, untradeable | **17:00 → 18:00** | "the gap between 1700 and 1800 is what we call spread hour, where there is no market that is open… you will see the spreads on every single pair get very, very large. It's because there's no money in the market" |

He truncates each session at the next one's open on purpose:
> "Technically, London session goes till 11:30 New York time, but we want to end all of
> these sessions when the next one is opening."

**Conflict on the pre-market open: record both.** TIME says 08:30. BIAS-STEPS says 08:00:
> "technically at 8 is when New York pre-market opens. Okay, so pre-market opens at 8."
The verification file's current guess of 08:30 matches TIME (the dedicated timing video),
and 08:30 is also where he places the high-impact news release. **NEEDS VIDEO** to settle
whether 08:00 is a slip or a genuine revision.

## 2B. The intraday clock: this is the part a bot actually runs

| Window (Eastern) | What it is | His words |
|---|---|---|
| **09:30** | Market open | "we have open, right, which is at 9:30 a.m. Eastern time" |
| **09:30 → 09:50** | **Manipulation window**, expect the push through a level here | "what I call our manipulation time frame, which is from 9:30 to 9:50" |
| **09:50 → 10:10** | **Entry window**, the ideal entry | "from 9:50 to 10:10, we have our entry period… That's called the macro… Typically, the ideal entry time" |
| **10:30** | **HARD CUT-OFF: no new trades** | "if I can't find a trade by 10:30, I'm done for the day, because that's when the market tends to slow down" |
| **13:00** | PM session opens, **he does not trade it** | "We also have PM session that opens at around 1:00 p.m. Me, personally, I don't trade this" |

**The windows are soft edges, the cut-off is not.** He says explicitly the entry can land
outside 09:50–10:10:
> "this doesn't have to be point-blank period, like we can only look to enter at 9:50 to
> 10:10. That's not the case. I take trades at 10:20 sometimes. I take trades at 9:45
> sometimes."
And an example where the push-through arrived late: "we finally see the final leg of
manipulation happening a little bit later at 9:52… the manipulation was just 2 minutes
later than our typical manipulation time frame."

The 10:30 cut-off is restated independently in UPDATED-2026 at [0:53:30], tied to the
index-disagreement rule:
> "at this point in time, it's 10:20. By 10:30, I'm done for the freaking day. If neither
> of the indexes are aligned and it's 10:20 on the freaking timer on the Eastern Eastern
> time zone, call it a freaking day."

He then shows a valid setup at **11:05** and declines it on grounds of not wanting to sit
through the chop, so the 10:30 rule is a preference, consistently held, not a mechanical
impossibility:
> "sure we can target these highs for like a 1 to 1 risk-to-reward ratio. Sure, it played
> out in our favor. But me personally, I'm not willing to sit through all of this chop and
> all of this BS to take this trade at 11:20."

## 2C. Which windows are for marking, which are for trading

- **Asia and London: marking only.** He does not trade them on the indexes. Their job is
  to produce the session highs/lows he marks and to supply the previous-session profile.
  Day34: "are we gonna trade that hell no it's the S&P 500 who's trading the S&P during
  London session."
- **New York pre-market (08:30–09:30): watching only, never entering.** Stated flatly in
  UPDATED-2026 on a day where the whole setup formed in pre-market:
  > "Do we want to be entering during pre-market? The answer is always going to be no. I
  > want to wait until price actually until market actually opens and like gives us some
  > real volume."
  Pre-market price action still *counts*, it can be the push-through that sets up a
  09:30+ entry.
- **New York 09:30–10:30: the trading window.** Everything he takes lives here.
- **After 10:30: done.** After 17:00: nothing is open.

**Why open matters at all**, in his framing: a session open brings "new money" in, and new
money has to push through a level before the real move.
> "I'm always looking to trade right at market opens… because I know that that's when
> there's going to be volume and volatility coming into the market." (BIAS-STEPS)

---

# 3. NEWS

Sources: bootcamp Day19 (the dedicated news lesson), Day47 (CPI), Day49 (PPI), Day43 and
Day51 (the weekly news review), Day50, Day55.

## 3A. Where the schedule comes from
> "where do I get my news from it is called Forex Factory okay so I literally just go
> forexfactory.com" (Day19)

He filters it down before reading it:
- **Drops the yellow (low-impact) entries entirely**: "these yellow folders these are just
  random stupid news events that happen day in and day out that don't really affect the
  market… so I get rid of those."
- **Keeps the grey ones** because they flag bank holidays and non-trading days.
- **Filters to only the currencies behind what he trades.** For the S&P: "your S&P 500 news
  events will be covered by USD."
- The site auto-converts to local time: "it automatically like connects to whatever time
  zone you're on."

## 3B. The hard block list: four releases, no trading at all

> "there's a couple news events that I always avoid you guys should write these down
> **CPI PPI FOMC and NFP** those four… those four I will not I do not trade whatsoever"
> (Day19)

> "if it's CPI PPI FOMC or NFP just call it quits bro sleep in live to trade another day
> don't lose your money you're trading in unprofitable conditions" (Day19)

This is the one genuinely hard, schedulable, bot-implementable news rule in the cluster.
It is honoured in practice repeatedly:
- Day47: CPI day, "we did not trade today."
- Day49: "the reason why we didn't want to trade today was we had core PPI, PPI,
  unemployment claims" (he notes a Fed member speaking the same day "wasn't really any of
  my concerns", **a scheduled Fed speaker alone does not block the day; the three data
  releases did**).
- Day43, planning the week ahead: "we have CPI on Wednesday so I likely will not be trading
  that day."

His stated reason on CPI specifically is that the move is gone before he could take it:
> "the reason why I don't like trading on CPI because most the time the move has already
> been made… CPI comes out makes a 27 point move versus… a four point move" (Day47)
> "you're getting a super low volatility move… you're trading way later into the session
> than you need to be" (Day47)

## 3C. The rule for every OTHER red/orange release: wait, then judge

This is the soft rule, and it is time-shaped enough to code:

> "if there is a red news folder no matter what I will always always always **wait until
> the news comes out**" (Day19)

Then a **15–20 minute observation window** after the release:
> "if news doesn't affect the market for like after like 15 or 20 minutes after it comes
> out so at like 8:45 or like at 8:50 if news didn't affect the market I would have been
> okay to trade" (Day19 (a release at 08:30 → clear to consider trading at 08:45–08:50))

The judgement he applies at the end of that window:
> "always wait for news to come out let price develop see if it drastically affected the
> market you know with **large wicks large moves** okay and if it does that **don't trade**…
> and if it doesn't okay you can potentially look for a trade but still be playing on that
> defensive side" (Day19)

**NEEDS VIDEO / genuinely under-specified:** "drastically affected" and "large wicks, large
moves" are never given a number. A bot needs a threshold and the transcripts do not supply
one.

And if he does trade after news, he cuts size:
> "I should probably risk less I should probably reduce my risk… so de-risk yourself from
> the market when there's big news" (Day19)

## 3D. Release times he states

| Release | Time (Eastern) | Source quote |
|---|---|---|
| CPI / PPI / unemployment claims | **08:30**, i.e. "an hour before market open" | Day43: "those news events they happen an hour before Market opens"; Day51: "all of that is pre-market, hour before market open"; Day19 implies 08:30 via "8:45 or 8:50" being 15–20 min after |
| Some releases | **09:15**, "15 minutes before market open" | Day51 |
| Consumer sentiment / existing home sales | **10:00**, "30 minutes into market open" | Day50: "prelim consumer sentiment that comes out 30 minutes in the market to open so that's something to keep in mind we won't be trading until then"; Day51: "we'll wait 30 minutes into market open for the existing home sales news data" |
| GBP-pair news (weekly-plan example) | **11:00** "U.S. time" | Day43 |

**The 10:00 release is the awkward one for a bot**, because it collides with the entry
window. He describes exactly what he does:
> "we have news that comes out 30 minutes into market open, market opens at 9:30 for me:
> boom news comes out at 10. what am I going to do I'm going to sit on my hands… and I
> will not trade until 10 a.m. hits and I'm and I still won't trade until like 10:30 hits
> because we need price to develop" (Day19)

So on a 10:00-release day the practical tradable window collapses to roughly **10:30**,
which is also his cut-off. That is close to a no-trade day by construction.

## 3E. Other stand-downs he mentions
- **Whole weeks**: Day19, "I probably won't trade on Thursday either because look we have
  one red folder two red folder three red folder four red folder… and all of these are for
  USD so if anything I'll probably only be looking at like GJ on Thursday." (When the USD
  calendar is stacked he switches to a non-USD instrument rather than forcing the index.)
- **Government shutdown**: Strategy_Revealed, "The government is currently shut down. So,
  I've been kind of avoiding trading this week." Stated as behaviour, not codified.
- **War news**: BIAS-STEPS, "I'm not going to be trading today because we had war news that
  came out during Asian session." He still does the bias exercise, just doesn't trade.
- **Pair-specific**: Day51, "CPI on Wednesday, so I will definitely be avoiding GBP/USD
  and GBP/JPY." Day55, GBP CPI landed in London session, so he avoided the pound pairs
  and considered waiting for Asia instead.

## 3F. How he reads the number itself (for completeness: he says he does not trade on it)

> "if the actual is greater than the forecast then it is good for the currency" (Day19)

Then the inversion, because good for the US dollar is bad for the things he trades:
> "when the DXY goes up anything against the dollar goes down so gold… the S&P will follow
> down… good for the dollar bad for SPX" (Day19)
> "whatever's on top it's positive correlation whatever's on bottom it's just inversed"

But he explicitly refuses to trade off this read:
> "that's why we can't necessarily trust news bias because **price action is superior**
> that's why we have to wait for news to come out" (Day19)

**A bot should therefore NOT use the news number to set direction.** It is a filter on
whether to trade at all, not an input to bias.

---

# 4. WHAT HE ACTUALLY TRADES

## Instruments
**Primary and current: the two US index futures, together.**
> "I trade the indexes. I trade the S&P 500 and NASDAQ." (BIAS-STEPS)
> "if we're trading the S&P 500 and Nasdaq, which is what I'm teaching you guys how to do
> within this series" (TIME)

He refers to them as **ES** (S&P 500) and **NASDAQ/NQ**, and in UPDATED-2026 he switches
which one he takes the trade on based on which one produced the setup:
> "even though we didn't get the manipulation on ES, that's why I actually took the trade
> on NASDAQ."
> "As long as one of the indexes is doing it for us, that's all we need."

**Both charts are required, not optional**, see the alignment rule in section 5.

**Other markets he names.** In the bootcamp era he actively traded and analysed
**gold**, **GBPUSD** ("gu") and **GBPJPY** ("GJ") alongside the S&P (Day35, Day36; the
Day54 recap is a GBPJPY trade). Day01: his original edge was GBPJPY at the London open:
"all I would do was trade GJ and I noticed that right when London session would open it
would fake the [f***] out and then it would go in the opposite direction."

He states the method is market-agnostic as long as you shift which session you watch:
> "Some of you guys, you guys may trade Euro EuroUSD. You guys may trade gold… The same
> thing applies. We're just looking at the past session that had just passed."
> "regardless of if I'm trading an index or if I'm trading forex or if I'm trading a
> commodity such as gold, I'm going to want to be trading at a market open." (BIAS-STEPS)

One index-only caveat he flags: the two-index cross-check (and the divergence confluence
built on it) is by construction unavailable outside the S&P/NASDAQ pair.

## Timeframes: analysis versus execution

| Timeframe | Used for |
|---|---|
| Weekly / Monthly | Orientation only, bootcamp method (Procedure B); absent from the current method |
| **Daily** | Sets the bias in Procedure B |
| **4-hour** | Marking levels (4h highs/lows); trend agreement check |
| **1-hour** | Marking levels (1h highs/lows); trend agreement check |
| **15-minute** | Marking the smaller levels on a continuation day; bootcamp execution timeframe |
| **5-minute** | **The main execution timeframe.** The push-through confirmation and the pullback both get read here |
| **1-minute** | **The trigger timeframe.** The final entry signal only |

His own compression of the whole thing in UPDATED-2026:
> "We're looking for a liquidity sweep, 5 minute break of structure. Then we're looking for
> a one minute break of structure to the upside and then one minute break of structure to
> the downside. Awesome. We're entering right there."

Note the older STRAT-P2P explicitly refuses to name a fixed timeframe order:
> "I'm not going to be like, 'Hey, you look at this time frame first and then you look down
> on this time frame'"
whereas UPDATED-2026 does fix it. **Use UPDATED-2026.**

---

# 5. THE ASSEMBLED STRATEGY: one ordered procedure

**Primary source: UPDATED-2026.** Where the older videos disagree, the difference is
recorded at the end of this section under "What changed."

His own four steps, in his numbering. The detail of *how* to draw each confluence belongs
to the other spec files; this is the order and the gating.

---

### BEFORE 09:30: preparation (no orders, ever)

**P1. News gate.** Check the calendar (section 3). CPI, PPI, FOMC or NFP today → **stand
down, no trading.** Any other red/orange release → note its clock time; do not trade before
it lands, then observe 15–20 minutes.

**P2. Daily bias.** Run section 1. Get a lean (up / down) and the instrument-level
permission (daily and 4-hour agreeing).

**P3. Mark the levels.** 1-hour highs/lows, 4-hour highs/lows, Asia session high/low,
London session high/low, previous day high/low. These serve double duty, entry triggers
and profit targets:
> "our exit and our entries are based off of the same exact thing." (UPDATED-2026)

**P4. Load BOTH index charts.** S&P 500 and NASDAQ, side by side. Required, not optional.

---

### STEP 1: a marked level gets pushed through ("manipulation")

> "Step number one, I'm looking for draws on liquidity… session highs, session lows,
> 1 hour highs, 1 hour lows, 4 hour highs, 4 hour lows… I'm looking for price to take out a
> draw on liquidity. And then from there, I'm looking for price to manipulate and then
> reverse off of that."

Expected window: **09:30–09:50** (section 2B). Only one index needs to do it:
> "even though we didn't get the manipulation on ES, that's why I actually took the trade
> on NASDAQ… As long as one of the indexes is doing it for us, that's all we need."

**The pre-market special case (his "step 2B", from the older videos and consistent with
UPDATED-2026's no-pre-market-entry rule).** If the higher-timeframe level got pushed
through *before* 09:30, that does not count as your trigger, you need a fresh, smaller
push-through after the open:
> "When the high time frame liquidity sweep happens during pre-market… I am always going
> to wait for a low time frame manipulation… we need to be waiting for another form of
> **five-minute** manipulation." (Strategy_Revealed)
> "Do we want to be entering during pre-market? The answer is always going to be no."
> (UPDATED-2026)

---

### STEP 2: the 5-minute turn ("confirmation the orders were filled")

> "step number two… I'm looking for confirmation that those orders were filled through a
> change in trend. So what does that typically look like? I'm looking for a **five-minute
> break of structure** or a **five-minute inverse fair value gap**."

Direction is the opposite of the push-through: level broken upward → look for the 5-minute
turn **down**; level broken downward → look for the 5-minute turn **up**.

**Break of structure, in his own definition** (needed verbatim because a bot must code it):
> "a break of structure to the upside is a **candlestick closure above the most recent
> high** that was made within the market. And then a break of structure to the downside is
> when we see a **candle closure underneath the most recent low**."

**≡ GATE: the two indexes must agree here.** This is the single biggest addition in
UPDATED-2026:
> "I do not like and I would highly recommend you guys don't take trades when the two
> indexes are not aligned… if ES is bullish on the five minute and NASDAQ is bearish, I
> don't want to take the trade. Now why is that? Because if both the indexes are telling
> us two different things, then the market is probably indecisive."
> "until both of them can be aligned… I don't want to take a trade."

They may align later in the session, and that is fine, but the 10:30 cut-off still binds:
> "If the indexes weren't aligned at the start of the session, that's fine. They can still
> get aligned later in the session. So, let's look for it."
> "at this point in time, it's 10:20. By 10:30, I'm done for the freaking day."

---

### STEP 3: the 5-minute pullback ("continuation confluence")

> "step number three is going to be a **five-minute continuation confluence** which is
> either going to be **equilibrium** or a **fair value gap** getting filled."

Do not enter on the step-2 signal itself:
> "I'm not just going to enter right here when I see the inverse value gap. No, I want to
> see some form of a retrace."
> "A lot of people will probably enter here, but that's going to cause you guys to get a
> horrible entry and probably get you guys scared when we end up making this retrace."

---

### STEP 4: the 1-minute trigger (the entry)

He gives two equivalent formulations. The simplified one is the one to build:

**Formulation A (his simplification, UPDATED-2026):**
> "we can even make this even simpler… We're looking for a liquidity sweep, 5-minute break
> of structure. Then we're looking for a **one minute break of structure to the upside and
> then one minute break of structure to the downside.** Awesome. We're entering right
> there." (for a short; mirrored for a long)

The 1-minute counter-move *is* how he detects that the 5-minute pullback happened:
> "On the one minute time frame, what I like to do is I like to classify five minute
> retraces as a break of structure to the upside on the one minute."

**Formulation B (fuller, matches STRAT-P2P and the older videos):** wait for the 5-minute
pullback into equilibrium or the gap, scale to the 1-minute, and take either a 1-minute
break of structure **or** a 1-minute inverse fair value gap back in the trade direction.

So for a **short**, the full trigger sequence is:
1. push above a marked high
2. 5-minute break of structure down (or 5-minute inverse fair value gap down)
3. both indexes bearish on the 5-minute
4. 1-minute break of structure **up** (this is the pullback)
5. 1-minute break of structure **down** → **ENTER SHORT**

For a long, mirror every direction.

Stops and targets live in the trade-management spec. What this spec records, in his words:
- stop goes beyond the structure that would prove the idea wrong, "**stop above the second
  high**" for a short, "**stops underneath the second low**" for a long (UPDATED-2026)
- targets are the marked levels in the opposite direction, taken in pieces:
  "we target our other draws on liquidity," "I'll look for **intermediate highs**" rather
  than one distant target; "I took my first profit and then I moved my stop loss to break
  even."

---

### THE STAND-DOWN CONDITIONS: collected in one place

A bot must be able to produce "no trade today." These are all of them stated in this
cluster:

1. **CPI, PPI, FOMC or NFP on the calendar** → no trading (Day19).
2. **Other red/orange news not yet released** → wait; after release, wait 15–20 min; if the
   move was violent, don't trade (Day19).
3. **The two indexes disagree on the 5-minute** → no trade until they agree (UPDATED-2026).
4. **Daily and 4-hour disagree on the instrument** → stand down or downgrade it (Day50,
   Day53, Day55).
5. **10:30 passed with no setup** → done for the day (TIME, UPDATED-2026).
6. **The sequence didn't complete**, e.g. price ran without giving the 5-minute pullback,
   or the 1-minute never broke back:
   > "NASDAQ dumps all the way down and doesn't give us the opportunity… We don't get any
   > sort of a five-minute retrace. We don't get any sort of a one minute break of structure
   > to the upside." (UPDATED-2026)
7. **The marked levels never got touched** → no trade, even with everything else aligned:
   > "even though every single thing was in alignment, we wouldn't have taken a trade
   > because our building blocks didn't get hit and we couldn't find any execution points."
   > (Day49)
8. **Already took a loss for the day** → he stops rather than adding risk:
   > "do I want to take another trade and put more risk on the table? No… there's just no
   > reason to add more risk onto the table potentially lose even more." (Day50)

The governing philosophy, stated twice and turned into a slogan:
> "Our strategy is less about what trade to take and more about what trades it stops us
> from taking." (UPDATED-2026)
> "if you guys end up taking less trades, it just means that you're protecting yourself
> from more losses."

---

## 5A. WHAT CHANGED: older videos vs UPDATED-2026

Prefer UPDATED-2026 in every row.

| Item | Older videos | **UPDATED-2026 (use this)** |
|---|---|---|
| Confirmation signal list | break of structure, inverse fair value gap, **SMT divergence** (the two indexes disagreeing at a high/low), **79% Fibonacci extension closure** (Stupid_Simple, Data_Backed, Strategy_Revealed) | **Only two: 5-minute break of structure or 5-minute inverse fair value gap.** SMT and the 79% extension are not mentioned anywhere in it |
| Continuation signal list | equilibrium, fair value gaps, **order blocks, breaker blocks** (Data_Backed) | **Equilibrium or fair value gap only.** Strategy_Revealed already announced the cut: "I used to talk about order blocks and breaker blocks… I pretty much completely removed that… this has been my best year of trading" |
| The two-index rule | Used as a *confluence*, trade the **leading** index: "we want to be trading on the S&P 500… because it's the leading index on that SMT divergence, and it's closest to our draws on liquidity" (Strategy_Revealed); "NASDAQ is the lagging index… so we're going to go over to the S&P 500" (Data_Backed) | Used as a **veto**: if the two indexes' 5-minute trends disagree, **do not trade at all**. Instrument choice becomes simply "whichever one gave the push-through" |
| Step structure | Same skeleton, more branches (a conditional "2B" for pre-market sweeps) | Four clean steps; pre-market handled by the blanket "never enter in pre-market" |
| Whether to give a step-by-step at all | STRAT-P2P **refuses**: "we're not going to do the step-by-step strategy… I should purposely omit little pieces" | Gives it explicitly, bar by bar |
| Trade frequency |, | Explicitly fewer trades is the goal |

There is also a separate **aggressive variant** (Science_Based, "$291,000"), which he says
sits *alongside* the main method, not replacing it: skip the 5-minute stage and enter off
the 1-minute, only on a strong-bias day, at **half normal risk**:
> "I'm going to be derisking… around like half of what I'm willing to risk for the day."
> "If I have a weak bias or if I'm like, 'Oh, price could go in either direction here,'
> why would I want to try and take an aggressive trade entry?"
**Recommend not building this first.** It is gated on a subjective "strong bias" judgement.

---

# 6. HIS OWN EVIDENCE: the numbers to check a build against

Recorded so we know what a correct implementation should roughly reproduce. These are his
claims, transcribed, not verified.

## 6A. UPDATED-2026: the most complete and most useful set

Broker-linked journal (TradeZella), **1 January 2026 → 1 June 2026**:

| Metric | His number |
|---|---|
| **Win rate** | **64.29%** ("my daily win rate is around 64% or 64.29%") |
| **Average reward vs risk** | **1 : 1.233** (transcript renders "a 123.3"; he restates it as "1 to 1.33") |
| **Average winning trade** | **~$22,000** |
| **Average losing trade** | **~$16,000** |
| Total, this strategy, year to date | **"over $700,000"**; broker account shows **$874,782** before fees and swap are deducted |

Month by month: January **~$41,000** · February **$148,000** · March **$293,000** ·
April **~$230,000** · May **~$34,000**. No losing month in that span.

**The most useful line for us is his description of the shape of the equity curve**, because
that is what a backtest must reproduce:
> "green week green week red week red week still green on the month"
> May specifically: "I made money the first week, I lost 10k the second week, and then I
> lost 70k the third week, and then I made 84k the fourth week."

He also warns his stated win rate is understated, because break-even exits that end
slightly negative after fees are logged as losses:
> "This trade got stopped out at break even… you take this plus the fee, you're getting a
> negative $1,180 in P&L, so it counts it as a loss. So, my win rate is actually a little
> bit higher than what it says on here."

**Fees and swap are material and he says so explicitly**, TradeZella nets them out, the
raw broker figure does not, and the gap is $874,782 − ~$700,000. Any backtest that ignores
costs will not reproduce these numbers.

## 6B. Data_Backed_Strategy_Everyday: "56 trading days"

> "I've tested it over **56 trading days** and it has made me **seven figures**."

Dashboard, **1 April → 30 September** (as transcribed; the month/day/dollar pairing is
garbled in the machine transcript, so it is quoted rather than tidied):
> "15 trading days. I was able to make $491,000. In September, I was able to make $247,000.
> In August with just seven trading days in July… In June, I was able to make $140,000 over
> the course of 11 trading days. In May, I was able to make $116,000 over the course of 10
> trading days. And then in April, I was able to make $53,000 over the course of seven
> trading days."

The number that survives the garbling and is worth keeping: **roughly 7–15 trading days per
month**, i.e. he trades on a minority of sessions. Two example trades are given at
**1 : 7.36** and **1 : 1.39** reward-to-risk, and he summarises a two-day stretch as
"two wins, one loss."

## 6C. Stupid_Simple_Strategy_Backtested

> "This stupidly simple strategy made me **$156,000 last month**."
(also rendered "$156,94350", likely $156,943.50). No win rate, no trade count.

## 6D. Strategy_Revealed: six months, April 1 → October 2

> "In the last 6 months, I have made **$1,047,984** trading." (transcript garbles it to
> "$1,47,984"; the filename carries the full figure)
- "my monthly P&L is **$491,000** just over the past month of September"
- **"my average trade win was $22,000 and my average trade loss was around $11,000."**
- Sample daily results as he lists them: "$14,000, $28,000, $32,000, $426,000, $98,000,
  25K, 14K, 47K, a lousy $1,000."
- Fee note again: "I made $3,000 but TradeZella counts it as only $1,000 made because
  there's fees subtracted from that."

## 6E. Science_Based_Strategy: the aggressive variant

> "how I was able to make **$291,000** with a new aggressive trading strategy", "this past
> month." Example reward-to-risk figures quoted: 1:4.8, 1:3.4, 1:4.7, "1 to 8." No win rate.

## 6F. What our build should reproduce if we built it right

The two numbers to target, both from UPDATED-2026 because it is the current method and the
only one with a clean win rate and a clean average reward-to-risk:

- **Win rate ~64%** (his figure is 64.29%, and he says the true figure is slightly higher)
- **Average reward-to-risk ~1 : 1.23**, wins averaging roughly 1.4× the size of losses in
  dollar terms ($22k vs $16k)
- **Trade frequency: a minority of sessions**, on the order of 7–15 trading days a month
- **Losing weeks are expected and normal**; the month is the unit that should be green

If a backtest of this spec produces a much higher win rate, or trades most days, the
implementation has almost certainly dropped one of the stand-down conditions in section 5.

---

# 7. THE SINGLE ORDERED CHECKLIST A BOT RUNS EACH DAY

All times US Eastern. Cross-references point at the other agents' spec files for the
drawing rules.

### Overnight / pre-open

1. **18:00 (prev day) – 03:00**, record Asia session high and low. No trading.
2. **03:00 – 08:30**, record London session high and low. No trading. This session's
   behaviour is the input to the bias.
3. **~08:00–08:30: news gate.** Pull the calendar. If **CPI, PPI, FOMC or NFP** → **STOP,
   no trading today.** Otherwise note the clock time of every red/orange release.
4. **Mark the levels**: previous day high/low, 1-hour highs/lows, 4-hour highs/lows, Asia
   high/low, London high/low. Drop any level already pushed through with no reaction.
5. **Set the bias** (section 1):
   - a. Daily and 4-hour direction must agree → otherwise **STOP** for this instrument.
     Daily wins when they conflict.
   - b. Classify what London did against the marked levels: consolidation / manipulation
     only / manipulation + reversal → gives expect-reversal or expect-continuation.
   - c. If expecting continuation, additionally mark **15-minute and 5-minute** highs/lows.
6. **Load both index charts.** S&P 500 and NASDAQ.
7. **08:30 – 09:30 (pre-market): observe only.** Never place an order. If a marked level
   gets pushed through here, it does **not** count as the trigger, a fresh 5-minute
   push-through after 09:30 is required.
8. If a red/orange release lands in this window, wait **15–20 minutes** after it. If the
   move was violent (large wicks / large moves, **threshold NEEDS VIDEO**) → **STOP**.
   If trading anyway → **reduce size**.

### The trading window

9. **09:30: market opens.** Clock starts.
10. **09:30 – 09:50: watch for STEP 1**: a marked level gets pushed through, on **either**
    index. → *liquidity/sweep spec.*
11. **STEP 2: 5-minute turn** in the opposite direction: a 5-minute break of structure (a
    candle **closing** past the most recent high/low) or a 5-minute inverse fair value gap.
    → *break-of-structure and fair-value-gap specs.*
12. **≡ INDEX GATE**: S&P 500 and NASDAQ must both be on the same side on the 5-minute.
    Disagree → **HOLD**, re-check as the session develops.
13. **STEP 3: 5-minute pullback** into equilibrium or a fair value gap. → *confluences
    spec.* Do not enter on step 2.
14. **STEP 4: 1-minute trigger**: 1-minute break of structure **against** the trade
    direction (this marks the pullback), then 1-minute break of structure **with** the
    trade direction (or a 1-minute inverse fair value gap). → **ENTER.**
    Ideal clock window **09:50 – 10:10**; acceptable a little either side.
15. **Stop** beyond the second high (short) / second low (long). **Targets** are the marked
    levels in the opposite direction, taken in pieces, first target then stop to break even.
    → *trade-management spec.*
16. **10:00**, if a release is scheduled here, no entries until at least **10:30**, which
    effectively ends the day.
17. **10:30: HARD CUT-OFF. No new trades.** If nothing has triggered, the day is over.
18. **If a loss was taken**, stop for the day rather than re-entering.
19. **13:00**, PM session opens. He does not trade it. Skip.
20. **17:00 – 18:00**, spread hour, nothing is open. Never trade.

---

# 8. WHAT IS GENUINELY AMBIGUOUS: re-watch these

Honest gaps. Each is a place where a bot needs a number the transcripts do not give.

1. **New York pre-market: 08:00 or 08:30?** TIME says 08:30 twice and puts the news release
   there. BIAS-STEPS says "technically at 8 is when New York pre-market opens. Okay, so
   pre-market opens at 8." Only matters for where the pre-market high/low gets measured
   from. → re-watch `L4xz2o23aPQ` ~[0:01:26] and `e_FV0Q14k8E`.

2. **"Drastically affected the market" has no threshold.** The whole post-news
   go/no-go rests on "large wicks, large moves" judged by eye 15–20 minutes after a
   release. A bot needs a number (points? a multiple of the recent range?). Nothing in the
   cluster supplies one. → re-watch Day19 for on-screen examples of a move he accepted vs
   one he rejected.

3. **Which bias procedure is the live one.** He *teaches* the previous-session profile
   method (Procedure A) and *performs* the nested-trend method (Procedure B) on every live
   morning in the bootcamp. The bootcamp is the older material, so this may simply be
   chronology, but no video in this cluster shows him running Procedure A live under
   pressure. → re-watch `e_FV0Q14k8E` alongside any recent live-bias video.

4. **Whether the 10:30 cut-off is absolute.** He states it twice, then shows a valid 11:05
   entry and declines it on preference ("I'm not willing to sit through all of this chop"),
   and separately took a 14:00-ish trade on Day53. Build it as hard; know he treats it as
   strong preference. → `8PYgFVB0GHE` ~[0:53:30].

5. **Every level on every live morning is pointed at, never spoken.** "Right here," "this
   candle," "boom." Across Day47, Day49, Day50, Day51, Day53, Day54 and Day55 there is not
   a single spoken price. **NEEDS VIDEO** for any attempt to replay those specific
   mornings as test cases.

6. **What counts as "the most recent high/low"** for a break of structure, the lookback
   is never defined. It is the single most load-bearing undefined term in the whole
   strategy, since steps 2 and 4 both depend on it. → belongs to the break-of-structure
   spec, flagged here because the day's logic collapses without it.

7. **Equal/near-equal levels and "low resistance liquidity"**, he leans heavily on stacked
   highs or lows being a stronger magnet ("why did market only want to take out these three
   lows and not this one all the way down here? Because these three were **stacked up**")
   but never says how close counts as stacked. → `KxBRLErkel0`.

8. **Whether Asia's high/low or London's takes priority** when both sit nearby, and whether
   a previous-day level outranks a session level. He marks all of them and picks by eye.

9. **A Fed speaker is not a blocking event, but a Fed *decision* is.** Day49 distinguishes
   them explicitly ("FOMC member… that wasn't really any of my concerns"). The calendar
   filter must distinguish FOMC rate decisions/minutes from member speeches.

10. **Whether the two-index veto has an equivalent for anything else.** He trades the
    method on gold, GBPUSD and GBPJPY where no second correlated index exists. He never
    says what replaces the gate there. Since we are building indices/crypto, worth settling
    before porting the method off the S&P/NASDAQ pair.

