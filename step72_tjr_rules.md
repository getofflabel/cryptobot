# step72_tjr_rules.md — round 72: THE TJR 2026 STRATEGY, distilled

Source: full auto-transcript of "My UPDATED Day Trading Strategy (2026)"
(10,622 words, one continuous monologue + live chart walkthrough).
Quotes below are <15 words, paraphrase-anchored to the transcript text.

## 0. What he claims, in his own numbers

- "made over $700,000 from this strategy alone" this year (Jan-Jun 2026),
  broker account +$874,782 gross (TradeZella subtracts fees/swap).
- "daily win rate is around 64% or 64.29%", "average risk-to-reward on a
  trade is a 1 to 3.3" [he says "123.3" verbally = 1-to-1.33].
  "every single winning trade... $22,000... every single losing trade...
  $16,000" -> win/loss dollar ratio ~1.375, consistent with ~1.33R stated.
- No losing month all year (Jan +41k, Feb +148k, Mar +293k, Apr +230k,
  May +34k). Losing WEEKS are explicitly normal and expected.
- Instruments: ES (S&P 500) and NASDAQ (NQ) index futures, ALWAYS
  evaluated as a PAIR. "on both the indexes, we push above session highs."
- He trades live, futures/CFD style ("Trade Zella... directly connected
  to my broker"), NOT crypto, NOT single stocks.

## 1. The four-step setup sequence (his own numbered steps)

**STEP 1 — draws on liquidity (the SWEEP / manipulation).**
"draws and liquidity are essentially going to be session highs, session
lows, 1 hour highs, 1 hour lows, 4 hour highs, 4 hour lows." Price must
push ABOVE a high (or below a low) so the market can "fill orders" that
were resting there — this is the manipulation leg, and it is also later
reused as the EXIT target ("our exit and our entries are based off of
the same exact thing"). MECHANICAL: level = most-recently-completed
session high/low (he names London/Asia/NY sessions explicitly) OR
1h swing high/low OR 4h swing high/low; a break is price trading through
one of these. Requires only a wick/close beyond the level — he never
requires an immediate same-bar reclaim (unlike a classic SMC "sweep"),
just "push above a high."
DISCRETIONARY: which of the several available levels (session vs 1h vs
4h, and which specific prior high among several candidates) is "the"
draw he's watching is chosen by eye in his walkthroughs, not by a fixed
priority rule.

**STEP 2 — confirmation of reversal (5-minute).**
"I'm looking for confirmation that those orders were filled through a
change in trend... a five-minute break of structure or a 5-minute
inverse fair value gap." MECHANICAL, OR-condition: on the 5-minute
chart, EITHER (a) a break of structure (BOS) — "a candlestick closure
above [or below] the most recent high [low]" in the direction OPPOSITE
the Step-1 sweep, OR (b) an inverse fair value gap (IFVG) — a 3-candle
FVG that "gets disrespected," i.e. price closes back through the gap's
near edge, opposite its own formation bias.

**STEP 3 — continuation confluence (5-minute).**
"a five-minute equilibrium or a fair value gap getting filled." He then
explicitly SIMPLIFIES this himself: "we can just say we want a one
minute break of structure to the upside or to the downside" — folding
step 3 into step 4's retrace requirement. MECHANICAL under his own
simplification, folded into step 4 below.

**STEP 4 — 1-minute entry trigger.**
"scale down to the one-minute time frame and... look for a break of
structure to the downside [continuation] or an inverse fair value gap."
Concretely, from worked examples: (i) a 1-minute BOS AGAINST the new
trend first (the retrace: "I want to see a 5-minute retrace... a break
of structure to the upside" while expecting a short), THEN (ii) a
1-minute BOS BACK in the trade direction = the actual entry ("this is
where we want to short"). MECHANICAL two-stage sequence (retrace, then
continuation), both edge-triggered BOS events.

**STOP.** "we can put our stop above the second high" / "stops
underneath the second low" — beyond the retracement swing point formed
during step 4's retrace leg. MECHANICAL in principle (a specific swing
price), but "the second high" is read off the chart by eye each time,
not a formally defined k-bar fractal — APPROXIMATED here as the nearest
confirmed swing extreme on the entry timeframe at trade time.

**TARGET.** "we target our other draws on liquidity" — the next
session/1h/4h high or low beyond entry, in the trade direction, taken in
PARTIALS ("I did have extended takeprofits at this daily low and then at
these lows down here, but I took my first profit and then I moved my
stop loss to break even"). DISCRETIONARY: which intermediate level to
partial at, how much size, and exactly when to move to break-even are
all judgment calls, not a formal rule ("I'll look for intermediate highs
that can be taken out" — no fixed selection rule given).

**RISK PER TRADE.** Never stated as a percentage or fixed dollar/contract
size anywhere in the transcript. UNSPECIFIED / not mechanizable from this
source — flagged, not guessed.

## 2. Filters (explicit, mechanical)

- **Cross-index alignment (hard filter).** "I do not like... you guys
  don't take trades when the two indexes are not aligned... if ES is
  bullish and NASDAQ is bearish... I don't want to take the trade."
  MECHANICAL: both ES and NQ must show the SAME 5-minute trend/BOS
  direction before any entry is taken, in either instrument.
- **No pre-market entries.** "Do we want to be entering during
  pre-market? The answer is always going to be no... wait until market
  actually opens." MECHANICAL: entries gated to the regular NY session
  after 9:30am ET.
- **Soft time cutoff.** "By 10:30, I'm done for the freaking day" if
  the indexes aren't aligned by then — but in another example he takes
  a valid trade at 11:05 once alignment finally resolves. DISCRETIONARY
  / soft — treated here as a testable SESSION-WINDOW parameter (tight
  9:30-10:30 ET vs extended 9:30-11:30 ET), not a hard rule.
- **"Less trades is better."** Explicit, repeated philosophy — not a
  mechanizable rule by itself, but supports NOT loosening any of the
  above filters to manufacture volume.

## 3. Filters/conditions NOT present in the transcript (checked for, absent)

- No news-calendar filter of any kind is mentioned.
- No day-of-week filter is mentioned.
- No stated maximum trades/day or daily loss limit.
- No explicit overnight-hold rule, but every walked example resolves
  same session — treated as an implicit flat-by-session-end day-trader
  constraint (mechanized as a fixed max-hold).

## 4. Mechanical vs discretionary — summary table

| Rule | Status |
|---|---|
| Draws-on-liquidity levels (session/1h/4h H&L) | MECHANICAL |
| Which specific level is "the" target/reference | DISCRETIONARY |
| Step 1 sweep = price trades through a level | MECHANICAL |
| Step 2 confirm = 5m BOS or 5m IFVG (opposite sweep dir) | MECHANICAL |
| Step 3 continuation confluence | MECHANICAL (his own fold-in to step 4) |
| Step 4 = 1m retrace-BOS then 1m continuation-BOS = entry | MECHANICAL |
| Stop = beyond retracement swing ("second high/low") | MECHANICAL intent, DISCRETIONARY exact point |
| Target = next draw on liquidity, partials + BE-stop | MECHANICAL intent, DISCRETIONARY execution detail |
| Risk % per trade | UNSPECIFIED |
| ES+NQ 5m alignment required | MECHANICAL |
| No pre-market entries | MECHANICAL |
| ~10:30 ET soft cutoff | DISCRETIONARY / soft |
| News/day-of-week filters | ABSENT (none stated) |

See step72_tjr.py's module docstring for exactly how each MECHANICAL rule
above is translated into a shift-disciplined signal function, and every
place a DISCRETIONARY rule required a stated approximation.
