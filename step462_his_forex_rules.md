> **SHELVED BY WALLACE, 2026-07-26: "dont use tjr method on forex."**
>
> **This document is NOT to be implemented.** Nothing in it may be wired into
> `tjr_bot.py`, `tjr_crypto.py` or the desk. It is kept only as evidence of what
> TJR says, and as the reason we are not doing it: he trades ES and NQ, he does
> not trade forex, and the forex system described here is one he taught and
> demonstrated on camera rather than one he runs.
>
> **Forex belongs to Alex Gonzalez (@fxalexg), whose corpus is being built
> separately in `ag_transcripts/` and `step464_*`. The two methods stay separate
> and never mix.**
>
> TJR's method stays on the markets TJR trades.

# Step 462 — What TJR actually says about trading FOREX

Read-only extraction from the 553-file transcript corpus in `tjr_transcripts/`. Every rule
below carries a verbatim quote, the source file, and a date. Dates come from
`step460_dated_index_and_january_course.md` where the video is listed there; where it is
not, the dating method is stated inline and flagged.

Structure of every section: **what he says → what that means for our bot → do we already
do it.**

Where his material is silent, it says **SILENT**. Where a design choice would have to be
invented, it says **NOT IN HIS MATERIAL** and is left for Wallace. Where his statements
conflict, both are reported with dates and the newer one governs.

---

## 0. THE HEADLINE — the pivotal quote is the OLDEST video in the playlist

The quote this whole question hangs on:

> "this also works incredibly well on Forex and **I've honestly shifted the majority of my
> attention over to 4X** even though I've been playing around with the s p still I like
> just leaving my options open um this has worked on Forex"

- **Source:** `tjr_transcripts/playlist3/003_My ＂New＂ Day Trading Strategy Revealed.txt`
- **Date: 2023-09-05.** Nearly three years old.

That date is not a guess. `step460` §0.1 established that `playlist3` file numbers run
chronologically with four exceptions, and 003 is one of them: **003 is the oldest video in
the entire playlist**, older than 001 (2023-11-02) and 002 (2023-09-27). It sits in the
same fortnight as Boot Camp 2.0.

**So the pivotal claim is the weakest-dated thing we have on forex, not the strongest.**
He said it before he moved to futures, not after. Read it as "the method worked on forex
when forex was what I traded," not as a recent instruction to go trade forex.

What overrules it, in his own words, eight months later:

> "for me I only trade two pairs I trade es which is the S&P 500 and NQ which is NASDAQ
> okay **before this I used to trade Forex and I used to only trade GBP JPY in Gold okay
> now because I moved on to Futures I'm only trading indexes**"

- `tjr_transcripts/playlist3/033_How To Pass A Funded Account 101.txt` — **2024-05-27**

And two years after that, mid-lesson while demonstrating the forex method:

> "**I haven't even traded Forex in forever** and just literally explaining this old Forex
> strategy to you guys makes me want to trade forex again. But no, [expletive] it. We're
> good at indexes. Lock in."

- `tjr_transcripts/playlist3/096_How To Start Day Trading As A Beginner In 2026 (9 hours).txt`
  — **2025-09-25**

**Bottom line for Wallace:** he does not currently trade forex and has not for years. What
he *does* have is a complete, taught, session-based forex strategy he built himself on
GBP/JPY and gave away in full in September 2025. That is the thing worth building. He is
not telling us he moved back.

---

## 1. THE BIG FIND — a dedicated forex strategy, taught end to end, 2025-09-25

The last ~130,000 characters of `playlist3/096` (2025-09-25, the 9-hour beginner guide)
are a self-contained multi-part segment he calls the "Forex transformation boot camp" /
"Forex strategy creation." It is not in the dated index as a separate item because it is
buried inside video 096. **It is the single most valuable forex source in the corpus and
nothing in this project has used it.**

His framing:

> "I know a lot of you guys are Forex traders as well. So, I wanted to start going into an
> **old Forex strategy that I used to use**. um the strategy that I teach in the trading
> transformation in the boot camp. It's still applicable to Forex. I just kind of wanted to
> go into a **Forex specific** strategy. Um **I've never used it on indexes and I honestly
> don't think it would apply that well because this utilizes every single session for
> Forex.**"

> "I kind of just figured this [expletive] out **trading GBP JPY um for a long ass time and
> it worked really [expletive] well.** So now here it is. I'm giving it to you guys."

### 1.1 The steps, in his order

All from `playlist3/096`, **2025-09-25**.

**Step 1 — mark the three session opens, on New York time.**

> "we're mainly going to focus on Asian session, London session, and New York session. So,
> if we go over here, we know that **New York session opens at 8:00 a.m.** ... And then
> **London session opens at 300 a.m.** ... And then **Asian session opens at 8:00 PM.** So
> we can go ahead and mark that out. What is 8 PM? That's 20."

> "It depends on what pair you're trading. It's probably best if you just have this
> [expletive] **set to New York time.**"

He explicitly drops Australian session: *"we're actually going to ignore Australian
session."*

**Step 2 — mark session highs and lows on the 30-MINUTE chart, as boxes.**

> "what I like to do is I will mark out the session highs and the session lows. And **this
> is a little bit different than just marking out draws on liquidity** ... most of the time
> with liquidity, we're just marking every single high and [expletive] low. Um but with
> this, I'm marking out the session highs and session lows. And on top of that, **I like to
> do it on the 30 minute. And for whatever reason, this just came with [expletive] market
> experience. Don't ask me [expletive] why, but based on my experience, doing it this way
> works.**"

