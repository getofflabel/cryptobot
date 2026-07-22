# cryptobot — DEMO-ONLY BTC perp bot (BloFin demo)

Live paper-trading bot + research harness. See step5_paper_trade.py.
Cloud: runs as a Render cron job every 4h (`python step5_paper_trade.py --once`).
State lives in Supabase (secret-gated RPCs). No real-money capability exists in this codebase.
