"""
hourly.py — the cloud brain's single hourly heartbeat.

Run:  python hourly.py     (one full cycle, then exit — designed for cron)

Every hour, in strict order (serialized on purpose — two books placing
orders concurrently on one symbol is how positions get tangled):

  1. POSITIONING SNAPSHOT  -> Supabase (the growing trader-data archive)
  2. CORE BOOK (only at 4h boundaries) — the champion at 2x on 80%
  3. TACTICAL BOOK (every hour) — MTF Dip at 10x on 20%
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import config
from blofin_private import BlofinDemoPrivate, load_env


def main():
    env = load_env()
    for k, v in env.items():                 # collector reads os.environ
        os.environ.setdefault(k, v)

    private = BlofinDemoPrivate(env["BLOFIN_DEMO_API_KEY"],
                                env["BLOFIN_DEMO_API_SECRET"],
                                env["BLOFIN_DEMO_PASSPHRASE"])
    live_feed, symbol = config.make_exchange("live")
    demo_feed, _ = config.make_exchange("demo")
    hour = datetime.now(timezone.utc).hour

    # 1. positioning snapshot (best-effort: research data must never block
    #    trading)
    try:
        import collector
        collector.main()
    except Exception as e:
        print(f"snapshot failed (non-fatal): {str(e)[:100]}")

    # 2. core book at 4h boundaries
    if hour % 4 == 0:
        try:
            from step5_paper_trade import decide_and_trade
            print(f"[CORE {hour:02d}:xx UTC] 4h boundary — champion decides")
            decide_and_trade(private, live_feed, symbol)
        except Exception as e:
            print(f"CORE cycle error: {str(e)[:150]}")
            from step5_paper_trade import log_event
            log_event({"action": "error", "book": "core",
                       "error": str(e)[:300]})

    # 3. tactical book, every hour
    try:
        from step5_paper_trade import load_state
        from tactical import tactical_cycle
        state = load_state()
        tactical_cycle(private, live_feed, demo_feed, symbol, state)
    except Exception as e:
        print(f"TACTICAL cycle error: {str(e)[:150]}")
        from step5_paper_trade import log_event
        log_event({"action": "error", "book": "tactical",
                   "error": str(e)[:300]})


if __name__ == "__main__":
    main()