> "I like to take a little box and draw it out like this **from the base of the candle down
> to the low and then from the base of the candle up to the high.**"

A definitional rule he stresses twice — a session's high/low must be formed by a candle
that belongs to that session:

> "**this candle right here is a part of London session and this candle right here is a
> part of Asian session. So if we form a high, you guys have to understand on this line,
> it's not part of Asian session.**"

**Step 3 — overall sentiment first.**

> "what I like to do is I like to go and look at overall market sentiment. Okay, figure out
> like, all right, right now price is in a relative uptrend ... especially within the
> hourly"

**Step 4 — the trigger: sweep or revisit of a 30-minute session level, then drop to the
5-minute for a break of structure.**

> "you scale down into the fiveminut time frame and you just simply wait for those hourly
> highs and lows to get hit. Okay. So or sorry **not hourly 30 minute** ... **it's just like
> our futures trading strategy where we're looking for a fiveminute break of structure when
> these highs and lows get tested, revisited, or like swept.**"

**Step 5 — then one more confluence, or no trade.**

> "we're looking for a break of structure and then we're looking for **one of our several
> confluences. Either a fair value gap, equilibrium, order block, breaker block.**"

He enforces it against himself on the very first example:

> "Do we see a break of structure right here? Absolutely. But **do we see this imbalance get
> filled and moved off of? No. Okay. So, even though we pushed in here, got a break of
> structure, we don't give a [expletive] about it.**"

And rejects a setup for having no confluence at all:

> "We see a breaker structure, but **we need to wait for that next confluence. No
> equilibrium, no breaker block, no, nothing.**"

**Step 6 — targets are previous session highs/lows.**

> "in terms of targets, it's just like again, go re-watch any of my take-profit videos.
> Okay, we want to see price revisit highs."

> "you can either target previous lows made during New York session, 1 to 3 riskreward
> ratio, pretty [expletive] fire. Or literally just previous London lows, 1 to 1.5
> risk-reward ratio"

**Step 7 — stop placement, structural.**

> "stops underneath the low that it formed out of the imbalance"

> "If you put your stop loss underneath right underneath these lows, you would have been
> stopped out. **If you put your stop loss underneath fair value gap, you're good to go.**"

> "You can put the stop above equilibrium."

**What this means for our bot.** This is a genuinely different entry engine from the New
York one. Ours builds Asia/London/NY session levels and then only ever trades the 09:30
New York open off them. His forex engine trades **every session open against the previous
session's 30-minute high/low box**, giving up to three setups a day. The confluence menu,
break-of-structure trigger, 5-minute timeframe, and structural stop are all identical to
what we already run.

**Do we already do it?** Partly. `tjr_bot.py` already computes Asia (18:00-03:00) and
London (03:00-08:30) session highs and lows as key levels — that machinery exists. What
does not exist: the 30-minute-timeframe box construction, the session-belongs-to-candle
rule, and any entry path that fires outside the 09:50-10:30 New York window.

### 1.2 His own honest results, as he ran it live on camera

He backtests it on the spot and reports losses as well as wins. This is the closest thing
to a performance expectation he gives.

**GBP/JPY:**
> "if you're just following this strategy step by [expletive] step, you would have dubbed I
> don't even know how many trades we just took, **like out of six, you won four and you lost
> two.** Pretty [expletive] solid. And all the wins were much higher than a one to one
> riskreward."

**GBP/USD — worse:**
> "looking like another L on this strategy from GBPUSD. **not looking as hot as GBP JPY so
> far**"

**Gold — good:**
> "let's pull up gold because if I remember correctly, **this works pretty [expletive] well
> with gold.**" ... "three trades that we were able to take during New York session. **Two
> turned into dubs, one turned into an L.**"

**What this means for our bot.** If a backtest of this engine comes back with GBP/JPY
clearly ahead of GBP/USD and gold in between, that matches what he saw. If GBP/USD comes
back best, something is wrong with the implementation.

### 1.3 His summary line — the one sentence to build from

> "**Use the highs and lows of these sessions to your advantage if you are trading forex.
> They are definitely by far like in my eyes the best confluence to use.**"
> — `playlist3/096`, **2025-09-25**

---

## 2. WHICH PAIRS

### 2.1 The pairs he names, and the ranking he gives

From `playlist3/068_Beginners Guide To Start Day Trading In 2026 (5 hours).txt` —
**2025-03-07**, the clearest ranking anywhere in the corpus:

> "**Euro USD super good starter pair it moves rather slow** but that's good at the start
> when you guys are just learning this so Euro USD super good starter pair **GBP USD pound
> against the US dollar another good starter pair** if you want to get a little bit frisky
> **pound against the Yen it's a little bit faster moving it's a little bit more volatile
> but it's also a good Forex pair** so again this is if you're trading London session
> another fun one is gold okay **gold is a commodity and is also a good pair to trade it's a
> little bit more volatile it moves quickly sometimes it's a little bit harder to read**"

His own pair, repeatedly and across years:

> "I'll go ahead and pull up **GBP JPY because this was my favorite pair when I traded Forex
> back in the day**" — `playlist3/096`, **2025-09-25**

> "I actually used to trade London session back in the day ... **I would trade GBP JPY so
> the pound against the Yen during London session because it worked for me in my time
> zone**" — `playlist3/068`, **2025-03-07**

> "I was trading London session on GBP JPY and GBPUSD. **Those were like my main pairs.**"
> — `playlist3/072_This Simple Strategy Made Me My First $100k.txt`, **2025-04-14**

His actual pair history, told as a progression:

