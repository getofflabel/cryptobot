# step301_tjr_rules.md: TJR's method, compressed into executable rules

**Round 301. Knowledge compression, not evaluation.** No backtest was run,
no verdict is rendered on whether any of this works. The job was to learn
the method properly and write it down so an engineer can implement it.

## Sources

Channel: **TJR** (`@TJRTrades`, YouTube). 30 videos pulled as auto-caption
transcripts via `yt-dlp --js-runtimes node --cookies-from-browser chrome`,
237,028 words total. Every rule below carries a source file + timestamp.
Quotes are under 15 words each, paraphrase-anchored to the transcript.

The spine of this round is the **"Path to Profitability" series**, a
13-part structured course where he teaches one concept per episode with
formal definitions. Rounds 72/73/75 never touched it. That series is the
reason this round has mechanics where round 72 had vocabulary.

| Tag | File | Video ID | Runtime | What it carries |
|---|---|---|---|---|
| P2P-STRAT | `p2p_strategy_explained` | TEp3a-7GUds | 43m | the whole sequence, the stop |
| P2P-BOS | `p2p_break_of_structure` | Zzk864cVJek | 12m | exact BOS definition |
| P2P-BIAS | `p2p_daily_bias` | ironJFzNBic | 31m | preconditions, bias formation |
| P2P-TIME | `p2p_time_theory` | L4xz2o23aPQ | 11m | session clock, entry window |
| P2P-RISK | `p2p_risk_mgmt_psych` | hBnD6T1M4w8 | 18m | sizing, real stop distances |
| P2P-LIQ | `p2p_liquidity` | crMqxB_nHhk | 36m | what liquidity is |
| P2P-ADVLIQ | `p2p_advanced_liquidity` | AGmAVyAuBE0 | 54m | level taxonomy |
| P2P-FVG | `p2p_fair_value_gaps` | xX5LTSJ5wwM | 34m | FVG geometry |
| P2P-IFVG | `p2p_inverse_fvg` | 4sRDnVmLcMk | 22m | IFVG trigger, R:R effect |
| P2P-EQ | `p2p_equilibrium` | joe_XTCn5Bs | 14m | equilibrium construction |
| P2P-SMT | `p2p_smt_divergence` | 7dTQA0t8SH0 | 16m | SMT exact definition |
| P2P-IMB | `p2p_advanced_imbalance` | PlsHO33j6B8 | 23m | opening gaps, BPR |
| FULL | `full_tutorial_2026` | yiuFUp0kFz8 | 6h40m | everything, restated |
| LIQ-GUIDE | `only_liquidity_guide` | Vulini8xbB0 | 49m | swing point definition |
| EQ-ONLY | `only_equilibrium_video` | wzq2AMsoJKY | 19m | current toolkit statement |
| UPD-2026 | `updated_strategy_2026` | 8PYgFVB0GHE | 59m | the round-72 source |
| Live trade recaps | `only_setup_that_mattered_103k`, `60630_one_setup`, `one_setup_48305`, `75210_one_day`, `scalp_1min`, `pm_session_trades` | | | documented examples |
| Loss post-mortems | `80k_mistake`, `wrong_timeframe_loss` | | | invalidation rules |

Transcripts are cached at
`/private/tmp/claude-501/-Users-wallacechen/f12ae3f6-df77-43bb-b438-d778ff0c328d/scratchpad/tjr/`
(session scratchpad, not the repo).

---

## 0. What he is actually doing, in one paragraph

He trades **ES and NQ index futures only**, on the **New York cash open**,
in a **20 to 60 minute window**, taking **roughly one trade per day**. The
entire method is one setup expressed on a **cascade of four timeframes**:
a high-timeframe level gets swept, a mid-timeframe chart confirms the
reversal, a retrace into a mid-timeframe zone sets up the entry, and a
**1-minute** structural break fires it. Stops go at the **1-minute swing
that formed during that retrace**, which is why his real stops are
**16 to 35 ticks**. Targets are **other liquidity levels**, not R multiples.

He states the framing himself as four steps, and the wording is stable
across five separate videos:

> "potential for orders to be filled ... confirmation ... continuation
> ... exit" [P2P-STRAT 0:38:23], and the same four beats at
> [P2P-BOS 0:12:00], [FULL 9:37:12], [P2P-STRAT 0:10:43].

---

## 1. PRECONDITIONS

Everything in this section must be settled **before** he looks for a
trade. He does this pre-market, explicitly: "that's before way way way
way before market open" [P2P-STRAT 0:23:03].

### 1.1 Instrument (MECHANICAL)

ES and NQ, always both on screen, always as a pair. "we trade US indexes,
we're really only looking to be trading New York session" [P2P-TIME
0:00:18]. No forex, no crypto, no single stocks anywhere in 30 videos.
He tells forex/commodity viewers outright that the SMT layer does not
apply to them [P2P-SMT, FULL 4:13:52].

### 1.2 Chart timezone (MECHANICAL)

All charts set to **New York / Eastern**, regardless of where the trader
sits. "we're operating on Eastern time" [P2P-TIME 0:03:23]. Every clock
time below is ET.

### 1.3 The session clock (MECHANICAL)

Stated identically in P2P-TIME and FULL:

