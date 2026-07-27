# step472 — the four missing pieces of Alex Gonzalez, built

Built 2026-07-27. **Replay only. No order was placed on any venue. OANDA ends
this job, as it began it, with zero orders ever placed.** Nothing outside
`alex_engine.py`, `test_alex_engine.py` and `step472_*` was touched.

Wallace's sentence that started this job, verbatim:

> "to be honest, I dont think alex is the issue. I think you are."

He was right, and this file is the receipt. Four pieces of the man were not in
the step470 build, and one of them — his own go-to pattern — is the one he
names when he is asked how to grow a small account. We graded his prop-firm
plan on a strategy he was not recommending.

| file | what it is |
|---|---|
| `alex_engine.py` | the engine. Every new rule carries its verbatim quote in the module docstring |
| `test_alex_engine.py` | **67 tests, all green** (43 before, 24 added) |
| `step472_alex_replay.py` | the measurement run |
| `step472_alex_results.csv` | every row of every table below |

---

## 0. THE FOUR GAPS, CLOSED — with his words

### GAP 1 — THE HEAD AND SHOULDERS. Built.

It is not a footnote in his material. It is **111 mentions in the ten-hour
course** and the pattern he names in his newest upload of all.

> "my favorites and **the only reversal pattern that you're going to need** is
> going to be this head and shoulders pattern … **This is my go-to pattern.**
> I use this every single day in the market."
> — `grw58BIzotU.txt` 06:49:00, 2025-09-28

The detector is four of his sentences in order, and nothing else:

1. **Structure is drawn on bodies, never wicks.**
   > "this head and shoulders pattern is done to the market structure … that is
   > done to the **BODIES** of the candlestick. **We are not including the
   > wicks at no point** when identifying a head and shoulders."
   > — 06:51:10

2. **The neckline is the broken structure point — not a diagonal line.**
   > "the neckline is going to be based off of the previous structure points
   > which is basically **where the higher low and the shift has been
   > created** … This is the neckline. The neckline is not going to be this
   > imaginary line."
   > — 06:55:37

3. **Nothing is a head and shoulders until that line breaks.**
   > "The head and shoulders will only be valid **once we break the
   > neckline**. If we have not broken the neckline, we cannot count it as a
   > head and shoulders."
   > — 06:56:50

   And that break is, in his own equivalence, the change of character:
   > "That is a shift of structure. That is a change of character. That is a
   > break of structure. This is now bearish." — 06:52:27

4. **The entry is the retest, confirmed by a closed candle.**
   > "**we do not enter the trade on the breakout of the neckline.** We have to
   > wait for price to come back into this area and then retest. And then once
   > it retests, then you look for those candlestick formations here."
   > — 07:02:12

Plus the three rules that surround it:

- **Stop above the wick**, from his newest video:
  > "We shifted, retested, entered this position with **my stop loss above the
  > wick**, my take profit to the next structure point."
  > — `hb7ot1_szWI.txt` 00:28:46, **2026-07-26**

  Note the two different reads in one method: **bodies draw the pattern, the
  wick sets the stop.** Both are his, and they are implemented separately for
  exactly that reason.
- **The pattern has to sit somewhere that matters**, which was missing from
  the first cut of this build and cost real money in the measurement:
  > "You want to make sure that you're getting this head and shoulders pattern
  > **at a resistance**. If you're looking to sell, you want to make sure you
  > can have it **at a support**." — 07:04:36
- **The right-shoulder entry is built and switched OFF because he says not to
  take it**: "extremely high risk. I don't recommend it."

### GAP 2 — STRUCTURE TARGETS. Built, and it is the single biggest improvement.

The flat 1:2 was **ours**, not his.

> "my take profit to **the next structure point**. That is it."
> — `hb7ot1_szWI.txt` 00:28:46, 2026-07-26

> "I always place my take profit where I can have a reaction from that area.
> **The closer the better** and always at a minimum of a 1:2."
> — `DsPLtzjTONI.txt` 00:10:50, 2026-06-22