> "before all that [expletive] I was only trading GJ before I even before I even was doing
> the s p I was only doing GJ **before that when I was unprofitable I was trading gold and I
> was trading GBP USD together** now I look at them because I'm a [expletive] good Trader
> and guess what I can win off them but **when did I add them once I turned profitable with
> just GBP JPY choose one pair and stick to it** understand it and it will increase your
> probability within the market"
> — `bootcamp/Day29_Boot Camp Day 29： Trading Plan.txt`, **2023-06-24**

And the pre-market coverage list, which is a watchlist, not a trade list:

> "pre-market I go over pretty much every single pair es NQ I cover crypto **I cover Forex
> okay Euro USD gpp JPY gpp USD and gold**"
> — `playlist3/038_My Multi Millionaire Morning Routine.txt`, **2024-06-12**

### 2.2 The one-pair restriction — he states it hard, twice, five years apart

> "**you need to be consistent with pairs okay because a pair is like its own beast in
> itself** okay certain pairs move certain ways and if you guys just jump from Pair to pair
> to pair to pair to pair it's going to be really hard for you guys to be profitable"
> — `playlist3/033`, **2024-05-27**

> "I've added like 30 different Forex pairs Commodities cryptos and indexes and I've been
> looking at everyone at every single one of them at one time **trust me do not do that** ...
> **make a new watch list and only make it with one one single pair that you want to look at**
> so if you say I want to trade during London session awesome trade during London session
> and trade like the pound against the US dollar boom that's it just one"
> — `playlist3/068`, **2025-03-07**

Asked why he himself watches two:

> "**because I'm better at this [expletive] than you and I've been doing it for seven
> years**"

**What this means for our bot.** His restriction is about a human's attention, not about
edge. A bot has no attention budget. But the underlying claim — *"a pair is like its own
beast in itself,"* different pairs move differently — is a real claim: it says thresholds
should be calibrated per pair rather than shared. That is testable.

**Do we already do it?** No. We have no forex instrument at all.

**NOT IN HIS MATERIAL:** whether a bot should trade one forex pair or several. He never
addresses automation. Wallace's call.

---

## 3. SESSION AND CLOCK

### 3.1 The session boundaries — stable across the whole corpus, all New York time

Every statement agrees. Newest first:

> "**London session goes from 3:00 a.m. Eastern time all the way till 8:30 a.m. Eastern
> time.**" — `only_liquidity_guide.txt`, **2026-07-21** (newest source in the corpus)

> "**London session goes from 3 till 8:30.** Technically, technically London session goes
> till 11:30 New York time, but **we want to end all of these sessions when the next one is
> opening.** So, Asian session, London session pre-market actually opens at 2:00, but
> London session market opens at 3:00. New York pre-market opens at 8:30."
> — `full_tutorial_2026.txt`, **2026-05-07**

> "**London session opens at 3:00 a.m. So, we can go ahead and find 3** ... And then Asian
> session opens at 8:00 PM. So we can go ahead and mark that out. What is 8 PM? That's 20."
> — `playlist3/096`, **2025-09-25**

Consolidated, in his numbers, New York time:

| session | his window | note |
|---|---|---|
| Asia | 18:00 → 03:00 | some sources say 20:00 open (096); one says 19:00 (068) |
| London | **03:00 → 08:30** | true close is 11:00/11:30, he cuts it at the next open |
| New York — indexes | 08:30 pre-market, 09:30 open → 17:00 | |
| New York — **forex** | **08:00** → 17:00 | see 3.3, this is a real forex-only difference |
| spread hour | 17:00 → 18:00 | untradeable, see §5.1 |

There is a minor unresolved conflict on the Asia open: `096` (2025-09-25) says 20:00,
`only_liquidity_guide` (2026-07-21) says 18:00, `068` (2025-03-07) says 19:00. **The newest
governs: 18:00.** Our bot already uses 18:00.

### 3.2 The London manipulation — he teaches it as the same mechanism as the New York open

> "Right when London session opens, boom, we say [expletive] all the Asians ... **Where do
> they take them out? Boom. Right here, they take out the lowest point of Asia session. And
> then what happens after that? London session moves higher.**"
> — `only_liquidity_guide.txt`, **2026-07-21**

> "**Right when London session opens**, what does Central C say? ... **Moves and manipulate
> these lows to be able to fill Central C's buy orders right here.** Then Central C says,
> 'Thanks for the liquidity.' And then bang, what do we go up and do? **Take out Asia session
> highs.**"
> — `full_tutorial_2026.txt`, **2026-05-07**

> "something that I want to show you guys **specifically for my Forex people** and how this
> applies to you guys look here it's the same thing with London session and Asian session
> we have Asian session highs Asian session lows **look right when London session opens we
> immediately manipulate the Asian session low and then get legs up**"
> — `playlist3/068`, **2025-03-07**

**What this means for our bot.** The London open sweeps the Asia session high or low, then
reverses. That is structurally identical to what we already model at 09:30 New York, with
the Asia range playing the role the London range plays for New York.

### 3.3 The exact clock rules — the London equivalent of the 10:30 cutoff EXISTS

This is the single passage that answers the clock question, and it is unambiguous.
`playlist3/068_Beginners Guide To Start Day Trading In 2026 (5 hours).txt` — **2025-03-07**:

> "so for **indexes I'm only looking to trade from 950 to 1030** ... and then for Forex the
> Forex so New York Stock Exchange opens at 9:30 a.m. eastern time pre-market for New York
> Stock Exchange opens at 8:30 a.m. eastern time **that's for indexes** ... but **for people
> who are trading for Forex so let's say you want to trade like GBP USD or Euro USD during
> New York session** because that's what works for you guys **8 a.m. eastern time 2 10 a.m.
> eastern time are going to be your guys' times to trade okay that's Forex**"

