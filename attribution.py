"""
attribution.py — THE BOT MAY ONLY EVER TOUCH A POSITION IT OPENED ITSELF.

WHY THIS FILE EXISTS (2026-07-25)

Wallace trades the BloFin demo account personally. Earlier today a bot in
this project closed a trade HE had opened. That is the worst class of bug
this system can have: not a losing trade, but the machine reaching into a
human's position and taking it off him. It has to be impossible, not
unlikely.

THE RULE, in one sentence:
    Anything the bot cannot POSITIVELY prove it opened is his, and the bot
    does not reduce it, does not close it, does not put a stop on it, does
    not count it toward its own exposure, and does not "clean it up".

The three words that decide every hard case are AMBIGUITY RESOLVES TO HANDS
OFF. A read that failed, a page of order history that does not reach far
enough back, a position that is part ours and part his, an order with no
tag, an order with somebody else's tag — every one of those is HIS. There
is no branch in this file where "probably ours" becomes "ours".

HOW THE PROOF WORKS

Every order this codebase places carries a clientOrderId built by
blofin_private.make_client_order_id(), which always begins "CBOT_". The
exchange stores that string and hands it back on
GET /api/v1/trade/orders-history. Wallace's own orders, placed by hand in
the BloFin app, carry an EMPTY clientOrderId — verified on 100% of the real
rows on the account (see BLOFIN_API_REFERENCE.md).

So proving a position is ours means proving that EVERY order that built it
carries our prefix. Not "one of them did". Every one. A position that we
added to and he added to is his, because we cannot take our half off
without moving his.

THE CUTOVER DATE IS PART OF THE PROOF
Before blofin_private.TAGGING_CUTOVER_UTC nothing was tagged, so nothing
from before it can be proven ours. Positions opened before that moment are
therefore his BY DEFINITION, and this file says so in exactly those words
rather than falling through to some softer test.

WHAT IS IN HERE AND WHAT IS NOT
The verdict logic is PURE — it takes the exchange's own rows in and returns
a verdict out, with no network, no clock of its own, and no side effects.
That is what makes it testable to the point of boredom (test_attribution.py).
The one function that does talk to the exchange, attribute_symbol(), is a
thin wrapper whose entire job is to turn any failure at all into a
"not ours" verdict.

NOTHING IN THIS FILE PLACES, CANCELS OR MODIFIES AN ORDER.
"""

from __future__ import annotations

from datetime import datetime, timezone

from blofin_private import BOOK_TAGS, CLIENT_TAG_PREFIX, TAGGING_CUTOVER_UTC

# The prefix every order we place carries, and nothing he places ever does.
OUR_PREFIX = f"{CLIENT_TAG_PREFIX}_"

# How far BEFORE a position's own createTime we look for the orders that
# built it. The exchange stamps the ORDER a few milliseconds before the
# POSITION it creates (measured live: 39 ms on the real ETH row), and a
# position that was added to has a createTime from its first fill while
# later adds land after it. Sixty seconds is generous for the first case
# and irrelevant to the second, because the window's far end is open: we
# look at everything from window start to now.
OPENING_WINDOW_MS = 60_000


# ================================================================== VERDICT
class Verdict:
    """What the bot is allowed to do with one position, and why.

    `ours` is the only field any caller should branch on. Everything else
    exists so a refusal can be explained in a message to Wallace without
    anybody having to read this file to understand it.
    """

    __slots__ = ("ours", "reason", "tag", "symbol", "evidence")

    def __init__(self, ours: bool, reason: str, symbol: str = "",
                 tag: str | None = None, evidence: dict | None = None):
        self.ours = bool(ours)
        self.reason = reason
        self.symbol = symbol
        self.tag = tag
        self.evidence = evidence or {}

    def __bool__(self) -> bool:
        return self.ours

    def to_dict(self) -> dict:
        return {"ours": self.ours, "reason": self.reason, "symbol": self.symbol,
                "tag": self.tag, "evidence": self.evidence}

    def __repr__(self) -> str:
        return (f"<Verdict {self.symbol} "
                f"{'OURS' if self.ours else 'HIS'}: {self.reason}>")


def _his(reason: str, symbol: str = "", evidence: dict | None = None) -> Verdict:
    return Verdict(False, reason, symbol, None, evidence)


# ============================================================ TAG READING
def is_ours_coid(client_order_id) -> bool:
    """True only for a clientOrderId this codebase built. An empty string,
    a None, a number, a foreign string — all False, all his."""
    if not isinstance(client_order_id, str):
        return False
    return client_order_id.startswith(OUR_PREFIX)


def tag_of(client_order_id) -> str | None:
    """Which part of the bot placed it: "CBOT_dp_1785...006" -> "dp".
    None when the id is not ours at all."""
    if not is_ours_coid(client_order_id):
        return None
    parts = client_order_id.split("_")
    return parts[1] if len(parts) >= 3 and parts[1] else None


