"""
test_attribution.py — THE TEST THAT KEEPS THE BOT OFF HIS TRADES.

Run:  python3 test_attribution.py

NO NETWORK. Every exchange call is a fake that records what it was asked to
do, so a test can assert the strongest thing there is to assert: that ZERO
orders were placed.

WHAT IS BEING PROTECTED

On 2026-07-25 a bot in this project closed a position Wallace had opened by
hand on the BloFin demo account he trades personally. The rule that came out
of it is: THE BOT MAY ONLY EVER TOUCH A POSITION IT OPENED ITSELF, and
anything it cannot positively attribute to itself is his.

THE TEST THAT MATTERS MOST is test_no_reduce_path_without_attribution(). It
does not test one code path — it enumerates EVERY public method on
BlofinVenue, calls all of them against a position the bot did not open, and
fails if a single exchange order, bracket, or cancel came out the other
side. A future method added to that class that reduces a position without
asking attribution first is caught by this test the moment it exists,
because the test finds methods by reflection rather than by a list somebody
has to remember to update.

Underneath it, test_sealed_client_*() proves the third layer: the reducing
calls on the exchange client raise unless the guard opened the door, so even
code that never heard of the guard cannot get past it.
"""

from __future__ import annotations

import inspect
import sys
import traceback
from datetime import timedelta

import attribution
import venue as venue_mod
from blofin_private import TAGGING_CUTOVER_UTC

SYMBOL = "BTC/USD"
INST = "BTC-USDT"

AFTER = int((TAGGING_CUTOVER_UTC + timedelta(hours=2)).timestamp() * 1000)
BEFORE = int((TAGGING_CUTOVER_UTC - timedelta(hours=2)).timestamp() * 1000)


# ===========================================================  THE FAKES
class FakeClient:
    """Stands in for BlofinDemoPrivate. Never makes an HTTP call. Records
    every mutating call so a test can assert none happened."""

    def __init__(self, position=None, orders=None, pending=None,
                 history_raises=False):
        self._position = position
        self._orders = orders if orders is not None else []
        self._pending = pending or []
        self.history_raises = history_raises
        # what a test asserts on
        self.placed: list = []
        self.brackets: list = []
        self.cancels: list = []
        self.leverage_calls: list = []

    # -- reads -------------------------------------------------------------
    def positions(self, symbol=None):
        if self._position is None:
            return []
        if symbol and str(self._position.get("instId")) != symbol:
            return []
        return [self._position]

    def orders_history(self, symbol, limit=None):
        if self.history_raises:
            raise RuntimeError("throttled")
        return list(self._orders)

    def pending_tpsl(self, symbol):
        return list(self._pending)

    def instruments(self, inst_type="SWAP"):
        return [{"instId": INST, "contractValue": "0.001", "lotSize": "0.1",
                 "tickSize": "0.1", "maxLeverage": "150", "state": "live"},
                {"instId": "ETH-USDT", "contractValue": "0.01", "lotSize": "0.1",
                 "tickSize": "0.01", "maxLeverage": "150", "state": "live"}]

    def account_balance(self):
        return {"totalEquity": "100000"}

    def futures_balance(self):
        return {"balance": "100000", "available": "100000", "frozen": "0"}

    # -- writes ------------------------------------------------------------
    def ensure_leverage(self, symbol, leverage, margin_mode=None):
        self.leverage_calls.append((symbol, leverage, margin_mode))
        return True

    def market_order(self, symbol, side, contracts, reduce_only=False,
                     margin_mode=None, client_order_id=None, lot_size=None):
        self.placed.append({"symbol": symbol, "side": side,
                            "contracts": contracts, "reduce_only": reduce_only,
                            "client_order_id": client_order_id})
        return "order-1"

    def post_only_order(self, symbol, side, contracts, price,
                        reduce_only=False, client_order_id=None):
        self.placed.append({"symbol": symbol, "side": side,
                            "contracts": contracts, "reduce_only": reduce_only,
                            "client_order_id": client_order_id})
        return "order-2"

    def place_tpsl(self, symbol, position_side_close, contracts, tp, sl,
                   margin_mode=None, client_order_id=None, lot_size=None,
                   tick_size=None):
        self.brackets.append({"symbol": symbol, "sl": sl,
                              "client_order_id": client_order_id})
        return "tpsl-1"

    def cancel_tpsl(self, symbol, tpsl_id):
        self.cancels.append({"symbol": symbol, "tpsl_id": tpsl_id})

    def cancel_order(self, symbol, order_id):
        self.cancels.append({"symbol": symbol, "order_id": order_id})

    # -- the whole point ---------------------------------------------------
    def touched_anything(self) -> bool:
        return bool(self.placed or self.brackets or self.cancels)