| Window | Time (ET) | Role |
|---|---|---|
| Asia session | 18:00 to 03:00 | produces Asia session H/L |
| London pre-market open | 02:00 | |
| London session | 03:00 to 08:30 | produces London session H/L |
| NY pre-market | 08:30 to 09:30 | pre-market manipulation happens here |
| **NY open** | **09:30** | |
| **Manipulation window** | **09:30 to 09:50** | expects the sweep here |
| **Entry window ("the macro")** | **09:50 to 10:10** | expects the entry here |
| **Personal cutoff** | **10:30** | no setup by then, no trade |
| PM session | 13:00 | he says he does not trade it |
| Spread hour | 17:00 to 18:00 | no market |

> "if I can't find a trade by 10:30, I'm done for the day" [P2P-TIME
> 0:05:33].

**He explicitly softens his own window** in the same breath: "this doesn't
have to be point-blank period" [P2P-TIME 0:09:32], "I take trades at 10:20
sometimes. I take trades at 9:45 sometimes" [P2P-TIME 0:09:39]. He shows a
worked example where manipulation completed at 09:52 and calls it fine
[P2P-TIME 0:09:20]. Treat 09:30–10:30 as the **hard gate** and 09:50–10:10
as a **soft preference**, because that is exactly how he treats them.

London session end is a **self-contradiction**: "technically London goes
till 11:30 New York time" [P2P-TIME 0:01:09] but he truncates it at 08:30
"because we want to end all of these sessions when the next one is
opening" [P2P-TIME 0:01:16]. LIQ-GUIDE says 11:00 rather than 11:30
[LIQ-GUIDE 0:32:35]. Use 03:00 to 08:30 for the level, since that is what
he actually draws, and record the ambiguity.

### 1.4 Higher-timeframe order flow (DISCRETIONARY, with a mechanical skeleton)

He reads **4-hour and 1-hour** trend first: "identifying what order flow
are we in on the 4-hour and on the 1-hour" [P2P-STRAT 0:21:56]. The trend
definition itself is mechanical (see 2.1). What is discretionary is the
synthesis: he weighs whether HTF fair value gaps are being respected or
disrespected, whether equilibrium held, and where price sits in the swing.

Worked example of the actual reasoning [P2P-BIAS 0:08:09–0:09:10]: price
swept a low, then **closed above** an hourly FVG instead of respecting it,
therefore the down-leg is dead and bias flips bullish. That is a
mechanical test (close through an FVG edge) being used as the bias input.
But which gap, on which timeframe, and how much weight it gets against the
other evidence is by eye.

### 1.5 Mark the draws on liquidity for the day (MECHANICAL to enumerate, DISCRETIONARY to rank)

Before the open he marks, on both ES and NQ:
previous day high, previous day low, Asia session high/low, London session
high/low, and clusters of 1h and 4h swing highs/lows [P2P-STRAT
0:19:03–0:22:29].

**Enumeration is fully mechanical.** Ranking is not. He is asked directly
which one price will target and answers:

> "It's going to sound bad, but you don't need to know" [LIQ-GUIDE
> 0:21:46].

The only ranking statements he makes are (a) "the higher time frames hold
higher power" [LIQ-GUIDE], and (b) a level that has already been swept
with no reaction is dead: "that draw on liquidity is pretty much useless
for us" [P2P-STRAT 0:22:35]. **(b) is mechanical and implementable.**

### 1.6 Daily bias (DISCRETIONARY, and he overrides it live)

Bias = HTF trend direction + which side has the unswept liquidity. "my
bias was bearish. Why? Because on the high time frame, we had a whole
bunch of draws" [P2P-BIAS 0:02:27].

**Critical, and easy to miss: bias is not a filter on entry direction.**
In the single fully-walked trade in P2P-STRAT he comes in bullish and
takes a short:

> "I did have a bullish bias today, but what did the market do? The market
> proved me wrong" [P2P-STRAT 0:39:05].

The live sequence (sweep, then confirmation) **outranks** the pre-formed
bias. Bias tells him where to look first, not what he is allowed to trade.
Any implementation that gates entries on the daily bias is implementing a
rule he does not have.

### 1.7 News (SOFT, contradictory)

Two different positions, both stated:
- Reduce size on data days rather than skip: he halves contract size when
  "we see fundamental data ... there was PPI news data" [P2P-RISK 0:14:23].
- Skip entirely: "I don't plan on trading tomorrow due to interest rate
  decisions" [`wrong_timeframe_loss` 0:01:48]; "Friday I kind of doubt I'll
  trade too because it's CPI news data" [`80k_mistake` 0:55:59].

Record both. There is no stated rule that resolves them.

---

## 2. THE CORE DEFINITIONS (all mechanical, and more specific than we assumed)

### 2.1 Swing high / swing low (MECHANICAL), and this is where we went wrong

> "A high consists of an up candle, then a down candle" [LIQ-GUIDE 0:05:21].
> "A high is two candlestick pattern" [`liquidity_profitable_fast` 0:00:35].

A **swing high** is a two-candle pattern: one up-move candle immediately
followed by one down-move candle. The level is the **highest wick** of the
two. A **swing low** is the mirror: down candle then up candle, level =
the **lowest wick**.

That is the entire definition. There is **no N-bar fractal**, no lookback
window, no minimum-move filter, no ATR gate, anywhere in 237k words. It
confirms **one bar** after the pivot.

The consequence he states explicitly: the "most recent" swing being
monitored **updates constantly**, including to a lower low while still in
an uptrend. He walks it: "we're still in an uptrend even though we end up
making a lower high and a lower low ... this is the most recent low that
we're monitoring" [P2P-BOS 0:09:03–0:09:10].