def book_for_tag(tag: str | None) -> str | None:
    """The readable name behind a short tag, or None if we do not know it.
    An unknown tag is NOT treated as ours anywhere — see the note in
    attribute_position()."""
    if not tag:
        return None
    for name, short in BOOK_TAGS.items():
        if short == tag:
            return name
    return None


# ========================================================== ROW READING
def _ms(row: dict, key: str) -> int | None:
    try:
        v = row.get(key)
        return int(float(v)) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _f(row: dict, key: str, default: float = 0.0) -> float:
    try:
        v = row.get(key)
        return float(v) if v not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _filled(row: dict) -> bool:
    """An order that actually moved the position. A cancelled or unfilled
    order never built anything, so it is not evidence either way."""
    return _f(row, "filledSize") > 0


def _is_reduce(row: dict) -> bool:
    return str(row.get("reduceOnly", "")).lower() == "true"


# ============================================================ THE VERDICT
def attribute_position(position: dict | None, orders: list | None,
                       cutover: datetime = TAGGING_CUTOVER_UTC,
                       window_ms: int = OPENING_WINDOW_MS,
                       history_complete: bool | None = None,
                       page_limit: int | None = None) -> Verdict:
    """Decide whether the bot opened this position. PURE — rows in, verdict
    out.

    `position`  one row from GET /api/v1/account/positions, or None.
    `orders`    the rows from GET /api/v1/trade/orders-history for that same
                symbol. BloFin's clientOrderId= and orderId= query params do
                NOT filter server-side (verified live), so this is the whole
                recent page and the filtering happens here.
    `history_complete`
                pass False when the caller knows the page it fetched may not
                reach back to the position's own start. None means "work it
                out", which is done below.
    `page_limit`
                how many rows the caller ASKED the exchange for. If fewer
                came back, that page is the entire order history for the
                symbol and there is nothing older to miss — which is the
                normal case on a symbol the bot has just started trading.

    Every early return below is a refusal. The single path that ends in
    ours=True is at the bottom and it requires all of: a position that
    exists, opened after tagging began, with at least one filled opening
    order visible, and EVERY filled order touching the symbol in that window
    carrying our prefix.
    """
    symbol = str((position or {}).get("instId") or "")

    # ---- 1. nothing to act on -------------------------------------------
    if not position:
        return _his("there is no position on this symbol", symbol)
    size = _f(position, "positions")
    if size == 0:
        return _his("the position is flat, so there is nothing to act on",
                    symbol)

    # ---- 2. before tagging existed, nothing can be proven ---------------
    created = _ms(position, "createTime")
    if created is None:
        return _his("the exchange did not tell us when this position was "
                    "opened, so it cannot be attributed and it is his",
                    symbol, {"size": size})
    created_dt = datetime.fromtimestamp(created / 1000.0, timezone.utc)
    if created_dt < cutover:
        return _his(
            f"this position was opened at {created_dt:%Y-%m-%d %H:%M UTC}, "
            f"before the bot started tagging its orders at "
            f"{cutover:%Y-%m-%d %H:%M UTC}. Nothing from before that moment "
            f"can be proven to be the bot's, so it is his.",
            symbol, {"size": size, "opened_utc": created_dt.isoformat()})

    # ---- 3. we need the order history that built it ---------------------
    rows = list(orders or [])
    if not rows:
        return _his("we could not read any order history for this symbol, so "
                    "there is no proof the bot opened it and it is his",
                    symbol, {"size": size})

    window_start = created - int(window_ms)
    stamps = [s for s in (_ms(r, "createTime") for r in rows) if s is not None]
    if not stamps:
        return _his("the order history carries no usable timestamps, so the "
                    "position cannot be attributed and it is his", symbol,
                    {"size": size})

    # Does the page we were handed actually reach back far enough to contain
    # the orders that opened this position? Two ways it can:
    #   - its oldest row is older than the window we need, so we can see past
    #     the beginning of the position, or
    #   - fewer rows came back than were asked for, which means this IS the
    #     whole order history for the symbol and there is nothing older.
    # Anything else means the opening order could be off the end of the page,
    # and a record we cannot see the start of proves nothing. So: his.
    reaches_back = min(stamps) <= window_start
    whole_history = page_limit is not None and len(rows) < int(page_limit)
    if history_complete is False or (history_complete is None
                                     and not (reaches_back or whole_history)):
        return _his(
            "the order history we can see does not reach back to when this "
            "position was opened, so the order that opened it is not "
            "visible. An unverifiable position is his.",
            symbol, {"size": size, "oldest_row_ms": min(stamps),
                     "needed_back_to_ms": window_start})

    # ---- 4. every order that touched it in that window must be ours -----
    in_window = [r for r in rows
                 if (_ms(r, "createTime") or 0) >= window_start and _filled(r)]
    if not in_window:
        return _his("no filled order in the order history lines up with when "
                    "this position was opened, so it is not the bot's",
                    symbol, {"size": size})

    opens = [r for r in in_window if not _is_reduce(r)]
    if not opens:
        return _his("the order history shows no order that OPENED this "
                    "position, only orders that shrink one. Without the "
                    "opening order there is no proof, so it is his",
                    symbol, {"size": size})

    untagged = [r for r in in_window if not is_ours_coid(r.get("clientOrderId"))]
    if untagged:
        return _his(
            f"{len(untagged)} of the {len(in_window)} filled orders on this "
            f"symbol since it was opened carry no tag of ours, which means a "
            f"hand-placed order is part of this position. The bot does not "
            f"touch it.",
            symbol, {"size": size, "untagged_order_ids":
                     [str(r.get("orderId")) for r in untagged][:10]})

    # An order carrying our prefix but a tag we do not recognise is still
    # ambiguous — it means a version of this codebase we are not running
    # placed it. Same answer as everything else ambiguous: his.
    tags = {tag_of(r.get("clientOrderId")) for r in in_window}
    unknown = {t for t in tags if book_for_tag(t) is None}
    if unknown:
        return _his(
            f"orders on this position carry tag(s) {sorted(unknown)!r} that "
            f"this build does not know, so it cannot be sure which part of "
            f"the bot owns it. Hands off.",
            symbol, {"size": size, "tags": sorted(t for t in tags if t)})

    # The tagged orders have to account for the WHOLE position. If our own
    # fills add up to less than what is sitting there, the difference is his
    # and we cannot take our share off without moving his.
    ours_net = sum((_f(r, "filledSize") if str(r.get("side", "")).lower() == "buy"
                    else -_f(r, "filledSize")) for r in in_window)
    if abs(ours_net - size) > max(abs(size) * 1e-6, 1e-9):
        return _his(
            f"the bot's own tagged orders add up to {ours_net:+,.4f} contracts "
            f"but the exchange shows {size:+,.4f}. The difference is not ours, "
            f"so none of it is touched.",
            symbol, {"size": size, "our_tagged_net": ours_net})

    tag = sorted(t for t in tags if t)[0] if any(tags) else None
    return Verdict(
        True,
        f"every filled order that built this position carries the bot's own "
        f"tag ({book_for_tag(tag) or tag}), and they account for all "
        f"{size:+,.4f} contracts of it",
        symbol, tag,
        {"size": size, "orders_checked": len(in_window),
         "opened_utc": created_dt.isoformat()})


