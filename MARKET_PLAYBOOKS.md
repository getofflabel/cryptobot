# MARKET PLAYBOOKS — each market's personality, learned the hard way
Standing rule (Wallace, 2026-07-24): every market is different; the
adjustments per market must be REMEMBERED. This file is that memory —
updated after every research round and every live lesson. Numbers only,
no vibes.

## BITCOIN (BTC-USDT) — the home market
- Personality: 24/7, no sessions, news reacts instantly (1.33x baseline
  after WatcherGuru posts — the news edge's home). Volatility DECAYS
  era-over-era: hourly ATR medians fell ~0.9% -> ~0.45% across 6y.
- What works (validated): 4h trend w/ STRICT 1.5% vol gate (the gate's
  selectivity IS the edge in grinds — R54 sealed proof), 1h RSI3 dip-buys
  in uptrends (needs 48h room — same-day exits kill it, R43), news
  momentum (first-hour direction, sealed PASS), sparse volume-shock
  continuation (R50 two-window, sealed look pending).
- What dies here: ALL always-on shorts (5x confirmed), dense 15m anything
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
- OPEN: R55 (EMA crosses, sessions, intraday families) running.

## S&P 500 (SPY/ES=F research)
- VENUE (verified 2026-07-24): **SPY-USDT on BloFin prod IS the real S&P
  tracker** (last 738.75 vs real SPY 738.18 — 0.08% basis) but is NOT
  served on the demo host (ticker empty) and is THIN (~$650k/24h).
  **SPX-USDT is the SPX6900 MEMECOIN — one letter, wrong instrument,
  never confuse them.** Paper venue: none yet; research banks knowledge.
- Personality: session-bound (9:30-16:00 ET), overnight gaps carry the
  drift, WatcherGuru news does NOT move it in-session (1.03x — R47);
  the world's most mean-reverting major index historically.
- Findings so far: trend ports mostly INSUFFICIENT-SAMPLE on daily
  (too slow), dip/news families nothing yet. Needs its own system.
- OPEN: R60 (index-native families: gap plays, first-hour range,
  index dip-buying, EMA regimes) launching 2026-07-24.

## ETH / SOL / TSLA (satellites)
- ETH: amplifier (BTC panic-dip trigger at ETH geometry) validated;
  R52: stock perps track well (corr .76-.96) but listings young.
- TSLA: demo-tradeable, in Daily Pick rotation; NVDA d20 breakout was
  the strongest single-stock candidate (val>train, all decades) — no
  demo venue for NVDA yet.
- Playbooks to be written as their systems get built.