def position_row(size=10.0, created=None, inst=INST):
    return {"instId": inst, "positions": str(size), "averagePrice": "60000",
            "markPrice": "60100", "unrealizedPnl": "10",
            "unrealizedPnlRatio": "0.05", "liquidationPrice": "50000",
            "leverage": "20", "marginMode": "isolated",
            "createTime": str(created if created is not None else AFTER)}


def order_row(coid="", size=10.0, side="buy", created=None, reduce=False,
              state="filled"):
    return {"orderId": "o1", "clientOrderId": coid, "side": side,
            "size": str(size), "filledSize": str(size if state == "filled" else 0),
            "state": state, "createTime": str(created if created is not None
                                              else AFTER - 40),
            "reduceOnly": "true" if reduce else "false", "orderType": "market"}


OURS_COID = "CBOT_tjc_1785018742491000001"


def ours_client(size=10.0):
    """A position the bot genuinely opened, tagged all the way through."""
    return FakeClient(position=position_row(size),
                      orders=[order_row(OURS_COID, size)])


def his_client(size=10.0):
    """A position Wallace opened by hand — no tag on the opening order."""
    return FakeClient(position=position_row(size), orders=[order_row("", size)])


def build(client, **kw):
    return venue_mod.BlofinVenue(client=client, **kw)


# =====================================================  THE PURE VERDICT
def verdict(position, orders, **kw):
    """The pure verdict, told how big a page was asked for. Every fixture here
    is a SHORT page, which is the exchange saying "that is all there is"."""
    kw.setdefault("page_limit", 100)
    return attribution.attribute_position(position, orders, **kw)


def test_untagged_open_is_his():
    v = verdict(position_row(), [order_row("", 10.0)])
    assert not v.ours, v.reason
    assert "no tag" in v.reason


def test_tagged_open_is_ours():
    v = verdict(position_row(), [order_row(OURS_COID, 10.0)])
    assert v.ours, v.reason
    assert v.tag == "tjc"


def test_before_the_cutover_is_his_by_definition():
    """Nothing was tagged before the cutover, so nothing from before it can
    be proven ours — however innocent the order history looks."""
    v = verdict(
        position_row(created=BEFORE),
        [order_row(OURS_COID, 10.0, created=BEFORE - 40)])
    assert not v.ours, v.reason
    assert "before the bot started tagging" in v.reason


def test_mixed_position_is_his():
    """Half opened by the bot, half by him. There is one position on this
    exchange, so the bot cannot take its half off without moving his."""
    v = verdict(
        position_row(size=20.0),
        [order_row(OURS_COID, 10.0), order_row("", 10.0)])
    assert not v.ours, v.reason


def test_our_orders_not_adding_up_is_his():
    """Tagged orders account for 10 contracts, the exchange shows 20. The
    extra 10 came from somewhere we cannot see."""
    v = verdict(position_row(size=20.0), [order_row(OURS_COID, 10.0)])
    assert not v.ours, v.reason
    assert "add up to" in v.reason


def test_unknown_tag_is_his():
    """Our prefix but a tag this build does not know: a different version of
    this codebase placed it. Ambiguity resolves to hands off."""
    v = verdict(position_row(), [order_row("CBOT_zz_1785018742491000001", 10.0)])
    assert not v.ours, v.reason
    assert "does not know" in v.reason


def test_history_that_does_not_reach_back_is_his():
    """A FULL page came back (two rows asked for, two returned) and its
    oldest row is still newer than when the position was opened. The opening
    order is off the end of the page, so it is invisible, so it is his."""
    v = verdict(
        position_row(created=AFTER),
        [order_row(OURS_COID, 10.0, created=AFTER + 500_000),
         order_row(OURS_COID, 10.0, created=AFTER + 900_000)],
        page_limit=2)
    assert not v.ours, v.reason
    assert "does not reach back" in v.reason


def test_empty_history_is_his():
    assert not verdict(position_row(), []).ours


def test_no_position_is_not_ours():
    assert not verdict(None, []).ours
    assert not verdict(position_row(size=0.0), []).ours


def test_unreadable_history_is_his():
    """A read that failed is not a read that said yes."""
    v = attribution.attribute_symbol(FakeClient(position=position_row(),
                                                history_raises=True), INST)
    assert not v.ours, v.reason
    assert "order history" in v.reason


def test_cancelled_orders_are_not_evidence():
    """An order that never filled built nothing. It must not be able to
    make a position look ours OR make one look his."""
    v = verdict(
        position_row(),
        [order_row(OURS_COID, 10.0), order_row("", 5.0, state="canceled")])
    assert v.ours, v.reason