# =================================================== THE ONE NETWORK CALL
def attribute_symbol(client, symbol: str, history_limit: int = 100,
                     cutover: datetime = TAGGING_CUTOVER_UTC) -> Verdict:
    """The verdict for one symbol, reading the exchange for it.

    ANY failure at all — a network error, a throttle, an HTML page instead of
    JSON, a malformed row — comes back as "his". A guard that opens when it
    cannot see is not a guard.
    """
    try:
        rows = client.positions(symbol) or []
    except Exception as e:                                   # noqa: BLE001
        return _his(f"we could not read the position from the exchange "
                    f"({str(e)[:120]}), so nothing is touched", symbol)

    live = None
    for r in rows:
        try:
            if float(r.get("positions") or 0) != 0:
                live = r
                break
        except (TypeError, ValueError):
            continue
    if live is None:
        return _his("there is no open position on this symbol", symbol)

    try:
        orders = client.orders_history(symbol, limit=history_limit) or []
    except Exception as e:                                   # noqa: BLE001
        return _his(f"we could not read the order history from the exchange "
                    f"({str(e)[:120]}), so the position cannot be attributed "
                    f"and is treated as his", symbol)

    return attribute_position(live, orders, cutover=cutover,
                              page_limit=history_limit)


def survey(client, symbols=None, history_limit: int = 100) -> dict:
    """Read-only. Every open position on the account with a verdict beside
    it, so a report can say plainly what the bot considers his. Places
    nothing, cancels nothing, closes nothing."""
    try:
        rows = [r for r in (client.positions() or [])
                if float(r.get("positions") or 0) != 0]
    except Exception as e:                                   # noqa: BLE001
        return {"error": str(e)[:200], "positions": []}

    out = []
    for r in rows:
        sym = str(r.get("instId") or "")
        if symbols and sym not in symbols:
            continue
        try:
            orders = client.orders_history(sym, limit=history_limit) or []
        except Exception as e:                               # noqa: BLE001
            out.append(_his(f"order history unreadable ({str(e)[:80]})",
                            sym, {"size": _f(r, "positions")}).to_dict())
            continue
        out.append(attribute_position(r, orders,
                                      page_limit=history_limit).to_dict())
    return {"positions": out,
            "ours": [p for p in out if p["ours"]],
            "his": [p for p in out if not p["ours"]]}


if __name__ == "__main__":
    import json as _json

    from blofin_private import BlofinDemoPrivate, load_env

    env = load_env()
    cli = BlofinDemoPrivate(env["BLOFIN_DEMO_API_KEY"],
                            env["BLOFIN_DEMO_API_SECRET"],
                            env["BLOFIN_DEMO_PASSPHRASE"])
    print(_json.dumps(survey(cli), indent=2))
