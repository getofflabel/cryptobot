# Step 454 — what the newest corpus changes about the bot we built

Source: `tjr_transcripts/playlist3/`, **131 files, 105 unique videos, 911,557 words**
(26 files are renamed duplicates of numbered ones). Every unique video was read.
Compared against `step431` entries, `step432` confluences, `step433` management,
`step434` bias and the assembled strategy, `step436` conflicts resolved, and `step452`
Boot Camp 2.0.

This document reports **only deltas**. What the six existing specs already say correctly
is not repeated; it is listed by name in section 4.

---

## 0. THE FINDING THAT REORDERS EVERYTHING ELSE

### 0.1 The playlist is in chronological order, and that is provable

Files are numbered `NNN_Title.txt`. **The number ascends with time.** Four independent
proofs:

- **074** is the session where he loses $97,220. **075** opens: *"I'm locked in today.
  I can't believe I lost that much bread yesterday... Can't believe I lost 97 racks
  yesterday."*
- **022** and **036** mention 2024. **059-096** mention 2025 and Christmas. **099-111**
  all discuss the US government shutdown. **112, 113, 119, 120** mention 2026.
- **044** (the SMT lesson) says trade the *lagging* index. **100** says: *"Before I used
  to take the lagging index, but I changed that around like when was that like two and a
  half to three months ago."*
- **110** is titled "DOWN 350K THIS MONTH"; **111**, the next one, is "MY WORST TRADING
  MONTH EVER".

**A higher file number is newer teaching, and under the standing rule in `step436` it
governs.** Every finding below carries its file number, because that is what decides
which version wins. This is the most useful thing the corpus gave us: for the first time
we can date his contradictions instead of arguing about them.

### 0.2 Both open questions are answered, and the answer is that he abandoned both

`step452` PART D flags "prominent high" and "area of accumulation" as NEEDS VIDEO and
load-bearing. Both are defined in full in **003 "My 'New' Day Trading Strategy
Revealed"** — 82 uses of "prominent", 20 of "area of accumulation", 17 of "change of
trend".

Here is the part that matters. Across all 105 unique videos:

| Term | Files containing it | Newest file containing it |
|---|---|---|
| "prominent" | **003 only** | 003 |
| "area of accumulation" | **003 only** | 003 |
| "change of trend" | 003, plus 068 twice in a different sense | 068 |

**003 is the third-oldest video in the playlist. The vocabulary appears in that one
video and in none of the 117 videos that follow it.** Eight separate readers covering
every other file in the corpus reported zero occurrences. He announced this method,
used it for the two weeks the video describes, and never spoke of it again.

The definitions, since they are what was asked for:

> "this new strategy is based off three things okay it's change of trend... areas of
> accumulation and or slash where like orders are getting filled and then along with
> that prominent highs and lows"

**Prominent high.** He states plainly that it is not mechanical:

> "I'm doing it kind of based off of like it's more of like an eyeball approach"
> "this is all kind of opinion based really"
> "this is purely like just identifying the trend is purely based off the eyes"

The one codeable hook is the line chart, immediately undercut:

> "just toss it on a line chart you know we don't really care about these things"
> "this is also why I don't necessarily like to trust the line chart because if you look
> here you would say hey this High probably push past it Candlestick chart just a wick
> it's just a wick"

**Area of accumulation.**

> "what are areas of accumulation really just areas of consolidation prior to a big leg up"
> "this is where orders were filled within here right we can obviously see that orders
> were filled how can we see that with that big leg up afterwards"

And he refuses to distinguish it from an order block:

> "in this accumulation area or whatever I'm pretty much you can call this whatever you
> want... consolidation accumulation order block whatever the [expletive] you guys want"

**Verdict: do not build either one.** Building the most-documented concept in a cluster
after he stopped using it is the exact failure `step436` section 1 exists to prevent.
This is that failure a second time, wearing a different name.

### 0.3 Boot Camp 2.0 is OLD material — and `step452` is being treated as governing

This follows from 0.2 and it is the most consequential structural finding.