def test_tag_reading():
    assert attribution.is_ours_coid(OURS_COID)
    assert not attribution.is_ours_coid("")
    assert not attribution.is_ours_coid(None)
    assert not attribution.is_ours_coid("cbot_tjc_1")       # case matters
    assert not attribution.is_ours_coid(12345)
    assert attribution.tag_of(OURS_COID) == "tjc"
    assert attribution.tag_of("") is None


# ==============================  THE ONE THAT MATTERS MOST  ==============
def _public_methods(cls):
    return [n for n, f in inspect.getmembers(cls, inspect.isfunction)
            if not n.startswith("_")]


# Every public method on the venue, with arguments that would make it act on
# a position if it were allowed to. Methods NOT listed here are covered by
# test_every_public_method_is_accounted_for, which fails when one appears
# that nobody has decided about — so a new reduce path cannot slip in
# unnoticed.
CALLS = {
    "market_order": ((SYMBOL, "sell", 0.01),
                     {"reference_price": 60000.0, "stop": 59500.0}),
    "close_position": ((SYMBOL,), {}),
    "place_stop": ((SYMBOL, 59000.0), {}),
    "cancel_stops": ((SYMBOL,), {}),
}
READ_ONLY = {"account", "positions", "position", "orders", "fills", "misses",
             "refusals", "foreign_positions", "open_risk", "spec",
             "venue_symbol"}


def test_every_public_method_is_accounted_for():
    """If somebody adds a public method to BlofinVenue, this test fails until
    they say whether it acts on a position. That is the point: the list below
    cannot go stale silently."""
    known = set(CALLS) | READ_ONLY
    unknown = set(_public_methods(venue_mod.BlofinVenue)) - known
    assert not unknown, (
        f"BlofinVenue grew public method(s) {sorted(unknown)} that this test "
        f"does not know about. Add them to CALLS (if they can act on a "
        f"position) or READ_ONLY, so the attribution test covers them.")


def test_no_reduce_path_without_attribution():
    """THE TEST THE WHOLE FILE IS FOR.

    Against a position the bot did NOT open, call every acting method on the
    venue. Not one exchange order, bracket, or cancel may come out. If a new
    close/reduce/stop path is ever added without an attribution check, this
    fails the first time it is run.
    """
    for name, (args, kw) in CALLS.items():
        cli = his_client()
        v = build(cli)
        rec = getattr(v, name)(*args, **kw)
        assert not cli.touched_anything(), (
            f"{name}() reached the exchange on a position the bot did not "
            f"open: orders={cli.placed} brackets={cli.brackets} "
            f"cancels={cli.cancels}")
        assert rec.get("status") == "rejected", f"{name} -> {rec}"
        assert rec.get("refused_by") == "attribution", f"{name} -> {rec}"


def test_reduce_paths_still_work_on_our_own_position():
    """The guard has to be a gate, not a wall. On a position the bot did open,
    the same calls go through."""
    cli = ours_client()
    v = build(cli)
    r = v.place_stop(SYMBOL, 59000.0)
    assert r["status"] == "placed", r
    assert cli.brackets and cli.brackets[0]["sl"] == 59000.0
    assert attribution.is_ours_coid(cli.brackets[0]["client_order_id"])

    cli2 = ours_client()
    v2 = build(cli2)
    r2 = v2.close_position(SYMBOL)
    assert r2["status"] == "filled", r2
    assert cli2.placed and cli2.placed[0]["reduce_only"] is True
    assert attribution.is_ours_coid(cli2.placed[0]["client_order_id"])


def test_partial_close_is_first_class():
    cli = ours_client(size=10.0)          # 10 contracts = 0.01 BTC
    v = build(cli)
    r = v.close_position(SYMBOL, 0.005)   # half, in coins
    assert r["status"] == "filled", r
    assert abs(cli.placed[0]["contracts"] - 5.0) < 1e-9, cli.placed


def test_his_position_is_invisible_not_flagged():
    """It does not appear in positions(), does not answer position(), and
    does not count toward open risk. A position the bot cannot see is one it
    cannot reason itself into touching."""
    v = build(his_client())
    assert v.positions() == []
    assert v.position(SYMBOL) is None
    assert v.open_risk() == 0.0
    foreign = v.foreign_positions()
    assert len(foreign) == 1 and foreign[0]["symbol"] == SYMBOL
    assert foreign[0]["why_not_ours"]


def test_opening_is_refused_on_a_symbol_he_already_holds():
    """BloFin nets everything on a symbol into ONE position. Opening beside
    his would fuse the two and neither could be managed after that."""
    cli = his_client()
    v = build(cli)
    r = v.market_order(SYMBOL, "buy", 0.01, reference_price=60000.0,
                       stop=59500.0)
    assert r["status"] == "rejected", r
    assert r["refused_by"] == "attribution"
    assert not cli.placed


