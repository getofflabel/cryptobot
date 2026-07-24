"""
book_ledger.py — BOOK-AWARE POSITION ATTRIBUTION.

THE 2026-07-23 INCIDENT (why this file exists)
BloFin nets everything on one symbol into ONE exchange position. This bot
runs multiple independent "books" against BTC-USDT on the same account:
THE RIDE (step5_paper_trade.decide_and_trade, trend long/flat), THE STRIKES
(tactical.py, BTC slot), and THE SHORTS LAB (shorts_lab.py). Each book keeps
its OWN record of what it thinks it owns in state — but before this file
existed, the ride read the RAW exchange net position and treated the whole
thing as its own. When the shorts lab opened a -69.6 ct short, the ride's
champion signal was 0 (wants flat), saw net -69.6, and concluded "I am
short 69.6 contracts I don't want" — so it kept BUYING it back in 5-ct
post-only clips (execute_maker_or_chase's clip loop), fighting the lab's
own position. On top of that, the ride's exit/cleanup path did a BLANKET
cancel of every pending TP/SL bracket on the symbol, which stripped the
lab's protective stop out from under a live position. The owner watched
mystery buy-limits appear on a position he didn't open, and protection
vanish from one he did.

THE FIX
Every book's cycle must reason about its OWN SLICE of the net position,
never the raw net. The functions below are the single, shared accounting
layer every book (ride, tact, lab, and any future book) attributes through,
so there is exactly one way to compute "what do I actually hold" and it is
structurally impossible for one book to mistake another book's position for
its own ever again.

Pure functions only — no I/O, no exchange calls, no side effects. That
makes this file trivially unit-testable (see test_book_attribution.py) and
safe to import from every book without creating import cycles.
"""

from __future__ import annotations


def recorded_book_positions(state: dict) -> dict:
    """Read every book's own record of its position from `state`, signed:
    longs positive, shorts negative, missing/None book = 0.

    Books covered (all trade the SAME symbol, BTC-USDT, and therefore share
    one exchange net):
      "ride"       state["open_trade"]                       — always long
      "tact"       state["tactical"]["open_trade"]            — always long
      "lab"        state["shorts_lab"]["open_trade"]           — signed by
                                                                  "direction"
      "apprentice" state["apprentice"]["open_trade"]           — signed by
                                                                  "direction"
      "newsdesk"   state["newsdesk"]["open_trade"]             — signed by
                                                                  "direction"
                                                                  (round 45B,
                                                                  news_book.py
                                                                  promoted to
                                                                  live demo
                                                                  orders)

    state["tactical_eth"] is EXCLUDED on purpose — it trades ETH-USDT, a
    different symbol with its own separate exchange net. Mixing it in here
    would silently corrupt the BTC attribution.
    """
    out = {"ride": 0.0, "tact": 0.0, "lab": 0.0, "apprentice": 0.0,
           "newsdesk": 0.0}

    ride = state.get("open_trade")
    if ride:
        out["ride"] = float(ride.get("contracts", 0) or 0)   # always long

    tact = state.get("tactical", {}).get("open_trade")
    if tact:
        out["tact"] = float(tact.get("contracts", 0) or 0)   # always long

    lab = state.get("shorts_lab", {}).get("open_trade")
    if lab:
        direction = lab.get("direction", -1) or -1
        sign = 1 if direction > 0 else -1
        out["lab"] = sign * abs(float(lab.get("contracts", 0) or 0))

    appr = state.get("apprentice", {}).get("open_trade")
    if appr:
        direction = appr.get("direction", 0) or 0
        sign = 1 if direction > 0 else (-1 if direction < 0 else 0)
        out["apprentice"] = sign * abs(float(appr.get("contracts", 0) or 0))

    news = state.get("newsdesk", {}).get("open_trade")
    if news:
        direction = news.get("direction", 0) or 0
        sign = 1 if direction > 0 else (-1 if direction < 0 else 0)
        out["newsdesk"] = sign * abs(float(news.get("contracts", 0) or 0))

    return out


def attributed_position(net: float, state: dict, book: str) -> float:
    """The slice of the exchange net position that belongs to `book`.

    net minus the SUM of every OTHER book's recorded position. This is what
    a book should compare its own desired/held size against — NEVER the raw
    net, which includes whatever every other book is doing.
    """
    recorded = recorded_book_positions(state)
    if book not in recorded:
        raise ValueError(f"unknown book {book!r}; expected one of "
                         f"{sorted(recorded)}")
    others = sum(v for k, v in recorded.items() if k != book)
    return net - others


def unexplained_position(net: float, state: dict) -> float:
    """What's left of the exchange net once every book's own record is
    subtracted out — the slice NOBODY claims. In a healthy system this is
    always ~0. A nonzero value means either a book's bracket fired and
    hasn't been reconciled yet, or something opened the position by hand
    (or a bug placed an order outside all the book paths)."""
    recorded = recorded_book_positions(state)
    return net - sum(recorded.values())