He also says this pattern is scale-invariant, "this happens on every
single time frame", which means the definition gives no help choosing
which timeframe's swings matter. That choice is discretionary (see 11.2).

### 2.2 Break of structure (MECHANICAL, fully specified)

The single most precisely-defined rule in the entire body of work. He
gives a whole episode to it and screams the wick case.

- In an **uptrend**, monitor **only the most recent swing low**. BOS-down
  fires when a candle **body closes below** it.
- In a **downtrend**, monitor **only the most recent swing high**. BOS-up
  fires when a candle **body closes above** it.
- A **wick through the level does not count**, ever:
  > "It's not a candlestick wick. It's a candlestick closure" [P2P-BOS 0:11:21].
  > "Is this a break of structure? **NO!**" [P2P-BOS 0:08:43], about a wick
  > that ran far below the level.
- The comparison is body-close versus the **wick extreme** of the swing,
  not versus the swing candle's body. He rejects an exact-touch case:
  > "we need the candle body to close underneath the lowest point"
  > [P2P-BOS 0:04:51].
- "Emphasis on the most recent high" [P2P-BOS 0:03:09]: an older, more
  significant swing is **not** the reference. Only the newest one.

Implementable as stated: `bos_down[t] = close[t] < most_recent_swing_low_price`,
where the swing low is the 2-candle pattern of 2.1, refreshed every bar.

### 2.3 Fair value gap (MECHANICAL geometry, DISCRETIONARY size)

Three consecutive candles. Colors are irrelevant: "we do not care what
color the first or the third candlesticks are" [P2P-FVG 0:03:17].

- **Bullish FVG**: `low[3] > high[1]`. The gap is that span.
- **Bearish FVG**: `high[3] < low[1]`.
- If the wicks overlap at all there is no gap: "is there an imbalance
  here? No, because the wicks are overlapping" [P2P-FVG 0:10:45].

**Minimum size: not stated, anywhere.** He waves a marginal one through by
eye: "is this a fair value? Yeah, barely" [P2P-IFVG 0:13:46]. Do not invent
a threshold. This is a real hole in the source.

**Invalidation**: a full **body close through the gap**, same rule as BOS.
A wick into it does not kill it: "we still do not close underneath the
gap, it has not been disrespected yet" [P2P-FVG 0:17:44]. There is **no
50% fill rule**. "Filled" (price traded into it) and "invalidated" (price
closed through it) are two different states and he uses both.

**Stacked gaps (DISCRETIONARY grouping, mechanical once grouped)**: FVGs
that form with no retrace between them count as one zone, and only the
**deepest** one is the true invalidation point. "for this entire trend to
get invalidated, we would have to invalidate this gap down here" [P2P-BIAS
0:15:13]. Deciding which gaps are "stacked with no retrace between" is a
visual call.

### 2.4 Inverse fair value gap (MECHANICAL)

An FVG that gets a **full body close through it** while the trend it
belonged to is still running. Same close-through test as 2.3, but
repurposed: instead of "this gap is dead" it means "the trend is dead".

> "It is not an inverse fair value gap until we get a full candlestick
> closure above the gap" [P2P-IFVG 0:20:48].

Role: a **confirmation** event, interchangeable with BOS, and he prefers
it because it is **earlier**:

> "I use this confluence almost every single day almost more than break of
> structure" [P2P-IFVG 0:11:42], "more often than not it happens before
> break of structure even does" [P2P-IFVG 0:11:49].

**Why this matters more than it looks (see section 5):** the IFVG fires
earlier than BOS, so the stop, which sits at the swing behind the entry,
is **materially tighter**. He quantifies it on a worked example: entering
on the IFVG rather than the BOS made "my stop loss literally two times the
size" smaller, turning a 1:0.45 into a 1:1.3 [P2P-IFVG 0:10:42–0:11:07].
**The entry-trigger choice IS the stop-sizing decision.** They are not
separable.

### 2.5 Equilibrium (MECHANICAL once the range is chosen)

50% of the **most recent swing low to the most recent swing high** in an
uptrend, and the mirror in a downtrend. "It's from the most recent low up
to the most recent high" [P2P-EQ 0:05:32]. He repeats this with visible
frustration across two videos, calling the wrong-anchor mistake the #1
student error. Above 50% = premium, below = discount.

Role: a **continuation** confluence, i.e. the retrace zone he expects the
new trend to pull back into before continuing. Not an entry by itself.

### 2.6 SMT divergence (MECHANICAL comparison, DISCRETIONARY relevance)

ES versus NQ at the **same** swing / same liquidity-sweep event.

- **Bearish SMT**: one index sweeps a high and makes a **higher high**,
  the other makes a **lower high** at the correlated point.
- **Bullish SMT**: mirror, at lows.
- The index making the **less extreme** move (the one that failed to
  sweep) is the **leading** index. **Trade the leading index.**
  > "I'm going to want to be taking the trade on the S&P 500 ... it's the
  > leading index" [P2P-SMT 0:10:39].

He is blunt that the raw pattern is noise outside of a sweep: away from a
draw on liquidity it is "pretty much like useless" [P2P-SMT 0:05:20]. The
co-location requirement (SMT must occur AT a liquidity sweep) is the
discretionary part.

**This is not a hard filter.** It "strengthens my bearish bias"
[P2P-STRAT 0:39:01]. He takes trades without it (see 3.2).

---

## 3. THE SETUPS

There is really **one** setup, run on different timeframe pairs. He says
so: the steps are fixed, the timeframes are not. I split it into the
variants he actually demonstrates.

