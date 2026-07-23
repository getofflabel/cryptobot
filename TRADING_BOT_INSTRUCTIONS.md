# TRADING BOT INSTRUCTIONS — the constitution
(Idea adopted from TradingBotV2's instructions-file pattern; contents are
ours. Any session or agent touching this system reads this first.)

## 1. Project Goal
Grow a virtual $1,000 ledger to $2,000 on BloFin DEMO, proving a repeatable
formula worth real capital. Wallace's metrics: MONTHLY ledger growth with
compounding, benchmarked against buy-and-hold Bitcoin (underperforming HODL
cumulatively = failure). Universe: BTC, ETH, SOL only.

## 2. Safety Rules
- DEMO ONLY. `blofin_private.py` hardcodes the demo host — live trading is
  structurally impossible in this codebase. A live build is a separate,
  deliberate project with its own review.
- Secrets live in `.env` locally / GitHub Actions secrets in cloud. Never
  in git, chat, or logs.
- Every position carries a server-side stop-loss bracket. No naked holds.
- flatten.py is the emergency close-everything button (dry-run by default).

## 3. Strategy Rules (the live books)
- THE RIDE — 4h vol-gated MA 20/100 long-only + funding cap (<=1bp).
  Uncapped holds; exits when the trend dies; SL -8% (crash insurance only,
  never trade management — TP measured harmful and removed).
- THE STRIKES (one slot per asset, first trigger wins):
  BTC: panic-dip (RSI3<15) 10x · flag-touch(1h) 6x · flag-2h 3x (ON WATCH)
  ETH: the amplifier — fires on BTC's panic-dip, 8x, ETH geometry
  SOL: built, DORMANT until a re-audit passes it.
  All strike entries: maker-first with chase, TP limit + SL bracket, 48h max.
- SHADOWS (zero real orders, forward-evidence builders): forensic short
  (funding>2bp + pop + vol), 15-minute wide-stop system (promotion at 30+
  forward trades with positive expectancy).

## 4. Risk Rules
- Allocations: RIDE 60% x 3x (its measured growth peak). STRIKES 40%
  (BTC slot 25%, ETH slot 15%), per-trigger leverage from each trigger's
  own Kelly optimum. Peak combined exposure ~5.5-7.8x equity in bull dips —
  chosen aggression, documented worst combined drawdown -72% (in spec).
- Sizing always computed from CURRENT ledger equity (compounding).
- Leverage language with Wallace: slice-at-dial ("$200 in at 20x"), never
  exposure multiples.

## 5. Venue / Connection Rules
- Trades on BloFin demo; research data from Bybit/OKX/deribit publics.
- Cloud: GitHub Actions hourly heartbeat (hourly.yml) — snapshot -> ride
  (4h boundaries) -> strikes -> shadows. State in Supabase via secret-
  gated RPCs. NEVER run the old local loop alongside the cloud.

## 6. Memory Rules
- Ledger: trades_log.jsonl (local) + cryptobot_log (cloud) record every
  event. trigger_stats in state track live outcomes per trigger.
- AUTO-BENCH: any trigger with >=8 live trades and negative expectancy is
  benched automatically (no new entries) + Wallace notified. Small samples
  never veto — that would be learning from noise.
- Research memory: RESEARCH_LOG.md (every look recorded), RESEARCH_QUEUE.md
  (what's next), quarterly re-audits for benched near-misses.

## 7. Definition of Done (proof standard for real money)
>=3 months live or 30+ strike trades + 3+ ride trades, whichever later;
live expectancy inside backtest bands; fills consistent with model; zero
unexplained ledger/exchange divergences; infra clean. All five auditable
via `python3 audit.py`. Then the capital decision is Wallace's.
