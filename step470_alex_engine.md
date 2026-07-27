# step470 — The Alex Gonzalez engine: one method, two venues

Built 2026-07-26/27. Replay only. **No order was placed on any venue tonight,
OANDA included.** The OANDA practice account ends the night with zero orders
ever placed, and the code that touches OANDA (`step470_fetch_oanda.py`) has no
order path in it at all.

Files added, and nothing else was modified:

| file | what it is |
|---|---|
| `alex_engine.py` | the engine. His rules, with the quote for each one in the module docstring |
| `test_alex_engine.py` | 41 tests, all green |
| `step470_fetch_oanda.py` | the read-only candle pull and the spread measurement |
| `step470_alex_replay.py` | the measurement run (`--topdown` for the older reading) |
| `step470_alex_results.csv` | every row of the tables below |
| `step470_spreads.json` | the measured OANDA spreads |
| `data_oanda_*.parquet` | 5 years of candles, 4 instruments, 5 timeframes |

---

## 0. THE SPINE — his newest teaching, and it changed the build

Mid-job Wallace sent **`ag_transcripts/KPVVOa6c6dY_dumb_clean.txt`** — "How
Trading Dumb Made Me a Millionaire Trader", uploaded **2026-06-14**, his newest
teaching by six weeks. It is not a lesson on one piece; it is a deliberate
restatement of the whole method from scratch, and under newest-governs it
outranks everything older.

Its entire content is four choices:

> "This is literally **one time frame, one setup, one entry rule, and one
> session.** That is it."

| | the spine says | and it OVERRULES |
|---|---|---|
| **pair** | **EUR/USD** — "if I were to have to pick one market … it would be EuroUSD" | nothing; the older material never named one |
| **timeframe** | **the 4 hour, alone.** "This video is picking ONE TIME FRAME ONLY" | top-down weekly/daily/4H+1H, `grw58BIzotU.txt` 04:40:37, **2025-09-28**. He throws top-down out by name: "that is a different approach, which is more advanced. And it's not what this video is about." |
| **session** | **pre-London and London.** "one or two hours before London session … like 1 2 in the morning my time zone EST" | the wider 01:00–10:30 window, `grw58BIzotU.txt` 01:11:50, **2025-09-28** |
| **entry signal** | **the engulfing candle, and nothing else.** "it would come down to … the bullish and bearish engulfing candlestick confirmations" | the three-confirmation menu that also allowed rejection candles and stars, `BcWxqfcjk9A.txt` 00:01:58, **2026-04-16** |

Plus **one rule that appears in no older video at all**, the Friday exit:

> "**if you're in a losing position and the weekend is coming up and you're
> halfway through your stop loss, I would probably close before the market
> closes** because when market opens on Sunday when the spreads are quite high,
> that could simply take you out at a loss because of the spread."

That is not a break even — a break-even exit is at the entry price and this one
is at a loss — so "I am not a break even trader" (`ig6Z2Gbk_LE.txt`,
**2025-11-09**) is untouched. It is implemented, gated on both of his
conditions, and measured on and off.

**I built the top-down reading first, then rebuilt on the spine when it
arrived.** Both are in the file: `find_setups_dumb` ships,
`find_setups_topdown` is kept so the conflict is measured rather than asserted.

### And the rebuild moved the answer, decisively

| | 5 years, net $ | won | mean R | 12 months, net $ |
|---|---|---|---|---|
| top-down (the older reading) | **−214,186** | 30.7% | −0.20 | +9,215 |
| **the spine (ships)** | **−89,085** | 34.6% | −0.02 | **+24,460** |

And on the control that actually matters — same entry times, same stop
distances, direction replaced:

| direction taken | top-down build | **the spine** |
|---|---|---|
| the engine's own | 30.0% | **34.8%** |
| a coin flip | 33.6% | 31.0% |
| the exact opposite of the engine's | **38.5%** | 29.3% |
| theoretical no-edge value at 1:2 | 33.3% | 33.3% |

**The top-down build's direction call carried negative information — fading it
beat taking it by 8.5 points. The spine's carries positive information: it
beats a coin flip and beats its own inverse.** Same data, same costs, same
sizing, same measurement. That is the single most important number produced
tonight and it is entirely down to the newer video.