> "**London session opens at 3:00 a.m. eastern time and ideally you guys find your trade
> between 3:00 a.m. to 4:00 a.m. I highly recommend you guys don't take any trades after
> 4:00 a.m. on London session** same thing here on New York session **if you guys can't find
> a trade after 10:30 me personally I would avoid trading for that entire day** Forex same
> thing **if you guys can't find a trade from 8 to 10 a.m. I would avoid trading for that
> entire day**"

So, in his own numbers:

| | manipulation/open | entry window | hard cutoff |
|---|---|---|---|
| **Indexes, New York** (what we run) | 09:30 | 09:50 → 10:30 | 10:30, day over |
| **Forex, London** | 03:00 | **03:00 → 04:00** | **04:00, day over** |
| **Forex, New York** | 08:00 | **08:00 → 10:00** | **10:00, day over** |

And the second forex-only difference, from the same video:

> "we're trading indexes and **for Forex your Market open is going to be at 8** so I know
> that's really confusing ... **when we're marking out London session highs and lows for New
> York Stock Exchange on indexes we are looking for them before 8:30** okay and then **when
> we're looking for London session highs and lows for 4ex we are looking for them before 8**"

**What this means for our bot.** A forex build needs three constants that differ from the
index build: London session window closes at **08:00** not 08:30 when the instrument is
forex; the London entry window is **03:00-04:00** with a **04:00** hard cutoff; the forex
New York window is **08:00-10:00** with a **10:00** hard cutoff.

**Do we already do it?** No. `tjr_bot.py` hardcodes `MANIP_END_T = 09:50` and
`CUTOFF_T = 10:30` (lines 89 and 91) and defines the London level window as 03:00-08:30.
All three are index-correct and forex-wrong.

**⚠️ CONFLICT — and it is a real one.** The 03:00-04:00 London window (068, 2025-03-07)
does **not** match the strategy he taught in 096 (2025-09-25), which trades **every session
open** off the previous session's box and is not confined to the first hour of London. The
newer source (096) governs by the dated-index rule, and 096 does not restate any hard
cutoff. Reported, not resolved. Wallace's call whether the forex engine runs
session-open-triggered with no clock cutoff (096, newer) or a first-hour-only window
(068, older but explicit).

**SILENT:** he never gives a separate "manipulation window" for London the way he gives
09:30-09:50 for New York. He gives an entry window that starts at the open itself. Do not
invent a London 03:00-03:20.

### 3.4 Which session for forex — he ranks them

> "**during London session the best pairs to trade are literally All Foreign Exchange Pairs
> and commodities** so that could be gold that can be gbpusd that can be Euro USD that can
> even be some off pairs like GBP JPY"

> "**I would like to say that during London session the Forex Market moves a little bit
> better than New York session** so if you say I want to trade New York session I would
> recommend you trade indexes which is what I trade ... but if you guys say I want my
> trading hours to be during London session cool **you guys should probably trade Commodities
> or Forex** okay ... something I want you guys to keep in mind **indexes if you guys want to
> trade indexes they do not move well at all during London session**"
> — `playlist3/068`, **2025-03-07**

Asia session — he says avoid it, everywhere, including for a Japanese-yen pair:

> "**I highly recommend against you guys trading Asian session** okay for multiple reasons
> it's a super low volatility session and most of the time it's literally just accumulation"
> — `playlist3/060_Easiest Way To Start Day Trading in 2026.txt`, **2025-01-10**

> "**I don't care if you're trading an Asian pair like if you're trading the USD JPY Market
> does not move well during Asian session** the only two sessions that I would consider
> trading would be London session and New York session"
> — `playlist3/068`, **2025-03-07**

And live, while demonstrating on GBP/JPY:

> "**this would have been a [expletive] loser. Okay, cuz it's [expletive] Asian session.
> Look at this volume. It's dog [expletive]**"
> — `playlist3/096`, **2025-09-25**

**What this means for our bot.** London is the preferred forex session. Asia is a
stand-down. Note the tension inside 096 itself: the strategy he teaches there trades all
three session opens, yet he calls the Asia-session trades losers as he takes them.
Practical reading: build all three, gate Asia off by default.

---

## 4. WHAT CARRIES OVER UNCHANGED, AND WHAT DOES NOT

### 4.1 His "plain and simple" claim, and the two places he tests it himself

The claim:

> "me personally I trade the S&P 500 and I trade NASDAQ **I know there's a lot of Forex
> traders that watch me you guys can plain and simple just apply this same exact strategy to
> your own session that you guys trade**"
> — `playlist3/060_Easiest Way To Start Day Trading in 2026.txt`, **2025-01-10**

He restates it later with evidence attached:

> "Literally like everything I've given you guys the like literally strategy that I use for
> futures. I've given you guys now a [expletive] Forex strategy. **The strategy for futures
> works for Forex too. People in my mastermind have been using the strategy that I taught
> you guys on futures for forex and it's been working great for them.** So literally just
> find the strategy that works well for you and run with that"
> — `playlist3/096`, **2025-09-25**

And in 2023, running the futures method on GBP/JPY on camera:

