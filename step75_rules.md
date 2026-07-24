# step75_rules.md — round 75: PB Blake's "NEW UPDATED Trading Strategy for
# 2026" (4-step SMC model), distilled

Source: full auto-caption transcript of "My NEW UPDATED Trading Strategy for
2026 (70% Winrate)" (YouTube channel **PB Blake**, video id `9O6JU5_xTd8`,
uploaded 2026-05-30, runtime 32:40, 121,346 views / 5,135 likes / 86,200
subscribers as of 2026-07-24). 7,657-word transcript from yt-dlp's
auto-generated `.vtt` captions (`--extractor-args "youtube:player_client=
android"` was required — the default `web` client hit a 429; the android
client's auto-subs pulled clean, non-duplicated text, verified by an n-gram
repetition scan finding no caption-merge artifacts). Quotes below are <15
words, paraphrase-anchored to the transcript text.

## 0. Who he is and what he claims

- Channel "PB Blake" (86.2k subs). Self-described: "I have been trading for
  around five years now, so I am able to use discretion." Runs a paid "1%
  mentorship" (plugged at the end) with a "student success coach"; cites two
  named students' payout anecdotes (marketing testimonials, not his own
  track record) — **not independently verifiable, not treated as evidence
  of the strategy's own performance.**
- **Headline/repeated claim: "70% win rate"** — in the title and stated
  verbatim multiple times ("I use every single day in order to have
  profitable days and have a 70% win rate", "...so you can stay on side
  that 70% win rate statistic"). No sample size, no date range, no
  broker/journal screenshot is ever shown to substantiate the number —
  unlike round 72's TJR (TradeZella figures on screen) or round 73's Alex
  Gonzalez (in-platform stats screenshot), **this video shows ZERO
  performance-tracking software or aggregate P&L figures on camera.** The
  only concrete dollar figure is a single anecdote: "I ended up making
  around 11k today" (one day, no context for account size or risk %).
- **Stated R:R: "I really aim for that 1:1 RR to 1:3 RR... targeting
  low-hanging fruit"** — explicitly NOT holding to full higher-timeframe
  draws; he says he'll settle for a 1:1 if he lacks full conviction, up to
  a stated ceiling near 1:3, occasionally more with high conviction
  (no upper bound given for that case).
- **Instruments actually shown on screen: NASDAQ (NQ) as the primary traded
  chart, ES (S&P 500) used explicitly as an "SMT" cross-check reference on
  every worked example** ("I also like to look at ES and see if it's doing
  relatively the same thing", "we formed a bullish SMT... because ES ended
  up sweeping it out... whereas the NASDAQ did not"). No forex, no crypto,
  no other instrument is ever mentioned or shown.
- Video description/title claims "for the 2026 markets" broadly but the
  content and every worked example is index-futures/CFD day trading only.

## 1. The four-step model (his own numbering)

**STEP 1 — Bias + higher-timeframe draw on liquidity.**
"you need to be able to define the bias and the higher time frame draw on
liquidity... this simple step right here fixes win rate more than anything
else." Two-question method: (a) "what fair value gaps are we respecting
versus disrespecting?" — bullish bias respects bullish FVGs (they hold as
support) and disrespects bearish FVGs (price closes through them); bearish
bias is the mirror. (b) "what swing high or low are we going towards?" —
the nearest HTF swing extreme in the bias direction becomes the day's draw
on liquidity. Timeframes: "daily... 4-hour... 1-hour... 15-minute," mostly
anchored on daily/4h/1h. MECHANICAL INTENT (a directional gate that
eliminates counter-trend trades — "trade with the trend, the trend is your
friend"), but the FVG-respect/disrespect read is qualitative, no numeric
threshold given for how many gaps or how cleanly they must hold/break.

**STEP 2 — Identify a valid key level.** Timeframes: "3-minute, 5-minute,
15-minute, 30-minute, 1-hour, and 4-hour." Three named sub-types (any one
qualifies):
- **Fair value gap** — "an unmitigated fair value gap or an intermediate
  high/low inside of the gap." If the gap was already tapped once
  (e.g. premarket), the intermediate high/low INSIDE it (not the gap
  edge) becomes the valid level instead — "we cannot use this area right
  here as a key level... instead what we have to wait for is for this low
  inside of this gap to get swept."
- **CISD (change in state of delivery)** — his own coined term: "a body
  close above a candle or series of down closed candles that hit a fair
  value gap or an intermediate low" (bullish; mirror for bearish, body
  close below a series of up-closed candles). MECHANICAL INTENT but the
  candle-RUN boundary ("a candle OR SERIES of candles") has no stated
  minimum/maximum length.
