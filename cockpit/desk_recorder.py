"""
cockpit/desk_recorder.py — the desk, unchanged, with a notebook next to it.

WHAT IT IS
    tjr_desk.Desk does the watching and tjr_alerts writes the message. This
    file changes NEITHER. It subclasses the desk and overrides the two
    methods that push, so that every message going to his phone is also
    written down where the cockpit panel can read it.

    That is the whole trick, and it is deliberate: the panel is fed from the
    push itself, not from a second run of the method. There is no code path
    in which the screen and the phone can be looking at different signals,
    because there is only one signal and the screen sees a copy of the thing
    that was sent.

RUN THIS INSTEAD OF tjr_desk.py, NOT ALONGSIDE IT
    Two desks watching the same markets would message him twice for every
    setup. This one does everything tjr_desk.py does — same markets, same
    decisions, same alerts, same no-spam rules — and additionally records.

THE BALANCE IS READ FRESH, EVERY PASS
    tjr_desk carries ACCOUNT = 100,000 as a placeholder for a live runner to
    replace. This is that live runner. It reads the balance from the cockpit
    store before every pass, so the size in the alert is worked out off what
    is actually in his account.

    And when the balance is NOT known, it passes zero — which makes
    tjr_alerts print "Size COULD NOT BE WORKED OUT — do not take this one"
    instead of a number. That is the intended behaviour, not a bug to route
    around: a size worked out from a balance we are guessing at is worse
    than no size, because he would type it in.

SAFETY
    No orders. tjr_desk.py, tjr_alerts.py and every market file are imported
    and never written to. The only thing this process does to the outside
    world is what tjr_desk already did — send a Telegram message — plus
    writing JSON under cockpit/state.

USAGE
    python3 -m cockpit.desk_recorder --dry-run   # print alerts, still record
    python3 -m cockpit.desk_recorder --once      # one pass, then exit
    python3 -m cockpit.desk_recorder             # watch, and send
"""

from __future__ import annotations

import datetime as dt
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tjr_desk                                                # noqa: E402
from cockpit import store                                      # noqa: E402