> "we'll go ahead and move right on over to gbpjpy now ... first let's go over daily bias
> ... **break of structure to the downside on The Daily** we already seen this first bearish
> candle on the weekly we see the break of structure okay boom we're bearish we're bearish
> daily bias ... **we do see our Forex strategy worked pretty well here we see these London
> lows get pushed into and then we see boom the break of structure right here** ... and then
> Target Asian session highs"
> — `bootcamp/Day47_Boot Camp Day 47： Back Testing CPI.txt`, **≈2023-07-13** *(interpolated
> from the bootcamp 1.0 anchors in `step460`: Day41 = 2023-07-06, Day55 = 2023-07-25;
> approximately one video per day. Not a verified date.)*

### 4.2 Element by element, against his own material

| element | carries to forex? | evidence |
|---|---|---|
| Session highs/lows as key levels | **YES — he calls them the best confluence on forex** | 096, 2025-09-25 |
| Previous day high/low, 1h/4h highs and lows, fair value gaps as key levels | **YES** | 068 lists all of them in the same breath as forex, 2025-03-07 |
| Liquidity sweep of a level | **YES** | 096, 2025-09-25 |
| 5-minute break of structure | **YES, identical** | *"it's just like our futures trading strategy"* — 096 |
| Fair value gap | **YES** | 096 |
| Equilibrium | **YES** | 096, used repeatedly in the worked examples |
| Order block / breaker block | **YES** | 096, *"Either a fair value gap, equilibrium, order block, breaker block"* |
| Daily bias from weekly/daily/4h/1h structure | **YES** | Day47 walks GBP/JPY bias exactly as he does an index, ≈2023-07-13 |
| Targets = previous session highs/lows | **YES** | 096 |
| Structural stop, not a fixed distance | **YES** | 096 |
| **SMT divergence** | **NO — weak, see §5.2** | 044 / 068 / 115 / full_tutorial_2026 |
| Analysis timeframe for level marking | **CHANGED: 30-minute, not 1-hour** | 096, *"I like to do it on the 30 minute"* |
| Session windows and cutoffs | **CHANGED: see §3.3** | 068, 2025-03-07 |

**Do we already do it?** Every YES row is already built in `tjr_bot.py` for indexes. The
two CHANGED rows and the one NO row are the entire delta.

---

## 5. WHAT HE WARNS DOES NOT WORK ON FOREX

### 5.1 Spread hour — a real, dated, mechanical caveat

> "the gap between 1700 and 1800 is what we call **spread hour**, where there is no market
> that is open. And that's typically when you guys will see, **if you guys trade on like a
> CFD broker, or a forex, or a commodities broker, you will see the spreads on every single
> pair get very, very large. It's because there's no money in the market**"
> — `full_tutorial_2026.txt`, **2026-05-07** (also `Time_Theory_Explained.txt` and
> `p2p_time_theory.txt`, same lesson)

> "there's a 1 hour gap where it's **untradeable**, okay? From 5:00 p.m. to 6 p.m. So there's
> like from like **501 to 559, you can't trade**"
> — `only_liquidity_guide.txt`, **2026-07-21**

> "stop trying to make some random reason why you should enter a trade **during Asian
> session during spread hour** when Market's not even [expletive] moving"
> — `full_tutorial_2026.txt`, **2026-05-07**

**What this means for our bot.** A hard no-trade block, 17:00-18:00 New York. He names
forex brokers specifically as where this bites.

**Do we already do it?** Not applicable today — our New York window closes at 10:30, so
we never reach it. It becomes live the moment a forex engine trades outside New York hours.

### 5.2 SMT divergence — weak on forex, and he has said so four times over three years

Oldest to newest, and they get more discouraging, not less:

**2024-07-29**, `playlist3/044_DO NOT Trade Without This Confluence (SMT Divergence).txt`:
> "**unfortunately Forex crypto guys** ... **I wouldn't necessarily recommend it in Forex**
> the only correlation that I have seen this work pretty consistently with is **Euro USD and
> gbpusd** so if you want to use that sure go ahead **I haven't back tested it as much as I
> have with these indexes**"

**2025-03-07**, `playlist3/068`:
> "if you guys are Forex Traders so if you guys are trading gbpusd Euro USD gold okay **if
> you guys are trading anything besides the S&P 500 in NASDAQ this is not going to apply to
> you** ... so you guys fast forward through the smt Divergence"

**2026-01-27**, `playlist3/115_$1,000,000+ From One Simple Confluence.txt`:
> "**I know that some people use EuroUSD and GBPUSD** because it's the Euro and the pound. I
> know sometimes people use gold and silver. **I haven't seen as much correlation between
> those commodity and those currency pairs than I've seen when using indexes.** So, just
> keep that in the back of your mind."

**2026-05-07**, `full_tutorial_2026.txt` — the newest statement:
> "**for the forex and commodities people, unfortunately this is not going to be as
> beneficial for you guys** because this is specifically talking about the divergence
> between the S&P 500 and the NASDAQ."

**What this means for our bot.** No conflict here — four sources, one direction. If SMT is
used on forex at all it is EUR/USD against GBP/USD, and he has never backtested it. It
should not be a required confluence on a forex instrument.

**Do we already do it?** `tjr_bot.py` runs a both-indexes-agree veto (line 1901) that is
structurally the SMT check. Carrying that veto onto forex would be building on the one
thing he has repeatedly said does not transfer.

### 5.3 Asia session — see §3.4. Stand-down, in his words, on a JPY pair specifically.

### 5.4 The one he demonstrates rather than states: news candles are untradeable

> "**this had to have been on some crazy ass news because we see wicks wicks**"
> ... "Whole bunch of volatility from FX in this. I mean, this is a pretty good example, but
> **this looks like a news collapse** ... but [expletive] you know, **this was definitely a
> news candle.**"
> — `playlist3/096`, **2025-09-25**

