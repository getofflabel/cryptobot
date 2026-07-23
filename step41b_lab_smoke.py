"""
step41b_lab_smoke.py — local smoke test for shorts_lab.py.

Instantiates the real BlofinDemoPrivate client from .env, builds the live +
demo feeds exactly like hourly.py/daemon.py do, and runs shorts_lab.run_lab
ONCE with dry=True: it computes and prints the full decision (gate status,
both trigger conditions, sizing, stop/target) but places NO orders and makes
NO state/log/notify side effects (dry mode is enforced inside run_lab itself,
short-circuiting before every private.* order call and every save_state/
log_event/notify).

Run:  python3 step41b_lab_smoke.py
"""

from __future__ import annotations

import config
from blofin_private import BlofinDemoPrivate, load_env
from shorts_lab import run_lab
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

    state = load_state()
    print(f"ledger equity: ${state.get('virtual_equity', 0):,.2f} | "
          f"benched_triggers: {state.get('benched_triggers', [])}")
    print(f"core open_trade: {state.get('open_trade')}")
    print(f"tactical open_trade: {state.get('tactical', {}).get('open_trade')}")
    print(f"shorts_lab open_trade (pre-run): "
          f"{state.get('shorts_lab', {}).get('open_trade')}")

    print("\n--- run_lab(dry=True) ---")
    result = run_lab(private, live_feed, demo_feed, state, dry=True)
    print("--- end run_lab ---\n")

    print(f"DECISION SUMMARY: {result}")

    # prove dry mode made no state changes: reload from source of truth
    state_after = load_state()
    lab_before = state.get("shorts_lab", {}).get("open_trade")
    lab_after = state_after.get("shorts_lab", {}).get("open_trade")
    print(f"state unchanged by dry run: "
          f"{'YES' if lab_before == lab_after else 'NO -- BUG'}")


if __name__ == "__main__":
    main()
