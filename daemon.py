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


# BOOK HEALTH WATCHDOG (2026-07-24): a book that crashes every cycle is the
# WORST failure mode — it silently misses trades, which biases the live track
# record (it can still take losers while crashing through winners). The bs4
# bug did exactly this to the Newsdesk on launch night: "newsdesk error" every
# cycle, visible only in Render logs nobody was reading. Now: 3 consecutive
# failures of the same book -> ONE loud Telegram alert (per boot, so it can't
# spam), plus a log_event every failure so the journal shows the outage.
_book_fail_counts: dict = {}
_book_alerted: set = set()


def _run_book(name, fn):
    try:
        fn()
        _book_fail_counts[name] = 0
    except Exception as e:
        _book_fail_counts[name] = _book_fail_counts.get(name, 0) + 1
        n = _book_fail_counts[name]
        print(f"  {name} error ({n} in a row): {str(e)[:120]}")
        try:
            from step5_paper_trade import log_event, notify
            log_event({"action": "book_error", "book": name,
                       "consecutive": n, "error": str(e)[:200]})
            if n >= 3 and name not in _book_alerted:
                _book_alerted.add(name)
                notify(f"🚨 {name} IS DOWN (demo)",
                       f"{name} has crashed {n} cycles in a row and is "
                       f"MISSING ITS TRADES: {str(e)[:120]}")
        except Exception:
            pass


def full_cycle(private, live_feed, demo_feed, symbol, reason):
    """Run the whole decision stack once (same work the hourly job does)."""
    print(f"\n[{_now():%H:%M:%S}] === DECISION CYCLE ({reason}) ===")
    try:
        from step5_paper_trade import load_state, sync_ledger_to_account
        sync_ledger_to_account(private, symbol, load_state())
    except Exception as e:
        print(f"  ledger sync skipped: {str(e)[:60]}")
    hour = _now().hour

    def _ride():
        if hour % 4 == 0 or reason.startswith("shock"):
            from step5_paper_trade import decide_and_trade
            decide_and_trade(private, live_feed, symbol)

    def _strikes():
        from tactical import run_strikes
        from step5_paper_trade import load_state
        run_strikes(private, live_feed, demo_feed, load_state())

    def _lab():
        from shorts_lab import run_lab
        from step5_paper_trade import load_state
        run_lab(private, live_feed, demo_feed, load_state())

    def _news():
        from newsdesk import run_newsdesk
        from step5_paper_trade import load_state
        run_newsdesk(private, live_feed, demo_feed, load_state())

    def _gold():
        # THE GOLD BOOK (round 48, GLD donchian55/EMA20): broker-free, its
        # own separate paper ledger, zero exchange orders — safe to call on
        # EVERY full_cycle. run_gold_book's own internal last_bar_date
        # guard makes every call a no-op except the first one after a NEW
        # daily GLD bar closes; its own FETCH_THROTTLE_S (30 min) caps how
        # often it will even hit yfinance, independent of how often this
        # daemon cycles.
        from gold_book import run_gold_book
        from step5_paper_trade import load_state
        run_gold_book(load_state())

    _run_book("The Ride", _ride)
    _run_book("The Strikes", _strikes)
    _run_book("Shorts Lab", _lab)
    _run_book("The Newsdesk", _news)
    _run_book("The Gold Book", _gold)


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
        from step5_paper_trade import log_event, notify, load_state, save_state
        log_event({"action": "daemon_boot", "host": "render",
                   "price": boot_px})
        # PHONE ALERT GATE: only ping on boot if the last boot-ping was >2h
        # ago. Routine redeploys (minutes apart) must NOT spam the phone with
        # "worker online" price messages — that noise is what buried the real
        # trade alerts. A genuine outage recovery (long gap) still notifies.
        try:
            st = load_state()
            last = st.get("last_boot_notify")
            gap_ok = True
            if last:
                gap_ok = (_now() - datetime.fromisoformat(last)
                          ).total_seconds() > 7200
            if gap_ok:
                notify("🖥️ Bot back online",
                       "Restarted and watching again. Alerts only fire now "
                       "for real events: trades, fills, big moves. (demo)")
                st["last_boot_notify"] = _now().isoformat()
                save_state(st)
        except Exception:
            pass
        print(f"  boot ok — BloFin reachable, BTC ${boot_px:,.0f}", flush=True)
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
                    from step5_paper_trade import load_state
                    from live_read import write_live_read
                    st = load_state()
                    st["daemon_heartbeat"] = _now().isoformat()
                    # publishes the on-screen HUD's snapshot AND saves state
                    # (heartbeat included) in one write
                    write_live_read(live_feed, st)
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