### SETUP A: "The macro": NY-open sweep reversal (the primary, ~1/day)

This is the trade in P2P-STRAT, and the one he walks in most live recaps.

**Precondition.** Sections 1.1 through 1.6 complete. Clock inside
09:30–10:30 ET. Levels marked on both ES and NQ.

**Step 1, Opportunity (the sweep).** Price trades **through** a marked
draw on liquidity (session H/L, previous day H/L, 1h or 4h swing, equal
highs/lows). Wick through is sufficient to "fill orders"; no close beyond
required, no same-candle reclaim required.
> "the potential of orders to be filled ... by us pushing above a high"
> [P2P-STRAT 0:35:58].

The sweep is **necessary but never sufficient**, stated repeatedly:
> "it doesn't mean that the trend is going to change every single time"
> [FULL 1:44:19]; "just pressing sell once we get above highs is not a good
> strategy" [P2P-LIQ 0:35:23].

A breach with **no reaction** does not count as a tradeable sweep:
> "is it a liquidity sweep? No. Because it's not reacting to it"
> [`liquidity_profitable_fast` 0:16:47]. (DISCRETIONARY: "reacting" is
> undefined, and in practice the reaction IS step 2.)

**Step 2, Confirmation (5-minute).** On the **5-minute** chart, in the
direction **opposite** the sweep, EITHER:
  - (a) a **break of structure** per 2.2, OR
  - (b) an **inverse FVG** per 2.4.

They are explicitly alternatives, chosen by availability, not preference:
> "we didn't have a fair value gap to inverse ... so we had to wait for a
> break of structure" [P2P-STRAT 0:29:45].

**Step 3, Continuation (5-minute).** Price **retraces** and fills a
continuation confluence formed after step 2: a **5-minute FVG** or
**5-minute equilibrium**. Both are acceptable; he checks whichever exists.
> "Via equilibrium and via fair value gaps" [P2P-STRAT 0:36:43].

He is emphatic that filling the zone is **not** the entry:
> "if we just press sell right when equilibrium gets pushed into, then why
> do we even draw equilibrium" [P2P-STRAT 0:32:13].

**Step 4, Entry trigger (1-minute).** This is the two-stage machine, and
it is the part round 72 got structurally right but implemented at the
wrong resolution:

1. While price retraces into the 5-minute zone, the **1-minute** chart
   breaks structure **against** the trade direction (the retrace itself).
   > "on these 5-minute retraces, we are going to break 1-minute structure
   > back to the upside" [P2P-STRAT 0:33:38] (in a short setup).
2. Then the **1-minute** breaks back **in** the trade direction, via BOS
   or IFVG. **That is the entry.**
   > "we just simply wait for a break back down or wait for a change in
   > order flow back down" [P2P-STRAT 0:32:24].

**Explicit alternative (slower, worse fills):** skip the 1-minute and just
wait for the **next 5-minute candle to close** in the trade direction
[P2P-STRAT 0:33:03]. He shows this alternative filling **after his own
TP1 was already hit** [P2P-STRAT 0:37:33]. Two entry variants, both
stated, materially different fills. Record both.

**Stop.** See section 5.
**Target.** See section 6.

### SETUP B: Continuation in an established trend (same machine, no reversal)

Same four steps with step 1 satisfied by an HTF sweep that already
happened, and steps 2 to 4 running **with** the prevailing trend rather
than against the swept level. He walks it in P2P-BIAS: hourly downtrend,
price retraces into an hourly FVG, "if this gets respected, where is price
going to draw? Down to all of these ... draws" [P2P-BIAS 0:02:55].

The mechanics are identical. The only difference is that step 2's
"confirmation of reversal" is replaced by the HTF trend already being
established. Frequency and hit rate are not separately stated for this
variant.

### SETUP C: 1-minute scalp (rare, and he flags it as discretionary)

Compress the whole cascade one tier: sweep on 5m, confirm on 1m, enter on
1m. He describes exactly when he does this, and it is pure judgment:

> "there's a bunch of draws on liquidity that are about to get hit. So, I
> know that there's not going to be a higher time frame confirmation. So,
> I'm going to scale down" [P2P-STRAT 0:09:41].

He then names the source of that judgment directly: "that thought process
will only be built by putting the time required" [P2P-STRAT 0:09:58].
**This variant is not mechanizable from the source.** Flagged, not
approximated. `scalp_1min` is the worked example: triple equal highs
above, wait for a 5-minute low sweep, buy, break-even in ~4 candles.

### SETUP D: PM session (he says he does not trade it, then does)

"We also have PM session that opens at around 1:00 p.m. Me, personally, I
don't trade this" [P2P-TIME 0:04:04]. But `pm_session_trades` is an entire
video of him taking a 10:45 entry and flagging it: "this is way later than
I would typically be trading" [0:36:04]. The setup mechanics are unchanged.
Record as: stated rule = no PM, observed behaviour = sometimes, outside
his own window, self-flagged as atypical.

---

## 4. ENTRY, consolidated

| | Setup A (primary) | Setup A variant (slow) | Setup C (scalp) |
|---|---|---|---|
| Sweep TF | previous day / session / 1h / 4h levels | same | 5-minute |
| Confirm TF | 5-minute | 5-minute | 1-minute |
| Continuation TF | 5-minute (FVG or EQ) | 5-minute | 1-minute or none |
| Trigger | **1-minute** BOS-against then BOS/IFVG-with | next 5m candle closes in direction | 1-minute BOS/IFVG |
| Stated fill quality | best | "you guys are just now entering" while his TP1 hits | earliest |

