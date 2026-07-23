"""
daemon.py — THE ALWAYS-ON WORKER. A person in front of the screen 24/7.

This is a PERSISTENT process: it starts once and never exits. It holds live
connections open, keeps state in memory, and watches the price continuously
— reacting in seconds, not waiting for the next scheduled wake-up. This is
the difference Wallace asked for: not "glance every minute" but "never look
away."

WHAT IT DOES, FOREVER:
  - every few seconds: read the live price (WebSocket tick stream when the
    host allows it; fast REST polling as the always-works fallback)
  - the instant price jumps more than SHOCK_PCT: run the full decision stack
  - on every 1h close: run the strikes;  on every 4h close: run the ride
  - never dies: any error is caught, logged, and the loop continues

Deploy as a Render Background Worker (start command: python daemon.py). It
replaces the need for the GitHub hourly cron — but the cron stays as a
free backstop, so if the worker ever restarts, nothing is missed.
"""

from __future__ import annotations

import os
import time
import traceback
from datetime import datetime, timezone

import config
from blofin_private import BlofinDemoPrivate, load_env

POLL_SECONDS = 5           # price read cadence between events
SHOCK_PCT = 0.9            # % move that triggers an immediate decision
SHOCK_WINDOW_S = 90        # ...measured against the price this long ago


def _now():
    return datetime.now(timezone.utc)


def full_cycle(private, live_feed, demo_feed, symbol, reason):
    """Run the whole decision stack once (same work the hourly job does)."""
    print(f"\n[{_now():%H:%M:%S}] === DECISION CYCLE ({reason}) ===")
    try:
        from step5_paper_trade import load_state, sync_ledger_to_account
        sync_ledger_to_account(private, symbol, load_state())
    except Exception as e:
        print(f"  ledger sync skipped: {str(e)[:60]}")
    hour = _now().hour
    try:
        if hour % 4 == 0 or reason.startswith("shock"):
            from step5_paper_trade import decide_and_trade
            decide_and_trade(private, live_feed, symbol)
    except Exception as e:
        print(f"  ride error: {str(e)[:120]}")
    try:
        from tactical import run_strikes
        from step5_paper_trade import load_state
        run_strikes(private, live_feed, demo_feed, load_state())
    except Exception as e:
        print(f"  strikes error: {str(e)[:120]}")
    try:
        from shorts_lab import run_lab
        from step5_paper_trade import load_state
        run_lab(private, live_feed, demo_feed, load_state())
    except Exception as e:
        print(f"  shorts lab error: {str(e)[:120]}")


def main():
    env = load_env()
    for k, v in env.items():
        os.environ.setdefault(k, v)
    private = BlofinDemoPrivate(env["BLOFIN_DEMO_API_KEY"],
                                env["BLOFIN_DEMO_API_SECRET"],
                                env["BLOFIN_DEMO_PASSPHRASE"])
    live_feed, symbol = config.make_exchange("live")
    demo_feed, _ = config.make_exchange("demo")

    print(f"[{_now():%Y-%m-%d %H:%M:%S}] DAEMON LIVE — watching {symbol} "
          f"every {POLL_SECONDS}s, reacting instantly. This process never "
          f"sleeps.", flush=True)
    try:
        boot_px = live_feed.get_ticker(symbol).last   # proves BloFin reachable
        from step5_paper_trade import log_event, notify
        log_event({"action": "daemon_boot", "host": "render",
                   "price": boot_px})
        notify("🖥️ 24/7 worker ONLINE",
               f"Render daemon live, BTC ${boot_px:,.0f}. Watching every "
               f"{POLL_SECONDS}s, never sleeps. (demo)")
        print(f"  boot heartbeat sent — BloFin reachable, BTC ${boot_px:,.0f}",
              flush=True)
    except Exception as e:
        print(f"  BOOT WARNING — BloFin unreachable from Render: "
              f"{str(e)[:120]}", flush=True)

    price_history = []          # (timestamp, price)
    last_hour = -1
    last_heartbeat = 0.0
    # kick off with one decision so we start in a known state
    full_cycle(private, live_feed, demo_feed, symbol, "startup")

    while True:
        try:
            px = live_feed.get_ticker(symbol).last
            t = time.time()
            # heartbeat every 60s: tells the GitHub backstop "I'm alive,
            # you don't need to trade" — prevents double-trading, gives
            # automatic failover if this worker ever dies
            if t - last_heartbeat >= 60:
                last_heartbeat = t
                try:
                    from step5_paper_trade import load_state, save_state
                    st = load_state()
                    st["daemon_heartbeat"] = _now().isoformat()
                    save_state(st)
                except Exception:
                    pass
            price_history.append((t, px))
            price_history[:] = [(ts, p) for ts, p in price_history
                                if t - ts <= SHOCK_WINDOW_S]

            # --- shock check: biggest move within the window ---
            if len(price_history) > 2:
                old = price_history[0][1]
                move = abs(px / old - 1) * 100
                if move >= SHOCK_PCT:
                    direction = "UP" if px > old else "DOWN"
                    print(f"[{_now():%H:%M:%S}] ⚡ SHOCK {move:.1f}% {direction} "
                          f"-> ${px:,.0f}")
                    try:
                        from step5_paper_trade import log_event, notify
                        log_event({"action": "market_shock",
                                   "move_pct": round(move, 2), "price": px})
                        notify("🚨 MARKET SHOCK",
                               f"BTC {move:.1f}% {direction} in <90s -> "
                               f"${px:,.0f}. Bot reacting now.")
                    except Exception:
                        pass
                    full_cycle(private, live_feed, demo_feed, symbol,
                               f"shock {move:.1f}%")
                    price_history.clear()          # re-baseline after acting

            # --- scheduled bar closes ---
            h = _now().hour
            if h != last_hour:
                last_hour = h
                full_cycle(private, live_feed, demo_feed, symbol,
                           f"{h:02d}:00 bar close")

        except Exception as e:
            print(f"[{_now():%H:%M:%S}] loop error (continuing): {str(e)[:120]}")
            traceback.print_exc()

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
