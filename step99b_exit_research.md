# Step 99b — How Real Traders Actually Place Stops and Targets

**Round 99, Part 2. Literature only — no backtests run, no commits, no live
orders.** The exit-side companion to `step85_winning_trades.md`. Same
discipline: collect documented rules with their stated reasoning and
scenario, attribute everything, record disagreement rather than picking a
winner. Writes exactly two files: this one and `step99b_exit_methods.csv`.

**The owner's framing, verbatim:** *"there's, like, long trades where
you're in there for like a day, or there's downtrends or uptrends where
you're really riding a candle, or if you're just in consolidation and
you're trying to go into a mean reversion"* — and the corrected principle
that governs the whole file: **a stop is a LEVEL where the idea is proven
wrong, read off the chart, never a tuned percentage.**

**Units, per `BLOFIN_API_REFERENCE.md`:** almost everything below is
sourced as a **price-percentage** or an ATR multiple. The owner only sees
PnL as a percentage of margin on his screen. Every numeric example in this
file that plausibly maps onto a live BTC trade is given in both units
using this repo's own measured conversion: **margin% = price% ×
leverage**, and this project's own measured BTC 1h TRAIN-median ATR14% of
**1.21%** (`step59_exit_science.py`) as the reference volatility, at the
live STRIKES/NEWSDESK leverage of **20x**.

---

## 0. Relationship to `step59_exit_science.py`

This repo already ran a BACKTEST of six exit modules (X0-X5: fixed
target, prev-swing target, liquidity-pool target, structure-trailing,
partial+breakeven hybrid, ATR chandelier) against four live entries.
That work is empirical, not literature — this file supplies the
literature side R85 supplied for entries: what practitioners say they do
and why, organized by the scenario the owner named. Where step59 already
tested something described below, it's noted so the backtest and the
literature aren't confused with each other. The clearest gap step59
leaves: it never tested a mean-reversion-specific target (midline/POC vs.
opposite edge), never tested a moving-average trailing exit, never tested
Parabolic SAR, and never tested a genuine **conditional** time stop
("exit if no progress," as distinct from the hard time CAPS it already
has). See §7 for the full list.

---

## 1. SCENARIO: Trend rides

**What actually keeps you in.** Every source in this scenario agrees on
the mechanism, not just the vibe: a *trailing* stop that only ever moves
in the favorable direction, recalculated from realized price/volatility,
never a static level set once at entry.

- **Chandelier Exit (Chuck LeBeau, popularized by Alexander Elder in
  *Come Into My Trading Room*).** Exact rule: `stop = Highest High(22) −
  3.0 × ATR(22)` for longs (mirrored for shorts off the lowest low), the
  22-period lookback chosen to approximate one trading month. Ratchets up
  only — it can never move against you. Prescribed explicitly for
  **trending markets**; the entire premise is staying in until a real
  trend reversal, not getting flushed by a normal pullback. **[LeBeau/Elder, via StockCharts ChartSchool](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/chandelier-exit)**