He rejects those setups mid-demo. Leads directly to §7.

### 5.5 What he does NOT warn about — say it plainly

**SILENT** on all of the following. Nobody should fill these in:

- Rollover/swap financing on positions held across 17:00 New York. He mentions swap once,
  only as a line item Tradezella subtracts from his broker P&L, never as a decision input.
- Weekend gaps and the Sunday 18:00 open.
- Anything about spreads or slippage on forex outside the prop-firm context of §6.2.
- Any pair beyond GBP/JPY, GBP/USD, EUR/USD, USD/JPY (named once, only to say Asia session
  is bad for it) and gold. Exotics, crosses, and everything else: **NOT IN HIS MATERIAL.**

---

## 6. SIZING — his prop-firm rules and his own-money rules are DIFFERENT, and both exist

Wallace's account has no drawdown rule. This section separates the two carefully because
the numbers that circulate most are the prop-firm ones.

### 6.1 PROP-FIRM ONLY — do not apply to us

These are explicitly derived from evaluation drawdown limits, and he says so in the same
sentence.

> "**So for forex, I would be looking to risk around 1 to 1.5% per trade because again, we
> have to understand that our overall max draw down limit is going to be 8% and our profit
> target is going to be 8%.**" ... "**I found that this percentage risk per trade of your
> total account balance has worked the best for me when it comes to passing accounts on
> forex prop.**"
> — `playlist3/073_Beginners Guide To Get Funded In 2026.txt`, **2025-05-12**

> "most Prop firms they give you guys a **3 to 5% daily draw down** that's pretty typical okay
> so with that in mind how much of a percentage should we be risking per day **if we only
> have a 3% daily draw down the max I want to be risking per day is 1.5%** okay and the
> reason behind this is because first of all **slippage and spread is a very real thing and
> especially on prop firm accounts**"
> — `playlist3/033_How To Pass A Funded Account 101.txt`, **2024-05-27**

Both percentages above are **share of the account lost if the stop is hit**, not a move in
the price.

**⚠️ These are the 1-1.5% numbers. Both are load-bearing on a drawdown rule Wallace does
not have. They should not be ported.** Note also that 033's 1.5% is a **day** budget, while
073's 1-1.5% is **per trade** — they are not even the same rule.

### 6.2 HIS OWN MONEY, FOREX ERA — the lot-size lesson

`bootcamp/Day39_Boot Camp Day 39： Calculating Lot Size.txt` — **2023-07-04**. This is the
forex sizing mechanism, taught on GBP/USD with a pip-based position calculator.

The mechanism:
> "account balance at the top **risk amount and percent** and then **stop loss in Pips** okay
> so all you do let's say we have a 1,000 account ... we want to risk one percent we type
> one in there and then let's say our stop loss is 30 Pips we type 30 in there ... it tells
> you the exact lot size that you should use"

Reading the stop in pips straight off the chart tool:
> "when you set up your short position tool okay see this number right here **that is your
> stop-loss in Pips** so as we drag this ... boom our stop loss 11, boom stop loss 47 Pips,
> stop loss 16 Pips"

A broker-dependent trap he flags explicitly:
> "**most offshore brokerages** ... a lot of prop firms **their units per lot is going to be
> 10.** so make sure whenever you open a new account with a different brokerage with any
> different firm with anything **you check this because this could really mess you up**"

The set-size rule, and the fact that a wider stop deliberately costs more:
> "what's usually the lowest your stop loss will be during a trade okay so for me it's
> usually 400 ... **that is going to be our set lot size** ... **that means I'm going to be
> risking one percent if price hits stop right here that also means I'll be risking two
> percent of my account if we have a larger stop loss**"

His three-tier own-money ladder, in his words:
> "**normal risk** is just one percent it's showing you it's the set lot size ... **d-risk is
> 50 of it, confident is two times it.** simple as that"
> "**d-risk will be high impact news** or like there's something that I understand that will
> probably mess up the market"
> "**confident** ... that's on a day with **no news, I love the setup, all the biases are in
> line**"
> "**you guys should never use a confident lot size** ... you guys don't have proof in the
> market that you have the ability to be confident"

Every percentage in that block is **share of the account lost if the stop is hit**.

And the band, stated instrument-agnostically and naming forex:
> "risk **one to three percent of your account** ... per trade okay and **depending on if you
> do Futures if you do options if you do Forex there's a bunch of different ways to
> calculate this**"
> — `bootcamp/Day13_Boot Camp Day 13： Risk Management.txt`, **2023-06-07**

**What this means for our bot.** The forex sizing mechanism is: pick a stop from chart
structure, read its distance, and solve for the lot size that makes that distance cost the
chosen share of the account. That is exactly what `size_position()` already does for
indexes, with pips replacing ticks. **Leverage is an output of that calculation, never an
input.** The d-risk / normal / confident ladder is a multiplier on the result, gated on
news and bias agreement.

**Do we already do it?** The core sizing math, yes. What is missing for forex: pip value
per lot per pair, and the units-per-lot check he warns about, which is a venue property
and belongs to whoever is building the venue.

**⚠️ Note the age.** Day39 is 2023-07-04 and `step460` §2.1 already established that his
**2026-01-16** risk lesson overrules part of it — specifically, he now cuts size in half
when the day's stop is drastically wider than usual, where the 2023 lesson says hold the
size. That 2026 correction is taught on futures. Whether it applies to forex is
**NOT IN HIS MATERIAL**, but it is the same trader on the same sizing question two and a
half years later, and there is no forex-specific rebuttal.