---

## 1. THE CORPUS — dated index, finished

`ag_transcripts/_dated_index.tsv` — **198 uploads, real per-video upload dates**,
range **2021-03-29 → 2026-07-26**. Channel confirmed as `@fxalexg__` (two
trailing underscores), 1.31M subscribers; the handle in the original brief,
`@fxalexg`, is a 74-subscriber gaming channel squatting the name.

Transcripts on disk went from 45 to **54** tonight. I converted the nine
remaining teaching videos that had captions downloaded but no clean text:
`ny7zRePso_U`, `5J01qKDAziM`, `E3lYZsy8nYE`, `nOUJcxt9Ugk`, `BvSC5htaRUw`,
`dsohnQdm9Qs`, `ClwWG0SydYg`, `aEBpEMkx3jE`, `UlATmH-ux3I`. Everything still
missing is lifestyle content — Bugattis, the jet, the mansion, the Super Bowl
streak — and none of it was mined.

**A previous agent's corpus work survived being killed.** The brief said
`ag_transcripts/` held two videos; it holds 198 indexed and 54 transcribed,
and `step464_alex_gonzalez_corpus.md` is a complete 646-line read of them.
I built on that rather than re-pulling.

The anchor document is `grw58BIzotU.txt` — his free 10h 36m course, uploaded
**2025-09-28**. Most of the rules below come from it.

**Never date his material off the title.** "How To Trade Gold in **2026**" was
uploaded 2025-11-09. "The Blueprint To Become a Profitable Trader in **2025**"
was uploaded 2024-12-19.

---

## 2. HIS RULES, AS IMPLEMENTED

Every one carries a verbatim quote, a source file and a date. The full set with
longer quotes is in the `alex_engine.py` module docstring; this is the summary.

**Rows 1, 3, 4 and 5 are SUPERSEDED by the spine** (section 0) and do not ship
— the shipping engine reads the 4 hour alone, has no area-of-interest concept
at all, and takes engulfing candles only. Row 9's window is NARROWED by the
spine to pre-London and London. They are listed because the older material is
what fills in everything the spine leaves unstated, and because the conflict
should be visible rather than quietly resolved.

| # | rule | quote | source, date |
|---|---|---|---|
| 1 | ~~SUPERSEDED~~ Weekly / daily / 4H for direction, 1H for the trigger | "we will be using the weekly, the daily and the 4 hour … these are used to identify trend and area of interest" | `grw58BIzotU.txt` 04:40:37, **2025-09-28** |
| 2 | Structure shifts on the BODY close, never the wick | "If we have not body closed above or below, we are not shifting structure. Very simple." | `grw58BIzotU.txt` 03:44:23, **2025-09-28** |
| 3 | ~~SUPERSEDED~~ An area of interest needs a MINIMUM OF THREE TOUCHES, highs and lows counting toward the same area | "We need to have a minimum of three touches … You can have two touches that are resistance, one touch that is support" | `MhWSZp4yS2c.txt` 00:24:10, **2026-06-28** |
| 4 | He waits for the market to confirm; he does not anticipate, and accepts the worse price | "I'd really rather get an entry down here, but it have the confirmation that it's actually pushing to the downside." | `ig6Z2Gbk_LE_gold_clean.txt`, **2025-11-09** |
| 5 | ~~SUPERSEDED~~ The confirmation is a rejection candle, an engulfing candle, or a star | "either a rejection candlestick or a engulfing candlestick"; "As long as the candlestick engulfs the last two" | `BcWxqfcjk9A.txt` 00:01:58, **2026-04-16**; `grw58BIzotU.txt` 06:36:17, **2025-09-28** |
| 6 | Stop at structure, size derived from it | "I put my stop loss a little bit right above this level"; "this lot size … goes based off of your stop loss" | `grw58BIzotU.txt` 09:09:09 and 01:40:34, **2025-09-28** |
| 7 | 1:2 minimum | "always be a minimum of a one to two risk-to-reward. This is always going to be the minimum of every single trade" | `grw58BIzotU.txt` 08:37:45, **2025-09-28** |
| 8 | **NO break even, NO partials, NO trailing** | "I am not a break even trader. I am either going to have my trade hit my stop loss or have my trade hit my take profit. There's no in between." | `ig6Z2Gbk_LE.txt` 00:18:54, **2025-11-09** |
| 9 | ~~NARROWED~~ Entries only 01:00–10:30 New York; London and pre-London preferred; Sydney and Tokyo never | "You can only get involved in the market from 1 in the morning all the way up to around 10:30 in the morning." | `grw58BIzotU.txt` 01:11:50, **2025-09-28** |
| 10 | No Sunday, nothing after Thursday ~09:00 | "no trades on Sundays. No trades from Thursday on … your main focus is Monday through technically Wednesday London session." | `LwMsai2ppKc.txt` 00:34:43, **2026-02-22** |
| 11 | Few trades | "the max amount of trades that you want to take in a week is anywhere from one to two trades." | `LwMsai2ppKc.txt` 00:04:21, **2026-02-22** |
| 12 | **No news gating** — so there is no news calendar in the engine | "There's no way that I am going to modify my trading approach simply because of a news event" | `grw58BIzotU.txt` 03:01:55, **2025-09-28** |
| 13 | 3% of the account risked per trade, fixed for a calendar month | "it can be anywhere from 3 to 5% of your account"; "I risk 3% for the whole entire month and I stick to it" | `VzMlFZbWA0Y.txt` 00:08:48 and 00:09:39, **2024-01-28** |
| 14 | Gold is traded as a currency pair | "I'm taking this trade as if it were to be a foreign exchange currency pair … based off market structure, not for the commodity that it is." | `ig6Z2Gbk_LE_gold_clean.txt`, **2025-11-09** |