The trigger is **always an edge-triggered close event**, never a level
touch, never mid-candle. This is invariant across all 30 videos and is the
single most reliable mechanical statement in the body of work.

---

## 5. THE STOP, the thing this project has been getting wrong

### 5.1 The rule

**The stop goes immediately beyond the swing point formed by the retrace
leg that produced the entry.** For a short: above the high of the retrace
into the 5-minute continuation zone. For a long: below the low of it.

Direct statements, three separate videos:

> "I entered this trade once we inverse this [gap] and I put my stop loss
> above these [highs]" [P2P-STRAT 0:35:09], repeated verbatim at [FULL
> 6:24:29].
> "There could have been longs off of that with stops underneath this
> candlestick" [P2P-BIAS 0:07:38].
> "Could have longed off of that. Stops underneath here" [P2P-BIAS 0:07:54].
> "we inverse the gap. I'm going to put my stop loss underneath [it]"
> [`75210_one_day` 1:38:12].

### 5.2 Why that level

Because it is the price that **falsifies the specific claim the entry
made**. The entry claim is "the retrace is over and the new trend
resumes". If price takes out the retrace extreme, the retrace was not
over, so the idea is wrong. It is the invalidation point of the 1-minute
structure, not a volatility measure and not a money-management choice.

This is also why the stop level and the entry trigger are **the same
object**: the swing that the entry BOS/IFVG broke away from IS the stop.
You cannot implement one without the other.

### 5.3 What that means numerically (and this is the falsifiable part)

He gives his real observed stop distances:

> "my stop-loss size on ES was around 16 ticks" [P2P-RISK 0:12:03], and on
> other trades "34 ticks", "28 ticks" [P2P-RISK 0:12:17], with 35 ticks
> quoted as his typical **maximum** [P2P-RISK 0:12:44].

ES tick = 0.25 index points. So his stops are **4.00 to 8.75 index
points**. On ES around 6,000 to 6,900 that is:

**0.058% to 0.146% of price.**

That number is the headline of this round. See section 10.1.

### 5.4 What the stop is NOT

- **Not a percentage.** No percentage stop appears anywhere in 30 videos.
- **Not fixed ticks.** The 16/28/34 figures are *observations after the
  fact*, used only to sanity-check position size. He never targets a tick
  count.
- **Not ATR-based.** ATR is never mentioned.
- **Not swept or optimised.** There is no parameter here to sweep. The
  stop is read off the chart, per trade.

### 5.5 Position sizing (MECHANICAL, and unusual)

He abandoned percentage risk on purpose:

> "I moved away from ... risking only 1% of my account balance per trade,
> and I just went to I'm going to risk this amount of contracts"
> [P2P-RISK 0:10:50].

So: **fixed contract count per instrument**, one number for ES and one for
NQ, and the *dollar* risk floats with whatever the structural stop
happens to be that day. He validates the contract count by checking the
loss at his typical **widest** stop (~35 ticks) is tolerable.

Stated risk band: "usually the sweet spot is anywhere between like 1 to
3%" [P2P-RISK 0:11:43], **immediately contradicted** by "that could
potentially be risking like 3 or 4% ... but I'm willing to do that"
[P2P-RISK 0:13:11]. Record both.

Two stated size-halving triggers (MECHANICAL):
1. stop is "very drastically larger than usual" [P2P-RISK 0:14:14]
2. scheduled fundamental data that day (he names PPI) [P2P-RISK 0:14:23]

**Live behaviour contradicts all of this** on prop-firm evaluation
accounts: "No stop is crazy. It's on a funded ... I'm literally full
porting it" [`one_setup_48305` 0:21:20]. Recorded as a contradiction, not
as a rule.

---

## 6. TARGET

**Targets are other draws on liquidity, in the trade direction.** Same
objects as the entry levels. He states the symmetry directly: draws are
used "as one of two things: entries and targets" [P2P-STRAT 0:24:44].

> "we are looking to exit the trade at possible liquidation points such as
> high time frame highs, high time frame lows, previous session highs,
> previous session lows" [P2P-STRAT 0:41:20].

**Multiple targets, TP1/TP2/TP3**, at successive levels. In the P2P-STRAT
trade: London session lows (TP1), Asia session lows (TP2), hourly lows
(TP3) [P2P-STRAT 0:35:22].

**What is NOT specified anywhere:**
- how position size splits across TP1/TP2/TP3
- which intermediate levels get skipped
- any minimum R:R filter before taking a trade

On the last point: he **reports** R:R after the fact (1:1.3, 1:2, 1:4.81)
and uses it to argue the IFVG entry beats the BOS entry [P2P-IFVG,
P2P-RISK 0:13:47], but never states a floor. He explicitly accepts 1:1
when the stop is wide [P2P-RISK 0:13:20]. **There is no minimum-R rule.**

**Do not model targets as an R multiple of the stop.** That inverts the
causality: in his method the stop is set by 1-minute structure and the
target is set by where the levels are, and the resulting R is whatever it
is. See 10.1.

---

## 7. TRADE MANAGEMENT