### 6.3 The own-money rule that is neither of the above

> "**if we have a high win rate and a low risk reward then we can do slightly higher risk**
> ... let's say we have a 80% win rate that's really freaking good and a 1 to 1.5 risk
> reward ratio **me personally I would probably be willing to risk like two to 3% per trade**
> ... now in the reverse situation with the low win rate and a high risk reward we want to
> be a slightly lower risk"
> — `playlist3/069_Day Trading For Beginners： The Complete Starter Guide 2025.txt`,
> **2025-03-18**

Both figures are **share of the account lost if the stop is hit**. This is not
forex-specific but it is not prop-firm-contaminated either, and it is newer than Day39.

---

## 7. NEWS — what he gates on, and why our calendar cannot serve forex

### 7.1 Forex Factory is his source, everywhere, including in the 2026 material

> "**where do I get my news from it is called Forex Factory** okay so I literally just go
> forexfactory.com"
> — `bootcamp/Day19_Boot Camp Day 19： How to Read News Data.txt`, **≈2023-06-13**
> *(interpolated between the `step460` anchors Day13 = 2023-06-07 and Day29 = 2023-06-24.
> Not a verified date.)*

> "we can go on to this handy dandy website called **Forex Factory** and what we are going to
> look for is **red news folders**"
> — `full_tutorial_2026.txt`, **2026-05-07** (also `Advanced_Liquidity_Concepts.txt` /
> `p2p_advanced_liquidity.txt`, **2026-01-05**)

### 7.2 THE KEY PASSAGE — he filters the calendar BY CURRENCY, to the pairs he trades

This is the most directly actionable news instruction in the corpus for a forex build, and
our `news_calendar.py` cannot express it.

> "I also get rid of **all the currencies that I don't trade** so **do I trade AUD USD or any
> AUD pair no** do I trade any **Canadian dollar** pair nope do I trade any **CHF** pair no ...
> do I trade any **European** pair nope **do I trade a GBP a Great British pound pair yes I do
> I trade GBP USD and GBP JPY** cool **do I trade a JPY pair yes I trade GBP JPY** cool do I
> trade NCD no I do not **do I trade a USD pair yes I trade GBP USD I trade gold** and then I
> also trade the S&P 500 **your S&P 500 news events will be covered by USD** okay and then
> from there I hit apply filter"
> — `bootcamp/Day19`, **≈2023-06-13**

Two consequences he draws from it in the same lesson:

**Which side of the pair the news is on decides the direction.**
> "**whatever's on top it's positive correlation whatever's on bottom it's just inversed**
> okay so if we get good for currency on the US dollar price is going to go down"

**Multiple red folders on your currencies is a stand-down.**
> "today we had CPI as you can see red folder red folder red folder we also have **two red
> folders on GBP** um **overall just a terrible probability day to trade** ... we can see how
> large these Wicks are ... **this is not price action that you are able to trade it is
> unpredictable**"

**When only USD is red and you hold a non-USD pair, you can still trade the other one.**
> "**all of these are for USD so if anything I'll probably only be looking at like GJ**"
> — `bootcamp/Day19`

### 7.3 He gates GBP pairs on UK news, by name, twice

> "we do want to be careful about **GBP pairs at around 11 A.M U.S. time** ... this is
> happening during London sessions so **if you trade London stay away from GBP pairs or just
> wait for this news to come out**"
> — `bootcamp/Day43_Boot Camp Day 43： Weekly Analysis.txt`, **≈2023-07-08**
> *(interpolated; not verified.)*

> "just **GBP news tomorrow during London session so if you're a London session Trader stay
> away from any of the pound Pairs and maybe even some of the Euro pairs** because that could
> mess up the market a decent amount"
> — `bootcamp2/Day13_Boot Camp 2.0 Day 12： Red Day.txt`, **2023-09-11**

> "**bearish CPI for GBP/USD and GJ** ... that's why it just dumped at that time ... There is
> CPI for both these pairs. That was during London session. **I probably still won't
> necessarily want to trade**"
> — `bootcamp/Day55_Boot Camp Day 54： Daily Bias + No Trades Today.txt`, **2023-07-25**

### 7.4 The wait, and the day-killers

> "we wait for news to come out we wait to see the data ... and then **we wait for like you
> know 15 20 30 minutes** okay let price develop and then we can look to take a trade"
> — `bootcamp/Day19`, **≈2023-06-13**

His day-killer set, as named in that lesson: **CPI, PPI, FOMC, non-farm payroll.** All four
are US releases and all four are already in `news_calendar.DAY_KILLERS`.

**What this means for our bot.** A forex build needs a calendar with a **currency field**
and a currency filter, plus UK, EU and JP releases. His rule is: for pair XXX/YYY, a red
folder on **either** XXX or YYY gates the pair; a red folder on a currency you do not hold
does not.

**Do we already do it?** **No, and the gap is structural, not just missing rows.**
`news_calendar.py` (1,004 lines) pulls from BLS, the Federal Reserve FOMC calendar, and
BEA — three US agencies. Line 170 pins `TIMEZONE = "America/New_York"` with the comment
*"every time in this module, no exceptions."* The `Release` dataclass has `date`, `time`,
`name`, `impact`, `source`, `verified` — **there is no currency or country field**, so even
if UK/EU/JP rows were added there would be nothing to filter on. Adding forex means adding
a field to `Release` and new sources (Bank of England, ONS, ECB, Eurostat, Bank of Japan),
and `blocks_the_day()` becoming per-pair rather than global.