### The one rule that is the sharpest difference from TJR

**10:30 New York is his ENTRY cut-off, not a flatten.** Nothing in his material
closes a position at a clock time. The trade then runs for days and through
weekends. TJR's 10:30 closes the position. Getting this backwards would turn
his method into someone else's, and `test_exits_are_not_gated_by_the_clock_and_trades_live_for_days`
fails if it ever does.

### He held this line on camera, on the gold trade

> "right now we have the rejection that we've been looking for from gold, but
> there's a [expletive] problem and that is that we are out of session or about
> to be out of session. So, I'm going to be very interested in taking this
> trade come London session"
> — `ig6Z2Gbk_LE_gold_clean.txt`, **2025-11-09**

---

## 3. WHAT WAS BUILT

**Method assignment held.** Alex drives forex and gold. Nothing was imported
from TJR's or Craig's judgement. Exactly one import line crosses the boundary —
`from tjr_bot import size_position, two_candle_swings` — and both are pure
helpers with no opinion about when to trade.
`test_only_two_pure_helpers_come_from_another_method` fails if that changes.

**The shipping path is the spine** — `find_setups_dumb`: 4-hour market
structure gives the side, a 4-hour engulfing candle in that side is the trigger,
the bar must close at 01:00 or 05:00 New York, the stop goes beyond the
structure the entry candle came out of, the target is 1:2, and nothing but the
stop, the target or his Friday rule closes it. `find_setups_topdown` is the
older reading, kept and measured beside it.

**Data.** OANDA practice, read-only, **capped at 5 years per Wallace's
instruction tonight** (2021-07-01 → 2026-07-26). GBP_JPY, GBP_USD, EUR_USD and
XAU_USD at 15m / 1h / 4h / 1d / 1w. Daily bars come from OANDA natively at its
17:00 New York boundary, which is where the currency day actually rolls and
where his own daily bodies close — resampling the hour to midnight would put
every daily close five hours off his.

**Gold.** Replays on OANDA XAU/USD candles; would trade live as XAUT-USDT on
BloFin. Charged BloFin's costs, the pairs charged OANDA's.

**Costs, charged and never consulted.** Measured, not assumed:

| instrument | round trip | basis |
|---|---|---|
| GBP_JPY | 0.0156% of the price | OANDA, median during 01:00–10:30 New York, last 120 days |
| GBP_USD | 0.0141% | same |
| EUR_USD | 0.0138% | same |
| XAU_USD → **BloFin XAUT-USDT** | 0.1249% | 0.06% a side measured (`cost_truth.FEE_PER_SIDE`) × 2, plus the 0.0049% spread measured tonight |

No cost figure reaches an `if`, a comparison or a return, and
`test_the_cost_is_charged_and_never_consulted` reads the engine's own source to
prove it.

**Causality.** Every setup is re-derived with every later candle deleted on all
five timeframes at once and must come out identical; the quiet hours are
checked the same way; and a stronger test replaces the future with random
garbage and requires the answer not to move. Higher timeframes are invisible
until they close.

---

## 4. THE NUMBERS — the spine, which is what ships

Each instrument on its OWN $100,000. 3% of the account risked per trade — that
is share of ACCOUNT lost if the stop is hit, not a price move and not a share
of margin. **Leverage is the output.** Every trade closed on his Friday rule is
counted with the rest; excluding them would drop only losers and flatter the
page.

**HIS SPINE IS ONE PAIR, EUR/USD.** Running it on four instruments is OUR
extension, so EUR/USD is broken out everywhere and his own configuration can be
read on its own. Everything enters in pre-London / London, so the session split
is degenerate here by construction — that is his rule, not a missing column.

### Last 12 months — 2025-07-27 → 2026-07-26 (52 weeks)

| | trades | /week | won | mean R | net $ | leverage (median, band) |
|---|---|---|---|---|---|---|
| GBP_JPY | 35 | 0.67 | 22.9% | −0.36 | **−32,980** | 8.5x (4.2–32.6x) |
| GBP_USD | 44 | 0.85 | 40.9% | +0.20 | **+25,613** | 9.4x (2.4–24.1x) |
| **EUR_USD — his own pair** | **27** | **0.52** | **40.7%** | **+0.18** | **+12,533** | **9.1x (3.7–19.8x)** |
| XAU_USD (BloFin XAUT-USDT) | 14 | 0.27 | 50.0% | +0.45 | **+19,294** | 1.8x (0.7–3.4x) |
| **BOOK** | **120** | **2.31** | **36.7%** | **+0.06** | **+24,460** | **8.4x (0.7–32.6x)** |

- 49 weeks had a closed trade; **55% of them ended profitable.** His claim for
  himself is 60–70%. This is the closest the build gets to him.
- Stop distance ran **0.09% to 4.24% as a move in the price**.
- Hold time: median 31 hours, longest 694 hours (28.9 days).
- $19,498 of costs charged. His Friday rule fired 5 times. Zero trades had the
  stop and the target inside the same 15 minutes.

### July 2026 — 2026-07-01 → 2026-07-26 (4 weeks)

| | trades | /week | won | mean R | net $ | leverage |
|---|---|---|---|---|---|---|
| GBP_JPY | 3 | 0.84 | 33.3% | −0.08 | −982 | 11.2x (8.9–25.5x) |
| GBP_USD | 4 | 1.12 | 25.0% | −0.33 | −4,214 | 17.3x (13.2–21.6x) |
| **EUR_USD — his own pair** | **0** | — | — | — | **0** | — |
| XAU_USD (BloFin) | 1 | 0.28 | 0.0% | −1.05 | −3,159 | 1.3x |
| **BOOK** | **8** | **2.24** | **25.0%** | **−0.33** | **−8,354** | **14.8x (1.3–25.5x)** |

Eight trades in four weeks, and **zero on his own pair**. This window cannot
carry a conclusion and is reported because it was asked for.

### 5 years — 2021-07-05 → 2026-07-26 (264 weeks), the background check

| | trades | /week | won | mean R | net $ | leverage |
|---|---|---|---|---|---|---|
| GBP_JPY | 164 | 0.62 | 32.3% | −0.06 | −34,847 | 6.8x (1.4–32.6x) |
| GBP_USD | 223 | 0.85 | 35.9% | +0.04 | +9,704 | 8.2x (2.3–24.1x) |
| **EUR_USD — his own pair** | **184** | **0.70** | **32.6%** | **−0.06** | **−37,580** | **8.4x (1.3–25.2x)** |
| XAU_USD (BloFin) | 132 | 0.50 | 37.9% | −0.05 | −26,362 | 3.8x (0.7–17.6x) |
| **BOOK** | **703** | **2.66** | **34.6%** | **−0.02** | **−89,085** | **7.2x (0.7–32.6x)** |

