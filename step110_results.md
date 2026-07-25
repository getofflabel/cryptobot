# Round 110 — Live Oil Book Stand-Down Audit

**Verdict: STAND IT DOWN. Explicit.**

## What is actually live

`daemon.py` calls `tradfi_engine.run_tradfi_engine` every cycle
(`_run_book("TradFi Engine", _tradfi)`). That book runs a fully
self-contained **paper simulation** on `CL=F` (WTI, via yfinance) — it
is worth being precise here since the task brief frames the venue as
"WTIOIL-USDT on BloFin": tradfi_engine.py's own docstring says plainly
"there is no venue on BloFin for practice orders on CL=F ... It NEVER
touches BloFin and NEVER calls an order-placement endpoint." Oil is not
actually executing on BloFin at all right now; it's a paper book scoring
real CL=F candles and faking the fill.

The entry/exit logic that book runs is **`daily_pick.score_instrument`**
— imported unchanged from the crypto learning engine (BTC/ETH/SOL) —
plus `daily_pick._stop_target_pct` (stop = 1.0x ATR(14,1h) capped at a
flat 1.0%, target = 1.5x stop), `CONVICTION_FLOOR=40` (calm-regime
gate only), and `STOPOUT_COOLDOWN_H=6h`. Every point threshold inside
`score_instrument` — RSI3 <10/>90, 6x/2x volume shock, 1% momentum,
0.5% breakout proximity, MA20/100 cross — was tuned on crypto. None of
it was re-derived from oil's own distribution.

## Was it ever validated on oil?

No. Round 78 (2026-07-24, `step78_oil_playbook.py`) tested what was live
**that morning** — gold's donchian20+structure-trail and the S&P's RSI2
dip-buy — and found both FAIL on oil ("OIL STILL HAS ZERO VALIDATED
STRATEGIES, and now we also know the borrowed ones don't hold up").
`tradfi_engine.py` was written **later that same day** and swapped the
live logic to `score_instrument` — a *different* rule set than the one
round 78 tested — and that swap was never re-gauntleted. A grep of
`RESEARCH_LOG.md`/`MARKET_PLAYBOOKS.md` turns up zero mentions of
`score_instrument` or `tradfi_engine` ever being backtested, train/val
split, or sealed-tested on CL=F. The desk's one live winner (oil
+$58.39 — `tradfi_engine._migrated_paper_pnl_total`'s own docstring:
"yields exactly +58.39 — the oil win, and nothing else") is **one closed
trade** under this rule set. n=1 is not evidence of skill.

## What running it actually finds (this round)

Walk-forward replay of the **exact live decision loop** (every function
imported unchanged from `daily_pick.py`/`tradfi_engine.py` — no
reimplementation) against CL=F's full available history
(2024-03-27 → 2026-07-24, 1h bars), single-symbol (oil taken at every
slot it's eligible for, rather than competing with SPY for the live
book's 2-slot cap — a deliberate, generous relaxation: it can only make
oil's realized sample **larger** than what the live book actually gets,
never flatter the result any other way). `step110_livebook_audit.py`,
full trade list in `step110_table.csv`.

**1,888 replayed trades.** 60/20/20 split by trade count: train 1,132,
val 378, sealed 378 (never read).

Costs, execution="taker" always:
- Live book's own assumed cost (fee-only, 2bp/leg = 4bps round-trip):
  train **-$13.87/trade** (42.8% win), val **-$32.00/trade** (40.2% win).
- Repo-standard taker cost (fee 2bp + slippage 2bp + half-spread 1bp per
  leg = **10bps round-trip**, config.py's own conventions): train
  **-$37.10/trade** (edge -0.096% of notional, thickness **-0.96x** cost),
  val **-$54.05/trade** (edge -0.147% of notional, thickness **-1.47x**
  cost).

Both numbers are negative even before applying the 5x-thickness bar —
this isn't "the edge is too thin," it's negative expectancy outright,
train and val both, taker cost.

**Chance baseline** (randomized entry timing, same trade count/direction
mix/stop size as the real list, same exit engine, 500 resamples, taker
cost): train real result sits at the **81st percentile** of the random
distribution (i.e. *less bad* than random — the signal has some real
information on the exact slice it was scored on), but val real result
sits at the **8th percentile** (*worse* than random 92% of the time).
That flip between train and val is itself a finding: whatever the scorer
picks up on CL=F does not generalize — it's the classic in-sample-only
signature this desk has learned to distrust everywhere else.

**Stop-cap diagnostic:** 19% of trades (362/1,888) had their stop set by
the flat 1.0% cap, not by the ATR multiple — the evidence bar's
"never a swept percentage" rule is being violated on oil a fifth of the
time by construction, independent of the P&L result.

**Exit-reason breakdown:** 846 stops (avg **-$234.95**), 517 targets (avg
**+$264.96**), 525 time-exits (avg **-$7.69**, near flat as designed).
Roughly even win/loss geometry on winners vs losers by design (1.5x
target:stop), but the 40% win rate needed to break even at that ratio
plus taker cost isn't there (actual win rate ~38-43%).

Direction split: -960 short trades **-$40.67/trade avg**, 928 long
trades **-$28.85/trade avg** — both sides lose; this is not a
long-only-vs-short-only artifact.

## Cross-instrument transfer

**Not run.** The protocol is "CL=F survivors replay unchanged on a
second instrument" — there is no survivor here to transfer.

## The verdict, plainly

1. This exact rule set was **never validated on oil** before going live.
2. Run honestly against oil's own history at taker cost, it has
   **negative expectancy on both train and val**, with a val-period
   percentile against a randomized-timing chance baseline that says the
   scorer's picks are actively worse than noise out of sample.
3. It carries a **structural evidence-bar violation** (a flat 1.0%
   stop cap baked in from crypto, binding on 19% of oil trades) even
   setting the P&L result aside.
4. The one live "winner" (+$58.39) is n=1 under this rule set — luck on
   the board, not skill, exactly as flagged before this round started.

**Recommendation to Morgan: stand the live oil book down now.** Nothing
in this rule set should keep sizing real (paper) capital while a
replacement is built. This round does not propose a replacement — that
work starts at step112+ (see `step110_family_map.md`, appended through
the night).