**SILENT:** he never names Bank of England, ECB, or Bank of Japan as institutions. He works
entirely off Forex Factory's currency folders. Which specific UK/EU/JP releases count as
red folders is **NOT IN HIS MATERIAL** — Forex Factory's own classification is the only
authority he uses.

---

## 8. VENUE — what he actually traded forex on

Included only because it bears on the venue work, and flagged for what it is.

`bootcamp2/Day04_Boot Camp 2.0 Day 4： Best Forex Broker.txt`, **2023-08-26**, is a paid
affiliate announcement, not instruction. Two facts from it are still useful:

> "**it's a metatrader5 brokerage**"

> "literally every single foreign exchange brokerage that allows you to trade Majors miners
> indexes Futures Commodities ... **it has to be offshore and it has to be unregulated**"

**What this means for our bot.** His own forex venue was an offshore MetaTrader 5 CFD
broker. That is a statement about his situation in 2023 and is **not** a recommendation we
should act on. The venue question belongs to the agent building it.

---

## 9. SUMMARY — the delta between what we run and a forex build

| # | Rule | His source | Date | Already built? |
|---|---|---|---|---|
| 1 | Session highs/lows are the best forex confluence | `playlist3/096` | 2025-09-25 | Levels yes, forex engine no |
| 2 | Mark session levels on the **30-minute**, as boxes | `playlist3/096` | 2025-09-25 | **No** |
| 3 | A session's high/low must come from a candle inside that session | `playlist3/096` | 2025-09-25 | **No** |
| 4 | Trigger = sweep/revisit → 5-min break of structure → one confluence | `playlist3/096` | 2025-09-25 | Yes, for New York only |
| 5 | Confluence menu: FVG, equilibrium, order block, breaker block | `playlist3/096` | 2025-09-25 | Yes |
| 6 | Targets = previous session highs/lows | `playlist3/096` | 2025-09-25 | Yes |
| 7 | Structural stop (under the gap, under the swept low, above equilibrium) | `playlist3/096` | 2025-09-25 | Yes |
| 8 | London 03:00-08:30 NY; forex NY session opens **08:00** | `068` / `full_tutorial_2026` | 2025-03-07 / 2026-05-07 | London yes, forex 08:00 **no** |
| 9 | Forex London entry 03:00-04:00, cutoff 04:00 | `068` | 2025-03-07 | **No** — ⚠️ conflicts with #4, see §3.3 |
| 10 | Forex New York entry 08:00-10:00, cutoff 10:00 | `068` | 2025-03-07 | **No** |
| 11 | London session levels for forex end at **08:00**, not 08:30 | `068` | 2025-03-07 | **No** |
| 12 | Asia session = stand-down, even on a JPY pair | `068` / `060` / `096` | 2025-03-07 / 2025-01-10 / 2025-09-25 | N/A today |
| 13 | Spread hour 17:00-18:00 NY = untradeable, spreads blow out on forex brokers | `full_tutorial_2026` / `only_liquidity_guide` | 2026-05-07 / 2026-07-21 | **No** |
| 14 | SMT divergence is weak on forex | `044`/`068`/`115`/`full_tutorial_2026` | 2024-07-29 → 2026-05-07 | ⚠️ we run the equivalent veto |
| 15 | Daily bias from weekly/daily/4h/1h carries unchanged | `bootcamp/Day47` | ≈2023-07-13 *(est.)* | Yes |
| 16 | Size = risk / stop distance in pips; leverage is the output | `bootcamp/Day39` | 2023-07-04 | Math yes, pip conversion no |
| 17 | Cut size in half when today's stop is drastically wider | `p2p_risk_mgmt_psych` | 2026-01-16 | Taught on futures; forex silent |
| 18 | Filter the news calendar **by currency** to the pair you hold | `bootcamp/Day19` | ≈2023-06-13 *(est.)* | **No — no currency field exists** |
| 19 | GBP pairs stand down on GBP red folders during London | `Day43` / `bc2 Day13` | ≈2023-07-08 *(est.)* / 2023-09-11 | **No** |
| 20 | After news, wait 15-30 minutes before looking | `bootcamp/Day19` | ≈2023-06-13 *(est.)* | Yes, in spirit |
| 21 | GBP/JPY was his pair and backtests best; GBP/USD worst of the three | `096` / `Day29` | 2025-09-25 / 2023-06-24 | N/A |

### The three open conflicts, reported and not resolved

1. **§3.3** — first-hour-only London window (068, 2025-03-07) versus all-session-opens with
   no stated cutoff (096, 2025-09-25). Newer governs by the dated-index rule, but 096 simply
   does not address cutoffs, so this is a genuine gap rather than a clean override.
2. **§3.1** — Asia session opens at 18:00 (2026-07-21), 19:00 (2025-03-07) or 20:00
   (2025-09-25). Newest governs: **18:00**, which is what we already run.
3. **§6.1 vs §6.2** — the 1-1.5% figures are prop-firm artifacts; the own-money teaching is
   the 1-3% band and the d-risk/normal/confident ladder. Not a contradiction once separated,
   but they are routinely quoted as if they were the same rule.

### Where his material is SILENT — leave these to Wallace

- Rollover/swap costs, weekend gaps, the Sunday open.
- Any forex pair beyond GBP/JPY, GBP/USD, EUR/USD, USD/JPY and gold.
- A London manipulation window distinct from the London entry window.
- Whether a bot should trade one forex pair or several.
- Whether the 2026-01-16 half-size-on-a-wide-stop correction applies to forex.
- Which specific UK/EU/JP releases are red folders. He defers entirely to Forex Factory.