45% of the 254 weeks with a closed trade ended profitable. His Friday rule
fired 20 times; 4 trades reached our own 30-day cap.

**Cadence check.** 0.5–0.85 trades a week per instrument, and 0.70 on EUR/USD
alone, against his "one to two trades" a week. **The engine does not fire
daily.** That was the brief's correctness test and it passes on every
instrument in every window.

### HIS OWN QUALITY DIAL — and it works exactly as he says

> "**The more candlestick it engulfs, the better.**" … "This right here is
> probably my favorite type of engulfing candlestick simply because what you
> have here is one candlestick that has eaten the last 10 candlesticks."
> — the spine, **2026-06-14**

Swept over the 5 years. This is testing WHERE his instruction applies, not
whether it works:

| minimum candles eaten | trades | won | mean R | net $ (book) | EUR/USD alone |
|---|---|---|---|---|---|
| **≥ 1 — his literal floor, and what ships** | 703 | 34.6% | −0.02 | −89,085 | 0.70/week |
| ≥ 2 | 356 | 33.7% | −0.03 | −41,826 | 0.36/week |
| ≥ 3 | 191 | 35.6% | **+0.03** | **+2,688** | 0.19/week |
| ≥ 4 | 93 | 38.7% | **+0.13** | **+34,756** | 0.08/week |
| ≥ 5 | 54 | 35.2% | +0.04 | +4,133 | 0.05/week |
| ≥ 6 | 31 | 41.9% | **+0.25** | **+21,214** | 0.04/week |

Mean R climbs almost monotonically with the size of the engulf, which is his
sentence confirmed on five years of tape. **The sign of the 5-year book turns
positive at ≥ 3.**

**It is NOT shipped as the default, and that is deliberate.** His literal floor
is one ("the next candlestick … needs to engulf the last candlestick"); the
rest is stated preference. Picking ≥ 4 because it made the most money is
fitting. And the honest cost of the dial is on the right-hand column: at ≥ 4 his
own pair produces **one trade every twelve weeks**, which is nowhere near the
one-to-two a week he says he takes. Something is still missing at the settings
that pay.

### HIS FRIDAY RULE, ON AND OFF — 5 years

| | trades | won | mean R | net $ |
|---|---|---|---|---|
| **Friday rule ON — his** | 703 | 34.6% | −0.02 | **−89,085** |
| Friday rule OFF | 696 | 35.2% | −0.01 | −61,284 |

**His rule costs money on this tape — about $28,000 over five years — and it
ships anyway, because it is his.** Two caveats before anyone reads that as him
being wrong. First, it fired only 20 times in five years, so the difference is
20 trades. Second, and more important: he holds a half-stopped loser into the
weekend "if it's still rejecting" and never defines what that means, so our
version of his rule is **more eager to close than his**. See section 6.

### His 1:2 against his 1:3 — both readings measured

His material contradicts itself and the newer statement is the 1:3 one, so both
were run over the 12 months on the spine:

| | trades | won | mean R | net $ | weeks green |
|---|---|---|---|---|---|
| 1:2 — `grw58BIzotU.txt`, 2025-09-28 (the default; the spine also says "for the 1 to 2") | 120 | 36.7% | +0.06 | +24,460 | 55% |
| 1:3 — `LwMsai2ppKc.txt`, 2026-02-22 | 100 | 29.0% | +0.12 | **+57,027** | 42% |

The 1:3 reading more than doubles the money by winning less often and winning
bigger. The spine sides with 1:2 and 1:2 ships.

### The older top-down reading, for the record

Run it with `python3 step470_alex_replay.py --topdown`.