| Action | Rule | Status |
|---|---|---|
| Partial at TP1 | Yes, consistently. "close half of my position here" [`60630_one_setup` 0:15:22] | Observed in every live recap; **split % never stated** |
| Stop to break-even | Yes, immediately after TP1. "Rest is at break even" [`60630_one_setup` 0:15:22]; "So, now this is a risk-free trade" [`pm_session_trades` 0:40:54] | Consistent behaviour, **never taught as a rule** in P2P |
| Trailing stop | Once, at a structural point, not a fixed distance: "we'll put the sell stop slightly in profit ... if it comes all the way down here, then we're going to reverse" [`75210_one_day` 1:07:55] | Ad hoc |
| Time exit | Flat by end of session. "close everything here. And we're done for the day" [`only_setup_that_mattered_103k` 0:31:58] | Consistent |
| Discretionary early close | Yes, on boredom/time: "It's just taking too long, bro ... I'm just going to close everything" [`75210_one_day` 1:38:39], **on a winning trade** | Pure judgment |

**Note the gap.** Partials and break-even are the two things he does on
literally every live trade, and neither appears in the taught curriculum.
The Path to Profitability series never mentions break-even or trailing at
all. This is knowledge that exists only in the recaps.

---

## 8. INVALIDATION, when he will NOT take an otherwise-valid setup

Mechanical:
1. **No confirmation, no trade.** A sweep alone is never enough
   [FULL 1:44:19, P2P-LIQ 0:35:23]. An IFVG alone is never enough:
   "we can't just be taking sell positions on inverse fair value gaps ...
   willy-nilly" [P2P-IFVG 0:12:23].
2. **Wick-only breaks do not count** for BOS or FVG invalidation
   [P2P-BOS 0:11:21].
3. **A level already swept with no reaction is dead** and gets dropped
   from the day's map [P2P-STRAT 0:22:35].
4. **A stacked-FVG zone is not invalidated** until the deepest gap is
   closed through [P2P-BIAS 0:15:13].
5. **Past 10:30 ET, stand down** [P2P-TIME 0:05:33].
6. **Do not enter on the zone touch**, only on the confirmation out of it
   [P2P-STRAT 0:32:13].

Discretionary / stated-but-self-violated:
7. **Avoid the first ~10 minutes.** "at 9:41, I typically don't take
   trades during that time" [`60630_one_setup` 0:31:06]; he mocks a viewer
   for entering 7 minutes after the open [`pm_session_trades` 0:07:19].
   He then violates it himself: "Very early trade. Not typical at all"
   [`only_setup_that_mattered_103k` 0:08:53].
8. **Do not trade sick.** "don't trade while you're sick, guys"
   [`wrong_timeframe_loss` 0:49:43], said *after* he misread the 3-minute
   chart as the 5-minute and shorted anyway.
9. **One trade a day.** "I wouldn't really want to be looking for extra
   shorts because I already took my trade" [`one_setup_48305` 0:50:13].
   Violated in `75210_one_day` (two trades) and `80k_mistake` (re-entry
   after a stop-out).

**The `80k_mistake` post-mortem is the single most useful invalidation
document in the set,** because it is him stating the rule and then
breaking it on camera with a timestamp on both:

- Rule stated: "I need one-minute structure to break to the downside ...
  then I'm going to look for a 1-minute break up" [0:11:15].
- Patience stated: "I still do not want to long. I want to be patient"
  [0:21:10].
- Rule broken 10 minutes later, entry basis given as: "What did you enter
  off with? Hopes and [dreams]" [0:31:47].
- Result: "I lost 38K" [0:32:34].
- Same unconfirmed trade re-entered at the same size [0:33:35].
- Result: "84k" [0:53:39].

**The mechanical content of that video is: the step-4 1-minute confirmation
is the load-bearing filter, and skipping it cost $84k in one session.**

---

## 9. FREQUENCY AND HIT RATE

**Frequency (well-supported):** ~1 trade per day, in a 20 to 60 minute
window, with a hard personal stand-down at 10:30 ET. Implied by the
session structure [P2P-TIME] and stated as intent [`one_setup_48305`
0:49:52]. Days with zero trades are normal and he publishes them
(`Live Day Trading Making $0 (NO TRADES TAKEN)`).

**Hit rate: not stated anywhere in the Path to Profitability series.** He
teaches students to compute their own from a journal and never gives his
own number in the course.

The **only** sourced performance numbers are from UPD-2026 (the round 72
video), where TradeZella figures are on screen:
- "daily win rate is around 64% or 64.29%" [UPD-2026, per step72 notes]
- average R:R ~1:1.33
- per-trade averages ~$22k win / ~$16k loss

**Do not treat 64.29% as a per-trade win rate.** He says *daily* win rate,
and he takes ~1 trade/day but sometimes 2, and closes some trades manually
at break-even. Round 72 tested it as a per-trade hit rate. Different
quantity.

Recap-video self-report: "seven wins and one loss" on the month
[`75210_one_day` 1:39:44]. Single month, self-reported, not audited.

**Losses are large and public.** Video titles in the channel include
losing $192,560, $161,430, $151,780, $133,760, $99,500, $97,421, $76,340,
$75,610. Whatever the hit rate is, the loss distribution has a long tail,
and the tail is on record.

---

## 10. WHERE OUR PRIOR TESTING MEASURED A DIFFERENT THING

This is the section the brief asked for, and there are **four**, of which
the first is decisive.

### 10.1 ★ The stop floor excluded his entire real stop range

`step72_tjr.py` sets:

```python
STOP_CAP_PCT = 6.0
STOP_FLOOR_PCT = 0.15
...
def train_median_stop_pct(...):
    return float(min(max(vals.median(), floor), cap))
```