def test_opening_works_on_a_clean_symbol():
    cli = FakeClient(position=None, orders=[])
    v = build(cli)
    r = v.market_order(SYMBOL, "buy", 0.01, reference_price=60000.0,
                       stop=59500.0)
    assert r["status"] == "filled", r
    assert cli.placed and cli.placed[0]["reduce_only"] is False
    assert attribution.is_ours_coid(cli.placed[0]["client_order_id"]), cli.placed
    assert cli.leverage_calls, "leverage must be set before the order"
    assert cli.leverage_calls[0][2] == "isolated"


def test_unreadable_history_blocks_the_reduce():
    """A throttled read is not permission."""
    cli = FakeClient(position=position_row(), orders=[order_row(OURS_COID)],
                     history_raises=True)
    v = build(cli)
    r = v.close_position(SYMBOL)
    assert r["status"] == "rejected", r
    assert not cli.touched_anything()


def test_cancel_stops_leaves_his_brackets_alone():
    """Even on a position the bot DID open, a bracket he placed himself is
    his instruction and is not cancelled. This is the exact act that stripped
    protection off a live position on 2026-07-23."""
    cli = ours_client()
    cli._pending = [{"tpslId": "his-1", "clientOrderId": ""},
                    {"tpslId": "ours-1", "clientOrderId": OURS_COID}]
    v = build(cli)
    r = v.cancel_stops(SYMBOL)
    assert r["status"] == "done", r
    assert [c["tpsl_id"] for c in cli.cancels] == ["ours-1"], cli.cancels
    assert "his-1" in r["left_alone"]


# =========================================  THE SEALED CLIENT (LAYER THREE)
def test_sealed_client_blocks_a_bracket_outside_the_guard():
    v = build(ours_client())
    try:
        v._cli.place_tpsl(INST, "sell", 1.0, None, 59000.0)
    except venue_mod.NotOurs:
        return
    raise AssertionError("place_tpsl ran without the attribution guard open")


def test_sealed_client_blocks_a_reduce_only_order_outside_the_guard():
    v = build(ours_client())
    try:
        v._cli.market_order(INST, "sell", 1.0, reduce_only=True)
    except venue_mod.NotOurs:
        return
    raise AssertionError("a reduce-only order ran without the guard open")


def test_sealed_client_blocks_a_cancel_outside_the_guard():
    v = build(ours_client())
    for call in (lambda: v._cli.cancel_tpsl(INST, "x"),
                 lambda: v._cli.cancel_order(INST, "x")):
        try:
            call()
        except venue_mod.NotOurs:
            continue
        raise AssertionError("a cancel ran without the attribution guard open")


def test_sealed_client_lets_an_opening_order_through():
    """The seal is on reducing, not on everything. An opening order is a
    fresh position and needs no attribution."""
    cli = ours_client()
    v = build(cli)
    v._cli.market_order(INST, "buy", 1.0)
    assert cli.placed


def test_the_door_shuts_again_after_a_guarded_action():
    """Including when the action blows up. A door left open by an exception
    would be a guard that works until the first bad night."""
    cli = ours_client()
    v = build(cli)

    def boom(_verdict):
        raise RuntimeError("something went wrong mid-action")

    try:
        v._guarded_reduce(SYMBOL, "close", boom)
    except RuntimeError:
        pass
    assert object.__getattribute__(v._cli, "open_for") is None
    try:
        v._cli.place_tpsl(INST, "sell", 1.0, None, 1.0)
    except venue_mod.NotOurs:
        return
    raise AssertionError("the guard door stayed open after an exception")


# ==============================================  THE VENUE SAFETY GUARD
def test_blofin_is_registered_as_not_real_money():
    reg = venue_mod.registered()
    assert "blofin-demo" in reg
    assert reg["blofin-demo"]["real_money"] is False


def test_unknown_venue_still_falls_back_to_paper():
    # state_path/log_path None on purpose: resolving paper with its defaults
    # would write the REAL paper account's state file, and test_paper.py has
    # a test whose whole job is to catch exactly that.
    _, d = venue_mod.resolve("blofin-live", env={}, state_path=None,
                             log_path=None)
    assert d["chosen"] == "paper"
    assert d["real_money"] is False


# ====================================================================== RUN
def main() -> int:
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f"  ok    {name}")
        except Exception:                                    # noqa: BLE001
            failed.append(name)
            print(f"  FAIL  {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed")
    if failed:
        print("failed: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