| window | trades | /week | won | mean R | net $ |
|---|---|---|---|---|---|
| 5 years | 462 | 1.75 | 30.7% | −0.20 | −214,186 |
| 12 months | 85 | 1.63 | 37.6% | +0.04 | +9,215 |
| July 2026 | 6 | 1.68 | 33.3% | −0.14 | −2,485 |

---

## 5. THE HONEST READ

**The spine is a real improvement and it is still not what he describes.** Both
halves of that sentence matter.

### What the newer video fixed

The top-down build was worse than random — fading its direction call beat
taking it by 8.5 points. The spine's direction call beats a coin flip and beats
its own inverse. The 5-year hole shrank from $214,186 to $89,085, mean R went
from −0.20 to −0.02, and the 12-month book went from roughly flat to +$24,460
with 55% of weeks green. **One video moved the sign of the information the
engine carries.** That is the strongest evidence tonight for the standing rule
that his newest teaching governs, and it is a good argument for pulling his
material the moment it appears rather than in batches.

### What is still missing

He claims 60–70% of weeks profitable. On his own pair, at his own settings, we
get **45% over five years and 55% over the last twelve months**. Twelve months
is 27 trades on EUR/USD — too few to separate from luck either way, and the
five-year number is the one with the sample behind it.

Three things say the gap is his judgement rather than a further coding error:

1. **The cadence already matches him.** 0.7 trades a week on EUR/USD against
   his stated one to two. The engine is not over-trading, which was the
   brief's stated failure mode.
2. **His own quality dial turns the sign positive but destroys the cadence.**
   At ≥ 3 candles eaten the five-year book is green; at ≥ 4 it makes $34,756.
   But his own pair then fires once every twelve weeks. He takes one to two a
   week AND only takes the good ones — which means he is finding quality we
   cannot see, not just refusing more.
3. **The gap named in `step464` before this job started is still there.** He
   monitors continuously, extends winners past the planned target while
   higher-timeframe structure holds, and closes manually when structure shifts:
   "you have to know when to set and forget and when to not" (`grw58BIzotU.txt`
   09:20:44, 2025-09-28). No testable definition exists in 198 uploads. A
   literal bracket-order implementation is not what he does, and this
   measurement is what that difference costs.

### What I am NOT saying

I am not saying his method does not work. The spine's direction call carries
positive information, which is the opposite of what the first build found, and
that is a point in his favour rather than against him. What I can support is
narrower: **his rules, taken literally and executed without his judgement,
produce roughly break-even before costs and a loss after them over five years,
and a modest profit over the last twelve months.** That is not yet a reason to
put money behind it and it is not a reason to abandon it either.

### If this is taken further, in the order I would rank it

