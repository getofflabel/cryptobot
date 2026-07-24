# MARKET PLAYBOOKS — each market's personality, learned the hard way
Standing rule (Wallace, 2026-07-24): every market is different; the
adjustments per market must be REMEMBERED. This file is that memory —
updated after every research round and every live lesson. Numbers only,
no vibes.

## BITCOIN (BTC-USDT) — the home market
- Personality: 24/7, no sessions, news reacts instantly (1.33x baseline
  after WatcherGuru posts — the news edge's home). Volatility DECAYS
  era-over-era: hourly ATR medians fell ~0.9% -> ~0.45% across 6y.
- What works (validated): 1h CHoCH+confluence>=2 (structure flip with
  >=2 agreeing tools — sealed +$99.52/t through the drought; sweeps/FVG/
  fib are worthless ALONE but valuable as confluence votes), 4h HIDDEN RSI divergence (continuation entries
  at higher-low/RSI-lower-low inside trend — sealed +$52/t through the
  drought, ~18/yr, the toolkit's first sealed graduate), 4h trend w/ STRICT 1.5% vol gate (the gate's
  selectivity IS the edge in grinds — R54 sealed proof), 1h RSI3 dip-buys
  in uptrends (needs 48h room — same-day exits kill it, R43), news
  momentum (first-hour direction, sealed PASS), sparse volume-shock
  continuation (R50 two-window, sealed look pending).
- What dies here: order blocks (0/64), pin bars/engulfing/inside-bars
  (0/112 — and adding "context" made them WORSE), NR patterns, regular
  reversal divergences (1/96), ALL always-on shorts (5x confirmed), dense 15m anything
  (~9bps cost floor vs thin per-bar edge), fixed-parameter ports of any
  kind, same-day dip exits, momentum bursts/session breakouts in grinds.
- Dials: 1h stops ~1.2-1.7% work; funding matters (8h cadence, extremes
  = crowd signal); maker/taker 2/6bps.

## GOLD (XAUT-USDT live / GLD+GC=F research)
- Personality: session creature (London 08:00, NY 13:30 UTC), secular
  uptrend (shorts died 0/20 in R48), CALMER than BTC (hourly ATR% ~0.28
  -0.72 — BTC thresholds NEVER port; recompute per-market medians).
- What works (validated): donchian breakouts — d20+EMA20 exit sealed-
  PASSED 4x across GLD/GC=F incl. intraday-touch entry variant. ~5.4
  trades/yr at d20.
- What dies: crypto RSI3 dip-buy shape (1/72 in R48), shorts, tight ETF
  stops vs overnight gaps (44/45 gap-throughs at 0.5% — stops must
  respect gap risk or trade futures-style 23h venues).
- Venue notes: demo trades XAUT only (whole-contract lots, cv 0.001);
  weekend oracle ranges shrink 60-75% but never freeze; young-listing
  funding runs hot (~20%/yr on some TradFi perps).
- R55 VERDICT (2026-07-24): 114 configs, 23 two-window survivors, TOP 2
  EXECUTED AT SEALED: daily z-MR -$45.80/t x26 over 5.2y (the 2021-26
  trend regime kills gold mean reversion); 1h EMA20/50 -$61.86/t on its
  thin 5.8mo window (WATCH LIST — retest when hourly history grows, not
  dead). Sessions 0/6 (London/NY opens are NOT an edge here), pullback-
  in-trend 0/16, ALL shorts 0/36. Donchian fractals down (1h/4h two-
  window) but un-looked — thin-window rule applies. GOLD'S BAG REMAINS:
  breakouts, singular and proven.

## S&P 500 (SPY/ES=F research)
- VENUE (verified 2026-07-24): **SPY-USDT on BloFin prod IS the real S&P
  tracker** (last 738.75 vs real SPY 738.18 — 0.08% basis) but is NOT
  served on the demo host (ticker empty) and is THIN (~$650k/24h).
  **SPX-USDT is the SPX6900 MEMECOIN — one letter, wrong instrument,
  never confuse them.** Paper venue: none yet; research banks knowledge.
- Personality: session-bound (9:30-16:00 ET) with a REAL 17.5h dark
  overnight window on the ETF (SPY gaps >0.3% on 46.6% of days vs ES=F's
  6.8% — near-continuous futures sessions structurally don't have this).
  Long-biased: shorts and gap-up-fades lose to their long-side mirrors
  everywhere tested. WatcherGuru news does NOT move it in-session (R47,
  1.03x). The world's most famous dip-buy folklore market — and it's real.
- What works (validated, R60): RSI2<5 dip-buy (price>SMA200, exit
  close>SMA5 or RSI2>65, NO fixed target) — 12/12 configs SURVIVOR on
  BOTH SPY and ES=F, gap-honesty-clean, the round's cleanest edge.
  SMA100/200 regime membership (long while price>SMA, ~3-6 trades/yr) —
  4/4 SURVIVOR cross-instrument, but does NOT beat buy-and-hold on raw
  return (case is drawdown cut only: -15/-30% vs B&H's -20/-57%, exactly
  gold's R48 frame). Mean-reversion dip-buying generalizes across BOTH
  calm and crash/high-vol regimes (R60 family 4) — broader than the
  textbook "MR only in calm uptrends" claim.
- What dies: gap-fill (chase the fill after a gap, 0/16, confirmed dead
  both directions both instruments); naive N-day momentum continuation
  (0/24 across every regime cell tested, INCLUDING crash regimes where
  trend-following should theoretically win — refutes "momentum for
  crashes" for this shape specifically); golden cross (too slow to ever
  clear 30 trades on daily bars alone); first-hour range-break shorts and
  "both-directions" combos (long-only survives thin, everything else
  dies); overnight drift (real, t=4.4 on SPY, but the ~0.033%/night gross
  edge doesn't clear a single ETF round-trip cost — only reachable by a
  position already held overnight for other reasons, not a standalone
  day-trade); tight (1.0xATR) protective stops on the looser dip-buy
  shapes (rsi2<10/15, 5-day-low, downstreak) — give the dip room.
- Dials: daily median ATR% SPY 1.32% / ES=F 1.36% (recompute per-market,
  never port BTC/gold thresholds); ETF costs 4bps round trip, futures
  2bps; turn-of-month (R60 family 5) is the strongest seasonality signal
  found anywhere in this program, t=2.43, ~3x the rest-of-month mean —
  flagged for a dedicated round, not yet built into a strategy.
- OPEN: dedicated turn-of-month round; momentum-shape iteration (breakout/
  vol-scaled, since naive N-day continuation is dead); crash+below MR
  cell needs a wider look before trusting it (one config flips under
  gap-honesty); if SPY-USDT ever lands on the demo host, RSI2<5 dip-buy
  is the first candidate to deploy. Full detail: step60_results.md.

## ETH / SOL / TSLA (satellites)
- ETH: amplifier (BTC panic-dip trigger at ETH geometry) validated;
  R52: stock perps track well (corr .76-.96) but listings young.
- TSLA: demo-tradeable, in Daily Pick rotation; NVDA d20 breakout was
  the strongest single-stock candidate (val>train, all decades) — no
  demo venue for NVDA yet.
- Playbooks to be written as their systems get built.