- **Rejection block** — "a bullish wick that traded into a fair value gap
  or an intermediate low... and this is a bearish wick" for the bearish
  mirror. A wick-based reaction zone, again no numeric wick:body ratio.
- **SMT (smart money technique) divergence**, shown as an added confluence
  at the key level rather than a separate named step: one paired
  instrument (ES or NQ) sweeps its own equivalent swing level while the
  OTHER does not, at the same key-level test — "ES ended up sweeping it
  out... whereas the NASDAQ did not" (bullish reading: the instrument that
  HELD, i.e. did not sweep, is the one traded long). DISCRETIONARY IN
  PRACTICE (no stated rule for exactly how close in time/price the two
  instruments' levels must be to "count" as the same test).
No priority order or minimum-touch count is given for choosing among the
three key-level sub-types — DISCRETIONARY which one he's using at any
moment in the worked examples.

**STEP 3 — IFVG (inversion fair value gap) confirmation, "highest
timeframe in the manipulation leg."** Timeframes: "1-minute, 2-minute,
3-minute, 4-minute, and 5-minute" (he also says the 30-second chart is
usable "if you are more of an intermediate trader"). Rule, stated
precisely: define the "manipulation leg" as the swing-high-to-swing-low (or
mirror) that hit the step-2 key level; scan that leg for fair value gaps
across 30s/1m/2m/3m/4m/5m and identify the SINGLE HIGHEST timeframe on
which a gap exists inside that leg; wait for THAT gap to invert (a body
close back through its near edge) before entering — "nine times out of
10... I'm waiting for the highest time frame inversion." Explicitly stated
as a common beginner mistake to use a LOWER timeframe gap instead ("the
reason being because we haven't actually distributed through the whole
entire leg"). MECHANICAL, precisely defined rule — the clearest, most
specific mechanical rule in the entire video — but requires simultaneous
sub-minute (30s/1m) resolution data this repo cannot obtain at 60/20/20
gauntlet depth for ANY instrument (flagged in section 5 below).

**STEP 4 — Execution and risk management.**
- Entry: "typically just entering on the body closure of the IFG" (market
  order at/after the inversion close); if risk looks too wide off that
  close, "I'll either set a limit order at the IFEG or at the CISD"
  instead. DISCRETIONARY choice between the two, gated on an unstated
  risk-reward threshold ("it's really only if my risk reward is trash").
- Target: 1:1 to 1:3 RR, "low-hanging fruit" (nearest opposing HTF swing
  the current setup can realistically reach), NOT the full step-1 draw —
  see section 0.
- **Stop: "this really varies... at the swing low or high... at the body...
  at the fair value gap... sometimes even there's an order block."
  Explicit default: "I'll say that's for the majority of the trades where
  I put my stop loss is usually at the swing low."** MECHANICAL default
  (nearest confirmed swing extreme), DISCRETIONARY the rest of the time.
- **Max trades/day, explicit and numeric: "one to two trades a day max...
  one win, I am done for the day and one loss, I am probably also done
  for the day... if I take two losses in a day, then I am done for the
  day."** A conditional-on-outcome rule (win->stop, 2 losses->stop, up to
  1 more A+ setup allowed after a stop-out) — MECHANICAL INTENT,
  APPROXIMATED here as a flat hard cap because his own rule requires
  knowing a trade's REALIZED P&L before generating the NEXT signal, which
  this repo's signal-then-score architecture does not support without
  duplicating the backtest engine inside signal generation (stated
  simplification, see step75_video.py).