1. **Find the mechanical version of "the more it engulfs, the better."** His
   dial is directionally confirmed and the profitable settings starve the
   cadence. The answer is probably a quality score rather than a hard floor —
   size of the engulf relative to recent range, where it sits in the swing,
   how long the market had struggled at that level ("has struggled
   significantly to break through this area", his words about his favourite).
2. **Let winners run.** He books 1:4 and 1:5 on tape; the default caps at 1:2
   and the 1:3 run already doubled the money on the same mean R. A
   structure-based target — "this next structure point that's running around
   right here to the left", his words — rather than a fixed multiple is closer
   to what he does and has never been tested.
3. **Pull his uploads weekly, not in batches.** Tonight's largest single
   improvement came from a video six weeks old that we did not have when the
   job started.
4. **Nothing near live capital until the five-year sign turns at his own
   cadence.** Not a recommendation to stand down forever; a recommendation not
   to fund a negative measurement.

---

## 6. OURS, NOT HIS

The full list is in `alex_engine.in_his_words()` and a test fails if an item
goes undeclared. The ones that could change an answer:

0. **HIS SPINE IS ONE PAIR, EUR/USD. Running it on four instruments is our
   extension**, not his instruction. EUR/USD is broken out separately in every
   table so his own configuration can be read on its own.
0b. **`min_engulfed` defaults to 1**, his literal floor. His stated preference
   is much stronger and it is swept and reported rather than silently made the
   default — a setting picked for its result is fitting, a setting picked for
   his sentence is not.
0c. **"Still rejecting" is not implemented.** He holds a half-stopped loser
   into the weekend if it is "still rejecting" and never defines it, so our
   Friday exit is **more eager than his** and its measured cost is an upper
   bound on what his rule would actually cost.
1. **A swing point** is an up candle then a down candle. He draws swings on
   every chart and never defines one. Imported from `tjr_bot.two_candle_swings`
   rather than a second definition being invented in this repo.
2. **The stop buffer** is a quarter of the 4-hour average true range beyond
   the structure. His words are "a little bit right above this level".
3. **The target is exactly 1:2** — his stated floor. Both readings measured.
4. **Entry is the close of the engulfing candle, at market.** He says to wait
   for the confirmation and never says what price he pays.
5. **One position at a time** per instrument, with a two-bar wait after an
   exit. Concurrency is SILENT.
6. **A 30-day cap** on a held trade. He states no cap at all; this exists so a
   replay terminates. 4 trades reached it in 5 years and are scored as neither
   a win nor a loss.
7. **Same-bar ties go to the loss.** Zero trades needed it.
8. **3% of the account risked per trade** — the bottom of his own-money 3–5%
   band, `VzMlFZbWA0Y.txt` 00:08:48, 2024-01-28.
9. **No buying-power clamp** is passed to the sizing function, because its
   clamp divides by the entry price without the quote conversion, which is
   wrong for a yen pair. Leverage is reported and never capped here.
10. **Gold replays on OANDA XAU/USD and would trade on BloFin XAUT-USDT.**
11. Everything in the top-down path (three-touch areas, the ATR touch
    tolerance, the daily-calls-direction rule, the confirmation arithmetic for
    rejections and stars) is retained but **does not ship**; it is the older
    reading, kept so the conflict is measured.

### Left SILENT on purpose

- What makes him close a winner early. No testable definition exists in 198
  uploads, so the engine does not do it at all. **This is the finding.**
- What "still rejecting" means for holding a loser through a weekend.
- A maximum number of concurrent positions.
- Correlation rules between open positions.

---

## 7. SAFETY LEDGER

- **Zero orders placed on any venue.** OANDA was reached read-only, for candles
  and one spread measurement. `alex_engine.py` imports no venue at all and
  `test_no_venue_is_imported` fails if one appears.
- **No git commands run. No Render. No deploy.**
- `tjr_bot.py`, `tjr_crypto.py`, `tjr_desk.py`, `craig_crypto.py`, `venue.py`,
  `oanda_api.py` and `daemon.py` were **not modified**. `oanda_api` is imported
  by the fetch script only; `tjr_bot` is imported for two pure helpers only,
  and `test_only_two_pure_helpers_come_from_another_method` fails if that
  widens. Methods never mix.
- **Data capped at 5 years** per Wallace's instruction tonight. Nothing older
  than 2021-07-01 was fetched and no measurement on a longer window is
  reported.
- Downloads went only into `ag_transcripts/`, and tonight's were local VTT →
  text conversions of captions already on disk.
- **Tests: 41 new, all green.** Full suite: **764 passed, 13 failed.**

  Eleven are the known pre-existing failures in the retired books, unchanged:
  `test_breakout_book` ×4, `test_diver` ×2, `test_newsdesk_exit` ×2,
  `test_newsdesk_timing` ×1, `test_state_save` ×2.

  The other two belong to the agent working on the desk and on Craig tonight,
  not to this job:
  `test_craig_live.py::test_the_stock_and_gold_paths_are_untouched` — a file
  that did not exist when this job started (`craig_live.py` and its test were
  written at 22:57) — and
  `test_tjr_desk.py::test_the_day_budget_is_not_spent_twice`. **Both pass on
  their own**, so they are cross-test state leaks inside a repo being edited
  concurrently, and **neither file contains the string "alex"**. Nothing this
  job added is reachable from either.

  For completeness: an earlier full-suite run tonight failed a *different*
  desk test (`test_the_desk_names_each_venue_once_and_only_in_the_table`) which
  now passes. The desk's failures move between runs as that agent works. Mine
  do not move: `test_alex_engine.py` is 41/41 alone, 41/41 alongside the desk
  suite, and 41/41 inside the full run.