So: the **nearest** swing level in the trade's direction that still pays his
1:2, stopping a little short of it ("a little bit below the next structure
point", `E3lYZsy8nYE.txt` 00:24:25). And if no level within reach pays 1:2,
**the trade is not taken** — "Do not take a trade that is not worth the risk."
His 1:2 is a filter on which setups are worth having, not a fixed exit.

**On the engulf spine over 12 months this alone took +$24,460 to +$40,156, and
mean R from +0.06 to +0.12.**

### GAP 3 — STRUCTURE-SHIFT EXITS. Built, shipped OFF, and here is why.

step470 called his exit behaviour "unautomatable discretion". That was the
wrong frame — he does define change of character, bluntly:

> "**Change of character is when the market shifts.** When you changes from
> bullish to bearish. Simple. Break of structure is when this was the previous
> structure and we break it." — 06:09:21

Both halves are built: a trade is **cut** when the 4-hour structure that
justified it flips against it, and a winner past target is **held** while
structure keeps confirming, with his own ceiling on the runner:

> "once you get to a one to four, you're at your home run, **trade is done**."
> — `M8wDlKjaQRk.txt` 00:15:07, 2026-04-05

**Both default OFF, and the honest reason is that his own stated management
contradicts them:**

> "once you enter a trade you pretty much just have to **set and forget** …
> You either let the trade hit your stop loss or let the trade hit your
> takeprofit." — 02:47:06

Applying change of character to an OPEN trade is **ours**. It is measured both
ways in section 3 below and it does not pay on either window.

### GAP 4 — QUALITY-WEIGHTED SIZING. Built, and the first version of it was
wrong in a way worth naming.

The dial is his, in every input: how many candles the engulf ate ("the more
candlestick it engulfs, the better"), how many dojis stacked, both triggers
together, the higher timeframes agreeing, his 50 EMA.

> "**Low risk equals high reward** because the odds of you losing a trade that
> has a low risk of losing means that you have a high reward. So meaning **you
> can risk more on low-risk trades**."
> — `LwMsai2ppKc.txt` 00:22:34, 2026-02-22

**The first implementation anchored full size at perfect confluence, which
silently shrank every ordinary trade — a different instruction from the one he
gives, and it cost $23,000 over 12 months** (+$13,652 against +$24,460 flat).
Corrected: a plain valid setup gets the configured risk and confluence scales
it **up** to twice that. His floor for VALIDITY is untouched — still one candle
engulfed.

---

## 1. THE THREE THINGS WALLACE ADDED MID-JOB, ALL BUILT

**His two-a-week cap ships OFF.** Wallace's ruling, verbatim: *"tjr and alex do
that because they dont want to over trade and let emotions in their way. if you
see the setup, take the trade. its a demo at the end of the day."* The cap is
built (`human_cadence_cap`), defaulted off, and measured both ways. **It binds
almost never** — 3 setups refused in five years, 0 in the last twelve months,
because the engine already trades at 1.75/week. Every quality bar stayed
exactly where it was; a test asserts that turning the cap off changes only how
many validated setups are TAKEN and never which setups are VALID.

**The rejection/doji half of his trigger.** Built, and with the piece that was
missing from the naive version: **his dojis are never in mid-air.**

> "the two types of confirmation we look for is **either a rejection, a doji,
> or a bullish engulfing** … But **if you have both of these combined, they
> would be a lot more powerful. The more dojis that you would have, the more
> powerful.** If you have several dojis like this **set in place at a support
> level** and then you get a bullish engulfing candlestick, even better."
> — `BcWxqfcjk9A.txt` 00:03:18, 2026-04-16

A bare rejection candle with no level under it took the 12-month book to
**−$51,503**. Gating it on his own three-touch area of interest — a bar being
RAISED, not lowered — recovered it to **−$5,689**. It still does not pay, and
it ships OFF on dates: **the June-2026 spine is two months newer and cuts back
to the engulfing candle alone.** Newest governs.

**No liquidity-sweep machinery, and it is now doctrine rather than omission.**

> "this right here is what many would call a **liquidity sweep**, a fake out,
> an institutional grab … **it really is almost a big hoax.** It's almost like
> the aliens … there's no like real hardcore evidence."
> — `Rua24ytuHuY.txt` 00:06:29, 2026-06-04

A test now fails the build if the words sweep, liquidity, stop-hunt, judas or
inducement ever appear in this engine. The TJR book in this repo is built on
sweeps; none of it may cross over. A second test does the same for fibonacci —
4 mentions in ten hours, and he calls it a waste of his time.

**The course as backbone.** His area-of-interest definition was re-read from
the course and the engine's level definition was **replaced** to match it:
zones are now drawn on **bodies** ("These are the elbows. The elbows are based
off of the bodies of the candlesticks. At no point are we including wicks
here", 05:19:58) and are bounded by the structure they sit inside ("**You can
only have an area of interest within the higher high and the higher low**",
05:25:22). His only stated invalidation is structural, and he is explicit that
a zone is **not** spent by use, so nothing tracks freshness. His two indicators
were found: the 50 EMA (length 50, source close, offset 0) is in, as a
**confluence that moves size and never validity** — "My indicators are simply
an added confluence … It does not determine my whole entire trade." No-gap
candles is a chart-drawing preference with nothing to implement.

---

## 2. THE REPLAY — per pattern, with the control

Each instrument on its own $100,000, same basis as step470. Costs are charged
inside every net figure and never consulted by a decision. `acct/wk` is the
share of **the account** added per week — not a price move.

### 12 months (2025-07-27 → 2026-07-26)

| | n | /week | won | mean R | net $ | acct/wk | fade mean R |
|---|---|---|---|---|---|---|---|
| step470 spine (what we had) | 120 | 2.31 | 36.7% | +0.06 | **+24,460** | +0.12% | −0.28 |
| + head and shoulders alone | 33 | 0.63 | 39.4% | +0.18 | +23,019 | +0.11% | +0.09 |
| + structure targets alone | 80 | 1.54 | 32.5% | +0.12 | **+40,156** | +0.19% | −0.20 |
| **step472, engulf spine** | 80 | 1.54 | 32.5% | +0.12 | **+51,277** | +0.25% | −0.20 |
| step472, head and shoulders | 18 | 0.35 | 33.3% | +0.10 | +4,219 | +0.02% | +0.05 |
| **step472, both patterns** | 82 | 1.58 | 32.9% | **+0.13** | **+46,507** | +0.22% | **−0.21** |

### 5 years (2021-07-05 → 2026-07-26)

| | n | /week | won | mean R | net $ | acct/wk | fade mean R |
|---|---|---|---|---|---|---|---|
| step470 spine | 703 | 2.66 | 34.6% | −0.02 | −89,085 | −0.08% | −0.22 |
| + structure targets alone | 440 | 1.67 | 31.1% | +0.00 | −26,454 | −0.03% | −0.18 |
| step472, engulf spine | 440 | 1.67 | 31.1% | +0.00 | −13,834 | −0.01% | −0.18 |
| step472, head and shoulders | 101 | 0.38 | 27.7% | −0.12 | −45,015 | −0.04% | **+0.10** |
| step472, both patterns | 461 | 1.75 | 30.2% | −0.03 | −85,748 | −0.08% | −0.15 |

**The control is the standard step471 set: same entries, same days, same stop
distances, direction reversed.**

- **The engulf spine's direction call is real on both windows** — it beats its
  own fade by 0.32R over 12 months and by 0.18R over five years. Structure
  targets made it better on both.
- **The head and shoulders passes on 12 months (n=18) and FAILS on five years**
  — mean R −0.12 against a fade of +0.10. Per the standing rule that is
  reported as noise **and hunted**, not concluded against him. See section 5.

### Per instrument, 12 months, the full build

| | n | won | mean R | net $ | acct/wk |
|---|---|---|---|---|---|
| **EUR/USD — his own configuration** | 18 | **50.0%** | **+0.63** | **+49,562** | **+0.95%** |
| GBP/USD | 32 | 37.5% | +0.33 | +35,705 | +0.69% |
| XAU/USD | 10 | 30.0% | +0.20 | +2,744 | +0.05% |
| GBP/JPY | 22 | 13.6% | −0.62 | −41,503 | −0.80% |

His own configuration is **one pair, EUR/USD**. Running four instruments is our
extension of him and GBP/JPY is where it costs — it is the one instrument whose
direction call is worse than a coin on every cut.

---

## 3. THE PACE — the number that started the argument

He says **+1% to +3% of the account per week.**

| | 12 months | 5 years |
|---|---|---|
| step470, what we had | +0.12% | −0.08% |
| **step472, his own pair EUR/USD alone** | **+0.95%** | −0.00% |
| step472, our four-instrument book | +0.22% | −0.08% |
| step472 + his weekly-close rule, book | −0.06% | **+0.11%** |

**On his own pair, on the last twelve months, the rebuilt engine runs at
+0.95% of the account per week against his stated floor of +1%.** That is the
same order of magnitude as the man, from a build that was forty times under him
this morning. It does not hold over five years, and that is the honest half of
the sentence.

---

## 4. EVERY SWITCH, ONE AT A TIME

12 months / 5 years, net dollars on the four-instrument book:

| switch | 12mo | 5y |
|---|---|---|
| **the shipping build** | **+46,507** | −85,748 |
| his two-a-week cap ON | +46,507 (binds 0×) | −90,762 (binds 3×) |
| structure-shift exit ON | +18,624 | −112,024 |
| runner ON (half past target, 1:4 ceiling) | +28,646 | −133,362 |
| his rejection half ON (level-gated) | −8,461 | −47,112 |
| his high-risk right-shoulder entry ON | +28,275 | −77,398 |
| his engulf floor raised to 3 | −14,458 | +21,017 |
| size anchored at the top instead | +15,623 | −20,107 |
| flat size, no quality dial | +38,142 | −74,570 |
| **his weekly-close direction ON** | −12,268 | **+116,028** |
| top-down layers ON (weekly + daily) | −1,948 | +33,139 |

### The one that matters most, and it is his

> "you need to wait for those weekly candlesticks to close … And those
> candlesticks **opening and closing dictate the direction of the following
> week**."
> — `1dL3xmxA2e0.txt` 00:06:12, 2026-05-25

Over five years, requiring every trade to agree with the **last closed weekly
candle** turns the book from **−$85,748 into +$116,028**, mean R from −0.03 to
**+0.17**, against a fade of **−0.26**. Add his top-down weekly-and-daily layer
on top and mean R goes to **+0.48 at a 45.5% win rate**, against a fade of
−0.58 — the strongest direction signal anything in this project has produced
from his material.

**It does not ship as the default, and the reason is dates, not results.** The
June-2026 spine is his newest teaching and it says one timeframe only and
explicitly throws top-down out for this strategy. The layers are one month and
five months older. Newest governs, so the spine alone ships and the layered
reading is reported beside it. **This is the single biggest open question for
Wallace to rule on**, because it is his rule against his own newer rule, and
the deep window says the older one carries the information.

---

## 5. THE HEAD AND SHOULDERS FAILS ITS CONTROL OVER FIVE YEARS. WHAT IS STILL
## MISSING, RATHER THAN A VERDICT ON HIM

Over 12 months the pattern beats its fade. Over five years it loses to it
(−0.12 against +0.10, n=101). Per the standing rule, the default conclusion is
that the implementation is unfaithful. These are the specific pieces of him
still not in the file, in the order I would build them:

1. **NESTED PATTERNS — his actual A-plus setup, and it is not built.**
   > "It's a very big head and shoulders. Now on this retest of this neckline,
   > **I go down to the 4 hour** … I see a beautiful left head and then right
   > shoulder **retesting the bigger neckline of the head and shoulders**."
   > — 07:08:51
   > "I then go down to the 4 hour … We break this neckline. **I go down to the
   > 1 hour.** On the 1 hour, we then have another left head, right shoulder,
   > on the right shoulder of the head and shoulders on the 4 hour … **I have
   > just told you seven different confluences.**" — 07:37:31

   Every head-and-shoulders in this engine is a lone 4-hour pattern. His is a
   small one sitting on the right shoulder of a big one. That is a different
   and much rarer object and it is the **largest single piece of him still
   missing from this file**.

2. **The higher timeframe he says is stronger.** "the higher the time frame the
   stronger the pattern is going to be." Tested — the daily reading gives only
   14 patterns in five years and is negative — but it needs his session gate
   off (a daily candle closes at 17:00 New York, outside his own window), so
   the daily test is not a clean test of him.

3. **The line chart.** He finds structure on the line chart first and only then
   checks the candles. The engine reads candle bodies, which is the same
   information in a different order, and his "work your way up" scan for
   confluent levels is not reproduced.

4. **His own discretion at the retest.** He looks at the retest and decides.
   The engine takes the first qualifying candle in an 18-bar window. That
   window is ours; he gives no clock.

Everything else he says about the pattern is implemented and quoted.

---

## 6. OURS, NOT HIS — the additions in this step

The full register is in `alex_engine.in_his_words()`, items 15–22. In short:

- **Head and shoulders:** the "at least two body swings beyond the neckline"
  shape test, the 60-bar shoulder window, the 18-bar retest wait, and the rule
  that when two patterns land on one candle the more recent neckline wins. He
  gives no count and no clock for any of them.
- **Structure target:** the 120-bar search and the quarter-of-average-range
  shortfall. "The next structure point", "the closer the better" and "a minimum
  of 1:2" are all his.
- **Structure-shift exit and runner:** ours in mechanism, off by default,
  because his stated management is "set and forget". The runner's 1:4 ceiling
  is his; the half-and-half split is ours.
- **The quality ladder and its anchor:** entirely ours. Every input to it is
  his.
- **Rejection gated on a level:** the gate is his; implementing it as his
  three-touch area of interest is ours.
- **Four instruments:** his spine is one pair. EUR/USD is reported alone
  everywhere for that reason.
- **Running the head and shoulders on the 4 hour** is the spine's timeframe,
  not a claim of his.

## 7. SAFETY

No order on any venue. No fetch, no write outside `step472_alex_results.csv`,
no git, no Render. `tjr_bot.py`, `tjr_crypto.py`, `tjr_desk.py`,
`craig_crypto.py`, `craig_live.py`, `venue.py`, `oanda_api.py` and `daemon.py`
were not opened for writing. The only things this engine imports from another
man's method are the two pure helpers step470 already used — a swing definition
and the project's single sizing function — and a test still asserts that stays
true. **67 tests green**, including a mandatory truncation test proving the
neckline, the shoulders, the head, the entry, the stop and the target are all
derived from closed candles and survive both deleting and corrupting the future.
