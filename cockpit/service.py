"""
cockpit/service.py — the small local service the panel talks to.

WHY THE PANEL DOES NOT DO ANY OF THIS ITSELF
    A browser extension is the wrong place for trading logic and an actively
    dangerous place for credentials. Everything that knows anything — the
    Alpaca keys, the Telegram token, the signal journal, the balance — stays
    here, on his machine, bound to 127.0.0.1 so nothing off the machine can
    reach it. The extension is a pane of glass: it asks this for a picture
    and draws it.

THE CONTRACT WITH THE PANEL, WHICH IS THE WHOLE DESIGN
    1. Every value that can go stale is returned with an ABSOLUTE timestamp,
       never with an age. The panel subtracts from its own clock. That way,
       if this service dies, the ages on screen keep climbing and everything
       greys out by itself. An age computed here would freeze at whatever it
       was when the last answer arrived and would sit there looking healthy.
    2. Anything unknown is null WITH A SENTENCE SAYING WHY. There is no zero
       standing in for a missing number anywhere in this file.
    3. `server_time` comes back on every answer so the panel can notice its
       own clock disagreeing with this one rather than silently mis-stating
       every age.

SAFETY
    Read-only over HTTP: the only method allowed is GET. There is no route
    that places, modifies or cancels anything, and this file imports nothing
    that could.

USAGE
    python3 -m cockpit.service            # listens on 127.0.0.1:8787
    python3 -m cockpit.service --port 9000
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cockpit import prices, signals, store                     # noqa: E402

HOST = "127.0.0.1"
PORT = 8787

# The desk sweeps once a minute. Twice that with a little slack, and we can
# say it has stopped rather than that it is quiet.
DESK_SILENT_SECONDS = 150


def desk_state() -> dict:
    """Is the thing that watches the markets actually alive?

    "No signal" and "nothing has been watching for two hours" look identical
    on a panel that does not ask this, and they are opposite situations.
    """
    hb = store.heartbeat()
    if not hb:
        return {"alive": False, "as_of": None,
                "why": ("the desk recorder has never run. Start it:  "
                        "python3 -m cockpit.desk_recorder")}
    alive = hb["age_seconds"] <= DESK_SILENT_SECONDS

    # Which markets were actually checked on the last sweep, and which threw.
    # A market that could not be reached is not a quiet market, and the two
    # must not share a line on the panel.
    checked, failed = [], []
    for m in hb.get("markets") or []:
        if isinstance(m, dict):
            (checked if m.get("ok") else failed).append(m)
        else:
            checked.append({"name": m, "ok": True})

    return {"alive": alive, "as_of": hb["as_of"],
            "markets": [m["name"] for m in checked],
            "failed": failed,
            "note": hb.get("note") or "",
            "why": None if alive else
                   "the desk recorder has stopped sweeping the markets"}


def picture(tv_symbol: str) -> dict:
    """Everything the panel draws, in one answer."""
    out = {"server_time": time.time()}

    # ---- what he is looking at, and what it costs right now
    try:
        out["price"] = prices.quote(tv_symbol)
    except Exception as e:
        out["price"] = {"kind": "unknown", "symbol": tv_symbol,
                        "quote": {"ok": False,
                                  "why": f"the price lookup itself failed: "
                                         f"{str(e)[:140]}"}}

    # ---- the balance
    acct = store.account()
    out["account"] = acct
    out["account_why"] = None if acct else (
        "I do not know what is in the account. Nothing will be sized until I "
        "do. Text the bot:  balance 105000  — or run:  python3 -m "
        "cockpit.tv_balance --read")

    # ---- the signal, exactly as his phone has it
    try:
        sig = signals.current()
    except Exception as e:
        sig = None
        out["signal_error"] = f"the recorded signal could not be read back: " \
                              f"{str(e)[:160]}"
    out["signal"] = sig
    out["signal_why"] = None if sig else (
        "no entry alert has been recorded yet. Silence from the bot means "
        "nothing is setting up — but only while the desk recorder is running, "
        "which is shown below.")

    # ---- what that signal risks, against the balance we know NOW
    #
    # A SIGNAL THAT COULD NOT BE SIZED RISKS AN UNKNOWN AMOUNT, NOT ZERO.
    # Summing `None` as nought would put "this signal risks $0.00" on the
    # panel next to a trade he is about to place by hand, which is the worst
    # single line this thing could print. So the unsized ones are counted and
    # named, and if none of them has a size there is no risk figure at all.
    out["risk_now"] = None
    if sig and acct:
        known = [t["risk_dollars"] for t in sig["trades"]
                 if t.get("risk_dollars") is not None]
        unsized = [t["symbol"] for t in sig["trades"]
                   if t.get("risk_dollars") is None]
        used = sig.get("account_used") or 0
        notes = []
        if unsized:
            notes.append("no size could be worked out for " +
                         ", ".join(unsized) + ", so what it risks is unknown")
        if used and abs(used - acct["equity"]) > 0.005 * acct["equity"]:
            notes.append(f"this was sized against ${used:,.0f}, and the "
                         f"balance is ${acct['equity']:,.0f} now — the sizes "
                         f"above are the ones that went to your phone")
        if known:
            risked = sum(known)
            out["risk_now"] = {
                "dollars": round(risked, 2),
                "pct_of_account": round(100.0 * risked / acct["equity"], 2),
                "note": "; ".join(notes) or None,
            }
        elif unsized:
            out["risk_now"] = {"dollars": None, "pct_of_account": None,
                               "note": "; ".join(notes)}

    # ---- what the bot believes is open, and whether it could even know
    op = store.open_trades()
    started = op.get("desk_started_at")
    fired = (sig or {}).get("fired_at")
    op["may_be_incomplete"] = (
        f"the bot restarted after the last alert fired, and it keeps its open "
        f"trades in memory — so anything you took before that restart is not "
        f"in this list even if you are still in it"
        if started and fired and started > fired else None)
    out["open"] = op
    out["desk"] = desk_state()
    out["recent"] = signals.recent()
    return out


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        # The panel runs inside tradingview.com. This service listens on the
        # loopback address only, so nothing off this machine can reach it at
        # all, and the browser needs to be told the page may read the answer.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):                                    # noqa: N802
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path == "/health":
                self._send(200, {"ok": True, "server_time": time.time(),
                                 "desk": desk_state()})
            elif u.path in ("/cockpit", "/"):
                self._send(200, picture((q.get("symbol") or [""])[0]))
            else:
                self._send(404, {"ok": False, "why": f"no route {u.path}"})
        except Exception as e:
            traceback.print_exc()
            self._send(500, {"ok": False,
                             "why": f"the cockpit service hit an error: "
                                    f"{str(e)[:200]}",
                             "server_time": time.time()})

    def do_POST(self):                                   # noqa: N802
        # Nothing here changes anything. Saying so out loud is cheaper than
        # someone later assuming there must be a way.
        self._send(405, {"ok": False,
                         "why": "this service is read-only; it has no route "
                                "that changes anything"})

    def log_message(self, fmt, *args):
        return                     # one line per second in the terminal is noise


def serve(port: int = PORT) -> None:
    srv = ThreadingHTTPServer((HOST, port), Handler)
    print(f"cockpit service on http://{HOST}:{port}  (loopback only, GET only, "
          f"nothing here can place an order)")
    srv.serve_forever()


def main(argv):
    port = PORT
    if "--port" in argv:
        port = int(argv[argv.index("--port") + 1])
    serve(port)


if __name__ == "__main__":
    main(sys.argv)