def jsonable(x):
    """Signals carry pandas Timestamps and numpy numbers. They are turned
    into plain strings and floats HERE rather than at the point of writing,
    so that a signal which cannot be serialised is caught immediately
    instead of leaving a hole in the journal."""
    import numpy as np
    import pandas as pd
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, (pd.Timestamp, dt.datetime, dt.date)):
        return str(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


def kind_of(title: str) -> str:
    """Which of the three messages this is. The panel shows the ENTRY as the
    live signal and the others as history, so they must be told apart."""
    t = (title or "").lower()
    if "half off" in t or "move the stop" in t:
        return "first_target"
    if "close it" in t:
        return "close"
    if "stopped out" in t:
        return "stopped"
    return "entry"


class RecordingDesk(tjr_desk.Desk):
    """Everything tjr_desk.Desk does, written down as it happens."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        # THE DESK'S MEMORY OF WHAT IS OPEN LIVES IN MEMORY, so a restart
        # empties it. That is tjr_desk's design and not ours to change here,
        # but it means the panel's OPEN list can be missing a trade he is
        # genuinely still in — and an empty list reading as "you are flat" is
        # exactly the quiet wrongness we are trying to rule out. So the start
        # time is recorded, and the service compares it to when the last
        # alert fired: anything that fired before this process started cannot
        # be in the list, and the panel says so.
        self.started_at = time.time()

    def _send_entries(self, m, sigs) -> None:
        # The entry is recorded with the signal dictionaries AND the exact
        # text that went out AND the balance the size was worked out from.
        # All three, because the panel re-renders from the signals and then
        # checks its own numbers against the text — and it cannot do that
        # check without the balance that was actually used.
        import pandas as pd
        import tjr_alerts
        when = max(pd.Timestamp(s["fired_at"]) for s in sigs).to_pydatetime()
        upq = {s["symbol"]: s.get("usd_per_quote", 1.0) for s in sigs}
        title, msg = tjr_alerts.entry_message(sigs, self.account, upq, when)
        notes = [s["venue_note"] for s in sigs if s.get("venue_note")]
        if notes:
            msg += "\n\nNote: " + "; ".join(sorted(set(notes)))

        store.record_signal({
            "kind": "entry",
            "market": m.name,
            "title": title,
            "message": msg,
            "fired_at": str(when),
            "account_used": float(self.account),
            "usd_per_quote": {k: float(v) for k, v in upq.items()},
            "signals": [jsonable(s) for s in sigs],
        })

        self._push(title, msg, _already_recorded=True)
        for s in sigs:
            self.open_trades[(m.name, s["symbol"])] = {"sig": s,
                                                       "half_off": False}

    def _push(self, title: str, message: str, _already_recorded=False) -> None:
        if not _already_recorded:
            store.record_signal({"kind": kind_of(title), "title": title,
                                 "message": message,
                                 "fired_at": str(dt.datetime.now())})
        super()._push(title, message)

    # ------------------------------------------------------------ a pass
    def once(self, now=None) -> dict:
        """One sweep of every market, with the balance re-read first and what
        actually happened written down after.

        THIS DOES NOT CALL tjr_desk's OWN once(), AND THE REASON MATTERS.
        That one catches a market's exception, prints a line to the terminal
        and moves on — which is right for a process he is not watching, but
        it means a market that could not be reached at all is indistinguishable
        from a market where nothing set up. Alpaca resets a connection often
        enough that this is not hypothetical.

        On a panel, those two must never look the same. So the loop is done
        here, per market, and each market's outcome — checked, or failed and
        why — goes into the heartbeat. The panel then says "crypto could not
        be checked" instead of quietly implying it was.
        """
        self.account = store.account_or_zero()
        if self.account <= 0:
            print("  BALANCE UNKNOWN — alerts will go out with no size on "
                  "them. Text the bot:  balance 105000")
        out, status = {}, []
        for m in self.markets:
            try:
                out[m.name] = self.poll_market(m, now)
                status.append({"name": m.name, "ok": True,
                               "setups": len(out[m.name])})
            except Exception as e:
                out[m.name] = []
                status.append({"name": m.name, "ok": False,
                               "why": f"{type(e).__name__}: {str(e)[:120]}"})
                print(f"  {m.name}: {str(e)[:160]}")
        self._record_state(status)
        return out

    def _record_state(self, status: list | None = None) -> None:
        rows = []
        for (market, symbol), t in self.open_trades.items():
            sig = t["sig"]
            rows.append({
                "market": market,
                "symbol": symbol,
                "side": "BUY" if sig["direction"] > 0 else "SELL",
                "entry": float(sig["reference_price"]),
                "stop": float(sig["stop"]),
                "targets": [float(x) for x in (sig.get("targets") or [])],
                "half_off": bool(t["half_off"]),
                "opened_at": str(sig.get("fired_at") or ""),
            })
        store.record_open(rows, started_at=self.started_at)
        store.beat(status if status is not None
                   else [{"name": m.name, "ok": True} for m in self.markets],
                   note="dry run — nothing was sent to the phone"
                        if self.dry_run else "")

    def watch(self) -> None:
        print("watching " + ", ".join(m.name for m in self.markets) +
              ". Alerts go to Telegram and are mirrored to the cockpit panel. "
              "NO ORDERS ARE PLACED BY THIS PROCESS.")
        while True:
            self.once()
            time.sleep(max(2.0, 62.0 - (time.time() % 60.0)))


def main(argv):
    desk = RecordingDesk(account=store.account_or_zero(),
                         dry_run="--dry-run" in argv)
    if "--once" in argv:
        got = desk.once()
        for k, v in got.items():
            print(f"  {k:11s} {len(v)} setup(s)")
        return
    desk.watch()


if __name__ == "__main__":
    main(sys.argv)
