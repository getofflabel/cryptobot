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

    # 2b. SHADOW BOOK: the forensic short (funding>2bp + 4h pop>1.5% +
    #     ATR>1.2%) — both gauntlet windows positive but only 6 validation
    #     instances (rule needs 8). No orders: we LOG every live firing so
    #     forward evidence accumulates weekly instead of waiting quarters.
    try:
        from strategy import atr as _atr
        from step5_paper_trade import current_funding_bps, log_event
        c1 = live_feed.get_candles(symbol, "1h", 30)
        fb_now = current_funding_bps(live_feed, symbol)
        pop4 = (c1["close"].iloc[-1] / c1["close"].iloc[-5] - 1) * 100
        atr_now = float((_atr(c1, 14) / c1["close"] * 100).iloc[-1])
        if fb_now is not None and fb_now > 2.0 and pop4 > 1.5 and atr_now > 1.2:
            px = float(c1["close"].iloc[-1])
            print(f"[SHADOW] forensic-short FIRED @ {px:,.1f} "
                  f"(funding {fb_now:+.2f}bp, pop {pop4:+.1f}%, ATR {atr_now:.2f}%)")
            log_event({"action": "shadow_short_signal", "price": px,
                       "funding_bps": fb_now, "pop4": round(pop4, 2),
                       "atr_pct": round(atr_now, 2)})
    except Exception as e:
        print(f"shadow check failed (non-fatal): {str(e)[:80]}")

    # 3. tactical book, every hour
    try:
        from step5_paper_trade import load_state
        from tactical import run_strikes
        state = load_state()
        run_strikes(private, live_feed, demo_feed, state)
    except Exception as e:
        print(f"TACTICAL cycle error: {str(e)[:150]}")
        from step5_paper_trade import log_event
        log_event({"action": "error", "book": "tactical",
                   "error": str(e)[:300]})


if __name__ == "__main__":
    main()
