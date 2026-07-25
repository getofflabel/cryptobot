"""
flatten.py — the emergency "close everything" button.

Run:  python3 flatten.py            # show what's open, ask nothing, do nothing
      python3 flatten.py --confirm  # actually close every open position

Every trading system needs one of these, and you want it BEFORE you need it.
When something goes wrong at 3am — a stuck bot, a runaway loop, a strategy
behaving nothing like its backtest — you do not want to be writing this file
while positions move against you. You want to run one command.

Safety choices baked in:
  - does nothing without --confirm
  - reads each position's OWN margin mode instead of assuming
  - every order is reduce_only, so it can only ever shrink a position,
    never accidentally open a new one in the opposite direction
  - verifies flat afterwards instead of trusting that the order worked
"""

import argparse
import time

import config
from blofin_private import BlofinDemoPrivate, load_env, make_client_order_id


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true",
                    help="actually place the closing orders")
    args = ap.parse_args()

    env = load_env()
    p = BlofinDemoPrivate(env["BLOFIN_DEMO_API_KEY"],
                          env["BLOFIN_DEMO_API_SECRET"],
                          env["BLOFIN_DEMO_PASSPHRASE"])

    positions = [x for x in p.positions()
                 if float(x.get("positions", 0) or 0) != 0]

    if not positions:
        print("Account is already flat. Nothing to close.")
        return

    print(f"Found {len(positions)} open position(s) on the DEMO account:\n")
    for x in positions:
        size = float(x["positions"])
        print(f"  {x['instId']}  {size:+,.1f} contracts  "
              f"{x['marginMode']} {x.get('leverage', '?')}x")
        print(f"    entry {float(x['averagePrice']):,.2f}  "
              f"mark {float(x['markPrice']):,.2f}  "
              f"unrealized {float(x['unrealizedPnl']):+,.2f} USDT")

    if not args.confirm:
        print("\nDry run. Nothing was closed.")
        print("To actually close these, run:  python3 flatten.py --confirm")
        return

    print("\nClosing...")
    for x in positions:
        size = float(x["positions"])
        side = "sell" if size > 0 else "buy"
        oid = p.market_order(x["instId"], side, abs(size),
                             reduce_only=True,
                             margin_mode=x["marginMode"],
                             client_order_id=make_client_order_id("fl"))
        print(f"  {x['instId']}: {side} {abs(size):,.1f} contracts "
              f"(order {oid})")

    time.sleep(2)
    remaining = [x for x in p.positions()
                 if float(x.get("positions", 0) or 0) != 0]
    if remaining:
        print(f"\nWARNING: {len(remaining)} position(s) still open. "
              f"Check the BloFin app.")
        for x in remaining:
            print(f"  {x['instId']} {float(x['positions']):+,.1f}")
    else:
        print("\nAccount is now FLAT.")
        bal = p.futures_balance()
        print(f"  USDT balance: {float(bal['balance']):,.2f}  "
              f"(available {float(bal['available']):,.2f}, "
              f"frozen {float(bal['frozen']):,.2f})")


if __name__ == "__main__":
    main()
