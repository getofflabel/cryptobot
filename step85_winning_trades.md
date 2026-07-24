# Step 85 — Real Winning Trades and Why They Worked

**Round 85.** The owner's instruction, verbatim: *"Go online and capture some
winning trades and their strategies on why they were a good trade. RSI
divergence is world famous for a reason."* His standing doctrine governs
this round: profitable traders are profitable for a reason; when our
formalisation fails, OUR VERSION is wrong, not them. This round does not
judge anyone. It collects documented setups with their stated reasoning so
we can see what real traders required, and hold that up against how this
project has been testing.

**Research only. No commits, no live orders.** Writes exactly two files:
`step85_winning_trades.md` (this file) and `step85_setups.csv`. Does not
touch any step79-84 file (owned by concurrent agents).

---

## 1. What was collected

**36 documented setups** in `step85_setups.csv`, from 24 distinct sources —
TradingView published trade ideas (with real entry/stop/target price
levels), an exchange education article (Kraken), a payments/crypto
education site with a genuinely strong sourced case-study article
(Plisio), broker and prop-adjacent educational breakdowns (LuxAlgo,
Alchemy Markets, Pipcy, TradingSetupsReview, ChartingLens, FXNX,
LiteFinance, DailyForex, Swingfolio, MindMathMoney, TradingSim,
Quant-Signals, StockGro, TheMarketStructureTrader, Strike.money), and one
quantitative backtest write-up (Quant-Signals' EMA 9/21 study, the closest
thing in this haul to an actual out-of-sample transfer check — and it
fails a transfer check exactly the way this project's own work does, see
§4).

Coverage across the eight requested families (row counts in the CSV):
RSI divergence regular (7), RSI divergence hidden (5), MACD (4), moving
averages (6), support/resistance & range (5), breakout (3), liquidity
sweep / stop-hunt (2), session-open (2), trend-continuation pullback (2).
Two rows are pure cited statistics rather than single trades (the
stochastic-divergence 62%/48% trending-vs-ranging stat and the ORB
40-60% success-rate stat) — kept because the *conditions* they attach to
(regime, session) are exactly what this round is auditing for.

**Honesty on the flag column.** Of the 36 rows, roughly a third are
`documented real market event` or `documented published trade idea` with
real prices, dates, and (for the four BTC/ETH cases) real historical
outcomes. The rest are explicitly flagged `teaching/rule` or `illustrative
teaching example` — generic strategy write-ups, not closed trades with
audited P&L. **Not one source in this haul published a verified,
independently-audited track record of many closed trades for a single
mechanical rule** — the closest is Quant-Signals' EMA backtest, which is a
real quantitative study but still self-reported. This matches this
project's own prior finding (R58, R76, R82) that most "trading strategy"
content on the internet is unfalsifiable by design. That does not
invalidate the *reasoning* collected below — the context checklist a
setup requires is a separate, checkable claim from "and it worked" — but
it means the checklist, not the win-rate claims, is this round's real
output.

---

## 2. Context patterns — the per-family checklist

Tabulating what conditions recur across the collected setups, by family:

### RSI divergence (regular / reversal)
- [ ] **Trend already extended** — divergence is required to appear AT an
  extreme (a new high/low), not mid-trend. Every source that stated this
  explicitly used the word "extremes" or "exhaustion."
- [ ] **Timeframe floor** — 4H/Daily/Weekly/Monthly preferred; sources
  explicitly warn 1-minute/5-minute divergence is noise.
- [ ] **Structural level confluence** — a major prior high/low, S/R zone,
  or round number. Pipcy's own stated ladder: ~45-55% divergence alone ->
  ~65-75% with structural confluence -> ~70-80% with volume added.
- [ ] **Confirmation candle / structure break required before entry** —
  every source that gave a concrete rule said mark-but-don't-enter on the
  divergence itself; enter on the candle/structure confirmation after it.
- [ ] **NOT valid in a strong, still-accelerating trend** — stated
  explicitly as a trap condition, and directly evidenced by the BTC
  Mar 2024 $30k->$73,581 case in the CSV (divergence fired repeatedly,
  shorts "steamrolled" — the trend simply kept extending).