Every trade in round 72 got **one** stop percentage, the **train-set
median** distance-to-swing, floored at **0.15%**.

His actual stops are **0.058% to 0.146%** of price (5.3).

**The floor sits above his widest real stop.** Not near it, above it.
Round 72 could not have placed a stop where TJR places one even by
accident. Every trade it scored used a stop between 1x and 2.5x too wide
at the tight end, and it used the *same* stop on every trade while his
varies per trade by more than 2x (16 to 35 ticks).

Compounding it: `target_pct = stop_pct * rmult`, with R multiple swept.
So the exit was an R multiple of a wrong constant stop, when his exit is a
**price level on the chart** and R is an output, not an input.

**Verdict on the verdict: round 72's "claimed 64.29% WR never reproduces
(42-58%)" was measuring a strategy with a stop 1-2.5x too wide, a stop
that does not vary per trade, and an R-multiple target instead of a
liquidity target. That is not his strategy. It is a different strategy
that shares his entry signal.**

This is the same class of error as round 86's RSI-divergence finding, and
it is bigger, because the stop is where he is *most* explicit.

### 10.2 ★ The swing-point definition is a different object

`step41_shorts.confirmed_swings(d, k)` is a **centered (2k+1)-bar
fractal, shifted k bars** to avoid lookahead. Round 72 ran it at **k=3**,
i.e. a 7-bar window confirmed **3 bars late**.

TJR's swing is a **2-candle pattern confirmed 1 bar later** (2.1).

Two separate consequences:
- **Different level set.** A k=3 fractal returns far fewer, more
  significant pivots. His returns many more, minor ones. "The most recent
  low" is a different price under the two definitions, usually further
  away under ours. Which directly re-inflates the stop (10.1) and
  delays the BOS.
- **Different latency.** 3 bars late on a 1-minute entry chart is 3
  minutes of a 20-minute entry window, 15% of it, gone. His method
  confirms in 1.

`bos_chain` also requires a persistent HH+HL / LH+LL trend state before a
break counts as continuation vs change-of-character. TJR requires no such
state: he monitors the most recent swing unconditionally, and explicitly
keeps monitoring inside an uptrend that just made a lower high and a
lower low [P2P-BOS 0:09:08]. Another different quantity.

### 10.3 ★ The cross-index filter was backwards at the sweep

Round 72 implemented:

```python
def partner_alignment(...):
    """Both instruments' bos_chain 'chain' state must agree..."""
```

That is a **same-direction trend agreement** gate on both ES and NQ.

His actual rule has **two opposite requirements at two different points**:
1. **At the sweep: they must DISAGREE.** That is what SMT divergence *is*.
   One index sweeps the level, the other fails to. "NASDAQ swept out the
   highs, ES didn't" [P2P-STRAT 0:39:45].
2. **He then trades the one that FAILED to sweep** (the leading index)
   [P2P-SMT 0:10:39].

A filter demanding agreement at the sweep **removes his highest-conviction
setup by construction.** Round 72 also found ES survivors only with the
alignment filter *off*, which is consistent with the filter being wrong
rather than the strategy being wrong.

