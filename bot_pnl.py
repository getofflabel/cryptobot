"""Bot-only PnL, scored from the moment the bot took over.

Wallace's own trading before that moment does not count. The baseline lives in
bot_baseline.json so this number can never quietly drift.

    python3 bot_pnl.py
"""

import json
from pathlib import Path

from blofin_private import BlofinDemoPrivate, load_env

BASELINE = json.loads((Path(__file__).parent / "bot_baseline.json").read_text())


def bot_pnl() -> dict:
    env = load_env()
    p = BlofinDemoPrivate(
        env["BLOFIN_DEMO_API_KEY"],
        env["BLOFIN_DEMO_API_SECRET"],
        env["BLOFIN_DEMO_PASSPHRASE"],
    )

    balance = float(p.futures_balance()["balance"])
    unrealized = sum(
        float(x["unrealizedPnl"])
        for x in p.positions("BTC-USDT")
        if float(x.get("positions", 0) or 0)
    )

    start = BASELINE["start_equity_usdt"]
    equity = balance + unrealized

    return {
        "start_equity": start,
        "equity_now": equity,
        "bot_pnl": equity - start,
        "bot_pnl_pct": (equity - start) / start * 100,
        "balance": balance,
        "unrealized": unrealized,
    }


if __name__ == "__main__":
    r = bot_pnl()
    print(f"bot started    : {BASELINE['start_local']}  @  ${r['start_equity']:,.2f}")
    print(f"equity now     : ${r['equity_now']:,.2f}  "
          f"(balance {r['balance']:,.2f} + unrealized {r['unrealized']:+,.2f})")
    print(f"BOT PnL        : ${r['bot_pnl']:+,.2f}  ({r['bot_pnl_pct']:+.3f}%)")
    print()
    print(f"excluded (yours): ${BASELINE['excluded_pre_bot']['realized_pnl_usdt']:+,.2f} "
          "realized before the bot started — not the bot's score")
