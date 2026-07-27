"""
cockpit/store.py — the ONE place a number lives, and it never lives without
a timestamp next to it.

WHY THIS FILE EXISTS AT ALL
    Wallace places every trade by hand. The moment he skips a signal, or
    types a different size than the one we sent, our record and his real
    account stop agreeing. And the position size in every future alert is
    worked out FROM the account balance — so a balance that is quietly wrong
    makes every size after it quietly wrong too.

    So there is exactly one rule in this file and it is not negotiable:

        NEVER INVENT A BALANCE.

    There is no default, no fallback constant, no last-known-value dressed
    up as current. `account()` returns None when we do not know, and
    everything downstream is expected to say "we do not know" and refuse to
    state a size, which is what tjr_alerts already does when it is handed a
    zero.

TWO ROUTES IN, ONE NUMBER OUT
    tradingview   read off his TradingView trading panel, read-only, by
                  cockpit/tv_balance.py
    telegram      he texts the bot `balance 105000`, handled by
                  cockpit/telegram_balance.py

    Both write here with the time they were taken. `account()` hands back
    whichever is FRESHER and says which one it was and how old it is. It
    never averages them and never prefers one on principle — the freshest
    reading is the one closest to the truth.

WHAT ELSE LIVES HERE
    the signals the desk has actually sent, the trades it believes are still
    open, and a heartbeat saying when the desk recorder last drew breath.
    All three are written by cockpit/desk_recorder.py and all three carry a
    timestamp, because a panel that shows an hour-old position list as if it
    were current is worse than a panel showing nothing.

SAFETY
    This file reads and writes JSON on disk. It imports nothing that can
    place an order and holds no credentials.
"""

from __future__ import annotations

import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state")

ACCOUNT_PATH = os.path.join(STATE, "account.json")
SIGNALS_PATH = os.path.join(STATE, "signals.jsonl")
OPEN_PATH = os.path.join(STATE, "open.json")
HEARTBEAT_PATH = os.path.join(STATE, "heartbeat.json")

# A balance older than this is still shown — hiding it would be its own kind
# of lie — but it is shown WITH the words "this is a day old" on its face.
STALE_BALANCE_SECONDS = 24 * 60 * 60

ROUTES = ("tradingview", "telegram")


# --------------------------------------------------------------- plumbing
def _ensure() -> None:
    os.makedirs(STATE, exist_ok=True)


def _read(path: str, default):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _write(path: str, obj) -> None:
    """Write through a temporary file and rename.

    The service reads these files roughly once a second while the recorder
    writes them. A half-written file read at the wrong moment would surface
    as an unexplained blank in the panel, which is the exact failure mode
    this whole cockpit exists to make impossible.
    """
    _ensure()
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(obj, fh, indent=2)
    os.replace(tmp, path)


# ---------------------------------------------------------------- balance
def record_balance(route: str, equity: float, detail: str = "") -> dict:
    """File a reading from one of the two routes. Refuses anything that is
    not a positive number, because a zero balance sitting in this file would
    read downstream as "we know it, and it is nothing"."""
    if route not in ROUTES:
        raise ValueError(f"unknown route {route!r}; expected one of {ROUTES}")
    equity = float(equity)
    if equity <= 0 or equity != equity:          # NaN fails the second test
        raise ValueError(f"refusing to store {equity!r} as a balance")
    book = _read(ACCOUNT_PATH, {})
    book[route] = {"equity": equity, "as_of": time.time(), "detail": detail}
    _write(ACCOUNT_PATH, book)
    return book[route]


def account() -> dict | None:
    """The freshest balance we actually have, or None.

    None means we do not know. It does not mean zero, and no caller may turn
    it into a zero on the way past.
    """
    book = _read(ACCOUNT_PATH, {})
    have = [(r, v) for r, v in book.items()
            if isinstance(v, dict) and v.get("equity")]
    if not have:
        return None
    route, v = max(have, key=lambda rv: rv[1].get("as_of") or 0)
    age = time.time() - float(v["as_of"])
    other = {r: {"equity": x["equity"], "as_of": x["as_of"]}
             for r, x in book.items() if r != route and isinstance(x, dict)}
    return {
        "equity": float(v["equity"]),
        "as_of": float(v["as_of"]),
        "age_seconds": age,
        "route": route,
        "route_words": ("read off his TradingView trading panel"
                        if route == "tradingview" else
                        "he texted it to the bot"),
        "detail": v.get("detail", ""),
        "stale": age > STALE_BALANCE_SECONDS,
        "also_known": other,
    }


def account_or_zero() -> float:
    """For the one caller that has to hand a number to the sizing code.

    Zero is deliberate and it is not a stand-in for the balance: tjr_alerts'
    position_size answers `ok: False` on a zero account, and the alert then
    prints "COULD NOT BE WORKED OUT — do not take this one" instead of a
    size. Not knowing therefore produces a refusal, never a wrong number.
    """
    a = account()
    return float(a["equity"]) if a else 0.0


# ---------------------------------------------------------------- signals
def record_signal(row: dict) -> None:
    """Append one thing the desk actually pushed to his phone."""
    _ensure()
    row = dict(row, recorded_at=time.time())
    with open(SIGNALS_PATH, "a") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


def signals(limit: int = 40) -> list:
    """The most recent pushes, newest last. Missing file is an empty list —
    which the service reports as "nothing recorded", never as "no signal"."""
    try:
        with open(SIGNALS_PATH) as fh:
            lines = fh.readlines()[-limit:]
    except (FileNotFoundError, OSError):
        return []
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out


def latest_entry() -> dict | None:
    """The most recent ENTRY push — the one he would be placing right now.
    Manage-and-close pushes are recorded too but they are not a trade to
    enter, so they are not returned here."""
    for row in reversed(signals(200)):
        if row.get("kind") == "entry":
            return row
    return None


# --------------------------------------------- open trades and heartbeat
def record_open(trades: list, started_at: float | None = None) -> None:
    """What the desk believes is open, and WHEN THE DESK STARTED.

    The second one matters as much as the first. The desk keeps its open
    trades in memory, so a restart wipes them — and an empty list that reads
    as "you are flat" when he is actually holding something is the worst
    thing this panel could imply. Recording the start time lets the service
    notice that an alert predates the process and say the list may be
    incomplete.
    """
    _write(OPEN_PATH, {"as_of": time.time(), "trades": trades,
                       "desk_started_at": started_at})


def open_trades() -> dict:
    return _read(OPEN_PATH, {"as_of": None, "trades": []})


def beat(markets: list, note: str = "") -> None:
    """The desk recorder saying it is alive. Without this the panel cannot
    tell "nothing is setting up" from "the thing that watches died an hour
    ago", and those two must never look the same."""
    _write(HEARTBEAT_PATH, {"as_of": time.time(), "markets": list(markets),
                            "note": note})


def heartbeat() -> dict | None:
    hb = _read(HEARTBEAT_PATH, None)
    if not hb or not hb.get("as_of"):
        return None
    hb["age_seconds"] = time.time() - float(hb["as_of"])
    return hb