- **Session: "only trading from 9:30 a.m. to 11:00 a.m. Eastern time...
  the golden hour... it is very very rare I'll execute [past] 11:00."**
  MECHANICAL, mostly-hard window with a stated rare exception ("that's
  really only if 9:30 to 11:00 has been really bad... and if we generated
  a lot of liquidity") — mechanized here as a swept TIGHT vs EXTENDED
  window, same idiom as round 72's TJR ~10:30 soft cutoff.

## 2. Explicit numeric claims (for the required claimed-vs-realized check)

- Win rate: **70%** (title + repeated verbatim in-video).
- Risk:reward: **"1:1 RR to 1:3 RR"** typical, no fixed target, some trades
  held past 1:3 on high conviction (no ceiling given for that case).
- Max trades/day: **1-2**, outcome-conditional (see step 4 above).
- Session: **9:30-11:00am ET**, rare extension past 11:00.
- No dollar/percentage risk-per-trade is EVER stated (checked the full
  transcript for "%", "percent", "risk" near any number — the only hits
  are the win-rate and R:R figures above; sizing itself is never given).
  UNSPECIFIED / not mechanizable — flagged, not guessed, exactly like
  round 72's TJR and round 73's Gonzalez risk-sizing gaps.
- No total account P&L, no time-in-market track record, no broker/journal
  screenshot — unlike round 72/73's videos, this one shows NO aggregate
  performance evidence on camera at all.

## 3. Filters/conditions checked for and NOT present

- No news-calendar filter, no day-of-week filter.
- No explicit stop-loss distance formula (pips/ATR/%) — "this really
  varies," no numeric example given anywhere in this video (unlike round
  73's one worked pip example).
- No explicit statement on shorting frequency vs. longing frequency beyond
  step 1's "trade with the trend" (he notes late-cycle bullish bias has
  made him mostly long lately — a market-regime remark, not a rule).

## 4. Mechanical vs discretionary — summary table

| Rule | Status |
|---|---|
| Bias = HTF trend direction (FVG respect/disrespect + swing target) | MECHANICAL intent, qualitative FVG-hold read not numerically specified |
| Key level: FVG (raw or intermediate H/L) | MECHANICAL intent, no touch-count/size threshold |
| Key level: CISD (body close through opening of a same-direction candle run) | MECHANICAL intent, run length unspecified |
| Key level: rejection block (wick into a FVG/intermediate H/L) | MECHANICAL intent, no wick:body ratio given |
| SMT divergence (partner sweeps, self doesn't, at the key level) | MECHANICAL intent, DISCRETIONARY time/price "same test" tolerance |
| IFVG = highest-timeframe-in-leg inversion, 30s-5m | MECHANICAL, precisely stated — but below this repo's honest data-depth ceiling (section 5) |
| Entry at IFVG body-close (or limit at IFVG/CISD if risk too wide) | MECHANICAL default, DISCRETIONARY fallback trigger |
| Target 1:1-1:3 RR, "low-hanging fruit" | MECHANICAL floor/ceiling stated, DISCRETIONARY beyond it |
| Stop: swing low/high (majority), else body/FVG/order-block | MECHANICAL default (swing extreme), DISCRETIONARY alternatives |
| Max 1-2 trades/day, outcome-conditional | MECHANICAL intent, APPROXIMATED as flat cap (engine-architecture reason stated above) |
| Session 9:30-11:00am ET, rare extension | MECHANICAL, mostly-hard, swept tight/extended per round 72's idiom |
| Risk % per trade | UNSPECIFIED |
| Win rate 70% / RR 1:1-1:3 | CLAIMED, unverified on camera (no journal/broker screenshot shown) |

See step75_video.py's module docstring for exactly how each MECHANICAL rule
above is translated into a shift-disciplined signal function, and every
place a DISCRETIONARY or data-depth gap required a stated, non-guessed
approximation.