Caveat, recorded honestly: UPD-2026 does contain a genuine
non-alignment veto ("if ES is bullish and NASDAQ is bearish ... I don't
want to take the trade"). Both are real. The reconciliation the videos
support is: **divergence at the sweep, agreement at the confirmation.**
Round 72 implemented the second and dropped the first.

### 10.4 The timeframe collapse removed the setup's defining feature

Round 72's index leg ran at **1-hour** resolution because yfinance caps
intraday history, collapsing steps 2, 3 and 4 into one bar. Its own
docstring flags this as "the loudest, largest approximation".

Now that we have his exact clock: his **manipulation window is 20 minutes
and his entry window is 20 minutes**, inside a 60-minute stand-down. A
1-hour bar cannot represent a 09:30–09:50 sweep followed by a 09:50–10:10
entry. It is one bar. **The entire time structure of the setup is
invisible at that resolution.**

The BTC transfer leg mapped his 5m to our 15m and his 1m to our 5m, a 3x
dilation, on an instrument with **no 09:30 open, no session cutoff, no
pre-market, and no correlated partner index for SMT**. Four of his six
preconditions are undefined on BTC. That leg tested the geometry with the
context deleted.

---

## 11. CONTRADICTIONS, recorded as required

| Topic | Version A | Version B |
|---|---|---|
| Risk % | "sweet spot ... 1 to 3%" [P2P-RISK 0:11:43] | "3 or 4% ... I'm willing to do that" [P2P-RISK 0:13:11] |
| Step-by-step | "I'm not going to give you step one, step two" [P2P-STRAT 0:12:19] | "This is the step-by-step TJR strategy" [P2P-STRAT 0:35:48] |
| News days | halve size [P2P-RISK 0:14:23] | skip entirely [`wrong_timeframe_loss` 0:01:48] |
| PM session | "I don't trade this" [P2P-TIME 0:04:10] | trades at 10:45 and later [`pm_session_trades` 0:36:04] |
| One trade/day | "I already took my trade" [`one_setup_48305` 0:50:13] | two trades [`75210_one_day`], re-entry [`80k_mistake`] |
| Early entries | "at 9:41, I typically don't take trades" [`60630_one_setup` 0:31:06] | "Very early trade. Not typical at all" [`only_setup_that_mattered_103k` 0:08:53] |
| Stops | structural stop, 1-3% risk [P2P-RISK] | "No stop ... I'm literally full porting it" [`one_setup_48305` 0:21:20] |
| London end | 11:30 ET [P2P-TIME 0:01:09] | 11:00 ET [LIQ-GUIDE 0:32:35] / drawn to 08:30 |
| Equal highs tolerance | "dead equal in price" [P2P-ADVLIQ 0:38:49] | accepts 50 cents apart, "close enough" [P2P-ADVLIQ 0:40:55] |
| FVGs as draws | not draws, no obligation to fill [P2P-FVG 0:30:11] | opening gaps are "very strong draws" [P2P-IMB] |

---

## 12. WHAT A BOT CAN RUN TODAY

### 12.1 Fully mechanical, implementable now, no chart read, no judgment

These are specified tightly enough to code from this document alone.

1. Session clock and all session H/L levels (ET, DST-aware).
2. Previous day high / low.
3. Swing highs and lows, **2-candle definition**, 1-bar confirmation.
4. Break of structure: body close beyond the **most recent** swing extreme.
   Wick rejected.
5. FVG detection: 3-candle wick-gap, overlap test.
6. FVG invalidation: body close through the gap edge.
7. IFVG: FVG invalidated counter-trend, used as confirmation.
8. Equilibrium: 50% of most-recent-low to most-recent-high.
9. SMT divergence: ES/NQ higher-high vs lower-high at the same swing;
   identify the leading index.
10. Level-is-dead rule: swept with no reaction, drop it.
11. The 4-step sequence state machine (sweep → 5m confirm → 5m retrace
    into zone → 1m BOS-against then 1m BOS/IFVG-with).
12. **The stop: the retrace swing extreme.** Per trade, from the chart, not
    a parameter.
13. Time gates: 09:30 open, 10:30 stand-down, flat by session end.
14. Fixed contract sizing, with the two halving triggers.
15. Target enumeration: the next unswept levels in the trade direction.

**That is the whole primary setup.** It is more mechanical than round 72
concluded, because the P2P series defines the pieces that UPD-2026 only
narrated.

### 12.2 Needs a chart read we do not have

Codeable in principle, but the source gives no threshold, so building it
means inventing one. Flagged, not filled:

1. **Minimum FVG size.** No number exists. "Yeah, barely" is the standard.
2. **Equal highs/lows tolerance.** "Dead equal" in theory, 50 cents in
   practice, instrument and timeframe unstated.
3. **Which draw on liquidity is "the" one.** He says outright you don't
   need to know. A bot needs to know. This is the largest genuine hole.
4. **How many stacked levels make a cluster "low resistance".** Examples
   run 2 to 5. No minimum stated.
5. **Stacked-FVG grouping** ("no retrace in between"): needs a definition
   of retrace we do not have.
6. **"Reaction" after a sweep** as distinct from step 2's confirmation.
7. **TP1/TP2/TP3 size split.** Never stated. Every live trade uses it.
8. **HTF bias synthesis** (1.4). The inputs are mechanical, the weighting
   is not.

**Recommendation for this bucket: parameterise and sweep these, but label
them OURS, not his.** They are our inventions filling his gaps, and any
result that depends on one of them is a result about us.

### 12.3 Needs Wallace

Not thresholds. Actual judgment calls that the source explicitly assigns
to experience:

1. **Which timeframe to drop to on a given day** (Setup C). He names this
   as the discretionary core and says it only comes from screen time.
2. **Taking the earlier IFVG entry versus waiting for the BOS.** This is
   the stop-size decision (2.4) and he makes it by feel.
3. **Closing a winner early because it is taking too long**
   [`75210_one_day` 1:38:39].
4. **Sizing up or down on conviction**, half-risk when unsure.
5. **The news call**: halve or skip.
6. **Whether today is a no-trade day.**

### 12.4 The honest summary

**Rule count: 84 discrete rules captured** (plus 8 prior-testing mismatch
rows = 92 lines in `step301_tjr_rules.csv`).

| Status | Count | Meaning |
|---|---|---|
| MECHANICAL | 61 | computable from OHLCV + a clock, no judgment |
| DISCRETIONARY | 12 | visual read; the visual is named, no threshold invented |
| PARTIALLY SPECIFIED | 2 | mechanical intent, one number missing (TP split, cluster size) |
| UNSPECIFIED (gap in source) | 4 | FVG min size, equal-highs tolerance, TP split, his own win rate |
| CONTRADICTION | 5 | both versions recorded, no resolution stated |

**73% of his method is mechanical.** That is much higher than round 72
concluded, and the reason is simply that round 72 read the wrong video.

**What changed versus round 72:** round 72 concluded his method was
mostly mechanical with a discretionary stop and target. The opposite is
closer to true. **The stop and the entry trigger are the most precisely
specified things he teaches.** What is actually discretionary is level
selection, timeframe selection, and bias weighting.

**The single highest-value next build** is not a backtest. It is a
faithful re-implementation of 12.1 with:
- the 2-candle swing definition replacing `confirmed_swings(k)`
- a **per-trade structural stop**, with **no floor**, replacing
  `train_median_stop_pct`
- **level targets** replacing `stop_pct * rmult`
- **1-minute and 5-minute** ES/NQ data replacing 1-hour
- **divergence at the sweep**, agreement at the confirmation

Four of those five are corrections to things we built wrong, not to things
he taught unclearly. The data requirement (intraday 1m/5m index futures,
which yfinance will not give us) is the one real external blocker, and it
is a purchase decision, not a research one.