Boot Camp 2.0 uses "accumulation" **77 times** and "prominent" **19 times** across its
14 days, and defers the definition to a forthcoming video three separate times (*"that
new strategy video should be coming out to you guys today"*). The only video in 131 that
contains those terms is **003**.

So Boot Camp 2.0 is contemporaneous with 003, which sits near the **old** end of the
playlist — roughly 117 videos of later teaching sit on top of it.

**Confidence: high, but inferential.** Boot Camp 2.0 is in a different directory and
carries no date, so it cannot be placed by number directly. The chain is: 003 is provably
old within playlist3 → Boot Camp 2.0 shares vocabulary that exists in 003 and in no other
video → Boot Camp 2.0 defers to a "new strategy video" that can only be 003. Strong, and
worth confirming against upload dates, but it should not be ignored.

**What this costs us.** `step452` was extracted today and its conclusions were written as
governing. Three of them are already implemented in `tjr_bot.py`. They are re-examined
individually in section 1.11 — none is disproven by age, and two are independently
re-confirmed by newer videos. But *"Boot Camp 2.0 is the newer teaching"* is no longer a
valid reason to prefer anything.

---

## 1. WHAT CHANGED

Ordered by what it costs us to have it wrong.

### 1.1 SMT divergence was never dropped. It is the confluence he credits with seven figures. — CONTRADICTS

`step436` item 12 lists *"Divergence between correlated markets — dropped from the
current strategy"*. `step434` section 5A says SMT *"is not mentioned anywhere in"*
UPDATED-2026 and drops it from the confirmation list.

**That is wrong.** Video **115**, fifth-newest in the playlist, is titled
"$1,000,000+ From One Simple Confluence" and opens:

> "This is going to be the only SMT divergence video that you guys will ever need. This
> has been one of the key confluences to help me make seven figures over the past couple
> years trading."

(Identity cross-checked by content match against `tjr_transcripts/one_simple_confluence.txt`,
video `FJch02ucIO8`.)

Beyond that, SMT is the **organising logic of every live session in the corpus** — 076,
100, 101, 103, 105, 106, 108, 110, 111, usually dozens of times each. From 105, on what
he was waiting for before entering:

> "all I was waiting for was 1-minute confirmation to show that we were going to form a
> 5-minute SMT divergence"

And **112**, which he teaches as current everyday material, lists it in the working
cheat sheet (section 1.2b).

**Newer governs: SMT divergence is IN.** Our bot does not compute it at all.

Its mechanics, from 115, stated cleanly enough to build:

- **Only two positively-correlated instruments.** S&P 500 and NASDAQ. He tried and
  rejected others: *"I haven't seen as much correlation between those commodity and those
  currency pairs."*
- **Bearish**: one index makes a high then a *lower* high; the other makes a high then a
  *higher* high. **Bullish**: mirror, with lows.
- **The index that already reversed is the LEADING one.** The one still pushing is
  LAGGING.
- **Completion is a targeting rule**: the divergence is not finished until price takes
  out *"the low that is attached to the high that started the move"*.

### 1.2 What SMT actually does — and why our index-agreement veto SURVIVES — REFINES

The obvious worry is that `enforce_index_agreement` would block every SMT setup, since a
divergence *is* the two charts disagreeing. **120 answers this directly:**

> "What about SMT divergence? SMT divergence just strengthens our bias... me personally I
> use it to determine what index I should take the trade off of... **It doesn't tell me
> to take a trade. It doesn't tell me to execute. It just helps strengthen my bias.**"

And in the same coaching session the agreement gate is stated as still live:
*"we want both to be confirmed."* Confirmed again in 106: *"we get a fiveminute break of
structure to the upside on both the indexes."*

So SMT has **two jobs, neither of which is a trigger**:
1. It strengthens an already-established bias. 044 adds the direction filter: *"let's say
   our daily bias is bullish but we see a bearish SMT divergence, are we going to want to
   take that? No."*
2. **It selects which of the two instruments gets the order.**

The two tests measure different things — the agreement gate is about the two charts'
5-minute *trend state*, SMT is about a single swing point taken on one chart and not the
other. **Our veto survives unchanged.** What we lack is the SMT computation and the
instrument-selection rule it drives.

106 adds the precise strength: **necessary but not sufficient, and its absence is a
stand-down.**

> "As long as ES can stay underneath these highs, then we will have a bearish SMT. If
> not, then we won't have a bearish SMT."
> "we still have to wait for a lot of confluences for me to be able to enter a trade. I
> think that I'm just going to call it here."

**One honest complication, and it is not resolved.** The two-index agreement gate is
**absent from all seven of the dedicated strategy videos** (033, 072, 073, 082, 089, 095,
099), including 099, which is the newest of them. And **089 states the opposite outright**:

> "it really doesn't matter what index you were looking at"

Against that, 120 and 106 — both later than 089 — do state it. So the gate survives on
recency, but its evidence base is thinner than `step434` implies: it rests on
UPDATED-2026 plus two live sessions, against one explicit denial and five silences.
**Our `enforce_index_agreement` should stay on, because it only ever removes trades, but
it should be a measured config knob rather than an article of faith.**

### 1.2b The current strategy is SIX steps, not four — CONTRADICTS

`step434` section 5 records four steps. **112** gives six, taught as current
(*"if you guys are new here"*), and the menus are wider than ours:

1. Sweep a 1-hour, 4-hour or session high or low.
2. **5-minute confirmation confluence — any ONE of: break of structure, inverse fair
   value gap, a 79% extension closure, or a 5-minute SMT divergence.**
3. (2B) If step 1 happened pre-market, wait for a fresh 5-minute sweep after the open.
4. **5-minute continuation confluence: equilibrium, a fair value gap, or — if 2B fired —
   an SMT divergence.**
5. The same confirmation menu again on the **1-minute** → enter.
6. Target the other draws on liquidity in the trade's direction.

Steps 1, 4, 5 and 6 are what we have. Step 3 matches our
`premarket_sweep_carries_forward`. **Step 2's menu is where we differ** — we accept two
of his four options and never compute the other two.

**103 confirms the wider 1-minute menu too**, and this is new:

> "Why did I go short before seeing a one minute inverse fair value gap or a one minute
> break of structure to the downside? Because we had this one minute bearish SMT
> divergence."

`step434` filed 112 as an older video superseded by UPDATED-2026. Its own contents date
it to a live event on *"November 8th, 9th, and 10th"* pitched as preparation for
*"going into 2026"*, and it sits at position 112 of 120. **It is not old.**

### 1.3 Which instrument gets the order: the LEADING one, and "leading" is timeframe-relative — REFINES

Two of his videos give opposite instructions on the identical scenario, and the numbering
settles it.

**044** (old): *"Why do we want to enter off of NASDAQ? Because it's the lagging index —
ES has already made its move down, and it's pretty much telling us the future of what
NASDAQ is going to do."*

**100** (much newer), dating his own change of mind: *"That's why we always take the
leading index. Before I used to take the lagging index, but I changed that around like
when was that like two and a half to three months ago."*

**112** states it as a live instruction: *"We don't want to be trading on NASDAQ because
NASDAQ is the lagging index... So, we're going to go over here to the S&P 500. And this
is going to be our primary focus for this trading day."*

**120** repeats it while coaching: *"I would much rather you take the trade on ES just
because it's the more bearish index. This is the leading index on the bearish side."*

**Newer governs: trade the LEADING instrument.** `step434` recorded the leading-index
rule as the *older* practice and the agreement-veto as the newer; that ordering is
inverted.

Two refinements that matter for coding it:

**The label is per-timeframe, not per-instrument.** From 076:
> "on ES, is the lagging high time frame index, but on the low time frame, it's the
> leading one. On NASDAQ, the high time frame, it's the leading one, but on the low time
> frame, it's the lagging one."

**The lagging instrument is still watched, because it is what can invalidate the idea.**
From 101:
> "I'm mainly looking at the S&P 500 for my entry on Nasdaq... I wasn't willing to take
> the trade entry because ES was still down here and didn't give us confirmation to the
> upside yet."

**103 is the counter-example that proves it.** He identified the pair correctly, then
traded the wrong one under time pressure and named it as the error:
> "we kind of should have taken the trade on ES. I was just panicking a little bit
> because price started moving so fast."

**NEEDS VIDEO** for the mechanical test of "leading" — first to break structure, or first
to sweep. He points at it rather than defining it.

### 1.4 The 79% extension was never dropped either — CONTRADICTS

`step436` item 12 lists *"The 79% extension — dropped"*. It appears in **fourteen** files,
from 066 through **112**:

> 066, 075, 077, 080, 082, 089, 095, 099, 103, 105, 106, 109, 110, 112

It is in 112's current cheat sheet as a step-2 confirmation option, and it is used live
as a real decision input. From 075:

> "We did get a closure above the um we did get a closure above the 79% extension though."

From 103: *"if we can close above the 79% extension, I'll go long on NASDAQ."*

And in **106** the *absence* of the 79% close is the stated reason he took no trade:
> "We could also get a close underneath the 79% extension... we didn't close underneath
> the 79% extension."

**Newer governs: the 79% extension is IN**, as a third route to the trend-break state
alongside break of structure and gap inversion, exactly as `step432` section 2.2 had it.
He ranks it last himself in 066 (*"I rarely use this one, you guys can very well do
without this"*), so it widens a menu rather than adding a gate.

**And the anchor question `step432` flagged is answered.** From 099:

> "we take it from the low up to the high and we just wait for a candlestick closure
> underneath the 79% extension"

Swing low to swing high, the same anchor as equilibrium, with a **candle close** past the
level — not a wick. That is enough to build it.

### 1.5 Order blocks and breaker blocks: the retirement holds, but narrower than we wrote it — REFINES

`step436` section 1 retires both, quoting **116**, which the numbering confirms is
genuinely near-newest. The quote is accurate and the retirement stands. But read it
again:

> "I no longer use order blocks. I no longer use breaker blocks. The only
> **continuation** confluences that I need are equilibrium and fair value gaps."

He retires them **as continuation confluences** — the pullback you enter on. He does not
say he stops marking them, and he does not: 076, 077, 083 and 105 all have him naming
them on a live chart.

> 105: "We have the order block. We have the breaker block."
> 083: "We have this order block right here. Huge order block right here."

Independently corroborated by **112**, the current cheat sheet, where *"order block"*
appears **zero times** as an entry tool.

**Resolution unchanged for the build** — the pullback entry stays equilibrium and fair
value gaps only, which is what our code does. `step436` section 1 currently reads as
though he stopped using them entirely; that is broader than what he said, and the
wording should be tightened so nobody later "discovers" him naming one and reopens it.

### 1.6 The aggressive entry is not a half-size trade — CONTRADICTS

`step434` section 5A records the aggressive variant (from 082) as: skip the 5-minute
stage, enter off the 1-minute, only on a strong-bias day, **at half normal size**.

**All four clauses are confirmed in 082 itself**, and the half-size clause is stated flatly
three separate times, including inside a live recap:

> "the first thing is I have to have a strong bias with strong draw on liquidity"
> "around like half of what I'm willing to risk for the day"
> "This aggressive, we put half of our risk on because we have this super strong bias."
> "this does not mean that that old strategy that I was using and I still use to this day
> is just done... It still works perfectly fine."

**But this is a taught-versus-performed gap, the same shape as the two bias procedures in
`step434` section 1D.** In **075**, a much later live session, he names the aggressive
entry and runs it at the opposite size:

> "I used my aggressive trade strategy to enter on the S&P 500. And then on this we were
> using just the typical normal 5minute entry strategy"
> "I went super risk-heavy on the day for this trade... When I know what my bias is, when
> I know where the market wants to go, I have to stick to my guns and I have to put money
> where my mouth is."

The next day he reverts (*"I definitely will not be going nearly as risk heavy"*), and in
**077** he does run it de-risked as taught (*"I'll probably do like a d[e]-risked one
minute entry with a lot of confluences"*).

**So the teaching is unambiguous — half size — and the practice is a discretionary
conviction call.** The practice is not codeable and it is the most dangerous thing in this
corpus to copy: 075 is the $159,786 day; 105 is the $152,060 loss taken *"with two times
my original size"*. **Keep the aggressive variant unbuilt, as `step434` already advises,
and keep the double-size tier disabled.** Recorded so the "he sizes up on conviction"
quote is not mined out of context later.

### 1.7 The normal entry sequence, restated by him mid-trade — REFINES

From **075**, naming his own method while running it:

> "we were using just the typical normal 5minute entry strategy where we wait for again
> some sort of draw and liquidity to get hit. We wait for a fiveminute break of
> structure. We wait for a fiveminute confluence to get hit. From there scale down to the
> one minute time frame. Wait for a one minute break of structure. from their execute."

Five steps, matching `step434` section 5 exactly. **The strongest single confirmation in
the corpus that our assembled strategy is right.** It also confirms "never enter on the
break of structure itself", from the same session:

> "As much as I would love to just enter straight off of that break of structure, I'm
> going to be patient and wait for another confluence"

then, two minutes later: *"glad that I didn't enter off of that break of structure."*

### 1.8 "Macro" is a named window, and 09:50 is its open — REFINES

`step436` item 4 derives 09:50 from one sentence. It is far better established, and it
has a name, an end, and a mechanical reason.

**075**, live: *"10 minutes until the macro opens"* → *"Macro opens in 2 minutes"* →
*"Macro is o[pen] now. It's 950."*

**044**: *"typically these things will happen within those macros so from like 950 to
1010 that's typically a hot spot"*

**096**: *"It's really at like 9:50 that the kill zone starts, and it goes from 950 to
around 1010... Why? Because the 4hour candle closes at 10. This 4hour candle closes, this
1 hour candle closes. There's a bunch of candle closures that can cause a lot of
movements."*

So **09:50–10:10 New York is the prime window** and 10:30 remains the cutoff. Our
`US_INDEX_ETF` already carries `manip_end_t=09:50`, `entry_ideal_end_t=10:10`,
`cutoff_t=10:30`. **All three are confirmed and now have a source each.** No change
needed; recorded because this was previously one of the weaker-sourced parts of the build.

**083** adds a softer marker before the hard cutoff:
> "when the last 10 minutes are printing candles like this and it's getting near 10:30,
> it's kind of when you got to sit yourself down and have a conversation and say, 'Hey,
> it might be time to call it a day.'"

### 1.9 The New York pre-market ambiguity in `step434` is not an ambiguity — REFINES

`step434` section 8 flags 08:00 versus 08:30 as unresolved. **068** answers it in one
breath:

> "New York Stock Exchange opens at 9:30 a.m. eastern time, pre-market for New York Stock
> Exchange opens at 8:30 a.m. eastern time — that's for indexes... for people who are
> trading Forex... 8 a.m. eastern time"

08:00 is the **forex** New York open; 08:30 is the **index** pre-market open. Both are
his, for different instruments. **038** independently confirms 08:30 for indexes:
*"pre-market is about to open at 8:30... I start all of my kick streams at premarket open
at 8:30 a.m. eastern time."* The ambiguity can be struck.

### 1.10 A losing month is on the record, at the very end of the corpus — REFINES

This bears directly on Wallace's standard. The newest run of live sessions shows what a
genuinely bad stretch looks like for him:

- **108** — worst day ever, $234,060, ending the month at −$185,000
- **110** — $151,020, titled "DOWN 350K THIS MONTH"
- **111** — $80,450, "MY WORST TRADING MONTH EVER", and in it: *"I've lost $400,000 over
  the last two trading days."*

**What he changes coming out of it: nothing about the method.** No size cut is announced,
no rule tightened, no stand-down declared. Consistent with `step452` item 5 and `step433`
section 6.4, now supported by the largest drawdown in the corpus rather than by a single
teaching sentence. Our `losing_weeks_to_escalate = 2` pullback tightening is the only
reaction in the code and nothing here argues against it.

**And the year still closes green.** From **120**, a full-year self-report:
> "My win rate is approximately 60% with a average risk-to-reward of around 1 to 1.5. I
> am overall green over the course of 365 days."

### 1.11 Re-examining the `step452` changes already shipped in `step453`

**These are already in the bot** — `step453_bootcamp2_implemented.md` landed while this
extraction was running, applying the daily-risk budget, the multi-trade day, the 50/25
ladder and matched sizing across the replay and live paths.

Since section 0.3 dates Boot Camp 2.0 as old, each shipped change needs its authority
re-checked. **Good news: none is disproven, and two get a better source than the one they
shipped with.** Nothing in `step453` needs to be reverted on the strength of this
document.

| Change, as built | Boot Camp 2.0 authority | Newer independent support | Verdict |
|---|---|---|---|
| `target_fractions()` — 50% at target 1, 25% at target 2, rest a runner | Day 9 | **Group B: skipping this ladder is the direct cause of his three largest losses** (074, 108, 110). Also 101, 026, 007 all show multi-stage partials with stop to break even after the first. | **KEEP. Stronger than before.** |
| `DayBudget` — a per-day risk budget with release on break-even | Day 8, Day 9 | **076**: *"I'm definitely going to be de-risking. I went heavy on the risk the past two trading days... Ideally I only risk like 30K on this."* A per-day dollar budget, set fresh, in a much newer video. | **KEEP.** The budget survives; the specific 50%/25%/75% release arithmetic still rests on Boot Camp 2.0 alone. |
| No red-day halt | Day 12 | 108 and 110 both continue trading after large losses; 103 and 076 both make no rule change after a bad or good day. | **KEEP. Strongly confirmed.** |
| More than one trade a day | Day 8, Day 9 | 108 (2-3 trades), 110 (3 trades), 103 (3 trades), 074 (2 trades) — the newest live sessions routinely run two to four. 068 gives the beginner ceiling: *"one or two trades in a day."* | **KEEP. Strongly confirmed.** |
| Matched sizing across replay and live | not from Boot Camp 2.0 — a bug `step453` found | n/a | **KEEP.** A correctness fix, unaffected by dating. |

---

## 2. WHAT IS NEW

Rules we have nothing for at all.

### 2.1 He proactively cuts size AFTER a winning streak — NEW

`step433` section 6.5 says "never increase size after a win". He goes further, and it is
a policy, not a mood. From **081**:

> "did I absolutely crush it the last two weeks in trading? Yeah, 100% I did. But... how
> have I been risking? How have I been trading? I've been de-risking. I've been not
> taking as many trades... not increasing risk just because I had two good weeks in a
> row. Typically, when you get on a winning streak, what's the only thing that could
> potentially follow a winning streak? At least one loss. So you'd kind of be dumb to be
> increasing risk during a winning streak because eventually that winning streak is going
> to be over and the market's going to humble you... I'll purposely de-risk like the
> following week or the following day after a really big day or a really good week."

Confirmed twice more: **075**, the day after his best session
(*"I definitely will not be going nearly as risk heavy"*), and **076**
(*"I went heavy on the risk the past two trading days... Ideally I only risk like 30K"*).

This is the mirror of the losing-streak escalation and we have no counterpart.
**Two triggers are stated: after a really big day, and after a really good week.**
No percentage is attached, so the depth of the cut is **NEEDS VIDEO**.

### 2.2 Three new draw-on-liquidity level types — NEW

None is in `step431` section 5. All are used as targets and bias inputs, and all appear
in the newest live sessions:

- **"new day opening gap"** — 075 (seven uses), 077. Used as a primary target: *"I think
  my take profit one is going to be Asia highs because it's pretty much in line with the
  new day opening gap."*
- **"new week opening gap"** — 074, 077, 081, **110 (ten uses)**, 111. In 110 it is the
  reason he refuses to take partial profits: *"I don't want to take any profits until we
  come down and take out or start filling this new week opening gap."*
- **"midnight open"** — 075, 076, 077, 078, 080. Marked alongside session highs and lows.

**NEEDS VIDEO** for the exact construction of each — which two candles form the gap, which
timeframe, and whether "midnight" is 00:00 New York. The names are consistent across five
sessions, so these are standard levels for him. We mark none of them.

### 2.3 The "imbalanced price range" as a target zone — NEW

Distinct from a single fair value gap: a fast one-sided leg with *"nothing on the
left-hand side of the chart"*, which price is expected to revisit and "balance out".
Appears in **103**, **101** and **040**, and in 103 it is the entire rationale for a full
take-profit rather than an entry confluence. In 040 he calls it a named prior lesson:

> "what did we learn about my literally my most previous YouTube video talking about
> imbalances... price comes down and wants to balance out that price action"

Our targets come from marked levels only. **NEEDS VIDEO** for the marking rule.

### 2.4 A PM session, with its own compressed timeframe stack — NEW

Every spec we have is New York morning only. **096** describes a second session:

> "For PM session, we have the macro... the most optimal time to trade is from two to
> 3 pm. Okay, we can kind of drag this over to like 1:30... from like 1:30 to 300 p.m.
> Eastern time is really our prime time."

with an exact inner window given later as **13:50–14:10**, and a rescaled stack:

> "I pretty much treat PM session similar to how I trade AM session, except just on lower
> time frames... We're treating those [15-minute / 5-minute] as like our 4 hour and our
> hourly. And we're executing on the one minute."

15-minute takes the 4-hour's role, 5-minute takes the 1-hour's, 1-minute executes. He
hedges it himself — *"don't take that as just like the golden rule"* — so this is a
lower-confidence addition, but it is a whole trading window we do not have.

### 2.5 A target-duration figure — NEW

**096**: *"The way that I like to trade is I like to catch one to three-hour moves. Okay?
So ideally I'm in the market for 1 to 3 hours."*

We have no holding-time expectation anywhere. Useful as a shape check on a replay: if our
trades close in minutes or run all day, the shape is wrong even when the profit is right.

### 2.6 Where to sit inside the 1%-to-3% band, chosen from win rate — NEW

**069** gives a second axis for the daily budget that we do not have. This is a share of
the account, per day:

> "if we have a high win rate and a low risk reward... we can do slightly higher risk why
> because we're winning more way more than we're losing... let's say we have a 80% win
> rate... and a 1 to 1.5 risk reward ratio me personally I would probably be willing to
> risk like two to 3%"
> "in the reverse situation with the low win rate and a high risk reward we want to be a
> slightly lower risk"
> "me personally I'm a high win rate and low risk to reward person so I have slightly
> higher risk"

Not a contradiction of the fixed-size rule — that governs holding size constant once
chosen. This is about which baseline to choose. Given his own stated 60% win rate and
1:1.5 reward-to-risk (120), his self-description places him toward the upper half of the
band, which sits oddly against the ~1% his Boot Camp 2.0 arithmetic implies. **Flagged,
not resolved.**

### 2.7 Confirmation-gated entry in two tranches — NEW, and it contradicts a rule we wrote

`step433` section 8.2 says *"Size is never added to an open position. No averaging in, no
scaling up."* From **078**:

> "I might enter with like a tiny ass risk right here... This is like probably a fifth of
> what I'm willing to risk on the day... Let me add this equilibrium back on because if
> we can get a closure back above this, that would be solid. And then I can enter with
> the rest of the risk that I'm willing to."

then, once that close happened: *"Okay, we closed above that. I'm going to enter with the
rest of my position here."*

A first tranche at about a fifth of the day's risk budget before full confirmation,
completed on a named confirming close. It is not adding to a winner.
**Flagged for a decision rather than built** — it needs either an explicit carve-out in
the no-averaging rule, or a note that we deliberately do not build it.

### 2.8 The "insurance play" — NEW, recorded but not recommended

From **110**:

> "we could have like an insurance play which is like we take a trade on NASDAQ as
> well... we slowly take profits on NASDAQ as these lows start getting taken out because
> then... whatever we're making profit we move our stop loss to break even on NASDAQ...
> while ES we go for like the long shot."

Scale out fast on one index to fund a bigger single target on the other. It appears in a
$151,020 losing session, and the same pairing appears in 108, the worst day in the corpus.

### 2.9 Standing down for a whole week, and trading the news release itself — NEW, do not build

`step434` section 3B blocks the whole day on CPI, PPI, FOMC, NFP. The newest sessions show
something more specific. From **110** and **111**:

> "I think Wednesday is probably a good day to not trade, just stay out of the markets
> because we have FOMC"
> "I'm going to do exactly what I did last FOMC and wait for news to come out, wait for a
> high time frame sweep of liquidity... and short it all the way down."
> "tomorrow I know exactly how I'm coming into the market or I'm not trading on market
> open. But FOMC, bro, I'm coming for its head... I'm just not trading market open."

He references making **$400,000** on the previous FOMC doing this. So his real rule is
**not "no trade on a major-news day" but "no trade at the open; the release itself is
tradeable once it has swept liquidity."**

**Do not build this.** It is a discretionary post-news reversal on the highest-volatility
prints in the calendar, which is exactly what our news gate exists to keep an automated
system away from. Recorded because our blanket block is now known to be *stricter than
him*, which is the safe direction to be wrong in, and we should know we chose it.

**023** adds a discriminator worth keeping: the Fed *Chair* speaking, stacked with NFP,
buys a whole week off — *"Powell speaks today so I won't be trading[.] I actually won't be
trading this entire week cuz Powell speaks today[,] Powell speaks tomorrow and then we
have NFP."* But in **027**, a lone Powell appearance does not: *"Powell speaks uh today so
hopefully we can find a trade before he hops on."* It is the stacking that triggers the
week, not the speaker alone.

---

## 3. WHAT THE LOSSES TEACH

Nine losing or zero sessions. The pattern across them is worth more than any one, so it
comes first.

### 3.0 His four biggest losses are all the same mistake, and it is not an entry mistake

In 074, 108 and 110 the entry was fine and he says so. What killed all three was
**deciding, in the moment, not to take the partial profit ladder** — the 50% at target 1
and stop to break even that he teaches everywhere.

- **074**: *"I was up around $130 something,000 at the peak up here and uh didn't move
  stops to break even because my first take profit didn't get hit. Um, I wanted to hold
  all the way throughout this and that was my decision to make."*
- **108**: *"I'm lowkey confident enough to just put my stop underneath these lows... we
  might as well go full extendo on them, we might as well go full freaking extension"*
- **110**: *"I don't want to take any profits until we come down and take out or start
  filling this new week opening gap. I don't care how long we're on this. This is what
  I'm going to do for the day."*

He refuses to soften it afterwards, in 074:

> "It would be pretty easy for me to... say that, oh, I moved stops to break even, only
> lost $38,000. But I am not that type of person."

**This is the most important passage in this document for the build.** A bot cannot have
this failure mode unless we give it one. **The exit ladder must never carry a
discretionary override**, and any "let it run because conviction is high" branch is the
single feature most likely to reproduce his worst days. We do not have one. We must not
add one.

### 3.1 Per session, oldest to newest

**074 — $97,220, S&P 500, two trades.** Trade 1 stopped for $38,000. Trade 2 was a revenge
re-entry he narrates sarcastically as it happens: *"This is literally revenge revenge
trade part two... I'm a full-time emotional revenge trader."* It reached +$130,000
unrealized; he took no partial and it reversed. **Rule broken twice** — revenge re-entry,
ladder skipped. **Changes afterwards: nothing.** He states he will trade PPI and Powell the
following day, and does — and makes $159,786 (075).

**077 — $8,720, ES/NASDAQ short. The best-managed session in the corpus.** He judged the
short dangerous against an "up only" trend and de-risked *before* entering, took a
thinner-than-usual stack (break of structure + equilibrium + breaker, no fair value gap)
at reduced size, took one trade, and refused a second: *"I'm just going to call this one a
day... No second trades this time."* The phrase "this time" is him naming his own pattern.
**Rule followed. Smallest loss in the set.** The correlation between "de-risked, one
trade, no re-entry" and "smallest loss" is the cleanest signal in group B.

**081 — $0, no trade.** No chart mechanics at all. This is the win-streak de-risk policy
video quoted in 2.1, plus explicit anti-FOMO: *"I'm not going to get FOMO on that. I'm
completely fine sitting today out."* A zero day is treated as a successful outcome.
**Rule followed.**

**083 — $0, no trade.** Waited on ISM manufacturing, judged the price action un-tradeable
chop across two sessions, stood aside. Source of the soft 10:30 marker in 1.8.
**Rule followed.**

**103 — $52,660, "MADE DUMB MISTAKES".** Opens by correctly reading a bullish SMT
divergence and correctly forecasting a possible no-trade day: *"this very well could just
be a no trade day for me."* He traded anyway. Then two named errors: he **traded the
lagging index under time pressure** (*"I was just panicking a little bit because price
started moving so fast"*), and after being stopped he re-entered with nothing behind it:

> "I'm back in longs... I don't know what I was thinking. Genuinely, I don't even know
> what I was thinking... There was actually not a thought. There was not a thought behind
> that position that was just taken."
> "I really only should have lost like under 20k today and I ended up just giving the
> market 50k."

**Rule broken three times.** He does not blame the strategy or the signals. **Changes
afterwards: nothing systemic**, only a same-day decision to stop.

**105 — $152,060, NASDAQ short, "I MARRIED MY BIAS".** Entered *"purely just off of that
5-minute SMT"*, skipping the equilibrium retrace he normally requires: *"Should have
waited for my freaking confluences, dude."* Then the sizing:

> "I entered with two times my original size... the stop loss was two times my original
> size, so it ended up being like 4x what I usually end up risking."

**Rule broken twice, and they multiplied.** This is the concrete case for keeping the
double-size tier disabled: 2x size on a 2x-wider stop is 4x the money, on the trade that
also had one confluence too few. **Changes afterwards: nothing** — *"not tripping about
it."*

**108 — $234,060, ES + NASDAQ, worst day ever.** Trade 1 was a simultaneous long on both
indexes on an agreed 5-minute break of structure — the agreement gate working as designed
— stopped for $67,200. Trade 2 was an immediate re-entry at deliberately elevated size:
*"I'm going high risk, bro. I don't care."* He widened the stop mid-trade and skipped the
ladder. **Entry good, management bad.** Month ends at −$185,000.

**110 — $151,020, three trades, "DOWN 350K THIS MONTH".** The most instructive session in
the corpus, because it holds a good loss and a bad one on the same day. Trade 1 stopped for
$84,000 combined, and he grades it:

> "This was a good loss. I was satisfied with the risk that I put on. I traded it how I
> was supposed to."

He then explicitly does **not** revenge trade, and names why:

> "last time what caused me to lose even more money was making the emotional decision of
> jumping straight back into one and I saved myself from that"

And he refuses to abandon the setup type after two losses on it, reasoning from the base
rate rather than the sample:

> "if the market consistently, more often than not, gives me a high time frame liquidity
> sweep of London session highs and then gives me a bearish SMT divergence off of that.
> I've found success taking that trade a hundred times more than... Did I get stopped out
> off of market action like that twice? Yes. But does that mean I should be trying to
> trade it? No."

Trade 3 had a full fresh confluence stack — *"every single step was hit"* — and he
pre-committed on camera to skipping the ladder for the new week opening gap. It reversed.
**A good loss, then a good entry ruined by the same management decision as 074 and 108.**

**The discriminator this gives us, and it is codeable:** a legitimate second trade requires
a **complete fresh confluence stack**; a revenge re-entry is characterised by *degraded or
absent confluence plus elevated size*. That is testable, not a mood.

**111 — $80,450, "MY WORST TRADING MONTH EVER".** He attributes the prior day's loss to
letting a macro narrative override a sound technical read:

> "This was my issue yesterday. Technical analysis like I was very satisfied with the
> trades that I took if we didn't have the fundamental bullish news coming out this week."

Trade 1 was a *"jumped the gun"* long on NASDAQ before ES completed its own setup, stopped
for $39,000. **Rule broken** — he entered on one index before the pair confirmed. A point
in favour of keeping some form of two-index gate whatever we conclude about SMT. It is also
a direct endorsement of our mechanical-only design: the discretionary macro layer is what
he blames.

### 3.2 What the losses do NOT contain

No stand-down after a loss. No size reduction after a losing day, week or month. No rule
change. Across the largest drawdown in 911,557 words, **the method is never altered** —
and the year still finishes green at a 60% win rate. That is the answer to "what size does
he trade coming out of one": the same size. It confirms `step452` item 5 and `step436`
item 8 from the hardest available test case.

The one thing that *does* change after a bad run is nothing to do with losses at all — it
is the win-streak de-risk in 2.1, which fires after *good* runs.

---

## 4. CONFIRMED

Checked, unchanged, no detail needed.

- **The assembled strategy** (`step434` §5) — restated verbatim by him mid-trade in 075, and again while coaching in 120. Our strongest confirmation.
- **Never enter on the break of structure itself; wait for the pullback** — 075, live.
- **09:50 earliest entry, 10:10 ideal end, 10:30 hard cutoff** — 075, 044, 096. All three now sourced.
- **Two-candle swing definition** (up candle then down candle, higher of the two wicks) — restated verbatim in 098, 058 and 050. Nothing in the corpus revises it.
- **A break of structure needs a body CLOSE, not a wick** — 098: *"We need a full candlestick body close above a high or underneath a low."* Equal-to-the-level is not a break (058).
- **A single break flips the trend; both a higher high AND a higher low are NOT required** — 098: *"even though we make a higher low right here, that doesn't change the current downtrend structure... we are only monitoring the highs."* Our single-break reading is right.
- **Equilibrium: exact midpoint, most recent swing low to most recent swing high, buy below / sell above** — 116, verbatim as `step436` §6 has it. The wick-versus-close question on touching it remains **NEEDS VIDEO**.
- **Fair value gap definition and gap inversion** — 063, 100. Unchanged.
- **Daily bias Procedure A** — 088 is the same video as `step434`'s source; full match, nothing new.
- **Targets are chart levels, never a fixed multiple; first target at 1:1 when a level sits there; drop the setup if none does** — unchanged across the corpus.
- **Stop goes beyond the structure that proves the idea wrong, with a small buffer; no fixed-distance or percentage stop** — 068, 120. Still no buffer number outside forex.
- **Three-tier stop-placement priority** (beyond the sweep, beyond the high/low inside the confluence, beyond the confluence zone) — 096, matching `step431` §9.1 exactly.
- **No red-day halt** — 108, 110, 103, 076 all continue or change nothing.
- **Losing-weeks escalation, not losing-days** — nothing newer contradicts it.
- **1% to 3% of the account per day** — 068 corroborates the per-day framing from an earlier source than we had. 093 and 070 repeat the looser "per trade" phrasing (070 narrows it to 1-2%) without overriding it.
- **Account size is not a strategy input** — 030, 047, 064, 070 all route small accounts to a funded challenge rather than changing any rule. Settles that open question: the logic should never branch on account size.
- **One to two trades a day** — 068: *"you guys should only be taking like one or two trades in a day."*
- **The pre-market "no entry before the open" rule** — 073 confirms it from the funded-account side: *"For the most part, I am not looking to trade within the first 20 minutes of market open."*
- **The London-session-fake-out method (072)** — his original edge, and a genuinely *different* strategy: session pushes through a level, 5-minute break of structure back the other way, enter, target the opposite session's level. No continuation-confluence stage at all. He says himself it predates his current method. **Do not merge it into the current spec.**
- **His timeline** — 113: *"It took me 2 years to turn profitable in day trading"*, six years to current results.

- **Rule-list videos (091, 093, 113, 118)** and the whole mindset cluster (008, 009, 014, 016, 017, 019, 021, 024, 025, 027, 028, 031, 032, 034, 035, 038, 046, 048, 059, 087, 090, 092, 094, 102, 107, 119) — psychology and lifestyle. Nothing mechanical. Nothing to build.
- **071 "$11 Trillion Market Crash"** — checked specifically for a high-volatility regime rule. There is none; the video pivots to long-term investing. **Null result for our regime label.**
- **Funded accounts (010, 011, 012, 033, 073, 109)** — 010-012 are a hedging exploit on one prop firm which he disowns (*"I highly highly recommend you do not use this with prop firms"*). 109 is a sponsor video in which he says *"I currently do not trade on fundeds."* **Encode nothing from any of them.** Every drawdown limit, daily loss limit and profit target in them is a named firm's product term, not his rule. Two things in 073 and 033 *are* his and are worth knowing, though neither applies to us: he raises the selectivity bar on someone else's money (*"when I am trading on funded accounts I am only looking for A+ setups"*), and he sizes so the firm's daily drawdown is never the binding constraint (*"only risk half of the daily draw down per day and that's Max"*). He also discloses that he owns a prop firm, so his framing of firm rules is partly an operator's.

### 4a. His performance numbers — THREE separate measurements. Do not merge them.

Each covers a different period and comes from a different video. Merging them would
manufacture a figure he never said, and these are what we check the build against.

| Source | Period | Win rate | Average reward-to-risk | Other |
|---|---|---|---|---|
| UPDATED-2026 (via `step436` item 11) | Jan–June 2026 | 64.29% | 1:1.233 | 7–15 trading days a month |
| **099** | April 1 → October 2 | not stated | *"1 to 2 point something"* | average win $22,000, average loss ~$11,000 |
| **120** | 365 days to April 2026 | *"approximately 60%"* | *"around 1 to 1.5"* | *"I am overall green over the course of 365 days"* |

All three sit in the same region — roughly a 60-65% win rate at a reward-to-risk a little
above 1:1. **Beating any of them in a replay is a bug report, not a success**, and the
trade-count check from `step436` item 11 remains the most sensitive test we have: if our
build trades most days, we have dropped a stand-down condition.

---

## 5. CODE CHANGES, in priority order

Each names the file and the current behaviour it replaces. Nothing here has been applied.

### 1. `tjr_bot.py` — add SMT divergence; it does not exist anywhere in the codebase
**Replaces:** nothing. There is no SMT computation in `tjr_bot.py`, `tjr_desk.py` or
`tjr_alerts.py`.
**With:** at a swept level, compare the two correlated instruments — a divergence is one
making a new extreme while the other fails to. Its two jobs, per 120, are to
**strengthen an existing bias** and to **select the instrument**. Gate it on the daily
bias direction (044) and on a sweep actually happening (044: outside a sweep *"these
things will show up all the time and will be pretty much useless to us"*).
**Source:** 115, 112, 120, 044, and every live session from 076 to 111.

### 2. `tjr_bot.py` — instrument selection: trade the LEADING instrument
**Replaces:** `step434`'s "whichever one gave the push-through", which is what our level
bookkeeping effectively does.
**With:** the instrument that has already reversed in the intended direction, evaluated
**per timeframe** (076), with the lagging one still watched for invalidation (101).
**Source:** 100, 112, 120; 103 is the counter-example.
**NEEDS VIDEO** for the mechanical test of "leading".

### 3. `tjr_bot.py` — widen the step-2 confirmation menu
**Replaces:** confirmation on a 5-minute break of structure or a 5-minute inverse fair
value gap only (`SymbolDay.on_5m`).
**With:** 112's four-option menu — break of structure, inverse fair value gap, **a 79%
extension closure**, or **a 5-minute SMT divergence**. And on the 1-minute, add SMT as a
third trigger alongside break of structure and inverse gap (103).
**Source:** 112, 103, 106.
**Note this only ever ADDS trades**, so it must be measured against his 7-15 trading days
a month before it ships. If our trade count rises above that, the menu is too wide.

### 4. `tjr_bot.py` — `Config`, add a win-streak de-risk
**Replaces:** nothing. We have `losing_weeks_to_escalate = 2` and no counterpart on the
winning side.
**With:** a size reduction after a large winning day or a strong winning week, mirroring
081, 075 and 076. The depth of the cut is **NEEDS VIDEO** — he states the policy and never
attaches a number, so this ships as a named, **disabled** config knob rather than a guess.

### 5. `tjr_bot.py` — `session_levels()` (line 595), add three level types
**Replaces:** a level set of session highs/lows, previous day high/low and swing levels.
**With:** the same plus **new day opening gap**, **new week opening gap** and **midnight
open**, which appear across 074-081 and 110-111 as both targets and bias inputs and which
we mark none of. Exact construction is **NEEDS VIDEO**.

### 6. `tjr_bot.py` — `target_fractions()` (line 1448) and `TjrBot._manage`
**Replaces:** nothing — the 50 / 25 / runner ladder is already built, from `step452`.
**With:** no change to the arithmetic, but **add the constraint that the ladder can never
be overridden.** Its authority also changes: it no longer rests on Boot Camp 2.0's
now-doubtful recency but on group B, where skipping it is the direct cause of his three
largest losses. Whatever we build later, there must be no path where high conviction lets
a position run past target 1 untouched.
**Source:** 074, 108, 110.

### 7. Documentation only — correct `step436`, `step434` and `step452`
- `step436` item 12: **strike** *"Divergence between correlated markets — dropped"* and
  *"The 79% extension — dropped"*. Both are contradicted by the newest videos.
- `step436` §1: narrow the order-block retirement to *continuation confluences*, which is
  what he actually said.
- `step434` §5A: the leading-index rule is the NEWER practice, not the older one. And 112
  is a recent video, not a superseded one — its six steps supersede the four.
- `step434` §8: strike the 08:00-versus-08:30 ambiguity; both are his, for forex and
  indexes respectively.
- `step452`: add the dating caveat from section 0.3, and the re-examination table in 1.11.

### 8. Do NOT build — recorded so it is not rediscovered later
- **Prominent highs, areas of accumulation, change of trend** (003). Defined, then
  abandoned across 117 subsequent videos. He also calls the marking *"purely based off the
  eyes"*, so it is not codeable even if it were current.
- **The aggressive 1-minute entry** (082, 075, 077). Size is a discretionary conviction
  call and he runs it both large and small.
- **Trading the news release** (110, 111). Our blanket news block is deliberately stricter
  than him.
- **The insurance play** (110) and **dual-index simultaneous entries** (108). Both appear
  in his largest losses.
- **The funded-account material** (010-012, 033, 073, 109). He disowns the exploit and does
  not trade funded accounts.
- **Any small-account variant** (030, 047, 064, 070, 040). There isn't one. 040's
  challenge sizing is explicitly disclaimed: *"Is this how I would normally trade?
  Definitely not."*

---

## 6. WHAT I DID NOT REACH

- **Every unique video in `playlist3/` was read.** 105 of 105, by nine readers plus me.
- **Not read:** `bootcamp/` (the original 56-day course) and the top-level standalone
  videos, both already covered by step431-434 and out of this task's scope. The full
  corpus is 252 transcripts and 1,488,646 words; this document covers the 911,557 in
  playlist3.
- **The one video I could not place in the chronology** is `UPDATED_Day_Trading_Strategy_2026`
  (`8PYgFVB0GHE`), which `step434` treats as the newest and most authoritative source. It
  is **not in playlist3**, so the numbering cannot date it. That matters, because it is the
  single source behind `step434`'s claim that SMT and the 79% extension were dropped, and
  five later playlist3 videos contradict it. Resolving this needs its upload date.
- **NEEDS VIDEO, unresolved:** the mechanical test for "leading" index; the construction of
  the three new gap/open levels; the marking rule for an "imbalanced price range"; the
  depth of the win-streak size cut; the stop buffer outside forex; whether equilibrium
  needs a wick touch or a close.
