# cryptobot — a two-book, multi-asset paper-trading operation (DEMO ONLY)

Grows a virtual $1,000 ledger on BloFin's demo exchange using five
gauntlet-validated strategies, cloud-run 24/7, with a research engine that
keeps hunting nightly. **No real-money capability exists in this codebase**
(the demo host is hardcoded). Read `TRADING_BOT_INSTRUCTIONS.md` first —
it is the constitution.

## Architecture
```
GitHub Actions (hourly.yml, :07 every hour)
  └─ hourly.py ── collector.py      positioning snapshot -> Supabase
               ├─ step5 (RIDE)      4h trend book, at 4h boundaries
               ├─ tactical.py       THE STRIKES: BTC triggers + ETH amplifier
               └─ shadow15.py       15-minute system (shadow mode)
State/ledger: Supabase (secret-gated RPCs) ── survives any restart
Research:    nightly scheduled session works RESEARCH_QUEUE.md
```

## Commands (run from this directory)
| command | what it does |
|---|---|
| `python3 step5_paper_trade.py --check` | verify credentials + read balances (no orders) |
| `python3 hourly.py` | one full heartbeat (what the cloud runs) — CAUTION: places real demo orders when signals fire; never run near :07 |
| `python3 audit.py` | the proof engine: live vs backtest, five criteria |
| `python3 step2_verify_backtest.py` | 30 hand-checked engine tests |
| `python3 exec_test.py` | live-fire execution drill (tiny real orders, then flat) |
| `python3 flatten.py [--confirm]` | emergency close-everything |
| `gh run list --workflow=hourly.yml` | cloud heartbeat health |

## Files that matter
- `backtest.py` — the verified engine (costs, funding, intra-bar stops/targets, fractional sizing)
- `strategy.py` — all signal functions
- `TRADING_BOT_INSTRUCTIONS.md` — rules, risk, memory, definition of done
- `RESEARCH_LOG.md` / `RESEARCH_QUEUE.md` — every look taken / what's next
- `trades_log.jsonl` — the local event ledger (mirrored to cloud)
- `data_*.parquet` — cached research data (gitignored)

## Experimenting safely
New strategy ideas go through the gauntlet (see any `step*_round*.py` for
the pattern): 6yr data, 60/20/20 train/val/test, full costs, positive on
train AND val before ONE sealed test look. Survivors get deployed;
failures get logged in RESEARCH_LOG.md. Never re-tune a failed config.

## Safety limitations
Demo-only by construction · every position bracketed server-side ·
auto-bench memory pulls any trigger that proves bad live · secrets never
in git · deleting `.env` disables everything local.
