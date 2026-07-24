"""
step46_newsdesk_smoke.py — local smoke test for newsdesk.py.

Hits the REAL Supabase news RPC and REAL BloFin candles (read-only), then
runs newsdesk.run_newsdesk ONCE with dry=True: it computes and prints the
full decision (reconcile, pending/entry logic, sizing, stop/target) but
places NO orders and makes NO state/log/notify side effects (enforced
inside run_newsdesk itself, short-circuiting before every private.* order
call and every save_state/log_event/notify).

Prints, in order:
  1. the latest WatcherGuru rows found on the wire (and which are relevant
     per the exact classify_headline() import)
  2. current newsdesk pending/open state (before the dry run)
  3. what the book WOULD do right now
  4. proof the dry run made zero state writes (reload from source of truth)

Run:  python3 step46_newsdesk_smoke.py
"""

from __future__ import annotations

import config
from blofin_private import BlofinDemoPrivate, load_env
from newsdesk import SCAN_N, _fetch_recent_news, _is_watcherguru, run_newsdesk
from step45b_news_events import classify_headline
from step5_paper_trade import load_state


def main():
    env = load_env()
    private = BlofinDemoPrivate(
        env["BLOFIN_DEMO_API_KEY"],
        env["BLOFIN_DEMO_API_SECRET"],
        env["BLOFIN_DEMO_PASSPHRASE"],
    )
    live_feed, symbol = config.make_exchange("live")
    demo_feed, _ = config.make_exchange("demo")
    print(f"connected. symbol={symbol}")

    bal = private.futures_balance()
    net = private.net_position_contracts(symbol)
    print(f"demo futures balance: {float(bal.get('balance', 0)):,.2f} | "
          f"current net {symbol} position: {net:+.2f} contracts")

    # -- 1. the real news wire ------------------------------------------
    print(f"\n--- fetching {SCAN_N} most recent rows from cryptobot_recent_news ---")
    headlines = _fetch_recent_news(SCAN_N)
    print(f"total rows returned: {len(headlines)}")
    wg_rows = [h for h in headlines if _is_watcherguru(h)]
    print(f"WatcherGuru rows ('[WatcherGuru]' prefix): {len(wg_rows)}")
    for h in wg_rows:
        tag = classify_headline(h)
        rel = "RELEVANT" if tag["relevant"] else "not relevant"
        print(f"  [{rel:>13}] {h[:110]!r}")
    if not wg_rows:
        print("  (none in this window — the feed mixes many sources; see "
              "newsdesk.py's module docstring REALITY CHECK)")

    # -- 2. current state, before the dry run ----------------------------
    state = load_state()
    nd_before = state.get("newsdesk", {})
    print(f"\nledger equity: ${state.get('virtual_equity', 0):,.2f}")
    print(f"newsdesk open_trade (pre-run): {nd_before.get('open_trade')}")
    print(f"newsdesk pending    (pre-run): {nd_before.get('pending')}")
    print(f"newsdesk last_event_ts        : {nd_before.get('last_event_ts')}")
    print(f"newsdesk seen_headlines count : "
          f"{len(nd_before.get('seen_headlines', []))}")

    # -- 3. what the book would do now -----------------------------------
    print("\n--- run_newsdesk(dry=True) ---")
    result = run_newsdesk(private, live_feed, demo_feed, state, dry=True)
    print("--- end run_newsdesk ---\n")
    print(f"DECISION SUMMARY: {result}")

    # -- 4. prove dry mode made no state changes -------------------------
    state_after = load_state()
    nd_after = state_after.get("newsdesk", {})
    unchanged = (nd_before.get("open_trade") == nd_after.get("open_trade")
                and nd_before.get("pending") == nd_after.get("pending")
                and nd_before.get("last_event_ts") == nd_after.get("last_event_ts")
                and nd_before.get("seen_headlines") == nd_after.get("seen_headlines"))
    print(f"state unchanged by dry run: {'YES' if unchanged else 'NO -- BUG'}")


if __name__ == "__main__":
    main()