### RSI divergence (hidden / continuation)
- [ ] **Established prior trend with intact structure** — the defining
  requirement (tradingsetupsreview's own phrase: "the trend holds up
  despite the momentum going against it") — price must still be printing
  higher lows (bullish) or lower highs (bearish) even as the oscillator
  disagrees. This is a structural precondition, not optional.
- [ ] **Pullback, not reversal** — sources distinguish a shallow
  retracement from an actual trend change; one guide's own worked failure
  case (Example #4) shows the setup breaking specifically when the
  "pullback" turned out to be a real reversal.
- [ ] **Timeframe floor** — hourly or higher stated as the reliability
  threshold, same as regular divergence.
- [ ] **A trigger on top of the divergence** — trendline break, pennant
  break, or continuation candle; never traded as a bare oscillator
  reading.

### MACD
- [ ] **Confirmation from price action, not the crossover alone** — every
  MACD source explicitly downgraded the raw crossover to a "momentum
  shift is happening" signal, and required a resistance break, pullback
  into a level, or structural confirmation before treating it as a trade.
- [ ] **Zero-line cross used as a trend filter, not an entry** — sources
  treat this as validation layered under another signal.
- [ ] **Multi-timeframe agreement** — HTF sets direction, LTF times entry.
- [ ] **Divergence variant needs the same structural-level confluence as
  RSI divergence** — support/resistance plus a candlestick confirmation.

### Moving-average systems
- [ ] **Regime dependency stated outright** — golden cross explicitly
  flagged as producing frequent false signals in range-bound markets; the
  EMA 9/21 backtest's own authors attribute their positive numbers to the
  2020-2025 window having strong directional trends, not to the rule
  being universally good.
- [ ] **Multi-MA stack for pullback entries** — price above 200-EMA, a
  RISING 50-EMA, pullback into the 21/34-EMA zone specifically (not a deep
  dip — RSI ~40-50, not oversold), confirmation candle required.
- [ ] **Cross-asset transfer is explicitly NOT assumed** — the one
  quantitative source in this haul (Quant-Signals) published its own
  transfer failure: the same 9/21 rule went from +0.330R (BTC daily) and
  +0.271R (EURUSD daily) to -0.071R on GBP/USD at 1H. Same rule, different
  asset/timeframe, sign flip — a real published instance of exactly the
  BTC-to-ETH transfer failure this project keeps finding.

### Support/resistance & range trades
- [ ] **Level must be pre-tested** — every source with a stated rule
  required 2+ prior touches before treating a level as valid support/
  resistance; untested levels explicitly downgraded.
- [ ] **Range-bound regime required** — sources warn range/S&R trading
  specifically fails in trending markets (the mirror image of the MA
  golden-cross warning above).
- [ ] **Rejection confirmation at the level** — wick, engulfing candle, or
  a structure break at the level, not a bare touch.

### Breakout trades
- [ ] **Volume confirmation is close to universal** — every breakout
  source required volume materially above the trailing average (120% to
  150%+ cited) on the breakout bar itself; low-volume breaks explicitly
  flagged as the common failure mode.
- [ ] **Prior contraction/consolidation** — Bollinger squeeze and the
  symmetrical-triangle case both require a visible LOW-volatility base
  before the expansion is treated as meaningful, not a breakout from an
  already-volatile range.
- [ ] **A real, closable statistic exists here too, and it's not
  flattering**: the cited Bollinger squeeze number is 30-40% of squeezes
  FAIL to reach even a 1:2 target — i.e. even with the textbook context
  present, this is a moderate not a high-probability setup.

### Liquidity sweep / stop-hunt reversals
- [ ] **The sweep itself is explicitly NOT the entry** — every source
  with a concrete rule was emphatic: entry is the Market Structure Shift
  (MSS) AFTER the sweep — a break of the most recent opposing swing WITH
  displacement (fast, full-bodied candles / a fair value gap) — not the
  sweep wick itself.
- [ ] **The swept level must be a visible, "obvious" liquidity pool** —
  equal highs/lows, a session extreme, a multi-week swing — the entire
  logic depends on the level being one the whole market can see and place
  stops at.
- [ ] **Direction must agree with the higher-timeframe bias** — sources
  explicitly warn against fading a sweep against a strong HTF trend.
- [ ] **Stop goes beyond the sweep wick extreme, never inside it** —
  stated explicitly as a common mistake to avoid (placing the stop inside
  the wick recreates the exact stop cluster that just got hunted).

### Session-open plays
- [ ] **A defined pre-session range is the setup, the session open is the
  trigger** — both London Breakout and ORB require the range (Asian
  session, or the first 15-30 minutes) to be marked FIRST; the breakout of
  that specific range at the session transition is what's traded, not a
  breakout of an arbitrary level at an arbitrary time.
- [ ] **Confirmation bar quality matters, not just a level cross** — ORB's
  stated rule requires the breakout candle's range to exceed the prior
  5-candle average AND most of the candle body to sit outside the range —
  a materially stricter trigger than "price crossed the line."
- [ ] **Stated success rate is explicitly modest, not "high win rate"** —
  ORB's own cited number is 40-60%, explicitly conditioned on volatility
  and trend regime.

### Trend-continuation pullbacks
- [ ] **Full multi-timeframe stack required, not a single-TF signal** —
  the most detailed source (TheMarketStructureTrader) requires THREE
  aligned layers: daily EMA sets bias, 4H RSI extension gates the setup,
  15-min trigger fires the entry — directly parallel to this project's own
  step58 Family-3 MTF-stacking work, where only the full stack (not
  setup-only) survived cleanly.
- [ ] **A prior established trend leg, defined numerically** — pullback
  sources anchor to a real prior move (e.g. "rose from 50 to 70, pulls
  back to 65") rather than an undefined "trend."

---

## 3. What we got wrong — per family, specifically

Reading this checklist against `step76_results.md` and the step80/82
context work already done in this repo:

**RSI divergence — the biggest gap, and the owner named it directly.**
R76 tested RSI only as OB/OS threshold crosses and a 50-line cross — it
never tested divergence AT ALL as a standalone family; R58 did (see §4
below) and is closer to what the literature describes, but even R58's own
definition never required: (a) the divergence sitting at a *structural*
level (major prior high/low, not just any confirmed swing), (b) a
confirmation candle/structure-break gate AFTER the divergence forms before
entry is allowed (R58's entries fire on the divergence itself), or (c) an
explicit "not in an accelerating trend" filter for the regular flavor —
exactly the condition the BTC Mar-2024 trap case in the CSV shows failing
in the real world. R58's hidden-divergence definition already requires
trend alignment (gated to the 4h champion regime) — which is very close to
the literature's own "trend intact" checklist item, and likely explains
why hidden survived while regular didn't (see §4).

**MACD.** R76 tested MACD-histogram 0-cross and divergence as lone
triggers; the literature is unanimous that a bare MACD crossover is
explicitly a momentum-shift SIGNAL that needs a structural/price-action
CONFIRMATION on top before being tradeable, and multi-timeframe agreement
before an entry timeframe's crossover is trusted. Neither confirmation nor
MTF-gating of MACD specifically was tested in R76's MACD rows.

**Moving averages.** R76's EMA-cross survivors (12/26 and 10/30) are bare
crossovers with no regime filter and huge drawdowns (-38.9%, -42.1%) —
exactly the failure mode the literature warns about (whipsaw in
range-bound conditions). The literature's EMA-pullback rule (price above
200-EMA AND a rising 50-EMA AND a shallow, RSI 40-50 pullback into the
21/34-EMA zone, confirmed by a candle) is a materially more specific,
context-gated version of "EMA" than anything tested in R76, and closer to
step80's committee/regime designs than to R76's lone crossover.

**Support/resistance & range.** R76's Camarilla and Classic pivot
(reversion) rows are FAIL across the board — but the literature's own
condition for range trading is a range-bound REGIME in the first place,
tested with a pre-established level (2+ touches) and a rejection
confirmation. R76 tested pivot reversion everywhere, unconditionally, with
no regime gate — precisely the "used it in the wrong context" failure mode
step80 was built to address for other indicator families, but pivots were
not revisited under step80's regime-conditional design.

**Breakout.** R76's Bollinger breakout (20/2.5) and BB-in-KC squeeze
release both survived, and the literature agrees this family wants a
volatility-contraction-to-expansion transition. What's still missing
against the literature checklist: a VOLUME gate on the breakout bar. None
of R76's breakout-family survivors condition on volume at all — the
literature treats volume confirmation as close to mandatory, and cites
low-volume breakouts as the dominant failure mode.

**Liquidity sweep / stop-hunt.** This project has extensive CHoCH/BOS/
confluence work (step56, step66, step80) but no round has explicitly
tested the "sweep of a visible equal-high/low pool, THEN wait for MSS with
displacement (not the sweep itself)" sequence as its own standalone
family, with the stop specifically OUTSIDE the sweep wick (not at a fixed
ATR/pct distance) and the direction gated to HTF bias. This is a genuine
gap — a distinct, well-specified setup this project hasn't coded as its
own testable unit.

**Session-open.** MARKET_PLAYBOOKS.md and step43's session-breakout/VWAP-
fade work exist in this repo, but the literature's specific ORB
confirmation-candle rule (candle range > prior-5-average AND most of body
outside the range) is stricter than a level-cross and has not been tested
here as its own gate.

**Trend-continuation pullback.** step58's Family-3 MTF stacking already
tests something close to the literature's 3-layer stack (bias/setup/
trigger) and found the full stack was the one clean survivor — this is
the one family where this project's prior work and the literature
checklist are already well aligned. The gap is narrower here than
anywhere else: mainly that step58 used RSI(3)<10/15 as the setup layer,
where the literature's version uses RSI(14) EXTENSION (>70/80) on the
counter-trend swing as the gate, a related but distinct parameterization
worth testing directly.

---

## 4. RSI divergence deep-dive

This is where the owner asked for the most depth, so the collected
evidence is laid out candidate-by-candidate against what the literature
actually says (not what's assumed):

**Candidate 1 — "must form at a significant level."** CONFIRMED across
every source that gave a concrete rule (LuxAlgo, Pipcy, Finveroo,
Alchemy). Pipcy is the most quantified: ~45-55% divergence alone, jumping
to ~65-75% with structural confluence. This project's own R58 divergence
definition does **not** gate on level significance at all — it fires on
any confirmed swing, anywhere on the chart. This is the single most
concrete, literature-backed gap.

**Candidate 2 — "must be confirmed by a structure break."** CONFIRMED,
repeated across nearly every source with operational detail
(Pipcy: "don't enter on the first instance... wait for the confirmation
candle" called the "#1 failure mode" when skipped; LuxAlgo's S/R strategy
requires a rejection wick/engulfing/structure break; ChartingLens'
liquidity-sweep MSS logic is structurally the same idea applied to
divergence-adjacent reversal trading). R58 enters on the divergence swing
itself with no post-divergence confirmation gate — this is the second
concrete gap.

**Candidate 3 — "must be on the higher-timeframe trend side."**
CONFIRMED, and this is the one condition R58's *hidden*-divergence
definition already implements (hidden divergence gated to the 4h champion
regime) — it is NOT implemented for R58's *regular*-divergence definition,
which is unconditional. That asymmetry in what R58 tested lines up with
what R58 found (below).

**Candidate 4 — "hidden vs regular usage differs."** CONFIRMED
unambiguously. Every source that distinguished them agrees: regular
divergence signals reversal and needs to appear at trend extremes/
exhaustion; hidden divergence signals continuation and needs to appear
mid-trend, during a pullback, with the prior trend's structure still
intact. They are not two flavors of the same trade — they require
opposite trend contexts.

**Candidate 5 — "divergence in strong trends is a known trap."**
CONFIRMED, and directly evidenced with a real, dated, sourced case: the
BTC Mar 2024 rally ($30k -> $73,581 in ~3 months) repeatedly threw regular
bearish divergence signals that failed as the trend kept extending
("shorts steamrolled," per Plisio's own account) — a real, citable
instance of exactly the failure mode the literature warns about.

**Does the literature explain R58's regular-vs-hidden asymmetry?**
R58 found: regular divergence 1/96 configs survived (essentially dead on
BTC), while hidden divergence sealed-passed and is live (step82/RESEARCH_LOG
puts 4h hidden RSI divergence among the project's validated edges). The
literature explains this almost exactly:

- Regular divergence's own literature-stated precondition (level
  significance + confirmation gate + trend-extreme timing) was **not**
  implemented in R58's test — it fired at every confirmed swing,
  unconditionally, which is close to the worst-case way to test the
  regular flavor per every source above. A test built to fail by omission
  producing near-zero survivors is not surprising, and is not evidence
  against regular divergence generally — it's evidence against testing it
  without its required context, which the literature is explicit about.
- Hidden divergence's own literature-stated precondition (prior trend
  intact / mid-trend pullback) **was** implemented in R58 (gated to the 4h
  champion regime) — the one condition the literature treats as
  non-negotiable for the hidden flavor was already present in the test
  that succeeded.

In other words: the literature does not just fail to contradict the R58
asymmetry, it predicts it. R58 tested hidden divergence closer to the
textbook recipe than it tested regular divergence, and the flavor tested
closer to the textbook recipe is the one that survived. This is the
single clearest "our version was wrong, not the traders" finding in this
round: regular divergence was never given the structural-level +
confirmation-candle + trend-extreme gates the literature treats as
mandatory, so its near-total failure in R58 measures an under-specified
test, not a dead pattern.

---

## 5. Testable proposals — concrete, ready to code

Eight configurations drawn directly from the checklists above, none of
which this project has tested in this exact form:

1. **Regular divergence, level-gated.** Re-run R58's exact regular RSI(14)
   divergence definition (4h and 1h, both k=5/k=8 swing windows) but ADD a
   gate: the divergence's price extreme must be within N% (sweep N in
   {0.5%, 1%, 2%}) of a prior confirmed swing high/low from at least M
   bars back (M in {50, 100, 200}) — i.e. "at a level," operationalizing
   Candidate 1 directly, on the family this project already found dead
   without it.

2. **Regular divergence, confirmation-gated.** Same base definition, but
   entry is delayed from the divergence bar to the first subsequent bar
   that closes back through the nearer swing point (a literal "structure
   break" gate) — operationalizing Candidate 2. Test independently from
   #1, then combined, to see which gate (if either) does the real work.

3. **Regular divergence, trend-extreme-only.** Restrict entries to
   divergences where the 4h champion regime (already computed in
   step56/step66/step80) is EITHER flat/undefined OR has been in the SAME
   direction as the divergence's implied reversal for fewer than K bars
   (K in {20, 50}) — i.e. only take reversal divergence near a trend's
   apparent age/exhaustion, not mid-trend. Directly tests the "not valid
   in an accelerating trend" claim against the Mar-2024 trap pattern.

4. **MACD crossover with structural confirmation.** Re-test R76's MACD-
   hist 0-cross signal, but require the crossover bar to also be a
   Donchian(20) breakout bar (reuse strategy.py's own base) OR a break of
   the prior N-bar swing high/low — operationalizing "crossover needs
   price-action confirmation," not tested as its own MACD-specific gate
   in R76 or R80.

5. **EMA pullback (regime + shallow-dip + candle), the literature's exact
   recipe.** Long only when: close > EMA200 AND EMA50 is rising (positive
   slope over the last 10 bars) AND price has pulled back so RSI(14) is in
   [40,50] AND price is within X% of EMA21/EMA34 AND the entry bar is a
   bullish engulfing (close > prior bar's high, open < prior bar's close).
   Stop below the pullback low. This is a materially more specific EMA
   rule than either of R76's bare EMA-cross survivors and follows the
   literature's stack exactly.

6. **Volume-gated breakout.** Re-test R76's two breakout-family survivors
   (Bollinger breakout 20/2.5 and BB-in-KC squeeze release) with an added
   gate: breakout bar's volume >= 1.2x (and separately >= 1.5x) its own
   trailing 20-bar average volume — operationalizing the near-universal
   "volume confirms breakouts" claim on the two configs this project
   already knows survive on price alone, to see if volume improves them,
   is a no-op (already usually true at real breakouts), or hurts (cuts
   sample the way step76's FILTER-VALUE section found for other gates).

7. **Liquidity sweep -> MSS -> displacement, as its own signal family.**
   New signal, not a filter on the existing Donchian base: (a) identify
   equal highs/lows (within X% of each other) or an N-bar swing extreme as
   the liquidity pool; (b) flag a sweep when price trades beyond the pool
   by a small amount and closes back inside within Y bars; (c) entry
   triggers only on the subsequent break of the nearest OPPOSING swing
   point with a displacement bar (range > 1.5x the recent ATR); (d) stop
   beyond the sweep wick extreme + buffer, target the opposing liquidity
   pool. This is a genuinely new, well-specified family per §3's gap
   finding, distinct from step56/step66's CHoCH/BOS work.

8. **ORB-style session-open breakout with the stricter confirmation bar.**
   Re-test the existing session-breakout logic (step43/MARKET_PLAYBOOKS)
   but replace a bare level-cross entry with the literature's two-part
   confirmation: breakout bar's range > average of the prior 5 bars' range
   AND the bar's body occupies >= 70% of its own range with the close
   beyond the opening-range boundary — testing whether the stricter bar
   quality gate (not just session timing) is what the literature's cited
   40-60% success band actually depends on.

---

## Sources (24 distinct, full list in step85_setups.csv)

TradingView (multiple published trade ideas: BTCUSDT hidden-divergence
live trade, BTCUSD hidden-divergence pennant, GBPUSD "Mastering MACD"
guide, Gold/S&P500/USOIL/IBM range ideas), Plisio.net (RSI divergence
crypto case studies), Kraken Learn, StockGro, Pipcy, LuxAlgo (5 articles),
Alchemy Markets, TradingSetupsReview, Finveroo, ChartingLens, FXNX (2
articles), LiteFinance, DailyForex, Swingfolio, MindMathMoney, TradingSim
(2 articles), Quant-Signals, TheMarketStructureTrader, Strike.money.