- **Generic ATR trailing stop.** Same mechanism, tuned multiplier by
  regime: **1.5-2x ATR** for ordinary swing trades, widened to **2.5-3.5x
  ATR** specifically "to avoid being shaken out by normal pullbacks" in a
  **strong** trend — the multiplier itself is the tool for avoiding the
  shakeout the owner asked about, not a separate mechanism. Most swing
  traders converge on 2-2.5x as the practical middle. On this repo's own
  BTC 1h ATR (1.21%), a 2.5x trail = 3.0% price = **60% of margin at
  20x**; 1.5x = 1.8% price = **36% of margin**. **[Pro Trader Dashboard](https://protraderdashboard.com/blog/atr-based-stops/), [Aurra Markets](https://www.aurra.markets/academy/advanced-guides/the-4-best-trailing-stop-strategies-to-maximize-profit)**

- **Structural (swing-low/high) trailing stop.** Exact rule: the stop
  moves to the most recent CONFIRMED swing low (long) / high (short), and
  only ever ratchets in the favorable direction as new higher lows (or
  lower highs) print. No ATR or fixed distance at all — the chart's own
  structure sets the distance. This is functionally identical to
  step59's own X3 module, which this repo already found to be the single
  clean survivor for its fast BTC tactical entry (E1 STRIKES) and the
  decisive winner over non-structural ATR trailing on the two fast crypto
  entries specifically (`step59_results.md` §5). **[mywinnerdays.com](https://mywinnerdays.com/trading-journal/trading-basics/trailing-stop-take-profit/)**

- **20-EMA close-below exit.** Exact rule: exit when price CLOSES beyond
  the 20-period EMA — an intrabar wick through it is explicitly NOT the
  trigger, only a completed close is. Reasoning given: the 20-EMA is
  called the trend's "center of gravity," and a mere touch is treated as
  noise while a close through it is treated as the actual regime change.
  One source states one daily close below the 20MA is sufficient to
  "invalidate the trend regime." This is a genuinely different mechanism
  from the swing-low trail above (it trails to an indicator level, not a
  price-structure point) and was NOT one of step59's six modules. **[TradingSim](https://www.tradingsim.com/blog/20-moving-average-pullback), [TradingWithRayner](https://www.tradingwithrayner.com/trailing-stop-loss/)**

- **Parabolic SAR.** Exact rule: stop sits at the current SAR dot, which
  ratchets automatically along the trend per its own acceleration
  formula. Explicitly prescribed FOR trending markets only — warned
  explicitly against ranging markets ("generates excessive whipsaw").
  One source claims it captures 60-80% of directional moves when
  trending, and that pairing it with a trend filter (ADX > 25, or price
  above a 50-day MA) cuts false signals by roughly 35% in backtesting —
  both numbers self-reported by a secondary source, not independently
  verified here. Not tested anywhere in this repo. **[TradeAlgo](https://www.tradealgo.com/trading-guides/technical-analysis/parabolic-sar-the-trailing-stop-indicator-for-trend-traders)**

**Is a fixed target ever used in a trend, or is trailing universal?**
The clearest doctrinal answer in this haul is Richard Dennis's (Market
Wizards): *"The correct approach is to say: This structure means up, and
this structure means up no more, but never that this structure means up
this much and no more."* i.e., trend followers as a group explicitly
reject a fixed profit target for a trend-riding trade — the trailing stop
IS the exit, full stop (no pun avoidable). Ed Seykota's own described
process (identify a trend, act on it, manage risk, let it run) is
consistent with the same doctrine. This is a qualitative, not numeric,
finding — no source in this scenario gave a countervailing "use a fixed
target in a trend" rule with its own stated reasoning. **[Market Wizards, via thetrendfollower.com](https://www.thetrendfollower.com/2016/11/a-famous-lesson-for-turtles-from.html), [Dr Wealth summary](https://drwealth.com/wisdom-from-market-wizards/)**

---

## 2. SCENARIO: Mean reversion in consolidation

Direct answer to the owner's question: **the target is the midline / the
range's Point of Control (POC), not the opposite edge — every source that
gave a concrete rule agreed on this.**

- **Target placement.** Exact rule (FXNX): *"When you enter at the edge,
  don't aim for the opposite side immediately. Aim for the POC."* The POC
  is the high-volume/fair-value node inside the range, not the geometric
  midpoint necessarily, but functionally close to it. Reasoning given:
  POC is where the most trading agreement occurred historically, making
  it a more probable magnet than the far, less-tested extreme. One
  secondary synthesis offers a two-stage version: first target = the
  moving average/mean, second target = range mid or the opposite band —
  i.e., even sources that eventually allow the far edge treat it as a
  SECOND target, never the first. **[FXNX](https://fxnx.com/en/blog/mastering-range-trading-math-of-the-middle-avoiding-chop)**

- **Stop placement.** Exact rule: **1.5-2x ATR beyond the range
  boundary** (not at the boundary itself). Worked example given: 1H ATR
  = 10 pips, support at 1.2500 → stop below 1.2500 minus the ATR buffer.
  Reasoning: absorbs the wick noise that a well-tested, widely-watched
  level attracts without moving the stop so far the trade's R:R breaks
  down. On this repo's own BTC ATR (1.21%), 1.5-2x = 1.8-2.4% price =
  **36-48% of margin at 20x**. **[FXNX](https://fxnx.com/en/blog/mastering-range-trading-math-of-the-middle-avoiding-chop)**

- **Context required before the fade is even valid.** 2-3 clean prior
  touches/rejections at BOTH range boundaries (matches R85's own S/R
  checklist finding exactly — this is the same "2+ touches" condition
  R85 found for S/R divergence and pivot trades, now confirmed
  independently on the exit side). One variant adds a liquidity-sweep
  confirmation: price must briefly breach the edge and close back inside
  before the fade is valid — structurally the same "sweep-then-MSS" logic
  R85 documented for liquidity-sweep reversals. **[Blofin Academy](https://blofin.com/en/academy/education/range-trading-strategies), [FXNX](https://fxnx.com/en/blog/mastering-range-trading-math-of-the-middle-avoiding-chop)**

- **Explicitly warned against.** Using this exact logic in a market that
  is trending on a HIGHER timeframe. FXNX's own phrasing: a range that is
  actually "a bull flag on the daily chart will 'steamroll' mean-reversion
  trades" — the same verb Plisio used in R85 for regular RSI divergence
  failing in the March-2024 BTC trend. The failure mode is identical
  across both rounds: fading/reverting against a trend that hasn't
  actually exhausted. **[FXNX](https://fxnx.com/en/blog/mastering-range-trading-math-of-the-middle-avoiding-chop)**

- **Time stop specific to this scenario.** Exit if price shows no
  progress toward the midline within **5-8 candles** — a range fade that
  isn't moving is more likely failing than slow-winning (see §6).
  **[Blofin Academy](https://blofin.com/en/academy/education/range-trading-strategies)**

Note against step59: neither X1 (prev-swing target) nor X2 (liquidity-
pool target) is the same rule as "target the POC/midline of an active
range" — both of step59's target modules were built and tested on
trend-context entries (STRIKES, NEWSDESK, gold breakout), not on a range-
fade entry. **A range-specific stop/target combination, as literally
described by the mean-reversion literature, has not been tested in this
repo at all.**

---

## 3. SCENARIO: Breakout continuation

- **Measured-move target.** Exact rule: project the height of the prior
  impulse leg ("flagpole") from the breakout point. Worked numeric
  example: pole from $50→$70 ($20 tall), flag breaks out at $67, target =
  $67 + $20 = $87. Explicitly framed as a *minimum expected advance*, a
  reference level from pattern geometry, not a guarantee. Continuation
  rate for "textbook" flags (strong high-volume pole, shallow retrace
  under half the pole on declining volume, breakout on expanding volume)
  cited at **60-70%** in "studies of classical chart patterns" — self-
  reported, source did not cite the underlying study by name.
  **[FinWiz](https://finwiz.io/chart-patterns/bull-flag), [Alchemy Markets](https://alchemymarkets.com/education/strategies/continuation-patterns/)**
- Stop and volume-confirmation conditions for this scenario were already
  collected in `step85_setups.csv` (rows 29-31: volume ≥120-150% of the
  20-bar average on the breakout bar, stop just inside the broken range
  or an ATR-multiple beyond it, target 1R-2R or the measured move). This
  round adds only the measured-move TARGET mechanic on top of what R85
  already found for breakout ENTRIES — the two rounds' breakout findings
  are consistent, not contradictory.

---

## 4. SCENARIO: News/event and scalp (fast trades)

- **Scalp fixed stop + fixed target.** Exact rule: stop 1-2 pips beyond
  the entry candle's high/low (5-10 pips on majors generally), fixed
  target 8-10 pips. Explicitly a trailing/structural exit is NOT used
  here — reasoning given is that at this timeframe noise dominates any
  structure signal, and the edge comes from repeating a small, consistent
  size advantage many times, not from letting any single trade run.
  **[Tradezella](https://www.tradezella.com/blog/scalping-strategies)**
- **Event/news flatten rule.** Flatten before a scheduled binary event
  (earnings, major macro print) the position's thesis didn't already
  price in — explicit reasoning: a technical stop is meaningless against
  a gap, so the only real protection is not holding through the event at
  all. Directly relevant to this repo's NEWSDESK entry, which trades
  headline events by construction.
- **Fast momentum time stop.** If the trade hasn't shown its expected
  momentum within a short window, exit regardless of P&L; if it HAS,
  commit to a longer hold with a trailing stop instead of a static
  target — "no middle ground" is the explicit framing in one source.
  Cited windows are inconsistent across sources (5 min, 25 min, 1 hour)
  — **no numeric consensus**, only the shape of the rule (a binary
  early gate, not a single universal number) is well-supported.

step59's E2 (NEWSDESK) result is the sharpest empirical echo of this
scenario: **every exit module tested (X0-X5) failed validation** for the
news entry — the literature's own scalp/event doctrine (fixed tight
levels, explicit flatten-before-binary-event rules, fast conditional
time stops) describes several mechanisms this repo has NOT yet tried on
that entry (see §7).

---

## 5. SCENARIO: Swing / multi-day trend-continuation pullback

R85 already collected the entry-side context checklist for this family
(three-timeframe stack: daily bias, HTF setup gate, LTF trigger — see
`step85_winning_trades.md` §2, "Trend-continuation pullbacks"). On the
exit side specifically, TheMarketStructureTrader's own worked numeric
example uses a breakeven-move-at-Fibonacci-extension pattern (move stop
to breakeven at the 1st Fib extension, take profit at the 2nd) — a
concrete instance of the breakeven debate in §6 below, applied to this
scenario. No further exit-specific rule beyond the trend-ride mechanisms
in §1 was found distinctly attached to this scenario; the literature
treats swing trend-continuation as "the trend-ride exit toolkit, entered
via a pullback" rather than a separate exit discipline.

---

## 6. Cross-cutting: the partial-exit question

**How common is scaling out?** Common enough to have a standard name
("scale out") and a standard shape (close 50% at 1R, move stop on the
remainder to breakeven, trail or fixed-target the rest) — but the sources
disagree sharply on whether it HELPS.

- **The case for.** Locks in a partial win so a full round-trip back to
  breakeven doesn't feel like the whole trade was wasted; reduces the
  emotional weight of watching an open position; makes the remaining
  runner easier to hold through a pullback because "something is already
  banked." One source frames exit method as only 30-40% of exit
  performance vs. 60-70% for execution discipline — i.e., HAVING a
  pre-planned partial rule matters more than which specific rule, in
  this source's own (self-reported, unverified) framing. **[Metriclan](https://www.metriclan.com/blog/partial-profit-taking), [The Trapped Trader](https://thetrappedtrader.com/learn/foundations/risk-management/9)**

- **The case against.** Dave Mabe's own backtest (single strategy, stated
  plainly as not a general law) found taking 50% off at a predetermined
  level gave up **roughly half the total profit** vs. holding full size
  to the same exit rule. His argument: partials optimize for WIN RATE,
  not total dollars — a $0.01 partial-protected win and a $1,000 full-
  size win count identically toward "I didn't lose on that one," but the
  dollar difference is what actually matters. He states partials work
  WORST specifically for short-duration strategies where the full target
  could plausibly be hit at full size anyway, and work better for long
  holds, large size that would move the market, drawdown periods, or
  external constraints like monthly settlement at a prop firm. **[Dave Mabe](https://davemabe.com/should-you-ever-take-partials)**

- **This repo's own data point (not literature, stated for completeness
  since it bears directly on this question): step59's X4 hybrid (X1
  target, 50% off at 1R, remainder to breakeven) is the WORST or
  near-worst of all six exits on E1, E2, and E4**, and underperforms its
  own family's incumbent on E3's val windows too, even though it does
  produce the smallest drawdown on gold — the mechanism itself works as
  designed, but the asymmetry between a 100%-sized full stop-out and a
  50%-sized partial winner loses more than the breakeven protection
  saves, on any entry with a high stop-out rate (`step59_results.md` §4).
  **This backtest finding and Dave Mabe's literature finding point the
  same direction independently** — a rare case in this file where the
  backtest and the literature agree without either citing the other.

**We have never tested a partial-exit variant that ISN'T X4's specific
shape** (50% @ 1R + breakeven + structure target on the remainder) — no
thirds, no partial-without-breakeven-move, no partial sized differently
by scenario. See §7.

---

## 7. Cross-cutting: break-even moves — both sides, no winner declared

- **Pro.** Moving the stop to entry once price has moved favorably
  (commonly triggered at 1R) removes downside risk entirely on that
  trade and is argued to reduce impulsive, fear-driven decisions by
  eliminating the "it could go back to a loss" tension. **[Trading Heroes](https://www.tradingheroes.com/move-stoploss-breakeven/)**
- **Con.** *"There is never a good time to move your stop loss to
  breakeven... it is never logical nor strategic to do so"* — the
  argument is that only the target and the original invalidation level
  matter once a trade is on; moving to breakeven converts trades that
  would have gone on to be real winners into scratches whenever price
  makes an ordinary pullback through entry before continuing, which
  measurably lowers a system's expectancy if it wasn't part of the
  original tested rule. **[Daily Price Action](https://dailypriceaction.com/blog/the-best-time-move-stop-loss-breakeven/), [BabyPips forum thread](https://forums.babypips.com/t/how-long-before-you-move-your-stop-loss-to-be-or-better-on-a-profitable-trade/1206808)**
- **Reconciliation, not resolution:** the strongest version of either
  camp's argument is conditional — *"Breakeven is a powerful risk
  management tool, but only when used as part of a system"* — i.e., the
  disagreement is really about whether the breakeven trigger was itself
  BACKTESTED into the rule (survives) vs. applied by feel mid-trade
  (destroys edge). No source in this haul offers a numeric win-rate/
  expectancy comparison of the same system with and without a BE rule —
  this is exactly the kind of unfalsifiable-sounding advice this round
  was told to be skeptical of, EXCEPT that it IS codeable (BE-trigger at
  N × R, tested against no-BE, on a fixed entry) and none of step59's six
  modules isolated the BE-move as its OWN independent variable — X4
  always couples it with a 50% partial. **A pure "move to BE at 1R, no
  partial" exit has never been tested in this repo.**

---

## 8. Cross-cutting: stop placement relative to the swing — buffer size

There IS a consensus on the SHAPE of the rule (never place the stop
exactly at the obvious swing point) but **not** on the exact buffer size
— sources disagree by roughly an order of magnitude depending on how
they frame it:

| source's stated buffer | basis | reasoning given |
|---|---|---|
| 0.3-0.5x ATR | ATR-scaled | noise buffer against ordinary wicks |
| 5-15% of recent ATR | ATR-scaled | "structural stop" framing, smaller fraction |
| 1.5-2x ATR (range-fade specifically) | ATR-scaled | wider because a well-tested range edge draws MORE wick noise, not less |
| $0.10-$0.50 | fixed dollar (equities) | simple, non-volatility-adjusted alternative |
| "beyond the sweep wick extreme, never inside it" | structural, no fixed size | R85's liquidity-sweep finding — placing the stop inside the wick recreates the exact cluster that just got hunted |

**The reasoning is uniform even where the number isn't:** every source
that gave ANY numeric buffer justified it the same way — protecting
against the single most commonly cited failure pattern in this whole
file, a stop triggered by a brief wick through a well-known level that
immediately reverses. **The size of the buffer should plausibly scale
with how "obvious"/heavily-watched the level is** (tighter for an
arbitrary swing point, wider for a widely-drawn range edge or equal-
highs liquidity pool) — this is an inference from comparing sources
side by side, not a claim any single source made explicitly, and is
flagged as such.

---

## 9. Cross-cutting: time stops

**Who uses them, for what, and why:**

- **Range fades** — exit if no progress toward the midline within 5-8
  candles. Reasoning: a stalled fade is more likely failing than slow.
- **Fast momentum/news trades** — exit if the expected momentum hasn't
  shown within a short window (sources disagree on the exact window:
  5 min / 25 min / 1 hour cited by different authors); if it HAS shown,
  switch to a trailing exit instead of a static target. Reasoning:
  momentum decays fast after a spike, so a stall after the initial
  window is evidence the move is over, not "about to start."
- **General discretionary framing (ATAS):** a trade with no follow-
  through demonstrates a balance of buyer/seller forces the original
  thesis didn't anticipate; continuing to hold converts the position from
  "trading a thesis" into "hoping," plus a stated opportunity-cost
  argument (capital tied up in a dead trade could be working elsewhere).
- **Event-driven hard flatten** — flatten before a scheduled binary event
  regardless of current unrealized P&L, because a technical stop cannot
  protect against a gap.

**Distinct from what this repo already has.** step59's X0/E1/E2/E4
already include hard TIME CAPS (48h, 24h, 240 bars) — but those are
unconditional maximum-hold limits, not the literature's CONDITIONAL "exit
early if no progress" rule. **A genuine no-progress time stop (exit
before the cap if the trade hasn't moved a meaningful fraction of its
target within a fraction of its own time budget) has not been tested
anywhere in this repo.**

---

## 10. What kills traders' exits — the documented failure modes

Mirroring R85's "#1 failure mode when skipped" framing, applied to exits:

1. **Moving the stop AWAY from the level that proved the idea wrong.**
   This is the single most concrete, numerically-illustrated failure
   mode in this haul. Cited example: a trader who widens a stop from
   $98→$95→$90 and finally exits at $85 loses roughly **$1,500**, vs.
   an original planned loss of roughly **$200** at the first honored
   stop — a 7.5x amplification from a single act of not honoring the
   plan. This is the exact inverse of the owner's own stated principle
   (a stop is a level the idea is proven wrong, not a number to
   negotiate with mid-trade). **[wemastertrade.com](https://wemastertrade.com/stop-loss-mistakes-risk-management/), [pfhmarkets](https://blog.pfhmarkets.com/trading-risk-management/trading-risk-mistakes/)**

2. **The disposition effect — cutting winners short, holding losers
   long.** This is the one finding in this file with genuine, named
   academic backing rather than a trading-blog synthesis: Shefrin &
   Statman (1985), "The Disposition to Sell Winners Too Early and Ride
   Losers Too Long," and Terrance Odean's empirical follow-up (UC
   Berkeley, 10,000 discount-brokerage accounts, 1987-1993): investors
   were **1.5x more likely** to sell a winning position than a losing
   one, even in cases where the losing position was objectively the
   better sale. A separate Finnish dataset attributes **3.2-5.7% of
   average investor returns** to this specific bias. Root cause cited:
   prospect theory (Kahneman & Tversky) — losses are felt roughly twice
   as painfully as equivalent gains, so the instinct is to lock in the
   good feeling early and defer the bad one. **[Odean, UC Berkeley (PDF)](https://faculty.haas.berkeley.edu/odean/papers%20current%20versions/areinvestorsreluctant.pdf), [Wikipedia: Disposition effect](https://en.wikipedia.org/wiki/Disposition_effect)**

3. **Revenge trading after a stop-out.** Re-entering immediately after a
   loss, without the original plan, seeking to "get it back" — usually
   with a worse setup or larger size than the original trade justified.
   Cited (single secondary-source survey, **not independently verified**
   in this pass): 78% of retail traders who fall into this pattern lose
   more than their initial deposit within six months. **[Axi](https://www.axi.com/int/blog/education/revenge-trading), [Bullish Bears](https://bullishbears.com/revenge-trading/)**

4. **Whipsaw from a trail set too tight for the regime.** Named across
   multiple trend/trailing sources as the mirror-image mistake to #1:
   where #1 is "too loose, too late," this is "too tight, too early" —
   a trailing stop or Parabolic SAR set for a calm regime gets triggered
   repeatedly by ordinary volatility once the regime shifts, cutting a
   trend ride into many small losses instead of one large win.

5. **Fading a range that's actually a higher-timeframe trend.** The
   direct exit-side analog of R85's "regular RSI divergence in an
   accelerating trend" trap: FXNX's own word for it, again, is
   "steamrolled." Documented independently on both the entry side (R85)
   and the exit side (this round), by unrelated sources, using the same
   descriptive language — the single strongest piece of *convergent*
   evidence in this file that this specific failure mode is real and not
   an artifact of one author's phrasing.

6. **Applying one fixed/naive stop rule without checking it against the
   asset's own behavior.** The academic-adjacent literature on stop-loss
   efficacy is genuinely mixed (see the caveat below) but converges on
   one point: **tight, naive stops only help when the asset's returns
   are meaningfully serially correlated (trending)**; on a mean-reverting
   or low-autocorrelation asset the same stop rule can destroy edge and
   run up transaction costs. At least one cited study (Larry Connors)
   found the empirically optimal stop-loss level was "none" for the
   system tested. This is consistent with — not contradicting — the
   scenario-specific framing this whole file is built around: the
   question is never "is a stop-loss good," it's "is THIS stop rule
   right for THIS regime."

**Caveat on #3 and the "30+ peer-reviewed studies" claim in one search
synthesis:** these came from secondary/aggregator sources (trading-
education sites summarizing claimed research) rather than a primary
academic source fetched and read directly in this pass. They are
reported here as claims, not verified findings — flagged exactly the way
R85 flagged its own unfalsifiable-advice risk.

---

## 11. Which of these methods does our repo not currently implement or test at all?

This is the list that feeds the backtesting matrix, cross-checked against
`step59_exit_science.py`'s actual six modules (X0-X5) and the rest of the
repo (`backtest.py`'s `stop_pct`/`target_pct`, `strategy.py`'s
hysteresis-based regime exits):

1. **Range-fade-specific stop/target** — ATR-buffer-beyond-edge stop +
   POC/midline target, entered on an actual range-fade signal (not a
   trend-context entry retrofitted with a structure target). step59's
   X1/X2 target modules were tested only on trend/breakout entries.
2. **A pure breakeven-move rule, isolated from partial exits.** step59's
   only breakeven mechanism (X4) is permanently coupled to a 50% partial;
   "move stop to BE at N×R, no partial, let 100% run" has never been
   tested as its own variable.
3. **Partial-exit variants beyond X4's exact shape** — no thirds, no
   partial-without-breakeven, no partial sized by scenario (e.g., bigger
   first slice on a fast/scalp entry, smaller on a slow trend ride).
4. **A moving-average trailing exit** (e.g., close below 20-EMA/50-EMA)
   as its own exit module, distinct from step59's X3 (which trails to
   swing-low structure) and X5 (which trails by ATR chandelier).
5. **Parabolic SAR trailing stop** — not implemented or tested anywhere
   in this repo.
6. **A genuine conditional time stop** ("exit if no meaningful progress
   within a fraction of the position's own time budget"), as distinct
   from the hard time CAPS (48h/24h/240-bar) already present in every
   E1-E4 exit tested. No "stalled trade" logic exists.
7. **Regime-conditional ATR-multiplier switching** (calm-market
   multiplier vs. volatile-market multiplier on the SAME trailing rule,
   switched by a measured volatility state) — step59's X5 used one fixed
   multiplier per split, selected on train and frozen, not a live
   regime-adaptive switch.
8. **An explicit event/news flatten rule** — closing or refusing new
   entries ahead of a scheduled binary event, distinct from NEWSDESK's
   current after-the-fact reactive entry logic.
9. **Scalp-scenario fixed tight stop/tight target as its own tested
   family** — this repo's fast entries (STRIKES, NEWSDESK) use the
   incumbent's percentage stop/target, but the literature's SPECIFIC
   scalp doctrine (candle-relative stop, single-digit-pip-equivalent
   target, explicitly no trailing) has not been isolated and tested on
   its own terms.
10. **Measured-move (flagpole-projection) targets** on this repo's own
    breakout survivors (Bollinger 20/2.5, BB-in-KC squeeze release) —
    R85 already flagged the missing volume gate on these; this round
    adds the missing target-projection mechanic as a second, independent
    gap on the same family.

---

## Sources (18 distinct)

StockCharts ChartSchool (Chandelier Exit / LeBeau via Elder), Pro Trader
Dashboard (2 articles), Aurra Markets, mywinnerdays.com, TradingSim (20MA
pullback), TradingWithRayner, TradeAlgo (Parabolic SAR), Market Wizards
(via thetrendfollower.com and Dr Wealth's summary), FXNX (range trading
math-of-the-middle), Blofin Academy, FinWiz, Alchemy Markets, Tradezella,
Metriclan, The Trapped Trader, Dave Mabe (davemabe.com), Trading Heroes,
Daily Price Action, BabyPips forum, traderssecondbrain.com, ATAS,
wemastertrade.com, pfhmarkets.com, Axi, Bullish Bears, Terrance Odean /
UC Berkeley (primary academic PDF), Wikipedia (Disposition effect,
tertiary but accurately summarizes Shefrin & Statman 1985), LuxAlgo (ATR
stop-loss strategies), quantifiedstrategies.com / secondary aggregation
of the stop-loss-efficacy academic literature (flagged as unverified
primary-source claims, §10).
