"""
cockpit/telegram_balance.py — route B for the balance: he texts it.

WHY THERE IS A SECOND ROUTE
    Route A reads the balance off his TradingView panel, which is better
    because it needs nothing from him. But it depends on a browser session
    that will eventually be logged out, and on a page whose layout is not
    ours. When it stops working we must not fall back to a guess, so there
    has to be a route that always works and needs only his phone.

    He sends the bot:            balance 105000
    It answers:                  Balance set to $105,000. Noted at 19:42.
    He sends just:               balance
    It answers with the stored number AND how old it is.

    Both routes write to cockpit/store, which hands whichever is FRESHER to
    everything downstream.

WHO IS ALLOWED TO SET IT
    Only the chat id in .env — his own. A message from any other chat is
    ignored without a reply. This is not paranoia about a busy bot: the
    balance sets the size of every future trade, so anyone who could write
    it could change how much money he puts on the line.

SAFETY
    This process reads messages and writes one number to disk. It has no
    trading command, no order path, and nothing it can be told to do beyond
    setting or reporting a balance. Anything it does not recognise is
    ignored — it never runs, forwards or acts on the content of a message.

USAGE
    python3 -m cockpit.telegram_balance            # listen
    python3 -m cockpit.telegram_balance --once     # drain what is waiting
    python3 -m cockpit.telegram_balance --show     # print what is stored
"""

from __future__ import annotations

import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cockpit import store                                      # noqa: E402

OFFSET_PATH = os.path.join(store.STATE, "telegram_offset.json")

# "balance 105000", "balance $105,000.50", "balance: 105k" — but never a bare
# number on its own, which would make a stray message move his position size.
BALANCE_RE = re.compile(
    r"^\s*balance\b[:\s]*\$?\s*([0-9][0-9,_]*(?:\.[0-9]+)?)\s*([kKmM])?\s*$",
    re.I)                    # he types it however he types it
QUERY_RE = re.compile(r"^\s*balance\s*\??\s*$", re.I)


def creds() -> tuple:
    import alpaca                       # its load_env reads the same .env
    env = alpaca.load_env()
    tok = os.environ.get("TELEGRAM_BOT_TOKEN") or env.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID") or env.get("TELEGRAM_CHAT_ID")
    return tok, chat


def parse(text: str) -> float | None:
    """The number he meant, or None. 105k means 105,000 because he types it
    that way; a bare 105 means 105 dollars and is left alone."""
    m = BALANCE_RE.match(text or "")
    if not m:
        return None
    n = float(m.group(1).replace(",", "").replace("_", ""))
    suffix = (m.group(2) or "").lower()
    if suffix == "k":
        n *= 1_000
    elif suffix == "m":
        n *= 1_000_000
    return n


def say(tok: str, chat: str, text: str) -> None:
    import requests
    try:
        requests.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                      data={"chat_id": chat, "text": text}, timeout=8)
    except Exception as e:
        print(f"  reply failed: {str(e)[:100]}")


def stored_words() -> str:
    a = store.account()
    if not a:
        return ("I do not know your balance. Nothing will be sized until I "
                "do. Send:  balance 105000")
    mins = a["age_seconds"] / 60.0
    when = (f"{mins:.0f} minutes ago" if mins < 90 else
            f"{mins / 60:.1f} hours ago" if mins < 48 * 60 else
            f"{mins / 1440:.1f} days ago")
    line = (f"${a['equity']:,.2f}, {a['route_words']}, set {when}.")
    if a["stale"]:
        line += ("\n\nTHAT IS MORE THAN A DAY OLD. Every size I send is worked "
                 "out from it. Send me the current one.")
    return line


def handle(text: str, tok: str, chat: str) -> bool:
    """One message. True if it was a balance command."""
    if QUERY_RE.match(text or ""):
        say(tok, chat, stored_words())
        return True
    n = parse(text)
    if n is None:
        return False
    if n <= 0:
        say(tok, chat, "That is not a balance I can use. Send a positive "
                       "number, like:  balance 105000")
        return True
    store.record_balance("telegram", n, detail="he texted it")
    say(tok, chat, f"Balance set to ${n:,.2f}, noted "
                   f"{time.strftime('%H:%M')}. Every size from here is worked "
                   f"out from that.")
    print(f"  balance set to {n:,.2f}")
    return True


def offset() -> int:
    return int((store._read(OFFSET_PATH, {}) or {}).get("offset") or 0)


def set_offset(n: int) -> None:
    store._write(OFFSET_PATH, {"offset": int(n)})


def drain(tok: str, chat: str, wait: int = 25) -> int:
    """One long poll. Returns how many messages were read."""
    import requests
    try:
        r = requests.get(f"https://api.telegram.org/bot{tok}/getUpdates",
                         params={"offset": offset() + 1, "timeout": wait},
                         timeout=wait + 10)
        updates = (r.json() or {}).get("result") or []
    except Exception as e:
        print(f"  telegram did not answer: {str(e)[:100]}")
        time.sleep(5)
        return 0
    for u in updates:
        set_offset(u.get("update_id", offset()))
        msg = u.get("message") or u.get("edited_message") or {}
        frm = str((msg.get("chat") or {}).get("id") or "")
        text = msg.get("text") or ""
        if frm != str(chat):
            # Not him. Not answered, not acted on, not stored.
            print(f"  ignored a message from chat {frm}")
            continue
        handle(text, tok, chat)
    return len(updates)


def main(argv):
    if "--show" in argv:
        print(stored_words())
        return
    tok, chat = creds()
    if not tok or not chat:
        print("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID are not in .env — this "
              "route cannot listen.")
        return
    if "--once" in argv:
        n = drain(tok, chat, wait=1)
        print(f"  read {n} message(s)")
        return
    print("listening for:  balance 105000   (and for a bare 'balance' to "
          "read it back). Nothing else is acted on.")
    while True:
        drain(tok, chat)


if __name__ == "__main__":
    main(sys.argv)
